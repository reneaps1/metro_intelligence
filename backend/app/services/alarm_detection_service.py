"""Live Monitor alarm fix (2026-07): persists a real, auditable `Alert` row
from `app.engines.spc.alarm_rules`' pure rule output.

Detection only ever happens from the WS live-replay path (`_run_one` in
`app.api.v1.live_monitor`), never from the read-only `/capability-history`
endpoint -- that endpoint is documented end-to-end as having no side effects
(`app.api.v1.measurements` module docstring), and it recomputes on every
date-range change, which would duplicate alarms on every page revisit. The
WS replay evaluates each point/window exactly once, which is what makes it
the correct, idempotent trigger point (paired with the dedup check below).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.spc.alarm_rules import AlarmRuleResult
from app.models.intelligence import Alert
from app.models.measurement import MeasurementResult
from app.services.audit_service import write_audit_log

# The WS replay task has no authenticated HTTP request to build an
# `AuditContext` from (`app.services.audit_service.get_audit_context` depends
# on `get_current_user`) -- this is a system-detected event, not a user
# action, so it uses `write_audit_log`'s lower-level primitive directly, the
# same "pre-auth" shape `app.api.v1.auth` uses for events with no resolved
# actor.
SYSTEM_ACTOR_IDENTIFIER = "system:alarm_rules_engine"

# Roles this alarm type is delivered to -- the shop-floor/quality roles that
# act on a live measurement alarm day to day, not every role rbac.md
# eventually permits to *read* one via `GET /alerts` (viewer/auditor can
# still read it, just aren't its primary audience).
TARGET_ROLES = ["metrologist", "quality_engineer", "admin"]


class MeasurementResultNotFoundError(ValueError):
    """No `MeasurementResult` row matches the triggering event's
    (characteristic_id, measured_at) -- should not happen for a point the
    replay just evaluated from real seeded data, but this fails loudly
    instead of silently inventing a `trigger_id`."""


def _find_open_alert(db: Session, characteristic_id: uuid.UUID, trigger_type: str) -> Alert | None:
    stmt = select(Alert).where(
        Alert.characteristic_id == characteristic_id,
        Alert.trigger_type == trigger_type,
        Alert.acknowledged_at.is_(None),
    )
    return db.execute(stmt).scalars().first()


def _resolve_trigger_id(db: Session, characteristic_id: uuid.UUID, measured_at: datetime) -> uuid.UUID:
    stmt = (
        select(MeasurementResult.id)
        .where(
            MeasurementResult.characteristic_id == characteristic_id,
            MeasurementResult.measured_at == measured_at,
        )
        .limit(1)
    )
    result_id = db.execute(stmt).scalar_one_or_none()
    if result_id is None:
        raise MeasurementResultNotFoundError(
            f"No measurement result found for characteristic {characteristic_id} at {measured_at}."
        )
    return result_id


def record_alarm_if_new(
    db: Session,
    characteristic_id: uuid.UUID,
    rule_result: AlarmRuleResult,
    event_measured_at: datetime,
) -> Alert | None:
    """Edge-triggered: only opens a new alert if there is no existing *open*
    (unacknowledged) alert for this (characteristic, rule) pair -- otherwise
    every consecutive NOK point, or every recalculation still under the
    capability threshold, would spam a new row. One open alert per rule per
    characteristic until acknowledged. Does not commit -- the caller controls
    the transaction boundary."""
    if _find_open_alert(db, characteristic_id, rule_result.trigger_type) is not None:
        return None

    trigger_id = _resolve_trigger_id(db, characteristic_id, event_measured_at)
    now = datetime.now(UTC)

    alert = Alert(
        severity=rule_result.severity,
        target_roles=TARGET_ROLES,
        trigger_type=rule_result.trigger_type,
        trigger_id=trigger_id,
        characteristic_id=characteristic_id,
        engine_name=rule_result.engine_name,
        engine_version=rule_result.engine_version,
        rationale=rule_result.rationale,
        computed_inputs=rule_result.computed_inputs,
        message=rule_result.rationale,
        delivered_at=now,
    )
    db.add(alert)
    db.flush()

    write_audit_log(
        db,
        action="created",
        entity_type="intelligence.alert",
        actor_identifier=SYSTEM_ACTOR_IDENTIFIER,
        entity_id=alert.id,
        after_state={
            "characteristic_id": str(characteristic_id),
            "trigger_type": rule_result.trigger_type,
            "severity": rule_result.severity,
            "rationale": rule_result.rationale,
            "computed_inputs": rule_result.computed_inputs,
            "engine_name": rule_result.engine_name,
            "engine_version": rule_result.engine_version,
        },
    )

    return alert
