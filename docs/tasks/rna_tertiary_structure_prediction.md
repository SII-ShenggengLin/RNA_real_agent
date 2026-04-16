# 任务：`rna_tertiary_structure_prediction`

## 任务目标

对单条 RNA 序列预测 3D 结构（PDB）与置信度摘要。

## 输入 / 输出

- **输入**：RNA 序列文件路径
- **输出**：`pdb_filepath`、`mean_plddt` 等

## 前置条件

- RhoFold 微服务（端口 8005），通常依赖 GPU/权重

## 工具

- `predict_rna_tertiary_structure_with_rhofold`

## 标准工具链

见 `docs/workflows/rna_tertiary_structure_prediction_workflow.md`。

