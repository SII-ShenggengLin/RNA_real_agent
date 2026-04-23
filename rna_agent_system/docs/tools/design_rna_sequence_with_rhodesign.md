# RhoDesign 接口契约文档

> **INTERFACE LOCK (v0.2.0)** — 本文件为 RhoDesign 工具的**权威接口定义**。  
> 任何字段的增删改都必须同步修改以下四个位置，否则会导致 Agent 层、微服务层和 ToolSpec 注册层不一致。

## 同步清单

修改前必须同步检查并更新：

1. **`agent_core/tool_specs.py`**
   - `RhoDesignOutput` 输出模型
   - `"design_rna_sequence_with_rhodesign"` ToolSpec 注册项

2. **`agent_core/tools.py`**
   - `RhoDesignInput` 输入 Pydantic 模型
   - `design_rna_sequence_with_rhodesign()` 包装函数的返回值字典键名

3. **`microservices/rhodesign_service/main.py`**
   - `RhoDesignRequest` 请求模型
   - `RhoDesignResponse` 响应模型

4. **本文档**（`docs/tools/design_rna_sequence_with_rhodesign.md`）

---

## 端点

```
POST http://127.0.0.1:8006/design/from-structure
```

---

## 输入（Agent 层 → 微服务层）

### `RhoDesignInput`（`agent_core/tools.py`）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pdb_filepath` | `str` | **必填** | PDB/CIF 结构文件路径（workspace 相对路径或绝对路径） |
| `secondary_structure_filepath` | `Optional[str]` | `None` | `.npy` contact-map 路径；为 `None` 时进入 **PDB-only（without-2D）** 模式 |
| `service_url` | `str` | `http://127.0.0.1:8006/design/from-structure` | 微服务 REST 端点 |
| `temperature` | `float` | `1e-5` | 采样温度（Agent 层默认值，实际会根据模式在微服务层被覆盖，见下方“温度动态默认”） |
| `device` | `int` | `0` | CUDA 设备索引 |
| `timeout_seconds` | `int` | `3600` | 子进程超时（秒） |

### `RhoDesignRequest`（`microservices/rhodesign_service/main.py`）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pdb_path` | `str` | **必填** | 同上 |
| `secondary_structure_path` | `Optional[str]` | `None` | 同上 |
| `temperature` | `Optional[float]` | `None` | **微服务层动态默认**：`None` 时，with-2D 默认 `1e-5`，without-2D 默认 `1.0` |
| `device` | `int` | `0` | 同上 |
| `timeout_seconds` | `int` | `3600` | 同上 |

> **注意**：`temperature` 在 `RhoDesignInput` 的默认值为 `1e-5`，但微服务 `RhoDesignRequest` 的默认值为 `None`。  
> 如果用户显式传入 `temperature`，则覆盖动态默认值；如果用户不传（即 Agent 层发送默认值 `1e-5`），微服务会将其视为显式传入，**不会**触发动态默认逻辑。  
> 这是当前已知的行为特征，后续如需优化，需在 `agent_core/tools.py` 中将默认值也改为 `None` 并同步更新本文档。

---

## 输出（微服务层 → Agent 层）

### `RhoDesignResponse`（`microservices/rhodesign_service/main.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_pdb_path` | `str` | 解析后的 PDB 绝对路径 |
| `secondary_structure_path` | `Optional[str]` | 解析后的 `.npy` 绝对路径（without-2D 时为 `None`） |
| `output_fasta_path` | `str` | 服务生成的 FASTA 文件绝对路径 |
| `predicted_sequence` | `str` | 设计的 RNA 序列（已 T→U 转换） |
| `recovery_rate` | `Optional[float]` | 序列恢复率（从 stdout 正则提取） |
| `used_secondary_structure` | `bool` | 是否使用了 with-2D 模式 |
| `checkpoint_path` | `str` | 实际使用的 checkpoint 路径 |
| `service_output_dir` | `str` | 服务本次运行的输出目录 |
| `temperature_used` | `float` | 实际传入上游脚本的温度值 |
| `model` | `str` | 固定为 `"RhoDesign"` |
| `stdout` | `str` | 上游脚本标准输出 |
| `stderr` | `str` | 上游脚本标准错误 |

### `RhoDesignOutput`（`agent_core/tool_specs.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_pdb_filepath` | `str` | 同上 |
| `output_fasta_filepath` | `str` | 从服务复制到 workspace 的 FASTA 路径 |
| `predicted_sequence` | `str` | 同上 |
| `recovery_rate` | `float` | 同上（`None` 时默认 `0.0`） |
| `model` | `str` | 同上 |

### `design_rna_sequence_with_rhodesign` 实际返回字典（`agent_core/tools.py`）

除了 `RhoDesignOutput` 定义的字段外，还包含以下额外键（向后兼容/调试用途）：

| 额外键 | 说明 |
|--------|------|
| `output_filepath` | `save_sequence()` 生成的 workspace 序列文件路径 |
| `used_secondary_structure` | 布尔值 |
| `service_output_dir` | 服务输出目录 |
| `checkpoint_path` | checkpoint 路径 |
| `secondary_structure_filepath` | 用户传入的 `.npy` 路径（如有） |
| `output_fasta_filepath` | 从服务复制到 workspace 的 FASTA 路径 |
| `rhodesign_stdout_filepath` | stdout 日志文件路径 |
| `rhodesign_stderr_filepath` | stderr 日志文件路径 |

---

## 温度动态默认逻辑

```python
if payload.temperature is not None:
    temperature = payload.temperature
else:
    temperature = 1e-5 if use_secondary_structure else 1.0
```

| 模式 | `secondary_structure_path` | 动态默认值 |
|------|---------------------------|-----------|
| with-2D | 非 `None` | `1e-5` |
| without-2D | `None` | `1.0` |

---

## Checkpoint 文件要求

| 文件 | 大小（约） | 用途 |
|------|-----------|------|
| `external_repos/RhoDesign/checkpoint/ss_apexp_best.pth` | ~142 MB | with-2D 模式 |
| `external_repos/RhoDesign/checkpoint/no_ss_apexp_best.pth` | ~141 MB | without-2D 模式 |

下载来源：https://drive.google.com/drive/folders/1H3Itu6TTfaVErPH50Ly7rmQDxElH3JEz?usp=sharing

---

## 上游脚本参数

微服务通过 subprocess 调用以下脚本，参数通过 `-ckpt` 显式传入 checkpoint 路径：

```bash
# with-2D
python inference.py -pdb <pdb> -ss <npy> -save <dir> -device <dev> -temp <temp> -ckpt <ckpt>

# without-2D
python inference_without2d.py -pdb <pdb> -save <dir> -device <dev> -temp <temp> -ckpt <ckpt>
```

---

## 修改历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| v0.2.0 | 2026-04-22 | 接口锁定：统一字段名 `predicted_sequence` / `recovery_rate`；添加 `timeout_seconds`；温度动态默认；`-ckpt` 参数透传；提取 `common_utils.py` 共享模块 | Kimi Code CLI |
| v0.1.0 | — | 初始实现 | — |
