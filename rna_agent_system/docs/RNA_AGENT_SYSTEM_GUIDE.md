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
  - 另含 ViennaRNA 扩展摘要：`vienna_sirna_duplex_mfe`、`vienna_aso_mean_unpaired`、`vienna_aso_joint_unpaired`、`vienna_inverse_best_sequence`（由对应工具回填，可选）

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
    - `design_sgrna_handle_with_crgpt`
    - `analyze_cds_codon_metrics_with_codonw_slim`（真实 [codonw-slim](https://github.com/smsaladi/codonw-slim)；默认「结构预测型」链路中替代原 mock 前置步骤）
    - `mock_codon_optimization`（仍保留在代码库中，规则工作流**当前不再默认调用**）
    - `predict_rna_secondary_structure`
    - `design_mrna_cds_with_rnarl`
    - `design_mrna_cds_with_gemorna`
    - `design_mrna_cds_with_lineardesign`
    - `predict_putative_ires_with_iresfinder`
    - `predict_rna_secondary_structure_with_linearfold`
    - `predict_rna_tertiary_structure_with_rhofold`
    - `compute_sirna_duplex_binding_vienna`（siRNA 正反义链共折叠 / 结合能）
    - `compute_aso_target_accessibility_vienna`（ASO 靶区 RNAplfold 可及性）
    - `inverse_fold_rna_secondary_structure_vienna`（RNAinverse 二级结构逆折叠）
    - `run_blastn_similarity_search`（NCBI **BLAST+** `blastn`；微服务 **§10M**，默认 **8019**）

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
  - ViennaRNA：**二级结构 / MFE**、**siRNA 正反义链 cofold**、**RNAplfold 靶区可及性**、**RNAinverse 逆折叠**
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

- `odesign_service/`
  - ODesign 的 biomolecular design 推理服务
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8012`
  - 当前主项目里优先接入的是 RNA 相关能力
  - 当前已封装：
    - `GET /health`
    - `POST /design/from-json`
  - 当前服务定位是：
    - Linux + CUDA 服务器侧运行
    - 通过输入 JSON 文件驱动上游推理
    - 把预测结果 `*.cif` / `run.log` 等摘要回传给 Agent

- `iresfinder_service/`
  - IRESfinder 的 putative IRES 预测服务（Python 3 重实现）
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8013`
  - 当前已封装接口：
    - `GET /health`
    - `POST /predict`
  - 输入是 `fasta_content`（支持 FASTA 或纯序列文本）
  - 支持参数：
    - `mode`（0/1/2）
    - `window_size`
    - `step_size`
    - `decision_threshold`
  - 输出包括：
    - `has_putative_ires`
    - `best_fragment_id`
    - `max_score`
    - `result_tsv_path`

- `lineardesign_service/`
  - [LinearDesign](https://github.com/LinearDesignSoftware/LinearDesign) 的 protein-to-mRNA CDS 设计服务（调用上游 `bin/LinearDesign_2D`）
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8014`
  - 当前已封装接口：
    - `GET /health`
    - `POST /generate/cds`
  - 上游源码与编译产物默认目录：
    - `rna_agent_system/external_repos/LinearDesign/`
    - 部署后需在上述目录执行 `make`，生成 `bin/LinearDesign_2D`
  - 可选环境变量：
    - `LINEARDESIGN_ROOT`：覆盖 LinearDesign 检出根目录（需已 `make` 且存在 `bin/LinearDesign_2D`）

- `linearfold_service/`
  - [LinearFold](https://github.com/LinearFold/LinearFold.git) 的 RNA 二级结构预测服务（调用上游 `linearfold` 脚本与 `bin/linearfold_c|v`）
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8015`
  - 当前已封装接口：
    - `GET /health`
    - `POST /fold`
  - 输入是 `sequence`
  - 支持参数：
    - `beam_size`
    - `use_vienna`
    - `dangles`
  - 输出包括：
    - `sequence`
    - `structure`
    - `mfe`
    - `backend`（`LinearFold-C` 或 `LinearFold-V`）
  - 上游源码与编译产物默认目录：
    - `rna_agent_system/external_repos/LinearFold/`
    - 部署后需在上述目录执行 `make`，生成 `bin/linearfold_c` 与 `bin/linearfold_v`
  - 可选环境变量：
    - `LINEARFOLD_ROOT`：覆盖 LinearFold 检出根目录（需已 `make` 且存在 `bin/linearfold_c|v`）

- `evitar_service/`
  - [Evitar](https://github.com/dingyaozhang/Evitar.git) 的 siRNA/Cas13 设计服务（调用上游 `Evitar.pl`）
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8016`
  - 当前已封装接口：
    - `GET /health`
    - `POST /design`
  - 支持模式：
    - `existing`（已有病毒，需 `input + strains`）
    - `predesign`（future-virus 预设计，需 `input`）
  - 支持参数：
    - `predict=predsi|rnaxs|CRISPR`
    - `off_target`
    - `ncores`
  - 运行时说明：
    - 上游 `bin/` 含 Linux 可执行文件
    - macOS 上常见 `cannot execute binary file`，最终验证应在 Linux 服务器完成

- `sgrna_design_service/`
  - [sgrna_design](https://github.com/bitguolab/sgrna_design.git) 的 sgRNA handle 设计服务（CRGPT 推理封装）
  - `environment.yml` + `main.py` + `start.sh`
  - 默认端口 `8017`
  - 当前已封装接口：
    - `GET /health`
    - `POST /design`
  - 输入是 `seed_sequence`（DNA/RNA，服务端会统一归一化为 DNA）
  - 支持参数：
    - `n_samples`
    - `mutation_number`
    - `temperature`
    - `max_overlap`
    - `device`
  - 输出包括：
    - `generated_count`
    - `output_fasta_path`
    - `summary_json_path`
    - `candidates`
  - 运行时说明：
    - 上游模型文件为 `pytorch_model.bin`，需使用 `torch>=2.6`
    - GPU 环境需保证 torch CUDA 构建与服务器驱动代际匹配（见 §10K）

- `codonw_slim_service/`
  - [codonw-slim](https://github.com/smsaladi/codonw-slim.git) 的 CDS 密码子使用指标服务（CAI、Fop、CBI、Nc/ENC、疏水性、芳香性、碱基组成等）
  - `environment.yml` + `main.py` + `start.sh` + **`install_codonw_slim.sh`**
  - 默认端口 **`8018`**
  - 当前已封装接口：
    - `GET /health`
    - `POST /analyze/cds`
  - 输入为 JSON 字段 `sequence`（DNA `ATGC` 或 RNA `AUGC`，支持 FASTA）；可选 `genetic_code`（0--7）、`cai_ref`、`fop_ref`、`factor_in_rare`、`include_codon_tables`、`include_dinucleotide`
  - 输出包括：`cai`、`fop`、`cbi`、`enc`、`hydropathy`、`aromaticity`、`silent_base_usage`、`bases2` 等；完整 JSON 由 Agent 工具层写入 `workspace/codonw_metrics_*.json`
  - 运行时说明（**必读**）：
    - **`conda env create` 成功后必须执行 `bash install_codonw_slim.sh`**：用 `pip install --no-build-isolation -e` 编译子模块，避免 pip 隔离构建环境缺少 `Cython`；脚本还会在每次安装前将上游 `codonw.pyx` 中 **`astype(long)`** 替换为 **`astype(np.int64)`**（Python 3 / 新版 Cython 兼容）
    - 需要可用的 **C 编译器**（Linux 上通常为 `gcc`）以编译 Cython/C 扩展
    - 详细说明见 **§10L**

- `blast_service/`
  - NCBI **BLAST+**（`blastn` / `makeblastdb`）的核酸相似性搜索服务
  - `environment.yml`（`python=3.10` + bioconda **`blast`**）+ `main.py` + `start.sh`
  - 默认端口 **`8019`**
  - 当前已封装接口：
    - `GET /health`
    - `POST /blastn`
  - 输入支持：`query_filepath`（服务器可读路径，相对路径按 `rna_agent_system/` 解析）；**二选一** `subject_fasta_path`（服务内现场 `makeblastdb`）或 `subject_db`（已有核苷酸 BLAST 库前缀）；可选 `task`、`evalue`、`word_size`、`max_target_seqs`、`perc_identity`、`strand`、`outfmt`、`blastn_timeout_sec`
  - 输出包括：`hit_count`、制表符结果预览、完整 `tabular_output`（响应体过大时会截断并标记 `tabular_output_truncated`）
  - Agent 工具层会把完整制表结果写入 `workspace/blastn_out_*.tsv`（见 **§10M**）
  - **与 `off_target_blast`（8002）区分**：后者仍为 **mock** 脱靶计数；真实 BLAST 比对请使用本服务

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
- `ODesign/`
- `IRESfinder/`
- `LinearDesign/`
- `LinearFold/`
- `Evitar/`
- `ViennaRNA/`
- `sgrna_design/`
- `codonw-slim/`

**重要：**

- `external_repos/GEMORNA` 应作为 **git submodule** 管理
- `external_repos/GerNA-Bind` 也应作为 **git submodule** 管理
- `external_repos/RNASTOP` 也应作为 **git submodule** 管理
- `external_repos/RhoFold` 也应作为 **git submodule** 管理
- `external_repos/RhoDesign` 也建议作为 **git submodule** 管理
- `external_repos/CRISOT` 也应作为 **git submodule** 管理
- `external_repos/ODesign` 也应作为 **git submodule** 管理
- `external_repos/IRESfinder` 也应作为 **git submodule** 管理
- `external_repos/LinearDesign` 也应作为 **git submodule** 管理
- `external_repos/LinearFold` 也应作为 **git submodule** 管理
- `external_repos/Evitar` 也建议作为 **git submodule** 管理
- `external_repos/ViennaRNA`（官方 ViennaRNA Package 源码）也应作为 **git submodule** 管理
- `external_repos/sgrna_design` 也应作为 **git submodule** 管理
- `external_repos/codonw-slim` 也应作为 **git submodule** 管理
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
- `ODesign` 生成的 `cif` / `run.log` / error logs
- `codonw_slim_service` 经 Agent 工具落盘的 `codonw_metrics_*.json`
- `blast_service` 经 Agent 工具落盘的 `blastn_out_*.tsv`（`blastn` 制表符输出）
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

- 如果文本中包含 `mrna`、`design`、`protein`、`cds`、`utr`、`structure`、`fold`、`gemorna`、`lineardesign`、`linear design`、`linearfold`、`linear fold`、`rhofold`、`rhodesign`、`rnasmol`、`rnastop`、`gernabind`、`gerna-bind`、`iresfinder`、`ires`、`internal ribosome`、`stability`、`degradation`、`稳定性`、`降解`、`smiles`、`ligand`、`配体`、`pdb`、`cif`、`3d`、`tertiary`、`三级结构`、`三维结构`、`aso`、`gapmer`、`morpholino`、`accessibility`、`可及性`、`plfold`、`inverse fold`、`逆折叠`、`rnainverse`、`codonw`、`codonw-slim`、`codon bias`、`blast`、`blastn`、`megablast`、`dc-megablast`、`相似性搜索` 等关键词
  - 路由到 `mrna_specialist`
- 如果包含 `crisot`、`crispr`、`cas9`、`sgrna`、`guide rna`、`off-spec`
  - 以及 `sgrna handle`、`sgrna design`、`crgpt`、`sgrna_design`
  - 路由到 `crispr_specialist`
- 如果包含 `evitar`、`predesign`、`future virus`、`rnaxs`、`predsi`、`cas13`
  - 路由到 `sirna_specialist`
- 如果包含 `sirna`、`脱靶`、`off-target`，或命中 **siRNA 双链 / cofold** 语义（如 `duplex`、`rnacofold`、`正反义`、`双链`、`sirna duplex`、`结合能` 等与双链热力学相关的组合语境）
  - 路由到 `sirna_specialist`
- 默认也偏向 `mrna_specialist`

### 5.2 siRNA Specialist

规则式地产生两个工具调用：

- `predict_sirna_efficiency(filepath)`
- `check_off_target(filepath)`

当请求命中 Evitar 关键词时，切换到 Evitar 分支：

- `design_sirna_with_evitar(filepath, mode, predict, strains_path, off_target, ncores)`
- 默认服务地址：`http://127.0.0.1:8016/design`

当请求命中 **siRNA 正反义链共折叠 / duplex 结合能**（且非 Evitar）时，切换到 ViennaRNA 分支：

- `compute_sirna_duplex_binding_vienna(filepath, service_url="http://127.0.0.1:8003/sirna-duplex")`
- 输入文件：两条 FASTA（先 sense 后 antisense），或两行无 `>` 的 RNA；亦可在自然语言中写 `sense=...` / `antisense=...`（或 `guide` / `passenger`），由节点写入 `workspace/` 后再调工具

### 5.3 mRNA Specialist

分多种模式（按规则优先级依次匹配）：

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

- 如果用户文本偏 **codonw-slim / 密码子指标**（独立分析，不混在设计型分支里）
  - 命中条件包括：`codonw`、`codonw-slim`、`codon usage`、`codon metrics`，或中文 **「密码子」** 与 **分析 / 指标 / 偏好 / CAI / ENC / Fop / CBI** 等组合（实现见 `nodes.py` 中 `_needs_codonw_standalone`）
  - 触发 `analyze_cds_codon_metrics_with_codonw_slim(filepath, service_url="http://127.0.0.1:8018/analyze/cds", ...)`
  - 输入解析与 RNASTOP 类似：正文长 RNA 或 `.fasta/.fa/.txt/.seq` 路径；内容应为 **in-frame CDS**（非 3 倍数时由服务端截去末尾 1--2 nt）
  - 可选从自然语言解析：`genetic_code=`、`cai_ref=`、`fop_ref=`、`factor_in_rare`、`include_codon_tables` / `rscu` / `dinuc` 等（见 `_build_codonw_tool_args`）
  - 该分支排在 **RNASTOP 之后、RhoDesign 结构到序列之前**，且排在 **`design_mode`（含 `cds` 关键词的设计型）之前**，避免纯密码子统计被误判为蛋白 CDS 设计

- 如果用户文本偏 **NCBI BLAST+ / blastn 核酸相似性搜索**
  - 命中条件包括：`blast`、`blastn`、`megablast`、`dc-megablast`、`相似性搜索` 等（实现见 `nodes.py` 中 `_needs_blast_search`）
  - 触发 `run_blastn_similarity_search(filepath, subject_fasta_path=None, subject_db=None, service_url="http://127.0.0.1:8019/blastn", ...)`（`subject_fasta_path` 与 `subject_db` **二选一**，由规则解析填入）
  - **query** 输入解析与 RNASTOP / IRESfinder 类似：正文长 RNA / DNA 或 `.fasta/.fa/.txt/.seq` 路径，会先落入 `workspace/` 再传 `filepath`
  - 必须在自然语言中显式提供 subject **之一**：
    - **FASTA 库**：`subject_fasta=`、`subject=`、`target_fasta=`，或带扩展名的命名路径（`.fa/.fasta/.fna/.fas`）
    - **已有 BLAST 核苷酸库前缀**：`subject_db=`、`blast_db=`、`blastdb=`、`database=`
  - 可选从自然语言解析：`evalue=`、`word_size=`、`max_target_seqs=`、`perc_identity=`、`strand=plus|minus`；若出现 `megablast` / `dc-megablast` 等关键词会映射到 `blastn` 的 `-task`
  - 该分支在 `mrna_specialist_node` 中排在 **独立 codonw-slim 分支之后、RhoDesign「结构到序列」之前**；若缺少 subject，节点只返回说明性 `AIMessage`，**不**发起工具调用
  - **与 `check_off_target` / `off_target_blast`（8002）区分**：siRNA 默认链路里的 `check_off_target` 仍为 **mock**；真实 BLAST 比对由本工具 + **`blast_service`（8019）** 完成（详见 **§10M**）

- 如果用户文本偏“IRES 识别型”
  - 触发 `predict_putative_ires_with_iresfinder(filepath, mode=0, window_size=174, step_size=50, decision_threshold=0.5)`
  - 输入是 RNA 序列文件路径（或 FASTA 文件路径）
  - 支持从自然语言中解析可选参数：
    - `ires_mode` / `iresfinder_mode`
    - `window_size`
    - `step_size`
    - `decision_threshold` / `ires_threshold`
  - 当前返回核心摘要包括：
    - `has_putative_ires`
    - `best_fragment_id`
    - `max_score`
    - `positive_count`
    - `fragment_count`
    - `result_tsv_filepath`

- 如果用户文本偏 **ViennaRNA 二级结构逆折叠**（`inverse fold`、`逆折叠`、`rnainverse` 等）
  - 触发 `inverse_fold_rna_secondary_structure_vienna(filepath, service_url="http://127.0.0.1:8003/inverse-fold", repeats=1, ...)`
  - 输入文件：**第一行**为点括号二级结构；**第二行**可选为 RNAinverse 起始串（`N` 表示可随机化位点）
  - 或在自然语言中写 `structure=(((...)))`；`repeats=5` 可映射到工具参数
  - 当前实现中，该分支在 `nodes.py` 里排在 **IRESfinder 之后、RNASTOP 之前**

- 如果用户文本偏 **ASO 与靶 mRNA 结合区域可及性**（`aso`、`accessibility`、`可及性`、`plfold`、`rnaplfold` 等）
  - 触发 `compute_aso_target_accessibility_vienna(filepath, region_start, region_end, service_url="http://127.0.0.1:8003/aso-accessibility", ...)`
  - 靶序列：正文内 **≥12 nt** 的 RNA 片段（取最长）或 `.fasta/.fa/.txt/.seq` 路径（与 RNASTOP 输入解析同源）
  - 区间：`region=10-50`、`start=... end=...` 或形如 `10-50` 的坐标；若未解析到，则回退为 `1..min(20, L)`（`L` 为序列长度）
  - 当前实现中，该分支在 **IRESfinder 之后、RNASTOP 之前**

- 如果用户文本偏“结构到序列设计型”
  - 触发 `design_rna_sequence_with_rhodesign(pdb_filepath, secondary_structure_filepath=None)`
  - 输入是 `pdb` 文件路径
  - 如果用户文本里给了 `.npy` 路径，则自动走带 2D 约束的模式
  - 如果没有提供结构文件，当前会回退到 `external_repos/RhoDesign/example/2zh6_B.pdb` 作为默认调试输入

- 如果用户文本显式提到 `ODesign` / `odesign`
  - 触发 `run_odesign_inference(input_json_filepath, infer_model_name="odesign_base_na_rigid", design_modality="rna", ...)`
  - 当前支持三种入口：
    - 显式给 `ODesign` 输入 JSON 路径
    - 直接请求 `RNA backbone` / `length=...`
    - 直接请求 `protein-binding RNA`，并提供：
      - `ref_file=/path/to/*.cif|*.pdb`
      - `hotspot=C/18,C/90,...`
      - `length=61`
  - 对于 `protein-binding RNA` 模式：
    - 如果给了 `protein_segment=C/1-96`，则直接透传
    - 如果没给 `protein_segment`，但给了 `protein_chain=C` 或 hotspot 所在链，当前节点会尝试从参考结构自动推断蛋白链范围
  - 当前仍建议复杂任务优先显式准备 JSON，而不是让规则解析自由生成所有字段

- 如果用户文本显式提到 `LinearDesign` / `lineardesign` / `linear design`，且整体仍偏“设计型”
  - 触发 `design_mrna_cds_with_lineardesign(filepath, service_url="http://127.0.0.1:8014/generate/cds", lambda_value=0.0, codon_usage_path=None, verbose=False)`
  - 输入文件保存的是蛋白序列（与 GEMORNA / RNARL 相同，由规则从自然语言抽取并写入 `workspace/`）
  - 若未显式写 RNARL 关键词且未写 GEMORNA，则 **LinearDesign 优先于 GEMORNA**
  - 如果用户请求里还包含结构预测语义，当前会在 LinearDesign 设计完成后继续自动调用：
    - `predict_rna_secondary_structure`
    - `predict_rna_tertiary_structure_with_rhofold`（当文本含 `rhofold`、`3d`、`tertiary` 等关键词时）

- 如果用户文本偏“设计型”（且未命中上述 LinearDesign 显式分支时，仍走原默认）
  - 触发 `design_mrna_cds_with_gemorna(filepath)` 或 `design_mrna_cds_with_rnarl(...)`（由是否含 `rnarl` 等关键词决定）
  - 输入文件保存的是蛋白序列
  - 如果用户请求里还包含结构语义，当前会在 **CDS 设计工具**（GEMORNA / RNARL）完成后继续自动调用结构预测工具
- 如果用户文本偏“结构预测型”
  - 触发：
    - `analyze_cds_codon_metrics_with_codonw_slim(filepath, ...)`（**真实 codonw-slim**；在 fold 之前给出 CAI / Nc 等摘要，完整指标写入 `workspace/` JSON）
    - `predict_rna_secondary_structure(filepath)`（默认 ViennaRNA）
    - 当文本显式包含 `linearfold`（或不与 `lineardesign` 冲突的 `linear fold`）时，改为触发 `predict_rna_secondary_structure_with_linearfold(filepath, beam_size=..., use_vienna=..., dangles=...)`
  - 如果用户文本里还包含 `rhofold`、`3d`、`tertiary`、`三级结构`、`三维结构`、`pdb`
    - 还会额外触发 `predict_rna_tertiary_structure_with_rhofold(filepath)`

另外，如果先做了 **`GEMORNA` / `RNARL` / `LinearDesign`** 任一 CDS 设计，而用户请求中又包含结构预测语义，当前 `tool_execution_node` 会在拿到生成 CDS 输出后继续自动调用折叠工具（默认 ViennaRNA；显式 `linearfold` 时切到 LinearFold）：

- `predict_rna_secondary_structure`
- `predict_rna_tertiary_structure_with_rhofold`

### 5.3A CRISPR Specialist

当前新增 `crispr_specialist`，主要负责 `CRISOT` 相关请求。

- 如果用户文本偏 sgRNA handle 设计语义（如 `sgrna handle` / `sgrna design` / `crgpt`）
  - 触发 `design_sgrna_handle_with_crgpt(filepath, n_samples, mutation_number, temperature, max_overlap, device)`
- `seed/template/handle/wildtype` 等参数支持 40-140nt 提取；若未显式给 seed，则回退到默认 wildtype 61nt
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
- `sgrna_design_generated_count`
- `sgrna_design_best_nn_score`
- `sgrna_design_best_mutation_count`
- `sgrna_design_output_filepath`
- `sgrna_design_summary_filepath`
- `sgrna_design_model_path`
- `cai_score`
- `codonw_metrics_filepath`
- `codonw_enc`
- `codonw_fop`
- `codonw_cbi`
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
- `iresfinder_result_tsv_filepath`
- `iresfinder_has_putative_ires`
- `iresfinder_max_score`
- `iresfinder_best_fragment_id`
- `iresfinder_positive_count`
- `iresfinder_fragment_count`
- `iresfinder_model`
- `odesign_input_json_filepath`
- `odesign_output_dir`
- `odesign_prediction_filepaths`
- `odesign_run_log_filepath`
- `odesign_model_name`
- `odesign_design_modality`
- `vienna_sirna_duplex_mfe`
- `vienna_aso_mean_unpaired`
- `vienna_aso_joint_unpaired`
- `vienna_inverse_best_sequence`
- `blast_hit_count`
- `blast_tabular_tsv_filepath`
- `blast_subject_mode`

### 5.5 Critic

当前是**规则 Critic**，不调用 LLM。

逻辑：

- siRNA：
  - 如果 `off_target_genes > 0`，则 reject 并重试
- mRNA 结构预测：
  - 如果用户请求里有结构相关语义，并且 `mfe > -20.0`，则 reject 并重试
  - **注意**：判断条件是严格的数值比较。短序列经 ViennaRNA 得到的 MFE 常在 **-2 ~ -10 kcal/mol** 量级，同样满足 `mfe > -20.0`，因此会反复 reject，直到 **`retry_count` 达到 `max_retries` 后强制 pass**；这**不会**使 MFE 自动变得更负，仅体现当前规则与短链热力学尺度不匹配。若产品上要接受此类真实预测，应调整阈值或规则（见 §14.18）。
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
- `8012`: `odesign_service`
- `8013`: `iresfinder_service`
- `8014`: `lineardesign_service`
- `8015`: `linearfold_service`
- `8016`: `evitar_service`
- `8017`: `sgrna_design_service`
- `8018`: `codonw_slim_service`
- `8019`: `blast_service`（NCBI BLAST+ `blastn`）

后续新增工具也建议继续顺延，例如：

- `8020`: 新工具 C
- `8021`: 新工具 D

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

ViennaRNA 已经成功接入，作为“真实工具接入模板”。微服务在具备 **RNAlib**（`import RNA`）时优先用库内折叠；否则自动回退到 **`RNAfold` 命令行**，便于部分仅安装了可执行文件的环境。

### 8.0 上游源码层（git submodule）

目录：

```text
external_repos/ViennaRNA
```

来源：

- 上游仓库：[ViennaRNA/ViennaRNA](https://github.com/ViennaRNA/ViennaRNA.git)

当前建议：

- 通过 **git submodule** 管理；克隆或拉取主仓库后执行 `git submodule update --init --recursive`
- **默认部署**仍推荐在 `viennarna_fold` 的 Conda 环境中安装 **bioconda `viennarna`**（与 `environment.yml` 一致），即可使用 RNAlib
- 子模块源码用于版本对照、阅读官方安装说明；**可选**在 Linux 上按上游流程自编译（见 `microservices/viennarna_fold/build_from_submodule_linux.sh`），不作为大多数部署的必做步骤

### 8.1 微服务层

目录：

```text
microservices/viennarna_fold/
```

文件：

- `environment.yml`（`python=3.10` + bioconda `viennarna` + FastAPI 栈；文件头注释说明了 conda 为主、子模块为可选上游）
- `main.py`（二级结构：`RNAlib` 或 `RNAfold --noPS`；siRNA 双链：`RNAlib` 或 `RNAcofold`；ASO 可及性：`RNAplfold` 解析 `*_lunp`；逆折叠：`RNAinverse`）
- `start.sh`
- `build_from_submodule_linux.sh`（可选；在 Linux 上将子模块 `configure --prefix="${CONDA_PREFIX}" --with-python` 后安装到当前激活的 Conda 环境；依赖 autotools、swig 及上游 README 中的 `src` 下归档解压步骤）

接口（**默认端口 `8003`**）：

- `GET /health`
  - `status`：`rnalib` 与 `rnafold_cli` 至少其一可用时为 `ok`，否则为 `degraded`
  - `rnalib`、`rnafold_cli`、`rnacofold_cli`、`rnaplfold_cli`、`rnainverse_cli`
  - `extensions_ready`：`RNAcofold` / `RNAplfold` / `RNAinverse` 与 duplex+plfold+inverse 扩展链路是否齐备（布尔）

- `POST /fold` — 单序列 MFE 二级结构（与历史行为一致）

输入：`sequence`（RNA）

输出：`sequence`、`structure`、`mfe`、`backend`（`RNAlib` 或 `RNAfold-cli`）、`model`

- `POST /sirna-duplex` — siRNA **正反义链共折叠**（`sense&antisense` 热力学）

输入（二选一）：

- `sense` + `antisense`（各为 5'→3' RNA 文本），或
- `fasta_content`（两段 FASTA：先 sense 后 antisense）

输出：`sense`、`antisense`、`cofold_sequence`（含 `&`）、`structure`、`mfe`、`backend`、`model`

- `POST /aso-accessibility` — **RNAplfold** 局部未配对概率，用于 ASO / 反义寡核苷酸靶区可及性

输入：`sequence`（全长靶 RNA，可为 FASTA）、`region_start` / `region_end`（**1-based 闭区间**）、`aso_oligo_length`（默认 18）、`winsize` / `span` / `unpaired_ulength` / `temp_c`

输出：`sequence_length`、`mean_unpaired_prob_single_nt`、`joint_unpaired_prob_stretch_ending_at_region_end`（可能为 `null`，取决于 `-u` 与区间长度）、`backend` 等

**部署注意**：部分发行版自带的 `RNAplfold` **不支持** `--noPS`；当前实现**不会**对该子进程传入 `--noPS`，以避免 `unrecognized option '--noPS'`。临时工作目录中可能产生 `*_dp.ps` 等文件，随临时目录删除。

- `POST /inverse-fold` — **RNAinverse** 二级结构逆折叠

输入：`structure`（点括号）、可选 `start_sequence`、可选 `repeats`、`temp_c`、`function_mode`（`m` / `p` / `mp`）

输出：`best_sequence`、`hamming_distance`、`backend`、`model` 等

### 8.2 Agent 工具层

工具函数：

- `predict_rna_secondary_structure(filepath, service_url="http://localhost:8003/fold")`  
  - 当前返回格式为单行字符串，例如：`filepath=...; structure=...; mfe=...; backend=RNAlib`  
  - 当服务端未返回 `backend` 字段时，工具字符串中可能省略 `; backend=...` 段。

- `compute_sirna_duplex_binding_vienna(filepath, service_url="http://127.0.0.1:8003/sirna-duplex")`  
  - 返回结构化 `dict`（`mfe_kcal_per_mol`、`structure`、`sense`、`antisense` 等）。

- `compute_aso_target_accessibility_vienna(filepath, region_start, region_end, service_url="http://127.0.0.1:8003/aso-accessibility", ...)`  
  - 返回 `mean_unpaired_prob_single_nt`、`joint_unpaired_prob_stretch_ending_at_region_end` 等。

- `inverse_fold_rna_secondary_structure_vienna(filepath, service_url="http://127.0.0.1:8003/inverse-fold", ...)`  
  - 返回 `best_sequence`、`best_sequence_filepath`（写入 `workspace/`）等。

### 8.3 验证状态（补充）

- 已在 Linux 上完成 `GET /health`、`POST /fold`、`POST /sirna-duplex`、`POST /aso-accessibility`、`POST /inverse-fold` 的闭环验证（Conda `viennarna` + 对应 CLI）
- 自然语言前端在触发二级结构预测、duplex、ASO 可及性或逆折叠时，需保证 **`viennarna_fold` 在 `8003` 已启动**；注意 §5.5 / §14.18 中 **Critic 与 MFE 阈值** 对默认「结构预测型」分支里短序列行为的影响（duplex / ASO / inverse 分支通常不触发该条 mRNA MFE 规则，但以实际路由为准）

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

#### 默认参考基因组可通过环境变量覆盖

当前 `crisot_service` 支持可选环境变量：

- `CRISOT_DEFAULT_REF_GENOME`

用于覆盖默认参考基因组路径（默认是上游仓库中的 `script/hg38.fa`）。

适用场景：

- 服务器上希望统一把默认参考基因组指到本地绝对路径
- `score` 请求不显式传 `genome_path` 时，希望仍能稳定使用服务器上的指定参考基因组

建议在 Linux 服务器启动服务前设置，例如：

```bash
export CRISOT_DEFAULT_REF_GENOME=/absolute/path/to/genome.fa
```

#### `/health` 诊断字段与状态语义

当前 `GET /health` 会额外返回：

- `default_ref_genome_env_var`
- `default_ref_genome_env_value`
- `missing_requirements`
- `warnings`

状态语义：

- `status=ok`：服务必需条件满足（上游仓库与核心参数文件可用）
- `status=degraded`：存在必需依赖缺失（如上游仓库或 `crisot_score_param.pkl` 缺失）

说明：

- 若仅默认参考基因组文件不存在，当前会进入 `warnings`，不直接降级为 `degraded`
- 这样可以避免在“仅跑 `/score` 且显式传参”的场景下误报不可用

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
- 已在本地完成最小 smoke test：`GAGTCCGAGCAGAAGAAGAANGG` vs `GAGTCCGAGGAGAAGACGAAGGG`，得分 `0.6892195294509914`（与上游 README 示例一致）
- `/optimize` 已在 Linux 服务器上成功触发真实 `Cas-OFFinder` 链路
- 已修复 `pandas>=2` 下的 `DataFrame.append()` 兼容性问题
- 前端自然语言测试已通过

这意味着：

- `CRISOT` 已经通过“上游源码 -> 微服务接口 -> Agent 工作流 -> 前端自然语言触发”这一层验证
- 当前项目里已经具备真实的 CRISPR off-target 打分与优化能力

---

## 10F. ODesign 的接入方式

### 10F.1 上游源码层

目录：

```text
external_repos/ODesign
```

来源：

- 上游仓库：[OTeam-AI4S/ODesign](https://github.com/OTeam-AI4S/ODesign.git)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 vendoring 进主仓库历史

### 10F.2 为什么当前采用“项目内微服务封装”

当前接入的 `ODesign` 不是直接让 Agent 去调用上游内部 Python 模块，而是采用：

- 保留上游源码仓库
- 在 `microservices/odesign_service/` 中封装稳定 REST 入口

这样做的原因是：

- 上游推理入口是 JSON 驱动的命令行脚本
- 运行环境依赖 Linux + CUDA 12.1，更适合作为服务器侧工具
- 输出目录中会产生多份 `*.cif` / `run.log` / traceback 文件，更适合通过文件路径管理
- 本项目仍然希望保持“Agent 不直接耦合第三方仓库内部实现”的架构原则

### 10F.3 当前微服务能力

目录：

```text
microservices/odesign_service/
```

当前已封装接口：

- `GET /health`
- `POST /design/from-json`

输入：

- `input_json_path`
- `infer_model_name`
- `design_modality`
- `exp_name`
- `seeds_json`
- `n_sample`
- `use_msa`
- `num_workers`
- `cuda_visible_devices`

输出：

- `output_dir`
- `prediction_filepaths`
- `sample_names`
- `run_log_path`
- `error_filepaths`
- `stdout`
- `stderr`

### 10F.4 当前 Agent 工具能力

工具函数：

- `run_odesign_inference(input_json_filepath, service_url="http://127.0.0.1:8012/design/from-json", infer_model_name="odesign_base_na_rigid", design_modality="rna", ...)`

当前实现会把：

- ODesign 生成的 `*.cif`
- `run.log`
- 服务 stdout / stderr
- error logs

复制回 `workspace/`，这样上层 Agent 仍然以文件路径和摘要信息为主。

### 10F.5 当前工作流集成方式

当前 `Router / mRNA specialist / tool_execution` 已经接入 `ODesign`：

- `router_node` 会识别 `odesign`
- `mrna_specialist_node` 当前支持三种规则入口：
  - 显式传入 `.json` 路径
  - `RNA backbone` / `length=...`
  - `protein-binding RNA` 自然语言请求

当前 `protein-binding RNA` 规则解析支持：

- `ref_file=/path/to/file.cif`
- `hotspot=C/18,C/90,C/79,C/49`
- `length=61`
- `protein_chain=C`
- `protein_segment=C/1-96`
- `sample_name=my_case`

其中：

- 如果用户没有显式给 `protein_segment`
- 但给了 `protein_chain`，或 hotspot 链本身足够明确
- 当前节点会尝试从参考结构文件自动推断蛋白链残基范围

### 10F.6 ODesign 的实际运行注意事项

#### 推荐运行环境

当前更合理的实际运行方式是：

- Linux
- Conda
- Python 3.10
- CUDA 12.1
- NVIDIA GPU

macOS 不作为 ODesign 的最终运行环境，只适合开发与推送代码。

#### 推理所需 checkpoint

当前 RNA 相关最小推理闭环至少需要：

```text
external_repos/ODesign/ckpt/odesign_base_na_rigid.pt
external_repos/ODesign/ckpt/oinvfold_rna.ckpt
```

其中：

- `odesign_base_na_rigid.pt` 来自 ODesign 主模型
- `oinvfold_rna.ckpt` 来自 OInvFold

可通过上游脚本下载：

```bash
cd external_repos/ODesign
bash ckpt/get_odesign_ckpt.sh ckpt
```

#### 推理所需 data 文件

当前推理还需要至少准备：

```text
external_repos/ODesign/data/components.v20240608.cif
external_repos/ODesign/data/components.v20240608.cif.rdkit_mol.pkl
```

注意：

- `odesign_full_data.tar.gz` 是训练数据，不是最小推理闭环所必需
- 当前项目只要求部署推理所需的两个 data 文件

#### 依赖版本注意事项

当前实际调试中已经遇到两类常见环境坑：

- `biotite` 版本过低时，可能缺少 `biotite.interface.rdkit`
- `networkx` 版本漂移时，可能触发上游导入期异常

当前更稳妥的原则是：

- 保持与上游 `requirements.txt` 尽量一致
- 如果为了 `biotite.interface.rdkit` 需要升级 `biotite`
- 应优先以服务器上的真实最小推理闭环结果为准，而不是只看 dependency resolver 警告

#### 服务器侧下载资源，开发机不跑重推理

当前推荐工作方式仍然是：

- macOS：改代码、提交 GitHub
- Linux 服务器：下载 ODesign checkpoint / data、创建环境、启动服务、执行推理

### 10F.7 当前验证状态

`ODesign` 目前已经完成以下验证：

- 上游源码已成功以 submodule 形式接入
- `odesign_service` 已成功接入项目
- `RNA backbone` 上游最小推理已在 Linux 服务器跑通
- `protein-binding RNA` 上游示例已可作为微服务输入
- Agent 自然语言已成功触发：
  - `RNA backbone`
  - `protein-binding RNA`
- 已修复自然语言 `hotspot=... length=...` 解析问题

这意味着：

- `ODesign` 已经通过“上游源码 -> 微服务接口 -> Agent 工作流 -> 前端自然语言触发”这一层验证
- 当前项目里已经具备真实的 ODesign RNA 设计入口
- 但复杂 ODesign 任务仍建议优先通过显式 JSON 输入，避免规则解析覆盖不足

---

## 10G. IRESfinder 的接入方式

### 10G.1 上游源码层

目录：

```text
external_repos/IRESfinder
```

来源：

- 上游仓库：[xiaofengsong/IRESfinder](https://github.com/xiaofengsong/IRESfinder.git)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 vendoring 进主仓库历史

### 10G.2 为什么当前采用“项目内 Python 3 微服务封装”

当前接入的 `IRESfinder` 不是直接依赖上游 Python 2 入口脚本，而是采用：

- 保留上游源码仓库及其训练数据
- 在 `microservices/iresfinder_service/` 中重建 Python 3 可部署推理入口

这样做的原因是：

- 主项目微服务栈统一为 Python 3
- 上游流程可复用的核心资源是 `module/train.data`
- 需要标准 REST API 供 Agent 稳定调用

### 10G.3 当前微服务能力

目录：

```text
microservices/iresfinder_service/
```

当前已封装接口：

- `GET /health`
- `POST /predict`

输入：

- `fasta_content`
- `mode`（默认 0）
- `window_size`（默认 174）
- `step_size`（默认 50）
- `decision_threshold`（默认 0.5）

输出：

- `has_putative_ires`
- `best_fragment_id`
- `max_score`
- `positive_count`
- `fragment_count`
- `result_tsv_path`
- `predictions`

### 10G.4 当前 Agent 工具能力

工具函数：

- `predict_putative_ires_with_iresfinder(filepath, service_url="http://127.0.0.1:8013/predict", mode=0, window_size=174, step_size=50, decision_threshold=0.5)`

输入：

- `filepath`，其中保存的是 RNA 序列或 FASTA 内容

输出：

- `has_putative_ires`
- `best_fragment_id`
- `max_score`
- `positive_count`
- `fragment_count`
- `result_tsv_filepath`

### 10G.5 当前工作流集成方式

当前 `Router / mRNA specialist / tool_execution` 已接入 `IRESfinder`：

- `router_node` 会识别 `iresfinder` / `ires` / `internal ribosome` 等语义
- `mrna_specialist_node` 会在 RNA-ligand / RNASTOP 分支之外优先匹配 IRES 语义并触发 IRESfinder
- `tool_execution_node` 会更新以下额外状态：
  - `iresfinder_result_tsv_filepath`
  - `iresfinder_has_putative_ires`
  - `iresfinder_max_score`
  - `iresfinder_best_fragment_id`
  - `iresfinder_positive_count`
  - `iresfinder_fragment_count`
  - `iresfinder_model`

### 10G.6 IRESfinder 的实际运行注意事项

当前服务默认要求以下目录存在：

```text
external_repos/IRESfinder/module/train.data
```

推荐运行环境：

- Linux
- Conda
- Python 3.10

服务启动方式：

```bash
cd rna_agent_system/microservices/iresfinder_service
conda env create -f environment.yml
conda activate iresfinder_service_env
bash start.sh
```

### 10G.7 当前验证状态

IRESfinder 目前已经完成最小闭环验证：

- 上游仓库已以 submodule 形式接入
- `iresfinder_service` 可启动
- `GET /health` 成功
- `POST /predict` 成功返回 IRES 评分摘要
- Agent 工作流已可触发 IRESfinder 并回填 `final_report` 字段

这意味着：

- IRESfinder 已完成“上游源码 -> 微服务接口 -> Agent 工作流”的接入链路
- 当前项目已具备 IRES 相关快速筛查能力

---

## 10H. LinearDesign 的接入方式

### 10H.1 上游源码层

目录：

```text
external_repos/LinearDesign
```

（完整路径为 `rna_agent_system/external_repos/LinearDesign`。）

来源：

- 上游仓库：[LinearDesignSoftware/LinearDesign](https://github.com/LinearDesignSoftware/LinearDesign.git)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 `git add .`

### 10H.2 为什么当前采用“微服务 + 直接调用二进制”

当前接入的 LinearDesign 不是依赖上游仓库里的 `lineardesign` Python 2 包装脚本（`#!/usr/bin/env python2`），而是采用：

- 保留上游源码与 `Makefile`
- 在 `microservices/lineardesign_service/` 中通过子进程调用 `bin/LinearDesign_2D`

这样做的原因是：

- 主项目微服务栈统一为 Python 3
- 服务器侧以 `make` 编译出的 `LinearDesign_2D` 为稳定入口，避免 Python 2 运行时依赖

### 10H.3 当前微服务能力

目录：

```text
microservices/lineardesign_service/
```

当前已封装接口：

- `GET /health`
- `POST /generate/cds`

输入：

- `protein_sequence`
- `lambda_value`（默认 `0.0`）
- `codon_usage_path`（可选；默认使用上游自带 `codon_usage_freq_table_human.csv`）
- `verbose`（可选）

输出：

- `generated_sequence`
- `structure`
- `mfe`
- `cai_score`
- `codon_usage_path`
- `raw_output` / `stderr`

### 10H.4 当前 Agent 工具能力

工具函数：

- `design_mrna_cds_with_lineardesign(filepath, service_url="http://127.0.0.1:8014/generate/cds", lambda_value=0.0, codon_usage_path=None, verbose=False)`

输入：

- `filepath`，其中保存的是蛋白序列

输出：

- `generated_sequence`
- `output_filepath`
- `structure` / `mfe` / `cai_score` 等摘要字段

### 10H.5 当前工作流集成方式

当前 `Router / mRNA specialist / tool_execution` 已接入 LinearDesign：

- `router_node` 会识别 `lineardesign` / `linear design` 等语义（与既有 mRNA 关键词一起路由到 `mrna_specialist`）
- `mrna_specialist_node` 在用户显式提到 LinearDesign 且请求仍偏“设计型”时，优先触发 `design_mrna_cds_with_lineardesign`
- 若用户请求中还包含结构预测语义，`tool_execution_node` 在拿到 CDS 输出后可继续自动调用 ViennaRNA / RhoFold（与 GEMORNA / RNARL 分支一致）

### 10H.6 LinearDesign 的实际运行注意事项

#### 编译与二进制路径

部署后必须在 submodule 目录执行编译：

```bash
cd rna_agent_system/external_repos/LinearDesign
make
```

成功后应存在：

```text
rna_agent_system/external_repos/LinearDesign/bin/LinearDesign_2D
```

微服务默认按 **`rna_agent_system/external_repos/LinearDesign`** 解析上游目录（与 `microservices/lineardesign_service/main.py` 相对路径一致）；若需覆盖，可在启动服务前设置：

```bash
export LINEARDESIGN_ROOT=/absolute/path/to/LinearDesign
```

#### 推荐运行环境

- Linux
- `g++` 可成功链接上游提供的 `LinearDesign_linux64.so`（或 Makefile 回退的 `LinearDesign_linux64_old.so`）

#### Conda 环境

```bash
cd rna_agent_system/microservices/lineardesign_service
conda env create -f environment.yml
conda activate lineardesign_service_env
bash start.sh
```

若环境已存在，可使用：

```bash
conda env update -f environment.yml --prune
```

### 10H.7 当前验证状态

LinearDesign 目前已经完成以下最小闭环验证：

- 上游源码以 submodule 形式置于 `rna_agent_system/external_repos/LinearDesign`
- Linux 上 `make` 成功生成 `bin/LinearDesign_2D`
- `lineardesign_service` 可启动，`GET /health` 与 `POST /generate/cds` 成功
- Agent 工具层已封装 HTTP 调用，规则工作流可显式关键词触发

这意味着：

- LinearDesign 已具备“上游编译产物 -> 微服务接口 -> Agent 工具”的标准接入形态
- 与 `mock_codon_optimization` 不同，这是**真实的蛋白到 mRNA CDS 设计**能力之一（与 GEMORNA / RNARL 并列可选）

---

## 10I. LinearFold 的接入方式

### 10I.1 上游源码层

目录：

```text
external_repos/LinearFold
```

（完整路径为 `rna_agent_system/external_repos/LinearFold`。）

来源：

- 上游仓库：[LinearFold/LinearFold](https://github.com/LinearFold/LinearFold.git)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 `git add .`
- 建议在 `.gitmodules` 中为该子模块设置 `ignore = untracked`，避免 `make` 生成 `bin/` 后主仓库长期显示子模块脏状态

### 10I.2 为什么当前采用“微服务 + 调用上游脚本”

当前接入的 LinearFold 采用：

- 保留上游源码与 `Makefile`
- 在 `microservices/linearfold_service/` 中通过子进程调用上游 `linearfold` 脚本

这样做的原因是：

- 与现有工具链一致，保持 Python 3 的 REST 微服务入口
- 上游 `linearfold` 脚本本身会调度 `bin/linearfold_c` / `bin/linearfold_v`，便于统一参数透传

### 10I.3 当前微服务能力

目录：

```text
microservices/linearfold_service/
```

当前已封装接口：

- `GET /health`
- `POST /fold`

输入：

- `sequence`
- `beam_size`（默认 `100`）
- `use_vienna`（默认 `false`，为 `true` 时走 `LinearFold-V`）
- `dangles`（仅支持 `0` 或 `2`）

输出：

- `sequence`
- `structure`
- `mfe`
- `backend`（`LinearFold-C` / `LinearFold-V`）
- `model`

### 10I.4 当前 Agent 工具能力

工具函数：

- `predict_rna_secondary_structure_with_linearfold(filepath, service_url="http://127.0.0.1:8015/fold", beam_size=100, use_vienna=False, dangles=2)`

当前行为：

- 结构预测分支默认仍使用 ViennaRNA
- 当用户请求中显式包含 `linearfold`（或不与 `lineardesign` 冲突的 `linear fold`）时，工作流切到 LinearFold 工具
- 已支持从自然语言解析：
  - `beam_size` / `beamsize` / `beam`
  - `dangles=0|2`
  - `linearfold-v` / `linearfold_v` / 与 `linearfold` 同句 `vienna`（自动置 `use_vienna=true`）

### 10I.5 LinearFold 的实际运行注意事项

#### 编译与二进制路径

部署后必须在 submodule 目录执行编译：

```bash
cd rna_agent_system/external_repos/LinearFold
make
```

成功后应存在：

```text
rna_agent_system/external_repos/LinearFold/bin/linearfold_c
rna_agent_system/external_repos/LinearFold/bin/linearfold_v
```

微服务默认按 `rna_agent_system/external_repos/LinearFold` 解析上游目录；若需覆盖，可在启动服务前设置：

```bash
export LINEARFOLD_ROOT=/absolute/path/to/LinearFold
```

#### Conda 环境

```bash
cd rna_agent_system/microservices/linearfold_service
conda env create -f environment.yml
conda activate linearfold_service_env
bash start.sh
```

若环境已存在，可使用：

```bash
conda env update -f environment.yml --prune
```

### 10I.6 当前验证状态

LinearFold 目前已经完成以下最小闭环验证：

- 上游源码以 submodule 形式置于 `rna_agent_system/external_repos/LinearFold`
- 本地 `make` 成功生成 `bin/linearfold_c` 与 `bin/linearfold_v`
- `linearfold_service` 的 `GET /health` 与 `POST /fold` 成功
- Agent 规则分支已可通过 `linearfold` 关键词触发 LinearFold 二级结构预测

这意味着：

- LinearFold 已具备“上游编译产物 -> 微服务接口 -> Agent 工具”的标准接入形态
- 当前项目在 RNA 二级结构上已同时具备 ViennaRNA（默认）和 LinearFold（显式触发）两条可用路径

---

## 10J. Evitar 的接入方式

### 10J.1 上游源码层

目录：

```text
external_repos/Evitar
```

（完整路径为 `rna_agent_system/external_repos/Evitar`。）

来源：

- 上游仓库：[dingyaozhang/Evitar](https://github.com/dingyaozhang/Evitar.git)

当前建议：

- 优先通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 vendoring 进主仓库历史

### 10J.2 为什么当前采用“微服务 + 调用 Perl CLI”

当前接入的 Evitar 采用：

- 保留上游源码与 `bin/`
- 在 `microservices/evitar_service/` 中通过子进程调用 `perl Evitar.pl`

这样做的原因是：

- 与现有工具链一致，统一走 Python 3 的 REST 接口
- Evitar 本体是 Perl CLI，直接作为底层执行入口更稳
- 输出文件可落到 `workspace/`，便于 Agent 只传路径

### 10J.3 当前微服务能力

目录：

```text
microservices/evitar_service/
```

当前已封装接口：

- `GET /health`
- `POST /design`

`/design` 输入：

- `input_path`
- `mode`（`existing` / `predesign`）
- `predict`（`predsi` / `rnaxs` / `CRISPR`）
- `strains_path`（`existing` 模式必需）
- `off_target`
- `ncores`
- 可选高级参数：
  - `p3utr_path`
  - `transcriptome_path`
  - `weight_path`
  - `limitnum`
  - `repeatnum`
  - `sumtype`
  - `pmcuff`
  - `umcuff`
  - `mircuff`
  - `maxgc`
  - `mingc`
  - `middlegc`

`/design` 输出：

- `mode`
- `predict`
- `input_path`
- `output_path`
- `result_count`
- `top_results`
- `command`
- `stdout`
- `stderr`

### 10J.4 当前 Agent 工具能力

工具函数：

- `design_sirna_with_evitar(filepath, mode="existing", predict="predsi", strains_path=None, off_target=False, ncores=1, service_url="http://127.0.0.1:8016/design")`

输入：

- `filepath`（输入 FASTA）
- `mode` / `predict` / `strains_path` 等可选透传参数

输出：

- `output_filepath`
- `mode`
- `predict`
- `result_count`
- `top_results`
- `command`

### 10J.5 当前工作流集成方式

当前 `Router / siRNA specialist / tool_execution` 已接入 Evitar：

- `router_node` 会识别 `evitar`、`predesign`、`future virus`、`rnaxs`、`predsi`、`cas13`
- `sirna_specialist_node` 在命中 Evitar 请求时，优先分发 `design_sirna_with_evitar`
- `tool_execution_node` 会回填：
  - `evitar_mode`
  - `evitar_predict`
  - `evitar_output_filepath`
  - `evitar_result_count`
  - `evitar_command`

当前规则还加入了防误路由兜底：

- 若 Evitar 请求误入 `mrna_specialist`，会在节点内部回退到 Evitar 工具调用

### 10J.6 Evitar 的实际运行注意事项

#### 运行环境

Evitar 上游 README 明确要求：

- Linux
- Perl5

当前更稳妥的部署方式：

- macOS 仅用于改代码与推仓库
- Linux 服务器用于启动服务与实际验证

#### 上游 `bin/` 可执行文件

Evitar 仓库自带 `bin/` 中的可执行文件（如 `RNAplfold`、`muscle3.8.31_i86linux64`）是 Linux 构建产物。

因此在 macOS 上直接运行时常见：

- `cannot execute binary file`

这不代表接入失败，而是运行平台不匹配。

#### `/health` 诊断字段

当前 `evitar_service` 的 `/health` 会额外给出：

- `linux_runtime`
- `perl_path`
- `evitar_script_exists`
- `binaries.<name>.exists`
- `binaries.<name>.executable`

建议把它作为服务器侧第一检查点。

### 10J.7 当前验证状态

Evitar 已完成以下接入验证：

- 上游仓库已接入 `external_repos/Evitar`
- `evitar_service` 已完成 API 封装（`/health` + `/design`）
- Agent 工具层已封装 `design_sirna_with_evitar`
- 规则工作流已支持 Evitar 关键词触发并回填状态

当前结论：

- Evitar 属于 Linux 优先工具
- 最终可用性验证应以 Linux 服务器结果为准

---

## 10K. sgrna_design 的接入方式

### 10K.1 上游源码层

目录：

```text
external_repos/sgrna_design
```

来源：

- 上游仓库：[bitguolab/sgrna_design](https://github.com/bitguolab/sgrna_design.git)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 vendoring 进主仓库历史

### 10K.2 为什么当前采用“项目内微服务封装”

当前接入的 `sgrna_design` 不是直接让 Agent 运行上游 `sample.py`，而是采用：

- 保留上游源码仓库
- 在 `microservices/sgrna_design_service/` 中封装稳定 REST 入口

这样做的原因是：

- 上游 `environment.yml` 信息不完整
- 上游脚本默认强依赖 `cuda:0`
- 需要把参数解析、输出落盘、CPU/GPU 选择统一到当前项目规范

### 10K.3 当前微服务能力

目录：

```text
microservices/sgrna_design_service/
```

当前已封装接口：

- `GET /health`
- `POST /design`

`/design` 输入：

- `seed_sequence`
- `n_samples`
- `mutation_number`
- `temperature`
- `max_overlap`
- `device`

`/design` 输出：

- `generated_count`
- `model_path`
- `device`
- `output_fasta_path`
- `summary_json_path`
- `candidates`

### 10K.4 当前 Agent 工具能力

工具函数：

- `design_sgrna_handle_with_crgpt(filepath, n_samples=10, mutation_number=22, temperature=1.0, max_overlap=21, device=None, service_url="http://127.0.0.1:8017/design")`

输入：

- `filepath`（种子序列文件路径）

输出：

- `best_sequence`
- `best_nn_score`
- `best_mutation_count`
- `output_fasta_filepath`
- `summary_json_filepath`
- `best_sequence_filepath`

### 10K.5 当前工作流集成方式

当前 `Router / crispr_specialist / tool_execution` 已接入 `sgrna_design`：

- `router_node` 会识别 `sgrna handle` / `sgrna design` / `crgpt` / `sgrna_design`
- `crispr_specialist_node` 命中后会优先分发 `design_sgrna_handle_with_crgpt`
- `tool_execution_node` 会回填：
  - `sgrna_design_generated_count`
  - `sgrna_design_best_nn_score`
  - `sgrna_design_best_mutation_count`
  - `sgrna_design_output_filepath`
  - `sgrna_design_summary_filepath`
  - `sgrna_design_model_path`

### 10K.6 实际运行注意事项

#### torch 安全版本要求

上游模型文件为 `pytorch_model.bin`（非 safetensors），因此服务环境需满足：

- `torch>=2.6`

否则可能触发 `torch.load` 的安全限制报错（与 `CVE-2025-32434` 相关）。

#### GPU 版本匹配

当前已验证过一个常见环境坑：

- 如果错误安装了 `torch + cu130`，而服务器驱动只支持到 CUDA 12.x（例如 12.8）
- 会导致 `torch.cuda.is_available() == False`

更稳妥的原则是：

- 让 torch CUDA 构建版本与服务器驱动代际匹配（例如 `cu128`）
- 如需抢占空闲卡，可通过 `CUDA_VISIBLE_DEVICES` 限制设备

### 10K.7 当前验证状态

`sgrna_design` 已完成以下接入验证：

- 上游仓库已以 submodule 形式接入
- `sgrna_design_service` 已完成 API 封装（`/health` + `/design`）
- Agent 已支持自然语言触发 sgRNA handle 设计分支
- 已修复：
  - 长度溢出导致的 `index out of range` 问题
  - 推理打分阶段 tensor 维度问题
  - 前端 `seed=...` 被误截断为短序列的问题

当前结论：

- `sgrna_design` 已通过“上游源码 -> 微服务接口 -> Agent 工作流”接入链路
- 最终可用性验证应以 Linux 服务器实际运行结果为准

---

## 10L. codonw-slim 的接入方式

### 10L.1 上游源码层

目录：

```text
external_repos/codonw-slim
```

来源：

- 上游仓库：[smsaladi/codonw-slim](https://github.com/smsaladi/codonw-slim.git)

当前建议：

- 通过 **git submodule** 管理
- 不要把整个上游仓库当普通目录直接 `git add .`

### 10L.2 为什么采用「微服务 + HTTP」而不是 Agent 直接 import

- `codonw-slim` 为 **Cython + C** 扩展，编译与 ABI 与 Python/编译器版本强相关
- 与主 Agent 环境隔离，部署失败面更小
- 保持与其它工具一致：**Agent 只通过 HTTP 调用**，不直接耦合上游 Python/C 实现

### 10L.3 当前微服务能力

目录：

```text
microservices/codonw_slim_service/
```

文件：

- `environment.yml`（`python=3.10` + conda-forge 的 `numpy` / `pandas` / `cython` / `setuptools` / `wheel`；`pip` 安装 FastAPI 栈）
- `main.py`（`GET /health`、`POST /analyze/cds`）
- `start.sh`（默认端口 **8018**；启动前检测 `codonw` 是否已安装）
- **`install_codonw_slim.sh`**（**必须**：`pip install --no-build-isolation -e` 子模块，并在每次安装前对上游 `codonw.pyx` 做 **Python 3 兼容补丁**）

接口（**默认端口 `8018`**）：

- `GET /health`  
  - `status`：`codonw_import_ok` 为真时为 `ok`，否则为 `degraded`

- `POST /analyze/cds` — CDS 密码子使用及相关指标

输入（JSON）：

- `sequence`（必填）：编码序列，DNA 或 RNA（`U`→`T`），可为 FASTA
- `genetic_code`（默认 `0`，范围 `0--7`，与上游 `CodonSeq` 一致）
- `cai_ref`（默认 `0`，范围 `0--2`）
- `fop_ref`（默认 `0`，范围 `0--7`）
- `factor_in_rare`（布尔，传入 `CodonSeq.fop`）
- `include_codon_tables`（布尔，是否返回 `codon_usage` / `rscu`）
- `include_dinucleotide`（布尔，是否返回 `dinuc` 表）

输出（摘要字段，完整结构见接口 JSON）：

- `cai`、`fop`、`cbi`、`enc`、`hydropathy`、`aromaticity`
- `silent_base_usage`、`bases2`
- 可选：`codon_usage`、`rscu`、`dinuc`

说明：

- 上游 **不对** CDS 做起始密码子 / 终止密码子 / 内含子等校验；输入应为 **可读框内的 CDS**。长度非 3 倍数时，服务会截去末尾 1--2 个碱基并在 `normalization_note` 中说明。

### 10L.4 当前 Agent 工具能力

工具函数：

- `analyze_cds_codon_metrics_with_codonw_slim(filepath, service_url="http://127.0.0.1:8018/analyze/cds", genetic_code=0, cai_ref=0, fop_ref=0, factor_in_rare=False, include_codon_tables=False, include_dinucleotide=False)`

输入：

- `filepath`：`workspace/` 或项目内路径，内容为 CDS（与 RNASTOP 输入解析同源时可从自然语言写入）

输出（字典，节选）：

- `metrics_json_filepath`：完整服务响应写入 `workspace/codonw_metrics_*.json`
- `cai_score`、`enc`、`fop`、`cbi`、`hydropathy`、`aromaticity` 等标量摘要

### 10L.5 当前工作流集成方式

- `router_node` 已增加 `codonw` / `codonw-slim` / `codon bias` 等关键词，与其它 mRNA 关键词一起路由到 `mrna_specialist`
- `mrna_specialist_node`：
  - **独立分支**：命中 §5.3 所述 codonw 专用语义时，仅调用 `analyze_cds_codon_metrics_with_codonw_slim`
  - **默认「结构预测型」分支**：在 `predict_rna_secondary_structure`（或 LinearFold）**之前**调用 `analyze_cds_codon_metrics_with_codonw_slim`，替代历史上的 `mock_codon_optimization` 占位
- `tool_execution_node` 会回填：`cai_score`、`codonw_metrics_filepath`、`codonw_enc`、`codonw_fop`、`codonw_cbi` 等
- `critic_node` 对 codonw **本身**无单独 reject；若同一句请求仍含 **fold / 二级结构** 等语义，则仍可能触发 §14.18 的 MFE 规则

### 10L.6 实际运行注意事项（部署 checklist）

推荐运行环境：

- **Linux** + **Conda** + **Python 3.10**（与 `environment.yml` 一致）
- 系统已安装 **gcc** 等 C 编译工具链

推荐安装顺序：

```bash
cd rna_agent_system/microservices/codonw_slim_service
conda env create -f environment.yml
conda activate codonw_slim_service_env
bash install_codonw_slim.sh
bash start.sh
```

`install_codonw_slim.sh` 解决两类常见问题：

1. **`pip` 隔离构建环境缺少 `Cython`**：使用 `pip install --no-build-isolation -e ...`，复用当前 Conda 环境内的 `cython` / `numpy`
2. **上游 `codonw.pyx` 使用 `astype(long)`**：在 Python 3 / 新版 Cython 下编译失败；脚本在每次安装前替换为 `astype(np.int64)`

若 **`conda env create` 曾失败**且环境处于半安装状态，可先 `conda env remove -n codonw_slim_service_env` 再按上表重建。

### 10L.7 当前验证状态

- 已在 **Linux 服务器** 上完成：`install_codonw_slim.sh` 成功、`start.sh` 常驻、`GET /health` 与 `POST /analyze/cds` 闭环可用
- Agent 规则层已接入独立 codonw 分支与默认结构预测链路的前置指标

---

## 10M. BLAST+（blastn）的接入方式

### 10M.1 定位

当前接入的是 **NCBI BLAST+** 中的 **`blastn`**（核酸对核酸），用于：

- 在用户自备的 **subject 多序列 FASTA** 上快速建库并比对，或
- 在服务器上已用 `makeblastdb` 建好的 **核苷酸 BLAST 数据库前缀**上比对。

**不**替代 `off_target_blast`（**8002**）mock 服务；真实比对走 **`blast_service`（8019）** 与 Agent 工具 `run_blastn_similarity_search`。

### 10M.2 微服务目录

```text
microservices/blast_service/
```

文件：

- `environment.yml`（`python=3.10` + bioconda **`blast`** + FastAPI 栈）
- `main.py`（`GET /health`、`POST /blastn`）
- `start.sh`（默认端口 **8019**）

### 10M.3 当前微服务能力

接口（**默认端口 `8019`**）：

- `GET /health`  
  - 返回 `blastn` / `makeblastdb` 是否在 `PATH` 中、`rna_agent_system` 根路径解析提示等。

- `POST /blastn`

输入（JSON）：

- `query_filepath`（必填）：查询序列文件路径；可为 **绝对路径**，或与仓库一致的 **`rna_agent_system/` 相对路径**（服务内按 `rna_agent_system` 根目录解析）。
- **二选一**：
  - `subject_fasta_path`：subject 多序列 FASTA；服务在临时目录中执行 `makeblastdb` 后调用 `blastn`。
  - `subject_db`：已有核苷酸 BLAST 数据库的**前缀路径**（与 `blastn -db` 一致，不含扩展名）。
- 常用可选字段：`task`（默认 `blastn-short`）、`evalue`、`word_size`、`max_target_seqs`、`perc_identity`、`strand`（`both` / `plus` / `minus`）、`outfmt`、`blastn_timeout_sec`。

输出（摘要）：

- `hit_count`、`hits_preview`、`tabular_output`（过长时截断并 `tabular_output_truncated=true`）、`blastn_command`、`makeblastdb_command`（仅 FASTA subject 时有值）、`subject_mode`、`resolved_query_path`、`resolved_subject` 等。

服务会将查询文件内容规范为 **DNA（U→T）** 后再写入临时 query FASTA，避免混用 RNA 字母导致 `blastn` 报错。

### 10M.4 当前 Agent 工具能力

工具函数：

- `run_blastn_similarity_search(filepath, subject_fasta_path=None, subject_db=None, service_url="http://127.0.0.1:8019/blastn", task="blastn-short", evalue=10.0, word_size=None, max_target_seqs=50, perc_identity=None, strand="both")`

输入：

- `filepath`：query 序列文件（通常由规则节点先写入 `workspace/`）。
- `subject_fasta_path` **或** `subject_db`：**必须**提供其一；路径可为绝对路径或相对 `rna_agent_system/` 的相对路径（工具层会解析为服务器绝对路径再 POST）。

输出（字典，节选）：

- `hit_count`、`hits_preview`、`tabular_tsv_filepath`（完整制表符结果写入 `workspace/blastn_out_*.tsv`）、`blastn_command`、`subject_mode` 等。

### 10M.5 当前工作流集成方式

- `router_node`：在既有 mRNA 关键词之外，增加对 **`blast` / `blastn` / `megablast` / `dc-megablast` / `相似性搜索`** 的识别，与其它 mRNA 关键词一致路由到 `mrna_specialist`。
- `mrna_specialist_node`：命中 BLAST 语义时单独分支调用 `run_blastn_similarity_search`；参数由 `_build_blast_tool_args` 从自然语言解析（见 **§5.3**）。
- `tool_execution_node`：回填 `blast_hit_count`、`blast_tabular_tsv_filepath`、`blast_subject_mode`；`final_report` 中追加对应字段。
- `critic_node`：对纯 BLAST 请求无单独 reject 规则（不因 MFE 等结构规则误伤）。

### 10M.6 实际运行注意事项

- **Linux 服务器**侧安装与验证；macOS 可用于改代码与推仓库。
- 依赖 Conda 环境中可执行的 **`blastn`** 与 **`makeblastdb`**（`environment.yml` 已包含 bioconda `blast`）。
- **大库 / 高 `max_target_seqs`** 时单次请求可能较慢，可调大 `blastn_timeout_sec` 或缩小库与参数。
- Subject FASTA 的序列 ID 若含特殊字符，`makeblastdb` 可能失败；优先使用规范 FASTA header。

### 10M.7 当前验证状态

- 推荐在 **Linux** 上完成：`conda env create` → `conda activate blast_service_env` → `bash start.sh`，再对 `GET /health` 与 `POST /blastn` 做最小 `curl` 闭环（见 **§13.1** 示例）。
- Agent 规则层已具备自然语言触发 BLAST 分支的能力；**前提是 `8019` 微服务已启动**。

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
├── start.sh
└── （按需）install_*.sh 或其它本地编译/补丁脚本 — 例如 `codonw_slim_service/install_codonw_slim.sh`
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
- `ODesign`
- `IRESfinder`
- `LinearDesign`
- `LinearFold`
- `Evitar`
- `ViennaRNA`
- `sgrna_design`
- `codonw-slim`

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
- `external_repos/ODesign/ckpt/odesign_base_na_rigid.pt`
- `external_repos/ODesign/ckpt/oinvfold_rna.ckpt`
- `external_repos/ODesign/data/components.v20240608.cif`
- `external_repos/ODesign/data/components.v20240608.cif.rdkit_mol.pkl`

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

例如测试 ViennaRNA（`microservices/viennarna_fold`，端口 **8003**）：

1. 启动服务（示例）：

```bash
cd rna_agent_system/microservices/viennarna_fold
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate viennarna_fold_env
python -m uvicorn main:app --host 0.0.0.0 --port 8003
```

2. `curl /health`

```bash
curl -sS http://127.0.0.1:8003/health | python3 -m json.tool
```

3. `POST /fold`

```bash
curl -sS -X POST http://127.0.0.1:8003/fold \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"GGGGAAAACCCC"}' | python3 -m json.tool
```

4. `POST /sirna-duplex`

```bash
curl -sS -X POST http://127.0.0.1:8003/sirna-duplex \
  -H 'Content-Type: application/json' \
  -d '{"sense":"GGCAUGCAUGC","antisense":"GCAUGCAUGCC"}' | python3 -m json.tool
```

5. `POST /aso-accessibility`（序列需足够长，例如 `AUGC` 重复 50 次）

```bash
SEQ="$(python3 -c "print('AUGC'*50)")"
curl -sS -X POST http://127.0.0.1:8003/aso-accessibility \
  -H 'Content-Type: application/json' \
  -d "{\"sequence\":\">target\\n${SEQ}\",\"region_start\":10,\"region_end\":35,\"aso_oligo_length\":18,\"winsize\":70,\"span\":70,\"unpaired_ulength\":25,\"temp_c\":37.0}" | python3 -m json.tool
```

6. `POST /inverse-fold`

```bash
curl -sS -X POST http://127.0.0.1:8003/inverse-fold \
  -H 'Content-Type: application/json' \
  -d '{"structure":"((((....))))","repeats":3,"temp_c":37.0,"function_mode":"m"}' | python3 -m json.tool
```

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

例如测试 IRESfinder：

1. 启动 `iresfinder_service`
2. `curl /health`
3. `curl /predict`

推荐优先测试 payload：

```json
{
  "fasta_content": ">query\nAUGGCUACGUAGCUAGCUAGCUAGCUGA",
  "mode": 0,
  "decision_threshold": 0.5
}
```

例如测试 LinearDesign：

1. 在 `rna_agent_system/external_repos/LinearDesign` 执行 `make`，确认存在 `bin/LinearDesign_2D`
2. 启动 `lineardesign_service`
3. `curl /health`
4. `curl /generate/cds`

推荐优先测试 payload：

```json
{
  "protein_sequence": "MNDTEAI",
  "lambda_value": 0.0,
  "verbose": false
}
```

例如测试 LinearFold：

1. 在 `rna_agent_system/external_repos/LinearFold` 执行 `make`，确认存在 `bin/linearfold_c` 与 `bin/linearfold_v`
2. 启动 `linearfold_service`
3. `curl /health`
4. `curl /fold`

推荐优先测试 payload：

```json
{
  "sequence": "GGGCUCGUAGAUCAGCGGUAGAUCGCUUCCUUCGCAAGGAAGCCCUGGGUUCAAAUCCCAGCGAGUCCACCA",
  "beam_size": 20,
  "use_vienna": false,
  "dangles": 2
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
   - 可选先设置：`export CRISOT_DEFAULT_REF_GENOME=/absolute/path/to/genome.fa`
2. `curl /health`
   - 关注返回中的：`status`、`missing_requirements`、`warnings`
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

例如测试 sgrna_design：

1. 启动 `sgrna_design_service`
2. `curl /health`
3. `curl /design`

推荐优先测试 payload：

```json
{
  "seed_sequence": "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
  "n_samples": 4,
  "mutation_number": 20,
  "temperature": 1.0,
  "max_overlap": 21,
  "device": "cpu"
}
```

例如测试 codonw-slim：

1. 确保子模块已检出：`git submodule update --init --recursive`（`external_repos/codonw-slim`）
2. `cd rna_agent_system/microservices/codonw_slim_service`
3. `conda env create -f environment.yml`（若已存在则 `conda env update -f environment.yml --prune`）
4. `conda activate codonw_slim_service_env`
5. **`bash install_codonw_slim.sh`**
6. `bash start.sh`（或 `python -m uvicorn main:app --host 0.0.0.0 --port 8018`）
7. `curl /health`
8. `curl /analyze/cds`

推荐优先测试 payload（与上游 README 示例一致）：

```bash
curl -sS -X POST http://127.0.0.1:8018/analyze/cds \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"ATGAATATGCTCATTGTCGGTAGAGTTGTTGCTAGTGTTGGGGGAAGCGGACTTCAAACG"}' | python3 -m json.tool
```

例如测试 **BLAST+（`blast_service`，8019）**：

1. 启动 `blast_service`（见 **§10M.6**）
2. `curl /health`
3. `POST /blastn`（见下方 `curl`）

推荐最小 payload（subject 为 FASTA；路径请改为服务器上真实存在的文件）：

```bash
curl -sS -X POST http://127.0.0.1:8019/blastn \
  -H 'Content-Type: application/json' \
  -d '{
    "query_filepath": "rna_agent_system/workspace/blast_test_query.fa",
    "subject_fasta_path": "rna_agent_system/workspace/blast_test_subject.fa",
    "task": "blastn-short",
    "evalue": 10,
    "max_target_seqs": 10
  }' | python3 -m json.tool
```

若使用已有 BLAST 库，将 `subject_fasta_path` 换为 `subject_db`（**库前缀绝对路径或相对 `rna_agent_system/` 的路径**），并视情况调整 `task`（例如 `megablast`）。

### 13.2 智能体集成测试

在**相关微服务已启动**（至少对应当次请求的工具，例如 ViennaRNA 需 `8003`）后，再启动：

- `frontend/app.py`

推荐从**仓库根目录**（含 `rna_agent_system/` 的那一层）启动：

```bash
streamlit run rna_agent_system/frontend/app.py --server.fileWatcherType none
```

远程 SSH 访问时如需绑定到所有网卡并指定端口（示例 **8501**）：

```bash
streamlit run rna_agent_system/frontend/app.py --server.fileWatcherType none --server.address 0.0.0.0 --server.port 8501
```

浏览器打开：`http://<主机>:8501`（本机则为 `http://127.0.0.1:8501`）。

说明：

- 当前 `frontend/app.py` 已在代码中自动补了父目录到 `sys.path`
- 因此正常情况下不再需要手动设置 `PYTHONPATH`
- 某些 Linux 服务器上 `inotify watch limit` 偏小，因此建议保留 `--server.fileWatcherType none`
- Agent 工具默认请求 `http://127.0.0.1:<端口>`；若 Streamlit 与微服务不在同一台机器，需自行做端口转发或改工具 `service_url` / 环境，此处不展开

#### 13.2A Streamlit 自然语言案例（可复制到聊天框）

以下案例假设 **`viennarna_fold` 已在 `127.0.0.1:8003` 运行**；duplex / ASO / inverse 亦依赖该服务。涉及 **codonw 指标 + fold** 的句子需同时启动 **`codonw_slim_service`（8018）** 与 **8003**。涉及 **BLAST** 时需启动 **`blast_service`（8019）**，并在句中给出 **`subject_fasta=`** 或 **`subject_db=`**。

| 目的 | 建议输入示例（整句粘贴） |
|------|---------------------------|
| 仅 codonw-slim（CDS 密码子指标） | `codonw-slim 分析 CDS 密码子 CAI，序列：` 后接 in-frame CDS 或 `.fa` 路径；可加 `genetic_code=0` |
| 默认 mRNA 二级结构（ViennaRNA fold） | `请预测这条 RNA 的二级结构 fold：AUGCUAACGUAGCUAUGCUAUGCUAACGUAGCUAUGCUA` |
| siRNA 双链结合能（cofold） | `请用 ViennaRNA 计算 siRNA duplex 结合能 rnacofold，sense=GGCAUGCAUGCAUGCAUGC antisense=GCAUGCAUGCAUGCAUGCC` |
| ASO 靶区可及性（RNAplfold） | `ASO accessibility plfold 可及性，region=10-50，靶标 mRNA：` 后接一段 **至少约 50 nt** 的 `AUGC...` 重复序列（或与 RNASTOP 相同规则的长 RNA 文本 / `workspace/*.fa` 路径） |
| 二级结构逆折叠（RNAinverse） | `inverse fold 逆折叠 rnainverse，structure=((((....))))，repeats=5` |
| siRNA 效率 + 脱靶（原默认分支） | `sirna AUGCUAACGUAGCUAUGCUA`（需 `8001`/`8002` 等 mock 服务若仍接入） |
| mRNA 结构 + LinearFold | `fold linearfold 二级结构 AUGGCUACGUAGCUAGCUAGCUAGCUGA beam_size=20` |
| BLAST blastn（subject FASTA） | `blastn 比对 subject_fasta=rna_agent_system/workspace/blast_test_subject.fa 序列 ATGCATGCATGCATGC`（路径与序列按服务器实际情况修改） |

然后测试（回归清单，含上文未列能力）：

- siRNA 请求
- mRNA 结构预测请求
- mRNA 结构预测请求（默认 ViennaRNA）
- mRNA 结构预测请求（显式 `linearfold`，并可附 `beam_size=...` / `dangles=...`）
- codonw-slim 独立 CDS 指标请求（**8018**）
- BLAST blastn 相似性搜索（**8019**，且句中含 `subject_fasta=` 或 `subject_db=`）
- mRNA 结构预测 + codonw 前置指标（**8018** + **8003**）
- GEMORNA 设计请求
- GEMORNA 设计 + RNAfold 联合请求
- LinearDesign 设计请求（自然语言中显式包含 `lineardesign` / `linear design` 等关键词，例如「请用 lineardesign 设计 mRNA CDS，蛋白序列 MNDTEAI」）
- RNA 三级结构预测请求
- Evitar existing-virus 设计请求（`input + strains`）
- Evitar future-virus predesign 请求（`mode=predesign`）
- GEMORNA 设计 + RhoFold 联合请求
- LinearDesign 设计 + 结构预测联合请求（在同一句用户输入中同时包含设计语义与 `fold` / `rhofold` 等结构关键词时，由 `tool_execution_node` 串联）
- LinearDesign 设计 + Linearfold 联合请求（在同一句用户输入中同时包含设计语义与 `linearfold` 关键词时，后续折叠改走 `linearfold_service`）
- RhoDesign 结构到序列设计请求
- RNAsmol RNA-ligand 打分请求
- RNASTOP mRNA 稳定性预测请求
- GerNA-Bind RNA-ligand 打分请求
- CRISOT single-pair 打分请求
- CRISOT genome-wide specificity 请求
- CRISOT sgRNA 优化请求
- sgRNA handle 设计请求（`sgrna design` / `crgpt`）
- ODesign RNA backbone 请求
- ODesign protein-binding RNA 请求

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

### 14.2 密码子指标：`codonw-slim` 与 `mock_codon_optimization`

当前 mRNA 分支里：

- `predict_rna_secondary_structure` 已是真实 ViennaRNA
- `design_mrna_cds_with_gemorna` 已是真实 GEMORNA 接入
- `design_mrna_cds_with_lineardesign` 已是真实 LinearDesign 接入（显式关键词触发）
- **默认「结构预测型」链路**中，原 **`mock_codon_optimization` 占位已由 `analyze_cds_codon_metrics_with_codonw_slim`（真实 codonw-slim）替代**；详见 **§10L**
- `mock_codon_optimization` **仍保留在代码库**中供调试或未来编排复用，但**规则工作流当前不再默认调用**

后续仍可考虑：引入「真实密码子**优化**」（序列改写）类工具，与当前「密码子**统计/偏好**」能力区分产品边界。

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

### 14.16 `ODesign` 当前更适合作为“服务器侧重工具”而不是本地开发机工具

当前 `ODesign` 最容易踩坑的地方之一不是 Agent 规则，而是：

- 运行环境偏重
- 依赖 CUDA 12.1
- 推理需要额外 checkpoint 与 data 文件

因此当前更稳妥的使用原则是：

- 开发机只负责改代码和推 GitHub
- Linux 服务器负责安装环境和运行推理
- 优先先测上游 `scripts/inference.py`
- 再测 `odesign_service`
- 最后再测前端自然语言入口

### 14.17 `ODesign` 的自然语言入口仍是有限规则解析

当前已经支持：

- 显式 JSON
- RNA backbone
- protein-binding RNA

但这并不意味着：

- 任意 ODesign 复杂任务都能被自由自然语言稳定还原成 JSON

因此：

- 复杂任务仍建议显式写 JSON
- 当前自然语言入口更适合作为“常用模板调用”而不是完整的 ODesign 任务编排器

### 14.18 mRNA 规则 Critic 的 `mfe > -20.0` 与短序列折叠

当前 `critic_node` 在用户请求含结构相关关键词时，若 **`mfe > -20.0`** 则 **hard reject** 并重试，直到 **`retry_count < max_retries`** 不再成立才 **pass**。

这在热力学上容易与**短 RNA** 的典型 MFE 尺度冲突：很多合法、已用 ViennaRNA 或 LinearFold 正确折叠的序列，其 MFE 在 **-1 ~ -15 kcal/mol** 仍**大于** `-20`，因此会连续触发 reject，**重试并不会改变物理预测**，只是在耗尽重试次数后放行。

更稳妥的后续方向包括：

- 按序列长度或任务类型调整阈值（例如仅对 `len(seq) > N` 启用 `-20` 规则）
- 将“稳定性”判据改为与长度归一化的指标或独立业务阈值
- 对纯“二级结构查询”类请求跳过该条 mRNA 规则

---

## 15. 后续最推荐的发展路线

建议按下面顺序继续推进：

1. 先把工具链接全；默认 mRNA 结构预测链路中的 **mock 密码子占位** 已由 **`codonw-slim`** 替换，其余 mock 工具按优先级逐步替换
2. 保持规则模式，先把每个工具独立跑通
3. 先在 Agent 层把 `RhoFold` / `RhoDesign` / `RNAsmol` / `GerNA-Bind` / `CRISOT` / `ODesign` / `LinearDesign` / `LinearFold` / `Evitar` / **`codonw-slim`** 的一句话调用链路稳定下来
4. 等工具生态稳定后，再恢复可配置的 LLM 模式
5. 再逐步引入：
   - 更细的 specialist
   - 更强的 critic
   - 结果排序 / 候选集筛选
   - 多工具串联规划
6. 后续再考虑：
   - 用真实密码子**优化**（改写 CDS）工具补充或替换仍保留的 `mock_codon_optimization` 代码路径（与当前 **codonw-slim 统计指标**区分；LinearDesign 已可作为显式设计路径之一）
   - 为 `RhoFold` 增加可选的 MSA 模式
  - 优化 `RhoDesign` 的输入文件校验与错误提示
  - 优化 `RNAsmol` 的输入解析与批量评分模式
  - 为 `GerNA-Bind` 增加更细粒度的前端参数透传与批量推理模式
  - 为 `ODesign` 扩展更多自然语言模板到 JSON 的安全映射
  - 优化前端结果展示与文件下载体验

---

## 16. 一句话总结

当前这个项目的核心设计可以概括为：

**上层 Agent 只负责规则路由与工作流编排，下层所有复杂生信能力都通过 `Conda + FastAPI` 微服务隔离运行，长序列统一走 `workspace filepath` 传递，第三方源码通过 `external_repos/` 的 submodule 方式独立管理；其中 NCBI BLAST+（`blastn`）由 `blast_service`（8019）提供，与 8002 的 mock 脱靶服务并存。**

以后新增工具时，统一按下面的固定动作做：

1. 放到 `external_repos/`
2. 建 `microservices/<tool>_service/`（若需本地编译/补丁，可像 `codonw_slim_service` 一样增加 `install_*.sh`）
3. 在 `agent_core/tools.py` 封装 HTTP 工具
4. 在 `nodes.py` 接 specialist
5. 先测原始命令，再测微服务，再测 Agent
6. 如果仓库里有 submodule 和运行时输出，不要默认 `git add .`

