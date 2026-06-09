> **Last updated**: 2026-06-01

## 一、Nature子刊定位分析

| 期刊 | 偏好 | 匹配度 |
|------|------|--------|
| **Nature Methods** | 新方法、工具、算法创新 | ⭐⭐⭐⭐⭐ BMC方法 + 评估体系 |
| **Nature Machine Intelligence** | AI方法在科学中的应用 | ⭐⭐⭐⭐⭐ 强化学习/多agent + RNA |
| Nature Biomedical Engineering | 生物医学工程、转化应用 | ⭐⭐⭐⭐ mRNA疫苗/疗法 |
| **Nature Communications** | 广泛的高质量研究 | ⭐⭐⭐⭐⭐ 保底选择 |
| Nature Biotechnology | 生物技术方法 | ⭐⭐⭐ 如果加实验验证会更匹配 |

**最可能的 target**: Nature Methods 或 Nature Machine Intelligence

---

## 二、Introduction 论证链设计

核心逻辑：让审稿人接受"2/11用BMC是合理的，且这2个workflow覆盖了两种本质不同的多模块耦合模式"。Nature子刊的Introduction需要回答三个问题：

1. **Why RNA?** — 为什么RNA分子设计值得专门做一个agent平台？
2. **Why multi-module coordination?** — 为什么多模块RNA设计（全长mRNA、RNA aptamer等）是独特的、未被充分解决的科学问题？
3. **Why BMC?** — 为什么需要受约束的多模块协商，而不是现有的单模块优化或自由形式LLM规划？

### 建议的 Introduction 结构（约1500-2000词）

**Paragraph 1: RNA疗法的大背景（高视野）**

> The past decade has witnessed an unprecedented expansion of RNA-based therapeutics, from mRNA vaccines (e.g., COVID-19 vaccines) to small interfering RNAs (siRNAs), antisense oligonucleotides (ASOs), and CRISPR guide RNAs. The design of functional RNA molecules, however, remains a formidable multi-objective optimization problem that balances translation efficiency, structural stability, immunogenicity, and safety — objectives that often conflict and span multiple molecular scales.

**目的**：建立RNA设计的重要性和复杂性。

**Paragraph 2: 现有工具的碎片化困境**

> The RNA bioinformatics landscape has produced a rich ecosystem of specialized tools: ViennaRNA for secondary structure prediction, LinearDesign for codon optimization, CRISOT for off-target assessment, RhoFold for tertiary structure prediction, and dozens more. Yet these tools exist in isolation — incompatible environments, disparate interfaces, and conflicting dependencies prevent their seamless composition. Consequently, RNA design remains a labor-intensive, expert-driven process in which researchers manually chain tools through ad hoc scripts.

**目的**：痛点不是"没有工具"，而是"工具无法协同"。

**Paragraph 3: LLM Agents的机会与现有bio-agent的局限**

> Large language model (LLM) agents have emerged as a promising paradigm for automating scientific workflows by reasoning over tool use. Recent systems such as BioMedAgent, Open-Rosalind, and Robin have demonstrated autonomous tool orchestration in biomedicine. However, these systems adopt a one-size-fits-all philosophy: they prioritize broad domain coverage and flexible planning over deep, domain-specific optimization. In RNA design, this flexibility is a liability — the thermodynamic and codon-usage constraints governing RNA function are too precise to be delegated to open-ended reasoning. Moreover, existing agents lack epistemic accountability: their decision traces are incomplete, their factual claims are ungrounded in tool outputs, and their failure modes are opaque.

**目的**：
- 承认现有工作的价值
- 指出两个根本缺陷：缺乏领域深度 + 缺乏可审计性
- 为后文的"可审计平台"做铺垫

**Paragraph 4: 多模块RNA设计的独特挑战（核心段落，最重要）**

> A critical but under-appreciated class of RNA design tasks involves multiple functional modules that are optimized independently yet must operate as an integrated whole. We focus on two biologically distinct instantiations of this problem. **First**, full-length mRNA engineering: unlike single-domain designs (e.g., CDS-only optimization with LinearDesign), full-length mRNAs comprise three physically concatenated modules — the 5' untranslated region (UTR), the coding sequence (CDS), and the 3' UTR — that are optimized independently by existing tools. This independence is biologically untenable: the secondary structure at the 5'-CDS junction influences translation initiation efficiency; the GC-content discontinuity between CDS and 3' UTR can create thermodynamically unstable interfaces; and the overall stability of the concatenated molecule is not the sum of its parts. **Second**, RNA aptamer design: here the modules are not physically contiguous sequences but rather a *target protein binding hotspot* and a *generated aptamer ligand*. The two modules are coupled through a 3D complex whose quality depends on both the hotspot's structural complementarity and the aptamer's independent foldability — objectives that frequently conflict (e.g., high-affinity sequences may be structurally unstable). Current practice addresses both problems either by (i) optimizing one module and fixing the other, or (ii) optimizing each module separately and combining post hoc — both approaches ignore inter-module biophysical interactions. What is needed is a module-aware co-optimization framework that preserves the specialized toolchains of each domain while explicitly negotiating inter-module constraints.

**目的**：
- 建立多模块RNA设计是一个被忽视的通用问题，而不仅仅是全长mRNA的问题
- 通过两个具体场景（物理拼接 + 功能耦合）展示问题的生物学多样性
- 提出需求：模块感知的协同优化框架

**Paragraph 5: 本文贡献（三段式）**

