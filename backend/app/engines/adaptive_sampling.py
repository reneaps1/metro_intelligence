"""EXPERIMENTAL (Thompson-Sampling adaptive inspection sampling frequency
recommender). Pure, deterministic-when-seeded (CLAUDE.md §3, §16, §22):
no DB/IO, no hidden global random state -- every call takes an explicit,
injectable `random.Random` and returns everything needed to audit the
result back to real numbers (never a black-box verdict). Stdlib only:
`random.Random.betavariate` for the Beta sampling, `statistics.fmean` for
the trend comparison -- no numpy/scipy, no new dependency.

Read-only and purely advisory (CLAUDE.md §2/§16/§22): this module never
writes anything and never overrides `app.engines.adaptive_inspection`, the
real rule-based Recommendation/Decision system. `ENGINE_VERSION`'s
"-experimental" suffix must never be dropped -- same convention as
`app.engines.experimental_ml.drift_cusum`.
"""

from __future__ import annotations

import random
import statistics
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

ENGINE_NAME = "adaptive_sampling_engine"
ENGINE_VERSION = "v1-experimental"

CpkTrend = Literal["stable", "improving", "declining"]

# Ascending: smaller number = more frequent inspection (tighter), larger
# number = sparser inspection. Must stay within [minimum_frequency,
# maximum_frequency] -- enforced by `_clamp` regardless of what a caller
# passes via AdaptiveSamplingConfig.
DEFAULT_FREQUENCY_BUCKETS: tuple[int, ...] = (5, 10, 20, 50, 100)

DEFAULT_CPK_THRESHOLD = Decimal("1.67")
DEFAULT_MINIMUM_FREQUENCY = 5
DEFAULT_MAXIMUM_FREQUENCY = 100
DEFAULT_MINIMUM_WINDOWS = 5
# How many of the most recent windows to analyze -- mirrors the
# MIN_HISTORY_FOR_FREQUENCY_DECREASE=20 / CAPABILITY_WINDOW_SIZE=20
# convention already used elsewhere in this codebase for "enough recent
# history to trust a signal".
DEFAULT_LOOKBACK_WINDOWS = 20

# Variance of Beta(1,1) -- the uniform prior with zero evidence, and the
# maximum variance among Beta(a,b) for a,b >= 1 (a,b are always >=1 here:
# a=successes+1, b=failures+1). Used to normalize confidence into [0,1];
# confidence rises toward 1 as evidence accumulates (more windows), and
# never depends on the random draw itself, only on successes/failures.
BETA_UNIFORM_VARIANCE = 1 / 12

# A Cpk change smaller than this across the two halves of the analyzed
# window series is noise, not a real trend. An absolute Cpk delta rather
# than a relative one, since Cpk itself is already a normalized,
# unit-free ratio.
DEFAULT_TREND_TOLERANCE = 0.1

CONSERVATIVE_LOW_CONFIDENCE = 0.0

CONFLICT_TIGHTENING_TYPES = {"frequency_increase", "immediate_inspection", "investigate_cause"}
CONFLICT_RELAXING_TYPES = {"frequency_decrease"}
# post_event_validation is deliberately NOT in either set -- see
# detect_conflicts' docstring for why it's treated as context, never a
# direction to auto-flag against.
ACTIVE_RECOMMENDATION_STATES = {"pending", "accepted"}


@dataclass(frozen=True)
class AdaptiveSamplingConfig:
    cpk_threshold: Decimal = DEFAULT_CPK_THRESHOLD
    minimum_frequency: int = DEFAULT_MINIMUM_FREQUENCY
    maximum_frequency: int = DEFAULT_MAXIMUM_FREQUENCY
    minimum_windows: int = DEFAULT_MINIMUM_WINDOWS
    lookback_windows: int = DEFAULT_LOOKBACK_WINDOWS
    frequency_buckets: tuple[int, ...] = DEFAULT_FREQUENCY_BUCKETS
    trend_tolerance: float = DEFAULT_TREND_TOLERANCE


@dataclass(frozen=True)
class AdaptiveSamplingResult:
    """Every intermediate is returned, not just the verdict (CLAUDE.md §16:
    no unexplainable black-box output) -- `successes`/`failures`/
    `beta_sample` let a human trace exactly how `recommended_frequency` was
    reached."""

    recommended_frequency: int
    confidence: float
    windows_analyzed: int
    successes: int
    failures: int
    beta_sample: float | None
    cpk_trend: CpkTrend
    rationale: str
    engine_name: str = ENGINE_NAME
    engine_version: str = ENGINE_VERSION


