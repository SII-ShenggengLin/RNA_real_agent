#!/usr/bin/env python3
"""Fig 4 plot: BMC Type-II — RNA aptamer design on 20 targets.

Data sources (final):
- `experiments/results/fig4_summary.json` — per-target per-condition means,
  per-cell hypervolumes, paired tests (experiments/analysis/summarize_fig4.py).
- `experiments/results/fig4_type2_shard_{a,b}.jsonl` — raw runs (panel e).
- `experiments/results/fig4_known_aptamers.jsonl` — known-aptamer validation
  blocks (panels c/d).

Output: `experiments/plots/fig4.png` (300 dpi, 2×3 grid) + per-panel PDFs
under `experiments/plots/fig4_panels/`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/plots/plot_fig4.py
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

COND_ORDER = ["serial", "bmc_x1", "bmc_x2", "bmc_x3"]
COND_LABELS = {"serial": "Serial", "bmc_x1": "BMC×1", "bmc_x2": "BMC×2", "bmc_x3": "BMC×3"}
COND_COLORS = {"serial": "#7f7f7f", "bmc_x1": "#1f77b4", "bmc_x2": "#2ca02c", "bmc_x3": "#d62728"}
OBJECTIVES = ["egarps_component", "rhofold_component", "iptm_component"]
OBJ_SHORT = {"egarps_component": "EGARPS", "rhofold_component": "RhoFold", "iptm_component": "ipTM"}


def load_jsonl(path: Path) -> list[dict]:
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def panel_label(ax, letter, title, note="", note_loc="bottom"):
    ax.set_title(f"{letter}  {title}", loc="left", fontweight="bold")
    if note:
        y, va = (0.02, "bottom") if note_loc == "bottom" else (0.98, "top")
        ax.text(0.98, y, note, transform=ax.transAxes, ha="right", va=va,
                fontsize=6.5, color="#444444")


def box_strip(ax, groups, labels, colors, ylabel, positions=None, width=0.55):
    positions = positions or list(range(1, len(groups) + 1))
    bp = ax.boxplot([g if g else [np.nan] for g in groups], positions=positions,
                    widths=width, showfliers=False, patch_artist=True,
                    medianprops={"color": "black", "linewidth": 1.2})
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
    rng = np.random.default_rng(0)
    for pos, group, color in zip(positions, groups, colors):
        if not group:
            continue
        jitter = rng.uniform(-0.12, 0.12, size=len(group))
        ax.scatter(np.full(len(group), pos) + jitter, group, s=6, color=color,
                   alpha=0.75, linewidths=0, zorder=3)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)


def latest_by_key(records, keyf):
    latest = {}
    for r in records:
        k = keyf(r)
        prev = latest.get(k)
        if prev is None or str(r.get("timestamp") or "") >= str(prev.get("timestamp") or ""):
            latest[k] = r
    return latest


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def panel_a(ax, summ):
    """asf_fixed per condition across 19 targets (Ferritin = boundary)."""
    pt = summ["per_target"]
    groups, labels, colors = [], [], []
    for cond in COND_ORDER:
        vals = [pt[t][cond]["asf_fixed"]["mean"] for t in pt
                if cond in pt[t] and pt[t][cond].get("asf_fixed", {}).get("mean") is not None]
        groups.append(vals)
        labels.append(f"{COND_LABELS[cond]}\n(n={len(vals)})")
        colors.append(COND_COLORS[cond])
    box_strip(ax, groups, labels, colors, "ASF distance (fixed reference)")
    tests = summ["paired_tests"]["metrics"]["asf_fixed"]
    notes = [f"×1 p={tests['bmc1_vs_serial']['wilcoxon_p']:.2f} δ={tests['bmc1_vs_serial']['cliffs_delta']:.2f}",
             f"×2 p={tests['bmc2_vs_serial']['wilcoxon_p']:.2f}",
             f"×3 p={tests['bmc3_vs_serial']['wilcoxon_p']:.2f}"]
    panel_label(ax, "a", "ASF to fixed reference by condition", ", ".join(notes), note_loc="top")


def panel_b(ax, summ):
    """Pareto hypervolume (3-D) per (target, seed) cell by condition (log y)."""
    per_cell = summ["hypervolume"]["per_cell"]
    groups, labels, colors = [], [], []
    for cond in COND_ORDER:
        vals = [cell[cond]["hv3d"] for cell in per_cell.values() if cond in cell]
        groups.append(vals)
        labels.append(f"{COND_LABELS[cond]}\n(n={len(vals)})")
        colors.append(COND_COLORS[cond])
    box_strip(ax, groups, labels, colors, "Pareto hypervolume (3-D, log)")
    ax.set_yscale("log")
    tests = summ["paired_tests"]["hypervolume"]["hv3d"]
    notes = [f"×1 p={tests['bmc1_vs_serial']['wilcoxon_p']:.1e} δ=+{tests['bmc1_vs_serial']['cliffs_delta']:.2f}",
             f"×2 p={tests['bmc2_vs_serial']['wilcoxon_p']:.1e}",
             f"×3 p={tests['bmc3_vs_serial']['wilcoxon_p']:.1e}"]
    panel_label(ax, "b", "Pareto hypervolume by condition", ", ".join(notes), note_loc="top")


def panel_c(ax, kav):
    """Known-aptamer validation: designed pools vs known aptamer scores."""
    comps = OBJECTIVES
    xlabels, groups, colors, positions = [], [], [], []
    known_points = []
    group_centers = []
    pos = 1
    for tid, short in (("Thrombin", "Thrombin (TBA)"), ("SARS-CoV-2_Nucleocapsid", "Nucleocapsid (N-apt)")):
        start = pos
        wf = kav.get(("workflow_run", tid)) or {}
        pool = [p for p in (wf.get("pool_objectives") or []) if isinstance(p, dict)]
        kn = kav.get(("known_aptamer_score", tid)) or {}
        kcomp = kn.get("components") or {}
        for comp in comps:
            vals = [float(p[comp]) for p in pool if isinstance(p.get(comp), (int, float))]
            groups.append(vals)
            positions.append(pos)
            colors.append({"Thrombin": "#1f77b4", "SARS-CoV-2_Nucleocapsid": "#2ca02c"}[tid])
            xlabels.append(OBJ_SHORT[comp])
            kv = kcomp.get(comp)
            if isinstance(kv, (int, float)):
                known_points.append((pos, kv))
            pos += 1
        group_centers.append(((start + pos - 1) / 2, short))
        pos += 1.0
    box_strip(ax, groups, xlabels, colors, "component score", positions=positions, width=0.6)
    ax.tick_params(axis="x", labelsize=6.5)
    for x, y in known_points:
        ax.scatter([x], [y], marker="*", s=140, color="#d62728", edgecolor="black",
                   linewidths=0.5, zorder=5)
    ax.scatter([], [], marker="*", s=80, color="#d62728", edgecolor="black",
               linewidths=0.5, label="known aptamer (ProteinX complex)")
    ax.legend(frameon=False, loc="lower right")
    for xc, name in group_centers:
        ax.text(xc, -0.14, name, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=7, color="#444444")
    ax.set_ylim(bottom=-0.05)
    panel_label(ax, "c", "known aptamers vs designed pools", "", note_loc="top")


def panel_d(ax, kav):
    """VEGF case: designed pool vs pegaptanib through the same chain."""
    v = kav.get(("vegf_case", "VEGF")) or {}
    wf = v.get("workflow_run") or {}
    pool = [p for p in (wf.get("pool_objectives") or []) if isinstance(p, dict)]
    peg = (v.get("pegaptanib_score") or {}).get("components") or {}
    groups, positions, colors, xlabels = [], [], [], []
    peg_points = []
    for i, comp in enumerate(OBJECTIVES):
        vals = [float(p[comp]) for p in pool if isinstance(p.get(comp), (int, float))]
        groups.append(vals)
        positions.append(i + 1)
        colors.append("#9467bd")
        xlabels.append(f"{OBJ_SHORT[comp]}\n(n={len(vals)})")
        kv = peg.get(comp)
        if isinstance(kv, (int, float)):
            peg_points.append((i + 1, kv))
    box_strip(ax, groups, xlabels, colors, "component score", positions=positions)
    for x, y in peg_points:
        ax.scatter([x], [y], marker="*", s=140, color="#d62728", edgecolor="black",
                   linewidths=0.5, zorder=5)
    ax.scatter([], [], marker="*", s=80, color="#d62728", edgecolor="black",
               linewidths=0.5, label="pegaptanib (unmodified parent)")
    ax.legend(frameon=False, loc="upper left")
    hot = (v.get("identified_hotspot") or {}).get("residues") or []
    note = f"hotspot {','.join(h.replace('A/', '') for h in hot[:5])}; site cmp: data gap"
    panel_label(ax, "d", "anti-VEGF case (1VPF, BMC×1)", note, note_loc="bottom")


def panel_e(ax, runs):
    """Boundedness: rounds executed + per-round wall-clock from bmc_trace."""
    conds = ["bmc_x1", "bmc_x2", "bmc_x3"]
    maxr = {"bmc_x1": 1, "bmc_x2": 2, "bmc_x3": 3}
    data = {c: [] for c in conds}
    round_ms = []
    for r in runs:
        if not r.get("success") or not r.get("bmc_max_rounds"):
            continue
        cond = f"bmc_x{r['bmc_max_rounds']}"
        if cond in data and r.get("bmc_rounds_executed") is not None:
            data[cond].append(r["bmc_rounds_executed"])
        for e in (r.get("bmc_trace") or []):
            t = e.get("time_elapsed_ms") or e.get("elapsed_ms")
            if isinstance(t, (int, float)):
                round_ms.append(t / 60000.0)
    x = np.arange(len(conds))
    for i, cond in enumerate(conds):
        vals = data[cond]
        if not vals:
            continue
        full = sum(1 for v in vals if v == maxr[cond]) / len(vals)
        early = 1.0 - full
        ax.bar(x[i], full, color=COND_COLORS[cond], alpha=0.9, width=0.55)
        ax.bar(x[i], early, bottom=full, color=COND_COLORS[cond], alpha=0.35,
               hatch="//", edgecolor="white", width=0.55)
        if full > 0.05:
            ax.text(x[i], full / 2, f"all\n{full:.0%}", ha="center", va="center", fontsize=6)
        if early > 0.05:
            ax.text(x[i], full + early / 2, f"early\n{early:.0%}", ha="center", va="center", fontsize=6)
    ax.set_xticks(x)
    ax.set_xticklabels([COND_LABELS[c] for c in conds])
    ax.set_ylabel("fraction of runs")
    ax.set_ylim(0, 1.05)
    note = f"per-round wall: median {np.median(round_ms):.0f} min (n={len(round_ms)})" if round_ms else ""
    panel_label(ax, "e", "rounds executed (hatched = early stop)", note, note_loc="top")


def panel_f(ax, summ):
    """Boundary & governance notes (text panel)."""
    ax.axis("off")
    lines = [
        "Ferritin (1FHA): ODesign produced zero",
        "sequences in all 12 matrix cells + retries",
        "— target-side boundary (limitations).",
        "",
        "Zika / Factor VIII (Fig 3): LinearDesign",
        "OOM on ≥7 kb CDS — operating envelope.",
        "",
        "Myoglobin r3 s2: QualityAgent hallucinated",
        "abort; retry succeeded — LLM is advisory,",
        "not load-bearing (governance case).",
        "",
        f"ASF tests: egarps ×1 p={summ['paired_tests']['metrics']['egarps_component']['bmc1_vs_serial']['wilcoxon_p']:.1e}",
        f"hv3d ×1 p={summ['paired_tests']['hypervolume']['hv3d']['bmc1_vs_serial']['wilcoxon_p']:.1e}",
    ]
    ax.text(0.02, 0.98, "\n".join(lines), transform=ax.transAxes, ha="left",
            va="top", fontsize=6.8, family="monospace")
    ax.set_title("f  boundary & notes", loc="left", fontweight="bold")


PANELS = ["a", "b", "c", "d", "e", "f"]


def main() -> int:
    summ = json.loads((RESULTS / "fig4_summary.json").read_text())
    kav = latest_by_key(load_jsonl(RESULTS / "fig4_known_aptamers.jsonl"),
                        lambda r: (r.get("block"), r.get("target_id")))
    runs = load_jsonl(RESULTS / "fig4_type2_shard_a.jsonl") + load_jsonl(RESULTS / "fig4_type2_shard_b.jsonl")

    PLOTS.mkdir(parents=True, exist_ok=True)
    (PLOTS / "fig4_panels").mkdir(parents=True, exist_ok=True)

    def call(letter, ax):
        if letter in ("a", "b", "f"):
            globals()[f"panel_{letter}"](ax, summ)
        elif letter in ("c", "d"):
            globals()[f"panel_{letter}"](ax, kav)
        else:
            globals()[f"panel_{letter}"](ax, runs)

    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.4))
    for letter, ax in zip(PANELS, axes.flat):
        call(letter, ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig4.png", dpi=300)
    print(f"wrote {PLOTS / 'fig4.png'}")

    for letter in PANELS:
        f, ax = plt.subplots(figsize=(3.4, 3.0))
        call(letter, ax)
        f.tight_layout()
        f.savefig(PLOTS / "fig4_panels" / f"panel_{letter}.pdf")
        plt.close(f)
    print(f"wrote {len(PANELS)} panel PDFs -> {PLOTS / 'fig4_panels'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
