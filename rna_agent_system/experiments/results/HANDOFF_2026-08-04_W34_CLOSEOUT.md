# 交接提示词（2026-08-04 W3–4 收官版：E4 路线已定，新会话专用）

> 用法：新会话先读本文件 + `HANDOFF_2026-08-04_W12.md`（工程纪律 §6 全部仍有效），再按本文件 §1 执行。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（命令统一带 `PYTHONPATH="$(pwd):$PYTHONPATH"`）。

## 0. 一句话现状

**W3–4 三个里程碑全部收官，当日无在跑实验、无待重启任务、GPU 空闲、监控 cron 已全部删除。**
E1 扩展判定书出炉（预注册方向全面成立）；E4 执行器路线用户已拍板 = **生成时集成**（接头项进 LinearDesign 生成目标）。
下一步是 W5–9：Layer 3 重建（SelfModel/DecisionGate/ClaimGate/CaseMemory/ExperimentPlanner）+ E3。pytest 基线 507 passed, 1 skipped（全天未动 agent_core）。

## 1. 下一步（按优先级）

### 1.0 无需接管任何在跑任务

- E1 扩展 GPU 画像已于 2026-08-04 ~10:30 UTC 正常完成（日志 `experiments/results/logs/e1_extension_run.log` 尾部有 `Part B done`），合并分析已跑，监控 cron 已删。
- 若发现意外残留的 `run_e1_capability` 进程，先查日志再决定（`--resume` 幂等，命令见 `HANDOFF_2026-08-04_W34_E1EXT.md` §1.0）——但预期没有。

### 1.1 主线：W5–9 Layer 3 重建 + E3（设计文档 §2.2 / §3 E3）

动工前必读：`docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md`（v2 已批准版，今日 E4 拍板已同步进 §3 E4 与 §5）。
新组件清单与耦合关系见该文档 §2.2 架构图；一次战役标准流程见 §2.3；E3 预注册（≥20 审计任务、两臂、盲评、假阳性率主指标 + 决策层越权次级指标）见 §3 E3。
工程纪律：新组件走**新增**而非修改（旧 agent 栈保留为 E3 对照臂；INTERFACE_LOCKS 锁定接口全部不动）；遵循 `docs/CONTRIBUTING.md`（含简洁性纪律 §0）；改代码后必跑 pytest 回到基线。

### 1.2 W10–11 预告（现在不动手）

设计时集成优化器落地（接头项进 LinearDesign 生成目标）→ E4 全矩阵（20 靶点 × 两臂，预算匹配铁律，双终点：效率 + 已验证指标设计收益）。E4 执行器不得使用任何未画像 oracle 作评判（设计文档 §3 E4 边界）。

### 1.3 暂缓项

- E2(b) 文献 claim 复核（3–5 篇外部论文，措辞限"用法复核"、不点名羞辱）——W3–4 只要求自家审计，文献审计排期由用户定。
- E2 自家审计若需进论文：bmc_x1 的 BSA seed0/seed1 为代码版本异常格（P3 判定书 caveat），进论文前需按当前代码重跑。

## 2. 今日（W3–4 收官）已落盘的关键资产

- **E1 扩展判定书**：`experiments/results/e1_capability_summary_v2.json`（试点+扩展按 id 合并，66 Part A + 102 Part B poses；`experiments/analysis/e1_extension_analysis.py`）。
  - Screening：18 组合无一过 AUROC>0.8（敏感性：6/18 过 0.6、0/18 过 0.9）→「no oracle shows reliable screening power for RNA-protein aptamers across targets」成立。
  - Ranking：ranking-eligible 同 assay 子集无一 ρ≥0.6。
  - Docking：EGARPS native top-1 = 0/5（Thrombin 0/3 + 1HVU 10/21 + 8EPK 10/21）→ docking power 不迁移，5 锚点稳住。
  - 原始记录：`e1_oracle_scoring_v2.jsonl`（37/37）、`e1_docking_power_v2.jsonl`（42 poses）；零 LLM（已录 MODEL_API_USAGE.md）。
- **锚点基础设施**：`docs/ANCHORS.md`（目录规范 + JSON schema + 断言优先 curation 模式九条；已登记根 AGENTS.md 索引）。
- **E2 自家审计落文**：`experiments/results/E2_SELF_AUDIT_FIG4_FIG7B.md`——图 4 主效应 + 图 7B pegaptanib 对比逐条过画像协议；**存活率 0/2 < 70% → E2 审计故事成立**；含 ClaimGate 降级表述与 DecisionGate 反事实；Results 3 worked example 骨架在 §4。
- **E4 拍板**：生成时集成（2026-08-04 W3–4 收尾，用户三选一拍的）——已同步 `docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §3 E4（设计/依赖/依赖图）+ §5 里程碑表 + `docs/CHANGELOG.md` 2026-08-04 设计决策段。
- **文档同步**：CHANGELOG 2026-08-04 条目（W3–4 小节）、`experiments/results/MODEL_API_USAGE.md`（v2 curation + 扩展画像两行，零 LLM）、`data/benchmarks/external_anchors/SOURCES.md`（E1 扩展完整出处段）。

## 3. 工程纪律（W12 交接 §6 全部有效，重点重申）

- **GPU 单工作者**：任何 GPU 驱动启动前 `pgrep -af` 确认；`GPU_get.py` 等他租户任务勿杀勿等；常驻 uvicorn 服务空闲占显存正常。
- **预算匹配铁律** + 预注册写驱动 docstring 再跑。
- **pytest 基线 507 passed, 1 skipped**；改代码后必跑。
- **git 操作（commit/push）必须先问用户**。
- **序列核实纪律**：图版序列不收；正文/表格 + 复核；断言放生成器（`docs/ANCHORS.md` 已固化该模式）。
- **MODEL_API_USAGE.md**：凡产生论文数据的实验当天更新。
- **cron 会话级**：新会话需重建监控任务；已完成任务及时删 cron。长任务 `setsid nohup` + 日志落盘 + 低频监控。
- 子代理配额可用（文献核实用 explore 效果好）；写大脚本主 agent 自己写。

## 4. 悬而未决

- 无。E4 路线已拍板；E2(b) 文献审计排期与 W5–9 开工节奏由用户定。
