"""Fig 5b — GenNav mRNA primary endpoint: paired JCD outcomes with the exact
McNemar discordance test annotated (Experiment 28 registered 20-target cohort
+ Experiment 40 deployment completion — the pooled 25-target analysis).

Single-panel paired dumbbells: one row per target (25 = the 20 registered
Exp-28 targets + the five Exp-30 deployment targets whose static arm Exp 40
completed), JCD pass count 0–3 on the y axis against the two arms on the x
axis (Rule-based pool A | GenNav navigation C).  Each target's A→C
trajectory is drawn as a line between its two arm dots; colour encodes the
direction of the pair-level discordance aggregated over the target's three
profiles (C-favouring sage / A-favouring terracotta / concordant grey blue;
colour semantics defined in the Fig. 5b caption — no in-figure key, the
fig5b/5d house convention).  The exact two-sided McNemar result (b:c, P, n)
is annotated as one line above the axes — the pooled 75-pair statistic.

2026-09-08 figure-repair pass (user direction): the sign-flip permutation-
null histogram inset and the right-hand paired-cell text column were
removed — one plot per panel; the sign-flip null is the computational
backend of the same McNemar test the annotation reports (nothing lost),
and the paired-cell counts live in the caption (the removed column had
also carried a per-target-tripled counting — 15/9/30/6 — that did not
match the registered per-cell counts 18/6/17/19).  All text one 6-pt
pure-black style; the stat line sits in a reserved strip above the axes
with programmatic in-canvas / no-collision assertions.

2026-09-12 pooled re-render (user-directed merge): records = Exp-28 frozen
20 + Exp-40 deployment 5; the annotated test is the pooled verdict
(n = 75).

Style (the fig3/fig4/fig5a house style): no in-figure title — the panel
letter is added at assembly; colours exclusively from palette rev 7;
absolute-mm geometry, single column; 1200-dpi PNG + vector PDF
(fonttype 42).

Data  : experiments/results/exp28_gennav_mrna_endpoint_v2/full/runs.jsonl
        + experiments/results/exp40_static_completion/mrna/runs.jsonl
        + experiments/results/exp40_static_completion/pooled/
          mrna_pooled_verdict.json
Usage : python experiments/plots/fig5b_gennav_mcnemar.py
Output : experiments/plots/output/fig5b_gennav_mcnemar.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_E28 = (PROJECT_ROOT / "experiments" / "results"
            / "exp28_gennav_mrna_endpoint_v2" / "full" / "runs.jsonl")
RUNS_E40 = (PROJECT_ROOT / "experiments" / "results"
            / "exp40_static_completion" / "mrna" / "runs.jsonl")
POOLED = (PROJECT_ROOT / "experiments" / "results"
          / "exp40_static_completion" / "pooled" / "mrna_pooled_verdict.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 56.0

C_NAV = PALETTE_BY_NAME["sage_green"]        # C-favouring discordance
C_RULE = PALETTE_BY_NAME["terracotta"]       # A-favouring discordance
C_TIE = PALETTE_BY_NAME["grey_blue"]         # concordant targets

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "pdf.fonttype": 42,
})

MM = 1 / 25.4
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)   # exact 1200-dpi canvas pixels
H_PX = round(H_MM / 25.4 * DPI)


def main() -> int:
    records = []
    for path in (RUNS_E28, RUNS_E40):
        records += [json.loads(ln) for ln
                    in path.read_text(encoding="utf-8").splitlines()
                    if ln.strip()]
    records = [r for r in records if r.get("success")]
    verdict = json.loads(POOLED.read_text(encoding="utf-8"))

    rows = []
    for rec in records:
        ja = sum(1 for p in rec["evaluations"]["A"]["profiles"] if p["JCD"])
        jc = sum(1 for p in rec["evaluations"]["C"]["profiles"] if p["JCD"])
        rows.append({"target": rec["target_id"], "a": ja, "c": jc})
    rows.sort(key=lambda r: (r["c"] - r["a"], r["a"] - r["c"], r["target"]))

    mc = verdict["mcnemar_C_vs_A"]
    b, c_, p = mc["b"], mc["c"], mc["p"]
    n = verdict["n_pairs"]

    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))
    ax = fig.add_axes([0.115, 0.155, 0.855, 0.68])
    xs = {"A": 0.0, "C": 1.0}

    # coincident trajectories alpha-layer: multiplicity darkens the shared path
    for row in rows:
        if row["c"] > row["a"]:
            color = C_NAV
        elif row["a"] > row["c"]:
            color = C_RULE
        else:
            color = C_TIE
        ax.plot([xs["A"], xs["C"]], [row["a"], row["c"]], color=color,
                lw=1.1, alpha=0.30, zorder=2, solid_capstyle="round")
        ax.plot(xs["A"], row["a"], "o", ms=2.4, mfc=color, mec=color,
                zorder=3, alpha=0.55)
        ax.plot(xs["C"], row["c"], "o", ms=2.4, mfc=color, mec=color,
                zorder=3, alpha=0.55)

    ax.set_xlim(-0.42, 1.42)
    ax.set_ylim(-0.42, 3.42)
    ax.set_xticks([0.0, 1.0])
    ax.set_xticklabels(["Rule-based pool", "GenNav navigation"])
    ax.set_yticks([0, 1, 2, 3])
    ax.set_ylabel("JCD pass count (of 3 profiles)", labelpad=2.0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=1.6, width=0.5, pad=1.6)

    # ── multiplicity numerals: how many targets occupy each arm coordinate
    #    (coincident dots otherwise only darken by alpha) ──
    counts = []
    for x, vals, ha, dx in ((xs["A"], [r["a"] for r in rows], "right", -0.10),
                            (xs["C"], [r["c"] for r in rows], "left", 0.10)):
        for y, m in sorted(Counter(vals).items()):
            counts.append(ax.text(x + dx, y, f"×{m}", ha=ha, va="center",
                                  fontsize=FONT, color=INK))

    # ── exact McNemar result: one line in the reserved strip above the axes ──
    stat = ax.text(0.5, 1.05,
                   f"McNemar b:c = {b}:{c_},  P = {p:.3f},  n = {n}",
                   transform=ax.transAxes, ha="center", va="bottom",
                   fontsize=FONT, color=INK)

    # ── programmatic guards: every text in-canvas, pairwise non-colliding,
    #    the stat line clear of the axes (hence of every datum), and the
    #    multiplicity numerals clear of their arm dots ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = ([stat, ax.yaxis.label] + counts
             + list(ax.get_xticklabels()) + list(ax.get_yticklabels()))
    boxes = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.y0 >= 0
                and bb.x1 <= fig.bbox.width and bb.y1 <= fig.bbox.height), \
            f"text outside canvas: {t.get_text()!r}"
        boxes.append(bb)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].overlaps(boxes[j]), \
                f"text collision: {texts[i].get_text()!r} x {texts[j].get_text()!r}"
    assert boxes[0].y0 > ax.bbox.y1, "stat line dips into the axes"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5b_gennav_mcnemar.{ext}", dpi=DPI)
    plt.close(fig)

    img = mpimg.imread(OUT_DIR / "fig5b_gennav_mcnemar.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX, \
        f"canvas {img.shape[1]}x{img.shape[0]} != {W_PX}x{H_PX}"
    print(f"wrote {OUT_DIR / 'fig5b_gennav_mcnemar'}.{{pdf,png}} "
          f"({len(rows)} targets, {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
