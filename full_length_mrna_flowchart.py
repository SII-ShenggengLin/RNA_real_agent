import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.font_manager import FontProperties
import numpy as np

# Use Noto Sans CJK SC for Chinese text
font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_prop = FontProperties(fname=font_path, size=11)
font_prop_bold = FontProperties(fname=font_path, size=11, weight='bold')
font_prop_small = FontProperties(fname=font_path, size=10)
font_prop_title = FontProperties(fname=font_path, size=11, weight='bold')

fig, ax = plt.subplots(figsize=(24, 5.5))
ax.set_xlim(0, 27)
ax.set_ylim(0, 5)
ax.axis('off')

# Define boxes: (x, y, width, height, text_lines, is_title_bold_list)
boxes = [
    (0.5, 1.5, 3.0, 2.0, ["输入：蛋白质序列"], [True]),
    (4.2, 0.8, 4.8, 3.4, [
        "CDS生成与评估",
        "MrnaCdsDesignWorkflow",
        "LinearDesign + RNARL + GEMORNA",
        "评估：MFE / CAI / GC含量"
    ], [True, False, False, False]),
    (9.5, 0.8, 4.5, 3.4, [
        "UTR组合拼接",
        "3×3 UTR组合",
        "(GEMORNA short/medium/long)",
        "full = utr5 + cds + utr3"
    ], [True, False, False, False]),
    (14.7, 0.6, 4.8, 3.8, [
        "增量评估",
        "全长二级结构 (MFE)",
        "5'UTR IRES / 5'UTR MRL",
        "3'UTR稳定性 / RNASTOP",
        "全长稳定性评估"
    ], [True, False, False, False, False]),
    (20.2, 0.8, 4.5, 3.4, [
        "Borda Count排序",
        "cds_component + utr5_mrl",
        "+ utr3_stability",
        "按 total_rank 升序排列"
    ], [True, False, False, False]),
]

# Draw boxes
for x, y, w, h, lines, bold_flags in boxes:
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.05,rounding_size=0.4",
        facecolor='white',
        edgecolor='black',
        linewidth=1.5
    )
    ax.add_patch(box)
    
    n_lines = len(lines)
    line_height = 0.38
    start_y = y + h / 2 + (n_lines - 1) * line_height / 2
    for i, (line, is_bold) in enumerate(zip(lines, bold_flags)):
        fp = font_prop_title if is_bold else font_prop_small
        ax.text(
            x + w / 2,
            start_y - i * line_height,
            line,
            ha='center',
            va='center',
            fontproperties=fp,
            color='black'
        )

# Draw arrows between boxes
for i in range(len(boxes) - 1):
    x1 = boxes[i][0] + boxes[i][2]  # right edge of current box
    y1 = boxes[i][1] + boxes[i][3] / 2  # center y
    x2 = boxes[i + 1][0]  # left edge of next box
    y2 = boxes[i + 1][1] + boxes[i + 1][3] / 2  # center y
    
    arrow = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle='->',
        mutation_scale=20,
        linewidth=1.5,
        color='black'
    )
    ax.add_patch(arrow)

# Output box (on the right)
output_x = 25.0
output_y = 1.7
output_w = 3.0
output_h = 1.6
output_box = FancyBboxPatch(
    (output_x, output_y), output_w, output_h,
    boxstyle="round,pad=0.05,rounding_size=0.4",
    facecolor='white',
    edgecolor='black',
    linewidth=1.5
)
ax.add_patch(output_box)
ax.text(
    output_x + output_w / 2,
    output_y + output_h / 2 + 0.22,
    "排序输出",
    ha='center',
    va='center',
    fontproperties=font_prop_title,
    color='black'
)
ax.text(
    output_x + output_w / 2,
    output_y + output_h / 2 - 0.25,
    "Top-K候选全长mRNA",
    ha='center',
    va='center',
    fontproperties=font_prop_small,
    color='black'
)

# Arrow to output box
arrow_out = FancyArrowPatch(
    (boxes[-1][0] + boxes[-1][2], boxes[-1][1] + boxes[-1][3] / 2),
    (output_x, output_y + output_h / 2),
    arrowstyle='->',
    mutation_scale=20,
    linewidth=1.5,
    color='black'
)
ax.add_patch(arrow_out)

plt.tight_layout()
plt.savefig('full_length_mrna_workflow.png', dpi=200, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
plt.close()
print("Saved to full_length_mrna_workflow.png")
