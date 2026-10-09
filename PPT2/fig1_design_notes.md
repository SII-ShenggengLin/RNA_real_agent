# Fig 1 系统示意图设计文档

> 用途：指导 RNADesignAgent 论文 Fig 1（系统示意图）的绘制与后续修改。
> 依据：`relevant_references/` 下七篇 Nature/Science/Nature 子刊智能体系统论文的主示意图逐一分析（图页视觉分析 + 作者图例原文提取），叠加 Nature Methods 作图规范与本项目 palette rev 7 作图约定。
> 本文档与旧版 PPT/fig1 无关，为全新设计。生成日期：2026-09-08。
> **2026-09-09 修订（用户反馈 16 点）**：六面板 → 四面板（删去旧 c「规模/审计」与旧 f「基准组成」，旧 d/e 重编号为 c/d）；a 图输入卡列出全部 11 个 workflow 任务芯片，删除带圈交叉引用字母与 iterate 回卷箭头；b/c/d 各自标题行标明所处层（L4 / Layer-0 工具调用 + Layer-4 声明 / Layer-2 生成步骤）；b 图改为 输入→四智能体主流→输出 结构，ASF rank 作为 SpecialistAgent 工作流的第 4 步内嵌（不再孤立），删除已证伪的 coordination loop；c/d 均为 输入→机制→输出 三段式；全图文字统一纯黑 Arial（三档字号：6.5 面板标题 / 5.8 卡名 / 5.0 正文）；`build_pptx.py` 重写为 python-pptx 原生形状渲染（`pptx_backend.py`），PPT 中每个组件可编辑（零图片）。

---

## 一、七篇参考文献主示意图逐篇分析

### P1 · Robin — "A multi-agent system for automating scientific discovery" (Nature 2025)

**结构**：3 个子图，全宽、纵向堆叠，整体约 2:1 宽高比（a ≈25% 高，b ≈45%，c ≈30%）。
- **a 端到端循环**：给定疾病靶点 → 生成假设 → 选出候选治疗药物 → 湿实验（画实验仪器图标）→ 自主分析原始数据 → 洞见 → 更新假设，**首尾闭合的循环箭头**。
- **b 智能体交互**：Robin 核心与语言智能体的分工（假设生成 / 实验数据分析）。
- **c 支撑智能体**：Crow、Falcon（浅/深文献检索）、Finch（实验数据分析）如何喂数给假设生成。
**视觉语法**：统一形状语言贯穿三张子图；湿实验用仪器图标；循环用回卷箭头；面板从宏观（做什么）到微观（谁来做）。

### P2 · AI Co-Scientist — "Accelerating scientific discovery with Co-Scientist" (Nature)

**结构**：3 个子图。
- **a 总览 + 交互范式**：自然语言研究目标 → 假设锦标赛（生成/反思/排序/进化/邻近/元评审六类 Gemini 智能体）→ 自我改进循环；科学家通过 UI 始终在场（对话、约束、反馈）。
- **b 多智能体架构**：Supervisor 解析目标 → 异步任务队列 → 专职 worker 智能体。**颜色类目编码明确**：红框 = 各专职智能体（框内只有名称）、蓝框 = 科学家在环输入与反馈、深灰箭头 = 信息流、红箭头 = 智能体间反馈回路。
- **c 端到端验证**：三个生物医学问题（AML 药物重定位 / 肝纤维化表观靶点 / AMR 基因转移）+ 体外实验验证。
**视觉语法**：圆角矩形智能体卡（名称 + 一行角色）；泳道式排布；箭头颜色即语义；panel b 是"架构解剖图"的典范。

### P3 · "Agentic AI and the rise of in silico team science" (Nature Medicine, Perspective)

**结构**：1 张概念图，两个语义区。
- **a** 人类研究团队 vs 智能体 AI 团队并排对照（同样的分工结构）。
- **b** 角色扮演智能体的内部特征：每个智能体被赋予角色/职责 + AI 能力增强；强调人 ↔ 智能体 ↔ 计算工具的通信质量决定最终目标达成。
**视觉语法**：上下对照布局；人类与智能体镜像排布；中心突出"通信/协作"连线。

### P4 · ERA — "An AI system to help scientists write expert-level empirical software" (Nature)

**结构**：1 张主示意 + 2 张轻结果（示意图与首个结果同图）。
- **a 算法示意**：可评分任务 + 研究思路 → LLM 生成代码 → 沙盒评估 → 嵌入树搜索（探索/利用平衡的节点选择）。
- **b** Kaggle 基准性能条形图。**c** 自动化迭代闭环示意。
**视觉语法**：单面板内部用三条水平泳道承载"输入—核心循环—输出"；核心算法画成循环 + 树结构小图；文字极少。

### P5 · DeepRare — "An agentic system for rare disease diagnosis with traceable reasoning" (Nature Medicine)

