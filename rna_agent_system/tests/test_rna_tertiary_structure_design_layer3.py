"""Layer 3 integration tests for RNA tertiary structure design workflow.

Covers:
1. ExecutionController → workflow progress_callback forwarding
2. _execution_log event type completeness
3. Critic retry loop with replan
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch


from agent_core.capabilities.base import CapabilityResult
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.workflows.rna_tertiary_structure_design import (
    RnaTertiaryStructureDesignWorkflow,
)


_TMP_PDB_PATH = "/tmp/test_structure.pdb"


def _ensure_tmp_pdb() -> None:
    import os
    if not os.path.exists(_TMP_PDB_PATH):
        with open(_TMP_PDB_PATH, "w") as fh:
            fh.write("ATOM    1  N   A   A   1      10.000  10.000  10.000  1.00  0.00           N\n")


def _make_full_registry():
    """Registry with all mocked capabilities for tertiary structure workflow."""
    reg = MagicMock()

    # RhoDesign mock
    _rhodesign_call_count = 0
    _rhodesign_seqs = [
        "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
        "AUGCAUGCAUGCAUGCAUGCAUGCAUGCAU",
    ]

    def _rhodesign_invoke(args, state=None):
        nonlocal _rhodesign_call_count
        seq = _rhodesign_seqs[_rhodesign_call_count % len(_rhodesign_seqs)]
        _rhodesign_call_count += 1
        return CapabilityResult(
            success=True,
            tool_name="design_rna_sequence_with_rhodesign",
            output={
                "predicted_sequence": seq,
                "recovery_rate": 0.85,
                "output_fasta_filepath": "workspace/rhodesign_out.fasta",
                "input_pdb_filepath": _TMP_PDB_PATH,
            },
        )

    cap_rhodesign = MagicMock()
    cap_rhodesign.invoke = _rhodesign_invoke

    # RiboDiffusion mock
    cap_ribodiffusion = MagicMock()
    cap_ribodiffusion.invoke.return_value = CapabilityResult(
        success=True,
        tool_name="design_rna_inverse_fold_with_ribodiffusion",
        output={
            "predicted_sequence": "CCGAUCCGAUCCGAUCCGAUCCGAUCCGAU",
            "recovery_rate": 0.72,
            "output_fasta_filepaths": ["workspace/ribodiffusion_0.fasta"],
            "input_pdb_filepath": _TMP_PDB_PATH,
        },
    )

    # Evaluation mocks
    def _gc_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="compute_rna_sequence_gc_content",
            output={"gc_content": 0.48, "sequence_length": 30},
        )

    def _fold_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_secondary_structure",
            output={
                "structure": "((((....))))....((((....))))",
                "mfe_kcal_per_mol": -15.5,
                "backend": "ViennaRNA",
            },
        )

    def _rhofold_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_tertiary_structure_with_rhofold",
            output={"pdb_filepath": "workspace/rhofold_test.pdb", "mean_plddt": 85.0},
        )

    def _alignment_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="score_structure_alignment",
            output={
                "rmsd": 2.1,
                "tm_score": 0.88,
                "aligned_residue_count": 30,
            },
        )

    caps = {
        "design_rna_sequence_with_rhodesign": cap_rhodesign,
        "design_rna_inverse_fold_with_ribodiffusion": cap_ribodiffusion,
        "compute_rna_sequence_gc_content": MagicMock(),
        "predict_rna_secondary_structure": MagicMock(),
        "predict_rna_tertiary_structure_with_rhofold": MagicMock(),
        "score_structure_alignment": MagicMock(),
    }
    caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
    caps["predict_rna_secondary_structure"].invoke = _fold_invoke
    caps["predict_rna_tertiary_structure_with_rhofold"].invoke = _rhofold_invoke
    caps["score_structure_alignment"].invoke = _alignment_invoke

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


# ─────────────────────────────────────────────────────────────────────────────
# 1. ExecutionController + progress_callback
# ─────────────────────────────────────────────────────────────────────────────


def test_execution_controller_progress_callback():
    """ExecutionController should forward progress_callback to workflow.run()."""
    _ensure_tmp_pdb()
    reg = _make_full_registry()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    workflow_registry = {"rna_tertiary_structure_design": wf}

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_tertiary_structure_design",
                input_binding={
                    "structure_filepath": _TMP_PDB_PATH,
                    "design_tools": "rhodesign",
                    "n_samples_per_tool": 2,
                },
                output_key="result",
                description="Design RNA tertiary structure",
            )
        ]
    )

    events = []

    def callback(event: dict[str, Any]) -> None:
        events.append(event)

    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry=workflow_registry,
    )
    state: dict[str, Any] = {"_llm_critic_enabled": False}
    result_state = controller.execute(plan, state, progress_callback=callback)

    assert result_state["_plan_executed"] is True
    assert len(events) > 0

    event_types = [e["event"] for e in events]
    assert "step_start" in event_types
    assert "step_done" in event_types
    # workflow.run() internal events
    assert "generate_complete" in event_types
    assert "evaluate_progress" in event_types
    assert "plan_complete" in event_types


def test_execution_controller_no_callback():
    """ExecutionController should work without progress_callback."""
    _ensure_tmp_pdb()
    reg = _make_full_registry()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    workflow_registry = {"rna_tertiary_structure_design": wf}

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_tertiary_structure_design",
                input_binding={
                    "structure_filepath": _TMP_PDB_PATH,
                    "design_tools": "rhodesign",
                    "n_samples_per_tool": 2,
                },
                output_key="result",
            )
        ]
    )

    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry=workflow_registry,
    )
    state: dict[str, Any] = {"_llm_critic_enabled": False}
    result_state = controller.execute(plan, state)

    assert result_state["_plan_executed"] is True
    log = result_state.get("_execution_log", [])
    assert len(log) >= 3  # step_start, step_done, plan_complete


# ─────────────────────────────────────────────────────────────────────────────
# 2. _execution_log completeness
# ─────────────────────────────────────────────────────────────────────────────


def test_execution_log_event_types():
    """_execution_log should contain all expected event types."""
    _ensure_tmp_pdb()
    reg = _make_full_registry()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    workflow_registry = {"rna_tertiary_structure_design": wf}

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_tertiary_structure_design",
                input_binding={
                    "structure_filepath": _TMP_PDB_PATH,
                    "design_tools": "rhodesign",
                    "n_samples_per_tool": 2,
                },
                output_key="result",
            )
        ]
    )

    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry=workflow_registry,
    )
    state: dict[str, Any] = {"_llm_critic_enabled": False}
    result_state = controller.execute(plan, state)

    log = result_state.get("_execution_log", [])
    assert len(log) > 0
    event_types = [e["event"] for e in log]
    assert "step_start" in event_types
    assert "step_done" in event_types
    assert "plan_complete" in event_types

    # Verify step_start metadata
    start_entries = [e for e in log if e["event"] == "step_start"]
    assert len(start_entries) == 1
    assert start_entries[0]["step_id"] == "step_1"
    assert start_entries[0]["type"] == "workflow"
    assert start_entries[0]["target"] == "rna_tertiary_structure_design"

    # Verify step_done metadata
    done_entries = [e for e in log if e["event"] == "step_done"]
    assert len(done_entries) == 1
    assert done_entries[0]["step_id"] == "step_1"
    assert done_entries[0]["success"] is True

    # Verify plan_complete metadata
    complete_entries = [e for e in log if e["event"] == "plan_complete"]
    assert len(complete_entries) == 1
    assert complete_entries[0]["step_count"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. Critic retry path
# ─────────────────────────────────────────────────────────────────────────────


class _OneTimeRetryCritic:
    """Critic that triggers retry exactly once."""

    def __init__(self):
        self.call_count = 0

    def should_retry(self, workflow_result: WorkflowResult, state: dict[str, Any]) -> bool:
        self.call_count += 1
        return self.call_count == 1


def test_critic_retry_replan_and_progress_callback():
    """Critic retry should re-execute from step 1 and continue progress_callback."""
    _ensure_tmp_pdb()
    reg = _make_full_registry()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    workflow_registry = {"rna_tertiary_structure_design": wf}

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_tertiary_structure_design",
                input_binding={
                    "structure_filepath": _TMP_PDB_PATH,
                    "design_tools": "rhodesign",
                    "n_samples_per_tool": 2,
                },
                output_key="result",
            )
        ],
        max_retries=2,
    )

    events = []

    def callback(event: dict[str, Any]) -> None:
        events.append(event)

    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry=workflow_registry,
    )

    def replan_fn(state: dict[str, Any]) -> ExecutionPlan:
        return plan

    state: dict[str, Any] = {}

    with patch(
        "agent_core.workflows.registry.get_critic_for_workflow",
        return_value=_OneTimeRetryCritic(),
    ):
        result_state = controller.execute(
            plan, state, replan_fn=replan_fn, progress_callback=callback
        )

    log = result_state.get("_execution_log", [])
    event_types = [e["event"] for e in log]

    # Executed twice (initial + 1 retry)
    assert event_types.count("step_start") == 2
    assert event_types.count("step_done") == 2
    assert "critic_retry" in event_types
    assert "replan" in event_types
    assert "plan_complete" in event_types
    assert result_state.get("retry_count") == 1

    # progress_callback should have received the same events
    callback_types = [e["event"] for e in events]
    assert "critic_retry" in callback_types
    assert "replan" in callback_types
    assert "plan_complete" in callback_types


def test_critic_retry_max_retries_exhausted():
    """When max_retries is exhausted, controller should return with retries_exhausted."""
    _ensure_tmp_pdb()
    reg = _make_full_registry()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    workflow_registry = {"rna_tertiary_structure_design": wf}

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_tertiary_structure_design",
                input_binding={
                    "structure_filepath": _TMP_PDB_PATH,
                    "design_tools": "rhodesign",
                    "n_samples_per_tool": 2,
                },
                output_key="result",
            )
        ],
        max_retries=1,
    )

    # Critic that always retries
    class _AlwaysRetryCritic:
        def should_retry(self, workflow_result: WorkflowResult, state: dict[str, Any]) -> bool:
            return True

    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry=workflow_registry,
    )

    def replan_fn(state: dict[str, Any]) -> ExecutionPlan:
        return plan

    state: dict[str, Any] = {}

    with patch(
        "agent_core.workflows.registry.get_critic_for_workflow",
        return_value=_AlwaysRetryCritic(),
    ):
        result_state = controller.execute(plan, state, replan_fn=replan_fn)

    log = result_state.get("_execution_log", [])
    event_types = [e["event"] for e in log]

    # Initial run + 1 retry (max_retries=1 means one retry allowed)
    assert event_types.count("step_start") == 2
    assert event_types.count("step_done") == 2
    assert event_types.count("critic_retry") == 2
    assert event_types.count("replan") == 1
    assert event_types.count("plan_complete") == 1

    # Verify retries_exhausted flag
    complete_entries = [e for e in log if e["event"] == "plan_complete"]
    assert len(complete_entries) == 1
    assert complete_entries[0].get("retries_exhausted") is True
    assert result_state.get("retry_count") == 1


def test_registry_critic_used_by_default():
    """ExecutionController should use the critic registered in workflows/registry.py."""
    _ensure_tmp_pdb()
    reg = _make_full_registry()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    workflow_registry = {"rna_tertiary_structure_design": wf}

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_tertiary_structure_design",
                input_binding={
                    "structure_filepath": _TMP_PDB_PATH,
                    "design_tools": "rhodesign",
                    "n_samples_per_tool": 2,
                },
                output_key="result",
            )
        ],
    )

    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry=workflow_registry,
    )
    state: dict[str, Any] = {"_llm_critic_enabled": False}
    result_state = controller.execute(plan, state)

    # With _llm_critic_enabled=False, the critic is bypassed and no retry occurs.
    log = result_state.get("_execution_log", [])
    event_types = [e["event"] for e in log]
    assert "critic_retry" not in event_types
    assert "plan_complete" in event_types
    assert result_state.get("retry_count") is None


def test_workflow_run_signature_has_progress_callback():
    """RnaTertiaryStructureDesignWorkflow.run() must accept progress_callback."""
    import inspect

    sig = inspect.signature(RnaTertiaryStructureDesignWorkflow.run)
    assert "progress_callback" in sig.parameters
    param = sig.parameters["progress_callback"]
    assert param.default is None
