# Decisions, Concluded Directions and Do-Not-Repeat Register

> **Purpose**: the single register of what this project has concluded — directions we will
> **not** pursue again (with the evidence that closed them), positive results that **are**
> established (with their evidence pointers), and a one-line project timeline.
> Before proposing any new experiment, optimization, or narrative claim, check Part 1 first.
> **Last updated**: 2026-08-22

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
  See `CHANGELOG.md` 2026-08-10 (§19 v3.4.0 entry).

### (h) Do not launch E5-S2 (18 targets) without a generation-method-layer change

- **Conclusion**: under an unchanged generation layer, scaling constraint navigation from 5
  to 18 targets is pointless — end-to-end delivery is saturated between arms, so the paired
  McNemar is structurally p = 1.0 (discordant pairs ≈ 0). E6 (generation-layer navigation)
  was the sanctioned route instead.
- **Evidence**: E5 S1 final (r5) NO-GO with all remaining failures structural in the
  generation-method layer (λ-gear separation, λ saturation, feasible-gear coverage);
  S2-not-recommended rationale recorded in `E5_REPORT_2026-08-09.md` (2026-08-09).

### (i) Do not re-open the aptamer GenNav primary endpoint via symmetric budget rescale or panel expansion (2026-08-13)

- **Conclusion**: after E8/E9/E10 (aptamer side, 48-raw two-arm budget-matching cap),
  the primary endpoint (paired McNemar p < 0.05 ∧ C e2e ≥ 0.8) is closed on both escape
  routes. (1) A symmetric cap rescale 48→64 is structurally NO-GO: every symmetric
  extension of the A-arm static grid (63–64 raw) strengthens the rule-based baseline
  (A-fail 14 → 5–8) and erodes the navigator's discordant repairs (b = 9 → 2–7) while
  sub-20%-pass-rate bands still absorb reinforcement rounds (c = 3–4); floor-round and
  degrade-aware C protocols do not rescue it. (2) Panel expansion cannot reach p < 0.05:
  the benchmark has 20 targets (19 usable after the ferritin zero-output exclusion) and
  the full-panel two-sided McNemar is ≈ 0.11–0.13 (the "20-target p ≈ 0.07" estimate in
  `HANDOFF_2026-08-13_E10_COMPLETE.md` was a one-sided value). The asymmetric A-48/C-64
  variant alone reaches p = 0.0215 in simulation but changes the comparison basis (C +33%
  budget while A demonstrably could use it, A-fail 14 → 5 at 63 raw) — rejected by user
  decision against the budget-matching iron rule (Part 1 (f)). The aptamer boundary is
  structural: the navigator's advantage peaks at 48 raw and shrinks as the static grid
  grows (same saturation logic as E5/E8).
- **Evidence**: `experiments/analysis/e11_feasibility_sim.py` (pre-registration-gate
  simulation on the real E10 S2 cache, 5 A-lattice × 3 C-protocol grid, deterministic);
  `e10_verdict_s2.json` (b=9/c=4/p=0.267); exact two-sided McNemar recomputation for the
  panel scenarios; `docs/FIX_2026-08-12_DUAL_GENERALIZATION.md` 附录 H (2026-08-13).

### (j) Oracle-ontology boundary: learned outcome predictors gated; thermodynamic/algorithmic computation never gated (2026-08-18)

- **Conclusion**: the CapGate managed-oracle set follows one boundary rule,
  now encoded in the ToolSpec ontology (`ToolKind` / `OracleDescriptor`,
  CHANGELOG 2026-08-18 (b)): a tool is a managed oracle **iff** it is a
  learned predictor of a biological outcome **whose score a workflow consumes
  as candidate-quality evidence** (ranking / screening / docking use).
  Thermodynamic and algorithmic structure computation (ViennaRNA folding,
  LinearFold, BLAST/Bowtie2, CAI, GC/metrics) is `compute` — established
  conventions, deterministic, never gated. Generators produce candidates and
  are never gated; their outputs are evaluated by the oracles above them.
  Under this rule the **E16+ profiling backlog is fixed at five pending
  oracles**: GerNA-Bind, RNASTOP, IRESfinder, CRGPT handle score, CRISOT
  off-target score — all consumed as evidence in production workflows while
  unprofiled; each is reviewed+audited (never blocked) until its campaign
  delivers SelfModel records, then flips to `enforce`. Consequence accepted
  by user decision (2026-08-18): any pending oracle that fails profiling will
  be blocked in production, the affected workflow components zeroed equally,
  and RNADesign-210 panels / fig2 numbers regenerated rather than the verdict
  softened.
- **Evidence**: `agent_core/tool_interface.py` (ontology schema);
  `tests/test_tool_ontology.py` (pinned enforce/pending sets);
  `experiments/results/tool_inventory.json` (54 tools: 40 production /
  2 experiment-only / 11 reserved / 1 demo).

### (k) Task-keyed gating + the microservice-internal oracle transparency boundary (2026-08-18)

- **Conclusion (gating keying)**: DecisionGate reviews are keyed to the
  **calling workflow's** task type, never to the oracle's registered default
  alone (`task_context` contextvar set by `BaseDomainWorkflow`; W1.2,
  CHANGELOG 2026-08-18 (c)). Cross-workflow oracle reuse is therefore
  adjudicated honestly: RhoFold from `rna_tertiary_structure_design` gates as
  unprofiled (no records for that task), not as an inherited E1-aptamer
  failure. Flagship workflows keep byte-identical verdicts because their
  `task_type` equals their SelfModel record keys (pinned in
  `tests/test_task_context.py`).
- **Registered boundary (audit transparency)**: oracle invocations that
  happen **inside a microservice** (e.g. the GerNA-Bind service folding RNA
  via RhoFold internally when no PDB is supplied) are not `ToolExecutor`
  calls — they are neither gated nor recorded in the platform audit trail.
  The paper's "every tool call is recorded" claim is accurate at the agent
  tool-call layer only. Do **not** present service-internal hops as gated;
  closing this gap (service-side audit write-back) is future platform work,
  registered here so it is not rediscovered as a "bug".
- **Evidence**: `agent_core/calibrated/runtime.py` (`task_context`,
  `_TASK_TYPE_CONTEXT`); `agent_core/workflows/base.py` (`task_type`,
  `_task_type_context`); `rna_aptamer_design.py` (contextvars thread
  propagation); `tests/test_task_context.py` (5 tests incl. thread pattern).

### (l) E16/E17/E18 verdicts: three pending oracles failed their declared-use gates; CRISOT-Score + CRGPT remain pending on a registered data gap (2026-08-18)

