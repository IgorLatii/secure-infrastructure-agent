from typing import Any

import json

from openai import AsyncOpenAI

from ..llm import AgentLLM
from ..models import ToolCall, ToolDefinition, ToolResult


class OpenAIAgentLLM(AgentLLM):
    """
    OpenAI implementation of the provider-neutral AgentLLM interface.
    """

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
    ):
        self._client = client
        self._model = model
        self._previous_response_id: str | None = None

    async def decide(
            self,
            user_request: str,
            tool_definitions: list[ToolDefinition],
            tool_results: list[ToolResult],
    ) -> ToolCall | str:
        if self._previous_response_id is None:
            input_data = user_request
        else:
            input_data = build_openai_tool_outputs(
                tool_results[-1:]
            )

        response = await self._client.responses.create(
            model=self._model,
            input=input_data,
            tools=build_openai_tools(tool_definitions),
            previous_response_id=self._previous_response_id,
            parallel_tool_calls=False,
        )

        self._previous_response_id = response.id

        print(
            "OpenAI response output:",
            [
                (
                    item.type,
                    getattr(item, "name", None),
                    getattr(item, "call_id", None),
                )
                for item in response.output
            ],
        )

        for item in response.output:
            if item.type == "function_call":
                return ToolCall(
                    call_id=item.call_id,
                    name=item.name,
                    arguments=json.loads(item.arguments),
                )

        return response.output_text


def build_openai_tools(
    tool_definitions: list[ToolDefinition],
) -> list[dict[str, Any]]:
    """
    Convert provider-neutral tool definitions into
    OpenAI function tool definitions.
    """
    return [
        {
            "type": "function",
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        }
        for tool in tool_definitions
    ]

def build_openai_tool_outputs(
    tool_results: list[ToolResult],
) -> list[dict[str, str]]:
    """
    Convert provider-neutral tool results into
    OpenAI function call outputs.
    """
    return [
        {
            "type": "function_call_output",
            "call_id": result.call_id,
            "output": json.dumps(result.content),
        }
        for result in tool_results
    ]