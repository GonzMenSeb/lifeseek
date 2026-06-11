"""Novelty result types (Task 4.0 contract, SPEC §6).

Fail-closed by construction: the default/uncertain status is ``UNCERTAIN`` (never a
silent ``NOVEL``). The acceptance gate only treats ``NOVEL`` as a discovery.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class NoveltyStatus(StrEnum):
    NOVEL = "NOVEL"
    KNOWN = "KNOWN"
    DERIVATIVE = "DERIVATIVE"
    UNCERTAIN = "UNCERTAIN"  # fail-closed default (e.g. network failure, partial census)


class NoveltyResult(BaseModel):
    """Immutable two-tier novelty verdict (SPEC §6)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: NoveltyStatus
    apgcode: str | None = None
    snapshot_hash: str | None = None
    nearest_known: str | None = None
    mdl_delta: float | None = None
    notes: str = ""
