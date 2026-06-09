# Change Log

> **Scope**: locked interface changes and major workflow introductions.
> **Last updated**: 2026-06-09

---

## 2026-06-09 — GEMORNA UTR Evaluators Restored in Full-Length mRNA Design

**Fixed** (`agent_core/workflows/full_length_mrna_design.py`):

| Evaluator | Tool | Previous Behaviour | Current Behaviour |
|-----------|------|-------------------|-------------------|
| `UTR5MrlEvaluator` | `predict_5utr_mrl_with_gemorna` (8004) | Skipped (hard-coded empty dict) | **Real invocation** |
| `UTR3StabilityEvaluator` | `predict_3utr_stability_with_gemorna` (8004) | Skipped (hard-coded empty dict) | **Real invocation** |

**Impact**:
- `evaluate()` now produces non-`None` values for `utr5_predicted_mrl` and `utr3_predicted_stability` when the GEMORNA microservice is available.
- Borda-count ranking (`cds_component` + `utr5_mrl` + `utr3_stability`) and BMC weighted scoring now use actual GEMORNA predictions instead of penalising all candidates equally.
- `required_capabilities` already listed both tools; no interface version bump required.

**Benchmark updates**:

- All 22 `02_full_length_mrna_design_*.json` task files: `expected_tool_chain` updated to include `predict_5utr_mrl_with_gemorna` and `predict_3utr_stability_with_gemorna`.
- `generate_tasks.py` updated accordingly.

**Files touched**: `workflows/full_length_mrna_design.py`, benchmark task JSONs, `generate_tasks.py`.

---

## 2026-06-09 — U Content Evaluation Added to mRNA Workflows

**New evaluator** (`agent_core/workflows/evaluators.py`):

| Component | Description |
|-----------|-------------|
| `UContentEvaluator` | Wraps `compute_rna_sequence_u_content` (port 8020). Returns `u_fraction` and `u_count`. Always enabled (no toggle flag). |

**Workflow changes**:

| Workflow | Change |
|----------|--------|
| `MrnaCdsDesignWorkflow` | `CompositeEvaluator` now includes `UContentEvaluator`. `required_capabilities` adds `"compute_rna_sequence_u_content"`. Summary output includes `U=xxx`. |
| `FullLengthMrnaDesignWorkflow` | `SubWorkflowEvaluator` key_map remaps `"u_fraction" → "cds_u_fraction"`. `_u_content_evaluator` evaluates full-length sequence directly. Summary output includes `cdsU=xxx` and `fullU=xxx`. `required_capabilities` adds `"compute_rna_sequence_u_content"`. |

**Supporting changes**:

- `agent_core/sequence_utils.py`: `compute_mrna_metric_bundle()` now accepts optional `u_fraction` parameter.
- Benchmark task JSONs (`01_mrna_cds_design_*`, `02_full_length_mrna_design_*`): `expected_tool_chain` updated to include `"compute_rna_sequence_u_content"`.
- Tests: `test_u_content_capability` added to both comprehensive test suites; workflow Layer-2 assertions verify `u_fraction` / `cds_u_fraction` / `full_u_fraction` presence.

**Notes**:
- U content is a **reference metric only**; it does **not** enter either scoring formula (`total_score = -mfe + codon_count * log(CAI)` for CDS, Borda-count / BMC weighted sum for full-length).

**Files touched**: `workflows/evaluators.py`, `workflows/mrna_cds_design.py`, `workflows/full_length_mrna_design.py`, `sequence_utils.py`, benchmark task JSONs, comprehensive tests.

---

## 2026-05-28 — RNA Aptamer Design Workflow v1.0.0 + BMC Type-II

**New Layer-2 workflow** (`agent_core/workflows/rna_aptamer_design.py`):

| Component | Description |
|-----------|-------------|
| `RnaAptamerDesignWorkflow` | `BaseDomainWorkflow`: hotspot identification → ODesign ligand generation → RhoFold + EGARPS + ProteinX complex evaluation |
| `AptamerCoordinator` | BMC Type-II deterministic coordinator with 6 threshold-based diagnostic rules |
| `RnaAptamerDesignLLMCritic` | LLM-driven critic for user-intent alignment and scoring weight adjustment |

**New tools** (port 8022 ProteinX, port 8023 EGARPS, port 8012 ODesign):

| Tool | Purpose |
|------|---------|
| `predict_protein_structure_with_proteinx` | Protein structure prediction |
| `predict_rna_protein_complex_with_proteinx` | RNA-protein complex prediction |
| `analyze_rna_protein_interface` | Interface contact / SASA / H-bond analysis |
| `identify_protein_binding_hotspots` | Hotspot identification via freesasa + DBSCAN |
| `score_rna_protein_complex_with_egarps` | Complex quality scoring |
| `run_odesign_inference` | Aptamer sequence generation |
| `build_odesign_aptamer_input_json` | ODesign input builder |

**Files touched**: `workflows/rna_aptamer_design.py`, `workflows/coordinator.py`, `workflows/registry.py`, `tools.py`, `tool_specs.py`

---

## 2026-05-20 — RNA Secondary/Tertiary Structure Design Workflows v1.0.0

**New Layer-2 workflows**:

