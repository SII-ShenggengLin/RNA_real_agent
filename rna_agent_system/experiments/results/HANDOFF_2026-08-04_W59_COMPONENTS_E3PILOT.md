# 交接提示词（2026-08-04 W5–9 开工版：Layer 3 重建组件齐套 + E3 试点已跑，新会话专用）

> 用法：新会话先读本文件 + `HANDOFF_2026-08-04_W34_CLOSEOUT.md`（工程纪律 §3 全部仍有效）。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（命令统一带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。

## 0. 一句话现状

**W5–9 的组件层全部落地（SelfModel/CapabilityProfiler/DecisionGate/ClaimGate/CaseMemory/ExperimentPlanner/AuditTrail + CalibratedCampaignRunner），E3 脚手架 + 6 任务试点已跑通。**
pytest 基线 **563 passed, 1 skipped**（507 + 新增 56）。当日无在跑实验、无待重启任务。
**悬而未决：E3 全矩阵（20 任务）开工前需用户对试点发现的两项修正拍板**（见 §3）。

## 1. 今日已落盘的关键资产

- **新包 `agent_core/calibrated/`**（纯新增，旧 agent 栈未动一行，留作 E3 对照臂）：
  `models.py`（CASF 四能力模式）、`self_model.py`（query：精确→transferred 降级→unprofiled；transferred 保留 `transferred_from_grade` 供门控区分迁移自 verified/failed）、`case_memory.py`（JSONL 战役档案 + 确定性加权相似检索 + SelfModel 持久化）、`audit_trail.py`（append-only JSONL）、`profiling_metrics.py` + `profiler.py`（e1_driver 子进程后端 + deterministic 纯 Python 后端）、`decision_gate.py`、`claim_gate.py`（降级阶梯 absolute→within_target_relative→trend_only，模板措辞，LLM 润色默认关）、`experiment_planner.py`（LLM 依赖声明 + 确定性预算分配）、`campaign_runner.py`（§2.3 七步流）。
  文档：ARCHITECTURE.md §2.4.1、CHANGELOG 2026-08-04 W5–9 条目。
- **E3 脚手架**：任务集 `experiments/e3/audit_tasks.json`（20 任务 = 10 确定性指标优化 + 10 适配体排序/筛选，候选取自 E1 v2 锚点集、Kd 真值保留在 ground_truth 里不给 agent；生成器 `experiments/e3/build_audit_tasks.py` 断言优先、确定性）；驱动 `experiments/run_e3_gated_vs_ungated.py`（**预注册在 docstring**；`--pilot/--tasks/--arm/--resume` 幂等）；裁定 `experiments/analysis/e3_adjudicate.py`（确定性真值校验 + 盲化文件 + 可选 `--llm-review`）；分析 `experiments/analysis/e3_analysis.py`。
- **E3 试点结果**（6 任务 × 2 臂，24 次 DeepSeek 调用，temp 0，零 GPU——oracle 分数走 E1 预计算查找表，**注意驱动合并读取试点+v2 两个 scoring JSONL，单读 v2 只有 37/66**）：
  `experiments/results/e3_runs_pilot{,_adjudicated,_summary}.json{,l}`、盲化文件 + SEALED 映射同目录。
  - 非门控臂：FP 率 0.667（4 FP / 2 TP），决策层越权 **5 次**；门控臂：FP 率 0.75（3 FP / 1 TP / 1 suppressed / 1 borderline），越权 **0**（DecisionGate 硬保证成立）。
  - 任务集区分度成立（对照臂 untrusted_oracle 3 FP）；`aptamer_ranking_1` 门控臂教科书式拒答（"ranking 被拒，不发 claim"）。
  - MODEL_API_USAGE.md 已录（§2 末行 + §1 例外注记——**被测系统内 LLM 首次进实验数据**）。

## 2. 试点暴露的两个问题（非门控失效，全矩阵前须处理）

1. **A 类任务 LLM 长度马虎**：门控臂 gc_target_0/purine_band_0 的 final_sequence 为 58/61 nt（任务要求 60）→ 判 FP。是执行/提示词问题，与门控无关（非门控臂同类 2/3 对）。修法候选：报告提示词加硬性格式要求 + 驱动端长度校验重试一次。
2. **未声明代理绕过 ClaimGate**：门控臂 `aptamer_ranking_0` 在 structural oracle 被拒后改用 "GC content as a structural proxy" 排序（dependencies=[]），选了错候选 → 判 FP。ClaimGate 只门控已声明依赖，空依赖的代理 claim 漏网。修法候选：(a) 用 CapabilityProfiler deterministic 后端把 gc/u/purine 也画像进 SelfModel（aptamer_affinity 上必 failed）并要求 LLM 声明一切排序依据；(b) ClaimGate 加规则——aptamer_affinity 的 ranking/screening claim 空依赖即 reject（无依据不发定量 claim）。

## 3. 下一步（按优先级，等用户拍板）

1. **E3 全矩阵开工决策**：§2 两项修正的取舍（提示词修 + ClaimGate 空依赖规则/代理画像），然后 20 任务 × 2 臂（40 runs、80 次 LLM 调用、零 GPU，~半小时墙钟）。
2. W10–11 预告（不动手）：设计时集成优化器（接头项进 LinearDesign 生成目标）→ E4 全矩阵。
3. 暂缓项同 W34 交接 §1.3（E2(b) 文献审计排期、bmc_x1 BSA 重跑）。

## 4. 工程纪律重申（W12/W34 全部有效）

- **后台驱动纪律（今日新坑 16）**：`setsid nohup` 后台化时若重定向目标目录不存在，外层 shell 报 redirect 失败但进程仍可能被拉起——**启动后必须 `pgrep -af` 数进程**，今日 E3 试点双驱动并发写了 2 条重复行（已去重，保首条）。
- E3 裁定/分析脚本吃项目外路径（`--runs /tmp/...`） smoke 没问题；盲化映射文件带 `_SEALED` 后缀，论文复核前勿打开。
- git 操作必须先问用户；pytest 基线 563 passed, 1 skipped。
- E3 全矩阵属论文数据，跑完当天更新 MODEL_API_USAGE.md。
