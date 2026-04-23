# `run_odesign_inference`

- **source**: `https://github.com/OTeam-AI4S/ODesign`
- **endpoint**: `http://127.0.0.1:8012/design/from-json`
- **input schema**: `rna_agent_system/agent_core/tools.py:ODesignInferenceInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:ODesignInferenceOutput`

> ⚠️ **INTERFACE LOCK (v0.3.0)**：ODesign 接口已锁定。任何字段的增删改都必须同步更新以下三个位置，否则会导致三层接口不一致：
> - `agent_core/tools.py` —— LangChain 工具封装（`ODesignInferenceInput` / `run_odesign_inference`）
> - `agent_core/tool_specs.py` —— ToolSpec 注册表（`ODesignInferenceOutput`）
> - `microservices/odesign_service/main.py` —— FastAPI 微服务（`ODesignInferenceRequest` / `ODesignInferenceResponse`）

## 能力边界

- **capabilities**：对显式 JSON 定义的设计任务运行 ODesign 推理，输出预测文件与日志
- **limitations**：需要 GPU/权重/数据文件；复杂任务建议由调用方明确准备 JSON

