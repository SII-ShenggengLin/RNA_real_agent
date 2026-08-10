# 交接提示词（2026-08-07 晚：最终拍板落定 + 驱动已改已测 + Insulin 重放通过，S0 待重跑）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E5_SURVEY_DONE_REPLAY_READY_WAIT_PINBOARD.md`（扫描完成、等拍板）→ **本文件（用户最终拍板、实施完成、S0 待重跑）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令带绝对路径或同条命令内 `cd`，Bash cwd 每次调用可能重置，勿依赖持久）。

## 0. 一句话现状

**用户已最终拍板（2026-08-07）：约束矩阵 9→5 条（C1/C2/C6/C7/M1）；C2 6→14（Twist 硬线）、C3/C4 降软约束、C6 10→12；>1300aa 靶点全实验排除（Factor_VIII 2352/Zika 3420，分母 20→18）；HER2(1255)/Spike(1273) 保留（Spike 新方案 9/36 可过，HER2 0/36 约束层结构性不可行、如实报告）。驱动已改并通过 pytest 全量（649 passed, 1 skipped）；Insulin 池重放 ×2 通过（12/36 = 离线矩阵预测值，确定性 ✓）；PREREG 已同步（§15 注记）；MODEL_API_USAGE 已更新。下一步：重跑 S0（约 25–35min）→ 呈判定书 → 用户确认 → S1 → S2。无运行中后台实验。所有修改未 commit。**

## 1. 本会话已完成（勿重做，均在磁盘）

### 1.1 检索结论：LinearDesign 无 DFA 生成约束实现（用户条件决策的依据）
- 官方开源：LinearDesignSoftware/LinearDesign（Nature 2023，DOI 10.1038/s41586-023-06127-z；Zenodo v1.0.0）。**无 "LinearDesign2"**（多次检索零结果；同组后续 EnsembleDesign（ISMB 2025/Bioinformatics）是 ensemble free energy 设计，非 LinearDesign2，也无约束输入）。
- 论文 Methods（"DFAs for other genetic codes, coding constraints and modified nucleotides"）**理论上**支持 coding constraints（Extended Data Fig.3c 相邻密码子对 / Supplementary Fig.5 限制酶位点），但：
  - GitHub README 仅 `--lambda`/`--codonusage`/`--verbose` 三个选项，无约束参数；
  - 本地源码 `external_repos/LinearDesign/src/linear_design.cpp` argc ∈ {4,5,7,8}（λ/verbose/codon 表/本项目 junction 补丁），grep restrict/constraint/homopolymer/motif 零命中；
  - 微服务 8014（lineardesign_service）无约束通道。
- → 用户条件指令走**放宽分支**：C2=14、C3 软、C6 放宽。

### 1.2 用户最终拍板（2026-08-07，与 §0 同）
| 项 | 原 | 新 | 依据 |
|---|---|---|---|
| C2 同聚物 | <6 | **<14**（允许 ≤13nt，≥14 判失败） | Twist 合成硬线 ≥14bp；找不到 DFA 分支 |
| C3 polyA | 硬 | **软**（`C3_polya_signal_count` 档案） | 找不到 DFA，无法生成时规避 |
| C4 酶切位点 | 硬 | **软**（`C4_restriction_hits` 档案） | 体外转录无克隆阶段 |
| C6 起始区茎 | ≤10 | **≤12** | 找不到 DFA，放宽 |
| 长度阈值 | — | **>1300aa 排除**（Factor_VIII/Zika） | 用户拍板，全实验过滤 |
| HER2/Spike | — | **保留**（Spike 9/36；HER2 0/36 如实报告） | 用户拍板 |
| 矩阵条数 | 9 条 | **5 条**（C1/C2/C6/C7/M1） | C3+C4 软化（C5/C8 已软） |

