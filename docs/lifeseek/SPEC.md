# lifeseek — v1 Specification (source of truth)

> Status: **approved design, ready to implement**. Date: 2026-06-11.
> This document is the *what & why*. The *how & in what order* lives in `IMPLEMENTATION_PLAN.md`.
> Live build state lives in `PROGRESS.md` (read it first every session).

`lifeseek` is a **directed, re-aimable scientific-discovery harness for Conway's Game of Life (B3/S23)**.
You hand it a typed **target specification**; it runs steered, budget-bounded search campaigns that wrap
open-source Life engines; a result is accepted as a **discovery** only when it is **spec-met ∧ independently
re-simulation-verified ∧ novel** vs known catalogs. Editing the target spec re-aims the entire effort.

This spec was hardened by an adversarial, literature-grounded review panel (6 lenses over the project's
`papers/Scientific Discovery Agents/` knowledge base). Every non-obvious decision below cites the finding
that drives it. The panel's headline: the two-layer trust architecture is correct; the domain model,
verification predicate, and self-revision mechanisms needed to be made faithful and enforceable. They are, here.

---

## 1. Non-negotiable principles (the trust architecture)

1. **The agent never self-certifies.** All acceptance logic lives in a deterministic, LLM-free core
   (`lifecore`). Claude proposes; the core disposes. *(Huang et al., "LLMs Cannot Self-Correct Reasoning Yet";
   "When Tree Search Helps — it depends on the discriminator".)*
2. **Verification is by an independent code path.** The spec-compliance re-simulation MUST run on the
   NumPy **reference** simulator, never a second invocation of the producing engine (lifelib). Canonicalization
   for accepted discoveries is cross-checked by an independent canonicalizer. *(Lange et al., "AI CUDA Engineer":
   agents produced fake 50–120× kernels that passed a single-path verifier.)*
3. **Closed-world, type-specific acceptance.** Loophole exploitation lives in an under-specified predicate.
   The verifier embeds each candidate in an empty field with margin, asserts an **empty residual set**
   (kills debris/clipping loopholes), checks **true period** (not a trivial LCM), and applies **object-type-specific**
   logic. *(Lange et al.; Wang & Buehler, categorical MDL gate.)*
4. **Fail-closed novelty.** Unknown/unreachable catalog ⇒ `novelty-uncertain`, never silent "novel".
   *(Huang et al. POPPER Type-I control; Kapoor et al., "AI Agents That Matter".)*
5. **The gate is structurally immutable from the agent side.** The target spec, verifier, novelty test,
   and budget caps are hashed/signed at campaign start and exposed read-only through the MCP bridge with no
   setters. Textual "do not change" is empirically insufficient. *(Zelikman et al., STOP: models disabled a
   sandbox 0.46% of the time **despite** a textual warning.)*
6. **Provenance is append-only and reproducible.** Every accepted discovery carries a recipe that replays
   bitwise on the deterministic pipeline. *(Kapoor et al.; categorical provenance graph.)*
7. **No agentic cleverness ships unless it beats simple baselines at equal budget.**
   *(Gideoni et al., "Simple Baselines are Competitive with Code Evolution".)*

---

## 2. User-locked requirements (from brainstorming)

| Dimension | Decision |
|---|---|
| Mode | **Directed target search**, re-aimable by editing the spec. Open-ended/QD is LATER. |
| Rule | **B3/S23 now**, rule is a swappable parameter (a rule change is a *regime change* — verifier claims are scoped to the declared rule). |
| Autonomy | **Steered campaigns** with human checkpoint/accept gates (+ async redirect). |
| Build | **Hybrid**, wrapping **only open-source** Life tooling. |
| Brain | **Claude** via Claude Code subscription (primary) and/or Anthropic API (optional runner). Brain need not be OSS. |
| Target spec | **Typed object catalog** with mechanism-faithful, per-type params. |
| Accept bar | **Spec-met ∧ re-sim-verified ∧ novel** (+ MDL minimality tier). |

---

## 3. Architecture (two layers + bridge)

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 2 — Claude agent frontends  (the "smart" layer; never certifies)│
│  • Claude Code: skill `lifeseek` + subagents                          │
│      Strategist · Search-runner · Verifier-caller · Analyst           │
│      staged progress-manager (feasibility→tune→deep→verify),          │
│      UCB/diverse-restart over a strategy tree, width-escalation        │
│  • (optional) Anthropic-API runner — same tools, unattended            │
└───────────────▲───────────────────────────────────────────────────────┘
                │  MCP bridge  (ENFORCES immutability: read-only spec/gate/budget,
                │               no setters, rejects relaxation, human-gated retarget)
