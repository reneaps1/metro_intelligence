"""Phase 13 preview (docs/roadmap.md, CLAUDE.md §22): a two-sided CUSUM
(cumulative sum control chart) drift detector over a real Cpk-window series.

Pure engine function (CLAUDE.md §3): no DB/IO -- the caller loads the
windowed values (`app.services.drift_detection_service`). Deliberately a
classic, textbook statistical technique rather than a fitted/opaque model:
every intermediate (target, k, h, running S+/S-) is returned in `points`, so
a "drift detected" result is always auditable back to real numbers, never a
black box (CLAUDE.md §16). `ENGINE_VERSION`'s "-experimental" suffix must
never be dropped -- this engine is shadow-mode only (see
`app.services.drift_detection_service` and the Live Monitor UI block that
renders this): it never writes an Alert/Recommendation and never feeds any
other engine.

Self-starting/retrospective CUSUM: `target` and `stdev` are estimated from
the same `values` series being tested (there is no separately known
historical baseline for a characteristic yet) -- same sample-stdev
convention as `app.engines.spc.capability`. This means the detector is
looking for a shift *within* the given window, not against an
externally-fixed process target.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ENGINE_NAME = "cusum_drift_engine"
ENGINE_VERSION = "v1-experimental"  # never drop "-experimental": this engine is shadow-mode only.

MIN_POINTS = 8
DEFAULT_K_STDEVS = Decimal("0.5")
DEFAULT_H_STDEVS = Decimal("4.0")


@dataclass(frozen=True)
class CusumPoint:
    index: int
    value: Decimal
    cusum_high: Decimal
    cusum_low: Decimal


@dataclass(frozen=True)
class DriftDetectionResult:
    drift_detected: bool
    drift_direction: str | None  # "upward" | "downward" | None
    drift_index: int | None
    target: Decimal
    stdev: Decimal
    k: Decimal
    h: Decimal
    points: list[CusumPoint]
    rationale: str
    engine_name: str = ENGINE_NAME
    engine_version: str = ENGINE_VERSION


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, start=Decimal(0)) / len(values)


def _sample_stdev(values: list[Decimal], mean: Decimal) -> Decimal:
    variance = sum(((v - mean) ** 2 for v in values), start=Decimal(0)) / (len(values) - 1)
    return variance.sqrt()


def detect_cusum_drift(
    values: list[Decimal],
    *,
    k_stdevs: Decimal = DEFAULT_K_STDEVS,
    h_stdevs: Decimal = DEFAULT_H_STDEVS,
) -> DriftDetectionResult | None:
    """`None` when there are fewer than `MIN_POINTS` values, or when the
    series has zero variance (a decision threshold in "stdevs" is undefined
    when stdev is 0) -- nothing meaningful to say in either case, same
    convention as `summarizeCapabilityTrend`'s `insufficient_data`."""
    if len(values) < MIN_POINTS:
        return None

    target = _mean(values)
    stdev = _sample_stdev(values, target)
    if stdev == 0:
        return None

    k = k_stdevs * stdev
    h = h_stdevs * stdev

    points: list[CusumPoint] = []
    high = Decimal(0)
    low = Decimal(0)
    drift_index: int | None = None
    drift_direction: str | None = None

    for index, value in enumerate(values):
        high = max(Decimal(0), high + (value - target) - k)
        low = max(Decimal(0), low - (value - target) - k)
        points.append(CusumPoint(index=index, value=value, cusum_high=high, cusum_low=low))

        if drift_index is None and (high > h or low > h):
            drift_index = index
            drift_direction = "upward" if high > h else "downward"

    drift_detected = drift_index is not None
    if drift_detected:
        rationale = (
            f"CUSUM drift detected ({drift_direction}): cumulative deviation crossed the "
            f"decision threshold (h={h_stdevs}σ) at window {drift_index + 1} of {len(values)} "
            f"(target {target:.2f}, k={k_stdevs}σ, σ={stdev:.3f})."
        )
    else:
        rationale = (
            f"No sustained drift detected across {len(values)} windows (CUSUM stayed within the "
            f"±{h_stdevs}σ decision threshold; target {target:.2f}, k={k_stdevs}σ, σ={stdev:.3f})."
        )

    return DriftDetectionResult(
        drift_detected=drift_detected,
        drift_direction=drift_direction,
        drift_index=drift_index,
        target=target,
        stdev=stdev,
        k=k,
        h=h,
        points=points,
        rationale=rationale,
    )