- **Conclusion (graded, all enforce now)**: the first three E16+ profiling
  campaigns returned **all-failed verdicts on the oracles' declared uses** —
  IRESfinder (screening AUROC 0.679/0.731/0.762 across three upstream
  held-out families, gate 0.8), GerNA-Bind (screening AUROC 0.462 on the
  17-pair PDB panel — chance level; S0 sign inversion foreshadowed it:
  binder mean 0.197 < negative mean 0.255), RNASTOP (screening verified
  AUROC 0.908 [0.853, 0.956] but ranking ρ = 0.579 < 0.6 — its declared use
  in the mRNA workflows is a ranking component). All three flipped
  pending → enforce with SelfModel records (29 packaged records now):
  under the default enforce policy these calls are gated in production.
  Consequence per the standing user decision (row (j)): the affected
  workflow components zero equally / the workflow degrades, and
  **RNADesign-210 + fig2 panels are to be regenerated against the gated
  platform** (registered next step; not softened).
- **Registered data gap**: CRISOT-Score (`crisot_off_target_score`) and CRGPT
  (`crgpt_handle_score`) stay governance=pending — no labeled anchor set
  exists on disk (CRISOT ships an unlabeled On/Off example; the CRGPT repo
  has no efficiency benchmark). Do not improvise self-referential anchors
  (e.g. on-vs-off discrimination on CRISOT's own example.csv — trivially
  biased, not a biological efficacy measurement); curating real GUIDE-seq /
  CIRCLE-style datasets is the prerequisite for E19/E20.
- **Evidence**: `experiments/results/e16_e17_e18/verdict.json` (+ per-campaign
  verdicts, raw scoring caches, `self_model.json`); anchor sets
  `data/benchmarks/external_anchors/{ires/e16_ires_anchor_set.json,
  small_molecule/e17_gernabind_anchor_set.json,
  mrna_stability/e18_rnastop_anchor_set.json}` (curator:
  `experiments/curate_e16_e17_e18_anchor_sets.py`, assertion-checked,
  deterministic).

### (m) BMC framework removed from the system (2026-08-18)

- **Conclusion**: the BMC implementation itself (not just the narrative) was
  deleted from the codebase — `CoordinatorAgent`, `workflows/coordinator.py`,
  the `run_initial`/`bmc_prepare`/`bmc_run_round`/`bmc_finalize` interface on
  `full_length_mrna_design` and `rna_aptamer_design`, the `bmc_*` input
  fields, and the `_bmc_trace` audit plumbing. Both workflows now run the
  plain generate → evaluate → score → ASF/Pareto-rank path. Removal
  condition satisfied: P0 (`p0_budget_matched_summary.json`) showed that
  serial generation at equal evaluated-candidate budget is statistically
  indistinguishable from BMC (δ = 0.278 < 0.3 gate, p = 0.129, BMC wins 9/12
  cells NS), and Fig 3 showed no significant ASF difference at any BMC depth
  on Type-I — so deleting the loop costs no measured performance. The
  auditable ASF reference-point ranking and the per-run state/tool-trace
  writeback are retained unchanged. Historical BMC-ablation evidence
  (fig3/fig4/fig5, P0, P3) remains in `experiments/results/`.
- **Evidence**: this register (a) + (f); `docs/CHANGELOG.md` 2026-08-18.

### (n) Superseded/dead code is deleted, not archived in-tree (2026-08-18)

- **Conclusion**: user-directed simplification policy — code is the source of
  truth; once a strategy is superseded or falsified, its implementation is
  deleted instead of accumulating compatibility layers. Applied 2026-08-18:
  12 dead tools (junction-aware LinearDesign, junction codon shuffler, six
  reserved CRISOT alternates, LinearFold evaluate/zuker, batch LinearDesign,
  codonw-slim) with their service endpoints; the E1/E3-era calibrated
  experiment machinery (profiler / experiment_planner / campaign_runner /
  case_memory); all concluded E1–E15 experiment drivers, probes, one-off
  repair scripts, analysis scripts (except `stats_utils.py`) and plot
  scripts. The `experiments/results/` evidence tree is the durable audit
  record and is never deleted. If a deleted strategy is ever needed again,
  re-derive it from the results JSONs and the distilled cores kept in-tree
  (e.g. `agent_core/generation/gennav_aptamer.py`).

### (o) ASF audit fixes + shared ranking layer is the single multi-objective ranking mechanism (2026-08-20)

- **Conclusion**: the 2026-08-20 audit of the ASF ranking strategy (user-
  directed) found the augmented-Chebyshev skeleton correct (formula,
  normalization discipline, Pareto companion, documented utopian-caveat) but
  four defects, all fixed the same day. (1) A per-candidate *missing*
  objective was omitted from that candidate's Chebyshev max — omission can
  only lower ASF, so per-candidate evaluation failures were **rewarded**
  (extreme case: a candidate measured only on its champion dimension could
  win with ASF 0); missing dimensions now impute at the measured pool-worst
  value, and the aptamer/siRNA 0.0-literal fills became `None` + imputation
  (the 0.0 fills had also distorted the min-max normalization of measured
  candidates). (2) A partial user `reference_point` silently collapsed the
  ranking onto the supplied subset; still restricts, but now flagged
  (`asf_ranking_note`). (3) Pool-wide unmeasured dimensions (CapGate
  enforce blocks, optional evaluators off) drop for everyone equally and are
  reported. (4) The ~100-line implementation existed twice, line-identical;
  both flagship workflows now call
  `workflows/multi_objective.py::apply_reference_point_ranking`.
- **Generalization policy**: ASF reference-point ranking is the **only**
  multi-objective ranking mechanism in the system. It is the default for
  every workflow whose candidate pool carries ≥2 heterogeneous objectives:
  full-length mRNA (cds/MRL/stability/MFE), aptamer (EGARPS/RhoFold/ipTM),
  siRNA v1.3.0 (efficiency/specificity/end-asymmetry — the terminal 5-bp
  NN end asymmetry of Khvorova 2003 / Schwarz 2003 computed additively by
  the sirna-duplex service v0.5.0, zero additional folding; Borda ranks
  demoted to diagnostics),
  sgRNA v1.3.0 (nn/crisot/crisot_specificity; `weight_*` inputs renormalized
  as ASF weights), tertiary-structure v1.2.0 (rhofold/rmsd/tm; TM-score
  injected at ranking time from the alignment TM-score with the additive
  `weight_tm_score` input — both closeness dims drop pool-wide in de-novo
  runs; audit guidance: closeness weights above `weight_rhofold` when a
  reference exists, since pool-relative min-max otherwise lets a pLDDT
  champion bury the native-closest candidate), and ASO v1.1.0 (2026-08-22,
  (q): accessibility × binding, Borda ranks demoted to diagnostics — the
  2026-08-20 classification of ASO under "intentionally not converted" is
  revised by (q); single-objective/n=1/domain-formula tasks remain
  unconverted: CDS combined score, sequence scoring, IRES, secondary
  structure, small molecule). siRNA ranks the full passing
  pool before truncating to `candidate_count` (the inherited
  truncate-then-rank order could drop the pool's best window before it was
  ever ranked). For the remaining single-objective/n=1/domain-formula tasks
  ASF is vacuous. Score functions and output keys unchanged; `total_score`-style
  keys remain reported diagnostics, preserving every consumer.
