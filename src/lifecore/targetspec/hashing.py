"""Deterministic spec hashing (Task 2.1).

A spec's identity is the SHA-256 of its *canonical* JSON encoding: keys sorted,
no insignificant whitespace, stable across dict ordering and YAML round-trips. This
``spec_id`` is what the campaign freezes/signs and what the MCP bridge treats as
immutable (SPEC §1.5, §4.1).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    """Canonical JSON: sorted keys, compact separators, ASCII — order-independent."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def spec_id_for(payload: Any) -> str:
    """SHA-256 hex digest of the canonical JSON encoding of ``payload``."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
