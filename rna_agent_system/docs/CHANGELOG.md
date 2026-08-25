# Change Log

> **Scope**: interface changes and major workflow introductions.
> **Last updated**: 2026-08-22

> **History policy**: this log records the current interface state and a
> condensed register of the most recent change eras. Full narratives live in
> git history and the audit-evidence directories cited per entry; the
> experimental do-not-repeat register is [`DECISIONS.md`](DECISIONS.md).

## 2026-08-22 (i) — Repo-wide simplification pass: workspace scratch isolation, demo tool retired, historical outputs purged

User-directed cleanliness pass over everything outside `external_repos/`
(code as the source of truth, no git archaeology):

- **Test-suite workspace leak fixed (real bug).** Every test run leaked
  scratch artifacts (`save_sequence` / `save_text_file` without a session
  context) into the real `workspace/` root — **141k files / 1.3 GB**
  accumulated. `tests/conftest.py` now redirects all default workspace bases
  to a per-run `workspace/_tests` scratch (removed afterwards); the redirect
  is inherited by subprocesses via the new `RNADA_WORKSPACE_BASE` env
  override honoured by `WorkspaceManager.__init__` (also useful for
  deployments). Literal-path test writers (`test_compute_*`) now write into
  the isolated base. Verified: full suite runs leave zero new files in the
  workspace root.
- **Demo tool removed**: `workflow_demo_echo` and the
  `build_default_tool_registry(include_demo=...)` parameter are gone —
  **41 registered tools, all production** (manifest regenerated:
  `experiments/results/tool_inventory.json`). Tests use local mock tools.
- **Layer-4 test dedup**: the identical QualityAgent retry-semantics blocks
  duplicated across the secondary/tertiary layer-4 modules moved to one
  parametrized module (`tests/test_layer4_agent_semantics.py`).
- **Documentation dedup in code**: 39 `tools.py` wrapper docstrings dropped
  their `Args/Returns/Raises` sections (verbatim duplicates of the Input-model
  `Field` descriptions); stale comments referencing deleted experiment
  drivers removed (`tools.py`, `evaluators.py`, `rna_aptamer_design.py`).
- **Historical outputs purged**: superseded figure generations
  (`experiments/plots/{paper,paper_v4,fig*_panels,fig*.png}`, ~24 MB),
  archived experiment rounds (`e5_s1_*_archive/`, `e14_audit_v{1,2}/`,
  versioned `e14/e8` re-run files, `codon_tables_e6/`, ~12 MB), orphaned
  `__pycache__`, and 141k leaked workspace scratch files + stale service-run
  intermediates (`workspace/*_service_runs` contents, 634 MB of RhoFold
  intermediates). **Repository shrank from 4.3 GB to 2.0 GB** (the remainder is dominated by 1.2 GB of required reference-genome data and the retained audit trail). Everything
  under `workspace/{audit,sessions}/` and every `*_fresh_audit_*` evidence
  directory is retained (audit trail untouched).
- Codonw-slim stub entries still present in two full-length-mRNA test files
  were removed with their tool (deleted 2026-08-18).
- Suite after the pass: **635 passed, 1 skipped** (the −1 is the merged
  demo-registration test); PA_006–PA_019 re-run green end-to-end.

## Condensed register: the 2026-08-18 → 2026-08-22 era

Each row: what changed, the defect count fixed on live-fetched data, the
evidence directory, and the DECISIONS.md entry. Suite counts are the
post-entry regression-suite size.

