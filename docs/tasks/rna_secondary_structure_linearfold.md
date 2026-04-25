# 任务：`rna_secondary_structure_linearfold`

## 任务目标

用 LinearFold 预测 RNA 二级结构与能量（近似 beam search），支持约束折叠、SHAPE 引导折叠、Zuker 次优结构枚举以及已知结构的能量评估。

## 输入 / 输出

- **输入**：RNA 序列文件路径 + 可选参数（见各工具输入 schema）
- **输出**：`structure`、`mfe`、`energy`、`structures` 等（见各工具输出 schema）

## 前置条件

- `microservices/linearfold_service`（端口 8015）
- `external_repos/LinearFold` 已编译（`make` 生成 `bin/linearfold_c` + `bin/linearfold_v`）

## 工具

| 工具 | 端点 | 说明 |
|---|---|---|
| `predict_rna_secondary_structure_with_linearfold` | `/fold` | 标准折叠、约束折叠、SHAPE 引导折叠 |
| `predict_rna_secondary_structure_with_linearfold_zuker` | `/fold/zuker_subopt` | Zuker 次优结构枚举 |
| `evaluate_rna_structure_with_linearfold` | `/eval` | 评估给定结构的自由能 |

## 标准工具链

见 `docs/workflows/rna_secondary_structure_linearfold_workflow.md`。
