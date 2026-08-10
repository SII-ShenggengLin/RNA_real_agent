# 交接提示词（2026-08-04 深夜收尾：E3 GO + P2 NO-GO，E4 执行器待用户拍板）

> 用法：新会话先读本文件；工程纪律沿用 `HANDOFF_2026-08-04_W34_CLOSEOUT.md` §3 与 `HANDOFF_2026-08-04_W59_COMPONENTS_E3PILOT.md` §4（含坑 16：后台启动后必须 pgrep 数进程）。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（命令统一带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。

## 0. 一句话现状

**无在跑实验、无在跑服务**。今日完成：E3 全矩阵 GO（三项 go 全绿，用户已拍 GO）+ Results 4 写作素材落地；W10–11 设计时集成优化器（接头项进 LinearDesign 生成目标）按预注册验收 **NO-GO**，文档/锁已收尾；**E4 执行器替代方案已摆给用户（A/B/C/D），等拍板**。pytest 基线 **587 passed, 1 skipped**（今日 +23）。

## 1. 今日时间线（都可溯源）

1. **E3 全矩阵**（20 任务 × 2 臂 = 40 runs，14:08–14:48 UTC）：`e3_runs_full.jsonl` 40 行无重复 → `e3_adjudicate.py` → `e3_analysis.py` → `e3_runs_full_summary.json`。结果：FP 57.9%→0%（相对降 100%，阈值 ≥50%）、TP 保留 112.5%（阈值 ≥90%）、门控臂越权 0 → 三项 go 全绿，**用户拍 GO**。盲化映射 `e3_runs_full_blind_map_SEALED.json` 封存勿开。
2. **Results 4 写作素材**：`experiments/results/RESULTS4_E3_MATERIALS.md`（per-arm 表、逐任务裁决表、worked example aptamer_ranking_1 双层门控各自起效、三个次级案例、建议图表、措辞纪律）。
3. **MODEL_API_USAGE.md** 已更新两行：E3 全矩阵（DeepSeek deepseek-v4-pro，80 次调用，<¥20 估算）、P2 验收（无 LLM）。
4. **W10–11 集成优化器**（计划文件在 session plans 目录，四 Phase 全走完）：
   - LinearDesign C++ 补丁（submodule `external_repos/LinearDesign/src/`，31 处 `JUNCTION-PATCH` 标记）：伪密码子固定侧翼进全局折叠 + 接头窗配对惩罚 w_jun；argc==4 逐字节回归通过；能量符号约定实测记录（最大化 score，打印=score/−100）。
   - 8014 新端点 `/generate/cds_junction_aware` + 新工具 `design_mrna_cds_junction_aware_with_lineardesign` v0.1.0（INTERFACE_LOCKS §21 新锁；全链注册；+23 单测）。
   - **P2 验收 NO-GO**：`experiments/junction_integrated_optimizer_eval.py` 跑 72 cells（6 靶点 × 3 rep × w_jun∈{0,0.5,1,2}），判定书 `junction_integrated_optimizer_summary.json`。三项判据无一权重全过（hard 修复率 ≤2/7、稳定性代价 0.015–0.031/nt vs 阈值 0.011、CAI 判据全过）。**机制：罚项坐标系（全长全局折叠，窗内配对 43→0 正常）≠ 指标坐标系（孤立 40nt 片段折叠，CDS 端 20nt 片段内自发卡仍 buried）**——第二次 NO-GO，与 P1 v2（事后局部代理）证据链互补。
   - 文档收尾全做：`docs/tools/design_mrna_cds_junction_aware_with_lineardesign.md`、`docs/change_logs/2026-08-04_lineardesign_junction_patch.md` + `..._tool_v0.1.0.md`、INTERFACE_LOCKS §21、TOOLS.md、CHANGELOG.md、AGENTS.md。**新工具状态 = 已注册能力、未接入任何工作流**。

## 2. 待用户拍板：E4 执行器替代方案（已摆出，未选）

- **A. 接头修复剥离出 E4**：执行器 = 现有 FullLengthMrnaDesignWorkflow（shuffle-only）；接头无可靠修复手段进 Discussion 局限；最保 W12–13 成稿排期。
- **B. 继续 P3**：罚项改坐标系（CKY 内对窗内子序列建片段折叠惩罚，与指标同坐标系）；机制诊断明确但已消耗两轮，有排期风险。
- **C. generate-and-select 用真指标筛选（助手建议）**：λ 扫多样性 → JunctionEvaluator 真指标 + 全长 MFE + CAI 做 Pareto 选择；预算匹配下选择计入预算。损失"设计时集成"叙事点，但 P1 v2 + P2 两个预注册负结果可写成 Discussion"接头优化为何困难"小节。
- **D. 混合**：E4 先用 C 跑，B 作技术债并行。
- 拍板后：选 C/D/A → 把执行器方案回写设计文档 `docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4 依赖条（回写惯例上先给用户过目）；选 B → 先出 P3 实现方案。

## 3. 关键指针

- E4 设计：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4（双终点：效率——20 靶点预算节省 ≥25%；设计收益——已验证指标 Wilcoxon + Cliff's δ ≥0.3；预算匹配铁律；**禁用未画像 oracle 作评判**）。
- E4 排期硬知识：HER2 单 LinearDesign 进程 RSS ~47GiB、Beta_gal ~32GiB，cgroup 200GiB → 并发 ≤2；HER2 ~920s/cell。
- P2 判定书机制注记写法可复用（`junction_integrated_optimizer_summary.json` mechanism_posthoc）。
- E3 素材：`RESULTS4_E3_MATERIALS.md`；E2 审计：`E2_SELF_AUDIT_FIG4_FIG7B.md`。

## 4. 暂缓项（同前，未动）

- E2(b) 文献审计排期（Results 3 第二块）。
- bmc_x1 BSA seed0/seed1 异常格按当前代码重跑（进论文前）。
- 论文目标：Nat Methods 直冲；不做提前预注册公开。

## 5. 纪律重申

- git 操作必须先问用户；pytest 基线 **587 passed, 1 skipped**；改代码后必跑。
- 产生论文数据当天更新 MODEL_API_USAGE.md。
- 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程（单工作者）。
- 锁接口只增不改，涉及锁定接口先走 `docs/INTERFACE_LOCKS.md` 流程。
