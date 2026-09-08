# 顶刊智能体系统论文 Fig 1（系统示意图）设计模式总结

> 来源：对 7 篇 Nature/Science/Nature 子刊智能体系统论文主系统图的逐面板研读
> （Robin·Nature 2025；Co-Scientist·Nature；DeepRare·Nature；ERA·Nature；Biomni·Science 2026；
> BioMedAgent·Nat. Biomed. Eng. 2026；in silico team science·Nat. Biotechnol. Perspective）。
> 用途：指导 RNADesignAgent 论文 Fig 1 的绘制。渲染底稿留存于 `/tmp/figref/`。

## 1. 共同骨架：一张 Fig 1 讲完整个系统

- 7 篇论文都把**全部架构表达预算押在 Fig 1 一张图上**（占第 2 页整栏），后续图全是结果图。
- 统一采用 **2–3 层"变焦"结构**（zoom-in），而非一张图塞平所有细节：
  - 顶层 = 黑盒 I/O 视图：输入在左、系统在中间、输出在右（Robin-a、CoSci-a、DeepRare-a、BioMedAgent 顶层概览条）；
  - 中层 = 内部流程/架构展开：分层色带或泳道（DeepRare 三条 pastel 色带 = Central host / Agent servers / External sources；BioMedAgent 的 Planning→Coding→Execution 泳道）；
  - 底层 = 组件名片或证据：agent 职责卡（Robin-c、teamscience-b 的能力 chip 矩阵）、真实执行 trace（Biomni-C）、或验证案例三件套"目标原文→系统输出→小结果图"（CoSci-c）。
- 常用构图手法：**顶层黑盒 + 一根对角虚线向下引出展开图**（BioMedAgent），10 秒速读版与细节版共存。

## 2. 面板组织与图-文对应

- 面板用**粗体小写字母 a/b/c** 标注于左上角；caption 按面板逐段写，逐个点名组件——caption 本身就是方法章节的索引。
- 图例尽量**写进 caption 而非图面**（Co-Scientist 最典型："red boxes = agents, blue = human inputs, dark grey arrows = information flow"），图面最多放两行小组图例。
- 每个组件框内带 1–3 行"人话"说明，图可脱离正文自读；但**单个元素标签 ≤5 词**，长文本只允许出现在"真实示例"区域。
- 面板与论文贡献点一一对应（CoSci-c 三行案例 ↔ 三个验证章节）。机制详图放 Extended Data，主图保持克制。

## 3. 视觉编码规则（硬规则，全图一致）

| 编码通道 | 约定 |
|---|---|
| 形状 | 大圆角容器 = 系统/阶段边界（DeepRare 用虚线圆角容器）；胶囊/圆角矩形 = 组件；**堆叠多重描边 = 可迭代过程**（Robin）；堆叠重复条 = 可并行资源池（CoSci worker 池） |
| 颜色 | **颜色 = 组件角色，全图固定且跨面板一致**（DeepRare 色带色在 a/b 两面板复用互指；Robin-c 的 agent 颜色 = b 的列颜色）。主色 ≤5 种，低饱和 pastel/莫兰迪，白底黑字细描边 |
| 强调色 | **全局唯一**：DeepRare 全图只有自家系统是红色；ERA 全图只有最优解有星。强调色只给论文最核心的贡献点 |
| 箭头（语义分级） | 粗实线 = 主数据流；细双向 = 层间交互/调用；**虚线 = 反馈/回退回路**；红/绿虚线 = 失败/成功控制流（BioMedAgent）；**迭代循环用专属符号单独表达**（大括号、顶部环形箭头），不混在数据流里 |
| 图标 | 承担类别语义：人形 = 用户，机器人 = LLM agent，数据库 = 记忆/存储，齿轮 = 编排；文字随之压到 1–3 词 |
| 边界 | 人机边界、干湿边界显式画出：Robin 用中央竖置色柱做分界墙；CoSci 把人形图标放图外左侧、专色标"人在回路" |

## 4. 文字与配色纪律

- 字号三级：面板/区块标题（加粗）> 组件名（粗体感）> 说明文字；Nature 印版正文文字 5–7 pt、面板字母 8 pt 粗体（Helvetica/Arial）。
- 配色：低饱和粉彩 + 纯白背景 + 纯黑文字 + 细描边；无渐变、无阴影。与本项目 palette rev 7（12 色 Morandi）天然兼容。
- **用真实 artifacts 代替抽象占位符**：真实输入 prompt、真实 ranked 输出列表、真实工具名、真实代码/trace 片段（7 篇无一例外）——这是 agent 系统论文建立可信度的通用手法。
- **数字徽章做钩子**：Biomni 的 "105 softwares / 150 tools / 59 databases" 小色块横排，醒目且零版面成本。

## 5. 对我们 Fig 1 的操作性结论

1. 骨架 = 「a 端到端循环+七层脊柱 → b L4 多智能体层 → d CapGate 环 → e GenNav 环」，侧栏 c 放数字徽章+审计组成（对应 Biomni 徽章），底部 f 放 RNADesign-210 组成旭日图——与 `docs/FIGURE_PLAN_V5.md` 的 6 面板规划一致。
2. 语义配色固定：**陶土色 = CapGate 治理（全图唯一强调色，虚线陶土箭头 = 门控/阻断）**，板岩灰实线 = 数据流，紫灰 = 工作流，灰蓝 = 工具/服务，藕紫 = LLM 智能体，暖黄 = 用户侧，灰绿 = 产出。
3. 迭代与 advisory 关系一律用虚线回环表达（QualityAgent 建议回路、GenNav probe→reinforce 环），主链绝不画回头实线。
4. 输入框放真实任务文本、输出框放真实 ranked 候选 + 审计条目示例；c/f 面板用真实数字（41/21/11/210、11,003 事件）。
5. 治理介入点直接编码进流程节点颜色（DeepRare ED-Fig1c 的"节点颜色=执行层"手法），让"我们的差异化=治理"在图面上自证。
