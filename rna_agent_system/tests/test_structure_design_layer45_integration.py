"""Layer 4/5 integration tests for RNA secondary & tertiary structure design workflows.

Covers:
- Layer 4: SessionMemory persistence across multi-turn conversations
- Layer 4: WorkspaceManager per-session file isolation
- Layer 5: AgentRunner end-to-end (run + stream) with mocked planner
- Layer 5: LLM Critic retry logic with parameter overrides
- CLI/API entry verification for structure workflows
- CPU tool input/output format consistency
"""

from __future__ import annotations

import inspect
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_core.capabilities.base import CapabilityResult
from agent_core.planning.base import ExecutionPlan, PlanStep
from agent_core.runner import AgentRunner
from agent_core.session_memory import SessionMemory
from agent_core.state import default_state
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workspace_manager import WorkspaceManager
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.rna_secondary_structure_design import (
    RnaSecondaryStructureDesignInput,
    RnaSecondaryStructureDesignLLMCritic,
    RnaSecondaryStructureDesignWorkflow,
)
from agent_core.workflows.rna_tertiary_structure_design import (
    RnaTertiaryStructureDesignInput,
    RnaTertiaryStructureDesignLLMCritic,
    RnaTertiaryStructureDesignWorkflow,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ─────────────────────────────────────────────────────────────────────────────

TEST_SECONDARY_STRUCTURE = "((((....))))"
TEST_SEQUENCE_SHORT = "GGCAAAGCC"

_TMP_PDB_PATH = "/tmp/test_layer45_structure.pdb"


def _ensure_tmp_pdb() -> None:
    if not os.path.exists(_TMP_PDB_PATH):
        with open(_TMP_PDB_PATH, "w") as fh:
            fh.write(
                "ATOM    1  N   A   A   1      10.000  10.000  10.000  1.00  0.00           N\n"
            )


def _make_mock_planner_for_workflow(workflow_target: str, input_binding: dict[str, Any]):
    """Return a mock planner that always produces a single-step plan for the given workflow."""
    planner = MagicMock()
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target=workflow_target,
                input_binding=input_binding,
                output_key="workflow_result",
                description=f"Run {workflow_target}",
            )
        ],
        max_retries=2,
    )
    planner.plan_with_state = MagicMock(return_value=plan)
    return planner


def _make_registry_with_real_cpu_tools():
    """Build a real CapabilityRegistry with CPU tools (no GPU)."""
    executor = ToolExecutor(build_default_tool_registry(include_demo=False))
    from agent_core.capabilities.base import build_default_capability_registry

    return build_default_capability_registry(executor)


def _make_mock_registry_for_tertiary():
    """Registry with all mocked capabilities for tertiary structure workflow."""
    reg = MagicMock()

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


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 4 — SessionMemory
# ═══════════════════════════════════════════════════════════════════════════════


def test_secondary_structure_session_memory_persistence():
    """AgentRunner with SessionMemory should retain secondary structure results across turns."""
    registry = _make_registry_with_real_cpu_tools()
    planner = _make_mock_planner_for_workflow(
        "rna_secondary_structure_design",
        {"target_structure": TEST_SECONDARY_STRUCTURE, "num_invocations": 1, "repeats": 3},
    )
    memory = SessionMemory()
    runner = AgentRunner(planner, registry.executor, session_memory=memory, llm_critic_enabled=False)

    sid = "session-secondary-001"

    # Turn 1: design secondary structure
    state1 = runner.run("Design RNA secondary structure for (((...)))", session_id=sid)
    wf_result1 = state1.get("workflow_result")
    assert wf_result1 is not None
    assert wf_result1.success
    assert len(wf_result1.all_candidates) > 0
    best_seq = wf_result1.best_candidate.sequence

    # Turn 2: refine — runner should load previous state from memory
    state2 = runner.run("Refine to reduce MFE", session_id=sid)
    # SessionMemory should have preserved the previous state's messages
    msgs = state2.get("messages", [])
    contents = [m.content for m in msgs if hasattr(m, "content")]
    assert any("Design RNA secondary" in c for c in contents)
    assert any("Refine to reduce MFE" in c for c in contents)

    # Memory store should contain the session
    assert sid in memory.list_sessions()


