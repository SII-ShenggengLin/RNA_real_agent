# 两篇 mRNA 序列设计论文的湿实验详细文档

> 本文档基于以下两篇论文及其补充材料整理，聚焦**湿实验（wet-lab）部分**的实验设计、材料、操作流程、检测方法与结果，供实验复现与方案设计参考。
>
> - **论文一（LinearDesign）**：Zhang H. et al. *Algorithm for optimized mRNA design improves stability and immunogenicity.* Nature 621, 396–403 (2023). DOI: 10.1038/s41586-023-06127-z（百度研究院 + 斯微生物 + 加州大学尔湾分校等）
> - **论文二（GEMORNA）**：Zhang H. et al. *Deep generative models design mRNA sequences with enhanced translational capacity and stability.* Science 390, eadr8470 (2025). DOI: 10.1126/science.adr8470（Raina Biosciences + MIT 等）

---

# 第一部分：LinearDesign 论文（Nature 2023）湿实验

## 1.1 湿实验总体设计

LinearDesign 是一种基于"格解析（lattice parsing）"的 mRNA 编码区（CDS）优化算法，联合优化最小自由能（MFE，结构稳定性）与密码子适应指数（CAI，密码子最优性）。湿实验的核心目的是验证：**低 MFE（结构更稳定）+ 高 CAI 的 CDS 设计是否能带来更强的化学稳定性、蛋白表达与体内免疫原性**。全部湿实验围绕两类抗原 mRNA 疫苗展开：

| 实验体系 | 编码蛋白 | 测试序列 | 对照序列 |
|---|---|---|---|
| 新冠（COVID-19）mRNA 疫苗 | SARS-CoV-2 全长刺突蛋白（spike，1273 aa，**不含 2P 脯氨酸突变**，即野生型） | LinearDesign 设计的 7 条亚最优序列 A–G（beam search，b = 500，分布于 MFE ≤ −1400 kcal/mol 的低自由能区域；在 MFE 或 CAI 上互相锚定以便拆解两个变量） | 序列 H：OptimumGene（Thermo/GenScript 类工具）密码子优化的基准序列（该序列曾用于进入 I 期临床的新冠 mRNA 疫苗，CTR20210542）；另设 BNT 序列（与 BNT162b2 几乎相同，但 ①2P 突变改回野生型；②使用与 A–H 相同的 5′/3′ UTR；③使用天然未修饰核苷酸），用于与 BioNTech-Pfizer 疫苗的头对头比较 |
| VZV（水痘-带状疱疹病毒）mRNA 疫苗 | VZV 全长 gE 蛋白 | LinearDesign 设计的 5 条序列 gE-A 至 gE-E | gE-Ther：GeneOptimizer 密码子优化序列；gE-WT：野生型 gE CDS |

所有 mRNA 的编码区两侧均接有相同的 5′ UTR 和 3′ UTR，并带 **70 nt 的 poly(A) 尾**；所有序列**均未使用化学修饰核苷酸**（这是该论文强调的一个特点：仅靠序列优化即获得高稳定性与免疫原性，且降低生产成本）。

## 1.2 mRNA 的体外转录合成（IVT）

- **模板**：线性化质粒 DNA。
- **转录酶**：T7 RNA 聚合酶，体外转录。
- **新冠 spike 序列（A–H、BNT）**：
  1. IVT 反应：37 °C，4 小时；
  2. DNase I（Hongene Biotech）消化去除 DNA 模板；
  3. **酶法加帽**：使用牛痘病毒加帽酶（Vaccinia Capping Enzyme，Hongene Biotech）；
  4. 磁珠纯化：Dynabeads（Thermo Fisher）；
  5. 去磷酸化处理：Antarctic Phosphatase（Hongene Biotech），37 °C，30 min，去除残留的 5′-三磷酸（降低免疫原性杂质）。
- **VZV gE 序列**：采用**共转录加帽**，使用帽类似物 m7(3′OMeG)(5′)ppp(5′)(2′OMeA)pG（Hongene Biotech），"一锅法"反应 30 °C，16 小时；随后 DNase I 处理、磁珠纯化。
- **制剂**：mRNA 疫苗采用 **LPP（lipopolyplex，脂多聚复合物）** 递送系统包封（斯微生物平台，配方参照文献 Persano et al., Biomaterials 2016）。

## 1.3 mRNA 理化性质表征

### 1.3.1 非变性琼脂糖凝胶电泳（结构紧凑度/迁移率）

