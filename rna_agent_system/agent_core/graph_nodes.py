"""Thin LangGraph node wrappers around the five-layer architecture."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END

from agent_core.capabilities.base import build_default_capability_registry
from agent_core.planning.base import ExecutionController, ExecutionPlan
from agent_core.planning.rule_based.planner import RuleBasedPlanner
from agent_core.planning.rule_based.parsers.common import (
    _needs_dot_bracket_unpaired_fraction_metric,
    _needs_iresfinder_prediction,
    _needs_rna_gc_content_metric,
    _needs_rna_plfold_local_profile,
    _needs_rnastop_prediction,
    _needs_ribodiffusion_design,
    _needs_structure_to_sequence_design,
)
from agent_core.state import AgentState, default_state
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflows import MrnaCdsDesignWorkflow

# ═══════════════════════════════════════════════════════════════════════════════
# Module-level singletons (mirrors AgentRunner composition)
# ═══════════════════════════════════════════════════════════════════════════════

_planner = RuleBasedPlanner()
_executor = ToolExecutor(build_default_tool_registry(include_demo=False))
_capability_registry = build_default_capability_registry(_executor)
_workflow_registry: dict[str, Any] = {
    "mrna_cds_design": MrnaCdsDesignWorkflow(_capability_registry),
}
_controller = ExecutionController(
    capability_registry=_capability_registry,
    workflow_registry=_workflow_registry,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Critic final-report fields (preserves backward-compatible state summary)
# ═══════════════════════════════════════════════════════════════════════════════

_FLOAT_FIELDS = [
    "crisot_score","crisot_spec","crisot_best_delta_spec","sgrna_design_best_nn_score",
    "sgrna_design_score_nn_score","sgrna_design_score_log_likelihood","cai_score",
    "codonw_enc","codonw_fop","codonw_cbi","codonw_hydropathy","codonw_aromaticity",
    "mfe","mean_plddt","gernabind_probability","rnasmol_probability","rnastop_mean_reactivity",
    "rnastop_mean_deg_mg_ph10","rnastop_mean_deg_mg_50c","rnastop_overall_stability","rnastop_mfe",
    "iresfinder_max_score","iresfinder_decision_threshold","vienna_sirna_duplex_mfe",
    "vienna_rnaup_interaction_energy","vienna_aso_mean_unpaired","vienna_aso_joint_unpaired",
    "sequence_gc_content","dot_bracket_unpaired_fraction","evitar_umcuff","evitar_mircuff",
    "evitar_maxgc","evitar_mingc","evitar_middlegc","crisot_off_target_count",
    "sgrna_design_generated_count","sgrna_design_best_mutation_count",
    "sgrna_design_score_constraint_mutation_count","codonw_genetic_code","codonw_cds_length_nt",
    "codonw_cds_length_codons","sequence_recovery_rate",
]
_INT_FIELDS = [
    "crisot_rescore_sgrna_count","gernabind_predicted_label","rnasmol_predicted_label",
    "iresfinder_positive_count","iresfinder_fragment_count","iresfinder_mode",
    "iresfinder_window_size","iresfinder_step_size","blast_hit_count","evitar_result_count",
    "evitar_limitnum","evitar_repeatnum","evitar_pmcuff",
]
_BOOL_FIELDS = ["crisot_optimized_available","iresfinder_has_putative_ires","evitar_off_target"]
_LIST_FIELDS = ["odesign_prediction_filepaths"]
_DICT_FIELDS = ["codonw_silent_base_usage","codonw_bases2"]
_STR_FIELDS = [
    "crisot_target_sequence","crisot_input_csv_filepath","crisot_output_csv_filepath",
    "crisot_genome_path","crisot_optimization_csv_filepath","crisot_optimized_sgrna_filepath",
    "crisot_best_mutation","crisot_scores_csv_filepath","crisot_rescore_csv_filepath",
    "crisot_fp_csv_filepath","crisot_fp_xgb_model","crisot_genfp_csv_filepath",
    "sgrna_design_seed_sequence","sgrna_design_best_log_likelihood","sgrna_design_sampling_mode",
    "sgrna_design_output_filepath","sgrna_design_output_ali_filepath","sgrna_design_summary_filepath",
    "sgrna_design_model_path","sgrna_design_score_sequence","codonw_metrics_filepath",
    "codonw_normalization_note","design_model","rnarl_model_type","rnarl_checkpoint_path",
    "rnarl_esm2_model_path","design_input_pdb_filepath","designed_sequence_fasta_filepath",
    "tertiary_structure_filepath","ligand_smiles","gernabind_checkpoint_path",
    "gernabind_preprocessing_pdb_path","rnasmol_checkpoint_path","rnastop_prediction_filepath",
    "rnastop_checkpoint_path","iresfinder_result_tsv_filepath","iresfinder_best_fragment_id",
    "iresfinder_model","odesign_input_json_filepath","odesign_output_dir","odesign_run_log_filepath",
    "odesign_model_name","odesign_design_modality","evitar_mode","evitar_predict",
    "evitar_output_filepath","evitar_command","evitar_p3utr_path","evitar_transcriptome_path",
    "evitar_weight_path","evitar_sumtype","evitar_allow_path","evitar_ban_path",
    "vienna_rnaup_interaction_structure","vienna_inverse_best_sequence","blast_tabular_tsv_filepath",
    "blast_subject_mode","blast_hits_preview","blast_blastn_command","blast_resolved_query_path",
    "blast_resolved_subject",
]


def _build_final_report(state: dict[str, Any], specialist: str, mfe: float, retry_count: int) -> str:
    """Build a compact backward-compatible summary string."""
    parts: list[str] = [f"specialist={specialist}", f"filepath={state.get('current_filepath', '')}"]
    for key in _FLOAT_FIELDS:
        parts.append(f"{key}={state.get(key, 0.0)}")
    for key in _INT_FIELDS:
        parts.append(f"{key}={state.get(key, 0)}")
    for key in _BOOL_FIELDS:
        parts.append(f"{key}={state.get(key, False)}")
    for key in _LIST_FIELDS:
        parts.append(f"{key}={state.get(key, [])}")
    for key in _DICT_FIELDS:
        parts.append(f"{key}={state.get(key, {})}")
    for key in _STR_FIELDS:
        value = state.get(key, "")
        if key in ("blast_hits_preview", "blast_blastn_command") and isinstance(value, str):
            value = value[:80]
        parts.append(f"{key}={value}")
    parts.append(f"retries={retry_count}")
    return "; ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# Node implementations
# ═══════════════════════════════════════════════════════════════════════════════


def router_node(state: AgentState) -> AgentState:
    """Route by deterministic rules without LLM.

    Delegates to ``RuleBasedPlanner.plan_with_state`` so that workspace file
    preparation and plan construction happen in one place.
    """
    user_text = state.get("input_sequence", "")
    plan = _planner.plan_with_state(user_text, state)
    state["_execution_plan"] = plan.model_dump(mode="json")

    route = state.get("route", "mrna")
    state["active_specialist"] = {
        "sirna": "sirna_specialist",
        "mrna": "mrna_specialist",
        "crispr": "crispr_specialist",
    }.get(route, "mrna_specialist")

    state["messages"] = state.get("messages", []) + [
        AIMessage(content=f"Router decision (rule-based): {route}")
    ]
    return state


def tool_execution_node(state: AgentState) -> AgentState:
    """Execute the plan produced by the router."""
    plan_data = state.get("_execution_plan")
    if not plan_data:
        return state
    plan = ExecutionPlan.model_validate(plan_data)
    return _controller.execute(plan, state)


def critic_node(state: AgentState) -> AgentState:
    """Use hard rules only (no LLM) to decide pass/reject."""
    mfe = state.get("mfe", 0.0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    specialist = state.get("active_specialist", "")
    user_text = state.get("input_sequence", "").lower()
    raw_user = state.get("input_sequence", "")

    hard_reject = (
        specialist == "mrna_specialist"
        and not _needs_rnastop_prediction(user_text)
        and not _needs_iresfinder_prediction(user_text)
        and not _needs_structure_to_sequence_design(user_text)
        and not _needs_ribodiffusion_design(user_text)
        and not _needs_rna_gc_content_metric(user_text)
        and not _needs_dot_bracket_unpaired_fraction_metric(user_text)
        and not _needs_rna_plfold_local_profile(raw_user)
        and any(k in user_text for k in ["structure", "fold", "rnafold", "二级结构", "linearfold"])
        and mfe > -20.0
    )
    should_retry = hard_reject and retry_count < max_retries

    if should_retry:
        state["retry_count"] = retry_count + 1
        state["next_action"] = "retry"
        state["critic_verdict"] = "reject"
        state["messages"] = state.get("messages", []) + [
            AIMessage(
                content=(
                    f"Critic (rule-based): reject and retry. "
                    f"specialist={specialist}, mfe={mfe}, retry={retry_count + 1}"
                )
            )
        ]
    else:
        state["next_action"] = "finish"
        state["critic_verdict"] = "pass"
        state["final_report"] = _build_final_report(state, specialist, mfe, retry_count)
        state["messages"] = state.get("messages", []) + [
            AIMessage(
                content=(
                    f"Critic (rule-based): pass. "
                    f"specialist={specialist}, mfe={mfe}"
                )
            )
        ]
    return state


def route_after_critic(state: AgentState) -> str:
    """Choose whether to retry or finish."""
    if state.get("next_action") != "retry":
        return END
    return "tool_execution"
