"""State definitions for the MVP LangGraph workflow."""

from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage


class AgentState(TypedDict, total=False):
    """Shared state across all LangGraph nodes."""

    messages: list[Any]
    current_task: str
    workspace_files: list[str]
    input_sequence: str
    candidate_sequence: str
    efficiency_score: float
    off_target_genes: int
    retry_count: int
    max_retries: int
    route: Literal["sirna", "unsupported"]
    next_action: Literal["retry", "finish"]
    final_report: str


def default_state(user_text: str) -> AgentState:
    """Create a default state object for one user request."""
    return AgentState(
        messages=[HumanMessage(content=user_text)],
        current_task="sirna_design",
        workspace_files=[],
        input_sequence=user_text.strip(),
        retry_count=0,
        max_retries=2,
    )
