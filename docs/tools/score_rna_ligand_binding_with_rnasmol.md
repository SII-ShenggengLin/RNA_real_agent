# `score_rna_ligand_binding_with_rnasmol`

- **source**: `https://github.com/hongli-ma/RNAsmol`
- **endpoint**: `http://127.0.0.1:8007/score`
- **input schema**: `rna_agent_system/agent_core/tools.py:RNAsmolScoreInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:RNAsmolScoreOutput`

## 能力边界

- **capabilities**：对 RNA + ligand SMILES 输出分类概率/标签（RNAsmol 模型）
- **limitations**：模型输出依赖 checkpoint；不等同实验亲和力

