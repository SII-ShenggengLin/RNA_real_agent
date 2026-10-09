"""Fig 1c — CapGate: evidence gating (181 × 50 mm).

Where it sits: the DecisionGate guards the Layer-1 tool-execution choke
point, the ClaimGate guards Layer-4 outgoing claims. Upper evidence band:
verified anchor sets -> pre-registered profiling -> capability map. Lower
enforcement band: planned tool call -> DecisionGate verdicts; draft claim ->
ClaimGate scope row; every decision appended to the audit trail (shown as
example records).

2026-10-07 panel-c adjustment batch (user-directed; code fixed first, then
re-rendered):
* Anchor sets card: the bare "verified / 95 entries" text replaced by a
  small molecule-and-measured-value graphic (bead chain + value bar) plus
  "known measurements" / "95 molecules" — each anchor entry is one aptamer
  with a measured Kd (e1_anchor_set_v3.json), "entries" read as database
  jargon (follow-up);
* Profiling card narrowed 46 -> 28 mm and its three protocol lines centred
  (were left-aligned under a centred title);
* capability map: title centred on the card (was centred over the grid);
  the matrix is transposed — predictors head the columns, the three tasks
  (screening / ranking / docking) are the rows — and the grade legend moved
  to a horizontal row under the grid, de-crowding the card;
* planned tool call / draft claim cards: the cryptic subtitles ("via
  ToolExecutor", "agent or workflow") replaced by concrete centred examples
  ("e.g. call LinearDesign"; "e.g. 'candidate 1 is best'"; the
  prompt/speech-bubble glyphs tried in the same round were judged
  non-informative and removed, follow-up);
* DecisionGate caption "allow executes · unprofiled predictors blocked"
  deleted and the card shortened 11 -> 10 mm;
* audit-trail card: example records as a plain log ("gate allow" reworded
  "verdict allow", the Fig-4h "Gate verdicts" noun); the timeline with
  typed node glyphs tried in the same round was judged non-informative and
  removed (follow-up);
* bug fix: the profiling -> capability-map arrow ended 1.7 mm inside the
  map card (the shaft crossed the card edge); it now stops 0.3 mm short;
* follow-up 2: the audit-trail card narrowed 40 -> 32 mm from the right
  (its left edge keeps the gate-arrow geometry) and the whole panel content
  shifted +5 mm right — after the narrowing the content block (10..171 mm)
  carries balanced ~10 mm side margins.
"""
import style as S

W, H = 181, 50

# (predictor, [screening, ranking, docking]) — from the packaged capability
# map; drawn transposed (predictors as column heads, tasks as rows).
MATRIX = [
    ("MRL · 5′UTR", ["verified", "verified", "na"]),
    ("RNAsmol", ["verified", "failed", "na"]),
    ("RNASTOP", ["verified", "failed", "na"]),
    ("RhoFold · EGARPS", ["failed", "failed", "failed"]),
    ("GerNA-Bind", ["failed", "failed", "na"]),
]
TASKS = ("screening", "ranking", "docking")
TILE = {"verified": (S.C_SAGE, 0.55), "failed": (S.C_TERRACOTTA, 0.55),
        "na": (S.C_WARM_GREY, 0.20)}


