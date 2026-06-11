# lifeseek v1 — Implementation Progress Tracker

> **This file is the single source of truth for "where we are."** Read it at the start of every session.
> Update it **in the same commit** as the task it describes. A fresh session must be able to resume from this
> file + git history alone — never rely on conversation memory.
>
> Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked.
> When you finish a task: check its box, paste the commit hash, log any decision/deviation, move the
> **⮕ CURRENT POSITION** marker, and (before stopping) rewrite the **HANDOFF NOTE**.

---

## ⮕ CURRENT POSITION
**Phase 0 · Task 0.1 — not yet started.** First action: `git init` + scaffold (see IMPLEMENTATION_PLAN Task 0.1).

## HANDOFF NOTE (rewrite before every stop)
- **Just did:** _nothing yet — fresh start._
- **Doing next:** Phase 0, Task 0.1 (repo + tooling).
- **Half-done / careful:** _none._
- **Resume command:** `cd lifeseek && cat docs/lifeseek/PROGRESS.md && git log --oneline -5`
- **Open questions for the human:** confirm engine source SHAs to pin (qfind, rlifesrc, LLS) in Task 0.2.

---

## Environment / invariants checklist (verify once, re-verify if they change)
- [ ] `uv` env builds from `uv.lock`; `pytest`, `ruff`, `mypy` run clean.
- [ ] `python-lifelib` importable in CI; engine binaries build in the Containerfile at pinned SHAs.
- [ ] **INVARIANT:** `verify/verifier.py` imports `sim/reference.py` and **never** lifelib (guard test green).
- [ ] **INVARIANT:** producer (lifelib) and verifier (numpy) share no simulation code; novelty uses an
      independent cross-check canonicalizer for accepted discoveries.
- [ ] **INVARIANT:** spec/verifier/novelty/budget are read-only through the MCP bridge (no setters).

---

## Phase checklist

### Phase 0 — Scaffold, env lock, progress artifact
- [ ] 0.1 Repo + tooling — commit: ______
- [ ] 0.2 Containerfile + version pins — commit: ______
- [ ] 0.3 Instantiate PROGRESS.md — commit: ______

### Phase 1 — Pattern model + dual simulators + differential harness  *(bedrock; gates Phase 2)*
- [ ] 1.1 (contract) Pattern + RLE io — commit: ______
- [ ] 1.2 ⟂A NumPy reference simulator (verifier path; no lifelib) — commit: ______
- [ ] 1.3 ⟂B lifelib HashLife backend — commit: ______
- [ ] 1.4 (integration) lifelib↔numpy differential harness **(green required to proceed)** — commit: ______

### Phase 2 — Target spec + capability map + hashing
- [ ] 2.1 (contract) base spec + hashing + YAML — commit: ______
- [ ] 2.2 ⟂A spaceship spec (population/bbox = post-hoc, not engine input) — commit: ______
- [ ] 2.3 ⟂B oscillator (mechanism-split) + still-life + LATER stubs — commit: ______
- [ ] 2.4 (integration) capability map (gun/oblique → no-capable-engine) — commit: ______

### Phase 3 — Verification gate (crown jewel)
- [ ] 3.1 (contract) universal closed-world verifier + record (reference path only) — commit: ______
- [ ] 3.2 ⟂A oscillator rotor/stator + true-period (reject trivial LCM) — commit: ______
- [ ] 3.3 ⟂B still-life stability + rigorous GoE (orphan witness) — commit: ______
- [ ] 3.4 (integration) acceptance gate + adversarial golden suite **(release blocker)** — commit: ______

### Phase 4 — Novelty oracle (two-tier, fail-closed)
- [ ] 4.0 (contract) NoveltyResult types — commit: ______
- [ ] 4.1 ⟂ canonical (apgcode + independent cross-check) — commit: ______
- [ ] 4.2 ⟂ catagolue (frozen snapshot; network-fail → UNCERTAIN) — commit: ______
- [ ] 4.3 ⟂ mdl/minimality (reject derivative-of-known) — commit: ______
- [ ] 4.4 (integration) symmetry soundness suite **(release blocker)** — commit: ______

