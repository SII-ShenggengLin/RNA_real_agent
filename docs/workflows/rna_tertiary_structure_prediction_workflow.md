# 工作流：`rna_tertiary_structure_prediction`

## 基础链（最稳）

- **Step 1 输入校验**：RNA 文件可读；长度限制由服务端决定
- **Step 2 预处理**：无
- **Step 3 候选生成**：无
- **Step 4 评估**：`predict_rna_tertiary_structure_with_rhofold`
- **Step 5 过滤**：可按 `mean_plddt` 阈值（若输出存在）
- **Step 6 排序**：无（单序列）
- **Step 7 格式化**：输出 PDB/日志路径与 `mean_plddt`

