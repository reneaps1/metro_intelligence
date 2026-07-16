"""LM.4 (docs/tasks/LM4-live-monitor-deep-dive.md): capability-history
windowing tests, against a real disposable PostgreSQL (same fixture pattern
as test_measurements_api.py's `demo_characteristic`).

The underlying Cpk/control-limit math itself is F8.D's own responsibility
and already hand-verified in test_spc_engine.py -- these tests check that
this module partitions rows into windows correctly (determinism, the
spec-version-boundary split, and the <2-point edge case), not that cpk()
computes the right number for a given input.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
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
from app.models.org import Area, Cell, Line, Machine, Organization, Site
from app.services.capability_history_service import compute_capability_history


@pytest.fixture
def demo_machine() -> uuid.UUID:
    suffix = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        org = Organization(code=f"ORG-{suffix}", name="Demo org (fictitious)")
        db.add(org)
        db.flush()
        site = Site(organization_id=org.id, code=f"SITE-{suffix}", name="Demo site")
        db.add(site)
        db.flush()
        area = Area(site_id=site.id, code=f"AREA-{suffix}", name="Demo area")
        db.add(area)
        db.flush()
        line = Line(area_id=area.id, code=f"LINE-{suffix}", name="Demo line")
        db.add(line)
        db.flush()
        cell = Cell(line_id=line.id, code=f"CELL-{suffix}", name="Demo cell")
        db.add(cell)
        db.flush()
        machine = Machine(cell_id=cell.id, code=f"CMM-{suffix}", name="Demo CMM")
        db.add(machine)
        db.commit()
        return machine.id
    finally:
        db.close()


@pytest.fixture
def characteristic_with_two_spec_versions(demo_machine: uuid.UUID) -> dict:
    """12 results on the old spec (+/-1), then 6 more on a new spec (+/-2)
    that takes over -- enough for a window_size=5 partition to land a
    boundary mid-window on the old side, and a short 6-point tail on the
    new side."""
    suffix = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        family = ProductFamily(code=f"MI-DEMO-FAM-{suffix}", name="Demo family (fictitious)")
        db.add(family)
        db.flush()
        part = PartNumber(product_family_id=family.id, code=f"MI-DEMO-{suffix}", name="Demo bracket")
        db.add(part)
        classification = CharacteristicClassification(code=f"CLS-{suffix}", name="Demo classification")
        db.add(classification)
        db.flush()
        characteristic = Characteristic(
            part_number_id=part.id,
            balloon_number="1",
            name="Demo diameter",
            characteristic_type="diameter",
            unit="mm",
            classification_id=classification.id,
        )
        db.add(characteristic)
        db.flush()

        start = datetime(2026, 1, 1, tzinfo=UTC)
        boundary = start + timedelta(days=12)
        old_spec = Specification(
            characteristic_id=characteristic.id,
            nominal=10,
            lower_tol=-1,
            upper_tol=1,
            unit="mm",
            valid_from=start,
            valid_to=boundary,
        )
        new_spec = Specification(
            characteristic_id=characteristic.id,
            nominal=10,
            lower_tol=-2,
            upper_tol=2,
            unit="mm",
            valid_from=boundary,
        )
        db.add_all([old_spec, new_spec])
        db.flush()

        program = MeasurementProgram(
            part_number_id=part.id, name="CMM Program", output_mapping={"1": "COL_1"}
        )
        db.add(program)
        db.flush()

        def _add_result(day: int, value: Decimal, spec_id: uuid.UUID) -> None:
            run = MeasurementRun(
                measurement_program_id=program.id,
                machine_id=demo_machine,
                operator_identifier="OP",
                batch_lot=f"BATCH-{day}",
                run_at=start + timedelta(days=day),
            )
            db.add(run)
            db.flush()
            sample = MeasurementSample(measurement_run_id=run.id, sample_sequence=1)
            db.add(sample)
            db.flush()
            db.add(
                MeasurementResult(
                    measured_at=run.run_at,
                    measurement_sample_id=sample.id,
                    characteristic_id=characteristic.id,
                    specification_id=spec_id,
                    value=value,
                )
            )
            db.flush()

        # Small alternating jitter so stdev isn't zero (cpk/control limits
        # need real variance to be defined).
        for day in range(12):
            value = Decimal("10.1") if day % 2 == 0 else Decimal("9.9")
            _add_result(day, value, old_spec.id)
        for day in range(12, 18):
            value = Decimal("10.2") if day % 2 == 0 else Decimal("9.8")
            _add_result(day, value, new_spec.id)

        db.commit()
        return {
            "characteristic_id": characteristic.id,
            "old_spec_id": old_spec.id,
            "new_spec_id": new_spec.id,
            "boundary": boundary,
        }
    finally:
        db.close()


def test_windowing_is_deterministic(characteristic_with_two_spec_versions: dict) -> None:
    db = SessionLocal()
    try:
        kwargs = dict(
            characteristic_id=characteristic_with_two_spec_versions["characteristic_id"],
            from_=None,
            to=None,
            window_size=5,
        )
        first = compute_capability_history(db, **kwargs)
        second = compute_capability_history(db, **kwargs)
    finally:
        db.close()

    assert [w.window_start for w in first] == [w.window_start for w in second]
    assert [w.point_count for w in first] == [w.point_count for w in second]
    assert [w.cpk for w in first] == [w.cpk for w in second]


def test_window_closes_early_at_a_spec_version_boundary(
    characteristic_with_two_spec_versions: dict,
) -> None:
    """window_size=5 would normally land points 11-15 in one window, but the
    old spec only covers points 0-11 (12 points) -- the window covering
    points 10-11 must close at exactly 2 points rather than reaching across
    into the new spec's points 12-14."""
    db = SessionLocal()
    try:
        windows = compute_capability_history(
            db,
            characteristic_id=characteristic_with_two_spec_versions["characteristic_id"],
            from_=None,
            to=None,
            window_size=5,
        )
    finally:
        db.close()

    # 12 old-spec points at window_size=5 -> [5, 5, 2], then 6 new-spec
    # points -> [5, 1]. No window may span the day-12 boundary.
    assert [w.point_count for w in windows] == [5, 5, 2, 5, 1]
    boundary = characteristic_with_two_spec_versions["boundary"]
    assert windows[2].window_end < boundary
    assert windows[3].window_start >= boundary


