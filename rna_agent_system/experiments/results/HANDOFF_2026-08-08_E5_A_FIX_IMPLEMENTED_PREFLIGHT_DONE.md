# 交接提示词(2026-08-08 晚间:档位 A 已实现+pytest 通过+预演验证完成,下一决策点待用户拍板)

> **用法**:新会话先读本文件。背景链:`HANDOFF_2026-08-08_E5_S1_NOGO_DECISION_PENDING.md`(S1 NO-GO+诊断+原待拍板)→ **本文件(A 实现+预演证据+新待拍板)**。
> 项目根:`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`,主工程 `rna_agent_system/`。**Bash 工作目录可能被外部切回项目根——所有命令用绝对路径或同条内 `cd rna_agent_system &&`;git 命令 `-C <项目根>`**。

## 0. 一句话现状

**档位 A 三处改动已实现(用户已拍板授权),全量 pytest 649 passed 1 skipped;IL-2 预演(重建池+回放)证实:λ_pref 机制在规则层(A 臂)R3 已修复(0/3→2/3 分离),但权重 0.25 太弱——R4 反受损(偏好 λ 候选非全局 U-max),C 臂真实场景 R3 大概率仍 fail;且 crit1(e2e 饱和)无论如何仍 fail → **按当前实现直接重跑 S1 大概率仍 NO-GO**。尚未启动 S1 重跑,决策点(见 §3)待用户拍板。**

## 1. 本会话完成的事(勿重做)

1. **核实交接状态**:E5 驱动无在跑;RNARL 8008(PID 2844154,PYTHONPATH 已带,health ok)在位;8004/8014/8015 ok。
2. **用户拍板**:档位 A 授权全部 3 项;档位 B 选 **B3 暂不动**(先修 A 看数据)。
3. **实现档位 A**(`experiments/run_e5_constraint_nav.py`,文件本身 untracked):
   - ① `W_LAMBDA = 0.25`,新增 `_lambda_pref_comp()`(λ_rank 档距归一化 span=5),`utility()` 改为 `(0.8×regional + 0.2×global + 0.25×λ偏好)/1.25`;
   - ② `LAMBDA_PREF_VALUE = {small: 0.0, large: 10.0, middle: 4.0}`(映射修正);
   - ③ `_default_delivery()`:首位取画像偏好 λ 的 U 最大候选,再跨 λ 分散,交付按 U 降序排序(§6 既定)。
   - 合成校验通过:三画像 top-1 正确分离(expression→rank0、stability→rank3、balanced→rank2)。
4. **全量 pytest:649 passed 1 skipped**(与基线一致)。
5. **IL-2 预演**(`experiments/preflight_e5_s1_lambda_fix.py`,~5min,重建确定性池+回放 round-3 C 臂选集,产物 `e5_preflight_lambda_fix.log`):见 §2。
6. **第 3 轮产物归档** `experiments/results/e5_s1_round3_archive/`(verdict/log/runs/audit)——重跑会覆盖 verdict,已备份。

## 2. 预演证据(IL-2 重建池,新 U;结论硬证据)

### A 臂(确定性规则层——机制是否生效的干净检验)
| 画像 | top-1 | λ_rank | 对比 round-3 |
|---|---|---|---|
| expression | ld1_u5m_u3l | 1 | round-3 三画像同 rn_u5m_u3l |
| stability | ld10_u5m_u3l | 3 | — |
| balanced | ld4_u5m_u3l | 2 | — |
- **R3: 2/3 对分离 PASS**(v4 判据 ≥1/3):expression-stability λ差2;expression-balanced CAI差0.137;stability-balanced λ差1+CAI差0.041 未过。
- **R4: 2/3 画像 FAIL**(expression/balanced)——偏好 λ 候选(ld1/ld4)非全局 U-max:stability top-1 ld10 的 U=0.8138 高于 expression top-1 的 0.7389,λ 增益上限 ~0.08 翻不动 base U 差距 ~0.13。
- R1 仍 False(交付级 E3 junction 入 U 后重排,round-3 真实 A 臂 R1 也 False——**A 臂 R1 不参与判据**,仅 C 臂考核)。
- D1/D2/D3/e2e 全 True。

### C 臂回放(round-3 LLM 选集 + 新 U 机制化重排;局限:LLM 未看到新 U)
- **R3: 0/3 FAIL**——round-3 选集无 λ0/λ1 候选,重排后 expression/balanced top-1 同为 ld4。
- R4: 1/3 True(仅 stability 的 ld10 恰为全局 max)。
- **局限**:真实第 4 轮 LLM 会看到含 λ 偏好的新 U,选集可能变;但 λ 倾斜太弱,LLM 大概率仍选全局高 U 候选(ld10/GEMORNA 主导)→ C 臂 R3 大概率仍 fail,不确定性主要在此。

### 判据层结论
- **crit1(e2e C≥0.8 且 C>A)必定仍 fail**:池过约束率饱和,两臂 e2e_gene 均 ~1.0 → 平局。→ 只修 A 不可能 GO,必须动 B 档位。
- crit3(R1+R4 全过 + R3):按预演,当前实现下 C 臂 R3/R4 大概率仍 fail。
- **∴ 直接重跑 S1 ≈ 白烧 ~1h + LLM/LD/GEMORNA 预算,判定书大概率仍是 NO-GO(仅 A 臂 R3 修复可证)**。

## 3. 待用户拍板(下会话第一步:呈证据 + 以下选项)

