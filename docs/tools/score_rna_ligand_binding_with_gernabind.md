# `score_rna_ligand_binding_with_gernabind`

- **source**: `https://github.com/GENTEL-lab/GerNA-Bind`
- **endpoint**: `http://127.0.0.1:8010/score`
- **input schema**: `rna_agent_system/agent_core/tools.py:GerNABindScoreInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:GerNABindScoreOutput`

## 能力边界

- **capabilities**：对 RNA + ligand SMILES 输出 affinity 分类概率/标签（GerNA-Bind 模型）
- **limitations**：依赖 GPU/权重；binding-site 预测是另一条接口路径（若启用）