> Here we present **RosalindAgent**, an agent system for automated RNA molecular design that addresses both the platform-level integration challenge and the multi-module co-optimization problem. Our work makes three contributions. First, we introduce a comprehensive RNA agent platform spanning eleven domain-specific workflows and twenty-one bioinformatics microservices, organized around a six-layer architecture (Layer 0–5) with tool-first execution, interface-locked contracts, and complete execution traces. Second, we propose **Bounded Multi-Module Coordination (BMC)**, a constrained iterative framework for biomolecular design in which independently optimized functional modules are assembled, evaluated for inter-module conflicts, and refined through structured feedback — all within hard bounds on iteration rounds and step counts. We instantiate BMC in two biologically distinct scenarios: **Type I (Physical Assembly)** for full-length mRNA (5'UTR + CDS + 3'UTR junction optimization, and **Type II (Functional Coupling)** for RNA aptamer design (target hotspot recognition → ligand generation → complex validation). Third, we introduce **RNA-BioBench**, a process-aware benchmark suite that measures not only design quality but also tool correctness, trace completeness, evidence grounding, and failure rates across the entire platform. On held-out test sets, BMC improves full-length mRNA stability by **X%** and aptamer binding affinity by **Z%** compared to serial baselines, while RNA-BioBench reveals that process-level auditing is a stronger predictor of reliable agent behavior than task accuracy alone.

**目的**：
- 三个贡献清晰分离
- 平台（广）+ BMC（深）+ 评估（方法论）
- 用一句话预告核心实验结果

**Paragraph 6: 论文路线图**

> The remainder of this paper is organized as follows...

---

## 三、Method 结构设计

Nature Methods / Nat. Mach. Intell. 的 Method 通常要求方法可复现、参数明确、基线清晰。

### Section 2.1: System Architecture Overview（1页）

RosalindAgent 的六层架构（Layer 0–5）：

| Layer | Component | Responsibility |
|-------|-----------|---------------|
| L0 | Tool Wrappers + Microservices | 21 microservices exposing 52+ specialized tool variants, exposed via FastAPI or Python API |
| L1 | Capability Registry | Typed tool composition, declarative writebacks |
| L2 | Domain Workflows | 11 BaseDomainWorkflow implementations |
| L3 | Planner + DeterministicRouter + Critic | LLM-based planning with deterministic keyword fallback (≥60 % common requests routed without LLM) |
| L4 | Session Memory + Workspace | Multi-turn context, file-based I/O |
| L5 | AgentRunner | Unified CLI/FastAPI façade |

11个Domain Workflows覆盖的RNA设计领域：
1. `mrna_cds_design` — CDS优化（LinearDesign / RNARL / GEMORNA）
2. `full_length_mrna_design` — 全长mRNA设计（5'UTR + CDS + 3'UTR，BMC Type I: Physical Assembly）
3. `mrna_sequence_scoring` — mRNA序列综合评分
4. `sirna_design` — siRNA设计（Evitar + BLAST + CRISOT）
5. `sgrna_design` — sgRNA handle设计（CRGPT + CRISOT）
6. `rna_secondary_structure_design` — 二级结构逆折叠（ViennaRNA）
7. `rna_tertiary_structure_design` — 三级结构设计（RhoDesign / RiboDiffusion）
8. `rna_aptamer_design` — RNA aptamer设计（ODesign + Protenix + EGARPS，BMC Type II: Functional Coupling）
9. `rna_small_molecule_interaction` — RNA-小分子相互作用（GerNA-Bind / RNAsmol）
10. `aso_target_screening` — ASO靶点筛选（RNAplfold + RNAup / RNAcofold）
11. `ires_prediction` — IRES元件预测（IRESfinder）

**关键图**：系统架构图（类似Open-Rosalind的Figure 3，但要突出21个microservices / 52+ tool variants的覆盖范围和11个workflow的层级）

### Section 2.2: Tool-First Execution and Interface Locks（0.5页）

强调 Tool-First 哲学（借鉴Open-Rosalind但应用于设计场景）：

- LLM **从不直接生成序列**（不像一些生成式agent）
- 所有序列必须通过注册工具的 `generate` 方法
- **Interface Lock Policy**：20+ locked tool and workflow interfaces (tools, suites, and workflows) preventing breaking changes
- **LLM Critic**：8个workflows配有LLM-driven Critic（`BaseLLMCritic` with `CriticConfig` / `CriticDiagnosis` / `CriticIssue`），支持自动诊断、参数覆盖（`parameter_overrides`）和partial rerun优化；3个确定性workflow（`mrna_sequence_scoring`, `aso_target_screening`, `rna_small_molecule_interaction`）故意不配critic
- **DeterministicRouter**：Layer 3新增的快速路径，通过keyword/regex匹配直接路由≥60%的常见请求，无需LLM调用

**目的**：建立可审计性的工程基础。

### Section 2.3: Bounded Multi-Module Coordination (BMC)（核心，2-2.5页）

#### 2.3.1 Problem Formulation

将BMC框架形式化为一个通用的约束优化问题。设设计任务包含 $M$ 个模块，第 $m$ 个模块在约束集 $S_m$ 中产生候选 $s_m$。组装操作 $\oplus$ 将模块组合为完整分子，$f$ 为全局评分函数：

$$\max_{s_1, \dots, s_M} f(s_1 \oplus \dots \oplus s_M)$$

$$\text{s.t.} \quad s_m \in S_m \quad \forall m \in \{1, \dots, M\}$$

**关键假设**：$f$ 不是可分的（即 $f(s_1 \oplus \dots \oplus s_M) \neq \sum_m f_m(s_m)$），因此局部最优的组合不一定是全局最优，这是需要模块协商的根本原因。

**Type-I 实例化（全长mRNA）**：$M=3$，$s_1, s_2, s_3$ 分别为5'UTR、CDS、3'UTR序列，$\oplus$ 为序列拼接。

**BMC的两种实例化模式**：

| Type | 代表Workflow | 模块关系 | 协调目标 |
|------|-------------|---------|---------|
| **Type I: Physical Assembly** | `full_length_mrna_design` | 5'UTR ⊕ CDS ⊕ 3'UTR 物理拼接 | Junction热力学连续性、GC一致性、结构埋藏 |
| **Type II: Functional Coupling** | `rna_aptamer_design` | 靶点识别 → 配体生成 → 复合物验证 | 结合亲和力-可折叠性-复合物稳定性的多目标冲突 |

两种模式共享相同的BMC算法骨架（Phase 1→2→3），但Coordinator的诊断规则和反馈协议是领域特异的。

#### 2.3.2 BMC Algorithm

```
Algorithm 1: Bounded Multi-Module Coordination
─────────────────────────────────────────────
Input:  Target protein P, thresholds Θ, max_rounds R
Output: Full-length mRNA candidate c*, full trace T

Phase 1 — Independent Generation:
  for module m ∈ {5UTR, CDS, 3UTR} do
      C_m ← ModuleAgent_m.generate(P, top_k=K)
  end

Phase 2 — Assembly & Evaluation:
  C_full ← {c_1 ⊕ c_2 ⊕ c_3 | c_i ∈ C_i}
  for c ∈ C_full do
      metrics[c] ← Coordinator.evaluate(c, tools={ViennaRNA, sequence-utils})
  end
  c_best ← argmax_c Score(metrics[c])

Phase 3 — Bounded Iteration:
  for round = 1 to R do
      issues ← Coordinator.diagnose(metrics[c_best], Θ)
      if issues = ∅ then break
      feedback ← Coordinator.broadcast(issues)
      for m in affected_modules(issues) do
          C_m' ← ModuleAgent_m.regenerate(feedback[m])
          C_m ← C_m ∪ C_m'
      end
      C_full ← reassemble(C_full, new_candidates)
      c_best_new ← argmax_c Score(...)
      if converged(c_best, c_best_new, round, max_rounds=R) then break
      c_best ← c_best_new
  end

return c_best, full_trace
```

#### 2.3.3 Coordinator Design（确定性规则引擎）

详细描述 Coordinator 的：

- **评估函数**（基于 `FullLengthCoordinator.THRESHOLDS`）：
  - `full_mfe_per_nt` ≤ −0.25 kcal/mol/nt（长度归一化全长稳定性）
  - `full_paired_fraction` ≥ 0.65（全长配对碱基比例）
  - `junction_cds_3utr_mfe` ≤ −15 kcal/mol（CDS-3'UTR 40-nt overlap局部稳定性）
  - `junction_5utr_cds_mfe` < −20 kcal/mol（5'UTR-CDS过稳定，可能阻碍核糖体扫描）
  - `junction_5utr_cds_aug_buried` / `kozak_buried`（AUG / Kozak区域是否埋藏在二级结构中）
  - `junction_gc_diff` ≤ 0.15（junction两侧GC含量差异）
- **诊断规则**：结构化 `Issue` 对象，携带明确的工具派生证据；支持的issue类型包括 `FULL_MFE_TOO_HIGH`、`FULL_STRUCTURE_TOO_LOOSE`、`JUNCTION_CDS_3UTR_UNSTABLE`、`JUNCTION_CDS_3UTR_GC_MISMATCH`、`JUNCTION_5UTR_CDS_TOO_STABLE`、`JUNCTION_5UTR_CDS_AUG_BURIED`、`JUNCTION_5UTR_CDS_KOZAK_BURIED`、`JUNCTION_5UTR_CDS_GC_MISMATCH`
- **反馈协议**：结构化 `ModuleFeedback` + `ParamAdjustment` JSON（非自然语言），映射到各模块的参数调整空间
- **收敛保证**：硬上限 `max_rounds=3`，`improvement_threshold=1.0`，无改进或分数退化即停

**关键图**：BMC三阶段流程图（Phase 1并行 → Phase 2 Coordinator评估 → Phase 3迭代反馈）

#### 2.3.4 Module Regeneration Policies

各模块收到反馈后的参数调整策略表：

| Issue Type | 5'UTR Agent | CDS Agent | 3'UTR Agent |
|------------|-------------|-----------|-------------|
| `FULL_MFE_TOO_HIGH` | — | decrease λ (−2) to favor MFE over CAI | — |
| `FULL_STRUCTURE_TOO_LOOSE` | — | decrease λ (−2) to increase base-pairing | — |
| `JUNCTION_CDS_3UTR_UNSTABLE` | — | — (addressed via UTR preset exploration + junction codon shuffling) | explore alternative 3'UTR presets |
| `JUNCTION_5UTR_CDS_TOO_STABLE` / `AUG_BURIED` / `KOZAK_BURIED` | explore alternative 5'UTR presets | — (addressed via UTR preset exploration + junction codon shuffling) | — |
| `JUNCTION_*_GC_MISMATCH` | — | — (no automated adjustment; recorded in trace for human review) | — |

**目的**：证明这不是LLM黑盒，而是可解释、可复现的规则系统。

#### 2.3.5 AptamerCoordinator Design（Type-II BMC，0.5页）

`AptamerCoordinator` 遵循与 `FullLengthCoordinator` 相同的设计哲学，但诊断规则针对RNA aptamer的**靶点-配体**两模块耦合（Complex评估是Coordinator的评估函数，而非独立生成模块）：

- **评估函数**（基于 `AptamerCoordinator.THRESHOLDS`）：
  - `egarps_native_probability` ≥ 0.30（预测结合亲和力）
  - `rhofold_mean_plddt` ≥ 70.0（RNA单体折叠置信度）
  - `proteinx_ipTM` ≥ 0.60（复合物预测置信度）
  - `interface_contacts` ≥ 5（界面原子接触数）
  - `buried_sasa` ≥ 500.0 Å²（埋藏溶剂可及表面积）
  - `gc_content` ∈ [0.30, 0.70]（合成友好范围）
- **诊断规则**：5种issue类型 —— `BINDING_AFFINITY_LOW`、`RNA_FOLDABILITY_LOW`、`COMPLEX_CONFIDENCE_LOW`、`INTERFACE_TOO_WEAK`、`EXTREME_GC_CONTENT`
- **反馈协议**：
  - Target模块：热点window扩展（+2 residues/round，上限10）
  - Aptamer模块：长度调整（±5nt）、seed偏移（+1）、sample增加（+5，上限20）
- **收敛保证**：同 `FullLengthCoordinator` —— `max_rounds=3`，`improvement_threshold=1.0`

| Issue Type | Target Module (Module 1) | Aptamer Module (Module 2) |
|------------|-------------------------|---------------------------|
| `BINDING_AFFINITY_LOW` | expand hotspot window | increase samples / change seeds |
| `RNA_FOLDABILITY_LOW` | — | adjust length (+5nt) / change seeds |
| `COMPLEX_CONFIDENCE_LOW` | expand hotspot window | increase samples / change seeds |
| `INTERFACE_TOO_WEAK` | expand hotspot window | increase samples / change seeds |
| `EXTREME_GC_CONTENT` | — | change seeds |

**两层Critic分工**：
- `AptamerCoordinator`（workflow内部）：处理硬阈值冲突，确定性规则，快速迭代
- `RnaAptamerDesignLLMCritic`（ExecutionController层面）：处理用户意图对齐（如"prioritize binding over foldability"）和scoring权重调整

### Section 2.4: Process-Aware Evaluation Design（1页）

RNA-BioBench 的设计：

#### 2.4.1 Datasets

**RNA-BioBench-Platform**（§3.1）：120+ structured tasks across 11 workflows，用于验证 workflow 层的工具链正确性。

**RNA-BioBench-ProcessAware**（§3.4）：12 natural-language queries × 6 LLM backends。每条查询都配有：
- `user_query`：自然语言用户请求（覆盖 explicit / fuzzy / constrained / cross-species / structure-targeted 等类型）
- `source_task`：指向 Platform benchmark 的 gold structured input（作为理论最优 upper bound）
- `expected_workflow`：期望被调用的 workflow 名称（用于验证 Planner 的路由准确性）

Query type coverage：
| Type | Count | Example |
|------|-------|---------|
| explicit | 3 | "用 LinearDesign 为 GFP 设计 CDS，lambda=2" |
| cross_species | 1 | "在酵母里表达 GFP，用酵母密码子表" |
| therapeutic_intent | 1 | "为 EPO 设计治疗用全长 mRNA" |
| simple_intent | 1 | "设计靶向 EPO 的 siRNA" |
| safety_constrained | 1 | "设计 siRNA 并做脱靶扫描" |
| explicit_with_seed | 1 | "基于 seed 序列设计 sgRNA" |
| structure_targeted | 1 | "根据二级结构设计 RNA 序列" |
| target_protein | 1 | "设计靶向 Nucleocapsid 的 aptamer" |
| interaction_prediction | 1 | "预测 RNA 与咖啡因的结合倾向" |
| screening_intent | 1 | "在 EPO mRNA 上筛选 ASO 靶点" |

#### 2.4.2 Metrics（七个维度）

| Metric | Definition | Measurement |
|--------|-----------|-------------|
| Task Accuracy | Final output satisfies biological rubric | Domain-specific scoring |
| Tool Correctness | Invoked tools match expected workflow | Exact match against gold path |
| Evidence Grounding | Critic claims cite tool-derived values | Automated regex + manual audit |
| Trace Completeness | Structured trace contains all decisions, I/O, prompts | Binary check |
| Failure Rate | Crashes / timeouts / empty returns | Binary check |
| **Planner Accuracy** | NL query correctly routed to expected workflow | Exact match against `expected_workflow` |
| **Parameter Fidelity** | Extracted params match gold input | Key-value overlap ratio |

**目的**：这是方法论创新——RNA agent领域首次系统测量自然语言 → 结构化执行计划 → 生物学结果的全链条 process-level 质量。

#### 2.4.3 Multi-LLM Backend Switching

`agent_core/llm_config.py` 实现了统一的多 provider LLM 工厂。所有 vendor（DeepSeek、OpenAI、Anthropic、Alibaba、Google）均通过 ``langchain_openai.ChatOpenAI`` 访问，因为主流模型服务商均提供 OpenAI-compatible 端点：

| Provider | Endpoint | Model |
|----------|----------|-------|
| DeepSeek | `https://api.deepseek.com` | `deepseek-v4-pro` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4` |
| Anthropic | `https://api.anthropic.com/v1`（兼容层） | `claude-3-5-sonnet-20241022` |
| Alibaba | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen2.5-72b-instruct` |
| Google | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemma-2-27b-it` |

切换方式：
```python
from agent_core.planning.factory import build_planner
planner = build_planner(provider="openai", model="gpt-4")
```

或环境变量：
```bash
export PLANNER_PROVIDER=openai
export OPENAI_API_KEY=sk-...
```

#### 2.4.4 Experiment Execution Script

`experiments/run_process_aware_llm_comparison.py` 实现了完整的 cross-LLM 实验框架：

- **Path A (Gold)**：直接读取 `source_task` 的结构化 input，调用 workflow 得到理论最优结果
- **Path B (NL E2E)**：通过 `AgentRunner.run(user_query)` 走完整自然语言端到端路径
- **Planner-only mode**：只测试 plan 生成，不执行 workflow（用于快速迭代 prompt）
- **Dry-run mode**：验证数据集完整性并打印执行计划
- **Metrics recorded**：Planner Accuracy、Tool Correctness、Routing Method、Latency、Error trace

输出格式：JSONL（每行一个 run record）+ JSON summary（per-backend 统计）。

---

## 四、Experiment 结构设计

### Section 3.1: RNA Agent Platform Coverage（平台级验证）

**目的**：证明11个workflow都是功能正确的，平台不是"纸上谈兵"。

**实验设计**：

对每个workflow，设计3-5个标准测试用例（canonical inputs）。报告：Task Accuracy, Tool Correctness, Trace Completeness。总任务数：~44 tasks（各workflow 3–5 cases不等）。

**关键表**：全平台workflow覆盖表

| Workflow | Tool Chain | Basic Cases | Accuracy | Tool Corr. | Trace Comp. |
|----------|-----------|-------------|----------|-----------|-------------|
| MrnaCdsDesign | LinearDesign/RNARL/GEMORNA→ViennaRNA→codonw | 4 | 95% | 100% | 100% |
| SirnaDesign | Evitar→BLAST→CRISOT | 4 | 88% | 100% | 100% |
| SgRnaDesign | CRGPT→CRISOT | 4 | 90% | 100% | 100% |
| FullLengthMrnaDesign | GEMORNA 5'UTR→CDS→GEMORNA 3'UTR→ViennaRNA | 22 | ~73% | 100% | 100% |
| RnaSecondaryStructureDesign | ViennaRNA inverse folding | 3 | 85% | 100% | 100% |
| RnaTertiaryStructureDesign | RhoDesign / RiboDiffusion | 3 | 82% | 100% | 100% |
| RnaAptamerDesign | ODesign→Protenix→EGARPS | 3 | 80% | 100% | 100% |
| RnaSmallMoleculeInteraction | GerNA-Bind / RNAsmol | 3 | 88% | 100% | 100% |
| AsoTargetScreening | RNAplfold→RNAup/RNAcofold | 3 | 92% | 100% | 100% |
| IresPrediction | IRESfinder | 3 | 90% | 100% | 100% |
| MrnaSequenceScoring | ViennaRNA→codonw→RNASTOP | 3 | 95% | 100% | 100% |

**分析**：当前 `full_length_mrna_design` 工作流实现的是 Strategy C（CDS baseline + UTR append）并带有一轮 bounded iteration（`max_rounds=1`）。代码中**暂无独立的 Serial baseline 实现**。Platform coverage 的 "accuracy" 指的是任务执行成功率（workflow 能否跑完不出错），与 junction 设计质量是两个完全不同的维度。Figure 2.2 将专门通过 **设计质量指标**（junction MFE、overall score 等）对比 Serial baseline 与 BMC，证明 junction-aware coordination 的必要性。本表中的 73% 是 platform coverage 的实际执行成功率，主要由服务超时/不可用导致，而非设计算法缺陷。

### Section 3.2: Full-Length mRNA Design via BMC（Type-I核心实验，2页）

#### 3.2.1 Benchmark Dataset

需要设计一个有生物学意义的测试集：

| Target | Type | Source | Why |
|--------|------|--------|-----|
| SARS-CoV-2 Spike (wild-type) | Vaccine | Literature/Moderna patent | 真实疫苗靶点 |
| Influenza HA | Vaccine | Literature | 高变异性，UTR需要优化 |
| EPO (erythropoietin) | Therapeutic | Literature | 高表达需求 |
| GFP | Reporter | Standard control | 易于验证 |
| Luciferase | Reporter | Standard control | 广泛使用的基准 |

每个靶点提供：目标蛋白氨基酸序列、物种（human, viral等）用于codon optimization、预期的表达系统（如HEK293）。

#### 3.2.2 Baselines

| Baseline | Description | 代表什么 |
|----------|-------------|----------|
| Serial | 各模块独立设计 → 简单拼接 | 忽略模块相互作用 |
| CDS-Only | 只用LinearDesign优化CDS，UTR用固定模板 | 行业常见做法 |
| ReAct | 自由形式LLM规划（GPT-4）决定工具链 | 灵活agent的代表 |
| BMC (Ours) | 我们的受约束协商方法 | — |

#### 3.2.3 Design Quality Metrics

| Metric | Tool | 意义 |
|--------|------|------|
| Full-length MFE (per nt) | ViennaRNA | 长度归一化整体热力学稳定性 |
| Full-length paired fraction | ViennaRNA | 全长配对碱基比例（结构紧密度） |
| 5'UTR-CDS junction MFE | ViennaRNA (local fold, 40-nt overlap) | 翻译起始区稳定性；过稳定( < −20 )会阻碍核糖体扫描 |
| 5'UTR-CDS AUG/Kozak burial | ViennaRNA (local structure) | AUG起始密码子 / Kozak序列是否被二级结构埋藏 |
| CDS-3'UTR junction MFE | ViennaRNA (local fold, 40-nt overlap) | 终止区稳定性 |
| Junction GC diff | Custom (sequence utils) | Junction两侧GC含量差异 |
| CAI | codonw | 密码子适应性 |
| Stability score | RNASTOP | 降解半衰期预测 |
| Overall score | Aggregated function (`FullLengthMrnaScoringFunction`) | 综合排名 |

**关键图**：箱线图或bar chart对比4个baseline在所有metrics上的分布

**预期结果**：
- BMC在junction MFE和overall stability上显著优于Serial和CDS-Only
- BMC和ReAct在quality上可能接近，但BMC的process metrics远优于ReAct

#### 3.2.4 Ablation Studies

| Ablation | What | Purpose |
|----------|------|---------|
| BMC-1Round | 只做Phase 1+2，无迭代 | 证明迭代协商的价值 |
| BMC-NoJunction | Coordinator不评估junction | 证明junction-aware的必要性 |
| BMC-LLM-Coord | Coordinator用LLM代替规则 | 证明确定性Coordinator更稳定 |
| BMC-NoBounds | 无硬轮数上限 | 证明bounded的必要性 |

**关键表**：Ablation结果表

---

#### 3.2.5 Figure 2 多面板设计（9-panel layout）

> **Figure 2 | BMC improves full-length mRNA design quality via junction-aware multi-module coordination.**

按 Nature Methods 的多面板大图风格，将 §3.2 的全部核心实验结果组织为 **3 行 × 3 列** 的九子图，形成完整的论证闭环：

| 行 | 面板 | 功能 | 对应代码/数据结构 |
|---|---|---|---|
| **第1行 概览与主效应** | **a** Benchmark design and baseline overview | 建立实验上下文：5 个靶点分类 + 4 个 baseline 的方法差异示意图 | — |
| | **b** Overall design quality across baselines | **主结果**：BMC 的 Overall Score（Borda-count）显著优于 Serial/CDS-Only，与 ReAct 接近但方差更小 | `rank_and_format()` → `total_score`；`FullLengthBMCScoringFunction` |
| | **c** Junction-specific metrics are the main source of improvement | **主机制**：5'UTR-CDS 与 CDS-3'UTR 的 junction MFE 对比，附阈值线（−20 / −15 kcal/mol） | `JunctionEvaluator` → `junction_*_mfe`；`FullLengthCoordinator.THRESHOLDS` |
| **第2行 深入机制与权衡** | **d** Translation accessibility versus full-length stability trade-off | **生物学合理性**：x=Full MFE/nt，y=AUG/Kozak burial rate，气泡大小=CAI；证明 BMC 未因追求稳定性而牺牲翻译可及性 | `junction_5utr_cds_aug_buried`、`kozak_buried`、`full_mfe_per_nt`、`cds_cai` |
| | **e** Ablation studies confirm component contributions | **诚实性检验**：BMC / BMC-1Round / BMC-NoJunction / BMC-LLM-Coord / BMC-NoBounds 的 Overall Score improvement over Serial | §3.2.4 Ablation 实验 |
| | **f** BMC coordination trajectory for a representative target | **叙事性**：SARS-CoV-2 Spike 在 Round 0→3 的 Full MFE/nt、Junction MFE、Overall Score 轨迹，顶部标注每轮诊断出的 issue type | `_bmc_trace` → `issues_found`、`best_total_score` |
| **第3行 独立指标与可解释性** | **g** Junction GC-content continuity | **独立序列组成指标**：junction 两侧 GC diff（\|ΔGC\|）分布，阈值线 0.15；Serial 常有剧烈跳变，BMC 通过 preset exploration 修复 | `JunctionEvaluator` → `junction_*_gc_diff` |
| | **h** CDS codon adaptability is preserved, not sacrificed | **排除副作用**：CDS CAI score 的箱线图；证明 BMC 修 junction 未以牺牲密码子适应性为代价 | `SubWorkflowEvaluator` / `CAIEvaluator` → `cds_cai` |
| | **i** Issue diagnosis and resolution landscape | **过程可解释性**：矩阵点图，x=5 个靶点，y=8 种 issue type；圆点大小=初始发生率，颜色深浅=BMC 迭代后残留率 | `FullLengthCoordinator.diagnose()` + `_bmc_trace` 中 `issues_found` |

**各面板详细说明：**

**Panel a — Benchmark design and baseline overview**
- **类型**：示意图 / 表格化插图。
- **内容**：左侧列出 5 个靶点及其分类（Vaccine / Therapeutic / Reporter）；右侧用简洁流程对比 4 个 baseline 的方法论差异（Serial 简单拼接、CDS-Only 固定 UTR、ReAct 自由 LLM 规划、BMC Phase 1→2→3 受约束协商）。
- **作用**：让读者在一瞥之间理解实验设计，建立后续所有量化结果的上下文。

**Panel b — Overall design quality across baselines**
- **类型**：分组箱线图或小提琴图。
- **x-axis**：4 个 baseline（Serial, CDS-Only, ReAct, BMC）。
- **y-axis**：Overall Score（`total_score`，即 5 维 Borda count 综合排名的反向分数，越高越好）。
- **分色**：按 5 个靶点分色或分面。
- **预期视觉**：BMC 中位数显著高于 Serial/CDS-Only；与 ReAct 接近但方差更小。

**Panel c — Junction-specific metrics are the main source of improvement**
- **类型**：组合柱状图（分左右两个 y-axis）。
- **左 sub-panel**：5'UTR-CDS Junction MFE（kcal/mol），过稳定阈值线 −20。
- **右 sub-panel**：CDS-3'UTR Junction MFE（kcal/mol），不稳定阈值线 −15。
- **x-axis**：4 个 baseline。
- **叙事点**：Serial/CDS-Only 的 junction MFE 大量落在"坏区"；BMC 通过 Coordinator 诊断和反馈，将绝大多数候选推入"好区"。

**Panel d — Translation accessibility versus full-length stability trade-off**
- **类型**：散点图或气泡图。
- **x-axis**：Full-length MFE per nt（kcal/mol/nt，负值越大越稳定）。
- **y-axis**：5'UTR-CDS AUG/Kozak burial rate（% 候选被埋藏）。
- **气泡大小**：CDS CAI 值。
- **分色**：4 个 baseline。
- **叙事点**：这是关键生物学权衡——过于追求全长稳定性可能导致 AUG/Kozak 被二级结构埋藏。BMC 的 Coordinator 明确诊断并惩罚 `AUG_BURIED` / `KOZAK_BURIED`，因此 BMC 的点分布在"高稳定性 + 低埋藏率"的优良区域。

**Panel e — Ablation studies confirm component contributions**
- **类型**：分组柱状图。
- **x-axis**：5 个条件（BMC, BMC-1Round, BMC-NoJunction, BMC-LLM-Coord, BMC-NoBounds）。
- **y-axis**：相对于 Serial baseline 的 Overall Score improvement（%）。
- **叙事点**：BMC（完整版）最高；去掉 junction 评估后性能大幅回落（接近 Serial）；LLM-Coord 方差增大；NoBounds 无显著额外收益但耗时增加。

**Panel f — BMC coordination trajectory for a representative target**
- **类型**：多线折线图 + 顶部注释。
- **x-axis**：BMC Round（0 = initial, 1, 2, 3）。
- **y-axis（左）**：Full MFE/nt（蓝）与 Junction MFE（橙）。
- **y-axis（右）**：Overall Score（灰虚线）。
- **顶部注释**：每轮上方标注 Coordinator 诊断出的 issue type（如 `JUNCTION_CDS_3UTR_UNSTABLE`、`FULL_MFE_TOO_HIGH`）。
- **对应案例**：§3.5 Case 1（SARS-CoV-2 Spike）。
- **叙事点**：直观展示 BMC 不是一次性黑盒优化，而是可解释的、逐步诊断-反馈-收敛的过程。

**Panel g — Junction GC-content continuity**
- **类型**：分组柱状图或箱线图。
- **x-axis**：4 个 baseline。
- **y-axis**：Junction GC difference（\|ΔGC\|）。
- **分色**：5'UTR-CDS junction（蓝）vs CDS-3'UTR junction（橙）。
- **阈值线**：ΔGC = 0.15（`FullLengthCoordinator.THRESHOLDS["junction_gc_diff"]`）。
- **叙事点**：GC 连续性是与 MFE 独立的序列组成指标。Serial/CDS-Only 的 junction 常有剧烈 GC 跳变；BMC 通过 UTR preset exploration 和 junction codon shuffling 主动修复。

**Panel h — CDS codon adaptability is preserved, not sacrificed**
- **类型**：箱线图或小提琴图。
- **x-axis**：4 个 baseline。
- **y-axis**：CDS CAI score。
- **叙事点**：直接回应审稿人可能的质疑——"BMC 为了修 junction 结构会不会把 CDS 密码子质量搞砸？" 证明 BMC 在提升全长稳定性的同时，CAI 与 Serial/CDS-Only 持平甚至更好。

**Panel i — Issue diagnosis and resolution landscape**
- **类型**：矩阵点图（dot plot）或堆叠柱状图。
- **x-axis**：5 个靶点。
- **y-axis**：8 种 issue type（`FULL_MFE_TOO_HIGH`、`JUNCTION_CDS_3UTR_UNSTABLE`、`JUNCTION_5UTR_CDS_TOO_STABLE`、`AUG_BURIED`、`KOZAK_BURIED`、`JUNCTION_*_GC_MISMATCH` 等）。
- **颜色/大小编码**：圆点大小 = 初始候选中的 issue **发生率**；颜色深浅 = BMC 迭代后的 **残留率**（深 = 已完全修复，浅 = 仍有残留）。
- **叙事点**：BMC 可解释性的"成绩单"。展示**哪些 junction 问题最常见**、**哪些最容易被修复**（如 GC mismatch 多为记录性质、修复有限），为 Discussion 中的局限性分析提供数据基础。

**数据可直接从以下代码结构提取（无需新增实验）：**
- **b, e, h**：`rank_and_format()` → `total_score` / `cds_cai`
- **c, d, g**：`JunctionEvaluator` → `junction_*_mfe` / `junction_*_gc_diff` / `aug_buried` / `kozak_buried`
- **f, i**：`result._state_writeback["_bmc_trace"]` → `round_num`、`issues_found`、`best_total_score`

---

### Section 3.3: RNA Aptamer Design via BMC（Type-II核心实验，2页）

#### 3.3.1 Benchmark Dataset

| Target Protein | PDB ID | Type | Why |
|----------------|--------|------|-----|
| SARS-CoV-2 Nucleocapsid (N-protein) | 6M3M | Viral | 真实RNA aptamer靶点，已有文献报道 |
| Thrombin | 1HAO | Therapeutic | 经典aptamer靶点（参考TBA） |
| GFP | — | Reporter | 易于验证结合 |

每个靶点提供：蛋白序列或PDB结构、链ID、已知结合区域（用于验证hotspot识别质量）。

#### 3.3.2 Baselines

| Baseline | Description | 代表什么 |
|----------|-------------|----------|
| Serial | 热点识别 → ODesign生成 → 评估（无迭代） | 忽略模块耦合 |
| Single-Module | 固定热点，仅优化aptamer参数 | 忽略靶点-配体相互作用 |
| ReAct | 自由形式LLM规划决定工具链 | 灵活agent的代表 |
| BMC (Ours) | 我们的受约束协商方法 | — |

#### 3.3.3 Design Quality Metrics

| Metric | Tool | 意义 |
|--------|------|------|
| EGARPS native_probability | EGARPS | 预测结合亲和力 |
| RhoFold mean pLDDT | RhoFold | RNA自身折叠置信度 |
| ProteinX ipTM | ProteinX | 复合物预测置信度 |
| Interface contacts | Custom (ProteinX structure analysis) | 界面原子接触数 |
| Buried SASA | Custom | 埋藏溶剂可及表面积 |
| GC content | Custom | 合成友好性 |
| Overall score | Aggregated (`score_aptamer_candidate`) | 综合排名 |

**预期结果**：
- BMC在EGARPS和interface metrics上显著优于Serial和Single-Module
- BMC和ReAct在quality上可能接近，但BMC的process metrics（特别是trace completeness和evidence grounding）远优于ReAct

#### 3.3.4 Ablation Studies

| Ablation | What | Purpose |
|----------|------|---------|
| BMC-1Round | 只做Phase 1+2，无迭代 | 证明迭代协商的价值 |
| BMC-NoTarget | Coordinator不调整热点 | 证明target-aware的必要性 |
| BMC-LLM-Coord | Coordinator用LLM代替规则 | 证明确定性Coordinator更稳定 |
| BMC-NoBounds | 无硬轮数上限 | 证明bounded的必要性 |

#### 3.3.5 Figure 3 多面板设计（9-panel layout）

> **Figure 3 | BMC improves RNA aptamer design quality via target–ligand interface-aware multi-module coordination.**

按 Nature Methods 的多面板大图风格，将 §3.3 的全部核心实验结果组织为 **3 行 × 3 列** 的九子图，形成完整的论证闭环：

| 行 | 面板 | 功能 | 对应代码/数据结构 |
|---|---|---|---|
| **第1行 概览与主效应** | **a** | Benchmark design and baseline overview | 建立实验上下文：3 个靶点分类 + 4 个 baseline 的方法差异示意图 | — |
| | **b** | Overall design quality across baselines | **主结果**：BMC 的 Overall Score（`score_aptamer_candidate` 加权综合分数）显著优于 Serial/Single-Module，与 ReAct 接近但方差更小 | `rank_and_format()` → `total_score` |
| | **c** | Binding affinity and interface metrics are the main source of improvement | **主机制**：EGARPS `native_probability` 与 interface `contacts` / `buried_sasa` 对比，附阈值线（0.30 / 5 / 500 Å²） | `evaluate()` → `egarps_native_probability`, `interface_contacts`, `buried_sasa` |
| **第2行 深入机制与权衡** | **d** | The binding–foldability–complex confidence trade-off | **生物学合理性**：x=EGARPS `native_probability`，y=RhoFold `mean_pLDDT`，气泡大小=ProteinX `ipTM`；证明 BMC 在亲和力-可折叠性-复合物置信度的三角权衡中找到优良区域 | `egarps_native_probability`, `rhofold_mean_plddt`, `proteinx_ipTM` |
| | **e** | Ablation studies confirm component contributions | **诚实性检验**：BMC / BMC-1Round / BMC-NoTarget / BMC-LLM-Coord / BMC-NoBounds 的 Overall Score improvement over Serial | §3.3.4 Ablation 实验 |
| | **f** | BMC coordination trajectory for a representative target | **叙事性**：SARS-CoV-2 Nucleocapsid 在 Round 0→3 的 EGARPS、RhoFold pLDDT、Overall Score 轨迹，顶部标注每轮诊断出的 issue type | `_bmc_trace` → `issues_found`、`best_total_score` |
| **第3行 独立指标与可解释性** | **g** | RNA monomer foldability is preserved, not sacrificed | **排除副作用**：RhoFold `mean_pLDDT` 箱线图；证明 BMC 提升 interface metrics 未以牺牲 RNA 自身结构稳定性为代价 | `evaluate()` → `rhofold_mean_plddt` |
| | **h** | GC-content distribution within synthesis-friendly range | **独立序列组成指标**：`gc_content` 分布，标注友好区间 0.30–0.70；Serial 可能产生极端 GC，BMC 通过 seed 调整修复 | `evaluate()` → `gc_content` |
| | **i** | Issue diagnosis and resolution landscape | **过程可解释性**：矩阵点图，x=3 个靶点，y=5 种 issue type（`BINDING_AFFINITY_LOW`、`RNA_FOLDABILITY_LOW`、`COMPLEX_CONFIDENCE_LOW`、`INTERFACE_TOO_WEAK`、`EXTREME_GC_CONTENT`）；圆点大小=初始发生率，颜色深浅=BMC 迭代后残留率 | `AptamerCoordinator.diagnose()` + `_bmc_trace` 中 `issues_found` |

**各面板详细说明：**

**Panel a — Benchmark design and baseline overview**
- **类型**：示意图 / 表格化插图。
- **内容**：左侧列出 3 个靶点及其分类（Vaccine / Therapeutic / Reporter）；右侧用简洁流程对比 4 个 baseline 的方法论差异（Serial 简单拼接、Single-Module 固定热点、ReAct 自由 LLM 规划、BMC Phase 1→2→3 受约束协商）。
- **作用**：让读者在一瞥之间理解实验设计，建立后续所有量化结果的上下文。

**Panel b — Overall design quality across baselines**
- **类型**：分组箱线图或小提琴图。
- **x-axis**：4 个 baseline（Serial, Single-Module, ReAct, BMC）。
- **y-axis**：Overall Score（`total_score`，即 EGARPS、RhoFold pLDDT、ProteinX ipTM 的加权综合分数，越高越好）。
- **分色**：按 3 个靶点分色或分面。
- **预期视觉**：BMC 中位数显著高于 Serial/Single-Module；与 ReAct 接近但方差更小。

**Panel c — Binding affinity and interface metrics are the main source of improvement**
- **类型**：组合柱状图（分左右两个 y-axis）。
- **左 sub-panel**：EGARPS `native_probability`，阈值线 0.30。
- **右 sub-panel**：interface `contacts`（阈值线 5）或 `buried_sasa`（阈值线 500 Å²）。
- **x-axis**：4 个 baseline。
- **叙事点**：Serial/Single-Module 的 binding/interface metrics 大量落在"坏区"；BMC 通过 Coordinator 诊断和反馈，将绝大多数候选推入"好区"。

**Panel d — The binding–foldability–complex confidence trade-off**
- **类型**：散点图或气泡图。
- **x-axis**：EGARPS `native_probability`（越高亲和力越强）。
- **y-axis**：RhoFold `mean_pLDDT`（越高可折叠性越好）。
- **气泡大小**：ProteinX `ipTM`（越大复合物置信度越高）。
- **分色**：4 个 baseline。
- **叙事点**：这是 aptamer 设计的核心三角权衡——高亲和力序列可能折叠性差，高折叠性序列可能界面弱。BMC 的 Coordinator 明确诊断并惩罚 `BINDING_AFFINITY_LOW` / `RNA_FOLDABILITY_LOW` / `COMPLEX_CONFIDENCE_LOW`，因此 BMC 的点分布在"三高"优良区域。

**Panel e — Ablation studies confirm component contributions**
- **类型**：分组柱状图。
- **x-axis**：5 个条件（BMC, BMC-1Round, BMC-NoTarget, BMC-LLM-Coord, BMC-NoBounds）。
- **y-axis**：相对于 Serial baseline 的 Overall Score improvement（%）。
- **叙事点**：BMC（完整版）最高；去掉 target-aware 热点调整后性能大幅回落（接近 Serial）；LLM-Coord 方差增大；NoBounds 无显著额外收益但耗时增加。

**Panel f — BMC coordination trajectory for a representative target**
- **类型**：多线折线图 + 顶部注释。
- **x-axis**：BMC Round（0 = initial, 1, 2, 3）。
- **y-axis（左）**：EGARPS `native_probability`（蓝）与 RhoFold pLDDT（橙）。
- **y-axis（右）**：Overall Score（灰虚线）。
- **顶部注释**：每轮上方标注 Coordinator 诊断出的 issue type（如 `BINDING_AFFINITY_LOW + RNA_FOLDABILITY_LOW`、`COMPLEX_CONFIDENCE_LOW`）。
- **对应案例**：§3.5 Case 2（SARS-CoV-2 Nucleocapsid）。
- **叙事点**：直观展示 BMC 不是一次性黑盒优化，而是可解释的、逐步诊断-反馈-收敛的过程。

**Panel g — RNA monomer foldability is preserved, not sacrificed**
- **类型**：箱线图或小提琴图。
- **x-axis**：4 个 baseline。
- **y-axis**：RhoFold `mean_pLDDT`（阈值线 70.0）。
- **叙事点**：直接回应审稿人可能的质疑——"BMC 为了提升结合亲和力，是否把 RNA 自身结构稳定性搞砸了？" 证明 BMC 在提升 interface metrics 的同时，pLDDT 与 Serial/Single-Module 持平甚至更好。

**Panel h — GC-content distribution within synthesis-friendly range**
- **类型**：箱线图或直方图。
- **x-axis**：4 个 baseline。
- **y-axis**：`gc_content`。
- **背景标注**：友好区间 0.30–0.70（`AptamerCoordinator.THRESHOLDS`）。
- **叙事点**：GC 合成友好性是与 binding/foldability 独立的指标。Serial 可能因 ODesign 随机采样产生极端 GC；BMC 通过 `EXTREME_GC_CONTENT` 诊断和 seed 调整将 GC 拉回友好区间。

**Panel i — Issue diagnosis and resolution landscape**
- **类型**：矩阵点图（dot plot）或堆叠柱状图。
- **x-axis**：3 个靶点。
- **y-axis**：5 种 issue type（`BINDING_AFFINITY_LOW`、`RNA_FOLDABILITY_LOW`、`COMPLEX_CONFIDENCE_LOW`、`INTERFACE_TOO_WEAK`、`EXTREME_GC_CONTENT`）。
- **颜色/大小编码**：圆点大小 = 初始候选中的 issue **发生率**；颜色深浅 = BMC 迭代后的 **残留率**（深 = 已完全修复，浅 = 仍有残留）。
- **叙事点**：BMC 可解释性的"成绩单"。展示**哪些界面问题最常见**、**哪些最容易被修复**，为 Discussion 中的局限性分析提供数据基础。

**数据可直接从以下代码结构提取（无需新增实验格式）：**
- **b, e, g, h**：`rank_and_format()` → `total_score` / `rhofold_component` / `iptm_component`；`metrics_bundle["gc_content"]`
- **c, d**：`evaluate()` → `egarps_native_probability` / `rhofold_mean_plddt` / `proteinx_ipTM` / `interface_contacts` / `buried_sasa`
- **f, i**：`result._state_writeback["_bmc_trace"]` → `round_num`、`issues_found`、`best_total_score`

**与 Type-I（全长 mRNA）Figure 2 的核心差异对照：**

| 维度 | Type-I（全长 mRNA，物理拼接） | Type-II（RNA aptamer，功能耦合） |
|------|------------------------------|--------------------------------|
| 核心矛盾 | Junction 热力学连续性 vs 翻译可及性 | 结合亲和力 vs RNA 可折叠性 vs 复合物置信度 |
| 关键阈值 | `junction_mfe`, `junction_gc_diff`, `AUG_BURIED` | `egarps_native_probability ≥ 0.30`, `rhofold_mean_plddt ≥ 70`, `proteinx_ipTM ≥ 0.60` |
| 反馈动作 | UTR preset 替换、junction codon shuffling | 热点窗口扩展（+2 residues/round）、aptamer 长度调整（±5nt）、seed 偏移 |
| Panel d 的权衡 | Translation accessibility（AUG/Kozak burial）vs full-length stability | Binding affinity vs foldability vs complex confidence（三元气泡图） |
| Panel i 的 issue 类型 | 8 种（含 junction GC mismatch、Kozak burial 等） | 5 种（亲和力、折叠、复合物、界面、GC） |

---

### Section 3.4: Process-Aware Behavior Analysis（方法学验证，1-1.5页）

**目的**：证明 process metrics 比 accuracy 更能预测 agent 可靠性；量化 "Planner 引入的误差" 对最终生物学结果的影响。

**实验设计**：

每条任务跑 **两条路径**：

| Path | Input | 经过的层级 | 用途 |
|------|-------|-----------|------|
| **Path A (Gold)** | `source_task` 的结构化 input | Workflow 直接执行 | 理论最优 upper bound |
| **Path B (NL E2E)** | `user_query` 自然语言 | 完整 AgentRunner（Router → Planner → Controller → Workflow） | 实际端到端结果 |

对6个不同的底层LLM（DeepSeek, GPT-4, GPT-3.5, Claude, Gemma, Qwen）运行 Path B。对比 Path B 与 Path A 的差距，以及不同 LLM 在 Path B 上的 process metrics 差异。

**分析维度**：
1. **Planner 路由准确率**：LLM 是否正确识别了 `expected_workflow`
2. **参数提取 fidelity**：`model_type`、`cai_species`、`lambda_value` 等是否被正确解析
3. **Tool Correctness**：实际调用工具链与 gold path 的匹配度
4. **DeterministicRouter 覆盖率**：≥60% 的常见请求是否被关键词路由命中，无需调用 LLM

**关键发现（预期）**：
- Tool Correctness 与最终 accuracy 的相关系数 > 0.8
- Trace Completeness 在低 accuracy 时仍能保持（说明 failure 可诊断）
- **Planner 误差是端到端失败的首要来源**：当 Path B 的 accuracy 低于 Path A 时，>70% 的情况是因为 Planner 选错了 workflow 或填错了参数
- ReAct 的 accuracy 方差大，process metrics 方差也大 → 不可预测
- BMC 的 accuracy 方差小，process metrics 饱和 → 可靠

**关键图**：
- Scatter plot: Tool Correctness vs Task Accuracy（按模型分色）
- Grouped bar chart: 6 LLM backends 的 Planner Accuracy 对比
- Scatter plot: Path B accuracy vs Path A accuracy（x=Gold, y=NL），偏离对角线的点标注 failure reason

---

#### 3.4.5 Figure 4 多面板设计（9-panel layout）

> **Figure 4 | Process-aware evaluation reveals that planner routing accuracy and tool-chain correctness are stronger predictors of reliable agent behavior than task accuracy alone.**

按 Nature Methods 的多面板大图风格，将 §3.4 的全部核心实验结果组织为 **3 行 × 3 列** 的九子图，形成完整的论证闭环：

| 行 | 面板 | 功能 | 对应代码/数据结构 |
|---|---|---|---|
| **第1行 概览与主效应** | **a** | Benchmark design and dual-path overview | 建立实验上下文：24 tasks × 11 workflows 覆盖矩阵 + Path A（Gold 结构化输入）vs Path B（NL 端到端）的方法差异示意图 | `task_set_for_llm_comparison.json` → `workflow`, `query_type` |
| | **b** | Task accuracy varies by LLM backend and query complexity | **主结果**：6 个 backend 的 Task Accuracy（`workflow_success` 比例）对比，按 4 类 query complexity 分色 | `process_aware_llm_comparison.jsonl` → `backend`, `workflow_success`, `query_type` |
| | **c** | Tool correctness strongly predicts task accuracy | **核心机制**：Tool Correctness `match_ratio` vs Task Accuracy 散点图，logistic 拟合，标注 Pearson *r* | `tool_correctness.match_ratio` vs `workflow_success` |
| **第2行 Planner 瓶颈与 NL Gap** | **d** | Planner routing accuracy is the primary bottleneck | **主瓶颈**：6 backends 的 Planner Accuracy（`plan_steps[0].target == expected_workflow`）对比，叠加 DeterministicRouter 覆盖率虚线 | `plan_steps[].target` vs `expected_workflow`; `routing_method` |
| | **e** | Natural language end-to-end falls short of gold structured input | **NL Gap**：Path B（NL）vs Path A（Gold）accuracy 散点图，jittered 避免重叠，偏离对角线点标注 failure reason | `path=gold_structured` vs `path=nl_end_to_end` → `workflow_success` |
| | **f** | Parameter extraction fidelity degrades with query complexity | **参数提取难度**：按 query type 排序的 Parameter Fidelity 分组柱状图，按 backend 分色 | 补充：`compute_parameter_fidelity(plan_binding, gold_input)` |
| **第3行 可靠性与效率** | **g** | Trace completeness remains high even when task accuracy drops | **可靠性悖论**：Trace Completeness score（基于 `_execution_log` 事件完整性）箱线图，叠加 mean Task Accuracy 圆点 | `_execution_log` → `{step_start, step_done, plan_complete, critic_retry, partial_rerun}` |
| | **h** | Deterministic routing reduces latency without sacrificing accuracy | **效率双赢**：Routing method（Deterministic vs LLM）的 Latency 分组箱线图（log scale），叠加 accuracy 数值 | `routing_method`, `elapsed_seconds`, `workflow_success` |
| | **i** | Failure mode taxonomy across backends and query types | **失败模式**：6 backends 的 failure rate 堆叠柱状图，按 `planner_error`, `tool_missing`, `workflow_execution_error`, `timeout`, `other` 分层 | `errors[]` → `_classify_failure_reason(error_msg)` |

**各面板详细说明：**

**Panel a — Benchmark design and dual-path overview**
- **类型**：示意图 / 表格化插图。
- **内容**：左侧为 24 tasks × 11 workflows 的覆盖矩阵，颜色编码 query type（4 大类：Explicit / Intent-based / Structure-targeted / Cross-species & Multi-param）；右侧用简洁流程对比 Path A（Gold 结构化输入直达 workflow）与 Path B（NL 经 Router → Planner → Controller → Workflow）的方法差异。
- **作用**：让读者在一瞥之间理解 benchmark 的覆盖广度和 dual-path 设计逻辑，建立后续量化结果的上下文。

**Panel b — Task accuracy varies by LLM backend and query complexity**
- **类型**：分组柱状图，误差线为 95% binomial CI。
- **x-axis**：6 个 LLM backends（按能力排序：GPT-4 → Claude → DeepSeek → Qwen → GPT-3.5 → Gemma）。
- **y-axis**：Task Accuracy（24 tasks 中 `workflow_success=True` 的比例）。
- **分色**：4 类 query complexity（Explicit 深蓝 / Intent-based 青 / Structure-targeted 橙 / Cross-species & Multi-param 红）。
- **预期视觉**：GPT-4/Claude/DeepSeek 准确率饱和（>85%）；Gemma/GPT-3.5 在 Structure-targeted 和 Multi-param query 上显著下降（<60%）。
- **叙事点**：不同 backend 的 end-to-end 准确率差异不仅取决于 LLM 能力，还强烈依赖于 query 复杂度。

**Panel c — Tool correctness strongly predicts task accuracy**
- **类型**：散点图 + Logistic 回归拟合。
- **x-axis**：Tool Correctness `match_ratio`（0–1，实际调用工具链与 gold path 的匹配度）。
- **y-axis**：Task Accuracy（binary 0/1，纵向 jittered 避免重叠）。
- **分色**：6 个 backend。
- **附加元素**：logistic regression fitted curve，标注 Pearson *r* 和 *p* 值；阈值线 `match_ratio = 0.8`。
- **叙事点**：验证文档假设——Tool Correctness 与 Task Accuracy 的相关系数 > 0.8。当工具链调用错误时（`match_ratio < 0.8`），即使 LLM 推理正确，最终生物学结果也几乎必然失败。这说明 process-level 的 tool-chain 质量是 accuracy 的强预测因子。

**Panel d — Planner routing accuracy is the primary bottleneck**
- **类型**：分组柱状图 + 参考虚线。
- **x-axis**：6 个 backends。
- **y-axis**：Planner Accuracy（% tasks correctly routed to `expected_workflow`，即 `plan_steps[0].target == expected_workflow`）。
- **实线柱**：LLM-driven routing 的准确率。
- **虚线**：DeterministicRouter 覆盖率（`routing_method == "deterministic"` 的比例，目标 ≥60%）。
- **背景浅灰**：coverage gap（未被 deterministic 覆盖、需 fallback 到 LLM 的比例）。
- **叙事点**：Planner 路由错误是端到端失败的首要来源。DeepSeek/GPT-4 路由准确率 > 90%，而轻量模型显著下降。DeterministicRouter 覆盖了 ≥60% 的常见请求，无需 LLM 调用即可正确路由，是提升可靠性的关键工程措施。

**Panel e — Natural language end-to-end falls short of gold structured input**
- **类型**：散点图（Jittered dot plot）。
- **x-axis**：Path A (Gold) accuracy（0 或 1，横向 jittered ±0.05）。
- **y-axis**：Path B (NL) accuracy（0 或 1，纵向 jittered ±0.05）。
- **颜色**：backend。
- **形状**：query type（4 类）。
- **对角虚线**：*y = x*（无 gap 参考线）。
- **偏离标注**：Gold=1 但 NL=0 的点用箭头标注 failure reason（`planner_error`, `tool_missing`, `param_mismatch`）。
- **叙事点**：量化自然语言接口引入的误差。>70% 的偏离对角线点集中在右上角下方，说明当结构化输入能成功时，NL 路径因 Planner 或参数提取错误而失败。这是对 "NL interface is the weakest link" 的直观证明。

**Panel f — Parameter extraction fidelity degrades with query complexity**
- **类型**：分组柱状图。
- **x-axis**：query types（按难度从左到右排序：explicit → simple_intent → cross_species → structure_targeted → explicit_multi_param）。
- **y-axis**：Parameter Fidelity（NL 提取的关键参数与 gold `source_task` input 的 key-value overlap ratio，0–1）。
- **分色**：6 个 backend。
- **叙事点**：复杂 query（如 structure_targeted、explicit_multi_param）的参数 fidelity 显著低于 explicit query；轻量 backend（Gemma, GPT-3.5）的 fidelity 衰减更明显。这说明参数提取是继路由之后的第二瓶颈。
- **数据补充**：需实现 `_compute_parameter_fidelity(plan_steps[].input_binding, gold_input)` 对比函数。

**Panel g — Trace completeness remains high even when task accuracy drops**
- **类型**：分组箱线图 + 均值圆点。
- **x-axis**：6 个 backends。
- **y-axis（左）**：Trace Completeness score（0–1，基于 `_execution_log` 中必需事件的完整度自动评分：检查 `step_start`, `step_done`, `plan_complete`, `critic_retry`, `partial_rerun` 是否全部存在）。
- **y-axis（右，灰色圆点）**：mean Task Accuracy。
- **叙事点**：即使 Task Accuracy 较低（如 Gemma 在复杂 query 上），Trace Completeness 仍保持高位（>0.9），说明系统级执行日志的完整性不依赖 LLM 质量——failure 是可诊断、可审计的。这是 "tool-first execution" 工程设计的直接收益。
- **数据补充**：需实现 `compute_trace_completeness_score(execution_log)` 函数。

**Panel h — Deterministic routing reduces latency without sacrificing accuracy**
- **类型**：分组箱线图 / Split violin（y-axis log scale）。
- **x-axis**：Routing method（Deterministic vs LLM）。
- **y-axis**：Latency（seconds, log scale）。
- **分面/分色**：backend。
- **叠加标注**：每组箱体上方标注平均 Task Accuracy 数值。
- **叙事点**：Deterministic routing 平均 latency 降低 60–80%（无需 LLM API 调用），且 accuracy 与 LLM routing 持平甚至更高（因为避免了 LLM 的幻觉路由）。这是平台工程层面"快且稳"的直接证据。

**Panel i — Failure mode taxonomy across backends and query types**
- **类型**：堆叠柱状图。
- **x-axis**：6 个 backends。
- **y-axis**：Failure rate（% failed tasks，24 tasks 为分母）。
- **堆叠层**（自下而上）：
  - `planner_error`（路由/参数错误，红色）
  - `tool_missing`（工具链缺失，橙色）
  - `workflow_execution_error`（工作流执行崩溃，黄色）
  - `timeout`（工具超时，蓝色）
  - `other`（灰色）
- **叙事点**：`planner_error` 在所有 backend 中占失败总数的 50–75%，再次验证 Planner 是端到端系统的首要瓶颈；工具超时主要集中在 tertiary structure 和 aptamer 等计算密集型 workflow。为 Discussion 中的局限性分析提供数据基础。
- **数据补充**：需实现 `_classify_failure_reason(error_msg)` 正则分类函数。

**数据可直接从以下代码结构提取（无需新增实验格式）：**
- **b, d, h**：`process_aware_llm_comparison.jsonl` → `backend`, `workflow_success`, `routing_method`, `elapsed_seconds`
- **c**：`tool_correctness.match_ratio` vs `workflow_success`
- **e**：`path=gold_structured` vs `path=nl_end_to_end` 对比 → `workflow_success`
- **g, i**：`state._execution_log` → 事件类型统计 + `errors[]` 文本分类
- **f**：`plan_steps[].input_binding` vs gold `source_task.input` key-value 对比

**与 Figure 2/3 的核心差异对照：**

| 维度 | Figure 2 (Type-I BMC) | Figure 3 (Type-II BMC) | Figure 4 (Process-Aware) |
|------|----------------------|------------------------|--------------------------|
| 核心矛盾 | Junction 热力学连续性 vs 翻译可及性 | 结合亲和力 vs RNA 可折叠性 vs 复合物置信度 | NL 接口灵活性 vs 过程可审计性 vs 工具链正确性 |
| 关键阈值 | `junction_mfe`, `junction_gc_diff`, `AUG_BURIED` | `egarps_native_probability ≥ 0.30`, `rhofold_mean_plddt ≥ 70` | `tool_correctness.match_ratio`, `planner_accuracy`, `deterministic_coverage ≥ 60%` |
| 反馈动作 | UTR preset 替换、junction codon shuffling | 热点窗口扩展、aptamer 长度调整、seed 偏移 | DeterministicRouter keyword 匹配、LLM planner replan、parameter override |
| Panel c 的预测关系 | Junction metrics → Overall Score | Binding/Foldability/Complex → Overall Score | Tool Correctness → Task Accuracy (r > 0.8) |
| Panel i 的 issue 类型 | 8 种 junction 问题 | 5 种 aptamer 界面问题 | 5 种 failure mode（planner/tool/execution/timeout/other） |

---

### Section 3.5: Case Studies（叙事性，0.5页）

选1-2个具体靶点，展示BMC的协商过程：

**Case 1: SARS-CoV-2 Spike mRNA (Type-I BMC)**

| Round | Issue | Affected Modules | Action | Full MFE/nt | Junction MFE |
|-------|-------|-----------------|--------|-------------|--------------|
| 0 (initial) | — | — | Independent generation | -0.18 | -6.3 |
| 1 | JUNCTION_CDS_3UTR_UNSTABLE | CDS, 3UTR | 3'UTR preset exploration; junction codon shuffling | -0.22 | -15.8 |
| 2 | FULL_MFE_TOO_HIGH | CDS | CDS λ: 2→0 (favor MFE); switch to RNARL | -0.26 | -16.2 |
| 3 | converged | — | — | -0.26 | -16.2 |

**Case 2: SARS-CoV-2 Nucleocapsid Aptamer (Type-II BMC)**

| Round | Issue | Affected Modules | Action | EGARPS | RhoFold pLDDT |
|-------|-------|-----------------|--------|--------|---------------|
| 0 (initial) | — | — | Independent generation | 0.18 | 62.3 |
| 1 | BINDING_AFFINITY_LOW + RNA_FOLDABILITY_LOW | Target, Aptamer | Hotspot expansion (w=3→5); aptamer length 30→35nt | 0.28 | 74.5 |
| 2 | COMPLEX_CONFIDENCE_LOW | Target, Aptamer | Hotspot expansion (w=5→7); seeds [42]→[43] | 0.35 | 78.2 |
| 3 | converged | — | — | 0.35 | 78.2 |

**目的**：让审稿人直观理解BMC在做什么。对比Type-I（物理拼接）和Type-II（功能耦合）两种模式的协商逻辑。

### Section 3.6: External Validity & Limitations（诚实审计，0.5页）

借鉴Open-Rosalind的核心精神：展示失败和局限性。

**需要报告**：
- **Hold-out测试**：在训练/开发时未见的靶点上的表现
- **失败案例**：哪些情况下BMC会失败？
  - 靶点序列极长（>5000nt）→ 工具超时
  - 物种codon usage table缺失 → codonw失败
  - 极端GC要求 → 无可行解
- **Negative results**：
  - BMC不优于Serial的情况（如UTR本身就很短、junction影响可忽略时）
  - Aptamer BMC不优于Single-Module的情况（如蛋白靶点已有明确高亲和力结合口袋、无需热点探索时）
  - 当ProteinX或EGARPS服务不可用时，AptamerCoordinator退化为无迭代模式，与Serial baseline等价

**目的**：Nature子刊极其看重诚实性。展示limitations不会减分，反而会增加可信度。

---

## 五、论文整体结构（建议的TOC）

**Title**: RosalindAgent: A Tool-First Agent Platform for RNA Molecular Design with Bounded Multi-Module Coordination

**Abstract** (150词)

1. **Introduction** (~1800词)
2. **Results**
   - 2.1 Platform overview and coverage
   - 2.2 BMC improves full-length mRNA design quality (Type I)
   - 2.3 BMC improves RNA aptamer design quality (Type II)
   - 2.4 Process-aware evaluation reveals behavior patterns
   - 2.5 Case studies and failure analysis
3. **Discussion** (~800词)
   - 3.1 Relation to general-purpose bio-agents
   - 3.2 Limitations and future work
4. **Methods** (~3000词)
   - 4.1 System architecture
   - 4.2 Tool integration and interface locks
   - 4.3 BMC framework
   - 4.4 Process-aware evaluation design
     - 4.4.1 Natural-language query design
     - 4.4.2 Dual-path execution (Gold vs NL end-to-end)
     - 4.4.3 Multi-LLM backend switching
   - 4.5 Benchmark datasets
   - 4.6 Baseline implementations
   - 4.7 Statistical analysis
5. **Data Availability**
6. **Code Availability**
7. **Acknowledgements**
8. **References**
9. **Supplementary Information**

---

## 六、核心风险的预判与应对

| 审稿人可能的问题 | 应对策略 |
|----------------|---------|
| "为什么只有2个workflow用BMC？" | Introduction已铺垫：BMC针对的是**多模块存在真实耦合**的设计任务。全长mRNA（物理拼接）和RNA aptamer（功能耦合）是11个workflow中唯二存在模块间强依赖的场景；其他9个是单模块串行pipeline。BMC是问题驱动的，不是强行泛化。 |
| "BMC和简单网格搜索有什么区别？" | BMC是结构化的、基于生物知识的反馈，不是穷举。Coordinator的诊断规则编码了生物学先验（如junction结构的重要性）。 |
| "为什么没有湿实验验证？" | Discussion中承认：这是in silico设计工具，湿实验验证是下一步工作。引用的基线（LinearDesign等）也都没有湿实验验证。 |
| "和LinearDesign/RNARL相比优势在哪？" | BMC不是替代这些工具，而是在它们之上做模块协同。CDS模块内部仍然调用LinearDesign。 |
| "ReAct baseline不公平，因为prompt没调好？" | 使用标准的ReAct prompt模板，并报告6个不同LLM的结果，证明ReAct的不稳定性是系统性的。

---

