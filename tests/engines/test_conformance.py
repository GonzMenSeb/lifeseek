"""Adapter conformance suite (Task 6.7).

A single parametrized contract every adapter must satisfy, regardless of whether its
binary is installed: the ABC shape holds, ``build_input`` raises ``NoCapability`` for
an unhandled spec, ``run`` never raises and returns a valid typed outcome, and
``parse`` is total. The ikpx2 stub is the only adapter that returns no candidates
even from a valid FOUND stdout — it is handled explicitly.
"""

from __future__ import annotations

import pytest

from lifecore.engines.base import (
    Candidate,
    CapabilitySet,
    EngineAdapter,
    EngineBudget,
    EngineConfig,
    EngineOutcome,
    NoCapability,
    RawResult,
)
from lifecore.engines.ikpx2 import Ikpx2Adapter
from lifecore.engines.lls import LlsAdapter
from lifecore.engines.qfind import QfindAdapter
from lifecore.engines.rlifesrc import RlifesrcAdapter
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import Gun

GLIDER_STDOUT = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!\n"

ADAPTERS: list[EngineAdapter] = [
    QfindAdapter(),
    RlifesrcAdapter(),
    LlsAdapter(),
    Ikpx2Adapter(),
]


def _ids(adapter: EngineAdapter) -> str:
    return adapter.id.value


@pytest.fixture(params=ADAPTERS, ids=_ids)
def adapter(request: pytest.FixtureRequest) -> EngineAdapter:
    param: EngineAdapter = request.param
    return param


def test_is_engine_adapter_with_engine_id(adapter: EngineAdapter) -> None:
    assert isinstance(adapter, EngineAdapter)
    assert isinstance(adapter.id, EngineId)


def test_capabilities_returns_capability_set(adapter: EngineAdapter) -> None:
    caps = adapter.capabilities()
    assert isinstance(caps, CapabilitySet)
    assert caps.engine_id is adapter.id


def test_build_input_unhandled_spec_raises_no_capability(adapter: EngineAdapter) -> None:
    # A Gun routes to no-capable-engine for every adapter (construction toolkits LATER).
    with pytest.raises(NoCapability):
        adapter.build_input(Gun(bbox_max=(10, 10)), EngineBudget())


def test_run_never_raises_returns_valid_outcome(adapter: EngineAdapter) -> None:
    raw = adapter.run(EngineConfig(engine_id=adapter.id, argv=[adapter.id.value]))
    assert isinstance(raw, RawResult)
    assert raw.outcome in set(EngineOutcome)
    if adapter.id is EngineId.IKPX2:
        assert raw.outcome is EngineOutcome.NO_CAPABILITY
    else:
        # Real binaries are absent in this environment -> ERROR.
        assert raw.outcome is EngineOutcome.ERROR


def test_parse_empty_outcome_returns_empty(adapter: EngineAdapter) -> None:
    assert adapter.parse(RawResult(outcome=EngineOutcome.UNSAT)) == []


def test_parse_found_stdout_yields_single_candidate(adapter: EngineAdapter) -> None:
    raw = RawResult(outcome=EngineOutcome.FOUND, meta={"stdout": GLIDER_STDOUT})
    cands = adapter.parse(raw)
    if adapter.id is EngineId.IKPX2:
        assert cands == []
        return
    assert len(cands) == 1
    cand = cands[0]
    assert isinstance(cand, Candidate)
    assert cand.pattern.population == 5
    assert cand.engine_id is adapter.id
