"""Tests for RNA-small molecule interaction workflow.

Covers:
1. score_rna_ligand_candidate unit scoring
2. RnaSmallMoleculeInteractionInput Pydantic validation
3. Workflow integration with mocked capabilities
4. rank_and_format edge cases (empty candidates, all tools failing)
"""

from __future__ import annotations

from tests.helpers import make_mock_capability

from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_core.capabilities.base import CapabilityResult
from agent_core.workflow_models import Candidate
from agent_core.workflows.rna_small_molecule_interaction import (
    RnaSmallMoleculeInteractionInput,
    RnaSmallMoleculeInteractionWorkflow,
    score_rna_ligand_candidate,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Scoring function tests
# ─────────────────────────────────────────────────────────────────────────────


def test_score_rna_ligand_both_tools():
    """Both probabilities available → average."""
    metrics = {
        "rnasmol_probability_positive": 0.80,
        "gernabind_probability_positive": 0.60,
    }
    scores = score_rna_ligand_candidate(metrics)
    assert scores["rnasmol_component"] == pytest.approx(0.80, abs=1e-6)
    assert scores["gernabind_component"] == pytest.approx(0.60, abs=1e-6)
    assert scores["total_score"] == pytest.approx(0.70, abs=1e-6)


def test_score_rna_ligand_only_rnasmol():
    """Only RNAsmol available → total = that component."""
    metrics = {"rnasmol_probability_positive": 0.75}
    scores = score_rna_ligand_candidate(metrics)
    assert scores["rnasmol_component"] == pytest.approx(0.75, abs=1e-6)
    assert scores["gernabind_component"] == 0.0
    assert scores["total_score"] == pytest.approx(0.75, abs=1e-6)


def test_score_rna_ligand_only_gernabind():
    """Only GerNA-Bind available → total = that component."""
    metrics = {"gernabind_probability_positive": 0.40}
    scores = score_rna_ligand_candidate(metrics)
    assert scores["rnasmol_component"] == 0.0
    assert scores["gernabind_component"] == pytest.approx(0.40, abs=1e-6)
    assert scores["total_score"] == pytest.approx(0.40, abs=1e-6)


def test_score_rna_ligand_no_metrics():
    """No metrics → total_score = 0.0."""
    scores = score_rna_ligand_candidate({})
    assert scores["total_score"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pydantic input validation tests
# ─────────────────────────────────────────────────────────────────────────────


def test_input_basic():
    inp = RnaSmallMoleculeInteractionInput(
        rna_sequence="AUGCAUGC",
        smiles="CCO",
    )
    assert inp.rna_sequence == "AUGCAUGC"
    assert inp.smiles == "CCO"
    assert inp.scoring_tools == ["rnasmol", "gernabind"]


def test_input_dict_coercion():
    raw = {
        "rna_sequence": "AUGC",
        "smiles": "c1ccccc1",
        "scoring_tools": ["rnasmol"],
    }
    inp = RnaSmallMoleculeInteractionInput(**raw)
    assert inp.scoring_tools == ["rnasmol"]


def test_input_invalid_rna_sequence():
    with pytest.raises(Exception):
        RnaSmallMoleculeInteractionInput(
            rna_sequence="AUGCX",
            smiles="CCO",
        )


def test_input_invalid_smiles():
    with pytest.raises(Exception):
        RnaSmallMoleculeInteractionInput(
            rna_sequence="AUGC",
            smiles="xyz!!!",
        )


def test_input_empty_smiles():
    with pytest.raises(Exception):
        RnaSmallMoleculeInteractionInput(
            rna_sequence="AUGC",
            smiles="   ",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Workflow integration tests (mocked capabilities)
# ─────────────────────────────────────────────────────────────────────────────


def _make_registry() -> MagicMock:
    """Registry with mocked scoring capabilities."""
    reg = MagicMock()

    cap_rnasmol = make_mock_capability({
        "probability_positive": 0.80,
        "predicted_label": 1,
    })
    cap_gernabind = make_mock_capability({
        "probability_positive": 0.60,
        "predicted_label": 1,
    })

    caps = {
        "score_rna_ligand_binding_with_rnasmol": cap_rnasmol,
        "score_rna_ligand_binding_with_gernabind": cap_gernabind,
    }

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


def test_generate_candidates_wraps_input():
    """User input should be wrapped as a single candidate."""
    reg = _make_registry()
    wf = RnaSmallMoleculeInteractionWorkflow(reg)
    inp = RnaSmallMoleculeInteractionInput(
        rna_sequence="AUGCAUGC",
        smiles="CCO",
    )
    candidates = wf.generate_candidates(inp)
    assert len(candidates) == 1
    assert candidates[0].sequence == "AUGCAUGC"
    assert candidates[0].metadata["smiles"] == "CCO"


def test_evaluate_with_mocked_capabilities():
    """Evaluation should populate metrics_bundle with both tool results."""
    reg = _make_registry()
    wf = RnaSmallMoleculeInteractionWorkflow(reg)
    candidate = Candidate(
        sequence="AUGCAUGC",
        metadata={"smiles": "CCO", "scoring_tools": ["rnasmol", "gernabind"]},
    )
    metrics = wf.evaluate(candidate)
    assert metrics["rnasmol_probability_positive"] == pytest.approx(0.80, abs=1e-6)
    assert metrics["gernabind_probability_positive"] == pytest.approx(0.60, abs=1e-6)


def test_score_and_rank_pipeline():
    """Full pipeline: generate → evaluate → score → rank."""
    reg = _make_registry()
    wf = RnaSmallMoleculeInteractionWorkflow(reg)
    inp = RnaSmallMoleculeInteractionInput(
        rna_sequence="AUGCAUGC",
        smiles="CCO",
    )
    result = wf.run(inp)
    assert result.success is True
    assert result.best_candidate is not None
    assert len(result.all_candidates) == 1
    assert result.best_candidate.scores["total_score"] == pytest.approx(0.70, abs=1e-6)
    assert "RNAsmol_prob=" in result.summary
    assert "GerNA-Bind_prob=" in result.summary


def test_rank_and_format_empty_candidates():
    wf = RnaSmallMoleculeInteractionWorkflow(MagicMock())
    result = wf.rank_and_format([])
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_rank_and_format_all_tools_fail():
    """When both scoring tools fail, result.success should be False."""
    reg = MagicMock()
    reg.has.return_value = True
    # Simulate failures for both tools
    cap_fail = MagicMock()
    cap_fail.invoke.return_value = CapabilityResult(
        success=False,
        tool_name="mock",
        output={},
        error="service unreachable",
    )
    reg.get.return_value = cap_fail

    wf = RnaSmallMoleculeInteractionWorkflow(reg)
    candidate = Candidate(
        sequence="AUGCAUGC",
        metadata={"smiles": "CCO", "scoring_tools": ["rnasmol", "gernabind"]},
    )
    # Manually set up metrics_bundle with None scores (as evaluate would do on failure)
    candidate.metadata["metrics_bundle"] = {
        "rna_sequence": "AUGCAUGC",
        "smiles": "CCO",
        "sequence_length": 8,
        "rnasmol_probability_positive": None,
        "rnasmol_predicted_label": None,
        "gernabind_probability_positive": None,
        "gernabind_predicted_label": None,
    }
    candidate.scores = wf.score(candidate.metadata["metrics_bundle"])
    candidates = [candidate]

    result = wf.rank_and_format(candidates)
    assert result.success is False
    assert "all_scoring_tools_failed" in result.errors


# ─────────────────────────────────────────────────────────────────────────────
# 5. Layer 3 integration tests
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_agent_runs_workflow():
    """PipelineAgent should execute rna_small_molecule_interaction as a workflow node."""
    from agent_core.agents.pipeline_agent import PipelineAgent
    from agent_core.agents.quality_agent import QualityAgent
    from agent_core.agents.specialist_agent import SpecialistAgent
    from agent_core.agents.synthesis_agent import SynthesisAgent
    from agent_core.pipeline.models import PipelinePlan
    from agent_core.quality_profiles.rna_small_molecule_interaction import (
        RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE,
    )

    reg = _make_registry()
    wf = RnaSmallMoleculeInteractionWorkflow(reg)
    specialist = SpecialistAgent(wf, RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE)
    pipeline_agent = PipelineAgent(
        specialist_registry={"rna_small_molecule_interaction": specialist},
        quality_agent=QualityAgent(),
        synthesis_agent=SynthesisAgent(),
    )

    plan = PipelinePlan.single(
        workflow="rna_small_molecule_interaction",
        static_params={"rna_sequence": "AUGCAUGC", "smiles": "CCO"},
        plan_id="ligand_run",
        output_alias="ligand_result",
    )

    result = pipeline_agent.execute(plan)

    assert result.success is True
    node_result = result.node_results["n1"]
    assert node_result.workflow_result is not None
    assert node_result.workflow_result.success is True
    assert result.quality_reports["n1"].action == "pass"


def test_pipeline_agent_no_quality_retry():
    """rna_small_molecule_interaction has empty QualityProfile; retry must not be triggered."""
    from agent_core.agents.pipeline_agent import PipelineAgent
    from agent_core.agents.quality_agent import QualityAgent
    from agent_core.agents.specialist_agent import SpecialistAgent
    from agent_core.agents.synthesis_agent import SynthesisAgent
    from agent_core.pipeline.models import PipelinePlan
    from agent_core.quality_profiles.rna_small_molecule_interaction import (
        RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE,
    )

    reg = _make_registry()
    wf = RnaSmallMoleculeInteractionWorkflow(reg)
    specialist = SpecialistAgent(wf, RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE)
    pipeline_agent = PipelineAgent(
        specialist_registry={"rna_small_molecule_interaction": specialist},
        quality_agent=QualityAgent(),
        synthesis_agent=SynthesisAgent(),
    )

    plan = PipelinePlan.single(
        workflow="rna_small_molecule_interaction",
        static_params={"rna_sequence": "AUGCAUGC", "smiles": "CCO"},
        plan_id="ligand_no_retry",
        output_alias="ligand_result",
    )

    result = pipeline_agent.execute(plan)

    node_result = result.node_results["n1"]
    assert node_result.metadata.get("retry_count", 0) == 0
    assert result.quality_reports["n1"].action == "pass"


def test_pipeline_agent_progress_callback():
    """progress_callback should receive payload events from the workflow."""
    from agent_core.agents.pipeline_agent import PipelineAgent
    from agent_core.agents.quality_agent import QualityAgent
    from agent_core.agents.specialist_agent import SpecialistAgent
    from agent_core.agents.synthesis_agent import SynthesisAgent
    from agent_core.pipeline.models import PipelinePlan
    from agent_core.quality_profiles.rna_small_molecule_interaction import (
        RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE,
    )

    reg = _make_registry()
    wf = RnaSmallMoleculeInteractionWorkflow(reg)
    specialist = SpecialistAgent(wf, RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE)
    pipeline_agent = PipelineAgent(
        specialist_registry={"rna_small_molecule_interaction": specialist},
        quality_agent=QualityAgent(),
        synthesis_agent=SynthesisAgent(),
    )

    plan = PipelinePlan.single(
        workflow="rna_small_molecule_interaction",
        static_params={"rna_sequence": "AUGCAUGC", "smiles": "CCO"},
        plan_id="ligand_progress",
        output_alias="ligand_result",
    )

    progress_events: list[dict[str, Any]] = []

    def progress_callback(event: dict[str, Any]) -> None:
        progress_events.append(event)

    pipeline_agent.execute(plan, progress_callback=progress_callback)

    events = {e.get("event") for e in progress_events}
    assert "generate_complete" in events or "evaluate_progress" in events or "step_done" in events
