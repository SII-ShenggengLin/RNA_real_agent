# HANDOFF 2026-08-08 — E5 S1: B1 放宽落地(v6 最终形态 GC 30-80 + CAI 0.8)、preflight 复验完成、真实 C 臂探针 v6 正在后台跑(EPO/GFP 未完)

**上一会话:** HANDOFF_2026-08-08_E5_B1_DIAGNOSED_PROBES_DONE.md(诊断完成后)
**下一会话目标:** 等探针 v6 4 靶全部完成 → 呈报 5 靶 crit3 完整证据 → AskUserQuestion 拍板判据① → GO(预登记 S2 + 重跑 S1 全量)或 NO-GO(呈报)。

---

## 0. 当前状态(2026-08-08 ~16:30,会话关闭时)

- **探针 v6 正在后台跑**(pid 928540 setsid 分离,会话关闭不受影响):顺序 A1AT → Insulin → EPO → GFP。
  - **A1AT ✅ 完成**(rc=0):R3=False;expression/stability/balanced e2e+R1+R4+D2+D3 全 True,D1=True,constraint_rate 1.00;top-1 = ld4/ld10/ld4。
  - **Insulin ✅ 完成**(rc=0):R3=False;**D1=False(0.0082 < 全长 2%)**;其余 e2e/R1/R4/D2/D3 True;top-1 = ld4/ld10/ld4。
  - **EPO ⏳ 池构建中**(16:24 起,~10-30min);**GFP ⏳ 待跑**(预期 PROBE_CRASH rc=2——0/315 pool 空交付兜底,预期行为)。
  - 完成标志:日志尾部 `ALL_PROBES_DONE`。日志:`experiments/results/e5_probe_carm_4targets_v6.log`(勿覆盖)。
- **微服务:** 探针日志确认 3 service healthy(8004/8008/8015 等)。勿杀任何微服务。
- **git:** 工作树大量未提交修改(自 fd61126 checkpoint)。git 操作必须先问用户。

## 1. 本会话已完成(代码已改、测试全绿、文档已同步)

### 1.1 B1 最终形态(用户 2026-08-08 两次拍板)

| 项 | 值 | 说明 |
|---|---|---|
| C1 GC 窗口 | **30.0–80.0**(`GC_MIN/GC_MAX`) | 原 B-1 加严 35–70 被真实 C 臂探针证伪(4/5 靶清零)→ 放宽保留 |
| CAI 硬约束 | **≥ 0.8**(`CAI_MIN = 0.8`) | **用户最终拍板:先试探 0.7,preflight 实测 GFP 仍 0/315(池 max CAI 0.684 结构性不可达)→ 用户拍板"0.7 已很低,恢复 0.8"**;GFP 0-pass 视为**系统能力结论**(生成池无法产出 CAI≥0.8 的 GFP CDS,后续需优化生成方法),不降阈值 |
| M1 边界 GC | 20–80(`BOUNDARY_GC`) | 不变,勿混淆 |

约束共 6 条:C1 GC 30–80(100nt 滑窗) + C2 无 ≥14 同聚物 + C6 起始区最长茎 ≤12bp + C7 全长最长茎 ≤30bp + M1 边界 GC 20–80 + CAI ≥ 0.8。

改动文件:`experiments/run_e5_constraint_nav.py`(阈值 + 全部 docstring/注释同步,v6 记录追加;L377/385 为最终值)、`experiments/preflight_e5_s1_lambda_fix.py`(池统计标签 → GC 30-80 + CAI>=0.8)、`experiments/probe_e5_carm_il2.py`(**修复 llm_calls KeyError**:`evaluations.C` 无该键,改为读 `arm_results.C.llm_calls` 并兜底;头部 docstring 更新为 v6)。

### 1.2 pytest

**649 passed, 1 skipped**(CAI 0.8 恢复后重跑 ×1,全绿)。

### 1.3 preflight v6b 复验(CAI 0.8 口径,`/tmp/e5_probe_carm/preflight_v6b.log`)

| 靶点 | B-1(35-70+0.8) | 诊断预测 GC[30,80]+0.8 | **v6 实测 n_pass** | 结论 |
|---|---|---|---|---|
| A1AT | 9/315 | 60 | **60/315 (19.0%)** | 精确吻合 ✓ |
| Insulin | 0/315 | 92 | **92/315 (29.2%)** | 精确吻合 ✓ |
| EPO | 0/315 | 306 | **306/315 (97.1%)** | 精确吻合 ✓(0.7 时 312,6 个 CAI∈[0.7,0.8) 被 0.8 拒,符合预期) |
| GFP | 0/315 | 0 | **0/315 (0.0%)** | 池 CAI 分布 0.554–0.684,max 0.684 < 0.8,结构性(能力结论) |

→ **GC[30,80]+CAI≥0.8 为有效最终形态,4/5 靶放宽复验全部与诊断预测精确吻合。** GFP preflight 0-pass 后脚本 IndexError 崩溃为预期(空通过子集选点,无兜底;探针脚本有 try/except 兜底 rc=2)。

### 1.4 预注册文档

`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md` **§18 v6 拍板注记**已追加:18.1 B-1 证伪表 + 杀手诊断;18.2 v6 拍板 2 项(GC 30–80 保留 / CAI 维持 0.8 + GFP 能力结论);18.3 preflight 复验表(实测已填);18.4 判据①待拍板(占位,拍板后追加最终决议)。

## 2. 探针已出结果解读(呈报材料基础)