- mRNA 样品悬浮于 Ambion RNA storage buffer（Thermo Fisher）；
- **75 °C 变性 5 min，冰浴骤冷**；
- 上样于 **1% 非变性琼脂糖凝胶**，130 V，室温电泳 1 h；
- 成像：Gel Doc XR+ 凝胶成像系统（Bio-Rad）。
- **结果**：MFE 越低（结构越紧凑）的序列迁移率越高——spike 序列 A（MFE 最低）迁移最快，序列 H（MFE 最高）迁移最慢；VZV 的 gE-A 同样迁移最快。说明 LinearDesign 的 MFE 计算与分子实际折叠紧凑度一致。（未裁剪凝胶图见补充图 1。）

### 1.3.2 体外化学稳定性（in-solution degradation）与半衰期

- mRNA 样品于 **37 °C** 孵育于含 Mg²⁺ 的 PBS 缓冲液：
  - **10 mM Mg²⁺**：取样时间点 0、1、2、4、8、12、16、24、32、48、60 h；
  - **20 mM Mg²⁺**（加速降解）：取样时间点 0、1、2、4、8、12、15、18、21、24 h；
- RNA 完整性用 **Qsep100 毛细管电泳系统**分析，以电泳图谱上全长 mRNA 所占比例表示，归一化至 0 h；
- 半衰期拟合：一相衰减方程（one-phase decay）Y = (Y₀ − plateau)·e^(−KX) + plateau，其中 Y₀ = 100、plateau = 0，半衰期 T½ = ln(2)/K；
- 每个降解实验独立重复 3 次，数据以 mean ± s.d. 表示。
- **结果**：
  - spike 序列 A（MFE 最低）降解最慢：T½ = **20.0 h**（10 mM Mg²⁺）/ 12.6 h（20 mM）；序列 H（MFE 最高）最快：T½ = 3.9 h / 3.3 h；
  - VZV gE-A：T½ = **66.5 h**（10 mM）/ 50.7 h（20 mM），对照 gE-Ther 仅 10.9 h / 5.9 h；gE mRNA 整体比 spike 更稳定（分子更短）；
  - 头对头比较：序列 A、C 的降解速率显著低于 BNT 序列（BNT 与 H 的 MFE、CAI、半衰期非常接近）。

## 1.4 细胞水平的蛋白表达检测

### 1.4.1 细胞培养

- 细胞：HEK293（ATCC）；
- 培养基：DMEM（Hyclone）+ 10% FBS（GEMINI）+ 1% 青霉素-链霉素（Gibco）；
- 培养条件：37 °C，5% CO₂。

### 1.4.2 mRNA 转染

- 转染试剂：Lipofectamine MessengerMAX（Thermo Scientific）；
- 用量：**每孔 2 µg mRNA + 6 µl Lipofectamine 试剂**，按说明书配制复合物；
- 转染后孵育 **24 h 或 48 h** 收样检测。

### 1.4.3 流式细胞术检测 spike 抗原表达

1. 收集细胞，活/死细胞染料染色（Fixable Viability Stain 510，BD），5 min；
2. 洗涤后，一抗孵育：抗 spike RBD 嵌合单克隆抗体（1:100 稀释，Sino Biological），30 min；
3. 洗涤后，二抗孵育：PE 标记抗人 IgG Fc（1:100 稀释，BioLegend），30 min；
4. 上机：BD Canto II（BD Biosciences）；每次实验采集 **10,000 个活细胞**；
5. 数据分析：FlowJo V10.1（Tree Star），以平均荧光强度（MFI）定量。

- **结果**：
  - 7 条 LinearDesign 序列（A–G）的 spike 表达均显著高于密码子优化基准 H（48 h）；序列 D、G（CAI 与 H 几乎相同但 MFE 更低）表达量为 H 的 2.3 倍，序列 A 达 2.9 倍；
  - VZV 体系：gE-B、gE-C、gE-D（CAI 与 MFE 均落在"甜区"的分子）表达最高，优于 gE-A（CAI 最低）与 gE-E（MFE 最高），验证了**联合优化 CAI + MFE** 的必要性；
  - 序列 A、C 的蛋白表达显著高于 BNT 序列（24 h 与 48 h）。
- 统计：Kruskal–Wallis 方差分析 + Dunn 多重比较（分别对 H 组或 gE-Ther 组）。

## 1.5 小鼠体内免疫原性研究

