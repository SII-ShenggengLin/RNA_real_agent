# `score_rna_ligand_binding_with_rnasmol`

> **INTERFACE LOCK (v0.2.0)**: 以下接口定义已与原始仓库 `https://github.com/hongli-ma/RNAsmol` 的关键推理路径对照，并以端到端测试确认服务可运行。任何后续修改必须同步更新以下全部位置，禁止单方面变更：
>
> - `microservices/rnasmol_service/main.py` :: `ScoreRequest` / `ScoreResponse`
> - `agent_core/tools.py` :: `RNAsmolScoreInput` / `score_rna_ligand_binding_with_rnasmol`
> - `agent_core/tool_specs.py` :: `RNAsmolScoreOutput` / `score_rna_ligand_binding_with_rnasmol` `ToolSpec`
> - `agent_core/state.py` :: `rnasmol_*` 字段
> - `agent_core/nodes.py` :: `_extract_rnasmol_overrides` / RNAsmol 分支
> - 本文档

---

## ⚠️ 接口冻结声明（2026-04-23 生效）

**RNAsmol 工具的接口自 v0.2.0 起正式冻结，以此版本为准。**

本次接口已经过以下完整验证：
- 与原始仓库 `hongli-ma/RNAsmol` 的模型架构、预处理逻辑、权重加载逐行对照
- 全部 6 个权重文件（pdb/robin × mol/net/rna perturbation）均可正常加载并推理
- 端到端测试覆盖：基本推理、智能权重选择、`device` 切换、错误边界处理
- LangChain Wrapper 层 (`agent_core/tools.py`) 与微服务端点 (`main.py`) 字段完全对齐

**任何人若需修改此接口，必须同时满足以下三条规则，否则视为破坏性变更并回退：**

1. **全量同步**：修改以下 6 个文件中的**全部**对应定义，禁止遗漏任何一处：
   - `microservices/rnasmol_service/main.py`
   - `agent_core/tools.py`
   - `agent_core/tool_specs.py`
   - `agent_core/state.py`
   - `agent_core/nodes.py`
   - `docs/tools/score_rna_ligand_binding_with_rnasmol.md`（本文档）
2. **回归测试**：修改后必须重新运行 RNAsmol 端到端测试，覆盖：
   - 基本推理（`filepath` + `smiles`）
   - 权重智能选择（`dataset` / `perturbation_type`）
   - `device` 切换（`cuda:0` / `cpu`）
   - 错误边界（无效 SMILES、空序列、不存在 checkpoint）
3. **版本升级**：同步提升所有 INTERFACE LOCK 版本号（如 `v0.2.0 → v0.3.0`）。

---

- **source**: `https://github.com/hongli-ma/RNAsmol`
- **endpoint**: `http://127.0.0.1:8007/score`
- **input schema**: `rna_agent_system/agent_core/tools.py:RNAsmolScoreInput`
- **output schema**: `rna_agent_system/agent_core/tool_specs.py:RNAsmolScoreOutput`

## 能力边界

- **capabilities**：对 RNA + ligand SMILES 输出分类概率/标签（RNAsmol 模型）
- **limitations**：模型输出依赖 checkpoint；不等同实验亲和力

## 模型权重选择

RNAsmol 原始仓库提供了 6 个预训练权重文件，对应不同的训练数据来源和数据扰动策略：

```
saved_model/
├── pdb_bothaug_molperturbation.pt      # PDB数据 + 分子扰动
├── pdb_bothaug_netperturbation.pt      # PDB数据 + 网络扰动
├── pdb_bothaug_rnaperturbation.pt      # PDB数据 + RNA扰动
├── robin_bothaug_molperturbation.pt    # ROBIN数据 + 分子扰动
├── robin_bothaug_netperturbation.pt    # ROBIN数据 + 网络扰动
└── robin_bothaug_rnaperturbation.pt    # ROBIN数据 + RNA扰动
```

上层智能体可通过以下参数控制权重选择（优先级从高到低）：

1. **`checkpoint_path`**（显式指定完整路径）
2. **`dataset`** + **`perturbation_type`**（智能匹配）
   - `dataset`: `"pdb"` 或 `"robin"`
   - `perturbation_type`: `"molperturbation"`, `"netperturbation"` 或 `"rnaperturbation"`
3. 环境变量 `RNASMOL_CHECKPOINT_PATH`
4. 自动选择第一个可用的 `.pt` 文件

## 已知问题（需关注）

原始仓库 `rnasmol/preprocessing.py` 与 `rnasmol/preprocessing_demo.py` 中的 `mol_to_graph()` 函数在构造 adjacency matrix 时存在实现缺陷（`zip(edge_index[0], edge_index[1])` 仅处理前两条边且索引偏移 `-1`），导致生成的分子图与真实 bond 结构不一致。

当前微服务 `microservices/rnasmol_service/main.py` 中的 `_mol_to_graph()` 使用了**正确的**图构造逻辑。若上游预训练权重是在原始 buggy 预处理数据上训练的，则服务中的实时预处理可能与训练分布存在偏差。如需严格对齐原始推理行为，应进一步校准 `_mol_to_graph` 与上游 `preprocessing.py` 的输出一致性。