┌───────────────┴───────────────────────────────────────────────────────┐
│ LAYER 1 — lifecore  (deterministic, OSS-only, NO LLM)                  │
│  sim/      pattern model + lifelib(HashLife) producer + NumPy reference │
│  targetspec/ mechanism-faithful typed spec + capability map + hashing   │
│  engines/  qfind · rlifesrc · LLS · ikpx2(stub)   (directed solvers)    │
│  verify/   closed-world, type-specific gate on the REFERENCE path       │
│  novelty/  apgcode canon + indep. cross-check · Catagolue(frozen) · MDL  │
│  store/    append-only SQLite provenance + reproducible recipe          │
│  campaign/ config + budget ledger + IID/SCS baselines                   │
│  strategy/ strategy archive (DGM parent-select) + failure memory        │
│  sandbox/  bubblewrap/seccomp/cgroups for wrapped binaries + fuzz parse  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why C (two-layer) over alternatives:** putting logic in Claude Code skills (option A) couples the verifier to
the agent runtime — contra principle 1 — and is hard to unit-test/reproduce; a pure API service (option B)
abandons the subscription constraint. C keeps a testable deterministic core and uses Claude as an
interchangeable frontend. Validated by all six review lenses.

---

## 4. The GoL domain model (corrected — highest-risk layer)

The review scored the original uniform model 5/10: it would feed `population`/`bbox` to engines that ignore them
and route impossible specs to incapable engines. The faithful model:

### 4.1 Target spec types (`lifecore/targetspec/`)
All specs share: `rule` (default `B3/S23`), `notes`, and serialize to/from **YAML** (the re-aim knob).
The spec is **hashed (`spec_id`) and frozen** at campaign start.

- **Spaceship**
  - `displacement: (dx, dy)`, `period: p` → derived `slope` and `velocity` (e.g. `(2,0)/p` = c/?? orthogonal).
  - `symmetry_class ∈ {asymmetric, bilateral_even, bilateral_odd, glide_reflect}` (glide-reflect = flipped copy at p/2).
  - `search_width: {w_min, w_max}` (the dominant cost lever; engine input, with escalation policy).
  - `population_range`, `bbox_max` are **post-hoc filters**, NOT engine inputs.
  - Routing: `slope` → engine formulation (orthogonal / diagonal / oblique). Oblique/knightships → `ikpx2`.
- **Oscillator** — split by **mechanism** (Strategist selects by period band):
  - `low_period_direct` (small p, direct search via rlifesrc/LLS),
  - `hassler_catalyst`, `period_multiplier`, `signal_loop_conduit` (assembly mechanisms — **v1 stubs**:
    schema + `no-capable-engine` return; real construction toolkits are LATER).
  - params: `period`, `bbox_max`, `symmetry`, optional `mechanism`.
- **StillLife** — `bbox_max`, `population_range`, `symmetry`. Engine: LLS (SAT) / rlifesrc.
- **Gun / Puffer / Rake / Eater** — **schema-only stubs in v1** (interaction verification + construction
  toolkits are LATER); selecting them returns `no-capable-engine` with a clear message.

### 4.2 Capability map (`targetspec/capability.py`)
A pure function `capable_engines(spec) -> [EngineId]`. If empty, the campaign returns **`no-capable-engine`** —
*never* an empty "not found". This single rule eliminates the most dangerous silent failure the panel found.

### 4.3 Engine roles (`lifecore/engines/`) — corrected
| Engine | OSS source | Role |
|---|---|---|
| **qfind** | github.com/Matthias-Merzenich/qfind | Primary spaceship search (orthogonal/diagonal), width-parameterized. |
| **rlifesrc** | github.com/AlephAlpha/rlifesrc (Rust port of lifesrc) | General backtracking: low-period oscillators, still-lifes, small ships. |
| **LLS** | github.com/OscarCunningham/logic-life-search | SAT: still-lifes, exists-in-bbox, **GoE preimage** (thickness ≥ 4 padding). |
| **ikpx2** | hatsya/lifelib ecosystem | Oblique / knightship / hard new velocities. **v1: adapter stub** (interface only). |
| **lifelib** | gitlab.com/apgoucher/lifelib (`python-lifelib`) | **Backend only**: HashLife evolution, canonicalization, soup census. **NOT a directed engine.** |
| **apgsearch / Catagolue** | conwaylife.com | **Census/novelty oracle only.** Not directed search. |

