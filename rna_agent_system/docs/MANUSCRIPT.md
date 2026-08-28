# RNADesignAgent — Experiment Manual

> **Scope**: benchmark/anchor assets, the pilot-first protocol (still in force), and the data-availability register for both experiment campaigns.
> **Last updated**: 2026-08-28 (experiment-programme reset; Exps 1–13 executed)

---

## 0. Status Banner (read first)

**The old Fig 2–7 narrative is superseded.** The v3 edition of this manual was a
figure-by-figure runbook for the legacy campaign (Figs 2–7: platform quality,
BMC ablations, cross-LLM robustness, case studies). That narrative was retired
after the 2026-08-03 pivot pilots (P0/P2/P3 NO-GO) and the E2 self-audit showed
its central claims do not survive capability profiling and budget matching.
The current manuscript draft lives at [`docs/PAPER_DRAFT.md`](PAPER_DRAFT.md);
the do-not-repeat register and concluded directions live at
[`docs/DECISIONS.md`](DECISIONS.md); verified numbers for writing live at
[`docs/PAPER_FACT_SHEET.md`](PAPER_FACT_SHEET.md).

What remains in force from the old manual:

1. the benchmark and external-anchor **assets** (§1);
2. the **pilot-first rule** (§2) — the process specification every new
   experiment must follow;
3. the **data-availability register** (§3), now two tiers.

The per-figure runbooks (run commands, per-figure budget tables) are retired
and were removed in this edition; the drivers themselves remain under
`experiments/` and every campaign's final verdicts/summaries remain under
`experiments/results/` (§3). Historical detail is preserved in
`docs/CHANGELOG.md`.

---

## 1. Input Assets

### 1.1 Benchmarks (all under `rna_agent_system/data/benchmarks/`)

| Benchmark | Path | Size | Used by |
|-----------|------|------|---------|
| RNA-BioBench-Platform | `RNA-BioBench-Platform/tasks/<dir>/<task>.json` | 210 tasks / 11 workflows | **Exp 1 / Fig 2a (2026-08-25 reset run, 210/210)**; subsequent Fig 2 panels |
| RNA-BioBench-FullLength-mRNA | `RNA-BioBench-FullLength-mRNA/targets/*.json` (+`sequences/*.fa`) | 20 targets | Fig 2 b–c panels; navigation campaigns (to be re-run under the reset) |
| RNA-BioBench-Aptamer | `RNA-BioBench-Aptamer/targets/*.json` (+`structures/*.pdb`) | 20 targets | aptamer profiling/navigation campaigns (to be re-run under the reset) |
| RNA-BioBench-ProcessAware | `RNA-BioBench-ProcessAware/task_set_for_llm_comparison.json` | 19 tasks on disk (PA_006–024) | CLI regression (`run_pa_test.py`) |
| PA batch-B registry | `pa_benchmarks.json` entries 025–036 | 12 fresh-data benchmarks (all 11 workflows + GenNav `navigation=true`) | CLI regression batch-B (GenNav production coverage) |

Platform task JSON → the `input` object is passed verbatim as the CLI params
file; `evaluation_rubric` defines pass thresholds; `expected_tool_chain` is
CI-only. FullLength-mRNA target JSON fields used: `protein_sequence`,
`species_for_codon_optimization` (→ `cai_species`), `expression_system`,
`target_id`. Aptamer target JSON fields used: `pdb_id`, `pdb_chain`,
`known_hotspot_residues` (2/20 targets), `known_aptamer_reference{sequence, kd_nm}`.

### 1.2 External anchors (dry-lab validation data)

Curated under `data/benchmarks/external_anchors/` (spec:
[`docs/ANCHORS.md`](ANCHORS.md); each file carries a `SOURCES.md` entry with
URL + accession + download date):

