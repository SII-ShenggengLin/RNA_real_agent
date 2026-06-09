# 窗口2：RNAi Workflow（siRNA + sgRNA）— Layer 4/5 全面检查

## 项目背景
- 工作目录：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system`
- 架构：五层架构（Layer 0~5），Layer 3 为 DeepSeek 驱动的 LLMPlanner
- Layer 4 = `SessionMemory` + `WorkspaceManager`
- Layer 5 = `AgentRunner` + CLI (`cli/`) + FastAPI (`workflow_api/`)
- 当前 Layer 0/1/2/3 已全部测试通过

## 本次检查目标 Workflow（2个）
1. `SirnaDesignWorkflow` — siRNA 设计
2. `SgRnaDesignWorkflow` — sgRNA 设计（CRGPT 微服务端口 8017）

## 必须完成的检查项

### 一、Layer 4 — Session & Memory 集成
- [ ] 验证 `AgentRunner` 调用 siRNA/sgRNA workflow 时，session 状态是否正确保存/加载
- [ ] 多轮对话：第一轮 "Design siRNA for target sequence AUGCAUGCAU"，第二轮 "increase specificity"，验证 state 中保留 `best_candidate` 和 `messages`
- [ ] `WorkspaceManager` 文件管理是否正确（如生成的候选序列文件、报告文件）

### 二、Layer 5 — AgentRunner 端到端
- [ ] `AgentRunner.run("Design siRNA for target AUGCAUGCAUGCAUGCAUGC")` 能否成功：
  - DeepSeek 真实调用，生成包含 `sirna_design` 步骤的 Plan
  - `ExecutionController` 执行成功，返回 `WorkflowResult`
  - `final_report` 包含候选 siRNA 序列、得分、特异性信息
- [ ] `AgentRunner.run("Design sgRNA for target DNA ATCGATCGATCG")` 能否成功：
  - 生成包含 `sgrna_design` 步骤的 Plan
  - CRGPT 微服务（端口 8017）调用成功（如果服务未启动，需先启动或记录明确错误）
  - 返回 sgRNA 候选序列及得分
- [ ] `AgentRunner.stream()` 对两个 workflow 的事件流是否正确
- [ ] LLM Critic 对 siRNA（`SirnaDesignLLMCritic`）和 sgRNA（`SgRnaDesignLLMCritic`）的 retry 逻辑是否生效

### 三、CLI / API 入口
- [ ] `cli/sirna_workflow.py` 命令行入口能否正确运行
- [ ] `workflow_api/app.py` 中 `/v1/workflows/sirna/run` 是否能正确路由到 `SirnaDesignWorkflow`
- [ ] `workflow_api/sirna_handler.py` 的请求/响应 schema 是否与 AgentRunner 返回一致
- [ ] sgRNA 是否有对应的 API endpoint 或是否通过统一 `/v1/workflows/run` 路由

### 四、DeepSeek API 真实调用验证
- [ ] `LLMPlanner` 对 siRNA/sgRNA 请求的 plan 生成：真实调用 DeepSeek，验证返回的 JSON plan 可被解析
- [ ] `SirnaDesignLLMCritic` 和 `SgRnaDesignLLMCritic` 的真实 LLM 调用验证：
  - 构建 mock 低质量结果（如低特异性），确认 critic 返回 actionable diagnosis
  - 验证 retry 时的 parameter overrides 能被 controller 正确应用
- [ ] API 失败降级机制：mock API 失败时 workflow 不 crash

### 五、CPU / GPU 工具运行验证
- [ ] siRNA CPU 工具：`design_sirna_with_evitar`（evitar）、`run_blastn_similarity_search`（blastn）、ViennaRNA 相关必须在 CPU 上成功
- [ ] sgRNA 工具：`design_sgrna_handle_with_crgpt`、`score_sgrna_handle_with_crgpt` 需要 CRGPT 微服务（端口 8017，GPU 强烈建议）
  - 如果微服务未启动，尝试启动它（`bash microservices/sgrna_design_service/start.sh`）
  - 如果无法启动或无 GPU，记录明确的 fallback 行为和日志
- [ ] CRISOT 套件（端口 8011）如果 sgRNA workflow 中有用到，也需验证

### 六、代码规范检查
- [ ] 类型注解完整（`-> AgentState`、参数类型等）
- [ ] 异常处理完善（微服务连接失败、超时、空结果等情况）
- [ ] INTERFACE LOCK 注释是否完整且与 `__init__.py`、`registry.py` 同步
- [ ] 无死代码、无未使用的 import
- [ ] 测试文件命名规范

## 执行步骤
1. 阅读 `agent_core/runner.py`、`agent_core/session_memory.py`、`workflow_api/app.py`、`cli/sirna_workflow.py`
2. 阅读目标 workflow 源码及现有测试（`test_sirna_design_comprehensive.py`、`test_sgrna_design_e2e.py`、`test_sirna_design_workflow.py`、`test_sgrna_design_workflow.py`）
3. 编写新的综合测试脚本 `tests/test_rnai_layer45_integration.py`，覆盖上述所有检查项
4. 运行该脚本，确保全部 PASS
5. 运行现有 pytest 测试：`cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/test_sirna_design_comprehensive.py tests/test_sgrna_design_e2e.py tests/test_sirna_design_workflow.py tests/test_sgrna_design_workflow.py tests/test_agent_runner_memory.py -v -s`
6. 修正代码规范问题
7. 输出最终报告

## 输出报告格式
```
## 窗口2 检查报告

### 检查结论
- [ ] 全部通过 / [ ] 部分通过

### 各 Workflow 状态
| Workflow | Layer4 | Layer5 | API调用 | CPU工具 | GPU工具/微服务 | 代码规范 | 备注 |
|----------|--------|--------|---------|---------|---------------|----------|------|
| SirnaDesignWorkflow | PASS/FAIL | ... | ... | ... | N/A | ... | |
| SgRnaDesignWorkflow | ... | ... | ... | ... | CRGPT: PASS/FAIL | ... | |

### 发现的问题与修复
1. ...
2. ...

### 修改的文件列表
- ...

### 测试运行命令及结果
```
