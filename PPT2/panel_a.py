"""Fig 1a — End-to-end cycle and the seven-layer platform spine (181 × 50 mm).

User design goal -> RNADesignAgent platform (L6..L0 spine, audit rail) ->
ranked candidates + append-only audit trail + gated report; iteration loop
returns to the goal; two design-commitment badges at the spine bottom.
"""
import style as S


def ranked_icon(ax, cx, cy, w, color, lw=0.7, zorder=6):
    for i, f in enumerate((1.0, 0.68, 0.40)):
        y = cy + 1.15 - i * 1.15
        ax.plot([cx - w / 2, cx - w / 2 + w * f], [y, y], color=color, lw=lw * 1.5,
                zorder=zorder, solid_capstyle="round")


def main():
    W, H = 181, 50
    fig, ax = S.canvas(W, H)

    # ---- zones -------------------------------------------------------------
    S.zone(ax, 2, 8, 30, 40, face=S.C_ROSE, alpha=0.10)
    S.zone(ax, 34, 7.2, 113, 41.5, face=S.C_GREY_BLUE, alpha=0.07)
    S.zone(ax, 149, 8, 30, 40, face=S.C_MAUVE_GREY, alpha=0.10)

    # ---- input card ---------------------------------------------------------
    S.card(ax, 3.5, 21, 27, 17, face=S.C_ROSE, alpha=0.22)
    S.icon_person(ax, 6.6, 34.6, 3.4, S.C_ROSE, lw=0.8)
    S.txt(ax, 12.5, 34.4, "Design goal", size=6.2, weight="bold", ha="left")
    S.txt(ax, 6.0, 31.6, "natural language", size=5.0, color=S.C_DARK, ha="left")
    for i, m in enumerate(("mRNA", "aptamer")):
        S.card(ax, 5.5 + i * 12.2, 26.8, 11.4, 3.4, face=S.C_ROSE, alpha=0.14, lw=0.5, radius=0.6)
        S.txt(ax, 5.5 + i * 12.2 + 5.7, 28.5, m, size=5.0)
    for i, m in enumerate(("siRNA", "sgRNA")):
        S.card(ax, 5.5 + i * 12.2, 22.4, 11.4, 3.4, face=S.C_ROSE, alpha=0.14, lw=0.5, radius=0.6)
        S.txt(ax, 5.5 + i * 12.2 + 5.7, 24.1, m, size=5.0)
    S.icon_rna(ax, 25.6, 33.6, 3.2, S.C_ROSE, lw=0.7)

    # ---- platform spine -----------------------------------------------------
    S.txt(ax, 38, 46.4, "RNADesignAgent platform", size=6.4, weight="bold",
          color=S.C_SLATE, ha="left")
    S.txt(ax, 76.5, 46.4, "seven deterministic layers", size=5.2, color=S.C_DARK,
          ha="left", style="italic")
    S.ref_chip(ax, 98.8, 46.4, "c")

    rows = [
        ("L6", "Entry", "CLI forms · FastAPI", S.C_MAUVE_GREY, None),
        ("L5", "Session", "memory · workspace", S.C_WARM_GREY, None),
        ("L4", "Agents", "pipeline · specialist · review · synthesis", S.C_MAUVE_PINK, "b"),
        ("L3", "Services", "21 microservices · health-checked", S.C_KHAKI, None),
        ("L2", "Workflows", "11 · generate → evaluate → score → rank", S.C_SAGE, "e"),
        ("L1", "Capabilities", "IO-validated · audit write-back", S.C_GREY_BLUE, None),
        ("L0", "Tools", "41 tools · 20 vendored codes", S.C_ROSE, None),
    ]
    x0, x1 = 38, 136
    rh, gap = 4.0, 0.5
    y_top = 44.6
    centers = []
    for i, (code, name, fact, col, ref) in enumerate(rows):
        y = y_top - rh - i * (rh + gap)
        c = y + rh / 2
        centers.append(c)
        S.card(ax, x0, y, x1 - x0, rh, face=col, alpha=0.16, lw=0.7, radius=0.7)
        S.txt(ax, x0 + 2.2, c, code, size=5.6, weight="bold", color=col, ha="left")
        S.txt(ax, x0 + 7.0, c, name, size=6.0, weight="bold", ha="left")
        S.txt(ax, x1 - 1.8, c, fact, size=5.2, ha="right")
        if ref:
            S.ref_chip(ax, x0 - 1.7, c, ref, r=1.05, color=col)

    # ---- audit rail ---------------------------------------------------------
    rail_x = 138.6
    S.plain_line(ax, (rail_x, centers[6]), (rail_x, centers[0]), color=S.C_SLATE, lw=0.9)
    for c in centers:
        S.plain_line(ax, (x1, c), (rail_x, c), color=S.C_SLATE, lw=0.45)
    S.txt(ax, rail_x + 1.35, 36.6, "every tool call", size=5.0, color=S.C_SLATE,
          rotation=90, va="center")

    # ---- output cards -------------------------------------------------------
    S.card(ax, 150.5, 36.5, 27, 8.5, face=S.C_GREY_BLUE, alpha=0.20)
    ranked_icon(ax, 155.5, 40.2, 5.2, S.C_GREY_BLUE)
    S.txt(ax, 170.5, 41.3, "Ranked", size=6.0, weight="bold", ha="center")
    S.txt(ax, 170.5, 38.9, "candidates", size=6.0, weight="bold", ha="center")

    S.card(ax, 150.5, 23.5, 27, 8.5, face=S.C_MAUVE_GREY, alpha=0.20)
    S.icon_db(ax, 155.5, 27.75, 4.6, 5.4, S.C_MAUVE_GREY, lw=0.8)
    S.txt(ax, 170.5, 28.3, "Audit trail", size=6.0, weight="bold")
    S.txt(ax, 170.5, 25.9, "append-only", size=5.2, color=S.C_DARK)

    S.card(ax, 150.5, 10.5, 27, 8.5, face=S.C_SAND, alpha=0.24)
    S.icon_doc(ax, 155.5, 14.75, 4.6, S.C_TERRACOTTA, lw=0.8)
    S.txt(ax, 170.5, 15.3, "Report", size=6.0, weight="bold")
    S.txt(ax, 170.5, 12.9, "claims gated", size=5.2, color=S.C_DARK)

    # main arrows
    S.flow(ax, (30.7, 29.5), (37.5, 29.5), kind="data", lw=1.2, ms=8)
    S.flow(ax, (146.8, 40.7), (150.1, 40.7), kind="data", lw=1.2, ms=8)
    S.flow(ax, (rail_x + 0.1, 27.7), (150.1, 27.7), kind="data", lw=1.0, ms=8)
    S.flow(ax, (146.8, 14.7), (150.1, 14.7), kind="data", lw=1.0, ms=8)

    # ---- design commitments --------------------------------------------------
    S.card(ax, 38, 8.8, 46, 3.9, face=S.C_SLATE, alpha=0.13, lw=0.6, radius=0.7)
    S.icon_check(ax, 40.6, 10.75, 1.05, color=S.C_SAGE, lw=0.9)
    S.txt(ax, 62.6, 10.75, "LLM never writes sequences", size=5.4, weight="bold")
    S.card(ax, 88, 8.8, 48, 3.9, face=S.C_SLATE, alpha=0.13, lw=0.6, radius=0.7)
    S.icon_check(ax, 90.6, 10.75, 1.05, color=S.C_SAGE, lw=0.9)
    S.txt(ax, 113.5, 10.75, "pre-registered · budget-matched comparisons",
          size=5.4, weight="bold")

    # ---- iteration loop ------------------------------------------------------
    S.flow(ax, (164, 9.2), (17.5, 9.2), kind="data", lw=1.0, ms=8, rad=-0.088)
    S.txt(ax, 90.5, 4.5, "iterate — review · refine", size=5.2, color=S.C_SLATE,
          style="italic")

    # ---- benchmark anchor (RNADesign-210 enters as design goals) -------------
    S.ref_chip(ax, 14.3, 13.6, "f")
    S.txt(ax, 15.8, 13.6, "RNADesign-210 · 210 tasks", size=5.0, color=S.C_DARK,
          ha="left", style="italic")

    S.save(fig, "a")


if __name__ == "__main__":
    main()
