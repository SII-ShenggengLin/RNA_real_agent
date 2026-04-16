# 工作流：`crispr_offtarget_scoring`

## 基础链（最稳）

- **Step 1 输入校验**：sgRNA 文件可读；`target_sequence` 归一化后长度必须为 23（wrapper 强制）
- **Step 2 预处理**：`_normalize_crisot_sequence`（wrapper 内部）
- **Step 3 候选生成**：无
- **Step 4 评估**：`score_crispr_off_target_with_crisot`
- **Step 5 过滤**：无
- **Step 6 排序**：按 `crisot_score`（方向以任务定义为准）
- **Step 7 格式化**：输出 score 与规范化序列

