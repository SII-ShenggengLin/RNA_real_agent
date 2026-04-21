# Agent Build Plan（工具抽象层增量）

## 统一工具抽象层设计与用法

本次新增 `rna_agent_system/agent_core/tool_runtime.py`，作为可执行工具运行时抽象层。  
该层与已有 `agent_core/tool_interface.py` / `agent_core/tool_specs.py` 的关系是：

- `tool_interface.py` / `tool_specs.py`：定义工具“规格和 contract”
- `tool_runtime.py`：定义工具“执行方式和标准结果”

即：规格层不变，新增运行时层，避免重复造轮子。

### 核心能力

- 标准结果结构 `ToolResult`
  - `success`
  - `tool_name`
  - `stdout`
  - `stderr`
  - `artifacts`
  - `metrics`
  - `error`
  - `elapsed_time`
- 统一基类 `BaseExecutableTool`
  - 输入 schema 校验（可选 Pydantic `input_model`）
  - `run()` 统一入口
  - 超时与异常捕获
  - 标准化失败返回
- 两类工具实现
  - `PythonFunctionTool`：内部 Python 函数型工具
  - `CommandLineTool`：外部命令行工具 wrapper
- CLI 执行辅助
  - `assemble_command()` 命令拼接
  - `run_subprocess_command()` subprocess 执行、stdout/stderr 捕获、超时、非零退出码处理
  - `managed_temp_dir()` 临时目录管理

### 最小用法示例

1) Python 内部函数工具
- 用 `PythonFunctionTool(name, description, func, input_model=...)` 定义
- `func` 返回 dict 或 `ToolResult`，会自动归一为 `ToolResult`

2) 外部命令行工具
- 用 `CommandLineTool(name, description, base_command, arg_builder=...)` 定义
- `run()` 自动处理：
  - 超时 -> `success=false` + `error.type=timeout`
  - 非零退出码 -> `success=false` + `error.type=ToolExecutionError`

## 后续如何接入具体 RNA 工具

建议按“最小闭环”逐步迁移，不一次性改全量：

1. 先挑一个现有工具（如 `lineardesign` 或 `linearfold`）  
   在 `agent_core/tools.py` 中保留原有 `@tool` 对外接口不变。

2. 在内部执行逻辑中引入 `CommandLineTool`（或 `PythonFunctionTool`）  
   将 subprocess/错误处理从单点函数挪到统一抽象层。

3. 返回值继续映射到现有 `tool_specs.py` output_model  
   保持与 `nodes.py` / `AgentState` 兼容。

4. 新增工具时优先遵循：
   - 先写输入 model
   - 再写 runtime wrapper（函数型或命令行型）
   - 最后在 `tool_specs.py` 注册 contract

## 本次实现文件

- 新增：`rna_agent_system/agent_core/tool_runtime.py`
- 修改：`rna_agent_system/agent_core/__init__.py`
- 新增测试：`rna_agent_system/tests/test_tool_runtime.py`

---

## Agent 工作流数据模型（候选 → 评估 → 排序 → 迭代）

### 与现有结构的关系

- **`agent_core/state.py` 的 `AgentState`**：`TypedDict`，用于 LangGraph 节点间传递当前一条请求的扁平字段（工具返回值、路由等）。适合运行时图状态，不适合承载「多候选 + 可追溯 trace」。
- **`agent_core/workflow_models.py`**（新增）：**Pydantic** 模型，专门承载「生成候选 → 调工具评估 → 打分排序 → 迭代」的可序列化对象，便于 API 返回与结果落盘（`model_dump()` / `model_dump(mode="json")`），与数据库/ORM 无耦合。

### 各对象职责

| 对象 | 职责 |
|------|------|
| **`Candidate`** | 一条候选序列：序列本体、`sequence_type`（mRNA / utr / circrna 等）、来源步骤、`scores`、`metadata`、挂载在该候选上的 **`tool_records`**、`rank`、`status`、时间戳。 |
| **`ToolCallRecord`**（别名 **`StepRecord`**） | 单次工具调用记录：`step_name`、`tool_name`、输入/输出摘要、`success`、`error`、`elapsed_time`、`artifacts` / `metrics`。既可挂在候选上，也可写入任务级 trace。 |
| **`TaskState`** | 一次任务会话：`task_id`、`task_type`、`input_payload`、`constraints`、**`candidates`**、**`best_candidate`**、`iteration_index`、`messages` / `logs`、`status`、时间戳。提供 **`append_candidate`**、**`update_best_candidate(score_key)`** 等辅助方法。 |
| **`WorkflowResult`** | 工作流结束快照：`success`、`task_id`、`best_candidate`、`all_candidates`、`summary`、`errors`、**`trace`**（整次运行的工具/步骤记录列表）。 |

