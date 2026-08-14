# Change Log

> **Scope**: locked interface changes and major workflow introductions.
> **Last updated**: 2026-08-14

> **Layer-numbering note (2026-08-10)**: the architecture was renumbered from
> five layers (L0–L5, including "Layer 2.5") to **seven layers (L0–L6)** —
> old Layer 2.5 → L3 (service orchestration), old Layer 3 → L4 (planning &
> multi-agent execution), old Layer 4 → L5 (session/workspace), old Layer 5 →
> L6 (entry points). Entries dated before 2026-08-10 keep the numbering in
> force at the time they were written.

## 2026-08-14 — E13 controlled replication: panel-axis formally closed (NO-GO, bit-identical to E12)

**Campaign conclusion (no interface lock changes).** E13 (criteria book
`run_e13_gennav_aptamer.py`, pre-registered 259973c) was a controlled
replication: everything identical to E12 except the panel rule, which was
changed to a direct per-target constraint on the e2e driver (nav ≥ 1 ∧
a_fail ≥ 1 per target, ≤3 exceptions each, her2 ≤ 2; score 2·nav + a_fail).
User confirmed the panel-rule change is not a standards reduction (criteria
P<0.05 ∧ C e2e≥0.8 untouched).

- Pre-registration analysis (cached-data deterministic replay) found the
  E12 addendum-v2 rule ("per-target A-fail ≤ 1") infeasible (only 9/19
  targets qualify), and its proxy misdirected — A-fail is not the e2e
  driver; rate-based nav is (E12 e2e achievers all nav=2 incl. double-A-fail;
  nav≤1 targets e2e=0). E12's panel was already nav-maximal (21/21).
- S0/S1 mechanism gates GO; panel gate PASSED with the pre-registered
  projection — panel identical to E12's, target-for-target.
- S2: **NO-GO, bit-identical to E12** — McNemar b=9/c=2/P=0.0654, C e2e
  0.25/A e2e 0.00; all 36 JCD pairs equal to E12 (programmatic check).
  Whole campaign ran from cache in 133 s, zero new ODesign generations.
- **Conclusion: panel axis formally closed.** No panel rule moves the
  dual-gate endpoint under 48-raw; e2e ≥ 0.8 is a per-target reliability ×
  budget bound. Matrix (appendix J), protocol (appendix I), and panel
  (appendix L) axes all closed.
- Evidence: `e13_verdict_s{0,1,2}.json`, `e13_runs_s{0,1,2}.jsonl`,
  `e13_audit/`, `docs/FIX_2026-08-12_...` 附录 L.

---

## 2026-08-14 — E12 aptamer GenNav (lattice-densified + S1 priors): primary endpoint NO-GO, discordance near-significant

**Campaign conclusion (no interface lock changes).** E12 (criteria book
`run_e12_gennav_aptamer.py`, pre-registered 2026-08-13) ran the full
S0/S1/S2 discipline with matrix v3 (stems 7/9/12), a 17-length densified
C lattice, S1-measured laplace priors, and a pre-registered panel gate.

- S0 mechanism gate GO; S1 (19-candidate dense probe) GO with panel gate
  (rate-based NAV, addendum v1) PASSED — her2 targets 1/19 (BSA), e2e
  ceiling 12/12.
- S2 (12 targets, equal 48-raw cap): McNemar **b=9, c=2, P=0.0654**
  (E10: b=9/c=4/P=0.267 — c halved, P 4x improved, one c-cell short of
  significance), C e2e **0.25** vs criterion 0.8 (structural: 48-raw repair
  capacity cannot fully deliver 2-A-fail targets), A e2e 0.00. Mechanism
  block all-pass; NO budget violations.
- Addendum v2 recorded: the panel gate's aggregate-NAV constraint does not
  model per-target repair capacity — an e2e-reachable panel needs per-target
  A-fail <= 1, a design lesson for any future campaign. Criteria unchanged.
- Evidence: `e12_verdict_s{0,1,2}.json`, `e12_runs_s{0,1,2}.jsonl`,
  `e12_odesign_cache.jsonl`, `e12_audit/`, `docs/FIX_2026-08-12_...` 附录 J/K.

---

---

## 2026-08-13 — Dual-generalization campaign close-out: E3-M GO, E9/E10 NO-GO, escape routes closed by simulation

**Campaign conclusion (no interface lock changes).** The two core-innovation
generalization claims now stand as follows:

- **E3-M (mRNA-side calibrated-agency) — GO**: gated-vs-ungated audit on real
  full-length mRNA design-reporting tasks (20 tasks; 10 trusted-deterministic +
  10 untrusted-oracle) — FP 38.9% (7/18) → 8.3% (1/12), true-positive retention
  100%, gated overreach 0. Together with E3 (57.9% → 0%) the "both flagship
  task families" gating claim has double support. Artifacts:
  `experiments/e3_mrna/` (audit task set + builder), `run_e3_mrna_gated_vs_ungated.py`,
  `experiments/results/e3_mrna_runs_{pilot,full}_adjudicated*`.
- **E9/E10 (aptamer-side GenNav) — NO-GO, boundary localized**: re-anchored
  scarcity matrix (E9: b=6/c=8, P=0.79) then mechanized allocation (E10:
  b=9/c=4, P=0.267, mechanism block all-pass). The aptamer boundary is budget
  structure, not mechanism — c-reversal bands need 2+ reinforcement rounds at
  sub-20% pass rates, unreachable in 3 rounds at the 48-raw two-arm cap.
- **E11 pre-registration-gate simulation closed both escape routes**
  (`experiments/analysis/e11_feasibility_sim.py`, real E10 S2 cache, 5 A-lattice
  × 3 C-protocol grid): symmetric cap 48→64 is structurally NO-GO — any
  symmetric static-grid extension strengthens the rule arm (A-fail 14 → 5–8)
  and erodes the navigator's discordant repairs (b = 9 → 2–7, P ≥ 0.34);
  panel expansion is capped by the 20-target benchmark (19 usable; full-panel
  two-sided McNemar ≈ 0.11–0.13 — the handoff's "20-target P ≈ 0.07" was a
  one-sided value). The asymmetric A-48/C-64 variant (simulated P = 0.0215)
  was rejected by user decision against the budget-matching iron rule.
- **Paper sync**: `PAPER_DRAFT.md` GenNav paragraph now reports the aptamer
  boundary as structural with both escape routes closed; `PAPER_FACT_SHEET.md`
  gained E9/E10/E11 rows; `DECISIONS.md` Part 1 (i) + Part 2 row 10 + timeline;
  `FIX_2026-08-12_DUAL_GENERALIZATION.md` gained 附录 H.
- **Commit scope**: full campaign evidence base (E3-M runs/adjudications, E9/E10
  runs/verdicts/caches, drivers, feasibility sims, docs) — intermediates
  (`experiments/e3_mrna/{tmp,work,__pycache__}`) intentionally excluded.

---

## 2026-08-11 — RNAsmol scoring tool v0.3.0: preprocessing-fidelity fix (official test.py parity)

**Locked interface change (RNAsmol tool lock, v0.2.0 → v0.3.0).** The
request/response schema is unchanged — the bump records a behavior-level
preprocessing-fidelity fix in the RNAsmol microservice.

- **Bug**: `microservices/rnasmol_service/main.py` uppercased RNA sequences
  (destroying the case-sensitive modified-base vocab tokens 5-8) and built a
  *corrected* full molecular adjacency, while upstream
  `external_repos/RNAsmol/rnasmol/preprocessing.py` builds the adjacency with
  a quirk (only the first two directed edge pairs zipped, indices shifted -1)
  that the shipped checkpoints were actually trained with.
- **Fix**: the service now ports upstream preprocessing verbatim — sequence
  case is preserved, and the upstream adjacency / `get_top_k_matrix` slicing
  semantics are replicated bit-for-bit (do not "fix" them). No Pydantic
  field, endpoint, or inference-graph change.
- **Evidence**: post-fix the service reproduces the official upstream
  `test.py` reference metrics exactly — `robin_molperturbation` test AUROC
  0.9744, `pdb_molperturbation` test AUROC 0.9828; decoy case studies rank
  the true binder at 2/1601 (FMN_ribocil) and 7/265 (MALAT1_furamidine).
  Boundary panel: `experiments/results/rnasmol_boundary_panel.json`.
- **Sync surfaces**: `microservices/rnasmol_service/main.py` (header lock
  block + `ScoreRequest` / `ScoreResponse` / `score()` docstrings),
  `agent_core/tools.py` (`RNAsmolScoreInput` + wrapper lock comments),
  `agent_core/tool_specs.py` (spec `version="0.3.0"`), `docs/TOOLS.md` §5.1,
  and `docs/tools/score_rna_ligand_binding_with_rnasmol.md` (newly created —
  the lock header had listed it as a sync surface but the file never
  existed).

---

## 2026-08-10 — Documentation & repository cleanup: seven-layer renumbering, DECISIONS.md, experiment-register consolidation

**Documentation-side cleanup accompanying the §18 v1.1.0 / §19 v3.4.0 code
changes (same day).** No locked interface changed in this entry.

- **Code side** (context for the doc updates): `agent_core/planning/` deleted
  (`Planner` ABC, `AgentContext`, `LLMPlanner`, `build_planner`);
  `tool_runtime.py` deleted (`ToolResult` now defined in `tool_executor.py`);
  LOCK §18 → v1.1.0 (`MrnaSequenceScoringWorkflow` takes `CapabilityRegistry`);
  LOCK §19 → v3.4.0 (`AgentRunner` drops `planner`); QualityAgent governance
  (`review_unavailable` zero-confidence pass on LLM-call failure, advisory-only
  abort, `WorkflowResult.is_hard_failure` as the sole retry trigger — neither
  path can flip a successful run to failed); `MRNA_LANGCHAIN_TOOLS` renamed
  `GENERAL_LANGCHAIN_TOOLS`; truncate field-description fixes; dead `AgentState`
  fields (`_available_capabilities` / `_available_workflows` /
  `_workflow_param_schemas`) removed; tests renamed `test_*_layer3.py` →
  `test_*_layer4.py`, `test_llm_planner.py` / `test_tool_runtime.py` deleted.
  Test baseline: **668 passed**.
- **Data side**: deleted ~64 GB of workspace intermediate files, the
  `experiments/results/e1_poses/` intermediate structures (592 MB),
  microservice logs, and PA scratch inputs/logs. All final verdicts, summaries
  and reports are retained under `experiments/results/` (register:
  `docs/MANUSCRIPT.md` §3).
- **Docs side**: architecture renumbered to seven layers (L0–L6) across
  `AGENTS.md`, `docs/README.md`, `docs/ARCHITECTURE.md` (incl. a new §2.5.2 on
  how the calibrated-agent stack maps onto the seven layers),
  `docs/BMC_FRAMEWORK.md` (repositioned: bounded budget allocation +
  resampling + auditability; coordination-gain narrative retired),
  `docs/DEPLOYMENT.md`, `docs/INTERFACE_LOCKS.md` (current-state text only);
  `docs/MANUSCRIPT.md` condensed to the pilot-first protocol + two-tier data
  availability register (legacy Fig 2–7 + E1–E6); E4/E5/E6 outcomes added to
  `docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §4/milestones; new
  `docs/DECISIONS.md` (do-not-repeat register, confirmed positives, timeline);
  the cross-LLM backend matrix extension recorded as **cancelled** (user
  decision 2026-08-10). `docs/change_logs/` was reviewed and **retained**: the
  two 2026-08-04 junction-patch logs carry implementation detail (C++ CLI
  contract, internal energy/sign convention, per-file patch-marker map,
  byte-level regression evidence) beyond the 2026-08-04 entry above, and the
  tool doc links to them.

---

## 2026-08-10 — MrnaSequenceScoringWorkflow §18 v1.1.0: constructor unified to CapabilityRegistry

**Locked interface change (INTERFACE_LOCKS §18, v1.0.0 → v1.1.0).**
`MrnaSequenceScoringWorkflow.__init__` now takes a `CapabilityRegistry` like
every other workflow (previously a raw `ToolExecutor` — the lone inconsistency
in the Layer-2 constructor surface). The registry's `executor` is still used
internally for tool dispatch and `ToolCallRecord` trace attachment; evaluation
behavior is unchanged. `AgentRunner.workflow_registry` now passes
`self.capability_registry`; the standalone `run_mrna_sequence_scoring()`
convenience function takes `capability_registry=` instead of the old
`registry=`/`executor=` kwargs. Callers updated: `agent_core/runner.py`,
`agent_core/workflow_baseline_eval.py`, `tests/test_mrna_workflow.py`,
`tests/test_workflow_observability.py`,
`tests/test_mrna_sequence_scoring_layer3.py`, `tests/test_service_manager.py`.

---

## 2026-08-10 — AgentRunner §19 v3.4.0: planner parameter and planning/ package removed

**Locked interface change (INTERFACE_LOCKS §19, v3.3.0 → v3.4.0).** The
`AgentRunner` constructor no longer takes `planner`; the entire
`agent_core/planning/` package (`Planner` ABC, `AgentContext`, `LLMPlanner`,
`build_planner`) is deleted. The production path never invoked the planner —
routing has been explicit-only since v3.0.0 — so the parameter only stored an
unused attribute, while forcing every caller (CLI, FastAPI, tests) to build an
LLM client it never used. LLM clients for `QualityAgent` / `SynthesisAgent`
are constructed directly from `agent_core/llm_config.py`
(`get_llm_for_provider` / `get_deepseek_llm`); no QualityAgent prompt feature
depended on the planner. Also removed the runner's dead planner-context
attributes `_available_capabilities` / `_available_workflows`, the CLI
`flash_planner` construction in `cli/form_chat.py`, and the
`agent_core/planning/base.py` lines from nine workflow INTERFACE LOCK
comments. Callers updated: `agent_core/runner.py`, `cli/form_chat.py`,
`workflow_api/app.py`, `tests/test_runner_form.py`,
`tests/test_form_schema_builder.py`,
`tests/test_mrna_sequence_scoring_layer3.py`,
`tests/test_full_length_mrna_e2e_live.py` (LLMPlanner live-test class
removed), `tests/test_rna_small_molecule_interaction.py` (planner-prompt test
removed), `tests/test_llm_planner.py` (deleted with the package).
`experiments/run_quality_ablation.py` and
`experiments/run_llm_backend_comparison.py` still reference the old API and
are frozen experiment drivers — update them if they are ever rerun.

Related governance fixes landed in the same pass (no lock impact):
`QualityAgent` LLM-call failures now mark the review `review_unavailable`
(zero-confidence pass, `state["_quality_review_error"]` retained for audit)
instead of returning a destructive `abort`, and a `SpecialistAgent` abort
report is advisory-only — neither can flip a successful run to failed
(DeepSeek-402 and hallucinated-abort incidents, 2026-07).

---

## 2026-08-05 — FullLengthMrnaDesignWorkflow §14 v2.8.0: junction metric upgraded to full-length ddG; BMC junction auto-repair stripped

**Locked interface change (INTERFACE_LOCKS §14, v2.7.0 → v2.8.0).** The legacy
junction metric (isolated 40-nt fragment fold + `aug_buried`/`kozak_buried`
booleans) was falsified by three pre-registered experiments — P1 v2, P2
(`junction_integrated_optimizer_summary.json`), and the Phase 0 ddG pilot
(`experiments/results/junction_ddg_pilot_summary.json`, 2026-08-05: fragment
burial is uncorrelated, even anti-correlated, with full-length ddG; Gate-2
Route-C NO-GO → fall back to plan A, E4 executor = existing workflow).

- **JunctionEvaluator upgrade**: new full-length constrained-fold ddG report
  metric at the 5'UTR-CDS junction — `ddG_open = MFE_constrained −
  MFE_unconstrained` on the full construct (utr5+cds+utr3) via LinearFold,
  constraint = '?' full-length + '.' inside the window. W1 (narrow, CDS start
  −6..+9, 15 nt) and W2 (wide, 5'UTR tail 60 nt + CDS head 30 nt, clipped to
  the actual UTR length). New `metrics_bundle` fields
  `junction_5utr_cds_ddg_open_w1/w2` + `junction_5utr_cds_ddg_{w1,w2}_{start,end}`;
  unconstrained MFE reuses the workflow's full fold (LinearFold backend only);
  fold failure → `None`, never raises. ddG is **report/profile only** — no
  score, issue, or repair path consumes it. Fragment-fold junction metrics
  (`junction_*_{mfe,mfe_per_nt,gc_diff,...}`) are unchanged.
- **Removed**: `junction_5utr_cds_aug_*` / `junction_5utr_cds_kozak_*`
  evaluator output fields; `_collect_boolean_issues()` and the
  `boolean_issues` parameter of `ReferencePointCoordinator.diagnose()`;
  `JUNCTION_5UTR_CDS_AUG_BURIED` / `JUNCTION_5UTR_CDS_KOZAK_BURIED` issue
  types; the `_regenerate_modules()` `shuffle_cds_junction_codons` branch
  (plus `shuffled` source label, `bmc_shuffle_end` metadata, and the method's
  `issues` parameter); `shuffle_cds_junction_codons` from
  `required_capabilities`. The tool itself stays locked (v0.1.0) and available
  for explicit user invocation. `JunctionEvaluator._check_translation_start()`
  is retained for experiment-script reproducibility.
- Tests: removed 2 burial-path tests, added 9 ddG tests (constraint-string
  construction, window clipping, ddG ≥ 0, workflow-fold reuse vs self-fold,
  fault tolerance, no-burial-keys regression); made two mock registries
  collision-proof (per-call unique sequence tags). pytest 594 passed,
  1 skipped.

---

## 2026-08-04 — Junction-aware LinearDesign: C++ patch, new endpoint/tool v0.1.0, P2 acceptance NO-GO

**Design-time junction integration (REDESIGN §3 E4 route, W10-11).** Local
JUNCTION-PATCH to `external_repos/LinearDesign/src` (4 files, 32
`// JUNCTION-PATCH (2026-08)` markers; argc ∈ {4,5,7,8}, legacy argc == 4
byte-for-byte regressed): fixed UTR flanks join the global CKY fold as
pseudo-codons and newly formed junction-window pairs are penalized by w_jun
inside the design objective (forward 10 + backtrace 9 hook points +
special-hairpin precompute). New endpoint `POST /generate/cds_junction_aware`
(port 8014) and new locked tool
`design_mrna_cds_junction_aware_with_lineardesign` **v0.1.0**
(INTERFACE_LOCKS §21; `mfe` = CKY objective value vs `mfe_thermo` =
thermodynamic MFE; `junction_window_pair_count` with C++-identical window
coordinates). All additive: no locked interface modified. Tests +23; pytest
587 passed, 1 skipped. Change logs:
`docs/change_logs/2026-08-04_lineardesign_junction_patch.md`,
`docs/change_logs/2026-08-04_design_mrna_cds_junction_aware_tool_v0.1.0.md`.