Adapter contract (`engines/base.py`):
```python
class EngineOutcome(Enum): FOUND; UNSAT; TIMEOUT; ERROR; NO_CAPABILITY
@dataclass(frozen=True)
class RawResult: outcome: EngineOutcome; patterns_rle: list[str]; stderr: str; meta: dict
class EngineAdapter(ABC):
    id: str
    def capabilities(self) -> CapabilitySet: ...
    def build_input(self, spec: TargetSpec, budget: EngineBudget) -> EngineConfig: ...   # may raise NoCapability
    def run(self, cfg: EngineConfig) -> RawResult: ...      # sandboxed; typed outcome, never raises on UNSAT/TIMEOUT
    def parse(self, raw: RawResult) -> list[Candidate]: ... # fuzz-tested parser; untrusted input
```
`TIMEOUT` and `UNSAT` are **distinct typed outcomes** — a timeout is *not* evidence of non-existence
(width-escalation policy must not misread it).

---

## 5. The verification gate (`lifecore/verify/`) — closed-world & type-specific

Runs on `sim/reference.py` (NumPy) **only**. Produces a signed `VerificationRecord`.

### 5.1 Universal protocol (all moving/periodic objects)
1. Embed candidate (gen 0) in an empty field with margin `M > max(|dx|,|dy|) * p + bbox_diag` (no clipping).
2. Declare a **settling policy**: `T_settle` (transient budget); the object's period is the **first exact
   recurrence after `T_settle`**; require **≥ 2 full periods** of confirmed recurrence.
3. At gen `p` (post-settle), require live cells to equal **exactly** the declared transform (translation by
   `(dx,dy)`; for glide-reflect, the flipped image at `p/2`) of gen-0 — and assert the **residual set is empty**
   (no stray/leaked/debris cells). Any residual ⇒ **REJECT** (this kills the bbox-clipping and reabsorbed-debris loopholes).
4. **True-period check:** confirm the *minimal* period equals the claimed `p` and that ≥ 1 cell genuinely
   oscillates at the full period (reject patterns whose "period" is a trivial LCM of sub-oscillators).

### 5.2 Per-type additions
- **Oscillator:** compute rotor/stator; reject still-life-equivalent (p=1) unless asked; confirm minimal period.
- **StillLife:** stability for ≥ T_settle + small perturbation-stability sanity (optional v1).
- **GoE / "no such object":** report a Garden of Eden / non-existence **only with an orphan witness** from a
  thickness-≥4 padded SAT preimage. Never infer non-existence from one small-box UNSAT.
- **Gun/Eater/Puffer/Rake (LATER):** interaction tests (output-stream periodicity; perturb-and-recover;
  intended-debris). v1 designs the hook but scopes these out.

### 5.3 `VerificationRecord` (signed; stored)
`{spec_id, rule, field_size, margin, T_settle, claimed_vs_observed_period, claimed_vs_observed_displacement,
residual_cell_count(=0 to pass), reference_sim_version_hash, producer_engine_version_hash, verdict, signature}`.

### 5.4 Acceptance gate (`verify/gate.py`)
`ACCEPTED ⇔ verifier.verdict == PASS ∧ novelty.status == NOVEL`. No setters. The gate is the only path to
`store.accept()`.

---

## 6. Novelty (`lifecore/novelty/`) — two-tier, fail-closed

1. **Canonicalization** (`canonical.py`): pattern → **apgcode** via lifelib; for *accepted* candidates,
   cross-check with an **independent** canonicalizer. A **symmetry soundness suite** (all 8 dihedral images ×
   all phases × random translations of each known object → the *same* apgcode and flagged KNOWN) is a
   **release blocker**.
2. **Catalog membership** (`catagolue.py`): query a **frozen, dated local Catagolue census snapshot**
   (hash recorded in provenance) first; optional live refresh via an allowlisted egress proxy. Network failure
   ⇒ `novelty-uncertain` (never "novel").
3. **MDL / minimality tier** (`mdl.py`): reject **derivative-of-known** — decompose into connected components;
   if the pattern = (known object) + (separable inert component) and is not compressive vs the nearest known
   (cheap-edit distance), flag `derivative` (not a discovery). *(Wang & Buehler MDL gate; community values minimal forms.)*

