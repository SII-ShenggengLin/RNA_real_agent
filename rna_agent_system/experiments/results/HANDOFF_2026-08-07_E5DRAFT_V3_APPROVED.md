# 交接提示词（2026-08-07：E5 定稿 v3 已拍板 + B 臂可行性已查 + 锚点缺失待拍板；无实验在跑，新会话从「锚点方案拍板」继续）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E4FULL_FINAL_RERUN.md`（E4 收尾）→ `HANDOFF_2026-08-07_E5DRAFT_READY.md`（v1）→ `HANDOFF_2026-08-07_E5DRAFT_V2_MRNADESIGNER.md`（v2）→ **本文件（定稿 v3 + 实施前核查）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`（所有命令在 `rna_agent_system/` 下执行并带 `PYTHONPATH="$(pwd):$PYTHONPATH"`；**Bash 工作目录跨调用持久——后台任务须同条命令内 `cd rna_agent_system &&`，git 命令带 `-C <项目根>`**）。

## 0. 一句话现状

**E5 预注册已定稿 v3（13 条未决问题全部拍板采纳 + 新增 §14 耗时预算与 LinearDesign 最小化）；B 臂可行性已核查完毕（旧栈不可用 → 等价替代 = 手写 agentic 循环，已报告用户）；实施中发现 §3.1 锚点前提不成立（20 靶点无自然参考 UTR），已呈用户待拍板（推荐方案①去锚点）；无实验在跑，无需监控/续跑——下一步 = 等用户拍板锚点方案，然后写 run_e5 驱动并实施 S0→S1→S2。**

## 1. 本会话已完成（勿重做）

