# RNAsmol RNA-Ligand Binding Scoring

> **Version**: v0.3.0  
> **Last updated**: 2026-09-25  
> **Upstream**: [hongli-ma/RNAsmol](https://github.com/hongli-ma/RNAsmol)  
> **Microservice**: `microservices/rnasmol_service/` (Port 8007)  
> **Conda Env**: `rnasmol_service_gpu_env` (GPU, activated by `microservices/rnasmol_service/start_gpu.sh` — the platform auto-start default since 2026-09-25); CPU variant `rnasmol_service_env` via `start.sh` (`environment.yml`), retired from the reference machine.

---

## 1. Overview

RNAsmol scores RNA-ligand interactions with an MCNN_GCN classifier: the ligand SMILES is converted to a molecular graph diffused through a Personalized-PageRank (PPR) top-k matrix, and the RNA sequence is integer-encoded and processed by a multi-channel CNN. The service returns the positive-class (binding) probability together with the raw logits.

---

## 2. Capabilities

- Score a single RNA sequence against a single ligand SMILES
- Checkpoint auto-selection from `dataset` / `perturbation_type` hints
- CPU or CUDA inference (CPU is the packaged default)

---

## 3. Input

### Agent Tool Interface

```python
score_rna_ligand_binding_with_rnasmol(
    filepath: str,                                # Path to a file containing the RNA sequence (not raw text)
    smiles: str,                                  # Ligand SMILES
    service_url: str = "http://127.0.0.1:8007/score",
    checkpoint_path: Optional[str] = None,        # Explicit checkpoint override
    dataset: Optional[str] = None,                # e.g. "pdb", "robin"
    perturbation_type: Optional[str] = None,      # e.g. "molperturbation"
    device: Optional[str] = None,                 # e.g. "cpu", "cuda:0"
) -> dict
```

### Service Endpoint

`POST http://127.0.0.1:8007/score`

### Request Fields (`ScoreRequest`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rna_sequence` | `str` | ✅ | RNA sequence to score. FASTA-like text is accepted (blank lines and `>` header lines are dropped). Case is preserved — see §7 |
| `smiles` | `str` | ✅ | Ligand SMILES string scored by RNAsmol |
| `checkpoint_path` | `str \| null` | ❌ | Optional checkpoint override. Defaults to service auto-discovery (§5) |
| `dataset` | `str \| null` | ❌ | Training-dataset hint for checkpoint auto-selection, e.g. `pdb` (RCSB PDB), `robin` (ROBIN) |
| `perturbation_type` | `str \| null` | ❌ | Data-perturbation hint for checkpoint auto-selection, e.g. `molperturbation`, `netperturbation`, `rnaperturbation` |
| `device` | `str \| null` | ❌ | Optional PyTorch device string such as `cuda:0` or `cpu` |

---

## 4. Output

### Response Fields (`ScoreResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `rna_sequence` | `str` | Normalized RNA sequence echoed back |
| `smiles` | `str` | SMILES echoed back (stripped) |
| `probability_positive` | `float` | Positive-class (binding) probability |
| `predicted_label` | `int` | Predicted binary label (0 or 1) |
| `raw_logits` | `List[float]` | Raw model logits `[logit_0, logit_1]` |
| `checkpoint_path` | `str` | Resolved checkpoint actually loaded |
| `device` | `str` | Device used for inference |
| `dataset` | `str \| null` | Dataset hint reflected back |
| `perturbation_type` | `str \| null` | Perturbation hint reflected back |
| `model` | `str` | Always `"RNAsmol"` |

The agent wrapper additionally sets `input_filepath` (and re-attaches `smiles` / `rna_sequence`) on the return dict before handing it to the workflow.

---

## 5. Checkpoint Auto-Selection

`_resolve_checkpoint_path()` in `microservices/rnasmol_service/main.py` resolves the model weights in this order:

1. **Explicit `checkpoint_path`** request field (relative paths resolve against the repo root).
2. **`RNASMOL_CHECKPOINT_PATH`** environment variable.
3. **Dataset / perturbation glob match** against `external_repos/RNAsmol/saved_model/*.pt`, whose filenames follow `{dataset}_bothaug_{perturbation_type}.pt`. Patterns are tried in order: `{dataset}_bothaug_{perturbation_type}.pt` → `{dataset}_bothaug_*.pt` → `*_{perturbation_type}.pt`.
4. **Alphabetical first** of all remaining `saved_model/*.pt`.

Git-LFS pointer files are rejected at every step. The default checkpoint is preloaded at service startup, so a passed health check means scoring is immediately ready.

---

## 6. Deployment

### 6.1 Start Microservice

```bash
cd rna_agent_system/microservices/rnasmol_service
bash start.sh        # CPU: rnasmol_service_env, pins RNASMOL_DEVICE=cpu
bash start_gpu.sh    # GPU: rnasmol_service_gpu_env (torch 2.1), RNASMOL_DEVICE=cuda:0
```

Service listens on `http://0.0.0.0:8007`. `start.sh` pins `RNASMOL_DEVICE=cpu` because the bundled env ships PyTorch 1.7.1 (max sm_75), which cannot run kernels on RTX 4090-class (sm_89) GPUs and otherwise stalls the first request on PTX JIT; CPU inference is milliseconds-fast for this model.

### 6.2 Health Check

```bash
curl http://127.0.0.1:8007/health
```

---

## 7. Preprocessing Fidelity (do not "fix")

The service is a **verbatim port** of `external_repos/RNAsmol/rnasmol/preprocessing.py`. Two properties are load-bearing because the shipped checkpoints were trained on tensors built exactly this way:

1. **Case-sensitive RNA vocab.** Lowercase `a/c/g/u` encode modified bases (vocab tokens 5–8); uppercase `A/C/G/U` are tokens 1–4; anything else maps to token 9. The sequence is **not** uppercased and **no** T→U conversion is applied.
2. **Upstream adjacency quirk.** `mol_to_graph` zips only the first two directed edge pairs and shifts each index by −1 when building the molecular adjacency, and `get_top_k_matrix` keeps its negative-slice semantics. These quirks are reproduced bit-for-bit on purpose — a "corrected" full adjacency silently degrades the model.

Other preprocessing facts:

- RNA targets are **zero-padded or truncated to exactly 500 nt**.
- SMILES that produce empty / bond-less / degenerate molecular graphs are rejected with HTTP 400.
- PPR matrix uses `alpha=0.1`; top-k sparsification uses `k=5`.

**Verified parity (2026-08-11)**: post-fix the service reproduces the official upstream `test.py` reference metrics exactly — `robin_molperturbation` test AUROC **0.9744**, `pdb_molperturbation` test AUROC **0.9828**; decoy case studies rank the true binder at 2/1601 (FMN_ribocil) and 7/265 (MALAT1_furamidine). Boundary panel: `experiments/results/rnasmol_boundary_panel.json`.
