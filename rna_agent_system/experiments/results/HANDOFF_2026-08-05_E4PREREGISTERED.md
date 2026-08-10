# 交接提示词（2026-08-05：E4 试点 GO + 修复完成，全矩阵已拍板待实施启动）

> **用法**：新会话先读本文件。上一份交接：`HANDOFF_2026-08-05_E4PILOT_RUNNING.md`（试点运行期监控职责已终结——试点 2026-08-05 10:41 UTC 正常收尾，12/12）。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。
> 本会话退出时**无任何实验在跑**（已核实：无实验驱动进程，仅常驻微服务）。

## 0. 一句话现状

**E4 试点 GO（6/6 管道判据全绿），final λ 重构偏差已修复（代码+记录纠正+判定书重生成+pytest 627），全矩阵预注册 4 项全部拍板（本文件 §2）——下一步：实施全矩阵预注册并启动 120 战役**（约 1 周墙钟，详见 §3）。

## 1. 试点收官（已完成，勿重做）

- 判定书 `experiments/results/e4_pilot_summary.json`：**overall_pass=True**；6 条判据（①12 场完成 ②注入点火 2/4 ③评估量归约 0 偏差 ④预算截断 6/6 cell 等臂 ⑤resume 幂等 ⑥字段完整）全绿。
- 描述性要点（全矩阵排期用）：单场 321–974s；注入战役评估量 58→13（−78%）；memory 臂总墙钟比 nomem 省 ~21%；预算匹配后 best-of-pool ASF 方向混杂（A 组 memory 全胜、B 组 nomem 全胜）——**试点期不做效应量断言**，这正是全矩阵 120 场要回答的。
- 产物：`e4_pilot_runs.jsonl`（12 条）、session `workspace/sessions/e4_*`、记忆根 `workspace/e4_pilot/case_memory/{A,B}`（试点专用，全矩阵不复用）。

## 2. 已拍板的决策（2026-08-05，用户拍板或委托）

1. **矩阵规模：120 保留**（20 靶点 × 2 臂 × 3 种子组）。理由（已向用户呈报）：全 BioBench 套件 = 自然总体；减种子组（3→2）把主终点斜率配对 n 从 3 降到 2（df=1，统计上近轶事）；减靶点伤次终点 n 且砍掉的恰是 HER2/Spike 这类最有学习曲线故事的重靶；砍 λ 网格/工具数破坏「nomem = Fig 3 逐位相同」对照锚点。
2. **默认 bmc_max_rounds = 2**（用户委托决定，本会话已定）。依据（Fig 3 实测 264 runs）：
   - Fig 3 的 `bmc_max_rounds` 本身是消融维度（0/1/2/3 各 ~65 次），但 `bmc_rounds_executed` 实测 **113+123 次为 0–1 轮、仅 4 次到 2 轮**——BMC 早停收敛，max 给到 3 也不增成本；
   - 默认 1 时旋钮 3 结构性 no-op（预注册 flag 已注明）；默认 2 后，相似战役执行轮数中位（实测 ≈1）→ 注入 1 ≠ 默认 2 → **旋钮 3 点火（向下修剪预算，恰是效率故事的方向）**；
   - 成本影响 ≈ 0（早停主导）。实施：驱动 `DEFAULT_BMC_MAX_ROUNDS = 1 → 2`，钳位 `[1, 2]`。
3. **全矩阵用全新记忆根**（用户批准）：`workspace/e4_full/case_memory/{A,B,C}`；试点根仅作验证件保留。
4. **λ 跨度阈值 6 与双终点阈值按试点原样锁定**（用户批准）：效率终点——记忆臂学习曲线回归斜率显著为负且 20 靶点累计预算节省 ≥25%；设计收益终点——预算匹配截断后已验证指标（CAI、MFE、接头 mfe/nt、GemORNA MRL，禁用未画像 oracle）配对 Wilcoxon 显著且 Cliff's δ ≥ 0.3。任一终点过 → GO。

