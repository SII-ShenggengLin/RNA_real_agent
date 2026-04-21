"""Dispatch tools by name and attach trace records to workflow models."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Optional

from agent_core.tool_registry import ToolNotRegisteredError, ToolRegistry
from agent_core.tool_runtime import ToolResult
from agent_core.workflow_models import Candidate, TaskState, ToolCallRecord

_LOGGER = logging.getLogger(__name__)


def _truncate(text: str, limit: int = 400) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 15] + "...(truncated)"


def _summarize_kwargs(kwargs: dict[str, Any]) -> str:
    """Short string for logs (avoid dumping huge sequences)."""

    try:
        payload = json.dumps(kwargs, ensure_ascii=True, default=str)
    except TypeError:
        payload = str(kwargs)
    return _truncate(payload, limit=500)


def _summarize_payload(payload: Any) -> str:
    try:
        text = json.dumps(payload, ensure_ascii=True, default=str)
    except TypeError:
        text = str(payload)
    return _truncate(text, limit=600)


def build_default_tool_registry(*, include_demo: bool = False) -> ToolRegistry:
    """Populate registry with LangChain tools from ``agent_core.tools``.

    Parameters
    ----------
    include_demo:
        When True, also registers ``workflow_demo_echo`` for smoke tests.
    """

    from agent_core import tools as tools_mod

    names = list(tools_mod.ALL_LANGCHAIN_AGENT_TOOLS)
    if include_demo:
        names.extend(tools_mod.WORKFLOW_DEMO_LANGCHAIN_TOOLS)
    registry = ToolRegistry()
    registry.register_many(names)
    return registry


class ToolExecutor:
    """Resolve tools via ``ToolRegistry``, invoke LangChain ``.invoke``, normalize output."""

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        logger: Optional[logging.Logger] = None,
        result_normalizer: Optional[Callable[[str, Any], ToolResult]] = None,
    ):
        self.registry = registry
        self.logger = logger or _LOGGER
        self._normalizer = result_normalizer or self._default_normalize_result

    @staticmethod
    def _default_normalize_result(tool_name: str, raw: Any) -> ToolResult:
        """Wrap LangChain tool return value into ``ToolResult``."""

        if isinstance(raw, ToolResult):
            out = raw
            if out.tool_name != tool_name:
                out.tool_name = tool_name
            return out
        if isinstance(raw, dict):
            metrics = {k: raw[k] for k in raw if isinstance(raw[k], (int, float))}
            return ToolResult(
                success=True,
                tool_name=tool_name,
                artifacts={"result": raw},
                metrics=metrics,
            )
        return ToolResult(
            success=True,
            tool_name=tool_name,
            artifacts={"result": raw},
            metrics={},
        )

    def run_tool(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Invoke tool by name with standardized success/error handling."""

        started = time.perf_counter()
        try:
            tool_obj = self.registry.get(tool_name)
        except ToolNotRegisteredError as exc:
            elapsed = time.perf_counter() - started
            self.logger.warning("tool not registered: %s", exc.tool_name)
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error={
                    "type": "ToolNotRegisteredError",
                    "message": str(exc),
                    "tool_name": exc.tool_name,
                },
                elapsed_time=elapsed,
            )

        self.logger.info("tool invoke start name=%s kwargs=%s", tool_name, _summarize_kwargs(kwargs))
        try:
            raw = tool_obj.invoke(kwargs)
            result = self._normalizer(tool_name, raw)
            if result.elapsed_time <= 0:
                result.elapsed_time = time.perf_counter() - started
            self.logger.info(
                "tool invoke ok name=%s elapsed=%.4fs success=%s",
                tool_name,
                result.elapsed_time,
                result.success,
            )
            return result
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self.logger.exception("tool invoke failed name=%s", tool_name)
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error={"type": type(exc).__name__, "message": str(exc)},
                elapsed_time=elapsed,
            )

    def run_tool_for_workflow(
        self,
        tool_name: str,
        *,
        task: TaskState,
        candidate: Optional[Candidate] = None,
        step_name: str = "tool",
        write_candidate: bool = True,
        write_task_log: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        """Run tool and append a ``ToolCallRecord`` to candidate and/or task logs."""

        result = self.run_tool(tool_name, **kwargs)
        if result.success:
            output_summary = _summarize_payload(result.artifacts.get("result", result.metrics))
        else:
            output_summary = _summarize_payload(result.error if result.error is not None else result.artifacts)
        record = ToolCallRecord(
            step_name=step_name,
            tool_name=tool_name,
            input_summary=_summarize_kwargs(kwargs),
            output_summary=output_summary,
            success=result.success,
            error=(
                json.dumps(result.error, ensure_ascii=True)
                if isinstance(result.error, dict)
                else (str(result.error) if result.error else None)
            ),
            elapsed_time=result.elapsed_time,
            artifacts=dict(result.artifacts),
            metrics=dict(result.metrics),
        )
        if candidate is not None and write_candidate:
            candidate.add_tool_record(record)
        if write_task_log:
            task.append_log(record)
        return result
