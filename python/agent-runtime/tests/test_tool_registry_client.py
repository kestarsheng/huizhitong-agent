import asyncio

from app.tools.registry_client import ToolRegistryClient


def test_tool_registry_client_fails_open_when_service_unavailable():
    result = asyncio.run(ToolRegistryClient("http://127.0.0.1:1").available_tools("inventory", 1))
    assert result == []
