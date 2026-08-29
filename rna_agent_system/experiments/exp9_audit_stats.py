#!/usr/bin/env python3
"""Experiment 9 (paper §2.2, Fig. 2h): production audit-trail statistics.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2; zero-intervention rule)
---------------------------------------------------------------------------
* Question: what is the composition of the production audit trail left by the
  platform's end-to-end campaign — tool calls vs gate decisions — and what
  does a representative session's milestone track reveal about the record's
  per-event expressiveness (call status, gate verdicts, turn structure)?
* Instrument: a read-only analyzer over ``workspace/audit/platform_audit.jsonl``.
  No platform process is launched and no platform state is touched — running
  more workflows would only append to the trail, so the zero-intervention
  measurement here is to read the trail exactly as the campaign left it. No
  thresholds, no filtering of the trail beyond the corpus rule below.
* Corpus (fixed, user-confirmed 2026-08-27): the audit slice of the 241
  registered Exp-8 runs — all 210 RNADesign-210 tasks + all 31 PA form
  sessions (PA_028 = the amended re-run ``exp8_r2_pa028``), i.e. exactly the
  Fig-2i campaign. The session set is derived 1:1 from the registered Exp-8
  records (``lane_*.jsonl`` + ``pa_batch.jsonl``, latest-record-wins,
  ``success=True`` required), never hand-listed; the four pilot sessions and
  the censored PA_028 original (``exp8_pa028``) drop out of that mapping by
  construction and are inventoried as exclusions.
* Attribution rules: ``tool_call`` events carry a session stamp and are
  attributed directly. ``gate_decision`` / ``ranking_objective_assembly`` /
  ``claim_verdict`` events carry no session stamp (platform record format as
  shipped — not modified); they are attributed by session time window. Hard
  assertions make the attribution provable: (i) the 241 corpus windows are
  pairwise disjoint (the campaign ran strictly sequentially); (ii) zero
  unstamped ``tool_call`` events fall inside the campaign span; (iii) events
  outside every corpus window (service pre-warm / between-lane gaps; the
  excluded pilot and censored windows) belong to no registered run and are
  excluded with full counts disclosed in the manifest.
* Freeze: the selected events are written verbatim (one added provenance key
  ``corpus_session``) to ``data/exp9_corpus.jsonl``; ``MANIFEST.json`` records
  the selection rule, per-category counts, and the source trail's byte size /
  line count / SHA-256 at extraction time. Later appends to the production
  trail cannot change the frozen slice, so the figure is regenerable.
* Metrics: composition counts by event type; distinct tools; call success /
  failure; gate verdicts × oracles; per-session audit summaries; and the
  representative session's full event stream with turn boundaries (gaps > 60 s
  between consecutive attributed events; cross-checked against the registered
  ``n_turns``).
* Representative session (rule registered verbatim with the corpus
  confirmation, 2026-08-27): "multi-turn PA sessions; the one whose attributed
  gate decisions span the most distinct verdict types; ties → the median event
  count among the tied sessions; residual ties → lowest PA number". Event
  count = all attributed events of the session (calls + gates + ranking +
  claims). DISCLOSED CORRECTION: the corpus-confirmation message claimed this
  rule uniquely selects PA_024 — that pre-check compared only the four largest
  PA sessions. The full candidate set contains three sessions with all three
  verdict types (PA_019 / PA_024 / PA_036, all full-length mRNA); the
  registered median tie-break (57 / 186 / 300 attributed events) selects
  **PA_036** (``exp8_pa036``). The rule is applied exactly as registered — no
  post-hoc adjustment toward the earlier claim.
* Pilot: full read-only reconnaissance over the production trail on
  2026-08-27 established the expected values the frozen run must reproduce:
  241 sessions (210 + 31); 8,798 tool calls (8,792 ok / 6 failed; 40 distinct
  tools); 1,377 gate decisions (reject 690 / require_profiling 553 /
  downgrade 134; 11 oracles); 42 ranking-objective assemblies; 0 claim
  verdicts (ClaimGate fires only in multi-node pipeline synthesis, which form
  runs do not exercise); 0 window overlaps; 0 unstamped campaign-span calls.
* Outputs under ``experiments/results/exp9_audit_stats/``:
    data/exp9_corpus.jsonl, MANIFEST.json, stats.json,
    representative_session.json

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp9_audit_stats.py
"""
from __future__ import annotations

