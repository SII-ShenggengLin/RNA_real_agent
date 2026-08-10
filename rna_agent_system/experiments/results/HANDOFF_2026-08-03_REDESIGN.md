# 交接提示词（2026-08-03 战略转向·新会话专用）

> 用法：新会话先读本文件，再按 §2 的必读顺序补背景，然后按 §4 执行。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（命令统一带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。

## 0. 一句话现状

P0–P3 四个试点全部收官（P1 GO；P0/P2/P3 均 NO-GO），旧 BMC/平台叙事被判定撑不起 Nat Methods 档；**用户已拍板：保留 RNA 设计智能体身份，推倒重做 Layer 3 的系统设计/创新点/实验**。新系统设计文档已写好待评审，下一步是文档获批后启动 W1–2 工作（P1 v2 + E1 画像试点）。

## 1. 今日决策链（勿再争论，已落盘）

1. 四试点判定书全部在 `experiments/results/HANDOFF_2026-08-03_PIVOT.md` §0：P0 δ=0.278（预算解释图 4 主效应）、P2 ρ=0.40/AUROC=0.356（oracle 无 ranking/screening 能力）、P3 δ=0.222（诊断内容不优于纯重采样）、P1 GO（接头感知优化器 18/18）。
2. 文献调研结论（已写进设计文档 §1）：工具链不是私货（RhoFold/Protenix/EGARPS+ 均为已发表标准件）；P2 的"发现"是 CASF 已知常识（评分函数四能力分开考核，EGARPS+ 原文只声明 docking power）；**真正的空位在 agent 侧——没有任何 agentic 系统在战役前实测 oracle 科学适用性并门控 claim**。
3. 修正后创新点：**oracle 能力画像 + claim 门控**（架构原语）+ 跨战役案例记忆 + 预算感知实验决策。概念是 CASF + ML 指导工程校准的迁移，论文不得把概念本身表述为原创。
4. 目标期刊：Nat Methods 冲 / Nat Commun 稳 / NAR G&B 保底；无湿实验通道。

## 2. 必读顺序

1. **本文件**（现状与下一步）。
2. `rna_agent_system/docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` —— 新系统设计文档（架构、预注册实验矩阵 E1–E4、论文骨架、12 周里程碑、风险退路）。**一切动工以它为准。**
3. `experiments/results/HANDOFF_2026-08-03_PIVOT.md` —— 四试点判定书 + 新坑 11–14。
4. 需要细节时：`experiments/results/HANDOFF_PROMPT.md` §5（13 条血泪教训，全部仍有效）、`docs/MANUSCRIPT.md` §13.1（试点规范）。

## 3. 今日已落盘的关键资产

- 设计文档：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md`
- P3 驱动/分析/判定书：`experiments/run_p3_guided_vs_unguided.py`、`analysis/p3_go_no_go.py`、`results/p3_guided_vs_unguided{,.jsonl,_summary.json}`（12/12，全 pool=16）
- P0/P2 判定书：`results/p0_budget_matched_summary.json`、`p2_aptamer_calibration_summary.json`；分析脚本 `analysis/p0_go_no_go.py`、`p2_go_no_go.py`
- 文档更新：CHANGELOG 2026-08-03 条目（含 P3）、MODEL_API_USAGE P0–P3 行、PIVOT handoff §0/§5/§6
- pytest 基线 507 passed, 1 skipped（全天未动 agent_core）

## 4. 下一步（按优先级）

### 4.0 先问用户

- **设计文档是否已获用户/导师批准？** 未批准 → 先与用户过文档（重点：创新点表述边界、E1–E4 矩阵、12 周排期、§6 预注册公开与否待定项），按反馈修订，不要动工。
- 批准 → 按 4.1/4.2 动工。

### 4.1 W1 任务 A：P1 v2（接头感知优化器加稳定性权重）

- 现状：`experiments/junction_aware_codon_optimizer.py`（P1，18/18 GO）；代价是全局稳定性下降（大蛋白 +0.009/nt、小蛋白 +0.044/nt mfe/nt）。
- v2 目标：加**可调稳定性权重**，把稳定性代价做成用户可控 trade-off 旋钮；用现有 18 run 矩阵回归验证（权重扫描 + 接头修复率 vs 稳定性代价曲线）。
- 完成后：作为设计时选项集成进 `FullLengthMrnaDesignWorkflow`（**该工作流是锁定接口 v2.7.0，改动必须走 `docs/INTERFACE_LOCKS.md` 锁流程**）。

### 4.2 W1–2 任务 B：E1 oracle 能力画像试点（数据就绪，可立即开工）

- 预注册在设计文档 §3 E1：CASF 四能力 × 3 oracle（egarps native_probability、proteinx ipTM、rhofold pLDDT）× 3 靶点（Thrombin/VEGF/PDGF-BB）。
- 数据：`data/benchmarks/external_anchors/aptamers/calibration_set.json`（15 条目 prototype）；E1 需扩展——每靶点 ≥4 binder 亲和力梯度 + ≥3 固定种子阴性 + 天然/诱饵构象对（docking power 用）；序列核实纪律见 PIVOT §3.13。
- 驱动模式照抄 `experiments/run_aptamer_calibration.py`（RhoFold→ProteinX→EGARPS 直调链，--resume 幂等，严守 EGARPS 三坑纪律）；分析模式照抄 `analysis/p2_go_no_go.py`；预注册写进驱动 docstring 再跑。
- go/no-go 与叙事反转预案见设计文档 §3 E1 与 §6。

### 4.3 暂不做的

- BSA 三格 bmc_x1 重跑（版本异常格）：仅当图 4 数据要进论文时才需要，E2 审计阶段再说。
- E2 文献审计、E3/E4 建设：等 E1 结果 + 设计文档批准后按里程碑排。

## 5. 工程纪律（本项目血泪，新会话必读）

- **血泪教训 13 条**见 `HANDOFF_PROMPT.md` §5 + **新坑 11–14**见 PIVOT §3（session artifact 截断、CAI 表 RNA 键、文献核实边界、预算匹配铁律）。
- **GPU 单工作者**：RhoFold/ProteinX/EGARPS 服务不能并行抢，任何时刻只跑一个 GPU 驱动；启动前 `pgrep -af` 确认进程表为空。
- **长任务模式**：`setsid nohup ... &` 脱离会话 + 日志落盘 + **cron 每小时检查一次**（用户明确要求，不要 13 分钟高频）；进程死了先查日志区分正常退出/被杀再 `--resume` 重启。
- **预算匹配铁律**（R1 教训）：任何 best-of-pool/超体积比较，各臂总生成评估量必须相等；预注册（假设/主指标/阈值/试点 n）写进驱动 docstring 再跑。
- **pytest 基线 507 passed, 1 skipped**；改代码后必跑；git 操作（commit/push）必须先问用户。
- **模型 API 记录强制**（`MODEL_API_USAGE.md` §6 规范）：凡产生论文数据的实验当天更新。
- 子代理配额可用，但写大脚本优先主 agent 自己写。

## 6. 待用户决定事项（不要擅自决定）

1. 设计文档整体批准与否（含 12 周排期可行性）。
2. 是否在 W2 前把 E1 协议做预注册公开（OSF/arXiv）防抢发（设计文档 §6）。
3. 投稿目标顺序：Nat Methods 直冲 vs Nat Commun 起步。
