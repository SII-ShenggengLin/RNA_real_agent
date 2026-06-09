# Tools Reference

> **Scope**: per-tool specs, microservice deployment notes, and port registry.
> **Last updated**: 2026-06-01

---

## Table of Contents

1. [Port Registry](#1-port-registry)
2. [RNA Secondary Structure](#2-rna-secondary-structure)
3. [CDS Design](#3-cds-design)
4. [Tertiary Structure & Inverse Folding](#4-tertiary-structure--inverse-folding)
5. [Ligand Scoring](#5-ligand-scoring)
6. [RNA-Protein Complex](#6-rna-protein-complex)
7. [CRISPR / sgRNA](#7-crispr--sgrna)
8. [siRNA / Antisense](#8-sirna--antisense)
9. [Sequence & CDS Metrics](#9-sequence--cds-metrics)
10. [Other Tools](#10-other-tools)

---

## 1. Port Registry

| Port | Service directory | Tool name | Domain | Validation |
|------|-------------------|-----------|--------|------------|
| 8003 | `microservices/viennarna_fold/` | ViennaRNA | Secondary structure / cofold / accessibility / inverse folding | ✅ Linux |
| 8004 | `microservices/gemorna_service/` | GEMORNA | CDS + UTR design | ✅ Linux GPU |
| 8005 | `microservices/rhofold_service/` | RhoFold | Tertiary structure prediction | ✅ Linux GPU |
| 8006 | `microservices/rhodesign_service/` | RhoDesign | Structure → sequence design | ✅ Linux GPU |
| 8007 | `microservices/rnasmol_service/` | RNAsmol | RNA–ligand scoring | ✅ Linux GPU |
| 8008 | `microservices/rnarl_service/` | RNARL | CDS design (7 species) | ✅ Linux GPU |
| 8009 | `microservices/rnastop_service/` | RNASTOP | mRNA stability | ✅ Linux GPU |
| 8010 | `microservices/gernabind_service/` | GerNA-Bind | RNA–ligand scoring + binding-site | ✅ Linux GPU |
| 8011 | `microservices/crisot_service/` | CRISOT | CRISPR off-target / specificity / optimization | ✅ Linux |
| 8012 | `microservices/odesign_service/` | ODesign | Biomolecule design | ✅ Linux GPU |
| 8013 | `microservices/iresfinder_service/` | IRESfinder | IRES prediction | ✅ Linux |
| 8014 | `microservices/lineardesign_service/` | LinearDesign | CDS design | ✅ Linux |
| 8015 | `microservices/linearfold_service/` | LinearFold | Secondary structure (beam search) | ✅ Linux |
| 8016 | `microservices/evitar_service/` | Evitar | siRNA design | ✅ Linux |
| 8017 | `microservices/sgrna_design_service/` | CRGPT | sgRNA handle design | ✅ Linux GPU |
| 8018 | `microservices/codonw_slim_service/` | codonw-slim | Codon metrics | ✅ Linux |
| 8019 | `microservices/blast_service/` | BLAST+ | Nucleotide similarity | ✅ Linux |
| 8020 | `microservices/rna_sequence_metrics_service/` | RNA metrics | GC / U / unpaired fraction | ✅ Linux |
| 8021 | `microservices/ribodiffusion_service/` | RiboDiffusion | 3D → sequence (diffusion) | ✅ Linux GPU |
| 8022 | `microservices/proteinx_service/` | ProteinX | Protein structure + RNA-protein complex | ✅ Linux GPU |
| 8023 | `microservices/egarps_service/` | EGARPS | RNA-protein complex scoring | ✅ Linux GPU |
| 8024 | `microservices/bowtie2_service/` | Bowtie2 | Short-sequence alignment | ✅ Linux |

> New tools should use ports starting from **8025**.

---

## 2. RNA Secondary Structure

### 2.1 ViennaRNA Suite (Port 8003)

| Upstream | [ViennaRNA/ViennaRNA](https://github.com/ViennaRNA/ViennaRNA.git) |
| Endpoints | `GET /health`, `POST /fold`, `POST /sirna-duplex`, `POST /aso-accessibility`, `POST /plfold-profiles`, `POST /inverse-fold` |
| Backend | Prefer RNAlib (`import RNA`), fallback to CLI |

**Agent tools**

| Tool | Input | Output |
|------|-------|--------|
| `predict_rna_secondary_structure` | `filepath` | `structure`, `mfe_kcal_per_mol` |
| `compute_sirna_duplex_binding_vienna` | `filepath` (2 FASTA records) | `structure` (with `&`), `mfe_kcal_per_mol` |
| `compute_rna_rna_interaction_vienna` | `filepath` (2 FASTA records) | `structure`, `mfe_kcal_per_mol` |
| `compute_aso_target_accessibility_vienna` | `filepath`, `region_start`, `region_end` | `mean_unpaired_prob` |
| `predict_rna_local_accessibility_profile_vienna` | `filepath` | per-position unpaired probs |
| `inverse_fold_rna_secondary_structure_vienna` | `filepath` (dot-bracket + optional hint) | `best_sequence` |

**Notes**
- Default install via Conda bioconda `viennarna`; no compilation needed.
- `POST /plfold-profiles` default limit: **≤8000 nt**.

### 2.2 LinearFold Suite (Port 8015)

| Upstream | [LinearFold/LinearFold](https://github.com/LinearFold/LinearFold.git) |
| Endpoints | `GET /health`, `POST /fold`, `POST /fold/zuker_subopt`, `POST /eval` |
| Backend | Direct C++ binary calls |

**Agent tools**

| Tool | Input | Output |
|------|-------|--------|
| `predict_rna_secondary_structure_with_linearfold` | `filepath`, optional `constraints` | `structure`, `mfe` |
| `evaluate_rna_structure_with_linearfold` | `filepath` | energy evaluation |
| `predict_rna_secondary_structure_with_linearfold_zuker` | `filepath` | subopt structures |

**Notes**
- Run `cd external_repos/LinearFold && make` to build binaries.
- `LINEARFOLD_ROOT` env var can override the repo directory.

---

## 3. CDS Design

### 3.1 LinearDesign (Port 8014)

| Upstream | [LinearDesignSoftware/LinearDesign](https://github.com/LinearDesignSoftware/LinearDesign.git) |
| Endpoints | `GET /health`, `POST /generate/cds`, `POST /generate/cds/batch` |

**Agent tools**

| Tool | Key parameters |
|------|----------------|
| `design_mrna_cds_with_lineardesign` | `lambda_value` (MFE/CAI balance), `codon_usage_path`, `verbose` |
| `design_mrna_cds_batch_with_lineardesign` | Same params; accepts FASTA or multi-line text |

**Notes**
- Run `cd external_repos/LinearDesign && make` to generate `bin/LinearDesign_2D`.
- `LINEARDESIGN_ROOT` env var can override the directory.

### 3.2 RNARL (Port 8008)

| Upstream | [SII-ShenggengLin/RNARL](https://github.com/SII-ShenggengLin/RNARL.git) |
| Endpoints | `GET /health`, `GET /models`, `POST /generate/cds` |

**Agent tool**: `design_mrna_cds_with_rnarl(protein_sequence, model_type="Homo sapiens mRNA", ...)`

**7 checkpoints**

| `model_type` | Checkpoint |
|--------------|------------|
| `homo_mrna` | Homo sapiens mRNA |
| `homo_circ` | Homo sapiens circular RNA |
| `Arabidopsis` | Arabidopsis thaliana |
| `EscherichiaColi` | E. coli |
| `PC` | Penicillium chrysogenum |
| `CR` | Chlamydomonas reinhardtii |
| `TK` | Thermococcus kodakarensis KOD1 |

**Notes**
- Weights: `external_repos/RNARL/checkpoints/*.pt` + `esm2_model_t33_650M_UR50D/`
- Max 1308 amino acids.

### 3.3 GEMORNA (Port 8004)

| Upstream | [RainaBio/GEMORNA](https://github.com/RainaBio/GEMORNA) |
| Endpoints | `POST /generate/cds`, `POST /generate/5utr`, `POST /generate/3utr`, `POST /predict/5utr_mrl`, `POST /predict/3utr_stability` |

**Agent tools**

| Tool | Purpose |
|------|---------|
| `design_mrna_cds_with_gemorna` | CDS design |
| `design_5utr_with_gemorna` | 5'UTR design |
| `design_3utr_with_gemorna` | 3'UTR design |
| `predict_5utr_mrl_with_gemorna` | 5'UTR mean ribosomal load prediction |
| `predict_3utr_stability_with_gemorna` | 3'UTR stability prediction |

**Notes**
- Checkpoints via Git LFS: `external_repos/GEMORNA/checkpoints/*.pt`
- **Python 3.10 only** — `.so` ABI requirement.
- Requires Linux + GPU.

---

## 4. Tertiary Structure & Inverse Folding

### 4.1 RhoFold (Port 8005)

| Upstream | [ml4bio/RhoFold](https://github.com/ml4bio/RhoFold) |
| Endpoint | `POST /predict` |

**Agent tool**: `predict_rna_tertiary_structure_with_rhofold(filepath, relax_steps=0, ...)`

**Notes**
- Default `single_seq_pred=true`; no local MSA database required.
- **Local-first policy**: if no local weight found, the service errors out instead of auto-downloading.

### 4.2 RhoDesign (Port 8006)

| Upstream | [ml4bio/RhoDesign](https://github.com/ml4bio/RhoDesign) |
| Endpoint | `POST /design/from-structure` |

**Agent tool**: `design_rna_sequence_with_rhodesign(pdb_filepath, ...)`

**Notes**
- Needs `ss_apexp_best.pth` + `no_ss_apexp_best.pth`.
- PyG wheels must match `torch 1.12.1 + cu113`.

### 4.3 RiboDiffusion (Port 8021)

| Upstream | [ml4bio/RiboDiffusion](https://github.com/ml4bio/RiboDiffusion.git) |
| Endpoint | `POST /design/from-pdb` |

**Agent tool**: `design_rna_inverse_fold_with_ribodiffusion(pdb_filepath, n_samples=1, ...)`

**Notes**
- Checkpoints: `exp_inf.pth` (default) and `exp_inf_large.pth`.
- First-time setup: run `bash install_pyg_torch_extensions.sh` after `conda activate`.

---

## 5. Ligand Scoring

### 5.1 RNAsmol (Port 8007)

| Upstream | [hongli-ma/RNAsmol](https://github.com/hongli-ma/RNAsmol) |
| Endpoint | `POST /score` |

**Agent tool**: `score_rna_ligand_binding_with_rnasmol(filepath, smiles, ...)`

**Notes**
- New GPUs (RTX 4090) **must** use `environment.gpu.yml`.
- Device can be overridden via `RNASMOL_DEVICE` env var.

### 5.2 GerNA-Bind (Port 8010)

| Upstream | [GENTEL-lab/GerNA-Bind](https://github.com/GENTEL-lab/GerNA-Bind) |
| Endpoints | `POST /score`, `POST /predict-binding-site` |

**Agent tool**: `score_rna_ligand_binding_with_gernabind(filepath, smiles, ...)`

**Notes**
- Checkpoints: `Robin_random.pth` (affinity) + `Hariboss_Model_baseline.pth` (binding-site).
- If no `pdb_path` provided, auto-calls `rhofold_service` to generate 3D structure.

---

## 6. RNA-Protein Complex

### 6.1 EGARPS (Port 8023)

| Upstream | [hzau-liulab/EGARPS](https://github.com/hzau-liulab/EGARPS) |
| Endpoint | `POST /score` |

**Agent tool**: `score_rna_protein_complex_with_egarps(filepath, academic=False)`

**Notes**
- GPU required.
- Non-academic mode (`academic=False`, default) skips DSSR and NACCESS, using zero-padding.
- Academic mode requires DSSR and NACCESS licenses.

### 6.2 ProteinX (Port 8022)

| Upstream | [bytedance/Protenix](https://github.com/bytedance/Protenix) |
| Endpoints | `POST /predict`, `POST /predict/complex` |

**Agent tools**

| Tool | Purpose |
|------|---------|
| `predict_protein_structure_with_proteinx` | Protein structure prediction |
| `predict_rna_protein_complex_with_proteinx` | RNA-protein complex prediction |

**Notes**
- Outputs `ipTM` (interface predicted TM-score) from confidence JSON.

### 6.3 Interface Analysis (Pure Python)

**Agent tool**: `analyze_rna_protein_interface(complex_pdb_filepath, protein_chain_id="A", rna_chain_id="B")`

**Metrics computed**

| Metric | Method |
|--------|--------|
| `interface_contacts` | Residue pairs with any atom ≤ 5.0 Å |
| `buried_sasa` | ΔSASA via freesasa |
| `hydrogen_bonds` | Donor-acceptor atoms 2.5–3.5 Å |
| `salt_bridges` | Charged residues ≤ 4.0 Å |

---

## 7. CRISPR / sgRNA

### 7.1 CRISOT (Port 8011)

| Upstream | [bm2-lab/CRISOT](https://github.com/bm2-lab/CRISOT.git) |
| Endpoints | `GET /health`, `POST /score`, `POST /scores`, `POST /spec`, `POST /off-spec`, `POST /rescore`, `POST /optimize`, `POST /crisot-fp`, `POST /gen-fp` |

**Agent tools**

| Tool | Needs cas-offinder |
|------|-------------------|
| `score_crispr_off_target_with_crisot` | ❌ |
| `calculate_crispr_specificity_with_crisot` | ❌ |
| `search_crispr_off_targets_with_crisot` | ✅ |
| `optimize_sgrna_with_crisot` | ✅ |
| `score_batch_crispr_off_targets_with_crisot` | ❌ |
| `rescore_sgrnas_with_crisot` | ✅ |
| `predict_crispr_off_target_with_crisot_fp` | ❌ |
| `generate_crispr_fingerprint_with_crisot` | ❌ |

**Notes**
- `cas-offinder` must be on PATH for genome-wide operations.
- Default genome via `CRISOT_DEFAULT_REF_GENOME` env var.

### 7.2 CRGPT / sgrna_design (Port 8017)

| Upstream | [bitguolab/sgrna_design](https://github.com/bitguolab/sgrna_design.git) |
| Endpoints | `GET /health`, `POST /design`, `POST /score` |

**Agent tools**

| Tool | Description |
|------|-------------|
| `design_sgrna_handle_with_crgpt` | Generate handle sequences from seed |
| `score_sgrna_handle_with_crgpt` | Re-score a handle sequence |

**Notes**
- Modes: `mcmc` (default, requires ViennaRNA) and `naive`.
- `seed_sequence` and `filepath` are mutually exclusive.

---

## 8. siRNA / Antisense

### 8.1 Evitar (Port 8016)

| Upstream | [dingyaozhang/Evitar](https://github.com/dingyaozhang/Evitar.git) |
| Endpoint | `POST /design` |

**Agent tool**: `design_sirna_with_evitar(filepath, mode=..., predict=..., off_target_params=...)`

**Notes**
- Linux only (upstream `bin/` contains Linux executables).

---

## 9. Sequence & CDS Metrics

### 9.1 RNA Sequence Metrics (Port 8020)

| Endpoint | Tool | State fields |
|----------|------|--------------|
| `POST /gc-content` | `compute_rna_sequence_gc_content` | `sequence_gc_*` (5 fields) |
| `POST /u-content` | `compute_rna_sequence_u_content` | `sequence_u_*` (3 fields) |
| `POST /unpaired-fraction` | `compute_dot_bracket_unpaired_fraction` | `dot_bracket_*` (3 fields) |

### 9.2 CAI for CDS (Pure Python)

**Agent tool**: `compute_cai_for_cds_sequence(filepath, species="Homo sapiens", ...)`

**Built-in species (11)**: Human, Mouse, Rat, Fruit fly, Worm, Zebrafish, Arabidopsis, Yeast, E. coli K-12, B. subtilis, CHO.

**Notes**
- Pure Python; no microservice.
- Uses Sharp & Li relative adaptiveness weights from Kazusa tables.
- Stop codons excluded from calculation.

### 9.3 codonw-slim (Port 8018)

**Agent tool**: `analyze_cds_codon_metrics_with_codonw_slim(filepath)`

**Metrics**: CAI, Fop, CBI, Nc (ENC), GC, GC1/2/3, hydropathy, aromaticity, and optional tables.

**Notes**
- **Must run `bash install_codonw_slim.sh` after `conda env create`.**
- Input must be in-frame CDS.

### 9.4 Junction Codon Shuffler (Pure Python)

**Agent tool**: `shuffle_cds_junction_codons(filepath, junction_end, codon_count=6, num_variants=8, species="Homo sapiens", seed=None)`

Generate synonymous-codon variants at the N- or C-terminus of a CDS to alter local RNA secondary structure at module junctions (5'UTR-CDS or CDS-3'UTR) without changing the encoded protein.

**Parameters**
| Parameter | Description |
|-----------|-------------|
| `junction_end` | ``n_terminus`` (affects 5'UTR-CDS junction) or ``c_terminus`` (affects CDS-3'UTR junction) |
| `codon_count` | Number of terminal codons to shuffle (1--12, default 6) |
| `num_variants` | Number of variant sequences to generate (1--32, default 8) |
| `species` | Reference species for codon-usage weighting |
| `seed` | Optional RNG seed for reproducibility |

**Returns**
- `original_sequence`, `junction_end`, `shuffled_region_start/end`
- `variants`: list of `{sequence, cai_score, changed_codons, changes}`

**Notes**
- Pure Python; no microservice.
- Synonymous choices are weighted by species codon usage (Kazusa tables) so high-CAI variants are naturally favored.
- Used by the BMC coordinator as a fine-grained local control for junction structure optimization.

---

## 10. Other Tools

### 10.1 BLAST+ (Port 8019)

**Agent tool**: `run_blastn_similarity_search(filepath, subject_fasta_path=..., subject_db=..., task=..., evalue=..., ...)`

**Notes**
- `subject_fasta_path` and `subject_db` are **mutually exclusive**.

### 10.2 RNASTOP (Port 8009)

**Agent tool**: `predict_mrna_stability_with_rnastop(filepath, structure=None, loop_type=None)`

**Notes**
- **Hard limit**: 512 nt (DNABERT encoder maximum).
- Sequences >1022 nt are truncated.

### 10.3 IRESfinder (Port 8013)

**Agent tool**: `predict_putative_ires_with_iresfinder(filepath, mode=0, ...)`

**Notes**
- Needs `external_repos/IRESfinder/module/train.data`.
- Input is DNA-normalized (U→T).

### 10.4 ODesign (Port 8012)

**Agent tool**: `run_odesign_inference(input_json_filepath)`

**Notes**
- Checkpoints: `odesign_base_na_rigid.pt` + `oinvfold_rna.ckpt`.
- Complex tasks are best prepared with explicit JSON.

### 10.5 Structure Utilities (Pure Python)

| Tool | Description |
|------|-------------|
| `extract_rna_sequence_from_cif` | Extract RNA sequence from mmCIF file |
| `build_odesign_aptamer_input_json` | Build ODesign aptamer input JSON |
| `identify_protein_binding_hotspots` | Identify binding hotspots using freesasa + DBSCAN |
| `score_structure_alignment` | Compute RMSD + TM-score between two PDBs |

---

*For workflow deep-dives, see [`WORKFLOWS.md`](WORKFLOWS.md).  
For architecture and core module APIs, see [`ARCHITECTURE.md`](ARCHITECTURE.md).*
