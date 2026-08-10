# Decisions, Concluded Directions and Do-Not-Repeat Register

> **Purpose**: the single register of what this project has concluded — directions we will
> **not** pursue again (with the evidence that closed them), positive results that **are**
> established (with their evidence pointers), and a one-line project timeline.
> Before proposing any new experiment, optimization, or narrative claim, check Part 1 first.
> **Last updated**: 2026-08-10

All evidence files live under `rna_agent_system/experiments/results/` unless noted.
Exact numbers are fact-checked in [`PAPER_FACT_SHEET.md`](PAPER_FACT_SHEET.md).

---

## Part 1 — Do-Not-Repeat Register (concluded directions)

### (a) Do not try to rescue the BMC "coordination gain" narrative

- **Conclusion**: the claim that BMC's diagnosis-guided coordination beats serial assembly
  on outcome metrics is falsified. BMC is retained **only** as bounded, auditable budget
  allocation + resampling mechanics (hard round/improvement bounds, deterministic
  reference-point diagnosis, full trace).
- **Evidence** (triple falsification): P0 budget-matched control — Cliff's δ = 0.278 < 0.3
  gate, Wilcoxon p = 0.129, NO-GO (`p0_budget_matched_summary.json`, 2026-08-03); P3 guided
  vs unguided at identical mechanics and budget — δ = 0.222, p = 0.110, NO-GO
  (`p3_guided_vs_unguided_summary.json`, 2026-08-03); Fig 5 b/c mechanism ablations — no
  test survives BH-FDR (`fig5_summary.json`). Date closed: 2026-08-03.

### (b) Do not build junction (5'UTR–CDS) auto-repair

- **Conclusion**: fixing junction burial always costs global stability — there is no free
  lunch. Three mutually corroborating pre-registered NO-GOs closed every route we tried
  (post-hoc weight tuning, design-time integration, generate-and-select). The full-length
  ddG metric survives as a **report/profile-only** metric; no score, issue, or repair path
  consumes it.
- **Evidence**: P1 v2 stability-weight sweep — hard repair 7/7 at every weight but median
  stability cost 0.0214–0.0249/nt, never ≤ the 0.0110/nt gate, NO-GO
  (`p1_v2_stability_sweep_summary.json`, 2026-08-04); junction-integrated LinearDesign
  optimizer — penalty/metric coordinate mismatch (global CKY fold vs fragment-fold burial),
  hard repair ≤ 2/7 at all w_jun, NO-GO (`junction_integrated_optimizer_summary.json`,
  2026-08-04); ddG Phase-0 pilot Route C (codon shuffle) — only 1/3 targets pass
  (|ΔMFE/nt| gate), overall NO-GO → plan A (`junction_ddg_pilot_summary.json`, 2026-08-05).

### (c) Do not revive cross-campaign memory strategies

- **Conclusion**: the E4 case-memory / experience-injection strategy is abandoned (user
  decision). Memory cut budget 74.2% (814 vs 3153 evaluations) but showed no learning-curve
  improvement and no design gain; nothing here justifies a retry with the same mechanism.
- **Evidence**: E4 full matrix (20 targets × 2 arms × 3 seed groups = 120 campaigns, 115
  success + 5 memory-arm cli_failures): all 3 memory learning slopes positive (one-sample t
  p = 0.91), design-gain endpoint 0/4 metrics significant (best: CDS CAI p = 0.092,
  δ = +0.17, NS after BH) → overall NO-GO (`e4_full_summary.json`, 2026-08-07).

### (d) Cross-LLM backend matrix experiment — cancelled

- **Conclusion**: the planned extension of the Fig-6b backend matrix (purchasing 5
  additional API keys) is cancelled. Rationale: the only LLM touchpoints are advisory
  (QualityAgent review, SynthesisAgent); DeepSeek's results there extrapolate — no material
  difference across backends is expected, and everything else in the system is
  deterministic.
- **Evidence / record**: user decision 2026-08-10. Existing fig6b data is kept as
  historical fact: DeepSeek arm 19/19 (93 QualityAgent calls, 414,088 prompt + 194,261
  completion tokens); the nominal Claude arm's 8 failures were endpoint misconfiguration
  (404s against a gateway that does not serve it), not a model result
  (`fig6_backends.jsonl`, `MODEL_API_USAGE.md`).

### (e) Never ground screening/ranking claims on an unprofiled oracle

- **Conclusion**: no oracle may support a screening, ranking, or docking claim until it has
  passed `CapabilityProfiler` anchor-set profiling for that capability. Optimization claims
  are restricted to relative, same-target comparisons on verified metrics.
- **Evidence**: E1 — screening 0/18 oracle×target cells (AUROC > 0.8 gate), ranking no cell
  at ρ ≥ 0.6, docking 0/5 native top-1 (`e1_capability_summary_v2.json`, 2026-08-04); P2 —
  EGARPS native_probability on known aptamers: thrombin Kd series ρ = 0.40,
  binder-vs-negative AUROC = 0.356, NO-GO (`p2_aptamer_calibration_summary.json`,
  2026-08-03). The cost of violating this rule is quantified by E2: both legacy flagship
  claims (Fig 4 main effect, Fig 7B pegaptanib comparison) died under re-audit, survival
  0/2 (`E2_SELF_AUDIT_FIG4_FIG7B.md`).

### (f) Budget-matching iron rule

