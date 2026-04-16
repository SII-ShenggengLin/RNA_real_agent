# `inverse_fold_rna_secondary_structure_vienna`

- **source**: `https://github.com/ViennaRNA/ViennaRNA`
- **endpoint**: `http://127.0.0.1:8003/inverse-fold`
- **input schema**: `rna_agent_system/agent_core/tools.py:InverseFoldViennaInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:ViennaInverseFoldOutput`

## 能力边界

- **capabilities**：给定 dot-bracket 结构（可选起始序列 hint）运行 RNAinverse，输出一个可折叠到该结构的候选序列
- **limitations**：启发式搜索；不保证唯一/全局最优