### 1.5.1 免疫方案

- 动物：C57BL/6 小鼠，6–8 周龄；spike 实验每组 n = 6，VZV 实验每组 n = 5（头对头 BNT 比较实验 n = 5）；
- 给药：**肌肉注射（i.m.）LPP 制剂化的 mRNA 疫苗，每次 10 µg**；
- 免疫程序：**初免 + 2 周后加强免疫（共两针，间隔 2 周）**；
- 采样：加强免疫后 14 天采集**血清与脾脏**。
- 伦理：实验经上海南方模式生物 IACUC 批准，遵循中国实验动物相关法规；实验未随机化、未设盲。

### 1.5.2 结合抗体 ELISA（抗-spike IgG / 抗-gE IgG）

1. 包被：重组 SARS-CoV-2 spike 胞外域蛋白或 VZV gE 蛋白（Genscript），用包被缓冲液（BioLegend）稀释，**100 ng/孔**包被 96 孔 EIA/RIA 板（Greiner Bio-one），4 °C 过夜；
2. 洗涤：1× PBS-T（0.05% Tween-20）；
3. 封闭：2% BSA（PBS-T 配制），室温 2 h；
4. 加样：血清系列稀释液，室温孵育 2 h；
5. 二抗：HRP 标记山羊抗小鼠 IgG（1:10,000），室温 1 h；
6. 显色：TMB 底物（Invitrogen），BioTek 酶标仪读取 **450 nm** 吸光度；
7. 终点滴度（end-point titre）：取信号超过背景 **2.1 倍**的最大血清稀释倍数的倒数。

- **结果**：
  - 新冠疫苗：序列 A–D（位于设计空间最优边界附近的分子）诱导的抗-spike IgG 滴度比基准 H 高 **57–128 倍**；序列 A、C 显著高于 BNT 序列；
  - VZV 疫苗：gE-B、gE-C、gE-E 诱导的抗-gE IgG 显著高于 gE-Ther 与 gE-WT。

### 1.5.3 假病毒替代中和实验（sVNT，surrogate virus neutralization test）

1. 96 孔板（Greiner Bio-one）包被重组人 ACE2 蛋白，**100 ng/孔**，4 °C 过夜；
2. 1× PBS-T 洗涤，2% BSA 室温封闭 2 h；
3. HRP 标记的 RBD（100 ng/ml）与系列稀释的免疫小鼠血清**等体积（各 60 µl）混合**，37 °C 孵育 30 min；PBS 处理小鼠血清为阴性对照；
4. 取 100 µl 混合液加入包被板，37 °C 孵育 15 min；
5. 洗涤后 TMB 显色，BioTek 酶标仪读 450 nm；
6. **IC₅₀** 用四参数 logistic 非线性回归计算。

- **结果**：序列 A–D 诱导的中和抗体滴度比基准 H 高 **9–20 倍**；A、C 显著高于 BNT。

### 1.5.4 ELISpot（抗原特异性 T 细胞应答）

- 试剂盒：Mouse IFNγ ELISpotplus Kit（Mabtech）；
- 操作：每孔加入 **3 × 10⁵ 个小鼠脾细胞** 至预包被抗小鼠 IFNγ 捕获抗体的孔中，与 spike 蛋白或 VZV gE **肽库（10 µg/ml）** 共孵育 **20 h**；
- 洗涤后加入链霉亲和素-碱性磷酸酶（1:1,000），室温 1 h；
- BCIP/NBT 底物显色，斑点用 Immunospot S6 分析仪（CTL）计数。
- **结果**：仅 LinearDesign 设计的 mRNA 诱导了强劲的、Th1 偏向的 spike 特异性 IFNγ⁺ T 细胞应答；基准 H 诱导的应答非常有限。

## 1.6 统计学与可重复性

- 数据表示：算术均值或几何均值 ± 相应标准差（柱状图高度或符号）；
- 两组比较（体内实验）：双尾 Mann–Whitney U 检验；
- 多组比较（体外表达）：单因素 ANOVA + Dunn 多重比较（或 Kruskal–Wallis）；
- 软件：GraphPad Prism v8；显著性标注 \*P < 0.05，\*\*P < 0.01，\*\*\*P < 0.001；
- 体外实验独立重复 3 次；动物实验完成 1 次；凝胶电泳重复 3 次结果一致；
- 未预先估算样本量；实验未随机化，研究者未设盲。

## 1.7 LinearDesign 湿实验主要结论

