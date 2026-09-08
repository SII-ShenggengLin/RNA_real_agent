# 湿实验批次验证报告 — EPO × Influenza HA (PR8)，五臂 × 两蛋白 = 10 条全长构建

日期：2026-09-08 ｜ 驱动器：`experiments/wetlab_batch_epo_ha/run_wetlab_batch.py` ｜ 交付物：`outputs/wetlab_batch_EPO_HA.xlsx`

## 1. 序列验证（15 项断言全部 PASS）

### 蛋白序列（多渠道一致）
- **EPO = UniProt P01588，193 aa**：与靶点资产逐残基一致；RefSeq NM_000799.4 全 mRNA（1662 nt）中以精确翻译 ORF 定位 CDS 579 nt（天然终止码 UGA），翻译与蛋白一致。注意当前 RefSeq 版本是 **.4**（.5 不存在）。
- **HA = UniProt P03452（HEMA_I34A1，A/Puerto Rico/8/1934 H1N1），565 aa**：与靶点资产逐残基一致；GenBank **ABD77675.1**（segment 4 记录 **CY009444** 的注释 CDS）与之逐残基一致，WT CDS 1695 nt（天然 UGA）从中提取。
- **发现并修正的真实错误**：靶点资产原 `ncbi_reference: AAL09324.1` 解析为**狒狒 duffy 抗原**（错误引用），已修正为 ABD77675.1（蛋白序列本身未变，镜像 fasta 一致）。
- **565/566 疑问的根源（披露）**：PR8 HA 存在两个常用谱系——UniProt P03452/CY009444 = 565 aa（本实验采用，与既往全部实验记录连续）；RefSeq NC_002017.1 = V01088 = **Winter/Fields/Brownlee Nature 1981 经典测序谱系**（566 aa），与所用 565 aa 序列**仅差 8 个 HA1 残基**（TK146-147N，即 1-aa 缺失+替换；E155A、P199S、E203D、L207I、M268R、Y308F、T397S，按 565 编号；98.6% 氨基酸一致），不采用、已留档。565 aa = **Mount Sinai 谱系**（NIAID 对 St. Jude Webster/Hoffmann 库存的重测序），也是 UniProt 收录的规范条目、Hoffmann-Webster 八质粒反向遗传学体系和商品化 PR8 HA 试剂（Sino Biological 等，Asp18–Gln528 胞外域构建）所用的谱系。

### BNT162b2 UTR 底盘（三渠道）
- **5'UTR 51 nt**（α-珠蛋白衍生、GCCACCAUG Kozak 优化形）：= 疫苗批种质粒 **PP544446.1（FP9359）T7 启动子后 3527..3577 区间**（其后紧跟 ATG）；亦在第二批质粒 **PP544445.1（FP8191）中逐字出现**；与天然 HBA1（NM_000558.5）leader 核心一致（仅 Kozak C→G 差异，Xia & Lim 2021）。
- **3'UTR 94 nt**（AES–mtRNR1）：= **LinearDesign Nature 2023 补充材料逐字**（COVID 与 VZV 两节各出现一次、逐字相同——两节提取比对一致）。两个批种质粒均为 ORF-only 亚克隆、不含 3'UTR（已披露）；该元件为工程化嵌合体，与天然 AES/mtRNR1 存在已知改造差异（按 Xia & Lim 记载为"衍生"）。

## 2. 五臂生成（每臂断言：编码区回译 = 目标蛋白逐残基、长度 = 3N、统一单终止码）