**P2 pre-registered acceptance (72 cells = 6 targets × 3 reps × w_jun ∈
{0, 0.5, 1, 2}): NO-GO** (`experiments/junction_integrated_optimizer_eval.py`,
summary `experiments/results/junction_integrated_optimizer_summary.json`). No
weight passed all three criteria (hard AUG/Kozak repair ≤ 2/7 vs ≥ 2/3
required; median stability cost 0.015–0.031/nt vs ≤ 0.011; CAI criterion
passed trivially). One-line mechanism: the penalty clears window pairs in the
optimizer's global fold (43 → 0) but the JunctionEvaluator metric folds the
isolated 40-nt junction fragment, which still self-hairpins — penalty/metric
coordinate mismatch. The tool stays a registered capability, **not wired into
any workflow**.

---

## 2026-08-04 — Redesign W5–9 (start): calibrated Layer-3 stack added (additive, no locked-interface changes)

New package `agent_core/calibrated/` implementing `REDESIGN_2026-08-03_CALIBRATED_AGENT.md`
§2.2: `SelfModel` (empirical capability map, transfer with decayed confidence),
`CaseMemory` (campaign archive + similarity retrieval + SelfModel persistence),
`AuditTrail` (append-only JSONL), `CapabilityProfiler` (CASF grading via
`e1_driver` subprocess / `deterministic` backends), `DecisionGate`,
`ClaimGate` (scope-ladder downgrades), `ExperimentPlanner` (LLM dependency
declaration + deterministic budgeting), `CalibratedCampaignRunner` (§2.3
seven-step flow, E3 treatment arm). All components additive; the legacy agent
stack stays untouched as the E3 control arm. Architecture doc gains §2.4.1.
Tests: +56 (tests/test_calibrated_*.py, test_self_model/case_memory/
profiling_metrics/profiler/decision_gate/claim_gate/experiment_planner/
campaign_runner); pytest 563 passed, 1 skipped.

**E3 scaffolding + pilot (REDESIGN §3 E3)**

- Task set: `experiments/e3/audit_tasks.json` (20 tasks = 10 trusted-deterministic
  metric optimization + 10 untrusted-oracle aptamer ranking/screening over E1 v2
  anchor subsets; assertion-first generator `experiments/e3/build_audit_tasks.py`).
- Driver `experiments/run_e3_gated_vs_ungated.py` (pre-registration in docstring):
  ungated = free LLM plan/report; gated = same two LLM calls inside
  `CalibratedCampaignRunner` with SelfModel pre-loaded from
  `e1_capability_summary_v2.json` (all 18 oracle×target cells failed).
  Adjudication `experiments/analysis/e3_adjudicate.py` (deterministic ground
  truth + blinding for optional LLM review); summary `e3_analysis.py`.
- Pilot (6 tasks x 2 arms): `experiments/results/e3_runs_pilot.jsonl`,
  `_adjudicated.jsonl`, `_summary.json`. Ungated FP rate 0.667 (4 FP / 6 claims,
  overreach 5); gated 0.75 (3 FP / 1 TP / 1 suppressed / 1 borderline,
  overreach 0 — DecisionGate hard guarantee holds). Task set discriminates
  (control 3 FP on untrusted_oracle). Gated-arm FPs traced to: LLM length
  sloppiness on metric tasks (58/61 nt vs 60) and a fallback to an undeclared
  deterministic proxy (GC content) when the structural oracle was blocked —
  both prompt/protocol issues logged for the full-matrix design, not gate
  failures. LLM usage recorded in MODEL_API_USAGE.md (24 calls, temp 0).

**E3 pre-registration amendment v1.1 (post-pilot, user-approved direction)**

- Uniform "no claim without a verified basis" rule (one principle, two legs):
  (a) comparative claims must declare a capability-checked basis; deterministic
  metrics used as affinity proxies are profiled into the gated SelfModel via
  the same CapabilityProfiler protocol (profiler gains a `purine_content`
  scorer); ClaimGate rejects undeclared-basis ranking/screening claims
  (`COMPARATIVE_CLAIM_TYPES`). (b) Execution verification: the gated arm
  recomputes deterministic artifacts before writing and abstains on failure.
  Driver docstring amended accordingly; +1 test (pytest 564 passed, 1 skipped).

---

## 2026-08-04 — Redesign W1–2: P1 v2 NO-GO (local stability proxy), E1 Pilot Complete (experiments/ only)

**No agent_core changes.** New drivers/analysis under `experiments/`, anchor
data under `data/benchmarks/`, doc updates (`REDESIGN_2026-08-03_CALIBRATED_AGENT.md`
v2 approved by user; CONTRIBUTING.md gains the simplicity-first rule §0).
pytest baseline unchanged (507 passed, 1 skipped).

**Design decisions (user, 2026-08-04)**

- REDESIGN doc v2 approved: profiling/gating sunk into an empirical SelfModel
  core (DecisionGate + ClaimGate, mechanisms A+B+C); Fig-4 kept as worked
  example (no self-retraction rhetoric); E4 gains a budget-matched
  verified-metric endpoint; Nat Methods direct submission; no early
  pre-registration.
- Simplicity-first rule: no backward-compat shims; superseded code/docs are
  deleted (CONTRIBUTING.md §0; locked interfaces and experimental baselines
  excepted).
- E4 executor route (W3-4 wrap-up): design-time integration — the junction
  term goes into the LinearDesign generation objective (logically consistent
  with the P1 v2 NO-GO); the E4 dependency on P1 v2 is dropped, integration
  lands in W10-11 before the E4 full matrix (REDESIGN §3 E4 + §5 updated).

**P1 v2 (junction optimizer stability weight): NO-GO**

- 72 cells (6 targets x 3 reps x w_stab in {0.1, 0.25, 0.5, 1.0}) +
  w=0 regression 18/18 identical to v1. Judgment:
  `experiments/results/p1_v2_stability_sweep_summary.json`.
- Mechanism: the knob moves the search (sequences diverge) but the extended
  terminal-window proxy moves the WRONG way (dominated by the junction term
  in the same windows) and the true full-construct cost is flat — global
  stability loss lives in long-range rearrangements invisible to 160-nt
  windows. Post-hoc local proxies cannot control global stability; the
  trade-off belongs inside the generative tool at design time.

**E1 oracle capability profiling pilot (3 targets x 3 oracles): complete, expected-direction**

- Anchor set: `data/benchmarks/external_anchors/aptamers/e1_anchor_set.json`
  (29 entries; Thrombin 10 / VEGF 11 / PDGF-BB 8; assertion-checked
  generator `experiments/curate_e1_anchor_set.py`; literature sequences
  re-verified against Europe PMC full texts; PDGF-08 stored as printed 58-nt).
- Judgment: `experiments/results/e1_capability_summary.json`.
  - Screening: NO oracle-target passes AUROC > 0.8 (best: rhofold pLDDT on
    PDGF-BB at exactly 0.8 with CI 0.33-1.0; EGARPS on Thrombin 0.286).
  - Ranking: no cell rho >= 0.6 (best rhofold/PDGF-BB 0.564; EGARPS/Thrombin
    drops to 0.143 at n=6 vs P2's 0.40 at n=4).
  - Docking (first test, Thrombin anchors 4DII/4I7Y/3DD2): EGARPS native
    top-1 in 0/3 anchors — TBA native pose ranks LAST (21/21), Toggle-25t
    19/21, HD22-27mer 4/18. Native-vs-decoy chemistry is identical within
    each anchor (decoys derive from the same cleaned pose), so the
    comparison is internally valid.
  - Pre-registered conclusion: "deployed oracles lack screening power for
    RNA-protein aptamers" stands as an empirical finding; EGARPS docking
    power does NOT transfer to these RNA-protein aptamer complexes either.

**New pitfall (item 15)**

- EGARPS pipeline skips pdbfixer when `<basename>_fix.pdb` exists — re-scoring
  a MODIFIED pdb under the same basename silently reuses the stale fixed
  structure. Every pose must be scored in its own isolated directory with a
  unique basename (fixed in `experiments/run_e1_capability_profiling.py`,
  documented in its docstring).

**W3–4 in progress (same day): anchor infrastructure + E2 self-audit**

- Anchor infrastructure consolidated: `docs/ANCHORS.md` — directory spec for
  `data/benchmarks/external_anchors/`, anchor-set JSON schema (v2 superset),
  and the assertion-first curation pattern templated on
  `experiments/curate_e1_anchor_set{,_v2}.py` (the v2 assertion pattern caught
  three real transcription errors: AptAF42 length misreading, tNSP9/10
  parent-row offset, Seq15_12_35 literal typo). Indexed in the root AGENTS.md.
- E2 self-audit written: `experiments/results/E2_SELF_AUDIT_FIG4_FIG7B.md` —
  the Fig-4 main effect and the Fig-7B pegaptanib comparison re-audited
  through the capability-profiling protocol (ungated claim vs profile evidence
  vs budget-matched control vs gated verdict). Both claims FAIL the audit
  (survival 0/2 < 70% pre-registered threshold -> E2 audit story holds);
  gated re-statements drafted for the Results-3 worked example.
- E1 extension GPU profiling COMPLETE (anchor set v2, 66 entries, 6 Part-A
  targets + 5 docking anchors; 37/37 Part A + 42 Part-B poses, zero LLM).
  Merged pilot+extension judgment: `experiments/results/e1_capability_summary_v2.json`
  (66 Part A, 102 Part-B poses, via `experiments/analysis/e1_extension_analysis.py`).
  All pre-registered directions hold on the extended set:
  - Screening: 0/18 oracle-target cells pass AUROC > 0.8 (sensitivity grid:
    6/18 pass AUROC > 0.6, 0/18 pass > 0.9) — "no oracle shows reliable
    screening power for RNA-protein aptamers across targets" stands.
  - Ranking: no cell rho >= 0.6 on the ranking-eligible same-assay subsets.
  - Docking (5 anchors: pilot 3 Thrombin + 1HVU HIV-1 RT + 8EPK Factor IXa):
    EGARPS native top-1 = 0/5 (1HVU native rank 10/21; 8EPK 10/21; Thrombin
    0/3 as in the pilot) -> docking power does NOT transfer.

---

## 2026-08-03 — Pilot Pivot: Budget Confound Found, P0/P2 NO-GO, P1 Optimizer GO (experiments/ only)

**No agent_core changes.** All work is new drivers/analysis under `experiments/`
plus benchmark data; pytest baseline unchanged (507 passed, 1 skipped).

**Root-cause findings (recorded in driver docstrings, do not re-litigate)**

- R1 budget confound: every Fig-4 BMC round regenerates candidates, doubling
  the evaluated pool (serial=8 → bmc_x1=16); the Type-II "main effect" was
  not budget-matched.
- R2 mechanism asymmetry: Type-I coordination can only tune λ / shuffle 24
  junction codons / pick UTR presets — no sequence-space exploration, so the
  absent Fig-3 main effect is structural.
- R3: Fig-5b/c all-negative ⇒ the gain carrier is "more generations", not
  "better diagnosis".
- R4: scoring chain uncalibrated (pegaptanib ~5e-7 on the in-house EGARPS
  chain) — confirmed by P2.

**Pilot results (pre-registered go/no-go, `MANUSCRIPT.md` §13.1)**

- P0 budget-matched control (`run_budget_matched_control.py`,
  `analysis/p0_go_no_go.py`): 12/12 runs; bmc_x1 vs serial_ext16 egarps
  best-of-pool Cliff's δ = 0.278 < 0.3 → **NO-GO** (budget explains most of
  the Fig-4 effect; residual coordination effect small, 9/12 wins, NS).
  Summary: `results/p0_budget_matched_summary.json`.
- P1 junction-aware codon optimizer (`junction_aware_codon_optimizer.py`):
  18/18 → **GO**; fixes 13/14 baseline-buried junctions, CAI median +0.0025,
  at the cost of global stability (v2 needs a tunable stability term).
  Summary: `results/p1_junction_optimizer_summary.json`.
- P2 aptamer calibration (`run_aptamer_calibration.py`,
  `analysis/p2_go_no_go.py`): 15/15 scored; thrombin series Spearman ρ = 0.40
  (< 0.6) and binder-vs-negative AUROC = 0.356 (< 0.8, below chance;
  random/scrambled negatives outscore most real binders) → **NO-GO**.
  Manuscript consequence: per-target calibration gating; optimization claims
  restricted to relative same-target comparisons; the calibration result is
  reported as a method boundary finding. Note P0's NO-GO rests on the egarps
  metric that P2 shows is uncalibrated — both point at objective
  trustworthiness as the primary issue.
  Summary: `results/p2_aptamer_calibration_summary.json`.
