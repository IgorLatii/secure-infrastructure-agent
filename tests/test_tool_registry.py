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

@pytest.mark.anyio
async def test_registry_exposes_provider_neutral_tool_definitions():
    mcp_server = create_server()

    async with Client(mcp_server) as client:
        registry = MCPToolRegistry(client)
        await registry.load()

        definitions = registry.get_tool_definitions()

    assert len(definitions) == 3

    definitions_by_name = {
        definition.name: definition
        for definition in definitions
    }

    assert "get_system_health" in definitions_by_name
    assert "get_top_processes" in definitions_by_name
    assert "get_service_status" in definitions_by_name

    health_definition = definitions_by_name["get_system_health"]

    assert health_definition.description is not None
    assert "target" in health_definition.input_schema["properties"]

    processes_definition = definitions_by_name["get_top_processes"]

    assert processes_definition.description is not None
    assert "target" in processes_definition.input_schema["properties"]
    assert (
        processes_definition.input_schema["properties"]["target"]["type"]
        == "string"
    )
    assert "target" in processes_definition.input_schema["required"]

    service_definition = definitions_by_name["get_service_status"]

    assert service_definition.description is not None

    service_schema = service_definition.input_schema

    assert "target" in service_schema["properties"]
    assert service_schema["properties"]["target"]["type"] == "string"

    assert "service_name" in service_schema["properties"]
    assert service_schema["properties"]["service_name"]["type"] == "string"

    assert "target" in service_schema["required"]
    assert "service_name" in service_schema["required"]