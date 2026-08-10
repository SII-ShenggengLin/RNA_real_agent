# 交接提示词（2026-08-06 05:45 UTC：E4 全矩阵运行中，两 shard 均在跑；新会话续检/续跑）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-05_E4PREREGISTERED.md`（预注册决策与实施）→ `HANDOFF_2026-08-05_E4FULL_RUNNING.md` → `HANDOFF_2026-08-05_E4FULL_MIDRUN.md`（含 §3 监控检查项）→ `HANDOFF_2026-08-06_E4FULL_PAUSED_RESTART.md`（暂停/续跑交接）→ **本文件（续跑后运行中交接）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。
> 写本文件时：**两 shard 驱动均存活、在跑**，总计 **60/120 战役完成**（A 32/80、B 28/40），无异常死亡，未做任何代码/git 改动。

## 0. 一句话现状

**E4 全矩阵（120 战役）续跑中，两 shard 均正常在跑**：shard A（PID 160421，04:29:57 启动，当前 [33/80] A/memory c13 Beta_galactosidase）、shard B（PID 1451436，本会话启动，当前 [29/40] C/memory c9 Factor_VIII）。**无需重启任何进程**。本会话已核实 2 条续跑后新增的 cli_failure 记录（见 §3，需呈报用户定夺收尾口径），并重设了每小时监控 cron（**cron 随本会话失效，新会话须重设**，见 §4）。

## 1. 本会话做了什么（勿重做）

1. **核实现状**：续跑前发现 shard A 已在跑（04:29:57 启动，`--resume` 续跑正常，非本会话启动——疑似上会话或用户启动），shard B 未启动。
2. **单独启动 shard B**：`setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py --targets "$T" --seed-groups C --timeout 9000 --resume --output experiments/results/e4_full_shard_b.jsonl ...`（日志 append 衔接暂停前）。启动后 pgrep 确认 **2 个 python 进程**。
3. **重设每小时监控 cron**：CronCreate `7 * * * *`（prompt 指向 `HANDOFF_2026-08-05_E4FULL_MIDRUN.md` §3 检查项 + 本文件 §3 的 cli_failure 呈报项）。**本会话关闭后 cron 即失效，新会话自行重设**（同 §4）。
4. **核实 2 条新 cli_failure 记录**（见 §3）：确认为预声明靶点（Zika_E_protein、Factor_VIII）LinearDesign SIGKILL（returncode=-9）OOM 形态，**记录勿重启**；但驱动 `acceptable_failure=False`（driver.log 无 OOM 关键词），**收尾分析会受影响 → 呈报用户定夺**。
5. **未改任何代码、未做任何 git 操作**。

## 2. 当前进度（写本文件时快照，勿误读）

- **shard A**（种子组 A+B，80 战役）：JSONL **32 行**（A/nomem 20 + A/memory 12，其中 c7 Zika、c8 Factor_VIII 为 cli_failure）。当前 [33/80] A/memory c13 Beta_galactosidase。剩余：A/memory c14-c20 + B 组 40 场。
- **shard B**（种子组 C，40 战役）：JSONL **28 行**（C/nomem 20 + C/memory 8）。当前 [29/40] C/memory c9 Factor_VIII（**预声明靶点，大概率同样 cli_failure**）。剩余 C/memory c10-c20。
- 记忆根 `workspace/e4_full/case_memory/{A,B,C}`：A 组 5 条、C 组 8 条（驱动每次启动按 JSONL 重建，`--resume` 幂等，勿手工改动）。
- **耗时参考**：memory 臂注入后显著加速（1-30min/场，evals 1-13），nomem 中位 ~23min/场。剩余 ~60 场，双 shard 并行预计 **~1 天内跑完**（nomem 为主）。

### memory 注入效果（续跑后新增，均为 memory 臂）

| cell | evals | fired |
|---|---|---|
| A c6 Growth_hormone | 13 | design_tool+λ, bmc_max_rounds |
| A c7 Zika_E_protein | **FAIL cli_failure** | 预声明靶点（见 §3） |
| A c8 Factor_VIII | **FAIL cli_failure** | 预声明靶点（见 §3） |
| A c9 HER2 | 待完成 | |
| C c8 IFN_alpha_2a | **1** | 三注入全触发 |

