# HANDOFF 2026-08-08 — E5 生成方法优化探针:分析已完成,待拍板 + B0 链路待查(会话关闭于 ~20:20)

**上一会话:** HANDOFF_2026-08-08_E5_GENOPT_PROBE_RUNNING.md(探针 19:20 启动)
**下一会话目标:** (1) 查 B0 透传+header 修复后仍无效的链路断点; (2) 将 6 表分析结论呈报用户并逐项拍板(A/B0/B1/B2/C); (3) 落地后全套验证。

---

## 0. 当前状态(2026-08-08 ~20:20,会话关闭时)

- **无在跑实验**。探针 4 次运行全部结束:
  - r1(PID 1838502,19:20-19:38):5 靶全跑,JSON `/tmp/e5_probe_carm/e5_probe_genopt_r1.json`(人类 4 靶完整 + GFP error)
  - GFP 重跑 3 次(修探针 bug):最后第 4 次(PID 3372090,~20:1x)成功,JSON `/tmp/e5_probe_carm/e5_probe_genopt.json` = 仅 GFP(含表②③④⑤⑥,sanity OK)
  - **分析用数据**:人类 4 靶用 r1 JSON;GFP 用当前 JSON。日志备份:`e5_probe_genopt_r1.log`(全靶)、`e5_probe_genopt_gfp3.log`(GFP 最终)。
- **本会话已改 3 个文件(未提交,工作树本就有大量未提交修改)**:
  1. `experiments/probe_e5_generation_optimization.py`:修 3 处探针 bug(sanity 口径、R3 sim 空交付打印、kazusa_csv 属性)+ B0 CSV 加 header 行 `#,,"`
  2. `agent_core/workflows/mrna_cds_design.py`:`generate_candidates` 透传 `lineardesign_codon_usage_path` → 工具参数 `codon_usage_path`(仅显式传值时;默认行为零变化;相关 pytest 31 passed 已验)
- **⚠ B0 仍未生效(关键未解问题)**:透传 + CSV header 修复后第 4 次重跑,B0 结果 λ10 CAI=**0.6843**、λ50 CAI=**0.7005** 与「不传 CSV」逐位相同 → `lineardesign_codon_usage_path` 链路仍有断点,**未拍板前不要按 B0 有效来决策**。

## 1. 探针 6 表核心结论(数据可信:sanity 重建口径与 r4 全池逐位吻合)

**sanity(重要)**:r1 探针打印的 `SANITY: MISMATCH` 是探针汇总口径 bug(只统计 λ∈{0,1,4,10},漏 gm/rnarl 档)。用表①聚合行重建 r4 全池口径(λ0/1/4/10 + gm + rnarl 各档 passing_utr_combos 之和):
A1AT 9+33+0+0+9+9=**60** ✓ / Insulin 80+0+0+6+6=**92** ✓ / EPO 9+270+0+9+9+9=**306** ✓ / IL-2 6+168+0+6+6+6=**192** ✓ / GFP 0 ✓。**约束判定数据全部与 r4 逐位一致,可信。**

