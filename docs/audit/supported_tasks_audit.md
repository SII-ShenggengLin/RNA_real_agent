# 当前真实支持任务审计（按代码为准）

> 审计标准（来自需求）：
>
> - 有可调用入口（API / CLI / agent workflow / service）
> - 有对应工具或流程实现
> - 依赖链基本闭合
> - 不是 mock / TODO / fake result
>
> 入口定义（本仓库实际存在）：
>
> - **UI/Workflow 入口**：`rna_agent_system/frontend/app.py` → `agent_core/graph.py:compiled_graph` → `agent_core/nodes.py`
> - **工具入口**：`rna_agent_system/agent_core/tools.py`（LangChain `@tool` 包装的 HTTP 微服务调用）
> - **微服务入口**：`rna_agent_system/microservices/*/main.py`（FastAPI）

---

## 1. 总览：本仓库“可执行”任务的真实边界

按 `agent_core/nodes.py` 的三条 specialist 分支（`sirna_specialist` / `mrna_specialist` / `crispr_specialist`）与 `tools.py` 可调用工具集合，当前任务主要覆盖：

- **RNA 二级结构相关**（ViennaRNA / LinearFold / RNAinverse / RNAplfold / duplex）
- **mRNA/CDS 设计**（GEMORNA / RNARL / LinearDesign）
- **RNA 三级结构预测**（RhoFold）
- **RNA 结构→序列设计**（RhoDesign）
- **RNA-ligand 打分**（RNAsmol / GerNA-Bind）
- **mRNA 稳定性/降解预测**（RNASTOP）
- **IRES 预测**（IRESfinder microservice）
- **BLAST 相似性搜索**（BLAST+ microservice）
- **CRISPR off-target 打分/特异性/优化**（CRISOT）
- **sgRNA handle 设计**（CRGPT / `sgrna_design_service`）
- **ODesign JSON 推理**（ODesign）

同时存在明确的 mock 能力（因此“不算真实支持”）：

- siRNA 效率预测（mock）
- siRNA 脱靶计数（mock）
- mRNA 密码子优化（mock）

---

## 2. 任务逐项审计（任务名 / 入口 / 依赖工具 / 输入 / 输出 / 状态 / 判断依据）

> 说明：以下“判断依据”只引用本仓库内的代码文件路径（不以 README 宣称为准）。

### 2.1 siRNA 相关

#### 任务：siRNA 效率预测（AttSiOff）

- **入口位置**：
  - Workflow：`agent_core/nodes.py` → `sirna_specialist_node` 默认会发出 `predict_sirna_efficiency`
  - 工具：`agent_core/tools.py:predict_sirna_efficiency`
  - 微服务：`microservices/sirna_attsioff/main.py` → `POST /predict`
- **依赖工具**：`predict_sirna_efficiency`（HTTP → 8001）
- **输入**：`filepath`（workspace 文件，内容为 RNA 序列文本/FASTA）
- **输出**：`efficiency_score`（0~1）
- **当前状态**：**不可用（mock）**
- **判断依据**：
  - 微服务 docstring 明确 `Mock ...` 且 `random()` 生成分数（`microservices/sirna_attsioff/main.py`）

#### 任务：siRNA 脱靶检查（off-target count）

- **入口位置**：
  - Workflow：`agent_core/nodes.py` → `sirna_specialist_node` 默认会发出 `check_off_target`
  - 工具：`agent_core/tools.py:check_off_target`
  - 微服务：`microservices/off_target_blast/main.py` → `POST /check`
- **依赖工具**：`check_off_target`（HTTP → 8002）
- **输入**：`filepath`
- **输出**：`off_target_genes`（0~2）
- **当前状态**：**不可用（mock）**
- **判断依据**：
  - 微服务 docstring 明确 `Mock ...` 且 `randint(0, 2)` 生成计数（`microservices/off_target_blast/main.py`）

#### 任务：siRNA sense/antisense duplex 结合能（ViennaRNA cofold）

- **入口位置**：
  - Workflow：`agent_core/nodes.py` → duplex 关键词触发 tool `compute_sirna_duplex_binding_vienna`
  - 工具：`agent_core/tools.py:compute_sirna_duplex_binding_vienna`
  - 微服务：`microservices/viennarna_fold/main.py`（端口 8003，文档中声明有 `/sirna-duplex`）
- **依赖工具**：`compute_sirna_duplex_binding_vienna`（HTTP → 8003）
- **输入**：
  - `filepath`：包含两条链（两条 FASTA 记录或两行序列）
- **输出**：
  - `mfe_kcal_per_mol`、`structure`、`sense`、`antisense` 等（dict）
