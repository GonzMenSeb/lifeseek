# agentic-search-for-life

A **directed, re-aimable scientific-discovery harness for Conway's Game of Life (B3/S23)** — internal harness
codename **`lifeseek`**. You give it a typed *target specification* (e.g. "a c/5 orthogonal spaceship", "a
period-19 oscillator"); it runs steered, budget-bounded search campaigns wrapping open-source Life engines; a
result is accepted as a **discovery** only when it is **spec-met ∧ independently re-simulation-verified ∧ novel**
vs known catalogs. Edit the target spec → re-aim the whole effort.

> This repo currently contains the **approved, literature-vetted design and implementation plan** — not yet the
> code. It is ready to execute.

## Read these in order
1. [`docs/lifeseek/SPEC.md`](docs/lifeseek/SPEC.md) — source of truth: architecture, the (corrected) GoL domain
   model, the closed-world verification protocol, novelty, budget/baseline/statistics, provenance & reproduce,
   sandboxing, MCP immutability, and the v1 acceptance criteria. Every non-obvious choice cites the paper behind it.
2. [`docs/lifeseek/IMPLEMENTATION_PLAN.md`](docs/lifeseek/IMPLEMENTATION_PLAN.md) — phased, TDD task plan (13
   phases) with explicit **⟂PARALLEL** lanes for concurrent subagents.
3. [`docs/lifeseek/PROGRESS.md`](docs/lifeseek/PROGRESS.md) — **live build state** (checklist + handoff note).
   Read it first every session; update it in the same commit as each task.

## To execute (hand off to a fresh Claude Code session)
Open this repo in a new session and say roughly:

> Implement `agentic-search-for-life` (codename `lifeseek`) by following `docs/lifeseek/IMPLEMENTATION_PLAN.md`.
> Read `SPEC.md` and `PROGRESS.md` first. Use the `superpowers:subagent-driven-development` skill, dispatch the
> ⟂PARALLEL lanes to concurrent subagents, and update `PROGRESS.md` in the same commit as each task. Stop at the
> Phase 1 differential-harness gate for my review.

## Invariants the implementation must never violate (from SPEC §1)
- The agent **never self-certifies** — all acceptance logic lives in the deterministic, LLM-free `lifecore`.
- Verification runs on the **independent NumPy reference path**, never a second invocation of the producing
  engine (lifelib); accepted-discovery canonicalization is independently cross-checked.
- Acceptance is **closed-world & object-type-specific** (empty-field embedding, empty-residual assertion,
  true-period vs trivial-LCM).
- Novelty is **fail-closed** (unknown ⇒ `UNCERTAIN`, never silent "novel").
- The target spec, verifier, novelty test, and budget are **structurally immutable** from the agent side
  (MCP-enforced, no setters).
- Provenance is append-only; accepted discoveries replay **bitwise** via `lifeseek reproduce`.

## License
TBD (add before any public release).
