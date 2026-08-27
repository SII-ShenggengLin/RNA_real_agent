#!/usr/bin/env python3
"""Fig. 2i — production audit trail: composition + representative session.

Left: composition donut of the frozen Exp-9 corpus (the audit slice of the
241 registered Exp-8 runs) — tool calls vs gate decisions vs ranking-objective
assemblies (claim verdicts are 0 in this corpus: ClaimGate fires only in
multi-node pipeline synthesis, which form runs do not exercise; noted in the
paper legend, not drawn).

Right: representative-session milestone track (BioMedAgent Extended Data
Fig. 5–8 style) for the session selected by the pre-registered rule
(exp8_pa036, full-length mRNA, 3 turns): one lane per form turn, one dot per
audited tool call (status-coloured), one diamond per gate decision (verdict-
coloured), small triangles for ranking-objective assemblies. Turn lanes are
split at idle gaps > 60 s between consecutive audit events (cross-checked
against the registered turn count). Everything drawn derives from the frozen
audit records alone.

Colours (palette rev 7): tool calls grey blue; gate decisions terracotta with
verdict accents (reject terracotta, require_profiling sand, downgrade mauve
grey); ranking assemblies khaki; failures (none in this session) would take
the held-out dark warm grey.

Data  : experiments/results/exp9_audit_stats/data/exp9_corpus.jsonl
        experiments/results/exp9_audit_stats/representative_session.json
        experiments/results/exp9_audit_stats/stats.json

Usage : python experiments/plots/fig2i_audit_trail.py
Output : experiments/plots/output/fig2i_audit_trail.{pdf,png}
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

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 6,
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


def draw_donut(ax, comp: dict, n_runs: int, n_tools: int, n_oracles: int) -> None:
    labels = [
        ("tool_call", "tool calls"),
        ("gate_decision", "gate decisions"),
        ("ranking_objective_assembly", "ranking assemblies"),
    ]
    present = [(key, lab) for key, lab in labels if comp.get(key, 0) > 0]
    values = [comp[key] for key, _ in present]
    colors = [C_CALL, C_REJECT, C_RANKING][: len(present)]
    total = sum(values)

    def pct(p: float) -> str:
        return f"{p:.1f}%" if p >= 1.0 else ""

    wedges, _, autotexts = ax.pie(
        values, colors=colors, startangle=90, counterclock=False,
        autopct=pct, pctdistance=0.77,
        wedgeprops=dict(width=0.44, edgecolor="white", linewidth=0.8),
        textprops=dict(fontsize=5.6, color=TEXT),
    )
    for t in autotexts:
        t.set_fontsize(5.2)
    ax.text(0, 0.13, f"{total:,}", ha="center", va="center",
            fontsize=8.5, fontweight="bold", color=TEXT)
    ax.text(0, -0.16, "audit events", ha="center", va="center",
            fontsize=5.4, color=TEXT)
    ax.text(0, -0.34, f"{n_runs} runs · {n_tools} tools\n{n_oracles} gate oracles",
            ha="center", va="center", fontsize=4.8, color=TEXT, linespacing=1.4)

    handles = [
        plt.Line2D([], [], marker="s", linestyle="", markersize=4.5,
                   markerfacecolor=c, markeredgecolor="white", markeredgewidth=0.3,
                   label=f"{lab} — {comp[key]:,} ({comp[key] / total * 100:.1f}%)")
        for (key, lab), c in zip(present, colors)
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.02),
              fontsize=5.0, frameon=False, handletextpad=0.15,
              labelspacing=0.3, markerfirst=True)
    ax.set_title("Audit-trail composition", loc="left",
                 fontsize=6.5, pad=3, x=-0.12)


def draw_track(ax, rep: dict) -> None:
    t0 = datetime.fromisoformat(rep["stream"][0]["timestamp"])
    gap_ts = [datetime.fromisoformat(g["after"]) for g in rep["turn_gaps"]]

    # Turn assignment: events before the 1st idle gap -> turn 1, etc.
    lane_colors: list[list[dict]] = [[] for _ in range(len(gap_ts) + 1)]
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
        lane_colors[lane].append(mark)
        n_marks[mark["key"]] = n_marks.get(mark["key"], 0) + 1

    n_lanes = len(lane_colors)
    for lane, marks in enumerate(lane_colors):
        y = n_lanes - lane  # turn 1 on top
        for m in marks:
            ax.scatter(m["x"], y, s=m["s"], marker=m["marker"], c=m["c"],
                       alpha=m["alpha"], edgecolors="white", linewidths=0.3, zorder=4)
        ax.axhline(y - 0.5, color=NEUTRAL_GRID, linewidth=0.4, zorder=1)
    ax.set_ylim(0.3, n_lanes + 0.7)
    ax.set_yticks([n_lanes - i for i in range(n_lanes)])
    ax.set_yticklabels([f"turn {i + 1}" for i in range(n_lanes)], fontsize=5.4)
    ax.tick_params(axis="both", labelsize=5.4, length=1.5, pad=1)

    # Idle turn gaps: light vertical shading at each boundary (between lanes).
    for g in gap_ts:
        x = (g - t0).total_seconds() / 60.0
        ax.axvline(x, color=NEUTRAL_GRID, linewidth=0.5, linestyle=(0, (2, 2)), zorder=1)

    reg = rep["registered_record"]
    n_calls = sum(1 for ev in rep["stream"] if ev["event_type"] == "tool_call")
    n_gates = sum(1 for ev in rep["stream"] if ev["event_type"] == "gate_decision")
    ax.set_title(
        f"Representative session — {reg['pa_id']} "
        f"(full-length mRNA, {reg['n_turns']} turns):\n"
        f"{n_calls} audited calls · {n_gates} gate decisions",
        loc="left", fontsize=6.5, pad=3)
    ax.set_xlabel("time within session (min)", fontsize=6, labelpad=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # Legend from the mark kinds actually present, in reading order.
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
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.135, 1.045),
              fontsize=5.0, frameon=False, handletextpad=0.15,
              labelspacing=0.28, markerfirst=True, ncol=1)


def main() -> int:
    stats = _load("stats.json")
    rep = _load("representative_session.json")
    comp = stats["composition"]

    fig_w, fig_h = 183 / 25.4, 62 / 25.4  # double-column panel (fig2a/2h geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax_donut = fig.add_axes([0.025, 0.30, 0.21, 0.58])
    ax_donut.set_aspect("equal")
    draw_donut(
        ax_donut, comp,
        n_runs=stats["corpus"]["n_sessions"],
        n_tools=stats["tool_calls"]["distinct_tools"],
        n_oracles=len(stats["gate_decisions"]["by_oracle"]),
    )
    ax_track = fig.add_axes([0.335, 0.20, 0.635, 0.66])
    draw_track(ax_track, rep)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2i_audit_trail.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    print(f"composition: {comp}; representative: {rep['selected']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
