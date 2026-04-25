# `design_mrna_cds_with_lineardesign` / `design_mrna_cds_batch_with_lineardesign`

- **source**: `https://github.com/LinearDesignSoftware/LinearDesign`
- **single endpoint**: `http://127.0.0.1:8014/generate/cds`
- **batch endpoint**: `http://127.0.0.1:8014/generate/cds/batch`
- **input schema (single)**: `rna_agent_system/agent_core/tools.py:LinearDesignCdsInput`
- **input schema (batch)**: `rna_agent_system/agent_core/tools.py:LinearDesignCdsBatchInput`
- **output schema (single)**: `rna_agent_system/agent_core/tool_specs.py:LinearDesignCdsOutput`
- **output schema (batch)**: `rna_agent_system/agent_core/tool_specs.py:LinearDesignCdsBatchOutput`

## INTERFACE LOCK (v0.2.0)

关联文件清单（修改时必须全部同步）：
  - `microservices/lineardesign_service/main.py`
  - `agent_core/tools.py`
  - `agent_core/tool_specs.py`
  - `agent_core/state.py`
  - `agent_core/nodes.py`
  - `workflow_api/mrna_handler.py`
  - `workflow_api/mrna_schemas.py`
  - 本文件

规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。

## 能力边界

- **capabilities**：
  - 输入单条蛋白序列，生成 CDS（服务端封装 LinearDesign 可执行文件）
  - 输入多条蛋白序列（FASTA 或纯文本），批量生成 CDS（`/generate/cds/batch`）
  - 支持调节 `lambda`（MFE 与 CAI 的平衡系数）
  - 支持自定义密码子使用频率表（`codon_usage_path`）
  - 支持 `verbose` 模式获取详细运行日志
- **limitations**：
  - 需要服务器侧已编译 `bin/LinearDesign_2D`（在 `external_repos/LinearDesign` 执行 `make`）
  - Batch 模式下所有序列共享同一组 `lambda` / `codon_usage_path` / `verbose` 参数
  - 部署环境依赖见项目指南

## 与原始仓库对齐

原始仓库支持：
```bash
echo SEQUENCE | ./lineardesign [OPTIONS]
cat FASTA_FILE | ./lineardesign [OPTIONS]
```

当前封装完整覆盖了原始仓库的 CLI 参数：
| 原始参数 | 当前字段 | 说明 |
|---------|---------|------|
| `-l, --lambda` | `lambda_value` | MFE/CAI 平衡系数，默认 0.0 |
| `-c, --codonusage` | `codon_usage_path` | 密码子使用频率表路径，默认 human table |
| `-v, --verbose` | `verbose` | 详细输出模式 |

单序列 wrapper 通过 `filepath` 读取蛋白序列文件；batch wrapper 通过 `filepath` 读取 FASTA 或多行纯文本文件，解析后调用 batch endpoint。
