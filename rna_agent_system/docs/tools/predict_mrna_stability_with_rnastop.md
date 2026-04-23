# RNASTOP 接口契约文档

> **INTERFACE LOCK (v0.1.0)** — 本文件为 RNASTOP 工具的**权威接口定义**。  
> 任何字段的增删改都必须同步修改以下五个位置，否则会导致 Agent 层、微服务层、ToolSpec 注册层和状态层不一致。

## 同步清单

修改前必须同步检查并更新：

1. **`microservices/rnastop_service/main.py`**
   - `StabilityPredictionRequest` 请求模型
   - `StabilityPredictionResponse` 响应模型

2. **`agent_core/tools.py`**
   - `RNASTOPPredictionInput` 输入 Pydantic 模型
   - `predict_mrna_stability_with_rnastop()` 包装函数的返回值字典键名

3. **`agent_core/tool_specs.py`**
   - `RNASTOPPredictionOutput` 输出模型
   - `"predict_mrna_stability_with_rnastop"` ToolSpec 注册项（`produces` 列表）

4. **`agent_core/nodes.py`**
   - `tool_execution_node` 中 RNASTOP 分支的 `tool_result` 读取键名
   - `critic_node` 中 RNASTOP 摘要字符串（如修改了展示字段）

5. **`agent_core/state.py`**
   - `AgentState` TypedDict 中的 `rnastop_*` 字段

6. **本文档**（`docs/tools/predict_mrna_stability_with_rnastop.md`）

---

## 端点

```
POST http://127.0.0.1:8009/predict/stability
```

---

## 输入（Agent 层 → 微服务层）

### `RNASTOPPredictionInput`（`agent_core/tools.py`）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `filepath` | `str` | **必填** | 包含 RNA 序列的文件路径（workspace 相对路径或绝对路径） |
| `service_url` | `str` | `http://127.0.0.1:8009/predict/stability` | 微服务 REST 端点 |
| `structure` | `Optional[str]` | `None` | 可选的点括号二级结构（长度须与序列一致）；省略时由 ViennaRNA 计算 MFE 结构 |
| `loop_type` | `Optional[str]` | `None` | 可选的 loop-type 注释字符串；省略时从 structure 推导 |
| `checkpoint_path` | `Optional[str]` | `None` | 可选的 checkpoint 路径覆盖 |
| `device` | `Optional[str]` | `None` | 可选的 torch 设备字符串，如 `cuda:0` 或 `cpu` |

### `StabilityPredictionRequest`（`microservices/rnastop_service/main.py`）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sequence` | `str` | **必填** | RNA 序列；支持 FASTA 格式文本 |
| `checkpoint_path` | `Optional[str]` | `None` | 同上 |
| `rnafm_model_path` | `Optional[str]` | `None` | RNA-FM 权重 `.pth` 路径覆盖 |
| `dnabert_model_path` | `Optional[str]` | `None` | DNABERT 模型目录路径覆盖 |
| `structure` | `Optional[str]` | `None` | 同上 |
| `loop_type` | `Optional[str]` | `None` | 同上 |
| `device` | `Optional[str]` | `None` | 同上 |

> **注意**：Agent 层通过 `filepath` 读取序列后，以 `sequence` 字段发送给微服务。`rnafm_model_path` 和 `dnabert_model_path` 仅在微服务层暴露，Agent 层不直接传入。

---

## 输出（微服务层 → Agent 层）

### `StabilityPredictionResponse`（`microservices/rnastop_service/main.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `sequence` | `str` | 原始输入序列 |
| `used_sequence` | `str` | 实际传入模型的序列（若超过 1022 nt 则截断） |
| `sequence_length` | `int` | `len(sequence)` |
| `used_length` | `int` | `len(used_sequence)` |
| `truncated` | `bool` | 是否发生截断 |
| `structure` | `str` | 点括号二级结构（MFE 或用户传入） |
| `loop_type` | `str` | Loop-type 注释字符串 |
| `mfe` | `float` | 最小自由能（kcal/mol） |
| `mean_reactivity` | `float` | 平均 reactivity |
| `mean_deg_Mg_pH10` | `float` | 平均 deg_Mg_pH10 |
| `mean_deg_Mg_50C` | `float` | 平均 deg_Mg_50C |
| `overall_stability` | `float` | 三项指标的全局均值：`mean(predictions[:, :3])` |
| `per_position_predictions` | `Dict[str, List[float]]` | 三项逐位预测值，键为 `"reactivity"`、`"deg_Mg_pH10"`、`"deg_Mg_50C"` |
| `checkpoint_path` | `str` | 实际使用的 checkpoint 绝对路径 |
| `rnafm_model_path` | `str` | 实际使用的 RNA-FM 权重绝对路径 |
| `dnabert_model_path` | `str` | 实际使用的 DNABERT 目录绝对路径 |
| `use_dnabert` | `bool` | 是否使用了含 DNABERT 的 checkpoint |
| `device` | `str` | 推理设备 |
| `model` | `str` | 固定为 `"RNASTOP"` |

