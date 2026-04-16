# 系统能力矩阵（任务 → 工具链 → 工具接口）

> 以代码为准：
> - 工具规格来源：`rna_agent_system/agent_core/tool_specs.py:TOOL_SPECS`
> - 任务目录：`docs/tasks/`
> - 工作流目录：`docs/workflows/`

---

## 表 1：工具总表

| 工具名 | 来源 | 类型 | 支持任务 | 输入核心字段 | 输出核心字段 | 是否严格 schema | 当前状态 |
|---|---|---|---|---|---|---|---|
| `compute_sirna_duplex_binding_vienna` | ViennaRNA | HTTP | `sirna_duplex_energy` | `filepath` | `mfe_kcal_per_mol`, `structure` | 是（input+output） | available |
| `design_sirna_with_evitar` | Evitar | HTTP | `sirna_design_evitar` | `filepath`, `mode`, `predict` | `output_filepath`, `top_results` | 是（input+output） | partial（Linux） |
| `predict_rna_secondary_structure` | ViennaRNA | HTTP | `rna_secondary_structure_viennarna` | `filepath` | `mfe_kcal_per_mol`, `structure` | 是（input+output） | available |
| `compute_aso_target_accessibility_vienna` | ViennaRNA | HTTP | `aso_accessibility_viennarna` | `filepath`, `region_start/end` | `mean_unpaired_prob_single_nt` | 是（input+output） | available |
| `inverse_fold_rna_secondary_structure_vienna` | ViennaRNA | HTTP | `inverse_folding_viennarna` | `filepath`, `repeats` | `best_sequence`, `best_sequence_filepath` | 是（input+output） | available |
| `predict_rna_secondary_structure_with_linearfold` | LinearFold | HTTP | `rna_secondary_structure_linearfold` | `filepath`, `beam_size` | `mfe`, `structure` | 是（input+output） | available |
| `design_mrna_cds_with_lineardesign` | LinearDesign | HTTP | `protein_to_cds_design` | `filepath` | `generated_sequence`, `output_filepath` | 是（input+output） | partial |
| `design_mrna_cds_with_rnarl` | RNARL | HTTP | `protein_to_cds_design` | `filepath`, `model_type` | `generated_sequence`, `output_filepath` | 是（input+output） | partial（GPU/权重） |
| `design_mrna_cds_with_gemorna` | GEMORNA | HTTP | `protein_to_cds_design` | `filepath` | `generated_sequence`, `output_filepath` | 是（input+output） | partial（GPU/权重） |
| `analyze_cds_codon_metrics_with_codonw_slim` | codonw-slim | HTTP | `cds_codon_metrics` | `filepath` | `cai_score`, `metrics_json_filepath` | 是（input+output） | partial |
| `run_blastn_similarity_search` | BLAST+ | HTTP | `blastn_similarity_search` | `filepath`, subject（二选一） | `hit_count`, `tabular_tsv_filepath` | 是（input+output） | partial |
| `predict_putative_ires_with_iresfinder` | IRESfinder | HTTP | `ires_prediction` | `filepath` | `result_tsv_filepath`, `max_score` | 是（input+output） | partial |
| `predict_mrna_stability_with_rnastop` | RNASTOP | HTTP | `mrna_stability_prediction` | `filepath` | `prediction_filepath`, 降解指标 | 是（input+output） | partial（GPU/权重） |
| `predict_rna_tertiary_structure_with_rhofold` | RhoFold | HTTP | `rna_tertiary_structure_prediction` | `filepath` | `pdb_filepath`, `mean_plddt` | 是（input+output） | partial（GPU/权重） |
| `design_rna_sequence_with_rhodesign` | RhoDesign | HTTP | `rna_structure_to_sequence_design` | `pdb_filepath` | `output_fasta_filepath`, `designed_sequence` | 是（input+output） | partial（GPU/权重） |
| `score_rna_ligand_binding_with_rnasmol` | RNAsmol | HTTP | `rna_ligand_scoring` | `filepath`, `smiles` | `probability`, `predicted_label` | 是（input+output） | partial（GPU/权重） |
| `score_rna_ligand_binding_with_gernabind` | GerNA-Bind | HTTP | `rna_ligand_scoring` | `filepath`, `smiles` | `probability`, `predicted_label` | 是（input+output） | partial（GPU/权重） |
| `score_crispr_off_target_with_crisot` | CRISOT | HTTP | `crispr_offtarget_scoring` | `filepath`, `target_sequence` | `crisot_score` | 是（input+output） | partial |
| `calculate_crispr_specificity_with_crisot` | CRISOT | HTTP | `crispr_specificity_csv` | `csv_filepath` | `crisot_spec`, `scored_csv_filepath` | 是（input+output） | partial |
| `search_crispr_off_targets_with_crisot` | CRISOT | HTTP | `crispr_offtarget_search` | `filepath`, `target_sequence`, `genome_path` | `off_target_count`, `scored_csv_filepath` | 是（input+output） | partial |
| `optimize_sgrna_with_crisot` | CRISOT | HTTP | `crispr_sgrna_optimization` | `filepath`, `genome_path` | `best_sgrna`, `best_delta_spec` | 是（input+output） | partial |
| `design_sgrna_handle_with_crgpt` | sgrna_design | HTTP | `sgrna_handle_design` | `filepath`, `n_samples` | `best_sequence`, `output_fasta_filepath` | 是（input+output） | partial |
| `run_odesign_inference` | ODesign | HTTP | `odesign_inference` | `input_json_filepath` | `prediction_filepaths`, `run_log_filepath` | 是（input+output） | partial（GPU/权重） |
| `mock_codon_optimization` | 本仓库占位实现 | Python（本地） | （不计入真实任务） | `filepath` | `cai_score`（固定） | 否（mock） | mock |

