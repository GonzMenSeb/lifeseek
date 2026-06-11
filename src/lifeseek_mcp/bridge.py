"""Immutability-enforcing bridge core (Task 9.1/9.2, SPEC §11) — safety-critical.

This is the mechanical guard between the (fallible) Claude agent layer and the
deterministic core. It exposes ONLY read + append operations. It has NO setters for
the spec, gate, novelty, or budget, and it MECHANICALLY REJECTS any agent attempt to:

  * widen a tolerance field (search width beyond w_max, bbox_max, population_range,
    symmetry) — :class:`RelaxationError`;
  * propose an engine the capability map does not allow — :class:`RelaxationError`;
  * record a candidate as more-novel than the deterministic novelty oracle computed
    (e.g. reinterpret UNCERTAIN as NOVEL) — :class:`RelaxationError`;
  * re-aim the campaign without an approved human checkpoint — :class:`CheckpointRequired`.

The MCP transport (``server.py``) is a thin wrapper over this core; the enforcement
lives here so it is unit-testable without the optional ``mcp`` package. Textual "do not
change" is empirically insufficient (Zelikman et al., STOP) — hence the hard checks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from lifecore.campaign.campaign import Campaign
from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.pattern import Pattern
from lifecore.targetspec.capability import capable_engines
from lifecore.targetspec.models import Spaceship, TargetSpec
from lifecore.verify import gate, verifier
from lifecore.verify.records import VerificationRecord


class RelaxationError(Exception):
    """Raised when an agent attempts to relax/widen an immutable part of the gate."""


class CheckpointRequired(Exception):
    """Raised when a retarget is attempted without an approved human checkpoint."""


def _fail_closed_uncertain(_pattern: Pattern) -> NoveltyResult:
    return NoveltyResult(status=NoveltyStatus.UNCERTAIN, notes="no novelty oracle wired")


# Engine-tunable parameter keys the agent MAY set. Anything else is an immutable
# tolerance field and proposing it is a relaxation attempt.
_TUNABLE_KEYS = frozenset({"width", "seed", "engine_cpu_seconds"})
_IMMUTABLE_FIELD_KEYS = frozenset(
    {"bbox_max", "population_range", "symmetry", "symmetry_class", "period", "displacement", "rule"}
)


@dataclass
class _PendingRetarget:
    new_spec: TargetSpec
    diff: dict[str, Any]
    approved: bool = False


@dataclass
class Bridge:
    """Read/append surface over a frozen campaign, with mechanical immutability."""

    campaign: Campaign
    novelty_fn: Callable[[Pattern], NoveltyResult] = _fail_closed_uncertain
    failure_memory: Any = None  # optional lifecore.strategy.failure_memory.FailureMemory
    archive: Any = None  # optional lifecore.strategy.archive.StrategyArchive
    _pending: dict[str, _PendingRetarget] = field(default_factory=dict, init=False)
    _checkpoint_seq: int = field(default=0, init=False)

    # --- read tools (return copies / read-only views) ----------------------------
    def get_campaign(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign.campaign_id,
            "spec_id": self.campaign.spec.spec_id,
            "spec": self.campaign.spec.canonical_payload(),  # a copy; the real spec stays frozen
            "engine_policy": [e.value for e in self.campaign.engine_policy],
            "has_capable_engine": self.campaign.has_capable_engine,
        }

    def get_failure_memory(self) -> list[dict[str, Any]]:
        """Prior UNSAT envelopes relevant to this campaign's spec (read-only)."""
        if self.failure_memory is None:
            return []
        relevant = self.failure_memory.get_relevant(self.campaign.spec)
        return [
            {
                "spec_kind": e.spec_kind,
                "descriptor": e.descriptor,
                "engines": list(e.engines),
                "budget": e.budget,
                "source": e.source,
            }
            for e in relevant
        ]

    def get_strategy_archive(self) -> list[dict[str, Any]]:
        """Read-only snapshot of the strategy archive nodes."""
        if self.archive is None:
            return []
        return [
            {"node_id": n.node_id, "parent_id": n.parent_id, "descriptor": n.descriptor}
            for n in self.archive.nodes()
        ]

    def run_search(
        self,
        engine_id: str,
        params: dict[str, Any],
        runner: Callable[[str, dict[str, Any]], Any],
    ) -> Any:
        """Gate a search: validate the engine + params against the frozen spec, then run.

        ``runner`` is the injected (sandboxed) engine executor — the bridge enforces
        policy and non-relaxation, it does not itself execute binaries.
        """
        self.propose_engine_policy([engine_id])
        self.propose_search_params(params)
        return runner(engine_id, params)

    # --- append / action tools (validated) ---------------------------------------
    def propose_engine_policy(self, engine_ids: list[str]) -> list[str]:
        """Accept an engine policy ONLY if every engine is capability-map-allowed."""
        allowed = {e.value for e in capable_engines(self.campaign.spec)}
        bad = [e for e in engine_ids if e not in allowed]
        if bad:
            raise RelaxationError(
                f"engines {bad} are not capable for this spec (allowed: {sorted(allowed)})"
            )
        return engine_ids

    def propose_search_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Accept only engine-tunable params within the frozen spec's bounds.

        Proposing an immutable tolerance field, or a width beyond ``w_max``, is a
        relaxation attempt and is rejected.
        """
        for key in params:
            if key in _IMMUTABLE_FIELD_KEYS:
                raise RelaxationError(f"'{key}' is an immutable spec field; it cannot be retuned")
            if key not in _TUNABLE_KEYS:
                raise RelaxationError(f"'{key}' is not an agent-tunable parameter")
        if "width" in params and isinstance(self.campaign.spec, Spaceship):
            w_min, w_max = self.campaign.spec.search_width
            width = int(params["width"])
            if width > w_max or width < w_min:
                raise RelaxationError(
                    f"width {width} outside frozen search_width [{w_min}, {w_max}]"
                )
        return params

    def verify_candidate(self, candidate: Pattern) -> VerificationRecord:
        """Verify against the FROZEN spec on the reference path. No spec override allowed."""
        return verifier.verify(candidate, self.campaign.spec)

    def check_novelty(self, candidate: Pattern) -> NoveltyResult:
        return self.novelty_fn(candidate)

    def record_result(
        self,
        candidate: Pattern,
        claimed_novelty: NoveltyStatus | None = None,
    ) -> gate.AcceptanceDecision:
        """Run the real gate. If the agent CLAIMS a novelty status, it must match the
        oracle's — claiming NOVEL when the oracle says UNCERTAIN/KNOWN is rejected."""
        verification = self.verify_candidate(candidate)
        novelty = self.check_novelty(candidate)
        if claimed_novelty is not None and claimed_novelty != novelty.status:
            raise RelaxationError(
                f"claimed novelty {claimed_novelty} != oracle {novelty.status}; "
                "the agent may not reinterpret the novelty verdict"
            )
        return gate.accept(verification, novelty)

    # --- human-gated retarget (re-aim) -------------------------------------------
    def request_retarget_checkpoint(self, new_spec: TargetSpec) -> str:
        """Stage a re-aim; returns a checkpoint id. Does NOT apply — needs human approval."""
        self._checkpoint_seq += 1
        checkpoint_id = f"ckpt-{self._checkpoint_seq}"
        diff = {
            "from_spec_id": self.campaign.spec.spec_id,
            "to_spec_id": new_spec.spec_id,
        }
        self._pending[checkpoint_id] = _PendingRetarget(new_spec=new_spec, diff=diff)
        return checkpoint_id

    def approve_checkpoint(self, checkpoint_id: str) -> None:
        """HUMAN-SIDE action (gated to the human channel in the MCP server)."""
        if checkpoint_id not in self._pending:
            raise KeyError(f"unknown checkpoint {checkpoint_id!r}")
        self._pending[checkpoint_id].approved = True

    def retarget(self, checkpoint_id: str) -> Bridge:
        """Apply an APPROVED retarget, returning a fresh bridge on the new frozen spec."""
        pending = self._pending.get(checkpoint_id)
        if pending is None:
            raise CheckpointRequired(f"no such checkpoint {checkpoint_id!r}")
        if not pending.approved:
            raise CheckpointRequired(
                "retarget requires an approved human checkpoint (provenance diff recorded)"
            )
        new_campaign = Campaign.create(
            pending.new_spec,
            engine_policy=None,
            budget_limits=self.campaign.budget_limits,
        )
        return Bridge(campaign=new_campaign, novelty_fn=self.novelty_fn)
