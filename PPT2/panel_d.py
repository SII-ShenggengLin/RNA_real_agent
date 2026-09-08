"""Fig 1d — CapGate: capability-layer evidence gating.

Top band (evidence): assertion-curated anchor sets -> pre-registered
profiling -> SelfModel capability map (tile matrix). Bottom band
(enforcement): DecisionGate on planned actions + ClaimGate on outgoing
claims (scope ladder), every decision appended to the audit trail.
121 × 46 mm.
"""
import style as S
from matplotlib.patches import Rectangle

# (oracle row, [screening, ranking, docking]) — verified/failed/na, from the
# packaged default SelfModel (gemorna MRL families verified; RNAsmol/RNASTOP
# verified screening, failed ranking; structure oracles failed; GerNA-Bind
# failed).
MATRIX = [
    ("MRL · 5′UTR", ["verified", "verified", "na"]),
    ("RNAsmol", ["verified", "failed", "na"]),
    ("RNASTOP", ["verified", "failed", "na"]),
    ("RhoFold · EGARPS", ["failed", "failed", "failed"]),
    ("GerNA-Bind", ["failed", "failed", "na"]),
]
TILE = {"verified": (S.C_SAGE, 0.55), "failed": (S.C_TERRACOTTA, 0.55),
        "na": (S.C_WARM_GREY, 0.18)}


