# 交接提示词(2026-08-07 晚:机制修复完成 + S0 重跑进行中,新会话接监控)

> **用法**:新会话先读本文件。背景链:`HANDOFF_2026-08-07_E5_PINNED_READY_S0.md`(用户拍板、驱动已改、S0 待重跑)→ 上会话做了 S0 重跑(NO-GO)→ 用户授权"根据实验结果直接决定"→ 本会话实施 5 项机制修复 + 重跑 S0 → **本文件(修复后 S0 正在跑,新会话接监控与判定)**。
> 项目根:`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`,主工程 `rna_agent_system/`(所有命令用绝对路径或同条命令内 `cd`,Bash cwd 每次调用可能重置)。

## 0. 一句话现状

**S0 重跑(修复后驱动)正在后台运行:PID 3009821,19:00:45 启动,~10min 完成(参考首轮 639s)。旧 verdict(18:04)为 NO-GO(R2 τ_min=0.0),新 verdict 会覆盖写入 `e5_verdict_s0.json`。本会话的 until 循环已随会话关闭消失,需新会话重新挂。所有修改未 commit。**

## 1. 上会话已完成(勿重做,均在磁盘)

### 1.1 S0 首轮判定(NO-GO,证据齐全)
- 判据逐项:①约束识别 100% ✅ ②输出格式完整(5 候选+排序+档案)✅ ③**R2 τ≥0.8 ❌(τ_min=0.0)** ④无崩溃 ✅ ⑤639s/2400s ✅。
- R2 明细:expression 0.0 / stability 1.0(假象)/ balanced 0.6;llm_calls=8(2+3+3)。
- 池:构建态 36 候选/12 过(与离线重放预测 12/36 完全一致 ✓);C 臂修复轮 extra_ld(λ=2.0)追加 9 候选 → 记录态 45/21。
- 3 次重复交付:rep1/rep2 的 expression 为 λ=2.0(x2_*),rep3 换成 λ=10.0(ld10_*)——画像 λ 定位漂移;stability 的 τ=1.0 是度量 bug 假象(rep3 交付集合与 rep1/2 零交集)。

### 1.2 根因与修复(用户已授权"根据实验结果直接决定",已实施,未 commit)
| # | 缺陷 | 修复(均在 `experiments/run_e5_constraint_nav.py`) |
|---|---|---|
| 1 | kendall 度量 bug:`shared==ids2[:0]` 对空表恒真 → 完全不相交排序被计 τ=1.0 | `kendall_tau_rankings`:共享 <2 项 → 返回 0.0(已验证 identical→1.0, disjoint→0.0) |
| 2 | 池跨重复变异:extra_ld 追加写共享池,rep2/3 非"同输入" | `run_one_cell`:每重复从 `_pool_snapshot()`(深拷贝除 registry)出发;merge-back 按 id 去重并入主池;交付副本同步 U(`scores`/`utility` 用主池 norms 重算) |
| 3 | 机制缺口 R1:候选表无 U 值,LLM 无排序依据 | `_candidate_table` 加 `U(expression)/U(stability)/U(balanced)` 列 |
| 4 | 机制缺口 D2 + 陈旧文本:overview 仍写"9 constraints"、矛盾指令"必须交付失败候选" | `_pool_overview`:动态 λ 计数、`len(CONSTRAINT_IDS)` 条约束、交付规则(仅过约束候选/λ 跨 ≥3 档/按 U 排序) |
| 5 | ACTION_SYSTEM 无交付指导 | sort/finalize 说明:ranking 必须按 U 列顺序(tie 由 arbitration 层断),5 候选须跨 ≥3 个 λ 档(pool 允许时) |

- **判据零改动**(R2≥0.8、R1–R4、D1–D3、5 条约束矩阵全部维持),只修机制使其可达。
- **pytest 全量:649 passed, 1 skipped ✓**(与基线一致,21s)。
- MODEL_API_USAGE.md E5 行已加 S0 实测(LLM 8 次 + LinearDesign 5 次 + GEMORNA 6 次)。

## 2. 正在运行/可监控的后台任务

- **S0 重跑(修复后)**:PID 3009821,19:00:45 启动(setsid nohup,会话关闭后存活),日志追加 `experiments/results/e5_s0.log`(第 57 行 marker `=== rerun after mechanism fixes Fri Aug  7 19:00:45 ===`)。截至 19:03:池 36/12(62s)建成,repeat 1/3 完成,repeat 2/3 进行中,audit 文件 `e5_audit/s0_Insulin.jsonl` 正常增长。
- 微服务 8004(GEMORNA)/8014(LinearDesign)/8015(LinearFold)仍在跑(实验拉起的,勿杀)。
- 本会话的 until 循环(boozvhi61/bqjxudcss)随会话关闭消失——**新会话必须自己挂等待**。

