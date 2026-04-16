# 任务：`mrna_stability_prediction`

## 任务目标

对 mRNA 序列输出 RNASTOP 的稳定性/降解相关摘要预测。

## 输入 / 输出

- **输入**：mRNA 序列文件路径
- **输出**：`prediction_filepath` 与摘要指标（如 `mean_deg_mg_ph10` 等）

## 前置条件

- RNASTOP 微服务（端口 8009），通常依赖 GPU/权重

## 工具

- `predict_mrna_stability_with_rnastop`

## 标准工具链

见 `docs/workflows/mrna_stability_prediction_workflow.md`。

