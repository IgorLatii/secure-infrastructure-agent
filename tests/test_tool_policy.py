import pytest

from src.agent.policy.tool_policy import ToolPolicy


def test_tool_policy_allows_explicitly_allowed_tool():
    policy = ToolPolicy(
        allowed_tools={"get_system_health"},
        allowed_targets = {"LAB-PC"},
    )

    policy.validate(
        "get_system_health",
        {"target": "LAB-PC"},
    )


def test_tool_policy_rejects_unknown_tool():
    policy = ToolPolicy(
        allowed_tools={"get_system_health"},
        allowed_targets = {"LAB-PC"},
    )

    with pytest.raises(
        PermissionError,
        match="Tool is not allowed by policy: run_powershell",
    ):
        policy.validate(
            "run_powershell",
            {"target": "LAB-PC"},
        )

def test_tool_policy_rejects_disallowed_target():
    policy = ToolPolicy(
        allowed_tools={"get_system_health"},
        allowed_targets={"LAB-PC"},
    )

    with pytest.raises(
        PermissionError,
        match="Target is not allowed by policy: DC01",
    ):
        policy.validate(
            "get_system_health",
            {"target": "DC01"},
        )

def test_tool_policy_allows_service_status_when_explicitly_allowed():
    policy = ToolPolicy(
        allowed_tools={
            "get_system_health",
            "get_top_processes",
            "get_service_status",
        },
        allowed_targets={"LAB-PC"},
    )

    policy.validate(
        "get_service_status",
        {
            "target": "LAB-PC",
            "service_name": "W32Time",
        },
    )