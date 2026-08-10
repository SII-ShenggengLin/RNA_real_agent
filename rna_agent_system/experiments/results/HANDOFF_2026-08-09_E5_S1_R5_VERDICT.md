# HANDOFF 2026-08-09 — S1 r5 已收尾:判定书 NO-GO、对比完成、git 已提交、pytest 全绿

**上一会话:** HANDOFF_2026-08-08_E5_B0_LANDED.md(B0 落地 + S1 r5 启动)
**本会话:** 收集 r5(22:15 完成)→ 逐靶对比 r4 vs r5 → 归因分析 → git 提交(用户拍板)→ pytest 全绿
**下一会话目标:** (1) 确认归因 / 可选复跑验证;(2) GFP D2 处置拍板;(3) 分支合并/推进决策;(4) 长期未提交改动(245+166)保持原样,除非用户要求。

---

## 0. 当前状态(2026-08-09,会话关闭时)

- **S1 r5 已完成**(pid 831358,21:28 启动 → 22:15:07 正常退出,无残留进程,无 kill)。日志 `experiments/results/e5_s1_r5.log` 正常收尾:`E5 s1: 3 cell(s) failed verdict -> ['A1AT', 'Insulin', 'GFP']`。
- **判定书 `e5_verdict_s1.json` = NO-GO**(逐靶覆盖;磁盘上当前为最后跑靶 IL-2=GO,汇总 3 cells failed)。
- **runs.jsonl 现 15 条**(末 5 条 = r5)。
- **git 已提交**:`b6dad08` 在分支 **`feat/e5-b0-s1-r5`**(仅 4 个 E5 文件,用户 AskUserQuestion 拍板:仅 E5 相关 4 文件 + 新建分支)。未 push,未合并 main。
- **pytest:649 passed, 1 skipped, 30 deselected** ✓(与基准一致)。
- **无实验在跑**。微服务照常运行,勿杀。

## 1. r4 vs r5 逐靶对比结论(完整数据来自 e5_s1_runs.jsonl,15 条)

| 靶 | pool r4→r5 | arm A 交付 | arm B 交付 | 结论 |
|---|---|---|---|---|
| A1AT | 60/315 → **60/315** ✓ | 3 profile **逐位一致** | stability DIFF(ids 换 + R1 True→False, spearman 1.0→0.9) | 确定性链路零回归 |
| Insulin | 92/315 → **92/315** ✓ | 3 profile **逐位一致** | expression DIFF(ld4_u5m_u3l→ld4_u5s_u3s + R1 True→False) | 同上;D1 仍 False(已接受) |
| EPO | 306/315 → **306/315** ✓ | 3 profile **逐位一致** | 3 profile 全 DIFF(ids 换;balanced R1 False→True 反向) | 同上 |
| GFP | 0/333 → **12/315** ✅ | 空交付 → 全交付,R4/D1/D3 False→True | 同左 | **B0 落地成功**(与离线验证 12 pass 逐位吻合) |
| IL-2 | 192/315 → **192/315** ✓ | 3 profile **逐位一致** | 3 profile **逐位一致**(碰巧相同) | 完全一致 |

**arm B 差异归因 = LLM 非确定性(非代码回归)**,决定性证据:4 靶的 B-arm `history[].payload.rationale` 文本全部不同(含交付完全一致的 IL-2),且 history 长度不同(r4=2 vs r5=1)。arm B 是唯一含 LLM 自由选择的臂(`E11_utility_lambda: "B-arm: LLM free choice"`);R1 翻转(spearman 0.9 vs 1.0)是候选选择不同导致排序微变的自然结果。arm A 26 个 profile 交付 ids 逐位一致 → LD/池/判据链路零变化。

**GFP 剩余问题**:r5 中 GFP 全部 arm×profile 的 **D2 = False**(λ 多样性 <3 个 distinct ranks),e2e_pass=True。D2 与 Insulin D1 同源为「λ 饱和结构性」的推测需下会话确认(是否接受/处置)。

## 2. 本会话落地

1. **对比脚本** `/tmp/e5_r4_r5_compare.py`(runs.jsonl 末 10 条逐靶对比 pool/判据/ids)。⚠ /tmp 可能被清,结论以上表 + 判定书为准。
2. **git 提交** `b6dad08`(分支 `feat/e5-b0-s1-r5`):`sequence_utils.py`(export_codon_usage_csv)、`mrna_cds_design.py`(_ld_args 透传)、`run_e5_constraint_nav.py`(_ld_codon_usage_path + 两处透传)、`probe_e5_generation_optimization.py`(探针 bug + header)。**PREREG/MODEL_API_USAGE/codon CSV 在 experiments/results/ 下,被 .gitignore:24 忽略,未入库**(属本地产物)。
3. **归因收窄确认**:S1 整体 NO-GO 归因 = A1AT R3 + Insulin R3/D1 + **GFP(非 human 已修但 D2 仍 False)**。

## 3. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/results/e5_s1_r5.log | r5 日志(正常收尾;勿覆盖 r4.log / e5_s1.log) |
| experiments/results/e5_verdict_s1.json | 判定书(当前=IL-2,汇总 NO-GO 3 cells) |
| experiments/results/e5_s1_runs.jsonl | 15 条证据(末 5 = r5) |
| /tmp/e5_r4_r5_compare.py | 对比脚本(可能已随 /tmp 清理) |
| HANDOFF_2026-08-08_E5_B0_LANDED.md | 上一会话(B0 链路查证/4 项拍板/代码落地) |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | §18.4/§19(判据与决议) |
| experiments/results/MODEL_API_USAGE.md | §2 E5 行(B0 注记) |

## 4. 下一会话候选动作(需用户拍板)

1. **归因确认(可选)**:复跑 1 次 B-arm(或 IL-2 第 3 次)验证 LLM 非确定性——预期 rationale 再次不同;或直接采信现有 4 靶 rationale 全不同的证据。
2. **GFP D2=False 处置**:分析 λ 多样性分布(GFP 交付集中在 λ4/λ10?);判定是否与 Insulin D1 同类(λ 饱和结构性,接受)或需动作——**判据/处置变更必须拍板**并同步 PREREG §19 + MODEL_API_USAGE §2。
3. **分支决策**:`feat/e5-b0-s1-r5`(b6dad08)是否合并 main / 推送远端——git 操作先问用户。
4. **长期未提交改动**:工作树 245 已跟踪 + 166 未跟踪(非本会话产生,含大量删除/重构/新目录)——保持原样,除非用户明确要求处理。
5. E5 整体结论与论文/报告线(如适用)由用户指示推进。

## 5. 纪律重申(与前会话一致)

- git 操作必须先问用户;判据/阈值/处置变更必须拍板并同步 PREREG 与 MODEL_API_USAGE。
- 工作目录可能被外部切换 → 一律绝对路径(仓库根 `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`)。
- 勿杀微服务(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 重启须带 PYTHONPATH=<rna_agent_system>)。
- e5_s1_round3_archive/ 勿删;e5_s1_r4.log / e5_s1.log / e5_s1_r5.log 勿覆盖;IL-2 探针勿重跑;探针产物写 /tmp/e5_probe_carm/。
- 当前无实验在跑;若后续再跑 S1 变体,勿动 codon_tables/CSV 与 generate_candidates 链路(破坏可复现)。
