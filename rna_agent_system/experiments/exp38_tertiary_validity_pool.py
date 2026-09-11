#!/usr/bin/env python3
"""EXP 38 — tertiary-structure workflow validity pool (Supplementary Note 2,
section "RNA tertiary structure design"; zero new computation).

Pools the per-candidate quality fields already produced by the 20 benchmark
tasks of ``rna_tertiary_structure_design`` (RNA-BioBench-Platform
``tasks/07_rna_tertiary_structure/``) and scores them against each task's
registered evaluation rubric. The paper's Fig. 2 carries the five workflows
with biological-validity evidence; this experiment is the supplementary
output-quality register for the tertiary-structure workflow.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2)
-----------------------------------------------------
* Question: what fraction of designed sequences pass the task-registered
  rubric — mean pLDDT of the RhoFold re-fold >= ``mean_plddt_threshold``
  (65 or 70 per task) and, where the task registers one, refold-vs-reference
  RMSD <= ``rmsd_threshold`` (2.0 or 3.0) — and how do the pooled metrics
  distribute across the 8 real PDB reference structures (1EHZ, 1F7U, 1GID,
  1HR2, 1MME, 1Y26, 2GDI, 3D2V)?
* Data source (primary): the 2026-09-07 (bb)-era Exp-24 production campaign
  sessions listed in
  ``experiments/results/exp24_production_campaign/lane_07_rna_tertiary_structure.jsonl``
  (one session per task, 20/20 successful, per-candidate
  ``rhofold_mean_plddt`` / ``alignment_rmsd`` / ``alignment_tm_score`` /
  ``recovery_rate`` present in every candidate's ``scores``). Fallback, if a
  session artifact lacks these fields: the Exp-1 era sessions
  (``workspace/sessions/exp1_07_*``, 2026-08-25) with the summary JSON
  carrying ``session_era = "exp1 2026-08-25"``. No new design, folding or
  alignment is run by this driver.
* Primary metric: per-candidate rubric pass (conjunct over the thresholds
  the task registers; tasks without an ``rmsd_threshold`` gate on pLDDT
  alone). Reported per task, per reference PDB, and pooled. No pass-rate
  threshold is pre-registered — the outcome is reported as measured,
  including mixed/negative outcomes.
* Secondary metrics: recovery_rate (RhoDesign/RiboDiffusion sequence
  recovery vs the reference chain) and alignment_tm_score, descriptive
  only; the RMSD axis is interpreted as an inverse-folding fidelity bound —
  designed sequences deliberately differ from the reference sequence, so a
  high refold RMSD is an expected regime, not a tool malfunction.
* Gate: all 20 lane-listed sessions must yield a parseable
  ``workflow_results_*.json`` with ``success`` true and at least one
  candidate with complete quality fields; a missing/failed session is
  reported, never silently dropped.
* ``--verify`` recomputes both frozen files byte-identically from the
  session artifacts.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp38_tertiary_validity_pool.py
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp38_tertiary_validity_pool.py --verify

Outputs under ``experiments/results/exp38_tertiary_validity_pool/``:
    records.jsonl, summary.json
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = (PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Platform"
             / "tasks" / "07_rna_tertiary_structure")
LANE_PATH = (PROJECT_ROOT / "experiments" / "results" / "exp24_production_campaign"
             / "lane_07_rna_tertiary_structure.jsonl")
OUT_DIR = PROJECT_ROOT / "experiments" / "results" / "exp38_tertiary_validity_pool"
RECORDS_PATH = OUT_DIR / "records.jsonl"
SUMMARY_PATH = OUT_DIR / "summary.json"

SESSION_ERA_PRIMARY = "exp24 (bb) 2026-09-07"
SESSION_ERA_FALLBACK = "exp1 2026-08-25"

QUALITY_FIELDS = ("rhofold_mean_plddt", "alignment_rmsd",
                  "alignment_tm_score", "recovery_rate")


def load_tasks() -> dict[str, dict[str, Any]]:
    tasks = {}
    for p in sorted(TASKS_DIR.glob("07_rna_tertiary_structure_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        tasks[d["task_id"]] = d
    return tasks


def find_results_file(session_dir: Path) -> Path | None:
    candidates = sorted(
        session_dir.glob("workflow_results_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def candidate_field(cand: dict[str, Any], key: str) -> Any:
    """Quality fields live in ``scores`` (``metrics`` mirrors them)."""
    scores = cand.get("scores") or {}
    if scores.get(key) is not None:
        return scores[key]
    return (cand.get("metrics") or {}).get(key)


def collect_records() -> list[dict[str, Any]]:
    """One record per candidate, lane order then candidate rank."""
    tasks = load_tasks()
    lane = [json.loads(ln) for ln in LANE_PATH.read_text(encoding="utf-8").splitlines()
            if ln.strip()]
    records: list[dict[str, Any]] = []
    for entry in lane:
        task_id = entry["task_id"]
        task = tasks[task_id]
        rubric = task.get("evaluation_rubric") or {}
        plddt_thr = rubric.get("mean_plddt_threshold")
        rmsd_thr = rubric.get("rmsd_threshold")

        session_id = entry["session_id"]
        era = SESSION_ERA_PRIMARY
        results_file = find_results_file(
            PROJECT_ROOT / "workspace" / "sessions" / session_id)
        if results_file is None:
            # era fallback: Exp-1 sessions carry the same task naming
            fallback_id = session_id
            for prefix in ("exp24_r4_", "exp24_r3_", "exp24_"):
                if fallback_id.startswith(prefix):
                    fallback_id = "exp1_" + fallback_id[len(prefix):]
                    break
            results_file = find_results_file(
                PROJECT_ROOT / "workspace" / "sessions" / fallback_id)
            session_id = fallback_id
            era = SESSION_ERA_FALLBACK
        if results_file is None:
            records.append({
                "task_id": task_id, "session_id": session_id,
                "session_era": era, "error": "no_results_file",
            })
            continue
        w = json.loads(results_file.read_text(encoding="utf-8"))
        cands = w.get("candidates") or []
        if not w.get("success") or not cands:
            records.append({
                "task_id": task_id, "session_id": session_id,
                "session_era": era,
                "error": "workflow_success_false" if not w.get("success")
                         else "no_candidates",
            })
            continue
        for cand in cands:
            vals = {k: candidate_field(cand, k) for k in QUALITY_FIELDS}
            if any(vals[k] is None for k in QUALITY_FIELDS):
                records.append({
                    "task_id": task_id, "session_id": session_id,
                    "session_era": era,
                    "candidate_id": cand.get("id"),
                    "error": "missing_quality_fields",
                })
                continue
            pass_plddt = (plddt_thr is not None
                          and vals["rhofold_mean_plddt"] >= plddt_thr)
            pass_rmsd = (rmsd_thr is not None
                         and vals["alignment_rmsd"] <= rmsd_thr)
            records.append({
                "task_id": task_id,
                "category": task.get("category"),
                "paper_reference": task.get("paper_reference"),
                "session_id": session_id,
                "session_era": era,
                "candidate_id": cand.get("id"),
                "candidate_rank": cand.get("rank"),
                "design_tool": (cand.get("metadata") or {}).get("design_tool")
                               or cand.get("source"),
                "sequence_length": candidate_field(cand, "sequence_length"),
                "rhofold_mean_plddt": vals["rhofold_mean_plddt"],
                "alignment_rmsd": vals["alignment_rmsd"],
                "alignment_tm_score": vals["alignment_tm_score"],
                "recovery_rate": vals["recovery_rate"],
                "total_score": (cand.get("scores") or {}).get("total_score"),
                "mean_plddt_threshold": plddt_thr,
                "rmsd_threshold": rmsd_thr,
                "pass_plddt": pass_plddt,
                "pass_rmsd": pass_rmsd if rmsd_thr is not None else None,
                "pass_rubric": pass_plddt and (pass_rmsd if rmsd_thr is not None else True),
                "error": None,
            })
    return records


def _metric_stats(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def _pool(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate a record subset (task-level, reference-level or pooled)."""
    ok = [r for r in recs if r.get("error") is None]
    out: dict[str, Any] = {
        "n_candidates": len(ok),
        "n_pass_rubric": sum(1 for r in ok if r["pass_rubric"]),
        "pass_rate": (sum(1 for r in ok if r["pass_rubric"]) / len(ok)) if ok else None,
        "n_pass_plddt": sum(1 for r in ok if r["pass_plddt"]),
        "n_pass_rmsd": sum(1 for r in ok if r["pass_rmsd"]),
        "n_rmsd_gated": sum(1 for r in ok if r["rmsd_threshold"] is not None),
    }
    for key, field in (("plddt", "rhofold_mean_plddt"),
                       ("rmsd", "alignment_rmsd"),
                       ("tm_score", "alignment_tm_score"),
                       ("recovery_rate", "recovery_rate")):
        vals = [r[field] for r in ok]
        out[key] = _metric_stats(vals) if vals else None
    return out


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    tasks = load_tasks()
    errors = [r for r in records if r.get("error") is not None]
    ok = [r for r in records if r.get("error") is None]

    per_task: dict[str, Any] = {}
    for task_id, task in tasks.items():
        recs = [r for r in ok if r["task_id"] == task_id]
        entry = _pool(recs)
        entry["mean_plddt_threshold"] = (task.get("evaluation_rubric") or {}).get(
            "mean_plddt_threshold")
        entry["rmsd_threshold"] = (task.get("evaluation_rubric") or {}).get(
            "rmsd_threshold")
        entry["paper_reference"] = task.get("paper_reference")
        entry["session_era"] = (recs[0]["session_era"] if recs else None)
        per_task[task_id] = entry

    per_reference: dict[str, Any] = {}
    for ref in sorted({r["paper_reference"] for r in ok}):
        recs = [r for r in ok if r["paper_reference"] == ref]
        entry = _pool(recs)
        entry["n_tasks"] = len({r["task_id"] for r in recs})
        per_reference[ref] = entry

    tasks_with_any_pass = sum(1 for t in per_task.values()
                              if (t["n_pass_rubric"] or 0) > 0)
    return {
        "experiment": "exp38_tertiary_validity_pool",
        "workflow": "rna_tertiary_structure_design",
        "session_era": SESSION_ERA_PRIMARY if not any(
            r.get("session_era") == SESSION_ERA_FALLBACK for r in records
        ) else SESSION_ERA_FALLBACK,
        "data_source": ("experiments/results/exp24_production_campaign/"
                        "lane_07_rna_tertiary_structure.jsonl + session "
                        "workflow_results JSONs"),
        "rubric_rule": ("pass = rhofold_mean_plddt >= task mean_plddt_threshold "
                        "AND (no task rmsd_threshold OR alignment_rmsd <= threshold)"),
        "n_tasks": len(per_task),
        "n_tasks_with_records": len({r["task_id"] for r in ok}),
        "n_tasks_with_any_pass": tasks_with_any_pass,
        "n_errors": len(errors),
        "errors": [{"task_id": r["task_id"], "session_id": r.get("session_id"),
                    "error": r["error"]} for r in errors],
        "pooled": _pool(ok),
        "per_reference": per_reference,
        "per_task": per_task,
        "notes": (
            "Zero new computation: every value re-read from the frozen campaign "
            "session artifacts. alignment_rmsd is the RhoFold refold of the "
            "designed sequence vs the task's input reference chain; designed "
            "sequences deliberately differ from the reference sequence "
            "(recovery_rate < 1), so the RMSD axis is an inverse-folding "
            "fidelity bound — reported as measured, mixed/negative outcomes "
            "included."
        ),
    }


