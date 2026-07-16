"""LM.1 (docs/tasks/LM1-live-monitor-mvp.md): deterministic replay of
already-seeded ``measurement_results`` for the Live Monitor demo panel.

This is a presentation-layer replay, not a new data source (CLAUDE.md §6,
docs/design/live-monitor-panel.md): it only reads rows that F3.3's seed
generator already wrote, in the order they were measured, and never inserts,
updates, or deletes a ``MeasurementResult``. Each replayed point is
re-evaluated with the real Compliance engine (F7.D) against the
characteristic's *currently active* specification (``valid_to IS NULL`` --
deliberately not the ``specification_id`` the original row was measured
against, since the point of the demo is to show the live pipeline
value -> evaluation -> event, not to reproduce history byte-for-byte). Every
``CONTROL_LIMIT_RECALC_EVERY`` points, the real SPC engine (F8.D) recomputes
Cpk and I-MR control limits over the values replayed so far.

Determinism: :func:`build_replay_events` is a pure function of
(characteristic_id, spec, ordered results) -- no randomness, no wall-clock
dependency -- so the same characteristic replayed from the same starting rows
always produces the same event sequence. Only :func:`stream_replay`'s pacing
(``asyncio.sleep`` between points) depends on wall-clock speed settings; the
event *sequence* it yields is exactly what :func:`build_replay_events` would
produce for the same input.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.compliance.evaluate import SpecificationSnapshot as ComplianceSpec
from app.engines.compliance.evaluate import evaluate
from app.engines.spc.capability import ToleranceSpec, cpk
from app.engines.spc.control_limits import individuals_moving_range_limits
from app.models.catalog import Characteristic, Specification
from app.models.measurement import MeasurementResult

CONTROL_LIMIT_RECALC_EVERY = 5
MIN_POINTS_FOR_CONTROL_LIMITS = 2

SECONDS_PER_DAY = 86400.0
DEFAULT_SECONDS_PER_REPLAY_DAY = 2.0
MAX_SLEEP_SECONDS = 5.0


@dataclass(frozen=True)
class PointEvent:
    characteristic_id: uuid.UUID
    value: Decimal
    deviation: Decimal
    is_ok: bool
    measured_at: datetime
    rationale: str
    engine_name: str
    engine_version: str


@dataclass(frozen=True)
class ControlLimitsEvent:
    characteristic_id: uuid.UUID
    cpk: Decimal | None
    center_line: Decimal
    ucl: Decimal
    lcl: Decimal
    engine_name: str
    engine_version: str


ReplayEvent = PointEvent | ControlLimitsEvent


class ReplayNotAvailable(ValueError):
    """Raised when a characteristic has no active specification or fewer
    than two measurement results -- nothing meaningful to replay/derive
    control limits from."""


def load_replay_source(
    db: Session, characteristic_id: uuid.UUID
) -> tuple[Specification, list[MeasurementResult]]:
    """Load the characteristic's active spec and its measured results, ordered
    by ``measured_at``. Raises :class:`ReplayNotAvailable` if there's nothing
    to replay -- the caller decides whether that skips one characteristic in
    a multi-signal stream or fails a single-characteristic request."""
    characteristic = db.get(Characteristic, characteristic_id)
    if characteristic is None:
        raise ReplayNotAvailable(f"Characteristic {characteristic_id} not found.")

    spec = db.execute(
        select(Specification).where(
            Specification.characteristic_id == characteristic_id,
            Specification.valid_to.is_(None),
        )
    ).scalar_one_or_none()
    if spec is None:
        raise ReplayNotAvailable(f"Characteristic {characteristic_id} has no active specification.")

    results = list(
        db.execute(
            select(MeasurementResult)
            .where(MeasurementResult.characteristic_id == characteristic_id)
            .order_by(MeasurementResult.measured_at)
        )
        .scalars()
        .all()
    )
    if len(results) < MIN_POINTS_FOR_CONTROL_LIMITS:
        raise ReplayNotAvailable(f"Characteristic {characteristic_id} has fewer than 2 measurement results.")

    return spec, results


def build_replay_events(
    characteristic_id: uuid.UUID,
    spec: Specification,
    results: list[MeasurementResult],
    *,
    control_limit_recalc_every: int = CONTROL_LIMIT_RECALC_EVERY,
) -> list[ReplayEvent]:
    """Pure event-sequence builder -- no DB access, no sleeping (CLAUDE.md
    §3's "engines are pure" spirit applied to this service's core logic so it
    can be unit-tested for determinism without a database or an event loop)."""
    compliance_spec = ComplianceSpec(
        nominal=spec.nominal, lower_tol=spec.lower_tol, upper_tol=spec.upper_tol, unit=spec.unit
    )
    tolerance_spec = ToleranceSpec(nominal=spec.nominal, lower_tol=spec.lower_tol, upper_tol=spec.upper_tol)

    events: list[ReplayEvent] = []
    accumulated: list[Decimal] = []

    for result in results:
        compliance = evaluate(result.value, compliance_spec)
        events.append(
            PointEvent(
                characteristic_id=characteristic_id,
                value=result.value,
                deviation=compliance.deviation,
                is_ok=compliance.is_ok,
                measured_at=result.measured_at,
                rationale=compliance.rationale,
                engine_name=compliance.engine_name,
                engine_version=compliance.engine_version,
            )
        )
        accumulated.append(result.value)

        due_for_recalc = (
            len(accumulated) >= MIN_POINTS_FOR_CONTROL_LIMITS
            and len(accumulated) % control_limit_recalc_every == 0
        )
        if due_for_recalc:
            limits = individuals_moving_range_limits(accumulated)
            try:
                cpk_value = cpk(accumulated, tolerance_spec)
            except ValueError:
                # Undefined for a unilateral spec or a zero-variance run so
                # far -- report the control limits without a Cpk rather than
                # dropping the whole update.
                cpk_value = None
            events.append(
                ControlLimitsEvent(
                    characteristic_id=characteristic_id,
                    cpk=cpk_value,
                    center_line=limits.center_line,
                    ucl=limits.individuals_ucl,
                    lcl=limits.individuals_lcl,
                    engine_name=limits.engine_name,
                    engine_version=limits.engine_version,
                )
            )

    return events


def _sleep_seconds_for_gap(
    gap_seconds: float, seconds_per_replay_day: float, speed_multiplier: float
) -> float:
    if gap_seconds <= 0 or speed_multiplier <= 0 or seconds_per_replay_day <= 0:
        return 0.0
    real_days = gap_seconds / SECONDS_PER_DAY
    return min(real_days * seconds_per_replay_day / speed_multiplier, MAX_SLEEP_SECONDS)


PAUSE_POLL_SECONDS = 0.1


@dataclass
class PlaybackControl:
    """LM.3 (docs/tasks/LM3-live-monitor-presenter-controls.md): shared,
    mutable playback state for one WS session. Built once per connection and
    passed to every characteristic's :func:`stream_replay` call so a single
    pause/resume/speed-change control message affects the whole session
    without restarting any of its tasks. ``running`` is set while playing,
    cleared while paused -- starts set (playing) per :meth:`__post_init__`.
    """

    seconds_per_replay_day: float = DEFAULT_SECONDS_PER_REPLAY_DAY
    speed_multiplier: float = 1.0
    running: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        self.running.set()


async def _controlled_sleep(control: PlaybackControl, total_seconds: float) -> None:
    """Sleep ``total_seconds``, but stop advancing while ``control.running``
    is cleared and resume from wherever it left off (never restarting the
    full duration) once it's set again -- this is what lets a pause/resume
    control message take effect on an in-flight wait without losing or
    re-emitting the point it's waiting to deliver. Ticking in small
    increments (rather than a single ``asyncio.sleep``) is what makes pause
    responsive instead of only checked once per point."""
    remaining = total_seconds
    while remaining > 0:
        await control.running.wait()
        tick = min(PAUSE_POLL_SECONDS, remaining)
        await asyncio.sleep(tick)
        remaining -= tick


async def stream_replay(
    db: Session,
    characteristic_id: uuid.UUID,
    *,
    seconds_per_replay_day: float = DEFAULT_SECONDS_PER_REPLAY_DAY,
    speed_multiplier: float = 1.0,
    control_limit_recalc_every: int = CONTROL_LIMIT_RECALC_EVERY,
    control: PlaybackControl | None = None,
) -> AsyncIterator[ReplayEvent]:
    """Yield :func:`build_replay_events`'s sequence for ``characteristic_id``,
    paced so that ``seconds_per_replay_day`` real seconds of clock time elapse
    per real day of measurement history (design target: 1-3s/day), scaled by
    ``speed_multiplier``. Pass a shared :class:`PlaybackControl` (LM.3) to let
    an external pause/resume/speed-change mutate an *in-flight* session; the
    ``seconds_per_replay_day``/``speed_multiplier`` kwargs still work
    standalone (LM.1's original call sites/tests) by building a private,
    unshared control internally when ``control`` is omitted. Raises
    :class:`ReplayNotAvailable` if the characteristic has no active spec or
    fewer than two results."""
    spec, results = load_replay_source(db, characteristic_id)
    events = build_replay_events(
        characteristic_id, spec, results, control_limit_recalc_every=control_limit_recalc_every
    )

    session_control = control or PlaybackControl(
        seconds_per_replay_day=seconds_per_replay_day, speed_multiplier=speed_multiplier
    )

    previous_measured_at: datetime | None = None
    for event in events:
        if isinstance(event, PointEvent):
            if previous_measured_at is not None:
                gap = (event.measured_at - previous_measured_at).total_seconds()
                sleep_for = _sleep_seconds_for_gap(
                    gap, session_control.seconds_per_replay_day, session_control.speed_multiplier
                )
                if sleep_for > 0:
                    await _controlled_sleep(session_control, sleep_for)
            previous_measured_at = event.measured_at
        yield event