| 表 | 关键数据 | 结论 |
|---|---|---|
| ① λ×约束 | A1AT: λ20/50/100/200 全 pass 9/9,CAI 0.997/0.9992(λ50+ 同序列饱和);Insulin: λ20 pass 6/9,λ50+ local=0(GC 超界);EPO: 全 λ 过(342/351);IL-2: 全 λ pass 6/9;GFP: 全 0 | 高 λ 对 EPO/IL-2/A1AT 全过约束;Insulin 高 λ 超 GC;GFP 全不过(CAI) |
| ② GFP 天花板 | λ200 实测 CAI=**0.7005** = LD 表最优按 Kazusa 计分(0.7005)= **λ→∞ 上界**(已到达);Kazusa-max=1.0,GC 48.6% | **结构性证实生成表不匹配,推高 λ 对 GFP 无效**;蛋白化学可达 → B0/B1 是唯一生成侧修复路径 |
| ③ R3 模拟(两口径) | A1AT/Insulin: **两口径均 fail(0/3)**;EPO/IL-2: 两口径均 PASS(2/3);GFP: 空交付 fail | **两口径结果逐位相同(口径 (i) 序数重映射对 R3 零影响)**——机制: `_default_delivery` top-1 = 画像偏好 λ 档内 U 最大(偏好 λ 无过候选 → 全局 U-max),新 λ(20/50/100/200)不在偏好 λ 集 {0,4,10} 中 → 永不成为 top-1 → 档距/CAI 差不变 → **A 分支(λ 网格扩展 + 口径 i)不修 A1AT/Insulin R3,计划预期被证伪** |
| ④ D1 pairwise | A1AT: 4v10=0.055 ✓已过;10v20=0.026;50v100=0.0(饱和)。Insulin: 4v10=0.0121、4v20=0.0212、**10v20=0.0091** → min 0.0091 <2% → **加 λ 不修 Insulin D1(λ 饱和,高 λ 序列趋同)** | 同计划预判 |
| ⑤ gm C1 淘汰率 | A1AT 26/30(87% 全 9-killed!)、Insulin 18/30、EPO 0/30、GFP 5/30、IL-2 2/30 | **C 分支(gm 30→60)对 A1AT 基本无效**(采样加倍只 +3~4 可用);对 Insulin 边际(+12 可用);EPO/IL-2 已 GO 无需 |
| ⑥ B0 预演 | λ10 CAI 0.6843 / λ50 CAI 0.7005(与默认表逐位相同) | **CSV 未生效,链路断点未解(见 §0 ⚠)** |

**A1AT/Insulin R3 修复路径(呈报用,未验证)**:
- 候选 1(生成侧):**λ1 的 C7 修复**——A1AT/Insulin 的 λ1 均 local 9/9 但 pass 0/9(C7 全长最长茎>30 清)。若 λ1 CDS 可序列修补(C6/C7 茎翻转,B1 同思路),expression 偏好 λ0 空 → 全局 U-max 可能变 λ1(rank1)→ vs stability λ10(rank3):d_lam=2 ✓ + d_cai≈0.15 ✓ → R3 可 PASS。需新探针采 λ1 CDS 的最长茎长度/位置(本地 fold 即可,零 LD)。
- 候选 2(判据配置):画像偏好 λ 重配置(balanced→λ20 等)→ 判据改动需拍板;探针数据倾向 λ20 的 U 输给 ld4,大概率不可行。

## 2. 本会话已完成

1. 探针 r1 完成 + 分析(6 表,见 §1)。
2. 探针 3 bug 修复 + workflow 透传 + CSV header 修复(见 §0)。
3. 定位 B0 无效的第一层原因:`generate_candidates`(mrna_cds_design.py)只传 `lambda_value`,`lineardesign_codon_usage_path` 未透传(Input 字段存在但从未消费)→ 已修;LD C++ 解析(codon.h L35-63)无条件跳过第一行当 header → B0 CSV 加 `#,,"` header 已修。
4. **但修复后 B0 仍与默认相同 → 链路更深层断点未解**。待查点(按优先级):
   - (a) **LD 二进制是否消费 argv[3]**:`external_repos/LinearDesign/src/linear_design.cpp` main 的参数解析与 codon-usage 文件读取——若 LD 内部忽略该参数(或服务端传参序/文件名错位),B0 结构性无效(需服务端代码改动,超出「零服务改动」前提,拍板点变化);
   - (b) 直接 curl 服务 `/generate/cds` 带 `codon_usage_path=/tmp/e5_probe_carm/kazusa_Escherichia_coli_K-12.csv`(绕过 workflow,隔离断点层:服务端 vs 工具层 vs LD 二进制);
   - (c) 对比服务响应 `stderr`(verbose 输出含 codon table path 确认)。

## 3. 下一会话执行步骤(按序)

