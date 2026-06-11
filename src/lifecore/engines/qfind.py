"""qfind adapter (Task 6.3, SPEC §4.3) — primary spaceship search.

qfind is the width-parameterized orthogonal/diagonal spaceship searcher. Oblique
ships are ikpx2's job (the capability map already excludes them here). Crucially,
qfind cannot *prove* non-existence: a non-found clean exit is a TIMEOUT, never UNSAT,
so the width-escalation policy keeps widening instead of giving up.
"""

from __future__ import annotations

import shutil

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
from lifecore.targetspec.models import SlopeClass, Spaceship, TargetSpec

BINARY = "qfind"


def _build_argv(spec: Spaceship) -> tuple[list[str], dict[str, object]]:
    """Map a spaceship spec to a qfind argv + provenance meta (testable in isolation).

    Flags are reasonable placeholders pinned later in ``tools/versions.lock``; the
    mapping (width, slope, period, displacement) is what matters for routing/tests.
    """
    params = spec.engine_params()
    w_min, w_max = params["search_width"]
    dx, dy = (abs(c) for c in params["displacement"])
    period = params["period"]
    slope = params["slope"]
    speed = max(dx, dy)  # cells advanced per period along the axis of travel

    diagonal = slope == SlopeClass.DIAGONAL.value
    argv = [
        BINARY,
        "-w", str(w_max),
        "-W", str(w_min),
        "-p", str(period),
        "-y", str(speed),
        ("-d" if diagonal else "-o"),
    ]
    meta: dict[str, object] = {
        "spec_id": spec.spec_id,
        "slope": slope,
        "search_width": (w_min, w_max),
        "period": period,
        "displacement": params["displacement"],
    }
    return argv, meta


class QfindAdapter(EngineAdapter):
    """Adapter over the ``qfind`` spaceship searcher."""

    id = EngineId.QFIND

    def capabilities(self) -> CapabilitySet:
        return CapabilitySet(self.id)

    def build_input(self, spec: TargetSpec, budget: EngineBudget) -> EngineConfig:
        if not self.capabilities().handles(spec) or not isinstance(spec, Spaceship):
            raise NoCapability(f"{self.id} cannot handle {spec.kind}")
        argv, meta = _build_argv(spec)
        return EngineConfig(engine_id=self.id, argv=argv, budget=budget, meta=meta)

    def run(self, cfg: EngineConfig) -> RawResult:
        # qfind cannot prove UNSAT: a clean non-found exit is a TIMEOUT, not UNSAT.
        return run_engine(
            cfg,
            binary=BINARY,
            which=shutil.which,
            sandbox_available=sandbox_available,
            run_sandboxed=run_sandboxed,
            unsat_markers=(),
            non_found_clean_exit=EngineOutcome.TIMEOUT,
        )

    def parse(self, raw: RawResult) -> list[Candidate]:
        return parse_stdout(raw, self.id)
