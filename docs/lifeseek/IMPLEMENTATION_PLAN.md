# lifeseek v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL — use `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
> **Read `SPEC.md` (source of truth) and `PROGRESS.md` (live state) before doing anything.**

**Goal:** Build `lifeseek` v1 — a directed, re-aimable Conway's-Game-of-Life discovery harness whose deterministic
OSS core accepts a pattern as a discovery only when it is spec-met ∧ independently-verified ∧ novel, driven by a
Claude agent layer that can never self-certify.

**Architecture:** Two layers + an immutability-enforcing MCP bridge (see `SPEC.md §3`). Layer 1 `lifecore`
(deterministic, LLM-free Python) holds the simulator, typed target spec, engine adapters, verifier, novelty
oracle, provenance store, budget/baseline harness, strategy archive, and sandbox. Layer 2 is the Claude Code
skill + subagents.

**Tech Stack:** Python 3.11+, `uv` (env+lock), `pydantic` v2 (specs), `numpy` (reference sim + analysis),
`python-lifelib` (HashLife backend/canonicalization — *backend only*), `pysat`/LLS, external OSS binaries
(`qfind`, `rlifesrc`, `LLS`, `ikpx2`-stub), `sqlite3`, `requests` (Catagolue via proxy), `bubblewrap`+`seccomp`
(sandbox), `pytest`+`hypothesis` (tests/fuzz), `mcp` (bridge). All Life tooling OSS; brain = Claude.

---

## How to use this plan (READ FIRST)

1. **Every task follows the TDD micro-cycle** (writing-plans discipline): write the failing test → run it, see it
   fail → minimal implementation → run it, see it pass → commit. Where a task lists "Test spec" instead of full
   code, write those exact tests first; where full code is given, use it.
2. **Progress tracking is mandatory.** `PROGRESS.md` is the single source of "where we are". At the **start of
   every session** read it; after **every task** update it (check the box, paste the commit hash, log decisions);
   before **stopping** write a handoff note. The plan is designed so any fresh session can resume from `PROGRESS.md`
   alone. Never rely on conversation memory for state.
3. **Parallelization.** Phases are mostly sequential (dependency-ordered). **Within** a phase, tasks marked
   `⟂PARALLEL[lane]` are independent and SHOULD be dispatched to concurrent subagents once that phase's
   **contract task** (the ABC / data model / test harness it depends on) is committed. Parallel lanes in the same
   phase share no files. After parallel lanes land, run the phase's **integration task** sequentially.
4. **Commit discipline:** small, frequent, conventional commits; one logical change per commit; never commit
   red tests. Each task ends in a commit.
5. **Definition of done per task:** its tests pass, `ruff` + `mypy` clean, `PROGRESS.md` updated, committed.

---

## File structure (locked decomposition)

```
lifeseek/                      # repo root (git)
  pyproject.toml  uv.lock  ruff.toml  mypy.ini  .pre-commit-config.yaml
  Containerfile                # pinned image for engines + reproduce
  docs/lifeseek/{SPEC,IMPLEMENTATION_PLAN,PROGRESS}.md
  src/lifecore/
    sim/{pattern.py, lifelib_engine.py, reference.py, rle.py}
    targetspec/{models.py, yaml_io.py, hashing.py, capability.py}
    engines/{base.py, qfind.py, rlifesrc.py, lls.py, ikpx2.py}
    verify/{verifier.py, gate.py, records.py}
    novelty/{canonical.py, catagolue.py, mdl.py, symmetry_suite.py}
    store/{db.py, schema.sql, recipe.py, resume.py}
    campaign/{campaign.py, budget.py, baseline.py, stats.py}
    strategy/{archive.py, battery.py, failure_memory.py}
    sandbox/{runner.py, parsers.py}
    cli.py                     # `lifeseek` entrypoint (run, reproduce, retarget, report)
  src/lifeseek_mcp/server.py   # MCP bridge (immutability enforcement)
  agent/                       # Claude Code skill + subagents (see Phase 10)
    skills/lifeseek/SKILL.md
    subagents/{strategist.md, search_runner.md, verifier_caller.md, analyst.md}
  tests/                       # mirrors src/ ; fixtures/ has RLEs + a frozen Catagolue snapshot
  benchmarks/                  # baseline runs, cost/accuracy frontier outputs
```

---

## Phase 0 — Scaffold, environment lock, progress artifact
*Goal: a reproducible skeleton + the tracking system. Sequential (foundational).*

