# Change Log

> **Scope**: interface changes and major workflow introductions.
> **Last updated**: 2026-08-29

> **History policy**: this log records the current interface state and a
> condensed register of the most recent change eras. Full narratives live in
> git history and the audit-evidence directories cited per entry; the
> experimental do-not-repeat register is [`DECISIONS.md`](DECISIONS.md).

## 2026-08-29 — QualityAgent 提示词/profile 全面审计：3 处方向性错误修正 + 过时默认值同步

- **审计范围**: 全部 4 个 LLM 调用点（QualityAgent 默认诊断提示词、
  secondary-structure `build_prompt` 覆盖、SynthesisAgent 综合报告、ClaimGate
  抽取/润白）+ 8 个进入提示词的 QualityProfile 的 evaluation_dimensions 与
  adjustable_params hints，逐条对照当前工作流实现、工具语义与重置后实验结论。
- **方向性错误修正（3 处）**: (1) `blast_perc_identity` hint 写反 — BLAST
  perc_identity 是最低相似度过滤，higher = stricter（fewer matches），
  原文 "Lower = stricter" 反了；(2) RNASTOP `overall_stability`（mrna_cds +
  full_length 两处）写反 — 该值是 mean(reactivity, deg_Mg_pH10, deg_Mg_50C)
  反应性/降解均值，**lower = more stable**，原文 "closer to 1.0 = higher
  stability" 方向反且无归一化依据；(3) sgrna 的 CRISOT 语义混淆 —
  CRISOT-Score 是 sgRNA–DNA 对切割活性评分（工作流配 on-target 对，higher =
  预测 on-target 活性强），基因组级脱靶特异性是独立的 CRISOT-Spec 分量。
- **过时内容同步（2026-08-20 评分权重审计之后未跟进）**: tertiary profile 的
  "carefully tuned defaults" 句与其 hints 声称 rhodesign_temperature=1e-5 /
  权重 0.5/0.5 — 实际 workflow 默认 0.1 / 0.30/0.50/0.50（三组分），补
  `weight_tm_score`；sgrna profile 补 `weight_crisot_specificity`（默认 0.3）；
  ires 的 `run_structural_validation` hint 由 "ViennaRNA structural
  validation" 更正为 LinearFold 主 / ViennaRNA 备的当前实现；siRNA GC 评审
  维度由 "30-60%" 对齐工作流自身门限 [mingc=0.25, maxgc=0.60]。
- **阈值证据化**: mrna_cds 的 CAI 评审维度由 "human >0.8 good / <0.4 poor"
  的悬空启发式改为 Exp-2/3 零模型证据（人类随机同义重抽 ≈0.67、优化设计
  ≈0.83），并强调物种相关；MFE 维度补长度归一化提示（MFE 随长度缩放，
  跨长度比较用 MFE/nt — 与 Exp-2 的分析约定一致）；CRGPT nn_score 删除
  "close to 1.0 excellent / >3.0 poor" 无依据阈值并标注为未剖析
  （governance=pending）的模型似然代理 — 与 standing fact "CRISOT+CRGPT
  data gap" 一致。
- **核对通过、未改动**: QualityAgent 默认 11 条规则（无阈值、与参数白名单
  机制一致）；secondary-structure 覆盖段的默认值（repeats=10/
  num_invocations=3/mode m/37 °C，与 workflow 一致）与分数语义
  （total_score = distance/length、smaller better，与 score() 实现一致；
  0.3 触发线与 Exp-4 证据不矛盾，保留）；aptamer profile 全部参数/边界/
  reference_point 键与工作流逐项一致，其 "Do NOT apply hard thresholds for
  EGARPS/pLDDT/ipTM" 与 E10–E13 重置结论一致保留；ires 的反通用阈值条款与
  Exp-5 一致保留；ClaimGate 抽取提示词的 oracle 示例（gemorna_5utr_mrl /
  egarps_native_probability / rnasmol）与 capability 枚举与 SelfModel/
  CapabilityKind 完全一致；CDS "GC/unpaired 不进排序分" 与
  score_mrna_candidate（−MFE + codon_count·log CAI）一致。
- **验证**: 6 profile 导入 + 默认提示词构建冒烟通过；测试套件
  **646 passed, 1 skipped**（= 基线）。

## 2026-08-28 — Exp 13 (Fig 3e): affinity calibration at anchor-set scale — chance-level, inversion does not survive scale

- **Driver** `experiments/exp13_affinity_calibration.py` (pre-registered
  docstring; pilot 6/6 → full 95/95, 0 failures, wall ≈ 4.4 h): the retained
  P2 pilot's question re-registered on `e1_anchor_set_v3.json` verbatim (95
  entries / 9 targets — the Fig-3b/c/d data source, user-confirmed); zero
  intervention (ToolExecutor.run_tool → deployed rhofold 8005 / proteinx
  8022 / egarps 8023, fixed protocol args only); CapGate advisory; every
  call audited; the retained P2 15-record reference recovered from git
  e601913 and embedded (12/15 ids live in v3, drops disclosed).
- **Results**: thrombin 6-point Kd series ρ = 0.4857 (sub-gate; retained
  4-point 0.40 re-measures 0.20 — realization variance); pooled
  binder-vs-negative AUROC **0.5225 (CI 0.391–0.652, 62 vs 28)** — gate
  fails, CI covers chance; **the retained pilot's below-chance 0.356 does
  not survive scale — the honest reading upgrades "directionally inverted"
  to "uncalibrated, chance-level"** (per-entry inversion reproduces:
  pegaptanib 1.27e-6 vs scrambled TBA 0.983); all three ridgeline classes
  span the full 9-order score range; legacy-12 1:1 median |Δnp| = 7e-4
  (3 large shifts = the disclosed EGARPS bimodal class); vs exp10_v3:
  RhoFold bit-identical, EGARPS median Δ 5.7e-4. Verdict: **NO-GO on both
  P2 gates — no validated affinity calibration**.