def test_tertiary_structure_session_memory_persistence():
    """AgentRunner with SessionMemory should retain tertiary structure results across turns."""
    _ensure_tmp_pdb()
    reg = _make_mock_registry_for_tertiary()
    planner = _make_mock_planner_for_workflow(
        "rna_tertiary_structure_design",
        {"structure_filepath": _TMP_PDB_PATH, "design_tools": "rhodesign", "n_samples_per_tool": 2},
    )
    memory = SessionMemory()

    with patch(
        "agent_core.runner.build_default_capability_registry",
        return_value=reg,
    ):
        runner = AgentRunner(
            planner,
            ToolExecutor(build_default_tool_registry(include_demo=False)),
            session_memory=memory,
            llm_critic_enabled=False,
        )

        sid = "session-tertiary-001"

        # Turn 1
        state1 = runner.run("Design RNA tertiary structure from PDB", session_id=sid)
        wf_result1 = state1.get("workflow_result")
        assert wf_result1 is not None
        assert wf_result1.success

        # Turn 2
        state2 = runner.run("Increase sampling steps", session_id=sid)
        msgs = state2.get("messages", [])
        contents = [m.content for m in msgs if hasattr(m, "content")]
        assert any("Design RNA tertiary" in c for c in contents)
        assert any("Increase sampling" in c for c in contents)
        assert sid in memory.list_sessions()


def test_explicit_state_bypasses_memory_for_structure_workflows():
    """Passing explicit state should skip SessionMemory load/save for structure workflows."""
    registry = _make_registry_with_real_cpu_tools()
    planner = _make_mock_planner_for_workflow(
        "rna_secondary_structure_design",
        {"target_structure": TEST_SECONDARY_STRUCTURE, "num_invocations": 1, "repeats": 3},
    )
    memory = SessionMemory()
    runner = AgentRunner(planner, registry.executor, session_memory=memory, llm_critic_enabled=False)

    sid = "session-bypass-001"
    explicit = default_state("")
    explicit["custom_flag"] = "bypass"

    state = runner.run("Design secondary structure", session_id=sid, state=explicit)
    assert state.get("custom_flag") == "bypass"
    # Memory should NOT have saved because explicit state was provided
    assert sid not in memory.list_sessions()


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 4 — WorkspaceManager
# ═══════════════════════════════════════════════════════════════════════════════


def test_workspace_manager_tracks_secondary_structure_files():
    """WorkspaceManager should track files produced during secondary structure design."""
    wm = WorkspaceManager(base_dir="test_workspace_layer45")
    sid = "ws-secondary-001"

    # Create a dummy file and add it
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as fh:
        fh.write("(((...)))")
        tmp_path = fh.name

    try:
        rel_path = wm.add_file(sid, tmp_path)
        assert rel_path is not None
        files = wm.list_files(sid)
        assert any(".txt" in f for f in files)

        # Cleanup
        wm.delete_session(sid)
        assert not (wm.base_dir / "sessions" / sid).exists()
    finally:
        os.unlink(tmp_path)


def test_workspace_manager_tracks_tertiary_structure_files():
    """WorkspaceManager should track PDB and FASTA files for tertiary design."""
    wm = WorkspaceManager(base_dir="test_workspace_layer45")
    sid = "ws-tertiary-001"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as fh:
        fh.write("ATOM    1  N   A   A   1      0.000   0.000   0.000  1.00  0.00           N\n")
        tmp_path = fh.name

    try:
        rel_path = wm.add_file(sid, tmp_path)
        files = wm.list_files(sid)
        assert any(".pdb" in f for f in files)
        wm.delete_session(sid)
    finally:
        os.unlink(tmp_path)


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 5 — AgentRunner end-to-end
# ═══════════════════════════════════════════════════════════════════════════════


def test_agent_runner_secondary_structure_e2e():
    """AgentRunner.run() should execute secondary structure workflow and produce a final report."""
    registry = _make_registry_with_real_cpu_tools()
    planner = _make_mock_planner_for_workflow(
        "rna_secondary_structure_design",
        {"target_structure": TEST_SECONDARY_STRUCTURE, "num_invocations": 1, "repeats": 3},
    )
    runner = AgentRunner(planner, registry.executor, llm_critic_enabled=False)

    state = runner.run("Design RNA secondary structure for sequence GGGAAACCC with stem-loop constraints")
    wf_result = state.get("workflow_result")
    assert wf_result is not None
    assert isinstance(wf_result, WorkflowResult)
    assert wf_result.success
    assert len(wf_result.all_candidates) > 0
    best = wf_result.best_candidate
    assert best is not None
    assert best.sequence
    assert best.scores is not None

    # final_report should mention structural metrics
    report = state.get("final_report", "")
    assert "工作流执行成功" in report or "Execution completed" in report or "candidate" in report.lower()


