"""MDL / minimality tier tests (Task 4.3): reject derivative-of-known patterns."""

import ast
from pathlib import Path

from lifecore.novelty import mdl
from lifecore.novelty.canonical import independent_canonical
from lifecore.novelty.results import NoveltyStatus
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle

BLOCK = "2o$2o!"
BLINKER = "3o!"


def test_connected_components_splits_far_pieces() -> None:
    block = parse_rle(BLOCK)
    blinker_far = parse_rle(BLINKER).translate(50, 50)
    combo = Pattern(block.cells | blinker_far.cells)
    comps = mdl.connected_components(combo)
    assert len(comps) == 2
    assert sum(c.population for c in comps) == combo.population


def test_connected_components_single_for_touching() -> None:
    block = parse_rle(BLOCK)
    comps = mdl.connected_components(block)
    assert len(comps) == 1
    assert comps[0].population == block.population


def test_known_plus_far_blinker_is_DERIVATIVE() -> None:
    block = parse_rle(BLOCK)
    blinker_far = parse_rle(BLINKER).translate(50, 50)
    combo = Pattern(block.cells | blinker_far.cells)
    known = {independent_canonical(block), independent_canonical(parse_rle(BLINKER))}
    result = mdl.classify(combo, known)
    assert result.status == NoveltyStatus.DERIVATIVE
    assert result.nearest_known is not None
    assert result.mdl_delta is not None


def test_single_known_object_not_derivative() -> None:
    block = parse_rle(BLOCK)
    result = mdl.classify(block, {independent_canonical(block)})
    assert result.status == NoveltyStatus.NOVEL


def test_two_unknown_pieces_not_derivative() -> None:
    block = parse_rle(BLOCK)
    blinker_far = parse_rle(BLINKER).translate(50, 50)
    combo = Pattern(block.cells | blinker_far.cells)
    result = mdl.classify(combo, set())
    assert result.status == NoveltyStatus.NOVEL


def test_mdl_is_lifelib_free() -> None:
    tree = ast.parse(Path(mdl.__file__ or "").read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "lifelib" not in imported
