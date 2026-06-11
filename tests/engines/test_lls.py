"""Tests for the LLS SAT adapter (Task 6.5)."""

from __future__ import annotations

import shutil

import pytest

from lifecore.engines import lls as lls_mod
from lifecore.engines.base import EngineBudget, EngineOutcome, NoCapability, RawResult
from lifecore.engines.lls import LlsAdapter
from lifecore.sandbox.runner import SandboxResult
from lifecore.sim.pattern import Pattern
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import Oscillator, Spaceship, StillLife, SymmetryClass

GLIDER_RLE = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!\n"


def _still() -> StillLife:
    return StillLife(bbox_max=(6, 6))


def _osc() -> Oscillator:
    return Oscillator(period=2, bbox_max=(8, 8))


def _ship() -> Spaceship:
    return Spaceship(
        displacement=(0, 1),
        period=4,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(3, 9),
    )


def _block() -> Pattern:
    return Pattern(frozenset({(0, 0), (1, 0), (0, 1), (1, 1)}))


def _patch_present(monkeypatch: pytest.MonkeyPatch, result: SandboxResult) -> None:
    monkeypatch.setattr(lls_mod.shutil, "which", lambda _: "/usr/bin/LLS")
    monkeypatch.setattr(lls_mod, "sandbox_available", lambda: True)
    monkeypatch.setattr(lls_mod, "run_sandboxed", lambda *a, **k: result)


def test_id_and_capabilities() -> None:
    a = LlsAdapter()
    assert a.id is EngineId.LLS
    assert a.capabilities().engine_id is EngineId.LLS


def test_build_input_still_life() -> None:
    cfg = LlsAdapter().build_input(_still(), EngineBudget())
    assert "LLS" in cfg.argv[0]


def test_build_input_oscillator() -> None:
    cfg = LlsAdapter().build_input(_osc(), EngineBudget())
    assert "LLS" in cfg.argv[0]
    assert "2" in " ".join(cfg.argv)  # period


def test_build_input_spaceship_raises_no_capability() -> None:
    with pytest.raises(NoCapability):
        LlsAdapter().build_input(_ship(), EngineBudget())


def test_goe_preimage_rejects_thin_padding() -> None:
    with pytest.raises(ValueError, match="padding_thickness"):
        LlsAdapter().build_goe_preimage_input(_block(), padding_thickness=3, budget=EngineBudget())


def test_goe_preimage_accepts_thick_padding() -> None:
    cfg = LlsAdapter().build_goe_preimage_input(
        _block(), padding_thickness=4, budget=EngineBudget()
    )
    assert "LLS" in cfg.argv[0]
    assert cfg.meta["padding_thickness"] == 4
    assert cfg.meta["mode"] == "goe_preimage"


def test_run_missing_binary_returns_error() -> None:
    cfg = LlsAdapter().build_input(_still(), EngineBudget())
    assert LlsAdapter().run(cfg).outcome is EngineOutcome.ERROR


def test_run_unsat_marker_maps_to_unsat(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_present(monkeypatch, SandboxResult(0, "UNSAT\n", "", False))
    cfg = LlsAdapter().build_input(_still(), EngineBudget())
    raw = LlsAdapter().run(cfg)
    assert raw.outcome is EngineOutcome.UNSAT
    assert raw.outcome is not EngineOutcome.TIMEOUT


def test_run_found(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_present(monkeypatch, SandboxResult(0, GLIDER_RLE, "", False))
    cfg = LlsAdapter().build_input(_still(), EngineBudget())
    assert LlsAdapter().run(cfg).outcome is EngineOutcome.FOUND


def test_run_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_present(monkeypatch, SandboxResult(-1, "", "", True))
    cfg = LlsAdapter().build_input(_still(), EngineBudget())
    assert LlsAdapter().run(cfg).outcome is EngineOutcome.TIMEOUT


def test_parse_yields_candidates() -> None:
    raw = RawResult(outcome=EngineOutcome.FOUND, meta={"stdout": GLIDER_RLE})
    cands = LlsAdapter().parse(raw)
    assert len(cands) == 1
    assert cands[0].pattern.population == 5
    assert cands[0].engine_id is EngineId.LLS


@pytest.mark.skipif(shutil.which("LLS") is None, reason="LLS binary not installed")
def test_integration_still_life() -> None:  # pragma: no cover - requires binary
    cfg = LlsAdapter().build_input(_still(), EngineBudget(wall_seconds=5.0))
    assert LlsAdapter().run(cfg).outcome in set(EngineOutcome)
