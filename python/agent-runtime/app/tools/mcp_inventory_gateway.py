import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpInventoryGateway:
    def __init__(self, server_dir: str | None = None) -> None:
        default_dir = Path(__file__).parents[4] / "mcp-servers" / "inventory-server"
        self.server_dir = Path(server_dir or os.getenv("INVENTORY_MCP_DIR", default_dir)).resolve()

    async def analyze(self, product_id: str) -> dict:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.server"],
            cwd=self.server_dir,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("analyze_inventory_risk", {"product_id": product_id})
                if getattr(result, "structuredContent", None):
                    return result.structuredContent
                text = result.content[0].text
                return json.loads(text)