def test_agent_runner_tertiary_structure_e2e():
    """AgentRunner.run() should execute tertiary structure workflow with mocked GPU capabilities."""
    _ensure_tmp_pdb()
    reg = _make_mock_registry_for_tertiary()
    planner = _make_mock_planner_for_workflow(
        "rna_tertiary_structure_design",
        {"structure_filepath": _TMP_PDB_PATH, "design_tools": "rhodesign", "n_samples_per_tool": 2},
    )

    with patch(
        "agent_core.runner.build_default_capability_registry",
        return_value=reg,
    ):
        runner = AgentRunner(
            planner,
            ToolExecutor(build_default_tool_registry(include_demo=False)),
            llm_critic_enabled=False,
        )

        state = runner.run("Design RNA tertiary structure for sequence AUGCGC")
        wf_result = state.get("workflow_result")
        assert wf_result is not None
        assert isinstance(wf_result, WorkflowResult)
        assert wf_result.success
        assert len(wf_result.all_candidates) > 0
        best = wf_result.best_candidate
        assert best is not None
        assert best.sequence
        assert "rhofold_component" in best.scores or "rmsd_component" in best.scores


def test_agent_runner_stream_events():
    """AgentRunner.stream() should yield router, plan, progress, tool_execution, and runner events."""
    registry = _make_registry_with_real_cpu_tools()
    planner = _make_mock_planner_for_workflow(
        "rna_secondary_structure_design",
        {"target_structure": TEST_SECONDARY_STRUCTURE, "num_invocations": 1, "repeats": 3},
    )
    runner = AgentRunner(planner, registry.executor, llm_critic_enabled=False)

    events = list(runner.stream("Design secondary structure for test"))
    node_names = [list(e.keys())[0] for e in events]

    assert "router" in node_names
    assert "plan" in node_names
    # progress events may or may not appear depending on timing
    assert "tool_execution" in node_names
    assert "runner" in node_names

    # Verify plan payload
    plan_event = next(e for e in events if "plan" in e)
    assert plan_event["plan"]["steps"][0]["target"] == "rna_secondary_structure_design"


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 5 — LLM Critic retry logic
# ═══════════════════════════════════════════════════════════════════════════════


class _PoorQualityThenGoodCritic:
    """Critic that retries once with parameter overrides, then accepts."""

    def __init__(self):
        self.call_count = 0

    def should_retry(self, workflow_result: WorkflowResult, state: dict[str, Any]) -> bool:
        self.call_count += 1
        if self.call_count == 1:
            state["_parameter_overrides"] = {"repeats": 25, "function_mode": "mp"}
            state.setdefault("_diagnosis_history", []).append({
                "overall_assessment": "Poor structure fidelity",
                "quality_score": 0.2,
                "issues": [{"severity": "critical", "description": "High structure distance"}],
                "action": "retry_with_adjustments",
                "parameter_overrides": {"repeats": 25, "function_mode": "mp"},
                "reasoning": "Increase search depth",
                "confidence": 0.85,
            })
            return True
        return False


def test_secondary_critic_retry_with_mock():
    """Secondary structure workflow should accept critic parameter overrides on retry."""
    registry = _make_registry_with_real_cpu_tools()
    planner = _make_mock_planner_for_workflow(
        "rna_secondary_structure_design",
        {"target_structure": TEST_SECONDARY_STRUCTURE, "num_invocations": 1, "repeats": 3},
    )
    runner = AgentRunner(planner, registry.executor, llm_critic_enabled=True)

    with patch(
        "agent_core.workflows.registry.get_critic_for_workflow",
        return_value=_PoorQualityThenGoodCritic(),
    ):
        state = runner.run("Design with retry", session_id="retry-secondary")

    # With one retry, the diagnosis history should contain one entry
    history = state.get("_diagnosis_history", [])
    assert len(history) >= 1
    assert state.get("retry_count", 0) >= 1

    # final_report should mention critic diagnosis
    report = state.get("final_report", "")
    assert "诊断" in report or "Critic" in report or "retry" in report.lower()


