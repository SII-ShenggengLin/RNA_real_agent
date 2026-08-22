# Change Log

> **Scope**: locked interface changes and major workflow introductions.
> **Last updated**: 2026-08-22

> **History policy (2026-08-18)**: this log now records only the current
> interface state and the most recent change era. The detailed per-day ledger
> through 2026-08-18 was purged in the 2026-08-18 simplification pass; the
> experimental arc (what was tried, what was falsified, with evidence
> pointers) lives in [`DECISIONS.md`](DECISIONS.md), and every experiment's
> raw verdicts live under `experiments/results/`.

## 2026-08-22 (c) — Layer-4 fresh-data audit: multi-agent + CapGate + ranking governance verified; five defects fixed

First dedicated fresh-data audit of Layer 4 — the multi-agent execution stack
(`PipelineAgent` / `SpecialistAgent` / `QualityAgent` / `SynthesisAgent`), the
calibrated CapGate stack (`CalibratedRuntime`, `DecisionGate`, `SelfModel`,
`ClaimGate`, audit trail) and the ranking governance
(`objective_assembly`) — on data fetched live during the audit (EPO mRNA
NM_000799 + CDS + protein, EV71 5'UTR NC_001612 + EV71-derived sgRNA spacer,
B2M CDS NM_004048, a live-esearched Xenopus laevis 5S rRNA record, RCSB 1AKI
lysozyme). Nothing reused from prior audits, PA fixtures or benchmark inputs.
Evidence: `workspace/layer4_fresh_audit_2026-08-22/` (fetch script, driver,
pass-2/2b re-verification drivers, per-phase audit JSONLs,
`audit_report.json` + `audit_report_pass2.json` + `audit_report_pass2b.json`).

What was exercised for real: real-LLM QualityAgent reviews on real workflow
results (EV71 IRES, B2M siRNA, EPO CDS — fenced/prose JSON parsing, override
filtering, state markers); the deterministic-profile LLM bypass (zero LLM
calls); the `review_unavailable` governance path (injected LLM failure);
hard-failure pass→retry conversion on a genuinely failing run; evaluator-only
partial rerun (`run_gc=False` keeps candidates, CAI recomputed, GC falls back
to the local deterministic compute by design); user-explicit parameter
protection; a real 2-node pipeline (EV71 IRES → mRNA scoring with a bound
input) through real-LLM multi-node synthesis **with ClaimGate gating** (4
claim verdicts, REJECTED lines appended to the report, `claim_verdict` audit
events); single-node synthesis passthrough (zero LLM); CapGate enforce blocks
a failed aptamer oracle pre-invoke while allowing a *verified* GEMORNA call
through (real service response), pending-governance CRISOT never blocked,
`oracle_use("scoring_annotation")` lifts the block; ranking governance on
real runs — siRNA identical ranking under advisory/enforce/off (fresh B2M),
full-length EPO (utr5 kept/transferred, utr3 kept/unprofiled, nothing
demoted), sgrna with pending flags, aptamer on 1AKI delivering the
`ranking_evidence_unavailable` degrade with success intact and the
light-stage RhoFold filter demoted to pool order; ClaimGate scope-ladder
downgrade on a transferred-verified grade.

**Five defects found and fixed** (regressions:
`tests/test_layer4_fresh_audit_regressions.py`, 11 tests; suite 591 passed):

1. **Ranking-governance audit events were silently dropped** (the big one):
   `ranking_objective_assembly` was not in the `AuditEvent.event_type`
   Literal, so pydantic rejected every event and the best-effort writer in
   `assemble_for_workflow` swallowed the `ValidationError` — the DECISIONS
   (p) mechanism's audit trail was empty. The type is now registered
   (extend-only) and events verified in the live sirna/full-length runs.
2. **`PipelineAgent` crashed on a runtime-dangling input binding**: a plan
   that passes construction-time validation can still bind against an
   upstream node that was *skipped* (non-critical, no specialist) or produced
   no result; the unhandled `BindingResolutionError` took down the whole
   pipeline. Binding-resolution failures now degrade to a per-node failure
   with the error recorded and `critical` semantics respected.
3. **`ires_prediction` swallowed generation tool failures as "no candidates
   found"**: an IRESfinder error (e.g. missing input file) returned
   `success=True, errors=[]` — indistinguishable from a legitimate no-hit.
   Generation errors are now collected (`_generation_errors`) and surfaced as
   a hard failure; the legitimate empty-scan success=True contract (benchmark
   rubric `min_candidates=0`) is preserved and pinned by test.
4. **`SpecialistAgent` counted abandoned retry attempts**: when every
   suggested override was protected as user-explicit, `retry_count` was
   incremented although nothing re-ran. The counter now reflects real
   re-executions only.
5. **`QualityAgent` dropped quoted int-enum overrides**: LLM diagnoses
   returning `"iresfinder_mode": "2"` (string) failed the strict enum
   membership check and the retry was silently lost. All-int enum value
   lists now coerce numeric strings; string enums are untouched.