1. MFE 与凝胶迁移率、化学稳定性直接相关：MFE 最低的序列 A 半衰期 20.0 h，比基准 H（3.9 h）长约 5 倍；
2. 低 MFE + 高 CAI 联合优化的分子蛋白表达最高（最高为 H 的 2.9 倍），且优于 BNT162b2 序列；
3. 小鼠体内：抗-spike IgG 最高提升 **128 倍**，中和抗体提升 **9–20 倍**，并诱导 Th1 偏向的 T 细胞应答；结论在 VZV gE 疫苗体系中得到重复验证；
4. 全部序列未用化学修饰核苷酸即获得上述效果。

---

# 第二部分：GEMORNA 论文（Science 2025）湿实验

## 2.1 湿实验总体设计

GEMORNA 是基于 Transformer 的生成式 RNA 模型，包含 **GEMORNA-CDS**（编码器-解码器结构，输入蛋白质序列、生成 CDS）和 **GEMORNA-UTR**（GPT 式仅解码器结构，从头生成 5′/3′ UTR）两个模块。湿实验验证围绕以下层次递进展开：

1. **CDS 层面**：以去稳定化萤火虫荧光素酶（Fluc2P，带促降解突变的变体）为报告蛋白，比较 GEMORNA 生成的 4 条 CDS（GMR-FL-CDS1～4，贪心/采样解码）与 5 个对照（GenScript 在线工具 CAI-G、IDT 在线工具 CAI-I、LinearDesign 联合优化序列、biLSTM-CRF 深度学习序列、商业化载体 pGL4.11 的 CDS）；
2. **UTR 层面**：固定 CDS 与另一端的 UTR，分别筛选 12 条 GEMORNA 5′ UTR 与 10 条 3′ UTR，对照包括天然 UTR 及其衍生物、基于结构的理性设计、机器学习+遗传算法设计、商用 mRNA 药物（BNT162b2、mRNA-1273）所用 UTR；
3. **UTR 配对**：8 条 5′ UTR × 11 条 3′ UTR 组合（Fluc2P 与 CD19 CAR 两种 CDS）；
4. **全长 mRNA**：4 个蛋白靶标——Fluc2P、新冠 spike 抗原（两步法：先选最优 CDS 再配 UTR）、NanoLuc 与人促红细胞生成素 EPO（直接设计全长）；
5. **环状 RNA（circRNA）**：NanoLuc、EPO 及 CD19 CAR circRNA，并做 CAR-T 体外杀伤功能验证；
6. **体内实验**：小鼠 EPO 表达、小鼠新冠疫苗免疫原性。

## 2.2 质粒构建

- 方法：**限制性内切酶克隆 + Gibson 组装**；
- 本研究所有 mRNA 与 circRNA 构建体的序列详见论文补充表 S1（线性 mRNA）与表 S2（circRNA）。

## 2.3 mRNA 体外合成（IVT）

1. **模板制备**：PCR 扩增 IVT 模板，用 Zymoclean Gel DNA Recovery Kit（Zymo Research，D4008）纯化；
2. **转录反应**：T7 Co-transcription RNA Synthesis Kit（Synthgene，10111-3011）；**UTP 全部替换为 N1-甲基假尿苷三磷酸（m1Ψ，N1-Methylpseudo-UTP）**；
3. 反应条件：**37 °C，2 小时**（新冠疫苗 mRNA 为 1 小时）；
4. 模板去除：DNase I（NEB）消化；
5. 纯化：磁珠（beads）纯化后用于后续实验。

> 与 LinearDesign 论文的关键区别：GEMORNA 全部使用 m1Ψ 修饰核苷酸，验证其设计与上市 mRNA 药物所用化学修饰兼容。

## 2.4 环状 RNA（circRNA）合成与纯化

- **拓扑结构**：采用基于**内含子自剪接的环化方法（intron-based circularization，即 PIE 法）**；CDS 上游使用 IRES 驱动翻译（Fluc 筛选阶段用 EMCV IRES；后续 NanoLuc/EPO 设计使用挖掘到的 PbV-A4、PbV-A3 等 IRES；CD19 CAR 用 CVB3 IRES）。GEMORNA 采用**简化的拓扑结构**（AI 生成 CDS + 挖掘的 IRES），对照为 Chen et al.（Cell 2022）系统优化过的拓扑（含筛选/优化的 UTR、iHRV-B3 IRES + Apt-eIF4G、PABP 等元件）；
1. PCR 扩增 IVT 模板，Zymoclean 胶回收纯化；
2. IVT：HiScribe T7 High Yield RNA Synthesis Kit（NEB），37 °C，2 h；
3. DNase I 去除模板；
4. **环化**：补加 GTP 至终浓度 2 mM，**55 °C 孵育 15 min**，诱导自剪接环化；
5. 磁珠纯化 IVT 产物；
6. **RNase R（LGC Biosearch Technologies，RNR07250）消化**，去除残留的线性 RNA 前体；
7. 再次磁珠纯化，得 circRNA。

