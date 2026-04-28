"""Layer 1 — Atomic Capabilities: single-tool invocation + auto-writeback."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from agent_core.capabilities.writebacks import STANDARD_WRITEBACKS, apply_writeback
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolNotRegisteredError
from agent_core.tool_runtime import ToolResult
from agent_core.tool_specs import TOOL_SPECS


@dataclass
class CapabilityResult:
    """Normalized result of one capability invocation."""

    success: bool
    tool_name: str
    output: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    elapsed_time: float = 0.0


class Capability:
    """Wraps a single tool so the planner can invoke it like any other step.

    Layer 1 responsibilities:
    1. Invoke the underlying tool via ``ToolExecutor``.
    2. Validate the raw result against ``ToolSpec.output_model`` (if present).
    3. Write the result back to ``state["tool_results"][tool_name]`` automatically.
    """

    def __init__(
        self,
        tool_name: str,
        executor: ToolExecutor,
        *,
        state_writeback: bool = True,
        extra_writeback: Optional[Callable[[dict[str, Any], dict[str, Any]], None]] = None,
    ):
        self.tool_name = tool_name
        self.executor = executor
        self.state_writeback = state_writeback
        self._extra_writeback = extra_writeback

    @property
    def name(self) -> str:
        return self.tool_name

    @property
    def required_tools(self) -> list[str]:
        return [self.tool_name]

    def invoke(self, tool_args: dict[str, Any], state: Optional[dict[str, Any]] = None) -> CapabilityResult:
        """Run the tool and optionally write the result back to *state*."""
        result = self.executor.run_tool(self.tool_name, **tool_args)

        normalized: dict[str, Any]
        if result.success and isinstance(result.artifacts.get("result"), dict):
            normalized = dict(result.artifacts["result"])
        elif result.success:
            normalized = {"result": result.artifacts.get("result", result.artifacts)}
        else:
            normalized = {"error": result.error} if result.error else {}

        # Validate against ToolSpec output_model if available
        spec = TOOL_SPECS.get(self.tool_name)
        if spec and spec.output_model and result.success:
            try:
                validated = spec.output_model.model_validate(normalized)
                normalized = validated.model_dump(mode="json")
            except Exception:
                # Allow extra fields; validation failure is non-fatal here
                pass

        cap_result = CapabilityResult(
            success=result.success,
            tool_name=self.tool_name,
            output=normalized,
            error=json.dumps(result.error, ensure_ascii=True, default=str) if result.error else None,
            elapsed_time=result.elapsed_time,
        )

        if state is not None and self.state_writeback:
            self._writeback(state, cap_result)

        return cap_result

    def _writeback(self, state: dict[str, Any], cap_result: CapabilityResult) -> None:
        """Store the capability result under ``state["tool_results"][tool_name]``."""
        if "tool_results" not in state:
            state["tool_results"] = {}
        state["tool_results"][self.tool_name] = cap_result.output

        # Declarative backward-compatible state field writeback
        apply_writeback(state, self.tool_name, cap_result.output)

        if self._extra_writeback is not None:
            self._extra_writeback(state, cap_result.output)


class CapabilityRegistry:
    """Lightweight registry mapping capability names to ``Capability`` instances."""

    def __init__(self, executor: ToolExecutor):
        self.executor = executor
        self._capabilities: dict[str, Capability] = {}

    def register(self, tool_name: str, *, extra_writeback: Optional[Callable[[dict[str, Any], dict[str, Any]], None]] = None) -> Capability:
        """Build a ``Capability`` for *tool_name* and keep it in the registry."""
        cap = Capability(tool_name, self.executor, extra_writeback=extra_writeback)
        self._capabilities[tool_name] = cap
        return cap

    def register_many(self, tool_names: list[str]) -> None:
        for name in tool_names:
            self.register(name)

    def get(self, name: str) -> Capability:
        if name not in self._capabilities:
            raise KeyError(f"Capability '{name}' not registered")
        return self._capabilities[name]

    def has(self, name: str) -> bool:
        return name in self._capabilities

    def list_names(self) -> list[str]:
        return sorted(self._capabilities.keys())

    def snapshot(self) -> dict[str, Capability]:
        return dict(self._capabilities)


def build_default_capability_registry(executor: ToolExecutor) -> CapabilityRegistry:
    """Register capabilities for all tools that have standard writeback rules.

    This is the Layer-1 entry point used by ``AgentRunner``.
    """
    registry = CapabilityRegistry(executor)
    for tool_name in STANDARD_WRITEBACKS:
        registry.register(tool_name)
    return registry
