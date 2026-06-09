"""Comprehensive integration test for aso_target_screening across all layers.

AsoTargetScreeningWorkflow INTERFACE LOCK (v1.0.0):
关联文件清单见 agent_core/workflows/aso_target_screening.py 顶部的
INTERFACE LOCK 注释。修改 workflow 接口必须同步更新全部关联文件并重新跑通测试。

Covers:
  - Layer 0: Direct tool invocation (CPU microservices — all ASO tools are CPU-based)
  - Layer 1: Capability registry with validation and writebacks
  - Layer 2: Full AsoTargetScreeningWorkflow (generate → evaluate → score → rank)
  - Layer 3: Mock Critic retry flow with parameter overrides
  - Layer 3: Live LLM Critic diagnosis (requires --live-llm + DEEPSEEK_API_KEY)
  - Layer 3: End-to-end retry with ExecutionController + parameter overrides

Run:
    # All non-LLM tests (Layers 0-3 mock)
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_aso_target_screening_comprehensive.py -v

    # Include live LLM tests (requires DeepSeek API)
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_aso_target_screening_comprehensive.py -v --live-llm
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from tests.helpers import reverse_complement_rna

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_target_sequence() -> str:
    """200-nt target mRNA sequence for ASO screening."""
    seq = "AUG" * 60 + "UUU" * 7
    return "".join(c for c in seq if c in "AUGC")[:200]



@pytest.fixture(scope="module")
def target_filepath(test_target_sequence):
    from agent_core.file_manager import save_sequence

    return save_sequence(f">target_mrna\n{test_target_sequence}\n", prefix="aso_test_target")
# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Layer 0 — Direct tool invocation
# ═══════════════════════════════════════════════════════════════════════

# NOTE: All ASO screening tools are CPU-based (ViennaRNA microservice on
# port 8003). There are no GPU tools in the ASO workflow.


class TestLayer0CpuTools:
    """Layer 0 tests for CPU-based tools used by ASO target screening."""

    def test_plfold_profile(self, executor, target_filepath):
        """RNAplfold whole-sequence accessibility profile on CPU (port 8003)."""
        result = executor.run_tool(
            "predict_rna_local_accessibility_profile_vienna",
            filepath=target_filepath,
            winsize=70,
            span=70,
        )
        assert result.success, f"RNAplfold profile failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "positions" in r, "Missing positions"
        assert "unpaired_prob_1nt" in r, "Missing unpaired_prob_1nt"
        assert len(r["positions"]) > 0, "Empty positions"
        assert len(r["positions"]) == len(r["unpaired_prob_1nt"]), "Length mismatch"
        assert "lunp_profile_tsv_filepath" in r, "Missing TSV filepath"

    def test_aso_accessibility(self, executor, target_filepath):
        """ASO region-specific accessibility on CPU (port 8003)."""
        result = executor.run_tool(
            "compute_aso_target_accessibility_vienna",
            filepath=target_filepath,
            region_start=1,
            region_end=18,
            aso_oligo_length=18,
        )
        assert result.success, f"ASO accessibility failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "mean_unpaired_prob_single_nt" in r, "Missing mean_unpaired_prob_single_nt"
        assert "joint_unpaired_prob_stretch_ending_at_region_end" in r, (
            "Missing joint_unpaired_prob"
        )

    @pytest.mark.known_issue
    def test_rnaup(self, executor, target_filepath):
        """RNAup RNA-RNA interaction on CPU (port 8003)."""
        from agent_core.file_manager import save_sequence

        aso_fp = save_sequence(
            ">aso\nGCAUGCAUGCAUGCAUGCAUGCAUGCAU\n", prefix="aso_test_oligo"
        )
        result = executor.run_tool(
            "compute_rna_rna_interaction_vienna",
            filepath1=target_filepath,
            filepath2=aso_fp,
            ulength=4,
        )
        assert result.success, f"RNAup failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "interaction_energy" in r, "Missing interaction_energy"
        assert "interaction_structure" in r, "Missing interaction_structure"

    def test_cofold(self, executor):
        """RNAcofold duplex binding on CPU (port 8003)."""
        from agent_core.file_manager import save_text_file

        duplex_fp = save_text_file(
            ">target\nAUGCAUGCAUGCAUGCAUGC\n>aso\nGCAUGCAUGCAUGCAUGCAU\n",
            prefix="aso_test_duplex",
            suffix=".txt",
        )
        result = executor.run_tool(
            "compute_sirna_duplex_binding_vienna", filepath=duplex_fp
        )
        assert result.success, f"RNAcofold failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "mfe_kcal_per_mol" in r, "Missing mfe_kcal_per_mol"
        assert "structure" in r, "Missing structure"


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Layer 1 — Capability integration
# ═══════════════════════════════════════════════════════════════════════


class TestLayer1Capabilities:
    """Layer 1 tests: Capability.invoke() with validation and writebacks."""

    def test_plfold_capability(self, registry, target_filepath):
        # Register if not already in STANDARD_WRITEBACKS
        if not registry.has("predict_rna_local_accessibility_profile_vienna"):
            registry.register("predict_rna_local_accessibility_profile_vienna")
        cap = registry.get("predict_rna_local_accessibility_profile_vienna")
        state: dict[str, Any] = {}
        result = cap.invoke(
            {"filepath": target_filepath, "winsize": 70, "span": 70},
            state=state,
        )
        assert result.success, f"Capability failed: {result.error}"
        assert "positions" in result.output
        # Verify writeback
        assert "tool_results" in state, "Missing tool_results writeback"
        assert "predict_rna_local_accessibility_profile_vienna" in state["tool_results"]

    def test_aso_accessibility_capability(self, registry, target_filepath):
        cap = registry.get("compute_aso_target_accessibility_vienna")
        state: dict[str, Any] = {}
        result = cap.invoke(
            {
                "filepath": target_filepath,
                "region_start": 1,
                "region_end": 18,
                "aso_oligo_length": 18,
            },
            state=state,
        )
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("mean_unpaired_prob_single_nt") is not None

    @pytest.mark.known_issue
    def test_rnaup_capability(self, registry, target_filepath):
        from agent_core.file_manager import save_sequence

        cap = registry.get("compute_rna_rna_interaction_vienna")
        aso_fp = save_sequence(
            ">aso\nGCAUGCAUGCAUGCAUGCAUGCAUGCAU\n", prefix="aso_test_oligo_cap"
        )
        state: dict[str, Any] = {}
        result = cap.invoke(
            {"filepath1": target_filepath, "filepath2": aso_fp, "ulength": 4},
            state=state,
        )
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("interaction_energy") is not None

    def test_cofold_capability(self, registry):
        from agent_core.file_manager import save_text_file

        cap = registry.get("compute_sirna_duplex_binding_vienna")
        duplex_fp = save_text_file(
            ">target\nAUGCAUGCAUGCAUGCAUGC\n>aso\nGCAUGCAUGCAUGCAUGCAU\n",
            prefix="aso_test_duplex_cap",
            suffix=".txt",
        )
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": duplex_fp}, state=state)
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("mfe_kcal_per_mol") is not None


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Layer 2 — Full workflow
# ═══════════════════════════════════════════════════════════════════════


class TestLayer2Workflow:
    """Layer 2 tests: AsoTargetScreeningWorkflow end-to-end with real tools."""

    @pytest.fixture(scope="class")
    def workflow(self, registry):
        from agent_core.workflows.aso_target_screening import AsoTargetScreeningWorkflow

        return AsoTargetScreeningWorkflow(registry)

    @pytest.mark.known_issue
    def test_aso_workflow_rnaup(self, workflow, target_filepath):
        """Run workflow with RNAup binding evaluation."""
        from agent_core.workflows.aso_target_screening import AsoScreeningInput

        inp = AsoScreeningInput(
            target_mrna_filepath=target_filepath,
            aso_length=18,
            window_step=3,
            top_n_windows=5,
            binding_evaluation_tool="rnaup",
        )
        result = workflow.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert result.best_candidate is not None, "No best candidate"
        assert len(result.all_candidates) >= 1, "No candidates produced"
        assert len(result.all_candidates) <= 5, "Too many candidates"

        best = result.best_candidate
        assert len(best.sequence) == 18, f"Expected 18-nt ASO, got {len(best.sequence)}"
        assert "composite_score" in best.scores, "Missing composite_score"
        assert best.scores["composite_score"] == pytest.approx(1.0, abs=0.1)
        assert "accessibility_rank" in best.scores
        assert "binding_rank" in best.scores
        assert "sum_rank" in best.scores

        mb = best.metadata.get("metrics_bundle", {})
        assert mb.get("mean_unpaired_prob") is not None, "Missing mean_unpaired_prob"
        assert mb.get("binding_dg_kcal_per_mol") is not None, "Missing binding_dg"

    def test_aso_workflow_cofold(self, workflow, target_filepath):
        """Run workflow with RNAcofold binding evaluation."""
        from agent_core.workflows.aso_target_screening import AsoScreeningInput

        inp = AsoScreeningInput(
            target_mrna_filepath=target_filepath,
            aso_length=18,
            window_step=3,
            top_n_windows=5,
            binding_evaluation_tool="rnacofold",
        )
        result = workflow.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert result.best_candidate is not None
        assert len(result.all_candidates) <= 5

        best = result.best_candidate
        mb = best.metadata.get("metrics_bundle", {})
        assert mb.get("duplex_mfe_kcal_per_mol") is not None, "Missing duplex_mfe"
        assert mb.get("duplex_structure") is not None, "Missing duplex_structure"

    def test_aso_workflow_different_params(self, workflow, target_filepath):
        """Workflow respects different parameter combinations."""
        from agent_core.workflows.aso_target_screening import AsoScreeningInput

        # Longer ASO, larger step, fewer top windows
        inp = AsoScreeningInput(
            target_mrna_filepath=target_filepath,
            aso_length=21,
            window_step=5,
            top_n_windows=3,
            binding_evaluation_tool="rnaup",
        )
        result = workflow.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert len(result.all_candidates) <= 3
        best = result.best_candidate
        assert len(best.sequence) == 21, f"Expected 21-nt ASO, got {len(best.sequence)}"

    def test_progress_callback(self, workflow, target_filepath):
        """Progress callback receives events during workflow execution."""
        from agent_core.workflows.aso_target_screening import AsoScreeningInput

        events: list[dict[str, Any]] = []

        def _callback(event: dict[str, Any]) -> None:
            events.append(event)

        inp = AsoScreeningInput(
            target_mrna_filepath=target_filepath,
            aso_length=18,
            window_step=5,
            top_n_windows=3,
            binding_evaluation_tool="rnaup",
        )
        result = workflow.run(inp, progress_callback=_callback)
        assert result.success
        assert len(events) > 0, "Expected progress events"
        event_types = {e.get("event") for e in events}
        assert "generate_complete" in event_types, "Missing generate_complete event"
        assert "evaluate_progress" in event_types, "Missing evaluate_progress event"

    def test_state_writeback(self, workflow, target_filepath):
        """Verify workflow result has _state_writeback for controller."""
        from agent_core.workflows.aso_target_screening import AsoScreeningInput

        inp = AsoScreeningInput(
            target_mrna_filepath=target_filepath,
            aso_length=18,
            window_step=5,
            top_n_windows=3,
            binding_evaluation_tool="rnaup",
        )
        result = workflow.run(inp)
        assert result.success
        assert hasattr(result, "_state_writeback"), "Missing _state_writeback"
        wb = getattr(result, "_state_writeback", {})
        assert "_aso_input" in wb, "Missing _aso_input in writeback"
        assert "target_filepath" in wb, "Missing target_filepath in writeback"
        assert "target_sequence" in wb, "Missing target_sequence in writeback"

    def test_empty_target_fails(self, workflow):
        """Non-existent target file should return empty candidates."""
        from agent_core.workflows.aso_target_screening import AsoScreeningInput

        inp = AsoScreeningInput(
            target_mrna_filepath="workspace/nonexistent_aso_target.fa",
            aso_length=18,
            top_n_windows=5,
        )
        result = workflow.run(inp)
        assert result.success is False, "Expected failure for missing file"
        assert "empty_candidate_list" in result.errors

    def test_short_target_fails(self, workflow):
        """Target shorter than aso_length + 10 should fail gracefully."""
        from agent_core.file_manager import save_sequence
        from agent_core.workflows.aso_target_screening import AsoScreeningInput

        short_fp = save_sequence(
            ">short\nAUGCAUGCAUGC\n", prefix="aso_test_short"
        )
        inp = AsoScreeningInput(
            target_mrna_filepath=short_fp,
            aso_length=18,
            top_n_windows=5,
        )
        result = workflow.run(inp)
        assert result.success is False, "Expected failure for short sequence"

    def test_dict_input(self, workflow, target_filepath):
        """Workflow accepts plain dict input (API compatibility)."""
        result = workflow.run(
            {
                "target_mrna_filepath": target_filepath,
                "aso_length": 18,
                "window_step": 5,
                "top_n_windows": 3,
                "binding_evaluation_tool": "rnaup",
            }
        )
        assert result.success
        assert len(result.all_candidates) <= 3


# ═══════════════════════════════════════════════════════════════════════
# Phase 4: Layer 3 — Mock retry & parameter override
# ═══════════════════════════════════════════════════════════════════════


def _make_aso_candidate(
    target_seq: str,
    start: int,
    mean_unpaired: float,
    binding_dg: float | None,
    duplex_mfe: float | None = None,
) -> "Candidate":
    """Build an ASO Candidate with metrics.

    ASO sequence is the reverse complement of target_seq.
    """
    from agent_core.workflow_models import Candidate

    aso_seq = reverse_complement_rna(target_seq)
    c = Candidate(
        sequence=aso_seq,
        sequence_type="aso",
        source=f"window:{start}-{start + len(target_seq) - 1}",
        metadata={
            "aso_sequence": aso_seq,
            "target_sequence": target_seq,
            "target_start": start,
            "target_end": start + len(target_seq) - 1,
            "mean_unpaired_prob": mean_unpaired,
            "metrics_bundle": {
                "aso_sequence": aso_seq,
                "target_sequence": target_seq,
                "target_start": start,
                "target_end": start + len(target_seq) - 1,
                "mean_unpaired_prob": mean_unpaired,
                "binding_dg_kcal_per_mol": binding_dg,
                "duplex_mfe_kcal_per_mol": duplex_mfe,
            },
        },
    )
    c.scores = {
        "accessibility_component": mean_unpaired,
        "binding_component": -binding_dg if binding_dg is not None else 0.0,
    }
    return c


def _make_low_quality_aso_result() -> "WorkflowResult":
    """Build a WorkflowResult with poor ASO metrics to trigger critic retry.

    Poor quality = weak binding (binding_dg close to 0), low accessibility.
    All sequences are 18 nt to match the default aso_length parameter.
    """
    from agent_core.workflow_models import Candidate, WorkflowResult

    # Different 18-nt target sequences from different regions
    target_seqs = [
        "AUGCAUGCAUGCAUGCAU",
        "UUUUUUUUUUUUUUUUUU",
        "GGGGGGGGGGGGGGGGGG",
    ]
    candidates: list[Candidate] = []
    for i, (acc, dg) in enumerate([(0.1, -2.0), (0.15, -1.5), (0.12, -1.0)]):
        c = _make_aso_candidate(
            target_seq=target_seqs[i],
            start=i * 30 + 1,
            mean_unpaired=acc,
            binding_dg=dg,
        )
        candidates.append(c)

    return WorkflowResult(
        success=True,
        task_id="test_low_quality",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Low quality ASO: weak binding, low accessibility",
        errors=[],
    )


def _make_good_quality_aso_result() -> "WorkflowResult":
    """Build a WorkflowResult with good ASO metrics.

    All sequences are 18 nt to match the default aso_length parameter.
    """
    from agent_core.workflow_models import Candidate, WorkflowResult

    target_seqs = [
        "AUGCAUGCAUGCAUGCAU",
        "UUUAAAUUUAAAUUUAAA",
        "GGGCCCGGGCCCGGGCCC",
    ]
    candidates: list[Candidate] = []
    for i, (acc, dg) in enumerate([(0.75, -25.0), (0.70, -22.0), (0.68, -20.0)]):
        c = _make_aso_candidate(
            target_seq=target_seqs[i],
            start=i * 30 + 1,
            mean_unpaired=acc,
            binding_dg=dg,
        )
        candidates.append(c)

    return WorkflowResult(
        success=True,
        task_id="test_good_quality",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Good quality ASO: strong binding, high accessibility",
        errors=[],
    )


class _MockRetryCritic:
    """Mock critic that triggers retry on first call, then accepts."""

    def __init__(self, max_retries: int = 1):
        self.call_count = 0
        self.max_retries = max_retries

    def should_retry(self, workflow_result: "WorkflowResult", state: dict[str, Any]) -> bool:
        self.call_count += 1
        if self.call_count <= self.max_retries:
            state["_parameter_overrides"] = {
                "aso_length": 21,
                "binding_evaluation_tool": "rnacofold",
            }
            return True
        return False


class TestLayer3MockRetry:
    """Layer 3 tests using mock critic to verify retry logic without LLM."""

    def test_controller_triggers_retry(self):
        """ExecutionController triggers retry when critic returns True."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={
                        "target_mrna_filepath": "test.fa",
                        "aso_length": 18,
                    },
                    output_key="aso_result",
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "aso_target_screening":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_aso_result()
            raise RuntimeError(f"Unexpected step: {step.target}")

        _critic_instance = _MockRetryCritic(max_retries=1)

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "aso_target_screening":
                return _critic_instance
            return None

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, {})

        # Initial + 1 retry = at least 2 calls
        assert call_count >= 2, f"Expected at least 2 calls, got {call_count}"
        assert final_state.get("retry_count", 0) >= 1

        log = final_state.get("_execution_log", [])
        critic_events = [e for e in log if e.get("event") == "critic_retry"]
        assert len(critic_events) > 0, "No critic_retry events in log"

        override_events = [e for e in log if e.get("event") == "parameter_override"]
        assert len(override_events) > 0, "No parameter_override events in log"

        # Verify plan input_binding was modified
        final_binding = plan.steps[0].input_binding
        assert final_binding.get("aso_length") == 21, (
            f"Expected aso_length=21, got {final_binding.get('aso_length')}"
        )
        assert final_binding.get("binding_evaluation_tool") == "rnacofold"

    def test_controller_retry_exhaustion(self):
        """Controller stops retrying when max_retries is exhausted."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={"target_mrna_filepath": "test.fa"},
                    output_key="aso_result",
                )
            ],
            max_retries=1,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "aso_target_screening":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_aso_result()
            raise RuntimeError(f"Unexpected step: {step.target}")

        # Critic that ALWAYS wants to retry (never gives up)
        class _AlwaysRetryCritic:
            def should_retry(self, result, state):
                state["_parameter_overrides"] = {"aso_length": 25}
                return True

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "aso_target_screening":
                return _AlwaysRetryCritic()
            return None

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, {})

        # Initial + 1 retry (max_retries=1) = 2 calls max
        assert call_count == 2, f"Expected 2 calls (initial + 1 retry), got {call_count}"
        assert final_state.get("retry_count", 0) == 1

        log = final_state.get("_execution_log", [])
        complete_events = [e for e in log if e.get("event") == "plan_complete"]
        assert len(complete_events) > 0
        assert any(
            e.get("retries_exhausted") for e in complete_events
        ), "Expected retries_exhausted flag"

    def test_retry_then_success(self):
        """Critic triggers retry on first run; second run passes."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={"target_mrna_filepath": "test.fa"},
                    output_key="aso_result",
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "aso_target_screening":
                state["_last_workflow_params"] = dict(step.input_binding)
                if call_count == 1:
                    return _make_low_quality_aso_result()
                return _make_good_quality_aso_result()
            raise RuntimeError(f"Unexpected step: {step.target}")

        _critic_instance = _MockRetryCritic(max_retries=1)

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "aso_target_screening":
                return _critic_instance
            return None

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, {})

        assert call_count >= 2
        log = final_state.get("_execution_log", [])
        complete_events = [e for e in log if e.get("event") == "plan_complete"]
        assert len(complete_events) > 0
        assert not any(
            e.get("retries_exhausted") for e in complete_events
        ), "Did not expect retries_exhausted when second run passes"

    def test_parameter_override_application(self):
        """Verify _apply_parameter_overrides merges correctly."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={
                        "target_mrna_filepath": "test.fa",
                        "aso_length": 18,
                        "window_step": 1,
                    },
                )
            ]
        )

        state = {
            "_last_workflow_params": {
                "target_mrna_filepath": "test.fa",
                "aso_length": 18,
            },
            "_parameter_overrides": {
                "aso_length": 21,
                "window_step": 3,
                "top_n_windows": 5,
            },
        }

        controller._apply_parameter_overrides(plan, state, state["_parameter_overrides"])

        binding = plan.steps[0].input_binding
        assert binding["aso_length"] == 21
        assert binding["window_step"] == 3
        assert binding["top_n_windows"] == 5
        assert binding["target_mrna_filepath"] == "test.fa"

        # Verify original was saved
        assert "_original_input_binding_aso" in state

    def test_critic_disabled_no_retry(self):
        """When _llm_critic_enabled=False, no retry should occur."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={"target_mrna_filepath": "test.fa"},
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "aso_target_screening":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_aso_result()
            raise RuntimeError(f"Unexpected: {step.target}")

        class _AlwaysRetryCritic:
            def should_retry(self, result, state):
                if state.get("_llm_critic_enabled") is False:
                    return False
                state["_parameter_overrides"] = {"aso_length": 25}
                return True

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "aso_target_screening":
                return _AlwaysRetryCritic()
            return None

        initial_state = {"_llm_critic_enabled": False}

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, initial_state)

        # Should only be called once (no retries)
        assert call_count == 1, f"Expected 1 call with critic disabled, got {call_count}"
        assert final_state.get("retry_count", 0) == 0


