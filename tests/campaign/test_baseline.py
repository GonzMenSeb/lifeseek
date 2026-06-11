"""Tests for the mandatory baselines run through the same gate (Task 7.3, SPEC §8)."""

from __future__ import annotations

import itertools

from lifecore.campaign.baseline import (
    BaselineResult,
    iid_random_sampler,
    run_baseline,
    scs_sampler,
)
from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.pattern import Pattern
from lifecore.targetspec.models import Oscillator


def _blinker_spec() -> Oscillator:
    return Oscillator(period=2, bbox_max=(8, 8))


def _always_novel(_pattern: Pattern) -> NoveltyResult:
    return NoveltyResult(status=NoveltyStatus.NOVEL)


def _take(it: object, k: int) -> list[Pattern]:
    return list(itertools.islice(it, k))  # type: ignore[call-overload]


def test_iid_sampler_deterministic() -> None:
    spec = _blinker_spec()
    a = _take(iid_random_sampler(spec, seed=7), 5)
    b = _take(iid_random_sampler(spec, seed=7), 5)
    c = _take(iid_random_sampler(spec, seed=8), 5)
    assert [p.cells for p in a] == [p.cells for p in b]
    assert [p.cells for p in a] != [p.cells for p in c]


def test_scs_is_sequentially_conditioned() -> None:
    spec = _blinker_spec()
    stream = _take(scs_sampler(spec, seed=3), 6)
    # Reproducible.
    stream2 = _take(scs_sampler(spec, seed=3), 6)
    assert [p.cells for p in stream] == [p.cells for p in stream2]
    # Samples vary across the stream (not a constant).
    assert len({p.cells for p in stream}) > 1


def test_run_baseline_through_gate() -> None:
    spec = _blinker_spec()
    # A horizontal blinker (3 in a row) is a genuine period-2 oscillator.
    blinker = Pattern(frozenset({(0, 0), (1, 0), (2, 0)}), spec.rule)

    def blinker_stream() -> object:
        while True:
            yield blinker

    result = run_baseline(
        spec, blinker_stream(), n_attempts=4, novelty_fn=_always_novel  # type: ignore[arg-type]
    )
    assert isinstance(result, BaselineResult)
    assert result.attempts == 4
    # The real verifier confirms each blinker -> all accepted.
    assert result.discoveries == 4
    assert result.discovery_rate == 1.0


def test_run_baseline_random_rarely_meets_spec() -> None:
    spec = _blinker_spec()
    result = run_baseline(
        spec, iid_random_sampler(spec, seed=11), n_attempts=20, novelty_fn=_always_novel
    )
    assert result.attempts == 20
    assert 0 <= result.discoveries <= result.attempts
    assert result.discovery_rate == result.discoveries / result.attempts


def test_equal_budget_same_attempts() -> None:
    spec = _blinker_spec()
    n = 15
    iid = run_baseline(spec, iid_random_sampler(spec, seed=1), n_attempts=n, novelty_fn=_always_novel)
    scs = run_baseline(spec, scs_sampler(spec, seed=1), n_attempts=n, novelty_fn=_always_novel)
    assert iid.attempts == scs.attempts == n
