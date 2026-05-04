# Development, Deployment & Change Logs

> **Scope**: environment setup, deployment procedures, testing recipes, coding standards, the new-tool standard procedure, and locked interface change logs.

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Deployment Guide](#2-deployment-guide)
3. [Testing](#3-testing)
4. [Coding Standards](#4-coding-standards)
5. [New Tool Standard Procedure](#5-new-tool-standard-procedure)
6. [Change Log: GC Content Interface v0.1.0](#6-change-log-gc-content-interface-v010)
7. [Change Log: Dot-Bracket Unpaired Fraction v0.1.0](#7-change-log-dot-bracket-unpaired-fraction-v010)
8. [Change Log: RNA Sequence U Content v0.1.0](#8-change-log-rna-sequence-u-content-v010)
9. [Change Log: CAI for CDS v0.1.0](#9-change-log-cai-for-cds-v010)
10. [Change Log: LinearDesign Interface v0.2.0](#10-change-log-lineardesign-interface-v020)
11. [Architecture Audit Summary](#11-architecture-audit-summary)
12. [Enhancement Proposals](#12-enhancement-proposals)

---

## 1. Environment Setup

### 1.1 Development machine vs. runtime machine

| Environment | Purpose |
|-------------|---------|
| macOS | Code editing, Git commits |
| Linux server | `git pull`, Conda env creation, microservice startup, Agent execution |

**Linux server path**: `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`

### 1.2 Main Agent environment

```bash
cd rna_agent_system
pip install -r requirements.txt
```

### 1.3 Per-tool Conda environments

Each microservice has its own `environment.yml`. Generic creation pattern:

```bash
cd rna_agent_system/microservices/<tool>_service
conda env create -f environment.yml
conda activate <tool>_service_env
# Optional: run install_*.sh if present
bash start.sh
```

### 1.4 Submodule initialization

```bash
# Fresh clone
git clone --recurse-submodules <repo-url>

# Existing clone
git pull && git submodule update --init --recursive
```

Current submodules: GEMORNA, GerNA-Bind, RNARL, RhoFold, RhoDesign, RiboDiffusion, RNAsmol, RNASTOP, CRISOT, ODesign, IRESfinder, LinearDesign, LinearFold, Evitar, ViennaRNA, sgrna_design, codonw-slim.

---

## 2. Deployment Guide

### 2.1 Services requiring compilation or extra scripts

| Service | Extra step |
|---------|------------|
| LinearDesign | `cd external_repos/LinearDesign && make` |
| LinearFold | `cd external_repos/LinearFold && make` |
| codonw-slim | `bash microservices/codonw_slim_service/install_codonw_slim.sh` |
| RiboDiffusion | `conda activate ribodiffusion_service_env && bash install_pyg_torch_extensions.sh` |

### 2.2 Large file / weight management

The following files are **not** tracked in the main Git repository and must be prepared separately on the server:

| Tool | Weight paths |
|------|--------------|
| GEMORNA | `external_repos/GEMORNA/checkpoints/*.pt` |
| RNARL | `external_repos/RNARL/checkpoints/*.pt` + `esm2_model_t33_650M_UR50D/` |
| RhoFold | `external_repos/RhoFold/pretrained/RhoFold_pretrained.pt` |
| RhoDesign | `external_repos/RhoDesign/checkpoint/*.pth` |
| RNAsmol | `external_repos/RNAsmol/saved_model/*.pt` |
| RNASTOP | `external_repos/RNASTOP/models/*` + `RNA-FM_pretrained.pth` + `DNABERT6/` |
| GerNA-Bind | `external_repos/GerNA-Bind/Model/*.pth` |
| ODesign | `external_repos/ODesign/ckpt/*.pt` + `ckpt/*.ckpt` + `data/components.*` |
| RiboDiffusion | `external_repos/RiboDiffusion/ckpts/exp_inf.pth` (or `exp_inf_large.pth`) |

### 2.3 Starting the Streamlit frontend

```bash
# Local
streamlit run rna_agent_system/frontend/app.py --server.fileWatcherType none

# Remote SSH
streamlit run rna_agent_system/frontend/app.py \
  --server.fileWatcherType none \
  --server.address 0.0.0.0 \
  --server.port 8501
```

---

## 3. Testing

### 3.1 Three-layer validation

Always validate in this order:

1. **Microservice layer**: `curl /health` → `curl` business endpoint
2. **Agent tool layer**: `tools.py` wrapper functions
3. **Frontend integration**: Streamlit natural-language input

### 3.2 Agent-core test suite

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x --ignore=tests/integration -m "not integration"
```

### 3.3 Key test files

| Test file | Coverage |
|---|---|
| `test_compute_rna_sequence_gc_content.py` | GC content tool |
| `test_compute_dot_bracket_unpaired_fraction.py` | Dot-bracket tool |
| `test_rna_gc_content_workflow.py` | GC workflow tool |
| `test_rna_unified_http.py` | Unified HTTP handler |
| `test_workflow_dispatch.py` | Task type classification |
| `test_workflow_models.py` | Pydantic workflow models |
| `test_tool_registry_executor.py` | Registry + executor |
| `test_tool_runtime.py` | Subprocess / Python runtime |
| `test_tool_specs_output_models.py` | ToolSpec schemas |
| `test_viennarna_wrapper_output.py` | ViennaRNA output |
| `test_workflow_baseline_eval.py` | Baseline eval |
| `test_mrna_workflow.py` | mRNA workflow |
| `test_mrna_workflow_api.py` | HTTP API |
| `test_cli_mrna_entry.py` | CLI entry |
| `test_rhodesign_interface.py` / `test_rhodesign_full.py` | RhoDesign |
| `test_workflow_observability.py` | Observability / tracing |
| `test_integration_registry_smoke.py` | Integration smoke tests |
| `conftest.py` | Shared pytest fixtures |

### 3.4 Microservice curl examples

```bash
# ViennaRNA fold
curl -sS -X POST http://127.0.0.1:8003/fold \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"GGGGAAAACCCC"}' | python3 -m json.tool

# ViennaRNA RNAplfold whole-sequence profile
curl -sS -X POST http://127.0.0.1:8003/plfold-profiles \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"GGGGAAAACCCCUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC","winsize":40,"span":30,"unpaired_ulength":15,"temp_c":37}' \
  | python3 -m json.tool

# GEMORNA CDS design
curl -sS -X POST http://127.0.0.1:8004/generate/cds \
  -H 'Content-Type: application/json' \
  -d '{"protein_sequence":"MNDTEAI"}' | python3 -m json.tool

# RhoFold tertiary structure
curl -sS -X POST http://127.0.0.1:8005/predict \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"AUGGCUACGUAGCUAGCUAGCUAGCUGA","single_seq_pred":true,"relax_steps":0}' | python3 -m json.tool

# CRISOT score
curl -sS -X POST http://127.0.0.1:8011/score \
  -H 'Content-Type: application/json' \
  -d '{"sgrna":"GAGTCCGAGCAGAAGAAGAANGG","target_sequence":"GAGTCCGAGGAGAAGACGAAGGG"}' | python3 -m json.tool

# codonw-slim
curl -sS -X POST http://127.0.0.1:8018/analyze/cds \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"ATGAATATGCTCATTGTCGGTAGAGTTGTTGCTAGTGTTGGGGGAAGCGGACTTCAAACG"}' | python3 -m json.tool

# RNA sequence metrics (GC)
curl -sS -X POST http://127.0.0.1:8020/gc-content \
  -H 'Content-Type: application/json' \
  -d '{"sequence_filepath":"rna_agent_system/workspace/blast_test_query.fa"}' | python3 -m json.tool

# RNA sequence metrics (unpaired fraction)
printf '%s\n' '(((....)))' > /tmp/rna_ss_example.txt
curl -sS -X POST http://127.0.0.1:8020/unpaired-fraction \
  -H 'Content-Type: application/json' \
  -d '{"structure_filepath":"/tmp/rna_ss_example.txt"}' | python3 -m json.tool

# BLAST
curl -sS -X POST http://127.0.0.1:8019/blastn \
  -H 'Content-Type: application/json' \
  -d '{"query_filepath":"rna_agent_system/workspace/blast_test_query.fa","subject_fasta_path":"rna_agent_system/workspace/blast_test_subject.fa","task":"blastn-short","evalue":10}' | python3 -m json.tool

# RiboDiffusion
curl -sS http://127.0.0.1:8021/health | python3 -m json.tool
curl -sS -X POST http://127.0.0.1:8021/design/from-pdb \
  -H 'Content-Type: application/json' \
  -d '{"pdb_path":"/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/external_repos/RiboDiffusion/example/R1107.pdb","n_samples":1,"sampling_steps":50}' | python3 -m json.tool
```

### 3.5 Streamlit natural-language test cases

| Test purpose | Input example |
|--------------|---------------|
| Secondary structure (ViennaRNA) | `请预测这条 RNA 的二级结构 fold：AUGCUAACGUAGCUAUGCUAUGCUAACGUAGCUAUGCUA` |
| siRNA duplex energy | `ViennaRNA duplex rnacofold，sense=GGCAUGCAUGC antisense=GCAUGCAUGCC` |
| ASO accessibility | `ASO accessibility plfold 可及性，region=10-50，靶标 mRNA：AUGCAUGCAUGC...` (≥50 nt) |
| RNAplfold whole-sequence profile | `RNAplfold 局部可及性曲线 lunp，序列 AUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC` or `local structure RNAplfold profile` + long sequence |
| Inverse folding | `inverse fold 逆折叠 rnainverse，structure=((((....))))，repeats=5` |
| LinearFold | `fold linearfold 二级结构 AUGGCUACGUAGCUAGCUAGCUAGCUGA beam_size=20` |
| Codon metrics | `codonw-slim 分析 CDS 密码子 CAI` + CDS sequence |
| GC content | `gc content 计算 GC 含量` + RNA sequence or `workspace/*.fa` path |
| Unpaired fraction | `unpaired fraction 未配对比例 structure=(((....))))` or `workspace/*.ss` dot-bracket file |
| BLAST search | `blastn 比对 subject_fasta=workspace/test.fa 序列 ATGCATGCATGC` |
| RiboDiffusion inverse folding | `ribodiffusion 扩散逆折叠 PDB=workspace/my.pdb n_samples=3 checkpoint_name=exp_inf_large` (requires 8021; optional default keyword `ribodiffusion 三级结构逆折叠`) |

---

## 4. Coding Standards

### 4.1 Commit conventions

- **Do not use `git add .`**.
- Recommended workflow:
  ```bash
  git status --short
  git submodule status
  git add <specific_file>
  git commit -m "meaningful message"
  git push origin main
  ```

### 4.2 Do not commit

- `__pycache__/` / `*.pyc`
- `.DS_Store`
- `workspace/` runtime outputs
- Large weight files (`*.pt` / `*.pth`)
- `.env` (contains API keys)

### 4.3 Interface Lock annotations

When locking a new tool interface, add a comment block like this in **all** affected files:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# <Tool name> INTERFACE LOCK (vX.Y.Z) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
# Synchronized files (must all be updated together):
#   - microservices/<tool>_service/main.py
#   - agent_core/tools.py
#   - agent_core/tool_specs.py
#   - agent_core/state.py
#   - agent_core/capabilities/writebacks.py
#   - frontend/app.py
#   - rna_agent_system/docs/DEVELOPMENT.md
# ═══════════════════════════════════════════════════════════════════════════════
```

---

## 5. New Tool Standard Procedure

```
1. Clone upstream repo into external_repos/ (git submodule add)
2. Create microservices/<tool>_service/
   ├── environment.yml
   ├── main.py         (FastAPI: GET /health + POST /...)
   ├── start.sh
   └── install_*.sh    (optional)
3. Add @tool wrapper in agent_core/tools.py
4. Add routing logic in agent_core/planning/rule_based/parsers/common.py (specialist + parsing)
5. Add a writeback entry in agent_core/capabilities/writebacks.py (auto state writeback)
6. Add state fields in agent_core/state.py (if needed)
7. Add node/edge in agent_core/graph.py (if new specialist needed)
8. Test order: raw command → microservice endpoint → Agent invocation → frontend
```

---

## 6. Change Log: GC Content Interface v0.1.0

> **Status**: LOCKED — Any future modification must synchronize all files listed below and re-run the full test suite.  
> **Locked on**: 2026-04-25

### What is locked

- **Input schema** (`RnaGcContentInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`RnaGcContentOutput`): `input_filepath`, `resolved_filepath`, `sequence_length`, `g_count`, `c_count`, `gc_count`, `gc_content`, `model`
- **ToolSpec identity**: `compute_rna_sequence_gc_content`
- **Workflow tool name**: `workflow_rna_gc_content`
- **Microservice endpoint**: `POST /gc-content` on port `8020`
- **State fields**: `sequence_gc_content`, `sequence_gc_length`, `sequence_gc_count`, `sequence_g_count`, `sequence_c_count`

### Architecture decisions

1. **LangChain tool is the single source of truth for HTTP** — `run_rna_gc_content_workflow()` delegates to `compute_rna_sequence_gc_content.invoke()`. HTTP logic lives in one place: `agent_core/tools.py`.
2. **`agent_core/sequence_utils.py` deduplicates normalization** — Three independent implementations previously existed (microservice, local fallback scorer, test stub). The agent-core fallback and test stub now import from `sequence_utils.py`.
3. **`timeout_seconds` added to input model** — Previously hard-coded to 120 s; now customizable by agent LLM and downstream workflows.

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- [ ] `microservices/rna_sequence_metrics_service/main.py`
- [ ] `agent_core/tools.py`
- [ ] `agent_core/tool_specs.py`
- [ ] `agent_core/state.py`
- [ ] `agent_core/capabilities/writebacks.py`
- [ ] `agent_core/workflow_tools/rna_gc_content_workflow.py`
- [ ] `agent_core/workflows/mrna_workflow.py`
- [ ] `agent_core/workflows/mrna_scoring.py`
- [ ] `agent_core/workflow_baseline_eval.py`
- [ ] `agent_core/sequence_utils.py`
- [ ] `tests/test_rna_gc_content_workflow.py`
- [ ] `tests/test_compute_rna_sequence_gc_content.py`

### Tests that must pass

```bash
pytest tests/test_compute_rna_sequence_gc_content.py tests/test_rna_gc_content_workflow.py -v
pytest tests/test_mrna_workflow.py tests/test_workflow_observability.py -v
pytest tests/test_integration_registry_smoke.py -v
```

### Notes for future maintainers

- Do **not** revert `workflow_tools/rna_gc_content_workflow.py` to direct `requests.post`. That re-creates duplicate HTTP logic.
- Do **not** remove `agent_core/sequence_utils.py` and inline the math back into `mrna_scoring.py` or `workflow_baseline_eval.py`. That re-creates 3-way duplication.
- If you change normalization rules in the microservice, you **must** update `sequence_utils.py` as well, or local fallback scores and stub test results will diverge.

---

## 7. Change Log: Dot-Bracket Unpaired Fraction v0.1.0

> **Status**: LOCKED — Any future modification must synchronize all files listed below and re-run the full test suite.  
> **Locked on**: 2026-04-25

### What is locked

- **Input schema** (`DotBracketUnpairedFractionInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`DotBracketUnpairedFractionOutput`): `input_filepath`, `resolved_filepath`, `structure_length`, `dot_count`, `unpaired_fraction`, `model`
- **ToolSpec identity**: `compute_dot_bracket_unpaired_fraction`
- **Microservice endpoint**: `POST /unpaired-fraction` on port `8020`
- **State fields**: `dot_bracket_unpaired_fraction`, `dot_bracket_structure_length`, `dot_bracket_dot_count`

### Architecture decisions

1. **LangChain tool is the single source of truth for HTTP** — `agent_core/tools.py::compute_dot_bracket_unpaired_fraction` is the only place that calls `requests.post` to port 8020 `/unpaired-fraction`.
2. **`agent_core/sequence_utils.py` provides shared parsing/validation** — `extract_dot_bracket()`, `validate_dot_bracket()`, and `compute_dot_bracket_unpaired_fraction()` are used by both local stubs and the microservice.
3. **Complete state tracking** — 3 fields tracked, not just the scalar fraction.

### Before editing anything dot-bracket-related

Read `agent_core/sequence_utils.py` and `microservices/rna_sequence_metrics_service/main.py` first.

---

---

## 8. Change Log: RNA Sequence U Content v0.1.0

> **Status**: LOCKED — Any future modification must synchronize all files listed below and re-run the full test suite.  
> **Locked on**: 2026-04-28

### What is locked

- **Input schema** (`RnaUContentInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`RnaUContentOutput`): `input_filepath`, `resolved_filepath`, `sequence_length`, `u_count`, `u_fraction`, `model`
- **ToolSpec identity**: `compute_rna_sequence_u_content`
- **Microservice endpoint**: `POST /u-content` on port `8020`
- **State fields**: `sequence_u_fraction`, `sequence_u_count`, `sequence_u_length`

### Architecture decisions

1. **LangChain tool is the single source of truth for HTTP** — `agent_core/tools.py::compute_rna_sequence_u_content` is the only place that calls `requests.post` to port 8020 `/u-content`.
2. **`agent_core/sequence_utils.py` provides shared computation** — `compute_u_content()` is used by both the microservice and local stubs/scoring modules.
3. **Complete state tracking** — 3 fields tracked (`sequence_u_fraction`, `sequence_u_count`, `sequence_u_length`), not just the scalar fraction.

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- [ ] `microservices/rna_sequence_metrics_service/main.py`
- [ ] `agent_core/tools.py`
- [ ] `agent_core/tool_specs.py`
- [ ] `agent_core/state.py`
- [ ] `agent_core/capabilities/writebacks.py`
- [ ] `agent_core/sequence_utils.py`
- [ ] `tests/test_compute_rna_sequence_u_content.py`
- [ ] `rna_agent_system/docs/DEVELOPMENT.md`

### Tests that must pass

```bash
pytest tests/test_compute_rna_sequence_u_content.py -v
pytest tests/ -x --ignore=tests/integration -m "not integration"
```

### Notes for future maintainers

- Do **not** add duplicate HTTP logic in workflow tools or scoring modules. Always delegate to `compute_rna_sequence_u_content.invoke()`.
- If you change normalization rules in the microservice, you **must** update `sequence_utils.py` as well, or local fallback scores and stub test results will diverge.

---

## 9. Change Log: CAI for CDS v0.1.0

> **Status**: LOCKED — Any future modification must synchronize all files listed below and re-run the full test suite.  
> **Locked on**: 2026-04-28

### What is locked

- **Input schema** (`CaiForCdsInput`): `filepath`, `species`, `custom_codon_table_path`
- **Output schema** (`CaiForCdsOutput`): `input_filepath`, `cai_score`, `species`, `cds_length_nt`, `codon_count`, `valid_codons`, `invalid_codons`, `stop_codons_encountered`, `model`
- **ToolSpec identity**: `compute_cai_for_cds_sequence`
- **Transport**: `python_api` (pure Python, no microservice)
- **State fields**: `cai_for_cds_score`, `cai_for_cds_species`, `cai_for_cds_length_nt`, `cai_for_cds_codon_count`

### Architecture decisions

1. **Pure Python calculation** — CAI is a deterministic geometric-mean algorithm (Sharp & Li, 1987). No external binary or HTTP microservice is required. The tool runs directly in `agent_core/tools.py`.
2. **Kazusa Codon Usage Database as default source** — Built-in tables scraped from https://www.kazusa.or.jp/codon/ and shipped as `agent_core/data/codon_usage_kazusa.json`. This avoids runtime network dependencies.
3. **Custom table support** — Users can provide their own JSON codon usage table via `custom_codon_table_path`, enabling tissue-specific or engineered host tables.
4. **Species aliases** — Common names (`human`, `mouse`, `ecoli`, `cho`, etc.) are mapped to canonical Kazusa species names so LLM agents do not need exact Latin names.
5. **CDS validation** — Input is strictly validated as CDS (length multiple of 3, AUGC only). Stop codons are excluded from the CAI calculation.

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- [ ] `agent_core/tools.py`
- [ ] `agent_core/tool_specs.py`
- [ ] `agent_core/state.py`
- [ ] `agent_core/capabilities/writebacks.py`
- [ ] `agent_core/sequence_utils.py`
- [ ] `agent_core/data/codon_usage_kazusa.json`
- [ ] `tests/test_compute_cai_for_cds_sequence.py`
- [ ] `rna_agent_system/docs/DEVELOPMENT.md`

### Tests that must pass

```bash
pytest tests/test_compute_cai_for_cds_sequence.py -v
pytest tests/ -x --ignore=tests/integration -m "not integration"
```

### Notes for future maintainers

- Do **not** add an HTTP microservice wrapper for this tool. That would duplicate the calculation and add an unnecessary runtime dependency.
- If you update the built-in Kazusa tables, ensure the JSON schema stays consistent: `{codon: {aa: str, fraction: float}}`.
- The `fraction` field in Kazusa data is the *relative frequency within the amino-acid group* (sums to 1.0 per group). `build_cai_weights()` converts these to Sharp & Li relative adaptiveness weights (max = 1.0).

---

## 10. Change Log: LinearDesign Interface v0.2.0

> **Status**: LOCKED — Any future modification must synchronize all files listed below and re-run the full test suite.  
> **Locked on**: 2026-04-24

### Change motivation

1. **Missing INTERFACE LOCK** — LinearDesign lacked version-locked annotations.
2. **Missing batch capability** — Upstream `cat FASTA | ./lineardesign` supports batch design; only single-sequence was exposed.
3. **Missing upstream CLI parameters** — `--lambda`, `--codonusage`, `--verbose` were not exposed.
4. **State-layer coupling** — `tool_execution_node` mixed LinearDesign, RNARL, GEMORNA, and UTR design in a shared branch, causing RNARL-specific fields to be incorrectly written into LinearDesign results.
5. **Missing stderr** — Upstream stderr was not captured.
6. **Stale code** — `ProteinToCdsOutput` was unused but still referenced in docs.

### Canonical contract

#### Single-sequence tool

- **Tool name**: `design_mrna_cds_with_lineardesign`
- **Endpoint**: `POST http://127.0.0.1:8014/generate/cds`
- **Input model**: `agent_core/tools.py:LinearDesignCdsInput`
- **Output model**: `agent_core/tool_specs.py:LinearDesignCdsOutput`
- **Parameters**:
  - `lambda_value` (float, ge=0.0, default=0.0)
  - `codon_usage_path` (Optional[str], default=human table)
  - `verbose` (bool, default=False)
- **Required output fields**: `generated_sequence`, `structure`, `mfe`, `cai_score`, `lambda_value`, `codon_usage_path`, `raw_output`, `stderr`, `model`, `input_filepath`, `output_filepath`

#### Batch tool

- **Tool name**: `design_mrna_cds_batch_with_lineardesign`
- **Endpoint**: `POST http://127.0.0.1:8014/generate/cds/batch`
- **Input model**: `agent_core/tools.py:LinearDesignCdsBatchInput`
- **Output model**: `agent_core/tool_specs.py:LinearDesignCdsBatchOutput`
- **Required output fields**: `count`, `success_count`, `items`, `best_generated_sequence`, `best_structure`, `best_mfe`, `best_cai_score`, `batch_json_filepath`, `lambda_value`, `codon_usage_path`, `model`

#### AgentState dedicated fields

```python
lineardesign_output_filepath: str
lineardesign_generated_sequence: str
lineardesign_structure: str
lineardesign_mfe: float
lineardesign_cai_score: float
lineardesign_lambda_value: float
lineardesign_codon_usage_path: str
lineardesign_raw_output: str
lineardesign_stderr: str
lineardesign_model: str
lineardesign_batch_json_filepath: str
lineardesign_batch_count: int
lineardesign_batch_success_count: int
```

#### Upstream CLI alignment

| Upstream CLI | Current wrapper field | Description |
|--------------|----------------------|-------------|
| `echo SEQ \| ./lineardesign` | `/generate/cds` + `protein_sequence` | Single-sequence |
| `cat FASTA \| ./lineardesign` | `/generate/cds/batch` + `protein_sequences` | Batch |
| `-l, --lambda` | `lambda_value` | MFE/CAI balance, default 0.0 |
| `-c, --codonusage` | `codon_usage_path` | Codon table, default human |
| `-v, --verbose` | `verbose` | Verbose logs |

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- [ ] `microservices/lineardesign_service/main.py`
- [ ] `agent_core/tools.py`
- [ ] `agent_core/tool_specs.py`
- [ ] `agent_core/state.py`
- [ ] `agent_core/capabilities/writebacks.py`
- [ ] `workflow_api/mrna_handler.py`
- [ ] `workflow_api/mrna_schemas.py`
- [ ] `tests/test_integration_registry_smoke.py`

### Post-change rules

1. Re-run end-to-end tests (health / single / batch / wrapper / registry smoke).
2. Update this document's "Canonical contract" section.
3. If the change is breaking, **upgrade the version** (e.g., `0.2.0-port8014` → `0.3.0-port8014`).

---

## 11. Architecture Audit Summary

These findings were established during a codebase audit and remain true:

### Tool registry audit

- `ToolRegistry` (`tool_registry.py`) + `CapabilityRegistry` (`capabilities/base.py`) are dynamic and driven by `TOOL_SPECS`.
- Tool selection remains deterministic (`RuleBasedPlanner`), but the architecture supports swapping to `LLMFunctionCallingPlanner` without touching Layer 2 or below.

### Schema audit

- Input schemas are enforced via Pydantic models in `tools.py`.
- Output schemas in `tool_specs.py` are validated at runtime by `Capability` via `output_model.model_validate()`.
- Error schemas are largely missing; errors propagate as raw exception strings. (Still true.)

### Planning / critic / retry audit

- The system is a **deterministic rule-driven workflow**, not an open-ended agent.
- The LangGraph path critic is a hard threshold checker (`mfe > -20.0`).
- The mRNA CDS Workflow path has **no critic** — ranking by `-mfe + codon_count * log(CAI)` is sufficient. Re-running the same tools on the same protein does not improve candidates.
- Retry logic is bounded by `max_retries = 3` (graph path) or `ExecutionPlan.max_retries` (workflow path).

### Supported tasks audit (current ground truth)

| Category | Available | Partial | Unavailable (mock removed) |
|----------|-----------|---------|---------------------------|
| siRNA / antisense | `sirna_duplex_energy` | `sirna_design_evitar` | siRNA efficiency, off-target count |
| RNA 2° structure | `rna_secondary_structure_viennarna`, `rna_secondary_structure_linearfold`, `aso_accessibility_viennarna`, `inverse_folding_viennarna` | — | — |
| mRNA / CDS | — | `cds_codon_metrics`, `protein_to_cds_design`, `mrna_stability_prediction`, `ires_prediction`, `blastn_similarity_search` | — |
| RNA 3D / design / ligand | — | `rna_tertiary_structure_prediction`, `rna_structure_to_sequence_design`, `rna_ligand_scoring`, `odesign_inference` | — |
| CRISPR / sgRNA | — | `crispr_offtarget_scoring`, `crispr_specificity_csv`, `crispr_offtarget_search`, `crispr_sgrna_optimization`, `sgrna_handle_design` | — |

> **Partial** = tool exists but depends on Linux / GPU / weights / reference genome / large files that may not be present in all environments.

---

## 13. Change Log: RNA Aptamer Design Tools

### v0.2.0 — Added ProteinX complex prediction & interface analysis (2026-05-04)

| Tool | Transport | Files touched |
|------|-----------|---------------|
| `predict_rna_protein_complex_with_proteinx` | HTTP | `tools.py`, `tool_specs.py`, `state.py`, `writebacks.py`, + `microservices/proteinx_service/` |
| `analyze_rna_protein_interface` | Pure Python (biopython + freesasa) | `tools.py`, `tool_specs.py`, `state.py`, `writebacks.py` |

**Scoring simplification**: Removed MFE, GC, and unpaired-fraction components from the aptamer total score. Current formula:
```
total_score = EGARPS + (RhoFold_pLDDT / 100) + ipTM
```
GC content is still computed (for critic quality gating) but no longer contributes to ranking.

### v0.1.0 — Initial aptamer toolkit (2026-05-01)

| Tool | Transport | Files touched |
|------|-----------|---------------|
| `extract_rna_sequence_from_cif` | Pure Python (biopython) | `tools.py`, `tool_specs.py`, `state.py`, `writebacks.py` |
| `build_odesign_aptamer_input_json` | Pure Python | `tools.py`, `tool_specs.py`, `state.py`, `writebacks.py` |
| `predict_protein_structure_with_proteinx` | HTTP | `tools.py`, `tool_specs.py`, `state.py`, `writebacks.py`, + `microservices/proteinx_service/` |
| `identify_protein_binding_hotspots` | Pure Python (freesasa + DBSCAN) | `tools.py`, `tool_specs.py`, `state.py`, `writebacks.py` |
| `score_structure_alignment` | Pure Python (biopython) | `tools.py`, `tool_specs.py`, `state.py`, `writebacks.py` |

### New dependencies

- `biopython>=1.79`
- `freesasa>=2.2`
- `scikit-learn` (for DBSCAN hotspot clustering)

### Microservice added

- `microservices/proteinx_service/` — framework only (FastAPI returns 501 until ProteinX backend is deployed).

---

## 12. Enhancement Proposals

The following proposals are **not yet fully implemented** but are documented for future development:

### Proposal 1: Unified task routing with `ToolSpec.task_tags`

- **Problem**: Router keywords and Specialist dispatch tables are scattered across `planning/rule_based/parsers/common.py` and `graph_nodes.py` and drift over time.
- **Design**: Add `task_tags: list[str]` to `ToolSpec`. Build a bidirectional index (`tag -> list[tool_name]`). Router outputs a canonical `task_id`; workflow uses the index to select tools.
- **Affected tasks**: All.
- **Risks**: Maintenance cost of keeping tags accurate.
- **Benefits**: Reduced mis-routing and unauthorized tool calls.

### Proposal 2: Strict input / parameter validator

- **Problem**: Invalid inputs often fail late (inside the microservice) with opaque error messages.
- **Design**: Add a `Validator` step before `tool_execution_node` that checks file existence, sequence length, required columns, region bounds, etc.
- **Affected tasks**: duplex / BLAST / CRISOT / ASO in the first wave.
- **Risks**: Overly strict rules may reject edge-case valid inputs.
- **Benefits**: Earlier failure, better diagnostics.

### Proposal 3: Output standardization (Vienna fold dict)

- **Problem**: Some older tools return raw strings that require downstream parsing.
- **Design**: Ensure every tool returns a structured dict with stable key names (e.g., `structure`, `mfe_kcal_per_mol`).
- **Affected tasks**: All fold-related tasks.
- **Risks**: Compatibility changes in downstream consumers.
- **Benefits**: Removes string parsing and improves auditability.
- **Status**: **Partially implemented** — ViennaRNA fold already returns a dict.

### Proposal 4: Deterministic failure recovery / fallback rules

- **Problem**: A single microservice failure breaks the entire workflow.
- **Design**: Define explicit fallback chains (e.g., ViennaRNA → LinearFold for folding; GEMORNA → LinearDesign for CDS).
- **Affected tasks**: fold, CDS design.
- **Risks**: Extra calls increase latency.
- **Benefits**: Higher completion rate.
- **Status**: **Partially implemented** — ViennaRNA already falls back to LinearFold on failure.

---

*For system overview and capability matrix, see `README.md`. For architecture and core interfaces, see `ARCHITECTURE.md`. For per-tool specs and task mapping, see `TOOLS_AND_TASKS.md`.*