## 2.5 细胞培养与转染/电转

### 2.5.1 细胞系与培养基

| 细胞 | 来源/货号 | 培养基 |
|---|---|---|
| HEK293T | ATCC CRL-3216 | DMEM（Gibco 10569010）+ 10% FBS（Gibco A5669701）+ 100 U/ml 青霉素 + 100 µg/ml 链霉素 |
| HepG2 | ATCC HB-8065 | 同上 |
| Jurkat | ATCC TIB-152 | RPMI 1640（Gibco 11875093）+ 10% FBS + 双抗（Gibco 15140122） |
| NALM-6（稳定表达 firefly luciferase-GFP） | 上海奥维生物 SAc0269LG | 同 Jurkat |

培养条件：37 °C，5% CO₂ 湿润培养箱。

### 2.5.2 转染与电转

- **HEK293T、HepG2**：转染前 1 天铺 96 孔板，使用 **Lipofectamine MessengerMAX（Gibco，LMRNA015）** 按说明书转染；
- **Jurkat 细胞、原代 T 细胞**：电转，Gene Pulser Xcell 电穿孔系统（Bio-Rad），按说明书操作（详见 2.9）。

## 2.6 报告基因与蛋白表达检测

### 2.6.1 萤火虫荧光素酶（Fluc）检测

- 每孔加入 **100 µl Bright-Glo Luciferase 试剂（Promega，E2620）**，混匀，室温孵育 5 min；
- 转移 100 µl 混合液至平底白色不透明板，酶标仪测化学发光。

### 2.6.2 NanoLuc 荧光素酶检测（分泌型，用于长时程监测）

- 各时间点取 **5–20 µl 细胞培养上清**，转入白色不透明平底板，用培养基补至 100 µl；
- 加入等体积 Nano-Glo Luciferase Assay Reagent（Promega，N1130），酶标仪测发光；
-  circRNA 实验最长监测至转染后 **144 h**（每 24 h 测一次），并计算 144 h/24 h 表达比值作为持久性指标。

### 2.6.3 EPO ELISA（人促红细胞生成素）

- 试剂盒：Abcam **ab274397**，按说明书操作；
- 样品：各时间点收集的细胞培养上清，**1:200 稀释**后检测。

### 2.6.4 膜表面 spike 蛋白表达（流式）

- mRNA 转染 HEK293T 后 24 h、48 h 收细胞；
- 活细胞染料染色 5 min → 洗涤 → 抗 spike RBD 嵌合单抗（**1:100**，Sino Biological，40150-D001）30 min → 洗涤 → PE-抗人 IgG Fc（**1:100**，BioLegend，410708）30 min；
- BD FACSVerse 流式分析。

## 2.7 体外表达与稳定性主要结果（细胞水平）