**结构**：3 个子图。
- **a 系统工作流**：多模态患者数据（HPO 术语、基因组变异）→ 分层 MCP 式架构（BioRender 风格图标）→ 排名 top-K 诊断 + 证据支撑的推理链。
- **b 知识架构**：**sunburst（双层环形图）**层级化整合诊断工具与生物医学知识源。
- **c 性能基准**：各类 LLM/智能体系统对比。
**视觉语法**：BioRender 生物风格图标（DNA、文档、数据库圆柱）；分层泳道；工具/知识全景用 sunburst 表达"覆盖面"。

### P6 · Biomni — "Autonomous biomedical research with an artificial intelligence agent" (Science)

**结构**：3 个子图（A/B/C 大写，Science 体例）。
- **A 行动空间构建流程**：2500 篇 bioRxiv → AI 驱动抽取 → 人工专家验证 → 105 个软件包 + 150 个专用工具 + 59 个数据库（**数字直接印在图中**）。
- **B 统一行动空间**：跨越 11 个生物医学子领域的工具/数据库全景（代表性工具列举）。
- **C 示例工作流**：检索相关工具 → 结构化推理计划 → 组合可执行代码 → 依观察迭代 → 收敛到答案。
**视觉语法**：面板 A = 数据加工流水线；面板 B = 广度全景（领域 × 工具矩阵感）；面板 C = 一条具体运行轨迹（retrieval→plan→code→refine 循环）。

### P7 · BioMedAgent — "Empowering AI data scientists using a multi-agent LLM framework…" (Nature Biomedical Engineering)

**结构**：2 个子图。
- **a 框架**：自然语言问题输入 → 规划/编码/执行三阶段（编号步骤 1–5，配 IE、MR、LTU 模块）→ 分析输出；用 DNA 序列比对小图作为领域图标。
- **b 基准组成**：327 道人工标注生物医学分析题的类别饼图。
**视觉语法**：顶层横条 = 输入→系统→输出；系统内部按阶段分块、步骤编号；末端配基准构成图。

---

## 二、共同点总结（可直接迁移的规律）

1. **面板数量 2–4 个，角色分工固定**：
   - **第 1 张：端到端总览**（做什么）——输入（自然语言目标/数据）→ 系统 → 输出（假设/诊断/候选），带一条**闭环箭头**表达迭代（Robin a、Co-Scientist a、Biomni C、ERA c 全部如此）。
   - **第 2 张：架构解剖**（怎么做）——智能体/模块画成圆角卡片，卡内只有**名称 + 最多一行角色**，箭头表达信息流，**颜色类目编码**（智能体 vs 人类 vs 工具 vs 数据各占一色）（Co-Scientist b、Robin b/c、BioMedAgent a）。
   - **可选第 3 张：广度全景或验证预览**——行动空间/知识源全景（Biomni B、DeepRare b 的 sunburst）或三案例验证（Co-Scientist c、DeepRare c）。
2. **阅读顺序 = 左→右、上→下，且"逐级放大"**：宏观循环 → 内部架构 → 单次运行/广度。读者 10 秒内从 panel a 获得闭环叙事，30 秒内从后续 panel 找到自己关心的模块。
3. **文字极简**：标签全部 ≤ 6 个词；数字（工具数、任务数、验证率）以 KPI 形式直接印在图中；**图内没有完整句子**（例句最多以引号短语出现）；所有解释性内容留给 caption。
4. **视觉语言全局统一**：同一种卡片圆角、同一族箭头、同一种图标体系贯穿全图；颜色 = 语义类目而非装饰（一般 3–6 个填充色 + 灰/黑中性色）；虚线/实线/颜色区分信息流类型。
5. **图与论文叙事一一对应**：panel a 对应摘要首句的主张；架构 panel 对应 Methods 的模块小节；广度/验证 panel 对应首个结果小节。图就是论文的"目录"。
6. **循环感是这类图的第一识别特征**：几乎每篇的主图都有一个显眼的自我改进/假设更新/推理迭代闭环。
7. **Nature 家族版式细节**：子图字母 a、b、c（8 pt 粗体无衬线，左上角，无括号无句点）；图内无标题（主张写进 caption）；无衬线字体 5–7 pt；矢量优先；双栏宽 183 mm。

## 三、Nature Methods 作图硬性要求（用于本图的自检清单）

- **宽度**：单栏 89 mm / 1.5 栏 120 mm / 双栏 183 mm；本图取双栏 183 mm，高 ≈ 185 mm（≤ 247 mm 上限）。
- **字号**：图内文字 5–7 pt（本图统一 6 pt，纯黑 `#000000`；面板字母 8 pt Arial Bold）。
- **字体**：Arial/Helvetica 无衬线（本机 Arial 已可用；`pdf.fonttype 42`）。
- **面板字母**：小写粗体 a–f，组图时统一绘制在每面板左上角（无括号、无句点）。
- **图内无标题、无边框装饰**；主张与统计写 caption。
- **配色**：色盲友好、避免红绿对；本项目 palette rev 7 十二色 Morandi 低饱和组天然满足。
- **线宽**：0.25–1 pt 区间（框线 0.8、主流 1.0、发丝线 0.4）。
- **交付**：矢量 PDF + ≥1200 dpi PNG；灰度打印仍可辨（本图用形状+文字冗余编码颜色语义）。

