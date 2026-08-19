import asyncio

from app.tools.mcp_inventory_gateway import McpInventoryGateway


def test_real_mcp_inventory_tool() -> None:
    result = asyncio.run(McpInventoryGateway().analyze("P1002"))
    assert result["risk"] == "HIGH"
    assert result["suggestion"] == "建议补货"
