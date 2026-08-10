# HANDOFF 2026-08-08 — E5 判据① v7 拍板落地、S1 重跑(r4)进行中(3/5 完成,EPO 靶判定书 GO!)

**上一会话:** HANDOFF_2026-08-08_E5_B1_RELAXED_V6_PROBES_RUNNING.md(探针 v6 在跑)
**下一会话目标:** 等 S1 重跑(r4)全部完成(进程 2677963 退出)→ 汇总 5 靶判定 → 更新 MODEL_API_USAGE 实测 → PREREG §18.4 补 S1 结果 → 呈报用户拍板下一步(是否启动 S2)。

---

## 0. 当前状态(2026-08-08 ~17:55,会话关闭时)

- **S1 重跑(r4)正在后台跑**(setsid pid **2677963**,17:13 启动,已 41min):`cd rna_agent_system && setsid nohup python experiments/run_e5_constraint_nav.py s1 > experiments/results/e5_s1_r4.log 2>&1 &`(**勿覆盖 `e5_s1.log`**)。
  - **已完成 3/5 靶**:A1AT(17:32,单靶判定 NO-GO)、Insulin(17:39,NO-GO)、**EPO(17:5x,单靶判定 GO!)**——EPO 是 5 靶中唯一 R3=True 的靶,在 v7 判据下 6 判据全过,完整达成 GO 形态,验证判据①修复后系统在该靶端到端达标。
  - **GFP ⏳ 池构建中**;IL-2 ⏳ 待跑。预计 ~15-20min 全部完成。
  - 完成标志:**进程 2677963 退出**(main 循环结束后打印 `E5 s1: N cell(s) failed verdict -> [...]`)。完整 5 靶记录追加在 `experiments/results/e5_s1_runs.jsonl`(已 3 条:17:32/17:39/17:5x)。
- **判定书语义(重要,既有设计)**:main 逐靶调用 `run_s1([target_id])` → `e5_verdict_s1.json` 被每靶覆盖写,**最终只保留 IL-2(最后靶)的单靶判定书**。第 3 轮(round3_archive 内)同样如此。**完整 5 靶判定要看 `e5_s1_runs.jsonl` 最后 5 条记录** + `e5_s1_r4.log` 每靶的 `[s1] verdict` 行。
- **微服务:** S1 日志确认 3 service healthy(8004/8008/8015 等)。勿杀任何微服务。
- **git:** 工作树大量未提交修改(自 fd61126 checkpoint)。git 操作必须先问用户。

## 1. 本会话已完成(代码已改、测试全绿、文档已同步)

### 1.1 探针 v6 4 靶全部完成(`e5_probe_carm_4targets_v6.log`,ALL_PROBES_DONE 已确认)

| 靶点 | pool n_pass | R3 | e2e×3 | R1/R4 | D1 | D2/D3 | constraint_rate | rc / llm_calls |
|---|---|---|---|---|---|---|---|---|
| A1AT | 60/315 | False(λ档距 1/0/1 均<2) | True×3 | 全 True | True(0.0207) | True | 1.00 | rc=0 / 2 |
| Insulin | 92/315 | False(同 ld4/ld10 模式) | True×3 | 全 True | **False(0.0082<2%)** | True | 1.00 | rc=0 / 1 |
| EPO | 306/315 | **True**(ld1/ld10/ld4,档距 3/2) | True×3 | 全 True | True(0.0415) | True(D2 ranks[1-5]) | 1.00 | rc=0 / 2 |
| GFP | 0/315 | —(空交付) | — | — | — | — | — | rc=2 预期(能力结论) |
| IL-2(v5 既有) | 192/315 | **True**(ld1/ld10/ld4,恰一对档距 2) | True×3 | 全 True | True | True | 1.00 | rc=0 / ~1-2 |

探针产物审计在 `/tmp/e5_probe_carm/e5_audit/`(s1_A1AT/Insulin/EPO/GFP.jsonl)。IL-2 探针勿重跑。

### 1.2 判据① v7 拍板(2026-08-08,用户委托按实验结果自决)

- **用户答复 AskUserQuestion:「你自己根据实验结果决定」** → 选定 **e2e 改「C≥0.8 且 C≥A(平局算过)」**。
- 依据:(a) 4/5 可交付靶 constraint_rate 全 1.00、e2e 两臂 1.00 平局结构性成立(严格 C>A 不可达);(b) GFP 0/315 反例否定「池通过数<5 + C 臂自救」路径(空交付直接崩溃 rc=2);(c) 判据①本意「C 臂不劣于 A 臂」;(d) 真实质量信号在 crit3 层。
- 实现:`run_e5_constraint_nav.py` run_s1 crit1 `>`→`>=`;判定书 key `e2e_pass_C_ge_0.8_and_C_ge_A_ties_pass`。
- **连带修复**:`evaluate_delivery` D3 空交付兜底(GFP 0-pass 空池 `max()` 崩溃 → 空列表极差记 0.0、D3=False;该靶记失败不崩全盘)。空交付语义:e2e=False、constraint_rate=0.0、D1-D3/R4=False,计入 crit1 分母。
- 冒烟测试 PASS + **pytest 649 passed, 1 skipped**(全绿,与基线一致)。