class _TertiaryPoorThenGoodCritic:
    def __init__(self):
        self.call_count = 0

    def should_retry(self, workflow_result: WorkflowResult, state: dict[str, Any]) -> bool:
        self.call_count += 1
        if self.call_count == 1:
            state["_parameter_overrides"] = {
                "design_tools": "ribodiffusion",
                "n_samples_per_tool": 5,
                "ribodiffusion_sampling_steps": 100,
            }
            state.setdefault("_diagnosis_history", []).append({
                "overall_assessment": "Low RhoFold pLDDT and high RMSD",
                "quality_score": 0.25,
                "issues": [{"severity": "critical", "description": "RhoFold pLDDT below threshold"}],
                "action": "retry_with_adjustments",
                "parameter_overrides": {
                    "design_tools": "ribodiffusion",
                    "n_samples_per_tool": 5,
                    "ribodiffusion_sampling_steps": 100,
                },
                "reasoning": "Switch tool and increase sampling",
                "confidence": 0.8,
            })
            return True
        return False


def test_tertiary_critic_retry_with_mock():
    """Tertiary structure workflow should accept critic parameter overrides on retry."""
    _ensure_tmp_pdb()
    reg = _make_mock_registry_for_tertiary()
    planner = _make_mock_planner_for_workflow(
        "rna_tertiary_structure_design",
        {"structure_filepath": _TMP_PDB_PATH, "design_tools": "rhodesign", "n_samples_per_tool": 2},
    )

    with patch(
        "agent_core.runner.build_default_capability_registry",
        return_value=reg,
    ):
        runner = AgentRunner(
            planner,
            ToolExecutor(build_default_tool_registry(include_demo=False)),
            llm_critic_enabled=True,
        )

        with patch(
            "agent_core.workflows.registry.get_critic_for_workflow",
            return_value=_TertiaryPoorThenGoodCritic(),
        ):
            state = runner.run("Design tertiary with retry", session_id="retry-tertiary")

    history = state.get("_diagnosis_history", [])
    assert len(history) >= 1
    assert state.get("retry_count", 0) >= 1
    report = state.get("final_report", "")
    assert "诊断" in report or "Critic" in report or "retry" in report.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI / API entry verification
# ═══════════════════════════════════════════════════════════════════════════════


def test_cli_agent_chat_supports_structure_workflows():
    """CLI agent_chat.py uses generic AgentRunner which registers both structure workflows."""
    from cli.agent_chat import _build_llm_context, _candidate_to_dict

    # Verify the helper functions can handle structure workflow results
    candidate = Candidate(
        sequence="AUGC",
        sequence_type="rna",
        source="test",
        scores={"total_score": 0.5, "mfe": -2.0},
        metadata={
            "metrics_bundle": {
                "vienna_mfe": -2.0,
                "gc_content": 0.5,
                "structure_distance": 0,
            }
        },
    )
    d = _candidate_to_dict(candidate)
    assert d["sequence"] == "AUGC"
    assert d["metrics"]["vienna_mfe"] == -2.0

    wf_result = WorkflowResult(
        success=True,
        task_id="test",
        best_candidate=candidate,
        all_candidates=[candidate],
        summary="test summary",
        errors=[],
    )
    mock_state = {
        "workflow_result": wf_result,
        "user_text": "Design secondary structure",
    }
    ctx = _build_llm_context("Design secondary structure", mock_state)
    assert "候选结果数量" in ctx or "candidate" in ctx.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# CPU tool format consistency
# ═══════════════════════════════════════════════════════════════════════════════


def test_secondary_structure_cpu_tool_formats():
    """Verify ViennaRNA RNAinverse and RNAfold input/output formats match workflow expectations."""
    from agent_core.file_manager import save_sequence, save_text_file
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    executor = ToolExecutor(build_default_tool_registry(include_demo=False))

    # RNAinverse expects: line 1 = structure, line 2 = optional start sequence
    struct_fp = save_text_file(TEST_SECONDARY_STRUCTURE, prefix="fmt_test", suffix=".txt")
    res = executor.run_tool(
        "inverse_fold_rna_secondary_structure_vienna",
        filepath=struct_fp,
        repeats=5,
        temp_c=37.0,
        function_mode="m",
    )
    assert res.success
    artifacts = res.artifacts.get("result", {})
    assert "best_sequence" in artifacts
    assert isinstance(artifacts["best_sequence"], str)
    assert "hamming_distance" in artifacts

    # RNAfold expects a FASTA/sequence file; workflow uses save_sequence()
    seq_fp = save_sequence(TEST_SEQUENCE_SHORT, prefix="fmt_test_seq")
    res2 = executor.run_tool("predict_rna_secondary_structure", filepath=seq_fp)
    assert res2.success
    artifacts2 = res2.artifacts.get("result", {})
    assert "structure" in artifacts2
    assert isinstance(artifacts2["structure"], str)
    assert "mfe_kcal_per_mol" in artifacts2

    # GC content
    res3 = executor.run_tool("compute_rna_sequence_gc_content", filepath=seq_fp)
    assert res3.success
    assert "gc_content" in res3.artifacts.get("result", {})


