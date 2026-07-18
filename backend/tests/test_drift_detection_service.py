"""Phase 13 preview: integration test for
``app.services.drift_detection_service`` against a real Postgres instance
(CLAUDE.md §11) -- confirms the real wiring (compute_capability_history's
windows -> the CUSUM engine) against real `MeasurementResult` rows, not just
the pure-function vectors in ``test_drift_cusum.py``."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.database import SessionLocal
from app.models.catalog import (
    Characteristic,
    CharacteristicClassification,
    MeasurementProgram,
    PartNumber,
    ProductFamily,
    Specification,
)
from app.models.measurement import MeasurementResult, MeasurementRun, MeasurementSample
from app.services.drift_detection_service import compute_experimental_drift

# Deterministic, distinct offsets within one window -- never all-identical,
# so each window's own Cpk is defined (nonzero within-window stdev).
TIGHT_OFFSETS = [Decimal("-0.02"), Decimal("-0.01"), Decimal("0"), Decimal("0.01"), Decimal("0.02")]
LOOSE_OFFSETS = [Decimal("-0.9"), Decimal("-0.5"), Decimal("0"), Decimal("0.5"), Decimal("0.9")]
WINDOW_SIZE = len(TIGHT_OFFSETS)


def _make_characteristic(db) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    suffix = uuid.uuid4().hex[:8]
    family = ProductFamily(code=f"MI-DEMO-DFT-{suffix}", name="Demo family (fictitious)")
    db.add(family)
    db.flush()
    part = PartNumber(product_family_id=family.id, code=f"MI-DEMO-DFT-{suffix}", name="Demo bracket")
    db.add(part)
    classification = CharacteristicClassification(code=f"DFT-CLS-{suffix}", name="Demo classification")
    db.add(classification)
    db.flush()
    characteristic = Characteristic(
        part_number_id=part.id,
        balloon_number="1",
        name="Drift demo diameter",
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
    program = MeasurementProgram(
        part_number_id=part.id, name="Drift CMM Program", output_mapping={"1": "COL_1"}
    )
    db.add(program)
    db.flush()
    db.commit()
    return characteristic.id, spec.id, program.id


def _insert_windows(
    db, characteristic_id, spec_id, program_id, *, n_windows: int, offsets: list[Decimal], start=None
):
    cursor = start or datetime(2026, 1, 1, tzinfo=UTC)
    for _ in range(n_windows):
        run = MeasurementRun(measurement_program_id=program_id, operator_identifier="OP", run_at=cursor)
        db.add(run)
        db.flush()
        sample = MeasurementSample(measurement_run_id=run.id, sample_sequence=1)
        db.add(sample)
        db.flush()
        for offset in offsets:
            db.add(
                MeasurementResult(
                    measured_at=cursor,
                    measurement_sample_id=sample.id,
                    characteristic_id=characteristic_id,
                    specification_id=spec_id,
                    value=Decimal(10) + offset,
                )
            )
            cursor += timedelta(minutes=1)
    db.commit()
    return cursor


def test_none_when_too_few_windows(auth_database: None) -> None:
    db = SessionLocal()
    try:
        characteristic_id, spec_id, program_id = _make_characteristic(db)
        _insert_windows(db, characteristic_id, spec_id, program_id, n_windows=2, offsets=TIGHT_OFFSETS)

        result = compute_experimental_drift(
            db, characteristic_id, from_=None, to=None, window_size=WINDOW_SIZE
        )
        assert result is None
    finally:
        db.close()


def test_drift_detected_across_a_capability_regime_shift(auth_database: None) -> None:
    db = SessionLocal()
    try:
        characteristic_id, spec_id, program_id = _make_characteristic(db)
        cursor = _insert_windows(
            db, characteristic_id, spec_id, program_id, n_windows=12, offsets=TIGHT_OFFSETS
        )
        _insert_windows(
            db, characteristic_id, spec_id, program_id, n_windows=12, offsets=LOOSE_OFFSETS, start=cursor
        )

        result = compute_experimental_drift(
            db, characteristic_id, from_=None, to=None, window_size=WINDOW_SIZE
        )

        assert result is not None
        assert result.drift_detected is True
        assert result.engine_name == "cusum_drift_engine"
        assert result.engine_version == "v1-experimental"
        assert len(result.points) == 24
    finally:
        db.close()
