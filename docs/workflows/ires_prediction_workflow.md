# 工作流：`ires_prediction`

## 基础链（最稳）

- **Step 1 输入校验**：RNA 文件可读
- **Step 2 预处理**：无
- **Step 3 候选生成**：无
- **Step 4 评估**：`predict_putative_ires_with_iresfinder`
- **Step 5 过滤**：可按 `max_score` 阈值
- **Step 6 排序**：按 `max_score` 降序
- **Step 7 格式化**：输出 tsv 路径与摘要字段

