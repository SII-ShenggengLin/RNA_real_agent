# HANDOFF 2026-08-09 — E5 收尾:E5 已合并 main 并推送、GFP D2 拍板接受、正式报告定稿、文档同步完成

**上一会话:** HANDOFF_2026-08-09_E5_S1_R5_VERDICT.md(S1 r5 判定书 NO-GO + 对比归因 + git 提交)
**本会话:** 状态确认 → 归因复核(全部成立)→ GFP D2 机理查清 → 用户 4 项拍板 → 合并推送 → 文档同步 → E5 报告定稿
**下一会话目标:** 按用户指示推进(报告/论文线已有初稿;S2 启动需生成方法层变更先行拍板)。

---

## 0. 当前状态(2026-08-09,会话关闭时)

- **git**:分支 `feat/e5-b0-s1-r5` 已 **fast-forward 合并 main(b6dad08)并推送远端**(`8f7a7ad..b6dad08 main -> main`),本地与 origin/main 同步。工作树 418 行非 E5 改动保持原样(用户拍板)。
- **GFP D2 处置:接受**(用户拍板,与 Insulin D1 同源结构性,零代码改动/判据零变更)。
- **pytest 重跑确认**:649 passed, 1 skipped, 30 deselected(26.7s)。
- **无实验在跑**。微服务勿杀(8003–8020 端口不在本容器监听,可能外部映射;jupyter + GPU_get.py 在跑)。

## 1. 本会话落地

1. **状态确认**:全部符合预期(进程无残留 / git b6dad08 / runs.jsonl 15 条末 5=r5 / 判定书=IL-2 GO 汇总 3 cells failed)。
2. **归因复核**(runs.jsonl 重算):池 4/5 逐位一致(GFP 0→12 预期)、arm A 4/5 逐位一致、arm B rationale 5 靶全不同 + history 长度不同 → **LLM 非确定性证据充分,不再复跑**。
3. **GFP D2 机理查清**(附发现):12 pass 全集中 λ4/λ10(ranks {2,3} 档距 1 <2,D2 硬性判据结构性不满足);λ1/GEMORNA/RNARL 0 pass(交付反推)。**新记录**:GFP arm A/B stability/balanced R1=0.9 为设计行为(junction 入 U 重算后 A/B 臂不重排,判据仅考核 C 臂,预注册 §9)——C 臂 R1 全 True,无影响。
4. **用户 4 项拍板**:①分支合并 main 并推送(已执行)②GFP D2 接受③长期改动保持原样④整理 E5 报告/论文线。
5. **文档同步**(本地产物,不入库):PREREG §19 追加「GFP D2 处置决议(2026-08-09)」;MODEL_API_USAGE §2 E5 行追加 r5 实测(LLM 11 次 + LD 20 + RNARL 5 + GEMORNA 0 新增)+ 第 4 行最后更新日期。
6. **E5 正式报告**:`experiments/results/E5_REPORT_2026-08-09.md`(摘要/设计/过程/逐靶判定/归因/决议/结论教训/附录);HTML 版 `/tmp/e5_report_artifact.html`(Artifact 发布因无 claude.ai 登录跳过,文件可直开)。

## 2. 关键文件索引

| 文件 | 说明 |
|---|---|
| E5_REPORT_2026-08-09.md | **E5 正式报告(本会话定稿)** |
| HANDOFF_2026-08-09_E5_S1_R5_VERDICT.md | 上一会话(S1 r5 判定书 + r4/r5 对比) |
| e5_verdict_s1.json / e5_s1_runs.jsonl / e5_s1_r5.log | 判定书/15 条证据/日志(勿覆盖) |
| PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | §19 已追加 GFP D2 处置决议 |
| MODEL_API_USAGE.md | §2 E5 行已追加 r5 实测 |
| /tmp/e5_report_artifact.html | 报告 HTML 版(可能随 /tmp 清理) |

## 3. 下一会话候选动作(需用户指示)

1. **S2 是否启动**:当前判据/生成方法层不变 → S2(18 靶)配对显著性结构性不可达(p=1.0 预期),重复同一 NO-GO 结论。启动前置条件 = 生成方法层变更(如物种表/多样 CDS 策略)或判据修订,须先拍板。
2. **论文/报告线推进**:E5_REPORT 初稿已就绪,可按需扩展(方法学/图表/英文版)。
3. **长期未提交改动(418 行)**:保持原样,除非用户明确要求处理。
4. 微服务状态:8003–8020 未在本容器监听(外部映射可能),如用户预期应监听需排查;勿杀任何服务。

## 4. 纪律重申(与前会话一致)

- git 操作必须先问用户;判据/阈值/处置变更必须拍板并同步 PREREG 与 MODEL_API_USAGE。
- 工作目录可能被外部切换 → 一律绝对路径(仓库根 `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`)。
- 勿杀微服务(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 重启须带 PYTHONPATH=<rna_agent_system>)。
- e5_s1_round3_archive/ 与 e5_s1_r2_rnarl_down_archive/ 勿删;e5_s1_r4.log / e5_s1.log / e5_s1_r5.log 勿覆盖;IL-2 探针勿重跑;探针产物写 /tmp/e5_probe_carm/。
- 若再跑 S1 变体,勿动 codon_tables/CSV 与 generate_candidates 链路(破坏可复现)。
