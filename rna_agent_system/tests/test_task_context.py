"""W1.2 task-context gating tests.

DecisionGate reviews must be keyed to the *calling* workflow's task type, not
the oracle's registered default: ``BaseDomainWorkflow`` declares ``task_type``,
wraps its execution paths in ``task_context(...)``, and the runtime consults
the contextvar.  Flagship workflows must keep querying the exact SelfModel
task keys their profiling campaigns recorded under.
"""

from __future__ import annotations

import contextvars
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from agent_core.calibrated.runtime import (
    CalibratedRuntime,
    current_task_type,
    task_context,
)
from agent_core.workflows.aso_target_screening import AsoTargetScreeningWorkflow
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.full_length_mrna_design import FullLengthMrnaDesignWorkflow
from agent_core.workflows.ires_prediction import IresPredictionWorkflow
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignWorkflow
from agent_core.workflows.mrna_sequence_scoring import MrnaSequenceScoringWorkflow
from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignWorkflow
from agent_core.workflows.rna_secondary_structure_design import (
    RnaSecondaryStructureDesignWorkflow,
)
from agent_core.workflows.rna_small_molecule_interaction import (
    RnaSmallMoleculeInteractionWorkflow,
)
from agent_core.workflows.rna_tertiary_structure_design import (
    RnaTertiaryStructureDesignWorkflow,
)
from agent_core.workflows.sgrna_design import SgRnaDesignWorkflow
from agent_core.workflows.sirna_design import SirnaDesignWorkflow
from agent_core.workflow_models import Candidate, WorkflowResult

# Workflows whose task_type MUST equal the SelfModel key their (E1/E7/RNAsmol)
# profiling records live under — a drift would silently change gating.
SELF_MODEL_KEYED_WORKFLOWS = {
    RnaAptamerDesignWorkflow: "rna_aptamer_design",
    FullLengthMrnaDesignWorkflow: "full_length_mrna",
    RnaSmallMoleculeInteractionWorkflow: "rna_small_molecule",
}

ALL_WORKFLOW_CLASSES = [
    MrnaCdsDesignWorkflow,
    SirnaDesignWorkflow,
    SgRnaDesignWorkflow,
    RnaAptamerDesignWorkflow,
    RnaSmallMoleculeInteractionWorkflow,
    AsoTargetScreeningWorkflow,
    IresPredictionWorkflow,
    RnaSecondaryStructureDesignWorkflow,
    RnaTertiaryStructureDesignWorkflow,
    FullLengthMrnaDesignWorkflow,
    MrnaSequenceScoringWorkflow,
]


def test_every_workflow_declares_task_type() -> None:
    assert len(ALL_WORKFLOW_CLASSES) == 11
    for cls in ALL_WORKFLOW_CLASSES:
        assert cls.task_type, f"{cls.__name__}: task_type not declared"
    for cls, key in SELF_MODEL_KEYED_WORKFLOWS.items():
        assert cls.task_type == key, (
            f"{cls.__name__}.task_type={cls.task_type!r} drifted from SelfModel key {key!r}"
        )


def test_review_keyed_to_calling_task(tmp_path: Path) -> None:
    runtime = CalibratedRuntime.configure(audit_path=tmp_path / "audit.jsonl", policy="enforce")
    try:
        # Default (no workflow context): RhoFold queries its E1 aptamer records
        # -> conservative transfer of the failed families -> reject.
        d = runtime.review_tool_call("predict_rna_tertiary_structure_with_rhofold")
        assert d is not None and d.verdict == "reject"

        # Inside the aptamer workflow's context: identical keying.
        with task_context("rna_aptamer_design"):
            d = runtime.review_tool_call("predict_rna_tertiary_structure_with_rhofold")
            assert d is not None and d.verdict == "reject"

        # Inside the tertiary-structure workflow's context: the honest key —
        # no profiling records for (rhofold, rna_tertiary_structure_design)
        # -> unprofiled, not an inherited aptamer failure.
        with task_context("rna_tertiary_structure_design"):
            d = runtime.review_tool_call("predict_rna_tertiary_structure_with_rhofold")
            assert d is not None and d.verdict == "require_profiling"

        # Flagship oracles keep their verdicts under their own workflows'
        # contexts (E7 MRL verified on 3 families -> transferred downgrade).
        with task_context("full_length_mrna"):
            d = runtime.review_tool_call("predict_5utr_mrl_with_gemorna")
            assert d is not None and d.verdict == "downgrade"

        # Context resets cleanly after exit.
        assert current_task_type() is None
    finally:
        CalibratedRuntime.clear()


def _probe_workflow(task: str) -> type[BaseDomainWorkflow]:
    """Minimal concrete workflow recording the task context seen in evaluate()."""

    class ProbeWorkflow(BaseDomainWorkflow):
        name = "probe_workflow"
        task_type = task
        seen: list[str | None] = []

        def generate_candidates(self, inp: Any) -> list[Candidate]:
            return [Candidate(sequence="AUGCGCGCGCGCGUGU", sequence_type="rna", source="probe")]

        def evaluate(self, candidate: Candidate) -> dict[str, Any]:
            type(self).seen.append(current_task_type())
            return {"gc": 0.5}

        def score(self, metrics: dict[str, Any]) -> dict[str, float]:
            return {"total": metrics["gc"]}

        def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
            return WorkflowResult(success=True, task_id="probe", summary="probe", best_candidate=candidates[0] if candidates else None)

    return ProbeWorkflow


def test_base_run_propagates_task_context() -> None:
    for expected in ("rna_tertiary_structure_design", ""):
        probe_cls = _probe_workflow(expected)
        wf = probe_cls()
        wf.auto_start_services = False
        result = wf.run({})
        assert result.success
        assert probe_cls.seen == [expected or None]


def test_thread_pool_context_propagation_pattern() -> None:
    """The exact pattern used by the aptamer concurrent evaluator."""
    def reader() -> str | None:
        return current_task_type()

    with task_context("rna_small_molecule"):
        with ThreadPoolExecutor(max_workers=2) as executor:
            copied = executor.submit(contextvars.copy_context().run, reader)
            bare = executor.submit(reader)  # no copy -> contextvar default
        assert copied.result() == "rna_small_molecule"
        assert bare.result() is None


def test_contextvar_is_isolated_across_tests() -> None:
    assert current_task_type() is None
