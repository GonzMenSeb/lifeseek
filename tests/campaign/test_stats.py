"""Tests for confidence intervals + discovery-time correction (Task 7.4, SPEC §8)."""

from __future__ import annotations

import pytest

from lifecore.campaign.stats import (
    evalue_threshold,
    proportion_point_estimate,
    range_target_strictly_inside,
    wilson_ci,
)


def test_wilson_ci_contains_estimate() -> None:
    for successes, n in [(0, 10), (5, 10), (10, 10), (3, 100), (1, 7)]:
        lo, hi = wilson_ci(successes, n)
        p_hat = proportion_point_estimate(successes, n)
        assert 0.0 <= lo <= p_hat <= hi <= 1.0


def test_wilson_ci_n_zero() -> None:
    assert wilson_ci(0, 0) == (0.0, 1.0)


def test_evalue_threshold_decreases_with_queries() -> None:
    t1 = evalue_threshold(1)
    t10 = evalue_threshold(10)
    t100 = evalue_threshold(100)
    assert t1 > t10 > t100
    # never blows up at zero queries
    assert evalue_threshold(0) == pytest.approx(evalue_threshold(1))


def test_range_target_must_be_strictly_inside() -> None:
    assert range_target_strictly_inside(5.0, 1.0, 10.0) is True
    # boundary -> False (strict)
    assert range_target_strictly_inside(1.0, 1.0, 10.0) is False
    assert range_target_strictly_inside(10.0, 1.0, 10.0) is False
    # outside -> False
    assert range_target_strictly_inside(0.5, 1.0, 10.0) is False
    assert range_target_strictly_inside(11.0, 1.0, 10.0) is False
