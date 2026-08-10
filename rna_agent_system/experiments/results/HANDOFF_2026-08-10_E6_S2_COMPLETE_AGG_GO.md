# HANDOFF 2026-08-10 — E6 S2 已完成(18/18),聚合判定 **GO**(主终点过,辅终点未过已披露);剩余收尾

> **重要**:本会话结束后将换用**其他模型/编程 agent** 继续,其**不知道**本仓库的
> 记忆文件、默认配置与历史约定。本 HANDOFF 已把记忆/配置/纪律/进度全部内联自包含,
> 下一会话**先读本文档 + 下述必读文件**,再动手。

**上一会话:** HANDOFF_2026-08-09_E6_S2_RUNNING.md(S1 GO;S2 运行 1/18 时转交)
**本会话:** 监控 S2 → 修第 4 处崩溃 bug(request_generate 审计枚举)→ 重启 → S2 完成 18/18 → 聚合复算判定 **GO**(主终点过,辅终点未过披露)→ 本 HANDOFF
**下一会话目标:** 收尾四件事(见 §7):MODEL_API_USAGE 实测、复现锚点核查、收尾 HANDOFF、向用户汇报(GO + 披露 + 归因)

---

## 0. 当前状态(2026-08-10,S2 已完成,无运行中实验)

- **S2 主实验已跑完**:18/18 靶全部 success=True,写入 `results/e6_s2_runs.jsonl`(18 行);进程已正常退出(pid=1816657),**无后台进程需监控**。
- **聚合判定(本会话已复算,结果落盘)**:`results/e6_s2_verdict_aggregated.json` = **GO**。复算脚本 `experiments/recompute_e6_s2_verdict.py`(逻辑与 `run_s2` 判定段逐行一致)。
- **判定书 `e6_verdict_s2.json`(267KB)是逐靶覆盖的单靶态**(最后一个靶 Transferrin),中间 NO-GO 不算数;**最终判定以上述聚合复算为准**(S1 同款语义)。
- **本会话修的崩溃 bug(第 4 处)**:`request_generate` 审计事件不在 `AuditEvent.event_type` 字面量枚举 → 已按 extend-only 先例补入(见 §5)。崩溃日志备份 `/tmp/e6_s2_run_crash_request_generate.log`。

## 1. S2 聚合判定结果(复算,§20 双终点口径)

| 判据 | 结果 | 实测 |
|---|---|---|
| 主终点 McNemar(C vs A, n=54) p<0.05 | ✅ | **p=1.86e-09**(discordant b=30, c=0, 全单向) |
| 主终点 c_e2e_gene ≥0.8 | ✅ | **1.0** |
| **endpoint1(主)** | ✅ | **True** |
| 辅终点 Wilcoxon(C vs A) p<0.05 | ✅ | p=1.65e-07 |
| 辅终点 质量判据(R1&R4&R3&D1&D2&D3 全过 + E14 ge_3) | ❌ | R1/R4=True;R3 全过=False;D1/D2/D3 全过=False;ge_3 全过=False |
| 辅终点 约束率 C≥0.9 | ✅ | True |
| **endpoint2(辅)** | ❌ | False |
| **go_no_go** | **GO** | 主过即 GO |
| 披露 | ✅ | `endpoint2_not_passed_disclosed=True`(主过辅不过,§20 要求披露) |

**quality 败项归因**(复算脚本同样输出):败项几乎全由 **HER2 单靶**贡献(HER2:p0-2 的 D1/D2/D3 全挂 + 臂级 R3=false + E14 ge_3=false)。HER2 探测结果 `feasible=[] tier=0 plan_mode=degrade`(该靶在本实验物种上下文中**零可行 λ 档**,格 0 cells,走降级路径——非 E6 方法缺陷,与 E5 时代同类靶困境一致)。零星失败:Albumin:p1 D3、Beta_galactosidase:p0/p1 D2、SARS-CoV-2_Spike_WT:p0 D1/D2/D3。主终点 30:0 不受影响。

