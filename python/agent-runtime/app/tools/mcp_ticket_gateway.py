import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpTicketGateway:
    """通过 stdio 拉起 ticket-server 的 MCP 客户端。"""

    def __init__(self, server_dir: str | None = None) -> None:
        default_dir = Path(__file__).parents[4] / "mcp-servers" / "ticket-server"
        self.server_dir = Path(server_dir or os.getenv("TICKET_MCP_DIR", default_dir)).resolve()

    async def _call(self, tool_name: str, arguments: dict) -> dict:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.server"],
            cwd=self.server_dir,
            env={**os.environ},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if getattr(result, "structuredContent", None):
                    return result.structuredContent
                text = result.content[0].text
                return json.loads(text)

    async def create(self, subject: str, description: str, priority: str = "MEDIUM", customer_id: str = "") -> dict:
        return await self._call("create_ticket", {
            "subject": subject,
            "description": description,
            "priority": priority,
            "customer_id": customer_id,
        })

    async def query(self, ticket_id: str) -> dict:
        return await self._call("query_ticket", {"ticket_id": ticket_id})
