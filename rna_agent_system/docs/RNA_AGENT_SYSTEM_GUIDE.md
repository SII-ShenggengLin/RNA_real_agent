# RNA Design Multi-Agent System Guide

## 1. 文档目的

本文档用于说明当前 `RNA_real_agent` 项目的整体架构、已有能力、目录规范、部署方式，以及后续新增生信工具时的标准流程。

目标读者包括两类：

- 人类开发者：快速理解项目的设计思路、当前状态和后续开发方式
- 后续接手的大模型：读完后能够立即知道项目结构、工具接入方式、调试顺序和扩展规范

本文档描述的是**当前真实代码状态**，不是最初设想中的理想状态。

---

## 2. 项目目标

本项目希望实现一个 RNA 设计智能体系统：

- 输入：自然语言任务、RNA 序列、蛋白序列
- 输出：调用底层生信工具得到设计结果、评分结果、结构预测结果
- 方式：上层 Agent 负责路由与编排，下层工具通过本地微服务隔离运行

核心原则：

- 长序列不直接在 Agent 上下文中传递
- Agent 与工具之间尽量通过 `workspace/` 文件路径通信
- 复杂生信依赖与主 Agent 环境隔离
- 主 Agent 层只通过 HTTP API 调用工具，不直接耦合底层仓库实现

---

## 3. 当前架构总览

当前项目采用：

- `Agent orchestration`: `LangGraph`
- `UI`: `Streamlit`
- `Tool interface`: `LangChain @tool`
- `Tool runtime`: `FastAPI`
- `Dependency isolation`: `Conda environment + FastAPI`
- `External repos`: 放在 `external_repos/`，优先作为独立上游源码层管理

当前主逻辑已经从“LLM 驱动节点”切换为“**规则驱动节点**”，原因是当前阶段重点是验证工具链是否可接入，而不是验证 LLM 推理效果。

也就是说：

- `Router` 目前是规则判断
- `Specialist` 目前是规则触发工具调用
- `Critic` 目前是规则判定 pass / retry
- 后续在工具链稳定后，可以再切回可配置的 LLM 模式

---

## 4. 当前目录结构与职责

建议从内层应用根目录理解项目，也就是：

```text
rna_agent_system/
```

当前关键目录如下：

```text
rna_agent_system/
├── agent_core/                     # Agent 编排逻辑
├── frontend/                       # Streamlit 前端
├── microservices/                  # 我们维护的微服务封装层
├── external_repos/                 # 第三方源码仓库层
├── workspace/                      # 运行中间文件
├── docs/                           # 项目文档
└── .env                            # LLM 配置（当前可不用）
```

### 4.1 `agent_core/`

主要文件：

- `state.py`
  - 定义 `AgentState`
  - 记录 `messages`、`current_filepath`、`workspace_files`、`retry_count`、`active_specialist`、`mfe`、`cai_score` 等状态

- `file_manager.py`
  - `save_sequence(content, prefix)`
  - `read_sequence(filepath)`
  - 是整个项目“长序列走文件、不走 prompt”的核心基础设施

- `tools.py`
  - 把微服务 HTTP 接口封装为 Agent 工具
  - 当前主要工具：
    - `predict_sirna_efficiency`
    - `check_off_target`
    - `score_crispr_off_target_with_crisot`
    - `calculate_crispr_specificity_with_crisot`
    - `search_crispr_off_targets_with_crisot`
    - `optimize_sgrna_with_crisot`
    - `mock_codon_optimization`
    - `predict_rna_secondary_structure`
    - `design_mrna_cds_with_rnarl`
    - `design_mrna_cds_with_gemorna`

- `nodes.py`
  - Router / Specialist / Tool Execution / Critic 的核心逻辑
  - 当前是**规则模式**

- `graph.py`
  - 用 `LangGraph` 组装工作流图

### 4.2 `microservices/`

这里放的是**我们自己的服务封装**，而不是第三方原始仓库。

当前已有：

- `sirna_attsioff/`
  - Mock siRNA 效率预测服务
  - FastAPI
  - 默认端口 `8001`

- `off_target_blast/`
  - Mock 脱靶检查服务
  - FastAPI
  - 默认端口 `8002`

- `viennarna_fold/`
  - ViennaRNA 的二级结构 / MFE 预测服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8003`

- `gemorna_service/`
  - GEMORNA 的 mRNA CDS 设计服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8004`

- `rhofold_service/`
  - RhoFold 的 RNA 三级结构预测服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8005`
  - 当前默认走单序列预测模式，不依赖本地 MSA 数据库

- `rhodesign_service/`
  - RhoDesign 的 RNA structure-to-sequence 设计服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8006`
  - 输入是 `pdb`，可选 `secondary structure .npy`
  - 输出是预测 RNA 序列及对应 FASTA / 日志路径

- `rnasmol_service/`
  - RNAsmol 的 RNA-ligand 打分服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8007`
  - 输入是 RNA sequence + ligand SMILES
  - 输出是正类概率、预测标签、checkpoint 路径等摘要信息

- `rnarl_service/`
  - RNARL 的 protein-to-mRNA CDS 生成服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8008`
  - 当前采用的是**项目内自建推理封装**，但推理逻辑已按作者 `RNARL.ipynb` 对齐
  - 支持 7 个作者提供的 checkpoint：
    - `homo_mrna.pt`
    - `homo_circ.pt`
    - `Arabidopsis.pt`
    - `EscherichiaColi.pt`
    - `PC.pt`
    - `CR.pt`
    - `TK.pt`
  - 默认权重目录：
    - `rna_agent_system/external_repos/RNARL/checkpoints/`
    - `rna_agent_system/external_repos/RNARL/esm2_model_t33_650M_UR50D/`

- `rnastop_service/`
  - RNASTOP 的 mRNA 稳定性 / 降解预测服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8009`
  - 当前只封装**稳定性预测**，不封装上游仓库里的优化流程
  - 服务当前采用的是**项目内自建推理封装**
  - 会在服务层自动补齐：
    - ViennaRNA 二级结构
    - loop type
    - RNASTOP 所需图特征
  - 当前默认运行资源目录：
    - `rna_agent_system/external_repos/RNASTOP/models/`
    - `rna_agent_system/external_repos/RNASTOP/DNABERT6/`
    - `rna_agent_system/external_repos/RNASTOP/RNA-FM_pretrained.pth`

- `gernabind_service/`
  - GerNA-Bind 的 RNA-ligand 打分 / binding-site 预测服务
  - `environment.yml` + `main.py` + `start.sh`
  - 额外提供 `install_pyg_gpu.sh`
  - 默认端口 `8010`
  - 输入是 RNA sequence + ligand SMILES
  - 可选输入：
    - `pdb_path`
    - `secondary_structure`
    - `device`
  - 当前默认运行资源目录：
    - `rna_agent_system/external_repos/GerNA-Bind/Model/`
    - 其中会优先读取本地 `RNA-FM_pretrained.pth`

- `crisot_service/`
  - CRISOT 的 CRISPR off-target 打分 / specificity / sgRNA 优化服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8011`
  - 当前已封装接口：
    - `GET /health`
    - `POST /score`
    - `POST /spec`
    - `POST /off-spec`
    - `POST /optimize`
  - 当前实现直接调用上游 `crisot_modules.py`
  - 会绕开上游 `CRISOT.py` 对 `xgboost` 的顶层硬依赖

### 4.3 `external_repos/`

这里放第三方原始仓库。

当前已有：

- `GEMORNA/`
- `GerNA-Bind/`
- `RNARL/`
- `RNASTOP/`
- `RhoFold/`
- `RhoDesign/`
- `RNAsmol/`
- `CRISOT/`

**重要：**

- `external_repos/GEMORNA` 应作为 **git submodule** 管理
- `external_repos/GerNA-Bind` 也应作为 **git submodule** 管理
- `external_repos/RNASTOP` 也应作为 **git submodule** 管理
- `external_repos/RhoFold` 也应作为 **git submodule** 管理
- `external_repos/RhoDesign` 也建议作为 **git submodule** 管理
- `external_repos/CRISOT` 也应作为 **git submodule** 管理
- 不要把外部仓库当普通目录直接 `git add .`
- `NuFold` 曾被评估过，但当前不纳入正式接入路线，原因见后文

### 4.4 `workspace/`

存放运行中间文件，例如：

- 原始 RNA 序列
- 生成后的 CDS
- 结构字符串文件
- `RhoFold` 生成的 `pdb` / `ct` / `npz` / `log`
- `RhoDesign` 生成的 `fasta` / `stdout log` / `stderr log`
- `CRISOT` 生成的 specificity / optimization CSV
- 其他中间输出

所有长序列原则上都应先保存到 `workspace/`，然后在 Agent 内只传 `filepath`。

---

## 5. 当前智能体工作流逻辑

当前工作流图结构如下：

```text
User Input
  -> Router
  -> Specialist (siRNA or mRNA or CRISPR)
  -> Tool Execution
  -> Critic
  -> End 或回到对应 Specialist
```

### 5.1 Router

当前是**规则路由**，不调用 LLM。

基本逻辑：

- 如果文本中包含 `mrna`、`design`、`protein`、`cds`、`utr`、`structure`、`fold`、`gemorna`、`rhofold`、`rhodesign`、`rnasmol`、`rnastop`、`gernabind`、`gerna-bind`、`stability`、`degradation`、`稳定性`、`降解`、`smiles`、`ligand`、`配体`、`pdb`、`cif`、`3d`、`tertiary`、`三级结构`、`三维结构` 等关键词
  - 路由到 `mrna_specialist`
- 如果包含 `crisot`、`crispr`、`cas9`、`sgrna`、`guide rna`、`off-spec`
  - 路由到 `crispr_specialist`
- 如果包含 `sirna`、`脱靶`、`off-target`
  - 路由到 `sirna_specialist`
