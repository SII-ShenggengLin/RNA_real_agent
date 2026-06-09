# 图 2.1 子图绘制提示词模板

> **依据文档**: `rna_agent_system/docs/MANUSCRIPT.md` §Results 2.1  
> **Figure 2.1 整体布局**: 3 × 3 网格 (9 panels a–i)。其中 **(a)(b)(h) 为概念图/静态图**，不需要 benchmark 实验结果；**以下模板只包含需要实验数据的 6 个子图**。

---

## 一、项目背景与数据来源

- **项目根目录**: `/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system`
- **实验结果目录**: `experiments/results/platform_coverage_by_workflow/{workflow_name}/`
- **每个 workflow 包含**:
  - `raw/platform_coverage_{workflow_name}.jsonl` —— 逐条任务原始结果
  - `summary/summary_{workflow_name}.json` —— 该 workflow 汇总统计
- **已完成的 11 个 workflow**:
  - `mrna_cds_design` (19 tasks)
  - `full_length_mrna_design` (22 tasks)
  - `mrna_sequence_scoring` (13 tasks)
  - `sirna_design` (22 tasks)
  - `sgrna_design` (30 tasks)
  - `rna_secondary_structure_design` (25 tasks)
  - `rna_tertiary_structure_design` (18 tasks)
  - `rna_aptamer_design` (18 tasks)
  - `rna_small_molecule_interaction` (15 tasks)
  - `aso_target_screening` (14 tasks)
  - `ires_prediction` (12 tasks)

**Workflow 生物学分组（用于配色统一）**：

| 分组 | 颜色主题 | Workflows |
|------|---------|-----------|
| **mRNA Therapeutics Development** | 绿色系 | `mrna_cds_design`, `full_length_mrna_design`, `mrna_sequence_scoring` |
| **Gene Silencing & Editing** | 蓝色系 | `sirna_design`, `sgrna_design`, `aso_target_screening` |
| **RNA Structural Engineering** | 粉色系 | `rna_secondary_structure_design`, `rna_tertiary_structure_design` |
| **Functional RNA Discovery** | 黄色/暖色系 | `rna_aptamer_design`, `rna_small_molecule_interaction`, `ires_prediction` |

---

## 二、绘图规范（必须严格遵守）

### 2.1 代码生成原则
- **图必须由 Python 代码生成**，严禁使用 AI 直接生成图片。
- 使用 `matplotlib` + `seaborn` 绘制，可配合 `pandas` / `numpy` 处理数据。
- 代码必须可复现：固定 `figsize`、`dpi`、随机种子。

### 2.2 配色风格 —— 莫兰迪色系
- 全局使用低饱和度、柔和统一的莫兰迪配色。
- **推荐主色板**:
  ```python
  MORANDI_COLORS = [
      "#8B9DAF",  # 灰蓝 (Gene Silencing & Editing)
      "#B5C4B1",  # 薄荷绿 (mRNA Therapeutics Development)
      "#D4C4B7",  # 奶茶色
      "#C9B8A8",  # 暖灰
      "#A8B5A0",  # 灰绿
      "#D8A7A7",  # 灰粉 (RNA Structural Engineering)
      "#A7B8D8",  # 淡紫蓝
      "#C4B7D8",  # 淡紫
      "#D8C4A7",  # 驼色 (Functional RNA Discovery)
      "#A0A0A0",  # 中灰
      "#B8D4C8",  # 青灰
  ]
  ```
- **Category 分级色**（用于 basic / full / edge 等）:
  - basic → 浅色 (`#D4C4B7`)
  - edge → 中色 (`#C9B8A8`)
  - full / therapeutic / reporter → 深色 (`#8B9DAF`)
- **Trace Completeness 专用色**:
  - Complete → `#7A9E7E` (深绿)
  - Partial → `#B5C4B1` (浅绿)
  - None → `#B5B5B5` (灰)
