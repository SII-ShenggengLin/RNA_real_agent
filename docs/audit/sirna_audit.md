# siRNA 相关实现审计（按代码为准）

> 审计范围：全仓库（不含运行时生成的 `workspace/`）
>
> 关键词：`sirna` / `siRNA` / `mock` / siRNA 设计/打分/脱靶/候选生成
>
> 结论摘要（先给结论，后给证据）：
>
> - **“两个 siRNA mock”= 两个 FastAPI 微服务**：`microservices/sirna_attsioff`（端口 8001）与 `microservices/off_target_blast`（端口 8002），均返回**随机/伪造结果**。
> - 这两个 mock **不仅是 API 层 mock**：它们还被封装成 agent 可见的 `@tool`（`predict_sirna_efficiency` / `check_off_target`），并被 workflow（Router/Specialist/Tool Executor）与前端 UI 直接使用。
> - 当前仓库还存在**非 siRNA 的 mock 工具**：`mock_codon_optimization`（mRNA 方向）。本文件仅记录（不在“两个 siRNA mock”范围内）。

---

## 1. 发现清单（文件路径 → 作用 → mock/占位判断 → 引用链 → 删除影响）

### 1.1 siRNA mock 微服务（核心确认点：就是两个独立服务）

#### A) `rna_agent_system/microservices/sirna_attsioff/`

- **文件**：
  - `rna_agent_system/microservices/sirna_attsioff/main.py`
  - `rna_agent_system/microservices/sirna_attsioff/start.sh`
  - `rna_agent_system/microservices/sirna_attsioff/environment.yml`
- **作用**：FastAPI 服务 `POST /predict`，输入 `sequence`，返回 `efficiency_score`。
- **是否 mock/stub/placeholder**：**是**。
  - `main.py` 第一行 docstring 明确：`"Mock siRNA efficiency prediction microservice."`
  - 实现用 `random()` 生成 `efficiency_score`（0~1）。
- **是否被路由/agent/workflow/UI/测试引用**：**是**（见 1.2 / 1.3 / 1.4）。
- **删除后可能影响模块**：
  - `agent_core/tools.py`（`predict_sirna_efficiency`）
  - `agent_core/nodes.py`（`SIRNA_TOOLS`、`sirna_specialist_node`、`tool_execution_node`、`critic_node` 的 siRNA 分支）
  - `frontend/app.py`（展示 `efficiency_score`）
  - `rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md`（能力/端口表宣称）

#### B) `rna_agent_system/microservices/off_target_blast/`

- **文件**：
  - `rna_agent_system/microservices/off_target_blast/main.py`
  - `rna_agent_system/microservices/off_target_blast/start.sh`
  - `rna_agent_system/microservices/off_target_blast/environment.yml`
- **作用**：FastAPI 服务 `POST /check`，输入 `sequence`，返回 `off_target_genes`。
- **是否 mock/stub/placeholder**：**是**。
  - `main.py` 第一行 docstring 明确：`"Mock off-target check microservice."`
  - 实现用 `randint(0, 2)` 生成 `off_target_genes`（0~2）。
- **是否被路由/agent/workflow/UI/测试引用**：**是**（见 1.2 / 1.3 / 1.4）。
- **删除后可能影响模块**：
  - `agent_core/tools.py`（`check_off_target`）
  - `agent_core/nodes.py`（同上）
  - `frontend/app.py`（展示 `off_target_genes`）
  - `rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md`（能力/端口表宣称）

---

### 1.2 Agent Tool 层（`@tool` 包装：让 agent “看见并能调用” mock）

#### `rna_agent_system/agent_core/tools.py`

- **相关工具函数**：
  - `predict_sirna_efficiency(filepath, service_url="http://127.0.0.1:8001/predict")`
  - `check_off_target(filepath, service_url="http://127.0.0.1:8002/check")`
- **作用**：读取 `filepath` 内容，通过 HTTP 调用上述两个 mock 微服务，并把响应 dict 原样返回（附加 `filepath`）。
- **是否 mock/stub/placeholder**：**是（包装 mock 服务）**。
  - docstring 明确写了 `Predict mock siRNA efficiency` / `Check mock off-target risk`。
- **删除影响**：
  - `nodes.py` 的 siRNA 工具链与 `SIRNA_TOOLS` registry 依赖这两个工具对象存在（`tool.name` 会被映射到 `TOOLS_BY_NAME`）。

> 注：`tools.py` 里还有一个**非 siRNA** mock：`mock_codon_optimization`（见 1.6）。它会影响“支持任务审计”，但不属于“两个 siRNA mock”。

---

### 1.3 Workflow/节点层（Router/Specialist/Tool Executor/Critic 直接依赖 mock 结果）

#### `rna_agent_system/agent_core/nodes.py`

- **工具注册中心**（静态列表）：
  - `SIRNA_TOOLS` 显式包含：
    - `predict_sirna_efficiency`
    - `check_off_target`
    - `design_sirna_with_evitar`
    - `compute_sirna_duplex_binding_vienna`
  - `TOOLS = SIRNA_TOOLS + CRISPR_TOOLS + MRNA_TOOLS`
  - `TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}`
- **siRNA Specialist**：
  - 默认 siRNA 路径会发出 tool_calls：`predict_sirna_efficiency` + `check_off_target`
  - duplex 模式会发出：`compute_sirna_duplex_binding_vienna`（ViennaRNA，非 mock）
  - evitar 关键词会发出：`design_sirna_with_evitar`（Evitar，非 mock，但仅 Linux）
- **Tool Executor**：
  - `tool_execution_node` 会执行 tool_calls 并把结果写回 `AgentState`：
    - `efficiency_score` 来自 `predict_sirna_efficiency`（mock）
    - `off_target_genes` 来自 `check_off_target`（mock）
