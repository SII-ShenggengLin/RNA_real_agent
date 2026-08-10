# HANDOFF 2026-08-09 — E6 S0 GO 完成;S1 运行中(2/5 靶),后续会话继续监控与判定

**上一会话:** HANDOFF_2026-08-09_E6_PROBED_PENDING.md(探针 P1–P5 完成,3 点已拍板)
**本会话:** 落驱动代码(gennav_core / run_e6_gennav / test_gennav_core)→ S0 GO → 文档同步(PREREG §20 + MODEL_API_USAGE §2)→ S1 启动,用户因上下文长度关闭会话,转下一会话
**下一会话目标:** 监控 S1 跑完(剩 EPO/GFP/IL-2)→ 判据 v8 判定 → S1 全过才 S2(18 靶双终点)→ MODEL_API_USAGE 实测更新 → 复现锚点 + 收尾 HANDOFF

---

## 0. 当前状态(2026-08-09,S1 运行中)

- **S1 在跑**:`python experiments/run_e6_gennav.py s1 --resume`(pid=150290,日志 `/tmp/e6_s1_run.log`);已含 `--resume`,断点续跑安全。
- **进度 2/5**:A1AT、Insulin 已完成(success=True,arm_results 含 A/B/C_runs);当前 EPO 格构建中;剩余 **EPO/GFP/IL-2**。
- **中间判定书** `experiments/results/e6_verdict_s1.json` = 逐靶覆盖风格(E5 先例:最终以 `e6_s1_runs.jsonl` 末 5 条为准),当前显示 NO-GO 是中间值,**不是最终结论**。
- 5 靶可行档(全缓存命中,ld_calls=0):A1AT{2,4,8,10,20,50} tier=6 / Insulin{2,4,8,10,20} tier=5 / EPO{1,2,4,8,10,20,50} tier=7。
- 微服务健康(gemorna 8004 / lineardesign 8014 / linearfold 8015 已探活);勿杀任何服务;jupyter + GPU_get.py 在跑。

## 1. 本会话完成(拍板后按序实施)

1. **`agent_core/generation/gennav_core.py`**(组件 1–4 纯函数,按拍板口径):dynamic_rank_map / independent_rank / dynamic_pref_ranks / gear_selection_plan(≥3 full,2 bisect,≤1 degrade)/ utility_dyn / assign_utilities_dyn / 三方向轴(axis_cai_max / axis_frac_tuned 接受重试 [0.88,0.92] / axis_apply_frac 源 CDS 上应用 / axis_cai_floor target 0.85)/ synonymous_diversify / min_pairwise / diversity_accept / delivery_cai_span / **d2_composite(拍板①)** / lattice_gear_declaration(E14)/ CodonContextResolver(构造 KeyError 显式失败;codon_usage_csv human→None,非 human→`<canonical>_<sha12>.csv`)。
2. **`experiments/run_e6_gennav.py`**(~1990 行):三臂分层池 + gate_action 第 5 道闸 request_generate(B ≤1 共享档、C ≤2 且 LD 总 ≤3/基因);seed_e6_caches;probe_feasibility;regenerate_cells;ACTION_SYSTEM_B;判据书 v8 六项 + S2 双终点;CLI s0/s1/s2 + --resume/--dry-run。
3. **`tests/test_gennav_core.py`**:47 项全绿;**pytest 全量 696 passed, 1 skipped, 30 deselected**(基线 649 保持)。
4. **文档同步(本地产物不入库)**:PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md 追加 **§20 E6 决议注记**(C1–C6 + 拍板①②③ + 判据书 v8 + S2 双终点 + 落地 + 关键口径);MODEL_API_USAGE.md §2 新增 **E6 预登记行**(LLM A0/B2–4/C5–9;LD 探测 5/靶+细化 0–2+C 臂 ≤3 ≈ 90–160;GEMORNA 8 行/靶零新调用;RNARL 零调用)。
5. **E6 S0(Insulin × C 臂 × 3 重复)→ GO**:六项判据全过(output_format_complete / R2_stability_tau=1.0 / axis_locked_r3(3/3 分离对)/ no_crash / elapsed 568s<2400s / lattice_determinism_recorded);LLM 6 次(预算 15–27);格 288 细胞 204 pass,13 源(含 8 GEMORNA);产物 `e6_s0_runs.jsonl` + `e6_verdict_s0.json`(GO)。

### 本会话修 3 处启动/运行 bug(均在 run_e6_gennav.py,已修复)

