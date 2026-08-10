# 交接提示词（2026-08-08：S1 第 3 轮正式 NO-GO + 机制诊断完成，修复方案待用户拍板）

> **用法**：新会话先读本文件。背景链：`HANDOFF_2026-08-07_E5_PLAN_B_S0_GO_S1_RUNNING.md` → `HANDOFF_2026-08-08_E5_V4_S1_RERUNNING.md`（v4 判据 + S1 重跑）→ **本文件（S1 NO-GO + 诊断 + 待拍板）**。
> 项目根：`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`，主工程 `rna_agent_system/`。**Bash 工作目录可能被外部切回项目根——所有命令用绝对路径或同条内 `cd rna_agent_system &&`；git 命令 `-C <项目根>`**。

## 0. 一句话现状

**S1 第 3 轮（RNARL 修复后，数据有效）判定 NO-GO（5/5 cell fail）；4 类失败根因已全部从代码+数据定位（λ_pref 未实现、e2e 饱和、R4 判据-机制失配、D1 Insulin 靶特异）；修复方案分档位 A（机制 bug 修复）/ B（设计变更）**已呈用户，等待拍板。当前无任何实验在跑。**

## 1. 本会话完成的事（勿重做）

1. **核实 S1 第 2 轮重跑（06:34–07:27）判定无效**：RNARL 8008 全程宕机（5/5 靶池 `WARN rnarl returned no candidates`，池 306/315 缺 RNARL 档，B 臂语义受损）。产物归档 `experiments/results/e5_s1_r2_rnarl_down_archive/`。
2. **修复 RNARL 8008**：根因 = `start.sh` 未设 PYTHONPATH 而 `main.py:18` `import agent_core`（重启时才发现）。已用 `PYTHONPATH=<rna_agent_system>` 拉起（当前 PID 2844154），验证真实生成 200 OK（21aa→63nt，15s）。
3. **S1 第 3 轮重跑（08:19–09:08，RNARL 在位）**：池 315/315 完整，判定 **NO-GO**（判定书 `e5_verdict_s1.json`，5 cell 全 fail：`E5 s1: 5 cell(s) failed verdict`）。
4. **机制诊断（代码+数据双证）**，见 §2。
5. **MODEL_API_USAGE.md E5 行已更新**（S1 第 2/3 轮实测：LLM 13+13 次、LD 20+20、RNARL 5+0、GEMORNA 0+150；池 315）。

## 2. 诊断结论（证据齐，供修复方案依据）

### 根因 1：R3 分离失败 = `λ_pref` 定义了却从未实现（代码 bug，档位 A）
- `LAMBDA_PREF_VALUE = {small:1.0, large:4.0, middle:4.0}`（`run_e5_constraint_nav.py:390`）**未被 `utility()`/`regional_metric()` 消费**（grep 证实，仅注释提到）。
- 3 画像 U 差异只剩 utr5_axis（0.6/0.4 vs 0.4/0.6 vs 0.5/0.5）与 region_weights（±0.1）——弱到不翻转 top-1。
- 实测：5/5 靶 A 臂、3/5 B 臂、3/5 C 臂的三画像 top-1 **同一候选**；IL-2 的 2/3 分离纯靠 CAI 差 0.063 恰过阈值。
- 预注册 §5 画像表含「λ 选点偏好」列、§6 A 臂「按画像权重选 λ」——实现缺失，非设计问题。
- 附带：λ 档 rank{0:0, 1:1, 4:2, 10:3}，small=1/large=4 仅差 1 档，判据要 ≥2 档 → 映射需配合修正。

### 根因 2：e2e 饱和 45/45 = 判据退化（设计层，档位 B）
- `delivery_e2e_pass` = 交付 5 条全过约束；池过约束率 60–312/315（EPO 99%）→ 任意 5 条全过。
- 约束 C1/C2/C6/C7/M1 阈值是 2026-08-07 用户拍板定稿（且放宽过：GC 上限 80、同聚物 14）。
- 修复方向三选一：B1 加严约束 / B2 e2e 加画像级阈值 / B3 暂不动（判据①依旧 fail）。

### 根因 3：R4 部分失败（3/5 靶各 1 画像）= 判据-机制失配
- R4 要求 top-1 = 约束全过子集 U 全局最大；机制化重排只在 **LLM 选集内**排 → 选集 ≠ 全局 top-5 即 fail。

### 根因 4：D1 Insulin = 靶特异（CDS 330nt，2% 差异 = 6.6nt，315 候选多样不足）

## 3. 修复方案（已呈用户，未拍板——下会话第一步：请用户拍板）

