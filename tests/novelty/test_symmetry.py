"""Symmetry soundness suite (Task 4.4) — RELEASE BLOCKER (SPEC §6.1, §14.1)."""

import pytest

pytest.importorskip("lifelib", reason="symmetry soundness needs the apgcode canonicalizer")

from lifecore.novelty import symmetry_suite
from lifecore.novelty.canonical import apgcode
from lifecore.novelty.catagolue import load_snapshot
from lifecore.sim.rle import parse_rle

# (expected apgcode, RLE) for catalog objects covering ship / oscillator / still-life.
CATALOG = {
    "xq4_153": "bob$2bo$3o!",  # glider (ship)
    "xp2_7": "3o!",  # blinker (oscillator)
    "xs4_33": "2o$2o!",  # block (still life)
}


def test_each_catalog_object_canonicalizes_to_single_apgcode() -> None:
    for expected, rle in CATALOG.items():
        p = parse_rle(rle)
        codes = symmetry_suite.apgcodes_for_orbit(p, n_phases=4, n_translations=5, seed=17)
        # every D8 image x phase x translation collapses to the one expected apgcode
        assert codes == {expected}, f"{rle}: orbit produced {codes}, expected {{{expected}}}"


def test_known_objects_flagged_known() -> None:
    census, _ = load_snapshot()
    for rle in ("bob$2bo$3o!", "3o!", "2o$2o!"):
        assert apgcode(parse_rle(rle)) in census  # flagged KNOWN by the frozen snapshot


def test_is_symmetry_sound_true_for_glider() -> None:
    assert symmetry_suite.is_symmetry_sound(parse_rle("bob$2bo$3o!"), n_phases=4, n_translations=3)