### 辅助函数

- **`sort_candidates_by_score(candidates, score_key, descending=True)`**：按某一 `scores` 字段排序；缺少该字段的候选排在末尾，并为有序部分写入 **`rank`**。

### 实现文件

- 新增：`rna_agent_system/agent_core/workflow_models.py`
- 导出：`rna_agent_system/agent_core/__init__.py`（`Candidate`、`TaskState`、`ToolCallRecord`、`StepRecord`、`WorkflowResult`、`sort_candidates_by_score`）
- 测试：`rna_agent_system/tests/test_workflow_models.py`

### 后续接入方式

迭代循环可在 orchestration 代码中维护一个 **`TaskState`**：每轮生成或更新 **`Candidate`**，调用工具后将 **`ToolCallRecord`** 写入对应候选（或追加到 **`WorkflowResult.trace`**），更新 **`scores`**，再调用 **`sort_candidates_by_score`** 与 **`update_best_candidate`**。最终组装 **`WorkflowResult`** 返回前端或写入 JSON。

---

## Tool Registry + Executor（按名调用工具）

### 与现有能力的关系

- **`tool_specs.py` / `TOOL_SPECS`**：审计与文档用的工具规格（不变）。
- **`nodes.py` 中的 `TOOLS` / `TOOLS_BY_NAME`**：历史上由 LangChain `@tool` 列表手工拼成字典；现已改为使用 **`agent_core.tools.ALL_LANGCHAIN_AGENT_TOOLS`** 作为**单一列表来源**，避免与 registry 分叉。
- **未引入**独立 DI 容器、插件框架或平行 registry；仅增加轻量 **`ToolRegistry`** + **`ToolExecutor`**。

### 核心接口

| 组件 | 路径 | 作用 |
|------|------|------|
| **`ToolRegistry`** | `agent_core/tool_registry.py` | `register` / `register_many`、`get`（缺名抛 `ToolNotRegisteredError`）、`has`、`list_names` |
| **`ToolExecutor`** | `agent_core/tool_executor.py` | `run_tool(tool_name, **kwargs)` → **`ToolResult`**；`run_tool_for_workflow(..., task=, candidate=, ...)` 自动写入 **`Candidate.tool_records`** 与 **`TaskState.logs`** |
| **`build_default_tool_registry(include_demo=False)`** | `agent_core/tool_executor.py` | 从 **`ALL_LANGCHAIN_AGENT_TOOLS`** 注册全部生产 LangChain 工具；`include_demo=True` 时额外注册 **`workflow_demo_echo`**（仅用于联通性示例） |

### 后续 RNA 工具如何接入

1. 在 **`agent_core/tools.py`** 中继续用 **`@tool`** 定义 wrapper（HTTP 调用微服务），并把该函数加入 **`ALL_LANGCHAIN_AGENT_TOOLS`** 对应分组列表（或新增分组并并入总列表）。
2. **`TOOL_SPECS`** 中同步注册契约（现有流程不变）。
3. Workflow 编排中通过 **`ToolExecutor.run_tool("tool_name", filepath=...)`** 或 **`run_tool_for_workflow`** 按名调用，无需在业务代码写长链 `if tool_name == ...`（路由若仍用规则，可逐步改为“计划步 → executor”）。

### 相关文件

- `rna_agent_system/agent_core/tool_registry.py`
- `rna_agent_system/agent_core/tool_executor.py`
- `rna_agent_system/agent_core/tools.py`（`ALL_LANGCHAIN_AGENT_TOOLS`、`workflow_demo_echo`）
- `rna_agent_system/agent_core/nodes.py`（`TOOLS = ALL_LANGCHAIN_AGENT_TOOLS`）
- `rna_agent_system/tests/test_tool_registry_executor.py`

---

## 第一个 workflow 层真实工具：RNA GC 含量（`workflow_rna_gc_content`）

### 候选工具与选型

| 候选 | 依赖 | 输入 | 稳定性 |
|------|------|------|--------|
| **`rna_sequence_metrics_service`（GC）** | Python + FastAPI，端口 **8020** | 单个序列文件路径 | **高**：纯计数，无 Vienna/无 GPU |
| ViennaRNA fold（8003） | Conda bioconda ViennaRNA | 序列 | 中高，依赖编译/环境 |
| LinearFold（8015） | 编译 LinearFold | 序列 | 需编译产物 |
| codonw-slim（8018） | CDS + 参考表 | in-frame CDS | 输入约束更窄 |