---

## 表 2：任务总表

| 任务名 | 当前是否支持 | 入口 | 所需工具链 | 是否完全可用 | 限制 |
|---|---|---|---|---|---|
| `sirna_duplex_energy` | 是 | UI/workflow | `sirna_duplex_energy_workflow` | 是 | 需两条链 |
| `sirna_design_evitar` | 部分 | workflow | `sirna_design_evitar_workflow` | 否 | Linux only |
| `rna_secondary_structure_viennarna` | 是 | UI/workflow | `rna_secondary_structure_viennarna_workflow` | 是 | 依赖 8003 |
| `rna_secondary_structure_linearfold` | 是 | UI/workflow | `rna_secondary_structure_linearfold_workflow` | 是 | 依赖 8015 |
| `aso_accessibility_viennarna` | 是 | workflow | `aso_accessibility_viennarna_workflow` | 是 | region 必须合法 |
| `inverse_folding_viennarna` | 是 | workflow | `inverse_folding_viennarna_workflow` | 是 | 启发式 |
| `cds_codon_metrics` | 部分 | workflow | `cds_codon_metrics_workflow` | 否 | 需 8018 环境 |
| `protein_to_cds_design` | 部分 | workflow | `protein_to_cds_design_workflow` | 否 | 多工具依赖 Linux/GPU/权重 |
| `mrna_stability_prediction` | 部分 | workflow | `mrna_stability_prediction_workflow` | 否 | GPU/权重 |
| `ires_prediction` | 部分 | workflow | `ires_prediction_workflow` | 否 | 需模型/数据 |
| `blastn_similarity_search` | 部分 | workflow | `blastn_similarity_search_workflow` | 否 | 需 BLAST+ 与 subject 数据 |
| `rna_tertiary_structure_prediction` | 部分 | workflow | `rna_tertiary_structure_prediction_workflow` | 否 | GPU/权重 |
| `rna_structure_to_sequence_design` | 部分 | workflow | `rna_structure_to_sequence_design_workflow` | 否 | GPU/权重 + PDB |
| `rna_ligand_scoring` | 部分 | workflow | `rna_ligand_scoring_workflow` | 否 | GPU/权重 |
| `odesign_inference` | 部分 | workflow | `odesign_inference_workflow` | 否 | GPU/权重/数据 |
| `crispr_offtarget_scoring` | 部分 | workflow | `crispr_offtarget_scoring_workflow` | 否 | 需 8011 |
| `crispr_specificity_csv` | 部分 | workflow | `crispr_specificity_csv_workflow` | 否 | 需 8011 |
| `crispr_offtarget_search` | 部分 | workflow | `crispr_offtarget_search_workflow` | 否 | genome + Cas-OFFinder |
| `crispr_sgrna_optimization` | 部分 | workflow | `crispr_sgrna_optimization_workflow` | 否 | 可能很慢 |
| `sgrna_handle_design` | 部分 | workflow | `sgrna_handle_design_workflow` | 否 | 模型/torch |

---

## 表 3：任务-工具链映射表（Step 1~7）