- P3 guided-vs-unguided (`run_p3_guided_vs_unguided.py`, `analysis/p3_go_no_go.py`):
  unguided arm replicates bmc_x1's two-pass mechanics exactly (same initial
  batch, forced seeds+1 second batch, pool=16) with the diagnosis replaced
  by a fixed resampling instruction — isolating the diagnosis content itself
  (in-process workflow drive, coordinator instance patched; zero agent_core
  changes, zero LLM). 12/12 runs; guided bmc_x1 vs unguided_2pass Cliff's
  δ = 0.222 < 0.3 → **NO-GO** (guided 9/12 wins, NS; caveat: 2 of the 3
  guided losses are the BSA pre-EGARPS-fix vintage cells). Diagnosis content
  shows no value beyond resampling at pilot scale; BMC's defensible value
  reduces to adaptive budget allocation (1/12 guided cells converged at
  pool 8, halving budget at equal quality) + resampling mechanics.
  Summary: `results/p3_guided_vs_unguided_summary.json`.

**New benchmark data**

- `data/benchmarks/external_anchors/aptamers/calibration_set.json` (15
  entries: thrombin 4-point Kd gradient, VEGF/PDGF-BB/IgE/SARS-N binders,
  5 fixed-seed negatives; sequences verified against RCSB 4I7Y/3DD2) +
  `proteins/{pdgfbb,ige_fc}.fa` + SOURCES.md additions.

**New pitfalls (HANDOFF_2026-08-03_PIVOT.md §3, items 11–14)**

- Session-artifact `metadata.cds_sequence`/`protein_sequence` may be
  `...(truncated)`; full CDS must be sliced from `best_candidate.sequence`.
- CAI weight tables are keyed by RNA codons (AUG) — T→U before lookup.
- Any best-of-pool / hypervolume arm comparison must match total
  generated-and-evaluated candidates (fixed into §13.1).

---

## 2026-07-30 — Fig-4kav EGARPS Chain Fix + Campaign Pins (comments only)

**Driver fix (behavioral, experiment scripts only)**

- `experiments/run_case_study_pipelines.py` (lossless resume): resumed-skip
  node paths previously returned bare stubs, so sweep-triggered
  `case_summary.json` rebuilds blanked `elapsed_seconds` (timeline collapsed
  to 0) and dropped the Case-B pegaptanib_anchor scoring outputs. Fixed via
  `latest_node_record()` (prior fields restored from nodes.jsonl) + the
  anchor node persisting `outputs` into nodes.jsonl at write time; a NOTE
  also records that the direct anchor chain does not auto-start services
  (ensure via `service_manager.ensure_services_ready` first). Verified: all
  3 case summaries rebuilt losslessly (A 5110 s / B 2796 s / C 73 s).
- `experiments/run_known_aptamer_validation.py::_proteinx_cif_to_pdb`: the
  known-aptamer scoring chain now converts the ProteinX mmCIF to a `.pdb`
  copy via gemmi before EGARPS/interface analysis, and sanitizes the output
  basename (`protein`/`rna` substrings stripped). Fixes three chained
  failures that made all `known_aptamer_score`/`vegf_case` blocks fail:
  (a) EGARPS's CIF reader rejects Protenix OP3 atoms
  (`OP3 not in STD_ATOM_NAMES`); (b) EGARPS `ins.py` derives cache paths via
  `pdb.replace('.pdb', ...)` — a no-op for `.cif` inputs — and overwrote the
  original mmCIFs with its pickle caches (verified: 2 of 5178 ProteinX
  outputs were pickles, exactly the two EGARPS had touched); (c) EGARPS
  `feature_residue.py` chain typing (`re.search('protein', key)`) hijacked
  RNA chains into the protein DSSP path whenever the basename contained
  'protein' (e.g. 'proteinx'), producing 3-wide vs 7-wide ss rows and the
  `np.row_stack` crash in `dataload._install_external_feat`.
- `experiments/run_bmc_mechanism_ablations.py`: Ferritin (panels b/c) and
  SARS-CoV-2_Nucleocapsid (panel e_type2, out-of-range explicit hotspots
  A/44–48 vs 6M3M) are skipped as confirmed ODesign boundaries
  (`FERRITIN_BOUNDARY_PANELS`, `NUCLEOCAPSID_E2_BOUNDARY`, both NOTE-dated).

**Warning comments pinned (no behavior change)**

- `external_repos/EGARPS/scripts/ins.py::get_input_data` — input-overwrite
  trap for non-`.pdb` filenames.
- `external_repos/EGARPS/scripts/feature_residue.py::get_ss_feat_for_dir` +
  `get_universal_feat_for_dir` — `re.search('protein', k)` basename trap.
- `agent_core/tools.py::score_rna_protein_complex_with_egarps` docstring —
  real-`.pdb`-only input contract + gemmi-conversion pointer.
- `microservices/egarps_service/main.py::_run_egarps` and
  `microservices/proteinx_service/main.py::ProteinXPredictResponse` —
  `pdb_filepath` is Protenix's raw mmCIF (OP3), not a PDB.
- `experiments/run_llm_backend_comparison.py::BACKENDS` — 2026-07-27
  incident: the env `ANTHROPIC_BASE_URL` is a Kimi relay serving no claude
  models; the 8 claude 404 records are endpoint misconfig, not backend data.
- `experiments/run_quality_ablation.py::_turn_time_limit` — the SIGALRM
  turn timeout is not a hard kill: broad `except Exception` handlers can
  absorb it (observed on fig6b PA_020, ~146 min under a 5400 s cap while
  still progressing); do not kill long turns that show forward progress.
- `experiments/analysis/failure_taxonomy.py` — fig3 `rep` vs fig4 `seed_idx`
  dedupe-key fallback note.

**New analysis/plot scripts**

- `experiments/analysis/summarize_fig5.py` (fig5_summary.json; panels b–e,
  utopian-of-pool fixed ASF, one BH-FDR family) and
  `experiments/analysis/failure_taxonomy.py` (failure_taxonomy.json;
  events vs final-state views, identity-confirmed boundary classes).
- `experiments/plots/plot_fig{3,4,5,6}.py` (style per plot_fig2.py; all
  outputs visually inspected).

---

## 2026-07-27 — Campaign Lessons Pinned as Code Comments

**Boundary documentation (comments only, no behavior change)**

- `agent_core/agents/specialist_agent.py` (abort branch): an `abort`
  QualityReport fails the whole run even when the workflow succeeded —
  documented with the two campaign incidents (DeepSeek 402 infra failure;
  hallucinated abort on Myoglobin) and the `state["_quality_review_error"]`
  marker that distinguishes infra failure from quality abort.
- `agent_core/agents/quality_agent.py` (LLM-failure fallback): same pointer —
  the fallback fires on ANY exception including billing/network, and the abort
  is applied destructively downstream.
- `agent_core/workflows/rna_aptamer_design.py`:
  - `_extract_protein_sequence_from_structure`: sequence always comes from the
    PDB's FIRST chain; on 1HAO that is the DNA aptamer chain, so ProteinX is
    skipped and all designed Thrombin candidates got `iptm_component = 0`
    (silent). Cross-reference to the known-aptamer validation driver, which
    extracts from the target chain instead.
  - ODesign zero-sequence path: documented as a target-side boundary
    (Ferritin/1FHA: 12/12 matrix cells + 3 retries) — do not "fix" by retrying.
- `experiments/run_bmc_type1_ablation.py` / `run_bmc_type2_ablation.py`
  docstrings: ops notes — `--timeout 9000` for HER2/Spike-class proteins;
  Ferritin boundary; MBP governance abort; Myoglobin hallucinated abort.

Previously fixed sites verified still carrying their NOTE/CAVEAT comments:
`cli/form_chat.py` (`_bmc_trace` fallback 2026-07-20),
`agent_core/services/service_manager.py` (`health_timeout` 30 s 2026-07-19 +
`_port_listening` busy rule 2026-07-22), `agent_core/workflows/multi_objective.py`
(utopian ASF=0 caveat), `agent_core/tools.py` (LinearDesign ≥7 kb OOM),
`agent_core/workflows/coordinator.py` (`APTAMER_FEEDBACK_MODE`).

---

## 2026-07-22 — Busy-Service Health Starvation Fix

**Root-cause fix**

- **Busy single-worker services were still double-started**
  (`agent_core/services/service_manager.py` `ensure_services_ready`): the
  2026-07-19 `health_timeout` 2 s → 30 s fix covered short busy spells, but
  EGARPS crunching back-to-back scores for one shard starves `/health` for
  minutes — the other shard's pre-flight then declared it down and started a
  duplicate that died on "address already in use", failing whole ~20-min runs
  in waves (fig4 `cli_failure` clusters). New rule: after a failed health
  check, `_port_listening()` distinguishes busy (port held) from down (port
  free); busy services are waited out within the startup budget and then
  simply proceeded past (their real HTTP calls carry their own long
  timeouts), and are never restarted. Down services follow the original
  start path unchanged. Tests +2 (`tests/test_service_manager.py`, 33/33);
  signature and the 30 s `health_timeout` convention unchanged.

---

## 2026-07-20 — BMC Trace Artifact Fix + Fig-5b Feedback Toggle

**Root-cause fix**

- **`_bmc_trace` never reached CLI artifacts** (`cli/form_chat.py`
  `_save_workflow_results`): the dump read `state["_bmc_trace"]`, a key no code
  path ever sets (`AgentRunner._prepare_state_form` only *pops* it for
  cross-turn hygiene), so the audit field was always `[]` even though each BMC
  workflow's `bmc_finalize` wrote the real trace to
  `result._state_writeback["_bmc_trace"]` (INTERFACE_LOCKS §14/§20). The
  artifact now falls back to the writeback value; additive fallback, no locked
  key/signature changed, 505 tests pass. **Experiment impact**: fig3/fig4
  shard JSONL records written before this fix carry `bmc_trace=None` —
  per-run round execution is recoverable post-hoc from session candidate
  metadata (`bmc_regenerated` / `bmc_round`), and the Fig-3e trace panel gets
  one dedicated Spike re-run after the shards finish.

**Additive experiment toggle (Fig 5b)**

- **`APTAMER_FEEDBACK_MODE={source_aware,pool_average}`** (env, default
  `source_aware` = byte-identical behavior): `AptamerCoordinator
  .broadcast_feedback()` gained an optional `pool_metrics` kwarg and
  `RnaAptamerDesignWorkflow` a private `_pool_mean_metrics()` helper; in
  `pool_average` mode per-module feedback derives from candidate-pool mean
  metrics instead of worst-violation source metrics. See INTERFACE_LOCKS.md
  §15 additive note and BMC_FRAMEWORK.md §5. Tests +2 (`tests/
  test_rna_aptamer_design.py`).

---

## 2026-07-19 — Experiment-Hardening Fixes from the Fig 2–4 Batch Runs

Issues found while running the manuscript experiments at scale (~1 400 runs);
each fix carries an inline NOTE/CAVEAT at the code site so it is not reverted.

**Root-cause fixes**

- **Service health-check timeout 2 s → 30 s** (`agent_core/services/service_manager.py`
  `ensure_services_ready(health_timeout=…)`): a busy single-worker service
  (EGARPS mid-scoring) can take seconds to answer `/health`; the 2 s probe
  falsely declared it down, triggering a duplicate start that died on
  "address already in use" and failed whole task waves across concurrent
  shards. `tests/test_service_manager.py` updated; 31/31 pass.
- **Non-interactive EOF crash** (`cli/form_chat.py` service pre-flight prompt):
  `input("是否继续? (y/n): ")` raised `EOFError` whenever stdin was not a TTY
  (batch drivers, nohup, CI), killing runs in seconds as misleading
  `cli_failure`s. The prompt now only appears on a TTY; non-interactive runs
  continue and rely on the workflow-level pre-flight for re-validation.
- **Missing CB atoms block ODesign** (benchmark structure `3v03.pdb`):
  ODesign featurization asserts one representative atom per token; 3v03 has
  backbone-only LYS-316/ALA-367 (chains A and B), aborting every BSA aptamer
  run. Repaired with `experiments/repair_structure_cb.py` (idealized CB from
  backbone geometry, chain-inferred chirality; originals under
  `structures/originals/`). Docstring NOTE added in
  `RnaAptamerDesignWorkflow._run_odesign_inference`.

**Boundary documentation (comments only, no behavior change)**

- `design_mrna_cds_with_lineardesign` (`agent_core/tools.py`): LinearDesign is
  OOM-killed on CDS ≳ 7 kb (deterministic; Factor VIII, Zika) — use
  RNARL/GEMORNA for long targets; belongs to the manuscript limitations.
- `compute_utopian_reference_point` (`agent_core/workflows/multi_objective.py`):
  utopian-reference best candidates can have `asf_distance == 0` by
  construction; ablations must compare against a shared fixed reference,
  per-objective components, or Pareto hypervolume.
- `agent_core/runner.py` pipeline error wrapping: where to look when
  "pipeline failed without recorded errors" appears (session driver log).

---

## 2026-07-17 — Correctness Fixes Across Tools, Services, and BMC

**Tool / service fixes**

- **LinearFold-C MFE sign** (`microservices/linearfold_service/main.py`): upstream
  `linearfold_c` prints a raw CONTRAfold Viterbi score (*higher = more stable*),
  which the service returned verbatim as `mfe`, inverting every downstream
  "more negative = more stable" comparison (e.g. `score_mrna_candidate`).
  `/fold` and `/fold/zuker_subopt` now negate LinearFold-C energies; `/eval`
  already returned true thermodynamic (negative) energies.
- **RNASTOP service** (`microservices/rnastop_service/main.py`):
  - Default checkpoint changed to `best_model_weights_withoutDNABERT` — the
    DNABERT6 pretrained weights are not shipped (`external_repos/RNASTOP/DNABERT6`
    is empty), so the previous default always failed at first request.
  - User-supplied `structure` / `loop_type` are truncated to 512 nt alongside
    the sequence instead of rejecting full-length overrides with HTTP 400.
  - Structure overrides are sanitized for dangling brackets before native
    ViennaRNA calls — `RNA.db_to_element_string` segfaults on unbalanced
    dot-bracket input and previously killed the whole service process.
- **RNASTOP tool wrapper** (`agent_core/tools.py`): removed the >512 nt
  short-circuit that returned fabricated zero metrics (`overall_stability=0.0`)
  without calling the service; the service already truncates properly.
  `exceeded_max_length` is gone from the return dict and from
  `tool_specs.py` `produces[]`.
- **Evitar / siRNA FASTA header** (`agent_core/workflows/sirna_design.py`):
  the antiviral branch saved `target_sequence` as a headerless single-line
  file, but Evitar's `predictsiRNA` unconditionally discards the first input
  line as a FASTA header — the entire sequence was lost and `--predict predsi`
  returned zero candidates (`empty_candidate_list`). The workflow now writes a
  proper `>sirna_target` FASTA record.
- **Bowtie2 auto-start**: added `microservices/bowtie2_service/start.sh`
  (base conda env provides the `bowtie2` binary) and registered it in
  `CAPABILITY_SERVICE_MAP`; `SirnaDesignWorkflow` pre-flight no longer fails
  when the service is down.
- **GerNA-Bind → RhoFold dependency made explicit**
  (`agent_core/workflows/rna_small_molecule_interaction.py`):
  `required_capabilities` now includes `predict_rna_tertiary_structure_with_rhofold`
  (INTERFACE LOCK §9 bumped to **v1.1.0**), so the CLI pre-flight starts
  RhoFold instead of failing at runtime.
- **RNAsmol cold start / GPU incompatibility** (`microservices/rnasmol_service/`):
  `start.sh` pins `RNASMOL_DEVICE=cpu` (bundled env's PyTorch 1.7.1 cannot use
  sm_89/RTX 4090; first CUDA touch triggered minutes-long PTX JIT and client
  read timeouts), and the default checkpoint is preloaded at startup so a
  passed health check means scoring is immediately ready. GPU inference
  remains available via `start_gpu.sh` (`rnasmol_service_gpu_env`, torch 2.1).
- **EGARPS start.sh** now activates `egarps_env` (it previously activated
  `base`, whose torch 2.7 is incompatible with the EGARPS inference code).
- **CLI failure diagnostics** (`agent_core/runner.py`): when a pipeline run
  fails without raising, the streamed error now carries
  `pipeline_result.errors` instead of the opaque `"Unknown error"`.

**BMC**

