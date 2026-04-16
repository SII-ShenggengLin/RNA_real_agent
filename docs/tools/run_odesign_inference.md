# `run_odesign_inference`

- **source**: `https://github.com/OTeam-AI4S/ODesign`
- **endpoint**: `http://127.0.0.1:8012/design/from-json`
- **input schema**: `rna_agent_system/agent_core/tools.py:ODesignInferenceInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:ODesignInferenceOutput`

## 能力边界

- **capabilities**：对显式 JSON 定义的设计任务运行 ODesign 推理，输出预测文件与日志
- **limitations**：需要 GPU/权重/数据文件；复杂任务建议由调用方明确准备 JSON