## 3. 下一步：全矩阵实施清单（按序执行）

1. **全矩阵预注册落文**（给用户过目后实施）：更新 `experiments/run_e4_learning_curve.py` 的 docstring 预注册全文（矩阵=120、bmc_max_rounds=2、新记忆根、20 靶点、Zika/Factor_VIII 预声明为预期失败 cell——LinearDesign 对 ~7kb+ CDS OOM（SIGKILL），Fig 2 空跑已确诊，属可接受失败模式；JSONL 分析注意：同一 task 可能多条记录取最新）。
2. **驱动改造**（试点驱动已继承 Fig 3 的 resume/done-key 模式，增量改）：
   - `DEFAULT_BMC_MAX_ROUNDS = 2`、`SEED_GROUPS = {"A":0,"B":1,"C":2}`、`CASE_MEMORY_ROOT = workspace/e4_full/case_memory`；
   - 靶点清单 = `data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/` 全部 20 个（A1AT, Albumin, Beta_galactosidase, EPO, Factor_VIII, GFP, Growth_hormone, HER2, HIV-1_Env_gp120, HPV16_L1, IFN_alpha_2a, IL-2, Influenza_HA_H1N1, Insulin, Luciferase, Ovalbumin, RSV_F_protein, SARS-CoV-2_Spike_WT, Transferrin, Zika_E_protein）；
   - 新增 `--seed-groups A,B` 分片参数（种子组内记忆顺序语义不可跨分片切分）；输出 `e4_full_shard_a.jsonl` / `e4_full_shard_b.jsonl`（照抄 Fig 3 双 shard 各写一 JSONL）；
   - **分片方案**：shard A = 种子组 A+B（80 战役），shard B = 种子组 C（40 战役）；内存并发 ≤2（cgroup 200GiB，HER2 单进程 RSS 数十 GiB），两 shard 同时后台运行即可。
3. **双终点统计接口**（`experiments/analysis/e4_analysis.py`，试点留桩未实现）：回归斜率用 numpy 一元回归（ASF vs 累计评估量，per 种子组 per 臂 → 组内配对比）；Wilcoxon/Cliff's δ 用 `experiments/analysis/stats_utils.py`（已有 wilcoxon_paired / cliffs_delta / bh_fdr）。
4. **测试 + 基线**：扩展 `tests/test_e4_pilot.py`（新常量/新种子组/钳位逻辑），全量 `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x` 基线 **627 passed, 1 skipped**（改动后 ≥627）。
5. **启动**（两 shard，先给用户过目预注册与启动命令）：
   ```bash
   cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system
   setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py \
     --targets A1AT,Albumin,...,Zika_E_protein --seed-groups A,B --timeout 9000 --resume \
     --output experiments/results/e4_full_shard_a.jsonl > experiments/results/e4_full_shard_a.log 2>&1 &
   setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py \
     --targets A1AT,Albumin,...,Zika_E_protein --seed-groups C --timeout 9000 --resume \
     --output experiments/results/e4_full_shard_b.jsonl > experiments/results/e4_full_shard_b.log 2>&1 &
   ```
   启动后必须 `pgrep -af run_e4_learning_curve` 数进程确认双实例（坑 16）。
6. **监控**：每小时查两 shard 日志进度；`--timeout 9000` 全覆盖（HER2 在负载下 ~87 分钟，Fig 3 实测）；可接受失败 = 子进程超时 / LinearDesign OOM bad_alloc（勿重启，先报告用户；续跑同一命令 `--resume` 幂等）。跑完 → 合并分析出判定书 → 向用户报告双终点 GO/NO-GO。
7. **当天纪律**：启动时在 `experiments/results/MODEL_API_USAGE.md` 预登记 E4 全矩阵行（120 战役 × 2 轮诊断 = **240 次** QualityAgent deepseek-v4-pro 调用，试点实测 24 次/12 战役）；跑完当天更新实测。

