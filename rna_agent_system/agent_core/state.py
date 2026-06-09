"""AgentState definition for the RNA Design multi-agent workflow."""
from typing import Any, TypedDict
from langchain_core.messages import HumanMessage

class AgentState(TypedDict, total=False):
    """Shared state — framework fields only; tool results live in ``tool_results``."""
    # User / session
    messages: list[Any]
    current_task: str
    user_text: str
    session_id: str
    # Workspace / shared design state
    workspace_files: list[str]
    input_sequence: str
    current_filepath: str
    candidate_sequence: str
    # Retry / execution control
    retry_count: int
    max_retries: int
    # Generic tool results container (no tool-specific keys at top level)
    tool_results: dict[str, Any]
    # Workflow output
    workflow_result: Any
    final_report: str
    # Internal execution metadata
    _execution_plan: Any
    _available_capabilities: list[str]
    _available_workflows: list[str]
    _workflow_param_schemas: dict[str, str]
    _execution_log: list[dict[str, Any]]
    _llm_critic_enabled: bool
    _critic_should_retry: bool
    _parameter_overrides: dict[str, Any]
    _last_workflow_params: dict[str, Any]
    _last_workflow_target: str
    _diagnosis_history: list[dict[str, Any]]
    _llm_critic_error: dict[str, Any]
    _plan_executed: bool

def default_state(user_text: str) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=user_text)],
        current_task="mrna_design",
        workspace_files=[],
        input_sequence=user_text.strip(),
        retry_count=0,
        max_retries=3,
    )
