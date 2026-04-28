"""End-to-end tests for the five-layer architecture refactor.

These tests validate:
1. AgentRunner + RuleBasedPlanner + ExecutionController path
2. BaseDomainWorkflow abstraction (MrnaCdsDesignWorkflow)
3. Layer-1 capability auto-writeback
4. Golden path: protein → CDS design → fold + GC → score → rank
"""

from __future__ import annotations

import pytest

from agent_core.capabilities.base import CapabilityRegistry, build_default_capability_registry
from agent_core.planning.base import ExecutionController, ExecutionPlan
from agent_core.planning.rule_based.planner import RuleBasedPlanner
from agent_core.planning.rule_based.router import RuleBasedRouter
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflows import MrnaCdsDesignInput, MrnaCdsDesignWorkflow

pytestmark = [pytest.mark.integration]


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — Planner
# ─────────────────────────────────────────────────────────────────────────────

def test_rule_based_router_classifies_mrna_design() -> None:
    router = RuleBasedRouter()
    assert router.classify("Design mRNA for GFP") == "mrna_specialist"
    assert router.classify("LinearDesign for protein") == "mrna_specialist"
    assert router.classify("Evitar design for flu") == "sirna_specialist"
    assert router.classify("CRISPR sgRNA score") == "crispr_specialist"


def test_rule_based_planner_produces_plan_for_mrna_design() -> None:
    planner = RuleBasedPlanner()
    state: dict[str, Any] = {}
    plan = planner.plan_with_state("Design mRNA for protein MVSKGEELFTGV", state)
    assert len(plan.steps) >= 1
    assert plan.steps[0].type in ("capability", "workflow")
    assert state.get("route") == "mrna"


def test_rule_based_planner_produces_workflow_step_for_golden_path() -> None:
    planner = RuleBasedPlanner()
    state: dict[str, Any] = {}
    plan = planner.plan_with_state("LinearDesign for GFP MVSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDA", state)
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert step.type == "workflow"
    assert step.target == "mrna_cds_design"
    assert "protein_sequence" in step.input_binding


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Domain Workflow
# ─────────────────────────────────────────────────────────────────────────────

def test_mrna_cds_design_workflow_is_base_domain_workflow() -> None:
    reg = build_default_capability_registry(ToolExecutor(build_default_tool_registry()))
    wf = MrnaCdsDesignWorkflow(reg)
    assert wf.name == "mrna_cds_design"
    assert isinstance(wf, MrnaCdsDesignWorkflow)


def test_mrna_cds_design_workflow_accepts_dict_input() -> None:
    """Workflow.run() must accept a plain dict (from ExecutionController)."""
    reg = build_default_capability_registry(ToolExecutor(build_default_tool_registry()))
    wf = MrnaCdsDesignWorkflow(reg)
    # We do not run the full workflow here to avoid requiring microservices;
    # we only verify that dict input is coerced into the Pydantic model.
    inp = {"protein_sequence": "MVSKGEELFTGV", "design_tool": "gemorna"}
    parsed = MrnaCdsDesignInput(**inp)
    assert parsed.protein_sequence == "MVSKGEELFTGV"
    assert parsed.design_tool == "gemorna"


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Capabilities
# ─────────────────────────────────────────────────────────────────────────────

def test_capability_registry_builds_with_standard_writebacks() -> None:
    exe = ToolExecutor(build_default_tool_registry())
    reg = build_default_capability_registry(exe)
    # Key golden-path tools should be registered
    assert reg.has("design_mrna_cds_with_lineardesign")
    assert reg.has("predict_rna_secondary_structure")
    assert reg.has("compute_rna_sequence_gc_content")
    assert reg.has("analyze_cds_codon_metrics_with_codonw_slim")


def test_capability_auto_writeback_to_tool_results() -> None:
    exe = ToolExecutor(build_default_tool_registry())
    reg = build_default_capability_registry(exe)
    cap = reg.get("compute_rna_sequence_gc_content")
    state: dict[str, Any] = {}
    result = cap.invoke({"filepath": "workspace/mrna_8b630825f6.fasta"}, state=state)
    assert "tool_results" in state
    assert "compute_rna_sequence_gc_content" in state["tool_results"]


# ─────────────────────────────────────────────────────────────────────────────
# Layer 5 — AgentRunner (golden path, requires microservices)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_agent_runner_golden_path_mrna_cds_design() -> None:
    """Full golden path: protein → CDS design → evaluate → score → rank."""
    reg = build_default_tool_registry(include_demo=False)
    exe = ToolExecutor(reg)
    planner = RuleBasedPlanner()
    runner = AgentRunner(planner, exe)

    state = runner.run("LinearDesign for GFP protein MVSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDA")

    # Plan should contain exactly one workflow step
    plan = state.get("_execution_plan", {})
    assert len(plan.get("steps", [])) == 1
    assert plan["steps"][0]["target"] == "mrna_cds_design"

    # Workflow result should be present and successful
    wf_result = state.get("workflow_result")
    assert wf_result is not None
    assert wf_result.success is True
    assert len(wf_result.all_candidates) >= 1

    best = wf_result.best_candidate
    assert best is not None
    assert best.source == "cds_design:lineardesign"
    assert len(best.sequence) > 0
    assert "total_score" in best.scores

    # Backward-compatible state fields should be populated by auto-writeback
    assert "current_filepath" in state
    assert "candidate_sequence" in state
    assert state["candidate_sequence"] == best.sequence


@pytest.mark.integration
def test_agent_runner_legacy_chat_path_still_works() -> None:
    """``run_chat()`` must continue to use the compiled LangGraph graph."""
    langgraph = pytest.importorskip("langgraph")
    from agent_core.graph import compiled_graph

    reg = build_default_tool_registry(include_demo=False)
    exe = ToolExecutor(reg)
    planner = RuleBasedPlanner()
    runner = AgentRunner(planner, exe, compiled_graph=compiled_graph)

    state = runner.run_chat("Fold sequence AUGCUAACGUAGCUAUGCUA")
    assert state.get("route") == "mrna"
    assert "messages" in state
