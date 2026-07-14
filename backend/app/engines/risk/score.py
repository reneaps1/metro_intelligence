"""F9.D (MI-46): composite, explainable risk score per characteristic.

Pure, deterministic engine function (CLAUDE.md §3, §16, §22): no DB access,
no ML ("ML enters only when data foundation justifies it" -- not yet), and
every factor that composes the score is returned alongside it with a
human-readable label and its numeric contribution, so a score is never a
black box (CLAUDE.md §16).

Scope decision (this task's Notion page, MI-46, was blank -- see
docs/tasks/F9.D.md): four factors for this first iteration --
- Historical NOK rate (recent results).
- Proximity to a tolerance limit (worst deviation in the window).
- Process capability (Cpk, from F8.D) -- optional input, since not every
  characteristic has enough data for a stable Cpk yet.
- Trend toward a limit (mean deviation of the second half of the window vs.
  the first half, only counted when it's moving *away* from nominal).

Explicitly deferred to a later iteration: correlating a risk increase with a
specific process_event (CLAUDE.md/roadmap: "demo shows first iteration" for
this engine). Each factor's weight is its maximum possible contribution;
they sum to 100 by construction, so the total score is always the sum of
its own factor contributions -- never a separate computation that could
drift out of sync with what's shown.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.engines.spc.capability import ToleranceSpec

ENGINE_NAME = "risk_engine"
ENGINE_VERSION = "v1"

NOK_RATE_WEIGHT = Decimal(40)
PROXIMITY_WEIGHT = Decimal(25)
CAPABILITY_WEIGHT = Decimal(20)
TREND_WEIGHT = Decimal(15)

CAPABLE_CPK_THRESHOLD = Decimal("1.33")

# Matches the thresholds already established in the F5.M mock frontend
# (frontend/src/lib/mock/fixtures.ts, levelFromScore) so the real engine and
# the existing demo screens agree on what "high"/"critical" mean.
CRITICAL_THRESHOLD = 80
HIGH_THRESHOLD = 60
MEDIUM_THRESHOLD = 35


@dataclass(frozen=True)
class ResultPoint:
    """One measurement result's contribution to the risk window. Callers
    pass points ordered by measured_at ascending (oldest first) -- the trend
    factor depends on that order and does not re-sort."""

    deviation: Decimal
    is_ok: bool


@dataclass(frozen=True)
class RiskFactor:
    label: str
    contribution: int


@dataclass(frozen=True)
class RiskAssessmentResult:
    score: int
    level: str
    factors: list[RiskFactor]
    engine_name: str
    engine_version: str


def _level_for(score: int) -> str:
    if score >= CRITICAL_THRESHOLD:
        return "critical"
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _nok_rate_factor(points: list[ResultPoint]) -> RiskFactor:
    nok_count = sum(1 for p in points if not p.is_ok)
    rate = Decimal(nok_count) / Decimal(len(points))
    contribution = round(rate * NOK_RATE_WEIGHT)
    return RiskFactor(label="Historical NOK rate", contribution=contribution)


def _proximity_ratio(deviation: Decimal, spec: ToleranceSpec) -> Decimal:
    ratios: list[Decimal] = []
    if spec.upper_tol is not None and spec.upper_tol != 0:
        ratios.append(deviation / spec.upper_tol)
    if spec.lower_tol is not None and spec.lower_tol != 0:
        ratios.append(deviation / spec.lower_tol)
    if not ratios:
        return Decimal(0)
    return max(Decimal(0), min(Decimal(1), max(ratios)))


def _proximity_factor(points: list[ResultPoint], spec: ToleranceSpec) -> RiskFactor:
    worst = max((_proximity_ratio(p.deviation, spec) for p in points), default=Decimal(0))
    contribution = round(worst * PROXIMITY_WEIGHT)
    return RiskFactor(label="Proximity to tolerance limit", contribution=contribution)


def _capability_factor(cpk: Decimal | None) -> RiskFactor:
    if cpk is None:
        return RiskFactor(label="Process capability (Cpk) -- insufficient data", contribution=0)
    shortfall = max(Decimal(0), CAPABLE_CPK_THRESHOLD - cpk) / CAPABLE_CPK_THRESHOLD
    shortfall = min(Decimal(1), shortfall)
    contribution = round(shortfall * CAPABILITY_WEIGHT)
    return RiskFactor(label="Process capability (low Cpk)", contribution=contribution)


def _trend_factor(points: list[ResultPoint], spec: ToleranceSpec) -> RiskFactor:
    if len(points) < 4:
        return RiskFactor(label="Trend toward limit -- insufficient data", contribution=0)

    midpoint = len(points) // 2
    first_half = points[:midpoint]
    second_half = points[midpoint:]
    first_mean = sum((p.deviation for p in first_half), start=Decimal(0)) / len(first_half)
    second_mean = sum((p.deviation for p in second_half), start=Decimal(0)) / len(second_half)

    # Only a move *away* from nominal counts as risk-increasing; moving back
    # toward nominal is an improving trend and contributes nothing.
    shift = abs(second_mean) - abs(first_mean)
    if shift <= 0:
        return RiskFactor(label="Trend toward limit", contribution=0)

    tolerance_sides = [abs(t) for t in (spec.lower_tol, spec.upper_tol) if t is not None]
    if not tolerance_sides:
        return RiskFactor(label="Trend toward limit", contribution=0)
    tolerance_scale = sum(tolerance_sides, start=Decimal(0)) / len(tolerance_sides)
    if tolerance_scale == 0:
        return RiskFactor(label="Trend toward limit", contribution=0)

    ratio = min(Decimal(1), shift / tolerance_scale)
    contribution = round(ratio * TREND_WEIGHT)
    return RiskFactor(label="Trend toward limit", contribution=contribution)


def score_characteristic(
    points: list[ResultPoint],
    spec: ToleranceSpec,
    *,
    cpk: Decimal | None = None,
) -> RiskAssessmentResult:
    if not points:
        raise ValueError("score_characteristic requires at least one result point.")

    factors = [
        _nok_rate_factor(points),
        _proximity_factor(points, spec),
        _capability_factor(cpk),
        _trend_factor(points, spec),
    ]
    score = max(0, min(100, sum(f.contribution for f in factors)))

    return RiskAssessmentResult(
        score=score,
        level=_level_for(score),
        factors=factors,
        engine_name=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
    )
