"""Reproducible recipe object (Task 5.2, SPEC §9).

A :class:`Recipe` freezes everything needed to reproduce a run bit-for-bit: which
engine + version + build flags, the exact config, seed, budget, and the content
hashes of the two trust-path code modules (reference simulator and canonicalizer),
the Catagolue census snapshot, and the container image digest. Its ``recipe_id`` is
the SHA-256 of its canonical-JSON encoding, so two recipes that differ only in dict
ordering hash identically while any semantic change changes the id.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from lifecore.targetspec.hashing import canonical_json
from lifecore.verify.records import reference_sim_version_hash


class Recipe(BaseModel):
    """Immutable, fully-specified reproduction recipe for one run (SPEC §9)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    engine: str
    engine_version: str
    build_flags: str
    config: dict[str, Any]
    seed: int
    budget: dict[str, Any]
    reference_sim_version: str
    canonicalizer_version: str
    catagolue_snapshot_hash: str
    container_image_digest: str
    spec_id: str
    notes: str = ""

    @property
    def recipe_id(self) -> str:
        """SHA-256 of the canonical-JSON encoding — order-independent content id."""
        return hashlib.sha256(
            canonical_json(self.model_dump(mode="json")).encode("utf-8")
        ).hexdigest()


def current_reference_sim_version() -> str:
    """SHA-256 of the running reference-simulator source (the verification trust path)."""
    return reference_sim_version_hash()


def current_canonicalizer_version() -> str:
    """SHA-256 of the running canonicalizer source (the novelty trust path)."""
    from lifecore.novelty import canonical

    src = Path(canonical.__file__ or "")
    return hashlib.sha256(src.read_bytes()).hexdigest()
