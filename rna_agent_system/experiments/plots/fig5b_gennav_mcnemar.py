"""Fig 5b — GenNav mRNA primary endpoint: paired JCD outcomes and the
permutation-null discordance test (Experiment 27, paper registry E6).

Main panel — paired dumbbells: one row per target (20), JCD pass count
0–3 on the y axis against the two arms on the x axis (Rule-based pool A |
GenNav navigation C).  Each target's A→C trajectory is drawn as a line
between its two arm dots; colour encodes the direction of the pair-level
discordance aggregated over the target's three profiles (C-favouring sage /
A-favouring terracotta / concordant grey blue).  The b:c discordant counts
and the exact two-sided McNemar P are annotated as a text block (the
headline numbers also live in the Fig. 5b caption).

Inset — permutation-null histogram (the Robin Extended Data Fig. 4c /
fig3i convention): 10⁴ sign-flips of the observed discordant pairs'
directions under H₀ (b ~ Bin(b+c, 0.5)); the observed number of
C-favouring discordants is marked with a vertical line and tag.

Style (the fig3/fig4/fig5a house style): no in-figure title — the panel
letter is added at assembly; every text element one 6-pt pure-black style;
colours exclusively from palette rev 7; absolute-mm geometry, single
column; 1200-dpi PNG + vector PDF (fonttype 42).

Data  : experiments/results/exp28_gennav_mrna_endpoint_v2/full/
        {runs.jsonl, verdict.json}
Usage : python experiments/plots/fig5b_gennav_mcnemar.py
Output : experiments/plots/output/fig5b_gennav_mcnemar.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS = (PROJECT_ROOT / "experiments" / "results"
        / "exp28_gennav_mrna_endpoint_v2" / "full" / "runs.jsonl")
VERDICT = (PROJECT_ROOT / "experiments" / "results"
           / "exp28_gennav_mrna_endpoint_v2" / "full" / "verdict.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 76.0

C_NAV = PALETTE_BY_NAME["sage_green"]        # C-favouring discordance
C_RULE = PALETTE_BY_NAME["terracotta"]       # A-favouring discordance
C_TIE = PALETTE_BY_NAME["grey_blue"]         # concordant targets
C_BAR = PALETTE_BY_NAME["warm_grey"]         # null histogram
C_OBS = PALETTE_BY_NAME["terracotta"]        # observed marker (= favoured arm
#                                            of the re-measured direction; set
#                                            in code from the verdict)

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
    records = [json.loads(ln) for ln in RUNS.read_text(encoding="utf-8").splitlines()
               if ln.strip()]
    records = [r for r in records if r.get("success")]
    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    profiles = ["expression", "stability", "balanced"]

    rows = []
    for rec in records:
        ja = sum(1 for p in rec["evaluations"]["A"]["profiles"] if p["JCD"])
        jc = sum(1 for p in rec["evaluations"]["C"]["profiles"] if p["JCD"])
        rows.append({"target": rec["target_id"], "a": ja, "c": jc})
    rows.sort(key=lambda r: (r["c"] - r["a"], r["a"] - r["c"], r["target"]))

    mc = verdict["mcnemar_C_vs_A"]
    b, c_, p = mc["b"], mc["c"], mc["p"]

    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))
    ax = fig.add_axes([0.145, 0.115, 0.50, 0.855])
    xs = {"A": 0.0, "C": 1.0}

    # coincident trajectories alpha-layer: multiplicity darkens the shared path
    for i, row in enumerate(rows):
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
    ax.set_ylabel("JCD profiles passed (of 3)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=1.6, width=0.5, pad=1.6)

    # ── stats block: right-hand margin column, vertically centred;
    #    renderer-measured width under a canvas-overflow assert ──
    n_both = sum(1 for r in rows if r["a"] == 3 and r["c"] == 3)
    n_rule_only = sum(1 for r in rows if r["a"] > r["c"])
    n_nav_only = sum(1 for r in rows if r["c"] > r["a"])
    n_none = sum(1 for r in rows if r["a"] == 0 and r["c"] == 0)
    stats = (
        "paired cells\n"
        f"both pass   {n_both * 3:>2}\n"
        f"rule-only   {n_rule_only * 3:>2}\n"
        f"nav-only    {n_nav_only * 3:>2}\n"
        f"neither     {n_none * 3:>2}\n"
        "\n"
        f"b : c = {b} : {c_}\n"
        f"McNemar P = {p:.1e}\n"
        f"n = {verdict['n_pairs']}"
    )
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    t = fig.text(0.700, 0.50, stats, ha="left", va="center", fontsize=FONT,
                 color=INK, linespacing=1.55)
    bb = t.get_window_extent(renderer)
    right = bb.x1 / fig.bbox.width
    assert right < 0.995, f"stats block overflows canvas: {right:.3f}"

    # ── inset: permutation-null histogram of b (Robin EDF 4c convention) ──
    null = verdict["permutation_null"]
    hist = {int(k): v for k, v in null["null_b_histogram"].items()}
    observed = null["observed_b"]
    obs_color = C_NAV if b >= c_ else C_RULE

    ix, iy, iw, ih = 0.265, 0.615, 0.26, 0.26
    axi = fig.add_axes([ix, iy, iw, ih])
    ks = sorted(hist)
    axi.bar(ks, [hist[k] for k in ks], width=0.9, color=C_BAR,
            edgecolor=INK, linewidth=0.3)
    axi.axvline(observed, color=obs_color, lw=0.9)
    # observed tag at mid-height, offset away from the bar cluster, white-backed
    tag_x = observed + (0.12 * max(ks + [1]) if observed <= max(ks) / 2
                        else -0.12 * max(ks + [1]))
    axi.text(tag_x, 0.55, f"observed\n{observed}", ha="center", va="center",
             fontsize=FONT, color=INK, linespacing=1.3, zorder=8,
             bbox=dict(fc="white", ec="none", pad=0.8))
    axi.set_title("sign-flip null, 10,000 draws", fontsize=FONT, color=INK,
                  pad=2.0)
    axi.set_xlabel("C-favouring discordants", fontsize=FONT, color=INK,
                   labelpad=1.2)
    axi.tick_params(length=1.2, width=0.4, pad=1.0, labelsize=FONT)
    for s in axi.spines.values():
        s.set_linewidth(0.4)
    # white backdrop frame covering the inset + its title, above the dumbbells
    frame = FancyBboxPatch(
        (ix - 0.014, iy - 0.026), iw + 0.028, ih + 0.080,
        transform=fig.transFigure, boxstyle="round,pad=0.004",
        fc="white", ec=INK, lw=0.4, zorder=6)
    fig.patches.append(frame)
    axi.set_zorder(7)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5b_gennav_mcnemar.{ext}", dpi=1200)
    plt.close(fig)
    print(f"wrote {OUT_DIR / 'fig5b_gennav_mcnemar'}.{ext} ({len(rows)} targets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
