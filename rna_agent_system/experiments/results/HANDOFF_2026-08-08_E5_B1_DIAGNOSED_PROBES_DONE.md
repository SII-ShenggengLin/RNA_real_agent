# HANDOFF 2026-08-08 — E5 约束导航 S1:B1 已证伪、诊断完成、用户已拍板放宽、探针证据齐备

**上一会话:** HANDOFF_2026-08-08_E5_A_FIX_IMPLEMENTED_PREFLIGHT_DONE.md(v5 预演完成后)
**下一会话目标:** 执行 B1 放宽(GC [30,80] + CAI≥0.7)→ pytest → preflight 5 靶复验 → 重跑真实 C 臂探针 → 拍板判据① → 决定 S1 全量。

---

## 0. 当前状态(2026-08-08,会话切换时)

- **无实验在跑。** 全部后台任务已结束(4 靶探针 `ALL_PROBES_DONE` ✓、诊断 v2 完成 ✓)。
- **微服务:** 8004/8008/8014/8015 UP;8003/8009/8020 DOWN(无需处理;若 RNARL 8008 需要重启,必须 `PYTHONPATH=<rna_agent_system>`)。
- **已提交/未提交:** 工作树有大量未提交修改(自 fd61126 checkpoint 以来)。git 操作必须先问用户。

## 1. 用户已拍板的两个决策(2026-08-08,AskUserQuestion)

| # | 决策 | 内容 |
|---|---|---|
| **Q1** | **B1 约束调整** | **GC 窗口 [35,70] → [30,80];CAI ≥0.8 → ≥0.7**(推荐选项) |
| **Q2** | **判据①(e2e 饱和)走向** | **暂不定**——先等 B1 放宽后重跑探针验证,拿到完整数据再拍板 |

代码尚未按 Q1 修改!这是下一会话的第一步。

## 2. 证据链(本会话完成,全部在 experiments/results/ 下)

### 2.1 v5 实现 + 验证(上一会话已做)
- `W_LAMBDA = 0.8`(A+1,从 0.25 上调);λ 映射 small→0/large→10/middle→4;A 臂 `_default_delivery` 按画像 λ 选点。
- 约束 v5:B1 加严 = C1 GC 35-70(100nt 滑窗)+ CAI≥0.8 硬约束 → 共 6 条(C1/C2/C6/C7/M1/CAI)。
- 全量 pytest **649 passed 1 skipped**(×2 次)。
- IL-2 preflight:A 臂 R3 2/3 PASS、R4 3/3 PASS(机制修复有效);C 臂回放 R3 0/3(旧 LLM 选集未看新 U,已知局限)。
- 预注册 v5 已同步:PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md(§17)。

### 2.2 真实 C 臂探针(4 靶完成,A1AT/Insulin/EPO/GFP)
日志:`experiments/results/e5_probe_carm_4targets.log`(IL-2 单靶在 e5_probe_carm_il2.log)。

| 靶点 | wt_gc | B1 pool 通过率 | C 臂真实结果 | crit3 |
|---|---|---|---|---|
| IL-2 | 0.385 | 192/315 (61%) | R3=True;3 画像 R1+R4+D1-D3+e2e 全 True;cr=1.00 | ✅ |
| A1AT | 0.520 | **9/315 (2.9%)** | R3=False;D2=False;D3=False;e2e/R1/R4=True | ❌ |
| Insulin | 0.646 | **0/315 (0%)** | 交付为空 → 评估崩溃(ValueError) | ❌ |
| EPO | 0.603 | **0/315 (0%)** | 同上 | ❌ |
| GFP | 0.384 | **0/315 (0%)** | 同上 | ❌ |

**结论 1:** A+1 机制修复在 IL-2 上端到端成立(真实 LLM 看到 λ 倾斜 U 后选出 λ-consistent top-1)。
**结论 2:** B1 加严过度,5 靶中 4 靶被结构性清零。full S1 会直接崩溃(空交付 → `evaluate_delivery` 的 D3 `max()` 空 iterable)。
**结论 3:** crit1(C≥0.8 且 C>A)结构性不可达——pool 通过数 ≥5 时 A/C 臂 e2e 都饱和到 1.0,平局。

### 2.3 B1 杀手约束诊断(脚本:diag_e5_b1_constraint_killer.py;日志:e5_b1_constraint_diag.log + _v2.log)
关键发现:诊断放宽敏感度**必须用滑动窗口语义**重算 C1(`m.sliding_window_gc_out_of_bounds(c["sequence"], lo, hi)`),不能用全局 GC——全局 GC 全在 [25,80] 内但滑窗约束只放行 27/315。

per-constraint pass(/315):

| 靶点 | C1 滑窗(35-70) | C6 | C7 | CAI(≥0.8) | joint |
|---|---|---|---|---|---|
| A1AT | 27 | 312 | 297 | 189 | 9 |
| Insulin | **0** | 249 | 295 | 306 | 0 |
| EPO | **0** | 312 | 315 | 306 | 0 |
| GFP | 165 | 246 | 315 | **0** | 0 |

放宽敏感度(joint,单约束放宽):

