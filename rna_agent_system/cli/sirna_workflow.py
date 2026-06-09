#!/usr/bin/env python3
"""CLI entry for siRNA design via natural-language prompt (Layer 5).

Run from ``rna_agent_system`` directory::

    python cli/sirna_workflow.py --target-sequence AUGC... --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from agent_core.planning.factory import build_planner  # noqa: E402
from agent_core.runner import AgentRunner  # noqa: E402
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry  # noqa: E402


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Run siRNA design via natural-language prompt.")
    p.add_argument("--mode", type=str, default="generic", choices=["antiviral", "generic"])
    p.add_argument("--target-sequence", type=str, default=None, dest="target_sequence")
    p.add_argument("--target-fasta", type=str, default=None, dest="target_fasta_path")
    p.add_argument("--species", type=str, default="homo_sapiens")
    p.add_argument("--candidate-count", type=int, default=10, dest="candidate_count")
    p.add_argument("--user-text", type=str, dest="user_text", help="Direct natural-language request.")
    p.add_argument("--output-json", action="store_true", dest="output_json", help="Print full JSON response to stdout.")
    p.add_argument("--task-id", type=str, default=None, dest="task_id")
    p.add_argument("--top-k", type=int, default=None, dest="top_k")
    p.add_argument("--debug", action="store_true")
    args = p.parse_args(argv)

    if args.user_text:
        user_text = args.user_text
    elif args.target_sequence:
        user_text = (
            f"Design siRNA in {args.mode} mode against target sequence "
            f"{args.target_sequence} for species {args.species}"
        )
    elif args.target_fasta_path:
        user_text = (
            f"Design siRNA in {args.mode} mode against target FASTA "
            f"{args.target_fasta_path} for species {args.species}"
        )
    else:
        print("Error: Provide --target-sequence, --target-fasta, or --user-text", file=sys.stderr)
        return 2

    if args.candidate_count != 10:
        user_text += f" with {args.candidate_count} candidates"

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
        "task_type": "sirna",
        "best_candidate": wf_result.best_candidate.model_dump(mode="json") if wf_result.best_candidate else None,
        "candidates": [c.model_dump(mode="json") for c in wf_result.all_candidates],
        "summary": getattr(wf_result, "public_summary", wf_result.summary) or "",
        "operational_summary": wf_result.summary or "",
        "errors": list(wf_result.errors),
        "warnings": list(getattr(wf_result, "warnings", [])),
    }

    if args.top_k is not None:
        payload["candidates"] = payload["candidates"][: args.top_k]

    if args.output_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"task_id: {payload['task_id']}")
        print(f"success: {payload['success']}")
        print(f"summary: {payload['summary']}")
        if payload["operational_summary"]:
            print(f"operational_summary: {payload['operational_summary']}")
        if payload["best_candidate"]:
            bc = payload["best_candidate"]
            print(f"best_sequence: {bc.get('sequence', '')}")
            print(f"best_total_score: {bc.get('scores', {}).get('total_score')}")
        print(f"candidates: {len(payload['candidates'])}")
        for i, c in enumerate(payload["candidates"][:10], start=1):
            print(f"  #{i} {c.get('sequence', '')} | score={c.get('scores', {}).get('total_score', 0.0):.3f} | source={c.get('source', '')}")
        if payload["warnings"]:
            print(f"warnings ({len(payload['warnings'])}):", "; ".join(payload["warnings"][:5]))
        if payload["errors"]:
            print(f"errors ({len(payload['errors'])}):", "; ".join(payload["errors"]))

    return 0 if payload["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
