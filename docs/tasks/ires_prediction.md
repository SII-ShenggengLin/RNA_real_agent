# 任务：`ires_prediction`

## 任务目标

对输入 RNA 预测 putative IRES 片段与打分摘要。

## 输入 / 输出

- **输入**：RNA 序列文件路径
- **输出**：`result_tsv_filepath`、`max_score`、`positive_count` 等

## 前置条件

- IRESfinder 微服务（端口 8013）及其模型/数据文件

## 工具

- `predict_putative_ires_with_iresfinder`

## 标准工具链

见 `docs/workflows/ires_prediction_workflow.md`。

