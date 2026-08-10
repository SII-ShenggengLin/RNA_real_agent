# 交接提示词（2026-08-05 22:02 UTC：E4 全矩阵 120 战役运行中段，新会话接管监控）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-05_E4PREREGISTERED.md`（预注册决策与实施）→ `HANDOFF_2026-08-05_E4FULL_RUNNING.md`（启动时交接）→ **本文件（运行中段交接）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。
> 写本文件时：**E4 全矩阵双分片运行中，29/120 完成，两驱动健康无异常**（详见 §2）。

## 0. 一句话现状

**E4 全矩阵（120 战役）双分片运行至中段：shard A（种子组 A+B）12/80、shard B（种子组 C）17/40，合计 29/120。** 两驱动进程存活，全程无异常死亡、无重启。预声明预期失败 cell（Zika_E_protein、Factor_VIII）在 A 侧已如期触发并记录（记录即止、勿重启）。新会话职责不变：**每小时监控 → 跑完合并分析出判定书 → 报告双终点 GO/NO-GO**。

## 1. 已完成的实施（勿重做）

1. 预注册落文、驱动改造、双终点分析脚本、测试基线（649 passed, 1 skipped）、git 提交 `3a2cf63`、MODEL_API_USAGE.md 预登记 240 次——**全部已完成**，细节见 `HANDOFF_2026-08-05_E4FULL_RUNNING.md` §1，勿重做。
2. 运行期监控（本会话及前两会话）：累计 29 场完成，无异常死亡、无重启、无 timeout/OOM 之外的记录。

## 2. 当前运行中的实验（勿动，监控即可）

- **shard A**：PID `3977587`，`--seed-groups A,B`（80 战役），输出 `experiments/results/e4_full_shard_a.jsonl` / `.log`。当前战役 `[13/80]` A/nomem Beta_galactosidase（子进程 PID `2259046`，写本文件时已跑 ~49min，正常——单场最长为 5918s ≈ 99min）。
- **shard B**：PID `3995634`，`--seed-groups C`（40 战役），输出 `experiments/results/e4_full_shard_b.jsonl` / `.log`。当前战役 `[18/40]` C/nomem SARS-CoV-2_Spike_WT（子进程 PID `3442482`，刚启动 ~2min）。
- 记忆根 `workspace/e4_full/case_memory/{A,B,C}` 已建（目前仅记录 nomem 完成键，memory 战役随 A/B 组后续进度写入）。

### 关键监测经验（重要，避免误判）

- **驱动 stdout 有缓冲滞后**：日志尾部可能滞后实际进度数分钟（滞后期间日志仍显示旧战役）。**以 JSONL 行数 + `workspace/sessions/` 目录 mtime 为真实进度基准**，日志尾部仅作参考。
- 上会话曾因日志滞后误判"Factor_VIII 空转 73 分钟"——实际已正常完成（4394s）。核查方法：`ls -la --time-style='+%m-%d %H:%M' workspace/sessions/ | grep e4_e4_A` 看各 session 目录 mtime 序列，与 `OK in <秒>` 时长相减可验证一致性。
- 子进程存活但长时间零输出 ≠ 异常：初始 LLM 规划阶段可能静默数十分钟（Factor_VIII 全程 4394s 内约前 19min 无 driver.log 输出）。

### 已触发的预声明预期失败 cell（记录即可，勿重启）

- A 侧 c7 Zika_E_protein：`OK in 963s, evals=9, final_lambda=None`（预期失败形态）。
- A 侧 c8 Factor_VIII：`OK in 4394s, evals=9, final_lambda=None`（预期失败形态）。
- B 侧如后续出现同款（evals=9 / final_lambda=None 或 timeout/OOM），同属预声明范围，记录勿重启。

## 3. 监控职责（每小时）

> 上一会话设的每小时 cron 是会话内有效的（关闭即失效）——新会话**自行重设每小时监控**（CronCreate `7 * * * *`，prompt 指向本文件 §3 检查项）或手动按节拍查。

1. **每小时**：`pgrep -af run_e4_learning_curve | grep -v "bash -c"` 应见 2 个 python 进程 + `wc -l` 两 JSONL 得完成数（对照 `[n/80]`、`[n/40]` 当前战役）。
2. **可接受失败**（记录，**勿重启**）：子进程超时（`error == "timeout"`）/ LinearDesign OOM（driver.log 含 out-of-memory/bad_alloc，SIGKILL）；Zika_E_protein、Factor_VIII 的失败属**预声明预期 cell**。
3. **异常死亡先报告用户，勿自动重启**：进程数 ≠ 2、非 OOM 的 Traceback/Killed、驱动主进程意外退出。
4. **续跑**：同一命令加 `--resume` 幂等（done-key = (seed_group, arm, target_id)；JSONL 无重复完成键）。用户决定重启时用 §4 命令。
5. 进度汇报要点：两 shard JSONL 行数 / `[n/80]`、`[n/40]` 当前战役 / 子进程活跃情况。

