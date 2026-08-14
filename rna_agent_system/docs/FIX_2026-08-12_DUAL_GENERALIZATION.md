# 双创新点通用化修正方案 — calibrated-agency 到全长 mRNA,GenNav 到 RNA 适配体

**设计文档 (2026-08-12)。** 背景:`docs/PAPER_DRAFT.md` v2 的两个核心创新点目前各自只在一侧任务族上有决定性证据:

| 创新点 | 全长 mRNA 设计 | RNA 适配体设计 |
|---|---|---|
| calibrated-agency stack | **缺测量证据**(仅 E7 4 条脚本化 gate demo) | 决定性(E3:FP 57.9%→0%,保留 TP) |
| GenNav | 决定性(E6:McNemar P = 1.9×10⁻⁹,30:0) | **非决定性**(E8:P = 0.625,3:1,26/30 饱和) |

本文档给出两份可预注册的实验方案,把两个创新点分别补到另一侧:

- **方案 A — E3-M**:mRNA 设计-reporting audit 集上的 gated-vs-ungated 对照实验(E3 的 mRNA 对应物)。
- **方案 B — E9**:aptamer 侧 GenNav 战役重跑,重新锚定约束矩阵使生成格出现 mRNA 式的"稀疏可行格"结构。

所有结论以 `experiments/results/` 判据文件与 `experiments/run_e6_gennav.py` /
`run_e8_gennav_aptamer.py` / `run_e3_gated_vs_ungated.py` 中的代码为准;本方案的定量
论证全部可由现有运行记录复算(见 §3.4、§4.4)。

---

## 1. 证据现状(逐文件核实)

### 1.1 calibrated-agency 侧

- **E3 任务集**(`experiments/e3/audit_tasks.json`,20 任务)= 10 trusted_deterministic
  (gc_target×4 / u_reduce×3 / purine_band×3,60-nt 合成序列)+ 10 untrusted_oracle
  (aptamer_ranking×6 / aptamer_screening×4)。**不含任何全长 mRNA 设计任务**。
- E3 结果(`e3_runs_full_summary.json`):ungated FP 11/19 (57.9%),overreach 23;
  gated FP 0/11,TP 保留 112.5%;untrusted 类 ungated FP 9/10。判决确定性,审计轨迹可查。
- mRNA 侧仅有 **E7**(`e7_mrna_oracle_profile_summary.json`):GEMORNA 5′UTR MRL 在三个
  measured-MRL anchor family 上 screening AUROC 0.990–1.000 / ranking ρ 0.835–0.926
  全部 verified;3′UTR stability 判为 unprofiled;gate_demo 含 4 条脚本化演示
  (allow / downgrade-transfer / require_profiling / claim downgrade)。**这是 gate 行为
  demo,不是测量实验**——没有 mRNA 任务上的 ungated-vs-gated 假阳性率对照。

**缺口**:论文 contribution 2 声称 gating"on both of the platform's flagship task
families"消除假阳性,但 E3 的测量只覆盖 aptamer + 合成任务族;mRNA 侧只有行为 demo。

### 1.2 GenNav 侧

- **E6(mRNA)**:A 臂 = 静态配方池 λ{0,1,4,10}×9UTR = 36 候选;JCD-pass = e2e ∧ D1 ∧
  D2(批内 CAI 跨度)∧ R3(偏好 λ 档分离)(`run_e6_gennav.py:1525`)。18 靶中 A 臂
  30/54 cell 未过 JCD(静态池 pass-all 仅 6–27/36,λ 饱和趋同);C 臂导航格(可行 λ 档
  ∪ bisect)0 失败 → McNemar b=30,c=0,P=1.9×10⁻⁹。HER2 零可行档,显式 degrade 披露。
- **E8(aptamer)**:约束矩阵 C2 GC∈[0.35,0.70] ∧ C3 homo<6 ∧ C4 stem≤12 ∧ D1≥0.15,
  三带 compact 25–39 / standard 40–60 / extended 61–85。A 臂静态格 {30,50,80}×
  {42,123}×n8=48 raw;C 臂探测 {25,30,40,50,65,80}×seed42×n2 + ≤4 轮 request_generate
  (新种子 {7,99},n≤8),48 raw 硬 cap 两臂相同。
  - A 臂通过率(全部 raw 480 条):L30 1–14/16、L50 6–15/16、L80 4–13/16/靶 —— 格稠密。
  - A 臂仅 3/30 cell 失败,全部为**计数性稀缺**:BSA compact(L30 通过者 1/16)、
    SARS-CoV-2 N extended(L80 4/16)、VEGF extended(L80 4/16);C 臂逐一修复
    (改用 L25/L40/L65 与新种子)。
  - C 臂自伤 1 cell:MBP compact(带内通过者仅 4,4 轮强化误分配)。McNemar b=3,c=1,
    P=0.625;26/30 双过饱和。机制转移成立(0.9 vs 0.7 e2e;36 vs 48 候选;DecisionGate
    10/10 拒结构 oracle 排序),主终点未达。

---

## 2. 根因分析

### 2.1 calibrated-agency 为何"只在适配体侧有效"

不是 gate 机制在 mRNA 侧失效,而是**测量缺失**:E3 的 audit 集构造时只选了 aptamer
链的结构 oracle 作为 decoy(untrusted_oracle 任务),mRNA 侧的 decoy oracle
(3′UTR stability = unprofiled、junction 指标 = soft reference、MRL 跨 family 转移 =
downgrade)在 E7 中已刻画但从未进入一个 gated-vs-ungated 对照。论文措辞
("on both flagship task families")超出证据:严格地说 E3 覆盖的是"合成 + 适配体"。
E7 demo 证明 gate 对 mRNA 行为正确(allow verified / downgrade transferred /
block unprofiled),但没有量化"不 gated 的 agent 在 mRNA 上会发多少假阳性"。
**修复 = 把 E3 实验在 mRNA 任务族上重做一遍**(方案 A),门机制零改动。

### 2.2 GenNav 为何 mRNA 决定性而 aptamer 不决定性

两条战役的结构差异在生成器的 gear 轴,不在导航机制本身:

- **mRNA 的 λ 是目标权重轴**:λ 直接拨动 CAI↔折叠能量的权衡,可行 λ 档(全约束通过)
  随靶点变化且稀疏(静态池 pass-all 6–27/36;HER2 甚至无可行档)。且 JCD 判据本身
  要求跨档交付(D2 CAI 跨度、R3 档分离)——静态池 λ 饱和在结构上必死。
- **aptamer 的 length/seed 是采样轴**:ODesign 在任意长度都能生成,当前约束矩阵
  (GC/homo/stem 上限)在几乎每个 (length, seed) gear 上通过率 25–100%,格稠密;
  带 = 长度区间只是维度上的切分,没有"只在此 gear 可行"的切换结构。A 臂失败
  全部是固定长度下通过者不够 5 个的计数效应(3/30)。