def classify_cpk_trend(cpk_values: list[Decimal], *, tolerance: float = DEFAULT_TREND_TOLERANCE) -> CpkTrend:
    """Splits the given (already-ordered, oldest-first) series in half and
    compares the mean of the earlier half to the mean of the recent half.
    Fewer than 2 values -> "stable" (nothing to compare)."""
    if len(cpk_values) < 2:
        return "stable"
    values = [float(v) for v in cpk_values]
    midpoint = len(values) // 2
    earlier_mean = statistics.fmean(values[:midpoint])
    recent_mean = statistics.fmean(values[midpoint:])
    delta = recent_mean - earlier_mean
    if delta > tolerance:
        return "improving"
    if delta < -tolerance:
        return "declining"
    return "stable"


def _clamp(value: int, *, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def recommend_sampling_frequency(
    cpk_values: Sequence[Decimal | None],
    *,
    config: AdaptiveSamplingConfig | None = None,
    rng: random.Random | None = None,
) -> AdaptiveSamplingResult:
    """Thompson Sampling over the last `config.lookback_windows` windows
    with a defined Cpk: success = Cpk > `config.cpk_threshold`, failure =
    Cpk <= threshold. Samples from Beta(successes+1, failures+1) via the
    injected `rng` (defaults to a fresh, unseeded `random.Random()` -- never
    the module-level `random` functions, so there is no shared global
    state between calls and callers can pass a seeded instance for
    deterministic tests).

    Fewer than `config.minimum_windows` valid windows -> conservative
    default (`minimum_frequency`, confidence 0.0), never raises.
    """
    cfg = config if config is not None else AdaptiveSamplingConfig()
    generator = rng if rng is not None else random.Random()

    valid_values = [v for v in cpk_values if v is not None]
    analyzed = valid_values[-cfg.lookback_windows :]
    windows_analyzed = len(analyzed)
    trend = classify_cpk_trend(analyzed, tolerance=cfg.trend_tolerance)

    if windows_analyzed < cfg.minimum_windows:
        return AdaptiveSamplingResult(
            recommended_frequency=cfg.minimum_frequency,
            confidence=CONSERVATIVE_LOW_CONFIDENCE,
            windows_analyzed=windows_analyzed,
            successes=0,
            failures=0,
            beta_sample=None,
            cpk_trend=trend,
            rationale=(
                f"Only {windows_analyzed} window(s) with a defined Cpk available "
                f"(minimum {cfg.minimum_windows} required) -- defaulting to the most "
                f"conservative frequency (every {cfg.minimum_frequency}th part) with low "
                "confidence until more history accumulates."
            ),
        )

    successes = sum(1 for v in analyzed if v > cfg.cpk_threshold)
    failures = windows_analyzed - successes
    alpha = successes + 1
    beta_param = failures + 1

    beta_sample = generator.betavariate(alpha, beta_param)
    bucket_count = len(cfg.frequency_buckets)
    bucket_index = min(int(beta_sample * bucket_count), bucket_count - 1)
    raw_frequency = cfg.frequency_buckets[bucket_index]
    recommended_frequency = _clamp(
        raw_frequency, minimum=cfg.minimum_frequency, maximum=cfg.maximum_frequency
    )

    variance = (alpha * beta_param) / (((alpha + beta_param) ** 2) * (alpha + beta_param + 1))
    confidence = max(0.0, min(1.0, 1 - (variance / BETA_UNIFORM_VARIANCE)))

    rationale = (
        f"Thompson Sampling over the last {windows_analyzed} windows: {successes} above the "
        f"Cpk {cfg.cpk_threshold} threshold, {failures} at or below it. "
        f"Beta({alpha},{beta_param}) sample={beta_sample:.3f} maps to a recommended sampling "
        f"frequency of every {recommended_frequency}th part (confidence {confidence:.2f})."
    )

    return AdaptiveSamplingResult(
        recommended_frequency=recommended_frequency,
        confidence=round(confidence, 4),
        windows_analyzed=windows_analyzed,
        successes=successes,
        failures=failures,
        beta_sample=beta_sample,
        cpk_trend=trend,
        rationale=rationale,
    )


# --- Conflict detection against the real rule-based Recommendation table ---


@dataclass(frozen=True)
class ExistingRecommendationSignal:
    """The subset of a real `Recommendation` row this comparator needs,
    decoupled from the ORM model -- same `RiskSignal` pattern as
    `app.engines.adaptive_inspection.recommend`."""

    id: uuid.UUID
    recommendation_type: str
    state: str
    rationale: str


@dataclass(frozen=True)
class RecommendationConflict:
    id: uuid.UUID
    type: str
    status: str
    title: str
    reason: str
    conflict_reason: str


def _short_title(recommendation_type: str, rationale: str) -> str:
    label = recommendation_type.replace("_", " ").capitalize()
    truncated = rationale if len(rationale) <= 140 else rationale[:137] + "..."
    return f"{label}: {truncated}"


def detect_conflicts(
    existing: list[ExistingRecommendationSignal],
    recommended_frequency: int,
    *,
    tight_frequency_threshold: int = DEFAULT_MINIMUM_FREQUENCY,
) -> list[RecommendationConflict]:
    """Pure, explainable, no-ML conflict rule (CLAUDE.md §3):

    - `rejected` rows never conflict -- "rejected no se trata como una
      instrucción activa" is explicit; a rejected recommendation carries no
      weight here at all (not even as inert context, since surfacing a
      dead-end recommendation next to a live experimental signal invites
      exactly the confusion CLAUDE.md §24 warns against -- state must
      always be visible and unambiguous).
    - `superseded`/`expired` rows never conflict -- terminal, inactive,
      same reasoning as `rejected`.
    - An *active* (`pending` or `accepted`) `frequency_increase`,
      `immediate_inspection`, or `investigate_cause` always conflicts: the
      rule-based system is actively asking for tighter/urgent inspection,
      while this experimental engine only ever proposes a routine periodic
      frequency -- any such proposal contradicts that urgency, regardless
      of how tight the proposed number is.
    - An active `frequency_decrease` conflicts only when the adaptive
      result is at the tightest configured frequency
      (`recommended_frequency <= tight_frequency_threshold`, default the
      engine's own `minimum_frequency`) -- the rule-based system wants to
      relax, the adaptive engine is signalling maximum caution instead.
    - `post_event_validation` is deliberately excluded from both conflict
      sets: "needs validation before anything else can be trusted" isn't a
      frequency directive in either direction, so auto-flagging it would be
      inferring a conflict from text/intent alone, not from the two
      systems actually disagreeing on a number -- surfaced as inert
      context by the caller instead (never returned here as a conflict).
    - Any `recommendation_type` outside the five known values is treated
      the same way -- informational-only, never auto-flagged (defensive
      for future types the DB CHECK constraint doesn't allow today but
      this comparator shouldn't crash on).
    - `accepted` produces a strictly stronger `conflict_reason` wording
      than `pending` (an accepted recommendation is a live human decision,
      not just an engine suggestion) -- both are reported in the same list;
      `status` on each entry always tells the caller which.

    No `severity` key on the returned conflicts: `Recommendation` has no
    real severity field in this schema (only `Alert.severity` exists) --
    inventing one here would present a fabricated field as if it were real
    data, which contradicts using only fields that actually exist. The
    `status`+`conflict_reason` wording already carries the "how serious"
    signal (accepted vs. pending) without a made-up enum.
    """
    conflicts: list[RecommendationConflict] = []
    for rec in existing:
        if rec.state not in ACTIVE_RECOMMENDATION_STATES:
            continue

        conflict_reason: str | None = None
        strength = "An already-accepted" if rec.state == "accepted" else "A pending"

        if rec.recommendation_type in CONFLICT_TIGHTENING_TYPES:
            conflict_reason = (
                f"{strength} '{rec.recommendation_type}' recommendation asks for tighter "
                f"inspection; this experimental engine is instead proposing a routine "
                f"frequency of every {recommended_frequency}th part, which contradicts "
                "that direction."
            )
        elif (
            rec.recommendation_type in CONFLICT_RELAXING_TYPES
            and recommended_frequency <= tight_frequency_threshold
        ):
            conflict_reason = (
                f"{strength} '{rec.recommendation_type}' recommendation asks to relax "
                f"inspection; this experimental engine is instead proposing an unusually "
                f"tight frequency of every {recommended_frequency}th part, which "
                "contradicts that direction."
            )

        if conflict_reason is None:
            continue

        conflicts.append(
            RecommendationConflict(
                id=rec.id,
                type=rec.recommendation_type,
                status=rec.state,
                title=_short_title(rec.recommendation_type, rec.rationale),
                reason=rec.rationale,
                conflict_reason=conflict_reason,
            )
        )
    return conflicts
