"""Bitwise reproduce tests (Task 11.2, SPEC §14.6 — release blocker)."""

from __future__ import annotations

import pytest

from lifecore.campaign.reproduce import reproduce_discovery
from lifecore.campaign.runner import run_campaign
from lifecore.cli import discovery_artifact
from lifecore.novelty.oracle import novelty_query
from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.models import Oscillator

NOVEL = NoveltyResult(status=NoveltyStatus.NOVEL, apgcode="x")


def _run_and_build_artifact() -> dict[str, object]:
    spec = Oscillator(period=2, bbox_max=(3, 3))
    report = run_campaign(
        spec,
        candidate_source=[parse_rle("3o!")],
        novelty_fn=lambda p: NOVEL,
    )
    assert report.discoveries, "expected an accepted discovery"
    return discovery_artifact(spec, report.discoveries[0])


def test_reproduce_is_bitwise_identical() -> None:
    artifact = _run_and_build_artifact()
    result = reproduce_discovery(artifact, novelty_fn=lambda p: NOVEL)
    assert result.ok is True
    assert result.verification_match is True
    assert result.novelty_match is True
    assert result.recipe_match is True


def test_reproduce_detects_tampering() -> None:
    artifact = _run_and_build_artifact()
    # Tamper with a verification field; the stored signature no longer replays.
    artifact["verification"]["residual_cell_count"] = 999  # type: ignore[index]
    result = reproduce_discovery(artifact, novelty_fn=lambda p: NOVEL)
    assert result.ok is False
    assert result.verification_match is False


def test_reproduce_detects_signature_tampering() -> None:
    artifact = _run_and_build_artifact()
    artifact["verification"]["signature"] = "0" * 64  # type: ignore[index]
    result = reproduce_discovery(artifact, novelty_fn=lambda p: NOVEL)
    assert result.ok is False


def test_reproduce_real_pipeline() -> None:
    pytest.importorskip("lifelib")
    spec = Oscillator(period=2, bbox_max=(3, 3))
    report = run_campaign(
        spec,
        candidate_source=[parse_rle("3o!")],
        novelty_fn=novelty_query,
    )
    if not report.discoveries:
        pytest.skip("blinker not NOVEL against the live snapshot (expected KNOWN)")
    artifact = discovery_artifact(spec, report.discoveries[0])
    result = reproduce_discovery(artifact)
    assert result.ok is True
