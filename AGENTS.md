# Agent Guidelines for RNA_real_agent

> **Consolidated index.** Authoritative documentation lives in `rna_agent_system/docs/`.
> **Last updated**: 2026-09-09 (论文全量一致性审计+修正（用户指示）— 所有图/表/正文数字对照冻结结果文件逐一核验；Fig 1 同日重建为四面板（PPT2 原生形状）。此前：平台变更 DECISIONS (bb) — 全长两步重设计+治理化 UTR 池；Exp 24/18/37 caseA 重跑队列。可用 GPU 0/1/2)

## What's New

> Condensed register (compressed 2026-09-02 from narrative entries; details — protocols, pre-registrations, amendments, disclosures, figure-QA rounds — are in `docs/CHANGELOG.md` under the matching dates). Driver pattern for every reset experiment: `experiments/expN_*.py`, pre-registered docstring, pilot-first, zero-intervention production tool path (`ToolExecutor.run_tool`), `RNADA_CAPGATE=advisory` unless gating is the object of study, palette rev 7 figures (absolute mm, 6-pt pure-black text, 1200-dpi PNG + vector PDF), `--verify` byte-identical recomputation.

- **论文全量一致性审计与修正（2026-09-09，用户指示）**: 计算实验全部完成后，逐条核验 PAPER_DRAFT 每个数字 vs `experiments/results/` 冻结文件 + 每个面板的实际渲染数据。修正：(i) **Table 1 caseA** 重基到 (bb) 重跑（6.8 h / 108 候选 / CAI 0.959 vs 0.952，生成 UTR 胜出基准池——原文残留 (aa) 时代 6.6 h / 0.969）；(ii) **Fig 4f** 正文+图例+面板全部重基到 (bb) 门统计（4,862 = 1,800r/489p/1,391d/**1,182a**——allow 类此前正文残留首-reset 的 1,392 [709/549/134]、图例残留 (aa) 的 1,356 [616/586/154]、面板漏画 allow；fig2h 面板同补 allow 272）；(iii) **fig2i** 脚本 glob 缺陷修复（`pa_batch.jsonl` 定名漏掉 (bb) 按工作流分片的 `pa_batch_w*.jsonl`——面板曾只画 210 任务；现 241 会话入图）+ 正文/图例中位数区间更正为汇总语料值 2.8 s–8.9 min（原 2.5 s/8.8 min 分别为最小值与 210-子集值）；(iv) **Fig 4g/4h** 核验出 09-05 PA_028-v4 刷新后的真实状态：review-on **145** 调用（72×2+重试首轮 1）、retries **0/1/0**（原正文 144/0-0-0 残留 09-01 态）、Exp 24 review 调用 **483**（原 482）、Exp 18 **80**/40（fig4h 数据 JSON 曾残留 92/46、490/245 中间态）；导航战役按登记计划入图（Exp 27/28/29 零 LLM、Exp 30 = 22/11、Exp 37 = 8/3）；(v) **fig4d** 面板补画 (bb) 时代 1 个 ClaimGate 抑制块（深暖灰独立 key，图例原已声明）+ 图例 1/12→1/13；(vi) Exp 15 v0.2.0 复现一致界更正 ≤0.009→0.0094；siRNA 扫描句精确化（3 请求 2 执行）；Methods PA 套件 19→31、ASF 工作流 5→**6**（代码核实 `apply_reference_point_ranking` 调用含 aso_target_screening）、Statistics 删 memory 孤儿句并更新适配体 McNemar 登记（n=60/36/24 + 39 靶扫描）；(vii) **Fig 1** 同日经用户 16 点反馈重建为**四面板**（删旧 c 规模/审计 donut 与旧 f 基准 sunburst，旧 d/e 重编号 c/d；`PPT2/{panel_a..d}.py` + `build_pptx.py` 原生形状零图片）——正文引用 (Fig. 1c/1d) 与图例同步重写字。Data availability 补 exp29/30/31/37；页脚改为真实 `experiments/plots/` 布局 + 五图清单。FACT_SHEET 补 Exp 2+3 (aa) 节（Fig 2b/c 0.896/0.729/0.675 此前缺登记）+ §6#2 取代注记；FIGURE_PLAN 头部/Fig 1 表/2b/2c/2h/2i/4d/4f/4g/4h/5e（pooled 40:40）/5h（去 inset）行全量同步；MANUSCRIPT Exp 24/25 行同步。fig2/fig4 组合图重装配，raster QA 绿。
- **Fig 1 四面板重建（2026-09-09，用户 16 点反馈）**: 六面板→四面板（a 端到端+七层骨架+11 工作流芯片+两条设计承诺；b = L4 多智能体主流（PipelineAgent→SpecialistAgent〔generate/evaluate/score/ASF rank 内嵌第 4 步〕→SynthesisAgent→ClaimGate→产出，QualityAgent 顾问侧挂，删除已证伪 coordination loop）；c = CapGate 三段式（锚集→预登记 profiling→SelfModel→DecisionGate+ClaimGate→审计轨）；d = GenNav 三段式（profile→probe→allocate→deliver-or-degrade，格点导航图）；全图纯黑 Arial 三档字号，`build_pptx.py` 重写为 python-pptx 原生形状（零图片、PPT 内全可编辑）。