Also recorded (not defects): the packaged SelfModel has no *scoring*
capability cells (E1 profiled screening/ranking/docking only), so claims
declaring a `scoring` dependency on a profiled oracle reject as
"never profiled" — conservative and consistent with DECISIONS (e); the
`mrna_sequence_scoring` CAI annotation records a non-fatal tool warning for
non-CDS-length inputs (745-nt IRES region) while folding/GC still score.

## 2026-08-22 (b) — Layer-3 fresh-data audit: service orchestration verified on live services, degraded-service pre-flight hole fixed

First dedicated audit of Layer 3 (`agent_core/services/service_manager.py` +
`cli/service_orchestrator.py` + the `BaseDomainWorkflow` pre-flight hook) on
**live microservices and fresh real data** — sequences fetched live from NCBI
during the audit (human insulin INS mRNA NM_000207.3 + CDS, human 5S rRNA
NR_023363; CRISPR on/off-target pair derived from the INS CDS itself), nothing
reused from prior audits or fixtures. Evidence:
`workspace/layer3_fresh_audit_2026-08-22/` (fetch script, audit driver,
helper services, `audit_report.json`). **45 checks / 0 failures** post-fix;
full suite 580 passed.

What was exercised for real: health sweep over all 21 mapped services (10 up
→ all healthy, 11 down → correctly unhealthy); a genuine **cold-start** of
CRISOT (port 8011 down → `ensure_services_ready` auto-start via `start.sh` →
healthy in 5 s) followed by a real capability-layer CRISOT-Score call on the
fresh INS-derived single-mismatch pair (score 0.831); concurrent
`ensure_services_ready` from two processes on a fresh slow-start service
(real flock contention — exactly one start, both callers ready); busy-port
proceed-anyway semantics preserved with **no** restart attempt; a real
workflow pre-flight chain (`run_mrna_sequence_scoring` on the fresh INS CDS:
GC 64.6 %, MFE −50.25 kcal/mol, length 333 — biologically sane); CLI
multi-workflow orchestration.

Three defects found and fixed:

- **Degraded services passed pre-flight** (the real one): a *listening*
  service whose `/health` answers 200 with `status: "degraded"` (e.g.
  RNAsmol reporting a missing checkpoint) fell into the 2026-07-22
  busy-port proceed-anyway branch — `ensure_services_ready` returned ready
  and the workflow failed later at tool-call time with a confusing error.
  The busy branch now classifies the endpoint first
  (`_classify_service_health`): an endpoint that **answers** with a non-ok
  status (`degraded`) or an HTTP error fails pre-flight with a clear error
  naming the service; only a genuinely **unresponsive** endpoint (starved
  worker, connection refused/timeout) keeps the wait-then-proceed-anyway
  behaviour. The 2026-07-22 no-double-start guarantee is unchanged (raw
  starved listener still passes; regression-tested both ways). See
  DECISIONS.md (r).
- **`cli/service_orchestrator.__all__` listed unimported names**:
  `check_service_health` / `start_service` were exported but never imported,
  so `from cli.service_orchestrator import check_service_health` raised
  ImportError. Both now imported (re-export restored as the `__all__`
  comment intended).
- **`microservices/bowtie2_service/start.sh` shipped 100644** (all other 20
  services are 100755). Exec bit restored; a repo-state regression test now
  asserts every mapped start script exists and is executable. A stale
  orphan comment referencing the deleted junction-aware LinearDesign tool
  was also removed.

New regression tests in `tests/test_service_manager.py`: listening-degraded
service fails ensure with a `degraded status` error, listening-http-error
service likewise, all mapped start scripts executable, `__all__` exports
resolvable (36 passed in-module).

## 2026-08-22 — GenNav-λ production wiring (CDS v1.2.0), ASO → ASF (v1.1.0), CDS Pareto annotation

User-directed consistency pass, following the 2026-08-21/22 Layer-2
fresh-data audit (12/12 workflows green on live-fetched inputs — NCBI
IL-6/GM-CSF/Zika/HBB/TNF/HBA2/FMDV/rCRS + RCSB 1UBQ/430D/1NTA + PubChem;
875 audited tool calls, 0 failures; evidence
`workspace/layer2_fresh_audit_2026-08-21/`).

- **`MrnaCdsDesignWorkflow` v1.2.0**: new opt-in `navigation` input field
  (default `False`). `navigation=True` replaces the static LinearDesign
  λ=[0,1,4,10] grid with the deterministic zero-LLM GenNav-λ constraint
  navigation — pure core `agent_core/generation/gennav_mrna_lambda.py`
  (E6 λ-curve probe {0,1,2,4,8,10,20,50} → band-gap-first interstitial
  reinforcement, 16-raw budget, E14 cycling guarantee → expression /
  stability / balanced matrix delivery ×5 with D1 ≥ 0.05, domain-calibrated). Full trace in
  `_state_writeback["_gennav_trace"]`; empty delivery is the dedicated
  `navigation_delivery_empty` degrade. RNARL/GEMORNA are not called on the
  navigation path; `full_length_mrna_design` keeps the static grid
  (λ×UTR composition registered as follow-up, DECISIONS (q)). Successful
  runs now also attach the CAI × MFE/nt **Pareto frontier annotation**
  (`pareto_frontier` extras, `pareto_frontier_size` in summary,
  per-candidate `pareto_tag`) — ranking stays `total_score`.