### Task 0.1: Repo + tooling
- Files: `pyproject.toml`, `uv.lock`, `ruff.toml`, `mypy.ini`, `.pre-commit-config.yaml`, `src/lifecore/__init__.py`.
- [ ] `git init`; create the `src/` tree above (empty `__init__.py`s).
- [ ] `uv init`; add deps (pydantic, numpy, python-lifelib, pysat, requests, pytest, hypothesis, mcp); `uv lock`.
- [ ] Configure ruff + mypy (strict) + pre-commit (ruff, mypy, pytest -q on changed).
- [ ] Add a trivial `tests/test_smoke.py::test_import` that imports `lifecore`; run `pytest` → PASS.
- [ ] Commit: `chore: scaffold lifeseek project, tooling, lockfile`.

### Task 0.2: Containerfile + version pins (env lock foundation)
- Files: `Containerfile`, `tools/versions.lock` (engine commit SHAs + build flags).
- [ ] Pin base image by digest; document build steps for qfind/rlifesrc/LLS (cloned at fixed SHAs). Do not build them yet.
- [ ] Commit: `chore: pin container image and engine versions`.

### Task 0.3: Instantiate `PROGRESS.md`
- Files: `docs/lifeseek/PROGRESS.md` (copy the template already in this repo if present; else create from the
  structure in §"Progress protocol" below).
- [ ] Fill the phase/task checklist mirroring this plan; mark Phase 0 in-progress.
- [ ] Commit: `docs: add implementation progress tracker`.

---

## Phase 1 — Pattern model + dual simulators + differential harness  ← **bedrock of trust**
*Goal: two independent simulators that agree, plus the RLE/pattern primitives. `⟂PARALLEL` after Task 1.1.*

### Task 1.1 (contract): `Pattern` data model + RLE I/O
- Files: Create `src/lifecore/sim/pattern.py`, `src/lifecore/sim/rle.py`; Test `tests/sim/test_pattern.py`.
- [ ] **Failing test** (`tests/sim/test_pattern.py`):
```python
from lifecore.sim.pattern import Pattern
from lifecore.sim.rle import parse_rle, to_rle
def test_glider_roundtrip():
    g = "bob$2bo$3o!"                      # canonical glider RLE
    p = parse_rle(g, rule="B3/S23")
    assert p.population == 5
    assert p.bbox == (0, 0, 2, 2)          # (xmin,ymin,xmax,ymax)
    assert parse_rle(to_rle(p)).cells == p.cells
def test_translate_and_eq():
    p = parse_rle("bob$2bo$3o!")
    assert p.translate(10, -3).translate(-10, 3).cells == p.cells
```
- [ ] Run → FAIL. Implement `Pattern` (immutable frozenset of `(x,y)`; `rule`; `population`, `bbox`, `translate`,
  `normalize`, `__eq__`/`__hash__`) and a strict RLE parser/writer. Run → PASS. `ruff`+`mypy`. Commit
  `feat(sim): pattern model + RLE io`. **This is the contract for Tasks 1.2–1.4 — do not change after they start.**

### Task 1.2 ⟂PARALLEL[lane-A]: NumPy reference simulator (the verifier path)
- Files: Create `src/lifecore/sim/reference.py`; Test `tests/sim/test_reference.py`. **MUST NOT import lifelib.**
- [ ] **Test spec** (write these first): `step(pattern, n)` evolves B3/S23 exactly on a bounded NumPy grid sized
  to fit growth; `test_blinker_period_2`, `test_block_still_life`, `test_glider_moves_1_1_per_4`
  (after 4 gens the glider equals `gen0.translate(1,1)`), `test_rule_param` (passing `B36/S23` HighLife changes
  outcome on a replicator seed). Edge: grid auto-expands so nothing clips.
- [ ] Implement (convolution-based neighbor count; rule parsed from `Bxx/Sxx`). Run → PASS. Commit
  `feat(sim): independent numpy reference simulator`.

### Task 1.3 ⟂PARALLEL[lane-B]: lifelib (HashLife) backend wrapper (producer + canonicalize)
- Files: Create `src/lifecore/sim/lifelib_engine.py`; Test `tests/sim/test_lifelib_engine.py` (skip if lifelib
  absent, but CI installs it).
- [ ] **Test spec:** `evolve(pattern, n)` matches reference on glider/blinker; `apgcode(pattern)` returns the known
  apgcodes (`xq4_153` glider, `xp2_7` blinker, `xs4_252` block); `fast_forward(pattern, big_n)` works via HashLife.
