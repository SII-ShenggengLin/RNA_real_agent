# RNA Design Multi-Agent System Guide

> **读者**：人类开发者 / 后续接手的大模型  
> **描述**：本文档描述 `RNA_real_agent` 项目的 **当前真实代码状态**，包括架构、工具、部署和扩展规范。

---

## 目录

1. [项目目标与核心原则](#1-项目目标与核心原则)
2. [架构总览](#2-架构总览)
3. [目录结构](#3-目录结构)
4. [工具与端口总表](#4-工具与端口总表)
5. [智能体工作流逻辑](#5-智能体工作流逻辑)
6. [各工具接入详情](#6-各工具接入详情)
7. [LLM 配置状态](#7-llm-配置状态)
8. [部署与运行](#8-部署与运行)
9. [测试指南](#9-测试指南)
10. [代码与仓库管理规范](#10-代码与仓库管理规范)
11. [新增工具标准流程](#11-新增工具标准流程)
12. [已知限制与后续计划](#12-已知限制与后续计划)

---

## 1. 项目目标与核心原则

本项目实现一个 RNA 设计智能体系统：

- **输入**：自然语言任务、RNA 序列、蛋白序列
- **输出**：调用底层生信工具得到设计结果、评分结果、结构预测结果
- **方式**：上层 Agent 负责路由与编排，下层工具通过本地微服务隔离运行

**核心原则**：

| 原则 | 说明 |
|------|------|
| 序列不走 prompt | 长序列通过 `workspace/` 文件路径传递，不在上下文中搬运 |
| 环境隔离 | 每个工具有独立 Conda 环境 + FastAPI 微服务 |
| HTTP 解耦 | Agent 层只通过 HTTP API 调用工具，不直接 import 第三方仓库 |
| 源码独立 | 第三方仓库通过 `external_repos/` 的 git submodule 管理 |

---

## 2. 架构总览

```
┌──────────────────────────────────────────────────────┐
│  Streamlit UI  (frontend/app.py)                     │
├──────────────────────────────────────────────────────┤
│  LangGraph Agent  (agent_core/)                      │
│  ┌─────────┐  ┌────────────┐  ┌──────┐  ┌────────┐  │
│  │ Router  │→│ Specialist │→│ Tool │→│ Critic │  │
│  │ (规则)  │  │   (规则)   │  │ Exec │  │ (规则) │  │
│  └─────────┘  └────────────┘  └──────┘  └────────┘  │
├──────────────────────────────────────────────────────┤
│  HTTP Tool Layer  (@tool → requests.post)            │
├──────────────────────────────────────────────────────┤
│  FastAPI Microservices  (microservices/*/main.py)     │
│  每个服务独立 Conda 环境，独占端口                       │
├──────────────────────────────────────────────────────┤
│  External Repos  (external_repos/*)                  │
│  第三方源码 + 权重 + 编译产物                            │
└──────────────────────────────────────────────────────┘
```

**技术栈**：

- Agent 编排：LangGraph
- 前端：Streamlit
- 工具接口：LangChain `@tool`
- 工具运行时：FastAPI + Conda
- 当前模式：**规则驱动**（Router / Specialist / Critic 均为规则实现，工具链稳定后可切回 LLM）

---

## 3. 目录结构

```
rna_agent_system/
├── agent_core/                 # Agent 编排层
│   ├── state.py                #   AgentState 定义
│   ├── graph.py                #   LangGraph 工作流构建
│   ├── nodes.py                #   Router / Specialist / Critic 节点逻辑
│   ├── tools.py                #   @tool 封装（HTTP → 微服务）
│   ├── file_manager.py         #   workspace 文件读写
│   └── llm_config.py           #   LLM 客户端配置（当前未启用）
├── frontend/
│   └── app.py                  # Streamlit 聊天界面
├── microservices/              # 微服务封装层（每个工具一个子目录）
│   ├── <tool>_service/
│   │   ├── environment.yml     #   Conda 环境定义
│   │   ├── main.py             #   FastAPI 服务入口
│   │   ├── start.sh            #   启动脚本
│   │   └── install_*.sh        #   （可选）编译/补丁脚本
│   └── ...
├── external_repos/             # 第三方源码仓库（git submodule）
├── workspace/                  # 运行中间文件（序列、结构、日志等）
├── docs/                       # 项目文档
├── .env                        # LLM 配置（当前规则模式下可不用）
└── requirements.txt            # 主 Agent 环境依赖
```

### 核心文件说明

| 文件 | 职责 |
|------|------|
| `state.py` | 定义 `AgentState` TypedDict，含所有工具产出的状态字段 |
| `file_manager.py` | `save_sequence()` / `read_sequence()` / `copy_file_to_workspace()` |
| `tools.py` | 将每个微服务 HTTP 接口封装为 LangChain `@tool` |
| `nodes.py` | 规则路由、specialist 分发、工具执行、critic 判定 |
| `graph.py` | 用 LangGraph 组装 `Router → Specialist → Tool → Critic` 工作流 |

---

## 4. 工具与端口总表

| 端口 | 服务目录 | 工具名称 | 能力说明 | 验证状态 |
|------|----------|----------|----------|----------|
| 8003 | `viennarna_fold` | ViennaRNA | 二级结构 / cofold / RNAplfold / RNAinverse | ✅ Linux |
| 8004 | `gemorna_service` | GEMORNA | 蛋白→mRNA CDS 设计 | ✅ Linux GPU |
| 8005 | `rhofold_service` | RhoFold | RNA 三级结构预测（单序列模式） | ✅ Linux GPU |
| 8006 | `rhodesign_service` | RhoDesign | RNA 结构→序列设计 | ✅ Linux GPU |
| 8007 | `rnasmol_service` | RNAsmol | RNA-ligand 打分 | ✅ Linux GPU |
| 8008 | `rnarl_service` | RNARL | 蛋白→mRNA CDS 设计（7 物种） | ✅ Linux GPU |
| 8009 | `rnastop_service` | RNASTOP | mRNA 稳定性/降解预测 | ✅ Linux GPU |
| 8010 | `gernabind_service` | GerNA-Bind | RNA-ligand 打分 + binding-site | ✅ Linux GPU |
| 8011 | `crisot_service` | CRISOT | CRISPR off-target 打分/优化 | ✅ Linux |
| 8012 | `odesign_service` | ODesign | 生物分子设计（RNA 相关） | ✅ Linux GPU |
| 8013 | `iresfinder_service` | IRESfinder | IRES 预测（Python 3 重实现） | ✅ Linux |
| 8014 | `lineardesign_service` | LinearDesign | 蛋白→mRNA CDS 设计 | ✅ Linux |
| 8015 | `linearfold_service` | LinearFold | RNA 二级结构预测 | ✅ Linux |
| 8016 | `evitar_service` | Evitar | siRNA/Cas13 设计（Perl CLI） | ✅ Linux |
| 8017 | `sgrna_design_service` | CRGPT | sgRNA handle 设计 | ✅ Linux GPU |
| 8018 | `codonw_slim_service` | codonw-slim | CDS 密码子指标（CAI/Fop/CBI/Nc 等） | ✅ Linux |
| 8019 | `blast_service` | BLAST+ | blastn 核酸相似性搜索 | ✅ Linux |
| 8020 | `rna_sequence_metrics_service` | RNA metrics | 序列 GC 含量；点括号结构未配对（`.`）比例 | ✅ Linux |

> 后续新增工具从 **8021** 起顺延。

---

## 5. 智能体工作流逻辑

### 5.1 工作流图

```
User Input → Router → Specialist → Tool Execution → Critic → End / 回到 Specialist
```

### 5.2 Router（规则路由）

根据用户文本关键词路由到对应 Specialist：

| 路由目标 | 触发关键词（部分） |
|----------|-------------------|
| `sirna_specialist` | `sirna`、`脱靶`、`off-target`、`duplex`、`cofold`、`结合能`、`evitar`、`predesign`、`cas13`、`rnaxs`、`predsi` |
| `crispr_specialist` | `crispr`、`cas9`、`sgrna`、`crisot`、`guide rna`、`crgpt`、`sgrna handle` |
| `mrna_specialist` | `mrna`、`design`、`protein`、`cds`、`fold`、`structure`、`gemorna`、`lineardesign`、`linearfold`、`rhofold`、`rhodesign`、`rnasmol`、`rnastop`、`gernabind`、`ires`、`stability`、`aso`、`inverse fold`、`codonw`、`blast`、`blastn` 等 |
| 默认 | `mrna_specialist` |

### 5.3 Specialist 分发

#### siRNA Specialist

| 条件 | 调用工具 |
|------|----------|
| 默认 siRNA | `predict_sirna_efficiency` + `check_off_target` |
| Evitar 关键词 | `design_sirna_with_evitar` |
| siRNA duplex / cofold 语义 | `compute_sirna_duplex_binding_vienna` |

#### CRISPR Specialist

| 条件 | 调用工具 |
|------|----------|
| sgRNA handle/design/crgpt | `design_sgrna_handle_with_crgpt` |
| 单对打分 | `score_crispr_off_target_with_crisot` |
| CSV specificity | `calculate_crispr_specificity_with_crisot` |
| genome + off-spec | `search_crispr_off_targets_with_crisot` |
| optimize/优化 | `optimize_sgrna_with_crisot` |

#### mRNA Specialist

按规则优先级依次匹配（命中即停）：

| 优先级 | 条件 | 调用工具 |
|--------|------|----------|
| 1 | 显式 `gernabind` | `score_rna_ligand_binding_with_gernabind` |
| 2 | RNA-ligand 打分（`rnasmol` / `smiles` / `ligand`） | `score_rna_ligand_binding_with_rnasmol` |
| 3 | IRES 识别 | `predict_putative_ires_with_iresfinder` |
| 4 | ViennaRNA 逆折叠（`inverse fold` / `rnainverse`） | `inverse_fold_rna_secondary_structure_vienna` |
| 5 | ASO 可及性（`aso` / `plfold` / `accessibility`） | `compute_aso_target_accessibility_vienna` |
| 6 | mRNA 稳定性（`stability` / `degradation` / `rnastop`） | `predict_mrna_stability_with_rnastop` |
| 7 | 独立密码子指标（`codonw` / `codon usage`） | `analyze_cds_codon_metrics_with_codonw_slim` |
| 7b | 序列 GC 含量（`gc content` / `gc含量` 等） | `compute_rna_sequence_gc_content` |
| 7c | 二级结构点括号未配对比例（`unpaired fraction` / `未配对比例` 等） | `compute_dot_bracket_unpaired_fraction` |
| 8 | BLAST 搜索（`blast` / `blastn`） | `run_blastn_similarity_search` |
| 9 | 结构→序列（`rhodesign` + `.pdb`） | `design_rna_sequence_with_rhodesign` |
| 10 | ODesign 设计 | `run_odesign_inference` |
| 11 | LinearDesign CDS 设计 | `design_mrna_cds_with_lineardesign` |
| 12 | RNARL CDS 设计（含 `rnarl` 关键词） | `design_mrna_cds_with_rnarl` |
| 13 | GEMORNA CDS 设计 | `design_mrna_cds_with_gemorna` |
| 14 | 结构预测（默认） | `analyze_cds_codon_metrics_with_codonw_slim` → `predict_rna_secondary_structure` (ViennaRNA) / `predict_rna_secondary_structure_with_linearfold` |
| — | 文本含 `rhofold`/`3d`/`tertiary` | 额外调用 `predict_rna_tertiary_structure_with_rhofold` |

CDS 设计（GEMORNA / RNARL / LinearDesign）完成后，若用户请求含结构预测语义，`tool_execution_node` 会自动串联折叠工具。

### 5.4 Critic（规则判定）

| 场景 | 规则 | 行为 |
|------|------|------|
| siRNA | `off_target_genes > 0` | reject → 重试 |
| mRNA 结构预测 | `mfe > -20.0` | reject → 重试 |
| RhoDesign | 微服务成功返回 | pass |
| 其他 | — | pass |
| 重试上限 | `max_retries = 3` | 强制 pass |

> **注意**：短序列 MFE 通常在 -2 ~ -15 kcal/mol，会连续触发 reject 直到耗尽重试次数后放行。后续应调整阈值或按序列长度归一化。

---

## 6. 各工具接入详情

### 6.1 ViennaRNA (端口 8003)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [ViennaRNA/ViennaRNA](https://github.com/ViennaRNA/ViennaRNA.git) |
| 微服务目录 | `microservices/viennarna_fold/` |
| 环境 | `python=3.10` + bioconda `viennarna` |
| 接口 | `GET /health`、`POST /fold`、`POST /sirna-duplex`、`POST /aso-accessibility`、`POST /inverse-fold` |
| 后端策略 | 优先 RNAlib（`import RNA`），回退到 CLI（`RNAfold --noPS`） |

**Agent 工具函数**：
- `predict_rna_secondary_structure(filepath)` — 单序列 MFE 二级结构
- `compute_sirna_duplex_binding_vienna(filepath)` — siRNA 正反义链共折叠
- `compute_aso_target_accessibility_vienna(filepath, region_start, region_end)` — RNAplfold 可及性
- `inverse_fold_rna_secondary_structure_vienna(filepath)` — RNAinverse 逆折叠

**部署注意**：
- 默认通过 Conda bioconda `viennarna` 安装，无需从源码编译
- 可选 `build_from_submodule_linux.sh` 从 submodule 源码编译

### 6.2 GEMORNA (端口 8004)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [RainaBio/GEMORNA](https://github.com/RainaBio/GEMORNA) |
| 微服务目录 | `microservices/gemorna_service/` |
| 环境 | `python=3.10`（**必须**，`.so` 有 ABI 依赖） |
| 接口 | `POST /generate/cds` |
| Agent 工具 | `design_mrna_cds_with_gemorna(filepath)` |

**关键注意事项**：
- checkpoint 通过 Git LFS 管理，需 `git lfs pull` 或手动放入 `external_repos/GEMORNA/checkpoints/`
- **不要用 Python 3.9**，会出现 `undefined symbol: PyDescr_IsData`
- 需要 Linux + GPU

### 6.3 RNARL (端口 8008)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [SII-ShenggengLin/RNARL](https://github.com/SII-ShenggengLin/RNARL.git) |
| 微服务目录 | `microservices/rnarl_service/` |
| 环境 | `python=3.10` + GPU |
| 接口 | `GET /health`、`GET /models`、`POST /generate/cds` |
| Agent 工具 | `design_mrna_cds_with_rnarl(filepath, model_type=...)` |

**7 个 checkpoint**：

| model_type | checkpoint |
|------------|-----------|
| Homo sapiens mRNA | `homo_mrna.pt` |
| Homo sapiens circular RNA | `homo_circ.pt` |
| Arabidopsis thaliana mRNA | `Arabidopsis.pt` |
| Escherichia coli mRNA | `EscherichiaColi.pt` |
| Penicillium chrysogenum mRNA | `PC.pt` |
| Chlamydomonas reinhardtii mRNA | `CR.pt` |
| Thermococcus kodakarensis KOD1 mRNA | `TK.pt` |

**关键注意事项**：
- 权重目录：`external_repos/RNARL/checkpoints/` + `external_repos/RNARL/esm2_model_t33_650M_UR50D/`
- ESM-2 必须使用**本地目录**（`local_files_only=True`）
- `.pt` 必须是真实二进制权重（非 LFS pointer）

### 6.4 RhoFold (端口 8005)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [ml4bio/RhoFold](https://github.com/ml4bio/RhoFold) |
| 微服务目录 | `microservices/rhofold_service/` |
| 环境 | `python=3.7.12` + `pytorch=1.10.2` + `cudatoolkit=11.3.1` |
| 接口 | `GET /health`、`POST /predict` |
| Agent 工具 | `predict_rna_tertiary_structure_with_rhofold(filepath)` |

**关键注意事项**：
- 当前默认 `single_seq_pred=true`，不依赖本地 MSA 数据库
- checkpoint：`external_repos/RhoFold/pretrained/RhoFold_pretrained.pt`
- 首次运行可能需网络访问 Hugging Face
- 微服务代码专门使用 Python 3.7 兼容写法

### 6.5 RhoDesign (端口 8006)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [ml4bio/RhoDesign](https://github.com/ml4bio/RhoDesign) |
| 微服务目录 | `microservices/rhodesign_service/` |
| 环境 | `python=3.9` + `pytorch=1.12.1` + `cudatoolkit=11.3.1` |
| 接口 | `GET /health`、`POST /design/from-structure` |
| Agent 工具 | `design_rna_sequence_with_rhodesign(pdb_filepath)` |

**关键注意事项**：
- 需要 `ss_apexp_best.pth` + `no_ss_apexp_best.pth` 在 `external_repos/RhoDesign/checkpoint/`
- PyG 依赖必须通过 `data.pyg.org` 安装匹配 wheel（`torch 1.12.1 + cu113`）
- 未提供 pdb 时默认回退到 `external_repos/RhoDesign/example/2zh6_B.pdb`

### 6.6 RNAsmol (端口 8007)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [hongli-ma/RNAsmol](https://github.com/hongli-ma/RNAsmol) |
| 微服务目录 | `microservices/rnasmol_service/` |
| 环境 | `environment.yml`（旧卡/CPU）或 `environment.gpu.yml`（RTX 4090 等新卡） |
| 接口 | `GET /health`、`POST /score` |
| Agent 工具 | `score_rna_ligand_binding_with_rnasmol(filepath, smiles)` |

**关键注意事项**：
- 新 GPU（RTX 4090）必须使用 `environment.gpu.yml`
- 旧版 `torch 1.7.1 + cu102` 在新卡上会卡住
- 可通过 `RNASMOL_DEVICE` 环境变量显式指定设备

### 6.7 RNASTOP (端口 8009)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [SII-ShenggengLin/RNASTOP](https://github.com/SII-ShenggengLin/RNASTOP.git) |
| 微服务目录 | `microservices/rnastop_service/` |
| 环境 | `python=3.10` + GPU + `transformers==4.34.0` |
| 接口 | `GET /health`、`POST /predict/stability` |
| Agent 工具 | `predict_mrna_stability_with_rnastop(filepath)` |

**关键注意事项**：
- 资源目录：`external_repos/RNASTOP/models/` + `DNABERT6/` + `RNA-FM_pretrained.pth`
- 服务端自动补齐 ViennaRNA 二级结构、loop type 和图特征
- 当前只封装稳定性预测，不封装 beam/MCTS 优化

### 6.8 GerNA-Bind (端口 8010)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [GENTEL-lab/GerNA-Bind](https://github.com/GENTEL-lab/GerNA-Bind) |
| 微服务目录 | `microservices/gernabind_service/` |
| 环境 | `pytorch 2.1.x + pytorch-cuda=11.8` + `install_pyg_gpu.sh` |
| 接口 | `GET /health`、`POST /score`、`POST /predict-binding-site` |
| Agent 工具 | `score_rna_ligand_binding_with_gernabind(filepath, smiles)` |

**关键注意事项**：
- checkpoint：`external_repos/GerNA-Bind/Model/Robin_random.pth`（affinity）
- 本地 RNA-FM：`external_repos/GerNA-Bind/Model/RNA-FM_pretrained.pth`
- 未提供 `pdb_path` 时自动调用 `rhofold_service` 补 3D 结构
- `Hariboss_Model_baseline.pth`（binding-site 用）需手动补齐
- 可通过 `GERNABIND_DEVICE` 环境变量指定设备

### 6.9 CRISOT (端口 8011)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [bm2-lab/CRISOT](https://github.com/bm2-lab/CRISOT.git) |
| 微服务目录 | `microservices/crisot_service/` |
| 环境 | 含 `cas-offinder`（Conda 安装） |
| 接口 | `GET /health`、`POST /score`、`POST /spec`、`POST /off-spec`、`POST /optimize` |

**Agent 工具函数**：
- `score_crispr_off_target_with_crisot(filepath, target_sequence)`
- `calculate_crispr_specificity_with_crisot(csv_filepath)`
- `search_crispr_off_targets_with_crisot(filepath, target_sequence, genome_path)`
- `optimize_sgrna_with_crisot(filepath, genome_path)`

**关键注意事项**：
- `score` / `spec` 不需要额外权重
- `off-spec` / `optimize` 依赖 `cas-offinder` + reference genome FASTA
- 可通过 `CRISOT_DEFAULT_REF_GENOME` 环境变量覆盖默认基因组
- `optimize` 在大基因组 + `mismatches=6` + CPU 下可能耗时数十分钟
- 已修复 `pandas>=2` 的 `DataFrame.append()` 兼容性问题

### 6.10 ODesign (端口 8012)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [OTeam-AI4S/ODesign](https://github.com/OTeam-AI4S/ODesign.git) |
| 微服务目录 | `microservices/odesign_service/` |
| 环境 | `python=3.10` + CUDA 12.1 |
| 接口 | `GET /health`、`POST /design/from-json` |
| Agent 工具 | `run_odesign_inference(input_json_filepath)` |

**支持模式**：显式 JSON 路径 / RNA backbone / protein-binding RNA

**关键注意事项**：
- checkpoint：`external_repos/ODesign/ckpt/odesign_base_na_rigid.pt` + `oinvfold_rna.ckpt`
- 数据文件：`external_repos/ODesign/data/components.v20240608.cif` + `.rdkit_mol.pkl`
- 复杂任务优先显式准备 JSON

### 6.11 IRESfinder (端口 8013)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [xiaofengsong/IRESfinder](https://github.com/xiaofengsong/IRESfinder.git) |
| 微服务目录 | `microservices/iresfinder_service/`（Python 3 重实现） |
| 环境 | `python=3.10` |
| 接口 | `GET /health`、`POST /predict` |
| Agent 工具 | `predict_putative_ires_with_iresfinder(filepath)` |

**关键注意事项**：需要 `external_repos/IRESfinder/module/train.data`

### 6.12 LinearDesign (端口 8014)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [LinearDesignSoftware/LinearDesign](https://github.com/LinearDesignSoftware/LinearDesign.git) |
| 微服务目录 | `microservices/lineardesign_service/` |
| 接口 | `GET /health`、`POST /generate/cds` |
| Agent 工具 | `design_mrna_cds_with_lineardesign(filepath)` |

**关键注意事项**：
- 部署后需在 `external_repos/LinearDesign/` 执行 `make` 生成 `bin/LinearDesign_2D`
- 可通过 `LINEARDESIGN_ROOT` 环境变量覆盖目录

### 6.13 LinearFold (端口 8015)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [LinearFold/LinearFold](https://github.com/LinearFold/LinearFold.git) |
| 微服务目录 | `microservices/linearfold_service/` |
| 接口 | `GET /health`、`POST /fold` |
| Agent 工具 | `predict_rna_secondary_structure_with_linearfold(filepath)` |

**关键注意事项**：
- 部署后需在 `external_repos/LinearFold/` 执行 `make` 生成 `bin/linearfold_c` + `bin/linearfold_v`
- 可通过 `LINEARFOLD_ROOT` 环境变量覆盖目录

### 6.14 Evitar (端口 8016)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [dingyaozhang/Evitar](https://github.com/dingyaozhang/Evitar.git) |
| 微服务目录 | `microservices/evitar_service/` |
| 接口 | `GET /health`、`POST /design` |
| Agent 工具 | `design_sirna_with_evitar(filepath)` |

**关键注意事项**：
- 上游 `bin/` 是 Linux 可执行文件，macOS 会报 `cannot execute binary file`
- **仅限 Linux 运行**

### 6.15 CRGPT / sgrna_design (端口 8017)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [bitguolab/sgrna_design](https://github.com/bitguolab/sgrna_design.git) |
| 微服务目录 | `microservices/sgrna_design_service/` |
| 接口 | `GET /health`、`POST /design` |
| Agent 工具 | `design_sgrna_handle_with_crgpt(filepath)` |

**关键注意事项**：
- 需要 `torch>=2.6`（`pytorch_model.bin` 加载安全限制）
- torch CUDA 版本需与服务器驱动匹配

### 6.16 codonw-slim (端口 8018)

| 项目 | 说明 |
|------|------|
| 上游仓库 | [smsaladi/codonw-slim](https://github.com/smsaladi/codonw-slim.git) |
| 微服务目录 | `microservices/codonw_slim_service/` |
| 环境 | `python=3.10` + gcc |
| 接口 | `GET /health`、`POST /analyze/cds` |
| Agent 工具 | `analyze_cds_codon_metrics_with_codonw_slim(filepath)` |

**关键注意事项**：
- **`conda env create` 后必须执行 `bash install_codonw_slim.sh`**
- 脚本解决两个问题：`pip` 隔离构建缺 Cython；上游 `astype(long)` → `astype(np.int64)` 兼容性
- 输入应为 in-frame CDS

### 6.17 RNA sequence metrics (端口 8020)

| 项目 | 说明 |
|------|------|
| 微服务目录 | `microservices/rna_sequence_metrics_service/` |
| 环境 | `python=3.10` + FastAPI（无第三方算法依赖） |
| 接口 | `GET /health`、`POST /gc-content`、`POST /unpaired-fraction` |
| Agent 工具 | `compute_rna_sequence_gc_content(filepath)`、`compute_dot_bracket_unpaired_fraction(filepath)` |

**关键注意事项**：

- GC：从文件中读取序列，规范化后统计 A/U/G/C，`gc_content = (G+C)/N`。
- 未配对比例：从文件中读取点括号串（仅允许 `. ( ) [ ] { } < >`），`unpaired_fraction = count('.')/length`。
- 自然语言可写 `structure=(((...)))` 写入 workspace 再调用；或提供 `workspace/*.ss` 等路径。

### 6.18 BLAST+ (端口 8019)

| 项目 | 说明 |
|------|------|
| 微服务目录 | `microservices/blast_service/` |
| 环境 | `python=3.10` + bioconda `blast` |
| 接口 | `GET /health`、`POST /blastn` |
| Agent 工具 | `run_blastn_similarity_search(filepath, subject_fasta_path=..., subject_db=...)` |

**关键注意事项**：
- `subject_fasta_path`（现场 `makeblastdb`）或 `subject_db`（已有库前缀）**二选一**
- 与历史 mock `off_target_blast` 不同：本服务是真实 BLAST 比对
- Agent 工具层会把完整结果写入 `workspace/blastn_out_*.tsv`

### 6.19 Mock 服务（已移除）

历史上曾存在两个用于开发调试的 siRNA mock 微服务（端口 8001/8002），用于返回随机的“效率分数/脱靶计数”以跑通早期工作流。

当前仓库已**移除**这两个入口；如需 siRNA 效率/脱靶的生产级实现，需要接入真实算法与数据库/基因组依赖。

---

## 7. LLM 配置状态

当前所有节点逻辑（Router / Specialist / Critic）均为**规则模式**，不依赖 LLM。

`.env` 和 `llm_config.py` 仍保留在代码中。后续恢复 LLM 建议做成配置开关：

```
USE_LLM_ROUTER=true/false
USE_LLM_SPECIALIST=true/false
USE_LLM_CRITIC=true/false
```

---

## 8. 部署与运行

### 8.1 开发机与运行机分离

| 环境 | 用途 |
|------|------|
| macOS | 代码编辑、提交 GitHub |
| Linux 服务器 | `git pull`、创建 Conda 环境、启动微服务、运行 Agent |

**Linux 服务器路径**：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`

### 8.2 微服务启动（通用模式）

```bash
cd rna_agent_system/microservices/<tool>_service
conda env create -f environment.yml      # 首次
conda activate <tool>_service_env
# 若有 install_*.sh，先执行
bash start.sh
```

### 8.3 需编译的服务

| 服务 | 编译步骤 |
|------|----------|
| LinearDesign | `cd external_repos/LinearDesign && make` |
| LinearFold | `cd external_repos/LinearFold && make` |
| codonw-slim | `bash microservices/codonw_slim_service/install_codonw_slim.sh` |

### 8.4 启动 Agent 前端

```bash
# 确保相关微服务已启动，然后从仓库根目录启动
streamlit run rna_agent_system/frontend/app.py --server.fileWatcherType none

# 远程 SSH 访问
streamlit run rna_agent_system/frontend/app.py \
  --server.fileWatcherType none \
  --server.address 0.0.0.0 \
  --server.port 8501
```

### 8.5 大文件 / 权重管理

以下文件不通过主仓库 Git 传输，需在服务器端单独准备：

| 工具 | 权重路径 |
|------|----------|
| GEMORNA | `external_repos/GEMORNA/checkpoints/*.pt` |
| RNARL | `external_repos/RNARL/checkpoints/*.pt` + `esm2_model_t33_650M_UR50D/` |
| RhoFold | `external_repos/RhoFold/pretrained/RhoFold_pretrained.pt` |
| RhoDesign | `external_repos/RhoDesign/checkpoint/*.pth` |
| RNAsmol | `external_repos/RNAsmol/saved_model/*.pt` |
| RNASTOP | `external_repos/RNASTOP/models/*` + `RNA-FM_pretrained.pth` + `DNABERT6/` |
| GerNA-Bind | `external_repos/GerNA-Bind/Model/*.pth` |
| ODesign | `external_repos/ODesign/ckpt/*.pt` + `ckpt/*.ckpt` + `data/components.*` |

---

## 9. 测试指南

### 9.1 测试顺序

**始终按三层依次验证**：

1. **微服务层**：`curl /health` → `curl` 业务接口
2. **Agent 工具层**：`tools.py` 中的函数
3. **前端集成**：Streamlit 自然语言输入

### 9.2 微服务 curl 示例

```bash
# ViennaRNA 二级结构
curl -sS -X POST http://127.0.0.1:8003/fold \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"GGGGAAAACCCC"}' | python3 -m json.tool

# GEMORNA CDS 设计
curl -sS -X POST http://127.0.0.1:8004/generate/cds \
  -H 'Content-Type: application/json' \
  -d '{"protein_sequence":"MNDTEAI"}' | python3 -m json.tool

# RhoFold 三级结构
curl -sS -X POST http://127.0.0.1:8005/predict \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"AUGGCUACGUAGCUAGCUAGCUAGCUGA","single_seq_pred":true,"relax_steps":0}' | python3 -m json.tool

# CRISOT 打分
curl -sS -X POST http://127.0.0.1:8011/score \
  -H 'Content-Type: application/json' \
  -d '{"sgrna":"GAGTCCGAGCAGAAGAAGAANGG","target_sequence":"GAGTCCGAGGAGAAGACGAAGGG"}' | python3 -m json.tool

# codonw-slim 密码子指标
curl -sS -X POST http://127.0.0.1:8018/analyze/cds \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"ATGAATATGCTCATTGTCGGTAGAGTTGTTGCTAGTGTTGGGGGAAGCGGACTTCAAACG"}' | python3 -m json.tool

# RNA sequence metrics（GC；未配对比例需服务器可读的结构文件路径）
curl -sS -X POST http://127.0.0.1:8020/gc-content \
  -H 'Content-Type: application/json' \
  -d '{"sequence_filepath":"rna_agent_system/workspace/blast_test_query.fa"}' | python3 -m json.tool
printf '%s\n' '(((....)))' > /tmp/rna_ss_example.txt
curl -sS -X POST http://127.0.0.1:8020/unpaired-fraction \
  -H 'Content-Type: application/json' \
  -d '{"structure_filepath":"/tmp/rna_ss_example.txt"}' | python3 -m json.tool

# BLAST
curl -sS -X POST http://127.0.0.1:8019/blastn \
  -H 'Content-Type: application/json' \
  -d '{"query_filepath":"rna_agent_system/workspace/blast_test_query.fa","subject_fasta_path":"rna_agent_system/workspace/blast_test_subject.fa","task":"blastn-short","evalue":10}' | python3 -m json.tool
```

### 9.3 Streamlit 自然语言测试用例

| 测试目的 | 输入示例 |
|----------|----------|
| 二级结构（ViennaRNA） | `请预测这条 RNA 的二级结构 fold：AUGCUAACGUAGCUAUGCUAUGCUAACGUAGCUAUGCUA` |
| siRNA duplex 结合能 | `ViennaRNA duplex rnacofold，sense=GGCAUGCAUGC antisense=GCAUGCAUGCC` |
| ASO 可及性 | `ASO accessibility plfold 可及性，region=10-50，靶标 mRNA：AUGCAUGCAUGC...`（≥50 nt） |
| 逆折叠 | `inverse fold 逆折叠 rnainverse，structure=((((....))))，repeats=5` |
| LinearFold | `fold linearfold 二级结构 AUGGCUACGUAGCUAGCUAGCUAGCUGA beam_size=20` |
| 密码子指标 | `codonw-slim 分析 CDS 密码子 CAI` + CDS 序列 |
| GC 含量 | `gc content 计算 GC 含量` + RNA 序列或 `workspace/*.fa` 路径 |
| 未配对比例 | `unpaired fraction 未配对比例 structure=(((....))))` 或 `workspace/*.ss` 点括号文件 |
| BLAST 搜索 | `blastn 比对 subject_fasta=workspace/test.fa 序列 ATGCATGCATGC` |

---

## 10. 代码与仓库管理规范

### 10.1 Submodule 管理

所有 `external_repos/` 下的第三方仓库通过 git submodule 管理：

```bash
# 新 clone
git clone --recurse-submodules <repo-url>

# 已有 clone
git pull && git submodule update --init --recursive
```

当前 submodule 列表：GEMORNA、GerNA-Bind、RNARL、RhoFold、RhoDesign、RNAsmol、RNASTOP、CRISOT、ODesign、IRESfinder、LinearDesign、LinearFold、Evitar、ViennaRNA、sgrna_design、codonw-slim

### 10.2 提交规范

**不要使用 `git add .`**，推荐：

```bash
git status --short
git submodule status
git add <具体文件>
git commit -m "meaningful message"
git push origin main
```

### 10.3 不应提交的内容

- `__pycache__/` / `*.pyc`
- `.DS_Store`
- `workspace/` 运行期输出
- 大权重文件（`*.pt` / `*.pth`）
- `.env`（含 API 密钥）

---

## 11. 新增工具标准流程

```
1. 克隆到 external_repos/（git submodule add）
2. 建 microservices/<tool>_service/
   ├── environment.yml
   ├── main.py         (FastAPI: GET /health + POST /...)
   ├── start.sh
   └── install_*.sh    (可选)
3. 在 agent_core/tools.py 新增 @tool 封装
4. 在 agent_core/nodes.py 接入 specialist + 解析逻辑
5. 在 agent_core/state.py 补新状态字段（如需）
6. 在 agent_core/graph.py 补节点和边（如需新增 specialist）
7. 测试顺序：原始命令 → 微服务接口 → Agent 调用
```

---

## 12. 已知限制与后续计划

### 当前限制

| 编号 | 限制 | 影响 |
|------|------|------|
| L1 | Router/Specialist/Critic 为规则模式 | 复杂自然语言理解有限 |
| L2 | Critic MFE 阈值 `-20.0` 对短序列不合理 | 短序列反复 reject 直到耗尽重试 |
| L3 | siRNA 效率/脱靶能力未提供生产实现 | 历史 mock（8001/8002）已移除，当前仅保留 Evitar/Vienna duplex 等非 mock 子能力 |
| L4 | RhoFold 仅单序列模式 | 未接 MSA 数据库 |
| L5 | RNASTOP 仅稳定性预测 | 未接 beam/MCTS 优化 |
| L6 | ODesign 自然语言覆盖有限 | 复杂任务仍需显式 JSON |
| L7 | 前端为最小可用调试界面 | 非产品级 UI |

### 后续计划

1. 保持规则模式，确保所有工具链稳定运行
2. 逐步替换 mock 服务为真实实现
3. 工具生态稳定后恢复可配置 LLM 模式
4. 引入更细的 specialist / 更强的 critic / 多工具串联规划
5. 优化前端结果展示与文件下载体验