- **Figure** `experiments/plots/fig3e_affinity_calibration.py` →
  `output/fig3e_affinity_calibration.{pdf,png}` (Kd–score scatter with the
  thrombin series emphasized + horizontal ridgeline densities on the shared
  log-score axis, ridgeline style after SeFMol Fig. 3d; palette rev 7; the
  group legend as a centred row block under the axis, the fig2i
  convention).
- **Docs**: PAPER_DRAFT Fig-3e legend + Results sentence (anti-signal →
  noise, inversion → chance-level at scale with the per-entry inversion
  preserved), PAPER_FACT_SHEET (E13 section + key-number 11), FIGURE_PLAN_V5
  row e, MANUSCRIPT reset table (Exp 13 row).

## 2026-08-28 — Fig 2 panel-letter swap: audit trail ↔ runtime (h ↔ i; user-directed)

The audit-trail panel is now **Fig 2h** and the end-to-end runtime ECDF
is now **Fig 2i** (lettering-only change — no data, statistics or panel
content touched), which also restores strict a → i reading order in the
composite (the f–g–h equal-height row now precedes the full-width i).
Files renamed: `experiments/plots/fig2h_audit_trail.py` (was
`fig2i_audit_trail.py`), `experiments/plots/fig2i_runtime_ecdf.py` (was
`fig2h_runtime_ecdf.py`), plus the four
`experiments/plots/output/fig2{h,i}_*.{pdf,png}` outputs; script
docstrings, usage lines and save stems updated. References swapped
across `PAPER_DRAFT.md` (Results citations + the Fig. 2 legend, whose
(h)/(i) paragraphs also traded places so the legend still runs a → i;
the Results' end-to-end sentence likewise traded its audit and runtime
clauses so the citations run Fig. 2h → Fig. 2i — "the 241-run campaign
above" became "below"),
`FIGURE_PLAN_V5.md` (Fig-2 table rows h/i contents + the
diversification-paragraph chart-type references), `PAPER_FACT_SHEET.md`
(the Exp-9/audit and Exp-8/runtime sections retitled and reordered;
**legacy** no-space records `Fig2i_ires` / `Fig2h_small_molecule` /
`fig2h 17 pairs` / `fig2_summary.json fig2i` deliberately untouched —
they name pre-reset artifacts, not the current panels), `MANUSCRIPT.md`
(reset table), this log's historical entries (re-lettered to the new
convention), `AGENTS.md` (Exp-8/Exp-9 What's-New bullets),
`experiments/exp8_runtime.py` / `exp9_audit_stats.py` docstrings, and
the frozen `exp9_audit_stats/MANIFEST.json` `experiment` field
(metadata only — the SHA-256 corpus hash entries are untouched).
`fig2_composite.{pdf,png}` regenerated.

## 2026-08-28 — Fig 2 composite assembly (a–i)

`experiments/plots/fig2_assemble.py` added →
`experiments/plots/output/fig2_composite.{pdf,png}`: the nine finished
Fig. 2 panels combined into one figure on the Nature conventions surveyed
in `relevant_references/` (bold lowercase letters at each panel's
top-left corner, strict column grid, rows top-aligned so the letters
share one line). Panels are embedded as vectors; every panel already
carries the reset programme's single 6-pt ink-black text style, so all
panels share one scale unless a row must shrink to fit. Layout
(user-directed): a (tile carpet) full width; b c and d e two per row at
scale 1.0, centred in their columns; **f g h share one row drawn at one
equal height** (f's squarer aspect made it look bigger than g/h under a
uniform row scale; per-panel scales differ, ≈ 0.59/0.67/0.71, widths
follow their aspects and the leftover width becomes even gutters),
sized so the row fills edge to edge and the first revision's empty
bottom-right half-cell disappears; i (ECDF) closes the figure full
width. After the same-day h ↔ i letter swap (entry above) the composite
reads in strict lettering order a → i. Letters Helvetica-Bold 8 pt ink
black, drawn by the assembler at one size regardless of row scale. PNG
rendered from the composite PDF at 300 dpi.

## 2026-08-28 — Fig 2h figure revision (user-directed; no data change)

`experiments/plots/fig2h_audit_trail.py` revised and regenerated
(`fig2h_audit_trail.{pdf,png}`; the Exp-9 corpus, session selection and
numbers are unchanged): the composition donut dropped — it carried three
numbers the paper already states in the Results text and the Fig. 2h caption;
the in-figure panel titles removed (Nature style — the headline lives in the
caption and panels carry letters only, the fig2d/fig2f/fig2i convention);
every text element now shares one font size (6 pt) and one colour (ink black
— the old layout's 4.8–5.6 pt labels antialiased to a pale grey); the legend
moved from floating half-outside the axes into the empty upper-right of the
milestone track; geometry changed from the double-column two-panel layout to
the single-column panel size of fig2b–g. `PAPER_DRAFT.md` Fig 2h legend,
`FIGURE_PLAN_V5.md` row i and `PAPER_FACT_SHEET.md` Fig-2h figure line
updated to match.

## 2026-08-28 — Fig 2i figure revision (user-directed; no data change)

`experiments/plots/fig2i_runtime_ecdf.py` revised and regenerated
(`fig2i_runtime_ecdf.{pdf,png}`; the Exp-8 numbers are unchanged): the
in-figure title removed (Nature style — the headline lives in the caption and
panels carry letters only, the fig2d/fig2f convention); every text element
now shares one font size (6 pt) and one colour (ink black — the legend
entries were previously set in their pale workflow colours); the box inset —
which overlapped the ECDF curves — dropped entirely (it summarized the same
samples the ECDF already shows in full, and the legend carries the medians);
the legend moved from floating at the figure's right margin to a centred row
block under the x-axis, so it reads as part of the panel; axis wording
corrected target → run (the 241-run sample times whole PA sessions as single
runs); y-range headroom added above the y = 1 step so the curve tops no
longer touch the panel edge. `PAPER_DRAFT.md` Fig 2i legend and
`FIGURE_PLAN_V5.md` row h chart-type phrase updated to match.

## 2026-08-28 — anchor set v3 Part-A extension + Exps 10–11 v3 re-runs: 9 targets / 95 entries, 2/27 and 4/27 nominal passes, none reliable

User-sequenced second curation pass (after the Fig. 3d run). Survey
(2026-08-27) vs curation outcomes — the assertion gate arbitrated:
**admitted** FGF2 (10 binders, Jellinek 1993; sequences/Kd via the
Ribocentre transcription + family-motif nesting assertions — primary PDF
bot-walled, deviation registered), swine influenza H3N2 HA (4 binders +
printed negative HA1c, Wongphatcharachai 2013; protein surrogate
A/swine/Illinois/03040/2010 full-length HA0 — selection strain
GISAID-restricted, 95.1% identity to the MN/2008 partial, registered), and
IFN-γ (B1-4 + 5 in-silico mutants, Zhao 2022; every mutant DERIVED from
B1-4 by its registered point-mutation list and asserted equal to the SI
print; M5-5 cross-checked between SI Tables S1 and S5; printed
docking-negative mutant admitted as negative). **Rejected at curation**
(two survey verdicts overturned): SARS-CoV-2 RBD (Shekar 2025 — 83-sequence
SI zip without any printed ID mapping) and HIV-1 RT FANA (Ferreira-Bravo
2015 — sequences figure-only; a vision extraction contradicted the paper's
own text-printed primer flanks). Part-A 66 → 95 entries (v2 byte-verbatim),
9 targets; docking anchors byte-identical to the first-pass v3 (asserted —
the Fig. 3d measurement unaffected); generator deterministic (md5
`7b7a71b915a2c3a181673ea3d27bdd27`); SOURCES.md second-pass section added.

- **Exp 10 v3** (`EXP_ANCHOR_SET` override, results `*_v3/`; defaults and
  v2-run records untouched): **95/95, 0 failures** (pilot 6/6; first
  attempt crashed on a generator fasta-path convention bug at the first
  new-target entry — 66 v2 records unaffected, fixed, `--resume` continued).
  **27/27 cells: 2 nominal passes > 0.8** (proteinx × swH3-HA 0.833 CI
  0.333–1.0; egarps × IFN-γ 0.833 CI 0.5–1.0) — both small-n, **all 27 CIs
  cover chance**; sensitivity 10/7/2/0; FGF2 (widest Kd span, 2.25 orders)
  sub-gate 0.47/0.43/−0.18.
- **Exp 11 v3**: **54/54, 0 failures** (pilot 4/4). **27/27 cells: 4 nominal
  ρ ≥ 0.6, all CIs span zero** — egarps/proteinx/rhofold × IFN-γ
  (+0.714/−0.226–1.0, +0.657/−0.5–1.0, +0.600/−0.6–1.0; n=6, single
  in-silico-mutant family, Kd span 0.94 orders — within-family covariation
  caveat registered) + proteinx × Ang2 (n=3). Sensitivity 8/6/4/2. Vs the
  first reset run: 10/18 v2 cells identical, rest ProteinX-realization
  variance (egarps × PDGF-BB 0.67 → 0.10 — the disclosed instability
  class). Headline invariant: no oracle–target cell shows reliable ranking
  power.
- Figures 3b/3c re-rendered on the v3 summaries (9-target data-driven
  columns/rows via `FIG3_SUMMARY`; v2 regression render verified; fig3b
  cell values gained a white halo after a vision check found two truncated
  at minimal bubble size). Docs updated: PAPER_DRAFT (Results, Fig 3 b/c
  legends, Discussion counts), PAPER_FACT_SHEET (Fig 3b/c sections + key
  numbers), FIGURE_PLAN_V5 rows b/c, MANUSCRIPT reset table.

## 2026-08-27 — Exp 12 (Fig 3d) executed under the reset + anchor set v3: docking-power profile on the extended panel, 397/399, 0/19 native top-1

Two-part delivery. (1) **Anchor set v3** (`data/benchmarks/external_anchors/aptamers/e1_anchor_set_v3.json`,
generator `experiments/curate_e1_anchor_set_v3.py`, user-approved scope
"admit every qualifying complex"): docking anchors 5 → **19 complexes / 14
independent protein targets**; Part-A 66 entries carried byte-verbatim
(asserted). Survey backbone = Troisi 2023 (144 protein–aptamer PDB entries)
+ a full-text RCSB sweep of all post-2024 "aptamer" deposits; every admitted
entry chain-composition/meth­od/resolution-verified against the RCSB API at
generation time (the assertion screen itself caught that 6RTI A9g is
2′-F-modified, missed by the survey scan). Chemistry screen rejected
SOMAmer-class and mirror-image complexes with RCSB-chemcomp-verified reasons
(4ZBN/8J1Q/7YQ3/9SA8/5UC6/4NI7/7JTN/6TXR; 4WB2/4WB3/4R8I) plus redundant
families and out-of-scope systems — 18 rejection classes registered.
(2) **Exp 12** (`experiments/exp12_docking_capability.py`, pre-registered
docstring, pilot 3/3; evidence `experiments/results/exp12_docking_capability/`):
per complex, native pose + 20 seeded rigid-body decoys; decoy parameters
offline-calibrated so the 1HVU decoy-RMSD distribution matches the retained
Part-B evidence, and the contact computation reproduces the retained 1HVU
native n_contacts = 152 exactly (protocol anchors). Instrument zero-intervention:
ToolExecutor.run_tool → deployed egarps 8023 (`academic=False` only); CapGate
advisory; every call audited.

- **399 poses attempted, 397 scored** — 2 reproducible service-side failures
  (8ZBF decoy16, 5HRU decoy13; one disclosed retry reproduced the failure;
  those complexes analysed with 20 candidates). Wall ≈ 4.6 h, median 38 s/pose.
- **0/19 complexes rank the native pose top-1** (gate ≥ 2/3 fails
  decisively); native ranks 6–20 of 21; native scores below the median decoy
  in most complexes (1HVU 0.008 vs 0.34); within-decoy Spearman(np, −RMSD)
  −0.59…+0.44.
- Vs retained: 0/5 headline invariant under the union 0/19; native-np deltas
  ≤ 0.0058 (service variance); per-complex ranks shift under the regenerated
  decoy protocol (disclosed).
- Figure `experiments/plots/fig3d_docking_lollipop.py` →
  `fig3d_docking_lollipop.{pdf,png}` (lollipop + top-1 gate line, grouped by
  protein target; terracotta EGARPS colour across Fig. 3; open markers = the
  five v2-retained anchors). Docs updated: PAPER_DRAFT (Fig 3d legend +
  Results + Discussion counts), PAPER_FACT_SHEET (E12 section + key numbers),
  FIGURE_PLAN_V5 row d, MANUSCRIPT reset table, SOURCES.md v3 section.
- **Next (user-sequenced)**: the five surveyed Part-A targets (FGF2 /
  influenza HA / HIV-1 RT FANA / SARS-CoV-2 RBD / IFN-γ) enter the same v3
  set in a second curation pass, then Exps 10–11 re-run on v3 for Figs 3b–c.

## 2026-08-27 — Exp 11 (Fig 3c) executed under the reset: structure-oracle ranking-power profile, 34/34, no reliable ranking power

Zero-intervention ranking-power profiling on the affinity subsets of the
same anchor set (`experiments/exp11_oracle_ranking_power.py`, pre-registered
docstring, pilot 4/4; evidence
`experiments/results/exp11_oracle_ranking_power/`). Subset rule = per target,
binders with measured Kd gated by `ranking_eligible` (flag defaults True
where absent — pilot-3 targets carry none), giving the retained per-target
n 6/8/5/6/3/6 = 34 entries; the rule was pre-verified by recomputing the
nine retained v2 JSONL cells to max |Δρ| = 0. ρ = Spearman(oracle score,
−log10 Kd), gate 0.6 analysis-side only. Instrument identical to Exp 10
(`ToolExecutor.run_tool` → deployed rhofold/proteinx/egarps, GPU-pinned
0/1/2 inherited; fixed protocol args only); CapGate advisory; every call
audited to `platform_audit.jsonl`.

- **34/34 successful, 0 failures** (wall ≈ 1.7 h, 164–208 s/entry).
- **18/18 cells measured; no oracle shows reliable ranking power across
  targets** — 2/18 nominal ρ ≥ 0.6 passes, both small-n with vacuous
  uncertainty (egarps × PDGF-BB n = 5, ρ = +0.667, CI −0.40–1.0, an
  ordering of near-zero scores; proteinx × Ang2 n = 3, ρ = +1.0 with two of
  three entries flipping ~0 ↔ ~1 across complex realizations); no oracle
  passes on more than one target; sensitivity 6/4/2/1 at 0.4/0.5/0.6/0.7;
  the retained best cell (rhofold × PDGF-BB +0.5643) reproduces
  bit-identically and stays sub-gate.
- Vs retained evidence: **10/18 cells identical** (all 6 RhoFold
  bit-deterministic — also re-derives the pilot-3 targets' retained ρ
  exactly); 8 shifted by ProteinX-complex realization variance (largest
  Δρ +0.5). Vs Exp-10 per-entry scores (same 34 ids): RhoFold max |Δ| = 0,
  ProteinX median 0.005, EGARPS median 1.9e-5 with 5 bimodal entries
  (max 0.9998) — the disclosed instability class.
- Figure `experiments/plots/fig3c_oracle_ranking.py` →
  `fig3c_oracle_ranking.{pdf,png}` (Cleveland dot plot, 3 oracle blocks ×
  6 targets; zero line solid / 0.6 gate dashed with nominal-pass rings;
  retained open markers + dumbbell hairlines; palette rev 7).
  `PAPER_DRAFT.md` Fig 3c legend + Results reset sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row c, `MANUSCRIPT.md` reset
  table, `AGENTS.md` updated. Docking panel 3d remains on retained evidence
  pending its own reset re-run.

## 2026-08-27 — Exp 10 (Fig 3b) executed under the reset: structure-oracle screening-power profile, 66/66, 0/18 cells pass

Zero-intervention oracle profiling on the registered aptamer anchor set
(`experiments/exp10_structure_oracle_screening.py`, pre-registered docstring,
pilot 6/6; evidence `experiments/results/exp10_structure_oracle_screening/`).
Anchor set `e1_anchor_set_v2.json` verbatim (66 entries, 6 targets;
user-confirmed after the target-count review — 6 is the discipline-exhausted
maximum). Instrument = the platform production tool path
(`ToolExecutor.run_tool` → deployed rhofold/proteinx/egarps services; DNA
scored as RNA via T→U per the anchor-set convention); CapGate advisory
(regression convention — under default enforce the three oracles are
SelfModel-governed and blocked); every call audited to
`platform_audit.jsonl` (the driver activates the audit runtime via
`runtime_from_env()`; an initial unaudited ~8-record attempt was discarded
and the run restarted from scratch — disclosed).

- **66/66 successful, 0 failures** (wall ≈ 3.3 h, 165–225 s/entry).
- **18/18 cells measured, 0/18 pass AUROC > 0.8; all 18 bootstrap 95% CIs
  cover chance**; best cell 0.800 exactly (RhoFold pLDDT × PDGF-BB);
  sensitivity 5/2/0/0 cells above 0.6/0.7/0.8/0.9.
- Secondary ranking (descriptive): ρ ≥ 0.6 only on two n = 3 Angiopoietin-2
  SPR subsets — underpowered by pre-registration.
- Vs retained evidence: **11/18 cells identical** (RhoFold bit-deterministic,
  pilot cross-check bit-identical; 5/6 ProteinX); the 6 EGARPS cells + 1
  ProteinX cell shift by ProteinX-complex realization variance (largest
  Δ +0.476, egarps × Thrombin) — headline invariant.
- Figure `experiments/plots/fig3b_oracle_screening.py` →
  `fig3b_oracle_screening.{pdf,png}` (balloon matrix; size + colour
  dual-encode AUROC, printed values, chance/gate reference lines; palette
  rev 7). `PAPER_DRAFT.md` Fig 3b legend + Results reset sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row 3b, `MANUSCRIPT.md` reset
  table updated.

## 2026-08-27 — Exp 8 (Fig 2i) executed under the reset: end-to-end runtime by workflow, 241/241, minutes-to-1 h per target

Zero-intervention timing of the 11 workflows (`experiments/exp8_runtime.py`
+ orchestrator `experiments/exp8_run_all.sh`, pre-registered docstring,
pilot 4/4; evidence `experiments/results/exp8_runtime/`). Instrument = one
`cli/form_chat.py` subprocess per run through the user form entry, inputs
verbatim, no thresholds, CapGate advisory (the documented regression
convention); services pre-warmed and GPU-pinned 0/1/2 by
`exp1_bring_up_services.sh`, so per-run time measures the delivered
workflow (pre-flight → generate → evaluate → score → rank → advisory
review → writeout), not cold model loads; lanes strictly sequential
(gpu_aptamer → gpu_tertiary → cpu → PA batch) against cross-lane
contention. Successful runs only enter the distribution.

- **241/241 successful**: all 210 RNADesign-210 tasks + all 31 PA
  regression sessions (PA_006–PA_036, each timed as one whole form
  session). Pooled median **2.6 min** (mean 4.4).
- **Workflow medians**: mRNA scoring 2.5 s; small-molecule 0.23 min; ASO
  0.28; secondary structure 1.21; IRES 1.34; siRNA 2.61; sgRNA 3.20; CDS
  3.21; tertiary structure 3.87; full-length mRNA 4.32; aptamer 6.29.
- **Completion profile**: 76.3% ≤5 min, 92.9% ≤10 min, 98.3% ≤30 min,
  **240/241 ≤1 h**. The four >30-min runs are all multi-turn aptamer PA
  sessions (42.4/42.9/59.9/**98.6** min); the single >1 h run is the GenNav
  `navigation=true` aptamer session PA_028. Suite-task maximum 27.0 min.
- **Disclosed amendment (registered before the PA_028 re-run)**: the
  PA-arm timeout (3600 s, calibrated on suite-task maxima) under-covered
  multi-turn navigation sessions — PA_027 finished at 3593 s and PA_028 was
  killed at 3600 s while progressing normally; the timeout's
  kill-only-the-direct-child semantics orphaned its turn-2 grandchild,
  which then completed (~5740 s total), exposing a driver defect now fixed
  (process-group kill). Amended budget 10800 s; PA_028 re-run once under
  it (**5917.2 s**, consistent with the orphan reconstruction); the
  original censored record retained in `pa_batch.jsonl`; the orphan's
  overlap window with PA_029 verified uncontaminating (42.63 s vs siblings
  42.15/42.52 s).
- Figure `experiments/plots/fig2i_runtime_ecdf.py` →
  `fig2i_runtime_ecdf.{pdf,png}` (log-axis ECDF per workflow + box inset,
  1 h reference line; palette rev 7 unchanged). `PAPER_DRAFT.md`,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md`, `MANUSCRIPT.md`, `AGENTS.md`
  updated.

## 2026-08-26 — Exp 7 (Fig 2g) executed under the reset: RNAsmol two-sided boundary, every registered metric reproduced

Zero-intervention re-run of the small-molecule oracle's two-sided profile
(`experiments/exp7_rnasmol_boundary.py`, pre-registered docstring, pilot
37/37; evidence `experiments/results/exp7_rnasmol_boundary/`). Instrument =
the deployed RNAsmol microservice exactly as the platform ships it (CPU
default via its own `start.sh`), one call per pair, sequences and SMILES
verbatim and **case-preserving** — the official held-out splits encode
modified bases in lowercase, and the agent tool layer's uppercase+T→U
normalization would silently re-introduce the v0.2.0 fidelity-defect class,
so the service endpoint is the fidelity-correct instrument (the retained
evidence's protocol; no ToolExecutor calls, hence no CapGate audit entries
at this layer). Checkpoint auto-selection via data-provenance hints only
(robin/pdb + molperturbation; FMN→pdb, MALAT1→robin; OOD no hints →
platform default); no thresholds, no tuning.

- **3,545/3,545 pairs scored, 0 failures**: robin test 1,492 + pdb test 170
  + FMN decoys 1,601 + MALAT1 decoys 265 + OOD panel 17.
- **Every registered metric of the retained 2026-08-11 evidence reproduced
  exactly**: robin AUROC 0.9744 (0.9678–0.9803), pdb 0.9828 (0.9607–0.9970;
  ≤500-nt subset 0.9788, n=126, 44 truncated service-side); decoy true-binder
  ranks 2/1601 (0.125 pct) and 7/265 (2.642 pct); OOD binder-vs-random-chem
  0.7222 (0.2778–1.0) and binder-vs-near-cognate 0.5625 (0.0625–1.0) — both
  CIs span chance. Verdict GO on all three axes.
- **Per-pair cross-check** vs the retained JSONL: medians ~1e-6 (MALAT1
  ≤3.8e-5, OOD ≤6.3e-4); a minority of near-decision-boundary inputs amplify
  inference-backend arithmetic (robin max 0.021 at 1/1492 pairs >1e-3; pdb
  0.047 at 1/170; FMN 0.367 at 53/1601 — one unstable near-0.5-band decoy,
  idx 367, re-scored bit-identical to confirm this run's determinism; the
  retained run's device is unrecorded). No registered metric moves. The
  cross-check tolerance was amended from bit-level to the disclosed
  4-decimal-AUROC + decoy-rank criterion **before** the full run (docstring
  records the amendment).
- Figure `experiments/plots/fig2g_rnasmol_boundary.py` →
  `fig2g_rnasmol_boundary.{pdf,png}` (forest dot + CI; khaki in-distribution
  / dark-warm-grey OOD; chance + 0.8 screening-gate reference lines; palette
  rev 7 unchanged). `PAPER_DRAFT.md` Fig 2g legend + Results sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row g and `MANUSCRIPT.md`
  reset-run table updated with the re-run as the numbers of record.

## 2026-08-25 — Platform fix: species-resolved LinearDesign codon tables; Exp 2+3 (Fig 2b–c) re-run

User-reported defect (the Exp 2+3 E. coli outliers): ``cai_species`` only
reached the CAI evaluator — LinearDesign always designed against the
service's bundled human table regardless of species (GFP / β-galactosidase
designed CAI ≈ 0.60 scored against their E. coli tables). Fixed at the
platform layer, not the driver:

- **Species-resolved codon tables**: 11 LinearDesign-format CSVs generated
  from the same Kazusa tables the CAI evaluator uses
  (``agent_core/data/codon_usage_lineardesign/``; generator
  ``scripts/gen_lineardesign_codon_tables.py`` with a ``--check`` drift
  guard used by the test suite). ``mrna_cds_design`` resolves
  ``cai_species → codon_usage_path`` on **both** the golden path and the
  GenNav navigation path; an explicit ``lineardesign_codon_usage_path``
  still wins. Human designs now use the platform Kazusa table (verified to
  produce the same argmax sequences as the bundled table). Unresolvable
  species fail fast at the input layer with a clear message instead of
  silently designing against the human table. ``full_length_mrna_design``
  inherits the fix (it delegates CDS generation to the same workflow). The
  audit trail records the codon table on every LinearDesign call (verified
  on the live run). Note: LinearDesign λ=0 is pure-MFE, so the table only
  influences λ>0 designs — confirmed live before the re-run.
- **Tests**: +10 (``tests/test_lineardesign_species_wiring.py``); the old
  "unsupported species still runs" contract test rewritten to the new
  fail-fast contract; suite **646 passed, 1 skipped**. Folded in a repair of
  a pre-existing reset breakage: ``agent_core/calibrated/
  profiling_metrics.py`` still imported the deleted
  ``experiments/analysis/stats_utils`` — ``bootstrap_auroc_ci`` inlined
  verbatim from git history.
- **Exp 2+3 re-run** (driver docstring updated; pre-fix run archived at
  ``exp2_cds_nulls_prefix/``, session prefixes ``exp2d_/exp2s_`` vs the
  re-run's ``exp2rd_/exp2rs_``): 20/20 design + 240/240 scoring, 0 failures.
  CAI medians **0.832 / 0.729 / 0.675** (designed-vs-WT P = 6.9e-4,
  δ = 0.63; WT-vs-random P = 6.8e-7, δ = 0.67; designed-vs-random
  P = 2.2e-13, δ ≈ 1.0); MFE/nt medians **−0.336 / −0.051 / −0.047**
  (designed vs both nulls δ = −1.0; WT-vs-random NS P = 0.29). E. coli
  targets after the fix: GFP 0.597 → 0.701 (above its WT 0.560),
  β-galactosidase 0.603 → 0.740 (above its WT 0.729). Figures refreshed
  (``fig2b_cai``, ``fig2c_mfe_per_nt``); PAPER_DRAFT / FIGURE_PLAN_V5 /
  MANUSCRIPT §3.0 numbers updated.

## 2026-08-25 — Exp 5 (Fig 2e) executed under the reset: IRES literature panel at chance on the default path

Paper §2.2 experiment 5 re-run against the frozen gated platform
(`experiments/exp5_ires_literature_panel.py`, pre-registration in its
docstring; pilot 6/6 then the full panel, `RNADA_CAPGATE=advisory`):

- **Panel (user-approved expansion before any run)**: positives extended
  from 3 to **9 literature IRES 5′UTRs** — the original EMCV/HCV/poliovirus
  plus FMDV (NC_004004.1:1-1058), HRV-A1 (NC_038311.1:1-626), BVDV-1
  (NC_001461.1:1-385) and the three cellular IRES the asset table had
  promised but never landed (c-myc NM_002467.6:1-363, Bip/GRP78
  NM_005347.5:1-217, VEGF-A NM_001025366.3:1-496; ranges = 1..CDS_start−1,
  provenance recorded in the anchor `SOURCES.md`); negatives unchanged (50
  GENCODE v46 200-nt 5′UTR windows). n = 59.
- **Zero-intervention rule (user-directed)**: one `ires_prediction`
  workflow run per sequence with platform defaults; the only deviation is
  `probability_threshold=0.0`, registered before the pilot — the threshold
  is a labelling knob (the service computes every fragment's probability
  regardless), and 0.0 merely disables the label filter so raw
  probabilities reach the workflow's score/rank layer for below-threshold
  sequences. Threshold-free AUROC over the raw scores; ROC + pointwise 95%
  TPR band via stratified bootstrap (10⁴ replicates, seed 20260825).
- **Primary result (pre-registered mode-0 arm — the workflow default)**:
  59/59 scored, 0 failures; **AUROC 0.478 (95% CI 0.311–0.649),
  Mann–Whitney P = 0.841 — indistinguishable from chance**. 20/50
  negatives score above 0.5 (median 0.449); score–length correlation
  r = 0.018 (not a length artifact). The legacy 3-positive-panel 0.762
  does **not** reproduce: the legacy-3 subset against the same 50
  negatives scores 0.513 (legacy protocol unrecoverable — deleted in the
  reset; this re-derivation is the number of record).
- **Disclosed mode-2 addendum arm** (registered after the primary was
  known, never substituted for it): sliding-window scanning at upstream
  defaults (window 174 / step 50 — the native regime; removes the
  341–1058-nt-vs-200-nt regime mismatch between positives and negatives).
  **AUROC 0.673 (95% CI 0.467–0.862), P = 0.102** — directionally better,
  CI still spans 0.5, and the estimate sits exactly where E16 graded the
  oracle on IRESfinder's own held-out sets (0.68/0.73/0.76, all below the
  0.8 screening gate → enforce-gated). The calibrated self-knowledge and
  the literature panel agree: the deployed IRES oracle has ~0.7
  discrimination at best and the default full-sequence path has none.
- Evidence `results/exp5_ires_panel/` (`panel_runs.jsonl`,
  `panel_runs_mode2.jsonl`, `summary.json`, `roc_points_{mode0,mode2}.csv`);
  figures `experiments/plots/fig2e_ires_roc.py` →
  `plots/output/fig2e_ires_roc.{pdf,png}` and
  `fig2e_ires_roc_mode0.{pdf,png}` (all palette rev 7; the workflow's warm
  grey `#B7B0A2`, chance diagonal in neutral grid). **Figure endpoint
  re-registered to the mode-2 scanning arm (user direction, 2026-08-26)**:
  the canonical `fig2e_ires_roc.*` now renders mode-2 (AUROC 0.673) — it is
  the legacy panel's protocol (legacy per-sequence scores match this arm
  exactly, confirmed against `PAPER_FACT_SHEET.md`) and the oracle's native
  window regime; the pre-registered mode-0 default-path result stays the
  primary analysis record and its figure is archived as
  `fig2e_ires_roc_mode0.*`. No scores were recomputed.
- `docs/MANUSCRIPT.md` asset table + §3.0 programme table updated;
  `docs/FIGURE_PLAN_V5.md` row 2e and the `PAPER_DRAFT.md` Fig. 2e
  legend/Results observation (3) updated to the measured numbers (and the
  stale "EMCV 0.808, poliovirus 0.891 literature-panel reproduction"
  parenthetical dropped — those were task-protocol scores, not panel
  scores).

## 2026-08-25 — Exp 4 (Fig 2d) executed under the reset: inverse folding 21/25 exact

Paper §2.2 experiment 4 re-run against the frozen gated platform
(`experiments/exp4_inverse_folding.py`, pre-registration in its docstring;
pilot 5/5 then the full 25-task matrix, `RNADA_CAPGATE=advisory`):

- **Zero-intervention rule (user-directed)**: the platform is measured
  as-is — no threshold presets, no objective tuning, no parameter sweeps;
  task inputs fed verbatim from RNADesign-210
  `06_rna_secondary_structure` (25 targets, 9–54 nt, 4–70 °C, function
  modes m/p/mp, start-sequence constraints). The single arm is the
  `rna_secondary_structure_design` golden path (RNAinverse ×N → RNAfold
  fold-back validation + GC → scoring → ranking).
- **Primary metric**: best-ranked candidate dot-bracket Hamming distance to
  the target (the platform's own `structure_distance`; 0 = exact recovery).
  Secondary: base-pair distance (analysis-side), per-candidate profile,
  any-candidate-exact (generation vs delivery).
- **Results**: 25/25 runs successful; **21/25 exact recovery** (dot-bracket
  distances 0×21, 2, 2, 4, 6; base-pair distances of the four misses
  1, 2, 3, 1 — at most 3 of 10–14 target pairs). All four misses are
  mp-mode / combined-parameter / extreme-temperature / longest-target edge
  tasks (015, 018, 021, 024); no candidate in any miss's ranked set was
  exact (generation-limited, not ranking-limited). Categories: basic 1/1,
  edge 19/21, full 1/3. The pre-reset run and the Exp-1 lane had observed
  22/25 (different stochastic realization; RNAinverse is stochastic) —
  this run's 21/25 is the number of record.
  Evidence `results/exp4_inverse_folding/` (`pilot.jsonl`, `records.jsonl`,
  `summary.json`); figure `experiments/plots/fig2d_inverse_folding.py` →
  `plots/output/fig2d_inverse_folding.{pdf,png}` (strip + step cumulative
  curve; exact dots in the workflow's grey green `#8DA290`, misses in the
  reserved dark warm grey `#7A7672`, cumulative curve slate blue
  `#6B7B8D` — all from palette rev 7).
- Driver fix during analysis: base-pair distance corrected to the standard
  |P₁ Δ P₂| definition (an integer-halving slip mis-scored asymmetric
  stem extensions; recomputed from the stored structure strings, no
  platform re-run).
- `docs/PAPER_DRAFT.md` Results §2.2 observation (2) and the Fig. 2d
  legend updated to 21/25; `docs/FIGURE_PLAN_V5.md` row 2d re-pointed to
  the new evidence path.

## 2026-08-25 — Exp 2+3 (Fig 2b–c) executed under the reset; fig 2c re-registered as a three-arm panel

Paper §2.2 experiments 2 and 3 merged into one driver and re-run against the
frozen gated platform (`experiments/exp2_cds_null_model.py`, pre-registration
in its docstring; pilot 3/3 then full matrix, `RNADA_CAPGATE=advisory`):

- **Designed arm = the system's CDS golden path as-is** (user-directed):
  `mrna_cds_design` with `design_tool="all"` — LinearDesign λ∈{0,1,4,10} +
  RNARL + GEMORNA, each candidate folded (LinearFold), GC/CAI/RNASTOP-scored
  and ranked; the best-ranked candidate is the arm's data point. No λ or
  codon-table tuning (the legacy "pure-CAI LinearDesign" attribution is not
  reconstructible and is replaced by this registration).
- **Null arms**: WT = the 20 NCBI RefSeq `wt_cds/` anchors; random = 10
  seeded synonymous resamples per WT (n = 200, uniform over the standard
  code, seed `exp2:<target>:<draw>`, deterministic). One scoring path for
  all 240 sequences (`mrna_sequence_scoring`: CAI via Kazusa tables,
  species-resolved + GC + LinearFold MFE).
- **Results**: design 20/20, scoring 240/240, zero failures. CAI medians
  **0.830 / 0.729 / 0.675** (designed > WT > random gate PASS;
  designed-vs-WT P = 7.1e-3 δ = 0.50; WT-vs-random P = 6.8e-7 δ = 0.67).
  MFE/nt medians **−0.336 / −0.051 / −0.047** (designed vs both nulls
  P ≤ 7e-8, δ = −1.0; WT-vs-random NS P = 0.29).
- **Fig 2c re-registered (user-directed)**: the legacy WT-vs-random-only
  folding control becomes a full three-arm MFE/nt panel — the designed CDSs
  lead on codon adaptation and structure simultaneously, and the WT≈random
  null contrast shows the CAI ordering is not a folding artifact. Evidence
  `results/exp2_cds_nulls/` (`design_runs.jsonl`, `fig2_cds_nulls.jsonl`,
  `summary.json`); figures `experiments/plots/fig2bc_cds_nulls.py` →
  `plots/output/fig2b_cai.{pdf,png}`, `fig2c_mfe_per_nt.{pdf,png}`.
- **Palette**: `ARM_COLORS` semantic slots added to `experiments/plots/palette.py`
  under rev 7 (designed = terracotta `#C08B7C`, WT = sage `#A3B18A`,
  random = the reserved dark warm grey `#7A7672`); Fig 2a re-rendered.
- `docs/PAPER_DRAFT.md` Results §2.2 observation (1) and the Fig. 2 legend
  rewritten to the reset numbers; `docs/FIGURE_PLAN_V5.md` rows 2b/2c and
  `docs/MANUSCRIPT.md` §3.0 register updated. Known recorded caveats: the
  two E. coli targets (GFP, β-galactosidase) are designed against
  LinearDesign's default human codon table (frozen-platform behaviour,
  documented in the driver docstring) and the Influenza HA WT anchor derives
  from a different strain than the benchmark protein (pre-existing anchor
  documentation).

## 2026-08-25 (z) — Experiment-programme reset: legacy campaigns deleted, RNADesign-210 audited+repaired, Exp 1 re-run 210/210

User-directed reset (DECISIONS (z)): the architecture moved too much since
the legacy campaigns, so **all paper experiments re-run against the frozen
gated platform** with newly written drivers and figures; the legacy campaign
drivers (`run_platform_quality_benchmark.py`, `run_e16_e17_e18_oracle_profiling.py`,
`curate_*`), the `experiments/analysis` helpers, the `experiments/plots/paper_v5`
figure programme and the legacy campaign results (fig2–fig7, E3–E15, P0–P3,
junction line, PA regressions, caches/logs) are deleted. Retained: the
packaged-SelfModel evidence chain (`e1_*_v2`, `e7_*`, `rnasmol_boundary_panel*`,
`e16_e17_e18/`, `build_default_self_model.py`), `codon_tables/`,
`tool_inventory.json`, `MODEL_API_USAGE.md`, the workspace audit trail.

**RNADesign-210 dataset audit and repair** (`experiments/audit_rnadesign210.py`
+ `fix_rnadesign210.py`, report `results/rnadesign210_audit.json`): all 210
task inputs validate against the current workflow Input models; benchmark
manifest recounts (208→210, tertiary 18→20); category taxonomy normalized to
basic/edge/full (was 14 ad-hoc values incl. BMC-era labels); the 12 IRES tasks
rebuilt on real IRES-positive anchors (poliovirus 5′UTR for mode 0 — the old
synthetic 5′UTR scores 0.458 < its own 0.5 task threshold and mode-0 scores
of canonical IRES 5′UTRs peak ≈0.48, so the two mode-0 detection tasks use
0.45 with the rationale recorded in-task; EMCV 5′UTR for mode 2; best window
251–424 for mode 1); absolute IRES paths → repo-relative; stale junction-tool
expected chains dropped; all expected chains regrounded from observed traces
(`reground_tool_chains.py`; re-audit: 0 issues / 0 warnings).

**Exp 1 (paper §2.2 experiment 1, Fig. 2a) executed**: pilot 10/11 (the one
failure was the IRES data defect, fixed and verified 12/12 against the live
service), then the full matrix — **210/210 successful across the 11 workflows**
(primary arm `RNADA_CAPGATE=advisory`; five parallel lanes; GPU-pinned services
via `experiments/exp1_bring_up_services.sh`; records and per-workflow medians
in `results/exp1_rnadesign210/`). A 4-task **enforce probe** documents the
gated-platform boundary as data: IRES tasks refuse with an explicit
`GatedActionError`, small-molecule tasks fail cleanly with both oracles gated
(`enforce_probe.jsonl`). **Fig 2a** rendered (per-task tile carpet + horizontal
bar summary) from the new **unified palette**
(`experiments/plots/palette.py`). Palette history: rev 1 = the ten mandated
colours; rev 2 = a 12-colour replacement (withdrawn same day); rev 3 = ten
colours + two in-family extensions (withdrawn same day); rev 4 = twelve
colours extracted from a user reference figure (withdrawn same day);
rev 5 = the user's muted Morandi set (withdrawn same day);
rev 6 = the user's cool pastel set (withdrawn same day);
**rev 7 (final, user-confirmed 2026-08-25)** = the earthy Morandi
twelve-colour set, supplied directly (`#B5838D #D3B5B0 #C08B7C #D9C3A9
#CDBF9E #A3B18A #8DA290 #8FA6BB #6B7B8D #A99AAF #B7B0A2 #7A7672`) — eleven
identify the workflows (#7A7672 dark warm grey held out, reserved for
neutral-dark semantics such as failed tiles); warm and cool tones alternate,
slate blue separates the palest warms. All subsequent experiment figures use
rev 7 exclusively (DECISIONS (z)).

## 2026-08-25 — Paper figure-lettering unification (doc-only)

All six figure legends in `docs/PAPER_DRAFT.md` re-lettered to
`docs/FIGURE_PLAN_V5.md` (the operative build plan for
`experiments/plots/paper_v5/`). The v5 figure rebuild had updated the
Results body citations and the built figures, but the legends kept
pre-rebuild lettering — stale in Figs. 1 (b/c/f), 2 (g–i), 3 (f–i),
4 (c–i), 5 (d–i) and 6 (missing g–i). Body text gained citations for
previously unreferenced panels (Fig. 1c,f; 2g; 4g,i; 6g–i); the
representative-claims examples moved from main Fig. 4 to the planned
Supplementary Table S1, now registered in the figure plan alongside the
GenNav aptamer supplementary archive. Draft endnote panel counts corrected
(6 + 9×5; "End of draft v4.3" → v4.5). No numbers changed — lettering and
cross-references only. Same day, the first Results subsection was split
into a system-design subsection ("Overview of the RNADesignAgent platform",
Fig. 1) and the RNADesign-210 biological-validity results subsection
(Fig. 2), so experimental results begin with the second Results
subsection; content unchanged apart from the new heading. A legacy→v5
panel-lettering map was added to `docs/PAPER_FACT_SHEET.md` (legacy letters
double as `fig2_summary.json` keys and are kept verbatim), and the AGENTS.md
What's New index records the pass.

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
