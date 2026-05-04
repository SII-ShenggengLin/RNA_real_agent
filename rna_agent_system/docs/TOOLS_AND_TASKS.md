# Tools & Tasks Reference

> **Scope**: per-tool specs, task definitions, workflow step patterns, and microservice deployment notes.

---

## Table of Contents

1. [Tool Registry by Domain](#1-tool-registry-by-domain)
2. [ViennaRNA Suite (Port 8003)](#2-viennarna-suite-port-8003)
3. [LinearFold Suite (Port 8015)](#3-linearfold-suite-port-8015)
4. [CDS Design Tools](#4-cds-design-tools)
5. [Structure Prediction & Design](#5-structure-prediction--design)
6. [Ligand Scoring](#6-ligand-scoring)
7. [CRISPR / sgRNA Tools](#7-crispr--sgrna-tools)
8. [siRNA / Antisense Tools](#8-sirna--antisense-tools)
9. [Sequence Metrics (Port 8020)](#9-sequence-metrics-port-8020)
10. [Other Tools](#10-other-tools)
11. [Task-Workflow Mapping](#11-task-workflow-mapping)
12. [Standard Workflow Step Pattern](#12-standard-workflow-step-pattern)

---

## 1. Tool Registry by Domain

### RNA secondary structure

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `predict_rna_secondary_structure` | 8003 | `filepath` | `structure`, `mfe_kcal_per_mol` | ViennaRNA RNAfold; falls back to LinearFold on failure |
| `compute_sirna_duplex_binding_vienna` | 8003 | `filepath` (2 FASTA records) | `structure` (with `&`), `mfe_kcal_per_mol` | RNAcofold; v0.2.0-port8003 |
| `compute_aso_target_accessibility_vienna` | 8003 | `filepath`, `region_start`, `region_end` | `mean_unpaired_prob` | RNAplfold target region |
| `predict_rna_local_accessibility_profile_vienna` | 8003 | `filepath` | per-position unpaired probs | RNAplfold whole-sequence profile; ≤8000 nt default limit |
| `inverse_fold_rna_secondary_structure_vienna` | 8003 | `filepath` (dot-bracket + optional hint) | `best_sequence` | RNAinverse; heuristic |
| `predict_rna_secondary_structure_with_linearfold` | 8015 | `filepath`, optional `constraints`, `shape_file_path` | `structure`, `mfe` | Beam-search folding; v0.2.0 |
| `evaluate_rna_structure_with_linearfold` | 8015 | `filepath` | energy evaluation | Evaluates a known structure |
| `predict_rna_secondary_structure_with_linearfold_zuker` | 8015 | `filepath` | subopt structures | Zuker subopt enumeration |

### CDS design (protein → mRNA)

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `design_mrna_cds_with_lineardesign` | 8014 | `filepath`, `lambda_value`, `codon_usage_path`, `verbose` | `generated_sequence`, `structure`, `mfe`, `cai_score`, `stderr` | v0.2.0; requires `make` |
| `design_mrna_cds_batch_with_lineardesign` | 8014 | `filepath` (FASTA or multi-line) | `count`, `items`, `best_*` | Batch endpoint; same params |
| `design_mrna_cds_with_rnarl` | 8008 | `filepath`, `model_type` (7 options) | `generated_sequence` | v0.2.0; max 1308 aa; GPU |
| `design_mrna_cds_with_gemorna` | 8004 | `filepath` (protein) | `generated_sequence` | Python 3.10 only; GPU |

### Tertiary structure & inverse folding

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `predict_rna_tertiary_structure_with_rhofold` | 8005 | `filepath`, `relax_steps`, `checkpoint_path`, `device` | `pdb_filepath`, `ct_filepath`, `mean_plddt` | v0.2.0; GPU; local checkpoint priority |
| `design_rna_sequence_with_rhodesign` | 8006 | `pdb_filepath`, optional `.npy` contact map | `predicted_sequence`, `recovery_rate`, FASTA | v0.2.0; with-2D vs without-2D |
| `design_rna_inverse_fold_with_ribodiffusion` | 8021 | `pdb_filepath`, `n_samples`, `sampling_steps`, `checkpoint_name` | `predicted_sequence`, `recovery_rate`, FASTA paths | v0.2.0; GPU; `--deterministic` / `--nodeterministic` |

### Ligand scoring

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `score_rna_ligand_binding_with_rnasmol` | 8007 | `filepath`, `smiles`, `dataset`, `perturbation_type`, `device`, `checkpoint_path` | `probability_positive`, `predicted_label` | v0.2.0; 6 weight files |
| `score_rna_ligand_binding_with_gernabind` | 8010 | `filepath`, `smiles`, `dataset`, `split_method` | `probability`, `predicted_label` | v0.1.0; auto-calls RhoFold if no PDB |

### RNA-protein complex scoring & design

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `score_rna_protein_complex_with_egarps` | 8023 | `filepath` (PDB), `academic` | `complex_id`, `native_probability` | v0.1.0; GPU required; non-academic mode skips DSSR/NACCESS |
| `predict_rna_protein_complex_with_proteinx` | 8022 | `protein_filepath`, `rna_filepath` | `pdb_filepath`, `mean_plddt`, `ipTM`, `ranking_confidence` | v0.1.0; `rnaChain` + `proteinChain`; GPU |
| `analyze_rna_protein_interface` | — (pure Python) | `complex_pdb_filepath`, `protein_chain_id`, `rna_chain_id` | `interface_contacts`, `buried_sasa`, `hydrogen_bonds`, `salt_bridges` | v0.1.0; biopython + freesasa |

### CRISPR / sgRNA

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `score_crispr_off_target_with_crisot` | 8011 | `filepath`, `target_sequence` | `crisot_score` | Normalized to 23 nt |
| `calculate_crispr_specificity_with_crisot` | 8011 | `csv_filepath` | `scored_csv_filepath` | On/Off pairs |
| `search_crispr_off_targets_with_crisot` | 8011 | `filepath`, `target_sequence`, `genome_path` | off-target list + spec | Needs Cas-OFFinder |
| `optimize_sgrna_with_crisot` | 8011 | `filepath`, `genome_path` | `best_sgrna`, `best_delta_spec` | Can be very slow |
| `design_sgrna_handle_with_crgpt` | 8017 | `filepath` / `seed_sequence`, `n_samples` | `best_sequence`, `nn_score` | v0.3.0; `mcmc` or `naive` mode |

### siRNA / antisense

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `design_sirna_with_evitar` | 8016 | `filepath`, `mode`, `predict`, off-target params | candidate list, output file | v0.2.0; Linux only |

### Sequence metrics

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `compute_rna_sequence_gc_content` | 8020 | `filepath` | `gc_content`, `sequence_length`, `gc_count`, `g_count`, `c_count` | v0.1.0; T→U normalization |
| `compute_rna_sequence_u_content` | 8020 | `filepath` | `u_fraction`, `sequence_length`, `u_count` | v0.1.0; T→U normalization |
| `compute_dot_bracket_unpaired_fraction` | 8020 | `filepath` | `unpaired_fraction`, `structure_length`, `dot_count` | v0.1.0; validates characters |

### CDS metrics

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `compute_cai_for_cds_sequence` | — (pure Python) | `filepath`, `species`, optional `custom_codon_table_path` | `cai_score`, `species`, `cds_length_nt`, `codon_count`, `valid_codons` | v0.1.0; Kazusa tables; 11 built-in species; stop codons excluded |
| `analyze_cds_codon_metrics_with_codonw_slim` | 8018 | `filepath` (in-frame CDS) | `cai_score`, metrics JSON | v0.2.0; requires `install_codonw_slim.sh`; 3 CAI refs only |

### Other

| Tool | Port | Input (key fields) | Output (key fields) | Notes |
|------|------|--------------------|---------------------|-------|
| `run_blastn_similarity_search` | 8019 | `filepath`, `subject_fasta_path` **or** `subject_db` | `hit_count`, `tabular_tsv_filepath` | v0.2.0; mutually exclusive subject modes |
| `predict_mrna_stability_with_rnastop` | 8009 | `filepath`, optional `structure`/`loop_type` | `mean_reactivity`, `mean_deg_mg_ph10`, `mean_deg_mg_50c`, `overall_stability` | v0.1.0; >1022 nt truncated |
| `predict_putative_ires_with_iresfinder` | 8013 | `filepath`, `mode` (0/1/2), window params | probability scores | v0.2.0; DNA-normalized input (U→T) |
| `run_odesign_inference` | 8012 | `input_json_filepath` | prediction files, logs | v0.3.0; GPU/weights required |

---

## 2. ViennaRNA Suite (Port 8003)

| Item | Description |
|------|-------------|
| Upstream | [ViennaRNA/ViennaRNA](https://github.com/ViennaRNA/ViennaRNA.git) |
| Microservice | `microservices/viennarna_fold/` |
| Environment | `python=3.10` + bioconda `viennarna` |
| Endpoints | `GET /health`, `POST /fold`, `POST /sirna-duplex`, `POST /aso-accessibility`, `POST /plfold-profiles`, `POST /inverse-fold` |
| Backend strategy | Prefer RNAlib (`import RNA`), fallback to CLI (`RNAfold --noPS`); RNAplfold uses **`RNAplfold`** executable |

**Agent tool functions**

- `predict_rna_secondary_structure(filepath)` — single-sequence MFE secondary structure
- `compute_sirna_duplex_binding_vienna(filepath)` — sense/antisense cofold
- `compute_aso_target_accessibility_vienna(filepath, region_start, region_end)` — RNAplfold target region accessibility
- `predict_rna_local_accessibility_profile_vienna(filepath, ...)` — whole-sequence local accessibility curve (lunp column 1); writes to `workspace/vienna_rnaplfold_profile_*.tsv`
- `inverse_fold_rna_secondary_structure_vienna(filepath)` — RNAinverse

**Deployment notes**

- Default install via Conda bioconda `viennarna`; no compilation needed.
- Optional: `build_from_submodule_linux.sh` for source compilation.
- `POST /plfold-profiles` default limit: **≤8000 nt** (server-side constant `_MAX_PLFOLD_PROFILE_SEQ_LEN`).

**Endpoint detail: `/fold`**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sequence` | str | Yes | RNA sequence |
| `params` | dict | No | Energy model params |
| `constraint` | str | No | Hard constraint string |
| `shape_file` | str | No | SHAPE reactivity file path |

Returns: `structure`, `mfe`, `centroid_structure`, `ensemble_free_energy`.

**Endpoint detail: `/sirna-duplex`**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sense` / `antisense` | str | Alt | Two sequences |
| `fasta_content` | str | Alt | 2-record FASTA |
| `params` | dict | No | Energy model params |

Returns: `structure`, `mfe`, `equilibrium_concentrations` (if concentrations provided).

**Endpoint detail: `/aso-accessibility`**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sequence` | str | Yes | Target sequence |
| `region_start` / `region_end` | int | Yes | 1-based interval |
| `aso_oligo_length` | int | No | ASO length |

Returns: `mean_unpaired_prob`, `joint_unpaired_prob`.

**Endpoint detail: `/plfold-profiles`**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sequence` | str | Yes | Target sequence |
| `params` | dict | No | `winsize`, `span`, `unpaired_ulength`, `temp_c` |

Returns: `positions`, `unpaired_prob_1nt` per position.

**Endpoint detail: `/inverse-fold`**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `structure` | str | Yes | Dot-bracket structure |
| `start_sequence` | str | No | Initialization hint |
| `params` | dict | No | Search params |

Returns: `best_sequence`, `hamming_distance`, `partition_probability`.

---

## 3. LinearFold Suite (Port 8015)

| Item | Description |
|------|-------------|
| Upstream | [LinearFold/LinearFold](https://github.com/LinearFold/LinearFold.git) |
| Microservice | `microservices/linearfold_service/` |
| Endpoints | `GET /health`, `POST /fold`, `POST /fold/zuker_subopt`, `POST /eval` |
| Backend | Direct C++ binary calls (`linearfold_c`, `linearfold_v`) |

**Agent tool functions**

- `predict_rna_secondary_structure_with_linearfold(filepath)` — beam-search folding
- `evaluate_rna_structure_with_linearfold(filepath)` — energy evaluation of a known structure
- `predict_rna_secondary_structure_with_linearfold_zuker(filepath)` — Zuker subopt enumeration

**Deployment notes**

- Run `cd external_repos/LinearFold && make` to build `bin/linearfold_c` + `bin/linearfold_v`.
- `LINEARFOLD_ROOT` env var can override the repo directory.

---

## 4. CDS Design Tools

### 4.1 LinearDesign (Port 8014)

| Item | Description |
|------|-------------|
| Upstream | [LinearDesignSoftware/LinearDesign](https://github.com/LinearDesignSoftware/LinearDesign.git) |
| Microservice | `microservices/lineardesign_service/` |
| Endpoints | `GET /health`, `POST /generate/cds`, `POST /generate/cds/batch` |
| Agent tools | `design_mrna_cds_with_lineardesign(filepath, lambda_value=0.0, codon_usage_path=None, verbose=False)`  
|  | `design_mrna_cds_batch_with_lineardesign(filepath, lambda_value=0.0, codon_usage_path=None, verbose=False)` |

**Key parameters**

| Parameter | Maps to CLI | Default | Description |
|-----------|-------------|---------|-------------|
| `lambda_value` | `-l, --lambda` | `0.0` | MFE/CAI balance |
| `codon_usage_path` | `-c, --codonusage` | human table | Codon table file |
| `verbose` | `-v, --verbose` | `False` | Verbose logs |

**Deployment notes**

- Run `cd external_repos/LinearDesign && make` to generate `bin/LinearDesign_2D`.
- `LINEARDESIGN_ROOT` env var can override the directory.
- Batch endpoint accepts FASTA or multi-line plain text; each sequence runs independently with shared params.

### 4.2 RNARL (Port 8008)

| Item | Description |
|------|-------------|
| Upstream | [SII-ShenggengLin/RNARL](https://github.com/SII-ShenggengLin/RNARL.git) |
| Microservice | `microservices/rnarl_service/` |
| Environment | `python=3.10` + GPU |
| Endpoints | `GET /health`, `GET /models`, `POST /generate/cds` |
| Agent tool | `design_mrna_cds_with_rnarl(filepath, model_type=...)` |

**7 checkpoints**

| `model_type` | Checkpoint |
|--------------|------------|
| Homo sapiens mRNA | `homo_mrna.pt` |
| Homo sapiens circular RNA | `homo_circ.pt` |
| Arabidopsis thaliana mRNA | `Arabidopsis.pt` |
| Escherichia coli mRNA | `EscherichiaColi.pt` |
| Penicillium chrysogenum mRNA | `PC.pt` |
| Chlamydomonas reinhardtii mRNA | `CR.pt` |
| Thermococcus kodakarensis KOD1 mRNA | `TK.pt` |

**Key notes**

- Weights: `external_repos/RNARL/checkpoints/*.pt` + `esm2_model_t33_650M_UR50D/`
- ESM-2 must use local directory (`local_files_only=True`).
- `.pt` files must be real binary weights (not LFS pointers).
- Max 1308 amino acids.

### 4.3 GEMORNA (Port 8004)

| Item | Description |
|------|-------------|
| Upstream | [RainaBio/GEMORNA](https://github.com/RainaBio/GEMORNA) |
| Microservice | `microservices/gemorna_service/` |
| Environment | `python=3.10` (required due to `.so` ABI) |
| Endpoint | `POST /generate/cds` |
| Agent tool | `design_mrna_cds_with_gemorna(filepath)` |

**Key notes**

- Checkpoints via Git LFS: `external_repos/GEMORNA/checkpoints/*.pt`
- **Do not use Python 3.9** — causes `undefined symbol: PyDescr_IsData`.
- Requires Linux + GPU.

---

## 5. Structure Prediction & Design

### 5.1 RhoFold (Port 8005)

| Item | Description |
|------|-------------|
| Upstream | [ml4bio/RhoFold](https://github.com/ml4bio/RhoFold) |
| Microservice | `microservices/rhofold_service/` |
| Environment | `python=3.7.12` + `pytorch=1.10.2` + `cudatoolkit=11.3.1` |
| Endpoints | `GET /health`, `POST /predict` |
| Agent tool | `predict_rna_tertiary_structure_with_rhofold(filepath, relax_steps=0, checkpoint_path=None, device=None)` |

**Key notes**

- Default `single_seq_pred=true`; no local MSA database required.
- Checkpoint priority search in `external_repos/RhoFold/pretrained/`: `RhoFold_pretrained.pt` → `rhofold_pretrained_params.pt` → `model_20221010_params.pt`.
- **Local-first policy**: if no local weight found, the service errors out instead of auto-downloading from Hugging Face.
- Custom checkpoint and device can be passed via parameters.

### 5.2 RhoDesign (Port 8006)

| Item | Description |
|------|-------------|
| Upstream | [ml4bio/RhoDesign](https://github.com/ml4bio/RhoDesign) |
| Microservice | `microservices/rhodesign_service/` |
| Environment | `python=3.9` + `pytorch=1.12.1` + `cudatoolkit=11.3.1` |
| Endpoints | `GET /health`, `POST /design/from-structure` |
| Agent tool | `design_rna_sequence_with_rhodesign(pdb_filepath)` |

**Key notes**

- Needs `ss_apexp_best.pth` + `no_ss_apexp_best.pth` in `external_repos/RhoDesign/checkpoint/`.
- PyG wheels must match `torch 1.12.1 + cu113` (install from `data.pyg.org`).
- If no PDB provided, defaults to `external_repos/RhoDesign/example/2zh6_B.pdb`.

### 5.3 RiboDiffusion (Port 8021)

| Item | Description |
|------|-------------|
| Upstream | [ml4bio/RiboDiffusion](https://github.com/ml4bio/RiboDiffusion.git) |
| Microservice | `microservices/ribodiffusion_service/` |
| Environment | `python=3.10` + `pytorch 1.13.x` + CUDA |
| Endpoints | `GET /health`, `POST /design/from-pdb` |
| Agent tool | `design_rna_inverse_fold_with_ribodiffusion(pdb_filepath, n_samples=1, sampling_steps=50, checkpoint_name="exp_inf")` |

**Key notes**

- Checkpoints: `external_repos/RiboDiffusion/ckpts/exp_inf.pth` (default) and `exp_inf_large.pth` (more diversity).
- First-time setup: run `bash install_pyg_torch_extensions.sh` after `conda activate ribodiffusion_service_env` to install `torch-scatter` / `torch-sparse` / `torch-cluster`.
- Upstream runs via subprocess `python main.py --PDB_file ...`; weight path is dynamically injected.
- Boolean flags must use `--deterministic` / `--nodeterministic` style.

---

## 6. Ligand Scoring

### 6.1 RNAsmol (Port 8007)

| Item | Description |
|------|-------------|
| Upstream | [hongli-ma/RNAsmol](https://github.com/hongli-ma/RNAsmol) |
| Microservice | `microservices/rnasmol_service/` |
| Environments | `environment.yml` (old cards / CPU) or `environment.gpu.yml` (RTX 4090 etc.) |
| Endpoints | `GET /health`, `POST /score` |
| Agent tool | `score_rna_ligand_binding_with_rnasmol(filepath, smiles, dataset=None, perturbation_type=None, device=None, checkpoint_path=None)` |

**Key notes**

- New GPUs (RTX 4090) **must** use `environment.gpu.yml`.
- Old `torch 1.7.1 + cu102` hangs on new cards.
- Device can be overridden via `RNASMOL_DEVICE` env var.

### 6.2 GerNA-Bind (Port 8010)

| Item | Description |
|------|-------------|
| Upstream | [GENTEL-lab/GerNA-Bind](https://github.com/GENTEL-lab/GerNA-Bind) |
| Microservice | `microservices/gernabind_service/` |
| Environment | `pytorch 2.1.x` + `pytorch-cuda=11.8` |
| Endpoints | `GET /health`, `POST /score`, `POST /predict-binding-site` |
| Agent tool | `score_rna_ligand_binding_with_gernabind(filepath, smiles)` |

**Key notes**

- Checkpoints: `external_repos/GerNA-Bind/Model/Robin_random.pth` (affinity), `Hariboss_Model_baseline.pth` (binding-site).
- Local RNA-FM: `external_repos/GerNA-Bind/Model/RNA-FM_pretrained.pth`.
- If no `pdb_path` provided, auto-calls `rhofold_service` to generate 3D structure.
- Device can be set via `GERNABIND_DEVICE` env var.

### 6.3 EGARPS+ (Port 8023)

| Item | Description |
|------|-------------|
| Upstream | [hzau-liulab/EGARPS](https://github.com/hzau-liulab/EGARPS) |
| Microservice | `microservices/egarps_service/` |
| Environment | `egarps_env` (Python 3.10 + PyTorch 1.12.1 + DGL 1.0.1 + CUDA 11.6) |
| Endpoints | `GET /health`, `POST /score` |
| Agent tool | `score_rna_protein_complex_with_egarps(filepath, academic=False)` |

**Key notes**

- GPU required for inference (hard-coded `cuda` in upstream).
- Non-academic mode (`academic=False`, default) skips DSSR and NACCESS, using zero-padding for missing features. Performance may degrade slightly.
- Academic mode (`academic=True`) requires DSSR and NACCESS licenses.
- ESM2 and RNA-FM checkpoints are cached locally under `external_repos/EGARPS/esm2_models/` and `rna_fm_models/`.
- GHECOM is not available from upstream; a stub script is used to generate zero-valued pocketness features.

### 6.4 ProteinX RNA-Protein Complex Prediction (Port 8022)

| Item | Description |
|------|-------------|
| Upstream | [bytedance/Protenix](https://github.com/bytedance/Protenix) |
| Microservice | `microservices/proteinx_service/` (same service, new `/predict/complex` endpoint) |
| Environment | Same as protein prediction |
| Endpoint | `POST /predict/complex` |
| Agent tool | `predict_rna_protein_complex_with_proteinx(protein_filepath, rna_filepath, num_models=1)` |

**Key notes**

- Submits both `proteinChain` and `rnaChain` to Protenix for joint structure prediction.
- Outputs `ipTM` (interface predicted TM-score) from the best model confidence JSON.
- Used in the RNA aptamer design workflow as a parallel quality metric alongside EGARPS.

### 6.5 RNA-Protein Interface Analysis (Pure Python)

| Item | Description |
|------|-------------|
| Source | In-repo utility (`agent_core/tools.py`) |
| Transport | Pure Python (`python_api`); no microservice, no port |
| Agent tool | `analyze_rna_protein_interface(complex_pdb_filepath, protein_chain_id="A", rna_chain_id="B", contact_cutoff=5.0)` |

**Metrics computed**

| Metric | Method |
|--------|--------|
| `interface_contacts` | Residue pairs with any atom ≤ `contact_cutoff` Å |
| `buried_sasa` | ΔSASA = (protein_SASA + RNA_SASA) − complex_SASA via freesasa |
| `hydrogen_bonds` | Donor-acceptor atoms 2.5–3.5 Å apart |
| `salt_bridges` | Charged residues (Arg/Lys/His vs Asp/Glu) ≤ 4.0 Å apart |
| `interface_area` | Approximated as `buried_sasa × 0.5` |

---

## 7. CRISPR / sgRNA Tools

### 7.1 CRISOT (Port 8011)

| Item | Description |
|------|-------------|
| Upstream | [bm2-lab/CRISOT](https://github.com/bm2-lab/CRISOT.git) |
| Microservice | `microservices/crisot_service/` |
| Environment | Includes `cas-offinder` (Conda) |
| Endpoints | `GET /health`, `POST /score`, `POST /scores`, `POST /spec`, `POST /off-spec`, `POST /rescore`, `POST /optimize`, `POST /crisot-fp`, `POST /gen-fp` |

**Agent tool functions**

- `score_crispr_off_target_with_crisot(filepath, target_sequence)` — single-pair CRISOT-Score
- `score_batch_crispr_off_targets_with_crisot(csv_filepath)` — batch scoring
- `calculate_crispr_specificity_with_crisot(csv_filepath)` — CSV specificity
- `search_crispr_off_targets_with_crisot(filepath, target_sequence, genome_path)` — genome-wide off-target + specificity
- `rescore_sgrnas_with_crisot(txt_filepath, genome_path)` — genome-wide rescore & rank
- `optimize_sgrna_with_crisot(filepath, genome_path)` — sgRNA optimization
- `predict_crispr_off_target_with_crisot_fp(csv_filepath, xgb_model)` — CRISOT-FP XGBoost
- `generate_crispr_fingerprint_with_crisot(sgrna, target_sequence)` — fingerprint encoding

**Key notes**

- `score` / `scores` / `spec` / `crisot-fp` / `gen-fp` do **not** need `cas-offinder`.
- `off-spec` / `rescore` / `optimize` require `cas-offinder` + reference genome FASTA.
- Default genome can be overridden via `CRISOT_DEFAULT_REF_GENOME` env var.
- `crisot-fp` needs `trained_models.zip` extracted to `models/`.
- `optimize` / `rescore` can be slow on large genomes with `mismatches=6`.
- `pandas>=2` compatibility fix already applied.

### 7.2 CRGPT / sgrna_design (Port 8017)

| Item | Description |
|------|-------------|
| Upstream | [bitguolab/sgrna_design](https://github.com/bitguolab/sgrna_design.git) |
| Microservice | `microservices/sgrna_design_service/` |
| Endpoints | `GET /health`, `POST /design` |
| Agent tool | `design_sgrna_handle_with_crgpt(seed_sequence=None, filepath=None, n_samples=...)` |

**Key notes**

- Two sampling modes: `mcmc` (default, requires ViennaRNA) and `naive` (direct `model.generate`).
- `seed_sequence` and `filepath` are mutually exclusive; if neither is provided, a built-in 61-nt wildtype is used.
- Requires `torch>=2.6` due to `pytorch_model.bin` loading safety limits.

---

## 8. siRNA / Antisense Tools

### 8.1 Evitar (Port 8016)

| Item | Description |
|------|-------------|
| Upstream | [dingyaozhang/Evitar](https://github.com/dingyaozhang/Evitar.git) |
| Microservice | `microservices/evitar_service/` |
| Endpoints | `GET /health`, `POST /design` |
| Agent tool | `design_sirna_with_evitar(filepath, mode=..., predict=..., off_target_params=...)` |

**Key notes**

- Upstream `bin/` contains Linux executables; macOS will report `cannot execute binary file`.
- **Linux only**.

---

## 9. Sequence Metrics (Port 8020)

| Item | Description |
|------|-------------|
| Microservice | `microservices/rna_sequence_metrics_service/` |
| Environment | `python=3.10` + FastAPI (no third-party algorithm dependencies) |
| Endpoints | `GET /health`, `POST /gc-content`, `POST /u-content`, `POST /unpaired-fraction` |
| Agent tools | `compute_rna_sequence_gc_content(filepath)`, `compute_rna_sequence_u_content(filepath)`, `compute_dot_bracket_unpaired_fraction(filepath)` |

**GC content**

- Reads sequence from file, normalizes (strip FASTA headers, uppercase, T→U, drop non-AUGC), then computes `gc_content = (G+C)/N`.
- State fields: `sequence_gc_content`, `sequence_gc_length`, `sequence_gc_count`, `sequence_g_count`, `sequence_c_count`.

**U content**

- Reads sequence from file, normalizes (strip FASTA headers, uppercase, T→U, drop non-AUGC), then computes `u_fraction = U_count / N`.
- State fields: `sequence_u_fraction`, `sequence_u_count`, `sequence_u_length`.

**Unpaired fraction**

- Reads dot-bracket string from file (only `. ( ) [ ] { } < >` allowed).
- Computes `unpaired_fraction = count('.') / length`.
- State fields: `dot_bracket_unpaired_fraction`, `dot_bracket_structure_length`, `dot_bracket_dot_count`.

---

## 10. Other Tools

### 10.1 CAI for CDS (Pure Python)

| Item | Description |
|------|-------------|
| Source | [Kazusa Codon Usage Database](https://www.kazusa.or.jp/codon/) |
| Data file | `agent_core/data/codon_usage_kazusa.json` |
| Transport | Pure Python (`python_api`); no microservice, no port |
| Agent tool | `compute_cai_for_cds_sequence(filepath, species="Homo sapiens", custom_codon_table_path=None)` |

**Built-in species (11)**

Human, Mouse, Rat, Fruit fly, Worm, Zebrafish, Arabidopsis, Yeast, E. coli K-12, B. subtilis, Chinese hamster (CHO).

**Key notes**

- Input must be a valid CDS (length multiple of 3; AUGC only after normalization).
- Stop codons (UAA/UAG/UGA) are excluded from the CAI calculation.
- Uses Sharp & Li relative adaptiveness weights computed from Kazusa fractions.
- Custom tables accepted as JSON: `{codon: {aa: str, fraction: float}}`.
- State fields: `cai_for_cds_score`, `cai_for_cds_species`, `cai_for_cds_length_nt`, `cai_for_cds_codon_count`.

### 10.2 codonw-slim (Port 8018)

| Item | Description |
|------|-------------|
| Upstream | [smsaladi/codonw-slim](https://github.com/smsaladi/codonw-slim.git) |
| Microservice | `microservices/codonw_slim_service/` |
| Environment | `python=3.10` + gcc |
| Endpoint | `POST /analyze/cds` |
| Agent tool | `analyze_cds_codon_metrics_with_codonw_slim(filepath)` |

**Exposed metrics**

- Core: CAI, Fop, CBI, Nc (ENC), hydropathy, aromaticity
- Base composition: GC, GC1/2/3, GC3s, GCn3s, silent base usage
- Optional tables: codon_usage, RSCU, dinucleotide, aa_usage, RAAU, bases
- Genetic codes: 0–7; reference species: CAI/CBI 0–2, Fop 0–7

**Key notes**

- **Must run `bash install_codonw_slim.sh` after `conda env create`**.
- Input must be in-frame CDS; trailing non-multiple-of-3 bases are auto-truncated.

### 10.3 BLAST+ (Port 8019)

| Item | Description |
|------|-------------|
| Microservice | `microservices/blast_service/` |
| Environment | `python=3.10` + bioconda `blast` |
| Endpoint | `POST /blastn` |
| Agent tool | `run_blastn_similarity_search(filepath, subject_fasta_path=..., subject_db=..., task=..., evalue=..., word_size=..., max_target_seqs=..., perc_identity=..., strand=..., outfmt=...)` |

**Key notes**

- `subject_fasta_path` (on-the-fly `makeblastdb`) and `subject_db` (existing DB prefix) are **mutually exclusive**.
- Agent layer writes full results to `workspace/blastn_out_*.tsv`.

### 10.4 RNASTOP (Port 8009)

| Item | Description |
|------|-------------|
| Upstream | [SII-ShenggengLin/RNASTOP](https://github.com/SII-ShenggengLin/RNASTOP.git) |
| Microservice | `microservices/rnastop_service/` |
| Environment | `python=3.10` + GPU + `transformers==4.34.0` |
| Endpoint | `POST /predict/stability` |
| Agent tool | `predict_mrna_stability_with_rnastop(filepath, structure=None, loop_type=None)` |

**Key notes**

- Resources: `external_repos/RNASTOP/models/`, `DNABERT6/`, `RNA-FM_pretrained.pth`.
- Server auto-complements ViennaRNA secondary structure, loop type, and graph features if not provided.
- Sequences >1022 nt are truncated.
- Only stability prediction is exposed; beam/MCTS optimization is not connected.

### 10.5 IRESfinder (Port 8013)

| Item | Description |
|------|-------------|
| Upstream | [xiaofengsong/IRESfinder](https://github.com/xiaofengsong/IRESfinder.git) |
| Microservice | `microservices/iresfinder_service/` (Python 3 re-implementation) |
| Environment | `python=3.10` |
| Endpoint | `POST /predict` |
| Agent tool | `predict_putative_ires_with_iresfinder(filepath, mode=0, window_params=...)` |

**Key notes**

- Needs `external_repos/IRESfinder/module/train.data`.
- Input is DNA-normalized (U→T).
- CPU only.

### 10.6 ODesign (Port 8012)

| Item | Description |
|------|-------------|
| Upstream | [OTeam-AI4S/ODesign](https://github.com/OTeam-AI4S/ODesign.git) |
| Microservice | `microservices/odesign_service/` |
| Environment | `python=3.10` + CUDA 12.1 |
| Endpoint | `POST /design/from-json` |
| Agent tool | `run_odesign_inference(input_json_filepath)` |

**Key notes**

- Checkpoints: `external_repos/ODesign/ckpt/odesign_base_na_rigid.pt` + `oinvfold_rna.ckpt`.
- Data files: `external_repos/ODesign/data/components.v20240608.cif` + `.rdkit_mol.pkl`.
- Complex tasks are best prepared with explicit JSON.

---

## 11. Task-Workflow Mapping

There are **20 tasks** with corresponding workflows. Both directories previously had `INDEX.md` files; this table replaces them.

> **Note on routing**: Every task in this table is currently dispatched via **deterministic keyword-based routing** (`router_node` → `specialist_node`). This is an intentional phase-1 design choice to keep tests fast, reproducible, and debuggable. See `ARCHITECTURE.md` §8 for the rationale and the planned migration to LLM-driven routing.

| # | Task | Workflow | Domain |
|---|------|----------|--------|
| 1 | `sirna_duplex_energy` | `sirna_duplex_energy_workflow` | siRNA / antisense |
| 2 | `sirna_design_evitar` | `sirna_design_evitar_workflow` | siRNA / antisense |
| 3 | `rna_secondary_structure_viennarna` | `rna_secondary_structure_viennarna_workflow` | RNA 2° structure |
| 4 | `rna_secondary_structure_linearfold` | `rna_secondary_structure_linearfold_workflow` | RNA 2° structure |
| 5 | `aso_accessibility_viennarna` | `aso_accessibility_viennarna_workflow` | RNA 2° structure |
| 6 | `inverse_folding_viennarna` | `inverse_folding_viennarna_workflow` | RNA 2° structure |
| 7 | `cds_codon_metrics` | `cds_codon_metrics_workflow` | mRNA / CDS |
| 7b | `cai_computation` | `cai_computation_workflow` | mRNA / CDS |
| 8 | `protein_to_cds_design` | `protein_to_cds_design_workflow` | mRNA / CDS |
| 9 | `mrna_stability_prediction` | `mrna_stability_prediction_workflow` | mRNA / CDS |
| 10 | `ires_prediction` | `ires_prediction_workflow` | mRNA / CDS |
| 11 | `blastn_similarity_search` | `blastn_similarity_search_workflow` | mRNA / CDS |
| 12 | `rna_tertiary_structure_prediction` | `rna_tertiary_structure_prediction_workflow` | RNA 3D / design / ligand |
| 13 | `rna_structure_to_sequence_design` | `rna_structure_to_sequence_design_workflow` | RNA 3D / design / ligand |
| 14 | `rna_ligand_scoring` | `rna_ligand_scoring_workflow` | RNA 3D / design / ligand |
| 15 | `odesign_inference` | `odesign_inference_workflow` | RNA 3D / design / ligand |
| 16 | `crispr_offtarget_scoring` | `crispr_offtarget_scoring_workflow` | CRISPR |
| 17 | `crispr_specificity_csv` | `crispr_specificity_csv_workflow` | CRISPR |
| 18 | `crispr_offtarget_search` | `crispr_offtarget_search_workflow` | CRISPR |
| 19 | `crispr_sgrna_optimization` | `crispr_sgrna_optimization_workflow` | CRISPR |
| 20 | `sgrna_handle_design` | `sgrna_handle_design_workflow` | CRISPR |

### Per-task tool chain (Step 1~7)

Every workflow follows the same 7-step template:

1. **Input validation** — validate file existence, sequence length, column names, etc.
2. **Preprocessing** — usually none (handled by server)
3. **Candidate generation** — none for evaluation-only tasks; active for design/optimization tasks
4. **Evaluation** — call the primary tool (often a single HTTP call to a microservice)
5. **Filtering** — none or threshold-based (caller-defined)
6. **Sorting** — often by score / MFE / probability; sometimes none
7. **Formatting** — write back `AgentState` fields and produce file paths / reports

| Task | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Step 6 | Step 7 |
|---|---|---|---|---|---|---|---|
| `sirna_duplex_energy` | validate | none | none | `compute_sirna_duplex_binding_vienna` | none | by MFE | format |
| `sirna_design_evitar` | validate | none | `design_sirna_with_evitar` | none | none | none | write back |
| `rna_secondary_structure_viennarna` | validate | none | none | `predict_rna_secondary_structure` (fallback LinearFold) | none | optional by MFE | format |
| `rna_secondary_structure_linearfold` | validate | none | none | `predict_rna_secondary_structure_with_linearfold` | none | optional by MFE | format |
| `aso_accessibility_viennarna` | validate | none | none | `compute_aso_target_accessibility_vienna` | none | optional by accessibility | format |
| `inverse_folding_viennarna` | validate | none | `inverse_fold_rna_secondary_structure_vienna` | none | none | none | format |
| `cds_codon_metrics` | validate | none | none | `analyze_cds_codon_metrics_with_codonw_slim` | none | optional by CAI | format |
| `cai_computation` | validate | none | none | `compute_cai_for_cds_sequence` | none | none | format |
| `protein_to_cds_design` | validate | none | `design_mrna_cds_*` | optional evaluate | optional filter | optional rerank | format |
| `mrna_stability_prediction` | validate | none | none | `predict_mrna_stability_with_rnastop` | none | optional sort | format |
| `ires_prediction` | validate | none | none | `predict_putative_ires_with_iresfinder` | optional threshold | by max_score | format |
| `blastn_similarity_search` | validate | none | none | `run_blastn_similarity_search` | optional filter | none | format |
| `rna_tertiary_structure_prediction` | validate | none | none | `predict_rna_tertiary_structure_with_rhofold` | optional threshold | none | format |
| `rna_structure_to_sequence_design` | validate | none | `design_rna_sequence_with_rhodesign` | optional evaluate | optional filter | optional sort | format |
| `rna_ligand_scoring` | validate | none | none | RNAsmol / GerNA-Bind | optional threshold | by probability | format |
| `odesign_inference` | validate | none | `run_odesign_inference` | none | none | none | format |
| `crispr_offtarget_scoring` | validate | normalize | none | `score_crispr_off_target_with_crisot` | none | by score | format |
| `crispr_specificity_csv` | validate | none | none | `calculate_crispr_specificity_with_crisot` | none | by spec | format |
| `crispr_offtarget_search` | validate | none | none | `search_crispr_off_targets_with_crisot` | by count | by spec | format |
| `crispr_sgrna_optimization` | validate | none | `optimize_sgrna_with_crisot` | built-in | by available | none | format |
| `sgrna_handle_design` | validate | normalize | `design_sgrna_handle_with_crgpt` | built-in | none | by NN score | format |
| `rna_aptamer_design` | validate | none | `build_odesign_aptamer_input_json` | `run_odesign_inference` + `predict_rna_protein_complex_with_proteinx` + `analyze_rna_protein_interface` | none | none | format |
| `protein_structure_prediction` | validate | none | none | `predict_protein_structure_with_proteinx` | none | none | format |
| `protein_hotspot_identification` | validate | parse | none | `identify_protein_binding_hotspots` | by relSASA | by patch size | format |
| `structure_alignment` | validate | parse | none | `score_structure_alignment` | none | by TM-score | format |

---

## 12. Standard Workflow Step Pattern

All workflows share the same conceptual pipeline. When documenting a new workflow, follow this schema:

```markdown
## Workflow: <task_name>

### Purpose
One-line description.

### Prerequisites
- Microservice running on port XXXX
- Input format: ...

### Step 1: Input validation
Validate file existence, length limits, required columns, etc.

### Step 2: Preprocessing
(Usually "none" — handled by the microservice.)

### Step 3: Candidate generation
(For design/optimization tasks: call the design tool. For evaluation tasks: "none".)

### Step 4: Evaluation
Call the primary tool(s). List exact tool name(s) and key parameters.

### Step 5: Filtering
Apply thresholds or skip.

### Step 6: Sorting / Ranking
Sort by score, MFE, probability, etc.

### Step 7: Formatting
Write results back to AgentState and produce output file paths / reports.
```
