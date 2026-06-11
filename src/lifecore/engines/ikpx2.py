"""ikpx2 adapter — v1 STUB (Task 6.6, SPEC §4.3).

ikpx2 is the oblique / knightship searcher. It is routed oblique spaceships by the
capability map, but the search itself is LATER: rather than silently returning "not
found" (which the policy would misread as evidence of non-existence), this stub
reports a typed ``NO_CAPABILITY`` so the campaign records an honest no-capable-engine
result. Replacing this file with a real adapter is all that's needed later.
"""

from __future__ import annotations

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
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import TargetSpec


class Ikpx2Adapter(EngineAdapter):
    """v1 stub: routes correctly but cannot execute (oblique search is LATER)."""

    id = EngineId.IKPX2

    def capabilities(self) -> CapabilitySet:
        return CapabilitySet(self.id)

    def build_input(self, spec: TargetSpec, budget: EngineBudget) -> EngineConfig:
        raise NoCapability("ikpx2 oblique search is not implemented in v1; LATER")

    def run(self, cfg: EngineConfig) -> RawResult:
        return RawResult(outcome=EngineOutcome.NO_CAPABILITY, meta={"reason": "ikpx2 stub"})

    def parse(self, raw: RawResult) -> list[Candidate]:
        return []
