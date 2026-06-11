"""Append-only SQLite provenance event log (Task 5.1, SPEC §9).

The :class:`Store` is the single durable record of the pipeline:
``campaign -> run -> candidate -> {verification, novelty, acceptance}``. It is
append-only by construction — every table has BEFORE UPDATE / BEFORE DELETE
triggers (see ``schema.sql``) that ``RAISE(ABORT, ...)``, so the only legal write
is an INSERT and any attempted UPDATE/DELETE surfaces as a :class:`sqlite3.Error`.

Every append accepts an optional ``idempotency_key``; replaying an append with a
key already present returns the EXISTING row id rather than inserting a duplicate,
which is what makes crash-safe resume (Task 5.3) re-derive the same provenance.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from lifecore.novelty.results import NoveltyResult
from lifecore.targetspec.hashing import canonical_json
from lifecore.verify.gate import AcceptanceDecision
from lifecore.verify.records import VerificationRecord

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# Columns that hold canonical-JSON text and should be decoded on read.
_JSON_COLUMNS = frozenset(
    {"spec_json", "budget_json", "config_json", "record_json", "result_json"}
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    """Append-only SQLite provenance log over the discovery pipeline."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        self._conn.commit()

    # -- low-level ---------------------------------------------------------

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Run an arbitrary statement (commits on success). Mutations raise sqlite3 errors."""
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur

    def _append(
        self,
        table: str,
        columns: dict[str, Any],
        idempotency_key: str | None,
    ) -> int:
        """Insert a row (with ``created_at`` + ``idempotency_key``) and return its id.

        If ``idempotency_key`` is already present the insert is ignored and the id of
        the pre-existing row is returned — appends are idempotent under their key.
        """
        if idempotency_key is not None:
            existing = self._conn.execute(
                f"SELECT id FROM {table} WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                return int(existing["id"])

        data = {**columns, "created_at": _now(), "idempotency_key": idempotency_key}
        names = ", ".join(data)
        placeholders = ", ".join("?" for _ in data)
        cur = self._conn.execute(
            f"INSERT INTO {table} ({names}) VALUES ({placeholders})",
            tuple(data.values()),
        )
        self._conn.commit()
        if cur.lastrowid is None:  # pragma: no cover - defensive
            raise RuntimeError(f"insert into {table} returned no row id")
        return int(cur.lastrowid)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        out: dict[str, Any] = dict(row)
        for col in _JSON_COLUMNS & out.keys():
            value = out[col]
            if isinstance(value, str):
                out[col] = json.loads(value)
        return out

    def _get_by_id(self, table: str, row_id: int) -> dict[str, Any]:
        row = self._conn.execute(
            f"SELECT * FROM {table} WHERE id = ?", (row_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"no {table} row with id {row_id}")
        return self._row_to_dict(row)

    # -- append methods ----------------------------------------------------

    def append_campaign(
        self,
        spec_id: str,
        spec_json: dict[str, Any],
        budget_json: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> int:
        return self._append(
            "campaign",
            {
                "spec_id": spec_id,
                "spec_json": canonical_json(spec_json),
                "budget_json": canonical_json(budget_json),
            },
            idempotency_key,
        )

    def append_run(
        self,
        campaign_id: int,
        engine: str,
        config_json: dict[str, Any],
        seed: int,
        idempotency_key: str | None = None,
    ) -> int:
        return self._append(
            "run",
            {
                "campaign_id": campaign_id,
                "engine": engine,
                "config_json": canonical_json(config_json),
                "seed": seed,
            },
            idempotency_key,
        )

    def append_candidate(
        self,
        run_id: int,
        rle: str,
        population: int,
        idempotency_key: str | None = None,
    ) -> int:
        return self._append(
            "candidate",
            {"run_id": run_id, "rle": rle, "population": population},
            idempotency_key,
        )

    def append_verification(
        self,
        candidate_id: int,
        record: VerificationRecord,
        idempotency_key: str | None = None,
    ) -> int:
        return self._append(
            "verification",
            {
                "candidate_id": candidate_id,
                "verdict": record.verdict.value,
                "record_json": canonical_json(record.model_dump(mode="json")),
            },
            idempotency_key,
        )

    def append_novelty(
        self,
        candidate_id: int,
        result: NoveltyResult,
        idempotency_key: str | None = None,
    ) -> int:
        return self._append(
            "novelty",
            {
                "candidate_id": candidate_id,
                "status": result.status.value,
                "result_json": canonical_json(result.model_dump(mode="json")),
            },
            idempotency_key,
        )

    def append_acceptance(
        self,
        candidate_id: int,
        decision: AcceptanceDecision,
        idempotency_key: str | None = None,
    ) -> int:
        return self._append(
            "acceptance",
            {
                "candidate_id": candidate_id,
                "accepted": int(decision.accepted),
                "reason": decision.reason,
            },
            idempotency_key,
        )

    # -- read helpers ------------------------------------------------------

    def get_campaign(self, campaign_id: int) -> dict[str, Any]:
        return self._get_by_id("campaign", campaign_id)

    def get_run(self, run_id: int) -> dict[str, Any]:
        return self._get_by_id("run", run_id)

    def get_candidate(self, candidate_id: int) -> dict[str, Any]:
        return self._get_by_id("candidate", candidate_id)

    def list_candidates(self, run_id: int) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM candidate WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _get_by_candidate(self, table: str, candidate_id: int) -> dict[str, Any]:
        row = self._conn.execute(
            f"SELECT * FROM {table} WHERE candidate_id = ? ORDER BY id LIMIT 1",
            (candidate_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"no {table} row for candidate {candidate_id}")
        out = self._row_to_dict(row)
        if "accepted" in out:
            out["accepted"] = bool(out["accepted"])
        return out

    def get_verification(self, candidate_id: int) -> dict[str, Any]:
        return self._get_by_candidate("verification", candidate_id)

    def get_novelty(self, candidate_id: int) -> dict[str, Any]:
        return self._get_by_candidate("novelty", candidate_id)

    def get_acceptance(self, candidate_id: int) -> dict[str, Any]:
        return self._get_by_candidate("acceptance", candidate_id)

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
