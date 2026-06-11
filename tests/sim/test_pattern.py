"""Contract tests for the Pattern model + RLE I/O (Task 1.1, frozen for 1.2-1.4)."""

import pytest

from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle, to_rle

GLIDER = "bob$2bo$3o!"  # canonical glider RLE


def test_glider_roundtrip() -> None:
    p = parse_rle(GLIDER, rule="B3/S23")
    assert p.population == 5
    assert p.bbox == (0, 0, 2, 2)  # (xmin, ymin, xmax, ymax)
    assert parse_rle(to_rle(p)).cells == p.cells


def test_translate_and_eq() -> None:
    p = parse_rle(GLIDER)
    assert p.translate(10, -3).translate(-10, 3).cells == p.cells
    assert p.translate(0, 0) == p


def test_default_rule_is_life() -> None:
    assert parse_rle(GLIDER).rule == "B3/S23"


def test_pattern_is_immutable() -> None:
    p = parse_rle(GLIDER)
    with pytest.raises((AttributeError, TypeError)):
        p.rule = "B36/S23"  # type: ignore[misc]
    # cells is a frozenset -> no mutation API
    with pytest.raises(AttributeError):
        p.cells.add((9, 9))  # type: ignore[attr-defined]


def test_hash_and_equality_value_based() -> None:
    a = parse_rle(GLIDER)
    b = parse_rle(GLIDER)
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}  # usable as set/dict keys
    assert a != a.translate(1, 0)


def test_normalize_moves_to_origin() -> None:
    p = parse_rle(GLIDER).translate(37, -11)
    n = p.normalize()
    assert n.bbox[:2] == (0, 0)
    assert n.population == p.population
    # normalize is translation-invariant on the canonical form
    assert n == parse_rle(GLIDER).normalize()


def test_empty_pattern() -> None:
    e = Pattern(frozenset(), rule="B3/S23")
    assert e.population == 0
    assert e.is_empty
    assert e.normalize() == e
    # round-trips through RLE as an empty body
    assert parse_rle(to_rle(e)).population == 0


def test_rle_header_and_comments_parsed() -> None:
    text = "#N Glider\n#C a comment\nx = 3, y = 3, rule = B3/S23\nbob$2bo$3o!\n"
    p = parse_rle(text)
    assert p.population == 5
    assert p.rule == "B3/S23"


def test_rle_blank_rows_with_counts() -> None:
    # two blinkers stacked with a gap: row0 has a cell, two blank rows, row3 a cell
    p = parse_rle("o3$o!")
    assert p.cells == frozenset({(0, 0), (0, 3)})


def test_explicit_rule_overrides_header() -> None:
    text = "x = 1, y = 1, rule = B3/S23\no!"
    assert parse_rle(text, rule="B36/S23").rule == "B36/S23"


def test_width_height() -> None:
    p = parse_rle(GLIDER)
    assert p.width == 3 and p.height == 3
    assert Pattern(frozenset()).width == 0
