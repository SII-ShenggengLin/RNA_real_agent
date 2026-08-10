# 交接提示词(2026-08-07 深夜→凌晨:S0 重跑 #2 完成 = GO,S1 已启动运行中,新会话接续)

> **用法**:新会话先读本文件。背景链:`HANDOFF_2026-08-07_E5_PLAN_B_PENDING.md`(方案 B 拍板待参数确认)
→ `HANDOFF_2026-08-07_E5_PLAN_B_S0_RERUNNING.md`(方案 B 已实施,S0 重跑 #2 运行中)→ **本文件(S0 重跑 #2 完成 = GO,S1 运行中)**。
> 项目根:`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`,主工程 `rna_agent_system/`(所有命令用绝对路径或同条命令内 `cd`,Bash cwd 每次调用可能重置)。

## 0. 一句话现状

**S0 重跑 #2(方案 B 池 + 排序机制化)已完成,判定书 = GO(五项全过,R2 τ≈1.0);S1(5 靶 × 3 臂)已 setsid nohup 启动,运行中**。新会话第一步 = 监控 S1 verdict → 判定 → 门控 S2。

## 1. S0 判定书(2026-08-07 20:45:03,`e5_verdict_s0.json`,go_no_go = GO)

| 判据(PREREG §9) | 结果 | 证据 |
|---|---|---|
| ① 约束识别 100% | ✅ | `criteria.constraint_identification_100pct = true` |
| ② 输出格式完整(5 候选+排序+档案) | ✅ | `criteria.output_format_complete = true` |
| ③ R2 稳定性 τ≥0.8 | ✅ | `R2_tau_min = 1.0`,三档 profile(expression/stability/balanced)均 ≈1.0 → **排序机制化生效**(交付序 = U 降序确定性,LLM 仅 U tie 仲裁) |
| ④ 无崩溃 | ✅ | audit bug 修复(mechanized_reorder 记录改 history,不进 audit_trail)重跑 #2 全程无 traceback |
| ⑤ elapsed ≤2400s | ✅ | `elapsed_seconds = 344.3s`(池 140.5s + C 臂 ×3) |

关键实测:池 225 候选 / 45 过约束(20%),GEMORNA CDS 缓存复用(unique=19,零新增采样);LLM 仅 **3 次**(机制化压降,预登记 15–27);LD 6 次(池 4 λ + C 臂修复轮 2 次 λ=2.0,audit `lineardesign_extra`×2);RNARL 1;LinearFold 池级 fold 本地零 API。MODEL_API_USAGE.md E5 行已更新(S0 最终案 + 弃用运行另耗)。

## 2. S1 启动信息(本次会话启动)

- 命令:`python experiments/run_e5_constraint_nav.py s1`(默认 5 靶 A1AT,Insulin,EPO,GFP,IL-2 × 默认 A/B/C 三臂,repeat=1)
- setsid nohup,日志 `experiments/results/e5_s1.log`;输出 `e5_s1_runs.jsonl`;判定书 `e5_verdict_s1.json`
- 预计 ~1.5–2h(PREREG §14);每靶池独立构建(Insulin GEMORNA CDS 复用缓存)

## 3. S1 判据(PREREG §9,驱动 write_verdict 自动判定)

①端到端通过率 C ≥ 0.8 **且** C ≥ A + 0.4 ②约束满足率 C ≥ 0.9 ③R1–R4 全过(一致性/稳定性/敏感性/最优性)④D1–D3 全过 ⑤每靶点方向性 C ≥ A 至少 4/5 ⑥BMC 预算记录(描述性)。
**全过 → S2(18 靶,2 分片串行,~2.5–3.5h;McNemar p<0.05;HER2 预期 0 分如实报告);任一不过 → 报告用户**。

## 4. 进程/服务状态(勿杀)

| 项 | 状态 |
|---|---|
| S1 | `python experiments/run_e5_constraint_nav.py s1`(setsid nohup,日志 `experiments/results/e5_s1.log`;PID 见 §6) |
| 8004 GEMORNA / 8008 RNARL / 8014 LinearDesign / 8015 LinearFold | 均运行中(实验拉起的,勿杀) |

## 5. 下会话第一步(严格按序)

1. `pgrep -af run_e5_constraint_nav` 确认 S1 是否在跑;`tail experiments/results/e5_s1.log` 看进度;`stat experiments/results/e5_verdict_s1.json` 看 mtime(S1 启动时间 = 基线,更新即完成)
2. 若还在跑:`until [ mtime > 基线 ] || ! pgrep ...s1...; do sleep 30; done` 等完成
3. 判定书对照 §9 六项,读 `e5_verdict_s1.json` + `e5_audit/s1_*.jsonl`
4. **GO**(全过)→ 直接进 S2(18 靶,`--targets` 全 18,默认 3 臂,~2.5–3.5h;判据 §9:McNemar p<0.05 / R1–R4、D1–D3 全过 / 约束满足率 C≥0.9;HER2 预期 0 分如实报告)
5. **NO-GO** → 分析呈证据;阈值/判据变更必须呈用户,不单方面降
6. S1 完成当天更新 MODEL_API_USAGE.md 实测行(S1 LLM/生成器计数待填;预登记:LLM ~35–65,生成器 LD 20 + RNARL 5 + GEMORNA 130/5 靶)

## 6. 未 commit(全部未 commit;git 操作必须先问用户)

- `experiments/run_e5_constraint_nav.py`(方案 B 实施 + audit bug 修复)
- `experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`(§3.1/§14 已更新方案 B)
- `experiments/results/MODEL_API_USAGE.md`(E5 行 S0 实测已更新)
- 五个交接文档(HANDOFF_*)
- 工作区另有大量历史未 commit(与本次无关,勿动)

## 7. 工程纪律(不变)

1. git 操作必须先问用户。2. 改代码必跑 pytest 全量(649 passed, 1 skipped)。3. 预注册项改动(判据/约束/阈值)先呈用户;机制层改动可自主实施。4. 论文数据当天更新 MODEL_API_USAGE.md。5. 后台驱动:setsid nohup + 日志落盘 + pgrep 确认 + until 等完成。6. 微服务 8004/8008/8014/8015 勿杀。7. S0/S1/S2 每阶段出判定书,未过不进下一阶段。8. 用户授权"根据实验结果直接决定"沿用(限预注册流程内门控;阈值/判据变更仍呈用户)。

## 8. 关键数据/代码指针

- 判定书:PREREG §9;S1 verdict:`e5_verdict_s1.json`;runs:`e5_s1_runs.jsonl`(append-only);audit:`e5_audit/s1_*.jsonl`
- 驱动:`run_e5_constraint_nav.py`(build_pool@~660、mechanize_delivery_order@~1300、run_arm_c finalize@~1640、_candidate_table@~1135、_pool_overview@~1105、ACTION_SYSTEM@~1195)
- GEMORNA 采样缓存:`experiments/results/e5_gemorna_cds_cache.json`(Insulin 20 条已落盘;S1 其余 4 靶首次采样)
- 实测脚本:`/tmp/e5_gemorna_cds_probe.py`
- 离线重放(最终案):17/18 可行靶;Insulin 12/36、HER2 0/36、Spike 9/36(36 候选口径;方案 B 225 候选口径重放未做)