### 1.3 驱动修改（`experiments/run_e5_constraint_nav.py`，未 commit）
- `FULL_TARGETS` 20→18（移除 Factor_VIII、Zika_E_protein，含注记）；`CONSTRAINT_IDS` = ["C1","C2","C6","C7","M1"]；`HOMOPOLYMER_MIN` 6→14；`START_REGION_MAX_STEM` 10→12。
- C3/C4 判定移出 `constraints` dict，新增软约束档案：`polya_signal_count()`/`restriction_site_hits()`，archive 加 `C3_polya_signal_count`/`C4_restriction_hits`（build_pool 与 `_evaluate_candidate_in_pool` 两处）。
- 文档字符串/表头（§4 矩阵、§7.1、R4、候选表头 C1C2C6C7M1）同步。
- **pytest 全量：649 passed, 1 skipped ✓**（22s，与基线一致）。

### 1.4 Insulin 池重放 ×2（`/tmp/e5_pool_replay.py`，已完成）
- `pass all 5: 12/36`（run1=run2）——**与离线重放矩阵预测（Insulin 12/36）完全一致**；确定性 ✓（seq_fp=a94bf3275526 两次相同）。
- 脚本末尾 `REPLAY_RESULT: CHECK_NEEDED` 是旧脚本写死的 ≥18 阈值，**实际 12/36 正确，勿当失败、勿改判定**。

### 1.5 文档同步（均未 commit）
- `PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`：头部 v3.1 注记、§4 注记 + 现行 5 条矩阵表、§7.1 分母 9→5、§9 S2 18 靶、§11、§13-1、§14 后新增 **§15 实施修正注记汇总**（15.1 检索依据 / 15.2 靶点过滤与 HER2 文档化 / 15.3 重放数字 / 15.4 对 §11/§14 连带影响）。只增注记，原拍板文本保留。
- `MODEL_API_USAGE.md` §2 E5 行：实测更新（池级扫描 2026-08-07：LinearDesign 80 次 + GEMORNA 120 次 + LinearFold 本地；S2 预登记 20→18 基因，~126–234 次 LLM）。

### 1.6 关键重放数字（`/tmp/e5_replay_v2.py` 可重跑，纯离线 ~3s；`/tmp/e5_survey_replay.py` 是旧版 D 案脚本）
| 方案 | pass≥5 | λ≥2 |
|---|---|---|
| 现状（C2<6+C4硬+C6≤10+C3硬） | 5/20 | 4/20 |
| D 案（C2<8+C4软+C6≤12+C3硬） | 16/20 | 12/20 |
| **最终（C2<14+C4软+C6≤12+C3软）** | **17/20 = 17/18 可行靶** | 14/20 |
- 每靶点（最终案）：EPO 33、GFP 30、Albumin 27、Luciferase 27、Growth_hormone 27、IL-2 24、A1AT 18、IFN 18、Influenza 18、Ovalbumin 18、HIV-1 18、HPV16 15、Insulin 12、Beta_gal 9、RSV 9、**Spike 9**、Transferrin 6、**HER2 0**。
- 18 可行靶仅 HER2 不可救（C1 84% GC ∩ C7 41–43bp 茎，与阈值无关）。

## 2. 正在运行/可监控的后台任务

- **无运行中后台实验**（Insulin 重放已完成；上一会话的 until 循环随会话关闭消失）。
- 微服务 8004（GEMORNA）/8014（LinearDesign）/8015（LinearFold）仍在跑（实验拉起的，勿杀，驱动会幂等自启）。

## 3. 未完成——下一会话下一步（严格按序）

1. **重跑 S0**（判据 §9：①约束识别 100% ②输出格式完整（每画像 5 候选+排序+档案）③R2 τ≥0.8 ④无崩溃 ⑤≤40min，**不含池通过率**）：
   ```
   echo "=== rerun after final pin $(date) ===" >> experiments/results/e5_s0.log
   cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent && setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s0 --targets Insulin --repeat 3 --resume >> experiments/results/e5_s0.log 2>&1 &
   pgrep -af run_e5_constraint_nav   # 确认进程数
   ```
   然后挂 until 循环等 `e5_verdict_s0.json`（用 Bash run_in_background 的 until 循环；判据含 R2 τ≥0.8，S0 无成功记录，`--resume` 等价全新跑）。