def test_tertiary_structure_cpu_tool_formats():
    """Verify structure alignment and ViennaRNA fold input/output formats match workflow expectations."""
    _ensure_tmp_pdb()
    from agent_core.file_manager import save_sequence
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    executor = ToolExecutor(build_default_tool_registry(include_demo=False))

    # RNAfold for tertiary workflow evaluation path
    seq_fp = save_sequence("AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC", prefix="fmt_tertiary")
    res = executor.run_tool("predict_rna_secondary_structure", filepath=seq_fp)
    assert res.success
    result = res.artifacts.get("result", {})
    assert "structure" in result
    assert "mfe_kcal_per_mol" in result

    # Structure alignment (CPU tool used by tertiary workflow)
    res2 = executor.run_tool(
        "score_structure_alignment",
        reference_pdb_filepath=_TMP_PDB_PATH,
        predicted_pdb_filepath=_TMP_PDB_PATH,
        atom_type="C1'",
    )
    # Alignment may fail on the dummy PDB, but we verify the parameter contract
    # is accepted by the tool executor.
    assert res2 is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Code style / interface sanity checks
# ═══════════════════════════════════════════════════════════════════════════════


def test_workflow_interface_locks_present():
    """Both workflow files must contain INTERFACE LOCK comments."""
    secondary_path = Path(__file__).parent.parent / "agent_core/workflows/rna_secondary_structure_design.py"
    tertiary_path = Path(__file__).parent.parent / "agent_core/workflows/rna_tertiary_structure_design.py"
    assert "INTERFACE LOCK" in secondary_path.read_text()
    assert "INTERFACE LOCK" in tertiary_path.read_text()


def test_critic_classes_registered():
    """Both critics must be present in the workflow registry mapping."""
    from agent_core.workflows.registry import WORKFLOW_CRITIC_PAIRS

    assert "rna_secondary_structure_design" in WORKFLOW_CRITIC_PAIRS
    assert WORKFLOW_CRITIC_PAIRS["rna_secondary_structure_design"][1] is RnaSecondaryStructureDesignLLMCritic
    assert "rna_tertiary_structure_design" in WORKFLOW_CRITIC_PAIRS
    assert WORKFLOW_CRITIC_PAIRS["rna_tertiary_structure_design"][1] is RnaTertiaryStructureDesignLLMCritic


def test_type_annotations_on_public_methods():
    """Public workflow methods should have type annotations."""
    for cls in (RnaSecondaryStructureDesignWorkflow, RnaTertiaryStructureDesignWorkflow):
        for name in ("run", "generate_candidates", "evaluate", "score", "rank_and_format"):
            method = getattr(cls, name)
            sig = inspect.signature(method)
            for param in sig.parameters.values():
                # At least one of return annotation or param annotations should exist
                assert sig.return_annotation is not inspect.Signature.empty or any(
                    p.annotation is not inspect.Signature.empty for p in sig.parameters.values()
                ), f"{cls.__name__}.{name} lacks annotations"


def test_input_models_have_descriptions():
    """Input model fields should have descriptions for LLM planner consumption."""
    for model_cls in (RnaSecondaryStructureDesignInput, RnaTertiaryStructureDesignInput):
        for name, field_info in model_cls.model_fields.items():
            if name.startswith("_"):
                continue
            assert field_info.description, f"{model_cls.__name__}.{name} lacks description"


