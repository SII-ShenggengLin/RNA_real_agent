# 任务：`crispr_sgrna_optimization`

## 任务目标

在参考基因组约束下优化 sgRNA（突变）以提升特异性，并输出最优候选与审计文件。

## 输入 / 输出

- **输入**：sgRNA 文件路径 + `genome_path`（FASTA）+ mismatch/设备参数
- **输出**：`best_sgrna`、`best_delta_spec`、`optimization_csv_filepath` 等

## 前置条件

- CRISOT 微服务（端口 8011）+ Cas-OFFinder + reference genome

## 工具

- `optimize_sgrna_with_crisot`

## 标准工具链

见 `docs/workflows/crispr_sgrna_optimization_workflow.md`。