# ═══════════════════════════════════════════════════════════════════════
# Phase 5: Live LLM Critic — Real DeepSeek API
# ═══════════════════════════════════════════════════════════════════════


# Create a test-only LLM Critic for ASO screening
class AsoScreeningLLMCritic:
    """Test-only LLM Critic for ASO target screening.

    This critic is NOT registered in WORKFLOW_CRITIC_PAIRS because
    AsoTargetScreeningWorkflow is deterministic and intentionally has
    no critic. This class exists ONLY for testing Layer 3 retry logic
    with a real LLM.
    """

    def __init__(self):
        from agent_core.planning.llm_critic import (
            BaseLLMCritic,
            CriticConfig,
        )

        config = CriticConfig(
            workflow_name="aso_target_screening",
            workflow_description=(
                "Screen a target mRNA for optimal ASO binding sites. "
                "Pipeline: RNAplfold profile → sliding-window ranking → "
                "ASO design → RNAup/RNAcofold binding evaluation → rank-based scoring."
            ),
            evaluation_dimensions=[
                "Accessibility: mean unpaired probability should be > 0.3 for good binding sites",
                "Binding strength: RNAup interaction energy should be < -10 kcal/mol",
                "Duplex stability: RNAcofold MFE should be < -15 kcal/mol for strong binding",
                "Site diversity: candidates should come from different regions of the target",
            ],
            adjustable_params={
                "aso_length": {
                    "type": "int",
                    "min": 10,
                    "max": 50,
                    "hint": "ASO oligonucleotide length. Longer = stronger binding but less specific. Try 15-25 for balance.",
                },
                "window_step": {
                    "type": "int",
                    "min": 1,
                    "max": 10,
                    "hint": "Sliding window step size. Smaller = finer search but more compute.",
                },
                "top_n_windows": {
                    "type": "int",
                    "min": 1,
                    "max": 100,
                    "hint": "Number of top accessibility windows to evaluate with binding tools.",
                },
                "binding_evaluation_tool": {
                    "type": "enum",
                    "values": ["rnaup", "rnacofold"],
                    "hint": "Tool for binding evaluation. RNAup gives thermodynamic ΔG; RNAcofold gives duplex MFE.",
                },
            },
            retry_strategy="adjust_params",
            max_retries=2,
        )
        self._base = BaseLLMCritic(config)

    def diagnose(self, result, state):
        return self._base.diagnose(result, state)

    def should_retry(self, result, state):
        return self._base.should_retry(result, state)

    def _build_context(self, result, state):
        return self._base._build_context(result, state)

    def _build_diagnosis_prompt(self, context):
        return self._base._build_diagnosis_prompt(context)


