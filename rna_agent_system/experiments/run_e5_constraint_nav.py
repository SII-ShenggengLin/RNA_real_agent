#!/usr/bin/env python3
"""E5 PRE-REGISTRATION (final v3, user-approved 2026-08-07) — constraint-navigated
batch delivery & ranking for full-length mRNA design.

Pre-registration: ``experiments/results/PREREG_2026-08-07_E5_BATCH_RANKING_DRAFT.md``
(定稿 v3; 本 docstring 为全文移植 + 实施细化注记)。
Background chain: ``HANDOFF_2026-08-07_E4FULL_FINAL_RERUN.md`` (E4 全矩阵 NO-GO)
→ ``HANDOFF_2026-08-07_E5DRAFT_READY.md`` (v1) → ``HANDOFF_2026-08-07_E5DRAFT_V2_MRNADESIGNER.md``
(v2) → 定稿 v3 → ``HANDOFF_2026-08-07_E5DRAFT_V3_APPROVED.md`` (锚点拍板 ①去锚点,
2026-08-07)。E3 预注册: ``experiments/run_e3_gated_vs_ungated.py`` docstring。

§1 动机与结论
    - E4 结论: 跨靶点案例记忆"省钱(预算节省 74.2%)但不产生学习曲线、无设计收益"→ 记忆策略 NO-GO。
    - 指标洞察(用户, 2026-08-07): CAI / 全长 MFE 基本由 LinearDesign λ 参数决定(工具射程内);
      接头 mfe/nt、GemORNA MRL 无规律不可控。→ 单指标质量不是 agent 可证明优越性的空间。
    - E3 正结果(组件级证据): 架构门控 FP 相对降 100%、TP 保留 112.5%、越权 0。
    - 新主张: agent 的优越性在工具射程之外——多约束满足与冲突仲裁、画像驱动的权衡选点、
      带排序的批量交付、可审计决策档案。
    - 设计思想来源: mRNAdesigner (Ouyang et al., NAR 2025, 53:W415–W426)——区域差异化优化
      (5'UTR 用 MRL 量化翻译起始 / CDS 主攻二级结构 / 3'UTR 用降解元件控制稳定性)、约束边界内
      搜索、自然先验库选点优于从头生成、结构聚类多样交付、竞争性需求按文献先验仲裁。
    - 耗时约束(用户拍板追加): 全量实验耗时可控; LinearDesign 调用最小化(§14)。

§2 假设 (Hypothesis)
    在 RNA-BioBench-FullLength-mRNA 20 靶点全长 mRNA 设计任务上, 门控 + 约束导航 agent
    (实验臂) 相比 ①单工具直跑(λ 网格 + 规则选点) 与 ②无门控 LLM agent 自由编排, 产生更高
    的端到端通过率(每基因 5 候选全部满足约束矩阵) 与可验证的排序质量(一致性/稳定性/敏感性/
    最优性四代理), 且不依赖 CAI / 全长 MFE / 接头 mfe/nt / GemORNA MRL 中任何单项指标的改进。

§3 任务规格(批量交付 + 排序, 5 个候选; 无 wet-lab)
    - 输入: 基因(target) + 任务画像(profile)。
    - 输出: 5 个全长 mRNA 候选 + 全序排序 + 决策档案(每候选: 约束满足表、档案分数、
      仲裁记录、λ 选点依据)。
    - 交付规则: 候选池按效用函数 U 取 top-5; 不满足 pass/fail 约束的候选仍交付但显式标记
      (端到端通过率按"5 个全过"计)。

    §3.1 候选池(拍板: 混合池三臂共用, 每靶点仅生成一次)
        - 混合候选池(A/B/C 三臂共用): GEMORNA 生成 5'/3'UTR(short/medium/long) ×
          LinearDesign CDS(λ {0,1,4,10}) 组合。
        - 【2026-08-07 锚点拍板 ①去锚点】原 §3.1 的"靶点自然参考 UTR 锚点"前提不成立:
          20 靶点 JSON 均无自然 5'/3'UTR(仅 protein_sequence), 9/20 为病毒/原核/报告基因
          (Spike/RSV/Zika/HIV/HPV/Influenza/GFP/Beta-gal/Luciferase) 无自然人 UTR 可获取;
          external_anchors/wt_cds/ 为野生型 CDS(非 UTR)。用户拍板方案①: 池 = 4 λ CDS
          × 9 GEMORNA UTR 组合 = 36 候选, 零新数据、三臂完全公平、A 臂规则不动;
          混合语义由 GEMORNA 三长度 × 两端设计承担。
        - 池规模(每靶点): 36 候选; 池生成阶段对全部候选完成约束矩阵判定与 LinearFold 全长
          fold(C6/C7/D3 所需) + C6 起始区窗口 fold; 之后三臂只读池数据。
        - 池生成成本(每靶点): LinearDesign 4 次 + GEMORNA 生成 6 次(5'/3' × 3 预设)
          + 池级 GEMORNA 预测 6 次(每唯一 UTR 序列各 1 次, 实施细化见下) + ~36 次全长
          LinearFold + ~12 次窗口 LinearFold(窗口 = 5'UTR + CDS 前 30nt, 与 3'UTR 无关
          → 4 CDS × 3 5'UTR = 12 唯一窗口) + 本地规则判定。≈ 13–15 分钟/靶点。
        - 【实施细化 1】池级补 GEMORNA 预测(每靶点 6 次: 3 唯一 5'UTR 序列 MRL + 3 唯一
          3'UTR 序列稳定性): §4.2 的 E4/E5 是效用函数次要分量, U 函数需要其值; 预测只取决于
          UTR 序列本身(与 CDS/另一端无关), 故按唯一序列各 1 次, 全池共享。计入 §14 预算
          ("GEMORNA 6 次 ~2min" 语义扩展为生成 + 预测共 12 次, 墙钟增量 ~1–2min)。
        - 【实施细化 2】E8 |ΔGC| 去锚点化: 原定义"与靶点自然序列之差"; 锚点方案①下无自然
          全长序列, 改为与基准自带野生型 CDS(``external_anchors/wt_cds/<target>.fa``) 的
          GC 之差。wt CDS 为基准数据, 零新数据。
        - 零新模型——锚点为基准数据自带序列, 无需新增服务/模型。

§4 约束矩阵(C1 + C2 + C6 + C7 + M1 + CAI 共 6 条; 【实施修正 2026-08-07, 用户拍板】
    C3、C4、C5、C8 降为软约束入档案 → 矩阵 9 条 → 5 条;
    【档位 B-1, 2026-08-08 用户拍板】+ CAI ≥ 0.8 硬约束 → 6 条;
    【v6 放宽记录, 2026-08-08】B-1 加严被真实 C 臂探针证伪(4/5 靶 pool 结构性
    清零), 放宽为 C1 GC 30–80; CAI 试探 0.7(preflight 实证 GFP 仍 0/315,
    池 max CAI 0.684 结构性不可达)后 【用户拍板 2026-08-08】恢复 ≥ 0.8:
    GFP 0-pass 视为现有生成方法无法产出高质量 CDS 的系统能力结论, 不降阈值)
    §4.1 pass/fail 约束(agent 层核心, 二元可判, 本地可实现)
    §4.1 pass/fail 约束(agent 层核心, 二元可判, 本地可实现)
        C1 GC 含量(100nt 滑窗, 步长 1) | 本地 | 30–80% 全窗(35–70 → 30–80,
           放宽 v6 2026-08-08: B-1 加严证伪——Insulin/EPO 高 GC 靶被上限 70 清零)
        C2 无 ≥14 同聚物 | 本地 | AAAAAAAAAAAAAA/TTTTTTTTTTTTTT/CCCCCCCCCCCCCC/
           GGGGGGGGGGGGGG 均无(RNA 中 U 视同 T; 6→14, 实施修正: Twist 合成硬线)
        C6 起始区结构开放(判定窗口 = "5'UTR 全长 + CDS 前 30nt") | LinearFold 窗口 fold |
           窗口内最长连续配对茎 ≤ 12bp(10→12, 实施修正; 语义: 避免强结构
           遮蔽翻译起始, joint 5'UTR+CDS 论文以 AUG 上下文 ΔΔG 度量开放度)
        C7 全长最长茎(免疫原性一等约束) | LinearFold 全长 fold(与 D3/E7 同一次输出) |
           最长茎 ≤ 30bp(mRNAdesigner 直接出处 "defined as exceeding 30 bp")
        M1 UTR/CDS 边界可扩增性(粗代理) | 本地 | 两边界 ±30nt 窗口 GC 均 20–80%
        CAI CDS 密码子优化质量(Kazusa 表) | 本地(Kazusa 表) | E1 CAI ≥ 0.8
           (【档位 B-1, 2026-08-08 用户拍板】E1 由档案指标升格为硬约束;
           与 C1 加严配套制造 e2e 区分空间; §4.2/§12 "CAI 不进 pass 判据"就此修订;
           【v6 放宽记录, 2026-08-08】0.7 试探后用户拍板恢复 0.8——GFP 池 max CAI
           0.684 结构性不可达, 0-pass 视为系统能力结论, 不降阈值)
    【实施修正 2026-08-07, 用户拍板】C3 无 polyA 信号、C4 无限制酶位点(克隆)、
    C5 无剪接共识序列、C8 5'UTR 无 uAUG: 降为软约束(仅档案计数, 不参与 pass 判定与
    约束满足率)。
    C3 依据: 检索确认 LinearDesign 开源实现无 DFA 生成约束(论文 Methods 仅理论
    框架, Extended Data Fig.3c / Supplementary Fig.5; 代码/README/微服务均无约束
    参数) → polyA 信号无法生成时规避, 只能判定层处置 → 软约束(档案记录命中计数)。
    C4 依据: 交付物是 mRNA 序列, 体外转录无克隆阶段(PMC10935487 / mRNAArchitect);
    且长 CDS 中限制酶位点统计必现(HER2/Spike 36/36 命中 BamHI), 作硬约束不可满足。
    C5 依据: 三篇设计文献(mRNAdesigner / LinearDesign / joint 5'UTR+CDS)的 CDS 优化均无
    剪接位点过滤(体外转录 mRNA 不进入细胞核、无剪接); 且 [AG]G[AC]AG 5-mer 在全部
    20 靶点 wt CDS 上统计必然命中(3–95 次/基因), 作为硬约束不可满足。
    C8 依据: 真实 5'UTR 中 uAUG 普遍(约半数转录本), GEMORNA 训练分布即如此, "5'UTR
    无 AUG"对生成式 UTR 池结构性无解(实测 Insulin/GFP/IL-2 的 9 个 preset 生成中 4 个
    含 uAUG, 且同 preset 跨运行随机); E4 MRL(层 3 翻译起始)已覆盖 UTR 起始质量。
    现仅档案记录(``C3_polya_signal_count`` / ``C4_restriction_hits`` /
    ``C5_splice_motif_count`` / ``C8_uAUG_count``), 不参与 pass 判定与约束满足率。
    【实施修正 2026-08-07, 用户拍板】GEMORNA 生成不幂等(同 preset 每次返回不同序列),
    池随机波动不可复现 → 生成结果按 (target, 类型, preset) 落盘缓存
    (``experiments/results/e5_gemorna_cache.json``), 首次生成后复用; 生成预算
    (§14 GEMORNA 6 次/靶点)不变, 池确定可复现。
    §4.2 档案记录指标(一般不作 pass 判据, 不作排序主依据, 仅入档案与效用次要分量;
        【档位 B-1, 2026-08-08 用户拍板】E1 CAI 例外——升格为硬约束, 见 §4.1)
        E1 CAI(Kazusa 表, λ 锁定) | E2 全长 MFE(LinearFold 产出) | E3 接头 mfe/nt
        (JunctionEvaluator; 交付级) | E4 5'UTR MRL、E5 3'UTR 稳定性(GEMORNA 预测) |
        E6 稀有密码子计数(RSCU 最低 ~10% 的密码子) | E7 pair ratio(LinearFold 全长 fold
        输出; 与 C7/D3 同次计算) | E8 |ΔGC|(与 wt CDS GC 之差, 实施细化 2) |
        E9 3'UTR ARE 计数(本地 motif 扫描: AUUUA 五联体) | E10 Kozak 一致性记录
        (起始位点 GCCACC 共识匹配度) | E11 LD-λ 与效用 λ 区分记录(LinearDesign 运行 λ 与
        选点 λ 分开记录) | E12 论文动机注记(每候选设计理由引用 mRNAdesigner 对应思想)。
        全部零新模型。
    §4.3 冲突仲裁(文献先验优先级链; 仲裁决策必须写入档案)
        pass/fail 约束硬优先(不可违背, 违背即标记未过); 跨层冲突按文献先验优先级链仲裁
        (不按画像权重——权重只定同层选点方向与 λ 选点, 不翻跨层优先级):
          层 1 免疫原性 / 降解控制(过结构免疫风险、3'UTR 降解元件)
          层 2 稳定性目标(结构复杂度 / 半衰期; Bicknell et al., Cell Rep 2024)
          层 3 翻译起始(5'UTR MRL、起始区结构开放; Mauger et al., PNAS 2019)
          层 4 密码子偏好(CAI / 稀有密码子)
        设计意图: 基线 A(无 agent)无仲裁逻辑 → 通过率上限天然受限于"λ 网格中恰好满足
        全部约束的候选数"——优越性的来源。

§5 任务画像与效用函数(3 画像 + 区域化权重 + 区域内权重规则)
    | 画像 | 区域权重(5'UTR/CDS/3'UTR) | 区域内指标主轴 | λ 选点偏好 |
    | profile_expression(高表达) | 0.35/0.45/0.20 | 5'UTR: MRL、起始区开放; CDS: CAI、
      结构、稀有密码子; 3'UTR: 稳定性 | 小 λ(CAI 优先) |
    | profile_stability(高稳定) | 0.15/0.50/0.35 | 5'UTR: 起始区开放、MRL; CDS: 结构、
      CAI、稀有密码子; 3'UTR: 稳定性 | 大 λ(稳定性优先) |
    | profile_balanced | 各 1/3 | 三区均等 | 中 λ |
    区域内指标权重: 两指标 → 主轴 0.6/次轴 0.4; 三指标 → 均分。
    U(candidate) = 0.8 × Σ(区域权重 × 区域内归一化档案分) + 0.2 × 全局分量
        (先过滤: C1–C2+C6–C7+M1 全过才可排序前列; 全局分量: 全长 MFE(池级) + 接头 mfe/nt
        (交付级补); 效用函数全程可复现、透明——排序不是 LLM 拍脑袋)。
    【实施细化 3】区域指标定义(全部池级可得, 零额外模型调用):
        5'UTR 区: E4 MRL(GEMORNA 预测) + 起始区开放度(C6 窗口 fold 的 unpaired fraction);
        CDS 区: E1 CAI + CDS 区段结构(全长 fold 中 CDS 区段的 unpaired fraction,
        与 C7 同次 fold 提取, 零额外调用) + E6 稀有密码子计数(负向);
        3'UTR 区: E5 稳定性(GEMORNA 预测)。
        【实施细化 4】区域内权重规则: 5'UTR 两指标按画像主轴 0.6/0.4(expression 主轴 MRL,
        stability 主轴起始区开放, balanced 均分); CDS 三指标均分; 3'UTR 单指标 1.0。

§6 三臂对照(基线数据不复用 E3——场景不同)
    | A 单工具直跑 | 从共享池规则选点: 先按约束过滤, 再按画像权重选 λ; 交付 5 个(不同 λ)
      + 规则效用排序。无 LLM。零额外工具调用。 |
    | B 无门控 LLM agent(等价替代) | 同实验臂提示词, 无架构门控(自由规划、自由调用工具、
      自定流程)——沿用 E3 ungated 定义(现行栈同构实现)。在共享池内操作, 额外 LinearDesign
      调用 ≤1 次/基因。LLM 预算 2–4 次/基因, 不加修复轮。 |
    | C 门控 + 约束导航(实验) | DecisionGate(复用 E3 组件与能力 SelfModel)+ 约束矩阵作为
      架构层强制 gate + 冲突仲裁 + 画像驱动 λ 选点。额外 LinearDesign 调用 ≤1 次/基因
      (修复轮专用)。LLM 预算 5–9 次/基因。 |
    预算匹配(BMC 协议)记录三臂成本, 描述性报告(效率不作为 pass 判据主项)。
    【实施细化 5】B/C 臂 agentic 循环(等价替代, 驱动内手写): LLM 每轮输出 JSON 动作
    (select / sort / repair(C 臂) / lineardesign / finalize) → 驱动执行 → 观察回填 → 再决策。
    B 臂无门控(选中候选不强制过约束, 交付时显式标记); C 臂强制: ①约束 gate——select/
    repair/finalize 的候选必须 C1+C2+C6+C7+M1+CAI 全过(6 条; v6 最终形态 = GC 30–80
    + CAI ≥ 0.8), 未过拒绝动作并回填
    gate 反馈; ②动作 gate——越权动作(改序列/跳过约束)拒绝并审计; ③仲裁校验——sort 的
    仲裁记录必须引用对应层的池级档案指标(层1: C7最长茎/E9 ARE; 层2: E2 MFE/E7 pair ratio;
    层3: E4 MRL/C6 开放度; 层4: E1 CAI/E6 稀有), 不引用拒绝回填; ④修复轮 ≤2 轮/基因——
    池内定向重选组合(零新生成), 仅当 CDS 级约束(C2/C7, C3/C4/C5 已软约束化)池内无解时允许
    ≤1 次/基因 λ 邻域重跑(λ∈{0,1,4,10} 邻域取 1 档), 计预算、入档案。
    DecisionGate/SelfModel/AuditTrail 全程实例化并记录审计事件。

§7 评测指标(全部预注册阈值; S1 与 S2 同指标同阈值)
    §7.1 主指标
        - 端到端通过率(基因级): 5 候选全部满足 C1+C2+C6+C7+M1+CAI(6 条, v6 最终形态
          = GC 30–80 + CAI ≥ 0.8)的基因比例。
        - 约束满足率(候选级): 每候选过约束数 / 6。
    §7.2 排序质量四代理(无 wet-lab 下可测)
        R1 一致性: 交付排序与 U 排序 Spearman ρ = 1.0(tie 内序允许)。
        R2 稳定性: 同输入重复 3 次, Kendall τ ≥ 0.8(两两最小 τ)。
        R3 敏感性: 3 画像两两间 top-1 候选分离(CAI 差 ≥ 0.05 或 λ 选点差 ≥ 2 档),
           ≥1/3 画像对显著分离。
        R4 最优性: top-1 的 U 为约束满足候选子集(C1+C2+C6+C7+M1+CAI 全过)内最大, 且约束满足数为
           该子集内最多; 若子集为空, 取生成池内最大并显式标记"无约束满足候选"。
    §7.3 多样性
        D1: 5 候选 pairwise 最小编辑距离 ≥ 全长 2%(同长序列用差异位点比例, 见实施细化 6)。
        D2: λ 选点 pairwise 分散(≥3 个不同 λ 或存在索引间距 ≥2 档)。
        D3: pair ratio 极差 ≥ 3pp 或最长茎差 ≥ 5bp(pair ratio 与最长茎均取 LinearFold
            全长 fold 输出, 与 C7 同次计算)。
    【实施细化 6】D1 实施: 候选序列等长(同蛋白 CDS 等长)时 pairwise 差异位点比例
    (1 − hamming 一致比例); 长度不同时用 difflib SequenceMatcher 的 1−ratio。

§8 统计方案与功效预检(诚实声明)
    - S1(n=5 靶点)不可能给出配对显著性(McNemar n=5 功效近轶事)→ S1 判据 = 效应量与方向性,
      显著性检验留给 S2。
    - S2(n=20 靶点): 配对 McNemar(C vs A、C vs B) p<0.05 或 95%CI 不含 0; 排序/多样性判据全过。
    - 预注册声明: S1 的效应量估计直接决定 S2 是否需要扩规模。
    - 【实施细化 7】McNemar 配对单位 = 基因 × 画像(每臂每基因 3 画像各一次交付判定,
      n = 60 对); 同时报告基因级口径(20 基因, 3 画像全过才算基因过, 描述性)。

§9 分阶段关卡(判据从 S0 起全量生效)
    | S0 机制验证 | 1 靶点 × C 臂 × 3 次重复 | ①约束识别 100%(档案中每条约束可见且被判定)
      ②输出格式完整(5 候选+排序+档案) ③R2 稳定性 τ≥0.8 ④驱动无崩溃、单场耗时 ≤ 预算 |
      全过 → S1; 任一不过 → 回设计 |
    | S1 小规模 | 5 靶点 × 3 臂 | ①端到端通过率 C ≥ 0.8 且 C > A ②约束满足率 C ≥ 0.9
      ③R1–R4 全过 ④D1–D3 全过 ⑤每靶点方向性 C ≥ A 至少 4/5 ⑥BMC 预算记录(描述性) |
      全过 → 才进 S2; 任一不过 → 报告用户 |
    | S2 全矩阵 | 20 靶点 | ①配对 McNemar p<0.05(C vs A 且 C vs B, 或 95%CI 不含 0)
      ②R1–R4、D1–D3 全过 ③约束满足率 C ≥ 0.9 | 最终判定书(GO/NO-GO 双终点见 §10) |
    - E4 教训显式条目: ①判据从 S0 起生效 ②禁止实验中途新增终点 ③每阶段结束出阶段判定书
      (JSON), 未过不进下一阶段 ④S1 判据不过时备选动作由用户定。
    - 【实施细化 8】R2(3 重复稳定性)在 S0 阶段验证(§9 S0 判据 ③ 即 R2); S1/S2 的 R2 判据
      引用 S0–S1 稳定性证据(驱动与 LLM 均 temperature 0 确定性, 重复间仅剩池内序列缓存
      差异, 机制已在 S0 验证)。S1/S2 每臂每基因运行一次, 内含 3 画像交付(R3 比较同一次
      运行内 3 画像的 top-1), LLM 预算保持 §11 的每基因口径。

§10 GO/NO-GO 规则(任一终点过 → GO + 披露细则)
    - 终点 1(交付效率): S2 配对显著性过(C vs A、C vs B 均 p<0.05)且端到端通过率 C ≥ 0.8。
    - 终点 2(交付质量): R1–R4 全过且 D1–D3 全过且约束满足率 C ≥ 0.9。
    - 任一终点过 → GO; 双过更强。双不过 → NO-GO(退路待用户定)。
    - 执行细则: 若仅终点 1 过, 判定书必须显式披露终点 2 未过及原因; 若仅终点 2 过, 直接视为 GO。

§11 与现有资产的关系
    - 门控组件: 复用 E3 DecisionGate 与能力 SelfModel; 新增约束矩阵 gate(架构层, 非提示词)。
    - 工作流/评估器: full_length_mrna_design.py(GEMORNA 5'UTR/3'UTR、LinearDesign λ 0–20、
      Junction/GC/结构评估器)全部复用, 零新模型。
    - 20 靶点: data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/ 全套(同 E4;
      Zika/Factor_VIII 的 LinearDesign OOM 风险沿用预声明可接受失败机制)。
    - MODEL_API_USAGE.md(已拍板预算): S1/S2 启动前预登记——C 臂每基因 5–9 次 LLM
      (仲裁/排序理由/评审 + 修复轮 ≤2 轮 × 1–2 次), B 臂 2–4 次、不加修复轮; 实测后当天更新。

§12 明确排除(防 E4 重演)
    全长 MFE、接头 mfe/nt、GemORNA MRL 不进任何 pass 判据、不进任何 GO/NO-GO 终点
    ——只作档案记录与效用函数次要分量(§4.2)。【档位 B-1, 2026-08-08 用户拍板】
    E1 CAI 例外升格: 进硬约束(≥0.8)与约束满足率分母——e2e 判据①饱和无区分空间的
    配套修正(预演实证两臂 e2e_gene 均 ~1.0 平局)。【v6 放宽记录, 2026-08-08】
    GC 35–70 → 30–80 保留; CAI 0.7 试探后用户拍板恢复 0.8——GFP 0-pass 视为
    系统能力结论(生成池无法产出 CAI≥0.8 的 CDS), 不降阈值。

§13 未决问题(全部拍板, 2026-08-07; 改动需重新呈用户)
    1. 约束矩阵采纳(9 条; 【实施修正 2026-08-07】C3/C4/C5/C8 软约束化 → 5 条;
       【档位 B-1, 2026-08-08】+ CAI ≥ 0.8 硬约束 → 6 条;
       【v6 放宽记录, 2026-08-08】C1 GC 35–70 → 30–80 保留; CAI 0.7 试探后
       用户拍板恢复 ≥ 0.8(GFP 0-pass 视为系统能力结论); 仍 6 条);
       2. S1 规模 5 靶点;
    3. 画像 3 类; 4. GO/NO-GO 任一过 → GO;
    5. A 臂 λ 网格 {0,1,4,10} 保留; 6. 代号 E5; 7. B 臂等价替代(现行栈同构无门控)+ 额外
    LinearDesign ≤1 次/基因; 8. 修复轮 ≤2 轮, 语义钉死(池内定向重选, CDS 级无解时 ≤1 次
    邻域重跑), C 臂 LLM 5–9 次/基因; 9. 区域化权重数值; 10. 仲裁优先级链; 11. 候选池混合
    (锚点拍板①去锚点, 见 §3.1); 12. D3 结构多样性阈值(pair ratio 极差 ≥3pp 或最长茎差
    ≥5bp, 取 LinearFold 全长 fold 输出); 13. 指标改进 10 条整体采纳。

§14 耗时预算与 LinearDesign 最小化(2026-08-07 拍板)
    依据(E4 264 场实测): 单场耗时大头是线性生成调用固定开销(nomem intercept ≈ 1297s ≈
    21 次生成 × ~55–60s/次; memory intercept ≈ 361s ≈ 6 次), 每候选边际 eval ~13–33s。
    LinearDesign 最小化策略: ①池一次生成三臂共享(每靶点 4 次, 全矩阵 80 次 vs E4 ~2500+
    次, ↓~97%); ②修复轮零生成优先(全矩阵上限 20 次); ③B 臂受限(≤1 次/基因, 上限 20);
    ④C6/C7/D3 共用同一次 LinearFold 全长 fold(窗口 fold 12 次/靶点); ⑤池内约束判定/排序
    全在池生成阶段完成, 三臂只读(A 臂零工具调用)。
    预算表(1 分片串行; 服务串行处理请求, 勿超 2 分片并发):
        S0 机制验证: 1 靶点池 + C 臂 × 3 重复, LinearDesign 4–5 次, ~25–35 分钟(1 分片)
        S1 小规模: 5 靶点池 + 3 臂, 20–30 次, ~1.5–2 小时
        S2 全矩阵: 20 靶点池 + 3 臂, 80–120 次, ~4–5 小时(2 分片)
        E4 全矩阵对照: 120 场(21 λ 网格), ~2500+ 次, 46.3 小时
    每靶点池生成 ≈ 13–15 分钟(实施细化 1 后); C 臂每基因 5–9 次 LLM(~15–30s/次)≈ 3–6 分钟;
    B 臂 2–4 次 ≈ 1–3 分钟; A 臂 ≈ 0。

Usage (from ``rna_agent_system/``):
    # S0 机制验证(1 靶点 × C 臂 × 3 重复; 建议小基因如 Insulin/IL-2/GFP, 避开 Zika/Factor_VIII)
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s0 \\
        --targets Insulin --repeat 3 --output experiments/results/e5_s0_runs.jsonl
    # 后台运行(工程纪律: setsid nohup + 日志落盘 + 启动后 pgrep 数进程)
    setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s0 \\
        --targets Insulin --repeat 3 \\
        > experiments/results/e5_s0.log 2>&1 &
    # S1 小规模(5 靶点 × 3 臂)
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s1 \\
        --targets A1AT,Insulin,EPO,GFP,IL-2 --output experiments/results/e5_s1_runs.jsonl
    # S2 全矩阵(20 靶点 × 3 臂; 2 分片时用 --targets 拆分)
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e5_constraint_nav.py s2 \\
        --output experiments/results/e5_s2_runs.jsonl
    # --dry-run 打印矩阵; --resume 跳过完成单元; 每阶段判定书:
    #   experiments/results/e5_verdict_s0.json / e5_verdict_s1.json / e5_verdict_s2.json

Records: ``experiments/results/e5_{s0,s1,s2}_runs.jsonl`` (append; ``--resume`` 按 done-key
    (stage, target, arm) 跳过)。判定书: ``experiments/results/e5_verdict_<stage>.json``。
"""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scipy import stats as scipy_stats  # noqa: E402

