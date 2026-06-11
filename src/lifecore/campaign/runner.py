"""Deterministic campaign orchestrator (Phase 10 support, SPEC §7/§8/§12).

This is the LLM-free loop the agent layer drives through the MCP bridge: capability
check -> candidate stream -> verify -> novelty -> gate -> provenance, plus mandatory
IID/SCS baselines at EQUAL budget and an async intervention queue (redirect/chat). The
candidate stream is injected (in production it comes from sandboxed engine adapters);
the orchestrator itself never self-certifies — acceptance is always the gate's.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from lifecore.campaign.baseline import (
    BaselineResult,
    iid_random_sampler,
    run_baseline,
    scs_sampler,
)
from lifecore.campaign.budget import BudgetExceeded, BudgetLedger, BudgetLimits
from lifecore.campaign.stats import wilson_ci
from lifecore.novelty.catagolue import load_snapshot
from lifecore.novelty.results import NoveltyResult
from lifecore.sim.pattern import Pattern
from lifecore.store.recipe import (
    Recipe,
    current_canonicalizer_version,
    current_reference_sim_version,
)
from lifecore.targetspec.capability import capable_engines
from lifecore.targetspec.models import TargetSpec
from lifecore.verify import gate, verifier
from lifecore.verify.records import VerificationRecord


@dataclass
class Intervention:
    kind: str  # "redirect" | "chat"
    payload: Any


@dataclass
class InterventionQueue:
    """Async human intervention channel (SPEC §12): redirect takes precedence; chat logs."""

    _items: list[Intervention] = field(default_factory=list)

    def redirect(self, new_spec: TargetSpec) -> None:
        self._items.append(Intervention("redirect", new_spec))

    def chat(self, note: str) -> None:
        self._items.append(Intervention("chat", note))

    def drain(self) -> list[Intervention]:
        out = self._items[:]
        self._items.clear()
        return out


@dataclass(frozen=True)
class AcceptedDiscovery:
    pattern: Pattern
    verification: VerificationRecord
    novelty: NoveltyResult
    recipe: Recipe


@dataclass(frozen=True)
class CampaignReport:
    spec_id: str
    no_capable_engine: bool
    attempts: int
    discoveries: tuple[AcceptedDiscovery, ...]
    baselines: dict[str, BaselineResult]
    notes: tuple[str, ...]
    redirect_requested: TargetSpec | None = None

    def discovery_rate_ci(self) -> tuple[float, float]:
        return wilson_ci(len(self.discoveries), self.attempts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "no_capable_engine": self.no_capable_engine,
            "attempts": self.attempts,
            "discoveries": len(self.discoveries),
            "discovery_rate_ci": self.discovery_rate_ci(),
            "baselines": {
                name: {
                    "attempts": b.attempts,
                    "discoveries": b.discoveries,
                    "rate": b.discovery_rate,
                    "rate_ci": wilson_ci(b.discoveries, b.attempts),
                }
                for name, b in self.baselines.items()
            },
            "notes": list(self.notes),
        }


def _make_recipe(spec: TargetSpec, seed: int, budget: dict[str, Any], engine: str) -> Recipe:
    _, snapshot_hash = load_snapshot()
    return Recipe(
        engine=engine,
        engine_version="injected",
        build_flags="",
        config=spec.engine_params() if hasattr(spec, "engine_params") else {},
        seed=seed,
        budget=budget,
        reference_sim_version=current_reference_sim_version(),
        canonicalizer_version=current_canonicalizer_version(),
        catagolue_snapshot_hash=snapshot_hash,
        container_image_digest="uncertain:python:3.12-slim-bookworm",  # pinned at release
        spec_id=spec.spec_id,
    )


def run_campaign(
    spec: TargetSpec,
    *,
    candidate_source: Iterable[Pattern],
    novelty_fn: Callable[[Pattern], NoveltyResult],
    budget_limits: BudgetLimits | None = None,
    baseline_seed: int = 0,
    min_baseline_attempts: int = 10,
    interventions: InterventionQueue | None = None,
    engine: str = "injected",
) -> CampaignReport:
    """Run a directed campaign and return a report including mandatory baselines.

    Returns ``no_capable_engine=True`` immediately if the capability map routes the spec
    to no engine (never a misleading empty 'not found').
    """
    if not capable_engines(spec):
        return CampaignReport(
            spec_id=spec.spec_id,
            no_capable_engine=True,
            attempts=0,
            discoveries=(),
            baselines={},
            notes=("no-capable-engine: the capability map routes this spec to no engine",),
        )

    ledger = BudgetLedger(budget_limits or BudgetLimits())
    discoveries: list[AcceptedDiscovery] = []
    notes: list[str] = []
    redirect_requested: TargetSpec | None = None
    attempts = 0

    for candidate in candidate_source:
        if interventions is not None:
            for iv in interventions.drain():
                if iv.kind == "chat":
                    notes.append(f"chat: {iv.payload}")
                elif iv.kind == "redirect":
                    redirect_requested = iv.payload  # human-gated retarget handled by the bridge
                    notes.append("redirect requested (defer to human-gated retarget)")
            if redirect_requested is not None:
                break

        attempts += 1
        record = verifier.verify(candidate, spec)
        novelty = novelty_fn(candidate)
        decision = gate.accept(record, novelty)
        if decision.accepted:
            recipe = _make_recipe(spec, baseline_seed, ledger.as_dict(), engine)
            discoveries.append(AcceptedDiscovery(candidate, record, novelty, recipe))
        else:
            notes.append(f"rejected: {decision.reason}")

        try:
            ledger.charge_engine_cpu(1.0)
        except BudgetExceeded:
            notes.append("budget exhausted (hard stop)")
            break

    n_baseline = max(attempts, min_baseline_attempts)
    baselines = {
        "iid": run_baseline(
            spec, iid_random_sampler(spec, seed=baseline_seed), n_attempts=n_baseline, novelty_fn=novelty_fn
        ),
        "scs": run_baseline(
            spec, scs_sampler(spec, seed=baseline_seed), n_attempts=n_baseline, novelty_fn=novelty_fn
        ),
    }

    if not discoveries and not notes:
        notes.append("no discoveries")

    return CampaignReport(
        spec_id=spec.spec_id,
        no_capable_engine=False,
        attempts=attempts,
        discoveries=tuple(discoveries),
        baselines=baselines,
        notes=tuple(notes),
        redirect_requested=redirect_requested,
    )
