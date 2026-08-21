# Deployment & Testing Guide

> **Scope**: environment setup, deployment procedures, testing recipes, and microservice curl examples.
> **Last updated**: 2026-08-18

---

## 1. Environment Setup

### 1.2 Main Agent environment

```bash
cd rna_agent_system
pip install -r requirements.txt
```

### 1.3 Per-tool Conda environments

Each microservice has its own Conda `environment.yml`; create and activate it before running `start.sh`.

> **Note**: The CLI auto-starts microservices; manual `start.sh` is for individual service debugging.

### 1.4 Submodule initialization

`external_repos/` holds **20 vendored external repos, 17 of them registered git submodules** (EGARPS, Protenix and RiboDiffusion are vendored as plain directories and are not in `.gitmodules`).

```bash
# Fresh clone
git clone --recurse-submodules <repo-url>

# Existing clone
git pull && git submodule update --init --recursive
```

Registered submodules (17): GEMORNA, GerNA-Bind, RNARL, RhoFold, RhoDesign, RNAsmol, RNASTOP, CRISOT, ODesign, IRESfinder, LinearDesign, LinearFold, Evitar, ViennaRNA, sgrna_design, InstructNA, codonw-slim (legacy: its service was removed 2026-08-18; the submodule stays registered). Vendored (unregistered): EGARPS, Protenix, RiboDiffusion.

#### Pinned forks with local patches (read before first run)

Three submodules do **not** point at the original upstream repositories: `.gitmodules` pins them to public forks under `SII-ShenggengLin/` that carry **one local patch commit on top of upstream**. A `--recurse-submodules` clone fetches the patched code automatically (the forks are public and the pinned SHAs are their `main` tips), but if you compare behaviour against the originals, know that these differ:

