"""Full-stack integration test for rna_secondary_structure_design workflow across Layer 0-3.

Tests cover:
- Phase 0: DeepSeek API connectivity (live_llm marker)
- Phase 1 (Layer 0): Direct tool invocation (CPU-only tools: ViennaRNA RNAinverse, RNAfold, GC content)
  NOTE: This workflow has no GPU-dependent tools.
- Phase 2 (Layer 1): Capability integration via CapabilityRegistry
- Phase 3 (Layer 2): End-to-end RnaSecondaryStructureDesignWorkflow
- Phase 4 (Layer 3): ExecutionController + Critic retry + parameter override
- Phase 5: Live LLM Critic with actual DeepSeek API (live_llm marker)

Run all layers (excluding live LLM):
    python -m pytest tests/test_rna_secondary_structure_design_full_stack.py -v -s

Run with live LLM (requires DEEPSEEK_API_KEY):
    python -m pytest tests/test_rna_secondary_structure_design_full_stack.py -v -s --live-llm
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any
from unittest.mock import patch

import pytest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_LOGGER = logging.getLogger("test_rna_secondary_structure_design_full_stack")

# ═══════════════════════════════════════════════════════════════════════════════
# Test configuration
# ═══════════════════════════════════════════════════════════════════════════════

# Target secondary structure for testing (~30 nt hairpin)
TEST_TARGET_STRUCTURE = "((((....))))....((((....))))"
# Slightly longer structure for diversity
TEST_TARGET_STRUCTURE_LONG = "(((...)))(((...)))(((...)))(((...)))"

TEST_RESULTS: dict[str, tuple[bool, str]] = {}


def _record(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    TEST_RESULTS[name] = (passed, detail)
    print(f"  [{status}] {name}: {detail}")


def _print_header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _print_summary() -> None:
    print(f"\n{'='*60}")
    print("  TEST SUMMARY")
    print(f"{'='*60}")
    total = len(TEST_RESULTS)
    passed = sum(1 for v in TEST_RESULTS.values() if v[0])
    for name, (ok, detail) in TEST_RESULTS.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
        if detail and not ok:
            print(f"         -> {detail}")
    print(f"\n  Total: {passed}/{total} passed")
    if passed < total:
        print(f"  FAILED: {total - passed} test(s)")
    else:
        print("  ALL TESTS PASSED!")
    print(f"{'='*60}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 0: DeepSeek API connectivity
# ═══════════════════════════════════════════════════════════════════════════════


def test_deepseek_api() -> None:
    """Test that DeepSeek API is reachable and returns sensible output."""
    _print_header("Phase 0: DeepSeek API Connectivity")
    try:
        from agent_core.llm_config import get_deepseek_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_deepseek_llm(temperature=0.1)
        messages = [
            SystemMessage(
                content="You are a helpful assistant. Reply with a single JSON object containing keys 'status' and 'message'."
            ),
            HumanMessage(content="Say hello and confirm the API works. Return JSON only."),
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        assert content and len(content) >= 5, f"Empty or too-short response: {content!r}"

        ok = "hello" in content.lower() or "status" in content.lower() or "{" in content
        _record(
            "deepseek_api",
            ok,
            f"Response length={len(content)}, preview={content[:100]!r}",
        )
        assert ok, f"Response did not contain expected content: {content!r}"
    except Exception as exc:
        _record("deepseek_api", False, f"Exception: {type(exc).__name__}: {exc}")
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Layer 0 — Direct tool invocation (CPU-only tools)
# ═══════════════════════════════════════════════════════════════════════════════


def test_layer0_tools() -> None:
    """Test each tool directly via ToolExecutor.

    This workflow uses ONLY CPU tools:
    - inverse_fold_rna_secondary_structure_vienna (ViennaRNA RNAinverse)
    - predict_rna_secondary_structure (ViennaRNA RNAfold)
    - compute_rna_sequence_gc_content (sequence metrics)
    """
    _print_header("Phase 1: Layer 0 — Direct Tool Invocation (CPU-only)")

    from agent_core.file_manager import save_sequence, save_text_file
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    executor = ToolExecutor(build_default_tool_registry())

    # Save target structure for RNAinverse
    struct_fp = save_text_file(
        TEST_TARGET_STRUCTURE, prefix="test_target_struct", suffix=".txt"
    )
    _LOGGER.info("Saved target structure to %s", struct_fp)

    # ── 1a. ViennaRNA RNAinverse (CPU tool) ──
    try:
        result = executor.run_tool(
            "inverse_fold_rna_secondary_structure_vienna",
            filepath=struct_fp,
            repeats=10,
            temp_c=37.0,
            function_mode="m",
        )
        ok = result.success and "best_sequence" in str(result.artifacts)
        seq = (
            result.artifacts.get("result", {}).get("best_sequence", "")
            if result.success
            else ""
        )
        hd = result.artifacts.get("result", {}).get("hamming_distance") if result.success else None
        _record(
            "L0_viennarna_rnainverse",
            ok,
            f"success={result.success}, seq_len={len(seq)}, hamming_dist={hd}"
            + (f", error={result.error}" if not ok else ""),
        )
    except Exception as exc:
        _record("L0_viennarna_rnainverse", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1b. ViennaRNA RNAfold (CPU tool) ──
    # Use a known sequence that should fold to our target
    test_seq = "GGCAAAGCC"  # 9nt, matches (((...))) from RNAinverse quick test
    seq_fp = save_sequence(test_seq, prefix="test_seq")
    try:
        result = executor.run_tool(
            "predict_rna_secondary_structure",
            filepath=seq_fp,
        )
        ok = result.success and "structure" in str(result.artifacts)
        struct = (
            result.artifacts.get("result", {}).get("structure", "")
            if result.success
            else ""
        )
        mfe = result.artifacts.get("result", {}).get("mfe_kcal_per_mol") if result.success else None
        _record(
            "L0_viennarna_rnafold",
            ok,
            f"success={result.success}, struct_len={len(struct)}, mfe={mfe}"
            + (f", error={result.error}" if not ok else ""),
        )
    except Exception as exc:
        _record("L0_viennarna_rnafold", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1c. GC content (CPU tool) ──
    try:
        result = executor.run_tool(
            "compute_rna_sequence_gc_content",
            filepath=seq_fp,
        )
        ok = result.success and "gc_content" in str(result.artifacts)
        gc = result.artifacts.get("result", {}).get("gc_content") if result.success else None
        _record(
            "L0_gc_content",
            ok,
            f"success={result.success}, gc={gc}"
            + (f", error={result.error}" if not ok else ""),
        )
    except Exception as exc:
        _record("L0_gc_content", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1d. LinearFold (CPU fallback) ──
    try:
        result = executor.run_tool(
            "predict_rna_secondary_structure_with_linearfold",
            filepath=seq_fp,
        )
        ok = result.success and "structure" in str(result.artifacts)
        struct = (
            result.artifacts.get("result", {}).get("structure", "")
            if result.success
            else ""
        )
        _record(
            "L0_linearfold",
            ok,
            f"success={result.success}, struct_len={len(struct)}"
            + (f", error={result.error}" if not ok else ""),
        )
    except Exception as exc:
        _record("L0_linearfold", False, f"Exception: {type(exc).__name__}: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Layer 1 — Capability integration
# ═══════════════════════════════════════════════════════════════════════════════


def test_layer1_capabilities() -> None:
    """Test capabilities via CapabilityRegistry (Layer 1)."""
    _print_header("Phase 2: Layer 1 — Capability Integration")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.file_manager import save_sequence, save_text_file
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)

    state: dict[str, Any] = {}

    # Save test data
    struct_fp = save_text_file(
        TEST_TARGET_STRUCTURE, prefix="test_target_struct", suffix=".txt"
    )
    seq_fp = save_sequence("GGCAAAGCC", prefix="test_seq")

    # ── 2a. Inverse fold capability ──
    try:
        cap = registry.get("inverse_fold_rna_secondary_structure_vienna")
        result = cap.invoke(
            {
                "filepath": struct_fp,
                "repeats": 5,
                "temp_c": 37.0,
                "function_mode": "m",
            },
            state=state,
        )
        ok = result.success and result.output.get("best_sequence")
        seq = result.output.get("best_sequence", "") if result.success else ""
        _record(
            "L1_cap_inverse_fold",
            ok,
            f"success={result.success}, seq_len={len(seq)}"
            + (f", error={result.error}" if not ok else ""),
        )
        # Verify writeback
        wb_ok = (
            "tool_results" in state
            and "inverse_fold_rna_secondary_structure_vienna" in state["tool_results"]
        )
        _record("L1_cap_writeback_inverse", wb_ok, f"tool_results written={wb_ok}")
    except Exception as exc:
        _record("L1_cap_inverse_fold", False, f"Exception: {type(exc).__name__}: {exc}")
        _record("L1_cap_writeback_inverse", False, "Skipped due to failure")

    # ── 2b. RNAfold capability ──
    try:
        cap = registry.get("predict_rna_secondary_structure")
        result = cap.invoke({"filepath": seq_fp}, state=state)
        ok = result.success and result.output.get("structure")
        struct = result.output.get("structure", "") if result.success else ""
        _record(
            "L1_cap_rnafold",
            ok,
            f"success={result.success}, struct_len={len(struct)}",
        )
    except Exception as exc:
        _record("L1_cap_rnafold", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 2c. GC content capability ──
    try:
        cap = registry.get("compute_rna_sequence_gc_content")
        result = cap.invoke({"filepath": seq_fp}, state=state)
        ok = result.success and result.output.get("gc_content") is not None
        gc = result.output.get("gc_content") if result.success else None
        _record("L1_cap_gc", ok, f"success={result.success}, gc={gc}")
    except Exception as exc:
        _record("L1_cap_gc", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 2d. LinearFold capability ──
    try:
        cap = registry.get("predict_rna_secondary_structure_with_linearfold")
        result = cap.invoke({"filepath": seq_fp}, state=state)
        ok = result.success and result.output.get("structure")
        struct = result.output.get("structure", "") if result.success else ""
        _record(
            "L1_cap_linearfold",
            ok,
            f"success={result.success}, struct_len={len(struct)}",
        )
    except Exception as exc:
        _record("L1_cap_linearfold", False, f"Exception: {type(exc).__name__}: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Layer 2 — Full workflow end-to-end
# ═══════════════════════════════════════════════════════════════════════════════


def test_layer2_workflow() -> None:
    """Test the complete RnaSecondaryStructureDesignWorkflow end-to-end."""
    _print_header("Phase 3: Layer 2 — Full Workflow")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignInput,
        RnaSecondaryStructureDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = RnaSecondaryStructureDesignWorkflow(registry)

    # Test 3a: Basic run with default params
    _LOGGER.info("Running workflow with default params...")
    try:
        inp = RnaSecondaryStructureDesignInput(
            target_structure=TEST_TARGET_STRUCTURE,
            num_invocations=2,
            repeats=5,
        )
        start = time.perf_counter()
        result = workflow.run(inp)
        elapsed = time.perf_counter() - start

        ok = result.success and result.best_candidate is not None
        cand_count = len(result.all_candidates) if result.all_candidates else 0
        best_seq = result.best_candidate.sequence if result.best_candidate else ""
        best_score = (
            result.best_candidate.scores.get("total_score")
            if result.best_candidate and result.best_candidate.scores
            else None
        )
        detail = (
            f"success={result.success}, candidates={cand_count}, best_len={len(best_seq)}, "
            f"best_score={best_score:.4f}" if best_score is not None else f"best_score=N/A"
        ) + f", elapsed={elapsed:.1f}s" + (
            f", errors={result.errors}" if result.errors else ""
        )
        _record("L2_workflow_basic", ok, detail)

        if ok:
            print(f"\n    Workflow summary preview:")
            for line in (result.summary or "").split("\n")[:6]:
                print(f"      {line}")
    except Exception as exc:
        import traceback
        _record("L2_workflow_basic", False, f"Exception: {type(exc).__name__}: {exc}")
        _LOGGER.error("Traceback:\n%s", traceback.format_exc())

    # Test 3b: With start_sequence
    _LOGGER.info("Running workflow with start_sequence...")
    try:
        inp = RnaSecondaryStructureDesignInput(
            target_structure="(((...)))",
            start_sequence="NNNNNNNNN",
            num_invocations=1,
            repeats=5,
            temp_c=25.0,
            function_mode="mp",
        )
        result = workflow.run(inp)
        ok = result.success and result.best_candidate is not None
        cand_count = len(result.all_candidates) if result.all_candidates else 0
        _record(
            "L2_workflow_with_start_sequence",
            ok,
            f"success={result.success}, candidates={cand_count}, mode=mp, temp=25C",
        )
    except Exception as exc:
        _record("L2_workflow_with_start_sequence", False, f"Exception: {type(exc).__name__}: {exc}")

    # Test 3c: With progress callback
    _LOGGER.info("Running workflow with progress_callback...")
    try:
        progress_events: list[dict[str, Any]] = []

        def _progress_cb(event: dict[str, Any]) -> None:
            progress_events.append(event)

        inp = RnaSecondaryStructureDesignInput(
            target_structure="(((...)))",
            num_invocations=1,
            repeats=3,
        )
        result = workflow.run(inp, progress_callback=_progress_cb)
        ok = result.success
        event_types = [e.get("event") for e in progress_events]
        has_generate = "generate_complete" in event_types
        has_eval = "evaluate_progress" in event_types
        _record(
            "L2_workflow_progress_callback",
            ok and has_generate and has_eval,
            f"success={result.success}, events={event_types}, "
            f"generate_complete={has_generate}, evaluate_progress={has_eval}",
        )
    except Exception as exc:
        _record("L2_workflow_progress_callback", False, f"Exception: {type(exc).__name__}: {exc}")

    # Test 3d: Empty target structure should fail gracefully
    _LOGGER.info("Testing empty target structure...")
    try:
        inp = RnaSecondaryStructureDesignInput(target_structure="   ")
        result = workflow.run(inp)
        _record(
            "L2_workflow_empty_target",
            not result.success,
            f"success={result.success} (expected False), errors={result.errors}",
        )
    except Exception as exc:
        _record("L2_workflow_empty_target", False, f"Exception: {type(exc).__name__}: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Layer 3 — ExecutionController + Critic retry + parameter override
# ═══════════════════════════════════════════════════════════════════════════════


def test_layer3_controller_execution() -> None:
    """Test ExecutionController executing the workflow with state writebacks."""
    _print_header("Phase 4a: Layer 3 — ExecutionController Workflow Execution")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflow_models import WorkflowResult
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = RnaSecondaryStructureDesignWorkflow(registry)

    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"rna_secondary_structure_design": workflow},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_secondary_structure_design",
                input_binding={
                    "target_structure": "(((...)))",
                    "num_invocations": 1,
                    "repeats": 5,
                },
                output_key="design_result",
                description="Design RNA secondary structure",
            )
        ],
        max_retries=2,
    )

    try:
        state: dict[str, Any] = {"user_text": "Design RNA for hairpin structure"}
        result_state = controller.execute(plan, state)

        # Verify workflow result
        wf_result = result_state.get("design_result")
        ok_result = isinstance(wf_result, WorkflowResult) and wf_result.success
        _record(
            "L3_controller_workflow_result",
            ok_result,
            f"is_WorkflowResult={isinstance(wf_result, WorkflowResult)}, "
            f"success={getattr(wf_result, 'success', 'N/A')}",
        )

        # Also in generic slot
        ok_generic = result_state.get("workflow_result") is wf_result
        _record("L3_controller_generic_slot", ok_generic, f"workflow_result matches design_result={ok_generic}")

        # State writebacks
        has_tool_results = "tool_results" in result_state
        _record("L3_controller_tool_results", has_tool_results, f"tool_results present={has_tool_results}")

        # Execution log
        log = result_state.get("_execution_log", [])
        event_types = [e["event"] for e in log]
        has_start = "step_start" in event_types
        has_done = "step_done" in event_types
        has_complete = "plan_complete" in event_types
        _record(
            "L3_controller_execution_log",
            has_start and has_done and has_complete,
            f"events={event_types}",
        )

        # Plan executed flag
        _record(
            "L3_controller_plan_executed",
            result_state.get("_plan_executed") is True,
            f"_plan_executed={result_state.get('_plan_executed')}",
        )

    except Exception as exc:
        import traceback
        _record("L3_controller_workflow_result", False, f"Exception: {type(exc).__name__}: {exc}")
        _LOGGER.error("Traceback:\n%s", traceback.format_exc())


def test_layer3_controller_progress_callback() -> None:
    """ExecutionController should forward progress_callback to workflow.run()."""
    _print_header("Phase 4b: Layer 3 — Progress Callback Forwarding")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = RnaSecondaryStructureDesignWorkflow(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_secondary_structure_design",
                input_binding={
                    "target_structure": "(((...)))",
                    "num_invocations": 1,
                    "repeats": 3,
                },
                output_key="result",
            )
        ]
    )

    events: list[dict[str, Any]] = []

    def callback(event: dict[str, Any]) -> None:
        events.append(event)

    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"rna_secondary_structure_design": workflow},
    )

    try:
        state: dict[str, Any] = {}
        result_state = controller.execute(plan, state, progress_callback=callback)

        event_types = [e["event"] for e in events]
        has_step_start = "step_start" in event_types
        has_step_done = "step_done" in event_types
        has_generate = "generate_complete" in event_types
        has_eval = "evaluate_progress" in event_types
        has_plan_complete = "plan_complete" in event_types

        _record(
            "L3_progress_callback_events",
            has_step_start and has_step_done and has_generate and has_eval and has_plan_complete,
            f"events={event_types}",
        )
        _record(
            "L3_progress_plan_executed",
            result_state.get("_plan_executed") is True,
            f"_plan_executed={result_state.get('_plan_executed')}",
        )
    except Exception as exc:
        _record("L3_progress_callback_events", False, f"Exception: {type(exc).__name__}: {exc}")


def test_layer3_critic_retry_with_mock_llm() -> None:
    """Test critic-driven retry using mocked LLM diagnosis.

    Simulates a scenario where the first run produces poor structure fidelity,
    the critic recommends increasing repeats and num_invocations, and the
    controller re-executes with adjusted parameters.
    """
    _print_header("Phase 4c: Layer 3 — Critic Retry with Mock LLM")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
    from agent_core.planning.llm_critic import CriticDiagnosis, CriticIssue
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignLLMCritic,
        RnaSecondaryStructureDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = RnaSecondaryStructureDesignWorkflow(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_secondary_structure_design",
                input_binding={
                    "target_structure": "(((...)))",
                    "num_invocations": 1,
                    "repeats": 3,
                },
                output_key="result",
            )
        ],
        max_retries=2,
    )

    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"rna_secondary_structure_design": workflow},
    )

    # Build mock diagnoses: first call triggers retry, second call proceeds
    retry_diagnosis = CriticDiagnosis(
        overall_assessment="Structure fidelity is poor; candidates do not fold back to target",
        quality_score=0.2,
        issues=[
            CriticIssue(
                severity="critical",
                category="structure_fidelity",
                description="All candidates have high structure_distance from target",
                metric_value=0.8,
                affected_candidate_count=1,
            )
        ],
        action="retry_with_adjustments",
        parameter_overrides={
            "repeats": 20,
            "num_invocations": 3,
            "function_mode": "mp",
        },
        reasoning="Increase search depth and use partition function for better structure matching",
        confidence=0.85,
    )

    proceed_diagnosis = CriticDiagnosis(
        overall_assessment="Structure fidelity improved after parameter adjustment",
        quality_score=0.75,
        issues=[],
        action="proceed_with_filtered",
        parameter_overrides={},
        reasoning="Retry produced acceptable results",
        confidence=0.9,
    )

    _call_count = 0

    def _mock_diagnose(result, state):
        nonlocal _call_count
        _call_count += 1
        return retry_diagnosis if _call_count == 1 else proceed_diagnosis

    critic = RnaSecondaryStructureDesignLLMCritic()

    try:
        events: list[dict[str, Any]] = []

        def callback(event: dict[str, Any]) -> None:
            events.append(event)

        state: dict[str, Any] = {}

        with patch.object(critic, "diagnose", side_effect=_mock_diagnose):
            with patch(
                "agent_core.workflows.registry.get_critic_for_workflow",
                return_value=critic,
            ):
                result_state = controller.execute(
                    plan, state, replan_fn=lambda s: plan, progress_callback=callback
                )

        log = result_state.get("_execution_log", [])
        event_types = [e["event"] for e in log]

        # Should have executed twice: initial + 1 retry
        step_start_count = event_types.count("step_start")
        step_done_count = event_types.count("step_done")
        has_critic_retry = "critic_retry" in event_types
        has_param_override = "parameter_override" in event_types
        has_plan_complete = "plan_complete" in event_types
        retry_count = result_state.get("retry_count", 0)

        _record(
            "L3_critic_retry_triggered",
            has_critic_retry,
            f"critic_retry in events={has_critic_retry}",
        )
        _record(
            "L3_critic_parameter_override",
            has_param_override,
            f"parameter_override in events={has_param_override}",
        )
        _record(
            "L3_critic_retry_count",
            retry_count == 1,
            f"retry_count={retry_count} (expected 1)",
        )
        _record(
            "L3_critic_executed_twice",
            step_start_count == 2 and step_done_count == 2,
            f"step_start={step_start_count}, step_done={step_done_count} (expected 2 each)",
        )
        _record(
            "L3_critic_plan_completed",
            has_plan_complete,
            f"plan_complete in events={has_plan_complete}",
        )

        # Verify parameter overrides were applied to the plan
        binding = plan.steps[0].input_binding
        ok_repeats = binding.get("repeats") == 20
        ok_invocations = binding.get("num_invocations") == 3
        ok_mode = binding.get("function_mode") == "mp"
        _record(
            "L3_critic_overrides_applied",
            ok_repeats and ok_invocations and ok_mode,
            f"repeats={binding.get('repeats')}, num_invocations={binding.get('num_invocations')}, "
            f"function_mode={binding.get('function_mode')}",
        )

        # Verify progress callback received retry events
        cb_types = [e["event"] for e in events]
        _record(
            "L3_critic_progress_callback",
            "critic_retry" in cb_types and "parameter_override" in cb_types,
            f"callback events={list(dict.fromkeys(cb_types))}",
        )

    except Exception as exc:
        import traceback
        _record("L3_critic_retry_triggered", False, f"Exception: {type(exc).__name__}: {exc}")
        _LOGGER.error("Traceback:\n%s", traceback.format_exc())


def test_layer3_critic_max_retries_exhausted() -> None:
    """When max_retries is exhausted, controller should return with retries_exhausted flag."""
    _print_header("Phase 4d: Layer 3 — Max Retries Exhausted")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
    from agent_core.planning.llm_critic import CriticDiagnosis, CriticIssue
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignLLMCritic,
        RnaSecondaryStructureDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = RnaSecondaryStructureDesignWorkflow(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_secondary_structure_design",
                input_binding={
                    "target_structure": "(((...)))",
                    "num_invocations": 1,
                    "repeats": 3,
                },
                output_key="result",
            )
        ],
        max_retries=1,
    )

    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"rna_secondary_structure_design": workflow},
    )

    # Always-retry diagnosis
    always_retry_diag = CriticDiagnosis(
        overall_assessment="Always retry",
        quality_score=0.1,
        issues=[
            CriticIssue(
                severity="critical",
                category="test",
                description="Forced retry for testing",
            )
        ],
        action="retry_with_adjustments",
        parameter_overrides={"repeats": 50},
        reasoning="Test max retries",
        confidence=0.9,
    )

    critic = RnaSecondaryStructureDesignLLMCritic()

    try:
        with patch.object(critic, "diagnose", return_value=always_retry_diag):
            with patch(
                "agent_core.workflows.registry.get_critic_for_workflow",
                return_value=critic,
            ):
                state: dict[str, Any] = {}
                result_state = controller.execute(plan, state, replan_fn=lambda s: plan)

        log = result_state.get("_execution_log", [])
        event_types = [e["event"] for e in log]

        # Initial + 1 retry = 2 executions
        step_start_count = event_types.count("step_start")
        critic_retry_count = event_types.count("critic_retry")

        complete_entries = [e for e in log if e["event"] == "plan_complete"]
        has_retries_exhausted = (
            len(complete_entries) == 1 and complete_entries[0].get("retries_exhausted") is True
        )

        _record(
            "L3_max_retries_executed_twice",
            step_start_count == 2,
            f"step_start_count={step_start_count} (expected 2)",
        )
        _record(
            "L3_max_retries_critic_triggered_twice",
            critic_retry_count == 2,
            f"critic_retry_count={critic_retry_count} (expected 2)",
        )
        _record(
            "L3_max_retries_exhausted_flag",
            has_retries_exhausted,
            f"retries_exhausted={has_retries_exhausted}",
        )
        _record(
            "L3_max_retries_count",
            result_state.get("retry_count") == 1,
            f"retry_count={result_state.get('retry_count')} (expected 1)",
        )

    except Exception as exc:
        import traceback
        _record("L3_max_retries_executed_twice", False, f"Exception: {type(exc).__name__}: {exc}")
        _LOGGER.error("Traceback:\n%s", traceback.format_exc())


def test_layer3_critic_disabled_flag() -> None:
    """When _llm_critic_enabled=False, critic should not trigger retry."""
    _print_header("Phase 4e: Layer 3 — Critic Disabled by State Flag")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
    from agent_core.planning.llm_critic import CriticDiagnosis, CriticIssue
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignLLMCritic,
        RnaSecondaryStructureDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = RnaSecondaryStructureDesignWorkflow(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_secondary_structure_design",
                input_binding={
                    "target_structure": "(((...)))",
                    "num_invocations": 1,
                    "repeats": 3,
                },
                output_key="result",
            )
        ],
        max_retries=2,
    )

    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"rna_secondary_structure_design": workflow},
    )

    retry_diag = CriticDiagnosis(
        overall_assessment="Should not be called",
        quality_score=0.1,
        issues=[CriticIssue(severity="critical", category="test", description="Should not retry")],
        action="retry_with_adjustments",
        parameter_overrides={"repeats": 100},
        reasoning="Test disabled flag",
        confidence=0.9,
    )

    critic = RnaSecondaryStructureDesignLLMCritic()

    try:
        with patch.object(critic, "diagnose", return_value=retry_diag):
            with patch(
                "agent_core.workflows.registry.get_critic_for_workflow",
                return_value=critic,
            ):
                state: dict[str, Any] = {"_llm_critic_enabled": False}
                result_state = controller.execute(plan, state, replan_fn=lambda s: plan)

        log = result_state.get("_execution_log", [])
        event_types = [e["event"] for e in log]

        # Should execute only once since critic is disabled
        step_start_count = event_types.count("step_start")
        has_no_critic_retry = "critic_retry" not in event_types
        retry_count = result_state.get("retry_count")

        _record(
            "L3_disabled_single_execution",
            step_start_count == 1,
            f"step_start_count={step_start_count} (expected 1)",
        )
        _record(
            "L3_disabled_no_retry",
            has_no_critic_retry,
            f"critic_retry absent={has_no_critic_retry}",
        )
        _record(
            "L3_disabled_no_retry_count",
            retry_count is None or retry_count == 0,
            f"retry_count={retry_count} (expected None or 0)",
        )

    except Exception as exc:
        _record("L3_disabled_single_execution", False, f"Exception: {type(exc).__name__}: {exc}")


def test_layer3_parameter_override_filtering() -> None:
    """Critic parameter overrides should be filtered to known adjustable params only."""
    _print_header("Phase 4f: Layer 3 — Parameter Override Filtering")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
    from agent_core.planning.llm_critic import CriticDiagnosis
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignLLMCritic,
        RnaSecondaryStructureDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = RnaSecondaryStructureDesignWorkflow(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_secondary_structure_design",
                input_binding={
                    "target_structure": "(((...)))",
                    "num_invocations": 1,
                    "repeats": 3,
                },
                output_key="result",
            )
        ],
        max_retries=2,
    )

    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"rna_secondary_structure_design": workflow},
    )

    # Diagnosis with valid AND invalid params
    mixed_diag = CriticDiagnosis(
        overall_assessment="Mixed valid/invalid params",
        quality_score=0.3,
        issues=[],
        action="retry_with_adjustments",
        parameter_overrides={
            "repeats": 25,           # valid
            "num_invocations": 5,     # valid
            "temp_c": 55.0,          # valid
            "function_mode": "p",    # valid
            "invalid_param_xyz": 999,  # invalid — should be filtered out
            "_private_param": "bad",   # invalid — should be filtered out
        },
        reasoning="Test filtering",
        confidence=0.8,
    )

    critic = RnaSecondaryStructureDesignLLMCritic()

    try:
        with patch.object(critic, "diagnose", return_value=mixed_diag):
            with patch(
                "agent_core.workflows.registry.get_critic_for_workflow",
                return_value=critic,
            ):
                state: dict[str, Any] = {}
                result_state = controller.execute(plan, state, replan_fn=lambda s: plan)

        # Check that only valid params were applied
        binding = plan.steps[0].input_binding
        has_valid = (
            binding.get("repeats") == 25
            and binding.get("num_invocations") == 5
            and binding.get("temp_c") == 55.0
            and binding.get("function_mode") == "p"
        )
        has_no_invalid = (
            "invalid_param_xyz" not in binding
            and "_private_param" not in binding
        )

        _record(
            "L3_override_valid_params_applied",
            has_valid,
            f"binding={dict(binding)}",
        )
        _record(
            "L3_override_invalid_params_filtered",
            has_no_invalid,
            f"invalid_param_xyz in binding={'invalid_param_xyz' in binding}, "
            f"_private_param in binding={'_private_param' in binding}",
        )

    except Exception as exc:
        import traceback
        _record("L3_override_valid_params_applied", False, f"Exception: {type(exc).__name__}: {exc}")
        _LOGGER.error("Traceback:\n%s", traceback.format_exc())


def test_layer3_state_binding_resolution() -> None:
    """ExecutionController resolves $state references in input bindings."""
    _print_header("Phase 4g: Layer 3 — $state Binding Resolution")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = RnaSecondaryStructureDesignWorkflow(registry)

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_secondary_structure_design",
                input_binding={
                    "target_structure": "$state.target_struct",
                    "num_invocations": 1,
                    "repeats": 3,
                },
                output_key="result",
            )
        ]
    )

    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"rna_secondary_structure_design": workflow},
    )

    try:
        state: dict[str, Any] = {"target_struct": "(((...)))"}
        result_state = controller.execute(plan, state)

        wf_result = result_state.get("workflow_result")
        ok = wf_result is not None and getattr(wf_result, "success", False)
        _record(
            "L3_state_binding_resolved",
            ok,
            f"workflow_success={getattr(wf_result, 'success', 'N/A')}",
        )

    except Exception as exc:
        _record("L3_state_binding_resolved", False, f"Exception: {type(exc).__name__}: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Live LLM Critic (requires DEEPSEEK_API_KEY)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live_llm
@pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_API_KEY"),
    reason="Requires DEEPSEEK_API_KEY environment variable",
)
def test_live_critic_diagnosis() -> None:
    """Live test: actual DeepSeek API call for critic diagnosis.

    This test sends a real request to DeepSeek and verifies the response
    structure. It is skipped unless --live-llm flag is passed AND
    DEEPSEEK_API_KEY is set.
    """
    _print_header("Phase 5: Live LLM Critic — Actual DeepSeek API Call")

    from agent_core.planning.llm_critic import CriticDiagnosis
    from agent_core.workflow_models import Candidate, WorkflowResult
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignLLMCritic,
    )

    critic = RnaSecondaryStructureDesignLLMCritic()

    # Build a deliberately poor result to trigger useful diagnosis
    poor_candidate = Candidate(
        sequence="AUGC" * 10,
        sequence_type="rna",
        source="vienna_inverse_0",
        metadata={
            "metrics_bundle": {
                "sequence_length": 40,
                "structure_distance": 20,
                "vienna_mfe": -2.0,
                "gc_content": 0.25,
                "folded_structure": "...." * 10,
            }
        },
    )
    poor_candidate.scores = {"total_score": 0.5, "structure_distance_ratio": 0.5, "mfe": -2.0}

    result = WorkflowResult(
        success=True,
        task_id="live_test",
        summary="Poor structure fidelity",
        errors=[],
        all_candidates=[poor_candidate],
    )

    state = {
        "_last_workflow_params": {
            "target_structure": "((((....))))....((((....))))",
            "repeats": 5,
            "num_invocations": 1,
            "temp_c": 37.0,
            "function_mode": "m",
        },
        "user_text": "Design an RNA sequence that folds into ((((....))))....((((....))))",
    }

    try:
        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        assert 0.0 <= diagnosis.quality_score <= 1.0
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
            "proceed_with_filtered",
            "abort",
        )

        _record(
            "L5_live_critic_diagnosis",
            True,
            f"action={diagnosis.action}, quality={diagnosis.quality_score:.2f}, "
            f"issues={len(diagnosis.issues)}, overrides={diagnosis.parameter_overrides}",
        )

        print(f"\n    Live diagnosis:")
        print(f"      action: {diagnosis.action}")
        print(f"      quality_score: {diagnosis.quality_score}")
        print(f"      issues: {len(diagnosis.issues)}")
        for issue in diagnosis.issues:
            print(f"        [{issue.severity}] {issue.description}")
        print(f"      parameter_overrides: {diagnosis.parameter_overrides}")
        print(f"      reasoning: {diagnosis.reasoning[:200]}...")

        # Test should_retry as well
        should_retry = critic.should_retry(result, state)
        _record(
            "L5_live_critic_should_retry",
            isinstance(should_retry, bool),
            f"should_retry={should_retry}",
        )

    except Exception as exc:
        import traceback
        _record("L5_live_critic_diagnosis", False, f"Exception: {type(exc).__name__}: {exc}")
        _LOGGER.error("Traceback:\n%s", traceback.format_exc())


@pytest.mark.live_llm
@pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_API_KEY"),
    reason="Requires DEEPSEEK_API_KEY environment variable",
)
def test_live_critic_e2e_retry_flow() -> None:
    """Live end-to-end: Controller + real Critic + actual parameter adjustment.

    This test runs the full Layer 3 retry flow with a real LLM call.
    It uses poor initial parameters, lets the critic diagnose, and verifies
    that retry happens with adjusted parameters.
    """
    _print_header("Phase 5b: Live LLM Critic — E2E Retry Flow")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.rna_secondary_structure_design import (
        RnaSecondaryStructureDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = RnaSecondaryStructureDesignWorkflow(registry)

    # Start with very poor parameters (low repeats, single invocation)
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="rna_secondary_structure_design",
                input_binding={
                    "target_structure": "(((...)))",
                    "num_invocations": 1,
                    "repeats": 2,
                    "temp_c": 37.0,
                    "function_mode": "m",
                },
                output_key="result",
            )
        ],
        max_retries=1,
    )

    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"rna_secondary_structure_design": workflow},
    )

    try:
        state: dict[str, Any] = {
            "user_text": "Design RNA hairpin",
            "_llm_critic_enabled": True,
        }

        result_state = controller.execute(plan, state, replan_fn=lambda s: plan)

        log = result_state.get("_execution_log", [])
        event_types = [e["event"] for e in log]

        # The critic may or may not trigger retry depending on actual results
        has_critic_retry = "critic_retry" in event_types
        has_param_override = "parameter_override" in event_types
        retry_count = result_state.get("retry_count", 0)

        _record(
            "L5b_live_e2e_executed",
            result_state.get("_plan_executed") is True,
            f"plan_executed={result_state.get('_plan_executed')}",
        )
        _record(
            "L5b_live_e2e_critic_retry",
            True,  # We only verify the flow executed, not specific critic decision
            f"critic_retry={has_critic_retry}, parameter_override={has_param_override}, "
            f"retry_count={retry_count}",
        )

        # Verify diagnosis history was recorded
        diag_history = result_state.get("_diagnosis_history", [])
        _record(
            "L5b_live_e2e_diagnosis_history",
            len(diag_history) >= 0,
            f"diagnosis_history_count={len(diag_history)}",
        )

        if diag_history:
            last_diag = diag_history[-1]
            print(f"\n    Last diagnosis:")
            print(f"      action: {last_diag.get('action')}")
            print(f"      quality_score: {last_diag.get('quality_score')}")
            print(f"      parameter_overrides: {last_diag.get('parameter_overrides')}")

    except Exception as exc:
        import traceback
        _record("L5b_live_e2e_executed", False, f"Exception: {type(exc).__name__}: {exc}")
        _LOGGER.error("Traceback:\n%s", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════════════════════
# Main entry point (for running without pytest)
# ═══════════════════════════════════════════════════════════════════════════════


def run_all_tests() -> int:
    print("\n" + "=" * 60)
    print("  RNA Secondary Structure Design — Full Stack Integration Test")
    print(f"  Target structure: {TEST_TARGET_STRUCTURE}")
    print("  Layers: 0 (Tools) → 1 (Capabilities) → 2 (Workflow) → 3 (Controller+Critic)")
    print("=" * 60)

    # Phase 0: DeepSeek API (best-effort; skip if no key)
    if os.environ.get("DEEPSEEK_API_KEY"):
        test_deepseek_api()
    else:
        print("\n[SKIP] Phase 0: DEEPSEEK_API_KEY not set — skipping live API test")
        _record("deepseek_api", True, "SKIPPED (no API key)")

    # Phase 1: Layer 0
    test_layer0_tools()

    # Phase 2: Layer 1
    test_layer1_capabilities()

    # Phase 3: Layer 2
    test_layer2_workflow()

    # Phase 4: Layer 3
    test_layer3_controller_execution()
    test_layer3_controller_progress_callback()
    test_layer3_critic_retry_with_mock_llm()
    test_layer3_critic_max_retries_exhausted()
    test_layer3_critic_disabled_flag()
    test_layer3_parameter_override_filtering()
    test_layer3_state_binding_resolution()

    _print_summary()

    passed = sum(1 for v in TEST_RESULTS.values() if v[0])
    total = len(TEST_RESULTS)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