- **Full-length mRNA UTR mode honoured** (`agent_core/workflows/coordinator.py`,
  `agent_core/workflows/full_length_mrna_design.py`, INTERFACE LOCK §14 bumped
  to **v2.7.0**): removed the coordinator's `utr_preset_exploration`
  adjustment and its handling in `_regenerate_modules()`. The mechanism was a
  no-op for `utr_mode="all"` and otherwise silently overrode an explicit
  single-preset `utr_mode`. Junction issues are now addressed solely by
  junction codon shuffling.

**Deployment**

- Removed `start_full_length_services.sh`: superseded by the CLI /
  `AgentRunner` service pre-flight, and it had diverged (force-killed ports,
  did not start RNARL 8008, wrote to a different log directory).

**Test-data fixes** (`pa_benchmarks.json`)

- PA_014 turns 1-2: `fold_tool_name="predict_rna_secondary_structure"` (Vienna)
  is now paired with `fold_service_url=http://127.0.0.1:8003/fold`; previously
  the default LinearFold URL was passed to the Vienna tool, silently folding
  with the wrong backend.

**Test-suite maintenance**

- `tests/test_tui_form_renderer.py` uses `pytest.importorskip("textual")`.
- `tests/test_service_manager.py`: `test_bowtie2_has_no_auto_start_script`
  replaced by `test_bowtie2_auto_start_script_registered`.

---

## 2026-07-16 — End-to-End Regression Fixes for PA Benchmarks

**What changed**

- Made `TuiFormRenderer` lazy-imported in `agent_core/form/__init__.py` so non-interactive CLI runs do not fail when `textual` is not installed.
- Fixed `RnaTertiaryStructureDesignWorkflow.generate_candidates` to clamp RhoDesign sampling temperatures to `>= 1e-6`, avoiding `temperature <= 0` service validation errors when `n_samples_per_tool > 1` and the base temperature is very small.
- Updated `pa_benchmarks.json` to match current workflow input models and file paths:
  - PA_012: corrected `sequence_filepath` to `test_5utr_long.fa`, added `top_n_candidates` and `run_structural_validation`.
  - PA_014: replaced obsolete `fold_tool_name` value `predict_rna_secondary_structure_with_viennarna` with the registered name `predict_rna_secondary_structure`; changed `sequence` to `sequences` for multi-sequence turns.
- Hardened microservice startup scripts to resolve import paths for `agent_core` / `microservices` modules:
  - `microservices/rna_sequence_metrics_service/start.sh` now exports `PYTHONPATH` pointing at the repo root.
  - `microservices/blast_service/start.sh` now exports `PYTHONPATH` pointing at the repo root.
  - `microservices/proteinx_service/start.sh` now tolerates unbound variables during `conda activate proteinx_service`.

---

## 2026-07-16 — Codebase Streamlining and Documentation Cleanup

**What changed**

- Deleted obsolete source modules that were no longer imported or maintained:
  - `agent_core/capabilities/writebacks.py` — declarative writeback mapping superseded by direct `Capability.invoke` and `_state_writeback` handling in workflows.
  - `agent_core/gpu_utils.py` — unused GPU utility helpers.
  - `data/references/download_references.py` — one-off reference downloader, no longer referenced.
- Removed deprecated natural-language entry points from `AgentRunner`:
  - `AgentRunner.run()` and `AgentRunner.stream()` were replaced by the form-driven `run_form()` / `stream_form()` / `run_pipeline()` APIs.
  - Removed the unused `_build_plan()`, `_build_workflow_param_schemas()`, and `_extract_param_schema()` helpers.
- Simplified the multi-agent base abstraction:
  - Removed the unused `AgentMessage` protocol from `agent_core/agents/base.py`.
  - `BaseAgent.handle()` now uses `Any` instead of the obsolete message type.
- Removed the legacy `FullLengthMrnaScoringFunction` from `agent_core/workflows/scoring.py`; active full-length mRNA scoring uses `FullLengthBMCScoringFunction`.
- Removed the deprecated `MrnaWorkflowInput` alias from `agent_core/workflows/mrna_sequence_scoring.py`.
- Removed unused species constants `CAI_CANONICAL_SPECIES` and `REFERENCE_SPECIES_DISPLAY_NAMES`.
- Consolidated the 19 individual PA benchmark drivers (`run_pa006_test.py` … `run_pa024_test.py`) into a single `run_pa_test.py` plus `pa_benchmarks.json`, eliminating duplicated boilerplate.
- Removed obsolete top-level end-to-end scripts superseded by the consolidated driver and the `tests/` suite:
  - `test_pa003_full_length_end_to_end.py`
  - `test_pa004_full_length_end_to_end.py`
  - `test_pa009_rna_aptamer_end_to_end.py`
  - `run_pa020_r3_optimized.py`
- Cleaned stale `agent_core/capabilities/writebacks.py` references from INTERFACE LOCK boxes across the codebase.
- Removed historical test artifacts, generated workspace reports, and stray logs/core dumps from the project root and `rna_agent_system/`.
- Drastically simplified `MULTI_AGENT_REDESIGN.md` to a concise landing summary; full details now live in `docs/ARCHITECTURE.md`, `docs/WORKFLOWS.md`, `docs/BMC_FRAMEWORK.md`, and `docs/INTERFACE_LOCKS.md`.
- Updated `AGENTS.md` and `docs/INTERFACE_LOCKS.md` §20 to reference the consolidated `run_pa_test.py` driver.

**Impact**

- Reduced non-test Python code volume by ~5% and project Markdown volume by ~87%.
- No functional behavior changes for supported form-driven and pipeline entry points.

---

## 2026-07-06 — Documentation Sync with Latest Code

**Verified** (non-breaking; docs-only):

| Interface / Document | Version | Reference |
|----------------------|---------|-----------|
| `CoordinatorAgent` | BMC controller | `agent_core/agents/coordinator_agent.py` |
| `MrnaCdsDesignWorkflow` | v1.1.0 | `docs/INTERFACE_LOCKS.md` §8 |
| `SgRnaDesignWorkflow` | v1.1.0 | `docs/INTERFACE_LOCKS.md` §11 |
| `FullLengthMrnaDesignWorkflow` | v2.6.3 | `docs/INTERFACE_LOCKS.md` §14 |
| `RnaAptamerDesignWorkflow` | v1.4.2 | `docs/INTERFACE_LOCKS.md` §15 |
| `AgentRunner` | v3.3.0 | `docs/INTERFACE_LOCKS.md` §19 |

**What changed**

- Synchronized all authoritative Markdown documentation with the current code base:
  - `CoordinatorAgent` is now documented as the BMC controller that orchestrates the bounded convergence loop, not a V1 facade.
  - Removed all references to the obsolete `TODO(MULTI_AGENT_REDESIGN)` and "BMC loop lives inside workflows" descriptions.
  - Unified workflow interface-lock versions across code headers, `docs/INTERFACE_LOCKS.md`, and `AGENTS.md`.
  - Corrected `SgRnaDesignInput.mutation_number` default to `22` in `docs/INTERFACE_LOCKS.md` §11.
  - Updated `FullLengthMrnaDesignWorkflow.required_capabilities` in `docs/WORKFLOWS.md` to match the code.
  - Added missing locked tools to the `AGENTS.md` summary and `docs/INTERFACE_LOCKS.md` table.
  - Refreshed `MULTI_AGENT_REDESIGN.md` to reflect that the redesign has been implemented.
  - Updated `docs/MANUSCRIPT.md` BMC issue types from legacy threshold names to `*_BELOW_REFERENCE`.
  - Refreshed all `Last updated` timestamps.

**Docs updated**: `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/BMC_FRAMEWORK.md`, `docs/CHANGELOG.md`, `docs/CONTRIBUTING.md`, `docs/DEPLOYMENT.md`, `docs/INTERFACE_LOCKS.md`, `docs/MANUSCRIPT.md`, `docs/README.md`, `docs/TOOLS.md`, `docs/WORKFLOWS.md`, `docs/tools/score_rna_protein_complex_with_egarps.md`, `MULTI_AGENT_REDESIGN.md`.

**Impact**

- Documentation now matches the runtime behavior of the codebase.
- No functional code changes.

---

## 2026-07-06 — Service Pre-Flight Hardening

**Verified** (non-breaking for public orchestration API; breaking for direct consumers of deleted legacy symbols):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `MrnaSequenceScoringWorkflow` | v1.0.0 | `docs/INTERFACE_LOCKS.md` §18 |
| `MrnaCdsDesignWorkflow` | v1.1.0 | `docs/INTERFACE_LOCKS.md` §8 |
| `start_service` | — | `agent_core/services/service_manager.py` |
| `cli/service_orchestrator.py` | — | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- `MrnaSequenceScoringWorkflow.run()` now calls `_service_preflight_result()` before generating/evaluating candidates, so `AgentRunner`-enabled `auto_start_services` is honored and missing LinearFold/ViennaRNA/GC/CAI services are started instead of failing mid-run.
- `MrnaCdsDesignWorkflow.partial_rerun()` now calls `_service_preflight_result()` before re-evaluating existing candidates, preventing service-down exceptions during `QualityAgent` / `SpecialistAgent` retries.
- `agent_core.services.service_manager.start_service()` now checks the exit code of `start.sh`. A non-zero exit produces a clear `RuntimeError` with the log tail, instead of silently returning and eventually timing out on health checks.
- Removed the legacy hand-maintained `SERVICE_HEALTH_URLS`, `_PORT_SERVICE_MAP`, `_build_workflow_services()`, and `get_workflow_services()` from `cli/service_orchestrator.py`. CLI orchestration continues to derive microservices from each workflow's `required_capabilities` via `CAPABILITY_SERVICE_MAP`, eliminating drift between the orchestrator and actual workflow needs.
- Fixed `ensure_services_ready()` lock-contention fallback: when another caller holds the startup lock, the fallback health poll now waits for the *remaining service-startup budget* (`timeout`) instead of `lock_timeout`, so slow-starting services (e.g., RhoFold/GEMORNA) no longer cause concurrent callers to fail prematurely.
- Fixed `check_service_health()` to inspect the JSON response body: endpoints that return HTTP 200 with `"status": "degraded"` are now treated as not ready, preventing workflows from entering tool execution when a runtime dependency is missing.
- The standalone convenience function `run_mrna_sequence_scoring()` now defaults to `auto_start_services=True`, matching `AgentRunner`-managed behavior. Pass `auto_start_services=False` when supplying a custom `ToolExecutor` in tests or other managed environments.

**Docs updated**: `docs/ARCHITECTURE.md`, `docs/CONTRIBUTING.md`, `docs/DEPLOYMENT.md`, `docs/TOOLS.md`, and this changelog.

**Impact**

- Workflows that bypassed service pre-flight now fail fast with actionable error messages when required microservices cannot be started.
- Troubleshooting service startup failures is faster because `start.sh` errors are surfaced immediately.
- Maintainers no longer need to keep two parallel service mappings in sync.

---

## 2026-07-05 — Agent-Layer Cleanup: BMC Facade, Pipeline Edges, and Hard-Failure Centralization

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `CoordinatorAgent` | BMC controller | `agent_core/agents/coordinator_agent.py` |
| `WorkflowResult` | — | `agent_core/workflow_models.py` |
| `PipelinePlan` | — | `agent_core/pipeline/models.py` |

**What changed**

- `CoordinatorAgent` now orchestrates the BMC convergence loop for BMC-capable workflows by consuming their four-phase interface (`run_initial`, `bmc_prepare`, `bmc_run_round`, `bmc_finalize`). The domain-specific diagnosis and feedback broadcasting remain inside `full_length_mrna_design.py` and `rna_aptamer_design.py` (`ReferencePointCoordinator` / `AptamerCoordinator`).
- Documented the strict `PipelinePlan` binding/edge rule: every data dependency declared in `input_bindings` must also be represented by an explicit `PipelineEdge`; a binding alone is not enough to create an execution dependency.
- Centralized the hard-failure predicate onto `WorkflowResult.is_hard_failure` and removed the duplicate `_is_hard_failure()` helpers from `QualityAgent` and `SpecialistAgent`.
- Confirmed `QualityProfile.build_prompt` is an active, intentional extension point (used by `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE`) and kept it; added guidance to avoid expanding the profile hierarchy unnecessarily.

**Docs updated**: `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/BMC_FRAMEWORK.md`, and this changelog.

**Impact**

- No observable runtime behavior change.
- Future agents will not mistakenly assume BMC coordination has already moved into `CoordinatorAgent`.
- The definition of a "hard failure" now has a single source of truth, reducing maintenance drift between `QualityAgent` and `SpecialistAgent`.

---

## 2026-07-04 — Multi-Agent Execution Engine Redesign (AgentRunner v3.2.0)

**Verified** (breaking for code importing deleted legacy symbols):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `AgentRunner` | v3.2.0 | `docs/INTERFACE_LOCKS.md` §19 |
| `CLI End-to-End Execution Flow` | v2.2.0 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Replaced the legacy execution engine with a dedicated multi-agent layer:
  - `PipelineAgent` — deterministic pipeline orchestration (no LLM).
  - `SpecialistAgent` — per-workflow execution and retry decisions.
  - `QualityAgent` — unified LLM-driven quality review using workflow-specific `QualityProfile` instances.
  - `SynthesisAgent` — final report synthesis for multi-node pipelines.
  - `CoordinatorAgent` — BMC controller for coupled workflows (initially introduced as a facade; loop orchestration fully implemented in 2026-07-05 cleanup).
- Introduced `PipelinePlan` / `PipelineNode` / `PipelineEdge` / `PipelineResult` in `agent_core/pipeline/` and `BindingResolver` for inter-node input bindings.
- Added `AgentRunner.run_pipeline(plan: PipelinePlan)` as the unified execution entry point; `run_form()` / `stream_form()` now build a single-node `PipelinePlan` internally.
- Removed legacy symbols:
  - `agent_core/planning/llm_critic.py`
  - `ExecutionPlan`, `PlanStep`, `ExecutionController` from `agent_core/planning/base.py`
  - Per-workflow `*LLMCritic` classes and `WORKFLOW_CRITIC_PAIRS` / `agent_core/workflows/registry.py`
  - The `Critic` ABC from `agent_core/planning/critic.py`
- Added `agent_core/quality_profiles/` package with a `QualityProfile` for every workflow; deterministic workflows use placeholder profiles with empty `evaluation_dimensions`.
- Migrated all Layer-3 tests from `ExecutionController` / `*LLMCritic` to `PipelineAgent` / `QualityAgent` / `SpecialistAgent`.
- Updated `docs/INTERFACE_LOCKS.md`, `docs/ARCHITECTURE.md`, `docs/WORKFLOWS.md`, `docs/BMC_FRAMEWORK.md`, `docs/README.md`, `docs/CONTRIBUTING.md`, root `AGENTS.md`, and all workflow INTERFACE LOCK headers to reference the new agents and quality profiles.

**Impact**

- Observable CLI/API behavior is unchanged.
- Any external code importing `ExecutionController`, `ExecutionPlan`, `PlanStep`, per-workflow `*LLMCritic` classes, or `agent_core/workflows/registry.py` must migrate to `PipelinePlan` / `PipelineAgent` / `QualityAgent` / `QualityProfile`.

---

## 2026-07-04 — Unified Species / Organism Registry

**What changed**

- Added `agent_core/constants/species.py` as the single source of truth for species/organism-related constants:
  - CAI codon-usage species aliases and canonical names (`CAI_SPECIES_ALIASES`, `CAI_CANONICAL_SPECIES`, `DEFAULT_CAI_SPECIES`)
  - RNARL trained model types and checkpoint mappings (`RNARLModelType`, `RNARL_MODEL_TYPES_LIST`, `RNARL_MODEL_TYPE_TO_CHECKPOINT`, `DEFAULT_RNARL_MODEL_TYPE`)
  - Reference transcriptome species IDs for siRNA/off-target workflows (`REFERENCE_SPECIES_IDS`, `REFERENCE_SPECIES_DISPLAY_NAMES`, `DEFAULT_REFERENCE_SPECIES_ID`)
