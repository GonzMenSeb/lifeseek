"""Idempotent crash-safe resume (Task 5.3, SPEC §9).

The pipeline assigns an *idempotency key* to each step that has a side effect (a paid
Claude call, a candidate write, ...). :func:`checkpointed` enforces the
CHECKPOINT-AFTER-SIDE-EFFECT rule:

1. If the key is already recorded in the ``checkpoint`` table, the stored result is
   returned WITHOUT re-running the action — so a resumed run never re-pays a Claude
   call nor double-writes a candidate.
2. Otherwise the action runs, and ONLY AFTER it returns is the checkpoint written.
   A crash mid-action therefore leaves no checkpoint, so the step is safely retried.

Results are stored as canonical JSON, so an action must return a JSON-able value.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TypeVar

from lifecore.store.db import Store
from lifecore.targetspec.hashing import canonical_json

T = TypeVar("T")


def _load_checkpoint(store: Store, key: str) -> tuple[bool, object]:
    """Return ``(found, result)``; ``result`` is the decoded stored value when found."""
    row = store.execute(
        "SELECT result_json FROM checkpoint WHERE idempotency_key = ?", (key,)
    ).fetchone()
    if row is None:
        return False, None
    return True, json.loads(row["result_json"])


def checkpointed(store: Store, idempotency_key: str, action: Callable[[], T]) -> T:
    """Run ``action`` at most once per ``idempotency_key`` (crash-safe).

    On a cache hit the previously recorded result is returned and ``action`` is NOT
    called. On a miss ``action`` runs first; its result is checkpointed only afterwards
    (so an interrupted action is retried, never marked done).
    """
    found, cached = _load_checkpoint(store, idempotency_key)
    if found:
        return cached  # type: ignore[return-value]

    result = action()  # side effect — runs before the checkpoint is recorded

    store.execute(
        "INSERT INTO checkpoint (idempotency_key, result_json, created_at) VALUES (?, ?, ?)",
        (idempotency_key, canonical_json(result), datetime.now(UTC).isoformat()),
    )
    return result
