# 交接提示词（2026-08-05：E4 试点运行中，新会话接管监控）

> **用法**：新会话先读本文件。上一个会话的交接链：`HANDOFF_2026-08-04_P2NOGO_E4DECISION.md`（E3 GO + P2 NO-GO 背景）、`HANDOFF_2026-08-04_W34_CLOSEOUT.md` §3、`HANDOFF_2026-08-04_W59_COMPONENTS_E3PILOT.md` §4（工程纪律出处，含坑 16：后台启动后必须 pgrep 数进程）。
> **注意**：新会话使用的是**另一款编程 agent（非 Kimi Code）**，不继承上一个会话的记忆与定时任务。**E4 试点的定时监控已随旧会话失效，新会话必须自行建立监控**（见 §1）。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。

## 0. 一句话现状

**E4 试点正在跑**（12 场战役 = 3 靶点 × 2 臂 × 2 种子组，2026-08-05 07:53 UTC 启动，预计 3–5 小时）。今日已完成：接头线三次预注册实验收尾（Phase 0 ddG 试点 NO-GO → 用户拍板退方案 A）、ddG 指标落地 + BMC 接头自动修复剥离（锁 §14 v2.8.0）、E4 试点驱动实现并启动。pytest 基线 **627 passed, 1 skipped**。

## 1. 在跑实验：E4 试点（接手监控）

- **进程**：单实例 python 驱动（启动时 PID 3644721，先 `pgrep -af "run_e4_learning_curve"` 确认；匹配到的 bash 包装进程不算）。
- **启动命令**（如需续跑，同一命令，`--resume` 幂等）：
  ```bash
  cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system
  setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" \
    python experiments/run_e4_learning_curve.py --pilot --resume --timeout 3600 \
    > experiments/results/e4_pilot_driver.log 2>&1 &
  ```
  启动后必须 pgrep 数进程确认单实例（坑 16）。
- **日志/产物**：日志 `experiments/results/e4_pilot_driver.log`（`[x/12]` 进度行）；增量落盘 `experiments/results/e4_pilot_runs.jsonl`；session 于 `workspace/sessions/e4_*`；记忆 root `workspace/e4_pilot/case_memory/{A,B}`。
- **跑完后**：`PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/e4_analysis.py` → 判定书 `experiments/results/e4_pilot_summary.json`，向用户报告 **6 条预注册管道判据**（见驱动 docstring）与描述性数据（per 战役评估量、final λ、墙钟——全矩阵排期用）。
- **异常处理**：进程死了但 <12 场 → 查日志尾部定位原因（可接受失败 = 子进程超时 / LinearDesign OOM bad_alloc），**先报告用户再决定是否续跑**；不要擅自重启。单场超时 3600s。
- **建议监控方式**：每小时看一次日志进度即可（旧会话的 cron 不跨会话）。

## 2. 今日（2026-08-05）决策链与已完成工作（全部用户拍板）

1. **E4 执行器路线：C → 试点 → 退 A**。
   - 背景：接头修复两次预注册 NO-GO（P1 v2 事后局部代理；P2 设计时集成，罚项坐标系≠指标坐标系，判定书 `junction_integrated_optimizer_summary.json`）。用户拍板走 C（generate-and-select）。
   - **Phase 0 试点**（`experiments/junction_ddg_pilot_eval.py`，108 cell，判定书 `experiments/results/junction_ddg_pilot_summary.json`）：门 1（全长 ddG 指标有效性）**GO**（约束服从 216/216、LinearFold vs Vienna 无约束 MFE r=0.945）；门 2（shuffle 修接头有效性）**NO-GO**——ddG 改善中位 3.3–6.2 kcal/mol、ΔCAI 达标，但稳定性代价 0.0121–0.0125/nt 超阈（≤0.01），3 靶点仅 EPO 过。用户拍板**退方案 A**：E4 执行器 = 现有 FullLengthMrnaDesignWorkflow。
   - 附带实证：旧片段 buried 布尔与全长 ddG 不相关甚至反向（buried=True 中位 4.56 < unburied 5.70）；上市疫苗 BNT162b2/mRNA-1273 在旧指标下同样 aug_buried=kozak_buried=True（`fig3_anchors.json`）——接头指标是软代理，三次负结果（P1 v2/P2/Phase 0）互证「接头修复必花稳定性」，写入 Discussion「接头优化为何困难」。
