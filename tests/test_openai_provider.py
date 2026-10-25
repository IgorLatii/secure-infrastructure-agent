from types import SimpleNamespace
import json
import pytest

from src.agent.models import ToolCall, ToolDefinition, ToolResult
from src.agent.providers.openai import (
    OpenAIAgentLLM,
    build_openai_tool_outputs,
    build_openai_tools,
)

def test_build_openai_tools_from_provider_neutral_definitions():
    definitions = [
        ToolDefinition(
            name="get_system_health",
            description="Get system health.",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                    }
                },
                "required": ["target"],
            },
        )
    ]

    tools = build_openai_tools(definitions)

    assert tools == [
        {
            "type": "function",
            "name": "get_system_health",
            "description": "Get system health.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                    }
                },
                "required": ["target"],
            },
        }
    ]

@pytest.mark.anyio
async def test_openai_llm_converts_function_call_to_tool_call():
    class FakeResponses:
        async def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_001",
                output=[
                    SimpleNamespace(
                        type="function_call",
                        call_id="call_123",
                        name="get_system_health",
                        arguments='{"target":"LAB-PC"}',
                    )
                ],
                output_text="",
            )

    class FakeOpenAIClient:
        def __init__(self):
            self.responses = FakeResponses()

    definitions = [
        ToolDefinition(
            name="get_system_health",
            description="Get system health.",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                },
                "required": ["target"],
            },
        )
    ]

    llm = OpenAIAgentLLM(
        client=FakeOpenAIClient(),
        model="test-model",
    )

    decision = await llm.decide(
        user_request="Why is LAB-PC slow?",
        tool_definitions=definitions,
        tool_results=[],
    )

    assert decision == ToolCall(
        call_id="call_123",
        name="get_system_health",
        arguments={"target": "LAB-PC"},
    )

def test_build_openai_tool_outputs_from_provider_neutral_results():
    results = [
        ToolResult(
            call_id="call_123",
            name="get_system_health",
            content={
                "cpu_percent": 15.0,
                "pending_reboot": False,
            },
        )
    ]

    outputs = build_openai_tool_outputs(results)

    assert len(outputs) == 1

    assert outputs[0]["type"] == "function_call_output"
    assert outputs[0]["call_id"] == "call_123"

    assert json.loads(outputs[0]["output"]) == {
        "cpu_percent": 15.0,
        "pending_reboot": False,
    }

@pytest.mark.anyio
async def test_openai_llm_continues_tool_conversation_with_previous_response_id():
    requests = []

    class FakeResponses:
        async def create(self, **kwargs):
            requests.append(kwargs)

            if len(requests) == 1:
                return SimpleNamespace(
                    id="resp_001",
                    output=[
                        SimpleNamespace(
                            type="function_call",
                            call_id="call_123",
                            name="get_system_health",
                            arguments='{"target":"LAB-PC"}',
                        )
                    ],
                    output_text="",
                )

            return SimpleNamespace(
                id="resp_002",
                output=[],
                output_text="CPU usage is normal.",
            )

    class FakeOpenAIClient:
        def __init__(self):
            self.responses = FakeResponses()

    definitions = [
        ToolDefinition(
            name="get_system_health",
            description="Get system health.",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                },
                "required": ["target"],
            },
        )
    ]

    llm = OpenAIAgentLLM(
        client=FakeOpenAIClient(),
        model="test-model",
    )

    first_decision = await llm.decide(
        user_request="Why is LAB-PC slow?",
        tool_definitions=definitions,
        tool_results=[],
    )

    assert first_decision == ToolCall(
        call_id="call_123",
        name="get_system_health",
        arguments={"target": "LAB-PC"},
    )

    result = ToolResult(
        call_id="call_123",
        name="get_system_health",
        content={
            "cpu_percent": 15.0,
            "pending_reboot": False,
        },
    )

    second_decision = await llm.decide(
        user_request="Why is LAB-PC slow?",
        tool_definitions=definitions,
        tool_results=[result],
    )

    assert second_decision == "CPU usage is normal."

    assert requests[0]["previous_response_id"] is None

    assert requests[1]["previous_response_id"] == "resp_001"

    assert requests[1]["input"][0]["type"] == "function_call_output"
    assert requests[1]["input"][0]["call_id"] == "call_123"

    assert json.loads(
        requests[1]["input"][0]["output"]
    ) == {
        "cpu_percent": 15.0,
        "pending_reboot": False,
    }