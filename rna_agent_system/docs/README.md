# RNA Design Multi-Agent System

> **Project root**: `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`  
> **Readers**: human developers / AI agents  
> **Scope**: this document describes the current real code state of `rna_agent_system/`, including capabilities, quick-start, and the master capability matrix.

---

## Table of Contents

1. [Project Goals & Core Principles](#1-project-goals--core-principles)
2. [Architecture at a Glance](#2-architecture-at-a-glance)
3. [Directory Structure](#3-directory-structure)
4. [Master Capability Matrix](#4-master-capability-matrix)
5. [Tool & Port Registry](#5-tool--port-registry)
6. [Agent Workflow Logic](#6-agent-workflow-logic)
7. [Quick Start](#7-quick-start)
8. [Known Limitations & Roadmap](#8-known-limitations--roadmap)

---

## 1. Project Goals & Core Principles

This project implements an RNA design agent system:

- **Input**: natural-language tasks, RNA sequences, protein sequences
- **Output**: design results, scores, and structure predictions produced by underlying bioinformatics tools
- **Mechanism**: the upper Agent layer handles routing and orchestration; lower tools run in isolated local microservices

**Core principles**

| Principle | Description |
|-----------|-------------|
| Sequences never go in prompts | Long sequences travel via `workspace/` file paths, never inside chat context |
| Environment isolation | Every tool has its own Conda environment + FastAPI microservice |
| HTTP decoupling | Agent layer calls tools only through HTTP APIs, never by directly importing third-party repos |
| Source independence | Third-party repos are managed as git submodules under `external_repos/` |

---

## 2. Architecture at a Glance

```
┌────────────────────────────────────────────────────────────┐
│  Streamlit UI  (frontend/app.py)                           │
├────────────────────────────────────────────────────────────┤
│  LangGraph Agent  (agent_core/)                            │
│  ┌─────────┐  ┌────────────┐  ┌────────┐  ┌──────────┐    │
│  │ Router  │→│ Specialist │→│ Tool   │→│ Critic   │    │
│  │ (rules) │  │  (rules)   │  │ Exec   │  │ (rules)  │    │
│  └─────────┘  └────────────┘  └────────┘  └──────────┘    │
├────────────────────────────────────────────────────────────┤
│  HTTP Tool Layer  (@tool → requests.post)                  │
├────────────────────────────────────────────────────────────┤
│  FastAPI Microservices  (microservices/*/main.py)          │
│  One service per tool, isolated port & Conda env           │
├────────────────────────────────────────────────────────────┤
│  External Repos  (external_repos/*)                        │
│  Third-party source + weights + compiled artifacts         │
└────────────────────────────────────────────────────────────┘
```

**Stack**

- Orchestration: LangGraph
- Frontend: Streamlit
- Tool interface: LangChain `@tool`
- Tool runtime: FastAPI + Conda
- Agent architecture: **Five-layer** (Capability → Workflow → Planning → Session → Runner)
- Current mode: **rule-driven** (`RuleBasedPlanner` / `ExecutionController`; architecture supports swapping to LLM mode without touching Layer 2 or below). mRNA CDS design has no critic — ranking by `-mfe + codon_count * log(CAI)` is sufficient.

---

## 3. Directory Structure

```
rna_agent_system/
├── agent_core/                 # Agent orchestration layer
│   ├── state.py                #   AgentState definition
│   ├── graph.py                #   LangGraph workflow builder
│   ├── graph_nodes.py          #   Thin LangGraph wrappers (replaced monolithic nodes.py)
│   ├── tools.py                #   @tool wrappers (HTTP → microservices)
│   ├── tool_specs.py           #   Pydantic output schemas & ToolSpec registry
│   ├── tool_registry.py        #   Minimal name→callable registry
│   ├── tool_executor.py        #   Dispatch + tracing wrapper
│   ├── tool_runtime.py         #   Execution primitives (subprocess, timeout)
│   ├── workflow_models.py      #   Serializable Candidate / TaskState / WorkflowResult
│   ├── workflow_dispatch.py    #   Task-type classifier
│   ├── sequence_utils.py       #   Shared normalization / GC / dot-bracket math
│   ├── file_manager.py         #   workspace file I/O
│   ├── session_memory.py       #   Layer 4: multi-turn session persistence
│   ├── workspace_manager.py    #   Layer 4: session-scoped directory management
│   ├── runner.py               #   Layer 5: unified AgentRunner façade
│   ├── capabilities/           #   Layer 1: atomic tool wrappers + auto-writeback
│   ├── planning/               #   Layer 3: Planner + ExecutionController + rule-based backends
│   ├── workflows/              #   Layer 2: higher-level workflow modules
│   └── workflow_tools/         #   LangChain Runnable workflow tools
├── frontend/
│   └── app.py                  # Streamlit chat UI
├── microservices/              # Microservice wrappers (one subdir per tool)
│   ├── <tool>_service/
│   │   ├── environment.yml     #   Conda env definition
│   │   ├── main.py             #   FastAPI entry point
│   │   ├── start.sh            #   Launch script
│   │   └── install_*.sh        #   (Optional) compile / patch scripts
│   └── ...
├── external_repos/             # Third-party source (git submodule)
├── workspace/                  # Runtime artifacts (sequences, structures, logs)
├── tests/                      # pytest suite
├── docs/                       # Project documentation (this directory)
├── cli/                        # Command-line workflow entry points
├── workflow_api/               # FastAPI HTTP API for workflow execution
└── requirements.txt            # Main Agent environment dependencies
```

---

## 4. Master Capability Matrix

### 4.1 Tool Master Table

| Tool name | Source | Port | Supported tasks | Core input | Core output | Status |
|---|---|---:|---|---|---|---|
| `predict_rna_secondary_structure` | ViennaRNA | 8003 | `rna_secondary_structure_viennarna` | `filepath` | `structure`, `mfe_kcal_per_mol` | available |
| `compute_sirna_duplex_binding_vienna` | ViennaRNA | 8003 | `sirna_duplex_energy` | `filepath` | `structure`, `mfe_kcal_per_mol` | available |
| `compute_aso_target_accessibility_vienna` | ViennaRNA | 8003 | `aso_accessibility_viennarna` | `filepath`, region params | `mean_unpaired_prob` | available |
| `predict_rna_local_accessibility_profile_vienna` | ViennaRNA | 8003 | — | `filepath` | per-position unpaired probs | available |
| `inverse_fold_rna_secondary_structure_vienna` | ViennaRNA | 8003 | `inverse_folding_viennarna` | `filepath` | `best_sequence` | available |
| `predict_rna_secondary_structure_with_linearfold` | LinearFold | 8015 | `rna_secondary_structure_linearfold` | `filepath` | `structure`, `mfe` | available |
| `evaluate_rna_structure_with_linearfold` | LinearFold | 8015 | — | `filepath` | energy evaluation | available |
| `predict_rna_secondary_structure_with_linearfold_zuker` | LinearFold | 8015 | — | `filepath` | subopt structures | available |
| `design_mrna_cds_with_lineardesign` | LinearDesign | 8014 | `protein_to_cds_design` | `filepath` | `generated_sequence`, `cai_score` | partial |
| `design_mrna_cds_batch_with_lineardesign` | LinearDesign | 8014 | `protein_to_cds_design` | `filepath` | batch JSON | partial |
| `design_mrna_cds_with_rnarl` | RNARL | 8008 | `protein_to_cds_design` | `filepath`, `model_type` | `generated_sequence` | partial (GPU/weights) |
| `design_mrna_cds_with_gemorna` | GEMORNA | 8004 | `protein_to_cds_design` | `filepath` | `generated_sequence` | partial (GPU/weights) |
| `analyze_cds_codon_metrics_with_codonw_slim` | codonw-slim | 8018 | `cds_codon_metrics` | `filepath` | `cai_score`, metrics JSON | partial |
| `run_blastn_similarity_search` | BLAST+ | 8019 | `blastn_similarity_search` | `filepath`, subject | `hit_count`, TSV | partial |
| `predict_putative_ires_with_iresfinder` | IRESfinder | 8013 | `ires_prediction` | `filepath` | `max_score`, TSV | partial |
| `predict_mrna_stability_with_rnastop` | RNASTOP | 8009 | `mrna_stability_prediction` | `filepath` | stability metrics | partial (GPU/weights) |
| `predict_rna_tertiary_structure_with_rhofold` | RhoFold | 8005 | `rna_tertiary_structure_prediction` | `filepath` | `pdb_filepath`, `mean_plddt` | partial (GPU/weights) |
| `design_rna_sequence_with_rhodesign` | RhoDesign | 8006 | `rna_structure_to_sequence_design` | `pdb_filepath` | `designed_sequence`, `recovery_rate` | partial (GPU/weights) |
| `design_rna_inverse_fold_with_ribodiffusion` | RiboDiffusion | 8021 | — | `pdb_filepath` | `predicted_sequence`, `recovery_rate` | partial (GPU/weights) |
| `score_rna_ligand_binding_with_rnasmol` | RNAsmol | 8007 | `rna_ligand_scoring` | `filepath`, `smiles` | `probability_positive` | partial (GPU/weights) |
| `score_rna_ligand_binding_with_gernabind` | GerNA-Bind | 8010 | `rna_ligand_scoring` | `filepath`, `smiles` | `probability`, `label` | partial (GPU/weights) |
| `run_odesign_inference` | ODesign | 8012 | `odesign_inference` | `input_json_filepath` | prediction files | partial (GPU/weights) |
| `score_crispr_off_target_with_crisot` | CRISOT | 8011 | `crispr_offtarget_scoring` | `filepath`, target seq | `crisot_score` | partial |
| `calculate_crispr_specificity_with_crisot` | CRISOT | 8011 | `crispr_specificity_csv` | `csv_filepath` | `scored_csv_filepath` | partial |
| `search_crispr_off_targets_with_crisot` | CRISOT | 8011 | `crispr_offtarget_search` | `filepath`, genome | off-target list + spec | partial |
| `optimize_sgrna_with_crisot` | CRISOT | 8011 | `crispr_sgrna_optimization` | `filepath`, genome | `best_sgrna`, `best_delta_spec` | partial |
| `design_sgrna_handle_with_crgpt` | sgrna_design | 8017 | `sgrna_handle_design` | `filepath` / seed | `best_sequence` | partial (GPU/weights) |
| `design_sirna_with_evitar` | Evitar | 8016 | `sirna_design_evitar` | `filepath`, `mode` | candidate list | partial (Linux only) |
| `compute_rna_sequence_gc_content` | RNA metrics | 8020 | — | `filepath` | `gc_content`, 5 fields | available |
| `compute_rna_sequence_u_content` | RNA metrics | 8020 | — | `filepath` | `u_fraction`, 3 fields | available |
| `compute_dot_bracket_unpaired_fraction` | RNA metrics | 8020 | — | `filepath` | `unpaired_fraction`, 3 fields | available |
| `compute_cai_for_cds_sequence` | Pure Python (Kazusa) | — | `cds_codon_metrics` | `filepath`, `species` | `cai_score`, 6 fields | available |
| `extract_rna_sequence_from_cif` | Pure Python (biopython) | — | `rna_sequence_extraction` | `cif_filepath`, optional `chain_id` | `sequence`, `chain_id`, `residue_count`, `is_rna` | available |
| `build_odesign_aptamer_input_json` | Pure Python | — | `odesign_aptamer_input` | `protein_structure_path`, `protein_chain_id`, `hotspot_residues`, `aptamer_length` | `input_json_filepath`, `design_config` | available |
| `predict_protein_structure_with_proteinx` | ProteinX (Protenix) | 8022 | `protein_structure_prediction` | `filepath` (FASTA) | `pdb_filepath`, `mean_plddt`, `model_scores` | available (needs GPU) |
| `predict_rna_protein_complex_with_proteinx` | ProteinX (Protenix) | 8022 | `rna_protein_complex_prediction` | `protein_filepath`, `rna_filepath` | `pdb_filepath`, `mean_plddt`, `ipTM`, `ranking_confidence` | available (needs GPU) |
| `analyze_rna_protein_interface` | Pure Python (biopython + freesasa) | — | `rna_protein_interface_analysis` | `complex_pdb_filepath`, `protein_chain_id`, `rna_chain_id` | `interface_contacts`, `buried_sasa`, `hydrogen_bonds`, `salt_bridges` | available |
| `identify_protein_binding_hotspots` | Pure Python (freesasa + DBSCAN) | — | `protein_hotspot_identification` | `protein_structure_path`, `chain_id` | `hotspot_residues`, `hotspot_patch_size`, `patch_center_coords` | available |
| `score_structure_alignment` | Pure Python (biopython) | — | `structure_alignment` | `reference_pdb_filepath`, `predicted_pdb_filepath` | `rmsd`, `tm_score`, `aligned_residue_count` | available |

### 4.2 Task Master Table

| Task | Supported | Entry | Tool chain | Complete | Limitations |
|---|---|---|---|---|---|
| `sirna_duplex_energy` | Yes | UI / workflow | `compute_sirna_duplex_binding_vienna` | Yes | Needs two strands |
| `sirna_design_evitar` | Partial | workflow | `design_sirna_with_evitar` | No | Linux only |
| `rna_secondary_structure_viennarna` | Yes | UI / workflow | `predict_rna_secondary_structure` | Yes | Falls back to LinearFold on failure |
| `rna_secondary_structure_linearfold` | Yes | UI / workflow | `predict_rna_secondary_structure_with_linearfold` | Yes | Depends on 8015 |
| `aso_accessibility_viennarna` | Yes | workflow | `compute_aso_target_accessibility_vienna` | Yes | Region must be valid |
| `inverse_folding_viennarna` | Yes | workflow | `inverse_fold_rna_secondary_structure_vienna` | Yes | Heuristic |
| `cds_codon_metrics` | Partial | workflow | `analyze_cds_codon_metrics_with_codonw_slim` | No | Needs 8018 env |
| `protein_to_cds_design` | Partial | workflow | `design_mrna_cds_with_*` | No | Multi-tool, Linux/GPU/weights |
| `mrna_stability_prediction` | Partial | workflow | `predict_mrna_stability_with_rnastop` | No | GPU/weights |
| `ires_prediction` | Partial | workflow | `predict_putative_ires_with_iresfinder` | No | Needs model/data |
| `blastn_similarity_search` | Partial | workflow | `run_blastn_similarity_search` | No | Needs BLAST+ and subject data |
| `rna_tertiary_structure_prediction` | Partial | workflow | `predict_rna_tertiary_structure_with_rhofold` | No | GPU/weights |
| `rna_structure_to_sequence_design` | Partial | workflow | `design_rna_sequence_with_rhodesign` | No | GPU/weights + PDB |
| `rna_ligand_scoring` | Partial | workflow | RNAsmol / GerNA-Bind | No | GPU/weights |
| `odesign_inference` | Partial | workflow | `run_odesign_inference` | No | GPU/weights/data |
| `crispr_offtarget_scoring` | Partial | workflow | `score_crispr_off_target_with_crisot` | No | Needs 8011 |
| `crispr_specificity_csv` | Partial | workflow | `calculate_crispr_specificity_with_crisot` | No | Needs 8011 |
| `crispr_offtarget_search` | Partial | workflow | `search_crispr_off_targets_with_crisot` | No | Genome + Cas-OFFinder |
| `crispr_sgrna_optimization` | Partial | workflow | `optimize_sgrna_with_crisot` | No | Can be very slow |
| `sgrna_handle_design` | Partial | workflow | `design_sgrna_handle_with_crgpt` | No | Model / torch |
| `rna_aptamer_design` | Partial | workflow | `build_odesign_aptamer_input_json` → `run_odesign_inference` → `predict_rna_protein_complex_with_proteinx` + `analyze_rna_protein_interface` | No | Requires ODesign + Protenix GPU/weights |
| `protein_structure_prediction` | Yes | workflow | `predict_protein_structure_with_proteinx` | No | Needs GPU + Protenix weights on first run |
| `protein_hotspot_identification` | Yes | workflow | `identify_protein_binding_hotspots` | Yes | Requires freesasa + scikit-learn |
| `structure_alignment` | Yes | workflow | `score_structure_alignment` | Yes | Requires biopython |

### 4.3 Removed Capabilities

| Capability | Removal reason | Original location | Current replacement |
|---|---|---|---|
| siRNA efficiency (mock) | Returned random values | `microservices/sirna_attsioff` + `predict_sirna_efficiency` | None (production implementation not yet available) |
| siRNA off-target count (mock) | Returned random values | `microservices/off_target_blast` + `check_off_target` | None (generic `run_blastn_similarity_search` can be used as a basic building block, but is not a full pipeline) |

---

## 5. Tool & Port Registry

| Port | Service directory | Tool name | Capability | Validation |
|------|-------------------|-----------|------------|------------|
| 8003 | `microservices/viennarna_fold/` | ViennaRNA | Secondary structure / cofold / RNAplfold / RNAinverse | ✅ Linux |
| 8004 | `microservices/gemorna_service/` | GEMORNA | Protein → mRNA CDS design | ✅ Linux GPU |
| 8005 | `microservices/rhofold_service/` | RhoFold | RNA tertiary structure prediction (single-seq) | ✅ Linux GPU |
| 8006 | `microservices/rhodesign_service/` | RhoDesign | Structure → sequence design | ✅ Linux GPU |
| 8007 | `microservices/rnasmol_service/` | RNAsmol | RNA–ligand scoring | ✅ Linux GPU |
| 8008 | `microservices/rnarl_service/` | RNARL | Protein → mRNA CDS design (7 species) | ✅ Linux GPU |
| 8009 | `microservices/rnastop_service/` | RNASTOP | mRNA stability / degradation prediction | ✅ Linux GPU |
| 8010 | `microservices/gernabind_service/` | GerNA-Bind | RNA–ligand scoring + binding-site | ✅ Linux GPU |
| 8011 | `microservices/crisot_service/` | CRISOT | CRISPR off-target scoring / optimization | ✅ Linux |
| 8012 | `microservices/odesign_service/` | ODesign | Biomolecule design (RNA-related) | ✅ Linux GPU |
| 8013 | `microservices/iresfinder_service/` | IRESfinder | IRES prediction (Python 3 re-implementation) | ✅ Linux |
| 8014 | `microservices/lineardesign_service/` | LinearDesign | Protein → mRNA CDS design (single / batch) | ✅ Linux |
| 8015 | `microservices/linearfold_service/` | LinearFold | RNA secondary structure prediction / constrained fold / SHAPE-guided / Zuker subopt / energy eval | ✅ Linux |
| 8016 | `microservices/evitar_service/` | Evitar | siRNA / Cas13 design (Perl CLI) | ✅ Linux |
| 8017 | `microservices/sgrna_design_service/` | CRGPT | sgRNA handle design | ✅ Linux GPU |
| 8018 | `microservices/codonw_slim_service/` | codonw-slim | CDS codon metrics (CAI / Fop / CBI / Nc) | ✅ Linux |
| 8019 | `microservices/blast_service/` | BLAST+ | blastn nucleotide similarity search | ✅ Linux |
| 8020 | `microservices/rna_sequence_metrics_service/` | RNA metrics | Sequence GC content; U content; dot-bracket unpaired fraction | ✅ Linux |
| 8021 | `microservices/ribodiffusion_service/` | RiboDiffusion | PDB tertiary structure → RNA sequence (diffusion inverse folding) | ✅ Linux GPU |
| 8022 | `microservices/proteinx_service/` | ProteinX (Protenix) | Protein structure prediction | ✅ Linux GPU |

> New tools should use ports starting from **8023**.

---

## 6. Agent Workflow Logic

### 6.1 Workflow Graph

```
User Input → Router → Specialist → Tool Execution → [Optional Critic] → End / Retry
```

### 6.2 Router (rule-based)

The router dispatches to a specialist based on keyword matching in user text:

| Target | Trigger keywords (partial list) |
|--------|--------------------------------|
| `sirna_specialist` | `sirna`, `off-target`, `duplex`, `cofold`, `evitar`, `cas13`, `rnaxs`, `predsi` |
| `crispr_specialist` | `crispr`, `cas9`, `sgrna`, `crisot`, `guide rna`, `crgpt`, `sgrna handle` |
| `mrna_specialist` | `mrna`, `design`, `protein`, `cds`, `fold`, `structure`, `gemorna`, `lineardesign`, `linearfold`, `rhofold`, `rhodesign`, `ribodiffusion`, `rnasmol`, `rnastop`, `gernabind`, `ires`, `stability`, `aso`, `plfold`, `inverse fold`, `codonw`, `blast`, `blastn`, `gc content`, `u content`, `cai`, `codon adaptation index`, `unpaired fraction`, etc. |
| Default | `mrna_specialist` |

### 6.3 Specialist Dispatch

**siRNA Specialist**

| Condition | Tool called |
|-----------|-------------|
| Evitar keywords | `design_sirna_with_evitar` |
| siRNA duplex / cofold semantics | `compute_sirna_duplex_binding_vienna` |

**CRISPR Specialist**

| Condition | Tool called |
|-----------|-------------|
| sgRNA handle / design / crgpt | `design_sgrna_handle_with_crgpt` |
| Single-pair scoring | `score_crispr_off_target_with_crisot` |
| CSV specificity | `calculate_crispr_specificity_with_crisot` |
| Genome + off-target search | `search_crispr_off_targets_with_crisot` |
| Optimize / optimization | `optimize_sgrna_with_crisot` |

**mRNA Specialist** (priority order, first match wins)

| Priority | Condition | Tool called |
|----------|-----------|-------------|
| 1 | Explicit `gernabind` | `score_rna_ligand_binding_with_gernabind` |
| 2 | RNA-ligand scoring (`rnasmol` / `smiles` / `ligand`) | `score_rna_ligand_binding_with_rnasmol` |
| 3 | IRES recognition | `predict_putative_ires_with_iresfinder` |
| 4 | ViennaRNA inverse folding | `inverse_fold_rna_secondary_structure_vienna` |
| 5 | ASO / gapmer / morpholino accessibility | `compute_aso_target_accessibility_vienna` |
| 5b | RNAplfold whole-sequence local profile | `predict_rna_local_accessibility_profile_vienna` |
| 6 | mRNA stability (`stability` / `degradation` / `rnastop`) | `predict_mrna_stability_with_rnastop` |
| 7 | Codon metrics (`codonw` / `codon usage`) | `analyze_cds_codon_metrics_with_codonw_slim` |
| 7b | GC content | `compute_rna_sequence_gc_content` |
| 7c | U content | `compute_rna_sequence_u_content` |
| 7d | Dot-bracket unpaired fraction | `compute_dot_bracket_unpaired_fraction` |
| 7e | CAI (direct Kazusa) | `compute_cai_for_cds_sequence` |
| 8 | BLAST search | `run_blastn_similarity_search` |
| 9 | RiboDiffusion inverse folding | `design_rna_inverse_fold_with_ribodiffusion` |
| 10 | Structure → sequence (`rhodesign` + `.pdb`) | `design_rna_sequence_with_rhodesign` |
| 11 | ODesign inference | `run_odesign_inference` |
| 12 | LinearDesign CDS (single) | `design_mrna_cds_with_lineardesign` |
| 12b | LinearDesign CDS (batch) | `design_mrna_cds_batch_with_lineardesign` |
| 13 | RNARL CDS design | `design_mrna_cds_with_rnarl` |
| 14 | GEMORNA CDS design | `design_mrna_cds_with_gemorna` |
| 15 | ODesign aptamer input JSON | `build_odesign_aptamer_input_json` |
| 16 | ODesign inference | `run_odesign_inference` |
| 17 | Extract RNA from CIF | `extract_rna_sequence_from_cif` |
| 18 | Structure alignment / RMSD+TM-score | `score_structure_alignment` |
| 19 | Protein hotspot identification | `identify_protein_binding_hotspots` |
| 20 | Protein structure prediction | `predict_protein_structure_with_proteinx` |
| 21 | Default structure prediction | `analyze_cds_codon_metrics_with_codonw_slim` → `predict_rna_secondary_structure` or `predict_rna_secondary_structure_with_linearfold` |
| — | Text contains `rhofold` / `3d` / `tertiary` | Additional `predict_rna_tertiary_structure_with_rhofold` |

After CDS design (GEMORNA / RNARL / LinearDesign), if the user request implies structure prediction, `tool_execution_node` automatically chains a folding tool.

### 6.4 Critic (rule-based evaluation, currently unused for mRNA CDS)

> mRNA CDS design intentionally has **no critic**. Re-running the same design tools on the same protein sequence does not yield better candidates; ranking by the combined score is sufficient.

| Scenario | Rule | Behavior |
|----------|------|----------|
| mRNA CDS design | — | **No critic** — ranking only |
| siRNA | `off_target_genes > 0` | reject → retry |
| mRNA structure prediction | `mfe > -20.0` | reject → retry |
| RNAplfold whole-sequence profile | — | pass (MFE critic is not applied to avoid false rejects on "local structure" queries) |
| RhoDesign | Microservice returns successfully | pass |
| Others | — | pass |
| Retry cap | `max_retries = 3` | Force pass |

> **Note**: short sequences often have MFE in the -2 ~ -15 kcal/mol range, which triggers repeated rejections until retries are exhausted. Future work should adjust the threshold or normalize by sequence length.

---

## 7. Quick Start

### 7.1 Start a microservice (generic pattern)

```bash
cd rna_agent_system/microservices/<tool>_service
conda env create -f environment.yml      # first time only
conda activate <tool>_service_env
# If there is an install_*.sh, run it first
bash start.sh
```

### 7.2 Services requiring compilation or extra install scripts

| Service | Extra step |
|---------|------------|
| LinearDesign | `cd external_repos/LinearDesign && make` |
| LinearFold | `cd external_repos/LinearFold && make` |
| codonw-slim | `bash microservices/codonw_slim_service/install_codonw_slim.sh` |
| RiboDiffusion | `conda activate ribodiffusion_service_env && bash install_pyg_torch_extensions.sh` |

### 7.3 Launch the Streamlit frontend

```bash
# From the repository root
streamlit run rna_agent_system/frontend/app.py --server.fileWatcherType none

# Remote SSH access
streamlit run rna_agent_system/frontend/app.py \
  --server.fileWatcherType none \
  --server.address 0.0.0.0 \
  --server.port 8501
```

### 7.4 Run tests

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x --ignore=tests/integration -m "not integration"
```

### 7.5 Submodule management

```bash
# Fresh clone
git clone --recurse-submodules <repo-url>

# Existing clone
git pull && git submodule update --init --recursive
```

Current submodules: GEMORNA, GerNA-Bind, RNARL, RhoFold, RhoDesign, RiboDiffusion, RNAsmol, RNASTOP, CRISOT, ODesign, IRESfinder, LinearDesign, LinearFold, Evitar, ViennaRNA, sgrna_design, codonw-slim.

---

## 8. Known Limitations & Roadmap

### Current limitations

| ID | Limitation | Impact |
|----|------------|--------|
| L1 | Router / Specialist are rule-based (`RuleBasedPlanner`) | Limited complex NL understanding; LLM backend reserved for future (Layer 3 is backend-pluggable) |
| L2 | Critic MFE threshold `-20.0` (when used) is unreasonable for short sequences | Short sequences are repeatedly rejected until retries are exhausted |
| L3 | siRNA efficiency / off-target capabilities have no production implementation | Historical mocks (ports 8001/8002) were removed; only Evitar / Vienna duplex remain |
| L4 | RhoFold is single-sequence mode only | MSA database not connected |
| L5 | RNASTOP only supports stability prediction | Beam / MCTS optimization not connected |
| L6 | ODesign natural-language coverage is limited | Complex tasks still need explicit JSON |
| L7 | Frontend is a minimal debug UI | Not a product-grade interface |

### Roadmap

1. Keep the rule-based mode stable while all tool chains are verified end-to-end.
2. Replace mock services with real implementations where needed.
3. After the tool ecosystem stabilizes, restore configurable LLM mode.
4. Introduce finer specialists, optional critics for safety-critical workflows, and multi-tool chaining planning.

---

*For architecture details, see `ARCHITECTURE.md`. For tool & task reference, see `TOOLS_AND_TASKS.md`. For development, deployment, and change logs, see `DEVELOPMENT.md`.*