2. **ddG 指标落地 + BMC 接头修复剥离（锁 §14 v2.7.0 → v2.8.0，用户拍板）**：
   - `JunctionEvaluator`：删 J1 的 5 个 buried 字段，新增全长约束折叠 `junction_5utr_cds_ddg_open_w1/w2`（kcal/mol，= MFE_constrained − MFE_unconstrained，W1=AUG−6..+9，W2=UTR 末 60+CDS 前 30，UTR 不足裁剪）+ 窗口坐标字段；ddG 只进 metrics_bundle，**不进 score/issue/repair、不进 E4 终点**；片段折叠指标（mfe/mfe_per_nt/gc_diff 等）保留（E4 终点列表含「接头 mfe/nt」）。
   - BMC：`_collect_boolean_issues` 及 shuffle 修复分支整条删除；`coordinator.diagnose()` 删 `boolean_issues` 形参。`shuffle_cds_junction_codons` 工具保留（锁定 v0.1.0，可显式调用），工作流不再自动使用。
   - 同步文档：INTERFACE_LOCKS §14、CHANGELOG（2026-08-05 条目）、WORKFLOWS、BMC_FRAMEWORK、AGENTS.md。测试 -2+9，全量 594→**627 passed**。
   - 注意：`experiments/` 历史分析脚本（plot_fig2/3/7、run_bmc_* 等）未动，读历史数据正常；但对**新跑**的工作流结果取 buried 字段会得到 None。
   - `docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4 已回写退 A（设计条/依赖条/依赖图/§5 里程碑 W10–11 四处）。
3. **E4 试点实现**（用户拍板注入映射后实施）：
   - 新文件：`experiments/run_e4_learning_curve.py`（驱动，预注册全文在 docstring）、`experiments/analysis/e4_analysis.py`（管道判定书；全矩阵双终点统计留接口未实现）、`tests/test_e4_pilot.py`（33 单测）。
   - **注入映射（已拍板钉死，全矩阵预注册时方可改）**：memory 臂每场前 `CaseMemory.similar(k=3)` 检索，三旋钮——① λ 共识（final λ 跨度 ≤6 且 ≥2 场可追溯）→ `design_tool="lineardesign"` + λ=中位数；② UTR 共识（≥2/3 相似战役 best 同一 preset 族）→ utr_mode 收窄；③ bmc_max_rounds=相似战役实际轮数中位（钳 [1, 默认]）。冷启动 → 与 nomem 逐位相同（Fig 3 默认：design_tool=all、λ=2.0、utr_mode=all、bmc_max_rounds=1、utopian）。nomem 臂不碰记忆。
   - **预算匹配铁律实现**：事后按候选时间序截断（多截至少），截后 best-of-pool 进设计收益终点；不等则 cell invalid。评估量 = 全长候选评估数（归约定义见驱动 docstring，已对真实 session 验证 0 偏差）。
   - **已知 flag（全矩阵预注册时处理）**：bmc_max_rounds 旋钮试点期恒为 no-op（默认 1），注入点火只靠 λ/UTR；λ 阈值 6 经 Fig 3 分布校准保留（16 靶点中位跨组跨度恰为 6，边界触发）；全矩阵建议默认轮数提到 2–3（Fig 3 水平）。

## 3. 试点 GO 后的下一步（E4 全矩阵，需用户拍板预注册）

1. 向用户报告试点判定书（6 条管道判据 + 描述性数据）。
2. **全矩阵预注册**（给用户过目）：20 靶点（`data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/`，恰 20 个）× 2 臂 × 3 种子组 = 120 战役；默认 bmc_max_rounds 建议提高（用户拍）；Zika(10.3kb)/Factor_VIII(7kb) 撞 LinearDesign OOM 边界，按 Fig 3 先例预先声明为预期失败 cell；双终点——效率（累计评估量~战役序位回归斜率显著为负 + 20 靶点累计预算节省 ≥25%）+ 设计收益（预算匹配截断后已验证指标配对 Wilcoxon 显著 + Cliff's δ ≥0.3，指标 = CAI、MFE、接头 mfe/nt、GemORNA MRL，**禁用未画像 oracle**）；任一终点过 → GO。
3. 规模与运维（Fig 3 实测）：120 战役 ≈ 100–170 CPU·h，约 2 周墙钟；重靶点 HER2 需 `--timeout 9000`；内存并发 ≤2（cgroup 200GiB，HER2 单进程 RSS 数十 GiB）；分片方式照抄 Fig 3（两 shard 各写一个 JSONL）；驱动骨架照 Fig 3 `run_bmc_type1_ablation.py` 的 resume/done-key 模式（试点驱动已继承）。
4. 跑完 → 实现 `e4_analysis.py` 的双终点统计接口（stats_utils 已有 wilcoxon_paired/cliffs_delta/bh_fdr；回归斜率 numpy 一元回归即可）→ 判定书 → Results 5 写作素材。

## 4. 关键指针

- E4 设计：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4 + §5 里程碑（W12–13 成稿）。
- 试点：驱动 `experiments/run_e4_learning_curve.py`（docstring = 预注册全文）；判定书 `experiments/results/e4_pilot_summary.json`（跑完后生成）；日志 `e4_pilot_driver.log`。
- 接头线：Phase 0 判定书 `junction_ddg_pilot_summary.json`；P2 判定书 `junction_integrated_optimizer_summary.json`（mechanism_posthoc 写法可复用）；ddG 试点脚本 `junction_ddg_pilot_eval.py`。
- E3（已 GO）：素材 `RESULTS4_E3_MATERIALS.md`；盲化映射 `e3_runs_full_blind_map_SEALED.json` **封存勿开**。
- E2 审计：`E2_SELF_AUDIT_FIG4_FIG7B.md`。疫苗锚点：`fig3_anchors.json`（两款上市疫苗 aug_buried=True 的出处）。
- 锁流程：`docs/INTERFACE_LOCKS.md`（§14 = v2.8.0 最新）。
- Fig 3 实测耗时：`fig3_type1_shard_a/b.jsonl`；运维教训 `RESUME_CHECKPOINT.md:63-138`。

## 5. 工程纪律（新 agent 必须遵守；用户既定规则）

1. **git 操作必须先问用户**（任何 commit/push/reset 等，每次都要问）。
2. **pytest 基线 627 passed, 1 skipped**；改代码后必跑全量：`cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x`。
3. **简洁优先（2026-08-04/05 用户拍板，`docs/CONTRIBUTING.md` §0）**：不留兼容包袱；有了更好策略，旧策略代码与文档可删除防止膨胀。例外：锁定接口走锁流程；作为实验对照保留的代码（旧 agent 栈 = E3 对照臂）在实验完成前不删。
4. **试点先行（2026-08-05 用户拍板，`docs/MANUSCRIPT.md` §1.4）**：新实验方案/改进思路先小规模试点（预注册判据）确认有效，再大规模验证。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`（E4 试点已预登记：QualityAgent deepseek-v4-pro，约 12 次）。
6. 后台驱动：setsid nohup + 日志落盘 + **启动后 pgrep 数进程**（单实例，坑 16）。
7. 锁接口只增不改；涉及锁定接口先走 `docs/INTERFACE_LOCKS.md` 流程（同步清单 + 版本 bump + 全量测试）。
8. 锁的 CLI 回归：`run_pa_test.py <006..024>`（基准 `pa_benchmarks.json`）。
9. 微服务无需手动启动：工作流/`ensure_services_ready` pre-flight 自动拉起；GPU 服务见 `docs/MANUSCRIPT.md` §1.3（2×RTX 4090）。
10. 项目文档索引见根 `AGENTS.md`（权威文档在 `rna_agent_system/docs/`）；新 agent 应先读 `docs/ARCHITECTURE.md` 与 `docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` 建立全局认识。
11. 论文目标：Nat Methods 直冲；**不做提前预注册公开**（用户 2026-08-04 拍板）。
12. 决策文化：重大路线选择（方案拍板、预注册阈值、终点定义）由用户决定；助手给建议与证据，不擅自拍板。

## 6. 暂缓项（沿袭，未动）

- E2(b) 文献审计排期（Results 3 第二块）。
- bmc_x1 BSA seed0/seed1 异常格按当前代码重跑（进论文前）。
