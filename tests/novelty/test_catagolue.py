"""Tests for the Catagolue frozen-snapshot membership tier (Task 4.2, SPEC §6.2).

The cardinal rule under test: a live-lookup failure yields UNCERTAIN, never NOVEL.
"""

from __future__ import annotations

import re

import pytest

from lifecore.novelty import catagolue
from lifecore.novelty.results import NoveltyStatus

_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")


def test_known_apgcode_in_snapshot() -> None:
    result = catagolue.query("xs4_33")
    assert result.status is NoveltyStatus.KNOWN
    assert result.apgcode == "xs4_33"
    assert result.snapshot_hash is not None
    assert _HEX64.match(result.snapshot_hash)


def test_unknown_apgcode_offline_is_novel() -> None:
    result = catagolue.query("xs99_madeup")
    assert result.status is NoveltyStatus.NOVEL
    assert result.apgcode == "xs99_madeup"


def test_network_failure_is_uncertain_not_novel() -> None:
    def boom(_apgcode: str) -> bool:
        raise ConnectionError("network down")

    result = catagolue.query("xs99_madeup", fetcher=boom)
    # The cardinal rule: a network failure is UNCERTAIN, NOT a (false) NOVEL.
    assert result.status not in (NoveltyStatus.NOVEL, NoveltyStatus.KNOWN)
    assert result.status is NoveltyStatus.UNCERTAIN
    assert result.apgcode == "xs99_madeup"
    assert result.notes  # explains the failure


def test_live_found_is_known() -> None:
    def found(_apgcode: str) -> bool:
        return True

    result = catagolue.query("xs99_madeup", fetcher=found)
    assert result.status is NoveltyStatus.KNOWN


def test_live_not_found_is_novel() -> None:
    def not_found(_apgcode: str) -> bool:
        return False

    result = catagolue.query("xs99_madeup", fetcher=not_found)
    assert result.status is NoveltyStatus.NOVEL


def test_snapshot_hash_is_stable() -> None:
    _, hash_a = catagolue.load_snapshot()
    _, hash_b = catagolue.load_snapshot()
    assert hash_a == hash_b
    assert _HEX64.match(hash_a)


def test_known_apgcode_uses_snapshot_even_with_fetcher() -> None:
    # A census hit short-circuits before any live lookup is attempted.
    def boom(_apgcode: str) -> bool:
        raise ConnectionError("must not be called")

    result = catagolue.query("xp2_7", fetcher=boom)
    assert result.status is NoveltyStatus.KNOWN


def test_load_snapshot_returns_frozenset() -> None:
    census, _ = catagolue.load_snapshot()
    assert isinstance(census, frozenset)
    assert "xq4_153" in census


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
