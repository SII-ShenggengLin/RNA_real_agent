"""Fig 1b — Layer 4 multi-agent execution (181 × 44 mm).

Input (pipeline plan) -> PipelineAgent -> SpecialistAgent (runs one workflow:
generate, evaluate, score, ASF rank) -> SynthesisAgent -> ClaimGate ->
output (ranked candidates + gated report). QualityAgent advises the
SpecialistAgent on a dotted advisory loop.

2026-10-07 third adjustment batch (user-directed; code fixed first, then
re-rendered):
* input/output cards reworded and recoloured: the plan card reads
  "single-node or / multi-node / explicitly selected" (paper phrasing —
  Methods: "The user selects the workflow explicitly"); the two data-artifact
  cards (pipeline plan, ranked candidates) now carry a neutral warm-grey
  edge so the agent cards alone keep the grey-blue edge;
* PipelineAgent's description replaced by the legend-verbatim "schedules the
  pipeline" ("deterministic schedule" and "0 LLM calls" deleted);
* the ASF-rank chip no longer carries a bold face and a slate edge — all
  four workflow-step chips share one style;
* "retries hard failures only" and "advisory · cannot fail a run" deleted
  (both facts are carried by the Fig. 1 legend and the main text);
* the QualityAgent card is a solid-edged agent card like the others (the
  advisory semantics live on the dotted arrows and the legend);
* the arrowhead/shaft overlap on the short gate arrow and the dotted
  advisory arrows fixed at the shared style.flow level (shaft stops at the
  head's base, head drawn solid).

Same-day follow-ups: the arrow-semantics legend first became one centred
block, then — user: the QualityAgent's solo row read empty — moved up to
share the second row, centred in the free region right of the QualityAgent
card; the card itself is vertically centred in the band under the main row
(y 6.75–14.25, arrows 14.65–19.45).

2026-10-07 second adjustment batch (user-directed; code fixed first, then
re-rendered):
* advisory loop arrows: shafts lengthened and heads shrunk (QualityAgent card
  lowered, the two dotted arrows spread apart) — the arrowheads no longer
  overlap the dotted shafts;
* ClaimGate narrowed so the gate arrow to the output card gets a visible
  shaft;
* output-card icon removed, text centred; ASF-rank chip marked by a stronger
  edge and weight instead of a deeper fill (structural fills retired
  figure-wide, terracotta edge reserved for the ClaimGate).
"""
import style as S

W, H = 181, 44

Y0, Y1 = 21.0, 35.0  # main row card band


def build(B):
    B.txt(4, 41.0, "Layer 4 · multi-agent execution", size=6.5, weight="bold",
          ha="left")

    # ---- input card (a data artifact, not an agent: neutral grey edge) ------
    B.card(4, Y0, 22, Y1 - Y0, face=S.C_WARM_GREY)
    B.txt(15, 31.6, "Pipeline plan", size=5.8, weight="bold")
    B.txt(15, 28.4, "single-node or", size=5.0)
    B.txt(15, 25.9, "multi-node", size=5.0)
    B.txt(15, 23.4, "explicitly selected", size=5.0)

    # ---- agent cards ---------------------------------------------------------
    def agent(x, w, name, lines, face=S.C_GREY_BLUE, dashed=False):
        B.card(x, Y0, w, Y1 - Y0, face=face, dashed=dashed)
        B.txt(x + w / 2, 31.6, name, size=5.8, weight="bold")
        for i, ln in enumerate(lines):
            B.txt(x + w / 2, 28.4 - i * 2.5, ln, size=5.0)

    agent(32, 26, "PipelineAgent", ["schedules the pipeline"])
    agent(109, 20, "SynthesisAgent",
          ["multi-node synthesis", "drafts the report"])

    # SpecialistAgent: runs the workflow — generate/evaluate/score/ASF rank chips
    B.card(64, Y0, 39, Y1 - Y0, face=S.C_GREY_BLUE)
    B.txt(83.5, 31.9, "SpecialistAgent", size=5.8, weight="bold")
    B.txt(83.5, 29.6, "runs one workflow", size=5.0)
    steps = [("generate", 9.4), ("evaluate", 9.4), ("score", 7.0),
             ("ASF rank", 9.8)]
    x = 65.0
    for name, wch in steps:
        B.card(x, 24.6, wch, 3.4, face=S.C_GREY_BLUE, lw=0.4, radius=0.5)
        B.txt(x + wch / 2, 26.3, name, size=5.0)
        x += wch + 0.6

    # ClaimGate + output (the output is a data artifact: neutral grey edge)
    agent(135, 19, "ClaimGate", ["checks every claim", "before release"],
          face=S.C_TERRACOTTA)
    B.card(158, Y0, 19, Y1 - Y0, face=S.C_WARM_GREY)
    B.txt(167.5, 31.9, "Ranked", size=5.8, weight="bold")
    B.txt(167.5, 29.6, "candidates", size=5.8, weight="bold")
    B.txt(167.5, 26.8, "gated report", size=5.0)

    # ---- main execution arrows -------------------------------------------------
    for xa, xb in ((26.3, 31.7), (58.3, 63.7), (103.3, 108.7), (129.3, 134.7)):
        B.flow(xa, 28, xb, 28, kind="data", lw=1.1)
    B.flow(154.3, 28, 157.7, 28, kind="gate", lw=1.1, ms=5)

    # ---- advisory QualityAgent loop (a solid agent card like the others; ----
    # ---- the advisory semantics live on the dotted arrows and the legend) ----
    # ---- vertically centred in the band under the main row --------------------
    B.card(73.5, 6.75, 20, 7.5, face=S.C_GREY_BLUE)
    B.txt(83.5, 10.5, "QualityAgent", size=5.8, weight="bold")
    B.flow(80.0, 14.65, 80.0, 19.45, kind="advisory", lw=0.8, ms=4.5)
    B.flow(86.0, 19.45, 86.0, 14.65, kind="advisory", lw=0.8, ms=4.5)

    # ---- arrow-semantics legend — shares the second row, centred in the ------
    # ---- free region right of the QualityAgent card ---------------------------
    items = [("data", "data flow"), ("gate", "governance"),
             ("advisory", "advisory")]
    arrow_len, arrow_text_gap, item_gap = 7.0, 1.4, 10.0
    widths = [arrow_len + arrow_text_gap + B.measure(label, 5.0)
              for _, label in items]
    total = sum(widths) + item_gap * (len(items) - 1)
    lx = 98 + (177 - 98 - total) / 2
    for (kind, label), iw in zip(items, widths):
        B.flow(lx, 10.5, lx + arrow_len, 10.5, kind=kind, lw=1.0)
        B.txt(lx + arrow_len + arrow_text_gap, 10.5, label, size=5.0,
              ha="left")
        lx += iw + item_gap


def main():
    fig, ax = S.canvas(W, H)
    build(S.MplBackend(ax))
    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "b")


if __name__ == "__main__":
    main()
