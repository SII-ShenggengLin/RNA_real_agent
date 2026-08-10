# 交接提示词（2026-08-06 03:30 UTC：E4 全矩阵因机器关机暂停，已安全停止；新会话续跑）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-05_E4PREREGISTERED.md`（预注册决策与实施）→ `HANDOFF_2026-08-05_E4FULL_RUNNING.md`（启动时交接）→ `HANDOFF_2026-08-05_E4FULL_MIDRUN.md`（中段交接，含 §3 监控检查项）→ **本文件（暂停/续跑交接）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。
> 写本文件时：**E4 全矩阵 52/120 完成，驱动已由 SIGTERM 安全停止（无半条记录），--resume 续跑即可，无需重跑已完成战役。**

## 0. 一句话现状

**E4 全矩阵（120 战役）暂停于 52/120（A 25、B 27），全部 success。** 机器需关机，驱动与子进程已全部停止，JSONL 无损坏、无半条记录。开机后新会话**用原命令加 `--resume` 分别单独启动两 shard 即可续跑**，当前正在跑的 2 场（A/memory c6 Growth_hormone、C/memory c8 IFN_alpha_2a）无完成记录，重启后自动重跑。**memory 注入效果已显现且显著**（详见 §3）。

## 1. 已完成的实施（勿重做）

1. 预注册落文、驱动改造、双终点分析脚本、测试基线（649 passed, 1 skipped）、git 提交 `3a2cf63`、MODEL_API_USAGE.md 预登记 240 次——**全部已完成**，细节见 `HANDOFF_2026-08-05_E4FULL_RUNNING.md` §1，勿重做。
2. 运行期监控（多会话累计）：截至暂停 52 场完成，**全程无异常死亡、无重启、无 timeout/OOM 之外记录**；4 个预声明预期失败 cell（Zika_E_protein ×2、Factor_VIII ×2，均为 `evals=9, final_lambda=None`）已如期出现并记录。
3. **2026-08-06 03:30 UTC 停止操作**（本次会话执行）：`kill -TERM` 两驱动主进程（3977587、3995634）→ 清理 2 个孤儿子进程（A/memory c6、C/memory c8 的 form_chat.py）→ 已 `pgrep` 验证无残留 python 进程。**停止是安全的**：驱动 `load_done_keys` 只认 `success=True` 记录，JSONL append 发生在子进程完成后，SIGTERM 不产生半条记录；未完成 cell 由 `--resume` 重跑。

## 2. 当前进度（暂停时快照，勿误读）

- **shard A**（种子组 A+B，80 战役）：JSONL **25 行** = A/nomem 20 + A/memory 5。停止时正在跑：A/memory c6 Growth_hormone（无完成记录，重启重跑）。
- **shard B**（种子组 C，40 战役）：JSONL **27 行** = C/nomem 20 + C/memory 7。停止时正在跑：C/memory c8 IFN_alpha_2a（无完成记录，重启重跑）。
- 剩余：A/memory c6-c20（15 场）+ B 组全部（40 场）= 68 场。**种子组 B 尚未开始**（B 排在 A 组之后）。
- 记忆根 `workspace/e4_full/case_memory/{A,B,C}`：A 组 5 条、C 组 7 条（驱动每次启动按 JSONL 重建，`--resume` 幂等，勿手工改动）。

### memory 注入效果（暂停时实况，预注册假设的强证据）

| cell | evals | fired |
|---|---|---|
| A c1 Influenza_HA_H1N1 | 58 | 无（冷启动） |
| A c2 Insulin | 58 | bmc_max_rounds |
| A c3 Albumin | **13** | design_tool+λ, bmc_max_rounds |
| A c4 HIV-1_Env_gp120 | **13** | design_tool+λ, bmc_max_rounds |
| A c5 Ovalbumin | **13** | design_tool+λ, bmc_max_rounds |
| C c1 Albumin | 58 | 无（冷启动） |
| C c2 Beta_galactosidase | 58 | bmc_max_rounds |
| C c3 Transferrin | **1** | 三注入全触发 |
| C c4 IL-2 | **1** | 三注入全触发 |
| C c5 GFP | 7 | utr_mode, bmc_max_rounds |
| C c6 RSV_F_protein | **1** | 三注入全触发 |
| C c7 Influenza_HA_H1N1 | 7 | utr_mode, bmc_max_rounds |