1. **用户拍板（2026-08-07）**：E5 草案 §13 全部 13 条采纳 + 2 个实施细节认可（修复轮语义钉死、B 臂工具预算 ≤1 次 LinearDesign/基因）+ **耗时约束**（全量实验耗时可控、LinearDesign 调用最小化）。
2. **草案 → 定稿 v3**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md` 已更新为定稿 v3（状态行、§13 全部 ✅、§14 耗时预算）。拍板落定要点：
   - 约束矩阵 **C1–C8 + M1 共 9 条**（C5 改名「剪接共识序列过滤」非真实剪接预测；C7 全长最长茎 ≤30bp、C8 5'UTR 无 uAUG 新增并入）；
   - 档案指标 E1–E12（E7 pair ratio / E8 |ΔGC| / E9 ARE / E10 Kozak / E11 LD-λ 与效用 λ 区分 / E12 动机注记，全部零新模型）；
   - 修复轮 ≤2 轮/基因：**池内定向重选组合**（池已全量 eval，零新生成），仅 CDS 级约束（C2–C5/C7）池内无解时允许 ≤1 次/基因 λ 邻域重跑；C 臂 LLM 预算 5–9 次/基因；
   - 区域内权重规则：两指标 0.6/0.4、三指标均分；GO/NO-GO「任一过→GO」+ 披露细则（仅终点 1 过须披露终点 2 状态）；
   - D3 定义钉死：pair ratio 与最长茎均取 LinearFold 全长 fold 输出（与 C7 同次计算）。
3. **耗时预算（§14，基于 E4 264 场实测回归）**：LinearDesign 等线性生成调用 ~55–60s/次是单场耗时大头（nomem intercept ≈ 1297s ≈ 21 次生成；memory ≈ 361s ≈ 6 次）。E5 策略：池一次生成三臂共享（每靶点 4 λ = 4 次 LinearDesign），全矩阵 80–120 次 vs E4 ~2500+ 次（**↓ ~97%**）；C6/C7/D3 共用同一次 LinearFold 全长 fold。预算：**S0 ~30min（1 分片）/ S1 ~1.5–2h / S2 ~4–5h（2 分片）**，为 E4 46.3h 的 ~10%。每靶点池生成 ≈ 13min（LinearDesign 4×55s + GEMORNA 6 次 ~2min + 36–40 候选池级 eval × 全长 LinearFold ~10s）。
4. **B 臂可行性核查（结论已报告用户）**：旧栈 `planning/router.py`、`llm_critic.py`、`workflow_tools/` 已删 → **不可用**。现行栈 `LLMPlanner` 是一次性 JSON 规划（非 agentic loop）；E3 ungated = 2 次 LLM 调用。**等价替代（现行栈可落地，已获用户认可方向）**：驱动内手写 agentic 循环——LLM 每轮输出 JSON 动作（查池/选点/排序/修复/档案）→ 驱动执行 → 观察回填 → 再决策；B 臂不加 DecisionGate/约束 gate，C 臂加（复用 `agent_core/calibrated/`：DecisionGate/SelfModel/AuditTrail，见 §7 指针）。
5. **锚点核查（呈用户待拍板）**：20 靶点 JSON **均无自然 5'/3'UTR**（仅 protein_sequence）；`external_anchors/wt_cds/` 是野生型 **CDS**；疫苗锚点（BNT162b2/mRNA-1273）与 20 靶点无关；8/20 靶点（病毒/原核/报告基因：Spike/RSV/Zika/HIV/HPV/Influenza/GFP/Beta-gal）无自然人 UTR 可获取。已呈用户两方案：**①去锚点（推荐）**：池 = 4 λ CDS × 9 GEMORNA UTR 组合 = 36 候选，混合语义由 GEMORNA 三长度×两端承担，零新数据、三臂完全公平、不动 A 臂定义；**②wt CDS 作锚点**：5 CDS × 9 UTR = 45 候选，更贴"自然先验"但 wt 无 λ、A 臂规则选点复杂化。**等用户拍板 ①/②**。
6. **cai_species 细节（已定，无需再问）**：3/20 靶点 cai_species 为 E. coli（GFP/Beta_galactosidase 等），按 E4 先例取靶点 JSON 的 cai_species（非一律人类表），驱动 docstring 注明。
7. **workflow 接口核查（实施时直接复用）**：`FullLengthMrnaDesignWorkflow.generate_candidates(inp)`（design_tool="lineardesign" → CDS 由 `MrnaCdsDesignWorkflow` 生成 4 λ {0,1,4,10} × 9 UTR 组合 = 36 候选；CDS 评估推迟到 evaluate()）；`evaluate(candidate)` 是全量 eval（~30s，含 GEMORNA 预测/junction——**池级 eval 不要用**，仅交付级 5 候选用）；工具经 capability registry（`design_5utr/3utr_with_gemorna`、`design_mrna_cds_with_lineardesign`、`predict_rna_secondary_structure_with_linearfold`）；`score_full_length_mrna_candidate`（模块级函数，312 行附近）可查。CAI 工具：`compute_cai_for_cds_sequence`（species_key=cai_species）。

## 2. 待用户拍板（当前唯一阻塞项）

**锚点方案 ①（去锚点，推荐）还是 ②（wt CDS 作锚点）？**——已在上会话向用户呈表，用户因上下文长度关会话，**新会话第一步先向用户呈现此问题**（含 §1.5 的核查事实与两方案对比），拍板后按 §3 实施。

## 3. 下一步（锚点拍板后按序实施；拍板前不要动 E5 定稿与代码）

1. **写 E5 驱动** `experiments/run_e5_constraint_nav.py`（新文件；沿 E4 先例 `run_e4_learning_curve.py`：753 行单文件、docstring = 定稿全文移植；CLI 子命令 S0/S1/S2 + 靶点/臂过滤 + 判定书 JSON 输出）。
2. **实现模块**（可与驱动同文件或拆 `experiments/e5_support.py`，简洁优先）：
   - 约束判定器 C1–C8+M1（本地规则纯函数 + LinearFold：C6 起始区窗口「5'UTR 全长 + CDS 前 30nt」、C7 全长最长茎 ≤30bp；C7/E7-pair ratio/D3 共用同一次全长 fold）；
   - 池生成：`MrnaCdsDesignWorkflow`（design_tool="lineardesign"）4 CDS + GEMORNA 9 UTR 组合（+ 锚点按拍板）；池级 eval 只做约束判定 + 全长 LinearFold，**不调 workflow.evaluate**；交付级 5 候选再补 E3 junction/E4-E5 GEMORNA 预测/档案全量；
   - 三臂：agentic 循环骨架（§1.4 等价替代）；A 臂规则选点（过滤 → 画像权重 → 选 5 + U 排序，零 LLM 零工具）；B 臂无门控（≤1 次 LinearDesign/基因）；C 臂 DecisionGate + 约束 gate + 仲裁链 + 修复轮（池内重选，CDS 无解时 ≤1 次邻域 λ 重跑）；
   - R1–R4 / D1–D3 / U 函数 / 阶段判定书生成（S0 判据：约束识别 100% / 输出格式完整 / R2 τ≥0.8 / 无崩溃 + 单场耗时 ≤ 预算）。
3. **pytest 全量**：`PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -q`（基线 649 passed, 1 skipped，~25s）——改代码后必跑。
4. **MODEL_API_USAGE.md 预登记**（S1/S2 启动前）：C 臂 5–9 次/基因、B 臂 2–4 次；跑完当天更新实测。
5. **S0 机制验证**（1 靶点 × C 臂 × 3 重复；建议选无 OOM 风险小基因，如 Insulin/IL-2/GFP，避开 Zika/Factor_VIII）→ 阶段判定书 → **用户确认** → S1（5 靶点 × 3 臂，判据与 S2 同指标同阈值，任一不过报告用户不自动进 S2）→ S2（20 靶点，配对 McNemar）。
6. S0/S1/S2 全程预计：S0 ~30min、S1 ~1.5–2h、S2 ~4–5h（2 分片；服务串行处理请求勿超 2 分片并发）。

## 4. 工程纪律（用户既定规则，必须遵守）

1. **git 操作必须先问用户**（commit/push/reset）。
2. **pytest 基线 649 passed, 1 skipped**；改代码后必跑全量（约 25s）。
3. 简洁优先；锁定接口走 `docs/INTERFACE_LOCKS.md`（只增不改）。
4. **预注册项若需改动，先呈用户**（E5 定稿 v3 已拍板，改动须重新呈用户——锚点即为实例）。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`。
6. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程；命令同条内 `cd rna_agent_system &&`。
7. 决策文化：重大路线由用户决定，助手给建议与证据；论文 Nat Methods 直冲，不做提前预注册公开。

