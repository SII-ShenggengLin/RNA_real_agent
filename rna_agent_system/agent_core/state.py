"""AgentState definition for the RNA Design multi-agent workflow."""

from typing import Any, Literal, Optional, TypedDict

from langchain_core.messages import HumanMessage


class AgentState(TypedDict, total=False):
    """Shared state across all LangGraph nodes."""

    messages: list[Any]
    current_task: str
    workspace_files: list[str]
    input_sequence: str
    current_filepath: str
    candidate_sequence: str
    # ═══════════════════════════════════════════════════════════════════════════
    # CRISOT INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单见 agent_core/tool_specs.py 中 CRISOT ToolSpec 注册区域的
    # INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
    # ═══════════════════════════════════════════════════════════════════════════
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
    crisot_scores_csv_filepath: str
    crisot_rescore_csv_filepath: str
    crisot_rescore_sgrna_count: int
    crisot_fp_csv_filepath: str
    crisot_fp_xgb_model: str
    crisot_genfp_csv_filepath: str
    # ═══════════════════════════════════════════════════════════════════════════
    # sgrna_design INTERFACE LOCK (v0.3.0) —— 禁止单方面变更
    # 关联文件清单见 agent_core/tool_specs.py 中 design_sgrna_handle_with_crgpt
    # 的 INTERFACE LOCK 注释。任何修改必须全部同步。
    # ═══════════════════════════════════════════════════════════════════════════
    sgrna_design_seed_sequence: str
    sgrna_design_generated_count: int
    sgrna_design_best_nn_score: float
    sgrna_design_best_log_likelihood: Optional[float] = None
    sgrna_design_best_mutation_count: int
    sgrna_design_sampling_mode: str
    sgrna_design_output_filepath: str
    sgrna_design_output_ali_filepath: str
    sgrna_design_summary_filepath: str
    sgrna_design_model_path: str
    sgrna_design_score_sequence: str
    sgrna_design_score_nn_score: float
    sgrna_design_score_log_likelihood: float
    sgrna_design_score_structure_distance: Optional[int] = None
    sgrna_design_score_mfe: Optional[float] = None
    sgrna_design_score_constraint_mutation_count: int
    cai_score: float
    # ═══════════════════════════════════════════════════════════════════════════
    # codonw-slim INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单见 agent_core/tool_specs.py 中 CodonwSlimOutput 的
    # INTERFACE LOCK 注释。任何字段增删必须同步到 tool_execution_node
    # 的 codonw 结果回写分支及 critic_node 的 summary 字符串。
    # ═══════════════════════════════════════════════════════════════════════════
    codonw_metrics_filepath: str
    codonw_enc: float
    codonw_fop: float
    codonw_cbi: float
    codonw_hydropathy: float = 0.0
    codonw_aromaticity: float = 0.0
    codonw_genetic_code: int = 0
    codonw_cds_length_nt: int = 0
    codonw_cds_length_codons: int = 0
    codonw_normalization_note: str = ""
    codonw_silent_base_usage: dict[str, Any] = {}
    codonw_bases2: dict[str, Any] = {}
    codonw_codon_usage: Optional[dict[str, Any]] = None
    codonw_rscu: Optional[dict[str, Any]] = None
    codonw_dinuc: Optional[dict[str, Any]] = None
    codonw_aa_usage: Optional[dict[str, Any]] = None
    codonw_raau: Optional[dict[str, Any]] = None
    codonw_bases: Optional[dict[str, Any]] = None
    # ═══════════════════════════════════════════════════════════════════════════
    # LinearDesign INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/lineardesign_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py
    #   - agent_core/state.py  ← 本文件
    #   - agent_core/nodes.py
    #   - docs/tools/design_mrna_cds_with_lineardesign.md
    #   - docs/change_logs/lineardesign_interface_v0.2.0.md
    #   - workflow_api/mrna_handler.py
    #   - workflow_api/mrna_schemas.py
    # 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
    # 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
    # 本次修改的基准日期：2026-04-24。
    # ═══════════════════════════════════════════════════════════════════════════
    lineardesign_output_filepath: str
    lineardesign_generated_sequence: str
    lineardesign_structure: str
    lineardesign_mfe: float
    lineardesign_cai_score: float
    lineardesign_lambda_value: float
    lineardesign_codon_usage_path: str
    lineardesign_raw_output: str
    lineardesign_stderr: str
    lineardesign_model: str
    lineardesign_batch_json_filepath: str
    lineardesign_batch_count: int
    lineardesign_batch_success_count: int
    # ═══════════════════════════════════════════════════════════════════════════
    mfe: float
    structure_filepath: str
    design_input_pdb_filepath: str
    design_input_secondary_structure_filepath: str
    designed_sequence_fasta_filepath: str
    sequence_recovery_rate: float
    # ═══════════════════════════════════════════════════════════════════════════
    # RiboDiffusion INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/ribodiffusion_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py
    #   - agent_core/state.py  ← 本文件
    #   - agent_core/nodes.py
    #   - docs/RNA_AGENT_SYSTEM_GUIDE.md
    # 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
    # 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
    # ═══════════════════════════════════════════════════════════════════════════
    ribodiffusion_checkpoint_path: str
    tertiary_structure_filepath: str
    tertiary_structure_ct_filepath: str
    tertiary_results_filepath: str
    tertiary_log_filepath: str
    mean_plddt: float
    ligand_smiles: str
    # INTERFACE LOCK (v0.1.0) — GerNA-Bind state fields
    # Any field addition/removal must be synchronized with:
    # - microservices/gernabind_service/main.py :: ScoreResponse / BindingSiteResponse
    # - agent_core/tools.py :: score_rna_ligand_binding_with_gernabind return dict
    # - agent_core/tool_specs.py :: GerNABindScoreOutput
    # - docs/tools/score_rna_ligand_binding_with_gernabind.md
    gernabind_probability: float
    gernabind_predicted_label: int
    gernabind_checkpoint_path: str
    gernabind_preprocessing_pdb_path: str
    # ═══════════════════════════════════════════════════════════════════════════
    # RNAsmOL 接口冻结声明 (v0.2.0) —— 禁止单方面变更
    # ═══════════════════════════════════════════════════════════════════════════
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/rnasmol_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py
    #   - agent_core/state.py  ← 本文件
    #   - agent_core/nodes.py
    #   - docs/tools/score_rna_ligand_binding_with_rnasmol.md
    # 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
    # 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
    # ═══════════════════════════════════════════════════════════════════════════
    # INTERFACE LOCK (v0.2.0) — RNAsmol state fields
    # Any field addition/removal must be synchronized with:
    # - microservices/rnasmol_service/main.py :: ScoreResponse
    # - agent_core/tools.py :: score_rna_ligand_binding_with_rnasmol return dict
    # - agent_core/tool_specs.py :: RNAsmolScoreOutput
    # - docs/tools/score_rna_ligand_binding_with_rnasmol.md
    rnasmol_probability: float
    rnasmol_predicted_label: int
    rnasmol_raw_logits: list[float]
    rnasmol_checkpoint_path: str
    rnasmol_device: str
    rnasmol_dataset: str
    rnasmol_perturbation_type: str
    # INTERFACE LOCK (v0.1.0) — RNASTOP state fields
    # Any field addition/removal must be synchronized with:
    # - microservices/rnastop_service/main.py :: StabilityPredictionResponse
    # - agent_core/tools.py :: predict_mrna_stability_with_rnastop return dict
    # - agent_core/tool_specs.py :: RNASTOPPredictionOutput
    # - agent_core/nodes.py :: tool_execution_node RNASTOP branch
    # - docs/tools/predict_mrna_stability_with_rnastop.md
    rnastop_prediction_filepath: str
    rnastop_sequence: str
    rnastop_used_sequence: str
    rnastop_structure: str
    rnastop_loop_type: str
    rnastop_mean_reactivity: float
    rnastop_mean_deg_mg_ph10: float
    rnastop_mean_deg_mg_50c: float
    rnastop_overall_stability: float
    rnastop_mfe: float
    rnastop_checkpoint_path: str
    rnastop_device: str
    # INTERFACE LOCK (v0.2.0) — IRESfinder state fields
    # The canonical contract is the state after the 2026-04-23 refactor.
    # Any field addition/removal must be synchronized with:
    # - microservices/iresfinder_service/main.py :: IRESfinderPredictResponse
    # - agent_core/tools.py :: predict_putative_ires_with_iresfinder return dict
    # - agent_core/tool_specs.py :: IRESfinderPredictionOutput
    # - agent_core/nodes.py :: tool_execution_node IRESfinder branch
    # - docs/tools/predict_putative_ires_with_iresfinder.md
    iresfinder_result_tsv_filepath: str
    iresfinder_has_putative_ires: bool
    iresfinder_max_score: float
    iresfinder_best_fragment_id: str
    iresfinder_positive_count: int
    iresfinder_fragment_count: int
    iresfinder_model: str
    iresfinder_mode: int
    iresfinder_window_size: int
    iresfinder_step_size: int
    iresfinder_decision_threshold: float
    iresfinder_predictions: list[dict[str, Any]]
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
    evitar_strains_path: str
    evitar_off_target: bool
    evitar_p3utr_path: str
    evitar_transcriptome_path: str
    evitar_weight_path: str
    evitar_sumtype: str
    evitar_limitnum: int
    evitar_repeatnum: int
    evitar_pmcuff: int
    evitar_umcuff: float
    evitar_mircuff: float
    evitar_maxgc: float
    evitar_mingc: float
    evitar_middlegc: float
    evitar_allow_path: str
    evitar_ban_path: str
    # ViennaRNA INTERFACE LOCK (v0.4.0) —— 禁止单方面变更
    # 关联文件清单见 microservices/viennarna_fold/main.py 顶部的 INTERFACE LOCK。
    # 任何字段增删必须同步更新全部关联文件并重新跑通端到端测试。
    vienna_sirna_duplex_mfe: float
    vienna_rnaup_interaction_energy: Optional[float] = None
    vienna_rnaup_interaction_structure: Optional[str] = None
    vienna_aso_mean_unpaired: float
    vienna_aso_joint_unpaired: float
    vienna_inverse_best_sequence: str
    # ═══════════════════════════════════════════════════════════════════════════
    # BLAST+ INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单见 agent_core/tool_specs.py 中 run_blastn_similarity_search
    # 的 INTERFACE LOCK 注释。任何字段增删必须同步更新全部关联文件。
    # ═══════════════════════════════════════════════════════════════════════════
    blast_hit_count: int
    blast_tabular_tsv_filepath: str
    blast_subject_mode: str
    blast_hits_preview: str
    blast_preview_truncated: bool
    blast_blastn_command: str
    blast_resolved_query_path: str
    blast_resolved_subject: str
    # ═══════════════════════════════════════════════════════════════════════════
    # RNA sequence metrics (GC content) INTERFACE LOCK (v0.1.0) —— 禁止单方面变更
    # 关联文件清单见 agent_core/tool_specs.py 中 compute_rna_sequence_gc_content
    # 的 INTERFACE LOCK 注释。任何字段增删必须同步更新全部关联文件。
    # ═══════════════════════════════════════════════════════════════════════════
    sequence_gc_content: float
    sequence_gc_length: int = 0
    sequence_gc_count: int = 0
    sequence_g_count: int = 0
    sequence_c_count: int = 0
    # ── dot-bracket unpaired fraction ──
    dot_bracket_unpaired_fraction: float
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
        current_task="mrna_design",
        workspace_files=[],
        input_sequence=user_text.strip(),
        active_specialist="",
        retry_count=0,
        max_retries=3,
    )
