"""LM.1 (docs/tasks/LM1-live-monitor-mvp.md): unit tests for the pure,
DB-free replay event builder. No database, no event loop -- this is the
"replay is deterministic" acceptance criterion in isolation. RBAC, the
WebSocket wire format, and the no-persistence guarantee are covered in
``test_live_monitor_api.py`` against a real Postgres instance.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.catalog import Specification
from app.models.measurement import MeasurementResult
from app.services.live_replay_service import (
    ControlLimitsEvent,
    PointEvent,
    build_replay_events,
)


def _spec(**overrides: object) -> Specification:
    defaults: dict[str, object] = {
        "nominal": Decimal("10"),
        "lower_tol": Decimal("-1"),
        "upper_tol": Decimal("1"),
        "unit": "mm",
    }
    defaults.update(overrides)
    return Specification(**defaults)  # type: ignore[arg-type]


def _results(values: list[str], start: datetime) -> list[MeasurementResult]:
    return [
        MeasurementResult(value=Decimal(v), measured_at=start + timedelta(days=i))
        for i, v in enumerate(values)
    ]


def test_same_input_produces_the_same_event_sequence() -> None:
    characteristic_id = uuid.uuid4()
    spec = _spec()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    values = ["10.1", "9.8", "10.3", "10.0", "9.9", "10.2"]

    first = build_replay_events(characteristic_id, spec, _results(values, start))
    second = build_replay_events(characteristic_id, spec, _results(values, start))

    assert first == second
    assert len(first) > 0


def test_different_starting_point_changes_the_sequence() -> None:
    characteristic_id = uuid.uuid4()
    spec = _spec()
    start = datetime(2026, 1, 1, tzinfo=UTC)

    from_the_start = build_replay_events(characteristic_id, spec, _results(["10.1", "9.8", "10.3"], start))
    from_the_second_point = build_replay_events(characteristic_id, spec, _results(["9.8", "10.3"], start))

    assert from_the_start != from_the_second_point


def test_point_events_carry_real_compliance_evaluation() -> None:
    characteristic_id = uuid.uuid4()
    spec = _spec()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    results = _results(["10.5", "11.5"], start)  # nominal 10 +/-1: first OK, second NOK

    events = build_replay_events(characteristic_id, spec, results)
    points = [e for e in events if isinstance(e, PointEvent)]

    assert len(points) == 2
    assert points[0].is_ok is True
    assert points[0].deviation == Decimal("0.5")
    assert points[0].engine_name == "compliance_engine"
    assert points[1].is_ok is False
    assert points[1].characteristic_id == characteristic_id


def test_control_limits_recalculated_every_n_points() -> None:
    characteristic_id = uuid.uuid4()
    spec = _spec()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    values = [str(Decimal("10.0") + Decimal("0.1") * (i % 3)) for i in range(12)]
    results = _results(values, start)

    events = build_replay_events(characteristic_id, spec, results, control_limit_recalc_every=5)
    control_events = [e for e in events if isinstance(e, ControlLimitsEvent)]

    # 12 points, recalculated every 5th point -> fires after point 5 and point 10.
    assert len(control_events) == 2
    assert all(e.engine_name == "spc_engine" for e in control_events)
    assert events.index(control_events[0]) == 5  # right after the 5th PointEvent (indices 0-4)


def test_zero_variance_run_reports_control_limits_without_cpk() -> None:
    characteristic_id = uuid.uuid4()
    spec = _spec()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    results = _results(["10.0"] * 6, start)

    events = build_replay_events(characteristic_id, spec, results, control_limit_recalc_every=5)
    control_events = [e for e in events if isinstance(e, ControlLimitsEvent)]

    assert len(control_events) == 1
    assert control_events[0].cpk is None
    assert control_events[0].center_line == Decimal("10.0")


def test_no_control_limits_event_before_the_first_recalc_threshold() -> None:
    characteristic_id = uuid.uuid4()
    spec = _spec()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    results = _results(["10.1", "9.9", "10.0"], start)

    events = build_replay_events(characteristic_id, spec, results, control_limit_recalc_every=5)

    assert all(isinstance(e, PointEvent) for e in events)
    assert len(events) == 3
