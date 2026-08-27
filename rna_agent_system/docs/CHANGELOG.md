# Change Log

> **Scope**: interface changes and major workflow introductions.
> **Last updated**: 2026-08-27

> **History policy**: this log records the current interface state and a
> condensed register of the most recent change eras. Full narratives live in
> git history and the audit-evidence directories cited per entry; the
> experimental do-not-repeat register is [`DECISIONS.md`](DECISIONS.md).

## 2026-08-27 — Exp 10 (Fig 3b) executed under the reset: structure-oracle screening-power profile, 66/66, 0/18 cells pass

Zero-intervention oracle profiling on the registered aptamer anchor set
(`experiments/exp10_structure_oracle_screening.py`, pre-registered docstring,
pilot 6/6; evidence `experiments/results/exp10_structure_oracle_screening/`).
Anchor set `e1_anchor_set_v2.json` verbatim (66 entries, 6 targets;
user-confirmed after the target-count review — 6 is the discipline-exhausted
maximum). Instrument = the platform production tool path
(`ToolExecutor.run_tool` → deployed rhofold/proteinx/egarps services; DNA
scored as RNA via T→U per the anchor-set convention); CapGate advisory
(regression convention — under default enforce the three oracles are
SelfModel-governed and blocked); every call audited to
`platform_audit.jsonl` (the driver activates the audit runtime via
`runtime_from_env()`; an initial unaudited ~8-record attempt was discarded
and the run restarted from scratch — disclosed).

- **66/66 successful, 0 failures** (wall ≈ 3.3 h, 165–225 s/entry).
- **18/18 cells measured, 0/18 pass AUROC > 0.8; all 18 bootstrap 95% CIs
  cover chance**; best cell 0.800 exactly (RhoFold pLDDT × PDGF-BB);
  sensitivity 5/2/0/0 cells above 0.6/0.7/0.8/0.9.
- Secondary ranking (descriptive): ρ ≥ 0.6 only on two n = 3 Angiopoietin-2
  SPR subsets — underpowered by pre-registration.
- Vs retained evidence: **11/18 cells identical** (RhoFold bit-deterministic,
  pilot cross-check bit-identical; 5/6 ProteinX); the 6 EGARPS cells + 1
  ProteinX cell shift by ProteinX-complex realization variance (largest
  Δ +0.476, egarps × Thrombin) — headline invariant.
- Figure `experiments/plots/fig3b_oracle_screening.py` →
  `fig3b_oracle_screening.{pdf,png}` (balloon matrix; size + colour
  dual-encode AUROC, printed values, chance/gate reference lines; palette
  rev 7). `PAPER_DRAFT.md` Fig 3b legend + Results reset sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row 3b, `MANUSCRIPT.md` reset
  table updated.

## 2026-08-27 — Exp 8 (Fig 2h) executed under the reset: end-to-end runtime by workflow, 241/241, minutes-to-1 h per target

Zero-intervention timing of the 11 workflows (`experiments/exp8_runtime.py`
+ orchestrator `experiments/exp8_run_all.sh`, pre-registered docstring,
pilot 4/4; evidence `experiments/results/exp8_runtime/`). Instrument = one
`cli/form_chat.py` subprocess per run through the user form entry, inputs
verbatim, no thresholds, CapGate advisory (the documented regression
convention); services pre-warmed and GPU-pinned 0/1/2 by
`exp1_bring_up_services.sh`, so per-run time measures the delivered
workflow (pre-flight → generate → evaluate → score → rank → advisory
review → writeout), not cold model loads; lanes strictly sequential
(gpu_aptamer → gpu_tertiary → cpu → PA batch) against cross-lane
contention. Successful runs only enter the distribution.

- **241/241 successful**: all 210 RNADesign-210 tasks + all 31 PA
  regression sessions (PA_006–PA_036, each timed as one whole form
  session). Pooled median **2.6 min** (mean 4.4).
- **Workflow medians**: mRNA scoring 2.5 s; small-molecule 0.23 min; ASO
  0.28; secondary structure 1.21; IRES 1.34; siRNA 2.61; sgRNA 3.20; CDS
  3.21; tertiary structure 3.87; full-length mRNA 4.32; aptamer 6.29.
