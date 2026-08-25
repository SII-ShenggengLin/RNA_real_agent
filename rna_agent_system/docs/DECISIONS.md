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

Falsified three times: P0 budget-matched control (Cliff's δ = 0.278 < 0.3 gate,
Wilcoxon p = 0.129, NO-GO, `p0_budget_matched_summary.json`); P3 guided vs
unguided at identical mechanics (δ = 0.222, p = 0.110, NO-GO,
`p3_guided_vs_unguided_summary.json`); Fig 5 b/c mechanism ablations (no test
survives BH-FDR, `fig5_summary.json`). Closed 2026-08-03; the framework itself
was later removed entirely — see (m).

### (b) Do not build junction (5'UTR–CDS) auto-repair

Fixing junction burial always costs global stability. Three corroborating
NO-GOs closed every route (post-hoc weight tuning: `p1_v2_stability_sweep_summary.json`;
junction-integrated optimizer: `junction_integrated_optimizer_summary.json`;
codon-shuffle generate-and-select: `junction_ddg_pilot_summary.json`). The
full-length ddG metric survives as report/profile-only — no score, issue or
repair path consumes it.

### (c) Do not revive cross-campaign memory strategies

E4 case-memory / experience injection (user-abandoned): budget cut 74.2% but
no learning-curve improvement and no design gain — all 3 memory slopes
positive-test p = 0.91, design-gain endpoint 0/4 significant
(`e4_full_summary.json`). Nothing justifies a retry with the same mechanism.

### (d) Cross-LLM backend matrix experiment — cancelled

User decision 2026-08-10: the only LLM touchpoints are advisory
(QualityAgent/SynthesisAgent review); DeepSeek's results extrapolate. Existing
fig6b data kept as historical fact (`fig6_backends.jsonl`, `MODEL_API_USAGE.md`).

### (e) Never ground screening/ranking claims on an unprofiled oracle

No oracle may support a screening, ranking or docking claim until it passed
anchor-set profiling for that capability (E1: screening 0/18 cells, ranking no
cell at ρ ≥ 0.6, docking 0/5 top-1, `e1_capability_summary_v2.json`; P2 EGARPS
calibration NO-GO, `p2_aptamer_calibration_summary.json`). Violations die
under re-audit — both legacy flagship claims did (survival 0/2,
`E2_SELF_AUDIT_FIG4_FIG7B.md`).

### (f) Budget-matching iron rule

Any best-of-pool or hypervolume comparison must use equal total
generated-and-evaluated candidates in both arms. The Fig-4 Type-II "main
effect" (p = 2.1e-4) collapsed to δ = 0.278 NS once budget-matched (P0).
Codified in [`MANUSCRIPT.md`](MANUSCRIPT.md) §2.

### (g) An LLM advisor (QualityAgent) never flips a successful run to failed

Quality review is advisory: LLM-call failure → `review_unavailable`
(zero-confidence pass) with the error retained in
`state["_quality_review_error"]`; LLM-chosen `abort` is recorded advice only.
Hard-failure retry is decided solely by `WorkflowResult.is_hard_failure`.
Governance fix 2026-08-10 after the DeepSeek-402 destructive-abort and a
hallucinated-abort incident.

### (h) Do not launch E5-S2 (18 targets) without a generation-method-layer change

With an unchanged generation layer, scaling from 5 to 18 targets is saturated
between arms — the paired McNemar is structurally p = 1.0. E6
(generation-layer navigation) was the sanctioned route
(`E5_REPORT_2026-08-09.md`).

### (i) Do not re-open the aptamer GenNav primary endpoint via symmetric budget rescale or panel expansion

Both escape routes closed (2026-08-13): a symmetric 48→64 rescale strengthens
the static baseline and erodes discordant repairs (structurally NO-GO); panel
expansion cannot reach p < 0.05 at 20 targets (full-panel two-sided McNemar
≈ 0.11–0.13); the asymmetric A-48/C-64 variant was rejected against the
budget-matching iron rule (f). Evidence: pre-registration-gate simulation on
the real E10 S2 cache + `e10_verdict_s2.json`.

### (j) Oracle-ontology boundary: learned outcome predictors gated; thermodynamic/algorithmic computation never gated

