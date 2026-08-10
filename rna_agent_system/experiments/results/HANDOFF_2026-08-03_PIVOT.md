# 交接提示词（2026-08-03 试点转向版，新会话专用）

> 用法：新开会话后，先读本文件，再按需要参考 `HANDOFF_PROMPT.md`（2026-07-30 版，含历史血泪教训 §5，仍全部有效）与 `rna_agent_system/docs/MANUSCRIPT.md` §13.1（新试点规范）。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（命令统一带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。

## 0. 一句话现状

图 2–7 已全部完成（见旧 HANDOFF）。经根因分析，当前主线是**三个试点（P0/P1/P2）决定论文新叙事**：
**P1 已完成且判定 GO；P0 已完成（12/12）且判定 NO-GO；P2 已完成（15/15）且判定 NO-GO；P3 已完成（12/12）且判定 NO-GO。全部收官，最终叙事见 §5。**

### P0 判定书（2026-08-03，NO-GO）

- 分析脚本：`experiments/analysis/p0_go_no_go.py`；判定书：`experiments/results/p0_budget_matched_summary.json`。
- 12 格全齐（4 靶点 × 3 种子组），bmc_x1 vs serial_ext16（egarps best-of-pool，预算均 16）：**Cliff's δ = 0.278 < 0.3 阈值 → NO-GO**；bmc_x1 赢 9/12 格，Wilcoxon p = 0.129（NS）；中位 bmc_x1 0.624 vs ext16 0.242。
- 解读：协调相对预算匹配基线的优势未达到预注册效应量，图 4 主效应**无法与采样预算效应区分**——按预注册，叙事转向"预算感知、诊断引导的自适应搜索"，P3（同预算下诊断引导再生成 vs 随机再采样头对头）成为主战场。
- 注意 δ=0.278 接近阈值且方向一致（9/12 胜），写论文时表述为"预算可解释大部分增益、协调残差效应为小效应量（δ≈0.28, NS）"，不要写成"协调完全无效"。

### P2 判定书（2026-08-03，NO-GO）

- 分析脚本：`experiments/analysis/p2_go_no_go.py`；判定书：`experiments/results/p2_aptamer_calibration_summary.json`。
- 15/15 全成功。凝血酶系列（n=4，HD22 0.5 / HD22[T27] 0.7 / Toggle-25t 0.54 / TBA 25 nM）：**Spearman ρ(native_probability, −log Kd) = 0.40 < 0.6**；全靶点 binder(9) vs negative(5)：**AUROC = 0.356（95% CI 0.00–0.76）< 0.8，低于随机** → 双指标均未过线，**NO-GO**。
- 关键证据：随机阴性 random30_a(Thrombin) np=0.952、scrambled_tba np=0.987，高于多数真 binder（pegaptanib 2e-6、PDGF 适配体 ~1e-8）；TBA（25 nM，最弱 binder）np=0.0009 反而垫底。连凝血酶靶点内 binder/negative 分离都失败（nu172 binder 0.999 但两个阴性 0.95/0.99）。
- 解读（R4 证实）：EGARPS native_probability 不追踪亲和力、不分 binder/阴性。按预注册——论文加"逐靶点校准门控"，优化 claim 限同靶点同批次相对比较，校准结果本身写成方法边界发现。**注意：P0 的 NO-GO 结论建立在 egarps best-of-pool 上，而 P2 证明该指标本身未校准——P0 结论的解读需带上这一限定（两者一致指向"目标函数可信度"是首要问题）。**

### P3 判定书（2026-08-03，NO-GO）

- 驱动：`experiments/run_p3_guided_vs_unguided.py`（进程内驱动 + coordinator 实例补丁，零 agent_core 改动、零 LLM）；分析：`experiments/analysis/p3_go_no_go.py`；判定书：`experiments/results/p3_guided_vs_unguided_summary.json`。
- 设计：非引导臂完全复刻 bmc_x1 两段式机制（同初始批 8 → 强制第二批 seeds+1 共 8，pool 恒 16），仅把诊断替换为固定重采样指令——单独隔离"诊断内容"这一成分（P0 的 serial_ext16 还混入了机制差异）。
- 结果：12/12 全成功（全 pool=16）。guided(bmc_x1) vs unguided_2pass：**Cliff's δ = 0.222 < 0.3 → NO-GO**；guided 赢 9/12，Wilcoxon p = 0.110（NS）；中位 guided 0.624 vs unguided 0.520。次级指标（预算）：guided 仅 Thrombin seed2 收敛于 pool=8（省一半预算且质量持平 0.891 vs 0.889），其余 11 格诊断均选择再生成。
- **重要 caveat**：guided 输的 3 格中 2 格是 BSA seed0/seed1（0.03 vs 0.92、0.49 vs 0.72）——正是 rounds_executed=0 的代码版本异常格（2026-07-19/20，EGARPS 链修复前）。剔除 BSA 后 guided 赢 7/9，方向一致但效应量仍小。预注册按 12 格判定，NO-GO 成立；BSA 格若要进论文需按当前代码重跑 bmc_x1。
- 解读：诊断内容（相对纯重采样）无超出预注册效应量的价值；方向性残差（9/12 胜、中位差 +0.10）与 P0 一致但同样 NS。叠加 P2（目标未校准），BMC 的可辩护价值收敛为**自适应预算分配**（收敛即停省钱）+ 重采样机制，"诊断引导"叙事在试点尺度不成立。最终叙事：P1 设计时集成（唯一 GO）+ BMC 定位为预算感知自适应框架 + 校准门控作为方法边界。

