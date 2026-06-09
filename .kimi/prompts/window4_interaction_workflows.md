# 窗口4：相互作用 Workflow（Aptamer + Small Molecule）— Layer 4/5 全面检查

## 项目背景
- 工作目录：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system`
- 架构：五层架构（Layer 0~5），Layer 3 为 DeepSeek 驱动的 LLMPlanner
- Layer 4 = `SessionMemory` + `WorkspaceManager`
- Layer 5 = `AgentRunner` + CLI (`cli/`) + FastAPI (`workflow_api/`)
- 当前 Layer 0/1/2/3 已全部测试通过

## 本次检查目标 Workflow（2个）
1. `RnaAptamerDesignWorkflow` — RNA Aptamer 设计
2. `RnaSmallMoleculeInteractionWorkflow` — RNA-小分子相互作用预测

## 必须完成的检查项

### 一、Layer 4 — Session & Memory 集成
- [ ] `AgentRunner` 调用 aptamer / small molecule workflow 时，session 状态是否正确保存/加载
- [ ] 多轮对话测试：第一轮 "Design aptamer for protein XXX"，第二轮 "score binding affinity"，验证 state 保留结果
- [ ] `WorkspaceManager` 是否正确管理蛋白质结构文件、aptamer 序列文件等

### 二、Layer 5 — AgentRunner 端到端
- [ ] `AgentRunner.run("Design RNA aptamer for target protein with structure path XXX")` 能否成功：
  - DeepSeek 真实调用，生成包含 `rna_aptamer_design` 步骤的 Plan
  - `ExecutionController` 执行成功，返回 `WorkflowResult`
  - `final_report` 包含 aptamer 候选序列、对接得分
  - 注意：`rna_unified_handler.py` 中 `_run_aptamer_via_agent_runner` 的实现方式与直接 AgentRunner 调用是否一致
- [ ] `AgentRunner.run("Predict RNA small molecule interaction for RNA XXX and SMILES CCC...")` 能否成功：
  - 生成包含 `rna_small_molecule_interaction` 步骤的 Plan
  - 返回相互作用预测结果（结合亲和力、结合位点等）
  - 注意：此 workflow 无 critic（固定输入），验证不触发 retry
- [ ] `AgentRunner.stream()` 事件流正确性

### 三、CLI / API 入口
- [ ] aptamer 是否通过 `/v1/workflows/run`（task_type="aptamer"）路由？验证 `rna_unified_handler.py` 中的 `_run_aptamer_via_agent_runner` 是否正确工作
- [ ] small molecule workflow 是否有 CLI 或 API 入口？如有则测试；如无则确认是否仅通过 AgentRunner 调用
- [ ] `workflow_api/rna_unified_handler.py` 的 schema 转换是否正确（`MrnaWorkflowHttpRequest` 与 aptamer 输入之间的字段映射）

### 四、DeepSeek API 真实调用验证
- [ ] `LLMPlanner` 对 aptamer / small molecule 请求的 plan 生成：真实调用 DeepSeek，验证 JSON plan 可解析
- [ ] `RnaAptamerDesignLLMCritic` 真实 LLM 调用验证：构建低质量结果，确认 critic 返回 retry 建议
- [ ] `RnaSmallMoleculeInteractionWorkflow` 无 critic，验证 registry.py 中的注释说明是否准确，且 retry 不被触发
- [ ] API 失败降级验证

### 五、CPU / GPU 工具运行验证
- [ ] Aptamer CPU 工具：结构分析工具、序列生成工具等必须在 CPU 上成功
- [ ] Aptamer GPU 工具：如有深度学习模型（如基于结构的预测模型），需在 GPU 上运行成功；无 GPU 时记录 fallback
- [ ] Small Molecule CPU 工具：分子对接工具、描述符计算等必须在 CPU 上成功
- [ ] Small Molecule GPU 工具：如有图神经网络模型，需在 GPU 上运行成功

### 六、代码规范检查
- [ ] 类型注解完整
- [ ] 异常处理完善（蛋白质结构文件不存在、SMILES 格式错误、对接失败等）
- [ ] INTERFACE LOCK 注释完整且与 `__init__.py`、`registry.py` 同步
- [ ] `RnaSmallMoleculeInteractionWorkflow` 在 `WORKFLOW_CRITIC_PAIRS` 中被故意省略，验证注释说明
- [ ] 无死代码、无未使用的 import

## 执行步骤
1. 阅读 `agent_core/runner.py`、`agent_core/session_memory.py`、`workflow_api/app.py`、`workflow_api/rna_unified_handler.py`
2. 阅读目标 workflow 源码及现有测试（`test_rna_aptamer_design.py`、`test_rna_small_molecule_interaction_comprehensive.py`、`test_rna_small_molecule_interaction.py`）
3. 编写新的综合测试脚本 `tests/test_interaction_layer45_integration.py`
4. 运行该脚本，确保全部 PASS
5. 运行现有 pytest：`cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/test_rna_aptamer_design.py tests/test_rna_small_molecule_interaction_comprehensive.py tests/test_rna_small_molecule_interaction.py tests/test_agent_runner_memory.py -v -s`
6. 修正代码规范问题
7. 输出最终报告

## 输出报告格式
```
## 窗口4 检查报告

### 检查结论
- [ ] 全部通过 / [ ] 部分通过

### 各 Workflow 状态
| Workflow | Layer4 | Layer5 | API调用 | CPU工具 | GPU工具 | 代码规范 | 备注 |
|----------|--------|--------|---------|---------|---------|----------|------|
| RnaAptamerDesignWorkflow | PASS/FAIL | ... | ... | ... | ... | ... | |
| RnaSmallMoleculeInteractionWorkflow | ... | ... | ... | ... | ... | ... | 无critic |

### 发现的问题与修复
1. ...
2. ...

### 修改的文件列表
- ...

### 测试运行命令及结果
```
