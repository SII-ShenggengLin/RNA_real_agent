# Deployment & Testing Guide

> **Scope**: environment setup, deployment procedures, testing recipes, and microservice curl examples.
> **Last updated**: 2026-06-01

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

Current submodules: GEMORNA, GerNA-Bind, RNARL, RhoFold, RhoDesign, RiboDiffusion, RNAsmol, RNASTOP, CRISOT, ODesign, IRESfinder, LinearDesign, LinearFold, Evitar, ViennaRNA, sgrna_design, codonw-slim, Protenix, EGARPS.

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
| CRGPT | `external_repos/sgrna_design/trained_model/crgen_small/pytorch_model.bin` |
| CRISOT | `external_repos/CRISOT/models/crisot_score_param.pkl` + `crisot_fingerprint_encoding.pkl` |
| ProteinX | `external_repos/Protenix/checkpoints/` |
| EGARPS | `external_repos/EGARPS/esm2_models/` + `rna_fm_models/` |

---

## 3. Testing

### 3.1 Three-layer validation

Always validate in this order:

1. **Microservice layer**: `curl /health` → `curl` business endpoint
2. **Agent tool layer**: `tools.py` wrapper functions
3. **CLI / API integration**: natural-language input

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
| `test_compute_rna_sequence_u_content.py` | U content tool |
| `test_compute_cai_for_cds_sequence.py` | CAI computation |
| `test_rna_gc_content_workflow.py` | GC workflow tool |
| `test_mrna_workflow.py` | mRNA workflow |
| `test_mrna_sequence_scoring_layer3.py` | mRNA sequence scoring (Layer 3) |
| `test_mrna_cds_design_layer3.py` | mRNA CDS design (Layer 3) |
| `test_full_length_mrna_design.py` | Full-length mRNA design |
| `test_sirna_design_workflow.py` | siRNA design |
| `test_sgrna_design_workflow.py` | sgRNA design |
| `test_rna_secondary_structure_design.py` | 2° structure → sequence |
| `test_rna_tertiary_structure_design.py` | 3° structure → sequence |
| `test_rna_small_molecule_interaction.py` | RNA–ligand scoring |
| `test_rna_aptamer_design.py` | RNA aptamer design |
| `test_ires_prediction.py` | IRES prediction |
| `test_aso_target_screening.py` | ASO target screening |
| `test_llm_planner.py` | LLM planner |
| `test_tool_registry_executor.py` | Registry + executor |
| `test_agent_runner.py` | AgentRunner natural-language end-to-end |
| `test_integration_registry_smoke.py` | Integration smoke tests |
| `test_mrna_cds_design_comprehensive.py` | mRNA CDS design (comprehensive) |
| `test_mrna_sequence_scoring_comprehensive.py` | mRNA sequence scoring (comprehensive) |
| `test_full_length_mrna_design_comprehensive.py` | Full-length mRNA design (comprehensive) |
| `test_sirna_design_comprehensive.py` | siRNA design (comprehensive) |
| `test_sgrna_design_e2e.py` | sgRNA design (end-to-end) |
| `test_rna_secondary_structure_design_comprehensive.py` | 2° structure design (comprehensive) |
| `test_rna_tertiary_structure_design_comprehensive.py` | 3° structure design (comprehensive) |
| `test_rna_small_molecule_interaction_comprehensive.py` | RNA–ligand scoring (comprehensive) |
| `test_ires_prediction_comprehensive.py` | IRES prediction (comprehensive) |
| `test_aso_target_screening_comprehensive.py` | ASO target screening (comprehensive) |
| `test_bmc_full_length_mrna.py` | BMC full-length mRNA |
| `test_deterministic_router.py` | Deterministic router |
| `test_partial_retry.py` | Partial retry optimization |
| `test_shuffle_cds_junction_codons.py` | Junction codon shuffler |

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

### 3.5 Natural-language test cases