def _records_text(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                   for r in records)


def _summary_text(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main() -> int:
    records = collect_records()
    summary = build_summary(records)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RECORDS_PATH.write_text(_records_text(records), encoding="utf-8")
    SUMMARY_PATH.write_text(_summary_text(summary), encoding="utf-8")
    pooled = summary["pooled"]
    print(f"wrote {RECORDS_PATH} ({len(records)} records) and {SUMMARY_PATH}")
    print(f"  era={summary['session_era']}; tasks {summary['n_tasks_with_records']}/"
          f"{summary['n_tasks']}, candidates {pooled['n_candidates']}, "
          f"errors {summary['n_errors']}")
    print(f"  pooled rubric pass {pooled['n_pass_rubric']}/{pooled['n_candidates']} "
          f"= {pooled['pass_rate']:.4f}; plddt-pass {pooled['n_pass_plddt']}, "
          f"rmsd-pass {pooled['n_pass_rmsd']} (of {pooled['n_rmsd_gated']} gated)")
    print(f"  tasks with >=1 rubric-passing candidate: "
          f"{summary['n_tasks_with_any_pass']}/{summary['n_tasks']}")
    print(f"  plddt median {pooled['plddt']['median']:.2f}; rmsd median "
          f"{pooled['rmsd']['median']:.2f}; recovery median "
          f"{pooled['recovery_rate']['median']:.4f}")
    return 0 if summary["n_errors"] == 0 else 1


def verify() -> int:
    records = collect_records()
    summary = build_summary(records)
    ok = True
    for path, fresh in ((RECORDS_PATH, _records_text(records)),
                        (SUMMARY_PATH, _summary_text(summary))):
        stored = path.read_text(encoding="utf-8")
        if stored == fresh:
            print(f"VERIFY OK — {path} byte-identical on recomputation")
        else:
            print(f"VERIFY FAIL — {path} differs from recomputation")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true",
                    help="recompute and byte-compare the frozen outputs")
    args = ap.parse_args()
    raise SystemExit(verify() if args.verify else main())
