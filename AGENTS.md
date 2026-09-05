# Agent Guidelines for RNA_real_agent

> **Consolidated index.** Authoritative documentation lives in `rna_agent_system/docs/`.
> **Last updated**: 2026-09-05 (FOURTH programme reset in progress — Figs 2/3/4 + Fig 5a–h ALL DONE (5d = Exp 31 figure-only render on frozen Exp-28 data, 2026-09-05); next: Fig 6. Usable GPUs 0/1/2 (user-confirmed 2026-09-05; exp1 bring-up script pins them). What's New compressed to a one-line-per-milestone register; full per-experiment records in `docs/CHANGELOG.md`, claim checks in `docs/PAPER_FACT_SHEET.md`, experiment manual in `docs/MANUSCRIPT.md`)

## What's New

> Condensed register (compressed 2026-09-02 from narrative entries; details — protocols, pre-registrations, amendments, disclosures, figure-QA rounds — are in `docs/CHANGELOG.md` under the matching dates). Driver pattern for every reset experiment: `experiments/expN_*.py`, pre-registered docstring, pilot-first, zero-intervention production tool path (`ToolExecutor.run_tool`), `RNADA_CAPGATE=advisory` unless gating is the object of study, palette rev 7 figures (absolute mm, 6-pt pure-black text, 1200-dpi PNG + vector PDF), `--verify` byte-identical recomputation.

- **Exp 31 / Fig 5d — Fig 5 COMPLETE (2026-09-05, figure-only)**: the Exp-28 secondary-endpoint panel rendered from frozen data (`exp31_fig5d_secondary.py` → `panel_data.json`, every number recomputed from the Exp-28 records + asserted equal to its verdict, `--verify` byte-identical; no prior fig5d existed in this reset). Three blocks — criteria bullet bars (gene-e2e conjunct **0.45 = 9/20 vs 0.8 legacy gate**, rule pool 1.00 = 20/20 context; constraint rate **0.944 ≥ 0.9 TRUE**), Δ-composite stacked dots (**+24/=18/−18, Wilcoxon P = 0.73 NS**), per-target spend strip (mean 24.55/35, 10 at cap + 10 early-stop, **0 violations · 0 LLM**); text-collision guards + raster QA GREEN; 89×74 mm. PAPER_DRAFT legend (d) + §2.5 Fig. 5d citation, FIGURE_PLAN row d, FACT_SHEET Exp 31, MANUSCRIPT E6 row synced. **Next: Fig 6, same pattern.**

- **Exp 29 / Fig 5e–5h COMPLETE incl expanded pool (2026-09-03→05, the paper's citation)**: 20-pool v4 arc — seg3 **10:3 P=0.092 (delivered 24:17, e2e 4:0 nav-only)**, seg4 1:8 (disclosed), pooled parity at 48; **expanded 39-target budget sweep (RNA-BioBench-Aptamer-Expanded: 12 docking-anchor complex proteins + 7 anchor-fasta/ProteinX-folded) — cap16 10:2 P=0.039 SIGNIFICANT nav win (the aptamer-side promotion point), cap20 9:4, cap24 18:15, cap32 10:22 P=0.050 and cap48 12:30 P=0.008 static wins (both disclosed — the two-sided regime characterization)**; full curve nav [10,9,18,17,34] vs static [2,4,15,29,52] in `expanded_summary.json`. Production: v4 navigator (least-served band rotation + shrinkage/UCB + D1-aware gaps), `navigation_raw_budget` knob, 650+ tests green; **resident ODesign services** (model weights resident on GPU, ~22 s/request vs ~90 s subprocess path, byte-identical outputs; launcher `microservices/odesign_service/start_resident.sh`; two mid-run shutdowns saved/resumed via RESTORE_NOTE). fig5e/f/g/h re-rendered on final data, raster QA green; §2.5 + legend + FIGURE_PLAN + FACT_SHEET re-based.
- **Fourth programme reset opened** (2026-09-02, user-directed — architecture changed again): ALL paper experiments re-run with newly written code **one experiment at a time** — old code/results/figures/docs of the experiment being re-run may be deleted, all other files untouched. Palette rev 7 (12-colour Morandi set) re-confirmed verbatim; usable GPUs 0/1/2 (`experiments/exp1_bring_up_services.sh`). The paper presents the latest re-run results only; old-vs-new comparisons stay in the internal registers.
- **Exp 28 / Fig 5b+5c (repaired system)** (2026-09-02→03, `experiments/exp28_gennav_mrna_endpoint_v2.py`, zero LLM, 20/20): the E6/S2 endpoint re-run against the REPAIRED production navigator after Exp 27's 0:24 starvation boundary — budget matching (35 raw calls/arm, violations 0), densified 35-λ lattice, constraint bands anchored dimension-by-dimension to the registered matrix (CAI 0.80 all bands incl. stability, CDS-level stem ≤30bp=C7 new dimension, GC [0.30,0.80]=C1, homo<14=C2), the legacy E6 synonymous-diversity expander restored (zero generation budget), CDS-level D1 floor 0.03 (P3 calibration), parallel memory-adaptive probe. **Paired discordance significant favouring navigation: b:c = 17:6, McNemar p = 0.0347, n = 60**; navigation 35/60 JCD cells vs rule 24/60; HER2 delivers (legacy zero-feasible target); GFP the counter-boundary (3 rule-only cells); c_e2e_gene 0.45 < 0.8 conjunct + composite secondary disclosed; three pilot rounds of root-cause calibration; tests 25+110 green; `--verify` byte-identical; fig5b/5c re-rendered on exp28 data, raster QA green. Machine change 2026-09-03 (user-directed): usable GPU = 0 only, bring-up repinned, mid-run shutdown saved/resumed via RESTORE_NOTE. Paper re-based to the repaired-system results (abstract, contribution 4, §2.5, Discussion, Fig 5 legend b–d, Methods, LLM usage, data availability); Exp 27 = internal boundary register. **Next: rest of Fig 5 (aptamer campaigns e–h) and Fig 6, same pattern.**
- **Exp 27 / Fig 5b+5c (boundary measurement)** (2026-09-02, `exp27_gennav_mrna_endpoint.py`, zero LLM): pre-repair boundary — the v1 shipped defaults failed the endpoint 0:24 (batch starvation: 49/60 cells <5 delivered); mechanism criteria passed (D1 56/60, D2 55/60, R3 20/20 vs rule 53/35/8) — the internal register that motivated the Exp-28 repair. Same-day dataset-record fixes (user-directed): FullLength-mRNA manifest/sequences/README corrected to the operative 20-target set.
- **Exp 26 / Fig 5a** (2026-09-02, `experiments/exp26_selection_layer_pool.py`, zero LLM): selection-layer pool-failure re-measurement, S1 five targets (A1AT/Insulin/EPO/GFP/IL-2) × 315 full-length constructs (LinearDesign λ{0,1,4,10} + RNARL + GEMORNA 30×9), legacy protocol recovered verbatim from git `b6dad08`. 6/6 cells: pass counts EPO 306 / IL-2 297 / Insulin 144 / A1AT 27 / **GFP 0/315 default human codon table → 18/315 E. coli table** (passing candidates confined to the λ{4,10} gears — the B0 species-table defect reproduced); Insulin delivered-batch diversity 1.01% < 2% gate (λ-saturation failure reproduced); dominant binding constraint C1 sliding GC; `--verify` byte-identical.
- **Exp 25 / Fig 4g+4h** (2026-09-01, `exp25_quality_review_advisory.py` + `exp25_fig4h_data.py`): quality-review advisory three-arm re-run, 31 PA sessions × arms (off / on / on+API-outage) = **93/93 form-entry CLI runs**. Paired per-turn outcome identity TRUE (0 mismatches — the advisory property measured on every session); sole workflow-level exception PA_023 fails identically in all arms (inherited fixture gap `workspace/pa023_5utr.fa`, same FileNotFoundError in the frozen exp8/exp24 corpora — disclosed as measured, not recreated). Outage arm: 144 failed review calls → `review_unavailable` zero-confidence-pass markers, no turn killed. New `RNADA_QUALITY_REVIEW` env knob in `cli/form_chat.py` (default on). Fig 4h LLM usage: Exp 5 = 90, Exp 17 = 90, Exp 18 = 80, Exp 23 = 0, Exp 24 = 482 (mean 2.0/run), Exp 25 arms 0/144/0.
- **Exp 24 / Fig 4f + Fig 2a/2h/2i re-measured** (2026-09-01, `exp24_production_campaign.py` + `exp24_run_parallel.py` + `exp24_audit_gate_stats.py`; user-directed shared-instrument design + eleven workflow-exclusive parallel workers, campaign wall ≈ 6.8 h): all 210 RNADesign-210 tasks + 31 PA form sessions, **241/241, 0 failures**. Frozen audit slice: 10,395 events = 8,818 tool calls (84.8%, 40 tools, 3 isolated failures) + 1,392 gate decisions (reject 709 / require_profiling 549 / downgrade 134 / allow 0 across 11 oracles — the only downgrades are the certified MRL oracle's transferred-grade decays) + 185 ranking assemblies + 0 claims. Runtimes: pooled median 2.32 min, 76.8% ≤5 min, 240/241 ≤1 h (max = GenNav PA_028 68.1 min after the 2026-09-05 final-code v4 re-measurement; the original frozen slice's 10,395-event composition became 10,331 via the registered surgical re-freeze `exp24_refreeze_pa028.py` — see CHANGELOG 2026-09-05). Representative session = PA_036 (152 calls + 32 gates + 3 ranking). Legacy exp1/exp8/exp9 assets superseded and deleted per the reset rule (`exp1_bring_up_services.sh` retained).
- **Exp 23 / Fig 4e** (2026-09-01, `exp23_selective_gating.py`, 0 LLM): selective-gating decision matrix under `RNADA_CAPGATE=enforce` + packaged default SelfModel. **12/12 cells met pre-registered expectations (GO)**: DecisionGate allow ×3 (conf 1.0) / downgrade (conf exactly 0.5 = 1.0 × 0.5 transfer decay) / require_profiling ×2 blocked; ClaimGate pass / downgrade (absolute → within_target_relative) / reject; enforcement layer — allow executes (predicted MRL exactly the Exp-14 cached value), downgrade executes (capping is ClaimGate's job), require_profiling blocked pre-call (GatedActionError, no service call).
- **Exp 18 / Fig 4d** (2026-09-01, `exp18_build_mrna_audit_tasks.py` + `exp18_mrna_claim_gating.py`): E3-M mRNA-side claim gating, 20 tasks dual-arm, **40/40**: FP 6/17 = 35.3% → 1/12 = 8.3%, TP retention 11/11 = 100%, overreach 6 → 0 (go-rule PASS); surviving FP = the symmetric MRL rank-flip on the weakest certified family. Disclosed platform defect found mid-run: results-JSON `metadata.cds_sequence` is a storage-truncated echo — the builder resolves the true CDS from the CDS-design cache (10 runs superseded).
- **Exp 17 / Fig 4a–c** (2026-08-31, `exp17_claim_gating.py`): aptamer claim gating, 45 tasks paired with the Exp-5 ungated arm, **45/45**: FP 0/31 = 0% vs ungated 54.5% (hard guarantee holds); overreach 59 → 0 (71 plan requests blocked); TP retention 80.0% (25 → 20) — **below the pre-registered 90% gate, reported as measured** (2 uniform-basis-rule suppressions, 2 length-sloppy abstentions, 2 unretainable lucky TPs, +1 rescue).
- **Fig 3 composite + panel renaming** (2026-08-31, user-directed): `experiments/plots/fig3_assemble.py` → `fig3_composite.{pdf,png}` (eight panels a–h, 1200-dpi PNG from the all-vector composite PDF). Result figures no longer open with summary/mechanism schematics — the planned Fig-3a/4a/5a schematic panels were removed and Fig 3's b–i panels re-lettered to a–h (mechanism schematics live in Fig 1d/1e; historical registers keep their written-time letters).
- **Exp 16 / Fig 3h** (2026-08-29→31, `exp16_confounded_improvement.py`): confounded-improvement falsification at full panel — 20 aptamer targets × 3 seed sets × 4 arms = 240 cells (228 ok + 12 Ferritin boundary failures; the removed BMC coordination loop reconstructed verbatim as the object of study). Apparent effect δ = +0.1397 (nominally significant, already sub-gate) → budget-matched +0.0504 (dissolved) → fixed-resampling −0.0120 (nothing); self-audit survival 0/2.
- **Exp 15 / Fig 3g** (2026-08-29, `exp15_rnasmol_fidelity.py` + v0.2.0 sandbox addendum): RNAsmol deployment-fidelity A/B, 3,324/3,324 — tool-path normalization is **AUROC-neutral in-distribution** (0.9745/0.9860 vs verbatim 0.9744/0.9828; the pre-registered defect-class criterion FAILED, disclosed falsification). The re-measured v0.2.0 sandbox (0.790/0.420) isolates the adjacency rewrite — not case handling — as the damage carrier.
- **Exp 14 / Fig 3f** (2026-08-29, `exp14_mrl_oracle_certification.py`, zero LLM): MRL oracle certification, 706/706 — all three families pass both gates (AUROC 0.9903/1.0/1.0; ρ 0.9256/0.9201/0.8353); 1:1 vs the retained `e7_mrl_scoring.jsonl` exact (max |Δ MRL| = 0) — deterministic end-to-end through the deployed chain.
- **Third programme reset + Exp 5 / Fig 3e** (2026-08-29, `exp5_build_audit_tasks.py` + `exp5_claim_overreach.py`): the one-experiment-at-a-time rule established (an initial blanket deletion was restored from git the same day). Ungated claim-overreach control, 45 tasks, 45/45: FP 30/55 = 54.5% (Wilson 41.5–67.0), 59 decision-layer overreach events; class-selective — deterministic 23 TP/0 FP vs untrusted-oracle 30 FP/2 TP.
- **Exp 13 / Fig 3d** (2026-08-28, `exp13_affinity_calibration.py`): affinity calibration on anchor set v3 (95 entries), 95/95 — thrombin 6-point Kd series ρ = 0.486 (sub-gate); pooled binder-vs-negative AUROC 0.5225 (CI 0.391–0.652): **"uncalibrated, chance-level at scale"** (per-entry inversion reproduces 1:1).
- **Anchor set v3 + Exps 10–11 v3 re-runs** (2026-08-28): Part-A extended 6 → 9 targets / 66 → 95 entries (`e1_anchor_set_v3.json`, generator assertion-checked). exp10 v3: 27/27 screening cells, 2 nominal passes >0.8, all 27 CIs cover chance. exp11 v3: 27/27 ranking cells, 4 nominal ρ passes, all CIs span zero. Headline invariant: no reliable screening or ranking cell. Figs 3a/3b re-rendered on v3.
- **Exp 12 / Fig 3c** (2026-08-27, `exp12_docking_capability.py`): docking power on v3 (19 complexes / 14 independent protein targets, all RCSB-verified; contact computation reproduces 1HVU n_contacts = 152 exactly). 397/399 poses scored; **0/19 native top-1** (gate ≥ 2/3 fails decisively; native ranks 6–20 of 21).
- **Exp 11 / Fig 3b** (2026-08-27, `exp11_oracle_ranking_power.py`): ranking power, 34/34, 18/18 cells — 2 nominal ρ ≥ 0.6 passes, both small-n with vacuous uncertainty; no oracle passes on >1 target.
- **Exp 10 / Fig 3a** (2026-08-27, `exp10_structure_oracle_screening.py`): screening power, 66/66, 18/18 cells — **0/18 pass AUROC > 0.8, all CIs cover chance** (best cell 0.800 exactly).
- **Exp 9 + Exp 8 / Fig 2h + 2i** (2026-08-27): audit-trail statistics (10,217 events) + runtime by workflow (241/241, pooled median 2.6 min). **Superseded by Exp 24's re-measurement; assets deleted per the reset rule.**
- **Exp 7 / Fig 2g** (2026-08-26, `exp7_rnasmol_boundary.py`, current evidence — untouched by Exp 15): RNAsmol two-sided boundary, 3,545/3,545 pairs, case-preserving verbatim inputs — robin AUROC 0.9744, pdb 0.9828; OOD panel 0.7222/0.5625, both CIs span chance.
- **Exp 6 / Fig 2f** (2026-08-26, `exp6_sirna_offtarget.py`): siRNA off-target, 22/22 runs — 21/22 zero predicted off-targets (sole nonzero task 013, 3 bowtie2 hits); scan evidence trace-verified.
- **Platform fix + Exp 2+3 re-run / Figs 2b–c** (2026-08-25): species-resolved LinearDesign codon tables (11 Kazusa-derived CSVs in `agent_core/data/codon_usage_lineardesign/`, wired into `mrna_cds_design` golden path + GenNav navigation; audit trail records the table per call). Re-run 20/20 + 240/240: CAI medians 0.832/0.729/0.675, MFE/nt −0.336/−0.051/−0.047; E. coli targets GFP 0.597→0.701, β-gal 0.603→0.740. Suite **646 passed, 1 skipped**.
- **Exp 5-IRES / Fig 2e** (2026-08-25, `exp5_ires_literature_panel.py`): 59/59 — pre-registered mode-0 primary AUROC 0.478 (at chance); disclosed mode-2 scanning addendum 0.673 = the canonical figure arm (user direction). Coexists with the Exp-5 claim-overreach drivers of the third reset.
- **Exp 4 / Fig 2d** (2026-08-25, `exp4_inverse_folding.py`): 25/25, **21/25 exact recovery**; all four misses generation-limited edge tasks.
- **First programme reset + Exp 1 / Fig 2a** (2026-08-25, DECISIONS (z)): all paper experiments re-run against the frozen gated platform; RNADesign-210 audited/repaired on disk (208→210); Exp 1 210/210 across 11 workflows; **unified palette rev 7 locked (user-finalized)**. Fig 2a since re-measured by Exp 24.
- **Paper-prep doc pass** (2026-08-25): external baselines E21 (bare-LLM) / E22 (same-tools ReAct) registered (planned, not yet run); `docs/FIGURE_PLAN_V5.md` = the single source of truth for panel lettering.
- **Repo-wide simplification** (2026-08-22, DECISIONS (y)): test-suite workspace leak fixed (`RNADA_WORKSPACE_BASE` → per-run `workspace/_tests`); demo tool removed — 41 registered tools, all production; historical outputs purged 4.3 GB → 2.0 GB.
- **Full-platform E2E + Layer 0–6 fresh-data audits** (2026-08-21/22, DECISIONS (r)–(x)): every layer audited on live-fetched data; 17 + 3 defects fixed; 56 checks / 0 failures post-fix.
- **GenNav production wiring** (2026-08-19/22, DECISIONS (n)/(q)): opt-in `navigation` mode on `rna_aptamer_design` (length lattice) and `mrna_cds_design` (GenNav-λ) — deterministic, zero-LLM, trace in `_state_writeback["_gennav_trace"]`; six workflows rank by the shared ASF layer from CapGate verdicts (`docs/RANKING_GOVERNANCE.md`).
- **System simplification** (2026-08-18, DECISIONS (a)/(m)/(n)): BMC framework removed (coordination-gain narrative triple-falsified); 12 dead tools purged; E1–E15 machinery deleted (evidence JSONs kept).

## Standing facts (keep in mind before proposing work)

- **Registered next steps**: under the **2026-09-02 fourth programme reset**, every paper experiment is re-run with newly written code **one at a time in the user's sequence — replace only the current experiment's artifacts, never touch not-yet-re-run experiments' files** (progress: Figs 2, 3, 4 (a–h each) and Fig 5 (a–h) done — see What's New; **next: Fig 6**; the paper presents the latest re-run results only — retained-evidence old-vs-new comparisons stay out of the PAPER_DRAFT text and legends). New drivers follow the established pattern (`experiments/expN_*.py`, pre-registered docstring, pilot-first, zero-intervention production tool path, advisory CapGate, unified palette rev 7 figures); E19/E20 stay reserved for the CRISOT/CRGPT data gap.
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

Run the agent-core test suite before committing (current baseline: **646 passed, 1 skipped** — the suite is workspace-isolated: test scratch goes to `workspace/_tests/`, never the real workspace root):

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
