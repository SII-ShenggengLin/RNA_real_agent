#!/usr/bin/env python3
"""Fig 5 plot: mechanism ablations — why each BMC design choice matters.

Data sources (final):
- `experiments/results/fig5_summary.json` — paired tests, panel-d lambda
  boundedness (experiments/analysis/summarize_fig5.py).
- `experiments/results/fig5_ablations.jsonl` — raw runs (pair extraction,
  lambda trajectories).

Output: `experiments/plots/fig5.png` (300 dpi, 2×3 grid) + per-panel PDFs
under `experiments/plots/fig5_panels/`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/plots/plot_fig5.py
"""
from __future__ import annotations

import json
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

OBJECTIVES_T2 = ["egarps_component", "rhofold_component", "iptm_component"]
OBJ_SHORT = {"egarps_component": "EGARPS", "rhofold_component": "RhoFold", "iptm_component": "ipTM"}
E1_METRICS = ["asf_distance", "cds_component", "utr5_mrl", "full_mfe_score"]
E1_SHORT = {"asf_distance": "ASF", "cds_component": "CDS", "utr5_mrl": "utr5_mrl", "full_mfe_score": "full_MFE"}


def load_jsonl(path: Path) -> list[dict]:
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def dedupe(records):
    latest = {}
    for r in records:
        k = r.get("task_id")
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


def recompute_fixed_asf(records, panel, targets):
    """Reproduce summarize_fig5's utopian-of-pool fixed ASF (per target)."""
    from agent_core.workflows.multi_objective import (
        achievement_scalarizing_function, normalize_value)
    weights = {k: 1.0 / len(OBJECTIVES_T2) for k in OBJECTIVES_T2}
    asf = {}
    for t in targets:
        runs = [r for r in records.values()
                if r.get("success") and r.get("panel") == panel and r.get("target_id") == t]
        pts = [p for r in runs for p in (r.get("pool_objectives") or [])
               if isinstance(p, dict) and all(k in p for k in OBJECTIVES_T2)]
        if not pts:
            continue
        bounds = {k: (min(p[k] for p in pts), max(p[k] for p in pts)) for k in OBJECTIVES_T2}
        ref = {k: normalize_value(max(p[k] for p in pts), *bounds[k]) for k in OBJECTIVES_T2}
        for r in runs:
            best = r.get("best") or {}
            if not all(isinstance(best.get(k), (int, float)) for k in OBJECTIVES_T2):
                continue
            vec = {k: normalize_value(float(best[k]), *bounds[k]) for k in OBJECTIVES_T2}
            asf[r["task_id"]] = achievement_scalarizing_function(vec, ref, weights, rho=1e-3)
    return asf


def paired_slope(ax, records, panel, arm_x, arm_y, asf, letter, title):
    """Slope graph of asf_fixed per (target, seed) between two arms."""
    cells = {}
    for r in records.values():
        if r.get("success") and r.get("panel") == panel:
            cells.setdefault((r["target_id"], r.get("seed_idx")), {})[r["condition"]] = r
    pairs = []
    for (t, s), cell in sorted(cells.items()):
        rx, ry = cell.get(arm_x), cell.get(arm_y)
        if not rx or not ry:
            continue
        vx, vy = asf.get(rx["task_id"]), asf.get(ry["task_id"])
        if vx is None or vy is None:
            continue
        pairs.append((vx, vy))
    for vx, vy in pairs:
        ax.plot([0, 1], [vx, vy], color="#bdbdbd", linewidth=0.7, zorder=1)
    rng = np.random.default_rng(0)
    for i, vals, color, label in ((0, [p[0] for p in pairs], "#7f7f7f", arm_x),
                                  (1, [p[1] for p in pairs], "#1f77b4", arm_y)):
        jit = rng.uniform(-0.04, 0.04, len(vals))
        ax.scatter(np.full(len(vals), i) + jit, vals, s=8, color=color, alpha=0.8,
                   linewidths=0, zorder=3, label=label)
    med = [float(np.median([p[i] for p in pairs])) for i in (0, 1)]
    ax.plot([0, 1], med, color="black", linewidth=1.8, zorder=4)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([arm_x, arm_y])
    ax.set_ylabel("ASF distance (fixed reference)")
    panel_label(ax, letter, title, f"n={len(pairs)} pairs", note_loc="top")


