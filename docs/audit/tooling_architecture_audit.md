# 工具系统架构审计（按代码为准）

> 审计目标：梳理当前项目 agent 如何接入工具、工具注册与 schema 现状、planning/tool calling/critic/retry 机制是否“真实有效”。
>
> 关键代码入口：
> - `rna_agent_system/agent_core/tools.py`（工具封装：LangChain `@tool` + Pydantic args_schema + HTTP 调用）
> - `rna_agent_system/agent_core/nodes.py`（工具注册/路由/specialist/tool executor/critic）
> - `rna_agent_system/agent_core/graph.py`（LangGraph 图）
> - `rna_agent_system/agent_core/state.py`（状态字段）
> - `rna_agent_system/frontend/app.py`（集成入口）

---

## 1. 当前工具接入方式（真实机制）

### 1.1 工具注册机制（registry）

- **位置**：`rna_agent_system/agent_core/nodes.py`
- **机制**：
  - 以静态列表注册工具对象：`SIRNA_TOOLS` / `CRISPR_TOOLS` / `MRNA_TOOLS`
  - 合并后形成 `TOOLS`
  - 通过 `TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}` 建立名称到工具对象的映射
- **结论**：当前 registry 是 **Python 进程内静态 registry**，没有单独的“工具注册中心文件/配置/插件系统”。

### 1.2 工具描述 schema 与输入 schema

- **位置**：`rna_agent_system/agent_core/tools.py`
- **机制**：
  - 使用 `langchain_core.tools.tool` 装饰器导出工具
  - 使用 `@tool(args_schema=<Pydantic BaseModel>)` 约束输入参数（例如 `SirnaEfficiencyInput`、`BlastnSearchInput` 等）
- **现状结论**：
  - **输入 schema 相对统一**：大部分工具都有 `args_schema`，字段类型/默认值/部分范围约束（`ge/le`）已存在。
  - **“严格”程度不一致**：有些工具有严格生物学约束（例如 `_normalize_crisot_sequence` 强制 23nt），但多数工具只检查“文件可读/HTTP 成功”，对输入序列合法性/长度边界/互斥字段等约束不足或分散在工具内部逻辑里。

### 1.3 输出 schema / error schema（目前缺失统一规范）

- **问题 1：输出类型不统一**
  - 同一系统内工具返回值混用：
    - `dict[str, Any]`（多数工具）
    - `str`（例如 `predict_rna_secondary_structure` 返回拼接的 `filepath=...; structure=...; mfe=...` 字符串）
- **问题 2：输出字段不稳定/不可验证**
  - `nodes.py` 里对 tool_result 的读取是“按 key 猜测式”的（`tool_result.get("xxx")`），缺少“返回 schema 版本”约束。
- **问题 3：缺少统一 error schema**
  - `tools.py` 通常用 `raise ValueError(...)` 抛错，错误类型/字段/可恢复性（retryable / fatal）没有统一结构。

**结论**：当前工具接口定义**并不统一**，尤其是**输出 schema 与错误 schema**层面。

---

## 2. Agent 的 planning / tool calling / critic / retry 机制（按实现分解）

### 2.1 Router / Specialist（planning 与 tool calling）

- **位置**：`rna_agent_system/agent_core/nodes.py`
- **现状**：
  - Router 与 Specialist 均为**规则驱动**：通过关键词匹配决定 route 与 tool_calls。
  - tool_calls 由代码直接构造（`AIMessage(content=..., tool_calls=[...])`），不是 LLM 自主规划。
- **结论**：
  - 当前系统更像是**确定性 workflow 系统**，不是“开放式 agent 自由选工具”。
  - 这与仓库文档 `rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md` 的“规则驱动”描述一致。

### 2.2 Tool Execution（工具执行器）

- **位置**：`rna_agent_system/agent_core/nodes.py` → `tool_execution_node`
- **机制**：
  - 从 `AIMessage.tool_calls` 读取 tool 名称与 args
  - 使用 `TOOLS_BY_NAME` 查找工具对象
  - 调用 `tool_obj.invoke(tool_args)` 同步执行
  - 将结果序列化为 `ToolMessage(content=json.dumps(...))` 写回 messages
  - 同时把部分字段写回 `AgentState`（大量 `if tool_name == ...:` 分支）