- **Standing boundary**: ASF values remain pool-relative — min-max
  normalization makes ranks non-monotonic under pool composition and the
  utopian reference can be attained (ASF 0); cross-pool/cross-condition
  comparisons must not compare raw ASF distances (use shared fixed
  reference points, per-objective components, or Pareto hypervolume — the
  in-code ANALYSIS CAVEAT stands).
- **Evidence**: `tests/test_multi_objective_utils.py` (10 new regression
  tests: imputation parity, partial-ref flagging, pool-wide drop, weight
  renormalization); full suite 506 passed (baseline 496);
  `docs/CHANGELOG.md` 2026-08-20 (b); `docs/WORKFLOWS.md` §2 shared ASF
  ranking policy.

### (p) Ranking governance: ASF objectives are assembled from CapGate verdicts (2026-08-21)

- **Conclusion**: the shared ASF ranking layer consumes the DecisionGate
  verdict as a first-class input (`agent_core/calibrated/objective_assembly.py`,
  design doc [`RANKING_GOVERNANCE.md`](RANKING_GOVERNANCE.md)). Dimensions
  backed by oracles without verified (or transferred-verified) ranking power
  are demoted to `scoring_annotation` — excluded from ranking pool-wide
  equally — *before* `apply_reference_point_ranking` runs. Assembly is
  **mode-independent** (never reads `RNADA_CAPGATE`): advisory and enforce
  produce identical rankings wherever SelfModel records exist, differing only
  in whether annotation values were computed (enforce blocks demoted calls →
  annotation `gated`; recognized via `GatedActionError`, never an evaluation
  failure). Verdict→action mapping: verified → keep; transferred-verified →
  keep + flag; failed (direct or transferred) → demote; unprofiled-pending
  (CRISOT-Score / CRGPT, registered data gap (l)) → keep + `pending` flag;
  unprofiled-enforce (gemorna_3utr_stability, RhoFold under the tertiary task
  key per (k)) → keep + `unprofiled` flag — no punishment without a verdict.
  Deterministic compute dims (DECISIONS (j)) never enter the mechanism.
- **Degrade state**: a workflow whose ranking dims are fully demoted — with
  the packaged SelfModel, only `rna_aptamer_design` (all three components
  failed E1 on every family) — returns `ranking_evidence_unavailable`:
  success=True, generation order, annotations intact, no fabricated
  `asf_distance`, marker in summary/extras/`_state_writeback` (never in
  `errors` — a non-empty errors list is a hard failure). The light-stage
  RhoFold pLDDT top-k filter degrades to deterministic pool order when the
  screening profile is failed (a falsified oracle must not arbitrate
  selection).
- **Relation to (j)/(l)**: verdicts and the zeroed-equally consequence are
  unchanged; this entry supersedes only the *"fail whole workflows"*
  presentation of the accepted degradation. The regenerate-rather-than-soften
  stance is preserved — RNADesign-210 / fig2 regeneration runs against the
  platform *including* this mechanism. **Accepted divergence**: unprofiled-
  enforce dims are kept by assembly but still dropped at measurement time
  under enforce (blocked calls) — advisory ranks on more dims than enforce
  there; closes when those oracles gain records.
- **Deferred**: continuous profile-derived ASF weights (reliability factor
  over verified dims) — requires SelfModel coverage improvement and
  cross-family validation against circularity; the binary vocabulary here is
  the slot it slots into.
- **Evidence**: `tests/test_ranking_governance.py` (15 tests: per-workflow
  assembly pinning against the packaged SelfModel, mode independence, off
  escape hatch, aptamer degrade path, gated-error recognition, no-op
  regression for sirna/sgrna/tertiary/full-length); full suite 534 passed;
  `docs/CHANGELOG.md` 2026-08-21.

### (q) GenNav-λ production wiring + ASO converts to ASF; E6 evidence promoted from evidence-only (2026-08-22)

- **Conclusion (user-directed)**: two ranking/navigation consistency
  changes, both on the heels of the 2026-08-21/22 Layer-2 fresh-data audit
  (12/12 workflows, 875 audited tool calls, 0 failures;
  `workspace/layer2_fresh_audit_2026-08-21/`).
- **GenNav-λ (mrna_cds_design v1.2.0)**: the static LinearDesign λ=[0,1,4,10]
  grid is now *replaced on the opt-in `navigation=True` path* by the
  deterministic zero-LLM λ navigation (pure core
  `agent_core/generation/gennav_mrna_lambda.py`): E6's λ-curve probe
  {0,1,2,4,8,10,20,50} → band-gap-first interstitial reinforcement (refinement
  λ set, 16-raw budget, E14 cycling guarantee) → per-profile matrix delivery
  (expression/stability/balanced × 5, D1 ≥ 0.05). The E6 "evidence-only"
  status is thereby superseded **for the production wiring** — the E6 campaign
  machinery (U-scores, codon-table direction axes, LLM arbitration) stays
  deleted per (n); the production core reuses the E8–E14 levers on the
  platform's own metrics. Constraint bands are documented production
  defaults (CAI floor 0.85 anchored to E6's A1AT λ-curve boundary
  0.8377-fail / 0.8717-pass; MFE-per-nt bands from the platform's LinearFold
  metrics), **not** campaign-validated matrices — no navigation-advantage
  claim is made for the mRNA side beyond E6's registered result. Static
  path unchanged; `full_length_mrna_design` keeps the static grid (λ×UTR
  GenNav composition is a registered follow-up, not silently wired).
- **ASO → ASF (aso_target_screening v1.1.0)**: ordering is now the shared
  ASF reference-point ranking over accessibility × binding (utopian
  reference, uniform weights); Borda ranks demoted to diagnostics — same
  precedent as siRNA v1.3.0, revising (o)'s classification of ASO. Missing
  measurements impute at the measured pool-worst (0.0-literal fills
  removed). Pareto frontier + `asf_distance` attached; `composite_score`
  semantics unchanged (final rank, 1 = best).
- **Pareto annotation (mrna_cds_design v1.2.0)**: successful runs attach the
  CAI × MFE/nt Pareto frontier as extras (`pareto_frontier`,
  `pareto_frontier_size`) with per-candidate `pareto_tag` — an annotation
  only; `total_score` ordering is untouched (CDS stays a domain-formula task
  under (o)). Workflows where Pareto is vacuous (single candidate or single
  objective: sequence scoring, IRES, secondary structure, small molecule)
  are intentionally not annotated. Same-day consistency completion:
  sirna v1.3.1 / sgrna v1.3.1 / tertiary v1.2.1 now also *surface* the
  frontier the shared layer computes (previously only full-length/aptamer
  surfaced it) — every ASF workflow reports `pareto_frontier` extras +
  `pareto_frontier_size` uniformly. Adversarial tests of the surfacing
  found one defect, fixed same-day: siRNA's post-ranking truncation to
  `candidate_count` could leave undelivered candidates in the surfaced
  frontier — the frontier is now intersected with the delivered set
  (`tests/test_asf_pareto_surfacing_adversarial.py`).