| 放宽 | A1AT | Insulin | EPO | GFP |
|---|---|---|---|---|
| GC [35,70](现状) | 9 | 0 | 0 | 0 |
| GC [30,75] | 60 | 0 | 9 | 0 |
| GC [30,80] | 60 | 92 | **306** | 0 |
| GC [25,80] | 153 | 92 | 306 | 0 |
| CAI≥0.7 | 9 | 0 | 0 | 0 |
| CAI≥0.6 | 9 | 0 | 0 | **112** |

**杀手定位:** Insulin/EPO = C1 滑窗 GC 上限 70(高 GC 靶);GFP = CAI(低 GC 靶);A1AT = C1+CAI 双杀手。
**⚠ 重要警示:** 用户拍板的 GC[30,80]+CAI≥0.7 **联合**效果未直接测量(诊断是单约束放宽)。GFP 在 CAI≥0.7 下仍为 0(需 CAI≥0.6 才有 112)→ **GFP 在用户拍板阈值下大概率仍为 0/315**。下一会话 preflight 5 靶复验必须特别检查 GFP,若仍为 0,需向用户呈报并询问(选项:GFP 单独降 CAI 至 0.6 / 全靶 CAI 0.6 / 接受 GFP 0-pass 作为 S1 证据)。

## 3. 下一会话执行步骤(按序)

1. **改代码** `experiments/run_e5_constraint_nav.py`:
   - `GC_MIN, GC_MAX = 35.0, 70.0` → `30.0, 80.0`(L362)
   - `CAI_MIN = 0.8` → `0.7`(L366)
   - 同步更新 docstrings:L63/L75(6 条约束说明)、L65-66(C1 35-70 → 30-80)、L839 注释、§4 文档段。
   - 注意 `BOUNDARY_GC_MIN/MAX = 20/80`(M1 边界约束)保持不变,勿混淆。
2. **全量 pytest**(基线 649 passed 1 skipped)。
3. **preflight 5 靶复验**:`python experiments/preflight_e5_s1_lambda_fix.py <target>`(接受 argv;IL-2 已跑过可跳过,重点 A1AT/Insulin/EPO/GFP)。**特别看 n_pass 与 GFP**(见 §2.3 警示)。若 GFP 0-pass → 停,呈报用户询问。
4. **重跑真实 C 臂探针**(4 靶或全 5 靶):`python experiments/probe_e5_carm_il2.py <target>`。背景跑:
   ```
   setsid nohup bash -c 'for t in A1AT Insulin EPO GFP; do echo "===== $t $(date +%H:%M:%S) ====="; python experiments/probe_e5_carm_il2.py "$t"; echo "rc=$?"; done; echo ALL_PROBES_DONE' > experiments/results/e5_probe_carm_4targets_v6.log 2>&1 &
   ```
   probe 脚本已知坑:rec 顶层无 `elapsed_seconds`(已修复,读 `rec["arm_results"]["C"]["elapsed_seconds"]`);空交付会崩(已 try/except 兜底,rc=2)。单靶 ~10-30min(池构建 3-14min + LLM)。
5. **呈报 5 靶 crit3 完整证据 → 拍板判据①**(仍"暂不定")。判据①选项已列出:e2e 改 C≥0.8 且 C≥A(ties 过)/ directionality ⑤ 升主判据 / 维持 v5 → NO-GO。
6. **判据①拍板后**:
   - GO → 重跑 S1 全量:`cd rna_agent_system && setsid nohup python experiments/run_e5_constraint_nav.py s1 > experiments/results/e5_s1_r4.log 2>&1 &`(~1h,**勿覆盖 e5_s1.log**);GO 前先在 MODEL_API_USAGE.md 预登记 S2。
   - NO-GO → 呈报。

## 4. 纪律(继续遵守)

- **git 操作必须先问用户**(工作树大量未提交修改)。
- **判据/阈值变更必须呈用户拍板**(AskUserQuestion),并同步预注册文档(PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md §17 追加 v6)。
- 工作目录可能被外部切回项目根:**一律用绝对路径,或在命令内 `cd rna_agent_system &&`**。
- **勿杀微服务**(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py)。
- RNARL 8008 重启必须带 `PYTHONPATH=<rna_agent_system>`(start.sh 本身缺)。
- 第 3 轮产物已归档 `e5_s1_round3_archive/`,重跑覆盖前勿删。
- S1 重跑 log 用 `e5_s1_r4.log`,勿覆盖 `e5_s1.log`。
- 探针/probe 产物写 `/tmp/e5_probe_carm/`,不污染 results/。

## 5. 关键文件索引

| 文件 | 说明 |
|---|---|
| experiments/run_e5_constraint_nav.py | 主 driver(改 B1 阈值的地方) |
| experiments/preflight_e5_s1_lambda_fix.py | 无 LLM 预演(接受 target argv) |
| experiments/probe_e5_carm_il2.py | 真实 C 臂探针(接受 target argv) |
| experiments/diag_e5_b1_constraint_killer.py | 约束杀手诊断(滑动窗口语义已修正) |
| experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md | 预注册(§17 已有 v5 记录) |
| experiments/results/e5_probe_carm_4targets.log | 4 靶探针日志(本会话) |
| experiments/results/e5_b1_constraint_diag_v2.log | 诊断日志(本会话) |
| experiments/results/HANDOFF_2026-08-08_E5_A_FIX_IMPLEMENTED_PREFLIGHT_DONE.md | 上一会话 handoff |