## 四、我们的 Fig 1 设计方案（四面板，双栏 183 × 200 mm，2026-09-09 修订）

依据：PAPER_DRAFT v4.5 的 Fig 1 图例（内容口径）+ 最新代码事实（2026-09-07 DECISIONS (bb) 后状态）+ 2026-09-09 用户反馈。整页 183 × 200 mm。布局行（全宽 181 mm，x=1，3 mm 间隔）：a（y=146.5, h=50）→ b（y=99.5, h=44）→ c（y=46.5, h=50）→ d（y=1, h=42）；面板字母 a–d 组图时绘制（每面板上方 0.8 mm 留白处，左上角）。

| 面板 | 内容（对应创新点） | 视觉形式 |
|---|---|---|
| **a** | 端到端总览：设计目标（自然语言）+ **全部 11 个 workflow 任务芯片**（mRNA CDS · full-length mRNA · mRNA scoring · siRNA · sgRNA · IRES · aptamer · ASO screen · RNA secondary · RNA tertiary · small-molecule）→ 七层平台脊柱（L6→L0，每层名称+关键数字，审计竖轨）→ 排名候选 + 追加式审计轨迹 + 门控报告；底边两条设计承诺徽章："LLM never writes sequences"、"pre-registered · budget-matched"（创新 1） | 左输入卡 — 中七层脊柱 — 右输出卡 |
| **b** | 多智能体执行层（标题行标明 Layer 4 / zoom of panel a）：**输入** Pipeline plan（single form · multi-node · explicit workflow）→ PipelineAgent（确定性调度，0 LLM）→ SpecialistAgent（内嵌工作流四步 generate → evaluate → score → **ASF rank**；仅硬失败重试）→ SynthesisAgent（多节点综合、起草报告）→ ClaimGate → **输出**（ranked candidates + gated report）；QualityAgent 虚线卡挂 SpecialistAgent 下方，两条点线箭头表达 advisory 双向（cannot fail a run）；左下角三态箭头图例（实线=data · 虚线=governance · 点线=advisory） | 输入—主流—输出 三段式 + advisory 支路 |
| **c** | CapGate 证据门控（创新 3；标题行标明"governs every Layer-0 tool call · every Layer-4 claim"）：上行 evidence 链 = 断言校验锚集（v3 · 95 entries）→ 预注册剖绘（AUROC>0.8 · ρ≥0.6 · top-1≥2/3）→ SelfModel 能力格阵（5 oracle × screening/ranking/docking + verified/failed/unprofiled 图例 + 迁移衰减 ×0.5、坏家族污染）；下行 enforcement = **输入**（planned tool call · draft claim）→ 拦截点（动作 pre-execution：ToolExecutor choke point · 逐调用审计戳记；声明 pre-publication：对照能力证据核查）→ DecisionGate（allow/downgrade/reject/require profiling）与 ClaimGate（声明阶梯 absolute→target-relative→trend→suppressed）→ 追加式审计轨迹 | 上下双带 + 左右出入 |
| **d** | GenNav 约束导航（创新 4；标题行标明"Layer-2 generation step · mRNA CDS · aptamer"）：**输入** design profile（objective band: stability/balanced/expression · constraints · quota 35 calls）→ 通用生成器设置可行性地图（三条 profile 泳道，feasible=sage / infeasible=空心 / delivered=环标；轴标注双任务："CDS: LinearDesign λ (35 values) · aptamer: length 25–80 nt"）→ probe → allocate → deliver 迷你流 → **输出** candidate set（quota per band · diversity floor D1≥0.03 · or declared infeasible）；显式不可行路径 | 输入—机制—输出 三段式 |

### 全图统一视觉规范（palette rev 7 + 2026-09-09 文字纪律）

- **色语义**（十二色 verbatim）：`#D3B5B0` 输入/用户域；`#8FA6BB`/`#6B7B8D` 平台层与数据主流（slate 最深，作分隔）；`#B5838D` 智能体卡；`#C08B7C` terracotta = 治理/门控（虚线箭头）；`#A3B18A`/`#8DA290` = verified/交付成功/ASF；`#7A7672` = 中性深灰（failed/降级）；`#D9C3A9`/`#CDBF9E` = 锚集/剖绘域；`#A99AAF` = 审计/报告域。
- **箭头语义**：实线 slate = 数据/执行流；虚线 terracotta = 门控/治理；点线 warm grey = advisory-only。全图只有这三种箭头（图例印在 b 图左下）。
- **卡片**：统一圆角矩形，填充 = 色域 6–24% 透明度 + 同族深色 0.8 pt 描边；卡内第一行 5.8 pt 粗体名称、其余 5.0 pt。
- **文字纪律（2026-09-09 收紧）**：全部文字纯黑 `#000000` Arial，仅三档字号（6.5 面板标题粗体 / 5.8 卡名粗体 / 5.0 正文）；层级只靠字重与字号，不用彩色文字；任何标签 ≤ 6 词；无完整句子；解释进 caption。
- **面板字母**：a–d 由 `assemble.py` / `build_pptx.py` 组图时统一绘制（8 pt Arial Bold `#1A1A1A`，面板左上角外侧）。