A tool is a managed oracle iff it is a learned predictor of a biological
outcome whose score a workflow consumes as candidate-quality evidence.
Thermodynamic/algorithmic computation (ViennaRNA, LinearFold, BLAST/Bowtie2,
CAI, GC/metrics) is `compute` — never gated; generators are never gated.
The E16+ profiling backlog was fixed at five pending oracles (GerNA-Bind,
RNASTOP, IRESfinder, CRGPT handle score, CRISOT off-target score); three have
since been profiled and flipped to enforce (see (l)), CRISOT-Score + CRGPT
remain pending on a registered data gap. Accepted consequence: a pending
oracle that fails profiling is blocked in production and affected workflow
components zero equally — verdicts are regenerated, never softened.
Evidence: `agent_core/tool_interface.py`; `tests/test_tool_ontology.py`;
`experiments/results/tool_inventory.json` (41 production tools).

### (k) Task-keyed gating + the microservice-internal oracle transparency boundary

DecisionGate reviews are keyed to the **calling workflow's** task type
(`task_context` contextvar), never the oracle's default alone — RhoFold from
tertiary design gates as unprofiled, not as an inherited E1-aptamer failure
(pinned in `tests/test_task_context.py`). **Audit boundary**: oracle hops
*inside* a microservice (e.g. GerNA-Bind folding via RhoFold internally) are
not ToolExecutor calls — neither gated nor platform-audited. Do not present
service-internal hops as gated; closing that gap is future platform work.

### (l) E16/E17/E18 verdicts — three oracles failed their declared-use gates; CRISOT-Score + CRGPT stay pending on a data gap

