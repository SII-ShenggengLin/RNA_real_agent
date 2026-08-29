# Figure Plan v5 — Six Main Figures for the Nature Methods Submission

> Owner doc for the `experiments/plots/paper_v5/` rebuild (2026-08-20).
> Design inputs: `docs/PAPER_DRAFT.md` (section structure) and
> `docs/PAPER_FACT_SHEET.md` (every number's evidence file).
> Style: shared `style.py` — Morandi palette, Arial, white background, strict
> arm→colour code (blue = gated/navigation/designed, terracotta = ungated/rule,
> sage = wild-type/certified, grey = random/null/baseline). One script per
> panel under `figN/<letter>_<slug>.py` exporting `figN/panels/<letter>.{pdf,png}`;
> `figN/assemble.py` composes the figure and draws panel letters.

## Layout grid

Page width 183 mm (Nature Methods double column), margins 5 mm, gaps 3 mm.
Standard results figure = 3 columns × 55 mm panels, 3 rows × 42 mm panels
(assembled page ≈ 181 × 149 mm). Fig 1 uses a mixed grid (below). Schematic
panels use free-form axes with pastel fills (`CREAM`, `CREAM_DK`) and
colour-coded arrows: solid slate = data flow, dashed terracotta = gate/block.

---

## Fig 1 | RNADesignAgent: a calibrated, tool-first agent for RNA design (6 panels)

| Panel | Content | Type | Size (mm) | Data source |
|---|---|---|---|---|
| a | End-to-end cycle: user goal → tool-first platform (LLM never writes sequences; every call audited) → candidates + audit trail; seven-layer stack L0–L6 drawn as the platform spine | schematic | colspan 3, 50 | ARCHITECTURE.md facts |
| b | Multi-agent execution layer (L4): PipelineAgent / SpecialistAgent / QualityAgent (advisory) / SynthesisAgent with measured contributions | schematic | colspan 2, 46 | PAPER_DRAFT Methods |
| c | Platform at a glance: 41 scientific tools · 21 services · 11 workflows · 210 tasks · 5,747 audit events · 12 sessions | KPI radar + audit-composition donut inset (tool_call vs gate_decision) | 55 × 46 | `workspace/audit/platform_audit.jsonl`, tool_specs |
| d | CapGate: anchor sets → capability profiling → SelfModel grades → DecisionGate / ClaimGate → append-only trail; scope ladder | schematic | colspan 2, 46 | CapGate Methods |
| e | GenNav: gear-lattice feasibility probe → budget allocation (guarantee rounds) → per-profile delivery or declared degrade; gear lattice drawn as a navigation map | schematic + lattice navigation map | 55 × 46 | GenNav Methods |
| f | RNADesign-210 composition: two-level sunburst (workflow family → workflow → task count) + null models + literature anchors annotation | two-level sunburst + annotations | colspan 3, 34 | `fig2_summary.json` coverage |

## Fig 2 | Eleven workflows, biologically valid outputs, full auditability (9 panels)

| Panel | Content | Type | Data |
|---|---|---|---|
| a | 210/210 task success by workflow (per-task tile carpet, all pass; n printed in row labels, ok/n success counts at row ends, tile-semantics legend in the bottom-right corner) | per-task tile carpet on a shared task-count axis (single panel; the former companion summary-bar panel merged into it, 2026-08-27 figure revision) | `fig2_summary.json` coverage |
| b | CDS null model, CAI arm: designed (golden-path ranked deliverable, species-resolved codon tables) vs WT vs random-synonymous (median 0.832/0.729/0.675; designed-vs-WT P=6.9e-4 δ=0.63; WT-vs-random P=6.8e-7 δ=0.67; post-species-fix re-run 2026-08-25) | violin + jitter | `exp2_cds_nulls/fig2_cds_nulls.jsonl` |
| c | CDS null model, folding arm: MFE/nt three-arm — designed −0.336 vs WT −0.051 vs random −0.047 (designed vs both P≤7e-8 δ=−1.0; WT vs random NS P=0.29); designed leads on CAI and structure simultaneously | violin + jitter | `exp2_cds_nulls/fig2_cds_nulls.jsonl` |
| d | Secondary-structure inverse folding: per-benchmark distance dots, 21/25 exact (reset run 2026-08-25; miss dot-bracket distances 2/2/4/6, base-pair distances 1/2/3/1) | stacked dot plot (Wilkinson): one dot per benchmark stacked above its distance, stack counts printed on top (2026-08-27 figure revision — the step cumulative encoding was not intuitive) | `exp4_inverse_folding/records.jsonl` |
| e | IRES literature panel (9 pos: 6 viral + 3 cellular / 50 neg GENCODE 5′UTR), threshold-free ROC + CI band — **figure endpoint: mode-2 sliding-window scanning arm, AUROC 0.673 (0.467–0.862, P=0.102)** (user re-registration 2026-08-26; the legacy panel's protocol and the oracle's native regime, matching the E16 oracle grading); pre-registered mode-0 default-path primary 0.478 (0.311–0.649, P=0.841) archived as `fig2e_ires_roc_mode0.*`; both below the 0.8 gate the capability profile assigns this oracle | ROC + CI band | `exp5_ires_panel/summary.json` |
| f | siRNA off-target scan: per-task predicted off-target hits of the delivered (best-ranked) candidate (reset run 2026-08-26: 21/22 at zero; sole nonzero = the bowtie2 identity-70 edge task, 3 hits; diamonds mark the two trace-verified transcriptome scans against GENCODE v46 — one clean, one the nonzero; the other zeros are scan-skipped per their benchmark inputs, one for lack of a species transcriptome reference) | stacked dot plot (Wilkinson): one dot per task stacked above its predicted off-target hit count, stack counts printed (2026-08-28 figure revision — the per-task lollipop read as 21 identical zeros along a task axis; aligned with the fig2d encoding) | `exp6_sirna_offtarget/records.jsonl` |
| g | Small-molecule oracle two-sided: in-distribution AUROC 0.974 (0.968–0.980) / 0.983 (0.961–0.997) vs OOD 0.722 (0.278–1.0) / 0.563 (0.063–1.0), all CI (reset run 2026-08-26: every registered metric of the retained evidence reproduced exactly — 3,545/3,545, zero failures) | forest dot + CI | `exp7_rnasmol_boundary/summary.json` |
| h | Production audit trail, frozen corpus = the audit slice of the 241 registered Exp-8 runs (user-confirmed 2026-08-27; reset run 2026-08-27): **10,217 events — 8,798 tool calls (86.2%, 40 tools, 6 failures in one recovered retry session) + 1,377 gate decisions (13.5%; reject 690 / require_profiling 553 / downgrade 134; 11 oracles) + 42 ranking assemblies + 0 claims**; representative session by pre-registered rule = PA_036 (full-length mRNA, 3 turns, 152 calls + 32 gates of all three verdicts) | representative-session milestone track (call-status dots + gate-decision diamonds; per-turn lanes split at >60 s idle gaps; 2026-08-28 user-directed figure revision — the composition donut dropped, its numbers already stated in the Results text and this caption; in-figure titles removed, one 6-pt ink-black text style, legend inside the track's empty upper right, single-column geometry) | `exp9_audit_stats/data/exp9_corpus.jsonl` (frozen slice + SHA-256 manifest; source `platform_audit.jsonl`) |
| i | End-to-end runtime by workflow (log scale; reset run 2026-08-27: **241/241 timed end-to-end runs, zero unresolved failures** = all 210 RNADesign-210 tasks + the 31 PA regression sessions, one CLI form subprocess per run, pre-warmed GPU-pinned services, CapGate advisory regression convention, inputs verbatim, no thresholds; workflow medians 2.5 s–6.3 min, pooled median 2.6 min; 76% ≤5 min, 93% ≤10 min, 240/241 ≤1 h — the single >1 h run is the GenNav navigation aptamer session at 98.6 min; PA-arm timeout amended 3600→10800 s before the disclosed PA_028 re-run — the registered budget was calibrated on suite-task maxima and under-covered multi-turn navigation sessions; original censored record retained, driver timeout now kills the process group) | log-axis ECDF curves | `exp8_runtime/{lane_*,pa_batch}.jsonl` + `summary.json` |

## Fig 3 | Three failure modes are measurable defaults (9 panels)

| Panel | Content | Type | Data |
|---|---|---|---|
| a | Failure-mode schematic: uncalibrated trust / claim overreach / confounded improvement entering an ungated agent | schematic | — |
| b | Screening: AUROC bubble-matrix heatmap 3 oracles × 6 targets, **0/18 pass (gate 0.8), all CIs cover chance** (reset run 2026-08-27: 66/66 zero-intervention re-scored through the deployed chain; 11/18 cells identical to the retained evidence, EGARPS cells shift by ProteinX-complex realization variance, largest +0.48 — headline invariant; sensitivity 5 cells >0.6, 2 >0.7) | bubble-matrix heatmap (size + colour encode AUROC) + printed values + chance reference line | `exp10_structure_oracle_screening/summary.json` |
| c | Ranking: per-cell Spearman ρ dots vs 0.6 gate, **no cell shows reliable ranking power** (v3 extended re-run 2026-08-28: 54/54 zero-intervention, 27 cells — **4/27 nominal passes, all CIs span zero**: all three oracles on IFN-γ (ρ=0.71/0.66/0.60, n=6, single in-silico-mutant family <1 Kd order, caveat registered) + proteinx × Ang2 n=3; sensitivity 8/6/4/2; first reset run 2/18 nominal of the same vacuous class, retained best 0.56 reproduced bit-identically, 10/18 v2 cells identical across runs) | Cleveland dot plot + nominal-pass rings (reset run only; no reference lines) | `exp11_oracle_ranking_power_v3/summary.json` |
| d | Docking: native-pose rank lollipop, **19 complexes / 14 independent protein targets, 0/19 native top-1** (ranks 6–20 of 21; reset run 2026-08-27 zero-intervention on the user-approved v3 anchor extension — 397/399 poses scored through the deployed EGARPS service, two reproducible service-side failures disclosed; decoy protocol offline-calibrated to the retained evidence, anchored by reproducing 1HVU native n_contacts = 152 exactly; the retained five complexes reproduce the 0/5 headline) | lollipop (2026-08-29 revision: no in-figure title, no group-band shading, target-group labels moved to the caption (aptamer→target mapping listed left to right), top-1 gate line dropped — one rank above the x-axis it read as a duplicate axis, the criterion is stated in the caption, single marker style — provenance legend dropped (reset run only, fig3c convention), single 6-pt ink-black text, NF-κB corrected, anchored 45° tick labels, 1200-dpi PNG) | `exp12_docking_capability/summary.json` |
| e | Affinity calibration: thrombin Kd series + pooled binder-vs-negative separation, **no validated calibration — chance-level at scale** (reset run 2026-08-28, Exp 13 on the full v3 anchor set: 95/95 zero-intervention, pilot 6/6; six-point thrombin series ρ=0.49 sub-gate, retained 4-point 0.40 re-measures 0.20 = realization variance; pooled AUROC **0.5225 (CI 0.391–0.652, 62 vs 28)** — the retained 15-record pilot's below-chance 0.356 does **not** survive scale; per-entry inversion reproduces 1:1 — pegaptanib 1.27e-6 vs scrambled TBA 0.983; all three ridgeline classes (67 binders / 11 literature negatives / 17 random sequences) span the full 9-order score range with interleaved medians; legacy-12 1:1: median |Δnp| 7e-4, 3 large shifts = the disclosed EGARPS bimodal class) | Kd–score scatter (thrombin emphasized, ρ annotated) + horizontal ridgeline densities sharing the log-score axis | `exp13_affinity_calibration/summary.json` |
| f | Claim overreach (ungated), 45-task reset scale: **FP 30/55 = 54.5% (CI 41.5–67.0)**, class-selective — deterministic 23 TP / 0 FP vs untrusted-oracle **93.8%** (ranking 16/17, screening 9/10); overreach events **59**, all untrusted, spread 8–11 per oracle×use cell; strata legacy-20 55.6% / 28 events vs extension-25 53.6% / 31; legacy-20 subset reproduces the registered control arm (57.9% / 23) within realization variance (reset run 2026-08-29 zero-intervention, live deployed oracle chain, 45/45, 0 failures) | waffle + bar | `exp5_claim_overreach/runs_summary.json` |
| g | Profiling certifies where power exists: MRL oracle 3 families — **all pass both gates** (AUROC 0.9903/1.000/1.000, CIs clear chance; ρ 0.926/0.920/0.835, descriptive CIs 0.75–0.95 all above gate; random 50-nt = the registered in-distribution positive control) (reset run 2026-08-29: 706/706 zero-intervention through the deployed GEMORNA service via the production tool path, pilot 6/6; every registered number reproduced exactly — per entry 706/706 bit-identical, max \|Δ\| = 0) | forest dot + CI vs gates (left AUROC: chance 0.5 + gate 0.8; right ρ: zero + gate 0.6; value printed above each dot) | `exp14_mrl_oracle_certification/summary.json` |
| h | Deployed-artifact fidelity (reset 2026-08-29, Exp 15 + same-day addendum): the git-recovered v0.2.0 service re-measured in a sandbox **0.790/0.420** (open markers; the registered incident 0.786/0.410 reproduces within ≤ 0.009) forking to both shipped paths re-verified live, zero-intervention, on all 1,662 official test pairs — default tool path (normalization verified applied per pair) **0.975/0.986**, verbatim endpoint **0.974/0.983** bit-identical to exp7; the exp7 prediction that agent-side normalization would re-introduce the defect class **falsified** (AUROC-neutral, score-perturbing: pdb median \|Δp\| 0.083, max 0.910) — the shared case treatment across arms isolates the v0.2.0 **adjacency rewrite** as the damage carrier | dumbbell + verification fork | `exp15_rnasmol_fidelity/summary.json` + `exp15_rnasmol_v020_sandbox/summary.json` |
| i | Confounded improvement dissolved: δ trajectory ungated effect (+0.46, P=2.1e-4) → budget-matched (0.278, NS) → guided-control (0.222, NS) → self-audit survival 0/2 | annotated slope + gate + permutation-null histogram inset (observed δ marked) | `fig4_summary.json`, `p0`, `p3`, E2 audit |

## Fig 4 | CapGate eliminates false claims, preserves true ones (9 panels)

| Panel | Content | Type | Data |
|---|---|---|---|
| a | CapGate schematic: DecisionGate + ClaimGate, scope ladder, deterministic, audited | schematic | — |
| b | E3 headline: FP rate 57.9%→0% and TP retention 112.5% (8→9) | grouped bars w/ values | `e3_runs_full_summary.json` |
| c | Per-claim adjudication: ungated (11 FP/8 TP) vs gated (0 FP/9 TP/1 supp/1 borderline) | per-claim colour-block matrix (task × status) + mosaic inset | e3 summary per-claim |
| d | Overreach events: 23 → 0 by category | paired bars + Δ annotation (23→0) | e3 runs |
| e | E3-M mRNA side: per-task-family verdicts, FP 38.9%→8.3%, TP 11/11; suppressions land on utr3/junction/cross-family | paired categorical strip | `e3_mrna_runs_full_adjudicated_summary.json` |
| f | Selective, not prohibitive: gate behaviour on certified vs transferred vs unprofiled oracles (allow/downgrade/require_profiling) | decision matrix | `e7_gate_demo.jsonl` |
| g | Production gate decisions: reject 816 / require_profiling 355 / downgrade 46 by oracle | horizontal Cleveland dot plot by oracle | `platform_audit.jsonl` |
| h | Governance: quality review advisory (19/19 with and without; retries 2 vs 0) | paired strip | `fig6_quality_ablation.jsonl` |
| i | LLM minimalism: calls per task/arm across campaigns (E3 2/task both arms; E6 2.4/gene; E14 1/run) — gates and guarantees are deterministic | bubble strip (dot size = calls per task) | campaign verdicts |

## Fig 5 | GenNav delivers pre-registered multi-constraint profiles (9 panels)

| Panel | Content | Type | Data |
|---|---|---|---|
| a | GenNav mechanism: probe → allocate (guarantee rounds) → deliver/degrade; budget cap | schematic | — |
| b | Why selection-layer failed (E5): pool pass rates (GFP 0/315→12/315; insulin diversity 0.0082 < 0.02 gate) | bars + gate line | E5 report numbers |
| c | mRNA primary endpoint: discordant 30:0, McNemar P=1.9e-9, n=54 | paired dots + counts + permutation-null histogram inset | `e6_s2_verdict_aggregated.json` |
| d | mRNA delivery map: 18 targets × 3 profiles pair-outcome mosaic (C-only / both / none) | categorical heatmap | `e6_s2_runs.jsonl` evaluations |
| e | mRNA secondary endpoint (disclosed): quality bundle fails via HER2 zero-feasible-gear degrade; LLM 43 calls (2.4/gene) | bullet bars + annotation | e6 verdict quality block |
| f | Aptamer campaign arc E8→E15: b:c discordance and P per campaign with labelled levers (lattice, priors, guarantee) | lollipop + P line | `e8/e9/e10/e12/e14/e15_verdict_s2.json` |
| g | E14 decisive: delivered cells 26/36 vs 15/36; e2e 6/12 vs 0/12; discordant 14:3 (P=0.0127) | grouped bars + inset mosaic | `e14_verdict_s2.json` |
| h | E14 delivery map: 12 targets × 3 profiles pair-outcome mosaic | categorical heatmap | e14 pairs |
| i | Budget compliance + production: raw spend ≤48/target; 1 LLM call; VEGF live campaign | cost–delivery Pareto scatter (cap-hit / early-stop markers) + breakthrough step-line inset | e14 secondary |

## Fig 6 | Pre-registered negative results delineate durable boundaries (9 panels)

| Panel | Content | Type | Data |
|---|---|---|---|
| a | The two-sided capability map: oracle × task-type grades (verified / failed / unprofiled) | categorical heatmap + task-type colour strips | E1 + E7 + RNAsmol verdicts |
| b | Junction repair has no free lunch: four pre-registered attempts vs their gates (P1 repair 13/14 but stability cost; P1v2 sweep; junction-integrated optimizer; ddG Route C 1/3) | small-multiple gate bars | `p1*`, `junction_*` summaries |
| c | ddG metric validity: obedience 216/216; LinearFold vs Vienna parent r=0.945 | bar + scatter | `junction_ddg_pilot_runs.jsonl` |
| d | Cross-campaign memory does not pay: budget −74.2% but no learning slope (3/3 positive, P=0.91), 0/4 quality gains | dual: bars + slope lines | `e4_full_summary.json` |
| e | Generator boundaries: ODesign zero-output (ferritin class, 24 final failures), LinearDesign memory ceiling (fail-fast), HER2-class no feasible λ | boundary matrix | `failure_taxonomy.json`, e6 runs |
| f | Aptamer scarcity boundary (E15): 14:6, P=0.115; pooled E14+E15 28:9, P=0.003 | mosaic + pooled inset | `e15_verdict_s2.json` |
| g | Escape routes closed (E11 simulation): cap-64 grid P≥0.34 across variants; asymmetric 48/64 P=0.0215 rejected by budget rule | P dot plot + rule line | E11 sim results (FACT_SHEET §4) |
| h | Failure taxonomy of all campaigns: 35 final failures classified; 188 transient recovered | two-level sunburst (failure class → subclass) + transient-recovery bars | `failure_taxonomy.json` |
| i | LLM usage & cost: per-campaign external-LLM call counts + measured tokens; everything else local | bars + annotations | `MODEL_API_USAGE.md` |

## Supplementary tables and figures (outside the six main figures)

| ID | Content | Type | Data |
|---|---|---|---|
| Suppl. Table S1 | Representative ungated claims and their gated rewrites, with gate reasons (moved out of main Fig. 4 in the v5 rebuild; cross-referenced from the Fig. 4 legend) | table | `e3_runs_full.jsonl`, E3-M adjudication |
| Suppl. Note S2 | GenNav aptamer pre-registration archive: campaign timeline (Gantt-style chart), user-adjudicated criteria revision, exact-McNemar power analysis, E14 discordant-cell sensitivity, protocol addenda, file map | note + tables | `docs/SUPPLEMENTARY_GENNAV_APTAMER.md` §S1–S6 |

2026-08-25 lettering unification: the main-figure legends in
`PAPER_DRAFT.md` were re-lettered to this plan (they had kept pre-rebuild
lettering — stale in Figs. 1 b/c/f, 2 g–i, 3 f–i, 4 c–i, 5 d–i, 6 g–i);
previously uncited panels gained Results citations (Fig. 1c,f; 2g; 4g,i;
6g–i). This plan remains the single source of truth for panel lettering.

2026-08-25 figure-type diversification: panel chart types across Figs. 1–6
diversified after a structured survey of eight agentic-science references
(`relevant_references/`: Robin, Co-Scientist, DeepRare, ERA, Biomni,
CASCADE, BioMedAgent, SeFMol) — KPI radar (1c), gear-lattice navigation
map (1e), two-level sunbursts (1f, 6h), per-task tile carpet (2a), stacked
dot plot (2d), log-axis ECDF (2i),
representative-session milestone track (2h), bubble-matrix heatmap (3b),
ridgeline densities (3e), permutation-null histogram insets (3i, 5c),
per-claim colour-block matrix + mosaic inset (4c), paired bars + Δ
annotation (4d), Cleveland dot plot (4g), bubble strip (4i),
cost–delivery Pareto scatter + breakthrough step-line inset (5i),
task-type colour strips (6a). Panel lettering, data sources and all
numbers unchanged; the legends in `PAPER_DRAFT.md` now name the new
types.

## Caption statistics conventions

Every caption states: n, exact test, two-sided P (or NS), effect size
(Cliff's δ / ρ / AUROC), and pre-registered gate where applicable. On-panel:
asterisks NS/\*/\*\*/\*\*\*/\*\*\*\* + exact P; gate thresholds as dashed
reference lines (0.8 AUROC, 0.6 ρ, δ ≥ 0.3, top-1/3, 48-raw budget).

## Build & QA

```bash
cd rna_agent_system/experiments/plots/paper_v5
python assemble.py            # renders every figN/assemble.py
```

QA loop: each assembled `figN.png` inspected via vision model for (i) Morandi
consistency, (ii) Arial consistency, (iii) text/element overlap, (iv) panel
letter placement; panel scripts iterate until clean.