## 2. E6 实验背景(拍板/判据,来自 PREREG §20 与已批准计划)

**E5 S1 整体 NO-GO** 归因 = R3(A1AT/Insulin λ 档距不足)+ D1(Insulin CDS 趋同)+ D2(GFP λ 档覆盖不足)→ **E6 方法学级改进**:约束导航从"选择层"下沉到"生成层",四组件统一 FAD 生成格:
- 组件 1 可行性优先自适应生成(探测 PROBE_LAMBDAS={0,2,8,20,50},5 次 LD/靶;动态档序)
- 组件 2 画像正交方向轴(cai_max/frac/cai_floor;拍板②:frac 半倾斜混合 mix_p=0.5 + 接受重试 CAI∈[0.88,0.92];floor 目标 **0.85**;硬约束 CAI_MIN 0.8 与分离阈值 0.05 不变)
- 组件 3 多样度扩展器(密度 0.10 标定;pairwise ≥3%)
- 组件 4 CodonContextResolver(物种上下文显式失败;18/18 host 表命中)

**三臂分层池(拍板①)**:A/B 臂 = 静态配方池(λ{0,1,4,10}×9UTR),C 臂 = 导航生成格;gate_action 第 5 道闸 request_generate(B≤1/C≤2,LD 总 C≤3/基因)。
**D2 复合判据(拍板①)**:D2 = D1 ∧ 交付内 CAI 跨度 ≥0.05;C 臂 λ 档覆盖由 E14_gen_lattice 格级声明(格内 LD 档数 ≥3)承担。
**R3 轴内语义(拍板③)**:R3 top-1 按轴锁定交付取,分离由构造保证(三轴 CAI 1.0/0.90/0.85 两两差 ≥0.05)。

**S2 双终点(§20)**:主 = per-profile JCD-pass(e2e∧D1∧D2∧R3)配对 McNemar(C vs A, n=54) p<0.05 且 c_e2e_gene≥0.8;辅 = 连续复合得分(0.4×e2e+0.2×约束率+0.2×D1/D2+0.2×R3)配对 Wilcoxon(C vs A) p<0.05 且 质量判据 且 约束率 C≥0.9;go = 主或辅任一过;主过辅不过须披露。**S2 为 A/C 双臂**,C vs B 仅披露不参与 gate。

**S1 判定(上上会话)**:GO,六项全过(判据书 v8 六项:① e2e C≥0.8 且 C≥A 平局算过 ② 约束率 C≥0.9 ③ R1–R4 ④ D1–D3 ⑤ 方向性 C≥A 4/5 ⑥ 预算记录)。S1 实测 LLM **A0/B8/C15**(预登记 35–65 内),LD 21(探测 1+静态 20+C 0)。

**探针结论(P1–P5,2026-08-09,产物 /tmp/e5_probe_carm/e6_*)**:P1 可行档 5 靶全 ≥3;P2 修 3 个生成层缺陷后 R3 分离/D1 全 True;P3 密度 0.10;P4 18/18 host;P5 功效预演 McNemar p=0.00024。**E5 已证伪路径勿重复**:A 分支(λ 网格扩展修 R3)、C 分支(GEMORNA 30→60)、B1 补救、λ 加档修 D1;IL-2 探针勿重跑。

## 3. 环境与配置(新 agent 必须知道,原记忆/配置不随会话迁移)

