#!/usr/bin/env python3
"""Fig. 2g — production audit trail: representative-session milestone track
(Exp-24 re-run).

Re-lettered h → g on 2026-09-11 (user direction) when the IRES panel moved
out of Fig. 2 to Supplementary Fig. S1; data and rendering unchanged.

Single panel: the session selected by the pre-registered rule (multi-turn PA
sessions; most distinct gate verdict types; ties → median event count;
residual ties → lowest PA number) — one lane per form turn, one dot per
audited tool call (status-coloured), one diamond per gate decision
(verdict-coloured), small triangles for ranking-objective assemblies. Turn
lanes are split at idle gaps > 60 s between consecutive audit events
(cross-checked against the registry's turn count by the analyzer).
Everything drawn derives from the frozen audit records alone.

Exp-24 shared-instrument re-measurement (2026-09-01): the corpus is the
frozen audit slice of the registered third-reset production campaign
(241 runs; SHA-256 manifest, experiments/exp24_audit_gate_stats.py). The
composition numbers stated in the paper text / caption come from the
analyzer's stats.json — not drawn. No in-figure titles (Nature style — the
headline lives in the caption); every text element one 6-pt ink-black style.

Colours (palette rev 7): tool calls grey blue; gate decisions by verdict
(reject terracotta, require_profiling sand, downgrade mauve grey, allow sage green); ranking
assemblies khaki; failed calls the held-out dark warm grey; lane/gap
reference lines non-data grey; all text ink black.

Data  : experiments/results/exp24_audit_gate_stats/representative_session.json
Usage : python experiments/plots/fig2g_audit_trail.py
Output : experiments/plots/output/fig2g_audit_trail.{pdf,png}
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
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp24_audit_gate_stats"
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
C_ALLOW = PALETTE_BY_NAME["sage_green"]      # #A3B18A — gate: allow (fig4e convention)
C_RANKING = PALETTE_BY_NAME["khaki"]         # #CDBF9E — ranking assemblies
C_FAIL = PALETTE_BY_NAME["dark_warm_grey"]   # #7A7672 — failed calls

VERDICT_COLOR = {
    "reject": C_REJECT,
    "require_profiling": C_REQPROF,
    "downgrade": C_DOWNGRADE,
    "allow": C_ALLOW,
}


def _load(name: str) -> dict:
    path = RESULTS_DIR / name
    if not path.exists():
        raise SystemExit(f"{path} not found — run experiments/exp24_audit_gate_stats.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def draw_track(ax, rep: dict) -> None:
    events = rep["events"]
    t0 = datetime.fromisoformat(events[0]["timestamp"])
    n_lanes = max(ev["turn"] for ev in events)

    # Turn-boundary x positions: the midpoint of each >60 s idle gap (the
    # analyzer assigned turns at those gaps; the boundary line marks the gap).
    gap_mid_x = []
    for prev, cur in zip(events, events[1:]):
        if cur["turn"] != prev["turn"]:
            t_prev = datetime.fromisoformat(prev["timestamp"])
            t_cur = datetime.fromisoformat(cur["timestamp"])
            gap_mid_x.append(((t_prev - t0).total_seconds()
                              + (t_cur - t0).total_seconds()) / 2.0 / 60.0)

    lane_marks: list[list[dict]] = [[] for _ in range(n_lanes)]
    n_marks: dict[str, int] = {}
    for ev in events:
        x = (datetime.fromisoformat(ev["timestamp"]) - t0).total_seconds() / 60.0
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
        lane_marks[ev["turn"] - 1].append(mark)
        n_marks[mark["key"]] = n_marks.get(mark["key"], 0) + 1

    for lane, marks in enumerate(lane_marks):
        y = n_lanes - lane  # turn 1 on top
        for m in marks:
            ax.scatter(m["x"], y, s=m["s"], marker=m["marker"], c=m["c"],
                       alpha=m["alpha"], edgecolors="white", linewidths=0.3, zorder=4)
        ax.axhline(y - 0.5, color=NEUTRAL_GRID, linewidth=0.4, zorder=1)
    ax.set_ylim(0.3, n_lanes + 1.0)  # headroom: legend clears the top lane line
    ax.set_yticks([n_lanes - i for i in range(n_lanes)])
    ax.set_yticklabels([f"turn {i + 1}" for i in range(n_lanes)], fontsize=FONT)
    ax.tick_params(axis="both", labelsize=FONT, length=1.5, pad=1)

    # Idle turn gaps: light vertical dashed line at each boundary midpoint.
    for x in gap_mid_x:
        ax.axvline(x, color=NEUTRAL_GRID, linewidth=0.5, linestyle=(0, (2, 2)), zorder=1)

    ax.set_xlabel("time within session (min)", fontsize=FONT, labelpad=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # Legend from the mark kinds actually present, in reading order, inside
    # the empty upper-right of the track (turn 1 occupies only x <~ 0.5).
    order = ["call ok", "reject", "require_profiling", "downgrade", "allow", "ranking assembly"]
    style = {
        "call ok": ("o", 7, C_CALL),
        "call failed": ("o", 7, C_FAIL),
        "reject": ("D", 13, C_REJECT),
        "require_profiling": ("D", 13, C_REQPROF),
        "downgrade": ("D", 13, C_DOWNGRADE),
        "allow": ("D", 13, C_ALLOW),
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
        out = OUT_DIR / f"fig2g_audit_trail.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    print(f"representative: {rep['session_id']} ({rep['workflow']}, "
          f"{rep['n_turns_gap_rule']} turns by gap rule / "
          f"{rep['n_turns_registry']} registered, {rep['n_events']} events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
