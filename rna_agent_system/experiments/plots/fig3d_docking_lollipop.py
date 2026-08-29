#!/usr/bin/env python3
"""Fig. 3d — EGARPS+ docking power: native-pose rank lollipop.

One lollipop per docking anchor (x = complex, ordered by protein target),
stem height = rank of the experimental native pose among the 21-candidate
decoy set by EGARPS+ native_probability (1 = top-1; ties broken against the
native).  The pre-registered docking criterion (native top-1; panel-level
gate >= 2/3 of complexes) is stated in the caption, not drawn — the y = 1
line sat one rank above the x-axis and read as a duplicate axis.

Style (reset programme, Nature convention): no in-figure title — the
headline lives in the caption and the assembler adds the panel letter;
every text element is one 6-pt ink-black style (fig2d/fig2f/fig2i/fig3c
convention).  2026-08-29 user-directed revisions: in-figure title dropped
(it duplicated the caption and sat off-centre); the alternating group
bands dropped — non-data shading; all markers one filled terracotta style
(the v2-retained/v3-added provenance split and its legend dropped — the
panel shows the reset run only, the fig3c convention); the protein-target
group labels moved out of the panel into the Fig. 3d caption, which lists
the aptamer→target mapping left to right (the two staggered text rows did
not track their groups); the top-1 gate line dropped after user review
(it sat one rank above the x-axis and read as a duplicate axis; the
pre-registered criterion is stated in the caption); all text unified 6-pt
ink black; NF-kB corrected
to NF-κB; y-axis "Native-pose rank" (the per-marker rank/N annotations
carry the denominators, which differ for pL1 after the disclosed pose
failure); PNG at 1200 dpi (Nature Methods line-art guidance; the PDF
stays vector, fonttype 42).

Colours (palette rev 7): lollipops in the EGARPS oracle colour used across
Fig. 3 (terracotta); all text in ink black.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SUMMARY_PATH = (
    PROJECT_ROOT / "experiments" / "results" / "exp12_docking_capability"
    / "summary.json"
)
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FS = 6  # the programme's single text size

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FS,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

C_ORACLE = "#C08B7C"           # terracotta — EGARPS across Fig. 3

# x order = protein-target groups (retained families first, then the v3
# additions by target then PDB); the aptamer→target mapping is stated in
# the Fig. 3d caption, not on the panel
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
    ("NF-κB", ["p50apt_nfkb"]),
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

    rows = []  # (group, aid, summary row)
    for group, ids in GROUP_ORDER:
        for aid in ids:
            v = per_anchor.get(aid)
            if v is None or v.get("native_rank") is None:
                continue
            rows.append((group, aid, v))
    assert rows, "no scored anchors in summary.json"

    n = len(rows)
    max_rank = max(v["native_rank"] for _, _, v in rows)

    fig, ax = plt.subplots(figsize=(6.2, 2.3))

    for i, (_, aid, v) in enumerate(rows):
        rank = v["native_rank"]
        n_poses = v["n_poses_scored"]
        ax.plot([i, i], [0, rank], color=C_ORACLE, lw=1.1, zorder=2,
                solid_capstyle="round")
        ax.scatter([i], [rank], s=24, facecolor=C_ORACLE,
                   edgecolor=C_ORACLE, linewidth=1.0, zorder=3)
        ax.annotate(f"{rank}/{n_poses}", (i, rank),
                    textcoords="offset points", xytext=(0, 4.5),
                    ha="center", fontsize=FS, color=TEXT, zorder=4)

    ax.set_xticks(range(n))
    ax.set_xticklabels([SHORT_LABELS.get(aid, aid) for _, aid, _ in rows],
                       rotation=45, ha="right", rotation_mode="anchor",
                       fontsize=FS)
    ax.set_ylabel("Native-pose rank", fontsize=FS, labelpad=2)
    ax.set_ylim(0, max_rank + 2.0)
    ax.set_yticks(range(0, max_rank + 3, 5))
    ax.set_xlim(-0.6, n - 0.4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", length=0)
    ax.tick_params(axis="both", labelsize=FS)
    ax.grid(axis="y", color=NEUTRAL_GRID, lw=0.4, zorder=1)

    n_top1 = sum(1 for _, _, v in rows if v["top1"])
    n_scored = sum(v["n_poses_scored"] for _, _, v in rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3d_docking_lollipop.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"wrote fig3d_docking_lollipop.{{pdf,png}} ({n} complexes, "
          f"{n_top1} top-1, {n_scored} poses scored)")


if __name__ == "__main__":
    main()
