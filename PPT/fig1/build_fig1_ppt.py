#!/usr/bin/env python3
"""Build RNADesignAgent Fig 1 (model schematic) as an editable PPTX.

Every panel is drawn with native PowerPoint shapes (rounded rects, connectors,
pies/block-arcs) so the user can edit each element afterwards. The same shape
spec is also rendered through matplotlib to PNG for visual QA (no LibreOffice
on this machine).

Slides: 1 = composite Fig 1 (a-f), then one slide per panel (a..f).

Layout follows docs/FIGURE_PLAN_V5.md (6 panels, a full-width top; b+c; d+e;
f full-width bottom). Palette = palette rev 7 (Morandi, user-locked).
"""
import math
import os

# ---------------------------------------------------------------- palette ---
PAL = {
    "mauve":     "#B5838D",  # LLM agents
    "rose":      "#D3B5B0",  # agent card light fill
    "terracotta":"#C08B7C",  # CapGate / governance (the single accent)
    "tan":       "#D9C3A9",  # user / human side
    "khaki":     "#CDBF9E",  # secondary mechanisms
    "sage":      "#A3B18A",  # outputs / deliverables
    "dsage":     "#8DA290",  # capabilities (validated wrappers)
    "gblue":     "#8FA6BB",  # tools / services infrastructure
    "slate":     "#6B7B8D",  # data-flow arrows
    "lav":       "#A99AAF",  # workflows
    "wgrey":     "#B7B0A2",  # support layers / neutral records
    "dgrey":     "#7A7672",  # dark neutral text accents / audit
}
INK = "#000000"
CREAM = "#F5F1EA"   # panel container fill (barely off-white)
CREAM_DK = "#EDE6DA"