## 五、文件清单（PPT2/，2026-09-09 版）

| 文件 | 作用 |
|---|---|
| `fig1_design_notes.md` | 本文档 |
| `style.py` | 共享样式：palette rev 7、字体、mm 坐标画布、卡片/箭头/图标绘制助手 + `MplBackend`（后端无关 API 的 matplotlib 实现） |
| `pptx_backend.py` | `PptxBackend`：同一后端 API 的 python-pptx 原生形状实现（圆角矩形 / 连接符 / 文本框 / 椭圆 / freeform，含填充透明度与箭头端点的 XML 注入）——PPT 每个组件可编辑 |
| `panel_a.py` … `panel_d.py` | 每面板一个脚本，核心为后端无关的 `build(B)`；直接运行 → matplotlib 渲染 `panels/{a..d}.{pdf,png(1200 dpi),_ppt.png(300 dpi)}`，内置文字碰撞 QA（`qa_check.py`） |
| `assemble.py` | 组合成 `panels/fig1_composite.{pdf,png(1200 dpi),_ppt.png(300 dpi)}`（183 × 200 mm，字母 a–d 组图时绘制） |
| `build_pptx.py` | 生成 `fig1_panels.pptx`（5 页，页面 = 183 × 200 mm）：第 1 页整图组合（四个面板原生形状 + 字母）、第 2–5 页每子图一页居中；**全部原生形状、零图片** |

修改入口：改单个面板 → 编辑对应 `panel_x.py` 的 `build()` 后 `python panel_x.py`（matplotlib 与 PPT 两个渲染共用同一份布局代码）；重排版/字母 → `python assemble.py`；重出 PPT → `python build_pptx.py`。

2026-09-12（批次五连带）：panel_d 画布文本与 §2.5 去术语化同步——gear/lattice/degrade → setting/value/infeasible（quota 措辞同步），面板重渲染 + 组合图 + pptx 重建，QA 绿。

2026-10-02（图例批挂账执行）：panel_a 底部两条设计承诺徽章删除（图例句已删、徽章失去指代；画布 50→44 mm、内容整体下移 6 mm）、面板文字术语同步——a "RNADesignAgent platform"→system；b 角注 "zoom of panel a · layer L4"→"a detailed view of the multi-agent execution layer in panel a"（对齐新图例）；c "assertion-curated"→verified、"SelfModel · capability map"→capability map、"transfer decay ×0.5"→"reduced confidence ×0.5"、"never-profiled"→unprofiled（全文退役词）。`assemble.py` 页高 200→194 mm（a 行 44 mm，其余不动），三面板重渲 + 组合图 + pptx 重建，QA 绿。上文第四节表格与布局行保留书写时形态（50 mm 时代）。

