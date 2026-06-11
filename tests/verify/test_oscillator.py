"""Oscillator verification tests (Task 3.2) — rotor/stator + true period (no LCM)."""

from lifecore.sim import reference
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.models import Oscillator
from lifecore.verify import verifier
from lifecore.verify.records import Verdict

BLINKER = "3o!"
# Widely published pentadecathlon (p15) RLE.
PENTADECATHLON = "2bo4bo2b$2ob4ob2o$2bo4bo!"


def _min_period(p: Pattern, cap: int) -> int:
    for q in range(1, cap + 1):
        if reference.step(p, q).cells == p.cells:
            return q
    raise AssertionError("no period within cap")


def test_blinker_p2_passes() -> None:
    rec = verifier.verify(parse_rle(BLINKER), Oscillator(period=2, bbox_max=(3, 3)))
    assert rec.verdict == Verdict.PASS
    assert rec.observed_period == 2
    assert rec.rotor_cell_count and rec.rotor_cell_count > 0
    assert rec.stator_cell_count == 1  # the centre cell


def test_pentadecathlon_is_really_p15() -> None:
    # sanity-check the fixture before relying on it
    assert _min_period(parse_rle(PENTADECATHLON), 30) == 15


def test_blinker_wrong_period_rejected() -> None:
    rec = verifier.verify(parse_rle(BLINKER), Oscillator(period=4, bbox_max=(3, 3)))
    assert rec.verdict == Verdict.REJECT  # true minimal period is 2


def test_trivial_lcm_rejected() -> None:
    # blinker (p2) + far pentadecathlon (p15): the pattern returns at lcm=30, but NO
    # single cell oscillates at p30 and the components are separable -> REJECT.
    blinker = parse_rle(BLINKER)
    pent = parse_rle(PENTADECATHLON).translate(60, 60)
    combo = Pattern(blinker.cells | pent.cells)
    assert _min_period(combo, 40) == 30  # the trivial LCM
    rec = verifier.verify(combo, Oscillator(period=30, bbox_max=(80, 80)))
    assert rec.verdict == Verdict.REJECT
    assert "period" in rec.notes.lower()


def test_glider_is_not_an_oscillator() -> None:
    rec = verifier.verify(parse_rle("bob$2bo$3o!"), Oscillator(period=4, bbox_max=(5, 5)))
    assert rec.verdict == Verdict.REJECT  # it translates, never returns stationary