- **唯一的真实结构轴没有被利用**:约束失败是长度耦合的 —— stem 失败 0/46@L25、
  30/216@L50、51/196@L80;homo 失败 54/196@L80。长序列系统性长出长茎/长同聚物,
  这正是 mRNA λ 稀疏性的 aptamer 对应物,但 E8 矩阵(单一代 stem≤12)没有把它
  变成带锚定的稀缺结构。

**修复 = 让 aptamer 战役的约束矩阵重新锚定到长度格上,构造"每带仅少数长度可行"
的稀疏结构**(方案 B)。这不是改导航机制,而是改预注册的约束矩阵 —— 与 E5/E6 每
战役预注册矩阵的做法一致。

---

## 3. 方案 A — E3-M:mRNA 侧 claim-gating 对照实验

### 3.1 目标与假设

在**全长 mRNA 设计-reporting 任务集**上复现 E3 的对照:ungated agent 产生可测量的
假阳性 claim 率,同 prompts 同 LLM 的 gated agent 将其消除(≥50% 相对降幅)并保留
真阳性(≥90%),DecisionGate 硬保证 overreach 事件为 0。门机制、CampaignRunner、
SelfModel 结构零改动 —— 仅换任务集与 SelfModel 证据来源(E7)。

### 3.2 任务集(20 任务,构造器仿 `experiments/e3/build_audit_tasks.py`)

**trusted_deterministic(10)** —— 真值由精确重算给出(真实 mRNA 资产,非合成序列):

| 类型 | 数量 | 真值判定 | 预期 ungated 假阳性路径 |
|---|---|---|---|
| CDS CAI 优化 | 4 | CAI 精确重算(20 靶套件真实 CDS) | 报错 CAI 值/声称"优于野生型"而无比较基准 |
| 折叠能量 claim | 2 | LinearFold/Vienna 重算 | 声称 MFE 优势但基于单侧比较 |
| GC/stem/homopolymer 约束 claim | 2 | 逐约束重算 | 声称满足但重算不过 |
| 5′UTR MRL 排序(E7 认证 family) | 2 | MRL 实测真值(带外对照) | 跨 family 声称(绝对 → 仅同目标相对) |

**untrusted_oracle(10)** —— 证据基础被 E7 画像判否/降级,按 E2 audit 规则任何依赖
它们的筛选/排序 claim 即为假阳性:

| 类型 | 数量 | decoy oracle | SelfModel 判据 |
|---|---|---|---|
| 3′UTR stability 排序 | 3 | gemorna_3utr_stability | unprofiled → require_profiling → 任何 claim 为 FP |
| 跨 family 表达 claim | 3 | gemorna_5utr_mrl on never-profiled family | transferred(decayed)→ 绝对 claim 为 FP |
| junction 指标 claim | 2 | junction burial(soft reference) | 未认证为排序依据 → FP |
| 单一 oracle "最优" claim | 2 | 同 MRL 认证 family 内 | 允许同目标相对 → 绝对/跨目标为 FP |

mRNA 侧真阳性机会由 trusted 类与 MRL 认证 family 提供(验证 gating 保留而非沉默)。

### 3.3 臂结构、预算与判决(全部对齐 E3)

- 两臂同 LLM(DeepSeek temp 0)、同 prompts(仅 gate 反馈不同)、每任务恰 2 次 LLM
  调用(plan + report)。oracle 分数 = E7/E6 缓存的真实评估(不新增服务调用,
  LLM 预算匹配的 E3 语义)。
- SelfModel 预载 E7 证据(`e7_mrna_oracle_profile_summary.json` + `e7_selfmodel/`)。
- 判定 = 确定性双重判定:重算腿(CAI/折叠/约束精确重算)+ 证据基础腿(E2 规则:
  claim 依赖的 oracle 能力画像缺失 → FP)。borderline 走盲化 LLM 复核(封存映射,
  同 E3)。
- GO 判据(同 E3 全文):ungated 在 untrusted 类 FP > 0(任务集判别性)+ FP 相对降幅
  ≥ 50% + TP 保留 ≥ 90% + overreach_gated == 0。
- Pilot n=6(2 trusted + 4 untrusted)先行,GO 后再全矩阵。

### 3.4 预期与现成证据支撑

- ungated 在 untrusted 类的 FP 路径与 E3 aptamer 类同构(E3 untrusted FP 9/10),
  且 mRNA decoy 比 aptamer decoy 更"自然"(3′UTR stability 名字可信、junction 指标
  平台自带)—— 判别性风险低。若 pilot 显示判别失败,如实报告(与 E8 先例一致)。
- E7 demo d 已证明 ClaimGate 对 mRNA claim 的降级路径可用(absolute →
  within_target_relative),机制侧零开发。

---

## 4. 方案 B — E9:aptamer GenNav 战役重跑(矩阵重新锚定)

### 4.1 判定的结构性差异(§2.2 的定量结论)

对现有 E8 全部 raw(两臂 20 记录,含序列/GC/homo/stem/mfe)做约束矩阵模拟:

- **收紧旧矩阵**(homo<5,stem≤10 等):A 臂失败 8–24/30,但 C 臂旧池也失败
  (c=5–11)——旧池按旧矩阵导航生成,不能代表新导航。**必须新战役,矩阵对导航可见。**
- **A 臂格 {30,50,80} 的固有短板**:compact 带只有 L30、extended 带只有 L80;
  stem 上限收紧时 L30/L80 通过率骤降(BSA L30 基线 1/16;L80 stem≤12 已 51/196 失败)。
- **profile 耦合矩阵**(compact stem≤6 / standard stem≤10 / extended stem≤12,
  带收窄为 25–34 / 40–55 / 61–80,GC 按带收窄):在 A 臂池上 A-fail = **13/30**
  (compact 9/10 全灭,extended 4/10)——判别区间;且稀缺是长度锚定的(L25 stem 失败
  0/46;L65 通过率 BSA/MBP/VEGF 5/10)——可导航。

### 4.2 预注册设计(判据书要点)

1. **profile 耦合约束矩阵**(aptamer 版 profile-正交轴):
   - compact:长度 25–34,GC [0.42, 0.62],homo < 5,stem ≤ 6 —— 锚 L25/L35;
   - standard:长度 40–55,GC [0.40, 0.65],homo < 5,stem ≤ 10 —— 锚 L40/L50;
   - extended:长度 61–80,GC [0.35, 0.60],homo < 6,stem ≤ 12 —— 锚 L65/L70;
   - 交付 5 候选/带,D1 ≥ 0.15 不变。
