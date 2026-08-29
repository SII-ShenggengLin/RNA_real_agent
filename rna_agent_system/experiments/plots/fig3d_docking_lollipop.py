#!/usr/bin/env python3
"""Fig. 3d — EGARPS+ docking power: native-pose rank lollipop.

One lollipop per docking anchor (x = complex, grouped by protein target),
stem height = rank of the experimental native pose among the 21-candidate
decoy set by EGARPS+ native_probability (1 = top-1; ties broken against the
native).  The top-1 gate line (y = 1) marks the pre-registered docking
criterion; the panel-level gate is native top-1 in >= 2/3 of complexes.
Marker fill distinguishes the five anchors carried over from the retained
v2 evidence set (open) from the fourteen admitted by the v3 curation
(filled) — the fig3c retained-open convention.

Colours (palette rev 7): lollipops in the EGARPS oracle colour used across
Fig. 3 (terracotta); gate line in text dark; group bands alternate the two
neutral greys.

Data  : experiments/results/exp12_docking_capability/summary.json
Usage : python experiments/plots/fig3d_docking_lollipop.py
Output : experiments/plots/output/fig3d_docking_lollipop.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SUMMARY_PATH = (
    PROJECT_ROOT / "experiments" / "results" / "exp12_docking_capability"
    / "summary.json"
)
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 6,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

C_ORACLE = "#C08B7C"           # terracotta — EGARPS across Fig. 3
C_BAND_A = "#F2EFEA"           # near-paper group band (non-data)
C_BAND_B = "#FFFFFF"
RETAINED_ANCHORS = {
    "tba_thrombin", "hd22_t27_thrombin", "toggle25t_thrombin",
    "t1p1_hiv1rt", "dtri177_fixa",
}

# protein-target groups (display order: retained families first, then the
# v3 additions by target then PDB)
GROUP_ORDER = [
    ("Thrombin", ["tba_thrombin", "hd22_t27_thrombin", "toggle25t_thrombin",
                  "m08s1_thrombin"]),
    ("HIV-1 RT", ["t1p1_hiv1rt"]),
    ("Factor IXa", ["dtri177_fixa"]),
    ("Factor Xa", ["11f7t_fx"]),
    ("vWF", ["arc1172_vwf", "bt100_vwf"]),
    ("SARS-CoV-2 N", ["a58t10_sars2n"]),
    ("SARS-CoV-2 RBD", ["fyapt_sars2rbd"]),
    ("PSMA", ["a9g_psma"]),
    ("Autotaxin", ["kato16_autotaxin"]),
    ("NF-kB", ["p50apt_nfkb"]),
    ("GRK2", ["c1318_grk2"]),
    ("TfR1", ["cheng22_tfr1"]),
    ("P. falciparum LDH", ["cheung13_pfldh", "c8n5t_pfldh"]),
    ("P. vivax LDH", ["pl1_pvldh"]),
]

SHORT_LABELS = {
    "tba_thrombin": "TBA", "hd22_t27_thrombin": "HD22", 
    "toggle25t_thrombin": "Toggle-25t", "m08s1_thrombin": "M08s-1",
    "t1p1_hiv1rt": "T1.1", "dtri177_fixa": "DTRI-177", "11f7t_fx": "11F7t",
    "arc1172_vwf": "ARC1172", "bt100_vwf": "BT-100", "a58t10_sars2n": "A58-T10",
    "fyapt_sars2rbd": "FY-apt", "a9g_psma": "A9g", "kato16_autotaxin": "Kato16",
    "p50apt_nfkb": "p50-apt", "c1318_grk2": "C13.18", "cheng22_tfr1": "TfR1-apt",
    "cheung13_pfldh": "PfLDH-1", "c8n5t_pfldh": "C8N5t", "pl1_pvldh": "pL1",
}


def main() -> None:
    summary = json.loads(SUMMARY_PATH.read_text())
    per_anchor = summary["per_anchor"]

    rows = []
    for group, ids in GROUP_ORDER:
        for aid in ids:
            v = per_anchor.get(aid)
            if v is None or v.get("native_rank") is None:
                continue
            rows.append((group, aid, v))
    assert rows, "no scored anchors in summary.json"

    n = len(rows)
    max_rank = max(v["native_rank"] for _, _, v in rows)

    fig, ax = plt.subplots(figsize=(5.6, 2.5))

    # group bands
    x = 0
    band_toggle = True
    group_ticks: list[tuple[float, str]] = []
    for group, ids in GROUP_ORDER:
        present = [aid for aid in ids if any(r[1] == aid for r in rows)]
        if not present:
            continue
        if band_toggle:
            ax.add_patch(Rectangle((x - 0.5, 0), len(present), max_rank + 1.6,
                                   facecolor=C_BAND_A, edgecolor="none",
                                   zorder=0))
        band_toggle = not band_toggle
        group_ticks.append((x + (len(present) - 1) / 2, group))
        x += len(present)

    for i, (group, aid, v) in enumerate(rows):
        rank = v["native_rank"]
        n_poses = v["n_poses_scored"]
        retained = aid in RETAINED_ANCHORS
        ax.plot([i, i], [0, rank], color=C_ORACLE, lw=1.1, zorder=2,
                solid_capstyle="round")
        ax.scatter([i], [rank], s=26 if not retained else 22,
                   facecolor=C_ORACLE if not retained else "white",
                   edgecolor=C_ORACLE, linewidth=1.0, zorder=3)
        ax.annotate(f"{rank}/{n_poses}", (i, rank), textcoords="offset points",
                    xytext=(0, 4.5), ha="center", fontsize=4.6, color=TEXT,
                    zorder=4)

    # top-1 gate line
    ax.axhline(1, color=TEXT, lw=0.7, ls=(0, (4, 2)), zorder=1.6)
    ax.annotate("top-1 gate", (n - 0.4, 1), textcoords="offset points",
                xytext=(0, 3), ha="right", fontsize=5, color=TEXT)

    ax.set_xticks(range(n))
    ax.set_xticklabels([SHORT_LABELS.get(aid, aid) for _, aid, _ in rows],
                       rotation=45, ha="right", fontsize=5.2)
    for gi, (gx, gname) in enumerate(group_ticks):
        # two staggered rows below the tick labels to avoid overlaps
        y_frac = -0.235 if gi % 2 == 0 else -0.305
        ax.annotate(gname, (gx, y_frac), xycoords=("data", "axes fraction"),
                    ha="center", fontsize=5.0, style="italic", color=TEXT)
    ax.set_ylabel("native-pose rank (of 21)", fontsize=6)
    ax.set_ylim(0, max_rank + 1.8)
    ax.set_xlim(-0.6, n - 0.4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=NEUTRAL_GRID, lw=0.4, zorder=1)

    handles = [
        Line2D([0], [0], marker="o", color=C_ORACLE, lw=1.1, markersize=4.6,
               markerfacecolor=C_ORACLE, label="v3-added anchor"),
        Line2D([0], [0], marker="o", color=C_ORACLE, lw=1.1, markersize=4.4,
               markerfacecolor="white", label="anchor retained from v2 set"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=5,
              handletextpad=0.4, borderaxespad=0.2)

    n_top1 = sum(1 for _, _, v in rows if v["top1"])
    n_scored = sum(v["n_poses_scored"] for _, _, v in rows)
    ax.set_title(
        f"Native pose top-1 in {n_top1}/{len(rows)} complexes "
        f"(gate \u2265 2/3); {n_scored}/{len(rows) * 21} poses scored",
        fontsize=6, pad=4)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig3d_docking_lollipop.{ext}", dpi=600,
                    bbox_inches="tight")
    plt.close(fig)
    print(f"wrote fig3d_docking_lollipop.{{pdf,png}} ({len(rows)} complexes, "
          f"{n_top1} top-1)")


if __name__ == "__main__":
    main()