### 档位 A（机制修复 = 实现预注册既定设计；建议直接授权）
1. λ_pref 进 U（λ 偏好分量，建议权重 ~0.25，档距归一化）；
2. λ_pref 映射修正：small→**0**、large→**10**、middle→**4**（画像对档差 2–3，λ 判据可达）；
3. A 臂按画像 λ 选点（§6 既定）。

### 档位 B（设计变更，必须用户拍板）
4. e2e 饱和处理：**B1** 加严约束（CAI≥0.8、GC 35–70）/ **B2** e2e 画像级阈值 / **B3** 暂不动，只修 R3/R4/D1。
5. R4 失配：档位 A 后观察，仍 fail 再议（可选机制化补全局最优进交付）。

**建议顺序**：档位 A(1+2) → pytest 全量（基线 649 passed 1 skipped）→ 重跑 S1（~1h，GEMORNA 缓存 30/靶全复用、RNARL 已在位）→ 看 R3/R4/D1 是否修复；e2e(B) 等数据出来一起定。

## 4. 下一步流程（拍板后）

1. 改代码（λ_pref 进 U + 映射 + 可选 A 臂 λ 选点）→ 跑全量 pytest。
2. 重跑 S1：`cd rna_agent_system && setsid nohup python experiments/run_e5_constraint_nav.py s1 > experiments/results/e5_s1.log 2>&1 &`（后台，~1h，完成即判定）。
3. 判定：GO → S2（18 靶 × 3 臂，~2.5–3.5h；S2 启动前在 MODEL_API_USAGE.md 预登记 S2 行）；NO-GO → 呈报证据，判据变更必先呈用户。
4. S2 预期（诚实预判）：S1 已见 e2e 饱和 + R3/R4/D1 失败，S2 双终点大概率也 NO-GO（饱和下 McNemar discordant=0 → p=1.0；endpoint2 含 R3/R4/D1）。

## 5. 当前运行状态（2026-08-08 ~10:50 核实）

| 项 | 状态 |
|---|---|
| E5 驱动进程 | **无在跑**（S1 第 3 轮已完成） |
| RNARL 8008 | ✅ 在跑（PID 2844154；**注意：须带 `PYTHONPATH=<rna_agent_system>` 启动，`start.sh` 本身缺 PYTHONPATH**；模型已加载，health ready） |
| 其他微服务 | 8004/8014/8015 在跑（S1 拉起，勿杀）+ 常驻 8003/8008/8009/8020 + jupyter + GPU_get.py（勿杀） |
| GEMORNA 缓存 | `e5_gemorna_cds_cache.json` 5 靶各 30 条（idx 0–29）——重跑全复用 |
| 产物 | 第 3 轮：`e5_s1.log`/`e5_verdict_s1.json`/`e5_s1_runs.jsonl`/`e5_audit/`（有效，勿动）；第 2 轮：`e5_s1_r2_rnarl_down_archive/`；首轮：`e5_s1_round1_archive/` |

## 6. 工程纪律（用户既定规则）

1. **git 操作必须先问用户**；pytest 基线 649 passed 1 skipped，改代码后必跑全量。
2. **判据/阈值变更必须先呈用户拍板**；机制层改动可自主实施（但方案先呈用户获认可）。
3. 预注册项改动先呈用户（草案 v4 已定稿，未拍板一字不改）。
4. 后台驱动：setsid nohup + 日志落盘 + 启动后 pgrep 数进程；命令同条内 `cd rna_agent_system &&`。
5. 产生论文数据当天更新 `experiments/results/MODEL_API_USAGE.md`（E5 S1 已更新，S2 完成当天补）。
6. 微服务勿杀；工作目录可能被外部切回项目根，用绝对路径。
7. verdict 文件每 cell 重写只留最后 cell（判据汇总 = 最后靶 IL-2；逐靶明细在 `e5_s1_runs.jsonl` / `e5_audit/s1_*.jsonl`）。

## 7. 关键指针

- **E5 草案 v4**：`experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md`（§5 画像/λ 选点、§7 R1–R4/D1–D3、§9 R1–R4 仅考核 C 臂、§10 S2 双终点、§16 v4 注记）。
- **驱动**：`experiments/run_e5_constraint_nav.py`（`PROFILE_DEFS@373`、`LAMBDA_PREF_VALUE@390`、`regional_metric@926`、`utility@963`、`mechanize_delivery_order@1292`、`write_verdict@1875`、`run_s1` 判据 ~1930–1990、R3@1107、R4@1050）。
- **判定书**：`e5_verdict_s0.json`（GO，S0）；`e5_verdict_s1.json`（第 3 轮 NO-GO）。
- **RNARL 服务**：`microservices/rnarl_service/`（start.sh 缺 PYTHONPATH 的坑，见 §5）。
