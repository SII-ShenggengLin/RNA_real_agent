# Supplementary Information — RNADesignAgent

> **Scope.** The main text's Fig. 2 subsection carries the biological-validity
> evidence for five workflows — CDS design (CAI/MFE, Fig. 2b,c), RNA secondary
> structure inverse folding (Fig. 2d), siRNA off-target behaviour (Fig. 2e) and
> small-molecule binding (Fig. 2f), together with the benchmark-wide completion
> panel (Fig. 2a). This document carries the corresponding evidence for the
> remaining seven workflows: Supplementary Note 1 reports the IRES-prediction
> literature panel (a measured negative, reported as such); Supplementary
> Note 2 collects the output-quality evidence for full-length mRNA design,
> aptamer design, RNA tertiary-structure design, mRNA sequence scoring, sgRNA
> design and ASO target screening.
>
> Every number below is backed by a frozen file under `experiments/results/`
> and recomputed byte-identically by its driver's `--verify` mode. Drivers
> follow the project's registered pattern (pre-registered docstring,
> pilot-first, zero-intervention production tool path through
> `ToolExecutor.run_tool`, `RNADA_CAPGATE=advisory`).

---

## Supplementary Note 1 — IRES prediction on the validated literature panel

The IRES-prediction workflow was run on a literature panel of 9
experimentally validated IRES elements — 6 viral (EMCV, HCV, poliovirus,
FMDV, HRV-A1, BVDV-1) and 3 cellular (c-myc, VEGF-A, Bip) — against 50
random human 5′UTR sequences as negatives (59/59 scored, zero failures;
frozen under `experiments/results/exp5_ires_panel/`, 2026-08-25). The
workflow ran with its production defaults except that the labelling
threshold was disabled to expose raw scores (pre-registered).

* **Pre-registered primary arm (mode 0, full-sequence path):**
  AUROC 0.478 (95% CI 0.311–0.649; two-sided Mann–Whitney P = 0.841;
  Cliff's δ = −0.04) — at chance.
* **Sliding-window addendum (mode 2, 174-nt window, 50-nt step;** registered
  after the mode-0 result was known and disclosed as post-hoc**):**
  AUROC 0.673 (95% CI 0.467–0.862; P = 0.102; δ = 0.35).

Both arms fall below the 0.8 screening gate encoded in this predictor's
capability profile — the same gate the platform's DecisionGate applies in
production. We report this measured negative as **untuned**, not excluded:
the workflow ships the predictor with its published default parameters and
no panel-specific tuning was performed. The capability-map consequence is
visible in production: across the 241-run campaign the DecisionGate recorded
24 reject verdicts for IRESfinder-dependent ranking/claim requests and none
in any other class (Fig. 4h).

**Supplementary Fig. S1** (`experiments/plots/output/figS1_ires_panel.png`):
the sliding-window (mode-2) ROC arm with its bootstrap 95% confidence band
against the chance diagonal; the pre-registered mode-0 arm is archived in the
companion panel `figS1_ires_panel_mode0.png`. Both arms sit below the 0.8
screening gate (values above).

---

## Supplementary Note 2 — Output-quality evidence for the remaining workflows

### S2.1 Full-length mRNA design

The end-to-end validity evidence for this workflow is the main text's
Table 1 case study A (Exp 37, 2026-09-07, on the two-step full-length
redesign of DECISIONS (bb)): the full-length Spike task completed in
6.8 h (24,320 s, no time cap) through the platform-default flow, delivering
108 candidates (3 navigation-selected CDSs × a 6×6 UTR shortlist). The
best-ranked construct's CDS reached CAI 0.959 against the human table,
exceeding the BNT162b2 benchmark CDS anchor (0.952) scored through the same
production tool, and its GEMORNA-generated UTR pair outscored the pooled
clinical benchmark UTR pairs on the certified MRL oracle — the benchmark
pairs competed in the same pool and lost fairly. The navigation budget was
respected (35/35 raw calls); the single zero-delivery boundary (the
stability profile) is disclosed in the case record. Benchmark-wide, all 22
full-length tasks succeed (210/210 completion, Fig. 2a; re-measured 22/22
in the 2026-09-07 Exp-24 campaign lane). Frozen record:
`experiments/results/exp37_table1_case_studies/caseA/record.json`.

### S2.2 RNA aptamer design

The effectiveness evidence is the main text's Fig. 5e–g (the Exp-29/40
campaign arc and its expanded 39-target budget sweep) and Table 1 case
study B (Exp 37: the anti-VEGF aptamer navigation session, 23.4 min,
self-audit narrative). One governance property bears repeating here: the
structure-based oracles this workflow would need for affinity validation —
EGARPS native probability, ProteinX ipTM, RhoFold mean pLDDT — were
profiled on assertion-curated anchor sets and showed no reliable screening,
ranking or docking power in any measured cell (main text Fig. 3a–c and the
affinity-calibration register, Exp 10–13). The workflow's reports are
therefore capability-map-driven by design: ranking and claims abstain from
the decertified oracles rather than dressing their outputs as affinity
evidence (Table 1 case B is exactly this behaviour on a real session).
Benchmark-wide, all 18 aptamer tasks succeed (Fig. 2a; 18/18 in the Exp-24
campaign lane).