- **当前状态**：**可用（依赖 ViennaRNA 服务可运行）**
- **判断依据**：
  - 工具函数从文件解析两条链并请求 `service_url=/sirna-duplex`（`agent_core/tools.py`）
  - Specialist/Tool executor 均有相应分支（`agent_core/nodes.py`）

#### 任务：siRNA/Cas13 设计（Evitar）

- **入口位置**：
  - Workflow：`agent_core/nodes.py` → 关键词触发 `design_sirna_with_evitar`
  - 工具：`agent_core/tools.py:design_sirna_with_evitar`
  - 微服务：`microservices/evitar_service/main.py`（端口 8016，文档声明 `POST /design`）
- **依赖工具**：`design_sirna_with_evitar`（HTTP → 8016）
- **输入**：`filepath`（FASTA），以及 `mode/predict/strains_path/off_target/ncores`
- **输出**：包含 `output_filepath`、`top_results`、`result_count` 等（dict）
- **当前状态**：**部分可用**
- **判断依据**：
  - 工具/节点链路完整（`tools.py` + `nodes.py` + `docs/RNA_AGENT_SYSTEM_GUIDE.md`）
  - 但文档明确 Evitar **仅限 Linux**（macOS 不能执行上游 binary），因此在本仓库所在环境（darwin）不能闭环运行（`rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md`）。

---

### 2.2 RNA 二级结构与相关分析

#### 任务：RNA 二级结构预测（ViennaRNA RNAfold）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 或兜底路径会调用 `predict_rna_secondary_structure`
  - 工具：`agent_core/tools.py:predict_rna_secondary_structure`
  - 微服务：`microservices/viennarna_fold/main.py`（端口 8003，文档声明 `POST /fold`）
- **依赖工具**：`predict_rna_secondary_structure`（HTTP → 8003）
- **输入**：`filepath`（RNA 序列文件）
- **输出**：字符串（包含 `structure` 与 `mfe`）
- **当前状态**：**可用（依赖 ViennaRNA 服务可运行）**
- **判断依据**：工具调用链完整（`graph.py` / `nodes.py` / `tools.py`），且非 mock。

#### 任务：RNA 二级结构预测（LinearFold）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 在 `linearfold` 关键词下改用 `predict_rna_secondary_structure_with_linearfold`
  - 工具：`agent_core/tools.py:predict_rna_secondary_structure_with_linearfold`
  - 微服务：`microservices/linearfold_service/main.py`（端口 8015，文档声明 `POST /fold`）
- **依赖工具**：`predict_rna_secondary_structure_with_linearfold`（HTTP → 8015）
- **输入**：`filepath` + `beam_size/use_vienna/dangles`
- **输出**：dict（`structure`、`mfe` 等）
- **当前状态**：**可用（依赖 LinearFold 服务可运行）**
- **判断依据**：工具/节点链路完整，且非 mock。

#### 任务：ASO 靶区可及性（ViennaRNA RNAplfold）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 在 `aso/plfold/accessibility` 语义下调用 `compute_aso_target_accessibility_vienna`
  - 工具：`agent_core/tools.py:compute_aso_target_accessibility_vienna`
  - 微服务：`microservices/viennarna_fold/main.py`（文档声明 `POST /aso-accessibility`）
- **依赖工具**：`compute_aso_target_accessibility_vienna`（HTTP → 8003）
- **输入**：`filepath` + `region_start/region_end` + RNAplfold 参数
- **输出**：dict（区域平均 unpaired 概率、joint 概率等）
- **当前状态**：**可用（依赖 ViennaRNA 服务可运行）**

#### 任务：二级结构逆折叠（ViennaRNA RNAinverse）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 在 `inverse fold/rnainverse` 语义下调用 `inverse_fold_rna_secondary_structure_vienna`
  - 工具：`agent_core/tools.py:inverse_fold_rna_secondary_structure_vienna`
  - 微服务：`microservices/viennarna_fold/main.py`（文档声明 `POST /inverse-fold`）
- **依赖工具**：`inverse_fold_rna_secondary_structure_vienna`（HTTP → 8003）
- **输入**：`filepath`（第一行 dot-bracket；可选第二行起始序列）+ `repeats`
- **输出**：dict（`best_sequence` + `best_sequence_filepath` 等）
- **当前状态**：**可用（依赖 ViennaRNA 服务可运行）**

---

### 2.3 mRNA/CDS 相关

#### 任务：蛋白序列 → mRNA CDS 设计（LinearDesign / RNARL / GEMORNA）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 在 `design/protein/cds` 等语义下选择：
    - `design_mrna_cds_with_lineardesign`
    - `design_mrna_cds_with_rnarl`
    - `design_mrna_cds_with_gemorna`
  - 工具：`agent_core/tools.py` 对应三个工具函数
  - 微服务：`microservices/lineardesign_service` / `rnarl_service` / `gemorna_service`
