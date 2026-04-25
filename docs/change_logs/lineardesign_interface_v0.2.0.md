# 变更记录：LinearDesign 接口锁定 v0.2.0（基准版本）

> **声明：以下文档与代码共同构成 LinearDesign 工具的权威接口契约。**
> **自 2026-04-24 起，所有 LinearDesign 相关修改必须以本次重构为基准，任何偏离必须同步更新本文件及 INTERFACE LOCK 关联清单中的所有文件，并重新跑通端到端测试。**

---

## 1. 变更动机

原 `design_mrna_cds_with_lineardesign` 存在以下问题：

1. **缺少 INTERFACE LOCK**：与其他工具（Evitar v0.2.0、CRISOT v0.2.0、sgrna_design v0.3.0 等）相比，LinearDesign 没有版本锁定注释，导致接口治理缺失。
2. **未对齐原始仓库的多序列能力**：原始仓库 `cat FASTA_FILE | ./lineardesign` 支持批量设计，但当前封装仅暴露单序列入口。
3. **未暴露原始仓库的全部可调参数**：原始仓库支持 `--lambda`、`--codonusage`、`--verbose`，但 workflow API 仅暴露 `service_url` 和 `lambda`。
4. **state 层耦合**：`tool_execution_node` 将 LinearDesign、RNARL、GEMORNA、UTR 设计混在同一个 `elif` 分支中处理，导致 RNARL 专用字段被无条件写入 lineardesign 结果，且缺少 `lineardesign_*` 专用字段。
5. **stderr 丢失**：原始仓库的 stderr 未被 wrapper 暴露。
6. **废弃代码**：`ProteinToCdsOutput` 已无任何工具引用，却被文档错误引用。

---

## 2. 权威接口契约（Canonical Contract）

### 2.1 单序列工具

- **工具名**：`design_mrna_cds_with_lineardesign`
- **微服务端点**：`POST http://127.0.0.1:8014/generate/cds`
- **输入模型**：`agent_core/tools.py:LinearDesignCdsInput`
- **输出模型**：`agent_core/tool_specs.py:LinearDesignCdsOutput`
- **可调参数**（与原始仓库 `--lambda` / `--codonusage` / `--verbose` 一一对应）：
  - `lambda_value` (float, ge=0.0, default=0.0)
  - `codon_usage_path` (Optional[str], default=human table)
  - `verbose` (bool, default=False)
- **输出字段**（必须存在）：
  - `generated_sequence`, `structure`, `mfe`, `cai_score`
  - `lambda_value`, `codon_usage_path`, `raw_output`, `stderr`, `model`
  - `input_filepath`, `output_filepath`

### 2.2 批量工具

- **工具名**：`design_mrna_cds_batch_with_lineardesign`
- **微服务端点**：`POST http://127.0.0.1:8014/generate/cds/batch`
- **输入模型**：`agent_core/tools.py:LinearDesignCdsBatchInput`
- **输出模型**：`agent_core/tool_specs.py:LinearDesignCdsBatchOutput`
- **输入格式**：FASTA（支持 `>` header）或多行纯文本
- **输出字段**（必须存在）：
  - `count`, `success_count`, `items` (list)
  - `best_generated_sequence`, `best_structure`, `best_mfe`, `best_cai_score`
  - `batch_json_filepath`, `lambda_value`, `codon_usage_path`, `model`

### 2.3 AgentState 专用字段

以下字段为 LinearDesign 独占，禁止被其他工具复用或覆盖：

```python
lineardesign_output_filepath: str
lineardesign_generated_sequence: str
lineardesign_structure: str
lineardesign_mfe: float
lineardesign_cai_score: float
lineardesign_lambda_value: float
lineardesign_codon_usage_path: str
lineardesign_raw_output: str
lineardesign_stderr: str
lineardesign_model: str
lineardesign_batch_json_filepath: str
lineardesign_batch_count: int
lineardesign_batch_success_count: int
```

### 2.4 原始仓库对齐表

| 原始仓库 CLI | 当前微服务 / Wrapper 字段 | 说明 |
|-------------|------------------------|------|
| `echo SEQ \| ./lineardesign` | `/generate/cds` + `protein_sequence` | 单序列 |
| `cat FASTA \| ./lineardesign` | `/generate/cds/batch` + `protein_sequences` | 批量 |
| `-l, --lambda` | `lambda_value` | MFE/CAI 平衡，默认 0.0 |
| `-c, --codonusage` | `codon_usage_path` | 密码子表，默认 human |
| `-v, --verbose` | `verbose` | 详细日志 |

---

## 3. 修改文件清单

### 3.1 新增

- `docs/change_logs/lineardesign_interface_v0.2.0.md`（本文件）

### 3.2 修改

1. `rna_agent_system/microservices/lineardesign_service/main.py`
   - 提取 `_run_lineardesign_once()` 公共函数
   - `LinearDesignResponse` 增加 `stderr`
   - 新增 `LinearDesignBatchRequest` / `LinearDesignBatchItem` / `LinearDesignBatchResponse`
   - 新增 `POST /generate/cds/batch`
   - 补上 INTERFACE LOCK (v0.2.0)

