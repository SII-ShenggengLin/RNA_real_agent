# 工作流：`protein_to_cds_design`

## 基础链（最稳）

- **Step 1 输入校验**：蛋白序列文件可读；仅包含氨基酸字母（服务端可能进一步校验）
- **Step 2 预处理**：无
- **Step 3 候选生成**：在以下工具中选 1 个（由调用方/路由决定）
  - `design_mrna_cds_with_lineardesign`
  - `design_mrna_cds_with_rnarl`
  - `design_mrna_cds_with_gemorna`
- **Step 4 评估**：可选 `analyze_cds_codon_metrics_with_codonw_slim` + 折叠工具（若任务需要）
- **Step 5 过滤**：无（可按 CAI/ENC/结构阈值过滤）
- **Step 6 排序**：可按多指标（CAI↑，ENC↓，MFE↓）做 rule-based rerank
- **Step 7 格式化**：输出 `generated_sequence` 与 `output_filepath`

