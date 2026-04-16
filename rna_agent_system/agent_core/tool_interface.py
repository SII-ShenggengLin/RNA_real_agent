"""Strict, auditable tool interface specification layer.

This module is intentionally decoupled from LangChain/LangGraph runtime wiring.
It defines a schema for tool metadata and IO contracts so we can:

- generate docs that match real wrapper behavior
- validate tool inputs/outputs deterministically
- constrain routing/tool selection to supported task boundaries
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field


class ToolTransport(str, Enum):
    http = "http"
    subprocess = "subprocess"
    python_api = "python_api"


class ToolStatus(str, Enum):
    available = "available"
    partial = "partial"
    unavailable = "unavailable"
    mock = "mock"


class ToolDependency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Dependency name, e.g. 'GPU', 'ViennaRNA', 'Cas-OFFinder'.")
    detail: Optional[str] = Field(default=None, description="Concrete requirement (paths, versions, etc).")


class ToolExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    input: Dict[str, Any]
    output_excerpt: Optional[Dict[str, Any]] = None


class ToolSpec(BaseModel):
    """A strict tool interface contract (metadata + IO schemas)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    identity: str = Field(..., description="Stable tool identity, typically matches LangChain tool name.")
    display_name: str = Field(..., description="Human-friendly name.")
    version: str = Field(..., description="Wrapper/microservice version (as implemented in this repo).")
    source: str = Field(..., description="Upstream repo/paper/website (URL or citation string).")

    transport: ToolTransport = Field(..., description="How this tool is invoked in this repo.")
    endpoint: Optional[str] = Field(
        default=None,
        description="HTTP endpoint URL (if transport=http) as used by wrappers (default).",
    )

    capabilities: List[str] = Field(default_factory=list, description="What the tool can do (bounded, concrete).")
    limitations: List[str] = Field(default_factory=list, description="What the tool cannot/should not do.")
    task_tags: List[str] = Field(default_factory=list, description="Tasks this tool is intended to support.")

    requires: List[ToolDependency] = Field(default_factory=list, description="Runtime dependencies/constraints.")
    produces: List[str] = Field(default_factory=list, description="Key output artifacts/fields produced.")

    input_model: Type[BaseModel] = Field(..., description="Pydantic model class for tool inputs.")
    output_model: Optional[Type[BaseModel]] = Field(
        default=None,
        description="Pydantic model class for tool outputs (wrapper return payload).",
    )

    error_model: Optional[Type[BaseModel]] = Field(
        default=None,
        description="Pydantic model class for structured errors (if implemented).",
    )

    status: ToolStatus = Field(..., description="Current support status in this repository.")
    examples: List[ToolExample] = Field(default_factory=list)

    def input_json_schema(self) -> Dict[str, Any]:
        return self.input_model.model_json_schema()

    def output_json_schema(self) -> Optional[Dict[str, Any]]:
        return self.output_model.model_json_schema() if self.output_model else None

