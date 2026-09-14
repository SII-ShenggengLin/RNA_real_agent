# Supplementary Information — RNADesignAgent

> **Scope.** The main text's Fig. 2 subsection carries the biological-validity
> evidence for five workflows — CDS design (CAI/MFE, Fig. 2b,c), RNA secondary
> structure inverse folding (Fig. 2d), siRNA off-target behaviour (Fig. 2e) and
> small-molecule binding (Fig. 2f), together with the benchmark-wide completion
> panel (Fig. 2a). This document carries the corresponding evidence for the
> remaining seven workflows — Supplementary Note 1 reports the IRES-prediction
> literature panel (a measured negative, reported as such) and Supplementary
> Note 2 collects the output-quality evidence for full-length mRNA design,
> aptamer design, RNA tertiary-structure design, mRNA sequence scoring, sgRNA
> design and ASO target screening — together with the Supplementary Methods
> (detailed protocols that support the main-text experiments: the governed
> two-step full-length design protocol, the claim-overreach audit and gating
> experiments, the constraint-navigation campaigns and the per-agent ablation).
>
> Every number below is backed by a frozen file under `experiments/results/`
> and recomputed byte-identically by its driver's `--verify` mode. Drivers
> follow the project's registered pattern (pre-registered docstring,
> pilot-first, zero-intervention production tool path through
> `ToolExecutor.run_tool`, `RNADA_CAPGATE=advisory`).

---

## Supplementary Methods

### The governed two-step full-length mRNA design protocol