- **Evidence**: `tests/test_gennav_mrna_core.py` (17),
  `tests/test_mrna_cds_gennav.py` (4: early-stop full delivery + audited
  calls, Pareto annotation + unchanged order, dedicated
  `navigation_delivery_empty` degrade, static path regression),
  `tests/test_aso_target_screening.py` (+4: ASF ordering + Borda
  diagnostics, missing-binding not rewarded, scale invariance); fresh-data
  e2e verification on live services (IFN-γ navigation run + ASO ASF rerun).
  The first live IFN-γ run domain-calibrated the delivery floor: adjacent-λ
  LinearDesign designs are near-clones (1–5% edit distance), so
  `d1_min_pairwise` = 0.05 for the CDS domain (≈25 nt of a ~500-nt CDS,
  proportionally the aptamer-side 0.15); post-calibration delivery
  expression 4/5, balanced 4/5, stability 2/5 with explicit degrade
  reasons (within-band diversity at low λ is structurally limited — the
  same λ-gear-separation saturation E5/E6 diagnosed).
  `docs/CHANGELOG.md` 2026-08-22; `docs/WORKFLOWS.md` §2/§12.

---

### (r) Layer-3 pre-flight: an *answering* degraded health endpoint fails; only an *unresponsive* one proceeds anyway (2026-08-22)

- **Conclusion (user-directed audit)**: the 2026-07-22 busy-port fix conflated
  two different failures. A listening port whose `/health` **answers** —
  200 with `status: "degraded"` (e.g. RNAsmol reporting a missing
  checkpoint) or any HTTP error — is running and *broken*, and
  `ensure_services_ready` must fail pre-flight with an error naming the
  service. A listening port whose `/health` is **unresponsive** (timeout /
  connection refused — the starved single-worker EGARPS case) keeps the
  2026-07-22 wait-then-proceed-anyway behaviour: no duplicate start, the
  tool's own long HTTP timeouts queue on the busy service. Before this
  split, `check_service_health`'s degraded-status detection was dead code on
  the `ensure_services_ready` path — every running degraded service was
  waved through pre-flight and failed later at tool-call time with a
  confusing error.
- **Mechanism**: `_classify_service_health` returns
  `ok | degraded | http_error | unresponsive`; `check_service_health` is
  `== "ok"` (legacy 2xx semantics — empty body, non-JSON body, missing
  status field — unchanged); the busy branch classifies once with a short
  timeout before waiting.
- **Do not** "fix" a degraded-service pre-flight failure by restarting the
  service: it is listening, a duplicate dies on "address already in use"
  (the 2026-07-22 restart-loop failure mode). The error message is the
  deliverable; the operator resolves the missing runtime dependency.
- **Evidence**: fresh-data audit `workspace/layer3_fresh_audit_2026-08-22/`
  (45 checks / 0 failures post-fix, live NCBI INS/5S data, real CRISOT
  cold-start + concurrent flock contention); regressions
  `tests/test_service_manager.py` (listening-degraded fails with a clear
  error, listening-http-error likewise, starved raw listener still passes —
  the 2026-07-22 test unchanged); `docs/CHANGELOG.md` 2026-08-22 (b).

---

### (s) Layer-4 boundaries: QualityAgent output stays outside ClaimGate; ranking-governance audit events are a registered event type (2026-08-22)

- **Conclusion (user-directed audit)**: the QualityAgent's `QualityReport` is
  an **internal control signal, not a publication claim**, and is
  deliberately *not* routed through ClaimGate. ClaimGate gates conclusions
  about candidate quality that will be written into final reports
  (`ClaimGate` mounts only on `SynthesisAgent` multi-node synthesis); the
  QualityReport's only execution-relevant channel is
  `parameter_overrides`, and that channel is already deterministically
  constrained — profile-declared adjustable params only, type/range/enum
  validation, user-explicit parameter protection, advisory `abort` can never
  flip a successful run. Wrapping every diagnosis round in claim
  extraction + adjudication would add LLM latency inside the control loop
  without changing any outcome-affecting path. Verified on live data in the
  2026-08-22 Layer-4 audit; revisit only if QualityReport text ever becomes
  a headline scientific statement in user-facing reports.
- **Audit's negative-space finding (keep in mind)**: the packaged SelfModel
  has **no `scoring` capability cells** (E1 profiled screening/ranking/
  docking only), so any claim declaring a `scoring` dependency on a
  profiled oracle rejects as "never profiled" even when the oracle's
  screening/ranking cells exist. Conservative and consistent with (e); not
  a defect. Do not "fix" this by inventing scoring grades without an
  anchor-set profiling campaign.
- **Mechanism fixes carried by the same audit** (details in CHANGELOG
  2026-08-22 (c)): `ranking_objective_assembly` added to the
  `AuditEvent.event_type` Literal (extend-only) — before this, *every*
  ranking-governance assembly event was rejected by pydantic and silently
  swallowed by the best-effort writer, so the (p) mechanism's audit trail
  was empty; `PipelineAgent` degrades a runtime-dangling input binding to a
  per-node failure instead of crashing the pipeline;
  `ires_prediction` surfaces generation tool failures as hard failures
  (`_generation_errors`) while keeping the legitimate empty-scan
  `success=True` contract (benchmark rubric `min_candidates=0`);
  `SpecialistAgent.retry_count` counts only real re-executions;
  `QualityAgent` coerces quoted int-enum override values.
- **Evidence**: fresh-data audit `workspace/layer4_fresh_audit_2026-08-22/`
  (37 checks across pass 1 + pass 2/2b re-verification, live NCBI
  EPO/EV71/B2M/Xenopus-5S + RCSB 1AKI, real-LLM reviews, real 2-node
  pipeline through ClaimGate-gated synthesis, CapGate enforce/advisory/off
  semantics on live services); regressions
  `tests/test_layer4_fresh_audit_regressions.py` (11 tests); suite 591
  passed; `docs/CHANGELOG.md` 2026-08-22 (c).

---

### (t) Layer-5 workspace isolation: session ids are untrusted single path components, validated before any filesystem effect (2026-08-22)

