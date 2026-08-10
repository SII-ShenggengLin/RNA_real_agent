# 交接提示词（2026-08-07 03:39 UTC：E4 收尾完成，E5 预注册草案就绪待用户审；无实验在跑，新会话从 E5 草案评审开始）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E4FULL_FINAL_RERUN.md`（E4 收尾）→ **本文件（E4 终局 + E5 起点）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`；**注意：Bash 工具工作目录跨调用持久——启动后台任务时须在同一条命令内 `cd rna_agent_system &&`，git 命令建议带 `-C <项目根>` 或先 cd 回项目根，本会话曾因此查错路径**）。

## 0. 一句话现状

**E4 全矩阵已彻底收尾（NO-GO 判定书已出、MODEL_API_USAGE.md 已更新实测）；用户已拍板放弃 E4 记忆策略方向，E5（约束导向的批量交付 + 排序）预注册草案已写好，等用户审 7 个未决问题；当前无任何实验在跑（已 pgrep 核实，仅常驻微服务），无需监控、无需续跑——下一步是等用户审 E5 草案。**

## 1. 本会话已完成（勿重做）

1. **E4 收尾全流程**（交接文档 `HANDOFF_2026-08-07_E4FULL_FINAL_RERUN.md` §3 按序走完）：
   - HPV16_L1 重跑确认成功（JSONL 第 83 行 `e4_B_memory_c1_HPV16_L1 success=True`；日志 `Done: 1 ok, 0 failed, 3 skipped`）→ 120 cell 全有记录（115 success + 5 预声明失败）。
   - `e4_analysis.py` 合并分析 → 判定书 `experiments/results/e4_full_summary.json` 已生成。
   - 已向用户报告双终点：**NO-GO**（详见 §2）。
   - `MODEL_API_USAGE.md` 已更新：E4 行预登记 240 → **实测 230 次**（A+B shard 154 + C shard 76；按 JSONL `quality_actions` 统计），页眉日期已改 2026-08-07。
2. **用户战略决策（2026-08-07）**：
   - E4 记忆策略放弃；**E3 门控结果可继续用**（FP 相对降 100%、TP 保留 112.5%、越权 0，作组件级证据引用，数据不复用——E5 场景不同）。
   - 不做 benchmark 类论文；**四个指标（CAI/全长 MFE/接头 mfe/nt/GemORNA MRL）被 λ 锁定或无规律，无法通过 agent 架构改进**——agent 优越性改从工具射程外寻找：约束满足/冲突仲裁/批量交付/排序。
   - 目标场景：全长 mRNA 批量交付 **~5 个排序候选**；暂不考虑 wet-lab；**大规模试验前必须小规模全面验证，判据从最早阶段全量生效**（E4 教训：全量 120 场跑完才发现问题，不再重演）。
