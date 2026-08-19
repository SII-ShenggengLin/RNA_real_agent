# Change Log

> **Scope**: locked interface changes and major workflow introductions.
> **Last updated**: 2026-08-19

> **History policy (2026-08-18)**: this log now records only the current
> interface state and the most recent change era. The detailed per-day ledger
> through 2026-08-18 was purged in the 2026-08-18 simplification pass; the
> experimental arc (what was tried, what was falsified, with evidence
> pointers) lives in [`DECISIONS.md`](DECISIONS.md), and every experiment's
> raw verdicts live under `experiments/results/`.

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