## 1. 为什么转向（根因，勿再争论，写在各驱动 docstring 里）

- **R1 预算混淆**：图 4 的 BMC 每轮重新生成使候选池翻倍（serial=8 → bmc_x1=16），"主效应"可能只是采样预算效应——缺预算匹配对照臂。
- **R2 机制不对称**：Type-I 协调动作空间只有拧 λ（LinearDesign 确定性）+ 24 密码子微扰 + 有限 UTR preset，无序列空间探索能力 → 图 3 无主效应是结构性的。
- **R3**：图 5b/c 全阴说明增益载体是"多生成"而非"诊断得好"。
- **R4**：评分链未校准（pegaptanib 在自家 EGARPS 链上 ~5e-7）。
- 新叙事方向：BMC 从"有界协调提升设计"升级为"预算感知、诊断引导的自适应搜索"+ Type-I 改用"设计时目标集成"。

## 2. 三个试点的状态与接续方式

### P0（已完成，NO-GO —— 判定书见 §0）

- 驱动：`experiments/run_budget_matched_control.py`（Serial 臂 n_odesign_samples=16 = BMC×1 总生成量，4 靶点 BSA/Lysozyme/Thrombin/VEGF × 3 种子组 = 12 runs）。
- **进程**：2026-08-03 09:05 以 setsid nohup 启动（脱离会话），日志 `experiments/results/fig4_budget_matched.log`，记录 `fig4_budget_matched.jsonl`（逐行增量，同 job 取最新）。速度 ~35 min/run（GPU 有其他租户），预计 12 runs 约 7 小时（~16:30 完成）。
- **接管**：先 `pgrep -af run_budget_matched_control` 确认是否活着；若进程没了但不足 12 条 success，用同一命令重启（`--resume` 幂等）：
  `setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_budget_matched_control.py --resume --timeout 5400 >> experiments/results/fig4_budget_matched.log 2>&1 < /dev/null &`
- **跑完后的分析（go/no-go 预注册在驱动 docstring）**：按 (target, seed_idx) 配对比较现有分片记录（`fig4_type2_shard_{a,b}.jsonl` 的 rounds=0/1/2）与 `fig4_budget_matched.jsonl` 的 serial_ext16：bmc_x1 vs serial_ext16 的 egarps best-of-pool Cliff's δ ≥ 0.3 → GO（协调有预算外价值）；δ≈0 → NO-GO（预算解释效应，叙事转"自适应预算分配"，启动 P3：同预算下诊断引导再生成 vs 随机再采样头对头）。

### P1（已完成，GO）

- 结果：`experiments/results/p1_junction_optimizer.jsonl` + `p1_junction_optimizer_summary.json`（判定书）。
- 结论：接头感知密码子优化器（`experiments/junction_aware_codon_optimizer.py`）18/18：基线掩埋 14 run 修复 13（硬靶点 8/9），CAI 中位 +0.0025（最差 −0.0026），接头 mfe/nt 16/18 优于 BMC×1。代价：全局稳定性下降，大蛋白 +0.009/nt、小蛋白 +0.044/nt（v2 需加可调稳定性项）。
- **后续（等 P0/P2 结论后一起做）**：v2 加稳定性权重 → 作为设计时选项集成进 `FullLengthMrnaDesignWorkflow` → 按 §13.1 规范跑 20 靶点全矩阵（预算匹配臂必须保留）。

### P2（已完成，NO-GO —— 判定书见 §0）

