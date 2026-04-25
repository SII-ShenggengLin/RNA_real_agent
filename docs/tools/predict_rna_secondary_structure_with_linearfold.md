# `predict_rna_secondary_structure_with_linearfold`

> **LinearFold INTERFACE LOCK (v0.2.0)**
>
> 本页描述的接口已冻结为正式版本。任何后续修改必须同步更新以下全部文件并重新跑通端到端测试：
> - `microservices/linearfold_service/main.py`
> - `agent_core/tools.py`（输入模型与工具包装器）
> - `agent_core/tool_specs.py`（输出模型与 ToolSpec）
> - `agent_core/nodes.py`（参数构建与状态处理）
> - `docs/tools/predict_rna_secondary_structure_with_linearfold.md` ← 本文件
> - `docs/workflows/rna_secondary_structure_linearfold_workflow.md`
> - `docs/tasks/rna_secondary_structure_linearfold.md`
> - `rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md`
>
> 违反上述规则的代码提交将被视为破坏性变更并回退。

- **source**: `https://github.com/LinearFold/LinearFold`
- **endpoint**: `http://127.0.0.1:8015/fold`
- **input schema**: `rna_agent_system/agent_core/tools.py:LinearFoldSecondaryInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:LinearFoldOutput`

## 能力边界

- **capabilities**：LinearFold beam search 预测二级结构与能量（服务端实现）。支持约束折叠（`constraints`）和 SHAPE 引导折叠（`shape_file_path`）。
- **limitations**：beam 参数影响结果；属于近似搜索。constraints 与 SHAPE 不能同时使用。

## 关联端点

| 端点 | 路径 | 说明 |
|---|---|---|
| `/fold` | `http://127.0.0.1:8015/fold` | 标准折叠 / 约束折叠 / SHAPE 引导折叠 |
| `/fold/zuker_subopt` | `http://127.0.0.1:8015/fold/zuker_subopt` | Zuker 次优结构枚举 |
| `/eval` | `http://127.0.0.1:8015/eval` | 评估给定结构的自由能 |

## 关联工具

| 工具名 | 端点 | 说明 |
|---|---|---|
| `predict_rna_secondary_structure_with_linearfold` | `/fold` | 标准折叠 |
| `predict_rna_secondary_structure_with_linearfold_zuker` | `/fold/zuker_subopt` | 次优结构 |
| `evaluate_rna_structure_with_linearfold` | `/eval` | 能量评估 |