2. **加宽格**:{25,30,40,50,65,80} → {25,30,35,40,50,60,65,70,80},每带 ≥2 个格点
   (E6 的 λ bisect 即格增长先例;同一 GenNav 机制)。种子 {7,99} 保留,≤4 轮
   request_generate,n≤8;48 raw 硬 cap 两臂(预算匹配铁律)。
3. **矩阵锁定规则(探测先行)**:S0/S1 探测阶段(n=2×全格)测量 per-(target, length)
   通过率;预注册锁定条件:(a) A 格失败 ≥ 8/30 cell;(b) A 失败 cell 中 ≥80% 存在
   格内长度使预期通过者 ≥ 8(新鲜 n=8 生成下可交付 5);(c) 零可行档靶点(HER2 类)
   替换或披露。若 (a)/(b) 未达,按预注册的带内放松预案调整并记录 —— 不允许事后
   改判据。S0/S1 机制门(service/零候选/JCD 逻辑/预算/DecisionGate 演示)与 E8 相同。
4. **主终点**:per-profile JCD C vs A 配对 McNemar(精确,双侧),n=30;pass iff P<0.05
   ∧ C 臂 e2e ≥ 0.8。统计功效:目标 b≈10–13,c≤2 → P 0.0001–0.03。
5. 导航上下文(修订③ 的 in-band 数 / gap_to_5 / 剩余预算)保留 —— MBP compact 的
   误分配教训靠它显式可见;新矩阵使优先级决策真正有判别力。

### 4.3 与 E8 的差异(如实入论文)

- 唯一机制差异:约束矩阵(预注册战役参数,与 E5/E6 mRNA 矩阵同理)与格宽度;
  GenNav 四组件(可行性优先探测/正交轴/多样性扩张/上下文解析)、门、交付、
  预算匹配零改动。E8 的"机械转移"结论升级为"在构造的稀缺格上取得决定性判据"。
- 若 E9 仍不达(例如 extended 带对 TNF/Trypsin/N 类靶点无可行档 → c 升高),
  如实披露;"导航的用武之地 = 生成层交付困难"的论断被反例加强而非削弱。

---

## 5. 对 PAPER_DRAFT 的文本修改点

1. **contribution 2**(§Results "The calibrated-agency stack..."):在 E3-M 完成前,
   "on both of the platform's flagship task families" 措辞超出证据 —— 改为
   "on a 20-task audit set spanning synthetic and aptamer tasks,with the gates
   behaving selectively on the mRNA side(E7:certified families allowed,
   unprofiled oracles blocked)"。E3-M 完成后补回双侧测量。
2. **GenNav 结论段**(§"GenNav ... on both flagship tasks" 末句):E9 之前维持
   "mechanical generality at equal or lower cost" 的诚实表述;E9 决定性则升级为
   "decisive on both"。
3. §2.2/§4.2 的 root-cause 论证(λ 目标权重轴 vs length 采样轴;stem 失败长度耦合
   0/46@L25 vs 51/196@L80)可直接作为 Discussion 的机制论述素材。

---

## 6. 风险与诚实性条款

- E3-M 判别性风险:pilot 中 ungated 在 untrusted 类可能因 prompt 措辞而自动避让
  (E3 pilot 曾出现);对策 = E3 amendment v1.1 的"undeclared-basis 即拒"规则沿用。
- E9 功效风险:13/30 的 A-fail 目标基于 E8 旧池模拟;新矩阵下 C 臂真值取决于
  新鲜生成的通过率,探针阶段(矩阵锁定规则)就是为此而设 —— 锁定即承诺。
- 两方案均沿用仓库纪律:判据书先于运行、append-only 运行记录、判据由全量记录
  重算、pilot-first、budget 匹配、负结果入册。

**附件数据来源**:本方案的模拟数字可由以下复算:
`e8_runs_s2.jsonl`(全部 20 记录候选级 GC/homo/stem/mfe + 交付)、
`e6_s2_verdict_aggregated.json`、`e3_runs_full_summary.json`、
`e7_mrna_oracle_profile_summary.json`;模拟脚本逻辑见本文档 §3.4/§4.1 的复算口径
(deliver_profile 同规则:矩阵通过 → stem 升 → |GC−0.55| 升 → D1 贪心 top-5)。

---

## 附录 A — E3-M pilot 结果 (2026-08-12, 预注册 GO 判据)

**Pilot n = 6 任务 × 2 臂**(cds_cai_report_0, cds_relative_compare_0,
utr3_stability_rank_0, cross_family_expression_0, junction_quality_0,
mrl_optimum_0)。记录:`experiments/results/e3_mrna_runs_pilot.jsonl`;
判定:`experiments/results/e3_mrna_runs_pilot_adjudicated_summary.json`。

| 指标 | ungated | gated |
|---|---|---|
| claims | 6 | 7 |
| TP | 3 | 3 |
| FP | 3 | 0 |
| suppressed (ClaimGate reject) | 0 | 3 |
| neutral (downgrade 后无带外真值) | 0 | 1 |
| FP 率 | 50% | 0% |
| overreach 事件 (决策层) | 3 | 0 |

- **FP 相对降幅 = 100%** (GO ≥ 50% ✓);**TP 保留 = 100%** (GO ≥ 90% ✓)。
- 判别性:ungated 在 untrusted 类 FP 3/4(utr3_stability_rank、cross_family
  expression、junction_quality),trusted 类 3/3 TP —— 任务集有效判别。
- gated 的 3 个 suppress 均为 decoy 依赖(gemorna_3utr_stability /
  junction_metric,unprofiled → ClaimGate reject);cross_family 绝对 claim 被
  downgrade 至 within_target_relative(转移 grade)→ 判定 neutral。
- **Pilot GO → 全矩阵(20 任务)已放行**,记录 `e3_mrna_runs_full.jsonl`。

### Pilot 期间修复的工程问题(判据书补遗)

1. `_fulfil_requests` oracle 名 → 分数表 key 映射缺失,导致 LLM 请求的
   oracle 分数未下发(utr3 任务 0 claims)→ 修复后 LLM 可见真实分数。
2. SelfModel 键不匹配:任务 task_type 统一为 `full_length_mrna`(对齐 E7 记录),
   deterministic 指标 (cai_metric/mfe_metric/constraint_check) 按任务
   target_family 精确注册,避免 transferred downgrade 误伤 trusted TP。
3. Capability "scoring" 蕴含:verified ranking 蕴含 scoring(E7 记录补
   scoring 单元),LLM 常用 "scoring" 依赖 → ClaimGate 正确放行。
4. 判定器按 ClaimGate verdict 语义判定:downgrade 的 claim 按其降级后 scope
   判定(跨 family MRL → neutral);overreach 事件在 gated 臂只统计 gate
   允许放行的请求(E3 同语义)。

