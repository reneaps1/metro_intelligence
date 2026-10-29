"""IQ-F7: HYPOTHETICAL what-if over the Vista B mechanism."""

from __future__ import annotations

import pytest
from app.engines.process_simulation.generator import build_timeline, nest_offsets
from app.engines.process_simulation.what_if import (
    PIECE_SD_MM,
    PRIMARY_MACHINE,
    WORN_NEST,
    WORN_OFFSET_MM,
    nok_probability_normal,
    what_if,
)


def test_normal_tail_against_hand_values() -> None:
    # Centred: |z| = 0.05 / 0.01 = 5 on both sides -> 2·(1 − Φ(5)) ≈ 5.7e-7.
    assert nok_probability_normal(12.0, 0.01) == pytest.approx(5.733e-7, rel=1e-3)
    # Mean exactly on the upper limit -> half of the pieces are out.
    assert nok_probability_normal(12.05, 0.01) == pytest.approx(0.5, abs=1e-6)


def test_mean_follows_the_imposed_formula() -> None:
    offsets = nest_offsets(PRIMARY_MACHINE)
    nest = 3
    r = what_if(580.0, 5.0, nest=nest)
    expected = 12.0 + 0.006 * 5.0 - 0.0006 * (580.0 - 620.0) + offsets[nest - 1]
    assert r.mean_mm == pytest.approx(expected)
    assert r.nok_probability == pytest.approx(nok_probability_normal(expected, PIECE_SD_MM))
    assert sum(c.mm for c in r.contributions) == pytest.approx(expected - 12.0)


def test_worn_insert_only_moves_its_nest() -> None:
    worn = what_if(620.0, 0.0, nest=WORN_NEST, worn_insert=True)
    healthy = what_if(620.0, 0.0, nest=WORN_NEST)
    assert worn.mean_mm - healthy.mean_mm == pytest.approx(WORN_OFFSET_MM)
    other = 1 if WORN_NEST != 1 else 2
    assert what_if(620.0, 0.0, nest=other, worn_insert=True).mean_mm == healthy.mean_mm - (
        nest_offsets(PRIMARY_MACHINE)[WORN_NEST - 1] - nest_offsets(PRIMARY_MACHINE)[other - 1]
    )


def test_all_nests_is_the_mixture_and_reference_is_nominal_settings() -> None:
    r = what_if(620.0, 8.0)
    each = [what_if(620.0, 8.0, nest=n).nok_probability for n in range(1, 13)]
    assert r.nok_probability == pytest.approx(sum(each) / 12)
    assert r.reference_nok_probability == pytest.approx(what_if(620.0, 0.0).nok_probability)
    assert r.nok_probability > 100 * r.reference_nok_probability
    assert [p.x for p in r.hold_sweep][:2] == [540.0, 550.0]
    assert len(r.mold_sweep) == 21


@pytest.mark.parametrize("args", [(530.0, 0.0), (620.0, 20.0), (620.0, 0.0, 13)])
def test_out_of_range_inputs_are_rejected(args: tuple) -> None:
    with pytest.raises(ValueError):
        what_if(*args)


def test_refactored_nest_offsets_keep_the_timeline() -> None:
    timeline = build_timeline("normal", PRIMARY_MACHINE)
    offsets = nest_offsets(PRIMARY_MACHINE)
    c = timeline.cycles[0]
    residual = c.dim_length - (
        12.0 + 0.006 * 0.0 - 0.0006 * (c.hold_pressure - 620.0) + offsets[c.cavity - 1]
    )
    # Only the measurement noise (σ = 0.007 mm) is left.
    assert abs(residual) < 0.035
