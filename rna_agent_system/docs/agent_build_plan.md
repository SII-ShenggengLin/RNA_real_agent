# RNA Agent 实施方案（贴合当前仓库）

## 1) 当前项目结构简析

本仓库已经具备“可运行的规则式多智能体 + 微服务工具层”基础，不是从零开始。

- `rna_agent_system/agent_core/`
  - `graph.py`：LangGraph 主流程（Router -> Specialist -> Tool -> Critic）
  - `nodes.py`：路由、任务识别、工具分发、fallback、critic 判定
  - `tools.py`：LangChain `@tool` 封装，统一通过 HTTP 调用本地微服务
  - `tool_specs.py` + `tool_interface.py`：工具规格/输入输出 schema（Pydantic）
  - `state.py`：AgentState 状态字段定义
  - `file_manager.py`：`workspace/` 文件中转（避免长序列直接进 prompt）
- `rna_agent_system/microservices/*_service/`
  - 19 个 FastAPI 服务，基本都采用 `main.py + environment.yml + start.sh` 结构
  - 各服务直接包装 `external_repos` 中的上游工具或模型
- `rna_agent_system/external_repos/`
  - 通过 submodule 管理第三方算法仓库（RNASTOP/RNARL/GEMORNA/ViennaRNA 等）
- `rna_agent_system/frontend/app.py`
  - Streamlit 前端入口，直接调用 `compiled_graph`
- `rna_agent_system/tests/`
  - 目前以 tool spec 与 wrapper 基础契约测试为主
- `docs/`（仓库根）+ `rna_agent_system/docs/`
  - 已有任务/工具/workflow 文档体系，`RNA_AGENT_SYSTEM_GUIDE.md` 说明较完整

结论：当前是“规则驱动编排 + 微服务工具调用”的成熟骨架，下一步应在现有抽象上增量实现，不建议重构目录或替换主流程。

## 2) 已有能力与可复用点

### 后端入口现状

- Agent 主入口：`rna_agent_system/frontend/app.py`（Streamlit 调 `agent_core.graph.compiled_graph`）
- 工作流主入口：`rna_agent_system/agent_core/graph.py`
- 工具执行入口：`rna_agent_system/agent_core/tools.py`
- 微服务入口：`rna_agent_system/microservices/*_service/main.py`（FastAPI）
- 未发现统一 Flask 入口；CLI 主要是各服务 `start.sh` 启动脚本

### 工具组织方式

- 上游算法仓库放在 `external_repos/`
- 每个工具有独立微服务（端口隔离、环境隔离）
- Agent 层不直接 import 上游仓库，统一 HTTP 调用（`tools.py`）
- 工具 contract 由 `tool_specs.py` 管理（这点非常值得复用）

### 目录抽象对应关系

- `task`：`docs/tasks/`
- `tool`：`docs/tools/`
- `workflow`：`docs/workflows/`
- `agent`：`agent_core/`
- `service`：`microservices/*_service/`
- `router`：在 `agent_core/nodes.py` 中（函数级，不是目录级）
- `schema`：在 `agent_core/tools.py` 输入模型 + `agent_core/tool_specs.py` 输出模型

### 配置、环境变量、日志、测试

- 依赖/环境：
  - Agent：`rna_agent_system/requirements.txt`
  - 每个服务：`rna_agent_system/microservices/*_service/environment.yml`
- 环境变量：
  - LLM 相关：`agent_core/llm_config.py`（`load_dotenv()`，当前规则模式基本未启用）
  - 服务内变量：如 `RNARL_DEVICE`、`RNASTOP_DEVICE`、`LINEARDESIGN_ROOT` 等（分散在各 `main.py`）
- 日志：
  - 目前仓库内未形成统一日志模块（多数服务依赖异常返回/stdout）
  - `external_repos` 中有各自 logger，不建议上层侵入
- 测试：
  - `rna_agent_system/tests/`（wrapper/spec 为主）

