"""Tests for AgentRunner.run_form() / stream_form() / run_pipeline()."""

from __future__ import annotations

import pytest

from agent_core.pipeline.models import PipelinePlan
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry


@pytest.fixture
def runner() -> AgentRunner:
    return AgentRunner(
        executor=ToolExecutor(build_default_tool_registry()),
    )


def test_validate_required_params(runner: AgentRunner):
    with pytest.raises(ValueError, match="Missing required parameters"):
        runner._validate_required_params_for_workflow(
            "rna_small_molecule_interaction",
            {"rna_sequence": "AUGC"},  # missing smiles
        )


def test_sanitize_form_params(runner: AgentRunner):
    params = runner._sanitize_form_params(
        "rna_small_molecule_interaction",
        {"rna_sequence": "AUGC", "smiles": "CCO", "invented": "x"},
    )
    assert params == {"rna_sequence": "AUGC", "smiles": "CCO"}


def test_run_pipeline_single_workflow(runner: AgentRunner):
    from agent_core.agents.specialist_agent import SpecialistAgent
    from agent_core.agents.quality_agent import QualityProfile
    from agent_core.workflow_models import Candidate, WorkflowResult

    class _MockWorkflow:
        name = "mock_workflow"
        input_model = None

        def run(self, inp, *, progress_callback=None):
            candidate = Candidate(sequence=inp.get("seq", "AUG"), source="mock")
            return WorkflowResult(
                success=True,
                task_id="t1",
                best_candidate=candidate,
                all_candidates=[candidate],
                summary="mock success",
            )

    runner.specialist_registry["mock_workflow"] = SpecialistAgent(
        _MockWorkflow(), QualityProfile(workflow_name="mock_workflow", max_retries=0)
    )

    plan = PipelinePlan.single(
        "mock_workflow",
        {"seq": "AUGCGC"},
        plan_id="test_single",
    )
    result = runner.run_pipeline(plan)
    assert result.success is True
    assert "n1" in result.node_results


def test_run_form_smoke(runner: AgentRunner):
    from agent_core.agents.specialist_agent import SpecialistAgent
    from agent_core.agents.quality_agent import QualityProfile
    from agent_core.workflow_models import Candidate, WorkflowResult

    class _MockWorkflow:
        name = "mock_workflow"
        input_model = None

        def run(self, inp, *, progress_callback=None):
            candidate = Candidate(sequence=inp.get("seq", "AUG"), source="mock")
            return WorkflowResult(
                success=True,
                task_id="t1",
                best_candidate=candidate,
                all_candidates=[candidate],
                summary="mock success",
            )

    runner.specialist_registry["mock_workflow"] = SpecialistAgent(
        _MockWorkflow(), QualityProfile(workflow_name="mock_workflow", max_retries=0)
    )

    state = runner.run_form(
        form_params={"seq": "AUGCGC"},
        session_id="s1",
        explicit_workflow="mock_workflow",
    )
    assert "workflow_result" in state
    assert "pipeline_result" in state
    assert "final_report" in state


def test_run_pipeline_multi_workflow(runner: AgentRunner):
    from agent_core.agents.specialist_agent import SpecialistAgent
    from agent_core.agents.quality_agent import QualityProfile
    from agent_core.pipeline.models import PipelineEdge, PipelineNode, PipelinePlan
    from agent_core.workflow_models import Candidate, WorkflowResult

    class _MockWorkflow:
        name = "mock_workflow"
        input_model = None

        def run(self, inp, *, progress_callback=None):
            seq = inp.get("seq", "AUG")
            candidate = Candidate(sequence=seq, source="mock")
            return WorkflowResult(
                success=True,
                task_id="t1",
                best_candidate=candidate,
                all_candidates=[candidate],
                summary=f"seq={seq}",
            )

    runner.specialist_registry["mock_workflow"] = SpecialistAgent(
        _MockWorkflow(), QualityProfile(workflow_name="mock_workflow", max_retries=0)
    )

    plan = PipelinePlan(
        plan_id="multi",
        nodes=[
            PipelineNode(
                node_id="first",
                workflow="mock_workflow",
                static_params={"seq": "AUG"},
                output_alias="first",
            ),
            PipelineNode(
                node_id="second",
                workflow="mock_workflow",
                static_params={},
                input_bindings={"seq": "$first.best_candidate.sequence"},
                output_alias="second",
            ),
        ],
        edges=[PipelineEdge(source="first", target="second")],
    )
    result = runner.run_pipeline(plan)
    assert result.success is True
    assert result.node_results["second"].workflow_result.best_candidate.sequence == "AUG"
    assert "multi" in result.final_report


def test_run_form_preserves_previous_workflow_result():
    from agent_core.agents.specialist_agent import SpecialistAgent
    from agent_core.agents.quality_agent import QualityProfile
    from agent_core.session_memory import SessionMemory
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflow_models import Candidate, WorkflowResult
    from agent_core.runner import AgentRunner

    class _MockWorkflow:
        name = "mock_workflow"
        input_model = None

        def run(self, inp, *, progress_callback=None):
            seq = inp.get("seq", "AUG")
            candidate = Candidate(sequence=seq, source="mock")
            return WorkflowResult(
                success=True,
                task_id="t1",
                best_candidate=candidate,
                all_candidates=[candidate],
                summary="mock success",
            )

    runner = AgentRunner(
        executor=ToolExecutor(build_default_tool_registry()),
        session_memory=SessionMemory(),
    )
    runner.specialist_registry["mock_workflow"] = SpecialistAgent(
        _MockWorkflow(), QualityProfile(workflow_name="mock_workflow", max_retries=0)
    )

    state1 = runner.run_form(
        form_params={"seq": "AAA"},
        session_id="s_prev",
        explicit_workflow="mock_workflow",
    )
    assert state1["workflow_result"].best_candidate.sequence == "AAA"

    state2 = runner.run_form(
        form_params={"seq": "BBB"},
        session_id="s_prev",
        explicit_workflow="mock_workflow",
    )
    assert state2["workflow_result"].best_candidate.sequence == "BBB"
    assert state2.get("_previous_workflow_result") is not None
    assert state2["_previous_workflow_result"].best_candidate.sequence == "AAA"
    history = state2.get("_workflow_result_history", [])
    assert len(history) == 1
    assert history[0].best_candidate.sequence == "AAA"


def test_load_pipeline_plan(tmp_path):
    import json as _json
    from cli.form_chat import _load_pipeline_plan

    plan_file = tmp_path / "plan.json"
    plan_file.write_text(
        _json.dumps({
            "plan_id": "test_plan",
            "nodes": [
                {"node_id": "n1", "workflow": "mock_workflow", "static_params": {"seq": "AUG"}}
            ],
            "edges": [],
        }),
        encoding="utf-8",
    )
    plan = _load_pipeline_plan(str(plan_file))
    assert plan.plan_id == "test_plan"
    assert len(plan.nodes) == 1
    assert plan.nodes[0].node_id == "n1"
