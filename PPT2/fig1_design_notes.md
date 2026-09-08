# Fig 1 系统示意图设计文档

> 用途：指导 RNADesignAgent 论文 Fig 1（系统示意图）的绘制与后续修改。
> 依据：`relevant_references/` 下七篇 Nature/Science/Nature 子刊智能体系统论文的主示意图逐一分析（图页视觉分析 + 作者图例原文提取），叠加 Nature Methods 作图规范与本项目 palette rev 7 作图约定。
> 本文档与旧版 PPT/fig1 无关，为全新设计。生成日期：2026-09-08。

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

## 四、我们的 Fig 1 设计方案（六面板，双栏 183 × 185 mm）

依据：PAPER_DRAFT v4.5 的 Fig 1 图例（内容口径）+ 最新代码事实（2026-09-07 DECISIONS (bb) 后状态）。整页 183 × 188 mm。布局行：a 全宽 181 × 50 mm（x=1, y=136）；b 121 × 46 + c 57 × 46（y=87）；d 121 × 46 + e 57 × 46（y=38）；f 全宽 181 × 34 mm（y=1）；面板字母 a–f 组图时绘制。

| 面板 | 内容（对应创新点） | 视觉形式 |
|---|---|---|
| **a** | 端到端循环 + 七层平台脊柱：设计目标（自然语言）→ 平台（L6→L0 七层堆叠，每层名称+关键数字）→ 排名候选 + 审计轨迹 + 报告，输出回环"迭代"；底边两条设计承诺徽章："LLM never writes sequences"、"pre-registered · budget-matched"（创新 1） | 左输入卡 — 中七层脊柱 — 右输出卡；审计竖轨连接每层工具调用 |
| **b** | 多智能体执行层（L4），**每个智能体的贡献被测量**：PipelineAgent（确定性调度，0 LLM）→ SpecialistAgent（仅硬失败重试）→ QualityAgent（advisory，31/31 会话 on/off/failing 逐轮结果一致）→ SynthesisAgent（报告→ClaimGate）；被证伪移除的协调环画成划掉的灰卡（创新 1 的"measured agency"） | 执行主流 + 虚线 advisory 支路；划除卡 + τ=1.0 注记 |
| **c** | 平台一瞥：KPI 雷达（11 workflows · 41 tools · 21 services · 210 tasks · 210/210 完成）+ 审计构成环形 inset（Exp-24 冻结切片 24,897 事件 = 19,848 工具调用 + 4,862 门决策 + 187 排名装配） | 雷达 + donut |
| **d** | CapGate 证据门控（创新 3）：断言校验锚集 → 剖绘（AUROC>0.8 · ρ≥0.6 · top-1≥2/3）→ SelfModel 能力格阵（verified/failed/unprofiled + 迁移衰减 ×0.5、坏家族污染）→ 双门：DecisionGate（allow/downgrade/reject/require profiling）与 ClaimGate（声明阶梯 absolute→target-relative→trend→suppressed）→ 追加式审计轨迹；底部两条微案例 | 左→右流水线 + 小格阵 + 双门卡 |
| **e** | GenNav 约束导航（创新 4）：λ 齿轮格点 35 点可行性地图（三档 profile 泳道：stability/balanced/expression，feasible=sage / infeasible=灰）→ 预算分配（35 raw calls）→ 每档交付 5 条（D1≥0.03 多样性下限）或显式降级；小字注明适配体长度格点同协议 | 导航地图 + 迷你循环 |
| **f** | RNADesign-210（创新 2）：双层 sunburst——内环 5 个任务族（mRNA 治疗 54 / RNAi·CRISPR 52 / 结构设计 45 / 适配体·小分子 33 / 筛选·预测 26），外环 11 工作流及任务数；侧注 null 模型（WT · random-synonymous）与文献锚（BNT162b2 · Kd sets · IRES · MRL）徽章 + "210/210" 徽章 | sunburst + 徽章 |

### 全图统一视觉规范（与 palette rev 7 一致）

- **色语义**（十二色 verbatim）：`#D3B5B0` 输入/用户域；`#8FA6BB`/`#6B7B8D` 平台层与数据主流（slate 最深，作分隔）；`#B5838D` 智能体卡；`#C08B7C` terracotta = 治理/门控（虚线箭头）；`#A3B18A`/`#8DA290` = verified/交付成功；`#7A7672` = 中性深灰（failed/移除/降级）；`#D9C3A9`/`#CDBF9E` = 锚集/基准域；`#A99AAF` = 审计/报告域；`#B7B0A2` = 服务/杂项。工作流专属色沿用 `WORKFLOW_COLORS`。
- **箭头语义**：实线 slate = 数据/执行流；虚线 terracotta = 门控/阻断；点线 warm grey = advisory-only。全图只有这三种箭头。
- **卡片**：统一圆角矩形（`boxstyle="round,pad=0"`，手动 mm 圆角），填充 = 色域 12–18% 透明度 + 同族深色 0.8 pt 描边；卡内第一行 6 pt 粗体名称、第二行 ≤4 词角色或数字。
- **图标**（纯矢量小件，全图统一）：RNA 茎环、文档（折角矩形）、数据库圆柱、齿轮、放大镜、勾/叉圆章。
- **文字纪律**：任何标签 ≤ 6 词；数字用 KPI 印刷体；无句子；解释进 caption。
- **面板字母**：a–f 由 `assemble.py` 组图时统一绘制（8 pt Arial Bold `#1A1A1A`，左上角，距面板 1.5 mm）。

## 五、文件清单（PPT2/）

| 文件 | 作用 |
|---|---|
| `fig1_design_notes.md` | 本文档 |
| `style.py` | 共享样式：palette rev 7、字体、mm 坐标画布、卡片/箭头/图标绘制助手 |
| `panel_a.py` … `panel_f.py` | 每面板一个脚本 → `panels/{a..f}.{png,pdf,_ppt.png}`（PNG 1200 dpi + 矢量 PDF + 300 dpi PPT 版）；脚本内置文字碰撞 QA（`qa_check.py`） |
| `assemble.py` | 组合成 `panels/fig1_composite.{png,pdf,_ppt.png}`（183 × 188 mm，字母 a–f 组图时绘制） |
| `build_pptx.py` | 生成 `fig1_panels.pptx`（8 页）：封面 + a–f 每子图一页（含标题条）+ 整图一页 |

修改入口：改单个面板 → 编辑对应 `panel_x.py` 后 `python panel_x.py`；重排版/字母 → `python assemble.py`；重出 PPT → `python build_pptx.py`。
