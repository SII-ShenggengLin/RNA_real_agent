#!/usr/bin/env python3
"""Fig 4h data assembly (Exp 25 companion): per-campaign LLM usage, measured.

Registers the LLM-usage dataset of Fig. 4h (bubble strip, the BioMedAgent 3e
convention) from the third-reset campaigns re-run to date. Every count is
measured from frozen campaign records — never assumed:

* ``exp5_ungated_control``   — per-task ``llm_calls`` in runs.jsonl (45 tasks)
* ``exp17_gated``            — per-task ``llm_calls`` in runs.jsonl (45 tasks)
* ``exp18_mrna_dual_arm``    — per-task ``llm_calls`` in runs_ungated/gated
                               (20 tasks × 2 arms, kept runs only)
* ``exp23_selective_gating`` — summary ``llm_calls`` = 0 (12 cells)
* ``exp24_production_campaign`` — MEASURED from the campaign's session
  workspaces: each run's saved ``workflow_results_*.json`` carries
  ``_diagnosis_history`` (one entry per completed advisory review call;
  structurally 2 per passing reviewed turn), summed per session id over the
  frozen run records (210 suite tasks + 31 PA sessions).
* ``exp25_quality_advisory`` — this experiment's three arms (off / on /
  fail-injected): successful review calls per session from records.jsonl;
  the fail arm's attempts all error before any completion (counted
  separately as failed attempts, zero successful).
* The navigation campaigns — re-run under the reset since the 2026-09-01
  registration of this assembly and now included (the earlier exclusion
  note retired): Exp 27/28 (mRNA endpoint) and Exp 29 (aptamer arc +
  expanded budget sweep) are deterministic in both arms — ``llm_calls`` = 0
  read from each segment's verdict file; Exp 30 (production navigation
  through the form entry, quality review on) and Exp 37 (Table-1 case
  studies) are MEASURED from their session workspaces like Exp 24.

Output: experiments/results/exp25_quality_review_advisory/fig4h_llm_usage.json
Usage : PYTHONPATH=. python experiments/exp25_fig4h_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT_ROOT / "experiments" / "results"
OUT_PATH = RESULTS / "exp25_quality_review_advisory" / "fig4h_llm_usage.json"


def _records(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _session_review_calls(session_id: str) -> int:
    """Measured review calls for one exp24 run (sum over its saved results)."""
    total = 0
    for p in (PROJECT_ROOT / "workspace" / "sessions" / session_id).glob("workflow_results_*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        total += len(d.get("_diagnosis_history") or [])
    return total


def campaign(name: str, per_task: list[int], note: str, **extra) -> dict:
    n = len(per_task)
    return {
        "campaign": name,
        "n_tasks": n,
        "per_task_llm_calls": per_task,
        "total_llm_calls": sum(per_task),
        "mean_llm_calls_per_task": round(sum(per_task) / n, 3) if n else None,
        "note": note,
        **extra,
    }


def main() -> int:
    campaigns: list[dict] = []

    # Exp 5 — ungated control (45 tasks)
    rows = _records(RESULTS / "exp5_claim_overreach" / "runs.jsonl")
    campaigns.append(campaign(
        "exp5_ungated_control",
        [int(r.get("llm_calls", 0)) for r in rows],
        "claim-overreach ungated control: plan + report, 2 LLM calls/task",
    ))

    # Exp 17 — gated treatment (45 tasks; single runs.jsonl, both arms keyed)
    rows = [r for r in _records(RESULTS / "exp17_claim_gating" / "runs.jsonl") if r.get("arm") == "gated"]
    campaigns.append(campaign(
        "exp17_gated",
        [int(r.get("llm_calls", 0)) for r in rows],
        "claim-gating gated arm: plan + report, 2 LLM calls/task",
    ))

    # Exp 18 — mRNA-side dual arm (20 tasks × 2 arms, kept runs)
    per_task: list[int] = []
    for part in ("runs_ungated.jsonl", "runs_gated.jsonl"):
        per_task += [int(r.get("llm_calls", 0)) for r in _records(RESULTS / "exp18_mrna_claim_gating" / part)]
    campaigns.append(campaign(
        "exp18_mrna_dual_arm",
        per_task,
        "E3-M mRNA dual arm: plan + report per task per arm (40 runs, kept records only)",
    ))

    # Exp 23 — selective gating decision matrix (12 cells, zero LLM)
    s23 = json.loads((RESULTS / "exp23_selective_gating" / "summary.json").read_text(encoding="utf-8"))
    n23 = 12
    campaigns.append(campaign(
        "exp23_selective_gating",
        [0] * n23,
        f"decision-matrix cells, zero LLM calls (summary llm_calls={s23.get('llm_calls')})",
    ))

    # Exp 24 — production campaign (210 suite tasks + 31 PA sessions), measured
    ex24 = RESULTS / "exp24_production_campaign"
    runs: list[dict] = []
    for p in sorted(ex24.glob("lane_*.jsonl")):
        runs += _records(p)
    for p in sorted(ex24.glob("pa_batch_w*.jsonl")):
        runs += _records(p)
    per_task = []
    missing = 0
    for r in runs:
        sid = r.get("session_id")
        if not sid:
            missing += 1
            continue
        per_task.append(_session_review_calls(sid))
    campaigns.append(campaign(
        "exp24_production_campaign",
        per_task,
        "241 production form runs (210 suite + 31 PA): advisory QualityAgent review calls only — "
        "measured as the sum of _diagnosis_history entries over each run's saved results JSONs",
        n_runs=len(runs),
        sessions_without_results_json=missing,
    ))

    # Exp 25 — this experiment's three arms
    e25 = RESULTS / "exp25_quality_review_advisory" / "records.jsonl"
    if e25.exists():
        recs = [r for r in _records(e25) if not r.get("pilot")]
        arms: dict[str, list[int]] = {}
        failed_attempts: dict[str, int] = {}
        for r in recs:
            arms.setdefault(r["arm"], []).append(int(r.get("total_successful_review_calls", 0)))
            failed_attempts[r["arm"]] = failed_attempts.get(r["arm"], 0) + int(r.get("total_failed_review_calls", 0))
        notes = {
            "off": "quality review disabled: zero LLM calls (the off-arm)",
            "on": "production quality review on: successful review calls per session (2 per passing reviewed turn)",
            "fail": "LLM failure injected: every attempted review call errors into audit metadata — "
                    "zero successful calls; failed attempts counted separately",
        }
        for arm in ("off", "on", "fail"):
            if arm in arms:
                campaigns.append(campaign(
                    f"exp25_quality_{arm}",
                    arms[arm],
                    notes[arm],
                    failed_review_attempts=failed_attempts.get(arm, 0),
                ))

    # Navigation campaigns — re-run under the reset since the 2026-09-01
    # registration of this assembly; measured, not assumed. Exp 27/28 (mRNA
    # endpoint) and Exp 29 (aptamer arc + expanded sweep) are deterministic
    # in both arms: llm_calls read from each segment's verdict file. Exp 30
    # (production navigation through the form entry, quality review on) and
    # Exp 37 (Table-1 case studies) are measured from their session
    # workspaces like Exp 24.
    def _zero_row(verdicts: list[Path]) -> list[int]:
        per: list[int] = []
        for v in verdicts:
            d = json.loads(v.read_text(encoding="utf-8"))
            assert int(d.get("llm_calls") or 0) == 0, f"{v} reports non-zero llm_calls"
            n = int(d.get("n_targets") or 0)
            assert n > 0, f"{v} carries no n_targets"
            per += [0] * n
        return per

    campaigns.append(campaign(
        "exp27_gennav_mrna_boundary",
        _zero_row([RESULTS / "exp27_gennav_mrna_endpoint" / "full" / "verdict.json"]),
        "mRNA navigation endpoint, pre-repair boundary measurement — deterministic, zero LLM calls",
    ))
    campaigns.append(campaign(
        "exp28_gennav_mrna_endpoint",
        _zero_row([RESULTS / "exp28_gennav_mrna_endpoint_v2" / "full" / "verdict.json"]),
        "mRNA navigation endpoint on the repaired shipped navigator — deterministic, zero LLM calls",
    ))
    arc = RESULTS / "exp29_aptamer_campaign_arc"
    campaigns.append(campaign(
        "exp29_aptamer_arc",
        _zero_row([arc / s / "verdict.json" for s in
                   ("seg1_migration", "seg2_reanchor", "seg3_decisive", "seg4_confirmation")]),
        "aptamer navigation campaign arc (four segments) — deterministic, zero LLM calls",
    ))
    campaigns.append(campaign(
        "exp29_expanded_sweep",
        _zero_row([arc / f"expanded_cap{c}" / "full_pool_verdict.json" for c in (16, 20, 24, 32, 48)]),
        "aptamer expanded-pool budget sweep (39 targets × 5 caps) — deterministic, zero LLM calls",
    ))

    def _measured_sessions(session_ids: list[str]) -> list[int]:
        return [_session_review_calls(sid) for sid in session_ids]

    e30 = RESULTS / "exp30_production_navigation_live"
    e30_sids: list[str] = []
    for part in ("aptamer", "mrna"):
        for r in _records(e30 / part / "runs.jsonl"):
            if r.get("session_id"):
                e30_sids.append(r["session_id"])
    campaigns.append(campaign(
        "exp30_production_navigation",
        _measured_sessions(e30_sids),
        "production navigation on new targets through the user form entry (quality review on): "
        "advisory review calls per session",
    ))
    e37 = RESULTS / "exp37_table1_case_studies"
    e37_sids = [json.loads((e37 / c / "record.json").read_text(encoding="utf-8"))["session_id"]
                for c in ("caseA", "caseB", "caseC")]
    campaigns.append(campaign(
        "exp37_case_studies",
        _measured_sessions(e37_sids),
        "Table-1 end-to-end case studies on the platform defaults (quality review on): "
        "advisory review calls per case",
    ))

    out = {
        "registered": "2026-09-01, Exp 25 (Fig 4h): per-campaign LLM usage — measured counts only; "
                      "2026-09-09: navigation campaigns added after their reset re-runs "
                      "(Exp 27/28/29 zero-LLM; Exp 30/37 measured from session workspaces)",
        "campaigns": campaigns,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[exp25 fig4h] wrote {OUT_PATH}")
    for c in campaigns:
        print(
            f"  {c['campaign']:28s} n={c['n_tasks']:3d} total={c['total_llm_calls']:4d} "
            f"mean={c['mean_llm_calls_per_task']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
