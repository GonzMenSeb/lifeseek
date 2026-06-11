"""Tests for the ikpx2 stub adapter (Task 6.6)."""

from __future__ import annotations

import pytest

from lifecore.engines.base import (
    EngineBudget,
    EngineConfig,
    EngineOutcome,
    NoCapability,
    RawResult,
)
from lifecore.engines.ikpx2 import Ikpx2Adapter
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import Spaceship, SymmetryClass


def _oblique_ship() -> Spaceship:
    return Spaceship(
        displacement=(1, 2),
        period=6,
        symmetry_class=SymmetryClass.ASYMMETRIC,
        search_width=(5, 12),
    )


def test_id_and_capabilities() -> None:
    a = Ikpx2Adapter()
    assert a.id is EngineId.IKPX2
    assert a.capabilities().engine_id is EngineId.IKPX2


def test_build_input_raises_no_capability_for_oblique() -> None:
    with pytest.raises(NoCapability, match="LATER"):
        Ikpx2Adapter().build_input(_oblique_ship(), EngineBudget())


def test_run_returns_no_capability() -> None:
    cfg = EngineConfig(engine_id=EngineId.IKPX2, argv=["ikpx2"])
    raw = Ikpx2Adapter().run(cfg)
    assert raw.outcome is EngineOutcome.NO_CAPABILITY
    assert raw.meta["reason"] == "ikpx2 stub"


def test_parse_returns_empty() -> None:
    raw = RawResult(
        outcome=EngineOutcome.FOUND,
        meta={"stdout": "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!\n"},
    )
    assert Ikpx2Adapter().parse(raw) == []