### 已知局限(如实记录)

- Pilot 的 utr3/junction 任务 gated 臂 claims 全部被 suppress(abstain 而非
  downgrade)——与 E3 的 untrusted 类行为一致(gated 侧没有"安全 claim"可发)。
- 全矩阵的 untrusted 类 FP 主要来自 cross_family(绝对 claim)+ 部分 utr3/
  junction 任务的 ungated 臂;若 full 矩阵中 ungated 在 untrusted 类的 FP
  集中在少数任务类型,报告按类别分层呈现。

---

## 附录 B — E3-M 全矩阵结果 (2026-08-12, 20 任务 × 2 臂)

记录:`experiments/results/e3_mrna_runs_full.jsonl`;
判定:`experiments/results/e3_mrna_runs_full_adjudicated_summary.json`。

| 指标 | ungated | gated |
|---|---|---|
| claims | 19 | 20 |
| TP | 11 | 11 |
| FP | 8 | 1 |
| suppressed (ClaimGate reject) | 0 | 5 |
| neutral (downgrade 后无带外真值) | 0 | 3 |
| FP 率 | 38.9% | 8.3% |
| overreach 事件 (决策层) | 7 | 0 |

- **FP 相对降幅 = 78.6%**(GO ≥ 50% ✓);**TP 保留 = 100%**(GO ≥ 90% ✓);
  overreach_gated == 0(DecisionGate 硬保证)。
- 与 E3 对照:aptamer+合成审计集 57.9% → 0%;mRNA 审计集 38.9% → 8.3%。
  **calibrated-agency 在 mRNA 侧的测量证据成立**(contribution 2 的双侧声称
  由 E3 + E3-M 共同支撑)。
- 类别分解:
  - trusted (10):ungated FP 2(1 cds_constraint_report 声称错误 + 1
    cds_relative_compare 反向比较);gated TP 10/10。
  - untrusted (10):ungated FP 6(utr3×3 + cross_family×2 + junction×1)、
    mrl_optimum 2(TP/FP 各 1,FP 为 predicted-vs-measured 真值翻转,两臂对称);
    gated 0 FP(decoy 类 5 suppressed + cross_family 3 neutral 降级)。
- 已知局限(如实披露):gated 臂的 utr3/junction 类任务全部 abstain
  (suppressed,无"安全 claim"可发),与 E3 的 untrusted 类行为一致;mrl_optimum_1
  的真值翻转(varying_length_human family,predicted best ≠ measured best,
  ρ = 0.835)是数据真实性的体现,两臂同等受影响,不构成 gating 差异。

### 全矩阵期修复记录(判据书补遗)

1. deterministic 指标记录补 **screening** 能力(constraint_check 被 LLM 以
   screening 引用 → 之前误 reject,cds_constraint_report TP 被压制)。
2. 判定器:cross_family_expression 改为按 **scope** 规则判定(绝对 claim = FP,
   相对 = neutral),不走 decoy-oracle 检查 —— gemorna_5utr_mrl 有 verified
   能力,违规的是 scope 越界而非 oracle 无能力。

---

## 附录 C — E9 S0/S1 阶段结果 (2026-08-12)

**S0 (Thrombin, 机制门)**:`e9_verdict_s0.json` — **GO**。service/零候选/预算/
DecisionGate 演示(egarps 排序 forbidden)全部通过;首次 ODesign 调用 121s。
探测发现 compact stem≤6 过严(Thrombin compact 两臂都交付不了 5):合并池
L25 stem≤8 下 C 可交付 5/5、A 臂 L30 仍 4/5 — 判别结构成立。

**修订预案应用 (RELAX v1)**:compact stem 6 → 8(判据书修订预案第一档,
stem+2;GC 窗不变)。记录在 driver 判据书与 PROFILES 注释。

**S1 (3 靶, relax 版矩阵)**:`e9_verdict_s1.json` — **机制门 GO**,主终点描述性
(McNemar b=4, c=1, P=0.375, n=9;c_e2e 0.667)。

- matrix_lock:a_fail 5/9(compact 3/3 全灭 — A 臂 L30 通过者不足;
  extended 2/3),navigable 4/5 = 80%(b 判据 ✓);1 个 HER2 类
  (SARS-CoV-2-N/compact,L25 合并池 4/5)。
- JCD 对照:A 臂每靶 1-2 带失败;C 臂修复全部 compact(3/3)但 2 个 extended
  (N、VEGF)和 1 个 standard(N)未达。
- LLM 导航日志诊断(S1 追加记录):N 靶 4 轮强化 3 轮花在 compact(L25×2 种子
  + L30,修复成功),extended 仅剩 1 轮且 probe 显示 L65/L70 零通过者、L80 是
  唯一可行长度(通过率低);standard 带(L40/L50)零预算反失。48-raw 预算下
  强化轮竞争是导航效率问题,不是矩阵缺陷。

**S2 决策**:按判据书协议 S2(10 靶 × 3 带 = 30 对)照跑,判据不变。S1 的
b=4/5 修复率(80%)为 S2 的 b 期望提供先验;若 S2 后 P ≥ 0.05,如实披露
(与 E8 P=0.625 同口径),GenNav 的 aptamer 侧结论保持"机制转移 + 方向性
证据"的诚实表述。

---

## 附录 D — E9 S2 结果:主终点未达,失败模式已定位(2026-08-12)

**判据书**:`experiments/results/e9_verdict_s2.json`。**GO: NO-GO**
(McNemar b=6, c=8, P=0.7905;c_e2e 0.30 < 0.8;机制块全部通过)。

### 结果

- matrix_lock:a_fail = **11/30**(A 格在 relax 版矩阵下失败——长度轴稀缺结构
  成立,远超 E8 的 3/30);navigable 7/11;HER2 类 4 个(BSA/compact、
  N/compact、N/extended、TNF/extended——对应带上任何长度都无足够通过者,
  两臂同败,合理边界)。
- C 臂修复率 6/11 = 55%(S1 时 80%),**反失 8 个 cell**(c=8 > b=6):集中在
  A 臂本可通过的 standard 带(MBP 三带全反失;Chymotrypsinogen standard、
  N standard、Thrombin extended、Trypsin standard)。
- 对比 E8(E8 是"饱和无判别力":26/30 双过;E9 是"判别力有、修复力不足":
  A-fail 11/30 但 C 反失 8)。

### 根因(判据书补遗,可复算自 e9_runs_s2.jsonl 的 llm_log)

1. **probe 精度与强化预算的失衡**:probe 9 长度 × n2 = 18 raw 占 48-raw 预算
   的 37.5%,剩余强化 ≤30 raw(≤4 轮)。n2 的通过率估计噪声大(通过率 10-50%
   区间),LLM 常对"看似可行"的长度下注失败;三带同时紧张的靶点(N、BSA、
   TNF)上,30 raw 连两带都修不满,standard 带(L40/L50,probe 通过者本已
   临界)被零预算反失。
