#!/usr/bin/env python3
"""Fig 7 plot: real-world end-to-end case studies.

Data sources:
- `experiments/results/fig7_cases/<A,B,C>/case_summary.json` (+ nodes.jsonl)
  — driver outputs of experiments/run_case_study_pipelines.py.
- `experiments/results/fig3_anchors.json` — BNT162b2 / mRNA-1273 anchors
  for the Case-A overlay.

Output: `experiments/plots/fig7.png` (300 dpi, 2×2 grid) + per-panel PDFs
under `experiments/plots/fig7_panels/`. Panels for cases whose summary is
missing or unsuccessful render a "pending" placeholder so the script can be
re-run as cases land.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/plots/plot_fig7.py
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
CASES = RESULTS / "fig7_cases"
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

OBJECTIVES = ["egarps_component", "rhofold_component", "iptm_component"]
OBJ_SHORT = {"egarps_component": "EGARPS", "rhofold_component": "RhoFold", "iptm_component": "ipTM"}


def load_case(case: str) -> dict | None:
    p = CASES / case / "case_summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def panel_label(ax, letter, title, note="", note_loc="bottom"):
    ax.set_title(f"{letter}  {title}", loc="left", fontweight="bold")
    if note:
        y, va = (0.02, "bottom") if note_loc == "bottom" else (0.98, "top")
        ax.text(0.98, y, note, transform=ax.transAxes, ha="right", va=va,
                fontsize=6.5, color="#444444")


def pending(ax, letter, case, reason):
    ax.axis("off")
    ax.text(0.5, 0.55, f"Case {case}\n{reason}", transform=ax.transAxes,
            ha="center", va="center", fontsize=9, color="#7f7f7f")
    panel_label(ax, letter, f"case {case} (pending)")


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def panel_a(ax):
    """Case A — Spike mRNA vaccine candidate vs approved-vaccine anchors."""
    s = load_case("A")
    if not s or not s.get("success"):
        pending(ax, "a", "A", "awaiting design node\n(resume sweep running)")
        return
    overlay = {e.get("molecule"): e for e in (s.get("anchor_overlay") or [])}
    top = s.get("designed_best") or overlay.get("designed_case_a") or {}
    metrics = [
        ("utr5_mrl", "5'UTR MRL"),
        ("utr3_stability", "3'UTR stability"),
        ("cds_cai", "CDS CAI"),
    ]
    series = [("designed", top, "#1f77b4"),
              ("BNT162b2", overlay.get("bnt162b2") or {}, "#d62728"),
              ("mRNA-1273", overlay.get("mrna1273") or {}, "#ff7f0e")]
    x = np.arange(len(metrics))
    w = 0.25
    for i, (name, vals, color) in enumerate(series):
        vv = [vals.get(k) if isinstance(vals.get(k), (int, float)) else 0 for k, _ in metrics]
        ax.bar(x + (i - 1) * w, vv, w, color=color, alpha=0.85, label=name)
        for xi, v in zip(x + (i - 1) * w, vv):
            ax.text(xi, v, f"{v:.2f}", ha="center", va="bottom", fontsize=5.5)
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab in metrics])
    ax.set_ylabel("value")
    ax.legend(frameon=False, fontsize=6, loc="upper right")
    buried = top.get("junction_5utr_cds_aug_buried")
    ires_nodes = [n for n in (s.get("nodes") or []) if n.get("node_id") == "ires_scan"]
    n_hits = len(((ires_nodes[0].get("outputs") or {}).get("top_probabilities") or [])) if ires_nodes else 0
    note = f"IRES hits: {n_hits} (safety); AUG buried={buried} (soft flag)"
    panel_label(ax, "a", "Case A — Spike mRNA vaccine candidate", note, note_loc="bottom")


def panel_b(ax):
    """Case B — anti-VEGF aptamer: top candidate vs pegaptanib anchor."""
    s = load_case("B")
    if not s or not s.get("success"):
        pending(ax, "b", "B", "awaiting case data")
        return
    top = ((s.get("interface") or {}).get("top_candidate")) or {}
    peg = {}
    for n in (s.get("nodes") or []):
        if n.get("node_id") == "pegaptanib_anchor":
            peg = (n.get("outputs") or {}).get("components") or {}
    x = np.arange(len(OBJECTIVES))
    w = 0.35
    tv = [float(top.get(k) or 0) for k in OBJECTIVES]
    pv = [float(peg.get(k) or 0) for k in OBJECTIVES]
    ax.bar(x - w / 2, tv, w, color="#1f77b4", alpha=0.85, label="top designed (n=24)")
    ax.bar(x + w / 2, pv, w, color="#d62728", alpha=0.85, label="pegaptanib (parent)")
    for xi, v in zip(x - w / 2, tv):
        ax.text(xi, v, f"{v:.2g}", ha="center", va="bottom", fontsize=6)
    for xi, v in zip(x + w / 2, pv):
        ax.text(xi, v, f"{v:.1g}", ha="center", va="bottom", fontsize=6)
    ax.set_xticks(x)
    ax.set_xticklabels([OBJ_SHORT[k] for k in OBJECTIVES])
    ax.set_ylabel("component score")
    ax.legend(frameon=False, fontsize=6, loc="upper left")
    ic = top.get("interface_contacts")
    hb = top.get("hydrogen_bonds")
    note = f"top: contacts {ic}, H-bonds {hb}; Kd(pegaptanib)≈49 pM"
    panel_label(ax, "b", "Case B — anti-VEGF aptamer (1VPF, BMC×2)", note, note_loc="bottom")


def panel_c(ax):
    """Case C — NSP12 siRNA: safety-ranked candidates vs design rules."""
    s = load_case("C")
    if not s or not s.get("success"):
        pending(ax, "c", "C", "awaiting case data")
        return
    table = (s.get("safety_table") or [])[:6]
    if not table:
        pending(ax, "c", "C", "no safety table")
        return
    y = np.arange(len(table))[::-1]
    gc = [r.get("gc_content", 0) * 100 for r in table]
    mfe = [r.get("duplex_mfe") for r in table]
    off = [r.get("off_target_count") for r in table]
    ax.barh(y, mfe, color="#1f77b4", alpha=0.6, height=0.6)
    for yi, r in zip(y, table):
        seq = r.get("sequence", "")
        ax.text(0.5, yi, f"#{r.get('rank')} {seq[:12]}…  GC {r.get('gc_content', 0) * 100:.0f}%  off-target {r.get('off_target_count'):.0f}",
                transform=ax.get_yaxis_transform(), va="center", fontsize=6, family="monospace")
    ax.axvspan(-60, -30, color="#2ca02c", alpha=0.06)
    ax.set_yticks([])
    ax.set_xlabel("duplex MFE (kcal/mol)")
    n_zero = sum(1 for r in table if (r.get("off_target_count") or 0) == 0)
    note = f"top{len(table)}: {n_zero} zero off-target; GC all in 30–60%"
    panel_label(ax, "c", "Case C — NSP12 siRNA safety table", note, note_loc="top")


def panel_d(ax):
    """Timeline & deliverables digest (text panel)."""
    ax.axis("off")
    lines = ["case timelines & deliverables", ""]
    for case, title in (("A", "Spike mRNA vaccine"), ("B", "anti-VEGF aptamer"), ("C", "NSP12 siRNA")):
        s = load_case(case)
        if not s:
            lines.append(f"{case} {title}: pending")
            continue
        tl = s.get("timeline_seconds")
        ok = s.get("success")
        lines.append(f"{case} {title}: {'OK' if ok else 'FAILED'} "
                     f"{(tl or 0) / 60:.0f} min, {len(s.get('nodes') or [])} nodes")
    lines += ["",
              "Anchors: BNT162b2/mRNA-1273 (A),",
              "pegaptanib 49 pM (B), design-rule",
              "thresholds GC 30–60% (C)."]
    ax.text(0.02, 0.98, "\n".join(lines), transform=ax.transAxes, ha="left",
            va="top", fontsize=6.8, family="monospace")
    ax.set_title("d  case digest", loc="left", fontweight="bold")


PANELS = ["a", "b", "c", "d"]


def main() -> int:
    PLOTS.mkdir(parents=True, exist_ok=True)
    (PLOTS / "fig7_panels").mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2))
    for letter, ax in zip(PANELS, axes.flat):
        globals()[f"panel_{letter}"](ax)
    fig.tight_layout()
    fig.savefig(PLOTS / "fig7.png", dpi=300)
    print(f"wrote {PLOTS / 'fig7.png'}")

    for letter in PANELS:
        f, ax = plt.subplots(figsize=(3.4, 3.0))
        globals()[f"panel_{letter}"](ax)
        f.tight_layout()
        f.savefig(PLOTS / "fig7_panels" / f"panel_{letter}.pdf")
        plt.close(f)
    print(f"wrote {len(PANELS)} panel PDFs -> {PLOTS / 'fig7_panels'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
