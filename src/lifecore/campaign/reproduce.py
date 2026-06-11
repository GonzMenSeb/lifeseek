"""Bitwise reproduction of an accepted discovery (Task 11.2, SPEC §14.6).

RELEASE BLOCKER. ``reproduce_discovery`` takes a stored discovery artifact, rebuilds
the spec and candidate from the *serialized* fields only, re-runs the independent
verification and novelty oracle, and compares the fresh outputs to the stored ones
BIT-FOR-BIT (canonical-JSON equality). Because a :class:`VerificationRecord` dumps its
own ``signature``, a bitwise match of the dumped record proves the content signature
replays too. The recipe is compared on its *reproducibility* fields only (the code-path
hashes, the census snapshot, and the spec id) — wall-clock-ish fields such as the live
budget ledger are intentionally excluded.

This is the function ``lifeseek reproduce`` calls; CI runs it nightly over the accepted
discoveries to guarantee the acceptance pipeline is bit-reproducible.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from lifecore.novelty.oracle import novelty_query
from lifecore.novelty.results import NoveltyResult
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle
from lifecore.targetspec.hashing import canonical_json
from lifecore.targetspec.yaml_io import from_yaml
from lifecore.verify import verifier

_RECIPE_REPRO_FIELDS = (
    "reference_sim_version",
    "canonicalizer_version",
    "catagolue_snapshot_hash",
    "spec_id",
)


@dataclass(frozen=True)
class ReproResult:
    """Outcome of a bitwise reproduction attempt."""

    ok: bool
    verification_match: bool
    novelty_match: bool
    recipe_match: bool
    details: str


def reproduce_discovery(
    artifact: dict[str, Any],
    *,
    novelty_fn: Callable[[Pattern], NoveltyResult] = novelty_query,
) -> ReproResult:
    """Replay the acceptance pipeline for ``artifact`` and compare bitwise."""
    spec = from_yaml(artifact["spec_yaml"])
    candidate = parse_rle(artifact["candidate_rle"])

    fresh_verification = verifier.verify(candidate, spec)
    fresh_novelty = novelty_fn(candidate)

    verification_match = canonical_json(
        fresh_verification.model_dump(mode="json")
    ) == canonical_json(artifact["verification"])
    novelty_match = canonical_json(fresh_novelty.model_dump(mode="json")) == canonical_json(
        artifact["novelty"]
    )

    # The recipe's reproducibility fields are recomputed from the live trust-path
    # modules and the spec, then compared to what was stored at discovery time.
    from lifecore.novelty.catagolue import load_snapshot
    from lifecore.store.recipe import (
        current_canonicalizer_version,
        current_reference_sim_version,
    )

    stored_recipe = artifact["recipe"]
    _, snapshot_hash = load_snapshot()
    fresh_repro = {
        "reference_sim_version": current_reference_sim_version(),
        "canonicalizer_version": current_canonicalizer_version(),
        "catagolue_snapshot_hash": snapshot_hash,
        "spec_id": spec.spec_id,
    }
    recipe_match = all(stored_recipe.get(f) == fresh_repro[f] for f in _RECIPE_REPRO_FIELDS)

    ok = verification_match and novelty_match and recipe_match
    details = "bitwise match" if ok else _mismatch_details(
        verification_match, novelty_match, recipe_match
    )
    return ReproResult(
        ok=ok,
        verification_match=verification_match,
        novelty_match=novelty_match,
        recipe_match=recipe_match,
        details=details,
    )


def _mismatch_details(verification: bool, novelty: bool, recipe: bool) -> str:
    bad = [
        name
        for name, ok in (("verification", verification), ("novelty", novelty), ("recipe", recipe))
        if not ok
    ]
    return "mismatch in: " + ", ".join(bad)
