# `analyze_cds_codon_metrics_with_codonw_slim`

- **source**: `https://github.com/smsaladi/codonw-slim`
- **endpoint**: `http://127.0.0.1:8018/analyze/cds`
- **input schema**: `rna_agent_system/agent_core/tools.py:CodonwSlimAnalyzeInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:CodonwSlimOutput`

## 能力边界

- **capabilities**：对 CDS 计算 CAI/Fop/CBI/ENC 等密码子指标，并可输出 JSON 明细到 workspace
- **limitations**：输入应为 in-frame CDS；指标解释需结合选择的参考表/遗传密码参数