### `RNASTOPPredictionOutput`（`agent_core/tool_specs.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_filepath` | `str` | 原始输入文件路径 |
| `prediction_filepath` | `str` | 保存到 workspace 的 JSON 预测结果路径 |
| `sequence` | `str` | 原始序列（服务返回或本地 fallback） |
| `used_sequence` | `str` | 实际评估序列 |
| `sequence_length` | `int` | 序列长度 |
| `used_length` | `int` | 实际使用长度 |
| `truncated` | `bool` | 是否截断 |
| `structure` | `str` | 二级结构 |
| `loop_type` | `str` | Loop-type 注释 |
| `mfe` | `float` | 最小自由能 |
| `mean_reactivity` | `float` | 平均 reactivity |
| `mean_deg_mg_ph10` | `float` | 平均 deg_Mg_pH10（字段名 snake_case） |
| `mean_deg_mg_50c` | `float` | 平均 deg_Mg_50C（字段名 snake_case） |
| `overall_stability` | `float` | 全局稳定性均值 |
| `checkpoint_path` | `str` | Checkpoint 路径 |
| `device` | `str` | 推理设备 |
| `model` | `str` | 固定为 `"RNASTOP"` |

### `predict_mrna_stability_with_rnastop` 实际返回字典（`agent_core/tools.py`）

实际返回的字典键与 `RNASTOPPredictionOutput` 完全一致（因为 `extra="allow"` 允许额外字段，但当前没有额外字段）。

**向后兼容说明**：`overall_stability` 字段如果微服务未返回（旧版本），Agent 层会本地兜底计算为 `(mean_reactivity + mean_deg_mg_ph10 + mean_deg_mg_50c) / 3.0`。

---

## 状态持久化（`agent_core/state.py`）

`tool_execution_node` 将以下键写入 `AgentState`：

| State 键 | 来源字段 | 类型 |
|----------|----------|------|
| `rnastop_prediction_filepath` | `prediction_filepath` | `str` |
| `rnastop_sequence` | `sequence` | `str` |
| `rnastop_used_sequence` | `used_sequence` | `str` |
| `rnastop_structure` | `structure` | `str` |
| `rnastop_loop_type` | `loop_type` | `str` |
| `rnastop_mean_reactivity` | `mean_reactivity` | `float` |
| `rnastop_mean_deg_mg_ph10` | `mean_deg_mg_ph10` | `float` |
| `rnastop_mean_deg_mg_50c` | `mean_deg_mg_50c` | `float` |
| `rnastop_overall_stability` | `overall_stability` | `float` |
| `rnastop_mfe` | `mfe` | `float` |
| `rnastop_checkpoint_path` | `checkpoint_path` | `str` |
| `rnastop_device` | `device` | `str` |
| `candidate_sequence` | `used_sequence` | `str`（与其他工具共享） |
| `mfe` | `mfe` | `float`（若 state 中尚无 mfe 则回填） |

---

## 资产路径策略

RNA-FM 权重**严格**从 repo 内路径加载（已移除 torch hub 缓存自动识别）：

1. `external_repos/RNASTOP/RNA-FM-main/pretrained/RNA-FM_pretrained.pth`
2. `external_repos/RNASTOP/scripts/RNA-FM-main/pretrained/RNA-FM_pretrained.pth`
3. `external_repos/RNASTOP/pretrained/RNA-FM_pretrained.pth`
4. `external_repos/RNASTOP/RNA-FM_pretrained.pth`

DNABERT6 路径：
- `external_repos/RNASTOP/scripts/DNABERT6/pytorch_model.bin`

Checkpoint 路径：
- 完整版：`external_repos/RNASTOP/models/best_model_weights`
- 无 DNABERT 版：`external_repos/RNASTOP/models/best_model_weights_withoutDNABERT`

---

## 测试验证记录

| 测试项 | 结果 | 备注 |
|--------|------|------|
| HTTP 端点 `POST /predict/stability` | ✅ 通过 | 完整版 + DNABERT + cuda:0 |
| `overall_stability` 字段返回 | ✅ 通过 | 值 ≈ 0.0925（36 bp 测试序列） |
| `structure` / `loop_type` 自动计算 | ✅ 通过 | ViennaRNA MFE |
| `per_position_predictions` 完整返回 | ✅ 通过 | 含三项指标 |
| 无 DNABERT checkpoint | ✅ 通过 | `best_model_weights_withoutDNABERT` 可用 |
| GPU 显存占用 | ✅ 确认 | GPU 0 占用 ~21,567 MiB |
