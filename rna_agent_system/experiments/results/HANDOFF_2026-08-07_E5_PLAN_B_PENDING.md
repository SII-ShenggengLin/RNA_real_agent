# 交接提示词(2026-08-07 深夜:S0 二次 NO-GO 已判定 + 方案 B 方向拍板待实施,新会话接续)

> **用法**:新会话先读本文件。背景链:`HANDOFF_2026-08-07_E5_PINNED_READY_S0.md`(拍板)→ `HANDOFF_2026-08-07_E5_MECHANISM_FIXED_S0_RERUNNING.md`(5 项机制修复 + 修复后 S0 重跑)→ 上会话完成判定与实测,用户拍板走方案 B(CDS 生成策略变更)方向 → **本文件(方案 B 参数待确认、实施待开始)**。
> 项目根:`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`,主工程 `rna_agent_system/`(所有命令用绝对路径或同条命令内 `cd`,Bash cwd 每次调用可能重置)。

## 0. 一句话现状

**无在跑实验**(S0 修复后重跑已于 19:06:34 结束,NO-GO)。用户已拍板走**方案 B**(CDS 生成 = LinearDesign 4 条 + RNARL 1 条 + GEMORNA 大量采样),但**参数未确认**(N 采样数、λ 标记方案、是否与"排序机制化"并行),下会话第一步呈参数决策。所有修改未 commit。

## 1. 关键结论:S0 修复后重跑判定书(19:06:34,NO-GO)

| 判据(PREREG §9) | 结果 | 证据 |
|---|---|---|
| ① 约束识别 100% | ✅ | 每候选 5 约束判定 + 10 项档案全量 |
| ② 输出格式完整 | ✅ | 3 轮 × 3 profile 均 5 候选 + 排序 + 档案 |
| ③ R2 τ≥0.8 | ❌ **τ_min = −1.0** | expression=−1.0;stability=1.0、balanced=1.0(**均为真实值**) |
| ④ 无崩溃 | ✅ | 正常落盘 |
| ⑤ ≤2400s | ✅ 346.7s | 池 62s + 3 重复;llm_calls=4 |

verdict 文件:`experiments/results/e5_verdict_s0.json`(19:06:34 覆盖旧 18:04 版本)。

## 2. 5 项机制修复验证(修复均在上上会话,`run_e5_constraint_nav.py`)

| # | 修复 | 验证 |
|---|---|---|
| 1 | kendall 度量 bug | ✅ 生效,stability=1.0 为真实一致(三轮共享 3 项顺序全同) |
| 2 | 池跨重复变异 | ✅ 生效,三轮候选 U 值逐位相同;run1=run2 交付完全一致 |
| 3 | 候选表 U 列 | ✅ 已入表 |
| 4 | 动态 λ 计数+交付规则 | ✅ 生效,run3 LLM 主动识别 D2 缺档并调 lineardesign λ=7(首轮"λ 漂移"已消除) |
| 5 | 排序指令 | ❌ **未达成**,交付排序不按 U(见根因) |

## 3. NO-GO 根因(修复后已收敛,证据齐全)

1. **直接原因**:expression τ=−1.0 = run3 交付与前两轮共享仅 2 项且顺序全反。
2. **LLM 未按 U 排序(独立缺陷)**:交付 vs U 降序 τ——expression **0.0/0.0/0.0**,stability 0.8/0.8/0.6,balanced 0.6/0.6/0.6。三轮×三 profile 无一轮按 U。
3. **端点非确定**:三轮输入一致(U 逐位相同、候选表相同),run1=run2 完全一致,run3 不同 → 同输入不同输出。"前两轮一致、第三轮漂移"已出现两次(18:04 轮 + 19:06 轮),指向 DeepSeek temp-0.0 端点真实可重复性上限。

## 4. 方案 B(用户已拍板方向,参数待确认)

**用户原话**:"CDS 生成时可以既用 lineardesign 生成 4 条,rnarl 生成 1 条,然后 gemorna 生成大量候选。这样可能效果会更好。"

### 三种生成器实测数据(Insulin,上会话完成)

| 生成器 | 数量 | 确定性 | 耗时/条 | CAI | 约束通过 | 备注 |
|---|---|---|---|---|---|---|
| LinearDesign | 4(λ 0/1/4/10) | ✅ | ~60s | 0.87–0.92 | 池 36 候选 12 过(33%) | 现池结构 |
| RNARL(homo_mrna) | 1 | ✅ argmax | 17.5s | **0.965** | 该条 C1 不过 | rare=0;确定性单条,过不过看运气 |
| GEMORNA | N(采样) | ❌ 随机 | ~4s | 0.86–0.94 | **5/10 过(50%)** | 10/10 唯一,失败全集中 C1(GC 滑窗) |