- **平台变更 — 全长 mRNA 两步重设计 + 治理化 UTR 池（2026-09-07，用户指示，DECISIONS (bb)，湿实验计划驱动）**: `full_length_mrna_design` 改两步协议（先按导航 profile 选 ≤3 CDS，再配每 run 一个 UTR 池 = GEMORNA 筛选规模 12+10 抽样 + 断言校验基准池：BNT162b2 UTR 对（5'UTR 模板验证 51-nt 形 / 3'UTR 94-nt AES–mtRNR1）+ LinearDesign 论文 5'UTR + 天然 HBA1 对）；准入规则只收文献定量阈值（U1 无 uAUG、U2 无 II 类 ARE、U3 帽入口 −30 kcal/mol、U4 扫描路径 −61 kcal/mol —— Kozak 1989/Sample 2019/Chen & Shyu 1995；无阈值的 U 含量/GU-motif/AAUAAA 明确不加）；`utr3_stability` 降级为报告诊断（unprofiled oracle 不再参与排序）；输出维持 5'UTR+CDS+3'UTR（不加尾不加帽）。测试 **686 passed 1 skipped**。受影响重跑：**Exp 24**（图 2a/2h/2i/4f）→ **Exp 18**（图 4d）→ **Exp 37 caseA**（表 1）；exp26/27/28/30/31 与其余战役不受影响（自含冰冻仪器）。改动前 in-flight 的 caseA 第三次运行保留为内部登记。

