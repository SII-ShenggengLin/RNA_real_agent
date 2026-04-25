from __future__ import annotations

from agent_core.tool_specs import TOOL_SPECS


def test_tool_specs_have_output_models_for_registered_tools():
    must_exist = [
        "predict_rna_secondary_structure",
        "predict_rna_secondary_structure_with_linearfold",
        "evaluate_rna_structure_with_linearfold",
        "predict_rna_secondary_structure_with_linearfold_zuker",
        "run_blastn_similarity_search",
        "compute_sirna_duplex_binding_vienna",
        "compute_rna_rna_interaction_vienna",
        "design_sirna_with_evitar",
    ]
    for name in must_exist:
        spec = TOOL_SPECS[name]
        assert spec.output_model is not None


def test_viennarna_fold_output_model_accepts_minimal_payload():
    spec = TOOL_SPECS["predict_rna_secondary_structure"]
    model = spec.output_model
    assert model is not None
    validated = model.model_validate(
        {
            "input_filepath": "workspace/seq_x.fasta",
            "structure": "....",
            "mfe_kcal_per_mol": -3.4,
            "backend": "RNAfold-cli",
            "model": "ViennaRNA-RNAfold",
            "ensemble_free_energy": -3.8,
            "centroid_structure": "....",
            "centroid_distance": 0.0,
        }
    )
    assert validated.mfe_kcal_per_mol == -3.4
    assert validated.ensemble_free_energy == -3.8


def test_rnaplfold_profile_tool_spec_output_model():
    spec = TOOL_SPECS["predict_rna_local_accessibility_profile_vienna"]
    assert spec.output_model is not None
    spec.output_model.model_validate(
        {
            "input_filepath": "workspace/seq_x.fasta",
            "sequence_length": 12,
            "profile_positions_count": 12,
            "mean_unpaired_prob_1nt": 0.4,
            "min_unpaired_prob_1nt": 0.1,
            "max_unpaired_prob_1nt": 0.9,
            "plfold_winsize": 70,
            "plfold_span": 70,
            "plfold_unpaired_ulength_effective": 25,
            "lunp_profile_tsv_filepath": "workspace/vienna_rnaplfold_profile_ab.tsv",
            "backend": "RNAplfold-cli",
            "model": "ViennaRNA-RNAplfold",
        }
    )


def test_rnaup_tool_spec_output_model():
    spec = TOOL_SPECS["compute_rna_rna_interaction_vienna"]
    assert spec.output_model is not None
    spec.output_model.model_validate(
        {
            "input_filepath1": "workspace/seq1.fasta",
            "input_filepath2": "workspace/seq2.fasta",
            "sequence1": "AUGC",
            "sequence2": "CGUA",
            "interaction_energy": -12.3,
            "interaction_structure": "((((&))))",
            "raw_stdout": "# RNAup output\n",
            "backend": "RNAup-cli",
            "model": "ViennaRNA-RNAup",
        }
    )