def mix(h1, h2, t):
    """Blend hex h1 toward h2 by t (0=h1, 1=h2)."""
    a = [int(h1[i:i+2], 16) for i in (1, 3, 5)]
    b = [int(h2[i:i+2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))

def lighten(h, t):  return mix(h, "#FFFFFF", t)
def darken(h, t):   return mix(h, "#000000", t)

# ------------------------------------------------------------------ canvas --
class Canvas:
    """Affine-transformed shape-spec collector. Units = inches, y down."""

    def __init__(self, items, ox=0.0, oy=0.0, s=1.0):
        self.items, self.ox, self.oy, self.s = items, ox, oy, s

    def _p(self, x, y):        return (self.ox + x * self.s, self.oy + y * self.s)
    def _l(self, v):           return v * self.s

    def rect(self, x, y, w, h, fill="#FFFFFF", line=None, lw=0.75, dash=None, radius=None, alpha=None):
        X, Y = self._p(x, y)
        self.items.append(("rrect" if radius else "rect", X, Y, self._l(w), self._l(h),
                           dict(fill=fill, line=line, lw=lw, dash=dash,
                                radius=radius, alpha=alpha)))

    def oval(self, x, y, w, h, fill="#FFFFFF", line=None, lw=0.75, dash=None):
        X, Y = self._p(x, y)
        self.items.append(("oval", X, Y, self._l(w), self._l(h),
                           dict(fill=fill, line=line, lw=lw, dash=dash)))

    def pie(self, cx, cy, r, a0, a1, fill, line=None, lw=0.75, inner=0.0):
        """Wedge; angles in degrees, 0 = 12 o'clock, clockwise positive."""
        X, Y = self._p(cx, cy)
        self.items.append(("pie", X, Y, self._l(r), a0, a1, self._l(inner),
                           dict(fill=fill, line=line, lw=lw)))

    def can(self, x, y, w, h, fill, line=None, lw=0.75):
        X, Y = self._p(x, y)
        self.items.append(("can", X, Y, self._l(w), self._l(h), dict(fill=fill, line=line, lw=lw)))

    def text(self, x, y, w, h, s_, size=9, bold=False, color=INK, align="c",
             valign="m", rotate=0, italic=False, spacing=1.0):
        X, Y = self._p(x, y)
        self.items.append(("text", X, Y, self._l(w), self._l(h),
                           dict(s=s_, size=size * self.s, bold=bold, color=color,
                                align=align, valign=valign, rotate=rotate,
                                italic=italic, spacing=spacing)))

    def line(self, pts, color, lw=1.0, dash=None, arrow="end", arrowhead=0.09):
        P = [self._p(px, py) for px, py in pts]
        self.items.append(("line", P, dict(color=color, lw=lw * self.s, dash=dash,
                                           arrow=arrow, ah=self._l(arrowhead))))

    # ------------------------------------------------ composites (icons) --
    def person(self, cx, cy, s, color):
        r = 0.42 * s
        self.oval(cx - r, cy - s - 0.05 * s, 2 * r, 2 * r, fill=color)
        self.pie(cx, cy + 0.62 * s, 0.78 * s, 270, 90, fill=color)

    def robot(self, cx, cy, s, color):
        w, h = 1.35 * s, 0.95 * s
        self.rect(cx - w / 2, cy - h / 2, w, h, fill=color, radius=0.18 * s)
        self.line([(cx, cy - h / 2), (cx, cy - h / 2 - 0.28 * s)], color=color, lw=1.4 * s, arrow="none")
        self.oval(cx - 0.05 * s, cy - h / 2 - 0.36 * s, 0.1 * s, 0.1 * s, fill=color)
        er = 0.14 * s
        self.oval(cx - 0.34 * s - er, cy - er, 2 * er, 2 * er, fill="#FFFFFF")
        self.oval(cx + 0.34 * s - er, cy - er, 2 * er, 2 * er, fill="#FFFFFF")

    def chip(self, x, y, w, h, s_, fill, tcolor=INK, size=8, bold=False, line=None, lw=0.75, dash=None):
        self.rect(x, y, w, h, fill=fill, line=line, lw=lw, dash=dash, radius=h / 2)
        self.text(x, y - 0.004, w, h, s_, size=size, bold=bold, color=tcolor)

    def card(self, x, y, w, h, title, body, fill, tcol=INK, accent=None,
             tsize=9, bsize=7.3, dash=None, lw=1.0, title_h=0.24):
        self.rect(x, y, w, h, fill=fill, line=accent or darken(fill, 0.25), lw=lw,
                  dash=dash, radius=0.06)
        self.text(x + 0.04, y + 0.015, w - 0.08, title_h, title, size=tsize, bold=True, color=tcol)
        if body:
            self.text(x + 0.05, y + title_h + 0.01, w - 0.10, h - title_h - 0.03, body,
                      size=bsize, color=tcol, valign="t", spacing=1.02)

# ============================================================ PANEL LAYOUT ==
# Local coordinates inside each panel box; composite places them.

def panel_a(c):
    """a | End-to-end cycle + seven-layer spine. Local box 12.97 x 2.02."""
    W, H = 12.97, 2.02
    # ---- left: user goal -------------------------------------------------
    c.person(0.42, 0.62, 0.16, PAL["tan"])
    c.text(0.02, 1.02, 1.5, 0.18, "User", size=8.5, bold=True)
    c.rect(0.0, 1.24, 1.62, 0.62, fill=lighten(PAL["tan"], 0.45),
           line=PAL["tan"], lw=1.0, radius=0.06)
    c.text(0.06, 1.28, 1.50, 0.54, "“Design a full-length\nmRNA for HER2,\nexpression + stability”",
           size=7.2, valign="t", spacing=1.0)
    # ---- right: outputs --------------------------------------------------
    ox = W - 2.42
    c.rect(ox, 0.30, 2.42, 0.68, fill=lighten(PAL["sage"], 0.55), line=PAL["sage"], lw=1.0, radius=0.06)
    c.text(ox + 0.06, 0.34, 2.30, 0.22, "Ranked candidate batch", size=8.2, bold=True)
    c.text(ox + 0.06, 0.56, 2.30, 0.40, "top-5 sequences per profile,\nASF reference-point ranked", size=7.0, valign="t")
    c.rect(ox, 1.14, 2.42, 0.68, fill=lighten(PAL["wgrey"], 0.5), line=PAL["wgrey"], lw=1.0, radius=0.06)
    c.can(ox + 0.10, 1.26, 0.26, 0.30, fill=PAL["dgrey"])
    c.text(ox + 0.44, 1.18, 1.94, 0.22, "Audit trail", size=8.2, bold=True, align="l")
    c.text(ox + 0.44, 1.40, 1.94, 0.40, "every tool call · gate decision\n· ranking · claim", size=7.0, align="l", valign="t")
    # ---- centre: platform container --------------------------------------
    px, pw = 1.95, 8.30
    c.rect(px, 0.06, pw, 1.80, fill=CREAM, line=PAL["dgrey"], lw=1.1, radius=0.08)
    c.text(px, 0.10, pw, 0.20, "RNADesignAgent — tool-first platform", size=9.5, bold=True)
    layers = [
        ("L6", "Entry façade", "CLI form chat · FastAPI", PAL["wgrey"], None),
        ("L5", "Session & workspace", "isolated per-session state", PAL["wgrey"], None),
        ("L4", "Multi-agent execution", "Pipeline · Specialist · Quality (advisory) · Synthesis", PAL["mauve"], "b"),
        ("L3", "Service orchestration", "health-check · auto-start", PAL["gblue"], None),
        ("L2", "Domain workflows × 11", "fixed generate → evaluate → score → rank", PAL["lav"], "e"),
        ("L1", "Capabilities", "validated outputs · audit write-back", PAL["dsage"], None),
        ("L0", "Scientific tools × 41", "behind 21 local microservices", PAL["gblue"], "c"),
    ]
    bx, bw = px + 0.12, pw - 0.55
    by, bh, bgap = 0.335, 0.183, 0.024
    for i, (tag, name, desc, col, cue) in enumerate(layers):
        y = by + i * (bh + bgap)
        c.rect(bx, y, 0.34, bh, fill=col, radius=0.03)
        c.text(bx, y - 0.004, 0.34, bh, tag, size=7.5, bold=True, color="#FFFFFF")
        c.rect(bx + 0.36, y, bw - 0.36, bh, fill=lighten(col, 0.62), line=col,
               lw=1.2 if cue else 0.6, radius=0.03)
        label = f"{name} — {desc}"
        c.text(bx + 0.44, y - 0.004, bw - 0.85, bh, label, size=7.6, align="l",
               bold=(cue is not None))
        if cue:
            c.text(bx + bw - 0.42, y - 0.004, 0.36, bh, f"→ {cue}", size=7.5,
                   bold=True, color=darken(col, 0.3))
    # CapGate cross-cutting bar (right edge of the stack, spanning L4..L0)
    gx = px + pw - 0.34
    l4_top = by + 2 * (bh + bgap)
    l0_bot = by + 6 * (bh + bgap) + bh
    c.rect(gx, l4_top, 0.22, l0_bot - l4_top, fill=PAL["terracotta"], radius=0.04)
    c.text(gx + 0.11 - 0.50, (l4_top + l0_bot) / 2 - 0.10, 1.00, 0.20, "CapGate → d",
           size=7.5, bold=True, color="#FFFFFF", rotate=270)
    # dashed stubs: gate touches L4 (claims) and L1/L0 (tool choke point)
    for yy in (l4_top + bh / 2, by + 6 * (bh + bgap) + bh / 2):
        c.line([(gx - 0.28, yy), (gx, yy)], color=PAL["terracotta"], lw=1.0,
               dash="dash", arrow="none")
    # ---- flow arrows -----------------------------------------------------
    c.line([(1.66, 1.55), (px - 0.04, 1.55)], color=PAL["slate"], lw=2.2)
    c.line([(px + pw + 0.03, 0.64), (ox - 0.04, 0.64)], color=PAL["slate"], lw=2.2)
    c.line([(px + pw + 0.03, 1.48), (ox - 0.04, 1.48)], color=PAL["slate"], lw=2.2)
    # ---- bottom: design commitments --------------------------------------
    c.rect(0.0, 1.86, 6.35, 0.16, fill=CREAM_DK, radius=0.05)
    c.text(0.0, 1.855, 6.35, 0.16, "① The LLM never writes a sequence — orchestrate · review · report only",
           size=7.4, bold=True)
    c.rect(6.62, 1.86, 6.35, 0.16, fill=CREAM_DK, radius=0.05)
    c.text(6.62, 1.855, 6.35, 0.16, "② Every comparison pre-registered & budget-matched",
           size=7.4, bold=True)


def panel_b(c):
    """b | Multi-agent execution layer (L4). Local box 8.55 x 1.98."""
    # input chip
    c.chip(0.0, 0.62, 0.78, 0.42, "plan\nnode(s)", lighten(PAL["wgrey"], 0.5), size=7.4)
    cards = [
        ("PipelineAgent", "deterministic scheduling of\nmulti-node plans (no LLM)",
         PAL["rose"], None),
        ("SpecialistAgent", "per-workflow strategy & retry\nhard failures only\nASF ranking · 6 workflows",
         PAL["rose"], None),
        ("SynthesisAgent", "multi-node report — claims\npass the ClaimGate before\npublication",
         PAL["rose"], "gate"),
        ("AgentResult", "candidates + quality report\n+ full audit write-back",
         lighten(PAL["sage"], 0.55), None),
    ]
    xw, gap, y0, ch = 1.56, 0.40, 0.30, 0.98
    xs = [1.02 + i * (xw + gap) for i in range(4)]
    for (title, body, fill, mark), x in zip(cards, xs):
        c.card(x, y0, xw, ch, title, body, fill, tsize=8.6, bsize=7.0)
        c.robot(x + xw - 0.18, y0 + 0.17, 0.055, PAL["mauve"] if mark != "gate" else PAL["terracotta"])
    for x in xs[:-1]:
        c.line([(x + xw + 0.03, y0 + ch / 2), (x + xw + gap - 0.03, y0 + ch / 2)],
               color=PAL["slate"], lw=2.0)
    c.line([(0.80, 0.83), (xs[0] - 0.03, 0.83)], color=PAL["slate"], lw=2.0)
    # ClaimGate mini-badge on SynthesisAgent
    c.chip(xs[2] + 0.30, y0 + ch - 0.26, 1.06, 0.20, "ClaimGate ✓", PAL["terracotta"],
           tcolor="#FFFFFF", size=7.0, bold=True)
    # QualityAgent advisory loop (below SpecialistAgent)
    qx, qw = xs[1] - 0.30, xw + 0.60
    c.card(qx, 1.52, qw, 0.40, "", "", "#FFFFFF", dash="dash", lw=1.1, accent=PAL["mauve"])
    c.text(qx, 1.545, qw, 0.18, "QualityAgent — advisory LLM review", size=7.6, bold=True,
           color=darken(PAL["mauve"], 0.15))
    c.text(qx, 1.71, qw, 0.18, "31/31 sessions identical on / off / failed · never flips success",
           size=6.6)
    qcx = xs[1] + xw / 2
    c.line([(qcx, 1.52), (qcx, y0 + ch + 0.03)],
           color=PAL["mauve"], lw=1.2, dash="dash", arrow="both")
    # removed coordination loop (falsified)
    rx = 7.30
    c.rect(rx, 1.56, 1.10, 0.34, fill="none", line=PAL["dgrey"], lw=0.9, dash="dash", radius=0.05)
    c.text(rx + 0.30, 1.585, 0.78, 0.30, "coordination loop\nremoved (falsified)", size=5.9,
           color=PAL["dgrey"], spacing=0.95, align="l")
    c.line([(rx + 0.07, 1.63), (rx + 0.25, 1.83)], color=PAL["terracotta"], lw=1.4, arrow="none")
    c.line([(rx + 0.25, 1.63), (rx + 0.07, 1.83)], color=PAL["terracotta"], lw=1.4, arrow="none")


def panel_c(c):
    """c | Platform at a glance: KPI badges + audit-composition donut. 4.30 x 1.98."""
    kpis = [("41", "scientific tools", PAL["gblue"]),
            ("21", "microservices", PAL["gblue"]),
            ("11", "workflows", PAL["lav"]),
            ("210", "benchmark tasks", PAL["wgrey"])]
    tw, th, gx, gy = 0.98, 0.60, 0.08, 0.16
    for i, (num, lab, col) in enumerate(kpis):
        x = gx + (i % 2) * (tw + 0.10)
        y = gy + (i // 2) * (th + 0.10)
        c.rect(x, y, tw, th, fill=lighten(col, 0.62), line=col, lw=0.8, radius=0.05)
        c.text(x, y + 0.015, tw, 0.30, num, size=14, bold=True, color=darken(col, 0.3))
        c.text(x, y + 0.335, tw, 0.24, lab, size=6.6)
    c.rect(gx, gy + 2 * (th + 0.10), 2 * tw + 0.10, 0.30, fill=CREAM_DK, radius=0.05)
    c.text(gx, gy + 2 * (th + 0.10) - 0.004, 2 * tw + 0.10, 0.30,
           "241 / 241 campaign runs · 0 failures", size=7.4, bold=True)
    # donut: audit-trail composition
    cx, cy, r = 3.22, 0.75, 0.60
    segs = [("tool calls", 9460, PAL["gblue"]),
            ("gate decisions", 1356, PAL["terracotta"]),
            ("ranking assemblies", 187, PAL["lav"])]
    total = sum(v for _, v, _ in segs)
    a = 0.0
    for name, v, col in segs:
        span = 360.0 * v / total
        c.pie(cx, cy, r, a, a + span, fill=col, line="#FFFFFF", lw=1.0, inner=r * 0.52)
        a += span
    c.text(cx - r, cy - 0.16, 2 * r, 0.20, "11,003", size=9.5, bold=True)
    c.text(cx - r, cy + 0.03, 2 * r, 0.16, "audit events", size=6.2)
    ly = 1.45
    leg = [("9,460 tool calls", PAL["gblue"]), ("1,356 gate decisions", PAL["terracotta"]),
           ("187 ranking assemblies", PAL["lav"])]
    c.text(2.16, ly, 2.1, 0.14, "production audit trail", size=6.6, bold=True, align="l")
    for i, (lab, col) in enumerate(leg):
        yy = ly + 0.13 + i * 0.135
        c.rect(2.16, yy + 0.015, 0.09, 0.09, fill=col, radius=0.02)
        c.text(2.30, yy, 1.95, 0.12, lab, size=6.4, align="l")


def panel_d(c):
    """d | CapGate loop: offline profiling feeds two runtime gates. 8.55 x 1.90."""
    # ---- top lane: offline evidence build
    tl = [("Anchor sets", "assertion-curated\nliterature anchors", PAL["tan"], 1.50),
          ("Capability profiler", "CASF: score · screen · rank · dock\ngates: AUROC .8 · ρ .6 · top-1 ⅔", PAL["gblue"], 2.00),
          ("SelfModel", "29 graded records: verified ·\ntransferred · failed · unprofiled", PAL["khaki"], 2.55)]
    x = 0.0
    ytop, htop = 0.13, 0.56
    centers = []
    for name, body, col, w in tl:
        c.card(x, ytop, w, htop, name, body, lighten(col, 0.5), accent=col,
               tsize=8.2, bsize=6.4, title_h=0.19)
        centers.append((x, w))
        x += w + 0.35
    for (x0, w0), (x1, _) in zip(centers, centers[1:]):
        c.line([(x0 + w0 + 0.03, ytop + htop / 2), (x1 - 0.03, ytop + htop / 2)],
               color=PAL["slate"], lw=1.8)
    smx, smw = centers[-1]
    c.text(6.95, ytop + 0.04, 1.58, 0.50,
           "packaged default SelfModel —\ngating ships as the\nout-of-box default", size=6.4,
           italic=True, align="l", color=PAL["dgrey"], spacing=1.0)
    # ---- runtime lane: two gated rows
    r1, r2, rh = 0.95, 1.33, 0.28
    c.chip(0.0, r1, 1.16, rh, "planned tool call", lighten(PAL["wgrey"], 0.55), size=7.0)
    c.chip(0.0, r2, 1.16, rh, "draft report claims", lighten(PAL["wgrey"], 0.55), size=7.0)
    for gy, gt, gs in ((r1, "DecisionGate", "before execution"),
                       (r2, "ClaimGate", "before publication")):
        c.rect(1.36, gy, 1.30, rh, fill=PAL["terracotta"], radius=0.06)
        c.text(1.36, gy + 0.005, 1.30, 0.15, gt, size=8.2, bold=True, color="#FFFFFF")
        c.text(1.36, gy + 0.155, 1.30, 0.11, gs, size=5.8, color="#FFFFFF")
        c.line([(1.19, gy + rh / 2), (1.33, gy + rh / 2)], color=PAL["slate"], lw=1.8)
    # verdict chips (row 1) and claim scope ladder (row 2)
    vx, vw, vg = 2.90, 0.98, 0.08
    verd = [("allow ✓", PAL["sage"]), ("downgrade", PAL["khaki"]),
            ("require profiling", PAL["wgrey"]), ("reject ✗", PAL["terracotta"])]
    for i, (lab, col) in enumerate(verd):
        c.chip(vx + i * (vw + vg), r1 + 0.02, vw, rh - 0.04, lab,
               lighten(col, 0.45), size=6.4, bold=True, line=col, lw=0.8)
    lad = ["absolute", "within-target", "trend-only", "suppressed"]
    for i, lab in enumerate(lad):
        col = mix(PAL["sage"], PAL["terracotta"], i / 3.0)
        cxx = vx + i * (vw + vg)
        c.chip(cxx, r2 + 0.02, vw, rh - 0.04, lab, lighten(col, 0.45),
               size=6.4, bold=True, line=col, lw=0.8)
        if i:
            c.line([(cxx - vg + 0.005, r2 + rh / 2), (cxx - 0.005, r2 + rh / 2)],
                   color=PAL["dgrey"], lw=1.0)
    for ry in (r1, r2):
        c.line([(2.69, ry + rh / 2), (vx - 0.03, ry + rh / 2)], color=PAL["slate"], lw=1.8)
    # audited execution outcome chip (spans both rows)
    c.chip(7.30, r1, 1.25, r2 + rh - r1, "audited\nexecution\n(traceable)",
           lighten(PAL["sage"], 0.55), size=7.0, bold=True, line=PAL["sage"], lw=1.0)
    for ry in (r1, r2):
        c.line([(vx + 4 * (vw + vg) + 0.01, ry + rh / 2), (7.27, ry + rh / 2)],
               color=PAL["slate"], lw=1.8)
    # SelfModel feeds the gates (dashed terracotta)
    c.line([(smx + smw / 2, ytop + htop + 0.02), (2.01, r1 - 0.03)],
           color=PAL["terracotta"], lw=1.3, dash="dash")
    c.line([(2.01, r1 + rh + 0.01), (2.01, r2 - 0.03)], color=PAL["terracotta"],
           lw=1.1, dash="dash")
    # audit-trail bar
    aby = 1.70
    c.rect(1.36, aby, 7.19, 0.17, fill=PAL["dgrey"], radius=0.05)
    c.can(1.45, aby + 0.015, 0.16, 0.14, fill=lighten(PAL["dgrey"], 0.4))
    c.text(1.68, aby - 0.004, 6.8, 0.17, "append-only audit trail — every call · gate · claim · ranking",
           size=6.8, bold=True, color="#FFFFFF", align="l")
    for fx in (2.01, 7.92):
        c.line([(fx, r2 + rh + 0.02), (fx, aby - 0.02)], color=PAL["dgrey"], lw=1.0, dash="dash")
    # production-default tag
    c.text(0.0, aby - 0.06, 1.34, 0.28, "production default\nsingle choke point\n(ToolExecutor)",
           size=6.0, align="l", color=PAL["dgrey"], spacing=0.95)


def panel_e(c):
    """e | GenNav constraint-navigation loop with gear lattice map. 4.30 x 1.90."""
    # gear lattice (navigation map): lambda gears
    gears = ["0", "1", "2", "4", "8", "10", "20", "50"]
    feasible = {"1", "2", "4", "8"}
    delivered = {"4"}
    c.text(0.24, 0.02, 4.06, 0.16, "generator gear lattice (LinearDesign λ · 35-pt)", size=6.8,
           bold=True, align="l")
    gr = 0.155
    for i, g in enumerate(gears):
        cx = 0.28 + i * 0.50
        cy = 0.42
        fill = PAL["sage"] if g in feasible else PAL["wgrey"]
        c.oval(cx - gr, cy - gr, 2 * gr, 2 * gr, fill=lighten(fill, 0.35),
               line=PAL["mauve"] if g in delivered else darken(fill, 0.25),
               lw=2.0 if g in delivered else 0.8)
        c.text(cx - gr, cy - 0.07, 2 * gr, 0.14, g, size=6.6, bold=True)
    c.text(3.9, 0.30, 0.38, 0.24, "…", size=10, bold=True, color=PAL["dgrey"])
    # legend
    c.oval(0.06, 0.66, 0.09, 0.09, fill=lighten(PAL["sage"], 0.35), line=darken(PAL["sage"], 0.25), lw=0.8)
    c.text(0.19, 0.645, 0.62, 0.13, "feasible", size=6.0, align="l")
    c.oval(0.78, 0.66, 0.09, 0.09, fill=lighten(PAL["wgrey"], 0.35), line=darken(PAL["wgrey"], 0.25), lw=0.8)
    c.text(0.91, 0.645, 0.68, 0.13, "infeasible", size=6.0, align="l")
    c.oval(1.62, 0.66, 0.09, 0.09, fill=lighten(PAL["sage"], 0.35), line=PAL["mauve"], lw=1.6)
    c.text(1.75, 0.645, 0.85, 0.13, "delivered", size=6.0, align="l")
    # loop steps
    steps = [("① probe", "feasibility-first\nscan of gears"),
             ("② allocate", "guaranteed-repair ·\nbudget = rule arm (35)"),
             ("③ deliver", "per-profile batch ×5\nor declared degrade")]
    sw, sh, sy = 1.30, 0.56, 0.90
    for i, (t, b) in enumerate(steps):
        x = 0.0 + i * (sw + 0.20)
        c.card(x, sy, sw, sh, t, b, lighten(PAL["khaki"], 0.5), accent=PAL["khaki"],
               tsize=7.6, bsize=6.2, title_h=0.18)
        if i:
            c.line([(x - 0.17, sy + sh / 2), (x - 0.03, sy + sh / 2)], color=PAL["slate"], lw=1.8)
    # reinforce dashed loop back
    c.line([(2 * (sw + 0.20) + sw / 2, sy + sh + 0.02), (2 * (sw + 0.20) + sw / 2, sy + sh + 0.14),
            (sw / 2, sy + sh + 0.14), (sw / 2, sy + sh + 0.02)],
           color=PAL["mauve"], lw=1.1, dash="dash")
    c.text(1.62, sy + sh + 0.13, 1.1, 0.14, "reinforce", size=6.2, color=darken(PAL["mauve"], 0.1))
    # bottom tag
    c.rect(0.0, 1.70, 4.30, 0.18, fill=CREAM_DK, radius=0.05)
    c.text(0.0, 1.695, 4.30, 0.18, "zero LLM · trace audited · default on mRNA workflows",
           size=7.0, bold=True)


RNAD210 = [  # (workflow, tasks, family)
    ("mRNA CDS design", 19, "mRNA"),
    ("full-length mRNA design", 22, "mRNA"),
    ("mRNA sequence scoring", 13, "mRNA"),
    ("siRNA design", 22, "silencing"),
    ("ASO target screening", 14, "silencing"),
    ("sgRNA design", 30, "CRISPR"),
    ("secondary structure design", 25, "structure"),
    ("tertiary structure design", 20, "structure"),
    ("aptamer design", 18, "aptamer & ligand"),
    ("RNA–small-molecule interaction", 15, "aptamer & ligand"),
    ("IRES prediction", 12, "IRES"),
]
FAM_COL = {"mRNA": PAL["mauve"], "silencing": PAL["gblue"], "CRISPR": PAL["dsage"],
           "structure": PAL["lav"], "aptamer & ligand": PAL["tan"], "IRES": PAL["khaki"]}


def panel_f(c):
    """f | RNADesign-210 composition sunburst. Local box 12.97 x 0.95."""
    cx, cy, r = 0.70, 0.50, 0.44
    total = sum(n for _, n, _ in RNAD210)
    # family ring (inner)
    fams = []
    for _, n, f in RNAD210:
        if not fams or fams[-1][0] != f:
            fams.append([f, 0])
        fams[-1][1] += n
    a = 0.0
    for fname, n in fams:
        span = 360.0 * n / total
        c.pie(cx, cy, r * 0.55, a, a + span, fill=FAM_COL[fname], line="#FFFFFF", lw=0.8)
        a += span
    # workflow ring (outer)
    a = 0.0
    fam_idx = {f: i for i, (f, _) in enumerate(fams)}
    for wname, n, fname in RNAD210:
        span = 360.0 * n / total
        col = lighten(FAM_COL[fname], 0.30 + 0.18 * (fam_idx[fname] % 2))
        c.pie(cx, cy, r, a, a + span, fill=col, line="#FFFFFF", lw=0.8, inner=r * 0.55)
        a += span
    c.text(cx - 0.3, cy - 0.10, 0.6, 0.20, "210", size=10, bold=True)
    c.text(cx - 0.3, cy + 0.06, 0.6, 0.14, "tasks", size=6.4)
    # legend chips: 2 columns x 6 rows
    lx, lyy = 1.25, 0.045
    col_w, row_h = 2.62, 0.148
    for i, (wname, n, fname) in enumerate(RNAD210):
        x = lx + (i // 6) * col_w
        y = lyy + (i % 6) * row_h
        c.rect(x, y + 0.015, 0.09, 0.09, fill=lighten(FAM_COL[fname], 0.30 + 0.18 * (fam_idx[fname] % 2)),
               line=FAM_COL[fname], lw=0.6, radius=0.02)
        c.text(x + 0.14, y, col_w - 0.15, 0.13, f"{wname} — {n}", size=6.6, align="l")
    # right annotation
    ax = lx + 2 * col_w + 0.25
    c.rect(ax, 0.10, 12.97 - ax - 0.05, 0.72, fill=CREAM, radius=0.06)
    c.text(ax + 0.10, 0.16, 12.97 - ax - 0.25, 0.60,
           "canonical · edge · full-biology tasks — every input schema-validated\n"
           "paired null models (wild-type / random-synonymous) and\nassertion-curated literature anchors",
           size=7.0, valign="t", align="l", spacing=1.05)


PANELS = [("a", "End-to-end cycle & seven-layer spine", panel_a, 12.97, 2.02),
          ("b", "Multi-agent execution layer (L4)", panel_b, 8.55, 1.98),
          ("c", "Platform at a glance", panel_c, 4.30, 1.98),
          ("d", "CapGate calibrated governance loop", panel_d, 8.55, 1.90),
          ("e", "GenNav constraint-navigation loop", panel_e, 4.30, 1.90),
          ("f", "RNADesign-210 benchmark composition", panel_f, 12.97, 0.95)]

COMP_POS = {"a": (0.18, 0.15), "b": (0.18, 2.29), "c": (8.85, 2.29),
            "d": (0.18, 4.39), "e": (8.85, 4.39), "f": (0.18, 6.41)}

SLIDE_W, SLIDE_H = 13.333, 7.5


def build_composite():
    items = []
    for letter, _, fn, w, h in PANELS:
        ox, oy = COMP_POS[letter]
        c = Canvas(items, ox, oy, 1.0)
        fn(c)
    letters = Canvas(items, 0.0, 0.0, 1.0)
    for letter, _, fn, w, h in PANELS:
        ox, oy = COMP_POS[letter]
        letters.text(ox - 0.03, oy - 0.075, 0.3, 0.22, letter, size=13, bold=True,
                     align="l", valign="t")
    return items


def build_panel_slide(letter):
    _, title, fn, w, h = next(p for p in PANELS if p[0] == letter)
    items = []
    s = min((SLIDE_W - 0.6) / w, (SLIDE_H - 0.85) / h)
    ox, oy = (SLIDE_W - w * s) / 2, 0.62 + (SLIDE_H - 0.85 - h * s) / 2
    c = Canvas(items, ox, oy, s)
    fn(c)
    c2 = Canvas(items, 0, 0, 1.0)
    c2.text(0.28, 0.12, 0.4, 0.32, letter, size=20, bold=True, align="l", valign="t")
    c2.text(0.72, 0.16, 11.0, 0.28, title, size=13, bold=True, align="l", color="#333333")
    return items

# ------------------------------------------------------------- pptx backend -

def emit_pptx(slides_items, path):
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
    from pptx.enum.dml import MSO_LINE_DASH_STYLE
    from pptx.oxml.ns import qn
    import copy

    DASH = {"dash": MSO_LINE_DASH_STYLE.DASH, "dot": MSO_LINE_DASH_STYLE.ROUND_DOT}

    def rgb(h): return RGBColor.from_string(h.lstrip("#"))

    def set_fill(shape, color, alpha=None):
        if color is None or color == "none":
            shape.fill.background()
        else:
            shape.fill.solid()
            shape.fill.fore_color.rgb = rgb(color)
            if alpha is not None:  # alpha in 0..1 opacity
                srgb = shape.fill.fore_color._xFill.find(qn('a:srgbClr'))
                if srgb is not None:
                    el = srgb.makeelement(qn('a:alpha'), {'val': str(int(alpha * 100000))})
                    srgb.append(el)

    def set_line(shape, color, lw, dash):
        if color is None:
            shape.line.fill.background()
        else:
            shape.line.color.rgb = rgb(color)
            shape.line.width = Pt(lw)
            if dash:
                shape.line.dash_style = DASH[dash]
        shape.shadow.inherit = False

    def set_adjustments(shape, vals):
        sp = shape._element.spPr
        geom = sp.find(qn('a:prstGeom'))
        av = geom.find(qn('a:avLst'))
        if av is None:
            av = geom.makeelement(qn('a:avLst'), {})
            geom.append(av)
        for ch in list(av):
            av.remove(ch)
        for name, val in vals:
            gd = av.makeelement(qn('a:gd'), {'name': name, 'fmla': f'val {int(round(val))}'})
            av.append(gd)

    def add_text(slide, x, y, w, h, o):
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, 0)
        tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE,
                              "b": MSO_ANCHOR.BOTTOM}[o["valign"]]
        lines = o["s"].split("\n")
        for i, ln_txt in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER,
                           "r": PP_ALIGN.RIGHT}[o["align"]]
            p.line_spacing = o["spacing"]
            run = p.add_run()
            run.text = ln_txt
            f = run.font
            f.size = Pt(max(o["size"], 1))
            f.bold = o["bold"]
            f.italic = o["italic"]
            f.name = "Arial"
            f.color.rgb = rgb(o["color"])
        if o["rotate"]:
            tb.rotation = o["rotate"]
        return tb

    def add_connector(slide, p0, p1, o, last):
        conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(p0[0]), Inches(p0[1]),
                                          Inches(p1[0]), Inches(p1[1]))
        conn.line.color.rgb = rgb(o["color"])
        conn.line.width = Pt(max(o["lw"], 0.5))
        if o["dash"]:
            conn.line.dash_style = DASH[o["dash"]]
        conn.shadow.inherit = False
        ln = conn.line._get_or_add_ln()
        arrow = o["arrow"] if last else ("start" if o["arrow"] == "both" else "none")
        if arrow in ("end", "both") and last:
            te = ln.makeelement(qn('a:tailEnd'), {'type': 'triangle', 'w': 'med', 'len': 'med'})
            ln.append(te)
        if o["arrow"] == "both":
            he = ln.makeelement(qn('a:headEnd'), {'type': 'triangle', 'w': 'med', 'len': 'med'})
            ln.append(he)
        return conn

    def to_ppt_deg(d):  # 0=top cw  ->  pptx 0=3o'clock cw
        return (d - 90.0) % 360.0

    for items in slides_items:
        slide = prs.slides.add_slide(blank)
        for it in items:
            kind = it[0]
            if kind in ("rect", "rrect"):
                _, x, y, w, h, o = it
                shp_type = MSO_SHAPE.ROUNDED_RECTANGLE if kind == "rrect" else MSO_SHAPE.RECTANGLE
                sp = slide.shapes.add_shape(shp_type, Inches(x), Inches(y), Inches(w), Inches(h))
                if kind == "rrect" and o["radius"] is not None:
                    try:
                        sp.adjustments[0] = max(min(o["radius"] / min(w, h), 0.5), 0.0)
                    except Exception:
                        pass
                set_fill(sp, o["fill"], o.get("alpha"))
                set_line(sp, o["line"], o["lw"], o["dash"])
                sp.text_frame.paragraphs[0].text = ""
            elif kind == "oval":
                _, x, y, w, h, o = it
                sp = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(w), Inches(h))
                set_fill(sp, o["fill"])
                set_line(sp, o["line"], o["lw"], o["dash"])
            elif kind == "pie":
                _, X, Y, r, a0, a1, inner, o = it
                a0, a1 = to_ppt_deg(a0), to_ppt_deg(a1)
                if inner > 0:
                    sp = slide.shapes.add_shape(MSO_SHAPE.BLOCK_ARC, Inches(X - r), Inches(Y - r),
                                                Inches(2 * r), Inches(2 * r))
                    # blockArc adj3 = inner radius as fraction of shape size (diameter)
                    frac = max(min(inner / (2 * r), 0.49), 0.01)
                    set_adjustments(sp, [("adj1", a0 * 60000), ("adj2", a1 * 60000),
                                         ("adj3", frac * 100000)])
                else:
                    sp = slide.shapes.add_shape(MSO_SHAPE.PIE, Inches(X - r), Inches(Y - r),
                                                Inches(2 * r), Inches(2 * r))
                    set_adjustments(sp, [("adj1", a0 * 60000), ("adj2", a1 * 60000)])
                set_fill(sp, o["fill"])
                set_line(sp, o["line"], o["lw"], None)
            elif kind == "can":
                _, x, y, w, h, o = it
                sp = slide.shapes.add_shape(MSO_SHAPE.CAN, Inches(x), Inches(y), Inches(w), Inches(h))
                set_fill(sp, o["fill"])
                set_line(sp, o["line"], o["lw"], None)
            elif kind == "text":
                _, x, y, w, h, o = it
                add_text(slide, x, y, w, h, o)
            elif kind == "line":
                _, pts, o = it
                for i in range(len(pts) - 1):
                    add_connector(slide, pts[i], pts[i + 1], o, last=(i == len(pts) - 2))
    prs.save(path)