- **仓库根**(绝对路径,一律用绝对路径):`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`
- **工作目录**:`.../RNA_real_agent/rna_agent_system`(python 代码所在);运行实验先 `cd` 到该目录
- **Python**:conda 环境(默认 `python3` 即含 scipy/pydantic 等;驱动以 `python3 experiments/run_e6_gennav.py` 运行,PATH 已就绪)
- **微服务(勿杀)**:8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 若需重启须带 `PYTHONPATH=<rna_agent_system>`;S2 运行日志显示 preflight 3 服务健康
- **测试基线**:pytest 696 passed, 1 skipped, 30 deselected(含 `tests/test_gennav_core.py` 47 项);pytest.ini 默认排除 integration/live_llm/slow
- **git**:当前分支 main,工作树有大量未提交修改(含 .kimi/prompts/* 与 BMC_Framework_Design_Notes.md 等删除项,系历史清理,未入库)。**git 操作先问用户**,本地产物(PREREG/MODEL_API_USAGE/判定书/HANDOFF 等)在 .gitignore:24 不入库
- **复现锚点**:LD 缓存键 = `{target}|{λ:.1f}|26308b892d84`(E. coli CSV 内容 hash,跨靶统一);GEMORNA CDS 缓存 e6←e5 setdefault 零新调用;UTR 复用 e5_gemorna_cache.json

## 4. 记忆文件内容(原 Claude 记忆 4 条,新 agent 需继承)

1. **MrnaCdsDesignWorkflow 接口锁定 v1.0.0**(2026-05-10,29 测试全绿):改 `agent_core/workflows/mrna_cds_design.py` 前先读 `docs/INTERFACE_LOCKS.md` §8;禁改输入模型字段/评分公式(total_score=-mfe+codon_count*log(CAI))/required_capabilities/CriticDiagnosis 模式/adjustable_params/pipeline 顺序;改后跑 `pytest tests/test_mrna_cds_design_comprehensive.py -v --live-llm`
2. **SirnaDesignWorkflow 接口锁定 v1.0.0**(2026-05-13,29 测试全绿):改 `agent_core/workflows/sirna_design.py` 前读 INTERFACE_LOCKS.md §10;禁改输入字段/评分(rank 制)/required_capabilities/Critic 模式/adjustable_params/pipeline;改后跑 `pytest tests/test_sirna_design_comprehensive.py -v --live-llm`
3. **SgRnaDesignWorkflow 接口锁定 v1.0.0**(2026-05-13,40 测试全绿):改 `agent_core/workflows/sgrna_design.py` 前读 INTERFACE_LOCKS.md §11;禁改输入字段/score_sgrna_candidate()/required_capabilities/Critic 模式/adjustable_params/pipeline;改后跑 `pytest tests/test_sgrna_design_workflow.py tests/test_sgrna_design_e2e.py -v`
4. **E6 探针记忆已过时**("探针完成待拍板"):拍板已于 2026-08-09 完成(PREREG §20),以本文档 + PREREG §20 为准

## 5. 本会话修改(4 处修复中的第 4 处;其余 3 处见 HANDOFF_2026-08-09_E6_S2_RUNNING.md §1.4)

- `agent_core/calibrated/models.py:161-163`:`AuditEvent.event_type` extend-only 追加 `"request_generate"`(先例 = E5 的 `lineardesign_extra`;旧 11 类型零改动;py_compile + 冒烟通过)
- 崩溃现场:HANDOFF 上一会话 3 处修复(`paired()` 缺臂早退 / `cx_cb/cy_cb` guard / endpoint1/2 按 §20 改口径)均在 `experiments/run_e6_gennav.py`,S2 重启后未再崩

## 6. S2 运行数据速览(供汇报参考)

- 18 靶顺序:FULL_TARGETS;除 HER2 外 17 靶均 tier≥3 正常模式;HER2 降级路径(0 格)
- 各靶 lattice_plan 快照在每靶 record 的 `pool.lattice.lattice_plan`(feasible_gears/gears_selected/rank_map/e14_declaration)
- 逐靶静态池 36 candidates(12–27 过),格 126–288 cells(114–288 过);格构建 72–253s
- LLM 实测次数(LD 次数)待下会话从 `arm_results` 统计(预登记口径:S2 18 基因 × C 臂 5–9 次 ≈ 90–162;LD 探测 5/靶 + 细化 0–2 + C 臂 ≤3 ≈ 90–160)

## 7. 下一步(收尾四件事,按序)

1. **汇报用户 S2 判定**:GO(主终点 McNemar p=1.86e-09,30:0 全单向;c_e2e_gene=1.0)+ 辅终点未过披露(endpoint2_not_passed_disclosed)+ quality 归因(HER2 降级路径一票否决 + 3 靶零星失败)。依据 `results/e6_s2_verdict_aggregated.json`。
2. **MODEL_API_USAGE.md §2 E6 行实测更新**:S1 已实测(A0/B8/C15,LD 21)可先行写入;S2 按判定书 observed + `e6_s2_runs.jsonl` 每靶 arm_results 统计 LLM/LD 实测数填(预登记 90–160 对照)。改动须同时同步 PREREG §20 口径(只增实测,不改预登记判据)。
3. **复现锚点核查**:e6_ld_cds_cache.json(现 44 键,键含 csv_hash 26308b892d84)+ e6_gemorna_cds_cache.json(150 键)+ 格 lattice_plan 快照(在 runs.jsonl 各靶);UTR 复用 e5_gemorna_cache.json;E. coli CSV hash == 26308b892d84。
4. **写收尾 HANDOFF_*.md**(S2 判定完成版,含双终点实测表)并同步/核对 CHANGELOG 等。

## 8. 纪律(逐条遵守)

- git 操作先问用户;判据/阈值/处置变更必须用户拍板 + 同步 PREREG §20 与 MODEL_API_USAGE §2
- 一律绝对路径;仓库根 `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`
- 勿杀微服务(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 重启须带 PYTHONPATH=rna_agent_system)
- **勿动旧链路(零改动)**:run_e5_constraint_nav.py / codon_tables/CSV / sequence_utils.py / mrna_cds_design.py / lineardesign_service
- E5 已证伪路径勿重复:A 分支、C 分支(GEMORNA 30→60)、B1 补救、λ 加档修 D1;IL-2 探针勿重跑
- e5_s1_round3_archive/ 与 e5_s1_r2_rnarl_down_archive/ 勿删;e5_s1_r4.log / e5_s1.log / e5_s1_r5.log 勿覆盖
- 探针产物只读(/tmp/e5_probe_carm/e6_* 是 E6 运行缓存种子)
- 每个阶段写 HANDOFF_*.md

## 9. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/run_e6_gennav.py | E6 驱动(未跟踪);s0/s1/s2 + --resume;run_s2 判定段 :1855-1949;本会话未改(修复在 models.py) |
| experiments/recompute_e6_s2_verdict.py | **本会话新建**:S2 聚合复算脚本(18 条复算,输出 results/e6_s2_verdict_aggregated.json) |
| agent_core/generation/gennav_core.py | E6 组件 1–4 纯函数(未跟踪) |
| agent_core/calibrated/models.py | **本会话修改**:AuditEvent 枚举 +"request_generate"(:161-163) |
| tests/test_gennav_core.py | 47 项测试(未跟踪) |
| experiments/results/e6_s2_runs.jsonl | S2 运行记录 **18 条(聚合判定依据)** |
| experiments/results/e6_s2_verdict_aggregated.json | **本会话产出:聚合判定 = GO** |
| experiments/results/e6_verdict_s2.json | S2 判定书(逐靶覆盖,末条 Transferrin 单靶态;勿当最终) |
| experiments/results/e6_s1_runs.jsonl / e6_verdict_s1.json | S1 记录 5 条 / 判定书(S1 GO 已定) |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | §20 = E6 决议注记(拍板①②③ + 判据书 v8 + S2 双终点口径) |
| experiments/results/MODEL_API_USAGE.md | §2 E6 行(预登记;S1 实测 A0/B8/C15、LD 21 待写入;S2 实测待统计) |
| /tmp/e6_s2_run.log | S2 运行日志(重启后) |
| /tmp/e6_s2_run_crash_request_generate.log | 本会话崩溃日志备份 |
| /tmp/e5_probe_carm/e6_* | 探针产物/缓存种子(只读) |
| /root/.claude/plans/gleaming-honking-ladybug.md | E6 已批准计划(执行依据) |
| rna_agent_system/docs/INTERFACE_LOCKS.md | 接口锁定文档(§8/§10/§11 对应三个 workflow) |