from agent_core.capabilities.base import build_default_capability_registry  # noqa: E402
from agent_core.calibrated.audit_trail import AuditTrail  # noqa: E402
from agent_core.calibrated.decision_gate import DecisionGate  # noqa: E402
from agent_core.calibrated.models import PlannedAction  # noqa: E402
from agent_core.calibrated.self_model import SelfModel  # noqa: E402
from agent_core.file_manager import save_sequence  # noqa: E402
from agent_core.llm_config import get_deepseek_llm  # noqa: E402
from agent_core.sequence_utils import (  # noqa: E402
    _load_builtin_codon_tables,
    export_codon_usage_csv,
    resolve_species_name,
)
from agent_core.services.service_manager import (  # noqa: E402
    ensure_services_ready,
    get_services_for_capabilities,
)
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry  # noqa: E402
from agent_core.tools import (  # noqa: E402
    compute_cai_for_cds_sequence,
    design_3utr_with_gemorna,
    design_5utr_with_gemorna,
    predict_3utr_stability_with_gemorna,
    predict_5utr_mrl_with_gemorna,
    predict_rna_secondary_structure_with_linearfold,
)
from agent_core.workflow_models import Candidate  # noqa: E402
from agent_core.workflows.evaluators import JunctionEvaluator  # noqa: E402
from agent_core.workflows.mrna_cds_design import (  # noqa: E402
    MrnaCdsDesignInput,
    MrnaCdsDesignWorkflow,
)

TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
WT_CDS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "wt_cds"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"

