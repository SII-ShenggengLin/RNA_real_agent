"""Fig 1d — GenNav: constraint navigation (181 × 42 mm).

Where it sits: the Layer-2 generation step (mRNA CDS and aptamer workflows).
Input: design profile (objective band · constraints · budget). Mechanism:
probe a generation-parameter lattice (CDS: LinearDesign λ, 35 gears; aptamer:
length 25–80 nt) feasibility-first -> allocate the raw-call budget across
bands -> deliver a per-band quota with a diversity floor, or declare degrade.
"""
import style as S

W, H = 181, 42

LANES = [("stability", "λ ≤ 2", 0, 12), ("balanced", "2 < λ < 8", 13, 20),
         ("expression", "λ ≥ 8", 21, 34)]
DELIVERED = {0: [1, 3, 5, 7, 9], 1: [14, 15, 17, 18, 19],
             2: [22, 25, 28, 31, 33]}
N_GEARS = 35
X0, X1 = 56.0, 140.0


def build(B):
    B.txt(4, 39.3, "GenNav · constraint navigation", size=6.5, weight="bold",
          ha="left")
    B.txt(40, 39.3, "Layer-2 generation step · mRNA CDS · aptamer", size=5.0,
          ha="left")

    # dot legend (top right)
    B.dot(102, 39.3, 0.55, face=S.C_SAGE)
    B.txt(103.6, 39.3, "feasible", size=5.0, ha="left")
    B.dot(114.5, 39.3, 0.55, face="white", edge=S.C_DARK, lw=0.4)
    B.txt(116.1, 39.3, "infeasible", size=5.0, ha="left")
    B.dot(128.5, 39.3, 0.62, face="white", edge=S.C_SLATE, lw=0.7)
    B.txt(130.3, 39.3, "delivered", size=5.0, ha="left")

    # ---- input: design profile ---------------------------------------------
    B.card(4, 10, 30, 26, face=S.C_ROSE, alpha=0.20)
    B.txt(19, 32.5, "Design profile", size=5.8, weight="bold")
    B.txt(19, 28.6, "objective band", size=5.0)
    B.txt(19, 26.0, "stability · balanced", size=5.0)
    B.txt(19, 23.4, "or expression", size=5.0)
    B.txt(19, 19.8, "constraints", size=5.0)
    B.txt(19, 16.2, "budget · 35 calls", size=5.0)

    # ---- mechanism: feasibility map over the parameter lattice --------------
    B.card(40, 17, 106, 18.5, face=S.C_KHAKI, alpha=0.08, edge=False,
           radius=1.4)

    def gx(i):
        return X0 + (X1 - X0) * i / (N_GEARS - 1)

    lane_y = [31.5, 27.7, 23.9]
    for li, (name, lam, a, b) in enumerate(LANES):
        y = lane_y[li]
        B.txt(54.0, y + 0.9, name, size=5.0, weight="bold", ha="right")
        B.txt(54.0, y - 1.5, lam, size=5.0, ha="right")
        for gi in range(N_GEARS):
            feasible = a <= gi <= b
            if feasible:
                B.dot(gx(gi), y, 0.42, face=S.C_SAGE)
            else:
                B.dot(gx(gi), y, 0.34, face="white", edge=S.C_DARK, lw=0.35)
        for gi in DELIVERED[li]:
            B.dot(gx(gi), y, 0.66, face="white", edge=S.C_SLATE, lw=0.65)

    B.line(X0, 21.2, X1, 21.2, color=S.C_DARK, lw=0.5)
    B.line(X0, 21.2, X0, 20.7, color=S.C_DARK, lw=0.5)
    B.line(X1, 21.2, X1, 20.7, color=S.C_DARK, lw=0.5)
    B.txt(X0, 19.9, "λ = 0", size=5.0)
    B.txt(X1, 19.9, "λ = 50", size=5.0)
    B.txt(98, 18.3, "generation-parameter lattice — CDS: LinearDesign λ "
          "(35 gears) · aptamer: length 25–80 nt", size=5.0)

    # ---- probe -> allocate -> deliver ----------------------------------------
    chips = ((44, 26, "probe", "feasibility-first"),
             (76, 30, "allocate", "35 raw calls"),
             (112, 30, "deliver", "5 per band · D1 ≥ 0.03"))
    for xc, wch, title, sub in chips:
        B.card(xc, 10, wch, 5.2, face=S.C_GREY_BLUE, alpha=0.18)
        B.txt(xc + wch / 2, 13.8, title, size=5.2, weight="bold")
        B.txt(xc + wch / 2, 11.5, sub, size=5.0)
    B.flow(70.3, 12.6, 75.7, 12.6, kind="data", lw=0.9)
    B.flow(106.3, 12.6, 111.7, 12.6, kind="data", lw=0.9)
    B.line(57, 16.7, 57, 15.5, color=S.C_SLATE, lw=0.6)

    # degrade path
    B.card(70, 3.2, 48, 4.4, face=S.C_DARK, alpha=0.10, lw=0.5, radius=0.6)
    B.txt(94, 5.4, "no feasible gear → declared degrade", size=5.0)
    B.flow(91, 9.7, 91, 7.9, kind="advisory", lw=0.8, ms=6)

    # ---- input/output arrows + output card -------------------------------------
    B.flow(34.3, 16.5, 43.7, 13.2, kind="data", lw=1.0)
    B.card(152, 10, 26, 26, face=S.C_SAGE, alpha=0.16)
    B.txt(165, 32.5, "Candidate set", size=5.8, weight="bold")
    B.txt(165, 28.6, "meets the band", size=5.0)
    B.txt(165, 26.0, "constraints", size=5.0)
    B.txt(165, 22.4, "quota per band", size=5.0)
    B.txt(165, 19.8, "diversity floor", size=5.0)
    B.txt(165, 16.2, "or declared degrade", size=5.0)
    B.flow(142.3, 12.6, 151.7, 12.6, kind="data", lw=1.0)


def main():
    fig, ax = S.canvas(W, H)
    build(S.MplBackend(ax))
    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "d")


if __name__ == "__main__":
    main()
