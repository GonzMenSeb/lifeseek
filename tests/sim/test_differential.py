"""Differential harness: numpy reference vs lifelib HashLife (Task 1.4, Phase-2 gate).

If the two *independent* simulators ever disagree on a random soup, one of them has a
bug — and since the verifier trusts the reference path, that is a hard failure. This
is the bedrock-of-trust test for the whole project (SPEC §14.1).
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

pytest.importorskip("lifelib", reason="differential harness needs the lifelib backend")

from lifecore.sim import lifelib_engine, reference
from lifecore.sim.pattern import Pattern


def random_soup(seed: int, k: int, rule: str = "B3/S23") -> Pattern:
    """A reproducible random k-by-k soup (~50% density) under ``rule``."""
    rng = np.random.default_rng(seed)
    mask = rng.integers(0, 2, size=(k, k), dtype=np.uint8)
    rows, cols = np.nonzero(mask)
    cells = frozenset((int(c), int(r)) for r, c in zip(rows, cols, strict=True))
    return Pattern(cells, rule)


@settings(max_examples=120, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=2**31),
    k=st.integers(min_value=4, max_value=12),
    t=st.integers(min_value=1, max_value=32),
)
def test_reference_matches_lifelib(seed: int, k: int, t: int) -> None:
    p = random_soup(seed, k, rule="B3/S23")
    ref_cells = reference.step(p, t).normalize().cells
    lif_cells = lifelib_engine.evolve(p, t).normalize().cells
    assert ref_cells == lif_cells


def test_known_objects_agree_long_horizon() -> None:
    # explicit non-random anchors over a longer horizon than hypothesis explores
    from lifecore.sim.rle import parse_rle

    for rle, horizon in (("bob$2bo$3o!", 100), ("3o!", 99), ("2o$2o!", 50)):
        p = parse_rle(rle)
        assert reference.step(p, horizon).normalize().cells == (
            lifelib_engine.evolve(p, horizon).normalize().cells
        )
