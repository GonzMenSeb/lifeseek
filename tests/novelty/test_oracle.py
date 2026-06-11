"""Tests for the composed fail-closed novelty oracle (SPEC §6)."""

import pytest

from lifecore.novelty.oracle import novelty_query
from lifecore.novelty.results import NoveltyStatus
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle


def test_fail_closed_when_lifelib_or_canonicalization_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    import lifecore.novelty.canonical as canon

    def boom(_p: Pattern) -> str:
        raise RuntimeError("no canonicalizer")

    monkeypatch.setattr(canon, "apgcode", boom)
    result = novelty_query(parse_rle("bob$2bo$3o!"))
    assert result.status is NoveltyStatus.UNCERTAIN  # never silently NOVEL


def test_known_object_is_known() -> None:
    pytest.importorskip("lifelib")
    assert novelty_query(parse_rle("bob$2bo$3o!")).status is NoveltyStatus.KNOWN  # glider in snapshot


def test_unknown_object_is_novel() -> None:
    pytest.importorskip("lifelib")
    # a 2x2 block translated/combined is still 'xs4_33' (KNOWN); use a clearly-not-in-snapshot still life:
    # a 'tub' (xs4_252) is NOT in our small frozen snapshot -> NOVEL relative to it
    tub = Pattern(frozenset({(1, 0), (0, 1), (2, 1), (1, 2)}))
    assert novelty_query(tub).status is NoveltyStatus.NOVEL