## 3. 新会话下一步(严格按序)

1. **挂 until 循环等新 verdict**(旧 verdict mtime=18:04,新 verdict 覆盖写入且 mtime 更新;进程死亡则报错):
   ```
   until [ -f <根>/rna_agent_system/experiments/results/e5_verdict_s0.json ] \
      && [ "$(stat -c %Y <...>/e5_verdict_s0.json)" -gt "$(date -d '2026-08-07 18:10:00' +%s)" ]; do
     pgrep -f "python experiments/run_e5_constraint_nav.py s0" >/dev/null || { tail -30 e5_s0.log; exit 1; }
     sleep 30; done; echo VERDICT_READY; tail -8 e5_s0.log
   ```
   (Bash run_in_background;也可 `stat -c %Y` 对比 19:00:45 启动前的时间戳,或直接看日志出 `[s0] verdict ->` 行)
2. **呈 S0 判定书**(对照 PREREG §9:①约束识别 100% ②输出格式完整 ③R2 τ≥0.8 ④无崩溃 ⑤≤2400s)。重点看:`R2_tau_min`、`R2_by_profile`(stability 这次应是真实值,不再有不相交假象)、`elapsed_seconds`(若 >2400s 则 ⑤ 不过)。
3. **判定门**:GO → 按 §9 直接进 S1(用户已在本会话授权"根据实验结果直接决定",下会话沿用此授权:每阶段出判定书、按预注册门控走,重大未预注册决策仍呈用户);NO-GO → 分析并呈证据,若失败收敛为"DeepSeek temp-0.0 端点真实可重复性上限",R2 阈值是否维持属于预注册阈值决策,**必须呈用户,不单方面降**。
4. **S1**:`python experiments/run_e5_constraint_nav.py s1 --targets A1AT,Insulin,EPO,GFP,IL-2 --arms A,B,C`(setsid nohup + 日志 + pgrep + until;~1.5–2h)。判据(§9):通过率 C≥0.8 且 C≥A+0.4 / 约束满足率 C≥0.9 / R1–R4 全过 / D1–D3 全过 / 方向性 C≥A 至少 4/5。全过 → S2;任一不过 → 报告用户。
5. **S2**:18 靶(FULL_TARGETS 已过滤 Factor_VIII/Zika),**2 分片串行**(服务串行处理请求,勿超 2 分片并发;~4–5h)。判据:配对 McNemar p<0.05(C vs A 且 C vs B)/ R1–R4、D1–D3 全过 / 约束满足率 C≥0.9;HER2 预期 0 分如实报告。
6. 每阶段完成当天更新 `MODEL_API_USAGE.md` 实测行(S0 行已更新;S1/S2 待)。当前未 commit 文件:`experiments/run_e5_constraint_nav.py`、`PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`、`MODEL_API_USAGE.md`、本次交接文档。

## 4. 关键状态与指针

- **S0 判据原文**:PREREG §9(`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`),S0 不含池通过率;§15 = 拍板注记汇总。
- **数据文件**:`e5_verdict_s0.json`(18:04 旧 NO-GO,将被覆盖)、`e5_s0_runs.jsonl`(append-only,已有首轮记录)、`e5_audit/s0_Insulin.jsonl`、`e5_s0.log`。
- **离线重放**(最终案,勿重做):17/18 可行靶;Insulin 12/36、HER2 0/36、Spike 9/36。脚本 `/tmp/e5_replay_v2.py`(/tmp 可能被清理,数据源 `e5_pool_survey.json` 在磁盘)。
- **工具函数验证点**:修复后 kendall(identical→1.0/disjoint→0.0)、`_pool_snapshot`(深拷贝除 registry)、交付副本 U 同步(在 `delivery_eval_junctions`+`assign_utilities` 之后执行)。

## 5. 工程纪律(用户既定规则,不变)

1. git 操作必须先问用户(当前 4 个文件未 commit)。
2. pytest 基线 649 passed, 1 skipped;改代码后必跑全量(约 25s)。
3. 简洁优先;锁定接口走 `docs/INTERFACE_LOCKS.md`(只增不改)。
4. 预注册项改动必须先呈用户(判据/约束/阈值;本次修复为机制层,判据零改动)。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动:setsid nohup + 日志落盘 + 启动后 pgrep 数进程 + until 等完成;命令用绝对路径或同条内 cd。
7. 决策文化:重大路线由用户决定;上会话用户已授权"根据实验结果直接决定"——沿用该授权处理已预注册流程内的门控判断,阈值/判据/约束变更仍呈用户。
8. 微服务 8004/8014/8015 为实验拉起的勿杀。
9. S0/S1/S2 每阶段结束出判定书(JSON),未过不进下一阶段;阶段判据禁止中途新增终点。
