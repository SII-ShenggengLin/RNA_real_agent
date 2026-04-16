# `design_rna_sequence_with_rhodesign`

- **source**: `https://github.com/ml4bio/RhoDesign`
- **endpoint**: `http://127.0.0.1:8006/design/from-structure`
- **input schema**: `rna_agent_system/agent_core/tools.py:RhoDesignInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:RhoDesignOutput`

## 能力边界

- **capabilities**：输入 RNA 的 3D 结构（PDB，可选二级结构文件），输出与结构匹配的设计序列
- **limitations**：依赖 GPU/权重；输入 PDB 必须可解析

