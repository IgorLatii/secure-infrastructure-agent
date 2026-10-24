class ToolPolicy:
    """
    Validates whether an LLM-proposed tool call is allowed.

    The policy fails closed: only explicitly allowed tools
    and targets may proceed to execution.
    """

    def __init__(
        self,
        allowed_tools: set[str],
        allowed_targets: set[str],
    ):
        self._allowed_tools = frozenset(allowed_tools)
        self._allowed_targets = frozenset(allowed_targets)

    def validate(
        self,
        tool_name: str,
        arguments: dict,
    ) -> None:
        if tool_name not in self._allowed_tools:
            raise PermissionError(
                f"Tool is not allowed by policy: {tool_name}"
            )

        target = arguments.get("target")

        if target not in self._allowed_targets:
            raise PermissionError(
                f"Target is not allowed by policy: {target}"
            )