"""MCP server wiring (Task 9.1, SPEC §11) — a thin transport over :mod:`bridge`.

All enforcement lives in :class:`lifeseek_mcp.bridge.Bridge`; this module only exposes
its read/append methods as MCP tools. The ``mcp`` package is an optional extra, so it is
imported lazily inside :func:`create_server` — importing this module never requires it.
The tool surface is exactly SPEC §11: read + append, no setters.
"""

from __future__ import annotations

from typing import Any

from lifeseek_mcp.bridge import Bridge

# The SPEC §11 tool surface. retarget is human-gated; there are no spec/gate/budget setters.
TOOL_NAMES: tuple[str, ...] = (
    "get_campaign",
    "get_failure_memory",
    "get_strategy_archive",
    "propose_engine_policy",
    "propose_search_params",
    "run_search",
    "verify_candidate",
    "check_novelty",
    "record_result",
    "request_checkpoint",
    "retarget",
)


def create_server(bridge: Bridge, name: str = "lifeseek") -> Any:
    """Build a FastMCP server exposing the bridge's read/append tools.

    Raises ImportError (with guidance) if the optional ``mcp`` extra is not installed.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "the 'mcp' extra is required to run the lifeseek MCP server; "
            "install it with `uv sync --extra mcp`"
        ) from exc

    server = FastMCP(name)

    @server.tool()
    def get_campaign() -> dict[str, Any]:
        return bridge.get_campaign()

    @server.tool()
    def get_failure_memory() -> list[dict[str, Any]]:
        return bridge.get_failure_memory()

    @server.tool()
    def get_strategy_archive() -> list[dict[str, Any]]:
        return bridge.get_strategy_archive()

    @server.tool()
    def propose_engine_policy(engine_ids: list[str]) -> list[str]:
        return bridge.propose_engine_policy(engine_ids)

    @server.tool()
    def request_checkpoint(new_spec_yaml: str) -> str:
        from lifecore.targetspec.yaml_io import from_yaml

        return bridge.request_retarget_checkpoint(from_yaml(new_spec_yaml))

    return server