| Workflow | Pipeline |
|----------|----------|
| `RnaSecondaryStructureDesignWorkflow` | ViennaRNA inverse folding → RNAfold validation → structure-distance scoring |
| `RnaTertiaryStructureDesignWorkflow` | RhoDesign / RiboDiffusion 3D→sequence inverse folding |

**Files touched**: `workflows/rna_secondary_structure_design.py`, `workflows/rna_tertiary_structure_design.py`, `workflows/registry.py`, `runner.py`

---

## 2026-05-15 — IRES Prediction Workflow v1.0.0

**New Layer-2 workflow** (`agent_core/workflows/ires_prediction.py`):

| Component | Description |
|-----------|-------------|
| `IresPredictionWorkflow` | IRESfinder-based putative IRES element prediction |
| `IresPredictionLLMCritic` | Quality gate with progressive threshold relaxation |

**Files touched**: `workflows/ires_prediction.py`, `workflows/registry.py`, `runner.py`

---

## 2026-05-10 — Full-Length mRNA Design v2.0.0 + BMC Type-I

**Major update** (`agent_core/workflows/full_length_mrna_design.py`):

| Component | Description |
|-----------|-------------|
| `FullLengthCoordinator` | BMC Type-I deterministic coordinator with 8 threshold-based diagnostic rules for junction quality |
| `JunctionEvaluator` | Dedicated evaluator for 5'UTR-CDS and CDS-3'UTR junction MFE, GC diff, AUG/Kozak burial |
| `shuffle_cds_junction_codons` | New pure-Python tool for synonymous codon shuffling at junctions |

**Files touched**: `workflows/full_length_mrna_design.py`, `workflows/coordinator.py`, `workflows/evaluators.py`, `workflows/scoring.py`, `tools.py`, `tool_specs.py`

---

## 2026-05-08 — sgRNA Design Workflow v1.0.0

**New Layer-2 workflow** (`agent_core/workflows/sgrna_design.py`):

| Component | Description |
|-----------|-------------|
| `SgRnaDesignInput` | Pydantic input with `seed_sequence`, `guide_sequence`, `target_sequence`, `sampling_mode` |
| `SgRnaDesignWorkflow` | `BaseDomainWorkflow`: generate → evaluate → score → rank |
| `score_sgrna_candidate` | Combined score: `weight_nn_score * nn_component + weight_crisot_score * crisot_component` |
| `SgRnaCritic` | Quality gate with progressive threshold relaxation |

**Files touched**: `workflows/sgrna_design.py`, `workflows/__init__.py`, `workflows/registry.py`, `runner.py`

---

## 2026-05-07 — siRNA Design Workflow v1.1.0

**Changes** (`agent_core/workflows/sirna_design.py`):

| Component | Before | After |
|-----------|--------|-------|
| `OFF_TARGET_THRESHOLD` | `0` | `3` |
| `SPECIFICITY_THRESHOLD` | `0.95` | `0.25` |
| `MAX_RETRIES` | `3` | `2` |
| Retry strategy | Tighten GC only | Progressive: tighten BLAST identity + GC; relax off-target to 5 on final retry |

**Files touched**: `workflows/sirna_design.py`, `workflows/__init__.py`, `workflows/registry.py`, `tests/test_sirna_design_workflow.py`

---

## 2026-05-04 — RNA Aptamer Design Tools v0.2.0

**Added**: ProteinX complex prediction & interface analysis.

| Tool | Transport |
|------|-----------|
| `predict_rna_protein_complex_with_proteinx` | HTTP |
| `analyze_rna_protein_interface` | Pure Python (biopython + freesasa) |

**Scoring simplification**: `total_score = EGARPS + (RhoFold_pLDDT / 100) + ipTM`

---

## 2026-05-01 — RNA Aptamer Design Tools v0.1.0

**Initial aptamer toolkit**:

| Tool | Transport |
|------|-----------|
| `extract_rna_sequence_from_cif` | Pure Python |
| `build_odesign_aptamer_input_json` | Pure Python |
| `predict_protein_structure_with_proteinx` | HTTP |
| `identify_protein_binding_hotspots` | Pure Python |
| `score_structure_alignment` | Pure Python |

---

## 2026-04-28 — RNA Sequence U Content v0.1.0

Locked interface for `compute_rna_sequence_u_content`. See `INTERFACE_LOCKS.md` §5.

---

## 2026-04-28 — CAI for CDS v0.1.0

Locked interface for `compute_cai_for_cds_sequence`. Pure Python calculation using Kazusa tables. See `INTERFACE_LOCKS.md` §6.

---

## 2026-04-25 — GC Content Interface v0.1.0

Locked interface for `compute_rna_sequence_gc_content`. See `INTERFACE_LOCKS.md` §3.

---

## 2026-04-25 — Dot-Bracket Unpaired Fraction v0.1.0

Locked interface for `compute_dot_bracket_unpaired_fraction`. See `INTERFACE_LOCKS.md` §4.

---

## 2026-04-24 — LinearDesign Interface v0.2.0

Locked interface for `design_mrna_cds_with_lineardesign` (single + batch). See `INTERFACE_LOCKS.md` §7.

---

*For interface lock details and sync checklists, see [`INTERFACE_LOCKS.md`](INTERFACE_LOCKS.md).*