2026-10-07（逐图调整批 — Fig. 1，用户八点指示；先修代码再重渲、子图先于大图；三项措辞裁定）：四面板全部文字与润色后正文 + Fig. 1 图例逐站核对（组合图 PDF 文本层逐字提取比对），修复代码后四面板重渲 + 组合图重装配（183×194 mm 页幅不变）+ `fig1_panels.pptx` 原生形状重建，文本层机检全绿（退役词零残留、新词全部在位、字母 a–d 各一次）、逐面板文字碰撞 QA 全绿，图例与正文零改动。零实验/零冻结数据改动（示意图；41 工具/21 微服务/11 工作流/95 entries 与五预测器能力格阵逐字）。(i) **a**：11 工作流芯片阵退役为一个具体自然语言设计目标例子（用户裁定全长 mRNA Spike 例，斜体引号；工作流计数留在 L2 行）；角注 "seven deterministic layers"→"seven layers"；层事实对齐润色后 Overview（L6 form-driven interface、L4 orchestrate · review · synthesize、L2 四名词逗号枚举退役箭头链、L1 validates outputs · audit write-back、L0 41 tools · uniform interface）；"claims gated"→"claim-gated"（图例形容词）。(ii) **b**：角注与右下审计注记删除（图例 (b) 句与 a 审计轨承载）；标题 "Layer 4 · multi-agent execution" 保持（用户裁定——与 Overview "multi-agent execution layer" 及图例逐字一致）；ClaimGate 两行对齐图例 "checks every claim / before release"；输出卡图标文字重叠修复（加宽至 19 mm、图标居左、文字左对齐）。(iii) **c**：标题带层标注 "(Layer-1 tool calls · Layer-4 claims)"（用户裁定，对齐 Overview "every Layer-1 capability call"），角注删；锚卡 "v3" 版本号删（95 entries 留——读者面不报版本）；能力图机制注记（reduced confidence ×0.5 / worst family poisons）退 Methods；两张拦截卡删（门标题 planned actions / outgoing claims 自带时序）；DecisionGate 芯片 "require profiling"→"require-profiling"（图例逐字）；ClaimGate 阶梯改下行楼梯形+渐淡填充+图例逐字四档（absolute / same-target relative / trend-only / suppressed——面板旧 "target-relative"/"trend" 已偏离图例）；剖绘三阈值配迷你图形（筛查曲线/排序柱/对接靶心，均由 line/dot 基元组成、双后端可渲）；审计卡瘦身（图标+audit trail+append-only）。(iv) **d**：标题改 "GenNav · constraint navigation (Layer-2 generation step)"（用户原话，mRNA/适配体范围由图例承载）；LinearDesign-λ 例图（三条 profile 泳道 × 35 设置 + "quota · 35 calls" + "D1 ≥ 0.03" 内部参数）退役——probe/allocate/deliver 三步各配一个通用图形（设置轴上探测三点〔2 可行 sage + 1 不可行空心〕/配额方块堆叠于可行设置〔3/2/1〕/五枚 delivered 环标+成对距离尺），例子不再独大、每图形各承其义；degrade 路径保留（"no feasible setting / declared infeasible"）；点图例（feasible/infeasible/delivered）保留。(v) **配色（用户第 3 点，仿 nanoLM 参考图）**：十二色用法退役为克制方案——grey-blue 结构主色（全部卡片/层/智能体）、slate 线条与图标、sage = verified/feasible/delivered/allow、terracotta 仅门控与 failed、中性灰 = unprofiled/downgrade/suppressed；箭头三语义（实线 slate 数据 / 虚线 terracotta 治理 / 点线 advisory）不变，图例仍在 b 左下。上文第四节表格与布局注记按 as-written 保留书写时形态。

2026-10-07（逐图调整批第二轮 — Fig. 1，用户八点指示；先修代码再重渲、子图先于大图）：(i) **全图去填充**——结构卡片一律无填充、颜色只留在线条/边框/箭头上（`style.card` 与 `PptxBackend.card` 同步新规则：`edge=False` 的语义标记〔capability map 格阵、图例芯片、feasible 点等〕保留填充，带边框结构卡默认无填充），三个背景 zone 与两条色带整删，灰蒙感消除；新增后端方法 `measure()`——Mpl 按渲染器实测文本宽度、Pptx 按校准系数（混排 Arial ≈ 0.175 mm/char/pt 粗体，正常 ÷1.06）估算。(ii) **a**：输入卡茎环图标退役，改画构造示意（5′UTR–CDS · Spike–3′UTR 段盒 + poly(A) 尾线 + AUG ··· UAA 标记）+ 三条具体设计要求（CAI ≥ 0.80 · high MRL / GC 30–80% · homopolymer < 14 nt / CDS stem ≤ 30 bp——均为注册约束矩阵口径）；右侧三张输出卡图标删除、文字居中。(iii) **b**：QualityAgent 卡下移（y 8.0–15.5），两支 advisory 点线箭头箭身加长至 4.8 mm、箭头 ms 4.5、横距拉开至 6 mm——箭头与箭身重叠修复；ClaimGate 收窄至 19 mm 使门控箭头露出箭身；输出卡文档图标删除、文字居中；ASF rank 芯片改 slate 粗边+粗体（不再用填充深浅区分）。(iv) **c**：锚卡文档图标与剖绘三迷你图形（筛查曲线/排序柱/对接靶心）删除；ClaimGate 阶梯退役为一排四枚同高芯片（absolute / same-target relative / trend-only / suppressed）+ 降级小箭头；audit trail 卡删除数据库图标与 "append-only"，改印四条示例记录（call LinearDesign / gate allow / result CAI 0.91 / claim checked），副题 "one record per tool call"。(v) **c/d 标题注记** "(Layer-1 tool calls · Layer-4 claims)" / "(Layer-2 generation step)" 紧跟主标题、同字号同字族（6.5 pt 常规字重，位置由 `measure()` 确定）。(vi) **d**：五卡同带对齐（y 16–36，中间三卡不再偏低）；degrade 卡与 probe 卡同 x 同宽（40–74）；三步图形重画为自解释示意——probe=设置轴上试测 4 点、迷你柱对约束阈值虚线（sage 点=可行、空心=不可行，三可行一不可行与 allocate 三段呼应）；allocate="quota · 35 calls" 括尺 + 18/12/5 调用堆叠段 + 可行设置回声点 + "calls per feasible setting"；deliver=5 条示例序列 + 多样性括尺（diverse）；两侧卡文字具体化（Design profile=pre-registered + CAI/GC/homopolymer/quota 四行；Candidate set=5 per profile / all constraints met / or declared infeasible）；顶部点图例退役（新图形自解码）。逐面板文本碰撞 QA 全绿；组合图 183×194 mm 页幅不变；`fig1_panels.pptx` 重建（5 页原生形状：279/68/51/89/71 shapes）；图例与正文零改动，零实验/零冻结数据改动（示意图）。