### Phase 5 — Store, provenance, recipe, crash-safe resume
- [ ] 5.1 append-only SQLite event log — commit: ______
- [ ] 5.2 reproducible recipe object — commit: ______
- [ ] 5.3 idempotent crash-safe resume — commit: ______

### Phase 6 — Sandbox + engine adapters
- [ ] 6.1 (contract) EngineAdapter ABC — commit: ______
- [ ] 6.2 (contract) sandbox runner + fuzzed parsers — commit: ______
- [ ] 6.3 ⟂ qfind adapter (TIMEOUT≠UNSAT) — commit: ______
- [ ] 6.4 ⟂ rlifesrc adapter — commit: ______
- [ ] 6.5 ⟂ LLS adapter (SAT + GoE preimage) — commit: ______
- [ ] 6.6 ikpx2 stub (NO_CAPABILITY) — commit: ______
- [ ] 6.7 (integration) adapter conformance suite — commit: ______

### Phase 7 — Campaign, budget ledger, baselines, statistics
- [ ] 7.1 campaign config (frozen spec) — commit: ______
- [ ] 7.2 budget ledger + hard stops — commit: ______
- [ ] 7.3 IID + SCS baselines (same gate, equal budget) — commit: ______
- [ ] 7.4 CIs + e-value/FDR discovery-time correction — commit: ______

### Phase 8 — Strategy archive + failure memory + reference battery
- [ ] 8.1 fixed reference battery (reachable + UNSAT) — commit: ______
- [ ] 8.2 strategy archive (DGM parent-select; credit correct UNSAT) — commit: ______
- [ ] 8.3 distilled failure memory — commit: ______

### Phase 9 — MCP bridge (immutability enforcement)
- [ ] 9.1 bridge read/append tools — commit: ______
- [ ] 9.2 adversarial immutability tests **(release blocker)** — commit: ______

### Phase 10 — Claude Code agent frontend
- [ ] 10.1 lifeseek SKILL.md (staged loop; forbidden actions) — commit: ______
- [ ] 10.2 subagents (strategist/search-runner/verifier-caller/analyst) — commit: ______
- [ ] 10.3 async redirect/chat + sync checkpoints — commit: ______
- [ ] 10.4 (integration) end-to-end campaigns (re-derive known; directed; no-capable-engine; baselines) — commit: ______

### Phase 11 — End-to-end validation, reproduce, docs
- [ ] 11.1 CLI (run/report/retarget/reproduce) — commit: ______
- [ ] 11.2 bitwise `reproduce` in CI **(release blocker)** — commit: ______
- [ ] 11.3 re-aim demo (edit YAML → new campaign, no code change) — commit: ______
- [ ] 11.4 README + tutorial + SPEC §14 acceptance criteria all green — commit: ______

### Phase 12 — (LATER) Anthropic-API unattended runner
- [ ] 12.1 runner stub + smoke test — commit: ______

---

## SPEC §14 acceptance criteria (final sign-off — tick when demonstrably true)
- [ ] 1. lifecore suite green: differential, golden (glider/blinker), adversarial gate, symmetry suite.
- [ ] 2. `capable_engines` returns `no-capable-engine` for oblique-ship/gun (no false "not found").
- [ ] 3. E2E re-derives a known object (PASS + KNOWN) AND a directed search runs to a typed outcome w/ provenance.
- [ ] 4. IID/SCS baselines at equal budget with CIs appear in the report.
- [ ] 5. MCP immutability adversarial test (relaxation attempt) blocked.
- [ ] 6. `lifeseek reproduce <id>` bitwise-replays an accepted discovery in CI.
- [ ] 7. Re-aim demo: editing spec YAML starts a new campaign with no code changes.

---

## Decisions log (append-only; record every deviation from the plan + why)
- _(none yet)_

## Blockers (open; clear with resolution + date)
- _(none yet)_

## Session log (one line per work session: date · who · phase/tasks touched · ending commit)
- _(none yet)_
