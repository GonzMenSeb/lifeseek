"""Adversarial immutability tests for the MCP bridge (Task 9.2) — RELEASE BLOCKER (SPEC §11)."""

import inspect

import pytest

from lifecore.campaign.campaign import Campaign
from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.models import Oscillator, Spaceship, StillLife, SymmetryClass
from lifeseek_mcp.bridge import Bridge, CheckpointRequired, RelaxationError


def ship_spec() -> Spaceship:
    return Spaceship(
        displacement=(1, 1),
        period=4,
        symmetry_class=SymmetryClass.GLIDE_REFLECT,
        search_width=(1, 5),
    )


def make_bridge(novelty: NoveltyStatus = NoveltyStatus.UNCERTAIN) -> Bridge:
    campaign = Campaign.create(ship_spec())
    return Bridge(campaign=campaign, novelty_fn=lambda _p: NoveltyResult(status=novelty))


# --- relaxation attempts must be blocked -----------------------------------------


def test_relaxation_attempt_blocked_width() -> None:
    bridge = make_bridge()
    # widen search width beyond the frozen w_max=5
    with pytest.raises(RelaxationError):
        bridge.propose_search_params({"width": 99})


def test_relaxation_attempt_blocked_tolerance_fields() -> None:
    bridge = make_bridge()
    for field in ("bbox_max", "population_range", "symmetry", "displacement", "period", "rule"):
        with pytest.raises(RelaxationError):
            bridge.propose_search_params({field: "whatever"})


def test_incapable_engine_policy_rejected() -> None:
    bridge = make_bridge()
    with pytest.raises(RelaxationError):
        bridge.propose_engine_policy(["lls"])  # LLS can't search a spaceship


def test_uncertain_cannot_be_recorded_as_novel() -> None:
    bridge = make_bridge(novelty=NoveltyStatus.UNCERTAIN)
    glider = parse_rle("bob$2bo$3o!")
    with pytest.raises(RelaxationError):
        bridge.record_result(glider, claimed_novelty=NoveltyStatus.NOVEL)


def test_known_cannot_be_recorded_as_novel() -> None:
    bridge = make_bridge(novelty=NoveltyStatus.KNOWN)
    glider = parse_rle("bob$2bo$3o!")
    with pytest.raises(RelaxationError):
        bridge.record_result(glider, claimed_novelty=NoveltyStatus.NOVEL)


# --- retarget requires a human checkpoint ----------------------------------------


def test_retarget_requires_human_checkpoint() -> None:
    bridge = make_bridge()
    new_spec = StillLife(bbox_max=(6, 6))
    ckpt = bridge.request_retarget_checkpoint(new_spec)
    # without approval, retarget is refused
    with pytest.raises(CheckpointRequired):
        bridge.retarget(ckpt)
    # an unknown checkpoint is also refused
    with pytest.raises(CheckpointRequired):
        bridge.retarget("ckpt-does-not-exist")
    # after human approval it succeeds and re-aims to the new frozen spec
    bridge.approve_checkpoint(ckpt)
    new_bridge = bridge.retarget(ckpt)
    assert new_bridge.campaign.spec.spec_id == new_spec.spec_id
    assert new_bridge.campaign.spec.spec_id != bridge.campaign.spec.spec_id


# --- structural: no setters on spec/gate/budget ----------------------------------


def test_bridge_has_no_setters() -> None:
    methods = [n for n, _ in inspect.getmembers(Bridge, inspect.isfunction)]
    forbidden = [m for m in methods if m.startswith(("set_", "widen", "relax", "override", "force"))]
    assert forbidden == []


def test_frozen_spec_not_mutated_by_bridge() -> None:
    bridge = make_bridge()
    spec = bridge.campaign.spec
    with pytest.raises((TypeError, ValueError, AttributeError)):
        spec.rule = "B36/S23"  # the spec the bridge holds is frozen


# --- happy paths still work ------------------------------------------------------


def test_valid_search_params_and_policy_accepted() -> None:
    bridge = make_bridge()
    assert bridge.propose_search_params({"width": 4}) == {"width": 4}
    assert bridge.propose_engine_policy(["qfind"]) == ["qfind"]


def test_record_result_matching_novelty_runs_gate() -> None:
    bridge = make_bridge(novelty=NoveltyStatus.NOVEL)
    glider = parse_rle("bob$2bo$3o!")
    decision = bridge.record_result(glider, claimed_novelty=NoveltyStatus.NOVEL)
    assert decision.accepted is True  # verified PASS + NOVEL


def test_oscillator_width_param_ignored_gracefully() -> None:
    # width is only meaningful for ships; for an oscillator campaign it's still tunable-keyed
    campaign = Campaign.create(Oscillator(period=2, bbox_max=(3, 3)))
    bridge = Bridge(campaign=campaign, novelty_fn=lambda _p: NoveltyResult(status=NoveltyStatus.NOVEL))
    assert bridge.propose_search_params({"seed": 7}) == {"seed": 7}
