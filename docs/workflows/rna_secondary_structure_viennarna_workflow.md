# 工作流：`rna_secondary_structure_viennarna`

## 基础链（最稳）

- **Step 1 输入校验**：`filepath` 可读；序列为核酸字符（服务端会校验/归一化）
- **Step 2 预处理**：无
- **Step 3 候选生成**：无（输入即候选）
- **Step 4 评估**：`predict_rna_secondary_structure`（输出 `structure` + `mfe_kcal_per_mol`）
- **Step 5 过滤**：无
- **Step 6 排序**：如需可按 `mfe_kcal_per_mol` 升序
- **Step 7 格式化**：写回 `AgentState.mfe` 等字段并生成最终报告

