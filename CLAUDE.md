# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

The project uses **`uv`** (env pinned by `uv.lock`, Python ≥3.11). All commands run through `uv run`.

```bash
uv run pytest -q                          # full suite (configured testpaths=tests, pythonpath=src)
uv run pytest tests/verify/test_oscillator.py            # one file
uv run pytest tests/verify/test_oscillator.py::test_name # one test
uv run pytest -k "immutability"           # by keyword
uv run ruff check .                        # lint (line-length 110; rules E,F,I,UP,B,SIM,RUF)
uv run ruff format .                       # format
uv run mypy                                # strict type-check (config in pyproject.toml; files=src,tests)
uv run pre-commit install                  # activate ruff + mypy + quick-pytest git hooks (run once)
```

The CLI is the `lifeseek` console script (`lifecore.cli:main`), with four subcommands:

```bash
uv run lifeseek run <campaign.yaml> --out runs/<dir>   # run a campaign; writes report.json + discoveries/*.json
uv run lifeseek report runs/<dir>                       # pretty-print a finished run
uv run lifeseek retarget <campaign.yaml> <new-spec.yaml> --out <new.campaign.yaml>  # re-aim (prints spec_id diff)
uv run lifeseek reproduce runs/<dir>/discoveries/<id>.json   # bitwise replay an accepted discovery
```

Exit codes carry meaning: `run` returns **2** for a `no-capable-engine` spec (e.g. a `gun`), never a misleading "not found"; `reproduce` returns **1** on any bitwise MISMATCH (a release blocker — see `docs/lifeseek/CI.md`, the nightly reproduce gate).

## Architecture — three layers, one-way trust boundary

lifeseek searches for typed Conway's-Game-of-Life objects (B3/S23). A result becomes a **discovery** only when **spec-met ∧ independently re-simulation-verified ∧ novel**. The whole design exists to make the LLM agent *unable to certify its own results*. Three layers under `src/`:

- **`lifecore/` — deterministic, LLM-free core.** Everything that decides acceptance. Sub-packages: `targetspec/` (typed specs, content-hashed to a frozen `spec_id`; `capability.py` maps a spec → capable engines), `sim/` (pattern model, RLE reader/writer, and the **independent NumPy reference simulator** used for verification), `engines/` (directed-search adapters: qfind/rlifesrc/LLS/ikpx2 — interfaces/stubs in v1), `sandbox/` (bubblewrap isolation + fuzz-parse for wrapped binaries), `verify/` (closed-world type-specific verifier + the pure acceptance `gate.py` + signed records), `novelty/` (apgcode canonicalizer + independent cross-check + frozen Catagolue lookup + MDL), `store/` (append-only SQLite provenance + reproducible recipe), `campaign/` (config, budget ledger, mandatory IID/SCS baselines, stats), `strategy/` (strategy archive + failure memory), `cli.py`.
- **`lifeseek_mcp/` — the immutability-enforcing bridge.** `bridge.py` is a read/append surface over a *frozen* campaign; `server.py` is a thin (optional, `mcp` extra) FastMCP transport exposing exactly the SPEC §11 tool surface. There are **no setters** on spec/gate/budget.
- **`lifeseek_runner/` — unattended Anthropic-API runner.** v1 ships the interface + a smoke test only; real autonomous execution is LATER.

The external Claude agent (`agent/skills/lifeseek/SKILL.md` + `agent/subagents/*`) is "Layer 2" — it proposes search strategy through the bridge but cannot reach the gate, spec, novelty test, or budget.

## Invariants you must not break

These are enforced by tests (several by AST guards) and are the reason the architecture exists. Changing trust-path code without preserving them is a regression even if other tests pass:

- **Verification is a separate code path.** `verify/verifier.py` runs acceptance on `sim/reference` (NumPy) only — **never** the producing engine (lifelib). An AST-guard test asserts `verifier.py` is lifelib-free. The producer and verifier share no sim code.
- **Novelty is fail-closed and independently cross-checked.** Unknown / un-canonicalizable ⇒ `UNCERTAIN`, never a silent `NOVEL`; only `NOVEL` is acceptable. `novelty/canonical.py` provides a lifelib-free independent canonicalizer (also AST-guarded).
- **The gate is a pure function.** `verify/gate.py`: `ACCEPTED ⇔ verifier PASS ∧ novelty NOVEL`. No setters, no side effects.
- **The MCP bridge mechanically rejects relaxation.** No setters on the frozen spec/gate/budget; widening a tolerance, proposing a non-capable engine, recording a candidate as more-novel than the oracle computed, or re-aiming without an approved human checkpoint must all be rejected. The adversarial immutability suite (`tests/mcp/test_immutability.py`) is a **RELEASE BLOCKER**.
- **No silent "not found".** An incapable spec returns `no-capable-engine` (exit 2) via the capability map, not an empty result.
- **Acceptance is reproducible bitwise.** Each accepted discovery carries a signed verification record + recipe pinning trust-path code hashes and the Catagolue snapshot; `lifeseek reproduce` replays the pipeline to canonical-JSON equality.
- **Agentic cleverness must beat baselines.** Every campaign runs mandatory IID + SCS baselines at equal budget, reported with Wilson CIs; a discovery rate is never read in isolation.

## v1 scope notes

External engine binaries are absent in this build: a campaign's candidate stream is seeded from an optional `seed_candidates` list of RLE strings (a stand-in for sandboxed engine output) — the verify → novelty → gate → provenance pipeline is identical either way. `gun`/`puffer`/`rake`/`eater` and the oscillator assembly mechanisms (`hassler_catalyst`, etc.) are schema-only stubs that return `no-capable-engine`. Engine source SHAs in `tools/versions.lock` are `TODO-CONFIRM` and only matter for real engine builds, not the pure-Python core.
