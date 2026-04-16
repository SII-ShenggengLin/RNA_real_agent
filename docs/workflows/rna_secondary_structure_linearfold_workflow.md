# 工作流：`rna_secondary_structure_linearfold`

## 基础链（最稳）

- **Step 1 输入校验**：`filepath` 可读；`dangles` 必须为 0 或 2（wrapper 校验）
- **Step 2 预处理**：无
- **Step 3 候选生成**：无
- **Step 4 评估**：`predict_rna_secondary_structure_with_linearfold`（`structure` + `mfe`）
- **Step 5 过滤**：无
- **Step 6 排序**：按 `mfe` 升序（更负更优）或按业务指标
- **Step 7 格式化**：写回 state 并输出

