"""Step status rules (app/services/process_status.py): known input -> output."""

from __future__ import annotations

import pytest
from app.services.process_status import is_partial, rolled_yield, step_status


@pytest.mark.parametrize(
    ("pieces", "nok_rate", "cpk", "expected"),
    [
        (0, None, None, "neutral"),
        (100, 0.0, None, "ok"),
        (100, 0.0, 1.5, "ok"),
        (100, 0.005, None, "warning"),
        (100, 0.0, 1.2, "warning"),
        (100, 0.01, None, "critical"),
        (100, 0.0, 0.9, "critical"),
    ],
)
def test_step_status(pieces, nok_rate, cpk, expected):
    assert step_status(pieces, nok_rate, cpk) == expected


@pytest.mark.parametrize(
    ("coverage", "expected"),
    [(None, False), (0.0, True), (0.001, True), (0.49, True), (0.5, False), (1.0, False)],
)
def test_is_partial(coverage, expected):
    assert is_partial(coverage) is expected


def test_rolled_yield_is_the_product_of_the_pass_rates():
    assert rolled_yield([]) is None
    assert rolled_yield([0.0, 0.0]) == 1.0
    # 0.97 * 0.98 * 0.999 = 0.9496494
    assert rolled_yield([0.03, 0.02, 0.001]) == pytest.approx(0.9496494)