2. **呈 S0 判定书**（对照 §9 判据逐项）→ **用户确认后**才进 S1。
3. **S1**：5 靶点 A1AT, Insulin, EPO, GFP, IL-2 × 3 臂（~1.5–2h；setsid nohup + 日志落盘 + pgrep 确认 + until 等完成）。判据：通过率 C≥0.8 且 C≥A+0.4 / 约束满足率 C≥0.9 / R1–R4 全过 / D1–D3 全过 / 方向性 C≥A 至少 4/5。全过才进 S2；任一不过 → 报告用户。
4. **S2**：18 靶点（FULL_TARGETS 已过滤 Factor_VIII/Zika），2 分片串行（~4–5h；服务串行处理请求，勿超 2 分片并发）。判据：配对 McNemar p<0.05（C vs A 且 C vs B）/ R1–R4、D1–D3 全过 / 约束满足率 C≥0.9。HER2 预期 0 分如实报告。
5. 每阶段完成当天更新 `MODEL_API_USAGE.md` 实测行（S0/S1/S2 的 LLM 调用数）。
6. **git 操作必须先问用户**（当前 `experiments/run_e5_constraint_nav.py`、PREREG、MODEL_API_USAGE.md 均未 commit）。

## 4. 关键状态与指针

- **未 commit**：`experiments/run_e5_constraint_nav.py`、`PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`、`MODEL_API_USAGE.md`（git 必须先问用户）。
- **未产出**：`e5_verdict_s0.json`、`e5_s0_runs.jsonl`（S0 无成功记录，`--resume` 等价全新跑）。
- **缓存**：`experiments/results/e5_gemorna_cache.json`（18 条靶点扫描缓存；**Insulin/A1AT/EPO 无缓存**，S0 用 Insulin 会重新生成 UTR）。
- **脚本**：`/tmp/e5_survey_replay.py`（旧 D 案重放）、`/tmp/e5_replay_v2.py`（**最终案重放，本会话新建**）、`/tmp/e5_pool_replay.py`（Insulin 重放，已跑过可重跑）、`/tmp/e5_selftest.py`（已过）。注意 /tmp 可能被清理，若丢失可从 `e5_pool_survey.json` 直接离线重算（脚本逻辑见 §1.6 数字）。
- **数据**：`experiments/results/e5_pool_survey.json`（18 靶，每候选含 constraints 快照/max_hp_run/restriction_hits/c6_win_stem/c7_full_stem/gc_min/max/序列）。
- **文献**：`relevant_references/` + WebSearch 依据（§1.1）；`/tmp/ld_paper.txt`（LinearDesign 论文全文文本，DFA 相关在 Methods 2147–2159 行）。
- **PREREG**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`（§15 = 本次拍板注记汇总；判据原文在 §7–§10）。

## 5. 工程纪律（用户既定规则）

1. git 操作必须先问用户（commit/push/reset）。
2. pytest 基线 649 passed, 1 skipped；改代码后必跑全量（约 25s）。
3. 简洁优先；锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项改动必须先呈用户**（本次 C2/C3/C4/C6 拍板与 1300aa 过滤已完成；后续任何约束/阈值改动需重新呈用户）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程；命令用绝对路径或同条内 cd（Bash cwd 每次调用可能重置）。
7. 决策文化：重大路线由用户决定，助手给建议与证据；论文 Nat Methods 直冲，不做提前预注册公开。
8. 微服务 8004/8014/8015 为实验拉起的勿杀。
9. S0/S1/S2 每阶段结束出判定书（JSON），未过不进下一阶段；阶段判据禁止中途新增终点。
