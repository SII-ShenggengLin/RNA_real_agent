#!/usr/bin/env python3
"""
Figure 2.1 — Panel (c): Task Success Rate per Workflow
Data source: RNA-BioBench-Platform benchmark results
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from figure_2_1_common import (
    BASE_DIR,
    GROUP_COLORS,
    GROUP_MAP,
    setup_mpl_style,
    SHORT_NAMES,
    WORKFLOWS,
)

setup_mpl_style(grid=True)

CATEGORY_MAP = {
    "basic": "basic",
    "edge": "edge",
    "edgecase": "edge",
    "boundary": "edge",
    "full": "full",
    "therapeutic": "full",
    "reporter": "full",
    "vaccine": "full",
    "full-length": "full",
    "prokaryotic": "full",
    "comparison": "full",
    "fungal": "full",
    "algae": "full",
    "archaea": "full",
}


def adjust_color_brightness(hex_color: str, factor: float) -> str:
    """Adjust RGB brightness: factor > 1 lightens, < 1 darkens."""
    rgb = mcolors.to_rgb(hex_color)
    adjusted = tuple(min(1.0, max(0.0, c * factor)) for c in rgb)
    return mcolors.to_hex(adjusted)


def get_category_colors(base_color: str) -> dict[str, str]:
    """Return basic/edge/full shades for a given base group colour."""
    return {
        "basic": adjust_color_brightness(base_color, 1.25),
        "edge": base_color,
        "full": adjust_color_brightness(base_color, 0.75),
    }


def load_summary(workflow: str) -> dict:
    path = BASE_DIR / workflow / "summary" / f"summary_{workflow}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_accuracy_data() -> pd.DataFrame:
    rows = []
    for wf in WORKFLOWS:
        summary = load_summary(wf)
        raw_path = BASE_DIR / wf / "raw" / f"platform_coverage_{wf}.jsonl"

        cat_data = None
        cat_key = None
        for key in ["by_category", "category_breakdown", "category_success", "category_success_rates"]:
            if key in summary:
                cat_data = summary[key]
                cat_key = key
                break

        agg = {"basic": {"total": 0, "success": 0},
               "edge": {"total": 0, "success": 0},
               "full": {"total": 0, "success": 0}}

        if cat_key == "category_success_rates":
            raw_cats = Counter()
            with open(raw_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        rec = json.loads(line)
                        raw_cats[rec.get("category", "unknown")] += 1
            for cat, rate in cat_data.items():
                mapped = CATEGORY_MAP.get(cat, "full")
                total = raw_cats.get(cat, 0)
                success = int(round(total * rate / 100)) if isinstance(rate, (int, float)) else total
                agg[mapped]["total"] += total
                agg[mapped]["success"] += success
        elif cat_data is not None:
            for cat, stats in cat_data.items():
                mapped = CATEGORY_MAP.get(cat, "full")
                if isinstance(stats, dict):
                    agg[mapped]["total"] += stats.get("total", 0)
                    agg[mapped]["success"] += stats.get("success", 0)

        for cat in ["basic", "edge", "full"]:
            if agg[cat]["total"] > 0:
                rate = agg[cat]["success"] / agg[cat]["total"] * 100
                rows.append({
                    "workflow": wf,
                    "group": GROUP_MAP[wf],
                    "category": cat,
                    "total": agg[cat]["total"],
                    "success": agg[cat]["success"],
                    "rate": rate,
                })
    return pd.DataFrame(rows)


def main():
    out_dir = Path(
        "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent"
        "/rna_agent_system/experiments/results/plots/figure_2_1"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    df = build_accuracy_data()

    categories = ["basic", "edge", "full"]
    n_cats = len(categories)
    n_wfs = len(WORKFLOWS)
    bar_width = 0.22
    x = np.arange(n_wfs)

    fig, ax = plt.subplots(figsize=(13, 6.5))

    group_shades = {g: get_category_colors(c) for g, c in GROUP_COLORS.items()}

    for i, cat in enumerate(categories):
        offsets = (i - (n_cats - 1) / 2) * bar_width
        cat_x = x + offsets

        heights = []
        colors = []
        ns = []
        for wf in WORKFLOWS:
            row = df[(df["workflow"] == wf) & (df["category"] == cat)]
            if len(row) == 0:
                heights.append(0)
                colors.append("#CCCCCC")
                ns.append(0)
            else:
                heights.append(row["rate"].values[0])
                group = GROUP_MAP[wf]
                colors.append(group_shades[group][cat])
                ns.append(row["total"].values[0])

        ax.bar(cat_x, heights, bar_width, color=colors, edgecolor="white", linewidth=0.5)

        # ── 修复2: n=标注统一放柱子外部上方，深色文字，按类别错开避免重叠 ──
        for bx, h, n in zip(cat_x, heights, ns):
            if h > 0:
                # 每个类别分配不同垂直偏移：basic=1.5, edge=5.5, full=9.5
                base_offsets = {0: 1.5, 1: 5.5, 2: 9.5}
                v_offset = base_offsets.get(i, 1.5)
                ax.text(bx, h + v_offset, f"n={n}",
                        ha="center", va="bottom", fontsize=6.5,
                        color="#444444", fontweight="bold")

    # X-axis labels
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT_NAMES[wf] for wf in WORKFLOWS], rotation=20, ha='right' ,fontsize=9)

    ax.set_ylabel("Task Success Rate (%)", fontsize=11)
    # ── 提高Y轴上限，给顶部n=标注留出空间 ──
    ax.set_ylim(0, 125)
    # ── 修复: 标题大幅上移(y=1.18)，避免和图例重叠 ──
    ax.set_title("Task Success Rate per Workflow", fontsize=14, fontweight="bold", y=1.18)

    # ── 修复1: 两个图例都放到图表上方外部，完全不遮挡柱子 ──

    # Biological Group 图例（左上角，图表外部）
    group_legend_elements = [
        Patch(facecolor=GROUP_COLORS[g], edgecolor="white", label=g)
        for g in GROUP_COLORS
    ]
    legend1 = ax.legend(handles=group_legend_elements, title="Biological Group",
                        fontsize=9, title_fontsize=10, frameon=True, edgecolor="#CCCCCC",
                        loc="lower left", bbox_to_anchor=(0.0, 1.01), ncol=2)

    # Complexity Level 图例（右上角，图表外部）
    # 使用中性灰色，避免读者误以为只适用于某个 Biological Group
    shade_elements = [
        Patch(facecolor="#C5C5C5", edgecolor="white", label="Level-1: Basic"),
        Patch(facecolor="#8A8A8A", edgecolor="white", label="Level-2: Intermediate"),
        Patch(facecolor="#555555", edgecolor="white", label="Level-3: Complex"),
    ]
    legend2 = ax.legend(handles=shade_elements, title="Complexity Level (darker → more complex)",
                        fontsize=8, title_fontsize=9, frameon=True, edgecolor="#CCCCCC",
                        loc="lower right", bbox_to_anchor=(1.0, 1.01), ncol=3)

    # 将两个 legend 都添加到 axes 上
    ax.add_artist(legend1)

    # ── 修复: 增大顶部边距，确保图例标题不被截断 ──
    plt.subplots_adjust(top=0.78)

    plt.savefig(
        out_dir / "fig2_1_c.png",
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.2,
    )
    print(f"Saved to {out_dir / 'fig2_1_c.png'}")


if __name__ == "__main__":
    main()