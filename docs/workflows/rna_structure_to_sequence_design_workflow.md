# 工作流：`rna_structure_to_sequence_design`

## 基础链（最稳）

- **Step 1 输入校验**：`pdb_filepath` 可读且为合法 PDB；可选二级结构文件可读
- **Step 2 预处理**：无
- **Step 3 候选生成**：`design_rna_sequence_with_rhodesign`
- **Step 4 评估**：可选 `predict_rna_secondary_structure` / `analyze_cds_codon_metrics_with_codonw_slim`（视任务而定）
- **Step 5 过滤**：可按 recovery/结构阈值
- **Step 6 排序**：若生成多候选（未来扩展），按多指标排序
- **Step 7 格式化**：输出 designed sequence 与 fasta 路径