## 5. 关键指针

- **E5 定稿 v3**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`（§14 耗时预算、§13 全部 ✅）。
- **本会话已呈用户、待拍板**：锚点方案（§1.5 / 本文件 §2）——新会话第一步呈现。
- **E4 驱动先例**：`experiments/run_e4_learning_curve.py`（docstring = 完整预注册；CLI subprocess run_task_dict 模式；753 行）。
- **E3 门控组件（C 臂复用）**：`agent_core/calibrated/`：`decision_gate.py`（DecisionGate.review）、`self_model.py`（SelfModel.query/update）、`campaign_runner.py`（CalibratedCampaignRunner 七步流，可参考或绕开）、`audit_trail.py`。
- **全长 mRNA 工作流**：`agent_core/workflows/full_length_mrna_design.py`（generate_candidates 852 行、evaluate 993 行、score_full_length_mrna_candidate 312 行；工具：design_5utr/3utr_with_gemorna、design_mrna_cds_with_lineardesign、predict_rna_secondary_structure_with_linearfold）；CDS：`mrna_cds_design.py`（MrnaCdsDesignWorkflow，CAI 经 CAIEvaluator/cai_species）。
- **20 靶点**：`data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/`（JSON 仅 protein_sequence，无 UTR）；wt CDS：`data/benchmarks/external_anchors/wt_cds/`。
- **E4 运维耗时表**：`HANDOFF_2026-08-05_E4PREREGISTERED.md` §4（264 场实测，单臂全靶 ~14.2h）。
- **MODEL_API_USAGE.md**：`experiments/results/MODEL_API_USAGE.md`（E4 已更新实测 230 次）。
