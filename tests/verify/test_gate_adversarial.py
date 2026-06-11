"""Acceptance gate + adversarial golden suite (Task 3.4, release blocker)."""

import inspect

import pytest

from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.models import Oscillator, Spaceship, StillLife, SymmetryClass
from lifecore.verify import gate, verifier
from lifecore.verify.records import Verdict

GLIDER = "bob$2bo$3o!"
BLINKER = "3o!"
BLOCK = "2o$2o!"
PENTADECATHLON = "2bo4bo2b$2ob4ob2o$2bo4bo!"

NOVEL = NoveltyResult(status=NoveltyStatus.NOVEL, apgcode="x")
KNOWN = NoveltyResult(status=NoveltyStatus.KNOWN, apgcode="x")
UNCERTAIN = NoveltyResult(status=NoveltyStatus.UNCERTAIN)


def glider_spec() -> Spaceship:
    return Spaceship(
        displacement=(1, 1), period=4, symmetry_class=SymmetryClass.GLIDE_REFLECT, search_width=(1, 5)
    )


# --- adversarial REJECTs (verifier must reject all of these) ---------------------


def test_junk_rejected() -> None:
    junk = Pattern(frozenset({(0, 0), (5, 2), (2, 7), (9, 9)}))
    assert verifier.verify(junk, glider_spec()).verdict == Verdict.REJECT


def test_mislabeled_period_rejected() -> None:
    spec = Spaceship(
        displacement=(1, 1), period=3, symmetry_class=SymmetryClass.GLIDE_REFLECT, search_width=(1, 5)
    )
    assert verifier.verify(parse_rle(GLIDER), spec).verdict == Verdict.REJECT


def test_debris_leaker_rejected() -> None:
    glider = parse_rle(GLIDER)
    blinker = Pattern(frozenset({(100, 100), (101, 100), (102, 100)}))
    combo = Pattern(glider.cells | blinker.cells)
    assert verifier.verify(combo, glider_spec()).verdict == Verdict.REJECT


def test_trivial_lcm_oscillator_rejected() -> None:
    blinker = parse_rle(BLINKER)
    pent = parse_rle(PENTADECATHLON).translate(60, 60)
    combo = Pattern(blinker.cells | pent.cells)
    rec = verifier.verify(combo, Oscillator(period=30, bbox_max=(80, 80)))
    assert rec.verdict == Verdict.REJECT


# --- golden PASSes ---------------------------------------------------------------


def test_real_objects_pass_verification() -> None:
    assert verifier.verify(parse_rle(GLIDER), glider_spec()).verdict == Verdict.PASS
    assert verifier.verify(parse_rle(BLINKER), Oscillator(period=2, bbox_max=(3, 3))).verdict == Verdict.PASS
    assert verifier.verify(parse_rle(BLOCK), StillLife(bbox_max=(2, 2))).verdict == Verdict.PASS


# --- the gate: PASS ∧ NOVEL only -------------------------------------------------


def test_gate_accepts_only_verified_and_novel() -> None:
    rec = verifier.verify(parse_rle(GLIDER), glider_spec())
    assert gate.accept(rec, NOVEL).accepted is True
    assert gate.accept(rec, KNOWN).accepted is False  # re-derived known object
    assert gate.accept(rec, UNCERTAIN).accepted is False  # fail-closed


def test_gate_rejects_when_verification_fails() -> None:
    junk = Pattern(frozenset({(0, 0), (5, 2), (2, 7), (9, 9)}))
    rec = verifier.verify(junk, glider_spec())
    assert gate.accept(rec, NOVEL).accepted is False  # NOVEL can't rescue a failed verification


def test_gate_decision_is_frozen() -> None:
    rec = verifier.verify(parse_rle(GLIDER), glider_spec())
    decision = gate.accept(rec, NOVEL)
    with pytest.raises((AttributeError, TypeError, ValueError)):
        decision.accepted = False  # type: ignore[misc]


def test_gate_has_no_mutation_api() -> None:
    # the gate module exposes only the pure accept() + a frozen decision; no setters.
    public = [name for name in dir(gate) if not name.startswith("_")]
    for name in public:
        obj = getattr(gate, name)
        if inspect.isfunction(obj):
            assert not name.startswith(("set", "override", "widen", "relax", "force"))
    assert "accept" in public
