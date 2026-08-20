# -*- coding: utf-8 -*-
"""组会进展汇报 PPT(2026-08)生成脚本。
风格仿制 PPT/组会报告-林圣庚-260820-智能体进展汇报.pptx:
白底、微软雅黑、28pt 加粗左上标题、圆角矩形+箭头示意、蓝头表格、右下页码。
"""
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

ROOT = Path("/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent")
CROPS = ROOT / "PPT/ppt_build_2608/crops"
OUT = ROOT / "PPT/组会报告-林圣庚-2026年8月-智能体进展汇报.pptx"

FONT = "微软雅黑"
BLACK = RGBColor(0x00, 0x00, 0x00)
GREY = RGBColor(0x59, 0x59, 0x59)
LGREY = RGBColor(0xF2, 0xF2, 0xF2)
BLUE = RGBColor(0x44, 0x72, 0xC4)
LBLUE = RGBColor(0xDE, 0xEB, 0xF7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

PAGE_W, PAGE_H = 13.333, 7.5

prs = Presentation()
prs.slide_width = Emu(12192000)
prs.slide_height = Emu(6858000)
BLANK = prs.slide_layouts[6]


# ---------------------------------------------------------------- helpers ----
def _style_run(run, size=18, bold=False, color=BLACK):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    f.name = FONT
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        rPr.append(ea)
    ea.set("typeface", FONT)


def add_text(slide, x, y, w, h, paras, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             space_after=6, line_spacing=1.12, wrap=True):
    """paras: list of para; para = list of run tuples (text, size, bold, color)
    or a dict {runs:[...], align:..., space_after:..., line_spacing:...}."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.03)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, para in enumerate(paras):
        if isinstance(para, dict):
            runs = para["runs"]
            p_align = para.get("align", align)
            p_sa = para.get("space_after", space_after)
            p_ls = para.get("line_spacing", line_spacing)
        else:
            runs, p_align, p_sa, p_ls = para, align, space_after, line_spacing
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = p_align
        p.space_after = Pt(p_sa)
        p.line_spacing = p_ls
        for text, size, bold, color in runs:
            r = p.add_run()
            r.text = text
            _style_run(r, size, bold, color)
    return tb


def R(text, size=18, bold=False, color=BLACK):
    return (text, size, bold, color)


def add_title(slide, text):
    add_text(slide, 0.4, 0.22, 12.5, 0.75, [[R(text, 28, True)]])


_pageno = [0]
def add_pagenum(slide):
    _pageno[0] += 1
    add_text(slide, 12.55, 7.08, 0.6, 0.35, [[R(str(_pageno[0]), 12, False, GREY)]],
             align=PP_ALIGN.RIGHT)


def add_box(slide, x, y, w, h, paras=None, fill=None, line=BLACK, lw=1.0,
            radius=0.10, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
            space_after=3, line_spacing=1.1, dash=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 Inches(x), Inches(y), Inches(w), Inches(h))
    try:
        shp.adjustments[0] = radius
    except Exception:
        pass
    shp.shadow.inherit = False
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(lw)
        if dash:
            ln = shp.line._get_or_add_ln()
            d = ln.makeelement(qn("a:prstDash"), {"val": dash})
            ln.append(d)
    if paras is not None:
        tf = shp.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = Inches(0.08)
        tf.margin_top = tf.margin_bottom = Inches(0.04)
        for i, para in enumerate(paras):
            if isinstance(para, dict):
                runs = para["runs"]
                p_align = para.get("align", align)
                p_sa = para.get("space_after", space_after)
                p_ls = para.get("line_spacing", line_spacing)
            else:
                runs, p_align, p_sa, p_ls = para, align, space_after, line_spacing
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = p_align
            p.space_after = Pt(p_sa)
            p.line_spacing = p_ls
            for text, size, bold, color in runs:
                r = p.add_run()
                r.text = text
                _style_run(r, size, bold, color)
    return shp


def add_arrow(slide, x1, y1, x2, y2, weight=1.5, color=BLACK):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1),
                                      Inches(y1), Inches(x2), Inches(y2))
    conn.line.color.rgb = color
    conn.line.width = Pt(weight)
    conn.shadow.inherit = False
    ln = conn.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "arrow", "w": "med", "len": "med"})
    ln.append(tail)
    return conn


def add_pic(slide, name, x, y, w=None, h=None):
    path = CROPS / name
    iw, ih = Image.open(path).size
    aspect = iw / ih
    if w is not None and h is None:
        h = w / aspect
    elif h is not None and w is None:
        w = h * aspect
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y),
                                   Inches(w), Inches(h))
    return pic, w, h


def new_slide(title=None):
    slide = prs.slides.add_slide(BLANK)
    if title:
        add_title(slide, title)
    add_pagenum(slide)
    return slide


# ------------------------------------------------------------------ S1 封面 ----
s = new_slide()
add_text(s, 1.67, 2.25, 10.0, 1.1, [[R("RNA 设计智能体:项目进展汇报", 40, False)]],
         align=PP_ALIGN.CENTER)
add_text(s, 1.67, 3.55, 10.0, 0.6,
         [[R("Calibrated Agency × Generation-layer Constraint Navigation", 20, False)]],
         align=PP_ALIGN.CENTER)
add_text(s, 1.67, 4.45, 10.0, 0.5, [[R("2026.8 / 林圣庚", 18, False)]],
         align=PP_ALIGN.CENTER)

# ------------------------------------------------------------------ S2 提纲 ----
s = new_slide("汇报提纲")
outline = [
    ("1", "背景与问题 —— LLM 智能体在科学工作流中的三种失效模式"),
    ("2", "方法一 —— calibrated-agency stack:先画像、再行动、后发言"),
    ("3", "方法二 —— generation-layer constraint navigation:约束导航沉入生成层"),
    ("4", "实验结果 —— 平台基准 / 能力画像 / 双重门控 / GenNav 双臂 / 失败分析"),
]
for i, (num, txt) in enumerate(outline):
    y = 1.75 + i * 1.3
    add_box(s, 0.9, y, 0.62, 0.62, [[R(num, 22, True)]])
    add_text(s, 1.85, y + 0.03, 10.8, 0.62, [[R(txt, 20, False)]],
             anchor=MSO_ANCHOR.MIDDLE)

# ------------------------------------------------------------------ S3 背景 ----
s = new_slide("背景:RNA 设计是多目标问题,依赖一整个工具星座")
add_text(s, 0.5, 1.45, 6.7, 5.3, [
    [R("· RNA 设计(mRNA、siRNA、适配体……)要同时满足表达、稳定性、特异性、结合亲和等多个目标", 18)],
    [R("· 每个目标对应专门工具:序列优化器、结构预测、表达与稳定性模型、脱靶扫描……", 18)],
    [R("· 跨工具、跨管线的串联长期是专家手工活,每个靶点动辄数天", 18)],
    [R("· 本平台已整合成七层工具栈(右图):", 18),
     R("54 个工具 · 22 个本地微服务 · 11 个领域工作流", 18, True)],
    [R("· LLM 智能体可以把这整套工具自动编排起来 —— 问题是:", 18),
     R("它什么时候可信?", 18, True, BLUE)],
], space_after=16, line_spacing=1.18)
_, w, h = add_pic(s, "f1_arch.png", 8.75, 1.2, h=5.75)
add_text(s, 7.35, 7.0, 5.85, 0.4,
         [[R("七层架构(L0 工具层 → L6 入口);L4 紫色框为 calibrated stack", 12, False, GREY)]],
         align=PP_ALIGN.CENTER)

# ------------------------------------------------------------------ S4 问题 ----
s = new_slide("问题:LLM 智能体存在三种可测量的失效模式")
add_text(s, 0.4, 1.12, 12.5, 0.5,
         [[R("文献调研与我们的前期实验(E1 / E3 / P0)共同指出:", 16, False, GREY)]])
fail_modes = [
    ("① 未校准的工具信任", "uncalibrated tool trust",
     "把预测模型的输出按面值采信,从不验证它对当前任务、当前靶点族是否有已证明的能力",
     "实测:3 个结构 oracle × 6 个靶点,screening 0/18 格通过;亲和力排序方向反转(E1 / P2)"),
    ("② 声明越界", "claim overreach",
     "自然语言叙述会漂移出证据支持的范围,且事后难以审计",
     "实测:未门控的智能体虚假声明率 57.9%(E3)"),
    ("③ 被混淆的“改进”", "confounded improvement",
     "agentic 策略常伴随更多采样 —— 表观收益可能只是预算差异,而非机制增益",
     "实测:预算匹配后,“协调效应”δ 0.457 → 0.278,塌缩且不显著(P0)"),
]
for i, (head, en, body, evi) in enumerate(fail_modes):
    x = 0.35 + i * 4.29
    add_box(s, x, 1.75, 4.05, 3.55, [
        [R(head, 19, True)],
        [R(en, 13, False, GREY)],
        [R(body, 14)],
        [R(evi, 13, False, BLUE)],
    ], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space_after=8)
add_box(s, 1.2, 5.8, 10.9, 0.85,
        [[R("共同根源:没有实证的自我能力模型,也没有预算控制 —— 必须先测量、再约束", 18, True)]],
        fill=LGREY, line=None)

# ------------------------------------------------------------------ S5 核心思想 ----
s = new_slide("核心思想:先测量、再约束 —— 可信智能体的智能在证据基础设施")
add_box(s, 0.9, 1.3, 11.5, 0.95,
        [[R("LLM 只编排、不设计:每个分子都来自已验证的生成器,每个声明都可追溯到确定性工具调用", 17, True)]],
        fill=LBLUE, line=None)
add_arrow(s, 3.55, 2.25, 3.55, 2.62)
add_arrow(s, 9.75, 2.25, 9.75, 2.62)
add_box(s, 0.6, 2.65, 5.85, 3.25, [
    [R("方法一 | calibrated-agency stack", 18, True)],
    [R("回答“信不信” —— 认识论治理", 14, False, GREY)],
    [R("· oracle 能力用外部锚点集实测画像,分等级注册(verified / failed / unprofiled)", 14)],
    [R("· 规划、动作、发言由确定性门约束(DecisionGate / ClaimGate)", 14)],
    [R("· 全程 append-only 审计,LLM 评审仅 advisory", 14)],
], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space_after=7)
add_box(s, 6.9, 2.65, 5.85, 3.25, [
    [R("方法二 | GenNav 生成层约束导航", 18, True)],
    [R("回答“做什么” —— 生成策略", 14, False, GREY)],
    [R("· 在可信边界内,按预注册的约束矩阵组织生成", 14)],
    [R("· 可行性探针 + 画像正交轴 + 定向补强,逐画像批量交付", 14)],
    [R("· 与规则基线同预算对比(预算匹配铁律)", 14)],
], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space_after=7)
add_box(s, 0.9, 6.2, 11.5, 0.8,
        [[R("贯穿铁律:一切比较先预注册、再预算匹配;阴性结果同样注册", 16, True)]],
        fill=LGREY, line=None)

# ------------------------------------------------------- S6 方法一示意图 ----
s = new_slide("方法一:calibrated-agency stack —— 先画像、再行动、后发言")
add_text(s, 0.4, 1.1, 12.5, 0.45,
         [[R("持久维护一张实证的自我模型:每个 oracle 对什么任务、什么靶点族,有哪项能力、什么等级", 15, False, GREY)]])
# top flow: anchors -> profiler -> selfmodel -> gates
add_box(s, 0.45, 1.7, 2.9, 1.85, [
    [R("外部锚点集", 16, True)],
    [R("带实测标签的分子:Kd 亲和力、MRL 表达、天然 pose……", 12.5)],
], space_after=4)
add_arrow(s, 3.35, 2.62, 3.62, 2.62)
add_box(s, 3.62, 1.7, 2.9, 1.85, [
    [R("CapabilityProfiler", 16, True)],
    [R("能力画像", 16, True)],
    [R("预注册门:AUROC > 0.8、ρ ≥ 0.6、top-1 ≥ 2/3", 12.5)],
], space_after=4)
add_arrow(s, 6.52, 2.62, 6.79, 2.62)
add_box(s, 6.79, 1.7, 2.9, 1.85, [
    [R("SelfModel", 16, True)],
    [R("实证自我模型", 16, True)],
    [R("(oracle × 任务 × 靶族)→ verified / failed / unprofiled", 12.5)],
], space_after=4)
add_arrow(s, 9.69, 2.3, 9.95, 2.05)
add_arrow(s, 9.69, 2.95, 9.95, 3.2)
add_box(s, 9.95, 1.3, 2.95, 1.5, [
    [R("DecisionGate 决策门", 15, True)],
    [R("行动前:allow / substitute / downgrade / reject / require_profiling", 12)],
], space_after=4)
add_box(s, 9.95, 2.95, 2.95, 1.5, [
    [R("ClaimGate 发言门", 15, True)],
    [R("写入前:absolute → 靶内相对 → 仅趋势 → 禁言", 12)],
], space_after=4)
# campaign strip
add_text(s, 0.45, 4.35, 12.4, 0.4,
         [[R("一次战役(campaign)的七步流程", 14, True, GREY)]])
steps = ["查询\nSelfModel", "声明能力\n依赖", "按需画像", "门控裁剪\n动作空间",
         "执行 + 漂移\n监控", "逐条校验\n发言", "归档入库"]
bw, gap, y0 = 1.66, 0.13, 4.8
for i, st in enumerate(steps):
    x = 0.45 + i * (bw + gap)
    lines = st.split("\n")
    add_box(s, x, y0, bw, 0.95,
            [[R(t, 12.5, i in (2, 3, 5))] for t in lines], space_after=1)
    if i < len(steps) - 1:
        add_arrow(s, x + bw, y0 + 0.475, x + bw + gap, y0 + 0.475, weight=1.2)
add_box(s, 0.45, 6.15, 12.4, 0.8,
        [[R("AuditTrail:append-only 审计日志记录每一次画像、门裁决与发言降级 —— 门内无 LLM,“零越级”是硬保证", 14.5, True)]],
        fill=LGREY, line=None)

# ------------------------------------------------------- S7 方法二示意图 ----
s = new_slide("方法二:GenNav —— generation-layer constraint navigation")
add_box(s, 0.45, 1.25, 12.4, 1.0, [
    [R("起点:选择层导航已被证伪(E5)", 14.5, True),
     R(" —— 固定候选池 + 生成后过滤:λ 档趋同(批内编辑距离 0.82% < 2% 门)、可行档覆盖不足(GFP 池 0/315),残余失败全部是生成层结构性问题", 13.5)],
], align=PP_ALIGN.LEFT, line=GREY, lw=1.0, dash="dash")
add_arrow(s, 6.65, 2.25, 6.65, 2.62)
gennav_steps = [
    ("① 可行性探针", "先在生成器档位格上探测哪些档可行;无档可行 → 显式声明降级,不静默弱交付"),
    ("② 画像正交轴", "cai_max / frac / cai_floor 三轴 ⇄ expression / balanced / stability,按构造保证画像可分"),
    ("③ 预算分配 + 定向补强", "缺口带保证轮修复 —— 确定性分配,全程仅 1 次 LLM 调用(E14)"),
    ("④ 约束矩阵交付", "逐画像批量交付(每画像 5 条),强制批内多样度 D1 ≥ 门限"),
]
bw2, gap2, y2 = 2.95, 0.22, 2.7
for i, (head, body) in enumerate(gennav_steps):
    x = 0.45 + i * (bw2 + gap2)
    add_box(s, x, y2, bw2, 2.1, [
        [R(head, 15.5, True)],
        [R(body, 12.5)],
    ], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space_after=6)
    if i < 3:
        add_arrow(s, x + bw2, y2 + 1.05, x + bw2 + gap2, y2 + 1.05, weight=1.5)
add_box(s, 0.45, 5.25, 12.4, 0.85, [
    [R("生成上下文显式解析:mRNA = 物种匹配密码子表;适配体 = 长度带 × 种子档位;一切对比与规则网格同预算", 14)],
], fill=LGREY, line=None)
add_text(s, 0.45, 6.3, 12.4, 0.8, [
    [R("价值域:导航在“生成层使交付变难”的地方挣得超越单工具的价值 —— mRNA 的密码子权衡、适配体的稀缺带分配", 14, False, GREY)],
])

# ------------------------------------------------------------- S8 结果总览 ----
s = new_slide("实验结果总览:全部结论由预注册实验支撑")
rows = [
    ("结果", "实验", "关键数字"),
    ("一 · 平台基准", "Fig 2", "210/210 任务全部成功;设计臂 CAI 中位 0.745 > 野生型 0.729 > 随机同义 0.672"),
    ("二 · 能力画像", "E1 / E7", "适配体侧 0/18 格否决;mRNA 侧 3/3 族认证(AUROC 0.990 – 1.000)"),
    ("三 · 双重门控", "E3 / E3-M", "虚假声明率 57.9% → 0%、38.9% → 8.3%;真阳性保留 ≥ 100%"),
    ("四 · GenNav·mRNA", "E6", "逐画像交付不一致对 30:0,McNemar P = 1.9e-09"),
    ("五 · GenNav·适配体", "E8→E14", "三次机制迭代后 14:3,P = 0.0127,主终点 GO"),
    ("六 · 失败与阴性结果", "Fig 6 等", "约 1400 次运行,35 个终态失败全为确定性边界;测试基线 668 passed"),
]
tbl_shape = s.shapes.add_table(7, 3, Inches(0.7), Inches(1.5),
                               Inches(11.9), Inches(5.0))
tbl = tbl_shape.table
tbl.columns[0].width = Inches(2.7)
tbl.columns[1].width = Inches(1.9)
tbl.columns[2].width = Inches(7.3)
for i, row in enumerate(rows):
    for j, txt in enumerate(row):
        cell = tbl.cell(i, j)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.08)
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if j == 2 else PP_ALIGN.CENTER
        r = p.add_run()
        r.text = txt
        _style_run(r, 15 if i == 0 else 14, i == 0, BLACK)

# ------------------------------------------------------------- S9 结果一 ----
s = new_slide("结果一:平台 210 项基准任务全部成功,产出生物学有效")
add_pic(s, "f2_coverage.png", 0.35, 1.45, w=4.55)
add_text(s, 0.35, 5.0, 4.55, 0.9,
         [[R("11 个工作流 × 210 项任务全部成功(含旧治理遗留任务复跑)", 13, False, GREY)]])
add_pic(s, "f2_cai.png", 5.15, 1.45, w=3.9)
add_text(s, 5.15, 5.0, 3.9, 1.1,
         [[R("设计臂 CAI 中位 0.745 > 野生型 0.729 > 随机同义 0.672(P = 4.0e-07)", 13, False, GREY)]])
add_pic(s, "f2_sirna.png", 9.35, 1.45, w=3.35)
add_text(s, 9.35, 5.0, 3.35, 1.1,
         [[R("siRNA 面板 21/22 零脱靶(Bowtie2 全转录组扫描)", 13, False, GREY)]])
add_text(s, 0.35, 6.25, 12.6, 0.8,
         [[R("更多面板:二级结构反向折叠 exact match 22/25 · 三级结构 pLDDT 分量中位 0.704 · IRES AUROC 0.762 —— 详见论文 Fig 2", 14)]])

# ------------------------------------------------------------- S10 结果二 ----
s = new_slide("结果二:能力画像是双面仪器 —— 能否决、能认证、还能抓出静默退化")
add_pic(s, "f3_screening.png", 0.3, 1.4, w=4.35)
add_text(s, 0.3, 5.0, 4.5, 1.35, [
    [R("否决(E1,适配体侧):", 13, True),
     R("3 个结构 oracle × 6 个靶点,screening 0/18 格通过、ranking 无一达 ρ ≥ 0.6 → 注册 failed,排序类动作被 DecisionGate 拒绝", 13, False, GREY)],
])
add_pic(s, "f3_mrna.png", 5.0, 1.4, w=7.6)
add_text(s, 5.0, 5.0, 7.6, 1.35, [
    [R("认证(E7,mRNA 侧):", 13, True),
     R("GEMORNA 5'UTR MRL oracle 在 3/3 个锚点族全部 verified(AUROC 0.990 / 1.000 / 1.000;706 个实测 MRL 锚点);3'UTR 稳定性预测器无锚点集 → 注册 unprofiled,门控关闭", 13, False, GREY)],
])
add_box(s, 0.3, 6.15, 12.3, 0.85, [
    [R("画像还抓出部署中的静默退化:RNAsmol 预处理不忠实上游,AUROC 仅 0.786 / 0.410;逐字移植官方预处理后精确复现 0.9744 / 0.9828(分布外短适配体仍无能力,如实注册)", 13.5)],
], fill=LGREY, line=None)

# ------------------------------------------------------------- S11 结果三 ----
s = new_slide("结果三:双重门控把虚假声明率从 57.9% 降到 0,真阳性一个不漏")
add_pic(s, "f4_whole.png", 1.0, 1.3, w=11.3)
add_text(s, 0.6, 6.42, 12.1, 0.9, [
    [R("左:预算匹配后效应塌缩(P0);中:四步自审计退役两条历史头条 claim(E2);右:双门治理(E3)", 13.5)],
    [R("E3 合成审计:虚假声明率 57.9% → 0%,真阳性 8 → 9,越级 23 → 0;E3-M 真实 mRNA 任务:38.9% → 8.3%,真阳性保留 100%", 13.5, True)],
])

# ------------------------------------------------------------- S12 结果四 ----
s = new_slide("结果四(GenNav · mRNA):生成层导航 30:0 完胜规则基线")
add_pic(s, "f5_e5.png", 0.3, 1.35, w=4.6)
add_text(s, 0.3, 4.15, 4.6, 1.3, [
    [R("病因诊断(E5):", 13, True),
     R("选择层的残余失败全部是生成层结构性问题(λ 档趋同、可行档不足)—— 由此提出 GenNav", 13, False, GREY)],
])
add_pic(s, "ppt_e6_grid.png", 5.1, 1.35, w=7.9)
add_text(s, 5.1, 5.05, 7.9, 0.9, [
    [R("E6 主终点:", 13, True),
     R("18 靶 × 3 画像逐画像交付,不一致对 30:0;框出的 HER2 零可行档 → 显式声明降级", 13, False, GREY)],
])
chips = ["McNemar P = 1.9e-09", "基因级 e2e = 1.0(18/18)",
         "LLM 均值 2.4 次/基因(预算 5–9)"]
for i, c in enumerate(chips):
    add_box(s, 0.3 + i * 4.28, 5.95, 4.03, 0.85,
            [[R(c, 15, True, BLUE)]], fill=WHITE, line=BLUE, lw=1.2)

# ------------------------------------------------------------- S13 结果五 ----
s = new_slide("结果五(GenNav · 适配体):三次机制迭代攻克交付稀缺面板")
timeline = [
    ("E8", "3:1 NS", "机制迁移成立"),
    ("E9", "6:8 NS", "稀缺矩阵"),
    ("E10", "9:4 NS", "分配机械化"),
    ("E12", "9:2 P=0.065", "格增密 + 实测先验"),
    ("E14", "14:3 P=0.0127", "保证轮分配 → GO"),
]
tw, tgap, ty = 2.25, 0.25, 1.3
for i, (name, stat, lever) in enumerate(timeline):
    x = 0.35 + i * (tw + tgap)
    last = i == len(timeline) - 1
    add_box(s, x, ty, tw, 1.45, [
        [R(name, 16, True)],
        [R(stat, 13, True, BLUE if last else BLACK)],
        [R(lever, 11.5, False, GREY)],
    ], fill=LBLUE if last else None, line=BLUE if last else BLACK,
        lw=1.5 if last else 1.0, space_after=2)
    if i < 4:
        add_arrow(s, x + tw, ty + 0.72, x + tw + tgap, ty + 0.72, weight=1.5)
add_pic(s, "ppt_e14_grid.png", 1.55, 3.0, w=10.2)
add_text(s, 0.6, 6.82, 12.1, 0.5, [
    [R("E15 确认性复跑(全新稀缺靶点):优势特异于交付稀缺面板 —— 合并 28:9,P = 0.0026;边界如实披露", 13, False, GREY)],
])

# ------------------------------------------------------------- S14 结果六 ----
s = new_slide("结果六:约 1400 次运行的失败全部可解释,阴性结果如实注册")
add_pic(s, "f6_fail.png", 0.3, 1.45, w=7.7)
add_text(s, 0.3, 4.8, 7.7, 1.0, [
    [R("214 个暂态事件全部自动恢复;35 个终态失败全部是确定性边界(ODesign 零输出 24 · 端点错配 8 · 内存边界 2 · 旧治理 abort 1)", 13, False, GREY)],
])
add_box(s, 8.25, 1.45, 4.75, 4.15, [
    [R("阴性结果同样注册", 16, True)],
    [R("· Junction 修复三连 NO-GO(“没有免费午餐”);ddG 指标本身验证 r = 0.945,转为仅报告", 12.5)],
    [R("· E4 跨战役记忆:省 74.2% 预算但无学习收益 → 方向放弃", 12.5)],
    [R("· BMC “协调增益”叙事被 P0 / P3 证伪 → 重新定位为可审计的有界预算分配", 12.5)],
    [R("· E15:GenNav 优势限于稀缺面板", 12.5)],
], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space_after=8)
add_box(s, 0.3, 6.05, 12.7, 0.85, [
    [R("工程与质量基线:LinearDesign 内存守卫(100 GiB 帽 + 1800 aa 前置拒绝)· 约 30 项接口全部锁定 · 测试 668 passed · PA 回归 19/19", 14)],
], fill=LGREY, line=None)

# ------------------------------------------------------------- S15 总结 ----
s = new_slide("总结:先测量、再约束、如实报告")
summary = [
    ("两个方法", "calibrated-agency stack:实证自我模型 + 双门,claim 越级硬保证为零\nGenNav:生成层多约束批量交付 —— mRNA 30:0、适配体 14:3"),
    ("一套治理", "预注册 · 预算匹配 · LLM 仅 advisory · 接口锁定 · 全链路审计;阴性结果同样注册"),
    ("下一步", "论文稿 v3 已完成(目标 Nature Methods);补 3'UTR 稳定性锚点集画像;扩展更多靶族的确认性战役"),
]
for i, (chip, body) in enumerate(summary):
    y = 1.55 + i * 1.8
    add_box(s, 0.7, y, 2.2, 1.4, [[R(chip, 19, True)]])
    paras = [[R(line, 16)] for line in body.split("\n")]
    add_text(s, 3.25, y, 9.4, 1.4, paras, anchor=MSO_ANCHOR.MIDDLE,
             space_after=8)

# ------------------------------------------------------------- S16 致谢 ----
s = new_slide()
add_text(s, 1.67, 3.1, 10.0, 1.2, [[R("谢谢大家  敬请批评指正", 36, False)]],
         align=PP_ALIGN.CENTER)

prs.save(str(OUT))
print("saved:", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
