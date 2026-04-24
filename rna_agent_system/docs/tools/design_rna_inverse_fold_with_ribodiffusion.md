# RiboDiffusion 接口契约文档

> **INTERFACE LOCK (v0.2.0)** — 本文件为 RiboDiffusion 工具的**权威接口定义**。  
> 任何字段的增删改都必须同步修改以下六个位置，否则会导致 Agent 层、微服务层、ToolSpec 注册层和状态层不一致。

## 同步清单

修改前必须同步检查并更新：

1. **`agent_core/tool_specs.py`**
   - `RiboDiffusionOutput` 输出模型
   - `"design_rna_inverse_fold_with_ribodiffusion"` ToolSpec 注册项

2. **`agent_core/tools.py`**
   - `RiboDiffusionInput` 输入 Pydantic 模型
   - `design_rna_inverse_fold_with_ribodiffusion()` 包装函数的返回值字典键名

3. **`microservices/ribodiffusion_service/main.py`**
   - `RiboDiffusionRequest` 请求模型
   - `RiboDiffusionResponse` 响应模型

4. **`agent_core/state.py`**
   - `ribodiffusion_checkpoint_path` 等状态字段

5. **`agent_core/nodes.py`**
   - `_build_ribodiffusion_tool_args()` 参数构建逻辑
   - `tool_execution_node` RiboDiffusion 分支的状态更新逻辑

6. **本文档**（`docs/tools/design_rna_inverse_fold_with_ribodiffusion.md`）

---

## 端点

```
POST http://127.0.0.1:8021/design/from-pdb
```

---

## 输入（Agent 层 → 微服务层）

### `RiboDiffusionInput`（`agent_core/tools.py`）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pdb_filepath` | `str` | **必填** | PDB 结构文件路径（workspace 相对路径或绝对路径） |
| `service_url` | `str` | `http://127.0.0.1:8021/design/from-pdb` | 微服务 REST 端点 |
| `n_samples` | `int` | `1` | 采样序列数量（`config.eval.n_samples`） |
| `sampling_steps` | `int` | `50` | 扩散采样步数（`config.eval.sampling_steps`） |
| `cond_scale` | `float` | `-1.0` | 分类器自由引导缩放；`-1` 表示禁用 |
| `dynamic_threshold` | `bool` | `False` | 是否启用动态阈值（`config.eval.dynamic_threshold`） |
| `deterministic` | `bool` | `True` | 是否固定随机种子 |
| `checkpoint_name` | `str` | `"exp_inf"` | Checkpoint basename（不含扩展名），支持 `exp_inf` / `exp_inf_large` |
| `device` | `int` | `0` | CUDA 设备索引（通过 `CUDA_VISIBLE_DEVICES` 传入） |

### `RiboDiffusionRequest`（`microservices/ribodiffusion_service/main.py`）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pdb_path` | `str` | **必填** | 同上 |
| `n_samples` | `int` | `1` | 同上 |
| `sampling_steps` | `int` | `50` | 同上 |
| `cond_scale` | `float` | `-1.0` | 同上；仅当 `>= 0.0` 时才会追加到上游命令行 |
| `dynamic_threshold` | `bool` | `False` | 同上；为 `True` 时追加 `--config.eval.dynamic_threshold=True` |
| `deterministic` | `bool` | `True` | 同上；映射为 `--deterministic` / `--nodeterministic` |
| `checkpoint_name` | `str` | `"exp_inf"` | 同上；通过 `--config.eval.model_path` 注入上游 |
| `device` | `int` | `0` | 同上 |
| `timeout_seconds` | `int` | `7200` | 子进程超时（秒） |

> **重要**：`deterministic` 的布尔值必须严格使用 absl.flags 标准格式 `--deterministic` / `--nodeterministic`，**禁止**使用 `--deterministic=true/false`。  
> `dynamic_threshold` 必须使用 `--config.eval.dynamic_threshold=True`（大写 `True`），**禁止**使用小写 `true`。

---

## 输出（微服务层 → Agent 层）

