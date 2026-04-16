# 工作流：`mrna_stability_prediction`

## 基础链（最稳）

- **Step 1 输入校验**：mRNA 文件可读
- **Step 2 预处理**：无（RNASTOP 服务端可能补齐特征）
- **Step 3 候选生成**：无
- **Step 4 评估**：`predict_mrna_stability_with_rnastop`
- **Step 5 过滤**：无
- **Step 6 排序**：若比较多个候选，可按降解指标方向做排序（以任务定义为准）
- **Step 7 格式化**：输出预测文件路径与摘要指标