import bisect
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXP8_DIR = PROJECT_ROOT / "experiments" / "results" / "exp8_runtime"
AUDIT_TRAIL = PROJECT_ROOT / "workspace" / "audit" / "platform_audit.jsonl"
OUT_DIR = PROJECT_ROOT / "experiments" / "results" / "exp9_audit_stats"
DATA_DIR = OUT_DIR / "data"

UNSTAMPED_TYPES = ("gate_decision", "ranking_objective_assembly", "claim_verdict")
TURN_GAP_S = 60.0  # consecutive-event idle gap that marks a form-turn boundary

# Pilot-derived expectations (read-only reconnaissance, 2026-08-27).
EXPECTED = {
    "n_sessions": 241,
    "n_task": 210,
    "n_pa": 31,
    "tool_call": 8798,
    "tool_ok": 8792,
    "tool_fail": 6,
    "distinct_tools": 40,
    "gate_decision": 1377,
    "gate_reject": 690,
    "gate_require_profiling": 553,
    "gate_downgrade": 134,
    "gate_oracles": 11,
    "ranking_objective_assembly": 42,
    "claim_verdict": 0,
}


def _fail(msg: str) -> None:
    raise SystemExit(f"ASSERTION FAILED: {msg}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_corpus_sessions() -> tuple[dict[str, dict], dict[str, Any]]:
    """Derive the 241 registered-run sessions from the Exp-8 records."""
    task_recs: dict[str, dict] = {}
    for lane in ("lane_cpu.jsonl", "lane_gpu_aptamer.jsonl", "lane_gpu_tertiary.jsonl"):
        for line in (EXP8_DIR / lane).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            task_recs[rec["task_id"]] = rec  # latest record wins
    pa_recs: dict[str, dict] = {}
    pa_all_sids: set[str] = set()
    for line in (EXP8_DIR / "pa_batch.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        pa_all_sids.add(rec["session_id"])
        pa_recs[rec["pa_id"]] = rec  # latest record wins (PA_028 -> r2 re-run)

    tasks = {r["session_id"]: r for r in task_recs.values() if r.get("success")}
    pas = {r["session_id"]: r for r in pa_recs.values() if r.get("success")}
    if len(tasks) != EXPECTED["n_task"]:
        _fail(f"expected {EXPECTED['n_task']} successful task sessions, got {len(tasks)}")
    if len(pas) != EXPECTED["n_pa"]:
        _fail(f"expected {EXPECTED['n_pa']} successful PA sessions, got {len(pas)}")
    if pas.get("exp8_r2_pa028") is None:
        _fail("PA_028 must resolve to the amended re-run exp8_r2_pa028")

    pilot_sids = {
        json.loads(line)["session_id"]
        for line in (EXP8_DIR / "pilot.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    censored = pa_all_sids - set(pas)
    if censored != {"exp8_pa028"}:
        _fail(f"excluded PA sessions expected {{exp8_pa028}}, got {sorted(censored)}")

    return {**tasks, **pas}, {
        "pilot_sessions": sorted(pilot_sids),
        "censored_sessions": sorted(censored),
    }


def main() -> int:
    if not AUDIT_TRAIL.exists():
        _fail(f"audit trail not found: {AUDIT_TRAIL}")
    corpus_recs, exclusions = load_corpus_sessions()
    if len(corpus_recs) != EXPECTED["n_sessions"]:
        _fail(f"expected {EXPECTED['n_sessions']} corpus sessions, got {len(corpus_recs)}")

    excluded_sids = set(exclusions["pilot_sessions"]) | set(exclusions["censored_sessions"])
    stamped: dict[str, list[dict]] = defaultdict(list)
    excluded_window_events: list[dict] = []
    unstamped: list[dict] = []
    line_count = 0
    with open(AUDIT_TRAIL, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            line_count += 1
            rec = json.loads(line)
            sid = (rec.get("payload") or {}).get("session_id")
            if sid in corpus_recs:
                if rec["event_type"] != "tool_call":
                    _fail(f"corpus-stamped event of unexpected type {rec['event_type']}")
                stamped[sid].append(rec)
            elif sid in excluded_sids:
                excluded_window_events.append(rec)
            elif not sid:
                unstamped.append(rec)

    # Corpus windows and disjointness (sequential campaign -> no overlaps).
    windows = sorted(
        (min(r["timestamp"] for r in recs), max(r["timestamp"] for r in recs), sid)
        for sid, recs in stamped.items()
    )
    for (a0, a1, sa), (b0, b1, sb) in zip(windows, windows[1:]):
        if b0 <= a1:
            _fail(f"corpus windows overlap: {sa} and {sb}")
    span_lo, span_hi = windows[0][0], windows[-1][1]
    starts = [w[0] for w in windows]

    def owner(ts: str) -> str | None:
        i = bisect.bisect_right(starts, ts) - 1
        return windows[i][2] if i >= 0 and ts <= windows[i][1] else None

    # Attributed unstamped events (gates / ranking / claims) + exclusions.
    # Unstamped events inside an excluded (pilot / censored) session's window
    # are disclosed separately from true between-session gaps.
    ex_windows = []
    for sid in excluded_sids:
        ts_list = [r["timestamp"] for r in excluded_window_events
                   if (r.get("payload") or {}).get("session_id") == sid]
        if ts_list:
            ex_windows.append((min(ts_list), max(ts_list), sid))

    def excluded_owner(ts: str) -> str | None:
        for a, b, sid in ex_windows:
            if a <= ts <= b:
                return sid
        return None

    attributed: dict[str, list[dict]] = defaultdict(list)
    gap_events: Counter[str] = Counter()
    unstamped_in_excluded: Counter[str] = Counter()
    span_unstamped_calls = 0
    for rec in unstamped:
        if not (span_lo <= rec["timestamp"] <= span_hi):
            continue
        if rec["event_type"] == "tool_call":
            span_unstamped_calls += 1
            continue
        o = owner(rec["timestamp"])
        if o is not None:
            attributed[o].append(rec)
        elif excluded_owner(rec["timestamp"]) is not None:
            unstamped_in_excluded[rec["event_type"]] += 1
        else:
            gap_events[rec["event_type"]] += 1
    if span_unstamped_calls:
        _fail(f"{span_unstamped_calls} unstamped tool_calls inside the campaign span")

    # Frozen slice: every attributed event, original order by timestamp, with
    # the single added provenance key corpus_session.
    frozen: list[dict] = []
    for sid, recs in stamped.items():
        for rec in recs:
            frozen.append((rec["timestamp"], {**rec, "corpus_session": sid}))
    for sid, recs in attributed.items():
        for rec in recs:
            frozen.append((rec["timestamp"], {**rec, "corpus_session": sid}))
    frozen.sort(key=lambda t: t[0])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    slice_path = DATA_DIR / "exp9_corpus.jsonl"
    with open(slice_path, "w", encoding="utf-8") as f:
        for _, rec in frozen:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Composition statistics.
    comp: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    ok = fail = 0
    gated_calls = 0
    verdicts: Counter[str] = Counter()
    oracles: Counter[str] = Counter()
    verdict_by_oracle: dict[str, Counter[str]] = defaultdict(Counter)
    for _, rec in frozen:
        et = rec["event_type"]
        comp[et] += 1
        p = rec.get("payload") or {}
        if et == "tool_call":
            tools[p.get("tool_name")] += 1
            ok += bool(p.get("success"))
            fail += not p.get("success")
            gated_calls += bool(p.get("gated"))
        elif et == "gate_decision":
            verdicts[p.get("verdict")] += 1
            oracles[p.get("oracle")] += 1
            verdict_by_oracle[p.get("oracle")][p.get("verdict")] += 1

    checks = {
        "tool_call": (comp["tool_call"], EXPECTED["tool_call"]),
        "tool_ok": (ok, EXPECTED["tool_ok"]),
        "tool_fail": (fail, EXPECTED["tool_fail"]),
        "distinct_tools": (len(tools), EXPECTED["distinct_tools"]),
        "gate_decision": (comp["gate_decision"], EXPECTED["gate_decision"]),
        "gate_reject": (verdicts["reject"], EXPECTED["gate_reject"]),
        "gate_require_profiling": (
            verdicts["require_profiling"], EXPECTED["gate_require_profiling"]),
        "gate_downgrade": (verdicts["downgrade"], EXPECTED["gate_downgrade"]),
        "gate_oracles": (len(oracles), EXPECTED["gate_oracles"]),
        "ranking_objective_assembly": (
            comp["ranking_objective_assembly"], EXPECTED["ranking_objective_assembly"]),
        "claim_verdict": (comp["claim_verdict"], EXPECTED["claim_verdict"]),
    }
    for name, (got, want) in checks.items():
        if got != want:
            _fail(f"{name}: got {got}, pilot expected {want}")

    # Per-session audit summaries.
    session_rows = []
    for _, _, sid in windows:
        calls = stamped[sid]
        others = attributed[sid]
        g_verdicts = Counter(
            r["payload"].get("verdict") for r in others if r["event_type"] == "gate_decision")
        reg = corpus_recs[sid]
        session_rows.append({
            "session_id": sid,
            "kind": "pa" if "_pa" in sid else "task",
            "workflow": reg.get("workflow"),
            "n_turns": reg.get("n_turns"),
            "tool_calls": len(calls),
            "failed_calls": sum(1 for r in calls if not r["payload"].get("success")),
            "gated_calls": sum(1 for r in calls if r["payload"].get("gated")),
            "gate_reject": g_verdicts.get("reject", 0),
            "gate_require_profiling": g_verdicts.get("require_profiling", 0),
            "gate_downgrade": g_verdicts.get("downgrade", 0),
            "ranking_objective_assembly": sum(
                1 for r in others if r["event_type"] == "ranking_objective_assembly"),
            "claim_verdict": sum(
                1 for r in others if r["event_type"] == "claim_verdict"),
            "window_start": min(r["timestamp"] for r in calls),
            "window_end": max(r["timestamp"] for r in calls),
        })

    # Representative session: registered rule (see docstring).
    pa_rows = [r for r in session_rows if r["kind"] == "pa" and (r["n_turns"] or 1) >= 2]
    max_types = 0
    type_counts: dict[str, int] = {}
    for r in pa_rows:
        n_types = sum(bool(r[k]) for k in
                      ("gate_reject", "gate_require_profiling", "gate_downgrade"))
        type_counts[r["session_id"]] = n_types
        max_types = max(max_types, n_types)
    tied = [r for r in pa_rows if type_counts[r["session_id"]] == max_types]
    marks = {r["session_id"]: (r["tool_calls"] + r["gate_reject"]
                               + r["gate_require_profiling"] + r["gate_downgrade"]
                               + r["ranking_objective_assembly"] + r["claim_verdict"])
             for r in tied}
    med = statistics.median_low(sorted(marks.values()))
    finalists = [sid for sid, m in marks.items() if m == med]
    rep_sid = sorted(finalists)[0]

    # Representative stream + turn boundaries (gaps > TURN_GAP_S).
    rep_events = sorted(
        [*stamped[rep_sid], *attributed.get(rep_sid, [])],
        key=lambda r: r["timestamp"])
    rep_turn_gaps = []
    for a, b in zip(rep_events, rep_events[1:]):
        ta = datetime.fromisoformat(a["timestamp"])
        tb = datetime.fromisoformat(b["timestamp"])
        if (tb - ta).total_seconds() > TURN_GAP_S:
            rep_turn_gaps.append({"after": a["timestamp"], "before": b["timestamp"]})
    rep_reg = corpus_recs[rep_sid]
    if len(rep_turn_gaps) != rep_reg["n_turns"] - 1:
        _fail(f"{rep_sid}: {len(rep_turn_gaps)} turn gaps vs registered n_turns="
              f"{rep_reg['n_turns']}")
    rep_stream = [{
        "timestamp": r["timestamp"],
        "event_type": r["event_type"],
        "tool_name": (r.get("payload") or {}).get("tool_name"),
        "success": (r.get("payload") or {}).get("success"),
        "verdict": (r.get("payload") or {}).get("verdict"),
        "oracle": (r.get("payload") or {}).get("oracle"),
    } for r in rep_events]
    representative = {
        "rule": ("multi-turn PA sessions; most distinct attributed gate verdicts; "
                 "ties -> median attributed event count among tied; residual ties -> "
                 "lowest PA number (registered with the corpus confirmation 2026-08-27)"),
        "correction_disclosure": (
            "The corpus-confirmation message claimed the rule uniquely selects PA_024; "
            "that pre-check compared only the four largest PA sessions. The full "
            "candidate set has three sessions with all three verdict types "
            "(exp8_pa019 / exp8_pa024 / exp8_pa036); the registered median "
            "tie-break selects exp8_pa036. Rule applied as registered."),
        "candidates": {sid: {"verdict_types": type_counts[sid],
                             "attributed_events": (marks.get(sid) if sid in marks else None)}
                       for sid in sorted(type_counts)},
        "tied_sessions": {sid: marks[sid] for sid in sorted(marks)},
        "median_marks": med,
        "selected": rep_sid,
        "registered_record": {k: rep_reg[k] for k in
                              ("pa_id", "workflow", "n_turns", "elapsed_seconds", "success")},
        "turn_gaps": rep_turn_gaps,
        "stream": rep_stream,
    }

    stats = {
        "corpus": {
            "definition": ("audit slice of the 241 registered Exp-8 runs "
                           "(210 RNADesign-210 tasks + 31 PA sessions; PA_028 = exp8_r2_pa028)"),
            "n_sessions": len(corpus_recs),
            "n_task": sum(1 for r in session_rows if r["kind"] == "task"),
            "n_pa": sum(1 for r in session_rows if r["kind"] == "pa"),
            "campaign_span": [span_lo, span_hi],
            "window_overlaps": 0,
            "unstamped_tool_calls_in_span": span_unstamped_calls,
        },
        "composition": {et: comp.get(et, 0) for et in
                        ("tool_call", "gate_decision",
                         "ranking_objective_assembly", "claim_verdict")},
        "tool_calls": {
            "distinct_tools": len(tools),
            "success": ok,
            "failure": fail,
            "gated": gated_calls,
            "by_tool": dict(tools.most_common()),
        },
        "gate_decisions": {
            "by_verdict": dict(verdicts),
            "by_oracle": dict(oracles.most_common()),
            "verdict_by_oracle": {o: dict(v) for o, v in verdict_by_oracle.items()},
        },
        "exclusions": {
            "pilot_sessions": exclusions["pilot_sessions"],
            "censored_sessions": exclusions["censored_sessions"],
            "events_in_excluded_windows": {
                **dict(Counter(r["event_type"] for r in excluded_window_events)),
                **{f"{k}(unstamped,in-window)": v
                   for k, v in unstamped_in_excluded.items()},
            },
            "between_session_gap_events": dict(gap_events),
        },
        "sessions": session_rows,
        "representative": representative,
    }
    (OUT_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "representative_session.json").write_text(
        json.dumps(representative, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "exp9_audit_stats (paper §2.2, Fig. 2h)",
        "source_trail": {
            "path": str(AUDIT_TRAIL.relative_to(PROJECT_ROOT)),
            "bytes": AUDIT_TRAIL.stat().st_size,
            "line_count": line_count,
            "sha256": _sha256(AUDIT_TRAIL),
        },
        "frozen_slice": {
            "path": str(slice_path.relative_to(PROJECT_ROOT)),
            "lines": len(frozen),
            "sha256": _sha256(slice_path),
            "note": ("records verbatim except the added provenance key "
                     "'corpus_session'"),
        },
        "selection_rule": (
            "tool_call: session stamp; gate/ranking/claim: unique session time "
            "window (windows pairwise disjoint, campaign strictly sequential); "
            "events outside every window belong to no registered run and are "
            "excluded with counts"),
        "corpus_definition": stats["corpus"]["definition"],
        "counts": stats["composition"],
        "exclusions": stats["exclusions"],
        "assertions_passed": [
            "241 corpus sessions = 210 tasks + 31 PA (1:1 with registered records)",
            "PA_028 resolves to exp8_r2_pa028 (censored original excluded)",
            "241 windows pairwise disjoint",
            "0 unstamped tool_calls inside the campaign span",
            "all pilot-derived expected counts reproduced",
            f"representative turn gaps == registered n_turns - 1 ({rep_sid})",
        ],
    }
    (OUT_DIR / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"corpus: {len(corpus_recs)} sessions, {len(frozen)} events frozen")
    print(f"composition: {stats['composition']}")
    print(f"representative: {rep_sid} ({len(rep_stream)} events, "
          f"{len(rep_turn_gaps)} turn gaps)")
    print(f"written: {slice_path}, MANIFEST.json, stats.json, representative_session.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
