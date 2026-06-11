# Async interventions & synchronous checkpoints (SPEC §12, Task 10.3)

Two human-in-the-loop channels, in addition to the staged phase boundaries:

## Async (do not halt in-flight runs)
- **`redirect`** — re-aim the active spec and re-prioritize the strategy frontier. It takes
  precedence over the *next* step without killing running searches. In the core this is an
  `InterventionQueue.redirect(new_spec)`; the runner drains it between candidates and surfaces
  `redirect_requested`. **Applying the redirect is a human-gated `retarget`** (see below) — the
  agent cannot re-aim unilaterally.
- **`chat`** — a logged note (`InterventionQueue.chat(...)`), recorded in the campaign report.

## Synchronous (phase-boundary)
- At each stage boundary the agent may `request_checkpoint(new_spec)`; a human must
  `approve_checkpoint(id)` before `retarget(id)` applies it. The retarget records a provenance
  diff (`from_spec_id` → `to_spec_id`). Without approval, `retarget` raises `CheckpointRequired`.

The runner (`lifecore.campaign.runner`) implements the async queue; the MCP bridge
(`lifeseek_mcp.bridge`) implements the synchronous human-gated retarget.
