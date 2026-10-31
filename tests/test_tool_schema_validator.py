import pytest

from mcp.client import Client

from src.agent.models import ToolCall
from src.agent.tool_registry import MCPToolRegistry
from src.agent.tool_schema_validator import ToolSchemaValidator
from src.windows_mcp.server import create_server


@pytest.mark.anyio
async def test_schema_validator_accepts_valid_arguments():
    server = create_server()

    async with Client(server) as client:
        registry = MCPToolRegistry(client)
        await registry.load()

        validator = ToolSchemaValidator(registry)

        call = ToolCall(
            call_id="test-call-1",
            name="get_system_health",
            arguments={"target": "LAB-PC"},
        )

        validator.validate(call)


@pytest.mark.anyio
async def test_schema_validator_rejects_missing_required_argument():
    server = create_server()

    async with Client(server) as client:
        registry = MCPToolRegistry(client)
        await registry.load()

        validator = ToolSchemaValidator(registry)

        call = ToolCall(
            call_id="test-call-1",
            name="get_system_health",
            arguments={},
        )

        with pytest.raises(
            ValueError,
            match="Invalid arguments",
        ):
            validator.validate(call)


@pytest.mark.anyio
async def test_schema_validator_rejects_wrong_argument_type():
    server = create_server()

    async with Client(server) as client:
        registry = MCPToolRegistry(client)
        await registry.load()

        validator = ToolSchemaValidator(registry)

        call = ToolCall(
            call_id="test-call-1",
            name="get_system_health",
            arguments={"target": 123},
        )

        with pytest.raises(
            ValueError,
            match="Invalid arguments",
        ):
            validator.validate(call)

@pytest.mark.anyio
async def test_schema_validator_rejects_unexpected_argument():
    server = create_server()

    async with Client(server) as client:
        registry = MCPToolRegistry(client)
        await registry.load()

        validator = ToolSchemaValidator(registry)

        call = ToolCall(
            call_id="test-call-1",
            name="get_system_health",
            arguments={
                "target": "LAB-PC",
                "script": "Get-Process",
            },
        )

        with pytest.raises(
                ValueError,
                match="Unexpected arguments",
        ):
            validator.validate(call)

@pytest.mark.anyio
async def test_schema_validator_rejects_invalid_event_id():
    server = create_server()

    async with Client(server) as client:
        registry = MCPToolRegistry(client)
        await registry.load()

        validator = ToolSchemaValidator(registry)

        call = ToolCall(
            call_id="test-call-events-1",
            name="get_windows_events",
            arguments={
                "target": "LAB-PC",
                "log_name": "System",
                "lookback_minutes": 60,
                "event_ids": [0, 41],
            },
        )

        with pytest.raises(
            ValueError,
            match="Invalid arguments",
        ):
            validator.validate(call)

@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_arguments",
    [
        {
            "target": "LAB-PC",
            "log_name": "UnknownLog",
            "lookback_minutes": 60,
        },
        {
            "target": "LAB-PC",
            "log_name": "System",
            "lookback_minutes": 0,
        },
        {
            "target": "LAB-PC",
            "log_name": "System",
            "lookback_minutes": 10081,
        },
        {
            "target": "LAB-PC",
            "log_name": "System",
            "lookback_minutes": 60,
            "levels": ["InvalidLevel"],
        },
        {
            "target": "LAB-PC",
            "log_name": "System",
            "lookback_minutes": 60,
            "event_ids": list(range(1, 22)),
        },
        {
            "target": "LAB-PC",
            "log_name": "System",
            "lookback_minutes": 60,
            "provider_name": "A" * 257,
        },
        {
            "target": "LAB-PC",
            "log_name": "System",
            "lookback_minutes": 60,
            "max_events": 101,
        },
    ],
)
async def test_schema_validator_rejects_out_of_bounds_windows_event_arguments(
    invalid_arguments,
):
    server = create_server()

    async with Client(server) as client:
        registry = MCPToolRegistry(client)
        await registry.load()

        validator = ToolSchemaValidator(registry)

        call = ToolCall(
            call_id="test-call-events-bounds",
            name="get_windows_events",
            arguments=invalid_arguments,
        )

        with pytest.raises(
            ValueError,
            match="Invalid arguments",
        ):
            validator.validate(call)