### S2.3 RNA tertiary structure design (Exp 38)

Exp 38 pools the per-candidate quality fields the 20 benchmark tasks
already produced — no new design, folding or alignment was run
(`experiments/exp38_tertiary_validity_pool.py`; frozen
`experiments/results/exp38_tertiary_validity_pool/records.jsonl` +
`summary.json`; `--verify` byte-identical). Source: the 2026-09-07
Exp-24-era campaign sessions (20/20 successful, 73 candidates, fields
`rhofold_mean_plddt` / `alignment_rmsd` / `alignment_tm_score` /
`recovery_rate` complete for every candidate). Each candidate is graded
against its task's registered rubric: refold mean pLDDT ≥ the task
threshold (65 or 70) and, where the task registers one (3 tasks),
refold-versus-reference RMSD ≤ 2.0 or 3.0 Å.

Measured outcome — **mixed, reported as measured**:

* Pooled rubric pass **28/73 = 38.4%**; the pLDDT axis passes 31/73; on the
  14 RMSD-gated candidates the RMSD axis passes **1/14** (the strict
  ≤ 2.0/3.0 Å gate is essentially unmet; the campaign-wide minimum is
  2.49 Å).
* **12/20 tasks** deliver at least one rubric-passing candidate.
* Pooled distributions: pLDDT median 37.4 (range 24.6–84.0); RMSD median
  18.8 Å (2.5–28.4); TM-score median 0.025; sequence recovery vs the
  reference chain median 0.690 (0.439–1.0).
* Per reference structure (tasks / candidates / rubric pass):

  | PDB | Reference | n cand | pass | pLDDT med | RMSD med (Å) |
  |-----|-----------|--------|------|-----------|---------------|
  | 1F7U | Theophylline aptamer | 14 | **14** | 82.6 | 21.2 |
  | 1EHZ | tRNA-Phe (yeast) | 5 | 4 | 79.0 | 21.0 |
  | 1Y26 | Hairpin ribozyme | 2 | 2 | 75.2 | 3.4 |
  | 1GID | Group I intron | 12 | 2 | 28.3 | 20.0 |
  | 1HR2 | P4-P6 domain | 11 | 3 | 27.4 | 23.7 |
  | 2GDI | T-box riboswitch | 7 | 2 | 26.6 | 18.8 |
  | 3D2V | SAM-I riboswitch | 4 | 1 | 27.7 | 17.8 |
  | 1MME | Hammerhead ribozyme | 18 | **0** | 36.3 | 9.7 |

Interpretation boundary: the designed sequences deliberately differ from
the reference sequence (median recovery 0.69), so the refold-RMSD axis is
an inverse-folding fidelity bound rather than a regression test — the
generators are asked to propose new sequences for a target fold, not to
reproduce the native chain. Confident refolds (pLDDT ≥ threshold)
concentrate on three of the eight references (1F7U 14/14, 1EHZ 4/5,
1Y26 2/2); the hammerhead-ribozyme tasks are the cleanest negative (0/18
despite the lowest median RMSD of the panel), and the two large Tetrahymena
references (1GID, 1HR2; ~315-nt designs) refold at pLDDT ≈ 27–28. All 20
tasks complete end-to-end (Fig. 2a; 20/20 in the Exp-24 lane).

### S2.4 mRNA sequence scoring (Exp 39)

Exp 39 validates the **scoring direction** of the deterministic
`mrna_sequence_scoring` stack — GC + LinearFold MFE + CAI, composite
`total_score = −MFE + codon_count · log(CAI)`
(`agent_core/sequence_utils.py::score_mrna_candidate`) — on external
anchors through the production tool path
(`experiments/exp39_scoring_anchor_direction.py`; frozen
`experiments/results/exp39_scoring_anchor_direction/records.jsonl` +
`summary.json`; 222/222 scored, zero failures; `--verify` regenerates every
arm sequence from its anchor/seed and rebuilds the summary
byte-identically). Arms: the BNT162b2 and mRNA-1273 vaccine CDSs (n = 2;
longest-ORF extraction from the putative assembled contigs as registered in
Exp 37), the 20 wild-type RefSeq CDS anchors of the FullLength-mRNA
benchmark (n = 20), and 10 seeded synonymous resamples of each WT (n = 200;
the identical generator and seeds as the Fig. 2b,c null arm). CAI species:
Homo sapiens for all arms.