### RNA/mRNA/codon/folding/evaluation 相关代码

已大量存在，尤其在：
- mRNA 设计：`design_mrna_cds_with_gemorna` / `design_mrna_cds_with_rnarl` / `design_mrna_cds_with_lineardesign`
- 折叠：`predict_rna_secondary_structure` / `predict_rna_secondary_structure_with_linearfold` / `predict_rna_local_accessibility_profile_vienna`
- 评估：`predict_mrna_stability_with_rnastop` / `analyze_cds_codon_metrics_with_codonw_slim` / `compute_rna_sequence_gc_content`
- 路由与编排：`agent_core/nodes.py` 中 `mrna_specialist_node` 和 `tool_execution_node`

## 3) 智能体系统最小闭环设计（优先 mRNA）

建议先做一个“可验证、可回归”的 mRNA 最小闭环，不增加新服务：

1. 输入：蛋白序列或 mRNA 序列（自然语言 + 文件路径）
2. 设计：复用已有 CDS 工具（先固定一种，建议 `lineardesign` 或 `gemorna`）
3. 评估：串联已有评估工具（至少 2 项）
   - `analyze_cds_codon_metrics_with_codonw_slim`
   - `predict_rna_secondary_structure`（或 `linearfold`）
   - 可选：`predict_mrna_stability_with_rnastop`
4. 输出：统一报告（关键指标 + 产物路径 + 下一步建议）
5. 验收：补齐对应测试与文档，前端能稳定触发

这个闭环完全复用现有架构，风险最低。

## 4) 推荐先实现的第一个任务（mRNA 设计）

任务名建议：`mrna_design_min_loop`

### 任务目标

给定蛋白序列，输出候选 CDS，并返回至少以下指标：
- CAI/ENC/FOP/CBI（codonw-slim）
- 二级结构与 MFE（ViennaRNA 或 LinearFold）
- （可选）稳定性预测（RNASTOP）

### 为何先做它

- 现有工具覆盖最完整，几乎不需要新增底层算法
- `nodes.py` 已有 mRNA 分支，可做小步增强
- 验收标准清晰（路径、指标、可重复测试）

## 5) 建议新增模块/文件与放置目录

以下为“增量增强”建议（避免大改）：

1. `rna_agent_system/agent_core/reporting.py`（新增）
   - 统一格式化 mRNA 任务输出（从 `state` 中组装更可读的报告）
2. `rna_agent_system/tests/test_mrna_min_loop.py`（新增）
   - mRNA 闭环回归测试（可 mock HTTP）
3. `docs/tasks/mrna_design_min_loop.md`（新增）
   - 新任务定义与输入输出样例
4. `docs/workflows/mrna_design_min_loop_workflow.md`（新增）
   - 任务执行链路（design -> evaluate -> report）
5. `docs/tools/` 下按需补文档（可选）
   - 若只复用现有工具，可不新增

可选小改（尽量少）：
- `rna_agent_system/agent_core/nodes.py`
  - 在 `mrna_specialist_node` 中增加一个“最小闭环专用触发词/模式”
  - 避免改动全局路由策略与已有工具名

## 6) 可复用模块 vs 尽量避免改动处

### 优先复用

- `agent_core/tools.py`：已有 HTTP wrapper 和输入模型
- `agent_core/tool_specs.py`：已有规范化输出 contract
- `agent_core/file_manager.py`：统一文件中转
- `agent_core/nodes.py` 中 mRNA 已有分支逻辑
- `microservices/*`：先不新增服务，直接复用

### 尽量避免改动

- `microservices/*_service/main.py` 的核心推理流程（稳定优先）
- `external_repos/*`（submodule 上游代码）
- `tool_specs.py` 中已上线工具 identity（避免破坏兼容）
- `frontend/app.py` 的主调用链（除非要增加展示字段）

## 7) 分步骤开发计划（含文件路径）

### Step 0：冻结边界（不写新算法）

