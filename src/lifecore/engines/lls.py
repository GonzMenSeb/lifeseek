"""LLS adapter (Task 6.5, SPEC §4.3, §5.2) — SAT-based search.

LLS (Logic Life Search) encodes the search as SAT: still-lifes, low-period
oscillators (exists-in-bbox), and — via :meth:`LlsAdapter.build_goe_preimage_input`
— Garden-of-Eden / non-existence *preimage* search. The preimage search REQUIRES a
padding thickness of at least 4 cells around the target (SPEC §5.2): a thinner border
can spuriously report UNSAT because a real predecessor needs room to feed the target.
LLS prints ``UNSAT`` when no predecessor exists.
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
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import to_rle
from lifecore.targetspec.capability import EngineId
from lifecore.targetspec.models import Oscillator, StillLife, TargetSpec

BINARY = "LLS"

UNSAT_MARKERS = ("unsat", "no solution", "unsatisfiable")

MIN_GOE_PADDING = 4  # SPEC §5.2: thinner borders can produce spurious UNSAT


def _build_argv(spec: StillLife | Oscillator) -> tuple[list[str], dict[str, Any]]:
    """Map a still-life / low-period oscillator spec to an LLS argv + provenance."""
    p = spec.engine_params()
    period = int(p["period"]) if isinstance(spec, Oscillator) else 1
    width, height = p["bbox_max"] or (16, 16)
    argv = [
        BINARY,
        "-p", str(period),
        "-x", str(width),
        "-y", str(height),
        "-r", str(p["rule"]),
    ]
    meta: dict[str, Any] = {
        "spec_id": spec.spec_id,
        "kind": spec.kind.value,
        "period": period,
        "box": (width, height),
    }
    return argv, meta


class LlsAdapter(EngineAdapter):
    """Adapter over the ``LLS`` SAT-based searcher."""

    id = EngineId.LLS

    def capabilities(self) -> CapabilitySet:
        return CapabilitySet(self.id)

    def build_input(self, spec: TargetSpec, budget: EngineBudget) -> EngineConfig:
        if not self.capabilities().handles(spec) or not isinstance(spec, StillLife | Oscillator):
            raise NoCapability(f"{self.id} cannot handle {spec.kind}")
        argv, meta = _build_argv(spec)
        return EngineConfig(engine_id=self.id, argv=argv, budget=budget, meta=meta)

    def build_goe_preimage_input(
        self, target_pattern: Pattern, padding_thickness: int, budget: EngineBudget
    ) -> EngineConfig:
        """Build a one-generation predecessor (GoE) search around ``target_pattern``.

        ``padding_thickness`` must be >= 4 (SPEC §5.2); a UNSAT here is meaningful
        evidence the target is a Garden of Eden (has no predecessor).
        """
        if padding_thickness < MIN_GOE_PADDING:
            raise ValueError(
                f"padding_thickness must be >= {MIN_GOE_PADDING} for a sound GoE "
                f"preimage search (got {padding_thickness})"
            )
        target_rle = to_rle(target_pattern)
        argv = [
            BINARY,
            "-g", "1",  # search for a generation-1 predecessor
            "-b", str(padding_thickness),
            "-t", "target.rle",
            "-r", target_pattern.rule,
        ]
        meta: dict[str, Any] = {
            "mode": "goe_preimage",
            "padding_thickness": padding_thickness,
            "target_population": target_pattern.population,
            "rule": target_pattern.rule,
        }
        return EngineConfig(
            engine_id=self.id,
            argv=argv,
            files={"target.rle": target_rle},
            budget=budget,
            meta=meta,
        )

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
