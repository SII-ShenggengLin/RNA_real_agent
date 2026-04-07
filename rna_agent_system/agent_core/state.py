"""State definitions for the MVP LangGraph workflow."""

from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage


class AgentState(TypedDict, total=False):
    """Shared state across all LangGraph nodes."""

    messages: list[Any]
    current_task: str
    workspace_files: list[str]
    input_sequence: str
    current_filepath: str
    candidate_sequence: str
    efficiency_score: float
    off_target_genes: int
    cai_score: float
    mfe: float
    structure_filepath: str
    design_input_pdb_filepath: str
    design_input_secondary_structure_filepath: str
    designed_sequence_fasta_filepath: str
    sequence_recovery_rate: float
    tertiary_structure_filepath: str
    tertiary_structure_ct_filepath: str
    tertiary_results_filepath: str
    tertiary_log_filepath: str
    mean_plddt: float
    ligand_smiles: str
    rnasmol_probability: float
    rnasmol_predicted_label: int
    rnasmol_checkpoint_path: str
    rnastop_prediction_filepath: str
    rnastop_mean_reactivity: float
    rnastop_mean_deg_mg_ph10: float
    rnastop_mean_deg_mg_50c: float
    rnastop_mfe: float
    rnastop_checkpoint_path: str
    design_model: str
    rnarl_model_type: str
    rnarl_checkpoint_path: str
    rnarl_esm2_model_path: str
    retry_count: int
    max_retries: int
    active_specialist: Literal["sirna_specialist", "mrna_specialist", ""]
    route: Literal["sirna", "mrna", "unsupported"]
    next_action: Literal["retry", "finish"]
    critic_verdict: Literal["pass", "reject"]
    final_report: str


def default_state(user_text: str) -> AgentState:
    """Create a default state object for one user request."""
    return AgentState(
        messages=[HumanMessage(content=user_text)],
        current_task="sirna_design",
        workspace_files=[],
        input_sequence=user_text.strip(),
        active_specialist="",
        retry_count=0,
        max_retries=3,
    )
