# RhoFold 接口契约文档

> **INTERFACE LOCK (v0.2.0)** — 本文件为 RhoFold 工具的**权威接口定义**。  
> 任何字段的增删改都必须同步修改以下五个位置，否则会导致 Agent 层、微服务层和 ToolSpec 注册层不一致。

## 同步清单

修改前必须同步检查并更新：

1. **`agent_core/tool_specs.py`**
   - `RhoFoldOutput` 输出模型
   - `"predict_rna_tertiary_structure_with_rhofold"` ToolSpec 注册项

2. **`agent_core/tools.py`**
   - `RhoFoldInput` 输入 Pydantic 模型
   - `predict_rna_tertiary_structure_with_rhofold()` 包装函数的返回值字典键名

3. **`microservices/rhofold_service/main.py`**
   - `RhoFoldPredictRequest` 请求模型
   - `RhoFoldPredictResponse` 响应模型

4. **`agent_core/nodes.py`**
   - RhoFold 结果摄取逻辑（`tool_result.get("pdb_filepath")` 等字段名）
   - Fallback 修复中的直接调用逻辑

5. **本文档**（`docs/tools/predict_rna_tertiary_structure_with_rhofold.md`）

---

## 端点

```
POST http://127.0.0.1:8005/predict
```

---

## 输入（Agent 层 → 微服务层）

### `RhoFoldInput`（`agent_core/tools.py`）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `filepath` | `str` | **必填** | 包含 RNA 序列的 workspace 文件路径（FASTA 或纯文本） |
| `service_url` | `str` | `http://127.0.0.1:8005/predict` | 微服务 REST 端点 |
| `relax_steps` | `int` | `0` | Amber 松弛迭代次数；`0` 表示跳过松弛 |
| `checkpoint_path` | `Optional[str]` | `None` | 自定义 RhoFold checkpoint 路径；为 `None` 时微服务自动搜索标准路径 |
| `device` | `Optional[str]` | `None` | 计算设备，如 `cpu`、`cuda`、`cuda:0`；为 `None` 时由 RhoFold 自动选择 |

### `RhoFoldPredictRequest`（`microservices/rhofold_service/main.py`）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sequence` | `str` | **必填** | 标准化后的 RNA 序列（仅含 A/U/G/C） |
| `single_seq_pred` | `bool` | `True` | 是否仅使用单序列预测（本仓库固定为 `True`，不暴露 MSA 数据库） |
| `input_a3m_path` | `Optional[str]` | `None` | 可选 A3M 路径；仅在 `single_seq_pred=false` 时生效 |
| `checkpoint_path` | `Optional[str]` | `None` | 同上 |
| `device` | `Optional[str]` | `None` | 同上 |
| `relax_steps` | `int` | `0` | 同上 |
| `timeout_seconds` | `int` | `7200` | 子进程超时（秒） |

> **注意**：Agent 层工具函数通过 `read_sequence()` 读取文件后，必须使用 `_normalize_nucleic_sequence()` 去除 FASTA 头行和非法字符，再将纯净序列发送给微服务。

---

## 输出（微服务层 → Agent 层）

### `RhoFoldPredictResponse`（`microservices/rhofold_service/main.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `sequence` | `str` | 标准化后的输入序列 |
| `output_pdb_path` | `str` | 生成的 PDB 文件绝对路径（若 `relax_steps > 0` 且松弛成功，则指向 `relaxed_{n}_model.pdb`，否则指向 `unrelaxed_model.pdb`） |
| `secondary_structure_ct_path` | `Optional[str]` | 预测的二级结构 `.ct` 文件路径 |
| `results_npz_path` | `Optional[str]` | 距离图和 pLDDT 的 `.npz` 文件路径 |
| `log_path` | `Optional[str]` | 运行日志 `log.txt` 路径 |
| `service_output_dir` | `str` | 本次运行的服务输出目录 |
| `mean_plddt` | `Optional[float]` | PDB 中 B-factor 列的平均值（Amber 松弛后会重置为 `0.0`） |
| `model` | `str` | 固定为 `"RhoFold+"` |
| `stdout` | `str` | 上游脚本标准输出 |
| `stderr` | `str` | 上游脚本标准错误 |

### `RhoFoldOutput`（`agent_core/tool_specs.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_filepath` | `str` | 原始输入文件路径 |
| `pdb_filepath` | `str` | 从服务复制到 workspace 的 PDB 路径 |
| `ct_filepath` | `str` | 从服务复制到 workspace 的 CT 路径（默认 `""`） |
| `results_filepath` | `str` | 从服务复制到 workspace 的 NPZ 路径（默认 `""`） |
| `log_filepath` | `str` | 从服务复制到 workspace 的 log 路径（默认 `""`） |
| `service_output_dir` | `str` | 服务原始输出目录（默认 `""`） |
| `mean_plddt` | `float` | 平均 pLDDT（默认 `0.0`） |
| `model` | `str` | 模型标识 |

### `predict_rna_tertiary_structure_with_rhofold` 实际返回字典（`agent_core/tools.py`）

除了 `RhoFoldOutput` 定义的字段外，还包含以下额外键：

| 额外键 | 说明 |
|--------|------|
| `stdout_filepath` | stdout 日志文件路径 |
| `stderr_filepath` | stderr 日志文件路径 |

---

## Checkpoint 文件要求

微服务采用**严格本地优先策略**：若以下路径均不存在，直接返回 `500` 错误，**不会**自动从 HuggingFace 下载。

| 优先级 | 路径 | 说明 |
|--------|------|------|
| 1 | `external_repos/RhoFold/pretrained/RhoFold_pretrained.pt` | 首选本地权重 |
| 2 | `external_repos/RhoFold/pretrained/rhofold_pretrained_params.pt` | HuggingFace 缓存软链接 |
| 3 | `external_repos/RhoFold/pretrained/model_20221010_params.pt` | 历史兼容文件名 |

用户也可通过 `checkpoint_path` 参数传入任意自定义路径。

---

## 上游脚本参数

微服务通过 subprocess 调用原始仓库的 `inference.py`：

```bash
python inference.py \
  --input_fas <temp_fasta> \
  --output_dir <temp_output> \
  --ckpt <resolved_checkpoint> \
  --relax_steps <relax_steps> \
  [--device <device>] \
  --single_seq_pred True
```

---

## 修改历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| v0.2.0 | 2026-04-23 | 接口锁定：统一返回字段名（`pdb_filepath` / `ct_filepath` / `results_filepath`）；暴露 `checkpoint_path` 和 `device`；修复 FASTA 头行解析 bug；强化本地优先 checkpoint 策略；增加 INTERFACE LOCK 注释 | Kimi Code CLI |
| v0.1.0 | — | 初始实现 | — |