2026-10-07（逐图调整批第三轮 — Fig. 1 面板 a，用户六点指示；先修代码再重渲、子图先于大图）：(i) "Design goal · natural language" 标题左侧人形图标删除，标题移至卡片左缘（x 6.8）；(ii) 输入卡图像由全长 mRNA 构造示意（5′UTR–CDS·Spike–3′UTR–poly(A) 段盒 + AUG ··· UAA 标记）改为刺突蛋白序列示意——mRNA 是设计输出而非输入，输入应为蛋白：珠链多肽（slate 连线 + 珠点、N/C 端标记）+ 前五枚珠下标注真实 P0DTC2 N 端残基 M F V F L + "Spike protein · 1,273 aa" 标签（序列与长度对基准靶标 `targets/SARS-CoV-2_Spike_WT.json` 逐字核实）；(iii) 输入卡内容纵向重排（标题 34.7 / 引号目标 28.8 / 蛋白标签 24.1 / 珠链 21.8 / 残基 19.8 / 三条要求 16.1·13.7·11.3），上下边距平衡至 ~4 mm、底部空带消除；(iv) L4 行 "orchestrate · review · synthesize" 经核对与润色后 Overview 定稿句 "The multi-agent execution layer (L4) orchestrates, reviews and synthesizes workflow runs" 逐字一致——保留不动（用户第 4 点答复：正文即此三动词，无更合适替换）；(v) 输出卡 "append-only" 删除（Fig. 1 图例仅载 "an audit trail"、正文未用该词，c 面板第二轮已删同词）、"Audit trail" 单行居中于卡心 22.75；(vi) 三支输出箭头对齐——全部自审计轨同一 x（rail_x+0.2 = 138.5）出发、止于各卡左缘同一 x（146.6）、y 取各卡中心（34.25/22.75/11.25），修复原 140.0/138.5 双起点错位。面板 QA 绿；组合图重装配（183×194 mm 页幅不变）+ `fig1_panels.pptx` 重建；组合图文本层机检按面板 a 区域裁取后绿（退役串 5′UTR/3′UTR/CDS · Spike/poly(A)/AUG ··· UAA/append-only 零残留、新串全部在位——"5′UTR" 在 c 面板能力格阵行标签为正当在位，故裁取检查）、字母 a–d 各一次。图例与正文零改动，零实验/零冻结数据改动（示意图）。登记：FIGURE_PLAN_V5（Fig 1 行 a + 表下段）、本条；PAPER_DRAFT 头注/CHANGELOG 沿第二轮先例待用户确认后补登。**同日追加（用户指出省略号与线段重合）**：珠链实线在省略处两侧断开（10.2–22.6 / 26.2–35.0）、只保留省略号，重渲 + 重装配 + pptx 重建，QA 绿。**同日追加二（用户指出省略号与线段未对齐 + 末三残基应标注）**：省略号文字退役，省略改画为链上三枚小圆点（r 0.28，x 23.5/24.4/25.3，与链同 y——根除字库度量偏移）；末三枚珠下标注真实 C 端残基 H Y T（P0DTC2 末端 …VKLHYT），重渲 + 重装配 + pptx 重建，QA 绿。

2026-10-07（逐图调整批第四轮 — Fig. 1 面板 b，用户六点指示；先修代码再重渲、子图先于大图）：(i) **输入卡措辞对齐正文**——"single form or / multi-node plan / explicit workflow" 改 "single-node or / multi-node / explicitly selected"（Methods L6 "The user selects the workflow explicitly" + README/ARCHITECTURE 的 single-node/multi-node PipelinePlan 口径；"form" 是 L6 界面层词汇、不属计划卡）；(ii) **PipelineAgent 介绍行**改图例 (b) 逐字 "schedules the pipeline"（"deterministic schedule" 与 "0 LLM calls" 删除——确定性与零 LLM 事实由 Methods 承载）；(iii) **ASF rank 芯片去强调**——粗体与 slate 粗边退役，四枚工作流步骤芯片同式（grey-blue 0.4 边、5.0 常规）；(iv) "retries hard failures only" 与 "advisory · cannot fail a run" 两行删除（Methods 与箭头语义已承载）；(v) **QualityAgent 卡改实边**——与其他三张智能体卡同式 grey-blue 实边（虚线轮廓此前误读为非智能体），卡收窄 30→20 mm、单行标题居中；advisory 语义仍由两支点线箭头与图例承载；(vi) **箭头/箭身重合根修**——共享 `style.flow` 改双段绘制（pattern 箭身止于箭头基线、箭头段纯色实绘，镜像同步 `PptxBackend.flow`；仅直箭头、曲线与退化箭头回退单段旧绘），b 的短门控箭（ClaimGate→输出，3.4 mm）与 advisory 点线（垂直对+图例）头身重叠消除，a/c/d 同享修复。同轮：pipeline plan 与 ranked candidates 两张**数据产物卡**（非智能体）改中性 warm-grey 边，grey-blue 边在面板 b 内读作智能体专属（ClaimGate 保 terracotta 门边）。逐面板碰撞 QA 绿；组合图重装配（183×194 mm 页幅不变）+ `fig1_panels.pptx` 重建（b 页 20 连接符=10 箭×〔箭身+箭头〕两段）；组合图文本层机检按面板 b 区域裁取后绿（退役串零残留、新串全部在位）、字母 a–d 各一次。图例与正文零改动、零实验/零冻结数据改动（示意图）。登记：FIGURE_PLAN_V5（Fig 1 标题行+行 b+表下段）、本条；PAPER_DRAFT 头注/CHANGELOG 沿第二、三轮先例待用户确认后补登。
**同日追加（用户指示）**：面板 b 左下三态箭头图例由左对齐改为整组水平居中——`measure()` 实测三枚标签宽度、固定箭头 7.0 mm/文距 1.4 mm/项距 10.0 mm 组合后置于画布中线；重渲+重装配+pptx 重建，QA 绿。
**同日追加二（用户指示：QualityAgent 独占一行偏空）**：三态箭头图例上移至第二行、居中于 QualityAgent 卡右侧空区（x 98–177），与卡同基线 y 10.5——第二行不再空、图例贴近它所解释的点线箭头；QualityAgent 卡垂直居中于主行下方带（y 6.75–14.25，advisory 箭头 14.65–19.45）。重渲+重装配+pptx 重建，QA 绿、文本层机检绿。

