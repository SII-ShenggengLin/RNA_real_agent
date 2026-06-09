"""On-demand state writeback registry for Layer-1 capabilities.

Each entry maps a *capability name* → a dict of ``{output_field: target_key}``.
When a capability finishes, ``apply_writeback`` copies matching values into
``state["tool_results"][tool_name][target_key]`` so that tools can publish
derived / aliased fields without modifying top-level state fields.
"""

from __future__ import annotations

from typing import Any, Callable

WritebackRule = dict[str, str]

_REGISTERED_WRITEBACKS: dict[str, WritebackRule] = {}
_SPECIAL_WRITEBACK_HANDLERS: dict[str, Callable[[dict[str, Any], Any], None]] = {}


def register_writeback(tool_name: str, rules: WritebackRule) -> None:
    """Register a writeback rule map for *tool_name*.

    *rules* maps ``output_field → target_key`` inside
    ``state["tool_results"][tool_name]``.
    """
    _REGISTERED_WRITEBACKS[tool_name] = rules


def register_special_handler(target_key: str, handler: Callable[[dict[str, Any], Any], None]) -> None:
    """Register a custom side-effect handler for a *target_key*.

    Handlers receive ``(state, value)`` and are invoked when a writeback rule
    points to *target_key*.
    """
    _SPECIAL_WRITEBACK_HANDLERS[target_key] = handler


def apply_writeback(state: dict[str, Any], tool_name: str, output: dict[str, Any]) -> None:
    """Apply registered writeback rules for *tool_name* into ``state["tool_results"]``.

    Also auto-tracks any filepath values starting with ``workspace/`` into
    ``state["workspace_files"]``.
    """
    rules = _REGISTERED_WRITEBACKS.get(tool_name)
    if not rules:
        return

    if "tool_results" not in state:
        state["tool_results"] = {}
    if tool_name not in state["tool_results"]:
        state["tool_results"][tool_name] = {}
    tool_bucket = state["tool_results"][tool_name]

    for out_key, target_key in rules.items():
        if out_key not in output:
            continue
        value = output[out_key]

        # Special handlers (e.g. auto-save structure to workspace)
        if target_key in _SPECIAL_WRITEBACK_HANDLERS:
            _SPECIAL_WRITEBACK_HANDLERS[target_key](state, value)
            continue

        tool_bucket[target_key] = value

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


def _write_structure_filepath(state: dict[str, Any], structure: Any) -> None:
    """Save a dot-bracket structure to workspace and update state."""
    from agent_core.file_manager import save_sequence
    if structure and isinstance(structure, str):
        fp = save_sequence(structure, prefix="structure")
        state["structure_filepath"] = fp
        state["workspace_files"] = state.get("workspace_files", []) + [fp]


# ── Register special handlers ────────────────────────────────────────────────
register_special_handler("_auto_structure_filepath", _write_structure_filepath)

# ── Register backward-compatible writeback rules ─────────────────────────────
# These map tool output fields into state["tool_results"][tool_name] so that
# consumers can find aliased / canonical keys without reaching into top-level
# state fields.

