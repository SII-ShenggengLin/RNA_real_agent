# HANDOFF 2026-08-08 — E5 生成方法优化探针运行中(会话关闭于 19:2x,A1AT 生成中)

**上一会话:** HANDOFF_2026-08-08_E5_S1_R4_RUNNING.md(S1 重跑 r4 完成、文档同步、用户拍板"先做生成方法优化")
**下一会话目标:** 等探针(PID **1838502**)完成 → 分析 6 表(sanity 必须复现 r4 口径 60/92/0/306/192)→ 呈报阶段 2 分支决策逐项拍板。

---

## 0. 当前状态(2026-08-08 ~19:22,会话关闭时)

- **生成方法优化探针正在后台跑**(setsid pid **1838502**,19:20 重启):`cd rna_agent_system && setsid nohup python experiments/probe_e5_generation_optimization.py > /tmp/e5_probe_carm/e5_probe_genopt.log 2>&1 &`
  - **探针脚本**:`experiments/probe_e5_generation_optimization.py`(本会话编写,已验证 + 修 1 bug + 重启)。
  - **已完成**:A1AT 开始(~19:20),正在 LD 8014 生成 λ∈{20,50,100,200}(4 新 λ/靶,每靶约 5-12 min,后续 8015 fold 本地过滤后 ~1200-1600 次)。
  - **完成标志**:日志尾部 `DONE -> /tmp/e5_probe_carm/e5_probe_genopt.json`。5 靶预计共 **45-75 min**(若 19:20 起,预计 ~20:05-20:35 完成)。
  - 探针资源:LD 8014 共 22 次(5 靶×4 新 λ + GFP B0 2 次)+ 8015 folds + GEMORMA 8004 预测 6×5;LLM 0。
- **Monitior 事件提醒**:本会话挂了 Monitor 监控日志(`SANITY|R3 sim|B0:|GFP ceiling|DONE|ERROR|Traceback|MISMATCH|=== [A-Z]`),会话关闭后失效;新会话需自己重新监控/轮询。
- **git:** 工作树大量未提交修改。git 操作必须先问用户。
- **微服务:** 勿杀任何微服务(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py)。

## 1. 本会话已完成

1. **探针脚本编写 + 验证 + 修复 + 启动**(`experiments/probe_e5_generation_optimization.py`,零代码改动产物只写 /tmp/e5_probe_carm/):
   - **API 验证全过**:`lineardesign_codon_usage_path` 字段存在(Input 支持,LD 服务零改动,B0 可用);build_pool 用 `lambda_value=`(工具层映射);C6 窗口 = utr5+cds[:30] 去重 key=(utr5,cds);E2 同 8015 `["mfe"]`;`pool_normalizers`/`_norm` 安全处理 None;survey/cache/runs 结构与 meta 字段全确认。
   - **修复 3 处**:(a) table2 LD CSV 路径多一层目录 → `Path(__file__).parent.parent/external_repos/...`;(b) table2 密码子校验优先级 bug → `len(parts[0])==3 and set(parts[0])<=set("ACGTU")`;(c) `_lambda_pref_comp` 读模块级 `LAMBDA_RANK_SPAN` → sim 前 monkey-patch/用后恢复。
   - **运行时 bug 修复 + 重启**:首跑 A1AT 报 `name 'p' is not defined` → L236 `u5[p]`/`u3[p]` 应为 `u5[u5p]`/`u3[u3p]`(旧进程 1623160 已 kill,ALL_GONE 确认)。19:20 重启为新 PID 1838502。
2. **探针输出 6 表**(脚本内,产物 JSON `/tmp/e5_probe_carm/e5_probe_genopt.json`):
   - 表① λ×CAI×逐约束 + **sanity diff**(r4 基准 60/92/0/306/192);表② GFP 天花板(λ 实测 vs LD 表最优 vs Kazusa-max);表③ R3 可达性模拟**两口径**(rank_i_renumbered: 新 λ 序数重映射排 4..7/gm=8/rn=9,SPAN=9;rank_ii_merged6: 新 λ 并入 λ10 档 rank3,SPAN=5;标注"模拟非判据");表④ Insulin D1 pairwise 距离(过约束 λ 档 CDS);表⑤ gm C1 淘汰率(缓存统计);表⑥ GFP+E.coli Kazusa CSV B0 预演(λ10/λ50)。

## 2. 下一会话执行步骤(按序)

1. **等探针完成**:`tail -f /tmp/e5_probe_carm/e5_probe_genopt.log`(或 until 循环等 `DONE ->`);`ps -p 1838502` 确认退出。**未完成不要中途杀**(杀 = 浪费 LD 生成进度)。
2. **分析 6 表**:
   - **sanity 必须 OK**:每靶 `SANITY: OK`(legacy-only 通过数 == r4 60/92/0/306/192)。MISMATCH = 探针 bug,先修再进入后续(不要用错误数据拍板)。
   - 表③ A1AT/Insulin R3 两口径对比(预期:口径 (i) 新 λ 拉开档距 → R3 可达;口径 (ii) 并入 6 档仍 0/3);EPO/IL-2 维持 GO;GFP 仍空交付(表② 天花板 <0.8 则证实结构性)。
   - 表④ Insulin D1:λ20/50 与 λ10 CDS 一致率;表⑥ B0:GFP + E.coli CSV 的 CAI/GC/约束。