- [ ] Implement thin wrapper over `python-lifelib`. Run → PASS. Commit `feat(sim): lifelib hashlife backend`.

### Task 1.4 (integration): differential test harness  ← release-relevant
- Files: Create `tests/sim/test_differential.py`.
- [ ] **Test** (hypothesis-driven): for N random soups in a kxk box, `reference.step(p, t) == lifelib.evolve(p, t)`
  (compare as normalized cell sets) for t in a range. Any disagreement is a hard failure (a shared-bug detector).
```python
from hypothesis import given, strategies as st
@given(seed=st.integers(0, 2**31), k=st.integers(4, 12), t=st.integers(1, 32))
def test_reference_matches_lifelib(seed, k, t):
    p = random_soup(seed, k, rule="B3/S23")
    assert reference.step(p, t).normalize().cells == lifelib_engine.evolve(p, t).normalize().cells
```
- [ ] Run → PASS. Commit `test(sim): lifelib vs numpy differential harness`. **Gate:** Phase 2 may not start until green.

---

## Phase 2 — Target spec (mechanism-faithful) + capability map + hashing
*Goal: the typed, re-aimable, frozen spec. `⟂PARALLEL` per object type after Task 2.1.*

### Task 2.1 (contract): base spec + hashing + YAML
- Files: Create `src/lifecore/targetspec/models.py` (base + enums), `hashing.py`, `yaml_io.py`;
  Test `tests/targetspec/test_base.py`.
- [ ] **Test spec:** `TargetSpec` base carries `rule="B3/S23"`, `kind`, `notes`; `spec_id = sha256(canonical_json)`
  is stable across key-order and equals after YAML round-trip; `freeze()` returns an immutable copy whose mutation
  raises. `test_yaml_roundtrip`, `test_spec_id_stable`, `test_frozen_is_immutable`.
- [ ] Implement with pydantic v2 (`model_config = ConfigDict(frozen=True)`), canonical JSON for hashing. Commit
  `feat(targetspec): base spec, deterministic hashing, yaml io`.

### Task 2.2 ⟂PARALLEL[lane-A]: Spaceship spec (the subtle one — see SPEC §4.1)
- Files: Create `src/lifecore/targetspec/models.py` (extend); Test `tests/targetspec/test_spaceship.py`.
- [ ] **Test spec:** `Spaceship(displacement=(dx,dy), period=p, symmetry_class, search_width=(w_min,w_max),
  population_range=None, bbox_max=None)`. Derived `slope`/`velocity` computed correctly
  (`(2,0)/4 → c/2 orthogonal`, `(1,1)/4 → c/4 diagonal`, `(2,1)/p → oblique`). Validation: `gcd(dx,dy,p)` sanity,
  reject `w_min>w_max`; population/bbox are **post-hoc filter fields**, asserted *not* present in
  `engine_params()`. `test_slope_classification`, `test_population_is_postfilter_not_engine_input`.
- [ ] Implement. Commit `feat(targetspec): mechanism-faithful spaceship spec`.

### Task 2.3 ⟂PARALLEL[lane-B]: Oscillator (mechanism-split) + StillLife specs; LATER-type stubs
- Files: extend `models.py`; Test `tests/targetspec/test_oscillator_stilllife.py`.
- [ ] **Test spec:** `Oscillator(period, mechanism ∈ {low_period_direct, hassler_catalyst, period_multiplier,
  signal_loop_conduit}, bbox_max, symmetry)`; `StillLife(bbox_max, population_range, symmetry)`. `Gun/Puffer/Rake/
  Eater` exist as schema-only stubs. `test_oscillator_mechanism_enum`, `test_stub_types_constructible`.
- [ ] Commit `feat(targetspec): oscillator/still-life specs + later-type stubs`.

### Task 2.4 (integration): capability map  ← kills the "silent not-found" failure
- Files: Create `src/lifecore/targetspec/capability.py`; Test `tests/targetspec/test_capability.py`.
- [ ] **Test spec:** `capable_engines(spec) -> list[EngineId]`. Spaceship orthogonal/diagonal → `[qfind, rlifesrc]`;
  oblique → `[ikpx2]`; low_period oscillator/still-life → `[rlifesrc, lls]`; gun/puffer/eater → `[]`. A `[]` result
  means the campaign returns `no-capable-engine`. `test_oblique_routes_to_ikpx2`, `test_gun_returns_no_capability`.