**最终选择：`rna_sequence_metrics_service` 的 `/gc-content`（workflow 名 `workflow_rna_gc_content`）。**  
理由：输入仅为 **filepath**；HTTP JSON 响应字段固定；**(G+C)/N**、长度、gc_count 等指标适合作为后续排序与管线验证的起点；环境与 **LangGraph** 并行，不独占 workflow 分支逻辑。

### 实现位置与接口

| 项目 | 路径 |
|------|------|
| 核心逻辑（`run_rna_gc_content_workflow` → `ToolResult`，含 **metrics**：`gc_content`、`sequence_length`、`gc_count`） | `rna_agent_system/agent_core/workflow_tools/rna_gc_content_workflow.py` |
| **`PythonFunctionTool`** 工厂 | `create_workflow_rna_gc_content_tool()`、`register_workflow_rna_gc_content_tool(registry)` |
| 对外导出 | `rna_agent_system/agent_core/workflow_tools/__init__.py` |

**输入（Pydantic）**：`RnaGcContentWorkflowInput` — `filepath`、`service_url`（默认 `http://127.0.0.1:8020/gc-content`）、`timeout_seconds`。  
**输出**：`ToolResult`，`artifacts` 含服务端返回的计数与路径；失败时 `error` 含 HTTP status / detail。

编排层只通过 **registry + executor** 按名调用，不把 HTTP 细节写死在 `nodes.py`。

### 最小示例

前置：启动 `rna_sequence_metrics_service`（见 `microservices/rna_sequence_metrics_service/start.sh`）。

```bash
python rna_agent_system/examples/workflow_gc_content_demo.py
```

脚本会写入测试序列、`ToolExecutor.run_tool_for_workflow`，并把 **`ToolCallRecord`** 写入 **`Candidate.tool_records`** 与 **`TaskState.logs`**。

### 后续接入更多工具的模式

1. 在 **`agent_core/workflow_tools/`** 新增 `{tool}_workflow.py`：`run_*_workflow(payload) -> ToolResult`，封装 HTTP 或 CLI，指标写入 **`metrics`**。
2. 提供 **`create_*_python_tool()`**，用 **`PythonFunctionTool`**（需 **`invoke`** 以供 **`ToolExecutor`**）。
3. 在编排处 **`registry.register(create_...())`**，或按需 **`register_workflow_*`**。
4. LangChain 侧的 **`tools.py` / `@tool`** 仍可保留供 Streamlit 路径；workflow 优先走 **`workflow_*`**，避免两套逻辑分叉——内部可酌情复用同一 HTTP 助手函数。

---

## mRNA 最小闭环 workflow（`MrnaWorkflow` / `run_mrna_workflow`）

目标：在**不做复杂规划**的前提下跑通 **输入 → 候选 → 工具评估 → 打分排序 → 输出 `WorkflowResult`**，并复用既有 **registry / executor** 与 **`workflow_models`**。

### 调用链（固定顺序）

```
MrnaWorkflowInput
  → generate_candidate_sequences（direct / synonymous_minimal / mock_augment）
  → build_candidates → TaskState.candidates
  → 对每个 Candidate：save_sequence（workspace 相对路径）
  → ToolExecutor.run_tool_for_workflow（默认：GC + LinearFold MFE）
  → compute_mrna_metric_bundle + score_mrna_candidate（独立打分模块）
  → sort_candidates_by_score(total_score)
  → WorkflowResult（best_candidate、all_candidates 已排序、trace=TaskState.logs、errors 记录工具失败说明）
```

说明：

- **Workflow 层**不写 `subprocess`/HTTP；仅通过 **`ToolExecutor`** 按注册名调用 **`agent_core.tools`** 中已有 LangChain `@tool`。
- 若某工具失败，**仍完成排序**：缺少的 MFE 等指标在 `mrna_scoring` 中采用**文档化中性分**（见 `mfe_stability_component`）；GC 可回退到序列本地统计的 `gc_content_local` 思路（bundle 中以 `gc_content` 统一呈现）。

### 涉及文件与复用模块