### 档位 A 补强(三选一或组合;均为机制/参数层,但方案先呈用户获认可)
- **A+1 提高 W_LAMBDA**(如 0.25→0.8):使偏好 λ 候选成为各画像 U-max → R3 ✓ 且 R4 ✓ 同获(共享池 per-profile max 不同 = R3 的机制本体)。代价:U 语义向 λ 主导偏移,CAI/MFE 区分度下降;参数从用户已批的 ~0.25 改走,需拍板。
- **A+2 C 臂机制化 λ 选点**:`run_arm_c.finish()` 镜像 A 臂——交付首位强制偏好 λ 候选(§6 C 定义"画像驱动 λ 选点"本应如此)。R3 构造性 ✓;R4 需配合 R4 补进(见下),否则偏好 λ 非全局 max 时 R4 fail。
- **A+3 R4 机制化补全局最优**:交付含全局 U-max 候选(handoff 已注"可选机制化补全局最优进交付")——R4 ✓;但改变交付构成,与 D2(≥3 档)可能冲突,需定实现。

### 档位 B(e2e 饱和,仍未拍板——GO 的必要条件)
- B1 加严约束(CAI≥0.8、GC 35–70)/ B2 e2e 画像级阈值 / B3 维持(判据①永 fail,GO 不可能)。约束阈值是 2026-08-07 拍板定稿,改必先呈用户+改预注册文档。

### 建议顺序(供参考)
A+1(权重 0.8)或 A+1+A+2 → pytest → 重跑 S1 → 看 R3/R4/D1;e2e(B) 与 S1 数据一起定。若用户倾向"先看真实 LLM 对 λ 信号的反应",也可直接按现实现重跑 S1(~1h,预期仍 NO-GO,但获得 C 臂真实数据)。

## 4. 下一步流程(拍板后)

1. 改参数/代码 → `cd rna_agent_system && python -m pytest -q`(基线 649 passed 1 skipped)。
2. 重跑 S1:`cd rna_agent_system && setsid nohup python experiments/run_e5_constraint_nav.py s1 > experiments/results/e5_s1_r4.log 2>&1 &`(~1h;**勿覆盖 e5_s1.log**,runs.jsonl 为 append,verdict 会覆盖但第 3 轮已归档)。
3. 判定:GO → S2(18 靶×3 臂,~2.5–3.5h;启动前在 MODEL_API_USAGE.md 预登记 S2 行);NO-GO → 呈报证据,判据变更必先呈用户。
4. 预演已产生 ~1 靶池的 API 用量(GEMORNA 预测等),建议在 MODEL_API_USAGE.md E5 行加注(可选)。

## 5. 当前运行状态(2026-08-08 晚核实)

| 项 | 状态 |
|---|---|
| E5 驱动进程 | **无在跑** |
| 预演进程 | 已完成(日志完整 `e5_preflight_lambda_fix.log`;可能残留无害的空转 bash 等待循环,会话关闭即清) |
| RNARL 8008 | ✅ PID 2844154(`python -m uvicorn main:app --port 8008`,PYTHONPATH=<rna_agent_system> 已带,health ok)——**start.sh 缺 PYTHONPATH 的坑,重启须手动带** |
| 其他微服务 | 8004/8014/8015 ok(E5 需要);8003/8009/8020 常驻(无 /health 响应属正常) |
| GEMORNA 缓存 | `e5_gemorna_cds_cache.json` 5 靶各 30 条——重跑全复用 |
| pytest | 649 passed, 1 skipped |
| 代码 | `run_e5_constraint_nav.py` 档位 A 三处改动(文件 untracked,git 未提交);新增 `preflight_e5_s1_lambda_fix.py`(untracked) |
| 产物 | 第 3 轮:`e5_s1_round3_archive/`(本轮新备份);预演:`e5_preflight_lambda_fix.log` |

## 6. 工程纪律(用户既定规则)

1. **git 操作必须先问用户**;pytest 基线 649 passed 1 skipped,改代码后必跑全量。
2. **判据/阈值变更必须先呈用户拍板**;机制层改动可自主实施(但方案先呈用户获认可)。
3. 预注册项改动先呈用户(草案 v4 定稿,未拍板一字不改)。
4. 后台驱动:setsid nohup + 日志落盘 + 启动后 pgrep 数进程;命令同条内 `cd rna_agent_system &&`;工作目录可能被外部切回项目根。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`(S1 第 2/3 轮已登记;S2 完成当天补;预演用量可选加注)。
6. 微服务勿杀(8003/8004/8008/8009/8014/8015/8020 + jupyter + GPU_get.py)。
7. verdict 文件每 cell 重写只留最后 cell(判据汇总 = 最后靶 IL-2;逐靶明细在 `e5_s1_runs.jsonl` / `e5_audit/s1_*.jsonl`)。

## 7. 关键指针

- **E5 草案 v4**:`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`(§5 画像/λ 选点、§6 三臂定义、§7 判据、§9 S1 仅考核 C 臂)。
- **驱动**:`experiments/run_e5_constraint_nav.py`(`LAMBDA_PREF_VALUE@390`、`W_LAMBDA@400`、`_lambda_pref_comp@972`、`utility@981`、`_default_delivery@1312`、`mechanize_delivery_order@1292`、`run_arm_c@1517`、`evaluate_delivery@1050`、`run_s1 判据@1960`)。
- **预演脚本**:`experiments/preflight_e5_s1_lambda_fix.py`(改参数后可直接复用验证)。
- **判定书**:`e5_verdict_s0.json`(GO);`e5_s1_round3_archive/e5_verdict_s1.json`(round-3 NO-GO,已归档)。
- **RNARL 服务**:`microservices/rnarl_service/`(start.sh 缺 PYTHONPATH 的坑,见 §5)。
