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

## Fig 3 | Three failure modes are measurable defaults (8 panels)

| Panel | Content | Type | Data |
|---|---|---|---|
| a | Screening: AUROC bubble-matrix heatmap 3 oracles × 9 targets, **2/27 nominal passes > 0.8, all 27 CIs cover chance** (v3 extended re-run 2026-08-28 — the run the panel shows: 95/95 zero-intervention through the deployed chain; proteinx × swH3-HA 0.833 (CI 0.33–1.0) + egarps × IFN-γ 0.833 (CI 0.50–1.0), both small-n; FGF2 widest-Kd-span target sub-gate 0.37/0.63/0.30; sensitivity 10/7/2/0 at 0.6/0.7/0.8/0.9. First 6-target reset run 2026-08-27: 66/66, 0/18 pass, all CIs cover chance; 11/18 cells identical to the retained evidence, EGARPS cells shift by ProteinX-complex realization variance, largest +0.48 — headline invariant) | bubble-matrix heatmap (size + colour encode AUROC) + printed values + chance reference line | `exp10_structure_oracle_screening_v3/summary.json` (first 6-target run: `exp10_structure_oracle_screening/summary.json`) |
| b | Ranking: per-cell Spearman ρ dots vs 0.6 gate, **no cell shows reliable ranking power** (v3 extended re-run 2026-08-28: 54/54 zero-intervention, 27 cells — **4/27 nominal passes, none reliable — the three IFN-γ CIs span zero; the proteinx × Ang2 cell is a degenerate n = 3 estimate (ρ = 1.0, CI [1.0, 1.0], realization-flip entries)**: all three oracles on IFN-γ (ρ=0.71/0.66/0.60, n=6, single in-silico-mutant family <1 Kd order, caveat registered) + proteinx × Ang2 n=3; sensitivity 8/6/4/2; first reset run 2/18 nominal of the same vacuous class, retained best 0.56 reproduced bit-identically, 10/18 v2 cells identical across runs) | Cleveland dot plot + nominal-pass rings (reset run only; no reference lines) | `exp11_oracle_ranking_power_v3/summary.json` |
| c | Docking: native-pose rank lollipop, **19 complexes / 14 independent protein targets, 0/19 native top-1** (ranks 6–20 of 21; reset run 2026-08-27 zero-intervention on the user-approved v3 anchor extension — 397/399 poses scored through the deployed EGARPS service, two reproducible service-side failures disclosed; decoy protocol offline-calibrated to the retained evidence, anchored by reproducing 1HVU native n_contacts = 152 exactly; the retained five complexes reproduce the 0/5 headline) | lollipop (2026-08-29 revision: no in-figure title, no group-band shading, target-group labels moved to the caption (aptamer→target mapping listed left to right), top-1 gate line dropped — one rank above the x-axis it read as a duplicate axis, the criterion is stated in the caption, single marker style — provenance legend dropped (reset run only, fig3b convention), single 6-pt ink-black text, NF-κB corrected, anchored 45° tick labels, 1200-dpi PNG) | `exp12_docking_capability/summary.json` |
| d | Affinity calibration: thrombin Kd series + pooled binder-vs-negative separation, **no validated calibration — chance-level at scale** (reset run 2026-08-28, Exp 13 on the full v3 anchor set: 95/95 zero-intervention, pilot 6/6; six-point thrombin series ρ=0.49 sub-gate, retained 4-point 0.40 re-measures 0.20 = realization variance; pooled AUROC **0.5225 (CI 0.391–0.652, 62 vs 28)** — the retained 15-record pilot's below-chance 0.356 does **not** survive scale; per-entry inversion reproduces 1:1 — pegaptanib 1.27e-6 vs scrambled TBA 0.983; all three ridgeline classes (67 binders / 11 literature negatives / 17 random sequences) span the full 9-order score range with interleaved medians; legacy-12 1:1: median |Δnp| 7e-4, 3 large shifts = the disclosed EGARPS bimodal class) | Kd–score scatter, single panel (thrombin ringed, ringed-marker legend entry carrying ρ; pegaptanib callout) (2026-08-29 revision: legend recentred as a single row under the whole figure — was clipped at the figure edge under the right panel; ridgelines spread evenly across their panel — were squashed into the left half; thrombin-ρ annotation moved into the head band above the data; pooled-AUROC stat moved off-panel into the Fig-3d caption (the fig3c convention); pegaptanib callout repositioned clear of points; scatter x-range extended to cover all 62 Kd binders — the three IFN-γ points at Kd 440–914 nM previously fell outside the axes; single 6-pt ink-black text; 1200-dpi PNG; round 2, same day: one-sided ridges replaced by mirrored density violins (same data, same Scott-bandwidth KDE — the half-violin look read as odd for three side-by-side groups), the legend row dropped in favour of direct group labels under each violin, the pegaptanib leader shortened to a short horizontal stub; round 3, same day: violin KDEs truncated at the probability boundary (score = 1 — density above a probability of one is a bandwidth artefact), restoring an empty head band that now carries the pooled-AUROC stat on-panel (value + CI + n, superseding the round-1 caption-only move); round 4, same day: the pooled-AUROC stat taken back off the panel (its 62-vs-28 basis — the registered P2 Kd-binder convention — read as inconsistent with the 67/11/17 group labels; value + CI + composition live in the caption and main text) and the ordinate marked directly on the right panel instead (y tick labels + major gridlines across the violins); round 5, same day: the thrombin head-band label replaced by a ringed-marker legend entry so the ink-ringed points are self-explanatory; round 6, same day: density violins replaced by jittered per-class column scatter with median ticks (at n = 11–67 over a nine-order log range a density curve implies structure that is not in the data — every point shown, medians ticked on the ordinate); round 7, same day: the class-distribution companion panel dropped altogether — single-panel Kd–score scatter; the class-separation evidence (pooled AUROC + three-class medians) is text-reported in the caption and main text, the screening failure shown systematically in row a) | `exp13_affinity_calibration/summary.json` |
| e | Claim overreach (ungated), 45-task reset scale: **FP 30/55 = 54.5% (CI 41.5–67.0)**, class-selective — deterministic 23 TP / 0 FP vs untrusted-oracle **93.8%** (ranking 16/17, screening 9/10); overreach events **59**, all untrusted, spread 8–11 per oracle×use cell; strata legacy-20 55.6% / 28 events vs extension-25 53.6% / 31; legacy-20 subset reproduces the registered control arm (57.9% / 23) within realization variance (reset run 2026-08-29 zero-intervention, live deployed oracle chain, 45/45, 0 failures) | bar (2026-08-30 revision, user-directed: waffle + bar → **bar only** — the per-claim waffle was judged too low-density, its class selectivity (deterministic 23/23 TP vs aptamer 30/32 FP) stated in one sentence in the Fig-3e caption and main text; same-day first round: no in-figure titles or summary stats (headline numbers in the caption, panel letter at assembly — the fig2d–fig3f convention; the two block titles had mutually overlapped), use legend a centred row directly under the panel (was figure-bottom), oracle labels centred on their bar pairs, single 6-pt pure-black text, absolute-mm layout, 1200-dpi PNG; round 3, same day: use-legend handles grey blue → the palette's reserved neutral dark warm grey (they encode only the solid/light alpha channel — the oracle colours are direct-labeled on the y-axis, no colour legend) and the legend anchored to the axes centre (was figure-centred, 6 mm left of the axes); round 4, same day (user direction): the neutral handles replaced by a six-swatch style key — two rows of the three oracle colours, solid = ranking objective above light = screening evaluation, one swatch per bar style, centred on the axes; round 5, same day (user direction): the two-row key collapsed to a single row — solid trio labelled ranking objective, then light trio labelled screening evaluation) | `exp5_claim_overreach/runs_summary.json` |
| f | Profiling certifies where power exists: MRL oracle 3 families — **all pass both gates** (AUROC 0.9903/1.000/1.000, CIs clear chance; ρ 0.926/0.920/0.835, descriptive CIs 0.75–0.95 all above gate; random 50-nt = the registered in-distribution positive control) (reset run 2026-08-29: 706/706 zero-intervention through the deployed GEMORNA service via the production tool path, pilot 6/6; every registered number reproduced exactly — per entry 706/706 bit-identical, max \|Δ\| = 0) | forest dot + CI vs gates (left AUROC: gate 0.8 dashed; right ρ: gate 0.6 dashed; value printed above each dot) (2026-08-30 revision, user-directed: chance/zero reference lines dropped — the certification reading rests on the pre-registered gates, chance stays visible on the shared 0–1 axis and in the caption (the fig2g second-revision convention); every text element pure black #000000 (the fig3e convention); the two x-label second lines shortened — they had mutually overlapped at the inter-panel gap, the tier/ranking n's moved into the caption; value labels white-backed against the gate dashes; row labels rewritten as the Sample-2019 5′UTR library names; rebalanced absolute-mm layout, 1200-dpi PNG) | `exp14_mrl_oracle_certification/summary.json` |
| g | Deployed-artifact fidelity (reset 2026-08-29, Exp 15 + same-day addendum): the git-recovered v0.2.0 service re-measured in a sandbox **0.790/0.420** (open markers; the registered incident 0.786/0.410 reproduces within ≤ 0.009) forking to both shipped paths re-verified live, zero-intervention, on all 1,662 official test pairs — default tool path (normalization verified applied per pair) **0.975/0.986**, verbatim endpoint **0.974/0.983** bit-identical to exp7; the exp7 prediction that agent-side normalization would re-introduce the defect class **falsified** (AUROC-neutral, score-perturbing: pdb median \|Δp\| 0.083, max 0.910) — the shared case treatment across arms isolates the v0.2.0 **adjacency rewrite** as the damage carrier | dumbbell + verification fork (2026-08-30 revision, user-directed: every text element pure black #000000 (the fig3e convention — the chance tag had been dark warm grey); x-label shortened to "Screening AUROC" (the held-out-split clause is caption material; the long label read as a misplaced title); in-figure legend rewritten as strategy labels without the internal version string or provenance qualifiers — "Pre-fix preprocessing" / "Tool-path normalization" / "Verbatim input" (the re-measured/live provenance lives in the caption); fork value labels moved left of the open markers — the below-placement sat on the gate 0.8 dashes; the chance line retained — the pre-fix PDB arm (0.420) falls below it, unlike fig2g/fig3f whose dropped chance lines carried no below-chance point); saved at the true 88 × 50 mm canvas, no tight crop, figure-centred legend row (the sparse panel's 78-mm tight crop had made the uniform 6-pt text effectively oversized next to the sibling panels)) | `exp15_rnasmol_fidelity/summary.json` + `exp15_rnasmol_v020_sandbox/summary.json` |
| h | Confounded improvement dissolved at full-panel scale (reset 2026-08-29→31, Exp 16): the removed coordination loop reconstructed driver-side verbatim (deterministic AptamerCoordinator rules recovered from git 1b45138~1; BMC stays out of the platform) — apparent effect **δ = +0.140 (P = 0.0026, already sub-gate)** → budget-matched **δ = +0.050 (P = 0.21, NS)** → fixed-resampling **δ = −0.012 (P = 0.73, NS)**; self-audit survival **0/2** vs the 70% threshold; 240 cells = 4 arms × 20 targets × 3 seeds, 228 successful (Ferritin the registered zero-output boundary), 56/56/57 paired (target, seed) cells, loop 56/57 hotspot-expansion branch, realized pools 8/16/16/16; deployment topology with service replicas disclosed | annotated slope + gate + permutation-null histogram inset (observed δ marked; quadrant-adaptive placement; stage dots terracotta / grey blue / sage, trajectory warm grey, gate dashed dark warm grey) | `exp16_confounded_improvement/summary.json` |

2026-08-31 Fig 3 composite assembled: `experiments/plots/fig3_assemble.py` →
`experiments/plots/output/fig3_composite.{pdf,png}` (190.5 × 254.6 mm page;
PNG 8999 × 12029 px at 1200 dpi from the all-vector PDF — the one embedded
raster element is the fig3a colour-bar gradient, re-rendered at 1200 dpi the
same day). Nature conventions re-verified against the published DeepRare main
Figs. 2–4 (`relevant_references/`, Nature 651, 2026): bold lowercase letters
at each panel's top-left corner (Helvetica-Bold 8 pt, no period/brackets),
strict reading order a → h, rows top-aligned so same-row letters share one
line. Layout (same-day user-directed revision): a full width; b + c share row
2 edge to edge — c embedded in a two-sub-row composite layout
(`fig3c_docking_lollipop_composite.{pdf,png}`, `FIG3C_LAYOUT=composite`;
the 19 lollipops wrap 11 + 8 at the SARS-CoV-2 RBD | PSMA group boundary
onto a 97.2 × 103.8 mm canvas matching b's height; the standalone
single-row panel c is unchanged); d + e share row 3 as matched-height
panels — d re-rendered smaller (86.7 × 44.1 mm) and e larger
(85.5 × 41.4 mm), both with unchanged 6-pt fonts and no data change, so the
first layout's height-mismatch blank band under e is gone; f g h close the
figure as one equal-height row (the fig2 fgh-row convention: one drawn
height 90.2 pt, per-panel scales ≈ 0.69/0.64/0.81, leftover width becomes
even gutters) — h does not span the full width; the first layout's
full-width h variant was retired the same day (standalone h panel
unchanged).

## Fig 4 | CapGate eliminates false claims, preserves true ones (8 panels)

| Panel | Content | Type | Data |
|---|---|---|---|
| a | E3 dual-arm re-run (Exp 17 gated arm + Exp 5 ungated control, 45 tasks, 2026-08-31): **FP rate 54.5% → 0%** (0/31, Wilson CI 0–16.1) and **TP retention 80.0% (25 → 20, below the pre-registered 90% gate)** — losses decompose as 2 true metric claims suppressed by the uniform basis rule (unprofiled deterministic-proxy dependency), 2 length-sloppy sequences correctly abstained (counterfactual FPs), 2 lucky untrusted TPs unretainable by design, +1 rescue | grouped bars w/ values | `exp17_claim_gating/summary.json` |
| b | Per-claim adjudication: ungated 25 TP / 30 FP vs gated **20 TP / 0 FP / 7 suppressed / 4 borderline** (task × status colour-block matrix, sage = retained / terracotta = false claim — the Biomni Fig. 2C–E convention; + arm × verdict mosaic inset) | per-claim colour-block matrix (task × status) + mosaic inset | `exp17_claim_gating/summary.json` (per_task_matrix) |
| c | Overreach events: **59 → 0** by oracle × use (ungated = Exp 5: RhoFold 9+11, ProteinX 11+8, EGARPS 11+9; gated = Exp 17: 0 in every cell — 71 plan requests blocked at the decision gate, stated in the caption) | paired bars + Δ annotation (59→0) | `exp5_claim_overreach/runs_summary.json` + `exp17_claim_gating/summary.json` |
| d | E3-M mRNA side re-run (Exp 18 dual-arm, 20 tasks, 2026-09-01): per-task-family verdicts, **FP 35.3% → 8.3%** (6/17 → 1/12), **TP 11/11 = 100%**; gated FPs fall to zero on utr3/junction via plan-layer blocks (6 blocked requests, the model publishes no claim — outlined empty cells), cross-family claims downgraded to relative scope (neutral); the one surviving FP = the symmetric MRL rank flip on the weakest certified family | paired categorical strip by task family + arm × verdict mosaic inset | `exp18_mrna_claim_gating/summary.json` |
| e | Selective, not prohibitive: gate behaviour on certified vs transferred vs unprofiled oracles (allow/downgrade/require_profiling) | decision matrix | `e7_gate_demo.jsonl` |
| f | Production gate decisions: reject 816 / require_profiling 355 / downgrade 46 by oracle | horizontal Cleveland dot plot by oracle | `platform_audit.jsonl` |
| g | Governance: quality review advisory (19/19 with and without; retries 2 vs 0) | paired strip | `fig6_quality_ablation.jsonl` |
| h | LLM minimalism: calls per task/arm across campaigns (E3 2/task both arms; E6 2.4/gene; E14 1/run) — gates and guarantees are deterministic | bubble strip (dot size = calls per task) | campaign verdicts |

## Fig 5 | GenNav delivers pre-registered multi-constraint profiles (8 panels)

| Panel | Content | Type | Data |
|---|---|---|---|
| a | Why selection-layer failed (E5): pool pass rates (GFP 0/315→12/315; insulin diversity 0.0082 < 0.02 gate) | bars + gate line | E5 report numbers |
| b | mRNA primary endpoint: discordant 30:0, McNemar P=1.9e-9, n=54 | paired dots + counts + permutation-null histogram inset | `e6_s2_verdict_aggregated.json` |
| c | mRNA delivery map: 18 targets × 3 profiles pair-outcome mosaic (C-only / both / none) | categorical heatmap | `e6_s2_runs.jsonl` evaluations |
| d | mRNA secondary endpoint (disclosed): quality bundle fails via HER2 zero-feasible-gear degrade; LLM 43 calls (2.4/gene) | bullet bars + annotation | e6 verdict quality block |
| e | Aptamer campaign arc E8→E15: b:c discordance and P per campaign with labelled levers (lattice, priors, guarantee) | lollipop + P line | `e8/e9/e10/e12/e14/e15_verdict_s2.json` |
| f | E14 decisive: delivered cells 26/36 vs 15/36; e2e 6/12 vs 0/12; discordant 14:3 (P=0.0127) | grouped bars + inset mosaic | `e14_verdict_s2.json` |
| g | E14 delivery map: 12 targets × 3 profiles pair-outcome mosaic | categorical heatmap | e14 pairs |
| h | Budget compliance + production: raw spend ≤48/target; 1 LLM call; VEGF live campaign | cost–delivery Pareto scatter (cap-hit / early-stop markers) + breakthrough step-line inset | e14 secondary |

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
representative-session milestone track (2h), bubble-matrix heatmap (3a),
Kd–score scatter (3d), permutation-null histogram insets (3h, 5b),
per-claim colour-block matrix + mosaic inset (4b), paired bars + Δ
annotation (4c), Cleveland dot plot (4f), bubble strip (4h),
cost–delivery Pareto scatter + breakthrough step-line inset (5h),
task-type colour strips (6a). Panel lettering, data sources and all
numbers unchanged; the legends in `PAPER_DRAFT.md` now name the new
types.


2026-08-31 Fig 4a/4b drawn from the Exp-17 dual-arm re-run (`experiments/plots/fig4a_claim_gating_headline.py` → `fig4a_claim_gating.{pdf,png}` grouped bars, FP rate + Wilson CI / TP counts, ungated terracotta vs gated sage; `experiments/plots/fig4b_claim_matrix.py` → `fig4b_claim_matrix.{pdf,png}` 45-row task × arm per-claim colour-block matrix with arm × verdict mosaic inset). Rows a/b updated to the re-measured numbers. Same-day: row c drawn (`experiments/plots/fig4c_overreach_events.py` → `fig4c_overreach_events.{pdf,png}`, same frozen results, no re-run).

2026-09-01 Fig 4d drawn from the Exp-18 E3-M dual-arm re-run (`experiments/plots/fig4d_mrna_family_strip.py` → `fig4d_mrna_family_strip.{pdf,png}`: 20 task rows grouped by the eight task families × two arm blocks, one tile per published claim — sage TP / terracotta FP / warm grey neutral, outlined-white = no published claim (the gated arm's plan-block abstentions) — with the arm × verdict mosaic inset). Row d updated to the re-measured numbers (FP 35.3% → 8.3%, TP 11/11).

2026-08-31 summary-panel removal (user direction): Figs 3–5 drop their lead
summary panel a — the failure-mode schematic (Fig 3, drawn 2026-08-31 and
removed the same day), the CapGate mechanism schematic (Fig 4) and the GenNav
mechanism schematic (Fig 5). Every results figure now opens directly on an
experimental-result panel: former panels b–i are re-lettered a–h in the three
figures, and the fig3b–i plot scripts and their pdf/png outputs are renamed to
fig3a–h accordingly (fig3a_failure_modes.* deleted). The mechanism schematics
live on in Fig 1 (d CapGate loop, e GenNav loop), which now carries the
mechanism citations from the Results text; Fig 2a (task-success carpet) and
Fig 6a (capability map) are data panels and unchanged. Historical registers
(CHANGELOG entries, pre-registered driver docstrings, frozen result summaries)
keep their as-written panel letters.

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