# -------------------------------------------------------- matplotlib backend -

def emit_mpl(items, path, title=None):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle, Ellipse, Wedge
    from matplotlib.lines import Line2D

    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), dpi=110)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, SLIDE_W)
    ax.set_ylim(0, SLIDE_H)
    ax.axis("off")

    def Y(y): return SLIDE_H - y

    def hexc(h):
        return h if (h and h != "none") else "none"

    for it in items:
        kind = it[0]
        if kind in ("rect", "rrect"):
            _, x, y, w, h, o = it
            if kind == "rrect" and o["radius"] is not None:
                p = FancyBboxPatch((x, Y(y + h)), w, h,
                                   boxstyle=f"round,pad=0,rounding_size={o['radius']}",
                                   fc=hexc(o["fill"]), ec=hexc(o["line"]) if o["line"] else "none",
                                   lw=o["lw"], ls="--" if o["dash"] else "-",
                                   alpha=o.get("alpha") or 1.0, mutation_aspect=1)
            else:
                p = Rectangle((x, Y(y + h)), w, h, fc=hexc(o["fill"]),
                              ec=hexc(o["line"]) if o["line"] else "none", lw=o["lw"],
                              ls="--" if o["dash"] else "-", alpha=o.get("alpha") or 1.0)
            ax.add_patch(p)
        elif kind == "oval":
            _, x, y, w, h, o = it
            ax.add_patch(Ellipse((x + w / 2, Y(y + h / 2)), w, h, fc=hexc(o["fill"]),
                                 ec=hexc(o["line"]) if o["line"] else "none", lw=o["lw"],
                                 ls="--" if o["dash"] else "-"))
        elif kind == "pie":
            _, X, Yy, r, a0, a1, inner, o = it
            t0, t1 = 90 - a1, 90 - a0
            ax.add_patch(Wedge((X, Y(Yy)), r, t0, t1, width=(r - inner) if inner > 0 else None,
                               fc=hexc(o["fill"]), ec=hexc(o["line"]) if o["line"] else "none",
                               lw=o["lw"]))
        elif kind == "can":
            _, x, y, w, h, o = it
            eh = 0.22 * h
            ax.add_patch(Rectangle((x, Y(y + h - eh / 2)), w, h - eh, fc=hexc(o["fill"]),
                                   ec=hexc(o["line"]) if o["line"] else "none", lw=o["lw"]))
            ax.add_patch(Ellipse((x + w / 2, Y(y + eh / 2)), w, eh, fc=hexc(lighten(o["fill"], 0.25)),
                                 ec=hexc(o["line"]) if o["line"] else "none", lw=o["lw"]))
            ax.add_patch(Ellipse((x + w / 2, Y(y + h - eh / 2)), w, eh, fc=hexc(o["fill"]),
                                 ec=hexc(o["line"]) if o["line"] else "none", lw=o["lw"]))
        elif kind == "text":
            _, x, y, w, h, o = it
            ha = {"l": "left", "c": "center", "r": "right"}[o["align"]]
            va = {"t": "top", "m": "center", "b": "bottom"}[o["valign"]]
            tx = {"l": x, "c": x + w / 2, "r": x + w}[o["align"]]
            ty = {"t": Y(y), "m": Y(y + h / 2), "b": Y(y + h)}[o["valign"]]
            rot = -o["rotate"] if o["rotate"] else 0
            ax.text(tx, ty, o["s"], fontsize=o["size"], fontweight="bold" if o["bold"] else "normal",
                    fontstyle="italic" if o["italic"] else "normal", color=o["color"],
                    ha=ha, va=va, rotation=rot, linespacing=o["spacing"],
                    family="DejaVu Sans")
        elif kind == "line":
            _, pts, o = it
            xs = [p[0] for p in pts]
            ys = [Y(p[1]) for p in pts]
            ax.add_line(Line2D(xs, ys, color=o["color"], lw=o["lw"],
                               ls="--" if o["dash"] else "-", solid_capstyle="round"))
            ah = o["ah"]
            def head(p0, p1):
                dx, dy = p1[0] - p0[0], Y(p1[1]) - Y(p0[1])
                n = math.hypot(dx, dy) or 1e-9
                dx, dy = dx / n, dy / n
                px, py = -dy, dx
                b = (p1[0] - dx * ah, Y(p1[1]) - dy * ah)
                tri = plt.Polygon([(p1[0], Y(p1[1])), (b[0] + px * ah * 0.45, b[1] + py * ah * 0.45),
                                   (b[0] - px * ah * 0.45, b[1] - py * ah * 0.45)],
                                  fc=o["color"], ec="none")
                ax.add_patch(tri)
            if o["arrow"] in ("end", "both"):
                head(pts[-2], pts[-1])
            if o["arrow"] == "both":
                head(pts[1], pts[0])
    if title:
        ax.text(0.3, SLIDE_H - 0.3, title, fontsize=13, fontweight="bold", ha="left")
    fig.savefig(path, dpi=110)
    plt.close(fig)


# -------------------------------------------------------------------- main --

def main():
    global prs, blank
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview")
    os.makedirs(out_dir, exist_ok=True)

    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    blank = prs.slide_layouts[6]

    slides = [build_composite()] + [build_panel_slide(l) for l, *_ in PANELS]
    pptx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "RNADesignAgent_Fig1_model_schematic.pptx")
    emit_pptx(slides, pptx_path)

    emit_mpl(slides[0], os.path.join(out_dir, "slide1_composite.png"))
    for i, (l, *_rest) in enumerate(PANELS):
        emit_mpl(slides[i + 1], os.path.join(out_dir, f"slide{i + 2}_panel_{l}.png"))
    print("wrote", pptx_path)
    print("previews in", out_dir)


if __name__ == "__main__":
    main()
