"""Fig 1d — GenNav: constraint navigation (181 × 42 mm).

Where it sits: the Layer-2 generation step. Input: a pre-registered design
profile (concrete constraints + call quota). Mechanism, one explanatory
graphic per step: probe tests a few of the generator's settings against the
constraint bar (mini bars on a settings axis) -> allocate spreads the call
quota over the feasible settings (stacked call counts) -> deliver returns a
batch of diverse sequences per profile — or the target is declared
infeasible.

2026-10-07 second adjustment batch (user-directed; code fixed first, then
re-rendered):
* all five cards share one band (y 16–36) — the three mechanism cards no
  longer sit lower than the input/output cards; the degrade card is aligned
  under the probe card (same x and width);
* step graphics redrawn so each step reads by itself: probe = a few settings
  tested on a settings axis, mini bars against the constraint threshold
  (sage dot = feasible, hollow = infeasible); allocate = the 35-call quota
  stacked over the three feasible settings (18/12/5 calls); deliver = five
  example sequences with a diversity bracket;
* input/output card text made concrete (CAI ≥ 0.80 · GC 30–80% ·
  homopolymer < 14 nt · quota 35 calls; 5 per profile · all constraints met
  · or declared infeasible);
* title annotation "(Layer-2 generation step)" right after the title in the
  same font size (measured placement); the dots-only legend retired (the new
  graphics are self-explanatory); structural fills retired figure-wide.

2026-10-07 sixth-round adjustment (user-directed, six points; code fixed
first, then re-rendered):
* probe: the axis title is centred under the axis ("generator setting",
  was right-aligned "generator settings"), and the graphic gained a
  two-line key so the marks decode — dash sample + "constraint", sage dot
  + "feasible", hollow dot + "infeasible" (the second batch's
  self-explanatory claim did not hold up for the reader);
* allocate: the bare numbers are decoded by the caption "3 feasible
  settings share the quota" (was "calls per feasible setting") — the dots
  are the three feasible settings, the numbers their call shares of the
  35-call quota;
* deliver: the five example sequences run longer with a mid-sequence
  ellipsis (9 + … + 4 nt) so they read as fragments of long sequences;
  the subtitle is "5 candidates · diversity threshold";
* candidate set: "5 per profile" spelt out as "5 candidates / per
  profile" on the input card's baselines — five lines fill the card, the
  bottom void is gone;
* degrade chip shrunk from probe width (34 mm) to text width
  (measure()-driven), still centred under the probe card with the dotted
  arrow (user-adjudicated: shrink in place, the branch stays visible);
* "diversity floor" → "diversity threshold" paper-wide (user-adjudicated):
  body §2.5 (two sites), Methods, the Fig. 1d legend, the fig5a panel tag
  and this panel; the Fig. 1d legend's "diversity minimum" aligned to the
  same term.

2026-10-07 sixth-round follow-up (user-directed, three points):
* probe: the dashed constraint line now spans the full axis (44–70, same
  extent as the solid settings axis);
* degrade chip back to the probe card's width (34 mm) with the two halves
  of the message on one line ("no feasible setting · declared
  infeasible", 31.1 mm measured — 1.5-mm side margins);
* deliver: the sequence block + diversity bracket + "diverse" label now
  centred on the card axis as one group (sequences at x = 132.8, the
  bracket measure()-driven off the widest row).
"""
import style as S

W, H = 181, 42

Y0, Y1 = 16.0, 36.0  # one shared card band


