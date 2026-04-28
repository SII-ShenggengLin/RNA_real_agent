#!/usr/bin/env python3
"""Batch-run the mRNA minimal workflow on baseline JSON samples (stub tools, no microservices).

Usage from ``rna_agent_system``::

    python examples/mrna_workflow_batch_demo.py
    python examples/mrna_workflow_batch_demo.py --samples examples/data/mrna_baseline_samples.json --json

Used as a lightweight regression / lab notebook anchor when adding tools or workflows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from agent_core.workflow_baseline_eval import (  # noqa: E402
    DEFAULT_SAMPLES_PATH,
    load_baseline_samples,
    run_baseline_batch,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Batch mRNA workflow baseline (stub GC+fold).")
    p.add_argument(
        "--samples",
        type=Path,
        default=DEFAULT_SAMPLES_PATH,
        help="Path to mrna_baseline_samples.json",
    )
    p.add_argument("--json", action="store_true", help="Print full row objects as JSON array.")
    args = p.parse_args()

    if not args.samples.is_file():
        print(f"Samples file not found: {args.samples}", file=sys.stderr)
        return 2

    rows = run_baseline_batch(
        samples_path=args.samples,
        persist_run=False,
    )
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=True))
    else:
        print("sample_id\ttask_id\tsuccess\tbest_total_score\tn_candidates\twarnings")
        for r in rows:
            print(
                f"{r['sample_id']}\t{r['task_id']}\t{r['success']}\t{r['best_total_score']}\t"
                f"{r['n_candidates']}\t{r['n_tool_warnings']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
