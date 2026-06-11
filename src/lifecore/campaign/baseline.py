"""Mandatory baselines run through the SAME gate (Task 7.3, SPEC §8).

Honest evaluation requires control arms. Two are mandated:

* **IID-random sampling** — independent random soups, the dumbest possible search.
* **Sequential-conditioned sampling (SCS)** — a Markov-ish chain where each draw is
  derived from the previous one (evolve one generation, then re-randomize a fraction of
  cells). Distinct from IID because each sample is *conditioned on its predecessor*.

Both are driven through the exact same :func:`lifecore.verify.verifier.verify` +
:func:`lifecore.verify.gate.accept` path at equal budget (``n_attempts``), so the real
campaign's discovery rate can be compared against them on equal footing.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import numpy as np

from lifecore.novelty.results import NoveltyResult
from lifecore.sim import reference
from lifecore.sim.pattern import Pattern
from lifecore.targetspec.models import TargetSpec
from lifecore.verify import gate
from lifecore.verify.verifier import verify

_DEFAULT_BOX = (8, 8)


def _spec_box(spec: TargetSpec) -> tuple[int, int]:
    bbox_max = getattr(spec, "bbox_max", None)
    if bbox_max is not None:
        w, h = bbox_max
        return (max(1, int(w)), max(1, int(h)))
    return _DEFAULT_BOX


def _soup(rng: np.random.Generator, width: int, height: int, density: float, rule: str) -> Pattern:
    """A random Pattern: each cell live with probability ``density``, within the box."""
    mask = rng.random((height, width)) < density
    rows, cols = np.nonzero(mask)
    cells = frozenset((int(c), int(r)) for r, c in zip(cols, rows, strict=True))
    return Pattern(cells, rule)


def iid_random_sampler(
    spec: TargetSpec, *, seed: int, density: float = 0.5
) -> Iterator[Pattern]:
    """Infinite stream of independent random soups sized to the spec's box.

    Deterministic given ``seed``: every draw is an *independent* Bernoulli soup, with no
    dependence on the previous sample.
    """
    width, height = _spec_box(spec)
    rng = np.random.default_rng(seed)
    while True:
        yield _soup(rng, width, height, density, spec.rule)


def scs_sampler(spec: TargetSpec, *, seed: int) -> Iterator[Pattern]:
    """Infinite Sequential-Conditioned stream: each sample depends on the previous.

    Start from a random soup; each step evolve the current sample one generation with the
    reference simulator and re-randomize a fraction of the cells inside the box. This makes
    the stream a reproducible Markov chain conditioned on its own history — explicitly
    distinct from the IID baseline. Deterministic given ``seed``.
    """
    width, height = _spec_box(spec)
    rng = np.random.default_rng(seed)
    mutate_fraction = 0.25
    current = _soup(rng, width, height, 0.5, spec.rule)
    while True:
        yield current
        # Condition the next draw on the current one: evolve, then perturb.
        evolved = reference.step(current, 1).normalize()
        live = set(evolved.cells)
        flips = rng.random((height, width)) < mutate_fraction
        rows, cols = np.nonzero(flips)
        for r, c in zip(rows, cols, strict=True):
            cell = (int(c), int(r))
            if cell in live:
                live.discard(cell)
            else:
                live.add(cell)
        current = Pattern(frozenset(live), spec.rule)


@dataclass(frozen=True)
class BaselineResult:
    """Outcome of a baseline run: attempts, gate-accepted discoveries, and the rate."""

    name: str
    attempts: int
    discoveries: int
    discovery_rate: float


def run_baseline(
    spec: TargetSpec,
    sampler: Iterator[Pattern],
    *,
    n_attempts: int,
    novelty_fn: Callable[[Pattern], NoveltyResult],
    name: str = "baseline",
) -> BaselineResult:
    """Draw ``n_attempts`` patterns and push each through the real verifier + gate.

    A pattern counts as a discovery iff :func:`gate.accept` accepts it (verified PASS and
    novelty NOVEL). ``novelty_fn`` is injected so callers control the novelty oracle.
    """
    discoveries = 0
    attempts = 0
    for pattern in sampler:
        if attempts >= n_attempts:
            break
        attempts += 1
        record = verify(pattern, spec)
        decision = gate.accept(record, novelty_fn(pattern))
        if decision.accepted:
            discoveries += 1
    rate = discoveries / attempts if attempts else 0.0
    return BaselineResult(
        name=name, attempts=attempts, discoveries=discoveries, discovery_rate=rate
    )
