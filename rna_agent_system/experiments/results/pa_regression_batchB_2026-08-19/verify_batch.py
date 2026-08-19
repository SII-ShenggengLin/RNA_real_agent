"""Batch-B verification analysis: per-session results, audit attribution,
GenNav navigation traces.

Usage (from rna_agent_system/): python experiments/results/pa_regression_batchB_2026-08-19/verify_batch.py
"""
from __future__ import annotations

import glob
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PAS = [f"{n:03d}" for n in range(25, 37)]
SESSIONS = ROOT / "workspace" / "sessions"
AUDIT = ROOT / "workspace" / "audit" / "platform_audit.jsonl"

summary = json.loads((ROOT / "pa_benchmarks.json").read_text())

# ── audit trail: tool_call events, session-stamped where available ──────────
audit_events = [json.loads(l) for l in AUDIT.read_text().splitlines() if l.strip()]
tool_calls = [e for e in audit_events if e["event_type"] == "tool_call"]
by_session: Counter[str] = Counter()
stamped = 0
for e in tool_calls:
    sid = e["payload"].get("session_id", "")
    if sid:
        stamped += 1
        by_session[sid] += 1
other_events = Counter(e["event_type"] for e in audit_events if e["event_type"] != "tool_call")
print(f"audit trail: {len(audit_events)} events total; {len(tool_calls)} tool_call "
      f"({stamped} session-stamped)")
print(f"other event types: {dict(other_events)}")

# ── per-PA session verdicts ──────────────────────────────────────────────────
rows = []
for pa in PAS:
    sid = f"pa{pa}_batchB"
    n_turns_expected = len(summary[pa]["params_by_turn"])
    result_files = sorted(glob.glob(str(SESSIONS / sid / "workflow_results_*.json")),
                          key=lambda f: Path(f).stat().st_mtime)[-n_turns_expected:]
    turns = []
    gennav = None
    for rf in result_files:
        d = json.loads(Path(rf).read_text())
        turns.append({
            "success": d.get("success"),
            "candidates": len(d.get("candidates", [])),
            "trace_records": len(d.get("trace", [])),
            "quality": (d.get("_quality_review") or {}).get("operation")
                       if isinstance(d.get("_quality_review"), dict) else None,
            "gennav_trace": bool(d.get("_gennav_trace")),
        })
        if d.get("_gennav_trace"):
            gennav = d["_gennav_trace"]
    rows.append((pa, summary[pa]["workflow"], len(summary[pa]["params_by_turn"]), turns, gennav))

print(f"\n{'pa':<4}{'workflow':<34}{'turns':<6}{'results':<9}{'ok':<4}{'cands':<7}{'trace':<7}{'audit'}")
all_ok = True
for pa, wf, n_turns, turns, gennav in rows:
    n_res = len(turns)
    ok = n_res == n_turns and all(t["success"] for t in turns)
    all_ok &= ok
    cands = sum(t["candidates"] for t in turns)
    trace = sum(t["trace_records"] for t in turns)
    audit_n = by_session.get(f"pa{pa}_batchB", 0)
    print(f"{pa:<4}{wf:<34}{n_turns:<6}{n_res:<9}{'✓' if ok else '✗':<4}{cands:<7}{trace:<7}{audit_n}")
    if gennav:
        d = gennav["deliveries"]
        print(f"     GenNav: raw_spent {gennav['raw_spent']}/{gennav['raw_budget']}, "
              f"pool {gennav['pool_size']}, rounds {len(gennav['rounds'])} "
              f"({Counter(r['kind'] for r in gennav['rounds'])}), "
              f"final_gaps {gennav['final_gaps']}, "
              f"delivered " + ", ".join(
                  f"{p} {len(d[p]['ids'])}/5{' degraded' if d[p]['degraded'] else ''}"
                  for p in d))

print(f"\nALL_OK={all_ok}")