- **`AsoTargetScreeningWorkflow` v1.1.0**: ordering mechanism converted from
  Borda rank-sum to the shared ASF reference-point ranking
  (`apply_reference_point_ranking`, accessibility × binding, utopian
  reference, uniform weights; DECISIONS (o)/(q) revision). Borda ranks
  (`accessibility_rank`/`binding_rank`/`sum_rank`) retained as diagnostics;
  missing measurements impute at pool-worst (0.0-literal fills removed);
  `asf_distance` added to scores and `AsoSite`; `pareto_frontier` extras
  attached; `composite_score` semantics unchanged (final rank, 1 = best).
- **Docs**: `DECISIONS.md` new entry (q) + (o) amendment;
  `INTERFACE_LOCKS.md` version bumps (mrna_cds v1.2.0, aso v1.1.0,
  full-length v3.1.0 lag fix); `WORKFLOWS.md` §2/§12; `AGENTS.md` ranking
  count fixed (six ASF workflows) + What's New.
- **Tests**: `tests/test_gennav_mrna_core.py` (17), new navigation wiring
  tests in `tests/test_mrna_cds_gennav.py` (4), ASO ASF tests (+4 in
  `tests/test_aso_target_screening.py`); fresh-data e2e verification on
  live services.
- **Pareto frontier consistency pass (same day)**: `sirna_design` v1.3.1,
  `sgrna_design` v1.3.1, `rna_tertiary_structure_design` v1.2.1 now surface
  the Pareto frontier the shared layer already computes (`pareto_frontier`
  extras + `pareto_frontier_size`; ordering unchanged) — previously only
  full-length/aptamer surfaced it. Adversarial testing of the surfacing
  found and fixed one defect: siRNA truncates to `candidate_count` after
  ranking, so the surfaced frontier could reference undelivered candidates
  — it is now intersected with the delivered set
  (`tests/test_asf_pareto_surfacing_adversarial.py`, 8 cases: empty pool,
  single candidate, unmeasured pool, identical candidates, dominated
  exclusion, partial measurement, truncation consistency, tertiary RMSD
  direction). Doc lags fixed: `ARCHITECTURE.md` GenNav
  paragraph (was aptamer-only), `README.md` mRNA capability row (GenNav-λ),
  `RANKING_GOVERNANCE.md` ObjectiveRef list (+ASO), ASO test-file lock header.
  Every ASF workflow now surfaces the frontier uniformly; single-objective
  workflows remain intentionally unannotated.

## 2026-08-21 (b) — Layer-1 fresh-data audit: 252 checks green, one EGARPS path defect fixed

First dedicated audit of the atomic-capability layer
(`agent_core/capabilities/base.py`, 179 lines — previously covered only
indirectly via workflow tests) on **entirely fresh real data**: sequences
fetched live from NCBI (SARS-CoV-2 Wuhan-Hu-1 Spike/N CDS, human GAPDH
UTRs+CDS, HCV 5'UTR IRES, P42212 GFP protein, J01369 yeast tRNA-Phe
mature splice) and structures from RCSB (1EHZ mmCIF/PDB, 1CVJ complex) —
nothing reused from fixtures or the earlier Layer-0 audit. Driver +
manifest: `workspace/layer1_fresh_audit_2026-08-21/` (fetch script, audit
driver, `audit_report.json`).

Coverage: 39 real tool invocations through `Capability.invoke` alone
(spans ViennaRNA ×7, CDS design ×4 incl. LinearDesign λ∈{1.0, 0.5, 1.0
repeat}, GEMORNA ×3, IRESfinder ×2 modes, CAI ×2 species, blastn/bowtie2,
CRISOT ×2, CRGPT, RNASTOP, Evitar, RhoFold, RNAsmol, GerNA-Bind, CIF
extract, interface/hotspots, EGARPS, structure alignment) plus registry
semantics, state-writeback key uniqueness (λ/species/mode-distinguished
and numeric keys, no clobber of unique payloads, plain-key latest-wins),
output_model validation fidelity (no dropped/renamed/corrupted keys, JSON
serializable), and error paths (unknown tool, bad path, non-dict
artifacts, non-serializable error payloads, enforce-mode gated call never
raises). Final state **252 pass / 0 fail**; both residual warnings were
audit-input usage errors, resolved by retry (EGARPS `academic=True`
requires DSSR/NACCESS licenses; RhoFold PDB output uses chain `0`, so
`score_structure_alignment` needs `chain_id=None` auto-detection).

Defect found and fixed:

- **`score_rna_protein_complex_with_egarps` did not resolve
  workspace-relative paths** (`agent_core/tools.py`): the wrapper posted
  `filepath` verbatim and the EGARPS+ service checks existence against its
  own working directory, so the canonical workspace-relative form 404'd
  ("PDB file not found") while blast/GC wrappers resolve client-side
  (`_absolute_path_under_project`). The wrapper now resolves before the
  POST; `input_filepath` still echoes the original argument and no locked
  return key changes. Verified live on the fresh 1CVJ complex
  (relative-path call now succeeds end-to-end through Layer 1);
  regression pinned in `tests/test_egarps_wrapper_path.py` (2 tests).
  Suite after: **541 passed, 1 skipped**.