- **Decision (user-directed audit)**: `WorkspaceManager` treats a session id
  as an **untrusted, single path-safe component**. Every public method
  resolves it through `_session_dir_path`, which rejects empty/whitespace ids
  and ids containing `/`, `\`, `.` or `..` with `ValueError`
  (`delete_session` returns `False` instead, mirroring `SessionMemory`'s
  empty-id guard). Session ids reach Layer 5 from two front doors — the CLI
  `--session-id` and the FastAPI `/v1/agent/run` `task_id` (client-controlled,
  mapped verbatim to `session_id` by `workflow_api/app.py`) — so validation
  belongs at the Layer-5 chokepoint, not per-caller.
- **Why (defects demonstrated on live data)**: (1) joining an empty path
  component is a no-op, so `delete_session("")` aliased the `sessions/` root
  and rmtree'd **every** session workspace while returning `True`; (2)
  unvalidated joins let `get_session_dir("../x")` create directories outside
  `sessions/`, and an absolute id discards the base entirely — a per-session
  isolation break; (3) `list_files` created the session directory as a side
  effect of a pure listing (its `exists()` guard was dead code). All three
  fixed; legitimate id shapes in the codebase (uuid4,
  `pa020_20260716_120000`) are unaffected — PA regressions PA_006–PA_036 use
  exactly these shapes.
- **Verified clean on fresh data** (no defects found):
  `SessionMemory` (multi-turn `_previous_workflow_result` /
  `_workflow_result_history` / `_last_form_params_by_workflow` prefill,
  session isolation, deepcopy isolation, explicit-state non-persistence,
  delete semantics) and `file_manager` (round-trips, context-propagated
  session scoping — run artifacts land under `workspace/sessions/<sid>/` with
  zero global-root leaks, CapGate `tool_call` audit lines carry the session
  id). Known non-fixed wart, accepted: `SessionMemory` keeps
  `_workflow_result_history` unbounded per session (documented cross-turn
  design, CLI sessions are short-lived).
- **Evidence**: fresh-data audit `workspace/layer5_fresh_audit_2026-08-22/`
  (37 checks post-fix, live NCBI TTR NM_000371 + IFNA2 NM_000605, three real
  `mrna_sequence_scoring` runs through real services); regressions
  `tests/test_layer5_fresh_audit_regressions.py` (15 tests); suite 606
  passed; `docs/CHANGELOG.md` 2026-08-22 (d).

### (u) Layer-6 entry-point contracts: pipeline runs are session-scoped; the API never reports a crashed run as success; progress events are part of the delivered stream (2026-08-22)

- **Decision (user-directed audit)**: the three Layer-6 front doors
  (`run_form`/`stream_form`, CLI `form_chat.py`, FastAPI `workflow_api`)
  now uphold the same contracts Layer 5 established for single runs:
  (1) `AgentRunner.run_pipeline` scopes `_SESSION_ID_CTX` from
  `state["session_id"]`, and both pipeline callers (CLI `--pipeline-file`,
  `/v1/agent/pipeline`) pass one — tool artifacts of pipeline runs land
  under `workspace/sessions/<session_id>/`, never the global root;
  (2) `/v1/agent/run` derives its fallback-branch `success`/`errors` from
  the recorded `pipeline_result`, so a node that crashed without producing
  a `WorkflowResult` is reported as a failure (pre-fix: `"success": true`
  with "Execution completed but no structured result was produced");
  (3) the API `task_id` echo always identifies the session directory the
  artifacts were written under (`state["session_id"]`; the old
  `state.get("task_id")` read was dead code); (4) the locked §19
  `stream_form` event sequence actually carries progress events —
  `PipelineAgent` emits `step_start`/`step_done` per node and
  `MrnaSequenceScoringWorkflow.run` emits `generate_complete`/
  `evaluate_progress` like the base class (the override had silently
  dropped the callback); (5) the CLI `--pipeline-file` branch follows the
  same non-tty `input()` rule as `--workflow` (2026-07 EOFError incident).
- **Why (defects demonstrated on live data)**: pre-fix audit — 2-node
  pipeline runs on fresh PRL/IL10 wrote `mrna_wf_*.fasta` into the global
  `workspace/` root with the session dir empty; a path-unsafe API
  `task_id="../l6_escape_probe"` crashed the node, was rejected by the
  Layer-5 validation (decision (t) holds — nothing escaped `sessions/`),
  yet the endpoint answered `"success": true`; `stream_form` on
  `mrna_sequence_scoring` yielded zero progress events (violating the
  §19-locked sequence); the CLI pipeline branch crashed with EOFError on
  non-tty stdin when a service failed to start.
- **Verified clean on fresh data** (31 checks post-fix): live PRL mRNA
  scoring through real services with independently recomputed GC; fresh
  2-node PRL→IL10 pipeline (API + CLI) with session-scoped artifacts; HAV
  NC_001489 5'UTR IRES scan (region 1-734, prob 0.835, confidence high —
  advisory CapGate, since IRESfinder is a gated oracle per (j)/(e));
  CapGate audit lines stamped with fresh session ids; two-turn
  `SessionMemory` contract; all-11-workflow form schema/validator
  consistency.
- **Evidence**: fresh-data audit `workspace/layer6_fresh_audit_2026-08-22/`
  (live NCBI PRL NM_000948 + IL10 NM_000572 + HAV NC_001489); regressions
  `tests/test_layer6_fresh_audit_regressions.py` (15 tests); suite 621
  passed; `docs/CHANGELOG.md` 2026-08-22 (e).

### (v) Interface Lock Policy retired (2026-08-22)

- **Decision (user-directed)**: the INTERFACE LOCK policy is removed. Every
  lock comment block (tool wrappers, tool specs, state, runner,
  sequence_utils, the 11 workflow headers, 20 microservice mains, two test
  docstrings), the policy document `docs/INTERFACE_LOCKS.md`, and its
  references across the documentation were deleted — a pure-deletion source
  diff (~1,250 lines, zero functional changes; suite 621 passed unchanged).
- **Why**: the policy predated the Layer-0–Layer-6 fresh-data audit
  programme and had drifted stale — e.g. the §20 lock table still listed
  `cli/form_chat.py` as a lock anchor although that file carried no lock
  block, and version numbers lagged the audited state. The maintenance cost
  of the sync lists exceeded their protective value once every layer was
  regression-pinned by the test suite and the PA_006–PA_036 drivers.
- **Kept**: the behavioural contracts themselves — workflow pipeline order,
  scoring formulas, `_state_writeback` structure, the `stream_form` event
  sequence, artifact key set — are unchanged and remain pinned by
  `docs/WORKFLOWS.md`, the regression suite, and the PA drivers. Do not
  reintroduce lock annotations; interface changes follow the normal
  test-first rules (`CONTRIBUTING.md`).
- **Evidence**: `docs/CHANGELOG.md` 2026-08-22 (f).

### (w) Oracle version stamps: SelfModel records carry the profiling-time artifact version; drift is warned + audited, never blocking (2026-08-22)

- **Decision (user-directed)**: pure-additive drift hardening of the CapGate
  evidence chain. (1) `OracleDescriptor` gains `oracle_version` — the
  deployed oracle artifact (microservice FastAPI app version) the descriptor
  currently pins — stamped on all 11 managed-oracle descriptors in
  `tool_specs.py`. (2) `CapabilityRecord` gains record-level `oracle_version`
  (profiling-time stamp; `None` on legacy records — they load unchanged and
  never fabricate drift). (3) `CalibratedRuntime.configure` compares the two:
  a mismatch emits a `WARNING` log plus an `oracle_version_mismatch` audit
  event (type registered in the `AuditEvent` Literal — the DECISIONS (s)
  silent-drop defect class) via the public `oracle_version_drift()`
  inspection method. **Semantics unchanged**: a drifted record gates exactly
  like an aligned one (pinned by test); nothing is blocked, no verdict moves.
- **Why**: SelfModel grades describe "the artifact profiled on
  2026-08-04/11/18", but nothing tied records to the deployed artifact — a
  checkpoint/service upgrade would silently invalidate the evidence chain.
  The RNAsmol boundary panel already caught one silent deployment divergence
  (Part 2 row 8); this makes such drift structurally detectable.
- **Stamp anchoring**: the generator (`experiments/build_default_self_model.py`)
  pins **literals** — never copied from live `TOOL_SPECS` (otherwise an
  upgrade + rebuild would silently re-anchor old grades to the new artifact
  and defeat the mechanism). Backfill validity: every oracle microservice's
  version string has been unchanged in git since service introduction
  (2026-04/05), which predates all profiling campaigns, so current strings
  equal profiling-time strings. The generator asserts every packaged oracle
  has a registered stamp and fails loudly otherwise.
- **Registered follow-up (not done)**: the stamp anchors to the microservice
  app version, not the model checkpoint; a service-side startup assertion
  needs the oracle microservices to expose their artifact identity in
  `/health` (only `rnasmol_service` reports `checkpoint_path` today). When
  that lands, extend the comparison to the health-reported identity.
- **Evidence**: `docs/CHANGELOG.md` 2026-08-22 (g); tests
  `tests/test_oracle_version_stamps.py` (7); suite **628 passed** (was 621).

---

## Part 2 — Confirmed Positive Results (established, citable)

| # | Result | Evidence |
|---|--------|----------|
| 1 | **E3 dual gating works**: on the 20-task audit set, gated vs ungated agent cut the false-positive claim rate 57.9% → 0% (relative reduction 100%), true-positive retention 112.5% (8 → 9), decision-layer overreach events 23 → 0 | `e3_runs_full_summary.json`; write-up `RESULTS4_E3_MATERIALS.md` |
| 2 | **E6 GenNav S2 primary endpoint GO**: per-profile JCD-pass paired McNemar (C vs A, n = 54 = 18 targets × 3 profiles) p = 1.86e-09, discordant 30:0, c_e2e_gene = 1.0. Secondary endpoint failed and is disclosed (Wilcoxon p = 1.65e-07 passes; quality bundle fails on HER2-class targets) | `e6_s2_verdict_aggregated.json`; closeout `HANDOFF_2026-08-10_E6_CLOSED_S2_GO.md` |
| 3 | **Junction ddG metric is valid**: constraint obedience 216/216, ddG ≥ 0 in 216/216, LinearFold-vs-Vienna parent Pearson r = 0.9449 — adopted as report/profile metric (LOCK §14 v2.8.0) | `junction_ddg_pilot_summary.json` (gate 1 GO) |
| 4 | **Project methodology**: interface locks + budget matching + pre-registered pilots with GO/NO-GO gates caught three expensive errors before scale-up (P0 budget confound, P1 v2/P2/Route-C junction line, E4 memory) | `MANUSCRIPT.md` §2; pilots under `experiments/results/` |
| 5 | **Platform output biological validity (Fig 2)**: 210/210 benchmark tasks succeed across 11 workflows (panel refreshed 2026-08-11: the legacy advisory-abort siRNA task completes under current governance; OTC 354 aa / PDGFB 241 aa replaced the two oversized targets); designed CDS CAI median 0.745 (n = 20) vs WT 0.729 (n = 20) vs random-synonymous 0.672 (n = 200; WT > random p = 4.0e-07); inverse folding exact match 22/25 | `fig2_summary.json` |
| 6 | **Open problem registered, not hidden**: HER2-class zero-feasible-λ-gear targets (`feasible_gears = []` → degrade path) are an unsolved methodological problem for generation-layer navigation; to be handled by the next probe round | `e6_s2_verdict_aggregated.json`; handoff 2026-08-10 §0/§1 |
| 7 | **E7 mRNA-oracle profiling GO (2026-08-11)**: GEMORNA 5′UTR MRL verified on all three measured-MRL anchor families (screening AUROC 0.990/1.000/1.000, ranking ρ 0.926/0.920/0.835; n = 706 anchors, Sample et al. GSE114002) — the positive-control counterpart to E1; 3′UTR stability predictor registered unprofiled and gated off | `e7_mrna_oracle_profile_summary.json`; `e7_gate_demo.jsonl` |
| 8 | **RNAsmol two-sided boundary + deployment-fidelity fix (2026-08-11)**: in-distribution AUROC 0.9744/0.9828 (exact official-pipeline parity after the v0.3.0 preprocessing port), decoy ranks 2/1601 and 7/265; OOD short aptamers show no demonstrated discrimination — profiling the *deployed* oracle caught a silent preprocessing divergence that the literature numbers could not | `rnasmol_boundary_panel.json`; `docs/CHANGELOG.md` 2026-08-11 |
| 9 | **E8 aptamer GenNav — mechanical transfer confirmed, primary endpoint NOT met (2026-08-11)**: the unmodified GenNav machinery transferred to ODesign's length/seed gears and repaired every rule-arm delivery failure it met (BSA compact, VEGF extended, SARS-CoV-2 N extended) with one self-inflicted shortfall (MBP compact, 4/5) — McNemar b=3/c=1, p = 0.625, n = 30 → NO-GO on the primary gate; C e2e 9/10 vs A 7/10 at lower raw spend (mean 36 vs 48). **Do not claim a decisive aptamer-side navigation advantage** — the aptamer matrix largely saturates (26/30 concordant-pass); report as a scope finding (same saturation logic as E5). Also fixed: target-JSON hotspots are now assertion-checked against structure numbering (SARS-CoV-2 N mismatch caught) | `e8_verdict_s2.json`; `e8_runs_s2.jsonl` |
| 11 | **E12 aptamer GenNav — densified lattice + S1 priors: discordance near-significant, dual-gate unmet (2026-08-14)**: at the same 48-raw cap, the navigator wins discordant cells 9:2 vs A (McNemar P = 0.0654, one c-cell short of 0.05; E10 was 9:4/P=0.267) — lattice densification + S1-measured laplace priors are effective levers (c halved, P 4x improved, e2e ceiling 1.0 via the pre-registered panel gate). Primary endpoint still NO-GO: C e2e 0.25 vs the 0.8 gate — 48-raw per-target repair capacity cannot fully deliver 2-A-fail targets (structural), and A e2e 0.00. **Do not claim a decisive aptamer-side navigation advantage; the boundary is the dual-gate structure (P one cell short; e2e repair-capacity-capped)** — report as mechanism transfer + densification improvement + structural boundary | `e12_verdict_s2.json`; `e12_runs_s2.jsonl`; `docs/FIX_2026-08-12_DUAL_GENERALIZATION.md` 附录 K |
| 10 | **E3-M mRNA-side gating replication GO (2026-08-12)**: calibrated-agency claim-gating reproduced on the second flagship task family — full-length mRNA design-reporting tasks (20-task audit set built on real mRNA assets: 10 trusted-deterministic + 10 untrusted-oracle tasks); gated vs ungated FP rate 38.9% (7/18) → 8.3% (1/12), true-positive retention 100%, gated overreach 0. Together with E3 (57.9% → 0%), the "both flagship task families" claim now has double support | `e3_mrna_runs_full_adjudicated_summary.json`; driver `run_e3_mrna_gated_vs_ungated.py` |
| 12 | **E13 controlled replication — panel axis formally closed (2026-08-14)**: with a fresh pre-registered criteria book (`run_e13_gennav_aptamer.py`, panel rule changed to a direct per-target nav ≥ 1 ∧ a_fail ≥ 1 constraint; user confirmed this is not a standards reduction — criteria untouched), S0/S1 mechanism gates GO, panel gate PASSED with the pre-registered projection (panel identical to E12's), and S2 NO-GO **bit-identical to E12** (b=9/c=2/P=0.0654, C e2e 0.25/A 0.00; all 36 JCD pairs equal, programmatic check; whole campaign from cache in 133 s, zero new generations). **Do not expect any panel rule to move the dual-gate endpoint under 48-raw** — E12's panel was already nav-maximal (21/21); e2e ≥ 0.8 is a per-target reliability × budget bound. Combined with appendix J (matrix axis) and appendix I (protocol axis), all three axes are now formally closed; the aptamer-side boundary statement in row 11 stands with full evidence | `e13_verdict_s2.json`; `e13_runs_s2.jsonl`; `docs/FIX_2026-08-12_DUAL_GENERALIZATION.md` 附录 L |
| 14 | **E15 confirmatory replication — scarcity-panel boundary (2026-08-14)**: pre-registered dual-outcome campaign (E14-final protocol, 4 never-paneled targets + top-8 of E14's panel) — McNemar b=14/c=6/P=0.1153, C e2e 0.333 vs 0.00: the guarantee repaired all three fixable A-fail cells of the new targets (b held at 14) but conceded four cells on their A-deliverable bands (c 3→6) — **the navigation advantage is regime-specific to delivery-scarce panels**, empirically confirming the paper's scarcity thesis; pooled E14+E15 28:9 (P=0.0026, driven by E14, heterogeneity acknowledged). E14 remains the primary positive; E15 disclosed as boundary | `e15_verdict_s2.json`; `docs/FIX_2026-08-12_DUAL_GENERALIZATION.md` 附录 N |
| 13 | **E14 aptamer GenNav — PRIMARY ENDPOINT GO (2026-08-14)**: same-budget (48-raw, both arms) navigation wins discordant cells **14:3, paired McNemar two-sided P = 0.0127 < 0.05** (n=36), with C e2e 0.50 vs A 0.00 (relative full-delivery 6:0). User-adjudicated criteria revision (single-gate P<0.05; e2e demoted to secondary disclosure — e2e≥0.8 is an absolute-delivery feasibility measure conflated with navigation advantage: 12/36 cells jointly infeasible at 48-raw, axes closed appendices I/J/L) + protocol addenda (v1 cycling guarantee; v2 4×n6 rounds + n8-over-n2 unblock), all pre-registered before each run. **Citable as a positive aptamer-side navigation result**: the three validated levers are lattice densification (E12: c 4→2), S1-measured priors (E12: P 4×), and guaranteed-repair allocation (E14: starvation eliminated); mechanism block all-pass, zero violations, C matrix pass rate 1.0 | `e14_verdict_s2.json`; `e14_runs_s2.jsonl`; `docs/FIX_2026-08-12_DUAL_GENERALIZATION.md` 附录 M |

---

## Part 3 — One-Line Timeline

- **2026-04**: platform built — tool wrappers, microservices, first workflows.
- **2026-05 → 07**: 11 workflows completed; legacy Fig 2–7 campaign executed and data-frozen.
- **2026-08-03**: four pivot pilots (P0–P3) falsified the coordination-gain and unprofiled-oracle narratives → redesign to the calibrated agent (`REDESIGN_2026-08-03_CALIBRATED_AGENT.md`).
- **2026-08-04 → 10**: calibrated campaign E1–E6 ran to completion — E1 oracle profiling (all capabilities fail), E2 self-audit (0/2), E3 gating (GO), E4 memory (NO-GO, abandoned), E5 selection-layer navigation (S1 NO-GO), E6 generation-layer navigation (S2 GO).
- **2026-08-10**: E6 closed (S2 GO, primary p = 1.86e-09); code slimming + seven-layer renumbering + QualityAgent governance fix; cross-LLM backend matrix cancelled; this register created; documentation cleanup (see `CHANGELOG.md`).
- **2026-08-11** (paper v2 refresh): Fig-2 benchmark to 210/210 (legacy advisory abort reruns green under current governance); fig2a panel swap (OTC/PDGFB replace the two oversized targets; designed CAI n = 20, median 0.7454); RNAsmol v0.3.0 preprocessing-fidelity fix (exact official parity 0.9744/0.9828) + two-sided boundary panel; E7 mRNA-oracle profiling GO (MRL verified on 3/3 families); E8 aptamer GenNav S2 — mechanical transfer confirmed, primary endpoint NOT met (b=3/c=1, p = 0.625), registered as a scope finding.
- **2026-08-13 → 14** (E12 aptamer GenNav): matrix v3 + 17-length densified lattice + S1 priors + panel gate (pre-registered, addenda v1/v2) — S0/S1 GO, S2 primary endpoint NO-GO but discordance near-significant (b=9/c=2, P=0.0654; c 4->2, P 4x vs E10); C e2e 0.25 vs 0.8 gate (structural repair-capacity limit); aptamer-side conclusion: densification works, dual-gate boundary structural.
- **2026-08-14** (E13 controlled replication): fresh pre-registration (`run_e13_gennav_aptamer.py`, direct per-target nav panel rule) — S0/S1 GO, panel gate PASSED with projection hit (panel = E12's), S2 NO-GO **bit-identical to E12** (b=9/c=2/P=0.0654, e2e 0.25/0.00, all 36 pairs equal, zero new generations) → **panel axis formally closed** (matrix J / protocol I / panel L all closed); aptamer-side boundary statement final as written in row 11.
- **2026-08-14** (E15 confirmatory replication): pre-registered dual-outcome run on 4 never-paneled targets — NO-GO (b=14/c=6/P=0.1153), the 40% branch: advantage is regime-specific (delivery-scarce panels), boundary disclosed; pooled E14+E15 28:9/P=0.0026 (heterogeneity acknowledged); E14 remains the positive headline.
- **2026-08-14** (E14 aptamer GenNav — PRIMARY ENDPOINT GO): user adjudication — criteria revised to single-gate McNemar P<0.05 (e2e demoted to disclosure: absolute-delivery measure, jointly-infeasible cells at 48-raw); protocol addenda v1 cycling guarantee (b=14/c=6/0.115) and v2 4×n6 + n8-over-n2 (b=10/c=3/0.092), all pre-registered; final **GO b=14/c=3/P=0.0127, C e2e 0.50 vs A 0.00** — citable positive aptamer-side navigation result (row 13).
- **2026-08-12 → 13** (dual-generalization campaign): E3-M mRNA-side gating GO (38.9% → 8.3%, TP retention 100%); aptamer GenNav E9 (re-anchored scarcity matrix, b=6/c=8, p = 0.79) and E10 (mechanized allocation, b=9/c=4, p = 0.267) — primary endpoint still NO-GO, boundary localized to budget structure; E11 pre-registration-gate simulation closed both escape routes (symmetric cap 64: A-arm strengthening erodes b, P ≥ 0.34; panel: 20-target two-sided p ≈ 0.11–0.13) → aptamer-side conclusion fixed as "mechanism transfer + structural budget boundary"; asymmetric A-48/C-64 rejected against the budget-matching iron rule.
- **2026-08-18** (simplification pass): BMC framework removed after triple falsification (DECISIONS (a)/(m)); 12 dead tools + concluded E1–E15 drivers + legacy calibrated experiment machinery deleted (102,673 → ~51,000 LOC, 709 → 488 tests all green); PA_006–PA_024 end-to-end rerun. The packaged SelfModel (29 records) and CapGate runtime unchanged.
- **2026-08-19** (GenNav production wiring + verification pass): the E14 GenNav
  strategy became a user-reachable production path — `RnaAptamerDesignWorkflow`
  v2.1.0 opt-in `navigation` mode running the E14 protocol deterministically
  (zero LLM) through the audited capability layer; the pure-function core in
  `agent_core/generation/gennav_aptamer.py` gained the matrix-v3 constraint and
  delivery functions. Full-platform re-verification: 496 tests green,
  PA_006–PA_024 rerun, CapGate audit trail checked on live runs. The E6
  mRNA-side λ navigation stays campaign machinery (evidence-only).
- **2026-08-19** (batch-B fresh-data re-verification): second user-directed
  platform pass on entirely new inputs — PA_025–PA_036 (12 benchmarks, all 11
  workflows + two GenNav navigation campaigns) **12/12, 0 failed turns**;
  navigation delivered 5/5 × 3 profiles on both fresh targets (1CA2 47/48
  budget-capped, 3CNA 35/48 early-stop). `tool_call` audit records gained
  `session_id`/`task_type` attribution (stream_form thread-context fix).
  Evidence: `experiments/results/pa_regression_batchB_2026-08-19/`.
- **2026-08-22 (b)** (Layer-3 fresh-data audit, user-directed): first live audit of the service-orchestration layer — 21 services swept (10 up / 11 down all classified correctly), real CRISOT cold-start via `ensure_services_ready` + fresh INS-derived CRISPR scoring, concurrent flock contention (exactly one start), busy-port proceed-anyway preserved; **45 checks / 0 failures post-fix**, live NCBI INS/5S data. Three defects fixed: degraded-but-answering services passed pre-flight (now fail with a clear error — decision (r)), `cli/service_orchestrator.__all__` exported unimported names, bowtie2 `start.sh` missing the exec bit. Evidence: `workspace/layer3_fresh_audit_2026-08-22/`.
- **2026-08-22 (c)** (Layer-4 fresh-data audit, user-directed): first live audit of the multi-agent + CapGate + ranking-governance stack — 37 checks across pass 1 + pass 2/2b re-verification on live NCBI EPO/EV71/B2M/Xenopus-5S and RCSB 1AKI (real-LLM quality reviews, real 2-node pipeline through ClaimGate-gated synthesis, CapGate enforce/advisory/off on live services, ranking-governance three-mode comparison). **Five defects fixed** (decision (s)): `ranking_objective_assembly` audit events silently dropped (unregistered Literal type — the (p) audit trail was empty), `PipelineAgent` crash on runtime-dangling bindings, `ires_prediction` swallowing generation tool failures as "no candidates found", `SpecialistAgent.retry_count` counting abandoned attempts, `QualityAgent` dropping quoted int-enum overrides. Regressions `tests/test_layer4_fresh_audit_regressions.py` (11); suite 591. Evidence: `workspace/layer4_fresh_audit_2026-08-22/`.
- **2026-08-22 (e)** (Layer-6 fresh-data audit, user-directed): first live audit of the entry-point layer — `AgentRunner` façade + `cli/form_chat.py` (incl. the `--pipeline-file` path) + FastAPI `workflow_api` on live NCBI PRL/IL10/HAV data — **31 checks / 0 failures post-fix**. **Six defects fixed** (decision (u)): pipeline runs leaked tool artifacts to the global workspace root (`run_pipeline` never set the session context), `/v1/agent/run` misreported a crashed node as `success: true`, the API `task_id` echo did not identify the artifact session, `MrnaSequenceScoringWorkflow.run` dropped `progress_callback` (locked §19 stream sequence carried no progress events), no component ever emitted `step_start`/`step_done` (dead CLI handlers), and the CLI `--pipeline-file` branch still had the bare non-tty-crashing `input()`. Fresh HAV 5'UTR IRES scan: region 1-734, prob 0.835, confidence high (advisory CapGate — IRESfinder gated per (j)). Regressions `tests/test_layer6_fresh_audit_regressions.py` (15); suite 621. Evidence: `workspace/layer6_fresh_audit_2026-08-22/`.
- **2026-08-22 (f)** (Interface Lock Policy retired, user-directed): all INTERFACE LOCK comment blocks, the `docs/INTERFACE_LOCKS.md` policy document and every doc reference removed (decision (v)) — pure-deletion source diff (~1,250 lines), zero functional changes, suite 621 passed unchanged; behavioural contracts stay pinned by `WORKFLOWS.md` + the regression suite + the PA drivers.
