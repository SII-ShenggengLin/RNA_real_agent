# `design_mrna_cds_with_rnarl`

> **接口规范版本**：v0.2.0（2026-04-22 定稿）  
> **警告**：以下 Input/Output schema、字段名、默认值均已与 RNARL 微服务对齐，后续修改必须同步更新本文档和代码三层（wrapper / spec / microservice），禁止单方面改动。

---

- **source**: `https://github.com/SII-ShenggengLin/RNARL`
- **endpoint**: `http://127.0.0.1:8008/generate/cds`
- **input schema**: `rna_agent_system/agent_core/tools.py:RNARLCdsInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:RNARLCdsOutput`

---

## 能力边界

- **capabilities**：输入蛋白序列，运行 RNARL actor 推理生成 mRNA CDS；支持 7 个物种/类型模型变体
- **limitations**：依赖 GPU、checkpoint、ESM2 本地权重；运行环境约束见项目指南；最大蛋白长度 1308 aa

---

## Input Schema（`RNARLCdsInput`）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `filepath` | `str` | ✅ | — | 工作区文件路径，内含蛋白质序列（FASTA 或纯文本） |
| `service_url` | `str` | — | `http://127.0.0.1:8008/generate/cds` | 微服务 POST 端点 |
| `model_type` | `str` | — | `"Homo sapiens mRNA"` | 物种/类型模型变体，**必须是以下 7 个值之一** |
| `checkpoint_path` | `Optional[str]` | — | `None` | 自定义 actor 检查点路径（覆盖默认值） |
| `esm2_model_path` | `Optional[str]` | — | `None` | 自定义 ESM-2 本地模型目录 |
| `device` | `Optional[str]` | — | `None` | torch 设备，如 `cuda:0` / `cpu` |

### `model_type` 允许的 7 个值

| 值 | 对应 checkpoint 文件名 |
|----|------------------------|
| `Homo sapiens mRNA` | `homo_mrna.pt` |
| `Homo sapiens circular RNA` | `homo_circ.pt` |
| `Arabidopsis thaliana mRNA` | `Arabidopsis.pt` |
| `Escherichia coli mRNA` | `EscherichiaColi.pt` |
| `Penicillium chrysogenum mRNA` | `PC.pt` |
| `Chlamydomonas reinhardtii mRNA` | `CR.pt` |
| `Thermococcus kodakarensis KOD1 mRNA` | `TK.pt` |

---

## Output Schema（`RNARLCdsOutput`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_filepath` | `str` | 原始输入文件路径 |
| `output_filepath` | `str` | 生成的 CDS 序列保存到工作区的路径 |
| `generated_sequence` | `str` | 生成的 RNA CDS 序列（A/U/G/C） |
| `model_type` | `str` | 实际使用的模型变体 |
| `checkpoint_path` | `str` | 实际使用的检查点路径 |
| `esm2_model_path` | `str` | 实际使用的 ESM-2 模型路径 |
| `device` | `str` | 实际使用的 torch 设备 |
| `model` | `str` | 固定为 `"RNARL-actor"` |

---

## 微服务接口契约（`microservices/rnarl_service/main.py`）

Wrapper 与微服务之间的 HTTP JSON 字段必须严格对齐：

### Request（`CdsDesignRequest`）

```json
{
  "protein_sequence": "MSTSK...",
  "model_type": "Homo sapiens mRNA",
  "checkpoint_path": null,
  "esm2_model_path": null,
  "device": null
}
```

### Response（`CdsDesignResponse`）

```json
{
  "protein_sequence": "MSTSK...",
  "generated_sequence": "AUG...",
  "model_type": "Homo sapiens mRNA",
  "checkpoint_path": "/abs/path/to/homo_mrna.pt",
  "esm2_model_path": "/abs/path/to/esm2_model_t33_650M_UR50D",
  "device": "cuda:0",
  "model": "RNARL-actor"
}
```

---

## 修改约束

> **任何涉及以下文件的修改，必须同步更新本文档，并通过 `py_compile` + 接口对比检查：**
>
> 1. `rna_agent_system/agent_core/tools.py`（`RNARLCdsInput`、`design_mrna_cds_with_rnarl`）
> 2. `rna_agent_system/agent_core/tool_specs.py`（`RNARLCdsOutput`、`ToolSpec` 注册）
> 3. `rna_agent_system/microservices/rnarl_service/main.py`（`CdsDesignRequest`、`CdsDesignResponse`、`generate_cds`）
> 4. `rna_agent_system/agent_core/nodes.py`（`_resolve_protein_to_cds_tool`、`_extract_rnarl_model_type`）
> 5. 本文档 `docs/tools/design_mrna_cds_with_rnarl.md`
