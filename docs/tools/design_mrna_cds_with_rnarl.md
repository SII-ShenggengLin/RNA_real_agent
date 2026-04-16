# `design_mrna_cds_with_rnarl`

- **source**: `https://github.com/SII-ShenggengLin/RNARL`
- **endpoint**: `http://127.0.0.1:8008/generate/cds`
- **input schema**: `rna_agent_system/agent_core/tools.py:RNARLCdsInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:ProteinToCdsOutput`

## 能力边界

- **capabilities**：输入蛋白序列，运行 RNARL actor 推理生成 CDS
- **limitations**：依赖 GPU、checkpoint、ESM2 本地权重；运行环境约束见项目指南