| 层级 | 路径 | 职责 |
|------|------|------|
| 编排 | `rna_agent_system/agent_core/workflows/mrna_workflow.py` | `MrnaWorkflow`、`MrnaWorkflowInput`、`run_mrna_workflow` |
| 候选 | `rna_agent_system/agent_core/workflows/mrna_candidates.py` | 直接序列 / 小型同义密码子替换 / mock 尾部扩增 |
| 打分 | `rna_agent_system/agent_core/workflows/mrna_scoring.py` | 权重 `MrnaScoreWeights`、GC 峰形、MFE 线性映射、长度目标 |
| 模型 | `rna_agent_system/agent_core/workflow_models.py` | `Candidate`、`TaskState`、`WorkflowResult`、`ToolCallRecord`（trace） |
| 工具 | `rna_agent_system/agent_core/tool_executor.py`、`tool_registry.py` | 默认 `build_default_tool_registry` → `compute_rna_sequence_gc_content` + `predict_rna_secondary_structure_with_linearfold` |
| 落盘 | `rna_agent_system/agent_core/file_manager.py` | `save_sequence` 写 workspace 供工具读路径 |

导出：`rna_agent_system/agent_core/workflows/__init__.py`。

### 扩展方式（UTR / circRNA / intron）

- **统一保留**：候选列表 + **`ToolExecutor.run_tool_for_workflow`** + 独立 **`score_*` 模块** + `WorkflowResult`。
- **替换点**：`MrnaWorkflowInput` 扩展字段；注册不同工具名；新建 `*_scoring.py` 或在本模块增加 `ScoreWeights` 子类。

### 测试

- `rna_agent_system/tests/test_mrna_workflow.py`：桩工具下端到端最佳候选；**双工具失败**仍返回可解释 `errors` + 非空 `best_candidate`。

### 当前能力边界（刻意保持最小）

- **支持**：多序列/单序列输入、少量同义密码子变体、对每条候选调用 **GC + folding（MFE）**、加权总分、排序与 trace。
- **不支持（尚未接入本 workflow）**：UTR/cap/poly(A) 设计、表达量/稳定性深度学习预测、密码子表驱动的完整优化器、并行微服务编排与重试策略。

**下一步最值得接入的工具（建议）**：在保持「filepath 接口」一致的前提下，将 **`analyze_cds_codon_metrics_with_codonw_slim`** 或 **`predict_mrna_stability_with_rnastop`** 作为第三步评估工具挂到同一 `ToolExecutor` 循环中，并把 CAI/稳定性指标并入 `compute_mrna_metric_bundle` 与加权表（扩展 `MrnaScoreWeights` 即可）。

---

### mRNA workflow 可调用的入口（HTTP + CLI）

仓库**没有**统一的「大 Agent FastAPI」（仅有各工具微服务），因此在 **`rna_agent_system/workflow_api/`** 增加了**编排层** FastAPI app，并与 **`rna_agent_system/cli/mrna_workflow.py`** 共用 **`workflow_api/mrna_handler.py`**，避免两套业务逻辑分叉。

#### 组件

| 组件 | 路径 |
|------|------|
| Request/Response Schema | `workflow_api/mrna_schemas.py` — `MrnaWorkflowHttpRequest` / `MrnaWorkflowHttpResponse` |
| 编排函数 | `workflow_api/mrna_handler.py` — `execute_mrna_workflow_http()` |
| FastAPI | `workflow_api/app.py` — `GET /health`、`POST /v1/workflows/mrna/run` |
| CLI | `cli/mrna_workflow.py` |

#### HTTP：请求 / 响应约定

- **POST** `/v1/workflows/mrna/run`，JSON body 对应 **`MrnaWorkflowHttpRequest`**：
  - **必选其一**：非空 **`sequence`**、非空 **`sequences`**、或非空 **`protein`**（互斥）。
  - **`task_type`**：默认 `"mrna"`（占位路由）。
  - **`task_id`**：可选；传入则写入底层 `TaskState.task_id`。
  - **`constraints`**：可选对象；仅 **`MrnaWorkflowInput`** 允许的字段会被合并（另支持 **`lineardesign_service_url`** / **`lineardesign_lambda`**，仅在 **`protein`** 路径用于 LinearDesign）。
  - **`top_k`**：可选；截断返回的 **`candidates`** 列表长度（**`best_candidate`** 仍为全流程最优）。
  - **`debug`**：`true` 时在成功响应中带 **`trace`**（工具调用摘要）；发生内部异常且 `debug=true` 时，`debug_detail` 含 traceback 文本。**默认不向客户端暴露 traceback**。
- **响应**：**`MrnaWorkflowHttpResponse`**：`task_id`、`success`、`task_type`、`best_candidate`（字典）、`candidates`、`summary`、`errors`（校验/编排失败）、`warnings`（工具调用失败条目）、可选 `trace` / `debug_detail`。