def build(B):
    B.txt(4, 39.3, "GenNav · constraint navigation", size=6.5, weight="bold",
          ha="left")
    tw = B.measure("GenNav · constraint navigation", 6.5, "bold")
    B.txt(4 + tw + 1.4, 39.3, "(Layer-2 generation step)", size=6.5,
          ha="left")

    # ---- input: design profile ---------------------------------------------
    B.card(4, Y0, 30, Y1 - Y0, face=S.C_GREY_BLUE, lw=0.9)
    B.txt(19, 32.4, "Design profile", size=5.8, weight="bold")
    B.txt(19, 29.2, "pre-registered", size=5.0)
    B.txt(19, 26.6, "CAI ≥ 0.80 · GC 30–80%", size=5.0)
    B.txt(19, 24.0, "homopolymer < 14 nt", size=5.0)
    B.txt(19, 21.4, "quota · 35 calls", size=5.0)

    # ---- probe: test a few settings against the constraint ------------------
    B.card(40, Y0, 34, Y1 - Y0, face=S.C_GREY_BLUE, lw=0.9)
    B.txt(57, 19.7, "probe", size=5.8, weight="bold")
    B.txt(57, 17.5, "find feasible settings", size=5.0)
    ax_y = 25.0
    B.line(44, ax_y, 70, ax_y, color=S.C_SLATE, lw=0.5)
    B.line(42, ax_y + 3.3, 72, ax_y + 3.3, color=S.C_DARK, lw=0.5,
           dash="dash")
    probed = {0: True, 2: True, 3: False, 5: True}
    for gi in range(7):
        gx = 44 + 4.33 * gi
        ok = probed.get(gi)
        if ok is None:
            B.dot(gx, ax_y, 0.26, face=S.C_WARM_GREY)
            continue
        bh = 4.6 if ok else 2.0
        col = S.C_SAGE if ok else S.C_DARK
        B.card(gx - 1.0, ax_y, 2.0, bh, face=col, edge=col, lw=0.6,
               radius=0.2)
        if ok:
            B.dot(gx, ax_y, 0.5, face=S.C_SAGE)
        else:
            B.dot(gx, ax_y, 0.45, face="white", edge=S.C_DARK, lw=0.35)
    B.txt(57, 22.6, "generator setting", size=5.0)
    # key: the dashed line is the constraint; sage dot feasible, hollow not
    w_con = B.measure("constraint", 5.0)
    xk = 57 - (3.2 + 1.0 + w_con) / 2
    B.line(xk, 33.9, xk + 3.2, 33.9, color=S.C_DARK, lw=0.5, dash="dash")
    B.txt(xk + 4.2, 33.9, "constraint", size=5.0, ha="left")
    w_f, w_i = B.measure("feasible", 5.0), B.measure("infeasible", 5.0)
    i1, i2 = 1.4 + w_f, 1.4 + w_i
    xk = 57 - (i1 + 2.6 + i2) / 2
    B.dot(xk + 0.45, 31.6, 0.5, face=S.C_SAGE)
    B.txt(xk + 1.4, 31.6, "feasible", size=5.0, ha="left")
    xk += i1 + 2.6
    B.dot(xk + 0.45, 31.6, 0.45, face="white", edge=S.C_DARK, lw=0.35)
    B.txt(xk + 1.4, 31.6, "infeasible", size=5.0, ha="left")

    # ---- allocate: spread the quota over the feasible settings ----------------
    B.card(80, Y0, 34, Y1 - Y0, face=S.C_GREY_BLUE, lw=0.9)
    B.txt(97, 19.7, "allocate", size=5.8, weight="bold")
    B.txt(97, 17.5, "quota across feasible settings", size=5.0)
    B.txt(97, 33.6, "quota · 35 calls", size=5.0)
    B.line(84, 32.3, 110, 32.3, color=S.C_SLATE, lw=0.6)
    B.line(84, 32.3, 84, 31.6, color=S.C_SLATE, lw=0.6)
    B.line(110, 32.3, 110, 31.6, color=S.C_SLATE, lw=0.6)
    for x0, x1, n in ((84, 97.4, "18"), (97.4, 106.3, "12"),
                      (106.3, 110, "5")):
        cx = (x0 + x1) / 2
        B.card(x0, 28.4, x1 - x0, 2.8, face=S.C_SAGE, edge=S.C_SAGE, lw=0.7,
               radius=0.3)
        B.txt(cx, 29.8, n, size=5.0)
        B.line(cx, 28.4, cx, 26.6, color=S.C_SAGE, lw=0.4)
        B.dot(cx, 26.0, 0.5, face=S.C_SAGE)
    B.txt(97, 23.9, "3 feasible settings share the quota", size=5.0)

    # ---- deliver: a diverse batch per profile -----------------------------------
    B.card(118, Y0, 34, Y1 - Y0, face=S.C_GREY_BLUE, lw=0.9)
    B.txt(135, 19.7, "deliver", size=5.8, weight="bold")
    B.txt(135, 17.5, "5 candidates · diversity threshold", size=5.0)
    rows = ("AUGCGUAAC…GCCU", "AUGGCACUG…UUCA", "AUGGUUACC…AGGA",
            "AUGCCGUAA…CUUG", "AUGAGCUCG…GAAC")
    w_seq = max(B.measure(s, 5.0) for s in rows)
    cx_seq = 135 - 2.2  # sequences + bracket + label centred on the card
    for k, seq in enumerate(rows):
        B.txt(cx_seq, 31.6 - 2.3 * k, seq, size=5.0)
    bx = cx_seq + w_seq / 2 + 1.5
    B.line(bx, 21.9, bx, 32.1, color=S.C_SLATE, lw=0.5)
    B.line(bx - 0.9, 32.1, bx, 32.1, color=S.C_SLATE, lw=0.5)
    B.line(bx - 0.9, 21.9, bx, 21.9, color=S.C_SLATE, lw=0.5)
    B.txt(bx + 2.0, 27.0, "diverse", size=5.0, rotation=90)

    # ---- probe -> allocate -> deliver ----------------------------------------
    B.flow(74.3, 26, 79.7, 26, kind="data", lw=0.9)
    B.flow(114.3, 26, 117.7, 26, kind="data", lw=0.9, ms=5)

    # degrade path (chip as wide as the probe card, one line)
    B.card(40, 5.0, 34, 5.4, face=S.C_DARK, edge=S.C_DARK, lw=0.6, radius=0.6)
    B.txt(57, 7.7, "no feasible setting · declared infeasible", size=5.0)
    B.flow(57, 15.7, 57, 10.7, kind="advisory", lw=0.8, ms=4.5)

    # ---- input/output arrows + output card -------------------------------------
    B.flow(34.3, 26, 39.7, 26, kind="data", lw=1.0)
    B.card(156, Y0, 23, Y1 - Y0, face=S.C_GREY_BLUE, lw=0.9)
    B.txt(167.5, 32.4, "Candidate set", size=5.8, weight="bold")
    B.txt(167.5, 29.2, "5 candidates", size=5.0)
    B.txt(167.5, 26.6, "per profile", size=5.0)
    B.txt(167.5, 24.0, "all constraints met", size=5.0)
    B.txt(167.5, 21.4, "or declared infeasible", size=5.0)
    B.flow(152.3, 26, 155.7, 26, kind="data", lw=1.0, ms=5)


def main():
    fig, ax = S.canvas(W, H)
    build(S.MplBackend(ax))
    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "d")


if __name__ == "__main__":
    main()
