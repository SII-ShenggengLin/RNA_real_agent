from __future__ import annotations

import json
from uuid import uuid4

import pytest

from agent_core.file_manager import PROJECT_ROOT
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_baseline_eval import StubCaiTool, StubFoldTool, StubGcTool
from agent_core.workflow_run_storage import maybe_persist_workflow_run
from agent_core.workflows.mrna_sequence_scoring import MrnaSequenceScoringInput, run_mrna_sequence_scoring


@pytest.fixture()
def stub_ex():
    reg = ToolRegistry()
    reg.register(StubGcTool())
    reg.register(StubFoldTool())
    return ToolExecutor(reg)


def _run_parent():
    d = PROJECT_ROOT / "workspace" / f"_obs_test_{uuid4().hex[:10]}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_workflow_persist_request_and_result_json(stub_ex):
    parent = _run_parent()
    inp = MrnaSequenceScoringInput(sequence="AUGCAUGCAUGCAU")
    out = run_mrna_sequence_scoring(inp, executor=stub_ex, task_id="paper-exp-001")
    assert out.public_summary
    assert out.public_summary.startswith("task_id=")

    maybe_persist_workflow_run(
        out,
        inp.model_dump(mode="json"),
        enabled=True,
        artifact_runs_parent=str(parent),
    )

    assert out.run_result_json_path
    res_abs = PROJECT_ROOT / out.run_result_json_path
    req_abs = res_abs.parent / "request.json"
    assert res_abs.is_file()
    assert req_abs.is_file()

    payload = json.loads(res_abs.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "workflow_run_v1"
    assert payload["task_id"] == out.task_id
    assert payload["success"] is True
    assert "tool_records" in payload and len(payload["tool_records"]) >= 2
    steps = [r["step_name"] for r in payload["tool_records"]]
    assert "gc_content" in steps and "secondary_structure" in steps
    assert payload["best_candidate"]["sequence"]

    req_payload = json.loads(req_abs.read_text(encoding="utf-8"))
    assert req_payload["workflow_input"]["sequence"] == "AUGCAUGCAUGCAU"


def test_workflow_failed_run_still_persisted(stub_ex):
    parent = _run_parent()
    inp = MrnaSequenceScoringInput(sequence="")
    out = run_mrna_sequence_scoring(inp, executor=stub_ex)
    assert out.success is False

    maybe_persist_workflow_run(
        out,
        inp.model_dump(mode="json"),
        enabled=True,
        artifact_runs_parent=str(parent),
    )

    assert out.run_result_json_path
    res_abs = PROJECT_ROOT / out.run_result_json_path
    body = json.loads(res_abs.read_text(encoding="utf-8"))
    assert body["success"] is False
    assert body["fatal_errors"]
    assert any("empty" in str(x).lower() for x in body["fatal_errors"])


def test_trace_contains_tool_steps():
    reg = ToolRegistry()
    reg.register(StubGcTool())
    reg.register(StubFoldTool())
    reg.register(StubCaiTool())
    ex = ToolExecutor(reg)
    inp = MrnaSequenceScoringInput(sequence="AUGCAU")
    out = run_mrna_sequence_scoring(inp, executor=ex)
    assert len(out.trace) == 3
    names = {r.tool_name for r in out.trace}
    assert "compute_rna_sequence_gc_content" in names
    assert "predict_rna_secondary_structure_with_linearfold" in names
    assert "compute_cai_for_cds_sequence" in names
