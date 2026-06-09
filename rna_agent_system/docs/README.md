# RNA Design Multi-Agent System

> **Project root**: `rna_agent_system/`  
> **Readers**: human developers / AI agents  
> **Last updated**: 2026-06-01

---

## 1. What is this?

An LLM-driven agent system for RNA bioinformatics design and analysis.

- **Input**: natural-language requests, RNA/protein sequences, structure files
- **Output**: designed sequences, predictions, scores, and structured reports
- **Mechanism**: DeepSeek-powered planner (Layer 3) orchestrates domain workflows (Layer 2) that call isolated microservices (Layer 0)

**Core principles**

| Principle | Description |
|-----------|-------------|
| Sequences never go in prompts | Long sequences travel via `workspace/` file paths, never inside chat context |
| Environment isolation | Every tool has its own Conda environment + FastAPI microservice |
| HTTP decoupling | Agent layer calls tools only through HTTP APIs, never by direct imports |
| Source independence | Third-party repos are managed as git submodules under `external_repos/` |

---

## 2. Architecture at a Glance

```
┌──────────────────────────────────────────────┐
│  Layer 5  Presentation                       │
│           FastAPI / CLI                      │
├──────────────────────────────────────────────┤
│  Layer 4  Session & Memory                   │
│           Multi-turn context, workspace      │
├──────────────────────────────────────────────┤
│  Layer 3  Planning & Control                 │
│           LLMPlanner → ExecutionController   │
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
├── agent_core/                 # Agent orchestration (Layers 1–5)
│   ├── capabilities/           #   Layer 1: atomic tool wrappers
│   ├── planning/               #   Layer 3: LLMPlanner + ExecutionController
│   ├── workflows/              #   Layer 2: domain workflow implementations
│   ├── workflow_tools/         #   LangChain Runnable workflow tools
│   ├── tools.py                #   Layer 0: @tool wrappers (HTTP → microservices)
│   ├── tool_specs.py           #   Pydantic output schemas & ToolSpec registry
│   ├── runner.py               #   Layer 5: AgentRunner façade
│   ├── state.py                #   AgentState definition
│   └── ...
├── microservices/              # FastAPI microservices (one per tool)
├── external_repos/             # Third-party source (git submodules)
├── workspace/                  # Runtime artifacts (sequences, structures, logs)
├── tests/                      # pytest suite
├── cli/                        # Command-line entry points
├── workflow_api/               # FastAPI HTTP API for workflow execution
└── docs/                       # Documentation (this directory)
```

---

## 4. Quick Start

```bash
# 1. Install main agent environment
cd rna_agent_system
pip install -r requirements.txt

# 2. Run the test suite
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x --ignore=tests/integration -m "not integration"
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
| **RNA–protein** | Aptamer design (ODesign + ProteinX), complex scoring (EGARPS), interface analysis | ✅ Available |
| **IRES / stability** | IRES prediction, mRNA stability (RNASTOP) | ✅ Available |
| **Homology** | BLASTn similarity search | ✅ Available |

### 5.2 Tool & Port Registry (summary)

| Port | Service | Domain |
|------|---------|--------|
| 8003 | ViennaRNA | Secondary structure / cofold / accessibility / inverse folding |
| 8004 | GEMORNA | CDS design |
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
| 8018 | codonw-slim | Codon metrics |
| 8019 | BLAST+ | Nucleotide similarity |
| 8020 | RNA metrics | GC / U content / unpaired fraction |
| 8021 | RiboDiffusion | 3D → sequence (diffusion) |
| 8022 | ProteinX | Protein structure + RNA-protein complex |
| 8023 | EGARPS | RNA-protein complex scoring |

> New tools should use ports starting from **8024**.

For per-tool specs and deployment notes, see [`TOOLS.md`](TOOLS.md).  
For workflow deep-dives, see [`WORKFLOWS.md`](WORKFLOWS.md).

---

## 6. Known Limitations

| ID | Limitation | Impact |
|----|------------|--------|
| L1 | Planner requires DeepSeek API | Planning fails if API is unavailable |
| L2 | Some GPU-weighted tools need manual setup | Not all environments can run every tool |
| L3 | RhoFold is single-sequence mode only | MSA database not connected |
| L4 | RNASTOP only supports stability prediction | Beam / MCTS optimization not connected |
| L5 | CLI is the primary interface | No web UI shipped |

---

## 7. Documentation Index

| Document | Purpose |
|----------|---------|
| [`README.md`](README.md) | This file — project overview and quick start |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Five-layer architecture, core module APIs, design principles |
| [`WORKFLOWS.md`](WORKFLOWS.md) | All domain workflows: pipelines, scoring formulas, critic design |
| [`TOOLS.md`](TOOLS.md) | Per-tool specs, port registry, microservice deployment notes |
| [`BMC_FRAMEWORK.md`](BMC_FRAMEWORK.md) | Bounded Multi-Module Coordination: Type-I/Type-II motivation and strategy |
| [`INTERFACE_LOCKS.md`](INTERFACE_LOCKS.md) | Interface Lock Policy, canonical references, sync checklists |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Environment setup, testing recipes, curl examples |
| [`CHANGELOG.md`](CHANGELOG.md) | Change logs for locked interfaces and major workflows |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Coding standards, new-tool procedure, commit conventions |
