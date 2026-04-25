# ViennaRNA 接口契约文档

> **INTERFACE LOCK (v0.4.0)** — 本文件为 ViennaRNA 工具族的**权威接口定义**。  
> 任何字段的增删改都必须同步修改以下六个位置，否则会导致 Agent 层、微服务层和 ToolSpec 注册层不一致。

## 同步清单

修改前必须同步检查并更新：

1. **`microservices/viennarna_fold/main.py`**
   - 5 个 Pydantic Request/Response 模型（`FoldRequest` / `FoldResponse`、`SirnaDuplexRequest` / `SirnaDuplexResponse`、`RnaUpRequest` / `RnaUpResponse`、`AsoAccessibilityRequest` / `AsoAccessibilityResponse`、`PlfoldProfilesRequest` / `PlfoldProfilesResponse`、`InverseFoldRequest` / `InverseFoldResponse`）
   - 5 个核心计算函数（`_fold_sequence`、`_cofold_duplex`、`_run_rnaup_cli`、`_run_plfold_accessibility_cli`、`_inverse_fold_cli`）
   - FastAPI endpoint 处理逻辑

2. **`agent_core/tools.py`**
   - 6 个 wrapper 输入 Pydantic 模型（`FoldViennaInput`、`SirnaDuplexViennaInput`、`RnaUpViennaInput`、`AsoAccessibilityViennaInput`、`PlfoldLocalProfileViennaInput`、`InverseFoldViennaInput`）
   - 6 个 `@tool` 包装函数的返回值字典键名

3. **`agent_core/tool_specs.py`**
   - 6 个输出 Pydantic 模型（`ViennaFoldOutput`、`ViennaDuplexOutput`、`ViennaRnaUpOutput`、`ViennaAsoAccessibilityOutput`、`ViennaPlfoldLocalProfileOutput`、`ViennaInverseFoldOutput`）
   - 6 个 ToolSpec 注册项

4. **`agent_core/state.py`**
   - ViennaRNA 相关 state 字段（`vienna_sirna_duplex_mfe`、`vienna_rnaup_interaction_energy`、`vienna_rnaup_interaction_structure`、`vienna_aso_mean_unpaired`、`vienna_aso_joint_unpaired`、`vienna_inverse_best_sequence`）

5. **`agent_core/nodes.py`**
   - ViennaRNA 工具调用路由逻辑（`_needs_*` 判断函数）
   - `tool_execution_node` 中 ViennaRNA 结果回写逻辑
   - `critic_node` 中 ViennaRNA 字段的 summary 输出

6. **本文档**（`docs/tools/viennarna_rna_tools.md`）

---

## 微服务架构

