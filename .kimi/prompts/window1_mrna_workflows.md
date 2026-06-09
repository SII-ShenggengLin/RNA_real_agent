# 窗口1：mRNA 核心 Workflow — Layer 4/5 全面检查

## 项目背景
- 工作目录：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system`
- 架构：五层架构（Layer 0~5），Layer 3 为 DeepSeek 驱动的 LLMPlanner
- Layer 4 = `SessionMemory` + `WorkspaceManager`（状态持久化）
- Layer 5 = `AgentRunner` + CLI (`cli/`) + FastAPI (`workflow_api/`)
- 当前 Layer 0/1/2/3 已全部测试通过

## 本次检查目标 Workflow（3个）
1. `MrnaCdsDesignWorkflow` — mRNA CDS 设计
2. `FullLengthMrnaDesignWorkflow` — 全长 mRNA 设计
3. `MrnaSequenceScoringWorkflow` — mRNA 序列打分

## 必须完成的检查项

### 一、Layer 4 — Session & Memory 集成
- [ ] `AgentRunner` 在 `run()` / `stream()` 中是否正确通过 `SessionMemory.load()` / `save()` 持久化状态
- [ ] 多轮对话测试：同一 `session_id` 下，第一轮设计 mRNA CDS，第二轮要求 "提高稳定性"，验证 state 中是否保留上一轮的结果（`best_candidate`、`messages` 等）
- [ ] `WorkspaceManager` 是否为每个 session 创建了独立目录，文件是否写入正确位置
- [ ] 显式传入 `state` 参数时是否绕过 memory（不 load/save）

### 二、Layer 5 — AgentRunner 端到端
- [ ] `AgentRunner.run("Design mRNA CDS for protein MKTLLILTVFGITMLLAVLAQG")` 能否成功：
  - DeepSeek API 被真实调用并生成 `ExecutionPlan`
  - Plan 中必须包含 `mrna_cds_design` 或 `full_length_mrna_design` 步骤
  - `ExecutionController` 正确执行并返回 `WorkflowResult`
  - `final_report` 被正确格式化
- [ ] `AgentRunner.stream()` 能否正确产出 `router` → `plan` → `progress` → `tool_execution` → `runner` 事件流
- [ ] LLM Critic 开启时，低质量结果是否能触发 retry，且 retry 时参数覆盖生效（如 `lambda_value` 调整）
- [ ] `AgentRunner` 对 `MrnaSequenceScoringWorkflow` 的路由是否正确（ deterministic，无 critic 时不 retry）

### 三、CLI / API 入口
- [ ] `cli/mrna_workflow.py` 能否通过命令行正确运行 mrna sequence scoring
- [ ] `workflow_api/app.py` 中 `/v1/workflows/mrna/run` 和 `/v1/agent/run` 是否能正确调用对应 workflow
- [ ] `workflow_api/mrna_handler.py` 的 HTTP 请求/响应schema 是否与 `AgentRunner` 返回的数据结构一致

### 四、DeepSeek API 真实调用验证
- [ ] 测试脚本中必须包含真实的 `LLMPlanner().plan()` 调用，验证 DeepSeek 返回的 JSON plan 能被正确解析
- [ ] 对 `full_length_mrna_design`，验证 `FullLengthMrnaDesignLLMCritic` 的真实 LLM 调用：构建低质量结果（低 CAI），确认 critic 返回 `retry_with_adjustments` 及参数覆盖
- [ ] 如果 DeepSeek API 调用失败（如网络问题），必须有降级机制（不 crash）

### 五、CPU / GPU 工具运行验证
- [ ] CPU 工具：`lineardesign`、`viennarna_fold`、`gc_content`、`cai`、`linearfold` 必须在 CPU 上成功运行
- [ ] GPU 工具：`rnarl`、`gemorna`、`rnastop` 如果当前环境有 GPU 则必须在 GPU 上运行成功；如果只有 CPU，允许 fallback 但必须有明确日志说明
- [ ] 每个工具的 success=True 且返回结果符合预期（序列长度、结构长度、数值范围合理）

### 六、代码规范检查
- [ ] 所有 Layer 4/5 代码是否有类型注解（`-> AgentState`、`-> str` 等）
- [ ] 异常处理是否完善（try/except 不吞异常，有日志记录）
- [ ] INTERFACE LOCK 注释是否完整，导出项是否与 `__init__.py`、`registry.py` 同步
- [ ] 无死代码、无未使用的 import、无硬编码的 API key
- [ ] 测试文件命名规范：`test_<workflow>_layer45.py` 或类似

## 执行步骤
1. 先阅读 `agent_core/runner.py`、`agent_core/session_memory.py`、`workflow_api/app.py`、`cli/mrna_workflow.py`
2. 阅读目标 workflow 的源码及现有测试（`test_mrna_cds_design_full_stack.py`、`test_full_length_mrna_e2e_live.py`、`test_mrna_sequence_scoring_comprehensive.py` 等）
3. 编写一个新的综合测试脚本 `tests/test_mrna_layer45_integration.py`，覆盖上述所有检查项
4. 运行该脚本，确保全部 PASS
5. 运行现有 pytest 测试：`cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/test_mrna_cds_design_full_stack.py tests/test_full_length_mrna_e2e_live.py tests/test_mrna_sequence_scoring_comprehensive.py tests/test_agent_runner_memory.py -v -s`
6. 修正发现的代码规范问题
7. 输出最终报告

## 输出报告格式
```
## 窗口1 检查报告

### 检查结论
- [ ] 全部通过 / [ ] 部分通过（说明哪些未通过）

### 各 Workflow 状态
| Workflow | Layer4 | Layer5 | API调用 | CPU工具 | GPU工具 | 代码规范 | 备注 |
|----------|--------|--------|---------|---------|---------|----------|------|
| MrnaCdsDesignWorkflow | PASS/FAIL | ... | ... | ... | ... | ... | |
| FullLengthMrnaDesignWorkflow | ... | ... | ... | ... | ... | ... | |
| MrnaSequenceScoringWorkflow | ... | ... | ... | ... | ... | ... | |

### 发现的问题与修复
1. ...
2. ...

### 修改的文件列表
- ...

### 测试运行命令及结果截图/日志
```
