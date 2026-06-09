# Bounded Multi-Module Coordination (BMC) Framework

> **Scope**: design motivation, conceptual foundations, and execution strategy of the BMC framework, covering both Type-I (Physical Assembly) and Type-II (Functional Coupling) instantiations.
> **Last updated**: 2026-06-01

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

BMC follows a three-phase algorithmic skeleton shared by both instantiations:

- **Phase 1 — Independent Generation**: Each module generates candidates within its own constraints.
- **Phase 2 — Assembly & Evaluation**: A Coordinator evaluates the assembled molecule for inter-module conflicts.
- **Phase 3 — Bounded Iteration**: The Coordinator diagnoses issues, broadcasts structured feedback to affected modules, and triggers targeted regeneration, all within hard convergence bounds.

---

## 2. What Does "Bounded" Mean?

"Bounded" is a core design principle of BMC. It means the entire multi-module negotiation process is strictly limited by explicit upper bounds and convergence conditions, preventing unbounded search or infinite loops. "Bounded" manifests at three levels:

### 2.1 Hard Round Limit

```python
max_rounds = 3
```

Regardless of the current result quality, BMC runs at most **3 iteration rounds** after the initial generation and evaluation.

**Why this bound?**
- Bioinformatics toolchains (ViennaRNA, ProteinX, RhoFold, etc.) are computationally expensive per call. Unbounded iteration leads to unpredictable time and cost.
- In practice, improvement typically saturates after 3 rounds; further iterations yield diminishing returns.
- It eliminates the systemic risk of an agent that "never finishes."

### 2.2 Improvement Threshold

```python
improvement_threshold = 1.0
```

Even before the round limit is reached, iteration stops immediately if the score improvement falls below this threshold (or if the score degrades).

**Why this bound?**
- Prevents meaningless oscillation in noisy metric ranges (e.g., MFE fluctuating from -0.26 to -0.255 with no biological significance).
- Conserves computational budget for tasks with genuine room for improvement.

### 2.3 Constrained Parameter Adjustment Space

Feedback from the Coordinator does not allow arbitrary modifications. Each module's adjustable parameters are pre-defined with clear bounds:

| Module | Allowed Adjustment | Bound Constraint |
|--------|-------------------|-----------------|
| 5'UTR | Switch UTR preset (short/medium/long) | 3 discrete options only |
| CDS | Adjust λ (MFE vs. CAI trade-off) | Step size ±2, with upper/lower bounds |
| 3'UTR | Switch UTR preset | 3 discrete options only |
| Aptamer length | ±5 nt | Min/max length enforced |
| Hotspot window | +2 residues per round | Upper bound 10 residues |
| Sample count | +5 per round | Upper bound 20 |

**Why this bound?**
- Prevents parameter drift (e.g., λ jumping from 2 to 10, causing the design to completely abandon translation efficiency).
- Ensures every adjustment stays within a biologically reasonable range.
- Makes the entire process **predictable, reproducible, and auditable** — not a "black-box exploration" by an LLM.

### 2.4 Bounded vs. Unbounded

| Aspect | Unbounded | Bounded (BMC) |
|--------|-----------|---------------|
| Iteration rounds | Infinite loop until "satisfied" | Hard upper bound of 3 |
| Improvement criterion | Continue on any change | Stop if improvement < 1.0 |
| Parameter adjustment | Arbitrary values and steps | Pre-defined options, bounded steps |
| Computational cost | Unpredictable, potentially infinite | Upper-bound predictable |
| Reproducibility | Low (LLM behavior varies) | High (deterministic rules) |
| Failure mode | May never converge | Safely exits after at most 3 rounds |

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
- What regeneration actions are allowed (UTR preset switching vs. hotspot window expansion).

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

**Phase 2 — Assembly & Evaluation**: The `FullLengthCoordinator` evaluates the assembled full-length sequence with a suite of junction-aware metrics:

| Metric | Threshold | Biological Meaning |
|--------|-----------|-------------------|
| `full_mfe_per_nt` | ≤ −0.25 kcal/mol/nt | Length-normalized global thermodynamic stability |
| `full_paired_fraction` | ≥ 0.65 | Overall structural compactness |
| `junction_cds_3utr_mfe` | ≤ −15 kcal/mol | Local stability at the CDS-3'UTR junction (40-nt overlap) |
| `junction_5utr_cds_mfe` | < −20 kcal/mol | 5'UTR-CDS junction over-stability (blocks ribosome scanning) |
| `junction_5utr_cds_aug_buried` / `kozak_buried` | Binary check | Whether the AUG / Kozak is buried in secondary structure |
| `junction_gc_diff` | ≤ 0.15 | GC-content discontinuity across the junction |

**Phase 3 — Bounded Iteration**: If the Coordinator detects issues, it broadcasts structured `ModuleFeedback` to affected modules:

| Issue Type | Affected Module(s) | Regeneration Action |
|-----------|-------------------|--------------------|
| `FULL_MFE_TOO_HIGH` / `FULL_STRUCTURE_TOO_LOOSE` | CDS | Decrease λ by 2 to favor MFE over CAI |
| `JUNCTION_CDS_3UTR_UNSTABLE` | 3'UTR (primary), CDS (secondary) | Explore alternative 3'UTR presets; shuffle junction codons |
| `JUNCTION_5UTR_CDS_TOO_STABLE` / `AUG_BURIED` / `KOZAK_BURIED` | 5'UTR (primary), CDS (secondary) | Explore alternative 5'UTR presets; shuffle junction codons |
| `JUNCTION_*_GC_MISMATCH` | — | Logged in trace for human review (no automated adjustment) |

