from mcp.client import Client

from .models import ToolDefinition


class MCPToolRegistry:
    """
    Loads tool definitions published by an MCP server.

    The MCP server remains the source of truth for tool definitions
    and input schemas.
    """

    def __init__(self, client: Client):
        self._client = client
        self._tools: dict[str, ToolDefinition] = {}

    async def load(self) -> None:
        result = await self._client.list_tools()

        self._tools = {
            tool.name: ToolDefinition(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
            )
            for tool in result.tools
        }

    def get_input_schema(
        self,
        tool_name: str,
    ) -> dict:
        try:
            return self._tools[tool_name].input_schema
        except KeyError:
            raise KeyError(
                f"Tool schema not found: {tool_name}"
            ) from None

    def get_tool_definitions(
        self,
    ) -> list[ToolDefinition]:
        return list(self._tools.values())