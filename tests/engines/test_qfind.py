"""Tests for the qfind spaceship adapter (Task 6.3)."""

from __future__ import annotations

import shutil

import pytest

from lifecore.engines import qfind as qfind_mod
from lifecore.engines.base import EngineBudget, EngineOutcome, NoCapability, RawResult
from lifecore.engines.qfind import QfindAdapter
from lifecore.sandbox.runner import SandboxResult
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import Spaceship, StillLife, SymmetryClass

GLIDER_RLE = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!\n"


def _ortho_ship() -> Spaceship:
    return Spaceship(
        displacement=(0, 2),
        period=4,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(5, 12),
    )


def _oblique_ship() -> Spaceship:
    return Spaceship(
        displacement=(1, 2),
        period=6,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(5, 12),
    )


def test_id_and_capabilities() -> None:
    a = QfindAdapter()
    assert a.id is EngineId.QFIND
    assert a.capabilities().engine_id is EngineId.QFIND


def test_build_input_orthogonal_includes_binary_and_width() -> None:
    cfg = QfindAdapter().build_input(_ortho_ship(), EngineBudget())
    assert "qfind" in cfg.argv[0]
    joined = " ".join(cfg.argv)
    assert "12" in joined  # the max search width
    assert cfg.meta["slope"] == "orthogonal"


def test_build_input_oblique_raises_no_capability() -> None:
    with pytest.raises(NoCapability):
        QfindAdapter().build_input(_oblique_ship(), EngineBudget())


def test_build_input_still_life_raises_no_capability() -> None:
    with pytest.raises(NoCapability):
        QfindAdapter().build_input(StillLife(bbox_max=(6, 6)), EngineBudget())


def test_run_missing_binary_returns_error_no_raise() -> None:
    cfg = QfindAdapter().build_input(_ortho_ship(), EngineBudget())
    raw = QfindAdapter().run(cfg)
    assert raw.outcome is EngineOutcome.ERROR


def test_run_non_found_clean_exit_is_timeout_not_unsat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lifecore.engines.qfind.shutil.which", lambda _: "/usr/bin/qfind")
    monkeypatch.setattr(qfind_mod, "sandbox_available", lambda: True)
    monkeypatch.setattr(
        qfind_mod,
        "run_sandboxed",
        lambda *a, **k: SandboxResult(0, "no results\n", "", False),
    )
    raw = QfindAdapter().run(QfindAdapter().build_input(_ortho_ship(), EngineBudget()))
    assert raw.outcome is EngineOutcome.TIMEOUT
    assert raw.outcome.value != EngineOutcome.UNSAT.value


def test_run_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lifecore.engines.qfind.shutil.which", lambda _: "/usr/bin/qfind")
    monkeypatch.setattr(qfind_mod, "sandbox_available", lambda: True)
    monkeypatch.setattr(
        qfind_mod, "run_sandboxed", lambda *a, **k: SandboxResult(-1, "", "", True)
    )
    raw = QfindAdapter().run(QfindAdapter().build_input(_ortho_ship(), EngineBudget()))
    assert raw.outcome is EngineOutcome.TIMEOUT


def test_run_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lifecore.engines.qfind.shutil.which", lambda _: "/usr/bin/qfind")
    monkeypatch.setattr(qfind_mod, "sandbox_available", lambda: True)
    monkeypatch.setattr(
        qfind_mod, "run_sandboxed", lambda *a, **k: SandboxResult(0, GLIDER_RLE, "", False)
    )
    raw = QfindAdapter().run(QfindAdapter().build_input(_ortho_ship(), EngineBudget()))
    assert raw.outcome is EngineOutcome.FOUND
    assert raw.meta["stdout"] == GLIDER_RLE


def test_parse_glider_yields_one_candidate_population_5() -> None:
    raw = RawResult(outcome=EngineOutcome.FOUND, meta={"stdout": GLIDER_RLE})
    cands = QfindAdapter().parse(raw)
    assert len(cands) == 1
    assert cands[0].pattern.population == 5
    assert cands[0].engine_id is EngineId.QFIND


@pytest.mark.skipif(shutil.which("qfind") is None, reason="qfind binary not installed")
def test_integration_small_c2_ship() -> None:  # pragma: no cover - requires binary
    cfg = QfindAdapter().build_input(_ortho_ship(), EngineBudget(wall_seconds=5.0))
    raw = QfindAdapter().run(cfg)
    assert raw.outcome in set(EngineOutcome)
