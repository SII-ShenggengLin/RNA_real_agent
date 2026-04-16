# 任务：`rna_structure_to_sequence_design`

## 任务目标

输入 RNA 的 3D 结构（PDB，可选二级结构），设计一个与结构匹配的候选 RNA 序列。

## 输入 / 输出

- **输入**：`pdb_filepath`（必填），可选 `secondary_structure_filepath`
- **输出**：设计序列与输出 FASTA 文件路径

## 前置条件

- RhoDesign 微服务（端口 8006），通常依赖 GPU/权重

## 工具

- `design_rna_sequence_with_rhodesign`

## 标准工具链

见 `docs/workflows/rna_structure_to_sequence_design_workflow.md`。

