# `score_crispr_off_target_with_crisot`

- **source**: `https://github.com/bm2-lab/CRISOT`
- **endpoint**: `http://127.0.0.1:8011/score`
- **input schema**: `rna_agent_system/agent_core/tools.py:CrisotScoreInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:CrisotScoreOutput`

## 能力边界

- **capabilities**：对单个 sgRNA-靶序列对计算 CRISOT score
- **limitations**：不做 genome-wide 搜索；输入会被 wrapper 归一化并强制长度为 23nt

