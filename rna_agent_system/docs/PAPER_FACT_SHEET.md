# Paper Fact Sheet — Verified Numbers from `experiments/results/`

> **Provenance note (2026-08-18, extended 2026-08-22)**: the experiment
> drivers, one-off repair scripts and HANDOFF notes named below
> (`run_e*_gennav_aptamer.py`, `swap_fig2a_targets.py`, `e3_adjudicate.py`,
> `HANDOFF_2026-08-10_*.md`, …) were deleted in the simplification passes
> (DECISIONS.md (n)/(y)); every number cited here is backed by the retained
> verdict/run files under `experiments/results/`.

> **Purpose**: fact-check table for manuscript writing. Every number below was copied verbatim from
> the named result file (JSON field path given); nothing was recomputed. Claims listed in the
> audit request are marked **VERIFIED** (file agrees), **VERIFIED-WITH-NUANCE** (number agrees but
> wording/semantics need care), or **MISMATCH** (file disagrees — correction given).
> All result files live in `rna_agent_system/experiments/results/` (gitignored but on disk).
> Compiled 2026-08-10.

> **Panel-lettering note (2026-08-25)**: section headings and data keys below use
> the **legacy (paper-v2-era) figure letters** — these strings match the keys inside
> `fig2_summary.json` and the on-disk data files and are kept verbatim. The current
> manuscript lettering is `docs/FIGURE_PLAN_V5.md`. Mapping: legacy Fig 2 → v5 Fig 2
> with letters remapped (2a CDS nulls → v5 2b/2c; 2e inverse folding → v5 2d;
> 2c siRNA → v5 2f; 2i IRES → v5 2e; 2h small molecule → v5 2g; runtime/audit panels
> are now v5 2h/2i; the legacy 2f tertiary-design panel has no v5 main panel — data
> retained). "Fig 2d addendum" (RNAsmol boundary) → v5 Fig 2g + Fig 3h. Legacy Fig 3
> and Fig 4 (Type-I/II BMC ablations) and Fig 5 (mechanism ablations) → v5 Fig 3i
> (confounded improvement). Legacy Fig 6a (QualityAgent ablation) → v5 Fig 4h;
> fig6b (backend matrix) has no v5 main panel (LLM cost lives in v5 4i/6i). Legacy
> Fig 7 (case studies) → v5 Table 1.

---

## 1. System scale (platform claims)

| Claim | File evidence | Status |
|---|---|---|
| 41 scientific tools | `agent_core/tool_specs.py`: `len(TOOL_SPECS) == 41`, all production (demo tool retired 2026-08-22); `agent_core/tool_inventory.py` manifest: `scientific_tools: 41` (recounted 2026-08-18 after the simplification pass removed 12 dead tools — pre-cleanup 54 verified 2026-08-10). Paper convention: "41 scientific tools" = registered total | VERIFIED |
| 21 microservices, ports 8003–8024 | `microservices/` contains 21 service directories (recounted 2026-08-18; 22 before the codonw-slim service removal) | VERIFIED |
| 11 workflows | `docs/ARCHITECTURE.md` §Layer 2 ("All 11 workflows"); `agent_core/workflows/` has 11 workflow classes (mrna_cds_design, full_length_mrna_design, mrna_sequence_scoring, sirna_design, sgrna_design, aso_target_screening, ires_prediction, rna_aptamer_design, rna_secondary_structure_design, rna_tertiary_structure_design, rna_small_molecule_interaction) | VERIFIED |
| "20 external-repo **submodules**" | `rna_agent_system/external_repos/` contains **20 directories**, but `.gitmodules` registers only **17 submodule paths** (EGARPS, Protenix, RiboDiffusion are plain directories, not registered submodules) | **MISMATCH → correct to "20 external repos vendored under `external_repos/`, 17 of them registered git submodules"** |
| PA regression 31 tasks (006–036) | `rna_agent_system/pa_benchmarks.json` keys: '006'…'036' = 31 tasks (006–024 original batch; 025–036 the 2026-08-19 fresh-data batch B incl. two GenNav `navigation=true` entries) | VERIFIED |
| Batch-B fresh-data regression 12/12 | `experiments/results/pa_regression_batchB_2026-08-19/summary.tsv`: 12 rows, exit_code 0, failed_turns 0 (PA_035 row = post-fix rerun, first attempt documented in `VERIFICATION.md`); audit trail 4,106 → 5,747 events; both navigation runs 5/5 × 3 profiles no-degrade (`gennav_{1ca2,3cna}_navigation_result.json`: raw_spent 47/48 and 35/48 early-stop) | VERIFIED |

---

## 2. Legacy Figure 2–7 campaign (final state)

