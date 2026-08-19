import os
from typing import Any


class ToolRegistryClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("TOOL_SERVICE_URL", "http://localhost:8083")).rstrip("/")

    async def available_tools(self, agent_type: str, tenant_id: int) -> list[dict[str, Any]]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(
                    f"{self.base_url}/internal/tools/available",
                    params={"agentType": agent_type, "tenantId": tenant_id},
                )
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, list) else []
        except Exception:
            # 工具治理服务不可用时，由运行时按本地配置继续工作。
            return []


tool_registry_client = ToolRegistryClient()
