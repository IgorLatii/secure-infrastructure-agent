from typing import Any

from mcp.client import Client


class MCPToolRegistry:
    """
    Loads tool definitions published by an MCP server.

    The MCP server remains the source of truth for tool input schemas.
    """

    def __init__(self, client: Client):
        self._client = client
        self._input_schemas: dict[str, dict[str, Any]] = {}

    async def load(self) -> None:
        result = await self._client.list_tools()

        self._input_schemas = {
            tool.name: tool.input_schema
            for tool in result.tools
        }

    def get_input_schema(
        self,
        tool_name: str,
    ) -> dict[str, Any]:
        try:
            return self._input_schemas[tool_name]
        except KeyError:
            raise KeyError(
                f"Tool schema not found: {tool_name}"
            ) from None