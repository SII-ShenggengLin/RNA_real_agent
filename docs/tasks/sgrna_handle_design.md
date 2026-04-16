# 任务：`sgrna_handle_design`

## 任务目标

对给定 sgRNA handle seed 生成候选 handle 序列并输出 best candidate 与候选文件。

## 输入 / 输出

- **输入**：handle seed 文件路径 + sampling 参数（n_samples 等）
- **输出**：`best_sequence`、`output_fasta_filepath`、summary JSON 等

## 前置条件

- `microservices/sgrna_design_service`（端口 8017），通常依赖模型/torch/GPU

## 工具

- `design_sgrna_handle_with_crgpt`

## 标准工具链

见 `docs/workflows/sgrna_handle_design_workflow.md`。

