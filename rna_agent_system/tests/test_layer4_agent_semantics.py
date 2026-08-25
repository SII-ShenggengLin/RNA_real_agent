"""Layer-4 agent semantics shared across reviewed workflows.

The QualityAgent retry loop, disabled-critic path, and the
``progress_callback`` run-signature contract are agent-layer contracts.  They
are pinned once here against two representative reviewed workflows
(secondary- and tertiary-structure design) instead of being duplicated in
each per-workflow Layer-4 module.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from agent_core.agents import (
    PipelineAgent,
    QualityAgent,
    QualityReport,
    SpecialistAgent,
    SynthesisAgent,
)
from agent_core.pipeline.models import PipelinePlan
from agent_core.quality_profiles.rna_secondary_structure_design import (
    RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE,
)
from agent_core.quality_profiles.rna_tertiary_structure_design import (
    RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE,
)
from agent_core.workflows.rna_secondary_structure_design import (
    RnaSecondaryStructureDesignWorkflow,
)
from agent_core.workflows.rna_tertiary_structure_design import (
    RnaTertiaryStructureDesignWorkflow,
)
from tests.test_rna_secondary_structure_design_layer4 import (
    _make_full_registry as _secondary_registry,
)
from tests.test_rna_tertiary_structure_design_layer4 import (
    _ensure_tmp_pdb,
    _make_full_registry as _tertiary_registry,
)

_TMP_PDB_PATH = "/tmp/test_structure.pdb"

# (registry factory, workflow class, quality profile, plan params, retry
# override key — an int input field the retrying QualityAgents adjust)
CASES = {
    "secondary": (
        _secondary_registry,
        RnaSecondaryStructureDesignWorkflow,
        RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE,
        {"target_structure": "((((....))))....((((....))))", "num_invocations": 1},
        "repeats",
    ),
    "tertiary": (
        _tertiary_registry,
        RnaTertiaryStructureDesignWorkflow,
        RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE,
        {"structure_filepath": _TMP_PDB_PATH, "design_tools": "rhodesign", "n_samples_per_tool": 2},
        "rhodesign_temperature_range",
    ),
}


def _pipeline_agent(case: str, quality_agent: QualityAgent) -> PipelineAgent:
    make_registry, wf_cls, profile, _, _ = CASES[case]
    specialist = SpecialistAgent(wf_cls(make_registry()), profile)
    return PipelineAgent(
        specialist_registry={specialist.workflow.name: specialist},
        quality_agent=quality_agent,
        synthesis_agent=SynthesisAgent(enable_llm=False),
    )


def _plan(case: str) -> PipelinePlan:
    _, wf_cls, _, params, _ = CASES[case]
    return PipelinePlan.single(workflow=wf_cls.name, static_params=params)


class _OneTimeRetryQualityAgent(QualityAgent):
    """QualityAgent that requests retry exactly once (bumping *key*), then passes."""

    def __init__(self, key: str):
        super().__init__(llm=None)
        self.key = key
        self.review_count = 0

    def review(self, result, profile, state):
        self.review_count += 1
        if self.review_count == 1:
            current = state.get("_last_workflow_params", {}).get(self.key, 1)
            return QualityReport(
                overall_assessment="Retry requested",
                quality_score=0.5,
                action="retry_with_adjustments",
                parameter_overrides={self.key: current + 1},
                reasoning="Increase search effort for better fidelity.",
            )
        return QualityReport(
            overall_assessment="Pass",
            quality_score=1.0,
            action="pass",
            reasoning="Acceptable after retry.",
        )


class _AlwaysRetryQualityAgent(QualityAgent):
    """QualityAgent that always recommends retry with a changing override."""

    def __init__(self, key: str):
        super().__init__(llm=None)
        self.key = key

    def review(self, result, profile, state):
        current = state.get("_last_workflow_params", {}).get(self.key, 1)
        return QualityReport(
            overall_assessment="Retry requested",
            quality_score=0.3,
            action="retry_with_adjustments",
            parameter_overrides={self.key: current + 1},
            reasoning="Keep increasing search effort.",
        )


@pytest.mark.parametrize("case", sorted(CASES))
def test_quality_agent_retry_once(case):
    """A retry recommendation should trigger exactly one workflow rerun."""
    _ensure_tmp_pdb()
    _, _, _, _, key = CASES[case]
    agent = _pipeline_agent(case, _OneTimeRetryQualityAgent(key))
    state: dict[str, Any] = {"_quality_review_enabled": True, "_quality_auto_retry": True}
    result = agent.execute(_plan(case), state)

    assert result.success is True
    assert result.node_results["n1"].metadata["retry_count"] == 1


@pytest.mark.parametrize("case", sorted(CASES))
def test_quality_agent_max_retries_exhausted(case):
    """SpecialistAgent stops retrying once the QualityProfile max_retries is reached."""
    _ensure_tmp_pdb()
    _, _, profile, _, key = CASES[case]
    agent = _pipeline_agent(case, _AlwaysRetryQualityAgent(key))
    state: dict[str, Any] = {"_quality_review_enabled": True, "_quality_auto_retry": True}
    result = agent.execute(_plan(case), state)

    assert result.success is True
    assert result.node_results["n1"].metadata["retry_count"] == profile.max_retries


@pytest.mark.parametrize("case", sorted(CASES))
def test_quality_agent_disabled_no_retry(case):
    """With the critic disabled, QualityAgent passes and no retry occurs."""
    _ensure_tmp_pdb()
    agent = _pipeline_agent(case, QualityAgent())
    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = agent.execute(_plan(case), state)

    assert result.success is True
    assert result.node_results["n1"].metadata["retry_count"] == 0
    assert result.quality_reports["n1"].action == "pass"


@pytest.mark.parametrize("case", sorted(CASES))
def test_workflow_run_signature_has_progress_callback(case):
    """The workflow's run() must accept an optional progress_callback."""
    _, wf_cls, _, _, _ = CASES[case]
    sig = inspect.signature(wf_cls.run)
    assert "progress_callback" in sig.parameters
    assert sig.parameters["progress_callback"].default is None
