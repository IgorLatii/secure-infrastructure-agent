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