- 默认也偏向 `mrna_specialist`

### 5.2 siRNA Specialist

规则式地产生两个工具调用：

- `predict_sirna_efficiency(filepath)`
- `check_off_target(filepath)`

### 5.3 mRNA Specialist

分六种模式：

- 如果用户文本显式提到 `GerNA-Bind` / `gernabind`
  - 触发 `score_rna_ligand_binding_with_gernabind(filepath, smiles, checkpoint_path=None, pdb_path=None, secondary_structure=None, device=None)`
  - 输入是 RNA 序列文件路径 + ligand `SMILES`
  - 当前规则解析优先要求用户在文本里显式给出：
    - `SMILES=...`
    - 或 `SMILES: ...`
  - RNA 输入可以是：
    - 文本中的 RNA 序列
    - 或 `.fasta/.fa/.txt/.seq` 文件路径
  - 当前还支持从自然语言中额外解析：
    - `.pdb/.cif` 路径
    - `secondary_structure=...`
    - `dot-bracket=...`
    - `二级结构=...`
  - 如果未提供 `pdb_path`，服务端会自动调用 `rhofold_service`
  - 如果未提供二级结构，服务端会自动补齐 ViennaRNA 2D 结构

- 如果用户文本偏“RNA-ligand 打分型”
  - 触发 `score_rna_ligand_binding_with_rnasmol(filepath, smiles, checkpoint_path=None)`
  - 输入是 RNA 序列文件路径 + ligand `SMILES`
  - 当前规则解析优先要求用户在文本里显式给出：
    - `SMILES=...`
    - 或 `SMILES: ...`
  - RNA 输入可以是：
    - 文本中的 RNA 序列
    - 或 `.fasta/.fa/.txt/.seq` 文件路径
  - 如果未提供 `SMILES`，当前会直接报错，而不是猜测

- 如果用户文本偏“mRNA 稳定性 / 降解预测型”
  - 触发 `predict_mrna_stability_with_rnastop(filepath, checkpoint_path=None, device=None)`
  - 输入是 RNA 序列文件路径
  - RNA 输入可以是：
    - 文本中的 RNA 序列
    - 或 `.fasta/.fa/.txt/.seq` 文件路径
  - 当前服务端会自动补齐：
    - `structure`
    - `loop_type`
    - RNASTOP 图特征
  - 当前返回的核心摘要包括：
    - `mean_reactivity`
    - `mean_deg_Mg_pH10`
    - `mean_deg_Mg_50C`
  - 当前不会触发 RNASTOP 上游仓库里的 beam / MCTS 优化逻辑

- 如果用户文本偏“结构到序列设计型”
  - 触发 `design_rna_sequence_with_rhodesign(pdb_filepath, secondary_structure_filepath=None)`
  - 输入是 `pdb` 文件路径
  - 如果用户文本里给了 `.npy` 路径，则自动走带 2D 约束的模式
  - 如果没有提供结构文件，当前会回退到 `external_repos/RhoDesign/example/2zh6_B.pdb` 作为默认调试输入

- 如果用户文本偏“设计型”
  - 触发 `design_mrna_cds_with_gemorna(filepath)`
  - 输入文件保存的是蛋白序列
  - 如果用户请求里还包含结构语义，当前会在 GEMORNA 设计完成后继续自动调用结构预测工具
- 如果用户文本偏“结构预测型”
  - 触发：
    - `mock_codon_optimization(filepath)`
    - `predict_rna_secondary_structure(filepath)`
  - 如果用户文本里还包含 `rhofold`、`3d`、`tertiary`、`三级结构`、`三维结构`、`pdb`
    - 还会额外触发 `predict_rna_tertiary_structure_with_rhofold(filepath)`

另外，如果先做了 `GEMORNA` 设计，而用户请求中又包含结构预测语义，当前 `tool_execution_node` 会在拿到 GEMORNA 输出后，继续自动调用：

- `predict_rna_secondary_structure`
- `predict_rna_tertiary_structure_with_rhofold`

### 5.3A CRISPR Specialist

当前新增 `crispr_specialist`，主要负责 `CRISOT` 相关请求。

- 如果用户文本偏单对打分语义
  - 触发 `score_crispr_off_target_with_crisot(filepath, target_sequence)`
- 如果用户文本偏 CSV specificity 语义
  - 触发 `calculate_crispr_specificity_with_crisot(csv_filepath)`
- 如果用户文本里给了 `genome`，并带有 `spec` / `off-spec` / `cas-offinder` 语义
  - 触发 `search_crispr_off_targets_with_crisot(filepath, target_sequence, genome_path, mismatches=6, device="C")`
- 如果用户文本里带有 `optimize` / `optimization` / `优化` / `降低脱靶`
  - 触发 `optimize_sgrna_with_crisot(filepath, genome_path, threshold=0.8, mismatches=6, device="C")`

当前规则解析支持：

- `sgRNA=...`
- `target=...`
- `genome=/path/to/genome.fa`
- `threshold=0.8`
- `mm=3`
- `device=C`

### 5.4 Tool Execution

负责真正执行工具调用，并把结果写回 `AgentState`。

当前会更新的关键状态包括：

- `current_filepath`
- `workspace_files`
- `candidate_sequence`
- `efficiency_score`
- `off_target_genes`
- `crisot_score`
- `crisot_spec`
- `crisot_target_sequence`
- `crisot_input_csv_filepath`
- `crisot_output_csv_filepath`
- `crisot_genome_path`
- `crisot_off_target_count`
- `crisot_optimization_csv_filepath`
- `crisot_optimized_sgrna_filepath`
- `crisot_best_mutation`
- `crisot_best_delta_spec`
- `crisot_optimized_available`
- `cai_score`
- `mfe`
- `structure_filepath`
- `design_input_pdb_filepath`
- `design_input_secondary_structure_filepath`
- `designed_sequence_fasta_filepath`
- `sequence_recovery_rate`
- `tertiary_structure_filepath`
- `tertiary_structure_ct_filepath`
- `tertiary_results_filepath`
- `tertiary_log_filepath`
- `mean_plddt`
- `ligand_smiles`
- `gernabind_probability`
- `gernabind_predicted_label`
- `gernabind_checkpoint_path`
- `gernabind_preprocessing_pdb_path`
- `rnasmol_probability`
- `rnasmol_predicted_label`
- `rnasmol_checkpoint_path`
- `rnastop_prediction_filepath`
- `rnastop_mean_reactivity`
- `rnastop_mean_deg_mg_ph10`
- `rnastop_mean_deg_mg_50c`
- `rnastop_mfe`
- `rnastop_checkpoint_path`

### 5.5 Critic

当前是**规则 Critic**，不调用 LLM。

逻辑：

- siRNA：
  - 如果 `off_target_genes > 0`，则 reject 并重试
- mRNA 结构预测：
  - 如果用户请求里有结构相关语义，并且 `mfe > -20.0`，则 reject 并重试
- `RhoDesign` 结构到序列设计：
  - 当前不走基于 `mfe` 的 reject 规则
  - 只要微服务成功返回即可 pass
- 否则 pass

最大重试次数：

- `max_retries = 3`

---

## 6. 当前工具与端口分配

建议维持固定端口表：

- `8001`: `sirna_attsioff`
- `8002`: `off_target_blast`
- `8003`: `viennarna_fold`
- `8004`: `gemorna_service`
- `8005`: `rhofold_service`
- `8006`: `rhodesign_service`
- `8007`: `rnasmol_service`
- `8008`: `rnarl_service`
- `8009`: `rnastop_service`
- `8010`: `gernabind_service`
- `8011`: `crisot_service`

后续新增工具也建议继续顺延，例如：

- `8012`: 新工具 A
- `8013`: 新工具 B

这样主 Agent 层的工具地址稳定，不会频繁冲突。

---

## 7. LLM 当前状态

### 7.1 当前代码状态

虽然项目里仍保留 `.env` 和 `llm_config.py`，但**当前节点逻辑已经切换为规则模式**，暂时不依赖 LLM。

这样做的原因：

- 现在的重点是验证复杂工具链接入
- 工具接入阶段如果 LLM 不稳定，会增加调试噪音
- 先保证规则编排 + 工具链跑通，再恢复 LLM 更合理

### 7.2 未来如何恢复 LLM

建议后续做成配置开关，例如：

- `USE_LLM_ROUTER=true/false`
- `USE_LLM_SPECIALIST=true/false`
- `USE_LLM_CRITIC=true/false`

这样可以：

- 工具调试阶段用规则
- 产品化阶段再切回 LLM

---

## 8. ViennaRNA 的接入方式

ViennaRNA 已经成功接入，作为“真实工具接入模板”。

### 8.1 微服务层

目录：

```text
microservices/viennarna_fold/
```

文件：

- `environment.yml`
- `main.py`
- `start.sh`

接口：

- `GET /health`
- `POST /fold`

输入：

- `sequence`

输出：

- `structure`
- `mfe`

### 8.2 Agent 工具层

工具函数：

- `predict_rna_secondary_structure(filepath, service_url="http://localhost:8003/fold")`

当前返回格式是字符串：

```text
filepath=...; structure=...; mfe=...
```

之后如果需要更稳健，建议改成 JSON 风格的结构化返回。

---

## 9. GEMORNA 的接入方式

### 9.1 上游源码层

目录：

```text
external_repos/GEMORNA
```

来源：

