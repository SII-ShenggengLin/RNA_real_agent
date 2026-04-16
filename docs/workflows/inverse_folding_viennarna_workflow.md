# 工作流：`inverse_folding_viennarna`

## 基础链（最稳）

- **Step 1 输入校验**：结构文件非空；第一行 dot-bracket；`repeats` 在允许范围
- **Step 2 预处理**：无
- **Step 3 候选生成**：`inverse_fold_rna_secondary_structure_vienna`（此步即生成候选序列）
- **Step 4 评估**：无（如需可回调 `predict_rna_secondary_structure` 验证）
- **Step 5 过滤**：无
- **Step 6 排序**：无（单候选）
- **Step 7 格式化**：输出 `best_sequence` 与 `best_sequence_filepath`

