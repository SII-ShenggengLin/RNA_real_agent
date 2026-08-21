# RNA Design Multi-Agent System

> **Project root**: `rna_agent_system/`  
> **Readers**: human developers / AI agents  
> **Last updated**: 2026-08-10

---

## 1. What is this?

A tool-first, calibrated multi-agent system for RNA bioinformatics design and analysis (paper positioning: the LLM orchestrates, reviews and reports but never writes sequences — every molecule traces to a deterministic generator call).

- **Input**: structured workflow parameters via TUI form or JSON file; RNA/protein sequences and structure files are provided as parameter values
- **Output**: designed sequences, predictions, scores, and structured reports
- **Mechanism**: The user explicitly selects a workflow and fills a structured form; `AgentRunner` executes the workflow directly. Routing is explicit-only — LLM calls exist only at the advisory/review points (quality review, multi-node synthesis + ClaimGate claim checking).

**Core principles**

| Principle | Description |
|-----------|-------------|
| Sequences never go in prompts | Long sequences travel via `workspace/` file paths, never inside chat context |
| Environment isolation | Every tool has its own Conda environment + FastAPI microservice |
| HTTP decoupling | Agent layer calls tools only through HTTP APIs, never by direct imports |
| Source independence | 20 vendored external repos under `external_repos/` (17 registered git submodules; 3 of them pinned to patched forks — see DEPLOYMENT §1.4) |

---

## 2. Architecture at a Glance

```
┌──────────────────────────────────────────────┐
│  Layer 6  Entry Points                       │
│           AgentRunner / FastAPI / TUI CLI    │
├──────────────────────────────────────────────┤
│  Layer 5  Session & Workspace                │
│           Multi-turn context, workspace      │
├──────────────────────────────────────────────┤
│  Layer 4  Planning & Multi-Agent Execution   │
│           PipelineAgent / SpecialistAgent    │
│           QualityAgent / SynthesisAgent      │
│           (+ calibrated/ CapGate stack)      │
├──────────────────────────────────────────────┤
│  Layer 3  Service Orchestration              │
│           Health check & auto-start          │
├──────────────────────────────────────────────┤
│  Layer 2  Domain Workflows                   │
│           mRNA / siRNA / CRISPR / ...        │
├──────────────────────────────────────────────┤
│  Layer 1  Atomic Capabilities                │
│           Single-tool invocation + writeback │
├──────────────────────────────────────────────┤
│  Layer 0  Tool Layer                         │
│           Microservices (FastAPI + Conda)    │
└──────────────────────────────────────────────┘
```

For full architecture details, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 3. Directory Structure

```
rna_agent_system/
├── agent_core/                 # Agent orchestration (Layers 1–6 internals)
│   ├── capabilities/           #   Layer 1: atomic tool wrappers
│   ├── workflows/              #   Layer 2: domain workflow implementations
│   ├── services/               #   Layer 3: microservice health/orchestration
│   ├── agents/                 #   Layer 4: multi-agent execution
│   │                           #     PipelineAgent, SpecialistAgent,
│   │                           #     QualityAgent, SynthesisAgent
│   ├── pipeline/               #   Layer 4: PipelinePlan/Node/Edge models
│   ├── calibrated/             #   Layer 4: CapGate strategy stack
│   │                           #     (SelfModel, DecisionGate, ClaimGate)
│   ├── tools.py                #   Layer 0: @tool wrappers (HTTP → microservices)
│   ├── tool_specs.py           #   Pydantic output schemas & ToolSpec registry
│   ├── llm_config.py           #   LLM client factory (get_llm_for_provider)
│   ├── runner.py               #   Layer 6: AgentRunner façade
│   ├── state.py                #   AgentState definition
│   └── ...
├── microservices/              # FastAPI microservices (one per tool)
├── external_repos/             # Third-party source (20 vendored repos, 17 git submodules)
├── workspace/                  # Runtime artifacts (sequences, structures, logs)
├── tests/                      # pytest suite
├── cli/                        # Command-line entry points
│   ├── form_chat.py            #   Interactive TUI form CLI (resource check → workflow select → service start → form)
│   ├── resource_checker.py     #   GPU / RAM / CPU pre-flight checks
│   └── service_orchestrator.py #   Workflow-to-microservice mapping & health polling
├── workflow_api/               # FastAPI HTTP API entry point (`app.py` only)
└── docs/                       # Documentation (this directory)
```

---

## 4. Quick Start

> **Vendored repos note (read before first run).** Clone with `--recurse-submodules`. Three submodules (LinearDesign, RhoDesign, RhoFold) are pinned to public forks carrying one local patch each on top of upstream — the clone gets the patched code automatically, but LinearDesign additionally **requires compiling** (`make` + wrapper restore, DEPLOYMENT §3.1), and several services need manually placed model weights (DEPLOYMENT §3.2). Full patch table and rationale: [`DEPLOYMENT.md` §1.4](DEPLOYMENT.md).

### 4.1 Install main agent environment

```bash
cd rna_agent_system
pip install -r requirements.txt
```

### 4.2 Interactive TUI CLI (recommended)

```bash
PYTHONPATH="$(pwd):$PYTHONPATH" python cli/form_chat.py
```