| 任务名 | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Step 6 | Step 7 |
|---|---|---|---|---|---|---|---|
| `sirna_duplex_energy` | 输入校验 | 无 | 无 | `compute_sirna_duplex_binding_vienna` | 无 | 按 MFE | 格式化 |
| `sirna_design_evitar` | 输入校验 | 无 | `design_sirna_with_evitar` | 无 | 无 | 无 | 写回/格式化 |
| `rna_secondary_structure_viennarna` | 输入校验 | 无 | 无 | `predict_rna_secondary_structure`（失败则 fallback LinearFold） | 无 | 可选按 MFE | 格式化 |
| `rna_secondary_structure_linearfold` | 输入校验 | 无 | 无 | `predict_rna_secondary_structure_with_linearfold` | 无 | 可选按 MFE | 格式化 |
| `aso_accessibility_viennarna` | 输入校验 | 无 | 无 | `compute_aso_target_accessibility_vienna` | 无 | 可选按可及性 | 格式化 |
| `inverse_folding_viennarna` | 输入校验 | 无 | `inverse_fold_rna_secondary_structure_vienna` | 无 | 无 | 无 | 格式化 |
| `cds_codon_metrics` | 输入校验 | 无 | 无 | `analyze_cds_codon_metrics_with_codonw_slim` | 无 | 可选按 CAI | 格式化 |
| `protein_to_cds_design` | 输入校验 | 无 | `design_mrna_cds_*` | 可选评估 | 可选过滤 | 可选 rerank | 格式化 |
| `mrna_stability_prediction` | 输入校验 | 无 | 无 | `predict_mrna_stability_with_rnastop` | 无 | 可选排序 | 格式化 |
| `ires_prediction` | 输入校验 | 无 | 无 | `predict_putative_ires_with_iresfinder` | 可选阈值 | 按 max_score | 格式化 |
| `blastn_similarity_search` | 输入校验 | 无 | 无 | `run_blastn_similarity_search` | 可选过滤 | 无 | 格式化 |
| `rna_tertiary_structure_prediction` | 输入校验 | 无 | 无 | `predict_rna_tertiary_structure_with_rhofold` | 可选阈值 | 无 | 格式化 |
| `rna_structure_to_sequence_design` | 输入校验 | 无 | `design_rna_sequence_with_rhodesign` | 可选评估 | 可选过滤 | 可选排序 | 格式化 |
| `rna_ligand_scoring` | 输入校验 | 无 | 无 | RNAsmol/GerNA-Bind | 可选阈值 | 按概率 | 格式化 |
| `odesign_inference` | 输入校验 | 无 | `run_odesign_inference` | 无 | 无 | 无 | 格式化 |
| `crispr_offtarget_scoring` | 输入校验 | 归一化 | 无 | `score_crispr_off_target_with_crisot` | 无 | 按 score | 格式化 |
| `crispr_specificity_csv` | 输入校验 | 无 | 无 | `calculate_crispr_specificity_with_crisot` | 无 | 按 spec | 格式化 |
| `crispr_offtarget_search` | 输入校验 | 无 | 无 | `search_crispr_off_targets_with_crisot` | 按计数 | 按 spec | 格式化 |
| `crispr_sgrna_optimization` | 输入校验 | 无 | `optimize_sgrna_with_crisot` | 内置 | 按 available | 无 | 格式化 |
| `sgrna_handle_design` | 输入校验 | 归一化 | `design_sgrna_handle_with_crgpt` | 内置 | 无 | 按 NN score | 格式化 |

---

## 表 4：已移除能力表

| 能力名 | 移除原因 | 原位置 | 当前替代方案 |
|---|---|---|---|
| siRNA efficiency（mock） | 返回随机值，禁止假装支持 | `microservices/sirna_attsioff` + `predict_sirna_efficiency` | 无（当前不支持生产实现） |
| siRNA off-target count（mock） | 返回随机值，禁止假装支持 | `microservices/off_target_blast` + `check_off_target` | 无（可用通用 `run_blastn_similarity_search` 作为基础组件，但不是完整 pipeline） |

---

## 表 5：增强设计表

| 增强名 | 作用任务 | 是否已实现 | 收益来源 | 风险 | 具体执行顺序 |
|---|---|---:|---|---|---|
| 统一任务路由与工具选择约束（ToolSpec.task_tags） | 全部 | 否 | 降低误路由/越权调用 | 维护成本 | 先落任务枚举→Router 输出 task_id→workflow 固化 |
| 严格输入/参数校验 Validator | 多任务 | 否 | 更早失败、更可诊断 | 规则过严 | 先覆盖 duplex/BLAST/CRISOT/ASO |
| 输出标准化（Vienna fold dict） | fold | 是 | 去字符串解析/提升审计性 | 兼容性改动 | wrapper 输出→state 写回→测试 |
| ToolSpec 输出契约校验 | 全部 | 是 | 关键字段缺失即时失败 | 需要维护 schema | 先覆盖关键工具→逐步扩展 |
| Vienna 失败 fallback Linearfold | fold | 是 | 提升完成率（失败时） | 额外调用 | 仅在异常时触发 |