- 校准集：`data/benchmarks/external_anchors/aptamers/calibration_set.json`（15 条目；凝血酶 4 点 Kd 梯度 HD22 0.5/HD22[27] 0.7/Toggle-25t 0.54/TBA 25 nM；VEGF/PDGF-BB/IgE/SARS-N；5 个固定种子阴性；序列经 RCSB 4I7Y/3DD2 复核；SOURCES.md 已补）。蛋白 FASTA 在 `aptamers/proteins/`。
- 打分驱动：`experiments/run_aptamer_calibration.py`（RhoFold→ProteinX→EGARPS 直调链，预检自起服务，--resume 幂等；严守 EGARPS 三坑纪律）。
- **启动条件**：P0 进程结束后（单工作者 GPU 服务不能并行抢）：
  `setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_aptamer_calibration.py --resume >> experiments/results/p2_aptamer_calibration.log 2>&1 < /dev/null &`
- **跑完后的分析（go/no-go 在驱动 docstring）**：凝血酶系列 Spearman(native_probability, −log Kd)（n=4，报 ρ 即可，n 小不报 p）；全靶点 binder vs negative AUROC。ρ ≥ 0.6 且 AUROC > 0.8 → GO（目标可信）；否则 → 论文加"逐靶点校准门控"，优化 claim 限同靶点相对比较，校准结果本身写成方法边界发现。

## 3. 新踩的坑（本次新增，旧 HANDOFF §5 十条仍然全部有效）

11. **session artifact 的 `metadata.cds_sequence`/`protein_sequence` 超长会被 `...(truncated)` 截断**——完整 CDS 必须从 `best_candidate.sequence` 按 UTR 长度切片（`junction_aware_codon_optimizer.py::load_serial_seed` NOTE）。
12. **CAI 权重表键是 RNA 密码子（AUG）**，DNA 序列查表前要 T→U（`junction_aware_codon_optimizer.py::_w_rna`）；`_load_builtin_codon_tables()` 的键是显示名（'Homo sapiens'）。
13. **后台子代理配额已恢复**（本次 P2 文献核实用 explore 子代理成功）；但一手文献序列在图片版 Figure 里的（9.3t、TTA1、RT1t49、t44）子代理核不到，不要强行收录。
14. 任何"best-of-pool/超体积"比较的臂必须**总生成评估量匹配**（R1 的教训；已固化进 `MANUSCRIPT.md` §13.1 试点规范）。

## 4. 本次已落盘的文件清单

- 驱动/脚本：`experiments/run_budget_matched_control.py`、`junction_aware_codon_optimizer.py`、`curate_aptamer_calibration.py`、`run_aptamer_calibration.py`
- 结果：`experiments/results/p1_junction_optimizer.jsonl` + `_summary.json`、`fig4_budget_matched.jsonl`（增长中）、`p2_aptamer_calibration.jsonl`（待生成）
- 数据：`data/benchmarks/external_anchors/aptamers/calibration_set.json` + `proteins/{pdgfbb,ige_fc}.fa` + SOURCES.md 追加
- 文档：`MANUSCRIPT.md` §13.1 试点规范、`MODEL_API_USAGE.md` 三行试点记录（P0 用 DeepSeek QualityAgent；P1/P2 零 LLM）
- pytest 基线未动（本次全是 experiments/ 新脚本，未改 agent_core）——收尾时跑一遍确认：`PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x`（基线 507 passed, 1 skipped）

## 5. 收尾待办（P0/P2 分析完成后）

- ~~两试点的 go/no-go 结论写进对应 summary JSON + 本文件更新~~ ✅ 2026-08-03 完成（P0/P2/P3 判定书见 §0）
- ~~`docs/CHANGELOG.md` 加 2026-08-03 条目~~ ✅ 2026-08-03 完成（含 P3 追加）
- ~~与用户讨论论文叙事分支~~ ✅ 2026-08-03 完成：用户拍板 P3 优先（已完成）、图 4 主文保留降级 claim；随后战略升级——旧叙事整体被新设计取代

## 6. 战略升级（2026-08-03 晚，用户拍板方向）

- 结论：旧 BMC/平台叙事撑不起目标期刊（Nat Methods 档），用户决定**保留 RNA 设计智能体身份、推倒重做 Layer 3 的系统设计/创新点/实验**。
- 经文献调研修正的创新点：**oracle 能力画像 + claim 门控**（非"发现 oracle 不可信"——那是 CASF 常识）+ 跨战役案例记忆 + 预算感知实验决策。
- **新系统设计文档：`rna_agent_system/docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md`**（含架构、预注册实验矩阵 E1–E4、论文骨架、12 周里程碑），待用户/导师评审后动工。
- **新会话入口：`experiments/results/HANDOFF_2026-08-03_REDESIGN.md`**（本文件之后以此为准）。
- 下一步（文档获批后）：W1–2 做 P1 v2（稳定性权重）+ E1 画像试点（3 靶点，数据就绪）。
