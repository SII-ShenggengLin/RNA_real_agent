"""Fig 1a — End-to-end system overview (181 × 44 mm).

Input: one natural-language design goal with concrete requirements and the
protein it references (a sketch of the Spike amino-acid sequence — the
full-length mRNA is the designed output, not the input). System spine: the
seven layers L6..L0 with the audit rail. Outputs: ranked candidates, audit
trail, claim-gated report.

2026-10-07 third adjustment round (user-directed, six points on panel a;
code fixed first, then re-rendered):
* the person icon next to the title removed;
* the input sketch changed from the mRNA construct bar to the Spike protein
  sequence (bead chain with the true P0DTC2 N-terminus M F V L ···, label
  "Spike protein · 1,273 aa") — what is designed is the mRNA, so the input
  sketch is the protein; the chain line breaks around the omission, drawn as
  three small on-line dots, and the three trailing beads carry the true
  C-terminus H Y T (same-day follow-ups);
* input-card content re-laid vertically (the bottom void removed, top and
  bottom margins balanced at ~4 mm);
* the L4 row wording checked against the polished Overview ("orchestrates,
  reviews and synthesizes workflow runs") — "orchestrate · review ·
  synthesize" kept verbatim;
* "append-only" removed from the audit-trail output card (the Fig. 1 legend
  carries only "an audit trail");
* the three output arrows aligned: all leave the audit rail at the same x
  and meet their cards at the card centres.

2026-10-07 second adjustment batch (user-directed; code fixed first, then
re-rendered):
* whole figure: structural cards no longer carry a tinted fill — colour lives
  on the lines only (no grey haze); background zones removed;
* input card: the decorative stem-loop glyph replaced by a construct sketch
  (cap – 5′UTR – CDS · Spike – 3′UTR – poly(A) with AUG ··· UAA markers) plus
  the concrete requirements of the example goal (CAI ≥ 0.80 · high MRL ·
  GC 30–80% · homopolymer < 14 nt);
* output cards: the three decorative icons removed, text centred.
"""
import style as S

W, H = 181, 44

LAYERS = [
    ("L6", "Entry", "form-driven interface"),
    ("L5", "Session", "memory · workspace"),
    ("L4", "Agents", "orchestrate · review · synthesize"),
    ("L3", "Services", "21 microservices · health-checked"),
    ("L2", "Workflows", "11 · generation, evaluation, scoring, ranking"),
    ("L1", "Capabilities", "validates outputs · audit write-back"),
    ("L0", "Tools", "41 tools · uniform interface"),
]


def build(B):
    # ---- input card: one natural-language design goal ------------------------
    B.card(4, 6, 38, 34, face=S.C_GREY_BLUE, lw=0.9)
    B.txt(6.8, 34.7, "Design goal · natural language", size=5.8,
          weight="bold", ha="left")
    B.txt(23.0, 28.8, "“Design a full-length mRNA\n"
          "encoding the SARS-CoV-2 Spike protein”", size=5.0, style="italic")
    # input sketch: the Spike protein sequence (P0DTC2, 1,273 aa) — the
    # full-length mRNA is the designed output, the protein is the input
    B.txt(23.0, 24.1, "Spike protein · 1,273 aa", size=5.0)
    cy = 21.8
    B.txt(9.0, cy, "N", size=5.0)
    B.line(10.2, cy, 22.6, cy, color=S.C_SLATE, lw=0.8)
    B.line(26.2, cy, 35.0, cy, color=S.C_SLATE, lw=0.8)
    for bx, res in zip((12.0, 14.2, 16.4, 18.6, 20.8), "MFVFL"):
        B.dot(bx, cy, 0.55, face=S.C_SLATE)
        B.txt(bx, 19.8, res, size=5.0)
    for ex in (23.5, 24.4, 25.3):  # omission dots drawn on the chain line
        B.dot(ex, cy, 0.28, face=S.C_SLATE)
    for bx, res in zip((28.0, 30.2, 32.4), "HYT"):  # the true C-terminus
        B.dot(bx, cy, 0.55, face=S.C_SLATE)
        B.txt(bx, 19.8, res, size=5.0)
    B.txt(36.2, cy, "C", size=5.0)
    # concrete requirements carried with the goal
    B.txt(23.0, 16.1, "CAI ≥ 0.80 · high MRL", size=5.0)
    B.txt(23.0, 13.7, "GC 30–80% · homopolymer < 14 nt", size=5.0)
    B.txt(23.0, 11.3, "CDS stem ≤ 30 bp", size=5.0)

    # ---- system spine ---------------------------------------------------------
    B.txt(48, 39.9, "RNADesignAgent system", size=6.5, weight="bold", ha="left")
    B.txt(136, 39.9, "seven layers", size=5.0, ha="right")
    x0, x1 = 48, 136
    rh, gap, y_top = 4.35, 0.62, 37.4
    centers = []
    for i, (code, name, fact) in enumerate(LAYERS):
        y = y_top - rh - i * (rh + gap)
        c = y + rh / 2
        centers.append(c)
        B.card(x0, y, x1 - x0, rh, face=S.C_GREY_BLUE, lw=0.7, radius=0.7)
        B.txt(x0 + 2.2, c, code, size=5.6, weight="bold", color=S.C_SLATE,
              ha="left")
        B.txt(x0 + 6.6, c, name, size=5.8, weight="bold", ha="left")
        B.txt(x1 - 1.8, c, fact, size=5.0, ha="right")

    # ---- audit rail -------------------------------------------------------------
    rail_x = 138.3
    B.line(rail_x, centers[6], rail_x, centers[0], color=S.C_SLATE, lw=0.9)
    for c in centers:
        B.line(x1, c, rail_x, c, color=S.C_SLATE, lw=0.45)

    # ---- output cards -------------------------------------------------------------
    B.card(147, 30, 30, 8.5, face=S.C_GREY_BLUE, lw=0.8)
    B.txt(162, 34.25, "Ranked candidates", size=5.8, weight="bold")
    B.card(147, 18.5, 30, 8.5, face=S.C_GREY_BLUE, lw=0.8)
    B.txt(162, 22.75, "Audit trail", size=5.8, weight="bold")
    B.card(147, 7, 30, 8.5, face=S.C_GREY_BLUE, lw=0.8)
    B.txt(162, 12.8, "Report", size=5.8, weight="bold")
    B.txt(162, 9.8, "claim-gated", size=5.0)

    # ---- main arrows (all three leave the audit rail at the same x and meet
    # their cards at the card centres) -----------------------------------------
    B.flow(42.3, 23, 47.6, 23, kind="data", lw=1.2)
    for ay in (34.25, 22.75, 11.25):
        B.flow(rail_x + 0.2, ay, 146.6, ay, kind="data", lw=1.1)


def main():
    fig, ax = S.canvas(W, H)
    build(S.MplBackend(ax))
    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "a")


if __name__ == "__main__":
    main()