### Fig 2 — platform coverage & biological output quality (updated 2026-08-11)
- **Purpose**: one-shot success and output quality of all 11 workflows on the 210-task benchmark.
- **Design**: 210 tasks across 11 workflows (per-workflow task counts in `coverage`), single run each.
- **2026-08-11 refresh** (paper v2): (a) the one legacy failure (`04_sirna_design_009_gc_rich_target`, a 2026-07 QualityAgent abort under pre-governance-fix rules) was rerun 2026-08-11 and **succeeded in 91.4 s** — under the 2026-08-10 governance an LLM abort is advisory-only and cannot fail a run; (b) the two oversized fig2a targets (Zika_E_protein 3419 aa, Factor_VIII 2351 aa, both beyond the LinearDesign memory guard) were **replaced by OTC (354 aa, UniProt P00480, RefSeq NM_000531.6) and PDGFB (241 aa, P01127, NM_002608.4)**, translation-verified by `experiments/swap_fig2a_targets.py`; their fig2_cds_nulls records were pruned and the two new targets run through `make_cds_nulls.py`; (c) the small-molecule panel was rerun after the RNAsmol v0.3.0 preprocessing-fidelity fix (see below).
- **Exact numbers** (`fig2_summary.json`, regenerated 2026-08-11):
  - `total.n_tasks` = 210, `total.n_success` = **210** (`coverage.sirna_design` 22/22).
  - Fig2a CDS nulls (`fig2a_cds_nulls`): n = 20 WT / 200 random-synonymous / **20 designed** (cai_only).
    CAI medians: designed **0.7454304750202037**, WT **0.7285905932693981**, random **0.6723169743681472**.
    WT vs random: Mann-Whitney **p = 4.023013793756525e-07**, Cliff's δ = 0.688; paired WT-beats-random 15/20.
    MFE/nt medians: WT −0.05066, random −0.04728, designed −0.35573 (WT vs random p = 0.2304, NS).
  - Fig2e secondary-structure inverse folding (`fig2e_secondary_design`): **exact_match 22/25** (rate 0.88, median distance 0).
  - Fig2f tertiary design: n = 20, median pLDDT component 0.704.
  - Fig2c siRNA: n = 22, median off-target 0.0, zero-off-target 21/22, `quality_abort_cases` = [].
  - Fig2i IRES (`fig2i_ires`): n_pos = 3, n_neg = 49; **AUROC 0.762**, 95% CI [0.429, 0.98]; positives EMCV 0.8081 / HCV 0.4425 / Poliovirus 0.9356. *Legacy record (its protocol = sliding-window scores — per-sequence scores match the reset run's mode-2 arm exactly); the 2026-08-25 reset re-ran this panel as Fig 2e on the user-approved 9-positive panel (`experiments/results/exp5_ires_panel/summary.json`): mode-2 arm AUROC 0.673 (0.467–0.862, P=0.102), pre-registered mode-0 default-path primary 0.478 (0.311–0.649, P=0.841) — the numbers of record.*
  - Fig2h small molecule (`fig2h_small_molecule`, rerun 2026-08-11 with RNAsmol v0.3.0): 4 binders / 4 near-cognate / 9 random-chem; **AUROC vs random-chem = 0.722**, vs near-cognate = 0.312 (workflow-level mean of RNAsmol + GerNA-Bind; out-of-training-distribution boundary stands — near-cognate discrimination absent).
- **Verdict**: n/a (descriptive). **Conclusion**: platform runs 210/210; designed CDSs lift CAI over WT (0.745 vs 0.729) while WT itself is already above random (p = 4.0e-7); IRES finder is moderately discriminative; small-molecule scoring is profiled two-sided (below).

### Fig 2d addendum — RNAsmol two-sided boundary panel (`rnasmol_boundary_panel.json`, 2026-08-11; driver `experiments/run_rnasmol_boundary_panel.py`)
- **Purpose**: profile the *deployed* small-molecule oracle from both sides — its own training distribution and the out-of-distribution (OOD) short-aptamer panel.
- **Deployment-fidelity finding**: pre-fix, the v0.2.0 service (uppercased RNA vocab; corrected full adjacency) scored AUROC **0.7864** (robin test) / **0.4103** (pdb test) on RNAsmol's own held-out splits; the upstream-official pipeline (`preprocessing.py` + `test.py`, same checkpoints) scores **0.9744 / 0.9828**. After the v0.3.0 verbatim-faithful preprocessing port, the service reproduces the official numbers **exactly** (0.9744/0.9828).
- **In-distribution**: robin_molperturbation test n = 1492, AUROC **0.9744** (95% CI 0.9678–0.9804); pdb_molperturbation test n = 170, AUROC **0.9828** (0.9615–0.9971; ≤500-nt subset 0.9788, n = 126; 44 rows truncated service-side at 500 nt). Decoy case studies: FMN_ribocil true binder rank **2/1601** (0.125 pct), MALAT1_furamidine rank **7/265** (2.6 pct).
- **Out-of-distribution** (fig2h 17 pairs, RNAsmol-only rescoring): binder-vs-random-chem AUROC **0.7222** (CI 0.278–1.0), binder-vs-near-cognate **0.5625** (CI 0.063–1.0) — both CIs include chance; guanine-riboswitch direction inverted (binder 0.27 < near-cognate adenine 0.98).
- **Verdict**: GO (in-distribution AUROCs > 0.8 gate with CIs excluding 0.5; decoys in top 5%; OOD chance-consistent) — the two-sided boundary statement the paper reports.
- **Reset re-run (2026-08-26)** — the numbers of record for Fig 2g (`experiments/results/exp7_rnasmol_boundary/`, driver `experiments/exp7_rnasmol_boundary.py`, pre-registered docstring, pilot 37/37): the identical two-sided profile re-executed zero-intervention against the frozen platform (deployed service at packaged CPU default via its own start.sh; sequences and SMILES verbatim/case-preserving; checkpoint auto-selection by data-provenance hints only; no thresholds). **3,545/3,545 pairs scored, zero failures.** Every registered metric reproduces exactly: robin **0.9744** (0.9678–0.9803; this run's bootstrap), pdb **0.9828** (0.9607–0.9970; ≤500-nt subset 0.9788, n = 126, 44 truncated), FMN **2/1601** (0.125 pct), MALAT1 **7/265** (2.642 pct), OOD **0.7222** (0.2778–1.0) / **0.5625** (0.0625–1.0). Per-pair cross-check vs the retained evidence: medians ~1e-6 (MALAT1 ≤ 3.8e-5, OOD ≤ 6.3e-4); a minority of near-decision-boundary inputs amplify inference-backend arithmetic (robin max 0.021 at 1/1492 pairs > 1e-3; pdb 0.047 at 1/170; FMN 0.367 at 53/1601 — one unstable near-0.5-band decoy, idx 367, re-scored bit-identical to confirm this run's determinism; the retained run's device is unrecorded) — no registered metric moves. Verdict GO on all three axes.

### Fig 2h — End-to-end runtime by workflow (Exp 8, reset 2026-08-27)
- **Purpose**: wall-clock runtime per target of each of the 11 workflows, platform as shipped.
- **Design**: 241 timed end-to-end runs = all 210 RNADesign-210 tasks + all 31 PA regression sessions (PA_006–PA_036, each timed as one whole form session); one `cli/form_chat.py` subprocess per run through the user form entry; inputs verbatim, no thresholds/parameter presets; CapGate advisory (the documented regression convention); services pre-warmed and GPU-pinned 0/1/2 (runtime measures the delivered workflow, not cold model loads); lanes strictly sequential (no cross-lane contention). Successful runs only enter the distribution (`experiments/results/exp8_runtime/`, driver `experiments/exp8_runtime.py`, pre-registered docstring, pilot 4/4).
- **Result**: **241/241 successful.** Pooled median **2.6 min** (mean 4.4); per-workflow medians: mRNA scoring 2.5 s, small-molecule 0.23 min, ASO 0.28 min, secondary structure 1.21 min, IRES 1.34 min, siRNA 2.61 min, sgRNA 3.20 min, CDS 3.21 min, tertiary structure 3.87 min, full-length mRNA 4.32 min, aptamer 6.29 min. Completion: 76.3% ≤5 min, 92.9% ≤10 min, 98.3% ≤30 min, **240/241 ≤1 h** — the four >30-min runs are all multi-turn aptamer PA sessions (42.4/42.9/59.9/**98.6** min; the >1 h one is the GenNav `navigation=true` session PA_028); suite-task maximum 27.0 min (CDS design).
- **Disclosed amendment (registered before the PA_028 re-run)**: the PA-arm timeout (3600 s, calibrated on suite-task maxima) under-covered multi-turn navigation sessions — PA_027 finished at 3593 s and PA_028 was killed at 3600 s while progressing normally (orphaned turn 2 later completed at ~5740 s, exposing a driver defect: timeout killed only the direct child). Amended to 10800 s + process-group kill; PA_028 re-run once under the amended budget (fresh session, **5917.2 s** — consistent with the orphan reconstruction); original censored record retained in `pa_batch.jsonl`; orphan-overlap window verified uncontaminating for PA_029 (42.63 s vs siblings 42.15/42.52 s).

### Fig 3 — Type-I BMC (full-length mRNA) ablation
- **Purpose**: does BMC coordination (×1/×2/×3) beat Serial on the full-length mRNA workflow?
- **Design**: 20 targets × 4 conditions (serial, bmc_x1/x2/x3) × 3 reps = 240 jobs; **240/240 success** (`n_jobs_success`). Primary metric: fixed-reference ASF recomputed per target (`asf_method` field; stored per-run utopian ASF explicitly not used).
- **Pre-registered gate**: none in file; inference = paired Wilcoxon per target (mean over reps), BH-FDR over 33 tests (11 metrics × 3 comparisons) (`paired_tests_note`).
- **Exact numbers** (`fig3_summary.json` → `paired_tests.asf_fixed.bmc1_vs_serial`): n = 20, median serial 0.14448455044700484 vs bmc1 0.1410091030196616, **Wilcoxon p = 0.8123550415039062**, Cliff's δ = 0.0, q_BH = 0.9854. bmc2 p = 0.2455, bmc3 p = 0.1536 — all NS across all 11 metrics (all q_BH ≥ 0.85).
  - Per-target fixed-ASF means (serial → bmc_x1): HER2 **0.1652803069369776 → 0.051062237848514526**; Beta_galactosidase **0.10622147686733906 → 0.025873459811008467**; Influenza_HA_H1N1 **0.13948462644295323 → 0.03030539776546423**.
  - Burial (`burial.per_target_repair.bmc1_vs_serial`): 18 targets buried under serial; **bmc_x1 cleared 4/18**, 14 still buried (bmc_x2: 0/18; bmc_x3: 1/18). Run-level burial proportions (any): serial 38/60 = 0.633, bmc_x1 27/60 = 0.45.
  - Rounds execution: bmc_x1 completed all rounds in 40/60 runs; median elapsed: serial 1458.98 s, bmc_x1 1769.74 s.
- **Verdict**: no significant ASF difference at any BMC depth. **Conclusion**: on Type-I, coordination neither helps nor hurts the fixed-reference scalarization; bmc_x1 incidentally cleared AUG/Kozak burial in 4 of 18 serial-buried targets.

**Claim check (Fig 3)**: bmc1 vs serial fixed-ASF p = 0.81 (NS) ✓ (exact 0.81236); HER2 0.165→0.051 ✓; Beta_gal 0.106→0.026 ✓; Influenza 0.139→0.030 ✓; burial repair bmc1 4/18 ✓ — **all VERIFIED**.

### Fig 4 — Type-II BMC (aptamer) ablation
- **Purpose**: does BMC coordination beat Serial on the RNA–protein aptamer workflow?
- **Design**: 20 targets × 4 conditions × 3 seed sets = 240 jobs; **228/240 success** — Ferritin failed all 12 cells (`cli_failure`), leaving 19 targets for ASF/component tests (n = 19) and 57 (target, seed) cells for hypervolume.
- **Pre-registered gate**: none in file; BH-FDR over up to 24 tests (`paired_tests_note`).
- **Exact numbers** (`fig4_summary.json` → `paired_tests`):
  - `metrics.egarps_component.bmc1_vs_serial`: n = 19, median serial 0.10096574466666668 vs bmc1 0.48522250666666666, **Wilcoxon p = 2.09808349609375e-04**, **Cliff's δ = +0.45706371191135736**, q_BH = 6.713e-04.
  - `hypervolume.hv3d.bmc1_vs_serial`: n = 57, median serial 7.892086226319085e-04 vs bmc1 3.5790891320509623e-03, **Wilcoxon p = 2.6140122552847835e-04**, δ = +0.2736, q_BH = 6.971e-04.
  - `metrics.asf_fixed.bmc1_vs_serial`: **p = 0.07283401489257812, δ = −0.2410** (NS, direction negative). rhofold/iptm components all NS.
- **Verdict**: significant ungated main effect on egarps and hypervolume — later shown confounded (see §3 P0 and §4 E2). **Conclusion**: BMC×1 raises the EGARPS component and 3-D hypervolume, but the effect is concentrated in an unprofiled oracle and a pool-size-sensitive metric.

**Claim check (Fig 4)**: egarps bmc×1 p = 2.1e-4, δ = +0.46 ✓ (exact p = 2.098e-4, δ = 0.4571); 3-D hypervolume p = 2.6e-4 ✓ (exact 2.614e-4) — **VERIFIED**.

### Fig 5 — mechanism ablations
- **Purpose**: isolate reference-point handling (b), utopian vs fixed reference (c), λ boundedness (d), and negative controls (e).
- **Design** (`panels.*.design`): b = 9 targets × {source_aware, pool_average} × 3 seed sets, BMC×1 (n = 27 pairs); c = 9 targets × {utopian, fixed_reference} × 3 seed sets (n = 27); d = 3 targets × λ = 18 extreme start × 3 reps (9 runs); e_type1 = 3 small proteins × {serial, bmc1} × 3 reps, utr_mode=short (negative control); e_type2 = explicit hotspots (Thrombin only; SARS-CoV-2 Nucleocapsid = declared boundary). 153 jobs, 141 success; boundaries documented in `boundary` (Ferritin b/c 6 cells, Nucleocapsid e2 6 cells).
- **Exact numbers** (`fig5_summary.json`):
  - Panel b: all four tests NS — asf_fixed p = 0.4996 (δ = 0.026), egarps p = 0.4996, rhofold p = 0.4140, iptm p = 0.5460; all q_BH = 0.7129.
  - Panel c: asf_fixed p = 0.2584 NS; **egarps raw p = 0.024539664387702942 but q_BH = 0.36809496581554413 → NS after BH-FDR**; rhofold p = 0.5057 NS; iptm p = 0.0815 NS.
  - Panel d boundedness: λ_initial = 18.0 (of clamp **[0, 20]**), `all_trajectories_within_clamp` = **true**, λ_final median 14.0, range [14.0, 20.0].
  - Panel e_type1 (negative control): all 5 tests NS (asf p = 0.0977, components p ≥ 0.20) — as designed.
- **Verdict/Conclusion**: reference-point mode and reference computation do not change outcomes; the λ clamp contains extreme starts; negative controls are clean.

**Claim check (Fig 5)**: "b/c 全 NS" ✓ **VERIFIED-WITH-NUANCE** — panel c egarps is nominally p = 0.0245 pre-correction; it is NS only after BH-FDR (q = 0.368). Cite as "no test survives BH-FDR". λ = 18 clamped back into [0, 20] ✓ VERIFIED.

### Fig 6a — QualityAgent ablation (note: no `fig6_summary.json` exists; numbers from raw JSONL)
- **Purpose**: does LLM quality review change end-to-end success on the PA regression suite?
- **Design**: 19 PA tasks (PA_006–PA_024) × 2 arms (quality_on / quality_off) = 38 runs (`fig6_quality_ablation.jsonl`).
- **Exact numbers**: `final_success` = true for **19/19 quality_on and 19/19 quality_off**; total retry counts 2 (on) vs 0 (off). (Fig 6b backend matrix, `fig6_backends.jsonl`: 29 records, 21 success; 8 failures all `endpoint_misconfig` — the nominal Claude arm 404'd against a gateway that does not serve it; DeepSeek arm 19/19.)
- **Conclusion**: quality review is advisory-only for success rate on this suite; both arms succeed 19/19.

**Claim check (Fig 6a)**: both arms 19/19 ✓ — **VERIFIED**.

### Fig 7 — three end-to-end case studies
- **Purpose**: worked examples chaining workflows with literature anchors.
- **Exact numbers**:
  - **Case A** (`fig7_cases/A/case_summary.json`): SARS-CoV-2 Spike mRNA. Designed best `cds_cai` = **0.9459299998627659** vs anchor BNT162b2 **0.9515304128311646** (mRNA-1273 0.9787, WT spike 0.6736); designed full_mfe_per_nt −0.2399 vs BNT162b2 −0.3443; utr5_mrl 4.45 vs 6.22. `timeline_seconds` = **5110.21 s = 85.2 min**. Note: designed candidate still `aug_buried = kozak_buried = true` (as is the BNT162b2 anchor under the fragment-fold metric).
  - **Case B** (`fig7_cases/B/case_summary.json`): anti-VEGF aptamer. Top candidate `cand_43edb912979a` `egarps_component` = **0.7046922** (RhoFold pLDDT 82.59, ProteinX ipTM 0.4881) vs pegaptanib anchor `egarps_native_probability` = **5.0472704e-07** (pLDDT 41.96, ipTM 0.4240); `timeline_seconds` = **2795.52 s = 46.6 min**. File caveats: different complex sources (ODesign vs ProteinX PDB), unmodified parent sequence (Kd 49 pM, Tucker 1999).
  - **Case C** (`fig7_cases/C/case_summary.json`): NSP12 siRNA. `safety_table` top-5 all `off_target_count` = **0.0**, specificity 1.0, GC 0.381 in [0.3, 0.6]; `timeline_seconds` = **72.83 s ≈ 73 s**.
- **Conclusion**: end-to-end cases complete in minutes-to-~hour and land near literature anchors on *score-chain* metrics (see E2 for why Case B's 6-orders-of-magnitude gap is not a superiority claim).

**Claim check (Fig 7)**: A 0.946 vs 0.952 in 85 min ✓; B 0.70 vs ~5e-7 in 47 min ✓ (exact 46.6 min); C top-5 zero off-target in 73 s ✓ — **all VERIFIED**.

---

## 3. Pivot pilots P0–P3 and the junction line

### P0 — budget-matched control (`p0_budget_matched_summary.json`, 2026-08-03)
- **Purpose**: is the Fig-4 Type-II main effect explained by the doubled sampling budget?
- **Design**: bmc_x1 vs serial_ext16 (budget-matched, 16 generated each), 4 targets (BSA, Lysozyme, Thrombin, VEGF) × 3 seeds = **12 cells**, metric = egarps_component best-of-pool.
- **Pre-registered gate**: GO if Cliff's δ ≥ 0.3 (`go_threshold` = 0.3).
- **Exact numbers**: **δ = 0.2777777777777778**, **Wilcoxon paired p = 0.12939453125**, bmc_x1 wins **9/12**; medians [IQR]: bmc 0.6242 [0.5325, 0.9017] vs serial_ext16 0.2417 [0.1551, 0.8789].
- **Verdict: NO-GO** — `verdict_meaning`: "budget explains the Fig-4 Type-II main effect; pivot to adaptive budget allocation (P3)".
- **Conclusion**: once budgets match, the coordination effect is small and non-significant.

**Claim check**: δ = 0.278 vs threshold 0.3 NO-GO ✓; 9/12 ✓; p = 0.129 ✓ — **VERIFIED**.

### P1 — junction-aware codon optimizer (`p1_junction_optimizer_summary.json`, 2026-08-03)
- **Purpose**: repair 5'UTR–CDS junction burial at design time via codon-level optimization.
- **Design**: 18 runs (6 targets × 3 reps); local CAI tables + LinearFold only, no LLM.
- **Pre-registered gate**: hard targets burial eliminated ≥ 2/3 AND j1 mfe/nt improved AND CAI Δ > −0.02; easy targets not degraded.
- **Exact numbers**: baseline buried 14 runs, **fixed 13/14 (rate 0.929)**, unfixed = Insulin_r0; hard targets 7/7 fixed; **CAI Δ median +0.0025 (min −0.0026)**; beats bmc1 j1 mfe/nt in 13/18 (`j1_mfe_per_nt_vs_bmc1_wins`; the `go_no_go.evidence` text says 16/18 — internal inconsistency in the file, the structured field says 13/18). Full-construct stability cost: +0.009/nt (large proteins), +0.044/nt (small).
- **Verdict: GO** (hard 8/9 fixed ≥ 6/9 required).
- **Conclusion**: junction burial is repairable at negligible CAI cost, but opening junctions costs global stability — motivating v2.

**Claim check**: "修 13/14、CAI 中位 +0.0025 GO" ✓ — **VERIFIED**.

### P1 v2 — stability-weight sweep (`p1_v2_stability_sweep_summary.json`, 2026-08-04)
- **Purpose**: can a tunable stability term w_stab ∈ {0, 0.1, 0.25, 0.5, 1.0} control the P1 stability cost?
- **Design**: 6 targets × 3 reps × 5 weights = 90 cells (18 per weight; file `per_weight` n_cells = 18; hard-buried-at-baseline = 7).
- **Pre-registered gate**: hard repair rate ≥ 2/3 AND stability cost ≤ 50% of v1 (v1 median 0.021996110355454235/nt) AND CAI drop ≤ 0.02.
- **Exact numbers**: hard repair 7/7 at every weight (rate 1.0), but median stability cost per nt stays 0.0214–0.0249 (never ≤ 0.0110); `go_weights` = [] → **decision NO-GO**. Post-hoc mechanism: the terminal-window proxy moves the wrong way (−0.1405 → −0.1153 as w_stab rises) because it overlaps the junction window; true full-construct cost is flat and driven by long-range rearrangements invisible to 160-nt windows.
- **Conclusion**: local proxies structurally cannot control global stability — pushed the junction term into the generative tool (P2 junction-integrated).

### Junction-integrated LinearDesign optimizer (`junction_integrated_optimizer_summary.json`, 2026-08-04)
- **Purpose**: pre-registered acceptance of the C++ junction-patch LinearDesign (w_jun penalty inside the design objective).
- **Design**: 6 targets × 3 reps × 4 w_jun {0, 0.5, 1, 2} = **72 cells, 72/72 success**, 2.483 h runtime; λ = 2.0 per cell.
- **Pre-registered gate**: hard repair ≥ 2/3, stability cost ≤ 0.010998055177727117/nt, CAI drop ≤ 0.02.
- **Exact numbers**: hard repair rates 1/7, 0/7, 2/7, 1/7 across w_jun (all ≤ 0.286); median stability cost 0.0150–0.0313/nt (all over threshold); median ΔCAI ≈ −0.06 (passes trivially); median junction window pair count falls 43 → 29.5 → 15 → 0. `go_weights` = [] → **decision NO-GO**. Mechanism: at w = 2, 6/9 hard cells have zero window pairs in the global fold yet 5 remain buried under the fragment-fold metric — **metric/optimizer coordinate mismatch** (global CKY fold vs isolated 40-nt fragment fold).
- **Conclusion**: a global-fold penalty cannot repair a fragment-fold burial metric; capability kept as locked tool, not wired into workflows.

### Junction ddG Phase-0 pilot (`junction_ddg_pilot_summary.json`, 2026-08-05)
- **Purpose**: validate the full-length constrained-fold ddG metric (gate 1) and test Route C codon-shuffle repair (gate 2).
- **Design**: 3 targets (Insulin, EPO, Growth_hormone) × 4 λ {0, 1, 4, 10} × (1 parent + 8 shuffle variants) = **108 rows, 108/108 success** (12 parents, 96 variants); LinearFold constrained fold; ViennaRNA cross-check on 12 parents. Runtime 93.8 s.
- **Pre-registered gates**: gate 1 metric validity (constraint obedience; ddG ≥ 0; LinearFold-vs-Vienna parent consistency); gate 2 Route C (median W1 improvement ≥ 1.0 kcal/mol AND median ΔCAI ≥ −0.02 AND median |ΔMFE/nt| ≤ 0.01, in ≥ 2 of 3 targets).
- **Exact numbers**: gate 1 — obedience **216/216 (rate 1.0)**, **ddG ≥ 0 in 216/216**, **LinearFold vs Vienna parent Pearson r = 0.9449077954313464** (n = 12) → **GO**. Gate 2 — only **EPO passes (1/3)**: median W1 improvement **5.835000000000008 kcal/mol**, ΔCAI −0.0012, |ΔMFE/nt| 0.0081; Growth_hormone fails on |ΔMFE/nt| (0.0121 > 0.01) and Insulin fails on |ΔMFE/nt| (0.0125); `n_targets_pass` = 1 < 2 → **NO-GO**. Overall `decision` = **NO-GO** (→ plan A per LOCK §14 v2.8.0). Old-vs-new consistency check: buried candidates' median ddG_open_w1 = 4.56 vs unburied 5.70 (n = 78/30) — the old fragment metric is *not* validated by the new one.
- **Conclusion**: the ddG metric is valid and obedient; Route C shuffle repair does not generalize — ddG adopted as report/profile-only metric, auto-repair stripped.

**Claim check (ddG pilot)**: r = 0.945 ✓ (exact 0.94491); ddG ≥ 0 216/216 ✓; Route C 1/3 targets, EPO improvement 5.84 kcal/mol ✓ (exact 5.835) — **VERIFIED** (note the overall decision is NO-GO because gate 2 failed; gate 1 passed).

### P2 — aptamer calibration (`p2_aptamer_calibration_summary.json`, 2026-08-03)
- **Purpose**: does the EGARPS native_probability oracle track binding affinity for known aptamers?
- **Design**: 15 records (9 binders with Kd, 1 binder without Kd, 5 negatives) across Thrombin/VEGF/PDGF-BB/IgE/SARS-CoV-2 N; thrombin 4-point Kd series.
- **Pre-registered gate**: Spearman ρ ≥ 0.6 (Kd ranking, n = 4, reported without p-value per pre-registration) AND binder-vs-negative AUROC ≥ 0.8.
- **Exact numbers**: thrombin series **ρ = 0.39999999999999997**; binder (9) vs negative (5) **AUROC = 0.35555555555555557**, 95% CI [0.0, 0.7556]. Direction-inverting detail: random negatives random30_a np = 0.952 and scrambled_tba np = 0.987 exceed pegaptanib (1.9e-6) and PDGF aptamers (~1e-8).
- **Verdict: NO-GO** — per-target calibration gating added; optimization claims restricted to relative same-target comparisons.
- **Conclusion**: EGARPS np has no validated screening/ranking power for RNA–protein aptamers.

**Claim check**: thrombin ρ = 0.40 ✓; AUROC = 0.356 ✓; NO-GO ✓ — **VERIFIED**.

### P3 — guided vs unguided diagnosis (`p3_guided_vs_unguided_summary.json`, 2026-08-03)
- **Purpose**: does the LLM diagnosis content itself (beyond mechanics/budget) drive the BMC gain?
- **Design**: guided bmc_x1 vs unguided_2pass, identical mechanics and budget 16, 4 targets × 3 seeds = **12 cells**; no LLM in the loop (fixed patches replace diagnosis).
- **Pre-registered gate**: GO if Cliff's δ ≥ 0.3.
- **Exact numbers**: **δ = 0.2222222222222222**, **Wilcoxon paired p = 0.10986328125**, guided wins 9/12; medians [IQR]: guided 0.6242 [0.5325, 0.9017] vs unguided 0.5201 [0.2928, 0.7633].
- **Verdict: NO-GO** — "diagnosis content unsupported at pilot scale; BMC value reduces to adaptive budget allocation + resampling mechanics". File caveat: egarps objective failed P2 calibration.
- **Conclusion**: guidance content adds nothing measurable over unguided two-pass at matched budget.

**Claim check**: δ = 0.222 ✓; p = 0.110 ✓ (exact 0.10986); NO-GO ✓ — **VERIFIED**.

---

## 4. E1–E6 (calibrated-agent campaign)

### E1 — oracle capability profiling (`e1_capability_summary.json` pilot; `e1_capability_summary_v2.json` extension, 2026-08-04)
- **Purpose**: profile the three structure oracles (EGARPS np, ProteinX ipTM, RhoFold pLDDT) for scoring/screening/ranking/docking power before letting the agent rely on them.
- **Design**: pilot 29 sequence entries × 3 targets (9 oracle×target cells) + 63 poses (3 docking cases); **v2: 66 Part-A entries × 6 targets (18 oracle×target cells) + 102 poses (5 docking cases)** across Thrombin, VEGF, PDGF-BB, IL-17A, Angiopoietin-2, SARS-CoV-2 N.
- **Pre-registered gates** (`thresholds`): screening AUROC > 0.8; ranking Spearman ρ ≥ 0.6; docking native top-1 fraction ≥ 2/3.
- **Exact numbers (v2)**: **screening 0/18 pass** (best cell = rhofold_mean_plddt × PDGF-BB AUROC = **0.8 exactly**, 95% CI [0.3333, 1.0] — does not exceed the strict > 0.8 threshold; egarps × VEGF 0.708 CI [0.333, 1.0]); sensitivity grid: 6/18 cells pass AUROC > 0.6, 0/18 pass > 0.9. **Ranking: no cell reaches ρ ≥ 0.6** (best = rhofold × PDGF-BB ρ = 0.564). **Docking: 0/5 native top-1** — native ranks: TBA (4DII) **21/21**, Toggle-25t (3DD2) **19/21**, t1p1 HIV-1 RT (1HVU) **10/21**, DTri177 FIXa (8EPK) **10/21**, HD22-T27 (4I7Y) 4/18. `n_part_a` = 66, `n_part_b` = 102.
- **Verdict**: NO PASS on all three capabilities (`decision_bits`), pilot and extension alike (pilot docking 0/3).
- **Conclusion**: none of the deployed oracles may ground screening/ranking/docking claims for RNA–protein aptamers — the evidence base for DecisionGate/ClaimGate.

**Claim check**: 66 entries / 6 targets ✓; screening 0/18 with best rhofold×PDGF-BB = 0.8, CI 0.33–1.0 ✓; no ranking ρ ≥ 0.6 ✓; docking 0/5 with TBA 21/21, Toggle-25t 19/21, 1HVU 10/21, 8EPK 10/21 ✓ — **all VERIFIED** (PDB IDs confirmed against `e1_poses/` directory names: 4DII = TBA, 3DD2 = Toggle-25t, 1HVU = t1p1_hiv1rt, 8EPK = dtri177_fixa).

### E2 — self-audit of legacy claims (`E2_SELF_AUDIT_FIG4_FIG7B.md`, 2026-08-04)
- **Purpose**: re-adjudicate the two strongest legacy claims (Fig-4 main effect; Fig-7B pegaptanib comparison) through the profiling protocol, as the paper's worked example.
- **Design**: 2 in-house claims × 4-step audit (dependency declaration → profiling re-check → confound control → gated verdict). Pre-registered threshold: audit story holds if claim survival < 70%.
- **Exact result**: **survival 0/2 = 0% < 70%** — both claims "不存活 → 降级" (Fig 4: oracle capability absent per E1/P2 + P0 budget confound δ = 0.278 NS + fixed-reference ASF NS p = 0.073; Fig 7B: EGARPS × VEGF ρ = −0.024 / AUROC 0.708 not passing, complex-source incomparability, unrepresentable 2'-F/PEG modifications).
- **Conclusion**: without gating, the ungated pipeline (including this project's own earlier version) would have issued both claims — the empirical motivation for the gated architecture.

**Claim check**: self-audit survival 0/2 ✓ — **VERIFIED**.

### E3 — gated vs ungated agent (`e3_runs_full_summary.json`; pilot `e3_runs_pilot_summary.json`; write-up `RESULTS4_E3_MATERIALS.md`, 2026-08-04)
- **Purpose**: does the two-layer gate (DecisionGate + ClaimGate + SelfModel preloaded with E1 evidence) cut false-positive claims without killing true positives?
- **Design**: **20 synthetic audit tasks × 2 arms = 40 runs** (`e3_runs_full.jsonl` = 40 records; adjudicated claims: ungated 19, gated 11), same prompts/model (DeepSeek deepseek-v4-pro, temp 0, 2 calls per task-arm = 80 LLM calls total), deterministic blind adjudication (`e3_adjudicate.py`; blind map sealed). Pilot: 6 tasks × 2 arms = 12 runs.
- **Pre-registered gates** (`thresholds`): FP relative reduction ≥ 0.5; TP retention ≥ 0.9.
- **Exact numbers (full matrix)**: ungated FP rate **0.5789473684210527 (11 FP / 19 claims, 8 TP)** → gated FP rate **0.0 (0 FP / 11 claims, 9 TP, 1 suppressed, 1 borderline)**; `fp_rate_relative_reduction` = **1.0**; `tp_retention` = **1.125**; overreach events ungated **23** vs gated **0**. Ungated FPs concentrate in untrusted_oracle (9/11) — task-set discriminability = true. GO bits: all three green (user declared GO 2026-08-04 per RESULTS4 doc). Pilot (superseded): FP relative reduction −0.125, TP retention 0.5 — not met at pilot scale.
- **Conclusion**: on the audit set the gate eliminates false positives entirely (57.9% → 0%) while slightly increasing true positives (8 → 9); abstention, not silence, is the mechanism.

**Claim check**: 20 × 2 = 40 runs ✓; FP 57.9% → 0%, relative reduction 100% ✓; TP retention 112.5% ✓; gated overreach 0 ✓ — **all VERIFIED**.

### E4 — cross-campaign memory / learning curve (`e4_pilot_summary.json`; `e4_full_summary.json`, 2026-08-05→07)
- **Purpose**: does cross-campaign memory (experience injection) improve efficiency or design quality on full-length mRNA campaigns?
- **Design**: pilot 3 targets × 2 arms (nomem/memory) × 2 seed groups × 3 campaigns = **12 campaigns** (all pass, overall_pass = true; memory c3 campaigns fired `design_tool+lambda_value` injection and dropped to 13 evals vs 58). **Full matrix: 20 targets × 2 arms × 3 seed groups = 120 campaigns; 115 success + 5 failures** (all 5 = memory-arm `cli_failure` on Zika_E_protein ×3 and Factor_VIII ×2; 55/60 cells budget-matched valid).
- **Pre-registered gates** (`go_no_go.thresholds`): efficiency endpoint = memory slope significantly negative (one-sample t, one-sided less, p < 0.05) **and** cumulative budget saving ≥ 25%; design-gain endpoint = q_BH < 0.05 **and** |δ| ≥ 0.3 in the favourable direction (4 metrics); **GO if ANY endpoint passes**.
- **Exact numbers (full)**:
  - Budget saving: memory total **814** vs nomem **3153** evals → `saving_fraction` = **0.7418331747542024 (74.2%)**, n_paired_cells = 55, component pass = true.
  - Learning slope: memory slopes per seed group **[+1.228e-04, +2.381e-05, +2.429e-04] — all 3 positive**; one-sample t `p_one_sided_less` = **0.9115596698872256** → slope component fails; efficiency endpoint pass = false.
  - Design gain (55 pairs each, all NS): CDS CAI **p = 0.09203080210085418, δ = +0.1709090909090909** (q = 0.368, favourable_direction = false); full-length MFE p = 0.2616, δ = 0.0149; junction mfe/nt p = 0.6753, δ = −0.04; 5'UTR MRL p = 0.9143, δ = 0.0383 — 0/4 pass.
  - `go_no_go.go` = **false** (overall NO-GO).
- **Conclusion**: memory cuts budget 74% but shows no learning-curve improvement and no quality gain; the memory strategy was abandoned (user decision), redirecting to E5.

**Claim check**: 20 × 2 × 3 = 120 campaigns, 115 + 5 ✓ — **VERIFIED-WITH-NUANCE**: the summary JSON classifies the 5 as `n_unexpected_failure` = 5 (`n_acceptable_failure` = 0, and criterion c1 therefore fails), whereas `MODEL_API_USAGE.md` narrates them as "预声明失败" (pre-declared). Numbers agree; terminology differs between the two files — quote as "115 success + 5 memory-arm cli_failures (Zika ×3, Factor_VIII ×2)". Budget saving 74.2% (814 vs 3153) ✓; 3 positive slopes, t p = 0.91 ✓ (exact 0.9116); 4 metrics NS incl. CAI p = 0.092 δ = 0.17 ✓; overall NO-GO ✓.

### E5 — constraint navigation: batch delivery & ranking (S0 `e5_verdict_s0.json`; S1 `e5_verdict_s1.json`; report `E5_REPORT_2026-08-09.md`, 2026-08-07→09)
- **Purpose**: end-to-end gated constraint-navigation delivery of 5 candidates × 3 profiles per target under a pre-registered constraint matrix, three arms (A rules / B ungated LLM / C gated).
- **Design**: S0 = Insulin × C arm × 3 reps (5 mechanism criteria). S1 = 5 targets (A1AT, Insulin, EPO, GFP, IL-2) × 3 arms, 6 v7 criteria (e2e C ≥ 0.8 and C ≥ A with ties passing; constraint rate C ≥ 0.9; R1–R4; D1–D3; directional C ≥ A ≥ 4/5; budget recorded). Pool = LD 4λ + RNARL 1 + GEMORNA 30 → 315 candidates/target. S1 ran 5 rounds (r1–r5; r2 invalidated by RNARL outage).
- **Exact numbers**:
  - **S0: GO** — all 5 criteria true; `R2_tau_min` = 0.9999999999999999 (τ = 1.0 in all 3 profiles), LLM calls = 3, elapsed 344.28 s (budget 2400 s).
  - **S1 r5 (final): NO-GO, 3/5 cells failed** — per-target: **EPO GO, IL-2 GO** (all 6 criteria); A1AT NO-GO (R3: pool λ-gear separation insufficient); Insulin NO-GO (R3 + **D1 edit distance 0.0082 < 2%**, λ-saturation, accepted by decision); GFP NO-GO (**D2**: only λ{4,10} gears pass; accepted 2026-08-09). Pool pass counts: A1AT 60/315, Insulin 92/315, EPO 306/315, IL-2 192/315, **GFP 0/315 → 12/315 after B0** (species-matched E. coli codon table; CAI 0.9956–1.0). r4→r5 bit-identical for the 4 human targets (arm A 26 profile deliveries identical); all arm-B differences attributed to LLM non-determinism. r5 budget: LLM 11 (A0/B5/C6... recorded as B5+C5+... in report §5.3: "LLM 11 次"), LD 20, RNARL 5, GEMORNA 0 new.
  - S1 aggregate (v7): crit1 ✓ (c_e2e_gene = 1.0), crit2 ✓ (1.0), crit3 ✓ (R3 2/5 targets), crit4 ✗ (Insulin D1 + GFP D2), crit5 ✓ → **overall NO-GO**. S2 (18 targets) explicitly not recommended under unchanged generation layer (McNemar discordant ≈ 0 → p = 1.0 structurally).
- **Conclusion**: the mechanism layer (gates, mechanized ranking, evaluation) is stable and reproducible; every remaining failure is structural in the generation-method layer (λ-gear separation, λ saturation, feasible-gear coverage).

**Claim check**: S0 GO with R2 τ = 1.0 ✓; S1 r5 NO-GO ✓; Insulin D1 0.0082 < 2% ✓; GFP 0/315 → 12/315 after B0 ✓; EPO/IL-2 single-target GO ✓ — **all VERIFIED**. (Note: `e5_verdict_s1.json` on disk holds the final per-target overwrite state = IL-2 GO cell; the S1-level NO-GO verdict lives in the report §5.3 — cite both with this semantics note.)

### E6 — generation-layer navigation (GenNav) (S0 `e6_verdict_s0.json`; S1 `e6_verdict_s1.json`; S2 `e6_s2_verdict_aggregated.json`; closeout `HANDOFF_2026-08-10_E6_CLOSED_S2_GO.md`)
- **Purpose**: sink constraint navigation from the selection layer into the generation layer (feasibility-first adaptive lattice + profile-orthogonal axes + diversity expander + codon-context resolver) to fix the E5 R3/D1/D2 structural failures.
- **Design**: S0 = Insulin × C × 3 reps; S1 = 5 targets × 3 arms, criteria book v8 (6 items); **S2 = 18 targets × arms A/C** (B disclosed only), dual endpoints: primary = per-profile JCD-pass (e2e ∧ D1 ∧ D2 ∧ R3) paired McNemar C vs A (n = 54 = 18 targets × 3 profiles) p < 0.05 **and** c_e2e_gene ≥ 0.8; secondary = continuous composite paired Wilcoxon p < 0.05 **and** quality criteria (R1&R4&R3&D1&D2&D3 all pass + E14 lattice ≥ 3 gears everywhere) **and** constraint rate C ≥ 0.9; GO if either endpoint passes; primary-pass/secondary-fail must be disclosed.
- **Exact numbers**:
  - **S0: GO** — all 6 criteria true, R2_tau_min = 0.9999999999999999, R3 3/3 separated, LLM 6 calls, elapsed 567.8 s; lattice: 5 feasible LD gears {2,4,8,10,20}.
  - **S1: GO** (per closeout handoff and `HANDOFF_2026-08-10_E6_S2_COMPLETE_AGG_GO.md` §2: "六项全过"; LLM 23 = A0/B8/C15, LD 21).
  - **S2: GO** (`e6_s2_verdict_aggregated.json`, recomputed from 18 run records by `recompute_e6_s2_verdict.py`):
    - Primary endpoint: **McNemar C vs A p = 1.862645149230957e-09**, discordant **b = 30, c = 0** (all one-direction), n_pairs = 54; `c_e2e_gene` = **1.0** → endpoint1 = true. McNemar C vs B = null (disclosure-only arm).
    - Secondary endpoint: Wilcoxon C vs A **p = 1.6511654049639136e-07** (passes), constraint rate C ≥ 0.9 true, but quality criteria fail (R1/R4 true; **R3_all_arms false; D1/D2/D3 false; E14 ge_3 false**) → endpoint2 = false; `endpoint2_not_passed_disclosed` = **true**.
    - Quality-failure attribution (handoff §0/§1): almost all failures from **HER2 single target** — probe found `feasible_gears = []` (λ 0–50 all 0 UTR pass), `plan_mode = degrade`, 0 lattice cells; sporadic failures: Albumin p1 D3, Beta_galactosidase p0/p1 D2, SARS-CoV-2_Spike_WT p0 D1/D2/D3. Other 14 targets pass all C-arm quality items.
    - S2 budget: **LLM 43 calls (A 0 / C 43; 1–4 per gene, mean 2.4**, below the pre-registered 5–9/gene); request_generate 1 (HER2, within the ≤ 2 gate); LD 125 slot counts (61 actual new service calls; 64 human static slots hit the e5 survey cache); GEMORNA 0 new; RNARL 0.
- **Conclusion**: generation-layer navigation makes the primary endpoint decisively significant (30:0 one-direction discordance) with C-arm e2e at ceiling; the stricter quality bundle still fails on HER2-class zero-feasible-gear targets and is disclosed, not hidden.

**Claim check**: S0/S2 GO ✓ (verdict files); **S1 GO — VERIFIED-WITH-NUANCE**: the on-disk `e6_verdict_s1.json` is a per-target-overwrite *intermediate* state (last cell IL-2, `go_no_go` = "NO-GO", directional_C_ge_A_4of5 = false on a single cell); both 2026-08-10 handoffs state the file uses E5-style overwrite semantics and the final S1 adjudication (on the last 5 run records) was GO with all six v8 criteria — do not cite `e6_verdict_s1.json` as the S1 verdict. McNemar p = 1.86e-09, 30:0, n = 54 ✓; c_e2e_gene = 1.0 ✓; secondary failed & disclosed (Wilcoxon p = 1.65e-07 passes, quality fails, HER2 feasible_gears = [] degrade) ✓; LLM 43, mean 2.4/gene ✓ (spot-check: run records contain 43 C-arm calls; a naive regex over the JSONL double-counts nested copies as 86) — **VERIFIED**.

### E7 — mRNA-side oracle capability profiling (`e7_mrna_oracle_profile_summary.json`, 2026-08-11)
- **Purpose**: extend capability profiling to the full-length mRNA workflow's oracles — the positive-control counterpart to E1 (profiling must be able to *certify* power, not only revoke it).
- **Design**: oracle = GEMORNA 5′UTR MRL (port 8004); 706 assertion-curated anchors with measured MRL from Sample et al. 2019 (GEO GSE114002; GSM3130435 random 50-nt EGFP library + GSM4084997 varying-length 25–100 nt library, split by its `set` column into random / human-endogenous families; generator `experiments/curate_e7_mrl_anchor_set.py`, anchor set `data/benchmarks/external_anchors/utr_mrl/e7_mrl_anchor_set.json`). Per family: 60 high-MRL + 60 low-MRL tier anchors (screening), 120 rank-stratified anchors (ranking). Gates identical to E1: screening AUROC > 0.8 (10,000-fold bootstrap CI, seed 0); ranking Spearman ρ ≥ 0.6.
- **Exact numbers**: `sample2019_egfp_random50` (in-training-distribution) AUROC **0.9903** [0.9753–1.0], ρ = **0.9256** → verified/verified; `sample2019_varying_length_random` AUROC **1.0000**, ρ = **0.9201** → verified/verified; `sample2019_varying_length_human` AUROC **1.0000**, ρ = **0.8353** → verified/verified. 706/706 service calls succeeded. S0 sanity: high-tier mean predicted MRL 6.34 vs low-tier 2.48.
- **Gate demonstration** (`e7_gate_demo.jsonl`): ranking by `gemorna_5utr_mrl` on a verified family → **allow**; on a never-profiled family of the same oracle → **downgrade** (the SelfModel transfers same-(oracle, task) grades across families with decayed confidence — designed behavior, recorded with `expectation_met: false` against the naive `require_profiling` expectation); ranking by `gemorna_3utr_stability` (no measured anchor set exists — unprofiled by design) → **require_profiling**; an absolute-scope expression claim → ClaimGate downgrade to `within_target_relative`.
- **Verdict: GO** (`go: true` — all three families pass both gates).
- **Conclusion**: the MRL oracle has verified screening/ranking power on human-assay 5′UTRs; the 3′UTR stability predictor stays unprofiled and gated off. The capability map is now two-sided across the platform's flagship task families.

**Claim check**: numbers as reported by the E7 driver run of 2026-08-11 against `e7_mrna_oracle_profile_summary.json` / `e7_gate_demo.jsonl` — **VERIFIED**.

### E8 — aptamer-side GenNav (GenNav-Apt) (`e8_verdict_s2.json`, 2026-08-11; driver `experiments/run_e8_gennav_aptamer.py`)
- **Purpose**: test GenNav's generality on the second flagship task family — RNA aptamer design with the ODesign structure-guided generator (length/seed/sample-count gears instead of LinearDesign λ), under the E1-imposed constraint that no structure oracle may rank candidates.
- **Design**: arms A (rule grid: lengths {30,50,80} × seeds {42,123} × 8 samples = 48 raw) vs C (gated navigation: 6-gear probe at n=2 (12 raw) + ≤ 4 request_generate rounds, same 48-raw cap; ≤ 9 LLM calls/target; DeepSeek temp 0.0). Delivery 5/profile, 3 length-banded profiles (compact 25–39, standard 40–60, extended 61–85 nt); matrix: GC ∈ [0.35,0.70], homopolymer < 6 nt, LinearFold stem ≤ 12 bp; batch diversity D1 ≥ 0.15 normalized Levenshtein. Primary endpoint: paired exact McNemar on per-profile JCD, n = 30 pairs (10 targets), p < 0.05 ∧ C-e2e ≥ 0.8. S0 = Thrombin mechanism gate; S1 = 3 targets (rerun once after the 2026-08-11 amendments ①–⑤: request cap 2→4, band-gap navigation context, delivery 5/profile confirmation, precise degrade reasons); S2 = 10 targets.
- **Notable fix en route**: SARS-CoV-2_Nucleocapsid's `known_hotspot_residues` (A/44–48) fall outside the 6m3m chain-A numbering (49–174) → deterministic zero-output from ODesign; the driver now assertion-checks JSON hotspots against structure numbering and falls back to auto-identify (fig4-consistent).
- **Exact numbers (S2)**: McNemar **b = 3, c = 1, p = 0.625** → primary endpoint **NOT met** (NO-GO on the pre-registered gate). Discordants: BSA compact (A✗/C✓), VEGF extended (A✗/C✓), SARS-CoV-2_Nucleocapsid extended (A✗/C✓), MBP compact (A✓/C✗ — C fell one D1-deliverable short, 4/5, after the LLM prioritized other bands with its 4 rounds). Gene-level e2e: **C 9/10 vs A 7/10**. 26/30 pairs concordant-pass (task largely saturates). C delivered-candidate matrix-pass rate 1.0; LLM 4–6 calls/target (S2 total 46, mean 4.6); request_generate ≤ 4; C raw spend mean ≈ 36 vs A 48; **zero budget violations**; DecisionGate demos 10/10 `reject` on oracle-ranking. Campaign LLM total: 76 calls (S0 4, S1 12 + 14 rerun, S2 46).
- **Verdict: NO-GO on the primary endpoint; reported as a scope finding** — navigation transfers mechanically and repairs every rule-arm failure it meets, but the aptamer matrix mostly saturates, so the advantage is not decisive (same saturation logic as E5's S2 recommendation).
- **Conclusion**: GenNav's value regime is confirmed two-sided in mechanism (probe → allocate → deliver-or-degrade, gates enforced) with the statistical decisiveness currently carried by the mRNA task, whose codon-objective trade-offs make delivery structurally hard.

**Claim check**: b=3/c=1/p=0.625, e2e 9/10 vs 7/10, mean raw 36 vs 48, LLM 46 at S2 / 76 total, 10/10 gate demos ✓ — **VERIFIED** against `e8_verdict_s2.json` and `e8_runs_s2.jsonl` (2026-08-11).

### E9 — aptamer GenNav re-anchored (scarcity matrix) (`e9_verdict_s2.json`, 2026-08-12; driver `experiments/run_e9_gennav_aptamer.py`)
- **Purpose**: probe whether the E8 aptamer boundary is budget rather than mechanism — re-anchor the constraint matrix so delivery becomes length-gear-scarce (per-profile stem caps: compact 25–34 nt/stem≤8, standard 40–55 nt/stem≤10, extended 61–80 nt/stem≤12, relax v1; nine-length lattice {25,30,35,40,50,60,65,70,80}).
- **Exact numbers (S2, 10 targets)**: McNemar **b = 6, c = 8, p = 0.79** → primary endpoint **NOT met**. Rule-arm failures rose 3/30 (E8) → 11/30 (E9) (scarcity structure works); navigator repaired 6/11 but conceded 8 cells (c = 8): LLM reinforcement decision noise (probe n2 → gear choice) + all-bands-scarce targets (N, BSA, TNF-α) starving the standard band.
- **Conclusion**: boundary localized to probe-vs-reinforcement budget structure within the fixed 48-raw cap; the re-anchored matrix is a reusable construct (per-profile gear-scarce delivery).

**Claim check**: b=6/c=8/p=0.79, rule-arm failures 11/30 ✓ — **VERIFIED** against `e9_verdict_s2.json` (2026-08-12).

### E10 — aptamer GenNav mechanized allocation (`e10_verdict_s2.json`, 2026-08-12; driver `experiments/run_e10_gennav_aptamer.py`)
- **Purpose**: mechanize the reinforcement decision (deterministic gap-weighted allocator with laplace-smoothed probe pass rates proposes gears; LLM arbitrates only) + two-stage probe (18 raw probe + ≤ 8 raw probe2) + 12-target panel (10 fixed + CAII/Pepsin via pre-registered A-fail-density rule, five-target S1 probe: frac 0.6 ≥ 0.3).
- **Exact numbers (S2, 12 targets)**: McNemar **b = 9, c = 4, p = 0.267** → primary endpoint **NOT met** (mechanism block all-pass: zero budget violations, gate demos forbidden). c = 4 all single-band starvations (BSA extended, MBP compact, N standard, Thrombin standard): bands with sub-20% pass rates need 2+ reinforcement rounds, unreachable in 3 rounds under the 48-raw cap. Min-round variants simulated worse (b = 7–9, c = 5–6) — E10's band-priority 3 rounds is the Pareto front at 48 raw. C e2e 0.50 vs A 0.33.
- **Conclusion**: mechanized allocation works as simulated (b 6→9, c 8→4, P 0.79→0.27); the aptamer boundary is budget structure, not mechanism.

**Claim check**: b=9/c=4/p=0.267, c-cell list, C e2e 0.50 vs A 0.33 ✓ — **VERIFIED** against `e10_verdict_s2.json` and `e10_runs_s2.jsonl` (2026-08-12).

### E12 — aptamer GenNav densified lattice + S1 priors (`e12_verdict_s2.json`, 2026-08-14; driver `experiments/run_e12_gennav_aptamer.py`)
- **Purpose**: last open lever after the matrix sweep (0/324 decisive, `e12_matrix_sweep.py`) — lattice densification (17 lengths, ~3 nt per band) + S1-measured laplace priors, with a pre-registered panel gate (rate-based NAV, addendum v1).
- **Exact numbers (S2, 12 targets)**: McNemar **b = 9, c = 2, P = 0.0654** (E10 was 9:4/P=0.267 — c halved, P 4× improved, one c-cell short); C e2e 0.25 vs A 0.00; mechanism block all-pass.
- **Conclusion**: densification + priors are effective levers (P 4×); e2e ≥ 0.8 gate structurally unreachable — panel's 7 double-A-fail targets exceed per-target repair capacity (addendum v2).

**Claim check**: b=9/c=2/p=0.0654296875, c-cell list (Pepsin compact, Thrombin standard), C e2e 0.25 ✓ — **VERIFIED** against `e12_verdict_s2.json` (2026-08-14).

### E13 — controlled replication: panel axis formally closed (`e13_verdict_s2.json`, 2026-08-14; driver `experiments/run_e13_gennav_aptamer.py`)
- **Purpose**: formally close the panel axis with a fresh pre-registered criteria book — panel rule changed to a direct per-target nav ≥ 1 ∧ a_fail ≥ 1 constraint (user-confirmed not a standards reduction; criteria untouched).
- **Exact numbers (S2, 12 targets)**: **bit-identical to E12** — b=9/c=2/P=0.0654, C e2e 0.25/A 0.00, all 36 JCD pairs equal (programmatic check); whole campaign from cache in 133 s, zero new generations.
- **Conclusion**: panel axis closed — E12's panel was nav-maximal (21/21); no panel rule moves the dual-gate endpoint; e2e ≥ 0.8 is a per-target reliability × budget bound.

**Claim check**: b=9/c=2/p=0.0654296875, 36-pair identity with E12 ✓ — **VERIFIED** against `e13_verdict_s2.json` + `e12_verdict_s2.json` (2026-08-14).

### E14 — aptamer GenNav PRIMARY ENDPOINT GO (`e14_verdict_s2.json`, 2026-08-14; driver `experiments/run_e14_gennav_aptamer.py`)
- **Purpose**: decisive same-budget test under a user-adjudicated relative-advantage endpoint (paired McNemar P<0.05 single gate; e2e demoted to secondary disclosure — 12/36 cells jointly infeasible at 48-raw, axes closed appendices I/J/L), with protocol addenda: v1 cycling guarantee (1803a77), v2 4×n6 rounds + n8-over-n2 unblock (7ce7875).
- **Exact numbers (S2, 12 targets)**: McNemar **b = 14, c = 3, P = 0.0127 < 0.05 — GO** (iteration path: E12/E13 9:2/0.0654 → v1 14:6/0.115 → v2 10:3/0.092 → v3 14:3/0.0127). C delivers 26/36 profile cells vs A 15/36 (72% vs 42%); C e2e 0.50 (6/12 targets) vs A 0.00 (relative 6:0); C matrix pass rate 1.0; zero budget violations; **1 LLM call across the run** (deterministic guarantee rounds); 3 A-wins (MBP extended, Papain compact, Thrombin extended) and 7 jointly-infeasible cells disclosed.
- **Conclusion**: **positive aptamer-side navigation result** — same-budget navigation wins discordant cells 14:3; validated levers: lattice densification (E12), S1 priors (E12), guaranteed-repair allocation (E14); absolute e2e gate is a target-set property at this budget, reported as boundary.

**Claim check**: b=14/c=3/p=0.012725830078125, c-cell list, C e2e 0.50/A 0.00, LLM=1 ✓ — **VERIFIED** against `e14_verdict_s2.json` + `e14_runs_s2.jsonl` (2026-08-14).

### E15 — confirmatory replication: scarcity-panel boundary (`e15_verdict_s2.json`, 2026-08-14; driver `experiments/run_e15_gennav_aptamer.py`)
- **Purpose**: pre-registered dual-outcome confirmatory run (E14-final protocol; 12 targets = 4 never-paneled scarce targets BSA/CAII/Chymotrypsinogen/GFP + top-8 of E14's panel by S1 score).
- **Exact numbers (S2)**: McNemar **b = 14, c = 6, P = 0.1153** → primary endpoint NOT met (pre-registered 40% branch); C e2e 0.333 vs A 0.00; mechanism all-pass, zero violations, 3 LLM calls. New targets: b=3 (all three fixable A-fail cells repaired), c=4 (their A-deliverable bands). Pooled E14+E15: b=28/c=9, P=0.0026 (driven by E14, heterogeneity acknowledged).
- **Conclusion**: **navigation advantage is regime-specific to delivery-scarce panels** — empirically confirms the paper's scarcity thesis; E14 remains the primary positive aptamer result, E15 disclosed as boundary.

**Claim check**: b=14/c=6/p=0.11531829833984375, c-cell list, C e2e 0.333, LLM=3 ✓ — **VERIFIED** against `e15_verdict_s2.json` + `e15_runs_s2.jsonl` (2026-08-14).

### E11 — escape-route closure simulation (cap 64 / panel expansion) (`experiments/analysis/e11_feasibility_sim.py`, 2026-08-13; pre-registration gate, real E10 S2 cache, no services)
- **Purpose**: close the two escape routes the E10 boundary left open — symmetric budget rescale (48→64) and panel expansion — before any re-preregistration.
- **Exact numbers**: symmetric cap-64 grid (5 A-arm lattices × 3 C protocols): rule-arm failing cells 14 → **5–8** under any symmetric lattice extension; navigator discordant repairs **b = 9 → 2–7**, conceded cells **c = 3–4**, **P ≥ 0.34** across all variants (floor-round and degrade-aware protocols do not rescue it — A-arm strengthening is the binding constraint). Asymmetric A-48/C-64 alone reaches b = 9/c = 1/p = 0.0215 but changes the comparison basis (C +33% budget) — rejected against the budget-matching iron rule (user decision 2026-08-13). Panel route: benchmark = 20 targets (19 usable, ferritin zero-output excluded); full-panel paired McNemar **≈ 0.11–0.13** (the "20-target P ≈ 0.07" estimate in the 2026-08-13 handoff was a one-sided value; two-sided ≈ 0.13).
- **Conclusion**: both escape routes closed by simulation/statistics — the aptamer boundary is structural (navigator advantage peaks at 48 raw, shrinks as the static grid grows).

**Claim check**: grid b/c/P values ✓ — **VERIFIED** by re-running `experiments/analysis/e11_feasibility_sim.py` (deterministic, real cache; 2026-08-13).

---

## 5. Failure taxonomy and API cost

### Failure taxonomy (`failure_taxonomy.json`)
- Method: sweep of all legacy-campaign JSONLs; categories distinguish transient/recovered vs final-state failures.
- Totals — failure events: transient_infra_recovered **188**, transient_timeout **20**, boundary_odesign_zero_output **72**, endpoint_misconfig **8**, driver_chain_bug_fixed **6**, llm_abort_correct **1**.
- **Final failures: 35 total** = boundary_odesign_zero_output 24 (Fig-4 Ferritin 12 + Fig-5 b/c boundaries 12), endpoint_misconfig 8 (Fig-6b nominal Claude arm 404s), boundary_lineardesign_oom 2 (Zika 10 kb / Factor VIII 7 kb CDS, λ = 0 arm, deterministic OOM), llm_abort_correct 1 (Fig-2 siRNA GC-rich task).
- File note: every non-final failure event was recovered by `--resume` sweeps; all final failures are deterministic boundaries or explicit governance/misconfig outcomes.

### Model API usage (`MODEL_API_USAGE.md`, updated 2026-08-10)
- Sole external LLM in all results: **DeepSeek `deepseek-v4-pro`** (official endpoint; QualityAgent reviews at temp 0.2 for the legacy campaign; temp 0.0 for the in-system LLM under test in E3/E5/E6). No successful OpenAI/Anthropic/Alibaba/Google calls anywhere (the Fig-6b "Claude" arm is 8 endpoint-misconfig 404s).
- Measured call counts: Fig-6b DeepSeek arm **93 QualityAgent calls, 414,088 prompt + 194,261 completion tokens** (usage_available = true); E3 full **80** calls; E4 pilot 24, E4 full **230** (vs 240 pre-registered; 10 fewer because the 5 failed memory cells produced no reviews); E5 S0 **3** / S1 r3 13 / r4 24 / r5 11; E6 S0 **6** / S1 **23** / S2 **43**. Other figures did not collect per-call tokens (usage_available = false; estimated from the §1 profile, per-figure cost < ¥10–20).
- All structure/sequence models are local microservices with local weights; Protenix runs `msa_mode="none"` (no MSA server). Experiment orchestration was assisted by Kimi CLI (disclosed in §5 as not part of the tested system).

---

## 6. Top-20 key numbers the paper can cite directly

1. Platform coverage: **210/210** benchmark tasks succeed across **11 workflows, 54 tools, 22 local microservices (ports 8003–8024)** (`fig2_summary.json` total, refreshed 2026-08-11; TOOLS.md §1). *Scale as of that refresh; the 2026-08-18 simplification pass later reduced the platform to 41 registered tools / 21 services with the 210/210 workflow set unchanged — the registered next step regenerates these panels against the gated platform.*
2. Designed CDS CAI median **0.7454** vs WT **0.7286** vs random-synonymous **0.6723** (n = 20/20/200; OTC/PDGFB replaced the two oversized targets 2026-08-11); WT > random p = **4.02e-07**, δ = 0.688 (`fig2_summary.json` fig2a_cds_nulls).
3. Secondary-structure inverse folding exact match **22/25 (0.88)** (`fig2_summary.json` fig2e). *Legacy record; the 2026-08-25 reset re-ran this panel as Fig 2d (`experiments/exp4_inverse_folding/`, zero-intervention golden path): 25/25 successful, exact match **21/25** (miss distances 2/2/4/6 dot-bracket, 1/2/3/1 base pairs) — the number of record for the paper.*
4. IRES AUROC **0.762** (95% CI [0.429, 0.98], 3 pos / 49 neg) (`fig2_summary.json` fig2i). *Legacy record; the 2026-08-25 reset re-ran this panel as Fig 2e on the user-approved 9-positive panel (`experiments/results/exp5_ires_panel/summary.json`, zero-intervention protocol): pre-registered mode-0 default-path primary **0.478 (0.311–0.649, P=0.841)**; mode-2 sliding-window arm — the legacy protocol — **0.673 (0.467–0.862, P=0.102)** — the numbers of record.*
5. Small-molecule oracle, two-sided profile (2026-08-11, `rnasmol_boundary_panel.json`; **reset re-run 2026-08-26 — `experiments/results/exp7_rnasmol_boundary/summary.json`, 3,545/3,545 zero-intervention, every registered metric reproduced exactly**): in-distribution test AUROC **0.9744** (robin) / **0.9828** (pdb) — exact official-pipeline parity after the RNAsmol v0.3.0 preprocessing-fidelity fix — decoy true-ligand ranks **2/1601** and **7/265**; out-of-distribution short-aptamer panel has no demonstrated power (workflow-level AUROC vs near-cognate **0.312**; RNAsmol-only 0.722/0.563, CIs include chance).
6. Fig-3 Type-I: bmc_x1 vs serial fixed-reference ASF **p = 0.8124, NS** (n = 20 targets, 240/240 jobs) (`fig3_summary.json`).
7. Fig-3 burial: serial buries AUG/Kozak in **38/60 runs (0.633)**; bmc_x1 clears **4/18** serial-buried targets (`fig3_summary.json` burial).
8. Fig-4 Type-II ungated effect: egarps component **p = 2.10e-04, δ = +0.457** (n = 19); 3-D hypervolume **p = 2.61e-04** (n = 57) (`fig4_summary.json`).
9. P0 budget-matched control: **δ = 0.278 < 0.3, p = 0.129 → NO-GO**; the Fig-4 effect is budget-confounded (`p0_budget_matched_summary.json`).
10. E1 v2 oracle profiling: **0/18** oracle×target cells pass screening (AUROC > 0.8), **0** pass ranking (ρ ≥ 0.6), docking native top-1 **0/5** (66 entries, 6 targets, 102 poses) (`e1_capability_summary_v2.json`).
11. P2 calibration: thrombin Kd series ρ = **0.40** (n = 4), binder-vs-negative AUROC = **0.356** → EGARPS np uncalibrated (`p2_aptamer_calibration_summary.json`).
12. E2 self-audit: in-house claim survival **0/2 (0% < 70% threshold)** — Fig-4 and Fig-7B claims both downgraded (`E2_SELF_AUDIT_FIG4_FIG7B.md`).
13. E3 gated vs ungated (40 runs): false-positive rate **57.9% → 0%** (relative reduction 100%), TP retention **112.5%** (8 → 9), gated overreach events **0** vs 23 (`e3_runs_full_summary.json`).
14. E4 full matrix (120 campaigns, 115 + 5 memory-arm cli_failures): budget saving **74.18%** (814 vs 3153 evals) but all 3 memory learning slopes positive (t p = 0.912) and 4/4 quality metrics NS (CAI p = 0.092, δ = 0.171) → **overall NO-GO** (`e4_full_summary.json`).
15. Junction ddG metric validity: constraint obedience **216/216**, ddG ≥ 0 **216/216**, LinearFold-vs-Vienna r = **0.9449**; Route C repair passes **1/3** targets (EPO, median W1 improvement **5.835 kcal/mol**) → Route C NO-GO (`junction_ddg_pilot_summary.json`).
16. E5 S1 final (r5): **NO-GO 3/5** with EPO and IL-2 single-target GO; Insulin D1 edit distance **0.0082 < 2%**; GFP pool pass **0/315 → 12/315** after species-matched codon table (B0) (`E5_REPORT_2026-08-09.md`).
17. E5 mechanism lesson: mechanized ranking (system-enforced utility order, LLM tie-arbitration only) cut S0 LLM calls to **3** with R2 τ = **1.0** → S0 GO (`e5_verdict_s0.json`).
18. E6 S2 primary endpoint: per-profile JCD-pass McNemar (C vs A, n = 54) **p = 1.86e-09, discordant 30:0**, c_e2e_gene = **1.0** → **GO** (`e6_s2_verdict_aggregated.json`).
19. E6 S2 secondary endpoint **failed and disclosed**: Wilcoxon p = 1.65e-07 passes but quality bundle fails, driven by HER2 `feasible_gears = []` degrade path (`e6_s2_verdict_aggregated.json`, handoff 2026-08-10).
20. Cost/transparency: sole external LLM = DeepSeek v4-pro; measured usages include Fig-6b **93 calls / 414,088 + 194,261 tokens**, E3 80 calls, E4 230 calls, E6 6 + 23 + 43 calls; all models otherwise local (`MODEL_API_USAGE.md`).

---

## 7. Discrepancy register (must-fix before submission)

1. **"20 submodules"** → external_repos has 20 directories but only **17 registered git submodules** (`.gitmodules`); EGARPS/Protenix/RiboDiffusion are unregistered. Use "20 vendored external repos (17 git submodules)".
2. **E4 "5 预声明失败"** → `e4_full_summary.json` records them as `n_unexpected_failure` = 5 (criterion c1 fails; `n_acceptable_failure` = 0). `MODEL_API_USAGE.md` calls them 预声明失败. Reconcile wording; safest: "115/120 success; 5 memory-arm cli_failures (Zika ×3, Factor_VIII ×2)".
3. **Fig-5c "全 NS"** → true only after BH-FDR; egarps raw p = 0.0245 (q = 0.368). Write "no panel-b/c test survives BH-FDR".
4. **E6 S1 verdict file semantics** → `e6_verdict_s1.json` on disk shows NO-GO (intermediate per-target overwrite state, last cell IL-2); final S1 GO is documented in the two 2026-08-10 handoffs. Same overwrite semantics as `e5_verdict_s1.json` (final cell IL-2 GO) and `e6_verdict_s2.json` (last cell Transferrin) — never cite per-stage verdict files directly; cite `e6_s2_verdict_aggregated.json` for S2 and the handoffs/report for S1.
5. **P1 file internal inconsistency** → `j1_mfe_per_nt_vs_bmc1_wins` structured field = "13/18" while `go_no_go.evidence` text says "16/18"; quote the structured field (13/18).
6. **E1 v2 "best screening 0.8"** → rhofold×PDGF-BB AUROC is exactly 0.8 and the gate is strict `> 0.8`; phrase as "best cell reached AUROC 0.8 (95% CI 0.33–1.0), still not passing".
7. **Fig-7A anchor nuance** → the designed candidate and BNT162b2 are *both* AUG/Kozak-buried under the fragment-fold metric; do not imply the designed candidate is junction-clean.
8. **RESOLVED 2026-08-11 — Fig-2 designed arm n = 18** → the two oversized WT proteins (Zika polyprotein 3419 aa, Factor VIII 2351 aa) were replaced by OTC (354 aa) and PDGFB (241 aa); the designed arm is now n = 20, median CAI 0.7454 (see §2 Fig 2 refresh). E4's historical target list kept the two old targets (its concluded results reference them).
