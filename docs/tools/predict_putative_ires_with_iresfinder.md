# `predict_putative_ires_with_iresfinder`

- **source**: `https://github.com/xiaofengsong/IRESfinder`
- **endpoint**: `http://127.0.0.1:8013/predict`
- **input schema**: `rna_agent_system/agent_core/tools.py:IRESfinderPredictionInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:IRESfinderPredictionOutput`

## 能力边界

- **capabilities**：对输入 RNA 预测 putative IRES 片段与打分（服务端实现为 Python3 重实现）
- **limitations**：依赖服务端模型/数据文件；结果为模型预测