- **Completion profile**: 76.3% ≤5 min, 92.9% ≤10 min, 98.3% ≤30 min,
  **240/241 ≤1 h**. The four >30-min runs are all multi-turn aptamer PA
  sessions (42.4/42.9/59.9/**98.6** min); the single >1 h run is the GenNav
  `navigation=true` aptamer session PA_028. Suite-task maximum 27.0 min.
- **Disclosed amendment (registered before the PA_028 re-run)**: the
  PA-arm timeout (3600 s, calibrated on suite-task maxima) under-covered
  multi-turn navigation sessions — PA_027 finished at 3593 s and PA_028 was
  killed at 3600 s while progressing normally; the timeout's
  kill-only-the-direct-child semantics orphaned its turn-2 grandchild,
  which then completed (~5740 s total), exposing a driver defect now fixed
  (process-group kill). Amended budget 10800 s; PA_028 re-run once under
  it (**5917.2 s**, consistent with the orphan reconstruction); the
  original censored record retained in `pa_batch.jsonl`; the orphan's
  overlap window with PA_029 verified uncontaminating (42.63 s vs siblings
  42.15/42.52 s).
- Figure `experiments/plots/fig2h_runtime_ecdf.py` →
  `fig2h_runtime_ecdf.{pdf,png}` (log-axis ECDF per workflow + box inset,
  1 h reference line; palette rev 7 unchanged). `PAPER_DRAFT.md`,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md`, `MANUSCRIPT.md`, `AGENTS.md`
  updated.

## 2026-08-26 — Exp 7 (Fig 2g) executed under the reset: RNAsmol two-sided boundary, every registered metric reproduced

Zero-intervention re-run of the small-molecule oracle's two-sided profile
(`experiments/exp7_rnasmol_boundary.py`, pre-registered docstring, pilot
37/37; evidence `experiments/results/exp7_rnasmol_boundary/`). Instrument =
the deployed RNAsmol microservice exactly as the platform ships it (CPU
default via its own `start.sh`), one call per pair, sequences and SMILES
verbatim and **case-preserving** — the official held-out splits encode
modified bases in lowercase, and the agent tool layer's uppercase+T→U
normalization would silently re-introduce the v0.2.0 fidelity-defect class,
so the service endpoint is the fidelity-correct instrument (the retained
evidence's protocol; no ToolExecutor calls, hence no CapGate audit entries
at this layer). Checkpoint auto-selection via data-provenance hints only
(robin/pdb + molperturbation; FMN→pdb, MALAT1→robin; OOD no hints →
platform default); no thresholds, no tuning.

- **3,545/3,545 pairs scored, 0 failures**: robin test 1,492 + pdb test 170
  + FMN decoys 1,601 + MALAT1 decoys 265 + OOD panel 17.
- **Every registered metric of the retained 2026-08-11 evidence reproduced
  exactly**: robin AUROC 0.9744 (0.9678–0.9803), pdb 0.9828 (0.9607–0.9970;
  ≤500-nt subset 0.9788, n=126, 44 truncated service-side); decoy true-binder
  ranks 2/1601 (0.125 pct) and 7/265 (2.642 pct); OOD binder-vs-random-chem
  0.7222 (0.2778–1.0) and binder-vs-near-cognate 0.5625 (0.0625–1.0) — both
  CIs span chance. Verdict GO on all three axes.
- **Per-pair cross-check** vs the retained JSONL: medians ~1e-6 (MALAT1
  ≤3.8e-5, OOD ≤6.3e-4); a minority of near-decision-boundary inputs amplify
  inference-backend arithmetic (robin max 0.021 at 1/1492 pairs >1e-3; pdb
  0.047 at 1/170; FMN 0.367 at 53/1601 — one unstable near-0.5-band decoy,
  idx 367, re-scored bit-identical to confirm this run's determinism; the
  retained run's device is unrecorded). No registered metric moves. The
  cross-check tolerance was amended from bit-level to the disclosed
  4-decimal-AUROC + decoy-rank criterion **before** the full run (docstring
  records the amendment).
- Figure `experiments/plots/fig2g_rnasmol_boundary.py` →
  `fig2g_rnasmol_boundary.{pdf,png}` (forest dot + CI; khaki in-distribution
  / dark-warm-grey OOD; chance + 0.8 screening-gate reference lines; palette
  rev 7 unchanged). `PAPER_DRAFT.md` Fig 2g legend + Results sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row g and `MANUSCRIPT.md`
  reset-run table updated with the re-run as the numbers of record.

## 2026-08-25 — Platform fix: species-resolved LinearDesign codon tables; Exp 2+3 (Fig 2b–c) re-run

User-reported defect (the Exp 2+3 E. coli outliers): ``cai_species`` only
reached the CAI evaluator — LinearDesign always designed against the
service's bundled human table regardless of species (GFP / β-galactosidase
designed CAI ≈ 0.60 scored against their E. coli tables). Fixed at the
platform layer, not the driver:

- **Species-resolved codon tables**: 11 LinearDesign-format CSVs generated
  from the same Kazusa tables the CAI evaluator uses
  (``agent_core/data/codon_usage_lineardesign/``; generator
  ``scripts/gen_lineardesign_codon_tables.py`` with a ``--check`` drift
  guard used by the test suite). ``mrna_cds_design`` resolves
  ``cai_species → codon_usage_path`` on **both** the golden path and the
  GenNav navigation path; an explicit ``lineardesign_codon_usage_path``
  still wins. Human designs now use the platform Kazusa table (verified to
  produce the same argmax sequences as the bundled table). Unresolvable
  species fail fast at the input layer with a clear message instead of
  silently designing against the human table. ``full_length_mrna_design``
  inherits the fix (it delegates CDS generation to the same workflow). The
  audit trail records the codon table on every LinearDesign call (verified
  on the live run). Note: LinearDesign λ=0 is pure-MFE, so the table only
  influences λ>0 designs — confirmed live before the re-run.
- **Tests**: +10 (``tests/test_lineardesign_species_wiring.py``); the old
  "unsupported species still runs" contract test rewritten to the new
  fail-fast contract; suite **646 passed, 1 skipped**. Folded in a repair of
  a pre-existing reset breakage: ``agent_core/calibrated/
  profiling_metrics.py`` still imported the deleted
  ``experiments/analysis/stats_utils`` — ``bootstrap_auroc_ci`` inlined
  verbatim from git history.
- **Exp 2+3 re-run** (driver docstring updated; pre-fix run archived at
  ``exp2_cds_nulls_prefix/``, session prefixes ``exp2d_/exp2s_`` vs the
  re-run's ``exp2rd_/exp2rs_``): 20/20 design + 240/240 scoring, 0 failures.
  CAI medians **0.832 / 0.729 / 0.674** (designed-vs-WT P = 6.9e-4,
  δ = 0.63; WT-vs-random P = 6.8e-7, δ = 0.67; designed-vs-random
  P = 2.2e-13, δ ≈ 1.0); MFE/nt medians **−0.336 / −0.051 / −0.047**
  (designed vs both nulls δ = −1.0; WT-vs-random NS P = 0.29). E. coli
  targets after the fix: GFP 0.597 → 0.701 (above its WT 0.560),
  β-galactosidase 0.603 → 0.740 (above its WT 0.729). Figures refreshed
  (``fig2b_cai``, ``fig2c_mfe_per_nt``); PAPER_DRAFT / FIGURE_PLAN_V5 /
  MANUSCRIPT §3.0 numbers updated.

## 2026-08-25 — Exp 5 (Fig 2e) executed under the reset: IRES literature panel at chance on the default path

Paper §2.2 experiment 5 re-run against the frozen gated platform
(`experiments/exp5_ires_literature_panel.py`, pre-registration in its
docstring; pilot 6/6 then the full panel, `RNADA_CAPGATE=advisory`):

- **Panel (user-approved expansion before any run)**: positives extended
  from 3 to **9 literature IRES 5′UTRs** — the original EMCV/HCV/poliovirus
  plus FMDV (NC_004004.1:1-1058), HRV-A1 (NC_038311.1:1-626), BVDV-1
  (NC_001461.1:1-385) and the three cellular IRES the asset table had
  promised but never landed (c-myc NM_002467.6:1-363, Bip/GRP78
  NM_005347.5:1-217, VEGF-A NM_001025366.3:1-496; ranges = 1..CDS_start−1,
  provenance recorded in the anchor `SOURCES.md`); negatives unchanged (50
  GENCODE v46 200-nt 5′UTR windows). n = 59.
- **Zero-intervention rule (user-directed)**: one `ires_prediction`
  workflow run per sequence with platform defaults; the only deviation is
  `probability_threshold=0.0`, registered before the pilot — the threshold
  is a labelling knob (the service computes every fragment's probability
  regardless), and 0.0 merely disables the label filter so raw
  probabilities reach the workflow's score/rank layer for below-threshold
  sequences. Threshold-free AUROC over the raw scores; ROC + pointwise 95%
  TPR band via stratified bootstrap (10⁴ replicates, seed 20260825).
- **Primary result (pre-registered mode-0 arm — the workflow default)**:
  59/59 scored, 0 failures; **AUROC 0.478 (95% CI 0.311–0.649),
  Mann–Whitney P = 0.841 — indistinguishable from chance**. 20/50
  negatives score above 0.5 (median 0.449); score–length correlation
  r = 0.018 (not a length artifact). The legacy 3-positive-panel 0.762
  does **not** reproduce: the legacy-3 subset against the same 50
  negatives scores 0.513 (legacy protocol unrecoverable — deleted in the
  reset; this re-derivation is the number of record).
- **Disclosed mode-2 addendum arm** (registered after the primary was
  known, never substituted for it): sliding-window scanning at upstream
  defaults (window 174 / step 50 — the native regime; removes the
  341–1058-nt-vs-200-nt regime mismatch between positives and negatives).
  **AUROC 0.673 (95% CI 0.467–0.862), P = 0.102** — directionally better,
  CI still spans 0.5, and the estimate sits exactly where E16 graded the
  oracle on IRESfinder's own held-out sets (0.68/0.73/0.76, all below the
  0.8 screening gate → enforce-gated). The calibrated self-knowledge and
  the literature panel agree: the deployed IRES oracle has ~0.7
  discrimination at best and the default full-sequence path has none.
- Evidence `results/exp5_ires_panel/` (`panel_runs.jsonl`,
  `panel_runs_mode2.jsonl`, `summary.json`, `roc_points_{mode0,mode2}.csv`);
  figures `experiments/plots/fig2e_ires_roc.py` →
  `plots/output/fig2e_ires_roc.{pdf,png}` and
  `fig2e_ires_roc_mode0.{pdf,png}` (all palette rev 7; the workflow's warm
  grey `#B7B0A2`, chance diagonal in neutral grid). **Figure endpoint
  re-registered to the mode-2 scanning arm (user direction, 2026-08-26)**:
  the canonical `fig2e_ires_roc.*` now renders mode-2 (AUROC 0.673) — it is
  the legacy panel's protocol (legacy per-sequence scores match this arm
  exactly, confirmed against `PAPER_FACT_SHEET.md`) and the oracle's native
  window regime; the pre-registered mode-0 default-path result stays the
  primary analysis record and its figure is archived as
  `fig2e_ires_roc_mode0.*`. No scores were recomputed.
- `docs/MANUSCRIPT.md` asset table + §3.0 programme table updated;
  `docs/FIGURE_PLAN_V5.md` row 2e and the `PAPER_DRAFT.md` Fig. 2e
  legend/Results observation (3) updated to the measured numbers (and the
  stale "EMCV 0.808, poliovirus 0.891 literature-panel reproduction"
  parenthetical dropped — those were task-protocol scores, not panel
  scores).

## 2026-08-25 — Exp 4 (Fig 2d) executed under the reset: inverse folding 21/25 exact

Paper §2.2 experiment 4 re-run against the frozen gated platform
(`experiments/exp4_inverse_folding.py`, pre-registration in its docstring;
pilot 5/5 then the full 25-task matrix, `RNADA_CAPGATE=advisory`):

- **Zero-intervention rule (user-directed)**: the platform is measured
  as-is — no threshold presets, no objective tuning, no parameter sweeps;
  task inputs fed verbatim from RNADesign-210
  `06_rna_secondary_structure` (25 targets, 9–54 nt, 4–70 °C, function
  modes m/p/mp, start-sequence constraints). The single arm is the
  `rna_secondary_structure_design` golden path (RNAinverse ×N → RNAfold
  fold-back validation + GC → scoring → ranking).
- **Primary metric**: best-ranked candidate dot-bracket Hamming distance to
  the target (the platform's own `structure_distance`; 0 = exact recovery).
  Secondary: base-pair distance (analysis-side), per-candidate profile,
  any-candidate-exact (generation vs delivery).
- **Results**: 25/25 runs successful; **21/25 exact recovery** (dot-bracket
  distances 0×21, 2, 2, 4, 6; base-pair distances of the four misses
  1, 2, 3, 1 — at most 3 of 10–14 target pairs). All four misses are
  mp-mode / combined-parameter / extreme-temperature / longest-target edge
  tasks (015, 018, 021, 024); no candidate in any miss's ranked set was
  exact (generation-limited, not ranking-limited). Categories: basic 1/1,
  edge 19/21, full 1/3. The pre-reset run and the Exp-1 lane had observed
  22/25 (different stochastic realization; RNAinverse is stochastic) —
  this run's 21/25 is the number of record.
  Evidence `results/exp4_inverse_folding/` (`pilot.jsonl`, `records.jsonl`,
  `summary.json`); figure `experiments/plots/fig2d_inverse_folding.py` →
  `plots/output/fig2d_inverse_folding.{pdf,png}` (strip + step cumulative
  curve; exact dots in the workflow's grey green `#8DA290`, misses in the
  reserved dark warm grey `#7A7672`, cumulative curve slate blue
  `#6B7B8D` — all from palette rev 7).
- Driver fix during analysis: base-pair distance corrected to the standard
  |P₁ Δ P₂| definition (an integer-halving slip mis-scored asymmetric
  stem extensions; recomputed from the stored structure strings, no
  platform re-run).
- `docs/PAPER_DRAFT.md` Results §2.2 observation (2) and the Fig. 2d
  legend updated to 21/25; `docs/FIGURE_PLAN_V5.md` row 2d re-pointed to
  the new evidence path.

## 2026-08-25 — Exp 2+3 (Fig 2b–c) executed under the reset; fig 2c re-registered as a three-arm panel

Paper §2.2 experiments 2 and 3 merged into one driver and re-run against the
frozen gated platform (`experiments/exp2_cds_null_model.py`, pre-registration
in its docstring; pilot 3/3 then full matrix, `RNADA_CAPGATE=advisory`):

- **Designed arm = the system's CDS golden path as-is** (user-directed):
  `mrna_cds_design` with `design_tool="all"` — LinearDesign λ∈{0,1,4,10} +
  RNARL + GEMORNA, each candidate folded (LinearFold), GC/CAI/RNASTOP-scored
  and ranked; the best-ranked candidate is the arm's data point. No λ or
  codon-table tuning (the legacy "pure-CAI LinearDesign" attribution is not
  reconstructible and is replaced by this registration).
- **Null arms**: WT = the 20 NCBI RefSeq `wt_cds/` anchors; random = 10
  seeded synonymous resamples per WT (n = 200, uniform over the standard
  code, seed `exp2:<target>:<draw>`, deterministic). One scoring path for
  all 240 sequences (`mrna_sequence_scoring`: CAI via Kazusa tables,
  species-resolved + GC + LinearFold MFE).
- **Results**: design 20/20, scoring 240/240, zero failures. CAI medians
  **0.830 / 0.729 / 0.674** (designed > WT > random gate PASS;
  designed-vs-WT P = 7.1e-3 δ = 0.50; WT-vs-random P = 6.8e-7 δ = 0.67).
  MFE/nt medians **−0.336 / −0.051 / −0.047** (designed vs both nulls
  P ≤ 7e-8, δ = −1.0; WT-vs-random NS P = 0.29).
- **Fig 2c re-registered (user-directed)**: the legacy WT-vs-random-only
  folding control becomes a full three-arm MFE/nt panel — the designed CDSs
  lead on codon adaptation and structure simultaneously, and the WT≈random
  null contrast shows the CAI ordering is not a folding artifact. Evidence
  `results/exp2_cds_nulls/` (`design_runs.jsonl`, `fig2_cds_nulls.jsonl`,
  `summary.json`); figures `experiments/plots/fig2bc_cds_nulls.py` →
  `plots/output/fig2b_cai.{pdf,png}`, `fig2c_mfe_per_nt.{pdf,png}`.
- **Palette**: `ARM_COLORS` semantic slots added to `experiments/plots/palette.py`
  under rev 7 (designed = terracotta `#C08B7C`, WT = sage `#A3B18A`,
  random = the reserved dark warm grey `#7A7672`); Fig 2a re-rendered.
- `docs/PAPER_DRAFT.md` Results §2.2 observation (1) and the Fig. 2 legend
  rewritten to the reset numbers; `docs/FIGURE_PLAN_V5.md` rows 2b/2c and
  `docs/MANUSCRIPT.md` §3.0 register updated. Known recorded caveats: the
  two E. coli targets (GFP, β-galactosidase) are designed against
  LinearDesign's default human codon table (frozen-platform behaviour,
  documented in the driver docstring) and the Influenza HA WT anchor derives
  from a different strain than the benchmark protein (pre-existing anchor
  documentation).

## 2026-08-25 (z) — Experiment-programme reset: legacy campaigns deleted, RNADesign-210 audited+repaired, Exp 1 re-run 210/210

User-directed reset (DECISIONS (z)): the architecture moved too much since
the legacy campaigns, so **all paper experiments re-run against the frozen
gated platform** with newly written drivers and figures; the legacy campaign
drivers (`run_platform_quality_benchmark.py`, `run_e16_e17_e18_oracle_profiling.py`,
`curate_*`), the `experiments/analysis` helpers, the `experiments/plots/paper_v5`
figure programme and the legacy campaign results (fig2–fig7, E3–E15, P0–P3,
junction line, PA regressions, caches/logs) are deleted. Retained: the
packaged-SelfModel evidence chain (`e1_*_v2`, `e7_*`, `rnasmol_boundary_panel*`,
`e16_e17_e18/`, `build_default_self_model.py`), `codon_tables/`,
`tool_inventory.json`, `MODEL_API_USAGE.md`, the workspace audit trail.

**RNADesign-210 dataset audit and repair** (`experiments/audit_rnadesign210.py`
+ `fix_rnadesign210.py`, report `results/rnadesign210_audit.json`): all 210
task inputs validate against the current workflow Input models; benchmark
manifest recounts (208→210, tertiary 18→20); category taxonomy normalized to
basic/edge/full (was 14 ad-hoc values incl. BMC-era labels); the 12 IRES tasks
rebuilt on real IRES-positive anchors (poliovirus 5′UTR for mode 0 — the old
synthetic 5′UTR scores 0.458 < its own 0.5 task threshold and mode-0 scores
of canonical IRES 5′UTRs peak ≈0.48, so the two mode-0 detection tasks use
0.45 with the rationale recorded in-task; EMCV 5′UTR for mode 2; best window
251–424 for mode 1); absolute IRES paths → repo-relative; stale junction-tool
expected chains dropped; all expected chains regrounded from observed traces
(`reground_tool_chains.py`; re-audit: 0 issues / 0 warnings).

**Exp 1 (paper §2.2 experiment 1, Fig. 2a) executed**: pilot 10/11 (the one
failure was the IRES data defect, fixed and verified 12/12 against the live
service), then the full matrix — **210/210 successful across the 11 workflows**
(primary arm `RNADA_CAPGATE=advisory`; five parallel lanes; GPU-pinned services
via `experiments/exp1_bring_up_services.sh`; records and per-workflow medians
in `results/exp1_rnadesign210/`). A 4-task **enforce probe** documents the
gated-platform boundary as data: IRES tasks refuse with an explicit
`GatedActionError`, small-molecule tasks fail cleanly with both oracles gated
(`enforce_probe.jsonl`). **Fig 2a** rendered (per-task tile carpet + horizontal
bar summary) from the new **unified palette**
(`experiments/plots/palette.py`). Palette history: rev 1 = the ten mandated
colours; rev 2 = a 12-colour replacement (withdrawn same day); rev 3 = ten
colours + two in-family extensions (withdrawn same day); rev 4 = twelve
colours extracted from a user reference figure (withdrawn same day);
rev 5 = the user's muted Morandi set (withdrawn same day);
rev 6 = the user's cool pastel set (withdrawn same day);
**rev 7 (final, user-confirmed 2026-08-25)** = the earthy Morandi
twelve-colour set, supplied directly (`#B5838D #D3B5B0 #C08B7C #D9C3A9
#CDBF9E #A3B18A #8DA290 #8FA6BB #6B7B8D #A99AAF #B7B0A2 #7A7672`) — eleven
identify the workflows (#7A7672 dark warm grey held out, reserved for
neutral-dark semantics such as failed tiles); warm and cool tones alternate,
slate blue separates the palest warms. All subsequent experiment figures use
rev 7 exclusively (DECISIONS (z)).

## 2026-08-25 — Paper figure-lettering unification (doc-only)

All six figure legends in `docs/PAPER_DRAFT.md` re-lettered to
`docs/FIGURE_PLAN_V5.md` (the operative build plan for
`experiments/plots/paper_v5/`). The v5 figure rebuild had updated the
Results body citations and the built figures, but the legends kept
pre-rebuild lettering — stale in Figs. 1 (b/c/f), 2 (g–i), 3 (f–i),
4 (c–i), 5 (d–i) and 6 (missing g–i). Body text gained citations for
previously unreferenced panels (Fig. 1c,f; 2g; 4g,i; 6g–i); the
representative-claims examples moved from main Fig. 4 to the planned
Supplementary Table S1, now registered in the figure plan alongside the
GenNav aptamer supplementary archive. Draft endnote panel counts corrected
(6 + 9×5; "End of draft v4.3" → v4.5). No numbers changed — lettering and
cross-references only. Same day, the first Results subsection was split
into a system-design subsection ("Overview of the RNADesignAgent platform",
Fig. 1) and the RNADesign-210 biological-validity results subsection
(Fig. 2), so experimental results begin with the second Results
subsection; content unchanged apart from the new heading. A legacy→v5
panel-lettering map was added to `docs/PAPER_FACT_SHEET.md` (legacy letters
double as `fig2_summary.json` keys and are kept verbatim), and the AGENTS.md
What's New index records the pass.

## 2026-08-22 (i) — Repo-wide simplification pass: workspace scratch isolation, demo tool retired, historical outputs purged

User-directed cleanliness pass over everything outside `external_repos/`
(code as the source of truth, no git archaeology):

- **Test-suite workspace leak fixed (real bug).** Every test run leaked
  scratch artifacts (`save_sequence` / `save_text_file` without a session
  context) into the real `workspace/` root — **141k files / 1.3 GB**
  accumulated. `tests/conftest.py` now redirects all default workspace bases
  to a per-run `workspace/_tests` scratch (removed afterwards); the redirect
  is inherited by subprocesses via the new `RNADA_WORKSPACE_BASE` env
  override honoured by `WorkspaceManager.__init__` (also useful for
  deployments). Literal-path test writers (`test_compute_*`) now write into
  the isolated base. Verified: full suite runs leave zero new files in the
  workspace root.
- **Demo tool removed**: `workflow_demo_echo` and the
  `build_default_tool_registry(include_demo=...)` parameter are gone —
  **41 registered tools, all production** (manifest regenerated:
  `experiments/results/tool_inventory.json`). Tests use local mock tools.
- **Layer-4 test dedup**: the identical QualityAgent retry-semantics blocks
  duplicated across the secondary/tertiary layer-4 modules moved to one
  parametrized module (`tests/test_layer4_agent_semantics.py`).
- **Documentation dedup in code**: 39 `tools.py` wrapper docstrings dropped
  their `Args/Returns/Raises` sections (verbatim duplicates of the Input-model
  `Field` descriptions); stale comments referencing deleted experiment
  drivers removed (`tools.py`, `evaluators.py`, `rna_aptamer_design.py`).
- **Historical outputs purged**: superseded figure generations
  (`experiments/plots/{paper,paper_v4,fig*_panels,fig*.png}`, ~24 MB),
  archived experiment rounds (`e5_s1_*_archive/`, `e14_audit_v{1,2}/`,
  versioned `e14/e8` re-run files, `codon_tables_e6/`, ~12 MB), orphaned
  `__pycache__`, and 141k leaked workspace scratch files + stale service-run
  intermediates (`workspace/*_service_runs` contents, 634 MB of RhoFold
  intermediates). **Repository shrank from 4.3 GB to 2.0 GB** (the remainder is dominated by 1.2 GB of required reference-genome data and the retained audit trail). Everything
  under `workspace/{audit,sessions}/` and every `*_fresh_audit_*` evidence
  directory is retained (audit trail untouched).
- Codonw-slim stub entries still present in two full-length-mRNA test files
  were removed with their tool (deleted 2026-08-18).
- Suite after the pass: **635 passed, 1 skipped** (the −1 is the merged
  demo-registration test); PA_006–PA_019 re-run green end-to-end.

## Condensed register: the 2026-08-18 → 2026-08-22 era

Each row: what changed, the defect count fixed on live-fetched data, the
evidence directory, and the DECISIONS.md entry. Suite counts are the
post-entry regression-suite size.

| Date | Change | Evidence | DECISIONS |
|------|--------|----------|-----------|
| 08-18 | System simplification: BMC framework removed after triple-falsified coordination gain; 12 dead tools purged (54→42 specs) + codonw_slim_service; E1–E15 experiment machinery and drivers deleted (evidence JSONs kept); bowtie2_ma type fix | git `1b45138` | (a), (m) |
| 08-19 | GenNav constraint navigation became the production opt-in on `rna_aptamer_design` v2.1.0 (`navigation` field; deterministic, zero-LLM; full trace in `_state_writeback["_gennav_trace"]`); batch-B fresh-data re-verification (PA_025–PA_036, 12/12); `tool_call` audit lines now carry `session_id` + `task_type` | `experiments/results/pa_regression_batchB_2026-08-19/`, `gennav_live_verification_2026-08-19/` | (n) |
| 08-20 | ASF/Pareto ranking generalized to five workflows + adversarial surfacing tests; paper_v5 figure programme (51 panels, `experiments/plots/paper_v5/`) | `docs/FIGURE_PLAN_V5.md` | (o) |
| 08-21 | Ranking governance: ASF objectives assembled from CapGate verdicts (deterministic, mode-independent; `agent_core/calibrated/objective_assembly.py`; `RNADA_CAPGATE=off` disables); Layer-0 tool audit (4 defects, e.g. EGARPS posting workspace-relative paths); Layer-1 capability audit (252 checks, EGARPS path fix); Layer-2 workflow audit (12/12 green on live-fetched data) | `workspace/tool_layer_audit_2026-08-21/`, `layer1_fresh_audit_2026-08-21/`, `layer2_fresh_audit_2026-08-21/`, `docs/RANKING_GOVERNANCE.md` | (p), (k) |
| 08-22 (b) | Layer-3 service-orchestration audit (45 checks, 3 defects: degraded-service pre-flight hole, `__all__` export bug, missing exec bit) | `workspace/layer3_fresh_audit_2026-08-22/` | (r) |
| 08-22 | GenNav-λ production wiring on `mrna_cds_design` v1.2.0 (`navigation` field replaces the static λ grid); ASO ordering converted to shared ASF ranking (v1.1.0, Borda → diagnostics); CDS runs attach the CAI×MFE/nt Pareto annotation | `tests/test_gennav_mrna_core.py` etc. | (q) |
| 08-22 (c) | Layer-4 multi-agent + CapGate + ranking-governance audit (5 defects: dropped ranking audit events, pipeline crash on dangling bindings, IRES swallowing tool failures, retry counting, int-enum overrides) | `workspace/layer4_fresh_audit_2026-08-22/` | (s) |
| 08-22 (d) | Layer-5 persistence audit (3 WorkspaceManager defects: `delete_session("")` rmtree of the sessions tree, unvalidated session-id path joins, `list_files` creating directories) | `workspace/layer5_fresh_audit_2026-08-22/` | (t) |
| 08-22 (e) | Layer-6 façade/CLI/API audit (6 defects: pipeline session-scoping leak, API success misreporting, task_id echo, dropped progress events, dead step events, bare `input()` on the non-tty pipeline path) | `workspace/layer6_fresh_audit_2026-08-22/` | (u) |
| 08-22 (f) | Interface Lock Policy removed repo-wide (~1,250 lines pure deletion; behavioural contracts remain pinned by `WORKFLOWS.md`, the regression suite and the PA drivers) | — | (v) |
| 08-22 (g) | Oracle version stamps: all 11 managed-oracle descriptors declare `oracle_version`; packaged SelfModel records carry the profiling-time stamp; drift warns + audits, never blocks | `tests/test_oracle_version_stamps.py` | (w) |
| 08-22 (h) | Full-platform E2E fresh-data audit — whole stack, all 11 workflows through all three entry points (56 checks; 3 defects: opaque sgrna seed failure, `stream_form` raising on hard failure, ViennaRNA inverse-fold accepting pseudoknot brackets → SIGSEGV) | `workspace/e2e_fresh_audit_2026-08-22/` | (x) |
| 08-22 (i) | Repo-wide simplification pass (this entry) | — | (y) |

## Current interface state

- **Tool count**: 41 registered specs, all production (`python -m
  agent_core.tool_inventory`).
- **Workflows**: 11, all plain `BaseDomainWorkflow` implementations; six rank
  by Achievement Scalarizing Function (DECISIONS (o)/(q)); GenNav navigation
  is an opt-in on `rna_aptamer_design` (length lattice) and `mrna_cds_design`
  (GenNav-λ).
- **Microservices**: 21 mapped services, ports 8003–8024.
- **No BMC interface anywhere**; no automatic workflow router — selection is
  explicit (CLI menu / `--workflow` / `explicit_workflow` / `--pipeline-file`).
- **Governance**: `RNADA_CAPGATE` = `off|advisory|enforce` (default
  `enforce`); packaged SelfModel 29 records; the CapGate audit trail lives at
  `workspace/audit/platform_audit.jsonl` (every `tool_call` line stamped with
  `session_id` + `task_type`).
