"""IQ-F7.b: long, hourly SIMULATED machine history with random failures.

Everything here is SIMULATED -- generic, physics-flavoured behaviour of a
fictitious injection-moulding cell, not data from any real plant, machine or
customer.

Generative model (per machine, own seeded RNG, hourly steps):

- Latent wear ``w`` grows a little every running hour at a per-machine rate.
  Scheduled preventive maintenance (about every 7 days, jittered) resets it to
  ~0; corrective repair after a failure only resets it partially.
- Failure hazard per hour is ``lambda = BASE_HAZARD + WEAR_HAZARD * w`` plus a
  short "infant mortality" bump right after a repair. Failures are drawn from
  this hazard ONLY -- the observable signals never feed back into it, so the
  signals are effects, not causes.
- Each failure draws a physical precursor with probability 0.6 (about 70 %
  realized in the fixed-seed history): vibration and motor current ramp up
  ``lead`` hours (3--10 h) before the failure. The rest have no precursor at
  all (not everything is predictable).
- Occasional precursor-like bumps that are NOT followed by a failure are added
  on purpose, so a model built on these signals has honest false alarms.
- Minor PLC alarms are a Poisson count whose rate rises with vibration.

Signals during downtime hours carry baseline-level values; those hours are
flagged in ``downtime`` and must be excluded from any training/evaluation row.

Pure and deterministic: no DB/IO, same machine -> same history (cached).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import lru_cache

HISTORY_VERSION = "failure-history-1.0.0"
SEED = 20261026
STEP_H = 1.0
MACHINES: tuple[str, ...] = ("INY-01", "INY-02", "INY-03", "INY-04")
WEEKS = 9
HOURS_PER_WEEK = 168
TOTAL_HOURS = WEEKS * HOURS_PER_WEEK

BASE_HAZARD = 0.003
WEAR_HAZARD = 0.022
POST_REPAIR_HAZARD = 0.02
POST_REPAIR_DECAY_H = 12.0
MAINTENANCE_PERIOD_H = 168
MAINTENANCE_JITTER_H = 12
REPAIR_WEAR_FACTOR = 0.5
DOWNTIME_RANGE_H = (2, 6)

PRECURSOR_PROBABILITY = 0.6
LEAD_RANGE_H = (3, 10)
MIN_PRECURSOR_LEAD_H = 3
FALSE_BUMP_RATE_PER_H = 1.0 / 120.0
FALSE_BUMP_DURATION_H = (3, 7)

VIBRATION_BASE_MM_S = 2.0
VIBRATION_WEAR_GAIN = 0.8
VIBRATION_NOISE = 0.25
VIBRATION_RAMP = 2.5
CURRENT_BASE_A = 45.0
CURRENT_WEAR_GAIN = 1.5
CURRENT_NOISE = 1.0
CURRENT_RAMP = 6.0
ALARM_BASE_RATE = 0.05
ALARM_VIBRATION_GAIN = 0.15


@dataclass(frozen=True)
class FailureEvent:
    """One simulated machine failure.

    Attributes:
        hour: Hour index (since simulation start) in which the machine failed.
        has_precursor: Whether vibration/current ramped up before the failure.
        lead_h: Hours between precursor onset and the failure, or ``None``.
    """

    hour: int
    has_precursor: bool
    lead_h: int | None


@dataclass(frozen=True)
class FailureHistory:
    """Hourly simulated history of one machine.

    Attributes:
        machine: Fictitious machine code.
        hours: Number of hourly steps.
        vibration: Vibration velocity (mm/s) per hour.
        current: Motor current (A) per hour.
        alarms: Count of minor PLC alarms per hour.
        failures: Failures in chronological order.
        maintenance_h: Hours at which preventive maintenance was performed.
        downtime: ``True`` for repair hours after a failure (machine stopped).
    """

    machine: str
    hours: int
    vibration: list[float]
    current: list[float]
    alarms: list[int]
    failures: list[FailureEvent]
    maintenance_h: list[int]
    downtime: list[bool]


def _poisson(rng: random.Random, rate: float) -> int:
    """Draws a Poisson count (Knuth's method; fine for small rates)."""
    limit = math.exp(-rate)
    count = 0
    product = rng.random()
    while product > limit:
        count += 1
        product *= rng.random()
    return count


def _simulate_events(
    rng: random.Random, hours: int
) -> tuple[list[float], list[int], list[int], list[bool], list[int]]:
    """First pass: wear, maintenance, failures and downtime (no signals).

    Returns:
        Tuple ``(wear, failure_hours, maintenance_h, downtime, downtime_end)``
        where ``downtime_end[i]`` is the first running hour after failure ``i``.
    """
    wear_rate = rng.uniform(0.8, 1.3) / HOURS_PER_WEEK
    next_maintenance = rng.randint(24, MAINTENANCE_PERIOD_H)
    wear_level = rng.uniform(0.0, 0.3)
    wear: list[float] = []
    failure_hours: list[int] = []
    downtime_end: list[int] = []
    maintenance_h: list[int] = []
    downtime = [False] * hours
    stopped_until = -1
    last_restart: int | None = None
    for h in range(hours):
        if h < stopped_until:
            downtime[h] = True
            wear.append(wear_level)
            continue
        if h >= next_maintenance:
            maintenance_h.append(h)
            wear_level = rng.uniform(0.0, 0.05)
            next_maintenance = (
                h + MAINTENANCE_PERIOD_H + rng.randint(-MAINTENANCE_JITTER_H, MAINTENANCE_JITTER_H)
            )
        wear_level += wear_rate * rng.uniform(0.5, 1.5)
        wear.append(wear_level)
        hazard = BASE_HAZARD + WEAR_HAZARD * wear_level
        if last_restart is not None:
            hazard += POST_REPAIR_HAZARD * math.exp(-(h - last_restart) / POST_REPAIR_DECAY_H)
        if rng.random() < hazard:
            failure_hours.append(h)
            repair = rng.randint(*DOWNTIME_RANGE_H)
            stopped_until = h + 1 + repair
            downtime_end.append(stopped_until)
            last_restart = stopped_until
            wear_level *= REPAIR_WEAR_FACTOR
    return wear, failure_hours, maintenance_h, downtime, downtime_end


def _ramp(onset: int, end: int, h: int) -> float:
    """Linear 0..1 ramp from ``onset`` (exclusive) to ``end`` (inclusive)."""
    if h <= onset or h > end:
        return 0.0
    return (h - onset) / (end - onset)


@lru_cache(maxsize=len(MACHINES))
def simulate_history(machine: str) -> FailureHistory:
    """Builds the deterministic simulated hourly history of one machine.

    Args:
        machine: Fictitious machine code, one of ``MACHINES``.

    Returns:
        The machine's ``FailureHistory`` over ``WEEKS`` weeks.

    Raises:
        ValueError: If the machine is unknown.
    """
    if machine not in MACHINES:
        raise ValueError(f"unknown machine: {machine}")
    rng = random.Random(f"{SEED}:{machine}")
    hours = TOTAL_HOURS
    wear, failure_hours, maintenance_h, downtime, downtime_end = _simulate_events(rng, hours)

    failures: list[FailureEvent] = []
    precursor = [0.0] * hours
    previous_restart = 0
    for index, f in enumerate(failure_hours):
        has_precursor = rng.random() < PRECURSOR_PROBABILITY
        lead = min(rng.randint(*LEAD_RANGE_H), f - previous_restart)
        if has_precursor and lead >= MIN_PRECURSOR_LEAD_H:
            onset = f - lead
            for h in range(onset + 1, f + 1):
                precursor[h] = max(precursor[h], _ramp(onset, f, h))
            failures.append(FailureEvent(hour=f, has_precursor=True, lead_h=lead))
        else:
            failures.append(FailureEvent(hour=f, has_precursor=False, lead_h=None))
        previous_restart = downtime_end[index]

    bump = [0.0] * hours
    for h in range(hours):
        if not downtime[h] and rng.random() < FALSE_BUMP_RATE_PER_H:
            duration = rng.randint(*FALSE_BUMP_DURATION_H)
            peak = rng.uniform(0.5, 0.9)
            for k in range(1, duration + 1):
                if h + k < hours:
                    # Triangular bump: rises then decays back to baseline.
                    shape = 1.0 - abs(2.0 * k / (duration + 1) - 1.0)
                    bump[h + k] = max(bump[h + k], peak * shape)

    vibration: list[float] = []
    current: list[float] = []
    alarms: list[int] = []
    for h in range(hours):
        excitation = 0.0 if downtime[h] else max(precursor[h], bump[h])
        vib = (
            VIBRATION_BASE_MM_S
            + VIBRATION_WEAR_GAIN * wear[h]
            + VIBRATION_RAMP * excitation
            + rng.gauss(0.0, VIBRATION_NOISE)
        )
        cur = CURRENT_BASE_A + CURRENT_WEAR_GAIN * wear[h] + CURRENT_RAMP * excitation
        cur += rng.gauss(0.0, CURRENT_NOISE)
        vib = max(vib, 0.1)
        rate = ALARM_BASE_RATE + ALARM_VIBRATION_GAIN * max(0.0, vib - VIBRATION_BASE_MM_S)
        vibration.append(round(vib, 3))
        current.append(round(cur, 2))
        alarms.append(0 if downtime[h] else _poisson(rng, rate))

    return FailureHistory(
        machine=machine,
        hours=hours,
        vibration=vibration,
        current=current,
        alarms=alarms,
        failures=failures,
        maintenance_h=maintenance_h,
        downtime=downtime,
    )
