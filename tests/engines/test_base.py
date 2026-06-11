"""Contract tests for the engine adapter ABC (Task 6.1)."""

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
from lifecore.sim.pattern import Pattern
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import Oscillator, Spaceship, SymmetryClass


def test_outcomes_are_distinct() -> None:
    # TIMEOUT and UNSAT must never be conflated (width-escalation correctness)
    assert len({EngineOutcome.TIMEOUT, EngineOutcome.UNSAT}) == 2
    assert {o.value for o in EngineOutcome} == {"FOUND", "UNSAT", "TIMEOUT", "ERROR", "NO_CAPABILITY"}


def test_capability_set_uses_central_map() -> None:
    ship = Spaceship(
        displacement=(1, 1), period=4, symmetry_class=SymmetryClass.ASYMMETRIC, search_width=(1, 6)
    )
    assert CapabilitySet(EngineId.QFIND).handles(ship) is True
    assert CapabilitySet(EngineId.LLS).handles(ship) is False
    osc = Oscillator(period=3, bbox_max=(8, 8))
    assert CapabilitySet(EngineId.LLS).handles(osc) is True


def test_raw_result_defaults_and_frozen() -> None:
    r = RawResult(outcome=EngineOutcome.UNSAT)
    assert r.patterns_rle == [] and r.stderr == ""
    with pytest.raises((AttributeError, TypeError)):
        r.outcome = EngineOutcome.FOUND  # type: ignore[misc]


def test_candidate_carries_pattern_and_provenance() -> None:
    c = Candidate(pattern=Pattern(frozenset({(0, 0)})), engine_id=EngineId.RLIFESRC)
    assert c.pattern.population == 1
    assert c.engine_id == EngineId.RLIFESRC


def test_abstract_methods_enforced() -> None:
    with pytest.raises(TypeError):
        EngineAdapter()  # type: ignore[abstract]


def test_minimal_concrete_adapter_conforms() -> None:
    class Dummy(EngineAdapter):
        id = EngineId.RLIFESRC

        def capabilities(self) -> CapabilitySet:
            return CapabilitySet(self.id)

        def build_input(self, spec: object, budget: EngineBudget) -> EngineConfig:
            raise NoCapability("dummy")

        def run(self, cfg: EngineConfig) -> RawResult:
            return RawResult(outcome=EngineOutcome.TIMEOUT)

        def parse(self, raw: RawResult) -> list[Candidate]:
            return []

    d = Dummy()
    assert d.run(EngineConfig(engine_id=EngineId.RLIFESRC, argv=[])).outcome == EngineOutcome.TIMEOUT
    with pytest.raises(NoCapability):
        d.build_input(object(), EngineBudget())
