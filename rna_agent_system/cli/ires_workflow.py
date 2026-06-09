#!/usr/bin/env python3
"""CLI entry for IRES prediction via natural-language prompt (Layer 5).

Run from ``rna_agent_system`` directory::

    python cli/ires_workflow.py --sequence AUGCAUGCAU --json
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
    p = argparse.ArgumentParser(description="Run IRES prediction via natural-language prompt.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--sequence", type=str, help="Single RNA/DNA sequence to screen.")
    src.add_argument(
        "--sequence-filepath", type=str, dest="sequence_filepath",
        help="Path to FASTA or plain-sequence file.",
    )
    src.add_argument("--user-text", type=str, dest="user_text", help="Direct natural-language request.")

    p.add_argument(
        "--mode", type=int, default=0, choices=(0, 1, 2), dest="iresfinder_mode",
        help="IRESfinder mode: 0=full sequence, 1=header subsequence, 2=sliding window.",
    )
    p.add_argument(
        "--threshold", type=float, default=0.5, dest="probability_threshold",
        help="Probability threshold for IRES labeling (default 0.5).",
    )
    p.add_argument("--window-size", type=int, default=174, dest="window_size")
    p.add_argument("--step-size", type=int, default=50, dest="step_size")
    p.add_argument("--top-n", type=int, default=5, dest="top_n_candidates")
    p.add_argument("--no-structural-validation", action="store_true", dest="no_structural_validation")
    p.add_argument("--task-id", type=str, default=None, dest="task_id")
    p.add_argument("--constraints", type=str, default=None)
    p.add_argument("--top-k", type=int, default=None, dest="top_k")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--json", action="store_true", help="Print full JSON response to stdout.")
    args = p.parse_args(argv)

    if args.user_text:
        user_text = args.user_text
    elif args.sequence:
        user_text = f"Predict IRES elements in sequence {args.sequence}"
    else:
        user_text = f"Predict IRES elements in file {args.sequence_filepath}"

    opts = []
    if args.iresfinder_mode != 0:
        opts.append(f"mode={args.iresfinder_mode}")
    if args.probability_threshold != 0.5:
        opts.append(f"threshold={args.probability_threshold}")
    if args.window_size != 174:
        opts.append(f"window_size={args.window_size}")
    if args.step_size != 50:
        opts.append(f"step_size={args.step_size}")
    if args.top_n_candidates != 5:
        opts.append(f"top_n={args.top_n_candidates}")
    if args.no_structural_validation:
        opts.append("no_structural_validation")
    if opts:
        user_text += " with options: " + ", ".join(opts)

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
        "task_type": "ires",
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
        print(f"task_id={payload['task_id']} success={payload['success']}")
        if payload["summary"]:
            print(payload["summary"])
        if payload["errors"]:
            print("ERRORS:", " | ".join(payload["errors"]))
        if payload["warnings"]:
            print("WARNINGS:", " | ".join(payload["warnings"]))

    return 0 if payload["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
