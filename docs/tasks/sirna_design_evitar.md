# 任务：`sirna_design_evitar`

## 任务目标

通过 Evitar 生成 siRNA/Cas13 guide 候选，并输出候选列表文件与前几条结果预览。

## 适用输入

- FASTA 文件路径（病毒/转录本等）

## 输出结果

- `output_filepath`（结果文件，尽量在 `workspace/`）
- `top_results`（前 N 条候选行）
- `result_count`

## 前置条件

- Linux 环境（上游 Evitar 二进制为 Linux 可执行文件）
- Evitar 微服务可用：`microservices/evitar_service`（端口 8016）

## 使用到的工具

- `design_sirna_with_evitar`

## 标准工具链步骤

见 `docs/workflows/sirna_design_evitar_workflow.md`。

## 当前限制

- 本仓库不提供生产级 siRNA efficacy/off-target 评估；如需需另行接入真实工具链

## 示例调用入口

- Workflow：`agent_core/nodes.py`（`evitar` 关键词触发）

