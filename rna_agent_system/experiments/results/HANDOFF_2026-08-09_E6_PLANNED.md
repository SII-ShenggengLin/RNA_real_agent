# HANDOFF 2026-08-09 — E6「约束导航生成器」规划完成,用户 4 项拍板,计划已批准,待探针先行实施

**上一会话:** HANDOFF_2026-08-09_E5_REPORTED_MERGED.md(E5 收尾:合并推送/GFP D2 接受/报告定稿)
**本会话:** 状态确认全通过 → 3 代理调研(判据链/生成方法层/智能体策略层)→ Plan 代理设计 → 用户 4 项拍板 → 计划批准
**下一会话目标:** **探针先行实施 E6**(P1–P5 探针 → E6 S0/S1/S2),按本 HANDOFF 附带的提示词执行

---

## 0. 当前状态(2026-08-09,会话关闭时)

- **git**:main = b6dad08,与 origin/main 同步;工作树 418 行非 E5 改动保持原样(未动)。
- **pytest**:649 passed, 1 skipped, 30 deselected(22.81s,与基准一致)。
- **无实验在跑**。jupyter(8088)+ GPU_get.py(pid 22923)在跑;8003–8020 本容器无监听(外部映射可能,未排查)。
- **计划已批准**(用户 ExitPlanMode 批准):`/root/.claude/plans/gleaming-honking-ladybug.md` 是 E6 完整实施计划(本 HANDOFF 仅摘要,执行细节以计划文件为准)。
- **会话原因**:上下文长度告警,用户关闭本会话,新会话继续实施。

## 1. 本会话落地

1. **状态确认**:全部符合预期(见 §0)。
2. **背景调研**(3 个 Explore 代理 + 精读 E5_REPORT):
   - 全部剩余 NO-GO 因子(R3 档距不可达 / D1 λ 饱和趋同 / D2 可行档不足 / S2 显著性平局)归因于**生成方法层结构性**,共同根源 = **生成与选择分离**(agent 只能在固定配方池上被动选择)。
   - 关键接缝已核实:LAMBDAS=(0,1,4,10)(run_e5:353)、LAMBDA_RANK :360、W_LAMBDA=0.8 :441、`_ld_codon_usage_path` 静默回退 :742-750、build_pool :753-932、gate_action :1616-1657、探针工具 probe:122-307、tools.py:1177 加权选择器。
3. **E6 方法设计**(Plan 代理):四组件统一为 **FAD 生成格**——①可行性优先自适应 λ 探测(动态档序,开采 GFP λ50)②画像正交方向轴(cai_max/frac/cai_floor,纯本地派生)R3 构造性分离 ③多样度扩展器(全 CDS 同义多样化,生成时 pairwise≥3%)修 D1 ④物种密码子上下文组件化(B0 升格,显式失败替代静默回退)。**全部新代码入新文件,旧链路(r5)逐字节不动**。
4. **用户 4 项拍板**:①三臂分层池(A/B=静态配方池,C=导航生成池)②S2 双终点(JCD-pass McNemar 主 + 连续复合得分 Wilcoxon 辅)③Insulin D1「已接受」撤销,组件 3 修复 ④新方法命名 **E6 新实验**(与 E5 历史隔离)。
5. **计划批准**:E6 实施计划已写入 `/root/.claude/plans/gleaming-honking-ladybug.md` 并经用户批准。

## 2. 关键文件索引

| 文件 | 说明 |
|---|---|
| `/root/.claude/plans/gleaming-honking-ladybug.md` | **E6 完整实施计划(已批准,执行依据)** |
| E5_REPORT_2026-08-09.md / PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | E5 报告与预注册(§19 已有全部 E5 决议) |
| experiments/run_e5_constraint_nav.py | E5 驱动(**零改动**,接缝参照与纯函数复用源) |
| experiments/probe_e5_generation_optimization.py | 探针方法论模板(make_mini_pool/sim_r3/kazusa_csv_for_species) |
| agent_core/tools.py(:1177-1310)/ sequence_utils.py(:180-312) | 加权选择器 / codon 表与 CSV 导出 |
| e5_verdict_s1.json / e5_s1_runs.jsonl / e5_s1_r5.log | E5 判定书/证据(勿覆盖/勿删) |

## 3. 下一会话动作(按序)

1. **读计划**:`/root/.claude/plans/gleaming-honking-ladybug.md`(实施细节全在计划文件)。
2. **探针先行(硬约束)**:写 `experiments/probe_e6_gennav.py`,跑 P1–P5(可行性区间/方向轴 R3/多样度扩展器/物种上下文/S2 功效预演),产物写 `/tmp/e5_probe_carm/e6_*`;**探针全部出结论前不落实验驱动代码**。
3. **实现**:`agent_core/generation/gennav_core.py`(组件 1–4 纯函数)→ `experiments/run_e6_gennav.py`(分层三臂+判定书)→ `tests/test_gennav_core.py`。
4. **同步文档**:PREREG 追加 §20「E6 决议注记」+ MODEL_API_USAGE §2 新增 E6 行(本地不入库),然后 E6 S0(Insulin×C×3)→ S1(5 靶×3 臂)→ S2(18 靶,双终点)。
5. **pytest 基线**:保持 649 passed + 新增 test_gennav_core 全绿。

## 4. 纪律重申(与前会话一致)

- git 操作必须先问用户;判据/阈值/处置变更必须拍板并同步 PREREG 与 MODEL_API_USAGE。
- 工作目录可能被外部切换 → 一律绝对路径(仓库根 `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`)。
- 勿杀微服务(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 重启须带 PYTHONPATH=<rna_agent_system>)。
- **勿动旧链路**:run_e5_constraint_nav.py / codon_tables/CSV / sequence_utils.py / mrna_cds_design.py / lineardesign_service 零改动(保护 r5 复现与 INTERFACE LOCK);新代码全入新文件。
- e5_s1_round3_archive/ 与 e5_s1_r2_rnarl_down_archive/ 勿删;e5_s1_r4.log / e5_s1.log / e5_s1_r5.log 勿覆盖;IL-2 探针勿重跑。
- E5 已证伪路径勿重复:A 分支(λ 网格扩展修 R3)、C 分支(GEMORNA 30→60)、B1 作为补救、λ 加档修 D1。
