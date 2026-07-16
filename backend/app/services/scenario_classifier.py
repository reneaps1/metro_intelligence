"""LM.3 (docs/tasks/LM3-live-monitor-presenter-controls.md): ranks
characteristics against the seed's 5 demo scenarios (`seed/config/
scenarios.yaml`) using their *real, already-computed* measurement history --
not a persisted seed-time label. `seed/generators/measurements.py` only ever
kept `scenario_by_characteristic_id` as an in-memory seeding artifact; it was
never written to any table or column, so there is nothing to query it from
at replay time (confirmed by inspection before writing this module -- see
this task's PR description).

Every score below is a simple, documented formula over real values (the real
Cpk from F8.D's engine, plus straightforward trend/variance/NOK-rate
statistics computed here) -- never a black box, never a re-implementation of
the SPC math itself (CLAUDE.md §16, §22). This is necessarily an
approximation: it ranks candidates by how much their *current statistical
behavior* resembles a scenario, not by which scenario generated them. A
characteristic seeded as "slow_drift" that happened to drift back to nominal
by the end of its history would not rank highly for "slow_drift" here --
arguably more honest than trusting a label the data no longer supports.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.spc.capability import ToleranceSpec, cpk
from app.models.catalog import Characteristic, Specification
from app.models.measurement import MeasurementResult

# Must match seed/config/scenarios.yaml's keys exactly (LM.3 scope: "no
# inventar escenarios nuevos").
SCENARIO_NAMES = ("stable_capable", "slow_drift", "shift_after_event", "high_variance", "outlier_nok")

MIN_POINTS_FOR_PROFILE = 4
DEFAULT_CANDIDATE_POOL_LIMIT = 200


@dataclass(frozen=True)
class ScenarioProfile:
    characteristic_id: uuid.UUID
    cpk: Decimal | None
    nok_rate: Decimal
    drift_score: Decimal  # signed: (mean of last third - mean of first third) / tolerance limit
    step_score: Decimal  # unsigned: largest jump between two contiguous halves / tolerance limit


def _tolerance_limit(spec: Specification) -> Decimal:
    # A spec always has at least one side (DB check constraint on
    # catalog_specifications) -- never both None.
    if spec.upper_tol is not None:
        return spec.upper_tol
    return abs(spec.lower_tol)  # type: ignore[arg-type]


def _thirds_mean(values: list[Decimal]) -> tuple[Decimal, Decimal]:
    third = max(len(values) // 3, 1)
    first, last = values[:third], values[-third:]
    return (
        sum(first, start=Decimal(0)) / len(first),
        sum(last, start=Decimal(0)) / len(last),
    )


def _biggest_step(values: list[Decimal]) -> Decimal:
    """Largest absolute jump between the mean before and after any of a few
    coarse split points (quarters) -- a deterministic proxy for "the process
    shifted partway through this window", distinct from `drift_score`'s
    gradual trend across the whole thing. Checking only quarter-points (not
    every possible split) keeps this cheap and its result easy to reason
    about."""
    n = len(values)
    if n < 4:
        return Decimal(0)
    biggest = Decimal(0)
    for split in (n // 4, n // 2, 3 * n // 4):
        if split < 1 or split >= n:
            continue
        before, after = values[:split], values[split:]
        jump = abs(
            sum(after, start=Decimal(0)) / len(after) - sum(before, start=Decimal(0)) / len(before)
        )
        biggest = max(biggest, jump)
    return biggest


def compute_profile(
    characteristic_id: uuid.UUID,
    values: list[Decimal],
    is_ok_flags: list[bool | None],
    spec: Specification,
) -> ScenarioProfile:
    """Pure -- no DB access. `is_ok_flags` accepts `None` (an unevaluated
    result) defensively, though the seed generator always sets it; `None`
    counts toward `nok_rate` the same as an explicit `False` rather than
    being silently assumed OK."""
    limit = _tolerance_limit(spec)
    nok_count = sum(1 for ok in is_ok_flags if ok is not True)
    nok_rate = Decimal(nok_count) / Decimal(len(is_ok_flags))

    first_mean, last_mean = _thirds_mean(values)
    drift_score = (last_mean - first_mean) / limit if limit != 0 else Decimal(0)
    step_score = _biggest_step(values) / limit if limit != 0 else Decimal(0)

    try:
        cpk_value: Decimal | None = cpk(
            values, ToleranceSpec(nominal=spec.nominal, lower_tol=spec.lower_tol, upper_tol=spec.upper_tol)
        )
    except ValueError:
        # Undefined for a unilateral spec with too little signal, or a
        # zero-variance run -- treat as "unknown", not "capable".
        cpk_value = None

    return ScenarioProfile(
        characteristic_id=characteristic_id,
        cpk=cpk_value,
        nok_rate=nok_rate,
        drift_score=drift_score,
        step_score=step_score,
    )


def _score_stable_capable(p: ScenarioProfile) -> Decimal:
    # scenarios.yaml: minimal noise, no drift/shift/outliers -> high Cpk,
    # near-zero drift/step, zero NOK.
    base_cpk = p.cpk if p.cpk is not None else Decimal(0)
    return base_cpk - abs(p.drift_score) * 5 - p.step_score * 5 - p.nok_rate * 10


def _score_slow_drift(p: ScenarioProfile) -> Decimal:
    # scenarios.yaml's drift_fraction: a gradual, sustained trend across the
    # whole window -- penalize a sudden step (that's shift_after_event) and
    # NOK noise (that's outlier_nok).
    return abs(p.drift_score) - p.step_score * Decimal("0.5") - p.nok_rate * 5


def _score_shift_after_event(p: ScenarioProfile) -> Decimal:
    # scenarios.yaml's shift_fraction after event_day_offset: a sudden level
    # change partway through, not a gradual trend across the whole window.
    return p.step_score - abs(p.drift_score) * Decimal("0.5") - p.nok_rate * 5


def _score_high_variance(p: ScenarioProfile) -> Decimal:
    # scenarios.yaml: noise_std_fraction_of_tolerance high -> low real Cpk.
    return -(p.cpk if p.cpk is not None else Decimal(10)) - p.nok_rate * 5


def _score_outlier_nok(p: ScenarioProfile) -> Decimal:
    # scenarios.yaml's nok_outlier_probability: elevated real NOK rate.
    return p.nok_rate


SCENARIO_SCORERS: dict[str, Callable[[ScenarioProfile], Decimal]] = {
    "stable_capable": _score_stable_capable,
    "slow_drift": _score_slow_drift,
    "shift_after_event": _score_shift_after_event,
    "high_variance": _score_high_variance,
    "outlier_nok": _score_outlier_nok,
}


def rank_by_scenario(profiles: list[ScenarioProfile], scenario: str, limit: int) -> list[uuid.UUID]:
    """Pure ranking over already-computed profiles -- the `limit`
    characteristic ids whose real, current behavior best matches `scenario`.
    Raises `KeyError` for an unknown scenario name; the API layer turns that
    into a 422, never a silent fallback to some default scenario."""
    scorer = SCENARIO_SCORERS[scenario]
    ranked = sorted(profiles, key=scorer, reverse=True)
    return [p.characteristic_id for p in ranked[:limit]]


def load_candidate_profiles(
    db: Session, *, pool_limit: int = DEFAULT_CANDIDATE_POOL_LIMIT
) -> list[ScenarioProfile]:
    """DB-backed candidate loader -- up to `pool_limit` characteristics with
    an active spec and enough history get a profile computed. Not pure
    (needs the DB); `compute_profile`/`rank_by_scenario` above are the pure,
    unit-testable core this wraps."""
    characteristics = db.execute(select(Characteristic).limit(pool_limit)).scalars().all()

    profiles: list[ScenarioProfile] = []
    for characteristic in characteristics:
        spec = db.execute(
            select(Specification).where(
                Specification.characteristic_id == characteristic.id,
                Specification.valid_to.is_(None),
            )
        ).scalar_one_or_none()
        if spec is None:
            continue

        rows = db.execute(
            select(MeasurementResult.value, MeasurementResult.is_ok)
            .where(MeasurementResult.characteristic_id == characteristic.id)
            .order_by(MeasurementResult.measured_at)
        ).all()
        if len(rows) < MIN_POINTS_FOR_PROFILE:
            continue

        values = [row.value for row in rows]
        is_ok_flags = [row.is_ok for row in rows]
        profiles.append(compute_profile(characteristic.id, values, is_ok_flags, spec))

    return profiles
