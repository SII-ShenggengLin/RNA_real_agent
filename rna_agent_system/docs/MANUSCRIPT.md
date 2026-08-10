# RNADesignAgent — Experiment Manual

> **Scope**: benchmark/anchor assets, the pilot-first protocol (still in force), and the data-availability register for both experiment campaigns.
> **Last updated**: 2026-08-10 (v4 — condensed rewrite)

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
| RNA-BioBench-Platform | `RNA-BioBench-Platform/tasks/<dir>/<task>.json` | 210 tasks / 11 workflows | Fig 2 (legacy) |
| RNA-BioBench-FullLength-mRNA | `RNA-BioBench-FullLength-mRNA/targets/*.json` (+`sequences/*.fa`) | 20 targets | Fig 3/7A (legacy); P0–P3, E4, E5, E6 |
| RNA-BioBench-Aptamer | `RNA-BioBench-Aptamer/targets/*.json` (+`structures/*.pdb`) | 20 targets | Fig 4/7B (legacy); P2, E1 |
| RNA-BioBench-ProcessAware | `RNA-BioBench-ProcessAware/task_set_for_llm_comparison.json` | 19 tasks on disk (PA_006–024) | Fig 6 (legacy), CLI regression (`run_pa_test.py`) |

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
| `ires/` | Validated viral IRES (EMCV, HCV, poliovirus) + cellular IRES (c-myc, VEGF, Bip); 50 random human 5′UTR negatives (GENCODE v46) |
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

All paths are under `rna_agent_system/experiments/results/`.

### 3.1 Tier 1 — legacy campaign (Figs 2–7): data complete, conclusions downgraded

Data collection for the legacy figure campaign is **complete**; the conclusions
are stated only in the downgraded form established by the P0–P3 pilots and the
E2 audit (`E2_SELF_AUDIT_FIG4_FIG7B.md`, claim survival 0/2). One-line status
per figure:

| Figure | Data | Verdict-file pointer | Downgraded conclusion |
|--------|------|----------------------|------------------------|
| 2 platform quality | ✅ 209/210 tasks | `fig2_summary.json` | Platform runs and outputs beat biological nulls (CAI 0.744 designed vs 0.730 WT vs 0.674 random); small-molecule scoring at chance (AUROC 0.5) reported as tool boundary |
| 3 Type-I BMC | ✅ 240/240 | `fig3_summary.json` | No significant fixed-reference ASF difference at any BMC depth (bmc×1 p = 0.81 NS) |
| 4 Type-II BMC | ✅ 228/240 | `fig4_summary.json` | Ungated egarps/hypervolume effects (p ≈ 2e-4) **confounded** — unprofiled oracle (P2/E1) + budget (P0); not a coordination claim |
| 5 mechanism ablations | ✅ 141 + 12 boundary | `fig5_summary.json` | No panel-b/c test survives BH-FDR; λ clamp contains extreme starts; negative controls clean |
| 6 governance/backends | ✅ 38 + 29 | `fig6_quality_ablation.jsonl`, `fig6_backends.jsonl` | QualityAgent advisory-only (both arms 19/19); backend matrix: deepseek 19/19, nominal claude arm 8 endpoint-misconfig failures (historical fact; extension cancelled, §4) |
| 7 case studies | ✅ 3/3 | `fig7_cases/*/case_summary.json` | End-to-end cases complete in minutes-to-hour and land near anchors on score-chain metrics; Case B is **not** a superiority claim (E2) |

### 3.2 Tier 2 — calibrated-agent campaign (E1–E6): verdicts

| Exp | Question | Verdict | Verdict / report files |
|-----|----------|---------|------------------------|
| E1 | What capabilities do the deployed oracles have? | **NO PASS** on screening (0/18 cells, AUROC > 0.8 gate), ranking (no ρ ≥ 0.6), docking (0/5 native top-1) | `e1_capability_summary.json` (pilot), `e1_capability_summary_v2.json` (6-target extension) |
| E2 | Do ungated legacy claims survive profiling? | Survival **0/2** (< 70% gate) → audit story holds | `E2_SELF_AUDIT_FIG4_FIG7B.md` |
| E3 | Does dual gating cut false-positive claims? | **GO**: FP rate 57.9% → 0%, TP retention 112.5%, gated overreach events 0 (vs 23) | `e3_runs_full_summary.json`; write-up `RESULTS4_E3_MATERIALS.md` |
| E4 | Does cross-campaign memory improve efficiency or design quality? | **NO-GO** (full matrix): budget saving 74.2% (814 vs 3153 evals) but all 3 learning slopes positive (t p = 0.91) and 4/4 quality metrics NS; memory strategy abandoned | `e4_pilot_summary.json`, `e4_full_summary.json` |
| E5 | Gated constraint navigation (selection layer) | **S0 GO** (τ = 1.0, 3 LLM calls); **S1 NO-GO** (3/5 cells failed: A1AT R3, Insulin D1, GFP D2; EPO/IL-2 single-target GO); every failure structural in the generation-method layer | `e5_verdict_s0.json`, `e5_verdict_s1.json` (per-target overwrite semantics — see fact sheet), report `E5_REPORT_2026-08-09.md` |
| E6 | Generation-layer navigation (GenNav) | **S0/S1/S2 GO**. S2 primary endpoint: per-profile JCD-pass McNemar C vs A (n = 54) **p = 1.86e-09, discordant 30:0**, c_e2e_gene = 1.0. Secondary endpoint **failed and disclosed** (Wilcoxon p = 1.65e-07 passes; quality bundle fails, driven by HER2 `feasible_gears = []` degrade) | `e6_s2_verdict_aggregated.json` (S2; do not cite per-stage verdict files), closeout `HANDOFF_2026-08-10_E6_CLOSED_S2_GO.md` |

Pivot pilots P0–P3 and the junction line (P1, P1 v2, junction-integrated
optimizer, ddG Phase-0 pilot) are summarized with exact numbers in
[`PAPER_FACT_SHEET.md`](PAPER_FACT_SHEET.md) §3; verdict files
`p0_budget_matched_summary.json`, `p1_junction_optimizer_summary.json`,
`p1_v2_stability_sweep_summary.json`, `junction_integrated_optimizer_summary.json`,
`junction_ddg_pilot_summary.json`, `p2_aptamer_calibration_summary.json`,
`p3_guided_vs_unguided_summary.json`.

Failure taxonomy across all campaigns: `failure_taxonomy.json` (35 final
failures, all deterministic boundaries or explicit governance/misconfig
outcomes). Model/API provenance: `MODEL_API_USAGE.md` (sole external LLM in all
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

- Drivers: `experiments/run_*.py`, `experiments/analysis/stats_utils.py`
  (Wilcoxon / Cliff's δ / BH-FDR / bootstrap AUROC), per-campaign drivers named
  in the verdict files. Two legacy drivers (`run_quality_ablation.py`,
  `run_llm_backend_comparison.py`) still reference the removed planner API and
  are frozen — update them if ever rerun.
- CLI regression: `run_pa_test.py <006..024>` over `pa_benchmarks.json`.
- Agent-core suite: `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x`
  (baseline 668 passed).
- Conventions: JSONL = one record per run; analysis never reads session logs
  directly — only the JSONLs/summaries above.