| Anchor set | Content |
|------------|---------|
| `vaccine_mrna/` | BNT162b2 and mRNA-1273 full CDS + UTR sequences (published) |
| `wt_cds/` | Wild-type CDS for the 20 full-length-mRNA targets (NCBI RefSeq) |
| `aptamers/` | Known aptamers: TBA (Kd 25 nM, vs 1HAO), SARS-CoV-2 N aptamer (Kd 15.2 nM, vs 6M3M), pegaptanib (Macugen) + VEGF165 binding-site residues |
| `ires/` | 9 validated IRES 5′UTRs — viral EMCV, HCV, poliovirus, FMDV, HRV-A1, BVDV-1 + cellular c-myc, VEGF-A, Bip/GRP78 (2026-08-25 user-approved expansion from 3 to 9 positives for Exp 5; provenance in the anchor `SOURCES.md`); 50 random human 5′UTR negatives (GENCODE v46) |
| `small_molecule/` | Binder/non-binder pairs: theophylline, HIV TAR, guanine aptamer panels |
| E1 anchor sets | Per-target binder Kd gradients + fixed-seed negatives + native/decoy pose pairs (prototype: P2's 15 entries, extended per task type) |

---

## 2. Pilot-First Rule (process specification, in force since 2026-08-05)

Lesson of the 2026-07 campaign: large matrices were run before key design
assumptions were verified (e.g. the Fig-4 Serial arm was not budget-matched to
the BMC arms, so "coordination" effects were confounded with sampling budget).
Every new method idea, executor change, metric, or evaluation protocol follows
this protocol **before** any full-matrix run:

1. **Pre-register**: hypothesis, primary metric, expected effect size,
   go/no-go threshold, and pilot n are written into the driver docstring
   *before* running anything.
2. **Pilot small**: 4–6 units per arm, sized to detect Cliff's δ ≥ 0.5; pilots
   must include the decisive control arm (e.g. budget-matched baseline) even if
   the full matrix later drops it.
3. **Budget matching (iron rule)**: all arms compared on best-of-pool or
   hypervolume metrics must use equal *total generated-and-evaluated*
   candidates (and comparable compute where wall-clock is claimed). This
   applies to any mechanism that regenerates candidates per round.
4. **Go/no-go gate**: scale to the full matrix only if the pre-registered
   threshold is met; otherwise the pilot result is still recorded (negative
   pilots are evidence, not waste) and the narrative branches accordingly.
5. **Record discipline**: pilots write their own JSONL under
   `experiments/results/` with the same record conventions as main campaigns
   (every record carries `session_id, condition, seed_set, params, success,
   elapsed_seconds, errors`), and are cited by name wherever used.

---

## 3. Data Availability Register

> **2026-08-25 reset (DECISIONS (z))**: the legacy campaign results (Tier 1
> below, E2–E15 of Tier 2, pivot/junction verdicts, failure taxonomy) were
> **deleted** — every paper experiment re-runs against the frozen gated
> platform with new drivers. The historical conclusions below are retained as
> the do-not-repeat context (full register: `DECISIONS.md` Parts 1–2); their
> evidence files no longer exist on disk except where noted. Retained on disk:
> the packaged-SelfModel evidence chain (`e1_capability_summary_v2.json`,
> `e1_oracle_scoring_v2.jsonl`, `e1_docking_power_v2.jsonl`, `e7_*`,
> `rnasmol_boundary_panel*`, `e16_e17_e18/`, `build_default_self_model.py`),
> `codon_tables/`, `tool_inventory.json`, `MODEL_API_USAGE.md`, the workspace
> audit trail, and the new reset-run results:

### 3.0 Reset programme (2026-08-25 →)

| Exp | Question | Status | Evidence |
|-----|----------|--------|----------|
| Exp 1 (Fig 2a) | RNADesign-210 full-platform benchmark | **210/210 across 11 workflows** (advisory arm; pilot 10/11 — the one failure was the IRES fixture defect, fixed and verified 12/12 pre-run); enforce probe: IRES refuses with `GatedActionError`, small-molecule fails cleanly with both oracles gated | `exp1_rnadesign210/` (driver `experiments/exp1_rnadesign210.py`; dataset audit `rnadesign210_audit.json`) |
| Exp 2+3 (Figs 2b–c) | CDS null model: designed vs WT vs random-synonymous on CAI **and** MFE/nt (re-run post species-table fix) | **20/20 design (golden path, `design_tool=all`, species-resolved LinearDesign codon tables) + 240/240 scoring, 0 failures**; CAI medians 0.832/0.729/0.675 (designed>WT>random gate PASS; designed-vs-WT P=6.9e-4 δ=0.63, WT-vs-random P=6.8e-7 δ=0.67); MFE/nt medians −0.336/−0.051/−0.047 (designed vs both nulls P≤7e-8 δ=−1.0; WT-vs-random NS P=0.29 — three-arm folding panel per user direction) | `exp2_cds_nulls/` (driver `experiments/exp2_cds_null_model.py`, pilot 3/3; figures `experiments/plots/fig2bc_cds_nulls.py`; pre-fix run archived `exp2_cds_nulls_prefix/`) |
| Exp 4 (Fig 2d) | Secondary-structure inverse folding, 25 RNADesign-210 targets, zero-intervention protocol | **25/25 runs, 21/25 exact dot-bracket recovery** (misses 2/2/4/6 positions = 1/2/3/1 base pairs of 10–14 target pairs; all edge-case categories) | `exp4_inverse_folding/` (driver `experiments/exp4_inverse_folding.py`; figure `experiments/plots/fig2d_inverse_folding.py`) |
| Exp 5 (Fig 2e) | IRES literature-panel prediction, threshold-free ROC (user-approved panel expansion 3→9 positives: 6 viral + 3 cellular vs 50 GENCODE 5′UTR negatives) | **59/59 sequences scored, 0 failures** (one workflow run per sequence, defaults except the labelling threshold disabled at 0.0 to expose raw scores). Pre-registered mode-0 primary (workflow default, full-sequence scoring): **AUROC 0.478 (95% CI 0.311–0.649), P=0.841 — at chance**. Disclosed mode-2 addendum arm (registered after the primary was known; upstream scanning regime, window 174/step 50 defaults): AUROC 0.673 (0.467–0.862), P=0.102 — matches the E16 oracle grading (0.68–0.76 on IRESfinder's own held-out sets, below the 0.8 gate → enforce-gated). Legacy 3-positive-panel AUROC 0.762 does not reproduce (legacy-3 subset on the same negatives: 0.513); **figure endpoint re-registered to the mode-2 arm (user direction, 2026-08-26)** — it is the legacy panel's protocol (legacy per-sequence scores match this arm exactly) and the oracle's native window regime; the mode-0 default-path result stays the pre-registered primary analysis record (archived figure variant `fig2e_ires_roc_mode0.*`) | `exp5_ires_panel/` (driver `experiments/exp5_ires_literature_panel.py`, pilot 6/6; figure `experiments/plots/fig2e_ires_roc.py` — mode-2 endpoint + mode-0 archive) |
| Exp 6 (Fig 2f) | siRNA off-target scanning, per-task predicted hits of the delivered candidates (zero-intervention protocol) | **22/22 runs, 0 failures (wall 58.8 min); 21/22 zero predicted off-targets** — sole nonzero: task 013 (bowtie2 identity-70 input) best candidate 3 transcriptome hits, reproducing the Exp-1 lane exactly (21/22, 013=3). Scan evidence trace-verified rather than assumed: 2 tasks executed transcriptome scans against GENCODE v46 (003 BLAST, zero hits; 013 bowtie2, 3 hits); 20 zero tasks scan-skipped (19 input-disabled + 021 `sars_cov_2`, which requested a scan but the species ships no transcriptome reference — graceful skip recorded as scan_requested/scan_executed fields) | `exp6_sirna_offtarget/` (driver `experiments/exp6_sirna_offtarget.py`, pilot 5/5; figure `experiments/plots/fig2f_sirna_offtarget.py`) |
| Exp 7 (Fig 2g) | RNAsmol small-molecule oracle two-sided boundary: official held-out splits + decoy case studies (in-distribution) vs the 17-pair literature short-aptamer panel (OOD); zero-intervention service-direct protocol (case-preserving verbatim inputs — the official splits encode modified bases in lowercase; the platform's packaged CPU-default deployment via its own start.sh; checkpoint auto-selection by data-provenance hints only; no thresholds) | **3,545/3,545 pairs scored, 0 failures — every registered metric of the retained 2026-08-11 evidence reproduced exactly**: robin test AUROC **0.9744** (0.9678–0.9803), pdb test **0.9828** (0.9607–0.9970; ≤500-nt subset 0.9788 n=126, 44 truncated service-side); decoy true-binder ranks **2/1601** (0.125 pct) and **7/265** (2.642 pct); OOD binder-vs-random-chem **0.7222** (0.2778–1.0), binder-vs-near-cognate **0.5625** (0.0625–1.0) — both CIs span chance. Per-pair cross-check vs the retained evidence: medians ~1e-6; one unstable near-0.5-band FMN decoy diverges 0.367 under backend arithmetic (re-scored bit-identical to confirm this run's determinism; retained run's device unrecorded) — no registered metric moves. Verdict GO | `exp7_rnasmol_boundary/` (driver `experiments/exp7_rnasmol_boundary.py`, pilot 37/37; figure `experiments/plots/fig2g_rnasmol_boundary.py`) |
| Exp 8 (Fig 2i) | End-to-end runtime by workflow, zero-intervention timing: one CLI form subprocess per run through the user entry, inputs verbatim, CapGate advisory regression convention, pre-warmed GPU-pinned services (measures the delivered workflow, not cold model loads), lanes strictly sequential; 241 runs = all 210 RNADesign-210 tasks + all 31 PA regression sessions (each timed as one whole form session) | **241/241 successful** (pilot 4/4). Pooled median **2.6 min**; per-workflow medians 2.5 s (mRNA scoring) → 6.29 min (aptamer); 76.3% ≤5 min, 92.9% ≤10 min, **240/241 ≤1 h** — the four >30-min runs are all multi-turn aptamer PA sessions (42.4/42.9/59.9/98.6 min; >1 h = the GenNav navigation session PA_028); suite-task max 27.0 min. Disclosed amendment (registered before the PA_028 re-run): PA-arm timeout 3600→10800 s — the registered budget was calibrated on suite-task maxima and under-covered multi-turn navigation sessions (PA_027 3593 s; PA_028 killed at 3600 s while progressing, orphaned turn 2 exposed a kill-only-the-child driver defect, now process-group kill); PA_028 re-run once at **5917.2 s** (consistent with the ~5740 s orphan reconstruction), original censored record retained | `exp8_runtime/` (driver `experiments/exp8_runtime.py` + orchestrator `experiments/exp8_run_all.sh`; figure `experiments/plots/fig2i_runtime_ecdf.py`) |
| Exp 9 (Fig 2h) | Production audit-trail statistics on a frozen, user-confirmed corpus: the audit slice of the 241 registered Exp-8 runs (210 tasks + 31 PA sessions, PA_028 = the amended re-run; pilots and the censored original excluded by the 1:1 record mapping); read-only analyzer over `platform_audit.jsonl` — no platform run, no thresholds; tool calls attributed by session stamp, gate/ranking/claim events by disjoint session windows (assertions: 0 window overlaps, 0 unstamped campaign-span calls); corpus frozen verbatim + SHA-256 manifest | **10,217 events**: **8,798 tool calls (86.2%**; 40 tools; 6 failures, all one session's recovered retry) + **1,377 gate decisions (13.5%**; reject 690 / require_profiling 553 / downgrade 134; 11 oracles) + **42 ranking assemblies** + **0 claims** (ClaimGate is pipeline-synthesis-only). Representative session by pre-registered rule = **PA_036** (full-length mRNA, 3 turns: 152 calls + 32 gates of all three verdicts); disclosed correction: the rule was initially claimed to select PA_024 on an incomplete four-session pre-check — the full candidate set has three verdict-complete sessions and the registered median tie-break selects PA_036 | `exp9_audit_stats/` (driver `experiments/exp9_audit_stats.py`; figure `experiments/plots/fig2h_audit_trail.py`) |
| Exp 10 (Fig 3b) | Structure-oracle screening-power profile on the registered aptamer anchor set (`e1_anchor_set_v2.json` verbatim — 66 entries, 6 targets; user-confirmed 2026-08-27 after the target-count review: 6 = the discipline-exhausted maximum, 7 candidate targets rejected with registered reasons). One zero-intervention pass through the platform production tool path (ToolExecutor.run_tool → deployed rhofold 8005 / proteinx 8022 / egarps 8023 services, DNA scored as RNA via T→U per the anchor-set convention, fixed protocol args only); CapGate advisory regression convention (under default enforce the three oracles are SelfModel-governed and blocked); every call audited to `platform_audit.jsonl` — the driver activates the audit runtime via `runtime_from_env()` (an initial unaudited ~8-record attempt was discarded and the run restarted from scratch for this, disclosed); gate 0.8 analysis-side only | **66/66 successful, 0 failures** (pilot 6/6; wall ≈ 3.3 h, 165–225 s/entry). **18/18 cells measured, 0/18 pass AUROC > 0.8; all 18 stratified-bootstrap 95% CIs (10⁴) cover chance**; best cell 0.800 exactly (RhoFold pLDDT × PDGF-BB); threshold sensitivity 5/2/0/0 cells above 0.6/0.7/0.8/0.9; secondary ranking ρ ≥ 0.6 only on two n = 3 Angiopoietin-2 SPR subsets (descriptive, underpowered by pre-registration). Vs retained evidence: **11/18 cells identical** (RhoFold bit-deterministic — pilot cross-check bit-identical; 5/6 ProteinX), the 6 EGARPS cells + 1 ProteinX cell shift by ProteinX-complex realization variance (largest Δ +0.476, egarps × Thrombin 0.286→0.762) — headline invariant | `exp10_structure_oracle_screening/` (driver `experiments/exp10_structure_oracle_screening.py`, pilot 6/6; figure `experiments/plots/fig3b_oracle_screening.py`) |
| Exp 11 (Fig 3c) | Structure-oracle ranking-power profile on the affinity subsets of the same anchor set (`e1_anchor_set_v2.json` verbatim; pre-registered subset rule = binders with measured Kd, `ranking_eligible` flag defaults True where absent — per-target n 6/8/5/6/3/6, 34 entries; rule verified by recomputing the nine retained v2 JSONL cells to max abs Δρ = 0; ρ = Spearman(score, −log10 Kd), gate 0.6 analysis-side only). One zero-intervention pass through the platform production tool path (ToolExecutor.run_tool → deployed rhofold 8005 / proteinx 8022 / egarps 8023, GPU-pinned 0/1/2 inherited; fixed protocol args only); CapGate advisory; every call audited to `platform_audit.jsonl` | **34/34 successful, 0 failures** (pilot 4/4; wall ≈ 1.7 h). **18/18 cells measured; no oracle shows reliable ranking power across targets** — 2/18 nominal ρ ≥ 0.6 passes, both small-n with vacuous uncertainty (egarps × PDGF-BB n = 5, ρ = +0.667, CI −0.40–1.0, an ordering of near-zero scores; proteinx × Ang2 n = 3, ρ = +1.0 with two of three entries flipping ~0 ↔ ~1 across complex realizations); no oracle passes on >1 target; sensitivity 6/4/2/1 at 0.4/0.5/0.6/0.7; retained best (rhofold × PDGF-BB +0.5643) reproduced bit-identically, still sub-gate. Vs retained: **10/18 cells identical** (all 6 RhoFold bit-deterministic — also re-derives the pilot-3 targets' retained ρ exactly), 8 shifted by ProteinX-complex realization variance (largest Δρ +0.5); vs Exp-10 per-entry scores: RhoFold max abs Δ = 0, ProteinX median 0.005, EGARPS median 1.9e-5 with 5 bimodal entries (max 0.9998) — the disclosed instability class | `exp11_oracle_ranking_power/` (driver `experiments/exp11_oracle_ranking_power.py`, pilot 4/4; figure `experiments/plots/fig3c_oracle_ranking.py`) |
| Exp 12 (Fig 3d) | Docking-power profile on the **v3 extension of the aptamer anchor set** (user-approved 2026-08-27: docking anchors 5 → 19 complexes / 14 independent protein targets — the retained five plus fourteen newly curated under the registered admission discipline; Part-A entries carried verbatim; generator `experiments/curate_e1_anchor_set_v3.py`, assertion-checked, deterministic; SOMAmer-class (4ZBN/8J1Q/7YQ3/9SA8/4NI7/7JTN/5UC6/6TXR) and mirror-image (4WB2/4WB3/4R8I) chemistries rejected with RCSB-chemcomp-verified reasons; 18 rejection classes registered). Per complex: native pose + 20 seeded rigid-body decoys (θ~U(6°,18°), d~U(1.5,5) Å, seed 1000+i — offline-calibrated so the 1HVU decoy-RMSD distribution matches the retained evidence; contact computation reproduces retained 1HVU native n_contacts = 152 exactly); chemistry mapping per anchor-set conventions (DNA→RNA T→U renaming; 2′-OMe/2′-F/FANA via NUC_MAP, the 8EPK precedent). One zero-intervention pass through the platform production tool path (ToolExecutor.run_tool → deployed egarps 8023, `academic=False` only); CapGate advisory; every call audited to `platform_audit.jsonl`; gate = native top-1 in ≥ 2/3 of complexes, analysis-side only | **399 poses attempted, 397 scored (2 reproducible service-side pose failures disclosed: 8ZBF decoy16, 5HRU decoy13 — retried once, reproduced; their complexes analysed with 20 candidates)** (pilot 3/3; wall ≈ 4.6 h, median 38 s/pose). **19/19 complexes measured, 0/19 native top-1 (gate ≥ 2/3 failed decisively)** — native ranks 6–20 of 21 (deepest: 9T74 RBD 20/21); native scores below the median decoy in most complexes (1HVU native 0.008 vs decoy median 0.34); within-decoy Spearman(np, −RMSD) weak and mixed (−0.59 to +0.44) — the score does not track pose quality. Vs retained evidence (the 5 v2 complexes): headline 0/5 → 0/19 invariant; native-np deltas at service-variance level (max +0.0058, 1HVU); per-complex ranks shift under the regenerated decoy protocol (4DII 21→15, 4I7Y 4→12, 3DD2 19→17, 1HVU 10→15, 8EPK 10→18) — disclosed as protocol re-registration effects, decoys being newly generated | `exp12_docking_capability/` (driver `experiments/exp12_docking_capability.py`, pilot 3/3; figure `experiments/plots/fig3d_docking_lollipop.py`; anchor set `data/benchmarks/external_anchors/aptamers/e1_anchor_set_v3.json`) |
| Exp 13 (Fig 3e) | EGARPS affinity-calibration profile, the retained P2 pilot's question re-registered at full anchor-set scale (user-confirmed 2026-08-28: `e1_anchor_set_v3.json` verbatim — 95 entries / 9 targets, 62 Kd binders + 5 binder_no_kd + 28 negatives; ridgeline split rule pre-registered: negatives with 'rand' in id = the in-silico random-sequence class (17), the rest literature negatives (11), asserted 11+17=28; the retained pilot's 15 records recovered from git e601913 and embedded in the driver as the 1:1 reference — 12/15 ids live in v3, the IgE pair and legacy sarsn_aptamer disclosed as dropped in anchor-set evolution). One zero-intervention pass through the platform production tool path (ToolExecutor.run_tool → deployed rhofold 8005 / proteinx 8022 / egarps 8023, GPU-pinned 0/1/2 inherited; fixed protocol args only); CapGate advisory; every call audited to `platform_audit.jsonl`; P2 gates re-registered verbatim (ρ ≥ 0.6 AND AUROC ≥ 0.8), analysis-side only | **95/95 successful, 0 failures** (pilot 6/6; wall ≈ 4.4 h, 157–250 s/entry). **Thrombin 6-point Kd series ρ = +0.486 (CI −1.0–1.0) — ranking gate fails**; the retained 4-point series re-measures ρ = 0.20 vs retained 0.40 (Δ −0.2, realization variance on n = 4). **Pooled binder-vs-negative AUROC = 0.5225 (95% CI 0.391–0.652, 62 vs 28) — screening gate fails, CI covers chance; the retained pilot's below-chance 0.356 (9 vs 5, CI 0–0.76) does not survive scale** — the honest reading upgrades from 'directionally inverted' to 'uncalibrated, chance-level' (secondary: all-binders variant 0.537; ProteinX 0.514; RhoFold 0.461 — all chance). Per-entry inversion reproduces 1:1 (pegaptanib 1.27e-6 vs scrambled TBA 0.983; retained 1.9e-6/0.987); all three ridgeline classes span the full 9-order score range, medians interleaved (0.223 / 0.0014 / 0.022). Legacy-12 1:1: median \|Δnp\| = 7e-4, 3 large shifts (hd22 0.238, toggle25t 0.219, random30_a 0.930) = the disclosed EGARPS bimodal/realization class; vs Exp-10 v3 per-entry: RhoFold max \|Δ\| = 0 (bit-deterministic), ProteinX median 0.007, EGARPS median 5.7e-4. **Verdict: NO-GO on both P2 gates — no validated affinity calibration** | `exp13_affinity_calibration/` (driver `experiments/exp13_affinity_calibration.py`, pilot 6/6; figure `experiments/plots/fig3e_affinity_calibration.py`) |
| Figs 4–6 campaigns, E21/E22 baselines | — | to be run under the reset (Figs 3b–e complete as Exps 10–13 + the v3 Part-A re-runs 2026-08-28: anchor set 6 → 9 targets / 66 → 95 entries — FGF2, swine H3 HA, IFN-γ admitted; SARS-CoV-2 RBD and HIV-1 RT FANA rejected at the curation gate (sequence printability); exp10 v3 95/95 → 27 cells, 2 nominal screening passes all-CIs-cover-chance; exp11 v3 54/54 → 27 cells, 4 nominal ranking passes all-CIs-span-zero; figures re-rendered on the v3 summaries) | — |

### 3.1 Tier 1 — legacy campaign (Figs 2–7): conclusions downgraded, files deleted 2026-08-25

Data collection for the legacy figure campaign completed pre-reset; the files
were deleted in the 2026-08-25 reset and the conclusions survive only in the
downgraded form established by the P0–P3 pilots and the E2 audit (claim
survival 0/2). One-line status per figure:

| Figure | Data | Verdict-file pointer | Downgraded conclusion |
|--------|------|----------------------|------------------------|
| 2 platform quality | ✅ 210/210 tasks | `fig2_summary.json` | Platform runs and outputs beat biological nulls (CAI 0.745 designed vs 0.729 WT vs 0.672 random; panel refreshed 2026-08-11: OTC/PDGFB replaced the two oversized targets, and the legacy advisory-abort siRNA task completes under current governance); small-molecule scoring profiled two-sided (in-distribution AUROC 0.974/0.983 exactly reproducing published power after the RNAsmol v0.3.0 preprocessing-fidelity fix; out-of-distribution short aptamers show no demonstrated near-cognate discrimination) — `rnasmol_boundary_panel.json` |
| 3 Type-I BMC | ✅ 240/240 | `fig3_summary.json` | No significant fixed-reference ASF difference at any BMC depth (bmc×1 p = 0.81 NS) |
| 4 Type-II BMC | ✅ 228/240 | `fig4_summary.json` | Ungated egarps/hypervolume effects (p ≈ 2e-4) **confounded** — unprofiled oracle (P2/E1) + budget (P0); not a coordination claim |
| 5 mechanism ablations | ✅ 141 + 12 boundary | `fig5_summary.json` | No panel-b/c test survives BH-FDR; λ clamp contains extreme starts; negative controls clean |
| 6 governance/backends | ✅ 38 + 29 | `fig6_quality_ablation.jsonl`, `fig6_backends.jsonl` | QualityAgent advisory-only (both arms 19/19); backend matrix: deepseek 19/19, nominal claude arm 8 endpoint-misconfig failures (historical fact; extension cancelled, §4) |
| 7 case studies | ✅ 3/3 | `fig7_cases/*/case_summary.json` | End-to-end cases complete in minutes-to-hour and land near anchors on score-chain metrics; Case B is **not** a superiority claim (E2) |

### 3.2 Tier 2 — calibrated-agent campaign (E1–E8): verdicts

| Exp | Question | Verdict | Verdict / report files |
|-----|----------|---------|------------------------|
| E1 | What capabilities do the deployed oracles have? | **NO PASS** on screening (0/18 cells, AUROC > 0.8 gate), ranking (no ρ ≥ 0.6), docking (0/5 native top-1) | `e1_capability_summary.json` (pilot), `e1_capability_summary_v2.json` (6-target extension) |
| E2 | Do ungated legacy claims survive profiling? | Survival **0/2** (< 70% gate) → audit story holds | `E2_SELF_AUDIT_FIG4_FIG7B.md` |
| E3 | Does dual gating cut false-positive claims? | **GO**: FP rate 57.9% → 0%, TP retention 112.5%, gated overreach events 0 (vs 23) | `e3_runs_full_summary.json`; write-up `RESULTS4_E3_MATERIALS.md` |
| E4 | Does cross-campaign memory improve efficiency or design quality? | **NO-GO** (full matrix): budget saving 74.2% (814 vs 3153 evals) but all 3 learning slopes positive (t p = 0.91) and 4/4 quality metrics NS; memory strategy abandoned | `e4_pilot_summary.json`, `e4_full_summary.json` |
| E5 | Gated constraint navigation (selection layer) | **S0 GO** (τ = 1.0, 3 LLM calls); **S1 NO-GO** (3/5 cells failed: A1AT R3, Insulin D1, GFP D2; EPO/IL-2 single-target GO); every failure structural in the generation-method layer | `e5_verdict_s0.json`, `e5_verdict_s1.json` (per-target overwrite semantics — see fact sheet), report `E5_REPORT_2026-08-09.md` |
| E6 | Generation-layer navigation (GenNav) | **S0/S1/S2 GO**. S2 primary endpoint: per-profile JCD-pass McNemar C vs A (n = 54) **p = 1.86e-09, discordant 30:0**, c_e2e_gene = 1.0. Secondary endpoint **failed and disclosed** (Wilcoxon p = 1.65e-07 passes; quality bundle fails, driven by HER2 `feasible_gears = []` degrade) | `e6_s2_verdict_aggregated.json` (S2; do not cite per-stage verdict files), closeout `HANDOFF_2026-08-10_E6_CLOSED_S2_GO.md` |
| E7 | mRNA-side oracle profiling (GEMORNA 5′UTR MRL on measured-MRL anchors, Sample et al. GSE114002) | **GO** (2026-08-11): all three families pass both E1-identical gates — screening AUROC **0.990 / 1.000 / 1.000**, ranking ρ **0.926 / 0.920 / 0.835** (706 anchors, zero LLM); 3′UTR stability predictor registered unprofiled → gated off | `e7_mrna_oracle_profile_summary.json`, `e7_gate_demo.jsonl`; anchor set `data/benchmarks/external_anchors/utr_mrl/e7_mrl_anchor_set.json` |
| E8 | Aptamer-side GenNav (ODesign length/seed gears; budget-matched 48-cap arms) | **Primary endpoint NOT met** (2026-08-11): McNemar **b=3/c=1, p = 0.625** (n = 30); C repairs all three rule-arm failures it meets (BSA compact; VEGF / SARS-CoV-2 N extended), one self-shortfall (MBP compact 4/5); C e2e 9/10 vs A 7/10 at mean 36 vs 48 raw spend; task largely saturates → registered as a scope finding (DECISIONS.md Part 2 row 9), not an advantage claim | `e8_verdict_s2.json`, `e8_runs_s2.jsonl`, audit `e8_audit/` |

Pivot pilots P0–P3 and the junction line (P1, P1 v2, junction-integrated
optimizer, ddG Phase-0 pilot) are summarized with exact numbers in
[`PAPER_FACT_SHEET.md`](PAPER_FACT_SHEET.md) §3; verdict files
`p0_budget_matched_summary.json`, `p1_junction_optimizer_summary.json`,
`p1_v2_stability_sweep_summary.json`, `junction_integrated_optimizer_summary.json`,
`junction_ddg_pilot_summary.json`, `p2_aptamer_calibration_summary.json`,
`p3_guided_vs_unguided_summary.json`.

Failure taxonomy across all campaigns: `failure_taxonomy.json` (35 legacy final
failures, all deterministic boundaries or explicit governance/misconfig
outcomes; 2026-08-11 note: the two LinearDesign-OOM targets have been replaced
in the benchmark panel by OTC/PDGFB, and the one legacy advisory abort completes
on rerun under current governance — the taxonomy file is kept as the historical
record). Model/API provenance: `MODEL_API_USAGE.md` (sole external LLM in all
results: DeepSeek `deepseek-v4-pro`).

---

## 4. Cross-LLM Backend Matrix — Extension Cancelled (2026-08-10)

The v3 plan to extend the Fig-6b backend matrix (purchasing 5 additional API
keys for OpenAI/Anthropic/Alibaba/Google arms) is **cancelled by user
decision**: DeepSeek's behavior on the advisory-only touchpoints extrapolates —
no material difference across backends is expected, and the system is
deterministic apart from those calls. The already-collected fig6b data is kept
and cited as historical fact: DeepSeek arm 19/19 (93 QualityAgent calls,
414,088 prompt + 194,261 completion tokens); the nominal Claude arm's 8
failures were endpoint misconfiguration (404 against a gateway that does not
serve it), never a model-quality result. See `DECISIONS.md` Part 1(d).

---

## 5. Reproduction Pointers

- Reset-run evidence: `experiments/results/exp1_rnadesign210/` (Exp 1) —
  per-lane JSONLs + `summary.json` + enforce probe; driver
  `experiments/exp1_rnadesign210.py` (pre-registration in its docstring);
  services GPU-pinned by `experiments/exp1_bring_up_services.sh`.
- Dataset audit/repair tooling: `experiments/audit_rnadesign210.py`,
  `experiments/fix_rnadesign210.py`, `experiments/reground_tool_chains.py`
  (report: `experiments/results/rnadesign210_audit.json`).
- SelfModel regeneration: `experiments/build_default_self_model.py` (reads
  the retained e1_v2/e7/rnasmol/e16_e17_e18 evidence chain).
- CLI regression: `run_pa_test.py <006..036>` over `pa_benchmarks.json`
  (006–024: original batch; 025–036: batch-B fresh-data batch incl. GenNav
  navigation runs).
- Agent-core suite: `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x`
  (baseline 635 passed, 2026-08-22).
- Conventions: JSONL = one record per run; analysis never reads session logs
  directly — only the JSONLs/summaries above.
