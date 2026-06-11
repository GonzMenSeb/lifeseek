"""MCP server surface tests (Task 9.1). The mcp transport itself is an optional extra."""

import pytest

from lifecore.campaign.campaign import Campaign
from lifecore.targetspec.models import Spaceship, SymmetryClass
from lifeseek_mcp import server
from lifeseek_mcp.bridge import Bridge


def test_tool_surface_is_read_append_only() -> None:
    # exactly the SPEC §11 surface; no setters
    assert "get_campaign" in server.TOOL_NAMES
    assert "retarget" in server.TOOL_NAMES
    assert not any(t.startswith(("set_", "widen", "relax", "override")) for t in server.TOOL_NAMES)


def test_create_server_requires_mcp_or_builds() -> None:
    spec = Spaceship(
        displacement=(1, 1), period=4, symmetry_class=SymmetryClass.GLIDE_REFLECT, search_width=(1, 5)
    )
    bridge = Bridge(campaign=Campaign.create(spec))
    pytest.importorskip("mcp", reason="mcp extra not installed")
    srv = server.create_server(bridge)
    assert srv is not None