### 1.3 MODEL_API_USAGE.md §2 E5 行已更新

- **v6 探针实测已追加**:LLM **5 次**(A1AT 2 + Insulin 1 + EPO 2 + GFP 0)+ LD 8014 **16 次**(4 靶×4λ)+ RNARL 8008 **4 次** + GEMORNA 8004 **0 次新增**(120 次调用全命中缓存 idx 0–29)+ LinearFold 8015 池级 fold 本地。
- S2 预登记(LLM ~126–234 次、LD 72 + RNARL 18 + GEMORNA 468)已在现成行,无需重复。

### 1.4 PREREG §18.4 已写最终决议

证据表 + 决议 4 项(口径/依据/连带修复/判定语义)+ S1 重跑记录。**S1 重跑完成结果待 §18.4 补记**(见下一步)。

## 2. 下一会话执行步骤(按序,不得跳步)

1. **等 S1 重跑(r4)全部完成**:`ps -p 2677963` 确认退出(或 `tail experiments/results/e5_s1_r4.log` 出现 `E5 s1: N cell(s) failed verdict` 汇总行)。未完成则等(~15-20min)。
2. **汇总 5 靶判定**:
   - `e5_s1_r4.log` 每靶的 `[s1] verdict` 行(判定书被覆盖,只有这些行 + runs.jsonl 是完整证据);
   - `e5_s1_runs.jsonl` 最后 5 条(success、evaluations);
   - 最终 `e5_verdict_s1.json` = IL-2 单靶判定书(既有设计,勿误读为全靶)。
   - **预期(探针预判)**:crit1/crit2/crit5 全过;crit3(R3 全靶)不过(A1AT/Insulin R3=False);crit4(D1-D3 全靶)不过(Insulin D1=False)→ 整体 NO-GO;唯一例外 EPO 靶单靶 GO(已验证)。**GFP 以空交付失败记录,不崩溃**(D3 兜底已生效)。
3. **更新 MODEL_API_USAGE.md §2 E5 行**:追加 S1 重跑(r4)实测(LLM 调用数等,从 runs.jsonl 汇总;判据① v7 口径注记;`e5_s1_r4.log` 已含每靶 verdict)。
4. **PREREG §18.4 补记 S1 重跑结果**(判定书路径、5 靶逐靶结果、EPO GO 信号)。
5. **呈报用户**:5 靶判定汇总表 + EPO GO 信号 + 整体 NO-GO(归因:R3 2/5 + Insulin D1)→ **用户拍板下一步(是否启动 S2 全矩阵;或先做生成方法优化——GFP 0-pass 能力结论是系统优化项,2026-08-08 已拍板不降阈值)**。
6. 若拍板启动 S2:`python experiments/run_e5_constraint_nav.py s2`(18 靶 × 3 臂,LLM ~126-234 次,LD 72+RNARL 18+GEMORNA 468 已在 MODEL_API_USAGE 预登记;日志用新文件勿覆盖现有;S2 预注册见 driver docstring)。

## 3. 纪律(继续遵守)

- **git 操作必须先问用户**(工作树大量未提交修改)。
- **判据/阈值变更必须呈用户拍板**(AskUserQuestion),并同步 PREREG。
- 工作目录可能被外部切回项目根:**一律用绝对路径,或在命令内 `cd rna_agent_system &&`**。
- **勿杀微服务**(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py)。RNARL 8008 重启必须带 `PYTHONPATH=<rna_agent_system>`。
- 探针产物写 `/tmp/e5_probe_carm/`;`e5_s1_round3_archive/` 勿删;`e5_s1_r4.log` 勿覆盖 `e5_s1.log`;探针日志 `e5_probe_carm_4targets_v6.log` 勿覆盖旧版。
- **IL-2 探针勿重跑**。
- 判定书 `e5_verdict_s1.json` 会被每靶覆盖(既有设计),完整证据以 runs.jsonl + r4 日志为准。

## 4. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/run_e5_constraint_nav.py | 主 driver(v6 阈值 L377/385:GC 30.0/80.0 + CAI_MIN 0.8;v7 判据① crit1 C≥A 平局算过 L2016;D3 空交付兜底 L1101 区) |
| experiments/results/e5_s1_r4.log | **S1 重跑日志(在跑,勿覆盖 e5_s1.log)** |
| experiments/results/e5_s1_runs.jsonl | 5 靶完整记录(第 3 轮 5 条 + 本次 5 条追加) |
| experiments/results/e5_verdict_s1.json | 判定书(最终 = IL-2 单靶,既有设计) |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | §18.4 v7 判据①最终决议(已写;S1 结果待补记) |
| experiments/results/MODEL_API_USAGE.md | §2 E5 行 v6 探针实测已追加;S1 r4 实测待补 |
| experiments/results/e5_probe_carm_4targets_v6.log | 探针 v6 日志(已完成,勿覆盖) |
| /tmp/e5_probe_carm/ | 探针产物(audit 4 靶 + preflight 日志) |
| HANDOFF_2026-08-08_E5_B1_RELAXED_V6_PROBES_RUNNING.md | 上一会话 handoff(探针在跑时) |
