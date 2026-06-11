"""Tests for the independent NumPy reference simulator (Task 1.2, verifier path)."""

from lifecore.sim import reference
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle


def test_no_lifelib_import() -> None:
    """The verifier trust path must never depend on the producer backend (AST-checked)."""
    import ast

    import lifecore.sim.reference as ref

    with open(ref.__file__ or "") as fh:
        tree = ast.parse(fh.read())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "lifelib" not in imported


def test_blinker_period_2() -> None:
    blinker = parse_rle("3o!")
    one = reference.step(blinker, 1)
    assert one.cells != blinker.cells  # phase 1 differs
    two = reference.step(blinker, 2)
    assert two.cells == blinker.cells  # true p2, stationary


def test_block_still_life() -> None:
    block = parse_rle("2o$2o!")
    for n in (1, 2, 5, 17):
        assert reference.step(block, n).cells == block.cells


def test_glider_moves_1_1_per_4() -> None:
    glider = parse_rle("bob$2bo$3o!")
    moved = reference.step(glider, 4)
    assert moved.cells == glider.translate(1, 1).cells


def test_step_zero_is_identity() -> None:
    p = parse_rle("bob$2bo$3o!")
    assert reference.step(p, 0).cells == p.cells


def test_grid_autoexpands_no_clipping() -> None:
    # a glider run far enough that a fixed small grid would clip it
    glider = parse_rle("bob$2bo$3o!")
    moved = reference.step(glider, 40)
    assert moved.population == 5
    assert moved.cells == glider.translate(10, 10).cells  # 40/4 = 10 diagonal steps


def test_rule_param_highlife_differs() -> None:
    # center (0,0) has exactly 6 live neighbours -> born under B36/S23, not B3/S23
    cells = frozenset({(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1)})
    life = reference.step(Pattern(cells, rule="B3/S23"), 1)
    highlife = reference.step(Pattern(cells, rule="B36/S23"), 1)
    assert (0, 0) not in life.cells
    assert (0, 0) in highlife.cells


def test_result_carries_rule() -> None:
    p = parse_rle("3o!", rule="B36/S23")
    assert reference.step(p, 1).rule == "B36/S23"
