"""One-line public summary for workflow results."""

from __future__ import annotations

from agent_core.workflow_models import WorkflowResult


def build_public_summary(wf: WorkflowResult) -> str:
    """One-line summary for APIs and paper-style logs."""

    ts = wf.task_id
    if not wf.success:
        err = wf.errors[0] if wf.errors else "failed"
        return f"task_id={ts} success=false error={err[:120]}"
    bc = wf.best_candidate
    score = None
    if bc and "total_score" in bc.scores:
        score = float(bc.scores["total_score"])
    n = len(wf.all_candidates)
    nw = len(wf.errors)
    score_s = f"{score:.4f}" if score is not None else "na"
    return (
        f"task_id={ts} success=true best_total_score={score_s} candidates={n} tool_warnings={nw}"
    )
