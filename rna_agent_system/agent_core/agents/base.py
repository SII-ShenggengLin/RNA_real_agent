"""Base abstractions for the multi-agent execution layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent_core.workflow_models import WorkflowResult


class AgentResult(BaseModel):
    """Result returned by a SpecialistAgent for one pipeline node."""

    node_id: str
    workflow: str
    success: bool
    workflow_result: WorkflowResult | None = None
    summary: str = ""
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent:
    """Base class for all agents.

    Agents are invoked through typed methods (``run()``, ``execute()``,
    ``synthesize()``); there is no message-passing protocol.
    """

    name: str = ""
