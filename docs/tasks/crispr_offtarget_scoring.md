# 任务：`crispr_offtarget_scoring`

## 任务目标

对单个 sgRNA 与目标序列对计算 CRISOT score。

## 输入 / 输出

- **输入**：sgRNA 文件路径 + `target_sequence`（23nt）
- **输出**：`crisot_score`（以及规范化后的 sgrna/target）

## 前置条件

- CRISOT 微服务（端口 8011）

## 工具

- `score_crispr_off_target_with_crisot`

## 标准工具链

见 `docs/workflows/crispr_offtarget_scoring_workflow.md`。

