# 增强设计提案（不发明新算法，工程可落地）

> 核心原则：结果仍来自现有工具；增强来自**更严格的约束、更稳的编排、更可审计的整合、更可恢复的失败处理**。

---

## 提案 1：统一“任务路由 + 工具选择约束”（基于 `ToolSpec.task_tags`）

### 当前问题

- Router/Specialist 主要靠关键词；工具集合是静态列表，缺少“能力边界”约束。
- 删除 siRNA mock 后，仍可能出现“路由到 siRNA 但无可执行工具”的边缘情况（已部分修复，但缺少体系化约束）。

### 设计思路

- 建立一个**任务枚举**（与 `docs/tasks/` 对齐）。
- Router 输出 `task_id` 而不是“specialist 名称”，并依据 `TOOL_SPECS`：
  - 只允许选择 `status != mock` 的工具
  - 只允许选择 `task_tags` 覆盖该任务的工具
- Specialist 只做**确定性工具链编排**（见 `docs/workflows/`），不做自由选工具。

### 作用任务

- 全部任务（尤其是 siRNA、CRISPR、mRNA 多工具分支）

### 实现位置（建议）

- 新增：`rna_agent_system/agent_core/task_router.py`
- 调整：`rna_agent_system/agent_core/nodes.py:router_node`（从 route→task）
- 约束来源：`rna_agent_system/agent_core/tool_specs.py:TOOL_SPECS`

### 风险

- 需要在代码层维护 task 与 workflow 的一致性（但这是“可审计”的成本）。

### 预期收益（来源可解释）

- **收益来源**：减少错误路由与越权工具调用（例如把 BLAST 当成 siRNA 脱靶评估）、减少“无工具可跑”的失败。
- **代价**：需要维护 task/工具标签，新增少量样板代码。

### 如何 benchmark/验证

- 以固定测试输入集（任务关键词覆盖）验证 Router 输出 task_id 的稳定性与合法性；
- 验证每个 task 的工具链步骤都能在 `TOOLS_BY_NAME` 中解析到工具对象。

---

## 提案 2：严格输入校验与参数校验（工具前置 Validator）

### 当前问题

- 校验逻辑分散在 wrapper 内（例如 CRISOT 23nt 校验）或服务端；错误信息不统一。

### 设计思路

- 在 tool_execution 前增加 validator：
  - workspace 文件存在/可读
  - 序列字母表与长度约束（按任务/工具定义）
  - 互斥字段（例如 BLAST subject 二选一）
- 校验失败时返回**结构化、可恢复的错误**（例如“缺 sense/antisense”→提示补齐输入）。

### 作用任务

- `sirna_duplex_energy`（双链校验）
- `blastn_similarity_search`（互斥字段/路径）
- `crispr_*`（23nt 与字母表）
- `aso_accessibility_viennarna`（region 合法性）

### 实现位置（建议）

- 新增：`rna_agent_system/agent_core/validators.py`
- 调整：`rna_agent_system/agent_core/nodes.py:tool_execution_node`

### 风险

- 校验规则过严会拒绝“边缘但可运行”的输入；需要明确范围并给出修复建议。

### 预期收益（来源可解释）

- **收益来源**：减少服务端/工具执行失败与不必要重试，提高失败可诊断性。

### 如何 benchmark/验证

- 单元测试覆盖典型非法输入（空文件、长度不符、互斥字段同时给等）。

---

## 提案 3：输出标准化与结果整合（统一 MFE/结构字段）

### 当前问题

- 工具输出类型不一致（例如 Vienna fold 返回拼接字符串，Linearfold 返回 dict）。
- 下游 state 写回需要正则解析字符串（脆弱，不可审计）。

### 设计思路

- 将关键工具输出统一为 dict 并对齐字段名/单位：
  - Vienna fold：`mfe_kcal_per_mol` + `structure`
  - Linearfold：保持 `mfe`，同时在 state 层映射成统一字段（例如 `mfe` 统一存 state）
- 结合 `ToolSpec.output_model` 做最小字段验证。

### 作用任务

- `rna_secondary_structure_viennarna`
- `rna_secondary_structure_linearfold`
- 依赖 MFE 的 critic 逻辑

### 实现位置（建议）

- 调整：`rna_agent_system/agent_core/tools.py:predict_rna_secondary_structure`
- 调整：`rna_agent_system/agent_core/nodes.py`（写回 `state["mfe"]` 的逻辑）

### 风险

- 需要同步调整 UI/最终报告字段；但这是可控改动。

### 预期收益（来源可解释）

- **收益来源**：减少解析失败，提升状态写回的确定性与可审计性。

### 如何 benchmark/验证

- 单元测试：对模拟返回 payload 校验 `ToolSpec.output_model`；
- 端到端：跑一次 fold 路径，确认 `state["mfe"]` 被正确写入。

---

## 提案 4：失败恢复与 fallback（“工具失败”与“输入不完整”的确定性恢复）

### 当前问题

- 当前重试机制主要是 critic 阈值触发 retry，且 mRNA MFE 阈值对短序列不合理（已在指南中指出）。
- 工具失败（HTTP 超时/缺依赖）时缺少确定性 fallback（例如 Vienna 不可用时改用 Linearfold）。

### 设计思路

- 对关键任务增加“工具失败 fallback”：
  - Vienna fold 失败 → 自动尝试 Linearfold fold（若可用）
  - duplex 输入不完整 → 明确提示需要两条链，而不是尝试无关工具
- 将 fallback 规则写入 workflow 文档并在代码中实现。

### 作用任务

- `rna_secondary_structure_viennarna`
- `sirna_duplex_energy`

### 实现位置（建议）

- 调整：`rna_agent_system/agent_core/nodes.py:tool_execution_node`（捕获 ValueError 并按规则 fallback）

### 风险

- fallback 会增加一次额外调用，带来耗时；需明确只在失败时触发。

### 预期收益（来源可解释）

- **收益来源**：减少“单点工具不可用导致任务完全失败”，提高完成率与可诊断性。

### 如何 benchmark/验证

- 在测试中模拟 Vienna 返回错误，验证 fallback 会调用 Linearfold 并写回 `state["mfe"]`。

