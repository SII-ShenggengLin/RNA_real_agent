# `predict_rna_secondary_structure_with_linearfold`

- **source**: `https://github.com/LinearFold/LinearFold`
- **endpoint**: `http://127.0.0.1:8015/fold`
- **input schema**: `rna_agent_system/agent_core/tools.py:LinearFoldSecondaryInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:LinearFoldOutput`

## 能力边界

- **capabilities**：LinearFold beam search 预测二级结构与能量（服务端实现）
- **limitations**：beam 参数影响结果；属于近似搜索

