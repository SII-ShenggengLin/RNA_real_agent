"""Fig 1c — CapGate: evidence gating (181 × 50 mm).

Where it sits: governs every Layer-0 tool call (DecisionGate) and every
Layer-4 outgoing claim (ClaimGate). Upper evidence band: assertion-curated
anchor sets -> pre-registered profiling -> SelfModel capability map. Lower
enforcement band: planned tool call -> DecisionGate verdicts; draft claim ->
ClaimGate scope ladder; every decision appended to the audit trail.
"""
import style as S

W, H = 181, 50

# (oracle row, [screening, ranking, docking]) — from the packaged SelfModel.
MATRIX = [
    ("MRL · 5′UTR", ["verified", "verified", "na"]),
    ("RNAsmol", ["verified", "failed", "na"]),
    ("RNASTOP", ["verified", "failed", "na"]),
    ("RhoFold · EGARPS", ["failed", "failed", "failed"]),
    ("GerNA-Bind", ["failed", "failed", "na"]),
]
TILE = {"verified": (S.C_SAGE, 0.55), "failed": (S.C_TERRACOTTA, 0.55),
        "na": (S.C_WARM_GREY, 0.20)}


def build(B):
    B.txt(4, 47.3, "CapGate · evidence gating", size=6.5, weight="bold",
          ha="left")
    B.txt(177, 47.3, "governs every Layer-0 tool call · every Layer-4 claim",
          size=5.0, ha="right")

    # ================= evidence band (offline) =================
    B.card(2, 27, 177, 18, face=S.C_KHAKI, alpha=0.07, edge=False, radius=1.4)

    B.card(5, 30.5, 26, 12, face=S.C_SAND, alpha=0.22)
    B.icon("doc", 9.2, 39.6, 3.2, S.C_TERRACOTTA, lw=0.7)
    B.txt(12.0, 39.8, "Anchor sets", size=5.8, weight="bold", ha="left")
    B.txt(18, 36.4, "assertion-curated", size=5.0)
    B.txt(18, 33.9, "v3 · 95 entries", size=5.0)

    B.card(37, 30.5, 38, 12, face=S.C_KHAKI, alpha=0.22)
    B.txt(56, 39.8, "Profiling · pre-registered", size=5.8, weight="bold")
    B.txt(56, 36.6, "screening — AUROC > 0.8", size=5.0)
    B.txt(56, 34.2, "ranking — ρ ≥ 0.6", size=5.0)
    B.txt(56, 31.8, "docking — top-1 ≥ 2/3", size=5.0)

    # SelfModel capability map
    B.card(81, 27.8, 95, 16.2, face=S.C_GREY_BLUE, alpha=0.14)
    B.txt(128.5, 42.0, "SelfModel · capability map", size=5.8, weight="bold")
    tile_w, tile_h = 7.0, 1.8
    col_x = [102, 110, 118]
    for j, cn in enumerate(("screening", "ranking", "docking")):
        B.txt(col_x[j] + tile_w / 2, 39.7, cn, size=5.0)
    row_y = [37.6, 35.5, 33.4, 31.3, 29.2]
    for i, (row, grades) in enumerate(MATRIX):
        B.txt(100.5, row_y[i], row, size=5.0, ha="right")
        for j, g in enumerate(grades):
            col, alpha = TILE[g]
            B.card(col_x[j], row_y[i] - tile_h / 2, tile_w, tile_h, face=col,
                   alpha=alpha, edge=False, lw=0.3, radius=0.3)
    # legend + notes
    B.card(130, 36.9, 1.8, 1.8, face=S.C_SAGE, alpha=0.55, edge=False,
           radius=0.3)
    B.txt(132.6, 37.8, "verified", size=5.0, ha="left")
    B.card(130, 34.5, 1.8, 1.8, face=S.C_TERRACOTTA, alpha=0.55, edge=False,
           radius=0.3)
    B.txt(132.6, 35.4, "failed", size=5.0, ha="left")
    B.card(130, 32.1, 1.8, 1.8, face=S.C_WARM_GREY, alpha=0.20, edge=False,
           radius=0.3)
    B.txt(132.6, 33.0, "unprofiled", size=5.0, ha="left")
    B.txt(146, 37.8, "transfer decay ×0.5", size=5.0, ha="left")
    B.txt(146, 35.4, "worst family poisons", size=5.0, ha="left")

    B.flow(31.3, 36.5, 36.7, 36.5, kind="data", lw=1.1)
    B.flow(75.3, 36.5, 80.7, 36.5, kind="data", lw=1.1)

    # ================= enforcement band (online) =================
    B.card(2, 2, 177, 23, face=S.C_TERRACOTTA, alpha=0.06, edge=False,
           radius=1.4)

    # inputs
    B.card(5, 14, 26, 9.5, face=S.C_GREY_BLUE, alpha=0.20)
    B.txt(18, 21.0, "planned tool call", size=5.8, weight="bold")
    B.txt(18, 18.2, "from any agent", size=5.0)
    B.txt(18, 15.8, "via ToolExecutor", size=5.0)
    B.card(5, 3.5, 26, 9.5, face=S.C_GREY_BLUE, alpha=0.20)
    B.txt(18, 10.6, "draft claim", size=5.8, weight="bold")
    B.txt(18, 7.8, "from SynthesisAgent", size=5.0)
    B.txt(18, 5.4, "or a workflow", size=5.0)

    # DecisionGate
    B.card(37, 14, 67, 10.5, face=S.C_TERRACOTTA, alpha=0.13)
    B.txt(70.5, 22.2, "DecisionGate · planned actions", size=5.8,
          weight="bold")
    verdicts = (("allow", 9.5, S.C_SAGE), ("downgrade", 13.0, S.C_SAND),
                ("reject", 9.0, S.C_TERRACOTTA),
                ("require profiling", 19.0, S.C_DARK))
    x = 39.5
    for name, vw, col in verdicts:
        B.card(x, 17.2, vw, 3.4, face=col, alpha=0.30, lw=0.4, radius=0.5)
        B.txt(x + vw / 2, 18.9, name, size=5.0)
        x += vw + 0.7
    B.txt(70.5, 15.5, "allow executes · never-profiled oracle blocked",
          size=5.0)

    # ClaimGate
    B.card(37, 2.8, 67, 10.5, face=S.C_TERRACOTTA, alpha=0.13)
    B.txt(70.5, 11.0, "ClaimGate · outgoing claims", size=5.8, weight="bold")
    ladder = (("absolute", 10.0, S.C_SAGE), ("target-relative", 16.0, S.C_SAND),
              ("trend", 8.5, S.C_KHAKI), ("suppressed", 12.5, S.C_DARK))
    x = 39.5
    for i, (name, lw_, col) in enumerate(ladder):
        B.card(x, 6.2, lw_, 3.4, face=col, alpha=0.30, lw=0.4, radius=0.5)
        B.txt(x + lw_ / 2, 7.9, name, size=5.0)
        if i < 3:
            B.flow(x + lw_ + 0.15, 7.9, x + lw_ + 1.75, 7.9, kind="gate",
                   lw=0.8, ms=6)
        x += lw_ + 2.0
    B.txt(70.5, 4.2, "over-reaching claim → downgraded one step", size=5.0)

    # audit trail
    B.card(150, 3.5, 26, 20, face=S.C_MAUVE_GREY, alpha=0.16)
    B.icon("db", 163, 18.6, 5.2, S.C_MAUVE_GREY, lw=0.8)
    B.txt(163, 14.4, "audit trail", size=5.8, weight="bold")
    B.txt(163, 11.6, "append-only", size=5.0)
    B.txt(163, 9.0, "every gate decision", size=5.0)
    B.txt(163, 6.6, "recorded", size=5.0)

    # gates consult the SelfModel; inputs reach the gates; decisions are logged
    B.flow(110, 27.6, 72, 24.9, kind="data", lw=1.0)
    B.line(120, 27.5, 120, 11, color=S.C_SLATE, lw=0.9)
    B.flow(120, 11, 104.3, 11, kind="data", lw=1.0)
    B.flow(31.3, 18.7, 36.7, 18.7, kind="data", lw=1.1)
    B.flow(31.3, 8.2, 36.7, 8.2, kind="data", lw=1.1)
    B.flow(104.3, 18.9, 149.7, 18.9, kind="gate", lw=1.0)
    B.flow(104.3, 7.9, 149.7, 7.9, kind="gate", lw=1.0)


def main():
    fig, ax = S.canvas(W, H)
    build(S.MplBackend(ax))
    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "c")


if __name__ == "__main__":
    main()
