# 交接提示词（2026-08-07：E5 草案升至 v2——并入 mRNAdesigner 论文设计思想；无实验在跑，新会话从 E5 草案 §13 评审继续）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E4FULL_FINAL_RERUN.md`（E4 收尾）→ `HANDOFF_2026-08-07_E5DRAFT_READY.md`（E5 草案 v1 就绪）→ **本文件（E5 草案 v2）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`；**注意：Bash 工具工作目录跨调用持久——启动后台任务时须在同一条命令内 `cd rna_agent_system &&`，git 命令建议带 `-C <项目根>`**）。

## 0. 一句话现状

**E5 预注册草案 v2 已写好（并入 mRNAdesigner 论文设计思想，§13 未决问题增至 13 条），等用户拍板后按序实施 S0→S1→S2；当前无实验在跑（已 pgrep 核实，仅常驻微服务），无需监控、无需续跑——下一步是向用户呈现 13 条未决问题并等待拍板。**

## 1. 本会话已完成（勿重做）

1. **阅读论文**：`relevant_references/mRNAdesigner an integrated web server for optimizing mRNA design and protein translation in eukaryotes.pdf`（Ouyang et al., Nucleic Acids Research 2025, 53:W415–W426，全文已读，文本提取见 `/tmp/mrnadesigner.txt`，新会话可快速检索）。
2. **向用户呈现论文对照分析两轮**：①指标部分改进建议 10 条（C7 最长茎 / C8 uAUG / pair ratio / ΔGC / ARE / Kozak / C6 窗口扩展 / 稀有密码子定义 / λ 语义区分 / 动机注记）——**待拍板（§13-13）**；②设计思想 6 条（区域差异化 / 仲裁文献先验 / 约束内搜索 / 自然库选点 / 迭代修复 / 结构聚类多样交付）。
3. **用户拍板：并入设计思想** → E5 草案升 **v2**（`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`），变更：§3.1 候选池混合、§4.3 仲裁优先级链（层 1–4 文献先验）、§5 区域化画像权重、§7.2 R4 语义钉死（约束集合内最优）、§7.3 新增 D3、§9/§10 D1–D2→D1–D3、§11 LLM 预算更新（迭代修复若采纳则 C 臂 5–9 次/基因）、§13 未决问题 7→13 条。**草案仍为草案，未实施任何代码。**
4. **核实无实验在跑**（pgrep：无 run_e* 驱动进程；常驻微服务 uvicorn 8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py 正常，勿动）。

## 2. 论文要点速查（新会话不必重读全文）

- **mRNAdesigner 三模块**：CDS（MCTS 同义替换，seq score `w=λ·runpair+(1−λ)·ΔGC+P(L)`，λ 默认 0.5，茎>30bp 则 P(L)=1）、5'UTR（库选点：排除 uAUG、≤100nt、可选 Kozak GCCACC、UTR-LM 预测 MRL、结构聚类 5 簇各取最高 MRL）、3'UTR（UTRdb 库、FIMO 扫 ARE/CURE 过滤）。
- **验证**：RSV F 优化后 GC 36.46→54.95%、pair ratio 59.88→61.42%、最长茎 19→21、CAI 0.868→0.958，表达 2.32 倍；MPXV 4 抗原 CAI 全 >0.9。
- **关键思想**：区域差异化优化；竞争需求显式仲裁（半衰期贡献 > 扫描速度，Bicknell Cell Rep 2024）；约束边界内搜索非打分最大化；自然先验库选点；结构聚类多样交付；免疫原性（>30bp 茎）是一等约束；不追求 CAI 最大化（罕见密码子有功能价值）——**与 E5"四指标不进场"主张互为印证**。
- 指标改进建议 10 条（§13-13）全部**零新模型**（LinearFold/序列规则/本地 motif 扫描）。

## 3. 当前状态

