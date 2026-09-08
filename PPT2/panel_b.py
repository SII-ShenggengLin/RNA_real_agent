"""Fig 1b — The multi-agent execution layer (L4), every contribution measured.

PipelineAgent -> SpecialistAgent -> SynthesisAgent main line; advisory
QualityAgent loop (dotted); ClaimGate on outgoing claims; the falsified
coordination loop drawn struck-through. 121 × 46 mm.
"""
import style as S


def main():
    W, H = 121, 46
    fig, ax = S.canvas(W, H)

    S.txt(ax, 2, 43.6, "Layer 4 · multi-agent execution", size=6.4, weight="bold",
          color=S.C_SLATE, ha="left")
    S.txt(ax, 42, 43.6, "every agent's contribution measured", size=5.2,
          color=S.C_DARK, ha="left", style="italic")
    S.ref_chip(ax, 75.5, 43.6, "a")

    y0, y1 = 25.0, 38.0
    # input card
    S.card(ax, 2, y0, 18, y1 - y0, face=S.C_ROSE, alpha=0.20)
    S.txt(ax, 11, 34.9, "Pipeline plan", size=5.8, weight="bold")
    S.txt(ax, 11, 31.9, "single-node form", size=5.0, color=S.C_DARK)
    S.txt(ax, 11, 29.4, "multi-node plan", size=5.0, color=S.C_DARK)
    S.txt(ax, 11, 26.9, "explicit workflow", size=5.0, color=S.C_DARK)

    # agent cards
    def agent_card(x, w, name, role, third=None, dashed=False):
        S.card(ax, x, y0, w, y1 - y0, face=S.C_MAUVE_PINK, alpha=0.16,
               dashed=dashed)
        S.txt(ax, x + w / 2, 34.8, name, size=5.8, weight="bold")
        S.txt(ax, x + w / 2, 31.8, role, size=5.0, color=S.C_DARK)
        if third:
            S.txt(ax, x + w / 2, 29.0, third, size=5.0, color=S.C_DARK)

    agent_card(24, 22, "PipelineAgent", "deterministic schedule", "binding resolution")
    agent_card(50, 22, "SpecialistAgent", "strategy · retry", "hard failures only")
    agent_card(76, 22, "SynthesisAgent", "result synthesis", "drafts report")

    # ClaimGate card (governance colour)
    S.card(ax, 101, y0, 18, y1 - y0, face=S.C_TERRACOTTA, alpha=0.16)
    S.txt(ax, 110, 34.8, "ClaimGate", size=5.8, weight="bold")
    S.txt(ax, 110, 31.8, "claims vs evidence", size=5.0, color=S.C_DARK)
    S.txt(ax, 110, 29.0, "scope ladder", size=5.0, color=S.C_DARK)

    # measured chips under cards
    for x, w, t in ((24, 22, "0 LLM calls"), (49, 10.5, "no quality-driven"),
                    (49 + 11.5, 10.5, "retries")):
        pass
    S.card(ax, 24, 20.6, 22, 3.6, face=S.C_MAUVE_PINK, alpha=0.13, lw=0.5, radius=0.6)
    S.txt(ax, 35, 22.4, "0 LLM calls", size=5.0)
    S.card(ax, 49, 20.6, 10.5, 3.6, face=S.C_MAUVE_PINK, alpha=0.13, lw=0.5, radius=0.6)
    S.txt(ax, 54.2, 22.4, "retry: hard", size=5.0)
    S.card(ax, 60.5, 20.6, 11.5, 3.6, face=S.C_MAUVE_PINK, alpha=0.13, lw=0.5, radius=0.6)
    S.txt(ax, 66.2, 22.4, "failures only", size=5.0)
    S.card(ax, 76, 20.6, 22, 3.6, face=S.C_MAUVE_PINK, alpha=0.13, lw=0.5, radius=0.6)
    S.txt(ax, 87, 22.4, "multi-node reports", size=5.0)
    S.card(ax, 101, 20.6, 18, 3.6, face=S.C_TERRACOTTA, alpha=0.13, lw=0.5, radius=0.6)
    S.txt(ax, 110, 22.4, "absolute → relative", size=5.0)

    # main execution arrows
    for xa, xb in ((20.2, 23.7), (46.3, 49.7), (72.3, 75.7)):
        S.flow(ax, (xa, 31.5), (xb, 31.5), kind="data", lw=1.1, ms=8)
    S.flow(ax, (98.3, 31.5), (100.7, 31.5), kind="gate", lw=1.1, ms=8)

    # gated report output
    S.card(ax, 101, 40.6, 18, 4.6, face=S.C_SAND, alpha=0.26)
    S.icon_doc(ax, 105.2, 42.9, 3.2, S.C_TERRACOTTA, lw=0.7)
    S.txt(ax, 111.6, 42.9, "gated report", size=5.4, weight="bold")
    S.flow(ax, (110, 38.2), (110, 40.3), kind="data", lw=1.0, ms=7)

    # advisory QualityAgent loop
    S.card(ax, 48, 9.6, 26, 9.0, face=S.C_MAUVE_PINK, alpha=0.14, dashed=True)
    S.txt(ax, 61, 16.9, "QualityAgent", size=5.8, weight="bold")
    S.txt(ax, 61, 14.5, "advisory — cannot fail a run", size=5.0,
          color=S.C_DARK)
    S.txt(ax, 61, 12.2, "31/31 sessions identical", size=5.0, color=S.C_DARK)
    S.txt(ax, 61, 10.4, "(on · off · failing)", size=5.0, color=S.C_DARK)
    S.flow(ax, (66, 18.8), (66, 24.8), kind="advisory", lw=0.9, ms=7, both=True)

    # ASF ranking chip
    S.card(ax, 2, 9.6, 42, 9.0, face=S.C_SAGE, alpha=0.16)
    S.txt(ax, 23, 16.9, "ASF ranking", size=5.8, weight="bold")
    S.txt(ax, 23, 14.4, "reference-point multi-objective (5 of 11 workflows)",
          size=5.0, color=S.C_DARK)
    S.txt(ax, 23, 11.9, "LLM: tie arbitration only · Kendall τ = 1.0", size=5.0,
          color=S.C_DARK)

    # removed coordination loop (struck through)
    S.card(ax, 78, 2.4, 41, 5.4, face=S.C_DARK, alpha=0.10, lw=0.6, radius=0.7)
    S.icon_cross(ax, 81.0, 5.1, 1.05, color=S.C_DARK, lw=0.9)
    S.txt(ax, 98.5, 5.1, "coordination loop — removed:", size=5.2, weight="bold")
    S.txt(ax, 98.5, 2.9, "benefit falsified under budget matching", size=5.0,
          color=S.C_DARK)
    S.plain_line(ax, (83.5, 5.1), (113.5, 5.1), color=S.C_DARK, lw=0.55)

    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "b")


if __name__ == "__main__":
    main()
