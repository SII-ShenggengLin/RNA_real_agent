# `predict_putative_ires_with_iresfinder`

- **source**: `https://github.com/xiaofengsong/IRESfinder`
- **endpoint**: `http://127.0.0.1:8013/predict`
- **input schema**: `rna_agent_system/agent_core/tools.py:IRESfinderPredictionInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:IRESfinderPredictionOutput`

> ⚠️ **INTERFACE LOCK (v0.2.0)**：IRESfinder 接口已锁定，**以 2026-04-23 的修改为准**。任何字段的增删改都必须同步更新以下五个位置，否则会导致多层接口不一致：
> - `agent_core/tools.py` —— LangChain 工具封装（`IRESfinderPredictionInput` / `predict_putative_ires_with_iresfinder`）
> - `agent_core/tool_specs.py` —— ToolSpec 注册表（`IRESfinderPredictionOutput` / `TOOL_SPECS`）
> - `agent_core/state.py` —— AgentState 字段（`iresfinder_*`）
> - `agent_core/nodes.py` —— 节点状态处理（`tool_execution_node` / `critic_node` IRESfinder 分支）
> - `microservices/iresfinder_service/main.py` —— FastAPI 微服务（`IRESfinderPredictRequest` / `IRESfinderPredictResponse`）
>
> **核心对齐原则**：微服务中的特征工程（k-mer 计数、StandardScaler、active column 筛选、19 selected features、LogisticRegressionCV）必须与原始 Perl 仓库 `external_repos/IRESfinder/module/calculate_features.pl` 和 `IRESfinder.py` 的行为保持一致。其中非 wildcard k-mer 计数必须使用**非重叠**匹配（对应 Perl `s/$_/$_/g`），wildcard k-mer 计数使用**重叠**匹配。

## 能力边界

- **capabilities**：使用 IRESfinder 发表模型预测 putative IRES 片段与概率打分。支持三种上游对齐的模式：
  - `mode=0`（默认）：对每条完整序列评分；
  - `mode=1`：从 FASTA header 末尾提取 `start_pos end_pos` 坐标，截取子序列后评分；
  - `mode=2`：滑动窗口切分序列后评分（需指定 `window_size` 和 `step_size`）。
- **limitations**：
  - 依赖服务端模型资产 `external_repos/IRESfinder/module/train.data`；
  - 输入序列归一化为 DNA（U→T），仅接受 A/C/G/T；
  - 本服务为 Python 3 重实现，与原始 Python 2.7 + sklearn 0.17 的数值结果可能存在微小差异（通常 < 0.001），但分类标签一致。

## 运行环境

- **设备**：纯 CPU 运行（逻辑回归模型，无需 GPU）。
- **Conda 环境**：`iresfinder_service_env`
- **启动命令**：`bash microservices/iresfinder_service/start.sh`
