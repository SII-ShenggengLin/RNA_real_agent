# `predict_mrna_stability_with_rnastop`

- **source**: `https://github.com/SII-ShenggengLin/RNASTOP`
- **endpoint**: `http://127.0.0.1:8009/predict/stability`
- **input schema**: `rna_agent_system/agent_core/tools.py:RNASTOPPredictionInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:RNASTOPPredictionOutput`

## 能力边界

- **capabilities**：预测 mRNA 稳定性/降解相关摘要指标（服务端封装 RNASTOP）
- **limitations**：本仓库仅暴露“预测”接口，不包含 beam/MCTS 优化链路