def paired_scatter(ax, records, panel, metrics, short, letter, title):
    """Paired scatter serial(x) vs bmc1(y) with identity line."""
    cells = {}
    for r in records.values():
        if r.get("success") and r.get("panel") == panel:
            rep = r.get("rep", r.get("seed_idx"))
            cells.setdefault((r["target_id"], rep), {})[r["condition"]] = r
    markers = ["o", "s", "^", "D"]
    for mi, metric in enumerate(metrics):
        xs, ys = [], []
        for (t, rep), cell in sorted(cells.items()):
            rs, rb = cell.get("serial"), cell.get("bmc1")
            if not rs or not rb:
                continue
            vx = (rs.get("best") or {}).get(metric)
            vy = (rb.get("best") or {}).get(metric)
            if isinstance(vx, (int, float)) and isinstance(vy, (int, float)):
                xs.append(float(vx))
                ys.append(float(vy))
        if xs:
            ax.scatter(xs, ys, s=14, marker=markers[mi % 4], alpha=0.8,
                       label=f"{short[metric]} (n={len(xs)})", linewidths=0.4,
                       edgecolor="black", zorder=3)
    lo = min(ax.get_xlim()[0], ax.get_ylim()[0])
    hi = max(ax.get_xlim()[1], ax.get_ylim()[1])
    ax.plot([lo, hi], [lo, hi], color="#7f7f7f", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Serial")
    ax.set_ylabel("BMC×1")
    ax.legend(frameon=False, fontsize=5.5, loc="upper left")
    panel_label(ax, letter, title, "identity line", note_loc="bottom")


def panel_c(ax, records):
    """Boundedness: lambda trajectories from the extreme start (λ=18)."""
    runs = [r for r in records.values() if r.get("success") and r.get("panel") == "d"]
    tcolors = {"Insulin": "#1f77b4", "Growth_hormone": "#2ca02c", "EPO": "#d62728"}
    for r in sorted(runs, key=lambda z: z["task_id"]):
        traj = r.get("lambda_trajectory") or []
        if not traj:
            continue
        ax.plot(range(len(traj)), traj, marker="o", markersize=3, linewidth=1.0,
                color=tcolors.get(r["target_id"], "#7f7f7f"), alpha=0.8,
                label=r["target_id"] if r.get("rep") in (0, None) else None)
    ax.axhspan(0, 20, color="#2ca02c", alpha=0.06)
    ax.axhline(20, color="#7f7f7f", linestyle="--", linewidth=0.8)
    ax.axhline(0, color="#7f7f7f", linestyle="--", linewidth=0.8)
    ax.set_ylim(-0.8, 21.5)
    ax.text(0.02, 0.6, "clamp interval [0, 20]", fontsize=6, color="#444444")
    ax.set_xlabel("BMC round index (0 = initial)")
    ax.set_ylabel("lambda_value")
    handles, labels = ax.get_legend_handles_labels()
    by = dict(zip(labels, handles))
    ax.legend(by.values(), by.keys(), frameon=False, fontsize=6, loc="center right")
    panel_label(ax, "c", "bounded adjustment from extreme start (λ=18)",
                f"n={len(runs)} runs, all within [0,20]", note_loc="bottom")


def panel_f(ax):
    ax.axis("off")
    s = SUMM
    b = s["panels"]["b"]["tests"]
    c = s["panels"]["c"]["tests"]
    e1 = s["panels"]["e_type1"]["tests"]
    lines = [
        "panel b (feedback mode): all NS",
        f"  asf_fixed p={b['asf_fixed']['wilcoxon_p']:.2f} q={b['asf_fixed']['q_bh']:.2f}",
        "panel c (reference point): asf NS",
        f"  asf_fixed p={c['asf_fixed']['wilcoxon_p']:.2f}",
        f"  egarps p={c['egarps_component']['wilcoxon_p']:.3f} q={c['egarps_component']['q_bh']:.2f}",
        "panel e1 (Type-I neg. control): NS as expected",
        f"  cds p={e1['cds_component']['wilcoxon_p']:.2f} utr5 p={e1['utr5_mrl']['wilcoxon_p']:.2f}",
        "panel e2 (Type-II neg. control): n=3, descriptive",
        "",
        "Boundaries: Ferritin b/c (6) +",
        "Nucleocapsid e2 (6) — ODesign zero",
        "output, deterministic (limitations).",
    ]
    ax.text(0.02, 0.98, "\n".join(lines), transform=ax.transAxes, ha="left",
            va="top", fontsize=6.8, family="monospace")
    ax.set_title("f  statistics digest", loc="left", fontweight="bold")


PANELS = ["a", "b", "c", "d", "e", "f"]


def main() -> int:
    global SUMM
    SUMM = json.loads((RESULTS / "fig5_summary.json").read_text())
    records = dedupe(load_jsonl(RESULTS / "fig5_ablations.jsonl"))
    targets_bc = sorted({r["target_id"] for r in records.values()
                         if r.get("panel") in ("b", "c") and r.get("success")})
    asf_b = recompute_fixed_asf(records, "b", targets_bc)
    asf_c = recompute_fixed_asf(records, "c", targets_bc)

    PLOTS.mkdir(parents=True, exist_ok=True)
    (PLOTS / "fig5_panels").mkdir(parents=True, exist_ok=True)

    def call(letter, ax):
        if letter == "a":
            paired_slope(ax, records, "b", "pool_average", "source_aware", asf_b,
                         "a", "source-aware vs pool-average feedback")
        elif letter == "b":
            paired_slope(ax, records, "c", "fixed_reference", "utopian", asf_c,
                         "b", "utopian vs fixed-threshold reference")
        elif letter == "c":
            panel_c(ax, records)
        elif letter == "d":
            paired_scatter(ax, records, "e_type1", E1_METRICS, E1_SHORT,
                           "d", "Type-I negative control (utr=short)")
        elif letter == "e":
            paired_scatter(ax, records, "e_type2", OBJECTIVES_T2, OBJ_SHORT,
                           "e", "Type-II negative control (explicit hotspot)")
        else:
            panel_f(ax)

    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.4))
    for letter, ax in zip(PANELS, axes.flat):
        call(letter, ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig5.png", dpi=300)
    print(f"wrote {PLOTS / 'fig5.png'}")

    for letter in PANELS:
        f, ax = plt.subplots(figsize=(3.4, 3.0))
        call(letter, ax)
        f.tight_layout()
        f.savefig(PLOTS / "fig5_panels" / f"panel_{letter}.pdf")
        plt.close(f)
    print(f"wrote {len(PANELS)} panel PDFs -> {PLOTS / 'fig5_panels'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