- [ ] Commit `feat(targetspec): engine capability map`.

---

## Phase 3 — Verification gate (crown jewel)  ← SPEC §5
*Goal: closed-world, type-specific, independent verifier on the NumPy path. `⟂PARALLEL` per type after Task 3.1.*

### Task 3.1 (contract): universal moving/periodic verifier + record
- Files: Create `src/lifecore/verify/verifier.py`, `src/lifecore/verify/records.py`; Test
  `tests/verify/test_universal.py`. **Imports `sim/reference.py` ONLY (assert no lifelib import).**
- [ ] **Failing test:**
```python
from lifecore.verify.verifier import verify
from lifecore.targetspec.models import Spaceship
def test_glider_passes_as_c4_diagonal():
    spec = Spaceship(displacement=(1,1), period=4, symmetry_class="glide_reflect", search_width=(1,5))
    rec = verify(parse_rle("bob$2bo$3o!"), spec)
    assert rec.verdict == "PASS"
    assert rec.residual_cell_count == 0
    assert rec.observed_period == 4 and rec.observed_displacement == (1,1)
def test_debris_leaker_rejected():
    # a glider with an extra distant blinker that desyncs -> residual != 0 after period
    rec = verify(glider_plus_far_blinker(), Spaceship((1,1),4,"glide_reflect",(1,8)))
    assert rec.verdict == "REJECT" and rec.residual_cell_count > 0
def test_uses_reference_path_only():
    import lifecore.verify.verifier as v, sys
    assert "lifelib" not in v.__dict__.get("__imports__", "")  # enforced via an import-guard test helper
```
- [ ] Implement the universal protocol (SPEC §5.1): empty-field embed with margin `M`, settling `T_settle`,
  exact-image-at-period check, **empty-residual assertion**, **true-period (min period, ≥1 full-period cell)**.
  Produce signed `VerificationRecord` (SPEC §5.3). Run → PASS. Commit `feat(verify): universal closed-world verifier`.
  **Contract frozen for 3.2–3.4.**

### Task 3.2 ⟂PARALLEL[lane-A]: oscillator-specific checks
- Files: extend `verifier.py`; Test `tests/verify/test_oscillator.py`.
- [ ] **Test spec:** rotor/stator computed; `test_blinker_p2_passes`; `test_trivial_lcm_rejected` (two far-apart
  blinker+pentadecathlon mislabeled as one p30 oscillator → REJECT, because no single cell oscillates at p30 and
  components are separable); minimal-period enforced.
- [ ] Commit `feat(verify): oscillator rotor/stator + true-period`.

### Task 3.3 ⟂PARALLEL[lane-B]: still-life + GoE/non-existence protocol
- Files: extend `verifier.py`; Test `tests/verify/test_stilllife_goe.py`.
- [ ] **Test spec:** `test_block_is_stable`; **GoE**: a non-existence/"no such object" verdict requires an orphan
  witness from a thickness-≥4 padded preimage (`test_goe_requires_orphan_witness`); a single small-box UNSAT must
  NOT produce a non-existence verdict (`test_smallbox_unsat_is_not_nonexistence`).
- [ ] Commit `feat(verify): still-life stability + rigorous GoE protocol`.

### Task 3.4 (integration): acceptance gate + adversarial golden suite  ← release blocker
- Files: Create `src/lifecore/verify/gate.py`; Test `tests/verify/test_gate_adversarial.py`.
- [ ] **Test spec (all must hold):** junk pattern → REJECT; known object mislabeled with wrong period → REJECT;
  debris-leaker → REJECT; trivial-LCM → REJECT; real glider/blinker/block → PASS. `gate.accept()` requires
  `verifier PASS ∧ novelty NOVEL` and has **no setters**. `test_gate_has_no_mutation_api`.
- [ ] Commit `feat(verify): acceptance gate + adversarial golden suite`. **Gate: Phase 4 may start in parallel
  with Phase 5+ but novelty (Phase 4) is required before the gate's `novelty` arm is live.**

---

## Phase 4 — Novelty oracle (two-tier, fail-closed)  ← SPEC §6
*`⟂PARALLEL` across canonical/catagolue/mdl after a shared `NoveltyResult` type.*

### Task 4.0 (contract): `NoveltyResult` + status enum. Commit `feat(novelty): result types`.
### Task 4.1 ⟂PARALLEL: `canonical.py` — apgcode via lifelib + independent cross-check canonicalizer.
  Test: glider→`xq4_153`, block→`xs4_252`; the independent canonicalizer agrees on accepted set.