- **依赖工具**：上述三者之一（HTTP → 8014/8008/8004）
- **输入**：`filepath`（蛋白序列文件；由节点侧 `save_sequence(..., prefix="protein")` 生成）
- **输出**：各服务返回的设计结果（dict，含 output 文件路径等）
- **当前状态**：**部分可用**
- **判断依据**：
  - 代码链路完整（`nodes.py` 构造 tool_calls；`tools.py` 调用微服务）
  - 但文档注明 GEMORNA/RNARL/LinearDesign 多数依赖 Linux/GPU/预训练权重与本地路径，macOS 环境无法闭环（`rna_agent_system/docs/RNA_AGENT_SYSTEM_GUIDE.md`）。

#### 任务：CDS 密码子指标分析（codonw-slim）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 默认会调用 `analyze_cds_codon_metrics_with_codonw_slim`
  - 工具：`agent_core/tools.py:analyze_cds_codon_metrics_with_codonw_slim`
  - 微服务：`microservices/codonw_slim_service/main.py`（端口 8018，文档声明 `POST /analyze/cds`）
- **依赖工具**：`analyze_cds_codon_metrics_with_codonw_slim`
- **输入**：`filepath`（CDS 序列文件）
- **输出**：dict（`cai_score/enc/fop/cbi` + `metrics_json_filepath` 等）
- **当前状态**：**可用（依赖微服务可运行）**

#### 任务：mRNA 密码子优化（mock）

- **入口位置**：
  - 工具：`agent_core/tools.py:mock_codon_optimization`
  - Workflow：`MRNA_TOOLS` 注册且 `tool_execution_node` 会解析其输出
- **输入**：`filepath`
- **输出**：固定 `cai_score=0.88`，并生成伪“optimized sequence”
- **当前状态**：**不可用（mock）**
- **判断依据**：工具 docstring 明确 `Mock codon optimization`，并返回固定分数与简单替换结果。

---

### 2.4 结构/设计/打分（3D 与 ligand）

#### 任务：RNA 三级结构预测（RhoFold）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 在 `rhofold/3d/tertiary` 语义下追加 `predict_rna_tertiary_structure_with_rhofold`
  - 工具：`agent_core/tools.py:predict_rna_tertiary_structure_with_rhofold`
  - 微服务：`microservices/rhofold_service/main.py`（端口 8005）
- **依赖工具**：`predict_rna_tertiary_structure_with_rhofold`
- **输入**：`filepath`（RNA 序列）
- **输出**：dict（包含输出结构文件路径、pLDDT 等）
- **当前状态**：**部分可用（依赖 Linux/GPU/权重）**
- **判断依据**：链路完整但文档标注 Linux GPU 依赖。

#### 任务：RNA 结构（PDB）→ 序列设计（RhoDesign）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 在结构设计语义下调用 `design_rna_sequence_with_rhodesign`
  - 工具：`agent_core/tools.py:design_rna_sequence_with_rhodesign`
  - 微服务：`microservices/rhodesign_service/main.py`（端口 8006）
- **依赖工具**：`design_rna_sequence_with_rhodesign`
- **输入**：`pdb_filepath`（以及可选 secondary structure file）
- **输出**：dict（设计序列文件路径、recovery rate 等）
- **当前状态**：**部分可用（依赖 Linux/GPU/权重）**

#### 任务：RNA-ligand 打分（RNAsmol / GerNA-Bind）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 根据关键词选择：
    - `score_rna_ligand_binding_with_rnasmol`
    - `score_rna_ligand_binding_with_gernabind`
  - 工具：`agent_core/tools.py` 对应工具函数
  - 微服务：`microservices/rnasmol_service` / `gernabind_service`
- **依赖工具**：上述两者之一
- **输入**：`filepath`（RNA）+ `smiles`；RNAsmol 额外支持 `dataset`、`perturbation_type`、`device`、`checkpoint_path`
- **输出**：dict（概率/标签/模型信息等）
- **当前状态**：**部分可用（依赖 Linux/GPU/权重）**

---

### 2.5 注释/搜索/预测（BLAST/IRES/RNASTOP）

#### 任务：BLAST 相似性搜索（BLAST+）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 识别 `blast/blastn` 时调用 `run_blastn_similarity_search`
  - 工具：`agent_core/tools.py:run_blastn_similarity_search`
  - 微服务：`microservices/blast_service/main.py`（端口 8019）
- **依赖工具**：`run_blastn_similarity_search`
- **输入**：`filepath`（query）+ `subject_fasta_path` 或 `subject_db`（二选一）
- **输出**：dict（`hit_count`、`tabular_tsv_filepath` 等）
- **当前状态**：**部分可用**
- **判断依据**：链路完整，但依赖服务器侧 BLAST+ 可用与本地 subject 数据可用；macOS 环境未必闭环。