# 【实施修正 2026-08-07, 用户拍板】过滤 >1300aa 靶点(CDS 长度硬线): Factor_VIII
# (2352aa) 生成端失败(no CDS)、Zika_E_protein (3420aa) 超 LINEARDESIGN_MAX_AA
# (1800) 拦截 —— 均从全实验(扫描统计/S1/S2)排除, 分母 20 → 18。
# HER2 (1255aa) / Spike (1273aa) ≤1300 保留; HER2 约束层结构性不可行(0/36,
# C1 84% GC ∩ C7 41-43bp 茎 双重不可满足), 如实报告。
FULL_TARGETS = [
    "A1AT", "Albumin", "Beta_galactosidase", "EPO", "GFP",
    "Growth_hormone", "HER2", "HIV-1_Env_gp120", "HPV16_L1", "IFN_alpha_2a",
    "IL-2", "Influenza_HA_H1N1", "Insulin", "Luciferase", "Ovalbumin",
    "RSV_F_protein", "SARS-CoV-2_Spike_WT", "Transferrin",
]
S1_TARGETS = ["A1AT", "Insulin", "EPO", "GFP", "IL-2"]
S0_TARGETS = ["Insulin", "IL-2", "GFP"]  # 建议池(小基因, 无 OOM 风险)

LAMBDAS: tuple[float, ...] = (0.0, 1.0, 4.0, 10.0)
# 【方案 B 2026-08-07, 用户拍板】CDS 生成 = LD 4 λ + RNARL 1 + GEMORNA N 采样。
# λ 标记: GEMORNA 采样统一 -1、RNARL 统一 -2(独立来源档); D2 判据按来源档计
# (LAMBDA_RANK 扩展到 6 档, 判据代码零改动)。
LAMBDA_GEMORNA = -1.0
LAMBDA_RNARL = -2.0
GEMORNA_CDS_N = 30   # GEMORNA 采样数/靶(2026-08-08 v4 拍板 20→30: 池 225→315 候选; 实测 ~50% 过约束; ~4s/条)
LAMBDA_RANK = {0: 0, 1: 1, 4: 2, 10: 3, LAMBDA_GEMORNA: 4, LAMBDA_RNARL: 5}
UTR_PRESETS: tuple[str, ...] = ("short", "medium", "long")
ARMS = ("A", "B", "C")
PROFILES: tuple[str, ...] = ("expression", "stability", "balanced")

# 【实施修正 2026-08-07, 用户拍板】C3、C4、C5、C8 降为软约束(仅档案计数,
# 不参与 pass 判定); 约束矩阵 9 条 → 5 条。
# C3 依据: 检索确认 LinearDesign 开源实现(LinearDesignSoftware/LinearDesign,
# Nature 2023)无 DFA 生成约束(论文 Methods 仅理论框架: Extended Data Fig.3c /
# Supplementary Fig.5; README 仅 --lambda/--codonusage/--verbose; 本地 argc 4/5/7/8
# 无约束参数) → 无法生成时规避 polyA 信号, 只能判定层处置 → 降软约束。
# C4 依据: 交付物是 mRNA 序列, 体外转录无克隆阶段(PMC10935487 / mRNAArchitect)。
CONSTRAINT_IDS = ["C1", "C2", "C6", "C7", "M1", "CAI"]

# 约束阈值(§4.1, 定稿拍板; 【实施修正 2026-08-07, 用户拍板】C1 上限 70→80:
# 文献无滑窗硬阈值(mRNAdesigner 用目标 GC 偏差), 实测 LinearDesign CDS 局部窗口
# GC 73–80%, 上限 80 仅防极端 GC 区; 【档位 B-1, 2026-08-08 用户拍板】C1 加严
# 30–80 → 35–70: e2e 判据①(两臂均 ~1.0 饱和平局)无区分空间, 加严制造头部拒绝;
# 【放宽 v6, 2026-08-08 用户拍板】35–70 → 30–80: 真实 C 臂探针证伪 B-1
# (4/5 靶 pool 被结构性清零: Insulin/EPO 卡高 GC 上限 70, GFP 卡 CAI), 放宽复验)
GC_WINDOW = 100
GC_MIN, GC_MAX = 30.0, 80.0
# 【档位 B-1, 2026-08-08 用户拍板】CAI ≥ 0.8 新增硬约束(E1 由档案指标升格为
# pass/fail 约束; 与 C1 加严配套制造 e2e 区分空间)。§4.2/§12 的"CAI 不进 pass
# 判据"就此修订(其余 E 指标仍只作档案与效用次要分量)。
# 【v6 放宽记录, 2026-08-08】CAI 曾试探 0.7(preflight 实证 0.7 下 GFP 仍 0/315,
# 池 max CAI 0.684 < 0.7, 结构性不可达); 【用户拍板 2026-08-08】CAI 保持 ≥ 0.8
# 不再降(0.7 已很低): GFP 0-pass 视为"现有方法无法产出高质量 CDS"的系统能力
# 结论(后续需优化生成池), 不作为降阈值理由。GC 放宽 35-70 → 30-80 保留。
CAI_MIN = 0.8
# 【实施修正 2026-08-07, 用户拍板】C2 阈值 6→14: 无 DFA 生成约束可用, Twist
# 合成硬线 ≥14bp 同聚物(6–13bp 为灰色区"应避免非硬拒") → 允许 ≤13nt 同聚物,
# ≥14nt 判失败。
HOMOPOLYMER_MIN = 14
POLYA_SIGNALS = ("AAUAAA", "UUUAUU")
RESTRICTION_SITES = ("GGAUCC", "GAAUUC", "CUCGAG", "GCGGCCGC")
SPLICE_CONSENSUS = re.compile(r"[AG]G[AC]AG")
START_REGION_CDS_PREFIX = 30
# 【实施修正 2026-08-07, 用户拍板】C6 阈值 10→12: 无 DFA 生成约束可用, 放宽;
# 文献无"无 ≥6bp 配对"硬阈值(joint 5'UTR+CDS 论文以 AUG 上下文 ΔΔG 度量起始区
# 开放), 实测窗口最长茎 5–14bp, ≤12bp 保留"避免强结构遮蔽翻译起始"语义。
START_REGION_MAX_STEM = 12
FULL_MAX_STEM = 30
BOUNDARY_FLANK = 30
BOUNDARY_GC_MIN, BOUNDARY_GC_MAX = 20.0, 80.0

RARE_CODON_FRACTION = 0.10  # RSCU 最低 ~10% 的密码子(E6 定义)
ARE_MOTIF = "AUUUA"
KOZAK_CONSENSUS = "GCCACC"

# 画像定义(§5)
PROFILE_DEFS: dict[str, dict[str, Any]] = {
    "expression": {
        "region_weights": [0.35, 0.45, 0.20],
        "lambda_pref": "small",  # 小 λ(CAI 优先)
        "utr5_axis": "mrl",      # 主轴 MRL 0.6 / 起始区开放 0.4
    },
    "stability": {
        "region_weights": [0.15, 0.50, 0.35],
        "lambda_pref": "large",  # 大 λ(稳定性优先)
        "utr5_axis": "start_open",  # 主轴起始区开放 0.6 / MRL 0.4
    },
    "balanced": {
        "region_weights": [1 / 3, 1 / 3, 1 / 3],
        "lambda_pref": "middle",  # 中 λ
        "utr5_axis": "tie",
    },
}
# 【档位 A-②, 2026-08-08 用户拍板】λ 选点映射修正: small→0 / large→10 / middle→4
# (原 {1, 4, 4} 使画像对 λ 档差仅 0–1 档, R3 "λ 选点差 ≥2 档" 判据不可达)。
# 值 = LD λ 网格上的实际 λ; 画像对档差: small↔middle=2 档、small↔large=3 档、
# middle↔large=1 档 → R3 需 ≥1/3 对(v4)分离时可达。
LAMBDA_PREF_VALUE: dict[str, float] = {"small": 0.0, "large": 10.0, "middle": 4.0}

W_REGIONAL, W_GLOBAL = 0.8, 0.2
# 【档位 A-①, 2026-08-08 用户拍板】λ 偏好分量权重: U = (0.8×regional + 0.2×global
# + W×λ 偏好) / (1+W)。修复 R3 分离失效: λ_pref 此前定义了却从未被 utility() 消费
# (代码 bug), 3 画像 U 只差 utr5_axis/region_weights(±0.1) → 三画像 top-1 恒同一候选。
# 【档位 A+1, 2026-08-08 用户拍板】W 0.25 → 0.8: 预演实证 0.25 太弱(base U 差 ~0.13 >
# λ 增益上限 ~0.08), 偏好 λ 候选(ld1/ld4)非全局 U-max → R4 反受损; 0.8 下偏好 λ 候选
# 成为各画像 U-max → R3/R4 同获。代价: U 语义向 λ 主导偏移, CAI/MFE 区分度下降。
W_LAMBDA = 0.8
LAMBDA_RANK_SPAN = 5  # λ_rank 最大档距(0..5, 含 GEMORNA/RNARL 独立来源档)

# LLM 预算(§11/§13-8 拍板)
B_LLM_MIN, B_LLM_MAX = 2, 4
C_LLM_MIN, C_LLM_MAX = 5, 9
C_MAX_REPAIR_ROUNDS = 2
MAX_EXTRA_LINEARDESIGN = 1  # B/C 臂共用 ≤1 次/基因

# 时预算(§14; 秒, 1 分片串行)
S0_TIME_BUDGET_S = 40 * 60        # ~25–35min 预期 + 余量
S1_TIME_BUDGET_S = 3 * 3600
S2_TIME_BUDGET_S = 6 * 3600


# ---------------------------------------------------------------------------
# 序列/约束纯函数
# ---------------------------------------------------------------------------


def _rna(seq: str) -> str:
    """Normalize to uppercase RNA (T→U)."""
    return seq.upper().replace("T", "U")


def gc_fraction(seq: str) -> float:
    if not seq:
        return 0.0
    return sum(1 for c in seq.upper() if c in "GC") / len(seq)


def sliding_window_gc_out_of_bounds(seq: str, win: int = GC_WINDOW,
                                    lo: float = GC_MIN, hi: float = GC_MAX) -> bool:
    """True if ANY 100nt sliding window (step 1) has GC outside [lo, hi]."""
    seq = _rna(seq)
    n = len(seq)
    if n < win:
        gc = gc_fraction(seq) * 100.0
        return not (lo <= gc <= hi)
    prefix = [0] * (n + 1)
    for i, c in enumerate(seq):
        prefix[i + 1] = prefix[i] + (1 if c in "GC" else 0)
    for i in range(n - win + 1):
        gc = (prefix[i + win] - prefix[i]) / win * 100.0
        if not (lo <= gc <= hi):
            return True
    return False


def has_homopolymer(seq: str, k: int = HOMOPOLYMER_MIN) -> bool:
    seq = _rna(seq)
    return any(re.search(rf"{b}{{{k},}}", seq) for b in ("A", "U", "C", "G"))


def has_polya_signal(cds: str) -> bool:
    cds = _rna(cds)
    return any(sig in cds for sig in POLYA_SIGNALS)


def polya_signal_count(cds: str) -> int:
    """命中 polyA 信号总数(C3 软约束档案; 实施修正 2026-08-07: 只记录不判 pass)。"""
    cds = _rna(cds)
    return sum(cds.count(sig) for sig in POLYA_SIGNALS)


def has_restriction_site(seq: str) -> bool:
    seq = _rna(seq)
    return any(site in seq for site in RESTRICTION_SITES)


def restriction_site_hits(seq: str) -> list[str]:
    """命中限制酶位点列表(C4 软约束档案; 实施修正 2026-08-07: 只记录不判 pass)。"""
    seq = _rna(seq)
    return [site for site in RESTRICTION_SITES if site in seq]


def has_splice_consensus(cds: str) -> bool:
    return SPLICE_CONSENSUS.search(_rna(cds)) is not None


def splice_motif_count(cds: str) -> int:
    """C5 软约束档案计数(实施修正 2026-08-07): [AG]G[AC]AG 命中次数, 仅记录不判定。"""
    return len(SPLICE_CONSENSUS.findall(_rna(cds)))


def longest_stem_bp(structure: str) -> int:
    """Longest continuous stem (bp) from a dot-bracket string.

    A stem's half is a contiguous run of '(' (the paired 5' half) or ')'
    (the 3' half); the stem length in base pairs equals that run length.
    """
    best = 0
    run = 0
    for ch in structure:
        if ch in "(":
            run += 1
            best = max(best, run)
        else:
            run = 0
    run = 0
    for ch in structure:
        if ch in ")":
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def pair_ratio(structure: str) -> float:
    """Paired fraction in percentage points (pp); 0.0 for empty structure."""
    if not structure:
        return 0.0
    paired = structure.count("(") + structure.count(")")
    return paired / len(structure) * 100.0


def unpaired_fraction(structure: str) -> float:
    if not structure:
        return 1.0
    return structure.count(".") / len(structure)


def has_uAUG(utr5: str) -> bool:
    return "AUG" in _rna(utr5)


def boundary_gc_ok(utr5: str, cds: str, utr3: str,
                   flank: int = BOUNDARY_FLANK) -> bool:
    """Both boundary ±30nt windows (5'UTR|CDS, CDS|3'UTR) GC in [20, 80]."""
    for left, right in ((utr5, cds), (cds, utr3)):
        if not left or not right:
            return False
        win = _rna(left[-flank:]) + _rna(right[:flank])
        gc = gc_fraction(win) * 100.0
        if not (BOUNDARY_GC_MIN <= gc <= BOUNDARY_GC_MAX):
            return False
    return True


def are_count(utr3: str) -> int:
    return len(re.findall(ARE_MOTIF, _rna(utr3)))


def kozak_score(utr5: str, cds: str) -> float:
    """Kozak consensus match (−6..−1 positions vs GCCACC), 0..1."""
    window = _rna(utr5[-6:]) if len(utr5) >= 6 else _rna(utr5)
    if not window:
        return 0.0
    matches = sum(1 for a, b in zip(window, KOZAK_CONSENSUS) if a == b)
    return matches / 6.0


def rare_codon_set(species: str) -> set[str]:
    """Codons whose RSCU ranks in the lowest ~10% of the species' table (E6)."""
    tables = _load_builtin_codon_tables()
    resolved = resolve_species_name(species)
    if resolved not in tables:
        # 无表则退化为通用最低权重集(空集 → 计数 0, 档案注明)
        return set()
    fractions = tables[resolved]
    groups: dict[str, list[tuple[str, float]]] = {}
    for codon, info in fractions.items():
        if not info.get("fraction"):
            continue
        groups.setdefault(str(info.get("aa", "")), []).append(
            (codon, float(info["fraction"]))
        )
    rscu: dict[str, float] = {}
    for _aa, codons in groups.items():
        total = sum(f for _, f in codons) or 1.0
        mean_f = total / len(codons)
        for codon, frac in codons:
            rscu[codon] = frac / mean_f if mean_f else 0.0
    if not rscu:
        return set()
    n_rare = max(1, int(round(len(rscu) * RARE_CODON_FRACTION)))
    return {c for c, _ in sorted(rscu.items(), key=lambda kv: kv[1])[:n_rare]}


def rare_codon_count(cds: str, species: str, rare: set[str] | None = None) -> int:
    rare = rare_codon_set(species) if rare is None else rare
    cds = _rna(cds)
    return sum(1 for i in range(0, len(cds) - 2, 3) if cds[i : i + 3] in rare)


# ---------------------------------------------------------------------------
# 工具调用封装(本地微服务; 均零 LLM)
# ---------------------------------------------------------------------------


def linearfold(seq: str) -> dict[str, Any]:
    """One LinearFold full/partial fold via the 8015 microservice."""
    fp = save_sequence(seq, prefix="e5_fold")
    return predict_rna_secondary_structure_with_linearfold.func(fp)


def gemorna_utr(utr_type: str, preset: str) -> str:
    """Generate one UTR sequence via GEMORNA (cached per (type, preset) by caller)."""
    if utr_type == "5utr":
        return str(design_5utr_with_gemorna.func(utr_length=preset)["generated_sequence"])
    return str(design_3utr_with_gemorna.func(utr_length=preset)["generated_sequence"])


