# Tools Reference

> **Scope**: per-tool specs, microservice deployment notes, and port registry.
> **Last updated**: 2026-08-22 (41 tools, all production)

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
    - 10.5 [Bowtie2](#105-bowtie2-port-8024)
    - 10.6 [Structure Utilities](#106-structure-utilities-pure-python)

---

## 1. Port Registry

| Port | Service directory | Tool name | Domain | Validation |
|------|-------------------|-----------|--------|------------|
| 8003 | `microservices/viennarna_fold/` | ViennaRNA | Secondary structure / cofold / accessibility / inverse folding | ✅ Linux |
| 8004 | `microservices/gemorna_service/` | GEMORNA | CDS + UTR design | ✅ Linux GPU |
| 8005 | `microservices/rhofold_service/` | RhoFold | Tertiary structure prediction | ✅ Linux GPU |
| 8006 | `microservices/rhodesign_service/` | RhoDesign | Structure → sequence design | ✅ Linux GPU |
| 8007 | `microservices/rnasmol_service/` | RNAsmol | RNA–ligand scoring | ✅ Linux (CPU default; GPU via `start_gpu.sh`) |
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
| 8019 | `microservices/blast_service/` | BLAST+ | Nucleotide similarity | ✅ Linux |
| 8020 | `microservices/rna_sequence_metrics_service/` | RNA metrics | GC / U / unpaired fraction | ✅ Linux |
| 8021 | `microservices/ribodiffusion_service/` | RiboDiffusion | 3D → sequence (diffusion) | ✅ Linux GPU |
| 8022 | `microservices/proteinx_service/` | ProteinX | Protein structure + RNA-protein complex | ✅ Linux GPU |
| 8023 | `microservices/egarps_service/` | EGARPS | RNA-protein complex scoring | ✅ Linux GPU |
| 8024 | `microservices/bowtie2_service/` | Bowtie2 | Short-sequence alignment | ✅ Linux |

> New tools should use ports starting from **8025**.
>
> **Note**: Bowtie2 (port 8024) is declared in `SirnaDesignWorkflow.required_capabilities`, so the CLI pre-flight auto-starts it via `microservices/bowtie2_service/start.sh` (base conda env provides the `bowtie2` binary).

---

## 2. RNA Secondary Structure

### 2.1 ViennaRNA Suite (Port 8003)

| Upstream | [ViennaRNA/ViennaRNA](https://github.com/ViennaRNA/ViennaRNA.git) |
| Endpoints | `GET /health`, `POST /fold`, `POST /sirna-duplex`, `POST /aso-accessibility`, `POST /plfold-profiles`, `POST /inverse-fold`, `POST /rnaup` |
| Backend | Prefer RNAlib (`import RNA`), fallback to CLI |

**Agent tools**

| Tool | Input | Output |
|------|-------|--------|
| `predict_rna_secondary_structure` | `filepath` | `structure`, `mfe_kcal_per_mol` |
| `compute_sirna_duplex_binding_vienna` | `filepath` (2 FASTA records) | `structure` (with `&`), `mfe_kcal_per_mol`; optional `dg_sense_5p_end_kcal_per_mol` / `dg_antisense_5p_end_kcal_per_mol` / `asymmetry_kcal_per_mol` (terminal 5-bp NN end asymmetry, higher = antisense 5′ end less stable = better guide loading) |
| `compute_rna_rna_interaction_vienna` | `filepath1`, `filepath2` | `interaction_energy`, `interaction_structure`, `raw_stdout`, `sequence1`, `sequence2` |
| `compute_aso_target_accessibility_vienna` | `filepath`, `region_start`, `region_end` | `mean_unpaired_prob_single_nt`, `joint_unpaired_prob_stretch_ending_at_region_end` |
| `predict_rna_local_accessibility_profile_vienna` | `filepath` | per-position unpaired probs |
| `inverse_fold_rna_secondary_structure_vienna` | `filepath` (dot-bracket + optional hint) | `best_sequence` |

**Notes**
- Default install via Conda bioconda `viennarna`; no compilation needed.
- `POST /plfold-profiles` default limit: **≤8000 nt**.

### 2.2 LinearFold Suite (Port 8015)

| Upstream | [LinearFold/LinearFold](https://github.com/LinearFold/LinearFold.git) |
| Endpoints | `GET /health`, `POST /fold` |
| Backend | Direct C++ binary calls |

**Agent tools**

| Tool | Input | Output |
|------|-------|--------|
| `predict_rna_secondary_structure_with_linearfold` | `filepath`, optional `constraints` | `structure`, `mfe` |

**Notes**
- Run `cd external_repos/LinearFold && make` to build binaries.
- `LINEARFOLD_ROOT` env var can override the repo directory.
- **MFE sign convention**: upstream `linearfold_c` (CONTRAfold) prints a raw
  Viterbi score where *higher = more stable*. The service negates it so that
  `mfe` from both backends always means *more negative = more stable*
  (consistent with LinearFold-V and ViennaRNA).

---

## 3. CDS Design

### 3.1 LinearDesign (Port 8014)

| Upstream | [LinearDesignSoftware/LinearDesign](https://github.com/LinearDesignSoftware/LinearDesign.git) — pinned to fork [SII-ShenggengLin/LinearDesign](https://github.com/SII-ShenggengLin/LinearDesign.git) @ `ef10882` (junction-aware C++ patch + memory-guard wrapper; see DEPLOYMENT §1.4) |
| Endpoints | `GET /health`, `POST /generate/cds` |

**Agent tools**

| Tool | Key parameters |
|------|----------------|
| `design_mrna_cds_with_lineardesign` | `lambda_value` (MFE/CAI balance), `codon_usage_path`, `verbose` |

**Notes**
- Run `cd external_repos/LinearDesign && make` to generate `bin/LinearDesign_2D.real`, then restore the memory-guard wrapper as `bin/LinearDesign_2D` (the wrapper caps the address space via `ulimit -v`, default 100 GiB, override with `LINEARDESIGN_MAX_RSS_KB`). Never expose the raw binary as `bin/LinearDesign_2D`: unbounded runs previously exhausted the 200 GiB container cgroup and the OOM killer SIGKILLed unrelated processes (2026-08-06).
- The service also rejects oversized proteins up front (`LINEARDESIGN_MAX_AA`, default 1800 aa; DP-lattice memory grows ~quadratically, ~7.5 GiB at 500 aa) so over-budget jobs fail fast instead of burning memory until the wrapper cap aborts them.
- `LINEARDESIGN_ROOT` env var can override the directory.
- Removed 2026-08-18: `design_mrna_cds_batch_with_lineardesign`, `design_mrna_cds_junction_aware_with_lineardesign` (P2 pre-registered NO-GO — the junction-aware objective never repaired fragment-fold burial; `experiments/results/junction_integrated_optimizer_summary.json`) and `shuffle_cds_junction_codons` (junction auto-repair strategy falsified, DECISIONS.md (b)).

### 3.2 RNARL (Port 8008)

| Upstream | [SII-ShenggengLin/RNARL](https://github.com/SII-ShenggengLin/RNARL.git) |
| Endpoints | `GET /health`, `GET /models`, `POST /generate/cds` |

**Agent tool**: `design_mrna_cds_with_rnarl(protein_sequence, model_type="Homo sapiens mRNA", ...)`

**7 checkpoints**

| `model_type` | Checkpoint |
|--------------|------------|
| `Homo sapiens mRNA` | Human mRNA |
| `Homo sapiens circular RNA` | Human circular RNA |
| `Arabidopsis thaliana mRNA` | Arabidopsis thaliana |
| `Escherichia coli mRNA` | E. coli |
| `Penicillium chrysogenum mRNA` | Penicillium chrysogenum |
| `Chlamydomonas reinhardtii mRNA` | Chlamydomonas reinhardtii |
| `Thermococcus kodakarensis KOD1 mRNA` | Thermococcus kodakarensis KOD1 |

**Notes**
- The canonical list of `model_type` values and their checkpoint filenames is maintained in `agent_core/constants/species.py` (`RNARL_MODEL_TYPES_LIST`, `RNARL_MODEL_TYPE_TO_CHECKPOINT`).
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

| Upstream | [ml4bio/RhoFold](https://github.com/ml4bio/RhoFold) — pinned to fork [SII-ShenggengLin/RhoFold](https://github.com/SII-ShenggengLin/RhoFold.git) @ `6761653` (local-checkpoint-first inference patch; see DEPLOYMENT §1.4) |
| Endpoint | `POST /predict` |

**Agent tool**: `predict_rna_tertiary_structure_with_rhofold(filepath, relax_steps=0, ...)`

**Notes**
- Default `single_seq_pred=true`; no local MSA database required.
- **Local-first policy**: if no local weight found, the service errors out instead of auto-downloading.

### 4.2 RhoDesign (Port 8006)

| Upstream | [ml4bio/RhoDesign](https://github.com/ml4bio/RhoDesign) — pinned to fork [SII-ShenggengLin/RhoDesign](https://github.com/SII-ShenggengLin/RhoDesign.git) @ `0dc7c54` (reproducible-seed inference patch; see DEPLOYMENT §1.4) |
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
- `start.sh` pins `RNASMOL_DEVICE=cpu`: the bundled `rnasmol_service_env` ships
  PyTorch 1.7.1 (max sm_75), which cannot run kernels on RTX 4090 (sm_89) and
  otherwise stalls the first request for minutes on PTX JIT. CPU inference is
  milliseconds-fast for this model. For real GPU inference use `start_gpu.sh`
  (`rnasmol_service_gpu_env`, torch 2.1) with `RNASMOL_DEVICE=cuda:0`.
- The default checkpoint is preloaded at service startup, so a passed health
  check means scoring is immediately ready.
- 2026-08-11 preprocessing-fidelity fix: the
  service now preserves the case-sensitive RNA vocab (lowercase `a/c/g/u` =
  modified bases, vocab tokens 5-8) and replicates upstream
  `rnasmol/preprocessing.py` verbatim, including its adjacency / top-k slicing
  quirks — do not "correct" them, the shipped checkpoints were trained on
  these tensors. Post-fix the service reproduces the official upstream
  `test.py` reference metrics exactly (`robin_molperturbation` test AUROC
  0.9744, `pdb_molperturbation` test AUROC 0.9828). Request/response schema
  unchanged; see `docs/tools/score_rna_ligand_binding_with_rnasmol.md`.

### 5.2 GerNA-Bind (Port 8010)

| Upstream | [GENTEL-lab/GerNA-Bind](https://github.com/GENTEL-lab/GerNA-Bind) |
| Endpoints | `POST /score` (agent tool); `POST /predict-binding-site` exists in the microservice but has no agent wrapper yet |

**Agent tool**: `score_rna_ligand_binding_with_gernabind(filepath, smiles, ...)`

**Notes**
- Checkpoints: `Robin_random.pth` (affinity) + `Hariboss_Model_baseline.pth` (binding-site).
- If no `pdb_path` provided, auto-calls `rhofold_service` (port 8005) to generate the 3D structure. `RnaSmallMoleculeInteractionWorkflow.required_capabilities` therefore declares `predict_rna_tertiary_structure_with_rhofold`, so the CLI pre-flight starts RhoFold automatically.
- First-time GPU setup: run `bash microservices/gernabind_service/install_pyg_gpu.sh` after creating the Conda environment.

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
- The service `start.sh` activates the `base` Conda environment. The upstream dependencies are expected to be installed in an environment named `egarps_env` (per `start.sh` comments), but the launcher currently uses `base` for uvicorn startup.

### 6.2 ProteinX (Port 8022)

| Upstream | [bytedance/Protenix](https://github.com/bytedance/Protenix) |
| Endpoints | `POST /predict/protein`, `POST /predict/complex` |

**Agent tools**

| Tool | Purpose |
|------|---------|
| `predict_protein_structure_with_proteinx` | Protein structure prediction |
| `predict_rna_protein_complex_with_proteinx` | RNA-protein complex prediction |

**Notes**
- Outputs `ipTM` (interface predicted TM-score) from confidence JSON.
- Long Protenix subprocess calls run in a background thread (`asyncio.to_thread`) so the `/health` endpoint stays responsive during inference.
- The service is currently single-worker; concurrent prediction requests are serialized by the single event-loop thread.

### 6.3 Interface Analysis (Pure Python)

**Agent tool**: `analyze_rna_protein_interface(complex_pdb_filepath, protein_chain_id="A", rna_chain_id="B")`

**Metrics computed**

| Metric | Method |
|--------|--------|
| `interface_contacts` | Residue pairs with any atom ≤ 5.0 Å |
| `buried_sasa` | ΔSASA via freesasa, computed on the two selected chains only (extra chains/waters in the file are excluded; 2026-08-21 fix — the old whole-file formula returned 0.0 for any multi-chain PDB) |
| `hydrogen_bonds` | Donor-acceptor atoms 2.5–3.5 Å |
| `salt_bridges` | Protein Arg/Lys/His nitrogen ≤ 4.0 Å from an RNA phosphate oxygen (OP1/OP2), unique residue pairs (2026-08-21 fix — the old protein Asp/Glu pairing never fires across a protein-RNA interface) |

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

**Agent tool**: `design_sirna_with_evitar(filepath, mode="existing", predict="predsi", off_target=False, p3utr_path=..., transcriptome_path=..., weight_path=..., pmcuff=..., umcuff=..., mircuff=...)`

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

**Built-in species (11)**: `arabidopsis`, `bsubtilis`/`b. subtilis`, `cho`, `ecoli`/`e. coli`, `fly`, `human`, `mouse`, `rat`, `worm`, `yeast`, `zebrafish`. Values are case-insensitive and map to the Kazusa codon-usage tables. The canonical aliases and mappings are maintained in `agent_core/constants/species.py` (`CAI_SPECIES_ALIASES`, `CAI_CANONICAL_SPECIES`).

**Notes**
- Pure Python; no microservice.
- Uses Sharp & Li relative adaptiveness weights from Kazusa tables.
- Stop codons excluded from calculation.

(9.3 codonw-slim and 9.4 junction codon shuffler removed 2026-08-18 together
with their tools — no production consumer; junction auto-repair strategy
falsified, DECISIONS.md (b).)

---

## 10. Other Tools

### 10.1 BLAST+ (Port 8019)

**Agent tool**: `run_blastn_similarity_search(filepath, subject_fasta_path=..., subject_db=..., task=..., evalue=..., ...)`

**Notes**
- `subject_fasta_path` and `subject_db` are **mutually exclusive**.

### 10.2 RNASTOP (Port 8009)

| Endpoint | `POST /predict/stability` |

**Agent tool**: `predict_mrna_stability_with_rnastop(filepath, structure=None, loop_type=None)`

**Notes**
- **Hard limit**: 512 nt (model encoder maximum). Longer sequences are truncated
  to the first 512 nt by the service (`truncated=True`); user-supplied
  `structure` / `loop_type` are truncated alongside, and dangling brackets from
  truncation are sanitized to unpaired before any native ViennaRNA call.
- Default checkpoint: `best_model_weights_withoutDNABERT` (the DNABERT6
  pretrained weights are not shipped in this repository).

### 10.3 IRESfinder (Port 8013)

| Endpoint | `POST /predict` |

**Agent tool**: `predict_putative_ires_with_iresfinder(filepath, mode=0, ...)`

**Notes**
- Needs `external_repos/IRESfinder/module/train.data`.
- Input is DNA-normalized (U→T).

### 10.4 ODesign (Port 8012)

| Endpoint | `POST /design/from-json` |

**Agent tool**: `run_odesign_inference(input_json_filepath)`

**Notes**
- Checkpoints: `odesign_base_na_rigid.pt` + `oinvfold_rna.ckpt`.
- Complex tasks are best prepared with explicit JSON.

### 10.5 Bowtie2 (Port 8024)

| Endpoint | `POST /align` |

**Agent tool**: `run_bowtie2_short_alignment(filepath, subject_fasta_path=..., subject_index=..., mode="local", k=50, score_min="G,20,8")`

**Notes**
- Provide exactly one of `subject_fasta_path` or `subject_index`.
- `mode` can be `local` (allows soft-clipping, preferred for short oligos) or `end-to-end`.
- Auto-started by the CLI service pre-flight (declared by `SirnaDesignWorkflow`).

### 10.6 Structure Utilities (Pure Python)

| Tool | Description |
|------|-------------|
| `extract_rna_sequence_from_cif` | Extract RNA sequence from mmCIF file |
| `build_odesign_aptamer_input_json` | Build ODesign aptamer input JSON |
| `identify_protein_binding_hotspots` | Identify binding hotspots using freesasa + DBSCAN |
| `score_structure_alignment` | Compute RMSD + TM-score between two PDBs |

---

*For workflow deep-dives, see [`WORKFLOWS.md`](WORKFLOWS.md).  
For architecture and core module APIs, see [`ARCHITECTURE.md`](ARCHITECTURE.md).*
