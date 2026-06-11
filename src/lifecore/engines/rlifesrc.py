"""rlifesrc adapter (Task 6.4, SPEC §4.3) — general backtracking search.

rlifesrc is the broad directed searcher: low-period oscillators, still-lifes, and
small orthogonal/diagonal ships (per the capability map). Unlike qfind it *can* prove
non-existence within the posed box, so a printed UNSAT marker maps to a typed UNSAT
outcome (distinct from a TIMEOUT).
"""

from __future__ import annotations

import shutil
from typing import Any

from lifecore.engines._common import parse_stdout, run_engine
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
from lifecore.sandbox.runner import run_sandboxed, sandbox_available
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import Oscillator, Spaceship, StillLife, TargetSpec

BINARY = "rlifesrc"

# rlifesrc reports unsatisfiability in a few phrasings depending on front-end.
UNSAT_MARKERS = ("unsatisfiable", "no solution", "not found")


def _build_argv(spec: Spaceship | Oscillator | StillLife) -> tuple[list[str], dict[str, Any]]:
    """Map a spec to an rlifesrc argv + provenance (period/translation/box flags)."""
    p = spec.engine_params()
    dx = dy = 0
    if isinstance(spec, Spaceship):
        period = int(p["period"])
        dx, dy = p["displacement"]
        width = height = int(p["search_width"][1])
    elif isinstance(spec, Oscillator):
        period = int(p["period"])
        width, height = p["bbox_max"] or (16, 16)
    else:  # StillLife
        period = 1
        width, height = p["bbox_max"] or (16, 16)

    argv = [
        BINARY,
        str(width),
        str(height),
        str(period),
        str(dx),
        str(dy),
        "--rule", str(p["rule"]),
    ]
    meta: dict[str, Any] = {
        "spec_id": spec.spec_id,
        "kind": spec.kind.value,
        "period": period,
        "box": (width, height),
        "translation": (dx, dy),
    }
    return argv, meta


class RlifesrcAdapter(EngineAdapter):
    """Adapter over the ``rlifesrc`` backtracking searcher."""

    id = EngineId.RLIFESRC

    def capabilities(self) -> CapabilitySet:
        return CapabilitySet(self.id)

    def build_input(self, spec: TargetSpec, budget: EngineBudget) -> EngineConfig:
        if not self.capabilities().handles(spec) or not isinstance(
            spec, Spaceship | Oscillator | StillLife
        ):
            raise NoCapability(f"{self.id} cannot handle {spec.kind}")
        argv, meta = _build_argv(spec)
        return EngineConfig(engine_id=self.id, argv=argv, budget=budget, meta=meta)

    def run(self, cfg: EngineConfig) -> RawResult:
        return run_engine(
            cfg,
            binary=BINARY,
            which=shutil.which,
            sandbox_available=sandbox_available,
            run_sandboxed=run_sandboxed,
            unsat_markers=UNSAT_MARKERS,
            non_found_clean_exit=EngineOutcome.ERROR,
        )

    def parse(self, raw: RawResult) -> list[Candidate]:
        return parse_stdout(raw, self.id)