2026-10-07（逐图调整批第五轮 — Fig. 1 面板 c，用户七点指示；先修代码再重渲、子图先于大图）：(i) **Anchor sets 卡**——裸文字 "verified / 95 entries" 改为小图形+白话：三行「珠链分子 + 实测值横条」（slate 链与珠、grey-blue 值条）+ "known measurements" / "95 entries"——锚集是什么一眼可见；(ii) **Profiling 卡收窄 46→28 mm**，三条协议行由左对齐改居中（原来标题居中、正文靠左不协调）；(iii) **capability map**——标题按卡片中心居中（原按格阵中心，偏左），格阵横纵转置：五预测器作列头（"MRL · 5′UTR"、"RhoFold · EGARPS" 按 " · " 拆两行）、screening/ranking/docking 作行标签，verified/failed/unprofiled 图例改一行横排于格阵下方——拥挤消除；成绩逐字不变（转置仅换布局）；(iv) **输入卡具体化**——"via ToolExecutor"/"agent or workflow" 退役，改具体例子+小图形：命令行符号 ">_" + "e.g. call LinearDesign"、对话气泡 + "e.g. 'candidate 1 is best'"（与审计示例记录、ClaimGate 阶梯呼应）；(v) **DecisionGate 卡注记 "allow executes · unprofiled predictors blocked" 删除**，卡高 11→10 mm；(vi) **audit trail 卡**——四条示例记录挂上竖直时间线，节点按记录类型配小图形（call=尖括号 / verdict=菱形 / result=三根递升柱 / claim=对勾；门控类 terracotta、执行/数据类 slate）；**后端修复**：`MplBackend.line` 补 zorder 透传（`PptxBackend.line` 同签名、PPT 插入序天然在后）——首版图形线被白色节点圆盖住（line 默认 zorder 4 < dot 的 5）；(vii) **缺陷修复**：profiling→capability map 箭头原止于 90.7、插入地图卡左缘（89）内 1.7 mm（箭身穿卡框）——新布局止于卡缘外 0.3 mm。逐面板碰撞 QA 绿；组合图重装配（183×194 mm 页幅不变）+ `fig1_panels.pptx` 重建（c 页 138 形状）；组合图文本层机检裁面板 c 区域后绿（退役串 "via ToolExecutor"/"agent or workflow"/"allow executes"/"unprofiled predictors blocked" 零残留、新串全部在位）、字母 a–d 各一次；图例与正文零改动、零实验/零冻结数据改动（示意图；95 entries 与五预测器成绩格逐字）。登记：FIGURE_PLAN_V5（Fig 1 标题行+行 c+表下段）、本条；PAPER_DRAFT 头注/CHANGELOG 沿第二至四轮先例待用户确认后补登。

2026-10-07（第五轮同日追加 — 面板 c，用户三点指示；先修代码再重渲）：(i) **"95 entries"→"95 molecules"**——用户问 entries 指什么：核对 `e1_anchor_set_v3.json`，每条 entry = 一个带实测 Kd 的适配体分子，"entries" 是数据库行话、读者不解码，改 "95 molecules"（与珠链图形互释）；(ii) **输入卡两枚小图形删除**（命令行符号与对话气泡经用户裁定无信息量），例子文字改为卡内居中，输入卡宽度恢复 32→30 mm、入射箭头恢复 35.3→43.7；(iii) **审计轨时间线与四枚节点图形删除**（经用户裁定无信息量），恢复纯文字四条示例记录（第五轮措辞 "verdict allow" 保留——Fig. 4h "Gate verdicts" 名词）。重渲 + 重装配 + pptx 重建（c 页 115 形状），文本层机检绿（"95 entries"/"gate allow" 等零残留、"95 molecules"/"verdict allow" 在位）、碰撞 QA 绿；图例与正文零改动。

