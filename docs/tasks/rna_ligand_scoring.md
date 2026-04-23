# 任务：`rna_ligand_scoring`

## 任务目标

对 RNA + ligand（SMILES）计算模型打分/分类概率，用于候选优先级排序或筛选。

## 输入 / 输出

- **输入**：RNA 序列文件路径 + `smiles`
- **输出**：`probability_positive`、`predicted_label`、`raw_logits`、checkpoint/设备/模型信息（依工具而定）；RNAsmol 额外支持 `dataset`、`perturbation_type` 权重选择

## 前置条件

- RNAsmol（端口 8007）或 GerNA-Bind（端口 8010）微服务可用，通常依赖 GPU/权重

## 工具

- `score_rna_ligand_binding_with_rnasmol`
- `score_rna_ligand_binding_with_gernabind`

## 标准工具链

见 `docs/workflows/rna_ligand_scoring_workflow.md`。

