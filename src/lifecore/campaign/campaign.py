"""Frozen campaign configuration (Task 7.1, SPEC §8).

A :class:`Campaign` freezes a :class:`TargetSpec` together with an engine policy, a
budget, and the checkpoint phases. The spec is hashed at construction into a stable
``campaign_id`` so the whole search is content-addressed and reproducible. The engine
policy is validated against the capability map: a campaign can never be aimed through an
engine that cannot search its spec. A campaign for a no-capable-engine spec (e.g. a Gun
or an oblique ship) is still *constructible*, but :attr:`has_capable_engine` is ``False``
so callers can return ``no-capable-engine`` instead of a misleading "not found".
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from lifecore.campaign.budget import BudgetLimits
from lifecore.targetspec.capability import EngineId, capable_engines
from lifecore.targetspec.hashing import canonical_json
from lifecore.targetspec.models import TargetSpec

_DEFAULT_PHASES = ("feasibility", "tuning", "deep_search", "verification")


@dataclass(frozen=True)
class Campaign:
    """Immutable campaign config: a hashed spec + engine policy + budget + checkpoints."""

    spec: TargetSpec
    engine_policy: tuple[EngineId, ...]
    budget_limits: BudgetLimits = field(default_factory=BudgetLimits)
    checkpoint_phases: tuple[str, ...] = _DEFAULT_PHASES

    @property
    def campaign_id(self) -> str:
        """SHA-256 over the canonical (spec_id, engine_policy, budget) tuple."""
        payload = {
            "spec_id": self.spec.spec_id,
            "engine_policy": [e.value for e in self.engine_policy],
            "budget": {
                "max_usd": self.budget_limits.max_usd,
                "max_tokens": self.budget_limits.max_tokens,
                "max_engine_cpu_seconds": self.budget_limits.max_engine_cpu_seconds,
                "max_replans": self.budget_limits.max_replans,
            },
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()

    @property
    def has_capable_engine(self) -> bool:
        """Whether any engine can actually search this spec (capability map non-empty)."""
        return capable_engines(self.spec) != []

    @classmethod
    def create(
        cls,
        spec: TargetSpec,
        *,
        engine_policy: tuple[EngineId, ...] | None = None,
        budget_limits: BudgetLimits | None = None,
    ) -> Campaign:
        """Build a campaign, defaulting and validating the engine policy.

        If ``engine_policy`` is ``None`` it defaults to the full capability list for the
        spec. Every chosen engine MUST be in ``capable_engines(spec)``; otherwise a
        :class:`ValueError` is raised (no silently-incapable engine in the policy).
        """
        capable = capable_engines(spec)
        if engine_policy is None:
            policy = tuple(capable)
        else:
            for engine in engine_policy:
                if engine not in capable:
                    raise ValueError(
                        f"engine {engine.value!r} is not a capable engine for this spec "
                        f"(capable: {[e.value for e in capable]})"
                    )
            policy = tuple(engine_policy)
        return cls(
            spec=spec,
            engine_policy=policy,
            budget_limits=budget_limits if budget_limits is not None else BudgetLimits(),
        )