- 上游仓库：[RainaBio/GEMORNA](https://github.com/RainaBio/GEMORNA)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库直接 vendoring 进主仓库历史

### 9.2 当前微服务能力

目录：

```text
microservices/gemorna_service/
```

当前已封装接口：

- `POST /generate/cds`

输入：

- `protein_sequence`

输出：

- `generated_sequence`
- `raw_output`

### 9.3 当前 Agent 工具能力

工具函数：

- `design_mrna_cds_with_gemorna(filepath, service_url="http://127.0.0.1:8004/generate/cds")`

输入：

- `filepath`，其中保存的是蛋白序列

输出：

- `generated_sequence`
- `output_filepath`
- `raw_output`

### 9.4 GEMORNA 的实际运行注意事项

这是当前最重要的工程细节之一。

#### 权重文件

`GEMORNA` 的 `checkpoints/*.pt` 很大，且原仓库通过 Git LFS 管理。

两种可行策略：

- 策略 A：服务器上执行 `git lfs pull`
- 策略 B：手动把真实 `.pt` 文件放入：

```text
external_repos/GEMORNA/checkpoints/
```

当前项目已经支持这两种方式。

如果 checkpoint 仍然是 LFS pointer，`gemorna_service/main.py` 会主动报错提示。

#### Python 版本

`GEMORNA` 官方环境要求：

- `python=3.10`

**不要用 `py39` 跑 GEMORNA。**

原因：

- 它依赖预编译的 `.so` 二进制扩展
- Python ABI 不匹配时会出现类似：
  - `undefined symbol: PyDescr_IsData`

因此 `gemorna_service` 一定要在独立 `python=3.10` 环境中运行。

#### Linux 优先

`GEMORNA` 更适合在 Linux 服务器上运行，特别是带 GPU 的环境。

你当前实际的推荐运行环境是：

- Linux
- Conda
- Python 3.10
- NVIDIA GPU（例如 4090）

---

## 9A. RNARL 的接入方式

### 9A.1 上游源码层

目录：

```text
external_repos/RNARL
```

来源：

- 上游仓库：[SII-ShenggengLin/RNARL](https://github.com/SII-ShenggengLin/RNARL.git)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库直接 vendoring 进主仓库历史

### 9A.2 为什么当前采用“项目内推理封装”

当前接入的 RNARL 不是直接调用上游训练脚本，而是采用：

- 保留上游源码与 `utils.py` / `transformer_encoder_MoE.py`
- 在 `microservices/rnarl_service/` 中按作者 `RNARL.ipynb` 重建推理流程

这样做的原因是：

- 上游仓库主体更偏训练代码
- `actor_train.py` / `grpo_train.py` 并不适合作为稳定在线推理入口
- 作者公开 notebook 已给出实际可运行的推理路径与 checkpoint 命名方式

### 9A.3 当前微服务能力

目录：

```text
microservices/rnarl_service/
```

当前已封装接口：

- `GET /health`
- `GET /models`
- `POST /generate/cds`

输入：

- `protein_sequence`
- `model_type`
- `checkpoint_path`（可选）
- `esm2_model_path`（可选）
- `device`（可选）

输出：

- `generated_sequence`
- `model_type`
- `checkpoint_path`
- `esm2_model_path`
- `device`

### 9A.4 当前 Agent 工具能力

工具函数：

- `design_mrna_cds_with_rnarl(filepath, service_url="http://127.0.0.1:8008/generate/cds", model_type="Homo sapiens mRNA")`

输入：

- `filepath`，其中保存的是蛋白序列
- `model_type`，当前支持 7 种作者 notebook 中给出的模型类型

输出：

- `generated_sequence`
- `output_filepath`
- `model_type`
- `checkpoint_path`
- `esm2_model_path`

### 9A.5 当前支持的 RNARL 模型类型

当前已按作者 notebook 对齐以下 7 个 checkpoint：

- `Homo sapiens mRNA` -> `homo_mrna.pt`
- `Homo sapiens circular RNA` -> `homo_circ.pt`
- `Arabidopsis thaliana mRNA` -> `Arabidopsis.pt`
- `Escherichia coli mRNA` -> `EscherichiaColi.pt`
- `Penicillium chrysogenum mRNA` -> `PC.pt`
- `Chlamydomonas reinhardtii mRNA` -> `CR.pt`
- `Thermococcus kodakarensis KOD1 mRNA` -> `TK.pt`

### 9A.6 RNARL 的实际运行注意事项

#### 权重与模型目录放置位置

当前默认目录为：

```text
external_repos/RNARL/checkpoints/
external_repos/RNARL/esm2_model_t33_650M_UR50D/
```

也就是在当前项目里对应：

```text
rna_agent_system/external_repos/RNARL/checkpoints/
rna_agent_system/external_repos/RNARL/esm2_model_t33_650M_UR50D/
```

说明：

- `checkpoints/` 放 RNARL 的 `.pt` 权重
- `esm2_model_t33_650M_UR50D/` 放本地 ESM-2 模型目录
- 这两个目录属于**运行时资源目录**
- 默认不会跟随 Git 自动创建空目录

#### ESM-2 必须使用本地目录

当前实现采用：

- `AutoTokenizer.from_pretrained(local_path, local_files_only=True)`
- `EsmModel.from_pretrained(local_path, local_files_only=True)`

也就是说：

- 传入的是**目录路径**
- 不是单个 `model.safetensors` 文件路径

#### checkpoint 文件必须是真实权重

当前已验证过一个非常常见的问题：

- 如果 `*.pt` 实际上是 Git LFS pointer 或错误下载得到的文本文件
- 推理时会出现：
  - `invalid load key, 'v'`

因此部署时必须确认：

- `.pt` 文件是真实二进制权重
- 文件大小为几百 MB 量级
- 不是只包含 `version https://git-lfs.github.com/spec/v1` 的 pointer 文件

#### checkpoint 加载兼容性

当前 `rnarl_service/main.py` 已兼容两类加载方式：

- 先尝试 `torch.load(..., weights_only=True)`
- 如果作者 checkpoint 不兼容，再回退到 `weights_only=False`

同时支持以下 checkpoint 结构：

- 原始 `state_dict`
- `state_dict`
- `model_state_dict`
- `model`

#### 推荐运行环境

当前实际验证通过的运行方式是：

- Linux
- Conda
- Python 3.10
- GPU 环境下运行 `EsmModel + RNARL actor`

### 9A.7 当前验证状态

RNARL 目前已经在 Linux 服务器上完成最小闭环验证：

- `rnarl_service` 成功启动
- `GET /health` 成功
- `GET /models` 可返回 7 个模型类型
- `POST /generate/cds` 成功
- 已成功返回 `generated_sequence`
- 已确认默认读取：
  - `rna_agent_system/external_repos/RNARL/checkpoints/homo_mrna.pt`
  - `rna_agent_system/external_repos/RNARL/esm2_model_t33_650M_UR50D/`

这意味着：

- RNARL 已经通过“作者 notebook 推理逻辑 -> 项目微服务封装 -> Linux 实际推理”这一层验证
- 后续如果再次报错，优先检查的应该是：
  - checkpoint 是否为真实权重
  - ESM2 本地目录是否完整
  - `model_type` 是否与 checkpoint 对应
  - GPU / 环境是否正常

---

## 10. RhoFold 的接入方式

### 10.1 上游源码层

目录：

```text
external_repos/RhoFold
```

来源：

- 上游仓库：[ml4bio/RhoFold](https://github.com/ml4bio/RhoFold)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库直接 vendoring 进主仓库历史

### 10.2 为什么当前采用 RhoFold 而不是 NuFold

`NuFold` 已做过前期评估，但当前不作为正式接入方案，主要原因是：

- 它更强依赖外部前处理链路
- 需要 `rMSA`
- 需要 `IPknot`
- `rMSA` 数据库量级约 `~2TB`
- 原始脚本更偏向固定 `CUDA` 运行，工程接入门槛更高

相对而言，`RhoFold` 当前更适合本项目：

- 支持 **single sequence prediction**
- 可以先不接本地 MSA 数据库
- 已在 Linux + GPU 服务器上成功跑通微服务接口
- 更适合作为当前阶段“真实 3D RNA 结构工具”的第一接入点

### 10.3 当前微服务能力

目录：

```text
microservices/rhofold_service/
```

当前已封装接口：

- `GET /health`
- `POST /predict`

输入：

- `sequence`
- `single_seq_pred`，当前默认 `true`
- `checkpoint_path`（可选）
- `device`（可选）
- `relax_steps`

输出：

- `output_pdb_path`
- `secondary_structure_ct_path`
- `results_npz_path`
- `log_path`
- `service_output_dir`
- `mean_plddt`

### 10.4 当前 Agent 工具能力

工具函数：

- `predict_rna_tertiary_structure_with_rhofold(filepath, service_url="http://127.0.0.1:8005/predict", relax_steps=0)`

输入：

- `filepath`，其中保存的是 RNA 序列

输出：

- `output_pdb_filepath`
- `secondary_structure_ct_filepath`
- `results_npz_filepath`
- `log_filepath`
- `mean_plddt`

当前实现会把 `RhoFold` 生成的关键结果文件复制回主项目 `workspace/`，这样上层 Agent 仍然只传 `filepath`，不直接在消息里搬运大结果。

### 10.5 RhoFold 的实际运行注意事项

#### Python 与依赖版本

当前 `rhofold_service` 的环境固定为：

- `python=3.7.12`
- `pytorch=1.10.2`
- `cudatoolkit=11.3.1`
- `fastapi==0.95.2`
- `pydantic==1.10.13`
- `uvicorn==0.22.0`

这样做的原因是：

- 上游 `RhoFold` 环境本身偏旧
- 新版 `pydantic` / `fastapi` 组合在 `python=3.7` 下更容易出现兼容性问题
- 当前微服务代码已专门改成 Python 3.7 兼容写法

#### checkpoint

微服务当前会优先检查这些路径：

```text
external_repos/RhoFold/pretrained/RhoFold_pretrained.pt
external_repos/RhoFold/pretrained/rhofold_pretrained_params.pt
external_repos/RhoFold/pretrained/model_20221010_params.pt
```

如果推理时可以正常访问 Hugging Face，部分依赖文件会自动拉取；如果自动下载失败，建议直接手动把权重放到：

```text
external_repos/RhoFold/pretrained/RhoFold_pretrained.pt
```

#### 单序列模式优先

当前推荐部署方式是：

- `single_seq_pred=true`
- 不接本地 MSA 数据库

原因：

- 接入成本低
- 已能产生有效的 3D 结构结果
- 适合当前项目阶段的“工具先跑通”目标

如果后续需要更高精度，再单独扩展：

- 用户自带 `.a3m`
- 或服务器本地维护数据库并启用 MSA 模式

### 10.6 当前验证状态

`RhoFold` 微服务已在 Linux + GPU 服务器上完成最小闭环验证：

- `POST /predict` 成功
- `cuda:0` 推理成功
- 成功生成 `unrelaxed_model.pdb`
- 成功生成 `ss.ct`
- 成功生成 `results.npz`
- 成功生成 `log.txt`
- 已成功返回 `mean_plddt`

这意味着：

- `RhoFold` 已经通过“上游命令封装 -> 微服务接口”这一层验证
- 后续如果 Agent 集成侧报错，优先怀疑的是编排层或环境层，不再是 `RhoFold` 本体是否能跑

---

## 10A. RhoDesign 的接入方式

### 10A.1 上游源码层

目录：

```text
external_repos/RhoDesign
```

来源：

- 上游仓库：[ml4bio/RhoDesign](https://github.com/ml4bio/RhoDesign)

当前建议：

- 优先通过 **git submodule** 管理
- 不要把整个上游仓库直接 vendoring 进主仓库历史

### 10A.2 当前微服务能力

目录：

```text
microservices/rhodesign_service/
```

当前已封装接口：

- `GET /health`
- `POST /design/from-structure`

输入：

- `pdb_path`
- `secondary_structure_path`（可选，`.npy`）
- `temperature`
- `device`

输出：

- `output_fasta_path`
- `predicted_sequence`
- `recovery_rate`
- `service_output_dir`
- `checkpoint_path`
- `stdout`
- `stderr`

### 10A.3 当前 Agent 工具能力

工具函数：

- `design_rna_sequence_with_rhodesign(pdb_filepath, secondary_structure_filepath=None, service_url="http://127.0.0.1:8006/design/from-structure")`

输入：

- `pdb_filepath`
- `secondary_structure_filepath`（可选）

输出：

- `predicted_sequence`
- `output_filepath`
- `output_fasta_filepath`
- `recovery_rate`
- `stdout_filepath`
- `stderr_filepath`

当前实现会把 `RhoDesign` 生成的关键结果复制回主项目 `workspace/`，这样上层 Agent 仍然只保留路径，不直接搬运大结果内容。

### 10A.4 当前工作流集成方式

当前 `Router / mRNA specialist / tool_execution` 已经接入 `RhoDesign`：

- `router_node` 会识别 `rhodesign`、`pdb`、`cif`、`结构到序列` 等语义
- `mrna_specialist_node` 会优先把这类请求路由到 `RhoDesign`
- 如果文本中带有 `.npy` 路径，会自动把它作为 `secondary_structure_filepath`
- 如果用户没有提供结构文件，当前默认回退到：

```text
rna_agent_system/external_repos/RhoDesign/example/2zh6_B.pdb
```

当前 `tool_execution_node` 还会更新这些额外状态：

- `design_input_pdb_filepath`
- `design_input_secondary_structure_filepath`
- `designed_sequence_fasta_filepath`
- `sequence_recovery_rate`

### 10A.5 RhoDesign 的实际运行注意事项

#### 运行环境

当前实际验证通过的运行方式是：

- Linux
- NVIDIA GPU
- Conda
- Python 3.9
- PyTorch 1.12.1 + `cudatoolkit=11.3.1`

注意：

- 即使服务器宿主机是 CUDA 12.x，也**不需要**把 `RhoDesign` 环境强行升到 `cu12x`
- 当前更稳的做法是：宿主机驱动较新，Conda 环境内部仍然维持 `torch 1.12.1 + cu113`

#### checkpoint

当前需要至少准备这两个权重：

```text
external_repos/RhoDesign/checkpoint/ss_apexp_best.pth
external_repos/RhoDesign/checkpoint/no_ss_apexp_best.pth
```

说明：

- `ss_apexp_best.pth` 用于带 2D 输入的模式
- `no_ss_apexp_best.pth` 用于仅 `pdb` 输入的模式

#### PyG 依赖安装方式

`RhoDesign` 依赖：

- `torch-scatter`
- `torch-sparse`
- `torch-cluster`
- `torch-spline-conv`
- `torch-geometric`

这组依赖不建议直接放进 `conda env create` 的 `pip:` 列表里一起装。

当前实际验证通过的做法是：

1. 先创建基础 Conda 环境，只安装 `torch 1.12.1 + cu113`
2. 再单独通过 `data.pyg.org` 安装匹配 wheel

当前已验证可用的版本组合为：

```bash
pip install --no-cache-dir \
  torch-scatter==2.1.0+pt112cu113 \
  torch-sparse==0.6.16+pt112cu113 \
  torch-cluster==1.6.0+pt112cu113 \
  torch-spline-conv==1.2.1+pt112cu113 \
  -f https://data.pyg.org/whl/torch-1.12.1+cu113.html

pip install --no-cache-dir torch-geometric==2.5.0
```

原因：

- 如果直接装不匹配的版本，`pip` 可能回退到源码构建
- 回退到源码构建后，常见报错是 build isolation 阶段的 `ModuleNotFoundError: No module named 'torch'`

#### 路径解析注意事项

当前 `rhodesign_service` 已专门兼容以下路径形式：

- 绝对路径
- `rna_agent_system/...`
- `external_repos/...`
- `workspace/...`

这样做的原因是：

- 前端自然语言请求里经常会直接写 `rna_agent_system/external_repos/...`
- 如果微服务只按单一路径前缀拼接，容易出现 `rna_agent_system/rna_agent_system/...` 这种错误路径

#### Python 3.9 兼容性

主 Agent 当前常用环境仍是 `py39`。

因此在 `agent_core/` 里新增类型注解时，要避免直接写：

- `str | None`
- `tuple[str, ...]`

更稳妥的写法是：

- `Optional[str]`
- `Tuple[str, ...]`

否则在 `py39 + pydantic` 环境里可能导致前端启动阶段直接报错。

### 10A.6 当前验证状态

`RhoDesign` 目前已经在 Linux + GPU 服务器上完成最小闭环验证：

- 微服务环境创建成功
- `PyG` 依赖安装成功
- `GET /health` 成功
- `POST /design/from-structure` 成功
- 前端自然语言请求已成功触发 `RhoDesign`
- Agent 集成链路已能返回设计结果

这意味着：

- `RhoDesign` 已经通过“上游命令封装 -> 微服务接口 -> Agent 工作流”这一层验证
- 后续如果再次出现报错，优先检查的应该是环境漂移、路径输入、或部署流程，而不是先怀疑 `RhoDesign` 主体不能跑

---

## 10B. RNAsmol 的接入方式

### 10B.1 上游源码层

目录：

```text
external_repos/RNAsmol
```

来源：

- 上游仓库：[hongli-ma/RNAsmol](https://github.com/hongli-ma/RNAsmol)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 `git add .`

### 10B.2 当前微服务能力

目录：

```text
microservices/rnasmol_service/
```

当前已封装接口：

- `GET /health`
- `POST /score`

输入：

- `rna_sequence`
- `smiles`
- `checkpoint_path`（可选）
- `device`（可选）

输出：

- `probability_positive`
- `predicted_label`
- `raw_logits`
- `checkpoint_path`
- `device`

### 10B.3 当前 Agent 工具能力

工具函数：

- `score_rna_ligand_binding_with_rnasmol(filepath, smiles, service_url="http://127.0.0.1:8007/score", checkpoint_path=None)`

输入：

- `filepath`，其中保存的是 RNA 序列
- `smiles`

输出：

- `probability_positive`
- `predicted_label`
- `checkpoint_path`
- `input_filepath`

当前实现会把 RNA 输入仍然统一落到 `workspace/` 文件路径，再由 Agent 工具通过 HTTP 调用 `RNAsmol` 微服务。

### 10B.4 当前工作流集成方式

当前 `Router / mRNA specialist / tool_execution` 已经接入 `RNAsmol`：

- `router_node` 会识别 `rnasmol`、`smiles`、`ligand`、`配体` 等语义
- `mrna_specialist_node` 会优先把这类请求路由到 `RNAsmol`
- 当前支持两种 RNA 输入方式：
  - 直接在文本里给 RNA 序列
  - 直接给 `.fasta/.fa/.txt/.seq` 路径
- 当前 `SMILES` 建议显式写成：
  - `SMILES=...`
  - 或 `SMILES: ...`

当前 `tool_execution_node` 还会更新这些额外状态：

- `ligand_smiles`
- `rnasmol_probability`
- `rnasmol_predicted_label`
- `rnasmol_checkpoint_path`

### 10B.5 RNAsmol 的实际运行注意事项

#### checkpoint

当前 `RNAsmol` 服务默认会优先检查：

```text
external_repos/RNAsmol/saved_model/*.pt
```

如果不想使用默认目录，也可以在启动服务前设置：

```bash
export RNASMOL_CHECKPOINT_PATH=/absolute/path/to/model.pt
```

#### 4090 / 新卡 GPU 兼容性

`RNAsmol` 上游原始环境更偏旧，例如：

- `python=3.7`
- `pytorch=1.7.1`
- `cudatoolkit=10.2`

这套组合在较新的 GPU（例如 `RTX 4090`, `sm_89`）上并不稳妥，常见现象包括：

- `torch.cuda.is_available()` 为 `True`
- 但真正执行 CUDA tensor 或模型推理时卡住
- 控制台提示 `sm_89 is not compatible with the current PyTorch installation`

因此当前项目里实际采用的是两套并行方案：

- `environment.yml`
  - 偏旧版本组合
  - 可作为 CPU 或旧卡兼容方案
- `environment.gpu.yml`
  - 面向新 GPU 的独立环境
  - 当前实际用于 `RTX 4090` 成功跑通

#### 设备选择

当前 `rnasmol_service/main.py` 支持：

- 请求体里显式传 `device`
- 或启动服务前设置环境变量：

```bash
export RNASMOL_DEVICE=cpu
export RNASMOL_DEVICE=cuda:0
```

服务默认逻辑是：

- 如果设置了 `RNASMOL_DEVICE`，优先使用它
- 否则自动退回到：
  - 有 CUDA 就用 `cuda:0`
  - 没 CUDA 就用 `cpu`

### 10B.6 当前验证状态

`RNAsmol` 目前已经在 Linux 服务器上完成最小闭环验证：

- 上游源码已成功以 submodule 形式接入
- `rnasmol_service` 已成功启动
- `GET /health` 成功
- checkpoint 已成功识别
- `POST /score` 在 `cpu` 模式成功
- `POST /score` 在 `RTX 4090 + 独立 GPU 环境` 下成功
- Agent 自然语言请求已成功触发 `RNAsmol`
- Agent 最终报告已能返回 `rnasmol_probability` 等字段

这意味着：

- `RNAsmol` 已经通过“上游源码 -> 微服务接口 -> Agent 工作流”这一层验证
- 后续如果再次报错，优先检查的应该是：
  - checkpoint 路径
  - PyG 版本匹配
  - GPU 环境是否使用了 `environment.gpu.yml`
  - `RNASMOL_DEVICE` 是否配置正确

---

## 10C. RNASTOP 的接入方式

### 10C.1 上游源码层

目录：

```text
external_repos/RNASTOP
```

来源：

- 上游仓库：[SII-ShenggengLin/RNASTOP](https://github.com/SII-ShenggengLin/RNASTOP.git)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 vendoring 进主仓库历史

### 10C.2 为什么当前采用“项目内推理封装”

当前接入的 RNASTOP 不是直接调用上游训练 / 分析脚本，而是采用：

- 保留上游源码仓库
- 在 `microservices/rnastop_service/` 中重建单条序列稳定性预测推理流程

这样做的原因是：

- 上游仓库没有直接提供适合 Agent 调用的单条序列 REST 入口
- 上游脚本更偏训练、分析和论文复现实验
- 当前项目只需要“mRNA 稳定性 / 降解预测”，不需要优化模块

### 10C.3 当前微服务能力

目录：

```text
microservices/rnastop_service/
```

当前已封装接口：

- `GET /health`
- `POST /predict/stability`

输入：

- `sequence`
- `checkpoint_path`（可选）
- `rnafm_model_path`（可选）
- `dnabert_model_path`（可选）
- `structure`（可选）
- `loop_type`（可选）
- `device`（可选）

输出：

- `mean_reactivity`
- `mean_deg_Mg_pH10`
- `mean_deg_Mg_50C`
- `per_position_predictions`
- `structure`
- `loop_type`
- `mfe`
- `checkpoint_path`
- `rnafm_model_path`
- `dnabert_model_path`
- `use_dnabert`

### 10C.4 当前 Agent 工具能力

工具函数：

- `predict_mrna_stability_with_rnastop(filepath, service_url="http://127.0.0.1:8009/predict/stability", checkpoint_path=None, device=None)`

输入：

- `filepath`，其中保存的是 RNA 序列

输出：

- `prediction_filepath`
- `mean_reactivity`
- `mean_deg_mg_ph10`
- `mean_deg_mg_50c`
- `mfe`
- `checkpoint_path`

当前实现会把完整预测结果保存为 `workspace/*.json`，这样上层 Agent 仍然主要通过 `filepath` 和摘要字段工作，而不是把长结果直接塞进消息。

### 10C.5 当前工作流集成方式

当前 `Router / mRNA specialist / tool_execution` 已经接入 `RNASTOP`：

- `router_node` 会识别 `rnastop`、`stability`、`degradation`、`稳定性`、`降解`、`半衰期` 等语义
- `mrna_specialist_node` 会优先把这类请求路由到 `RNASTOP`
- 当前支持两种 RNA 输入方式：
  - 直接在文本里给 RNA 序列
  - 直接给 `.fasta/.fa/.txt/.seq` 路径
- 当前 `tool_execution_node` 还会更新这些额外状态：
  - `rnastop_prediction_filepath`
  - `rnastop_mean_reactivity`
  - `rnastop_mean_deg_mg_ph10`
  - `rnastop_mean_deg_mg_50c`
  - `rnastop_mfe`
  - `rnastop_checkpoint_path`

### 10C.6 RNASTOP 的实际运行注意事项

#### 当前默认运行资源

当前服务默认会优先检查：

```text
external_repos/RNASTOP/models/best_model_weights
external_repos/RNASTOP/models/best_model_weights_withoutDNABERT
external_repos/RNASTOP/RNA-FM_pretrained.pth
external_repos/RNASTOP/DNABERT6/
```

说明：

- `best_model_weights` 对应完整模型路径，需要 `RNA-FM + DNABERT`
- `best_model_weights_withoutDNABERT` 是兼容降级路径
- `best_model_weights_withoutstrloopdnabert` 当前**不用于**这个稳定性预测服务

#### RNA-FM 本地优先

当前服务已经改成：

- 优先从本地 `RNA-FM_pretrained.pth` 加载
- 不依赖首次运行时在线下载

当前默认还兼容以下位置：

```text
external_repos/RNASTOP/RNA-FM-main/pretrained/RNA-FM_pretrained.pth
external_repos/RNASTOP/pretrained/RNA-FM_pretrained.pth
external_repos/RNASTOP/RNA-FM_pretrained.pth
```

#### DNABERT 当前兼容性处理

当前服务优先尝试：

- `AutoTokenizer.from_pretrained(local_dir)`
- `AutoModel.from_pretrained(local_dir)`

如果当前运行环境里的 `torch` / `transformers` 组合触发了本地加载限制，则会回退到：

- 读取本地 `config.json`
- 读取本地 `model.safetensors` 或 `pytorch_model.bin`
- 手动装载为 `BertModel` 或 `BertForMaskedLM`
- 推理时只取编码器输出

#### loop type 大小写处理

当前服务已经兼容：

- ViennaRNA / RNAlib 可能返回的小写 loop 标签

服务内部会自动转成 RNASTOP 训练代码使用的大写 token 集合，以避免 `loop_type contains unsupported characters` 这类报错。

#### 推荐运行环境

当前实际推荐的运行方式是：

- Linux
- Conda
- Python 3.10
- GPU 环境
- `transformers==4.34.0`

### 10C.7 当前验证状态

RNASTOP 目前已经完成最小闭环验证：

- `rnastop_service` 成功启动
- `GET /health` 成功
- 本地 `best_model_weights` 已成功识别
- 本地 `RNA-FM_pretrained.pth` 已成功识别
- 本地 `DNABERT6/` 已成功识别
- `POST /predict/stability` 已成功
- 前端自然语言请求已成功触发 `RNASTOP`

这意味着：

- `RNASTOP` 已经通过“上游源码 -> 微服务接口 -> Agent 工作流”这一层验证
- 当前项目里已经具备真实的 mRNA 稳定性预测能力
- 但当前还没有把 RNASTOP 的优化模块纳入主项目标准工作流

---

## 10D. GerNA-Bind 的接入方式

### 10D.1 上游源码层

目录：

```text
external_repos/GerNA-Bind
```

来源：

- 上游仓库：[GENTEL-lab/GerNA-Bind](https://github.com/GENTEL-lab/GerNA-Bind)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 `git add .`

### 10D.2 为什么当前采用“项目内微服务封装”

当前接入的 GerNA-Bind 不是直接调用上游的 `inference_affinity.py` / `inference_binding_site.py`，而是采用：

- 保留上游源码仓库
- 在 `microservices/gernabind_service/` 中重建在线推理入口

这样做的原因是：

- 上游推理脚本默认直接读写 `data/new_data.pkl`
- `train_model.py` / `test_model.py` 含有硬编码的 `/data/...` 路径
- `inference_affinity.py` 默认读取 `Model/Robin_Model_baseline.pth`，但上游下载脚本实际提供的是 `Model/Robin_random.pth`
- `inference_binding_site.py` 默认依赖 `Model/Hariboss_Model_baseline.pth`，但该权重不在上游下载脚本中
- 预处理链路依赖：
  - RNA-FM
  - ViennaRNA
  - RNA 3D 结构
- 更适合通过本项目已有的微服务体系来隔离依赖与运行时资源

### 10D.3 当前微服务能力

目录：

```text
microservices/gernabind_service/
```

当前已封装接口：

- `GET /health`
- `POST /score`
- `POST /predict-binding-site`

输入：

- `rna_sequence`
- `smiles`
- `checkpoint_path`（可选）
- `pdb_path`（可选）
- `secondary_structure`（可选）
- `device`（可选）
- `rhofold_service_url`（可选）

输出：

- `/score`
  - `probability_positive`
  - `predicted_label`
  - `raw_alpha`
  - `checkpoint_path`
  - `preprocessing_pdb_path`
  - `secondary_structure`
  - `device`
- `/predict-binding-site`
  - `per_residue_scores`
  - `checkpoint_path`
  - `preprocessing_pdb_path`
  - `secondary_structure`
  - `device`

### 10D.4 当前 Agent 工具能力

工具函数：

- `score_rna_ligand_binding_with_gernabind(filepath, smiles, service_url="http://127.0.0.1:8010/score", checkpoint_path=None, pdb_path=None, secondary_structure=None, device=None)`

输入：

- `filepath`，其中保存的是 RNA 序列
- `smiles`
- `pdb_path`（可选）
- `secondary_structure`（可选）

输出：

- `probability_positive`
- `predicted_label`
- `checkpoint_path`
- `preprocessing_pdb_path`
- `input_filepath`

当前实现会把 RNA 输入统一落到 `workspace/` 文件路径，再由 Agent 工具通过 HTTP 调用 `GerNA-Bind` 微服务。

### 10D.5 当前工作流集成方式

当前 `Router / mRNA specialist / tool_execution` 已经接入 `GerNA-Bind`：

- `router_node` 会识别 `GerNA-Bind`、`gernabind`、`smiles`、`ligand`、`配体` 等语义
- `mrna_specialist_node` 在用户显式提到 `GerNA-Bind` 时，会优先路由到 `GerNA-Bind`
- 当前支持两种 RNA 输入方式：
  - 直接在文本里给 RNA 序列
  - 直接给 `.fasta/.fa/.txt/.seq` 路径
- 当前 `SMILES` 建议显式写成：
  - `SMILES=...`
  - 或 `SMILES: ...`
- 当前前端自然语言还支持透传：
  - `.pdb/.cif` 路径
  - `secondary_structure=...`
  - `dot-bracket=...`
  - `二级结构=...`

当前 `tool_execution_node` 还会更新这些额外状态：

- `ligand_smiles`
- `gernabind_probability`
- `gernabind_predicted_label`
- `gernabind_checkpoint_path`
- `gernabind_preprocessing_pdb_path`

### 10D.6 GerNA-Bind 的实际运行注意事项

#### checkpoint

当前 `GerNA-Bind` affinity 服务默认会优先检查：

```text
external_repos/GerNA-Bind/Model/Robin_random.pth
external_repos/GerNA-Bind/Model/Biosensor_random.pth
external_repos/GerNA-Bind/Model/Robin_Model_baseline.pth
```

说明：

- 当前项目内默认优先使用 `Robin_random.pth`
- 上游 `Model/get_weights.sh` 可下载 Robin / Biosensor 的 affinity 权重
- `Hariboss_Model_baseline.pth` 需要你手动补齐，或通过环境变量显式指定

#### RNA-FM 本地优先

当前服务已经改成：

- 优先从本地 `RNA-FM_pretrained.pth` 加载
- 不依赖首次运行时在线下载

当前默认会优先检查：

```text
external_repos/GerNA-Bind/Model/RNA-FM_pretrained.pth
external_repos/RNASTOP/RNA-FM_pretrained.pth
external_repos/RNASTOP/RNA-FM-main/pretrained/RNA-FM_pretrained.pth
```

也可以在启动前设置：

```bash
export GERNABIND_RNAFM_PATH=/absolute/path/to/RNA-FM_pretrained.pth
```

#### RhoFold 作为默认 3D 预处理

当前服务默认行为是：

- 如果请求里提供了 `pdb_path`
  - 直接使用该结构文件
- 如果未提供 `pdb_path`
  - 自动调用已存在的 `rhofold_service`

因此：

- 想要更快调试时，优先显式传 `pdb_path`
- 想要走全自动链路时，再让服务自动调用 `RhoFold`

#### GPU 环境

当前 `gernabind_service` 已补成面向新 GPU 的环境：

- `environment.yml`
  - 使用 `pytorch + nvidia` channel
  - 固定 `pytorch 2.1.x + pytorch-cuda=11.8`
- `install_pyg_gpu.sh`
  - 安装与 `torch 2.1.0 + cu118` 对应的 `PyG` wheel

如果希望服务默认跑 GPU，可在启动前设置：

```bash
export GERNABIND_DEVICE=cuda:0
```

#### binding-site 权重

当前 `predict-binding-site` 端点还依赖：

```text
external_repos/GerNA-Bind/Model/Hariboss_Model_baseline.pth
```

这个文件是上游脚本引用的权重，但不会被 `Model/get_weights.sh` 自动下载。

### 10D.7 当前验证状态

GerNA-Bind 目前已经在 Linux + GPU 服务器上完成最小闭环验证：

- 上游源码已成功以 submodule 形式接入
- `gernabind_service` 已成功启动
- `GET /health` 成功
- affinity checkpoint 已成功识别
- 本地 `RNA-FM_pretrained.pth` 已成功识别
- `POST /score` 在 `cpu` 模式成功
- `POST /score` 在 `RTX 4090 + cuda:0` 下成功
- Agent 自然语言请求已成功触发 `GerNA-Bind`
- 前端自然语言中的 `pdb_path` / `secondary_structure` 透传已成功生效

这意味着：

- `GerNA-Bind` 已经通过“上游源码 -> 微服务接口 -> Agent 工作流 -> 前端自然语言触发”这一层验证
- 当前项目里已经具备真实的 RNA-ligand 打分能力，并且可在 `GerNA-Bind` 与 `RNAsmol` 两条链路之间并行保留
- 后续如果再次报错，优先检查的应该是：
  - checkpoint 路径
  - 本地 RNA-FM 权重路径
  - `PyG` GPU wheel 是否与 torch/CUDA 匹配
  - `GERNABIND_DEVICE` 是否配置正确

---

## 10E. CRISOT 的接入方式

### 10E.1 上游源码层

目录：

```text
external_repos/CRISOT
```

来源：

- 上游仓库：[bm2-lab/CRISOT](https://github.com/bm2-lab/CRISOT.git)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 vendoring 进主仓库历史

### 10E.2 为什么当前采用“项目内微服务封装”

当前接入的 `CRISOT` 不是直接调用上游 `CRISOT.py` CLI，而是采用：

- 保留上游源码仓库
- 在 `microservices/crisot_service/` 中直接调用上游 `crisot_modules.py`

这样做的原因是：

- 上游 `CRISOT.py` 在模块导入时就会 import `utils.py`
- `utils.py` 顶层 hard-import `xgboost`
- 即便只跑最基础的 `score`，如果环境里没有 `xgboost` 也会直接报错
- 当前项目只需要稳定的 `score/spec/off-spec/opti` 推理入口

### 10E.3 当前微服务能力

目录：

```text
microservices/crisot_service/
```

当前已封装接口：

- `GET /health`
- `POST /score`
- `POST /spec`
- `POST /off-spec`
- `POST /optimize`

当前支持能力：

- 单个 sgRNA-target 对的 `CRISOT-Score`
- 基于 CSV 的 `CRISOT-Spec`
- 通过 `Cas-OFFinder + reference genome` 的 genome-wide specificity
- 通过 `CRISOT-Opti` 的单碱基突变优化

### 10E.4 当前 Agent 工具能力

工具函数：

- `score_crispr_off_target_with_crisot(filepath, target_sequence, service_url="http://127.0.0.1:8011/score")`
- `calculate_crispr_specificity_with_crisot(csv_filepath, on_item="On", off_item="Off", service_url="http://127.0.0.1:8011/spec")`
- `search_crispr_off_targets_with_crisot(filepath, target_sequence, genome_path, mismatches=6, device="C", service_url="http://127.0.0.1:8011/off-spec")`
- `optimize_sgrna_with_crisot(filepath, genome_path, threshold=0.8, mismatches=6, device="C", service_url="http://127.0.0.1:8011/optimize")`

当前实现会把：

- specificity 结果 CSV
- optimization 结果 CSV
- 最优优化后 sgRNA

复制或保存回 `workspace/`，这样上层 Agent 仍然主要通过文件路径工作。

### 10E.5 当前工作流集成方式

当前 `Router / crispr_specialist / tool_execution` 已经接入 `CRISOT`：

- `router_node` 会识别：
  - `crisot`
  - `crispr`
  - `cas9`
  - `sgrna`
  - `guide rna`
  - `off-spec`
- `crispr_specialist_node` 会根据请求语义在 `score/spec/off-spec/optimize` 之间做规则分发
- 当前支持透传：
  - `sgRNA=...`
  - `target=...`
  - `genome=/path/to/genome.fa`
  - `threshold=...`
  - `mm=...`
  - `device=...`

### 10E.6 CRISOT 的实际运行注意事项

#### `score/spec` 不需要额外权重

当前已接入的：

- `score`
- `spec`
- `off-spec`
- `optimize`

只依赖上游仓库里已有的：

- `models/crisot_score_param.pkl`
- `models/crisot_fingerprint_encoding.pkl`

当前**不需要**额外下载：

- `trained_models.zip`
- `xgboost` 模型权重

除非后续要接 `crisot_fp`。

#### `off-spec` 与 `optimize` 依赖 `cas-offinder`

当前服务默认要求：

- `cas-offinder` 已安装
- 并且可从 `PATH` 调用

当前已验证可通过 Conda 安装到：

- `crisot_service_env`

#### reference genome FASTA 需要服务器本地准备

`off-spec` 和 `optimize` 还依赖：

- reference genome FASTA

例如：

```text
external_repos/CRISOT/data/hs1.fa
```

或任何你在请求里显式传入的绝对路径。

#### `CRISOT-Opti` 在大基因组 + CPU 模式下会很慢

原因：

- 优化流程会先算 WT
- 再枚举多个单碱基突变候选
- 每个候选都可能再次触发一次 genome-wide `Cas-OFFinder` 搜索

因此如果使用：

- 大参考基因组（例如 `hs1`）
- `mismatches=6`
- `device=C`

优化过程可能持续数十分钟甚至更久。

调试阶段更建议：

- 先单独验证 `/score`
- 优化时先把 `mismatches` 降低，例如 `mm=3`
- 或优先用更小的测试基因组做流程验证

#### pandas 2 兼容性

上游 `CRISOT` 仍使用了：

- `DataFrame.append()`

该 API 在 `pandas>=2` 中已移除。

当前 `crisot_service/main.py` 已在服务层加入兼容补丁，因此不需要直接修改上游仓库。

### 10E.7 当前验证状态

`CRISOT` 目前已经完成以下验证：

- 上游源码已成功以 submodule 形式接入
- `crisot_service` 可成功启动
- `GET /health` 成功
- `/score` 已验证可返回正确分数
- `/optimize` 已在 Linux 服务器上成功触发真实 `Cas-OFFinder` 链路
- 已修复 `pandas>=2` 下的 `DataFrame.append()` 兼容性问题
- 前端自然语言测试已通过

这意味着：

- `CRISOT` 已经通过“上游源码 -> 微服务接口 -> Agent 工作流 -> 前端自然语言触发”这一层验证
- 当前项目里已经具备真实的 CRISPR off-target 打分与优化能力

---

## 11. 新增生信工具时的标准流程

以后如果要新增新的第三方工具或仓库，统一按下面流程走。

### 11.1 先判断工具类型

判断这个工具属于哪类：

- 命令行工具
- Python 库工具
- 深度学习模型工具
- 需要大权重 / GPU 的工具

### 11.2 第三方源码层落地

如果是独立仓库：

- 克隆到 `external_repos/`
- 优先用 `submodule` 管理

例如：

```text
external_repos/new_tool_repo/
```

### 11.3 不要直接耦合上游实现到 Agent

主项目不要直接从 `agent_core/` 去 import 第三方仓库内部代码。

正确方式：

1. 先做 `microservices/new_tool_service/`
2. 再在 `agent_core/tools.py` 中通过 HTTP 封装

### 11.4 每个微服务都按统一模板建立

以后新的微服务目录至少应包含：

```text
microservices/new_tool_service/
├── environment.yml
├── main.py
└── start.sh
```

### 11.5 工具层统一只传 filepath

原则：

- 长序列不直接作为 tool 参数传
- 一律先写到 `workspace/`
- tool 入参尽量是 `filepath`

### 11.6 接入 Agent 的最小改动点

新增工具时通常只需要看这几个位置：

- `agent_core/tools.py`
  - 新增 `@tool`
- `agent_core/nodes.py`
  - 把工具加进某个 specialist
  - 补解析逻辑
- `agent_core/state.py`
  - 如果有新的关键指标，补状态字段
- `agent_core/graph.py`
  - 如果要新增 specialist，则补节点和边

### 11.7 测试顺序固定

建议统一按这三层测试：

1. 先测上游原始命令
2. 再测微服务接口
3. 最后测 Agent 调用

不要一开始就直接点 Streamlit，这样很难定位问题。

---

## 12. 代码与仓库传输规范

你当前不是在本地最终运行，而是在另一台 Linux 服务器上运行，因此要特别注意“仓库怎么传”和“哪些文件不应该靠 Git 传”。

### 12.1 开发机与运行机分离

当前推荐的实际工作方式是：

- macOS 机器只负责开发、改代码、提交到 GitHub
- 带 GPU 的 Linux 服务器负责 `git pull` 后创建环境、启动微服务和运行 Agent
- 如果 Linux 服务器运行时报错，应以服务器上的真实报错为准进行排查

这样做的原因是：

- 当前多个生信工具依赖 Linux / CUDA / Conda
- macOS 更适合作为代码编辑与仓库中转环境
- 不应把“在 macOS 上无法运行”误判为工具本身无法接入

### 12.2 主仓库传输

主仓库正常 `git push / git pull`

### 12.3 submodule 传输

像下面这些外部源码仓库，应通过 submodule 管理：

- `GEMORNA`
- `GerNA-Bind`
- `RhoFold`
- `RhoDesign`
- `RNAsmol`
- `RNASTOP`

新 clone：

```bash
git clone --recurse-submodules <repo-url>
```

已有 clone：

```bash
git pull
git submodule update --init --recursive
```

如果某次正在修复 submodule 指针，或临时遇到坏的 submodule 引用导致 `git pull` 卡住，可以临时用：

```bash
git -c submodule.recurse=false pull
git submodule update --init --recursive
```

### 12.4 大文件传输

大权重文件不建议依赖主仓库传输。

例如：

- `checkpoints/*.pt`

典型包括：

- `external_repos/GEMORNA/checkpoints/*.pt`
- `external_repos/RhoFold/pretrained/*.pt`
- `external_repos/RhoDesign/checkpoint/*.pth`
- `external_repos/RNAsmol/saved_model/*.pt`
- `external_repos/RNASTOP/models/*`
- `external_repos/RNASTOP/RNA-FM_pretrained.pth`
- `external_repos/GerNA-Bind/Model/*.pth`
- `external_repos/GerNA-Bind/Model/RNA-FM_pretrained.pth`

推荐方案：

- 用上游 `git lfs pull`
- 或你手动复制到服务器对应目录

当前 `RhoDesign`、`RNAsmol` 和 `GerNA-Bind` 也都属于这种情况。

例如你在本机已经放好的：

- `external_repos/RhoDesign/checkpoint/ss_apexp_best.pth`
- `external_repos/RhoDesign/checkpoint/no_ss_apexp_best.pth`
- `external_repos/RNAsmol/saved_model/*.pt`
- `external_repos/RNASTOP/models/best_model_weights`
- `external_repos/RNASTOP/models/best_model_weights_withoutDNABERT`
- `external_repos/RNASTOP/RNA-FM_pretrained.pth`
- `external_repos/RNASTOP/DNABERT6/`
- `external_repos/GerNA-Bind/Model/Robin_random.pth`
- `external_repos/GerNA-Bind/Model/Biosensor_random.pth`
- `external_repos/GerNA-Bind/Model/Hariboss_Model_baseline.pth`
- `external_repos/GerNA-Bind/Model/RNA-FM_pretrained.pth`

不应默认指望通过主仓库 Git 历史传到 Linux 服务器，更推荐在服务器侧单独补齐，或确认是否需要额外的大文件传输方案。

### 12.5 应该避免提交的内容

以下内容不要继续进入主仓库：

- `__pycache__/`
- `*.pyc`
- `.DS_Store`
- 本地临时日志
- 本地下载的大权重缓存
- `workspace/` 运行期输出
- 误加入索引的外部仓库目录

当前主仓库已经补了基础 `.gitignore`，但历史上误提交的缓存文件如果仍在索引中，需要后续手动清理。

### 12.6 提交流程建议

这个仓库里同时存在：

- submodule
- `workspace/`
- 外部模型权重

因此**不建议默认使用 `git add .`**。

更推荐的流程是：

```bash
git status --short
git submodule status
git add <具体文件或目录>
git commit -m "meaningful message"
git push origin main
```

### 12.7 GEMORNA 权重导致子模块脏状态时的处理

`GEMORNA` 的 `checkpoints/*.pt` 可能因为本地真实权重文件而表现为“子模块脏状态”，但这不一定代表代码真的变了。

如果你希望：

- 保留本地权重
- 又不想让主仓库一直显示 `m rna_agent_system/external_repos/GEMORNA`

可以在本机对子模块执行：

```bash
git -C rna_agent_system/external_repos/GEMORNA update-index --assume-unchanged \
  checkpoints/3utr.pt \
  checkpoints/5utr.pt \
  checkpoints/gemorna_3utr.pt \
  checkpoints/gemorna_5utr.pt \
  checkpoints/gemorna_cds.pt
```

这只是**本地 Git 状态技巧**，不会同步到远端，也不会传给别的机器。

---

## 13. 推荐测试顺序

### 13.1 单工具测试

例如测试 ViennaRNA：

1. 启动 `viennarna_fold`
2. `curl /health`
3. `curl /fold`

例如测试 GEMORNA：

1. 先直接跑 `src/generate.py`
2. 再启动 `gemorna_service`
3. 再 `curl /generate/cds`

例如测试 RhoFold：

1. 启动 `rhofold_service`
2. `curl /health`
3. `curl /predict`

推荐优先测试 payload：

```json
{
  "sequence": "AUGGCUACGUAGCUAGCUAGCUAGCUGA",
  "single_seq_pred": true,
  "relax_steps": 0,
  "device": "cuda:0"
}
```

例如测试 RhoDesign：

1. 启动 `rhodesign_service`
2. `curl /health`
3. `curl /design/from-structure`

推荐优先测试 payload：

```json
{
  "pdb_path": "rna_agent_system/external_repos/RhoDesign/example/2zh6_B.pdb",
  "temperature": 1e-5,
  "device": 0
}
```

例如测试 RNAsmol：

1. 启动 `rnasmol_service`
2. `curl /health`
3. `curl /score`

推荐优先测试 payload：

```json
{
  "rna_sequence": "AUGGCUACGUAGCUAGCUAG",
  "smiles": "CCO"
}
```

例如测试 RNASTOP：

1. 启动 `rnastop_service`
2. `curl /health`
3. `curl /predict/stability`

推荐优先测试 payload：

```json
{
  "sequence": "AUGGCUACGUAGCUAGCUAGCUAGCUGA"
}
```

例如测试 GerNA-Bind：

1. 启动 `gernabind_service`
2. `curl /health`
3. `curl /score`

推荐优先测试 payload：

```json
{
  "rna_sequence": "AUGGCUACGUAGCUAGCUAG",
  "smiles": "CCO",
  "device": "cuda:0"
}
```

如果你希望绕开 `RhoFold`，优先再测：

```json
{
  "rna_sequence": "AUGGCUACGUAGCUAGCUAG",
  "smiles": "CCO",
  "secondary_structure": "....................",
  "pdb_path": "/absolute/path/to/unrelaxed_model.pdb",
  "device": "cuda:0"
}
```

如果服务器是新卡（例如 `RTX 4090`），且需要显式覆盖设备，推荐再测：

```json
{
  "rna_sequence": "AUGGCUACGUAGCUAGCUAG",
  "smiles": "CCO",
  "device": "cuda:0"
}
```

例如测试 CRISOT：

1. 启动 `crisot_service`
2. `curl /health`
3. `curl /score`
4. `curl /optimize`

推荐优先测试 payload：

```json
{
  "sgrna": "GAGTCCGAGCAGAAGAAGAANGG",
  "target_sequence": "GAGTCCGAGGAGAAGACGAAGGG"
}
```

优化调试阶段推荐优先测试：

```json
{
  "target_sequence": "GAGTCCGAGGAGAAGACGAAGGG",
  "genome_path": "/absolute/path/to/hs1.fa",
  "threshold": 0.8,
  "mismatches": 3,
  "device": "C"
}
```

### 13.2 智能体集成测试

在微服务都启动后，再启动：

- `frontend/app.py`

推荐从仓库根目录启动：

```bash
streamlit run rna_agent_system/frontend/app.py --server.fileWatcherType none
```

说明：

- 当前 `frontend/app.py` 已在代码中自动补了父目录到 `sys.path`
- 因此正常情况下不再需要手动设置 `PYTHONPATH`
- 某些 Linux 服务器上 `inotify watch limit` 偏小，因此建议保留 `--server.fileWatcherType none`

然后测试：

- siRNA 请求
- mRNA 结构预测请求
- GEMORNA 设计请求
- GEMORNA 设计 + RNAfold 联合请求
- RNA 三级结构预测请求
- GEMORNA 设计 + RhoFold 联合请求
- RhoDesign 结构到序列设计请求
- RNAsmol RNA-ligand 打分请求
- RNASTOP mRNA 稳定性预测请求
- GerNA-Bind RNA-ligand 打分请求
- CRISOT single-pair 打分请求
- CRISOT genome-wide specificity 请求
- CRISOT sgRNA 优化请求

---

## 14. 当前已知风险与限制

### 14.1 Router / Specialist / Critic 目前是规则模式

优点：

- 稳定
- 可控
- 易调试

缺点：

- 灵活性不如 LLM
- 复杂自然语言理解能力有限

### 14.2 `mock_codon_optimization` 仍然是假的

当前 mRNA 分支里：

- `predict_rna_secondary_structure` 已是真实 ViennaRNA
- `design_mrna_cds_with_gemorna` 已是真实 GEMORNA 接入
- 但 `mock_codon_optimization` 仍是模拟工具

后续可以替换成真实密码子优化工具。

### 14.3 GEMORNA 输出解析仍可继续增强

当前是通过解析 `stdout` 抽取生成序列。  
如果后续发现输出格式变化，建议把解析逻辑改得更稳：

- 返回多候选
- 明确打分
- 明确输出文件

### 14.4 `GEMORNA` 的二进制 `.so` 对 Python 版本敏感

必须优先保证：

- Linux
- Python 3.10

否则可能出现 ABI 兼容性报错。

### 14.5 `RhoFold` 当前默认只接了单序列模式

当前已经接通的是：

- `single_seq_pred=true`

这意味着：

- 结构预测已经可用
- 但还没有把本地 MSA 数据库模式纳入主项目标准部署流程

后续如果要追求更高精度，可再扩展：

- 用户显式提供 `.a3m`
- 或服务器侧本地建库

### 14.6 前端当前仍然比较轻量

当前 `frontend/app.py` 主要是一个最小可用调试界面：

- 展示节点执行进度
- 展示简化后的 `final_report`

它暂时还不是一个产品级 UI，因此：

- 结果展示较粗糙
- 大结果文件的可视化仍有增强空间
- 更适合作为当前接入阶段的调试入口

### 14.7 `RhoFold` 首次运行可能需要网络访问

虽然推荐手动放好 checkpoint，但 `RhoFold` 运行时仍可能因为上游实现而访问 Hugging Face 拉取附属文件。

因此：

- 首次运行建议保证服务器网络可访问相关源
- 或后续在服务器上做好本地缓存

### 14.8 `RhoDesign` 的 PyG 版本匹配较脆弱

当前 `RhoDesign` 最容易踩坑的地方之一是：

- `torch-scatter`
- `torch-sparse`
- `torch-cluster`
- `torch-spline-conv`

这些包必须和：

- Python 版本
- PyTorch 版本
- CUDA 版本

同时匹配。

如果版本不匹配，常见现象包括：

- `pip` 回退到源码构建
- build isolation 阶段报 `No module named 'torch'`
- wheel 找不到

因此部署时优先原则是：

- 先锁定 `torch 1.12.1 + cu113`
- 再去 `data.pyg.org` 安装对应 wheel

### 14.9 `RhoDesign` 当前默认调试输入带有 fallback

当前如果用户请求触发了 `RhoDesign`，但没有明确提供 `.pdb` 路径，工作流会默认回退到：

```text
rna_agent_system/external_repos/RhoDesign/example/2zh6_B.pdb
```

这有利于当前接入阶段快速调试，但也意味着：

- 它更偏“开发期默认行为”
- 后续如果进入更正式的使用阶段，建议改成“没有结构文件就明确报错”，避免隐式使用示例输入

### 14.10 `RNAsmol` 的环境兼容性依赖实际 GPU

当前 `RNAsmol` 最容易踩坑的地方之一不是业务代码，而是环境代际差异：

- 上游原始依赖偏旧
- 新 GPU（例如 `RTX 4090`）对老版 `torch 1.7.1 + cu102` 不兼容

当前已知现象包括：

- 服务 `/health` 正常
- `cpu` 推理正常
- 但默认走 `cuda:0` 时卡住或无响应

当前更稳妥的部署原则是：

- 旧卡 / CPU：优先使用 `environment.yml`
- 新卡 / 4090：优先使用 `environment.gpu.yml`
- 显式设置 `RNASMOL_DEVICE`

### 14.11 `RNAsmol` 当前更适合作为评分工具而不是训练工具

当前主项目已经接通的是：

- 单条 RNA 序列 + 单条 ligand `SMILES` 的打分服务

这意味着：

- 作为 Agent 底层评分工具已经可用
- 但还没有把 `RNAsmol` 的完整训练、数据预处理、批量评估链路纳入主项目标准部署流程

### 14.12 `RNASTOP` 当前只接了稳定性预测，不接优化

当前主项目已经接通的是：

- 单条 RNA 序列的稳定性 / 降解预测

这意味着：

- 作为 Agent 底层预测工具已经可用
- 但还没有把 RNASTOP 的 beam search / MCTS 优化模块纳入标准部署流程
- 当前也没有把 RNASTOP 的训练、论文复现实验脚本纳入主项目默认工作流

### 14.13 `GerNA-Bind` 当前更适合作为推理服务而不是直接复用上游脚本

当前主项目已经接通的是：

- 单条 RNA 序列 + 单条 ligand `SMILES` 的打分服务
- 单条 RNA 序列的 binding-site 预测服务入口

这意味着：

- 作为 Agent 底层打分工具已经可用
- 但当前并没有把上游 `train_model.py` / `test_model.py` 的训练与评估脚本纳入主项目标准部署流程
- 上游仓库中硬编码的 `/data/...` 路径仍然不适合直接在本项目中复用

### 14.14 `GerNA-Bind` 对本地 RNA-FM 权重和 PyG 环境较敏感

当前 `GerNA-Bind` 最容易踩坑的地方之一是：

- RNA-FM 首次在线下载的缓存文件可能损坏
- `torch-geometric` 及其 CUDA wheel 需要与 `torch 2.1.x + cu118` 匹配

当前更稳妥的部署原则是：

- 优先使用本地 `RNA-FM_pretrained.pth`
- 启动前显式设置 `GERNABIND_DEVICE`
- 新 GPU 环境下先执行 `install_pyg_gpu.sh`

### 14.15 `CRISOT-Opti` 当前耗时较长

当前 `CRISOT` 最容易遇到的问题之一不是接口报错，而是：

- genome-wide 优化非常耗时

特别是在：

- 大参考基因组
- 较高 `mismatch tolerance`
- `device=C`

这种组合下，优化阶段会反复触发多个 `Cas-OFFinder` 搜索。

因此当前更稳妥的调试原则是：

- 先单独验证 `score`
- 再验证 `off-spec`
- 最后再验证 `optimize`
- 优化初期先用 `mm=3`

---

## 15. 后续最推荐的发展路线

建议按下面顺序继续推进：

1. 先把工具链接全，优先真实工具替换 mock 工具
2. 保持规则模式，先把每个工具独立跑通
3. 先在 Agent 层把 `RhoFold` / `RhoDesign` / `RNAsmol` / `GerNA-Bind` / `CRISOT` 的一句话调用链路稳定下来
4. 等工具生态稳定后，再恢复可配置的 LLM 模式
5. 再逐步引入：
   - 更细的 specialist
   - 更强的 critic
   - 结果排序 / 候选集筛选
   - 多工具串联规划
6. 后续再考虑：
   - 用真实密码子优化工具替换 `mock_codon_optimization`
   - 为 `RhoFold` 增加可选的 MSA 模式
  - 优化 `RhoDesign` 的输入文件校验与错误提示
  - 优化 `RNAsmol` 的输入解析与批量评分模式
  - 为 `GerNA-Bind` 增加更细粒度的前端参数透传与批量推理模式
  - 优化前端结果展示与文件下载体验

---

## 16. 一句话总结

当前这个项目的核心设计可以概括为：

**上层 Agent 只负责规则路由与工作流编排，下层所有复杂生信能力都通过 `Conda + FastAPI` 微服务隔离运行，长序列统一走 `workspace filepath` 传递，第三方源码通过 `external_repos/` 的 submodule 方式独立管理。**

以后新增工具时，统一按下面的固定动作做：

1. 放到 `external_repos/`
2. 建 `microservices/<tool>_service/`
3. 在 `agent_core/tools.py` 封装 HTTP 工具
4. 在 `nodes.py` 接 specialist
5. 先测原始命令，再测微服务，再测 Agent
6. 如果仓库里有 submodule 和运行时输出，不要默认 `git add .`