- **CDS 比较**：GEMORNA 的 4 条 Fluc2P CDS 表达量最高达 biLSTM-CRF 的 20 倍、pGL4.11 的 4.8 倍（48 h，HEK293T）；48 h/24 h 活性比值更高，提示 mRNA 胞内稳定性更好；HepG2 中结果一致（图 S5）；
- **5′ UTR 比较**：基准池中 BNT162b2 的 5′ UTR 最强；12 条 GEMORNA 5′ UTR 中有 **5 条达到或超过 BNT162b2 5′ UTR**；HEK293T 与 HepG2 结果相关性 r² = 0.92；
- **3′ UTR 比较**：10 条 GEMORNA 3′ UTR 中 **8 条达到或超过 BNT162b2 3′ UTR**（图 S8；其中 GMR-3U4～3U7 是在 GMR-3U1 基础上加入稳定化基序的衍生序列，但未见进一步提升）；
- **UTR 配对**：>80% 的 UTR 组合优于 BNT162b2 UTR 基准，Fluc 活性最高提升 7 倍；5′ UTR 主导表达调控，但 UTR 组合的表现具有蛋白靶标依赖性（Fluc2P 与 CD19 CAR 间相关性 r² = 0.096），说明不存在普适最优 UTR 组合；
- **全长 mRNA（Fluc2P）**：最优设计 GMR-FL-F5 表达量较基准 1（IDT CDS + α-珠蛋白 UTR）提高 **41 倍**，较基准 2（pGL4.11 CDS + BNT162b2 UTR）提高 8.2 倍（HepG2 中 15.9 倍）；
- **全长 mRNA（NanoLuc）**：7 条全长设计均优于强基准（BNT162b2 UTR + 文献 CDS），24–72 h 持续提升（图 S10）；
- **全长 mRNA（EPO）**：7 条设计中 6 条优于基准（密码子优化 CDS + BNT162b2 UTR）；GMR-EPO-F6 表达持续时间更长；
- **circRNA（NanoLuc）**：GEMORNA 设计（简化拓扑）累积表达显著高于 Chen et al. 优化拓扑基准；GMR-NL3 在 72 h 时活性为 24 h 的 3 倍，而基准 48 h 后持续下降；
- **circRNA（EPO）**：最优设计 144 h 累积表达为基准的 **13.8 倍**；144 h/24 h 表达比最高 46.5%（基准仅 2.5%）。

## 2.8 人原代 T 细胞激活与扩增

1. 复苏冻存人外周血单个核细胞（PBMC，上海奥理生物/Shanghai Origin Biotechnology，PB003F-C）；
2. 用**包被的抗 CD3（BioLegend 317301）与抗 CD28（BioLegend 302901）抗体（50 ng/ml）**激活；
3. T 细胞扩增培养基培养 **6 天**：RPMI 1640 + 10% CTS Immune Cell Serum Replacement（Gibco A2596101）+ 2 mM GlutaMAX（Gibco 35050061）+ 50 µM β-巯基乙醇 + 100 IU/ml IL-2（PeproTech 200-02）+ 双抗（Gibco 15140122）；
4. 37 °C、5% CO₂ 湿润环境培养。

## 2.9 电转制备 CD19 CAR-T 细胞

1. 电转前对扩增 T 细胞计数，台盼蓝（Trypan Blue）评估活率，无菌 PBS 洗 2 遍；
2. 用 Gene Pulser Electroporation Buffer（Bio-Rad）重悬至 **1 × 10⁷ cells/ml**；
3. 分装至 1.5 ml 离心管（**每条件 100 µl**），加入 IVT 制备的 mRNA 或 circRNA，吹打混匀；
4. 转入 **0.2 cm 间隙电转杯**（Gene Pulser/MicroPulser Cuvette，Bio-Rad）；
5. 电转参数：**方波，220 V，2 ms**；
6. 电转后立即转入含 **900 µl 预温 T 细胞扩增培养基**的 24 孔板。

## 2.10 流式细胞术（CAR 表达检测）

- 染色：PE 标记人 CD19 蛋白（Acrobiosystems，CD9-HP2H3）检测 CD19 CAR；共染抗人 CD3（BioLegend 300412）、CD4（344612）、CD8（344748）；
- 活性染料：Zombie Violet Fixable Viability Kit（BioLegend）；门控：FSC-A/SSC-A 圈淋巴细胞 → FSC-A/FSC-H 去粘连体；门内淋巴细胞活率 >98%；
- 仪器：BD FACSVerse；
- **结果**：GEMORNA circRNA 电转后 24 h，CAR 表达 MFI 较密码子优化基准（Benchmark-1）高 **28 倍**、较专利 circRNA（Benchmark-2）高 5.6 倍；电转后 **120 h 仍有约 50% 细胞 CAR 阳性**（两个基准在 72 h 内即消失）；CAR 阳性率最长追踪至 192 h（以 6 h 阳性率归一化电转效率，图 S14）。

## 2.11 CAR-T 体外杀伤实验（细胞毒性）

- 靶细胞：NALM-6（组成型表达 firefly luciferase）；
- 方法：NALM-6 铺 96 孔板，按设定的效靶比（E:T，图 5M 为 **1:6**，图 S15 为 **1:3**）加入 CD19 CAR-T 细胞共培养，最长 7 天；
- 检测：DPBS 洗涤、裂解后用 Bright-Glo（Promega E2620）测荧光素酶活性，残余发光信号反映存活肿瘤细胞；
- 对照组：仅肿瘤细胞、未转染 T 细胞（Mock）、Benchmark-1（密码子优化 circRNA）、Benchmark-2（专利 circRNA）；
- **结果**：GEMORNA circRNA 转染的 T 细胞可有效清除 NALM-6 细胞；密码子优化基准几乎无杀伤作用，专利基准效果亦弱于 GEMORNA 设计。

