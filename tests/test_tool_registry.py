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

    assert len(definitions) == 8

    network_tool = next(
        tool
        for tool in definitions
        if tool.name == "get_network_connections"
    )

    schema = network_tool.input_schema

    assert schema["required"] == ["target"]

    assert schema["properties"]["target"]["type"] == "string"

    assert schema["properties"]["max_connections"]["type"] == "integer"
    assert schema["properties"]["max_connections"]["minimum"] == 1
    assert schema["properties"]["max_connections"]["maximum"] == 100
    assert schema["properties"]["max_connections"]["default"] == 50

    process_details_tool = next(
        tool
        for tool in definitions
        if tool.name == "get_process_details"
    )

    schema = process_details_tool.input_schema

    assert schema["required"] == [
        "target",
        "pid",
    ]

    properties = schema["properties"]

    assert properties["target"]["type"] == "string"

    assert properties["pid"]["type"] == "integer"
    assert properties["pid"]["minimum"] == 1

    events_tool = next(
        definition
        for definition in definitions
        if definition.name == "get_windows_events"
    )

    schema = events_tool.input_schema

    assert schema["required"] == [
        "target",
        "log_name",
        "lookback_minutes",
    ]

    properties = schema["properties"]

    assert properties["log_name"]["enum"] == [
        "System",
        "Application",
        "Security",
    ]

    assert properties["lookback_minutes"]["minimum"] == 1
    assert properties["lookback_minutes"]["maximum"] == 10080

    assert properties["max_events"]["minimum"] == 1
    assert properties["max_events"]["maximum"] == 100

    levels_schema = properties["levels"]["anyOf"][0]

    assert levels_schema["type"] == "array"
    assert levels_schema["maxItems"] == 6
    assert levels_schema["items"]["enum"] == [
        "LogAlways",
        "Critical",
        "Error",
        "Warning",
        "Information",
        "Verbose",
    ]

    event_ids_schema = properties["event_ids"]["anyOf"][0]

    assert event_ids_schema["type"] == "array"
    assert event_ids_schema["maxItems"] == 20
    assert event_ids_schema["items"]["type"] == "integer"
    assert event_ids_schema["items"]["exclusiveMinimum"] == 0

    provider_schema = properties["provider_name"]["anyOf"][0]

    assert provider_schema["type"] == "string"
    assert provider_schema["maxLength"] == 256

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

    tasks_tool = next(
        definition
        for definition in definitions
        if definition.name == "get_scheduled_tasks"
    )

    tasks_schema = tasks_tool.input_schema

    assert tasks_schema["required"] == [
        "target",
    ]

    tasks_properties = tasks_schema["properties"]

    task_name_schema = tasks_properties["task_name"]["anyOf"][0]

    assert task_name_schema["type"] == "string"
    assert task_name_schema["minLength"] == 1
    assert task_name_schema["maxLength"] == 256

    assert tasks_properties["max_tasks"]["minimum"] == 1
    assert tasks_properties["max_tasks"]["maximum"] == 100
    assert tasks_properties["max_tasks"]["default"] == 50

    startup_tool = next(
        definition
        for definition in definitions
        if definition.name == "get_startup_entries"
    )

    startup_schema = startup_tool.input_schema

    assert startup_schema["required"] == [
        "target",
    ]

    startup_properties = startup_schema["properties"]

    assert startup_properties["target"]["type"] == "string"

    assert startup_properties["max_entries"]["type"] == "integer"
    assert startup_properties["max_entries"]["minimum"] == 1
    assert startup_properties["max_entries"]["maximum"] == 100
    assert startup_properties["max_entries"]["default"] == 50
