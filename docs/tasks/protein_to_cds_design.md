# 任务：`protein_to_cds_design`

## 任务目标

输入蛋白序列，生成一个候选 CDS（由服务端工具实现：LinearDesign / RNARL / GEMORNA 之一）。

## 输入 / 输出

- **输入**：蛋白序列文件路径
- **输出**：生成序列（`generated_sequence`）与 `output_filepath`

## 前置条件

- 依赖对应微服务与运行环境（多为 Linux，部分需 GPU/权重）

## 工具

- `design_mrna_cds_with_lineardesign`
- `design_mrna_cds_with_rnarl`
- `design_mrna_cds_with_gemorna`

## 标准工具链

见 `docs/workflows/protein_to_cds_design_workflow.md`。