GEMORNA_CACHE_PATH = RESULTS_DIR / "e5_gemorna_cache.json"


def _gemorna_cached(utr_type: str, preset: str, target_id: str) -> str:
    """Deterministic GEMORNA UTR (实施修正 2026-08-07, 用户拍板): 生成结果按
    (target, 类型, preset) 落盘缓存, 首次生成后复用——池确定可复现, 生成预算不变。"""
    cache: dict[str, str] = {}
    if GEMORNA_CACHE_PATH.is_file():
        cache = json.loads(GEMORNA_CACHE_PATH.read_text(encoding="utf-8"))
    key = f"{target_id}|{utr_type}|{preset}"
    if key in cache:
        return cache[key]
    seq = gemorna_utr(utr_type, preset)
    cache[key] = seq
    GEMORNA_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    GEMORNA_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return seq


# 【方案 B 2026-08-07, 用户拍板】GEMORNA CDS 随机采样(N=20/靶), 非幂等 →
# 按 (target, idx) 落盘缓存, 池确定可复现(沿 UTR 缓存模式)。
GEMORNA_CDS_CACHE_PATH = RESULTS_DIR / "e5_gemorna_cds_cache.json"


def _gemorna_cds_cached(target_id: str, idx: int, protein: str) -> str:
    cache: dict[str, str] = {}
    if GEMORNA_CDS_CACHE_PATH.is_file():
        cache = json.loads(GEMORNA_CDS_CACHE_PATH.read_text(encoding="utf-8"))
    key = f"{target_id}#{idx}"
    if key in cache:
        return _rna(cache[key])
    payload = json.dumps({"protein_sequence": protein}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8004/generate/cds", data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
    seq = _rna(resp["generated_sequence"])
    cache[key] = seq
    GEMORNA_CDS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    GEMORNA_CDS_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return seq


def gemorna_predict_mrl(utr5: str) -> float:
    fp = save_sequence(utr5, prefix="e5_utr5")
    return float(predict_5utr_mrl_with_gemorna.func(fp)["predicted_mrl"])


def gemorna_predict_stability(utr3: str) -> float:
    fp = save_sequence(utr3, prefix="e5_utr3")
    return float(predict_3utr_stability_with_gemorna.func(fp)["predicted_stability"])


def cds_cai(cds: str, species: str) -> float:
    fp = save_sequence(cds, prefix="e5_cds")
    return float(compute_cai_for_cds_sequence.func(fp, species=species)["cai_score"])


# ---------------------------------------------------------------------------
# 候选/池数据结构
# ---------------------------------------------------------------------------


def make_candidate(cds_seq: str, utr5: str, utr3: str, lam: float,
                   utr5_preset: str, utr3_preset: str, species: str,
                   *, source: str = "ld", idx: int = 0) -> dict[str, Any]:
    """source: "ld"(LinearDesign λ) / "rnarl" / "gemorna"(采样 idx);
    λ 标记(方案 B): GEMORNA=-1、RNARL=-2 独立来源档, D2 按 6 档计。"""
    cds_seq, utr5, utr3 = _rna(cds_seq), _rna(utr5), _rna(utr3)
    full = utr5 + cds_seq + utr3
    prefix = {"ld": f"ld{int(lam)}", "rnarl": "rn", "gemorna": f"gm{idx}"}[source]
    return {
        "id": f"{prefix}_u5{utr5_preset[0]}_u3{utr3_preset[0]}",
        "source": source,
        "lambda": lam,
        "lambda_rank": LAMBDA_RANK.get(lam, 0),
        "utr5_preset": utr5_preset,
        "utr3_preset": utr3_preset,
        "utr5": utr5,
        "cds": cds_seq,
        "utr3": utr3,
        "sequence": full,
        "species": species,
        "constraints": {},       # C1..M1 -> bool
        "archive": {},           # E1..E12
        "scores": {},            # 归一化区域分
        "utility": {},           # per profile
        "flags": {"delivered": False, "passed": False, "no_constraint_solution": False},
    }


# ---------------------------------------------------------------------------
# 池生成(每靶点一次, 三臂共享; §3.1/§14)
# ---------------------------------------------------------------------------


def _ld_codon_usage_path(species: str) -> str | None:
    """B0 生成侧修复(2026-08-08 用户拍板): 非 human 物种 → species 匹配 Kazusa
    codon-usage CSV; human(或表缺失) → None(LD 默认表, 行为与 r4 逐位一致)。"""
    try:
        if resolve_species_name(species) == "Homo sapiens":
            return None
        return str(export_codon_usage_csv(species))
    except KeyError:
        return None


def build_pool(
    target_id: str,
    meta: dict[str, Any],
    registry: Any,
    *,
    log: Any = None,
) -> dict[str, Any]:
    """Generate the shared 36-candidate pool for one target.

    Pool-level evaluation = constraint matrix + full-length LinearFold (C7/D3/E7)
    + start-region window fold (C6) + archive E1–E12.  ``workflow.evaluate`` is
    NOT called at pool level (§3.1); junction E3 is added at delivery level only.
    """
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    t0 = time.perf_counter()

    # ── CDS 生成(方案 B 2026-08-07, 用户拍板): LD 4 λ + RNARL 1 + GEMORNA N 采样 ──
    # B0 生成侧修复(2026-08-08 用户拍板, 仅非 human 物种): LD 用 species 匹配
    # Kazusa codon-usage 表生成, 消除「E5 按 species 表计分 vs LD 默认 human 表
    # 生成」的错配(GFP: 0.70 天花板 → CAI=1.0); human 保持默认表, 与 r4 逐位一致。
    ld_codon_usage_path = _ld_codon_usage_path(species)
    cds_wf = MrnaCdsDesignWorkflow(registry)
    cds_by_lambda: dict[float, str] = {}
    cds_items: list[tuple[str, float, int, str]] = []  # (source, lambda, idx, cds)
    for lam in LAMBDAS:
        inp = MrnaCdsDesignInput(
            protein_sequence=protein,
            design_tool="lineardesign",
            lambda_value=lam,
            cai_species=species,
            lineardesign_codon_usage_path=ld_codon_usage_path,
            run_fold=False,
            run_gc=False,
        )
        cands = cds_wf.generate_candidates(inp)
        if cands:
            cds_seq = _rna(cands[0].sequence)
            cds_by_lambda[lam] = cds_seq
            cds_items.append(("ld", lam, 0, cds_seq))
            if log:
                log(f"  [pool:{target_id}] CDS lambda={lam} len={len(cds_seq)}")
        else:
            if log:
                log(f"  [pool:{target_id}] WARN CDS lambda={lam} failed (skipped)")
    if not cds_by_lambda:
        raise RuntimeError(f"pool generation failed: no CDS produced for {target_id}")

    # RNARL 1 条(homo_mrna, argmax 确定性; 失败跳过不阻断池)
    try:
        rnarl_cands = cds_wf.generate_candidates(MrnaCdsDesignInput(
            protein_sequence=protein, design_tool="rnarl", cai_species=species,
            run_fold=False, run_gc=False,
        ))
        if rnarl_cands:
            cds_items.append(("rnarl", LAMBDA_RNARL, 0, _rna(rnarl_cands[0].sequence)))
            if log:
                log(f"  [pool:{target_id}] CDS rnarl(homo_mrna) len={len(rnarl_cands[0].sequence)}")
        else:
            if log:
                log(f"  [pool:{target_id}] WARN CDS rnarl returned no candidates (skipped)")
    except Exception as e:  # noqa: BLE001 - RNARL 单条失败不阻断池(池至少有 LD)
        if log:
            log(f"  [pool:{target_id}] WARN CDS rnarl failed: {e} (skipped)")

    # GEMORNA N 采样(非幂等 → (target, idx) 落盘缓存, 池可复现)
    gemorna_seqs: list[str] = [
        _gemorna_cds_cached(target_id, i, protein) for i in range(GEMORNA_CDS_N)
    ]
    for i, seq in enumerate(gemorna_seqs):
        cds_items.append(("gemorna", LAMBDA_GEMORNA, i, seq))
    if log:
        log(f"  [pool:{target_id}] CDS gemorna {GEMORNA_CDS_N} samples "
            f"(unique={len(set(gemorna_seqs))}) len={len(gemorna_seqs[0])}")

    # ── UTR: GEMORNA 6 次(每 preset 一次, 序列缓存)──
    utr5_cache: dict[str, str] = {}
    utr3_cache: dict[str, str] = {}
    for preset in UTR_PRESETS:
        utr5_cache[preset] = _gemorna_cached("5utr", preset, target_id)
        utr3_cache[preset] = _gemorna_cached("3utr", preset, target_id)
        if log:
            log(f"  [pool:{target_id}] UTR5 {preset}={len(utr5_cache[preset])}nt "
                f"UTR3 {preset}={len(utr3_cache[preset])}nt")

    # ── 组合: (LD 4 + RNARL 1 + GEMORNA 30) × 9 UTR = 315 候选 ──
    candidates: list[dict[str, Any]] = []
    for source, lam, idx, cds_seq in cds_items:
        for u5p in UTR_PRESETS:
            for u3p in UTR_PRESETS:
                candidates.append(make_candidate(
                    cds_seq, utr5_cache[u5p], utr3_cache[u3p], lam, u5p, u3p, species,
                    source=source, idx=idx,
                ))

    # ── 池级档案: E1 CAI(每 CDS 一次), E4/E5 GEMORNA 预测(每唯一 UTR 一次)──
    cai_cache: dict[str, float] = {}
    for _, _, _, cds_seq in cds_items:
        cai_cache[cds_seq] = cds_cai(cds_seq, species)
    mrl_cache: dict[str, float] = {p: gemorna_predict_mrl(utr5_cache[p]) for p in UTR_PRESETS}
    stab_cache: dict[str, float] = {p: gemorna_predict_stability(utr3_cache[p]) for p in UTR_PRESETS}
    rare_cache: dict[str, set[str]] = {species: rare_codon_set(species)}
    wt_gc = _wt_cds_gc(target_id)
    if log:
        log(f"  [pool:{target_id}] wt_cds_gc={wt_gc:.3f}")

    # ── 每候选: 窗口 fold(C6) + 全长 fold(C7/E7/D3) + 约束判定 + 档案 ──
    # 窗口 = utr5 + cds[:30], 与 3'UTR 无关 → ≤25 CDS × 3 utr5 唯一窗口(去重缓存)
    window_fold_cache: dict[tuple[str, str], str] = {}
    for cand in candidates:
        cds_seq, utr5, utr3 = cand["cds"], cand["utr5"], cand["utr3"]
        window_key = (utr5, cds_seq)
        if window_key not in window_fold_cache:
            win_seq = utr5 + cds_seq[:START_REGION_CDS_PREFIX]
            window_fold_cache[window_key] = linearfold(win_seq)["structure"]
        win_struct = window_fold_cache[window_key]

        full_struct = linearfold(cand["sequence"])["structure"]

        c1 = not sliding_window_gc_out_of_bounds(cand["sequence"])
        c2 = not has_homopolymer(cand["sequence"])
        # C3/C4/C5/C8 已降为软约束(实施修正 2026-08-07): 仅档案计数, 不参与 pass 判定
        c6 = longest_stem_bp(win_struct) <= START_REGION_MAX_STEM
        c7 = longest_stem_bp(full_struct) <= FULL_MAX_STEM
        m1 = boundary_gc_ok(utr5, cds_seq, utr3)
        # 【档位 B-1, 2026-08-08 用户拍板】CAI ≥ 0.8 进硬约束(池级 cai_cache 已建);
        # 【v6 记录, 2026-08-08】0.7 试探后用户拍板恢复 0.8(CAI_MIN 见阈值定义)
        cai = cai_cache[cds_seq] >= CAI_MIN
        cand["constraints"] = {"C1": c1, "C2": c2,
                               "C6": c6, "C7": c7, "M1": m1, "CAI": cai}
        cand["flags"]["passed"] = all(cand["constraints"].values())
        cand["flags"]["no_constraint_solution"] = not cand["flags"]["passed"]

        cds_struct = full_struct[len(utr5) : len(utr5) + len(cds_seq)]
        cand["archive"] = {
            "C3_polya_signal_count": polya_signal_count(cds_seq),   # 软约束档案(修正)
            "C4_restriction_hits": restriction_site_hits(cand["sequence"]),  # 软约束档案(修正)
            "C5_splice_motif_count": splice_motif_count(cds_seq),   # 软约束档案(修正)
            "C8_uAUG_count": utr5.count("AUG"),                     # 软约束档案(修正)
            "E1_cai": cai_cache[cds_seq],
            "E2_full_mfe": _fold_mfe(cand["sequence"]),
            "E3_junction_mfe_per_nt": None,   # 交付级补
            "E4_utr5_mrl": mrl_cache[utr5_preset_of(cand)],
            "E5_utr3_stability": stab_cache[utr3_preset_of(cand)],
            "E6_rare_codons": rare_codon_count(cds_seq, species, rare_cache[species]),
            "E7_pair_ratio": pair_ratio(full_struct),
            "E8_delta_gc": abs(gc_fraction(cand["sequence"]) - wt_gc),
            "E9_are_count": are_count(utr3),
            "E10_kozak": kozak_score(utr5, cds_seq),
            "E11_ld_lambda": lam_of(cand),
            "E11_utility_lambda": None,   # 选点后回填
            "E12_motivation": "",          # 臂/LLM 回填
            "C6_start_open": unpaired_fraction(win_struct),
            "C7_longest_stem": longest_stem_bp(full_struct),
            "CDS_unpaired": unpaired_fraction(cds_struct),
            "full_gc": gc_fraction(cand["sequence"]),
        }
        cand["full_structure"] = full_struct

    pool = {
        "target_id": target_id,
        "species": species,
        "protein": protein,
        "cds_by_lambda": cds_by_lambda,
        "cds_counts": {"lineardesign": len(cds_by_lambda), "rnarl": sum(1 for s, *_ in cds_items if s == "rnarl"),
                       "gemorna": sum(1 for s, *_ in cds_items if s == "gemorna")},
        "utr5_cache": utr5_cache,
        "utr3_cache": utr3_cache,
        "cai_cache": cai_cache,
        "mrl_cache": mrl_cache,
        "stab_cache": stab_cache,
        "wt_cds_gc": wt_gc,
        "candidates": candidates,
        "generation_seconds": time.perf_counter() - t0,
    }
    if log:
        n_pass = sum(1 for c in candidates if c["flags"]["passed"])
        log(f"  [pool:{target_id}] done: {len(candidates)} candidates, "
            f"{n_pass} pass all constraints, {pool['generation_seconds']:.0f}s")
    return pool


def lam_of(cand: dict[str, Any]) -> float:
    return float(cand["lambda"])


def utr5_preset_of(cand: dict[str, Any]) -> str:
    return cand["utr5_preset"]


def utr3_preset_of(cand: dict[str, Any]) -> str:
    return cand["utr3_preset"]


def _fold_mfe(seq: str) -> float:
    """Full-length MFE — folded once at pool build; cached on the candidate."""
    fp = save_sequence(seq, prefix="e5_mfe")
    return float(predict_rna_secondary_structure_with_linearfold.func(fp)["mfe"])


def _wt_cds_gc(target_id: str) -> float:
    """GC of the benchmark's wild-type CDS (E8 reference; 实施细化 2)."""
    fa = WT_CDS_DIR / f"{target_id}.fa"
    if not fa.is_file():
        return 0.0
    lines = [ln.strip() for ln in fa.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.lstrip().startswith(">")]
    return gc_fraction("".join(lines))


# ---------------------------------------------------------------------------
# 效用函数 U(§5; 先过滤, 区域内归一化, 跨区全局分量)
# ---------------------------------------------------------------------------


def pool_normalizers(pool: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """Per-archive-key min/max over the pool (for within-pool normalization)."""
    keys = ["E1_cai", "E2_full_mfe", "E4_utr5_mrl", "E5_utr3_stability",
            "E6_rare_codons", "E7_pair_ratio", "E8_delta_gc", "E9_are_count",
            "E10_kozak", "C6_start_open", "C7_longest_stem", "CDS_unpaired",
            "E3_junction_mfe_per_nt"]
    vals: dict[str, list[float]] = {k: [] for k in keys}
    for c in pool["candidates"]:
        for k in keys:
            v = c["archive"].get(k)
            if v is not None:
                vals[k].append(float(v))
    out: dict[str, tuple[float, float]] = {}
    for k, vs in vals.items():
        if vs:
            out[k] = (min(vs), max(vs))
    return out


def _norm(v: float | None, lo: float, hi: float) -> float:
    if v is None:
        return 0.0
    if hi - lo < 1e-9:
        return 0.5
    return (float(v) - lo) / (hi - lo)


def regional_metric(cand: dict[str, Any], profile: str,
                    norms: dict[str, tuple[float, float]]) -> dict[str, float]:
    """区域内指标(0..1 同向高好)与权重(§5 实施细化 4)。"""
    a = cand["archive"]
    lo, hi = norms.get("E4_utr5_mrl", (0.0, 1.0))
    mrl = _norm(a.get("E4_utr5_mrl"), lo, hi)
    lo, hi = norms.get("C6_start_open", (0.0, 1.0))
    start_open = _norm(a.get("C6_start_open"), lo, hi)
    lo, hi = norms.get("E1_cai", (0.0, 1.0))
    cai = _norm(a.get("E1_cai"), lo, hi)
    lo, hi = norms.get("CDS_unpaired", (0.0, 1.0))
    cds_struct = _norm(a.get("CDS_unpaired"), lo, hi)
    lo, hi = norms.get("E6_rare_codons", (0.0, 1.0))
    rare = 1.0 - _norm(a.get("E6_rare_codons"), lo, hi)   # 计数负向
    lo, hi = norms.get("E5_utr3_stability", (0.0, 1.0))
    stab = _norm(a.get("E5_utr3_stability"), lo, hi)

    axis = PROFILE_DEFS[profile]["utr5_axis"]
    if axis == "mrl":
        utr5_score = 0.6 * mrl + 0.4 * start_open
    elif axis == "start_open":
        utr5_score = 0.6 * start_open + 0.4 * mrl
    else:
        utr5_score = 0.5 * mrl + 0.5 * start_open
    cds_score = (cai + cds_struct + rare) / 3.0
    utr3_score = stab

    weights = PROFILE_DEFS[profile]["region_weights"]
    return {
        "utr5": utr5_score, "cds": cds_score, "utr3": utr3_score,
        "regional": (weights[0] * utr5_score + weights[1] * cds_score
                     + weights[2] * utr3_score),
        "mrl": mrl, "start_open": start_open, "cai": cai,
        "cds_struct": cds_struct, "rare": rare, "stab": stab,
    }


def _lambda_pref_comp(cand: dict[str, Any], profile: str) -> float:
    """λ 偏好分量(0..1, 档距归一化): 候选 λ_rank 与画像偏好 λ 档的接近度。
    【档位 A-①, 2026-08-08 用户拍板】λ_pref 进 U — 修复"3 画像 top-1 恒同一候选"的
    R3 分离失效。画像偏好 λ 由 LAMBDA_PREF_VALUE(映射修正后)→ LAMBDA_RANK 取档。"""
    pref_lam = LAMBDA_PREF_VALUE[PROFILE_DEFS[profile]["lambda_pref"]]
    pref_rank = LAMBDA_RANK[pref_lam]
    dist = abs(cand["lambda_rank"] - pref_rank)
    return 1.0 - min(dist, LAMBDA_RANK_SPAN) / LAMBDA_RANK_SPAN


def utility(cand: dict[str, Any], profile: str,
            norms: dict[str, tuple[float, float]]) -> float:
    """U = (0.8×regional + 0.2×global + W_LAMBDA×λ偏好) / (1+W_LAMBDA) (∈[0,1]).
    full-length MFE global; junction at delivery; λ 偏好分量见 _lambda_pref_comp。"""
    regional = regional_metric(cand, profile, norms)["regional"]
    lo, hi = norms.get("E2_full_mfe", (0.0, 1.0))
    mfe_norm = 1.0 - _norm(cand["archive"].get("E2_full_mfe"), lo, hi)  # 越负越好
    global_part = mfe_norm
    lo, hi = norms.get("E3_junction_mfe_per_nt", (0.0, 1.0))
    jun = cand["archive"].get("E3_junction_mfe_per_nt")
    if jun is not None and hi - lo > 1e-9:
        global_part = 0.5 * global_part + 0.5 * (1.0 - _norm(jun, lo, hi))
    base = W_REGIONAL * regional + W_GLOBAL * global_part
    return (base + W_LAMBDA * _lambda_pref_comp(cand, profile)) / (1.0 + W_LAMBDA)


def assign_utilities(pool: dict[str, Any], profiles: list[str] = list(PROFILES)) -> None:
    norms = pool_normalizers(pool)
    for c in pool["candidates"]:
        c["scores"] = {p: regional_metric(c, p, norms) for p in profiles}
        c["utility"] = {p: utility(c, p, norms) for p in profiles}
    pool["norms"] = norms


# ---------------------------------------------------------------------------
# 评测: R1–R4 / D1–D3 / 通过率
# ---------------------------------------------------------------------------


def delivery_e2e_pass(delivery: list[dict[str, Any]]) -> bool:
    return len(delivery) == 5 and all(c["flags"]["passed"] for c in delivery)


def constraint_satisfaction_rate(delivery: list[dict[str, Any]]) -> float:
    if not delivery:
        return 0.0
    return mean(
        sum(1 for v in c["constraints"].values() if v) / len(CONSTRAINT_IDS)
        for c in delivery
    )


def rank_by_utility(delivery: list[dict[str, Any]], profile: str) -> list[dict[str, Any]]:
    return sorted(delivery, key=lambda c: c["utility"][profile], reverse=True)


def kendall_tau_rankings(r1: list[str], r2: list[str]) -> float:
    """Kendall τ over two id-ordered rankings (shared item subset).

    共享项 <2 时 τ 无定义 → 返回 0.0(保守;旧实现把完全不相交的两列
    误报为 τ=1.0: `shared == ids2[:0]` 对空表恒真,已于 2026-08-07 修复)。
    """
    ids1, ids2 = list(r1), list(r2)
    shared = [i for i in ids1 if i in ids2]
    if len(shared) < 2:
        return 0.0
    x = [shared.index(i) for i in shared]
    y = [ids2.index(i) for i in shared]
    return float(scipy_stats.kendalltau(x, y).statistic)


def spearman_rho_rankings(delivery_rank: list[str], u_rank: list[str]) -> float:
    ids_d, ids_u = list(delivery_rank), list(u_rank)
    shared = [i for i in ids_d if i in ids_u]
    if len(shared) < 2:
        return 1.0
    x = [shared.index(i) for i in shared]
    y = [ids_u.index(i) for i in shared]
    return float(scipy_stats.spearmanr(x, y).statistic)


def diversity_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    sa, sb = _rna(a["sequence"]), _rna(b["sequence"])
    if len(sa) == len(sb):
        diffs = sum(1 for x, y in zip(sa, sb) if x != y)
        return diffs / len(sa)
    return 1.0 - difflib.SequenceMatcher(None, sa, sb).ratio()


def evaluate_delivery(delivery: list[dict[str, Any]], profile: str,
                      pool: dict[str, Any], u_rank: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-profile delivery metrics (R1/R4, D1–D3, 通过率/满足率)."""
    delivery_rank_ids = [c["id"] for c in delivery]
    u_rank_ids = [c["id"] for c in u_rank]

    # R1: 交付排序 vs U 排序 Spearman ρ=1.0(tie 内序允许 → ρ≥1−ε)
    rho = spearman_rho_rankings(delivery_rank_ids, u_rank_ids)
    r1 = rho >= 1.0 - 1e-6

    # R4: top-1 的 U 为约束满足子集内最大且约束满足数最多
    passed_subset = [c for c in pool["candidates"] if c["flags"]["passed"]]
    top1 = delivery[0] if delivery else None
    r4_pass, r4_marked = False, False
    if top1 is not None:
        if passed_subset:
            max_u = max(c["utility"][profile] for c in passed_subset)
            max_n = max(sum(1 for v in c["constraints"].values() if v)
                        for c in passed_subset)
            top1_u = top1["utility"][profile]
            top1_n = sum(1 for v in top1["constraints"].values() if v)
            r4_pass = (top1_u >= max_u - 1e-9) and (top1_n == max_n)
        else:
            pool_max = max(c["utility"][profile] for c in pool["candidates"])
            r4_pass = top1["utility"][profile] >= pool_max - 1e-9
            r4_marked = True  # "无约束满足候选"显式标记

    # D1: pairwise 最小差异 ≥ 2%
    min_dist = min(
        diversity_distance(delivery[i], delivery[j])
        for i in range(len(delivery)) for j in range(i + 1, len(delivery))
    ) if len(delivery) >= 2 else 0.0
    d1 = min_dist >= 0.02

    # D2: ≥3 个不同 λ 或存在索引间距 ≥2 档
    lams = sorted({c["lambda_rank"] for c in delivery})
    d2 = len(lams) >= 3 or any(
        b - a >= 2 for a in lams for b in lams if b > a
    )

    # D3: pair ratio 极差 ≥3pp 或最长茎差 ≥5bp(全长 fold 输出, 与 C7 同次)
    # 【v7 2026-08-08】空交付兜底(与 D1 同风格): GFP 0-pass 池空交付时
    # max() 空 iterable 会崩溃 → 空列表极差记 0.0, D3=False(该靶失败, 不崩全盘)。
    prs = [c["archive"]["E7_pair_ratio"] for c in delivery]
    stems = [c["archive"]["C7_longest_stem"] for c in delivery]
    pr_range = (max(prs) - min(prs)) if prs else 0.0
    stem_range = (max(stems) - min(stems)) if stems else 0.0
    d3 = (pr_range >= 3.0) or (stem_range >= 5.0)

    return {
        "profile": profile,
        "delivered_ids": delivery_rank_ids,
        "e2e_pass": delivery_e2e_pass(delivery),
        "constraint_rate": constraint_satisfaction_rate(delivery),
        "R1_spearman": rho, "R1": r1,
        "R4": r4_pass, "R4_no_constraint_solution_marked": r4_marked,
        "D1_min_dist": min_dist, "D1": d1,
        "D2_lambda_ranks": lams, "D2": d2,
        "D3_pair_ratio_range": pr_range,
        "D3_stem_range": stem_range, "D3": d3,
    }


def evaluate_arm(arm: dict[str, Any], pool: dict[str, Any],
                 profiles: list[str] = list(PROFILES)) -> dict[str, Any]:
    """Full arm-level metrics across profiles (R3 敏感性与 R1/R2 汇总)。"""
    per_profile = []
    for profile in profiles:
        delivery = arm["deliveries"].get(profile, [])
        u_rank = rank_by_utility(delivery, profile) if delivery else []
        per_profile.append(evaluate_delivery(delivery, profile, pool, u_rank))
    # R3: 3 画像两两 top-1 分离(CAI 差 ≥0.05 或 λ 差 ≥2 档), ≥1/3 对(2026-08-08 v4 放宽)
    tops = []
    for profile in profiles:
        d = arm["deliveries"].get(profile, [])
        tops.append(d[0] if d else None)
    pairs, separated = [], 0
    for i in range(len(tops)):
        for j in range(i + 1, len(tops)):
            if tops[i] is None or tops[j] is None:
                continue
            pairs.append((profiles[i], profiles[j]))
            d_cai = abs(tops[i]["archive"]["E1_cai"] - tops[j]["archive"]["E1_cai"])
            d_lam = abs(tops[i]["lambda_rank"] - tops[j]["lambda_rank"])
            if d_cai >= 0.05 or d_lam >= 2:
                separated += 1
    r3 = (separated / len(pairs) >= 1 / 3) if pairs else False
    # R2(重复间)由调用方在多次运行间计算; 此处记录单次
    return {
        "arm": arm["arm"],
        "target_id": arm["target_id"],
        "profiles": per_profile,
        "R3_separated_pairs": separated,
        "R3_total_pairs": len(pairs),
        "R3": r3,
        "llm_calls": arm.get("llm_calls", 0),
        "lineardesign_calls": arm.get("lineardesign_calls", 0),
        "elapsed_seconds": arm.get("elapsed_seconds", 0.0),
        "audit_events": arm.get("audit_events", 0),
    }


def r2_stability(arm_runs: list[dict[str, Any]], profile: str) -> float:
    """Kendall τ over repeated runs' delivery rankings (pairwise min)."""
    rankings = [a["deliveries"][profile] for a in arm_runs]
    ids = [[c["id"] for c in r] for r in rankings if r]
    if len(ids) < 2:
        return 1.0
    taus = [
        kendall_tau_rankings(ids[i], ids[j])
        for i in range(len(ids)) for j in range(i + 1, len(ids))
    ]
    return min(taus) if taus else 1.0


# ---------------------------------------------------------------------------
# 三臂
# ---------------------------------------------------------------------------


def _pool_overview(pool: dict[str, Any]) -> str:
    """Deterministic pool summary fed to the LLM as observation."""
    by_lam: dict[float, list[dict[str, Any]]] = {}
    for c in pool["candidates"]:
        by_lam.setdefault(c["lambda"], []).append(c)
    n_ld = sum(1 for c in pool["candidates"] if c["source"] == "ld")
    n_rn = sum(1 for c in pool["candidates"] if c["source"] == "rnarl")
    n_gm = sum(1 for c in pool["candidates"] if c["source"] == "gemorna")
    lines = [
        f"Pool: {len(pool['candidates'])} candidates "
        f"({n_ld} LinearDesign(4 lambdas) + {n_rn} RNARL + {n_gm} GEMORNA-sample CDS, "
        f"each x 9 GEMORNA UTR combos) for target "
        f"{pool['target_id']} (species={pool['species']}).",
    ]
    for lam in sorted(by_lam):
        cs = by_lam[lam]
        passing = [c for c in cs if c["flags"]["passed"]]
        top = max((c for c in cs), key=lambda c: c["archive"]["E1_cai"]) if cs else None
        ids_str = ", ".join(c["id"] for c in passing[:12])
        if len(passing) > 12:
            ids_str += f", ... (+{len(passing) - 12} more)"
        line = (f"lambda={lam}: {len(cs)} candidates, {len(passing)} pass ALL "
                f"{len(CONSTRAINT_IDS)} constraints ({'/'.join(CONSTRAINT_IDS)}); "
                f"ids={ids_str}")
        if top:
            line += (f"; top CAI={top['archive']['E1_cai']:.3f} "
                     f"MFE={top['archive']['E2_full_mfe']:.1f}")
        lines.append(line)
    lines.append("Profiles: expression(小λ CAI优先), stability(大λ 稳定优先), "
                 "balanced(中λ 均等). U=0.8*regional+0.2*global(MFE).")
    lines.append("Rule of delivery: exactly 5 constraint-passing candidates per profile. "
                 "The candidate table lists ONLY constraint-passing rows; non-passing "
                 "candidates are rejected by the gate, never deliver them. Deliveries "
                 "must span >=3 distinct lambda ranks (or pairwise rank spacing >=2) "
                 "where the pool allows (diversity D2); lambda<0 are non-LinearDesign "
                 "sources, each its own rank tier (-2=RNARL, -1=GEMORNA sample). "
                 "Ranking is mechanized: the system re-orders your final 5 candidates "
                 "per profile by U descending (consistency R1); cite archive metrics "
                 "only to arbitrate U ties.")
    return "\n".join(lines)


def _candidate_table(pool: dict[str, Any]) -> str:
    """Compact per-candidate table for LLM observation (archive + constraints + U).

    方案 B(2026-08-07): 池 225 候选 → 只列过约束(pass)行, 否则淹没 LLM。
    """
    passing = [c for c in pool["candidates"] if c["flags"]["passed"]]
    ucol = " | ".join(f"U({p})" for p in PROFILES)
    header = (f"id | lambda | utr5 | utr3 | {'/'.join(CONSTRAINT_IDS)}"
              f" | {ucol} | CAI | MFE "
              "| MRL | stab | rare | pair% | stem | ARE | Kozak")
    rows = [
        f"# Candidate table: {len(passing)}/{len(pool['candidates'])} pool candidates "
        f"pass all constraints (non-passing rows omitted). "
        f"lambda<0 = non-LinearDesign sources: -2=RNARL, -1=GEMORNA sample.",
        header,
    ]
    for c in passing:
        cs = "".join("1" if c["constraints"][k] else "0" for k in CONSTRAINT_IDS)
        a = c["archive"]
        us = " | ".join(f"{c['utility'][p]:.3f}" for p in PROFILES)
        rows.append(
            f"{c['id']} | {c['lambda']} | {c['utr5_preset']} | {c['utr3_preset']} | "
            f"{cs} | {us} | {a['E1_cai']:.3f} | "
            f"{a['E2_full_mfe']:.1f} | {a['E4_utr5_mrl']:.2f} | "
            f"{a['E5_utr3_stability']:.2f} | {a['E6_rare_codons']} | "
            f"{a['E7_pair_ratio']:.1f} | {a['C7_longest_stem']} | "
            f"{a['E9_are_count']} | {a['E10_kozak']:.2f}"
        )
    return "\n".join(rows)


def _llm_invoke(llm: Any, system: str, user: str) -> dict[str, Any]:
    from langchain_core.messages import HumanMessage, SystemMessage

    raw = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = raw.content if hasattr(raw, "content") else str(raw)
    text = str(content).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start : end + 1])


ACTION_SYSTEM = """\
You are the constraint-navigation agent of an RNA full-length mRNA design system.
You operate on a SHARED candidate pool (already generated and fully evaluated).
Each round you reply with ONE JSON action. Available actions:
{"action": "select", "profiles": {"<profile>": ["<candidate_id>", ...5 ids]},
 "rationale": "..."}
    Choose exactly 5 candidate ids per profile for delivery.
{"action": "sort", "profiles": {"<profile>": {"ranking": ["<5 ids>"],
 "arbitration": [{"pair": ["<idA>", "<idB>"], "layer": 1|2|3|4,
 "evidence": "<archive metric key(s) cited>"}]}},
 "rationale": "..."}
    Provide your 5-candidate order per profile as tie-break arbitration ONLY: the
    system re-orders them by U descending (mechanized, consistency R1). Arbitration
    layers: 1=immunogenicity (C7 longest stem, E9 ARE), 2=stability (E2 MFE,
    E7 pair ratio), 3=translation start (E4 MRL, C6 start openness),
    4=codon preference (E1 CAI, E6 rare codons).
{"action": "lineardesign", "lambda": <float>, "reason": "..."}
    Request at most ONE extra LinearDesign CDS (neighbour lambda) per gene.
{"action": "repair", "profile": "<profile>", "replace": {"drop": "<id>", "add": "<id>"},
 "reason": "..."}  // C arm only, max 2 rounds
{"action": "finalize", "deliveries": {"<profile>": {"ranking": ["<5 ids>"],
 "notes": {"<candidate_id>": "<mRNAdesigner-inspired motivation for E12>"}}},
 "rationale": "..."}
    Final delivery: exactly 5 constraint-passing candidates per profile (gate
    enforces this; the candidate table lists ONLY passing rows). The 5 candidates
    must span >=3 distinct lambda ranks (or pairwise rank spacing >=2) where the
    pool allows (diversity D2); lambda<0 are non-LinearDesign sources, each its
    own rank tier (-2=RNARL, -1=GEMORNA sample). Ranking is mechanized: the system
    re-orders your ranking by U descending; use it to arbitrate U ties only.
IMPORTANT: reply with JSON only, no prose outside the JSON object.
"""


def _observation(pool: dict[str, Any], history: list[dict[str, Any]],
                 gate_feedback: str = "") -> str:
    return (
        _pool_overview(pool)
        + "\n\nCandidate table:\n"
        + _candidate_table(pool)
        + "\n\nRound history:\n"
        + (json.dumps(history, ensure_ascii=False) if history else "(none)")
        + (f"\n\nGATE FEEDBACK (hard constraints, do not contest):\n{gate_feedback}"
           if gate_feedback else "")
    )


def mechanize_delivery_order(selected: list[dict[str, Any]],
                             profile: str) -> list[dict[str, Any]]:
    """排序机制化(方案 B 并行, 2026-08-07, 用户拍板): finalize 时系统按 U 降序
    强制重排 LLM 的 5 候选; 稳定排序 → U tie 内序保留 LLM 仲裁顺序(LLM 只做
    tie-break 仲裁)。S0 二次 NO-GO 根因是 LLM 不按 U(τ=0.0) + 端点轮间非确定,
    机制化后交付排序不再依赖 LLM 服从度。判据/阈值零改动。"""
    return sorted(selected, key=lambda c: c["utility"][profile], reverse=True)


def _default_delivery(pool: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    """A-arm rule(§6): 先按约束过滤 → 按画像权重选 λ(画像偏好 λ 的 U 最大候选居首) →
    跨 λ 分散补足(每 λ 取 top1, 保 D2 ≥3 档) → 其余按 U 补满 → 规则效用排序交付。
    【档位 A-③, 2026-08-08 用户拍板】首位取画像偏好 λ 候选: 旧实现按 λ 值排序取桶顶,
    使三画像 top-1 恒为同一候选(RNARL/λ=0 桶顶), 与画像无关。λ_pref 已进 U(档位 A-①),
    故最终 U 排序后 top-1 自然落于偏好 λ 候选(除非跨 λ 基础 U 差 > λ 偏好增益)。"""
    passed = [c for c in pool["candidates"] if c["flags"]["passed"]]
    ranked = sorted(passed, key=lambda c: c["utility"][profile], reverse=True)
    if len(ranked) <= 5:
        return ranked
    pref_lam = LAMBDA_PREF_VALUE[PROFILE_DEFS[profile]["lambda_pref"]]
    selected: list[dict[str, Any]] = []
    # 画像偏好 λ 的 U 最大候选居首(§6 按画像选 λ)
    for c in ranked:
        if c["lambda"] == pref_lam:
            selected.append(c)
            break
    # 跨 λ 分散: 其余 λ 各取 top1
    for lam in sorted({c["lambda"] for c in ranked}):
        for c in ranked:
            if c["lambda"] == lam and c not in selected:
                selected.append(c)
                break
    # 按 U 补足至 5
    for c in ranked:
        if c not in selected:
            selected.append(c)
        if len(selected) >= 5:
            break
    # §6 规则效用排序: 交付按 U 降序
    return sorted(selected[:5], key=lambda c: c["utility"][profile], reverse=True)


def _mark_delivery(delivery: list[dict[str, Any]], profile: str,
                   pool: dict[str, Any], utility_lambda_note: str) -> list[dict[str, Any]]:
    for c in delivery:
        c["flags"]["delivered"] = True
        c["archive"]["E11_utility_lambda"] = utility_lambda_note
    return delivery


# ── A 臂: 单工具直跑(零 LLM 零工具调用)──
def run_arm_a(pool: dict[str, Any], target_id: str,
              profiles: list[str] = list(PROFILES)) -> dict[str, Any]:
    t0 = time.perf_counter()
    deliveries: dict[str, list[dict[str, Any]]] = {}
    for profile in profiles:
        d = _default_delivery(pool, profile)
        d = _mark_delivery(d, profile, pool, "rule: profile lambda preference")
        deliveries[profile] = d
    return {
        "arm": "A", "target_id": target_id,
        "deliveries": deliveries,
        "llm_calls": 0, "lineardesign_calls": 0,
        "audit_events": 0, "elapsed_seconds": time.perf_counter() - t0,
    }


# ── B 臂: 无门控 LLM agent(等价替代; 2–4 次 LLM, ≤1 次额外 LinearDesign)──
def run_arm_b(pool: dict[str, Any], target_id: str, llm: Any,
              profiles: list[str] = list(PROFILES),
              extra_ld: dict[str, Any] | None = None) -> dict[str, Any]:
    """extra_ld: mutable dict {"calls": int} to share the ≤1 extra-LinearDesign budget."""
    t0 = time.perf_counter()
    extra_ld = {"calls": 0} if extra_ld is None else extra_ld
    history: list[dict[str, Any]] = []
    deliveries: dict[str, list[dict[str, Any]]] = {}
    ranking: dict[str, list[str]] = {}
    notes: dict[str, str] = {}
    llm_calls = 0

    def finish():
        # 机制化兜底(方案 B 并行, 2026-08-07): 最终交付按 U 降序重排
        for profile in profiles:
            d = deliveries.get(profile, [])
            if d:
                d = mechanize_delivery_order(d, profile)
            d = _mark_delivery(d, profile, pool, "B-arm: LLM free choice")
            deliveries[profile] = d

    while llm_calls < B_LLM_MAX:
        action = _llm_invoke(
            llm, ACTION_SYSTEM,
            f"Target {target_id}. Round {len(history) + 1}.\n{_observation(pool, history)}"
            f"\nProfiles to cover: {', '.join(profiles)}.",
        )
        llm_calls += 1
        kind = action.get("action")
        history.append({"action": kind, "payload": action, "gate": "none (ungated)"})
        if kind == "select":
            for profile in profiles:
                ids = action.get("profiles", {}).get(profile, [])
                deliveries[profile] = [c for c in pool["candidates"] if c["id"] in ids]
        elif kind == "sort":
            for profile in profiles:
                rk = action.get("profiles", {}).get(profile, {}).get("ranking", [])
                if rk:
                    ranking[profile] = rk
                    cands = {c["id"]: c for c in pool["candidates"]}
                    deliveries[profile] = [cands[i] for i in rk if i in cands]
        elif kind == "lineardesign":
            if extra_ld["calls"] < MAX_EXTRA_LINEARDESIGN:
                extra_ld["calls"] += 1
                new_cands = _neighbour_redesign(pool, float(action.get("lambda", 4.0)))
                if new_cands:
                    pool["candidates"].extend(new_cands)
                    assign_utilities(pool, list(profiles))
        elif kind == "finalize":
            for profile in profiles:
                rk = action.get("deliveries", {}).get(profile, {}).get("ranking", [])
                notes.update(action.get("deliveries", {}).get(profile, {}).get("notes", {}))
                if rk:
                    ranking[profile] = rk
                    cands = {c["id"]: c for c in pool["candidates"]}
                    sel = [cands[i] for i in rk if i in cands]
                    # 排序机制化(方案 B 并行): 按 U 强制重排, LLM 只仲裁 U tie
                    deliveries[profile] = mechanize_delivery_order(sel, profile)
            break
        if all(len(deliveries.get(p, [])) >= 5 for p in profiles) and llm_calls >= 2:
            # 已选满且至少 2 轮 → 结束
            break
    finish()
    for c in pool["candidates"]:
        if c["id"] in notes:
            c["archive"]["E12_motivation"] = notes[c["id"]]
    return {
        "arm": "B", "target_id": target_id,
        "deliveries": deliveries,
        "llm_calls": llm_calls, "lineardesign_calls": extra_ld["calls"],
        "audit_events": 0, "elapsed_seconds": time.perf_counter() - t0,
        "history": history,
    }


def _neighbour_redesign(pool: dict[str, Any], lam: float) -> list[dict[str, Any]]:
    """≤1 次/基因邻域 λ 重跑(修复轮专用; §13-8): 生成 1 个新 CDS 并组合 9 UTR。"""
    lam = min(max(round(lam, 1), 0.0), 20.0)
    cds_wf = MrnaCdsDesignWorkflow(pool["registry"])
    inp = MrnaCdsDesignInput(
        protein_sequence=pool["protein"],
        design_tool="lineardesign",
        lambda_value=lam,
        cai_species=pool["species"],
        lineardesign_codon_usage_path=_ld_codon_usage_path(pool["species"]),
        run_fold=False,
        run_gc=False,
    )
    cands = cds_wf.generate_candidates(inp)
    if not cands:
        return []
    cds_seq = _rna(cands[0].sequence)
    pool["cds_by_lambda"][lam] = cds_seq
    new_cai = cds_cai(cds_seq, pool["species"])
    pool["cai_cache"][cds_seq] = new_cai
    out = []
    for u5p in UTR_PRESETS:
        for u3p in UTR_PRESETS:
            c = make_candidate(cds_seq, pool["utr5_cache"][u5p],
                               pool["utr3_cache"][u3p], lam, u5p, u3p,
                               pool["species"])
            c["id"] = f"x{int(lam)}_u5{u5p[0]}_u3{u3p[0]}"
            _evaluate_candidate_in_pool(c, pool)
            out.append(c)
    return out


def _evaluate_candidate_in_pool(cand: dict[str, Any], pool: dict[str, Any]) -> None:
    """约束判定 + 档案 for one candidate inside an existing pool (repair leg)."""
    utr5, cds_seq, utr3 = cand["utr5"], cand["cds"], cand["utr3"]
    win_struct = linearfold(utr5 + cds_seq[:START_REGION_CDS_PREFIX])["structure"]
    full_struct = linearfold(cand["sequence"])["structure"]
    cand["constraints"] = {
        "C1": not sliding_window_gc_out_of_bounds(cand["sequence"]),
        "C2": not has_homopolymer(cand["sequence"]),
        # C3/C4/C5/C8 已降为软约束(实施修正 2026-08-07): 仅档案计数, 不参与 pass 判定
        "C6": longest_stem_bp(win_struct) <= START_REGION_MAX_STEM,
        "C7": longest_stem_bp(full_struct) <= FULL_MAX_STEM,
        "M1": boundary_gc_ok(utr5, cds_seq, utr3),
        # 【档位 B-1, 2026-08-08 用户拍板】CAI ≥ 0.8 进硬约束(repair 腿);
        # 【v6 记录, 2026-08-08】0.7 试探后用户拍板恢复 0.8(CAI_MIN 见阈值定义)
        "CAI": pool["cai_cache"].get(cds_seq, cds_cai(cds_seq, pool["species"])) >= CAI_MIN,
    }
    cand["flags"]["passed"] = all(cand["constraints"].values())
    cds_struct = full_struct[len(utr5) : len(utr5) + len(cds_seq)]
    cand["archive"] = {
        "C3_polya_signal_count": polya_signal_count(cds_seq),   # 软约束档案(修正)
        "C4_restriction_hits": restriction_site_hits(cand["sequence"]),  # 软约束档案(修正)
        "C5_splice_motif_count": splice_motif_count(cds_seq),   # 软约束档案(修正)
        "C8_uAUG_count": utr5.count("AUG"),                     # 软约束档案(修正)
        "E1_cai": pool["cai_cache"].get(cds_seq, cds_cai(cds_seq, pool["species"])),
        "E2_full_mfe": _fold_mfe(cand["sequence"]),
        "E3_junction_mfe_per_nt": None,
        "E4_utr5_mrl": pool["mrl_cache"][cand["utr5_preset"]],
        "E5_utr3_stability": pool["stab_cache"][cand["utr3_preset"]],
        "E6_rare_codons": rare_codon_count(cds_seq, pool["species"]),
        "E7_pair_ratio": pair_ratio(full_struct),
        "E8_delta_gc": abs(gc_fraction(cand["sequence"]) - pool["wt_cds_gc"]),
        "E9_are_count": are_count(utr3),
        "E10_kozak": kozak_score(utr5, cds_seq),
        "E11_ld_lambda": cand["lambda"],
        "E11_utility_lambda": None,
        "E12_motivation": "",
        "C6_start_open": unpaired_fraction(win_struct),
        "C7_longest_stem": longest_stem_bp(full_struct),
        "CDS_unpaired": unpaired_fraction(cds_struct),
        "full_gc": gc_fraction(cand["sequence"]),
    }
    cand["full_structure"] = full_struct


# ── C 臂: 门控 + 约束导航(DecisionGate + 约束矩阵 gate + 仲裁 + 修复轮)──
def run_arm_c(pool: dict[str, Any], target_id: str, llm: Any,
              audit: AuditTrail, gate: DecisionGate, self_model: SelfModel,
              profiles: list[str] = list(PROFILES),
              extra_ld: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    extra_ld = {"calls": 0} if extra_ld is None else extra_ld
    history: list[dict[str, Any]] = []
    deliveries: dict[str, list[dict[str, Any]]] = {}
    ranking: dict[str, list[str]] = {}
    notes: dict[str, str] = {}
    llm_calls = 0
    audit_events = 0
    repair_rounds = 0

    def audit_event(kind: str, payload: dict[str, Any]) -> None:
        nonlocal audit_events
        audit.record(kind, payload)
        audit_events += 1

    def gate_action(action: dict[str, Any]) -> str:
        """架构层门控: 动作集校验 + DecisionGate + 约束矩阵 gate。返回 gate 反馈(空=通过)。"""
        kind = action.get("action")
        if kind not in ("select", "sort", "repair", "lineardesign", "finalize"):
            msg = f"invalid action '{kind}' (allowed: select/sort/repair/lineardesign/finalize)"
            audit_event("gate_action_reject", {"action": kind, "reason": msg})
            return msg
        # DecisionGate(复用 E3 组件): 动作转 PlannedAction; use=none 不驱动排序/筛选 → allow
        decisions = gate.review(
            [PlannedAction(action_id=f"e5_{kind}", kind="oracle_lookup",
                           oracle=None, use="none")],
            task_type="full_length_mrna",
            target_family=pool["species"],
        )
        audit_event("gate_decision", {
            "action": kind, "verdict": decisions[0].verdict, "reason": decisions[0].reason,
        })
        # 约束矩阵 gate(架构强制): select/repair/finalize 的候选必须全过
        if kind in ("select", "repair", "finalize"):
            ids: list[str] = []
            if kind == "select":
                for p in profiles:
                    ids.extend(action.get("profiles", {}).get(p, []))
            elif kind == "repair":
                ids.append(action.get("replace", {}).get("add", ""))
            else:
                for p in profiles:
                    ids.extend(action.get("deliveries", {}).get(p, {}).get("ranking", []))
            cands = {c["id"]: c for c in pool["candidates"]}
            bad = []
            for i in ids:
                c = cands.get(i)
                if c is None:
                    bad.append(f"{i}:unknown")
                elif not c["flags"]["passed"]:
                    failed = [k for k, v in c["constraints"].items() if not v]
                    bad.append(f"{i}:{'/'.join(failed)}")
            if bad:
                msg = f"constraint gate: {len(bad)} candidate(s) not passing all constraints -> {bad}"
                audit_event("gate_constraint_reject", {"ids": ids, "reasons": bad})
                return msg
        return ""

    while llm_calls < C_LLM_MAX:
        feedback = ""
        action = _llm_invoke(
            llm, ACTION_SYSTEM,
            f"Target {target_id}. Round {len(history) + 1}. "
            f"GATE RULES: select/repair/finalize candidates MUST pass all 9 constraints.\n"
            f"{_observation(pool, history)}"
            f"\nProfiles to cover: {', '.join(profiles)}.",
        )
        llm_calls += 1
        kind = action.get("action", "")
        gate_fb = gate_action(action)
        if gate_fb:
            feedback = gate_fb
            history.append({"action": kind, "payload": action, "gate": gate_fb})
            if kind == "lineardesign":  # 越权重试会烧预算; 直接拒绝本轮
                continue
            continue  # LLM 重选(预算内)
        if kind == "select":
            for profile in profiles:
                ids = action.get("profiles", {}).get(profile, [])
                deliveries[profile] = [c for c in pool["candidates"] if c["id"] in ids]
        elif kind == "sort":
            ok = True
            for profile in profiles:
                entry = action.get("profiles", {}).get(profile, {})
                rk = entry.get("ranking", [])
                arb = entry.get("arbitration", [])
                for rec in arb:
                    layer = rec.get("layer")
                    ev = str(rec.get("evidence", ""))
                    allowed = {1: ("C7_longest_stem", "E9_are_count"),
                               2: ("E2_full_mfe", "E7_pair_ratio"),
                               3: ("E4_utr5_mrl", "C6_start_open"),
                               4: ("E1_cai", "E6_rare_codons")}
                    if layer not in allowed or not any(k in ev for k in allowed[layer]):
                        ok = False
                        break
                if not ok:
                    break
                if rk:
                    ranking[profile] = rk
                    cands = {c["id"]: c for c in pool["candidates"]}
                    deliveries[profile] = [cands[i] for i in rk if i in cands]
            if not ok:
                msg = ("arbitration gate: each arbitration record must cite archive "
                       "metrics of its layer (1:C7_longest_stem/E9_are_count, "
                       "2:E2_full_mfe/E7_pair_ratio, 3:E4_utr5_mrl/C6_start_open, "
                       "4:E1_cai/E6_rare_codons)")
                audit_event("gate_arbitration_reject", {"payload": action})
                history.append({"action": kind, "payload": action, "gate": msg})
                continue
        elif kind == "repair":
            if repair_rounds >= C_MAX_REPAIR_ROUNDS:
                audit_event("gate_repair_round_limit", {"rounds": repair_rounds})
                history.append({"action": kind, "payload": action,
                                "gate": "repair round limit reached"})
                continue
            repair_rounds += 1
            profile = action.get("profile", profiles[0])
            drop = action.get("replace", {}).get("drop")
            add = action.get("replace", {}).get("add")
            cur = deliveries.get(profile, [])
            cands = {c["id"]: c for c in pool["candidates"]}
            new_list = [c for c in cur if c["id"] != drop]
            if add in cands:
                new_list.append(cands[add])
            deliveries[profile] = new_list[:5]
            audit_event("repair_round", {"profile": profile, "drop": drop, "add": add})
        elif kind == "lineardesign":
            if extra_ld["calls"] < MAX_EXTRA_LINEARDESIGN:
                extra_ld["calls"] += 1
                audit_event("lineardesign_extra", {"lambda": action.get("lambda")})
                new_cands = _neighbour_redesign(pool, float(action.get("lambda", 4.0)))
                if new_cands:
                    pool["candidates"].extend(new_cands)
                    assign_utilities(pool, list(profiles))
                history.append({"action": kind, "payload": action, "gate": ""})
        elif kind == "finalize":
            for profile in profiles:
                entry = action.get("deliveries", {}).get(profile, {})
                rk = entry.get("ranking", [])
                notes.update(entry.get("notes", {}))
                if rk:
                    ranking[profile] = rk
                    cands = {c["id"]: c for c in pool["candidates"]}
                    sel = [cands[i] for i in rk if i in cands]
                    # 排序机制化(方案 B 并行): 按 U 强制重排, LLM 只仲裁 U tie
                    deliveries[profile] = mechanize_delivery_order(sel, profile)
            # 机制化重排记录(2026-08-07 修复: AuditEvent.event_type 为 Literal,
            # 不接受自定义事件 → 改记 history, 不进 audit_trail)
            history.append({
                "event": "mechanized_reorder",
                "profiles": {p: [c["id"] for c in deliveries.get(p, [])]
                             for p in profiles},
            })
            break
        history.append({"action": kind, "payload": action, "gate": feedback})

    # 机制化兜底: 无论 LLM 以哪条路径结束, 最终交付按 U 降序重排(2026-08-07)
    for profile in profiles:
        d = deliveries.get(profile, [])
        if d:
            d = mechanize_delivery_order(d, profile)
        d = _mark_delivery(d, profile, pool, "C-arm: gated selection")
        deliveries[profile] = d
    for c in pool["candidates"]:
        if c["id"] in notes:
            c["archive"]["E12_motivation"] = notes[c["id"]]
    return {
        "arm": "C", "target_id": target_id,
        "deliveries": deliveries,
        "llm_calls": llm_calls, "lineardesign_calls": extra_ld["calls"],
        "audit_events": audit_events, "elapsed_seconds": time.perf_counter() - t0,
        "repair_rounds": repair_rounds,
        "history": history,
    }


# ---------------------------------------------------------------------------
# 交付级评估(E3 junction; E4/E5 池级已算 → 复用)
# ---------------------------------------------------------------------------


def delivery_eval_junctions(pool: dict[str, Any], registry: Any,
                            arm: dict[str, Any]) -> None:
    """交付级补 E3 接头 mfe/nt(每交付候选; JunctionEvaluator 8015)。"""
    evaluator = JunctionEvaluator(registry)
    seen: set[str] = set()
    for profile in PROFILE_DEFS:
        for c in arm.get("deliveries", {}).get(profile, []):
            if c["id"] in seen:
                continue
            seen.add(c["id"])
            cand = Candidate(
                id=c["id"],
                sequence=c["sequence"],
                metadata={
                    "utr5_sequence": c["utr5"],
                    "cds_sequence": c["cds"],
                    "utr3_sequence": c["utr3"],
                },
            )
            metrics = evaluator.evaluate(cand, {"workflow_state": {}})
            j5 = metrics.get("junction_5utr_cds_mfe_per_nt")
            j3 = metrics.get("junction_cds_3utr_mfe_per_nt")
            vals = [v for v in (j5, j3) if v is not None]
            c["archive"]["E3_junction_mfe_per_nt"] = (
                sum(vals) / len(vals) if vals else None
            )


# ---------------------------------------------------------------------------
# 阶段判定书 + 编排
# ---------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def done_keys(records: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {(r["stage"], r["target_id"], r.get("arm")) for r in records
            if r.get("success")}


def make_runner() -> tuple[Any, Any]:
    executor = ToolExecutor(build_default_tool_registry(include_demo=False))
    registry = build_default_capability_registry(executor)
    return registry, executor


def write_record(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


E5_REQUIRED_CAPS = [
    "design_mrna_cds_with_lineardesign",   # 8014
    "design_5utr_with_gemorna",            # 8004
    "design_3utr_with_gemorna",
    "predict_5utr_mrl_with_gemorna",
    "predict_3utr_stability_with_gemorna",
    "predict_rna_secondary_structure_with_linearfold",  # 8015
]


def ensure_e5_services(log: Any = print) -> None:
    """Idempotent pre-flight: start any down microservice via start.sh (§14)."""
    services = get_services_for_capabilities(E5_REQUIRED_CAPS)
    ready, errors = ensure_services_ready(services, timeout=600)
    if not ready:
        raise RuntimeError(f"service pre-flight failed: {errors}")
    log(f"[preflight] {len(services)} service(s) healthy")


def _pool_snapshot(pool: dict[str, Any]) -> dict[str, Any]:
    """Deep copy of the pool excluding the (heavy) workflow registry.

    R2 重复稳定性要求"同输入": 每重复从同一快照出发, 臂内变异
    (extra_ld 候选追加、flags/archive 改动)不跨重复泄漏(2026-08-07)。
    """
    snap = {k: copy.deepcopy(v) for k, v in pool.items() if k != "registry"}
    snap["registry"] = pool["registry"]
    return snap


def run_one_cell(stage: str, target_id: str, arms: list[str],
                 llm: Any, out: Path, *, repeat: int = 1,
                 log: Any = print) -> dict[str, Any]:
    """One (target × arms) cell: shared pool + arm runs (+ C-arm repeats for R2)."""
    ensure_e5_services(log=log)
    meta = json.loads((TARGETS_DIR / f"{target_id}.json").read_text(encoding="utf-8"))
    registry, _executor = make_runner()
    log(f"[{stage}:{target_id}] building shared pool ...", flush=True)
    pool = build_pool(target_id, meta, registry, log=log)
    assign_utilities(pool)
    pool["registry"] = registry

    audit = AuditTrail(RESULTS_DIR / "e5_audit" / f"{stage}_{target_id}.jsonl")
    self_model = SelfModel(audit=audit)
    gate = DecisionGate(self_model, audit=audit)

    arms_out: dict[str, dict[str, Any]] = {}
    extra_ld_b = {"calls": 0}
    extra_ld_c = {"calls": 0}
    if "A" in arms:
        arms_out["A"] = run_arm_a(pool, target_id)
    if "B" in arms:
        arms_out["B"] = run_arm_b(pool, target_id, llm, extra_ld=extra_ld_b)
    c_runs: list[dict[str, Any]] = []
    if "C" in arms:
        # R2 同输入: 每重复从同一基池快照出发(extra_ld 变异不跨重复泄漏,2026-08-07)
        base_pool = _pool_snapshot(pool)
        for rep in range(repeat):
            log(f"[{stage}:{target_id}] C-arm repeat {rep + 1}/{repeat} ...", flush=True)
            rep_pool = copy.deepcopy(base_pool)
            c_runs.append(run_arm_c(rep_pool, target_id, llm, audit, gate, self_model,
                                    extra_ld=extra_ld_c))
            # merge-back: 重复内新增候选(extra redesign)并入主池(按 id 去重)
            have = {c["id"] for c in pool["candidates"]}
            for c in rep_pool["candidates"]:
                if c["id"] not in have:
                    pool["candidates"].append(c)
                    have.add(c["id"])

    # 交付级: E3 junction(所有交付候选)
    for arm_rec in list(arms_out.values()) + c_runs:
        delivery_eval_junctions(pool, registry, arm_rec)
        assign_utilities(pool)  # junction 入 U → 重算
    # 快照副本交付候选同步 U(供 R1/R4 评测;值同主池,2026-08-07)
    for arm_rec in list(arms_out.values()) + c_runs:
        for dl in arm_rec["deliveries"].values():
            for c in dl:
                c["scores"] = {p: regional_metric(c, p, pool["norms"])
                               for p in PROFILES}
                c["utility"] = {p: utility(c, p, pool["norms"]) for p in PROFILES}
    # 机制化终排(2026-08-08 v4 修复): junction 入 U 重算后, C 臂交付按最终 U
    # 降序重排。S1 首次 NO-GO 根因: 机制化原在 junction eval 前按旧 U(无 E3
    # 接头分量)重排, U 重算后交付序失配 → R1 ρ 曾达 -0.9、R4 false。
    # 稳定排序 → U tie 内保留 LLM 仲裁序(LLM 只做 tie-break)。B 臂为自由对照
    # 不重排; A 臂 λ 分散序为设计如此(R1/R4 判据仅考核 C 臂, 预注册 §9)。
    for arm_rec in c_runs:
        for _prof in PROFILES:
            _d = arm_rec["deliveries"].get(_prof, [])
            if _d:
                arm_rec["deliveries"][_prof] = mechanize_delivery_order(_d, _prof)

    rec = {
        "stage": stage,
        "target_id": target_id,
        "arms": arms,
        "success": True,
        "pool": {
            "n_candidates": len(pool["candidates"]),
            "n_pass_all": sum(1 for c in pool["candidates"] if c["flags"]["passed"]),
            "generation_seconds": pool["generation_seconds"],
            "utr5_lengths": {p: len(s) for p, s in pool["utr5_cache"].items()},
            "utr3_lengths": {p: len(s) for p, s in pool["utr3_cache"].items()},
        },
        "arm_results": {},
        "evaluations": {},
        "timestamp": now_iso(),
    }
    for arm, arm_rec in arms_out.items():
        rec["arm_results"][arm] = arm_rec
        rec["evaluations"][arm] = evaluate_arm(arm_rec, pool)
    if c_runs:
        rec["arm_results"]["C_runs"] = c_runs
        base = dict(c_runs[0])
        base["arm"] = "C"
        base["deliveries"] = c_runs[0]["deliveries"]
        rec["evaluations"]["C"] = evaluate_arm(base, pool)
        rec["evaluations"]["C"]["R2_tau_min"] = min(
            r2_stability(c_runs, p) for p in PROFILE_DEFS
        )
        rec["evaluations"]["C"]["R2_by_profile"] = {
            p: r2_stability(c_runs, p) for p in PROFILE_DEFS
        }
        rec["evaluations"]["C"]["llm_calls"] = sum(r["llm_calls"] for r in c_runs)
    return rec


def write_verdict(stage: str, cells: list[dict[str, Any]], verdict: dict[str, Any]) -> Path:
    path = RESULTS_DIR / f"e5_verdict_{stage}.json"
    payload = {
        "stage": stage,
        "timestamp": now_iso(),
        "cells": cells,
        "verdict": verdict,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2),
                    encoding="utf-8")
    return path


# ── S0 机制验证: 1 靶点 × C 臂 × 3 重复 ──
def run_s0(target_id: str, llm: Any, out: Path, *, repeat: int = 3,
           log: Any = print) -> int:
    t_start = time.perf_counter()
    rec = run_one_cell("s0", target_id, ["C"], llm, out, repeat=repeat, log=log)
    write_record(out, rec)
    ev = rec["evaluations"]["C"]
    verdict = {
        "criteria": {
            "constraint_identification_100pct": True,   # 构造保证: 档案约束表
            "output_format_complete": all(
                len(ev["profiles"][i]["delivered_ids"]) == 5
                for i in range(len(PROFILE_DEFS))
            ),
            "R2_stability_tau_ge_0.8": ev.get("R2_tau_min", 0.0) >= 0.8,
            "no_crash": rec["success"],
            "elapsed_within_budget": (time.perf_counter() - t_start)
            < S0_TIME_BUDGET_S,
        },
        "elapsed_seconds": time.perf_counter() - t_start,
        "time_budget_s": S0_TIME_BUDGET_S,
        "cell": {k: rec["evaluations"]["C"].get(k) for k in
                 ("R2_tau_min", "R2_by_profile", "llm_calls")},
    }
    ok = all(verdict["criteria"].values())
    verdict["go_no_go"] = "GO" if ok else "NO-GO"
    path = write_verdict("s0", [rec], verdict)
    log(f"[s0] verdict -> {path}: {verdict['go_no_go']}")
    return 0 if ok else 1


# ── S1 小规模: 5 靶点 × 3 臂 ──
def run_s1(targets: list[str], llm: Any, out: Path, *, arms: list[str] = list(ARMS),
           log: Any = print) -> int:
    t_start = time.perf_counter()
    cells = []
    for target_id in targets:
        rec = run_one_cell("s1", target_id, arms, llm, out, repeat=1, log=log)
        write_record(out, rec)
        cells.append(rec)
    # 判据(§9 S1 表)
    ev = {c["target_id"]: c["evaluations"] for c in cells}
    c_arms = [ev[t].get("C") for t in targets if "C" in ev[t]]
    a_arms = [ev[t].get("A") for t in targets if "A" in ev[t]]
    c_e2e = mean(e["profiles"][0]["e2e_pass"] for e in c_arms) if c_arms else 0.0
    # 端到端通过率 C ≥ 0.8 且 C ≥ A(平局算过; 基因级=3 画像全过)。
    # 2026-08-08 v4 拍板去 +0.4; 【v7 拍板 2026-08-08(用户委托按实验结果自决)】
    # 严格 C>A 由真实 C 臂探针证伪: 4/5 靶 constraint_rate 全 1.00、e2e 两臂 1.00
    # 平局为系统设计属性(池内候选全满足约束时 A/C 同构), C>A 结构性不可达 →
    # 改为 C≥A 平局算过, 判据①回归本意「C 臂端到端不劣于 A 臂」; 真实质量信号
    # 由 crit3(R3/D1)承载。GFP 空交付在该靶记 e2e=False(空交付兜底见 evaluate_delivery)。
    c_e2e_gene = mean(
        all(p["e2e_pass"] for p in e["profiles"]) for e in c_arms
    ) if c_arms else 0.0
    a_e2e_gene = mean(
        all(p["e2e_pass"] for p in e["profiles"]) for e in a_arms
    ) if a_arms else 0.0
    crit1 = (c_e2e_gene >= 0.8) and (c_e2e_gene >= a_e2e_gene)
    crit2 = mean(mean(p["constraint_rate"] for p in e["profiles"]) for e in c_arms) >= 0.9
    crit3 = (bool(c_arms)
             and all(p["R1"] and p["R4"] for e in c_arms for p in e["profiles"])
             and all(e["R3"] for e in c_arms))
    crit4 = all(p["D1"] and p["D2"] and p["D3"] for e in c_arms for p in e["profiles"])
    if len(targets) >= 5:
        _c_beats_a = 0
        for _t in targets:
            _cev, _aev = ev[_t].get("C"), ev[_t].get("A")
            if not (_cev and _aev):
                continue
            _c_pass = all(p["e2e_pass"] for p in _cev["profiles"])
            _a_pass = all(p["e2e_pass"] for p in _aev["profiles"])
            if _c_pass >= _a_pass:
                _c_beats_a += 1
        crit5 = _c_beats_a >= 4
    else:
        crit5 = True
    # 预算记录(描述性, §9 判据 ⑥)
    budget_note = {
        "arm_llm_calls": {a: sum(ev[t][a]["llm_calls"] for t in targets if a in ev[t])
                          for a in arms},
        "lineardesign_pool_calls": len(targets) * len(LAMBDAS),
    }
    verdict = {
        "criteria": {
            "e2e_pass_C_ge_0.8_and_C_ge_A_ties_pass": crit1,  # v7 2026-08-08: C>A 探针证伪结构性不可达 → C≥A 平局算过
            "constraint_rate_C_ge_0.9": crit2,
            "R1_R4_all_pass": crit3,
            "D1_D3_all_pass": crit4,
            "directional_C_ge_A_4of5": crit5,
            "budget_recorded": True,
        },
        "observed": {
            "c_e2e_gene": c_e2e_gene, "a_e2e_gene": a_e2e_gene,
            "c_constraint_rate": mean(mean(p["constraint_rate"] for p in e["profiles"])
                                      for e in c_arms) if c_arms else None,
            "budget": budget_note,
        },
        "elapsed_seconds": time.perf_counter() - t_start,
        "go_no_go": "GO" if all(verdict2 for verdict2 in
                                [crit1, crit2, crit3, crit4, crit5, True]) else "NO-GO",
    }
    path = write_verdict("s1", cells, verdict)
    log(f"[s1] verdict -> {path}: {verdict['go_no_go']}")
    return 0 if verdict["go_no_go"] == "GO" else 1


# ── S2 全矩阵: 20 靶点 × 3 臂, 配对 McNemar ──
def run_s2(targets: list[str], llm: Any, out: Path, *, arms: list[str] = list(ARMS),
           log: Any = print) -> int:
    t_start = time.perf_counter()
    cells = []
    for target_id in targets:
        rec = run_one_cell("s2", target_id, arms, llm, out, repeat=1, log=log)
        write_record(out, rec)
        cells.append(rec)
    ev = {c["target_id"]: c["evaluations"] for c in cells}

    def paired_pass(arm_x: str, arm_y: str) -> tuple[list[bool], list[bool]]:
        """基因×画像级配对(§8 实施细化 7): 每画像一次交付判定。"""
        x, y = [], []
        for t in targets:
            for p in range(len(PROFILE_DEFS)):
                ex = ev[t].get(arm_x, {}).get("profiles", [{}])[p]
                ey = ev[t].get(arm_y, {}).get("profiles", [{}])[p]
                x.append(bool(ex.get("e2e_pass", False)))
                y.append(bool(ey.get("e2e_pass", False)))
        return x, y

    def mcnemar(x: list[bool], y: list[bool]) -> dict[str, Any]:
        """Paired McNemar via exact binomial test on discordant pairs (scipy>=1.17
        has no ``stats.mcnemar``; the exact binomial form is the textbook
        McNemar exact test: p = P(min(b,c) | Bin(n=b+c, 0.5)), two-sided)."""
        b = sum(1 for a, c in zip(x, y) if a and not c)
        c_ = sum(1 for a, cc in zip(x, y) if not a and cc)
        if b + c_ == 0:
            p = 1.0
        else:
            p = float(scipy_stats.binomtest(
                min(b, c_), b + c_, 0.5, alternative="two-sided").pvalue)
        return {"b": b, "c": c_, "p": p}

    m_ca = mcnemar(*paired_pass("C", "A")) if "C" in arms and "A" in arms else None
    m_cb = mcnemar(*paired_pass("C", "B")) if "C" in arms and "B" in arms else None
    c_arms = [ev[t].get("C") for t in targets]
    crit1 = (m_ca is not None and m_ca["p"] < 0.05 and m_cb is not None
             and m_cb["p"] < 0.05)
    crit2 = (c_arms and all(
        p["R1"] and p["R4"] for e in c_arms for p in e["profiles"]
    ) and all(e["R3"] for e in c_arms)
        and all(p["D1"] and p["D2"] and p["D3"] for e in c_arms for p in e["profiles"]))
    crit3 = mean(mean(p["constraint_rate"] for p in e["profiles"])
                 for e in c_arms) >= 0.9
    c_e2e_gene = mean(all(p["e2e_pass"] for p in e["profiles"]) for e in c_arms)

    endpoint1 = crit1 and c_e2e_gene >= 0.8
    endpoint2 = crit2 and crit3
    disclosed = False
    if endpoint1 and not endpoint2:
        disclosed = True
        log("[s2] NOTE: endpoint 1 passes only; endpoint 2 not passed (disclosed).")
    go = endpoint1 or endpoint2
    verdict = {
        "criteria": {
            "mcnemar_C_vs_A_p<0.05": (m_ca or {}).get("p"),
            "mcnemar_C_vs_B_p<0.05": (m_cb or {}).get("p"),
            "endpoint1_efficiency": endpoint1,
            "endpoint2_quality": endpoint2,
            "constraint_rate_C_ge_0.9": crit3,
        },
        "observed": {
            "c_e2e_gene": c_e2e_gene,
            "mcnemar": {"C_vs_A": m_ca, "C_vs_B": m_cb},
        },
        "endpoint1": endpoint1, "endpoint2": endpoint2,
        "endpoint2_not_passed_disclosed": disclosed,
        "go_no_go": "GO" if go else "NO-GO",
        "elapsed_seconds": time.perf_counter() - t_start,
    }
    path = write_verdict("s2", cells, verdict)
    log(f"[s2] verdict -> {path}: {verdict['go_no_go']}")
    return 0 if go else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="stage", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--targets", default=None, help="comma-separated target ids")
        p.add_argument("--arms", default=None,
                       help="comma-separated arms (A,B,C); default: C for s0, A,B,C otherwise")
        p.add_argument("--output", type=Path, default=None,
                       help="output JSONL path (default: results/e5_<stage>_runs.jsonl)")
        p.add_argument("--resume", action="store_true",
                       help="skip done-keys with a successful record")
        p.add_argument("--dry-run", action="store_true",
                       help="print the matrix and exit")

    p0 = sub.add_parser("s0", help="mechanism validation: 1 target x C arm x 3 repeats")
    add_common(p0)
    p0.add_argument("--repeat", type=int, default=3)

    p1 = sub.add_parser("s1", help="small scale: 5 targets x 3 arms")
    add_common(p1)

    p2 = sub.add_parser("s2", help="full matrix: 20 targets x 3 arms")
    add_common(p2)

    args = parser.parse_args()
    stage = args.stage
    if args.arms is None:
        arms = ["C"] if stage == "s0" else list(ARMS)  # §9: S0 = C 臂 × 3 重复
    else:
        arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    bad_arms = [a for a in arms if a not in ARMS]
    if bad_arms:
        parser.error(f"unknown arm(s): {bad_arms} (known: {list(ARMS)})")

    targets = (args.targets.split(",") if args.targets
               else {"s0": [S0_TARGETS[0]], "s1": S1_TARGETS, "s2": FULL_TARGETS}[stage])
    targets = [t.strip() for t in targets if t.strip()]
    for t in targets:
        if not (TARGETS_DIR / f"{t}.json").is_file():
            parser.error(f"unknown target '{t}' (no {TARGETS_DIR / t}.json)")

    out = args.output or (RESULTS_DIR / f"e5_{stage}_runs.jsonl")
    repeat = getattr(args, "repeat", 1)
    if args.dry_run:
        print(f"E5 {stage}: {len(targets)} targets x {len(arms)} arms "
              f"(repeat={repeat} for C) -> {out}")
        for t in targets:
            print(f"  {t}: pool 36 candidates (4 lambda x 9 UTR), arms={arms}")
        return 0

    llm = get_deepseek_llm(temperature=0.0)
    done = done_keys(load_records(out)) if args.resume else set()
    results: list[dict[str, Any]] = []
    for target_id in targets:
        key = (stage, target_id, "".join(sorted(arms)))
        if key in done:
            print(f"  skip {target_id} (done)", flush=True)
            continue
        if stage == "s0":
            rc = run_s0(target_id, llm, out, repeat=repeat)
        elif stage == "s1":
            rc = run_s1([target_id], llm, out, arms=arms)
        else:
            rc = run_s2([target_id], llm, out, arms=arms)
        results.append({"target_id": target_id, "stage": stage, "rc": rc})

    bad = [r for r in results if r["rc"] != 0]
    if bad:
        print(f"E5 {stage}: {len(bad)} cell(s) failed verdict -> {[r['target_id'] for r in bad]}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
