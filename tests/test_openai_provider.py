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

@pytest.mark.anyio
async def test_openai_llm_supports_two_sequential_tool_calls():
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
                            call_id="call_health",
                            name="get_system_health",
                            arguments='{"target":"LAB-PC"}',
                        )
                    ],
                    output_text="",
                )

            if len(requests) == 2:
                return SimpleNamespace(
                    id="resp_002",
                    output=[
                        SimpleNamespace(
                            type="function_call",
                            call_id="call_processes",
                            name="get_top_processes",
                            arguments='{"target":"LAB-PC"}',
                        )
                    ],
                    output_text="",
                )

            return SimpleNamespace(
                id="resp_003",
                output=[],
                output_text="chrome.exe is the likely cause.",
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
        ),
        ToolDefinition(
            name="get_top_processes",
            description="Get top resource-consuming processes.",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                },
                "required": ["target"],
            },
        ),
    ]

    llm = OpenAIAgentLLM(
        client=FakeOpenAIClient(),
        model="test-model",
    )

    health_call = await llm.decide(
        user_request="Why is LAB-PC slow?",
        tool_definitions=definitions,
        tool_results=[],
    )

    assert health_call == ToolCall(
        call_id="call_health",
        name="get_system_health",
        arguments={"target": "LAB-PC"},
    )

    health_result = ToolResult(
        call_id="call_health",
        name="get_system_health",
        content={
            "cpu_percent": 87.0,
            "memory": {
                "used_percent": 88.75,
            },
        },
    )

    process_call = await llm.decide(
        user_request="Why is LAB-PC slow?",
        tool_definitions=definitions,
        tool_results=[health_result],
    )

    assert process_call == ToolCall(
        call_id="call_processes",
        name="get_top_processes",
        arguments={"target": "LAB-PC"},
    )

    process_result = ToolResult(
        call_id="call_processes",
        name="get_top_processes",
        content={
            "top_by_cpu": [
                {
                    "name": "chrome.exe",
                    "pid": 4120,
                    "cpu_percent": 42.0,
                    "memory_mb": 3200.0,
                }
            ],
            "top_by_memory": [],
        },
    )

    final_decision = await llm.decide(
        user_request="Why is LAB-PC slow?",
        tool_definitions=definitions,
        tool_results=[
            health_result,
            process_result,
        ],
    )

    assert final_decision == "chrome.exe is the likely cause."

    assert requests[1]["previous_response_id"] == "resp_001"
    assert requests[1]["input"][0]["call_id"] == "call_health"

    assert requests[2]["previous_response_id"] == "resp_002"
    assert requests[2]["input"][0]["call_id"] == "call_processes"


@pytest.mark.anyio
async def test_openai_llm_disables_parallel_tool_calls():
    requests = []

    class FakeResponses:
        async def create(self, **kwargs):
            requests.append(kwargs)

            return SimpleNamespace(
                id="resp_001",
                output=[],
                output_text="Done.",
            )

    class FakeOpenAIClient:
        def __init__(self):
            self.responses = FakeResponses()

    llm = OpenAIAgentLLM(
        client=FakeOpenAIClient(),
        model="test-model",
    )

    await llm.decide(
        user_request="Why is LAB-PC slow?",
        tool_definitions=[],
        tool_results=[],
    )

    assert requests[0]["parallel_tool_calls"] is False