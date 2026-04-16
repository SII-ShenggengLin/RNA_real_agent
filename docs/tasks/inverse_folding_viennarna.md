# 任务：`inverse_folding_viennarna`

## 任务目标

给定 dot-bracket 二级结构，生成一个可折叠到该结构的候选 RNA 序列（RNAinverse）。

## 输入 / 输出

- **输入**：结构文件（第一行结构；可选第二行起始序列 hint）+ `repeats`
- **输出**：`best_sequence` + `best_sequence_filepath`

## 前置条件

- ViennaRNA 微服务（端口 8003）

## 工具

- `inverse_fold_rna_secondary_structure_vienna`

## 标准工具链

见 `docs/workflows/inverse_folding_viennarna_workflow.md`。

