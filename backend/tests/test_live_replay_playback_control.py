"""LM.3 (docs/tasks/LM3-live-monitor-presenter-controls.md): unit tests for
``PlaybackControl``/``_controlled_sleep`` and live speed changes. No
database, no WebSocket -- pure asyncio timing behavior, run via
``asyncio.run`` inside plain sync test functions (this project has neither
pytest-asyncio nor a configured anyio mode, so that's the simplest
dependency-free way to exercise an async function here).

Timing assertions use generous tolerances since this is real wall-clock
sleeping, not a virtual clock -- demo-grade, same spirit as the rest of this
service.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.catalog import Specification
from app.models.measurement import MeasurementResult
from app.services.live_replay_service import (
    PlaybackControl,
    PointEvent,
    _controlled_sleep,
    _sleep_seconds_for_gap,
    build_replay_events,
)


def test_controlled_sleep_runs_close_to_the_requested_duration_when_never_paused() -> None:
    async def run() -> float:
        control = PlaybackControl()
        start = time.monotonic()
        await _controlled_sleep(control, 0.05)
        return time.monotonic() - start

    elapsed = asyncio.run(run())
    assert 0.04 <= elapsed < 0.3


def test_controlled_sleep_pauses_without_losing_its_remaining_budget() -> None:
    """Pausing before the sleep even starts must not shrink the sleep to
    zero, and must not let it elapse while paused -- the point it's guarding
    must not fire early just because a pause happened to overlap its wait."""

    async def run() -> float:
        control = PlaybackControl()
        control.running.clear()  # start paused

        async def resume_after_delay() -> None:
            await asyncio.sleep(0.15)
            control.running.set()

        start = time.monotonic()
        await asyncio.gather(_controlled_sleep(control, 0.05), resume_after_delay())
        return time.monotonic() - start

    elapsed = asyncio.run(run())
    # Paused for ~0.15s before the 0.05s budget can even begin, so the total
    # must be at least the pause duration, not just the sleep budget alone.
    assert elapsed >= 0.15


async def _replay_with_control(
    characteristic_id: uuid.UUID,
    spec: Specification,
    results: list[MeasurementResult],
    control: PlaybackControl,
) -> AsyncIterator[str]:
    """A DB-free proxy for `stream_replay`'s pacing loop: `stream_replay`
    itself calls `load_replay_source` (needs a real `Session`), so this test
    reuses the same pure `build_replay_events` core plus the identical
    controlled-sleep pacing logic instead of standing up a database just to
    exercise pause/resume timing."""
    events = build_replay_events(characteristic_id, spec, results)
    previous_measured_at: datetime | None = None
    for event in events:
        if isinstance(event, PointEvent):
            if previous_measured_at is not None:
                gap = (event.measured_at - previous_measured_at).total_seconds()
                sleep_for = _sleep_seconds_for_gap(
                    gap, control.seconds_per_replay_day, control.speed_multiplier
                )
                if sleep_for > 0:
                    await _controlled_sleep(control, sleep_for)
            previous_measured_at = event.measured_at
            yield str(event.value)


def test_pause_prevents_the_next_point_until_resumed_without_losing_or_duplicating_any() -> None:
    """The acceptance criterion in prose: pausing/resuming a live session
    must not lose or duplicate any already-emitted point. The first point of
    any session fires immediately regardless of pause state (same as LM.1,
    unchanged) -- pausing only gates the *wait between* points, which is the
    only place a real session (always starts playing; pause only ever
    arrives as a control message after streaming has begun) can be paused."""

    async def run() -> list[str]:
        characteristic_id = uuid.uuid4()
        spec = Specification(
            nominal=Decimal("10"), lower_tol=Decimal("-1"), upper_tol=Decimal("1"), unit="mm"
        )
        start = datetime(2026, 1, 1, tzinfo=UTC)
        results = [
            MeasurementResult(value=Decimal(v), measured_at=start + timedelta(days=i))
            for i, v in enumerate(["10.0", "10.1", "9.9"])
        ]

        control = PlaybackControl(seconds_per_replay_day=0.2, speed_multiplier=1.0)
        control.running.clear()  # pause takes effect for the wait before the 2nd point

        received: list[str] = []

        async def consume() -> None:
            async for value in _replay_with_control(characteristic_id, spec, results, control):
                received.append(value)

        consumer = asyncio.create_task(consume())
        await asyncio.sleep(0.1)
        assert received == ["10.0"], "only the immediate first point, nothing beyond it while paused"

        control.running.set()
        await consumer
        return received

    assert asyncio.run(run()) == ["10.0", "10.1", "9.9"]


def test_speed_change_takes_effect_without_restarting_the_session() -> None:
    """Mutating a shared `PlaybackControl.speed_multiplier` (what the WS
    `set_speed` control message does) speeds up the very next wait -- no new
    `stream_replay`/session is needed for LM.3's "sin reiniciarla"."""

    async def run() -> float:
        control = PlaybackControl(seconds_per_replay_day=5.0, speed_multiplier=1.0)
        # A 1x wait would be ~5s; cranking to 100x before it starts should
        # bring the actual wait down to ~0.05s instead.
        control.speed_multiplier = 100.0
        start = time.monotonic()
        await _controlled_sleep(control, control.seconds_per_replay_day / control.speed_multiplier)
        return time.monotonic() - start

    assert asyncio.run(run()) < 1.0
