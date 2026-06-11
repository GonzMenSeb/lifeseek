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
**Phase 2 · Task 2.1 — base TargetSpec + hashing + YAML (contract).** Phase 1 complete & green.

## HANDOFF NOTE (rewrite before every stop)
- **Just did:** Phase 1 complete — Pattern+RLE (1.1), numpy reference sim (1.2, lifelib-free), lifelib
  backend (1.3), differential harness (1.4, 120 soups agree). Full suite green, ruff+mypy clean.
- **Doing next:** Phase 2 Task 2.1 (contract) base TargetSpec (pydantic frozen) + deterministic hashing + YAML io.
- **Half-done / careful:** 2.1 is the frozen contract for 2.2–2.4. Spaceship pop/bbox are POST-HOC filters,
  never engine inputs (SPEC §4.1) — enforce in 2.2.
- **Resume command:** `cd <worktree> && uv run pytest -q && cat docs/lifeseek/PROGRESS.md && git log --oneline -8`
- **Open questions for the human:** engine source SHAs (qfind/rlifesrc/LLS) still TODO-CONFIRM in
  tools/versions.lock — only needed for real Phase 6 engine builds, not the core.

---

## Environment / invariants checklist (verify once, re-verify if they change)
- [ ] `uv` env builds from `uv.lock`; `pytest`, `ruff`, `mypy` run clean.
- [x] `python-lifelib` importable (lifelib extra, py3.12); engine binaries: Containerfile stubbed (Phase 6).
- [~] **INVARIANT:** reference path verified lifelib-free via AST guard test (Phase 3 wires verifier.py).
- [ ] **INVARIANT:** producer (lifelib) and verifier (numpy) share no simulation code; novelty uses an
      independent cross-check canonicalizer for accepted discoveries.
- [ ] **INVARIANT:** spec/verifier/novelty/budget are read-only through the MCP bridge (no setters).

---

## Phase checklist

### Phase 0 — Scaffold, env lock, progress artifact
- [x] 0.1 Repo + tooling — commit: f263232
- [x] 0.2 Containerfile + version pins — commit: 3a3c95e
- [x] 0.3 Instantiate PROGRESS.md — commit: (this commit)  **Phase 0 complete.**

### Phase 1 — Pattern model + dual simulators + differential harness  *(bedrock; gates Phase 2)*
- [x] 1.1 (contract) Pattern + RLE io — commit: (this commit)
- [x] 1.2 ⟂A NumPy reference simulator (verifier path; no lifelib) — commit: (this commit)
- [x] 1.3 ⟂B lifelib HashLife backend — commit: (this commit)
- [x] 1.4 (integration) lifelib↔numpy differential harness — commit: (this commit)  **Phase 1 complete; Phase 2 unblocked.**

### Phase 2 — Target spec + capability map + hashing
- [x] 2.1 (contract) base spec + hashing + YAML — commit: (this commit)
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
- **0.1 / tooling config consolidated into `pyproject.toml`** instead of separate `ruff.toml` + `mypy.ini`.
  Why: single source of truth, avoids config drift; ruff/mypy both read `[tool.*]` from pyproject. Same strictness.
- **0.1 / Python pinned to 3.12** (`.python-version`), not bare 3.11. Why: best wheel coverage for numpy 2.x and
  clean `python-lifelib` 2.5.6 build (verified importing + loading b3s23). `requires-python = >=3.11` kept.
- **0.1 / added `pyyaml` to core deps** (spec YAML io, Phase 2) and split heavy/build-sensitive backends
  (`python-lifelib`, `python-sat`, `mcp`) into optional extras so the deterministic numpy core always installs.
- **0.1 / `python-lifelib` confirmed working on 3.12** — JIT-compiles a shared object (~25s) on first rule load;
  locked into the `lifelib` extra. Removes the main external-build risk for Phase 1 lane-B.
- **1.3 / DOC ERROR corrected: block apgcode is `xs4_33`, not `xs4_252`** as written in SPEC §/PLAN 1.3 & 4.1.
  lifelib (the authoritative canonicalizer) is ground truth; tests assert `xs4_33`. Apply the same correction
  when implementing the novelty canonical cross-check (Task 4.1) and any golden fixtures.
- **1.1 / `bbox` of an empty Pattern returns `(0,0,-1,-1)`** so `width`/`height` compute to 0 cleanly
  (avoids a None branch in the verifier's residual logic).

## Blockers (open; clear with resolution + date)
- _(none yet)_

## Session log (one line per work session: date · who · phase/tasks touched · ending commit)
- 2026-06-11 · Claude (subagent-driven exec) · Phase 0 (0.1–0.3) scaffold/env/tracker · ending 9115794
- 2026-06-11 · Claude (subagent-driven exec) · Phase 1 (1.1–1.4) sim bedrock + differential · ending cab6f02 → (1.4 commit)