1. **查 B0 链路断点**(§2.4 的 a/b/c,~10-20 min):先 curl 直测服务端带 CSV → 看 CAI 是否变化;再看 linear_design.cpp 是否用 argv[3]。若确认 LD 二进制未消费 CSV(结构性)→ 呈报用户 B0 需服务端/二进制改动(拍板点变化)或转 B1。
2. **呈报用户 + 逐项拍板**(判据口径相关必须 AskUserQuestion):
   - **A(λ 网格扩展 + 口径 i)**:**被探针证伪**(A1AT/Insulin R3 两口径均 fail,EPO/IL-2 已 GO)——呈报证据,问用户是否放弃 A 或改走「λ1 C7 修复」探针(需拍板是否新开探针)。
   - **B0/B1/B2**(GFP):B0 链路先查清再呈报;B1(服务外全长同义补救,~1 天);B2(接受 GFP 结论,零改动)。
   - **C(gm 30→60)**:证据显示 A1AT 无效/Insulin 边际——价值低,呈报后可问是否放弃。
   - 推荐次序变化:**查 B0 链路 → 呈报(含 A 证伪证据)→ 拍板 → 落地 → 池重建 + S1 重跑 → 全套验证**。
3. 落地纪律:git 操作先问用户;判据/阈值变更必须拍板并同步 `PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md` §18.4 与 `MODEL_API_USAGE.md` §2;工作目录可能被外部切换——用绝对路径或 `cd rna_agent_system &&`;勿杀微服务(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py;RNARL 8008 重启须带 PYTHONPATH);探针产物写 `/tmp/e5_probe_carm/`;`e5_s1_round3_archive/` 勿删;`e5_s1_r4.log`/`e5_s1.log` 勿覆盖;IL-2 探针勿重跑;落地分支后先离线重算 → 池重建服务重跑 → run_s1 判定书对比 → pytest 649 passed 保持全绿。

## 4. 关键文件索引

| 文件 | 说明 |
|---|---|
| /tmp/e5_probe_carm/e5_probe_genopt_r1.json | r1 全靶 JSON(人类 4 靶权威;GFP 为 error) |
| /tmp/e5_probe_carm/e5_probe_genopt.json | 当前 JSON(GFP 靶权威:表①-⑥全,sanity OK) |
| /tmp/e5_probe_carm/e5_probe_genopt_r1.log | r1 全靶日志(含 GFP 表②天花板) |
| /tmp/e5_probe_carm/e5_probe_genopt_gfp3.log | GFP 最终重跑日志 |
| experiments/probe_e5_generation_optimization.py | 探针(本会话修 4 处:2 探针 bug + CSV header;上会话修 2 处) |
| agent_core/workflows/mrna_cds_design.py | 本会话新增 `_ld_args` 透传(lineardesign_codon_usage_path → codon_usage_path) |
| external_repos/LinearDesign/src/Utils/codon.h | L35-63 CSV 解析(跳过首行 header) |
| external_repos/LinearDesign/src/linear_design.cpp | **待查:argv 参数消费**(B0 链路断点候选) |
| microservices/lineardesign_service/main.py | L61-78 `_resolve_codon_usage_path`(绝对路径直返)、L267-289 /generate/cds |
| experiments/run_e5_constraint_nav.py | L349 LAMBDAS / L355 GEMORNA_CDS_N / L356 LAMBDA_RANK / L438 LAMBDA_RANK_SPAN / L1502 clamp / L1366-1395 _default_delivery / L1012-1035 _lambda_pref_comp |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | §18.4 判据决议(落地需同步) |
| experiments/results/MODEL_API_USAGE.md | §2 E5 行(预算口径更新需同步) |
| /root/.claude/plans/swirling-seeking-owl.md | 已批准计划(阶段 2 分支表;**表③证据显示 A 分支预期被证伪,拍板时引用**) |

## 5. 呈报要点(帮下会话组织语言)

- 探针 6 表齐(sanity 重建口径 60/92/0/306/192 逐位吻合,数据可信)。
- **核心反转**:A 分支(λ 网格扩展 + 口径 i)被证伪——机制是 `_default_delivery` 的 top-1 偏好 λ 锁定(expression→λ0/stability→λ10/balanced→λ4),新 λ 永不进 top-1,两口径逐位相同;A1AT/Insulin R3 需「λ1 C7 修复」类生成侧路径(新探针)或判据配置改动。
- GFP 天花板 0.7005 结构性证实;B0 链路断点未解(透传+header 已修仍无效,疑 LD 二进制未消费 CSV)→ B0 拍板前必须查清。
- Insulin D1:λ 饱和(10v20=0.0091),加 λ/gm 均边际 → 大概率需接受或 B1 类修复。
- C 分支(gm 30→60):A1AT 87% C1 灭 → 证据不支持。
