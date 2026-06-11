"""SPEC §14 acceptance-criteria cross-check (Task 11.4).

A lightweight meta-test asserting the in-process-checkable v1 criteria are green. It is a
cross-check over the real code paths, NOT a re-implementation; criteria needing the
optional lifelib backend (differential / live novelty) use ``importorskip``.
"""

from __future__ import annotations

import pytest

from lifecore.campaign.campaign import Campaign
from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.capability import EngineId, capable_engines
from lifecore.targetspec.models import (
    Gun,
    Oscillator,
    Spaceship,
    StillLife,
    SymmetryClass,
)
from lifecore.verify import gate, verifier
from lifecore.verify.records import Verdict
from lifeseek_mcp.bridge import Bridge, CheckpointRequired, RelaxationError

GLIDER = "bob$2bo$3o!"
BLINKER = "3o!"
NOVEL = NoveltyResult(status=NoveltyStatus.NOVEL, apgcode="x")
UNCERTAIN = NoveltyResult(status=NoveltyStatus.UNCERTAIN)


def _glider_spec() -> Spaceship:
    return Spaceship(
        displacement=(1, 1),
        period=4,
        symmetry_class=SymmetryClass.GLIDE_REFLECT,
        search_width=(1, 5),
    )


# --- Criterion 1: golden PASS + adversarial REJECT + gate semantics ----------------
def test_criterion_1_suites_present() -> None:
    import tests.novelty.test_symmetry as symm
    import tests.sim.test_differential as diff
    import tests.verify.test_gate_adversarial as adv

    for mod in (diff, adv, symm):
        assert mod is not None


def test_criterion_1_gate_rejects_junk() -> None:
    junk = Pattern(frozenset({(0, 0), (5, 2), (2, 7), (9, 9)}))
    record = verifier.verify(junk, _glider_spec())
    assert record.verdict is Verdict.REJECT
    decision = gate.accept(record, NOVEL)
    assert decision.accepted is False


def test_criterion_1_gate_accepts_glider() -> None:
    record = verifier.verify(parse_rle(GLIDER), _glider_spec())
    assert record.verdict is Verdict.PASS
    assert gate.accept(record, NOVEL).accepted is True


def test_criterion_1_golden_blinker_p2() -> None:
    record = verifier.verify(parse_rle(BLINKER), Oscillator(period=2, bbox_max=(3, 3)))
    assert record.verdict is Verdict.PASS


# --- Criterion 2: capability map is honest (no false "not found") ------------------
def test_criterion_2_gun_has_no_capable_engine() -> None:
    assert capable_engines(Gun()) == []


def test_criterion_2_oblique_ship_routes_to_ikpx2() -> None:
    oblique = Spaceship(
        displacement=(2, 1),
        period=6,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(1, 5),
    )
    assert capable_engines(oblique) == [EngineId.IKPX2]


# --- Criterion 5: MCP immutability blocks the Strategist's relaxation --------------
def test_criterion_5_mcp_relaxation_attempt_raises() -> None:
    campaign = Campaign.create(_glider_spec())
    bridge = Bridge(campaign=campaign, novelty_fn=lambda _p: UNCERTAIN)

    with pytest.raises(RelaxationError):
        bridge.propose_search_params({"width": 99})  # beyond frozen w_max
    with pytest.raises(RelaxationError):
        bridge.propose_engine_policy(["lls"])  # not capable for a spaceship
    with pytest.raises(RelaxationError):
        bridge.record_result(parse_rle(GLIDER), claimed_novelty=NoveltyStatus.NOVEL)
    with pytest.raises(CheckpointRequired):
        bridge.retarget("never-approved")


# --- Criterion 7: re-aim (YAML edit) changes the spec_id --------------------------
def test_criterion_7_reaim_changes_spec_id() -> None:
    osc = Oscillator(period=2, bbox_max=(3, 3))
    still = StillLife(bbox_max=(4, 4))
    assert osc.spec_id != still.spec_id


# --- Criteria needing lifelib (differential / live novelty) -----------------------
def test_criterion_1_differential_needs_lifelib() -> None:
    pytest.importorskip("lifelib")
    from lifecore.sim import lifelib_engine, reference

    soup = parse_rle(GLIDER)
    ref = reference.step(soup, 4).normalize().cells
    lib = lifelib_engine.evolve(soup, 4).normalize().cells
    assert ref == lib
