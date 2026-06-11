# lifeseek

**lifeseek** is a **directed, re-aimable scientific-discovery harness for Conway's Game of Life
(B3/S23)**: you give it a typed *target specification* (e.g. "a period-2 oscillator", "a c/4
diagonal spaceship") and it runs steered, budget-bounded search campaigns wrapping open-source Life
engines. A result becomes a **discovery** only when it is **spec-met ∧ independently
re-simulation-verified ∧ novel** against known catalogs — and the LLM agent layer can **never
self-certify**, because all acceptance logic lives in a deterministic, LLM-free core behind an
immutability-enforcing bridge. Re-aim the entire effort by editing one YAML file.

## Architecture

Three layers, with a one-way trust boundary:

- **Layer 1 — `lifecore` (deterministic OSS core).** Typed `TargetSpec`s (content-hashed to a
  `spec_id`), a strict RLE reader/writer, an **independent NumPy reference simulator** used for
  verification (never the producing engine), the closed-world type-specific verifier, a fail-closed
  novelty oracle (apgcode → Catagolue + MDL), the capability map, the campaign orchestrator with
  mandatory IID/SCS baselines, signed verification records, reproducible recipes, and the
  acceptance **gate** (`ACCEPTED ⇔ verifier PASS ∧ novelty NOVEL` — a pure function, no setters).
- **MCP bridge — `lifeseek_mcp`.** A read/append surface over a frozen campaign that *mechanically*
  rejects relaxation: widening a tolerance field, proposing a non-capable engine, recording a
  candidate as more-novel than the oracle computed, or re-aiming without an approved human
  checkpoint.
- **Layer 2 — the Claude agent (external).** Drives search strategy through the bridge. It proposes;
  the core disposes. The agent cannot reach past the bridge into the gate, spec, novelty test, or
  budget.

## First campaign

The CLI ships as the `lifeseek` console script. External engine binaries are absent in this build,
so a campaign's candidate stream is seeded from an optional `seed_candidates` list of RLE strings —
a v1 stand-in for sandboxed engine output. The verify → novelty → gate → provenance pipeline is
identical either way.

1. Write a campaign YAML (see [`examples/blinker.campaign.yaml`](examples/blinker.campaign.yaml)):

   ```yaml
   spec:
     kind: oscillator
     period: 2
     bbox_max: [3, 3]
     rule: B3/S23
   budget: { max_engine_cpu_seconds: 100.0 }
   seed_candidates: ["3o!"]      # the blinker, in RLE
   ```

2. Run it, then inspect the report:

   ```bash
   uv run lifeseek run examples/blinker.campaign.yaml --out runs/demo
   uv run lifeseek report runs/demo
   ```

   `run` writes `runs/demo/report.json` (attempts, discoveries, both baselines with Wilson CIs) and
   one self-contained artifact per accepted discovery under `runs/demo/discoveries/`. It returns
   exit code `2` for a `no-capable-engine` spec (e.g. a `gun`) rather than a misleading "not found".
   Re-deriving a *known* object yields a verifier PASS with novelty **KNOWN** and zero accepted
   discoveries — proof the loop and the fail-closed oracle work.

3. **Re-aim with zero code changes** — edit the spec, or retarget onto a new spec YAML:

   ```bash
   uv run lifeseek retarget examples/blinker.campaign.yaml still.yaml --out still.campaign.yaml
   uv run lifeseek run still.campaign.yaml --out runs/still
   ```

   `retarget` prints a provenance diff (`from_spec_id <old> -> to_spec_id <new>`) and writes a new
   campaign YAML; the new run has a different `spec_id`. No source file changes.

4. **Reproduce** an accepted discovery bit-for-bit (release blocker, see
   [`docs/lifeseek/CI.md`](docs/lifeseek/CI.md)):

   ```bash
   uv run lifeseek reproduce runs/demo/discoveries/<discovery_id>.json
   ```

## Trust guarantees

- **Independent verification.** Acceptance is checked on a separate NumPy reference simulator, never
  a second invocation of the engine that produced the candidate (closed-world, empty-field
  embedding, empty-residual assertion, true-period vs trivial-LCM).
- **Fail-closed novelty.** An unknown or un-canonicalizable pattern is `UNCERTAIN`, never a silent
  "novel"; only `NOVEL` is acceptable.
- **Immutable gate.** The spec, verifier, novelty test, and budget are structurally immutable from
  the agent side — the MCP bridge has no setters and mechanically rejects relaxation attempts.
- **Reproducible provenance.** Each accepted discovery carries a signed verification record and a
  recipe pinning the trust-path code hashes and census snapshot; `lifeseek reproduce` replays the
  acceptance pipeline bitwise.
- **Baselines.** Every campaign runs mandatory IID and SCS baselines at equal budget, reported with
  Wilson confidence intervals, so a "discovery rate" is never read in isolation.

## Documentation

- [`docs/lifeseek/SPEC.md`](docs/lifeseek/SPEC.md) — source of truth: architecture, GoL domain model,
  verification protocol, novelty, budget/baseline/statistics, provenance, sandboxing, MCP
  immutability, v1 acceptance criteria.
- [`docs/lifeseek/IMPLEMENTATION_PLAN.md`](docs/lifeseek/IMPLEMENTATION_PLAN.md) — phased TDD task plan.
- [`docs/lifeseek/CI.md`](docs/lifeseek/CI.md) — nightly bitwise-reproduce gate.

## License

[MIT](LICENSE) © 2026 GonzMenSeb.
