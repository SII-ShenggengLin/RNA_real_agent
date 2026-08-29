#!/usr/bin/env python3
"""Fig. 2h — production audit trail: representative-session milestone track.

Single panel (BioMedAgent Extended Data Fig. 5–8 style): the session selected
by the pre-registered rule (exp8_pa036, full-length mRNA, 3 turns) — one lane
per form turn, one dot per audited tool call (status-coloured), one diamond
per gate decision (verdict-coloured), small triangles for ranking-objective
assemblies. Turn lanes are split at idle gaps > 60 s between consecutive
audit events (cross-checked against the registered turn count). Everything
drawn derives from the frozen audit records alone.

Figure revision 2026-08-28 (user-directed; no data change — the Exp-9 corpus
and the session selection are untouched): the composition donut at left was
dropped — it carried three numbers the paper already states in the Results
text and the Fig. 2h caption (10,217 events: 8,798 tool calls / 1,377 gate
decisions / 42 ranking assemblies), so the composition now lives there only;
the in-figure panel titles removed (Nature style — the headline lives in the
caption and panels carry letters only, the fig2d/fig2f/fig2i convention);
every text element now shares one font size (6 pt) and one colour (ink black
— the old layout's 4.8–5.6 pt labels antialiased to a pale grey); the legend
moved from floating half-outside the axes into the empty upper-right of the
milestone track, inside the panel; geometry changed from the double-column
two-panel layout to the single-column panel size of fig2b–g.

Colours (palette rev 7): tool calls grey blue; gate decisions by verdict
(reject terracotta, require_profiling sand, downgrade mauve grey); ranking
assemblies khaki; failures (none in this session) would take the held-out
dark warm grey; lane/gap reference lines non-data grey; all text ink black.

Data  : experiments/results/exp9_audit_stats/representative_session.json
        (the composition numbers described in the paper text/caption come
        from experiments/results/exp9_audit_stats/stats.json — not drawn)

Usage : python experiments/plots/fig2h_audit_trail.py
Output : experiments/plots/output/fig2h_audit_trail.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, TEXT, PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp9_audit_stats"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FONT = 6  # single font size for every in-figure text element

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

C_CALL = PALETTE_BY_NAME["grey_blue"]        # #8FA6BB — audited tool calls
C_REJECT = PALETTE_BY_NAME["terracotta"]     # #C08B7C — gate: reject
C_REQPROF = PALETTE_BY_NAME["sand"]          # #D9C3A9 — gate: require_profiling
C_DOWNGRADE = PALETTE_BY_NAME["mauve_grey"]  # #A99AAF — gate: downgrade
C_RANKING = PALETTE_BY_NAME["khaki"]         # #CDBF9E — ranking assemblies
C_FAIL = PALETTE_BY_NAME["dark_warm_grey"]   # #7A7672 — failed calls (none here)

VERDICT_COLOR = {
    "reject": C_REJECT,
    "require_profiling": C_REQPROF,
    "downgrade": C_DOWNGRADE,
}


def _load(name: str) -> dict:
    path = RESULTS_DIR / name
    if not path.exists():
        raise SystemExit(f"{path} not found — run experiments/exp9_audit_stats.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def draw_track(ax, rep: dict) -> None:
    t0 = datetime.fromisoformat(rep["stream"][0]["timestamp"])
    gap_ts = [datetime.fromisoformat(g["after"]) for g in rep["turn_gaps"]]

    # Turn assignment: events before the 1st idle gap -> turn 1, etc.
    lane_marks: list[list[dict]] = [[] for _ in range(len(gap_ts) + 1)]
    n_marks: dict[str, int] = {}
    for ev in rep["stream"]:
        t = datetime.fromisoformat(ev["timestamp"])
        lane = sum(t > g for g in gap_ts)
        x = (t - t0).total_seconds() / 60.0
        et = ev["event_type"]
        if et == "tool_call":
            ok = bool(ev.get("success"))
            mark = {"x": x, "marker": "o", "s": 7,
                    "c": C_CALL if ok else C_FAIL, "key": "call ok" if ok else "call failed",
                    "alpha": 0.75}  # dense same-second bursts stay readable
        elif et == "gate_decision":
            v = ev.get("verdict")
            mark = {"x": x, "marker": "D", "s": 13,
                    "c": VERDICT_COLOR.get(v, C_REJECT), "key": v, "alpha": 1.0}
        else:
            mark = {"x": x, "marker": "v", "s": 10, "c": C_RANKING,
                    "key": "ranking assembly", "alpha": 1.0}
        lane_marks[lane].append(mark)
        n_marks[mark["key"]] = n_marks.get(mark["key"], 0) + 1

    n_lanes = len(lane_marks)
    for lane, marks in enumerate(lane_marks):
        y = n_lanes - lane  # turn 1 on top
        for m in marks:
            ax.scatter(m["x"], y, s=m["s"], marker=m["marker"], c=m["c"],
                       alpha=m["alpha"], edgecolors="white", linewidths=0.3, zorder=4)
        ax.axhline(y - 0.5, color=NEUTRAL_GRID, linewidth=0.4, zorder=1)
    ax.set_ylim(0.3, n_lanes + 1.0)  # headroom: legend clears the y = 2.5 lane line
    ax.set_yticks([n_lanes - i for i in range(n_lanes)])
    ax.set_yticklabels([f"turn {i + 1}" for i in range(n_lanes)], fontsize=FONT)
    ax.tick_params(axis="both", labelsize=FONT, length=1.5, pad=1)

    # Idle turn gaps: light vertical shading at each boundary (between lanes).
    for g in gap_ts:
        x = (g - t0).total_seconds() / 60.0
        ax.axvline(x, color=NEUTRAL_GRID, linewidth=0.5, linestyle=(0, (2, 2)), zorder=1)

    ax.set_xlabel("time within session (min)", fontsize=FONT, labelpad=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # Legend from the mark kinds actually present, in reading order, inside
    # the empty upper-right of the track (turn 1 occupies only x <~ 0.5).
    order = ["call ok", "reject", "require_profiling", "downgrade", "ranking assembly"]
    style = {
        "call ok": ("o", 7, C_CALL),
        "call failed": ("o", 7, C_FAIL),
        "reject": ("D", 13, C_REJECT),
        "require_profiling": ("D", 13, C_REQPROF),
        "downgrade": ("D", 13, C_DOWNGRADE),
        "ranking assembly": ("v", 10, C_RANKING),
    }
    handles = [
        plt.Line2D([], [], marker=style[k][0], linestyle="", markersize=4.2,
                   markerfacecolor=style[k][2], markeredgecolor="white",
                   markeredgewidth=0.3, label=f"{k} ({n_marks[k]})")
        for k in order if k in n_marks
    ]
    leg = ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.99, 0.98),
                    fontsize=FONT, frameon=False, handletextpad=0.2,
                    labelspacing=0.35, markerfirst=True, borderaxespad=0.1)
    for t in leg.get_texts():
        t.set_color(TEXT)


def main() -> int:
    rep = _load("representative_session.json")

    fig_w, fig_h = 88 / 25.4, 50 / 25.4  # single-column panel (fig2b–g geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax_track = fig.add_axes([0.42 / fig_w, 0.34 / fig_h,
                             (fig_w - 0.50) / fig_w, (fig_h - 0.42) / fig_h])
    draw_track(ax_track, rep)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2h_audit_trail.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    print(f"representative: {rep['selected']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