1. `import hashlib` 缺失(seed 路径) → 补 import。
2. `_gfp_lambda4_from_runs` 用 `_load_json`(json.loads 整文件)读 JSONL `e5_s1_runs.jsonl` → "Extra data" → 改逐行 `json.loads`。
3. `_observation` 无条件 `_lattice_overview`(需 pool['ld_gears']),静态池 arm B 崩溃 KeyError → 新增 `_static_overview(pool)`,`pool_kind=="static"` 分派。

### 测试暴露真 bug(gennav_core.py,已修复并回归)

- `synonymous_diversify` 双重索引:positions 存**核苷酸索引**(range(0, len-2, 3)),突变循环又 `i*3` → slice 越过列表末尾自动扩列(330→348);`min_pairwise` 不等长保守返回 1.0 曾掩盖假绿 → 修复为 `seq_list[i:i+3]`。

## 2. 下一步(下一会话,按序)

1. **监控 S1 至完成**(还剩 EPO/GFP/IL-2;单靶约 5–8 min 池构建 + 臂运行,总预算 3h)。日志 `/tmp/e6_s1_run.log`;断点续跑 `python experiments/run_e6_gennav.py s1 --resume`(勿重复启动)。
2. **S1 判定(判据书 v8 六项)**:① e2e C≥0.8 且 C≥A 平局算过 ② 约束率 C≥0.9 ③ R1–R4(R3 注记 E13_gen_axis)④ D1–D3(D2 复合判据;E14_gen_lattice ge_3)⑤ 方向性 C≥A 4/5 ⑥ 预算记录。逐靶判定以 `e6_s1_runs.jsonl` 末 5 条为准;判定书 `e6_verdict_s1.json` 逐靶覆盖。
3. **S1 全过 → S2**:`python experiments/run_e6_gennav.py s2`(18 靶 × 2 臂 A/C,双终点:主 = per-profile JCD-pass 配对 McNemar(n=54)+ c_e2e_gene ≥0.8;辅 = 连续复合得分配对 Wilcoxon + 质量判据;6h 预算)。S1 未全过 → 按判据书处置(逐靶 NO-GO 归因 + 汇报用户,勿自行改判据)。
4. **MODEL_API_USAGE §2 E6 行实测更新**(S0/S1/S2 完成后当天;LLM 次数实测 vs 预算)。
5. **复现锚点 + 收尾 HANDOFF**:e6_ld_cds_cache.json(23 键,键含 csv_hash 26308b892d84)+ e6_gemorna_cds_cache.json(150 键)+ 格 lattice_plan 快照;UTR 复用 e5_gemorna_cache.json。

## 3. 纪律重申

- git 操作先问用户;判据/阈值/处置变更必须拍板 + 同步 PREREG §20 与 MODEL_API_USAGE §2。
- 一律绝对路径(仓库根 `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`)。
- 勿杀微服务(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 重启须带 PYTHONPATH=<rna_agent_system>)。
- 勿动旧链路:run_e5_constraint_nav.py / codon_tables/CSV / sequence_utils.py / mrna_cds_design.py / lineardesign_service 零改动。
- e5_s1_round3_archive/ 与 e5_s1_r2_rnarl_down_archive/ 勿删;e5_s1_r4.log / e5_s1.log / e5_s1_r5.log 勿覆盖;IL-2 探针勿重跑。
- E5 已证伪路径勿重复:A 分支(λ 网格扩展修 R3)、C 分支(GEMORNA 30→60)、B1 补救、λ 加档修 D1。
- 探针产物只读(/tmp/e5_probe_carm/e6_* 是 E6 运行缓存种子);勿重跑 IL-2 探针。
- 每个阶段写 HANDOFF_*.md。

## 4. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/run_e6_gennav.py | **E6 驱动(未跟踪)**;s0/s1/s2 子命令 + --resume/--dry-run;判据书 v8 内嵌 |
| agent_core/generation/gennav_core.py | **E6 组件 1–4 纯函数(未跟踪)** |
| tests/test_gennav_core.py | 47 项测试(未跟踪);基线 696 passed 保持 |
| experiments/results/e6_verdict_s0.json / e6_s0_runs.jsonl | S0 判定书(GO)+ 运行记录 |
| experiments/results/e6_verdict_s1.json / e6_s1_runs.jsonl | S1 中间判定书(逐靶覆盖)+ 运行记录(已完成 2/5) |
| /tmp/e6_s1_run.log | S1 运行日志(监控入口) |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | §20 = E6 决议注记(拍板①②③ + 判据书 v8) |
| experiments/results/MODEL_API_USAGE.md | §2 E6 行(预登记;实测待更新) |
| /tmp/e5_probe_carm/e6_ld_probe_cache.json | 探针 LD 缓存 20 键(种子) |
| /root/.claude/plans/gleaming-honking-ladybug.md | E6 已批准计划(执行依据) |