| 属性 | 值 |
|------|-----|
| 服务目录 | `microservices/viennarna_fold/` |
| 启动脚本 | `start.sh`（conda 环境 `viennarna_fold_env`，端口 8003） |
| 上游仓库 | [ViennaRNA/ViennaRNA](https://github.com/ViennaRNA/ViennaRNA.git) |
| 安装方式 | `conda env create -f environment.yml`（bioconda `viennarna` 2.7.2） |
| 后端策略 | **优先 RNAlib**（`import RNA`），回退到 CLI 二进制文件 |
| 计算设备 | **纯 CPU**（ViennaRNA 是经典热力学算法，不使用 GPU） |

---

## 端点一览

| # | Endpoint | 工具 | 说明 |
|---|----------|------|------|
| 1 | `POST /fold` | **RNAfold** | 单序列二级结构预测（MFE、配分函数、Centroid） |
| 2 | `POST /sirna-duplex` | **RNAcofold** | 双链（sense/antisense）二聚体折叠与能量 |
| 3 | `POST /rnaup` | **RNAup** | RNA-RNA 相互作用热力学计算 |
| 4 | `POST /aso-accessibility` | **RNAplfold** | ASO 靶区局部可及性（区间汇总） |
| 5 | `POST /plfold-profiles` | **RNAplfold** | 全序列局部可及性曲线（lunp 第一列） |
| 6 | `POST /inverse-fold` | **RNAinverse** | 二级结构反向折叠 |

---

## 1. RNAfold — 单序列二级结构预测

### Endpoint
```
POST http://127.0.0.1:8003/fold
```

### 输入模型 `FoldRequest`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sequence` | `str` | **必填** | RNA 序列（纯文本或 FASTA） |
| `params` | `ViennaModelParams` | 见下 | 共享能量模型参数 |
| `constraint` | `Optional[str]` | `None` | 硬约束点括号字符串（`-C`） |
| `shape_file` | `Optional[str]` | `None` | SHAPE 反应性数据文件路径 |
| `shape_method` | `str` | `"D"` | SHAPE 方法：D、Z 或 W |
| `partfunc` | `bool` | `False` | 计算配分函数与 Centroid（`-p`） |
| `circ` | `bool` | `False` | 环状 RNA（`--circ`） |
| `gquad` | `bool` | `False` | G-四链体（`--gquad`） |

### 输出模型 `FoldResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `sequence` | `str` | 标准化后的 RNA 序列 |
| `structure` | `str` | MFE 二级结构（点括号） |
| `mfe` | `float` | 最小自由能（kcal/mol） |
| `backend` | `str` | `"RNAlib"` 或 `"RNAfold-cli"` |
| `ensemble_free_energy` | `Optional[float]` | 系综自由能（仅 `partfunc=true`） |
| `centroid_structure` | `Optional[str]` | Centroid 结构（仅 `partfunc=true`） |
| `centroid_distance` | `Optional[float]` | Centroid 距离（仅 `partfunc=true`） |

### Agent 层输出模型 `ViennaFoldOutput`

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_filepath` | `str` | 输入文件路径 |
| `structure` | `str` | MFE 结构 |
| `mfe_kcal_per_mol` | `float` | MFE |
| `ensemble_free_energy` | `Optional[float]` | 系综自由能 |
| `centroid_structure` | `Optional[str]` | Centroid |
| `centroid_distance` | `Optional[float]` | Centroid 距离 |

---

## 2. RNAcofold — 双链二聚体折叠

### Endpoint
```
POST http://127.0.0.1:8003/sirna-duplex
```

### 输入模型 `SirnaDuplexRequest`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sense` / `antisense` | `Optional[str]` | `None` | 两条链（5'→3'） |
| `fasta_content` | `Optional[str]` | `None` | 两条 FASTA 记录替代上述字段 |
| `params` | `ViennaModelParams` | 见下 | 能量模型参数 |
| `concentrations` | `bool` | `False` | 计算浓度平衡（`-c`，需 `conc_A` / `conc_B`） |
| `conc_A` / `conc_B` | `Optional[float]` | `None` | 初始单体浓度（mol/L） |
| `partfunc` | `bool` | `False` | 配分函数（`-p`） |

> ⚠️ **注意**：`concentrations=true` 时**强制使用 CLI 模式**（RNAlib Python API 不支持浓度计算）。

### 输出模型 `SirnaDuplexResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `sense` / `antisense` | `str` | 输入链 |
| `cofold_sequence` | `str` | 合并序列（`sense&antisense`） |
| `structure` | `str` | 二聚体结构（含 `&`） |
| `mfe` | `float` | 二聚体 MFE |
| `ensemble_free_energy` | `Optional[float]` | 系综自由能 |
| `equilibrium_concentrations` | `Optional[Dict[str,float]]` | 平衡浓度（AA/AB/BB/A/B） |

---

## 3. RNAup — RNA-RNA 相互作用

### Endpoint
```
POST http://127.0.0.1:8003/rnaup
```

### 输入模型 `RnaUpRequest`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sequence1` | `str` | **必填** | 第一条 RNA 序列（target，通常较长） |
| `sequence2` | `str` | **必填** | 第二条 RNA 序列（probe / small RNA） |
| `params` | `ViennaModelParams` | 见下 | 能量模型参数 |
| `ulength` | `int` | `4` | 输出非结构化区域长度（`-u`） |
| `window` | `int` | `25` | 最大相互作用区域长度（`-w`） |
| `include_both` | `bool` | `False` | 包含两条 RNA 的非配对概率（`-b`） |
| `extend5` / `extend3` | `int` | `0` | 5'/3' 端延伸长度 |
| `contributions` | `str` | `"S"` | 输出贡献类型（`-c`）：S/H/I/M/E |

### 输出模型 `RnaUpResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `sequence1` / `sequence2` | `str` | 输入序列 |
| `interaction_energy` | `Optional[float]` | 相互作用总能量（kcal/mol） |
| `interaction_structure` | `Optional[str]` | 相互作用结构（含 `&`） |
| `raw_stdout` | `str` | RNAup 原始 stdout |

---

## 4. RNAplfold — ASO 靶区可及性

### Endpoint
```
POST http://127.0.0.1:8003/aso-accessibility
```

### 输入模型 `AsoAccessibilityRequest`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sequence` | `str` | **必填** | 完整靶标 RNA（纯文本或 FASTA） |
| `region_start` / `region_end` | `int` | **必填** | 结合区域 1-based 起止 |
| `aso_oligo_length` | `int` | `18` | ASO 长度 |
| `winsize` | `int` | `70` | 窗口大小（`-W`） |
| `span` | `int` | `70` | 最大配对跨度（`-L`） |
| `unpaired_ulength` | `int` | `25` | 最大非配对长度（`-u`） |
| `cutoff` | `Optional[float]` | `None` | 概率阈值（`-c`） |
| `opening_energies` | `bool` | `False` | 返回开口能量对数（`-O`） |

### 输出模型 `AsoAccessibilityResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `sequence_length` | `int` | 序列长度 |
| `region_start` / `region_end` | `int` | 区域起止 |
| `mean_unpaired_prob_single_nt` | `Optional[float]` | 区域内单核苷酸平均非配对概率 |
| `joint_unpaired_prob_stretch_ending_at_region_end` | `Optional[float]` | 以区域结尾为终点的连续非配对概率 |
| `aso_oligo_length_used` | `int` | 实际使用的 ASO 长度 |

---

## 5. RNAplfold — 全序列可及性曲线

### Endpoint
```
POST http://127.0.0.1:8003/plfold-profiles
```

### 输入模型 `PlfoldProfilesRequest`

与 `AsoAccessibilityRequest` 相同，但不包含 `region_start` / `region_end` / `aso_oligo_length`。

### 输出模型 `PlfoldProfilesResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `sequence_length` | `int` | 序列长度 |
| `positions` | `List[int]` | 1-based 位置列表 |
| `unpaired_prob_1nt` | `List[float]` | 每个位置的单核苷酸非配对概率 |
| `mean_unpaired_prob_1nt` | `float` | 全序列平均 |
| `min_unpaired_prob_1nt` | `float` | 最小值 |
| `max_unpaired_prob_1nt` | `float` | 最大值 |

---

## 6. RNAinverse — 反向折叠

### Endpoint
```
POST http://127.0.0.1:8003/inverse-fold
```

### 输入模型 `InverseFoldRequest`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `structure` | `str` | **必填** | 目标二级结构（点括号） |
| `start_sequence` | `str` | `""` | IUPAC 提示序列（空 = 全 N） |
| `params` | `ViennaModelParams` | 见下 | 能量模型参数 |
| `repeats` | `int` | `1` | 搜索重复次数（`-R`） |
| `function_mode` | `str` | `"m"` | 目标函数：m / p / mp（`-F`） |
| `final_cost` | `Optional[float]` | `None` | 提前停止阈值（`-f`，仅 `-Fp`） |
| `alphabet` | `Optional[str]` | `None` | 自定义核苷酸字母表（`-a`） |

### 输出模型 `InverseFoldResponse`

| 字段 | 类型 | 说明 |
|------|------|------|
| `structure` | `str` | 目标结构 |
| `best_sequence` | `str` | 最佳匹配序列 |
| `hamming_distance` | `Optional[int]` | 汉明距离 |
| `partition_probability` | `Optional[float]` | 配分概率（`-Fp` 模式） |

---

## 共享能量模型参数 `ViennaModelParams`

所有 6 个端点共享以下能量模型参数（映射到上游 `vrna_md_t` / CLI 标志）：

| 字段 | 类型 | 默认值 | 对应 CLI 标志 | 说明 |
|------|------|--------|---------------|------|
| `temp_c` | `float` | `37.0` | `-T` | 温度（°C） |
| `dangles` | `int` | `2` | `-d` | 悬挂末端模型（0–3） |
| `noLP` | `bool` | `False` | `--noLP` | 禁止孤独配对 |
| `noGU` | `bool` | `False` | `--noGU` | 禁止 GU 配对 |
| `noClosingGU` | `bool` | `False` | `--noClosingGU` | 禁止螺旋末端 GU |
| `salt` | `Optional[float]` | `None` | `--salt` | 盐浓度（M） |
| `noTetra` | `bool` | `False` | `-4` | 忽略特殊环稳定能 |
| `energyModel` | `Optional[int]` | `None` | `--energyModel` | 能量模型 |
| `nsp` | `Optional[str]` | `None` | `--nsp` | 非标准配对（如 `'-GA'`） |
| `paramFile` | `Optional[str]` | `None` | `-P` | 自定义参数文件或 `"DNA"` |

---

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v0.4.0 | 2026-04-25 | **接口锁定**：对齐 upstream ViennaRNA 2.7.2 全部能力。新增 RNAup 完整集成、RNAcofold `mfe_dimer()` 修复、RNAplfold NA 解析修复、RNAcofold 浓度回退 CLI 逻辑、RNAinverse 解除 `-d2` 硬编码。添加 INTERFACE LOCK 注释与本文档。 |
| v0.2.0 | — | 早期版本（RNAfold + RNAplfold + RNAinverse 基础功能） |