- **Error / Failure 专用色**:
  - success → `#7A9E7E` (深绿)
  - service_unavailable → `#C9B8A8` (暖沙)
  - timeout → `#D8A7A7` (灰粉)
  - input_error → `#A7B8D8` (淡蓝)
  - validation_error → `#D8C4A7` (驼色)
- 背景色: `"#FAFAFA"`，网格线: `"#E0E0E0"`，避免鲜艳红/绿/蓝。

### 2.3 字体与排版
- 中文: `"SimHei"` / `"Microsoft YaHei"`；英文: `"DejaVu Sans"`。
- Title: 14–16 pt, axis label: 11–12 pt, tick: 9–10 pt, legend: 9–10 pt。

### 2.4 输出规范
- 保存路径: `experiments/results/plots/figure_2_1/`
- 文件名: `fig2_1_{c,d,e,f,g,i}.png`（对应论文 panel 字母）
- 分辨率: `dpi=300`
- 去除白边: `bbox_inches='tight', pad_inches=0.1`
- 单栏图: `figsize=(6, 4.5)` 或 `(7, 5)`；双栏/宽图: `(10, 5)` 或 `(12, 6)`。

### 2.5 代码结构模板

```python
#!/usr/bin/env python3
"""
Figure 2.1 — Panel [X]: [描述]
Data source: RNA-BioBench-Platform benchmark results
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# ───────────────────────────────────────────────
# 莫兰迪色板 & 全局样式
# ───────────────────────────────────────────────
MORANDI_COLORS = [
    "#8B9DAF", "#B5C4B1", "#D4C4B7", "#C9B8A8", "#A8B5A0",
    "#D8A7A7", "#A7B8D8", "#C4B7D8", "#D8C4A7", "#A0A0A0",
    "#B8D4C8",
]

plt.rcParams.update({
    "figure.facecolor": "#FAFAFA",
    "axes.facecolor": "#FAFAFA",
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#333333",
    "text.color": "#333333",
    "xtick.color": "#555555",
    "ytick.color": "#555555",
    "grid.color": "#E0E0E0",
    "grid.linewidth": 0.8,
    "axes.grid": True,
    "axes.axisbelow": True,
    "legend.frameon": True,
    "legend.facecolor": "#FAFAFA",
    "legend.edgecolor": "#CCCCCC",
    "font.size": 10,
    "axes.titlesize": 14,
    "axes.labelsize": 11,
})

# ───────────────────────────────────────────────
# 数据加载辅助函数
# ───────────────────────────────────────────────
BASE_DIR = Path(
    "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent"
    "/rna_agent_system/experiments/results/platform_coverage_by_workflow"
)

WORKFLOWS = [
    "mrna_cds_design", "full_length_mrna_design", "mrna_sequence_scoring",
    "sirna_design", "sgrna_design", "aso_target_screening",
    "rna_secondary_structure_design", "rna_tertiary_structure_design",
    "rna_aptamer_design", "rna_small_molecule_interaction", "ires_prediction",
]

# 生物学分组映射（用于统一配色）
GROUP_MAP = {
    "mrna_cds_design": "mRNA Therapeutics Development",
    "full_length_mrna_design": "mRNA Therapeutics Development",
    "mrna_sequence_scoring": "mRNA Therapeutics Development",
    "sirna_design": "Gene Silencing & Editing",
    "sgrna_design": "Gene Silencing & Editing",
    "aso_target_screening": "Gene Silencing & Editing",
    "rna_secondary_structure_design": "RNA Structural Engineering",
    "rna_tertiary_structure_design": "RNA Structural Engineering",
    "rna_aptamer_design": "Functional RNA Discovery",
    "rna_small_molecule_interaction": "Functional RNA Discovery",
    "ires_prediction": "Functional RNA Discovery",
}

GROUP_COLORS = {
    "mRNA Therapeutics Development": "#B5C4B1",
    "Gene Silencing & Editing": "#8B9DAF",
    "RNA Structural Engineering": "#D8A7A7",
    "Functional RNA Discovery": "#D8C4A7",
}


def load_summary(workflow: str) -> dict:
    path = BASE_DIR / workflow / "summary" / f"summary_{workflow}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_raw_records(workflow: str) -> list[dict]:
    path = BASE_DIR / workflow / "raw" / f"platform_coverage_{workflow}.jsonl"
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_all_records() -> pd.DataFrame:
    """Load all raw records from all workflows into a single DataFrame."""
    rows = []
    for wf in WORKFLOWS:
        for rec in load_raw_records(wf):
            rec["workflow"] = wf
            rec["group"] = GROUP_MAP.get(wf, "Other")
            rows.append(rec)
    return pd.DataFrame(rows)


# ───────────────────────────────────────────────
# 绘图代码（在此处编写具体 panel 逻辑）
# ───────────────────────────────────────────────

def main():
    out_dir = Path(
        "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent"
        "/rna_agent_system/experiments/results/plots/figure_2_1"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # TODO: 在此处编写具体 Panel 的绘图逻辑

    plt.savefig(
        out_dir / "fig2_1_X.png",
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.1,
    )
    print(f"Saved to {out_dir / 'fig2_1_X.png'}")


if __name__ == "__main__":
    main()
```

