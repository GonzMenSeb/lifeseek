"""Composed, fail-closed novelty oracle (SPEC §6) — apgcode -> Catagolue (+ MDL).

Glues the two tiers into a single function the runner/CLI/agent call. It is FAIL-CLOSED
by construction: if canonicalization is unavailable (lifelib missing) or a pattern won't
canonicalize (a chaotic soup that never settles), the verdict is ``UNCERTAIN`` — never a
silent ``NOVEL``.
"""

from __future__ import annotations

from pathlib import Path

from lifecore.novelty import catagolue, mdl
from lifecore.novelty.canonical import independent_canonical
from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.sim.pattern import Pattern


def novelty_query(
    pattern: Pattern,
    *,
    snapshot_path: Path | None = None,
    known_independent_keys: set[str] | None = None,
) -> NoveltyResult:
    """Two-tier novelty verdict, fail-closed.

    1. apgcode (lifelib) -> Catagolue membership (KNOWN / NOVEL / UNCERTAIN).
    2. If the catalog tier says NOVEL, an MDL pass can still downgrade a separable
       derivative-of-known to DERIVATIVE (when ``known_independent_keys`` is supplied).
    Any canonicalization failure short-circuits to UNCERTAIN.
    """
    try:
        from lifecore.novelty.canonical import apgcode

        code = apgcode(pattern)
    except Exception:
        return NoveltyResult(status=NoveltyStatus.UNCERTAIN, notes="canonicalization unavailable")

    result = catagolue.query(code, snapshot_path=snapshot_path)
    if result.status is not NoveltyStatus.NOVEL or not known_independent_keys:
        return result

    mdl_result = mdl.classify(pattern, known_independent_keys, identity=independent_canonical)
    if mdl_result.status is NoveltyStatus.DERIVATIVE:
        return mdl_result.model_copy(update={"apgcode": code, "snapshot_hash": result.snapshot_hash})
    return result
