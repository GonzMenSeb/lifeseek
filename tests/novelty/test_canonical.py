"""Canonicalization tests (Task 4.1): apgcode + independent lifelib-free cross-check."""

import ast
from pathlib import Path

import pytest

from lifecore.novelty import canonical
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle

GLIDER = "bob$2bo$3o!"
BLINKER = "3o!"
BLOCK = "2o$2o!"


def _d8(p: Pattern) -> list[Pattern]:
    return list(canonical.dihedral_images(p))


# --- independent (lifelib-free) canonicalizer ------------------------------------


def test_independent_canonical_is_phase_and_d8_invariant() -> None:
    g = parse_rle(GLIDER)
    base = canonical.independent_canonical(g)
    # invariant under translation, all 8 dihedral images, and phase advance
    assert canonical.independent_canonical(g.translate(13, -7)) == base
    for image in _d8(g):
        assert canonical.independent_canonical(image) == base
    from lifecore.sim import reference

    for i in range(1, 4):
        assert canonical.independent_canonical(reference.step(g, i)) == base


def test_independent_canonical_distinguishes_objects() -> None:
    keys = {
        canonical.independent_canonical(parse_rle(rle))
        for rle in (GLIDER, BLINKER, BLOCK)
    }
    assert len(keys) == 3  # three distinct objects -> three distinct keys


def test_independent_canonical_is_lifelib_free() -> None:
    tree = ast.parse(Path(canonical.__file__ or "").read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    # the independent cross-check path must not depend on the producer backend
    assert "lifelib" not in imported


# --- apgcode (lifelib) + agreement with the independent partition ----------------


def test_apgcode_known_objects() -> None:
    pytest.importorskip("lifelib")
    assert canonical.apgcode(parse_rle(GLIDER)) == "xq4_153"
    assert canonical.apgcode(parse_rle(BLINKER)) == "xp2_7"
    assert canonical.apgcode(parse_rle(BLOCK)) == "xs4_33"  # lifelib truth (docs said xs4_252)


def test_independent_partition_agrees_with_apgcode() -> None:
    pytest.importorskip("lifelib")
    objs = [parse_rle(GLIDER), parse_rle(BLINKER), parse_rle(BLOCK)]
    by_apg = {canonical.apgcode(o) for o in objs}
    by_indep = {canonical.independent_canonical(o) for o in objs}
    # both canonicalizers separate the three objects identically
    assert len(by_apg) == len(by_indep) == 3
