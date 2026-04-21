"""RNA GC content via ``rna_sequence_metrics_service`` (port 8020).

First workflow-layer integration: minimal HTTP surface, deterministic JSON, no GPU.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field

from agent_core.file_manager import PROJECT_ROOT, read_sequence
from agent_core.tool_registry import ToolRegistry
from agent_core.tool_runtime import PythonFunctionTool, ToolResult

WORKFLOW_RNA_GC_CONTENT_TOOL_NAME = "workflow_rna_gc_content"
DEFAULT_GC_SERVICE_URL = "http://127.0.0.1:8020/gc-content"


def _absolute_path_for_microservice(filepath: str) -> str:
    """Resolve workspace-relative paths to absolute paths (same contract as LangChain GC tool)."""

    path_obj = Path(filepath.strip())
    if path_obj.is_absolute():
        return str(path_obj.resolve())
    return str((PROJECT_ROOT / filepath).resolve())


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
    """Call GC microservice and return a standardized ``ToolResult``."""

    tool_name = WORKFLOW_RNA_GC_CONTENT_TOOL_NAME
    started = time.perf_counter()
    try:
        read_sequence(payload.filepath)
    except (OSError, FileNotFoundError, ValueError) as exc:
        return ToolResult(
            success=False,
            tool_name=tool_name,
            error={"type": type(exc).__name__, "message": str(exc)},
            elapsed_time=time.perf_counter() - started,
        )

    seq_abs = _absolute_path_for_microservice(payload.filepath)
    try:
        response = requests.post(
            payload.service_url,
            json={"sequence_filepath": seq_abs},
            timeout=payload.timeout_seconds,
        )
        body: dict[str, Any]
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not response.ok:
            detail = body.get("detail", response.text)
            return ToolResult(
                success=False,
                tool_name=tool_name,
                stderr=response.text[:2000],
                error={
                    "type": "HTTPError",
                    "status_code": response.status_code,
                    "detail": detail if isinstance(detail, str) else json.dumps(detail, default=str),
                },
                artifacts={"http_body": body} if body else {},
                elapsed_time=time.perf_counter() - started,
            )

        gc_content = float(body.get("gc_content", 0.0))
        sequence_length = int(body.get("sequence_length", 0))
        gc_count = int(body.get("gc_count", 0))
        metrics = {
            "gc_content": gc_content,
            "sequence_length": sequence_length,
            "gc_count": gc_count,
        }
        artifacts = {
            "input_filepath": payload.filepath,
            "resolved_filepath": str(body.get("resolved_filepath", "")),
            "sequence_length": sequence_length,
            "g_count": int(body.get("g_count", 0)),
            "c_count": int(body.get("c_count", 0)),
            "gc_count": gc_count,
            "gc_content": gc_content,
            "model": str(body.get("model", "rna-sequence-metrics-gc")),
        }
        return ToolResult(
            success=True,
            tool_name=tool_name,
            artifacts=artifacts,
            metrics=metrics,
            elapsed_time=time.perf_counter() - started,
        )
    except requests.RequestException as exc:
        return ToolResult(
            success=False,
            tool_name=tool_name,
            error={"type": type(exc).__name__, "message": str(exc)},
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
