"""Contract tests for the universal closed-world verifier (Task 3.1)."""

import ast

from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.models import Spaceship, SymmetryClass
from lifecore.verify import verifier
from lifecore.verify.records import Verdict

GLIDER = "bob$2bo$3o!"


def c4_spec() -> Spaceship:
    return Spaceship(
        displacement=(1, 1),
        period=4,
        symmetry_class=SymmetryClass.GLIDE_REFLECT,
        search_width=(1, 5),
    )


def glider_plus_far_blinker() -> Pattern:
    glider = parse_rle(GLIDER)
    blinker = Pattern(frozenset({(100, 100), (101, 100), (102, 100)}))
    return Pattern(glider.cells | blinker.cells)


def test_glider_passes_as_c4_diagonal() -> None:
    rec = verifier.verify(parse_rle(GLIDER), c4_spec())
    assert rec.verdict == Verdict.PASS
    assert rec.residual_cell_count == 0
    assert rec.observed_period == 4
    assert rec.observed_displacement == (1, 1)
    assert rec.signature_valid()


def test_debris_leaker_rejected() -> None:
    rec = verifier.verify(glider_plus_far_blinker(), c4_spec())
    assert rec.verdict == Verdict.REJECT
    assert rec.residual_cell_count > 0


def test_wrong_period_rejected() -> None:
    spec = Spaceship(
        displacement=(1, 1),
        period=2,  # glider is really p4
        symmetry_class=SymmetryClass.GLIDE_REFLECT,
        search_width=(1, 5),
    )
    rec = verifier.verify(parse_rle(GLIDER), spec)
    assert rec.verdict == Verdict.REJECT


def test_wrong_displacement_rejected() -> None:
    spec = Spaceship(
        displacement=(2, 0),  # claim orthogonal c/2; glider is diagonal
        period=4,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(1, 5),
    )
    rec = verifier.verify(parse_rle(GLIDER), spec)
    assert rec.verdict == Verdict.REJECT


def test_junk_pattern_rejected() -> None:
    junk = Pattern(frozenset({(0, 0), (5, 2), (2, 7), (9, 9)}))
    rec = verifier.verify(junk, c4_spec())
    assert rec.verdict == Verdict.REJECT


def test_record_is_signed_and_immutable() -> None:
    import pytest

    rec = verifier.verify(parse_rle(GLIDER), c4_spec())
    assert rec.signature_valid()
    with pytest.raises((TypeError, ValueError, AttributeError)):
        rec.residual_cell_count = 99


def test_uses_reference_path_only() -> None:
    """AST guard: the verifier module must never import the producer backend."""
    from pathlib import Path

    tree = ast.parse(Path(verifier.__file__ or "").read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "lifelib" not in imported
