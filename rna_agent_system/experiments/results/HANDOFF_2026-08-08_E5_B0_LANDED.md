# HANDOFF 2026-08-08(深夜)— E5 B0 已落地,S1 重跑(r5)在跑,待判定对比 + git 确认

**上一会话:** HANDOFF_2026-08-08_E5_GENOPT_PROBE_ANALYSIS.md(探针分析完成,B0 断点待查)
**本会话(关闭于 ~21:4x):** B0 链路查清(反转)+ 4 项拍板 + 代码落地 + 离线验证 + S1 r5 启动
**下一会话目标:** (1) 监控/收集 S1 r5 结果;(2) 判定书对比 r4;(3) git 提交确认;(4) 收尾验证。

---

## 0. 当前状态(2026-08-08 21:4x,会话关闭时)

- **S1 重跑(r5)正在跑**:`setsid nohup python experiments/run_e5_constraint_nav.py s1 > experiments/results/e5_s1_r5.log 2>&1`(pid **831358**,21:28 启动,~1h 完成 → ~22:30)。当前在 A1AT 池重建(日志仅 2 行,池重建 ~13min/靶)。**⚠ 工作目录可能被外部切换到 git 根 `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`——一律用绝对路径**。
- **B0 链路已查清(反转结论)**:CSV 透传**已生效**。上一会话 HANDOFF 所称「λ10=0.6843/λ50=0.7005 与默认逐位相同」是对表②(默认 human 表生成)数值的误读;table6 实际值 = λ10 **0.9956** / λ50 **1.0**(Kazusa E. coli 计分)。三证据:① curl 8014 直测带/不带 CSV → 序列/CAI/MFE 全变(λ10: 0.6843→0.9956);② `external_repos/LinearDesign/src/linear_design.cpp` L99-100 消费 argv[3] 作 CODON_TABLE(bin wrapper `"$@"` 完整转发);③ verbose 行确认 `Using codon frequency table = /tmp/e5_probe_carm/kazusa_Escherichia_coli_K-12.csv`。
- **B0 生成侧修复完整验证**:B0 λ50(E. coli 表)GFP CDS 全 6 条约束过(CAI=1.0 / C1 ✓ / C2 ✓ / M1 ✓ / C6=7≤12 / C7=17≤30)。

## 1. 用户拍板(2026-08-08,全部采纳推荐项,AskUserQuestion 确认)

1. **GFP = B0 落地,仅非 human 物种启用**(生成侧传 species 匹配 Kazusa CSV;human 4 靶保持默认 LD 表,与 r4 逐位一致)。放弃 B1(服务外同义补救)与 B2(接受结论)。
2. **A 分支(λ 网格扩展 + 口径 i)放弃**:A1AT/Insulin R3 不修;不新开「λ1 C7 修复」探针、不改判据。
3. **C 分支(gm 30→60)放弃**。
4. **Insulin D1 接受**(λ 饱和结构性,零动作)。

## 2. 本会话落地(代码已改,git 未提交)

1. `agent_core/sequence_utils.py`:`export_codon_usage_csv(species, out_path=None)`——LD 格式 CSV 导出(首行 `#,,"` 供 LD 无条件跳过;fraction 钳制 ≥1e-6;stop 编码 `*`;默认写 `experiments/results/codon_tables/<canonical>.csv`,幂等;与探针 CSV 逐字节一致已验证)。
2. `experiments/run_e5_constraint_nav.py`:`_ld_codon_usage_path(species)`(resolve==Homo sapiens → None,否则 CSV;表缺失 KeyError → 回退 None);`build_pool` 与 `_neighbour_redesign` 两处 `MrnaCdsDesignInput` 传 `lineardesign_codon_usage_path`。
3. 文档同步:`PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md` 新增 **§19**(探针 6 表 + B0 链路查证 + 4 项拍板 + 落地实现);`MODEL_API_USAGE.md` §2 E5 行追加 B0 预算注记(LD 调用数不变,CSV 本地导出零 API)。
4. **服务端零改动**(8014 原生支持 codon_usage_path);LD 二进制零改动;判据/阈值零变更。

