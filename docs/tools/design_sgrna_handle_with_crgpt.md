# `design_sgrna_handle_with_crgpt`

- **source**: `https://github.com/bitguolab/sgrna_design`
- **endpoint**: `http://127.0.0.1:8017/design`
- **input schema**: `rna_agent_system/agent_core/tools.py:SgRNADesignInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:SgRNADesignOutput`

## 能力边界

- **capabilities**：从 seed/handle 序列生成候选 handle，并给出 best candidate 与输出文件
- **limitations**：依赖模型权重与 torch 运行时限制；结果为模型生成