All regeneration operates within the hard bounds of `max_rounds=3` and `improvement_threshold=1.0`, with the Coordinator deterministically deciding convergence.

> **In one paragraph**: Full-length mRNA design employs BMC Type-I "Physical Assembly" because the molecule comprises three sequence modules (5'UTR, CDS, 3'UTR) that are independently optimized by existing tools but physically concatenated into a single chain. Simple concatenation causes junction-level defects — thermodynamic discontinuity, GC-content mismatch, and AUG/Kozak burial — that impair translation initiation. BMC addresses this through a three-phase process: independent module generation, assembly evaluation by a deterministic `FullLengthCoordinator` that checks junction MFE, GC difference, and start-codon accessibility against hard thresholds, and bounded iterative refinement where structured feedback drives targeted regeneration (UTR preset switching, λ adjustment, junction codon shuffling) within a hard limit of 3 rounds, ensuring the assembled molecule maintains thermodynamic continuity and structural accessibility at translation initiation sites.

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

BMC Type-II "Functional Coupling" addresses this through the same three-phase skeleton, but with a Coordinator that evaluates 3D complex quality rather than sequence junctions:

**Phase 1 — Independent Generation**: The two modules operate in parallel without knowledge of each other:

| Module | Tool / Method | Output |
|--------|--------------|--------|
| **Target** | Hotspot residue identification from PDB structure | Candidate hotspot residue windows (position, size, confidence) |
| **Aptamer** | ODesign generating RNA sequences based on hotspot info | Candidate aptamer sequences (varying length, seed, sampling parameters) |

**Phase 2 — Assembly & Evaluation**: The `AptamerCoordinator` evaluates each target-ligand pair as an assembled complex:

| Metric | Threshold | Biological Meaning |
|--------|-----------|-------------------|
| `egarps_native_probability` | ≥ 0.30 | Predicted binding affinity |
| `rhofold_mean_plddt` | ≥ 70.0 | RNA monomer folding confidence |
| `proteinx_ipTM` | ≥ 0.60 | Complex structure prediction confidence |
| `interface_contacts` | ≥ 5 | Number of atomic contacts at the interface |
| `buried_sasa` | ≥ 500.0 Å² | Buried solvent-accessible surface area |
| `gc_content` | [0.30, 0.70] | Synthesis-friendly range |

**Phase 3 — Bounded Iteration**: The Coordinator diagnoses issues and broadcasts structured feedback:

| Issue Type | Meaning | Target Module Action | Aptamer Module Action |
|-----------|---------|---------------------|----------------------|
| `BINDING_AFFINITY_LOW` | Insufficient predicted affinity | Expand hotspot window (+2 residues/round, max 10) | Increase samples / change seeds |
| `RNA_FOLDABILITY_LOW` | Poor RNA self-folding | — | Adjust length (±5 nt) / change seeds |
| `COMPLEX_CONFIDENCE_LOW` | Unreliable overall complex structure | Expand hotspot window | Increase samples / change seeds |
| `INTERFACE_TOO_WEAK` | Insufficient interface contacts / burial | Expand hotspot window | Increase samples / change seeds |
| `EXTREME_GC_CONTENT` | GC outside synthesis-friendly range | — | Change seeds |

### Two-Tier Critic Design

RNA aptamer design uniquely employs a **two-tier Critic** architecture:

| Tier | Component | Role | Decision Basis |
|------|-----------|------|---------------|
| **Workflow-internal** | `AptamerCoordinator` | Hard-threshold conflict detection and fast iteration | Deterministic rules (6 thresholds above), millisecond response |
| **ExecutionController-level** | `RnaAptamerDesignLLMCritic` | User intent alignment and scoring weight adjustment | LLM reasoning (e.g., when user requests "prioritize binding over foldability", adjusts scoring weights) |

The Coordinator handles **objective biophysical constraints** (if pLDDT < 70, the design must change — no discussion). The LLM Critic handles **subjective user preferences** (trading off one metric against another based on natural language intent).

> **In one paragraph**: RNA aptamer design employs BMC Type-II "Functional Coupling" because the task involves two functionally independent yet physically coupled modules — target protein hotspot identification (determining "where to bind") and RNA ligand generation (determining "what to bind with") — whose biological function depends on the quality of the assembled 3D RNA-protein complex. A naive serial pipeline ignores this coupling, producing designs that suffer from multi-objective conflicts such as high affinity but poor foldability, or strong local matching but low complex confidence. BMC addresses this through a three-phase process: parallel independent generation of hotspot windows and aptamer candidates, assembly evaluation by the `AptamerCoordinator` using EGARPS, RhoFold, and ProteinX to assess binding affinity, RNA foldability, and complex confidence against hard thresholds, and bounded iterative refinement where structured feedback drives targeted regeneration (hotspot window expansion, aptamer length/seed adjustment, sampling increase) within a deterministic rule engine and a hard limit of 3 rounds, thereby balancing binding affinity, structural foldability, and complex stability.

---
