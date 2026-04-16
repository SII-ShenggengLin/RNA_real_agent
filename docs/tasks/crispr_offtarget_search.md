# 任务：`crispr_offtarget_search`

## 任务目标

在参考基因组上搜索 sgRNA 的潜在 off-target，并给出特异性摘要与输出文件。

## 输入 / 输出

- **输入**：sgRNA 文件路径 + `target_sequence`（23nt）+ `genome_path`（FASTA）
- **输出**：`off_target_count`、`crisot_spec`、`scored_csv_filepath`

## 前置条件

- CRISOT 微服务（端口 8011）
- 服务端 Cas-OFFinder 可用 + 参考基因组可访问

## 工具

- `search_crispr_off_targets_with_crisot`

## 标准工具链

见 `docs/workflows/crispr_offtarget_search_workflow.md`。

