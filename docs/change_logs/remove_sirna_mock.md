# 变更记录：移除 siRNA 相关两个 mock（按代码为准）

## 1. 被删除的两个 mock 的准确定义

本次移除的“两个 siRNA mock”指：

1. **Mock siRNA efficiency**：
   - 微服务：`rna_agent_system/microservices/sirna_attsioff/`（历史端口 8001，`POST /predict`）
   - Agent 工具：`rna_agent_system/agent_core/tools.py` 中的 `predict_sirna_efficiency`（已删除）
2. **Mock off-target check**：
   - 微服务：`rna_agent_system/microservices/off_target_blast/`（历史端口 8002，`POST /check`）
   - Agent 工具：`rna_agent_system/agent_core/tools.py` 中的 `check_off_target`（已删除）

两者均为 FastAPI 返回随机/伪造结果的占位实现（详见审计文档 `docs/audit/sirna_audit.md`）。

---

## 2. 删除文件清单

### 2.1 删除

- `rna_agent_system/microservices/sirna_attsioff/`（目录整体删除）
- `rna_agent_system/microservices/off_target_blast/`（目录整体删除）

### 2.2 修改（去除入口/引用/宣称）

- `rna_agent_system/agent_core/tools.py`
  - 删除 `SirnaEfficiencyInput` / `OffTargetCheckInput`
  - 删除 `predict_sirna_efficiency` / `check_off_target`
- `rna_agent_system/agent_core/nodes.py`
  - 从 import 与 `SIRNA_TOOLS` registry 中移除上述两个工具
  - `sirna_specialist_node` 默认 siRNA 分支改为明确返回“不支持”
  - `tool_execution_node` 移除 mock 工具的 fallback 与解析写回
  - Router 收紧：仅 duplex / Evitar 才进入 siRNA 分支；其余 siRNA/off-target 请求直接判定不支持并结束
  - Critic 移除基于 `off_target_genes` 的 reject 规则（因为其来源已移除）
- `rna_agent_system/agent_core/state.py`
  - 从 `AgentState` 移除 `efficiency_score` / `off_target_genes`
  - 默认 `current_task` 从 `sirna_design` 改为 `mrna_design`
- `rna_agent_system/frontend/app.py`
  - 移除对 `efficiency_score/off_target_genes` 的 UI 展示
- `rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md`
  - 从端口表移除 8001/8002
  - 将“Mock 服务 (8001/8002)”更新为“已移除”，避免继续宣称存在该能力

---

## 3. 影响范围

- **被移除能力**：
  - siRNA efficiency 预测（mock）
  - siRNA 脱靶计数（mock）
- **保留的 siRNA 相关子能力**（非 mock）：
  - ViennaRNA duplex 能量（`compute_sirna_duplex_binding_vienna`）
  - Evitar siRNA/Cas13 设计（`design_sirna_with_evitar`，但仅 Linux 可闭环）

---

## 4. 删除后替代策略

- 本仓库当前**不支持**：
  - siRNA efficiency 真实预测
  - siRNA 脱靶的生产级评估（需要真实 BLAST/数据库/基因组与严格定义的 pipeline）
- 后续若需要恢复上述能力：
  - 必须引入真实实现，并以“严格工具接口规范（输入/输出/error schema + 能力边界）”形式接入，而不是再用随机值 mock 维持入口。

---

## 5. 删除后校验（本次实际执行/可复现）

### 5.1 残留引用搜索

- 搜索关键词：`sirna_attsioff` / `off_target_blast` / `predict_sirna_efficiency` / `check_off_target`
- 预期：仅出现在审计/变更文档等历史记录中，不应存在于可执行代码路径。

### 5.2 编译/静态检查（仅本项目代码，不含 external_repos）

- 命令：`python3 -m compileall rna_agent_system/agent_core rna_agent_system/frontend rna_agent_system/microservices`
- 预期：返回成功（0）。