## 3. 离线验证(已完成,全绿)

- **GFP(非 human)**:build_pool 重建 → 315 候选,**12 全约束 pass**(r4=0!);λ10 CAI=0.9956。
- **A1AT(human)**:60/315 与 r4 一致,4 λ CDS **逐位 MATCH**。
- **pytest:649 passed, 1 skipped, 30 deselected** ✓(与基准一致)。

## 4. 下一会话执行步骤(按序)

1. **收集 S1 r5 结果**(~22:30 完成,勿手动 kill):日志 `experiments/results/e5_s1_r5.log`;判定书 `e5_verdict_s1.json`(逐靶覆盖,既有设计);完整证据 `e5_s1_runs.jsonl` **末 5 条**。注意 r5 判定书**不覆盖 r4 判定书备份**——r4 完整证据在 `e5_s1_runs.jsonl` 中 r4 记录 + `e5_s1_r4.log`(勿覆盖/勿删)。
2. **判定对比 r4 vs r5**:逐靶对比(A1AT/Insulin/EPO/IL-2 应完全一致:池 60/92/306/192 + 判定;GFP 应 0→12 pass,空交付失败转为正常判定,crit1-4 由 False 转正常)。若 human 靶有差异 → 排查回归(应零差异)。
3. **git 提交确认(必须先问用户)**:工作树 253 文件长期未提交改动(非本会话)+ 本会话 5 个文件(sequence_utils.py / run_e5_constraint_nav.py / PREREG / MODEL_API_USAGE / 新产物 codon_tables/Escherichia_coli_K-12.csv)+ 上一会话 2 个文件(probe_e5_generation_optimization.py / mrna_cds_design.py)。问用户提交范围与方式。
4. **收尾验证**:pytest 649 全绿再确认;更新 HANDOFF(本文件)→ 若 S1 r5 判定书与预期一致,整体 NO-GO 归因收窄至 A1AT/Insulin(R3)+ Insulin(D1)。

## 5. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/results/e5_s1_r5.log | S1 r5 日志(勿覆盖 r4.log / e5_s1.log) |
| experiments/results/e5_verdict_s1.json | S1 判定书(逐靶覆盖,最终=最后跑靶) |
| experiments/results/e5_s1_runs.jsonl | 完整证据(末 5 条 = r5) |
| experiments/results/e5_s1_r4.log | r4 日志(勿动) |
| experiments/results/codon_tables/Escherichia_coli_K-12.csv | 新产物(B0 CSV,与探针逐字节一致) |
| /tmp/e5_probe_carm/e5_probe_genopt_r1.json / .json | 探针数据(人类 4 靶 / GFP) |
| agent_core/sequence_utils.py | export_codon_usage_csv(本会话新增) |
| experiments/run_e5_constraint_nav.py | _ld_codon_usage_path + 两处透传(本会话新增) |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | §19 本会话决议 |
| experiments/results/MODEL_API_USAGE.md | §2 E5 行 B0 注记 |

## 6. 纪律重申(与前会话一致)

- git 操作必须先问用户;判据/阈值变更必须拍板并同步 PREREG §18.4/§19 与 MODEL_API_USAGE §2。
- 工作目录可能被外部切换 → 一律绝对路径或 `cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system &&`。
- 勿杀微服务(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 重启须带 PYTHONPATH=<rna_agent_system>);S1 r5 进程 831358 勿 kill(除非确认卡死)。
- 探针产物写 /tmp/e5_probe_carm/;e5_s1_round3_archive/ 勿删;e5_s1_r4.log/e5_s1.log 勿覆盖;IL-2 探针勿重跑。
- S1 重跑(r5)期间勿动 codon_tables/CSV 与 generate_candidates 链路(会破坏结果可复现)。
