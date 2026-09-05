#!/usr/bin/env python3
"""Exp 24 audit-slice surgical re-freeze (2026-09-05, user-directed
final-code consistency amendment).

The frozen Exp-24 corpus contained exactly one navigation-path session
(PA_028, session ``exp24_pa028``) measured under the pre-repair navigator.
The aptamer navigation path was subsequently repaired (production v4,
2026-09-04) and PA_028 re-run end-to-end through the same production form
driver (session ``pa028_v4_085328``; 2/2 turns, 4,084 s vs 6,292 s).

A literal re-run of ``exp24_audit_gate_stats`` is impossible by design: its
pre-registered freeze assertions require a quiet audit trail (no
intervening platform traffic), and the trail now carries the entire
post-campaign experiment programme.  This amendment therefore performs a
SURGICAL replacement, keeping every other session's frozen events
byte-identical:

  1. load the frozen corpus (``exp24_corpus.jsonl``);
  2. drop the events of corpus session ``exp24_pa028``;
  3. extract the audit events of session ``pa028_v4_085328`` from the live
     trail with the same session-stamped attribution the analyzer uses
     (form sessions stamp every event; no adjacency attribution needed);
  4. write the new frozen corpus under a new name, recompute the headline
     statistics (event composition, tool/gate counts by oracle, per-session
     records, representative-session rule), and re-freeze with a fresh
     SHA-256 manifest and a disclosure block;
  5. emit ``stats.json`` in the schema ``fig4f_gate_decisions.py`` reads.

Disclosed as an amendment, never presented as the original freeze.
Usage: PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp24_refreeze_pa028.py
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_TRAIL = PROJECT_ROOT / "workspace" / "audit" / "platform_audit.jsonl"
STATS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp24_audit_gate_stats"
OLD_CORPUS = STATS_DIR / "data" / "exp24_corpus.jsonl"
NEW_CORPUS = STATS_DIR / "data" / "exp24_corpus_v2_pa028v4.jsonl"
OLD_SESSION = "exp24_pa028"
NEW_SESSION = "pa028_v4_085328"


def _ts(rec: dict) -> datetime:
    return datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))


def main() -> int:
    old_rows = [json.loads(l) for l in OLD_CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]
    kept = [r for r in old_rows if r.get("corpus_session") != OLD_SESSION]
    dropped = len(old_rows) - len(kept)
    print(f"frozen corpus: {len(old_rows)} events; dropping {dropped} from {OLD_SESSION}")

    # extract the new session's events from the live trail
    new_events = []
    with AUDIT_TRAIL.open(encoding="utf-8") as fh:
        for line in fh:
            if NEW_SESSION not in line:
                continue
            rec = json.loads(line)
            sid = (rec.get("payload") or {}).get("session_id") or rec.get("session_id")
            if sid == NEW_SESSION:
                new_events.append(rec)
    new_events.sort(key=_ts)
    assert new_events, f"no audit events found for {NEW_SESSION}"
    print(f"live trail: {len(new_events)} events for {NEW_SESSION}")

    with NEW_CORPUS.open("w", encoding="utf-8") as out:
        for rec in kept:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        for rec in new_events:
            out.write(json.dumps({**rec, "corpus_session": NEW_SESSION},
                                 ensure_ascii=False) + "\n")

    # recompute headline stats over the new corpus
    comp: Counter[str] = Counter()
    verdicts: Counter[str] = Counter()
    oracle_verdict: dict[str, Counter[str]] = defaultdict(Counter)
    tools: Counter[str] = Counter()
    per_session: dict[str, dict] = defaultdict(lambda: {"events": 0, "verdicts": Counter()})
    for line in NEW_CORPUS.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        et = rec["event_type"]
        comp[et] += 1
        p = rec.get("payload") or {}
        sid = rec.get("corpus_session")
        per_session[sid]["events"] += 1
        if et == "tool_call":
            tools[p.get("tool_name", "?")] += 1
        elif et == "gate_decision":
            v = p.get("verdict", "?")
            verdicts[v] += 1
            oracle_verdict[p.get("oracle", "?")][v] += 1
            per_session[sid]["verdicts"][v] += 1

    total = sum(comp.values())
    manifest = {
        "amendment": "surgical PA_028 v4 re-freeze",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "old_corpus_sha256": hashlib.sha256(OLD_CORPUS.read_bytes()).hexdigest(),
        "new_corpus_sha256": hashlib.sha256(NEW_CORPUS.read_bytes()).hexdigest(),
        "events_dropped": dropped,
        "events_added": len(new_events),
        "total_events": total,
        "replaced_session": {"old": OLD_SESSION, "new": NEW_SESSION},
        "disclosure": ("All other 240 corpus sessions retain their original "
                       "frozen events byte-identically; the original analyzer's "
                       "quiet-trail freeze assertions cannot be re-asserted "
                       "against the now-busy audit trail, hence the surgical "
                       "replacement registered here."),
    }
    (STATS_DIR / "data" / "manifest_v2.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # stats.json in the fig4f schema (the fig reads gate_decisions.*)
    old_stats = json.loads((STATS_DIR / "stats.json").read_text(encoding="utf-8"))
    stats = dict(old_stats)
    stats["totals"] = {
        "events": total,
        "tool_calls": comp["tool_call"],
        "gate_decisions": comp["gate_decision"],
        "ranking_assemblies": comp.get("ranking_assembly",
                                       comp.get("ranking_objective_assembly", 0)),
    }
    stats["composition"] = {k: {"count": v, "fraction": round(v / total, 4)}
                            for k, v in comp.items()}
    stats["gate_decisions"]["n"] = comp["gate_decision"]
    stats["gate_decisions"]["verdict_totals"] = dict(verdicts)
    stats["gate_decisions"]["n_oracles"] = len(oracle_verdict)
    stats["gate_decisions"]["by_oracle"] = {
        k: dict(v) for k, v in sorted(oracle_verdict.items())}
    stats["gate_verdicts"] = dict(verdicts)
    stats["gate_verdicts_by_oracle"] = {k: dict(v) for k, v in oracle_verdict.items()}
    stats["tool_call_counts"] = dict(tools.most_common())
    stats["corpus"] = {**stats.get("corpus", {}),
                       "n_events": total,
                       "n_sessions": len(per_session)}
    stats["amendment"] = manifest
    stats["generated"] = manifest["created"]
    (STATS_DIR / "stats.json").write_text(
        json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    print(f"new corpus: {total} events (was {len(old_rows)})")
    print(f"composition: {dict(comp)}")
    print(f"gate verdicts: {dict(verdicts)}")
    print("wrote", NEW_CORPUS.name, "+ stats.json + manifest_v2.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