`NoveltyResult = {status ∈ {NOVEL, KNOWN, DERIVATIVE, UNCERTAIN}, apgcode, snapshot_hash, nearest_known, mdl_delta}`.

---

## 7. Search loop, strategy & memory (`lifecore/strategy/` + agent)

- **Staged progress-manager** (agent, but stages defined here): `feasibility → tuning → deep-search → verification`,
  each with explicit stopping criteria and best-node carry-forward. Replaces the single "empty/timeout reflex".
  *(AI Scientist v2 staged tree-search; AIDE — but add exploration to avoid AIDE's greedy local-optima stall.)*
- **Strategy tree** with a UCB / diverse-restart exploration term (not pure greedy).
- **Strategy archive** (`strategy/archive.py`): typed, append-only; **DGM parent-selection** (`score × 1/(1+children)`);
  scored on a **FIXED reference battery** (`strategy/battery.py`) of ~10–20 specs that are *known-reachable* AND
  *known-UNSAT*. Meta-utility = **verified-novel discoveries per unit budget**, crediting **correct UNSAT** on
  impossible specs (so it isn't rewarded for thrashing). *(Hu et al. DGM; ADAS.)*
- **Failure memory** (`strategy/failure_memory.py`): distilled cross-session dead-ends
  (e.g. "c/5 orthogonal under 20×20 UNSAT across qfind+rlifesrc at budget B") read before planning.
- **Width-escalation policy** for spaceship search (width is the dominant unpredictable cost lever; a TIMEOUT at
  width w triggers escalation, never a non-existence claim).

---

## 8. Benchmarking, budget & statistics (`lifecore/campaign/`) — production discipline

- **Mandatory baselines** (`campaign/baseline.py`): every campaign also runs **IID random sampling** and
  **sequential-conditioned sampling (SCS)** through the *same gate* at *equal budget*, reported with 95% CIs.
  No future evolutionary/agentic search ships unless it beats all baselines. *(Gideoni et al.)*
- **Budget ledger** (`campaign/budget.py`): first-class accounting of Claude tokens/$, engine CPU-seconds,
  and re-plan count, with **hard stops**. Report **discoveries-per-dollar** on a cost/accuracy frontier.
  *(Kapoor et al.)*
- **Type-I / multiple-comparisons control:** pre-register (hash) the spec; log **every gate query**; apply an
  e-value / FDR-style discovery-time correction scaling with attempt count; accepted range-targets must sit
  **strictly inside** the requested range. *(Huang et al. POPPER.)*

---

## 9. Provenance, reproducibility & stop/resume (`lifecore/store/`)

- **Append-only SQLite** event log: `campaign → run → candidate → verification → novelty → acceptance`.
- **Reproducible recipe** per accepted discovery: `{engine, engine_version, build_flags, config, seed, budget,
  reference_sim_version, canonicalizer_version, catagolue_snapshot_hash, container_image_digest}`.
- **Environment lock:** pinned engine versions + build flags, container image digest, dependency lockfile,
  recorded RNG seeds. A CI `lifeseek reproduce <discovery_id>` asserts **bitwise-identical replay** of the
  *acceptance pipeline* (nightly).
- **Crash-safe resume:** idempotency key per pipeline step; checkpoint-*after*-side-effect; resume must not
  re-pay Claude calls or double-write candidates. A checkpoint captures Strategist policy state, strategy-tree
  frontier, in-flight run handles, and RNG seeds.
- **Honest non-determinism statement:** the *acceptance pipeline* replays bitwise; the *exploration trajectory*
  (Claude's prompts/tool-calls) does not, and we do not claim it does.

---

## 10. Sandboxing (`lifecore/sandbox/`)

Every wrapped binary **and** lifelib run inside bubblewrap/seccomp with cgroup CPU/mem/time limits, read-only
mounts, and **no network except an allowlisted Catagolue egress proxy**. All engine stdout and Catagolue
responses are **untrusted** → parsed by a strict, **fuzz-tested** RLE/apgcode parser before anything reaches the
store. Sandboxing also bounds runaway HashLife blowups (converted to TIMEOUTs, which width-escalation handles).

---

## 11. MCP bridge (`lifeseek_mcp/`) — immutability enforcement

Exposes lifecore to Claude as tools. **Mechanically enforces** (not via prompt):
- `targetspec`, `verifier`, `novelty`, `budget` are **read-only** (no setters);
- the bridge **rejects** any Strategist output that would alter spec/gate/budget or reinterpret
  `novelty-uncertain` as `novel`, or widen tolerance fields (bbox/population/symmetry/width beyond `w_max`);
- **re-aim** is a separate `retarget` op gated by a **human checkpoint** that records a provenance diff.
- Tools (read/append only): `get_campaign`, `get_failure_memory`, `get_strategy_archive`, `propose_engine_policy`
  (validated against capability map), `run_search`, `verify_candidate`, `check_novelty`, `record_result`,
  `request_checkpoint`, `retarget` (human-gated).
- **Adversarial test (release blocker):** a Strategist that explicitly attempts spec relaxation is **blocked**.

---

## 12. Agent frontend (`agent/`, Claude Code)

- Skill `lifeseek` + subagents: **Strategist** (goal→spec+policy via capability map; self-revises via strategy
  archive + failure memory; **forbidden** from touching the gate), **Search-runner**, **Verifier-caller**
  (requests the deterministic gate; never decides), **Analyst** (characterize, RLE, report).
- **Async human intervention**: `redirect` (retarget active spec + re-prioritize frontier, takes precedence over
  the next step without halting in-flight runs) and `chat` (logged note) — in addition to synchronous
  phase-boundary checkpoints.
- **Elo-style pairwise ranking** of multiple spec-met∧verified∧novel candidates on cheap domain criteria
  (smaller bbox, lower population, higher symmetry) — emit a *ranked* set, not an unordered accept blob.

---

## 13. v1 scope boundary

**IN:** B3/S23; **spaceships, low-period oscillators, still-lifes**; full `lifecore` (sim, targetspec, ≥3 real
engine adapters: qfind/rlifesrc/LLS, ikpx2 stub); closed-world type-specific verifier; two-tier fail-closed
novelty; provenance/recipe/reproduce; sandboxing; budget ledger + IID/SCS baselines; strategy archive + failure
memory; MCP bridge with enforced immutability; Claude Code frontend with checkpoints + async redirect; YAML re-aim.

**LATER (architected-for, stubbed):** rule-swap to Life-like; guns/puffers/rakes/eaters + interaction
verification; mid/high-period oscillators via construction toolkits (CatForce, Snark/Herschel loops); the
Anthropic-API unattended runner; QD/open-ended novelty mode; LLM-evolutionary search (FunSearch/AlphaEvolve-style)
— and only if it beats the baselines.

---

## 14. Acceptance criteria for "v1 done"

A reviewer can confirm v1 by checking:
1. `lifecore` test suite green, including: lifelib↔NumPy **differential** tests on random soups; **golden**
   verification of glider (c/4 diagonal, p4), blinker (p2); **adversarial** gate tests (junk, mislabeled-known,
   debris-leaker, trivial-LCM "oscillator" → all REJECTED); **symmetry soundness suite** (release blocker) green.
2. `capable_engines(spec)` returns `no-capable-engine` for an oblique-ship/gun spec (no false "not found").
3. An end-to-end campaign **re-derives a known object** (verifier PASS, novelty **KNOWN** — proving the loop +
   novelty work) AND a **genuinely directed search** runs to a typed outcome with full provenance.
4. The **IID/SCS baselines** ran at equal budget with CIs in the campaign report.
5. The **MCP immutability** adversarial test (Strategist relaxation attempt) is blocked.
6. `lifeseek reproduce <id>` replays an accepted discovery's acceptance pipeline **bitwise** in CI.
7. **Re-aim demo:** editing the spec YAML starts a new campaign with no code changes.

---

## 15. Residual risks (carry forward, do not forget)
- Interaction-object verification (guns/eaters/rakes) needs multi-init robustness testing — hook designed now, built LATER.
- MDL decomposition heuristic needs its own calibration corpus (could mis-flag novel compositions).
- Mid/high-period oscillators (p ≥ ~43) need construction toolkits the single-seed engine interface can't express.
- Frozen Catagolue snapshot + Claude-side memorization can't eliminate novelty error from partial census coverage.
- Claude exploration trajectory is non-deterministic by nature (only the acceptance pipeline is bit-reproducible).
- Cost/Type-I control assumes the budget ledger and gate-query counts are complete — no out-of-band engine calls.