非法 JSON 或 Schema 不满足（例如同时提供 `sequence` 与 `protein`）：FastAPI **422**。业务上 workflow 返回 `success=false` 时仍为 **HTTP 200**（便于脚本统一解析 JSON）。

#### CLI

在 **`rna_agent_system`** 目录下：

```bash
python cli/mrna_workflow.py --sequence AUGCAUGCAUGCAU --task-id demo-001 --json
python cli/mrna_workflow.py --sequences AUGCAU,GCAUGCAU --top-k 2
python cli/mrna_workflow.py --protein MKWV --constraints '{"lineardesign_service_url":"http://127.0.0.1:8014/generate/cds"}'
```

失败时进程退出码 **1**。

#### Linux 服务器示例路径与 curl

示例仓库路径：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`。

```bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system

# 安装依赖（若尚未安装 fastapi / uvicorn）
pip install -r requirements.txt

# 启动编排 API（与工具微服务并行；工具服务需另行启动 GC 8020、LinearFold 8015 等）
uvicorn workflow_api.app:app --host 0.0.0.0 --port 8090
```

另一终端示例请求：

```bash
curl -s -X POST "http://127.0.0.1:8090/v1/workflows/mrna/run" \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "AUGCAUGCAUGCAUGCAU",
    "task_id": "job-001",
    "task_type": "mrna",
    "constraints": {
      "gc_service_url": "http://127.0.0.1:8020/gc-content",
      "fold_service_url": "http://127.0.0.1:8015/fold"
    },
    "debug": false
  }'
