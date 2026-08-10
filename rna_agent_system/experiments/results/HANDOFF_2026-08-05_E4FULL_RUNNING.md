# 交接提示词（2026-08-05：E4 全矩阵 120 战役运行中，新会话接管监控）

> **用法**：新会话先读本文件。上一份交接：`HANDOFF_2026-08-05_E4PREREGISTERED.md`（全矩阵预注册实施已由上一会话完成——本文件是其实施后的运行期交接）。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。
> 写本文件时（2026-08-05 14:35 UTC）：**E4 全矩阵双分片正在运行**（详见 §2）。

## 0. 一句话现状

**E4 全矩阵（120 战役）已于 2026-08-05 14:2x UTC 启动，双分片运行中**（shard A = 种子组 A+B / 80 战役，shard B = 种子组 C / 40 战役）。预注册已落文、驱动/分析/测试已完成并提交 git（`3a2cf63`）、MODEL_API_USAGE.md 已预登记 240 次。新会话职责：**每小时监控 → 跑完合并分析出判定书 → 报告双终点 GO/NO-GO**。

## 1. 已完成的实施（勿重做）

1. **预注册落文**：`experiments/run_e4_learning_curve.py` docstring = 全矩阵预注册全文（矩阵 120、bmc_max_rounds=2、新记忆根 `workspace/e4_full/case_memory/{A,B,C}`、20 靶点、Zika_E_protein/Factor_VIII 预声明预期失败 cell、双终点阈值锁定、分片方案、JSONL 取最新记录注意事项）。
2. **驱动改造**：`DEFAULT_BMC_MAX_ROUNDS=2`、`SEED_GROUPS={"A":0,"B":1,"C":2}`、`FULL_TARGETS` 20 个、新增 `--seed-groups` 分片参数、移除 `--pilot`、`candidate_index` 扩展 4 个已验证指标（cds_cai/full_length_mfe/junction_mfe_per_nt 均值/utr5_predicted_mrl）。
3. **双终点分析接口**：`experiments/analysis/e4_analysis.py` 已实现（效率终点：per 组 per 臂 numpy 回归斜率 + 单样本 t 检验 + 预算节省；设计收益终点：4 指标配对 Wilcoxon + BH-FDR + Cliff's δ；`go_no_go` 判定；`--runs` 逗号分隔合并两 shard）。
4. **测试基线**：`649 passed, 1 skipped`（原 627 + 22 新增；`tests/test_e4_pilot.py` 扩展 + 新 `tests/test_e4_analysis.py`）。
5. **git**：4 个代码文件已提交 `3a2cf63`（用户批准）。`experiments/results/` 目录被 .gitignore 忽略（实验产物不入库），`workspace/` 同理。
6. **MODEL_API_USAGE.md**：已预登记 E4 全矩阵行（120 战役 × 2 轮诊断 = **240 次** QualityAgent deepseek-v4-pro 调用；跑完当天更新实测）。

## 2. 当前运行中的实验（勿动，监控即可）

- **shard A**：PID `3977587`，`--seed-groups A,B`（80 战役），输出 `experiments/results/e4_full_shard_a.jsonl`，日志 `experiments/results/e4_full_shard_a.log`。
- **shard B**：PID `3995634`，`--seed-groups C`（40 战役），输出 `experiments/results/e4_full_shard_b.jsonl`，日志 `experiments/results/e4_full_shard_b.log`。
- 两实例均 `--timeout 9000 --resume`，启动命令见 `run_e4_learning_curve.py` docstring Usage（或上一交接 §3.5）。
- 写本文件时：双方均在首场战役（A/nomem Influenza_HA_H1N1；C/nomem Albumin），JSONL 尚无记录（正常，单场 300–974s）。
- 记忆根 `workspace/e4_full/case_memory/{A,B,C}` 已建（内容随首个成功 memory 战役写入）。

## 3. 监控职责（每小时）

> 上一会话设的每小时 cron 是会话内有效的（关闭即失效）——新会话**自行重设每小时监控**（CronCreate `7 * * * *`，prompt 指向本文件 §3 检查项）或手动按节拍查日志。

1. **每小时查两 shard 日志尾部** + `pgrep -af run_e4_learning_curve | grep -v "bash -c"` 确认 2 个 python 进程。
2. **可接受失败**（记录，**勿重启**）：子进程超时（`error == "timeout"`）/ LinearDesign OOM（driver.log 含 out-of-memory/bad_alloc，SIGKILL）；Zika_E_protein、Factor_VIII 的 OOM 属**预声明预期 cell**，直接记录即可。
3. **异常死亡先报告用户，勿自动重启**：进程数 ≠ 2、日志出现非 OOM 的 Traceback/Killed、或驱动主进程意外退出。
4. **续跑**：同一命令加 `--resume` 幂等（done-key = (seed_group, arm, target_id)；JSONL 无重复完成键）。用户决定重启时用 §4 命令。
5. 进度汇报要点：`grep -c "OK in"` 两日志得完成数 / `[n/80]`、`[n/40]` 当前战役。

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

1. 确认两驱动进程退出、JSONL 各战役记录齐全（120 = 80 + 40）。
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
5. git 提交询问用户（4 个代码文件已提交；判定书/JSONL 在 ignored 目录）。

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
- 上一交接（决策背景/已拍板项）：`experiments/results/HANDOFF_2026-08-05_E4PREREGISTERED.md`。
- 试点判定书（管线验证件）：`experiments/results/e4_pilot_summary.json`（overall_pass=True）。
- 耗时参考：`HANDOFF_2026-08-05_E4PREREGISTERED.md` §4（per 靶点中位耗时；合计 ~14.2h/单臂全靶；双分片约 2–3 天纯计算、~1 周墙钟含续跑）。
- 服务由 `ensure_services_ready` 自动拉起（勿手动启动）；本实验仅 2 分片，无竞争超时风险。
- E4 设计：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4 + §5 里程碑。
