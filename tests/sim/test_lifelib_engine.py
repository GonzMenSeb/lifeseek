"""Tests for the lifelib HashLife backend wrapper (Task 1.3). Skipped if lifelib absent."""

import pytest

pytest.importorskip("lifelib", reason="python-lifelib (optional 'lifelib' extra) not installed")

from lifecore.sim import lifelib_engine, reference
from lifecore.sim.rle import parse_rle

GLIDER = "bob$2bo$3o!"
BLINKER = "3o!"
BLOCK = "2o$2o!"


def test_evolve_matches_reference_glider() -> None:
    g = parse_rle(GLIDER)
    for n in (1, 2, 3, 4, 8):
        assert lifelib_engine.evolve(g, n).cells == reference.step(g, n).cells


def test_evolve_matches_reference_blinker() -> None:
    b = parse_rle(BLINKER)
    for n in (1, 2, 3):
        assert lifelib_engine.evolve(b, n).cells == reference.step(b, n).cells


def test_apgcode_known_objects() -> None:
    assert lifelib_engine.apgcode(parse_rle(GLIDER)) == "xq4_153"
    assert lifelib_engine.apgcode(parse_rle(BLINKER)) == "xp2_7"
    # NOTE: lifelib (authoritative) gives the 2x2 block as xs4_33, not the docs' xs4_252.
    assert lifelib_engine.apgcode(parse_rle(BLOCK)) == "xs4_33"


def test_apgcode_translation_invariant() -> None:
    g = parse_rle(GLIDER)
    assert lifelib_engine.apgcode(g) == lifelib_engine.apgcode(g.translate(57, -13))


def test_fast_forward_hashlife() -> None:
    g = parse_rle(GLIDER)
    far = lifelib_engine.fast_forward(g, 4000)
    assert far.population == 5
    assert far.cells == g.translate(1000, 1000).cells  # c/4 diagonal * 1000


def test_evolve_zero_identity() -> None:
    g = parse_rle(GLIDER)
    assert lifelib_engine.evolve(g, 0).cells == g.cells
