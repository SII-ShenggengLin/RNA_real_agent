# 交接提示词（2026-08-08：E5 定稿 v4 判据修正落地，S1 重跑运行中，新会话接续）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E5_PLAN_B_S0_GO_S1_RUNNING.md`（S0 GO、S1 首轮）→ **本文件（v4 判据修正 + S1 重跑）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（**Bash 工具工作目录跨调用持久——后台任务须同条命令内 `cd rna_agent_system &&`；git 命令建议 `-C <项目根>`**）。

## 0. 一句话现状

**E5 预注册定稿 v4（3 项判据修正已拍板落地 + R1/R4 机制 bug 修复 + GEMORNA 30 条/靶）；S1 重跑已启动（约 2026-08-08 06:34 起，PID 见 §4），预计 ~2–2.5 小时，新会话第一步 = 监控 S1 verdict → 判定 → GO 进 S2（18 靶）/ NO-GO 报告用户。**

## 1. 本会话已完成（勿重做）

1. **向用户呈报 S1 首轮 NO-GO**（2026-08-07 21:53 完成，5 靶 A1AT/Insulin/EPO/GFP/IL-2 × 3 臂全 NO-GO），证据：e2e 饱和（三臂全 100%，池过约束候选 45–222/225）、R1/R4 机制 bug、R3 区分度不足。
2. **用户拍板 3 项判据修正**（2026-08-08）：
   - ① e2e 判据「C≥0.8 且 C≥A+0.4」→「**C≥0.8 且 C>A**」（饱和场景 +0.4 结构性无区分度；方向性判据已单独把关）；
   - ② R3 敏感性「≥2/3 画像对」→「**≥1/3 画像对**」（单靶单池 top-1 稳定，5 靶仅 1 过；U 实现已核对无误）；
   - ③ **GEMORNA CDS 采样 20→30 条/靶**（用户提出；池 225→315 候选；缓存增量复用）。