def test_window_with_fewer_than_two_points_reports_null_stats_not_a_crash(
    characteristic_with_two_spec_versions: dict,
) -> None:
    db = SessionLocal()
    try:
        windows = compute_capability_history(
            db,
            characteristic_id=characteristic_with_two_spec_versions["characteristic_id"],
            from_=None,
            to=None,
            window_size=5,
        )
    finally:
        db.close()

    single_point_window = windows[-1]
    assert single_point_window.point_count == 1
    assert single_point_window.cpk is None
    assert single_point_window.center_line is None
    assert single_point_window.ucl is None
    assert single_point_window.lcl is None
    assert single_point_window.engine_name is None


def test_windows_with_enough_points_carry_real_engine_output(
    characteristic_with_two_spec_versions: dict,
) -> None:
    db = SessionLocal()
    try:
        windows = compute_capability_history(
            db,
            characteristic_id=characteristic_with_two_spec_versions["characteristic_id"],
            from_=None,
            to=None,
            window_size=5,
        )
    finally:
        db.close()

    full_window = windows[0]
    assert full_window.point_count == 5
    assert full_window.center_line is not None
    assert full_window.ucl is not None
    assert full_window.lcl is not None
    assert full_window.ucl > full_window.center_line > full_window.lcl
    assert full_window.engine_name == "spc_engine"
    assert full_window.cpk is not None


def test_from_to_range_narrows_the_windowed_result_set(
    characteristic_with_two_spec_versions: dict,
) -> None:
    characteristic_id = characteristic_with_two_spec_versions["characteristic_id"]
    boundary = characteristic_with_two_spec_versions["boundary"]
    db = SessionLocal()
    try:
        all_windows = compute_capability_history(
            db, characteristic_id=characteristic_id, from_=None, to=None, window_size=5
        )
        narrowed = compute_capability_history(
            db, characteristic_id=characteristic_id, from_=boundary, to=None, window_size=5
        )
    finally:
        db.close()

    assert sum(w.point_count for w in narrowed) == 6
    assert sum(w.point_count for w in narrowed) < sum(w.point_count for w in all_windows)
