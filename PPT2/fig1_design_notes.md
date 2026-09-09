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
| **c** | CapGate 证据门控（创新 3；标题行标明"governs every Layer-0 tool call · every Layer-4 claim"）：上行 evidence 链 = 断言校验锚集（v3 · 95 entries）→ 预注册剖绘（AUROC>0.8 · ρ≥0.6 · top-1≥2/3）→ SelfModel 能力格阵（5 oracle × screening/ranking/docking + verified/failed/unprofiled 图例 + 迁移衰减 ×0.5、坏家族污染）；下行 enforcement = **输入**（planned tool call · draft claim）→ DecisionGate（allow/downgrade/reject/require profiling）与 ClaimGate（声明阶梯 absolute→target-relative→trend→suppressed）→ 追加式审计轨迹 | 上下双带 + 左右出入 |
| **d** | GenNav 约束导航（创新 4；标题行标明"Layer-2 generation step · mRNA CDS · aptamer"）：**输入** design profile（objective band: stability/balanced/expression · constraints · budget 35 calls）→ 通用生成参数格点可行性地图（三条 profile 泳道，feasible=sage / infeasible=空心 / delivered=环标；轴标注双任务："CDS: LinearDesign λ (35 gears) · aptamer: length 25–80 nt"）→ probe → allocate → deliver 迷你流 → **输出** candidate set（quota per band · diversity floor D1≥0.03 · or declared degrade）；显式降级路径 | 输入—机制—输出 三段式 |

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