### Task 4.2 ⟂PARALLEL: `catagolue.py` — query a **frozen local snapshot** (fixture) first; live refresh via proxy;
  **network failure → `UNCERTAIN`** (`test_network_failure_is_uncertain_not_novel`); snapshot hash recorded.
### Task 4.3 ⟂PARALLEL: `mdl.py` — connected-component decomposition; `test_known_plus_far_blinker_is_DERIVATIVE`;
  compressive-vs-nearest-known check.
### Task 4.4 (integration, **release blocker**): `symmetry_suite.py` — all 8 dihedral images × phases × random
  translations of each catalog object canonicalize to the **same** apgcode and flag KNOWN. Commit
  `test(novelty): symmetry soundness suite (release blocker)`.

---

## Phase 5 — Store, provenance, recipe, crash-safe resume  ← SPEC §9
### Task 5.1: `schema.sql` + `db.py` — append-only event log (campaign→run→candidate→verification→novelty→
  acceptance); inserts only, no updates/deletes (`test_store_is_append_only`).
### Task 5.2: `recipe.py` — reproducible recipe object capturing all SPEC §9 fields.
### Task 5.3: `resume.py` — idempotency keys per step; checkpoint-after-side-effect; `test_resume_no_double_write`,
  `test_resume_no_repaid_claude_call` (mock). Commit per task.

---

## Phase 6 — Sandbox + engine adapters  ← SPEC §4.3, §10  *(highest external-dependency risk)*
*`⟂PARALLEL` one agent per engine after Tasks 6.1–6.2.*

### Task 6.1 (contract): `engines/base.py` — `EngineAdapter` ABC, `EngineOutcome`, `RawResult`, `Candidate`
  (exactly as SPEC §4.3). Commit `feat(engines): adapter contract`.
### Task 6.2 (contract): `sandbox/runner.py` + `sandbox/parsers.py` — bubblewrap/seccomp/cgroup wrapper
  (`run(cmd, limits) -> CompletedProc`), no network; fuzz-tested RLE/apgcode parser (`hypothesis` on malformed
  input never crashes, never yields invalid Pattern). Commit `feat(sandbox): isolated runner + fuzzed parsers`.
### Task 6.3 ⟂PARALLEL[qfind]: `engines/qfind.py` — build_input from Spaceship (width, slope→orthogonal/diagonal),
  run sandboxed, parse; **TIMEOUT≠UNSAT**; integration: find a known c/2 orthogonal ship at small width.
### Task 6.4 ⟂PARALLEL[rlifesrc]: `engines/rlifesrc.py` — low-period oscillators/still-lifes; find blinker/block.
### Task 6.5 ⟂PARALLEL[lls]: `engines/lls.py` — SAT still-life + exists-in-bbox + padded GoE preimage.
### Task 6.6: `engines/ikpx2.py` — **stub** returning `NO_CAPABILITY` with a clear message + interface for LATER.
### Task 6.7 (integration): adapter conformance suite — every adapter honors the ABC, returns typed outcomes,
  never raises on UNSAT/TIMEOUT, round-trips a known search. Commit `test(engines): adapter conformance`.

---

## Phase 7 — Campaign, budget ledger, baselines, statistics  ← SPEC §8
### Task 7.1: `campaign/campaign.py` — `Campaign = frozen(spec) + engine_policy + budget + checkpoints`; spec hashed.
### Task 7.2: `campaign/budget.py` — ledger (Claude $/tokens, engine CPU-s, replan count) with **hard stops**
  (`test_budget_hard_stop_raises`).
### Task 7.3: `campaign/baseline.py` — IID-random + SCS samplers through the **same gate** at equal budget.
### Task 7.4: `campaign/stats.py` — 95% CIs + e-value/FDR discovery-time correction scaling with gate-query count;
  `test_range_target_must_be_strictly_inside`. Commit per task.

---

## Phase 8 — Strategy archive + failure memory + reference battery  ← SPEC §7
### Task 8.1: `strategy/battery.py` — ~10–20 fixed specs, each tagged known-reachable or known-UNSAT (with sources).
### Task 8.2: `strategy/archive.py` — typed append-only archive; DGM parent-selection `score×1/(1+children)`;
  meta-utility = verified-novel-per-budget, **crediting correct UNSAT** (`test_unsat_on_impossible_is_credited`).