- **Critic**（规则）：
  - siRNA 分支的 reject 规则：`specialist == "sirna_specialist" and off_target_genes > 0` → retry。
  - 这意味着 mock 输出会直接驱动“重试/结束”的控制流。

**判断**：这两个 mock 不只是 API demo，它们已经嵌入 workflow 的关键控制条件（critic 规则）与状态字段写回。

---

### 1.4 前端入口（UI 依赖 mock 字段展示）

#### `rna_agent_system/frontend/app.py`

- **作用**：Streamlit 通过 `compiled_graph.stream(default_state(user_input))` 执行整个图，并在界面上实时展示：
  - `efficiency_score` / `off_target_genes`（当 state 中出现这些 key 时会渲染）
- **是否依赖 mock**：**是**（字段来自 mock 工具写回）。
- **删除影响**：
  - UI 仍可运行，但“siRNA 方向”若被路由到 siRNA specialist，将缺少这两个字段，且相关工具调用会失败（若引用未移除）。

---

### 1.5 文档/宣称（明确写了 mock 且在端口表中占位）

#### `rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md`

- **作用**：系统指南，包含端口/服务/能力表。
- **与 siRNA mock 相关的宣称**：
  - 端口表将 `8001 sirna_attsioff` 与 `8002 off_target_blast` 标为 **Mock 服务**。
  - 单独章节 `6.18 Mock 服务 (端口 8001 / 8002)` 明确二者用于开发调试、后续替换真实实现。
- **删除影响**：需同步更新，否则会出现“文档宣称存在能力，但代码已删除”的冲突。

---

### 1.6 其他 mock（非 siRNA，但与“真实支持任务”判断有关）

#### `rna_agent_system/agent_core/tools.py` → `mock_codon_optimization(filepath)`

- **作用**：读取序列 → sleep → 做简单替换 → 返回固定 `cai_score=0.88`，并写入 `workspace/mrna_opt_*.fasta`。
- **是否 mock/stub/placeholder**：**是**（函数 docstring 明确 `Mock codon optimization`）。
- **是否被 workflow 引用**：**是**。
  - `nodes.py` 的 `MRNA_TOOLS` 列表包含该工具，并在 `tool_execution_node` 解析其输出写回 state。
- **影响**：在后续“支持任务清单”里必须标记为 **不可用/不算真实能力**（因为 fake result）。

---

## 2. “两个 siRNA mock”到底是哪两个？（精确定义）

按代码证据，“两个 siRNA mock”同时满足：

- **独立服务目录存在**：`microservices/<name>/main.py`
- **服务实现返回随机/伪造结果**（非真实算法）
- **被 agent 工具层封装为 `@tool`**，并被 `SIRNA_TOOLS` 注册，能进入 workflow

因此，本仓库中“两个 siRNA mock”的**准确定义**为：

1. `rna_agent_system/microservices/sirna_attsioff` + `agent_core/tools.py:predict_sirna_efficiency`
2. `rna_agent_system/microservices/off_target_blast` + `agent_core/tools.py:check_off_target`

---

## 3. 其他与 siRNA/mock 关键词强相关的文档（历史指令/占位说明）

这些文件不是运行时入口，但会在后续“移除能力/更新文档”阶段产生冲突（需要同步修订或明确标记历史背景）：

- `命令内容1.md`
  - 描述 Phase 1 目标：用 `sirna_attsioff` 与 `off_target_blast` 两个 Mock API 跑通 workflow。
- `命令内容2.md`
  - 描述 Phase 2 重构（workspace、路由、多分支、critic 循环），其中包含“新增 mRNA mock 工具”的历史说明。
- `命令内容3.md`
  - 明确提到要新增 `mock_codon_optimization`（已存在）与 `mock_rna_fold`（仓库中**不存在实现**，只存在于文档指令里）。

---

## 4. 删除后影响面（按入口层次列出）

> 本节为第二阶段“彻底移除”提供影响面清单；本审计阶段不改代码。

- **微服务层**：
  - 端口 8001/8002 相关的启动脚本与 conda env 将消失。
- **工具层**：
  - agent 不再可调用 `predict_sirna_efficiency` / `check_off_target`。
- **workflow 层**：
  - `sirna_specialist_node` 默认分支需要重写（否则会尝试调用已删除工具）。
  - `critic_node` 的 `off_target_genes > 0` 拒绝规则需要调整（否则依赖已删除字段来源）。
- **UI 层**：
  - `frontend/app.py` 中对 `efficiency_score/off_target_genes` 的展示逻辑需要调整为“可选字段”（或按支持任务渲染）。
- **文档层**：
  - `rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md` 的端口表与 mock 服务说明必须更新，避免“假装支持”。

---

## 5. 本阶段变更（仅文档）

- **新增文件**：
  - `docs/audit/sirna_audit.md`
- **原因**：把 siRNA/mock 的真实边界、引用链与删除影响面固化为可审计文档，作为第二阶段删除的实施依据。

---

## 6. 验证方式（不改代码即可执行）

- **验证“两个 mock 服务”定位正确**：
  - 搜索 `microservices/sirna_attsioff` 与 `microservices/off_target_blast`
  - 在 `main.py` 中确认 `Mock ...` docstring + `random()/randint()` 伪造输出
- **验证 agent/workflow/UI 引用链**：
  - 搜索 `predict_sirna_efficiency` / `check_off_target`
  - 确认 `nodes.py:SIRNA_TOOLS` 注册 + `sirna_specialist_node` 默认调用 + `tool_execution_node` 写回 `AgentState`
  - 确认 `frontend/app.py` 渲染 `efficiency_score/off_target_genes`