def main():
    W, H = 121, 46
    fig, ax = S.canvas(W, H)

    S.txt(ax, 2, 44.7, "CapGate — profiled oracles · gated claims", size=6.4,
          weight="bold", color=S.C_SLATE, ha="left")

    # ================= top band: evidence =================
    # anchor sets
    S.card(ax, 2, 28, 22, 15, face=S.C_SAND, alpha=0.22)
    S.icon_doc(ax, 6.2, 39.2, 3.4, S.C_TERRACOTTA, lw=0.7)
    S.txt(ax, 15.6, 40.4, "Anchor sets", size=5.8, weight="bold")
    S.txt(ax, 13.0, 37.4, "assertion-curated", size=5.0, color=S.C_DARK)
    S.txt(ax, 13.0, 34.9, "v3 · 95 entries", size=5.0, color=S.C_DARK)
    S.icon_doc(ax, 7.6, 32.3, 2.6, S.C_SAND, lw=0.6)
    S.icon_doc(ax, 12.6, 32.3, 2.6, S.C_SAND, lw=0.6)
    S.icon_doc(ax, 17.6, 32.3, 2.6, S.C_SAND, lw=0.6)

    # profiling
    S.card(ax, 28, 28, 28, 15, face=S.C_KHAKI, alpha=0.22)
    S.txt(ax, 42, 40.4, "Profiling", size=5.8, weight="bold")
    for i, t in enumerate(("screening — AUROC > 0.8", "ranking — ρ ≥ 0.6",
                           "docking — top-1 ≥ 2/3")):
        S.card(ax, 30, 36.0 - i * 2.8, 24, 2.5, face=S.C_KHAKI, alpha=0.30,
               lw=0.4, radius=0.5)
        S.txt(ax, 42, 37.25 - i * 2.8, t, size=5.0)

    # SelfModel capability map
    S.card(ax, 60, 28, 58, 15, face=S.C_GREY_BLUE, alpha=0.14)
    S.txt(ax, 89, 40.4, "SelfModel · capability map", size=5.8, weight="bold")
    cols = ("screening", "ranking", "docking")
    for j, cn in enumerate(cols):
        S.txt(ax, 76.9 + j * 7.8, 38.4, cn, size=5.0, color=S.C_DARK)
    for i, (row, grades) in enumerate(MATRIX):
        y = 36.6 - i * 2.15
        S.txt(ax, 72.2, y, row, size=5.0, ha="right", color=S.C_DARK)
        for j, g in enumerate(grades):
            col, alpha = TILE[g]
            ax.add_patch(Rectangle((73.0 + j * 7.8, y - 0.85), 7.4, 1.7,
                                   facecolor=col, alpha=alpha, edgecolor="white",
                                   lw=0.3, zorder=4))
    S.txt(ax, 98.6, 36.3, "transfer decay ×0.5", size=5.0, ha="left",
          color=S.C_DARK)
    S.txt(ax, 98.6, 33.9, "worst family poisons", size=5.0, ha="left",
          color=S.C_DARK)
    ax.add_patch(Rectangle((98.6, 30.6), 1.6, 1.6, facecolor=S.C_SAGE,
                           alpha=0.55, edgecolor="none"))
    S.txt(ax, 100.8, 31.4, "verified", size=5.0, ha="left")
    ax.add_patch(Rectangle((98.6, 28.4), 1.6, 1.6, facecolor=S.C_TERRACOTTA,
                           alpha=0.55, edgecolor="none"))
    S.txt(ax, 100.8, 29.2, "failed", size=5.0, ha="left")
    ax.add_patch(Rectangle((110.0, 30.6), 1.6, 1.6, facecolor=S.C_WARM_GREY,
                           alpha=0.2, edgecolor="none"))
    S.txt(ax, 112.2, 31.4, "n.a.", size=5.0, ha="left")

    S.flow(ax, (24.2, 35.5), (27.7, 35.5), kind="data", lw=1.1, ms=8)
    S.flow(ax, (56.2, 35.5), (59.7, 35.5), kind="data", lw=1.1, ms=8)

    # ================= bottom band: enforcement =================
    # DecisionGate
    S.card(ax, 2, 2.4, 42, 17, face=S.C_TERRACOTTA, alpha=0.13)
    S.txt(ax, 23, 16.6, "DecisionGate · planned actions", size=5.8, weight="bold")
    S.txt(ax, 23, 14.3, "one choke point · every tool call", size=5.0,
          color=S.C_DARK, style="italic")
    verdicts = (("allow", 7.0, S.C_SAGE), ("downgrade", 8.6, S.C_SAND),
                ("reject", 7.0, S.C_TERRACOTTA), ("require profiling", 13.4, S.C_DARK))
    x = 3.8
    for name, vw, col in verdicts:
        S.card(ax, x, 9.6, vw, 3.4, face=col, alpha=0.30, lw=0.4, radius=0.5)
        S.txt(ax, x + vw / 2, 11.3, name, size=5.0)
        x += vw + 0.6
    S.icon_cross(ax, 6.8, 6.2, 1.0, color=S.C_TERRACOTTA, lw=0.9)
    S.txt(ax, 8.6, 6.2, "never-profiled oracle → blocked", size=5.0, ha="left")
    S.txt(ax, 23, 3.8, "11 governed oracles · 9 enforce · 2 pending", size=5.0,
          color=S.C_DARK)

    # ClaimGate
    S.card(ax, 48, 2.4, 42, 17, face=S.C_TERRACOTTA, alpha=0.13)
    S.txt(ax, 69, 16.6, "ClaimGate · outgoing claims", size=5.8, weight="bold")
    S.txt(ax, 69, 14.3, "no claim without verification", size=5.0,
          color=S.C_DARK, style="italic")
    ladder = (("absolute", 7.2, S.C_SAGE), ("target-relative", 11.4, S.C_SAND),
              ("trend", 6.6, S.C_KHAKI), ("suppressed", 8.2, S.C_DARK))
    x = 49.9
    for i, (name, lw_, col) in enumerate(ladder):
        S.card(ax, x, 9.6, lw_, 3.4, face=col, alpha=0.30, lw=0.4, radius=0.5)
        S.txt(ax, x + lw_ / 2, 11.3, name, size=5.0)
        if i < 3:
            S.flow(ax, (x + lw_ + 0.15, 11.3), (x + lw_ + 1.95, 11.3),
                   kind="gate", lw=0.8, ms=6)
        x += lw_ + 2.1
    S.txt(ax, 69, 6.2, "over-reaching claim → downgraded one step", size=5.0)
    S.txt(ax, 69, 3.8, "FP 54.5 → 0% · 33.3 → 7.7% · TP kept", size=5.0,
          color=S.C_DARK)

    # audit trail
    S.card(ax, 94, 2.4, 25, 17, face=S.C_MAUVE_GREY, alpha=0.16)
    S.icon_db(ax, 106.5, 13.2, 6.0, 6.6, S.C_MAUVE_GREY, lw=0.8)
    S.txt(ax, 106.5, 8.6, "audit trail", size=5.6, weight="bold")
    S.txt(ax, 106.5, 6.3, "append-only · every", size=5.0, color=S.C_DARK)
    S.txt(ax, 106.5, 4.3, "gate decision recorded", size=5.0, color=S.C_DARK)

    # gates consult the SelfModel; decisions land in the trail
    S.flow(ax, (66, 27.8), (30, 19.8), kind="data", lw=1.0, ms=7, rad=0.18)
    S.flow(ax, (88, 27.8), (66, 19.8), kind="data", lw=1.0, ms=7, rad=0.14)
    S.flow(ax, (90.2, 11.0), (93.7, 11.0), kind="gate", lw=1.0, ms=7)
    # elbow: DecisionGate decisions sweep under ClaimGate into the trail
    dashed = (0, (2.6, 1.6))
    ax.plot([12, 12, 103, 103], [2.1, 0.8, 0.8, 1.5], color=S.C_TERRACOTTA,
            lw=0.9, linestyle=dashed, zorder=4)
    ax.annotate("", xy=(103, 2.6), xytext=(103, 1.4),
                arrowprops=dict(arrowstyle="-|>", color=S.C_TERRACOTTA, lw=0.9,
                                linestyle=dashed), zorder=4)

    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "d")


if __name__ == "__main__":
    main()
