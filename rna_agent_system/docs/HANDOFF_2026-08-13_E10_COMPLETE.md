# HANDOFF — 2026-08-13: 双创新点通用化(E3-M 完成、E10 完成),下一会话接续点

**会话背景**:用户要求让两个核心创新点在两侧任务族上都有效——
(1) calibrated-agency stack 在全长 mRNA 设计上同样有效;
(2) GenNav 在 RNA 适配体设计上同样有效。
本会话完成 E3-M(mRNA 侧 gating 测量,成功)与 E10(aptamer 侧机制化
分配,主终点仍 NO-GO 但边界精确定位)。**所有实验已结束,无后台任务。**

---

## 1. 当前状态一览

| 实验 | 状态 | 关键结果 |
|---|---|---|
| PAPER_DRAFT 措辞修正 | ✅ 完成 | 6 处更新(摘要/contribution 2/Results/Discussion/Methods/Data availability) |
| **E3-M**(mRNA 侧 calibrated-agency) | ✅ **全过** | pilot GO → full:ungated FP 38.9% (7/18) → gated 8.3% (1/12),TP 保留 100%,gated overreach=0 |
| **E9**(aptamer GenNav,矩阵重锚定) | ✅ 完成(NO-GO) | S0 机制 GO + relax v1;S1 描述性;S2: b=6, c=8, P=0.79 |
| **E10**(aptamer GenNav,机制化分配) | ✅ 完成(NO-GO) | S0 机制 GO;S1 探针→12 靶面板;S2: **b=9, c=4, P=0.267**,c_e2e 0.50 |
| E11 可行性模拟 | ✅ 完成 | 保底轮次变体更差(b=7-9, c=5-6);E10 带优先 3 轮是 48-raw cap 下帕累托前沿 |

**无运行中的实验进程**(已确认)。所有判据书文件已写入。

---

## 2. 关键文件索引

### 设计文档(主入口)
- `docs/FIX_2026-08-12_DUAL_GENERALIZATION.md` — 完整方案文档:
  - §1-2 根因分析;§3 方案 A(E3-M);§4 方案 B(E9)
  - 附录 A: E3-M pilot;附录 B: E3-M full(数字已修正为 38.9%→8.3%);
  - 附录 C: E9 S0/S1;附录 D: E9 S2;附录 E: E10 可行性模拟(机制化分配);
  - 附录 F: E10 S0/S1;附录 G: E10 S2 + E11 保底轮模拟结论

### 论文
- `docs/PAPER_DRAFT.md` — 已更新:
  - 摘要/contribution 2:双侧 gating 测量(57.9%→0% 与 38.9%→8.3%)
  - Results 门控段: E3-M 测量细节
  - GenNav 段: E8(饱和)→ E9(稀疏化,LLM 决策噪声)→ E10(机制化,b=9/c=4)完整边界图谱
  - Discussion/Methods/Data availability 同步

### E3-M 产物(mRNA 侧测量,全部完成)
- 任务集: `experiments/e3_mrna/audit_tasks_mrna.json`(20 任务,构造器 `build_audit_tasks_mrna.py`)
- driver: `experiments/run_e3_mrna_gated_vs_ungated.py`
- 判定器: `experiments/analysis/e3_mrna_adjudicate.py`
- 记录/判定: `experiments/results/e3_mrna_runs_{pilot,full}.jsonl` + `*_adjudicated*`

### E10 产物(aptamer 侧,完成)
- driver: `experiments/run_e10_gennav_aptamer.py`(判据书在 docstring;机制化分配 C 臂)
- 记录/判据: `experiments/results/e10_runs_s{0,1,2}.jsonl` + `e10_verdict_s{0,1,2}.json`
- 缓存: `e10_odesign_cache.jsonl`(读 E8∪E9∪E10;新靶点 CAII/Pepsin 已生成)
- 模拟: `experiments/analysis/e9_mechanized_sim.py`(机制化分配可行性)、
  `experiments/analysis/e10_minimum_round_sim.py`(保底轮次,E11 预演)

---

## 3. 科学结论(论文口径)

1. **calibrated-agency 双侧测量证据成立**:E3(aptamer+合成:57.9%→0%)+
   E3-M(mRNA:38.9%→8.3%,TP 保留 100%,overreach 0)。论文 contribution 2 的
   "both flagship task families" 声称现在有双重支撑。
2. **GenNav 在 aptamer 侧仍未决定性,但边界图谱完整**:
   - E8:矩阵稠密 → 饱和无判别力(3:1,P=0.625)
   - E9:矩阵稀疏化(relax v1)但 LLM 强化决策噪声 → b=6, c=8, P=0.79
   - E10:机制化分配(确定性贪心 + LLM 仲裁)→ b=9, c=4, P=0.267——
     b 达统计门槛边界,c 为预算竞争输家带(通过率 <20% 的带需 2+ 轮强化,
     3 轮预算内不可消除)
   - 模拟:保底轮次更差;48-raw 两臂同 cap 下 E10 是帕累托前沿

---

## 4. 下一步选项(等用户拍板,勿自行启动大规模实验)

