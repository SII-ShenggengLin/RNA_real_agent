# 严格工具接口规范（代码/文档统一标准）

> 本规范的代码落地位置：
>
> - 规范模型：`rna_agent_system/agent_core/tool_interface.py`
> - 工具清单与逐工具规格：`rna_agent_system/agent_core/tool_specs.py`
>
> 本目录下每个工具文档必须与 `ToolSpec` 保持一致；不得在文档中宣称 wrapper 未实现或上游工具不支持的能力。

---

## 1. 工具身份（Identity）

每个工具必须有稳定身份字段：

- **identity**：与 LangChain 工具名一致（例如 `run_blastn_similarity_search`）
- **display_name**：面向人类的名称
- **version**：本仓库内 wrapper/微服务版本（来自 `microservices/*/main.py` 的 `FastAPI(version=...)` 或 wrapper 自身版本）
- **source**：上游仓库/官网/论文（URL 或明确引用字符串）

---

## 2. 运输层（Transport）

必须明确工具在本仓库的调用方式：

- `http`：FastAPI 微服务（本仓库当前绝大多数工具）
- `subprocess`：本地子进程调用（若未来新增）
- `python_api`：直接 import 调用（本仓库当前原则上避免）

若为 `http`，必须给出：

- **endpoint**：wrapper 默认使用的 URL（例如 `http://127.0.0.1:8019/blastn`）

---

## 3. 能力边界（Capabilities / Limitations）

工具文档必须可审计、可执行、可反驳：

- **capabilities**：必须是“可落地”的动作描述（例如“计算 duplex MFE（kcal/mol）”），不能写泛泛的“RNA analysis”
- **limitations**：明确不能做什么/不适用什么任务（例如“不是 siRNA efficacy 预测”）
- **task_tags**：工具被允许服务的任务标签集合（用于后续路由约束）

---

## 4. 输入/输出 schema（IO Schema）

### 4.1 输入 schema（input_model）

必须使用 Pydantic 模型定义：

- 字段名/类型/必填/默认值
- 数值范围（`ge/le/gt/lt`）
- 互斥/依赖关系（必要时用验证器）
- 生物学约束（例如序列字符集、长度）

### 4.2 输出 schema（output_model）

必须使用 Pydantic 模型定义 wrapper 的返回字段（最少包含“关键字段”）：

- 字段含义与单位（例如 `mfe_kcal_per_mol` 的单位）
- 评分方向（越大越好/越小越好）若适用
- 文件路径字段必须明确是 workspace 相对路径还是服务器绝对路径

### 4.3 error schema（error_model）

若某工具需要结构化错误（可恢复 vs 致命），应定义 `error_model` 并在 wrapper 中返回/抛出可映射错误。

---

## 5. 依赖与执行约束（requires / status）

每个工具必须显式声明：

- `requires`：GPU / OS / checkpoint 路径 / 外部数据库 等
- `status`：`available` / `partial` / `unavailable` / `mock`

注意：

- `partial` 用于“代码链路闭合但运行依赖在特定环境（Linux/GPU/权重）才满足”的情况；
- `mock` 用于“返回伪造结果”的工具；此类工具不应被计入“真实支持任务”。

---

## 6. Agent 使用说明（通过任务/工作流文档承载）

工具“如何被 agent 使用”不写在工具能力里，而应在：

- `docs/tasks/<task>.md`（任务定义）
- `docs/workflows/<task>_workflow.md`（逐步工具链）

这样能避免把“编排策略”误写成“工具能力”。

