"""Fig 1b — Layer 4 multi-agent execution (181 × 44 mm).

Input (pipeline plan) -> PipelineAgent -> SpecialistAgent (runs one workflow:
generate -> evaluate -> score -> ASF rank) -> SynthesisAgent -> ClaimGate ->
output (ranked candidates + gated report). QualityAgent advises the
SpecialistAgent on a dotted advisory loop (it cannot fail a run).
"""
import style as S

W, H = 181, 44

Y0, Y1 = 21.0, 35.0  # main row card band


def build(B):
    B.txt(4, 41.0, "Layer 4 · multi-agent execution", size=6.5, weight="bold",
          ha="left")
    B.txt(177, 41.0, "zoom of panel a · layer L4", size=5.0, ha="right")

    # ---- input card ---------------------------------------------------------
    B.card(4, Y0, 22, Y1 - Y0, face=S.C_ROSE, alpha=0.20)
    B.txt(15, 31.6, "Pipeline plan", size=5.8, weight="bold")
    B.txt(15, 28.4, "single form or", size=5.0)
    B.txt(15, 25.9, "multi-node plan", size=5.0)
    B.txt(15, 23.4, "explicit workflow", size=5.0)

    # ---- agent cards ---------------------------------------------------------
    def agent(x, w, name, lines, face=S.C_MAUVE_PINK, dashed=False):
        B.card(x, Y0, w, Y1 - Y0, face=face, alpha=0.16, dashed=dashed)
        B.txt(x + w / 2, 31.6, name, size=5.8, weight="bold")
        for i, ln in enumerate(lines):
            B.txt(x + w / 2, 28.4 - i * 2.5, ln, size=5.0)

    agent(32, 26, "PipelineAgent", ["deterministic schedule", "0 LLM calls"])
    agent(109, 20, "SynthesisAgent", ["multi-node synthesis", "drafts the report"])

    # SpecialistAgent: runs the workflow — generate/evaluate/score/ASF rank chips
    B.card(64, Y0, 39, Y1 - Y0, face=S.C_MAUVE_PINK, alpha=0.16)
    B.txt(83.5, 31.9, "SpecialistAgent", size=5.8, weight="bold")
    B.txt(83.5, 29.6, "runs one workflow", size=5.0)
    steps = [("generate", 9.4, None), ("evaluate", 9.4, None),
             ("score", 7.0, None), ("ASF rank", 9.8, S.C_SAGE)]
    x = 65.0
    for name, wch, col in steps:
        B.card(x, 24.6, wch, 3.4, face=col or S.C_MAUVE_PINK,
               alpha=0.30 if col else 0.10, lw=0.4, radius=0.5)
        B.txt(x + wch / 2, 26.3, name, size=5.0,
              weight="bold" if col else "normal")
        x += wch + 0.6
    B.txt(83.5, 22.6, "retries hard failures only", size=5.0)

    # ClaimGate + output
    agent(135, 20, "ClaimGate", ["every claim checked", "vs capability evidence"],
          face=S.C_TERRACOTTA)
    B.card(161, Y0, 16, Y1 - Y0, face=S.C_SAND, alpha=0.24)
    B.icon("doc", 165.2, 31.2, 3.4, S.C_TERRACOTTA, lw=0.7)
    B.txt(170.6, 32.2, "Ranked", size=5.4, weight="bold")
    B.txt(170.6, 29.9, "candidates", size=5.4, weight="bold")
    B.txt(170.6, 26.6, "gated", size=5.0)
    B.txt(170.6, 24.3, "report", size=5.0)

    # ---- main execution arrows -------------------------------------------------
    for xa, xb in ((26.3, 31.7), (58.3, 63.7), (103.3, 108.7), (129.3, 134.7)):
        B.flow(xa, 28, xb, 28, kind="data", lw=1.1)
    B.flow(155.3, 28, 160.7, 28, kind="gate", lw=1.1)

    # ---- advisory QualityAgent loop --------------------------------------------
    B.card(68, 9.5, 30, 7.5, face=S.C_MAUVE_PINK, alpha=0.14, dashed=True)
    B.txt(83, 14.7, "QualityAgent", size=5.8, weight="bold")
    B.txt(83, 11.9, "advisory · cannot fail a run", size=5.0)
    B.flow(80.8, 17.3, 80.8, 20.7, kind="advisory", lw=0.8, ms=5)
    B.flow(85.2, 20.7, 85.2, 17.3, kind="advisory", lw=0.8, ms=5)

    # ---- arrow-semantics legend --------------------------------------------------
    B.flow(6, 5.2, 13, 5.2, kind="data", lw=1.0)
    B.txt(14.4, 5.2, "data flow", size=5.0, ha="left")
    B.flow(34, 5.2, 41, 5.2, kind="gate", lw=1.0)
    B.txt(42.4, 5.2, "governance", size=5.0, ha="left")
    B.flow(62, 5.2, 69, 5.2, kind="advisory", lw=1.0)
    B.txt(70.4, 5.2, "advisory", size=5.0, ha="left")
    B.txt(177, 5.2, "every agent action enters the audit trail", size=5.0,
          ha="right")


def main():
    fig, ax = S.canvas(W, H)
    build(S.MplBackend(ax))
    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "b")


if __name__ == "__main__":
    main()
