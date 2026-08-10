# HANDOFF 2026-08-10(收尾) — E6 战役关闭:S2 聚合判定 **GO**(双终点实测表内附);MODEL_API_USAGE 实测已写入;复现锚点核查通过

> **重要**:后续若换用**其他模型/编程 agent**,其**不知道**本仓库的记忆文件、默认配置与历史约定。
> 本 HANDOFF 自包含;先读本文档 + PREREG §20,再动手。

**上一会话:** HANDOFF_2026-08-10_E6_S2_COMPLETE_AGG_GO.md(S2 完成 18/18 + 聚合复算 GO,剩收尾四件事)
**本会话:** 复算验证 GO → 汇报口径确认 → MODEL_API_USAGE §2 E6 行实测更新(S0/S1/S2)→ 复现锚点核查(全部通过,1 处计数更正)→ 本收尾 HANDOFF
**E6 战役状态:** **关闭**。S0/S1 GO、S2 GO(主终点过,辅终点未过已披露)。无运行中实验,无待监控进程。

---

## 0. E6 最终判定(以聚合复算为准)

**S2 聚合判定 = GO**(`results/e6_s2_verdict_aggregated.json`,复算脚本 `experiments/recompute_e6_s2_verdict.py`,本会话已重跑验证,输出与落盘一致;18 条 `e6_s2_runs.jsonl` 复算,逻辑与 `run_e6_gennav.py::run_s2` 判定段逐行一致)。

### S2 双终点实测表(§20 口径)

| 判据 | 阈值 | 实测 | 结果 |
|---|---|---|---|
| 主终点 McNemar(C vs A, n=54) | p<0.05 | **p=1.86e-09**(discordant b=30, c=0,全单向) | ✅ |
| 主终点 c_e2e_gene | ≥0.8 | **1.0** | ✅ |
| **endpoint1(主)** | 两项全过 | — | **✅ True** |
| 辅终点 Wilcoxon(C vs A)复合得分 | p<0.05 | p=1.65e-07 | ✅ |
| 辅终点 质量判据 | R1&R4&R3&D1&D2&D3 全过 + E14 ge_3 | R1/R4=True;**R3=False;D1/D2/D3=False;E14 ge_3=False** | ❌ |
| 辅终点 约束率 C | ≥0.9 | True | ✅ |
| **endpoint2(辅)** | 三项全过 | — | **❌ False** |
| **go_no_go** | 主或辅任一过 | 主过 | **GO** |
| 披露义务(主过辅不过) | 须披露 | `endpoint2_not_passed_disclosed=True` | 已披露 |

### quality 败项归因(本会话从 runs.jsonl 逐靶复核,与上一会话一致)

- **HER2 单靶贡献几乎全部败项**:p0/p1/p2(expression/stability/balanced)D1/D2/D3 全挂 + 臂级 R3=false + E14 ge_3=false。根因:HER2 探测 `feasible_gears=[]`(λ 0–50 全档 0 UTR 过约束),`plan_mode=degrade`、格 0 cells,走降级路径——该靶在本实验物种上下文中**零可行 λ 档**,非 E6 方法缺陷(与 E5 时代同类靶困境一致)。
- **零星失败 3 靶**:Albumin:p1(stability) D3;Beta_galactosidase:p0(expression)/p1(stability) D2;SARS-CoV-2_Spike_WT:p0(expression) D1/D2/D3。
- 其余 14 靶 C 臂 quality 全项通过;主终点 30:0 不受败项影响。

**注意**:`e6_verdict_s2.json` 是逐靶覆盖的单靶态(末条 Transferrin),中间 NO-GO 不算数;最终判定以聚合复算 JSON 为准(S1 同款语义)。

## 1. MODEL_API_USAGE.md §2 E6 行实测(本会话已写入;只增实测,预登记判据文本零改动)

| 阶段 | LLM(DeepSeek v4-pro) | LD 8014 | 其他 |
|---|---|---|---|
| S0(Insulin×C×3rep) | **6**(2/rep;预登记 15–27) | **0 新调用**(探针种子缓存命中) | GEMORNA/RNARL 0 |
| S1(5 靶×3 臂,GO) | **23**(A0/B8/C15;预登记 ~35–65) | **21**(探测 1+静态 20 槽位+C 0) | request_generate 0;GEMORNA 0 新增 |
| S2(18 靶×A/C,GO) | **43**(A0/C43;1–4/基因,均值 2.4,低于预登记 5–9/基因,有利偏差) | **125 槽位计数**(探测/细化 52 新+静态 72 槽位+C 1;预登记 90–160 内;实际新服务调用 **61** = 52+8+C1,64 人源静态槽位命中 e5 survey 缓存) | request_generate **1**(HER2,闸 ≤2 内);GEMORNA 0 新增;RNARL 0 |

token 未逐条采集(usage_available=false,按 §1 剖面估算)。表头"最后更新"已改 2026-08-10。

## 2. 复现锚点核查(本会话全部实测通过)