- **Conclusion**: any best-of-pool or hypervolume comparison must use equal total
  generated-and-evaluated candidates in both arms (and comparable compute where wall-clock
  is claimed). This applies to every mechanism that regenerates candidates per round.
- **Evidence**: the Fig-4 Type-II "main effect" (egarps p = 2.1e-4, hypervolume p = 2.6e-4)
  collapsed to δ = 0.278 NS once the serial arm was budget-matched (P0,
  `p0_budget_matched_summary.json`). Codified in the pilot-first rule
  ([`MANUSCRIPT.md`](MANUSCRIPT.md) §2). Date: 2026-08-03.

### (g) An LLM advisor (QualityAgent) never flips a successful run to failed

- **Conclusion**: quality-review output is advisory. If the LLM review call fails, the
  report is marked `review_unavailable` (zero-confidence `pass`) with the error retained in
  `state["_quality_review_error"]` for audit; an LLM-chosen `abort` is recorded as advice
  only. Hard-failure retry is decided solely by `WorkflowResult.is_hard_failure`.
- **Evidence**: governance fix 2026-08-10 after two incidents (DeepSeek-402 review failure
  returned a destructive abort; a hallucinated LLM abort downgraded a good run, 2026-07).
  See `CHANGELOG.md` 2026-08-10 (§19 v3.4.0 entry) and `INTERFACE_LOCKS.md` §19.

### (h) Do not launch E5-S2 (18 targets) without a generation-method-layer change

- **Conclusion**: under an unchanged generation layer, scaling constraint navigation from 5
  to 18 targets is pointless — end-to-end delivery is saturated between arms, so the paired
  McNemar is structurally p = 1.0 (discordant pairs ≈ 0). E6 (generation-layer navigation)
  was the sanctioned route instead.
- **Evidence**: E5 S1 final (r5) NO-GO with all remaining failures structural in the
  generation-method layer (λ-gear separation, λ saturation, feasible-gear coverage);
  S2-not-recommended rationale recorded in `E5_REPORT_2026-08-09.md` (2026-08-09).

---

## Part 2 — Confirmed Positive Results (established, citable)

| # | Result | Evidence |
|---|--------|----------|
| 1 | **E3 dual gating works**: on the 20-task audit set, gated vs ungated agent cut the false-positive claim rate 57.9% → 0% (relative reduction 100%), true-positive retention 112.5% (8 → 9), decision-layer overreach events 23 → 0 | `e3_runs_full_summary.json`; write-up `RESULTS4_E3_MATERIALS.md` |
| 2 | **E6 GenNav S2 primary endpoint GO**: per-profile JCD-pass paired McNemar (C vs A, n = 54 = 18 targets × 3 profiles) p = 1.86e-09, discordant 30:0, c_e2e_gene = 1.0. Secondary endpoint failed and is disclosed (Wilcoxon p = 1.65e-07 passes; quality bundle fails on HER2-class targets) | `e6_s2_verdict_aggregated.json`; closeout `HANDOFF_2026-08-10_E6_CLOSED_S2_GO.md` |
| 3 | **Junction ddG metric is valid**: constraint obedience 216/216, ddG ≥ 0 in 216/216, LinearFold-vs-Vienna parent Pearson r = 0.9449 — adopted as report/profile metric (LOCK §14 v2.8.0) | `junction_ddg_pilot_summary.json` (gate 1 GO) |
| 4 | **Project methodology**: interface locks + budget matching + pre-registered pilots with GO/NO-GO gates caught three expensive errors before scale-up (P0 budget confound, P1 v2/P2/Route-C junction line, E4 memory) | `MANUSCRIPT.md` §2; pilots under `experiments/results/` |
| 5 | **Platform output biological validity (Fig 2)**: 209/210 benchmark tasks succeed across 11 workflows; designed CDS CAI median 0.744 (n = 18) vs WT 0.730 (n = 20) vs random-synonymous 0.674 (n = 200; WT > random p = 5.6e-07); inverse folding exact match 22/25 | `fig2_summary.json` |
| 6 | **Open problem registered, not hidden**: HER2-class zero-feasible-λ-gear targets (`feasible_gears = []` → degrade path) are an unsolved methodological problem for generation-layer navigation; to be handled by the next probe round | `e6_s2_verdict_aggregated.json`; handoff 2026-08-10 §0/§1 |

---

## Part 3 — One-Line Timeline

- **2026-04**: platform built — tool wrappers, microservices, first workflows.
- **2026-05 → 07**: 11 workflows completed; legacy Fig 2–7 campaign executed and data-frozen.
- **2026-08-03**: four pivot pilots (P0–P3) falsified the coordination-gain and unprofiled-oracle narratives → redesign to the calibrated agent (`REDESIGN_2026-08-03_CALIBRATED_AGENT.md`).
- **2026-08-04 → 10**: calibrated campaign E1–E6 ran to completion — E1 oracle profiling (all capabilities fail), E2 self-audit (0/2), E3 gating (GO), E4 memory (NO-GO, abandoned), E5 selection-layer navigation (S1 NO-GO), E6 generation-layer navigation (S2 GO).
- **2026-08-10**: E6 closed (S2 GO, primary p = 1.86e-09); code slimming + seven-layer renumbering + QualityAgent governance fix; cross-LLM backend matrix cancelled; this register created; documentation cleanup (see `CHANGELOG.md`).