- Replaced hard-coded species strings in `agent_core/sequence_utils.py`, `agent_core/tools.py`, `agent_core/tool_specs.py`, `agent_core/workflows/mrna_cds_design.py`, `agent_core/workflows/full_length_mrna_design.py`, `agent_core/workflows/mrna_sequence_scoring.py`, `agent_core/workflows/evaluators.py`, `agent_core/workflows/sirna_design.py`, `agent_core/workflow_baseline_eval.py`, `microservices/rnarl_service/main.py`, and `data/references/download_references.py` with imports from the new registry.
- Fixed `mrna_sequence_scoring.py` to use the workflow input's `cai_species` instead of a hard-coded `"Homo sapiens"`.

**Impact**

- No breaking interface changes; all locked field defaults and allowed values remain identical.
- Future species/model-type additions or renamings only need to change `agent_core/constants/species.py`.

**Docs updated**: `docs/TOOLS.md`, `docs/WORKFLOWS.md`, `docs/INTERFACE_LOCKS.md`, `data/references/README.md`, and this changelog.

---

## 2026-07-03 — Form-Driven CLI and AgentRunner v3.0.0 (breaking)

**Verified** (breaking for callers using natural-language input, clarification loops, or the old `cli/agent_chat.py` entry point):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `AgentRunner` | v3.0.0 | `docs/INTERFACE_LOCKS.md` §19 |
| `CLI End-to-End Execution Flow` | v2.0.0 | `docs/INTERFACE_LOCKS.md` §20 |
| `ExecutionPlan` | — | `agent_core/planning/base.py` |

**What changed**

- Replaced the natural-language / clarification-loop CLI (`cli/agent_chat.py`) with a form-driven TUI entry point (`cli/form_chat.py`).
- Added `agent_core/form/` package: `schema_builder.py`, `validator.py`, and `renderer.py` for deriving, validating, and rendering workflow forms from Pydantic input models.
- Added `AgentRunner.run_form()` and `AgentRunner.stream_form()`; removed all regex-based parameter extractors, sequence pre-extraction, and clarification-loop handling from `AgentRunner`.
- `ExecutionPlan` no longer carries `needs_clarification`, `missing_params`, `extracted_params`, or `clarification_message`.
- `AgentState` added `_form_params`, `_last_form_params`, and `_last_form_params_by_workflow` for per-workflow form prefilling; removed `_extracted_sequences`, `_extracted_rna_sequences`, and `_user_supplied_params`.
- Updated workflow `input_model` fields with `json_schema_extra={"ui_group": "basic"}` for core parameters; tool-prefixed override parameters default to the `advanced` group.
- Rewrote `workflow_api/app.py` to accept structured `workflow` + `params` input and call `run_form()`.
- Rewrote all PA end-to-end drivers (`run_pa006_test.py` through `run_pa024_test.py`) to use JSON parameter files with `cli/form_chat.py`; removed obsolete `run_pa*.exp` expect scripts.
- Added `tests/test_form_schema_builder.py`, `tests/test_form_validator.py`, `tests/test_tui_form_renderer.py`, and `tests/test_runner_form.py`; updated `tests/test_llm_planner.py` and `tests/test_cli_candidate_dict.py`.
- Updated `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/CONTRIBUTING.md`, `docs/INTERFACE_LOCKS.md` §19/§20, root `AGENTS.md`, and this changelog.

**Impact**

- All CLI and programmatic entry points now require an explicit workflow and structured parameters; natural-language input is no longer parsed for parameter extraction.
- Multi-turn state is isolated per workflow via `_last_form_params_by_workflow`.

---

## 2026-07-02 — RNA Aptamer Design Reference-Point/ASF Refactor (v1.4.0)

**Verified** (breaking for callers depending on `bmc_mode`, `bmc_targets`, weighted-sum `total_score`, or legacy AptamerCoordinator issue types):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `RnaAptamerDesignWorkflow` | v1.4.0 | `docs/INTERFACE_LOCKS.md` §15 |
| `AptamerCoordinator` | — | `agent_core/workflows/coordinator.py` |

**What changed**

- Replaced threshold-based BMC with reference-point driven BMC, matching the `FullLengthMrnaDesignWorkflow` pattern.
- Replaced weighted-sum `total_score` ranking with ASF-distance ranking; `score_aptamer_candidate()` now returns only component scores (`egarps_component`, `rhofold_component`, `iptm_component`).
- Removed `bmc_mode`, `bmc_targets`, and `LLMAptamerCoordinator` from the workflow.
- Added `bmc_max_rounds: int` (default `1`, `ge=0`) and `bmc_improvement_threshold: float` (default `0.05`, `ge=0.0`) to `RnaAptamerDesignInput`.
- `rank_and_format()` now uses `_apply_reference_point_and_pareto()`; user-provided `reference_point` values are normalized against the initial candidate pool and fixed across BMC rounds.
- `AptamerCoordinator.diagnose()` emits `{objective}_BELOW_REFERENCE` issues against the normalized reference point; module adjustments map to `EGARPS_COMPONENT_BELOW_REFERENCE`, `RHOFOLD_COMPONENT_BELOW_REFERENCE`, and `IPTM_COMPONENT_BELOW_REFERENCE`.
- `AptamerCoordinationRound` audit fields updated to `reference_point_mode`, `reference_point`, and `dim_bounds`.
- Removed `weight_egarps`/`weight_rhofold` from aptamer benchmark JSONs; design intent is now expressed via `reference_point`.
- Updated `tests/test_rna_aptamer_design.py`, `tests/test_bmc_full_length_mrna.py`, and `tests/test_bmc_workflow_e2e_mock.py`.
- Updated `docs/INTERFACE_LOCKS.md` §15, `docs/WORKFLOWS.md` §10, `docs/BMC_FRAMEWORK.md` §5, root `AGENTS.md`, and source-file interface-lock headers.

**Impact**

- Aptamer design now uses the same reference-point/ASF abstraction as full-length mRNA design, making multi-objective intent explicit and unifying the BMC coordinator interface.
- Legacy threshold and weight knobs are gone; the reference point is the single source of truth for ranking and module-level diagnosis.

---

## 2026-07-02 — RNA Aptamer Design BMC Diagnosis Set Expansion (v1.3.0)

**Verified** (breaking for callers depending on the old single-best-candidate BMC diagnosis or the old optional `metrics` argument to `AptamerCoordinator.broadcast_feedback()`):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `RnaAptamerDesignWorkflow` | v1.3.0 | `docs/INTERFACE_LOCKS.md` §15 |
| `AptamerCoordinator` | — | `agent_core/workflows/coordinator.py` |

**What changed**

- BMC Phase 3 no longer diagnoses only the ASF best candidate.
- Added `_select_diagnosis_candidates()` to build a representative set: ASF best + per-objective leaders across `egarps_component`, `rhofold_component`, and `iptm_component`.
- Added `_merge_issues_with_sources()` to merge issues by type while preserving the source candidate's raw metrics bundle for the worst violation.
- `AptamerCoordinator.broadcast_feedback()` now requires `metrics`; `_target_adjustments()` and `_aptamer_adjustments()` now require `metrics`.
- Module adjustments are now source-aware: e.g., `RNA_FOLDABILITY_LOW` uses `aptamer_length_delta = 10` when the source candidate's `rhofold_mean_plddt < 60.0`, otherwise 5.
- `AptamerCoordinationRound` now records `diagnosis_candidate_ids`.
- `_regenerate_modules()` now accepts required `issues` and `issue_source_metrics` arguments.
- Added `TestBmcDiagnosisSet` in `tests/test_rna_aptamer_design.py` covering diagnosis-set selection, issue merging, and multi-candidate diagnosis.
- Updated `docs/INTERFACE_LOCKS.md` §15, `docs/WORKFLOWS.md` §10, root `AGENTS.md`, and source-file interface-lock headers.

**Impact**

- BMC can now discover trade-offs that the single best candidate hides (e.g., a candidate with weak binding but excellent foldability, or vice versa).
- Feedback intensity is driven by the actual severity of the worst diagnosed issue, not by the average/best candidate metrics.

---

## 2026-07-01 — Full-Length mRNA Workflow Simplification (v2.5.0)

**Verified** (breaking for callers depending on Borda-count ranks, aggregate `junction_score`, or per-junction keys in `reference_point`):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `FullLengthMrnaDesignWorkflow` | v2.5.0 | `docs/INTERFACE_LOCKS.md` §14 |
| `ReferencePointCoordinator` | — | `agent_core/workflows/coordinator.py` |

**What changed**

- Removed the legacy 5-dimensional equal-weight Borda count from `rank_and_format()`.
- Candidates are now ranked by ASF distance to the reference point; `total_rank`, `total_score`, and per-dimension rank fields are no longer written to `candidate.scores`.
- Removed `junction_score` from `ReferencePointCoordinator.OBJECTIVES` and from user-facing `reference_point` keys.
- `junction_5utr_cds_score` and `junction_cds_3utr_score` remain internal coordinator diagnostics only.
- Reduced junction GC-diff penalty coefficient from `5.0` to `1.0` so MFE and GC-smoothness terms contribute on comparable scales.
- Added `target_cds_mfe` and `target_cds_cai` input fields; when both are provided they auto-convert to a `cds_component` reference point.
- Added full-length GC content evaluation (`full_length_gc` in `metrics_bundle`).
- Split CDS-level BMC feedback: weak CAI increases λ by 2; weak MFE stability decreases λ by 2.
- BMC convergence now uses normalized ASF improvement (`improvement_threshold=0.05`).
- Updated tests, `docs/INTERFACE_LOCKS.md` §14, `docs/WORKFLOWS.md` §4, root `AGENTS.md`, and source-file interface-lock headers.

**Impact**

- The user-facing objective space is smaller and more intuitive.
- Junction scores no longer leak into user-configurable reference points.
- CDS lambda adjustments are now directionally correct for the actual weakness (CAI vs MFE).

---

## 2026-07-02 — Full-Length mRNA Workflow Reference-Point Fixes (v2.5.1–v2.6.1)

**Verified** (non-breaking for end users; internal coordinator audit trace and user-reference-point stability improved):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `FullLengthMrnaDesignWorkflow` | v2.6.1 | `docs/INTERFACE_LOCKS.md` §14 |
| `ReferencePointCoordinator` | — | `agent_core/workflows/coordinator.py` |

**What changed**

- **v2.5.1**: `JunctionEvaluator` now computes `junction_*_gc_diff` across the actual UTR/CDS boundary (left fragment = UTR side, right fragment = CDS side), preserving biological meaning when one side is shorter than the 20-nt overlap window.
- **v2.5.2**: BMC Phase 3 now diagnoses a representative set (ASF best + per-objective leaders); issues are merged by type with the worst violation preserved; `_regenerate_modules()` collects CDS seeds from the full diagnosis set to preserve trade-off diversity; `bmc_max_rounds` and `bmc_improvement_threshold` are exposed as user inputs.
- **v2.6.0**: User-provided `reference_point` values are normalized against the initial candidate pool once and kept fixed across all BMC rounds; auto-derived utopian points are re-derived each round; `CoordinationRound` records `reference_point_mode`, normalized `reference_point`, and `dim_bounds`.
- **v2.6.1**: `reference_point` no longer accepts the internal `cds_component` key directly; valid user-facing keys are `utr5_mrl`, `utr3_stability`, and `full_mfe_score`; CDS objectives are supplied via `target_cds_mfe` and `target_cds_cai`, which are synthesized into the internal `cds_component` value.

**Impact**

- Cross-round reference-point behavior is deterministic and auditable.
- User intent for CDS objectives is expressed through familiar MFE/CAI targets rather than an internal combined score.

---

## 2026-07-01 — Reference-Point Driven BMC for Full-Length mRNA Design

**Verified** (breaking for callers depending on `FullLengthCoordinator`, `LLMFullLengthCoordinator`, `bmc_targets`, or old hard-threshold issue types):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `FullLengthMrnaDesignWorkflow` | v2.4.0 | `docs/INTERFACE_LOCKS.md` §14 |
| `ReferencePointCoordinator` | — | `agent_core/workflows/coordinator.py` |

**What changed**

- Replaced threshold-based `FullLengthCoordinator` with `ReferencePointCoordinator`.
- BMC diagnosis now measures normalized gaps to a reference point in the same objective space used by `best_candidate` selection (ASF).
- Removed `LLMFullLengthCoordinator` ablation and the `llm_coord` `bmc_mode` option.
- Removed `bmc_targets` from `FullLengthMrnaDesignInput`.
- `bmc_mode` is retained for interface compatibility and only accepts `"rp"`.
- Added per-junction score dimensions: `junction_5utr_cds_score` and `junction_cds_3utr_score`.
- New issue types: `*_BELOW_REFERENCE` for score dimensions; boolean AUG/Kozak burial issues remain.
- Updated `_regenerate_modules()` feedback mapping to use dimension-based issues.
- Updated tests in `tests/test_bmc_full_length_mrna.py` and `tests/test_bmc_workflow_e2e_mock.py`.
- Updated `docs/INTERFACE_LOCKS.md` §14, `docs/WORKFLOWS.md` §4, `docs/BMC_FRAMEWORK.md` §4, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, and source-file interface-lock headers.

**Impact**

- The reference point is the single source of truth for both ranking and BMC coordination.
- All score dimensions are comparable because they are min-max normalized within the candidate pool.
- The coordinator is fully deterministic and no longer relies on hand-tuned physical thresholds.

---

## 2026-07-01 — RPO/Pareto Become Default; BMC Coordinator Switches to Soft Target Constraints

**Verified** (breaking for callers depending on the old default ranking path or on `pareto_output`):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `FullLengthMrnaDesignWorkflow` | v2.4.0 | `docs/INTERFACE_LOCKS.md` §14 |
| `RnaAptamerDesignWorkflow` | v1.2.0 | `docs/INTERFACE_LOCKS.md` §15 |
| `FullLengthCoordinator` | — | `agent_core/workflows/coordinator.py` |
| `AptamerCoordinator` | — | `agent_core/workflows/coordinator.py` |

**What changed**

- Removed `pareto_output: bool` from both `FullLengthMrnaDesignInput` and `RnaAptamerDesignInput`. The Pareto-optimal frontier is now always computed and returned in `WorkflowResult.pareto_frontier`.
- `reference_point` is now optional in both workflows; when omitted, a utopian reference point is auto-derived from the candidate pool. `best_candidate` is always selected by Achievement Scalarizing Function (ASF) distance to this point.
- Removed the old default ranking fallback: full-length no longer selects the 5-d Borda winner as `best_candidate`, and aptamer no longer selects the weighted-sum winner as `best_candidate`. Both still compute `total_rank`/`total_score` for display and backward compatibility.
- Added `bmc_targets: Optional[dict[str, float]]` to both input models, allowing users to override coordinator target values.
- Converted `FullLengthCoordinator` and `AptamerCoordinator` from hard thresholds to soft target constraints. Every `Issue` now carries a continuous `violation` score (`0` = satisfied, larger = further from target).
- BMC Phase convergence now stops on zero total violation instead of a binary "no issues" check.
- `WorkflowResult` always carries `pareto_frontier`, `reference_point`, and `best_candidate_source` (when candidates exist).
- Updated `docs/INTERFACE_LOCKS.md`, `docs/WORKFLOWS.md`, root `AGENTS.md`, and source-file interface-lock headers.

**Impact**

- Multi-objective trade-offs are now the default behavior for the two BMC workflows.
- Coordinator decisions are continuous and tunable via `bmc_targets`, enabling softer, more granular refinement loops.

---

## 2026-07-01 — ProteinX Microservice Concurrency Fix

**Verified** (no interface/schema change; internal implementation fix):

| Component | Version | Reference |
|-----------|---------|-----------|
| `microservices/proteinx_service/main.py` | — | service implementation |
| `/predict/protein`, `/predict/complex` endpoints | — | `microservices/proteinx_service/main.py` |

**What changed**