---

## 三、需要实验数据的 6 个子图（对应 MANUSCRIPT.md）

### Panel (c): Task Success Rate per Workflow

**来源**: MANUSCRIPT.md §Panel c

**图表类型**: 分组条形图 (grouped bar chart)

**数据需求**:
- 横轴：11 个 workflows（按 4 个生物学分组着色）
- 纵轴：Task Success Rate (%)
- 分组：Complexity Level — *Level-1: Basic* (light), *Level-2: Intermediate* (medium), *Level-3: Complex* (dark)
- 柱顶或图注标注 `n=`（该 category 的任务数）

**关键说明**:
- 从各 workflow 的 `category_breakdown` 提取每个 category 的 `success_rate`
- 并非所有 workflow 都包含 full/edge category，缺失的不画柱
- 如果 accuracy 不是百分比而是小数，转换为 `%`

**视觉要求**:
- 使用莫兰迪分级色表示 Level-1: Basic / Level-2: Intermediate / Level-3: Complex
- 横轴 workflow 名称可旋转 30° 防重叠
- 添加图例

---

### Panel (d): Tool Correctness heatmap

**来源**: MANUSCRIPT.md §Panel d

**图表类型**: 热力图 (heatmap matrix)

**数据需求**:
- 横轴：11 个 workflows
- 纵轴：所有 `expected_tool_chain` 中出现过的 tools 的并集（去重后约 15 个高频工具）
- 色值：Tool Correctness ratio（0 = white/pale yellow, 1 = deep red）

**计算方法**:
- 读取每个 workflow 的 raw jsonl
- 对每个 (workflow, tool) 组合：统计 `tool_correctness=True` 且该 tool 在 `expected_tools` 中的任务数 / 该 tool 被期望的任务总数
- 如果某 workflow 不期望某 tool，则该 cell 为 NaN（显示为白色/浅灰）

**视觉要求**:
- 使用深红色渐变（非默认红黄绿）
- 添加 colorbar，标注 "Tool Correctness Ratio"
- 纵轴 tool 名称可适当缩写

---

### Panel (e): Trace Completeness and execution observability

**来源**: MANUSCRIPT.md §Panel e

**图表类型**: 水平堆叠条形图 (stacked horizontal bar chart)

**数据需求**:
- 读取所有 workflow 的 raw jsonl，统计每个 workflow 的 `trace_completeness`:
  - `complete`：深绿
  - `partial`：浅绿
  - `none`：灰色