- **风险点**：
  - 工具返回字段变化会直接导致 state 写回缺失或错误，但不会在类型层被捕获。
  - 工具 side-effect（写 workspace 文件）与 state 写回耦合在 `tool_execution_node`，扩展成本较高。

### 2.3 Critic / Retry（是否真实提升结果？）

- **位置**：`rna_agent_system/agent_core/nodes.py` → `critic_node`
- **现状**：
  - Critic 为**硬规则**，不是 LLM：
    - siRNA：`off_target_genes > 0` → reject → retry（直到 `max_retries`）
    - mRNA fold：当文本包含 fold 语义且 `mfe > -20.0` → reject → retry
  - `route_after_critic` 根据 `state["next_action"]` 决定回到哪个 specialist 或结束。
- **结论**：
  - 当前 critic **不是“提升生物学结果的评审器”**，更像是：
    - **格式/阈值检查**（`mfe` 阈值）
    - **流程补救**（触发 retry 循环）
  - 且存在已知问题（文档也写了）：短序列 MFE 可能天然 > -20，导致反复 reject 直到耗尽重试次数后放行。

---

## 3. 哪些工具描述过于松散 / schema 不严格（基于现有代码的可证据点）

### 3.1 输出 schema 松散（典型例）

- **`predict_rna_secondary_structure`（ViennaRNA fold）**
  - 返回 **字符串**（拼接字段），不利于后续工具链串联、评分、审计。
- **大量工具返回 `dict[str, Any]`**
  - 但缺少“output schema / version / error schema”，`nodes.py` 只能用 `.get()` 读字段。

### 3.2 能力边界不清（典型例）

- **HTTP 包装型工具**（多数）
  - 只在 docstring 写“调用某微服务”，但未在代码层提供统一的：
    - capabilities / limitations
    - requires（外部依赖，如 GPU、模型权重、参考基因组、OS 限制）
    - produces（关键输出字段定义与单位）

### 3.3 明确的 mock 工具（必须在“支持任务”里降级）

- `rna_agent_system/microservices/sirna_attsioff`（mock）
- `rna_agent_system/microservices/off_target_blast`（mock）
- `rna_agent_system/agent_core/tools.py:mock_codon_optimization`（mock）

---

## 4. 与需求可能冲突的既有实现（最小破坏修复方向）

你要求“不要保留 siRNA mock 入口来假装支持”。但当前实现里：

- Router 会在出现 `sirna/脱靶/off-target` 等关键词时路由到 `sirna_specialist`
- `sirna_specialist` 默认会调用 mock 工具（效率预测 + mock 脱靶）
- Critic 还依赖 mock 脱靶数来决定重试

**最小破坏修复方案（后续阶段实施，不在本审计阶段改代码）**：

- 删除 `predict_sirna_efficiency` 与 `check_off_target` 两个工具 + 两个微服务 + `SIRNA_TOOLS` 注册引用；
- 收紧 Router：`sirna_specialist` 只保留“非 mock 的 siRNA 相关能力”（当前代码里是 ViennaRNA duplex 与 Evitar），其余 siRNA 能力明确标为“不支持”并从入口移除。

---

## 5. 本阶段变更（仅文档）

- **新增文件**：
  - `docs/audit/tooling_architecture_audit.md`
- **原因**：将工具注册、schema 现状、agent 机制按代码证据审计并固化，作为后续“严格接口规范 + 任务工具链”重构依据。

---

## 6. 验证方式（不改代码即可执行）

- **全局搜索 registry/工具调用入口**：
  - 搜索 `TOOLS_BY_NAME` / `SIRNA_TOOLS` / `@tool(args_schema=`
- **确认 critic 与 retry 逻辑**：
  - 搜索 `critic_node` / `route_after_critic` / `max_retries`
- **确认输出类型不一致**：
  - 搜索 `def predict_rna_secondary_structure` 返回值类型与 `return (` 片段（字符串拼接）

