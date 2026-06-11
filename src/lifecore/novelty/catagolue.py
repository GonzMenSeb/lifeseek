"""Catagolue census-membership tier of the novelty oracle (Task 4.2, SPEC §6.2).

This is the *catalog-membership* tier of the two-tier, FAIL-CLOSED novelty oracle.
It answers "has this apgcode been seen before?" against a frozen local census
snapshot, with an optional live refresh hook.

Cardinal rule: a network / live-lookup failure must yield ``UNCERTAIN`` — never a
silent ``NOVEL``. Concretely, if the supplied ``fetcher`` raises *any* exception we
return ``NoveltyStatus.UNCERTAIN`` (SPEC §6.2).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.targetspec.hashing import canonical_json

DEFAULT_SNAPSHOT: Path = (
    Path(__file__).resolve().parents[3] / "tests/fixtures/catagolue_snapshot.json"
)


def load_snapshot(path: Path | None = None) -> tuple[frozenset[str], str]:
    """Load the frozen census snapshot.

    Returns ``(census_apgcodes, snapshot_hash)`` where ``snapshot_hash`` is the
    SHA-256 hex of the canonical JSON of the *sorted* census list — deterministic
    and independent of the source file's key/element ordering.
    """
    snapshot_path = path if path is not None else DEFAULT_SNAPSHOT
    with snapshot_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    census_list: list[str] = list(data["census"])
    census = frozenset(census_list)
    snapshot_hash = hashlib.sha256(
        canonical_json(sorted(census_list)).encode("utf-8")
    ).hexdigest()
    return census, snapshot_hash


def query(
    apgcode: str,
    *,
    fetcher: Callable[[str], bool] | None = None,
    snapshot_path: Path | None = None,
) -> NoveltyResult:
    """Verdict for ``apgcode`` against the frozen census, with optional live refresh.

    - In the snapshot census -> ``KNOWN``.
    - Not in census and ``fetcher is None`` (frozen-snapshot-only mode) -> ``NOVEL``
      (novel *relative to the frozen snapshot*; deterministic).
    - Not in census and a ``fetcher`` is given (live refresh requested):
        * fetcher raises -> ``UNCERTAIN`` (network failure; NEVER ``NOVEL``).
        * fetcher returns ``True`` (found live) -> ``KNOWN``.
        * fetcher returns ``False`` -> ``NOVEL``.
    """
    census, snapshot_hash = load_snapshot(snapshot_path)

    if apgcode in census:
        return NoveltyResult(
            status=NoveltyStatus.KNOWN,
            apgcode=apgcode,
            snapshot_hash=snapshot_hash,
            notes="present in frozen Catagolue census snapshot",
        )

    if fetcher is None:
        return NoveltyResult(
            status=NoveltyStatus.NOVEL,
            apgcode=apgcode,
            snapshot_hash=snapshot_hash,
            notes="absent from frozen snapshot; offline (no live fetcher)",
        )

    try:
        found = fetcher(apgcode)
    except Exception as exc:  # fail-closed: ANY failure -> UNCERTAIN, never NOVEL
        return NoveltyResult(
            status=NoveltyStatus.UNCERTAIN,
            apgcode=apgcode,
            snapshot_hash=snapshot_hash,
            notes=f"live Catagolue lookup failed ({type(exc).__name__}: {exc}); "
            "fail-closed to UNCERTAIN, not NOVEL",
        )

    if found:
        return NoveltyResult(
            status=NoveltyStatus.KNOWN,
            apgcode=apgcode,
            snapshot_hash=snapshot_hash,
            notes="found in live Catagolue census",
        )
    return NoveltyResult(
        status=NoveltyStatus.NOVEL,
        apgcode=apgcode,
        snapshot_hash=snapshot_hash,
        notes="absent from frozen snapshot and live Catagolue census",
    )
