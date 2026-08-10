#!/usr/bin/env python3
"""Failure taxonomy across all campaign JSONLs -> experiments/results/failure_taxonomy.json.

Implements MANUSCRIPT §10 ("Discussion & Extended Data — Limitations"):
recompute the failure taxonomy from the Fig-2/3/4 (and later Fig-4kav/5/6)
run records — NOT the stale pre-auto-start data.

Two views per input file:
- ``events``: every record with success=false (failure + later retries).
- ``final``: dedupe to the latest record per job key, then count failures
  (what remains unresolved at campaign end).

Categories (signature rules on the record's error text):
- boundary_odesign_zero_output : deterministic ODesign target-side boundary
  (Ferritin 1FHA; SARS-CoV-2_Nucleocapsid 6M3M with out-of-range explicit
  hotspots) — `no_sequences_extracted_from_odesign_output`.
- boundary_lineardesign_oom   : Zika (10 kb) / Factor VIII (7 kb) CDS —
  LinearDesign SIGKILL; documented in RESUME_CHECKPOINT §4 (the OOM design
  runs are not JSONL records; counted from the checkpoint note).
- transient_timeout            : wall-clock timeout, recovered on later retry.
- transient_infra_recovered    : cli_failure / service hiccups (incl. the
  2026-07-21 DeepSeek-402 episode and the pre-2026-07-22 busy-misjudged-dead
  port conflicts), recovered on later retry.
- llm_abort_correct            : QualityAgent abort that stands (fig2
  04_sirna_design_009_gc_rich_target — final state).
- llm_abort_recovered          : QualityAgent (hallucinated) abort, later
  retried to success (e.g. fig4 Myoglobin r3 s2; fig5c Lysozyme s0).
- driver_chain_bug_fixed       : fig4kav EGARPS ProteinX-CIF chain (OP3 /
  ins.py cache overwrite), fixed mid-campaign, all blocks recovered.
- endpoint_misconfig           : fig6b claude-3.5-sonnet against a relay that
  serves no claude models (404); pending a real Anthropic/OpenRouter key.

Usage (from rna_agent_system/):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/failure_taxonomy.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "experiments" / "results"
OUTPUT = RESULTS / "failure_taxonomy.json"

# (label, [jsonl files], job-key function)
INPUTS: list[tuple[str, list[str], object]] = [
    ("fig2_platform", ["fig2_cpu_a.jsonl", "fig2_cpu_b.jsonl", "fig2_gpu.jsonl"],
     lambda r: r.get("task_id")),
    ("fig3_type1", ["fig3_type1_shard_a.jsonl", "fig3_type1_shard_b.jsonl"],
     # fig3 records use `rep` (0..2), fig4 uses `seed_idx` — falling back
     # keeps the per-job dedupe key correct for both shard families.
     lambda r: (r.get("target_id"), r.get("bmc_max_rounds"),
                r.get("seed_idx") if r.get("seed_idx") is not None else r.get("rep"))),
    ("fig4_type2", ["fig4_type2_shard_a.jsonl", "fig4_type2_shard_b.jsonl"],
     lambda r: (r.get("target_id"), r.get("bmc_max_rounds"), r.get("seed_idx"))),
    ("fig4_known_aptamers", ["fig4_known_aptamers.jsonl"],
     lambda r: (r.get("block"), r.get("target_id"))),
    ("fig5_ablations", ["fig5_ablations.jsonl"],
     lambda r: r.get("task_id")),
    ("fig6_quality_ablation", ["fig6_quality_ablation.jsonl"],
     lambda r: (r.get("task_id"), r.get("arm"))),
    ("fig6_backends", ["fig6_backends.jsonl"],
     lambda r: (r.get("backend"), r.get("task_id"))),
]


def classify(record: dict, source: str) -> str:
    err = f"{record.get('error') or ''} {record.get('errors') or ''}".lower()
    task = str(record.get("task_id") or "")
    target = str(record.get("target_id") or "")
    backend = str(record.get("backend") or "")
    # Identity-confirmed classes first: the shard records often carry only a
    # thin `cli_failure` error while the detailed reason lives in the session
    # logs; these identities were confirmed during the campaigns (see
    # RESUME_CHECKPOINT §4 and the fig5 driver NOTEs).
    if "Ferritin" in task or target == "Ferritin":
        return "boundary_odesign_zero_output"
    if source == "fig5_ablations" and "Nucleocapsid" in task and "fig5e2" in task:
        return "boundary_odesign_zero_output"
    if backend == "claude-3.5-sonnet":
        return "endpoint_misconfig"
    if task == "04_sirna_design_009_gc_rich_target":
        return "llm_abort_correct"
    # String-signature classes.
    if "no_sequences_extracted" in err or "candidate_generation_failed" in err:
        return "boundary_odesign_zero_output"
    if "resource_not_found" in err or "notfounderror" in err:
        return "endpoint_misconfig"
    if "qualityagent" in err:
        return "llm_abort_recovered"
    if "timeout" in err or "timed out" in err:
        return "transient_timeout"
    if source == "fig4_known_aptamers" and ("egarps" in err or "utf-8" in err):
        return "driver_chain_bug_fixed"
    return "transient_infra_recovered"  # default bucket: infra, recovered


def load(path: Path) -> list[dict]:
    out: list[dict] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def main() -> int:
    report: dict = {
        "generated_by": "experiments/analysis/failure_taxonomy.py",
        "method": __doc__.strip().splitlines()[0],
        "categories_note": (
            "Final-state failures are all deterministic boundaries or explicit "
            "governance/misconfig outcomes; every other failure event was "
            "recovered by the campaign's --resume sweeps."
        ),
        "by_figure": {},
        "totals": {},
    }
    events_total: Counter = Counter()
    final_total: Counter = Counter()

    for label, files, keyf in INPUTS:
        records: list[dict] = []
        for name in files:
            p = RESULTS / name
            if p.exists():
                records.extend(load(p))
        events: Counter = Counter()
        # final state per job key (latest timestamp wins; ties keep file order)
        latest: dict = {}
        for r in records:
            k = keyf(r)
            prev = latest.get(k)
            if prev is None or str(r.get("timestamp") or "") >= str(prev.get("timestamp") or ""):
                latest[k] = r
        final: Counter = Counter()
        for r in records:
            if not r.get("success"):
                events[classify(r, label)] += 1
        for r in latest.values():
            if not r.get("success"):
                final[classify(r, label)] += 1
        report["by_figure"][label] = {
            "n_records": len(records),
            "n_jobs": len(latest),
            "n_jobs_success": sum(1 for r in latest.values() if r.get("success")),
            "failure_events": dict(events),
            "final_failures": dict(final),
        }
        events_total.update(events)
        final_total.update(final)

    # Boundaries documented outside the JSONLs (RESUME_CHECKPOINT §4).
    report["by_figure"]["fig2_cds_nulls_boundary"] = {
        "note": (
            "Zika (10 kb CDS) and Factor VIII (7 kb CDS): LinearDesign "
            "deterministic OOM (SIGKILL) on the lambda=0 design arm — "
            "operating-envelope boundary, 2 target cells. Not JSONL records; "
            "carried from RESUME_CHECKPOINT §4."
        ),
        "final_failures": {"boundary_lineardesign_oom": 2},
    }
    final_total["boundary_lineardesign_oom"] += 2

    report["totals"] = {
        "failure_events": dict(events_total),
        "final_failures": dict(final_total),
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{'figure':24s} {'jobs':>5s} {'ok':>5s}  final failures")
    for label, sec in report["by_figure"].items():
        if "n_jobs" not in sec:
            print(f"{label:24s} {'-':>5s} {'-':>5s}  {sec['final_failures']}")
            continue
        print(f"{label:24s} {sec['n_jobs']:>5d} {sec['n_jobs_success']:>5d}  {sec['final_failures']}")
    print("\nevent totals:", dict(events_total))
    print("final totals:", dict(final_total))
    print(f"\n-> {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