- 明确先复用：
  - `design_mrna_cds_with_lineardesign` 或 `design_mrna_cds_with_gemorna`
  - `analyze_cds_codon_metrics_with_codonw_slim`
  - `predict_rna_secondary_structure`（可切 `linearfold`）
- 涉及文件：
  - `rna_agent_system/agent_core/nodes.py`
  - `rna_agent_system/agent_core/tools.py`

### Step 1：实现统一报告层（最小改动）

- 新增 `rna_agent_system/agent_core/reporting.py`
  - 提供 `build_mrna_min_report(state)` 之类函数
- 在 `critic_node` pass 分支中调用报告构造（或在 `tool_execution_node` 尾部构造）
- 涉及文件：
  - `rna_agent_system/agent_core/reporting.py`（新增）
  - `rna_agent_system/agent_core/nodes.py`（小改）

### Step 2：增加 mRNA 最小闭环触发模式

- 在 `mrna_specialist_node` 添加明确关键词（如 `mrna_min_loop`）
- 使其固定执行“设计 + 指标 + 折叠”三步
- 涉及文件：
  - `rna_agent_system/agent_core/nodes.py`

### Step 3：补测试

- 新增针对最小闭环的单测（mock 微服务返回）
- 验证：
  - 工具调用顺序
  - `state` 关键字段落盘
  - 报告字段完整
- 涉及文件：
  - `rna_agent_system/tests/test_mrna_min_loop.py`（新增）
  - `rna_agent_system/tests/conftest.py`（必要时小改）

### Step 4：补文档与验收脚本

- 新增任务与 workflow 文档
- 在 `docs/tasks/INDEX.md`、`docs/workflows/INDEX.md` 增加索引（如已有规范）
- 涉及文件：
  - `docs/tasks/mrna_design_min_loop.md`（新增）
  - `docs/workflows/mrna_design_min_loop_workflow.md`（新增）
  - `docs/tasks/INDEX.md`（小改）
  - `docs/workflows/INDEX.md`（小改）

## 8) 命名冲突与兼容性注意事项

1. 不要新建与现有 tool identity 冲突的名称  
   例如已有 `design_mrna_cds_with_*`、`predict_rna_secondary_structure`，新流程建议用任务名，不新造同义工具名。

2. `nodes.py` 已较大，新增逻辑请“局部插入”  
   建议提取少量 helper 到新文件（如 `reporting.py`），避免继续把所有逻辑塞进 `nodes.py`。

3. 兼容已有 rule-based 默认行为  
   默认路由目前偏向 mRNA，新增闭环触发词应为“显式模式”，不要改变现有关键词语义。

4. 继续遵循文件路径输入约束  
   长序列应继续通过 `workspace/` 文件传递，不要改成直接在消息中传递全量序列。

5. 保持 submodule 边界  
   功能增强优先在 `agent_core` 和文档层完成，不在 `external_repos` 改上游源码。

## 9) 当前建议的开发顺序（最合理）

1. 先实现报告层（低风险、高收益）
2. 再加 mRNA 最小闭环触发规则
3. 再补测试保障回归
4. 最后补文档与索引

这个顺序可以确保每一步都有可见产出，且不需要先碰高风险的模型服务代码。

## 10) 扫描得到的关键目录树（精简）

```text
RNA_real_agent/
├── docs/
│   ├── tasks/
│   ├── tools/
│   └── workflows/
└── rna_agent_system/
    ├── agent_core/
    │   ├── graph.py
    │   ├── nodes.py
    │   ├── tools.py
    │   ├── tool_specs.py
    │   ├── state.py
    │   ├── workflow_models.py
    │   └── file_manager.py
    ├── frontend/
    │   └── app.py
    ├── microservices/
    │   ├── viennarna_fold/
    │   ├── lineardesign_service/
    │   ├── rnarl_service/
    │   ├── gemorna_service/
    │   ├── rnastop_service/
    │   ├── codonw_slim_service/
    │   └── ... (其余服务)
    ├── external_repos/
    ├── tests/
    ├── workspace/
    └── docs/
```

