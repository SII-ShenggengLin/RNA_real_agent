"""Fig 1a — End-to-end platform overview (181 × 50 mm).

Design goal (natural language) with all 11 workflow task chips -> seven-layer
platform spine (L6..L0, audit rail) -> ranked candidates + append-only audit
trail + gated report; two design-commitment badges at the bottom.
"""
import style as S

W, H = 181, 50

CHIPS = ["mRNA CDS", "full-length mRNA", "mRNA scoring", "siRNA", "sgRNA",
         "IRES", "aptamer", "ASO screen", "RNA secondary", "RNA tertiary",
         "small-molecule"]

LAYERS = [
    ("L6", "Entry", "CLI forms · FastAPI", S.C_MAUVE_GREY),
    ("L5", "Session", "memory · workspace", S.C_WARM_GREY),
    ("L4", "Agents", "pipeline · specialist · review · synthesis", S.C_MAUVE_PINK),
    ("L3", "Services", "21 microservices · health-checked", S.C_KHAKI),
    ("L2", "Workflows", "11 · generate → evaluate → score → rank", S.C_SAGE),
    ("L1", "Capabilities", "IO-validated · audit write-back", S.C_GREY_BLUE),
    ("L0", "Tools", "41 tools · 20 vendored codes", S.C_ROSE),
]


def build(B):
    # ---- background zones ---------------------------------------------------
    B.card(2, 8, 42, 40, face=S.C_ROSE, alpha=0.08, edge=False, radius=1.4)
    B.card(46, 8, 97, 40, face=S.C_GREY_BLUE, alpha=0.06, edge=False, radius=1.4)
    B.card(145, 8, 34, 40, face=S.C_MAUVE_GREY, alpha=0.08, edge=False, radius=1.4)

    # ---- input card: design goal + the 11 workflow task chips ---------------
    B.card(4, 12, 38, 34, face=S.C_ROSE, alpha=0.20)
    B.icon("person", 7.4, 43.4, 3.2, "#B0838C", lw=0.8)
    B.txt(10.0, 43.4, "Design goal · natural language", size=5.8, weight="bold",
          ha="left")
    chip_w, chip_h, gy = 17.6, 3.1, 0.8
    for i, name in enumerate(CHIPS):
        col, row = divmod(i, 6)
        x = 5.0 + col * 18.4
        y = 36.9 - row * (chip_h + gy)
        B.card(x, y, chip_w, chip_h, face=S.C_ROSE, alpha=0.14, lw=0.5,
               radius=0.6)
        B.txt(x + chip_w / 2, y + chip_h / 2, name, size=5.0)
    B.icon("rna", 32.6, 18.6, 3.4, "#B0838C", lw=0.7)
    B.txt(23.0, 15.0, "11 workflows", size=5.0, weight="bold")

    # ---- platform spine ------------------------------------------------------
    B.txt(48, 45.9, "RNADesignAgent platform", size=6.5, weight="bold", ha="left")
    B.txt(136, 45.9, "seven deterministic layers", size=5.0, ha="right")
    x0, x1 = 48, 136
    rh, gap, y_top = 4.35, 0.62, 43.4
    centers = []
    for i, (code, name, fact, col) in enumerate(LAYERS):
        y = y_top - rh - i * (rh + gap)
        c = y + rh / 2
        centers.append(c)
        B.card(x0, y, x1 - x0, rh, face=col, alpha=0.15, lw=0.7, radius=0.7)
        B.txt(x0 + 2.2, c, code, size=5.6, weight="bold", color=col, ha="left")
        B.txt(x0 + 6.6, c, name, size=5.8, weight="bold", ha="left")
        B.txt(x1 - 1.8, c, fact, size=5.0, ha="right")

    # ---- audit rail -----------------------------------------------------------
    rail_x = 138.3
    B.line(rail_x, centers[6], rail_x, centers[0], color=S.C_SLATE, lw=0.9)
    for c in centers:
        B.line(x1, c, rail_x, c, color=S.C_SLATE, lw=0.45)

    # ---- output cards -----------------------------------------------------------
    B.card(147, 36, 30, 8.5, face=S.C_GREY_BLUE, alpha=0.20)
    for k, f in enumerate((1.0, 0.68, 0.40)):
        B.line(149.8, 42.0 - k * 1.3, 149.8 + 4.6 * f, 42.0 - k * 1.3,
               color=S.C_GREY_BLUE, lw=1.1)
    B.txt(163.5, 40.2, "Ranked candidates", size=5.8, weight="bold")

    B.card(147, 24.5, 30, 8.5, face=S.C_MAUVE_GREY, alpha=0.20)
    B.icon("db", 152.2, 28.75, 4.8, S.C_MAUVE_GREY, lw=0.8)
    B.txt(164, 30.3, "Audit trail", size=5.8, weight="bold")
    B.txt(164, 27.3, "append-only", size=5.0)

    B.card(147, 13, 30, 8.5, face=S.C_SAND, alpha=0.24)
    B.icon("doc", 152.2, 17.25, 4.8, S.C_TERRACOTTA, lw=0.8)
    B.txt(164, 18.8, "Report", size=5.8, weight="bold")
    B.txt(164, 15.8, "claims gated", size=5.0)

    # ---- main arrows ---------------------------------------------------------
    B.flow(42.3, 29, 47.6, 29, kind="data", lw=1.2)
    B.flow(140.0, 40.2, 146.6, 40.2, kind="data", lw=1.1)
    B.flow(rail_x + 0.2, 28.7, 146.6, 28.7, kind="data", lw=1.1)
    B.flow(140.0, 17.2, 146.6, 17.2, kind="data", lw=1.1)

    # ---- design-commitment badges ---------------------------------------------
    B.card(48, 2.2, 44, 3.9, face=S.C_SLATE, alpha=0.12, lw=0.6, radius=0.7)
    B.icon("check", 50.8, 4.15, 1.05, S.C_SAGE, lw=0.9)
    B.txt(71, 4.15, "LLM never writes sequences", size=5.4, weight="bold")
    B.card(96, 2.2, 40, 3.9, face=S.C_SLATE, alpha=0.12, lw=0.6, radius=0.7)
    B.icon("check", 98.8, 4.15, 1.05, S.C_SAGE, lw=0.9)
    B.txt(117, 4.15, "pre-registered · budget-matched", size=5.4, weight="bold")


def main():
    fig, ax = S.canvas(W, H)
    build(S.MplBackend(ax))
    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "a")


if __name__ == "__main__":
    main()