- **E. coli CSV hash == 26308b892d84** ✅(现算 `export_codon_usage_csv` 字节 sha256[:12],与探针锚点一致;`run_e6_gennav.py::_verify_probe_csv_hash` 同口径)。
- **e6_ld_cds_cache.json = 80 键** ✅(全部键含 csv_hash 26308b892d84,0 例外)。组成:16 人源靶 × 探测 λ{2,8,20,50} = 64 + Beta_galactosidase/GFP × 8 λ{0,1,2,4,8,10,20,50} = 16(非人源靶静态池 λ{0,1,4,10} 无 e5 survey 缓存可命中,为新调用)。**更正:上一会话 HANDOFF §7.3 写"44 键"有误(疑为 S2 中途计数),实测 80 键,以此为准**;mtime 2026-08-09 23:07,S2 结束后未再变。
- **e6_gemorna_cds_cache.json = 150 键** ✅,与 `e5_gemorna_cds_cache.json` 逐键一致(0 缺失/0 值差异/0 新增)→ GEMORNA CDS setdefault 零新调用口径成立。
- **格 lattice_plan 快照 18/18 完整** ✅(每靶 `pool.lattice.lattice_plan` 含 feasible_gears/gears_selected/rank_map/e14_declaration;HER2 为 degrade 态 n_ld_gears=0、ge_3=false)。
- **UTR 复用 e5_gemorna_cache.json**(108 键,在库未动)✅。

## 3. 环境与配置(新 agent 必须知道)

- **仓库根**(一律绝对路径):`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`;工作目录 `.../rna_agent_system`。
- **微服务(勿杀)**:8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 重启须带 `PYTHONPATH=<rna_agent_system>`。
- **测试基线**:pytest 696 passed, 1 skipped, 30 deselected(含 `tests/test_gennav_core.py` 47 项);本会话收尾已全量复跑确认(27.14s,结果一致;本会话代码零改动,仅 results 文档)。
- **git**:分支 main,大量未提交修改(含 models.py AuditEvent extend-only +"request_generate"、新建 recompute_e6_s2_verdict.py;PREREG/MODEL_API_USAGE/判定书/HANDOFF 等本地产物在 .gitignore 不入库)。**git 操作先问用户**。

## 4. 纪律(持续有效)

- git 操作先问用户;判据/阈值/处置变更必须用户拍板 + 同步 PREREG §20 与 MODEL_API_USAGE §2。
- 勿动旧链路(零改动):run_e5_constraint_nav.py / codon_tables/CSV / sequence_utils.py / mrna_cds_design.py / lineardesign_service。
- E5 已证伪路径勿重复:A 分支、C 分支(GEMORNA 30→60)、B1 补救、λ 加档修 D1;IL-2 探针勿重跑。
- e5_s1_round3_archive/ 与 e5_s1_r2_rnarl_down_archive/ 勿删;e5_s1_r4.log / e5_s1.log / e5_s1_r5.log 勿覆盖;探针产物 /tmp/e5_probe_carm/e6_* 只读。
- 三个 workflow 接口锁定(MrnaCdsDesignWorkflow §8 / SirnaDesignWorkflow §10 / SgRnaDesignWorkflow §11),改前必读 docs/INTERFACE_LOCKS.md 并复跑对应测试。

## 5. 下一步(E6 已关闭;以下为战役外事项,由用户决定)

1. E6 结果写入 manuscript(E5 NO-GO → E6 方法学改进 → S1/S2 GO 叙事;辅终点未过 + HER2 降级路径须如实披露)。
2. HER2 类零可行档靶的处置(如需):属新一轮方法学问题,须重新探针 + 拍板,勿在 E6 判据上修补。
3. 未提交代码改动(models.py 枚举扩展 + recompute 脚本)是否入库——问用户。

## 6. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/run_e6_gennav.py | E6 驱动(未跟踪);run_s2 判定段 :1855-1949 |
| experiments/recompute_e6_s2_verdict.py | S2 聚合复算脚本(可重跑验证 GO) |
| experiments/results/e6_s2_runs.jsonl | S2 运行记录 18 条(聚合判定依据) |
| experiments/results/e6_s2_verdict_aggregated.json | **最终判定 = GO**(双终点实测见 §0) |
| experiments/results/e6_verdict_s2.json | 逐靶覆盖单靶态(勿当最终) |
| experiments/results/e6_{s0,s1}_runs.jsonl / e6_verdict_{s0,s1}.json | S0/S1 记录与判定书(均 GO) |
| experiments/results/MODEL_API_USAGE.md | §2 E6 行实测已写入(2026-08-10) |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | §20 = E6 决议注记(拍板①②③ + 判据书 v8 + S2 双终点) |
| experiments/results/e6_ld_cds_cache.json | LD 复现锚点缓存 **80 键**(键含 26308b892d84) |
| experiments/results/e6_gemorna_cds_cache.json | GEMORNA CDS 缓存 150 键(= e5 逐键一致) |
| agent_core/generation/gennav_core.py | E6 组件 1–4 纯函数(未跟踪) |
| agent_core/calibrated/models.py | AuditEvent 枚举 extend-only +"request_generate"(:161-163,未提交) |
| tests/test_gennav_core.py | 47 项测试(未跟踪) |
| /tmp/e6_s2_run.log / /tmp/e6_s2_run_crash_request_generate.log | S2 运行日志 / 崩溃日志备份 |
