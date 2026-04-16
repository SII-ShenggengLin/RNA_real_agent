# `predict_rna_tertiary_structure_with_rhofold`

- **source**: `https://github.com/ml4bio/RhoFold`
- **endpoint**: `http://127.0.0.1:8005/predict`
- **input schema**: `rna_agent_system/agent_core/tools.py:RhoFoldInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:RhoFoldOutput`

## 能力边界

- **capabilities**：输入单条 RNA 序列，预测 3D 结构（本仓库服务侧为 single-sequence 模式）
- **limitations**：依赖 GPU/权重；输出质量与运行配置相关

