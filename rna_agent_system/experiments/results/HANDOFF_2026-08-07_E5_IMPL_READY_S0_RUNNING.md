# 交接提示词（2026-08-07：E5 实施完成 + S0 机制验证正在后台运行）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E5DRAFT_V3_APPROVED.md`（定稿 v3 + 锚点拍板 ①去锚点）→ **本文件（实施完成，S0 运行中）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`；Bash 工作目录跨调用持久——后台任务须同条命令内 `cd rna_agent_system &&`，git 命令带 `-C <项目根>`）。

## 0. 一句话现状

**E5 驱动已写完并通过全部验证（离线自测 50+ 项、pytest 649 passed、LLM/微服务验证）；S0 机制验证（Insulin × C 臂 × 3 重复）正在后台运行（setsid 分离，会话关闭不影响）——新会话第一步 = 检查 S0 状态（`pgrep` + 日志 + 判定书），出判定书后呈用户确认，然后 S1 → S2。**

## 1. 本会话已完成（勿重做）

1. **锚点方案拍板**（2026-08-07，AskUserQuestion）：**①去锚点**——池 = 4 λ CDS × 9 GEMORNA UTR = 36 候选，零新数据、三臂公平。
2. **驱动写完** `experiments/run_e5_constraint_nav.py`（~1250 行，docstring = 定稿 v3 全文移植 + 9 条【实施细化】注记，含 CLI S0/S1/S2 + `--targets/--arms/--repeat/--resume/--dry-run/--output`）：
   - 约束判定器 C1–C8+M1（本地纯函数 + LinearFold；C6 窗口「5'UTR+CDS 前 30nt」、C7 全长最长茎 ≤30bp；C7/E7-pair ratio/D3 共用同一次全长 fold；窗口 fold 按 (utr5,cds) 去重缓存 → 12 次/靶点）；
   - 池生成（§3.1 方案①）：`MrnaCdsDesignWorkflow(registry).generate_candidates`（design_tool="lineardesign" 每次 1 CDS × λ{0,1,4,10}）+ GEMORNA 6 次生成（序列按 preset 缓存）+ 池级 GEMORNA 预测 6 次（按唯一 UTR 序列共享）+ ~36 全长 fold + 12 窗口 fold + 本地档案 E1–E12（E8 |ΔGC| 与 `external_anchors/wt_cds/<target>.fa` 比较，实施细化 2）；**池级不调 workflow.evaluate**，交付级 5 候选才补 E3 junction（JunctionEvaluator，真实 `Candidate` 模型，context={"workflow_state": {}}）；
   - 三臂：A 规则（过滤→画像权重→选 5，零 LLM 零工具）；B 无门控 agentic 循环（2–4 次 LLM，≤1 次 LinearDesign）；C 门控（DecisionGate 复用 E3 `PlannedAction(use="none")` + 约束矩阵 gate + 仲裁链 4 层校验 + 修复轮 ≤2 轮池内重选 / CDS 级无解时 ≤1 次 λ 邻域重跑；5–9 次 LLM）；**服务自启**：`ensure_e5_services()`（幂等，`get_services_for_capabilities` 映射 8004/8014/8015 → `ensure_services_ready`），`run_one_cell` 开头调用——因为直接调 `generate_candidates` 绕过 workflow.execute 的自启路径，**这个补丁必须有**；
   - U 函数（§5：区域权重 expression 0.35/0.45/0.20、stability 0.15/0.50/0.35、balanced 1/3；区域内 5'UTR 主轴 0.6/0.4、CDS 三指标均分、3'UTR 单指标 1.0；U=0.8×regional+0.2×global(MFE，交付级并入 junction)）；
   - R1–R4 / D1–D3 / 端到端通过率 / 约束满足率 / S0/S1/S2 判定书 JSON / S2 配对 McNemar（**scipy 1.17 无 `stats.mcnemar` → 用 `stats.binomtest` 二项精确检验**，`p = binomtest(min(b,c), b+c, 0.5, two-sided)`）；
3. **验证全过**：
   - 离线纯函数自测 50+ 项（`/tmp/e5_selftest.py`，可重跑）——约束判定、stem/pair_ratio 辅助、E6 rare codon、E10 Kozak、U 单调性、R1/R3/R4、D1–D3、R2 τ、McNemar、diversity_distance；
   - **pytest 全量 649 passed, 1 skipped**（基线一致）；
   - DeepSeek LLM 最小调用验证（deepseek-v4-pro, temp 0.0, 1.6s；`agent_core/llm_config.py:53` `load_dotenv()` 自动读 `.env`，无需手工导出环境变量）；
   - 微服务自启验证：**S0 启动时 3 服务（GEMORNA 8004 / LinearDesign 8014 / LinearFold 8015）自动拉起，`[preflight] 3 service(s) healthy`**。注意：交接文档此前说"常驻微服务勿动"，但实际 7 个 uvicorn 全部没在跑（仅 jupyter 8088 + GPU_get.py），S0 运行中已自启 GEMORNA/LinearDesign/LinearFold——**新会话监控时若看到 8004/8014/8015 有 uvicorn 进程属正常（S0 拉起的），勿杀**。
4. **MODEL_API_USAGE.md 预登记完成**（§2 表末行 + 头部时间戳）：E5 = C 臂 5–9 次/基因、B 臂 2–4 次、A 臂 0；S0 预算 15–27 次、S1 ~35–65、S2 ~140–260；**S0/S1/S2 跑完后当天更新实测行**（§6 规范 2）。

## 2. 正在运行的实验（S0 机制验证）——新会话第一步

- **命令**（已用 setsid nohup 启动，会话关闭不影响）：
  `setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s0 --targets Insulin --repeat 3 > experiments/results/e5_s0.log 2>&1 &`