register_writeback("compute_rna_sequence_gc_content", {
    "gc_content": "gc_content",
    "sequence_length": "sequence_length",
    "gc_count": "gc_count",
    "g_count": "g_count",
    "c_count": "c_count",
})
register_writeback("compute_rna_sequence_u_content", {
    "u_fraction": "u_fraction",
    "sequence_length": "sequence_length",
    "u_count": "u_count",
})
register_writeback("compute_cai_for_cds_sequence", {
    "cai_score": "cai_score",
    "species": "species",
    "cds_length_nt": "cds_length_nt",
    "codon_count": "codon_count",
})
register_writeback("shuffle_cds_junction_codons", {
    "original_sequence": "original_sequence",
    "junction_end": "junction_end",
    "shuffled_region_start": "shuffled_region_start",
    "shuffled_region_end": "shuffled_region_end",
    "variants": "variants",
})
register_writeback("compute_dot_bracket_unpaired_fraction", {
    "unpaired_fraction": "unpaired_fraction",
    "structure_length": "structure_length",
    "dot_count": "dot_count",
})
register_writeback("analyze_cds_codon_metrics_with_codonw_slim", {
    "cai_score": "cai_score",
    "enc": "enc",
    "fop": "fop",
    "cbi": "cbi",
    "hydropathy": "hydropathy",
    "aromaticity": "aromaticity",
    "genetic_code": "genetic_code",
    "cds_length_nt": "cds_length_nt",
    "cds_length_codons": "cds_length_codons",
    "normalization_note": "normalization_note",
    "silent_base_usage": "silent_base_usage",
    "bases2": "bases2",
    "codon_usage": "codon_usage",
    "rscu": "rscu",
    "dinuc": "dinuc",
    "aa_usage": "aa_usage",
    "raau": "raau",
    "bases": "bases",
    "metrics_json_filepath": "metrics_json_filepath",
})
register_writeback("predict_rna_secondary_structure", {
    "mfe_kcal_per_mol": "mfe",
    "structure": "_auto_structure_filepath",
})
register_writeback("predict_rna_secondary_structure_with_linearfold", {
    "mfe": "mfe",
    "structure": "_auto_structure_filepath",
})
register_writeback("design_mrna_cds_with_lineardesign", {
    "output_filepath": "output_filepath",
    "generated_sequence": "generated_sequence",
    "mfe": "mfe",
    "cai_score": "cai_score",
    "structure": "_auto_structure_filepath",
    "lambda_value": "lambda_value",
    "codon_usage_path": "codon_usage_path",
    "raw_output": "raw_output",
    "stderr": "stderr",
    "model": "model",
})
register_writeback("design_mrna_cds_batch_with_lineardesign", {
    "output_filepath": "output_filepath",
    "best_generated_sequence": "best_generated_sequence",
    "best_mfe": "best_mfe",
    "best_cai_score": "best_cai_score",
    "best_structure": "_auto_structure_filepath",
    "lambda_value": "lambda_value",
    "codon_usage_path": "codon_usage_path",
    "batch_json_filepath": "batch_json_filepath",
    "count": "count",
    "success_count": "success_count",
    "model": "model",
})
register_writeback("design_mrna_cds_with_gemorna", {
    "output_filepath": "output_filepath",
    "generated_sequence": "generated_sequence",
    "model": "model",
})
register_writeback("design_mrna_cds_with_rnarl", {
    "output_filepath": "output_filepath",
    "generated_sequence": "generated_sequence",
    "model_type": "model_type",
    "checkpoint_path": "checkpoint_path",
    "esm2_model_path": "esm2_model_path",
    "model": "model",
})
register_writeback("design_5utr_with_gemorna", {
    "output_filepath": "output_filepath",
    "generated_sequence": "generated_sequence",
    "model": "model",
})
register_writeback("design_3utr_with_gemorna", {
    "output_filepath": "output_filepath",
    "generated_sequence": "generated_sequence",
    "model": "model",
})
register_writeback("predict_5utr_mrl_with_gemorna", {
    "input_filepath": "input_filepath",
    "input_sequence": "input_sequence",
    "predicted_mrl": "predicted_mrl",
    "model": "model",
})
register_writeback("predict_3utr_stability_with_gemorna", {
    "input_filepath": "input_filepath",
    "input_sequence": "input_sequence",
    "predicted_stability": "predicted_stability",
    "model": "model",
})
register_writeback("predict_rna_tertiary_structure_with_rhofold", {
    "pdb_filepath": "pdb_filepath",
    "ct_filepath": "ct_filepath",
    "results_filepath": "results_filepath",
    "log_filepath": "log_filepath",
    "mean_plddt": "mean_plddt",
})
register_writeback("predict_mrna_stability_with_rnastop", {
    "prediction_filepath": "prediction_filepath",
    "sequence": "sequence",
    "used_sequence": "used_sequence",
    "structure": "structure",
    "loop_type": "loop_type",
    "mean_reactivity": "mean_reactivity",
    "mean_deg_mg_ph10": "mean_deg_mg_ph10",
    "mean_deg_mg_50c": "mean_deg_mg_50c",
    "overall_stability": "overall_stability",
    "mfe": "mfe",
    "checkpoint_path": "checkpoint_path",
    "device": "device",
})
register_writeback("predict_putative_ires_with_iresfinder", {
    "result_tsv_filepath": "result_tsv_filepath",
    "has_putative_ires": "has_putative_ires",
    "max_score": "max_score",
    "best_fragment_id": "best_fragment_id",
    "positive_count": "positive_count",
    "fragment_count": "fragment_count",
    "model": "model",
    "mode": "mode",
    "window_size": "window_size",
    "step_size": "step_size",
    "decision_threshold": "decision_threshold",
    "predictions": "predictions",
})
register_writeback("run_blastn_similarity_search", {
    "hit_count": "hit_count",
    "subject_mode": "subject_mode",
    "hits_preview": "hits_preview",
    "preview_truncated": "preview_truncated",
    "blastn_command": "blastn_command",
    "resolved_query_path": "resolved_query_path",
    "resolved_subject": "resolved_subject",
    "tabular_tsv_filepath": "tabular_tsv_filepath",
})
register_writeback("design_sirna_with_evitar", {
    "output_filepath": "output_filepath",
    "mode": "mode",
    "predict": "predict",
    "result_count": "result_count",
    "command": "command",
    "strains_path": "strains_path",
    "off_target": "off_target",
    "p3utr_path": "p3utr_path",
    "transcriptome_path": "transcriptome_path",
    "weight_path": "weight_path",
    "sumtype": "sumtype",
    "limitnum": "limitnum",
    "repeatnum": "repeatnum",
    "pmcuff": "pmcuff",
    "umcuff": "umcuff",
    "mircuff": "mircuff",
    "maxgc": "maxgc",
    "mingc": "mingc",
    "middlegc": "middlegc",
    "allow_path": "allow_path",
    "ban_path": "ban_path",
})
register_writeback("score_crispr_off_target_with_crisot", {
    "sgrna": "sgrna",
    "target_sequence": "target_sequence",
    "crisot_score": "crisot_score",
})
register_writeback("calculate_crispr_specificity_with_crisot", {
    "input_csv_filepath": "input_csv_filepath",
    "crisot_spec": "crisot_spec",
    "scored_csv_filepath": "scored_csv_filepath",
})
register_writeback("search_crispr_off_targets_with_crisot", {
    "sgrna": "sgrna",
    "target_sequence": "target_sequence",
    "genome_path": "genome_path",
    "crisot_spec": "crisot_spec",
    "off_target_count": "off_target_count",
    "scored_csv_filepath": "scored_csv_filepath",
})
register_writeback("optimize_sgrna_with_crisot", {
    "target_sequence": "target_sequence",
    "genome_path": "genome_path",
    "optimized_available": "optimized_available",
    "best_sgrna": "best_sgrna",
    "best_mutation": "best_mutation",
    "best_delta_spec": "best_delta_spec",
    "best_crisot_score": "best_crisot_score",
    "best_crisot_spec": "best_crisot_spec",
    "optimization_csv_filepath": "optimization_csv_filepath",
    "optimized_sgrna_filepath": "optimized_sgrna_filepath",
})
register_writeback("score_batch_crispr_off_targets_with_crisot", {
    "input_csv_filepath": "input_csv_filepath",
    "scored_csv_filepath": "scored_csv_filepath",
})
register_writeback("rescore_sgrnas_with_crisot", {
    "genome_path": "genome_path",
    "sgrna_count": "sgrna_count",
    "rescore_csv_filepath": "rescore_csv_filepath",
})
register_writeback("predict_crispr_off_target_with_crisot_fp", {
    "input_csv_filepath": "input_csv_filepath",
    "xgb_model": "xgb_model",
    "fp_csv_filepath": "fp_csv_filepath",
})
register_writeback("generate_crispr_fingerprint_with_crisot", {
    "target_sequence": "target_sequence",
    "fp_csv_filepath": "fp_csv_filepath",
})
register_writeback("design_sgrna_handle_with_crgpt", {
    "seed_sequence": "seed_sequence",
    "best_sequence": "best_sequence",
    "generated_count": "generated_count",
    "best_nn_score": "best_nn_score",
    "best_log_likelihood": "best_log_likelihood",
    "best_mutation_count": "best_mutation_count",
    "sampling_mode": "sampling_mode",
    "model_path": "model_path",
    "output_fasta_filepath": "output_fasta_filepath",
    "output_ali_filepath": "output_ali_filepath",
    "summary_json_filepath": "summary_json_filepath",
    "best_sequence_filepath": "best_sequence_filepath",
})
register_writeback("score_sgrna_handle_with_crgpt", {
    "sequence": "sequence",
    "nn_score": "nn_score",
    "log_likelihood": "log_likelihood",
    "structure_distance": "structure_distance",
    "mfe": "mfe",
    "constraint_mutation_count": "constraint_mutation_count",
})
register_writeback("design_rna_sequence_with_rhodesign", {
    "input_pdb_filepath": "input_pdb_filepath",
    "secondary_structure_filepath": "secondary_structure_filepath",
    "output_fasta_filepath": "output_fasta_filepath",
    "predicted_sequence": "predicted_sequence",
    "recovery_rate": "recovery_rate",
})
register_writeback("design_rna_inverse_fold_with_ribodiffusion", {
    "input_pdb_filepath": "input_pdb_filepath",
    "predicted_sequence": "predicted_sequence",
    "recovery_rate": "recovery_rate",
    "checkpoint_path": "checkpoint_path",
})
register_writeback("compute_sirna_duplex_binding_vienna", {
    "mfe_kcal_per_mol": "mfe_kcal_per_mol",
})
register_writeback("compute_rna_rna_interaction_vienna", {
    "interaction_energy": "interaction_energy",
    "interaction_structure": "interaction_structure",
})
register_writeback("compute_aso_target_accessibility_vienna", {
    "mean_unpaired_prob_single_nt": "mean_unpaired_prob_single_nt",
    "joint_unpaired_prob_stretch_ending_at_region_end": "joint_unpaired_prob_stretch_ending_at_region_end",
})
register_writeback("inverse_fold_rna_secondary_structure_vienna", {
    "best_sequence": "best_sequence",
})
register_writeback("score_rna_ligand_binding_with_gernabind", {
    "rna_sequence": "rna_sequence",
    "smiles": "smiles",
    "probability_positive": "probability_positive",
    "predicted_label": "predicted_label",
    "checkpoint_path": "checkpoint_path",
    "preprocessing_pdb_path": "preprocessing_pdb_path",
})
register_writeback("score_rna_ligand_binding_with_rnasmol", {
    "rna_sequence": "rna_sequence",
    "smiles": "smiles",
    "probability_positive": "probability_positive",
    "predicted_label": "predicted_label",
    "raw_logits": "raw_logits",
    "checkpoint_path": "checkpoint_path",
    "device": "device",
    "dataset": "dataset",
    "perturbation_type": "perturbation_type",
})
register_writeback("run_odesign_inference", {
    "input_json_filepath": "input_json_filepath",
    "infer_model_name": "infer_model_name",
    "design_modality": "design_modality",
    "output_dir": "output_dir",
    "prediction_filepaths": "prediction_filepaths",
    "run_log_filepath": "run_log_filepath",
})
register_writeback("extract_rna_sequence_from_cif", {
    "sequence": "sequence",
    "chain_id": "chain_id",
    "residue_count": "residue_count",
    "is_rna": "is_rna",
    "warnings": "warnings",
})
register_writeback("build_odesign_aptamer_input_json", {
    "input_json_filepath": "input_json_filepath",
    "design_config": "design_config",
})
register_writeback("predict_protein_structure_with_proteinx", {
    "pdb_filepath": "pdb_filepath",
    "mean_pae": "mean_pae",
    "mean_plddt": "mean_plddt",
    "ranking_confidence": "ranking_confidence",
    "model_scores": "model_scores",
})
register_writeback("predict_rna_protein_complex_with_proteinx", {
    "pdb_filepath": "pdb_filepath",
    "mean_plddt": "mean_plddt",
    "ipTM": "ipTM",
    "ranking_confidence": "ranking_confidence",
})
register_writeback("score_rna_protein_complex_with_egarps", {
    "complex_id": "complex_id",
    "native_probability": "native_probability",
    "academic": "academic",
    "pdb_path": "pdb_path",
})
register_writeback("analyze_rna_protein_interface", {
    "interface_contacts": "interface_contacts",
    "buried_sasa": "buried_sasa",
    "hydrogen_bonds": "hydrogen_bonds",
    "salt_bridges": "salt_bridges",
    "interface_area": "interface_area",
})
register_writeback("score_structure_alignment", {
    "rmsd": "rmsd",
    "tm_score": "tm_score",
    "aligned_residue_count": "aligned_residue_count",
    "superposition_matrix": "superposition_matrix",
    "warning": "warning",
})
register_writeback("identify_protein_binding_hotspots", {
    "hotspot_residues": "hotspot_residues",
    "hotspot_patch_size": "hotspot_patch_size",
    "patch_center_coords": "patch_center_coords",
    "exposed_basic_count": "exposed_basic_count",
    "protein_structure_path": "protein_structure_path",
    "chain_id": "chain_id",
    "warning": "warning",
})