The full-length mRNA workflow assembles its constructs in a governed two-step protocol, introduced ahead of the planned wet-lab validation programme. Step 1 selects coding sequences first: every CDS delivered by the (navigation-default) CDS workflow is evaluated once, at most one CDS per navigation profile is retained (the top three under a pinned static recipe), and selection ranks by the shared CDS combined score — untranslated-region draws are never resampled per CDS, so CDS ranking cannot be confounded by UTR sampling variance. Step 2 pairs the selected CDSs with one UTR pool per run: twelve generated 5′UTRs and ten generated 3′UTRs (the generative model's published screening scale) plus an assertion-verified benchmark pool — the BNT162b2 UTR pair (the template-verified 51-nucleotide α-globin-derived 5′UTR; the 94-nucleotide AES–mtRNR1 3′UTR), the LinearDesign-paper 5′UTR, and the natural human HBA1 pair, every sequence extracted programmatically from its primary source and checksum-verified at load time. The pool is screened by admission rules that carry citable quantitative thresholds only: no upstream AUG in a designed 5′UTR (the scanning model of eukaryotic initiation; the uAUG penalty is the strongest negative feature of the ribosome-load model whose assay certifies the MRL predictor), no Class-II tandem-AUUUA AU-rich element in a 3′UTR (the classical instability-element classification), and two Kozak structure gates on the assembled construct — the 5′-terminal 60-nucleotide window may not fold at or below −30 kcal/mol (a −30 hairpin 12 nucleotides from the cap prevents 40S subunit engagement, whereas the same hairpin 52 nucleotides from the cap has no effect), and no 150-nucleotide window through the AUG context may fold at or below −61 kcal/mol (the hp7 scanning-stall threshold). Rules without an established quantitative threshold in the literature — overall U-content caps, GU-rich innate-immune motif counts and internal polyadenylation-signal screens — were deliberately not implemented. The 5′UTR shortlist is ranked by the certified ribosome-load predictor, so a generated UTR is selected only when it outranks the clinical benchmarks in silico; the 3′UTR-stability predictor, which carries no profiling evidence under any registered task type, was demoted from a ranking objective to a report-only diagnostic rather than allowed to order candidates (its metric is still computed and reported, and 3′UTR selection is governed by the admission rules and whole-construct objectives). The emitted construct is 5′UTR + CDS + 3′UTR; capping and polyadenylation are wet-lab protocol steps outside the sequence designer.

### Claim-overreach audit and gating experiments

The 45-task claim-overreach audit set was built on the nine-target aptamer anchor set — an earlier registered 20-task set carried byte-verbatim and extended by pre-registered, assertion-checked construction rules: 24 trusted-deterministic tasks with exactly recomputable ground truth and 21 untrusted-predictor ranking and screening tasks spanning all nine anchor targets, with predictor scores fetched live from the deployed services. The ungated control condition issues exactly two LLM calls per task; the gated treatment condition runs the identical tasks through the production gate stack (SelfModel + DecisionGate + ClaimGate under enforce policy; plan requests gated per declared use at the predictors' registered task key; execution verification by exact recomputation before publication; ClaimGate suppression of unverifiable claims), paired task-for-task with the control and adjudicated blind to condition. The expression-predictor certification scored 706 of 706 anchors zero-intervention through the production tool path (advisory CapGate, zero LLM calls). The mRNA-side audit set mirrors the same construction on real full-length design assets: targets from the 20-target full-length suite with per-target codon tables (GFP designed and scored as E. coli, the suite's registration); CDS candidates from the production default CDS design flow (platform-default GenNav-λ deliveries); full-length constructs from the production full-length workflow (top-three ranked per target); ten trusted-deterministic tasks whose ground truth is computed by exact recomputation (CAI via Sharp–Li weights on the target's registered Kazusa table; folding energy via LinearFold; constraint satisfaction) and ten untrusted-predictor tasks whose scores are fetched live from the deployed services (GEMORNA 3′UTR stability and MRL; the junction metric computed as the current platform junction report — junction-window MFE per nucleotide plus constrained-fold ddG). Its gated condition runs the production gate stack with the packaged default SelfModel (the certified GEMORNA-MRL profile; scoring implied by a verified ranking grade), deterministic report metrics registered per task family, execution verification against the build-time ground truth, and ClaimGate review of every published claim; both conditions make exactly two LLM calls per task at temperature 0 with prompts held byte-identical to the set's original construction, and claims are adjudicated blind to condition. The selective-gating decision matrix comprises twelve pre-registered cells across the DecisionGate, ClaimGate and tool-execution layers on the two GEMORNA expression predictors — the three certified anchor families plus the production never-profiled family key drawn from the mRNA audit set — run through the enforcing runtime with the packaged default SelfModel and the platform audit trail, one live enforcement cell per verdict class (allow, downgrade, block), zero LLM calls.

All comparative experiments followed a pilot-first protocol: pre-registration (hypothesis, primary metric, expected effect size, decision gate and pilot sample size recorded before data collection), a small-scale pilot with a decisive control condition, a go/no-go gate, and disciplined recording of negative pilots as evidence. The budget-matching rule — equal total generated-and-evaluated candidates across conditions for any best-of-pool or hypervolume comparison — was enforced in every comparative campaign of this paper. Two-condition experiments held the prompts, the underlying LLM and the deployed predictor services identical between conditions, and claims were adjudicated blind to condition by a deterministic adjudicator.

### Constraint-navigation campaigns

**Selection-layer pool measurement.** The selection-layer precursor behind Fig. 5a was measured under the legacy pool protocol, recovered verbatim from version control: per target, LinearDesign λ{0,1,4,10} + one RNARL + 30 GEMORNA CDS samples = 35 CDS candidates × 9 GEMORNA UTR combinations = 315 full-length constructs, screened against the six-constraint hard matrix with thresholds unchanged, with rule deliveries over the three registered profiles and minimum pairwise batch diversity against the 2% gate, on the five-target registration (A1AT, insulin, EPO, GFP and IL-2, per-target codon species), through the production tool path under advisory CapGate with every call audited. GFP was measured under both codon-table wirings — the pre-fix default (human) table and the species-resolved E. coli table (the current production state) — with the RNARL, GEMORNA and UTR settings shared between wirings so that the codon table is the only lever; zero LLM calls.

**Endpoint campaigns and pooled deployment cohorts.** The mRNA and aptamer endpoint campaigns ran the pre-registered dual-condition protocols of the main text under the budget-matching rule. The deployment navigation runs entered through the production user-form path verbatim — one form subprocess per session on eleven new targets outside every other dataset: the five human therapeutic proteins of the mRNA deployment cohort (PTH, leptin, G-CSF, thrombopoietin and PLAT; sequences from the curated UniProt register, with accession and length asserted) designed through GenNav-λ at the 35-raw-call cap, and the six anchor-fasta proteins of the aptamer deployment cohort designed through the ODesign length–seed–sample grid at 48, three of them reusing disclosed same-sequence ProteinX folds. Their missing static comparison conditions were completed under the identical budget-matched protocols — for the five mRNA targets, the endpoint campaign's pool instrument, with the frozen form-session navigation traces composed and evaluated under the identical full-length matrix and utility stack; for the six aptamer targets, the campaign arc's static grid on the same structures and deterministic hotspots — after which the pooled 25-/26-target analyses reported in the Results were computed from the frozen records with cohort splits disclosed. Both conditions are deterministic with zero LLM calls (the form sessions' advisory review calls are these runs' only LLM usage: 22 review calls over the 11 sessions; the static-condition completion and pooled re-analysis consumed none). The expanded-pool budget sweep ran the same paired protocol per quota cap over the 39-target pool (the 20-target suite plus the 19-target expansion).

### External-baseline comparison (bare model and same-tool agent loop)

The three conditions of Fig. 6 ran on the 31-session process-aware suite (96 user turns, all eleven workflows), every session receiving identical turn-by-turn inputs rendered by one deterministic template. The platform condition reuses its frozen production records (no re-runs). The bare-model condition makes exactly one model call per turn per prompting regime (zero-shot and few-shot, the few-shot examples demonstrating the output schema only), the underlying model held identical to the platform's reviewer configuration family at temperature 0, with no tool access; fixture contents are inlined into the task text under a registered size rule. The same-tool condition is a thin text-JSON agent loop driving the same 41 production tools through the same audited executor (advisory policy, identical to the platform condition) — plus one environment file-writing primitive, disclosed separately, since every tool consumes file inputs that the platform's workflows materialize internally and without which no generic scaffold can operate at all. Its model-call budgets are tiered: the platform-matched tier equals the platform's own measured per-session model-call count (zero for the eight deterministic-workflow sessions that carry no advisory review — degenerate by construction and recorded as the measured floor), and two disclosed generous tiers at 3× and 10× of max(platform count, two calls per turn); the session budget is allocated evenly across turns, and the candidate-generation budget equals the platform's evaluated-candidate count at every tier. Adjudication is deterministic and identical across conditions: per-workflow structural validity by exact recomputation (length and alphabet, translation identity, target complementarity or antisense ancestry, window substring, PDB parseability, fold-back against the target dot-bracket); delivered quality on the two structure tasks at parity with the platform's own best frozen candidate on the same turn (base-pair distance; TM-score, with input-echo submissions — returning the task's own structure file as the deliverable — rejected by an integrity guard); claim verdicts by the blind adjudication rules with recomputable metrics recomputed exactly (GC/U locally, CAI via the platform's Kazusa tool, folding energy via the deployed folder) and claims whose only basis is an unprofiled predictor scored unverifiable for every condition alike; prediction-type workflows deliver at schema level for every condition, and a complete negative answer ("no regions above threshold") counts as delivered for every condition symmetrically (the platform's own threshold-negative IRES turns carry exactly this form). Claims were adjudicated blind to condition; the comparison's summary recomputation is verified byte-identical against the frozen records.

### Per-agent ablation of the multi-agent layer

The multi-agent layer was ablated agent by agent. The full 31-session process-aware suite was run through the user-form path in three conditions — production default, advisory review off (`RNADA_QUALITY_REVIEW=off`) and retries disabled (`RNADA_SPECIALIST_MAX_RETRIES=0`, an environment knob added for this experiment) — and two pre-registered two-node pipelines (inverse-folded structure design and diffusion aptamer design, each feeding its best candidate into the small-molecule interaction workflow; inputs verbatim from the process-aware benchmark) were each run under three conditions: the production CLI pipeline path, the same path with the synthesis LLM disabled (`RNADA_SYNTHESIS_LLM=off`), and sequential driver-side node execution with no agent layer at all. The in-process sequential condition's CapGate policy was matched to the subprocess convention after a first run was censored for a condition asymmetry (the default enforce policy rejected its small-molecule calls; the record is retained and the condition re-run once under advisory). Across its three form-suite conditions the ablation consumed 218 advisory review calls (146 in the production-default condition — two per reviewed turn plus one call per retry round — 0 with review off, and 72 with retries disabled, the final review alone) and four synthesis-side calls on the two multi-node probes (one synthesis call plus one claim-extraction call per probe in the full condition; none in the other conditions). The complete campaign-level evidence trail (pre-registrations, verdict files, adjudication materials, failure taxonomy) is retained in the project repository.

---

## Supplementary Note 1 — IRES prediction on the validated literature panel

The IRES-prediction workflow was run on a literature panel of 9
experimentally validated IRES elements — 6 viral (EMCV, HCV, poliovirus,
FMDV, HRV-A1, BVDV-1) and 3 cellular (c-myc, VEGF-A, Bip) — against 50
random human 5′UTR sequences as negatives (59/59 scored, zero failures;
frozen under `experiments/results/exp5_ires_panel/`, 2026-08-25). The
workflow ran with its production defaults except that the labelling
threshold was disabled to expose raw scores (pre-registered).

* **Pre-registered primary analysis (mode 0, full-sequence path):**
  AUROC 0.478 (95% CI 0.311–0.649; two-sided Mann–Whitney P = 0.841;
  Cliff's δ = −0.04) — at chance.
* **Sliding-window addendum (mode 2, 174-nt window, 50-nt step;** registered
  after the mode-0 result was known and disclosed as post-hoc**):**
  AUROC 0.673 (95% CI 0.467–0.862; P = 0.102; δ = 0.35).

Both analyses fall below the 0.8 screening gate encoded in this predictor's
capability profile — the same gate the platform's DecisionGate applies in
production. We report this measured negative as **untuned**, not excluded:
the workflow ships the predictor with its published default parameters and
no panel-specific tuning was performed. The capability-map consequence is
visible in production: across the 241-run campaign the DecisionGate recorded
24 reject verdicts for IRESfinder-dependent ranking/claim requests and none
in any other class (Fig. 4h).

**Supplementary Fig. S1** (`experiments/plots/output/figS1_ires_panel.png`):
the sliding-window (mode-2) ROC analysis with its bootstrap 95% confidence band
against the chance diagonal; the pre-registered mode-0 analysis is archived in the
companion panel `figS1_ires_panel_mode0.png`. Both analyses sit below the 0.8
screening gate (values above).

---

## Supplementary Note 2 — Output-quality evidence for the remaining workflows

### S2.1 Full-length mRNA design

The evidence is benchmark-wide completion plus the pre-registered
navigation campaign: all 22 full-length tasks succeed end-to-end
(210/210 completion, Fig. 2a; re-measured 22/22 in the 2026-09-07 Exp-24
campaign lane). The governed two-step protocol itself (GenNav-λ CDS
navigation, the benchmark-anchored UTR pool under the
literature-threshold admission rules, ASF reference-point ranking) is
specified in the Supplementary Methods, and its constraint-delivery behaviour is
characterized at scale by the mRNA navigation campaign (Fig. 5a–d; 25
targets pooled, budget-matched dual conditions). No single-run case study is
reported; practical end-to-end validation of designed constructs is
deferred to the wet-lab programme.

### S2.2 RNA aptamer design

The effectiveness evidence is the main text's Fig. 5e–g (the Exp-29/40
campaign arc and its expanded 39-target budget sweep). One governance
property bears repeating here: the
structure-based oracles this workflow would need for affinity validation —
EGARPS native probability, ProteinX ipTM, RhoFold mean pLDDT — were
profiled on assertion-curated anchor sets and showed no reliable screening,
ranking or docking power in any measured cell (main text Fig. 3a–c and the
affinity-calibration register, Exp 10–13). The workflow's reports are
therefore capability-map-driven by design: ranking and claims abstain from
the decertified oracles rather than dressing their outputs as affinity
evidence. Benchmark-wide, all 18 aptamer tasks succeed (Fig. 2a; 18/18 in
the Exp-24 campaign lane).

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
every condition's sequences from their anchor/seed and rebuilds the summary
byte-identically). Arms: the BNT162b2 and mRNA-1273 vaccine CDSs (n = 2;
longest-ORF extraction from the putative assembled contigs — the longest
in-frame AUG→stop open reading frame), the 20 wild-type RefSeq CDS anchors
of the FullLength-mRNA
benchmark (n = 20), and 10 seeded synonymous resamples of each WT (n = 200;
the identical generator and seeds as the Fig. 2b,c null condition). CAI species:
Homo sapiens for all conditions.

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
  with Fig. 2c, where MFE/nt separates the designed condition from both nulls but
  not WT from random. The vaccine CDSs lead on both components (CAI 0.952 /
  0.979; MFE/nt −0.085 / −0.113 vs random P = 3.9 × 10⁻⁴, δ = −0.99).

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
| Aptamer campaign arc + expanded sweep | `experiments/results/exp29_aptamer_campaign_arc/` | `experiments/exp29_aptamer_campaign_arc.py` |
| Benchmark completion (210/210) | `experiments/results/exp24_production_campaign/lane_*.jsonl` | Exp-24 production campaign |

Supplementary Fig. S1 is produced separately at
`experiments/plots/output/figS1_ires_panel.png` from the frozen Exp-5 IRES
panel records.