2. `rna_agent_system/agent_core/tools.py`
   - `design_mrna_cds_with_lineardesign` 返回 dict 增加 `stderr`，补上 INTERFACE LOCK
   - 新增 `_parse_fasta_protein_sequences()`
   - 新增 `LinearDesignCdsBatchInput` / `design_mrna_cds_batch_with_lineardesign`
   - 在 `MRNA_LANGCHAIN_TOOLS` 中注册 batch 工具

3. `rna_agent_system/agent_core/tool_specs.py`
   - `LinearDesignCdsOutput` 增加 `stderr`，补上 INTERFACE LOCK
   - 新增 `LinearDesignCdsBatchItemOutput` / `LinearDesignCdsBatchOutput`
   - 修正 `design_mrna_cds_with_lineardesign` ToolSpec（version 0.2.0，produces 补全）
   - 注册 `design_mrna_cds_batch_with_lineardesign` ToolSpec

4. `rna_agent_system/agent_core/state.py`
   - 新增 12 个 `lineardesign_*` 专用字段
   - 补上 INTERFACE LOCK

5. `rna_agent_system/agent_core/nodes.py`
   - 导入 `design_mrna_cds_batch_with_lineardesign`
   - 新增 `_needs_lineardesign_batch()`
   - `_resolve_protein_to_cds_tool()` 支持 batch dispatch
   - `specialist_node` 支持 batch 意图识别与提示文案
   - **解耦共享分支**：`design_mrna_cds_with_lineardesign` 独立分支
   - 新增 `design_mrna_cds_batch_with_lineardesign` 独立分支
   - 两个分支均写入 `lineardesign_*` 专用 state + 向后兼容通用字段
   - 移除 RNARL 字段在 lineardesign 分支中的错误写入

6. `rna_agent_system/workflow_api/mrna_handler.py`
   - `_STRIP_CONSTRAINT_KEYS` 增加 `lineardesign_codon_usage_path` / `lineardesign_verbose`
   - `protein_to_cds_sequence()` 增加 `codon_usage_path` 和 `verbose` 参数
   - `execute_mrna_workflow_http()` 解析并透传新参数

7. `rna_agent_system/workflow_api/mrna_schemas.py`
   - 更新 `constraints` 字段描述

8. `rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md`
   - 端口表、工具分发表、LinearDesign 章节更新（batch 端点 / 参数）

9. `docs/tools/design_mrna_cds_with_lineardesign.md`
   - 完全重写，修正 output schema 引用，新增 batch 说明与原始仓库对齐表

10. `docs/agent_build_plan.md`
    - 更新 constraints 说明和 CLI 示例

11. `rna_agent_system/tests/test_integration_registry_smoke.py`
    - 增加 batch 工具注册断言

### 3.3 删除

- `rna_agent_system/agent_core/tool_specs.py`：删除废弃的 `ProteinToCdsOutput`
- `docs/tools/design_mrna_cds_with_gemorna.md`：修正 `ProteinToCdsOutput` → `GemornaCdsOutput`

---

## 4. 验证结果

| 测试项 | 结果 |
|-------|------|
| Health check | ✅ `{"status":"ok"}` |
| 单序列微服务 `/generate/cds` | ✅ 输出与原始仓库 README 示例一致 |
| 批量微服务 `/generate/cds/batch` | ✅ 2 条序列均成功 |
| 单序列 Wrapper | ✅ 返回 `stderr` 等新字段 |
| 批量 Wrapper | ✅ FASTA 解析、batch JSON 审计文件正常 |
| 注册表检查 | ✅ 两个工具均注册 |
| 调度逻辑 | ✅ batch / single / RNARL / GEMORNA 路由正确 |
| 编译检查 | ✅ `py_compile` 全部通过 |

---

## 5. 后续修改规则

任何对 LinearDesign 接口的修改（字段增删、签名变动、返回值结构调整、端点变更）必须同时满足：

1. **同步更新 INTERFACE LOCK 关联清单中的所有文件**：
   - `microservices/lineardesign_service/main.py`
   - `agent_core/tools.py`
   - `agent_core/tool_specs.py`
   - `agent_core/state.py`
   - `agent_core/nodes.py`
   - `docs/tools/design_mrna_cds_with_lineardesign.md`
   - `workflow_api/mrna_handler.py`
   - `workflow_api/mrna_schemas.py`
   - `docs/change_logs/lineardesign_interface_v0.2.0.md`（本文件）
2. **重新跑通端到端测试**（health / single / batch / wrapper / registry smoke）。
3. **更新本文件第 2 节“权威接口契约”**中的对应条目。
4. **若修改涉及 breaking change，必须升级 version**（如 `0.2.0-port8014` → `0.3.0-port8014`）。

**违反上述规则的提交将被回退。**