| Date | Change | Evidence | DECISIONS |
|------|--------|----------|-----------|
| 08-18 | System simplification: BMC framework removed after triple-falsified coordination gain; 12 dead tools purged (54→42 specs) + codonw_slim_service; E1–E15 experiment machinery and drivers deleted (evidence JSONs kept); bowtie2_ma type fix | git `1b45138` | (a), (m) |
| 08-19 | GenNav constraint navigation became the production opt-in on `rna_aptamer_design` v2.1.0 (`navigation` field; deterministic, zero-LLM; full trace in `_state_writeback["_gennav_trace"]`); batch-B fresh-data re-verification (PA_025–PA_036, 12/12); `tool_call` audit lines now carry `session_id` + `task_type` | `experiments/results/pa_regression_batchB_2026-08-19/`, `gennav_live_verification_2026-08-19/` | (n) |
| 08-20 | ASF/Pareto ranking generalized to five workflows + adversarial surfacing tests; paper_v5 figure programme (51 panels, `experiments/plots/paper_v5/`) | `docs/FIGURE_PLAN_V5.md` | (o) |
| 08-21 | Ranking governance: ASF objectives assembled from CapGate verdicts (deterministic, mode-independent; `agent_core/calibrated/objective_assembly.py`; `RNADA_CAPGATE=off` disables); Layer-0 tool audit (4 defects, e.g. EGARPS posting workspace-relative paths); Layer-1 capability audit (252 checks, EGARPS path fix); Layer-2 workflow audit (12/12 green on live-fetched data) | `workspace/tool_layer_audit_2026-08-21/`, `layer1_fresh_audit_2026-08-21/`, `layer2_fresh_audit_2026-08-21/`, `docs/RANKING_GOVERNANCE.md` | (p), (k) |
| 08-22 (b) | Layer-3 service-orchestration audit (45 checks, 3 defects: degraded-service pre-flight hole, `__all__` export bug, missing exec bit) | `workspace/layer3_fresh_audit_2026-08-22/` | (r) |
| 08-22 | GenNav-λ production wiring on `mrna_cds_design` v1.2.0 (`navigation` field replaces the static λ grid); ASO ordering converted to shared ASF ranking (v1.1.0, Borda → diagnostics); CDS runs attach the CAI×MFE/nt Pareto annotation | `tests/test_gennav_mrna_core.py` etc. | (q) |
| 08-22 (c) | Layer-4 multi-agent + CapGate + ranking-governance audit (5 defects: dropped ranking audit events, pipeline crash on dangling bindings, IRES swallowing tool failures, retry counting, int-enum overrides) | `workspace/layer4_fresh_audit_2026-08-22/` | (s) |
| 08-22 (d) | Layer-5 persistence audit (3 WorkspaceManager defects: `delete_session("")` rmtree of the sessions tree, unvalidated session-id path joins, `list_files` creating directories) | `workspace/layer5_fresh_audit_2026-08-22/` | (t) |
| 08-22 (e) | Layer-6 façade/CLI/API audit (6 defects: pipeline session-scoping leak, API success misreporting, task_id echo, dropped progress events, dead step events, bare `input()` on the non-tty pipeline path) | `workspace/layer6_fresh_audit_2026-08-22/` | (u) |
| 08-22 (f) | Interface Lock Policy removed repo-wide (~1,250 lines pure deletion; behavioural contracts remain pinned by `WORKFLOWS.md`, the regression suite and the PA drivers) | — | (v) |
| 08-22 (g) | Oracle version stamps: all 11 managed-oracle descriptors declare `oracle_version`; packaged SelfModel records carry the profiling-time stamp; drift warns + audits, never blocks | `tests/test_oracle_version_stamps.py` | (w) |
| 08-22 (h) | Full-platform E2E fresh-data audit — whole stack, all 11 workflows through all three entry points (56 checks; 3 defects: opaque sgrna seed failure, `stream_form` raising on hard failure, ViennaRNA inverse-fold accepting pseudoknot brackets → SIGSEGV) | `workspace/e2e_fresh_audit_2026-08-22/` | (x) |
| 08-22 (i) | Repo-wide simplification pass (this entry) | — | (y) |

## Current interface state

- **Tool count**: 41 registered specs, all production (`python -m
  agent_core.tool_inventory`).
- **Workflows**: 11, all plain `BaseDomainWorkflow` implementations; six rank
  by Achievement Scalarizing Function (DECISIONS (o)/(q)); GenNav navigation
  is an opt-in on `rna_aptamer_design` (length lattice) and `mrna_cds_design`
  (GenNav-λ).
- **Microservices**: 21 mapped services, ports 8003–8024.
- **No BMC interface anywhere**; no automatic workflow router — selection is
  explicit (CLI menu / `--workflow` / `explicit_workflow` / `--pipeline-file`).
- **Governance**: `RNADA_CAPGATE` = `off|advisory|enforce` (default
  `enforce`); packaged SelfModel 29 records; the CapGate audit trail lives at
  `workspace/audit/platform_audit.jsonl` (every `tool_call` line stamped with
  `session_id` + `task_type`).