- Moved the blocking `subprocess.run(...)` calls inside `/predict/protein` and `/predict/complex` into `asyncio.to_thread(...)`.
- This keeps the FastAPI event loop responsive during long Protenix inference, so `GET /health` no longer times out and the workflow's `_ensure_services_running()` health check no longer falsely restarts the service.
- Request/response schemas are unchanged; therefore, no tool interface lock version bump is required.

**Validation**

- PA_009 RNA aptamer end-to-end test with `N_ODESIGN_SAMPLES=2` completed successfully (4 candidates, 1 BMC round, Pareto frontier size 3) without `/health` timeouts or false service restarts.

---

## 2026-07-01 — Reference-Point Optimization & Pareto Frontier Output for BMC Workflows

**Verified** (non-breaking for default path; additive interface change):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `FullLengthMrnaDesignWorkflow` | v2.3.0 | `docs/INTERFACE_LOCKS.md` §14 |
| `RnaAptamerDesignWorkflow` | v1.1.0 | `docs/INTERFACE_LOCKS.md` §15 |
| `agent_core/workflows/multi_objective.py` | v1.0.0 | new reusable utilities |

**What changed**

- Added `reference_point: Optional[dict[str, float]]` to `FullLengthMrnaDesignInput` and `RnaAptamerDesignInput`. When provided, `rank_and_format()` selects `best_candidate` by Achievement Scalarizing Function (ASF) distance to the reference point instead of the default Borda/weighted-sum winner.
- Added `pareto_output: bool` to both input models. When `True`, `rank_and_format()` computes the Pareto-optimal frontier over the workflow's objective dimensions and returns it in `WorkflowResult.pareto_frontier`.
- Added `agent_core/workflows/multi_objective.py` with reusable helpers for normalization, ASF scalarization, Pareto dominance, frontier capping, and frontier tagging.
- Full-length objectives for reference-point/Pareto: `cds_component`, `utr5_mrl`, `utr3_stability`, `full_mfe_score`, `junction_score`.
- Aptamer objectives for reference-point/Pareto: `egarps_component`, `rhofold_component`, `iptm_component`; ASF weights reuse the user's `weight_egarps`/`weight_rhofold`/`weight_iptm`.
- `WorkflowResult` now optionally carries `pareto_frontier`, `reference_point`, and `best_candidate_source` fields. API response, persistence (`result.json`), and CLI context include these fields when present.
- Existing default behavior is unchanged: without `reference_point` or `pareto_output`, workflows use their original ranking (5-d Borda for full-length, weighted sum for aptamer).
- Added `tests/test_multi_objective_utils.py` and extended `tests/test_full_length_mrna_design.py` / `tests/test_rna_aptamer_design.py` with reference-point and Pareto-frontier tests.
- Updated `docs/INTERFACE_LOCKS.md` §14/§15, `docs/WORKFLOWS.md` §4/§10, root `AGENTS.md`, and source-file interface-lock headers.

**Impact**

- Users can now express design intent as an aspiration vector (e.g., "prefer higher binding affinity" or "prioritize foldability") rather than relying solely on fixed aggregate rankings.
- Users can receive a trade-off frontier instead of a single best candidate, making multi-objective decisions explicit.
- Default paths remain backward-compatible; new features are opt-in.

---

## 2026-07-01 — Full-Length mRNA Junction MFE Normalization & AUG/Kozak Activation

**Verified** (breaking for direct coordinator/scoring callers; transparent for workflow end users):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `FullLengthMrnaDesignWorkflow` | v2.2.0 | `docs/INTERFACE_LOCKS.md` §14 |
| `FullLengthCoordinator` | — | `agent_core/workflows/coordinator.py` |

**What changed**

- Length-normalized junction MFE thresholds in `FullLengthCoordinator.THRESHOLDS`: `junction_5utr_cds_mfe_per_nt: -0.50` and `junction_cds_3utr_mfe_per_nt: -0.375` (derived from −20 / 40 nt and −15 / 40 nt). The coordinator and BMC scoring function now require `junction_*_mfe_per_nt`; raw `junction_*_mfe` values are no longer interpreted for threshold or scoring decisions.
- `JunctionEvaluator` now records `junction_*_length` and `junction_*_mfe_per_nt` for each junction.
- `FullLengthMrnaDesignWorkflow.evaluate()` now propagates AUG/Kozak burial metrics (`junction_5utr_cds_aug_*`, `junction_5utr_cds_kozak_*`) into the coordinator `metrics_bundle`, activating the previously dormant `JUNCTION_5UTR_CDS_AUG_BURIED` and `JUNCTION_5UTR_CDS_KOZAK_BURIED` diagnosis rules.
- `JunctionEvaluator._check_translation_start()` now receives the CDS start offset and checks the canonical start codon at the 5'UTR–CDS boundary, avoiding false positives from upstream AUGs in the 5'UTR portion.
- `FullLengthBMCScoringFunction.score()` now uses length-normalized `junction_*_mfe_per_nt` values for `junction_score`.
- Corrected aptamer BMC documentation: default `max_rounds` is 1, not 2 (`no_bounds` mode allows up to 5).
- Updated tests, `docs/INTERFACE_LOCKS.md` §14, `docs/WORKFLOWS.md` §4, `docs/BMC_FRAMEWORK.md` §4, and root `AGENTS.md` to reflect v2.2.0.

**Impact**

- Junction diagnosis is now fair for variable-length overlaps (e.g. short UTRs or CDS < 20 nt).
- AUG/Kozak burial checks are now active and precise to the CDS boundary; they will trigger UTR preset exploration + N-terminus codon shuffling when detected.
- Direct callers of `FullLengthCoordinator.diagnose()` or `FullLengthBMCScoringFunction.score()` must now supply `junction_*_mfe_per_nt` instead of raw `junction_*_mfe`. The `FullLengthMrnaDesignWorkflow` end-to-end path is unaffected because `JunctionEvaluator` emits per-nt values.


---

## 2026-07-01 — Full-Length mRNA BMC Coordinator Unification

**Verified** (non-breaking for default path; additive interface change):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `FullLengthMrnaDesignWorkflow` | v2.1.0 | `docs/INTERFACE_LOCKS.md` §14 |
| `FullLengthCoordinator` | — | `agent_core/workflows/coordinator.py` |

**What changed**

- Added `bmc_mode: Literal["full", "llm_coord"]` to `FullLengthMrnaDesignInput`.
- Added `LLMFullLengthCoordinator` — an opt-in, LLM-based `diagnose()` ablation that inherits from `FullLengthCoordinator`, reuses `broadcast_feedback()` / `has_converged()`, and falls back to deterministic rules on any LLM or parse failure.
- Wired `bmc_mode` into the Phase 3 BMC loop so the workflow selects between deterministic `FullLengthCoordinator` (default) and `LLMFullLengthCoordinator`.
- Preserved `bmc_mode` across `_adjust_input_from_feedback()` regeneration rounds.
- Moved `junction_5utr_cds_mfe: -20.0` from a hard-coded constant into `FullLengthCoordinator.THRESHOLDS` for consistency with the LLM coordinator prompt.
- Added `TestLLMFullLengthCoordinator` in `tests/test_bmc_full_length_mrna.py` covering mock-LLM diagnosis, JSON parsing, and deterministic fallback.
- Added `start_full_length_services.sh` to launch all 7 microservices required for a live full-length mRNA design run.
- Added `test_pa004_full_length_end_to_end.py` — a real end-to-end regression against live LinearDesign/GEMORNA/ViennaRNA/LinearFold/IRESfinder/RNASTOP/sequence-metrics services, using the PA_004 human EPO benchmark task.
- Updated `docs/INTERFACE_LOCKS.md` §14, `docs/WORKFLOWS.md` §4, `docs/BMC_FRAMEWORK.md` §4, `docs/DEPLOYMENT.md`, and root `AGENTS.md` to document the new mode and version bump.

**Impact**

- Default behavior (`bmc_mode="full"`) is unchanged and remains fully deterministic.
- Users can now optionally enable `bmc_mode="llm_coord"` for research ablation, matching the existing RNA aptamer design workflow.
- The paper narrative for BMC is unified: both Type-I and Type-II workflows share the same deterministic-by-default coordinator abstraction with an optional LLM-based diagnosis ablation.


---

## 2026-06-27 — Documentation Sync & Simplification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| All project Markdown docs | — | `rna_agent_system/docs/`, `AGENTS.md` |

**What changed**

- Synchronized all authoritative Markdown documentation with the current code base.
- Fixed interface-lock version mismatches (`AgentRunner` v3.0.0, `IresPredictionWorkflow` v1.1.0, CLI End-to-End v2.0.0).
- Corrected `FullLengthMrnaDesignWorkflow` scoring description to reflect the 5-dimensional equal-weight Borda count used by `rank_and_format()` and the `max_rounds=1` BMC bound.
- Fixed the aptamer workflow's RhoFold service mapping to port 8005 / `rhofold_service`.
- Added missing required capabilities for `SirnaDesignWorkflow` and `IresPredictionWorkflow`.
- Documented `RnaSecondaryStructureDesignWorkflow` fields (`repeats` default 10, `temp_c`, `function_mode`) and `RnaTertiaryStructureDesignWorkflow` scoring weights (`weight_rhofold`, `weight_rmsd`).
- Reduced total documentation word count by ≥10% by removing duplication and stale content.


**Impact**

- Docs now match the runtime behavior of the codebase.


---

## 2026-06-26 — PA_023 IRES Prediction Critic Context Fix

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `IresPredictionWorkflow` | v1.1.0 | `docs/INTERFACE_LOCKS.md` §13 |

**What changed**

- Extended `IresPredictionLLMCritic._build_context` to expose two IRES-specific facts to the LLM:
  1. The workflow automatically DNA-normalises RNA input (U→T) before calling IRESfinder.
  2. The raw IRESfinder output summary (`max_score`, `decision_threshold`, `has_putative_ires`, `positive_count`, `fragment_count`, `best_fragment_id`).
- Added an explicit evaluation dimension to `IRES_PREDICTION_CRITIC_CONFIG` instructing the Critic not to diagnose low/zero probabilities as nucleotide-alphabet mismatches.
- Updated `docs/INTERFACE_LOCKS.md` §13 and root `AGENTS.md` to document the enhanced Critic context.


**Impact**

- Eliminates a recurring LLM hallucination where the Critic incorrectly attributed a mode-0 no-positive result to "RNA contains U while IRESfinder expects DNA T".
- Future `ires_prediction` changes should continue to run `tests/test_ires_prediction.py` and the PA_023 regression.


---

## 2026-06-26 — PA_022 CLI End-to-End Interface Lock Update

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.7.4 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Promoted PA_022 (`aso_target_screening`) to a protected benchmark in the CLI End-to-End Interface Lock.
- Updated code-level INTERFACE LOCK comments in `cli/agent_chat.py` (`main()` and `_run_once()`) and `agent_core/runner.py` (`run()`) to v1.7.2 and added PA_022 to the verified benchmark list (also back-filled PA_021 in `runner.py`).
- Added canonical regression artifacts at the project root:
  - `run_pa022_test.py` (pexpect-based automated driver)
  - `pa022_query_r1.txt`, `pa022_query_r2.txt`, `pa022_query_r3.txt` (regression query files)
- Updated `docs/INTERFACE_LOCKS.md` §20 to list the PA_022 driver/query files and the required regression command (`python run_pa022_test.py`).


**Impact**

- Future changes to `cli/agent_chat.py`, `AgentRunner`, or `aso_target_screening` must also re-run the PA_022 regression in addition to PA_001–PA_021.
- The deterministic ASO override fix introduced earlier today is now protected by the locked CLI contract.


---

## 2026-06-26 — PA_022 ASO Target Screening Deterministic Parameter Override

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `AgentRunner` deterministic parameter overrides | v2.2.0 | `docs/INTERFACE_LOCKS.md` §19 |

**What changed**

