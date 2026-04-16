# `search_crispr_off_targets_with_crisot`

- **source**: `https://github.com/bm2-lab/CRISOT`
- **endpoint**: `http://127.0.0.1:8011/off-spec`
- **input schema**: `rna_agent_system/agent_core/tools.py:CrisotOffSpecInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:CrisotOffSpecOutput`

## 能力边界

- **capabilities**：结合 Cas-OFFinder（服务端）对参考基因组搜索 off-target，并用 CRISOT 计算特异性摘要
- **limitations**：需要 reference genome FASTA；耗时可能较长

