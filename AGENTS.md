# Agent Guidelines for RNA_real_agent

> **Consolidated index.** Authoritative documentation lives in `rna_agent_system/docs/`.
> **Last updated**: 2026-08-27 (experiment-programme reset + Exps 1–8 executed)

## What's New

- **Exp 8 (Fig 2h) executed** (2026-08-27, zero-intervention rule): end-to-end runtime by workflow (`experiments/exp8_runtime.py` + orchestrator `experiments/exp8_run_all.sh`, pre-registered docstring, pilot 4/4). Instrument = one CLI form subprocess per run through the user entry, inputs verbatim, no thresholds, CapGate advisory (regression convention), services pre-warmed GPU-pinned 0/1/2 (measures the delivered workflow, not cold model loads), lanes strictly sequential against cross-lane contention. Sample = **241 runs: all 210 RNADesign-210 tasks + all 31 PA regression sessions (each timed as one whole form session). 241/241 successful.** Pooled median 2.6 min; workflow medians 2.5 s (mRNA scoring) → 6.29 min (aptamer); 76.3% ≤5 min, 92.9% ≤10 min, **240/241 ≤1 h** — the four >30-min runs are all multi-turn aptamer PA sessions, the single >1 h being the GenNav `navigation=true` session PA_028 (98.6 min). **Disclosed amendment (registered before the PA_028 re-run)**: PA-arm timeout 3600→10800 s — the registered budget was calibrated on suite-task maxima and under-covered multi-turn navigation sessions (PA_027 finished at 3593 s; PA_028 was killed at 3600 s while progressing normally, and the timeout's kill-only-the-child semantics orphaned its turn-2 grandchild, which then completed — driver fixed to kill the process group); PA_028 re-run once under the amended budget (5917.2 s, consistent with the ~5740 s orphan reconstruction), original censored record retained in `pa_batch.jsonl`; orphan-overlap window verified uncontaminating for PA_029. Figure `experiments/plots/fig2h_runtime_ecdf.py` → `fig2h_runtime_ecdf.{pdf,png}` (log-axis ECDF per workflow + box inset, 1 h reference line, right legend with medians; palette rev 7 unchanged). `PAPER_DRAFT.md` Fig 2h legend + Results sentence, `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row h, `MANUSCRIPT.md` reset table updated.
- **Exp 7 (Fig 2g) executed** (2026-08-26, zero-intervention rule): RNAsmol small-molecule oracle two-sided boundary re-run (`experiments/exp7_rnasmol_boundary.py`, pre-registered docstring, pilot 37/37). Instrument = the deployed microservice as the platform ships it (CPU default via its own `start.sh`), one call per pair, **case-preserving verbatim inputs** (the official held-out splits encode modified bases in lowercase; the agent tool layer's uppercase+T→U normalization would re-introduce the v0.2.0 fidelity-defect class, so the service endpoint is the fidelity-correct instrument — the retained evidence's protocol; checkpoint auto-selection by data-provenance hints only, no thresholds). **3,545/3,545 pairs scored, 0 failures — every registered metric of the retained 2026-08-11 evidence reproduced exactly**: robin test AUROC 0.9744 (0.9678–0.9803), pdb test 0.9828 (0.9607–0.9970; ≤500-nt subset 0.9788, 44 truncated service-side); decoy true-binder ranks 2/1601 and 7/265; OOD short-aptamer panel 0.7222 (0.2778–1.0) vs random-chem and 0.5625 (0.0625–1.0) vs near-cognate — both CIs span chance. Per-pair cross-check vs the retained JSONL: medians ~1e-6; one unstable near-0.5-band FMN decoy diverges 0.367 under backend arithmetic (re-scored bit-identical — this run's determinism verified; the retained run's device is unrecorded); cross-check tolerance amended from bit-level to 4-decimal-AUROC + decoy-rank **before** the full run (disclosed in the docstring). Figure `experiments/plots/fig2g_rnasmol_boundary.py` → `fig2g_rnasmol_boundary.{pdf,png}` (forest dot + CI; khaki in-dist / dark-warm-grey OOD; chance + 0.8 gate reference lines; palette rev 7 unchanged). `PAPER_DRAFT.md` Fig 2g legend + Results, `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row g, `MANUSCRIPT.md` reset table updated.
- **Exp 6 (Fig 2f) executed** (2026-08-26, zero-intervention rule): siRNA off-target scanning re-run on the RNADesign-210 `04_sirna_design` sub-benchmark (`experiments/exp6_sirna_offtarget.py`, pre-registered docstring, pilot 5/5, advisory CapGate; task inputs verbatim — scan flags come from the inputs: 19 disabled, 3 requested). Single arm = the `sirna_design` golden path as-is; primary metric = predicted off-target hits of the delivered (best-ranked) candidate. **22/22 runs, 0 failures (wall 58.8 min); 21/22 zero predicted off-targets** — sole nonzero: task 013 (bowtie2, identity-70 input) 3 hits, reproducing the Exp-1 lane exactly. Scan evidence is trace-verified, not assumed (record fields `scan_requested`/`scan_executed`): 2 tasks executed transcriptome scans against GENCODE v46 (003 BLAST zero hits; 013 bowtie2 3 hits); task 021 requested a scan but `sars_cov_2` ships no transcriptome reference — graceful skip. Figure `experiments/plots/fig2f_sirna_offtarget.py` → `fig2f_sirna_offtarget.{pdf,png}` (lollipop vs zero line; siRNA slate blue = zero, held-out dark warm grey = nonzero, diamond = trace-verified scan, legend built from the observed combos 20/1/1; palette rev 7 unchanged). `PAPER_DRAFT.md` Fig 2f legend + Results sentence refreshed with the scan-evidence reading.
- **Platform fix: species-resolved LinearDesign codon tables + Exp 2+3 re-run** (2026-08-25, user-reported defect): `cai_species` previously reached only the CAI evaluator — LinearDesign always designed against its bundled human table. Now 11 Kazusa-derived LinearDesign CSVs ship with the platform (`agent_core/data/codon_usage_lineardesign/`, generator `scripts/gen_lineardesign_codon_tables.py`), wired into `mrna_cds_design` on both the golden path and GenNav navigation (explicit `lineardesign_codon_usage_path` still wins; unresolvable species fail fast at input; `full_length_mrna_design` inherits via delegation; audit trail records the table per call). Exp 2+3 re-run: **20/20 + 240/240, 0 failures; CAI medians 0.832/0.729/0.674** (designed-vs-WT P=6.9e-4 δ=0.63; WT-vs-random P=6.8e-7 δ=0.67); MFE/nt −0.336/−0.051/−0.047 (δ=−1.0 vs both nulls; WT-vs-random NS). E. coli targets: GFP 0.597→0.701, β-gal 0.603→0.740 (both now above their WT). Pre-fix run archived `exp2_cds_nulls_prefix/`. Suite **646 passed, 1 skipped** (10 new wiring tests; `bootstrap_auroc_ci` inlined to repair a reset-dangling import).
- **Exp 5 (Fig 2e) executed** (2026-08-25, user-approved panel expansion + zero-intervention rule): IRES literature panel re-run with the positives expanded **3 → 9** (viral EMCV/HCV/poliovirus + FMDV NC_004004.1, HRV-A1 NC_038311.1, BVDV-1 NC_001461.1 + cellular c-myc/VEGF-A/Bip, ranges 1..CDS_start−1, provenance in the anchor `SOURCES.md`) against the unchanged 50 GENCODE v46 5′UTR negatives (`experiments/exp5_ires_literature_panel.py`, pre-registered docstring, pilot 6/6, advisory CapGate). One `ires_prediction` run per sequence at platform defaults; the only deviation is `probability_threshold=0.0` (labelling knob off — raw probabilities flow to the score layer; threshold-free AUROC, stratified bootstrap 10⁴). **59/59 scored, 0 failures. Pre-registered mode-0 primary: AUROC 0.478 (95% CI 0.311–0.649, P=0.841 — at chance**; 20/50 negatives score >0.5; score–length r=0.018; legacy 0.762 does not reproduce — legacy-3 subset on the same negatives = 0.513). Disclosed mode-2 scanning addendum (registered after the primary was known): AUROC 0.673 (0.467–0.862, P=0.102), matching the E16 oracle grading (0.68–0.76 < 0.8 gate → enforce-gated). Figures `experiments/plots/fig2e_ires_roc.py`; **figure endpoint re-registered to the mode-2 scanning arm (user direction, 2026-08-26)** — it is the legacy panel's protocol (legacy per-sequence scores match this arm exactly) and the oracle's native regime; canonical `fig2e_ires_roc.{pdf,png}` now renders mode-2 (AUROC 0.673), the mode-0 primary stays the analysis record as `fig2e_ires_roc_mode0.{pdf,png}`. `PAPER_DRAFT.md` Fig 2e legend + Results observation (3) updated (stale "EMCV 0.808/poliovirus 0.891" parenthetical dropped).

- **Exp 4 (Fig 2d) executed** (2026-08-25, user-directed zero-intervention rule): secondary-structure inverse folding re-run on the RNADesign-210 `06_rna_secondary_structure` sub-benchmark (`experiments/exp4_inverse_folding.py`, pre-registered docstring, pilot 5/5). Single arm = the `rna_secondary_structure_design` golden path as-is (RNAinverse ×N → fold-back validation + GC → score → rank; task inputs verbatim, no threshold presets, no tuning, advisory CapGate). **25/25 successful, 21/25 exact recovery** (dot-bracket distances 0×21, 2/2/4/6; miss base-pair distances 1/2/3/1); all four misses are mp-mode / combined-params / 70 °C / 54-nt edge tasks and no candidate in their ranked sets was exact (generation-limited). Number of record 21/25 (pre-reset and Exp-1 lane observed 22/25 — different stochastic realization). Figure `experiments/plots/fig2d_inverse_folding.py` → `fig2d_inverse_folding.{pdf,png}` (strip + step cumulative curve; workflow grey-green / reserved dark warm grey / slate blue, all palette rev 7). Analysis-side fix during the run: base-pair distance corrected to |P₁ Δ P₂| (integer-halving slip; recomputed from stored structures, no platform re-run).
- **Exp 2+3 (Figs 2b–c) executed** (2026-08-25, user-directed design changes): experiments 2+3 merged into one driver (`experiments/exp2_cds_null_model.py`, pre-registered docstring, pilot 3/3). Designed arm = **the CDS golden path as-is** (`design_tool="all"`: LinearDesign λ-grid + RNARL + GEMORNA → evaluate → score → rank; no objective tuning); nulls = WT RefSeq anchors + 10 seeded synonymous draws per target (n=200). 20/20 design + 240/240 scoring, 0 failures. CAI medians **0.830/0.729/0.674** (designed>WT>random gate PASS; WT-vs-random P=6.8e-7 δ=0.67); MFE/nt **−0.336/−0.051/−0.047** (designed vs nulls δ=−1.0; WT-vs-random NS). **Fig 2c re-registered as a three-arm MFE/nt panel** (replaces the legacy WT-vs-random-only control) — designed CDSs lead on CAI and structure simultaneously. Figures `experiments/plots/fig2bc_cds_nulls.py` → `fig2b_cai.{pdf,png}`, `fig2c_mfe_per_nt.{pdf,png}`; palette gained `ARM_COLORS` slots (designed terracotta / WT sage / random dark warm grey) under rev 7.
- **Experiment-programme reset + Exp 1 done** (2026-08-25, DECISIONS (z), user-directed): the architecture moved too much since the legacy campaigns — **all paper experiments re-run against the frozen gated platform** with newly written drivers/figures; legacy campaign code, plots and results deleted (retained: SelfModel evidence chain `e1_*_v2`/`e7_*`/`rnasmol_boundary_panel*`/`e16_e17_e18/` + `build_default_self_model.py`, `codon_tables/`, `tool_inventory.json`, `MODEL_API_USAGE.md`, audit trail). **RNADesign-210 audited and repaired on disk** (`experiments/audit_rnadesign210.py` / `fix_rnadesign210.py`; manifest recounts 208→210, category taxonomy → basic/edge/full, IRES fixtures rebuilt on real poliovirus/EMCV anchors with mode-0 thresholds inside the oracle's measured regime, expected tool chains regrounded from live traces; re-audit 0 issues / 0 warnings). **Exp 1 (Fig 2a) executed: 210/210 across the 11 workflows** (`experiments/exp1_rnadesign210.py`, advisory arm, records under `experiments/results/exp1_rnadesign210/`; 4-task enforce probe documents the gated-refusal signatures). **Unified figure palette locked** (`experiments/plots/palette.py` rev 7, **user-finalized** — the earthy Morandi twelve-colour set; every subsequent experiment figure draws from it exclusively, no palette revisions without user direction; Fig 2a at `experiments/plots/output/fig2a_coverage.{pdf,png}`). Experiment services are GPU-pinned to 0/1/2 by `experiments/exp1_bring_up_services.sh`.
- **Paper-preparation documentation pass** (2026-08-25, doc-only): external-baseline arms **E21 (bare-LLM)** and **E22 (same-tools ReAct)** registered in `docs/DECISIONS.md` Part 4 (planned, not yet run — see Standing facts); all six `docs/PAPER_DRAFT.md` figure legends re-lettered to `docs/FIGURE_PLAN_V5.md` (the single source of truth for panel lettering); the first Results subsection split into a system-design Overview (Fig. 1) + RNADesign-210 results (Fig. 2); Supplementary Table S1 / Note S2 registered in the figure plan. Same-day **figure-type diversification pass** (doc-only): panel chart types across Figs. 1–6 diversified after a structured survey of eight agentic-science references — registered in `docs/FIGURE_PLAN_V5.md` and named in the `docs/PAPER_DRAFT.md` legends.
- **Repo-wide simplification pass — code is the source of truth, old artifacts purged** (2026-08-22, user-directed; `docs/CHANGELOG.md` 2026-08-22 (i) + DECISIONS (y)): (1) fixed a real leak — every test-suite run wrote scratch files to the real `workspace/` root (141k files / 1.3 GB accumulated); `tests/conftest.py` now redirects all default workspace bases to a per-run `workspace/_tests` scratch (subprocess-safe via the new `RNADA_WORKSPACE_BASE` env override honoured by `WorkspaceManager`), verified zero new root files across a full suite run. (2) Demo tool `workflow_demo_echo` removed — **41 registered tools, all production** (`python -m agent_core.tool_inventory`). (3) Duplicated QualityAgent retry tests consolidated into one parametrized module; duplicated `Args/Returns` docstrings stripped from 39 `tools.py` wrappers (the Input-model `Field` descriptions are the single source). (4) Historical outputs purged: superseded figure generations (`plots/{paper,paper_v4,fig*_panels}`), archived experiment rounds, leaked workspace scratch and stale service-run intermediates — **repository 4.3 GB → 2.0 GB** (remaining bulk: 1.2 GB of required reference genomes + the retained audit trail); the CapGate audit trail (`workspace/audit/`, `workspace/sessions/`) and every `*_fresh_audit_*` evidence directory retained. Suite **635 passed, 1 skipped**; PA_006–PA_019 rerun green.
- **Full-platform E2E fresh-data audit** (2026-08-22, DECISIONS (x); evidence `workspace/e2e_fresh_audit_2026-08-22/`): whole stack — all three Layer-6 entry points driving all 11 workflows on live services + live CapGate + live DeepSeek review on entirely fresh fetched data; 56 checks / 0 failures post-fix. Three defects fixed: opaque `sgrna_design` missing-seed failure (now a clear `ValueError`), `stream_form` raising on hard failure (now a final `runner` event), ViennaRNA inverse-fold accepting pseudoknot brackets (SIGSEGV behind a 503; now rejected up-front — normalise Rfam `SS_cons` upstream).
- **Layer 0–6 fresh-data audit programme complete** (2026-08-21/22, DECISIONS (r)–(u); evidence `workspace/layer{1..6}_fresh_audit_*/`): every layer audited on live-fetched data; 17 defects fixed across the stack (WorkspaceManager path-traversal/`delete_session("")` rmtree, pipeline session-scoping leak, API success misreporting, dropped progress events, degraded-service pre-flight hole, dropped ranking-governance audit events, …).
- **GenNav production wiring** (2026-08-19/22, DECISIONS (n)/(q)): opt-in `navigation` mode on `rna_aptamer_design` (v2.1.0, length lattice) and `mrna_cds_design` (v1.2.0, GenNav-λ) — deterministic, zero-LLM, full trace in `_state_writeback["_gennav_trace"]`. Six workflows now rank by the shared ASF layer; ranking objectives are assembled from CapGate verdicts (`docs/RANKING_GOVERNANCE.md`).
- **System simplification 2026-08-18** (DECISIONS (a)/(m)/(n)): BMC framework removed after its coordination-gain narrative was triple-falsified; 12 dead tools purged; E1–E15 experiment machinery deleted (evidence JSONs kept as the audit record).

## Standing facts (keep in mind before proposing work)

- **Registered next steps**: the remaining paper experiments (2.2 节实验 9 起:Fig 2i panel, Figs 3–6 campaigns, E21/E22 baseline arms; the Fig 2e framing decision is closed — mode-2 scanning arm is the figure endpoint, user re-registration 2026-08-26) re-run under the 2026-08-25 reset — new drivers follow the Exp-1 pattern (`experiments/expN_*.py`, pre-registered docstring, advisory primary arm + enforce probes where gating semantics matter, unified palette figures); E19/E20 stay reserved for the CRISOT/CRGPT data gap.
- **Pending profiling backlog**: CRISOT-Score + CRGPT stay governance=pending on a registered data gap — no labeled anchor set exists on disk; do **not** improvise self-referential anchors (DECISIONS (l)).
- **Auditability boundary**: every ToolExecutor call lands in the CapGate platform audit trail (`workspace/audit/platform_audit.jsonl`, session-stamped); microservice-internal oracle hops (e.g. GerNA-Bind folding via RhoFold inside the service) are **not** audited at the agent layer (DECISIONS (k)).
- **Never deleted**: the workspace audit trail and the SelfModel evidence chain (`e1_*_v2`/`e7_*`/`rnasmol_boundary_panel*`/`e16_e17_e18/`); campaign artifacts are deleted per reset (DECISIONS (n)/(y)/(z)).
- Before proposing any new experiment/optimization, check `docs/DECISIONS.md` Part 1 (do-not-repeat register).

## Documentation Index

| Document | Purpose |
|----------|---------|
| [`rna_agent_system/docs/README.md`](rna_agent_system/docs/README.md) | Project overview, quick start, capability summary |
| [`rna_agent_system/docs/ARCHITECTURE.md`](rna_agent_system/docs/ARCHITECTURE.md) | Seven-layer architecture, core module APIs, routing strategy |
| [`rna_agent_system/docs/WORKFLOWS.md`](rna_agent_system/docs/WORKFLOWS.md) | Domain workflows: pipelines, scoring formulas, critic design |
| [`rna_agent_system/docs/MANUSCRIPT.md`](rna_agent_system/docs/MANUSCRIPT.md) | Experiment manual: benchmark/anchor assets, pilot-first protocol, data availability |
| [`rna_agent_system/docs/TOOLS.md`](rna_agent_system/docs/TOOLS.md) | Per-tool specs, port registry, microservice notes |
| [`rna_agent_system/docs/DEPLOYMENT.md`](rna_agent_system/docs/DEPLOYMENT.md) | Environment setup, testing recipes, curl examples |
| [`rna_agent_system/docs/CHANGELOG.md`](rna_agent_system/docs/CHANGELOG.md) | Current interface state + condensed change-era register |
| [`rna_agent_system/docs/DECISIONS.md`](rna_agent_system/docs/DECISIONS.md) | Do-not-repeat register, established results, timeline |
| [`rna_agent_system/docs/RANKING_GOVERNANCE.md`](rna_agent_system/docs/RANKING_GOVERNANCE.md) | Ranking governance design: verdict-driven ASF objective assembly (DECISIONS (p)) |
| [`rna_agent_system/docs/CONTRIBUTING.md`](rna_agent_system/docs/CONTRIBUTING.md) | Coding standards, new-tool procedure, commit conventions |
| [`rna_agent_system/docs/ANCHORS.md`](rna_agent_system/docs/ANCHORS.md) | External-anchor directory spec, anchor-set JSON schema, assertion-first curation pattern |

## Project Architecture

Seven-layer design with a multi-agent execution layer at Layer 4:

- **Layer 0**: Tool wrappers, specs, registry, executor (`tools.py`, `tool_specs.py`, `tool_registry.py`, `tool_executor.py`) — 41 registered tools, all production
- **Layer 1**: `Capability` + `CapabilityRegistry` (`capabilities/`)
- **Layer 2**: `BaseDomainWorkflow` + 11 domain workflows (`workflows/`) — all plain generate → evaluate → score → rank pipelines; six workflows rank by Achievement Scalarizing Function (`full_length_mrna_design`, `rna_aptamer_design`, `sirna_design`, `sgrna_design`, `rna_tertiary_structure_design`, `aso_target_screening`; DECISIONS (o)/(q)); GenNav constraint navigation is an opt-in path on `rna_aptamer_design` (length lattice) and `mrna_cds_design` (GenNav-λ)
- **Layer 3**: Microservice health/orchestration (`agent_core/services/service_manager.py`)
- **Layer 4**: Planning & multi-agent execution (`pipeline/` + `agents/`; the calibrated CapGate stack lives in `agent_core/calibrated/`)
  - `PipelineAgent` — deterministic pipeline orchestration
  - `SpecialistAgent` — per-workflow strategy and retry decisions
  - `QualityAgent` — unified quality review (advisory only)
  - `SynthesisAgent` — multi-node result synthesis (ClaimGate-gated)
- **Layer 5**: `SessionMemory` + `WorkspaceManager` + `FileManager` (session ids validated as single path components; `RNADA_WORKSPACE_BASE` overrides the default workspace base)
- **Layer 6**: `AgentRunner` unified façade (CLI / FastAPI)

Shared cross-layer constants (e.g., the unified species/organism registry) live in `agent_core/constants/`; `agent_core/constants/species.py` is the single source of truth for CAI species, RNARL model types, and reference transcriptome species IDs.

Workflow selection is explicit: CLI menu, `--workflow`, `AgentRunner.run_form(..., explicit_workflow=...)`, or a multi-node `PipelinePlan` via `--pipeline-file`. There is no automatic router.

## LLM Configuration

Set these environment variables (or add them to `rna_agent_system/.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API key (primary) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API endpoint |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | `deepseek-v4-pro` or `deepseek-v4-flash` |
| `OPENAI_API_KEY` | — | OpenAI API key (optional) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (optional) |
| `ALIBABA_API_KEY` | — | Alibaba DashScope API key (optional) |
| `GOOGLE_API_KEY` | — | Google Gemini API key (optional) |

LLM clients are built via `agent_core/llm_config.py`:

```python
from agent_core.llm_config import get_llm_for_provider, get_deepseek_llm, list_supported_providers

print(list_supported_providers())                       # deepseek, openai, anthropic, alibaba, google
llm = get_llm_for_provider("openai", model="gpt-4")     # optional: api_key=, base_url=, temperature= (default 0.1)
llm = get_deepseek_llm()                                # primary provider shortcut
```

`QualityAgent` and `SynthesisAgent` accept an injectable `llm`; when constructed with `llm=None` they lazily build a DeepSeek client (`temperature=0.2` for `QualityAgent`, `0.3` for `SynthesisAgent`).

## Multi-Agent Execution

| Agent | Responsibility |
|-------|----------------|
| `PipelineAgent` | Deterministic scheduling of `PipelinePlan` nodes, input binding resolution, critical-failure handling, and final synthesis. Does **not** call LLMs. |
| `SpecialistAgent` | Per-workflow strategy: runs the workflow, invokes `QualityAgent`, decides retry/adjust/abort, and returns `AgentResult`. |
| `QualityAgent` | Unified quality review using workflow-specific `QualityProfile`. Outputs an advisory `QualityReport`; it neither triggers retry on its own nor can it flip a successful run to failed. |
| `SynthesisAgent` | Passes through single-node results; for multi-node pipelines, generates a concise synthesis report (claims pass the ClaimGate). |

| Workflows reviewed by QualityAgent | QualityProfile |
|-----------------------------------|----------------|
| `mrna_cds_design` | `MRNA_CDS_QUALITY_PROFILE` |
| `sirna_design` | `SIRNA_QUALITY_PROFILE` |
| `sgrna_design` | `SGRNA_QUALITY_PROFILE` |
| `rna_aptamer_design` | `RNA_APTAMER_QUALITY_PROFILE` |
| `ires_prediction` | `IRES_QUALITY_PROFILE` |
| `rna_secondary_structure_design` | `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE` |
| `rna_tertiary_structure_design` | `RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE` |
| `full_length_mrna_design` | `FULL_LENGTH_MRNA_QUALITY_PROFILE` |

| Workflows without quality review | Reason |
|----------------------------------|--------|
| `mrna_sequence_scoring` | Deterministic scoring task |
| `aso_target_screening` | Deterministic screening task |
| `rna_small_molecule_interaction` | Deterministic prediction task |

```python
runner = AgentRunner(
    executor=executor,
    quality_review_enabled=True,   # enable QualityAgent LLM diagnosis
    quality_auto_retry=False,      # advisory mode by default
)
```

`AgentRunner` automatically enables `auto_start_services` on every workflow it owns. If you instantiate a workflow directly and want the same pre-flight/auto-start behavior, set `workflow.auto_start_services = True` before calling `run()`. The standalone convenience function `run_mrna_sequence_scoring()` also defaults to `auto_start_services=True`; pass `auto_start_services=False` when providing a custom `CapabilityRegistry` in tests or other managed environments. When pre-flight fails, the workflow returns a `WorkflowResult(success=False, ...)` with actionable error messages instead of crashing mid-execution.

- **Advisory mode** (`quality_auto_retry=False`): `QualityAgent` records a `QualityReport` but the `SpecialistAgent` only retries on hard failures (`WorkflowResult.is_hard_failure`: `success=False`, empty candidates, tool errors).
- **Auto-retry mode** (`quality_auto_retry=True`): `SpecialistAgent` may auto-retry when `QualityReport` recommends adjustments with valid overrides.
- **Governance**: if the LLM review call fails, the report is marked `review_unavailable` (zero-confidence `pass`) and the error is retained in `state["_quality_review_error"]` for audit; an LLM-chosen `abort` is advisory-only. Neither path can flip a successful run to failed.
- **Cross-turn context**: before replacing a stale `workflow_result`, `AgentRunner` copies it to `_previous_workflow_result` and appends it to `_workflow_result_history`.

### Known limitations (do not assume these are already implemented)

1. **`PipelinePlan` edges are required for every data dependency.** A binding alone does **not** create an execution dependency; if node B consumes an output from node A, there must be both an edge `A → B` and an `input_bindings` entry in B.
2. **`QualityProfile.build_prompt` is an optional extension point** — only `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE` uses it. Avoid adding new `build_prompt` overrides unless the default prompt cannot express workflow-specific tuning guidance.

## Testing

Run the agent-core test suite before committing (current baseline: **635 passed, 1 skipped** — the suite is workspace-isolated: test scratch goes to `workspace/_tests/`, never the real workspace root):

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x
```

For CLI end-to-end regressions, run the PA_006–PA_036 inputs (all 11 workflows, user-input → final design result; 006–024 original batch, 025–036 the 2026-08-19 fresh-data batch including two GenNav `navigation=true` runs) using the consolidated driver:

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python run_pa_test.py 006
```

Benchmark configurations live in `rna_agent_system/pa_benchmarks.json`; pass any PA number `006`–`036` to the driver. The driver defaults its subprocesses to `RNADA_CAPGATE=advisory` (PA runs are process-aware CLI regressions; enforce-mode oracle gating — the registered E16–E18 consequence, DECISIONS (j)/(l) — would otherwise fail whole workflows whose scoring oracles are legitimately blocked in production). Set `RNADA_CAPGATE` explicitly to override. Static input fixtures live git-tracked under `data/benchmarks/RNA-BioBench-ProcessAware/fixtures/` (provenance in `data/benchmarks/README.md`).

For live microservice end-to-end smoke tests, no manual service startup is needed — the CLI / `AgentRunner` pre-flight auto-starts the services each workflow requires:

- `FullLengthMrnaDesignWorkflow`: run `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/test_full_length_mrna_e2e_live.py -v` (pytest module — plain `python` invocation is a silent no-op).
- `RnaAptamerDesignWorkflow`: run the PA_020 benchmark via `PYTHONPATH="$(pwd):$PYTHONPATH" python run_pa_test.py 020`.
