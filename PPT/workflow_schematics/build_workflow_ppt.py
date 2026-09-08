#!/usr/bin/env python3
"""Workflow schematics for mrna_cds_design and full_length_mrna_design.

Two 16:9 slides, one per workflow, drawn with native PPT shapes (editable).
Logic verified against the current code (2026-09-07):
  - mrna_cds_design: GenNav-λ default (8 probe λ → ≤27 interstitial
    reinforcement, raw budget 35 → per-profile constraint-matrix delivery,
    3 profiles × 5, D1>=0.03, declared degrade) ; static pinned-engine recipe
    (LinearDesign λ{0,1,4,10} + RNARL + GEMORNA → 6) ; evaluate (CAI / MFE /
    GC / U / RNASTOP / unpaired) → total_score + Pareto(CAI↑, MFE/nt↓).
  - full_length_mrna_design: delegate CDS (≤15 navigated) → GEMORNA 5'/3'UTR
    ×3 presets → ≤135 constructs → evaluate (CDS metrics, junctions, full
    fold, MRL, 3'UTR stability, RNASTOP) → CapGate-assembled ASF ranking.

Reuses the Fig-1 drawing framework (Canvas + pptx/mpl backends, palette).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fig1"))
import build_fig1_ppt as F

Canvas = F.Canvas
PAL = F.PAL
INK = F.INK
CREAM = F.CREAM
CREAM_DK = F.CREAM_DK
lighten, darken, mix = F.lighten, F.darken, F.mix

SLIDE_W, SLIDE_H = 13.333, 7.5

# ------------------------------------------------------------------ glyphs --

def beads(c, x, y, letters, r=0.125, col=None):
    col = col or PAL["tan"]
    for i, ch in enumerate(letters):
        cx = x + i * 2.35 * r
        c.oval(cx - r, y - r, 2 * r, 2 * r, fill=lighten(col, 0.35),
               line=darken(col, 0.3), lw=0.8)
        c.text(cx - r, y - 0.085, 2 * r, 0.17, ch, size=7, bold=True)
    ex = x + len(letters) * 2.35 * r
    c.text(ex - 0.05, y - 0.10, 0.3, 0.2, "…", size=9, bold=True, color=darken(col, 0.3))


def cds_bar(c, x, y, w, h, col, ticks=4, label=None, lw=0.8, line=None):
    c.rect(x, y, w, h, fill=lighten(col, 0.45), line=line or col, lw=lw, radius=h / 2.5)
    for i in range(1, ticks + 1):
        tx = x + w * i / (ticks + 1)
        c.line([(tx, y + h * 0.22), (tx, y + h * 0.78)], color=col, lw=0.6, arrow="none")
    if label:
        c.text(x, y - 0.005, w, h, label, size=6.5, bold=True, color=darken(col, 0.35))


def gear(c, cx, cy, r, label, state):
    """state: feasible / infeasible / delivered"""
    fill = {"feasible": PAL["sage"], "infeasible": PAL["wgrey"],
            "delivered": PAL["sage"]}[state]
    line = PAL["mauve"] if state == "delivered" else darken(fill, 0.25)
    c.oval(cx - r, cy - r, 2 * r, 2 * r, fill=lighten(fill, 0.35), line=line,
           lw=1.8 if state == "delivered" else 0.8)
    c.text(cx - r, cy - 0.08, 2 * r, 0.16, label, size=6.4, bold=True)


def stage_badge(c, x, y, n, title, col=None, tsize=10.5):
    col = col or PAL["mauve"]
    c.oval(x, y, 0.30, 0.30, fill=col)
    c.text(x, y + 0.015, 0.30, 0.27, str(n), size=11, bold=True, color="#FFFFFF")
    c.text(x + 0.38, y + 0.015, 4.5, 0.27, title, size=tsize, bold=True, align="l")


def mini_rank_bars(c, x, y, n, bw, bh, col, gap=0.055):
    for i in range(n):
        cc = darken(col, 0.18 * (1 - i / max(n - 1, 1)))
        c.rect(x + i * (bw + gap), y, bw, bh, fill=lighten(cc, 0.45 - 0.06 * i),
               line=cc, lw=0.7, radius=bh / 3)
        c.text(x + i * (bw + gap), y - 0.005, bw, bh, str(i + 1), size=5.5,
               bold=True, color=darken(cc, 0.3))


def can_chip(c, x, y, text, w=1.6):
    c.can(x, y + 0.01, 0.18, 0.22, fill=PAL["dgrey"])
    c.text(x + 0.24, y, w - 0.24, 0.22, text, size=6.8, align="l", color="#333333")


def legend_row(c, y):
    x = 0.3
    c.line([(x, y + 0.08), (x + 0.35, y + 0.08)], color=PAL["slate"], lw=2.0)
    c.text(x + 0.40, y, 0.95, 0.16, "data flow", size=6.8, align="l")
    x += 1.45
    c.line([(x, y + 0.08), (x + 0.35, y + 0.08)], color=PAL["mauve"], lw=1.3, dash="dash")
    c.text(x + 0.40, y, 1.3, 0.16, "iteration / advisory", size=6.8, align="l")
    x += 1.85
    c.rect(x, y + 0.01, 0.14, 0.14, fill=PAL["terracotta"], radius=0.03)
    c.text(x + 0.19, y, 1.25, 0.16, "CapGate governance", size=6.8, align="l")
    x += 1.60
    c.rect(x, y + 0.01, 0.14, 0.14, fill=lighten(PAL["sage"], 0.45), line=PAL["sage"],
           lw=0.8, radius=0.03)
    c.text(x + 0.19, y, 1.15, 0.16, "delivered output", size=6.8, align="l")
    c.text(SLIDE_W - 3.6, y, 3.3, 0.16, "no LLM inside the workflow — advisory review sits at the agent layer",
           size=6.8, align="r", italic=True, color="#555555")


# ============================================================== slide 1: CDS

def slide_cds():
    items = []
    c = Canvas(items, 0, 0, 1.0)
    c.text(0.3, 0.18, 6.0, 0.35, "mRNA CDS design workflow", size=16, bold=True, align="l")
    c.text(9.0, 0.24, 4.05, 0.25, "RNADesignAgent · workflow detail (default path)",
           size=8, align="r", color="#555555")

    # ---- A: input ---------------------------------------------------------
    c.text(0.28, 0.92, 1.9, 0.2, "user input", size=8.5, bold=True, color="#555555")
    c.rect(0.25, 1.18, 1.95, 3.42, fill=lighten(PAL["tan"], 0.55), line=PAL["tan"],
           lw=1.1, radius=0.07)
    beads(c, 0.60, 1.62, "MAKTL", r=0.125)
    c.text(0.35, 1.90, 1.75, 0.2, "protein sequence", size=7.5)
    c.chip(0.42, 2.28, 1.62, 0.30, "species → codon table", "#FFFFFF", size=7.2,
           line=PAL["khaki"], lw=0.9)
    c.chip(0.42, 2.68, 1.62, 0.30, "N/C truncation (opt.)", "#FFFFFF", size=7.2,
           line=PAL["khaki"], lw=0.9)
    c.rect(0.42, 3.10, 1.62, 0.62, fill="#FFFFFF", line=PAL["mauve"], lw=1.0,
           dash="dash", radius=0.06)
    c.text(0.42, 3.16, 1.62, 0.5, "navigation unset\n→ GenNav-λ default", size=7.2, bold=True)
    c.line([(2.22, 2.90), (2.44, 2.90)], color=PAL["slate"], lw=2.4)

    # ---- B: generate (GenNav-λ) ------------------------------------------
    stage_badge(c, 2.55, 0.92, 1, "generate — GenNav-λ constraint navigation", col=PAL["khaki"])
    c.rect(2.47, 1.35, 3.95, 3.55, fill="#FFFFFF", line=PAL["khaki"], lw=1.3, radius=0.08)
    c.text(2.66, 1.44, 2.6, 0.18, "probe — 8 λ gears (feasibility)", size=7.5, bold=True, align="l")
    lam = ["0", "1", "2", "4", "8", "10", "20", "50"]
    feas = {"1", "2", "4", "8"}
    bars = [0.03, 0.11, 0.09, 0.13, 0.08, 0.04, 0.03, 0.02]
    for i, g in enumerate(lam):
        gx = 2.78 + i * 0.44
        gear(c, gx, 1.86, 0.155, g, "feasible" if g in feas else "infeasible")
        c.rect(gx - 0.10, 2.10, 0.20, bars[i], fill=PAL["sage"] if g in feas else PAL["wgrey"],
               radius=0.01)
    c.line([(2.62, 2.26), (6.30, 2.26)], color=PAL["dgrey"], lw=0.7, arrow="none")
    # reinforce row
    c.text(2.66, 2.42, 2.0, 0.18, "reinforce — +27 interstitial λ",
           size=7.5, bold=True, align="l")
    for i in range(3):
        c.oval(2.95 + i * 0.40, 2.70, 0.17, 0.17, fill="none", line=PAL["mauve"],
               lw=1.1, dash="dash")
    c.line([(4.05, 2.78), (5.9, 2.78)], color=PAL["mauve"], lw=1.1, dash="dash", arrow="none")
    c.line([(6.15, 2.70), (6.25, 2.05)], color=PAL["mauve"], lw=1.1, dash="dash")
    c.chip(4.75, 2.42, 1.55, 0.28, "≤ 35 calls — rule-arm budget", CREAM_DK, size=6.6, bold=True)
    can_chip(c, 2.66, 3.06, "every LinearDesign / CAI / fold call audited", w=3.6)
    # candidate pool
    for i in range(3):
        cds_bar(c, 2.80, 3.48 + i * 0.24, 1.05, 0.15, PAL["lav"], ticks=3)
    c.text(4.05, 3.62, 2.3, 0.2, "λ-tagged candidate pool", size=7.2, align="l")
    c.line([(6.44, 2.00), (6.66, 2.00)], color=PAL["slate"], lw=2.4)

    # ---- C: deliver -------------------------------------------------------
    stage_badge(c, 6.77, 0.92, 2, "deliver — matrix × 3 profiles", col=PAL["khaki"])
    # constraint wall
    wall = ["CAI ≥ 0.80", "GC 0.30–0.80", "homopolymer < 14", "stem ≤ 30 bp"]
    for i, wtxt in enumerate(wall):
        c.chip(6.74, 1.42 + i * 0.35, 1.34, 0.28, wtxt, "#FFFFFF", size=6.8, bold=True,
               line=PAL["terracotta"], lw=0.9)
    c.text(6.74, 2.82, 1.75, 0.32, "stability / balanced\nadd MFE/nt caps", size=6.2,
           align="l", italic=True, color="#555555", spacing=0.95)
    # pass / fail glyphs
    cds_bar(c, 8.22, 1.50, 0.52, 0.13, PAL["sage"], ticks=2)
    c.text(8.78, 1.47, 0.2, 0.18, "✓", size=8, bold=True, color=darken(PAL["sage"], 0.25))
    cds_bar(c, 8.22, 1.78, 0.52, 0.13, PAL["sage"], ticks=2)
    c.text(8.78, 1.75, 0.2, 0.18, "✓", size=8, bold=True, color=darken(PAL["sage"], 0.25))
    cds_bar(c, 8.22, 2.06, 0.52, 0.13, PAL["wgrey"], ticks=2)
    c.text(8.78, 2.03, 0.2, 0.18, "✗", size=8, bold=True, color=PAL["terracotta"])
    # filtered survivors drop into the per-profile delivery rows
    c.line([(8.60, 2.35), (8.60, 3.20)], color=PAL["slate"], lw=1.8)
    # profile rows
    profs = [("expression", "CAI-led", PAL["mauve"]),
             ("stability", "MFE-led", PAL["gblue"]),
             ("balanced", "mixed", PAL["khaki"])]
    for j, (pname, ptag, pcol) in enumerate(profs):
        py = 3.28 + j * 0.46
        c.text(6.74, py - 0.02, 0.86, 0.30, f"{pname}\n({ptag})", size=6.6, bold=True,
               align="l", spacing=0.9)
        mini_rank_bars(c, 7.68, py, 5, 0.30, 0.17, pcol)
    c.text(7.68, 4.52, 1.75, 0.18, "↔ D1 ≥ 0.03 diversity", size=6.4, align="l",
           color="#555555")
    c.chip(6.74, 4.86, 1.70, 0.26, "else: declared degrade", "#FFFFFF", size=6.4,
           line=PAL["dgrey"], lw=0.9, dash="dash")
    c.line([(9.46, 3.74), (9.68, 3.74)], color=PAL["slate"], lw=2.4)

    # ---- D: evaluate & score ---------------------------------------------
    stage_badge(c, 9.79, 0.92, 3, "evaluate & score", col=PAL["gblue"])
    mets = ["CAI", "MFE / fold", "GC %", "U %", "RNASTOP", "unpaired"]
    for i, m in enumerate(mets):
        mx = 9.74 + (i % 2) * 0.80
        my = 1.42 + (i // 2) * 0.47
        c.rect(mx, my, 0.74, 0.40, fill=lighten(PAL["gblue"], 0.55), line=PAL["gblue"],
               lw=0.8, radius=0.05)
        c.text(mx, my + 0.02, 0.74, 0.36, m, size=6.8, bold=True)
    c.oval(10.02, 3.05, 0.62, 0.62, fill=lighten(PAL["gblue"], 0.35), line=PAL["gblue"], lw=1.1)
    c.text(10.02, 3.13, 0.62, 0.46, "total\nscore", size=7, bold=True)
    # pareto mini plot
    ax0, ay1, ax1, ay0 = 9.86, 4.42, 11.16, 3.92
    c.line([(ax0, ay1), (ax1, ay1)], color="#333333", lw=0.9, arrow="end", arrowhead=0.05)
    c.line([(ax0, ay1), (ax0, ay0)], color="#333333", lw=0.9, arrow="end", arrowhead=0.05)
    pts = [(10.0, 4.30), (10.2, 4.18), (10.45, 4.10), (10.7, 4.04), (10.95, 4.00), (10.35, 4.28), (10.8, 4.14)]
    for px, py in pts:
        c.oval(px - 0.03, py - 0.03, 0.06, 0.06, fill=PAL["gblue"])
    c.line([(10.0, 4.30), (10.45, 4.10), (10.95, 4.00)], color=PAL["terracotta"], lw=1.2, arrow="none")
    c.text(9.80, 4.48, 1.45, 0.15, "Pareto: CAI × MFE/nt", size=6.2, color="#555555")
    c.line([(11.28, 3.30), (11.50, 3.30)], color=PAL["slate"], lw=2.4)

    # ---- E: ranked output -------------------------------------------------
    stage_badge(c, 11.61, 0.92, 4, "ranked output", col=PAL["sage"])
    c.rect(11.53, 1.42, 1.55, 2.55, fill=lighten(PAL["sage"], 0.62), line=PAL["sage"],
           lw=1.1, radius=0.07)
    for i, cai_v in enumerate((".93", ".90", ".87")):
        ry = 1.58 + i * 0.48
        cds_bar(c, 11.66, ry, 0.78, 0.16, PAL["sage"], ticks=3)
        c.text(12.50, ry - 0.03, 0.5, 0.2, f"#{i + 1}", size=7.5, bold=True, align="l")
        c.text(12.50, ry + 0.15, 0.55, 0.16, f"CAI {cai_v}", size=6.0, align="l",
               color="#555555")
    c.text(12.88, 1.52, 0.2, 0.2, "★", size=10, bold=True, color=PAL["terracotta"])
    c.text(11.66, 3.02, 1.3, 0.2, "up to 15 = 3 × 5", size=6.8, color="#555555")
    can_chip(c, 11.66, 4.15, "audited trace", w=1.3)

    # ---- bottom: static alternative --------------------------------------
    c.rect(0.25, 5.30, 12.83, 0.72, fill="#FFFFFF", line=PAL["dgrey"], lw=1.0,
           dash="dash", radius=0.07)
    c.text(0.45, 5.40, 3.2, 0.2, "static recipe (pinned engine / navigation=false)",
           size=7.5, bold=True, align="l")
    for i, g in enumerate(["0", "1", "4", "10"]):
        gear(c, 0.70 + i * 0.34, 5.83, 0.13, g, "feasible")
    c.text(2.15, 5.72, 0.65, 0.2, "λ ×4", size=6.8, align="l")
    c.chip(2.85, 5.70, 1.05, 0.28, "LinearDesign", lighten(PAL["gblue"], 0.5), size=6.8, bold=True)
    c.chip(4.00, 5.70, 0.80, 0.28, "RNARL", lighten(PAL["gblue"], 0.5), size=6.8, bold=True)
    c.chip(4.90, 5.70, 0.95, 0.28, "GEMORNA", lighten(PAL["gblue"], 0.5), size=6.8, bold=True)
    c.text(5.95, 5.72, 1.3, 0.2, "→ 6 candidates,", size=7.2, align="l")
    c.line([(7.30, 5.84), (8.05, 5.84)], color=PAL["slate"], lw=1.8)
    c.text(8.15, 5.72, 4.6, 0.2, "same evaluate → score → rank path as above",
           size=7.5, align="l", bold=True)

    legend_row(c, 7.08)
    return items


# ====================================================== slide 2: full-length

def slide_full():
    items = []
    c = Canvas(items, 0, 0, 1.0)
    c.text(0.3, 0.18, 7.5, 0.35, "full-length mRNA design workflow", size=16, bold=True, align="l")
    c.text(9.0, 0.24, 4.05, 0.25, "RNADesignAgent · workflow detail (default path)",
           size=8, align="r", color="#555555")

    # ---- row 1: input -> CDS -> UTR -> assemble ---------------------------
    # A: input
    c.text(0.28, 0.92, 1.9, 0.2, "user input", size=8.5, bold=True, color="#555555")
    c.rect(0.25, 1.18, 1.85, 2.42, fill=lighten(PAL["tan"], 0.55), line=PAL["tan"],
           lw=1.1, radius=0.07)
    beads(c, 0.55, 1.58, "MAKTL", r=0.115)
    c.text(0.33, 1.84, 1.7, 0.18, "protein sequence", size=7.2)
    c.chip(0.37, 2.14, 1.62, 0.27, "species → codon table", "#FFFFFF", size=6.8,
           line=PAL["khaki"], lw=0.9)
    c.chip(0.37, 2.48, 1.62, 0.27, "UTR mode: short/med/long", "#FFFFFF", size=6.8,
           line=PAL["khaki"], lw=0.9)
    c.chip(0.37, 2.82, 1.62, 0.27, "reference point (opt.)", "#FFFFFF", size=6.8,
           line=PAL["khaki"], lw=0.9)
    c.rect(0.37, 3.14, 1.62, 0.38, fill="#FFFFFF", line=PAL["mauve"], lw=1.0,
           dash="dash", radius=0.06)
    c.text(0.37, 3.17, 1.62, 0.32, "navigation → CDS layer", size=6.8, bold=True)
    c.line([(2.12, 2.40), (2.36, 2.40)], color=PAL["slate"], lw=2.4)

    # B: CDS sub-design (delegated)
    stage_badge(c, 2.47, 0.92, 1, "CDS sub-design — delegated", col=PAL["khaki"])
    c.rect(2.40, 1.35, 2.90, 2.25, fill="#FFFFFF", line=PAL["khaki"], lw=1.3, radius=0.08)
    c.text(2.55, 1.43, 2.6, 0.18, "GenNav-λ inside (workflow 1)", size=7.2, bold=True,
           align="l", color=darken(PAL["khaki"], 0.35))
    for i, g in enumerate(["0", "1", "4", "10", "50"]):
        gear(c, 2.72 + i * 0.30, 1.85, 0.12, g, "feasible" if g in {"1", "4"} else "infeasible")
    c.line([(4.04, 1.85), (4.14, 1.85)], color=PAL["slate"], lw=1.5)
    # 3 profile rows x 3 bars
    for j, pcol in enumerate((PAL["mauve"], PAL["gblue"], PAL["khaki"])):
        for i in range(3):
            c.rect(4.20 + i * 0.28, 1.60 + j * 0.24, 0.24, 0.15,
                   fill=lighten(pcol, 0.45 - 0.05 * i), line=pcol, lw=0.6, radius=0.03)
    c.text(2.55, 2.55, 2.6, 0.2, "≤ 15 CDS = 3 profiles × 5", size=7.5, bold=True, align="l")
    c.text(2.55, 2.82, 2.6, 0.4, "same code path, same audit trail\n(state + trace handed back)",
           size=6.6, align="l", color="#555555", spacing=1.0)
    c.line([(5.32, 2.40), (5.56, 2.40)], color=PAL["slate"], lw=2.4)

    # C: UTR generation
    stage_badge(c, 5.67, 0.92, 2, "UTR generation — GEMORNA", col=PAL["khaki"])
    c.rect(5.60, 1.35, 2.40, 2.25, fill="#FFFFFF", line=PAL["khaki"], lw=1.3, radius=0.08)
    c.text(5.75, 1.50, 0.7, 0.2, "5′UTR", size=7.5, bold=True, align="l")
    for i, t in enumerate("SML"):
        c.chip(6.50 + i * 0.47, 1.48, 0.42, 0.26, t, lighten(PAL["tan"], 0.4), size=7,
               bold=True, line=PAL["tan"], lw=0.9)
    c.text(5.75, 2.05, 0.7, 0.2, "3′UTR", size=7.5, bold=True, align="l")
    for i, t in enumerate("SML"):
        c.chip(6.50 + i * 0.47, 2.03, 0.42, 0.26, t, lighten(PAL["khaki"], 0.4), size=7,
               bold=True, line=PAL["khaki"], lw=0.9)
    c.text(5.75, 2.50, 2.2, 0.2, "3 length presets each", size=6.8, align="l", color="#555555")
    c.text(5.75, 2.75, 2.2, 0.4, "one audited GEMORNA call\nper preset", size=6.6, align="l",
           color="#555555", spacing=1.0)
    c.line([(8.02, 2.40), (8.26, 2.40)], color=PAL["slate"], lw=2.4)

    # D: assemble
    stage_badge(c, 8.37, 0.92, 3, "assemble — combinatorial", col=PAL["khaki"])
    c.rect(8.30, 1.35, 2.60, 2.25, fill="#FFFFFF", line=PAL["khaki"], lw=1.3, radius=0.08)
    # construct cartoon
    yy = 1.70
    c.rect(8.55, yy, 0.50, 0.26, fill=lighten(PAL["tan"], 0.4), line=PAL["tan"], lw=0.9, radius=0.05)
    c.rect(9.05, yy, 1.10, 0.26, fill=lighten(PAL["lav"], 0.45), line=PAL["lav"], lw=0.9, radius=0.05)
    c.rect(10.15, yy, 0.50, 0.26, fill=lighten(PAL["khaki"], 0.4), line=PAL["khaki"], lw=0.9, radius=0.05)
    c.text(8.55, yy + 0.005, 0.50, 0.25, "5′", size=7.5, bold=True)
    c.text(9.05, yy + 0.005, 1.10, 0.25, "CDS", size=7.5, bold=True)
    c.text(10.15, yy + 0.005, 0.50, 0.25, "3′", size=7.5, bold=True)
    # combo grid
    for r_ in range(3):
        for q_ in range(3):
            c.rect(8.60 + q_ * 0.17, 2.30 + r_ * 0.17, 0.13, 0.13,
                   fill=lighten(PAL["lav"], 0.55), line=PAL["lav"], lw=0.6, radius=0.02)
    c.text(9.30, 2.30, 1.55, 0.5, "≤ 15 CDS × 3 × 3\n→ ≤ 135 constructs", size=7.0,
           bold=True, align="l", spacing=1.0)
    c.text(8.55, 3.02, 2.2, 0.2, "deduplicated by sequence", size=6.6, color="#555555")
    # wrap-around dashed conduit to row 2
    c.line([(9.60, 3.62), (9.60, 4.02), (0.55, 4.02), (0.55, 4.24)],
           color=PAL["slate"], lw=1.6, dash="dash")
    c.text(4.9, 3.86, 1.4, 0.16, "per construct", size=6.8, italic=True, color="#555555")

    # ---- row 2: evaluate -> ASF rank -> output ----------------------------
    # E: evaluate
    stage_badge(c, 0.35, 4.32, 4, "evaluate — per construct", col=PAL["gblue"])
    c.rect(0.25, 4.72, 4.10, 1.95, fill="#FFFFFF", line=PAL["gblue"], lw=1.3, radius=0.08)
    ev = [["CDS metrics (inherited)\nCAI · MFE · GC · U", "full-length fold\nMFE · paired fraction"],
          ["5′UTR MRL\nGEMORNA oracle", "3′UTR stability\nGEMORNA oracle"],
          ["junction ΔG × 2\n5′|CDS · CDS|3′", "RNASTOP\noverall stability"]]
    for r_ in range(3):
        for q_ in range(2):
            x = 0.42 + q_ * 2.02
            y = 4.86 + r_ * 0.56
            oracle = (r_ == 1)
            c.rect(x, y, 1.92, 0.48, fill=lighten(PAL["gblue"], 0.6), line=PAL["gblue"],
                   lw=0.8, radius=0.05)
            c.text(x + 0.05, y + 0.03, 1.82, 0.42, ev[r_][q_], size=6.6, align="l",
                   spacing=0.95, bold=False)
            if oracle:
                c.rect(x + 1.92 - 0.10, y + 0.04, 0.06, 0.40, fill=PAL["terracotta"],
                       radius=0.02)
    c.text(0.42, 6.52, 3.8, 0.16, "terracotta edge = oracle metric, CapGate-governed",
           size=6.2, italic=True, color=PAL["terracotta"], align="l")
    c.line([(4.37, 5.55), (4.61, 5.55)], color=PAL["slate"], lw=2.4)

    # F: ASF rank
    stage_badge(c, 4.72, 4.32, 5, "rank — ASF vs reference point", col=PAL["lav"])
    c.rect(4.65, 4.72, 4.00, 1.95, fill="#FFFFFF", line=PAL["lav"], lw=1.3, radius=0.08)
    # mini plot
    px0, py1, px1, py0 = 5.05, 6.10, 7.15, 5.00
    c.line([(px0, py1), (px1, py1)], color="#333333", lw=0.9, arrow="end", arrowhead=0.05)
    c.line([(px0, py1), (px0, py0)], color="#333333", lw=0.9, arrow="end", arrowhead=0.05)
    c.text(px0 + 0.35, py1 + 0.02, 1.6, 0.14, "objective i (higher = better)", size=6.0,
           color="#555555")
    star = (5.35, 5.16)
    c.text(star[0] - 0.11, star[1] - 0.13, 0.24, 0.24, "★", size=11, bold=True,
           color=PAL["terracotta"])
    c.text(star[0] + 0.10, star[1] - 0.10, 1.2, 0.15, "reference point", size=6.2,
           align="l", color=PAL["terracotta"])
    dots = [(5.7, 5.5), (6.0, 5.35), (6.3, 5.6), (6.6, 5.3), (6.9, 5.7), (6.15, 5.85), (6.55, 5.95)]
    for dx, dy in dots:
        c.oval(dx - 0.035, dy - 0.035, 0.07, 0.07, fill=PAL["lav"])
    c.line([(dots[0][0], dots[0][1]), (star[0], star[1])], color=PAL["dgrey"], lw=0.8, dash="dash", arrow="none")
    c.line([(dots[2][0], dots[2][1]), (star[0], star[1])], color=PAL["dgrey"], lw=0.8, dash="dash", arrow="none")
    c.text(7.25, 5.05, 1.3, 0.4, "closest to ★\n= rank #1", size=6.8, bold=True, align="l")
    c.line([(7.35, 5.55), (6.65, 5.75)], color="#555555", lw=0.8, arrow="end", arrowhead=0.05)
    # governance chip
    c.rect(4.85, 6.30, 3.60, 0.32, fill="#FFFFFF", line=PAL["terracotta"], lw=1.0,
           dash="dash", radius=0.06)
    c.text(4.90, 6.315, 3.50, 0.28, "CapGate assembles objectives — demoted oracles annotate, never rank",
           size=6.4, bold=True, color=darken(PAL["terracotta"], 0.15))
    c.line([(8.67, 5.55), (8.91, 5.55)], color=PAL["slate"], lw=2.4)

    # G: ranked output
    c.text(9.00, 4.32, 2.5, 0.2, "ranked output", size=8.5, bold=True, color="#555555")
    c.rect(8.95, 4.72, 4.13, 1.95, fill=lighten(PAL["sage"], 0.62), line=PAL["sage"],
           lw=1.1, radius=0.07)
    for i in range(3):
        ry = 4.90 + i * 0.50
        c.text(9.10, ry + 0.03, 0.35, 0.2, f"#{i + 1}", size=8, bold=True, align="l")
        c.rect(9.50, ry, 0.34, 0.20, fill=lighten(PAL["tan"], 0.4), line=PAL["tan"], lw=0.7, radius=0.04)
        c.rect(9.84, ry, 0.80, 0.20, fill=lighten(PAL["lav"], 0.45), line=PAL["lav"], lw=0.7, radius=0.04)
        c.rect(10.64, ry, 0.34, 0.20, fill=lighten(PAL["khaki"], 0.4), line=PAL["khaki"], lw=0.7, radius=0.04)
        mrl_v, cai_v, asf_v = [("6.2", ".93", ".10"), ("6.1", ".90", ".11"),
                               ("6.0", ".88", ".12")][i]
        c.text(11.10, ry - 0.01, 1.9, 0.2, f"MRL {mrl_v} · CAI {cai_v} · asf {asf_v}",
           size=6.4, align="l", color="#333333")
    c.text(12.72, 4.86, 0.25, 0.22, "★", size=10, bold=True, color=PAL["terracotta"])
    c.text(9.10, 6.38, 2.6, 0.18, "best = min ASF distance · Pareto frontier attached",
           size=6.6, color="#555555", align="l")
    can_chip(c, 11.45, 6.36, "every call in the audit trail", w=1.7)

    legend_row(c, 7.08)
    return items


# -------------------------------------------------------------------- main --

def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview")
    os.makedirs(out_dir, exist_ok=True)

    from pptx import Presentation
    from pptx.util import Inches
    F.prs = Presentation()
    F.prs.slide_width = Inches(SLIDE_W)
    F.prs.slide_height = Inches(SLIDE_H)
    F.blank = F.prs.slide_layouts[6]

    slides = [slide_cds(), slide_full()]
    pptx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "RNADesignAgent_workflow_schematics.pptx")
    F.emit_pptx(slides, pptx_path)
    F.emit_mpl(slides[0], os.path.join(out_dir, "wf1_cds.png"))
    F.emit_mpl(slides[1], os.path.join(out_dir, "wf2_full_length.png"))
    print("wrote", pptx_path)


if __name__ == "__main__":
    main()
