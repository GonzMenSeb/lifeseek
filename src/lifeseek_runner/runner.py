"""Unattended runner interface (Phase 12, LATER — interface + smoke test only).

The unattended runner is the optional Anthropic-API frontend: it drives the exact same
``lifeseek_mcp.bridge.Bridge`` read/append tools as the Claude Code skill, so it inherits
the identical, mechanically-enforced immutability (no setters; no relaxation; human-gated
retarget). v1 provides the shape and a queue for async checkpoints; the Agent-SDK loop is
deliberately NOT implemented yet — :meth:`UnattendedRunner.run` raises ``NotImplementedError``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from lifeseek_mcp.bridge import Bridge


@dataclass
class CheckpointQueue:
    """Async checkpoint queue for unattended runs (human approvals arrive out-of-band)."""

    _pending: list[str] = field(default_factory=list)
    _approved: set[str] = field(default_factory=set)

    def enqueue(self, checkpoint_id: str) -> None:
        self._pending.append(checkpoint_id)

    def approve(self, checkpoint_id: str) -> None:
        self._approved.add(checkpoint_id)

    def pending(self) -> list[str]:
        return [c for c in self._pending if c not in self._approved]

    def is_approved(self, checkpoint_id: str) -> bool:
        return checkpoint_id in self._approved


@dataclass
class UnattendedRunner:
    """(LATER) drives the MCP bridge via the Agent SDK. v1: interface + queue only."""

    bridge: Bridge
    agent_factory: Callable[..., Any] | None = None
    checkpoints: CheckpointQueue = field(default_factory=CheckpointQueue)

    def run(self, *_args: Any, **_kwargs: Any) -> Any:
        raise NotImplementedError(
            "the Anthropic-API unattended runner is LATER (v1 ships the interface only); "
            "use the Claude Code frontend (agent/skills/lifeseek) for now"
        )
