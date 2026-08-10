#!/usr/bin/env python3
"""Fig 6 plot: agent-layer governance, cross-LLM robustness, cost envelope.

Data sources (final):
- `experiments/results/fig6_quality_ablation.jsonl` — 19 PA tasks x 2 arms
  (panel a/c).
- `experiments/results/fig6_backends.jsonl` — backend matrix records
  (panel b/c); backends without API keys are shown as "not run".
- `experiments/results/fig{2,3,4,5}_*.jsonl` — wall-clock envelope (panel d).

Output: `experiments/plots/fig6.png` (300 dpi, 2×2 grid) + per-panel PDFs
under `experiments/plots/fig6_panels/`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/plots/plot_fig6.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS = PROJECT_ROOT / "experiments" / "results"
PLOTS = PROJECT_ROOT / "experiments" / "plots"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
})

BACKEND_ORDER = ["deepseek-v4-pro", "qwen2.5-72b", "gemma-2-27b",
                 "gpt-3.5-turbo", "gpt-4", "claude-3.5-sonnet"]
ARM_COLORS = {"quality_off": "#7f7f7f", "quality_on": "#1f77b4"}


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def dedupe(records, keyf):
    latest = {}
    for r in records:
        k = keyf(r)
        prev = latest.get(k)
        if prev is None or str(r.get("timestamp") or "") >= str(prev.get("timestamp") or ""):
            latest[k] = r
    return latest


def panel_label(ax, letter, title, note="", note_loc="bottom"):
    ax.set_title(f"{letter}  {title}", loc="left", fontweight="bold")
    if note:
        y, va = (0.02, "bottom") if note_loc == "bottom" else (0.98, "top")
        ax.text(0.98, y, note, transform=ax.transAxes, ha="right", va=va,
                fontsize=6.5, color="#444444")


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def panel_a(ax, qa):
    """QualityAgent value: identical success, advisory retries, latency cost."""
    arms = ["quality_off", "quality_on"]
    succ, retries, elapsed, recovered = [], [], [], []
    for arm in arms:
        rs = [r for (t, a), r in qa.items() if a == arm]
        n = len(rs)
        ok = sum(1 for r in rs if r.get("success"))
        succ.append(ok / max(n, 1))
        retries.append(sum(tu.get("retry_count", 0) for r in rs for tu in r.get("turns", [])))
        recovered.append(sum(1 for r in rs for tu in r.get("turns", []) if tu.get("hard_failure_recovered")))
        els = sorted(r.get("elapsed_seconds", 0) for r in rs)
        elapsed.append(els[len(els) // 2] if els else 0)
    x = np.arange(3)
    w = 0.35
    ax.bar(x - w / 2, [succ[0] * 100, retries[0], elapsed[0] / 60], w,
           color=ARM_COLORS["quality_off"], alpha=0.85, label="quality_off")
    ax.bar(x + w / 2, [succ[1] * 100, retries[1], elapsed[1] / 60], w,
           color=ARM_COLORS["quality_on"], alpha=0.85, label="quality_on")
    ax.set_xticks(x)
    ax.set_xticklabels(["task success (%)", "retries executed", "median min / task"])
    for xi, vals in zip(x, [(succ[0] * 100, succ[1] * 100), (retries[0], retries[1]),
                            (elapsed[0] / 60, elapsed[1] / 60)]):
        for off, v in zip((-w / 2, w / 2), vals):
            ax.text(xi + off, v, f"{v:.0f}" if v > 10 else f"{v:.1f}",
                    ha="center", va="bottom", fontsize=6)
    ax.legend(frameon=False, loc="upper right")
    ax.set_ylim(0, 115)
    panel_label(ax, "a", "QualityAgent ablation (19 PA tasks × 2 arms)",
                "success identical; LLM advisory", note_loc="bottom")


def panel_b(ax, backends, tasks_all):
    """Cross-backend task success matrix."""
    grid = np.full((len(BACKEND_ORDER), len(tasks_all)), np.nan)
    for i, b in enumerate(BACKEND_ORDER):
        for j, t in enumerate(tasks_all):
            r = backends.get((b, t))
            if r is None:
                continue
            grid[i, j] = 1.0 if r.get("success") else 0.0
    cmap = matplotlib.colors.ListedColormap(["#d62728", "#2ca02c"])
    cmap.set_bad("#dddddd")
    ax.imshow(grid, aspect="auto", cmap=cmap, vmin=0, vmax=1)
    ax.set_xticks(range(len(tasks_all)))
    ax.set_xticklabels([t.replace("PA_", "") for t in tasks_all], fontsize=5.5)
    ax.set_yticks(range(len(BACKEND_ORDER)))
    labels = []
    for b in BACKEND_ORDER:
        n = sum(1 for t in tasks_all if (b, t) in backends)
        ok = sum(1 for t in tasks_all if backends.get((b, t), {}).get("success"))
        labels.append(f"{b} ({ok}/{n if n else '—'})")
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_xlabel("PA task")
    panel_label(ax, "b", "task success by backend (grey = no key)",
                "", note_loc="top")


def panel_c(ax, qa):
    """Quality-report action distribution (quality_on arm)."""
    actions = Counter()
    n_turns = 0
    for (t, a), r in qa.items():
        if a != "quality_on":
            continue
        for tu in r.get("turns", []):
            n_turns += 1
            for act in (tu.get("quality_actions") or []):
                actions[act] += 1
    order = ["pass", "retry_with_adjustments", "retry_with_alternative", "abort"]
    vals = [actions.get(k, 0) for k in order]
    colors = ["#2ca02c", "#1f77b4", "#ff7f0e", "#d62728"]
    ax.bar(range(len(order)), vals, color=colors, alpha=0.85, width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=7)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([k.replace("retry_with_", "retry:\n") for k in order], fontsize=6.5)
    ax.set_ylabel("quality reports")
    panel_label(ax, "c", "QualityAgent action distribution",
                f"{n_turns} turns, advisory mode", note_loc="top")


def panel_d(ax):
    """Ops envelope: per-campaign wall-clock distribution (log scale)."""
    sources = [
        ("fig2\nplatform", ["fig2_cpu_a.jsonl", "fig2_cpu_b.jsonl", "fig2_gpu.jsonl"]),
        ("fig3\nType-I", ["fig3_type1_shard_a.jsonl", "fig3_type1_shard_b.jsonl"]),
        ("fig4\nType-II", ["fig4_type2_shard_a.jsonl", "fig4_type2_shard_b.jsonl"]),
        ("fig5\nmechanism", ["fig5_ablations.jsonl"]),
        ("fig6\nagent", ["fig6_quality_ablation.jsonl"]),
    ]
    groups, labels, colors = [], [], []
    for label, files in sources:
        vals = []
        for f in files:
            for r in load_jsonl(RESULTS / f):
                v = r.get("elapsed_seconds")
                if r.get("success") and isinstance(v, (int, float)) and v > 0:
                    vals.append(v / 60.0)
        groups.append(vals)
        labels.append(f"{label}\n(n={len(vals)})")
        colors.append("#1f77b4")
    positions = list(range(1, len(groups) + 1))
    bp = ax.boxplot([g if g else [np.nan] for g in groups], positions=positions,
                    widths=0.55, showfliers=False, patch_artist=True,
                    medianprops={"color": "black", "linewidth": 1.2})
    for patch in bp["boxes"]:
        patch.set_facecolor("#1f77b4")
        patch.set_alpha(0.35)
    rng = np.random.default_rng(0)
    for pos, group in zip(positions, groups):
        if not group:
            continue
        sample = group if len(group) <= 60 else list(rng.choice(group, 60, replace=False))
        ax.scatter(np.full(len(sample), pos) + rng.uniform(-0.12, 0.12, len(sample)),
                   sample, s=4, color="#1f77b4", alpha=0.4, linewidths=0, zorder=3)
    ax.set_yscale("log")
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylabel("wall-clock per run (min, log)")
    panel_label(ax, "d", "operations envelope across campaigns", "", note_loc="top")


PANELS = ["a", "b", "c", "d"]


def main() -> int:
    qa = dedupe(load_jsonl(RESULTS / "fig6_quality_ablation.jsonl"),
                lambda r: (r.get("task_id"), r.get("arm")))
    backends = dedupe(load_jsonl(RESULTS / "fig6_backends.jsonl"),
                      lambda r: (r.get("backend"), r.get("task_id")))
    tasks_all = sorted({t for (_b, t) in backends} | {t for (t, _a) in qa})

    PLOTS.mkdir(parents=True, exist_ok=True)
    (PLOTS / "fig6_panels").mkdir(parents=True, exist_ok=True)

    def call(letter, ax):
        if letter == "a":
            panel_a(ax, qa)
        elif letter == "b":
            panel_b(ax, backends, tasks_all)
        elif letter == "c":
            panel_c(ax, qa)
        else:
            panel_d(ax)

    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2))
    for letter, ax in zip(PANELS, axes.flat):
        call(letter, ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig6.png", dpi=300)
    print(f"wrote {PLOTS / 'fig6.png'}")

    for letter in PANELS:
        f, ax = plt.subplots(figsize=(3.4, 3.0))
        call(letter, ax)
        f.tight_layout()
        f.savefig(PLOTS / "fig6_panels" / f"panel_{letter}.pdf")
        plt.close(f)
    print(f"wrote {len(PANELS)} panel PDFs -> {PLOTS / 'fig6_panels'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
