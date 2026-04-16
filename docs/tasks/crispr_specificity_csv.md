# 任务：`crispr_specificity_csv`

## 任务目标

对 CSV 中的 On/Off 序列对计算 CRISOT specificity，并输出带分数的 CSV。

## 输入 / 输出

- **输入**：`csv_filepath`（含 On/Off 列名）
- **输出**：`crisot_spec` 与 `scored_csv_filepath`

## 前置条件

- CRISOT 微服务（端口 8011）

## 工具

- `calculate_crispr_specificity_with_crisot`

## 标准工具链

见 `docs/workflows/crispr_specificity_csv_workflow.md`。

