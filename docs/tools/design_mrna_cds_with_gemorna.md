# `design_mrna_cds_with_gemorna`

- **source**: `https://github.com/RainaBio/GEMORNA`
- **endpoint**: `http://127.0.0.1:8004/generate/cds`
- **input schema**: `rna_agent_system/agent_core/tools.py:GemornaCdsInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:GemornaCdsOutput`

## 能力边界

- **capabilities**：输入蛋白序列，运行 GEMORNA 生成 CDS
- **limitations**：依赖 Linux GPU、checkpoint、Python ABI（3.10）；运行环境约束见项目指南

