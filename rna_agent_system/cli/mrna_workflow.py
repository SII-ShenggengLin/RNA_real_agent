#!/usr/bin/env python3
"""CLI entry for the mRNA ranking workflow (same logic as POST ``/v1/workflows/mrna/run``).

Run from ``rna_agent_system`` directory::

    python cli/mrna_workflow.py --sequence AUGCAUGCAU --json

Server example (Linux)::

    cd /path/to/RNA_real_agent/rna_agent_system
    uvicorn workflow_api.app:app --host 0.0.0.0 --port 8090
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from workflow_api.mrna_handler import execute_mrna_workflow_http
from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest


def _parse_constraints(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--constraints must be a JSON object")
    return data


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Run mRNA workflow (GC + fold + ranking).")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--sequence", type=str, help="Single RNA/DNA sequence.")
    src.add_argument("--sequences", type=str, help="Comma-separated sequences.")
    src.add_argument("--protein", type=str, help="Amino-acid sequence (requires LinearDesign service).")

    p.add_argument("--task-type", type=str, default="mrna", dest="task_type")
    p.add_argument("--task-id", type=str, default=None, dest="task_id")
    p.add_argument("--constraints", type=str, default=None, help='JSON object, e.g. {"fold_service_url":"http://127.0.0.1:8015/fold"}')
    p.add_argument("--top-k", type=int, default=None, dest="top_k")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--json", action="store_true", help="Print full JSON response to stdout.")
    args = p.parse_args(argv)

    body: Dict[str, Any] = {
        "task_type": args.task_type,
        "task_id": args.task_id,
        "constraints": _parse_constraints(args.constraints),
        "top_k": args.top_k,
        "debug": args.debug,
    }
    if args.sequence:
        body["sequence"] = args.sequence
    elif args.sequences:
        body["sequences"] = [s.strip() for s in args.sequences.split(",") if s.strip()]
    else:
        body["protein"] = args.protein

    try:
        req = MrnaWorkflowHttpRequest.model_validate(body)
    except Exception as exc:
        print(f"Invalid arguments: {exc}", file=sys.stderr)
        return 2

    out = execute_mrna_workflow_http(req)
    payload = out.model_dump(mode="json")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"task_id: {out.task_id}")
        print(f"success: {out.success}")
        print(f"summary: {out.summary}")
        if out.operational_summary:
            print(f"operational_summary: {out.operational_summary}")
        if out.result_json_path:
            print(f"result_json_path: {out.result_json_path}")
        if out.artifact_directory:
            print(f"artifact_directory: {out.artifact_directory}")
        if out.best_candidate:
            bc = out.best_candidate
            print(f"best_sequence: {bc.get('sequence', '')[:120]}{'...' if len(str(bc.get('sequence',''))) > 120 else ''}")
            print(f"best_total_score: {bc.get('scores', {}).get('total_score')}")
        if out.warnings:
            print(f"warnings ({len(out.warnings)}):", "; ".join(out.warnings[:5]))
        if out.errors:
            print(f"errors ({len(out.errors)}):", "; ".join(out.errors))

    return 0 if out.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
