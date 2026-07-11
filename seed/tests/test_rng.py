from __future__ import annotations

import numpy as np

from seed.generators import make_rng


def test_same_seed_produces_identical_sequences() -> None:
    a = make_rng(20260709).standard_normal(50)
    b = make_rng(20260709).standard_normal(50)
    assert np.array_equal(a, b)


def test_different_seeds_produce_different_sequences() -> None:
    a = make_rng(1).standard_normal(50)
    b = make_rng(2).standard_normal(50)
    assert not np.array_equal(a, b)
