"""AgentState definition for the RNA Design multi-agent workflow."""

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
    crisot_score: float
    crisot_spec: float
    crisot_target_sequence: str
    crisot_input_csv_filepath: str
    crisot_output_csv_filepath: str
    crisot_genome_path: str
    crisot_off_target_count: int
    crisot_optimization_csv_filepath: str
    crisot_optimized_sgrna_filepath: str
    crisot_best_mutation: str
    crisot_best_delta_spec: float
    crisot_optimized_available: bool
    sgrna_design_generated_count: int
    sgrna_design_best_nn_score: float
    sgrna_design_best_mutation_count: int
    sgrna_design_output_filepath: str
    sgrna_design_summary_filepath: str
    sgrna_design_model_path: str
    cai_score: float
    codonw_metrics_filepath: str
    codonw_enc: float
    codonw_fop: float
    codonw_cbi: float
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
    gernabind_probability: float
    gernabind_predicted_label: int
    gernabind_checkpoint_path: str
    gernabind_preprocessing_pdb_path: str
    rnasmol_probability: float
    rnasmol_predicted_label: int
    rnasmol_checkpoint_path: str
    rnastop_prediction_filepath: str
    rnastop_mean_reactivity: float
    rnastop_mean_deg_mg_ph10: float
    rnastop_mean_deg_mg_50c: float
    rnastop_mfe: float
    rnastop_checkpoint_path: str
    iresfinder_result_tsv_filepath: str
    iresfinder_has_putative_ires: bool
    iresfinder_max_score: float
    iresfinder_best_fragment_id: str
    iresfinder_positive_count: int
    iresfinder_fragment_count: int
    iresfinder_model: str
    odesign_input_json_filepath: str
    odesign_output_dir: str
    odesign_prediction_filepaths: list[str]
    odesign_run_log_filepath: str
    odesign_model_name: str
    odesign_design_modality: str
    evitar_mode: str
    evitar_predict: str
    evitar_output_filepath: str
    evitar_result_count: int
    evitar_command: str
    vienna_sirna_duplex_mfe: float
    vienna_aso_mean_unpaired: float
    vienna_aso_joint_unpaired: float
    vienna_inverse_best_sequence: str
    blast_hit_count: int
    blast_tabular_tsv_filepath: str
    blast_subject_mode: str
    design_model: str
    rnarl_model_type: str
    rnarl_checkpoint_path: str
    rnarl_esm2_model_path: str
    retry_count: int
    max_retries: int
    active_specialist: Literal["sirna_specialist", "mrna_specialist", "crispr_specialist", ""]
    route: Literal["sirna", "mrna", "crispr", "unsupported"]
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