* **Primary, length-controlled (pre-registered):** within each target the
  WT total_score exceeds the median of its own 10 random-synonymous draws
  in **15/20** targets — and exceeds all 10 draws in 12/20 — two-sided sign
  test **P = 0.041**, Wilcoxon signed-rank on the per-target deltas
  **P = 0.0083**, median per-target Cliff's δ = 1.0. The five targets where
  WT does not beat its random median (GFP, HPV16 L1, Luciferase, RSV-F,
  Spike WT) are reported as measured.
* **Pooled contrasts on total_score:** WT vs random (20 vs 200)
  **P = 6.2 × 10⁻³, δ = 0.37**; vaccine vs random (2 vs 200)
  **P = 9.9 × 10⁻⁵, δ = 1.0**; vaccine+WT vs random (22 vs 200)
  **P = 9.7 × 10⁻⁴, δ = 0.43**. Descriptive (n = 2): vaccine vs WT
  P = 8.7 × 10⁻³, δ = 1.0; vaccine vs the 10 Spike-WT draws P = 0.030,
  δ = 1.0 (BNT162b2 260.7 and mRNA-1273 404.8 versus the draws'
  −373.4 … −277.1).
* **Components:** the WT-vs-random separation is carried by the CAI term
  (medians 0.725 vs 0.680, P = 1.5 × 10⁻⁷, δ = 0.71) — the human-table
  analogue of the species-resolved Fig. 2b ordering — whereas MFE/nt does
  not separate WT from random (−0.0508 vs −0.0473, P = 0.295), consistent
  with Fig. 2c, where MFE/nt separates the designed arm from both nulls but
  not WT from random. The vaccine CDSs lead on both components (CAI 0.952 /
  0.979; MFE/nt −0.085 / −0.113 vs random P = 3.9 × 10⁻⁴, δ = −0.99). The
  BNT162b2 CDS CAI through this path (0.9515) reproduces the Exp-37 Table-1
  anchor exactly.

Benchmark-wide, all 13 scoring tasks succeed (Fig. 2a; 13/13 in the Exp-24
lane).

### S2.5 sgRNA design — registered data-gap disclosure

The sgRNA workflow's quality oracles (CRGPT handle efficiency, CRISOT
off-target) remain **governance = pending** on a registered data gap: no
labelled anchor set exists on disk for either predictor, and the project's
decision register (DECISIONS.md (l)) prohibits improvising self-referential
anchors; the anchor-gap closure campaigns are pre-registered and reserved
as E19/E20. Until those land, the DecisionGate treats both predictors as
unprofiled — visible in production as the require-profiling verdicts of
Fig. 4h (CRGPT 244, CRISOT 25). No biological-validity claim is made for
this workflow; the evidence is completion only — all 30 sgRNA benchmark
tasks succeed end-to-end (210/210, Fig. 2a; re-measured 30/30 in the
2026-09-07 Exp-24 campaign lane).

### S2.6 ASO target screening

ASO target screening is a deterministic thermodynamic screen built on the
published ViennaRNA routines (RNAplfold site accessibility, RNAup/RNAcofold
duplex hybridisation energies); it inherits the validity of that
peer-reviewed thermodynamics rather than carrying a learned predictor that
would need anchor-set certification. No literature anchor set exists for
this specific screen — disclosed; no capability claim beyond the inherited
thermodynamics is made. The evidence is completion only: all 14 ASO
benchmark tasks succeed end-to-end (210/210, Fig. 2a; 14/14 in the Exp-24
campaign lane).

---

## Supplementary data availability

| Content | Frozen path | Driver |
|---------|-------------|--------|
| IRES literature panel (modes 0/2) | `experiments/results/exp5_ires_panel/` | `experiments/exp5_ires_literature_panel.py` |
| Tertiary-structure validity pool (Exp 38) | `experiments/results/exp38_tertiary_validity_pool/` | `experiments/exp38_tertiary_validity_pool.py` |
| Scoring anchor direction (Exp 39) | `experiments/results/exp39_scoring_anchor_direction/` | `experiments/exp39_scoring_anchor_direction.py` |
| Table-1 case studies A/B | `experiments/results/exp37_table1_case_studies/` | `experiments/exp37_table1_case_studies.py` |
| Aptamer campaign arc + expanded sweep | `experiments/results/exp29_aptamer_campaign_arc/` | `experiments/exp29_aptamer_campaign_arc.py` |
| Benchmark completion (210/210) | `experiments/results/exp24_production_campaign/lane_*.jsonl` | Exp-24 production campaign |

Supplementary Fig. S1 is produced separately at
`experiments/plots/output/figS1_ires_panel.png` from the frozen Exp-5 IRES
panel records.