### `RiboDiffusionResponse`（`microservices/ribodiffusion_service/main.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_pdb_path` | `str` | 解析后的 PDB 绝对路径 |
| `pdb_id` | `str` | PDB 文件名（不含 `.pdb` 后缀） |
| `predicted_sequence` | `str` | 第一条设计的 RNA 序列（已 T→U 转换） |
| `generated_sequences` | `list[str]` | 所有采样序列列表 |
| `output_fasta_paths` | `list[str]` | 服务生成的所有 FASTA 文件绝对路径 |
| `recovery_rate` | `Optional[float]` | 序列恢复率（从 stdout 正则提取） |
| `checkpoint_path` | `str` | **实际使用的 checkpoint 绝对路径** |
| `service_output_dir` | `str` | 服务本次运行的输出目录 |
| `fasta_dir` | `str` | 服务生成的 fasta/ 子目录 |
| `model` | `str` | 固定为 `"RiboDiffusion"` |
| `stdout` | `str` | 上游脚本标准输出 |
| `stderr` | `str` | 上游脚本标准错误 |

### `RiboDiffusionOutput`（`agent_core/tool_specs.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_pdb_filepath` | `str` | 同上 |
| `output_filepath` | `str` | `save_sequence()` 生成的 workspace 序列文件路径 |
| `predicted_sequence` | `str` | 同上 |
| `recovery_rate` | `float` | 同上（`None` 时默认 `0.0`） |
| `checkpoint_path` | `str` | 同上 |
| `model` | `str` | 同上 |

### `design_rna_inverse_fold_with_ribodiffusion` 实际返回字典（`agent_core/tools.py`）

除了 `RiboDiffusionOutput` 定义的字段外，还包含以下额外键：

| 额外键 | 说明 |
|--------|------|
| `pdb_id` | PDB ID |
| `service_output_dir` | 服务输出目录 |
| `fasta_dir` | fasta 子目录 |
| `generated_sequences` | 所有序列列表 |
| `output_fasta_filepaths` | 从服务复制到 workspace 的 FASTA 路径列表 |
| `ribodiffusion_stdout_filepath` | stdout 日志文件路径 |
| `ribodiffusion_stderr_filepath` | stderr 日志文件路径 |

---

## 上游脚本调用方式

微服务通过 subprocess 调用原始仓库入口：

```bash
cd external_repos/RiboDiffusion
CUDA_VISIBLE_DEVICES=<device> python main.py \
  --PDB_file <pdb_path> \
  --save_folder <save_folder> \
  --deterministic|--nodeterministic \
  --config.eval.n_samples=<n_samples> \
  --config.eval.sampling_steps=<sampling_steps> \
  --config.eval.model_path=<checkpoint_path> \
  [--config.eval.cond_scale=<cond_scale>] \
  [--config.eval.dynamic_threshold=True]
```

---

## Checkpoint 文件要求

| 文件 | 大小（约） | 用途 |
|------|-----------|------|
| `external_repos/RiboDiffusion/ckpts/exp_inf.pth` | ~1.04 GB | 默认 checkpoint，恢复率较高 |
| `external_repos/RiboDiffusion/ckpts/exp_inf_large.pth` | ~1.04 GB | 更多序列多样性，恢复率略低 |

下载来源：https://github.com/ml4bio/RiboDiffusion README 中的 Google Drive 链接。

> **注意**：原始仓库 `run_lib.py` 中的 checkpoint 路径原为硬编码 `./ckpts/exp_inf.pth`。  
> 本系统已补丁化为优先读取 `config.eval.model_path`，未配置时回退到默认路径，从而支持通过 `checkpoint_name` 动态切换权重。

---

## 状态更新（AgentState）

`tool_execution_node` 执行 RiboDiffusion 工具后，会向 `AgentState` 写入以下字段：

| 状态键 | 来源 |
|--------|------|
| `design_input_pdb_filepath` | `tool_result["input_pdb_filepath"]` |
| `current_filepath` | `tool_result["output_filepath"]` |
| `designed_sequence_fasta_filepath` | `tool_result["output_fasta_filepaths"][0]` |
| `candidate_sequence` | `tool_result["predicted_sequence"]` |
| `sequence_recovery_rate` | `tool_result["recovery_rate"]` |
| `ribodiffusion_checkpoint_path` | `tool_result["checkpoint_path"]` |
| `workspace_files` | 追加所有输出文件和日志文件 |

---

## 修改历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| v0.2.0 | 2026-04-24 | 接口锁定：修复 boolean flag 格式；增加 `checkpoint_name` 支持（`exp_inf` / `exp_inf_large`）；补丁化 `run_lib.py` 支持 `config.eval.model_path`；新增 `ribodiffusion_checkpoint_path` 状态字段；创建本契约文档 | Kimi Code CLI |
| v0.1.0 | — | 初始实现 | — |