- **状态检查**：`pgrep -af "run_e5_constraint_nav"`（应有 python 进程）；日志 `experiments/results/e5_s0.log`（末尾应见 `[s0:Insulin] building shared pool ...` → CDS/UTR 每步一行 → `pool done: 36 candidates, N pass all constraints` → `C-arm repeat 1/3..3/3` → `[s0] verdict -> ...`）。
- **输出**：`experiments/results/e5_s0_runs.jsonl`（append）+ `experiments/results/e5_verdict_s0.json`（判定书）。
- **S0 判据**（§9，全过 → GO）：①约束识别 100%（构造保证：档案约束表）②输出格式完整（每画像交付 5 候选）③R2 稳定性 τ≥0.8（`evaluations.C.R2_tau_min`）④无崩溃 ⑤单场耗时 ≤ 40min 预算。
- **预期耗时**：池生成 ~13–15min + 3 次 C 臂 agentic 循环（每次 ~3–6min LLM + 交付级 junction folds）≈ 30min。若本会话关闭时还在跑，新会话先 `pgrep` 确认进程活着，然后轮询日志（后台 `until` 循环等 `e5_verdict_s0.json` 出现或进程退出）。
- **若失败**：读日志定位（服务未起→驱动幂等自启会重试；LLM 报错→检查 `.env` 的 DEEPSEEK_API_KEY；池生成失败→`RuntimeError: pool generation failed`）；修驱动后 `--resume`（按 (stage, target, arm) done-key 跳过）重跑。

## 3. 下一步（S0 判定书出来后按序）

1. **呈 S0 判定书给用户**（criteria 五项 + GO/NO-GO），**用户确认后才进 S1**（E4 教训：判据从 S0 起生效、每阶段判定书、未过不进下一阶段；S1 判据不过时备选动作由用户定）。
2. **S1 小规模**（5 靶点 × 3 臂，~1.5–2h）：
   `setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s1 --targets A1AT,Insulin,EPO,GFP,IL-2 > experiments/results/e5_s1.log 2>&1 &`
   - 判据（§9 S1 表）：①端到端通过率 C≥0.8 且 C≥A+0.4 ②约束满足率 C≥0.9 ③R1–R4 全过 ④D1–D3 全过 ⑤方向性 C≥A 至少 4/5 ⑥BMC 预算记录（描述性）；任一不过 → 报告用户不自动进 S2。
   - 5 靶点确认：定稿 S1 靶点集是否用 `A1AT,Insulin,EPO,GFP,IL-2`（驱动内 `S1_TARGETS` 常量，Insulin/IL-2/GFP 为无 OOM 风险小基因，避开 Zika/Factor_VIII）。
3. **S2 全矩阵**（20 靶点 × 3 臂，~4–5h；2 分片串行，`--targets` 拆分，服务串行处理请求勿超 2 分片并发）：
   `... python experiments/run_e5_constraint_nav.py s2 --targets <10靶点> --output experiments/results/e5_s2_shard_a.jsonl ...`
   - 判据（§9 S2 表）：①配对 McNemar p<0.05（C vs A 且 C vs B；配对单位 = 基因×画像 n=60，实施细化 7；基因级 20 描述性报告）②R1–R4、D1–D3 全过 ③约束满足率 C≥0.9。
   - GO/NO-GO 双终点（§10）：终点 1（McNemar 双过 + C 端到端 ≥0.8）/ 终点 2（R1–R4+D1–D3 全过 + 约束满足率 ≥0.9）；任一过 → GO，仅终点 1 过须披露终点 2。
4. **S0/S1/S2 全部完成后当天更新 MODEL_API_USAGE.md 实测行**（§2 表末行：实测 LLM 调用数）。

## 4. 工程纪律（用户既定规则，必须遵守）

1. **git 操作必须先问用户**（commit/push/reset）。
2. **pytest 基线 649 passed, 1 skipped**；改代码后必跑全量（约 25s）。
3. 简洁优先；锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项若需改动，先呈用户**（E5 定稿 v3 已拍板）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程；命令同条内 `cd rna_agent_system &&`。
7. 决策文化：重大路线由用户决定，助手给建议与证据；论文 Nat Methods 直冲，不做提前预注册公开。

## 5. 关键指针

- **E5 驱动**：`experiments/run_e5_constraint_nav.py`（docstring = 定稿 v3 全文 + 实施细化注记；CLI `--dry-run` 可打印矩阵自检）。
- **E5 定稿 v3**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`（§9 关卡 / §10 GO-NO-GO / §14 耗时预算：S0 ~30min、S1 ~1.5–2h、S2 ~4–5h 2 分片）。
- **上一份交接**：`experiments/results/HANDOFF_2026-08-07_E5DRAFT_V3_APPROVED.md`（§3 实施顺序 / §4 纪律 / §5 指针）。
- **离线自测**：`/tmp/e5_selftest.py`（改纯函数后可重跑，无需微服务）。
- **E4 先例**：`experiments/run_e4_learning_curve.py`（驱动结构模板）。
- **门控组件**：`agent_core/calibrated/`（DecisionGate/SelfModel/AuditTrail；E5 用 `PlannedAction(use="none")` → allow + 审计）。
- **20 靶点**：`data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/`（JSON 仅 protein_sequence）；wt CDS：`data/benchmarks/external_anchors/wt_cds/`（E8 |ΔGC| 参考，方案①去锚点后仍用）。
- **MODEL_API_USAGE.md**：`experiments/results/MODEL_API_USAGE.md`（§2 末行 E5 预登记）。
- **微服务**：8004 GEMORNA（生成+预测）/ 8014 LinearDesign / 8015 LinearFold——S0 已自启，若新会话中发现 down，驱动 `run_one_cell` 会幂等自启。