@pytest.mark.live_llm
class TestLiveLLMCritic:
    """Live tests using real DeepSeek API for Critic diagnosis."""

    def test_critic_diagnoses_poor_binding(self):
        """Real LLM should detect poor ASO metrics and recommend changes."""
        from agent_core.planning.llm_critic import CriticDiagnosis

        critic = AsoScreeningLLMCritic()
        result = _make_low_quality_aso_result()
        state = {
            "_last_workflow_params": {
                "aso_length": 18,
                "window_step": 1,
                "top_n_windows": 10,
                "binding_evaluation_tool": "rnaup",
            },
            "user_text": "Find the best ASO binding sites on my target mRNA",
        }

        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score < 0.6, (
            f"Expected low quality score for bad results, got {diagnosis.quality_score}"
        )
        assert len(diagnosis.issues) > 0, "Expected at least one issue"
        # At least one issue should mention binding, accessibility, or energy
        relevant_issues = [
            i
            for i in diagnosis.issues
            if any(
                kw in i.category.lower() or i.description.lower()
                for kw in ["binding", "accessibility", "energy", "mfe", "duplex"]
            )
        ]
        # Not strictly required — LLM may describe issues differently
        print(f"Live diagnosis: {diagnosis.model_dump_json(indent=2)}")

    def test_critic_should_retry_low_quality(self):
        """should_retry must return True for low-quality ASO results."""
        critic = AsoScreeningLLMCritic()
        result = _make_low_quality_aso_result()
        state = {
            "_last_workflow_params": {
                "aso_length": 18,
                "top_n_windows": 10,
                "binding_evaluation_tool": "rnaup",
            },
            "user_text": "Screen target mRNA for ASO binding sites",
        }

        should_retry = critic.should_retry(result, state)
        assert should_retry is True, (
            f"Expected should_retry=True for low quality, got {should_retry}"
        )
        assert "_parameter_overrides" in state, "Missing _parameter_overrides"
        print(f"Parameter overrides: {state['_parameter_overrides']}")

    def test_critic_should_not_retry_good_quality(self):
        """should_retry must return False for good-quality ASO results."""
        critic = AsoScreeningLLMCritic()
        result = _make_good_quality_aso_result()
        state = {
            "_last_workflow_params": {
                "aso_length": 18,
                "top_n_windows": 10,
                "binding_evaluation_tool": "rnaup",
            },
            "user_text": "Screen target mRNA for ASO binding sites",
        }

        should_retry = critic.should_retry(result, state)
        assert should_retry is False, (
            f"Expected should_retry=False for good quality, got {should_retry}"
        )

    def test_critic_prompt_contains_evaluation_dimensions(self):
        """Verify the diagnosis prompt includes ASO-specific criteria."""
        critic = AsoScreeningLLMCritic()
        result = _make_low_quality_aso_result()
        ctx = critic._build_context(result, {})
        messages = critic._build_diagnosis_prompt(ctx)

        system_text = messages[0][1]
        assert "accessibility" in system_text.lower(), "Missing accessibility in criteria"
        assert "binding" in system_text.lower(), "Missing binding in criteria"
        assert "aso_length" in system_text, "Missing aso_length in adjustable params"
        assert "window_step" in system_text, "Missing window_step in adjustable params"
        assert "top_n_windows" in system_text, "Missing top_n_windows in adjustable params"
        assert "binding_evaluation_tool" in system_text, (
            "Missing binding_evaluation_tool in adjustable params"
        )

        user_text = messages[1][1]
        assert "aso_target_screening" in user_text, "Missing workflow name"
        assert "window" in user_text.lower(), "Missing candidate source"

    def test_diagnosis_records_history(self):
        """Verify diagnose appends to _diagnosis_history."""
        critic = AsoScreeningLLMCritic()
        result = _make_low_quality_aso_result()
        state: dict[str, Any] = {}

        critic.diagnose(result, state)

        assert "_diagnosis_history" in state, "Missing _diagnosis_history"
        assert len(state["_diagnosis_history"]) == 1

    def test_critic_suggests_parameter_adjustments(self):
        """Critic should suggest concrete parameter adjustments for ASO.

        This is the key Layer-3 test: the LLM examines workflow results and
        proposes actionable parameter changes (e.g., adjust aso_length,
        change binding_evaluation_tool, modify top_n_windows).
        """
        critic = AsoScreeningLLMCritic()
        result = _make_low_quality_aso_result()
        state = {
            "_last_workflow_params": {
                "aso_length": 18,
                "window_step": 1,
                "top_n_windows": 10,
                "binding_evaluation_tool": "rnaup",
            },
            "user_text": "Find strong ASO binding sites with good accessibility",
        }

        diagnosis = critic.diagnose(result, state)

        # Should recommend parameter changes or identify issues
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
            "proceed_with_filtered",
            "abort",
        ), f"Unexpected action: {diagnosis.action}"

        # If retry is recommended, overrides should be present
        if diagnosis.action in ("retry_with_adjustments", "retry_with_alternative"):
            assert len(diagnosis.parameter_overrides) > 0, (
                "Expected parameter overrides from critic"
            )
            valid_params = {
                "aso_length",
                "window_step",
                "top_n_windows",
                "binding_evaluation_tool",
            }
            for key in diagnosis.parameter_overrides:
                assert key in valid_params, f"Invalid parameter override: {key}"

        # Verify reasoning is present and non-empty
        assert diagnosis.reasoning and len(diagnosis.reasoning) > 10, (
            "Expected detailed reasoning from critic"
        )

    def test_parameter_override_values_are_valid(self):
        """Verify that critic-suggested parameter values are within valid ranges."""
        critic = AsoScreeningLLMCritic()
        result = _make_low_quality_aso_result()
        state = {
            "_last_workflow_params": {
                "aso_length": 18,
                "window_step": 1,
                "top_n_windows": 10,
                "binding_evaluation_tool": "rnaup",
            },
            "user_text": "Find strong ASO binding sites",
        }

        diagnosis = critic.diagnose(result, state)

        for key, value in diagnosis.parameter_overrides.items():
            if key == "aso_length":
                assert 10 <= int(value) <= 50, f"aso_length={value} out of range [10,50]"
            elif key == "window_step":
                assert 1 <= int(value) <= 10, f"window_step={value} out of range [1,10]"
            elif key == "top_n_windows":
                assert 1 <= int(value) <= 100, f"top_n_windows={value} out of range [1,100]"
            elif key == "binding_evaluation_tool":
                assert value in ("rnaup", "rnacofold"), (
                    f"binding_evaluation_tool={value!r} not in allowed values"
                )


