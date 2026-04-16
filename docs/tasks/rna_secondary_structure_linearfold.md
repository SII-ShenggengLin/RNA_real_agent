# 任务：`rna_secondary_structure_linearfold`

## 任务目标

用 LinearFold 预测 RNA 二级结构与能量（近似 beam search）。

## 输入 / 输出

- **输入**：RNA 序列文件路径 + `beam_size/use_vienna/dangles`（见工具输入 schema）
- **输出**：`structure`、`mfe` 等（见工具输出 schema）

## 前置条件

- `microservices/linearfold_service`（端口 8015）

## 工具

- `predict_rna_secondary_structure_with_linearfold`

## 标准工具链

见 `docs/workflows/rna_secondary_structure_linearfold_workflow.md`。