2026-10-07（第五轮同日追加二 — 面板 c 排版，用户两点指示；先修代码再重渲）：(i) **audit trail 卡收窄 40→32 mm**——从右侧收（左缘 134 不动，两条门控虚线箭头几何不变；记录文字块实测止於 ~163，右缘收至 166 后随整体平移至 171）；(ii) **面板 c 全部内容（含标题）整体右移 5 mm**——收窄后内容块 5–166 右空偏大，平移后 10–171、左右边距各 ~10 mm 均衡（兄弟面板内容 4–177/179/180）。重渲 + 重装配 + pptx 重建，碰撞 QA 绿、文本层机检绿（必备串全部在位、退役串零残留、字母 a–d 各一次）；图例与正文零改动。

2026-10-07（逐图调整批第六轮 — Fig. 1 面板 d，用户六点指示；先修代码再重渲、子图先于大图；两项裁定）：(i) **probe 图形补解码**——卡内顶部加两行紧凑键（dash 样例 + "constraint"；sage 点 + "feasible"、空心点 + "infeasible"，均 measure() 居中成组；第二轮"图形自解码"假设对读者不成立），轴标题居中改 "generator setting"（原右对齐 "generator settings"）；(ii) **allocate 数字解码**——注记 "calls per feasible setting" 改 "3 feasible settings share the quota"（回声点=probe 找到的三个可行设置，18/12/5=三者对 35 调用配额的分配）；(iii) **degrade 卡缩窄**（用户裁定"缩窄就地保留"）——自 probe 卡宽 34 mm 缩至文本宽（measure() 驱动 ~20 mm），仍在 probe 卡正下方、点线箭头保留（机制点"probe 阶段即发现不可行、不花预算"的分支出处可视化保留；删除整框与移到输出端两方案经用户否决）；(iv) **deliver 序列加长**——五条示例序列改 9 + … + 4 nt 带中省略号（"AUGCGUAAC…GCCU" 等），读作长序列片段而非全长；副题 "5 per profile · diversity floor" 改 "5 candidates · diversity threshold"；(v) **candidate set 卡补全**——"5 per profile" 展开为 "5 candidates / per profile"，卡面按输入卡基线排五行（32.4/29.2/26.6/24.0/21.4），底部空带消除；(vi) **floor 术语裁定**——"diversity floor" → "diversity threshold" 全文统一（用户裁定；§2.5 正文两处 + fig5a 子图标签 + 本面板），两处 "diversity minimum" 离群（Methods GenNav 组件句、Fig. 1d 图例）一并归一；fig5a 重渲 + Fig. 5 组合图重装配（190.1×260.6 mm 页幅不变、raster QA 绿、文本层机检 "diversity floor" 零残留/"diversity threshold" 在位/字母 a–g 全）。面板 d 碰撞 QA 绿；组合图重装配（183×194 mm 页幅不变）+ `fig1_panels.pptx` 重建；组合图文本层机检裁面板 d 区域后绿（退役串 "5 per profile"/"diversity floor"/"calls per feasible setting"/"generator settings" 零残留、新串全部在位、省略号以 U+2026 存活于文本层）、字母 a–d 各一次（按组图 8-pt 字号过滤——面板 a 内 5-pt 正文词 "a" 为本批前存量）。零实验/零冻结数据改动（示意图；quota 35 与 18/12/5 示意不变）。登记：FIGURE_PLAN_V5（Fig 1 标题行+行 d+表下段、Fig 5a 行注）、本条、AGENTS.md；PAPER_DRAFT 头注/CHANGELOG 沿第二至五轮先例待用户确认后补登（注意：与第二至五轮纯图件批不同，本批含正文与 Fig. 1d 图例的术语改动）。
**同日追加（用户三点指示）**：(i) probe 虚线与下方实线同长（44–70）；(ii) degrade 卡恢复 probe 卡同宽（34 mm）、两行文字并为一行 "no feasible setting · declared infeasible"（实测 31.1 mm、两侧各留 1.5 mm）；(iii) deliver 序列块+多样性括尺+"diverse" 标签作为整组在卡轴线上居中（序列 x=132.8、括尺随最宽行 measure() 定位），右侧空带消除。重渲+重装配+pptx 重建，碰撞 QA 与文本层机检绿。**同日追加二（用户指示）**：probe 约束虚线左端原起于 44、恰落在首根柱子（43–45）中部，像只画了一半——虚线向两端各延 2 mm（42–72），完整跨过设置轴区域；重渲+重装配+pptx 重建，QA 绿。
