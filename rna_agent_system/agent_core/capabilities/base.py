"""Layer 1 — Atomic Capabilities: single-tool invocation, result returned to caller."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from agent_core.tool_executor import ToolExecutor
from agent_core.tool_specs import TOOL_SPECS


# Well-known parameters that distinguish repeated invocations of the same tool.
# Used to build human-readable, non-overlapping keys in state["tool_results"].
_DISTINGUISHING_PARAMS = (
    "lambda_value",
    "model_type",
    "utr_length",
    "preset",
    "mode",
    "species",
)


def _unique_tool_result_key(
    tool_name: str,
    tool_args: dict[str, Any],
    existing_keys: set[str],
) -> str:
    """Return a unique, human-readable key for a tool invocation.

    Prefers well-known distinguishing parameters (e.g. ``lambda_value``) so that
    repeated calls with different arguments (LinearDesign with λ=1.0 vs λ=0.5)
    do not overwrite each other. Falls back to a numeric index when no such
    parameter is present.
    """
    for param in _DISTINGUISHING_PARAMS:
        value = tool_args.get(param)
        if value is not None:
            safe = re.sub(r"[^\w\.\-]+", "_", str(value)).strip("_") or "none"
            candidate = f"{tool_name}_{param}_{safe}"
            if candidate not in existing_keys:
                return candidate
            prefix = f"{candidate}_"
            idx = sum(1 for k in existing_keys if k.startswith(prefix))
            return f"{candidate}_{idx}"

    prefix = f"{tool_name}_"
    idx = sum(1 for k in existing_keys if k.startswith(prefix))
    return f"{tool_name}_{idx}"


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
    3. Return a normalized ``CapabilityResult`` — the caller decides where to
       store it (typically ``state["tool_results"][tool_name]``).
    """

    def __init__(self, tool_name: str, executor: ToolExecutor):
        self.tool_name = tool_name
        self.executor = executor

    @property
    def name(self) -> str:
        return self.tool_name

    def invoke(self, tool_args: dict[str, Any], state: Optional[dict[str, Any]] = None) -> CapabilityResult:
        """Run the tool and return a normalized ``CapabilityResult``.

        When *state* is provided the raw output is stored under
        ``state["tool_results"][tool_name]`` for backward compatibility.
        Top-level state fields are **never** written by this method.
        """
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

        # Minimal backward-compatible writeback: store raw output in the
        # generic tool_results bucket.  Top-level state fields are never touched.
        if state is not None:
            state.setdefault("tool_results", {})
            # Keep the original key pointing to the latest result (backward compatible).
            state["tool_results"][self.tool_name] = normalized
            # Also store a uniquely-keyed copy so repeated calls to the same tool
            # (e.g. LinearDesign with different lambdas) are all visible in audit JSON.
            unique_key = _unique_tool_result_key(
                self.tool_name, tool_args, set(state["tool_results"].keys())
            )
            state["tool_results"][unique_key] = normalized

            # Record per-tool elapsed time for auditability.
            state.setdefault("_tool_timings", {})
            state["_tool_timings"][self.tool_name] = result.elapsed_time
            state["_tool_timings"][unique_key] = result.elapsed_time

        return cap_result


class CapabilityRegistry:
    """Lightweight registry mapping capability names to ``Capability`` instances."""

    def __init__(self, executor: ToolExecutor):
        self.executor = executor
        self._capabilities: dict[str, Capability] = {}

    def register(self, tool_name: str) -> Capability:
        """Build a ``Capability`` for *tool_name* and keep it in the registry."""
        cap = Capability(tool_name, self.executor)
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
    """Register capabilities for all tools present in the executor registry.

    This is the Layer-1 entry point used by ``AgentRunner``.
    """
    registry = CapabilityRegistry(executor)
    for tool_name in executor.registry.list_names():
        registry.register(tool_name)
    return registry