### Task 8.3: `strategy/failure_memory.py` — distilled dead-ends; `get_relevant(spec)` returns prior UNSAT envelopes.
  Commit per task.

---

## Phase 9 — MCP bridge (immutability enforcement)  ← SPEC §11  *(safety-critical)*
### Task 9.1: `lifeseek_mcp/server.py` — expose read/append tools (SPEC §11). No setters on spec/gate/budget.
### Task 9.2 (**release blocker**): adversarial immutability tests — a Strategist call that tries to widen
  bbox/population/symmetry/width, mutate the gate, or reinterpret `UNCERTAIN`→`NOVEL` is **rejected**
  (`test_relaxation_attempt_blocked`, `test_retarget_requires_human_checkpoint`). Commit
  `feat(mcp): bridge + enforced immutability (+ adversarial tests)`.

---

## Phase 10 — Claude Code agent frontend  ← SPEC §12
### Task 10.1: `agent/skills/lifeseek/SKILL.md` — when to use; the staged loop (feasibility→tune→deep→verify);
  how to call the MCP tools; **forbidden actions** (never touch the gate; always route accept through the core).
### Task 10.2: subagents `strategist.md` (spec/policy via capability map + failure memory + strategy archive;
  UCB/diverse-restart; width-escalation), `search_runner.md`, `verifier_caller.md` (requests gate, never decides),
  `analyst.md` (characterize, RLE, Elo-rank multiple accepted candidates).
### Task 10.3: async intervention hooks (`redirect`/`chat`) + synchronous checkpoint handling.
### Task 10.4 (integration): end-to-end campaigns —
  (a) **re-derive a known object** → verifier PASS, novelty **KNOWN** (proves loop+novelty);
  (b) a **genuinely directed search** to a typed outcome with full provenance;
  (c) **`no-capable-engine`** path for an oblique/gun spec;
  (d) **baselines** present in the report. Commit per task.

---

## Phase 11 — End-to-end validation, reproduce, docs
### Task 11.1: `cli.py` — `lifeseek run <campaign.yaml>`, `report <campaign>`, `retarget <campaign> <new.yaml>`,
  `reproduce <discovery_id>`.
### Task 11.2 (**release blocker**): `reproduce` asserts **bitwise-identical** replay of an accepted discovery's
  acceptance pipeline; wire into CI nightly.
### Task 11.3: **re-aim demo** — edit a campaign YAML, run, confirm a new campaign with zero code changes.
### Task 11.4: `README.md` + a "first campaign" tutorial; final pass over SPEC §14 acceptance criteria — every item
  green. Commit `docs: v1 complete; acceptance criteria green`.

---

## Phase 12 (LATER, stub only) — Anthropic-API unattended runner
- `src/lifeseek_runner/` driving the **same** MCP tools via the Agent SDK; async checkpoint queue. Interface
  + a smoke test only in v1.

---

## Parallelization summary (for the orchestrating session)
Dispatch concurrent subagents **within** a phase only after its contract task is committed:
- Phase 1: lane-A `reference.py`, lane-B `lifelib_engine.py` (after 1.1) → integrate 1.4.
- Phase 2: lane-A spaceship, lane-B oscillator/still-life (after 2.1) → integrate 2.4.
- Phase 3: lane-A oscillator-verify, lane-B still-life/GoE-verify (after 3.1) → integrate 3.4.
- Phase 4: canonical / catagolue / mdl in parallel (after 4.0) → integrate 4.4.
- Phase 6: qfind / rlifesrc / lls in parallel (after 6.1–6.2) → integrate 6.7.
Everything else is sequential (dependency-bound). **Two-stage review** between tasks (per
`subagent-driven-development`): (1) does it meet the task's tests + acceptance? (2) does it honor the frozen
contract and SPEC principles (esp. the verifier-independence and immutability invariants)?

---

## Progress protocol (mandatory) — see `PROGRESS.md`
`PROGRESS.md` is the **only** durable record of state. Its contract:
- A checkbox per phase and per task, mirroring this plan.
- A **"⮕ CURRENT POSITION"** marker on the exact task in progress.
- A **decisions log** (any deviation from the plan + rationale), a **blockers** list, and per-task **commit hash**.
- A **"HANDOFF NOTE"** block rewritten before every stop: what was just done, what's next, any half-done state,
  and the exact command to resume.
Rule: **update `PROGRESS.md` in the same commit as the task it describes.** A fresh session must be able to resume
using `PROGRESS.md` + git history alone, with no conversation context.
