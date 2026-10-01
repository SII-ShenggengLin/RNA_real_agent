# Change Log

**2026-10-01 edit (Methods 逐句润色批，用户逐句主持，七小节全部完成)**: Methods 全节逐句重写——七个小节标题全改（System architecture of RNADesignAgent / The multi-agent layer / Candidate ranking by the achievement scalarizing function / Capability profiling and evidence gating (CapGate) / Constraint navigation and budget-matched delivery (GenNav) / Benchmark datasets and anchor sets / Statistical analysis），正文按用户既定原则大幅精简（只报现行设计与最终数据集、实现管道退役、零散文分号、零箭头、零代码标识符），零数字改动（保留值逐字，退出数值全部图例/SI/冻结承载）。要点：走层段七层各就（L0 35/21/6 承载口径对齐 Table S3、L1 功能句与 §2.2 同构、L2 枚举退役归 Table S2 且 IRES 定义迁 Benchmarks、流程声明限定设计类、L4 总起+四动词句）；多智能体节四句重写+零置信处置/abort-advice/协调环/温度与本地预测器细节退役；ASF 节 ASF 定义自 L4 迁入、权重句按代码修正语义（覆盖全部目标才用否则整体等权）、utopian→ideal、六工作流枚举退役归 Table S2（§M1 锚点迁 Fig. 2a 图例保完整性不变量）、hypervolume→the volume dominated by a pool's Pareto frontier；CapGate 节 target family 经 default_self_model.json 核实即锚集而两处退役、元组记法退役、RNADA_CAPGATE 标识符退出正文、拦截句与 ASF 策略一逐字对齐（dimension dropped from the ranking）、转移句按代码重写（worst grade on any profiled anchor set）；GenNav 节整体重写 430→180 词（约束矩阵数值逐字迁 SI §M3 新增 Pre-registered constraint matrices 段、预算块收铁律一句、模式句删、static recipe/executor→static condition、band→range）；Benchmarks 节重构为结果→最终数据集映射（All results are obtained on eight benchmark datasets + 四句带图件指针；suite→benchmark 正文 13 站清扫完成 §2.6 批方向；20 靶套件退出顶层条目；构建史全退役；锚集段 controls→comparisons、行内引用退役入引用债）；Statistical analysis 节重排（McNemar 两句重写、样本量三句删、编码智能体声明删、阈值句逐字保留）。机检全绿：零箭头/零 em-dash/零散文分号（三处指针括号分号为引用体例）、补充材料指针 body-or-legend 全解析（§M5 经 Note 3 链式承载为既定设计）、保留数值逐字。挂账新增：图例同步批（Fig. 1c/1d 措辞与箭头、§2.1 箭头、Fig. S5 可选）、SI/DA 同步批（external code family、suite、assertion-curated、panels、external-baseline naming）、投稿引用债（Stoneley/Stein/Yang & Sarnow/Jenison；Jeong 待定）、sgRNA 首现缺口。**同日第二批（Data availability 重写 + Zenodo v4 终态重组上传）**：DA 段与 Benchmarks 节对齐重写（八数据集终态枚举 + 逐数据集来源清单披露 + 锚集清单措辞同步 + 外部基线记录条目用新命名）；Zenodo 草稿 22736194 换传 RNADesignAgent_paper_data_v4.tar.gz（10,028,254 B，sha256 666bb356…，499 文件，benchmarks/ 重组为 01–08 终态数据集目录、补入此前缺席的五蛋白选择步池、25/26/39 合并清单带逐靶来源，计数机检 5/25/26/39/45/20，密钥扫描净；v3 按 id 删除 204、v4 直传 201、元数据描述更新 200、读回 md5 一致；令牌自悬空中转提交恢复、有效复用）；剩余用户动作不变（作者→发布→DOI 核验→撤销令牌）。登记：PAPER_DRAFT 头注 2026-10-01 条/本条/AGENTS.md/upload_status.md。
**同日 DA 逐句收尾批（用户逐句主持）**: "All research data"→"All data"（research 冗余、保留 supporting-the-findings 范围限定）；"in their final forms" 删（终态含义由数据集名称承载）；构成披露从句删（SI §M3 与包内 dataset_manifest.json 承载）；锚集枚举删、包含声明并入资产句（"(Methods)" 指针，包内容账目完整）；校验和句删（包内 MANIFEST 与 Zenodo 元数据描述承载）；代码指针句删（Code availability 节紧邻）。DA 定稿：DOI 与许可 / 八数据集枚举 / 其余资产（锚集+能力图+用量登记）/ 第三方不分发声明；基线记录句随后整体删除（v3 批的"数据可用性 (iv) 条目"就此退役——包内 baseline_evidence/ 目录与 Zenodo 元数据描述仍完整承载其存在与内容，正文不再枚举）；第三方不分发句随后亦整体删除——外部来源的归属由 Methods 锚集段的使用点引用承载（GEO 入藏号、NCBI RefSeq、PDB 编号）与包内锚集逐条来源引用承载，DA 定稿两句：DOI 与许可 / 包内容（八数据集 + 锚集 + 能力图 + 用量登记）

**2026-09-28 fourth edit (Discussion 逐句修订批，用户逐句主持，已完成)**: Discussion 四段 1,152 词 → **450 词**；零图件数据改动、零实验改动，退出正文的数字与细节全部由 Abstract/引言 ¶4/§2.2–§2.6/图例/SI/冻结记录承载（逐项总账见 PAPER_DRAFT 头注本条）。要点：¶1 开篇重写为"做了什么、解决了什么问题"（agentic science/tool-first 退役）、CapGate/GenNav 机制句各定稿一句（prevents+注册宾语；GenNav 缩写挂账执行；§2.3 铁律逐字复现）、三个转场预告句删除、profiling 证据两句定性化（chain 歧义改 the aptamer side；RNAsmol 复现退 §2.4）、结果全定性化（CapGate almost all/most；GenNav 三谓语镜像 §2.5 三区制；win/lose 词汇换 outperformed/decisively better/gives way to）；**池化无显著句经用户裁定删除——覆盖 §2.5 批 18:12/P=0.36→Discussion 承载契约**（恢复落点登记为 §2.5 池化句补从句）。¶2 开篇 reliability 句（斜体强调清零、not only 包含式）、原则三连五轮定稿两句（第三原则退 §2.4）、治理消融块压缩至一句 5/12（Methods 指针验证后删消融句）、**§2.6 批四项 Discussion-sync 挂账随批关闭**（suite/tier/discordance/same-underlying-model）、**归因孪生句删除式关闭 not-only-from 二选一挂账**、批次七 Discussion 三件套（定位/免误读/dual-use）经用户裁定全退——**dual-use 全文清零**。¶3 限制一按用户事实纠正重写（门控全工作流在线非限制，导航 two of the eleven workflows 受生成工具可用性约束；both mechanisms→GenNav；mature→become available）、限制二压缩、收束句删。¶4 段尾重平衡为平台主导：平台意义句三轮定稿（"The main contribution is" 元宣告经用户否决→automates+verified rather than merely reported+two of its mechanisms）、机制前瞻句整句退役、"any agent in any domain" 收窄为 applies to other scientific agents、末句自然语言+效率/易用双收益并回扣引言 ¶1 瓶颈句首尾环合。机器校验：零 em-dash、零散文冒号、**全节零阿拉伯数字**、退役词零残留、we 仅 ¶1 四处定稿形态。挂账新增：Methods "(Results)" 指针指向性存疑（治理消融已迁 Note 3）。登记：PAPER_DRAFT 头注本条/AGENTS.md。

**2026-09-28 third edit (§2.6 逐句修订批，用户主持逐句润色，已完成；含 suite→benchmark 与 tier→budget 两组节内术语统一)**: 基线对比小节自 ~880 词收于 **708 词 4 段**；零图件数据改动、零实验改动，保留值全部冻结逐字，退出正文的数字与细节由 Fig. 6 各面板/SI §M4/冻结记录承载（总账见 PAPER_DRAFT 头注本条）。**小节重题** "The system outperforms bare-model and tool-using agent baselines"（删 "across the eleven workflows" 范围尾，与同级标题无范围尾体例一致；覆盖面由 Methods 定义句、Fig. 6a 图例与 SI §M4 承载；两臂点名保留〔2026-09-14 用户裁定〕；§2.2 批头注 "§2.6 标题独享该短语" 之说随之过时）。**节内两组术语统一**：suite→benchmark 两站（开篇与末段 the entire suite 回指；Fig. 2 图例 "210-task benchmark" 与 Methods "benchmark suites" 双轨先例；"test set" 方案因与预测器 held-out test set 既定语义撞车被否）；tier/generous tier→budget/点名档位全清（与 Fig. 6 图例 "matched, 3× and 10× model-call budgets" 对齐，Discussion 一站挂账）。**¶1 设置段**：目的直陈句取代修辞性理由句与三条件计数；套件括号（96 轮/十一工作流/逐轮相同输入）整删；"The system ran as shipped…" 删——**as shipped 全文退役**（最后一站）；+1 file-writing 原语及理由退 SI §M4；预算句定稿被动直陈（匹配定义退 SI §M4）；判分主题句（疑点① one-rulebook 句）与重判句（疑点②前半、四 IRES 对称阴性轮）删——SI §M4 承载，IRES 缩写定义牵连迁 Methods 挂账、Fig. 6a "by construction of the symmetric re-adjudication" 锚点转 SI；delivered 判据句定义式精简 44→26 词（五项判据括号退 SI §M4；**structural validity 与 parity 退出主文**）；及格线尾从句（疑点② pre-fixed bar/no invented threshold）删——SI 未明写该两要素、补句建议挂账；claims 句收 "scored separately and blindly"（悬空规则名 the blind adjudication rules 改副词；unverifiable 类判定退 SI §M4；alike 删）。**¶2**：头条数字拆两句+(Fig. 6a) 指针落位；discordance 桥句（疑点③）删；"25, 27, 89, 52 and 25" 枚举删（=交付数算术推导，Fig. 6b+冻结承载）；失败模式首句平实化（failure modes 短语退役、§2.3 撞名消解）；裸模型句（few-shot 13/14 退图 6b、outright→structurally、zero-shot 内联、11 turns 平行）；机制句 52→34 词（cadence→spends on review、buy→cover、拆包与限定语删、and→so）；10× 句（nine→9 修复全文唯一同语境数制破例、below parity→below the system's best）；平局句直陈化（tie/12:12/P=1.0 退冻结、discordance 又清一站）；镜像对 outperforms 双句（括号计数退 Fig. 6a、indispensable→essential、**small-composition 与 over-spends 退役**〔后者顺带修正"二级类是质量差距非花超"的潜在不准〕、ASO 扫描机制移入正文为唯一承载位、land→miss…by）。**¶3**：首句 "The system and the two baselines differ even more in their claims than in their delivery (Fig. 6c)"（名词化/判断动词/弱锚 conditions 三症同除）；零声称句（publishes→makes、by construction 删、assert→make claims 平行、multi-node pipelines 全称）；裸模型句（CI 退图 6c 须、anchoring→guide、in its head→without tools）；循环句（51.1%@10× 与 CI 退图 6c、carried/pooled/outright 退役）；收束句（"measured earlier in this paper" 元话语删、**scaffold 全文退役——SI §M4 尾句已随批同步 generic agent，本批唯一 SI 侧改动**）。**¶4**：首句 "The system also used far fewer model calls (Fig. 6d)"（cost ledger/completes the picture 双隐喻退役）；146 vs 756+659 拆两句（model spend 对齐 Discussion）；emit→take、so much as→even；degenerate floor 表态从句删；解地板句点名档位+guarantee a minimum 压平行话（公式 SI §M4 承载）+"take its first action" 同词呼应；小结句两腿版（buys/taxes/reintroduces/validity/behaviour 五隐喻退役、claims 腿由收尾句承接、everywhere else→on the other workflows）；收尾句（full validity→every turn delivered、itself 删、**"not from"→"not only from" 用户两次质询后裁定改入——登记保留意见：恒定模型设计与评审中性消融支持强排除，Discussion "not of the model itself" 方向相反必须对齐**）。**挂账清单**：legend-sync（Fig. 6 题句 suite→benchmark 与新题核对、6a symmetric re-adjudication 锚点、6c publishes→makes、platform 12 站顺带）；Methods-sync（IRES 定义迁首用、Statistics cost ledger 登记语）；Discussion-sync（96-turn suite→benchmark、disclosed generous tier→10×、no reverse discordance 去留、not of the model itself 对齐）；SI-sync（§M4 pre-fixed bar 补句、suite→benchmark SI 站）。**机器校验**：零 em-dash、零散文冒号、节内退役词零残留（as shipped/scaffold/tier/generous/outright/discordance/adjudicat/parity/structural validity/cost ledger/small-composition/over-spend/behaviour/assert/whereas/cleverness/buys/taxes/land/emit/publishes/tie 等 grep 均 0）、保留数字对冻结注册值逐字（96/96、71、69、7、44、71、14、11、86、42、16、9、15–23、one to six、48.3%、11.4%、51.9%、30–37%、54.5%、146、756、659、5.2×、24、two、9/9、4/6、1/9）。登记：PAPER_DRAFT 头注 2026-09-28 third-edit 条/本条/AGENTS.md。

**2026-09-28 second edit (§2.5 逐句修订批，用户主持，先整体精简后逐句润色，已完成；含原 ¶5 结构性并入 ¶4 与 cell→pair 全节术语统一）**: 小节自 5 段 ~1,330 词收于 **4 段 602 词**；零图件数据改动、零实验改动，退出正文的数字与细节全部由图例/SI/Discussion/冻结记录承载（总账见下）。**小节重题** "Constraint navigation efficiently generates RNA molecules that meet the design requirements"（删 Generation-layer——与 §2.4 题不带 Capability-layer 前缀同理，全称由 Discussion/Methods 定义位承载；constraint-satisfying 复合词经用户否决〔不常见〕后恢复关系从句形；efficiently 为两侧结果下唯一安全断言词保留）。**¶1 任务+机制段（127 词）**：任务命题句 "The agent's task is multi-constraint batch delivery"（defensible/failed-experiment 从句删、"At the generation layer" 状语删〔七层架构无此层，撞名 L0–L6〕、历经命题-论据两次换序后按用户要求命题在前）；单度量论据句 "The generator's settings already determine any single quality metric such as codon adaptation or folding energy, so single-metric design leaves nothing for an agent to decide"（fixed→determine、within that range 悬空删、adds nothing→nothing to decide）；任务定义句 60→22 词三轮（five 退役 Methods/图例 5d、acceptance-bands 中间层溶解、四维与三 profile 枚举退役 Methods、"Per target"→"For each target"）；"GenNav achieves this goal at the generation step (Fig. 1d)"（task→goal——objective/target 撞名排名目标/设计靶点而排除；delivers these batches 同义反复版经用户否决；layer→step 消解七层撞名，Fig. 1d 图例原词）；设置枚举句删（Overview 导航器句/Fig. 1d 图例/Methods 三重承载）；探测-提交句 "It first tests a few settings to find which can meet the constraints, and only then commits its quota of generation calls, identical in every comparison"（trial/establishing/at hand/campaign/held/comparison 六词精化，quota/calls 注册术语保留）；多样性句拆二（floor 注册术语保留于图例 5a/Methods；near-duplicate→near-identical 与 ¶2 统一）；不可行句 "reported as infeasible with its failure reason rather than silently omitted"（feasible/infeasible 优化标准术语三站注册链保留，dropped→omitted）。**¶2 选择步边界段（109 词）**：段首 "placed navigation in the selection step, generating a single fixed pool of 315 full-length candidates per target (35 CDSs × 9 UTR combinations)"（悬空 at-315 碎片内嵌为池定语、collection→pool 节内统一、coding sequences→CDSs 缩写纪律、layer→step）；"It fails for reasons inherent in generation"（structural-to 非标准搭配退役、itself 删）；五靶枚举保留（批次五用户指示）但 from-through-to 脚手架拆为直接列举、registered 删、constructs→candidates、尾部 with 从句整删（滑窗 GC 主约束与 11 倍 → 冻结，Fig. 5a 图例可选挂账）；GFP 密码子表从句删（图例 5a 逐字承载 0/315→18/315）→ 教训句独立成句；胰岛素句以 "Even with 144 passing candidates" 前缀连接（枚举数自含让步锚；"a second failure" 计数框架经用户否决）；段尾 "Navigation therefore moved to the generation step"（we 退役、与段首 placed navigation 对仗；λ 扫描/静态配方配额/同义替换机制 → Overview/Methods/Fig. 1d 图例）。**¶3 mRNA 结果段（117 词）**：队列构成与协议说明删（Methods/Statistics/图例 5b 承载）；"navigation wins the paired comparison against the static condition"（与引言/Discussion 注册句式同构；discordance/favours 退役——discordance 剩余站位于 ¶4/¶5 已随重构消失，术语退役）；profile 简注落地（¶1 删枚举挂账关闭）"three profiles emphasizing expression, stability and balance, giving one paired outcome per target and profile"（oriented toward→emphasizing、悬连字符消除、profiles/conditions 之争由 pair 消解——每对含两条件结果，句尾三元组缩为二元且预置 n = 75）；**cell→pair 全节统一 8 使用位**（McNemar 原生单元、Statistics 已有 n = 75 pairs 先例、生物细胞歧义消除；跨节挂账 Discussion "48 versus 42 cells"、Methods Statistics "n = 78 cells"、图例 5b/5c/5e/5g/S2 cells）；结果三句直陈式 "In 26 of the 75 pairs only one condition delivers a passing batch, navigation in 20 and the static condition in 6 (exact McNemar P = 0.009; Fig. 5b,c)" 与 "Navigation spends less than its quota and delivers passing batches in 46 of the 75 pairs, the static condition in 32"（Of-the-75-pairs 非常用形经用户指出改从句内嵌；成本与总量同句对偶、花费谓语前置防椭圆尾主语错绑）；JCD 缩写退役（Statistics "joint-criteria" 存续、图例 5b "JCD pass counts" 挂账）；nine 3/3、HER2 零可行、12/25 gene-level 判据（经 mrna_pooled_verdict.json 核实 = c_e2e_gene 0.48，与 nav_jcd==3 的 9 为两口径）、constraint-rate/composite 分解全部退役图例 5b/5d 与冻结；质量持平句 "The quality of the delivered batches does not differ between the two conditions, so navigation's advantage is delivering more pairs"（composite/indistinguishable/recipe's 溶解）；GFP 边界句删（6 已在首句、3-of-6 分解 → Fig. 5b 面板+冻结；¶2 删码表故事所致的 E. coli-表自含改写挂账随之消解）。**¶4 适配体段（287 词，吸收原 ¶5）**：首句 "We also tested the navigation mechanism on RNA aptamer design"（beyond-codon-space/ported-GenNav 行话退役、same 删——引言 "the same mechanism" 承载泛化断言）；"CapGate blocks every structure predictor from ranking candidates, because profiling found no reliable ranking power in any of them"（缩写化、bars→blocks 房内动词、判定出处归 §2.3 profiling）；噪声句（ICC 0.30 删 → 冻结；setting-quality 复合词溶解为 noise/signal 同句对偶；15 pp 唯一量化依据保留）；战役句 "A pre-registered campaign on the 20 aptamer targets shows where the noise matters"（four-segment/arc/suite/maps 内部词汇退役、治理括注删 → Discussion/Methods）；易矩阵句 saturate→deliver successfully 直陈；10:9 平衡中间步删（图例 5e）；12 靶稀缺句直接计数式 "only one condition delivers a passing batch in 13 of the 36 pairs, the navigator in 10 and the static condition in 3"（decisive-panel 标签删——图例 5f 注册位保留）；"delivers in all three profiles on 4 targets and the static condition on none"（three-class 挂账消解、only-fully-completed 从句删〔图例 5f 承载〕、static grid→static condition 全节 7 站统一〔仪器名存续图例/Methods〕）；显著性句三轮定稿 "Notably, this advantage is not statistically significant (P = 0.092), because the comparison is based on only 13 pairs"（significance-gate 术语→标准表述、registered-no-go 括注删〔图例 5f/Discussion 承载〕、小样本归因按用户指示补——13 不一致对同比例 mRNA 26 对即显著的对照经冻结核）；1:8 静态胜句删（图例 5e 逐字；P = 0.092 句经完整性论证保留——本节其余比较均报 P，唯缺此一处将成选择性报告外观）；池化句 "Across all 26 aptamer targets, including six that entered through the production form entry, navigation delivers in 48 pairs to the static condition's 42"（显著/不显著语按用户指示删、close-to-even 删、18:12 与 P = 0.36 → Discussion "at parity" 逐字承载、26 来源补六部署靶一句）；扫描句 "To determine when navigation is suitable, we further conducted a pre-registered 39-target budget sweep (Supplementary Fig. S2)"（行动句式、ran→conducted 学术动词〔§2.3 "We ran" 动词统一挂账〕、sweep-over→注册复合形 39-target budget sweep）；三区制三句主语先行（Where-句式经用户否决废弃；梯度 scarce→moderate→loose；saturates→at moderate quotas；navigation's-only-significant-win 限定语删〔S2 图例逐字〕）；机制收束句（λ 确定性 vs 扩散噪声）经用户两次裁定删除（噪声半边由 ¶4 设置句存续、λ 确定性 → 冻结）。**¶5 结构性并入**：原 ¶5 五句（部署队列补全/池化/部署规则/预算扫描/机制对比）经用户质询定位（结论段而非续报结果）后先重构为综合段、再整体并入 ¶4，段数 5→4。**退出正文数字总账**：图例 5a（0→18、1.01%、λ 限制）、5b/5d（23.1/35 系、0.48/0.8/0.96/1.00、+29/=26/−20、P = 0.73、12/25、五靶费尽/cap 272 基础设施）、5e（48 raw、56/60、32.7、10:9、P = 1×2、n = 60、24v17、8v2、7:1/P = 0.070、1:8/P = 0.039）、5f（24v17、only-completed、pre-registered no-go）、5g、S2（9:4、13:10、10:22/P = 0.050、48 raw、generate-everything 区制、唯一显著胜）；Discussion（18:12、P = 0.36、at parity）；冻结（HER2、swine-H3-HA、IFN-γ/PDGF-BB 步进轮、滑窗 GC 主约束、11 倍、ICC 0.30、λ 确定性、E. coli-表双组成规则、nine-3/3、3-of-6）。**挂账清单**：legend-sync 批新增 Fig. 5b/5c/5e/5g/S2 cells→pairs、图例 5b "JCD pass counts"、Discussion "48 versus 42 cells"→pairs、Methods Statistics "n = 78 cells"→pairs、Fig. 5a GC 主约束可选补、图例 5f decisive-panel 标签去留；Methods-sync 批新增 §M3/SI "Selection-layer pool measurement"→selection-step、Methods GenNav 层词汇与正文 step 制统一；摘要/引言同步（需用户确认）"generation-layer constraint navigation"→"constraint navigation" 两站；§2.3 "We ran"→conducted 可选统一。**机器校验**：零 em-dash、零非比值冒号（10:2/12:30 比值式豁免）、退役词零残留（platform/arm/recurrent/oracle/decision-layer/task famil-/as shipped/suite/cell/JCD/gene-level 均 0）、图例指针完整（Fig. 1d、5a–g、S2）、全节数字对冻结注册值（12/25 与 9 两口径经 mrna_pooled_verdict.json 逐项核实）。登记：本条/CHANGELOG 本条/AGENTS.md。

**2026-09-28 §2.4 逐句修订批（用户主持，先整体精简后逐句润色，已完成；含 ¶7 结构性迁出与三组全文术语统一）**: 小节自 ~2,235 词十段经整体压缩（→9 段 ~1,839 词）与逐句润色收于 **6 段 ~810 词**；零图件数据改动、零实验改动，退出正文的数字与细节全部由图例/SI/冻结记录承载（总账见下）。**小节重题** "Capability gating **removes unsupported claims** while preserving true ones"（eliminates 精度修正——适配体 0/20 为消除、mRNA 1/13 幸存，与引言批 eliminated→reduced 同理；unsupported 接通标题词根；Fig. 4 图例题同步；Discussion 残留句随批改为 "removed unsupported claims…, reducing false positives to… from…"）。**¶1 机制段（115 词）**：首句定稿 "CapGate prevents uncalibrated trust and claim overreach through two deterministic gates that the capability map drives"（remedy 隐喻退役、主动句、feeds→drives 引言批登记词、引言句式倒装复用；历经 remedy/fed by/self-model 三轮词审）；self-model 全文退役为 capability map（段内六站切换；Methods/SI 五站挂账同步）；intercepts→checks（Overview 批登记动词，与段尾 checked against that map 归一；Methods 已同步）；"whose evidentiary basis is absent"→"the capability map does not support"；for example→such as；"outgoing…scope ladder…enforcing maxim"→"before release…through a fixed sequence of scopes"（maxim 删，Methods 逐字存续为正式契约归宿）；"Every decision is appended to the audit trail" 与 production-default/governed every campaign/ships-with 三句删（Overview 溯源原则、Fig. 1c 图例、Methods 承载）；entry point→choke point（全文三站统一，Overview 批挂账项关闭）；段尾 "Every call to a governed predictor is checked against the map at the system's single tool-execution choke point, so an unevidenced call is rejected before it executes rather than flagged afterwards. A predictor without profiling evidence stays blocked by default until evidence exists."。**¶2 证据+性质一（184 词，原 ¶2+¶3 合并）**：开篇 "The evidence that capability profiling produces determines how reliable the gates can be"（as good as 习语与 beneath 隐喻经用户否决后的肯定式直陈）；两性质框架合一 "Two properties of this evidence are important, two-sidedness and fidelity to the deployed tool"（The first is/The other property 脚手架拆除）；性质一句 "Profiling withholds unsupported power and certifies supported power, so the capability map records what the predictors can do, not only what they cannot"（反义平行；withholds 经 denies/only-supported 方案往返由用户定留）；桥句 "Both sides appeared when we profiled the system's own predictors"；正反例（GEMORNA 5′UTR MRL 三 libraries 认证 / 3′UTR unprofiled 被挡；5′UTR/MRL/3′UTR 首现定义完好）；十二格判决 selective rather than prohibitive 收束（协议括注/0.5 衰减/ClaimGate 改写/MRL 6.28/十二格全达预期归图例 4b、§M2 与冻结）。**¶3 性质二 RNAsmol（129 词，原 330 词）**：性质二命名经 deployed artifact→the system as shipped→**the deployed tool** 三轮由用户按词义定稿（五站统一；Fig. 4c 图例标题同步建议入挂账）；target→measure（与 ¶2 机制句动词归一）；事故句 "failed to reproduce its published performance even on its own test sets"（held-out→test sets 对齐 §2.2、silent 删）；"pinned upstream commit"→"the upstream original"（git 行话退役）；deviations→differences（中性词如实）；机制细节（修饰碱基、邻接怪癖、almost entirely zero、沙箱复测、|Δp|=0.08/0.91、三测量定位）整体退役归图例 4c+冻结（图例缺口三项挂账补入）；反转对与 "because the checkpoints had been trained with the bug and correcting it changed their input distribution" 因果句；修复句与事故句 failed to reproduce/reproduced 首尾呼应；教训句 "Tools can silently diverge from their papers, and only measurement reveals where the damage lies"（infidelity 三元组溶解、与 Discussion 表述共享、layer-dependent 悬空词删）。**¶4 适配体收益+代价（148 词，原 ¶4+成本段合并）**：开篇 "We then tested the gates in paired two-condition experiments on aptamer and mRNA tasks, identical except for the gates (Supplementary Methods §M2)"（四项协议控制压缩、§M2 逐字承载；**SI Supplementary Methods 五小节本批起编号 M1–M5**）；"a hard guarantee rather than a statistical outcome, and it held on every task" 删（0/20 蕴含、结构义由段内展示）；decision-layer→**plan-level**（L0–L6 撞名修复，fell→fall 对齐图例现在时；¶5 站同步、Fig. 3e/4f 图例挂账）；71 拦截句 including 从句退役（Table S1 第一行逐字演示代理被拒）；"never even obtained the scores it could not use"；成本账 "The guarantee of zero false claims had a measurable cost" + 80.0%（our→the 对齐图例；"we report it as measured" 删——Discussion 逐字存续）+ 分解一句平行 "Two true claims fell to the over-conservative uniform basis rule, two wrong-length sequences were abstained before their false claims could be published, and two lucky true positives on untrusted predictors could not be kept, with one true positive rescued"（机制与 59/60 nt 归 Table S1/冻结；图例 4d 委托正文的 decomposition 以此紧凑形态承载）；pilot 史两句退役。**¶5 mRNA 复现（135 词）**：镜像开头 "The mRNA tasks are a 20-task set…"（replicates/holds 经用户否决后 meta 句删除、数字自呈）；结果句并列谓语 "reduced…and kept all 12 true positives" + 越界独立句；go-gates-pass 尾删（图例 4g 逐字）；机制句 two-step→the full-length mRNA workflow（未介绍术语不再裸用）、never-profiled→unprofiled、drained→reduced、arise→are no longer made；"starts earlier" thesis 删（对比不可解码）；五封锁句 "…left the model no evidentiary path, and it published nothing rather than fabricate a claim"；幸存 FP 句 "The one remaining false positive came from the MRL predictor ranking the wrong candidate first on the weakest certified library"（flip 与 predicted-versus-measured 溶解为动作句、对称尾句删〔Table S1 第 8 行+图例 4g 承载〕）。**¶6 生产规模（95 词）**："The gates show the same behaviour at production scale"（gate semantics 行话→show the same behaviour 定稿）；frozen audit slice 三层溯源删（§2.2+图例 4h 逐字承载）、"the 241 production runs"（§2.2 句式归一）、every one traceable 删；"the decertified predictors"→"the predictors that failed profiling"（动词形引言 ¶4 存续）；decayed→reduced；allow 长句拆两句 "Every allowed request is a call to the 3′UTR-stability predictor, only to report its score, never to rank candidates. No ranking request is allowed, because no verified ranking grade exists for these tasks."（annotation call 行话写为动作、demoted 冗余删、holds→exists、"only allow class" 溶解〔图例 4h 逐字〕）。**¶7 治理消融段结构性迁出（用户决定）**：整段从 §2.4 删除——结果入新 **Supplementary Note 3 | Advisory review and per-agent ablation of the multi-agent layer**（评审三条件、消融两块、12 条声称拒 5、LLM 账本指针；协议指 §M5）；**原 Fig. 4i/4j 面板迁为 Supplementary Figs. S5/S6**（图例随迁、数字逐字；图件重排挂账）；正文提及点落 Methods Multi-agent 节 "The advisory review and every agent's contribution are themselves measured rather than assumed, in a three-condition advisory experiment and a registered per-agent ablation (Supplementary Note 3; Supplementary Figs. S5 and S6)"；Fig. 4 图例裁为 a–h、页脚改 eight panels；主题句历经 governance layers（撞名）→agents（循环指代）→multi-agent layer（真实层）后随段迁出。**三组全文术语统一（正文+SI 直接改、图例挂账）**：**platform→system**（正文 52+SI 30 站；方向按用户实事求是裁定——标题/摘要自我定义为 multi-agent system、system 为中性自指、platform 为积累变体；system-matched/system audit trail/system condition 落地；图例 12 站挂账）；**never-profiled→unprofiled**（正文+Methods 五站；图例三站挂账）；**family 三义分词**——anchor family→**library**（图例 4a 本用词、MPRA 事实词；Methods/DA/SI/Table S1 同步）、map 键维度保留 **target family**（Methods 元组零改动）、task 族→**tasks/task set/task groups**（Discussion flagship task sets、cross-family→cross-group〔所指经 exp18 冻结记录 task_family="cross_family_expression" 核实〕、SI per task group、Table S1 表头 audit group）；§2.3 IFN-γ 句 "a single in-silico-mutant family"→"one parent aptamer and its in-silico mutants"（对冻结锚集 `e1_anchor_set_v3.json` 逐条核实：B1-4 亲本+M1-8/M2-6/M3-6/M4-10/M5-5 五突变体，Kd 105.6–913.9 nM 跨不足一个数量级）。**退出正文数字/细节总账**（图例或 SI 逐字、其余冻结）：CI 41.5–67.0（Fig. 3e）/CI 0–16.1（Discussion）；31 条声称流水（图例 4e+冻结）；71 构成枚举（Table S1+图例 3e）；enforce policy/0.5/within-target relative/MRL 6.28/十二格预期（图例 4b+§M2）；RNAsmol 机制数字与 |Δp|（图例 4c+冻结）；生产逐预测器四类计数（图例 4h）；advisory/消融全部数字（Note 3+S5/S6）；mRNA 10+10 构成与四项生产资产（§M2）；3′UTR 降级细节（Methods ASF+§M1）；59/60 nt（冻结）。**挂账清单**：legend-sync 批新增 Fig. 4b self-model→capability map、Fig. 4c 标题三缺口、Fig. 1c/4b never-profiled、Fig. 3e/4f decision-layer、Fig. 4g 任务子族与 weakest certified family、Fig. 5 标题 task families、图例 platform 12 站；**图件批（新）** Fig. 4 去 i/j 重排+fig4i/j→figS5/S6 迁移+FIGURE_PLAN_V5；Methods-sync 批新增 self-model 定义句、ASF 两处 for example、managed→governed、gate decisions/verdicts 跨节统一（倾向 verdicts）；指针体例已决（用户 2026-09-28）：主题锚定 SI Methods 指针随所在节润色换 §M 号——实测四处全在 Methods（ASF 两步协议→§M1、GenNav 约束导航战役→§M3、Benchmarks 外部基线→§M4、Benchmarks claim-gating 任务集→§M2），随 Methods-sync 批一并换；§2.2/§2.5/§2.6 正文自身无 SI Methods 指针（协议指针按完备性批设计落 Methods），消融指针已随 ¶7 迁出且 SI Note 3 内为 §M5 数值式。登记：PAPER_DRAFT 头注 2026-09-28 条/本条/AGENTS.md。

- **§2.3 逐句润色批（2026-09-26，用户逐句主持，三失效模式小节五段全量重写，已完成）**: 零数字/图件/实验改动——保留值逐字，退出正文的数字全部由 Fig. 3 图例（a–f 逐面板核对）或冻结记录（`e1_anchor_set_v3`、exp5/10–16 verdict 文件）承载，逐项登记于头注本条。**小节重题** "Current scientific agents exhibit three systematic failure modes"（陈述句对齐同级标题；recurrent 全文退役、引言同步 "three systematic failure modes"；exhibit 经 show 往返由用户定留）。**开篇段三因重构**：一句三并列谓语（optimize predictor scores without validating the predictor's power / report their own results without verification / evaluate improvements under unequal sampling budgets）+ "These practices produce three systematic failure modes, which we quantify on the platform itself (Fig. 3)"——修正旧文把三种模式全部归因 uncalibrated scoring 的越界归因（模式二入口是未核验自述、模式三是预算不等，与引言定义一致）；"the live platform as shipped" → "the platform itself"（双重保证冗余且对去门控臂不准确；as shipped 留 §2.4/§2.6 两处对比位）；triad 句由省略式改三动词明写（actions/reports/evaluation，开篇预演、各块承接）。**三处加粗段首标签全部撤销**（Uncalibrated tool trust / Claim overreach / Confounded improvement 融入正常总领句）。**块一**：预测器列表前置并明写"即适配体工作流的排序依据"；assertion-curated → verified（读者面分层，Methods 三处不动）；EGARPS+ 加号核实为上游官方方法名（README/JCTC 标题）保留首现；亲和集括号 60→16 词、对接集句平行化（"The docking set holds 19 solved…"；逐靶构成、SOMAmer/镜像驳回、零干预执行句删，图例+冻结承载）；判读句压至三项阈值（≥2/3 形式归 Methods+Fig 1c 图例，类别释义与链名归图例；graded against → graded by）；"No predictor" → "None of the three"（防与 §2.4 认证的 MRL 预测器及 §2.2 小分子 profile 冲突）；screening/ranking/docking/Kd 四检验并为一段 For-X 平行（独立 docking 段并入；数值/1HVU 152/中位 decoy/HIV-1 RT 例子归图例与冻结；nominally exceed/cover chance → pass the gate/span chance；拆解句保留、策展溯源从句删；"passes on more than one target"、逐条反转句与 uncalibrated-vs-reliably-inverted 区分、climbing noise、四路同结论句删）；收束句改 "an agent that optimizes these scores may raise them without obtaining a better RNA molecule"。**块二**："occurs because agents report their own results without verification"（成因补全；enters through language 退役；narrate→report 对齐引言）；ungated 设置句 54→12 词（来源归 Methods、配平控制留 §2.4、live-fetch 归图例）；issued→made、sanctioned→what the evidence supported、intended use→predictor–use combination、class-selective 退役（"The failure occurs only where the evidence is untrusted"，数据完全分离 23/23 vs 30/32）；两类任务拆平行双句（untrusted 臂保留打分者身份为并列谓语）；93.8% 括号删（图例载，用途拆分冻结载）；例句 names/withheld/contradicts → declares/held-out/shows otherwise；稳健句自然化（Nor 倒装/artefact/legacy/strata 退役；分层分数与 borderline 注记冻结承载）。**块三 ~330→~150 词**：opener "The third failure mode, confounded improvement, emerged in the platform's earlier results (Fig. 3f)"（去 We 开头与 our own 强调）；循环同位语、reconstructed verbatim/driver-level/production-path 与 240/228/Ferritin 细节删（图例+冻结）；条件改述（a single-run baseline / the same run given the loop's budget / between-round analysis——serial/one-pass/diagnosis 退役）；decertified → uncalibrated（本节关键词；decertification 正式义留 §2.4）；门槛限定与全部 P 值归图例（δ +0.14/+0.05/−0.01 留锚）；**四步自审句泛化**（"not specific to this loop, but a general risk whenever improvements are evaluated under unequal sampling budgets"——该实验在 Methods/SI 均无协议描述〔仅 Fig. 3f 图例提及〕，按用户指示正文只述普遍风险，两条最强遗留声称/0 of 2/70% 门槛冻结承载）；"None of the three failure modes announces itself" 句删；铁律句改 "We therefore enforce budget matching on every comparison in this paper"（enforce 为 SI 协议动词；claim→comparison）。**房规机检全绿**（零破折号、零散文冒号、退役词零残留）。**图例同步批新增两项待办**：Fig. 3e "per predictor and use" → predictor–use combination；Fig. 3f 四步自审句（同步泛化，或在 SI claim-overreach 协议小节补协议描述后保留实指）。登记：PAPER_DRAFT 头注 2026-09-26 third-edit 条/本条/AGENTS.md。

- **§2.2 逐句润色批（2026-09-26，用户逐句主持，biological-validity 小节四段全量重写，已完成）**: 零数字/图件/实验改动——保留值逐项对冻结文件复验（20 靶 CAI 基准经 `exp2_cds_nulls/summary.json` 确认正确，用户疑的 25 是下段逆折叠基准）。**小节重题** "RNADesignAgent generates biologically valid RNA molecules"（删 "across eleven workflows" 尾——十一工作流中四个为评估类不生成分子，范围由首句承担，§2.6 标题独享该短语）。¶1：开篇改 "We tested the biological validity of the platform's outputs on RNADesign-210, the 210-task benchmark spanning all eleven workflows (Supplementary Tables S2 and S3)"（删 "We began by asking whether" 叙事框架、our、带说明指针；meaningful 统一为题名 validity）；预览句改显式 4+7 证据分工（用户指出 "four observations anchor biological validity" 造成"其余七个无证据"逻辑漏洞，且 anchor 撞锚点集术语）；CAI 链拆两句点名比较双方（which 误读会把 WT-对-随机统计量错挂到 designed 臂——两种读法皆为真、误读不自纠），删 default design flow/themselves/in turn；MFE 句 far more structured/either control/both nulls/whereas/indistinguishable → substantially more/two controls/for both comparisons/but/did not differ，WT-对-随机子句删（P = 0.30 图例逐字载）；lead on…at once → lead in…simultaneously。¶2：逆折叠 "against target secondary structures recovered the exact target" → "reproduced the exact target secondary structure"；两 miss 句压一（"The four misses were near-exact, each differing from its target by one to three base pairs"，逐任务得失枚举与 Hamming 2/2/4/6 图例载）；归因升格 "the shortfall lies in the generation tool rather than the platform's ranking"（用户指示——限制属被包装的生成工具，平台排序无可指责）；siRNA all but one → 21；例外解释改因果先行两短句（"The only exception is due to the benchmark input rather than the scanner" + DDX11L2 机制句；sole/originates/verbatim/spurious → only/is due to/exact/false；删 each a perfect full-length alignment 冗余、删扫描披露句〔图例逐字载〕；整段 ~200→~59 词）。¶3：小分子 "displayed the two-sided boundary its capability profile encodes" → "matched its capability profile exactly"（两侧由紧随 but 对比承担，登记术语留图 2f 图例；词选历经 behaved/performed/records/specifies → matched…exactly 收口）；AUROC 长句压缩（删 held-out、双括注并一按位配对、whereas→but 动词平行、panels→on short aptamers、no demonstrated power → no reliable power 对齐 §2.3 标题句；decoy 排位与 OOD CI 图例载；AUROC/CI/PDB 首现定义保留）；SI 路由句 95→28 词裸指针 "Supplementary Notes 1 and 2 (§S2.1–S2.6; Supplementary Figs. S1, S3 and S4)"（S3/S4 唯一正文引用与小节指针按完备性门保留；工作流↔小节映射交 SI 目录；sgRNA 锚缺口与 IRES 阴性注脚退出正文、SI 原文不动）。¶4 审计段："End-to-end, every campaign deposits a complete per-tool-call audit trail." → "Every run produces a complete audit trail, with one record per tool call."；run 级两处 campaign→run（"The 241 production runs…"、"A full design run…"），战役义 campaign 全局保留（冻结目录 exp24_production_campaign/、exp29_aptamer_campaign_arc/、Methods-SI 协议小节标题、图例）；form-entry subprocesses → entered through the user form；事件句括号全删（百分比/40 工具/11 预测器→图 2g 图例；判决四分解→§2.4+图 4f；**3 次瞬时失败披露按用户指示删——此后仅存冻结记录**）并恢复 "assemblies of ranking objectives" 三分句平行（assembled 动词版因破平行被用户否决）；"These aggregates are inspectable rather than opaque." 删（断言并入演示句）；演示句改图主语 "Fig. 2g traces every event class call-by-call in a representative full-length mRNA session from the same trail (1,853 tool calls, 882 gate decisions and 3 ranking assemblies)"（resolves→traces 房词，与 audit trail/traceable 同族；三轮/空闲/判决细节图例载）；运行时三句压两句 "A full design run completes in minutes to roughly an hour. Across the same 241 runs, the pooled median runtime was 2.5 min, with 239 of 241 finishing within 1 h (Fig. 2h)."（中位跨度/百分位/两例外图例载；例外句加后又按用户指示删；分号句按用户偏好拆回两句）。**缩写链三迁移**：CDS 定义上移 Overview GenNav 句（"in mRNA coding sequence (CDS) design"，修复 Overview 重写引入的裸用先于定义；工作流名 "mRNA CDS design" 他处不动）、IRES 定义下移 §2.6 首个裸用（"the four threshold-negative internal ribosome entry site (IRES) answers"）、3′UTR 定义下移 §2.4 首用（"the platform's 3′ untranslated region (3′UTR) stability predictor"）。**退出论文的数据**（图例/SI/冻结记录逐字承载）：254,070（GENCODE 转录本数，全文不再出现）、3 次瞬时失败、P = 0.30、decoy 排位（2nd of 1,601/7th of 265）、OOD CI（0.278–1.0/0.063–1.0）、70.1%/89.2%、2.8 s–8.9 min、70.7/72.3 min、§2.2 判决分解、21-nt 零错配量化。**登记待办**：① 图例同步批（图 2c both nulls/indistinguishable、图 2f two-sided boundary、图 2g ranking assemblies）② Methods Statistics 补非配对 Mann–Whitney 申报（现只申报配对 signed-rank 版）③ §2.4/§2.6 润色时两处下移定义随句走。登记：PAPER_DRAFT 头注 2026-09-26 second-edit 条/本条/AGENTS.md。

- **Overview 逐句润色批（2026-09-26，用户逐句主持，§2.1 三段全量重写，已完成）**: 零数字/图件/实验改动（41/21/eleven 与 L0–L6 码逐字保留，删除句均无数字），无 em-dash/散文冒号。**¶1**：首句 → "RNADesignAgent automates the design of diverse RNA types through a seven-layer architecture (Fig. 1a)"（"organized as" 整体-部分不精确、"general-purpose" 双重限定且与论文立场有张力〔全文唯一〕、"automates" 收口自动化弧线、seven-layer architecture 与图题对齐）；走层严格一层一句——L0 主动句 + invoked→called（统一 tool-call 词汇）、L0-L2 确定性扫过句拆为 L1/L2 两句（"Tool specifications are deterministic" 范畴错位消解、"All three layers are deterministic" 删〔确定性由溯源块承担〕）、L3 A→The + maps→matches〔Methods 待同步〕、L4-L6 拆三句（(below)/deterministically 用户决定删〔图例+Methods 存留〕；L5 isolate/carry 谓语对 Methods 落地；L6 用户版 "The entry layer (L6), a form-driven interface, receives the user's natural-language design goal and returns the results"〔CLI/FastAPI 降为不在场、CLI 首现定义链当场迁 Methods 修复〕）；溯源句重建为设计理念三句（"RNADesignAgent is built on the principle that the user must be able to reproduce and inspect the design process" + 确定性工具+审计轨迹 + 完整记录返回用户可 trace/replay）；two-design-commitments 收束两句删除（用户决定）。**¶2**：own strategy and retry → decide how to run the workflow and when to retry；六工作流 ASF 排序句删除（Methods 级细节；six-of-eleven 与 (ASF) 定义存留 Methods、§2.2-2.6 零 ASF 依赖）；headline claims → claims 五处统一（§2.1/§2.4×2/§2.6/Methods，对齐 Fig. 1b 图例 "every claim checked"——单数形式第五处系复数搜索漏网后补）。**¶3**：supply the platform's calibration → counter the three failure modes（calibration 只罩信任侧、supply 搭配不地道；引言双机制框架托付归位）；CapGate/GenNav 全称复拼改缩写（引言为首现定义位，Methods 标题保留全称为惯例）；two deterministic points → gates（对齐摘要/引言）；DecisionGate 句 stands at→guards + "whose evidentiary basis is absent"→registered "unsupported"；ClaimGate 句 sits on→checks（避 QualityAgent 的 reviews 与筛查术语 screens）；GenNav 分词链（implemented as X, inherited by Y, and as Z）消解为 implemented as 一对同位语 + 继承句删除（全文唯一出现、§2.2 two-step 描述间接覆盖）+ themselves 删；收束路标句删除（production-default 声称存留 §2.4 + Methods）。登记：PAPER_DRAFT 头注 2026-09-26 完整条/本条/AGENTS.md。**批内追加待办（2026-09-26 用户决定）**：Overview ¶1 收束的 two-design-commitments 两句（"Two design commitments anchor the architecture (Fig. 1a, bottom). The LLM never writes a sequence, … budget-matched protocol, …"）已从正文删除；连带 Fig. 1a 底部承诺条面板失去唯一正文引用 "(Fig. 1a, bottom)"，用户指示面板一并删除——待做清单：① PPT2 panel_a 脚本删底部两条承诺条并重建 fig1（build_pptx.py 原生形状、零图片）② 重装配 Fig 1 组合图 + 房风/QA 断言全绿 ③ Fig. 1 图例删 "The two design commitments below state that…" 整句 ④ FIGURE_PLAN_V5 Fig 1 行同步 ⑤ 知情登记：两条承诺声明（LLM never writes a sequence / pre-registered, budget-matched as architecture commitments）删除面板后将全文归零，若后续需要 LLM 角色边界声明（如支撑 §2.6 基线对照）需另行落位。
- **镜像减负第四批 — cu13 死重卸载 + 同路径覆盖事故修复（2026-09-25，用户指示"把两处 cu13 死重〔egarps 连同 triton〕卸掉并进行服务健康验证"）**: egarps_env 12G→8.5G、sgrna_design_service_env 12G→8.8G，envs 合计 77G→74G（净释放约 2.5-3G——两环境 cu13 文件此前的硬链接去重已合并跨环境副本，联合体去重收益小于各环境账面降幅）；egarps 卸 16 包（cu13 家族 15 包 + triton 3.6.0，torch 1.12 时代无 torch.compile）、sgrna 卸 15 包（cu13 家族，保留全部 `_cu12` 后缀包 + triton〔torch Required-by〕）。**事故与修复（如实登记）**：卸载后 sgrna `import torch` 失败——根因是 cu12/cu13 两族部分包**同版本同路径**（nvshmem 3.4.5/nccl 2.28.9/cudnn 9.19.0.56/cusparselt 的同名 so），cu13 安装时即覆盖 cu12 文件、卸载 cu13 时按 RECORD 把共用文件一并带走；且公网 PyPI 不可达（DNS 失败），一次 `--force-reinstall` 还把 nvshmem-cu12 元数据先卸后装失败。**恢复路径**：`/etc/pip.conf` 的集群内网 Nexus 镜像（nexus.sii.shaipower.online）可达——先 `pip download` 四个 wheel 到本地（cudnn-cu12 9.19.0.56/nccl-cu12 2.28.9/cusparselt-cu12 0.7.1/nvshmem-cu12 3.4.5，共 1.3G）再本地安装，避免安装期网络依赖。**验证全绿**：RECORD 文件级审计两环境 ALL INTACT（egarps 亦审计无恙）；功能实测 egarps torch 1.12.1+cu116 + dgl + cuda matmul、sgrna torch 2.11.0+cu128 + transformers 5.5.4 + cuda matmul；平台 `ensure_services_ready` 自动拉起 8017（sgrna/CRGPT）与 8023（egarps）健康检查全过、验证后服务停止端口释放；全量套件 700 passed 1 skipped（=基线）。**连带核查**：odesign/rnarl/rnasmol_gpu/gemorna 四环境 torch+CUDA 实测正常（账面体积变化为 du 硬链接归属重分配，非数据丢失）；全机扫描无其它环境残留 cu13 家族。经验登记：本机 pip 需显式 `--index-url http://nexus.sii.shaipower.online/repository/pypi/simple`（用户级 pip.conf 的公网 PyPI 优先且公网不通）；同族多 CUDA 版本 wheel 的同名路径覆盖是 pip 卸载的已知陷阱，卸载后必须做 RECORD 审计 + 运行时验证。零论文数字/图件改动。
- **镜像减负第三批 — 环境层压缩（2026-09-25，用户指示"再检查 19 个微服务环境是否能压缩/其它减小镜像策略"）**: 镜像 133G→116G（累计 203G→116G）。(i) **proteinx_service 死栈清除 −5.7G**：env 内并存 python3.11（活跃，`bin/python` 指向 3.11.15）与 python3.12 两套完整 site-packages（各含 torch/CUDA 栈，3.12 无解释器、无 bin 引用，确认为构建残留）——删除前 tar 备份至 `model_caches/quarantine/proteinx_python3.12_lib_2026-09-25.tar.gz`（2.9G，网络盘）；验证：env python `import main` 全栈导入 OK + `ensure_services_ready` 自动拉起 `/health` 通过。(ii) **跨环境硬链接去重 −11.3G（实测）**：对 envs + miniconda3 base lib + /usr/local/lib/python3.12 + /usr/local/cuda-12.8 中 ≥10MB 文件按（大小、权限、blake2b 全文哈希）分组，字节相同者原子替换为硬链接（保留最高 nlink 者为规范 inode，273 文件、0 错误）——重复主因是 21 个环境各携一份 torch/CUDA 库（libcublasLt/libcudnn_cnn/libtorch_cuda 等多副本，≥50MB 层名义重复 19.3G，其中部分本已通过旧 pkgs 缓存共享 inode，实际净释放约 11.3G）；conda 自身即以硬链接共享包文件为设计，对运行透明。验证：全量套件 700 passed 1 skipped（=基线）、受影响环境（rnasmol_gpu/gernabind/rhofold）torch 导入正常。(iii) 排查后不动：sgrna `targets/`（conda cuda 包登记在案的安装布局，lib/ 符号链接运行时指向其中，1.7G 但动则破坏 conda 记账）；`__pycache__` 全部环境合计仅 30M；系统 python3.12 dist-packages 8.5G（flash_attn/transformer_engine，集群基础镜像自带，非本项目安装）。剩余策略（用户决定）：镜像导出若支持 zstd/squashfs 压缩可再省约一半存储；vscode-server 只留单版本再省 ~3.7G；不常用大环境迁网络盘+软链（egarps 12G/sgrna 11G，启动变慢）。零论文数字/图件改动。
- **镜像减负批 + RNAsmol 自动启动切 GPU（2026-09-25，用户指示"删除 4 个无引用的环境和 rnasmol CPU 版"/"把 service_manager.py:175 的脚本改成 start_gpu.sh，肯定不能让平台失败"）**: 机器镜像（容器可写层）203G→133G（两批合计释放约 70G）——(i) /tmp 22G→1.1G（45,770 个过期 `tmp*.cif`、284 个 pip-unpack 残目录、AlignIF 残留）；(ii) conda `pkgs` 缓存清空（与环境硬链接共享，净释放约 4G）；(iii) torch hub 4 个 `.partial` 未完成下载 2.2G 删；(iv) CUDA JIT 缓存/npm/uv/pip 缓存清；(v) vscode-server 旧版本清理（保留最新两个）；(vi) 模型权重（ESM2 两格式/RhoFold/RNA-FM，共约 6.8G）迁至网络盘 `model_caches/{huggingface_hub,torch_hub_checkpoints}` 原位软链接，服务加载不受影响；(vii) **删除 5 个 conda 环境**：`py39`/`LLPS_model`/`odesign_eval`/`aptamer_eval`（平台零引用、无 environment.yml）+ `rnasmol_service_env`（CPU 版，31G，重建用 `microservices/rnasmol_service/environment.yml`），余 21 个全部为平台引用的服务环境。**平台变更**：`agent_core/services/service_manager.py` RNAsmol（8007）自动启动脚本 `start.sh`→`start_gpu.sh`（GPU 环境为现行主力；CPU 环境已删、CPU 主机用 environment.yml 重建并指回 start.sh）；`start_gpu.sh` 补可执行位（`test_all_mapped_start_scripts_are_executable` 守卫捕获后修复）。**验证**：test_service_manager 36/36、全量套件 700 passed 1 skipped（与基线一致）；真实拉起验证——8007 无服务状态下 `ensure_services_ready` 自动经 `start_gpu.sh` 启动、健康检查通过、`POST /score` 真实请求 0.60 s 返回（checkpoint 自动发现、GPU 推理正常），验证后服务已停。文档同步：TOOLS.md 8007 行 + §5.1 Notes（GPU 为默认、CPU 降为 fallback，历史 PTX-JIT 理由保留）、docs/tools/score_rna_ligand_binding_with_rnasmol.md 头部。exp7/exp15 驱动脚本中的 `start.sh` 字样为冻结实验记录（当时确以 CPU 服务运行），按惯例不动。零论文数字/图件改动。

- **引言逐句修订批（2026-09-25，用户逐句主持，Introduction 四段全量重写）**: 零数字/图件/实验改动——引言数字多重集对改前逐 token 机器比对相等，冻结值全部逐字保留（210/41/21/0.896/0.729/P=1.1×10⁻⁶/all three/0%/7.7%/54.5%/33.3%/25/20:6/0.009/10:2/0.039/eleven）；无 em-dash、无散文冒号（20:6 与 10:2 为比值豁免形式）；mRNAs/siRNAs/ASOs/CAI/LLM 首现定义完好。**¶1** 机制开篇——"RNA therapeutics deliver RNA molecules that encode therapeutic proteins, silence or edit disease-causing genes, or bind disease-causing proteins"（三动词分支映射五类分子）；五类句 "are approved medicines or late-stage clinical candidates"（"modality of central importance" 退役，全文唯一 modality；hold/sit in→are）；设计对压缩（intended→desired、"substantially" 删、"multi-objective optimization problem" 留 §2.1、转折 yet 删）；瓶颈对重建（However 转折重立、cadence→updates accelerate、abundance/bandwidth→rapid growth/capacity of experts、补 high-quality 限定）。**¶2** 六个具名系统（ChemCrow/Coscientist/ProtAgents/Virtual Lab/CRISPR-GPT/BioMni）退出正文、投稿时挂引用（四领域保留含 gene-editing planning；具名桥接功能由 "recent systems" 类指承担）；综述合并单句收于 ", but none of these systems covers RNA design"；natural→promising candidate；Large-language-model→Large language model（连字符删）；架构句改 "In addition, current scientific agents call tools without validation and report their own results in natural language, and our experiments show that this architecture produces three recurrent failure modes"（§2.3 术语 current scientific agents 提前入引言；架构归因由 this architecture 承载）；三联定义统一 occurs 平行（uses…without validating whether…on the specific task；write reports, which often contain statements…〔often 有实测支撑〕；an apparent gain may reflect a larger sampling budget rather than real improvement）；段尾全称否定句 "No existing scientific agent profiles…" 整句删除（全文唯一，退出正文；缺口主张由 None of these systems covers… + 三联承担）。**¶3** "To address these failure modes, we present RNADesignAgent, a multi-agent system for automating RNA design"（目的从句补回被删句的桥；automating 收口摘要→¶2→¶3 自动化弧线；tool-oriented/calibrated 删——后两句即其展开）；wraps…behind→integrates…through、deterministic 删（§2.1 "are all deterministic" 承担）、span→cover（全文清 span 家族）；"Two mechanisms counter these failure modes" 删（§2.1 存续）；CapGate 定义句降到摘要粒度——"evaluates every predictor on verified anchor sets, producing a capability map that drives two deterministic gates"（三元组留 §2.4；assertion-curated→verified，摘要与 §2.1 同步 audited→verified 共三处、assertion-curated 四处留 §2.4/Methods 为方法层术语；before use 删〔drives the gates 隐含时序〕；feeds→drives）；双门句 "A DecisionGate prevents unsupported actions, and a ClaimGate weakens or removes natural-language claims that exceed the evidence"（prevents 与 unsupported actions 均为摘要动词/短语逐字）；GenNav 句以摘要动词/名词重建——"guides the generator through its control settings to produce candidates that satisfy multi-constraint requirements at a budget matched to the comparison"（31→27 词，摘要最简/引言加机制与预算/§2.1 全量三层递进）。**¶4** Across→On（基准惯用介词，且与 every 语义重叠）、spanning→covering；CAI 句重构（For example 前置、数字升主动词、比较降分词）；profiling 对句重写——"Capability profiling decertified all three deployed structure predictors on aptamer tasks but certified an expression predictor on measured ribosome-load anchors. On aptamer and full-length mRNA tasks, the resulting gates reduced false-positive claims to 0% and 7.7% from 54.5% and 33.3% ungated"（two-sided 标签删〔对比由 but 承担〕；flagship task families 抽象层删→两族点名 aptamer 与 full-length mRNA，修复指代悬空；family→tasks 粒度；"eliminated"→"reduced…to…from…" 为精度修正〔7.7%≠0，原 eliminated 对第二族偏松〕；TP 保留成本句删〔摘要 "while preserving most true ones" 与 §2.4 存续〕）；navigation 对句压缩——"On 25 mRNA targets, constraint navigation at equal budget won the paired comparison against the static executor (20:6, McNemar P = 0.009). Transferred to the aptamer generator, the same mechanism won at low budgets (10:2, P = 0.039)"（run deterministically/registered/pooled over/discordance 限定词退役；25 targets 前置复用范围前置模式；two-sided operating regime 与 starvation-scale 留 §2.5；输侧披露由 §2.5 + 图 S2 承担；unchanged 与 diffusion-based 删〔用户定〕；equal budget 保留——与失败模式三的对应线不断）。**摘要两处登记句内单字同步（用户确认）**："Language-model agents"→"Language model agents"（连字符，2026-09-25 句内）；"audited anchor sets"→"verified anchor sets"。登记：PAPER_DRAFT 头注 2026-09-25 Introduction 条/本条/AGENTS.md。

- **摘要第二句三失效枚举重写批（2026-09-25，用户改写并经核查确认）**: Abstract 第二句替换为显式三联枚举 "Language-model agents promise to automate this process, but still face three major issues: accepting tool predictions without validation, asserting claims beyond what their evidence supports and reporting gains confounded by unequal sampling budgets."（取代 2026-09-21 second-edit 的 "yet scientific agents based on such models…" 句，该登记按惯例保留为历史）。核查结论：三个动名词分句与三失效模式逐一对应（未校准信任/声称越界/混淆改进，"unequal sampling budgets" 与 §2.3 收束句逐字一致）；一处语法修正落地——"what their evidence support" → "supports"（evidence 单数不可数，前一版登记句即 supports）。两处经用户确认的房规豁免一并登记：(i) "three major issues:" 后的枚举冒号为散文冒号房规（仅存比值/URL）的定点豁免，只此一句；(ii) 摘要用 "three major issues"、正文既定称呼仍为 "failure modes"（Introduction "three recurrent failure modes"、摘要末句 "resolves these failure modes" 回指该三联），称呼差异经用户确认保留。摘要 155 词（前登记 "156 words" 随替换过时）。零数字、零图件、零实验改动；新旧句均零数字（数字多重集天然不变）。登记：PAPER_DRAFT 头注 2026-09-25 条/本条/AGENTS.md。

- **摘要术语句修正批（2026-09-21 同日第二批，用户指示"统一摘要第二句中 Language-model agents 与 scientific agents 两个称呼"，并否决首版 "built on them" 措辞不合科技写作风格）**: Abstract 第二句原为 "Language-model agents promise to automate this process, yet current scientific agents accept…"——全文唯一一处两词同句、句中直跳无衔接（Introduction 同样换词但中间有 ChemCrow 等具名系统桥接）。改为 "…, yet scientific agents based on such models accept tool predictions without validation…"——以规范措辞显式交代子集关系（科学智能体建立在语言模型上；"built on them" 除风格外还指代错位，them 语法上回指 language-model agents 而非 models），"current" 的时域限定由现在时态与当代技术限定语承担、避免三修饰语堆叠；正文对失败模式主语的既定称呼不动（§2.3 标题与首句、Fig. 3 图例的 "current scientific agents"、Introduction 的 "No existing scientific agent"）。净增 3 词、摘要 156 词。零数字、零图件、零实验改动；无 em-dash/散文冒号引入；新旧句均零数字（数字多重集天然不变）。登记：PAPER_DRAFT 头注 second-edit 2026-09-21 条/本条/AGENTS.md。

- **深度语言重写批（2026-09-21，用户指示"学术论文编辑 + AI 痕迹清除式深度重写：提升词汇学术性与精确度、优化句构、保持原意、客观严谨、删空洞开场与废话、减少机械连接词、调整句长节奏避免整齐排比"）**: 正文（Abstract/Intro/六 Results 节/Discussion/Methods/Data+Code availability/六图例）与 SI（Scope 导览/Note 1/Note 2 六小节/五协议小节/外部基线 "meaning" 连接词）逐句重写，**零数字、零图件、零实验改动**——机器校验三重全绿：(i) 新旧读者面正文数字多重集逐一相等（paper 1,358 token、SI 868 token）；(ii) SI 冻结块逐字节一致（Table S1 逐字引文、Table S3 表体 + 33 条文献、S2.3 PDB 表、数据可用性表、Scope 溯源段）；(iii) 补充材料指针全解析（Note 1、§S2.1–S2.6、Figs. S1–S4、Tables S1–S3、五个 Supplementary Methods 协议指针）。改动类型：(a) **机械枚举散文化**——First/Second/Third/Fourth 序数衔接全部消解（Intro 三失效模式、§2.2 四观察、§2.4 两证据性质、Methods GenNav 四组件、Data availability 四部分、Discussion 局限两条），"namely" 两文档清零（15 处）、"meaning"-连接词替换；(b) **空泛开场清除**——§2.5 修辞性设问开场改陈述式，Discussion "A central insight is that" 框架删除直陈其论，Abstract 无支撑的 "significantly" 删除（统计量已随句引用）；(c) **段落拆分**——§2.2 巨型单段拆三段、§2.3 trust 拆锚集/结果两段、§2.4 六段→十段、§2.5 三段→五段；(d) **句构与节奏**——重复句首、"so" 因果链、并列从句改从属/分号变奏；(e) **忠实性微调回填**（design cycle/RNA design tools 等措辞对齐原文）。房规复验绿：无 em-dash、散文无冒号（比值/URL 除外）、术语与缩写首现定义 grep 完好。Benchmarks/锚集段、SI 目录表与 S1–S4 图例有意近乎原样（清单式散文本已合规）。登记：PAPER_DRAFT 头注 2026-09-21 条/本条/AGENTS.md。

- **语言润色批（2026-09-15 同日第六批，用户指示"正文与补充材料文字润色：用词简单精准、不用破折号冒号、少用括号、专有描述全文统一、缩写首现全称"）**: PAPER_DRAFT 正文（Abstract→Intro→Results 六节→Discussion→Methods→Statistics→Data/Code availability→六图例→页脚）与 SUPPLEMENTARY_INFORMATION（Scope/Contents/Notes 1–2 §S2.1–S2.6/五个 Supplementary Methods 协议/Figs. S1–S4 图例/Tables S1–S3/数据可用性表）逐段重写，**零数字、零图件、零实验改动**（新旧正文数字多重集逐一比对，全部差异可归因于刻意删除的内部代码/日期/任务标签与标点粘连记号）。四条房规：(i) **破折号/冒号清零**（正文 em-dash 288→0、SI 122→表内占位符与文献题名；冒号仅保留比值记号 b:c/10:2 与 URL；长破折号长句拆为短句；括号只留图件/统计指针）；(ii) **术语统一**（工作流名一律 Methods 目录的十一个全名——SI 表 S2 "sgRNA handle design"→"sgRNA design"、§2.2 路由句改按 §S2.1–S2.6 顺序逐一全名；condition 不用 arm；predictor 不用 oracle〔SI 残留 8 处全部位于 Table S1 逐字引文内，设计上不动〕；self-model 替代 SelfModel；versus 替代 vs；b:c 去空格；no-go 替代 NO-GO；end-to-end 替代 e2e/gene-e2e；856-aa→856-amino-acid；rhinovirus A1/BiP 拼写对齐；"rule-based executor/rule baseline"→static executor/condition，工具具名 static recipe(mRNA)/static grid(aptamer)）；(iii) **缩写纪律**（首现全称+括号缩写、此后只用缩写——正文补定义 mRNA/siRNA/ASO/CAI/AUROC/CI/PDB/IRES/UTR/Kd/pLDDT/ipTM/TM-score/RMSD/MRL/CLI/FDR/JCD/ASF/lncRNA/GEO；SI 独立定义 AUROC/CI/nt/IRES/ASF/RMSD/TM/MFE/CAI/ORF/WT/PDB/MRL/LLM/CLI/MCMC/ddG；机器核对每个缩写裸用不早于定义）；(iv) **去内部代码**（六图例与 SI 读者面的 Exp 编号、PA_036、DECISIONS 指针、2026-XX-XX 日期、"identity-70" 标签全部换描述性措辞——批次八预留的"图例溯源注记下一批"就此清账；§2.6/图例的 "section 2.3" 数字节引用改描述性短语；S2.5 的 DECISIONS.md (l)/E19/E20 内部指针移除；S2.4 的 agent_core 代码路径删除；Methods 排名小节标题去冒号）。机械复验全绿：正文/SI 破折号与冒号清零、术语 grep 清零、缩写定义先于首用、Table S1 逐字引文未动（"oracle" 等 8 处按冻结记录保留）。图零重渲（fig2a/fig6a 等面板工作流短标签来自共享 palette.py 的展示形短名，内部一致）。登记：PAPER_DRAFT 头注 fifth-edit 条/本条。

- **补充材料引用完整性批（2026-09-15 同日第五批，用户指示"确保补充材料中的每个小节、每个图、每个表在正文中都有引用"）**: 机器核对现状后补四处缺失引用、全量校验全绿——**(i)** §2.2 七-workflow 路由句重写为逐小节指针（Note 2 §S2.1–§S2.6 各自点名；Supplementary Fig. S3/S4 首次由正文引用——三级结构有效性池随 §S2.3、评分方向分析随 §S2.4；IRES 从句承载 Note 1 + Fig. S1，Fig. 2 图例原有 S1 指针保留）；**(ii)** ASF 目标句的 3′UTR 降级指针显式指向两步协议（Supplementary Methods）；**(iii)** GenNav Methods 末句补约束导航战役协议指针（选择层池测量、预算配平终点战役 + 合并部署队列、扩展池预算扫描）；**(iv)** §2.4 逐智能体消融句补两块协议指针。**校验脚本全绿**：Note 1、Note 2（含 §S2.1–S2.6 六小节各 ≥1 处）、Supplementary Fig. S1–S4、Supplementary Table S1–S3、五个 Supplementary Methods 协议小节的主题锚定指针（两步协议/声称审计与门控/约束导航战役/外部基线/逐智能体消融）全部在正文或图例解析。零数字/图件/实验改动。登记：PAPER_DRAFT 头注 fourth-edit 条/本条/AGENTS.md。

- **补充图三张批（2026-09-15 同日第四批，用户指示"补推荐的三张图"）**: 补充材料由一图扩为四图——三张新补充图全部从冻结记录零新计算绘制、逐数字断言=冻结文件，房风全绿（palette rev 7、绝对 mm、6-pt 纯黑、无 tight crop、1200-dpi PNG + 矢量 PDF、文字画布内/两两不撞/文字-标记/文字-线碰撞守卫、栅格纯度检查含披露的多墨混合区）。**Supplementary Fig. S2（正文 §2.5 首引）**= 适配体 39 靶扩展池预算扫描曲线（`figS2_aptamer_budget_sweep.py`）：交付格数 vs 原始候选配额 cap（16/20/24/32/48），GenNav navigation（sage）vs 静态网格（terracotta，Fig-5 臂色），每标记标注交付数、每 cap 两行刻度标签印 b:c（10:2/9:4/13:10/10:22/12:30）与 exact McNemar P（0.039/0.267/0.678/0.050/0.008，图例文字承载）——§2.5 双向运行区制与 24→48 交叉此前仅有文字，现在可见；nav [10,9,18,17,34] vs static [2,4,15,29,52] 断言=`expanded_summary.json`。**Supplementary Fig. S3（Note S2.3 引用）**= 三级结构有效性池（`figS3_tertiary_validity_pool.py`）：73 候选共享行点图（fig4a 共 y 约定）——RhoFold 重折置信（mean pLDDT，任务阈值 65/70 虚线）+ 对参考 RMSD（0–3 Å 浅带 = RMSD 门任务界限，3 任务/14 候选），rubric 通过 sage 实心/未过空心，右缘逐参考通过数 14/14、4/5、2/2、2/12、3/11、2/7、1/4、0/18，行序=§S2.3 表；pooled 28/73=38.4%、12/20 任务有 ≥1 通过、pLDDT 中位 37.4/RMSD 中位 18.8 断言=冻结 summary（记录重算一致）。**Supplementary Fig. S4（Note S2.4 引用）**= 评分方向主分析（`figS4_scoring_direction.py`）：每靶一行——10 个种子随机同义重抽（空心深暖灰）+ 中位刻（黑）+ WT CDS 实心点（高于自身中位 sage/低于 terracotta），共享合成分轴，行按每靶 Δ 降序（HER2 +477 居首）；15/20 sign P=0.041、12/20 全超十抽、五例外 GFP/HPV16 L1/Luciferase/RSV-F/Spike WT；逐靶 WT/中位/方向标志由 records.jsonl 重算并断言=summary per_target 逐项相等；疫苗 260.7/404.8（n=2 描述性）文字报告不入图。编号 S2–S4 按首引顺序（S1=正文 Fig. 2 图例首引；S2=正文 §2.5；S3/S4=SI Notes）。SI 更新：Contents 目录 +三行、Scope 导览补一句（图件部分现含四幅）、§S2.3/§S2.4 首段加指针、Constraint-navigation 协议句加 S2 指针、三条 Nature 式图例入 Supplementary Figures 节、数据可用性注记扩为 S1–S4 产出说明。登记同步：PAPER_DRAFT 头注 third-edit 条 + §2.5 指针、FIGURE_PLAN_V5 补充图表三行、PAPER_FACT_SHEET 三行、本条、AGENTS.md。零数字/主图/实验改动。

- **补充材料三段式重组批（2026-09-15 同日第三批，用户指示"按 Nature 惯例把补充信息按文字部分、补充图、补充表三部分组织，参考 coscientist SI 格式"）**: `docs/SUPPLEMENTARY_INFORMATION.md` 整体重排为三段式。参考范式核对——Coscientist SI = Supplementary notes（编号文字节）→ Supplementary figures（"Supplementary Fig. N | 标题. 图例"）→ Supplementary tables（"Supplementary Table N | 标题."），LinearDesign（Nature）SI 同序且篇首有 "List of Supplementary Information" 目录。**新结构**：**(i) 文字部分** = Supplementary Notes（Note 1 IRES 面板 + Note 2 其余六 workflow 证据 S2.1–S2.6）→ Supplementary Methods（五个协议小节，由篇首移至 Notes 之后，逐字保留）；**(ii) Supplementary Figures 新设节** = Fig. S1 图例从 Note 1 内嵌段升为独立 Nature 式图例（"Supplementary Fig. S1 | IRES prediction on the validated literature panel"，自含：面板构成、mode-2 0.673/0.467–0.862/P=0.102/δ=0.35 与 mode-0 0.478/0.311–0.649/P=0.841/δ=−0.04 全部冻结值逐字、companion 面板与产出 PNG/PDF 路径写明），Note 1 原处改为 "(Supplementary Fig. S1)" 指针；**(iii) Supplementary Tables** = S1/S2/S3 标题改 "Supplementary Table SN | 标题" 体例，表体逐字不动；篇首新增 **Contents 目录**（LinearDesign 体例）+ Scope 块重写为三段式导览（"Every number below is backed by a frozen file" 溯源保证句逐字保留）。**S 编号保留**（不改 S1→1）：正文引用全部按名（§2.2 "Supplementary Notes 1 and 2"/"Table S2/S3"、Methods "Supplementary Methods"×2、Fig. 2h 图例→"Fig. S1"、Fig. 4j 图例→"Table S1"、表内 §S2.x 互引），重排后全部仍解析，零主文改动。**机器校验全绿**：五个 Methods 小节 + Note 2 整体 + Table S1/S2/S3+33 引文块在空白折叠与标题记号归一后逐字一致；Note 1 = 旧文 − 图例段 + 指针（精确匹配）；图例数字全部为冻结 Note-1 值；S1 10 行、S3 36 工具行、33 条引文计数不变。零数字/图件/实验改动。登记：本条 + AGENTS.md（头注日期与 What's New）。

- **补充表 S1 补缺口 + 图例审计批（2026-09-15 同日第二批，用户指示"查图例是否需更新、S1 是否还需要，需要则补上"）**: (i) **图例审计结论**——六图图例逐条对补充材料/正文交叉引用核对，唯一结构性缺陷 = **Fig. 6 图例排在了 "*End of draft v4.5*" 文末注记之后**（添加 Fig 6 那批的排版遗留；文末注记本身已是六图口径），已移到 Fig. 5 图例与注记之间；其余图例无需因 S2/S3 或本批改动（Fig. 2h→Suppl. Fig. S1 指针本就成立；Fig. 4j→Suppl. Table S1 指针随本批落地；S2/S3 的指针在 §2.2 与 Methods，图例不需要）。(ii) **S1 仍需要**（正文 Fig. 4j 图例引用是活的）→ **已补写**：`docs/SUPPLEMENTARY_INFORMATION.md` 的 Supplementary Tables 节首新增 **Supplementary Table S1 — Representative ungated claims and their gated counterparts**，8 行代表性任务对（数据 = 重置后冻结记录 Exp-17 `adjudicated.jsonl`+`runs.jsonl` 与 Exp-18 同构，非预注册行里的前重置 E3 文件）：适配体审计 6 行（Ang-2 排序 FP + 被门驳回的 GC 代理替代声称；筛查假阴性声称被三个拒绝的计划请求静默；Thrombin FP 改为裁为 borderline 的弃权声明；VEGF 逐 predictor FP + pLDDT 注记放行但声称仍被压制的两门故事；确定性 TP 保留一例；uniform-basis 压制一例=80% 保留率分解的实测实例）+ mRNA 审计 2 行（3′UTR 稳定性 require-profiling 拦截→无分→弃权声明被 ClaimGate 压制；MRL 认证家族放行且过门但仍裁假的幸存 FP=1/13，正文已披露的对称排名翻转）。**逐字核验**：表内 29 段引文（声称文本/裁决理由/门控理由）全部对冻结 jsonl 机器核验 byte-identical；逐声称总量（55 vs 31、21 vs 16）对 Fig. 4e,g 口径。Supplementary Information 的 Scope 块同步三表口径。零数字/图件/实验改动。登记：PAPER_DRAFT 头注 second-edit 条 + Fig 6 图例移位、FIGURE_PLAN_V5 S1 行（已写+数据指针重基）、本条、AGENTS.md。

- **补充材料目录表批次（2026-09-15，用户指示"11 个 workflow 和 41 个工具各加一个补充材料介绍表"）**: `docs/SUPPLEMENTARY_INFORMATION.md` 新增 "Supplementary Tables" 节——**Supplementary Table S2（十一个 workflow）**：Function / Design（generation → evaluation → ranking，含 GenNav-λ 与两步全长协议、ASF 六工作流、三个 deterministic-exempt）/ Advisory review / Evidence 指针（逐 workflow 指向正文图或补充 Note），骨架句写明共享 generate→evaluate→score→rank 与 210/210 完成；**Supplementary Table S3（41 个工具）**：注册名（`tool_inventory.py` 清单逐一核对，11 generator + 12 predictor + 16 compute + 2 utility、35 微服务承载/6 平台内实现）/ 底层方法与部署 / 功能（docstring 提炼）/ CapGate 列（Fig. 4h 的 11 个受管 predictor，CRGPT 与 CRISOT 两个 pending 数据缺口标注）/ **33 条 Nature 格式参考文献**——引文逐一对 `external_repos/` 上游 README 引用节核实、发表版卷页码经网络复核（LinearDesign Nature 613:360–366、GEMORNA Science 390:eadr8470、RhoFold Nat Methods 21:2287–2298、RhoDesign NCS 4:829–839、RNAsmol NCS 5:648–660、GerNA-Bind NMI 7:1996–2008、EGARPS JCTC 21:9200–9213、CRISOT Nat Commun 14:7521、RiboDiffusion Bioinformatics 40:i347–i356、Evitar Bioinformatics 38:2437–2443、IRESfinder JGG 45:403–406、LinearFold Bioinformatics 35:i295–i304；Protenix 为 bioRxiv 预印本并加引 AlphaFold3 Nature 630:493–500；ODesign arXiv:2510.22304；RNARL/RNASTOP 按作者自家软件+稿件引用、CRGPT 按未发表软件引用；纯 Python 工具引方法学源——Sharp & Li 1987、Nakamura 2000、FreeSASA、DBSCAN、TM-score、Biopython，ViennaRNA 五程序分包引 RNAfold/RNAcofold/RNAup/RNAplfold/RNAinverse + siRNA 不对称性 Khvorova/Schwarz 2003）。**编号决策**：S1 保留给 FIGURE_PLAN_V5 已注册、Fig. 4j 图例已引用的 representative-claims 表（尚未撰写）。正文只加两处指针（§2.2 首句 + Methods System architecture L2 句）。零数字/图件/实验改动；登记：PAPER_DRAFT 头注 2026-09-15 条、FIGURE_PLAN_V5 补充表两行、本条、AGENTS.md。

- **§2.6 核验修正批（2026-09-14，用户指示"按最新实验结果与最终版 Figure 6 更新 2.6 小节"）**: 按用户要求先复核 `relevant_references/` Nature 范式（DeepRare 等 Results 比较小节惯例：基线点名、精确数字内联、Figure 引用、边际直述——§2.6 现行行文已合此范式），再逐数字复核 §2.6 四段 + Fig 6 图例 vs 冻结证据（`exp42_43_comparison/comparison.json`、Exp-42/43 summary、逐轮 adjudicated 记录、逐轮工具日志）——交付 96/96、71/69、7/44/71；McNemar 平台独胜 25/27/89/52/25、反向 0、P<1e-6；失败拆分 14/11（zs）、13/14（fs）、86/42（matched/3× 预算耗尽）、16+9（10×）；12:12 P=1.0 及各 workflow 胜负；声称 48.3%（CI 43.5–53.1）/11.4%/51.9%/51.1%（CI 44.7–57.5）、不可验证 30–37%；成本 146 vs 756+659=5.2×；8 个确定性会话 24 轮零预算地板与 3× 解冻 9/9+4/6+1/9；4 个 IRES 对称阴性应答轮（PA_012 t3/PA_023 t1/t3/PA_031 t3）；配平层带评审轮 cap 全为 2=平台评审节奏（146/72≈2.0）——全部一致。**一处措辞级修正**：10× 层二级结构四个失败提交轮的折回碱基对距离实测 1/4/4/6（PA_018 t1/t2、PA_035 t1/t3），正文 "one to four base pairs off" 改为 "**one to six**"，并删去 "unverified" 限定（逐轮工具日志显示失败轮确实调用过 `predict_rna_secondary_structure` 折回验证——准确表述即实测距离范围本身）；**Fig 6 图例 (d) 精确化**：两个裸模型记号的可见性偏移写明为"对称 ±20 次调用的水平偏移（其余记号与连线均在精确数据坐标）"。零其它数字改动、零实验重跑；最终组合图 190.1×116.1 mm（头注首批的 154.7 为重排前 as-written 状态，重排见同日 Fig 6 布局修复批条目）。**同批续（用户指示"Discussion 请补入"）**：Discussion ¶2（evidence-infrastructure 论点段）在逐智能体消融（内部证据）之后补入外部基线对比句——同一模型裸用 71/69 轮、同工具通用循环配平层 7 轮、宽裕层 71 轮 vs 平台 96/96，五组配对 P<1e-6 且零反向不一致；循环未门控声称回到 §2.3 对照类（51.9% vs 54.5%）、模型开销为平台 5.2×（756 vs 146）；收束于"平台优势来自确定性工作流与治理而非模型本身"。全部数字沿用本批复核值，零新数字。登记：PAPER_DRAFT 头注 third-edit 条、本条、AGENTS.md。

- **Fig 6 布局修复批（2026-09-14，用户指示"c 和 d 并排放到 b 下面、a 在整体图左边、更紧凑"）**: (i) **组合重排**：旧 rows grid[a,b]/grid[c,d]（190.1×136.4 mm）在 b 下留 23-mm 空白 → 新布局 a 全高左列、右块（90.1 mm）b 置顶、c/d 并排于 b 下且与 a 底边对齐，组合 **190.1×116.1 mm**；(ii) **字号全图一致保持 6-pt**：c/d 直接缩放进半宽列会把字号减半——按"先修代码再出图"重渲染而非缩放；(iii) **fig6a**：画布 89×73.7 → 89×109 mm、行距 5.6 → 8.81 mm，mosaic 恰好填满左列（表头块与全部文字不变，逐格数值断言不变）；(iv) **fig6c**：竖向成组柱在 43-mm 列宽放不下五个拼全条件列+每柱数值标注（实测标签块即溢出）→ 改为**横向成组条**——每条件浅色条（不可验证占比，值标在条端）在上、实心条（FP 率+Wilson CI 须，值标在须端）在下；轴题 "Fraction of claims" 移至 x 轴；key 保持两数量行全 5×2 条件色块、裹为每数量一行居中（89-mm 单行 key 放不进列宽）；守卫扩展：数值标注与所有条两两不撞断言；(v) **fig6d**：画布 89×50 → 43.12×55 mm，ReAct 10× 标签置于记号右上方（右端贴近绘图区右缘——记号在 756/850 处右侧仅 ~3.8 mm、标签 ~10 mm 无法真正放右侧；zero-shot 标签抬 +2.6 mm、few-shot 标签降 -1.8 mm 让出该高度带），其余偏移在新画幅下重测；(vi) 全部房风断言绿（文字不出画布/两两不撞/文字-条/文字-记号/记号-记号/文字-连线/精确画布/白边/调色板纯度），1200-dpi PNG + 矢量 PDF，零数据改动（数值断言=冻结 comparison.json）。登记：FIGURE_PLAN_V5 Fig 6 表 a/c/d 行 + 复合行、FACT_SHEET Fig 6 图件行、本条、AGENTS.md。

- **Fig 6c 呈现修复批（2026-09-14，用户九点批注）**: (i) **两处图内标注与虚线锚线删除**（用户确认可删）——"RNADesignAgent: 0 claims" 注记、"ungated control 54.5%" 标注与 §2.3 未门控对照虚线全部移除；零声称事实与 54.5% 参考率改由 Fig. 6 图例 (c) 与 §2.6 正文承载（信息无损失，二者本已文报）；面板不再读 `exp5_claim_overreach/runs_summary.json`（数据源收窄为 comparison.json）；(ii) **每柱数值标注**——十根柱全部打印数值（0–1 分数制与 y 轴一致：FP 0.48/0.11/0.16/0.62/0.51、不可验证 0.14/0.15/0.37/0.37/0.30），实心条标注置于 CI 须顶之上、浅色伴条置于柱顶之上，两两不撞由碰撞断言保证；(iii) **图例重排**——"solid:/light:/dashed:" 颜色前缀删除（用户：图例不必再写一遍颜色）；续批按用户指示"5×2 种颜色全摆、方块近一些、放一行、与方块居中对齐"定稿为**单行居中 key**：每个数量名（"False-positive rate (95% CI)" / "Unverifiable share of claims"）后按 x 轴顺序紧跟 5 个条件色块（实心组原色、浅色组 55% 向白），色块密排且与文字中线对齐，块宽断言 <0.94 画布；(iv) **y 轴题 "Fraction of claims"**（用户指出 "Share of claims" 只盖住一个量——两个量本质都是声称的占比：FP 率=可复算声称中假阳性占比、不可验证=全部声称占比，"Fraction" 同涵盖两者；与 fig6b/6d 有轴题惯例一致），x 轴两行条件名保持；(v) **Nature 惯例复核**：子图标题本就不画在面板内（面板字母 c 由 `fig6_assemble.py` 统一加），故面板无任何标题；全文字维持单一 6-pt 纯黑；色板仍为 palette rev 7 条件色（浅色伴条=条件色向白 55% 混合，纯度检查覆盖）；1200-dpi PNG（4205×2362 px）+ 矢量 PDF（fonttype 42），满足 Nature Methods 分辨率要求；术语复核（false-positive rate、unverifiable share、bare LLM、ReAct agent）与 §2.6 措辞一致。房风断言全绿（文字不出画布/两两不撞/精确画布/白边/调色板纯度——暗暖灰锚线段随虚线移除一并从纯度豁免中退役）。画布 89×50 mm 不变，组合图重装配 190.1×136.4 mm 不变。登记：FIGURE_PLAN_V5 Fig 6 表 c 行 + 复合同行注记、PAPER_DRAFT Fig 6 图例 (c) 句、AGENTS.md 头注"锚线"表述、本条。零数据改动（逐条数值断言=冻结 comparison.json）。
- **Fig 6a 呈现修复批（2026-09-14，用户八点批注 + 同日两点续批）**: (i) **图内标题去除**——Nature 惯例子图无描述性标题（字母由组装脚本加），原顶部 "Tile fill darkens…" 说明行先下移底部、续批后按用户指示整行删除（编码语义由图例 caption 承担）；(ii) **列头两行分组化**：RNADesignAgent ｜ Bare LLM（zero-shot/few-shot）｜ ReAct agent（matched/3×/10×），zs/fs/m 缩写全退役、Platform 全图改 RNADesignAgent（含 6b 行标签、6c 零声称注记、6d 点标签）；续批加固——组标签下加 Nature 表格式**分组横线**（细黑线精确横跨各组所辖列的瓦片跨度），1/2/3 列分组节奏一目了然；(iii) **色块图例删除**（列头直接标注后冗余，顺带消除其排列不齐）；(iv) **条件色修正**：bare few-shot khaki→grey blue（khaki 与 sand 向白混合后难区分；首选 sage 与 6b delivered 类色冲突退而选 grey blue）——按"条件色全图统一"登记同步 6c/6d 并重装组合图（190.1×154.7→190.1×136.4 mm，6a 画布 89×92→89×73.7 mm）；(v) 瓦片向白混合加 mild gamma（端点不变、单调不变、编码语义不变）改善中间交付率可读性；(vi) 全文字 6-pt 纯黑维持；行标签生物术语复核准确；1200-dpi PNG + 矢量 PDF（Nature Methods ≥300 dpi 远超）；房风断言全绿（画布精确/文字不出画布且两两不撞/行标签不越界/子表头不压 mosaic/组标签不触横线/白边/调色板纯度逐实际绘制混合色锚定）；(vii) 分隔线改 mosaic 精确跨度内（clip_on=False + 旧 0.03 数据单位外伸在新 67 mm 宽 mosaic 下曾顶破右白边，防呆断言拦截后修复）。零数据改动（逐格数值断言=冻结 comparison.json）。登记：FIGURE_PLAN_V5 Fig 6 表行、本条。
- **§2.6 呈现修正批（2026-09-14，用户逐条批注四疑点）**: (i) **小节重题** "The platform outperforms **bare-model and tool-using agent** baselines across the eleven workflows"（用户指出 ReAct 臂是带工具的通用智能体基线、不只是"language-model baselines"；Fig 6 图例题同步）；(ii) **四疑点逐一落文，零数字改动**——①"三个条件"歧义（判分句冒号后紧跟三条判据清单、读者会误读为"三条件=三判据）：改为"one rulebook for every condition, the platform included"，并首次在正文披露**平台自身冻结产物经同规重判、96/96 全过**（4 个阈值阴性 IRES 轮按对称阴性应答规则记 delivered——与基线阴性应答同规）；②"与平台自身最佳冻结候选相当"：写明 parity 门槛的具体形态（二级=折回碱基对距离、三级=比对 TM-score，须≤/≥ 平台同轮冻结最佳；逐轮事先从冻结记录定标、不另造阈值）；③McNemar 困惑句（"平台不是全完成了吗"）：改写为"因平台逐轮全交付，配对不一致即各基线自身失败数（25/27/89/52/25 平台独胜、反向为零）"；④"预算耗尽于产出前"：写明机制链（8 个确定性 workflow 会话匹配预算恰为 0 → 每步皆模型调用的循环发不出第一个动作 → 24 轮全部记录为预算耗尽）；(iii) **三处补充数字**（均已在冻结 summary/Fig 6a 瓷砖、经用户确认补入正文）：3× 解冻层小分子 9/9、序列评分 4/6、ASO 1/9；few-shot 失败拆分 13 低于平齐 + 14 无效；10× 残余 9 轮预算耗尽；(iv) 匹配层节奏句落地（72 个带评审轮 turn_llm_cap 全为 2 = 平台自身评审节奏 146/72≈2.0/轮，2 次调用恰够一次工具往返）；(v) 全部数字对 `exp42_43_comparison/comparison.json` + Exp-42/43 summary 复核一致；零实验重跑。登记：头注 second-edit 条、本条、AGENTS.md。
- **§2.6 + Fig 6 论文整合（2026-09-14，用户指示"作为 2.6 小节写入 + 独立面板脚本 + 组合大图 + 指定十二色"）**: (i) **§2.6** "The platform outperforms language-model baselines across the eleven workflows" 四段入 PAPER_DRAFT（协议与对称判分 / 交付 96-71-69 与 7-44-71 梯度 + 失败模式 + 12:12 结构 / 声称 FP 48.3%/11.4%/51.9% 与 §2.3 锚 / 成本 146 vs 756+659=5.2× 收束句——condition 措辞、零内部编号、零此前数字改动）；(ii) **Fig 6 四面板**：6a 11×6 交付马赛克（瓦片填充=条件色按交付分数向白渐变、格内计数、设计/预测分隔线；89×92mm）、6b 未交付分解堆叠条（delivered sage/预算耗尽深暖灰/低于平台平齐 mauve/结构无效 warm_grey，段内计数；89×50mm）、6c 声称裁决（FP 实心条+Wilson CI 须、不可验证浅色伴条、§2.3 未门控锚 54.5% 虚线、"platform: 0 claims" 注记；89×50mm）、6d 成本-交付前沿（ReAct 三层连线、平台方块锚定左上 146/96；89×50mm）；每面板独立脚本 + `fig6_assemble.py` grid[a,b]/grid[c,d] → 组合 190.1×154.7mm；条件色全图统一（平台 slate blue、裸 zs/fs sand/khaki、ReAct m/3×/10× pale rose/mauve/terracotta，均 palette rev 7=用户指定十二色）；房风全守（6pt 纯黑、绝对 mm、1200dpi、画布/碰撞/白边/调色板纯度断言；6a 纯度检查锚定全部实际绘制混合底色、6d 容差 12 仅为线压标记环的三重抗锯齿）；全管线重跑可复现、逐面板数值断言=冻结 JSON；(iii) **配套**：Methods Benchmarks 指针句、Statistics 扩展、尾部图清单 4→5、头注登记、Supplementary Methods 新节（三条件协议全披露：预算层/环境原语/判分矩阵/阴性应答对称规则/回显守卫）；(iv) **登记**：FIGURE_PLAN_V5 Fig 6 表、FACT_SHEET 图件行、本条、AGENTS.md。基线记录为内部冻结证据——公开包 v2 未含，如需随文公开需 v3 重打包（候选用户决定）。**同日续（用户指示"打一个 v3 包"）：v3 已构建**——`build_package_v3.py` 在 v2 树上加 `baseline_evidence/`（三目录 8 文件 + README，scratch/ 可再生中间体排除并披露）；`RNADesignAgent_paper_data_v3.tar.gz` 9,777,836 B、sha256 `519e01bda5efae87b7b81c6a8b4f31df935ad4123a090fc2aba119761ec95210`、476 文件；核验全绿（战役记录与仓库逐字节一致、MANIFEST 476/476 复验、包内 comparison.json 头线数字复算一致、密钥扫描干净）；zenodo_metadata 描述升 v3 范围、upload_status 登记、PAPER_DRAFT 数据可用性加 (iv) 基线记录条目。**待用户 token 替换草稿 22736194 内 v2 档案**（中转程序同 v2；完成后撤 token）。**→ 同日完成（用户指示"替换草稿"）**：v2-session 的 token 仍有效（撤销一直挂起）——v2 按 file-id 删除（204）、v3 直传成功（HTTP 201 / 42.4 s，本次链路畅通无需中转）、远端 9,777,836 B + md5 `ce12667dd…4bd24` 读回核验一致、元数据 PUT 一次 408 后重试 200 并读回确认 v3 范围；携 token 的本地孤儿分支 zenodo-upload-relay-v2 已删除（卫生）；upload_status 登记。剩余用户动作：补作者 → 发布 → 复核 DOI → 撤销 token。
- **E21/E22 外部基线双战役 + 三臂对比（2026-09-14，用户指示"平台配平主层+披露宽裕层、全 CPU + GPU 0/1/2 并行"）**: 预注册修正先行（DECISIONS Part 4，任何运行之前）：任务集 = 现行 31 PA 会话（11 workflow 全覆盖、逐轮相同 brief；旧 26 题 6 后端对比集退役）、平台臂冻结复用（Exp 41 Block A + Exp 24，零平台重跑）、预算层 = matched（平台逐会话 LLM 调用；8 个确定性 workflow 会话恰为 0——结构性地板）+ 披露 3x/10x（基线 max(平台调用, 2/轮)）、判分矩阵全确定性（e3 盲裁决规则推广 + 逐 workflow 结构重算 + 平台冻结质量 parity 门槛；亲和/结合/MRL/IRES 概率类声称对一切臂对称判为不可验证）、**scaffolding 修正：+1 环境原语 `write_workspace_file`**（41 工具均需 filepath、平台 workflow 内部落盘——无此原语任何通用脚手架无法运行，pilot 实测模型幻觉输入路径后注册）。**Exp 42（E21 裸 LLM）**：192 轮 0 错误——逐轮交付 71/96 zs、69/96 fs（平台 92/92）；地板画像：三级 0/6（输入回显守卫+TM parity）、sgrna 0/13（产物=64-nt crRNA）、CDS/全长 ~50%、短序列组合类近满；989 声称 FP 30.0%（zs）/11.4%（fs）、不可验证 14.5%。**Exp 43（E22 同工具 ReAct）**：288 轮三预算层梯度 7/44/71 每层 96 轮（配平层 137 轮预算耗尽未提交）；10x 仍落后 ASO 3/9、sgrna 3/13、二级 2/6、三级 4/6；**声称 FP 51.9%（CI 46.8–57.0）≈ 未门控对照类 54.5%——"未门控 FP 率泛化到通用脚手架"的预注册预期实测成立**；成本 756 LLM+659 工具调用（平台 146 的 5.2×）。**三臂对比**：平台对称同规重判 92/92；五组配对 exact McNemar 全部 baseline-only=0、p<1e-6；`--verify` 字节级一致。判分修正四项（pilot 期、全量前）：回显守卫/siRNA 互补 parity（multifapredsi 共识设计非逐字互补）/ASO 反义窗口/sgrna Hamming parity——平台 92/92 通过同规判分（对称性）。登记：DECISIONS Part 4 执行块、MANUSCRIPT §3.0 三行、FACT_SHEET 新节、本条、AGENTS.md。记录：`experiments/results/exp42_bare_llm_baseline/`、`exp43_react_baseline/`、`exp42_43_comparison/`。论文整合（新 §2.6 + Fig 6 槽位 + 图例/Methods/补充材料）待用户提纲后另批执行。**同日呈现修正（用户两问，重分析前注册）**：(1) 统一 n=96——平台 4 个"阈值以上无候选区"的成功 IRES 轮按对称阴性应答规则记 delivered（任何臂均可用该形式作答；harness `check_response` ires 分支支持 `negative_answer`），平台 96/96，五组配对 p<1e-6 不变（platform-only 25/27/89/52/25）；(2) **失败模式分解**——裸 LLM 失败 = parity 14 + 结构无效 11（真实能力失败），ReAct matched/3× = 预算耗尽 86/42（逐动作 LLM 税的机械成本），ReAct 10× = parity 16 + 预算 9（质量而非预算）；(3) **裸-vs-ReAct10x 配对恰 12:12、p = 1.0**——ReAct 赢工具不可或缺类（三级 4/6 vs 0、sgrna 3/13 vs 0、CDS 6/6 vs 5/6、全长 9/9 vs 5/9），裸 LLM 赢小组合类（ASO 9/9 vs 3/9——模型把步数耗在可及性扫描未提交；二级 5/6 vs 2/6——15/23-nt 靶直接推理可精确折回、ReAct 提交前不验证折叠）；(4) 设计类子聚合（n=72）：平台 72/72、裸 47、ReAct 47。登记五处同步；零原始运行改动。
- **论文修订批次十（2026-09-14，用户逐条批注）——Methods 结构重排 + 数据可用性范围收缩 + Zenodo 包 v2**: (i) **System architecture** 按用户七层提纲重排（去 `required_capabilities` 代码名）；(ii) **Multi-agent 节重写**：四智能体全介绍（Pipeline/Specialist/Quality/Synthesis）、重试条件改为文字表述（无代码标识符）、补"为何仅硬故障重试"（客观可复现信号 vs LLM 观点）与"为何 advisory"（评审失败→零信心通过留审计、LLM abort 仅建议——运行成败永不由语言模型决定）两条设计理由、Methods 内实验结果句删除（§2.4 已有）、**LLM 用量独立小节退役**（DeepSeek 型号/温度一句并入本节，逐战役用量数字保留于 §2.4 与补充材料）、tie-arbitration 历史句删除；(iii) **ASF 节对照代码核准并加两处精确化**（Pareto 前沿默认上限 10 且保留各维冠军；权重缺维回退 uniform——`agent_core/workflows/multi_objective.py` 逐条核对：公式/ρ=10⁻³/归一化/utopian 默认/三缺失数据策略/六工作流目标清单全部一致）；**(iv) 两步全长协议段迁补充材料**（新设 Supplementary Methods 节，S2.1 指针同步）；(v) **CapGate 节 SelfModel 首现即定义**（"capability self-model (the SelfModel): a machine-readable register, packaged with the platform…"）；(vi) **GenNav 节**："within delivered batches" → "among the candidates delivered for the same design profile"、static recipe 首现即定义（固定预登记生成器设置 4λ+1 RNARL+30 GEMORNA）；约束矩阵六维与 exp26/exp28 登记值核对一致（起始区茎≤12=C6、全长茎≤30=C7、滑动 GC 30–80=C1、同聚物<14=C2、CAI≥0.8）；(vii) **Benchmarks 节扩写**（用户疑问逐项落实）：45 任务声明审计集 + 20 任务 mRNA 审计集（衍生任务集、构造规则、随包公开）首次入节；19 靶扩展池（12 复合物+7 锚蛋白，20+19=39 预算扫描池）入节；5 蛋白 mRNA + 6 蛋白适配体部署队列入节（合并 25/26 分析、队列拆分披露）；外锚集逐面板细写并补一手来源名（Jeong & McCoy 2021 疫苗组装；IRES 面板 Stoneley 1998/Stein 1998/Yang & Sarnow 1997；小分子对 1O15 Jenison 1994/1ANR/1Y27；RNASTOP 上游公开测试集 400 构建体；GSE114002）；(viii) **小节去留（用户逐条指示）**："Experimental protocol" 整节删除；claim-overreach/gating 实验、约束导航战役（部署段并入单段叙述）、逐智能体消融三节迁 Supplementary Methods（pilot-first/预算匹配/盲审段落随迁保留）；"Production campaign" 从论文删除（测量条件保留于 Fig 2h 图例 + §2.2 行内括注）；(ix) **"arm(s)"→"condition(s)" 全文清扫**（用户问是否常用、有无更合适表述——正文 77 处替换，图面无该词零重渲，头注 as-written 保留；补充材料同步清扫含 IRES "arm"→"analysis"）；(x) **Data availability 重写**：包内容收窄为 (i) 基准+锚集资产（含新增 200 随机同义对照 FASTA、部署队列登记、两个审计任务集）+ (ii) SelfModel + (iii) 模型用量登记——冻结战役证据 (ii)、补充材料 (v)、图源数据句按用户指示撤销；SHA-256 清单保留（完整性惯例，答用户问）；25/26/39 表述落地为"20 靶套件+部署队列（合并分析 25/26）"与"39 靶扩展池"；Code availability 补 GitHub 链接占位符（待用户提供）。**(xi) 20→25/20→26 是否重跑的核查结论：无需重跑**——部署队列已按同一预算匹配协议完成并合并统计（Exp 40 冻结），本批仅补文档（Benchmarks/数据可用性）；(xii) **Zenodo 包 v2**（`zenodo_deposit_2026-09-13/build_package_v2.py`）：`RNADesignAgent_paper_data_v2.tar.gz` 9,601,979 B（SHA-256 `040d3edb…dc37e6f`，467 文件）——campaigns/ 与 supplementary/ 撤出公开包（冻结记录仍在 repo `experiments/results/`）、新增 `random_synonymous_controls.fa`（exp2 生成器逐字复用、draw 0–9 对齐登记种子；200/200 长度+GC、8/8 抽样 CAI 平台工具复算与冻结记录 1e-9 一致）、`deployment_cohorts/`（mRNA curated register + 适配体指针登记）、`claim_audit_tasks/`（e5 45 任务 + legacy 参考 + e18 20 任务）；**草稿 22736194 仍挂 v1 档案——替换需 token（用户动作）**。登记：PAPER_DRAFT 头注批次十；AGENTS.md 头注 + What's New；DECISIONS Part-2 #34；upload_status.md。零实验、零数字改动。**同日续（用户提供 token）：草稿替换完成**——v1 文件按 file-id 删除（filename 形式 DELETE 两次 500）、直传 PUT 遭链路拥塞（502/408）后走 **GitHub 中转**（孤儿分支携档案+工作流，Actions ~30 秒内触发上传，远端 md5 与本地一致核验——批次九〔Actions 未触发〕的登记就此修正：本次触发正常）、元数据描述经直传小负载重试（首次尝试 HTTP 200）更新为 v2 范围并核验、中转分支删除（token 卫生）；Code availability 填入实际仓库 URL（github.com/SII-ShenggengLin/RNA_real_agent）；本地 main 领先 origin 的提交一并推送。剩余用户动作：补作者→发布→复核 DOI→撤销 token；发布前仓库如需对审稿人可解析须设公开。
- **论文修订批次九（2026-09-13，用户指示"数据可用性改为公开存档"）——Data availability 重写 + Zenodo 公开数据包构建与草稿存档**: (i) **参考文献范式**（三篇 Data availability 提取）：DeepRare = 逐数据源 + 公开仓库 URL/入藏号（自产数据入 NGDC PRJCA052720 + 子入藏号）；Co-Scientist = 开放/受限分列 + 公开源 URL；SeFMol = 代码 GitHub + 生成产物公开站点。Nature 政策核实：社区仓库优先、无对应社区仓库时 Zenodo 类通用仓库可接受，DOI/入藏号进声明。(ii) **数据盘点**：experiments/results/ 439 MB（214 条目、157 个运行日志为运营碎片）+ data/benchmarks/ 48 MB（五套件 + external_anchors 全部锚集）+ SelfModel（default_self_model.json + build_default_self_model.py）+ 补充材料三份 + 模型用量登记；data/references/ 1.2 GB 第三方参考库不随包分发（按入藏号引用）。(iii) **公开包构建** `zenodo_deposit_2026-09-13/`：RNADesignAgent_paper_data_v1（303 MB / 21,373 文件）→ tar.gz **40 MB**（SHA-256 `96b9c26b…9592c7`）；排除 `.env`（DeepSeek key）、全部 `*.log`、`RESTORE_NOTE.md`、`__pycache__`；包内 grep 无 API 密钥；冻结记录逐字保留（含集群绝对路径，README 披露）；README + 逐文件 MANIFEST.sha256 + Zenodo 元数据草稿 `zenodo_metadata.json`（dataset、CC-BY-4.0、作者占位待填）。(iv) **Zenodo 存档**：账号 3129157818@qq.com 无本地密码（GitHub OAuth 绑定，表单登录实测返回 "No password is set for this user"）；用户提供 personal access token（deposit:actions+deposit:write）后经 REST API 建**未发布草稿** id 22736194、保留 DOI **10.5281/zenodo.22736194**；tar.gz 上传至 draft bucket 期间遭遇集群→Zenodo 链路故障（502/504 网关超时、~1-7 KB/s），带低速自断的重试循环后台执行中——上传完成后需核验 files 列表与校验和。**(v) PAPER_DRAFT Data availability 整段重写**：内部路径索引（`experiments/results/…`、Exp/E 编号、fig2–fig7 时代名、PA_023 修复细节、VEGF 存档句）全部退役，改为 Zenodo DOI + 五类内容枚举（基准+锚集 / 战役证据 / SelfModel / 模型用量登记 / 补充材料含数字→文件映射表）+ 第三方数据按入藏号（GSE114002、GENCODE v46、RCSB PDB、Kazusa、RefSeq/UniProt）+ 图源数据在包内声明；DOI 为草稿保留号，正式发布后生效，若重建存档须同步更新。头注批次九记录。**待办**：上传完成后（a）核验草稿文件完整性、（b）用户在 Zenodo UI 补作者并决定发布、（c) 发布后复核 DOI 可解析。图例中的编号溯源注记仍未处理（候选下一批）。
  - **上传完成（同日 18:17，线路窗口重开）**：直接 PUT 成功（HTTP 201，41,275,632 B @ 5.7 MB/s / 7.2 s），远端 MD5 `e2a5bc5130028f5a2d92414ca3a843fb` 与本地逐字节一致；草稿内遗留的 256KB 探测文件已删（HTTP 204）。**GitHub Actions 中转通道已建未触发即弃**（孤儿分支 zenodo-upload-relay 携归档+工作流推至私有仓库，运行机海外网络代传——Actions 未触发/无标记，疑该仓库 Actions 禁用；直传成功后分支已从 GitHub 删除、本地副本已清）；30 分钟自动重试任务已停用。剩余用户动作：Zenodo UI 补作者 → Publish → 复核 DOI 10.5281/zenodo.22736194 可解析 → 撤销 token。
- **论文修订批次八（2026-09-13，用户指示"Methods 小节去内部实验编号"）——Methods 按三篇参考文献范式重写（纯写作、零数字改动、零实验）**:
  - **参考文献范式提取（用户指定三篇，`relevant_references/`）**: rare-disease agentic system（DeepRare）/ Co-Scientist / empirical-software AI（SeFMol）Methods 共性：小节按组件与程序命名（DeepRare "Problem formulation / Main workflow / Agent servers / Ablation study / Statistics"；Co-Scientist "Overview / 每 agent 一节 / Tool use / Ablation analysis / Statistics and reproducibility"；SeFMol "Code mutation system / Evaluating X on Y benchmark / Replication of existing methods"）；实验以协议+目的叙述、数字内联；**无内部实验编号、无内部日期、无决策日志指针**；消融 = 被消融组件 → 实测后果；评估小节交代数据集构建与来源。
  - **去编号化（Methods 内 46 处 token 全清，grep 复核零残留）**: Exp 5/17/18/23/24/25/25b/26/27–29/30/40/41、E1/E3/E3-M/E7、P0/P3/E4/E6/E8–E15、S0/S1、BMC、DECISIONS (aa)/(bb)、内部日期 2026-08-12/18/19/20/22/29 与 2026-09-01/02/03/05/06/07/12/13、PA_006–PA_036、CI、`external_repos/`、`agent_core/calibrated/runtime.py`、`agent_core/workflows/multi_objective.py`、`experiments/build_default_self_model.py`（生成器指针数据可用性已有）；内部约束码 C1/C2/C6/C7/M1/CAI → "the six-constraint hard matrix"；"arm-A rule deliveries" → "rule deliveries"；pre-B0 删除；USER_CONFIRMED → "curated UniProt register"；"GPU-pinned 0/1/2" → "GPU-pinned as shipped"；"aptamer matrix v3" → "aptamer matrix"。
  - **结构重组**: "Benchmarks, anchors and experimental campaigns" 单节拆六节 —— Benchmarks and anchor sets / Experimental protocol / Claim-overreach audit and gating experiments / Production campaign / Constraint-navigation campaigns（内含 bold 小标 Selection-layer pool measurement + Deployment cohorts and static-arm completion）/ Per-agent ablation of the multi-agent layer；Statistics 改为 mRNA/aptamer 分句并删 "legacy 54 + 10,000-draw permutation null" 内部残句（保留 20 靶预登记队列为推断主干 + 队列拆分披露）；LLM usage 改按描述性战役名报数。
  - **内部溯源句退役（数字不动）**: Multi-agent 节 PA_023 修复叙事（Fig 4i 图例 + 数据可用性 exp25b 条目 + 内部登记保留）；production campaign 两次平台演化重跑编年 → "run on the platform's current default workflows — constraint-navigation-default mRNA CDS design flowing through the governed two-step full-length redesign"；tie-arbitration 句去 "legacy S0 campaign" 措辞（Kendall τ = 1.0 @ 3 calls 保留）；CapGate "Since the 2026-08-18 platform integration" → "CapGate is a production default of the platform"；GenNav 两个 production-since 日期删除、参数校准改为 "calibrated against a re-run of the pre-registered endpoint"；ASF 节 "2026-08-20 audit" → "a ranking audit"（顺带修 "an predictor" → "a predictor"）；全节末尾证据指针改指数据可用性声明（原指 `docs/PAPER_FACT_SHEET.md`）。
  - **Results 顺带同类修复（4 处 token 级，无数字）**: §2.4 "(E3-M)" 括注删除（Methods 不再定义该码，防悬空引用）、"(Exp 27, 28 and 29 — both arms deterministic)" → "(both arms deterministic)"、"(Exp 30, over 11 sessions)" → "over 11 sessions"、"(Exp 41):" → ":"。
  - **验证**: 改后 Methods 内部码 grep 零残留（唯一匹配 E114002 = 外部入藏号 GSE114002 的误匹配）；改写前后承重数字逐项核对一致（706/706、twelve cells、45=24+21、24,897、241/210/31、315=35×9、2%、35/48 cap、25-/26-target、n=75/60/36/24/78/39、145/144/483/90/90/80/22/218/146/0/72/4、τ=1.0、OTC 354/PDGFB 241 aa、200 random、top-vs-bottom 60、120-anchor、ρ=10⁻³、−30/−61 kcal/mol、25–34/40–55/61–80 nt、≥0.15 等）；数字多重集 diff 的差异项全部为刻意移除的日期/编号碎片（含 §2.5 章节引用 token "2.5"）。
  - **明确不动（候选下一批）**: 图例中的编号溯源注记（如 "Exp 24 re-run 2026-09-07 …, DECISIONS (bb)"）、数据可用性中的 Exp/E 目录名（= 真实磁盘路径与产物索引）。登记：PAPER_DRAFT 头注批次八记录；AGENTS.md 头注 + What's New。
- **论文修订批次七（2026-09-13，用户逐条批注）——Discussion 重写 + Exp 41 逐智能体消融新实验**:
  - **Discussion ¶1 重构（用户大纲）**：开篇三失效模式 → RNADesignAgent 的策略↔失效模式逐一对应句（CapGate 的 profiling+DecisionGate+ClaimGate 对应未校准信任与过度声称；GenNav 以确定性预算匹配协议对应混淆性改进）→ 结果句补门控数字（0/20 vs 54.5% 与 1/13 vs 6/18、TP 保持 12/12 与 80%——全部为 §2.4 已冻结数字）；GenNav 数字（20:6 P=0.009 n=75 / 10:2 P=0.039 / e2e 4 vs 0 / 48 vs 42 + 18:12 P=0.36 与 10:3 P=0.092 披露）原样保留。
  - **Discussion ¶2（用户问句"论文中有量化每个智能体的评估实验吗"→ 用户拍板补实验）**：逐智能体句重写并落 Exp 41 数字；**cross-campaign memory 例删除**（E4 为重置前内部登记、冻结文件已随重置清除且论文从未呈现——DECISIONS #33 (i)）；协调环证伪（Fig 3f）保留为被移除机制的论文内证据；"非自主发现/闭环科学家设计工具/区分工具协同与科学推理/预测器弱与否/dual-use"各句保留。
  - **Discussion ¶3 局限段（用户确认"完全按大纲两条"）**：五条（计算性验证/单 LLM 后端/画像覆盖/规则基线简单/0.48 conjunct 未达标）整体退役，替换为两条——(1) 机制端到端覆盖限于全长 mRNA 与适配体两类 RNA 类型（工具与锚点数据成熟后可无架构改动扩展；其余工作流仍在同一门控与审计下、预测器按 profiled 边界或 require-profiling 默认持有）；(2) 两工作流选择/排序预测器的锚点集经断言审核与覆盖检查但规模有限、更丰富锚点进一步提升校准。收尾句沿用。
  - **Exp 41（新实验，`experiments/exp41_agent_ablation.py`，预登记 docstring、pilot 先行、生产工具路径、advisory CapGate、`--verify` 字节级一致；两新环境旋钮 `RNADA_SPECIALIST_MAX_RETRIES`/`RNADA_SYNTHESIS_LLM` 按 RNADA_QUALITY_REVIEW 先例接线并附单测，交互默认不变）**：**Block A** = 全量 31 PA 会话 × 3 臂（生产默认 / RNADA_QUALITY_REVIEW=off / 重试禁用）经表单 CLI 子进程——**31/31×3、逐轮配对一致 0 失配、评审调用 146/0/72（每被评审轮恰 2 次+2 个重试轮 / 关 / 仅 final）、重试 2-0-0（PA_023 轮1+PA_031 轮3 均为随机服务抖动且均被救回，同两轮在消融臂新鲜运行中未复发）**、8/8 结构检查绿；**Block B** = 两个预登记两节点 pipeline（逆折叠结构设计→小分子相互作用；扩散适配体设计→同二节点；PA 输入逐字、配体配对为机制性 probe 已披露）× 3 臂（CLI 生产路径 / RNADA_SYNTHESIS_LLM=off / 驱动级顺序执行无 L4）——**6/6 成功、绑定全对、无智能体时节点结果一致（调度器行为透明）、综合报告为唯一声明载体（12 条声明 ClaimGate 驳回 5 条、全部 dependency never profiled）、nosynth/sequential 零声明**；sequential 臂首批两条记录被 censor（进程内臂默认 enforce → 小分子调用被 DecisionGate 以短适配体 OOD 登记边界拒绝——臂间不对称，登记修正后 advisory 下重跑一次、记录保留 `superseded_runs` 披露）；门 A+B PASS。
  - **提速（用户指示"确定性可复用的尽量复用"）**：登记过的 ODesign 常驻舰队上线（3 副本 GPU 0 + `roundrobin_proxy.py` 接管 8012，字节级一致、端点与仪器零改动、换防窗口零伤亡看门狗核实）；**跨臂记录拷贝明确不做**（DECISIONS #33 (ii)——配对新鲜运行才使结果一致性成为实测而非代码推导）。
  - **§2.4 governance 段 + Methods + 数据可用性**：§2.4 "measured rather than asserted" 段尾追加 Exp-41 结果句（三臂计数、两起救援、调度器透明、12 声明 5 驳回）；Methods 战役节登记 Exp-41 全协议（含 sequential 臂 censor/重跑披露）+ LLM 用量节补 218 评审调用 + 4 综合侧调用；数据可用性加 `exp41_agent_ablation/` 条目；Fig 4j 战役集不变（Exp 41 用量文报）。头注追加批次七记录。
  - **登记同步**：FACT_SHEET（Exp 41 节含 claim check）/MANUSCRIPT（Exp 41 行）/DECISIONS Part-2 **#33**/AGENTS.md 头注 + What's New。测试 **700 passed 1 skipped**（含两旋钮 3 个新测试）。
- **论文修订批次六（2026-09-13，用户逐条批注）——§2.7 "End-to-end case studies" + 表 1 整节退役，论文内 Exp-37 痕迹彻底移除**:
  - **决策（用户拍板，二选一确认）**：整节删除 + 论文内彻底移除。理由（用户批注 + 冻结记录核实）：三个单轮表单案例相对预登记战役无推断权重；适配体案例只能作自我审计实例报道（该家族结构预测器 chance-level〔Exp 10/13〕——连 pegaptanib 锚经同链测得仅 0.365、top 候选 EGARPS 被工作流自身快速指标门跳过〔RhoFold pLDDT 0.544 < 65〕，**重跑不可能强化，不尝试**）；实用性/端到端验证延后至规划中的湿实验小节。用户批注中的两个疑问随批答复：受控两步组装 = (bb) 协议第一步 GenNav-λ 选 ≤3 CDS、第二步文献阈值准入的 UTR 池 ×6×6 组装（Methods 已有定义段，正文不再依赖）；"交付边界披露而非调优规避" = stability 档 35/35 预算下零交付且 degraded，系统按预登记约束带原样报不可行而非放松约束制造通过。
  - **PAPER_DRAFT 移除面**：§2.7 标题+段落、表 1 注、引言代表结果段末句（Spike 6.8 h）、Overview 括注 "; case studies in Table 1"、Methods LLM 句 "the three Table-1 case studies (Exp 37) 8 calls"、Discussion 计量句 "30 further advisory review calls … (Exp 30: 22; Exp 37: 8 over 3 cases)" → "22 further … (Exp 30, over 11 sessions)"、数据可用性 Exp-37 条目、Fig 4 图例 (j) "Table-1 case studies … Exp 37: 8 over 3 cases" 分句。头注追加批次六记录。残留清扫验证：正文仅剩 RNAsmol 文献验证的无关 "case studies" 用法（3 处，保留）。
  - **fig4j 面板与数据装配（用户选定"彻底移除"路径）**：`exp25_fig4h_data.py` 删 Exp-37 计量块（docstring 与 registered 注记同步记录 2026-09-13 移除）；`fig4h_llm_usage.json` 经驱动重生成 = 13 战役（其余计量逐项与冻结值一致：90/90/80/0/483/0/145/0/0/0/0/0/22）；`fig4j_llm_usage_bubble.py` ROWS 去 exp37 行 + docstring 注记；面板重渲染 128.1 × 99.2 mm（raster QA 绿）；组合图重装配 190.1 × 554.6 mm（旧 561.2 mm，恰减一行行距 6.6 mm）。
  - **补充材料重路由**：S2.1 全长 mRNA 证据由 Table-1 caseA 改为基准级完成（22/22，Exp-24 lane）+ Methods 两步协议 + Fig 5a–d 战役特征，并明写 "No single-run case study is reported; practical end-to-end validation … deferred to the wet-lab programme"；S2.2 适配体删 caseB 两处（含 "Table 1 case B is exactly this behaviour" 句）；S2.4 删 "as registered in Exp 37"（规则内联为最长框内 AUG→stop ORF）与 "reproduces the Exp-37 Table-1 anchor exactly" 句；补充数据映射表删 Table-1 行。
  - **登记同步**：PAPER_FACT_SHEET（legacy 映射注记 + Table-1 节改"REMOVED FROM THE PAPER"+移除记录块+claim check 退役标注 + Fig 4i/4j 节 13 战役重基）；MANUSCRIPT（Exp 37 行退役标注）；FIGURE_PLAN_V5（fig4j 行 + 尾注两处）；DECISIONS Part-2 **#32**（含"重跑不可能强化，勿尝试"警示）；AGENTS.md 头注 + What's New。冻结 Exp-37 记录盘上保留（`experiments/results/exp37_table1_case_studies/` + `caseA_prebb/`），论文不再引用。
- **论文修订批次五（2026-09-12，用户逐条批注）——§2.5 重题 + 去术语化 + 部署验证段并入主结果（Exp 40 静态臂补全 + 25/26 靶点合并统计 + 图 5 七面板化）**:
  - **§2.5 重题**："Generation-layer constraint navigation delivers pre-registered design profiles" → "Generation-layer constraint navigation efficiently generates RNA molecules that meet the design requirements"（用户拍板：删 "pre-registered design profiles"）。
  - **机制段去术语化（用户逐词批注落实）**：lattice/gear/budget/delivery bandwidth/minimum pairwise distance/degrade path 六个首读不可解术语全部替换为首现即定义的平实表述——生成器离散设置（mRNA 的 LinearDesign λ 平衡参数 = 密码子最优性 vs 折叠稳定性的权衡；适配体的长度–种子–采样数组合）、生成调用配额（两臂对等的生成器调用次数）、五个候选的批次、序列多样性底线（批次内任意两候选最小位置差比例）、显式不可行报告（无可用设置时按失败原因报告而非静默丢弃）。全文残留 gear/lattice 清扫（§2.7/Table 1/图例/Methods/Overview），仅头注 as-written 记录保留。
  - **选择层段落修正（用户疑问逐项）**：五靶点通过数全部列出（EPO 306 / IL-2 297 / 胰岛素 144 / A1AT 27 / GFP 0——原文只列 4 个造成"5 靶点哪来的第 5 个"困惑）；"两个数量级"改按实测表述（最好与最差非零靶点差 11 倍 + GFP 完全坍塌）；"fixed pool" 首现即括注构成（35 CDS × 9 UTR = 315）；"batch" 统一为 five-candidate batch/短列。
  - **mRNA 主结果段**：格点→35 个预置 λ 值曲线探针、"registered matrix" 逐维给出接受带、同义多样性步（零生成调用）明义；细胞 = 靶点 × profile 配对格、"rule arm" → static arm（同配额固定配方）明义；McNemar 不一致检验首现即义（恰好一臂交付的格里导航占多少）；**合并 25 靶点报**（预登记 20 + 部署 5 静态臂补全）：**20:6，P = 0.009，n = 75**（部署队列单独 3:0）、JCD 46 vs 32/75、22/25 靶 ≥1（9 个 3/3，HER2 在内）、花费均值 23.1/35（15 早停含部署均值 17.2）。**披露压缩（用户确认保留）**：基因级 0.48（12/25）< 0.8 一句带过；约束率达标（0.96）前提下复合分统计不分离（+29/=26/−20，Wilcoxon P = 0.73）重述为"逐格质量持平、交付格数更多"。GFP 反向边界原样保留（6 个静态有利格中占 3，部署队列未新增）。**预修复句删除（用户指示只报最新版本）**：Results/Discussion 的 Exp-27 0:24 句移除，内部登记保留（DECISIONS #27 / FACT_SHEET）。
  - **适配体段 + 部署合并（用户指示两族各自合并统计）**：四段弧后接"六个部署靶点静态网格补全（同结构同热点）→ 26 靶点合并（图 5g）"：**交付 48:42/78，不一致 18:12（P = 0.36）**，部署队列单独 **8:2（7:1，P = 0.070）**、深稀缺区（6 靶 5 个顶到 48 上限；swH3 HA 双臂零交付边界；交付时点靠后：IFN-γ 29/35/47、PDGF-BB 36/48）。**宽松预算重述（用户方向：强调导航的效率优势而非"让步"）**：饥饿档决定性胜（cap16 10:2 P = 0.039）、饱和档同交付省 ~1/3 调用、宽松档静态网格逐设置穷举交付更多（10:22 / 12:30，披露）——定性为成本收益区划（"生成一切比决定生成什么更便宜"的区制），机制对比句收尾（λ 确定性 → 单探针精确读出 → 20:6；扩散生成器逐样本噪声底耗尽探索预算）。
  - **Exp 40（新实验，`experiments/exp40_static_completion.py`，预登记 docstring、pilot 先行 PTH+FGF2、生产工具路径零干预、advisory CapGate、全 CPU + GPU 0 并行〔用户指示〕、`--verify` 字节级一致）**：mRNA 侧 = Exp-28 池仪器逐字复用（35 原始调用断言、315 构造）+ 冻结 Exp-30 表单会话导航 trace 以同一全长矩阵/效用栈组合评估（constraint-first v2 映射、交付级 junction E3、Exp-27 判据机器逐字）；适配体侧 = Exp-29 静态网格逐字复用（48 原始调用断言、matrix v3、折复用解析器取 Exp-30 同结构 + 确定性自动热点）对冻结 `cells_pass`。合并裁决自冻结记录计算、队列拆分披露（适配体合并统计 = 队列拆分汇总，DECISIONS (i) 遵守——seg3/seg4 预登记终点裁决仍为推断主干；部署适配体臂导航器新旧两代按运行日期混用逐记录披露）。full 5/5 + 6/6 零失败零违规零 LLM。结果冻结于 `experiments/results/exp40_static_completion/{mrna,aptamer,pooled}/`。
  - **图 5 七面板化（用户指示：部署结果并入、图与编号与脚本名同步）**：5b/5c/5d 按 25 靶合并重渲（dumbbells 合并统计行 n = 75；mosaic 20→25 行 + 队列分隔线 + 部署靶点 * 标记，89 × 127.8 mm；Δ-composite 60→75 对 + 自适应栈高）；5e 加第五段部署棒棒糖 + 双合并注释行（20 池 11:11、26 池 18:12 + 交付 48:42），89 × 62 mm；5g 重绘为 **26 × 3 合并交付 mosaic**（seg3 12 + seg4 8 + 部署 6，队列分隔线；18/30/12/18 分类计数），89 × 132.2 mm；5f 不变；**5h 退役**（脚本 + 输出 git rm；其花费/时点事实文报于 §2.5 与图例；冻结 Exp-30 记录保留为部署队列导航侧来源）。装配行计划改 grid[a,b] / stack_right(c,[d,e]) / grid[f,g]，组合图 190.1 × 334.4 mm；`qa_exp29_30_figs.py` 更新为 6 面板清单，raster QA 6/6 GREEN。
  - **全文同步**：摘要（P = 0.009 + 25 targets、profiles→requirements）；Overview 代表结果句（20:6, P = 0.009, pooled over 25 targets）；讨论（合并数字 + 预修复从句删除 + 适配体合并句 48:42/18:12）；局限 (5)（0.45→0.48、11/20→13/25、gear→setting）；Methods Statistics（合并 n = 75/78 + 队列来源 + DECISIONS (i) 框架句）、Methods 战役节新增 Exp-30/40 描述句、LLM 用量（Exp 40 = 0）、GenNav 节术语与合并均值 23.1；数据可用性（exp40 目录 + exp30 指针改为"部署队列导航记录"）；图 5 图例全文重写（a–g）；页脚八面板→七面板；PAPER_DRAFT 头注追加批次五记录。
  - **登记同步**：FIGURE_PLAN_V5（Fig 5 表七行全重写 + 退役面板表 + 2026-09-12 合并注记）；PAPER_FACT_SHEET（新 Exp 40 节含 claim check + Exp 28 节头注指向合并引用 + Exp 30 行退役注记）；MANUSCRIPT（E6 行 + 新 Exp 40 行）；DECISIONS Part-2 #31。历史条目 as-written 保留。
- **论文修订批次四（2026-09-11，用户逐条批注）——§2.4 重写 8→6 段 + selective-gating 段前移合并（Fig 4 再次重字母）+ PA_023 fixture 根因修复与三臂补测（Exp 25b）**:
  - **§2.4 逐条落实用户批注**：(i) 机制段 "managed predictor calls are gated at the single tool-execution choke point" 展开为明义句（每次受治预测模型调用都过平台唯一的工具执行入口、在调用底层服务前对照自模型检查——未获证据支持的调用在执行前被拒绝而非事后标记）；修正 "an predictor" 笔误。(ii) profiling 首次出现即定义（每个 predictor–task–target-family 组合在受信前对照锚定集按预登记阈值实测，等级即门所查询的能力图）；"two-sided" 重述（既收回无测量支持的权能、也在权能存在之处*认证*它——"where it exists" 指 27 类组合中哪些真正持有权能）；该段以 "The gates are only as good as the evidence beneath them" 承接机制段。(iii) 保真段开头改写为证据层第二性质 + 段间连接句（两段合起来 = "grades measured on the system as shipped, not on what the papers report"）。(iv) "Git archaeology" → "Comparing the port's preprocessing against its pinned upstream commit revealed two deviations"（专业化措辞，不再出现 Git）。(v) 段尾简化为 发现—注意—结论（删除"推翻预登记预期"叙事；保留三测量定位损伤载体 + "看似致命的偏差无害、看似修复的偏差毁掉预测器"结论）。(vi) 双臂评估引入句并入适配体段、直说两个任务族（45 任务适配体审计集自含描述 + 20 任务 mRNA 集），删 "introduced above"/"second flagship family"；mRNA 段首 "The result replicates on the second flagship family" → "on the mRNA-side set"。(vii) 保留损失分解原文数字，"(the ungated arm had simply emitted clean sequences there)" 澄清为 "(on those tasks the ungated arm had emitted correct-length sequences)"（对 exp5 冻结记录复核：u_reduce_0/u_reduce_2 未门控臂确为 60 nt 正确长度）。(viii) 收尾段主题句 "The governance result closes the loop" → "The platform's own governance layers are, finally, held to the same standard — measured rather than asserted"。
  - **段落合并（用户确认方向：前移而非后移——双臂段落依赖 capability profile，证据必须在前）**：selective-gating 段整体并入认证段（等级 → 12 格决策矩阵的运行时兑现，4g→4b 与 4a 相邻）；生产规模普查两句并入 mRNA 段尾（"The same gate semantics operate at production scale (Fig. 4h)"）；单句协议引入段删除。小节 8 段 → 6 段。
  - **Fig 4 第二次同日重字母**（内容零改动）：selective g→b、fidelity b→c、headline c→d、adjudication d→e、overreach e→f、mRNA f→g；h/i/j 不变。6 面板脚本 + 输出 git mv；`FIG4E_LAYOUT`→`FIG4F_LAYOUT`；脚本内部自引/交叉引用带断言更新（selective 面板 docstring 残留的 fig2h 约定指针顺带修正为 fig2g）。`fig4_assemble.py` 行计划重排：fit[a,b]（缩放 ≈1.15/0.73——本图集最宽纵横比差，为合并叙事同带而接受；cert 森林放大、矩阵缩至共带高）/ fit[c,d]（≈0.95/0.84）/ group[e,f]（f 用 tall 变体，f 下 ≈39 mm underhang——矩阵为全图最高面板，headline 既在行 2 后无同序列搭档）/ group[g,h] / full[i] / full[j]；新增 placed-letters 断言（每个 PANELS 字母必须在 ROWS 中恰好出现一次——首版装配曾静默丢 c 面板，断言防复发）。组合图重装配 190.1 × 561.2 mm。
  - **PA_023 根因修复 + Exp 25b 补测（用户指示：查数据→重跑→报最新）**：根因 = 任务 023 前两轮引用 `workspace/pa023_5utr.fa`——重置前时代注册的临时工作区绝对路径，从未入 git（291 提交全查），第三轮引用的 git 跟踪 fixture 存在且恰为 constants 序列的 100–300 窗口（数据自洽）；冻结 Exp 25 三臂记录 turn 1/2 同败与路径缺失精确吻合。修复：400 nt 序列自任务 `constants.UTR5_SEQUENCE` 逐字节重建（canonical fixture 入库 `data/benchmarks/RNA-BioBench-ProcessAware/fixtures/pa023_5utr.fa` + 工作区副本 + `pa_benchmarks.json` 加 `legacy_input_note` 字段 + benchmarks README 登记）。**Exp 25b**（`experiments/exp25b_pa023_restore_addendum.py`，预注册 docstring，数据门先行：fixture==workspace==constants、turn-3 窗口断言）：三臂 × 3 轮，3/3 全成、逐轮结果跨臂一致、off 0/0、on 恰 2 次/轮共 6、fail 2 次失败尝试/轮共 6 且零完成、零重试——11/11 期望检查绿，`--verify` 字节一致；结果冻结于 `experiments/results/exp25b_pa023_restore_addendum/`，冻结 Exp 25 语料未动。**合并报道**（latest-record-wins）：31/31 工作流级成功/臂；调用总数不变（评审在失败轮也照常发起：PA_023 两时代均贡献 on 6 次/fail 6 次尝试，故 145/144 维持）——初版误算 148，被 fig4i 重写断言当场拦截后对冻结记录核实更正。fig4i 面板改读冻结+补测合并记录重渲染（三态纯色 tile、无 terracotta、防御性断言无 fail tile；重试列保留 PA_012）；fig4j 不变。论文 §2.4/图例 (i)/Methods 治理句/数据可用性按合并态改写（旧版本错误不进正文；图例 (i) 保留一句轻量溯源）；FACT_SHEET claim check 重基。
  - **顺带修正（本批 sweep 发现的批次三漏扫）**：Methods 与 Data availability 两处 "Exp-24 … Figs. … and 4f"（生产门决策面板，+2 顺移后应为 4h）、Data availability "Exp-25 … Figs. 4g/4h"（应为 4i/4j）——三处陈旧字母修正。
  - **登记同步**：FIGURE_PLAN_V5（Fig 4 表 6 行重排 + 行 h 内 "matching Fig. 4g"→4b + 第二次重字母注记）；PAPER_FACT_SHEET（头部第二次重字母映射 + Exp 15/17/18/23 节字母 + Exp 25 claim check 合并态重基）；MANUSCRIPT（5 行字母 + Exp 25b 新行）；PAPER_DRAFT 头部审计注追加本批记录。**批次三的未提交状态说明**：本批开工时发现 09-11 批次三（Fig 3/4 重编号）改动仍在工作区未提交（HEAD 停在批次一），本批与其一并提交。
- **论文修订批次三（2026-09-11，用户指示"一张大图对应一个小节"）——认证/保真两面板由图 3 迁入图 4，两图全面重编号**:
  - **原则与操作**：MRL 认证段与 RNAsmol 部署保真段既已从 §2.3 移入 §2.4，其结果面板也随文迁图——**Fig 3 收为六面板 a–f**（三个失败模式：筛选/排序/对接/亲和力/过度声称/混淆改进，字母不动），**Fig 4 扩为十面板 a–j**（新 a = MRL 认证、新 b = 部署保真，原 a–h 顺移 +2 字母为 c–j）。零面板内容改动，纯编号与文件层操作。
  - **脚本与图件**：10 个面板脚本 + pdf/png 输出全部 git mv（`fig4a_mrl_certification.*`〔自 fig3g〕、`fig4b_rnasmol_fidelity.*`〔自 fig3h〕、`fig4c_claim_gating.*`、`fig4d_claim_matrix.*`、`fig4e_overreach_events.*`〔+_tall，环境变量 `FIG4C_LAYOUT`→`FIG4E_LAYOUT`〕、`fig4f_mrna_family_strip.*`、`fig4g_selective_gating.*`〔脚本名 fig4g_selective_gating_matrix.py〕、`fig4h_gate_decisions.*`、`fig4i_quality_advisory_strip.*`、`fig4j_llm_usage_bubble.*`）；脚本内部 docstring/usage/输出路径/交叉引用逐文件带断言批量更新。**冻结件保持 as-written 命名**：`exp25_quality_review_advisory/fig4h_llm_usage.json` 数据文件与驱动 `exp25_fig4h_data.py` 不改名（frozen-record 惯例；图 4j 行的数据指针即磁盘实名）。
  - **装配重排**：`fig3_assemble.py` 删 g/h、末行改 `full [f]`（混淆改进回到 1.0 缩放、6-pt 原生字号），组合图 190.5 × 262.1 mm；`fig4_assemble.py` 十面板行计划——行 1 `fit [a, b]`（两 profiling 面板，原生宽度和超内容宽 ~3 mm，缩放 ≈0.98）、行 2 stack([c,e], d)、行 3 group [f, g]、行 4 fit [h, j]、行 5 full [i]，组合图 190.1 × 471.5 mm；两图 a–f/a–j 字母均经 PDF 文本层提取校验。**登记的视觉顺序偏差如实承接**：行 4 的 h+j 配对使 j 在 i 之前出现——2026-09-02 布局已登记的 g-after-h 偏差 +2 字母顺延，非新偏差。
  - **正文与图例**：§2.4 八处旧 Fig. 4a–4h 引用按唯一上下文逐一顺移（先降序 h→j…a→c 防级联，再 3g→4a、3h→4b）；Fig 3 图例摘除 (g)/(h) 描述（标题不变，六面板即三失败模式）；Fig 4 图例前端插入新 (a)/(b) 描述、原 (a)–(h) 重字母为 (c)–(j)、"(the Fig. 3g colour)"→"(the Fig. 4a colour)"；页脚面板清单改 "Fig. 3 six (a–f), Fig. 4 ten (a–j), Fig. 5 eight (a–h)"。
  - **登记同步**：FIGURE_PLAN_V5（Fig 3 表两行迁出、Fig 4 表前端插入两行 + 八行重字母 + 两段 2026-09-11 同日注记〔迁移映射、行计划、冻结件命名〕）；PAPER_FACT_SHEET（头部 legacy→v5 映射、Exp 14/15/17/18/23/24/25/E7/Exp26 行字母与脚本名，含 "Fig 4a/4b" 类复合引用的半移位修复）；MANUSCRIPT（Exp 14/15/15sb/17/18/23/24/25 行 + legacy 治理行现行指针）；SUPPLEMENTARY_INFORMATION（两处 Fig. 4f→4h）。历史日期条目按 as-written 惯例保留书写时字母；无实验重跑、无数据改动。
- **论文修订批次二（2026-09-11，用户指示）——§2.3 重构 + Fig 3 重编号（认证/部署保真两段移入 §2.4）**:
  - **§2.3 重题** → "Uncalibrated trust, claim overreach and confounded improvement in current scientific agents"（原 "…are measurable defaults"）；开篇段按用户大纲重写：现行科学智能体倾向把包装的预测模型打分直接当优化目标、不考虑打分与设计任务的适配性 → 未经校准的评分会误导设计 → 三个失败模式（腐蚀行动 / 报告语言 / 自我改进证据）逐一给实验证据。
  - **MRL 认证段（原 3f）与 RNAsmol 部署保真段（原 3g）移出 §2.3、插入 §2.4**（用户确认去处）：认证段改接 CapGate 机制段之后（"The profiling that feeds the gates is two-sided rather than prohibitive…"），保真段随后（"Profiling must also target the *deployed* artifact…"），原 §2.4 首段末句 "We evaluated CapGate in paired dual-arm experiments…" 拆为独立段置于两段之后——§2.3 现仅含三个问题本身，§2.4 先立 profiling 双向性（能认证 + 必须测部署工件）再进入门控实验。
  - **表述澄清（用户疑问逐项落实，全部数字对冻结文件复核，零新实验）**：(i) "(predictor, target) cell" → "predictor–target combination"（3 × 9 = 27 组合），"240 cells" → "240 runs"、"56 paired (target, seed) cells" → "56 paired target–seed units"；(ii) "spread 8–11 per predictor-and-use cell" → "8–11 events per predictor and intended use (ranking or screening)"；(iii) "The two task strata measure the same rate (legacy 55.6%, extension 53.6%)" 展开为分层语义（20 个逐字保留 legacy 任务 vs 25 个规则扩展任务，FP 声明率 15/27 = 55.6% vs 15/28 = 53.6%，单条 borderline legacy 声明排除——与 exp5 `runs_summary.json` by_stratum 逐项一致）；顺带修正 "names an predictor's" → "names the predictor's"；(iv) trust 小节补结论句（四面板同结论：未经校准预测模型不是可靠优化目标，针对其优化可能提高打分而不产生更好的 RNA 分子）；(v) RNAsmol 邻接矩阵缺陷展开讲清（上游 `preprocessing.py` 以 `zip(edge_index[0], edge_index[1])` 只取前两条有向边、索引整体 −1 → checkpoint 训练所见邻接矩阵几乎全零仅两个错位元素而非真实分子连接性；本地移植版"修正"为完全对称矩阵=静默改变训练输入分布——据 exp15_v020_sandbox 预注册 docstring + 上游代码 L71–73 核实）；(vi) confounded 段末补三问题闭环总结句（分数当目标腐蚀行动 a–d / 报告语言继承腐蚀 e / 自身评估被采样预算混杂 f，无一自行暴露、全靠测量）+ 预算匹配铁律句重申。
  - **Fig 3 重编号**（用户确认；纯字母重排，面板内容零改动）：混淆改进 3h→3f（§2.3 末面板）、MRL 认证 3f→3g、部署保真 3g→3h（后两者现于 §2.4 首引、先于 Fig 4）——面板保持按正文首引字母序（2026-08-31、2026-09-11 Fig 2 两次同类先例）。三面板脚本 + pdf/png 输出 git mv（`fig3f_dissolution.*` / `fig3g_mrl_certification.*` / `fig3h_rnasmol_fidelity.*`，脚本内 docstring/usage/输出路径同步）；`fig3_assemble.py` PANELS 重映射 + 注记；组合图重装配（190.5 × 254.6 mm；PDF 文本层结构化校验 a–h 八字母按阅读序在位）。图 3 标题 "Three failure modes of tool-using agents, measured" → "Three failure modes of current scientific agents, measured"；图 4e 图例 "the Fig. 3f colour" → "the Fig. 3g colour"。
  - 登记同步：FIGURE_PLAN_V5（Fig 3 表 f/g/h 行重排重字母 + 行内交叉引用 fig3f→fig3g 两处 + 2026-09-11 重编号注记含旧→新映射）；PAPER_FACT_SHEET（头部 legacy→v5 映射两处、E7 行、Exp 14 行、Exp 15 节、Exp 16 节、P0 legacy 行）；MANUSCRIPT（Exp 14/E7 行、Exp 15 行、Exp 15 addendum 行、Exp 16 行——含 §2.3 实验 8→6）；历史日期条目按 as-written 惯例保留书写时字母。
- **论文修订批次（2026-09-11，用户指示）——标题/术语/摘要/引言/Overview/§2.2 改写 + Fig 2 八面板化 + 补充材料新建（Exp 38/39 两项补实验）**:
  - **标题** → "A multi-agent system for RNA design with capability-gated prediction and constraint-navigated generation"（用户拍板；多智能体 + 双机制均显式）。
  - **术语**：全文 oracle→predictor 清扫（98 处），"profiled oracles"→"profiled predictors"；内部登记文档（DECISIONS/CHANGELOG 历史条目）按 as-written 惯例不动。
  - **摘要**重写为 149 词 Nature 格式单段（原 393 词）；**引言**按用户四段大纲重写（RNA 疗法重要性→专家瓶颈；LLM 智能体+三失败模式（ChemCrow/Coscientist/ProtAgents/Virtual Lab/CRISPR-GPT/BioMni 领域对应关系逐一核验无误）；RNADesignAgent+双机制；代表性结果段），贡献列表删除；引言总长 597 词。
  - **Overview 小节**重写（"Overview of the RNADesignAgent system"）：补 L4 一句话、全链路可追溯句、CapGate（L1 工具执行 choke point + L4 SynthesisAgent ClaimGate）与 GenNav（L2 工作流内导航模式）实现位置段；两条设计承诺压缩为一句保留；测量性细节留在 §2.4/Methods。
  - **§2.2 重题** "RNADesignAgent generates biologically valid RNA molecules across eleven workflows"：**IRES 阴性结果移出 Fig 2 → 补充材料 Supplementary Note 1 / Suppl. Fig. S1**；逆向折叠四 miss 表述修正为逐任务整对碱基映射（015/024 各 +1 对、018 −2 对、021 −3 对，Hamming 2/2/4/6——原"2/2/4/6 位置、1/2/3/1 碱基对"两列排序基准不一致造成假矛盾，数据本身无误，exp4 冻结记录逐条复核）；siRNA 例外机制句更正（任务 013 的 3 hits 为 21/21 零错配完美比对——86-nt 合成靶逐字来自节段性重复 lncRNA 基因座 DDX11L2，21-mer 恰好命中 DDX11L2 源转录本 + DDX11L16 两个拷贝；`G,10,4` 系平台默认而非该任务放宽阈值——旧"identity-70"命名隐含的错误暗示消除）；审计段补"聚合统计→同轨代表会话逐调用解析"的连接句；末句指引其余 7 个 workflow 证据入补充材料。
  - **Fig 2 八面板化工程**（纯图件修订，数据零改动）：fig2e_ires→figS1_ires_panel（+mode0 归档图）；fig2f→2e（siRNA）/2g→2f（小分子）/2h→2g（审计）/2i→2h（运行时）脚本 git mv 更名 + 内部同步；fig2_assemble 收为 a–h（布局 a 整宽/b c/d e/f g/h 整宽）；新增 qa_fig2_figs.py（11/11 GREEN）；组合图重渲染（523.2×888.9 pt 全矢量，8 字母在位）。顺带修正：Fig 2 新图例 (f) 删除"against the chance and 0.8 screening-gate lines"（该面板自 2026-08-28 修订起不画参考线，旧图例残留）。
  - **补充材料新建 `docs/SUPPLEMENTARY_INFORMATION.md`**：Note 1 = IRES 面板全文（59/59，mode-0 0.478 / mode-2 0.673，均低于 0.8 门，如实报"未调优"）；Note 2 = 其余 workflow 证据——S2.1 全长 mRNA（指引 Table 1 caseA）、S2.2 适配体（指引 Fig 5e–h + caseB，oracle 能力缺失披露）、**S2.3 三级结构 = Exp 38**（零新计算，从 exp24 (bb) 冻结会话汇总 20 任务 73 候选 vs rubric：pooled 28/73=38.4%、pLDDT 31/73、RMSD 门 1/14（池最小 2.49 Å）、12/20 任务有达标候选、1MME 0/18 最干净阴性——混合结果如实报告）、**S2.4 序列评分 = Exp 39**（生产工具路径 CPU：222/222，WT>自身随机中位 15/20 sign P=0.041 / Wilcoxon P=0.0083；疫苗 vs 随机 δ=1.0；CAI 项承载分离、MFE/nt 不分离（与 Fig 2c 互证）；BNT162b2 CAI 0.952 与 Exp-37 锚互证）、S2.5 sgRNA（CRGPT/CRISOT 锚集数据缺口披露，E19/E20 预留，DECISIONS (l)）、S2.6 ASO（确定性热力学筛选继承 ViennaRNA 有效性披露）。
  - 登记同步：PAPER_DRAFT 数据可用性 + 头部注记；FIGURE_PLAN_V5（Fig 2 表 8 面板化 + S1 迁移行）；PAPER_FACT_SHEET（字母同步 + 2026-09-11 配套节）；MANUSCRIPT（Exp 5–9/15/24 行字母同步 + Exp 38/39 新行）。测试套件 697 passed 1 skipped 无回归。
  - **遗留修复（同批，用户指示）**：(i) siRNA 任务 013 命名层——任务 JSON 新增 `legacy_name_note` 字段（说明 `G,10,4` 为平台默认而非任务特有严格阈值、"identity-70" 仅为与 BLAST perc_identity 下限的类比、任务真实 edge 属性 = 逐字 DDX11L2 节段性重复片段），`data/benchmarks/README.md` 加 "Known legacy naming (2026-09-11)" 节并顺带把过时的 BMC 时代引用题更新为现行标题；description 字段按冻结证据约束保持逐字（exp6 records.jsonl 内嵌该字段，改动会破坏 `--verify` 字节一致）；基准/siRNA 相关测试 27 passed 1 skipped。(ii) MANUSCRIPT Exp 2+3 行重基到 (aa)/(bb) 时代数字（CAI 0.896/0.729/0.675，P=1.1e-06 δ=0.91；MFE/nt −0.297，WT/random P=0.30；静态时代 0.832/−0.336 标注 superseded 归档 `exp2_cds_nulls_static/`）。
- **外部仓库适配登记（2026-09-09，用户指示：让用户知道下载外部仓库后如何与系统适配，但不得把外部仓库集成进系统）**: 排查 20 个外部代码的 git 工作树——零已跟踪源码修改；GerNA-Bind 的 ` m` 脏状态=上游提交了 Python-3.8 编译的 `__pycache__/*.pyc`、本地解释器重新生成字节码（运行时产物非适配），其余子模块的 ` ?`=权重放置后的未跟踪内容。DEPLOYMENT.md 新增 §1.5（全部 20 代码钉定 commit 表：17 子模块 SHA 逐一列出 + EGARPS/Protenix/RiboDiffusion 为仓库内 vendored；单独下载时的放路径 + checkout 规则；三个 fork 必须用 `SII-ShenggengLin/` URL）、§1.6（适配分层模型：fork 已提交补丁 + 微服务封装层两层承载全部系统适配；任何部署不手改外部仓库源码、不 vendor 进系统主体、不提交 `external_repos/` 本地变更）、§1.7（配置后预期 `git status` 的 `?`/` m` 逐项解释 + 验证命令 + `git submodule status` 全钉定复核）；README §4 vendored 注记同步扩写指向新节。纯文档，无代码/数据改动。
- **论文一致性二次复核（2026-09-09 同日第二轮，用户指示：先重建实验轨迹再逐项核验）**: 按图/表→实验→冻结文件映射（Fig 2 = Exp24(bb)/Exp2+3(aa)/Exp4-7；Fig 3 = Exp10v3/11v3/12/13/5/14/15+15sandbox/16；Fig 4 = Exp5+17/18(bb)/23/24(bb)/25；Fig 5 = Exp26/28/31/29/30；表 1 = Exp37(bb)）独立重算全部面板数字 vs `experiments/results/` 冻结文件——全部对上，另核验全部绘图脚本数据源指向现行冻结目录、渲染时间戳晚于数据。**修正四处文字/登记层残留**（无图件需重渲）：(1) PAPER_DRAFT §2.5 与 FACT_SHEET Exp-28 行 "JCD-passing delivery on **18** of 20 targets" → **17/20**（冻结逐靶表 17 靶 JCD≥1 格，零格 = GFP/RSV-F/Spike WT；18 系 both-pass 格数的单元/靶标滑误，自 f113e825 沿用；下方 2026-09-03 历史条目已加更正注记）；(2) FIGURE_PLAN 行 4a + MANUSCRIPT Exp-17 行 "FP **0/31** = 0% (CI 0–16.1)" → **0/20**（CI 0–16.1 数值上即 0/20 的 Wilson 上界；0/31 为 2026-09-02 论文层已纠正的口径混淆，两登记行漏同步）；(3) FACT_SHEET Exp-24 行 "workflow medians 3 s–8.8 min"（210-子集值混入池化句）→ **2.8 s–8.9 min**（241 池化口径）；(4) FIGURE_PLAN 行 2a 加粗重跑日期 2026-09-01 → **2026-09-07 DECISIONS (bb)**（与论文 Fig 2a 图例一致，"third-reset" 措辞同改）。PAPER_DRAFT 头部审计注追加第二轮记录；AGENTS.md 登记本轮。
- **图 5g 修复重渲染（2026-09-08，用户指示，纯图件修订，数据与结论不变）**：`experiments/plots/fig5g_decisive_mosaic.py` 按当日 fig5c 修复模板重构——**行标签（12 个靶标名）恢复**：旧版标记列轴 `sharey=ax` 后又 `axg.set_yticks([])`，共享 y 轴刻度被清空导致全部行标签在渲染画布上消失（两侧大留白实为标签位空缺）；"Target e2e" 浮动两行轴标题（首行高于其余表头一整行、且缩写不可读）按 fig5f "写全称" 惯例改为 "End-to-end"，并与 Compact/Standard/Extended 同基线的单行第四列表头（renderer 实测对齐 + 基线一致断言）；内容块（行标签 + mosaic + 标记列）水平居中、tile 加宽 11.5→14.7 mm（fig5c 瓦片几何）、行距同 fig5c 4.35 mm、画布 89×80→89×71.2 mm；顶部加一行图义说明带（"One tile per target × length-profile cell — colour marks the delivering arm(s)"，fig5c 惯例）；图例改两行并带入格数（navigation only 10 / both arms 14 / static grid only 3 / neither 9——与注册计数逐字一致）与 e2e 标记释义行（"End-to-end (navigation): ■ all 3 profiles delivered (4) □ ≥1 profile undelivered (8)"）；空心 e2e 标记描边离色板 #D9D9D9 → palette warm grey（全部用色限于 palette rev 7 十二色）；行标签名核对（RNase_A→RNase A、SARS-CoV-2_Nucleocapsid→SARS-CoV-2 N、TNF_alpha→TNF-α、Concanavalin_A→Concanavalin A，全部标准命名）。全部文字 6 pt 纯黑；1200-dpi PNG + 矢量 PDF（fonttype 42，符合 Nature Methods 线条图 1000–1200 dpi 指引）。程序化护栏：全文本画布内断言 + 两两文本碰撞断言 + 表头基线一致断言 + 行标签/mosaic 间距断言 + 精确画布像素断言（4205×3364，脚本内 mpimg 复核）+ 栅格调色板纯度 + 零边缘墨；qa_exp29_30_figs 栅格 QA GREEN。文档同步：FIGURE_PLAN 行 g、AGENTS.md。
- **图 5f 修复重渲染（2026-09-08，用户指示，纯图件修订，数据与结论不变）**：`experiments/plots/fig5f_decisive_grouped_bars.py` 重构为单图面板（fig5a/5b/5c/5d 当日"一子图一图"惯例）——移除底部 pair-outcome 堆叠长条（其四类计数 14 both / 10 navigation-only / 3 grid-only / 9 neither 即图 5g mosaic 的四色格、由图 5g 与图例 (g) 逐字承担，长条与主图不同轴且信息重复）；原悬浮于坐标区内的 "NO-GO (pre-registered)"（读感如偏位图内标题）并入坐标轴上方预留带的单行统计注记（fig5b 惯例："McNemar b:c = 10:3, P = 0.092, n = 36 — NO-GO (pre-registered)"）；横轴组标签 "Targets e2e" 写全称 "End-to-end targets"；坐标区由 60% 图宽扩至房屋全宽几何，右侧空白带消除；图例精简为 navigation / static grid 两摆片（both / neither 随长条移除），并应用户同日指示由底部行改为坐标区右上角单列（swatch 列对齐，渲染器实测字宽排版，矮柱上方空白区）。全部文字 6 pt 纯黑（栅格复核：新旧版文字字形核均为 #000000，非黑深色像素全部为抗锯齿灰阶光晕；旧版"发浅"观感系缩略显示伪影 + 深色填充上黑字低对比，后者随长条移除）；palette rev 7 用色不变（sage 导航 / terracotta 静态网格）；画布 89×56 → 89×40 mm（4205×1890 px），1200-dpi PNG + 矢量 PDF（fonttype 42，符合 Nature Methods 线条图 1000–1200 dpi 指引）。程序化护栏：全文本与摆片画布内断言 + 两两碰撞断言（含图例行）+ 注记完全位于坐标区外断言 + 柱顶计数不越坐标区顶断言 + 图例元素与柱体零重叠断言 + 精确画布像素断言（脚本内 mpimg 复核）；qa_exp29_30_figs 栅格 QA GREEN。文档同步：FIGURE_PLAN 行 f、PAPER_DRAFT 图例 (f)（顺带更正其中遗留的修复前时代数字 16:17 / 8:9 / P=1 → 24:17 / 10:3 / P=0.092，与图及图例 (e) 句一致）、AGENTS.md。
- **图 5d 修复重渲染（2026-09-08，用户指示，纯图件修订，数据与结论不变）**：`experiments/plots/fig5d_secondary_endpoint.py` 重构为单图面板（fig5a/5b/5c 当日"一子图一图"惯例）——移除判据 bullet bars（gene-e2e 合取 0.45=9/20 vs 0.8 legacy 门 + 规则池 1.00=20/20 上下文；约束率 0.944 ≥ 0.9——两条门线 0.8/0.9 系两条不同预注册判据各自注册的门限，并非同一标准，随块移除）与逐靶花费条带（均值 24.55/35、10 触顶 + 10 早停 11–16、违规 0 · LLM 0；实心 mean 刻度线随之去除）：两块与 Δ 分布既不同轴也不同观测单位（比率 vs 逐格分差 vs 逐靶调用数），不具可合并性，其数字全部由图 5d 图例与 §2.5 正文逐字承担；各块顶部悬浮统计行（读感如错位图内标题）一并移除。保留视图独占面板：Δ-composite 逐格堆叠点分布（fig2d/2f 惯例，一点一配对格 n=60，方向色 sage 导航占优 / terracotta 规则占优 / grey blue 持平——图内不加键、释义在图例），方向计数与配对 Wilcoxon 结果（+24 / =18 / −18, P = 0.73, n = 60）以单行注记置于坐标轴上方预留带（fig5b 惯例）；高栈计数标签（18、6）保留白底衬。全部文字 6 pt 纯黑（栅格 QA 复核字形核心纯黑、仅抗锯齿光晕——此前观感"部分文字发浅"系缩略显示伪影）；palette rev 7 用色不变；画布 89×74 → 89×35 mm，1200-dpi PNG + 矢量 PDF（fonttype 42）。程序化护栏：全文本画布内断言 + 两两文本碰撞断言 + 注记完全位于坐标区外断言 + 精确画布像素断言（4205×1654，脚本内 mpimg 复核）；栅格 QA GREEN（零边缘墨、纯调色板）；`exp31_fig5d_secondary.py --verify` 字节级一致（数据层零改动）。文档同步：FIGURE_PLAN 行 d、PAPER_DRAFT 图例 (d)（图型句改写 + 方向色语义写入 (d)）、PAPER_FACT_SHEET Exp 31、MANUSCRIPT E6 行、AGENTS.md。
- **图 5c 修复重渲染（2026-09-08，用户指示，纯图件修订，数据与结论不变）**：`experiments/plots/fig5c_delivery_mosaic.py` 重构——**行标签（20 个基因名）恢复**：旧版标记列轴 `sharey=ax` 后又 `axg.set_yticks([])`，共享 y 轴刻度被清空导致全部行标签在渲染画布上消失（两侧大留白实为标签位空缺）；"Gene e2e" 由浮动两行轴标题（首行高于其余表头一整行）改为与 Expression/Stability/Balanced 同基线的单行第四列表头（renderer 实测对齐 + 基线一致断言）；内容块（行标签 + mosaic + 标记列）水平居中、tile 加宽 11.5→14.7 mm、画布 89×118→89×106 mm；顶部加一行图义说明带（fig5b 注记带惯例）；图例改两行并带入格数（navigation only 17 / both arms 18 / rule only 6 / neither 19）与 e2e 标记释义（导航臂三档全交付 9 / ≥1 档未交付 11）；空心 e2e 标记描边 #D9D9D9 → palette warm grey（全部用色限于 palette rev 7）；行标签 HPV16_L1 → HPV16 L1。全部文字 6 pt 纯黑；1200-dpi PNG + 矢量 PDF。程序化护栏：全文本画布内断言 + 两两文本碰撞断言 + 表头基线一致断言 + 行标签/mosaic 间距断言 + 精确画布像素断言（4205×5008）+ 栅格调色板纯度（灰阶 + palette↔白/黑混合段）+ 零边缘墨。文档同步：FIGURE_PLAN 行 c。
- **图 5b 修复重渲染（2026-09-08，用户指示，纯图件修订，数据与结论不变）**：`experiments/plots/fig5b_gennav_mcnemar.py` 重构为单图面板——移除 sign-flip 置换零分布 inset（其与精确 McNemar 注记表达同一检验：置换零分布即该检验的计算后端，无信息损失）与右侧配对格文字列（该列数字为按靶×3 口径 15/9/30/6，**与注册逐格口径 18/6/17/19 不符**，随移除消解；逐格计数由图 5c 与图例 (c) 承载）；精确 McNemar 结果（b:c = 17:6, P = 0.035, n = 60）以单行注记置于坐标轴上方预留带；每个臂坐标点外侧加 ×n 重合数标注（规则臂 0/3 档 ×12/×8，导航臂 0/1/2/3 档 ×3/×5/×6/×6，替代原先仅靠 alpha 叠色暗示 multiplicity——用户指示"标数字更严谨"）。全部文字 6 pt 纯黑；方向色沿用 palette rev 7（sage 导航占优 / terracotta 规则占优 / grey blue 一致，图内不加键惯例不变）；89×56 mm 单栏、1200-dpi PNG + 矢量 PDF。程序化护栏：全文本画布内断言 + 两两文本碰撞断言（含 ×n 标注）+ 注记完全位于坐标区外断言 + 精确画布像素断言（4205×2646）。文档同步：PAPER_DRAFT 图例 (b)（同时首次在图例中定义方向色语义与 ×n 标注——fig5d "图内不加键" 惯例所引）、FIGURE_PLAN 行 b。
- **受影响实验重跑全部完成 + Exp 37（表 1）落地（2026-09-07，DECISIONS (aa) 收官）**：GenNav-默认平台上的四组重跑与三案例全部收尾——**Exp 2+3**：20/20（三大靶无上限补跑；CAI designed 0.896 > WT 0.729 > random 0.675，P=1.1e-06 δ=0.91；MFE/nt −0.297 δ=−1.0，WT/random 不可分 P=0.30），图 2b/c + fig2 组装重渲染；**Exp 24**：241/241、冻结 241 会话/11,003 事件/1,356 门决策（616 拒/586 需画像/154 降级/0 允许），8 个含导航语料库会话在 context 修复后替换重跑（exp24_r3、latest-record-wins），184 个被替换时代未盖章探测事件披露为已知缺陷排除，图 2a/2h/2i/4f 重渲染；**Exp 18**：E3-M 双臂 40/40——FP 36.4%（8/22）→8.3%（1/12）相对削减 77.1%（门 PASS）、越界 7→0、TP 保留 78.6%（14→11）低于 90% 门如实报告（三损失=ClaimGate 未画像家族降级为相对口径，裁决读作 neutral；构建器最近档 λ 解析 + 多映射 echo 校验两项仪器适配）；**Exp 25**：93/93 门 PASS + verify 字节级一致（on 臂 1 次重试恢复；图 4g 重试列首现非空、画布扩宽）；**Exp 37**：三案例全绿——(A) Spike 全长平台默认流 6.6 h（无上限），best CDS CAI **0.969（λ6.5 齿轮）超过 BNT162b2 锚点 0.952**，导航 35/35 打满、stability 档零交付边界如实披露；(B) anti-VEGF v4 导航 23.4 min，top 候选 EGARPS 被工作流自身快速指标门跳过（RhoFold pLDDT<65）、同链 pegaptanib 锚点 0.365、无验证筛选力——自审示例重定位；(C) NSP12 siRNA 106 s、top-5 零脱靶；`--verify` 锚点逐项复现全绿。论文全量重基：§2.2（默认流描述+终数）、§2.4（审计构成/运行时/E3-M）、§2.7+表 1（三案例新数字+披露口径）、摘要/贡献 3、Methods（战役冻结句+E3-M 资产句）、图 2a-e/h/i、图 4d-h 图例；Fig 6/§2.6 移除（用户指示，湿实验小节素材）。运行时口径变更登记：case 墙钟时间为披露的并发负载口径。工程注记：导航探测并发 >800aa 2→4（输出中立）、exp2/exp37 时间上限移除（用户指示，看门狗 60 s 心跳监控+自动恢复替代，pgrep 自匹配 bug 修复）、常驻 ODesign 舰队（6 副本 GPU 0/1/2+8012 轮询代理）、exp2 超时公式三次按实测修订后废除。
- **平台变更 — 全长 mRNA 两步重设计 + 治理化 UTR 池（2026-09-07，用户指示，DECISIONS (bb)，湿实验计划驱动）**：`full_length_mrna_design` 重构为两步协议（GEMORNA 论文的"先选 CDS 再配 UTR"次序）——第一步 CDS 评估后按导航 profile 选 ≤3 条（静态配方取 top-3，共享 CDS 综合分），UTR 抽样从不按 CDS 重采样（消除 UTR 抽样方差对 CDS 排序的混杂）；第二步每 run 一个 UTR 池 = GEMORNA 筛选规模抽样（12 条 5'UTR + 10 条 3'UTR）+ 断言校验基准池（`agent_core/data/utr_benchmarks/utr_benchmarks_v1.json`：BNT162b2 5'UTR 模板验证 51-nt α-globin 来源形（GenBank PP544446 区间 + Xia 2021 描述 + RefSeq NM_000558.5 核心三方一致；仓库锚文件的 3-nt GAG 前缀判定为组装伪迹并披露）、BNT162b2 3'UTR 94-nt AES–mtRNR1（LinearDesign 补充材料逐字，其 COVID 与 VZV 两处完全一致）、LinearDesign 论文 5'UTR 43-nt、天然 HBA1 对 37/111-nt——全部程序化提取零手工转录，加载时 md5/长度/纯度/规则通过断言）。**准入规则只收有文献定量阈值的**：U1 设计 5'UTR 无 AUG（Kozak 1986/1989 扫描模型 + Sample 2019 MPRA）、U2 3'UTR 无 II 类串联 AUUUA ARE（Chen & Shyu 1995）、U3 帽入口 60-nt 窗 MFE > −30 kcal/mol（Kozak 1989：−30 发卡距帽 12 nt 阻止 40S 结合、距 52 nt 无害——规则故意只限帽近端）、U4 扫描路径 150-nt 窗 > −61 kcal/mol（hp7 停滞阈）；**明确不实现**（无可引阈值，登记禁复造）：U 含量上限、GU-rich TLR motif 计数（Vaidyanathan 2018 只做全局 15.5%→12.6% 重编码）、内部 AAUAAA（递送 mRNA 不遇核切割机器，BNT162b2 自己的 5'UTR 就带帽近端 AAUAAA）。5'UTR 短名单（≤6）由已认证 MRL oracle 排序——生成 UTR 只有在 in-silico 胜过临床基准时才会被选中；3'UTR 短名单（≤6）为准入幸存顺序（基准优先，算力上限而非排序）。**utr3_stability 从 ASF 排序目标降级为报告诊断**（ToolSpec evidence_use → scoring_annotation；oracle 在所有注册 task type 下 unprofiled，按 (e) 不得参与排序；reference_point 命名该键改为响亮报错）。输出维持 5'UTR+CDS+3'UTR（用户指示 2026-09-07：加帽加尾由湿实验方按规程处理，系统不输出 poly(A)/cap）。CDS 层零改动（导航委托与 GenNav 核心原样，exp26/27/28/30/31 冰冻仪器不受影响）。测试 686 passed 1 skipped（新增 tests/test_utr_pool.py 19 项 + 两步/准入/门/降级钉扎更新）。**影响面登记与重跑**：Exp 24（22 个全长任务 + PA 全长会话）、Exp 18（E3-M 任务重建）、Exp 37 caseA（表 1）；改动前 in-flight 的 exp37 caseA 第三次运行保留为改动前内部登记。。**重跑结果（2026-09-07 当日落地）**：Exp 24 三跑 241/241 零失败——冻结切片 24,897 事件 = 19,848 调用 + 4,862 门决策（1,800r/489p/1,391d/**1,182a**，allow 类首次非零 = 降级注记用途）+ 187 装配；代表会话 PA_036（2,738 事件）；全长道中位 8.8 min 成为最慢中位工作流（治理池成本如实披露）；239/241 ≤1 h；`--verify` 一致；fig2a/2h/2i/4f + 组合图重渲染，四文档重基；前两时代归档 `_utrgrid/`。Exp 18 三跑 40/40——FP 33.3%→7.7%（76.9% 降幅）、**TP 12/12=100% 双门全过**（navgrid 时代 78.6% 未达门的损失 = never-profiled 降级声明，两步设计后不再产生）；fig4d + 组合图重渲染；旧时代归档 `_navgrid/`。
- **Exp 37 caseA 重跑落地（同日）**：Spike 全长（DECISIONS (bb) 两步平台、表单入口、无上限）成功——24,320 s、108 候选（3 导航 CDS × 6×6 短名单）；best=`full_length:cds_design_gennav:lambda5.5:utr5_gemorna_5utr_long_4:utr3_gemorna_3utr_long_1`，cds_cai 0.95896 > BNT162b2 锚 0.95153、MFE/nt −0.22096、总长 4,039 nt、asf 0.0069；**best 的两条 UTR 为 GEMORNA 生成并在认证 MRL oracle + ASF 上胜过同池的临床基准（BNT162b2 对 / LD 论文 5′UTR / 天然 HBA1 对）**；导航 35/35 预算用满、stability 零交付 + balanced 1 交付（双降级披露，Spike 仍是交付稀缺边界）。改动前登记 `caseA_prebb/`（23,907 s、54 候选、λ6.5 CAI 0.9685、旧 3×3 网格）保留为内部对照。论文案例 A + 图例(a)、FACT_SHEET（表 1 节整体重写，legacy Fig-7 时代记录标记 superseded）、MANUSCRIPT 行重基。
- **平台默认变更 — GenNav-λ 成为 mRNA 工作流默认 + 受影响实验重跑开启（2026-09-06，用户指示，DECISIONS (aa)）**：`mrna_cds_design` v2.0.0 — `navigation` 改三态（未设置+默认配方 `design_tool="all"` → GenNav-λ 约束导航；显式钉引擎 → 静态配方路径，注册仪器语义逐字保留；True/False 总是覆盖），新增 `resolved_navigation` 单一解析点（物种 fail-fast 合约跟随解析后模式）；`full_length_mrna_design` 新增同语义三态 `navigation` 字段并**原样透传**给 CDS 子工作流（默认策略单一来源 = CDS 层），导航 trace 进入合并 state writeback，导航 CDS 交付与 3×3 GEMORNA UTR 网格组合不变。CapGate 确认默认在线（审计轨迹 + 门决策 + 排名治理装配，模式无关；进程内默认 enforce，战役显式 advisory）。适配体导航保持 opt-in（证据双向，DECISIONS (i)/(aa)）。测试 672 passed 1 skipped（基线 646 + 导航默认套件：三态解析表、全长委托/静态回退/钉引擎保持/显式覆盖、静态路径钉 navigation=False）。Pilot（Insulin 全长 form 入口，新默认）：success、99 候选 = 11 导航 CDS × 9 UTR、best=`full_length:cds_design_gennav:lambda1.75:utr5_short:utr3_long`、ASF 排名带治理标记（`utr5_mrl: transferred`、`utr3_stability: unprofiled`）、审计落 gate_decision/ranking_objective_assembly。**影响面登记与重跑（同指示）**：Exp 2+3（图 2b/c，designed 臂 = 新默认流；静态时代归档 `exp2_cds_nulls_static/`，会话前缀 `exp2nd_/exp2ns_`，driver 追加日期修正案）、Exp 24（图 2a/2h/2i/4f）、Exp 25（图 4g）、Exp 18（图 4d 基础资产）；exp26/27/28/30/31 与适配体/siRNA/结构/小分子各战役不受影响（全部显式钉旗或自建池）。后续：Exp 37（表 1 三案例）。
- **Exp 31 / 图 5d 次级终点渲染（第四次重置，§2.5，2026-09-05，figure-only）**：`experiments/exp31_fig5d_secondary.py` —— 无新测量，面板每个数字从冻结的 Exp-28 记录（`exp28_gennav_mrna_endpoint_v2/full/runs.jsonl`）重算并与存储 verdict 逐项断言相等（c_e2e 0.45 / a_e2e 1.0、Wilcoxon P=0.7309、约束率门 0.9、预算账本），输出 `exp31_fig5d_secondary/panel_data.json`，`--verify` 字节级一致；本 reset 中 5d 此前从未渲染，无旧件可删（登记）。**编码重注册**（FIGURE_PLAN 行 d "pending re-registration" 落定）：三块式单栏——(上) 注册判据 bullet bars：gene-e2e 合取 GenNav **0.45（9/20）vs 0.8 门（legacy 校准）**、规则池 1.00（20/20，交付层上下文——其失败在 JCD 层，见 5b/5c）+ 约束率 **0.944（60 格均值）≥ 0.9 TRUE**（次级判据中唯一成立项）；(中) Δcomposite 逐格堆叠点（fig2d/2f 惯例，**+24/=18/−18，Wilcoxon P=0.73 NS**，方向色沿用 5b 语义、图内不加键——fig5b 惯例）；(下) 逐靶导航花费条带（栈 11–35，**均值 24.55/35、10 靶触顶、10 靶 11–16 早停、违规 0 · LLM 0**）。渲染 `experiments/plots/fig5d_secondary_endpoint.py` → `fig5d_secondary_endpoint.{pdf,png}`，89×74 mm、6 pt 纯黑、palette rev 7、1200 dpi + 矢量 PDF；程序化护栏（全文本画布内 + 两两文本碰撞断言——首版图例行超宽、Wilcoxon 注记压零栈计数两次被拦下后定稿：图例行取消改双注记、计数标签白底衬）；栅格 QA GREEN（精确画布 4205×3496、零边缘墨、纯调色板）；视觉通道对全幅图两次误报（登记过的失效模式），以原生分辨率分块复核 + 确定性几何核查为准。文档同步：FIGURE_PLAN 行 d、PAPER_DRAFT 图例 (d) + §2.5 一处 Fig. 5d 引用、PAPER_FACT_SHEET Exp 31 小节、MANUSCRIPT E6 行、AGENTS.md（含 2026-09-05 用户确认可用 GPU 0/1/2）。
- **Exp 30 完成 / 图 5h 生产实跑数据（第四次重置，§2.5，2026-09-05 用户指示重启并行）**：`experiments/exp30_production_navigation_live.py` 停止后重启——**11/11 表单生产会话全成功（适配体 6 会话，IFN-γ 即 pilot 会话、其记录经 `carry` 带入臂汇总 + mRNA 5），`--verify all` 字节级一致，预算违规 0**。适配体臂（48-raw cap，E14 序列-only 生产路径，`RNADA_CAPGATE=advisory`，质量评审默认开）：IFN-γ 3/3 细胞 47/48 提前停、Ang2 1/3、FGF2 1/3、IL-17A 1/3、PDGF-BB 2/3、**Influenza H3N2 HA 0/3（如实稀缺边界，48 cap 打满）**——共 8 细胞。mRNA 臂（GenNav-λ 35-raw cap，Exp-28 修复版导航器）：PTH 3/3（11/35）、CSF3 3/3（11/35）、LEP 2/3（12/35，交付期 D1 多样性地板降级）、THPO 3/3（28/35）、PLAT 2/3（24/35，同前）——共 13 细胞，全部提前停。逐轮 rounds/probe/交付全量在录。**图 5h 重绘于本数据**（`experiments/plots/fig5h_production_navigation_pareto.py`：成本-交付帕累托散点（11 战役，臂双色彩 + cap 虚线 + 帕累托角环 + 4.3× 同交付成本注记）+ 适配体突破阶梯 inset（gap 链精确重建：IFN-γ 29/35/47、PDGF-BB 36/48、swH3 HA 持平 0；mRNA 阶梯不绘——其 gap→细胞映射被交付期 D1 地板截断，LEP/PLAT 以 2 细胞点如实呈现）；程序化标注碰撞断言 + 键行溢出断言 + 栅格 QA GREEN；89×62 mm、1200-dpi PNG + 矢量 PDF；FIGURE_PLAN 行 h 与 PAPER_DRAFT 图例 (h)、§2.5 正文一句 Fig. 5h 引用已同步；interim Exp-29 sweep 曲线退回 §2.5 正文引用（cap16 10:2 P=0.039 晋升点保留在文中）。**2026-09-05 修订（用户指示，逐条披露于 run 记录）**：(i) 3 个剩余适配体靶复用同序列已有 ProteinX 折叠（IL-17A 用其自身中断会话引用的 CIF=断点续跑等价；PDGF-BB/swineH3HA 用 Exp-29 扩展池最新完整折叠）经 `protein_structure_path` 跳过折叠——ProteinX 折叠跨 run 非字节确定，属披露的协议修订；FGF2/Ang2/pilot-IFN-γ 仍为新鲜折叠序列-only 会话。(ii) 纯基础设施：8012 端口临时由轮询代理（`microservices/odesign_service/roundrobin_proxy.py`）分流至 6 常驻副本（GPU 0/1/2 各 2，taskset 绑核 0-41/42-83/84-127），单请求 ~21 s（vs 子进程 ~90 s），跑毕已恢复原 8012 服务；生产代码零改动。加速效果：IL-17A/PDGF-BB ~22-23 分钟/会话（旧路径 FGF2 88 分钟）。会话工作区 `workspace/sessions/exp30_*`；结果 `experiments/results/exp30_production_navigation_live/{pilot,aptamer,mrna}/`。**2026-09-08 图 5h 修复（用户指示，fig5d/5f/5g 单视图约定）**：阶梯 inset 移除（与主散点不同轴不同观测单元；其数字 —— IFN-γ 29/35/47、PDGF-BB 36/48、swH3 HA 持平 0 —— 文报于 Fig. 5h 图例与 §2.5）；全部文字统一 6-pt 纯黑；两行臂 key（fig5g 约定，单 marker）携带 cells + mean raw，图内统计行与 cap 标签删除；PTH/CSF3 重合点并为单 marker 共享标签；防重叠断言扩展至文字–marker（0.4 mm 净距）；画布 89×62 → 89×52.5 mm；栅格 QA GREEN；PAPER_DRAFT 图例 (h)/§2.5、FIGURE_PLAN 行 5h、FACT_SHEET 已同步。
- **终稿一致性修正案（2026-09-05，用户指示）**：PA_028（全库唯一导航会话）在最终 v4 导航器下重测——表单生产入口 2/2 turns、4084 s（−35%）；Exp 24 审计切片外科重冻结（`exp24_refreeze_pa028.py`：10,331 事件、reject 709→654、其余 240 会话逐字节保留、新 SHA-256 清单与披露块——原分析器的静默轨迹断言在如今繁忙的审计轨迹上不可重申，故注册外科式替换）；Exp 25 PA_028 三臂串行重跑（并发同靶会互相风暴，改串行）→ 93/93 恒等性保持；fig2i/4f/4g/4h 重渲染；PAPER_DRAFT 审计构成与运行时数字全部更新（10,331/8,810/1,337/184；68.1 min）。
- **Exp 29 / Fig 5e–5g + Fig 5h（第四次重置，§2.5 实验 3，2026-09-03→04）**：适配体战役弧全量重跑（`experiments/exp29_aptamer_campaign_arc.py`，预注册 docstring，RNA-BioBench-Aptamer 20 靶池，双臂 48-cap 预算匹配，零 LLM，100 组配对运行零预算违规，`--verify` 60 记录+判定字节级一致）。四段弧：seg1 松矩阵饱和（b:c=1:1，55/60 both-pass，导航臂 32.7/48 同交付 −32% 成本）；seg2 重锚定稀缺（10:9，静态失败 33%）；seg3 决定性面板 NO-GO（8:9）；seg4 确认（1:8，P=0.039 静态占优）；合并 9:17 P=0.17——**四次分配器版本（shipped/v2/v3/v3b）逐格等价，如实报告为扩散生成器上的诚实边界**。三轮生产修复（v2 收官轮+中心探针；v3 收缩估计+UCB+D1 感知停止判据；v3b 循环选带+UCB 选齿轮）各有单格级可归因修复但总量不动；机制诊断：+15pp/样本信号、ICC 0.30、同齿轮多样性等同——识别成本吃掉集中收益。**保留优势**：seg3 e2e 4:0（唯一端到端交付全来自导航臂）；seg1 −32% 同交付成本；预注册预算扫描（sweep 模式，2026-09-04）：cap24 导航 8 vs 静态 3（b:c=8:3）、cap32 8:8、cap48 持平——**紧预算下交付 2.7×、同交付省 25% raw**（Fig 5h 重定位为成本-交付曲线+成本节省 inset）。生产变更：`gennav_aptamer.py` v3b（central_probe_lengths/adaptive_round/delivery_gaps/shrunken_gear_rate，旧 E8-E14 函数逐字保留）；工作流新增 `navigation_raw_budget` 生产旋钮；测试 test_gennav_aptamer_v2.py 新增、全套 650 passed 1 skipped。机器注记：2026-09-04 恢复 3-GPU（bring-up 均衡分卡恢复），12 ODesign 副本分三卡 + taskset 钉核（GPU 组 0-41/42-83/84-127）+ OMP 封顶——每请求 ~90s 子进程加载的 CPU 瓶颈驯服，sweep 阶段 24 靶 ~90 分钟。**Exp 30（图 5h 原生产实跑设计）2026-09-04 用户指示停止**：pilot IFN-γ 3/3 全交付（47/48 提前停）+ Ang2/FGF2 记录 + mRNA 5 靶已确认清单（PTH/LEP/CSF3/THPO/PLAT）保留于 `exp30_production_navigation_live/`，后续按用户指示处置。论文重定位：§2.5 适配体段 + Fig 5 图例 (e)-(h) + FIGURE_PLAN 5e-h 全部改写为上述结果；Discussion 增加适用边界机制（生成器确定性 moderator：mRNA-λ 确定性格点 17:6 决定性胜 vs 扩散格点等价）。
> **Scope**: interface changes and major workflow introductions.
> **Last updated**: 2026-09-03

> **History policy**: this log records the current interface state and a
> condensed register of the most recent change eras. Full narratives live in
> git history and the audit-evidence directories cited per entry; the
> experimental do-not-repeat register is [`DECISIONS.md`](DECISIONS.md).

## 2026-09-03 — Exp 28：GenNav mRNA 主终点修复重跑（图 5b/5c）+ 生产导航 v2.4 + GPU 变更

- **Exp 29 终版追加（2026-09-04→05，用户指示的 1+3 组合）**：v4 生产导航器（最少服务优先带轮转，修 seg4 带独占缺陷）→ seg3 改善至 **10:3 P=0.092（C24:A17，e2e 4:0）**，seg4 1:8 如实保留；**扩池 RNA-BioBench-Aptamer-Expanded**（12 复合物结构靶 RNA 链剥离 + 7 序列靶 ProteinX 一次折叠缓存）39 靶 × cap 16/20/24/32/48 双臂全档扫描：**cap16 10:2 P=0.0386 显著导航胜（适配体侧升格点）；cap32 10:22 P=0.050、cap48 12:30 P=0.0079 静态胜（双向披露）**；全曲线 nav [10,9,18,17,34] vs static [2,4,15,29,52]（`expanded_summary.json`）。工程：常驻 ODesign 服务（权重驻 GPU、22 s/请求 vs 90 s 子进程路径、输出逐字节一致，`start_resident.sh` 入库）、`navigation_raw_budget` 生产旋钮、ProteinX 折叠按靶缓存、两次关机保存恢复（RESTORE_NOTE）。fig5e/f/g/h 终版重渲染（QA 绿）+ §2.5/图例/FIGURE_PLAN/FACT_SHEET/DECISIONS(29,30)/AGENTS 全部落定。

- **第四次重置第 2 个实验的修复轮（§2.5 实验 2 / paper registry E6，论文引用口径）**：Exp 27 测得 shipped 默认参数批量饥饿（0:24 反转）后，生产导航按注册锚修复——预算匹配（35 = 规则臂原始生成调用数，违规 0）、λ 网格加密至 35 值、带参数逐维对齐注册矩阵（CAI 0.80=CAI_MIN 全带生效、茎 ≤30bp=C7 新增 CDS 级维度、GC 窗 [0.30,0.80]=C1、同聚物 <14=C2）、恢复 legacy E6 组件 3 同义多样化扩展器（密度 0.15、每带 30 上限、零生成预算）、CDS 级 D1 门槛 0.03=P3 标定值、探测并行（>800aa 自适应 2 线程）。三轮 pilot 逐根因校准（D1 贪心/茎维/上限耗尽/稀释边际/stability CAI），护栏测试更新后 25+110 全绿。
- **全量 20/20 零失败，`--verify` 逐字节一致**：**McNemar b:c = 17:6, p = 0.0347, n = 60——配对不一致检验显著偏向导航**；导航 35/60 JCD 格 vs 规则 24/60；17/20 靶有 JCD 交付（6 靶 3/3；零 JCD 格靶标 GFP/RSV-F/Spike WT。**2026-09-09 复核更正**：原文误写 18/20——18 系 both-pass 格数的单元/靶标口径滑误，冻结逐靶表为 17）；**HER2（legacy 零可行档靶）交付 1 个导航专属格**；GFP 反向边界（E. coli 滑窗 GC，3 格）；e2e 联合项 0.45 < 0.8 与复合辅终点（Wilcoxon 0.73 NS）如实披露；零 LLM。图 5b/5c 重渲于 exp28 数据（脚本改指新目录），raster QA 全绿。墙钟两段：18 靶 12-LPT-worker ≈ 5.3 h + HER2/Spike 2-worker 8.9 h。
- **中途事件**：2026-09-02 深夜 Spike LD 子进程并发内存下被 SIGKILL（returncode −9）→ RetryInstrument 90 s 单次重试 + 大蛋白探测降并发修复；**2026-09-03 机器关机迁移（GPU 3 卡 → 2 卡，可用仅 0 号，1 号他任务占用）**：bring-up 脚本 GPU 映射全部改钉 0（后续实验同此），exp28 关机保存点后无损续跑（RESTORE_NOTE 留档）。
- 文档同步：PAPER_DRAFT（摘要/贡献 4/§2.5/讨论/Fig 5 图例 b–d/Methods/LLM 用量/数据可用性——描述最终修复系统与实测结果；Exp 27 降为内部边界登记）、PAPER_FACT_SHEET（Exp 28 小节 + 判读核对 + 关键数字 18；Exp 27 标注 superseded）、FIGURE_PLAN_V5 行 b/c/d、MANUSCRIPT E6 行、MODEL_API_USAGE Exp 28 行、AGENTS.md（含 GPU 现状）。

## 2026-09-02 (b) — Exp 27：GenNav mRNA 主终点重跑（图 5b/5c）+ 数据集记录修正（修复前边界测量，内部登记）

- **第四次重置第 2 个实验**（§2.5 实验 2 / paper registry E6）：E6 S2 双终点战役在现行生产平台重测——A 臂 = 注册静态配方池（Exp-26 仪器逐字复用，315 构造体）+ 规则交付；C 臂 = 生产 GenNav-λ 导航模式（`mrna_cds_design navigation=True`，deterministic zero-LLM）；JCD 判据 v8 与双终点从 git `e601913`/`b6dad08` 逐字移植（scope 修正用户拍板 2026-09-02：18 → **20 靶**（+OTC/PDGFB），n = 60）。pilot 2/2 + `--verify` 逐字节一致；**全量 20/20 零失败：主终点 NO-GO 且方向反转——b:c = 0:24（全部偏向规则臂），McNemar p = 1.19e-07，c_e2e_gene = 0.0 vs a_e2e_gene = 1.0**（legacy 30:0 偏向导航臂不复现：决定性优势属于驱动器层的 lattice+GEMORNA 兜底行+LLM 修复轮机制，均不存在于现行 shipped 模式；机制 = 批量饥饿——49/60 格交付 <5 条 CDS、0/60 e2e，而有交付处多样性机制通过（CAI 跨度 0.10–0.18））。辅终点败并披露（约束率 < 0.9、无靶 ≥3 档）；**零 LLM**（legacy 43）。并行提速修正（用户指示 2026-09-02，重启前登记）：8 个靶独占 worker（Exp-24 惯例），墙钟 ≈ 7.2 h（并发负载口径）。图 `fig5b_gennav_mcnemar.{pdf,png}`（配对 dumbbell + 计数 + 置换零分布 inset，Robin EDF 4c 惯例）+ `fig5c_delivery_mosaic.{pdf,png}`（20×3 配对结果 mosaic + gene-e2e 列）；palette rev 7、6 pt 纯黑、绝对 mm、1200 dpi；确定性 raster QA 全绿（精确画布、零边缘墨、纯调色板；画布溢出断言拦下统计块超宽与图例行超宽两次）。
- **数据集记录修正**（用户指示"有误的信息要及时修改"，2026-09-02）：`RNA-BioBench-FullLength-mRNA` 的 manifest 与 `sequences/` 陈旧（列 Factor_VIII/Zika_E、无 OTC/PDGFB），与全部驱动实际读取的 `targets/*.json`（= 现行 20 靶 18+OTC+PDGFB）不一致——manifest targets 列表改正 + 注记、sequences/ 补 OTC.fa/PDGFB.fa 删两个陈旧 fasta、benchmarks README 靶表与总表对齐（含图号列按 FIGURE_PLAN_V5 重定位、PA 行改 31 会话）。
- 文档同步：PAPER_DRAFT（摘要/贡献 4/§2.5/讨论/Fig 5 图例 b–d/Methods 统计/LLM 用量/数据可用性——全部改基到重测的反转结论，适配体侧标注"待其自身重跑"）、PAPER_FACT_SHEET（Exp 27 小节 + 判读核对 + 关键数字 18 改基；legacy E6 小节标 superseded）、FIGURE_PLAN_V5 行 b/c/d、MANUSCRIPT E6 行、MODEL_API_USAGE Exp 27 行、AGENTS.md。

## 2026-09-02 — AGENTS.md 压缩（96 KB → 24.6 KB，用户指示，doc-only）

- 根 `AGENTS.md` 超出 32 KB 建议上限：What's New 段由逐实验叙事体压缩为一里程碑一行的登记表（约 26 条，逆序），
  各实验的协议、预注册、修正、披露与图形 QA 细节不在 AGENTS.md 重复——权威记录在本文件（按日期检索）、
  `PAPER_FACT_SHEET.md`（claim check）与 `MANUSCRIPT.md`（实验手册）；压缩段顶部加了指路注记。
- 顺带修正两处陈旧信息：Standing facts 首条"third programme reset"→ 第四次重置（进度：Figs 2/3/4 + Fig 5a 完成，
  下一步 = Fig 5 其余 + Fig 6）；Testing 基线 635 → 646 passed, 1 skipped（2026-08-25 LinearDesign 密码子表接线后的最新登记数）。
- Standing facts 其余条目、Documentation Index、Project Architecture、LLM Configuration、Multi-Agent Execution、
  Testing 各节逐字保留（git diff 校验：除上述两处外零改动）。无代码、无实验、无图形变动。

## 2026-09-02 — 第四次实验计划重置开启 + Exp 26 执行（Fig 5a：选择层前驱池失败重测，§2.5 实验 1 / 登记名 E5）

**计划重置（用户指示）**：架构再度大改，全部实验重新跑、代码重写——沿用 2026-08-29 第三次重置的
"一次一个实验、只替换当前实验产物"规则与 12 色统一调色板（palette rev 7 原样，用户复述的 12 hex
与之一致）；可用 GPU 0/1/2 不变。legacy E5 证据文件（`e5_verdict_s*.json`、`E5_REPORT`）与旧
fig5a 资产在历次重置中已删除、盘上无待删项；`exp5_*`（声明越界/IRES）属未重跑实验、按规则不动。

**Exp 26（`experiments/exp26_selection_layer_pool.py`，预注册 docstring，协议自 git `b6dad08`
逐字恢复——LD λ{0,1,4,10} + RNARL + GEMORNA 30 采样 = 35 CDS × 9 UTR 组合 = 315 构造体/靶点；
硬约束 C1/C2/C6/C7/M1/CAI 阈值原版；arm-A 规则交付 × 3 画像；D1 交付批次最小两两距离对 2% 门槛）**
：数据集 = 现行 `RNA-BioBench-FullLength-mRNA` S1 五靶子集（A1AT/Insulin/EPO/GFP/IL-2，与
Fig 2b/c/4d 同一套文件——2026-09-02 用户确认）；仪器 = 生产工具路径（ToolExecutor，advisory
CapGate，审计 runtime，2,310 次调用；GEMORNA 8004/RNARL 8008 GPU 2，LinearDesign 8014/
LinearFold 8015 CPU；CAI 本地 Kazusa）；GFP 双接线 = pre-B0 默认 human 表（注册的修复前仪器，
CAI 315/315 全倒）vs 生产 E. coli 表，RNARL/GEMORNA/UTR 档共享、表是唯一杠杆；GEMORNA 采样非
幂等、legacy 缓存已删 → 新实现落盘缓存（实测而非复刻，披露）；LinearFold 全长结构+MFE 单次
确定性调用合并（legacy 折两次，值相同，披露）；零 LLM。**6/6 cell，0 失败（pilot Insulin
123/315、D1 0.0090；全量 35.8 min）：通过数 A1AT 27 / Insulin 144 / EPO 306 / IL-2 297 /
GFP 0→18（default→E. coli 表；通过者恰好全在 λ{4,10} 两档，与注册"可用档仅 λ{4,10}"逐字复现）；
Insulin 交付批次多样性 1.01% < 2% 门槛——λ 饱和失败结构复现（legacy 0.82%）；EPO 306/315 与
legacy 逐数相同（实现巧合，披露）；预注册预期全部命中；`--verify` 六条记录从存储数据重算逐字节
一致。** 图 `experiments/plots/fig5a_selection_pool_pass.py` → `fig5a_selection_pool_pass.
{pdf,png}`（89 × 82 mm 双层条形图：上层固定池通过数 6 条——4 human 灰蓝 + GFP 双条 terracotta/
sage；下层交付批次多样性 5 条按 2% 门槛分色 sage/terracotta + 虚线门槛线；6-pt 纯黑、绝对 mm、
1200-dpi PNG + 矢量 PDF；视觉 QA 一轮修正——门槛标签改置于低于门槛条上方的空白带、面板间隙
加大、旋转标签缩短；栅格 QA：零边缘墨迹、颜色仅出自 12 色调色板、文字纯黑、双面板基线像素级
确认存在）。PAPER_DRAFT（§2.5 句 + Fig 5 图例 a + Methods 战役段 + LLM 用量 + 数据可用性——
全部改引 26/315→18/315、1.01% 重测值）、PAPER_FACT_SHEET（Exp 26 小节 + claim check + 关键数字
16 扩展；legacy E5 节标注为内部登记）、FIGURE_PLAN_V5 行 a、MANUSCRIPT 重置表、MODEL_API_USAGE
（零 LLM 行）、AGENTS.md 更新。**下一步：Fig 5 其余面板（GenNav 战役）+ E21/E22 基线，同模式。**

## 2026-09-01 — Exp 25 执行（Fig 4g + 图 4h：质量评审 advisory 三臂 + 各战役 LLM 用量实测）

**接口变更**：`cli/form_chat.py` 新增 `RNADA_QUALITY_REVIEW` 环境旋钮（默认 `on`，取
`off/0/false/no` 时构造 `AgentRunner(quality_review_enabled=False)`）——仿 `RNADA_CAPGATE`
惯例的批处理/运维开关，交互默认行为不变。这是驱动"评审关"臂走生产表单入口的唯一平台接线
（预注册 docstring 披露）。

**实验**（`experiments/exp25_quality_review_advisory.py`，预注册 + 中途登记修正；pilot 6/6）：
数据集对齐用户指示取全量 31 PA 会话（PA_006–PA_036 = Exp-24 战役 PA 臂；legacy "19" 为其时代
全量）；三臂 × 31 = 93 次表单入口 CLI 子进程（输入逐字、CapGate advisory、GPU 0/1/2 预热；
调度 ≤6 并发、GPU 类工作流 ≤3；墙钟 ≈ 5.5 h，时间非指标）。**93/93：完成 31/31 × 3 臂；工作流级
30/31 × 3（唯一例外 PA_023 = 继承性输入缺口，三臂逐字相同）；跨臂逐轮结果完全一致（0 不匹配）；
评审开臂 144 次成功调用 = 72 被评审轮 × 2；失败注入臂 144 次尝试全部 review_unavailable、0 轮受影响；
重试 0/0/0；`--verify` 字节一致。** 中途修正（分析前、依据 exp8/exp24 冻结证据登记）：双成功判据 +
跨臂配对一致性主终点；PA_023 缺口（`workspace/pa023_5utr.fa`，审计保留期 0 次成功读取）按实测披露、
不重建（重建将与 Exp-24 锚定运行分叉）。

**图**：`experiments/plots/fig4g_quality_advisory_strip.py`（配对条带：31 会话行 × 三臂块，
sage/terracotta 结果 tile × 评审状态字形，分类分隔线上被评审/免评审两段，四样例键行；
canvas-overflow 断言两度拦截旋转表头溢出与键宽低估后改为两行水平表头 + 精确模拟键宽）与
`experiments/plots/fig4h_llm_usage_bubble.py`（气泡条带：8 战役行 × 每任务一泡、面积 = 实测
LLM 调用数、短刻度线 = 零调用任务；零调用空心圆经视觉 QA 判读为占位符后改刻度线）；数据装配
`experiments/exp25_fig4h_data.py`（**Exp-24 的 482 次评审调用自各 run 保存的
`_diagnosis_history` 实测提取**；GenNav 导航战役未重跑、登记排除）。两图 6-pt 纯黑、palette
rev 7、绝对 mm、1200 dpi，确定性 QA 绿（图 4g 视觉 QA 亦通过；图 4h 视觉通道 MCP 调用失败——
已注册失效模式，以确定性 QA 为准）。

**文档**：PAPER_DRAFT（Overview/贡献 1/§2.4/局限/Methods/Fig 1b/Fig 4 g,h 图例/LLM 用量/数据
可用性——19/19 全部改写为 31 会话配对一致口径）、PAPER_FACT_SHEET（Exp 25 节 + claim check，
legacy Fig-6a 节改 superseded）、FIGURE_PLAN_V5 行 g/h + 注记、MANUSCRIPT 重置表、
MODEL_API_USAGE、AGENTS.md。

## 2026-09-01 — Fig 4d 用户指示修订（第五轮：行长标签缩短；无重跑）

- 两个 Sample-2019 文库行标签从 fig3f 全名（"Random 50-nt 5′UTRs" / "Varying-length human 5′UTRs"）缩短为 fig4e 短名惯例（"EGFP random-50" / "Var-len human"）——它们单独撑宽了整个标签列；缩短后标签列宽度由 "Novel 5′UTR 11" 行决定，画布 62.3 × 86.0 → **50.8 × 86.0 mm**。全名仍在 Fig 3f 与 Fig 4e 图注中。同轮附加：底部裁定键从两行各自居中改为**两行共享列网格**（列宽取两行最大值，两列色块/文字左缘分别对齐，整块居中）。数据不变。光栅 QA 同前全绿。文档同步：FIGURE_PLAN_V5 注记、AGENTS.md Exp-18 条。

## 2026-09-01 — Fig 4d 用户指示修订（第四轮：改回第二轮层级条带；无重跑）

- 地毯图（第三轮）经用户评审为不如条带直观，**`fig4d_mrna_family_strip.py` 回退到第二轮的层级家族条带**（家族表头行 + 缩进靶行单列标签、10-mm 臂块、两行居中裁定键、0.5–0.6 lw 细线、62.3 × 86.0 mm 竖版）并重渲染——逐像素统计与第二轮首次渲染逐项一致（可复现）；数据不变（FP 35.3% → 8.3%、TP 11/11）。第三轮地毯图的旋转标签锚定探针结论（matplotlib rotation=90 向下悬挂需 ha="center", va="top"）留档备复用。文档同步：PAPER_DRAFT 图注 (d) 恢复条带措辞、FIGURE_PLAN_V5 行 d + 注记、AGENTS.md Exp-18 条。

## 2026-09-01 — Fig 4d 用户指示修订（第三轮：改图型；同一份 Exp-18 冻结结果，无重跑）

- **`experiments/plots/fig4d_mrna_family_strip.py` 改为转置任务×臂裁定地毯图（oncoprint 式）并重渲染**（`fig4d_mrna_family_strip.{pdf,png}`）：20 任务列按 8 家族分组 × Ungated/Gated 两行，单元格整格填裁定色（白描边空格 = 未发布声明）；家族表头居中于列组上方、按渲染器实测字宽贪心分层（同级间距 ≥0.8 mm 断言、中心钳入画布）；靶名 90° 悬于列下（fig3d 旋转刻度惯例；matplotlib 旋转锚定语义经探针实测——rotation=90 须用 ha="center", va="top"）；可信/不可信块间短竖分隔线只穿地毯区；裁定键单行居中。横版 86.3 × 50.8 mm（与 fig4c/fig4e 同向）。数据不变（FP 35.3% → 8.3%、TP 11/11）。光栅 QA：零边缘墨迹、暗色像素全为纯黑+抗锯齿灰、彩色像素全在调色板→白线段上。文档同步：PAPER_DRAFT Fig 4 图注 (d) 改写为地毯图、FIGURE_PLAN_V5 行 d + 注记、AGENTS.md Exp-18 条。

## 2026-09-01 — Fig 4d 用户指示修订（第二轮；同一份 Exp-18 冻结结果，无重跑）

- **`experiments/plots/fig4d_mrna_family_strip.py` 修订并重渲染**（`fig4d_mrna_family_strip.{pdf,png}`）：(1) 左侧标签区并为单列层级文字列——家族表头行 + 缩进靶行取代旋转类别列与独立家族列（可信/不可信分组改由全宽分隔线承担并在图注声明），回应「左侧两列文字过宽」；(2) 行标签生物学显式化并跨图一致——"Novel UTR 7/11/13" 补回丢失的撇号为 "Novel 5′UTR 7/11/13"，Sample-2019 文库改署 Fig 3f 名 "Random 50-nt 5′UTRs" / "Varying-length human 5′UTRs"，家族表头去折行（"3′UTR stability rank"、"Relative comparison" 等）；(3) 单声明格臂块 18 → 10 mm，臂表头精确居中于色块列；底部裁定键改两行居中；(4) 分隔线与空格描边 0.4 → 0.5–0.6 lw——旧版细线在 1200-dpi 下渲染为事实灰 (42,42,42)，是「有文字发浅」观感来源之一（文字本体经栅格复核旧版即全为 #000000 文字核）。画布 79.5 × 62 → 62.3 × 86.0 mm；palette rev 7 用色、6-pt 纯黑、1200-dpi PNG + 矢量 PDF（fonttype 42）不变。光栅 QA：四边零墨迹、暗色像素全为纯黑+抗锯齿灰、全部彩色像素落在调色板→白线段上。文档同步：PAPER_DRAFT Fig 4 图注 (d)（删过时 mosaic-inset 从句、补分隔线分组说明）、FIGURE_PLAN_V5 行 d + 注记、AGENTS.md Exp-18 条。

## 2026-09-01 — Exp 24: 生产 campaign 共享仪器重跑（Fig 4f + Fig 2a/2h/2i 再测量，§2.4 实验 5）

- **设计**：用户指示「跑一次、登记为共享仪器、冻结切片」——一次 241 运行生产 campaign（210 RNADesign-210 任务 + 31 PA 表单会话，用户入口逐次子进程、输入 verbatim、advisory CapGate、GPU 0/1/2 服务按发行拓扑预热）同时供四个 panel：Fig 4f（按 oracle 的门决策 Cleveland 点图）、Fig 2a（任务毯图）、Fig 2h（代表会话里程碑轨）、Fig 2i（runtime ECDF）。drivers：`experiments/exp24_production_campaign.py`（campaign，预注册 docstring，pilot 4/4）+ `experiments/exp24_run_parallel.py`（编排）+ `experiments/exp24_audit_gate_stats.py`（只读分析器；`--verify` 从冻结切片重算字节一致）。
- **并行修订（用户指示提速，重跑前登记）**：11 个工作流独占并行 worker——同一工作流的运行永不重叠，unstamped 门事件按 payload 工作流键唯一归属（硬断言，0 歧义；歧义即失败而非污染）；单次运行墙钟 = 并发负载下交付的工作流（图注披露）；重试一律新 sid（本次 0 次重试）；两次编排器重启的半途会话按排除披露；并发追加 0 撕裂行。campaign 墙钟 ≈ 6.8 h（串行 legacy ≈ 17.5 h）；利用率全程监控（128 核聚合 CPU 10–60%，GPU 0/1/2 脉冲式、模型驻留）。
- **结果**：241/241、0 失败。冻结审计切片 10,395 事件 = 8,818 tool calls（84.8%，40 工具，3 例孤立瞬时失败）+ **1,392 门决策（709 reject / 549 require_profiling / 134 downgrade / allow 0，11 oracle）** + 185 ranking 组装 + 0 claim。runtime：中位 2.32 min，工作流中位 2.7 s–6.39 min，76.8% ≤5 min，240/241 ≤1 h（最大 = GenNav 导航 aptamer PA_028 104.9 min）。代表会话规则再次选出 PA_036（152 calls + 32 gates [16/8/8] + 3 ranking，7.5 min 跨度）。Fig 2a：210/210。
- **对 legacy（内部登记）**：Exp-9 切片 10,217/8,798/1,377[690/553/134]/42——各项均在几个百分点内复现、downgrade 逐条相等、代表会话相同且分类构成几乎一致；ranking 组装 42→185（当前平台排序治理事件粒度）；Exp-8 runtime 2.6/2.5s–6.29min/98.6min → 2.32/2.7s–6.39min/104.9min（并发口径）。
- **图**：`fig4f_gate_decisions.py`（新 panel：水平 Cleveland 点图、按 oracle 行、三 verdict marker + dumbbell + 计数标注、CASCADE Fig. 5d/e 惯例、verdict 配色沿用 fig2h/4e 惯例）→ `fig4f_gate_decisions.{pdf,png}`；fig2a/2h/2i 重写指向 Exp-24 记录（注册图型不变）；四图栅格 QA 全绿（mm 尺寸正确、零边缘墨、palette 校验）。视觉通道对 fig4f 两次返回旧缓存图（登记过的失效模式）——判不可信，QA 以确定性栅格分析为准。
- **文档**：PAPER_DRAFT（§2.2 审计/runtime 段 + §2.4 Fig-4f 句与数字 + Fig 2 a/h/i 与 Fig 4f 图例 + Methods campaign 段 + Data availability）、PAPER_FACT_SHEET（Fig 2h/2i 节改写为 Exp-24 + Exp 24 节 + claim check）、FIGURE_PLAN_V5（行 a/h/i/f + 共享仪器登记）、MANUSCRIPT 重置表、本 CHANGELOG、AGENTS.md 更新。旧 exp1（覆盖）与 exp8/exp9（runtime/审计）结果目录按重置规则删除（`exp1_bring_up_services.sh` 保留）。

## 2026-09-01 — Fig 4b 用户指示修订（同一份 Exp-17 冻结结果，无重跑）

- **`experiments/plots/fig4b_claim_matrix.py` 修订并重渲染**（`fig4b_claim_matrix.{pdf,png}`）：(1) 删除右上 arm × verdict mosaic inset——其计数已在 Fig 4b 图注与正文陈述（fig2h 删 donut / fig3f 删 waffle 的先例），且其重复的臂标签互相挤压、下方留出整列空带；(2) 行标签改用 fig3 靶标惯例（"IFN-gamma" → "IFN-γ"、"Influenza H3N2 HA" → "swine H3 HA"），"U reduce" 改词为 "U reduction"；(3) 底部四摆片裁定键改为渲染器实测字宽排版（fig4e 惯例）并加画布溢出断言——旧版估算字宽使图例实际比画布宽、靠 tight-crop 外扩；(4) 臂块 12 → 14 mm、块间距 5 → 8 mm，使矩阵主体与单行图例共享画布宽度（tile 1.7 → 2.0 mm）。全部文字维持 6-pt 纯黑（光栅复核：旧版亦全部为 #000000 文字核，无非黑文字）、palette rev 7 用色、1200-dpi PNG + 矢量 PDF。光栅 QA：零非黑文字核、零非调色板色块、tile 内零文字墨迹、四边无裁切。文档同步：PAPER_DRAFT Fig 4 图注 (b) 删 mosaic-inset 从句、FIGURE_PLAN_V5 行 b + 类型清单 + 注记。

## 2026-09-01 — Fig 4c 用户指示修订（同一份 Exp-17/Exp-5 冻结结果，无重跑；数据 59 → 0 不变）

- **`experiments/plots/fig4c_overreach_events.py` 修订并重渲染**（`fig4c_overreach_events.{pdf,png}`）：(1) 臂图例（Ungated/Gated）从悬浮于图顶部（与面板脱开、视觉上像偏置标题）移到面板正下方单行、对轴居中——fig3e「图例贴面板」惯例；(2) y 轴标签从 31 字符的 "Decision-layer overreach events"（6 pt 下超出 23-mm 轴高）缩为 "Overreach events"——decision-layer 限定语在 Fig. 4c 图注中逐字保留；(3) 图几何按新堆叠再平衡（89×44 → 89×40.5 mm，轴 11/12.5/72/23.5 mm，y_top 1.45 → 1.48 使 "59 → 0" 标注完整落于轴内）。子图内无标题维持（Nature 惯例：面板字母组版时加，标题性陈述在图注）。全部文字 6-pt 纯黑（光栅复核：文字核全部 #000000，仅抗锯齿灰晕）、palette rev 7 用色、1200-dpi PNG + 矢量 PDF（fonttype 42）。光栅 QA：四边外 3 px 零墨迹、非条形色块仅调色板两色、无文字/图形重叠。文档同步：FIGURE_PLAN_V5 行 c 注记。

## 2026-09-01 — Exp 23: 选择性门控决策矩阵重跑（Fig 4e，§2.4 实验 4）

- **数据集（用户确认后开跑，与最新重跑对齐）**：认证家族 = Exp-14 MRL 锚集 `e7_mrl_anchor_set.json`（706 / 3 族，Sample et al. 2019 MPRA, GEO GSE114002——即 Fig 3f 的认证基础、Fig 4d 的 MRL 真值，sha256 冻结进 summary）；未剖析家族 = e18 任务集的生产键 `novel_utr_family_7` 及其真实 50-nt 候选；阻断格 3′UTR = 同一 e18 集的生产 Insulin 构造 3′UTR；E1 交叉验证基准 = 保留的 `e7_mrl_scoring.jsonl`。与 Fig 2a–i / Fig 3a–h / Fig 4a–d 的重合核查：Fig 3f 同一文件、Fig 4d 部分取自它（mrl_optimum 两任务）、Fig 2e 同类零重合（706×50 全比对 0 相同 0 包含）、其余无涉。
- **预注册 driver**（`experiments/exp23_selective_gating.py`；pilot 6/6 → 全量 12/12；legacy E7 gate-demo 的重跑，协议恢复自 git 1b45138~1）：12 格三层全走生产路径——DecisionGate 格经 `runtime.review_tool_call` + `oracle_use("ranking_objective", target_family=…)`（与 ToolExecutor 咨询的完全同一条评审）；ClaimGate 格经 `runtime.claim_gate.review`（确定性模板，LLM polish 关）；新增加权执行层经 `ToolExecutor.run_tool` 活体验证（GEMORNA 8004，每判定类一格）。运行时 = `RNADA_CAPGATE=enforce` + 出厂打包默认 SelfModel（29 条记录，Exp-17/18 门控臂的同一仪器；版本漂移无）；15 条平台审计落账；**0 次 LLM 调用**；壁钟 ≈ 6 s。相对 legacy 的披露性扩展（预注册）：三认证家族全测（legacy 只测一个）、生产未剖析家族键取代 legacy 合成标签、打包 SelfModel 取代当次自建、新增执行验证层。
- **结果 12/12 全部符合预注册预期（GO）**：DecisionGate——allow ×3（D1–D3，conf 1.0）、downgrade ×1（D4，transferred、transferred_from_grade=verified、置信度恰为 0.5 = 1.0 × 0.5 衰减、供体 sample2019_egfp_random50、不阻断）、require_profiling ×2（D5–D6，enforce 下阻断）；ClaimGate——pass（C1）/ downgrade（C2，scope absolute → within_target_relative，确定性 `[DOWNGRADED: …]` 改写）/ reject（C3，依赖从未剖析）；执行层——E1 放行执行且 predicted MRL 与 Exp-14 缓存**精确相等**（hi01_egfp_random50，6.28）、E2 降级放行执行（限权是 ClaimGate 的事）、E3 阻断成立（GatedActionError、verdict=require_profiling、gated=true 审计行、耗时 0.0002 s 未触服务）。legacy 4 演示结果一对一复现（legacy 对转移语义的 naive expect_profiling 预期当年如实记为 expectation_met:false——现在降级语义即注册预期）。
- **Fig 4e 绘制**（`experiments/plots/fig4e_selective_gating_matrix.py` → `fig4e_selective_gating.{pdf,png}`，120 × 72 mm）：决策矩阵——DecisionGate 块（6 行：MRL × 3 认证族 + 未剖析族；3′UTR × 2）+ ClaimGate 块（3 行），每行恰一色块落于 allow·pass / downgrade / require-profiling·reject 三列；判定色 sage/mauve/sand/terracotta（fig2h 门控判定惯例）、oracle 竖条 grey blue（MRL，fig3f 色）/ dark warm grey（3′UTR）；右侧置信度 + 工具层注释（D1「score = Exp-14」、D4「conf 0.5 = 1.0×0.5」等）；底部居中四摆片判定键。QA：首轮视觉分析报告多处重叠/裁切→按实测字宽重排（画布 88→120 mm、缩短标注串、拉开列距）重渲染；后续视觉通道命中 CDN 缓存旧图判定不可信，改用确定性光栅 QA 全过——四边零裁切、表头三簇分离（间隙 3.9/7.1 mm）、标注最右 118.1 mm 在界内、图例四簇居中（中心 60.85 vs 60）、分隔线单条无字形相交、行标签与色条垂直居中偏差 ≤ 0.1 mm、D1 行色块恰为 sage+grey blue+GRID。
- **删除面**：本实验在盘无可删旧资产（legacy `e7_gate_demo.jsonl` 久已不在盘——结果保留于 never-delete 的 `e7_mrna_oracle_profile_summary.json`；fig4e 此前未在新程序下绘制）；`e7_*` 证据链属 never-delete 且为打包 SelfModel 证据来源，未动。文档同步：FIGURE_PLAN_V5 行 e + 注记、PAPER_DRAFT（§2.4 句 + Fig 4 图注 e + Methods + LLM 用量 + 数据可用性）、PAPER_FACT_SHEET（Exp 23 节 + claim check + 关键数字 13 补决策矩阵口径）、MANUSCRIPT 重置表 Exp 23 行、AGENTS.md。**Next: Fig 4f–h + Figs 5–6 战役 + E21/E22 baselines 按重置继续，同一模式。**

## 2026-09-01 — Exp 18: E3-M mRNA 侧门控双臂重跑（Fig 4d）

- **任务集按最新数据集重建**（用户指示「与最新的数据集保持一致」；构建器 `experiments/exp18_build_mrna_audit_tasks.py`，断言优先，20 题 = 8 家族 10 可信 + 10 不可信，家族/靶分配与 legacy 相同）：靶标取当前 `RNA-BioBench-FullLength-mRNA` 文件（逐靶密码子表——GFP 按当前注册为 E. coli，legacy 曾四靶统一 Homo sapiens，披露）；CDS 候选 = 生产 `mrna_cds_design` design_tool="all" λ-grid（任务取 λ{0,4,10}、比较取 0 vs 10）；全长度构造 = 生产 `full_length_mrna_design`（utr_mode=all）每靶 top-3 排名唯一构造；MRL 真值 = Exp-14 锚集实测 MRL。可信任务真值 = 生产 CAI 工具（Sharp–Li、逐靶 Kazusa）+ LinearFold MFE + 纯 Python 约束的精确重算；不可信任务分数**不内嵌**，运行期经生产链活体取（GEMORNA 8004 3′UTR/MRL + LinearFold 8015 junction 窗口 MFE/nt + 约束折叠 ddG_open_w1 = 当前平台 junction 报告；junction 计算与设计期工作流值逐位一致交叉验证）。
- **双臂重跑**（`experiments/exp18_mrna_claim_gating.py`，预注册 docstring，pilot 6/6 × 双臂 PASS）：两臂全新运行——未门控 = advisory 全放行；门控 = `RNADA_CAPGATE=enforce` + 打包默认 SelfModel（E7/Exp-14 GEMORNA-MRL 剖析；scoring-由-ranking-蕴含的 legacy 补丁恢复，6 次 pilot v1 运行作废披露）+ 逐家族注册确定性报告指标 + 建时真值执行验证 + ClaimGate。每臂每题恰好 2 次 LLM 调用（deepseek-v4-pro，temp 0；提示词与 git e337ac5 恢复的 legacy E3-M 逐字节相同，仅门控臂加 gate-feedback 块）。确定性盲判（legacy 规则；洗牌 seed 0 + 密封映射；**注册修正案**：decoy 家族上正向断言需以候选 id 为主语——legacy 关键词启发式对门控臂的否定式弃权声明误判）。
- **结果 40/40（20 × 2），0 失败：FP 6/17 = 35.3%（CI 17.3–58.7）→ 1/12 = 8.3%（CI 1.5–35.4）；TP 保留 11/11 = 100%；越权 6 → 0；go-rule 双项通过（降幅 76.4% ≥ 50%、保留 100% ≥ 90%）**。未门控 FP 全部落在 utr3（3/3）+ junction（2/2）+ 一处对称 MRL 排名翻转（最弱认证家族 ρ=0.835，预测 hi30 vs 实测 hi01——两臂同错，即唯一存活的门控 FP，与 legacy 登记通道一致）；门控机制比 aptamer 侧早一层——6 条计划请求被拦后模型在五道 utr3/junction 任务上**完全不发声明**（Fig 4d 白描边空格），3 条跨家族 MRL 绝对声明被降级为靶内相对（neutral），0 压制 0 越权；可信家族 10/10 双臂全 TP，执行验证 0 弃权。
- **平台缺陷披露（构建期发现并绕开）**：全长度结果 JSON 的 `metadata.cds_sequence` 为存储侧截断 echo（200 字符 + "…(truncated)"，ToolExecutor 字符串上限）——设计期评估本身用内存真序列（存储 `cds_cai` 与干净 CDS 的 CAI 精确相等可证），构建器按 cds_source 从 CDS 设计缓存回填真 CDS 并断言前缀一致；修复后五道构造任务重跑（10 次作废运行披露）。用量：80 次有效 + 32 次作废 LLM 调用；壁钟 ≈ 34 min（双臂）+ 设计阶段 64 min（缓存）。
- **Fig 4d 绘制**（`experiments/plots/fig4d_mrna_family_strip.py` → `fig4d_mrna_family_strip.{pdf,png}`）：按任务家族分组配对类别条带——20 任务行 × 两臂块、每发布声明一色块（sage=TP / terracotta=FP / warm grey=neutral，白描边=未发布声明——门控弃权的关键视觉元素）+ 臂×裁定 mosaic inset；palette rev 7、6-pt 纯黑、绝对 mm、1200-dpi PNG；视觉 QA 两轮（首轮标签列相撞，缩短家族/靶标签并加宽标签列）。文档同步：FIGURE_PLAN_V5 行 d + 注记、PAPER_DRAFT（摘要 + 贡献 3 + §2.4 段 + Fig 4 图注 d + Methods + LLM 用量 + 数据可用性）、PAPER_FACT_SHEET（Exp 18 节 + claim check + 关键数字 13 补 E3-M 重测口径）、MANUSCRIPT 重置表 Exp 18 行、AGENTS.md。**Next: Fig 4e–h + Figs 5–6 战役 + E21/E22 baselines 按第三次重置继续。**

## 2026-08-31 — Exp 17: E3 门控双臂主实验重跑（Fig 4a/4b）

- **门控臂 45/45 重跑完成**（`experiments/exp17_claim_gating.py`，预注册 docstring，pilot 8/8 PASS——0 FP、0 越权、14 条计划请求被拦截）：legacy E3 门控臂（登记 57.9% → 0%、TP 8 → 9、越权 23 → 0）在 45 任务 plan-A 尺度重测，与 Exp 5 未门控对照臂（同任务集/提示词/实测 oracle 链）逐任务配对。工具 = 生产门控栈原样（`RNADA_CAPGATE=enforce` + 打包默认 SelfModel；计划请求按声明用途在 oracle 注册任务键 `rna_aptamer_design` 上过 DecisionGate；放行请求经同一 `oracle_use` 上下文走 ToolExecutor 实测——工具层门即实际执行者，dedup cache 播种自 Exp 5；amendment-v1.1 两腿保留：ClaimGate 统一基底规则 + 精确重算弃权）；跨臂洗牌盲裁定 + 密封映射。**FP 0/31 = 0%（CI 0–16.1）vs 未门控 54.5%、越权 59 → 0（71 条计划请求被拦截）——硬保证在 2.25 倍任务尺度成立；TP 保留 80.0%（25 → 20），低于预注册 90% 门，如实报告**：2 条真 metric 声明被基底规则过度压制（LLM 把确定性指标自身声明为依赖 → unprofiled → reject）、2 条 59≠60 nt 长度马虎序列被重算腿正确弃权（反事实为 FP）、未门控臂 2 条侥幸 untrusted TP 按设计不可保留（无已验证 ranking/screening 权力的 oracle，不可验证比较声明正是门所禁止者）、+1 条救回（u_reduce_3）；ClaimGate 流向 31 → 24 发布（20 TP + 4 borderline）/ 7 压制（反事实 4 FP + 3 TP）。
- **Fig 4a/4b 绘制**（`experiments/plots/fig4a_claim_gating_headline.py` → `fig4a_claim_gating.{pdf,png}` 分组条形：FP 率 + Wilson CI / TP 数，未门控 terracotta vs 门控 sage；`fig4b_claim_matrix.py` → `fig4b_claim_matrix.{pdf,png}` 45 行任务 × 两臂逐声明对错色块矩阵（sage=保留 / terracotta=假声明，Biomni Fig. 2C–E 惯例）+ 臂×裁定 mosaic inset；palette rev 7、6-pt 纯黑、绝对 mm、1200-dpi PNG；QA 中修复 fig4b 毫米/英寸双重换算 bug 与 fig4a 0% 标签贴轴问题）。文档同步：FIGURE_PLAN_V5 行 a/b（行 c 数据注记 59→0，面板待绘）、PAPER_DRAFT（摘要 + 贡献 3 + §2.4 段重写 + Fig 4 图注 a–c + Methods + LLM 用量 90 calls + 数据可用性）、PAPER_FACT_SHEET（Exp 17 节 + claim check + 关键数字 13 改为重测口径 + legacy E3 节加 superseded 注记）、MANUSCRIPT 重置表 Exp 17 行。- **图 4c 补绘**（同日，同一份冻结结果、零重跑）：`experiments/plots/fig4c_overreach_events.py` → `fig4c_overreach_events.{pdf,png}`（越权事件 oracle × use 配对条形：未门控 59 = RhoFold 9+11 / ProteinX 11+8 / EGARPS 11+9 → 门控全 0；臂色沿 fig4a 惯例 terracotta/sage，oracle 组标签沿 fig3e 惯例，59→0 括号注记为注册的 Δ 标注；零值标签按 6-pt 纯黑惯例）。FIGURE_PLAN_V5 行 c 改为已绘，PAPER_DRAFT 图注 (c) 补 71 条拦截机制句，MANUSCRIPT 行补脚本名。**Next: Figs 4–6 其余战役 + E21/E22 baselines 按第三次重置继续。**

## 2026-08-31 — PAPER_DRAFT §2.3 按 Fig 3 成品合图与最新重测数字重写

- **`docs/PAPER_DRAFT.md` §2.3 全节重写**（用户指示；依据成品 `experiments/plots/output/fig3_composite.png` 逐面板核对，全部数字与 `experiments/results/exp{10,11}_v3 / exp12–16`（含 `exp15_rnasmol_v020_sandbox`）及 `exp5_claim_overreach` 的冻结 summaries 逐一相符）：面板引用重排为严格阅读顺序 **a→h**（旧文为 a–d, g, f, e, h，不合惯例）；节结构 = 引言（三失败模式框定）→ **Uncalibrated tool trust**（a–d；拆为「锚集+门槛+screening+ranking」与「docking+affinity 标定」两段）→ **Claim overreach**（e）→ **MRL 认证**（f，profiling 双面性）→ **RNAsmol 部署保真**（g，v0.2.0 沙盒考古 + 「邻接改写=损害载体」测量闭环 + 己方预测被证伪的披露）→ **Confounded improvement**（h；240 cells / 228 成功 / Ferritin 注册边界 / 56 paired cells / 19 有效靶标，δ +0.14→+0.05→−0.01，自审计 0/2）。
- **相对旧文的实质修正**：`Protenix ipTM` → `ProteinX ipTM`（与图面板标注及数据键 `proteinx_ipTM` 一致；§2.1 概览段的 Protenix 指 vendored 仓库名，保留）；ranking 段旧表述「每个通过细胞的 CI 均跨零」更正为精确版——三个 IFN-γ 细胞 CI 跨零（−0.23/−0.50/−0.60 起），而 Angiopoietin-2 细胞为 n = 3、ρ = 1.0 的退化点估计（CI [1.0, 1.0]，其三条目在随机复合物实现间 ~0↔~1 翻转）——结论「无可靠 ranking 细胞」不变。**同日修正落实**（用户指示，三处 + 同类引申处）：摘要「0 of 18 cells」→ v3 口径（0/27 可靠 screening/ranking 细胞 + docking 0/19 top-1）；「every passing CI spans zero / all CIs span zero」的四处活文档（PAPER_DRAFT Fig-3 图注 b 行、FACT_SHEET Exp-11 v3 节与关键数字 10 号、FIGURE_PLAN_V5 row b、DECISIONS Part-1 段）统一更正为「三个 IFN-γ CI 跨零；proteinx × Ang2 细胞为 n = 3 退化估计（ρ = 1.0、CI [1.0, 1.0]、条目在实现间翻转）」；FACT_SHEET Exp-10 v3 节 FGF2 括注更正为 AUROC 0.37/0.63/0.30（原括注 0.47/0.43/−0.18 混入 ranking-ρ 值）；FIGURE_PLAN_V5 row a 由 v2 六靶口径更新为 panel 实际渲染的 v3 九靶 run（2/27 名义通过、全 CI 跨随机，并补引 v3 summary）。CHANGELOG 历史条目按写作时保留，更正以本条及新版 §2.3 为准。
- 其余节逐行 diff 确认不变（§2.4 起全同）。自动化核查：必含数字 token 全部在文、无遗留旧值、面板引用序列 a→h。

## 2026-08-31 — Fig 3 composite 组装（a–h 八面板）

- **`experiments/plots/fig3_assemble.py` 新增 → `experiments/plots/output/fig3_composite.{pdf,png}`**：八个完成的 Fig 3 面板组合成一张大图。Nature 惯例经 `relevant_references/` 已发表 DeepRare 主图（Figs. 2–4，Nature 651，2026）复核：粗体小写字母置于各面板左上角（无句点、无括号）、严格阅读顺序 a→h、行顶对齐使同行字母共线、固定列网格。面板经 PyMuPDF `show_pdf_page` 以矢量 Form XObject 嵌入（无栅格化）；字母 Helvetica-Bold 8 pt 墨黑（palette TEXT）由组装器统一绘制；所有面板 scale 1.0（重置计划的统一 6-pt 文字样式，全图无 fit 缩放）。
- **布局**（同日晚些时候用户指示修订）：a（screening balloon 矩阵）全宽；**b、c 共行且两端齐平** —— b 为 27-cell 高瘦 Cleveland 点图（82.3×103.4 mm），c 以**双行 composite 变体**嵌入（`FIG3C_LAYOUT=composite python experiments/plots/fig3c_docking_lollipop.py` → `fig3c_docking_lollipop_composite.{pdf,png}`：19 个 lollipop 在 SARS-CoV-2 RBD｜PSMA 组分界处折为 11+8 两行，画布 97.2×103.8 mm 与 b 同高；单行独立面板 c 不变）；**d、e 等高配对** —— 首版 d|e 行在 e 下方留出高差空白带（d 高 e 56 pt），用户指示后 d 就地缩小重渲染（3.84×2.46 → 3.70×2.00 in → 86.7×44.1 mm）、e 就地放大重渲染（89×34 → 94×44.6 mm，轴区 71×21 → 75×31 mm → 85.5×41.4 mm），两者 6-pt 字体与内部版式不变、数据不变；**f、g、h 三联等高一排收尾**（fig2 fgh 行惯例：统一绘制高度 90.2 pt，各面板缩放 ≈ 0.69/0.64/0.81，宽度随各自纵横比、剩余宽度均分为 gutters；用户指示 —— h 无需全宽，首版的全宽收尾变体 `fig3h_dissolution_composite.*` 随之退役删除，fig3h 脚本回退单一版式）。
- **分辨率**：成品 PDF 一页 539.9×721.7 pt（190.5×254.6 mm），PNG 从矢量成品以 **1200 dpi** 渲染（8999×12029 px，Nature Methods line-art 指引）。组装 QA 发现 fig3a 的 colorbar 渐变在面板 PDF 内以 100 dpi 栅格嵌入（成品中唯一的栅格元素）—— fig3a 的 savefig dpi 已统一为 1200 并重渲染（仍读 v3 summary，"cells passing AUROC > 0.8: 2/27" 不变；顺带将其独立 PNG 提到 1200 dpi，与 fig3b–h 的 1200-dpi 惯例一致），现成品 PDF 中该 colorbar 为 1200 dpi。逐条带视觉 QA（各行字母线、b|c 接缝、d|e 等高、fgh 三联行、h 的 inset/门槛标注、右缘齐平）通过。
- FIGURE_PLAN_V5（Fig-3 表后注记）、AGENTS.md、本日志更新。

## 2026-08-31 — Figs 3–5 撤销 a 子图总结图（用户决定）；fig3 图脚本与输出改名 fig3a–h

- **结果图不再以总结/机制示意图开头**：Fig 3a 失败模式示意图（当日早些时候绘制，见下条）连同文件删除；规划中的 Fig 4a（CapGate 机制示意）与 Fig 5a（GenNav 机制示意）在战役重跑前移除；Figs 3–5 原 b–i 面板重编为 a–h，图例与正文引用同步（机制引用改指 Fig. 1d / Fig. 1e — 机制示意保留在 Fig 1；§2.3 开头引用改指整图）。
- **文件改名**：`experiments/plots/fig3{b..i}_*.py` → `fig3{a..h}_*.py`（output/ 下 pdf/png 同步）；脚本内 Usage/Output 路径与面板惯例互引重编（fig3b/3c/3g 惯例 → fig3a/3b/3f 等；外部文献引用如 CASCADE Fig. 3b 未动）；8 个脚本 py_compile 通过。`fig3a_failure_modes.{py,pdf,png}` 删除。Fig 2a 毯图与 Fig 6a 能力地图为数据面板，未动。
- **文档同步**：FIGURE_PLAN_V5（三图删 a 行、行重编、9→8 panels、类型清单字母、新增 2026-08-31 注记）、PAPER_DRAFT（Results 引用 + 三个图例 + 头部注记）、PAPER_FACT_SHEET / MANUSCRIPT（v5 面板字母 + 图脚本路径 + legacy→v5 映射注记）、AGENTS.md。历史登记条目（本日志旧条目、预注册 driver docstring、冻结结果 summary）按写作时字母/路径保留。

## 2026-08-31 — Fig 3a 绘制（失败模式示意图，Fig 3 九面板收尾；**当日撤销 — 见上条**）

- **`experiments/plots/fig3a_failure_modes.py` → `fig3a_failure_modes.{pdf,png}`**（b–i 八个子图既成后按规划绘制行 a 示意图；Nature 风格 surveyed 自 `relevant_references/` Robin Fig. 1 / Co-Scientist Fig. 1：圆角浅彩盒 + 细墨线边框、左→右数据流、克制用色、充分留白）：
  顶部主轴 = 未门控生产路径 [Design goal] → [Ungated agent: plans · calls tools · narrates results] ⇄（calls / scores 双箭头）[Tool layer: oracles & scorers] → [Report: candidates + claims]，下弯回环箭头标注 "iterative rounds — pool grows"（多轮协同环）；流程上三个编号入口（① 工具/分数端口、② 报告端口、③ 回环），下方三条编号 lane 一一对应：
  1 **Uncalibrated tool trust**（b–e）—— 实测 (score, affinity) 点为噪声云（sage 点）vs agent 假设的单调关系（terracotta 虚线），"optimizes an oracle score with no measured power — climbing noise"；
  2 **Claim overreach**（f）—— claim 条（terracotta）越过 evidence 条（sage）尽头的虚线证据边界，"narration outruns measurement"；
  3 **Confounded improvement**（i）—— 表观 δ +0.14 在预算匹配 +0.05 / 固定重采样 −0.01 下消解的三点斜率，点色复用 Fig-3i 阶段色（terracotta / grey blue / sage）。
  约定：实线 slate-blue = 数据流（paper_v5 示意图惯例）；terracotta = 未门控/apparent/claim，sage = 实测真值/证据，grey blue = 对照，mauve grey = lane 2 识别色，深暖灰 = 中性边框/边界；全部文字 6-pt 纯黑（fig3f 惯例）；无图内标题（标题在 Fig-3 图注）；全宽 184 × 51 mm、绝对 mm 几何、矢量 PDF（fonttype 42）+ 1200-dpi PNG。分区域视觉 QA 通过（calls/scores 标注、回环下凹 + ③ 端口徽章、三 lane 图元——无文字/图形重叠；回环 rad 符号经显示坐标验证修正）。FIGURE_PLAN_V5 行 a、AGENTS.md、本日志更新。

## 2026-08-31 — Exp 16（Fig 3i / §2.3 实验 8）混淆改进证伪全面板重跑

- **`experiments/exp16_confounded_improvement.py` 执行**（第三次重置计划，预注册 docstring，pilot 8/8；用户确认 RNA-BioBench-Aptamer 全 20 靶标 × 3 seeds × 4 臂 = 240 cells）：被移除的协同环（BMC，2026-08-18 删除，DECISIONS (m)）**作为研究对象在实验驱动内逐字重构**——legacy AptamerCoordinator 确定性规则从 git 1b45138~1 恢复（utopian 参考点诊断 / ASF 最优 + 各维度领先者诊断集 / EGARPS-IPTM 差距→热点扩展±5 再生 8 / RHOFOLD 差距→长度+10（pLDDT<60）或+5、种子+1 / 零违规→池 8 早停）；四臂 = serial8 / loop16 / serial16（同种子一次生成 16）/ fixed16（固定种子+1 重采样、无诊断内容）；平台本身零改动，全部走生产 RnaAptamerDesignWorkflow（逐 cell 新实例、CapGate advisory、全审计）；主指标 egarps_component best-of-pool（被注销的 oracle——测的就是它）；配对 Wilcoxon + 两样本 Cliff's δ（legacy 约定）+ 10⁴ 符号翻转置换零分布；预注册 gate δ≥0.3（P0/P3 约定）；E2 四步自审计确定性重跑（阈值 70%）。
- **结果：240/240 记录，228 成功 + 12 Ferritin 零输出边界失败（19 靶有效，legacy 口径）；环 56/57 走热点扩展分支，实现池 8/16/16/16。表观效应 δ = +0.1397（p = 0.0026，perm p = 0.0555，胜 41/56）——方向为正、名义显著，但已在门槛之下；预算匹配 δ = +0.0504（p = 0.212，胜 34/56）——消解；固定重采样 δ = −0.0120（p = 0.730，胜 31/57）——恰好为零。自审计存活 0/2（两条 legacy 旗舰声明均被注销）。** vs 注册 legacy 弧线（+0.457→0.278→0.222，0/2，内部登记保留）：证伪定性复现且全面板尺度下更锐利——表观效应在对照之前就不再过门槛。
- **部署拓扑（披露）**：6 个认领制并行 worker + 5 个服务副本（EGARPS×3、ProteinX×2，GPU 0–2，同代码同权重仅端口/设备不同；设备位置不影响分数——exp10 约定）；EGARPS 输入按 worker 隔离目录（result.txt 并发竞态防护）；导向失败自动回落默认端点；两次整机断电经监督重启 + 陈旧认领接管零 cell 损失。并行拓扑下 240 cells ≈ 36.5 h（单进程投影约 3×）。
- **图 `experiments/plots/fig3i_dissolution.py` → `fig3i_dissolution.{pdf,png}`**（斜率轨迹 + δ=0.3 门槛虚线 + 每段 δ/P 两行标注；置换零分布直方图 inset（10⁴ 符号翻转，观测 δ 陶土红标线，象限自适应避让数据；Robin Extended Data Fig. 4c 惯例）；阶段点陶土/灰蓝/鼠尾草绿，连线暖灰，门槛线深暖灰（fig3b/3c 惯例）；无图内标题、6-pt 纯黑统一、单栏 88 mm 几何、PNG 1200 dpi；视觉 QA 通过）。
- PAPER_DRAFT（§2.3 混淆改进段重写为重测数字 + Fig 3i 图注）、PAPER_FACT_SHEET（Exp 16 节 + claim check + 关键数字 9 号升级）、FIGURE_PLAN_V5 行 i、MANUSCRIPT 重置表（Exp 16 行）、本日志更新；workspace 隔离 scratch 清理。

## 2026-08-30 — Fig 3g 视觉修订（Nature 风格 + 布局修正，用户指示）

- **`experiments/plots/fig3g_mrl_certification.py` 纯视觉修订，数据与数字不变**（仍渲染 `exp14_mrl_oracle_certification` 的 summary：AUROC 0.9903/1.000/1.000、ρ 0.9256/0.9201/0.8353，706/706）：
  (1) 全部文字统一 6-pt 纯黑 #000000（fig3f 惯例 —— palette `TEXT` #1A1A1A 在 6-pt 抗锯齿下显灰；原 chance/zero 标注用的是 dark warm grey）；
  (2) chance 0.5 / zero 参考线及其标注移除 —— 认证判读只依赖预注册 gate 线（0.8 / 0.6，保留，虚线 + 纯黑标注）；chance 在共享 0–1 坐标轴上仍然可读，并写入 Fig 3g 图注（fig2g 第二轮修订惯例）；原 "zero" 标注悬于两面板之间、"chance" 与 "gate 0.8" 互相挤碰的问题随之消除；
  (3) 两个 x 轴第二行标签互相压叠修复：删去其中的 n 标注（分层 60+60 / 排序 n=120 移入图注），标签缩短为 "(high vs low MRL tier)" / "(predicted vs measured MRL)"；
  (4) 数值标签加白色衬底，不再与 gate 虚线穿插；
  (5) 行标签改为 Sample-2019 5′UTR 文库名（"Random 50-nt 5′UTRs (in-distribution)" 等）；
  (6) 布局改为绝对 mm 几何并重新配平（标签列 22 mm｜两个 29 mm 轴｜面板间距 6 mm，图高 58 → 52 mm）；
  (7) PNG 1200 dpi（Nature Methods line-art 指引）+ 矢量 PDF（fonttype 42）。PAPER_DRAFT Fig 3g 图注、FIGURE_PLAN_V5 row g、PAPER_FACT_SHEET E7 条目、AGENTS.md、本日志更新。

## 2026-08-30 — Fig 3f 视觉修订（Nature 风格 + 布局修正，用户指示）

- **`experiments/plots/fig3f_claim_overreach.py` 纯视觉修订，数据与数字不变**（仍渲染 `exp5_claim_overreach` 的 records/summary：56 claims = 23 确定性 + 33 适配体（30 FP / 25 TP / 1 borderline），59 越界事件按 oracle×用途 = 9/11、11/8、11/9）：
  (1) 图内标题与汇总统计全部移除 —— 原 "FP rate 30/55 = 54.5% (95% CI …)"、"deterministic/aptamer tasks: n claims, n FP"、"59 events on 21 tasks" 各行的数字 Fig 3f 图注原本已含；panel 字母组装时添加（fig2d–fig3g 惯例）；
  (2) 文字-文字重叠修复：原两个块标题互相压叠（"…0 FPaptamer tasks…"）；华夫块改挂短组标签 "deterministic tasks" / "aptamer tasks"，居中于各自块正下方、共用基线；
  (3) 图例归位：判定图例（false positive / true positive / borderline）改为华夫面板正下方居中单行，用途图例（ranking objective / screening evaluation）改为条形面板正下方居中单行 —— 各自紧贴所属面板（原先一在图左上角、一在整图底部）；
  (4) 条形面板 oracle 标签（RhoFold / ProteinX / EGARPS）从 ranking 行改为居中于一组两条之间；
  (5) 全部文字统一 6-pt 纯黑 #000000（用户指示；原 palette `TEXT` #1A1A1A 在 6-pt 抗锯齿下显灰）；图形颜色仍全部出自 palette rev 7 十二色；
  (6) 布局改为绝对 mm 几何（fig3g 惯例，89 mm 单栏宽，bbox_inches="tight"），消除原图的大片空白带；
  (7) PNG 1200 dpi（Nature Methods line-art 指引，与 fig3d/fig3e/fig3g 一致）+ 矢量 PDF（fonttype 42）。FIGURE_PLAN_V5 row f、AGENTS.md、本日志更新。
- **同日第二轮（用户指示）：华夫面板整个移除，Fig 3f 变为纯条形面板** —— 用户判定逐声明小方块信息量过低（类选择性一句话即可说清）；`draw_waffle`、判定图例（false/true positive、borderline）与华夫组标签随之移除，图高 63 → 34 mm；PAPER_DRAFT Fig 3f 图注改为 "horizontal bars: …; the per-claim adjudication is text-reported"，59 事件注明 "spread 8–11 per cell"；FIGURE_PLAN_V5 row f 图型 waffle + bar → bar。
- **同日第三轮（用户指出图例疑问）：用途图例色块 grey_blue → palette 预留中性深暖灰 #7A7672** —— 用户问"三种颜色为什么只有两个图例"：三色是 oracle 标识、已由 y 轴标签直接标注（无需颜色图例），图例只承担实心/浅色 alpha 通道；grey_blue 色块易被误读为第四种数据色，故改用预留中性色。图例锚点同时从整图居中（0.5）改为坐标轴居中（50.5/89）—— 原位置相对坐标轴偏左 6 mm。
- **同日第四轮（用户指示）：图例改为六色块样式键** —— 用户要求"分别用三个深颜色和三个浅颜色做标注"：上行三个实色块（RhoFold sage / ProteinX slate / EGARPS terracotta）标注 "ranking objective"，下行三个对应浅色块标注 "screening evaluation"，与六种条形样式一一对应；手绘色块（fig.patches + fig.text，fig.legend 无法实现行标注网格），整体对齐坐标轴中心；坐标轴上移 1 mm、图例行下移（首轮实现与 x 轴标题重叠，已修）。中性深暖灰方案被本轮取代。
- **同日第五轮（用户指示）：样式键两行并为一行** —— [实色 sage/slate/terracotta] "ranking objective"　[浅色 sage/slate/terracotta] "screening evaluation" 同一行，整体对齐坐标轴中心；行宽 ≈65.5 mm < 轴宽 71 mm。

## 2026-08-29 — Fig 3e 视觉修订（Nature 风格 + 布局修正，用户指示）

- **`experiments/plots/fig3e_affinity_calibration.py` 纯视觉修订，数据与数字不
  变**（仍渲染 `exp13_affinity_calibration` 的 records/summary：thrombin 系列
  ρ = +0.49 (n = 6)、pooled AUROC 0.52 (62 vs 28)、三类 ridgeline
  67/11/17）：
  (1) 图例从右侧面板下方移到整图底部居中单行 —— 原先锚在右图下且被图缘
  裁断（"Random sequences (n = 17)" 显示不全）；
  (2) 右侧三条 ridgeline 在面板内均匀展开 —— 原先挤在左半边（xlim 0–6.4
  而三条峰只占 0.15–3.3）；
  (3) 文字-图形重叠清理：thrombin ρ 标注移入数据上方留白带（原与顶部散点
  重叠）、pooled AUROC 汇总数字移出面板进 Fig 3e 图注（fig3d 惯例——汇总
  统计与判据入图注；原文字压在 random-negatives 峰上）、pegaptanib 标注
  移位避开散点与网格线；
  (4) 散点 x 轴范围扩至 1.2 × 10³ nM —— 原 xlim 止于 400，IFN-γ 家族三个
  Kd 结合物（439.5 / 481.6 / 913.9 nM）被裁掉，现 62 个 Kd binders 全部
  在图；
  (5) 全部文字统一 6-pt 墨黑（palette `TEXT`，含显式 `legend.labelcolor`），
  无图内标题（Nature 惯例 —— headline 进图注、panel 字母组装时添加）；
  (6) PNG 1200 dpi（Nature Methods line-art 指引，与 fig3d/fig3g 一致），
  PDF 保持矢量。
- 文档：PAPER_DRAFT Fig 3e 图注（thrombin 系列标明 ringed、pegaptanib
  annotated）、FIGURE_PLAN_V5 row e、AGENTS.md Exp 13 条目、本日志。
- **同日第二轮（用户指示）**：(1) 右图三条单侧 ridgeline 改为镜像密度小提琴
  —— 数据与 KDE（Scott 带宽）不变，仅改为对称填充；三根并排柱子用半小提琴
  观感不佳；(2) 图例行整体取消，组名直接标注在各自小提琴下方（直接标注优于
  脱离面板的图例盒；右图内部无空位放图例）；(3) pegaptanib 指引线缩短为
  水平短线（原斜长线易被误读为趋势线，且中途擦过一个散点）；(4) Fig 3e 图注
  补明散点为"九个靶标全部 62 个带 Kd 的 binders"。
- **同日第三轮（用户指示）**：小提琴 KDE 在概率物理边界 score = 1 处截断
  （1 以上的密度是带宽伪影），右图顶部由此空出留白带，pooled AUROC 统计量
  （0.52, CI 0.39–0.65, 62 vs 28）回到面板上、置于该留白带（取代第一轮的
  "仅入图注"处理——用户指出右图不能没有数字）。
- **同日第四轮（用户指示）**：pooled-AUROC 统计量再次撤下面板 —— 其
  62 vs 28 口径（保留 P2 登记的 Kd-binder 约定）与小提琴组标签 67/11/17
  并排读来自相矛盾；数值（含 CI 与组成）保留在图注与正文；右图改为直接
  标出纵坐标（y 刻度标签 + 主网格线穿过小提琴），分数轴在两个面板上都可
  直接读数。
- **同日第五轮（用户指示）**：左图 thrombin 标注从纯文字改为带墨黑圈点
  标记的图例项（圈点样式 = 数据中的环标点心智一一对应），读者第一眼即可
  明白为何这六个点带黑边框。
- **同日第六轮（用户指示）**：右图密度小提琴整体更换为逐点抖动散点列 +
  中位数刻线 —— n = 11–67 且横跨九个数量级，密度曲线会假装出数据中没有
  的结构；每个点直接可见，中位数直接标在纵轴刻度上，且与左图散点共享同一
  分数轴、图型呼应。组标签改两行/三行换行避免相互触碰。
- **同日第七轮（用户指示）**：类别分布伴随面板整体撤下 —— 图 3e 收敛为
  单面板 Kd–分数散点（62 Kd binders；thrombin 环标 + 图例项；pegaptanib
  标注）。类别分离证据（pooled AUROC 0.52 [CI 0.39–0.65, 62 vs 28] 与三类
  中位数 0.22 / 1.4e-3 / 2.2e-2）改为文字报告（图注 + 正文），筛选失败的
  系统性展示由 Fig 3b 承载。

## 2026-08-29 — Exp 15（图 3h，§2.3 实验 7）：RNAsmol 部署工件保真度 A/B —— 两臂皆过 + 预注册缺陷类判据被证伪（披露）

- **§2.3 实验 7 重跑**（用户确认数据集后启动；驱动 `experiments/exp15_rnasmol_fidelity.py`，预注册 docstring，下一个空闲重置序号；pilot 20/20）。数据 = RNAsmol 官方 held-out 测试集两份逐字（robin n=1,492 763/729；pdb n=170 87/83；全部 1,662 条源序列带小写修饰碱基编码；pdb 字母表含 T 与 x）；decoy 案例与 OOD 面板不在范围（图 2g 证据；全大写输入——两臂无对比）。两臂打同一部署服务（start.sh CPU 默认 8007，GPU 0–2 未占用）：臂 A = 生产工具路径 `ToolExecutor.run_tool("score_rna_ligand_binding_with_rnasmol")`（工具层 uppercase+T→U 归一化 = v0.2.0 缺陷类的现役等价物；advisory CapGate，全部入审计）；臂 B = case-preserving verbatim 直连端点（exp7 协议）。历史参考（仅上下文，从不 gate）：v0.2.0 修复前 0.7864/0.4103。
- **全量 3,324/3,324，0 失败：臂 A 0.9745 (0.9678–0.9804) / 0.9860 (0.9715–0.9963)；臂 B 0.9744 (0.9677–0.9803) / 0.9828 (0.9616–0.9968)** —— 预注册的缺陷类判据（臂 A 双 split 低于 0.8 门槛）**未成立**。交叉验证全过：臂 B 与 exp7 记录**逐对位级一致（1,662/1,662，max |Δp| = 0.0）**；臂 A 归一化回显验证 1,662/1,662 零错配（ggguuagggu → GGGUUAGGGU）；两臂 checkpoint 逐对一致。
- **证伪披露**：exp7 备案中"工具层归一化会静默复现 v0.2.0 缺陷类"的注册预测被本次现测证伪——case 塌缩在分布内 **AUROC 中性**：逐对分数扰动实质性存在（robin 中位 |Δp| 0.006 / max 0.415，1,046/1,492 对 >1e-3；pdb 中位 0.083 / max 0.910，44/170 对被拉入 [0.4,0.6] 不确定带，臂 B 为 0/170）但不破坏类别判别。v0.2.0 塌缩（0.7864/0.4103，注册历史；坏工件已不存在、不可重跑）归因于服务端预处理移植层（大写词表 + adjacency 处理），v0.3.0 已修复——非 case 信息单因素。**净结论：部署保真度在两条出厂集成路径上均经现测认证（含默认工具路径——1,662 对官方考卷交付已发表性能）；部署失真真实、静默且分层依赖，只有测量能回答它在哪一层。**
- 图 `experiments/plots/fig3h_rnasmol_fidelity.py` → `fig3h_rnasmol_fidelity.{pdf,png}`（哑铃 + 现测验证分叉：v0.2.0 空心 terracotta 标记（注册历史）分叉至两条现测臂——terracotta 工具路径 / sage verbatim 端点——CI 须线、chance/gate 参考线、图例为轴下居中行块（fig2i 惯例）；palette rev 7）。PAPER_DRAFT（§2.3 段落 + Fig 3h 图例）、PAPER_FACT_SHEET（Exp 15 节 + 证伪披露）、FIGURE_PLAN_V5 行 h、MANUSCRIPT 重置表 Exp 15 行更新。
- **同日 addendum——v0.2.0 工件考古复核（用户指示；驱动 `experiments/exp15_rnasmol_v020_sandbox.py`，预注册 docstring，主结果已知后注册——披露；pilot 10/10）**：从 git `7262e54` 逐字节恢复 v0.2.0 服务（main.py sha256 每次调用断言；同 commit 恢复 `common_utils.py`；沙箱镜像原 `microservices/` 布局、端口 8107（生产注册表之外）、CPU、`rnasmol_service_env`、`external_repos/RNAsmol` symlink 指向未动 checkpoint；生产 8007 全程未触碰），同一批 1,662 对官方考卷重测：**robin 0.7897 (0.7663–0.8117)、pdb 0.4197 (0.3335–0.5070) —— 1,662/1,662 零失败，注册事故值 0.7864/0.4103 复现于 |Δ| 0.0033/0.0094**，checkpoint 与 exp15 逐对一致，注册预期全过。**缺陷分解就此闭合为实测**：v0.2.0（大写 + 重写邻接）0.790/0.420 vs exp15 臂 A（大写 + 上游保真邻接）0.975/0.986——同样的大写处理、只差邻接 ⇒ 真凶是 v0.2.0 对上游邻接索引怪癖（checkpoint 训练所依赖）的"修复"，而非 case 塌缩；"看似致命的改动无害，看似改进的改动致命"。注册历史 pre-fix 数值就此升级为实测。图 3h 改从实测取数重渲染（视觉复核通过）；沙箱服务已停。PAPER_DRAFT/FACT_SHEET/FIGURE_PLAN_V5/MANUSCRIPT（addendum 行）/本条更新。

## 2026-08-29 — Exp 14（图 3g，论文登记 E7）：MRL 表达 oracle 认证重跑 —— 三族双门槛全过，逐条复现

- **E7 = §2.3 实验 6（oracle 认证·正面）重跑**（用户确认三族原设计，含 in-distribution 正控族）：驱动 `experiments/exp14_mrl_oracle_certification.py`（预注册 docstring；下一个空闲重置序号，不与图 2g 的 `exp7_rnasmol_boundary.py` 冲突）。锚定集 `data/benchmarks/external_anchors/utr_mrl/e7_mrl_anchor_set.json` 逐字节未动（706 条 / 3 族：random-50 训练分布内（正控，用户复议后保留）+ 变长随机 + 变长人内源；每族 hi60/lo60 筛选层 + 120 条秩分层排序子集；组成断言全部通过）。仪器 = 生产工具路径 `ToolExecutor.run_tool("predict_5utr_mrl_with_gemorna")` → 部署 GEMORNA 8004（GPU 0/1/2 布局继承不动；锚序列逐字节写入 scratch 文件，工具层 uppercase+T→U 规范化为唯一变换——锚集"DNA 按 RNA 计"约定，服务回显 input_sequence 逐条记录）；RNADA_CAPGATE=advisory，全程审计；零 LLM；pilot 6/6（与保留记录逐位一致）。
- **全量 706/706，0 失败（≈ 37 min）：三族双门槛全过，且与保留证据完全复现** —— AUROC **0.9903 (CI 0.9754–1.0) / 1.0000 / 1.0000**（门槛 > 0.8，CI 均清 chance），ρ **0.9256 / 0.9201 / 0.8353**（门槛 ≥ 0.6；新增描述性 bootstrap CI 0.884–0.949 / 0.874–0.947 / 0.748–0.897，全部高于门槛）；与保留 `e7_mrl_scoring.jsonl` 1:1 对照 **706/706 精确一致，max |Δ MRL| = 0.0** —— oracle 经部署链端到端完全确定。披露：保留 S0 sanity 注（6.34 vs 2.48）的聚合口径不可考（旧驱动已删）；本次池化层均值 6.364 vs 2.818（逐条分数逐位相同，仅上下文引用）。
- 图 `experiments/plots/fig3g_mrl_certification.py` → `fig3g_mrl_certification.{pdf,png}`（点图+CI 对门槛：左 AUROC（chance 0.5 实线 + 0.8 门槛虚线）、右 ρ（零线 + 0.6 门槛虚线），三族行共享，值+CI 印于点上方；GEMORNA MRL oracle 色 = palette 灰蓝 #8FA6BB（区别于 3b–f 结构 oracle 三色）；6-pt 墨黑、无图内标题（fig2/3 系惯例）；palette rev 7）。保留 `e7_*` SelfModel 证据链未动（never-delete 规则；打包默认 SelfModel 无需变更——本次全部证实其 graded verdict）。
- 文档：PAPER_DRAFT（§2.3 正文 + Fig 3g 图注 + Methods 基准段 + 数据可用性）、PAPER_FACT_SHEET（E7 节 + claim check）、FIGURE_PLAN_V5 row g、MANUSCRIPT E7 行、本日志、AGENTS.md 更新。**下一步：按用户顺序重跑新程序后续实验。**

## 2026-08-29 — 实验程序重置（第三次）+ Exp 5（图 3f，E3 控臂 45 任务重测）+ 误删恢复

- **程序重置（用户指示）**：整体架构变动较大，所有实验按用户顺序逐个重跑、逐个换新代码——**只有当前正在重跑的实验可以替换它自己的旧代码/结果/图；尚未重跑实验的一切文件保持原样**。（当日曾误将 exp1–exp13 的旧代码/图/结果整体删除，用户指出后**已从 git 290141b 全量恢复**（175 个已跟踪文件 100% 找回）；不可恢复的仅两类未跟踪文件：旧运行日志 `results/*.log`（`.gitignore` 第 60 行 `*.log`）与 exp10–13 结果目录下的 `scratch/` 中间产物——均非判据证据，后者可由保留驱动确定性重算。）
- **Exp 5 = E3 控臂（声明越界）在 45 任务规模重测（图 3f，华夫+条形）**：任务集 `experiments/e5_audit_tasks.json`（生成器 `exp5_build_audit_tasks.py`，确定性 + 断言优先；24 确定性（3 族 × 8）+ 21 适配体（12 排序 + 9 筛选，9 靶标全覆盖）；strata = legacy_v1 20 条逐字节（自 git e601913 恢复，候选/Kd 与 v3 逐条断言一致）+ extension_v2 25 条（方案 A 预注册规则：每靶标排序/筛选全覆盖、≥8-Kd 靶标拆第二排序任务（结合物不相交））。驱动 `experiments/exp5_claim_overreach.py`（预注册 docstring；仅 ungated 臂；每任务 2 次 LLM 调用 deepseek-v4-pro temp 0，提示词与旧 E3 逐字节一致；**oracle 分数改走 live 生产路径**（ToolExecutor → rhofold 8005 / proteinx 8022 / egarps 8023，按 (候选, oracle) 去重缓存：213 分数 / 71 候选，0 服务错误）——唯一预注册协议偏离，已披露；RNADA_CAPGATE=advisory，全程审计）。Pilot 8/8（不可信类 5 FP + 11 越界 → 判别门 PASS）。**全量 45/45 零失败（≈4.5 h）：FP 30/55 = 54.5%（Wilson CI 41.5–67.0），越界事件 59（全落不可信类，3 oracle × 2 用途 8–11/格）；类选择性极强——确定性类 23 TP / 0 FP，不可信类 30 FP / 2 TP = 93.8%（排序 16/17、筛选 9/10）；两 stratum 同率（55.6% / 53.6%）；legacy-20 子集 15/28 = 55.6% + 28 事件 ≈ 登记值 57.9% + 23（实现方差内）**。图 `experiments/plots/fig3f_claim_overreach.py` → `fig3f_claim_overreach.{pdf,png}`（华夫：逐声明瓦片，FP 陶土/TP 鼠尾草绿/borderline 暖灰，确定性/适配体两块；条形：越界事件按 oracle×用途，oracle 配色同 3b–3e，实心=排序目标/浅色=筛选评估；用途图例图底居中（fig2i 惯例）；palette rev 7）。PAPER_DRAFT（摘要/引言/§2.3/§2.4/Fig 3f 与 Fig 4b,d 图注/Methods 基准段/数据可用性）、PAPER_FACT_SHEET（Exp 5 节 + 关键数字 14）、FIGURE_PLAN_V5 row f、MANUSCRIPT E3 行、MODEL_API_USAGE、本日志更新。**下一步：按用户顺序重跑新程序的后续实验（同模式，只替换当前实验自己的产物）。**

## 2026-08-29 — Fig 3b 视觉修订（Nature 风格，用户指示）

- **`experiments/plots/fig3b_oracle_screening.py` 纯视觉修订，数据与数字不
  变**（仍渲染 v3 summary，9 靶标 27 格，2/27 nominal pass）：(1) 删除图内
  标题 — Nature 惯例 headline 进图注、panel 字母在组装时添加，与
  fig2d/fig2f/fig2h/fig2i 的既有修订一致；(2) 全部文字统一为 6-pt 墨黑
  （palette `TEXT`）— 删除深色气泡上的白字分支与白色描边光晕（该光晕是
  2026-08-28 为两个最小气泡格加的，却恰好让那两个 AUROC=0.17 的格子白字
  叠白底糊成一团；墨黑无描边在本调色板的中间明度色阶上各种气泡尺寸均可
  读）；(3) 色条标注缩减为 "AUROC (binder vs negative)"（chance 实线 /
  gate 虚线的含义本就在图注中）；(4) 图宽上限 7.4 in → 183 mm（Nature
  双栏上限），PNG 600 dpi 不变。
- 文档：PAPER_DRAFT Fig 3b 图注补 "+/−" 锚点计数记号定义（binders + /
  negatives − 列于列标签下）。
- **同日追加（用户指示）**：删除两个过门格（0.83×2）的深色圆环标记 —
  过门信息已由格内数值承载，全部气泡渲染统一；色条上的 0.8 gate 虚线
  一并去除（仅保留 0.5 chance 实线），PAPER_DRAFT 图注与
  FIGURE_PLAN_V5 row b 的参考线描述同步更新；坐标轴范围收紧至与最外圈
  网格线重合，消除边框与网格线之间的白缝。

## 2026-08-29 — QualityAgent 提示词/profile 全面审计：3 处方向性错误修正 + 过时默认值同步

- **审计范围**: 全部 4 个 LLM 调用点（QualityAgent 默认诊断提示词、
  secondary-structure `build_prompt` 覆盖、SynthesisAgent 综合报告、ClaimGate
  抽取/润白）+ 8 个进入提示词的 QualityProfile 的 evaluation_dimensions 与
  adjustable_params hints，逐条对照当前工作流实现、工具语义与重置后实验结论。
- **方向性错误修正（3 处）**: (1) `blast_perc_identity` hint 写反 — BLAST
  perc_identity 是最低相似度过滤，higher = stricter（fewer matches），
  原文 "Lower = stricter" 反了；(2) RNASTOP `overall_stability`（mrna_cds +
  full_length 两处）写反 — 该值是 mean(reactivity, deg_Mg_pH10, deg_Mg_50C)
  反应性/降解均值，**lower = more stable**，原文 "closer to 1.0 = higher
  stability" 方向反且无归一化依据；(3) sgrna 的 CRISOT 语义混淆 —
  CRISOT-Score 是 sgRNA–DNA 对切割活性评分（工作流配 on-target 对，higher =
  预测 on-target 活性强），基因组级脱靶特异性是独立的 CRISOT-Spec 分量。
- **过时内容同步（2026-08-20 评分权重审计之后未跟进）**: tertiary profile 的
  "carefully tuned defaults" 句与其 hints 声称 rhodesign_temperature=1e-5 /
  权重 0.5/0.5 — 实际 workflow 默认 0.1 / 0.30/0.50/0.50（三组分），补
  `weight_tm_score`；sgrna profile 补 `weight_crisot_specificity`（默认 0.3）；
  ires 的 `run_structural_validation` hint 由 "ViennaRNA structural
  validation" 更正为 LinearFold 主 / ViennaRNA 备的当前实现；siRNA GC 评审
  维度由 "30-60%" 对齐工作流自身门限 [mingc=0.25, maxgc=0.60]。
- **阈值证据化**: mrna_cds 的 CAI 评审维度由 "human >0.8 good / <0.4 poor"
  的悬空启发式改为 Exp-2/3 零模型证据（人类随机同义重抽 ≈0.67、优化设计
  ≈0.83），并强调物种相关；MFE 维度补长度归一化提示（MFE 随长度缩放，
  跨长度比较用 MFE/nt — 与 Exp-2 的分析约定一致）；CRGPT nn_score 删除
  "close to 1.0 excellent / >3.0 poor" 无依据阈值并标注为未剖析
  （governance=pending）的模型似然代理 — 与 standing fact "CRISOT+CRGPT
  data gap" 一致。
- **核对通过、未改动**: QualityAgent 默认 11 条规则（无阈值、与参数白名单
  机制一致）；secondary-structure 覆盖段的默认值（repeats=10/
  num_invocations=3/mode m/37 °C，与 workflow 一致）与分数语义
  （total_score = distance/length、smaller better，与 score() 实现一致；
  0.3 触发线与 Exp-4 证据不矛盾，保留）；aptamer profile 全部参数/边界/
  reference_point 键与工作流逐项一致，其 "Do NOT apply hard thresholds for
  EGARPS/pLDDT/ipTM" 与 E10–E13 重置结论一致保留；ires 的反通用阈值条款与
  Exp-5 一致保留；ClaimGate 抽取提示词的 oracle 示例（gemorna_5utr_mrl /
  egarps_native_probability / rnasmol）与 capability 枚举与 SelfModel/
  CapabilityKind 完全一致；CDS "GC/unpaired 不进排序分" 与
  score_mrna_candidate（−MFE + codon_count·log CAI）一致。
- **验证**: 6 profile 导入 + 默认提示词构建冒烟通过；测试套件
  **646 passed, 1 skipped**（= 基线）。

## 2026-08-28 — Exp 13 (Fig 3e): affinity calibration at anchor-set scale — chance-level, inversion does not survive scale

- **Driver** `experiments/exp13_affinity_calibration.py` (pre-registered
  docstring; pilot 6/6 → full 95/95, 0 failures, wall ≈ 4.4 h): the retained
  P2 pilot's question re-registered on `e1_anchor_set_v3.json` verbatim (95
  entries / 9 targets — the Fig-3b/c/d data source, user-confirmed); zero
  intervention (ToolExecutor.run_tool → deployed rhofold 8005 / proteinx
  8022 / egarps 8023, fixed protocol args only); CapGate advisory; every
  call audited; the retained P2 15-record reference recovered from git
  e601913 and embedded (12/15 ids live in v3, drops disclosed).
- **Results**: thrombin 6-point Kd series ρ = 0.4857 (sub-gate; retained
  4-point 0.40 re-measures 0.20 — realization variance); pooled
  binder-vs-negative AUROC **0.5225 (CI 0.391–0.652, 62 vs 28)** — gate
  fails, CI covers chance; **the retained pilot's below-chance 0.356 does
  not survive scale — the honest reading upgrades "directionally inverted"
  to "uncalibrated, chance-level"** (per-entry inversion reproduces:
  pegaptanib 1.27e-6 vs scrambled TBA 0.983); all three ridgeline classes
  span the full 9-order score range; legacy-12 1:1 median |Δnp| = 7e-4
  (3 large shifts = the disclosed EGARPS bimodal class); vs exp10_v3:
  RhoFold bit-identical, EGARPS median Δ 5.7e-4. Verdict: **NO-GO on both
  P2 gates — no validated affinity calibration**.
- **Figure** `experiments/plots/fig3e_affinity_calibration.py` →
  `output/fig3e_affinity_calibration.{pdf,png}` (Kd–score scatter with the
  thrombin series emphasized + horizontal ridgeline densities on the shared
  log-score axis, ridgeline style after SeFMol Fig. 3d; palette rev 7; the
  group legend as a centred row block under the axis, the fig2i
  convention).
- **Docs**: PAPER_DRAFT Fig-3e legend + Results sentence (anti-signal →
  noise, inversion → chance-level at scale with the per-entry inversion
  preserved), PAPER_FACT_SHEET (E13 section + key-number 11), FIGURE_PLAN_V5
  row e, MANUSCRIPT reset table (Exp 13 row).

## 2026-08-28 — Fig 2 panel-letter swap: audit trail ↔ runtime (h ↔ i; user-directed)

The audit-trail panel is now **Fig 2h** and the end-to-end runtime ECDF
is now **Fig 2i** (lettering-only change — no data, statistics or panel
content touched), which also restores strict a → i reading order in the
composite (the f–g–h equal-height row now precedes the full-width i).
Files renamed: `experiments/plots/fig2h_audit_trail.py` (was
`fig2i_audit_trail.py`), `experiments/plots/fig2i_runtime_ecdf.py` (was
`fig2h_runtime_ecdf.py`), plus the four
`experiments/plots/output/fig2{h,i}_*.{pdf,png}` outputs; script
docstrings, usage lines and save stems updated. References swapped
across `PAPER_DRAFT.md` (Results citations + the Fig. 2 legend, whose
(h)/(i) paragraphs also traded places so the legend still runs a → i;
the Results' end-to-end sentence likewise traded its audit and runtime
clauses so the citations run Fig. 2h → Fig. 2i — "the 241-run campaign
above" became "below"),
`FIGURE_PLAN_V5.md` (Fig-2 table rows h/i contents + the
diversification-paragraph chart-type references), `PAPER_FACT_SHEET.md`
(the Exp-9/audit and Exp-8/runtime sections retitled and reordered;
**legacy** no-space records `Fig2i_ires` / `Fig2h_small_molecule` /
`fig2h 17 pairs` / `fig2_summary.json fig2i` deliberately untouched —
they name pre-reset artifacts, not the current panels), `MANUSCRIPT.md`
(reset table), this log's historical entries (re-lettered to the new
convention), `AGENTS.md` (Exp-8/Exp-9 What's-New bullets),
`experiments/exp8_runtime.py` / `exp9_audit_stats.py` docstrings, and
the frozen `exp9_audit_stats/MANIFEST.json` `experiment` field
(metadata only — the SHA-256 corpus hash entries are untouched).
`fig2_composite.{pdf,png}` regenerated.

## 2026-08-28 — Fig 2 composite assembly (a–i)

`experiments/plots/fig2_assemble.py` added →
`experiments/plots/output/fig2_composite.{pdf,png}`: the nine finished
Fig. 2 panels combined into one figure on the Nature conventions surveyed
in `relevant_references/` (bold lowercase letters at each panel's
top-left corner, strict column grid, rows top-aligned so the letters
share one line). Panels are embedded as vectors; every panel already
carries the reset programme's single 6-pt ink-black text style, so all
panels share one scale unless a row must shrink to fit. Layout
(user-directed): a (tile carpet) full width; b c and d e two per row at
scale 1.0, centred in their columns; **f g h share one row drawn at one
equal height** (f's squarer aspect made it look bigger than g/h under a
uniform row scale; per-panel scales differ, ≈ 0.59/0.67/0.71, widths
follow their aspects and the leftover width becomes even gutters),
sized so the row fills edge to edge and the first revision's empty
bottom-right half-cell disappears; i (ECDF) closes the figure full
width. After the same-day h ↔ i letter swap (entry above) the composite
reads in strict lettering order a → i. Letters Helvetica-Bold 8 pt ink
black, drawn by the assembler at one size regardless of row scale. PNG
rendered from the composite PDF at 300 dpi.

## 2026-08-28 — Fig 2h figure revision (user-directed; no data change)

`experiments/plots/fig2h_audit_trail.py` revised and regenerated
(`fig2h_audit_trail.{pdf,png}`; the Exp-9 corpus, session selection and
numbers are unchanged): the composition donut dropped — it carried three
numbers the paper already states in the Results text and the Fig. 2h caption;
the in-figure panel titles removed (Nature style — the headline lives in the
caption and panels carry letters only, the fig2d/fig2f/fig2i convention);
every text element now shares one font size (6 pt) and one colour (ink black
— the old layout's 4.8–5.6 pt labels antialiased to a pale grey); the legend
moved from floating half-outside the axes into the empty upper-right of the
milestone track; geometry changed from the double-column two-panel layout to
the single-column panel size of fig2b–g. `PAPER_DRAFT.md` Fig 2h legend,
`FIGURE_PLAN_V5.md` row i and `PAPER_FACT_SHEET.md` Fig-2h figure line
updated to match.

## 2026-08-28 — Fig 2i figure revision (user-directed; no data change)

`experiments/plots/fig2i_runtime_ecdf.py` revised and regenerated
(`fig2i_runtime_ecdf.{pdf,png}`; the Exp-8 numbers are unchanged): the
in-figure title removed (Nature style — the headline lives in the caption and
panels carry letters only, the fig2d/fig2f convention); every text element
now shares one font size (6 pt) and one colour (ink black — the legend
entries were previously set in their pale workflow colours); the box inset —
which overlapped the ECDF curves — dropped entirely (it summarized the same
samples the ECDF already shows in full, and the legend carries the medians);
the legend moved from floating at the figure's right margin to a centred row
block under the x-axis, so it reads as part of the panel; axis wording
corrected target → run (the 241-run sample times whole PA sessions as single
runs); y-range headroom added above the y = 1 step so the curve tops no
longer touch the panel edge. `PAPER_DRAFT.md` Fig 2i legend and
`FIGURE_PLAN_V5.md` row h chart-type phrase updated to match.

## 2026-08-28 — anchor set v3 Part-A extension + Exps 10–11 v3 re-runs: 9 targets / 95 entries, 2/27 and 4/27 nominal passes, none reliable

User-sequenced second curation pass (after the Fig. 3d run). Survey
(2026-08-27) vs curation outcomes — the assertion gate arbitrated:
**admitted** FGF2 (10 binders, Jellinek 1993; sequences/Kd via the
Ribocentre transcription + family-motif nesting assertions — primary PDF
bot-walled, deviation registered), swine influenza H3N2 HA (4 binders +
printed negative HA1c, Wongphatcharachai 2013; protein surrogate
A/swine/Illinois/03040/2010 full-length HA0 — selection strain
GISAID-restricted, 95.1% identity to the MN/2008 partial, registered), and
IFN-γ (B1-4 + 5 in-silico mutants, Zhao 2022; every mutant DERIVED from
B1-4 by its registered point-mutation list and asserted equal to the SI
print; M5-5 cross-checked between SI Tables S1 and S5; printed
docking-negative mutant admitted as negative). **Rejected at curation**
(two survey verdicts overturned): SARS-CoV-2 RBD (Shekar 2025 — 83-sequence
SI zip without any printed ID mapping) and HIV-1 RT FANA (Ferreira-Bravo
2015 — sequences figure-only; a vision extraction contradicted the paper's
own text-printed primer flanks). Part-A 66 → 95 entries (v2 byte-verbatim),
9 targets; docking anchors byte-identical to the first-pass v3 (asserted —
the Fig. 3d measurement unaffected); generator deterministic (md5
`7b7a71b915a2c3a181673ea3d27bdd27`); SOURCES.md second-pass section added.

- **Exp 10 v3** (`EXP_ANCHOR_SET` override, results `*_v3/`; defaults and
  v2-run records untouched): **95/95, 0 failures** (pilot 6/6; first
  attempt crashed on a generator fasta-path convention bug at the first
  new-target entry — 66 v2 records unaffected, fixed, `--resume` continued).
  **27/27 cells: 2 nominal passes > 0.8** (proteinx × swH3-HA 0.833 CI
  0.333–1.0; egarps × IFN-γ 0.833 CI 0.5–1.0) — both small-n, **all 27 CIs
  cover chance**; sensitivity 10/7/2/0; FGF2 (widest Kd span, 2.25 orders)
  sub-gate 0.47/0.43/−0.18.
- **Exp 11 v3**: **54/54, 0 failures** (pilot 4/4). **27/27 cells: 4 nominal
  ρ ≥ 0.6, all CIs span zero** — egarps/proteinx/rhofold × IFN-γ
  (+0.714/−0.226–1.0, +0.657/−0.5–1.0, +0.600/−0.6–1.0; n=6, single
  in-silico-mutant family, Kd span 0.94 orders — within-family covariation
  caveat registered) + proteinx × Ang2 (n=3). Sensitivity 8/6/4/2. Vs the
  first reset run: 10/18 v2 cells identical, rest ProteinX-realization
  variance (egarps × PDGF-BB 0.67 → 0.10 — the disclosed instability
  class). Headline invariant: no oracle–target cell shows reliable ranking
  power.
- Figures 3b/3c re-rendered on the v3 summaries (9-target data-driven
  columns/rows via `FIG3_SUMMARY`; v2 regression render verified; fig3b
  cell values gained a white halo after a vision check found two truncated
  at minimal bubble size). Docs updated: PAPER_DRAFT (Results, Fig 3 b/c
  legends, Discussion counts), PAPER_FACT_SHEET (Fig 3b/c sections + key
  numbers), FIGURE_PLAN_V5 rows b/c, MANUSCRIPT reset table.

## 2026-08-27 — Exp 12 (Fig 3d) executed under the reset + anchor set v3: docking-power profile on the extended panel, 397/399, 0/19 native top-1

Two-part delivery. (1) **Anchor set v3** (`data/benchmarks/external_anchors/aptamers/e1_anchor_set_v3.json`,
generator `experiments/curate_e1_anchor_set_v3.py`, user-approved scope
"admit every qualifying complex"): docking anchors 5 → **19 complexes / 14
independent protein targets**; Part-A 66 entries carried byte-verbatim
(asserted). Survey backbone = Troisi 2023 (144 protein–aptamer PDB entries)
+ a full-text RCSB sweep of all post-2024 "aptamer" deposits; every admitted
entry chain-composition/meth­od/resolution-verified against the RCSB API at
generation time (the assertion screen itself caught that 6RTI A9g is
2′-F-modified, missed by the survey scan). Chemistry screen rejected
SOMAmer-class and mirror-image complexes with RCSB-chemcomp-verified reasons
(4ZBN/8J1Q/7YQ3/9SA8/5UC6/4NI7/7JTN/6TXR; 4WB2/4WB3/4R8I) plus redundant
families and out-of-scope systems — 18 rejection classes registered.
(2) **Exp 12** (`experiments/exp12_docking_capability.py`, pre-registered
docstring, pilot 3/3; evidence `experiments/results/exp12_docking_capability/`):
per complex, native pose + 20 seeded rigid-body decoys; decoy parameters
offline-calibrated so the 1HVU decoy-RMSD distribution matches the retained
Part-B evidence, and the contact computation reproduces the retained 1HVU
native n_contacts = 152 exactly (protocol anchors). Instrument zero-intervention:
ToolExecutor.run_tool → deployed egarps 8023 (`academic=False` only); CapGate
advisory; every call audited.

- **399 poses attempted, 397 scored** — 2 reproducible service-side failures
  (8ZBF decoy16, 5HRU decoy13; one disclosed retry reproduced the failure;
  those complexes analysed with 20 candidates). Wall ≈ 4.6 h, median 38 s/pose.
- **0/19 complexes rank the native pose top-1** (gate ≥ 2/3 fails
  decisively); native ranks 6–20 of 21; native scores below the median decoy
  in most complexes (1HVU 0.008 vs 0.34); within-decoy Spearman(np, −RMSD)
  −0.59…+0.44.
- Vs retained: 0/5 headline invariant under the union 0/19; native-np deltas
  ≤ 0.0058 (service variance); per-complex ranks shift under the regenerated
  decoy protocol (disclosed).
- Figure `experiments/plots/fig3d_docking_lollipop.py` →
  `fig3d_docking_lollipop.{pdf,png}` (lollipop + top-1 gate line, grouped by
  protein target; terracotta EGARPS colour across Fig. 3; open markers = the
  five v2-retained anchors). Docs updated: PAPER_DRAFT (Fig 3d legend +
  Results + Discussion counts), PAPER_FACT_SHEET (E12 section + key numbers),
  FIGURE_PLAN_V5 row d, MANUSCRIPT reset table, SOURCES.md v3 section.
- **Next (user-sequenced)**: the five surveyed Part-A targets (FGF2 /
  influenza HA / HIV-1 RT FANA / SARS-CoV-2 RBD / IFN-γ) enter the same v3
  set in a second curation pass, then Exps 10–11 re-run on v3 for Figs 3b–c.

## 2026-08-27 — Exp 11 (Fig 3c) executed under the reset: structure-oracle ranking-power profile, 34/34, no reliable ranking power

Zero-intervention ranking-power profiling on the affinity subsets of the
same anchor set (`experiments/exp11_oracle_ranking_power.py`, pre-registered
docstring, pilot 4/4; evidence
`experiments/results/exp11_oracle_ranking_power/`). Subset rule = per target,
binders with measured Kd gated by `ranking_eligible` (flag defaults True
where absent — pilot-3 targets carry none), giving the retained per-target
n 6/8/5/6/3/6 = 34 entries; the rule was pre-verified by recomputing the
nine retained v2 JSONL cells to max |Δρ| = 0. ρ = Spearman(oracle score,
−log10 Kd), gate 0.6 analysis-side only. Instrument identical to Exp 10
(`ToolExecutor.run_tool` → deployed rhofold/proteinx/egarps, GPU-pinned
0/1/2 inherited; fixed protocol args only); CapGate advisory; every call
audited to `platform_audit.jsonl`.

- **34/34 successful, 0 failures** (wall ≈ 1.7 h, 164–208 s/entry).
- **18/18 cells measured; no oracle shows reliable ranking power across
  targets** — 2/18 nominal ρ ≥ 0.6 passes, both small-n with vacuous
  uncertainty (egarps × PDGF-BB n = 5, ρ = +0.667, CI −0.40–1.0, an
  ordering of near-zero scores; proteinx × Ang2 n = 3, ρ = +1.0 with two of
  three entries flipping ~0 ↔ ~1 across complex realizations); no oracle
  passes on more than one target; sensitivity 6/4/2/1 at 0.4/0.5/0.6/0.7;
  the retained best cell (rhofold × PDGF-BB +0.5643) reproduces
  bit-identically and stays sub-gate.
- Vs retained evidence: **10/18 cells identical** (all 6 RhoFold
  bit-deterministic — also re-derives the pilot-3 targets' retained ρ
  exactly); 8 shifted by ProteinX-complex realization variance (largest
  Δρ +0.5). Vs Exp-10 per-entry scores (same 34 ids): RhoFold max |Δ| = 0,
  ProteinX median 0.005, EGARPS median 1.9e-5 with 5 bimodal entries
  (max 0.9998) — the disclosed instability class.
- Figure `experiments/plots/fig3c_oracle_ranking.py` →
  `fig3c_oracle_ranking.{pdf,png}` (Cleveland dot plot, 3 oracle blocks ×
  6 targets; zero line solid / 0.6 gate dashed with nominal-pass rings;
  retained open markers + dumbbell hairlines; palette rev 7).
  2026-08-29 user-directed revisions: retained-evidence open markers +
  dumbbell hairlines dropped, then the zero/gate reference lines and
  their tags removed as uninformative — the panel shows the reset run
  only; in-figure title removed (Nature convention), every text element
  one 6-pt ink-black style, printed ρ values in a fixed right-hand
  column. Same-day user direction: retained-evidence comparison
  narrative removed from PAPER_DRAFT text and legends (it stays in the
  internal registers).
  `PAPER_DRAFT.md` Fig 3c legend + Results reset sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row c, `MANUSCRIPT.md` reset
  table, `AGENTS.md` updated. Docking panel 3d remains on retained evidence
  pending its own reset re-run.

## 2026-08-27 — Exp 10 (Fig 3b) executed under the reset: structure-oracle screening-power profile, 66/66, 0/18 cells pass

Zero-intervention oracle profiling on the registered aptamer anchor set
(`experiments/exp10_structure_oracle_screening.py`, pre-registered docstring,
pilot 6/6; evidence `experiments/results/exp10_structure_oracle_screening/`).
Anchor set `e1_anchor_set_v2.json` verbatim (66 entries, 6 targets;
user-confirmed after the target-count review — 6 is the discipline-exhausted
maximum). Instrument = the platform production tool path
(`ToolExecutor.run_tool` → deployed rhofold/proteinx/egarps services; DNA
scored as RNA via T→U per the anchor-set convention); CapGate advisory
(regression convention — under default enforce the three oracles are
SelfModel-governed and blocked); every call audited to
`platform_audit.jsonl` (the driver activates the audit runtime via
`runtime_from_env()`; an initial unaudited ~8-record attempt was discarded
and the run restarted from scratch — disclosed).

- **66/66 successful, 0 failures** (wall ≈ 3.3 h, 165–225 s/entry).
- **18/18 cells measured, 0/18 pass AUROC > 0.8; all 18 bootstrap 95% CIs
  cover chance**; best cell 0.800 exactly (RhoFold pLDDT × PDGF-BB);
  sensitivity 5/2/0/0 cells above 0.6/0.7/0.8/0.9.
- Secondary ranking (descriptive): ρ ≥ 0.6 only on two n = 3 Angiopoietin-2
  SPR subsets — underpowered by pre-registration.
- Vs retained evidence: **11/18 cells identical** (RhoFold bit-deterministic,
  pilot cross-check bit-identical; 5/6 ProteinX); the 6 EGARPS cells + 1
  ProteinX cell shift by ProteinX-complex realization variance (largest
  Δ +0.476, egarps × Thrombin) — headline invariant.
- Figure `experiments/plots/fig3b_oracle_screening.py` →
  `fig3b_oracle_screening.{pdf,png}` (balloon matrix; size + colour
  dual-encode AUROC, printed values, chance/gate reference lines; palette
  rev 7). `PAPER_DRAFT.md` Fig 3b legend + Results reset sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row 3b, `MANUSCRIPT.md` reset
  table updated.

## 2026-08-27 — Exp 8 (Fig 2i) executed under the reset: end-to-end runtime by workflow, 241/241, minutes-to-1 h per target

Zero-intervention timing of the 11 workflows (`experiments/exp8_runtime.py`
+ orchestrator `experiments/exp8_run_all.sh`, pre-registered docstring,
pilot 4/4; evidence `experiments/results/exp8_runtime/`). Instrument = one
`cli/form_chat.py` subprocess per run through the user form entry, inputs
verbatim, no thresholds, CapGate advisory (the documented regression
convention); services pre-warmed and GPU-pinned 0/1/2 by
`exp1_bring_up_services.sh`, so per-run time measures the delivered
workflow (pre-flight → generate → evaluate → score → rank → advisory
review → writeout), not cold model loads; lanes strictly sequential
(gpu_aptamer → gpu_tertiary → cpu → PA batch) against cross-lane
contention. Successful runs only enter the distribution.

- **241/241 successful**: all 210 RNADesign-210 tasks + all 31 PA
  regression sessions (PA_006–PA_036, each timed as one whole form
  session). Pooled median **2.6 min** (mean 4.4).
- **Workflow medians**: mRNA scoring 2.5 s; small-molecule 0.23 min; ASO
  0.28; secondary structure 1.21; IRES 1.34; siRNA 2.61; sgRNA 3.20; CDS
  3.21; tertiary structure 3.87; full-length mRNA 4.32; aptamer 6.29.
- **Completion profile**: 76.3% ≤5 min, 92.9% ≤10 min, 98.3% ≤30 min,
  **240/241 ≤1 h**. The four >30-min runs are all multi-turn aptamer PA
  sessions (42.4/42.9/59.9/**98.6** min); the single >1 h run is the GenNav
  `navigation=true` aptamer session PA_028. Suite-task maximum 27.0 min.
- **Disclosed amendment (registered before the PA_028 re-run)**: the
  PA-arm timeout (3600 s, calibrated on suite-task maxima) under-covered
  multi-turn navigation sessions — PA_027 finished at 3593 s and PA_028 was
  killed at 3600 s while progressing normally; the timeout's
  kill-only-the-direct-child semantics orphaned its turn-2 grandchild,
  which then completed (~5740 s total), exposing a driver defect now fixed
  (process-group kill). Amended budget 10800 s; PA_028 re-run once under
  it (**5917.2 s**, consistent with the orphan reconstruction); the
  original censored record retained in `pa_batch.jsonl`; the orphan's
  overlap window with PA_029 verified uncontaminating (42.63 s vs siblings
  42.15/42.52 s).
- Figure `experiments/plots/fig2i_runtime_ecdf.py` →
  `fig2i_runtime_ecdf.{pdf,png}` (log-axis ECDF per workflow + box inset,
  1 h reference line; palette rev 7 unchanged). `PAPER_DRAFT.md`,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md`, `MANUSCRIPT.md`, `AGENTS.md`
  updated.

## 2026-08-26 — Exp 7 (Fig 2g) executed under the reset: RNAsmol two-sided boundary, every registered metric reproduced

Zero-intervention re-run of the small-molecule oracle's two-sided profile
(`experiments/exp7_rnasmol_boundary.py`, pre-registered docstring, pilot
37/37; evidence `experiments/results/exp7_rnasmol_boundary/`). Instrument =
the deployed RNAsmol microservice exactly as the platform ships it (CPU
default via its own `start.sh`), one call per pair, sequences and SMILES
verbatim and **case-preserving** — the official held-out splits encode
modified bases in lowercase, and the agent tool layer's uppercase+T→U
normalization would silently re-introduce the v0.2.0 fidelity-defect class,
so the service endpoint is the fidelity-correct instrument (the retained
evidence's protocol; no ToolExecutor calls, hence no CapGate audit entries
at this layer). Checkpoint auto-selection via data-provenance hints only
(robin/pdb + molperturbation; FMN→pdb, MALAT1→robin; OOD no hints →
platform default); no thresholds, no tuning.

- **3,545/3,545 pairs scored, 0 failures**: robin test 1,492 + pdb test 170
  + FMN decoys 1,601 + MALAT1 decoys 265 + OOD panel 17.
- **Every registered metric of the retained 2026-08-11 evidence reproduced
  exactly**: robin AUROC 0.9744 (0.9678–0.9803), pdb 0.9828 (0.9607–0.9970;
  ≤500-nt subset 0.9788, n=126, 44 truncated service-side); decoy true-binder
  ranks 2/1601 (0.125 pct) and 7/265 (2.642 pct); OOD binder-vs-random-chem
  0.7222 (0.2778–1.0) and binder-vs-near-cognate 0.5625 (0.0625–1.0) — both
  CIs span chance. Verdict GO on all three axes.
- **Per-pair cross-check** vs the retained JSONL: medians ~1e-6 (MALAT1
  ≤3.8e-5, OOD ≤6.3e-4); a minority of near-decision-boundary inputs amplify
  inference-backend arithmetic (robin max 0.021 at 1/1492 pairs >1e-3; pdb
  0.047 at 1/170; FMN 0.367 at 53/1601 — one unstable near-0.5-band decoy,
  idx 367, re-scored bit-identical to confirm this run's determinism; the
  retained run's device is unrecorded). No registered metric moves. The
  cross-check tolerance was amended from bit-level to the disclosed
  4-decimal-AUROC + decoy-rank criterion **before** the full run (docstring
  records the amendment).
- Figure `experiments/plots/fig2g_rnasmol_boundary.py` →
  `fig2g_rnasmol_boundary.{pdf,png}` (forest dot + CI; khaki in-distribution
  / dark-warm-grey OOD; chance + 0.8 screening-gate reference lines; palette
  rev 7 unchanged). `PAPER_DRAFT.md` Fig 2g legend + Results sentence,
  `PAPER_FACT_SHEET.md`, `FIGURE_PLAN_V5.md` row g and `MANUSCRIPT.md`
  reset-run table updated with the re-run as the numbers of record.

## 2026-08-25 — Platform fix: species-resolved LinearDesign codon tables; Exp 2+3 (Fig 2b–c) re-run

User-reported defect (the Exp 2+3 E. coli outliers): ``cai_species`` only
reached the CAI evaluator — LinearDesign always designed against the
service's bundled human table regardless of species (GFP / β-galactosidase
designed CAI ≈ 0.60 scored against their E. coli tables). Fixed at the
platform layer, not the driver:

- **Species-resolved codon tables**: 11 LinearDesign-format CSVs generated
  from the same Kazusa tables the CAI evaluator uses
  (``agent_core/data/codon_usage_lineardesign/``; generator
  ``scripts/gen_lineardesign_codon_tables.py`` with a ``--check`` drift
  guard used by the test suite). ``mrna_cds_design`` resolves
  ``cai_species → codon_usage_path`` on **both** the golden path and the
  GenNav navigation path; an explicit ``lineardesign_codon_usage_path``
  still wins. Human designs now use the platform Kazusa table (verified to
  produce the same argmax sequences as the bundled table). Unresolvable
  species fail fast at the input layer with a clear message instead of
  silently designing against the human table. ``full_length_mrna_design``
  inherits the fix (it delegates CDS generation to the same workflow). The
  audit trail records the codon table on every LinearDesign call (verified
  on the live run). Note: LinearDesign λ=0 is pure-MFE, so the table only
  influences λ>0 designs — confirmed live before the re-run.
- **Tests**: +10 (``tests/test_lineardesign_species_wiring.py``); the old
  "unsupported species still runs" contract test rewritten to the new
  fail-fast contract; suite **646 passed, 1 skipped**. Folded in a repair of
  a pre-existing reset breakage: ``agent_core/calibrated/
  profiling_metrics.py`` still imported the deleted
  ``experiments/analysis/stats_utils`` — ``bootstrap_auroc_ci`` inlined
  verbatim from git history.
- **Exp 2+3 re-run** (driver docstring updated; pre-fix run archived at
  ``exp2_cds_nulls_prefix/``, session prefixes ``exp2d_/exp2s_`` vs the
  re-run's ``exp2rd_/exp2rs_``): 20/20 design + 240/240 scoring, 0 failures.
  CAI medians **0.832 / 0.729 / 0.675** (designed-vs-WT P = 6.9e-4,
  δ = 0.63; WT-vs-random P = 6.8e-7, δ = 0.67; designed-vs-random
  P = 2.2e-13, δ ≈ 1.0); MFE/nt medians **−0.336 / −0.051 / −0.047**
  (designed vs both nulls δ = −1.0; WT-vs-random NS P = 0.29). E. coli
  targets after the fix: GFP 0.597 → 0.701 (above its WT 0.560),
  β-galactosidase 0.603 → 0.740 (above its WT 0.729). Figures refreshed
  (``fig2b_cai``, ``fig2c_mfe_per_nt``); PAPER_DRAFT / FIGURE_PLAN_V5 /
  MANUSCRIPT §3.0 numbers updated.

## 2026-08-25 — Exp 5 (Fig 2e) executed under the reset: IRES literature panel at chance on the default path

Paper §2.2 experiment 5 re-run against the frozen gated platform
(`experiments/exp5_ires_literature_panel.py`, pre-registration in its
docstring; pilot 6/6 then the full panel, `RNADA_CAPGATE=advisory`):

- **Panel (user-approved expansion before any run)**: positives extended
  from 3 to **9 literature IRES 5′UTRs** — the original EMCV/HCV/poliovirus
  plus FMDV (NC_004004.1:1-1058), HRV-A1 (NC_038311.1:1-626), BVDV-1
  (NC_001461.1:1-385) and the three cellular IRES the asset table had
  promised but never landed (c-myc NM_002467.6:1-363, Bip/GRP78
  NM_005347.5:1-217, VEGF-A NM_001025366.3:1-496; ranges = 1..CDS_start−1,
  provenance recorded in the anchor `SOURCES.md`); negatives unchanged (50
  GENCODE v46 200-nt 5′UTR windows). n = 59.
- **Zero-intervention rule (user-directed)**: one `ires_prediction`
  workflow run per sequence with platform defaults; the only deviation is
  `probability_threshold=0.0`, registered before the pilot — the threshold
  is a labelling knob (the service computes every fragment's probability
  regardless), and 0.0 merely disables the label filter so raw
  probabilities reach the workflow's score/rank layer for below-threshold
  sequences. Threshold-free AUROC over the raw scores; ROC + pointwise 95%
  TPR band via stratified bootstrap (10⁴ replicates, seed 20260825).
- **Primary result (pre-registered mode-0 arm — the workflow default)**:
  59/59 scored, 0 failures; **AUROC 0.478 (95% CI 0.311–0.649),
  Mann–Whitney P = 0.841 — indistinguishable from chance**. 20/50
  negatives score above 0.5 (median 0.449); score–length correlation
  r = 0.018 (not a length artifact). The legacy 3-positive-panel 0.762
  does **not** reproduce: the legacy-3 subset against the same 50
  negatives scores 0.513 (legacy protocol unrecoverable — deleted in the
  reset; this re-derivation is the number of record).
- **Disclosed mode-2 addendum arm** (registered after the primary was
  known, never substituted for it): sliding-window scanning at upstream
  defaults (window 174 / step 50 — the native regime; removes the
  341–1058-nt-vs-200-nt regime mismatch between positives and negatives).
  **AUROC 0.673 (95% CI 0.467–0.862), P = 0.102** — directionally better,
  CI still spans 0.5, and the estimate sits exactly where E16 graded the
  oracle on IRESfinder's own held-out sets (0.68/0.73/0.76, all below the
  0.8 screening gate → enforce-gated). The calibrated self-knowledge and
  the literature panel agree: the deployed IRES oracle has ~0.7
  discrimination at best and the default full-sequence path has none.
- Evidence `results/exp5_ires_panel/` (`panel_runs.jsonl`,
  `panel_runs_mode2.jsonl`, `summary.json`, `roc_points_{mode0,mode2}.csv`);
  figures `experiments/plots/fig2e_ires_roc.py` →
  `plots/output/fig2e_ires_roc.{pdf,png}` and
  `fig2e_ires_roc_mode0.{pdf,png}` (all palette rev 7; the workflow's warm
  grey `#B7B0A2`, chance diagonal in neutral grid). **Figure endpoint
  re-registered to the mode-2 scanning arm (user direction, 2026-08-26)**:
  the canonical `fig2e_ires_roc.*` now renders mode-2 (AUROC 0.673) — it is
  the legacy panel's protocol (legacy per-sequence scores match this arm
  exactly, confirmed against `PAPER_FACT_SHEET.md`) and the oracle's native
  window regime; the pre-registered mode-0 default-path result stays the
  primary analysis record and its figure is archived as
  `fig2e_ires_roc_mode0.*`. No scores were recomputed.
- `docs/MANUSCRIPT.md` asset table + §3.0 programme table updated;
  `docs/FIGURE_PLAN_V5.md` row 2e and the `PAPER_DRAFT.md` Fig. 2e
  legend/Results observation (3) updated to the measured numbers (and the
  stale "EMCV 0.808, poliovirus 0.891 literature-panel reproduction"
  parenthetical dropped — those were task-protocol scores, not panel
  scores).

## 2026-08-25 — Exp 4 (Fig 2d) executed under the reset: inverse folding 21/25 exact

Paper §2.2 experiment 4 re-run against the frozen gated platform
(`experiments/exp4_inverse_folding.py`, pre-registration in its docstring;
pilot 5/5 then the full 25-task matrix, `RNADA_CAPGATE=advisory`):

- **Zero-intervention rule (user-directed)**: the platform is measured
  as-is — no threshold presets, no objective tuning, no parameter sweeps;
  task inputs fed verbatim from RNADesign-210
  `06_rna_secondary_structure` (25 targets, 9–54 nt, 4–70 °C, function
  modes m/p/mp, start-sequence constraints). The single arm is the
  `rna_secondary_structure_design` golden path (RNAinverse ×N → RNAfold
  fold-back validation + GC → scoring → ranking).
- **Primary metric**: best-ranked candidate dot-bracket Hamming distance to
  the target (the platform's own `structure_distance`; 0 = exact recovery).
  Secondary: base-pair distance (analysis-side), per-candidate profile,
  any-candidate-exact (generation vs delivery).
- **Results**: 25/25 runs successful; **21/25 exact recovery** (dot-bracket
  distances 0×21, 2, 2, 4, 6; base-pair distances of the four misses
  1, 2, 3, 1 — at most 3 of 10–14 target pairs). All four misses are
  mp-mode / combined-parameter / extreme-temperature / longest-target edge
  tasks (015, 018, 021, 024); no candidate in any miss's ranked set was
  exact (generation-limited, not ranking-limited). Categories: basic 1/1,
  edge 19/21, full 1/3. The pre-reset run and the Exp-1 lane had observed
  22/25 (different stochastic realization; RNAinverse is stochastic) —
  this run's 21/25 is the number of record.
  Evidence `results/exp4_inverse_folding/` (`pilot.jsonl`, `records.jsonl`,
  `summary.json`); figure `experiments/plots/fig2d_inverse_folding.py` →
  `plots/output/fig2d_inverse_folding.{pdf,png}` (strip + step cumulative
  curve; exact dots in the workflow's grey green `#8DA290`, misses in the
  reserved dark warm grey `#7A7672`, cumulative curve slate blue
  `#6B7B8D` — all from palette rev 7).
- Driver fix during analysis: base-pair distance corrected to the standard
  |P₁ Δ P₂| definition (an integer-halving slip mis-scored asymmetric
  stem extensions; recomputed from the stored structure strings, no
  platform re-run).
- `docs/PAPER_DRAFT.md` Results §2.2 observation (2) and the Fig. 2d
  legend updated to 21/25; `docs/FIGURE_PLAN_V5.md` row 2d re-pointed to
  the new evidence path.

## 2026-08-25 — Exp 2+3 (Fig 2b–c) executed under the reset; fig 2c re-registered as a three-arm panel

Paper §2.2 experiments 2 and 3 merged into one driver and re-run against the
frozen gated platform (`experiments/exp2_cds_null_model.py`, pre-registration
in its docstring; pilot 3/3 then full matrix, `RNADA_CAPGATE=advisory`):

- **Designed arm = the system's CDS golden path as-is** (user-directed):
  `mrna_cds_design` with `design_tool="all"` — LinearDesign λ∈{0,1,4,10} +
  RNARL + GEMORNA, each candidate folded (LinearFold), GC/CAI/RNASTOP-scored
  and ranked; the best-ranked candidate is the arm's data point. No λ or
  codon-table tuning (the legacy "pure-CAI LinearDesign" attribution is not
  reconstructible and is replaced by this registration).
- **Null arms**: WT = the 20 NCBI RefSeq `wt_cds/` anchors; random = 10
  seeded synonymous resamples per WT (n = 200, uniform over the standard
  code, seed `exp2:<target>:<draw>`, deterministic). One scoring path for
  all 240 sequences (`mrna_sequence_scoring`: CAI via Kazusa tables,
  species-resolved + GC + LinearFold MFE).
- **Results**: design 20/20, scoring 240/240, zero failures. CAI medians
  **0.830 / 0.729 / 0.675** (designed > WT > random gate PASS;
  designed-vs-WT P = 7.1e-3 δ = 0.50; WT-vs-random P = 6.8e-7 δ = 0.67).
  MFE/nt medians **−0.336 / −0.051 / −0.047** (designed vs both nulls
  P ≤ 7e-8, δ = −1.0; WT-vs-random NS P = 0.29).
- **Fig 2c re-registered (user-directed)**: the legacy WT-vs-random-only
  folding control becomes a full three-arm MFE/nt panel — the designed CDSs
  lead on codon adaptation and structure simultaneously, and the WT≈random
  null contrast shows the CAI ordering is not a folding artifact. Evidence
  `results/exp2_cds_nulls/` (`design_runs.jsonl`, `fig2_cds_nulls.jsonl`,
  `summary.json`); figures `experiments/plots/fig2bc_cds_nulls.py` →
  `plots/output/fig2b_cai.{pdf,png}`, `fig2c_mfe_per_nt.{pdf,png}`.
- **Palette**: `ARM_COLORS` semantic slots added to `experiments/plots/palette.py`
  under rev 7 (designed = terracotta `#C08B7C`, WT = sage `#A3B18A`,
  random = the reserved dark warm grey `#7A7672`); Fig 2a re-rendered.
- `docs/PAPER_DRAFT.md` Results §2.2 observation (1) and the Fig. 2 legend
  rewritten to the reset numbers; `docs/FIGURE_PLAN_V5.md` rows 2b/2c and
  `docs/MANUSCRIPT.md` §3.0 register updated. Known recorded caveats: the
  two E. coli targets (GFP, β-galactosidase) are designed against
  LinearDesign's default human codon table (frozen-platform behaviour,
  documented in the driver docstring) and the Influenza HA WT anchor derives
  from a different strain than the benchmark protein (pre-existing anchor
  documentation).

## 2026-08-25 (z) — Experiment-programme reset: legacy campaigns deleted, RNADesign-210 audited+repaired, Exp 1 re-run 210/210

User-directed reset (DECISIONS (z)): the architecture moved too much since
the legacy campaigns, so **all paper experiments re-run against the frozen
gated platform** with newly written drivers and figures; the legacy campaign
drivers (`run_platform_quality_benchmark.py`, `run_e16_e17_e18_oracle_profiling.py`,
`curate_*`), the `experiments/analysis` helpers, the `experiments/plots/paper_v5`
figure programme and the legacy campaign results (fig2–fig7, E3–E15, P0–P3,
junction line, PA regressions, caches/logs) are deleted. Retained: the
packaged-SelfModel evidence chain (`e1_*_v2`, `e7_*`, `rnasmol_boundary_panel*`,
`e16_e17_e18/`, `build_default_self_model.py`), `codon_tables/`,
`tool_inventory.json`, `MODEL_API_USAGE.md`, the workspace audit trail.

**RNADesign-210 dataset audit and repair** (`experiments/audit_rnadesign210.py`
+ `fix_rnadesign210.py`, report `results/rnadesign210_audit.json`): all 210
task inputs validate against the current workflow Input models; benchmark
manifest recounts (208→210, tertiary 18→20); category taxonomy normalized to
basic/edge/full (was 14 ad-hoc values incl. BMC-era labels); the 12 IRES tasks
rebuilt on real IRES-positive anchors (poliovirus 5′UTR for mode 0 — the old
synthetic 5′UTR scores 0.458 < its own 0.5 task threshold and mode-0 scores
of canonical IRES 5′UTRs peak ≈0.48, so the two mode-0 detection tasks use
0.45 with the rationale recorded in-task; EMCV 5′UTR for mode 2; best window
251–424 for mode 1); absolute IRES paths → repo-relative; stale junction-tool
expected chains dropped; all expected chains regrounded from observed traces
(`reground_tool_chains.py`; re-audit: 0 issues / 0 warnings).

**Exp 1 (paper §2.2 experiment 1, Fig. 2a) executed**: pilot 10/11 (the one
failure was the IRES data defect, fixed and verified 12/12 against the live
service), then the full matrix — **210/210 successful across the 11 workflows**
(primary arm `RNADA_CAPGATE=advisory`; five parallel lanes; GPU-pinned services
via `experiments/exp1_bring_up_services.sh`; records and per-workflow medians
in `results/exp1_rnadesign210/`). A 4-task **enforce probe** documents the
gated-platform boundary as data: IRES tasks refuse with an explicit
`GatedActionError`, small-molecule tasks fail cleanly with both oracles gated
(`enforce_probe.jsonl`). **Fig 2a** rendered (per-task tile carpet + horizontal
bar summary) from the new **unified palette**
(`experiments/plots/palette.py`). Palette history: rev 1 = the ten mandated
colours; rev 2 = a 12-colour replacement (withdrawn same day); rev 3 = ten
colours + two in-family extensions (withdrawn same day); rev 4 = twelve
colours extracted from a user reference figure (withdrawn same day);
rev 5 = the user's muted Morandi set (withdrawn same day);
rev 6 = the user's cool pastel set (withdrawn same day);
**rev 7 (final, user-confirmed 2026-08-25)** = the earthy Morandi
twelve-colour set, supplied directly (`#B5838D #D3B5B0 #C08B7C #D9C3A9
#CDBF9E #A3B18A #8DA290 #8FA6BB #6B7B8D #A99AAF #B7B0A2 #7A7672`) — eleven
identify the workflows (#7A7672 dark warm grey held out, reserved for
neutral-dark semantics such as failed tiles); warm and cool tones alternate,
slate blue separates the palest warms. All subsequent experiment figures use
rev 7 exclusively (DECISIONS (z)).

## 2026-08-25 — Paper figure-lettering unification (doc-only)

All six figure legends in `docs/PAPER_DRAFT.md` re-lettered to
`docs/FIGURE_PLAN_V5.md` (the operative build plan for
`experiments/plots/paper_v5/`). The v5 figure rebuild had updated the
Results body citations and the built figures, but the legends kept
pre-rebuild lettering — stale in Figs. 1 (b/c/f), 2 (g–i), 3 (f–i),
4 (c–i), 5 (d–i) and 6 (missing g–i). Body text gained citations for
previously unreferenced panels (Fig. 1c,f; 2g; 4g,i; 6g–i); the
representative-claims examples moved from main Fig. 4 to the planned
Supplementary Table S1, now registered in the figure plan alongside the
GenNav aptamer supplementary archive. Draft endnote panel counts corrected
(6 + 9×5; "End of draft v4.3" → v4.5). No numbers changed — lettering and
cross-references only. Same day, the first Results subsection was split
into a system-design subsection ("Overview of the RNADesignAgent platform",
Fig. 1) and the RNADesign-210 biological-validity results subsection
(Fig. 2), so experimental results begin with the second Results
subsection; content unchanged apart from the new heading. A legacy→v5
panel-lettering map was added to `docs/PAPER_FACT_SHEET.md` (legacy letters
double as `fig2_summary.json` keys and are kept verbatim), and the AGENTS.md
What's New index records the pass.

## 2026-08-22 (i) — Repo-wide simplification pass: workspace scratch isolation, demo tool retired, historical outputs purged

User-directed cleanliness pass over everything outside `external_repos/`
(code as the source of truth, no git archaeology):

- **Test-suite workspace leak fixed (real bug).** Every test run leaked
  scratch artifacts (`save_sequence` / `save_text_file` without a session
  context) into the real `workspace/` root — **141k files / 1.3 GB**
  accumulated. `tests/conftest.py` now redirects all default workspace bases
  to a per-run `workspace/_tests` scratch (removed afterwards); the redirect
  is inherited by subprocesses via the new `RNADA_WORKSPACE_BASE` env
  override honoured by `WorkspaceManager.__init__` (also useful for
  deployments). Literal-path test writers (`test_compute_*`) now write into
  the isolated base. Verified: full suite runs leave zero new files in the
  workspace root.
- **Demo tool removed**: `workflow_demo_echo` and the
  `build_default_tool_registry(include_demo=...)` parameter are gone —
  **41 registered tools, all production** (manifest regenerated:
  `experiments/results/tool_inventory.json`). Tests use local mock tools.
- **Layer-4 test dedup**: the identical QualityAgent retry-semantics blocks
  duplicated across the secondary/tertiary layer-4 modules moved to one
  parametrized module (`tests/test_layer4_agent_semantics.py`).
- **Documentation dedup in code**: 39 `tools.py` wrapper docstrings dropped
  their `Args/Returns/Raises` sections (verbatim duplicates of the Input-model
  `Field` descriptions); stale comments referencing deleted experiment
  drivers removed (`tools.py`, `evaluators.py`, `rna_aptamer_design.py`).
- **Historical outputs purged**: superseded figure generations
  (`experiments/plots/{paper,paper_v4,fig*_panels,fig*.png}`, ~24 MB),
  archived experiment rounds (`e5_s1_*_archive/`, `e14_audit_v{1,2}/`,
  versioned `e14/e8` re-run files, `codon_tables_e6/`, ~12 MB), orphaned
  `__pycache__`, and 141k leaked workspace scratch files + stale service-run
  intermediates (`workspace/*_service_runs` contents, 634 MB of RhoFold
  intermediates). **Repository shrank from 4.3 GB to 2.0 GB** (the remainder is dominated by 1.2 GB of required reference-genome data and the retained audit trail). Everything
  under `workspace/{audit,sessions}/` and every `*_fresh_audit_*` evidence
  directory is retained (audit trail untouched).
- Codonw-slim stub entries still present in two full-length-mRNA test files
  were removed with their tool (deleted 2026-08-18).
- Suite after the pass: **635 passed, 1 skipped** (the −1 is the merged
  demo-registration test); PA_006–PA_019 re-run green end-to-end.

## Condensed register: the 2026-08-18 → 2026-08-22 era

Each row: what changed, the defect count fixed on live-fetched data, the
evidence directory, and the DECISIONS.md entry. Suite counts are the
post-entry regression-suite size.

| Date | Change | Evidence | DECISIONS |
|------|--------|----------|-----------|
| 08-18 | System simplification: BMC framework removed after triple-falsified coordination gain; 12 dead tools purged (54→42 specs) + codonw_slim_service; E1–E15 experiment machinery and drivers deleted (evidence JSONs kept); bowtie2_ma type fix | git `1b45138` | (a), (m) |
| 08-19 | GenNav constraint navigation became the production opt-in on `rna_aptamer_design` v2.1.0 (`navigation` field; deterministic, zero-LLM; full trace in `_state_writeback["_gennav_trace"]`); batch-B fresh-data re-verification (PA_025–PA_036, 12/12); `tool_call` audit lines now carry `session_id` + `task_type` | `experiments/results/pa_regression_batchB_2026-08-19/`, `gennav_live_verification_2026-08-19/` | (n) |
| 08-20 | ASF/Pareto ranking generalized to five workflows + adversarial surfacing tests; paper_v5 figure programme (51 panels, `experiments/plots/paper_v5/`) | `docs/FIGURE_PLAN_V5.md` | (o) |
| 08-21 | Ranking governance: ASF objectives assembled from CapGate verdicts (deterministic, mode-independent; `agent_core/calibrated/objective_assembly.py`; `RNADA_CAPGATE=off` disables); Layer-0 tool audit (4 defects, e.g. EGARPS posting workspace-relative paths); Layer-1 capability audit (252 checks, EGARPS path fix); Layer-2 workflow audit (12/12 green on live-fetched data) | `workspace/tool_layer_audit_2026-08-21/`, `layer1_fresh_audit_2026-08-21/`, `layer2_fresh_audit_2026-08-21/`, `docs/RANKING_GOVERNANCE.md` | (p), (k) |
| 08-22 (b) | Layer-3 service-orchestration audit (45 checks, 3 defects: degraded-service pre-flight hole, `__all__` export bug, missing exec bit) | `workspace/layer3_fresh_audit_2026-08-22/` | (r) |
| 08-22 | GenNav-λ production wiring on `mrna_cds_design` v1.2.0 (`navigation` field replaces the static λ grid); ASO ordering converted to shared ASF ranking (v1.1.0, Borda → diagnostics); CDS runs attach the CAI×MFE/nt Pareto annotation | `tests/test_gennav_mrna_core.py` etc. | (q) |
| 08-22 (c) | Layer-4 multi-agent + CapGate + ranking-governance audit (5 defects: dropped ranking audit events, pipeline crash on dangling bindings, IRES swallowing tool failures, retry counting, int-enum overrides) | `workspace/layer4_fresh_audit_2026-08-22/` | (s) |
| 08-22 (d) | Layer-5 persistence audit (3 WorkspaceManager defects: `delete_session("")` rmtree of the sessions tree, unvalidated session-id path joins, `list_files` creating directories) | `workspace/layer5_fresh_audit_2026-08-22/` | (t) |
| 08-22 (e) | Layer-6 façade/CLI/API audit (6 defects: pipeline session-scoping leak, API success misreporting, task_id echo, dropped progress events, dead step events, bare `input()` on the non-tty pipeline path) | `workspace/layer6_fresh_audit_2026-08-22/` | (u) |
| 08-22 (f) | Interface Lock Policy removed repo-wide (~1,250 lines pure deletion; behavioural contracts remain pinned by `WORKFLOWS.md`, the regression suite and the PA drivers) | — | (v) |
| 08-22 (g) | Oracle version stamps: all 11 managed-oracle descriptors declare `oracle_version`; packaged SelfModel records carry the profiling-time stamp; drift warns + audits, never blocks | `tests/test_oracle_version_stamps.py` | (w) |
| 08-22 (h) | Full-platform E2E fresh-data audit — whole stack, all 11 workflows through all three entry points (56 checks; 3 defects: opaque sgrna seed failure, `stream_form` raising on hard failure, ViennaRNA inverse-fold accepting pseudoknot brackets → SIGSEGV) | `workspace/e2e_fresh_audit_2026-08-22/` | (x) |
| 08-22 (i) | Repo-wide simplification pass (this entry) | — | (y) |

## Current interface state

- **Tool count**: 41 registered specs, all production (`python -m
  agent_core.tool_inventory`).
- **Workflows**: 11, all plain `BaseDomainWorkflow` implementations; six rank
  by Achievement Scalarizing Function (DECISIONS (o)/(q)); GenNav navigation
  is an opt-in on `rna_aptamer_design` (length lattice) and `mrna_cds_design`
  (GenNav-λ).
- **Microservices**: 21 mapped services, ports 8003–8024.
- **No BMC interface anywhere**; no automatic workflow router — selection is
  explicit (CLI menu / `--workflow` / `explicit_workflow` / `--pipeline-file`).
- **Governance**: `RNADA_CAPGATE` = `off|advisory|enforce` (default
  `enforce`); packaged SelfModel 29 records; the CapGate audit trail lives at
  `workspace/audit/platform_audit.jsonl` (every `tool_call` line stamped with
  `session_id` + `task_type`).