IRESfinder (screening AUROC 0.679/0.731/0.762 < 0.8 gate), GerNA-Bind
(screening AUROC 0.462 — chance level), RNASTOP (ranking ρ = 0.579 < 0.6) all
flipped pending → enforce (packaged SelfModel now 29 records). RNADesign-210 /
fig2 regeneration against the gated platform is the registered next step.
**Data gap**: no labeled anchor set exists for CRISOT-Score / CRGPT on disk —
do **not** improvise self-referential anchors (on-vs-off discrimination on
CRISOT's own example is not an efficacy measurement); real GUIDE-seq /
CIRCLE-style datasets are the prerequisite for E19/E20. Evidence:
`experiments/results/e16_e17_e18/`; anchor sets under
`data/benchmarks/external_anchors/`.

### (m) BMC framework removed from the system

Deleted 2026-08-18 (not just the narrative): CoordinatorAgent, the `bmc_*`
interface, input fields and trace plumbing. Both flagship workflows run the
plain generate → evaluate → score → ASF/Pareto-rank path; removal cost no
measured performance (P0 indistinguishable at equal budget). Historical
ablation evidence remains under `experiments/results/`.

### (n) Superseded/dead code is deleted, not archived in-tree

Code is the source of truth; once a strategy is superseded or falsified its
implementation is deleted (applied 2026-08-18: 12 dead tools, E1/E3-era
calibrated experiment machinery, all concluded E1–E15 drivers/analysis/plot
scripts). `experiments/results/` evidence JSONs are the durable audit record
and are never deleted. Re-derive deleted strategies from the results JSONs if
ever needed (distilled cores stay in-tree, e.g.
`agent_core/generation/gennav_aptamer.py`).

### (o) The shared ASF reference-point ranking layer is the single multi-objective ranking mechanism

Default for every workflow whose candidate pool carries ≥2 heterogeneous
objectives: full-length mRNA, aptamer, siRNA v1.3.0, sgRNA v1.3.0,
tertiary-structure v1.2.0, ASO v1.1.0 (Borda ranks demoted to diagnostics).
Fixed defects the 2026-08-20 audit found: per-candidate missing objectives now
impute at measured pool-worst (omission previously *rewarded* failure);
partial user `reference_point` flagged (`asf_ranking_note`); pool-wide
unmeasured dimensions drop for everyone equally; the ~100-line implementation
existed twice and was unified into
`workflows/multi_objective.py::apply_reference_point_ranking`. **Standing
boundary**: ASF values are pool-relative — never compare raw ASF distances
across pools/conditions. Single-objective / n=1 / domain-formula tasks (CDS
combined score, sequence scoring, IRES, secondary structure, small molecule)
intentionally remain unconverted. Evidence: `tests/test_multi_objective_utils.py`.

### (p) Ranking governance: ASF objectives are assembled from CapGate verdicts

`agent_core/calibrated/objective_assembly.py` (design doc
[`RANKING_GOVERNANCE.md`](RANKING_GOVERNANCE.md)) consumes DecisionGate
verdicts as a first-class ranking input: verified / transferred-verified →
keep; failed → demote to `scoring_annotation` pool-wide equally; pending →
keep + flag; unprofiled-enforce → keep + flag. Mode-independent (never reads
`RNADA_CAPGATE`); `GatedActionError` at measurement time is an expected-missing
annotation, never an evaluation failure. Fully-demoted workflows (packaged
SelfModel: `rna_aptamer_design`) return the `ranking_evidence_unavailable`
degrade — success=True, generation order, annotations intact, marker never in
`errors`. Deferred: continuous profile-derived ASF weights. Evidence:
`tests/test_ranking_governance.py`.

### (q) GenNav-λ production wiring + ASO converts to ASF (2026-08-22)

`mrna_cds_design` v1.2.0 opt-in `navigation=True` replaces the static λ grid
with the deterministic zero-LLM GenNav-λ (pure core
`agent_core/generation/gennav_mrna_lambda.py`; E6 λ-curve probe → band-gap-first
reinforcement, 16-raw budget → per-profile matrix delivery; constraint bands
are documented production defaults, **not** campaign-validated matrices — no
mRNA-side navigation-advantage claim beyond E6's registered result).
`aso_target_screening` v1.1.0 converts to the shared ASF ranking
(accessibility × binding; Borda → diagnostics). CDS runs attach the
CAI × MFE/nt Pareto annotation (ordering unchanged). All ASF workflows now
surface `pareto_frontier` extras uniformly. Evidence: `tests/test_gennav_mrna_core.py`,
`tests/test_mrna_cds_gennav.py`, `tests/test_aso_target_screening.py`.

### (r) Layer-3 pre-flight: an answering degraded health endpoint fails; only an unresponsive one proceeds anyway

A listening service answering `/health` with `status:"degraded"` or an HTTP
error is running-and-broken → pre-flight fails naming the service. A listening
but unresponsive endpoint (timeout/refused — the starved single-worker case)
keeps the 2026-07-22 wait-then-proceed-anyway behaviour. Do not "fix" a
degraded-service failure by restarting: a duplicate dies on "address already
in use". Evidence: `workspace/layer3_fresh_audit_2026-08-22/` (45 checks);
regressions in `tests/test_service_manager.py`.

### (s) Layer-4 boundaries: QualityAgent output stays outside ClaimGate; ranking-governance audit events are a registered event type

The `QualityReport` is an internal control signal, not a publication claim —
ClaimGate mounts only on SynthesisAgent multi-node synthesis; the report's only
execution-relevant channel (`parameter_overrides`) is already deterministically
constrained. Negative-space finding: the packaged SelfModel has no `scoring`
capability cells — a `scoring` claim on a profiled oracle rejects as "never
profiled"; conservative, not a defect — do not invent scoring grades without a
campaign. Mechanism fixes carried by the same audit: `ranking_objective_assembly`
registered in the `AuditEvent` Literal (events were silently dropped);
pipeline dangling-binding degradation; IRES generation-error surfacing;
retry-count semantics; int-enum override coercion. Evidence:
`workspace/layer4_fresh_audit_2026-08-22/`; `tests/test_layer4_fresh_audit_regressions.py`.

### (t) Layer-5 workspace isolation: session ids are untrusted single path components

Every `WorkspaceManager` method resolves session ids through
`_session_dir_path` (rejects empty/whitespace and `/ \ . ..` with `ValueError`;
`delete_session` returns `False`) — ids reach Layer 5 from the client-controlled
CLI `--session-id` / API `task_id`. Fixed the demonstrated defects:
`delete_session("")` rmtree of the whole sessions tree; `get_session_dir("../x")`
escaping `sessions/`; `list_files` creating directories on a pure read.
Accepted wart: `_workflow_result_history` unbounded per session (short-lived
CLI sessions). Evidence: `workspace/layer5_fresh_audit_2026-08-22/`;
`tests/test_layer5_fresh_audit_regressions.py`.

### (u) Layer-6 entry-point contracts: pipeline runs are session-scoped; the API never reports a crashed run as success; the delivered stream carries progress events

(1) `run_pipeline` scopes `_SESSION_ID_CTX` from `state["session_id"]` (both
pipeline callers pass one) — pipeline tool artifacts land under
`workspace/sessions/<sid>/`. (2) `/v1/agent/run` derives fallback success/errors
from the recorded `pipeline_result`. (3) The API `task_id` echo identifies the
artifact session directory. (4) `PipelineAgent` emits `step_start`/`step_done`
per node and the `stream_form` sequence carries workflow progress events.
(5) The CLI `--pipeline-file` branch follows the non-tty `input()` rule.
Evidence: `workspace/layer6_fresh_audit_2026-08-22/`;
`tests/test_layer6_fresh_audit_regressions.py`.

### (v) Interface Lock Policy retired

All lock annotations and `docs/INTERFACE_LOCKS.md` removed 2026-08-22
(~1,250 lines, zero functional changes). Behavioural contracts (pipeline
order, scoring formulas, `_state_writeback`, `stream_form` event sequence,
artifact keys) remain pinned by `WORKFLOWS.md`, the regression suite and the
PA drivers. Do not reintroduce lock annotations.

### (w) Oracle version stamps: profiling-time artifact versions on SelfModel records; drift is warned + audited, never blocking

All 11 managed-oracle descriptors declare `oracle_version`; packaged SelfModel
records carry the profiling-time stamp (`experiments/build_default_self_model.py`
pins literals, never copied from live specs). `CalibratedRuntime.configure`
warns + audits `oracle_version_mismatch` via `oracle_version_drift()` — nothing
blocks, no verdict moves. Registered follow-up: `/health`-reported artifact
identity (only `rnasmol_service` reports `checkpoint_path` today). Evidence:
`tests/test_oracle_version_stamps.py`.

### (x) Whole-platform E2E contracts: stream failures are events; RNAinverse takes pseudoknot-free targets only; CRGPT seeds are handles

1. `stream_form` upholds `run_form`'s graceful-failure contract — a workflow
   hard failure is a final `runner` event carrying the failed state; only
   worker-thread crashes raise.
2. The ViennaRNA inverse-fold endpoint takes pseudoknot-free dot-bracket only
   (`.` and `()`); Rfam `SS_cons` must be normalised **upstream** — do not
   teach the workflow to silently rewrite user structures.
3. CRGPT's seed is an sgRNA **handle** (≥40 nt scaffold), not a 20-nt spacer;
   a missing seed fails fast with a `ValueError` naming the input.
Leak checks must be window-based (new files during the audit), not
prefix-any. Evidence: `workspace/e2e_fresh_audit_2026-08-22/` (56 checks);
`tests/test_e2e_fresh_audit_regressions.py`.

### (y) Repo-wide simplification policy applied to runtime artifacts and docs (2026-08-22)

The (n) delete-don't-archive policy extends to generated artifacts and
documentation: superseded figure generations, archived experiment rounds,
leaked workspace scratch (141k files / 1.3 GB — the root leak class itself is
now closed for tests via the conftest scratch redirect + `RNADA_WORKSPACE_BASE`),
and stale service-run intermediates are deleted, not hoarded. The audit trail
(`workspace/audit/`, `workspace/sessions/`, `*_fresh_audit_*` evidence dirs,
`experiments/results/` verdict JSONs) is never deleted. The demo tool is
retired — 41 tools, all production. Docs keep current-state contracts and a
condensed era register instead of per-day narrative. Do not reintroduce demo /
echo tools or per-day narrative logs. Evidence: `docs/CHANGELOG.md` 2026-08-22 (i).

---

## Part 2 — Confirmed Positive Results (established, citable)

| # | Result | Evidence |
|---|--------|----------|
| 1 | E3 dual gating: FP claim rate 57.9% → 0% on the 20-task audit set, TP retention 112.5%, overreach 23 → 0 | `e3_runs_full_summary.json`; `RESULTS4_E3_MATERIALS.md` |
| 2 | E6 GenNav S2 primary endpoint GO: per-profile JCD-pass McNemar p = 1.86e-09 (n = 54), c_e2e_gene = 1.0; secondary endpoint failed and is disclosed | `e6_s2_verdict_aggregated.json` |
| 3 | Junction ddG metric valid: constraint obedience 216/216, ddG ≥ 0 in 216/216, LinearFold-vs-Vienna r = 0.9449 — report/profile-only use | `junction_ddg_pilot_summary.json` |
| 4 | Methodology (locks + budget matching + pre-registered pilots) caught three expensive errors pre-scale (P0/P1/P2/E4) | `MANUSCRIPT.md` §2 |
| 5 | Platform output validity (Fig 2): 210/210 tasks succeed across 11 workflows; designed CDS CAI median 0.745 (n = 20) vs WT 0.729 vs random 0.672 (WT > random p = 4.0e-07); inverse folding exact match 22/25 | `fig2_summary.json` |
| 6 | HER2-class zero-feasible-gear targets: registered open problem, not hidden | `e6_s2_verdict_aggregated.json` |
| 7 | E7 mRNA-oracle profiling GO: GEMORNA 5′UTR MRL verified on 3/3 anchor families (AUROC 0.990/1.000/1.000, ρ 0.926/0.920/0.835; n = 706) | `e7_mrna_oracle_profile_summary.json` |
| 8 | RNAsmol two-sided boundary + deployment-fidelity fix: in-distribution AUROC 0.9744/0.9828, decoy ranks 2/1601 and 7/265; OOD short aptamers show no demonstrated discrimination | `rnasmol_boundary_panel.json` |
| 9 | E8 aptamer GenNav: mechanical transfer confirmed, primary endpoint NOT met (McNemar p = 0.625) — scope finding, no advantage claim | `e8_verdict_s2.json` |
| 10 | E3-M mRNA-side gating replication GO: FP 38.9% → 8.3%, TP retention 100% | `e3_mrna_runs_full_adjudicated_summary.json` |
| 11 | E12: densified lattice + S1 priors — discordance 9:2, P = 0.0654 (one cell short); dual-gate boundary structural | `e12_verdict_s2.json` |
| 12 | E13 controlled replication: S2 bit-identical to E12 from cache — panel axis formally closed | `e13_verdict_s2.json` |
| 13 | **E14 aptamer GenNav PRIMARY ENDPOINT GO**: same-budget 48-raw, discordant 14:3, McNemar P = 0.0127, C e2e 0.50 vs A 0.00 — citable positive (levers: lattice densification, S1 priors, guaranteed-repair allocation) | `e14_verdict_s2.json`; `e14_runs_s2.jsonl` |
| 14 | E15 confirmatory replication: advantage regime-specific to delivery-scarce panels (b=14/c=6/P=0.1153); pooled E14+E15 28:9 (P=0.0026) — E14 the positive, E15 the boundary | `e15_verdict_s2.json` |

---

## Part 3 — One-Line Timeline

- **2026-04**: platform built — tool wrappers, microservices, first workflows.
- **2026-05 → 07**: 11 workflows completed; legacy Fig 2–7 campaign executed and data-frozen.
- **2026-08-03**: pilots P0–P3 falsify the coordination-gain and unprofiled-oracle narratives → calibrated-agent redesign.
- **2026-08-04 → 14**: calibrated campaign E1–E15 runs to completion (E3/E3-M gating GO, E6 GenNav GO, E7 MRL GO, E8–E13 aptamer GenNav arc, E14 primary GO, E15 boundary); this register created.
- **2026-08-18**: simplification pass — BMC removed, 12 dead tools purged, E1–E15 drivers deleted; oracle ontology + E16/E17/E18 profiling flip three oracles to enforce.
- **2026-08-19**: GenNav production wiring (aptamer `navigation` opt-in) + batch-B fresh-data re-verification (PA_025–PA_036, 12/12).
- **2026-08-20 → 21**: ASF ranking generalized + ranking governance (CapGate-verdict-driven objectives); paper_v5 figure programme; Layer-0/1/2 fresh-data audits.
- **2026-08-22**: Layer-3/4/5/6 fresh-data audits + whole-platform E2E audit (14 defects fixed across the stack); oracle version stamps; Interface Locks retired; GenNav-λ + ASO-ASF production wiring.
- **2026-08-22 (i)**: repo-wide simplification pass — workspace scratch isolation, demo tool retired, 4.3 GB → ~0.9 GB, docs condensed (this register compressed; DECISIONS (y)).