- **无实验在跑**，无需监控/续跑。
- **git**：`.gitignore` 忽略 `experiments/results/`——HANDOFF、E5 草案、E4 判定书均未跟踪；本会话无代码文件改动；仓库根历史遗留 M/D 是否提交由用户定。**git 操作必须先问用户。**
- **E5 草案 v2**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`，§13 共 13 条未决问题（全文见下节）。

## 4. E5 草案 §13 未决问题清单（等待用户拍板，逐条或按优先级）

1. 约束矩阵 C1–C6+M1 清单与阈值是否合适？C5（剪接位点规则 [AG]G[AC]AG）够不够格？
2. S1 规模：5 靶点（草案建议）还是 3？
3. 画像 3 类与权重（§5 v2 区域化表）是否合适？
4. GO/NO-GO 规则（§10）：「任一终点过 → GO」是否采纳？
5. A 臂 λ 网格 {0,1,4,10} 是否保留？
6. 实验代号 E5 与文档命名是否认可？
7. B 臂（无门控 LLM agent）实施时如何构造（旧栈自由规划路径是否仍可用，需查代码）？
8. **迭代修复轮是否采纳**（≤2 轮/基因，C 臂 LLM 预算 3–5→5–9 次/基因）？
9. **区域化画像权重数值**（§5 v2 表）是否认可？
10. **仲裁优先级链**（§4.3 层 1–4）是否采纳？
11. **候选池混合**（§3.1 GEMORNA 生成 + 自然参考 UTR 锚点，A/C 臂共用）是否认可？
12. **D3 结构多样性阈值**（pair ratio 极差 ≥3pp / 最长茎差 ≥5bp）是否认可？
13. **指标改进建议 10 条**（C7 最长茎 ≤30bp、C8 5'UTR 无 uAUG、pair ratio 档案、ΔGC 偏差、3'UTR ARE 计数、Kozak 一致性、C6 窗口扩至 5'UTR+CDS 前 30nt、最稀有密码子定义、LD-λ 与效用 λ 区分、论文动机注记）——逐条或整体拍板？

## 5. 下一步（用户拍板后按序实施；拍板前不要动 E5 草案）

1. **等用户审 §13 的 13 条未决问题**（本会话已向用户呈报 v2 变更与 13 条清单；用户正因上下文长度关会话，新会话继续此对话）。
2. 用户拍板后（沿 E4 先例）：
   a. 定稿草案（全文移植到驱动 docstring）；
   b. **先查 B 臂可行性**：无门控 LLM agent 路径（旧栈自由规划风格，E3 ungated 同构）当前代码是否仍可用——`planning/router.py`、`llm_critic.py` 等已删；不可用则设计等价替代并报告用户；
   c. 实施 **S0 机制验证**（1 靶点 × C 臂 × 3 重复，判据：约束识别 100% / 输出格式完整 / R2 稳定性 τ≥0.8 / 无崩溃）→ 阶段判定书 → 用户确认；
   d. **S1 小规模**（5 靶点 × 3 臂，判据与 S2 同指标同阈值：端到端通过率 C≥0.8 且 C≥A+0.4 / 约束满足率 C≥0.9 / R1–R4 与 D1–D3 全过 / 方向性 ≥4/5）→ **任一不过 → 报告用户，不自动进 S2**；
   e. **S2 全矩阵**（20 靶点，配对 McNemar p<0.05 或 95%CI 不含 0）→ 最终判定书 GO/NO-GO；
   f. S1/S2 启动前在 `MODEL_API_USAGE.md` 预登记 E5 LLM 调用（C 臂 3–5 次/基因，若采纳迭代修复则 5–9；B 臂 2–4），跑完当天更新实测。
3. E5 判据不过时的备选动作（草案 §9）：修机制 / 调整约束阈值 / 放弃——由用户定，勿自作主张。

## 6. 工程纪律（用户既定规则，必须遵守）

1. **git 操作必须先问用户**（commit/push/reset）。
2. **pytest 基线 649 passed, 1 skipped**；改代码后必跑全量 `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -q`（约 25s）。
3. 简洁优先；锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项若需改动，先呈用户**（E5 草案未拍板前一字不改）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程；**命令须同条内 cd rna_agent_system &&，前台检查用绝对路径**。
7. 决策文化：重大路线由用户决定，助手给建议与证据；论文 Nat Methods 直冲，不做提前预注册公开。

## 7. 关键指针

- **E5 草案 v2**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`（§13 未决问题 13 条）。
- **论文**：`relevant_references/mRNAdesigner ... .pdf`（提取文本 `/tmp/mrnadesigner.txt`；PDF 图像无法直接显示，pdftotext 可读）。
- 上一交接：`experiments/results/HANDOFF_2026-08-07_E5DRAFT_READY.md`（E5 v1 要点、E4 判定书摘要、20 靶点运维耗时表指针）。
- E4 判定书：`experiments/results/e4_full_summary.json`；E3 预注册：`experiments/run_e3_gated_vs_ungated.py` docstring。
- 门控组件（E3 复用）：`agent_core/calibrated/decision_gate.py`（确定性、无 LLM）、`campaign_runner.py`、`self_model.py`。
- 全长 mRNA 工作流：`agent_core/workflows/full_length_mrna_design.py`（GEMORNA 5'UTR MRL/3'UTR 稳定性、LinearDesign λ 0–20、LinearFold/GC/Junction/二级结构评估器——零新模型）。
- 20 靶点：`data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/`。
