"""Append-only strategy archive with DGM parent-selection (SPEC §7; Hu et al., DGM).

The archive is the memory of the self-improvement loop: every search node ever run is
recorded and *never* removed or mutated. New campaigns evolve from an existing node
chosen by Darwin-Goedel-Machine-style parent selection — biased toward high-utility
nodes that have not yet been heavily explored (open-ended exploration).

The meta-utility is verified-novel discoveries per unit budget, with a correct UNSAT
on a known-impossible spec credited as one unit of useful work. This is the key
correctness property: the loop is *not* rewarded for thrashing on impossible specs and
*not* punished for correctly proving non-existence.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

_EPSILON = 1e-9
# Floor so every node retains nonzero selection weight (open-endedness).
_WEIGHT_FLOOR = 1e-6


@dataclass(frozen=True)
class StrategyOutcome:
    verified_novel: int
    budget_spent: float
    correct_unsat: bool = False
    """True iff the node correctly returned UNSAT on a known-impossible spec."""


@dataclass(frozen=True)
class StrategyNode:
    node_id: int
    parent_id: int | None
    descriptor: dict[str, Any]
    outcome: StrategyOutcome


def meta_utility(outcome: StrategyOutcome) -> float:
    """Verified-novel discoveries per unit budget; a correct UNSAT counts as one unit.

    Pure function. ``(verified_novel + correct_unsat) / max(budget_spent, epsilon)``.
    Crediting correct UNSAT means proving non-existence on an impossible spec is as
    valuable as finding one novel object, and thrashing (no result) yields 0.
    """
    useful = outcome.verified_novel + (1 if outcome.correct_unsat else 0)
    return useful / max(outcome.budget_spent, _EPSILON)


@dataclass
class StrategyArchive:
    """Append-only store of strategy nodes with DGM parent selection."""

    _nodes: list[StrategyNode] = field(default_factory=list)
    _child_counts: dict[int, int] = field(default_factory=dict)

    def add(
        self,
        parent_id: int | None,
        descriptor: dict[str, Any],
        outcome: StrategyOutcome,
    ) -> StrategyNode:
        """Append a new node with a fresh incrementing id; never mutates existing nodes."""
        node = StrategyNode(
            node_id=len(self._nodes),
            parent_id=parent_id,
            descriptor=dict(descriptor),
            outcome=outcome,
        )
        self._nodes.append(node)
        if parent_id is not None:
            self._child_counts[parent_id] = self._child_counts.get(parent_id, 0) + 1
        return node

    def nodes(self) -> tuple[StrategyNode, ...]:
        """Read-only snapshot of all nodes."""
        return tuple(self._nodes)

    def children_count(self, node_id: int) -> int:
        return self._child_counts.get(node_id, 0)

    def select_parent(self, rng: random.Random) -> StrategyNode | None:
        """DGM parent selection: weight each node by ``score / (1 + children_count)``.

        ``score = max(meta_utility(node.outcome), floor)`` so every node keeps a nonzero
        probability (open-ended exploration), while heavily-childed or low-utility nodes
        are sampled less often. Returns None if the archive is empty.
        """
        if not self._nodes:
            return None
        weights = [
            max(meta_utility(n.outcome), _WEIGHT_FLOOR) / (1 + self.children_count(n.node_id))
            for n in self._nodes
        ]
        return _weighted_choice(self._nodes, weights, rng)


def _weighted_choice(
    nodes: Sequence[StrategyNode], weights: Sequence[float], rng: random.Random
) -> StrategyNode:
    total = sum(weights)
    threshold = rng.random() * total
    upto = 0.0
    for node, weight in zip(nodes, weights, strict=True):
        upto += weight
        if upto >= threshold:
            return node
    return nodes[-1]  # floating-point fallback