```

示例返回片段（结构化 JSON；**`summary`** 为简洁 `public_summary`，完整计数见 **`operational_summary`**）：

```json
{
  "task_id": "job-001",
  "success": true,
  "task_type": "mrna",
  "best_candidate": {
    "id": "cand_...",
    "sequence": "AUGCAU...",
    "scores": { "total_score": 0.71, "gc_component": 0.8 }
  },
  "candidates": [...],
  "summary": "task_id=job-001 success=true best_total_score=0.7100 candidates=1 tool_warnings=0",
  "operational_summary": "candidates=1; best_total_score=0.71",
  "artifact_directory": "workspace/workflow_runs/20260421T120000Z_job-001_ab12cd34",
  "result_json_path": "workspace/workflow_runs/.../result.json",
  "errors": [],
  "warnings": []
}
```

若 GC 或 LinearFold 工具失败，**`warnings`** 为非空，`success` 仍可 **`true`**（workflow 仍以本地/中性分完成排序）。

#### 测试

- `rna_agent_system/tests/test_mrna_workflow_api.py`：`execute_mrna_workflow_http` 正常路径、工具失败 warnings、内部异常与 `debug`；FastAPI 422 与桩 registry 联通测试（未安装 **fastapi** 时跳过 HTTP 用例）。
- `rna_agent_system/tests/test_workflow_observability.py`：落盘 `request.json` / `result.json`、失败任务记录、`tool_records` 关键步骤。

---

### Workflow 可观测性与本地结果落盘（最小闭环）

项目侧**已有**：`agent_core/tool_executor.py` 内 **`logging`**（工具调用 INFO）、`workspace/` 下的 **`save_sequence` / `save_text_file`**（工具侧产物）；**未有**统一审计数据库。本次在 **workflow 编排层**增加 **`logging` 日志节点** + **`workspace/workflow_runs/`** 下的 **JSON 落盘**，与工具微服务目录解耦。

#### 日志（标准 logging）

- Logger 名称：**`agent_core.workflows.mrna`**（层级便于后续接入 `UTR`、`circRNA` 等子 logger）。
- 关键 INFO 事件（便于 grep / 聚合实验）：
  - **`mrna_task_start`**：`task_id`、`candidate_mode`、`persist_run`
  - **`mrna_candidates_generated`**：`count`、`source`
  - **`mrna_tool_start` / `mrna_tool_end`**：每个候选 × 每次工具调用（含 `elapsed_s`）
  - **`mrna_scoring_ranking`**：排序所用 `score_key`
  - **`mrna_task_complete`** / **`mrna_task_failed`**：收尾
  - **`workflow_run_persisted`**（在 `workflow_run_storage`）：落盘相对路径

查看方式：进程 **stdout/stderr**（uvicorn / CLI）、或部署侧将 Python logging 接到文件（如 `logging.basicConfig` / `LOGLEVEL=INFO`）。工具层原有 **`agent_core.tool_executor`** 的 `tool invoke start/ok` 日志仍保留。

#### 结果文件位置与命名

- 根目录（相对仓库 **`rna_agent_system/`**）：**`workspace/workflow_runs/`**
- 每次运行新建子目录（UTC 时间戳 + `task_id` slug + 短 uuid）：  
  **`workspace/workflow_runs/<YYYYMMDDTHHMMSSZ>_<task_id_slug>_<8hex>/`**
- 固定文件：
  - **`request.json`**：`schema_version`、`task_id`、`workflow_input`（`MrnaWorkflowInput` dump）、可选 **`http_request_audit`**（HTTP 入口原始 body）
  - **`result.json`**：完整审计（见下）
  - **`artifacts/`**（可选）：从各 **`tool_records[].artifacts`** 中解析到的 **`workspace/...`** 路径文件 **best-effort 拷贝**（上限数量防止爆炸）

关闭落盘：在 **`constraints`** 或 **`MrnaWorkflowInput`** 中设置 **`persist_run`: false**。自定义父目录（测试/笔记本）：**`artifact_runs_parent`** 指向绝对路径或仓库相对路径。

#### `result.json` 字段（`schema_version`: `workflow_run_v1`）

| 字段 | 含义 |
|------|------|
| `task_id`, `success`, `started_at`, `completed_at`, `created_at` | 标识与时间 |
| `public_summary` | 单行摘要（与 API **`summary`** 对齐） |
| `summary` | 运行侧计数摘要（与 API **`operational_summary`** 对齐） |
| `fatal_errors` | 任务级失败（如空候选）；成功运行时为 `[]` |
| `tool_warnings` | 工具调用失败条目；任务失败时为 `[]` |
| `workflow_input` | 完整 workflow 入参 |
| `http_request_audit` | HTTP 入口审计（CLI 为 `null`） |
| `best_candidate`, `candidates` | 完整候选对象 |
| `tool_records` | 全量 **`ToolCallRecord`**（含 `input_summary` / `output_summary` / `artifacts` / `metrics`） |
| `ranking` | `ordered_candidate_ids` 等 |
| `artifact_file_copies` | 拷贝进本 run `artifacts/` 的相对路径列表 |

#### 对外返回 vs 磁盘

- **`WorkflowResult.public_summary`** / HTTP **`summary`**：一行，适合实验表格与论文附录索引。
- **`WorkflowResult.summary`** / HTTP **`operational_summary`**：稍详细的计数字符串。
- **完整 trace**：在内存 **`WorkflowResult.trace`** 与磁盘 **`result.json`** 的 **`tool_records`**；HTTP 仅在 **`debug=true`** 时返回裁剪版 **`trace`**。

#### 批量实验扩展建议

- 为每条任务传入稳定 **`task_id`**（实验因子编码），结果目录可按 **`task_id` grep** 或通过 **`result.json`** 聚合。
- 外层脚本并行调用 CLI/API，统一收集 **`workspace/workflow_runs/*/result.json`**；后续若需 SQLite/TSV，只需扫描该目录_tree，无需改 workflow 内核。

---

## 如何运行测试

在仓库 **`rna_agent_system/`** 目录下执行（依赖见 **`requirements.txt`**）：

```bash
cd /path/to/RNA_real_agent/rna_agent_system
pip install -r requirements.txt

# 默认：全部单元 / 契约 / mock 路径（不向微服务发起真实 HTTP）
python -m pytest -q

# 仅跳过需要本机微服务的用例（推荐 CI）
python -m pytest -q -m "not integration"

# 含 FastAPI HTTP 路由测试需安装 fastapi（已在 requirements.txt）
```

**集成 / 活体**：标记为 **`@pytest.mark.integration`** 的用例会访问本机端口（例如 GC 服务的 **8020**）；若服务未启动会自动 **skip**。显式运行：

```bash
python -m pytest -q -m integration
```

配置文件：**`rna_agent_system/pytest.ini`**（定义 `integration` marker 与 `tests/` 路径）。

---

## 当前评估基线覆盖范围（盘点）

下列为 **已有 + 本轮补齐** 的测试分层说明，目标是：加工具 / workflow 时不破坏最小闭环。

### 已有测试（入库前）

| 类别 | 文件 | 说明 |
|------|------|------|
| 工具运行时 | `tests/test_tool_runtime.py` | `PythonFunctionTool` / `CommandLineTool` / 超时与退出码 |
| Registry / Executor | `tests/test_tool_registry_executor.py` | 注册、缺名错误、`run_tool` / `run_tool_for_workflow` |
| 工具契约 | `tests/test_tool_specs_output_models.py` | 规格与输出模型 |
| Vienna 封装 | `tests/test_viennarna_wrapper_output.py` | 输出形状 |
| GC workflow | `tests/test_rna_gc_content_workflow.py` | **mock HTTP** + 可选 **`integration`** 活体 |
| 数据模型 | `tests/test_workflow_models.py` | `Candidate` / `TaskState` / 排序 |

### 本轮补齐 / 强化

| 类别 | 文件 | 说明 |
|------|------|------|
| mRNA workflow（mock 工具） | `tests/test_mrna_workflow.py` | 端到端排序、双工具全失败退化 |
| mRNA 可观测 / 落盘 | `tests/test_workflow_observability.py` | `request.json` / `result.json`、`tool_records` |
| HTTP 入口 | `tests/test_mrna_workflow_api.py` | `execute_mrna_workflow_http`、422、FastAPI（无 fastapi 则跳过） |
| **基线数据集 + 评估** | `tests/test_workflow_baseline_eval.py` | 读取 **`examples/data/mrna_baseline_samples.json`**、批量得分、双候选排序、**示例脚本 subprocess** |
| **CLI 入口** | `tests/test_cli_mrna_entry.py` | `cli/mrna_workflow.py --json` |
| **Registry 集成烟测** | `tests/test_integration_registry_smoke.py` | 默认 registry 含核心 mRNA 工具名（无 HTTP） |

### 共享桩与示例数据（避免重复实现）

- **`agent_core/workflow_baseline_eval.py`**：`StubGcTool` / `StubFoldTool`、`run_baseline_batch`、`evaluate_sample`（测试与 **`examples/mrna_workflow_batch_demo.py`** 共用）。
- **`examples/data/mrna_baseline_samples.json`**：3 条序列 + 备注，用于回归对比得分。

### 批量演示脚本

```bash
cd rna_agent_system
python examples/mrna_workflow_batch_demo.py
python examples/mrna_workflow_batch_demo.py --json
```

---

## 最小能力边界（基线共识）

在当前测试基线通过的前提下，系统**保证**：

- **工具抽象层**：`ToolResult`、Python/CLI 可执行工具、超时与非零退出码行为可预期。
- **Registry / Executor**：按名调度、未注册工具返回标准化失败、workflow 侧写入 **Candidate / TaskState** trace。
- **Workflow 模型**：候选排序、`WorkflowResult` 与 JSON 序列化一致。
- **mRNA 最小闭环**（**桩 GC + 桩 LinearFold**）：候选生成 → 打分 → 排序 → `public_summary`；工具全挂时仍可排序；可选落盘 JSON。
- **入口**：HTTP（`workflow_api`）与 CLI 在 **`persist_run: false`** 下可在无微服务环境跑通；**HTTP 测试**依赖 **fastapi** 可选安装。

**不保证**（需 `integration` 或真实部署）：各微服务端口在线、LLM key、GPU、Streamlit 全链路。后续新增工具时，请至少补充：**registry 烟测**（若注册新名）+ **对应 workflow 单测（mock）** + 必要时 **integration** 一条。

---

## 多 RNA 任务扩展路线（轻量骨架）

设计原则：**不引入 planner / 多 agent 编排 / DSL**；仅在现有「候选 → `ToolExecutor` → 打分 → `WorkflowResult`」之上增加 **task_type 分发** 与 **约定文档**，便于接入 5′UTR、3′UTR、circRNA、IRES、Intron 等。

### 已实现层次（当前仓库）

| 层次 | 位置 | 说明 |
|------|------|------|
| 工具调用 | `agent_core/tool_executor.py` + LangChain `@tool` | 统一 **按名 `invoke`**，与具体 RNA 任务解耦 |
| 数据模型 | `agent_core/workflow_models.py` | **`Candidate`** / **`TaskState`** / **`WorkflowResult`** 已通用 |
| mRNA 专用 | `agent_core/workflows/mrna_*.py` | 候选生成、**`mrna_scoring`**、**`MrnaWorkflow`** |
| 任务分发 | **`agent_core/workflow_dispatch.py`** | **`normalize_task_type`**、**`classify_task_type`**、**`KNOWN_TASK_TYPES`**（**`IMPLEMENTED_TASK_TYPES`** / **`PLACEHOLDER_TASK_TYPES`**） |
| 打分扩展点 | **`agent_core/workflow_scoring_protocol.py`** | 可选 **`RnaWorkflowScorer`** Protocol；mRNA 仍以函数实现，无需强制实现 Protocol |
| HTTP | **`workflow_api/app.py`** | **`POST /v1/workflows/mrna/run`**（仅 **mrna**，非 mrna → **422**）；**`POST /v1/workflows/run`**（统一入口，按 **task_type** 分发） |
| 统一编排 | **`workflow_api/rna_unified_handler.py`** | **`execute_rna_workflow_http`**：仅 **mrna** 走现有逻辑；占位类型返回 **`success=false`** + 明确 **errors**；未知类型返回 **`dispatch_error:unknown_task_type`** |

### 约定（最小）

**输入（HTTP）**

- 共用 **`MrnaWorkflowHttpRequest`**（别名 **`RnaWorkflowHttpRequest`**）：**`sequence` / `sequences` / `protein`** 三选一 + **`task_type`** + **`constraints`**（自由 JSON，由各 workflow 的 Pydantic 输入模型自行消化）。
- **`constraints`**：建议各子 workflow 用独立 **Input** 模型文档化字段（同 mRNA 的 **`MrnaWorkflowInput`**），避免未定义键默默丢失。

**输出**

- 内存：**`WorkflowResult`**（**`public_summary`**、**`trace`**、**`errors`** 等）。
- HTTP： **`MrnaWorkflowHttpResponse`**（别名 **`RnaWorkflowHttpResponse`**），字段 **`summary`**（对外短句）、**`operational_summary`**、路径字段等。

**`Candidate` 推荐字段**

| 位置 | 推荐 |
|------|------|
| **`sequence_type`** | **`mrna`** / **`utr5`** / **`utr3`** / **`circrna`** / **`ires`** / **`intron`**（与 **task_type** 对齐） |
| **`metadata`** | **`workflow`**（如 **`mrna_ranking_minimal`**）、**`workspace_filepath`**、任务特有键（如 **`ires_window`**，后续按需） |
| **`scores`** | 至少 **`total_score`**；可加领域分量（如 **`gc_component`**），命名保持 **snake_case** |

**工具接入**

- 在 **`agent_core/tools.py`** 注册 **`@tool`**，加入 **`ALL_LANGCHAIN_AGENT_TOOLS`** 对应分组。
- Workflow 内只通过 **`ToolExecutor.run_tool` / `run_tool_for_workflow`** 调用；**不写裸 HTTP/subprocess**。

### 下一步最推荐优先支持的两个任务（建议）

1. **IRES（或 IRES 区域评估）**  
   - **原因**：仓库 **`agent_core/tools.py`** 中已有 **`predict_putative_ires_with_iresfinder`**，接入 **registry → 新 workflow** 的路径最短，适合做第二个闭环验证。
2. **5′UTR**  
   - **原因**：与现有 **mRNA CDS** 设计在同一转录本叙事下衔接自然；仓库 **`external_repos/GEMORNA`** 等已有 UTR 相关脚本可参考，便于定义 **`Utr5WorkflowInput`** 与候选结构。

（若优先「完整表达框」而非 IRES，可将 **3′UTR** 与 **5′UTR** 成对排期；本文档按「最短工具链验证 + 最常见调控区」排序。）

### API 路由备忘

| 路由 | 行为 |
|------|------|
| **`POST /v1/workflows/mrna/run`** | 强制 **mrna**（**`task_type`** 若非 mrna → **422**） |
| **`POST /v1/workflows/run`** | **`task_type=mrna`** 运行现有逻辑；占位类型返回结构化 **not implemented**；未知类型返回 **`unknown task_type`** |

---

### 新增 5′UTR workflow 时最少新增哪些文件（参考）

不设硬性文件名，最小增量通常为：

1. **`agent_core/workflows/utr5_workflow.py`**（或 **`utr5/`** 包）：**`Utr5WorkflowInput`**、`run_utr5_workflow` → **`WorkflowResult`**。  
2. **`agent_core/workflows/utr5_candidates.py`**（可选，若候选生成与 mRNA 不同）。  
3. **`agent_core/workflows/utr5_scoring.py`**（可选，打分规则独立时）。  
4. 修改 **`agent_core/workflow_dispatch.py`**：把 **`utr5`** 从 **`PLACEHOLDER_TASK_TYPES`** 移到 **`IMPLEMENTED_TASK_TYPES`**，并在 **`workflow_api/rna_unified_handler.py`** 增加 **`elif canonical == "utr5": return run_utr5_workflow_http(...)`**（或等价分支）。  
5. **测试**：**`tests/test_utr5_workflow.py`**（stub 工具）+ dispatcher 一条。  

工具侧若沿用现有 **`@tool`**，仅需保证名称在 **`ToolRegistry`** 内可查。
