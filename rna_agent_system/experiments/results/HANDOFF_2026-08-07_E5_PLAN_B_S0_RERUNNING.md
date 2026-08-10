# 交接提示词(2026-08-07 深夜:方案 B 已实施 + S0 重跑 #2 进行中,新会话接续)

> **用法**:新会话先读本文件。背景链:`HANDOFF_2026-08-07_E5_PINNED_READY_S0.md`(拍板)→ `HANDOFF_2026-08-07_E5_MECHANISM_FIXED_S0_RERUNNING.md`(5 项机制修复)→ `HANDOFF_2026-08-07_E5_PLAN_B_PENDING.md`(方案 B 拍板待参数确认)→ **本文件(方案 B 已实施,S0 重跑 #2 运行中)**。
> 项目根:`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`,主工程 `rna_agent_system/`(所有命令用绝对路径或同条命令内 `cd`,Bash cwd 每次调用可能重置)。

## 0. 一句话现状

**S0 重跑 #2(方案 B 池 + 排序机制化)正在运行**(setsid nohup 启动,PID 见 §4),池构建已过(225 候选/45 过约束,219s),C 臂 ×3 重复进行中;新会话第一步 = 监控 verdict → 判定 → 门控。首次重跑(#1)因实现 bug 崩溃已修复(§3.2)。所有修改未 commit。

## 1. 方案 B 参数确认(本会话,用户在线,三项全按推荐值拍板)

| 参数 | 拍板 | 依据 |
|---|---|---|
| GEMORNA 采样数 N | **20**/靶 | Insulin 实测 5/10 过约束(50%),~4s/条;池 225 候选 |
| λ 标记 | **GEMORNA=-1、RNARL=-2 独立来源档** | D2 判据按来源档计(6 档),判据代码零改动 |
| 排序机制化并行 | **是** | S0 二次 NO-GO 根因 = LLM 不按 U(τ=0.0)+ 端点轮间非确定;B 不解决 R2 |

## 2. 方案 B 实施清单(全部在 `experiments/run_e5_constraint_nav.py`,pytest 全量通过)

1. **build_pool**:CDS = LD 4 λ + RNARL 1(homo_mrna,workflow design_tool="rnarl")+ GEMORNA 20 采样(HTTP POST 8004 `/generate/cds`,按 (target,idx) 落盘缓存 `experiments/results/e5_gemorna_cds_cache.json`,池可复现;重跑复用缓存,采样零重复调用)
2. **λ 标记**:`LAMBDA_GEMORNA=-1`、`LAMBDA_RNARL=-2`;`LAMBDA_RANK` 扩至 6 档 {0:0,1:1,4:2,10:3,-1:4,-2:5};D2 判据代码零改动
3. **候选 id**:`ld{λ}_u5{u}_u3{u}` / `rn_u5{u}_u3{u}` / `gm{idx}_u5{u}_u3{u}`;候选新增 `source` 字段
4. **候选表瘦身** `_candidate_table`:只列过约束(pass)行(225→45),表头注来源档语义;`_pool_overview` 描述文本已更新(按来源计数)
5. **排序机制化** `mechanize_delivery_order`:finalize 时按 U 降序稳定重排(B/C 臂 finalize 分支 + C 臂循环外兜底 + B 臂 finish() 兜底);LLM 只做 U tie 仲裁;`ACTION_SYSTEM` 已同步语义

## 3. 关键过程记录

### 3.1 第一次重跑(方案 B)结果与崩溃
- 池构建 ✅:225 候选,**45 过约束(20%)**,219s(LD 4×15s + RNARL 17.5s + GEMORNA 20×4s + 225 候选 fold)
- 崩溃 ❌:C 臂 repeat 1 时 `audit_event("mechanized_reorder", ...)` 抛 pydantic ValidationError——`AuditEvent.event_type` 是 Literal,不接受自定义事件类型 → 进程退出
- **修复(本会话)**:finalize 分支机制化记录改 `history.append({"event": "mechanized_reorder", "profiles": {...}})`,不进 audit_trail;audit 零改动
- pytest 全量修复后重跑:649 passed, 1 skipped ✅

### 3.2 S0 重跑 #2(当前)
- 复用 GEMORNA CDS 缓存(20 条已落盘)→ 池构建预计 ~2.5–4min
- 判据不变(PREREG §9):①约束识别 100% ②输出格式完整 ③R2 τ≥0.8 ④无崩溃 ⑤≤2400s
- 机制化预期:交付排序 = U 降序(确定性),R2 应稳定 ≈1.0,除非 U tie 处 LLM 仲裁轮间漂移

## 4. 进程/服务状态(勿杀)

| 项 | 状态 |
|---|---|
| S0 重跑 #2 | `python experiments/run_e5_constraint_nav.py s0 --targets Insulin --repeat 3`(setsid nohup,日志 `experiments/results/e5_s0.log`) |
| 8004 GEMORNA / 8008 RNARL / 8014 LinearDesign / 8015 LinearFold | 均运行中(实验拉起的,勿杀) |

## 5. 下会话第一步(严格按序)

1. `pgrep -af run_e5_constraint_nav` 确认 S0 是否还在跑;`tail experiments/results/e5_s0.log` 看进度;`stat experiments/results/e5_verdict_s0.json` 看 mtime(基线 1786129594 = 19:06:34 旧判定,更新即本轮完成)
2. 若还在跑:`until [ mtime > 1786129594 ] || ! pgrep ...; do sleep 30; done` 等完成(预计从启动起 20–35min)
3. 判定书对照 §9 五项,读 `e5_verdict_s0.json` + `e5_audit/s0_Insulin.jsonl`:
   - R2 看 `R2_tau_min` / `R2_by_profile`(stability/balanced 应为真实值;机制化后应 ≈1.0)
   - ④ 无崩溃(本会话已修 audit bug,重跑 #2 应不再崩)
4. **GO**(全过)→ 直接进 S1:5 靶(A1AT,Insulin,EPO,GFP,IL-2)× 3 臂,判据 §9:通过率 C≥0.8 且 C≥A+0.4 / 约束满足率 C≥0.9 / R1–R4 全过 / D1–D3 全过 / 方向性 C≥A 4/5;预计 ~1.5–2h → 全过 → S2(18 靶,2 分片串行,~2.5–3.5h 重估后,McNemar p<0.05;HER2 预期 0 分如实报告)
5. **NO-GO** → 分析呈证据;若 R2 仍不过,结论收敛为"DeepSeek temp-0.0 端点真实可重复性上限",R2 阈值是否维持属预注册阈值决策,必须呈用户,不单方面降
6. 每阶段完成当天更新 MODEL_API_USAGE 实测行(S0 重跑 #2 的 LLM/生成器计数待填;方案 B 生成预算已预登记:LD 4 + RNARL 1 + GEMORNA 26/靶)

## 6. 未 commit(全部未 commit;git 操作必须先问用户)

- `experiments/run_e5_constraint_nav.py`(方案 B 实施 + audit bug 修复)
- `experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`(§3.1/§14 已更新方案 B)
- `experiments/results/MODEL_API_USAGE.md`(E5 行已加方案 B 生成预算)
- 四个交接文档(HANDOFF_*)
- 工作区另有大量历史未 commit(与本次无关,勿动)

## 7. 工程纪律(不变)

1. git 操作必须先问用户。2. 改代码必跑 pytest 全量(649 passed, 1 skipped)。3. 预注册项改动(判据/约束/阈值)先呈用户;机制层改动可自主实施。4. 论文数据当天更新 MODEL_API_USAGE.md。5. 后台驱动:setsid nohup + 日志落盘 + pgrep 确认 + until 等完成。6. 微服务 8004/8008/8014/8015 勿杀。7. S0/S1/S2 每阶段出判定书,未过不进下一阶段。8. 用户授权"根据实验结果直接决定"沿用(限预注册流程内门控;阈值/判据变更仍呈用户)。

## 8. 关键数据/代码指针

- 判定书:PREREG §9;verdict:`e5_verdict_s0.json`;runs:`e5_s0_runs.jsonl`(append-only);audit:`e5_audit/s0_Insulin.jsonl`
- 驱动:`run_e5_constraint_nav.py`(build_pool@~660、mechanize_delivery_order@~1300、run_arm_c finalize@~1640、_candidate_table@~1135、_pool_overview@~1105、ACTION_SYSTEM@~1195)
- GEMORNA 采样缓存:`experiments/results/e5_gemorna_cds_cache.json`(20 条 Insulin 已落盘)
- 实测脚本:`/tmp/e5_gemorna_cds_probe.py`(可改 N 重跑)
- 离线重放(最终案):17/18 可行靶;Insulin 12/36、HER2 0/36、Spike 9/36(36 候选口径;方案 B 225 候选口径重放未做,如需可离线跑)
