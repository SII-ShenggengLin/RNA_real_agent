# `score_rna_ligand_binding_with_gernabind`

> **INTERFACE LOCK (v0.1.0)**: 以下接口定义已经过与原始仓库 `https://github.com/GENTEL-lab/GerNA-Bind` 的逐行对照验证，并以端到端测试确认正确。任何后续修改必须同步更新以下全部位置，禁止单方面变更：
>
> - `microservices/gernabind_service/main.py` :: `ScoreRequest` / `ScoreResponse` / `BindingSiteRequest` / `BindingSiteResponse`
> - `agent_core/tools.py` :: `GerNABindScoreInput` / `score_rna_ligand_binding_with_gernabind`
> - `agent_core/tool_specs.py` :: `GerNABindScoreOutput` / `score_rna_ligand_binding_with_gernabind` `ToolSpec`
> - `agent_core/state.py` :: `gernabind_*` 字段
> - 本文档

- **source**: `https://github.com/GENTEL-lab/GerNA-Bind`
- **endpoint**: `http://127.0.0.1:8010/score`
- **input schema**: `rna_agent_system/agent_core/tools.py:GerNABindScoreInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:GerNABindScoreOutput`

## 能力边界

- **capabilities**：对 RNA + ligand SMILES 输出 affinity 分类概率/标签（GerNA-Bind 模型）。支持通过 `dataset`（Robin / Biosensor）和 `split_method`（random / RNA / mol / both）参数自动选择合适的预训练权重。
- **limitations**：依赖 GPU/权重；binding-site 预测是另一条接口路径（若启用）；不指定 `dataset` 时默认使用 `Robin_random.pth`。

## 验证记录

- **接口验证日期**: 2026-04-22
- **验证方式**: 以原始仓库 `inference_affinity.py` / `inference_binding_site.py` / `data_utils/process_data.py` 为基准，逐行核对输入生成、 collate 函数、模型前向传播参数顺序及输出解析逻辑。
- **端到端测试**:
  - `POST /score` (CPU) ✅ — `probability_positive: 0.1273`, `predicted_label: 0`
  - `POST /score` (GPU/cuda:0) ✅ — 结果与 CPU 一致（差异 < 1e-6）
  - `POST /predict-binding-site` (CPU) ✅ — 返回 54 个残基级结合分数
- **依赖服务**: RhoFold 微服务 (port 8005) 用于 RNA 3D 结构预处理