#### 任务：IRES 预测（IRESfinder microservice）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 识别 IRES 语义调用 `predict_putative_ires_with_iresfinder`
  - 工具：`agent_core/tools.py:predict_putative_ires_with_iresfinder`
  - 微服务：`microservices/iresfinder_service/main.py`（端口 8013）
- **依赖工具**：`predict_putative_ires_with_iresfinder`
- **输入**：`filepath`
- **输出**：dict（tsv 路径、score、正例数等）
- **当前状态**：**部分可用**（依赖模型/数据文件存在，文档有额外前置条件）

#### 任务：mRNA 稳定性/降解预测（RNASTOP）

- **入口位置**：
  - Workflow：`mrna_specialist_node` 识别 `stability/degradation/rnastop` 语义调用 `predict_mrna_stability_with_rnastop`
  - 工具：`agent_core/tools.py:predict_mrna_stability_with_rnastop`
  - 微服务：`microservices/rnastop_service/main.py`（端口 8009）
- **依赖工具**：`predict_mrna_stability_with_rnastop`
- **输入**：`filepath`
- **输出**：dict（预测文件路径、均值指标等）
- **当前状态**：**部分可用（依赖 Linux/GPU/权重）**

---

### 2.6 CRISPR/sgRNA 相关

#### 任务：CRISPR off-target 打分（CRISOT score）

- **入口位置**：
  - Workflow：`crispr_specialist_node` / `tool_execution_node` 会根据用户输入选择 `score_crispr_off_target_with_crisot`
  - 工具：`agent_core/tools.py:score_crispr_off_target_with_crisot`
  - 微服务：`microservices/crisot_service/main.py`（端口 8011）
- **依赖工具**：`score_crispr_off_target_with_crisot`
- **输入**：`filepath`（sgRNA）+ `target_sequence`（23nt）
- **输出**：dict（`crisot_score` 等）
- **当前状态**：**可用（依赖微服务可运行）**

#### 任务：CRISPR specificity（CSV）与 genome-wide off-spec 搜索 / optimize

- **入口位置**：同上，工具分别为：
  - `calculate_crispr_specificity_with_crisot`
  - `search_crispr_off_targets_with_crisot`
  - `optimize_sgrna_with_crisot`
- **输入/输出**：基于 `tools.py` 的 args_schema（csv 路径、genome_path、mismatches 等）
- **当前状态**：**部分可用**
- **判断依据**：链路完整，但 `off-spec/optimize` 明确依赖参考基因组与 Cas-OFFinder 等外部资源（文档已有说明）。

#### 任务：sgRNA handle 设计（CRGPT / sgrna_design_service）

- **入口位置**：
  - Workflow：`crispr_specialist_node` 识别 handle/design 语义后调用 `design_sgrna_handle_with_crgpt`
  - 工具：`agent_core/tools.py:design_sgrna_handle_with_crgpt`
  - 微服务：`microservices/sgrna_design_service/main.py`（端口 8017）
- **输入**：`filepath`（handle seed 序列）
- **输出**：dict（best sequence、候选数量、输出文件路径等）
- **当前状态**：**部分可用（依赖模型/torch/GPU）**

---

### 2.7 ODesign

#### 任务：ODesign JSON 推理（from-json）

- **入口位置**：
  - Workflow：`tool_execution_node` 在 `_needs_odesign_mode` 条件下调用 `run_odesign_inference`
  - 工具：`agent_core/tools.py:run_odesign_inference`
  - 微服务：`microservices/odesign_service/main.py`（端口 8012）
- **输入**：`input_json_filepath`
- **输出**：dict（输出目录、预测文件列表、日志文件等）
- **当前状态**：**部分可用（依赖 Linux/GPU/权重/数据文件）**

---

## 3. 本阶段变更（仅文档）

- **新增文件**：
  - `docs/audit/supported_tasks_audit.md`
- **原因**：把“README 宣称”与“代码真实能力”解耦，形成后续任务目录/工具链设计的基准面。

---

## 4. 验证方式（不改代码即可执行）

- **验证入口闭环（代码层）**：
  - `frontend/app.py` 是否调用 `compiled_graph`（存在）
  - `graph.py` 是否把 `router/specialist/tool_execution/critic` 串起来（存在）
  - `nodes.py` 是否把工具注册到 `TOOLS_BY_NAME` 并实际 `.invoke()`（存在）
- **验证 mock 排除**：
  - 搜索 `Mock` / `random()` / `randint()` / `model="mock_..."`（能定位 8001/8002 与 `mock_codon_optimization`）