**视觉要求**:
- 每个 workflow 一行，11 行
- 使用专用色：Complete `#7A9E7E` / Partial `#B5C4B1` / None `#B5B5B5`
- 右侧或柱内标注百分比
- 可添加总任务数标注

**注意**: 已有历史脚本参考 `experiments/results/figures/figure_2_1_panel_e.png`。

---

### Panel (f): Benchmark coverage and task diversity

**来源**: MANUSCRIPT.md §Panel f

**图表类型**: 主图 = 堆叠条形图；插图 = 饼图/环形图 (inset pie/donut)

**主图数据**:
- 横轴：11 个 workflows
- 纵轴：任务数量
- 堆叠：各 category（basic / edge / full / therapeutic / reporter / vaccine / boundary / comparison 等）

**插图数据** (右上角 inset):
- 全平台 216 个任务的整体 category 分布饼图

**视觉要求**:
- 主图使用莫兰迪渐变色堆叠
- 插图较小，放在主图内右上角（使用 `fig.add_axes([left, bottom, width, height])`）
- 插图中心可留空成环形

---

### Panel (g): Error taxonomy of failed tasks

**来源**: MANUSCRIPT.md §Panel g

**图表类型**: 主图 = 环形图 (donut chart)；插图 = 小表格 (table inset)

**主图数据**:
- 读取所有 workflow 的 raw jsonl 中 `success=False` 的记录
- 对 `errors` 字段进行关键词分类：
  - `Service Unavailable`（含 `service request failed`, `ConnectionError`）
  - `Timeout`（含 `timeout`, elapsed 异常大）
  - `Input Validation`（含 `ValidationError`, `too short`）
  - `Other / Unknown`

**插图数据**:
- 受影响最严重的 Top-3 workflow × failure class 表格

**视觉要求**:
- 莫兰迪配色：Dusty rose `#D4A5A5` / Warm sand `#C9B99A` / Sage green `#A5B5A0` / Neutral grey `#B5B5B5`
- 环形图中心留白，内部可标注总失败数
- 插图表格用 `ax.table()` 实现，背景半透明

---

### Panel (i): Computational latency by workflow group

**来源**: MANUSCRIPT.md §Panel i

**图表类型**: 箱线图 (box plot) 或 小提琴图 (violin plot)

**数据需求**:
- 读取所有 raw jsonl 的 `elapsed_seconds`
- 横轴：11 个 workflows，按计算强度分组：
  1. **CPU-only** (`mrna_sequence_scoring`, `sirna_design`, `sgrna_design`, `aso_target_screening`, `ires_prediction`)
  2. **Online microservices** (`mrna_cds_design`, `rna_secondary_structure_design`)
  3. **GPU-intensive** (`full_length_mrna_design`, `rna_tertiary_structure_design`, `rna_aptamer_design`, `rna_small_molecule_interaction`)

**视觉要求**:
- Y 轴使用对数刻度 `log10`（因耗时跨度大）
- 使用莫兰迪色，按强度组给背景加 subtle shading
- 每个 box/violin 上方标注中位数
-  outliers (>300s) 单独标为点
- 添加水平虚线标注 timeout 阈值（如 120s 或 7200s，视实验配置）

---

## 四、不需要实验结果的静态子图（供参考，本模板不生成代码）

| Panel | 内容 | 类型 |
|-------|------|------|
| (a) | 六层系统架构 | 概念示意图 |
| (b) | Workflow 分类与分组 | 层级表格 + 色标 |
| (h) | 跨 Workflow 工具复用矩阵 | 二值热力图（静态提取） |

---

## 五、用户输入格式

当需要绘制某个子图时，请复制以下格式发送：

```
请绘制图 2.1 的子图 (c)：
- 子图标题：Task Success Rate per Workflow
- 图表类型：分组条形图
- 额外要求：workflow 名称横排显示不下可缩写为 3-4 字母；柱顶标注 n=任务数
```

Kimi 将基于本模板生成**完整可执行的 Python 代码**，并保存到规范路径。