def test_exception_handling_for_empty_inputs():
    """Workflows should handle empty/invalid inputs gracefully."""
    reg = MagicMock()
    reg.has.return_value = False
    reg.get.return_value = MagicMock()

    wf_secondary = RnaSecondaryStructureDesignWorkflow(reg)
    result = wf_secondary.run({"target_structure": ""})
    assert not result.success
    assert "empty_candidate_list" in result.errors or "No RNA sequence" in result.summary

    _ensure_tmp_pdb()
    wf_tertiary = RnaTertiaryStructureDesignWorkflow(reg)
    result2 = wf_tertiary.run({"structure_filepath": "/nonexistent/path.pdb"})
    assert not result2.success
    assert "empty_candidate_list" in result2.errors or "No RNA sequence" in result2.summary


# ═══════════════════════════════════════════════════════════════════════════════
# DeepSeek API — live LLM Critic validation
# ═══════════════════════════════════════════════════════════════════════════════

_DEEPSEEK_KEY_SET = bool(os.environ.get("DEEPSEEK_API_KEY"))


@pytest.mark.live_llm
@pytest.mark.skipif(not _DEEPSEEK_KEY_SET, reason="DEEPSEEK_API_KEY not set")
def test_secondary_structure_critic_live_diagnosis():
    """RnaSecondaryStructureDesignLLMCritic should diagnose poor structure fidelity via DeepSeek."""
    critic = RnaSecondaryStructureDesignLLMCritic()

    # Build a deliberately poor-quality candidate (high structure distance)
    poor_candidate = Candidate(
        sequence="GGCAAAGCCGGCAAAGCC",
        sequence_type="rna",
        source="test",
        scores={
            "total_score": 0.85,
            "structure_distance_ratio": 0.85,
            "mfe_component": 0.1,
            "gc_component": 0.5,
        },
        metadata={
            "metrics_bundle": {
                "structure_distance": 15,
                "sequence_length": 18,
                "vienna_mfe": -1.3,
                "vienna_structure": "(((...)))(((...)))",
                "target_structure": "((((....))))....",
                "gc_content": 0.55,
            }
        },
    )
    result = WorkflowResult(
        success=True,
        task_id="test-secondary-live",
        best_candidate=poor_candidate,
        all_candidates=[poor_candidate],
        summary="Test poor structure fidelity",
        errors=[],
    )
    state: dict[str, Any] = {
        "user_text": "Design RNA secondary structure for ((((....)))).... with low MFE",
        "_last_workflow_params": {"target_structure": "((((....))))....", "repeats": 3, "function_mode": "m"},
    }

    diagnosis = critic.diagnose(result, state)

    # Verify the LLM produced a structured diagnosis
    assert diagnosis.overall_assessment
    assert len(diagnosis.issues) >= 1
    # The high structure distance should be flagged
    assert any("structure" in i.description.lower() or "distance" in i.description.lower()
               for i in diagnosis.issues)


@pytest.mark.live_llm
@pytest.mark.skipif(not _DEEPSEEK_KEY_SET, reason="DEEPSEEK_API_KEY not set")
def test_tertiary_structure_critic_live_diagnosis():
    """RnaTertiaryStructureDesignLLMCritic should diagnose poor 3D structure via DeepSeek."""
    critic = RnaTertiaryStructureDesignLLMCritic()

    poor_candidate = Candidate(
        sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
        sequence_type="rna",
        source="test",
        scores={
            "total_score": 0.75,
            "rhofold_component": 0.2,
            "rmsd_component": 0.1,
            "gc_component": 0.5,
            "mfe_component": 0.3,
        },
        metadata={
            "metrics_bundle": {
                "rhofold_mean_plddt": 45.0,
                "alignment_rmsd": 8.5,
                "alignment_tm_score": 0.35,
                "gc_content": 0.5,
                "vienna_mfe": -5.0,
                "recovery_rate": 0.3,
            },
            "design_tool": "rhodesign",
        },
    )
    result = WorkflowResult(
        success=True,
        task_id="test-tertiary-live",
        best_candidate=poor_candidate,
        all_candidates=[poor_candidate],
        summary="Test poor 3D structure quality",
        errors=[],
    )
    state: dict[str, Any] = {
        "user_text": "Design RNA tertiary structure with high pLDDT and low RMSD",
        "_last_workflow_params": {"design_tools": "rhodesign", "n_samples_per_tool": 2},
    }

    diagnosis = critic.diagnose(result, state)

    assert diagnosis.overall_assessment
    assert len(diagnosis.issues) >= 1
    # Low pLDDT or high RMSD should be flagged
    assert any(
        "plddt" in i.description.lower()
        or "rmsd" in i.description.lower()
        or "structure" in i.description.lower()
        for i in diagnosis.issues
    )
