"""Live Monitor alarm fix: integration tests for
``app.services.alarm_detection_service`` against a real Postgres instance
(CLAUDE.md §11) -- dedup, ``trigger_id`` resolution, and the audit trail
CLAUDE.md §23 requires. WS wiring itself is covered in
``test_live_monitor_api.py``."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import sqlalchemy as sa
from app.core.database import SessionLocal
from app.engines.spc.alarm_rules import evaluate_capability_alarm, evaluate_compliance_alarm
from app.models.catalog import (
    Characteristic,
    CharacteristicClassification,
    MeasurementProgram,
    PartNumber,
    ProductFamily,
    Specification,
)
from app.models.intelligence import Alert
from app.models.measurement import MeasurementResult, MeasurementRun, MeasurementSample
from app.models.security import AuditLog
from app.services.alarm_detection_service import record_alarm_if_new


def _make_characteristic_with_result(db, *, value: Decimal) -> dict:
    suffix = uuid.uuid4().hex[:8]
    family = ProductFamily(code=f"MI-DEMO-ALM-{suffix}", name="Demo family (fictitious)")
    db.add(family)
    db.flush()
    part = PartNumber(product_family_id=family.id, code=f"MI-DEMO-ALM-{suffix}", name="Demo bracket")
    db.add(part)
    classification = CharacteristicClassification(code=f"ALM-CLS-{suffix}", name="Demo classification")
    db.add(classification)
    db.flush()
    characteristic = Characteristic(
        part_number_id=part.id,
        balloon_number="1",
        name="Alarm demo diameter",
        characteristic_type="diameter",
        unit="mm",
        classification_id=classification.id,
    )
    db.add(characteristic)
    db.flush()
    spec = Specification(
        characteristic_id=characteristic.id, nominal=10, lower_tol=-1, upper_tol=1, unit="mm"
    )
    db.add(spec)
    db.flush()
    program = MeasurementProgram(
        part_number_id=part.id, name="Alarm CMM Program", output_mapping={"1": "COL_1"}
    )
    db.add(program)
    db.flush()

    measured_at = datetime(2026, 1, 1, tzinfo=UTC)
    run = MeasurementRun(measurement_program_id=program.id, operator_identifier="OP", run_at=measured_at)
    db.add(run)
    db.flush()
    sample = MeasurementSample(measurement_run_id=run.id, sample_sequence=1)
    db.add(sample)
    db.flush()
    result = MeasurementResult(
        measured_at=measured_at,
        measurement_sample_id=sample.id,
        characteristic_id=characteristic.id,
        specification_id=spec.id,
        value=value,
    )
    db.add(result)
    db.commit()
    return {"characteristic_id": characteristic.id, "measured_at": measured_at, "result_id": result.id}


def test_records_a_new_alert_with_real_engine_attribution_and_computed_inputs(auth_database: None) -> None:
    db = SessionLocal()
    try:
        ctx = _make_characteristic_with_result(db, value=Decimal("11.5"))
        rule_result = evaluate_compliance_alarm(
            is_ok=False, rationale="Out of tolerance.", value=Decimal("11.5"), deviation=Decimal("1.5")
        )
        assert rule_result is not None

        alert = record_alarm_if_new(db, ctx["characteristic_id"], rule_result, ctx["measured_at"])
        db.commit()

        assert alert is not None
        assert alert.characteristic_id == ctx["characteristic_id"]
        assert alert.trigger_id == ctx["result_id"]
        assert alert.trigger_type == "compliance_violation"
        assert alert.rationale == "Out of tolerance."
        assert alert.computed_inputs == {"value": "11.5", "deviation": "1.5"}
        assert alert.engine_name == "alarm_rules_engine"
        assert alert.acknowledged_at is None
    finally:
        db.close()


def test_does_not_open_a_second_alert_while_one_is_already_open_for_the_same_rule(
    auth_database: None,
) -> None:
    db = SessionLocal()
    try:
        ctx = _make_characteristic_with_result(db, value=Decimal("11.5"))
        rule_result = evaluate_compliance_alarm(
            is_ok=False, rationale="Out of tolerance.", value=Decimal("11.5"), deviation=Decimal("1.5")
        )
        assert rule_result is not None

        first = record_alarm_if_new(db, ctx["characteristic_id"], rule_result, ctx["measured_at"])
        db.commit()
        second = record_alarm_if_new(db, ctx["characteristic_id"], rule_result, ctx["measured_at"])
        db.commit()

        assert first is not None
        assert second is None

        open_count = db.execute(
            sa.select(sa.func.count())
            .select_from(Alert)
            .where(
                Alert.characteristic_id == ctx["characteristic_id"],
                Alert.trigger_type == "compliance_violation",
            )
        ).scalar_one()
        assert open_count == 1
    finally:
        db.close()


def test_opens_a_new_alert_once_the_previous_one_is_acknowledged(auth_database: None) -> None:
    db = SessionLocal()
    try:
        ctx = _make_characteristic_with_result(db, value=Decimal("11.5"))
        rule_result = evaluate_compliance_alarm(
            is_ok=False, rationale="Out of tolerance.", value=Decimal("11.5"), deviation=Decimal("1.5")
        )
        assert rule_result is not None

        first = record_alarm_if_new(db, ctx["characteristic_id"], rule_result, ctx["measured_at"])
        db.commit()
        assert first is not None

        first.acknowledged_at = datetime.now(UTC)
        db.commit()

        second = record_alarm_if_new(db, ctx["characteristic_id"], rule_result, ctx["measured_at"])
        db.commit()

        assert second is not None
        assert second.id != first.id
    finally:
        db.close()


def test_capability_alarm_records_cpk_and_control_limits_as_computed_inputs(auth_database: None) -> None:
    db = SessionLocal()
    try:
        ctx = _make_characteristic_with_result(db, value=Decimal("10.0"))
        rule_result = evaluate_capability_alarm(cpk=Decimal("0.90"), ucl=Decimal("10.1"), lcl=Decimal("9.9"))
        assert rule_result is not None

        alert = record_alarm_if_new(db, ctx["characteristic_id"], rule_result, ctx["measured_at"])
        db.commit()

        assert alert is not None
        assert alert.trigger_type == "capability_below_threshold"
        assert alert.severity == "critical"
        assert alert.computed_inputs["cpk"] == "0.90"
    finally:
        db.close()


def test_records_an_audit_log_entry_with_no_authenticated_actor(auth_database: None) -> None:
    # The WS replay task has no HTTP request/authenticated user to attribute
    # this to -- it's a system-detected event (CLAUDE.md §23 still requires
    # the audit trail to exist, just with a system actor identifier instead
    # of a user id).
    db = SessionLocal()
    try:
        ctx = _make_characteristic_with_result(db, value=Decimal("11.5"))
        rule_result = evaluate_compliance_alarm(
            is_ok=False, rationale="Out of tolerance.", value=Decimal("11.5"), deviation=Decimal("1.5")
        )
        assert rule_result is not None

        alert = record_alarm_if_new(db, ctx["characteristic_id"], rule_result, ctx["measured_at"])
        db.commit()
        assert alert is not None

        log_entry = db.execute(
            sa.select(AuditLog).where(
                AuditLog.entity_type == "intelligence.alert", AuditLog.entity_id == alert.id
            )
        ).scalar_one()
        assert log_entry.actor_user_id is None
        assert log_entry.actor_identifier == "system:alarm_rules_engine"
        assert log_entry.action == "created"
    finally:
        db.close()