3. **机制修复（非拍板项）**：C 臂最终机制化重排移到 junction eval + U 重算之后（原在 junction 前按旧 U 重排，U 重算后交付序失配，IL-2 R1 ρ 曾达 -0.9）。B 臂自由对照不重排；A 臂 λ 分散序为设计如此（R1/R4 判据仅考核 C 臂，预注册 §9）。
4. **代码落地**：`experiments/run_e5_constraint_nav.py`（`GEMORNA_CDS_N = 30`@332、R3 阈值 @1139、crit1 @1947、终排修复 @1846-1854、docstring 同步 5 处）。
5. **草案 v4 注记**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md` 头部状态行 + 文末 §16（含 S1 首轮证据表、v4 拍板 3 项、机制修复说明、连带影响）。
6. **pytest 全量通过**：649 passed, 1 skipped（与基线一致）。
7. **首轮 S1 产物归档**：`experiments/results/e5_s1_round1_archive/`（e5_s1.log、e5_verdict_s1.json、e5_s1_runs.jsonl、e5_audit/）。
8. **S1 重跑启动**（setsid nohup，日志 `experiments/results/e5_s1.log`，见 §4）。

## 2. v4 判据（S1/S2 现行判据，与代码一致）

| 判据 | v4 文本 |
|---|---|
| ① e2e | C ≥ 0.8 且 **C > A**（去 +0.4） |
| ② 约束满足率 | C ≥ 0.9 |
| ③ R1–R4 | R1 ρ=1.0（tie 内序允许）、R2 τ≥0.8、R3 **≥1/3 画像对**、R4 约束子集内最优 |
| ④ D1–D3 | 全过（D3: pair ratio 极差 ≥3pp 或最长茎差 ≥5bp） |
| ⑤ 方向性 | 每靶点 C ≥ A 至少 4/5 |
| ⑥ 预算记录 | 描述性 |

- S2 全矩阵：**18 靶**（>1300aa 排除，用户拍板；HER2 1255aa/Spike 1273aa 保留，HER2 预期 0 分如实报告）；配对 McNemar p<0.05 或 95%CI 不含 0；R1–R4、D1–D3 全过；约束满足率 C≥0.9。GO/NO-GO 双终点见草案 §10（任一终点过 → GO）。

## 3. S1 重跑须知

- **GEMORNA 缓存复用**：`experiments/results/e5_gemorna_cds_cache.json` 已有 5 靶各 20 条（idx 0–19），重跑按 (target, idx) 增量补采样 idx 20–29（10 条/靶新采样，~4s/条）。
- 池 315 候选/靶 → 池级 eval 更多（~8 分钟/靶），5 靶池 ≈ 40 分钟 + 三臂运行。
- 微服务由驱动 preflight 自动拉起（8004 GEMORNA / 8014 LinearDesign / 8015 LinearFold），启动时日志可见 `service_down_auto_starting`（正常）；RNARL 8008 状态由驱动检查。**勿杀任何 uvicorn / GPU_get.py**。
- 判据由驱动 `run_s1` 内 `write_verdict` 自动判定（crit1–crit5，见 §2 表）。

## 4. 当前运行状态（2026-08-08 06:36 核实）

| 项 | 状态 |
|---|---|
| S1 重跑 | `python experiments/run_e5_constraint_nav.py s1`（setsid nohup，日志 `experiments/results/e5_s1.log`，PID 1028944） |
| 微服务 | 8004/8014/8015 已由 preflight 拉起（uvicorn 1029929/1032586/1034221）+ 常驻 8003/8008/8009/8020 + jupyter + GPU_get.py（勿杀） |

## 5. 下会话第一步（严格按序）

1. `pgrep -af run_e5_constraint_nav` 确认 S1 是否在跑；`tail experiments/results/e5_s1.log` 看进度；`stat experiments/results/e5_verdict_s1.json` 看 mtime（重跑启动时间 ≈ 06:34，mtime 更新 = 有 cell 完成；**进程退出 = 全部完成**）。
2. 若还在跑：`until ! pgrep -f "run_e5_constraint_nav.py s1" > /dev/null; do sleep 60; done` 等完成（后台挂，进程退出会收到通知）。
3. 判定书对照 §2 六项（注意 **verdict 文件每 cell 重写，最终只留最后完成的 cell**——判据为全靶级汇总在文件顶层 `verdict.criteria`，逐靶明细在 `e5_s1_runs.jsonl` / `e5_audit/s1_*.jsonl`）。
4. **GO（全过）** → 直接进 **S2**：`python experiments/run_e5_constraint_nav.py s2`（18 靶 × 3 臂，~2.5–3.5h；2 分片可选 `--shards` 沿 E4 教训勿超 2 分片；判据 §2；HER2 预期 0 分如实报告）。S2 启动前在 MODEL_API_USAGE.md 预登记（§11：C 臂 5–9 次/基因、B 臂 2–4、生成器 LD 72 + RNARL 18 + GEMORNA 540+）。
5. **NO-GO** → 分析证据呈用户；**判据/阈值变更必须先呈用户拍板**（机制层改动可自主实施）。
6. S1 完成当天更新 `experiments/results/MODEL_API_USAGE.md` E5 行实测（LLM 计数、生成器计数、池规模 315）。

## 6. 工程纪律（用户既定规则，必须遵守）

1. **git 操作必须先问用户**（commit/push/reset；工作区大量历史未 commit 勿动）。
2. **pytest 基线 649 passed, 1 skipped**；改代码后必跑全量 `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -q`（约 27s）。
3. 简洁优先；锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项改动先呈用户**（E5 草案已定稿 v4；未拍板一字不改）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程；**命令须同条内 `cd rna_agent_system &&`**。
7. 决策文化：重大路线由用户决定，助手给建议与证据；论文 Nat Methods 直冲。

## 7. 关键指针

- **E5 草案 v4**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`（§16 v4 注记）。
- **驱动**：`experiments/run_e5_constraint_nav.py`（build_pool@~692、mechanize_delivery_order@~1292、终排修复@~1846、write_verdict@~1960+、GEMORNA_CDS_N@332）。
- **S1 首轮归档**：`experiments/results/e5_s1_round1_archive/`（证据：e2e 饱和 / R1 ρ=-0.9 / R3 0/3）。
- **S0 判定书**：`experiments/results/e5_verdict_s0.json`（GO，五项全过，R2 τ≈1.0）。
- 上一交接：`HANDOFF_2026-08-07_E5_PLAN_B_S0_GO_S1_RUNNING.md`。
- 20 靶目录：`data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/`（实际 18 靶）。
