# `design_mrna_cds_with_lineardesign`

- **source**: `https://github.com/LinearDesignSoftware/LinearDesign`
- **endpoint**: `http://127.0.0.1:8014/generate/cds`
- **input schema**: `rna_agent_system/agent_core/tools.py:LinearDesignCdsInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:ProteinToCdsOutput`

## 能力边界

- **capabilities**：输入蛋白序列，生成 CDS（服务端封装 LinearDesign 可执行文件）
- **limitations**：需要服务器侧已编译 binary；部署环境依赖见项目指南

