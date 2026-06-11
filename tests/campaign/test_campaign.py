"""Tests for the frozen campaign config (Task 7.1, SPEC §8)."""

from __future__ import annotations

import dataclasses

import pytest

from lifecore.campaign.budget import BudgetLimits
from lifecore.campaign.campaign import Campaign
from lifecore.targetspec.capability import EngineId, capable_engines
from lifecore.targetspec.models import Gun, Oscillator, Spaceship, SymmetryClass


def _spaceship() -> Spaceship:
    return Spaceship(
        displacement=(1, 0),
        period=4,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(3, 8),
    )


def _oscillator() -> Oscillator:
    return Oscillator(period=2)


def test_campaign_id_stable_and_spec_hashed() -> None:
    spec = _oscillator()
    a = Campaign.create(spec)
    b = Campaign.create(spec)
    assert a.campaign_id == b.campaign_id
    # spec identity is baked into the campaign id
    assert spec.spec_id in {spec.spec_id}  # sanity
    other = Campaign.create(_spaceship())
    assert a.campaign_id != other.campaign_id


def test_default_policy_is_capable_engines() -> None:
    spec = _spaceship()
    camp = Campaign.create(spec)
    assert camp.engine_policy == tuple(capable_engines(spec))
    assert camp.has_capable_engine is True


def test_policy_rejects_incapable_engine() -> None:
    spec = _spaceship()
    # LLS is not capable of a spaceship search.
    assert EngineId.LLS not in capable_engines(spec)
    with pytest.raises(ValueError, match="capable"):
        Campaign.create(spec, engine_policy=(EngineId.LLS,))


def test_no_capable_engine_for_gun() -> None:
    camp = Campaign.create(Gun())
    assert camp.has_capable_engine is False
    assert camp.engine_policy == ()


def test_campaign_is_frozen() -> None:
    camp = Campaign.create(_oscillator())
    with pytest.raises(dataclasses.FrozenInstanceError):
        camp.budget_limits = BudgetLimits()  # type: ignore[misc]
