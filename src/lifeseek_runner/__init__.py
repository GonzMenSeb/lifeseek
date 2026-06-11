"""lifeseek_runner — (LATER) unattended Anthropic-API campaign runner.

v1 ships the INTERFACE + a smoke test only (SPEC §13 LATER / Phase 12). The runner
will drive the SAME MCP bridge tools as the Claude Code frontend via the Agent SDK,
with an async checkpoint queue, so unattended runs honour the identical immutability
guarantees. No autonomous execution is wired in v1.
"""

from lifeseek_runner.runner import CheckpointQueue, UnattendedRunner

__all__ = ["CheckpointQueue", "UnattendedRunner"]