## 4. 续跑命令（如需重启某 shard）

```bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system
T="A1AT,Albumin,Beta_galactosidase,EPO,Factor_VIII,GFP,Growth_hormone,HER2,HIV-1_Env_gp120,HPV16_L1,IFN_alpha_2a,IL-2,Influenza_HA_H1N1,Insulin,Luciferase,Ovalbumin,RSV_F_protein,SARS-CoV-2_Spike_WT,Transferrin,Zika_E_protein"
# shard A
setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py --targets "$T" --seed-groups A,B --timeout 9000 --resume --output experiments/results/e4_full_shard_a.jsonl > experiments/results/e4_full_shard_a.log 2>&1 < /dev/null &
# shard B（若 A 已在跑只起 B）
setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py --targets "$T" --seed-groups C --timeout 9000 --resume --output experiments/results/e4_full_shard_b.jsonl > experiments/results/e4_full_shard_b.log 2>&1 < /dev/null &
```
（教训：同一条命令 `&` 串联两个 shard 时第二个可能因重定向竞态失败；**分别单独启动**，启动后 pgrep 数进程。）

## 5. 跑完后的收尾（按序执行）

1. 确认两驱动进程退出、JSONL 记录齐全（120 = 80 + 40）。
2. **合并分析出判定书**：
   ```bash
   PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/e4_analysis.py
   ```
   输出 `experiments/results/e4_full_summary.json`（pass_criteria + endpoints + go_no_go）。双终点判定规则（预注册锁定）：
   - **效率终点**（两分量都需）：① memory 斜率显著为负（per 组 per 臂回归；3 组 memory 斜率单样本 t one-sided less p<0.05）② 预算节省 1−Σmem/Σnomem ≥25%（配对成功 cell）。
   - **设计收益终点**（任一指标过即可）：4 个已验证指标（CAI↑、全长 MFE↓、接头 mfe/nt 均值↓、GemORNA MRL↑）配对 Wilcoxon、BH-FDR 校正、Cliff's δ |δ|≥0.3 方向有利 → q<0.05 且 δ 达标 → 指标过。
   - **任一终点过 → GO**；双终点均不过 → NO-GO（退路 = 记忆简化为画像结果复用，见 REDESIGN §6）。
3. 向用户报告双终点 GO/NO-GO + 判定书要点。
4. **更新 MODEL_API_USAGE.md**：E4 全矩阵行预登记 240 次 → 实测（按驱动 JSONL 中 `quality_actions` 统计，试点 24 次/12 战役）。
5. git 提交询问用户（判定书/JSONL 在 ignored 目录，代码文件是否需提交由用户定）。

## 6. 工程纪律（用户既定规则）

1. **git 操作必须先问用户**（commit/push/reset）。
2. **pytest 基线 649 passed, 1 skipped**；改代码后必跑全量 `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -q`（约 25s）。
3. 简洁优先；锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项若需改动，先呈用户**（全矩阵已拍板项见 `HANDOFF_2026-08-05_E4PREREGISTERED.md` §2，不要自行改动）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程。
7. 决策文化：重大路线由用户决定，助手给建议与证据；论文 Nat Methods 直冲，不做提前预注册公开。

## 7. 关键指针

- 全矩阵预注册全文：`experiments/run_e4_learning_curve.py` docstring。
- 前序交接（决策背景/已拍板项/启动时状态）：`experiments/results/HANDOFF_2026-08-05_E4PREREGISTERED.md`、`experiments/results/HANDOFF_2026-08-05_E4FULL_RUNNING.md`。
- 试点判定书（管线验证件）：`experiments/results/e4_pilot_summary.json`（overall_pass=True）。
- 耗时参考：`HANDOFF_2026-08-05_E4PREREGISTERED.md` §4（per 靶点中位耗时；合计 ~14.2h/单臂全靶；双分片约 2–3 天纯计算、~1 周墙钟含续跑）。
- 服务由 `ensure_services_ready` 自动拉起（勿手动启动）；本实验仅 2 分片，无竞争超时风险。
- E4 设计：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4 + §5 里程碑。
