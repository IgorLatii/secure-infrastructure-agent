import pytest

from mcp.client import Client

from src.agent.tool_registry import MCPToolRegistry
from src.windows_mcp.server import create_server


@pytest.mark.anyio
async def test_registry_loads_input_schema_from_mcp():
    server = create_server()

    async with Client(server) as client:
        registry = MCPToolRegistry(client)

        await registry.load()

        schema = registry.get_input_schema(
            "get_system_health"
        )

        assert schema["type"] == "object"
        assert "target" in schema["properties"]
        assert schema["properties"]["target"]["type"] == "string"
        assert "target" in schema["required"]

@pytest.mark.anyio
async def test_registry_rejects_unknown_tool():
    server = create_server()

    async with Client(server) as client:
        registry = MCPToolRegistry(client)

        await registry.load()

        with pytest.raises(
            KeyError,
            match="Tool schema not found: run_powershell",
        ):
            registry.get_input_schema("run_powershell")