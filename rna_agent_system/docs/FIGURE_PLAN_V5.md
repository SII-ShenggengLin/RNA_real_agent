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
| a | 210/210 task success by workflow (per-task tile carpet, all pass; n printed) | per-task tile carpet + horizontal-bar summary | `fig2_summary.json` coverage |
| b | CDS null model: CAI designed vs WT vs random-synonymous (median 0.745/0.729/0.672; MW P=4.0e-7, δ=0.69) | violin + jitter | `fig2_cds_nulls.jsonl` |
| c | Folding-energy control: MFE/nt WT vs random (NS, P=0.23) — CAI lift is not a folding artifact | violin + jitter | `fig2_cds_nulls.jsonl` |
| d | Secondary-structure inverse folding: per-benchmark distance dots, 22/25 exact | strip + step cumulative curve | fig2 raw runs (GPU jsonl) |
| e | IRES prediction: ROC curve, AUROC 0.762 (CI 0.43–0.98), 3 pos / 49 neg | ROC + CI band | `fig2_literature_panels.jsonl` |
| f | siRNA designs: predicted off-targets per task (21/22 at zero) | lollipop/strip vs zero line | fig2 raw runs |
| g | Small-molecule oracle two-sided: in-distribution AUROC 0.974/0.983 vs OOD 0.722/0.563, all CI | forest dot + CI | `rnasmol_boundary_panel.json` |
| h | End-to-end runtime by workflow (log scale; 210-task suite + PA regression batches) | log-axis ECDF curves + box inset | fig2 runtime rows + PA tsv |
| i | Production audit trail: 4,530 tool calls (39 tools) + 1,217 gate decisions; composition donut + sessions | donut + representative-session milestone track (call-status dots + gate-decision diamonds) | `platform_audit.jsonl` |

## Fig 3 | Three failure modes are measurable defaults (9 panels)

| Panel | Content | Type | Data |
|---|---|---|---|
| a | Failure-mode schematic: uncalibrated trust / claim overreach / confounded improvement entering an ungated agent | schematic | — |
| b | Screening: AUROC bubble-matrix heatmap 3 oracles × 6 targets, 0/18 pass (gate 0.8) | bubble-matrix heatmap (size + colour encode AUROC) + printed values | `e1_capability_summary_v2.json` |
| c | Ranking: per-cell Spearman ρ dots vs 0.6 gate (best 0.56) | dot plot + gate line | e1 v2 |
| d | Docking: native-pose rank lollipop for 5 complexes (0/5 top-1; TBA 21/21) | lollipop + gate zone | e1 v2 part B |
| e | Calibration inversion: thrombin Kd series (ρ=0.40) + binders-below-negatives (AUROC 0.356; pegaptanib ~2e-6 vs scrambled 0.99) | scatter + ridgeline densities (binders / negatives / random 30-mers) | `p2_aptamer_calibration_summary.json` |
| f | Claim overreach (ungated): FP 11/19 (57.9%), overreach events by category (23) | waffle + bar | `e3_runs_full.jsonl` |
| g | Profiling certifies where power exists: MRL oracle 3 families (AUROC 0.99–1.0, ρ 0.84–0.93) | dot + CI vs gates | `e7_mrna_oracle_profile_summary.json` |
| h | Deployed-artifact fidelity: RNAsmol service pre-fix (0.786/0.410) → official parity post-fix (0.974/0.983) | slope/dumbbell | `rnasmol_boundary_panel.json` |
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
| i | Budget compliance + production: raw spend ≤48/target; 1 LLM call; production runs 1CA2 47/48 (5 guarantee rounds), 3CNA 35/48 (early stop), VEGF live | cost–delivery Pareto scatter (cap-hit / early-stop markers) + breakthrough step-line inset | e14 secondary + `gennav_*_navigation_result.json` |

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
map (1e), two-level sunbursts (1f, 6h), per-task tile carpet (2a), step
cumulative curve (2d), log-axis ECDF + box inset (2h),
representative-session milestone track (2i), bubble-matrix heatmap (3b),
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