3. **E5 预注册草案已写**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`（**未定稿、未实施、未跑任何代码**）。内容：任务规格（5 候选 + 排序 + 决策档案）、约束矩阵（C1–C6+M1 pass/fail + 档案记录指标 §4.2）、排序质量四代理（R1 一致性 ρ=1.0 / R2 稳定性 τ≥0.8 / R3 敏感性 / R4 最优性）、多样性（D1/D2）、三臂对照（A λ 网格 {0,1,4,10} 直跑 / B 无门控 LLM agent / C 门控+约束导航）、S0/S1/S2 分阶段关卡、GO/NO-GO 规则（§10）、明确排除四指标（§12）、**7 个未决问题（§13）待用户拍板**。

## 2. E4 判定书要点（报告已给用户，此处备查）

- **NO-GO**（预注册规则：任一终点过 → GO；双终点均不过 → NO-GO）。
- 效率终点 ✗：预算节省 74.2%（814 vs 3153）✓ 大幅过；memory 斜率分量 ✗（3 组斜率全正 +1.2e-4/+2.4e-5/+2.4e-4，单样本 t 单侧 p=0.91；eval 从首 2 战役 58 骤降至 c3 起恒定 13——水平削减非递减曲线）。
- 设计收益终点 ✗：4 指标 q 全 ≥0.37、|δ| 全 ≤0.17，无一过。
- 判据 c1/c4 未过 = **分类缺口**（5 个预声明失败 cell：3×Zika + 2×Factor_VIII memory 臂 cli_failure，未打 acceptable 标——驱动 `is_acceptable_failure` 只认 timeout/OOM，分析侧无预声明名单）；**不影响 GO/NO-GO**（终点 n_pairs=55 已排除）。修复方案（分析侧加名单）待用户决定是否需要。
- 试点从未实测过终点（`declared, not implemented (pilot)`）——全矩阵是双终点首次实测，非与试点矛盾。

## 3. 当前状态

- **无实验在跑**（pgrep 核实：无实验驱动进程；仅常驻微服务 uvicorn 8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py，勿动，由 `ensure_services_ready` 自动拉起）。
- **git**：`.gitignore` 第 24 行忽略整个 `rna_agent_system/experiments/results/`——E5 草案、E4 判定书、MODEL_API_USAGE.md、全部 HANDOFF 均未跟踪。本会话无代码文件改动。仓库根有历史遗留的 M/D（AGENTS.md、agent_core/ 等，会话开始前即存在），是否提交由用户定。

## 4. 下一步（新会话按序，用户拍板前不要动 E5 草案）

1. **等用户审 E5 草案**（用户已收到草案 + 7 个未决问题）。核心待拍板项：①约束清单与阈值（尤其 C5 剪接位点规则是否够格）②S1 规模（草案建议 5 靶点）③画像 3 类与权重 ④GO/NO-GO 规则（任一终点过 → GO）。
2. **用户拍板后**（沿 E4 先例实施）：
   a. 定稿草案（全文移植到驱动 docstring）；
   b. **先查 B 臂可行性**：无门控 LLM agent 路径（旧栈自由规划风格，E3 ungated 同构）当前代码是否仍可用——E4/E3 之后旧栈有大量删除（`planning/router.py`、`llm_critic.py` 等已删），不可用则需设计等价替代并报告用户；
   c. 实施 **S0 机制验证**（1 靶点 × C 臂 × 3 重复，判据：约束识别 100% / 输出格式完整 / R2 稳定性 τ≥0.8 / 无崩溃）→ 出阶段判定书 → 用户确认；
   d. **S1 小规模**（5 靶点 × 3 臂，判据与 S2 同指标同阈值：端到端通过率 C≥0.8 且 C≥A+0.4 / 约束满足率 C≥0.9 / R1–R4 与 D1–D2 全过 / 方向性 ≥4/5）→ **任一不过 → 报告用户，不自动进 S2**；
   e. **S2 全矩阵**（20 靶点，配对 McNemar p<0.05 或 95%CI 不含 0）→ 最终判定书 GO/NO-GO；
   f. S1/S2 启动前在 `MODEL_API_USAGE.md` 预登记 E5 LLM 调用（草案 §11：C 臂每基因 3–5 次，B 臂 2–4 次），跑完当天更新实测。
3. **E5 草案判据不过时的备选动作**（草案 §9）：修机制 / 调整约束阈值 / 放弃——由用户定，勿自作主张。

## 5. 工程纪律（用户既定规则，必须遵守）

1. **git 操作必须先问用户**（commit/push/reset）。
2. **pytest 基线 649 passed, 1 skipped**；改代码后必跑全量 `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -q`（约 25s）。
3. 简洁优先；锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项若需改动，先呈用户**（E5 草案即预注册草案，未拍板前一字不改）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程；**命令须同条内 cd rna_agent_system &&，前台检查用绝对路径**。
7. 决策文化：重大路线由用户决定，助手给建议与证据；论文 Nat Methods 直冲，不做提前预注册公开。

## 6. 关键指针

- **E5 草案**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`（7 个未决问题在 §13）。
- E4 判定书：`experiments/results/e4_full_summary.json`；E4 收尾交接：`experiments/results/HANDOFF_2026-08-07_E4FULL_FINAL_RERUN.md`。
- E3 预注册：`experiments/run_e3_gated_vs_ungated.py` docstring；E3 判定书：`experiments/results/e3_runs_full_summary.json`。
- 全长 mRNA 工作流能力：`agent_core/workflows/full_length_mrna_design.py`（GEMORNA 5'UTR MRL/3'UTR 稳定性、LinearDesign λ 0–20、Junction/GC/二级结构评估器——零新模型）。
- 20 靶点：`data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/`；运维耗时表：E4 交接 `HANDOFF_2026-08-05_E4PREREGISTERED.md` §4。
- E4 教训与分阶段关卡设计：E5 草案 §9（S0 判据全量生效、S1 = S2 最小功效版、禁止中途新增终点）。