Documented observations (behavior by design, no change): failed calls also
land in `state["tool_results"][tool_name]` (plain key is latest-wins by
design — consumers should read `CapabilityResult`/unique keys); unknown
kwargs are silently dropped by LangChain args_schema `extra=ignore`
(typo'd parameter names run with defaults — a Layer-0 schema-wide
property); enforce-mode gating is verdict-driven and context-dependent, so
a context-free gated-tool invocation may legitimately run.

## 2026-08-21 — Layer-0 fresh-data tool audit: four defects fixed, all 42 registered tools (41 scientific + 1 demo) verified callable

Full Layer-0 sweep on **entirely fresh inputs** (nothing reused from
fixtures/benchmarks; sequences typed from canonical knowledge or seeded
back-translations of real proteins, structures downloaded live from RCSB —
1EHZ/1HEL/1URN, none previously in the repo). Phase 1 exercised all 42
registered tools through the real `ToolExecutor` path with all 21
microservices up; phase 2 re-verified the fixes. Evidence:
`experiments/results/tool_layer_audit_2026-08-21/` (final state 42/42
callable; drivers + fresh inputs under `workspace/tool_layer_audit_2026-08-21/`
— deliberately outside `experiments/` so the tool-inventory AST scan keeps
classifying `workflow_demo_echo` as demo). Final suite 539 passed.

Defects found and fixed (no interface/signature/return-key changes — the
locked contracts hold; the computations inside became correct):

- **`analyze_rna_protein_interface` buried SASA always 0 on multi-chain PDBs**
  (`agent_core/tools.py`): the formula subtracted the *whole-file* SASA from
  the sum of the two selected chains, ≤ 0 whenever waters/ions/crystal copies
  are present — a real 3-copy complex (1URN, 58 contacts, 32 H-bonds) reported
  `buried_sasa=0.0`. Now computed on extracted single-chain/two-chain temp
  PDBs (1URN A+P: 1771.6 Å²). **Salt bridges were structurally always 0**: the
  detector paired protein ARG/LYS/HIS against protein ASP/GLU, which never
  occurs across a protein-RNA interface; now counts basic-residue nitrogen ≤
  4.0 Å from RNA phosphate OP1/OP2 per unique residue pair (also fixes the
  comment-vs-code 3.5/4.0 Å cutoff mismatch). The exception handler also
  referenced `logging` without an import (NameError-on-error); fixed.
- **`extract_rna_sequence_from_cif` silently dropped modified nucleotides**
  (`agent_core/tools.py`): mmCIF flags modified nucleotides as hetero, and the
  hetero skip made the documented "render as N with warning" path unreachable
  — real structures (1EHZ: 14 mod residues) came back shortened and
  position-shifted with zero warnings. Hetero residues carrying O2' are now
  kept and rendered via the base map (1EHZ: 76 nt, N at mod positions,
  warnings complete).
- **`predict_rna_protein_complex_with_proteinx` truncated multi-line FASTA**
  (`agent_core/tools.py`): only the last FASTA line was sent, so any sequence
  wrapped past 60 columns reached the service as a ~16-nt fragment
  (silently). Now joined via `_extract_sequence` (76 aa + 76 nt verified
  reaching the service; mean pLDDT 79.6→81.9).
- **CRISOT `/spec` accepted sequences of any length**
  (`microservices/crisot_service/main.py`): 20-nt spacer rows were silently
  scored while `/score` enforces 23 nt (upstream reads only positions 1–20,
  so the result *looked* plausible). `/spec` now validates and normalizes
  every On/Off row to the same 23-nt (spacer+NGG PAM) rule with a row-numbered
  400 on violation; 23-nt results are bit-identical to before (upstream
  ignores positions 21–23). The sgRNA workflow degrades to
  `crisot_specificity=None` + warning on short rows (verified by test data +
  negative control).

Also: **RhoDesign service gains a PDB sanitizer**
(`microservices/rhodesign_service/main.py`) — upstream RhoDesign crashes with
a bare length assertion on any crystal PDB containing waters/ions/modified
residues (biotite counts 602 residues vs 245 coordinate groups for 1EHZ). The
service now rewrites the input keeping nucleotide residues only (drops
waters/ions/ligands/altlocs, maps modified nucleotides to parent bases) before
inference; 1EHZ now designs a 76-nt sequence recovering the native tRNA^Phe
almost exactly. Tests: `tests/test_tool_layer_fixes_2026_08_21.py` (5).
`docs/TOOLS.md` interface-analysis metric table updated.

## 2026-08-21 — Ranking governance: ASF objectives assembled from CapGate verdicts

Implements [`RANKING_GOVERNANCE.md`](RANKING_GOVERNANCE.md) (DECISIONS (p)):
the shared ASF ranking layer now consumes the DecisionGate verdict as a
first-class input, closing the pre-existing gap where advisory mode ranked by
metrics CapGate had falsified while enforce mode crashed workflows (or
silently returned generation order).