## 2.12 LNP 包封与表征

1. RNA 用**柠檬酸缓冲液（pH 4.0）稀释至 90 µg/ml**；
2. 脂质配方（摩尔比）：**ALC-0315 : DSPC : 胆固醇 : ALC-0159 = 46.3 : 9.4 : 42.7 : 1.6**（即 BNT162b2 型配方）；
3. 混合：脂质与 RNA 溶液按 **1:3 体积比**，用 **INano L+ 微流控设备（Micro&Nano）** 混合；
4. 换液浓缩：LNP-RNA 制剂用 1× PBS（pH 7.2–7.4）稀释 40 倍，Amicon Ultra 超滤管（Merck）浓缩；
5. 质量检测：
   - RNA 浓度与包封率：Quant-it RiboGreen RNA Assay Kit（Invitrogen，R11490）；
   - 粒径：动态光散射（DLS），Zetasizer Lab（Malvern）。

## 2.13 小鼠体内实验

- 伦理：遵循中国实验动物法规，经北京晨欣高科生物科技 IACUC 批准（方案号 20240017MSE）；小鼠随机分组，研究者未设盲。

### 2.13.1 体内 EPO 表达

- 动物：6–8 周龄雌性 **BALB/c 小鼠，每组 n = 4**；
- 给药：**尾静脉注射 3 µg LNP 制剂化 RNA**（mRNA 或 circRNA），对照为仅 LNP（安慰剂），1 ml 无菌注射器；
- 采血：各时间点采血清，ELISA 测 EPO；
- **结果**：
  - 线性 mRNA：GEMORNA 设计比基准表达更强、更持久；GMR-EPO-F7 在 24 h 表达量为基准的 **15 倍**；
  - circRNA：3 条 GEMORNA circRNA 在 24 h 的体内 EPO 表达均显著高于基准，最优者高 **121 倍**；6–168 h 内维持更高且持久的表达。

### 2.13.2 新冠 mRNA 疫苗免疫

- 动物：6–8 周龄雌性小鼠，**每组 n = 5**（方法部分记为 C57BL/6J；正文图 4 描述为 BALB/c——两处记载不一致，复现时可按方法部分的 C57BL/6J 执行并核实）；
- 给药：**肌肉注射 LNP 制剂化 mRNA，1 µg 或 3 µg**，对照为仅 LNP；**2 周后加强免疫一针**；
- 采血：初免后第 0、7、21、28、42、56 天等多个时间点采血测 anti-spike IgG；
- 测试序列：GMR-CV-F1/F2/F3（GEMORNA 全长设计）、BNT162b2 序列、LinearDesign Seq-C CDS + BNT162b2 UTR（相应两个密码子改入 2P 突变，m1Ψ 修饰）；
- **结果**：GEMORNA 全长设计在多个时间点诱导的抗体滴度均高于 BNT162b2 与 LinearDesign 序列（3 µg 剂量 Day 21 及 1 µg 剂量均如此）。

### 2.13.3 抗 spike IgG ELISA

1. 血清 **56 °C 灭活 30 min**；
2. 包被：重组 SARS-CoV-2 S 抗原（Novoprotein，DRA49）包被 96 孔板；
3. 加样：血清从 **1:100** 起始做 2 倍系列稀释，100 µl/孔，室温孵育 2 h；
4. 洗涤 3 次；加 HRP 标记山羊抗小鼠 IgG（1:10,000），室温 30 min；
5. 洗涤 4 次；加 HRP 底物与终止液，TECAN Spark 酶标仪读 **450 nm（参比 630 nm）**；
6. 阳性对照：抗 SARS-CoV-2 spike RBD 抗体（Sino Biological，40592-MP01）；
7. 终点滴度：四参数 logistic 曲线拟合，取信号为背景 **2.1 倍**的血清稀释倍数倒数。

## 2.14 统计学（GEMORNA）

- 体外实验：n = 3 生物学重复，误差棒为均值标准差；
- 体内 EPO 数据：均值标准差；体内疫苗抗体数据：几何均值的几何误差；
- 统计方法：单因素方差分析（One-way ANOVA）；\*P < 0.05，\*\*P < 0.01，\*\*\*P < 0.001，\*\*\*\*P < 0.0001。

