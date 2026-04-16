# 变更记录：已实现的增强（不发明新算法）

## 增强 1：ViennaRNA fold 输出结构化（去字符串解析）

- **动机**：原 `predict_rna_secondary_structure` 返回拼接字符串，`nodes.py` 通过正则提取 `mfe/structure`，脆弱且不可审计。
- **实现**：
  - `rna_agent_system/agent_core/tools.py`
    - `predict_rna_secondary_structure` 改为返回 dict（`structure` + `mfe_kcal_per_mol` + `backend/model`）
  - `rna_agent_system/agent_core/nodes.py`
    - state 写回改为直接读取 dict 字段（不再正则解析字符串）
- **收益来源**：输出一致性提升，减少解析失败与状态写回错误。
- **验证**：
  - `python3 -m compileall rna_agent_system/agent_core ...` 通过
  - 单元测试：`rna_agent_system/tests/test_viennarna_wrapper_output.py`

## 增强 2：基于 `ToolSpec.output_model` 的最小输出契约校验

- **动机**：工具输出字段松散，容易出现“缺字段但流程继续”的隐式错误。
- **实现**：
  - 新增 `ToolSpec` 层：
    - `rna_agent_system/agent_core/tool_interface.py`
    - `rna_agent_system/agent_core/tool_specs.py`
  - 在 `tool_execution_node` 执行工具后，对 `TOOL_SPECS` 中声明了 `output_model` 的工具执行 `model_validate`（允许额外字段，但至少保证关键字段存在且类型可解析）。
- **收益来源**：失败更早、更明确；避免下游状态写回 silent failure。
- **验证**：
  - 单元测试：`rna_agent_system/tests/test_tool_specs_output_models.py`

## 增强 3：折叠工具失败时的确定性 fallback（Vienna → LinearFold）

- **动机**：单点工具/服务不可用会导致任务整体失败；而 LinearFold 可作为结构预测的备用实现。
- **实现**：
  - `rna_agent_system/agent_core/nodes.py:tool_execution_node`
    - 捕获 `predict_rna_secondary_structure` 的 `ValueError` 后，若存在 `predict_rna_secondary_structure_with_linearfold` 且可确定 `filepath`，则自动 fallback 调用。
- **收益来源**：提高任务完成率（仅在失败时触发，不增加正常路径成本）。
- **验证**：
  - 编译检查通过；（后续可补充模拟 Vienna 失败的测试用例）

---

## 本次新增测试与依赖

- 新增测试：
  - `rna_agent_system/tests/conftest.py`
  - `rna_agent_system/tests/test_viennarna_wrapper_output.py`
  - `rna_agent_system/tests/test_tool_specs_output_models.py`
- 更新依赖：
  - `rna_agent_system/requirements.txt` 增加 `pytest`

