"""Tests for the append-only SQLite provenance event log (Task 5.1, SPEC §9)."""

from __future__ import annotations

import sqlite3

import pytest

from lifecore.novelty.results import NoveltyResult, NoveltyStatus
from lifecore.store.db import Store
from lifecore.verify.gate import accept
from lifecore.verify.records import Verdict, VerificationRecord


def _verification(spec_id: str = "a" * 64) -> VerificationRecord:
    return VerificationRecord(
        spec_id=spec_id,
        rule="B3/S23",
        verdict=Verdict.PASS,
        claim="spaceship",
        claimed_period=4,
        observed_period=4,
    ).signed()


def _novelty() -> NoveltyResult:
    return NoveltyResult(status=NoveltyStatus.NOVEL, apgcode="xq4_153")


def test_round_trip_campaign_run_candidate() -> None:
    with Store() as store:
        cid = store.append_campaign(
            spec_id="a" * 64,
            spec_json={"kind": "spaceship", "period": 4},
            budget_json={"wall_seconds": 60},
        )
        rid = store.append_run(cid, engine="rlifesrc", config_json={"width": 10}, seed=7)
        cand = store.append_candidate(rid, rle="bo$2bo$3o!", population=5)

        assert isinstance(cid, int)
        assert isinstance(rid, int)
        assert isinstance(cand, int)

        campaign = store.get_campaign(cid)
        assert campaign["spec_id"] == "a" * 64
        assert campaign["spec_json"]["period"] == 4
        assert campaign["budget_json"]["wall_seconds"] == 60

        run = store.get_run(rid)
        assert run["campaign_id"] == cid
        assert run["engine"] == "rlifesrc"
        assert run["config_json"]["width"] == 10
        assert run["seed"] == 7

        candidates = store.list_candidates(rid)
        assert len(candidates) == 1
        assert candidates[0]["id"] == cand
        assert candidates[0]["rle"] == "bo$2bo$3o!"
        assert candidates[0]["population"] == 5


def test_store_is_append_only() -> None:
    with Store() as store:
        cid = store.append_campaign(
            spec_id="b" * 64, spec_json={"k": 1}, budget_json={"b": 2}
        )
        with pytest.raises(sqlite3.Error):
            store.execute("UPDATE campaign SET spec_id = 'zzz' WHERE id = ?", (cid,))
        with pytest.raises(sqlite3.Error):
            store.execute("DELETE FROM campaign WHERE id = ?", (cid,))
        # row survived both attempts
        assert store.get_campaign(cid)["spec_id"] == "b" * 64


def test_idempotent_append_returns_same_id_and_no_duplicate() -> None:
    with Store() as store:
        first = store.append_campaign(
            spec_id="c" * 64,
            spec_json={"k": 1},
            budget_json={"b": 2},
            idempotency_key="campaign:c",
        )
        second = store.append_campaign(
            spec_id="c" * 64,
            spec_json={"k": 999},  # different payload, same key -> ignored
            budget_json={"b": 2},
            idempotency_key="campaign:c",
        )
        assert first == second
        count = store.execute("SELECT COUNT(*) AS n FROM campaign").fetchone()["n"]
        assert count == 1
        # the original payload is preserved (insert was ignored, not overwritten)
        assert store.get_campaign(first)["spec_json"]["k"] == 1


def test_append_verification_and_novelty_and_acceptance() -> None:
    with Store() as store:
        cid = store.append_campaign(
            spec_id="d" * 64, spec_json={"k": 1}, budget_json={"b": 2}
        )
        rid = store.append_run(cid, engine="lls", config_json={}, seed=0)
        cand = store.append_candidate(rid, rle="2o$2o!", population=4)

        record = _verification("d" * 64)
        novelty = _novelty()
        decision = accept(record, novelty)

        vid = store.append_verification(cand, record)
        nid = store.append_novelty(cand, novelty)
        aid = store.append_acceptance(cand, decision)
        assert all(isinstance(x, int) for x in (vid, nid, aid))

        v = store.get_verification(cand)
        assert v["verdict"] == "PASS"
        assert v["record_json"]["signature"] == record.signature
        assert v["candidate_id"] == cand

        n = store.get_novelty(cand)
        assert n["status"] == "NOVEL"
        assert n["result_json"]["apgcode"] == "xq4_153"

        a = store.get_acceptance(cand)
        assert a["accepted"] is True
        assert "accepted" in a["reason"]