## 4. 运维参考（Fig 3 实测，264 runs）

per 靶点中位耗时（nomem 全网格 = Fig 3 同配置；注入后 ~20%）：HER2 6737s、SARS-CoV-2_Spike_WT 5795s、Beta_galactosidase 4407s、HIV-1_Env_gp120 4051s、Albumin 2500s、Transferrin 2426s、Influenza_HA_H1N1 2156s、RSV_F_protein 2059s、Luciferase 2034s、HPV16_L1 1868s、Ovalbumin 1687s、Factor_VIII 1650s、A1AT 1615s、Growth_hormone 1603s、GFP 1571s、EPO 1416s、IFN_alpha_2a 1202s、IL-2 1154s、Insulin 1108s、Zika_E_protein 1069s。合计 ~14.2h/单臂全靶；120 场 ≈ 62–85 CPU·h → 双分片约 **2–3 天纯计算，~1 周墙钟**（含续跑/瞬时失败；设计文档「约 2 周」为早期保守估计，本数据为准）。服务串行处理请求（ensure_services_ready 自动拉起，勿手动启动）；4 分片并发会造成竞争超时——本实验仅 2 分片，安全。

## 5. 待办记录（本会话未做，勿漏）

- 未提交 git：① `run_e4_learning_curve.py` final λ 修复（`extract_campaign_outcome` 传 `start_lambda`）；② `e4_pilot_runs.jsonl` 2 条记录 final_lambda 4.0→2.0（A/B memory c3，注入战役）+ `case_memory/{A,B}` 重建；③ `e4_pilot_summary.json` 重生成；④ `MODEL_API_USAGE.md` E4 行（预登记 12→实测 24 次）。**git 操作必须先问用户**。

## 6. 工程纪律（用户既定规则，必须遵守）

1. **git 操作必须先问用户**（任何 commit/push/reset）。
2. **pytest 基线 627 passed, 1 skipped**；改代码后必跑全量。
3. **简洁优先**：不留兼容包袱；锁定接口走 `docs/INTERFACE_LOCKS.md` 流程（只增不改）。
4. **试点先行**：新实验方案先小规模预注册试点再大规模验证（本次全矩阵即试点 GO 后的正式执行）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程（单/双实例）。
7. 锁的 CLI 回归：`run_pa_test.py <006..024>`（基准 `pa_benchmarks.json`）。
8. 决策文化：重大路线选择（预注册阈值、终点定义、方案拍板）由用户决定；助手给建议与证据。**预注册项若需改动，先呈用户**（本次已拍板项见 §2，不要自行再改）。
9. 论文目标 Nat Methods 直冲，**不做提前预注册公开**。
10. 项目文档索引见根 `AGENTS.md`；新 agent 应先读 `docs/ARCHITECTURE.md` 与 `docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md`。

## 7. 关键指针

- E4 设计：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4 + §5 里程碑（W10–13）。
- 试点：驱动 `experiments/run_e4_learning_curve.py`（docstring = 试点预注册全文；全矩阵预注册将更新之）、判定书 `e4_pilot_summary.json`、日志 `e4_pilot_driver.log`。
- 分析桩：`experiments/analysis/e4_analysis.py`（双终点未实现）、`experiments/analysis/stats_utils.py`（Wilcoxon/Cliff's δ/BH-FDR 已有）。
- Fig 3 耗时/运维：`fig3_type1_shard_a/b.jsonl`、`RESUME_CHECKPOINT.md`（§2 续跑模式、§4 边界）。
- 前序决策：`HANDOFF_2026-08-05_E4PILOT_RUNNING.md`、`HANDOFF_2026-08-04_P2NOGO_E4DECISION.md`。
- 试点判定书修正记录：本文件 §1、§5（final λ 4.0→2.0，注入战役，输入 λ=0.0 + trace δ=+2.0）。
