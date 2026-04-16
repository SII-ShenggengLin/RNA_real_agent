# 任务：`sirna_duplex_energy`

## 任务目标

给定一对 siRNA 的 sense/antisense 链，计算 duplex 共折叠结构与结合能（MFE，kcal/mol），用于过滤/排序。

## 适用输入

- 两条链：
  - 两条 FASTA 记录（第一条 sense，第二条 antisense），或
  - 两行纯序列（第一行 sense，第二行 antisense）

## 输出结果

- `structure`（dot-bracket，含 `&`）
- `mfe_kcal_per_mol`（kcal/mol，越小越稳定）

## 前置条件

- ViennaRNA 微服务可用：`microservices/viennarna_fold`（端口 8003）

## 使用到的工具

- `compute_sirna_duplex_binding_vienna`（见 `docs/tools/compute_sirna_duplex_binding_vienna.md`）

## 标准工具链步骤

见 `docs/workflows/sirna_duplex_energy_workflow.md`。

## 当前限制

- 不提供 siRNA efficacy 预测与生产级脱靶评估（相关 mock 已移除）

## 不支持的情形

- 只给出单条链（无法构建 duplex）

## 示例调用入口

- UI：`rna_agent_system/frontend/app.py`（自然语言包含 duplex/cofold 语义）
- Workflow：`agent_core/nodes.py` → `sirna_specialist_node`（duplex 关键词）

