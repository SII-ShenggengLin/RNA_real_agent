#!/usr/bin/env python3
"""CLI entry for the RNA Agent (natural-language prompt, Layer 5).

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

from agent_core.planning.factory import build_planner  # noqa: E402
from agent_core.runner import AgentRunner  # noqa: E402
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry  # noqa: E402


def _parse_constraints(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--constraints must be a JSON object")
    return data


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Run RNA Agent via natural-language prompt.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--sequence", type=str, help="Single RNA/DNA sequence.")
    src.add_argument("--sequences", type=str, help="Comma-separated sequences.")
    src.add_argument("--protein", type=str, help="Amino-acid sequence (requires LinearDesign service).")
    src.add_argument("--user-text", type=str, dest="user_text", help="Direct natural-language request.")

    p.add_argument("--task-id", type=str, default=None, dest="task_id")
    p.add_argument(
        "--constraints", type=str, default=None,
        help='JSON object, e.g. {"design_tool": "lineardesign"}',
    )
    p.add_argument("--top-k", type=int, default=None, dest="top_k")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--json", action="store_true", help="Print full JSON response to stdout.")
    args = p.parse_args(argv)

    constraints = _parse_constraints(args.constraints) or {}

    # Build natural-language prompt
    if args.user_text:
        user_text = args.user_text
    elif args.protein:
        user_text = f"Design mRNA for protein {args.protein}"
        design_tool_hint = constraints.get("design_tool", "")
        if design_tool_hint:
            user_text += f" using {design_tool_hint}"
    elif args.sequence:
        user_text = f"Evaluate sequence {args.sequence}"
    else:
        user_text = f"Evaluate sequences {args.sequences}"

    runner = AgentRunner(
        planner=build_planner(),
        executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
    )

    try:
        state = runner.run(user_text, session_id=args.task_id or "")
    except Exception as exc:
        print(f"Execution failed: {exc}", file=sys.stderr)
        return 1

    wf_result = state.get("workflow_result")
    if wf_result is None:
        print("No workflow result produced.", file=sys.stderr)
        return 1

    payload = {
        "task_id": args.task_id or "",
        "success": wf_result.success,
        "task_type": getattr(wf_result, "task_type", "rna"),
        "best_candidate": wf_result.best_candidate.model_dump(mode="json") if wf_result.best_candidate else None,
        "candidates": [c.model_dump(mode="json") for c in wf_result.all_candidates],
        "summary": getattr(wf_result, "public_summary", wf_result.summary) or "",
        "operational_summary": wf_result.summary or "",
        "errors": list(wf_result.errors),
        "warnings": list(getattr(wf_result, "warnings", [])),
    }

    if args.top_k is not None:
        payload["candidates"] = payload["candidates"][: args.top_k]

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"task_id: {payload['task_id']}")
        print(f"success: {payload['success']}")
        print(f"summary: {payload['summary']}")
        if payload["operational_summary"]:
            print(f"operational_summary: {payload['operational_summary']}")
        if payload["best_candidate"]:
            bc = payload["best_candidate"]
            seq = str(bc.get("sequence", ""))
            print(f"best_sequence: {seq[:120]}{'...' if len(seq) > 120 else ''}")
            print(f"best_total_score: {bc.get('scores', {}).get('total_score')}")
        if payload["warnings"]:
            print(f"warnings ({len(payload['warnings'])}):", "; ".join(payload["warnings"][:5]))
        if payload["errors"]:
            print(f"errors ({len(payload['errors'])}):", "; ".join(payload["errors"]))

    return 0 if payload["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