- **Exp 37 / 表 1 caseA 重跑（2026-09-07，DECISIONS (bb) 两步平台）**: Spike 全长 24,320 s = 6.8 h（无上限）、**108 候选**（3 导航 CDS × 6×6 UTR 短名单）；best = gennav λ5.5（CAI 0.9590 > BNT162b2 锚 0.9515）× **GEMORNA 生成 UTR（long_4×long_1）在认证 MRL oracle 上胜过池内临床基准对**——基准同池竞争、公平落败，机制按设计运转；导航 35/35 预算、stability 零交付边界如实披露；改动前登记归档 caseA_prebb（23,907 s、54 候选、旧 3×3 网格）。caseB（anti-VEGF 适配体 23.4 min 自审案例）/caseC（NSP12 siRNA 106 s）不受 (bb) 影响、沿用 2026-09-06 记录。论文案例 A 段、图例(a)、FACT_SHEET 表 1 节、MANUSCRIPT 行全部重基。
- **平台默认变更收官（2026-09-06→07，用户指示，DECISIONS (aa)）— 受影响实验重跑全部完成 + Exp 37（表 1）落地**: Exp 2+3 20/20（CAI 0.896>0.729>0.675，P=1.1e-06 δ=0.91；MFE/nt −0.297 δ=−1.0）；Exp 24 241/241 + 冻结 11,003 事件/1,356 门决策（616/586/154，8 导航会话于 context 修复后替换，184 已知缺陷披露）；Exp 18 FP 36.4%→8.3%（削减 77.1% 门 PASS）、保留 78.6%<90% 如实报告（三损失=相对口径降级）；Exp 25 93/93+verify 一致；Exp 37：(A) Spike 全长默认流 6.6 h、CAI **0.969>BNT162b2 0.952**、导航 35/35+stability 零交付披露，(B) anti-VEGF v4 导航 23.4 min 自审示例（top EGARPS 被快速指标门跳过、同链锚点 0.365），(C) NSP12 siRNA 106 s 零脱靶，`--verify` 全绿。论文全量重基（§2.2/§2.4/§2.7/表 1/摘要/贡献/Methods/图例）；Fig 6 移除。工程：探测并发 2→4、时间上限废除（看门狗 60 s 自动恢复监控）、常驻 ODesign 舰队、contextvars 传播修复（平台缺陷）。此前条目： `mrna_cds_design` v2.0.0 三态 `navigation`（未设置+默认配方 "all" → GenNav-λ；钉引擎 → 静态配方逐字保留；True/False 覆盖；`resolved_navigation` 单一解析点，物种 fail-fast 跟随解析后模式）；`full_length_mrna_design` 同语义透传委托（默认策略单一来源 = CDS 层，导航 trace 入合并 writeback，导航 CDS × 3×3 UTR 组合不变——pilot Insulin 99 候选、best=`full_length:cds_design_gennav:lambda1.75:...`、ASF 带 CapGate 治理标记）；CapGate 确认默认在线（审计+门决策+排名治理，模式无关）；适配体导航保持 opt-in（证据双向）。测试 **672 passed 1 skipped**。受影响重跑（同指示，串行队列）：**Exp 2+3**（图 2b/c designed 臂=新默认流；静态时代归档 `exp2_cds_nulls_static/`，前缀 `exp2nd_/exp2ns_`）→ **Exp 24**（图 2a/2h/2i/4f）→ **Exp 18**（图 4d 资产重建+双臂）+ **Exp 25**（图 4g）→ **Exp 37 表 1 三案例**（Spike 全长新默认 / anti-VEGF 适配体 v4 导航〔行 B 统一决定：盘上无 EGF 资产，沿用 VEGF+pegaptanib 锚点与自审叙事〕/ NSP12 siRNA——driver `exp37_table1_case_studies.py`，pilot 已过：case C 87 s 全绿）。exp26/27/28/30/31 与适配体/siRNA/结构/小分子战役不受影响（显式钉旗或自建池）。Fig 6（§2.6 预注册阴性边界）经用户指示**移出本论文**（转为湿实验小节素材）。

- **Exp 31 / Fig 5d — Fig 5 COMPLETE (2026-09-05, figure-only)**: the Exp-28 secondary-endpoint panel rendered from frozen data (`exp31_fig5d_secondary.py` → `panel_data.json`, every number recomputed from the Exp-28 records + asserted equal to its verdict, `--verify` byte-identical; no prior fig5d existed in this reset). Three blocks — criteria bullet bars (gene-e2e conjunct **0.45 = 9/20 vs 0.8 legacy gate**, rule pool 1.00 = 20/20 context; constraint rate **0.944 ≥ 0.9 TRUE**), Δ-composite stacked dots (**+24/=18/−18, Wilcoxon P = 0.73 NS**), per-target spend strip (mean 24.55/35, 10 at cap + 10 early-stop, **0 violations · 0 LLM**); text-collision guards + raster QA GREEN; 89×74 mm. PAPER_DRAFT legend (d) + §2.5 Fig. 5d citation, FIGURE_PLAN row d, FACT_SHEET Exp 31, MANUSCRIPT E6 row synced. **2026-09-08 user-directed single-view repair (the fig5a/5b/5c one-plot-per-panel convention)**: bullet bars + spend strip removed — the panel is the Δ-composite stacked-dot distribution alone (the two removed blocks shared neither axis nor observation unit with it; their numbers are text-reported verbatim in the Fig. 5d caption and §2.5; the two gate dashes 0.8/0.9 = two distinct pre-registered criteria, not one standard, and the solid mean tick are gone from the panel); 89×74 → 89×35 mm; raster QA GREEN, `--verify` still byte-identical.