| 臂 | EPO | HA | 说明 |
|---|---|---|---|
| WT | 579+UGA | 1695+UGA | 天然 CDS（RefSeq/CY009444），天然 UGA |
| LinearDesign λ=4 | ✓ | ✓ | 官方二进制、人类密码子表、默认 beam；自报 CAI 0.934/0.951、MFE −375.30/−866.50 |
| RNARL | ✓ | ✓ | 平台部署的 actor 服务（确定性推断），model_type "Homo sapiens mRNA" |
| GEMORNA（独立运行，零平台组件） | draw5, CAI 0.927 | draw1, CAI 0.860 | 预注册规则：5 CDS 抽样→回译过滤→最高人 CAI；UTR 池 12+10（short/medium/long）→PRED-5UTR top（medium#4，MRL 6.47）× PRED-3UTR top（medium#1，稳定性 4.57）；池明细见 xlsx 第三页 |
| 我们的平台 rank-1 | GenNav λ0.75 × GEMORNA long 5'UTR × benchmark 3'UTR，108 候选，~23 min | GenNav λ2.25 × GEMORNA long 5'UTR × benchmark 3'UTR，108 候选，46 min | CLI 表单入口、navigation 未设置（平台默认全创新链路）、RNADA_CAPGATE=advisory；会话 `wetlab_ours_EPO` / `wetlab_ours_HA`（结果冻结，审计 trail 覆盖） |

GEMORNA 臂全程只用其仓库脚本（`gemorna_service_env` 直跑 `src/generate.py`、`main_pred5UTR.py`、`main_pred3UTR.py`），未经过任何平台治理组件。

## 3. in-silico 指标（统一口径；完整表见 xlsx）

| 蛋白 | 臂 | CAI | MFE-全长 | MFE-CDS | GC%-全长 | GC%-CDS | 5'UTR MRL | 3'UTR 稳定性 |
|---|---|---|---|---|---|---|---|---|
| EPO | WT | 0.792 | −286.2 | −238.5 | 58.7 | 60.5 | 6.12 | 2.19 |
| EPO | LinearDesign | 0.938 | −428.0 | −388.7 | 63.4 | 66.3 | 6.12 | 2.19 |
| EPO | RNARL | 0.978 | −350.8 | −301.9 | 67.4 | 71.3 | 6.12 | 2.19 |
| EPO | GEMORNA | 0.927 | −342.4 | −283.6 | 67.7 | 70.6 | 6.47 | 4.57 |
| EPO | 我们 | 0.817 | **−506.6** | **−442.8** | 63.7 | 64.4 | **6.74** | 3.15 |
| HA | WT | 0.727 | −458.3 | −406.4 | 42.7 | 41.9 | 6.12 | 2.19 |
| HA | LinearDesign | 0.955 | −941.4 | −903.7 | 58.2 | 58.7 | 6.12 | 2.19 |
| HA | RNARL | 0.976 | −725.7 | −672.4 | 62.1 | 63.0 | 6.12 | 2.19 |
| HA | GEMORNA | 0.860 | −637.2 | −583.6 | 53.7 | 53.4 | 6.47 | 4.57 |
| HA | 我们 | 0.897 | **−1089.2** | **−1011.2** | 56.9 | 56.7 | **6.80** | 3.15 |

口径：CAI=Kazusa 人表（Sharp-Li）；MFE=ViennaRNA RNAfold（37 °C）；CDS 指标按编码区（不含终止码）、全长按 5'UTR+CDS(含终止码)+3'UTR（不含 poly(A)/帽）；MRL= GEMORNA PRED-5UTR、3'UTR 稳定性= GEMORNA PRED-3UTR（与其基线臂选择同一模型、十臂统一）。诊断列：十条构建 5'UTR 均无 uAUG、3'UTR 均无 II 类 ARE、散在 AUUUA 均为 0。

## 4. 备注

- 我们的两条 rank-1 均落在 GenNav 稳定化档（λ0.75 / λ2.25）并配 GEMORNA 生成 5'UTR（MRL 6.74/6.80，高于 BNT 6.12 与 GEMORNA 自选 6.47）+ 天然 HBA1 benchmark 3'UTR——这是 ASF 复合目标在两次冻结运行中的自主选择，如实呈现。
- 所有输出为未加尾未加帽的 RNA 序列（U 字母表）；湿实验统一加尾/加帽/修饰，十臂一致。
- 中间产物全留档：`refs/`（外部记录原始文件）、`outputs/`（各阶段 JSON + 日志）、平台会话 `workspace/sessions/wetlab_ours_{EPO,HA}/`（含完整审计）。
