"""Tests for idempotent crash-safe resume (Task 5.3, SPEC §9)."""

from __future__ import annotations

from unittest.mock import Mock

from lifecore.store.db import Store
from lifecore.store.resume import checkpointed


def test_resume_no_double_write() -> None:
    with Store() as store:
        cid = store.append_campaign(spec_id="a" * 64, spec_json={}, budget_json={})
        rid = store.append_run(cid, engine="lls", config_json={}, seed=0)
        writes = 0

        def write_candidate() -> int:
            nonlocal writes
            writes += 1
            return store.append_candidate(rid, rle="2o$2o!", population=4)

        first = checkpointed(store, "candidate:1", write_candidate)
        second = checkpointed(store, "candidate:1", write_candidate)

        assert writes == 1  # the side effect ran exactly once
        assert first == second
        assert len(store.list_candidates(rid)) == 1


def test_resume_no_repaid_claude_call() -> None:
    with Store() as store:
        claude = Mock(return_value={"strategy": "narrow the box"})

        r1 = checkpointed(store, "claude:plan:1", claude)
        r2 = checkpointed(store, "claude:plan:1", claude)

        claude.assert_called_once()  # the paid call happened exactly once
        assert r1 == r2 == {"strategy": "narrow the box"}


def test_distinct_keys_run_independently() -> None:
    with Store() as store:
        calls: list[str] = []

        def make(tag: str) -> object:
            calls.append(tag)
            return {"tag": tag}

        a = checkpointed(store, "key:a", lambda: make("a"))
        b = checkpointed(store, "key:b", lambda: make("b"))

        assert calls == ["a", "b"]
        assert a == {"tag": "a"}
        assert b == {"tag": "b"}
