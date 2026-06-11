-- Append-only provenance event log (Task 5.1, SPEC §9).
--
-- The pipeline chain is campaign -> run -> candidate -> {verification, novelty,
-- acceptance}. Every table carries a nullable UNIQUE idempotency_key so a replay
-- after a crash re-derives the same row id instead of double-writing.
--
-- Immutability is enforced MECHANICALLY: each table has BEFORE UPDATE / BEFORE
-- DELETE triggers that RAISE(ABORT, ...). Any UPDATE/DELETE therefore raises a
-- sqlite3 error; the only legal mutation is INSERT.

CREATE TABLE IF NOT EXISTS campaign (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id         TEXT NOT NULL,
    spec_json       TEXT NOT NULL,
    budget_json     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS run (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id     INTEGER NOT NULL REFERENCES campaign(id),
    engine          TEXT NOT NULL,
    config_json     TEXT NOT NULL,
    seed            INTEGER NOT NULL,
    created_at      TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS candidate (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES run(id),
    rle             TEXT NOT NULL,
    population      INTEGER NOT NULL,
    created_at      TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS verification (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id    INTEGER NOT NULL REFERENCES candidate(id),
    verdict         TEXT NOT NULL,
    record_json     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS novelty (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id    INTEGER NOT NULL REFERENCES candidate(id),
    status          TEXT NOT NULL,
    result_json     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS acceptance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id    INTEGER NOT NULL REFERENCES candidate(id),
    accepted        INTEGER NOT NULL,
    reason          TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);

-- Idempotent crash-safe resume checkpoints (Task 5.3, SPEC §9). The checkpoint is
-- written AFTER the side effect, so a crash mid-action leaves no checkpoint row.
CREATE TABLE IF NOT EXISTS checkpoint (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT NOT NULL UNIQUE,
    result_json     TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

-- Append-only triggers: forbid UPDATE and DELETE on every table.

CREATE TRIGGER IF NOT EXISTS campaign_no_update BEFORE UPDATE ON campaign
BEGIN SELECT RAISE(ABORT, 'append-only store: campaign is immutable'); END;
CREATE TRIGGER IF NOT EXISTS campaign_no_delete BEFORE DELETE ON campaign
BEGIN SELECT RAISE(ABORT, 'append-only store: campaign is immutable'); END;

CREATE TRIGGER IF NOT EXISTS run_no_update BEFORE UPDATE ON run
BEGIN SELECT RAISE(ABORT, 'append-only store: run is immutable'); END;
CREATE TRIGGER IF NOT EXISTS run_no_delete BEFORE DELETE ON run
BEGIN SELECT RAISE(ABORT, 'append-only store: run is immutable'); END;

CREATE TRIGGER IF NOT EXISTS candidate_no_update BEFORE UPDATE ON candidate
BEGIN SELECT RAISE(ABORT, 'append-only store: candidate is immutable'); END;
CREATE TRIGGER IF NOT EXISTS candidate_no_delete BEFORE DELETE ON candidate
BEGIN SELECT RAISE(ABORT, 'append-only store: candidate is immutable'); END;

CREATE TRIGGER IF NOT EXISTS verification_no_update BEFORE UPDATE ON verification
BEGIN SELECT RAISE(ABORT, 'append-only store: verification is immutable'); END;
CREATE TRIGGER IF NOT EXISTS verification_no_delete BEFORE DELETE ON verification
BEGIN SELECT RAISE(ABORT, 'append-only store: verification is immutable'); END;

CREATE TRIGGER IF NOT EXISTS novelty_no_update BEFORE UPDATE ON novelty
BEGIN SELECT RAISE(ABORT, 'append-only store: novelty is immutable'); END;
CREATE TRIGGER IF NOT EXISTS novelty_no_delete BEFORE DELETE ON novelty
BEGIN SELECT RAISE(ABORT, 'append-only store: novelty is immutable'); END;

CREATE TRIGGER IF NOT EXISTS acceptance_no_update BEFORE UPDATE ON acceptance
BEGIN SELECT RAISE(ABORT, 'append-only store: acceptance is immutable'); END;
CREATE TRIGGER IF NOT EXISTS acceptance_no_delete BEFORE DELETE ON acceptance
BEGIN SELECT RAISE(ABORT, 'append-only store: acceptance is immutable'); END;

CREATE TRIGGER IF NOT EXISTS checkpoint_no_update BEFORE UPDATE ON checkpoint
BEGIN SELECT RAISE(ABORT, 'append-only store: checkpoint is immutable'); END;
CREATE TRIGGER IF NOT EXISTS checkpoint_no_delete BEFORE DELETE ON checkpoint
BEGIN SELECT RAISE(ABORT, 'append-only store: checkpoint is immutable'); END;
