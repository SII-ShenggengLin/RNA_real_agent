# `optimize_sgrna_with_crisot`

- **source**: `https://github.com/bm2-lab/CRISOT`
- **endpoint**: `http://127.0.0.1:8011/optimize`
- **input schema**: `rna_agent_system/agent_core/tools.py:CrisotOptimizeInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:CrisotOptimizeOutput`

## 能力边界

- **capabilities**：在给定 mismatch/设备等参数下优化 sgRNA，返回最优候选与特异性改善摘要
- **limitations**：依赖参考基因组与 Cas-OFFinder；可能耗时数十分钟（取决于基因组大小与参数）