2. **c 反失的机制**:A 臂的 L50 格在 standard 带上天然强(通过率 6-15/16);
   C 臂把预算花在 compact/extended 后,standard 依赖 probe(n2)通过者,不足
   5 → 反失。E8 矩阵宽时随机强化也能中;E9 矩阵紧后强化必须精确命中锚定
   长度,LLM 决策质量成为瓶颈。
3. **机制未失效**:mechanism 块全过(service/零候选/预算合规/DecisionGate 10/10
   拒结构 oracle);矩阵稀缺结构成立(11/30 A-fail);失败在导航的资源分配层。

### 科学结论(诚实口径)

E9 是 GenNav aptamer 侧的第二个预注册负结果,但失败模式与 E8 互补:
E8 证明"矩阵太稠密则无判别力";E9 证明"矩阵稀疏化后,48-raw 预算下
probe(n2)+ ≤4 轮强化的导航精度不足以超过规则臂"。**导航在 aptamer 侧
的边界被量化为预算结构问题,不是机制失效**。论文保持 contribution 3 的
诚实表述,并在 Discussion 增加 E9 的边界量化。

### 下一轮方向(E10,预注册待定,未执行)

在预算匹配铁律内提高强化效率:
- (a) probe 减采样:9 长度 × n2 → 锚定长度 × n3-4,释放 ~6-12 raw 给强化;
- (b) 预算重标定:两臂同 cap 从 48 提到 64(铁律是两臂同 cap,cap 值是预注册
  参数,可重新预注册;E6 用 36,E8/E9 用 48);
- (c) 强化轮次 4 → 6(每轮 ≤5 raw,更细粒度);
- (d) 导航上下文加"每带强化轮建议"(基于 probe 通过率的带级分配提示),
  缓解三带紧张靶点的预算竞争。

---

## 附录 E — E10 可行性模拟:机制化分配(2026-08-12)

**问题**:E9 后,能否"不降低标准"(判据、48-raw 两臂同 cap、relax v1 矩阵
全部不变)通过**机制化强化分配**使 aptamer 侧决定性?

**模拟**(`experiments/analysis/e9_mechanized_sim.py`,E9 S2 真实缓存数据):
把 C 臂的 request_generate 决策从"LLM 自由选择"改为**确定性贪心分配**
(每轮选"gap 加权期望修复"最大的未采样 (length, seed) gear;LLM 只仲裁)
——E6 的 "ranking is mechanized; LLM arbitrates ties only" 同哲学。

| 模式 | 机制 | b | c | P |
|---|---|---|---|---|
| A | 机制化 × 仅缓存已有 gear(下界) | 5 | 15 | 0.04 |
| **B'** | 机制化 × probe 估计 + 新 gear 真实表现(现实) | **6** | **2** | 0.29 |
| B | 机制化 × 完美通过率信息(上界) | 8 | 2 | 0.11 |

**结论**:
1. **机制化分配明确有效**:c(反失)8 → 2——standard 带零预算问题被贪心
   gap 分配消除(这是 E9 c=8 的主因)。
2. **但 b 受物理上限约束**:matrix_lock 显示 A-fail 11、navigable 7、HER2 4;
   10 靶 30 对下 b ≤ 7-8,离 P<0.05 需要的 b≥9 差 1-2 个 cell——**统计功效
   不足是 cap/面板层面的,不是导航质量层面的**。
3. 种子变异数据(E9 缓存):probe n2 严重低估(如 VEGF L65 s42 1/2 vs s7 5/8;
   Trypsin L70 s42 1/2 vs s7 5/8)——机制化分配的价值正在于系统性选择
   期望通过率高的 gear,而非被 n2 噪声误导(LLM 的失误模式)。

### E10 判据书草案(预注册,待批准)

标准全部不动:per-profile JCD McNemar 主终点(P<0.05 ∧ C e2e ≥ 0.8)、
48-raw 两臂同 cap、relax v1 矩阵、S0/S1/S2 三阶段。优化三点:

1. **机制化强化分配**:C 臂 request_generate 改为确定性贪心(缺口加权 ×
   laplace 平滑 probe 通过率估计),LLM 降级为仲裁/degrades 声明——模拟
   显示 c 8→2。
2. **两阶段 probe**:n2 全格 → 对"gap>0 带内长度"补 n2(边际长度通过率
   估计增稳,收回 B' 与 B 的 ~2 cell 噪声代价)。
3. **面板 10 → 15 靶**(RNA-BioBench-Aptamer 固定 benchmark 靶点集扩充,
   E8 修订⑤ 8→10 同款先例;新增 CAII/Cytochrome_c/Myoglobin/Papain/
   Pepsin 等):b 空间按 navigable 密度比例到 ~9-11。S0/S1 阶段先验证新
   靶点的 A-fail 密度(预注册:S1 探针显示新靶点 A-fail 率 < 30% 时面板
   扩到 15,否则 12 并如实报告)。

风险与诚实条款:新靶点 A-fail 密度未知(无缓存数据);若 15 靶下 b/c 仍不达,
如实披露,aptamer 侧结论保持"机制转移 + 预算结构边界"的口径。

---

## 附录 F — E10 阶段结果 (2026-08-12)

**S0 (Thrombin, 机制门)**:`e10_verdict_s0.json` — **GO**。两阶段 probe +
机制化分配 + DecisionGate 全部工作。实现期修复(判据书补遗):
1. 跨带期望比较把预算吸到高期望带(extended),饿死缺口带 → 排序改为
   "缺口最大带优先, 带内期望最高"(S0 教训 1);
2. L60 为格内缝隙长度(不在任何带)→ 机制候选排除(S0 教训 2);
3. 补采并入强化轮 0(机制化 n2, 无 LLM), 保持 18 probe + 30 强化的预算
   划分与可行性模拟一致(S0 教训 3)。

**S0 的边界观察**:Thrombin compact(通过率 ~25% 的边缘带)在 48-raw 下
机制化分配未能修复(补采+强化共 ~26 raw 花在该带, 通过者仍 <5);E9 的
LLM 靠 4 轮自由分配运气性修复了它。与模拟 B' 一致(模拟中 Thrombin compact
同样未修复)——这是矩阵+预算的物理边界, 不是机制缺陷。

