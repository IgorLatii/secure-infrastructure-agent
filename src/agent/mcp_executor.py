from mcp.client import Client

from .models import ToolCall, ToolResult


class MCPToolExecutor:
    """
    Executes agent tool calls through an MCP client.
    """

    def __init__(self, client: Client):
        self._client = client

    async def execute(self, call: ToolCall) -> ToolResult:
        result = await self._client.call_tool(
            call.name,
            call.arguments,
        )

        if result.is_error:
            raise RuntimeError(
                f"MCP tool execution failed: {call.name}"
            )

        content = result.structured_content

        if content is None:
            raise RuntimeError(
                f"MCP tool returned no structured content: {call.name}"
            )

        return ToolResult(
            name=call.name,
            content=content,
        )