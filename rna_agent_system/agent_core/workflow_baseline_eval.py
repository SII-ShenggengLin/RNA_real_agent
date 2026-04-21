"""Shared stub tools + batch evaluation helpers for mRNA workflow baseline (tests + examples).

Avoids importing HTTP-backed LangChain tools; deterministic scores for regression checks.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from agent_core.file_manager import PROJECT_ROOT
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflows.mrna_workflow import MrnaWorkflowInput, run_mrna_workflow

_LOGGER = logging.getLogger(__name__)

DEFAULT_SAMPLES_PATH = PROJECT_ROOT / "examples" / "data" / "mrna_baseline_samples.json"


class StubGcTool:
    name = "compute_rna_sequence_gc_content"

    def invoke(self, kwargs):
        fp = kwargs.get("filepath", "")
        path = Path(PROJECT_ROOT / fp) if not Path(fp).is_absolute() else Path(fp)
        text = path.read_text(encoding="utf-8")
        seq = "".join(
            ln.strip().upper().replace("T", "U")
            for ln in text.splitlines()
            if ln.strip() and not ln.startswith(">")
        )
        gc = (seq.count("G") + seq.count("C")) / max(len(seq), 1)
        return {"gc_content": float(gc), "sequence_length": len(seq), "model": "stub_gc"}


class StubFoldTool:
    name = "predict_rna_secondary_structure_with_linearfold"

    def invoke(self, kwargs):
        fp = kwargs.get("filepath", "")
        path = Path(PROJECT_ROOT / fp) if not Path(fp).is_absolute() else Path(fp)
        seq = "".join(ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
        ln = len(seq.replace(" ", ""))
        mfe = -10.0 - min(35.0, ln * 0.08)
        return {"mfe": float(mfe), "structure": "." * max(ln, 1), "model": "stub_fold"}


def build_stub_mrna_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(StubGcTool())
    reg.register(StubFoldTool())
    return reg


def make_stub_mrna_executor() -> ToolExecutor:
    return ToolExecutor(build_stub_mrna_registry(), logger=_LOGGER)


def load_baseline_samples(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    p = path or DEFAULT_SAMPLES_PATH
    data = json.loads(Path(p).read_text(encoding="utf-8"))
    return list(data.get("samples", []))


def iter_sample_inputs(
    samples: List[Dict[str, Any]],
    *,
    target_length_nt: Optional[int] = None,
    persist_run: bool = False,
) -> Iterator[Tuple[str, MrnaWorkflowInput]]:
    for row in samples:
        sid = str(row.get("id", "sample"))
        inp = MrnaWorkflowInput(
            sequence=str(row["sequence"]).strip(),
            candidate_mode="direct",
            target_length_nt=target_length_nt,
            persist_run=persist_run,
        )
        yield sid, inp


def evaluate_sample(
    sample_id: str,
    inp: MrnaWorkflowInput,
    *,
    executor: Optional[ToolExecutor] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one workflow; return a JSON-serializable summary row."""

    ex = executor or make_stub_mrna_executor()
    tid = task_id or f"baseline_{sample_id}"
    wf = run_mrna_workflow(inp, executor=ex, task_id=tid)
    best = wf.best_candidate
    score = float(best.scores["total_score"]) if best and "total_score" in best.scores else None
    return {
        "sample_id": sample_id,
        "task_id": wf.task_id,
        "success": wf.success,
        "public_summary": wf.public_summary,
        "best_total_score": score,
        "n_candidates": len(wf.all_candidates),
        "n_tool_warnings": len(wf.errors),
        "ordered_scores": [
            {"candidate_id": c.id, "total_score": c.scores.get("total_score"), "rank": c.rank}
            for c in wf.all_candidates
        ],
    }


def run_baseline_batch(
    *,
    samples_path: Optional[Path] = None,
    target_length_nt: Optional[int] = None,
    persist_run: bool = False,
    executor: Optional[ToolExecutor] = None,
) -> List[Dict[str, Any]]:
    samples = load_baseline_samples(samples_path)
    rows: List[Dict[str, Any]] = []
    ex = executor or make_stub_mrna_executor()
    for sid, inp in iter_sample_inputs(
        samples,
        target_length_nt=target_length_nt,
        persist_run=persist_run,
    ):
        rows.append(evaluate_sample(sid, inp, executor=ex))
    return rows


def print_batch_report(rows: List[Dict[str, Any]]) -> None:
    print("sample_id\ttask_id\tsuccess\tbest_total_score\tn_candidates\twarnings")
    for r in rows:
        print(
            f"{r['sample_id']}\t{r['task_id']}\t{r['success']}\t{r['best_total_score']}\t"
            f"{r['n_candidates']}\t{r['n_tool_warnings']}"
        )
