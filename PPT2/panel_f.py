"""Fig 1f — RNADesign-210: two-level sunburst (family → workflow → task count).

Inner ring: five task families; outer ring: the eleven workflows (segment
angle ∝ task count, counts printed in-segment); side legend with the full
mapping; right badges: designed null models, literature anchors, 210/210
completion. 181 × 34 mm.
"""
import math
import style as S
from matplotlib.patches import Wedge, Circle

# (family label, family colour, [(workflow key, short, count)])
FAMILIES = [
    ("mRNA therapeutics", S.C_SAND, [
        ("mrna_cds_design", "CDS", 19),
        ("full_length_mrna_design", "full-length", 22),
        ("mrna_sequence_scoring", "scoring", 13)]),
    ("RNAi · CRISPR targeting", S.C_SLATE, [
        ("sirna_design", "siRNA", 22),
        ("sgrna_design", "sgRNA", 30)]),
    ("structure design", S.C_MAUVE_PINK, [
        ("rna_secondary_structure_design", "secondary", 25),
        ("rna_tertiary_structure_design", "tertiary", 20)]),
    ("aptamer · small molecule", S.C_GREY_BLUE, [
        ("rna_aptamer_design", "aptamer", 18),
        ("rna_small_molecule_interaction", "interaction", 15)]),
    ("screening · prediction", S.C_MAUVE_GREY, [
        ("aso_target_screening", "ASO", 14),
        ("ires_prediction", "IRES", 12)]),
]


def main():
    W, H = 181, 34
    fig, ax = S.canvas(W, H)
    cx, cy = 19.5, 17.2
    r_in0, r_in1, r_out0, r_out1 = 4.6, 7.4, 7.9, 11.0

    a0 = 90.0
    for fam, fcol, wfs in FAMILIES:
        fcount = sum(c for _, _, c in wfs)
        sweep = 360.0 * fcount / 210.0
        ax.add_patch(Wedge((cx, cy), r_in1, a0 - sweep, a0, facecolor=fcol,
                           alpha=0.85, edgecolor="white", lw=0.6, zorder=3))
        mid = math.radians(a0 - sweep / 2)
        S.txt(ax, cx + (r_in0 + r_in1) / 2 * math.cos(mid),
              cy + (r_in0 + r_in1) / 2 * math.sin(mid), str(fcount),
              size=5.0, weight="bold", color="#1A1A1A", zorder=5)
        for key, short, count in wfs:
            wsweep = 360.0 * count / 210.0
            ax.add_patch(Wedge((cx, cy), r_out1, a0 - wsweep, a0,
                               facecolor=S.WORKFLOW_COLORS[key], alpha=0.80,
                               edgecolor="white", lw=0.6, zorder=3))
            wmid = math.radians(a0 - wsweep / 2)
            S.txt(ax, cx + (r_out0 + r_out1) / 2 * math.cos(wmid),
                  cy + (r_out0 + r_out1) / 2 * math.sin(wmid), str(count),
                  size=5.0, weight="bold", color="#1A1A1A", zorder=5)
            a0 -= wsweep
        a0 -= 0.0
    ax.add_patch(Circle((cx, cy), r_in0 - 0.4, facecolor="white",
                        edgecolor="none", zorder=4))
    S.txt(ax, cx, cy + 0.9, "210", size=6.2, weight="bold", zorder=5)
    S.txt(ax, cx, cy - 1.7, "tasks", size=5.0, color=S.C_DARK, zorder=5)

    # ---- family legend --------------------------------------------------------
    lx, lw_card = 36.0, 54.0
    ly = 28.6
    for fam, fcol, wfs in FAMILIES:
        fcount = sum(c for _, _, c in wfs)
        S.card(ax, lx, ly - 2.4, lw_card, 4.8, face=fcol, alpha=0.12, lw=0.5,
               radius=0.6)
        ax.add_patch(Wedge((lx + 2.2, ly + 0.6), 1.30, -30, 90, width=0.7,
                           facecolor=fcol, alpha=0.85, edgecolor="none",
                           zorder=5))
        ax.add_patch(Wedge((lx + 2.2, ly + 0.6), 1.30, -150, -30, width=0.7,
                           facecolor=fcol, alpha=0.45, edgecolor="none",
                           zorder=5))
        S.txt(ax, lx + 4.6, ly + 1.1, fam, size=5.2, weight="bold", ha="left")
        S.txt(ax, lx + lw_card - 1.4, ly + 1.1, f"{fcount}", size=5.2,
              weight="bold", ha="right", color=S.C_DARK)
        sub = " · ".join(f"{short} {c}" for _, short, c in wfs)
        S.txt(ax, lx + 4.6, ly - 1.4, sub, size=5.0, color=S.C_DARK, ha="left")
        ly -= 5.35

    # ---- right badges ---------------------------------------------------------
    bx, bw = 92, 87
    cards = [
        (24.4, "designed null models", "wild-type · random-synonymous controls on every scoring task", "null"),
        (14.6, "literature anchors", "BNT162b2 UTRs · aptamer Kd sets · IRES panel · measured MRL library", "doc"),
        (4.8, "RNADesign-210 · 210/210 completed", "deterministic success criteria · doubles as the platform regression suite", "check"),
    ]
    cols = [S.C_GREY_GREEN, S.C_KHAKI, S.C_SAGE]
    for (by, title, sub, icon), col in zip(cards, cols):
        S.card(ax, bx, by, bw, 7.2, face=col, alpha=0.16)
        ty = by + 4.6
        if icon == "null":
            ax.add_patch(Circle((bx + 3.4, ty), 0.8, facecolor=S.C_SAGE,
                                edgecolor="none", zorder=5))
            ax.add_patch(Circle((bx + 5.4, ty), 0.8, facecolor=S.C_DARK,
                                edgecolor="none", zorder=5))
            tx0 = bx + 7.4
        elif icon == "doc":
            S.icon_doc(ax, bx + 4.2, ty, 3.4, col, lw=0.7)
            tx0 = bx + 7.4
        else:
            S.icon_check(ax, bx + 4.0, ty, 1.25, color=S.C_SAGE, lw=1.0)
            tx0 = bx + 7.4
        S.txt(ax, tx0, ty, title, size=5.4, weight="bold", ha="left")
        S.txt(ax, bx + 3.4, by + 1.8, sub, size=5.0, color=S.C_DARK, ha="left")

    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "f")


if __name__ == "__main__":
    main()