| Submodule | `.gitmodules` URL (what you get) | Original upstream | Pinned patch | What the patch changes |
|---|---|---|---|---|
| LinearDesign | `SII-ShenggengLin/LinearDesign` @ `ef10882` | [LinearDesignSoftware/LinearDesign](https://github.com/LinearDesignSoftware/LinearDesign) | 2026-08-10 "junction-aware design patch + memory guard wrapper" | (a) C++ junction-aware objective in `src/linear_design.cpp` + beam-CKY parser/backtrace — the junction-aware *tool* was retired 2026-08-18 on a P2 NO-GO, but the patched source stays pinned and the standard `/generate/cds` build comes from it; (b) `bin/LinearDesign_2D` becomes a memory-guard wrapper (address-space cap + `oom_score_adj`) that `exec`s the compiled `bin/LinearDesign_2D.real` — the compile-and-rename sequence in §3.1 is **mandatory** |
| RhoDesign | `SII-ShenggengLin/RhoDesign` @ `0dc7c54` | [ml4bio/RhoDesign](https://github.com/ml4bio/RhoDesign) | 2026-08-10 "local deployment patches for the RNADesignAgent microservice" | `src/inference.py` / `src/inference_without2d.py`: drops the hard-coded `random.seed(1)` at import and adds a `--seed` CLI flag seeding python/numpy/torch/CUDA, so the microservice can offer reproducible sampling |
| RhoFold | `SII-ShenggengLin/RhoFold` @ `6761653` | [ml4bio/RhoFold](https://github.com/ml4bio/RhoFold) | 2026-08-10 "local inference patch + local weights path notes" | `inference.py`: skips the HuggingFace `snapshot_download` when the local checkpoint already exists (offline / air-gapped servers); `pretrained/README.md` notes on local weights; drops two `.DS_Store` |

The remaining 14 registered submodules are pinned to unmodified upstream commits; RNARL and RNASTOP are lab-original repositories (not forks).

---

## 2. CLI Startup Flow (Recommended)

The interactive TUI CLI (`cli/form_chat.py`) automates resource checking and microservice orchestration.

### 2.1 Resource pre-check

On launch, the CLI runs `cli/resource_checker.py`:

| Check | Tool | Requirement | Failure action |
|-------|------|-------------|----------------|
| GPU | `nvidia-smi` | ≥ 1 NVIDIA GPU with ≥ 24 GB VRAM | Warn and exit |
| Free RAM | `psutil` | ≥ 16 GB available | Warn and exit |
| CPU load | `psutil` | ≤ 90 % overall usage | Warn and exit |

### 2.2 Workflow selection

The CLI lists all 11 workflows. The user selects by number; multi-select is supported (e.g. `1,3,8`).

### 2.3 Automatic microservice startup

`cli/service_orchestrator.py` derives the union of all microservices required by the selected workflows from each workflow's `required_capabilities` (via `agent_core.services.service_manager.CAPABILITY_SERVICE_MAP`). For each service:

1. **Health probe** — `GET /health` (5 s timeout)
2. **Start if unhealthy** — `subprocess.Popen(["bash", "start.sh"], ...)` with `start_new_session=True`
3. **Poll until ready** — Retry every 5 s up to 300 s total

Services shared across workflows (e.g. ViennaRNA) are started only once.

### 2.4 Per-turn workflow selection

After all services are healthy, the user enters the dialogue loop. On each turn:
1. Pick the active workflow from the enabled set
2. Fill the structured TUI form (basic parameters shown by default; advanced tool overrides folded)
3. `AgentRunner.stream_form()` executes with `explicit_workflow=active_wf` and the validated form parameters

### 2.5 Non-interactive mode

```bash
PYTHONPATH="$(pwd):$PYTHONPATH" python cli/form_chat.py \
  --workflow rna_small_molecule_interaction \
  --params-file params.json
```

---

## 3. Deployment Guide

### 3.1 Services requiring compilation or extra scripts

| Service | Extra step |
|---------|------------|
| LinearDesign | `cd external_repos/LinearDesign && make` then **rename + restore the wrapper** (the compiled binary is NOT tracked and `make` overwrites it): `mv bin/LinearDesign_2D bin/LinearDesign_2D.real && git checkout -- bin/LinearDesign_2D`. The tracked `bin/LinearDesign_2D` is a memory-guard wrapper that `exec`s `LinearDesign_2D.real` (see §1.4 patch table) |
| LinearFold | `cd external_repos/LinearFold && make` |
| GerNA-Bind | `bash microservices/gernabind_service/install_pyg_gpu.sh` |
| RiboDiffusion | `conda activate ribodiffusion_service_env && bash install_pyg_torch_extensions.sh` |

### 3.2 Large file / weight management

The following files are **not** tracked in the main Git repository and must be prepared separately on the server:

| Tool | Weight paths |
|------|--------------|
| GEMORNA | `external_repos/GEMORNA/checkpoints/*.pt` |
| RNARL | `external_repos/RNARL/checkpoints/*.pt` + `esm2_model_t33_650M_UR50D/` |
| RhoFold | `external_repos/RhoFold/pretrained/RhoFold_pretrained.pt` |
| RhoDesign | `external_repos/RhoDesign/checkpoint/*.pth` |
| RNAsmol | `external_repos/RNAsmol/saved_model/*.pt` |
| RNASTOP | `external_repos/RNASTOP/models/best_model_weights_withoutDNABERT` + `RNA-FM_pretrained.pth` |
| GerNA-Bind | `external_repos/GerNA-Bind/Model/*.pth` |
| ODesign | `external_repos/ODesign/ckpt/*.pt` + `ckpt/*.ckpt` + `data/components.*` |
| RiboDiffusion | `external_repos/RiboDiffusion/ckpts/exp_inf.pth` (or `exp_inf_large.pth`) |
| CRGPT | `external_repos/sgrna_design/trained_model/crgen_small/pytorch_model.bin` |
| CRISOT | `external_repos/CRISOT/models/crisot_score_param.pkl` + `crisot_fingerprint_encoding.pkl` |
| ProteinX | `external_repos/Protenix/checkpoints/` |
| EGARPS | `external_repos/EGARPS/esm2_models/` + `rna_fm_models/` |

---

## 4. Testing

### 4.1 Three-layer validation

Always validate in this order:

1. **Microservice layer**: `curl /health` → `curl` business endpoint
2. **Agent tool layer**: `tools.py` wrapper functions
3. **CLI / API integration**: structured form parameters via TUI or JSON file

### 4.2 Agent-core test suite

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x
```

### 4.3 Key test files by category

| Category | Test files |
|----------|------------|
| Tool-level | `test_compute_rna_sequence_gc_content.py`, `test_compute_dot_bracket_unpaired_fraction.py`, `test_compute_rna_sequence_u_content.py`, `test_compute_cai_for_cds_sequence.py` |
| Workflow (unit) | `test_mrna_workflow.py`, `test_sirna_design_workflow.py`, `test_sgrna_design_workflow.py`, `test_rna_secondary_structure_design.py`, `test_rna_tertiary_structure_design.py`, `test_rna_small_molecule_interaction.py`, `test_rna_aptamer_design.py`, `test_aso_target_screening.py`, `test_full_length_mrna_design.py` |
| Layer 4 / integration | `test_runner_form.py`, `test_session_memory.py`, `test_mrna_cds_design_layer4.py`, `test_mrna_sequence_scoring_layer4.py`, `test_full_length_mrna_design_layer4.py`, `test_rna_secondary_structure_design_layer4.py`, `test_rna_tertiary_structure_design_layer4.py`, `test_integration_registry_smoke.py` |
| Infrastructure | `test_tool_registry_executor.py`, `test_full_length_mrna_evaluators.py` |
| End-to-end (live microservices) | `test_full_length_mrna_e2e_live.py` — full-length mRNA design with real LinearDesign/GEMORNA/ViennaRNA/LinearFold/IRESfinder/RNASTOP/sequence-metrics services |

### 4.4 Form validation

Required parameters are validated by `FormValidator` using the workflow's Pydantic input model. If validation fails, the TUI form is shown again with error hints. The API returns a 422 error for unknown workflows and a structured error response for execution failures.

### 4.5 Microservice curl examples

```bash
# ViennaRNA fold
curl -sS -X POST http://127.0.0.1:8003/fold \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"GGGGAAAACCCC"}' | python3 -m json.tool

# ViennaRNA RNAplfold whole-sequence profile
curl -sS -X POST http://127.0.0.1:8003/plfold-profiles \
  -H 'Content-Type: application/json' \
  -d '{"sequence":"GGGGAAAACCCCUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC","winsize":40,"span":30,"unpaired_ulength":15,"params":{"temp_c":37}}' \
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

# RNA sequence metrics (GC)
curl -sS -X POST http://127.0.0.1:8020/gc-content \
  -H 'Content-Type: application/json' \
  -d '{"sequence_filepath":"rna_agent_system/workspace/blast_test_query.fa"}' | python3 -m json.tool

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

---

## 4.6 Full-length mRNA design microservice launcher

No manual launcher is needed: the CLI / `AgentRunner` pre-flight maps each
workflow's `required_capabilities` to local microservices and auto-starts the
missing ones (health-checked on each port). For `FullLengthMrnaDesignWorkflow`
this covers LinearDesign (8014), GEMORNA (8004), ViennaRNA (8003), LinearFold
(8015), IRESfinder (8013), RNASTOP (8009) and the sequence-metrics service
(8020).

Run the regression smoke test against live services (services are started
automatically on demand):

```bash
PYTHONPATH="$(pwd):$PYTHONPATH" python tests/test_full_length_mrna_e2e_live.py
```

> **Note**: the full-length workflow's ranking is deterministic (ASF reference-point optimization); no LLM API key is required for it.

---

## 5. Microservice Runtime Dependencies

| Service | Port | Conda env | Key dependencies |
|---------|------|-----------|------------------|
| CRGPT | 8017 | `sgrna_design_service_env` | Weights (`crgen_small/pytorch_model.bin`); ViennaRNA for MCMC; GPU recommended |
| CRISOT | 8011 | `crisot_service_env` | Weights (`crisot_score_param.pkl`); `cas-offinder` on PATH for genome-wide ops; GPU recommended |
| ProteinX | 8022 | `proteinx_service` | Weights (`Protenix/checkpoints/`); **GPU required** |
| EGARPS | 8023 | `egarps_env` | Weights (`esm2_models/` + `rna_fm_models/`); **GPU required** |
| ODesign | 8012 | `odesign_service_env` | Weights (`ckpt/*.pt`); **GPU required** |

> **ProteinX runtime note**: predictions execute in a background thread so `/health` remains responsive. The service is single-worker, so requests are still serialized.

> For LLM configuration, see `AGENTS.md` §LLM Configuration.
