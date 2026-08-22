# EGARPS+ RNA-Protein Complex Scoring

> **Version**: v0.1.0  
> **Last updated**: 2026-07-06  
> **Upstream**: [hzau-liulab/EGARPS](https://github.com/hzau-liulab/EGARPS)  
> **Microservice**: `microservices/egarps_service/` (Port 8023)  
> **Conda Env**: `egarps_env` (activated by `microservices/egarps_service/start.sh`).

---

## 1. Overview

EGARPS+ evaluates the quality of RNA-protein complex structures using a graph-learning model that integrates intermolecular and intramolecular modules with biophysically inspired descriptors. It outputs a probability score indicating how likely the provided structure is a native (correct) complex.

---

## 2. Capabilities

- Score single RNA-protein complex PDB structures
- Ensemble inference over 7 model checkpoints (3 academic weights + 3 full weights + 1 mini weight)
- Native-structure probability estimation via sigmoid-averaged ensemble predictions

---

## 3. Input

### Agent Tool Interface

```python
score_rna_protein_complex_with_egarps(
    filepath: str,          # Absolute or workspace-relative path to PDB file
    academic: bool = False, # True = full mode (requires DSSR + NACCESS licenses)
    service_url: str = "http://127.0.0.1:8023/score",
) -> dict
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filepath` | `str` | ✅ | Path to the input PDB file containing the RNA-protein complex |
| `academic` | `bool` | ❌ | `True` enables full feature mode (DSSP + DSSR + NACCESS + GHECOM). `False` (default) uses reduced mode where DSSR, NACCESS features are zero-padded |
| `service_url` | `str` | ❌ | REST endpoint for the EGARPS+ microservice |

---

## 4. Output

| Field | Type | Description |
|-------|------|-------------|
| `complex_id` | `str` | Identifier extracted from the PDB filename |
| `native_probability` | `float` | Probability (0–1) that the structure is native |
| `academic` | `bool` | Whether academic mode was used for the run |
| `model` | `str` | Always `"EGARPS+"` |
| `pdb_path` | `str` | Resolved absolute path to the input PDB |

---

## 5. Runtime Requirements

### 5.1 Hardware
- **GPU required** — EGARPS+ hard-codes `cuda` in upstream `predict.py` and `feature_residue.py`
- CUDA runtime must be compatible with PyTorch 1.12.1+cu116 / DGL 1.0.1.cu116
- The conda environment ships `cudatoolkit=11.6` for backward compatibility

### 5.2 Third-Party Software

| Software | Mode | Status | Note |
|----------|------|--------|------|
| DSSP (mkdssp) | Always | ✅ Installed | Protein secondary structure |
| PyMOL | Always | ✅ Installed | Chain selection / atom identification |
| msms | Always | ✅ Installed | Molecular surface computation |
| ESM2 | Always | ✅ Local | Cached at `external_repos/EGARPS/esm2_models/` |
| RNA-FM | Always | ✅ Local | Cached at `external_repos/EGARPS/rna_fm_models/` |
| GHECOM | Always | ⚠️ Stub | Official binary unavailable; stub returns zero-valued pocketness features |
| DSSR | Academic only | ❌ Missing | Requires license; skipped in non-academic mode |
| NACCESS | Academic only | ❌ Missing | Requires license; skipped in non-academic mode |

### 5.3 Model Weights
- 7 `.pth` files (~6.9 GB total) under `external_repos/EGARPS/weights/`
  - `a1w1.pth`, `a1w2.pth`, `a1w3.pth` — non-academic ensemble
  - `p1w1.pth`, `p1w2.pth`, `p1w3.pth` — academic ensemble
  - `m1w1.pth` — mini single-model

---

## 6. Deployment

### 6.1 Environment Setup

```bash
cd rna_agent_system/external_repos/EGARPS
conda env create -f environment_fixed.yml   # or manual install per README
conda activate egarps_env
```

### 6.2 Start Microservice

```bash
cd rna_agent_system/microservices/egarps_service
bash start.sh
```

Service listens on `http://0.0.0.0:8023`.

### 6.3 Direct CLI Usage (without agent)

```bash
conda activate egarps_env
cd rna_agent_system/external_repos/EGARPS
python scripts/predict.py -non-academic /path/to/complex.pdb
# Output written to result.txt in the same directory as the PDB
```

---

## 7. Known Limitations

1. **GPU-only inference** — Cannot run on CPU due to hard-coded `.cuda()` calls in upstream.
2. **Non-academic performance** — Zero-padding DSSR/NACCESS features may cause slight accuracy degradation (acknowledged by upstream authors).
3. **GHECOM stub** — Pocketness features are all zeros because the official GHECOM binary is no longer publicly downloadable.
4. **CUDA compatibility** — Requires CUDA driver ≥ 11.6. Tested on RTX 4090 with CUDA 12.8 driver (backward-compatible).
5. **Long runtime** — First-run ESM2/RNA-FM embedding generation is slow (~minutes per complex) even on fast GPUs.
