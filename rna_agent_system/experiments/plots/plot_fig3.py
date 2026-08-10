#!/usr/bin/env python3
"""Fig 3 plot: BMC Type-I — full-length mRNA design on 20 targets.

Data sources (final):
- `experiments/results/fig3_summary.json` — per-target per-condition means,
  paired tests, burial stats (experiments/analysis/summarize_fig3.py).
- `experiments/results/fig3_type1_shard_{a,b}.jsonl` — raw runs (panels e/f).
- `experiments/results/fig3_steering.jsonl` — reference-point steering runs.
- `experiments/results/fig3_anchors.json` — BNT162b2 / mRNA-1273 / WT anchors.

Output: `experiments/plots/fig3.png` (300 dpi, 2×3 grid) + per-panel PDFs
under `experiments/plots/fig3_panels/`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/plots/plot_fig3.py
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
# Hard targets with real module conflict (handoff §5): strong ASF improvement.
HARD_TARGETS = {"HER2", "Beta_galactosidase", "Influenza_HA_H1N1"}


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


def box_strip(ax, groups, labels, colors, ylabel):
    positions = list(range(1, len(groups) + 1))
    bp = ax.boxplot([g if g else [np.nan] for g in groups], positions=positions,
                    widths=0.55, showfliers=False, patch_artist=True,
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


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def panel_a(ax, summ):
    """asf_fixed (fixed-reference ASF, lower=better) per condition, n=20 targets."""
    pt = summ["per_target"]
    groups, labels, colors = [], [], []
    for cond in COND_ORDER:
        vals = [pt[t][cond]["asf_fixed"]["mean"] for t in pt if cond in pt[t]]
        groups.append(vals)
        labels.append(f"{COND_LABELS[cond]}\n(n={len(vals)})")
        colors.append(COND_COLORS[cond])
    box_strip(ax, groups, labels, colors, "ASF distance (fixed reference)")
    tests = summ["paired_tests"]["asf_fixed"]
    notes = [f"×1 p={tests['bmc1_vs_serial']['wilcoxon_p']:.2f}",
             f"×2 p={tests['bmc2_vs_serial']['wilcoxon_p']:.2f}",
             f"×3 p={tests['bmc3_vs_serial']['wilcoxon_p']:.2f}"]
    panel_label(ax, "a", "ASF to fixed reference by condition", ", ".join(notes), note_loc="top")


def panel_b(ax, summ):
    """Per-target Δasf (BMC×1 − Serial), sorted; hard targets annotated."""
    pt = summ["per_target"]
    deltas = []
    for t in pt:
        d = pt[t]["bmc_x1"]["asf_fixed"]["mean"] - pt[t]["serial"]["asf_fixed"]["mean"]
        deltas.append((t, d))
    deltas.sort(key=lambda x: x[1])
    names = [d[0].replace("SARS-CoV-2_Spike_WT", "Spike").replace("Beta_galactosidase", "Beta_gal")
             .replace("Influenza_HA_H1N1", "Influenza").replace("_", " ") for d in deltas]
    vals = [d[1] for d in deltas]
    colors = ["#d62728" if t in HARD_TARGETS else "#bdbdbd" for t, _ in deltas]
    ax.bar(range(len(vals)), vals, color=colors, alpha=0.85, width=0.7)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(names, rotation=60, ha="right", fontsize=5.5)
    ax.set_ylabel("ΔASF (BMC×1 − Serial)")
    panel_label(ax, "b", "per-target ASF change (red = conflict targets)", "", note_loc="top")


def panel_c(ax, summ):
    """Burial-event proportions by condition (AUG / Kozak / any)."""
    burial = summ["burial"]["per_condition"]
    kinds = [("junction_5utr_cds_aug_buried", "AUG"), ("junction_5utr_cds_kozak_buried", "Kozak"), ("any", "any")]
    x = np.arange(len(COND_ORDER))
    width = 0.25
    for i, (key, label) in enumerate(kinds):
        vals = [burial[c][key]["proportion"] for c in COND_ORDER]
        ax.bar(x + (i - 1) * width, vals, width, label=label, alpha=0.85,
               color=["#1f77b4", "#ff7f0e", "#7f7f7f"][i])
    ax.set_xticks(x)
    ax.set_xticklabels([COND_LABELS[c] for c in COND_ORDER])
    ax.set_ylabel("burial fraction of runs")
    ax.legend(frameon=False)
    panel_label(ax, "c", "AUG/Kozak burial events", "60 runs per condition", note_loc="top")


def panel_d(ax, steering):
    """Reference-point steering: utr5_mrl / utr3_stability by profile."""
    targets = ["SARS-CoV-2_Spike_WT", "EPO"]
    profiles = ["translation-first", "stability-first", "balanced"]
    pcolors = {"translation-first": "#1f77b4", "stability-first": "#2ca02c", "balanced": "#d62728"}
    x = np.arange(len(targets))
    width = 0.12
    rng = np.random.default_rng(1)
    for i, prof in enumerate(profiles):
        for j, metric in enumerate(("utr5_mrl", "utr3_stability")):
            vals = [r["best"][metric] for r in steering
                    if r.get("success") and r.get("profile") == prof and metric in (r.get("best") or {})]
            per_t = [[r["best"][metric] for r in steering
                      if r.get("success") and r.get("profile") == prof
                      and r.get("target_id") == t] for t in targets]
            means = [np.mean(v) if v else np.nan for v in per_t]
            offset = (i - 1) * width * 2 + (j - 0.5) * width
            ax.bar(x + offset, means, width * 0.9,
                   color=pcolors[prof], alpha=0.85 if j == 0 else 0.45,
                   label=f"{prof} ({'utr5_mrl' if j == 0 else 'utr3_stab'})" if True else "")
            for k, v in enumerate(per_t):
                if v:
                    ax.scatter(np.full(len(v), x[k] + offset) + rng.uniform(-0.02, 0.02, len(v)),
                               v, s=4, color="black", alpha=0.5, linewidths=0, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(["Spike", "EPO"])
    ax.set_ylabel("metric value")
    ax.legend(frameon=False, fontsize=5.5, ncol=3, loc="upper center",
              bbox_to_anchor=(0.5, -0.12))
    panel_label(ax, "d", "reference-point steering (3 reps)", "", note_loc="top")


def panel_e(ax, runs, summ):
    """Boundedness: rounds executed before termination + Spike trace excerpt."""
    conds = ["bmc_x1", "bmc_x2", "bmc_x3"]
    data = {c: [] for c in conds}
    maxr = {"bmc_x1": 1, "bmc_x2": 2, "bmc_x3": 3}
    for r in runs:
        if not r.get("success") or not r.get("bmc_max_rounds"):
            continue
        cond = f"bmc_x{r['bmc_max_rounds']}"
        if cond in data and r.get("bmc_rounds_executed") is not None:
            data[cond].append(r["bmc_rounds_executed"])
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
        ax.text(x[i], full / 2, f"all rounds\n{full:.0%}", ha="center", va="center", fontsize=6)
        if early > 0.05:
            ax.text(x[i], full + early / 2, f"early\n{early:.0%}", ha="center", va="center", fontsize=6)
    ax.set_xticks(x)
    ax.set_xticklabels([COND_LABELS[c] for c in conds])
    ax.set_ylabel("fraction of runs")
    ax.set_ylim(0, 1.05)
    spike = [r for r in runs if r.get("target_id") == "SARS-CoV-2_Spike_WT"
             and r.get("bmc_max_rounds") == 3 and r.get("success")]
    n_rounds = [len(r.get("bmc_trace") or []) for r in spike]
    note = f"hatched = early stop; Spike×3: {len(spike)} reps, trace rounds {n_rounds}"
    panel_label(ax, "e", "rounds executed before termination", note, note_loc="top")


def panel_f(ax, runs, anchors):
    """Anchor overlay: Spike designed pool vs vaccine/WT anchors."""
    pts = [(r["best"]["cds_cai"], r["best"]["full_mfe_per_nt"]) for r in runs
           if r.get("success") and r.get("target_id") == "SARS-CoV-2_Spike_WT"
           and (r.get("best") or {}).get("cds_cai") is not None
           and (r.get("best") or {}).get("full_mfe_per_nt") is not None]
    if pts:
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=10, color="#1f77b4",
                   alpha=0.5, linewidths=0, label=f"designed pool (n={len(pts)})")
    marks = {"bnt162b2": ("BNT162b2", "*", "#d62728"),
             "mrna1273": ("mRNA-1273", "*", "#ff7f0e"),
             "wt_spike_cds": ("WT CDS", "^", "#7f7f7f")}
    for key, (label, marker, color) in marks.items():
        a = anchors.get(key) or {}
        cai = (a.get("cds") or {}).get("cai_score")
        mfe = (a.get("full_length") or {}).get("mfe_per_nt")
        if cai is not None and mfe is not None:
            ax.scatter([cai], [mfe], marker=marker, s=90, color=color, zorder=4,
                       edgecolor="black", linewidths=0.4, label=label)
    ax.set_xlabel("CDS CAI")
    ax.set_ylabel("full-length MFE/nt (kcal/mol)")
    ax.legend(frameon=False, fontsize=6, loc="lower left")
    panel_label(ax, "f", "designed Spike vs vaccine anchors", "", note_loc="top")


PANELS = ["a", "b", "c", "d", "e", "f"]


def args_for(letter, summ, steering, runs, anchors):
    if letter in ("a", "b", "c"):
        return (summ,)
    if letter == "d":
        return (steering,)
    if letter == "e":
        return (runs, summ)
    if letter == "f":
        return (runs, anchors)
    return ()


def main() -> int:
    summ = json.loads((RESULTS / "fig3_summary.json").read_text())
    steering = load_jsonl(RESULTS / "fig3_steering.jsonl")
    runs = load_jsonl(RESULTS / "fig3_type1_shard_a.jsonl") + load_jsonl(RESULTS / "fig3_type1_shard_b.jsonl")
    anchors = json.loads((RESULTS / "fig3_anchors.json").read_text())

    PLOTS.mkdir(parents=True, exist_ok=True)
    (PLOTS / "fig3_panels").mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.4))
    for letter, ax in zip(PANELS, axes.flat):
        globals()[f"panel_{letter}"](ax, *args_for(letter, summ, steering, runs, anchors))
    fig.tight_layout()
    fig.savefig(PLOTS / "fig3.png", dpi=300)
    print(f"wrote {PLOTS / 'fig3.png'}")

    for letter in PANELS:
        f, ax = plt.subplots(figsize=(3.4, 3.0))
        globals()[f"panel_{letter}"](ax, *args_for(letter, summ, steering, runs, anchors))
        f.tight_layout()
        f.savefig(PLOTS / "fig3_panels" / f"panel_{letter}.pdf")
        plt.close(f)
    print(f"wrote {len(PANELS)} panel PDFs -> {PLOTS / 'fig3_panels'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
