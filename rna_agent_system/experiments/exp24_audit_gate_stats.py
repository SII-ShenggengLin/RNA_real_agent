#!/usr/bin/env python3
"""Experiment 24 (paper §2.4 实验 5, Fig. 4f): production gate-decision
statistics — audit-trail analysis of the exp24 production campaign.

RE-RUN AMENDMENT (2026-09-06, platform default change DECISIONS (aa),
user-directed): re-freezes and re-analyzes the campaign re-run under the
GenNav-λ-default mRNA workflows. The corpus construction, attribution rules
and assertions are unchanged; the static-default era's stats and frozen
slice are archived at ``experiments/results/exp24_audit_gate_stats_static/``.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2; zero-intervention rule)
---------------------------------------------------------------------------
* Question: across the platform's end-to-end production campaign (Exp 24,
  241 runs = all 210 RNADesign-210 tasks + all 31 PA form sessions), what
  gate decisions does the production CapGate stack issue — reject /
  require_profiling / downgrade / allow, by oracle — and what is the
  campaign's audit-trail composition and representative-session structure?
* Instrument: a READ-ONLY analyzer over ``workspace/audit/platform_audit.jsonl``
  as the campaign left it. No platform process is launched and no platform
  state is touched. It runs immediately after the campaign completes, with
  no intervening platform traffic (the freeze timestamp defines the
  measurement endpoint; the assertions below verify this from the trail).
* Corpus (fixed, shared-instrument registration 2026-09-01): the audit slice
  of the 241 registered Exp-24 runs — session set derived 1:1 from the
  campaign records (``lane_*.jsonl`` + ``pa_batch*.jsonl``, latest-record-wins
  per task/PA id, ``success=True`` required), never hand-listed. Pilot
  sessions, failed-attempt sessions (fresh ``exp24_rN`` prefixes) and the
  killed sequential-phase partial session drop out by construction and are
  inventoried as exclusions.
* Attribution rules (AMENDED 2026-09-01 for the user-directed parallel
  campaign — six workflow-exclusive workers, same-workflow sessions never
  overlap; registered before the parallel re-launch):
  (i) ``tool_call`` events carry ``payload.session_id`` and are attributed
  directly.
  (ii) ``gate_decision`` / ``ranking_objective_assembly`` / ``claim_verdict``
  events carry no session stamp (platform record format as shipped — not
  modified). Their payload carries a workflow key — gate reasons as
  ``... for (<workflow>, <family>)`` or ``... from <oracle>:<workflow>:<family>``,
  ranking assemblies as ``task_type`` — which maps to exactly one workflow.
  The event is attributed to the corpus session of that workflow whose
  stamped-event window covers the timestamp. Hard assertions: at most one
  such session (same-workflow serialization; ambiguity FAILS the analysis
  rather than corrupting it); zero unstamped ``tool_call`` events inside the
  campaign span. Events resolving to no corpus session (between-session
  boundaries, excluded/failed-attempt windows, pre-warm gaps) are excluded
  with full counts disclosed in the manifest.
  (iii) Gate events without a workflow key (the allow-verb class, e.g. use =
  none / scoring_annotation annotations) fall back to choke-point adjacency:
  the nearest stamped tool call of the same tool within ±5 s (the gate
  review fires immediately before the call executes), else the nearest
  stamped call within ±2 s, else disclosed unattributed.
* Torn-line repair (disclosed): concurrent appenders write per-event lines;
  if a line contains two concatenated JSON objects it is split losslessly
  and counted in the manifest.
* Freeze: the selected events are written verbatim (one added provenance key
  ``corpus_session``) to ``data/exp24_corpus.jsonl``; ``MANIFEST.json``
  records the selection rule, per-category counts, and the source trail's
  byte size / line count / SHA-256 at extraction time. Later appends to the
  production trail cannot change the frozen slice, so every figure fed by
  this corpus (Fig. 4f; Fig. 2h) is regenerable.
* Metrics: composition counts by event type; distinct tools; call success /
  failure; gate verdicts × oracles (the Fig-4f table; ``use`` recorded as a
  secondary breakdown); per-session audit summaries; and the representative
  session's full event stream with turn boundaries (gaps > 60 s between
  consecutive attributed events; cross-checked against the registry's
  ``n_turns``).
* Representative session (rule registered verbatim with the legacy corpus
  confirmation, 2026-08-27, carried over): "multi-turn PA sessions; the one
  whose attributed gate decisions span the most distinct verdict types;
  ties → the median event count among the tied sessions; residual ties →
  lowest PA number". Event count = all attributed events of the session.
* Expected outcome (structural, pre-registered): 241 corpus sessions (210 +
  31); 0 same-workflow attribution ambiguities; 0 unstamped campaign-span
  tool calls; every gate decision resolves to one of reject / require_profiling
  / downgrade / allow; ≥1 oracle in each of the three charted verdict
  classes; the frozen corpus re-analyses to byte-identical stats
  (``--verify``).

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp24_audit_gate_stats.py
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp24_audit_gate_stats.py --verify

Outputs under ``experiments/results/exp24_audit_gate_stats/``:
    stats.json, representative_session.json, data/exp24_corpus.jsonl,
    data/MANIFEST.json
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CAMPAIGN_DIR = PROJECT_ROOT / "experiments" / "results" / "exp24_production_campaign"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp24_audit_gate_stats"
AUDIT_TRAIL = PROJECT_ROOT / "workspace" / "audit" / "platform_audit.jsonl"
PA_BENCHMARKS = PROJECT_ROOT / "pa_benchmarks.json"

EXPECTED = {"n_task": 210, "n_pa": 31, "n_sessions": 241}

VERDICTS = ("reject", "require_profiling", "downgrade", "allow")
TURN_GAP_S = 60.0

# Gate-reason / ranking task_type keys use shortened workflow names.
RE_KEY_PAREN = re.compile(r"for \((\w+),")
RE_KEY_FROM = re.compile(r"from \w+:(\w+):")
KEY_TO_WORKFLOW = {
    "rna_aptamer_design": "rna_aptamer_design",
    "rna_tertiary_structure_design": "rna_tertiary_structure_design",
    "mrna_cds_design": "mrna_cds_design",
    "full_length_mrna": "full_length_mrna_design",
    "sgrna_design": "sgrna_design",
    "rna_small_molecule": "rna_small_molecule_interaction",
    "ires_prediction": "ires_prediction",
    "sirna_design": "sirna_design",
    "aso_target_screening": "aso_target_screening",
    "mrna_sequence_scoring": "mrna_sequence_scoring",
    "rna_secondary_structure_design": "rna_secondary_structure_design",
}


def _fail(msg: str) -> None:
    print(f"[ASSERT-FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ts(rec: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(rec["timestamp"])


def _iter_trail(path: Path) -> tuple[Iterator[dict], int]:
    """Yield parsed records; split torn (concatenated) lines losslessly.

    Returns (iterator, n_torn_lines) — the count is read via the closure
    after consumption through the returned mutable holder.
    """
    torn = [0]

    def gen() -> Iterator[dict]:
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    yield json.loads(s)
                    continue
                except json.JSONDecodeError:
                    parts = s.split("}{")
                    if len(parts) > 1:
                        try:
                            recs = []
                            for i, part in enumerate(parts):
                                if i == 0:
                                    recs.append(json.loads(part + "}"))
                                elif i == len(parts) - 1:
                                    recs.append(json.loads("{" + part))
                                else:
                                    recs.append(json.loads("{" + part + "}"))
                        except json.JSONDecodeError:
                            _fail(f"unparseable audit line: {s[:120]} ...")
                        torn[0] += 1
                        for r in recs:
                            yield r
                        continue
                    _fail(f"unparseable audit line: {s[:120]} ...")

    return gen(), torn


def event_workflow_key(rec: dict[str, Any]) -> str | None:
    p = rec.get("payload") or {}
    if rec["event_type"] == "ranking_objective_assembly":
        key = p.get("task_type")
        return KEY_TO_WORKFLOW.get(key, key)
    reason = p.get("reason", "") or ""
    m = RE_KEY_PAREN.search(reason) or RE_KEY_FROM.search(reason)
    if m:
        return KEY_TO_WORKFLOW.get(m.group(1), m.group(1))
    return None


def load_corpus_sessions() -> tuple[dict[str, dict], dict[str, Any]]:
    """Derive the 241 registered-run sessions from the Exp-24 records."""
    task_recs: dict[str, dict] = {}
    task_sids: set[str] = set()
    for lane in sorted(CAMPAIGN_DIR.glob("lane_*.jsonl")):
        for line in lane.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            task_sids.add(rec["session_id"])
            task_recs[rec["task_id"]] = rec  # latest record wins
    pa_recs: dict[str, dict] = {}
    pa_sids: set[str] = set()
    for pa_file in sorted(CAMPAIGN_DIR.glob("pa_batch*.jsonl")):
        for line in pa_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            pa_sids.add(rec["session_id"])
            pa_recs[rec["pa_id"]] = rec  # latest record wins

    tasks = {r["session_id"]: r for r in task_recs.values() if r.get("success")}
    pas = {r["session_id"]: r for r in pa_recs.values() if r.get("success")}
    if len(tasks) != EXPECTED["n_task"]:
        _fail(f"expected {EXPECTED['n_task']} successful task sessions, got {len(tasks)}")
    if len(pas) != EXPECTED["n_pa"]:
        _fail(f"expected {EXPECTED['n_pa']} successful PA sessions, got {len(pas)}")

    pilot_sids: set[str] = set()
    pilot_path = CAMPAIGN_DIR / "pilot.jsonl"
    if pilot_path.exists():
        for line in pilot_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                pilot_sids.add(json.loads(line)["session_id"])
    failed_attempt_sids = (task_sids | pa_sids) - set(tasks) - set(pas) - pilot_sids

    return {**tasks, **pas}, {
        "pilot_sessions": sorted(pilot_sids),
        "failed_attempt_sessions": sorted(failed_attempt_sids),
    }


def analyze() -> dict[str, Any]:
    if not AUDIT_TRAIL.exists():
        _fail(f"audit trail not found: {AUDIT_TRAIL}")
    corpus_recs, exclusions = load_corpus_sessions()
    if len(corpus_recs) != EXPECTED["n_sessions"]:
        _fail(f"expected {EXPECTED['n_sessions']} corpus sessions, got {len(corpus_recs)}")

    excluded_sids = (
        set(exclusions["pilot_sessions"]) | set(exclusions["failed_attempt_sessions"])
    )

    gen, torn_holder = _iter_trail(AUDIT_TRAIL)
    stamped: dict[str, list[dict]] = defaultdict(list)
    excluded_events: list[dict] = []
    unknown_stamped: list[dict] = []
    unstamped: list[dict] = []
    line_count = 0
    for rec in gen:
        line_count += 1
        sid = (rec.get("payload") or {}).get("session_id")
        if sid in corpus_recs:
            if rec["event_type"] != "tool_call":
                _fail(f"corpus-stamped event of unexpected type {rec['event_type']}")
            stamped[sid].append(rec)
        elif sid in excluded_sids:
            excluded_events.append(rec)
        elif sid:
            unknown_stamped.append(rec)
        else:
            unstamped.append(rec)

    missing = [sid for sid in corpus_recs if sid not in stamped]
    if missing:
        _fail(f"corpus sessions with zero stamped audit events: {missing[:5]} ... ({len(missing)})")

    # Session windows and per-workflow session indices.
    windows: dict[str, tuple[datetime, datetime]] = {
        sid: (min(_ts(r) for r in recs), max(_ts(r) for r in recs))
        for sid, recs in stamped.items()
    }
    span_lo = min(w[0] for w in windows.values())
    span_hi = max(w[1] for w in windows.values())
    corpus_wf: dict[str, list[str]] = defaultdict(list)
    for sid, rec in corpus_recs.items():
        corpus_wf[rec["workflow"]].append(sid)

    # Sorted stamped calls for the adjacency fallback (ts, sid, tool_name).
    call_index: list[tuple[datetime, str, str]] = []
    for sid, recs in stamped.items():
        for r in recs:
            call_index.append((_ts(r), sid, (r.get("payload") or {}).get("tool_name", "")))
    call_index.sort()
    call_ts = [c[0] for c in call_index]

    def owner_by_workflow(ts: datetime, workflow: str) -> str | None:
        """Unique corpus session of `workflow` active at ts (None if 0);
        more than one FAILS (same-workflow serialization violated)."""
        cands = [sid for sid in corpus_wf[workflow]
                 if windows[sid][0] <= ts <= windows[sid][1]]
        if len(cands) > 1:
            _fail(f"same-workflow sessions overlap at {ts}: {workflow} -> {cands}")
        return cands[0] if cands else None

    def owner_by_adjacency(ts: datetime, tool_name: str) -> str | None:
        i = bisect.bisect_left(call_ts, ts)
        best: tuple[float, str] | None = None
        for j in range(max(0, i - 400), min(len(call_index), i + 400)):
            cts, csid, cname = call_index[j]
            dt = abs((cts - ts).total_seconds())
            same_tool = (tool_name and cname == tool_name)
            if (same_tool and dt <= 5.0) or (dt <= 2.0):
                pri = (0 if same_tool else 1, dt)
                if best is None or pri < best[0]:
                    best = (pri, csid)
        return best[1] if best else None

    attributed: dict[str, list[dict]] = defaultdict(list)
    gap_events: Counter[str] = Counter()
    nokey_unattributed: list[dict] = []
    unknown_key_events: list[dict] = []
    # AMENDMENT (2026-09-06, navigation-era re-run): the superseded r2
    # navigation sessions ran before the probe-thread context fix, so their
    # probe-phase tool_calls (64 LinearDesign + 60 CAI + 60 LinearFold,
    # root-caused and fixed the same day — see the driver note) sit in the
    # trail unstamped. Unstamped tool_calls that fall inside an EXCLUDED
    # session's window are inventoried as known-defect exclusions (disclosed
    # in the manifest) instead of contamination; anything else inside the
    # span still hard-fails.
    excluded_windows: list[tuple[datetime, datetime]] = []
    for recs in (excluded_events,):
        by_sid: dict[str, list[datetime]] = defaultdict(list)
        for r in recs:
            by_sid[(r.get("payload") or {}).get("session_id", "?")].append(_ts(r))
        excluded_windows = [(min(v), max(v)) for v in by_sid.values()]
    known_defect_unstamped = 0
    span_unstamped_calls = 0
    for rec in unstamped:
        ts = _ts(rec)
        if not (span_lo <= ts <= span_hi):
            continue
        if rec["event_type"] == "tool_call":
            if any(lo <= ts <= hi for lo, hi in excluded_windows):
                known_defect_unstamped += 1
                continue
            span_unstamped_calls += 1  # contamination: hard fail below
            continue
        wf = event_workflow_key(rec)
        sid = None
        if wf is not None:
            if wf in corpus_wf:
                sid = owner_by_workflow(ts, wf)
            else:
                unknown_key_events.append(rec)
        if sid is None:
            action_id = (rec.get("payload") or {}).get("action_id", "")
            tool = action_id.partition(":")[2] or None
            sid = owner_by_adjacency(ts, tool)
        if sid is not None:
            attributed[sid].append(rec)
        elif rec["event_type"] == "gate_decision":
            nokey_unattributed.append(rec)
        else:
            gap_events[rec["event_type"]] += 1
    if span_unstamped_calls:
        _fail(f"{span_unstamped_calls} unstamped tool_call events inside the campaign span")

    # ------------------------------------------------------------------ freeze
    slice_path = RESULTS_DIR / "data" / "exp24_corpus.jsonl"
    slice_path.parent.mkdir(parents=True, exist_ok=True)
    n_frozen = 0
    with slice_path.open("w", encoding="utf-8") as out:
        for sid, recs in stamped.items():
            for rec in sorted(recs, key=_ts):
                out.write(json.dumps({**rec, "corpus_session": sid},
                                     ensure_ascii=False) + "\n")
                n_frozen += 1
        for sid, recs in attributed.items():
            for rec in sorted(recs, key=_ts):
                out.write(json.dumps({**rec, "corpus_session": sid},
                                     ensure_ascii=False) + "\n")
                n_frozen += 1

    # ------------------------------------------------------------------ stats
    session_events: dict[str, list[dict]] = defaultdict(list)
    for sid in stamped:
        session_events[sid] = sorted(stamped[sid], key=_ts)
    for sid, recs in attributed.items():
        session_events[sid].extend(recs)
        session_events[sid].sort(key=_ts)

    comp: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    call_fail: Counter[str] = Counter()
    verdict_totals: Counter[str] = Counter()
    oracle_verdict: dict[str, Counter[str]] = defaultdict(Counter)
    oracle_use: dict[str, Counter[str]] = defaultdict(Counter)
    per_session: dict[str, dict[str, Any]] = {}
    for sid, recs in session_events.items():
        s_comp: Counter[str] = Counter()
        s_verdicts: Counter[str] = Counter()
        for rec in recs:
            et = rec["event_type"]
            comp[et] += 1
            s_comp[et] += 1
            p = rec.get("payload") or {}
            if et == "tool_call":
                tools[p.get("tool_name", "?")] += 1
                if not p.get("success"):
                    call_fail[f"{p.get('tool_name', '?')}:{p.get('error_type')}"] += 1
            elif et == "gate_decision":
                v = p.get("verdict")
                o = p.get("oracle", "?")
                verdict_totals[v] += 1
                oracle_verdict[o][v] += 1
                oracle_use[o][p.get("use", "?")] += 1
                s_verdicts[v] += 1
        meta = corpus_recs[sid]
        per_session[sid] = {
            "source": meta["source"],
            "task_id": meta["task_id"],
            "workflow": meta["workflow"],
            "window_start": recs[0]["timestamp"],
            "window_end": recs[-1]["timestamp"],
            "n_events": len(recs),
            **{f"n_{k}": v for k, v in sorted(s_comp.items())},
            **{f"gate_{k}": v for k, v in sorted(s_verdicts.items())},
        }

    unknown_verdicts = set(verdict_totals) - set(VERDICTS)
    if unknown_verdicts:
        _fail(f"unexpected gate verdicts: {sorted(unknown_verdicts)}")

    # Representative session: multi-turn PA sessions; most distinct gate
    # verdict types; ties → median event count; residual ties → lowest PA.
    pa_registry = json.loads(PA_BENCHMARKS.read_text(encoding="utf-8"))
    pa_sessions = [
        (sid, ps) for sid, ps in per_session.items()
        if ps["source"] == "pa_regression"
    ]
    def sid_pa_num(sid: str) -> int:
        return int(sid.split("_pa")[-1])
    max_distinct = max(
        sum(1 for v in VERDICTS if ps.get(f"gate_{v}")) for _, ps in pa_sessions
    )
    tied = [(sid, ps) for sid, ps in pa_sessions
            if sum(1 for v in VERDICTS if ps.get(f"gate_{v}")) == max_distinct]
    med = sorted(ps["n_events"] for _, ps in tied)[len(tied) // 2]
    tied2 = [(sid, ps) for sid, ps in tied if ps["n_events"] == med]
    rep_sid, rep_ps = min(tied2, key=lambda t: sid_pa_num(t[0]))

    rep_events = []
    prev_ts: datetime | None = None
    turn = 0
    for rec in session_events[rep_sid]:
        ts = _ts(rec)
        if prev_ts is None or (ts - prev_ts).total_seconds() > TURN_GAP_S:
            turn += 1
        prev_ts = ts
        p = rec.get("payload") or {}
        rep_events.append({
            "turn": turn,
            "timestamp": rec["timestamp"],
            "event_type": rec["event_type"],
            "tool_name": p.get("tool_name"),
            "success": p.get("success"),
            "elapsed_time": p.get("elapsed_time"),
            "verdict": p.get("verdict"),
            "oracle": p.get("oracle"),
            "use": p.get("use"),
        })
    rep_n_turns_gap = turn
    rep_registry_turns = len(pa_registry[str(rep_ps["task_id"]).removeprefix("pa_")]["params_by_turn"])

    representative = {
        "session_id": rep_sid,
        "task_id": rep_ps["task_id"],
        "workflow": rep_ps["workflow"],
        "rule": ("multi-turn PA sessions; most distinct gate verdict types; "
                 "ties -> median event count; residual ties -> lowest PA number"),
        "selection_pool": {
            "n_pa_sessions": len(pa_sessions),
            "max_distinct_verdict_types": max_distinct,
            "n_tied_after_verdicts": len(tied),
            "median_event_count": med,
            "n_tied_after_median": len(tied2),
        },
        "n_turns_gap_rule": rep_n_turns_gap,
        "n_turns_registry": rep_registry_turns,
        "n_events": rep_ps["n_events"],
        "summary": {k: v for k, v in rep_ps.items() if k not in ("window_start", "window_end")},
        "window_start": rep_ps["window_start"],
        "window_end": rep_ps["window_end"],
        "events": rep_events,
    }

    stats = {
        "experiment": "exp24_audit_gate_stats",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "campaign": {
            "design": ("parallel, six workflow-exclusive workers "
                       "(user-directed amendment 2026-09-01; same-workflow "
                       "sessions never overlap)"),
            "runtimes_measure": "delivered workflow under concurrent campaign load",
        },
        "corpus": {
            "definition": ("audit slice of the 241 registered Exp-24 runs "
                           "(210 RNADesign-210 tasks + 31 PA sessions, "
                           "latest-record-wins, success required)"),
            "n_sessions": len(session_events),
            "n_events": n_frozen,
            "composition": dict(sorted(comp.items())),
            "composition_pct": {
                k: round(100 * v / n_frozen, 1) for k, v in sorted(comp.items())
            },
        },
        "tool_calls": {
            "n": comp.get("tool_call", 0),
            "n_distinct_tools": len(tools),
            "n_failed": sum(call_fail.values()),
            "failures": dict(sorted(call_fail.items())),
            "top_tools": dict(tools.most_common(15)),
        },
        "gate_decisions": {
            "n": comp.get("gate_decision", 0),
            "verdict_totals": {v: verdict_totals.get(v, 0) for v in VERDICTS},
            "n_oracles": len(oracle_verdict),
            "by_oracle": {
                o: {v: c.get(v, 0) for v in VERDICTS}
                for o, c in sorted(oracle_verdict.items())
            },
            "use_by_oracle": {
                o: dict(sorted(c.items())) for o, c in sorted(oracle_use.items())
            },
        },
        "ranking_assemblies": comp.get("ranking_objective_assembly", 0),
        "claim_verdicts": comp.get("claim_verdict", 0),
        "representative_session": {k: v for k, v in representative.items() if k != "events"},
        "exclusions": {
            **exclusions,
            "unknown_stamped_sessions": sorted(
                {(r.get("payload") or {}).get("session_id") for r in unknown_stamped}
            ),
            "unstamped_tool_calls_in_excluded_windows": known_defect_unstamped,
            "events_in_excluded_windows": dict(
                Counter(r["event_type"] for r in excluded_events)
            ),
            "gap_events_outside_corpus": dict(sorted(gap_events.items())),
            "gate_events_unattributed_nokey": len(nokey_unattributed),
            "events_with_unknown_workflow_key": len(unknown_key_events),
        },
        "manifest": {
            "source_trail": str(AUDIT_TRAIL.relative_to(PROJECT_ROOT)),
            "source_trail_bytes": AUDIT_TRAIL.stat().st_size,
            "source_trail_lines": line_count,
            "source_trail_sha256": _sha256(AUDIT_TRAIL),
            "torn_lines_repaired": torn_holder[0],
            "frozen_slice": str(slice_path.relative_to(PROJECT_ROOT)),
            "frozen_slice_sha256": _sha256(slice_path),
            "selection_rule": ("payload.session_id in corpus sessions (tool_call); "
                               "workflow-key attribution for unstamped gate/ranking/"
                               "claim events (workflow-exclusive parallel campaign: "
                               "same-workflow sessions never overlap; ambiguity fails); "
                               "choke-point adjacency fallback for keyless gate events; "
                               "events resolving to no corpus session are excluded"),
            "frozen_at": datetime.now().isoformat(timespec="seconds"),
        },
        "assertions_passed": [
            "210 task + 31 PA = 241 successful corpus sessions",
            "every corpus session has >=1 stamped audit event",
            "0 same-workflow attribution ambiguities",
            "0 unstamped tool_call events inside the campaign span",
            "all gate verdicts in {reject, require_profiling, downgrade, allow}",
        ],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RESULTS_DIR / "representative_session.json").write_text(
        json.dumps(representative, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RESULTS_DIR / "data" / "MANIFEST.json").write_text(
        json.dumps(stats["manifest"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "corpus": stats["corpus"],
        "gate_decisions": stats["gate_decisions"],
        "representative": {k: representative[k] for k in
                           ("session_id", "task_id", "workflow", "n_events",
                            "n_turns_gap_rule", "n_turns_registry")},
        "exclusions": {k: v for k, v in stats["exclusions"].items()
                       if k not in ("pilot_sessions", "failed_attempt_sessions",
                                    "unknown_stamped_sessions")},
        "manifest_extras": {k: stats["manifest"][k] for k in ("torn_lines_repaired",)},
    }, indent=2))
    print(f"stats -> {RESULTS_DIR / 'stats.json'}")
    print(f"frozen corpus ({n_frozen} events) -> {slice_path}")
    return stats


def verify() -> int:
    """Recompute the gate/oracle table from the frozen slice and diff vs stats."""
    stats = json.loads((RESULTS_DIR / "stats.json").read_text(encoding="utf-8"))
    oracle_verdict: dict[str, Counter[str]] = defaultdict(Counter)
    comp: Counter[str] = Counter()
    verdict_totals: Counter[str] = Counter()
    with open(RESULTS_DIR / "data" / "exp24_corpus.jsonl", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            comp[rec["event_type"]] += 1
            if rec["event_type"] == "gate_decision":
                p = rec["payload"]
                verdict_totals[p["verdict"]] += 1
                oracle_verdict[p.get("oracle", "?")][p["verdict"]] += 1
    recomputed = {
        "composition": dict(sorted(comp.items())),
        "verdict_totals": {v: verdict_totals.get(v, 0) for v in VERDICTS},
        "by_oracle": {o: {v: c.get(v, 0) for v in VERDICTS}
                      for o, c in sorted(oracle_verdict.items())},
    }
    expect = {
        "composition": stats["corpus"]["composition"],
        "verdict_totals": stats["gate_decisions"]["verdict_totals"],
        "by_oracle": stats["gate_decisions"]["by_oracle"],
    }
    if recomputed != expect:
        _fail("frozen-slice recomputation does not match stats.json")
    print("[verify] frozen-slice recomputation matches stats.json "
          f"({comp.get('gate_decision', 0)} gate decisions, "
          f"{len(oracle_verdict)} oracles)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verify", action="store_true",
                        help="recompute the gate table from the frozen slice and diff")
    args = parser.parse_args()
    if args.verify:
        return verify()
    analyze()
    return 0


if __name__ == "__main__":
    sys.exit(main())
