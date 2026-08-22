"""Layer-4 fresh-data audit regressions (2026-08-22).

Four defects found by ``workspace/layer4_fresh_audit_2026-08-22/`` and fixed
the same day:

1. ``PipelineAgent.execute`` let a runtime-dangling input binding raise an
   unhandled ``BindingResolutionError`` out of the whole pipeline (reachable
   when an upstream non-critical node was skipped so its result never
   existed). It must degrade to a per-node failure like any other error.
2. ``SpecialistAgent`` counted an abandoned retry attempt (all overrides
   protected as user-explicit) in ``metadata["retry_count"]`` although no
   re-execution happened.
3. ``QualityAgent`` silently dropped LLM override suggestions that quoted an
   integer-valued enum parameter (``"iresfinder_mode": "2"``); they are now
   coerced to the int form.
4. ``AuditEvent.event_type`` lacked ``ranking_objective_assembly``, so the
   best-effort writer in ``assemble_for_workflow`` silently discarded every
   ranking-governance audit event (pydantic Literal rejection swallowed by
   ``except Exception: pass``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agent_core.agents.pipeline_agent import PipelineAgent
from agent_core.agents.quality_agent import QualityAgent, QualityProfile, QualityReport
from agent_core.agents.specialist_agent import SpecialistAgent
from agent_core.agents.synthesis_agent import SynthesisAgent
from agent_core.calibrated.objective_assembly import (
    ObjectiveRef,
    assemble_for_workflow,
)
from agent_core.calibrated.runtime import CalibratedRuntime
from agent_core.pipeline.models import PipelineEdge, PipelineNode, PipelinePlan
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.base import BaseDomainWorkflow


# --------------------------------------------------------------- fixtures

class _EchoWorkflow(BaseDomainWorkflow[Any, WorkflowResult]):
    """Minimal deterministic workflow: one candidate per run, no services."""

    name = "echo"
    task_type = "echo"
    input_model = None

    def __init__(self) -> None:
        self.runs = 0

    def generate_candidates(self, inp: Any) -> list[Candidate]:
        self.runs += 1
        return [Candidate(sequence="ACGUACGUACGU", sequence_type="rna", source="echo")]

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        return {"gc_content": 0.5}

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        return {"total_score": 1.0}

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        return WorkflowResult(success=True, task_id="t", all_candidates=candidates,
                              best_candidate=candidates[0] if candidates else None,
                              summary="echo ok")


class _ScriptedQualityAgent(QualityAgent):
    """Deterministic stand-in for the advisory LLM diagnosis."""

    def __init__(self, script: list[QualityReport]) -> None:
        super().__init__(llm=None)
        self._script = list(script)
        self._script.extend([
            QualityReport(overall_assessment="scripted pass", quality_score=1.0, action="pass")
        ] * 10)

    def review(self, result: Any, profile: Any, state: dict) -> QualityReport:
        return self._script.pop(0)


@pytest.fixture()
def echo_specialist() -> SpecialistAgent:
    return SpecialistAgent(_EchoWorkflow(), QualityProfile(workflow_name="echo"))


# ------------------------------------------ 1. dangling binding degrades

def test_dangling_binding_after_skipped_node_degrades_gracefully(echo_specialist):
    plan = PipelinePlan(plan_id="dangling", nodes=[
        PipelineNode(node_id="bad", workflow="no_such_workflow", critical=False),
        PipelineNode(node_id="good", workflow="echo",
                     input_bindings={"x": "$bad.workflow_result.best_candidate.sequence"}),
    ], edges=[PipelineEdge(source="bad", target="good")])

    agent = PipelineAgent(
        specialist_registry={"echo": echo_specialist},
        quality_agent=_ScriptedQualityAgent([]),
        synthesis_agent=SynthesisAgent(enable_llm=False),
    )
    result = agent.execute(plan, state={})  # must not raise

    assert result.success is False
    assert any("input binding resolution failed" in e for e in result.errors)
    assert "good" in result.node_results
    assert result.node_results["good"].success is False


def test_dangling_binding_critical_node_stops_pipeline(echo_specialist):
    plan = PipelinePlan(plan_id="dangling-critical", nodes=[
        PipelineNode(node_id="bad", workflow="no_such_workflow", critical=True),
    ], edges=[])
    agent = PipelineAgent(
        specialist_registry={"echo": echo_specialist},
        quality_agent=_ScriptedQualityAgent([]),
        synthesis_agent=SynthesisAgent(enable_llm=False),
    )
    result = agent.execute(plan, state={})
    assert result.success is False
    assert len(result.node_results) == 0  # nothing else scheduled after break


# --------------------------------- 2. retry_count counts real re-executions

def test_protected_overrides_do_not_consume_retry_count(echo_specialist):
    script = [
        QualityReport(overall_assessment="suggest change",
                      quality_score=0.5, action="retry_with_adjustments",
                      parameter_overrides={"design_tool": "rnarl"}),
    ]
    agent = _ScriptedQualityAgent(script)
    state = {"_user_explicit_params": ["design_tool"]}
    result = echo_specialist.run(
        "n", {"design_tool": "lineardesign"}, agent, state=state,
    )
    assert result.metadata["retry_count"] == 0
    assert result.workflow_result.success is True


def test_actionable_overrides_still_count(echo_specialist):
    script = [
        QualityReport(overall_assessment="suggest change",
                      quality_score=0.5, action="retry_with_adjustments",
                      parameter_overrides={"candidate_count": 7}),
    ]
    agent = _ScriptedQualityAgent(script)
    profile = QualityProfile(workflow_name="echo",
                             adjustable_params={"candidate_count": {"type": "int"}})
    specialist = SpecialistAgent(_EchoWorkflow(), profile)
    result = specialist.run(
        "n", {"candidate_count": 5}, agent,
        state={"_user_explicit_params": [], "_quality_auto_retry": True},
    )
    assert result.metadata["retry_count"] == 1


# ------------------------------- 3. int-enum string coercion in overrides

def _ires_profile() -> QualityProfile:
    return QualityProfile(workflow_name="ires_prediction", adjustable_params={
        "iresfinder_mode": {"type": "enum", "values": [0, 1, 2]},
        "mode": {"type": "enum", "values": ["antiviral", "generic"]},
    })


def test_int_enum_string_value_is_coerced():
    qa = QualityAgent.__new__(QualityAgent)
    filtered = qa._filter_overrides(
        {"iresfinder_mode": "2"}, _ires_profile(), set(), {}
    )
    assert filtered == {"iresfinder_mode": 2}


def test_int_enum_out_of_range_string_is_dropped():
    qa = QualityAgent.__new__(QualityAgent)
    filtered = qa._filter_overrides(
        {"iresfinder_mode": "9"}, _ires_profile(), set(), {}
    )
    assert filtered == {}


def test_string_enum_values_are_not_coerced():
    qa = QualityAgent.__new__(QualityAgent)
    filtered = qa._filter_overrides(
        {"mode": "antiviral"}, _ires_profile(), set(), {}
    )
    assert filtered == {"mode": "antiviral"}


# --------------------- 4. ranking-governance audit events are persisted

def test_assemble_for_workflow_records_audit_event(tmp_path: Path):
    CalibratedRuntime.clear()
    audit_path = tmp_path / "audit.jsonl"
    CalibratedRuntime.configure(audit_path=audit_path, policy="advisory")
    try:
        refs = {"egarps_component": ObjectiveRef(
            dim="egarps_component", tool_name="score_rna_protein_complex_with_egarps",
            oracle_id="egarps_native_probability")}
        assembled = assemble_for_workflow(
            ["egarps_component", "gc_content"], refs, "rna_aptamer_design"
        )
        events = [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
        roa = [e for e in events if e["event_type"] == "ranking_objective_assembly"]
        assert len(roa) == 1, f"expected one assembly event, got {len(roa)}"
        payload = roa[0]["payload"]
        assert payload["task_type"] == "rna_aptamer_design"
        assert "egarps_component" in payload["demoted"]
        assert "gc_content" in payload["ranking_dims"]
        assert assembled.demoted == {"egarps_component": payload["demoted"]["egarps_component"]}
    finally:
        CalibratedRuntime.clear()


def test_audit_event_accepts_ranking_objective_assembly_type():
    from agent_core.calibrated.models import AuditEvent

    event = AuditEvent(event_type="ranking_objective_assembly", payload={"a": 1})
    assert event.event_type == "ranking_objective_assembly"


# ------------- 5. IRES generation tool failures are not silent no-hits

def test_ires_generation_tool_failure_is_a_hard_failure(tmp_path, monkeypatch):
    from agent_core.capabilities.base import (
        CapabilityRegistry,
        CapabilityResult,
        build_default_capability_registry,
    )
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.ires_prediction import (
        IresPredictionInput,
        IresPredictionWorkflow,
    )

    registry = build_default_capability_registry(
        ToolExecutor(build_default_tool_registry(include_demo=False))
    )
    monkeypatch.setattr(
        "agent_core.capabilities.base.Capability.invoke",
        lambda self, args, state=None: CapabilityResult(
            success=False, tool_name=self.tool_name,
            error="FileNotFoundError: no such file",
        ),
    )
    wf = IresPredictionWorkflow(registry)
    missing = tmp_path / "missing.fa"
    result = wf.run(IresPredictionInput(sequence_filepath=str(missing),
                                        iresfinder_mode=0))
    assert result.success is False
    assert result.is_hard_failure
    assert any("iresfinder tool failed" in e for e in result.errors)
    assert result.summary != "No IRES candidate regions found."


def test_ires_legitimate_empty_scan_stays_success():
    """No generation errors (scan ran, nothing found) keeps success=True."""
    from agent_core.workflows.ires_prediction import IresPredictionWorkflow

    wf = IresPredictionWorkflow.__new__(IresPredictionWorkflow)
    wf._generation_errors = []
    result = wf.rank_and_format([])
    assert result.success is True
    assert result.summary == "No IRES candidate regions found."
