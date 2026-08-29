#!/usr/bin/env python3
"""Fig. 3h — RNAsmol deployment-artifact fidelity (dumbbell with a live
verification fork).

The same deployed small-molecule oracle, its own official held-out test
splits. The v0.2.0 service (uppercased RNA vocab; the defect class) scored
AUROC 0.786 / 0.410 on these splits — a silent degradation with zero error
signals, caught only by profiling the deployed artifact against its own
publication. The preprocessing repair restored exact official parity, and
today both of the platform's shipped integration paths were re-verified
live, zero-intervention, on all 1,662 pairs (exp15): the default agent tool
path (whose wrapper uppercases + T→U-converts — verified applied on every
pair) and the verbatim service endpoint both deliver the published AUROCs
(0.975 / 0.986 and 0.974 / 0.983), with the endpoint arm bit-identical to
the registered exp7 evidence.

Per split the panel draws three points: the v0.2.0 pre-fix value as an open
circle — re-measured from the git-recovered artifact (commit 7262e54,
sha-asserted, sandbox port 8107, exp15 addendum `exp15_rnasmol_v020_sandbox`),
agreeing with the registered 2026-08-11 history within ≤ 0.009 — forking to
the two live arms (default tool path in terracotta, verbatim endpoint in
sage), each with its stratified-bootstrap 95% CI. The decomposition closes:
v0.2.0 (uppercase + rewritten adjacency) collapses while arm A (uppercase +
upstream-faithful adjacency) does not — the same case treatment on both
sides, so the adjacency rewrite carries the damage. Chance 0.5 solid, the
0.8 screening-gate line dashed (the fig3b/3c/3g reference convention).

Colours (palette rev 7): terracotta (#C08B7C) = the platform's default tool
path — the fig3f failure semantic, and the pre-fix open marker's edge; sage
(#A3B18A) = the verbatim service endpoint — the fig3f true/pass semantic;
connector + gate line in the held-out dark warm grey.

Style: the fig2d–fig3g conventions — no in-figure title (the headline lives
in the caption), every text element one font size and ink black,
single-column geometry, legend as a centred row block under the axis (the
fig2i convention).

Data  : experiments/results/exp15_rnasmol_fidelity/summary.json (live arms)
        + experiments/results/exp15_rnasmol_v020_sandbox/summary.json
        (the git-recovered v0.2.0 pre-fix arm, re-measured)
Usage : python experiments/plots/fig3h_rnasmol_fidelity.py
Output : experiments/plots/output/fig3h_rnasmol_fidelity.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE_BY_NAME, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp15_rnasmol_fidelity"
V020_DIR = PROJECT_ROOT / "experiments" / "results" / "exp15_rnasmol_v020_sandbox"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FONT = 6          # single font size for every in-figure text element
C_PRE = PALETTE_BY_NAME["terracotta"]     # #C08B7C — default tool path / pre-fix edge
C_POST = PALETTE_BY_NAME["sage_green"]    # #A3B18A — service endpoint (verbatim)
C_LINK = PALETTE_BY_NAME["dark_warm_grey"]  # #7A7672 — connectors + gate line
C_REF = NEUTRAL_GRID                        # chance reference line

# The registered v0.2.0 values (PAPER_FACT_SHEET E7 register, 2026-08-11) —
# fallback only; the panel's points come from the re-measured sandbox arm.
HIST_AUROC_REGISTERED = {"robin_test": 0.7864, "pdb_test": 0.4103}

ROW_META = [
    ("robin_test", "ROBIN test\nn = 1,492"),
    ("pdb_test", "PDB test\nn = 170"),
]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

X_MIN, X_MAX = 0.0, 1.30  # 0–1 metric scale + label headroom


def ci_bar(ax, y: float, est: float, lo: float, hi: float, colour: str,
           size: float = 22.0) -> None:
    ax.plot([lo, hi], [y, y], color=colour, linewidth=1.3,
            solid_capstyle="butt", zorder=3)
    for x_edge in (lo, hi):
        ax.plot([x_edge, x_edge], [y - 0.07, y + 0.07], color=colour,
                linewidth=0.9, zorder=3)
    ax.scatter(est, y, s=size, c=colour, edgecolors="white",
               linewidths=0.4, zorder=4)


def main() -> int:
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("no summary.json — run experiments/exp15_rnasmol_fidelity.py "
              "--summary first")
        return 1
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    v020_path = V020_DIR / "summary.json"
    v020 = json.loads(v020_path.read_text(encoding="utf-8")) \
        if v020_path.exists() else None

    rows = []
    for split, label in ROW_META:
        pre = s[f"tool_layer::{split}"]
        post = s[f"service_endpoint::{split}"]
        if v020 is not None:
            hist = v020[f"v020_sandbox::{split}"]["point_auroc"]
            hist = float(hist)
        else:
            hist = HIST_AUROC_REGISTERED[split]
        rows.append({
            "split": split,
            "label": label,
            "hist": hist,
            "tool": (pre["point_auroc"], *pre["auroc_ci95"]),
            "endpoint": (post["point_auroc"], *post["auroc_ci95"]),
        })

    fig_w, fig_h = 88 / 25.4, 50 / 25.4  # single-column panel
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    label_mm, ax_w, y0_mm, h_mm = 22, 61, 12, 32
    ax = fig.add_axes([label_mm / 25.4 / fig_w, y0_mm / 25.4 / fig_h,
                       ax_w / 25.4 / fig_w, h_mm / 25.4 / fig_h])

    # per split: three lanes — verbatim endpoint (top), fork point (middle,
    # v0.2.0 open marker), default tool path (bottom)
    def lanes(i: int) -> tuple[float, float, float]:
        base = 2.0 - i * 1.32
        return base, base - 0.30, base - 0.60  # endpoint, hist, tool

    y_top = lanes(0)[0] + 0.16

    for i, row in enumerate(rows):
        y_ep, y_h, y_tool = lanes(i)
        hist_x, tool, ep = row["hist"], row["tool"], row["endpoint"]
        # fork connectors from the historical marker to both live dots
        ax.plot([hist_x, ep[0]], [y_h, y_ep], color=C_LINK,
                linewidth=0.6, zorder=2)
        ax.plot([hist_x, tool[0]], [y_h, y_tool], color=C_LINK,
                linewidth=0.6, zorder=2)
        # v0.2.0 pre-fix: open marker (registered history, no CI)
        ax.scatter(hist_x, y_h, s=20, facecolors="white", edgecolors=C_PRE,
                   linewidths=1.0, zorder=4)
        ax.text(hist_x, y_h - 0.13, f"{hist_x:.3f}", fontsize=FONT,
                ha="center", va="top", color=TEXT, zorder=5)
        # live arms with CIs and printed values
        ci_bar(ax, y_ep, *ep, colour=C_POST)
        ax.text(ep[0] + 0.02, y_ep + 0.10, f"{ep[0]:.3f} ({ep[1]:.2f}–{ep[2]:.2f})",
                fontsize=FONT, va="bottom", ha="left", color=TEXT, zorder=5)
        ci_bar(ax, y_tool, *tool, colour=C_PRE, size=16.0)
        ax.text(tool[0] + 0.02, y_tool - 0.10,
                f"{tool[0]:.3f} ({tool[1]:.2f}–{tool[2]:.2f})",
                fontsize=FONT, va="top", ha="left", color=TEXT, zorder=5)

    # reference lines: chance solid grid grey, gate dashed dark warm grey
    for x, gate, label in ((0.5, False, "chance"), (0.8, True, "gate 0.8")):
        ax.plot([x, x], [-0.25, y_top], color=C_LINK if gate else C_REF,
                linewidth=0.7, linestyle=(0, (3, 2)) if gate else "-",
                zorder=1)
        ax.text(x, y_top + 0.05, label, fontsize=FONT, ha="center",
                va="bottom", color=TEXT if gate else C_LINK, zorder=5)

    ax.set_yticks([lanes(i)[1] for i in range(len(rows))])
    ax.set_yticklabels([r["label"] for r in rows], fontsize=FONT,
                       linespacing=1.2, color=TEXT)
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(-0.25, y_top + 0.42)
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=FONT)
    ax.tick_params(axis="x", labelsize=FONT, length=1.5, pad=1)
    ax.tick_params(axis="y", labelsize=FONT, length=1.5, pad=2)
    ax.set_xlabel("Screening AUROC — the oracle's own official held-out splits",
                  fontsize=FONT, labelpad=2)
    for s_name in ("top", "right"):
        ax.spines[s_name].set_visible(False)

    # legend: centred row block under the axis (the fig2i convention)
    handles = [
        Line2D([], [], marker="o", linestyle="", markersize=3.4,
               markerfacecolor="white", markeredgecolor=C_PRE,
               markeredgewidth=0.8, label="v0.2.0 pre-fix service (re-measured, git-recovered)"),
        Line2D([], [], marker="o", linestyle="", markersize=3.4,
               markerfacecolor=C_PRE, markeredgecolor="white",
               markeredgewidth=0.4, label="default tool path (live)"),
        Line2D([], [], marker="o", linestyle="", markersize=3.4,
               markerfacecolor=C_POST, markeredgecolor="white",
               markeredgewidth=0.4, label="verbatim endpoint (live)"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.26),
              frameon=False, fontsize=FONT, ncols=3, handlelength=1.0,
              handletextpad=0.35, columnspacing=0.9, borderaxespad=0.0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3h_rnasmol_fidelity.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    for row in rows:
        print(f"{row['label'].splitlines()[0]}: v0.2.0 {row['hist']:.4f} | "
              f"tool_layer {row['tool'][0]} {tuple(row['tool'][1:])} | "
              f"endpoint {row['endpoint'][0]} {tuple(row['endpoint'][1:])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
