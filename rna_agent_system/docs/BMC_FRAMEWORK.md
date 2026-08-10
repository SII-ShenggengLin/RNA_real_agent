# Bounded Multi-Module Coordination (BMC) Framework

> **Scope**: design motivation, conceptual foundations, and execution strategy of the BMC framework, covering both Type-I (Physical Assembly) and Type-II (Functional Coupling) instantiations.
> **Last updated**: 2026-08-10

---

## Table of Contents

1. [What is BMC?](#1-what-is-bmc)
2. [What Does "Bounded" Mean?](#2-what-does-bounded-mean)
3. [Type-I vs. Type-II: Two Modes of Module Coupling](#3-type-i-vs-type-ii-two-modes-of-module-coupling)
4. [Type-I: Full-Length mRNA Design](#4-type-i-full-length-mrna-design)
5. [Type-II: RNA Aptamer Design](#5-type-ii-rna-aptamer-design)

---

## 1. What is BMC?

**Bounded Multi-Module Coordination (BMC)** is a constrained iterative framework for biomolecular design. It addresses the problem where independently optimized functional modules must be assembled into an integrated whole, and inter-module conflicts must be detected and resolved through structured feedback within hard bounds on iteration rounds and step counts.

The core idea is that the global scoring function of the assembled molecule is **not separable** — i.e., the quality of the full assembly is not simply the sum of each module's local quality. Therefore, local optima for individual modules do not guarantee a global optimum for the assembled molecule, and explicit inter-module negotiation is required.

> **Positioning note (2026-08-10) — what BMC is and is not.** The stronger "coordination gain" narrative — that BMC's diagnosis-guided coordination beats serial assembly on outcome metrics — was **falsified by three pre-registered/controlled results**: P0 budget-matched control (Cliff's δ = 0.278 < 0.3 gate, Wilcoxon p = 0.129 → NO-GO; `experiments/results/p0_budget_matched_summary.json`), P3 guided-vs-unguided (δ = 0.222, p = 0.110 → NO-GO; `experiments/results/p3_guided_vs_unguided_summary.json`), and the Fig 5 b/c mechanism ablations (no test survives BH-FDR; `experiments/results/fig5_summary.json`). The defensible value of BMC as deployed is therefore **bounded budget allocation + a resampling mechanism + auditability**: hard round/improvement bounds make iteration cost predictable, the per-round regeneration is where any gain comes from, and the deterministic reference-point diagnosis makes every adjustment inspectable and reproducible. The mechanism specification below (three phases, Type-I/Type-II coupling, reference-point ASF ranking, boundedness) is the **current in-use mechanism** and remains accurate; only the superiority claim is retired. See `docs/DECISIONS.md` for the full do-not-repeat register.

BMC follows a three-phase algorithmic skeleton shared by both instantiations:

- **Phase 1 — Independent Generation**: Each module generates candidates within its own constraints.
- **Phase 2 — Assembly & Evaluation**: A Coordinator evaluates the assembled molecule for inter-module conflicts.
- **Phase 3 — Bounded Iteration**: The Coordinator diagnoses issues, broadcasts structured feedback to affected modules, and triggers targeted regeneration, all within hard convergence bounds.

---

## 2. What Does "Bounded" Mean?

"Bounded" is a core design principle of BMC. It means the entire multi-module negotiation process is strictly limited by explicit upper bounds and convergence conditions, preventing unbounded search or infinite loops. "Bounded" manifests at three levels:

### 2.1 Hard Round Limit

The coordinator supports a configurable hard round limit. The current bounds are:

| Workflow | `max_rounds` |
|----------|--------------|
| `full_length_mrna_design` | 1 |
| `rna_aptamer_design` | 1 (configurable via `bmc_max_rounds`) |

These values are set in the workflow files (`full_length_mrna_design.py`, `rna_aptamer_design.py`), not in the coordinator itself.

> **Implementation note**: BMC-capable workflows expose a four-phase interface (`run_initial`, `bmc_prepare`, `bmc_run_round`, `bmc_finalize`). `CoordinatorAgent` (Layer 4) detects this interface and orchestrates the bounded convergence loop, while the concrete `ReferencePointCoordinator` / `AptamerCoordinator` objects remain inside the Layer-2 workflow modules and supply the domain-specific diagnosis/feedback rules.

- Prevents parameter drift (e.g., λ jumping from 2 to 10, causing the design to completely abandon translation efficiency).
- Ensures every adjustment stays within a biologically reasonable range.
- Makes the entire process **predictable, reproducible, and auditable** — not a "black-box exploration" by an LLM.

### 2.4 Bounded vs. Unbounded

| Aspect | Unbounded | Bounded (BMC) |
|--------|-----------|---------------|
| Iteration rounds | Infinite loop until "satisfied" | Hard upper bound = workflow `bmc_max_rounds` (1 for both workflows) |
| Improvement criterion | Continue on any change | Stop if improvement < workflow `improvement_threshold` |
| Parameter adjustment | Arbitrary values and steps | Pre-defined options, bounded steps |
| Computational cost | Unpredictable, potentially infinite | Upper-bound predictable |
| Reproducibility | Low (LLM behavior varies) | High (deterministic rules) |
| Failure mode | May never converge | Safely exits after at most `max_rounds` rounds |

> **In one sentence**: "Bounded" means BMC is not an open-ended search or LLM free exploration, but a structured negotiation process constrained by hard round limits, convergence thresholds, and bounded parameter adjustment spaces — ensuring iterative optimization completes within a computable, auditable, and terminable scope.

---

## 3. Type-I vs. Type-II: Two Modes of Module Coupling

BMC is instantiated in two biologically distinct modes. Understanding their difference is essential for understanding why the Coordinator's diagnosis logic and feedback strategy differ.

| Dimension | Type-I: Physical Assembly | Type-II: Functional Coupling |
|-----------|--------------------------|------------------------------|
| **What are the modules?** | 5'UTR, CDS, and 3'UTR — three segments on the **same RNA sequence** | A binding hotspot on the target protein and a generated RNA aptamer — two **independent molecules** |
| **Assembly operation** | Sequence concatenation (⊕): `5'UTR_seq + CDS_seq + 3'UTR_seq` | Spatial assembly: the hotspot region and the aptamer dock in 3D space to form a complex |
| **Where does coupling occur?** | At the **junction overlap region** (40-nt overlap), at the **1D sequence level** | At the **3D spatial interface** via molecular interactions (H-bonds, van der Waals, hydrophobic effects), at the **3D structural level** |
| **Do modules depend on each other?** | All three segments **must physically co-exist** on the same molecule | The target protein exists **independently** of the aptamer, but the aptamer's function **depends on** the target's binding site |

### Analogy

- **Type-I (Full-Length mRNA)**: The modules are "three segments of the same rope." Conflicts happen at the seams.
- **Type-II (RNA Aptamer)**: The modules are "a lock and a key." Conflicts happen at how well they fit and function together.

This distinction fundamentally shapes:
- What the Coordinator evaluates (junction thermodynamics vs. complex quality metrics).
- How feedback is routed (which specific module is responsible for the issue).
- What regeneration actions are allowed (junction codon shuffling vs. hotspot window expansion).

---

## 4. Type-I: Full-Length mRNA Design

### Motivation

A full-length mRNA consists of three functional modules physically concatenated on the same molecule: the 5' untranslated region (UTR), the coding sequence (CDS), and the 3' UTR. Existing specialized tools optimize each module in isolation — for example, LinearDesign optimizes the CDS for codon adaptation and thermodynamic stability, while GEMORNA optimizes the UTRs. However, simple concatenation of independently optimized modules creates severe problems at the module junctions:

- **Thermodynamic discontinuity**: The local minimum free energy (MFE) at the CDS-3'UTR junction may become unstable because the two modules were never co-folded.
- **GC content mismatch**: A sharp GC-content jump between CDS and 3'UTR creates a thermodynamically unstable interface.
- **Translation initiation blockage**: The 5'UTR-CDS junction may become overly stable, burying the AUG start codon or the Kozak sequence inside secondary structure, preventing ribosome scanning.

These are not hypothetical edge cases — they are biophysical consequences of ignoring inter-module interactions. The quality of the full-length molecule is **not separable**; optimizing each part locally does not guarantee a globally optimal assembled molecule.

### Strategy

BMC Type-I "Physical Assembly" addresses this by dividing the design into three phases:

**Phase 1 — Independent Generation**: Each module generates candidates in parallel. The 5'UTR and 3'UTR agents explore preset libraries (short/medium/long); the CDS agent runs LinearDesign or RNARL with a user-specified λ.

**Phase 2 — Assembly & Evaluation**: The `ReferencePointCoordinator` evaluates the assembled full-length sequence in normalized objective space using the same score dimensions that drive `best_candidate` selection:

| Dimension | Module(s) | Biological Meaning |
|-----------|-----------|-------------------|
| `cds_component` | CDS | Normalized CDS quality (`-mfe + codons*log(CAI)`) / length |
| `utr5_mrl` | 5'UTR | Predicted mean ribosomal load |
| `utr3_stability` | 3'UTR | Predicted 3'UTR stability |
| `full_mfe_score` | 5'UTR, CDS, 3'UTR | Inverted full-length MFE (higher = more stable) |

**Internal diagnostics** (used by the BMC coordinator but not exposed as user-facing `reference_point` keys):

| Dimension | Module(s) | Biological Meaning |
|-----------|-----------|-------------------|
| `junction_5utr_cds_score` | 5'UTR, CDS | 5'UTR-CDS junction quality (inverted MFE/nt minus GC-diff penalty, coefficient 1.0) |
| `junction_cds_3utr_score` | CDS, 3'UTR | CDS-3'UTR junction quality (inverted MFE/nt minus GC-diff penalty, coefficient 1.0) |

Each dimension is converted to maximization space and min-max normalized within the candidate pool. The reference point is user-provided (`reference_point`) or auto-derived as the utopian point (best observed value per dimension). A gap (`reference − candidate`) > 0 produces an issue whose `violation` equals the gap.

> **Junction ddG report metric (v2.8.0)**: The former AUG/Kozak burial booleans were removed after three pre-registered experiments (P1 v2, P2, Phase 0 ddG pilot) falsified fragment-fold burial as a translation-initiation proxy. `JunctionEvaluator` now reports a full-length constrained-fold ddG at the 5'UTR–CDS junction (`junction_5utr_cds_ddg_open_w1/w2` = MFE_constrained − MFE_unconstrained on the full utr5+cds+utr3 construct; W1 = CDS start −6..+9, W2 = 5'UTR tail 60 nt + CDS head 30 nt clipped to the actual UTR). ddG is a report/profile metric only — it is not a score dimension and never triggers regeneration.

**Phase 3 — Bounded Iteration**: If the Coordinator detects issues, it broadcasts structured `ModuleFeedback` to affected modules:

| Issue Type | Affected Module(s) | Regeneration Action |
|-----------|-------------------|--------------------|
| `CDS_COMPONENT_BELOW_REFERENCE` | CDS (primary), 5'UTR & 3'UTR logged | CDS: sub-diagnosis chooses λ direction — increase λ by 2 if CAI is weak, decrease λ by 2 if MFE is weak |
| `FULL_MFE_SCORE_BELOW_REFERENCE` | CDS (primary), 5'UTR & 3'UTR logged | CDS: same sub-diagnosis as `CDS_COMPONENT_BELOW_REFERENCE` |
| `UTR5_MRL_BELOW_REFERENCE` | 5'UTR | None — UTR presets always honour the user's `utr_mode`; the coordinator never overrides them |
| `UTR3_STABILITY_BELOW_REFERENCE` | 3'UTR | None — UTR presets always honour the user's `utr_mode` |
| `JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE` | 5'UTR (primary), CDS | None — UTR presets honour `utr_mode`; no junction-triggered CDS mutation (v2.8.0 removed codon shuffling) |
| `JUNCTION_CDS_3UTR_SCORE_BELOW_REFERENCE` | 3'UTR (primary), CDS | None — UTR presets honour `utr_mode`; no junction-triggered CDS mutation (v2.8.0 removed codon shuffling) |

All regeneration operates within the hard bound of `max_rounds=1`. Convergence is measured in normalized ASF space with `improvement_threshold=0.05` for full-length mRNA.

---

## 5. Type-II: RNA Aptamer Design

### Motivation

RNA aptamer design involves two functionally independent modules: **target protein binding hotspot identification** (deciding "where to bind") and **RNA ligand generation** (deciding "what to bind with"). These modules have distinct optimization objectives and specialized toolchains — the target module analyzes protein surfaces to find hotspot residues, while the aptamer module generates sequences predicted to bind that region. However, the biological function of the design depends entirely on the quality of the **three-dimensional RNA-protein complex** formed after assembly.

A naive serial pipeline (hotspot identification → ligand generation → evaluation) ignores the functional coupling between these modules, leading to predictable multi-objective conflicts:

- **Affinity vs. foldability**: A high-affinity sequence predicted by the target-ligand scoring model may fold poorly on its own (low RhoFold pLDDT), because sequence constraints imposed by the protein surface disrupt internal RNA base-pairing.
- **Affinity vs. complex confidence**: The ligand may match the hotspot well in local shape, yet the overall 3D complex (ProteinX ipTM) is structurally unreliable due to incompatible interface geometry.
- **Interface strength vs. synthesizability**: A design with strong interface contacts and high buried surface area may have extreme GC content, making chemical synthesis difficult.

These conflicts arise precisely because the two modules are optimized independently but functionally coupled. The quality of the assembled complex is **not separable** into the sum of hotspot quality and ligand quality.

### Strategy

BMC Type-II "Functional Coupling" addresses this through the same three-phase skeleton as Type-I, but with a Coordinator that evaluates 3D complex quality against a user-specified **reference point** rather than fixed biological thresholds:

**Phase 1 — Independent Generation**: The two modules operate independently without knowledge of each other (in the current implementation the target module runs before the aptamer module):

| Module | Tool / Method | Output |
|--------|--------------|--------|
| **Target** | Hotspot residue identification from PDB structure | Candidate hotspot residue windows (position, size, confidence) |
| **Aptamer** | ODesign generating RNA sequences based on hotspot info | Candidate aptamer sequences (varying length, seed, sampling parameters) |

**Phase 2 — Normalization, Ranking, and Reference-Point Diagnosis**: The workflow first normalizes the three user-facing objectives (`egarps_component`, `rhofold_component`, `iptm_component`) against the initial candidate pool. Candidates are ranked by **ASF (Achievement Scalarizing Function) distance** to the reference point, and a Pareto frontier is maintained. The `AptamerCoordinator` then diagnoses normalized gaps between candidate objective vectors and the reference point:

| Objective | Normalization | Reference-Point Meaning |
|-----------|--------------|------------------------|
| `egarps_component` | `egarps_native_probability` | Desired predicted binding affinity |
| `rhofold_component` | `max(0, min(1, rhofold_mean_plddt / 100))` | Desired RNA monomer folding confidence |
| `iptm_component` | `max(0, min(1, proteinx_ipTM))` | Desired complex structure prediction confidence |

The reference point is the single source of truth for both `best_candidate` selection and module-level feedback. User-provided reference values are normalized once against the initial pool and fixed across BMC rounds; auto-derived utopian reference points are re-derived each round from the current candidate set.

**Phase 3 — Bounded Iteration**: The Coordinator builds a representative diagnosis set (ASF best + per-objective leaders), diagnoses each candidate against the reference point, merges issues by objective while preserving the source metrics of the worst violation, and broadcasts structured feedback:

| Issue Type | Meaning | Target Module Action | Aptamer Module Action |
|-----------|---------|---------------------|----------------------|
| `EGARPS_COMPONENT_BELOW_REFERENCE` | Affinity below reference | Expand hotspot window (+2 residues/round, max 10) | Increase samples / change seeds |
| `RHOFOLD_COMPONENT_BELOW_REFERENCE` | Foldability below reference | — | Lengthen aptamer by +5 nt; **+10 nt** if source `rhofold_mean_plddt < 60.0`; also `seed_change` |
| `IPTM_COMPONENT_BELOW_REFERENCE` | Complex confidence below reference | Expand hotspot window | Increase samples / change seeds |

The feedback is **source-aware**: `broadcast_feedback()` receives the raw metrics of the candidate that triggered the worst violation, so adjustment intensity matches actual severity rather than the average/best candidate.

> **Ablation toggle (Fig 5b)**: setting the environment variable `APTAMER_FEEDBACK_MODE=pool_average` makes `AptamerCoordinator.broadcast_feedback()` derive adjustments from the candidate-pool mean metrics (supplied by the workflow via the optional `pool_metrics` argument) instead of the worst-violation source metrics. The default (`source_aware`, or any unset/unrecognized value) is byte-identical to the behavior described above.

### Interface with the Multi-Agent Execution Layer

`RnaAptamerDesignWorkflow` exposes the same reference-point/ASF interface as `FullLengthMrnaDesignWorkflow`: `reference_point`, `bmc_max_rounds`, and `bmc_improvement_threshold` are part of the workflow input. The `AptamerCoordinator` remains deterministic and reference-point driven. `CoordinatorAgent` orchestrates the BMC loop for both workflows by consuming their four-phase BMC interface; the domain-specific diagnosis and feedback broadcasting remain inside the workflow modules.

Quality review is performed by `QualityAgent` using the workflow-specific `RNA_APTAMER_QUALITY_PROFILE` (or `FULL_LENGTH_MRNA_QUALITY_PROFILE` for full-length mRNA). `QualityAgent` produces an advisory `QualityReport` with diagnosis and suggested overrides; retry decisions are made by `SpecialistAgent` based on that report and hard execution outcomes. `QualityAgent` does not trigger iteration on its own, and BMC round limits continue to be enforced by the coordinator logic.

The default bound for aptamer design is `bmc_max_rounds=1` (set to `0` to skip BMC iteration entirely).

---
