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
    candidate_sequence: str
    # Retry / execution control
    retry_count: int
    max_retries: int
    # Generic tool results container (no tool-specific keys at top level)
    tool_results: dict[str, Any]
    # Workflow output
    workflow_result: Any
    final_report: str
    # JSON-serialized PipelineResult for single/multi-node pipeline audits.
    pipeline_result: dict[str, Any]
    # Internal execution metadata
    _execution_plan: Any
    _execution_log: list[dict[str, Any]]
    _quality_review_enabled: bool
    _quality_auto_retry: bool
    _parameter_overrides: dict[str, Any]
    _last_workflow_params: dict[str, Any]
    _last_workflow_target: str
    # Form-based parameter state
    _form_params: dict[str, Any]                 # current turn form params
    _last_form_params: dict[str, Any]            # previous turn form params (same workflow)
    _last_form_params_by_workflow: dict[str, dict[str, Any]]  # per-workflow history
    _user_explicit_params: list[str]             # params the user explicitly filled this turn
    _diagnosis_history: list[dict[str, Any]]
    _quality_review_error: dict[str, Any]
    _plan_executed: bool
    # Transient cross-turn context used by QualityAgent and CLI report generation
    _previous_workflow_result: Any
    # Multi-turn workflow result history, allowing the CLI/LLM report to reference
    # any earlier turn (e.g. "与第一轮对比") instead of only the immediately
    # previous turn. Each entry is a snapshot of that turn's ``workflow_result``.
    _workflow_result_history: list[Any]

def default_state(user_text: str) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=user_text)],
        current_task="mrna_design",
        workspace_files=[],
        input_sequence=user_text.strip(),
        retry_count=0,
        max_retries=3,
    )