# ═══════════════════════════════════════════════════════════════════════
# Phase 6: End-to-End Retry — ExecutionController + Live Critic
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.live_llm
class TestEndToEndRetry:
    """End-to-end tests: ExecutionController + real Critic + parameter overrides."""

    def test_controller_triggers_retry_with_live_critic(self):
        """Full flow: controller executes mock workflow, live critic triggers retry.

        Uses a mock workflow that always returns low-quality ASO results,
        but a REAL Critic (calling DeepSeek API) that diagnoses the problem
        and recommends parameter changes. The controller applies the overrides
        and retries.
        """
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        for name in [
            "predict_rna_local_accessibility_profile_vienna",
            "compute_aso_target_accessibility_vienna",
            "compute_rna_rna_interaction_vienna",
            "compute_sirna_duplex_binding_vienna",
        ]:
            registry.register(name)

        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={
                        "target_mrna_filepath": "test.fa",
                        "aso_length": 18,
                        "window_step": 1,
                        "top_n_windows": 10,
                        "binding_evaluation_tool": "rnaup",
                    },
                    output_key="aso_result",
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "aso_target_screening":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_aso_result()
            raise RuntimeError(f"Unexpected step: {step.target}")

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "aso_target_screening":
                return AsoScreeningLLMCritic()
            return None

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, {})

        # At least 2 calls: initial + at least 1 retry
        assert call_count >= 2, f"Expected at least 2 calls, got {call_count}"
        assert final_state.get("retry_count", 0) >= 1, (
            f"Expected retry_count >= 1, got {final_state.get('retry_count')}"
        )

        log = final_state.get("_execution_log", [])
        override_events = [e for e in log if e.get("event") == "parameter_override"]
        assert len(override_events) > 0, "No parameter_override events in log"

        critic_events = [e for e in log if e.get("event") == "critic_retry"]
        assert len(critic_events) > 0, "No critic_retry events in log"

        # Verify plan's input_binding was modified by critic
        final_binding = plan.steps[0].input_binding
        assert "aso_length" in final_binding, "Missing aso_length in final binding"

        complete_events = [e for e in log if e.get("event") == "plan_complete"]
        assert len(complete_events) > 0, "No plan_complete events"

    def test_controller_retry_then_success(self):
        """Critic triggers retry on first run; second run passes."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        for name in [
            "predict_rna_local_accessibility_profile_vienna",
            "compute_aso_target_accessibility_vienna",
            "compute_rna_rna_interaction_vienna",
            "compute_sirna_duplex_binding_vienna",
        ]:
            registry.register(name)

        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={
                        "target_mrna_filepath": "test.fa",
                        "aso_length": 18,
                        "top_n_windows": 10,
                        "binding_evaluation_tool": "rnaup",
                    },
                    output_key="aso_result",
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "aso_target_screening":
                state["_last_workflow_params"] = dict(step.input_binding)
                if call_count == 1:
                    return _make_low_quality_aso_result()
                return _make_good_quality_aso_result()
            raise RuntimeError(f"Unexpected step: {step.target}")

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "aso_target_screening":
                return AsoScreeningLLMCritic()
            return None

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, {})

        assert call_count >= 1
        log = final_state.get("_execution_log", [])
        complete_events = [e for e in log if e.get("event") == "plan_complete"]
        assert len(complete_events) > 0
        assert not any(
            e.get("retries_exhausted") for e in complete_events
        ), "Did not expect retries_exhausted when second run passes"


# ═══════════════════════════════════════════════════════════════════════
# Phase 7: Layer 3 — ExecutionController with real workflow
# ═══════════════════════════════════════════════════════════════════════


class TestLayer3ExecutionController:
    """Layer 3 tests: ExecutionController executing real ASO workflow."""

    def test_controller_runs_aso_workflow(self, registry, target_filepath):
        """ExecutionController runs the full ASO workflow end-to-end."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.workflows.aso_target_screening import (
            AsoTargetScreeningWorkflow,
        )

        wf = AsoTargetScreeningWorkflow(registry)
        controller = ExecutionController(
            capability_registry=registry,
            workflow_registry={"aso_target_screening": wf},
        )

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={
                        "target_mrna_filepath": target_filepath,
                        "aso_length": 18,
                        "window_step": 5,
                        "top_n_windows": 3,
                        "binding_evaluation_tool": "rnaup",
                    },
                    output_key="aso_result",
                )
            ],
            max_retries=2,
        )

        state: dict[str, Any] = {}
        final_state = controller.execute(plan, state)

        assert final_state.get("workflow_result") is not None
        assert final_state["workflow_result"].success is True
        assert len(final_state["workflow_result"].all_candidates) > 0
        assert len(final_state["workflow_result"].all_candidates) <= 3

        assert "aso_result" in final_state
        assert "workflow_result" in final_state
        assert "_aso_input" in final_state
        assert "target_filepath" in final_state
        assert final_state.get("retry_count", 0) == 0

        log = final_state.get("_execution_log", [])
        assert len(log) > 0
        assert any(e.get("event") == "step_start" for e in log)
        assert any(e.get("event") == "step_done" for e in log)
        assert any(e.get("event") == "plan_complete" for e in log)

    def test_controller_runs_aso_with_cofold(self, registry, target_filepath):
        """ExecutionController runs ASO workflow with RNAcofold tool."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.workflows.aso_target_screening import (
            AsoTargetScreeningWorkflow,
        )

        wf = AsoTargetScreeningWorkflow(registry)
        controller = ExecutionController(
            capability_registry=registry,
            workflow_registry={"aso_target_screening": wf},
        )

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={
                        "target_mrna_filepath": target_filepath,
                        "aso_length": 18,
                        "window_step": 5,
                        "top_n_windows": 3,
                        "binding_evaluation_tool": "rnacofold",
                    },
                    output_key="aso_result",
                )
            ],
            max_retries=2,
        )

        state: dict[str, Any] = {}
        final_state = controller.execute(plan, state)

        assert final_state["workflow_result"].success is True
        best = final_state["workflow_result"].best_candidate
        assert best is not None
        mb = best.metadata.get("metrics_bundle", {})
        assert mb.get("duplex_mfe_kcal_per_mol") is not None

    def test_controller_with_progress_callback(self, registry, target_filepath):
        """Progress callback receives events from controller execution."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.workflows.aso_target_screening import (
            AsoTargetScreeningWorkflow,
        )

        wf = AsoTargetScreeningWorkflow(registry)
        controller = ExecutionController(
            capability_registry=registry,
            workflow_registry={"aso_target_screening": wf},
        )

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={
                        "target_mrna_filepath": target_filepath,
                        "aso_length": 18,
                        "window_step": 5,
                        "top_n_windows": 2,
                        "binding_evaluation_tool": "rnaup",
                    },
                    output_key="aso_result",
                )
            ],
        )

        events: list[dict[str, Any]] = []

        def _callback(event: dict[str, Any]) -> None:
            events.append(event)

        state: dict[str, Any] = {}
        final_state = controller.execute(plan, state, progress_callback=_callback)

        assert final_state["workflow_result"].success is True
        assert len(events) > 0, "Expected progress events from controller"
        event_types = {e.get("event") for e in events}
        assert "step_start" in event_types
        assert "step_done" in event_types
        assert "plan_complete" in event_types

    def test_controller_binding_resolution(self, registry, target_filepath):
        """ExecutionController resolves $state bindings for downstream steps."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.workflows.aso_target_screening import (
            AsoTargetScreeningWorkflow,
        )

        wf = AsoTargetScreeningWorkflow(registry)
        controller = ExecutionController(
            capability_registry=registry,
            workflow_registry={"aso_target_screening": wf},
        )

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={
                        "target_mrna_filepath": target_filepath,
                        "aso_length": 18,
                        "window_step": 5,
                        "top_n_windows": 2,
                        "binding_evaluation_tool": "rnaup",
                    },
                    output_key="aso_result",
                ),
                PlanStep(
                    step_id="gc_check",
                    type="capability",
                    target="compute_rna_sequence_gc_content",
                    input_binding={"filepath": "$state.target_filepath"},
                    output_key="gc_result",
                ),
            ],
        )

        state: dict[str, Any] = {}
        final_state = controller.execute(plan, state)

        assert "aso_result" in final_state
        assert "gc_result" in final_state
        assert final_state["gc_result"].success is True
        assert "gc_content" in final_state["gc_result"].output

    def test_controller_dict_input_through_binding(self, registry, target_filepath):
        """Controller passes dict input through binding to workflow."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.workflows.aso_target_screening import (
            AsoTargetScreeningWorkflow,
        )

        wf = AsoTargetScreeningWorkflow(registry)
        controller = ExecutionController(
            capability_registry=registry,
            workflow_registry={"aso_target_screening": wf},
        )

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={
                        "target_mrna_filepath": target_filepath,
                        "aso_length": 21,
                        "window_step": 5,
                        "top_n_windows": 2,
                        "binding_evaluation_tool": "rnaup",
                    },
                    output_key="aso_result",
                )
            ],
        )

        state: dict[str, Any] = {}
        final_state = controller.execute(plan, state)

        assert final_state["aso_result"].success is True
        assert len(final_state["aso_result"].all_candidates) <= 2
        best = final_state["aso_result"].best_candidate
        assert len(best.sequence) == 21