3. **呈报用户 + 拍板**(判据口径相关必须 AskUserQuestion):
   - **A: λ 网格扩展**(人类 4 靶)—— 表① 高 λ 全过约束时:改 `run_e5_constraint_nav.py` L349 LAMBDAS、L356 LAMBDA_RANK、L438 LAMBDA_RANK_SPAN、L1502 `_neighbour_redesign` clamp 0-20→0-100;MODEL_API_USAGE LD 4→8/靶。**口径 (i) vs (ii) 是判据口径变化,必须拍板;推荐 (i)**(A1AT R3 唯一生成侧修复路径)。
   - **B0: GFP 物种表 CSV**(表② 证实 λ 不可达 0.8 时):脚本内 `kazusa_csv_for_species()`(内置表导出,fraction 0→1e-6 钳制,stop 用 `*`);build_pool 传 `lineardesign_codon_usage_path`(绝对路径,零服务改动);缓存 key 版本化。生成表参照系变化 → 需拍板。
   - **B1: 服务外全长同义补救**(B0 不做/失败时):`rescue_full_length_cai()` 200-300 行,复用 `sequence_utils.build_cai_weights/compute_cai`;Kazusa-max 初始化→C1/C2 修复→fold→C6/C7 茎翻转→≤3 轮;插入 build_pool L806;新缓存文件。零锁影响;~1 天工作量。
   - **B2: 接受 GFP 结论**(用户不采纳 B0/B1):零改动。
   - **C: gm 采样密度 30→60**(表④⑤ 证 Insulin D1 需新 CDS):L355 `GEMORNA_CDS_N` 30→60(缓存 key 兼容 idx 30-59);MODEL_API_USAGE GEMORNA +30/靶;池 315→585/靶;需拍板。
   - **推荐次序:探针 → A(口径 i)→ B0 → (C|B1)→ 池重建 + S1 重跑 → 全套验证**。
4. 拍板落地后(每分支):先离线重算(探针 mini-pool 模式)→ 池重建服务重跑 → `run_s1` 5 靶判定书对比;pytest 649 passed 保持全绿;MODEL_API_USAGE §2 与 PREREG §18.4 同步;涉判据口径的改动先 AskUserQuestion。

## 3. 纪律(继续遵守)

- **git 操作必须先问用户**(工作树大量未提交修改)。
- **判据/阈值变更必须呈用户拍板**(AskUserQuestion),并同步 PREREG。
- 工作目录可能被外部切回项目根:**一律用绝对路径,或在命令内 `cd rna_agent_system &&`**。
- **勿杀微服务**(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py)。RNARL 8008 重启必须带 `PYTHONPATH=<rna_agent_system>`。
- 探针产物写 `/tmp/e5_probe_carm/`;`e5_s1_round3_archive/` 勿删;`e5_s1_r4.log`/`e5_s1.log` 勿覆盖;**本次探针日志 `e5_probe_genopt.log` 可覆盖**(它是对应探针自己的重跑日志)。
- IL-2 探针勿重跑;判定书 `e5_verdict_s1.json` 会被每靶覆盖(既有设计),完整证据以 runs.jsonl + r4 日志为准。

## 4. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/probe_e5_generation_optimization.py | **生成方法优化探针(在跑)**:仿 preflight 模式 import run_e5_constraint_nav as m;13 函数;6 表;产物 /tmp/e5_probe_carm/e5_probe_genopt.json |
| experiments/results/HANDOFF_2026-08-08_E5_S1_R4_RUNNING.md | 上一会话 handoff(S1 r4 汇总/文档同步已全部完成,可只读其纪律与判定书语义) |
| experiments/run_e5_constraint_nav.py | 主 driver(v6 阈值 L377/385;v7 判据① crit1 C≥A 平局算过 L2016;D3 空交付兜底 L1101 区;阶段 2 改动点 L349/355/356/438/806/1502) |
| /tmp/e5_probe_carm/e5_probe_genopt.{log,json} | 探针日志(在写)/ 6 表 JSON(完成后) |
| experiments/results/e5_pool_survey.json | 36 cand/靶 survey(与 r4 逐位一致),探针 LD 复用源 |
| experiments/results/e5_gemorna_cds_cache.json / e5_gemorna_cache.json | gm CDS 30×5 / UTR 缓存,探针复用源 |
| experiments/results/e5_s1_runs.jsonl | r4 5 靶完整记录(最后 5 条),探针 rnarl 重建源(A1AT/EPO/IL-2 有;Insulin/GFP 无) |
| experiments/results/MODEL_API_USAGE.md | §2 E5 行已含 r4 实测(24 LLM + LD 22 + RNARL 5);S2 预登记已备 |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | §18.4 已含 r4 结果 + 拍板决议 4 项 |
| /root/.claude/plans/swirling-seeking-owl.md | **已批准计划**(E5 生成方法优化,阶段 1/阶段 2 分支表),下一会话参考 |
| agent_core/sequence_utils.py | L180-312: Kazusa 表/CAI 计分/CSV 导出源(B0/B1 复用) |
| microservices/lineardesign_service/main.py | λ 无上限 L182-193、`codon_usage_path` 绝对路径 L61-78(B0 零服务改动) |

## 5. 已批准计划要点(swirling-seeking-owl.md)

阶段 1(在跑)= 探针;阶段 2 = 5 分支表(A λ 网格/B0 物种 CSV/B1 服务外补救/B2 接受结论/C gm 密度)。推荐次序:探针 → A(口径 i)→ B0 → (C|B1)→ 池重建 + S1 重跑 → 全套验证。判据影响点已标注在分支表(涉口径变更必须拍板)。