---

# 第三部分：两篇论文湿实验的关键差异对比

| 维度 | LinearDesign（Nature 2023） | GEMORNA（Science 2025） |
|---|---|---|
| 优化对象 | 仅 CDS | CDS + 5′ UTR + 3′ UTR 全长，并扩展至 circRNA |
| 核苷酸修饰 | **未修饰**（天然核苷酸） | **全程 m1Ψ 修饰** |
| IVT 加帽方式 | spike：转录后牛痘加帽酶酶法加帽 +  Antarctic Phosphatase 去 5′ 三磷酸；VZV：m7(3′OMeG)ppp(2′OMeA)pG 共转录加帽（30 °C 16 h 一锅法） | 试剂盒共转录体系（T7 Co-transcription Kit，Synthgene），37 °C 2 h（新冠 mRNA 1 h） |
| 递送系统 | LPP（脂多聚复合物） | LNP（ALC-0315/DSPC/Chol/ALC-0159 = 46.3:9.4:42.7:1.6，微流控 INano L+） |
| 体外稳定性检测 | Mg²⁺ 加速降解 + Qsep100 毛细管电泳定量完整性 + 一相衰减拟合半衰期；非变性胶看迁移率 | 用 48 h/24 h（或 144 h/24 h）报告基因活性比值间接表征胞内 mRNA 稳定性 |
| 体外表达细胞 | HEK293 | HEK293T、HepG2、Jurkat、人原代 T 细胞 |
| 表达检测 | 流式（抗 RBD 抗体染色，MFI） | Bright-Glo/Nano-Glo 发光、EPO ELISA、流式 |
| 动物模型 | C57BL/6，i.m. 10 µg×2（间隔 2 周），测 IgG/中和/ELISpot | 疫苗：i.m. 1/3 µg×2，测 anti-spike IgG；EPO：BALB/c 尾静脉 3 µg，血清 EPO 动态 |
| 功能拓展 | 无 | circRNA 合成（PIE 环化 + RNase R）、CAR-T 制备与 NALM-6 杀伤实验 |
| 峰值效果 | 抗-spike IgG 较密码子优化基准最高 +128 倍 | Fluc 体外表达较优化基准最高 +41 倍；体内 EPO mRNA +15 倍、circRNA +121 倍 |

# 第四部分：复现实验的实用要点

1. **序列获取**：LinearDesign 的全部 CDS 与 UTR 序列见其补充信息末尾及 figshare（DOI: 10.6084/m9.figshare.22193251）；GEMORNA 的构建体元件组成见其补充表 S1/S2，具体序列在 Data S1–S4。
2. **稳定性实验的关键变量**：Mg²⁺ 浓度强烈影响降解速率（10 mM vs 20 mM 是两种档位），务必用毛细管电泳（Qsep100 或同类）定量全长比例，并用一相衰减模型拟合半衰期。
3. **去核糖体修饰兼容性**：GEMORNA 强调 m1Ψ 修饰下设计仍有效；若复现 LinearDesign 结果，注意其全部使用未修饰核苷酸，两者不可混用直接对比。
4. **circRNA 纯化**：RNase R 消化去除线性前体是关键步骤，GTP 诱导环化的条件为终浓度 2 mM、55 °C 15 min。
5. **电转 T 细胞**：220 V/2 ms 方波、0.2 cm 电转杯、1 × 10⁷ cells/ml 是 GEMORNA 论文验证过的参数窗口。
6. **体内读数变异**：mRNA 疫苗的体内免疫原性数据变异天然较大（组织转染、翻译效率、个体免疫状态差异），建议每组 n ≥ 5 并用几何均值 + 非参数检验。
7. **对照设置建议**：CDS 优化效果评估时应固定 UTR（反之亦然）；推荐同时纳入密码子优化基准（GenScript/IDT 工具）、商用药物序列（BNT162b2 元件）与算法基准（LinearDesign 序列）三层对照——这也是 GEMORNA 论文的对照策略。

---

*文档说明：本整理仅涵盖两篇论文的湿实验部分（实验方法、流程与结果），算法与模型细节（Transformer/格解析架构、训练数据、超参数等）未展开；如需算法部分文档可另行整理。所有试剂货号、仪器型号、剂量与时间点均直接取自论文正文、方法部分及补充材料。*
