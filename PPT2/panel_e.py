"""Fig 1e — GenNav: generation-layer constraint navigation.

Top: feasibility map over the 35-gear LinearDesign-λ lattice — three
pre-registered profile lanes (stability · λ≤2, balanced · 2<λ<8, expression ·
λ≥8); sage = feasible gear, open grey = infeasible, ringed = delivered
(5 per profile). Bottom: probe → allocate → deliver loop with the explicit
degrade path. 57 × 46 mm.
"""
import style as S
from matplotlib.patches import Circle

# schematic feasibility pattern over gear index 0..34 (λ 0 → 50):
# stability feasible at low λ, balanced mid, expression high — directionally
# as registered (λ-region affinity), delivered marks ringed.
LANES = [
    ("stability", "λ ≤ 2", (0, 12)),
    ("balanced", "2 < λ < 8", (13, 20)),
    ("expression", "λ ≥ 8", (21, 34)),
]


def main():
    W, H = 57, 46
    fig, ax = S.canvas(W, H)

    S.txt(ax, 2, 44.7, "GenNav — constraint navigation", size=6.2, weight="bold",
          color=S.C_SLATE, ha="left")

    # legend + aptamer note
    ax.add_patch(Circle((5.2, 42.4), 0.55, facecolor=S.C_SAGE, edgecolor="none"))
    S.txt(ax, 6.6, 42.4, "feasible", size=5.0, ha="left")
    ax.add_patch(Circle((14.4, 42.4), 0.55, facecolor="white", edgecolor=S.C_DARK,
                        lw=0.4))
    S.txt(ax, 15.8, 42.4, "infeasible", size=5.0, ha="left")
    ax.add_patch(Circle((25.4, 42.4), 0.62, facecolor=S.C_SAGE,
                        edgecolor=S.C_SLATE, lw=0.7))
    S.txt(ax, 27.0, 42.4, "delivered", size=5.0, ha="left")
    

    # ---- feasibility map ------------------------------------------------------
    S.zone(ax, 3, 20.5, 53, 20.5, face=S.C_KHAKI, alpha=0.10)
    x0, x1 = 20.5, 52.5
    n_gears = 35
    def gx(i):
        return x0 + (x1 - x0) * i / (n_gears - 1)

    lane_y = [37.4, 32.6, 27.8]
    delivered = {0: [1, 3, 5, 7, 9], 1: [14, 15, 17, 18, 19], 2: [22, 25, 28, 31, 33]}
    for li, (name, lam, (a, b)) in enumerate(LANES):
        y = lane_y[li]
        S.txt(ax, 18.8, y, f"{name}", size=5.0, ha="right", weight="bold")
        S.txt(ax, 18.8, y - 2.1, lam, size=5.0, ha="right", color=S.C_DARK)
        for gi in range(n_gears):
            cx, feasible = gx(gi), a <= gi <= b
            if feasible:
                ax.add_patch(Circle((cx, y), 0.42, facecolor=S.C_SAGE,
                                    edgecolor="none", zorder=4))
            else:
                ax.add_patch(Circle((cx, y), 0.34, facecolor="white",
                                    edgecolor=S.C_DARK, lw=0.35, zorder=4))
        for gi in delivered[li]:
            cx = gx(gi)
            ax.add_patch(Circle((cx, y), 0.62, facecolor="none",
                                edgecolor=S.C_SLATE, lw=0.65, zorder=5))

    # axis
    S.plain_line(ax, (x0, 22.6), (x1, 22.6), color=S.C_DARK, lw=0.5)
    for frac, lab in ((0.0, "λ = 0"), (1.0, "λ = 50")):
        xx = x0 + frac * (x1 - x0)
        S.plain_line(ax, (xx, 22.6), (xx, 22.15), color=S.C_DARK, lw=0.5)
        S.txt(ax, xx + (1.8 if frac else -1.8), 21.1, lab, size=5.0,
              ha="center" if frac else "center", color=S.C_DARK)
    S.txt(ax, x0, 19.2, "35-gear λ lattice", size=5.0, color=S.C_DARK,
          style="italic", ha="left")
    S.txt(ax, 53, 19.2, "aptamer: 25–80 nt", size=5.0, color=S.C_DARK,
          style="italic", ha="right")

    # ---- probe → allocate → deliver loop ---------------------------------------
    chips = ((3.4, "probe", "feasibility-first", S.C_GREY_BLUE),
             (21.0, "allocate", "35 raw · guarantee", S.C_KHAKI),
             (38.6, "deliver", "5/profile · D1 ≥ 0.03", S.C_SAGE))
    for xc, title, sub, col in chips:
        S.card(ax, xc, 10.2, 16.2, 5.8, face=col, alpha=0.20)
        S.txt(ax, xc + 8.1, 14.0, title, size=5.2, weight="bold")
        S.txt(ax, xc + 8.1, 11.7, sub, size=5.0, color=S.C_DARK)
    S.flow(ax, (19.7, 13.1), (20.9, 13.1), kind="data", lw=0.9, ms=7)
    S.flow(ax, (37.3, 13.1), (38.5, 13.1), kind="data", lw=0.9, ms=7)
    # cycle returns over the top of the chip row
    S.flow(ax, (46.0, 16.2), (12.0, 16.2), kind="data", lw=0.9, ms=7, rad=0.16)

    # degrade path
    S.card(ax, 8, 1.8, 41, 4.4, face=S.C_DARK, alpha=0.10, lw=0.5, radius=0.6)
    S.txt(ax, 28.5, 4.0, "no feasible gear → declared degrade", size=5.0,
          color=S.C_DARK)
    S.flow(ax, (29.1, 9.9), (29.1, 6.5), kind="advisory", lw=0.8, ms=6)

    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "e")


if __name__ == "__main__":
    main()
