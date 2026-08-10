# E2 自家审计（落文）：图 4 主效应 + 图 7B pegaptanib 对比的画像协议复核

> 2026-08-04（W3–4 里程碑「E2 自家审计落文」）。按设计文档 §3 E2(a) 与 §4 Results 3：
> 自家历史 claim 逐条过画像协议复核，以 worked example 形式呈现（**非门控结论 vs 画像复核 vs 预算匹配对照**）。
> 不做"自我撤回"修辞（2026-08-04 用户决定）；本文件是论文 Results 3 worked example 的原料。
> 数据来源全部在 `experiments/results/`：`fig4_summary.json`、`p0_budget_matched_summary.json`、
> `p2_aptamer_calibration_summary.json`、`e1_capability_summary.json`、`fig7_cases/B/case_summary.json`。

## 0. 审计协议（每条 claim 走同一四步）

1. **依赖声明**：该 claim 依赖哪个 oracle、依赖哪种能力等级（CASF 四能力：scoring/screening/ranking/docking）？
2. **画像复核**：该 oracle-靶点组合的画像证据（E1 试点 / P2 校准）是否具备所依赖的能力？
3. **混淆对照**：是否存在非预算匹配等混淆（P0 预算匹配对照为判据）？
4. **门控裁定**：claim 存活 / 降级（重写为画像证据允许的强度）/ 拒绝。

## 1. Claim 1：图 4 主效应——「Type-II BMC 协调提升适配体设计」

### 1.1 非门控结论（当时的写法）

> BMC×1/×2/×3 相对 Serial 在 egarps_component best-of-pool 上显著更优
>（bmc_x1：Wilcoxon p=2.1e-4，q_BH=6.7e-4，Cliff's δ=0.457，n=19 靶点），
> 3-D 超体积 hv3d 同样显著（bmc_x1：p=2.6e-4，q=7.0e-4，δ=0.274，n=57 格）——
> 即「有界多模块协调提升 RNA-蛋白适配体设计质量」。
>（`fig4_summary.json` paired_tests；MANUSCRIPT.md 记录 228/240 成功）

### 1.2 依赖声明（审计第 1 步）

- 主指标 `egarps_component` = EGARPS native_probability，被用作**优化目标 + best-of-pool 排序依据**
  → 依赖 ranking power 与 screening power。
- hv3d 在 (egarps, rhofold, iptm) 三维上计算 → 三个 oracle 的能力全部进入 claim。

### 1.3 画像复核（审计第 2 步）

E1 试点（2026-08-04，29 条目 3 靶点，`e1_capability_summary.json`）与 P2（15 条目，ρ=0.40 / AUROC=0.356）一致：

| oracle × 靶点 | ranking ρ（需 ≥0.6） | screening AUROC（需 >0.8） |
|---|---|---|
| EGARPS np × Thrombin | 0.143 | 0.286 |
| EGARPS np × VEGF | −0.024 | 0.708（CI 0.33–1.0） |
| EGARPS np × PDGF-BB | 0.410 | 0.600 |
| RhoFold pLDDT × 3 靶点 | −0.20 / 0.167 / 0.564 | 0.381 / 0.500 / 0.800（CI 0.33–1.0） |
| Protenix ipTM × 3 靶点 | 0.314 / 0.238 / −0.410 | 0.381 / 0.250 / 0.667 |

**9 个组合无一通过 screening 或 ranking**。所依赖的能力等级不存在——主效应指标的"提升"
不能解释为适配体亲和力/质量提升。P2 进一步给出方向性反证：随机阴性 random30_a
np=0.952、scrambled_tba np=0.987，高于 pegaptanib（2e-6）与 PDGF 适配体（~1e-8）。

### 1.4 混淆对照（审计第 3 步）

- **预算混淆（P0）**：图 4 的 Serial 池 8 条 vs bmc_x1 池 16 条（bmc_x2 16–24）——原比较**未做预算匹配**。
  P0 预算匹配对照（serial_ext16 同样 16 条，12 格）：δ=0.278 < 0.3 预注册阈值，Wilcoxon p=0.129（NS），
  bmc_x1 赢 9/12 格。判定书原话："budget explains the Fig-4 Type-II main effect"。
  措辞纪律（PIVOT §0）：预算可解释大部分增益、协调残差为小效应量（δ≈0.28, NS），不写成"协调完全无效"。
- **内部一致性佐证**：预算不敏感的固定参考点 ASF 标量化 bmc_x1 vs serial **不显著**
  （p=0.073，q=0.103，δ=−0.241，方向甚至为负）；rhofold/iptm 分量全部 NS。
  显著性集中在 (a) 未画像 oracle 的分量，(b) 对池大小敏感的超体积——两条都是混淆通道。
- **墙钟佐证**：Serial 中位 1324 s vs bmc_x1 2630 s（≈2×），与池大小 8→16 同步翻倍。
- **数据质量登记**：bmc_x1 的 BSA seed0/seed1 为 rounds_executed=0 的代码版本异常格
  （2026-07-19/20，EGARPS 链修复前；P3 判定书 caveat）——若该数据进论文需按当前代码重跑。

### 1.5 门控裁定（审计第 4 步）

**不存活。** ClaimGate 降级后的合法表述：

> 「BMC×1 收敛时候选的 EGARPS native_probability 高于 Serial（p=2.1e-4）。但 EGARPS np 对
> RNA-蛋白适配体无已验证的 screening/ranking power（E1 试点，9 组合全灭；P2，AUROC 0.356），
> 且该效应与翻倍的采样预算不可区分（P0 预算匹配 δ=0.278，NS）。因此不许可任何关于
> 适配体亲和力或设计质量提升的结论；BMC 的可辩护价值收敛为自适应预算分配（收敛即停）。」