- **Exp 29 / Fig 5e–5h COMPLETE incl expanded pool (2026-09-03→05, the paper's citation)**: 20-pool v4 arc — seg3 **10:3 P=0.092 (delivered 24:17, e2e 4:0 nav-only)**, seg4 1:8 (disclosed), pooled parity at 48; **expanded 39-target budget sweep (RNA-BioBench-Aptamer-Expanded: 12 docking-anchor complex proteins + 7 anchor-fasta/ProteinX-folded) — cap16 10:2 P=0.039 SIGNIFICANT nav win (the aptamer-side promotion point), cap20 9:4, cap24 18:15, cap32 10:22 P=0.050 and cap48 12:30 P=0.008 static wins (both disclosed — the two-sided regime characterization)**; full curve nav [10,9,18,17,34] vs static [2,4,15,29,52] in `expanded_summary.json`. Production: v4 navigator (least-served band rotation + shrinkage/UCB + D1-aware gaps), `navigation_raw_budget` knob, 650+ tests green; **resident ODesign services** (model weights resident on GPU, ~22 s/request vs ~90 s subprocess path, byte-identical outputs; launcher `microservices/odesign_service/start_resident.sh`; two mid-run shutdowns saved/resumed via RESTORE_NOTE). fig5e/f/g/h re-rendered on final data, raster QA green; §2.5 + legend + FIGURE_PLAN + FACT_SHEET re-based. **2026-09-08 user-directed single-view repair (the fig5a/5b/5c/5d one-plot-per-panel convention)**: fig5f's bottom pair-outcome strip removed (its counts 14/10/3/9 are the fig5g mosaic tiles, text-reported in the captions) and the floating in-axes NO-GO text merged into a fig5b-convention stat line above the axes; "Targets e2e" spelt out "End-to-end targets"; key reduced to the two arm swatches as one column at the axes' upper right (same-day user direction); canvas 89×56 → 89×40 mm; raster QA GREEN; PAPER_DRAFT legend (f)'s stale pre-repair numbers (16:17/8:9/P=1) corrected to the v4 data (24:17/10:3/P=0.092). **2026-09-08 user-directed fig5g repair (the fig5c template)**: target-name row labels restored (the marker axes' sharey + set_yticks([]) had wiped the shared y ticks — the side whitespace was the empty label block); "Target e2e" floating two-line title → "End-to-end" single-line fourth column header on the profile-header baseline; content block horizontally centred, tiles 11.5 → 14.7 mm (fig5c tile geometry), canvas 89×80 → 89×71.2 mm; top context strip added; two-row key with per-class counts (10/14/3/9) + the e2e glyph legend (4 delivered / 8 not); open-marker outline #D9D9D9 → palette warm grey; raster QA GREEN. **2026-09-08 user-directed fig5h repair (same one-plot-per-panel convention)**: the aptamer breakthrough step-line inset removed from fig5h (its numbers — IFN-γ steps up at 29/35/47 raw, PDGF-BB 36/48, swine H3 HA flat to the cap — text-reported in the Fig. 5h caption and §2.5); all text unified to one 6-pt pure-black style; per-arm two-row key (the fig5g convention, one marker per row) carries cells + mean raw; cap labels and in-axes stat lines removed; the coincident PTH/CSF3 pair drawn as one marker with a shared label; collision guards extended to text–marker (0.4 mm clearance); canvas 89×62 → 89×52.5 mm; raster QA GREEN; PAPER_DRAFT legend (h) + §2.5, FIGURE_PLAN row 5h, FACT_SHEET synced.
- **Fourth programme reset opened** (2026-09-02, user-directed — architecture changed again): ALL paper experiments re-run with newly written code **one experiment at a time** — old code/results/figures/docs of the experiment being re-run may be deleted, all other files untouched. Palette rev 7 (12-colour Morandi set) re-confirmed verbatim; usable GPUs 0/1/2 (`experiments/exp1_bring_up_services.sh`). The paper presents the latest re-run results only; old-vs-new comparisons stay in the internal registers.
- **Exp 28 / Fig 5b+5c (repaired system)** (2026-09-02→03, `experiments/exp28_gennav_mrna_endpoint_v2.py`, zero LLM, 20/20): the E6/S2 endpoint re-run against the REPAIRED production navigator after Exp 27's 0:24 starvation boundary — budget matching (35 raw calls/arm, violations 0), densified 35-λ lattice, constraint bands anchored dimension-by-dimension to the registered matrix (CAI 0.80 all bands incl. stability, CDS-level stem ≤30bp=C7 new dimension, GC [0.30,0.80]=C1, homo<14=C2), the legacy E6 synonymous-diversity expander restored (zero generation budget), CDS-level D1 floor 0.03 (P3 calibration), parallel memory-adaptive probe. **Paired discordance significant favouring navigation: b:c = 17:6, McNemar p = 0.0347, n = 60**; navigation 35/60 JCD cells vs rule 24/60; HER2 delivers (legacy zero-feasible target); GFP the counter-boundary (3 rule-only cells); c_e2e_gene 0.45 < 0.8 conjunct + composite secondary disclosed; three pilot rounds of root-cause calibration; tests 25+110 green; `--verify` byte-identical; fig5b/5c re-rendered on exp28 data, raster QA green. Machine change 2026-09-03 (user-directed): usable GPU = 0 only, bring-up repinned, mid-run shutdown saved/resumed via RESTORE_NOTE. Paper re-based to the repaired-system results (abstract, contribution 4, §2.5, Discussion, Fig 5 legend b–d, Methods, LLM usage, data availability); Exp 27 = internal boundary register. **Next: rest of Fig 5 (aptamer campaigns e–h) and Fig 6, same pattern.**
- **Exp 27 / Fig 5b+5c (boundary measurement)** (2026-09-02, `exp27_gennav_mrna_endpoint.py`, zero LLM): pre-repair boundary — the v1 shipped defaults failed the endpoint 0:24 (batch starvation: 49/60 cells <5 delivered); mechanism criteria passed (D1 56/60, D2 55/60, R3 20/20 vs rule 53/35/8) — the internal register that motivated the Exp-28 repair. Same-day dataset-record fixes (user-directed): FullLength-mRNA manifest/sequences/README corrected to the operative 20-target set.
- **Exp 26 / Fig 5a** (2026-09-02, `experiments/exp26_selection_layer_pool.py`, zero LLM): selection-layer pool-failure re-measurement, S1 five targets (A1AT/Insulin/EPO/GFP/IL-2) × 315 full-length constructs (LinearDesign λ{0,1,4,10} + RNARL + GEMORNA 30×9), legacy protocol recovered verbatim from git `b6dad08`. 6/6 cells: pass counts EPO 306 / IL-2 297 / Insulin 144 / A1AT 27 / **GFP 0/315 default human codon table → 18/315 E. coli table** (passing candidates confined to the λ{4,10} gears — the B0 species-table defect reproduced); Insulin delivered-batch diversity 1.01% < 2% gate (λ-saturation failure reproduced); dominant binding constraint C1 sliding GC; `--verify` byte-identical.
- **Exp 25 / Fig 4g+4h** (2026-09-01, `exp25_quality_review_advisory.py` + `exp25_fig4h_data.py`): quality-review advisory three-arm re-run, 31 PA sessions × arms (off / on / on+API-outage) = **93/93 form-entry CLI runs**. Paired per-turn outcome identity TRUE (0 mismatches — the advisory property measured on every session); sole workflow-level exception PA_023 fails identically in all arms (inherited fixture gap `workspace/pa023_5utr.fa`, same FileNotFoundError in the frozen exp8/exp24 corpora — disclosed as measured, not recreated). Outage arm: 144 failed review calls → `review_unavailable` zero-confidence-pass markers, no turn killed. New `RNADA_QUALITY_REVIEW` env knob in `cli/form_chat.py` (default on). Fig 4h LLM usage: Exp 5 = 90, Exp 17 = 90, Exp 18 = 80, Exp 23 = 0, Exp 24 = 482 (mean 2.0/run), Exp 25 arms 0/144/0.
- **Exp 24 / Fig 4f + Fig 2a/2h/2i re-run（第三次，2026-09-07，DECISIONS (bb) 两步全长重设计平台，论文引用口径）**: 241/241 全成功；冻结审计切片 24,897 事件 = 19,848 工具调用（40 工具、3 个孤立 iresfinder FileNotFoundError）+ 4,862 门决策（1,800r/489p/1,391d/**1,182a——首个非零 allow 类 = 降级后的 gemorna_3utr 注记用途**，11 oracle）+ 187 排名装配；代表会话 PA_036（全长、3 轮、2,738 事件、1,853 调用、882 门）；运行时中位 2.5 min、全长道中位 8.8 min 成为最慢中位工作流（治理池成本）、239/241 ≤1 h（两例外：856-aa GenNav CDS 任务 70.7 min、适配体 PA_028 72.3 min）；战役墙钟 ≈6.0 h（与 exp18 builder 重叠披露）；`--verify` 字节级一致；前两时代归档 `_utrgrid/`、`_static/`。
- **Exp 23 / Fig 4e** (2026-09-01, `exp23_selective_gating.py`, 0 LLM): selective-gating decision matrix under `RNADA_CAPGATE=enforce` + packaged default SelfModel. **12/12 cells met pre-registered expectations (GO)**: DecisionGate allow ×3 (conf 1.0) / downgrade (conf exactly 0.5 = 1.0 × 0.5 transfer decay) / require_profiling ×2 blocked; ClaimGate pass / downgrade (absolute → within_target_relative) / reject; enforcement layer — allow executes (predicted MRL exactly the Exp-14 cached value), downgrade executes (capping is ClaimGate's job), require_profiling blocked pre-call (GatedActionError, no service call).
- **Exp 18 / Fig 4d 重跑（第三次，2026-09-07，DECISIONS (bb) 两步全长平台，论文引用口径）**: E3-M 双臂 40/40——FP 33.3%（6/18）→ 7.7%（1/13，相对降幅 76.9%），**TP 保持 12/12=100%，双预注册门全过**（上一 navgrid 时代 TP 78.6% 未达门——损失全部来自 never-profiled 家族降级，而两步 workflow 不再在未认证 3′UTR oracle 上排序后此类声明不再产生，治理效应自证）；机制：5 个计划请求拦截（utr3/junction 无证据路径→不发声明）+ 1 条 ClaimGate 压制 + 3 条降级（中性）；幸存 FP = 最弱认证家族（ρ=0.835）上的对称 MRL 排名翻转，四时代不变。fig4d 重渲染 + 组合图重装配；论文摘要/贡献3/§2.4/图例(d)、FACT_SHEET、MANUSCRIPT 全部重基；旧时代归档 `_navgrid/`、`_static/`。
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

- **Registered next steps**: under the **2026-09-02 fourth programme reset**, every paper experiment is re-run with newly written code **one at a time in the user's sequence — replace only the current experiment's artifacts, never touch not-yet-re-run experiments' files** (progress: Figs 2, 3, 4 (a–h each) and Fig 5 (a–h) done; **Fig 6 removed from the paper 2026-09-06 per user direction (§2.6 → wet-lab section material)**; the paper presents the latest re-run results only — retained-evidence old-vs-new comparisons stay out of the PAPER_DRAFT text and legends). **2026-09-06 platform default change (DECISIONS (aa))**: GenNav-λ is now the default on `mrna_cds_design` (tristate `navigation`) and flows through `full_length_mrna_design` by delegation — the affected experiments (Exp 2+3, 24, 18, 25) re-run in that order, then Exp 37 (Table 1, §2.7). New drivers follow the established pattern (`experiments/expN_*.py`, pre-registered docstring, pilot-first, zero-intervention production tool path, advisory CapGate, unified palette rev 7 figures); E19/E20 stay reserved for the CRISOT/CRGPT data gap.
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
