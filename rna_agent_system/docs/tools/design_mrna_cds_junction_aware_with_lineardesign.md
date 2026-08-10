# Junction-Aware LinearDesign CDS Design

> **Version**: v0.1.0  
> **Last updated**: 2026-08-04  
> **Upstream**: [LinearDesignSoftware/LinearDesign](https://github.com/LinearDesignSoftware/LinearDesign.git) (local JUNCTION-PATCH, 2026-08)  
> **Microservice**: `microservices/lineardesign_service/` (Port 8014)  
> **Conda Env**: `lineardesign_service_env` (activated by `microservices/lineardesign_service/start.sh`).

---

## 1. Overview

Junction-aware CDS design: the junction-side slices of the fixed 5'/3' UTRs are
folded **together with the CDS as one sequence** (pseudo-codon flanks), and base
pairs newly formed inside the two junction windows are penalized by `w_jun`
(kcal/mol per pair) inside the LinearDesign CKY objective. The goal is a CDS
whose termini stay unpaired with (and around) the UTR junctions at generation
time, instead of post-hoc repair.

Requires the patched `bin/LinearDesign_2D` binary (see
`docs/change_logs/2026-08-04_lineardesign_junction_patch.md`). With both flanks
empty the tool degenerates to the legacy `design_mrna_cds_with_lineardesign`
behavior (4-argument binary call, penalty not applied).

---

## 2. Capabilities

- CDS design with fixed UTR context folded globally (flank5 + CDS + flank3)
- Junction-window pair penalty (`junction_weight`) applied inside the design
  objective at every pair-forming CKY transition (forward + backtrace)
- CDS-only metrics alongside full-construct output (`cds_sequence`, `cds_cai`,
  `junction_window_pair_count`, `mfe_thermo`)

---

## 3. Input

### Agent Tool Interface

```python
design_mrna_cds_junction_aware_with_lineardesign(
    filepath: str,            # Workspace file containing the protein sequence
    protein_sequence: str | None = None,   # Explicit override for filepath
    service_url: str = "http://127.0.0.1:8014/generate/cds_junction_aware",
    lambda_value: float = 0.0,
    utr5_flank: str | None = None,
    utr3_flank: str | None = None,
    junction_weight: float = 0.0,
    junction_window_nt: int = 20,
    flank_nt: int = 21,
    codon_usage_path: str | None = None,
    verbose: bool = False,
) -> dict
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filepath` | `str` | ✅ | Workspace file path containing the input protein sequence (overridden by `protein_sequence` when given) |
| `protein_sequence` | `str` | ❌ | Explicit protein sequence; takes precedence over the file content |
| `service_url` | `str` | ❌ | REST endpoint of the junction-aware LinearDesign microservice |
| `lambda_value` | `float ≥ 0` | ❌ | LinearDesign λ balancing MFE and CAI (default 0.0) |
| `utr5_flank` | `str` | ❌ | 5' UTR flank (RNA or DNA alphabet); the junction-side `flank_nt` nt are used |
| `utr3_flank` | `str` | ❌ | 3' UTR flank; the junction-side `flank_nt` nt are used |
| `junction_weight` | `float ≥ 0` | ❌ | w_jun: penalty in kcal/mol per newly formed pair touching a junction window; 0 disables the penalty |
| `junction_window_nt` | `int > 0` | ❌ | Half-width (nt) of the two junction windows (default 20) |
| `flank_nt` | `int` | ❌ | Junction-side flank length per side; multiple of 3 and ≥ 3 (default 21) |
| `codon_usage_path` | `str` | ❌ | Optional codon usage CSV path (defaults to the human table in the LinearDesign repo) |
| `verbose` | `bool` | ❌ | Verbose LinearDesign output |

### Flank slicing rules (service-side)

- Flanks are normalized (uppercase, `T→U`); non-ACGU characters → HTTP 422.
- 5' flank: the **last** `flank_nt` nt (junction side) are used; 3' flank: the
  **first** `flank_nt` nt.
- Shorter flanks fall back to the largest multiple-of-3 length available;
  fewer than 3 usable nt → HTTP 422.
- The used slices are echoed back in `utr5_flank` / `utr3_flank`.

---

## 4. Output

| Field | Type | Description |
|-------|------|-------------|
| `generated_sequence` | `str` | Full-construct RNA (flank5 + CDS + flank3); equals the CDS alone in zero-flank mode |
| `full_construct_sequence` | `str` | Alias of `generated_sequence` |
| `cds_sequence` | `str` | CDS region with flanks stripped |
| `structure` | `str` | Full-construct dot-bracket structure |
| `mfe` | `float` | **CKY objective value** = thermodynamic MFE + `junction_weight × junction_window_pair_count` (equals the thermodynamic MFE when `junction_weight == 0` or no flanks) |
| `mfe_thermo` | `float` | **Thermodynamic MFE** = `mfe − junction_weight × junction_window_pair_count` when flanks are present; equals `mfe` in zero-flank mode |
| `cai_score` / `cds_cai` | `float` | CAI of the CDS region only |
| `junction_window_pair_count` | `int` | Pairs in `structure` with ≥1 endpoint in W1 = `[max(0, L5−w), L5+w)` or W2 = `[L5+Lcds−w, L5+Lcds+w)` (full-construct 0-based coordinates; same windows the C++ penalty uses) |
| `utr5_flank` / `utr3_flank` | `str` | Actually used junction-side flank slices |
| `junction_weight` / `junction_window_nt` / `flank_nt` | — | Echoes of the effective parameters |
| `lambda_value` | `float` | Echo of λ |
| `codon_usage_path` | `str` | Codon usage table actually used |
| `model` | `str` | Always `"LinearDesign"` |
| `input_filepath` / `output_filepath` | `str` | Workspace paths (wrapper saves the full construct) |
| `raw_output` / `stderr` | `str` | Raw LinearDesign stdout / stderr |

> **Key semantics**: `mfe` is the value the optimizer maximized against (more
> negative = better objective), **not** the pure thermodynamic MFE whenever
> `junction_weight > 0`. Use `mfe_thermo` for biophysics; use `mfe` to compare
> against the CKY objective.

---

## 5. Runtime Requirements

- CPU only (LinearDesign CKY beam search; no GPU).
- **Memory profile (measured 2026-08-04, cgroup-capped host)**: peak RSS scales
  steeply with construct length — HER2 (1255 aa + 42 nt flanks) ≈ **47 GiB**,
  Beta-galactosidase (1024 aa) ≈ 32 GiB. On a 200 GiB cgroup host keep
  **concurrency ≤ 2** for ≥1000 aa proteins (8-way concurrency was OOM-killed).
- Runtime: ~0.5–16 min per protein in the 110–1255 aa range at λ = 2.0
  (measured: Insulin 9.5 s, Influenza HA ~150 s, Beta-gal ~530 s, HER2 ~920 s).

---

## 6. Deployment

The workflow pre-flight (`agent_core/services/service_manager.py`) auto-starts
port 8014 via `microservices/lineardesign_service/start.sh` — no manual
launcher needed. Direct curl example:

```bash
curl -s -X POST http://127.0.0.1:8014/generate/cds_junction_aware \
  -H 'Content-Type: application/json' \
  -d '{
    "protein_sequence": "MELAALCRWGLLLALLPPGAASTQVCTGTD",
    "lambda_value": 2.0,
    "utr5_flank": "AGGGGGAGGCGUGAGAGAAAG",
    "utr3_flank": "UGUAAAUGUAAAUGUAAAUGU",
    "junction_weight": 1.0
  }'
```

The binary must be rebuilt after any `external_repos/LinearDesign/src` change:
`cd external_repos/LinearDesign && make`.

---

## 7. Known Limitations

1. **P2 acceptance NO-GO (2026-08-04)** — the pre-registered 72-cell evaluation
   (`experiments/junction_integrated_optimizer_eval.py`, summary
   `experiments/results/junction_integrated_optimizer_summary.json`) shows the
   global-fold window penalty clears window pairs in the optimizer's own fold
   (median pair count 43 → 0 as w_jun goes 0 → 2) but does **not** repair
   AUG/Kozak burial as measured by the workflow's `JunctionEvaluator` (isolated
   40-nt fragment fold): hard-target repair rate ≤ 2/7 at every weight.
   Mechanism: penalty/metric coordinate mismatch — the fragment fold still
   self-hairpins the CDS-terminal 20 nt even when global window pairs are zero.
   **The tool is kept as a registered capability but is NOT wired into any
   workflow.**
2. **Degenerate arm caveat** — at `junction_weight = 0` with flanks present the
   flanks still participate in the fold (argc == 8 path), so output is NOT
   byte-identical to the legacy no-flank endpoint; it is deterministic
   (repeated identical calls return identical CDSs).
3. **Memory** — see §5; large proteins need concurrency limits.
4. **Local patch** — the junction mode only exists in the locally patched
   binary (`JUNCTION-PATCH (2026-08)` markers); upstream LinearDesign has no
   such interface.

---

## 8. Interface Lock

> **v0.1.0** — Any field addition/removal must be synchronized with:
> - `microservices/lineardesign_service/main.py` :: `LinearDesignJunctionAwareRequest` / `LinearDesignJunctionAwareResponse`
> - `agent_core/tools.py` :: `LinearDesignCdsJunctionAwareInput` / `design_mrna_cds_junction_aware_with_lineardesign`
> - `agent_core/tool_specs.py` :: `LinearDesignCdsJunctionAwareOutput` + ToolSpec registration
> - `agent_core/services/service_manager.py` :: `CAPABILITY_SERVICE_MAP` (8014)
> - `docs/INTERFACE_LOCKS.md` §21
> - `docs/TOOLS.md` §3.1