DecisionGate 反事实：若门控在位，(a) 拿无 ranking power 的 egarps_component 作优化目标/排序依据
会被拒绝或强制预算匹配设计；(b) hv3d 比较会被强制池大小匹配。图 4 实验在规划阶段就会被改写。

## 2. Claim 2：图 7B pegaptanib 对比——「设计候选 vs 已上市药物」

### 2.1 非门控结论（数据原样）

图 7B 反 VEGF 适配体案例（`fig7_cases/B/case_summary.json`，2026-07-31，47 min）：

| 序列 | Kd（文献） | EGARPS np | RhoFold pLDDT | Protenix ipTM |
|---|---|---|---|---|
| 工作流 top 候选 cand_43edb912979a（30 nt） | 无湿实验 | **0.7047** | 82.6 | 0.488 |
| pegaptanib（Macugen 母序列 27 nt） | 49 pM（Tucker 1999） | **5.05e-7** | 42.0 | 0.424 |

非门控读法：设计候选在评分链上比 FDA 批准药物**高 6 个数量级**——若按评分即亲和力解读，
会得出"候选远优于上市药"的荒谬结论。这是 oracle 被用出验证边界的教科书式案例。

### 2.2 画像复核（审计第 1–2 步合并）

- 依赖能力：把 EGARPS np 跨序列比较当亲和力排序依据 → ranking power；把 0.70 当"像天然复合物"
  的通过信号 → screening power。
- 画像证据（VEGF 靶点族）：E1 试点 EGARPS × VEGF——ranking ρ=−0.024（8 binder），
  screening AUROC 0.708（CI 0.33–1.0，不过线）。P2：pegaptanib np=1.9e-6 低于多个固定种子
  随机阴性（0.952/0.543）；TBA（25 nM，最弱真 binder）np=8.6e-4 垫底。
- **结论：np 的跨序排序不携带亲和力信息**。候选 0.7047 vs pegaptanib 5e-7 的差是评分函数的
  系统性失准（高 np 恰恰常见于随机/非结合序列），不是设计胜利。

### 2.3 额外不可比性登记（case_summary 自记录的 caveat）

- EGARPS 对 pegaptanib 打的是 **ProteinX 复合物 PDB**，而工作流候选打的是 **ODesign 生成的复合物**
  （`chain_note` 原文）——复合物来源不同，np 不可直接比。
- pegaptanib 药用形式为 2′-F/2′-OMe 修饰 + PEG 化；锚点评分用的是未修饰母序列
  （`pegaptanib.json` notes；`binding_site_residues` 为 null，登记为 data gap）。
- RhoFold pLDDT / Protenix ipTM 的 VEGF 画像同样全灭（E1 上表），三个分量无一可作证据。

### 2.4 门控裁定（审计第 4 步）

**不存活（作为"优于 pegaptanib"或"高亲和力候选"的 claim）。** ClaimGate 降级后的合法表述：

> 「工作流 top 候选在评分链上得 EGARPS np 0.70，pegaptanib 母序列 5e-7。该 oracle 对
> RNA-蛋白适配体无已验证 screening/ranking power（E1/P2），且两侧复合物来源不同
> （ODesign vs ProteinX）——该数值差不构成候选优于 pegaptanib 的证据，仅作为
> 『评分链输出』如实报告。候选亲和力须经湿实验或已画像 oracle 验证后方可声称。」

DecisionGate 反事实：以 pegaptanib 为参照做"超过上市药"式对比的规划动作，在 VEGF 族画像
缺失/失败的状态下会被直接拒绝；ClaimGate 会把任何 superiority 措辞自动降级为上引表述。

## 3. 存活率与 E2 判定

| 被审 claim | 依赖能力 | 画像证据 | 混淆对照 | 裁定 |
|---|---|---|---|---|
| 图 4 主效应（协调提升设计） | EGARPS ranking/screening | 9 组合全灭（E1）+ P2 NO-GO | P0 预算匹配 δ=0.278 NS；ASF NS | **不存活 → 降级** |
| 图 7B pegaptanib 对比 | EGARPS ranking/screening | VEGF ρ=−0.024 / AUROC 0.708（不过） | 复合物来源不可比；修饰不可表示 | **不存活 → 降级** |

**自家 claim 存活率 0/2 = 0% < 70% 预注册阈值 → E2 审计故事成立**（设计文档 §3 E2 go/no-go）。
注意口径：n=2 是 worked example 主体（唯一数据齐全、不得罪外部作者的真实门控案例）；
文献 claim 复核（E2(b)，3–5 篇外部论文）是后续工作，措辞限"用法复核"、不点名羞辱。

## 4. 论文用法（Results 3 worked example 骨架）

1. **非门控结论**：图 4 p 值与图 7B 数值差原样呈现——这是非门控管线会发出的 claim。
2. **画像复核**：E1/P2 判定书作为判据表（§1.3、§2.2）。
3. **预算匹配对照**：P0 作为第二判据（§1.4）——双判据独立指向同一裁定。
4. **门控裁定对照表**：§1.5/§2.4 的降级表述展示 ClaimGate 输出形态；
   DecisionGate 反事实说明规划层会拦下什么。
5. 叙事定位：不是"我们过去错了"，而是"**没有门控，任何系统（包括我们的旧版）都会发出
   这类 claim**"——这是架构缺口的实证，不是个案失误。
