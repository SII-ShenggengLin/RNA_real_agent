# 交接提示词（2026-08-04 W5–9 深夜版：E3 全矩阵在跑，新会话专用）

> 用法：新会话先读本文件；工程纪律沿用 `HANDOFF_2026-08-04_W34_CLOSEOUT.md` §3 与 `HANDOFF_2026-08-04_W59_COMPONENTS_E3PILOT.md` §4（含坑 16：后台启动后必须 pgrep 数进程）。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（命令统一带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。

## 0. 一句话现状

**Layer 3 重建组件齐套（`agent_core/calibrated/`，pytest 基线 564 passed, 1 skipped）；E3 预注册修订 v1.1（"无核验依据不发言"统一规则）已落地并通过前置验证（三项 go 全绿）；E3 全矩阵（20 任务 × 2 臂 = 40 runs）正在后台跑。**

## 1. 正在跑的实验（首要任务：接管监控）

- **进程**：`python experiments/run_e3_gated_vs_ungated.py --resume --output experiments/results/e3_runs_full.jsonl`（2026-08-04 ~14:08 UTC 启动，单进程已确认）。
- **日志**：`experiments/results/logs/e3_full_run.log`（尾部应有 `done: 40 new runs` 即完成）。
- **产出**：`experiments/results/e3_runs_full.jsonl`，目标 **40 行**（20 任务 × ungated/gated 两臂），预计 35–45 分钟墙钟。
- 监控：`pgrep -af "e3_runs_full" | grep -v "bash -c"`；`wc -l experiments/results/e3_runs_full.jsonl`；`tail -2 日志`。
- 进程死了先查日志区分正常退出/被杀；`--resume` 幂等，重跑同一命令即可续（重复启动前必须确认旧进程已死——双驱动会写重复行）。
- **完成后**：
  1. 校验 40 个唯一 (task_id, arm)（若意外有重复，保首条去重——先例见 W59 交接 §4）。
  2. `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/e3_adjudicate.py --runs experiments/results/e3_runs_full.jsonl`（如需措辞边界复核加 `--llm-review`）。
  3. `PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/e3_analysis.py --runs experiments/results/e3_runs_full.jsonl` → `_summary.json`。
  4. **当天更新 `experiments/results/MODEL_API_USAGE.md`**：E3 全矩阵行（DeepSeek deepseek-v4-pro，temp 0，每任务每臂 2 次调用，共 **80 次**，零 GPU，usage_available=false 按 §1 剖面估算）。
  5. 向用户汇报全矩阵结果（FP 率对比、TP 保留、越权事件、go/no-go：FP 相对降 ≥50% 且 TP 保留 ≥90%），由用户判定 E3 是否 GO、是否进 Results 4 写作。

## 2. 预注册修订 v1.1（用户已定方向："无核验依据不发言"统一规则，非补丁）

一条原则两条腿：每条定量/比较 claim 的依据必须经系统真实核验——能精确重算的走**重算核验腿**（门控臂写出前确定性自检，不合格弃权不发）；不能重算的走**能力画像腿**（任何 oracle 含 GC 等"免费"代理，被用作排序/筛选依据时经 CapabilityProfiler 同一协议画像进 SelfModel）。
落地：ClaimGate 比较类 claim 空依赖即拒（`COMPARATIVE_CLAIM_TYPES`）；profiler 加 `purine_content` scorer；驱动 v1.1（docstring 修订、提示词要求声明依据、`_execution_verification`）。前置验证（6 任务）：门控臂 3 TP / 0 FP / 越权 0，对照臂 4 FP / 越权 5，三项 go 全绿 → 用户授权开全矩阵。记录：`e3_runs_precheck*.jsonl`、CHANGELOG 2026-08-04 W5–9 条目、ARCHITECTURE.md §2.4.1。

## 3. 关键背景指针

- 组件/试点细节：`HANDOFF_2026-08-04_W59_COMPONENTS_E3PILOT.md`（§2 两个试点问题 = v1.1 的由来）。
- E1 证据（gated SelfModel 预加载源）：`experiments/results/e1_capability_summary_v2.json`（18 oracle×target 细胞全 failed）；oracle 分数查找表须**合并读试点+v2 两个 scoring JSONL**（驱动已固化）。
- 任务集：`experiments/e3/audit_tasks.json`（生成器断言优先、确定性）；盲化映射 `_SEALED` 文件论文复核前勿开。
- 设计文档：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md`（E3 见 §3，v1.1 属 §2.3 step 6 的实例化，回写设计文档留给用户定）。

## 4. 后续（全矩阵完成后，按用户指示）

- E3 GO → Results 4 写作素材整理（per-arm summary + worked example：aptamer_ranking_1 教科书式拒答）。
- W10–11：设计时集成优化器（接头项进 LinearDesign 生成目标）→ E4 全矩阵（执行器禁用未画像 oracle 作评判）。
- 暂缓项同前：E2(b) 文献审计排期、bmc_x1 BSA seed 重跑（进论文前）。

## 5. 纪律重申

- git 操作必须先问用户；pytest 基线 **564 passed, 1 skipped**；改代码后必跑。
- 产生论文数据当天更新 MODEL_API_USAGE.md。
- 后台驱动：`setsid nohup` + 日志落盘 + 启动后 pgrep 数进程（单工作者）。
