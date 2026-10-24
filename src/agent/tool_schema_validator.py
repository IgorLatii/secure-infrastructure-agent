from jsonschema import ValidationError, validate

from .models import ToolCall
from .tool_registry import MCPToolRegistry


class ToolSchemaValidator:
    """
    Validates LLM-proposed tool arguments against
    input schemas published by the MCP server.
    """

    def __init__(self, registry: MCPToolRegistry):
        self._registry = registry

    def validate(self, call: ToolCall) -> None:
        schema = self._registry.get_input_schema(call.name)

        allowed_arguments = set(
            schema.get("properties", {}).keys()
        )
        provided_arguments = set(call.arguments.keys())

        unexpected_arguments = (
                provided_arguments - allowed_arguments
        )

        if unexpected_arguments:
            names = ", ".join(sorted(unexpected_arguments))

            raise ValueError(
                f"Unexpected arguments for tool "
                f"{call.name}: {names}"
            )

        try:
            validate(
                instance=call.arguments,
                schema=schema,
            )
        except ValidationError as exc:
            raise ValueError(
                f"Invalid arguments for tool "
                f"{call.name}: {exc.message}"
            ) from None