"""RNA GC content via ``rna_sequence_metrics_service`` (port 8020).

Workflow-layer integration: delegates to the canonical LangChain tool
``compute_rna_sequence_gc_content`` so HTTP logic is not duplicated.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agent_core.tools import compute_rna_sequence_gc_content
from agent_core.tool_registry import ToolRegistry
from agent_core.tool_runtime import PythonFunctionTool, ToolResult

WORKFLOW_RNA_GC_CONTENT_TOOL_NAME = "workflow_rna_gc_content"
DEFAULT_GC_SERVICE_URL = "http://127.0.0.1:8020/gc-content"


class RnaGcContentWorkflowInput(BaseModel):
    """Input for workflow GC tool."""

    model_config = ConfigDict(extra="forbid")

    filepath: str = Field(
        ...,
        description="Sequence file under workspace/ or absolute path on the server.",
    )
    service_url: str = Field(
        default=DEFAULT_GC_SERVICE_URL,
        description="POST /gc-content URL for rna_sequence_metrics_service.",
    )
    timeout_seconds: float = Field(default=120.0, gt=0, le=600)


def run_rna_gc_content_workflow(payload: RnaGcContentWorkflowInput) -> ToolResult:
    """Call GC microservice via the canonical LangChain tool and return a ``ToolResult``."""

    tool_name = WORKFLOW_RNA_GC_CONTENT_TOOL_NAME
    started = time.perf_counter()
    try:
        result: dict[str, Any] = compute_rna_sequence_gc_content.invoke(
            {
                "filepath": payload.filepath,
                "service_url": payload.service_url,
                "timeout_seconds": payload.timeout_seconds,
            }
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool_name=tool_name,
            error={"type": type(exc).__name__, "message": str(exc)},
            elapsed_time=time.perf_counter() - started,
        )

    gc_content = float(result.get("gc_content", 0.0))
    sequence_length = int(result.get("sequence_length", 0))
    gc_count = int(result.get("gc_count", 0))
    metrics = {
        "gc_content": gc_content,
        "sequence_length": sequence_length,
        "gc_count": gc_count,
    }
    artifacts = {
        "input_filepath": result.get("input_filepath", payload.filepath),
        "resolved_filepath": str(result.get("resolved_filepath", "")),
        "sequence_length": sequence_length,
        "g_count": int(result.get("g_count", 0)),
        "c_count": int(result.get("c_count", 0)),
        "gc_count": gc_count,
        "gc_content": gc_content,
        "model": str(result.get("model", "rna-sequence-metrics-gc")),
    }
    return ToolResult(
        success=True,
        tool_name=tool_name,
        artifacts=artifacts,
        metrics=metrics,
        elapsed_time=time.perf_counter() - started,
    )


def create_workflow_rna_gc_content_tool(
    *,
    timeout_seconds: float = 125.0,
) -> PythonFunctionTool:
    """Build a ``PythonFunctionTool`` for registry / executor use."""

    return PythonFunctionTool(
        name=WORKFLOW_RNA_GC_CONTENT_TOOL_NAME,
        description=(
            "RNA (G+C) fraction via rna_sequence_metrics_service POST /gc-content (port 8020). "
            "Inputs a sequence filepath; returns gc_content and counts in metrics."
        ),
        func=run_rna_gc_content_workflow,
        input_model=RnaGcContentWorkflowInput,
        timeout_seconds=timeout_seconds,
    )


def register_workflow_rna_gc_content_tool(registry: ToolRegistry, *, timeout_seconds: float = 125.0) -> PythonFunctionTool:
    """Register the workflow GC tool on an existing ``ToolRegistry``."""

    tool = create_workflow_rna_gc_content_tool(timeout_seconds=timeout_seconds)
    registry.register(tool)
    return tool