Flow:
1. System resource check (GPU ≥ 24 GB, free RAM ≥ 16 GB)
2. Pick 1 or more workflows (e.g. `1,3,8`)
3. Required microservices are started automatically
4. Each turn, pick the active workflow and fill the structured TUI form
5. Basic parameters are shown by default; advanced tool overrides are folded

### 4.3 Non-interactive single shot

Create a JSON file with the workflow parameters and run:

```bash
PYTHONPATH="$(pwd):$PYTHONPATH" python cli/form_chat.py \
  --workflow rna_small_molecule_interaction \
  --params-file params.json
```

Example `params.json`:

```json
{
  "rna_sequence": "AUGCAUGCAUGC",
  "smiles": "CCO"
}
```

### 4.4 Run the test suite

```bash
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x
```

> For full environment setup, microservice startup, compilation steps, submodule management, and per-service curl examples, see [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## 5. Capability Overview

### 5.1 Supported Domains

| Domain | Workflows | Status |
|--------|-----------|--------|
| **mRNA design** | CDS design, full-length mRNA design, sequence scoring | ✅ Available |
| **RNA structure** | 2° structure prediction (ViennaRNA / LinearFold), 2°→sequence design, 3° structure prediction, 3°→sequence design | ✅ Available |
| **siRNA / ASO** | siRNA design (Evitar), duplex energy, ASO target screening | ✅ Available |
| **CRISPR / sgRNA** | sgRNA handle design (CRGPT), CRISOT off-target scoring / optimization | ✅ Available |
| **RNA–ligand** | RNAsmol + GerNA-Bind scoring | ✅ Available |
| **RNA–protein** | Aptamer design (ODesign + ProteinX; opt-in GenNav navigation mode), complex scoring (EGARPS), interface analysis | ✅ Available |
| **IRES / stability** | IRES prediction, mRNA stability (RNASTOP) | ✅ Available |
| **Homology** | BLASTn similarity search | ✅ Available |

### 5.2 Tool & Port Registry (summary)

| Port | Service | Domain |
|------|---------|--------|
| 8003 | ViennaRNA | Secondary structure / cofold / accessibility / inverse folding |
| 8004 | GEMORNA | CDS + UTR design |
| 8005 | RhoFold | Tertiary structure prediction |
| 8006 | RhoDesign | Structure → sequence design |
| 8007 | RNAsmol | RNA–ligand scoring |
| 8008 | RNARL | CDS design (7 species) |
| 8009 | RNASTOP | mRNA stability |
| 8010 | GerNA-Bind | RNA–ligand scoring |
| 8011 | CRISOT | CRISPR off-target / specificity / optimization |
| 8012 | ODesign | Biomolecule design |
| 8013 | IRESfinder | IRES prediction |
| 8014 | LinearDesign | CDS design |
| 8015 | LinearFold | Secondary structure (beam search) |
| 8016 | Evitar | siRNA design |
| 8017 | CRGPT | sgRNA handle design |
| 8019 | BLAST+ | Nucleotide similarity |
| 8020 | RNA metrics | GC / U content / unpaired fraction |
| 8021 | RiboDiffusion | 3D → sequence (diffusion) |
| 8022 | ProteinX | Protein structure + RNA-protein complex |
| 8023 | EGARPS | RNA-protein complex scoring |
| 8024 | Bowtie2 | Short-sequence alignment |

> New tools should use ports starting from **8025**.

For per-tool specs and deployment notes, see [`TOOLS.md`](TOOLS.md).  
For workflow deep-dives, see [`WORKFLOWS.md`](WORKFLOWS.md).

---

## 6. Known Limitations

| ID | Limitation | Impact |
|----|------------|--------|
| L1 | LLM advisory calls (quality review / synthesis) default to DeepSeek API | Those two touches are skipped/fail-safe without a key; execution itself is fully deterministic |
| L2 | Some GPU-weighted tools need manual setup | Not all environments can run every tool |
| L3 | RhoFold is single-sequence mode only | MSA database not connected |
| L4 | RNASTOP only supports stability prediction | Beam / MCTS optimization not connected |
| L5 | CLI primary entry | No web UI |

---

## 7. Documentation Index

| Document | Purpose |
|----------|---------|
| [`README.md`](README.md) | This file — project overview and quick start |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Seven-layer architecture, core module APIs, design principles |
| [`WORKFLOWS.md`](WORKFLOWS.md) | All domain workflows: pipelines, scoring formulas, critic design |
| [`MANUSCRIPT.md`](MANUSCRIPT.md) | Experiment manual: benchmark/anchor assets, pilot-first protocol, data availability |
| [`TOOLS.md`](TOOLS.md) | Per-tool specs, port registry, microservice deployment notes |
| [`INTERFACE_LOCKS.md`](INTERFACE_LOCKS.md) | Interface Lock Policy, canonical references, sync checklists |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Environment setup, testing recipes, curl examples |
| [`CHANGELOG.md`](CHANGELOG.md) | Change logs for locked interfaces and major workflows |
| [`DECISIONS.md`](DECISIONS.md) | Decisions, concluded directions and do-not-repeat register |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Coding standards, new-tool procedure, commit conventions |