- nomem 基线 eval_count 中位 58（C 组含 62）；memory 单场最低 **1**（−98%）。**预算节省分量（1−Σmem/Σnomem ≥25%）目前看大幅达标**。
- 注意：C c3/c4/c6 evals=1 意味着候选池极小——**设计收益终点（budget-matched 截断后 4 指标配对 Wilcoxon）是最大不确定性**，方向待分析阶段判定（4 指标任一过即可，容错仍大）。

## 3. 监控职责（续跑后每小时）

> 每小时 cron 为会话内有效（关闭即失效）——**新会话自行重设**：CronCreate `7 * * * *`，prompt 指向中段交接 `HANDOFF_2026-08-05_E4FULL_MIDRUN.md` §3 检查项；或手动按节拍查。

1. **每小时**：`pgrep -af run_e4_learning_curve | grep -v "bash -c" | grep python` 应见 2 个 python 进程 + `wc -l` 两 JSONL 得完成数（对照 `[n/80]`、`[n/40]` 当前战役）。
2. **可接受失败**（记录，**勿重启**）：子进程超时（`error == "timeout"`）/ LinearDesign OOM（driver.log 含 out-of-memory/bad_alloc，SIGKILL）；Zika_E_protein、Factor_VIII 属**预声明预期 cell**（evals=9/final_lambda=None 形态）。
3. **异常死亡先报告用户，勿自动重启**：进程数 ≠ 2、非 OOM 的 Traceback/Killed、驱动主进程意外退出。
4. **续跑**：同一命令加 `--resume` 幂等（done-key = (seed_group, arm, target_id) 且仅 success=True 记 done；JSONL 无重复完成键）。用户决定重启时用 §4 命令。
5. 进度汇报要点：两 shard JSONL 行数 / 当前战役 / 子进程活跃情况。

## 4. 续跑命令（开机后执行，两 shard 分别单独启动）

```bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system
T="A1AT,Albumin,Beta_galactosidase,EPO,Factor_VIII,GFP,Growth_hormone,HER2,HIV-1_Env_gp120,HPV16_L1,IFN_alpha_2a,IL-2,Influenza_HA_H1N1,Insulin,Luciferase,Ovalbumin,RSV_F_protein,SARS-CoV-2_Spike_WT,Transferrin,Zika_E_protein"
# shard A（先起；B 组 40 场在 A 组之后）
setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py --targets "$T" --seed-groups A,B --timeout 9000 --resume --output experiments/results/e4_full_shard_a.jsonl > experiments/results/e4_full_shard_a.log 2>&1 < /dev/null &
# shard B
setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py --targets "$T" --seed-groups C --timeout 9000 --resume --output experiments/results/e4_full_shard_b.jsonl > experiments/results/e4_full_shard_b.log 2>&1 < /dev/null &
```
（教训：同一条命令 `&` 串联两个 shard 时第二个可能因重定向竞态失败；**分别单独启动**，启动后 pgrep 数进程应见 2 个 python。日志是 append 模式续写，会与暂停前日志衔接。）

## 5. 跑完后的收尾（按序执行）

1. 确认两驱动进程退出、JSONL 记录齐全（120 = 80 + 40，全部 success 或预声明失败形态）。
2. **合并分析出判定书**：
   ```bash
   PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/e4_analysis.py
   ```
   输出 `experiments/results/e4_full_summary.json`（pass_criteria + endpoints + go_no_go）。双终点判定规则（预注册锁定）：
   - **效率终点**（两分量都需）：① memory 斜率显著为负（per 组 per 臂回归；3 组 memory 斜率单样本 t one-sided less p<0.05）② 预算节省 1−Σmem/Σnomem ≥25%（配对成功 cell；预声明失败 cell 排除）。
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
- 前序交接（决策背景/已拍板项/启动时状态/中段监控检查项）：`experiments/results/HANDOFF_2026-08-05_E4PREREGISTERED.md`、`HANDOFF_2026-08-05_E4FULL_RUNNING.md`、`HANDOFF_2026-08-05_E4FULL_MIDRUN.md`。
- 试点判定书（管线验证件）：`experiments/results/e4_pilot_summary.json`（overall_pass=True）。
- 耗时参考：`HANDOFF_2026-08-05_E4PREREGISTERED.md` §4（per 靶点中位耗时）；暂停前实测 A/C 组 memory 臂约 1-30min/场（注入后显著加速），nomem 中位 ~23min/场、最长 5918s。
- 服务由 `ensure_services_ready` 自动拉起（勿手动启动）；本实验仅 2 分片，无竞争超时风险。
- E4 设计：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4 + §5 里程碑。