**A1AT v6**:R3=False。top-1 = ld4(λ 档 2)/ld10(λ 档 3)/ld4(λ 档 2),3 对 λ 档距 = 1/0/1 均 <2 档,CAI 差 <0.05 → 0 对分离 → False。**机制观察:v6 放宽后 A1AT pool 恢复(60/315)且 C 臂可交付,但真实 LLM 3 画像选点集中在 λ 4/10 相邻档,分离度不足**(v5 时 R3=False 因 pool 几乎清零,现在原因不同)。

**Insulin v6**:R3=False(top-1 同 ld4/ld10/ld4 模式)+ **D1=False(0.0082 < 全长 2% 阈值)**——交付 5 候选集中在同一 CDS(ld4/ld10)配不同 UTR(u5s×u3l/u3m/u3s),编辑距离仅 ~0.82%;通过子集(92/315)内 CDS 多样性不足。e2e/R1/R4/D2/D3 全 True,constraint_rate 1.00。**v5 时 Insulin 因 0/315 交付崩溃(ValueError);v6 已恢复可交付,但 D1 暴露 CDS 多样性不足。**

**IL-2(v5 既有,`e5_probe_carm_il2.log`)**:R3=True(ld1/ld10/ld4,恰有一对 λ 档距 2);3 画像 R1+R4+D1-D3+e2e 全 True,constraint_rate 1.00。注意:该日志末尾有旧 bug 的 KeyError(已修复,无需重跑 IL-2)。

**参考(IL-2 的 R3 为何过)**:λ 档位映射 `LAMBDA_RANK = {0:0, 1:1, 4:2, 10:3, gemorna:4, rnarl:5}`;R3 判据「3 画像两两 top-1 分离:CAI 差 ≥0.05 或 λ 档差 ≥2,≥1/3 对」(run_e5_constraint_nav.py L1168-1183)。ld4 vs ld10 档距仅 1。

## 3. 下一会话执行步骤(按序,不得跳步)

1. **确认探针 v6 全部完成**:`tail experiments/results/e5_probe_carm_4targets_v6.log`,找 `ALL_PROBES_DONE`。若 EPO/GFP 未完成,等待(单靶 10-30min;GFP 预期 PROBE_CRASH rc=2,预期行为非故障)。
2. **读取 EPO/GFP 探针结果**,与 §2 的 A1AT/Insulin + 既有 IL-2 合成为 **5 靶 crit3 完整证据表**。
3. **呈报 → AskUserQuestion 拍板判据①**(选项,沿用 §18.4):
   - e2e 改「C≥0.8 且 C≥A(ties 过)」
   - directionality ⑤ 升主判据
   - 维持 v5 → NO-GO(按 v5 判据跑 S1 = 必然 NO-GO,仅 crit1)
   - 其他(用户自定义)
   注意判据①拍板时需引用新数据:4 靶 crit1 的 e2e 仍全饱和 1.00(constraint_rate 1.00 全 True)vs 靶内真实差异在 R3/D1 上。
4. **判据①拍板后**:
   - **GO** → ①先在 `experiments/results/MODEL_API_USAGE.md` §2 的 E5 行追加 v6 探针实测(LLM ≈1-2 次/靶,已出 A1AT llm_calls=2、Insulin llm_calls=1)并预登记 S2(18 靶 × 3 臂,~126-234 次;生成器 LD 72 + RNARL 18 + GEMORNA 468,格式见现成行);②重跑 S1 全量:`cd rna_agent_system && setsid nohup python experiments/run_e5_constraint_nav.py s1 > experiments/results/e5_s1_r4.log 2>&1 &`(~1h,**勿覆盖 e5_s1.log**)。
   - **NO-GO** → 呈报。
5. **判据①决议追加进 PREREG §18.4**(最终决议)。

## 4. 纪律(继续遵守)

- **git 操作必须先问用户**(工作树大量未提交修改)。
- **判据/阈值变更必须呈用户拍板**(AskUserQuestion),并同步 PREREG(§18 已建,v6 记录完整)。
- 工作目录可能被外部切回项目根:**一律用绝对路径,或在命令内 `cd rna_agent_system &&`**。
- **勿杀微服务**(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py)。RNARL 8008 重启必须带 `PYTHONPATH=<rna_agent_system>`。
- 探针/probe 产物写 `/tmp/e5_probe_carm/`;`e5_s1_round3_archive/` 勿删。
- S1 重跑 log 用 `e5_s1_r4.log`,勿覆盖 `e5_s1.log`;探针 log 用 `e5_probe_carm_4targets_v6.log`,勿覆盖旧版。
- **IL-2 探针勿重跑**(v5 已过、无 bug 需要验证)。

## 5. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/run_e5_constraint_nav.py | 主 driver(v6 最终阈值 L377/385:GC 30.0/80.0 + CAI_MIN 0.8) |
| experiments/preflight_e5_s1_lambda_fix.py | 无 LLM 预演(接受 target argv;标签已更新 v6) |
| experiments/probe_e5_carm_il2.py | 真实 C 臂探针(llm_calls KeyError 已修复) |
| experiments/results/e5_probe_carm_4targets_v6.log | **探针 v6 日志(在跑,勿覆盖)** |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | 预注册(§18 v6 记录完整,§18.4 判据①待决议) |
| experiments/results/HANDOFF_2026-08-08_E5_B1_DIAGNOSED_PROBES_DONE.md | 上一会话 handoff(诊断细节) |
| /tmp/e5_probe_carm/preflight_v6b.log | preflight v6b 复验日志(CAI 0.8) |