- Added `_extract_aso_param_overrides` and `_apply_aso_overrides` to `agent_core/runner.py`.
- Extracts `aso_length`, `window_step`, `top_n_windows`, `binding_evaluation_tool`, and `target_mrna_filepath` directly from the user query so that follow-up turns (e.g.
- Applied alongside the existing siRNA / tertiary-structure / mRNA-scoring deterministic overrides in both the explicit-workflow and LLM-driven planning branches.


**Impact**

- PA_022 (`aso_target_screening`) three-turn regression now reliably switches parameters across turns: 18 nt/RNAup → 25 nt/RNAup → 25 nt/RNAcofold with `window_step=1→3` and `top_n_windows=10→20`.
- No change to public `AgentRunner` signatures or workflow input models.


---

## 2026-06-25 — PA_020 RNA Aptamer Design End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.6.0 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_020 (`rna_aptamer_design`) as a protected three-turn benchmark in the CLI End-to-End Interface Lock.
- Added `run_pa020_test.py` (pexpect-based automated driver) and `pa020_query_r1.txt` / `pa020_query_r2.txt` / `pa020_query_r3.txt` regression query files.
- Updated `docs/INTERFACE_LOCKS.md` §20, `AGENTS.md`, `cli/agent_chat.py`, `agent_core/runner.py`, and `agent_core/state.py` to include PA_020 in the locked CLI contract and regression checklist.


**Impact**

- Future CLI, `AgentRunner`, or `rna_aptamer_design` workflow changes must also re-run the PA_020 regression (`run_pa020_test.py`) in addition to PA_001–PA_019.
- The PA_020 run successfully exercised the full CLI flow and met the underlying scientific objective: all three turns produced VEGF165 aptamer candidates, respected the requested length/weight/hotspot/sampling parameter changes, generated correct cross-turn quantitative comparisons, and produced independent JSON/Markdown audit artifacts per turn.


---

## 2026-06-24 — PA_019 Full-Length mRNA Design End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.5.0 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_019 (`full_length_mrna_design`) as a protected three-turn benchmark in the CLI End-to-End Interface Lock.
- Added `run_pa019_test.py` (pexpect-based automated driver) and `pa019_query_r1.txt` / `pa019_query_r2.txt` / `pa019_query_r3.txt` regression query files.
- Updated `docs/INTERFACE_LOCKS.md` §20, `AGENTS.md`, `cli/agent_chat.py`, `agent_core/runner.py`, and `agent_core/state.py` to include PA_019 in the locked CLI contract and regression checklist.


**Impact**

- Future CLI, `AgentRunner`, or `full_length_mrna_design` workflow changes must also re-run the PA_019 regression (`run_pa019_test.py`) in addition to PA_001–PA_018.
- The PA_019 run successfully exercised the full CLI flow and met the underlying scientific objective: all three turns produced GFP full-length mRNA candidates, respected the requested lambda/UTR/codon-species parameter changes, generated correct cross-turn quantitative comparisons, and produced independent JSON/Markdown audit artifacts per turn.


---

## 2026-06-23 — PA_018 RNA Thermosensor Hairpin Inverse-Folding End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.4.0 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_018 (`rna_secondary_structure_design`) as a protected three-turn benchmark in the CLI End-to-End Interface Lock.
- Added `run_pa018_test.py` (pexpect-based automated driver) and `pa018_query_r1.txt` / `pa018_query_r2.txt` / `pa018_query_r3.txt` regression query files.
- Updated `docs/INTERFACE_LOCKS.md` §20, `AGENTS.md`, `cli/agent_chat.py`, `agent_core/runner.py`, and `agent_core/state.py` to include PA_018 in the locked CLI contract and regression checklist.


**Impact**

- Future CLI, `AgentRunner`, or `rna_secondary_structure_design` workflow changes must also re-run the PA_018 regression (`run_pa018_test.py`) in addition to PA_001–PA_017.
- The PA_018 run successfully exercised the full CLI flow and met the underlying scientific objective: all three turns produced 15 nt hairpin candidates, respected the requested structure constraints, temperature settings, and sampling parameters, and produced independent JSON/Markdown audit artifacts per turn.


---

## 2026-06-23 — PA_016 Antiviral siRNA Design End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.2.0 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_016 (`sirna_design`) as a protected three-turn benchmark in the CLI End-to-End Interface Lock.
- Added `run_pa016_test.py` (pexpect-based automated driver) and `pa016_query_r1.txt` / `pa016_query_r2.txt` / `pa016_query_r3.txt` regression query files.
- Added `workspace/sarscov2_nsp12_strains.fasta` as the multi-strain input required by the PA_016 third turn.
- Updated `docs/INTERFACE_LOCKS.md` §20, `AGENTS.md`, `cli/agent_chat.py`, `agent_core/runner.py`, and `agent_core/state.py` to include PA_016 in the locked CLI contract and regression checklist.


**Impact**

- Future CLI, `AgentRunner`, or `sirna_design` workflow changes must also re-run the PA_016 regression (`run_pa016_test.py`) in addition to PA_001–PA_015.
- The PA_016 run successfully exercised the full CLI flow and met the underlying scientific objective: all three turns produced 21 nt siRNA candidates, respected the requested algorithm/GC/off-target parameter changes, and produced independent JSON/Markdown audit artifacts per turn.


---

## 2026-06-22 — PA_013 RNA Tertiary Structure Design End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.8 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_013 (`rna_tertiary_structure_design`) as a protected three-turn benchmark in the CLI End-to-End Interface Lock.
- Added `pa013_inputs.txt` for manual end-to-end regression via input redirection.
- Updated `docs/INTERFACE_LOCKS.md` §20 and `AGENTS.md` to include PA_013 in the regression checklist.
- Updated `docs/WORKFLOWS.md` §8 to document PA_013 validation status and known third-party tool limitations (RiboDiffusion diversity collapse and RhoFold single-sequence failure on 1EHZ).
- Updated `cli/agent_chat.py` to render a tertiary-structure-specific cross-turn comparison table (length, GC, MFE, pLDDT, RMSD, TM-score, recovery rate, total_score) for `rna_tertiary_structure_design` sessions.


**Impact**

- Future CLI, `AgentRunner`, or `rna_tertiary_structure_design` workflow changes must also re-run the PA_013 regression (`pa013_inputs.txt`) in addition to PA_001–PA_012.
- The PA_013 run successfully exercised the full CLI flow but did **not** meet the underlying scientific objective of producing 1EHZ-faithful sequences; this is attributed to known limitations in the upstream RiboDiffusion and RhoFold models for this target, not to workflow or CLI defects.


---

## 2026-06-22 — `rna_tertiary_structure_design` Critic Config & Auditability Fix

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| `RnaTertiaryStructureDesignWorkflow` | v1.0.0 | `docs/INTERFACE_LOCKS.md` §17 |

**What changed**

- Aligned the LLM Critic configuration in `agent_core/workflows/rna_tertiary_structure_design.py` with the actual code defaults: `rhodesign_temperature` default is `0.8` (was incorrectly described as `0.1`) and `rhodesign_temperature_range` default is `0.5` (was incorrectly described as `0.2`).
- Added pre-deduplication design-tool counts (`_pre_dedup_design_tool_counts`) to the workflow state and surfaced them in the `WorkflowResult.summary`.


**Impact**

- No interface signature, return structure, or Pydantic field changes; the workflow lock version remains v1.0.0.
- Existing PA_013 and future `rna_tertiary_structure_design` runs will produce more accurate Critic guidance and clearer per-tool contribution audit trails.


---

## 2026-06-21 — PA_012 IRES Prediction End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.7 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_012 (`ires_prediction`) as a protected three-turn benchmark in the CLI End-to-End Interface Lock.
- Promoted `run_pa012_test.py` to the canonical automated pexpect-based regression driver for PA_012.
- Added `pa012_inputs.txt` for manual end-to-end regression via input redirection.
- Updated `docs/INTERFACE_LOCKS.md` §20 and `AGENTS.md` to include PA_012 in the regression checklist and to reference `run_pa006_test.py`, `run_pa007_test.py`, `run_pa008_test.py`, `run_pa010_test.py`, `run_pa011_test.py` and `run_pa012_test.py`.
- Updated `cli/agent_chat.py` interface-lock comments to name PA_012 as a consumer of the locked CLI flow.


**Impact**

- Future CLI, `AgentRunner`, or `ires_prediction` workflow changes must also re-run the PA_012 regression (`run_pa012_test.py`) in addition to PA_001–PA_011.


---

## 2026-06-21 — PA_011 ASO Target Screening End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.6 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_011 (`aso_target_screening`) as a protected three-turn benchmark in the CLI End-to-End Interface Lock.
- Promoted `run_pa011_test.py` to the canonical automated pexpect-based regression driver for PA_011.
- Updated `docs/INTERFACE_LOCKS.md` §20 and `AGENTS.md` to include PA_011 in the regression checklist and to reference `run_pa006_test.py`, `run_pa007_test.py`, `run_pa008_test.py`, `run_pa010_test.py` and `run_pa011_test.py`.
- Updated `cli/agent_chat.py` interface-lock comments to name PA_011 as a consumer of the locked CLI flow.


**Impact**

- Future CLI, `AgentRunner`, or `aso_target_screening` workflow changes must also re-run the PA_011 regression (`run_pa011_test.py`) in addition to PA_001–PA_010.


---

## 2026-06-21 — PA_010 RNA-Small-Molecule Interaction End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.5 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_010 (`rna_small_molecule_interaction`) as a protected three-turn benchmark in the CLI End-to-End Interface Lock.
- Promoted `run_pa010_test.py` to the canonical automated pexpect-based regression driver for PA_010.
- Updated `docs/INTERFACE_LOCKS.md` §20 and `AGENTS.md` to include PA_010 in the regression checklist and to reference `run_pa006_test.py`, `run_pa007_test.py`, `run_pa008_test.py` and `run_pa010_test.py`.
- Updated `cli/agent_chat.py` interface-lock comments to name PA_010 as a consumer of the locked CLI flow.


**Impact**

- Future CLI, `AgentRunner`, or `rna_small_molecule_interaction` workflow changes must also re-run the PA_010 regression (`run_pa010_test.py`) in addition to PA_001–PA_009.


---

## 2026-06-21 — PA_008 sgRNA Handle End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.4 | `docs/INTERFACE_LOCKS.md` §20 |
| `SgRnaDesignWorkflow` | v1.0.0 | `docs/INTERFACE_LOCKS.md` §11 |

**What changed**

- Added PA_008 (`sgrna_design`) as a protected three-turn benchmark in the CLI End-to-End Interface Lock.
- Promoted `run_pa008_test.py` to the canonical automated pexpect-based regression driver for PA_008.
- Updated `docs/INTERFACE_LOCKS.md` §20 and `AGENTS.md` to include PA_008 in the regression checklist and to reference `run_pa006_test.py`, `run_pa007_test.py` and `run_pa008_test.py`.
- Updated `cli/agent_chat.py` interface-lock comments to name PA_008 as a consumer of the locked CLI flow.


**Impact**

- Future CLI, `AgentRunner`, or `sgrna_design` workflow changes must also re-run the PA_008 regression (`run_pa008_test.py`) in addition to PA_001–PA_007 and PA_009.


---

## 2026-06-20 — PA_007 sgRNA Handle End-to-End Lock Verification & Default Tuning

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.3 | `docs/INTERFACE_LOCKS.md` §20 |
| `SgRnaDesignWorkflow` | v1.0.0 | `docs/INTERFACE_LOCKS.md` §11 |

**What changed**

- Added PA_007 (`sgrna_design`) as a protected four-turn benchmark in the CLI End-to-End Interface Lock.
- Added `run_pa007_test.py`, an automated pexpect-based regression driver that preserves the exact CLI prompt contract and records a timestamped log.
- Updated `docs/INTERFACE_LOCKS.md` §20 and `AGENTS.md` to include PA_007 in the regression checklist and to reference both `run_pa006_test.py` and `run_pa007_test.py`.
- Updated `cli/agent_chat.py` interface-lock comments to name PA_007 as a consumer of the locked CLI flow.
- Changed `SgRnaDesignInput.mutation_number` default from `22` to `3` so that the first round of PA_007 (and other sgRNA design tasks without an explicit mutation budget) starts with a conservative, therapeutic-friendly mutation count.


**Impact**

- Future CLI, `AgentRunner`, or `sgrna_design` workflow changes must also re-run the PA_007 regression (`run_pa007_test.py`) in addition to PA_001–PA_006 and PA_009.
- The `mutation_number` default change affects all `sgrna_design` calls that do not explicitly set the parameter; callers relying on the old default `22` must now pass `mutation_number=22` explicitly.


---

## 2026-06-18 — Legacy Workflow-API Cleanup

**Removed** (non-breaking for the current CLI / `AgentRunner` path):

| Component | Files | Reason |
|-----------|-------|--------|
| Legacy per-workflow HTTP handlers | `workflow_api/mrna_handler.py`, `workflow_api/mrna_schemas.py`, `workflow_api/sirna_handler.py`, `workflow_api/sirna_schemas.py`, `workflow_api/ires_handler.py`, `workflow_api/ires_schemas.py`, `workflow_api/rna_unified_handler.py` | Replaced by the unified `workflow_api/app.py` `/v1/agent/run` endpoint that routes through `AgentRunner` + `LLMPlanner`. |
| Legacy Layer 4/5 integration tests | `tests/test_mrna_layer45_integration.py`, `tests/test_rnai_layer45_integration.py`, `tests/test_ires_prediction_layer45.py`, `tests/test_aso_target_screening_layer45.py`, `tests/test_structure_design_layer45_integration.py`, `tests/test_prediction_screening_layer45_integration.py`, `tests/test_interaction_layer45_integration.py` | Tested the removed handlers and old `task_type` dispatch envelope. Core workflow logic is still covered by unit tests (`test_rna_aptamer_design.py`, `test_rna_small_molecule_interaction.py`, etc.). |
| Legacy workflow-specific API tests | `tests/test_mrna_workflow_api.py`, `tests/test_sirna_workflow_api.py` | Tested the removed handlers. |
| Legacy GC-content workflow tool | `agent_core/workflow_tools/`, `examples/workflow_gc_content_demo.py`, `tests/test_rna_gc_content_workflow.py` | Superseded by the atomic `compute_rna_sequence_gc_content` capability. |

**Impact**

- Python code base reduced by ~7,600 lines (~11.5%).
- `workflow_api/` now contains only the unified `app.py` entry point.
- Updated `INTERFACE_LOCKS.md` §3 and §7, `tool_specs.py` lock comments, and `DEPLOYMENT.md` test list to remove references to deleted files.


---

## 2026-06-17 — PA_009 Aptamer End-to-End Lock Verification & Documentation Audit

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.0 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_009 (`rna_aptamer_design`) to the CLI End-to-End Interface Lock verification set.
- Added the PA_009 manual regression command and `pa009_inputs.txt` to `docs/INTERFACE_LOCKS.md` §20 and `AGENTS.md`.
- Fixed `RnaAptamerDesignWorkflow._find_local_pdb_file()` and `_resolve_protein_structure()` to resolve bare PDB IDs (e.g.
- Fixed `RnaAptamerDesignWorkflow.evaluate()` metrics cache key to include evaluation `stage`, so full evaluation reuses cheap metrics but always reruns ProteinX + interface analysis.
- Updated `cli/agent_chat.py` LLM report context to explicitly label whether the protein structure came from a local file or a ProteinX prediction.
- Audited and refreshed `TOOLS.md`, `ARCHITECTURE.md`, `DEPLOYMENT.md`, and `README.md` to match current wrapper signatures, endpoints, parameter names, and BMC defaults.


**Impact**

- Future CLI / AgentRunner / aptamer-workflow changes must now also re-run the PA_009 regression in addition to PA_001, PA_002, PA_003 and PA_004.
- `TOOLS.md` now accurately reflects `filepath1`/`filepath2` RNAup inputs, ASO accessibility output keys, RNARL full model names, Evitar off-target parameters, the RNASTOP 512-nt hard limit, the Bowtie2 agent tool, and GerNA-Bind endpoint coverage.


---

## 2026-06-16 — PA_004 End-to-End Lock Verification

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.0 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_004 (`full_length_mrna_design`) to the CLI End-to-End Interface Lock verification set.
- Added the PA_004 manual regression command to `docs/INTERFACE_LOCKS.md` §20.
- Updated lock annotations in `cli/agent_chat.py`, `agent_core/runner.py`, `AGENTS.md`, and this changelog to include PA_004.


**Impact**

- Future CLI / AgentRunner / state-field changes must now also re-run the PA_004 regression in addition to PA_001, PA_002 and PA_003.


---

## 2026-06-15 — PA_003 End-to-End Lock Verification & Documentation Refresh

**Verified** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.0 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added PA_003 (`full_length_mrna_design`) to the CLI End-to-End Interface Lock verification set.
- Preserved regression artifacts under `rna_agent_system/PA_003_evidence/` and added the PA_003 manual regression command to `docs/INTERFACE_LOCKS.md` §20.
- Refreshed `ARCHITECTURE.md`, `WORKFLOWS.md`, `BMC_FRAMEWORK.md`, `TOOLS.md`, `DEPLOYMENT.md`, `AGENTS.md`, and `MANUSCRIPT.md` to match the current code:.
  - Removed all references to the deleted `DeterministicRouter`.
  - Documented the actual BMC bounds used by `full_length_mrna_design` (`max_rounds=1`) and `rna_aptamer_design` (`improvement_threshold=0.01`).
  - Corrected full-length scoring description to the 5-dimensional equal-weight Borda count.
  - Updated port registry, endpoints, environment names, and submodule list.


**Impact**

- Future CLI / AgentRunner / state-field changes must now also re-run the PA_003 regression in addition to PA_001 and PA_002.


---

## 2026-06-14 — Cross-Turn Critic Context for Accurate Metric Comparisons

**Fixed** (non-breaking):

| Issue | Files | Change |
|-------|-------|--------|
| LLM Critic hallucinated previous-round metrics during multi-turn optimization | `agent_core/runner.py`, `agent_core/planning/llm_critic.py`, `agent_core/state.py` | `AgentRunner.run()` and `AgentRunner.stream()` now preserve the previous turn's `workflow_result` as `_previous_workflow_result` before clearing stale results. `BaseLLMCritic._build_context()` exposes the previous best candidate's metrics in the diagnosis prompt, and the prompt rules forbid inventing previous metric values. |

**Impact**

- Multi-turn sessions (e.g., PA_003 lambda tuning and cross-species adaptation) now give the Critic exact previous-round CAI/MFE/UTR metrics.
- Prevents false claims such as "CAI did not improve" when the actual previous CAI was lower.


---

## 2026-06-13 — AgentRunner Cross-Turn Workflow Result Isolation

**Fixed** (non-breaking):

| Issue | Files | Change |
|-------|-------|--------|
| Stale `workflow_result` from previous turn polluted new design tasks | `agent_core/runner.py` | `AgentRunner.run()` and `AgentRunner.stream()` now pop any existing `workflow_result` from state at the start of a new workflow turn. This prevents old candidates (e.g., full-length GFP) from being merged into a subsequent redesign (e.g., truncated N-terminal GFP). Intra-turn multi-step plans and Critic retries still merge results via `ExecutionController`. |
| LLM Critic recommended invalid enum/null parameter values | `agent_core/planning/llm_critic.py` | Tightened diagnosis prompt: enum parameters now list exact allowed values, and rules explicitly forbid out-of-list enum values and null/None numeric overrides. |

**Impact**

- Multi-turn sessions no longer accumulate candidates across distinct design tasks.
- PA_002 regression (truncated GFP redesign after full-length run) now produces only 450 nt candidates in the second turn.


---

## 2026-06-13 — CLI End-to-End Interface Lock v1.0.0

**Locked** (non-breaking):

| Interface | Version | Reference |
|-----------|---------|-----------|
| CLI End-to-End Execution Flow | v1.0.0 | `docs/INTERFACE_LOCKS.md` §20 |

**What changed**

- Added `CLI END-TO-END INTERFACE LOCK (v1.0.0)` annotations to `cli/agent_chat.py`, `agent_core/runner.py`, and `agent_core/state.py`.
- Documented the full observable CLI contract: argument names, workflow selection sequence, microservice orchestration, `AgentRunner.run()` / `AgentRunner.stream()` signatures, `AgentState` fields consumed by the CLI, JSON/Markdown artifact structure, and synchronization checklist.
- Synchronized `ARCHITECTURE.md` §1.3 / §3.1 / §3.7 with the actual `AgentState` and `WorkflowResult` schemas.


**Impact**
- Future changes to the CLI→AgentRunner→result-files chain must now update all files listed in §20 and re-run the PA_001, PA_002 and PA_003 regressions.

---

## 2026-06-12 — Audit-Trail Fixes for Tool Results, Critic, and RNASTOP

**Fixed** (non-breaking, JSON output only):

| Issue | Files | Change |
|-------|-------|--------|
| Duplicate `tool_results` keys overwrote each other | `agent_core/capabilities/base.py`, `agent_core/planning/base.py` | New helper `_unique_tool_result_key()` generates human-readable, parameter-derived keys (e.g. `design_mrna_cds_with_lineardesign_lambda_value_0.5`) instead of numeric `_0` / `_1`. Preserves bare key backward compatibility. |
| Workflow `_state_writeback` lost on multi-step plans | `agent_core/planning/base.py` | Capture the current step's `_state_writeback` **before** `_merge_workflow_results()`; previously the merged `WorkflowResult` (which has no `_state_writeback`) caused later steps' tool results to disappear from audit JSON. |
| Critic diagnosis missing from JSON | `cli/agent_chat.py` | `_save_workflow_results()` now persists `_diagnosis_history`, `_quality_auto_retry`, `retry_count`, and `_quality_review_error`. |
| RNASTOP skipped/failed silently | `agent_core/workflows/evaluators.py`, `agent_core/workflows/mrna_cds_design.py` | `RNASTOPEvaluator` now returns `rnastop_failed` / `rnastop_error` on service errors. `MrnaCdsDesignWorkflow.evaluate()` propagates `rnastop_skipped`, `rnastop_skip_reason`, `rnastop_failed`, and `rnastop_error` into `metrics_bundle`. |

**Impact**:
- `workflow_results_*.json` now contains all distinct tool invocations when the same tool is called with different parameters.
- Critic diagnosis history is now reproducible from JSON, not only from Markdown reports.
- Long CDS sequences (> 512 nt) and RNASTOP service failures are auditable instead of appearing as unexplained `None` values.
- No scoring formulas or locked public signatures changed.

---

## 2026-06-12 — Documentation Refresh

Refreshed all project Markdown documentation to match the current Layer 3/4/5 implementation and the advisory-mode LLM Critic:

| Document | Changes |
|----------|---------|
| `README.md` | Updated dates, added clarification-loop note |
| `ARCHITECTURE.md` | Fixed Layer-0 file references, expanded `AgentState` fields, documented `user_params` and advisory retry |
| `WORKFLOWS.md` | Fixed `BaseDomainWorkflow.run()` signature, removed duplicate IRES critic paragraph, added `mrna_sequence_scoring` to landscape |
| `TOOLS.md` | Date refresh |
| `BMC_FRAMEWORK.md` | Date refresh |
| `INTERFACE_LOCKS.md` | Re-ordered §18/§19, expanded `AgentRunner` state fields, added `user_params` to `stream()` |
| `DEPLOYMENT.md` | Fixed section numbering, added clarification subsection, expanded test categories |
| `CONTRIBUTING.md` | Updated new-tool/workflow procedure for current Layer-1 writebacks |
| `AGENTS.md` | Synchronized with docs |

---

## 2026-06-10 — AgentRunner v2.1.0: Explicit Workflow Selection + CLI Orchestration

**Breaking change** (`agent_core/runner.py`):

| Component | Before | After |
|-----------|--------|-------|
| Routing | Two-tier: `DeterministicRouter` (keyword) → `LLMPlanner` fallback | **Explicit only**: caller provides `explicit_workflow` or CLI prompts the user |
| `AgentRunner.__init__` | Accepted `deterministic_router: Optional[DeterministicRouter] = None` | **Removed** `deterministic_router` parameter entirely |
| `AgentRunner.run()` | `run(user_input, *, session_id="", state=None)` | `run(user_input, *, session_id="", state=None, explicit_workflow=None)` |
| `AgentRunner.stream()` | `stream(user_input, *, session_id="")` | `stream(user_input, *, session_id="", explicit_workflow=None)` |
| `_build_plan()` | No workflow hint; full LLM routing | Accepts `explicit_workflow: Optional[str]`; when set, constrains `_available_workflows` to `[explicit_workflow]` and sets `_routing_method = "explicit"` |

**New CLI modules** (`cli/`):

| File | Purpose |
|------|---------|
| `cli/resource_checker.py` | GPU (≥ 24 GB), RAM (≥ 16 GB), CPU pre-flight checks |
| `cli/service_orchestrator.py` | Workflow-to-microservice mapping (reuses `SERVICE_HEALTH_URLS`), health polling, deduplicated startup |
| `cli/agent_chat.py` (refactored) | Full interactive flow: resource check → workflow multi-select → microservice startup → per-turn workflow pick → multi-turn chat |

**DeterministicRouter status**:
- Removed. `AgentRunner` now relies on explicit workflow selection via `explicit_workflow`.

**Updated documentation**:
- `AGENTS.md`, `ARCHITECTURE.md`, `README.md`, `DEPLOYMENT.md`, `CONTRIBUTING.md`, `INTERFACE_LOCKS.md`, `MANUSCRIPT.md`

**Migration guide for programmatic callers**:
```python
# Old (automatic routing)
runner = AgentRunner(planner, executor)
state = runner.run("Design siRNA for TP53")

# New (explicit workflow)
state = runner.run("Design siRNA for TP53", explicit_workflow="sirna_design")
```

---

## 2026-06-09 — GEMORNA UTR Evaluators Restored in Full-Length mRNA Design

**Fixed** (`agent_core/workflows/full_length_mrna_design.py`):

| Evaluator | Tool | Previous Behaviour | Current Behaviour |
|-----------|------|-------------------|-------------------|
| `UTR5MrlEvaluator` | `predict_5utr_mrl_with_gemorna` (8004) | Skipped (hard-coded empty dict) | **Real invocation** |
| `UTR3StabilityEvaluator` | `predict_3utr_stability_with_gemorna` (8004) | Skipped (hard-coded empty dict) | **Real invocation** |

**Impact**:
- `evaluate()` now produces non-`None` values for `utr5_predicted_mrl` and `utr3_predicted_stability` when the GEMORNA microservice is available.
- Borda-count ranking (`cds_component` + `utr5_mrl` + `utr3_stability`) and BMC weighted scoring now use actual GEMORNA predictions instead of penalising all candidates equally.
- `required_capabilities` already listed both tools; no interface version bump required.

**Benchmark updates**:

- All 22 `02_full_length_mrna_design_*.json` task files: `expected_tool_chain` updated to include `predict_5utr_mrl_with_gemorna` and `predict_3utr_stability_with_gemorna`.
- `generate_tasks.py` updated accordingly.

**Files touched**: `workflows/full_length_mrna_design.py`, benchmark task JSONs, `generate_tasks.py`.

---

## 2026-06-09 — U Content Evaluation Added to mRNA Workflows

**New evaluator** (`agent_core/workflows/evaluators.py`):

| Component | Description |
|-----------|-------------|
| `UContentEvaluator` | Wraps `compute_rna_sequence_u_content` (port 8020). Returns `u_fraction` and `u_count`. Always enabled (no toggle flag). |

**Workflow changes**:

| Workflow | Change |
|----------|--------|
| `MrnaCdsDesignWorkflow` | `CompositeEvaluator` now includes `UContentEvaluator`. `required_capabilities` adds `"compute_rna_sequence_u_content"`. Summary output includes `U=xxx`. |
| `FullLengthMrnaDesignWorkflow` | `SubWorkflowEvaluator` key_map remaps `"u_fraction" → "cds_u_fraction"`. `_u_content_evaluator` evaluates full-length sequence directly. Summary output includes `cdsU=xxx` and `fullU=xxx`. `required_capabilities` adds `"compute_rna_sequence_u_content"`. |

**Supporting changes**:

- `agent_core/sequence_utils.py`: `compute_mrna_metric_bundle()` now accepts optional `u_fraction` parameter.
- Benchmark task JSONs (`01_mrna_cds_design_*`, `02_full_length_mrna_design_*`): `expected_tool_chain` updated to include `"compute_rna_sequence_u_content"`.
- Tests: `test_u_content_capability` added to both comprehensive test suites; workflow Layer-2 assertions verify `u_fraction` / `cds_u_fraction` / `full_u_fraction` presence.

**Notes**:
- U content is a **reference metric only**; it does **not** enter either scoring formula (`total_score = -mfe + codon_count * log(CAI)` for CDS, Borda-count / BMC weighted sum for full-length).

**Files touched**: `workflows/evaluators.py`, `workflows/mrna_cds_design.py`, `workflows/full_length_mrna_design.py`, `sequence_utils.py`, benchmark task JSONs, comprehensive tests.

---

## 2026-05-28 — RNA Aptamer Design Workflow v1.0.0 + BMC Type-II

**New Layer-2 workflow** (`agent_core/workflows/rna_aptamer_design.py`):

| Component | Description |
|-----------|-------------|
| `RnaAptamerDesignWorkflow` | `BaseDomainWorkflow`: hotspot identification → ODesign ligand generation → RhoFold + EGARPS + ProteinX complex evaluation |
| `AptamerCoordinator` | BMC Type-II deterministic coordinator with 6 threshold-based diagnostic rules |
| `RnaAptamerDesignLLMCritic` | LLM-driven critic for user-intent alignment and scoring weight adjustment |

**New tools** (port 8022 ProteinX, port 8023 EGARPS, port 8012 ODesign):

| Tool | Purpose |
|------|---------|
| `predict_protein_structure_with_proteinx` | Protein structure prediction |
| `predict_rna_protein_complex_with_proteinx` | RNA-protein complex prediction |
| `analyze_rna_protein_interface` | Interface contact / SASA / H-bond analysis |
| `identify_protein_binding_hotspots` | Hotspot identification via freesasa + DBSCAN |
| `score_rna_protein_complex_with_egarps` | Complex quality scoring |
| `run_odesign_inference` | Aptamer sequence generation |
| `build_odesign_aptamer_input_json` | ODesign input builder |

**Files touched**: `workflows/rna_aptamer_design.py`, `workflows/coordinator.py`, `workflows/registry.py`, `tools.py`, `tool_specs.py`

---

## 2026-05-20 — RNA Secondary/Tertiary Structure Design Workflows v1.0.0

**New Layer-2 workflows**:

| Workflow | Pipeline |
|----------|----------|
| `RnaSecondaryStructureDesignWorkflow` | ViennaRNA inverse folding → RNAfold validation → structure-distance scoring |
| `RnaTertiaryStructureDesignWorkflow` | RhoDesign / RiboDiffusion 3D→sequence inverse folding |

**Files touched**: `workflows/rna_secondary_structure_design.py`, `workflows/rna_tertiary_structure_design.py`, `workflows/registry.py`, `runner.py`

---

## 2026-05-15 — IRES Prediction Workflow v1.0.0

**New Layer-2 workflow** (`agent_core/workflows/ires_prediction.py`):

| Component | Description |
|-----------|-------------|
| `IresPredictionWorkflow` | IRESfinder-based putative IRES element prediction |
| `IresPredictionLLMCritic` | Quality gate with progressive threshold relaxation |

**Files touched**: `workflows/ires_prediction.py`, `workflows/registry.py`, `runner.py`

---

## 2026-05-10 — Full-Length mRNA Design v2.0.0 + BMC Type-I

**Major update** (`agent_core/workflows/full_length_mrna_design.py`):

| Component | Description |
|-----------|-------------|
| `FullLengthCoordinator` | BMC Type-I deterministic coordinator with 8 threshold-based diagnostic rules for junction quality |
| `JunctionEvaluator` | Dedicated evaluator for 5'UTR-CDS and CDS-3'UTR junction MFE, GC diff, AUG/Kozak burial |
| `shuffle_cds_junction_codons` | New pure-Python tool for synonymous codon shuffling at junctions |

**Files touched**: `workflows/full_length_mrna_design.py`, `workflows/coordinator.py`, `workflows/evaluators.py`, `workflows/scoring.py`, `tools.py`, `tool_specs.py`

---

## 2026-05-08 — sgRNA Design Workflow v1.0.0

**New Layer-2 workflow** (`agent_core/workflows/sgrna_design.py`):

| Component | Description |
|-----------|-------------|
| `SgRnaDesignInput` | Pydantic input with `seed_sequence`, `guide_sequence`, `target_sequence`, `sampling_mode` |
| `SgRnaDesignWorkflow` | `BaseDomainWorkflow`: generate → evaluate → score → rank |
| `score_sgrna_candidate` | Combined score: `weight_nn_score * nn_component + weight_crisot_score * crisot_component` |
| `SgRnaCritic` | Quality gate with progressive threshold relaxation |

**Files touched**: `workflows/sgrna_design.py`, `workflows/__init__.py`, `workflows/registry.py`, `runner.py`

---

## 2026-05-07 — siRNA Design Workflow Tuning

**Changes** (`agent_core/workflows/sirna_design.py`):

| Component | Before | After |
|-----------|--------|-------|
| `OFF_TARGET_THRESHOLD` | `0` | `3` |
| `SPECIFICITY_THRESHOLD` | `0.95` | `0.25` |
| `MAX_RETRIES` | `3` | `2` |
| Retry strategy | Tighten GC only | Progressive: tighten BLAST identity + GC; relax off-target to 5 on final retry |

Interface version remains **v1.0.0** (`INTERFACE_LOCKS.md` §10); these are threshold/strategy changes, not breaking contract changes.

**Files touched**: `workflows/sirna_design.py`, `workflows/__init__.py`, `workflows/registry.py`, `tests/test_sirna_design_workflow.py`

---

## 2026-05-04 — RNA Aptamer Design Tools v0.2.0

**Added**: ProteinX complex prediction & interface analysis.

| Tool | Transport |
|------|-----------|
| `predict_rna_protein_complex_with_proteinx` | HTTP |
| `analyze_rna_protein_interface` | Pure Python (biopython + freesasa) |

**Scoring simplification**: `total_score = EGARPS + (RhoFold_pLDDT / 100) + ipTM`

---

## 2026-05-01 — RNA Aptamer Design Tools v0.1.0

**Initial aptamer toolkit**:

| Tool | Transport |
|------|-----------|
| `extract_rna_sequence_from_cif` | Pure Python |
| `build_odesign_aptamer_input_json` | Pure Python |
| `predict_protein_structure_with_proteinx` | HTTP |
| `identify_protein_binding_hotspots` | Pure Python |
| `score_structure_alignment` | Pure Python |

---

## 2026-04-28 — RNA Sequence U Content v0.1.0

Locked interface for `compute_rna_sequence_u_content`. See `INTERFACE_LOCKS.md` §5.

---

## 2026-04-28 — CAI for CDS v0.1.0

Locked interface for `compute_cai_for_cds_sequence`. Pure Python calculation using Kazusa tables. See `INTERFACE_LOCKS.md` §6.

---

## 2026-04-25 — GC Content Interface v0.1.0

Locked interface for `compute_rna_sequence_gc_content`. See `INTERFACE_LOCKS.md` §3.

---

## 2026-04-25 — Dot-Bracket Unpaired Fraction v0.1.0

Locked interface for `compute_dot_bracket_unpaired_fraction`. See `INTERFACE_LOCKS.md` §4.

---

## 2026-04-24 — LinearDesign Interface v0.2.0

Locked interface for `design_mrna_cds_with_lineardesign` (single + batch). See `INTERFACE_LOCKS.md` §7.

---

*For interface lock details and sync checklists, see [`INTERFACE_LOCKS.md`](INTERFACE_LOCKS.md).*