### 设计参数(上会话建议,待用户拍板)
1. **N=20** 采样/靶(~10 条过约束);池 = 25 CDS × 9 UTR = **225 候选/靶**(现 36),过约束 ~30
2. **λ 标记**:GEMORNA 采样统一 `lambda=-1`、RNARL `lambda=-2`(独立来源档);D2"跨 ≥3 档"按来源档计
3. **候选表瘦身**:表只列**过约束候选**(~30 行,现 45 行全列),否则 225 行淹没 LLM
4. **缓存**:GEMORNA CDS 非幂等 → 按 (target, idx) 落盘 `e5_gemorna_cds_cache.json`(沿 UTR 缓存模式,池可复现)
5. **成本重估**:池构建 62s → ~6.5 分钟/靶(225 候选 × 2 LinearFold);18 靶 ≈ 2h;GEMORNA 调用 20 次/靶 → MODEL_API_USAGE 更新
6. **⚠️ B 不解决 R2**:NO-GO 根因是 LLM 排序(不按 U + 端点非确定),池变大反而加剧集合漂移。**建议 B 与"排序机制化"并行**:finalize 时系统按 U 降序强制重排 LLM 的 5 候选(LLM 只做 tie-break 仲裁),判据零改动。此建议上会话已呈,用户未答复即关会话 → **下会话必须再次呈用户确认**(排序机制化属机制层改动,判据/阈值零改动,可自主实施;但用户已拍板走 B,是否同时走机制化需明确)。

## 5. 服务状态(勿杀,实验拉起的)

| 端口 | 服务 | PID | 备注 |
|---|---|---|---|
| 8004 | GEMORNA | 1491331 | 生成+预测(5'UTR MRL/3'UTR stability) |
| 8008 | **RNARL(新拉)** | 3898402 | 上会话启动;`microservices/rnarl_service/`,conda 环境 `rnarl_service_env`,启动需 `PYTHONPATH=<项目根> bash start.sh`(不带 PYTHONPATH 报 ModuleNotFoundError);checkpoints/ESM2 在 `external_repos/RNARL/` 全就位;2×4090,RNARL 用空闲卡 |
| 8014 | LinearDesign | 1492906 | 生成 |
| 8015 | LinearFold | 1495704 | fold |

## 6. 未 commit(全部未 commit;git 操作必须先问用户)

- `experiments/run_e5_constraint_nav.py`(5 项修复 + 待实施方案 B)
- `experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`(含 §14 预算,方案 B 需更新)
- `experiments/results/MODEL_API_USAGE.md`(S0 实测行已加;S1/S2 待)
- 三个交接文档(HANDOFF_*)
- 另有工作区大量历史未 commit(与本次无关,勿动)

## 7. 下会话下一步(严格按序)

1. **读本文件 + 呈方案 B 参数决策**(N=20?λ 标记?排序机制化并行?)——用户已拍板方向,参数属实施细节可带推荐值确认;若用户在线直接确认,若离线按推荐值实施(推荐值均基于实测)
2. **实施**:改 `build_pool`(LD4+RNARL1+GEMORNA_N、缓存、λ 标记)+ 候选表瘦身(只列 passed)+ 排序机制化(若用户认可)
3. **pytest 全量**(基线 649 passed, 1 skipped,~25s)必跑
4. **更新预注册**:PREREG §14(生成策略+预算表)、MODEL_API_USAGE(E5 生成行)
5. **重跑 S0**(`python experiments/run_e5_constraint_nav.py s0 --targets Insulin --repeat 3`,setsid nohup + 日志 + pgrep + until;判据不变:①100% ②格式 ③R2≥0.8 ④无崩溃 ⑤≤2400s)
6. **判定**:GO → S1(5 靶 A1AT/Insulin/EPO/GFP/IL-2 × A/B/C,~1.5–2h,判据 §9:通过率 C≥0.8 且 C≥A+0.4 / 约束满足率 C≥0.9 / R1–R4 全过 / D1–D3 全过 / 方向性 4/5)→ 全过 → S2(18 靶,2 分片串行,~4–5h,McNemar p<0.05;HER2 预期 0 分如实报告);NO-GO → 分析呈证据,R2 阈值变更必须呈用户
7. 每阶段完成当天更新 MODEL_API_USAGE 实测行

## 8. 工程纪律(不变)

1. git 操作必须先问用户。2. 改代码必跑 pytest 全量(649 passed, 1 skipped)。3. 预注册项改动(判据/约束/阈值)先呈用户;机制层改动可自主实施。4. 论文数据当天更新 MODEL_API_USAGE.md。5. 后台驱动:setsid nohup + 日志落盘 + pgrep 确认 + until 等完成。6. 微服务 8004/8008/8014/8015 勿杀。7. S0/S1/S2 每阶段出判定书,未过不进下一阶段。8. 用户授权"根据实验结果直接决定"沿用(限预注册流程内门控;阈值/判据变更仍呈用户)。

## 9. 关键数据/代码指针

- 判定书:PREREG §9(`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`);verdict:`e5_verdict_s0.json`;runs:`e5_s0_runs.jsonl`(append-only);audit:`e5_audit/s0_Insulin.jsonl`
- 驱动:`experiments/run_e5_constraint_nav.py`(build_pool@655、_candidate_table@1119、_pool_overview@~1085、ACTION_SYSTEM@~1177、kendall_tau_rankings@937、R2 汇总@1739)
- workflow 原生支持三引擎:`MrnaCdsDesignWorkflow.generate_candidates`(`design_tool="all"` = LD×4 + RNARL×1 + GEMORNA×1,`agent_core/workflows/mrna_cds_design.py:359`);E5 现只用 `design_tool="lineardesign"` 循环 4 次
- 实测脚本:`/tmp/e5_gemorna_cds_probe.py`(GEMORNA 采样通过率,可改 N 重跑)
- 离线重放(最终案):17/18 可行靶;Insulin 12/36、HER2 0/36、Spike 9/36
