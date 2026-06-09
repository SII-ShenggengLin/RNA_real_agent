"""Full-stack integration test for mrna_cds_design workflow across Layer 0, 1, 2.

Tests cover:
- DeepSeek API connectivity
- Layer 0: Individual tool invocations (CPU + GPU tools)
- Layer 1: Capability integration via CapabilityRegistry
- Layer 2: End-to-end MrnaCdsDesignWorkflow
- LLM Planner: DeepSeek generates plan → ExecutionController executes

Run: cd rna_agent_system && python -m pytest tests/test_mrna_cds_design_full_stack.py -v -s
"""

from __future__ import annotations

import logging
import pytest
import sys
import time
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_LOGGER = logging.getLogger("test_mrna_cds_design_full_stack")

# ═══════════════════════════════════════════════════════════════════════════════
# Test configuration
# ═══════════════════════════════════════════════════════════════════════════════

# Short protein sequence for fast testing (~22 aa = ~66 nt CDS)
TEST_PROTEIN_SEQUENCE = "MKTLLILTVFGITMLLAVLAQG"
TEST_LAMBDA = 1.0
TEST_SPECIES = "Homo sapiens"
TEST_MODEL_TYPE = "Homo sapiens mRNA"

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
# Phase 0: DeepSeek API test
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.live_llm
def test_deepseek_api() -> bool:
    """Test that DeepSeek API is reachable and returns sensible output."""
    _print_header("Phase 0: DeepSeek API Connectivity")
    try:
        from agent_core.llm_config import get_deepseek_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_deepseek_llm(temperature=0.1)
        messages = [
            SystemMessage(content="You are a helpful assistant. Reply with a single JSON object containing keys 'status' and 'message'."),
            HumanMessage(content="Say hello and confirm the API works. Return JSON only."),
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        if not content or len(content) < 5:
            _record("deepseek_api", False, f"Empty or too-short response: {content!r}")
            return False

        # Check response is sensible (contains some relevant words or JSON)
        ok = "hello" in content.lower() or "status" in content.lower() or "{" in content
        _record("deepseek_api", ok, f"Response length={len(content)}, preview={content[:100]!r}")
        return ok
    except Exception as exc:
        _record("deepseek_api", False, f"Exception: {type(exc).__name__}: {exc}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Layer 0 — Direct tool invocation
# ═══════════════════════════════════════════════════════════════════════════════

def test_layer0_tools() -> None:
    """Test each tool directly via ToolExecutor."""
    _print_header("Phase 1: Layer 0 — Direct Tool Invocation")

    from agent_core.file_manager import save_sequence
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    executor = ToolExecutor(build_default_tool_registry())

    # Save test protein sequence to workspace
    protein_fp = save_sequence(TEST_PROTEIN_SEQUENCE, prefix="test_protein")
    _LOGGER.info("Saved test protein to %s", protein_fp)

    # ── 1a. LinearDesign (CPU tool) ──
    try:
        result = executor.run_tool(
            "design_mrna_cds_with_lineardesign",
            filepath=protein_fp,
            lambda_value=TEST_LAMBDA,
        )
        ok = result.success and "generated_sequence" in str(result.artifacts)
        seq = result.artifacts.get("result", {}).get("generated_sequence", "") if result.success else ""
        _record("L0_lineardesign", ok,
                f"success={result.success}, seq_len={len(seq)}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L0_lineardesign", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1b. RNARL (GPU tool) ──
    try:
        result = executor.run_tool(
            "design_mrna_cds_with_rnarl",
            filepath=protein_fp,
            model_type=TEST_MODEL_TYPE,
        )
        ok = result.success and "generated_sequence" in str(result.artifacts)
        seq = result.artifacts.get("result", {}).get("generated_sequence", "") if result.success else ""
        _record("L0_rnarl", ok,
                f"success={result.success}, seq_len={len(seq)}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L0_rnarl", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1c. GEMORNA (GPU tool) ──
    try:
        result = executor.run_tool(
            "design_mrna_cds_with_gemorna",
            filepath=protein_fp,
        )
        ok = result.success and "generated_sequence" in str(result.artifacts)
        seq = result.artifacts.get("result", {}).get("generated_sequence", "") if result.success else ""
        _record("L0_gemorna", ok,
                f"success={result.success}, seq_len={len(seq)}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L0_gemorna", False, f"Exception: {type(exc).__name__}: {exc}")

    # Save a test CDS sequence for downstream tools (use a simple one if design failed)
    test_cds = "AUG" * 30  # 90 nt, valid CDS
    cds_fp = save_sequence(test_cds, prefix="test_cds")

    # ── 1d. ViennaRNA fold (CPU tool) ──
    try:
        result = executor.run_tool(
            "predict_rna_secondary_structure",
            filepath=cds_fp,
        )
        ok = result.success and "structure" in str(result.artifacts)
        struct = result.artifacts.get("result", {}).get("structure", "") if result.success else ""
        mfe = result.artifacts.get("result", {}).get("mfe_kcal_per_mol") if result.success else None
        _record("L0_viennarna_fold", ok,
                f"success={result.success}, struct_len={len(struct)}, mfe={mfe}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L0_viennarna_fold", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1e. LinearFold (CPU fallback tool) ──
    try:
        result = executor.run_tool(
            "predict_rna_secondary_structure_with_linearfold",
            filepath=cds_fp,
        )
        ok = result.success and "structure" in str(result.artifacts)
        struct = result.artifacts.get("result", {}).get("structure", "") if result.success else ""
        mfe = result.artifacts.get("result", {}).get("mfe") if result.success else None
        _record("L0_linearfold", ok,
                f"success={result.success}, struct_len={len(struct)}, mfe={mfe}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L0_linearfold", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1f. GC content (CPU tool) ──
    try:
        result = executor.run_tool(
            "compute_rna_sequence_gc_content",
            filepath=cds_fp,
        )
        ok = result.success and "gc_content" in str(result.artifacts)
        gc = result.artifacts.get("result", {}).get("gc_content") if result.success else None
        _record("L0_gc_content", ok,
                f"success={result.success}, gc={gc}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L0_gc_content", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1g. Dot-bracket unpaired fraction (CPU tool) ──
    # Need a structure file
    from agent_core.file_manager import save_text_file
    struct_fp = save_text_file("(((...)))" * 10, prefix="test_structure", suffix=".db")
    try:
        result = executor.run_tool(
            "compute_dot_bracket_unpaired_fraction",
            filepath=struct_fp,
        )
        ok = result.success and "unpaired_fraction" in str(result.artifacts)
        uf = result.artifacts.get("result", {}).get("unpaired_fraction") if result.success else None
        _record("L0_unpaired_fraction", ok,
                f"success={result.success}, unpaired={uf}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L0_unpaired_fraction", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1h. RNASTOP (GPU tool) ──
    try:
        result = executor.run_tool(
            "predict_mrna_stability_with_rnastop",
            filepath=cds_fp,
        )
        ok = result.success and "overall_stability" in str(result.artifacts)
        stab = result.artifacts.get("result", {}).get("overall_stability") if result.success else None
        _record("L0_rnastop", ok,
                f"success={result.success}, stability={stab}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L0_rnastop", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 1i. CAI for CDS (pure Python, no microservice) ──
    try:
        result = executor.run_tool(
            "compute_cai_for_cds_sequence",
            filepath=cds_fp,
            species=TEST_SPECIES,
        )
        ok = result.success and "cai_score" in str(result.artifacts)
        cai = result.artifacts.get("result", {}).get("cai_score") if result.success else None
        _record("L0_cai", ok,
                f"success={result.success}, cai={cai}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L0_cai", False, f"Exception: {type(exc).__name__}: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Layer 1 — Capability integration
# ═══════════════════════════════════════════════════════════════════════════════

def test_layer1_capabilities() -> None:
    """Test capabilities via CapabilityRegistry (Layer 1)."""
    _print_header("Phase 2: Layer 1 — Capability Integration")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.file_manager import save_sequence
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)

    state: dict[str, Any] = {}

    # Save test protein
    protein_fp = save_sequence(TEST_PROTEIN_SEQUENCE, prefix="test_protein")

    # ── 2a. LinearDesign capability ──
    try:
        cap = registry.get("design_mrna_cds_with_lineardesign")
        result = cap.invoke(
            {"filepath": protein_fp, "lambda_value": TEST_LAMBDA},
            state=state,
        )
        ok = result.success and result.output.get("generated_sequence")
        seq = result.output.get("generated_sequence", "") if result.success else ""
        _record("L1_cap_lineardesign", ok,
                f"success={result.success}, seq_len={len(seq)}" + (f", error={result.error}" if not ok else ""))
        # Verify writeback
        wb_ok = "tool_results" in state and "design_mrna_cds_with_lineardesign" in state["tool_results"]
        _record("L1_cap_writeback", wb_ok, f"tool_results written={wb_ok}")
    except Exception as exc:
        _record("L1_cap_lineardesign", False, f"Exception: {type(exc).__name__}: {exc}")
        _record("L1_cap_writeback", False, f"Skipped due to lineardesign failure")

    # ── 2b. RNARL capability ──
    try:
        cap = registry.get("design_mrna_cds_with_rnarl")
        result = cap.invoke(
            {"filepath": protein_fp, "model_type": TEST_MODEL_TYPE},
            state=state,
        )
        ok = result.success and result.output.get("generated_sequence")
        seq = result.output.get("generated_sequence", "") if result.success else ""
        _record("L1_cap_rnarl", ok,
                f"success={result.success}, seq_len={len(seq)}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L1_cap_rnarl", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 2c. GEMORNA capability ──
    try:
        cap = registry.get("design_mrna_cds_with_gemorna")
        result = cap.invoke(
            {"filepath": protein_fp},
            state=state,
        )
        ok = result.success and result.output.get("generated_sequence")
        seq = result.output.get("generated_sequence", "") if result.success else ""
        _record("L1_cap_gemorna", ok,
                f"success={result.success}, seq_len={len(seq)}" + (f", error={result.error}" if not ok else ""))
    except Exception as exc:
        _record("L1_cap_gemorna", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 2d. GC capability ──
    test_cds = "AUG" * 30
    cds_fp = save_sequence(test_cds, prefix="test_cds")
    try:
        cap = registry.get("compute_rna_sequence_gc_content")
        result = cap.invoke({"filepath": cds_fp}, state=state)
        ok = result.success and result.output.get("gc_content") is not None
        gc = result.output.get("gc_content") if result.success else None
        _record("L1_cap_gc", ok, f"success={result.success}, gc={gc}")
    except Exception as exc:
        _record("L1_cap_gc", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 2e. ViennaRNA fold capability ──
    try:
        cap = registry.get("predict_rna_secondary_structure")
        result = cap.invoke({"filepath": cds_fp}, state=state)
        ok = result.success and result.output.get("structure")
        struct = result.output.get("structure", "") if result.success else ""
        _record("L1_cap_fold", ok, f"success={result.success}, struct_len={len(struct)}")
    except Exception as exc:
        _record("L1_cap_fold", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 2f. RNASTOP capability ──
    try:
        cap = registry.get("predict_mrna_stability_with_rnastop")
        result = cap.invoke({"filepath": cds_fp}, state=state)
        ok = result.success and result.output.get("overall_stability") is not None
        stab = result.output.get("overall_stability") if result.success else None
        _record("L1_cap_rnastop", ok, f"success={result.success}, stability={stab}")
    except Exception as exc:
        _record("L1_cap_rnastop", False, f"Exception: {type(exc).__name__}: {exc}")

    # ── 2g. CAI capability ──
    try:
        cap = registry.get("compute_cai_for_cds_sequence")
        result = cap.invoke({"filepath": cds_fp, "species": TEST_SPECIES}, state=state)
        ok = result.success and result.output.get("cai_score") is not None
        cai = result.output.get("cai_score") if result.success else None
        _record("L1_cap_cai", ok, f"success={result.success}, cai={cai}")
    except Exception as exc:
        _record("L1_cap_cai", False, f"Exception: {type(exc).__name__}: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Layer 2 — Full workflow
# ═══════════════════════════════════════════════════════════════════════════════

def test_layer2_workflow() -> None:
    """Test the complete MrnaCdsDesignWorkflow end-to-end."""
    _print_header("Phase 3: Layer 2 — Full Workflow")

    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput, MrnaCdsDesignWorkflow

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    workflow = MrnaCdsDesignWorkflow(registry)

    # Test with a specific design_tool first (faster), then test "all"
    _LOGGER.info("Running workflow with design_tool='lineardesign'...")
    try:
        inp = MrnaCdsDesignInput(
            protein_sequence=TEST_PROTEIN_SEQUENCE,
            design_tool="lineardesign",
            lambda_value=TEST_LAMBDA,
            cai_species=TEST_SPECIES,
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
        _record(
            "L2_workflow_lineardesign",
            ok,
            f"success={result.success}, candidates={cand_count}, best_len={len(best_seq)}, "
            f"best_score={best_score:.3f}" if best_score is not None else f"best_score=N/A"
            + f", elapsed={elapsed:.1f}s"
            + (f", errors={result.errors}" if result.errors else "")
        )
    except Exception as exc:
        _record("L2_workflow_lineardesign", False, f"Exception: {type(exc).__name__}: {exc}")

    # Now test with design_tool="all" (includes GPU tools)
    _LOGGER.info("Running workflow with design_tool='all' (includes GPU tools)...")
    try:
        inp = MrnaCdsDesignInput(
            protein_sequence=TEST_PROTEIN_SEQUENCE,
            design_tool="all",
            cai_species=TEST_SPECIES,
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
            f"best_score={best_score:.3f}" if best_score is not None else f"best_score=N/A"
            + f", elapsed={elapsed:.1f}s"
            + (f", errors={result.errors}" if result.errors else "")
        )
        _record("L2_workflow_all_tools", ok, detail)

        # Print summary for inspection
        if ok:
            print(f"\n    Workflow summary preview:")
            for line in (result.summary or "").split("\n")[:8]:
                print(f"      {line}")
    except Exception as exc:
        import traceback
        _record("L2_workflow_all_tools", False, f"Exception: {type(exc).__name__}: {exc}\n{traceback.format_exc()}")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: LLM Planner → ExecutionController → Workflow
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.live_llm
def test_llm_planner_and_controller() -> None:
    """Test that DeepSeek generates a plan and ExecutionController can execute it."""
    _print_header("Phase 4: LLM Planner + ExecutionController (End-to-End)")

    try:
        from agent_core.capabilities.base import build_default_capability_registry
        from agent_core.planning.base import AgentContext, ExecutionController
        from agent_core.planning.llm_planner import LLMPlanner
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

        executor = ToolExecutor(build_default_tool_registry())
        registry = build_default_capability_registry(executor)

        # Build workflow registry
        from agent_core.workflows import MrnaCdsDesignWorkflow
        wf_registry = {
            "mrna_cds_design": MrnaCdsDesignWorkflow(registry),
        }

        planner = LLMPlanner()
        controller = ExecutionController(
            capability_registry=registry,
            workflow_registry=wf_registry,
        )

        # Test 4a: Planner generates a plan for mRNA CDS design
        user_input = (
            f"Design an mRNA CDS for protein sequence {TEST_PROTEIN_SEQUENCE} "
            f"using all available tools. Compute CAI for {TEST_SPECIES}."
        )
        ctx = AgentContext(
            session_id="test_session",
            available_capabilities=registry.list_names(),
            available_workflows=["mrna_cds_design"],
        )

        _LOGGER.info("Asking LLM to generate plan...")
        plan = planner.plan(user_input, ctx)

        ok_plan = len(plan.steps) > 0 and any(
            s.target == "mrna_cds_design" for s in plan.steps
        )
        _record(
            "L4_planner_generates_plan",
            ok_plan,
            f"steps={len(plan.steps)}, targets={[s.target for s in plan.steps]}"
        )

        if not ok_plan:
            _record("L4_controller_executes_plan", False, "Skipped: no valid plan generated")
            return

        # Test 4b: ExecutionController executes the plan
        state: dict[str, Any] = {
            "session_id": "test_session",
            "user_text": user_input,
            "_llm_critic_enabled": False,  # Disable critic to avoid extra LLM calls
        }

        _LOGGER.info("Executing plan via ExecutionController...")
        start = time.perf_counter()
        result_state = controller.execute(plan, state)
        elapsed = time.perf_counter() - start

        wf_result = result_state.get("workflow_result")
        ok_exec = (
            wf_result is not None
            and getattr(wf_result, "success", False)
            and getattr(wf_result, "best_candidate", None) is not None
        )

        if ok_exec:
            best = wf_result.best_candidate
            detail = (
                f"workflow_success={wf_result.success}, "
                f"candidates={len(wf_result.all_candidates) if wf_result.all_candidates else 0}, "
                f"best_len={len(best.sequence)}, "
                f"best_score={best.scores.get('total_score') if best.scores else 'N/A'}, "
                f"elapsed={elapsed:.1f}s"
            )
        else:
            detail = (
                f"workflow_result={wf_result}, "
                f"errors={getattr(wf_result, 'errors', 'N/A') if wf_result else 'no result'}, "
                f"elapsed={elapsed:.1f}s"
            )
        _record("L4_controller_executes_plan", ok_exec, detail)

        # Test 4c: Verify state writebacks
        has_tool_results = "tool_results" in result_state
        has_workflow_result = "workflow_result" in result_state
        _record(
            "L4_state_writebacks",
            has_tool_results and has_workflow_result,
            f"tool_results={has_tool_results}, workflow_result={has_workflow_result}"
        )

    except Exception as exc:
        import traceback
        _record("L4_planner_generates_plan", False, f"Exception: {type(exc).__name__}: {exc}")
        _record("L4_controller_executes_plan", False, "Skipped due to planner failure")
        _record("L4_state_writebacks", False, "Skipped")
        _LOGGER.error("Full traceback:\n%s", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run_all_tests() -> int:
    print("\n" + "=" * 60)
    print("  mRNA CDS Design — Full Stack Integration Test")
    print("  Protein sequence:", TEST_PROTEIN_SEQUENCE)
    print("  Length:", len(TEST_PROTEIN_SEQUENCE), "aa")
    print("=" * 60)

    # Phase 0: DeepSeek API
    test_deepseek_api()

    # Phase 1: Layer 0
    test_layer0_tools()

    # Phase 2: Layer 1
    test_layer1_capabilities()

    # Phase 3: Layer 2
    test_layer2_workflow()

    # Phase 4: LLM Planner + Controller
    test_llm_planner_and_controller()

    _print_summary()

    passed = sum(1 for v in TEST_RESULTS.values() if v[0])
    total = len(TEST_RESULTS)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