## 11) 建议新增/修改文件清单（执行时）

建议新增：
- `rna_agent_system/agent_core/reporting.py`
- `rna_agent_system/tests/test_mrna_min_loop.py`
- `docs/tasks/mrna_design_min_loop.md`
- `docs/workflows/mrna_design_min_loop_workflow.md`

建议小改：
- `rna_agent_system/agent_core/nodes.py`
- `docs/tasks/INDEX.md`
- `docs/workflows/INDEX.md`

本次实际已新增：
- `rna_agent_system/docs/agent_build_plan.md`

---

## 12) Agent 工作流数据模型（候选 → 评估 → 排序 → 迭代）

### 与现有结构的关系

- **`agent_core/state.py` 的 `AgentState`**：`TypedDict`，用于 LangGraph 节点间传递当前请求的扁平运行时字段，不适合承载多候选集合与完整 trace。
- **`agent_core/workflow_models.py`**：**Pydantic** 模型，承载候选集、工具调用记录、任务状态与最终结果；可 **`model_dump(mode="json")`** 序列化，无 ORM 耦合。

### 各对象职责

| 对象 | 职责 |
|------|------|
| **`Candidate`** | 候选序列：`id`、`sequence`、`sequence_type`、`source`、`scores`、`metadata`、`tool_records`、`rank`、`status`、时间戳；**`add_tool_record()`** 追加工具记录。 |
| **`ToolCallRecord`**（**`StepRecord`** 别名） | 单次工具调用：`step_name`、`tool_name`、`input_summary`、`output_summary`、`success`、`error`、`elapsed_time`、`artifacts`、`metrics`。 |
| **`TaskState`** | 任务会话：`task_id`、`task_type`、`input_payload`、`constraints`、`candidates`、`best_candidate`、`iteration_index`、`messages`、`logs`、`status`；**`update_best_candidate(score_key)`** 按分数更新最优候选。 |
| **`WorkflowResult`** | 结束快照：`success`、`task_id`、`best_candidate`、`all_candidates`、`summary`、`errors`、`trace`。 |

### 辅助函数

- **`sort_candidates_by_score`**：按 `scores` 某键排序；缺键候选置后；有序部分写入 **`rank`**。

### 文件与测试

- 实现：`rna_agent_system/agent_core/workflow_models.py`
- 导出：`rna_agent_system/agent_core/__init__.py`
- 测试：`rna_agent_system/tests/test_workflow_models.py`

---

## 13) Tool Registry + Executor

与 `docs/agent_build_plan.md`（仓库根）中 **「Tool Registry + Executor」** 章节内容一致，说明略。实现位置：

- `rna_agent_system/agent_core/tool_registry.py` — `ToolRegistry`，`ToolNotRegisteredError`
- `rna_agent_system/agent_core/tool_executor.py` — `ToolExecutor`，`build_default_tool_registry`
- `rna_agent_system/agent_core/tools.py` — `ALL_LANGCHAIN_AGENT_TOOLS`（与 `nodes.TOOLS` 同源），可选 `workflow_demo_echo` 用于 demo
- 测试：`rna_agent_system/tests/test_tool_registry_executor.py`

**建议 import**：`from agent_core.tool_executor import ToolExecutor, build_default_tool_registry`（避免在 `import agent_core` 时整表加载 `tools.py`）。

---

## 14) 第一个 workflow 真实工具：RNA GC（`workflow_rna_gc_content`）

见仓库根 `docs/agent_build_plan.md` 中同节。实现目录：

- `agent_core/workflow_tools/rna_gc_content_workflow.py`
- 示例：`rna_agent_system/examples/workflow_gc_content_demo.py`
- 测试：`rna_agent_system/tests/test_rna_gc_content_workflow.py`

微服务：`microservices/rna_sequence_metrics_service/`，端口 **8020**。
