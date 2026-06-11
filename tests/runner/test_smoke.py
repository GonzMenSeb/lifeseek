"""Smoke test for the (LATER) unattended runner stub (Phase 12)."""

import pytest

from lifecore.campaign.campaign import Campaign
from lifecore.targetspec.models import Spaceship, SymmetryClass
from lifeseek_mcp.bridge import Bridge
from lifeseek_runner import CheckpointQueue, UnattendedRunner


def _bridge() -> Bridge:
    spec = Spaceship(
        displacement=(1, 1), period=4, symmetry_class=SymmetryClass.GLIDE_REFLECT, search_width=(1, 5)
    )
    return Bridge(campaign=Campaign.create(spec))


def test_runner_interface_exists() -> None:
    runner = UnattendedRunner(bridge=_bridge())
    assert isinstance(runner.checkpoints, CheckpointQueue)
    # v1: the autonomous loop is LATER and must not silently no-op
    with pytest.raises(NotImplementedError):
        runner.run()


def test_checkpoint_queue_tracks_approvals() -> None:
    q = CheckpointQueue()
    q.enqueue("ckpt-1")
    assert q.pending() == ["ckpt-1"]
    assert not q.is_approved("ckpt-1")
    q.approve("ckpt-1")
    assert q.is_approved("ckpt-1")
    assert q.pending() == []
