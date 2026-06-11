"""Tests for the rlifesrc backtracking adapter (Task 6.4)."""

from __future__ import annotations

import shutil

import pytest

from lifecore.engines import rlifesrc as rls_mod
from lifecore.engines.base import EngineBudget, EngineOutcome, NoCapability, RawResult
from lifecore.engines.rlifesrc import RlifesrcAdapter
from lifecore.sandbox.runner import SandboxResult
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import Gun, Oscillator, Spaceship, StillLife, SymmetryClass

GLIDER_RLE = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!\n"


def _osc() -> Oscillator:
    return Oscillator(period=3, bbox_max=(8, 8))


def _still() -> StillLife:
    return StillLife(bbox_max=(6, 6), symmetry=SymmetryClass.ASYMMETRIC)


def _ship() -> Spaceship:
    return Spaceship(
        displacement=(0, 1),
        period=4,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(3, 9),
    )


def _patch_present(monkeypatch: pytest.MonkeyPatch, result: SandboxResult) -> None:
    monkeypatch.setattr(rls_mod.shutil, "which", lambda _: "/usr/bin/rlifesrc")
    monkeypatch.setattr(rls_mod, "sandbox_available", lambda: True)
    monkeypatch.setattr(rls_mod, "run_sandboxed", lambda *a, **k: result)


def test_id_and_capabilities() -> None:
    a = RlifesrcAdapter()
    assert a.id is EngineId.RLIFESRC
    assert a.capabilities().engine_id is EngineId.RLIFESRC


def test_build_input_oscillator() -> None:
    cfg = RlifesrcAdapter().build_input(_osc(), EngineBudget())
    assert "rlifesrc" in cfg.argv[0]
    assert "3" in " ".join(cfg.argv)  # period


def test_build_input_still_life() -> None:
    cfg = RlifesrcAdapter().build_input(_still(), EngineBudget())
    assert "rlifesrc" in cfg.argv[0]
    assert "1" in " ".join(cfg.argv)  # period 1 for a still life


def test_build_input_spaceship() -> None:
    cfg = RlifesrcAdapter().build_input(_ship(), EngineBudget())
    assert "rlifesrc" in cfg.argv[0]


def test_build_input_gun_raises_no_capability() -> None:
    with pytest.raises(NoCapability):
        RlifesrcAdapter().build_input(Gun(bbox_max=(10, 10)), EngineBudget())


def test_run_missing_binary_returns_error() -> None:
    cfg = RlifesrcAdapter().build_input(_osc(), EngineBudget())
    assert RlifesrcAdapter().run(cfg).outcome is EngineOutcome.ERROR


def test_run_unsat_marker_maps_to_unsat(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_present(monkeypatch, SandboxResult(0, "No solution\n", "", False))
    cfg = RlifesrcAdapter().build_input(_osc(), EngineBudget())
    raw = RlifesrcAdapter().run(cfg)
    assert raw.outcome is EngineOutcome.UNSAT
    assert raw.outcome is not EngineOutcome.TIMEOUT


def test_run_found(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_present(monkeypatch, SandboxResult(0, GLIDER_RLE, "", False))
    cfg = RlifesrcAdapter().build_input(_ship(), EngineBudget())
    raw = RlifesrcAdapter().run(cfg)
    assert raw.outcome is EngineOutcome.FOUND


def test_run_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_present(monkeypatch, SandboxResult(-1, "", "", True))
    cfg = RlifesrcAdapter().build_input(_osc(), EngineBudget())
    raw = RlifesrcAdapter().run(cfg)
    assert raw.outcome is EngineOutcome.TIMEOUT


def test_parse_yields_candidates() -> None:
    raw = RawResult(outcome=EngineOutcome.FOUND, meta={"stdout": GLIDER_RLE})
    cands = RlifesrcAdapter().parse(raw)
    assert len(cands) == 1
    assert cands[0].pattern.population == 5
    assert cands[0].engine_id is EngineId.RLIFESRC


@pytest.mark.skipif(shutil.which("rlifesrc") is None, reason="rlifesrc binary not installed")
def test_integration_small_oscillator() -> None:  # pragma: no cover - requires binary
    cfg = RlifesrcAdapter().build_input(_osc(), EngineBudget(wall_seconds=5.0))
    assert RlifesrcAdapter().run(cfg).outcome in set(EngineOutcome)