## 3. ⚠️ 需呈报用户的事项：2 条 cli_failure 记录（acceptable_failure=False）

**记录**：`e4_A_memory_c7_Zika_E_protein`、`e4_A_memory_c8_Factor_VIII`，`error=cli_failure`、`acceptable_failure=False`，session driver.log 为 `LinearDesign service request failed: 500 ... returncode=-9; stderr=`（**SIGKILL = 预声明 OOM 形态**）。

**判定**：目标（Zika/Factor_VIII ~7kb CDS）与失败模式均属预声明预期失败 cell（`run_e4_learning_curve.py` docstring 121-124 行），**按 §3.2 记录、勿重启** ✓（驱动已自动继续，无影响）。

**问题（收尾影响）**：驱动 `is_acceptable_failure` 只在 driver.log 出现 "out of memory"/"bad_alloc"/"oom" 或 `error=="timeout"` 时返回 True；本次 stderr 为空、日志无关键词 → `acceptable_failure=False`。而暂停前 4 场预声明失败（nomem 臂）是 `success=True + evals=9 + final_lambda=None` 形态，分析脚本对它们不产生意外失败计数。**这 2 条（以及后续 B、C 组 memory 臂同靶点预计 ~4 场同样失败）会被 `e4_analysis.py` 计为 n_unexpected_fail（c1）与 cells_bad（c4）→ overall_pass=False**，与预注册"这些 cell 无效化并列出、不计入终点"的意图不符。

**处置建议（呈用户拍板，勿自行改动预注册代码）**：
- 方案 A（推荐，最小改动）：收尾分析时按预声明靶点集合（Zika_E_protein、Factor_VIII）将此类 cli_failure 记录视作可接受失败（改 `e4_analysis.py` 判定或补录标志，**改代码前先问用户**）。
- 方案 B：维持现状，判定书如实报 n_unexpected_failure=6 左右，由用户决定整体判定口径。
- **到这一步时先报告用户，等指示后再动代码。**

## 4. 监控职责（新会话重设 cron：CronCreate `7 * * * *`，prompt 指向本文件 + MIDRUN §3）

> 每小时 cron 为会话内有效（关闭即失效）——**新会话自行重设**。prompt 建议：`E4 全矩阵每小时监控：① pgrep -af run_e4_learning_curve | grep -v "bash -c" | grep python 应见 2 个进程；② wc -l 两 JSONL 对照 [n/80]、[n/40]；③ 可接受失败（timeout/OOM/预声明 cell）记录勿重启；④ 异常死亡先报告用户勿自动重启；⑤ 跑完 120 战役后执行收尾（§6）；⑥ 详见 experiments/results/HANDOFF_2026-08-06_E4FULL_CONTINUED.md §4-6。`

1. **每小时**：`pgrep -af run_e4_learning_curve | grep -v "bash -c" | grep python` 应见 2 个 python 进程 + `wc -l` 两 JSONL 得完成数（对照 `[n/80]`、`[n/40]` 当前战役）。
2. **可接受失败**（记录，**勿重启**）：子进程超时（`error == "timeout"`）/ LinearDesign OOM（driver.log 含 out-of-memory/bad_alloc，SIGKILL）；Zika_E_protein、Factor_VIII 属**预声明预期 cell**（含本会话新增的 cli_failure/SIGKILL 形态，见 §3）。
3. **异常死亡先报告用户，勿自动重启**：进程数 ≠ 2、非 OOM 的 Traceback/Killed、驱动主进程意外退出。
4. **续跑**：同一命令加 `--resume` 幂等（done-key = (seed_group, arm, target_id) 且仅 success=True 记 done；JSONL 无重复完成键）。用户决定重启时用 §5 命令。
5. 进度汇报要点：两 shard JSONL 行数 / 当前战役 / 子进程活跃情况。

## 5. 续跑命令（用户决定重启某 shard 时用，两 shard 分别单独启动）

```bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system
T="A1AT,Albumin,Beta_galactosidase,EPO,Factor_VIII,GFP,Growth_hormone,HER2,HIV-1_Env_gp120,HPV16_L1,IFN_alpha_2a,IL-2,Influenza_HA_H1N1,Insulin,Luciferase,Ovalbumin,RSV_F_protein,SARS-CoV-2_Spike_WT,Transferrin,Zika_E_protein"
# shard A（若 A 已在跑只起 B）
setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py --targets "$T" --seed-groups A,B --timeout 9000 --resume --output experiments/results/e4_full_shard_a.jsonl > experiments/results/e4_full_shard_a.log 2>&1 < /dev/null &
# shard B
setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py --targets "$T" --seed-groups C --timeout 9000 --resume --output experiments/results/e4_full_shard_b.jsonl > experiments/results/e4_full_shard_b.log 2>&1 < /dev/null &
```
（教训：同一条命令 `&` 串联两个 shard 时第二个可能因重定向竞态失败；**分别单独启动**，启动后 pgrep 数进程应见 2 个 python。）

## 6. 跑完后的收尾（按序执行，120 战役 = 80 + 40）

1. 确认两驱动进程退出、JSONL 记录齐全（全部 success 或预声明失败形态）。
2. **先就 §3 的 cli_failure 记录处置呈报用户**（改分析代码前必须获准）。
3. **合并分析出判定书**：
   ```bash
   PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/e4_analysis.py
   ```
   输出 `experiments/results/e4_full_summary.json`（pass_criteria + endpoints + go_no_go）。双终点判定规则（预注册锁定）：
   - **效率终点**（两分量都需）：① memory 斜率显著为负（per 组 per 臂回归；3 组 memory 斜率单样本 t one-sided less p<0.05）② 预算节省 1−Σmem/Σnomem ≥25%（配对成功 cell；预声明失败 cell 排除）。
   - **设计收益终点**（任一指标过即可）：4 个已验证指标（CAI↑、全长 MFE↓、接头 mfe/nt 均值↓、GemORNA MRL↑）配对 Wilcoxon、BH-FDR 校正、Cliff's δ |δ|≥0.3 方向有利 → q<0.05 且 δ 达标 → 指标过。
   - **任一终点过 → GO**；双终点均不过 → NO-GO（退路 = 记忆简化为画像结果复用，见 REDESIGN §6）。
4. 向用户报告双终点 GO/NO-GO + 判定书要点。
5. **更新 MODEL_API_USAGE.md**：E4 全矩阵行预登记 240 次 → 实测（按驱动 JSONL 中 `quality_actions` 统计，试点 24 次/12 战役）。
6. git 提交询问用户（判定书/JSONL 在 ignored 目录，代码文件是否需提交由用户定）。

## 7. 工程纪律（用户既定规则）

1. **git 操作必须先问用户**（commit/push/reset）。
2. **pytest 基线 649 passed, 1 skipped**；改代码后必跑全量 `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -q`（约 25s）。
3. 简洁优先；锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项若需改动，先呈用户**（全矩阵已拍板项见 `HANDOFF_2026-08-05_E4PREREGISTERED.md` §2，不要自行改动）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程。
7. 决策文化：重大路线由用户决定，助手给建议与证据；论文 Nat Methods 直冲，不做提前预注册公开。

## 8. 关键指针

- 全矩阵预注册全文：`experiments/run_e4_learning_curve.py` docstring。
- 前序交接（决策背景/已拍板项/启动时状态/暂停续跑）：`experiments/results/HANDOFF_2026-08-05_E4PREREGISTERED.md`、`HANDOFF_2026-08-05_E4FULL_RUNNING.md`、`HANDOFF_2026-08-05_E4FULL_MIDRUN.md`、`HANDOFF_2026-08-06_E4FULL_PAUSED_RESTART.md`。
- 试点判定书（管线验证件）：`experiments/results/e4_pilot_summary.json`（overall_pass=True）。
- 服务由 `ensure_services_ready` 自动拉起（勿手动启动）；本实验仅 2 分片，无竞争超时风险。
- E4 设计：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4 + §5 里程碑。
