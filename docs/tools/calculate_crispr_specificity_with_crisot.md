# `calculate_crispr_specificity_with_crisot`

- **source**: `https://github.com/bm2-lab/CRISOT`
- **endpoint**: `http://127.0.0.1:8011/spec`
- **input schema**: `rna_agent_system/agent_core/tools.py:CrisotSpecInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:CrisotSpecOutput`

## 能力边界

- **capabilities**：对 CSV 中的 on/off 序列对计算 CRISOT specificity，并输出带分数的 CSV
- **limitations**：不生成 off-target 列表；仅对给定 CSV 做计算

