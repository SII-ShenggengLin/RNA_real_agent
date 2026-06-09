#!/usr/bin/env python3
"""Generate summary JSON for a workflow from its raw platform coverage results."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def generate_summary(raw_path: Path, workflow: str) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    if not records:
        return {"workflow": workflow, "total": 0, "note": "No records found."}

    total = len(records)
    success_records = [r for r in records if r.get("success")]
    failed_records = [r for r in records if not r.get("success")]
    success_count = len(success_records)
    fail_count = len(failed_records)

    # Per-category stats
    category_stats: Dict[str, Dict[str, int]] = {}
    for r in records:
        cat = r.get("category", "unknown")
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "success": 0}
        category_stats[cat]["total"] += 1
        if r.get("success"):
            category_stats[cat]["success"] += 1

    # Error type distribution
    error_counts: Counter = Counter()
    for r in failed_records:
        errors = r.get("errors", [])
        if errors:
            # Categorize by first error prefix
            first_err = str(errors[0])
            if "timeout" in first_err.lower():
                error_counts["timeout"] += 1
            elif "worker_exitcode" in first_err.lower():
                error_counts["worker_exitcode"] += 1
            elif "invalid_json" in first_err.lower():
                error_counts["invalid_json"] += 1
            elif "exception" in first_err.lower() or "traceback" in first_err.lower():
                error_counts["exception"] += 1
            else:
                error_counts["other"] += 1
        else:
            error_counts["unknown"] += 1

    # Timing stats
    elapsed_list = [r.get("elapsed_seconds", 0) for r in records]
    runner_elapsed_list = [r.get("runner_elapsed_seconds", 0) for r in records]

    def _safe_stats(values: List[float]) -> Dict[str, float]:
        if not values:
            return {"mean": 0.0, "median": 0.0, "max": 0.0, "min": 0.0}
        return {
            "mean": round(statistics.mean(values), 3),
            "median": round(statistics.median(values), 3),
            "max": round(max(values), 3),
            "min": round(min(values), 3),
        }

    # Tool correctness
    tool_correct_count = sum(1 for r in records if r.get("tool_correctness"))

    # Trace completeness distribution
    trace_comp_dist = Counter(r.get("trace_completeness", "unknown") for r in records)

    summary = {
        "workflow": workflow,
        "total": total,
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": round(success_count / total, 4) if total > 0 else 0.0,
        "by_category": {
            cat: {
                "total": stats["total"],
                "success": stats["success"],
                "rate": round(stats["success"] / stats["total"], 4) if stats["total"] > 0 else 0.0,
            }
            for cat, stats in category_stats.items()
        },
        "error_distribution": dict(error_counts),
        "elapsed_seconds": _safe_stats(elapsed_list),
        "runner_elapsed_seconds": _safe_stats(runner_elapsed_list),
        "tool_correctness_rate": round(tool_correct_count / total, 4) if total > 0 else 0.0,
        "trace_completeness_distribution": dict(trace_comp_dist),
    }

    return summary


def main():
    parser = argparse.ArgumentParser(description="Generate summary for a workflow coverage run")
    parser.add_argument("--workflow", required=True, help="Workflow name")
    parser.add_argument("--raw", help="Path to raw JSONL file (optional)")
    args = parser.parse_args()

    workflow = args.workflow
    if args.raw:
        raw_path = Path(args.raw)
    else:
        raw_path = (
            Path(__file__).resolve().parent.parent
            / "experiments"
            / "results"
            / "platform_coverage_by_workflow"
            / workflow
            / "raw"
            / f"platform_coverage_{workflow}.jsonl"
        )

    summary = generate_summary(raw_path, workflow)

    summary_dir = raw_path.parent.parent / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"summary_{workflow}.json"

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Summary written to: {summary_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
