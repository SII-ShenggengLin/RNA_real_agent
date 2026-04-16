# 工作流：`crispr_specificity_csv`

## 基础链（最稳）

- **Step 1 输入校验**：CSV 路径可读；列名满足 `on_item/off_item`
- **Step 2 预处理**：无
- **Step 3 候选生成**：无
- **Step 4 评估**：`calculate_crispr_specificity_with_crisot`
- **Step 5 过滤**：无
- **Step 6 排序**：按 `crisot_spec`（方向以任务定义为准）
- **Step 7 格式化**：输出 scored CSV 路径