def build(B):
    B.txt(9, 47.3, "CapGate · evidence gating", size=6.5, weight="bold",
          ha="left")
    tw = B.measure("CapGate · evidence gating", 6.5, "bold")
    B.txt(9 + tw + 1.4, 47.3, "(Layer-1 tool calls · Layer-4 claims)",
          size=6.5, ha="left")

    # ================= evidence band =================
    # anchor sets: molecules that come with known measurements
    B.card(10, 29.0, 30, 13.5, face=S.C_GREY_BLUE)
    B.txt(25, 40.1, "Anchor sets", size=5.8, weight="bold")
    for k, bw in enumerate((2.2, 3.6, 5.0)):
        y = 37.9 - 1.45 * k
        B.line(18.95, y, 24.75, y, color=S.C_SLATE, lw=0.7)
        for dx in (19.75, 21.85, 23.95):
            B.dot(dx, y, 0.32, face=S.C_SLATE)
        B.card(26.05, y - 0.55, bw, 1.1, face=S.C_GREY_BLUE, alpha=0.55,
               edge=False, radius=0.3)
    B.txt(25, 32.6, "known measurements", size=5.0)
    B.txt(25, 30.6, "95 molecules", size=5.0)

    # profiling protocols (centred; card sized to the widest line)
    B.card(44, 29.0, 28, 13.5, face=S.C_GREY_BLUE)
    B.txt(58, 39.9, "Profiling · pre-registered", size=5.8, weight="bold")
    for k, line in enumerate(("screening · AUROC > 0.8",
                              "ranking · ρ ≥ 0.6",
                              "docking · top-1 ≥ 2/3")):
        B.txt(58, 36.5 - 2.4 * k, line, size=5.0)

    # capability map — transposed matrix: predictors head columns
    B.card(78, 27.8, 87, 16.2, face=S.C_GREY_BLUE, lw=0.7)
    B.txt(121.5, 42.3, "capability map", size=5.8, weight="bold")
    tile_w, tile_h = 11.5, 1.7
    col_x = [93.8, 107.1, 120.4, 133.7, 147.0]
    for j, (name, _) in enumerate(MATRIX):
        parts = name.split(" · ")
        cx = col_x[j] + tile_w / 2
        if len(parts) == 2:
            B.txt(cx, 40.0, parts[0], size=5.0)
            B.txt(cx, 38.2, parts[1], size=5.0)
        else:
            B.txt(cx, 38.2, name, size=5.0)
    row_y = [35.8, 33.75, 31.7]
    for i, task in enumerate(TASKS):
        B.txt(92.3, row_y[i], task, size=5.0, ha="right")
        for j, (_, grades) in enumerate(MATRIX):
            col, alpha = TILE[grades[i]]
            B.card(col_x[j], row_y[i] - tile_h / 2, tile_w, tile_h, face=col,
                   alpha=alpha, edge=False, lw=0.3, radius=0.3)
    # grade legend — one horizontal row under the grid
    lx = 106.11
    for name, step in (("verified", 10.88), ("failed", 9.39),
                       ("unprofiled", 0.0)):
        col, alpha = TILE[{"unprofiled": "na"}.get(name, name)]
        B.card(lx, 28.6, 1.8, 1.6, face=col, alpha=alpha, edge=False,
               radius=0.3)
        B.txt(lx + 2.6, 29.4, name, size=5.0, ha="left")
        lx += step

    B.flow(40.3, 36.5, 43.7, 36.5, kind="data", lw=1.1)
    B.flow(72.3, 36.5, 77.7, 36.5, kind="data", lw=1.1)

    # ================= enforcement band =================
    # inputs — concrete centred examples
    B.card(10, 14, 30, 9.5, face=S.C_GREY_BLUE)
    B.txt(25, 20.9, "planned tool call", size=5.8, weight="bold")
    B.txt(25, 17.9, "e.g. call LinearDesign", size=5.0)

    B.card(10, 3.5, 30, 9.5, face=S.C_GREY_BLUE)
    B.txt(25, 10.5, "draft claim", size=5.8, weight="bold")
    B.txt(25, 7.5, "e.g. 'candidate 1 is best'", size=5.0)

    # DecisionGate
    B.card(49, 14.5, 82, 10, face=S.C_TERRACOTTA, lw=0.9)
    B.txt(90, 22.4, "DecisionGate · planned actions", size=5.8, weight="bold")
    verdicts = (("allow", 9.5, S.C_SAGE),
                ("downgrade", 13.0, S.C_WARM_GREY),
                ("reject", 9.0, S.C_TERRACOTTA),
                ("require-profiling", 20.0, S.C_DARK))
    x = 63.2
    for name, vw, col in verdicts:
        B.card(x, 16.9, vw, 3.4, face=col, edge=col, lw=0.7, radius=0.5)
        B.txt(x + vw / 2, 18.6, name, size=5.0)
        x += vw + 0.7

    # ClaimGate — the claim-scope ladder as one row (arrows = downgrade steps)
    B.card(49, 2.5, 82, 10, face=S.C_TERRACOTTA, lw=0.9)
    B.txt(90, 11.1, "ClaimGate · outgoing claims", size=5.8, weight="bold")
    ladder = (("absolute", 10.0, S.C_SAGE),
              ("same-target relative", 19.0, S.C_SAGE),
              ("trend-only", 9.5, S.C_WARM_GREY),
              ("suppressed", 12.0, S.C_DARK))
    x = 59.65
    for i, (name, lw_, col) in enumerate(ladder):
        B.card(x, 4.9, lw_, 2.9, face=col, edge=col, lw=0.7, radius=0.5)
        B.txt(x + lw_ / 2, 6.35, name, size=5.0)
        if i < 3:
            B.flow(x + lw_ + 0.3, 6.35, x + lw_ + 3.1, 6.35, kind="gate",
                   lw=0.8, ms=4.5)
        x += lw_ + 3.4

    # audit trail — example records
    B.card(139, 3.5, 32, 20, face=S.C_GREY_BLUE, lw=0.8)
    B.txt(155, 20.6, "audit trail", size=5.8, weight="bold")
    B.txt(155, 18.0, "one record per tool call", size=5.0)
    for k, line in enumerate(("10:21:03 · call LinearDesign",
                              "10:21:03 · verdict allow",
                              "10:21:04 · result CAI 0.91",
                              "10:21:05 · claim checked")):
        B.txt(142.5, 15.0 - 2.2 * k, line, size=5.0, ha="left")

    # flows: inputs -> gates; the map drives both gates; decisions are logged
    B.flow(40.3, 18.7, 48.7, 18.7, kind="data", lw=1.1)
    B.flow(40.3, 8.2, 48.7, 8.2, kind="data", lw=1.1)
    B.flow(117, 27.4, 117, 24.9, kind="data", lw=1.0)
    B.line(135, 27.4, 135, 7.8, color=S.C_SLATE, lw=0.9)
    B.flow(135, 7.8, 131.4, 7.8, kind="data", lw=1.0)
    B.flow(131.3, 18.5, 138.7, 18.5, kind="gate", lw=1.0)
    B.flow(131.3, 6.3, 138.7, 6.3, kind="gate", lw=1.0)


def main():
    fig, ax = S.canvas(W, H)
    build(S.MplBackend(ax))
    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "c")


if __name__ == "__main__":
    main()
