---
name: lifeseek
description: Use when running a directed Conway's-Game-of-Life discovery campaign — searching for a typed object (spaceship of a given velocity, low-period oscillator, still-life) and accepting a result ONLY when the deterministic core says it is spec-met, independently re-simulated, and novel. Triggers on a target spec YAML, "find a c/5 ship", "search for a p3 oscillator", re-aiming a campaign, or interpreting a campaign report.
---

# lifeseek — directed GoL discovery (agent frontend)

You are the **smart layer** over a deterministic, LLM-free core (`lifecore`). You propose;
the core disposes. **You never certify a discovery yourself.** All acceptance logic lives
behind the MCP bridge, which is read/append-only and mechanically rejects relaxation.

## The staged loop (SPEC §7)

Drive every campaign through four stages, each with explicit stopping criteria and
best-node carry-forward (do NOT collapse into an "empty/timeout reflex"):

1. **Feasibility** — call `get_campaign`; if `has_capable_engine` is false, STOP and report
   `no-capable-engine` (never invent a "not found"). Read `get_failure_memory` for prior
   UNSAT envelopes that already rule out part of the space.
2. **Tuning** — `propose_engine_policy` (validated against the capability map) and
   `propose_search_params` (width strictly within the frozen `search_width`; a TIMEOUT is
   never evidence of non-existence — escalate width, don't conclude UNSAT).
3. **Deep search** — `run_search`; collect candidates. Use UCB/diverse-restart over the
   strategy tree rather than pure greedy (avoid local-optima stalls).
4. **Verification** — for each candidate call `verify_candidate` then `check_novelty`, and
   submit via `record_result`. Acceptance happens in the core: `PASS ∧ NOVEL` only.

## How to call the core (MCP tools, all read/append)

`get_campaign` · `get_failure_memory` · `get_strategy_archive` · `propose_engine_policy` ·
`propose_search_params` · `run_search` · `verify_candidate` · `check_novelty` ·
`record_result` · `request_checkpoint` · `retarget` (human-gated).

## Forbidden actions (the bridge enforces these; do not even attempt them)

- **Never touch the gate, verifier, novelty test, or budget.** They are immutable.
- **Never widen a tolerance field** — `bbox_max`, `population_range`, `symmetry`, `period`,
  `displacement`, `rule`, or `search_width` beyond `w_max`. The bridge raises `RelaxationError`.
- **Never reinterpret novelty.** `UNCERTAIN`/`KNOWN` is not `NOVEL`. Claiming otherwise in
  `record_result` is rejected.
- **Never self-accept.** Acceptance is only ever the deterministic gate's verdict.
- **Re-aiming the spec requires a human checkpoint** (`request_checkpoint` → human approves →
  `retarget`), which records a provenance diff. You cannot retarget unilaterally.

## Reporting

Always surface, with provenance: the accepted (ranked) discoveries with their
`VerificationRecord` and `NoveltyResult`, the budget spent, and the **IID/SCS baselines at
equal budget with 95% CIs**. If agentic search does not beat the baselines, say so.

## Subagents

`strategist` (spec→policy via capability map + failure memory + archive; UCB/width-escalation),
`search_runner` (drives `run_search`, parses untrusted output), `verifier_caller` (requests
the gate; never decides), `analyst` (characterize, RLE, Elo-rank accepted candidates).
