# 窗口5：结构设计 Workflow（Secondary + Tertiary）— Layer 4/5 全面检查

## 项目背景
- 工作目录：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system`
- 架构：五层架构（Layer 0~5），Layer 3 为 DeepSeek 驱动的 LLMPlanner
- Layer 4 = `SessionMemory` + `WorkspaceManager`
- Layer 5 = `AgentRunner` + CLI (`cli/`) + FastAPI (`workflow_api/`)
- 当前 Layer 0/1/2/3 已全部测试通过

## 本次检查目标 Workflow（2个）
1. `RnaSecondaryStructureDesignWorkflow` — RNA 二级结构设计
2. `RnaTertiaryStructureDesignWorkflow` — RNA 三级结构设计

## 必须完成的检查项

### 一、Layer 4 — Session & Memory 集成
- [ ] `AgentRunner` 调用二级/三级结构 workflow 时，session 状态是否正确保存/加载
- [ ] 多轮对话测试：第一轮 "Design secondary structure for sequence XXX with constraints"，第二轮 "refine to reduce MFE"，验证 state 保留上一轮的结构和参数
- [ ] `WorkspaceManager` 是否正确管理结构文件（`.db`、`.ct`、PDB 等）

### 二、Layer 5 — AgentRunner 端到端
- [ ] `AgentRunner.run("Design RNA secondary structure for sequence GGGAAACCC with stem-loop constraints")` 能否成功：
  - DeepSeek 真实调用，生成包含 `rna_secondary_structure_design` 步骤的 Plan
  - `ExecutionController` 执行成功，返回 `WorkflowResult`
  - `final_report` 包含二级结构（dot-bracket）、MFE、未配对比例等
- [ ] `AgentRunner.run("Design RNA tertiary structure for sequence XXX")` 能否成功：
  - 生成包含 `rna_tertiary_structure_design` 步骤的 Plan
  - 返回三级结构（PDB 格式或坐标）
- [ ] `AgentRunner.stream()` 事件流正确性
- [ ] LLM Critic 对两个 workflow 的 retry 逻辑：
  - `RnaSecondaryStructureDesignLLMCritic` 在低 MFE 或高未配对比例时是否建议 retry
  - `RnaTertiaryStructureDesignLLMCritic` 在低质量结构时是否建议 retry

### 三、CLI / API 入口
- [ ] 这两个 workflow 是否有 CLI 入口？如有则测试
- [ ] 是否有 API endpoint？如有则测试；如无则确认是否仅通过 AgentRunner 调用
- [ ] 统一入口 `/v1/workflows/run` 是否能通过 task_type 路由到这两个 workflow

### 四、DeepSeek API 真实调用验证
- [ ] `LLMPlanner` 对结构设计请求的 plan 生成：真实调用 DeepSeek，验证 JSON plan 可解析
- [ ] `RnaSecondaryStructureDesignLLMCritic` 真实 LLM 调用：构建不合理结构结果（如过多未配对碱基），确认 critic 建议调整约束参数
- [ ] `RnaTertiaryStructureDesignLLMCritic` 真实 LLM 调用：构建低质量结果，确认 critic 返回 actionable diagnosis
- [ ] API 失败降级验证

### 五、CPU / GPU 工具运行验证
- [ ] 二级结构 CPU 工具：`predict_rna_secondary_structure`（ViennaRNA）、`predict_rna_secondary_structure_with_linearfold`、ViennaRNA 设计工具等必须在 CPU 上成功
- [ ] 二级结构评估：`compute_dot_bracket_unpaired_fraction`、`compute_rna_sequence_gc_content` 等 CPU 工具
- [ ] 三级结构工具：可能涉及 `RNAComposer`、`SimRNA`、`Rosetta` 或深度学习模型（如 `trrosetta`、`rhofold` 等）
  - 如有 GPU 模型，需在 GPU 上运行成功
  - 如只有 CPU 工具，确认在 CPU 上成功
  - 如无相关工具可用，记录明确的错误和 fallback 行为
- [ ] 确认工具的输入/输出格式与 workflow 代码中的解析逻辑一致

### 六、代码规范检查
- [ ] 类型注解完整
- [ ] 异常处理完善（序列过短、约束冲突、结构预测失败等）
- [ ] INTERFACE LOCK 注释完整且与 `__init__.py`、`registry.py` 同步
- [ ] 无死代码、无未使用的 import
- [ ] 测试文件命名规范

## 执行步骤
1. 阅读 `agent_core/runner.py`、`agent_core/session_memory.py`、`workflow_api/app.py`
2. 阅读目标 workflow 源码及现有测试（`test_rna_secondary_structure_design_comprehensive.py`、`test_rna_secondary_structure_design_full_stack.py`、`test_rna_secondary_structure_design_layer3.py`、`test_rna_tertiary_structure_design_comprehensive.py`、`test_rna_tertiary_structure_design_layer3.py`）
3. 编写新的综合测试脚本 `tests/test_structure_design_layer45_integration.py`
4. 运行该脚本，确保全部 PASS
5. 运行现有 pytest：`cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/test_rna_secondary_structure_design_comprehensive.py tests/test_rna_secondary_structure_design_full_stack.py tests/test_rna_tertiary_structure_design_comprehensive.py tests/test_agent_runner_memory.py -v -s`
6. 修正代码规范问题
7. 输出最终报告

## 输出报告格式
```
## 窗口5 检查报告

### 检查结论
- [ ] 全部通过 / [ ] 部分通过

### 各 Workflow 状态
| Workflow | Layer4 | Layer5 | API调用 | CPU工具 | GPU工具 | 代码规范 | 备注 |
|----------|--------|--------|---------|---------|---------|----------|------|
| RnaSecondaryStructureDesignWorkflow | PASS/FAIL | ... | ... | ... | ... | ... | |
| RnaTertiaryStructureDesignWorkflow | ... | ... | ... | ... | ... | ... | |

### 发现的问题与修复
1. ...
2. ...

### 修改的文件列表
- ...

### 测试运行命令及结果
```
