# Change Log

> **Scope**: locked interface changes and major workflow introductions.
> **Last updated**: 2026-08-18

> **History policy (2026-08-18)**: this log now records only the current
> interface state and the most recent change era. The detailed per-day ledger
> through 2026-08-18 was purged in the 2026-08-18 simplification pass; the
> experimental arc (what was tried, what was falsified, with evidence
> pointers) lives in [`DECISIONS.md`](DECISIONS.md), and every experiment's
> raw verdicts live under `experiments/results/`.

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
