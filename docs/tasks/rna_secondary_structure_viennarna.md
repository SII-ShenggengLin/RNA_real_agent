# 任务：`rna_secondary_structure_viennarna`

## 任务目标

对单条 RNA 序列预测二级结构（dot-bracket）与 MFE（kcal/mol）。

## 适用输入

- RNA 序列文件（plain 或 FASTA）

## 输出结果

- `structure`
- `mfe_kcal_per_mol`
- `backend`

## 前置条件

- ViennaRNA 微服务：`microservices/viennarna_fold`（端口 8003）

## 使用到的工具

- `predict_rna_secondary_structure`

## 标准工具链步骤

见 `docs/workflows/rna_secondary_structure_viennarna_workflow.md`。

## 示例调用入口

- UI：`frontend/app.py`
- Workflow：`agent_core/nodes.py`（mRNA specialist 默认/兜底折叠路径）