- **New module**: `agent_core/calibrated/objective_assembly.py` — pure,
  deterministic verdict→action mapping (verified → keep;
  transferred-verified → keep + flag; failed → demote to
  `scoring_annotation` pool-wide equally; pending → keep + flag;
  unprofiled-enforce → keep + flag; deterministic compute never enters).
  Assembly is **mode-independent** (never reads `RNADA_CAPGATE`);
  `RNADA_CAPGATE=off` disables the whole mechanism. One
  `ranking_objective_assembly` audit event per run; state in
  `_state_writeback["_ranking_governance"]`.
- **`RnaAptamerDesignWorkflow` v2.2.0**: all three ASF objectives are
  demoted under the packaged SelfModel → new
  `ranking_evidence_unavailable` degrade (success=True, generation order,
  annotations intact, no fabricated `asf_distance`; marker never enters
  `errors` since non-empty errors is a hard failure). Light-stage RhoFold
  pLDDT top-k filter degrades to deterministic pool order when the screening
  profile is failed; gated oracle calls (`GatedActionError`) are
  expected-missing annotations (gated ProteinX no longer raises).
- **`FullLengthMrnaDesignWorkflow` v3.1.0**: objectives assembled before
  ranking (`utr5_mrl` transferred-verified flag, `utr3_stability`
  unprofiled — its source is `gemorna_3utr_stability`, which has no records;
  RNASTOP's `overall_stability` is a diagnostic, not an ASF dim); reference
  points naming demoted keys are explained in `asf_ranking_note`.
- **siRNA / sgRNA / tertiary**: structural no-ops (all-compute / pending /
  unprofiled-under-task-key) — additive `_ranking_governance` state only.
- **Deferred (registered)**: continuous profile-derived ASF weights —
  blocked on SelfModel coverage and cross-family validation.
- **Tests**: `tests/test_ranking_governance.py` (15 tests: per-workflow
  assembly pinning, mode independence, off escape hatch, aptamer degrade
  path, gated-error recognition, no-op regression); full suite 534 passed.

## 2026-08-20 (b) — ASF audit fixes + shared ranking layer generalized to five workflows

User-directed audit of the Achievement Scalarizing Function (ASF) ranking
strategy (the ordering mechanism of the flagship workflows) found four
defects; all fixed, and the (now single) implementation promoted to the
default ranking layer of every genuinely multi-objective workflow. Full
rationale and policy: [`DECISIONS.md`](DECISIONS.md) (n).

- **Fixed (ranking-fairness)**: a per-candidate *missing* objective used to
  be omitted from that candidate's Chebyshev max — omission can only lower
  ASF, so per-candidate evaluation failures were *rewarded* (extreme case: a
  candidate measured on only its champion dimension could win with ASF 0).
  Missing dimensions now impute at the measured pool-worst value; imputation
  uses the measured minimum so it no longer distorts the min-max
  normalization of measured candidates. The aptamer/siRNA 0.0-literal fills
  were replaced by `None` + the same imputation.
- **Fixed (semantics)**: a partial user `reference_point` silently collapsed
  the ranking onto the supplied subset; it still restricts the ranking but is
  now flagged (`asf_ranking_note` in the summary + warning log). Pool-wide
  unmeasured dimensions (CapGate-enforced oracle blocks, optional evaluators
  off) drop for everyone equally and are reported the same way.
- **Deduplicated**: the ~100-line ASF loop existed twice (full-length mRNA +
  aptamer, line-identical); both now call
  `workflows/multi_objective.py::apply_reference_point_ranking`.
- **Generalized**: `SirnaDesignWorkflow` (v1.2.0; ASF over
  efficiency/specificity, Borda ranks become diagnostics),
  `SgRnaDesignWorkflow` (v1.3.0; ASF over nn/crisot/crisot_specificity,
  existing `weight_*` inputs renormalized as ASF weights),
  `RnaTertiaryStructureDesignWorkflow` (v1.1.0; ASF over
  rhofold/rmsd; RMSD drops pool-wide in de-novo runs). Score functions and
  all output keys unchanged (`total_score` etc. remain reported diagnostics);
  single-objective / n=1 / domain-formula workflows intentionally not
  converted (cds combined score, sequence scoring, IRES, ASO, secondary
  structure, small molecule).
- **Tests**: 10 new shared-layer regression tests (imputation parity with
  measured pool-worst, partial-ref flagging, pool-wide dim drop, weight
  renormalization, utopian balanced-preference, degradation edges); suite
  506 passed (baseline 496), all existing pins green.
- **Docs**: WORKFLOWS.md §2 shared ASF ranking policy + per-workflow ranking
  notes; INTERFACE_LOCKS.md §10/§11/§12/§14/§15 updated with bumped versions;
  PAPER_DRAFT.md Methods gains the ASF description.
- **Follow-up (same day, post-audit of the three new ASF workflows)**:
  (i) siRNA now **ranks the full passing pool before truncating** to
  `candidate_count` — the pre-existing truncate-then-rank order could drop
  the pool's best window beyond position N in generation order before it was
  ever ranked (regression test pins the surfacing case);
  (ii) tertiary structure gains the **TM-score ranking dimension**
  (`tm_component`, injected at ranking time from the alignment TM-score;
  new additive `weight_tm_score` input; lock v1.2.0) — TM stays
  informative where RMSD saturates ≥ 5 Å;
  (iii) tertiary **default weights rebalanced to 0.3/0.5/0.5**
  (`weight_rhofold` below the closeness weights) — the audit experiment
  showed uniform thirds let a pLDDT champion bury the native-closest
  candidate under pool-relative min-max; the defaults now implement the
  documented guidance;
  (iv) **siRNA thermodynamic end asymmetry** (Khvorova 2003 / Schwarz 2003):
  the sirna-duplex service endpoint (v0.5.0) now also returns the terminal
  5-bp nearest-neighbour end stabilities and
  `asymmetry = ΔG(antisense 5′) − ΔG(sense 5′)` (higher = preferential
  guide loading; RNAlib path with RNAeval CLI fallback, zero additional
  folding), the tool wrapper passes the additive keys through
  (older-service tolerant), and `asymmetry_component` joins the siRNA ASF as
  a third dimension (lock v1.3.0; linear map −3→0 / 0→0.5 / +3→1; drops
  pool-wide without measurements).

## 2026-08-20 — paper_v5 figure rebuild (Nature Methods conventions, survey-driven)

User-directed figure programme for the manuscript. A systematic survey of
seven Nature/Science agent-system papers (`relevant_references/`; inventory in
[`REFERENCE_FIGURE_SURVEY.md`](REFERENCE_FIGURE_SURVEY.md)) fixed the design
vocabulary: Fig 1 architecture + five results figures of 9 panels each, muted
Morandi palette with a strict arm-to-colour code, Arial throughout, per-paper
recurring panel types (capability heatmaps with printed values, paired
discordance mosaics, delivery maps, audit telemetry, annotated iteration arcs).

- **New figure set**: `experiments/plots/paper_v5/` — one script per panel
  (51 panels) + shared `style.py` / `data.py` / `schematic.py`; `assemble.py`
  composes vector PDFs + 450-dpi PNG proofs and draws panel letters at
  assembly time only. Plan: [`FIGURE_PLAN_V5.md`](FIGURE_PLAN_V5.md); build
  and QA recipes in the directory `README.md`.
- **Objective QA gate**: `qa_bounds.py` asserts every text/tick/title artist
  sits inside its figure (catches clipping deterministically); all 51 panels
  pass, plus per-figure vision-model checks (overlap, palette, letters).
- **Panels re-derive numbers from retained evidence** — every quantitative
  panel reads `experiments/results/` verdict files or the live
  `workspace/audit/platform_audit.jsonl` (5,747 events: 4,530 tool calls +
  1,217 gate decisions). Two documented exceptions carry provenance comments
  (RNAsmol pre-fix AUROCs; E11 simulation P values).
- `docs/PAPER_DRAFT.md` bumped to v4.4: panel references updated to the v5
  lettering (Fig 2g→h/2h→i, 3f→h, 3g→f, 3h→i, 4g→h, Fig 1b/c remapped).

## 2026-08-19 (batch-B) — fresh-data full-platform re-verification + session-stamped audit trail

User-directed second verification pass ("换一批数据，再重新测一次"): a
**fresh-data batch** of 12 new process-aware regressions (PA_025–PA_036,
`pa_benchmarks.json`) — every input differs from PA_006–PA_024 (new viral
targets, guides, aptamer targets, RNA–ligand pairs, ASO targets, authentic
IRES-positive 5'UTRs, fresh 3D structures and proteins), including two
GenNav `navigation=true` campaigns. **12/12 passed, 0 failed turns**
(evidence: `experiments/results/pa_regression_batchB_2026-08-19/`,
`VERIFICATION.md`). One authored-data incident (PA_035 start-sequence
length mismatch) was correctly rejected at the input layer and passed after
fixture repair. Both navigation campaigns delivered 5/5 in all three
profiles with no degrade: 1CA2 walked the full 47/48 budget with 5 cycling
guarantee rounds; 3CNA hit the early-stop rule at 35/48 — both allocation
paths verified live.

- **Audit session attribution**: `tool_call` audit records now carry
  `session_id` + `task_type` (`CalibratedRuntime.record_tool_call` stamps
  the context-propagated session and calling-workflow task), so every audit
  line maps to the run that produced it. Bug fix enabling this on the CLI
  path: `AgentRunner.stream_form` executes the pipeline in a worker thread,
  which does not inherit contextvars — it now runs the thread body under
  `contextvars.copy_context()` (`agent_core/runner.py`). `should_block`
  dropped its vestigial optional `tool_name` argument.
- **New git-tracked fixtures** (`data/benchmarks/README.md`): single-record
  `emcv_5utr.fa` (840 nt) and `poliovirus_5utr.fa` (742 nt) extracted from
  the IRES external-anchor panel — the first authentic IRES-positive inputs
  in the PA registry (mode-0 scans reproduced the fig2i literature scores,
  EMCV 0.808 / poliovirus 0.891).
- **Docs**: `MANUSCRIPT.md` PA registry rows now cover 006–036 and the 496
  test baseline; `AGENTS.md` testing section updated; paper draft → v4.3.

## 2026-08-19 — GenNav production wiring + full-platform end-to-end verification

User-directed verification pass ("is every workflow end-to-end successful,
are CapGate and GenNav working, is everything auditable") plus the completion
of the GenNav innovation's production path.

- **GenNav wired into the aptamer workflow** (`RnaAptamerDesignWorkflow`
  v2.1.0): new opt-in input field `navigation` (default `False`, static gear
  unchanged). The navigation path runs the E14 decisive protocol end-to-end
  and deterministically (zero LLM): 17-length lattice probe (seed 42) →
  cycling guaranteed-repair reinforcement (Laplace rates, seeds 7/99, ≤6 per
  round, 48-raw cap, early stop when every profile is deliverable) →
  per-profile mechanized delivery (matrix v3 + D1 greedy top-5, explicit
  degrade). The pure-function core
  (`agent_core/generation/gennav_aptamer.py`) gained the constraint-matrix
  and delivery functions (matrix v3 constants, GC/stem/homopolymer
  evaluation, normalized Levenshtein, `deliver_profile`); gear-sampled
  semantics fixed to cumulative depth (E14 addendum v2).
  `required_capabilities` gained
  `predict_rna_secondary_structure_with_linearfold` (constraint-matrix
  folding; audited through the capability layer like every other call). The
  full navigation trace (probe, rounds, final gaps, per-profile deliveries)
  is written to `_state_writeback["_gennav_trace"]`; delivered candidates
  carry `nav_bands` / `nav_gear` / `nav_matrix_pass` metadata into the
  standard evaluation + ASF ranking; a run with zero matrix-passing
  candidates fails with the dedicated `navigation_delivery_empty` error.
  Tests: `tests/test_rna_aptamer_gennav.py` (7 tests: probe coverage,
  budget cap, early stop, guarantee-band starvation, matrix/D1 delivery,
  run() integration, default-off path). The mRNA-side λ-lattice navigation
  (E6, P = 1.9e-09) remains validated campaign machinery — its driver was
  deleted in the simplification pass and the mechanism-identical levers
  live in the distilled core.
- **GenNav live verification** (real services, GPU 0, no caches): one
  full navigation campaign on VEGF (1vpf) through the form-driven CLI —
  raw_spent 41/48 with early stop, compact 5/5 + standard 5/5 + extended
  4/5 delivered (the extended shortfall an explicit degrade), 4
  guarantee-kind reinforcement rounds, 172 audited tool records.
  Evidence: `experiments/results/gennav_live_verification_2026-08-19/`.
- **CLI artifact lock v2.3.0 → v2.4.0**: the result JSON now carries the
  optional `_gennav_trace` navigation audit record (present only on
  navigation-mode runs); pinned by
  `tests/test_cli_candidate_dict.py::test_save_workflow_results_persists_gennav_trace`.
- **Full-platform end-to-end regression re-run**: agent-core suite 496
  passed; PA_006–PA_024 (all 11 workflows, user input → final design
  result) re-run against the gated platform on GPU 0 — 19/19 benchmarks,
  0 failed turns (summary archived at
  `experiments/results/pa_regression_2026-08-19/summary.tsv`). CapGate
  audit trail verified on the live runs: every tool call recorded
  (`workspace/audit/platform_audit.jsonl`), managed oracles reviewed
  (advisory runs review + audit without blocking; enforce-mode blocking
  verified from the earlier enforce-era records), CRGPT pending-governance
  verdicts recorded as `require_profiling` without block.

## 2026-08-18 — system simplification: BMC removed, dead tools purged, concluded experiment drivers archived away

User-directed cleanup (code is the source of truth; superseded strategies are
deleted rather than kept for compatibility). Baseline before: 709 tests /
102,673 lines of Python. After: 488 tests / ~51,000 lines, all green, plus a
full PA_006–PA_024 end-to-end rerun.

- **BMC framework removed** (`CoordinatorAgent`, `workflows/coordinator.py`,
  the `bmc_*` interface on `FullLengthMrnaDesignWorkflow` /
  `RnaAptamerDesignWorkflow`, `bmc_mode` / `bmc_max_rounds` /
  `bmc_improvement_threshold` input fields, `_bmc_trace` audit plumbing in
  runner/CLI/storage/schema). Rationale: the coordination-gain narrative was
  triple-falsified (P0 budget-matched, P3 guided-vs-unguided, Fig 5 b/c —
  DECISIONS.md (a), (m)) and the P0 budget-matched control showed serial
  generation at equal budget is statistically indistinguishable, so removal
  costs no measured performance. Both workflows now run the standard
  generate → evaluate → score → ASF/Pareto rank path with per-run state
  writeback intact (`_workflow_params`, full tool trace — auditability
  unchanged). LOCK §14 → v3.0.0, §15 → v2.0.0.
- **Twelve dead tools removed** (54 → 42 registered specs): the two
  experiment-only junction tools (`design_mrna_cds_junction_aware_with_lineardesign`
  — P2 NO-GO, never wired; `shuffle_cds_junction_codons` — junction
  auto-repair strategy falsified, DECISIONS.md (b)) and the ten reserved
  wrappers (six CRISOT suite alternates, LinearFold evaluate/zuker modes,
  batch LinearDesign, codonw-slim). Matching microservice endpoints and the
  whole `codonw_slim_service` were deleted; CRISOT service now serves
  `/health` `/score` `/spec`, LinearFold serves `/fold`, LinearDesign serves
  `/generate/cds`. `tool_inventory.py` reservations emptied;
  `tests/test_tool_ontology.py` pins updated (41 production / 1 demo).
- **Calibrated-stack experiment machinery removed**
  (`calibrated/profiler.py`, `experiment_planner.py`, `campaign_runner.py`,
  `case_memory.py` — the E1/E3-era campaign stack; the E4 memory strategy was
  NO-GO and abandoned, DECISIONS.md (c)). The production CapGate stack
  (`runtime.py`, `self_model.py`, `decision_gate.py`, `claim_gate.py`,
  `audit_trail.py`, `models.py`, `profiling_metrics.py`) is unchanged.
- **Concluded experiment drivers archived away** (E1–E15 gennav/BMC/junction/
  literature/backends drivers, probes, one-off repair scripts, `analysis/*`
  except `stats_utils.py`, `plots/*.py`, `lit_cache/`, `e3/`, `e3_mrna/`).
  Kept in `experiments/`: `run_platform_quality_benchmark.py` (fig2 E2E
  driver — the registered RNADesign-210 regeneration path),
  `run_e16_e17_e18_oracle_profiling.py` + `curate_e16_e17_e18_anchor_sets.py`
  + `curate_e7_mrl_anchor_set.py` (live profiling infrastructure),
  `build_default_self_model.py` (packaged SelfModel provenance),
  `analysis/stats_utils.py` (production dependency), and the complete
  `results/` evidence tree. The E14-validated aptamer GenNav strategy survives
  as the distilled pure-function core
  `agent_core/generation/gennav_aptamer.py` (behaviour pinned by
  `tests/test_gennav_aptamer_core.py`).
- **Dead scoring framework removed** (`workflows/scoring.py` reduced to
  `FullLengthScoringFunction`, renamed from `FullLengthBMCScoringFunction`;
  the unused `ScoringFunction` ABC, `MrnaCdsScoringFunction`,
  `SirnaRankScoringFunction`, `SgRnaScoringFunction`, `normalize_score`,
  `safe_divide` exports are gone). `multi_objective.py` lost its BMC-only
  helpers (`compute_violation`, `build_normalized_reference_point`).
  `workflow_run_storage.py` reduced to the production-used
  `build_public_summary` (the never-wired request/result persistence
  machinery is gone; per-run audit remains the CLI result JSON + CapGate
  platform audit trail).
- **Bug fixes**: (1) `SirnaDesignInput.bowtie2_ma` was typed `int` with a
  `'mode-dependent'` string default (pydantic serialization warning on every
  run); now typed `str` like its sibling `bowtie2_i`. (2) The PA benchmark
  static fixtures (`ns1_strains.fasta`, `sarscov2_nsp12_strains.fasta`,
  `epo_mrna.fa`, `ttr_mrna.fa`) had been lost with an untracked `workspace/`
  clean — rebuilt from NCBI records (`NC_00147{7,4,5}.1/-2/NC_002640.1`
  dengue NS1; `NC_045512.2` + Evitar local isolates nsp12; `NM_000799.3`
  EPO; `NM_000371.4` TTR) and moved to the git-tracked
  `data/benchmarks/RNA-BioBench-ProcessAware/fixtures/` with `pa_benchmarks.json`
  repointed (provenance in `data/benchmarks/README.md`). Note the GenBank
  SARS-CoV-2 nsp12 mat_peptide join overlaps 1 nt at the frameshift — extract
  the direct ORF1ab slice, never `feature.extract()`. (3) The PA driver now
  defaults its CLI subprocesses to `RNADA_CAPGATE=advisory` so enforce-mode
  oracle gating (registered E16–E18 consequence) does not fail process-aware
  regressions; production default remains `enforce`. (4) AGENTS.md's live-e2e
  instruction for `test_full_length_mrna_e2e_live.py` said `python <file>`
  which is a silent no-op — it is a pytest module.

## Earlier 2026-08-18 era (before the simplification pass)

Same day, in order: (a) platform CapGate runtime production integration
(`CalibratedRuntime`, `RNADA_CAPGATE` off|advisory|enforce default enforce,
packaged 24-record SelfModel); (b) oracle ontology + tool inventory
(`ToolSpec.kind` + `OracleDescriptor`, pending tier, `tool_inventory.py`
manifest); (c) task-keyed DecisionGate gating (W1.2) + the
microservice-internal oracle-hop audit boundary (DECISIONS.md (k)); (d)
E16/E17/E18 profiling campaigns — IRESfinder / GerNA-Bind / RNASTOP all
failed their declared-use gates and flipped pending → enforce (packaged
SelfModel now 29 records); CRISOT-Spec wiring (`SgRnaDesignWorkflow` v1.2.0,
`calculate_crispr_specificity_with_crisot` production); GenNav aptamer core
extraction (`agent_core/generation/gennav_aptamer.py`).

## Current locked-interface state

See [`INTERFACE_LOCKS.md`](INTERFACE_LOCKS.md) for the canonical table. Tool
count: 42 registered specs (41 production + 1 demo). Workflows: 11, all
plain `BaseDomainWorkflow` implementations (no BMC interface anywhere).
