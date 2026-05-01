"""Declarative state writeback mappings for Layer-1 capabilities.

Each entry maps a *capability name* → a dict of ``{output_field: state_field}``.
When a capability finishes, its normalized output is scanned against this map
and matching values are written back into the shared state dict.

This replaces the ~800-line ``if-elif`` block in ``nodes.py``
``tool_execution_node`` for the tools registered here.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

# Mapping: capability_name -> {output_field: state_field}
# If state_field is a callable, it receives (state, output_value) and mutates state.
WritebackRule = Dict[str, str]


STANDARD_WRITEBACKS: dict[str, WritebackRule] = {
    # ═══════════════════════════════════════════════════════════════════════
    # GC content (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "compute_rna_sequence_gc_content": {
        "gc_content": "sequence_gc_content",
        "sequence_length": "sequence_gc_length",
        "gc_count": "sequence_gc_count",
        "g_count": "sequence_g_count",
        "c_count": "sequence_c_count",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # U content (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "compute_rna_sequence_u_content": {
        "u_fraction": "sequence_u_fraction",
        "sequence_length": "sequence_u_length",
        "u_count": "sequence_u_count",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # CAI for CDS (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "compute_cai_for_cds_sequence": {
        "cai_score": "cai_for_cds_score",
        "species": "cai_for_cds_species",
        "cds_length_nt": "cai_for_cds_length_nt",
        "codon_count": "cai_for_cds_codon_count",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # Dot-bracket unpaired fraction (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "compute_dot_bracket_unpaired_fraction": {
        "unpaired_fraction": "dot_bracket_unpaired_fraction",
        "structure_length": "dot_bracket_structure_length",
        "dot_count": "dot_bracket_dot_count",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # codonw-slim (v0.2.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "analyze_cds_codon_metrics_with_codonw_slim": {
        "cai_score": "cai_score",
        "enc": "codonw_enc",
        "fop": "codonw_fop",
        "cbi": "codonw_cbi",
        "hydropathy": "codonw_hydropathy",
        "aromaticity": "codonw_aromaticity",
        "genetic_code": "codonw_genetic_code",
        "cds_length_nt": "codonw_cds_length_nt",
        "cds_length_codons": "codonw_cds_length_codons",
        "normalization_note": "codonw_normalization_note",
        "silent_base_usage": "codonw_silent_base_usage",
        "bases2": "codonw_bases2",
        "codon_usage": "codonw_codon_usage",
        "rscu": "codonw_rscu",
        "dinuc": "codonw_dinuc",
        "aa_usage": "codonw_aa_usage",
        "raau": "codonw_raau",
        "bases": "codonw_bases",
        "metrics_json_filepath": "codonw_metrics_filepath",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # ViennaRNA fold (v0.4.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "predict_rna_secondary_structure": {
        "mfe_kcal_per_mol": "mfe",
        "structure": "_auto_structure_filepath",  # handled by helper
    },
    # ═══════════════════════════════════════════════════════════════════════
    # LinearFold fold (v0.2.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "predict_rna_secondary_structure_with_linearfold": {
        "mfe": "mfe",
        "structure": "_auto_structure_filepath",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # LinearDesign single (v0.2.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "design_mrna_cds_with_lineardesign": {
        "output_filepath": "current_filepath",
        "generated_sequence": "candidate_sequence",
        "mfe": "mfe",
        "cai_score": "cai_score",
        "structure": "_auto_structure_filepath",
        # LinearDesign-specific fields
        "lambda_value": "lineardesign_lambda_value",
        "codon_usage_path": "lineardesign_codon_usage_path",
        "raw_output": "lineardesign_raw_output",
        "stderr": "lineardesign_stderr",
        "model": "lineardesign_model",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # LinearDesign batch (v0.2.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "design_mrna_cds_batch_with_lineardesign": {
        "output_filepath": "current_filepath",
        "best_generated_sequence": "candidate_sequence",
        "best_mfe": "mfe",
        "best_cai_score": "cai_score",
        "best_structure": "_auto_structure_filepath",
        "lambda_value": "lineardesign_lambda_value",
        "codon_usage_path": "lineardesign_codon_usage_path",
        "batch_json_filepath": "lineardesign_batch_json_filepath",
        "count": "lineardesign_batch_count",
        "success_count": "lineardesign_batch_success_count",
        "model": "lineardesign_model",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # GEMORNA / RNARL / UTR design
    # ═══════════════════════════════════════════════════════════════════════
    "design_mrna_cds_with_gemorna": {
        "output_filepath": "current_filepath",
        "generated_sequence": "candidate_sequence",
        "model": "design_model",
    },
    "design_mrna_cds_with_rnarl": {
        "output_filepath": "current_filepath",
        "generated_sequence": "candidate_sequence",
        "model_type": "rnarl_model_type",
        "checkpoint_path": "rnarl_checkpoint_path",
        "esm2_model_path": "rnarl_esm2_model_path",
        "model": "design_model",
    },
    "design_5utr_with_gemorna": {
        "output_filepath": "current_filepath",
        "generated_sequence": "candidate_sequence",
        "model": "design_model",
    },
    "design_3utr_with_gemorna": {
        "output_filepath": "current_filepath",
        "generated_sequence": "candidate_sequence",
        "model": "design_model",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # GEMORNA UTR prediction (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "predict_5utr_mrl_with_gemorna": {
        "input_filepath": "current_filepath",
        "input_sequence": "candidate_sequence",
        "predicted_mrl": "gemorna_5utr_predicted_mrl",
        "model": "gemorna_5utr_mrl_model",
    },
    "predict_3utr_stability_with_gemorna": {
        "input_filepath": "current_filepath",
        "input_sequence": "candidate_sequence",
        "predicted_stability": "gemorna_3utr_predicted_stability",
        "model": "gemorna_3utr_stability_model",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # RhoFold tertiary structure (v0.2.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "predict_rna_tertiary_structure_with_rhofold": {
        "pdb_filepath": "tertiary_structure_filepath",
        "ct_filepath": "tertiary_structure_ct_filepath",
        "results_filepath": "tertiary_results_filepath",
        "log_filepath": "tertiary_log_filepath",
        "mean_plddt": "mean_plddt",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # RNASTOP (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "predict_mrna_stability_with_rnastop": {
        "prediction_filepath": "rnastop_prediction_filepath",
        "sequence": "rnastop_sequence",
        "used_sequence": "rnastop_used_sequence",
        "structure": "rnastop_structure",
        "loop_type": "rnastop_loop_type",
        "mean_reactivity": "rnastop_mean_reactivity",
        "mean_deg_mg_ph10": "rnastop_mean_deg_mg_ph10",
        "mean_deg_mg_50c": "rnastop_mean_deg_mg_50c",
        "overall_stability": "rnastop_overall_stability",
        "mfe": "rnastop_mfe",
        "checkpoint_path": "rnastop_checkpoint_path",
        "device": "rnastop_device",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # IRESfinder (v0.2.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "predict_putative_ires_with_iresfinder": {
        "result_tsv_filepath": "iresfinder_result_tsv_filepath",
        "has_putative_ires": "iresfinder_has_putative_ires",
        "max_score": "iresfinder_max_score",
        "best_fragment_id": "iresfinder_best_fragment_id",
        "positive_count": "iresfinder_positive_count",
        "fragment_count": "iresfinder_fragment_count",
        "model": "iresfinder_model",
        "mode": "iresfinder_mode",
        "window_size": "iresfinder_window_size",
        "step_size": "iresfinder_step_size",
        "decision_threshold": "iresfinder_decision_threshold",
        "predictions": "iresfinder_predictions",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # BLAST+ (v0.2.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "run_blastn_similarity_search": {
        "hit_count": "blast_hit_count",
        "subject_mode": "blast_subject_mode",
        "hits_preview": "blast_hits_preview",
        "preview_truncated": "blast_preview_truncated",
        "blastn_command": "blast_blastn_command",
        "resolved_query_path": "blast_resolved_query_path",
        "resolved_subject": "blast_resolved_subject",
        "tabular_tsv_filepath": "blast_tabular_tsv_filepath",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # Evitar (v0.2.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "design_sirna_with_evitar": {
        "output_filepath": "current_filepath",
        "mode": "evitar_mode",
        "predict": "evitar_predict",
        "result_count": "evitar_result_count",
        "command": "evitar_command",
        "strains_path": "evitar_strains_path",
        "off_target": "evitar_off_target",
        "p3utr_path": "evitar_p3utr_path",
        "transcriptome_path": "evitar_transcriptome_path",
        "weight_path": "evitar_weight_path",
        "sumtype": "evitar_sumtype",
        "limitnum": "evitar_limitnum",
        "repeatnum": "evitar_repeatnum",
        "pmcuff": "evitar_pmcuff",
        "umcuff": "evitar_umcuff",
        "mircuff": "evitar_mircuff",
        "maxgc": "evitar_maxgc",
        "mingc": "evitar_mingc",
        "middlegc": "evitar_middlegc",
        "allow_path": "evitar_allow_path",
        "ban_path": "evitar_ban_path",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # CRISOT / CRGPT
    # ═══════════════════════════════════════════════════════════════════════
    "score_crispr_off_target_with_crisot": {
        "sgrna": "candidate_sequence",
        "target_sequence": "crisot_target_sequence",
        "crisot_score": "crisot_score",
    },
    "calculate_crispr_specificity_with_crisot": {
        "input_csv_filepath": "crisot_input_csv_filepath",
        "crisot_spec": "crisot_spec",
        "scored_csv_filepath": "crisot_output_csv_filepath",
    },
    "search_crispr_off_targets_with_crisot": {
        "sgrna": "candidate_sequence",
        "target_sequence": "crisot_target_sequence",
        "genome_path": "crisot_genome_path",
        "crisot_spec": "crisot_spec",
        "off_target_count": "crisot_off_target_count",
        "scored_csv_filepath": "crisot_output_csv_filepath",
    },
    "optimize_sgrna_with_crisot": {
        "target_sequence": "crisot_target_sequence",
        "genome_path": "crisot_genome_path",
        "optimized_available": "crisot_optimized_available",
        "best_sgrna": "candidate_sequence",
        "best_mutation": "crisot_best_mutation",
        "best_delta_spec": "crisot_best_delta_spec",
        "best_crisot_score": "crisot_score",
        "best_crisot_spec": "crisot_spec",
        "optimization_csv_filepath": "crisot_optimization_csv_filepath",
        "optimized_sgrna_filepath": "crisot_optimized_sgrna_filepath",
    },
    "score_batch_crispr_off_targets_with_crisot": {
        "input_csv_filepath": "crisot_input_csv_filepath",
        "scored_csv_filepath": "crisot_scores_csv_filepath",
    },
    "rescore_sgrnas_with_crisot": {
        "genome_path": "crisot_genome_path",
        "sgrna_count": "crisot_rescore_sgrna_count",
        "rescore_csv_filepath": "crisot_rescore_csv_filepath",
    },
    "predict_crispr_off_target_with_crisot_fp": {
        "input_csv_filepath": "crisot_input_csv_filepath",
        "xgb_model": "crisot_fp_xgb_model",
        "fp_csv_filepath": "crisot_fp_csv_filepath",
    },
    "generate_crispr_fingerprint_with_crisot": {
        "target_sequence": "crisot_target_sequence",
        "fp_csv_filepath": "crisot_genfp_csv_filepath",
    },
    "design_sgrna_handle_with_crgpt": {
        "seed_sequence": "sgrna_design_seed_sequence",
        "best_sequence": "candidate_sequence",
        "generated_count": "sgrna_design_generated_count",
        "best_nn_score": "sgrna_design_best_nn_score",
        "best_log_likelihood": "sgrna_design_best_log_likelihood",
        "best_mutation_count": "sgrna_design_best_mutation_count",
        "sampling_mode": "sgrna_design_sampling_mode",
        "model_path": "sgrna_design_model_path",
        "output_fasta_filepath": "sgrna_design_output_filepath",
        "output_ali_filepath": "sgrna_design_output_ali_filepath",
        "summary_json_filepath": "sgrna_design_summary_filepath",
        "best_sequence_filepath": "current_filepath",
    },
    "score_sgrna_handle_with_crgpt": {
        "sequence": "sgrna_design_score_sequence",
        "nn_score": "sgrna_design_score_nn_score",
        "log_likelihood": "sgrna_design_score_log_likelihood",
        "structure_distance": "sgrna_design_score_structure_distance",
        "mfe": "sgrna_design_score_mfe",
        "constraint_mutation_count": "sgrna_design_score_constraint_mutation_count",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # RhoDesign / RiboDiffusion
    # ═══════════════════════════════════════════════════════════════════════
    "design_rna_sequence_with_rhodesign": {
        "input_pdb_filepath": "design_input_pdb_filepath",
        "secondary_structure_filepath": "design_input_secondary_structure_filepath",
        "output_fasta_filepath": "designed_sequence_fasta_filepath",
        "predicted_sequence": "candidate_sequence",
        "recovery_rate": "sequence_recovery_rate",
    },
    "design_rna_inverse_fold_with_ribodiffusion": {
        "input_pdb_filepath": "design_input_pdb_filepath",
        "predicted_sequence": "candidate_sequence",
        "recovery_rate": "sequence_recovery_rate",
        "checkpoint_path": "ribodiffusion_checkpoint_path",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # ViennaRNA misc
    # ═══════════════════════════════════════════════════════════════════════
    "compute_sirna_duplex_binding_vienna": {
        "mfe_kcal_per_mol": "vienna_sirna_duplex_mfe",
    },
    "compute_rna_rna_interaction_vienna": {
        "interaction_energy": "vienna_rnaup_interaction_energy",
        "interaction_structure": "vienna_rnaup_interaction_structure",
    },
    "compute_aso_target_accessibility_vienna": {
        "mean_unpaired_prob_single_nt": "vienna_aso_mean_unpaired",
        "joint_unpaired_prob_stretch_ending_at_region_end": "vienna_aso_joint_unpaired",
    },
    "inverse_fold_rna_secondary_structure_vienna": {
        "best_sequence": "vienna_inverse_best_sequence",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # RNA ligand scoring
    # ═══════════════════════════════════════════════════════════════════════
    "score_rna_ligand_binding_with_gernabind": {
        "rna_sequence": "candidate_sequence",
        "smiles": "ligand_smiles",
        "probability_positive": "gernabind_probability",
        "predicted_label": "gernabind_predicted_label",
        "checkpoint_path": "gernabind_checkpoint_path",
        "preprocessing_pdb_path": "gernabind_preprocessing_pdb_path",
    },
    "score_rna_ligand_binding_with_rnasmol": {
        "rna_sequence": "candidate_sequence",
        "smiles": "ligand_smiles",
        "probability_positive": "rnasmol_probability",
        "predicted_label": "rnasmol_predicted_label",
        "raw_logits": "rnasmol_raw_logits",
        "checkpoint_path": "rnasmol_checkpoint_path",
        "device": "rnasmol_device",
        "dataset": "rnasmol_dataset",
        "perturbation_type": "rnasmol_perturbation_type",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # ODesign
    # ═══════════════════════════════════════════════════════════════════════
    "run_odesign_inference": {
        "input_json_filepath": "odesign_input_json_filepath",
        "infer_model_name": "odesign_model_name",
        "design_modality": "odesign_design_modality",
        "output_dir": "odesign_output_dir",
        "prediction_filepaths": "odesign_prediction_filepaths",
        "run_log_filepath": "odesign_run_log_filepath",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # Extract RNA from CIF (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "extract_rna_sequence_from_cif": {
        "sequence": "extract_rna_from_cif_sequence",
        "chain_id": "extract_rna_from_cif_chain_id",
        "residue_count": "extract_rna_from_cif_residue_count",
        "is_rna": "extract_rna_from_cif_is_rna",
        "warnings": "extract_rna_from_cif_warnings",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # ODesign aptamer input JSON builder (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "build_odesign_aptamer_input_json": {
        "input_json_filepath": "odesign_aptamer_input_json_filepath",
        "design_config": "odesign_aptamer_input_design_config",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # ColabFold protein structure prediction (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "predict_protein_structure_with_colabfold": {
        "pdb_filepath": "protein_structure_pdb_filepath",
        "mean_pae": "protein_structure_mean_pae",
        "mean_plddt": "protein_structure_mean_plddt",
        "ranking_confidence": "protein_structure_ranking_confidence",
        "model_scores": "protein_structure_model_scores",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # Structure alignment (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "score_structure_alignment": {
        "rmsd": "structure_rmsd",
        "tm_score": "structure_tm_score",
        "aligned_residue_count": "structure_aligned_residue_count",
        "superposition_matrix": "structure_superposition_matrix",
        "warning": "structure_alignment_warning",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # Protein binding hotspot identification (v0.1.0 INTERFACE LOCK)
    # ═══════════════════════════════════════════════════════════════════════
    "identify_protein_binding_hotspots": {
        "hotspot_residues": "hotspot_residues",
        "hotspot_patch_size": "hotspot_patch_size",
        "patch_center_coords": "patch_center_coords",
        "exposed_basic_count": "hotspot_exposed_basic_count",
        "protein_structure_path": "hotspot_protein_structure_path",
        "chain_id": "hotspot_chain_id",
        "warning": "hotspot_warning",
    },
}


def _write_structure_filepath(state: dict[str, Any], structure: Any) -> None:
    """Save a dot-bracket structure to workspace and update state."""
    from agent_core.file_manager import save_sequence
    if structure and isinstance(structure, str):
        fp = save_sequence(structure, prefix="structure")
        state["structure_filepath"] = fp
        state["workspace_files"] = state.get("workspace_files", []) + [fp]


# Special fields that need custom handling (e.g. saving structure to workspace)
_SPECIAL_WRITEBACK_HANDLERS: dict[str, Callable[[dict[str, Any], Any], None]] = {
    "_auto_structure_filepath": _write_structure_filepath,
}


def apply_writeback(state: dict[str, Any], tool_name: str, output: dict[str, Any]) -> None:
    """Apply the declarative writeback rules for *tool_name* to *state*.

    Also appends any filepath outputs to ``workspace_files`` when they live
    under ``workspace/``.
    """
    rules = STANDARD_WRITEBACKS.get(tool_name)
    if not rules:
        return

    for out_key, state_key in rules.items():
        if out_key not in output:
            continue
        value = output[out_key]

        # Special handlers (e.g. auto-save structure)
        if state_key in _SPECIAL_WRITEBACK_HANDLERS:
            _SPECIAL_WRITEBACK_HANDLERS[state_key](state, value)
            continue

        state[state_key] = value

        # Auto-track workspace file paths
        if isinstance(value, str) and value.startswith("workspace/"):
            existing = state.get("workspace_files", [])
            if value not in existing:
                state["workspace_files"] = existing + [value]

    # Extract candidate_sequence from Evitar top_results
    if tool_name == "design_sirna_with_evitar" and "top_results" in output:
        top_results = output["top_results"]
        if isinstance(top_results, list) and top_results:
            first_row = top_results[0]
            if isinstance(first_row, dict):
                for key in ("siRNA", "siRNA_sequence", "guide", "guide_sequence", "sequence"):
                    seq = first_row.get(key)
                    if isinstance(seq, str) and seq.strip():
                        state["candidate_sequence"] = seq.strip().upper().replace("T", "U")
                        break