> **【2026-08-13 后记】本 §4 已裁决**:E11 判据书前模拟
> (`experiments/analysis/e11_feasibility_sim.py`,E10 S2 真实缓存)证明对称 cap
> 64 结构性 NO-GO(A 静态格扩展侵蚀 b:9→2~7,P≥0.34;c 反失带 6 轮仍不可消),
> 且选项 B 的"20 靶 P≈0.07"为单侧值(正确双侧 ≈0.13,基准仅 20 靶/19 可用)。
> 唯一显著设计 A0(A 48/C 64,P=0.0215)改变比较基础,与预算匹配铁律冲突,
> 用户裁决拒绝。**最终选择:选项 3(接受边界)+ git 提交**。详见
> `DECISIONS.md` Part 1 (i)、`FIX_2026-08-12_DUAL_GENERALIZATION.md` 附录 H、
> `CHANGELOG.md` 2026-08-13。

用户此前要求"S0/S1/S2 三阶段,尽早发现问题",并强调**不降低标准**
(判据 P<0.05 ∧ e2e≥0.8、两臂同 cap、矩阵预注册)。三个选项:

### 选项 1 — E11:cap 重定标 48→64(两臂对称)
- 判据/矩阵不变;cap 是预注册参数(E6 用 36,E8/E9/E10 用 48)
- **待解决**:A 臂 64 raw 的"自然格"定义(3 长度 × 2 种子 × n8 = 48;加种子
  7 → 72;需预注册一个对称且非 rigged 的定义,例如 {30,50,80}×{42,123,7}
  各 n7 或 {30,50,80}×{42,123}×n8 + 每带 1 个锚定长度 × 新种子)
- 预期:C 强化 6 轮(18 probe + 46 强化)→ c 反失带可获 2+ 轮
- 流程:新判据书(复制 E10 driver)→ S0/S1/S2

### 选项 2 — 面板扩充到 ~20 靶
- 判据/预算不动;RNA-BioBench-Aptamer 有 20+ 靶点
- b/c 按比例增长:20 靶 b≈15/c≈7 → P≈0.07;24 靶 → P≈0.05 边缘
- 风险:审稿人可能质疑"扩面板到显著";需预注册面板规则
  (E10 的 A-fail 密度规则先例)

### 选项 3 — 接受 E10 边界
- aptamer 侧结论保持"机制转移 + 预算结构边界";论文已按此写好
- 可选收尾:git 提交全部改动、更新 CHANGELOG/DECISIONS

---

## 5. 已知事项(下个会话注意)

1. **E3-M 数字**:论文/文档已统一为最终判定 38.9% (7/18) → 8.3% (1/12)
   (修正 cross_family 判定语义后的重算;早期记录 42.1% 是修正前的)
2. **E10 判据书补遗**(driver docstring 外):S0 期 3 个实现修复
   (带优先排序/L60 缝隙/补采并入强化轮 0);S1 期 main 探针靶点 bug 修复;
   S2 期面板逻辑 load_records list/dict bug 修复
3. **LLM 配置**:DeepSeek via .env(DEEPSEEK_API_KEY),model 名不能传
   "deepseek"(必须 deepseek-v4-pro 或由 get_deepseek_llm() 默认读取)
4. **服务**:ODesign(8012 GPU)、LinearFold(8015)、GEMORNA(8004)可经
   `ensure_e10_services()` 自动启动;E10 缓存已含 CAII/Pepsin 全部生成
5. **未提交的改动**:大量新文件(experiments/e3_mrna/、run_e3_mrna*、
   run_e10*、e9_mechanized_sim.py、e10_minimum_round_sim.py、docs/FIX*、
   HANDOFF*)+ PAPER_DRAFT 修改——尚未 git commit

---

## 6. 下一个会话的提示词

```text
你是 RNADesignAgent 项目的延续会话。背景:为了让论文的两个核心创新点在
两侧任务族上都有效,上一会话完成了:(1) E3-M —— mRNA 侧 gated-vs-ungated
对照测量,全部判据达成(FP 38.9%→8.3%,TP 保留 100%);(2) E9/E10 ——
aptamer 侧 GenNav 三次尝试(E8 饱和→E9 稀疏化→E10 机制化分配),E10 达到
b=9/c=4 (P=0.267),主终点仍 NO-GO,边界定位为 48-raw cap 下的预算结构
(通过率<20% 的带需 2+ 轮强化,3 轮预算内不可消除)。所有实验已结束,
无后台任务。完整背景见 docs/FIX_2026-08-12_DUAL_GENERALIZATION.md(含
附录 A-G)与本交接文档 docs/HANDOFF_2026-08-13_E10_COMPLETE.md;论文草稿
docs/PAPER_DRAFT.md 已同步(GenNav 段含 E8/E9/E10 完整边界图谱)。

你的任务:
1. 先读 docs/HANDOFF_2026-08-13_E10_COMPLETE.md 和 docs/FIX_2026-08-12_DUAL_GENERALIZATION.md
   附录 G,确认无遗留实验;
2. 向用户汇报当前状态与三个下一步选项(见交接文档 §4):
   A) E11:cap 48→64 重预注册(需先定义 A 臂 64 raw 的对称自然格);
   B) 面板扩充到 ~20 靶(预注册面板规则);
   C) 接受边界,git 提交全部改动 + 更新 CHANGELOG/DECISIONS。
3. 等用户拍板后再行动;若用户选 A/B,必须按仓库纪律写新判据书
   (docstring 预注册)→ S0(机制门)→ S1(方向性/探针)→ S2(主终点),
   任何实现问题记录为判据书补遗,禁止事后改判据。
```