| Test purpose | Input example |
|--------------|---------------|
| Secondary structure (ViennaRNA) | `请预测这条 RNA 的二级结构 fold：AUGCUAACGUAGCUAUGCUAUGCUAACGUAGCUAUGCUA` |
| siRNA duplex energy | `ViennaRNA duplex rnacofold，sense=GGCAUGCAUGC antisense=GCAUGCAUGCC` |
| ASO accessibility | `ASO accessibility plfold 可及性，region=10-50，靶标 mRNA：AUGCAUGCAUGC...` (≥50 nt) |
| Inverse folding | `inverse fold 逆折叠 rnainverse，structure=((((....))))，repeats=5` |
| LinearFold | `fold linearfold 二级结构 AUGGCUACGUAGCUAGCUAGCUAGCUGA beam_size=20` |
| Codon metrics | `codonw-slim 分析 CDS 密码子 CAI` + CDS sequence |
| GC content | `gc content 计算 GC 含量` + RNA sequence |
| BLAST search | `blastn 比对 subject_fasta=workspace/test.fa 序列 ATGCATGCATGC` |
| RiboDiffusion | `ribodiffusion 扩散逆折叠 PDB=workspace/my.pdb n_samples=3` |

---

## 4. Microservice Runtime Dependencies

### CRGPT (sgRNA design & scoring) — port 8017

| Dependency | Status | Notes |
|------------|--------|-------|
| Conda env `sgrna_design_service_env` | Required | `cd microservices/sgrna_design_service && conda env create -f environment.yml` |
| Model weights | Required | `external_repos/sgrna_design/trained_model/crgen_small/pytorch_model.bin` (≈ 57 MB) |
| GPU | **Strongly recommended** | PyTorch CUDA inference; auto-falls back to CPU if unavailable |
| ViennaRNA | Required for MCMC mode | `import RNA` must succeed in service env |
| Startup | `bash microservices/sgrna_design_service/start.sh` | Runs `uvicorn main:app --host 0.0.0.0 --port 8017` |

### CRISOT (off-target scoring / specificity / optimization / fingerprinting) — port 8011

| Dependency | Status | Notes |
|------------|--------|-------|
| Conda env `crisot_service_env` | Required | `cd microservices/crisot_service && conda env create -f environment.yml` |
| Model weights | Required | `external_repos/CRISOT/models/crisot_score_param.pkl` + `crisot_fingerprint_encoding.pkl` |
| `cas-offinder` | Required for `/off-spec`, `/optimize`, `/rescore` | Must be on `PATH` in service env |
| Reference genome FASTA | Required for `/off-spec`, `/optimize`, `/rescore` | Set `CRISOT_DEFAULT_REF_GENOME=/absolute/path/to/genome.fa` or place `hg38.fa` under `external_repos/CRISOT/script/`; falls back to `external_repos/CRISOT/data/test_genome.fa` |
| GPU | **Strongly recommended** | CRISOT-Score / CRISOT-FP use PyTorch/XGBoost on GPU |
| Startup | `bash microservices/crisot_service/start.sh` | Runs `uvicorn main:app --host 0.0.0.0 --port 8011` |

### ProteinX (protein structure + RNA-protein complex prediction) — port 8022

| Dependency | Status | Notes |
|------------|--------|-------|
| Conda env `proteinx_service_env` | Required | `cd microservices/proteinx_service && conda env create -f environment.yml` |
| Model weights | Required | `external_repos/Protenix/checkpoints/` |
| GPU | **Required** | AlphaFold3-style architecture; CPU inference not viable |
| Startup | `bash microservices/proteinx_service/start.sh` | Runs `uvicorn main:app --host 0.0.0.0 --port 8022` |

### EGARPS (RNA-protein complex scoring) — port 8023

| Dependency | Status | Notes |
|------------|--------|-------|
| Conda env `egarps_service_env` | Required | `cd microservices/egarps_service && conda env create -f environment.yml` |
| Model weights | Required | `external_repos/EGARPS/esm2_models/` + `rna_fm_models/` |
| GPU | **Required** | ESM-2 + RNA-FM encoders need GPU |
| Startup | `bash microservices/egarps_service/start.sh` | Runs `uvicorn main:app --host 0.0.0.0 --port 8023` |

### ODesign (biomolecule design) — port 8012

| Dependency | Status | Notes |
|------------|--------|-------|
| Conda env `odesign_service_env` | Required | `cd microservices/odesign_service && conda env create -f environment.yml` |
| Model weights | Required | `external_repos/ODesign/ckpt/*.pt` + `ckpt/*.ckpt` |
| GPU | **Required** | Diffusion model inference |
| Startup | `bash microservices/odesign_service/start.sh` | Runs `uvicorn main:app --host 0.0.0.0 --port 8012` |

> For LLM configuration (DeepSeek / OpenAI / Anthropic / etc.), see `AGENTS.md` §LLM Configuration.
