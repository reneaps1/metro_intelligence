"""Phase 13 preview: pure-function vectors (CLAUDE.md §11) for
``app.engines.experimental_ml.drift_cusum``. Hand-calculated where the
result depends on exact arithmetic; see
``test_drift_detection_service.py`` for the DB-backed wiring against seeded
patterns."""

from __future__ import annotations

from decimal import Decimal

from app.engines.experimental_ml.drift_cusum import MIN_POINTS, detect_cusum_drift


def test_none_when_fewer_than_min_points() -> None:
    values = [Decimal("1.5")] * (MIN_POINTS - 1)
    assert detect_cusum_drift(values) is None


def test_none_when_series_has_zero_variance() -> None:
    values = [Decimal("1.5")] * (MIN_POINTS + 2)
    assert detect_cusum_drift(values) is None


def test_no_drift_for_a_stable_oscillating_series() -> None:
    # Symmetric +/-0.01 oscillation around a mean of 1.50 -- deviations
    # cancel out, cumulative sums never approach the 4-sigma threshold.
    values = [
        Decimal("1.50"),
        Decimal("1.51"),
        Decimal("1.49"),
        Decimal("1.50"),
        Decimal("1.51"),
        Decimal("1.49"),
        Decimal("1.50"),
        Decimal("1.51"),
        Decimal("1.49"),
        Decimal("1.50"),
    ]
    result = detect_cusum_drift(values)
    assert result is not None
    assert result.drift_detected is False
    assert result.drift_direction is None
    assert result.drift_index is None
    assert result.target == Decimal("1.50")


def test_drift_detected_for_a_sustained_level_shift() -> None:
    # A clean two-level step: 10 points at 1.00, then 10 points at 2.00.
    # Hand-calculated: target=1.50, sample stdev=sqrt(5/19)=0.512932...,
    # k=0.5*stdev=0.256466, h=4*stdev=2.051728. The low-side cumulative sum
    # (points below the grand mean) crosses h at index 8 -- within the
    # *first* (lower) segment, before the shift even starts. This is
    # expected/correct behavior for a self-starting CUSUM computed against
    # the whole series' own mean (CLAUDE.md §16: this asymmetry is exactly
    # why every intermediate is returned in `points`, auditable rather than
    # a bare verdict) -- it's detecting "a sustained level below the overall
    # mean", not localizing the exact transition point.
    values = [Decimal("1.00")] * 10 + [Decimal("2.00")] * 10
    result = detect_cusum_drift(values)
    assert result is not None
    assert result.drift_detected is True
    assert result.drift_direction == "downward"
    assert result.drift_index == 8
    assert result.target == Decimal("1.50")


def test_rationale_mentions_direction_and_engine_attribution() -> None:
    values = [Decimal("1.00")] * 10 + [Decimal("2.00")] * 10
    result = detect_cusum_drift(values)
    assert result is not None
    assert "downward" in result.rationale
    assert "CUSUM" in result.rationale
    assert result.engine_name == "cusum_drift_engine"
    assert result.engine_version == "v1-experimental"


def test_points_are_returned_for_every_input_value() -> None:
    values = [Decimal("1.00")] * 10 + [Decimal("2.00")] * 10
    result = detect_cusum_drift(values)
    assert result is not None
    assert len(result.points) == len(values)
    assert [p.index for p in result.points] == list(range(len(values)))
