# 窗口3：预测与筛选 Workflow（IRES + ASO）— Layer 4/5 全面检查

## 项目背景
- 工作目录：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system`
- 架构：五层架构（Layer 0~5），Layer 3 为 DeepSeek 驱动的 LLMPlanner
- Layer 4 = `SessionMemory` + `WorkspaceManager`
- Layer 5 = `AgentRunner` + CLI (`cli/`) + FastAPI (`workflow_api/`)
- 当前 Layer 0/1/2/3 已全部测试通过

## 本次检查目标 Workflow（2个）
1. `IresPredictionWorkflow` — IRES 预测
2. `AsoTargetScreeningWorkflow` — ASO 靶点筛选

## 必须完成的检查项

### 一、Layer 4 — Session & Memory 集成
- [ ] `AgentRunner` 调用 IRES/ASO workflow 时，session 状态是否正确保存/加载
- [ ] 多轮对话测试：第一轮 "Predict IRES in sequence XXX"，第二轮 "validate with structural analysis"，验证 state 保留上一轮结果
- [ ] `WorkspaceManager` 是否正确管理输入序列文件和输出报告

### 二、Layer 5 — AgentRunner 端到端
- [ ] `AgentRunner.run("Predict IRES sites in sequence GGGAAACCCUUU...")` 能否成功：
  - DeepSeek 真实调用，生成包含 `ires_prediction` 步骤的 Plan
  - `ExecutionController` 执行成功，返回 `WorkflowResult`
  - `final_report` 包含 IRES 候选位点、概率得分
- [ ] `AgentRunner.run("Screen ASO targets for transcript XXX")` 能否成功：
  - 生成包含 `aso_target_screening` 步骤的 Plan
  - 返回 ASO 靶点列表及可及性评分
  - 注意：ASO workflow 无 critic（确定性评估），验证 retry 不被触发
- [ ] `AgentRunner.stream()` 事件流正确性

### 三、CLI / API 入口
- [ ] `cli/ires_workflow.py` 命令行入口能否正确运行
- [ ] `workflow_api/app.py` 中 `/v1/workflows/ires/run` 是否能正确路由到 `IresPredictionWorkflow`
- [ ] `workflow_api/ires_handler.py` 的请求/响应 schema 与 AgentRunner 返回是否一致
- [ ] ASO workflow 是否有 CLI 或 API 入口？如有则测试；如无则确认是否为仅通过 AgentRunner 调用

### 四、DeepSeek API 真实调用验证
- [ ] `LLMPlanner` 对 IRES/ASO 请求的 plan 生成：真实调用 DeepSeek，验证 JSON plan 可解析
- [ ] `IresPredictionLLMCritic` 真实 LLM 调用验证：
  - 构建低置信度结果，确认 critic 返回 retry 建议及参数覆盖（如调整 `probability_threshold`）
- [ ] ASO workflow 无 critic，验证即使开启 `llm_critic_enabled=True`，也不会触发无意义的 retry
- [ ] API 失败降级：mock API 失败时流程不崩溃

### 五、CPU / GPU 工具运行验证
- [ ] IRES CPU 工具：`iresfinder`（如有）、ViennaRNA 结构验证、`compute_rna_sequence_gc_content` 等必须在 CPU 上成功
- [ ] ASO CPU 工具：`RNAplfold`、`RNAup`/`RNAcofold`、BLAST 相似性搜索等必须在 CPU 上成功
- [ ] 这些 workflow 主要依赖 CPU 工具，确认无 GPU 依赖或 GPU 工具被错误调用

### 六、代码规范检查
- [ ] 类型注解完整
- [ ] 异常处理完善（文件不存在、序列格式错误、工具返回空结果等）
- [ ] INTERFACE LOCK 注释完整且与 `__init__.py`、`registry.py` 同步
- [ ] ASO workflow 在 `WORKFLOW_CRITIC_PAIRS` 中被故意省略，验证 registry.py 注释说明是否准确
- [ ] 无死代码、无未使用的 import

## 执行步骤
1. 阅读 `agent_core/runner.py`、`agent_core/session_memory.py`、`workflow_api/app.py`、`cli/ires_workflow.py`
2. 阅读目标 workflow 源码及现有测试（`test_ires_prediction_comprehensive.py`、`test_ires_prediction.py`、`test_aso_target_screening_comprehensive.py`、`test_aso_target_screening.py`）
3. 编写新的综合测试脚本 `tests/test_prediction_screening_layer45_integration.py`
4. 运行该脚本，确保全部 PASS
5. 运行现有 pytest：`cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/test_ires_prediction_comprehensive.py tests/test_ires_prediction.py tests/test_aso_target_screening_comprehensive.py tests/test_aso_target_screening.py tests/test_agent_runner_memory.py -v -s`
6. 修正代码规范问题
7. 输出最终报告

## 输出报告格式
```
## 窗口3 检查报告

### 检查结论
- [ ] 全部通过 / [ ] 部分通过

### 各 Workflow 状态
| Workflow | Layer4 | Layer5 | API调用 | CPU工具 | GPU工具 | 代码规范 | 备注 |
|----------|--------|--------|---------|---------|---------|----------|------|
| IresPredictionWorkflow | PASS/FAIL | ... | ... | ... | N/A | ... | |
| AsoTargetScreeningWorkflow | ... | ... | ... | ... | N/A | ... | 无critic |

### 发现的问题与修复
1. ...
2. ...

### 修改的文件列表
- ...

### 测试运行命令及结果
```