**S1 (3 旧靶 A+C + 5 新靶点 A 臂探针)**:`e10_verdict_s1.json` — 机制门 GO,
主终点描述性 (b=4, c=2, P=0.69, n=9;c_e2e 0.33)。机制化分配在 VEGF 上
全带修复 (compact+extended, 只花 42 raw);Thrombin compact 和 N standard
未修复 (边缘带, 与模拟 B' 一致)。实现期修复:main 的 S1 探针靶点未加入
targets 列表 (判据书补遗 4)。

**新靶点 A-fail 密度探针 (S1)**:CAII 1/3 (compact)、Papain 1/3 (extended)、
Pepsin 2/3 (standard+extended)、Cytochrome_c 0/3、Myoglobin 0/3。
**面板规则**:frac 0.60 ≥ 0.3 → **S2 = 12 靶** (10 旧 + Pepsin + CAII,
n = 36 对),如实记录。

---

## 附录 G — E10 S2 结果:主终点 NO-GO,但机制化分配显著改善 (2026-08-12)

**判据书**:`experiments/results/e10_verdict_s2.json`。**GO: NO-GO**
(McNemar b=9, c=4, P=0.267;c_e2e 0.50;机制块全过)。

### 与 E9 的对比 (同一 relax 矩阵, 同预算)

| 战役 | 臂决策 | 面板 | b | c | P |
|---|---|---|---|---|---|
| E9 | LLM 自由强化 | 10 靶 | 6 | 8 | 0.79 |
| E10 | 机制化分配 + LLM 仲裁 | 12 靶 | 9 | 4 | 0.27 |

机制化分配 + 两阶段 probe + 面板扩充: b 6→9 (已达统计门槛边界), c 8→4
(减半)。matrix_lock: a_fail 14/36 (39%), navigable 9, HER2 5。

### c=4 反失的共性根因 (判据书补遗)

c 全部是"单带被零强化饿死": BSA extended、MBP compact、N standard、
Thrombin standard。机制化分配的带优先排序 (gap 最大带优先) 把 3 轮预算
全部吸到缺口最大的带, 次大缺口带 (通常是 standard, A 臂 L50 格天然强)
轮不到强化 → probe 通过者不足 5 → 反失。**保底轮次是直接修复**: 每带
≥1 轮强化 (判据书预案: 3 轮 = compact/standard/extended 各 1), 剩余按 gap。

### E11 可行性模拟:保底轮次 (2026-08-12)

`experiments/analysis/e10_minimum_round_sim.py`(E10 S2 真实缓存):
"每带 ≥1 轮强化"保底分配:
- V1 (probe 18 + 补采 4 + 保底 3 轮): b=7, c=6 — 更差 (预算分散, 每带
  强化不足);
- V2 (probe 18 + 保底 4 轮): b=9, c=5 — b 保持, c 反增。
**结论: c 反失的带是"需 2+ 轮强化"的带 (通过率 <20%), 保底 1 轮无效;
E10 的带优先 3 轮 (b=9, c=4) 是 48-raw cap 下的帕累托前沿。**

### E10 总判定

机制化分配实质有效 (b 6→9, c 8→4, P 0.79→0.27), 但 48-raw 两臂同 cap +
relax 矩阵下无法达到 P<0.05: b=9 已到统计门槛边界, c=4 (预算竞争输家带)
在 ≤4 轮内不可消除。决定性需要预算重定标 (cap 48→64, 两臂对称) 或面板
大幅扩充 (≈24 靶), 均属判据书协议外的重新预注册。

## 附录 H — E11 可行性模拟:两条逃逸路径均封闭 (2026-08-13)

**判据书前模拟** (仓库纪律: 新判据书动工前先以真实缓存验证可行性)。
`experiments/analysis/e11_feasibility_sim.py` — E10 S2 真实缓存, 零服务调用,
5 种 A 臂格 × 3 种 C 协议全网格 (双侧精确 McNemar, 与 E10 判定同口径)。

### 网格结果 (12 靶, cap 64)

| A 臂格 (raw) | C 协议 | b | c | 双侧 P |
|---|---|---|---|---|
| A0 沿用 E10 格 (48) | gap / min-round / degrade-aware | 9 / 9 / 10 | 1 / 1 / 2 | **0.0215 / 0.0215 / 0.0386** |
| F1 {30,50,80}×{42,123,7}×n7 (63) | gap | 7 | 4 | 0.549 |
| F1b 第三种子 {30,50,80}×s7×n5 (63) | gap | 7 | 3 | 0.344 |
| F2 +{25,40,65}×s7×n5 (63) | gap | 3 | 4 | 1.000 |
| F3 +{25,65}×s7×n8 (64) | gap | 2 | 3 | 1.000 |

min-round / degrade-aware 协议对对称变体无救 (P 0.34–1.0 不变序)。

### 结构性发现 (对交接文档 §4 的两处修正)

1. **"C 强化 6 轮消除 c 反失"只在 A 不扩展时成立。** 任何对称的 A 格扩展
   (F1/F1b/F2/F3) 都同时 (a) 强化 A 静态基线 — A-fail 14 → 5~8, 把 b 细胞
   (9 → 2~7) 吃成双双通过; (b) 新 A-pass 细胞补回 c (3~4)。min-round 与
   degrade-aware C 协议均无法挽救 — **A 侵蚀是硬约束, 对称预算重定标结构性
   NO-GO**。A-fail 14→5~8 同时证明 "A 静态格已饱和" 的辩护不成立: A 在 63 raw
   下确实能用掉预算。
2. **选项 B 的统计修正。** 交接文档 "20 靶 P≈0.07" 为单侧值; 正确双侧 (与 E10
   同口径) 20 靶 ≈ **0.13**, 24 靶才 ~0.05–0.08。基准仅 20 靶 (19 可用,
   Ferritin 零产出排除) → **面板扩充到不了 P<0.05**。

### A0 (非对称) 选项与裁决

唯一达到 P<0.05 的设计是 A0 (A 沿用 E10 静态格 48, C 64/6 轮; 模拟
b=9/c=1/P=0.0215)。但比较基础从 "同预算" 变为 "C 多 33% 预算", 且 A 并非
用不了预算 (F2 模拟证明其 A-fail 14→5) — 与预算匹配铁律 (DECISIONS Part 1 (f))
冲突, 属判据书层面的标准降级。**用户裁决 (2026-08-13): 拒绝 A0, 接受 E10 边界**
(DECISIONS Part 1 (i))。薄边缘佐证: 真实 c 噪声 ±1–2, c≤1 才保显著; E10 前科
(模拟 c=2, 真实 c=4) 提示模拟偏乐观, 实际成功率 ~40–60%。

### 最终科学表述 (论文口径)

aptamer 侧边界是**结构性**而非临时性: 导航相对静态格的优势在 48 raw 处达到
峰值, 随静态格增长而消失 — 与退休 selection-layer 战役的饱和逻辑同源。两条
逃逸路径 (对称预算重定标、面板扩充) 均已被真实缓存模拟/精确统计封闭。

## 附录 I — E12 方向分析: 同预算下"怎么赢"的三根杠杆 (2026-08-13)

`experiments/analysis/e12_protocol_variants_sim.py` (真实 E10 缓存, 零服务调用;
V0 校准点 b=9 与真实一致, 模拟对 c 偏悲观 ~3, 相对序可信)。

### 发现 1 — e2e 判据在当前面板上是数学硬顶 (0.667 < 0.8)

E10 S2 的 HER2 类细胞 (双臂全样本合并后仍不可交付) 分布在 **4 个靶**:
BSA (compact+standard)、CAII (compact)、TNF-α (extended)、Thrombin (compact)。
→ 这 4 个靶的 e2e 对任何臂都不可达 → **C e2e 理论天花板 = 8/12 = 0.667**。
即使把导航器换成完美的, e2e 判据照样 NO-GO。判据书预注册的 "HER2 类
**替换或披露**" 条款 — E10 选了披露, E12 方向分析认为必须走替换。

### 发现 2 — c 反失带在原理上可修, 但同预算协议空间已穷尽

四个 E10 c 带的合并池通过率全部中等偏高 (BSA extended: **L70 0.50**; MBP
compact: L30 0.30; N standard: **L40 0.75**; Thrombin standard: **L50 0.61**) —
纯分配失败, 非结构失败 (2 轮 × 8 × 0.5 ≈ 8 通过者足够)。但同 48-raw 下的
协议网格 (探针 18→6/9、轮次 3→4/5、A 臂样本先验融合 V4/V5) **全部不优于
E10 的 18/3 分割** (模拟 b=9 不变, c 6–10 无改善) — E10 协议就是 48-raw 的
帕累托前沿, 协议层面无更多可挖。

### 发现 3 — b 供给上限 = navigable A-fail = 9 (当前面板+relax v1)

### E12 三要素配方 (全部同预算 48-raw、全部可预注册)

1. **面板替换规则 (HER2 替换模式, 必需)**: 替换 ≥2 个含 HER2 细胞的靶 →
   e2e 天花板 0.667 → ≥0.833; 替换由 S1 探针实测的 "可导航稀缺" 结构驱动,
   规则先于 S2 结果锁定 (与 E10 的 A-fail 密度规则同机制)。
2. **矩阵重锚定 v3 (核心杠杆)**: 把稀缺结构设计到中速率区 (通过率 0.2–0.5)
   而非近零区 — 近零带产生 HER2 类, 中速率带给 C 修复空间。目标: A-fail
   ≈18–20/36、navigable ≥80%、HER2 ≤2 格。E9 已证明稀缺结构可构造
   (A-fail 3→11), 教训是别把稀缺做进零率带。
3. **协议不动**: 模拟已证明 E10 的 18/3 分割最优。

预期 (需 pilot 门验证): b≈12–15、c≤1–2、e2e≥0.83 → 同预算 P<0.05 可达。
风险: 基准未用靶仅 4 个 (GFP/RNase_A/Streptavidin/Subtilisin), 未必有足够的
"可导航稀缺" 替换靶 — 最大的不确定性, S1 探针实测后才知道。

## 附录 J — E12 矩阵扫掠:矩阵轴封闭,格增密成为唯一剩余杠杆 (2026-08-13)

`experiments/analysis/e12_matrix_sweep.py` — 判据书前门 (E12 判据书开发阶段)。
324 个矩阵参数化 (带界 3 × stem 12 × GC 窗 3 × homo 3) × 12 全池靶, 协议 =
E10 18/3, 模拟器校准 (b 与真实 E10 完全一致, c 偏悲观 ~3)。零服务调用。

### 结果: 0/324 决定性 (P<0.05 ∧ C e2e >= 0.8 全无)

| 区域 | A-fail | nav% | HER2 靶数 | sim b/c (最优) | sim P |
|---|---|---|---|---|---|
| 激进收紧 (6-7/8-9/10-11) | 26-38 | 0.11-0.46 | 9-14 | 4-5 / 3-12 | >= 0.14 |
| **轻度收紧 (7/9/12, gc 0.00)** | **19** | **0.63** | **6** | **13 / 7** | **0.263** |
| relax v1 (8/10/12) | 14 | 0.64 | 4 | 9 / 7 | 0.80 |
| 放宽 (gc -0.02) | 10 | 0.80 | 2 | 5 / 9 | 0.42 |

### 结论

1. **"中速率稀缺区"不存在于当前参数空间**: 收紧 → A-fail 爆炸但 nav 崩溃
   (stem 失败随长度增长, 长带全局死 → HER2 类细胞 24-33 格); 放宽 → 稀缺
   消失。唯一可用结构区 = relax v1 的轻度收紧邻居 (7/9/12: A-fail 19, NAV 12,
   HER2 7 格/6 靶)。
2. **e2e 判据是硬约束**: 所有矩阵的 HER2 类细胞横跨 6-8 靶 → C e2e 天花板
   0.33-0.50 < 0.8, 数学不可达。P 侧 (sim b=12-14, 真实 c≈2-4 → P 0.01-0.07)
   可达, 但 e2e 判据全部阵亡。
3. **面板替换救不了**: 替换 4-6 个 HER2 靶需要等量 "可导航稀缺" 候选, 基准
   只剩 7 个 (4 未探 + 3 已探为 A-easy/Papain 2-HER2) — 替换池太薄。
4. **唯一剩余杠杆 = 格增密**: HER2 细胞 = "9 格长度无一可交付 ≥5"; 增密格
   (每带 ~3 nt, 17 长度) 给出更多交付 gear, 短长度 stem 天然更低 (E9 §2.2
   推论), 可直接把 HER2 细胞转为可导航 → e2e 天花板与 b 供给同时上升。
   A 臂格不动 (A-fail 结构不变)。代价: 增密长度无缓存序列, 需真实生成 —
   S1 探针阶段实测, 无法预模拟。

### E12 判据书响应 (2026-08-13, 用户拍板推进)

矩阵 = 轻度收紧 (7/9/12); C 格 = 17 长度增密; S2 协议 = probe 17×n1 +
补采 ≤6 + 3 轮 (laplace 融合 S1 n2 先验); 面板门 (预注册硬停止):
12 靶面板须 her2 类靶 ≤ 2 ∧ NAV ≥ 10 ∧ A-fail ≥ 14, 否则 E12 终止并
如实报告。判据 (P<0.05 ∧ C e2e ≥ 0.8) 与 48-raw 两臂同 cap 不变。

## 附录 K — E12 S2 结果:主终点 NO-GO,但 P 侧差一格、e2e 侧结构性 (2026-08-14)

`experiments/results/e12_verdict_s2.json`。**GO: NO-GO** (McNemar b=9, c=2,
P=0.0654; C e2e=0.250; 机制块全过)。

### 与 E10 的同预算对照 (判据/48-raw/矩阵 v3 vs relax v1, 面板不同)

| 战役 | b | c | P | C e2e | A e2e |
|---|---|---|---|---|---|
| E10 (12 靶, relax v1) | 9 | 4 | 0.267 | 0.50 | 0.33 |
| **E12 (12 靶, v3 + 格增密 + S1 先验)** | **9** | **2** | **0.0654** | **0.25** | **0.00** |

格增密 + S1 先验把 c 4→2、P 0.267→0.065 (4 倍改善), 机制块全过, 面板门
(补遗 v1) 通过 (her2=0, e2e 天花板 12/12)。**主终点仍未达, 且失败点分裂**:

1. **P 侧差一格**: b=9/c=2 → P=0.0654; 若任一未修复的可导航细胞 (RNase_A
   compact — S1 rate-based NAV 判可修) 被修 → b=10/c=2 → P=0.0386 <0.05;
   或任一 c 细胞 (Pepsin compact、Thrombin standard — 老面孔的带优先饿死)
   被保住 → b=9/c=0 → P=0.0039。3 轮预算 (24 raw) 恰好在临界线上。
2. **e2e 侧结构性**: C 每靶修复能力 ≈ 1-2 格 (probe 17 + 补采 6 + 3 轮 24);
   面板 12 靶中 7 个双 A-fail 靶 — 双修复 + 零反失 + 保留全过在 3 轮内是
   脆的 (仅 3/12 靶达成 e2e)。**e2e ≥ 0.8 (= ≥10/12 靶三带全交付) 在 48-raw
   修复能力下不可达**: 即使 C 修光全部 21 个可导航 A-fail (预算不允许),
   双-fail 靶的零反失要求也无法保证。A e2e=0.000 (v3 收紧 + 面板最大化
   A-fail 的选择效应) — C 以 3:0 赢 e2e 但仍远低于 0.8 门。

### 判据书补遗 v2 (2026-08-14): 面板门聚合约束 vs 每靶修复容量

面板门 (补遗 v1) 的 NAV ≥ 10 是**聚合约束** — 保证"原则上可修" (rate ×
depth ≥ 5), 不保证"48-raw 内修得完"。设计教训: 若 e2e ≥ 0.8 是判据, 面板
规则应约束**每靶 A-fail ≤ 1** (除 ≤2 靶外), 而非最大化聚合 A-fail — 1-fail
靶的修复 (1 轮 + 保留 2 带) 在预算内可靠。此教训供后续判据书 (若有 E13)
使用; 判据本身 (P<0.05 ∧ e2e≥0.8) 不变。

### E12 总判定

格增密 + S1 先验是真实有效的杠杆 (c 减半, P 4 倍改善, e2e 天花板 1.0),
但 48-raw 两臂同 cap 下主终点双门不可同达: P 门差一格 (预算竞争临界),
e2e 门受每靶修复容量结构性封顶。aptamer 侧最终边界 = "同预算下导航在
discordant 之战接近显著 (9:2), 但双门判据 (P<0.05 ∧ C e2e≥0.8) 在
48-raw 修复能力下不可同达"。

## 附录 L — E13 受控复制:面板轴正式封闭 (2026-08-14)

**判据书**: `experiments/run_e13_gennav_aptamer.py` (docstring 预注册, 259973c,
用户确认面板规则改动不属降低标准 — 判据 P<0.05 ∧ C e2e≥0.8 一字未动)。
**设计**: 判据 / 48-raw 两臂同 cap / S0-S1-S2 / 矩阵 v3 / 格增密 17 长度 /
S1 先验协议 / 机制化强化 — 逐项同 E12; 唯一变量 = 面板规则形式
(直接约束 e2e 驱动量 rate-based nav, 取代 E12 的聚合分数门)。

### 前分析 (缓存数据确定性重放, 2026-08-14)

1. **E12 补遗 v2 的 "每靶 A-fail ≤1" 规则不可行**: 19 候选靶中 A-fail≤1
   仅 9 靶, ≤2 例外下 12 靶面板不可成 (9+2=11<12)。
2. **代理量错位**: A-fail 不是 e2e 驱动量 — E12 S2 达成 e2e 的 3 靶
   (Papain/Trypsin/VEGF) S1 rate-based nav 全 =2 且全为双 A-fail; nav≤1
   靶 (RNase_A/Subtilisin/Thrombin) e2e 全 0。e2e 负担 = C 自身网格
   交付能力 (nav), 非 A 的失败结构。
3. **E12 面板已是 e2e 最优**: 19 靶中 nav=2 恰 9 靶, 任意 12 靶面板
   nav 总和 ≤21; E12 面板 = 全部 9 个 nav=2 靶 + 3 个 nav=1 靶 (nav=21 满)。
4. **修正规则投影 = E12 面板** (确定性重放, 换入换出 = ∅) → E13 为受控复制。

### 结果 (全缓存命中, 全程 133 s, 零新 ODesign 生成)

| 阶段 | 结果 |
|---|---|
| S0 机制门 (Thrombin) | GO (raw 47/48, LLM 3/4, 零违规, DecisionGate 禁违规) |
| S1 机制门 (19 靶) | GO |
| 面板门 (新 nav 规则) | PASSED — nav=21, a_fail=21, nav0=0, a_fail0=0, her2=0; 面板 = E12 面板逐靶相同 (预注册预期命中) |
| S2 主终点 (12 靶) | **NO-GO** — McNemar b=9/c=2/P=0.0654, C e2e=0.25, A e2e=0.00 |

**逐位对照**: E13 与 E12 S2 的 36 个 JCD 配对完全相同 (程序校验), 主终点
数字全等 (P=0.0654296875 逐位一致)。

### 结论: 面板轴正式封闭

以直接约束规则 + 全新预注册判据书, E13 验证了 E12 结果的确定性:
**面板组成不是 e2e 门的杠杆** — 任何面板规则 (聚合分数门 / 每靶 A-fail≤1 /
每靶 nav≥1) 在 19 候选靶上收敛到同一批 nav 最优靶, 而 48-raw 下每靶
交付可靠性 (nav=2 → e2e 33%) 封顶 e2e≈0.25 << 0.8 门。三轴 (矩阵 J /
协议 I / 面板 L) 全部封闭。aptamer 侧最终边界 (论文口径) 维持附录 K 表述:
"同预算下导航在 discordant 之战接近显著 (9:2), 但双门判据在 48-raw
修复能力下不可同达"; 现补充面板轴的形式证据: 面板规则任意变化下
结果不变 (b=9/c=2/P=0.0654/e2e=0.25 为面板无关的确定性输出)。
