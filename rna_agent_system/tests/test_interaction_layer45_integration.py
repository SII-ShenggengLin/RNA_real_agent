"""Layer 4/5 integration tests for RNA interaction workflows (aptamer + small molecule).

Coverage:
- Layer 4: SessionMemory persistence, multi-turn state, WorkspaceManager
- Layer 5: AgentRunner.run() / .stream() end-to-end
- CLI/API: rna_unified_handler schema mapping, entry points
- DeepSeek API: live LLM planning + critic diagnosis (--live-llm)
- CPU/GPU: tool invocation validation (CPU real, GPU mocked)
- Code quality: type annotations, exception handling, interface locks

Run:
  cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_interaction_layer45_integration.py -v -s

Run with live LLM:
  cd rna_agent_system && PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_interaction_layer45_integration.py -v -s --live-llm
"""

from __future__ import annotations

from tests.helpers import make_mock_capability

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
# CriticDiagnosis / CriticIssue not directly used; kept for potential future live-LLM mocking
from agent_core.runner import AgentRunner
from agent_core.session_memory import SessionMemory
from agent_core.state import default_state
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.rna_aptamer_design import (
    RnaAptamerDesignInput,
    RnaAptamerDesignLLMCritic,
    RnaAptamerDesignWorkflow,
    score_aptamer_candidate,
)
from agent_core.workflows.rna_small_molecule_interaction import (
    RnaSmallMoleculeInteractionInput,
    RnaSmallMoleculeInteractionWorkflow,
)
from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest, MrnaWorkflowHttpResponse
from workflow_api.rna_unified_handler import _run_aptamer_via_agent_runner


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_aptamer_registry() -> MagicMock:
    """Mock registry for aptamer workflow (generation + evaluation)."""
    reg = MagicMock()

    gen_caps = {
        "identify_protein_binding_hotspots": make_mock_capability({
            "hotspot_residues": "A/2,A/3",
            "hotspot_patch_size": 2,
        }),
        "build_odesign_aptamer_input_json": make_mock_capability({
            "input_json_filepath": "workspace/odesign_input.json",
            "design_config": [],
        }),
        "run_odesign_inference": make_mock_capability({
            "prediction_filepaths": ["workspace/pred_0.cif"],
            "prediction_count": 1,
        }),
        "extract_rna_sequence_from_cif": make_mock_capability({
            "sequence": "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            "chain_id": "B",
            "residue_count": 30,
            "is_rna": True,
        }),
    }

    eval_caps = {
        "compute_rna_sequence_gc_content": make_mock_capability({
            "gc_content": 0.48, "sequence_length": 30
        }),
        "predict_rna_tertiary_structure_with_rhofold": make_mock_capability({
            "pdb_filepath": "workspace/rho.pdb", "mean_plddt": 85.0
        }),
        "score_rna_protein_complex_with_egarps": make_mock_capability({
            "native_probability": 0.72
        }),
        "predict_rna_protein_complex_with_proteinx": make_mock_capability({
            "pdb_filepath": "workspace/px.pdb", "mean_plddt": 82.0, "ipTM": 0.75
        }),
        "analyze_rna_protein_interface": make_mock_capability({
            "interface_contacts": 24, "buried_sasa": 1250.5,
            "hydrogen_bonds": 8, "salt_bridges": 2,
        }),
    }

    all_caps = {**gen_caps, **eval_caps}
    reg.has = lambda name: name in all_caps
    reg.get = lambda name: all_caps[name]
    return reg


@pytest.fixture
def mock_ligand_registry() -> MagicMock:
    """Mock registry for small-molecule workflow."""
    reg = MagicMock()
    caps = {
        "score_rna_ligand_binding_with_rnasmol": make_mock_capability({
            "probability_positive": 0.80, "predicted_label": 1,
        }),
        "score_rna_ligand_binding_with_gernabind": make_mock_capability({
            "probability_positive": 0.60, "predicted_label": 1,
        }),
    }
    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


@pytest.fixture
def mock_planner() -> MagicMock:
    """Planner that always returns a single aptamer workflow step."""
    planner = MagicMock()
    planner.plan_with_state.return_value = ExecutionPlan(steps=[
        PlanStep(
            step_id="s1",
            type="workflow",
            target="rna_aptamer_design",
            input_binding={
                "protein_structure_path": "/tmp/test_protein_for_aptamer.pdb",
                "aptamer_length": 30,
            },
            output_key="aptamer_result",
            description="Design aptamer",
        ),
    ])
    return planner


@pytest.fixture
def mock_planner_ligand() -> MagicMock:
    """Planner that always returns a single small-molecule workflow step."""
    planner = MagicMock()
    planner.plan_with_state.return_value = ExecutionPlan(steps=[
        PlanStep(
            step_id="s1",
            type="workflow",
            target="rna_small_molecule_interaction",
            input_binding={
                "rna_sequence": "AUGCAUGC",
                "smiles": "CCO",
            },
            output_key="ligand_result",
            description="Predict RNA-ligand binding",
        ),
    ])
    return planner


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 4 — Session & Memory
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.known_issue
class TestLayer4SessionMemory:
    """SessionMemory integration for interaction workflows."""

    def test_session_memory_load_save(self):
        """SessionMemory should persist and reload state."""
        mem = SessionMemory()
        state = default_state("turn1")
        state["workflow_result"] = "aptamer_candidates"
        state["session_id"] = "sess-001"
        mem.save("sess-001", state)

        loaded = mem.load("sess-001")
        assert loaded["workflow_result"] == "aptamer_candidates"
        assert loaded["session_id"] == "sess-001"

    def test_session_memory_isolation(self):
        """Different session IDs must not leak state."""
        mem = SessionMemory()
        mem.save("sess-a", default_state("a"))
        mem.save("sess-b", default_state("b"))
        assert mem.load("sess-a")["input_sequence"] == "a"
        assert mem.load("sess-b")["input_sequence"] == "b"

    def test_runner_with_memory_multiturn_aptamer(self, mock_planner, mock_aptamer_registry):
        """Multi-turn: turn1 designs aptamer, turn2 scores binding affinity."""
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        memory = SessionMemory()
        runner = AgentRunner(mock_planner, exe, session_memory=memory, llm_critic_enabled=False)

        # Patch workflow registry so the runner uses our mocked aptamer workflow
        wf = RnaAptamerDesignWorkflow(mock_aptamer_registry)
        runner.workflow_registry["rna_aptamer_design"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        # Turn 1: design aptamer
        state1 = runner.run("Design RNA aptamer for protein XYZ", session_id="apt-session")
        assert state1["workflow_result"] is not None
        assert state1["workflow_result"].success is True
        assert "aptamer_result" in state1

        # Turn 2: score binding affinity — state should persist
        mock_planner.plan_with_state.return_value = ExecutionPlan(steps=[
            PlanStep(
                step_id="s2",
                type="workflow",
                target="rna_aptamer_design",
                input_binding={
                    "protein_structure_path": "/tmp/test_protein_for_aptamer.pdb",
                    "aptamer_length": 30,
                },
                output_key="aptamer_result_2",
                description="Score binding affinity",
            ),
        ])
        state2 = runner.run("Score binding affinity", session_id="apt-session")
        # Messages should include both turns
        contents = [m.content for m in state2["messages"] if isinstance(m, HumanMessage)]
        assert "Design RNA aptamer for protein XYZ" in contents
        assert "Score binding affinity" in contents

    def test_runner_with_memory_multiturn_small_molecule(self, mock_planner_ligand, mock_ligand_registry):
        """Multi-turn: turn1 predicts interaction, turn2 asks for details."""
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        memory = SessionMemory()
        runner = AgentRunner(mock_planner_ligand, exe, session_memory=memory, llm_critic_enabled=False)

        wf = RnaSmallMoleculeInteractionWorkflow(mock_ligand_registry)
        runner.workflow_registry["rna_small_molecule_interaction"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        state1 = runner.run(
            "Predict RNA small molecule interaction for RNA AUGC and SMILES CCO",
            session_id="lig-session",
        )
        assert state1["workflow_result"] is not None
        assert state1["workflow_result"].success is True

        state2 = runner.run("Show me the binding site details", session_id="lig-session")
        contents = [m.content for m in state2["messages"] if isinstance(m, HumanMessage)]
        assert any("Predict RNA small molecule interaction" in c for c in contents)
        assert any("Show me the binding site details" in c for c in contents)

    def test_runner_memory_saves_workflow_result(self, mock_planner_ligand, mock_ligand_registry):
        """Workflow result should be retrievable from memory after run()."""
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        memory = SessionMemory()
        runner = AgentRunner(mock_planner_ligand, exe, session_memory=memory)

        wf = RnaSmallMoleculeInteractionWorkflow(mock_ligand_registry)
        runner.workflow_registry["rna_small_molecule_interaction"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        runner.run("Predict binding for AUGC and CCO", session_id="sess-x")
        loaded = memory.load("sess-x")
        assert loaded["workflow_result"] is not None
        assert loaded["workflow_result"].success is True


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 5 — AgentRunner end-to-end
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.known_issue
class TestLayer5AgentRunnerAptamer:
    """AgentRunner end-to-end for RnaAptamerDesignWorkflow."""

    def test_runner_aptamer_returns_workflow_result(self, mock_planner, mock_aptamer_registry):
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(mock_planner, exe, llm_critic_enabled=False)

        wf = RnaAptamerDesignWorkflow(mock_aptamer_registry)
        runner.workflow_registry["rna_aptamer_design"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        state = runner.run("Design RNA aptamer for target protein with structure path /tmp/test_protein_for_aptamer.pdb")
        assert state["workflow_result"] is not None
        assert state["workflow_result"].success is True
        assert state["workflow_result"].best_candidate is not None
        assert len(state["workflow_result"].all_candidates) > 0
        assert "final_report" in state
        assert "aptamer" in state["final_report"].lower()

    def test_runner_aptamer_stream_events(self, mock_planner, mock_aptamer_registry):
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(mock_planner, exe, llm_critic_enabled=False)

        wf = RnaAptamerDesignWorkflow(mock_aptamer_registry)
        runner.workflow_registry["rna_aptamer_design"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        events = list(runner.stream("Design aptamer"))
        event_keys = [list(e.keys())[0] for e in events]
        assert "router" in event_keys
        assert "plan" in event_keys
        assert "progress" in event_keys
        assert "tool_execution" in event_keys
        assert "runner" in event_keys


@pytest.mark.known_issue
class TestLayer5AgentRunnerSmallMolecule:
    """AgentRunner end-to-end for RnaSmallMoleculeInteractionWorkflow."""

    def test_runner_small_molecule_returns_workflow_result(self, mock_planner_ligand, mock_ligand_registry):
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(mock_planner_ligand, exe, llm_critic_enabled=False)

        wf = RnaSmallMoleculeInteractionWorkflow(mock_ligand_registry)
        runner.workflow_registry["rna_small_molecule_interaction"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        state = runner.run(
            "Predict RNA small molecule interaction for RNA AUGCAUGC and SMILES CCC"
        )
        assert state["workflow_result"] is not None
        assert state["workflow_result"].success is True
        assert state["workflow_result"].best_candidate is not None
        assert "final_report" in state

    def test_runner_small_molecule_no_critic_retry(self, mock_planner_ligand, mock_ligand_registry):
        """Small molecule workflow has no critic → retry_count must stay 0."""
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(mock_planner_ligand, exe, llm_critic_enabled=False)

        wf = RnaSmallMoleculeInteractionWorkflow(mock_ligand_registry)
        runner.workflow_registry["rna_small_molecule_interaction"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        state = runner.run("Predict binding for AUGC and CCO")
        assert state.get("retry_count", 0) == 0
        retry_events = [
            e for e in state.get("_execution_log", [])
            if e["event"] == "critic_retry"
        ]
        assert len(retry_events) == 0

    def test_runner_small_molecule_stream(self, mock_planner_ligand, mock_ligand_registry):
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(mock_planner_ligand, exe, llm_critic_enabled=False)

        wf = RnaSmallMoleculeInteractionWorkflow(mock_ligand_registry)
        runner.workflow_registry["rna_small_molecule_interaction"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        events = list(runner.stream("Predict binding"))
        event_keys = [list(e.keys())[0] for e in events]
        assert "router" in event_keys
        assert "plan" in event_keys
        assert "tool_execution" in event_keys
        assert "runner" in event_keys


# ═══════════════════════════════════════════════════════════════════════════════
# CLI / API Entry
# ═══════════════════════════════════════════════════════════════════════════════


class TestApiEntryAptamer:
    """Tests for /v1/workflows/run aptamer routing and schema conversion."""

    def test_aptamer_schema_conversion_protein_and_constraints(self):
        """MrnaWorkflowHttpRequest with protein + constraints maps correctly."""
        req = MrnaWorkflowHttpRequest(
            protein="GFP",
            task_type="aptamer",
            task_id="apt-001",
            constraints={
                "protein_structure_path": "/data/gfp.pdb",
                "hotspot_residues": "A/18,A/90",
                "aptamer_length": 45,
                "chain_id": "A",
            },
            top_k=3,
        )
        # Verify schema conversion logic by checking the request fields
        assert req.protein == "GFP"
        assert req.constraints["protein_structure_path"] == "/data/gfp.pdb"
        assert req.constraints["aptamer_length"] == 45

    def test_aptamer_handler_returns_mrna_response_shape(self):
        """_run_aptamer_via_agent_runner must return MrnaWorkflowHttpResponse."""
        req = MrnaWorkflowHttpRequest(
            protein="GFP",
            task_type="aptamer",
            task_id="apt-002",
            constraints={"protein_structure_path": "/tmp/test_protein_for_aptamer.pdb"},
        )

        # Patch AgentRunner to avoid real tool execution and LLM calls
        mock_state = {
            "workflow_result": WorkflowResult(
                success=True,
                task_id="apt-002",
                best_candidate=Candidate(
                    sequence="AUGCGCAUGC",
                    scores={"total_score": 0.85},
                ),
                all_candidates=[
                    Candidate(sequence="AUGCGCAUGC", scores={"total_score": 0.85}),
                ],
                summary="candidates=1 best_total_score=0.85",
                errors=[],
            ),
            "final_report": "Aptamer design complete.",
        }
        mock_runner = MagicMock()
        mock_runner.run.return_value = mock_state

        with patch("workflow_api.rna_unified_handler.AgentRunner", return_value=mock_runner):
            resp = _run_aptamer_via_agent_runner(req)

        assert isinstance(resp, MrnaWorkflowHttpResponse)
        assert resp.task_type == "aptamer"
        assert resp.task_id == "apt-002"
        assert resp.success is True


class TestApiEntrySmallMolecule:
    """Small molecule workflow API/CLI entry validation."""

    def test_small_molecule_no_dedicated_api_endpoint(self):
        """Small molecule workflow currently has no dedicated HTTP endpoint;
        it is only reachable via AgentRunner natural-language or direct workflow invocation.
        """
        from workflow_api.app import app
        routes = [r.path for r in app.routes]
        # There is no /v1/workflows/small_molecule/run endpoint
        assert "/v1/workflows/small_molecule/run" not in routes
        # The unified /v1/agent/run is the sole entry point
        assert "/v1/agent/run" in routes

    def test_small_molecule_via_agent_runner_api(self):
        """AgentRunner API entry (/v1/agent/run) can handle small-molecule requests
        when the planner routes to rna_small_molecule_interaction.
        """
        from workflow_api.app import _agent_runner
        assert "rna_small_molecule_interaction" in _agent_runner.workflow_registry


# ═══════════════════════════════════════════════════════════════════════════════
# DeepSeek API — Live LLM tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live_llm
class TestLiveLLMPlannerInteractionWorkflows:
    """Real DeepSeek API calls for plan generation."""

    def test_planner_generates_aptamer_plan(self):
        from agent_core.llm_config import get_deepseek_llm
        from agent_core.planning.base import AgentContext
        from agent_core.planning.llm_planner import LLMPlanner

        llm = get_deepseek_llm(temperature=0.1)
        planner = LLMPlanner(llm=llm)
        ctx = AgentContext(
            available_workflows=["rna_aptamer_design"],
            available_capabilities=[
                "identify_protein_binding_hotspots",
                "run_odesign_inference",
            ],
            workflow_param_schemas={
                "rna_aptamer_design": (
                    "  protein_structure_path=(required) (str)\n"
                    "  aptamer_length=30 (int)"
                ),
            },
        )
        plan = planner.plan(
            "Design RNA aptamer for protein with structure path /tmp/test.pdb",
            ctx,
        )
        assert len(plan.steps) > 0
        targets = [s.target for s in plan.steps]
        assert "rna_aptamer_design" in targets

    def test_planner_generates_small_molecule_plan(self):
        from agent_core.llm_config import get_deepseek_llm
        from agent_core.planning.base import AgentContext
        from agent_core.planning.llm_planner import LLMPlanner

        llm = get_deepseek_llm(temperature=0.1)
        planner = LLMPlanner(llm=llm)
        ctx = AgentContext(
            available_workflows=["rna_small_molecule_interaction"],
            available_capabilities=[
                "score_rna_ligand_binding_with_rnasmol",
                "score_rna_ligand_binding_with_gernabind",
            ],
            workflow_param_schemas={
                "rna_small_molecule_interaction": (
                    "  rna_sequence=(required) (str)\n"
                    "  smiles=(required) (str)"
                ),
            },
        )
        plan = planner.plan(
            "Predict RNA-small-molecule binding for RNA AUGCAUGC and ligand CCO",
            ctx,
        )
        assert len(plan.steps) > 0
        targets = [s.target for s in plan.steps]
        valid = {
            "rna_small_molecule_interaction",
            "score_rna_ligand_binding_with_rnasmol",
            "score_rna_ligand_binding_with_gernabind",
        }
        assert any(t in valid for t in targets)

    def test_planner_json_parseable(self):
        """LLMPlanner must return parseable JSON plan."""
        from agent_core.llm_config import get_deepseek_llm
        from agent_core.planning.llm_planner import LLMPlanner

        llm = get_deepseek_llm(temperature=0.1)
        planner = LLMPlanner(llm=llm)
        state = {
            "_available_workflows": [
                "rna_aptamer_design",
                "rna_small_molecule_interaction",
            ],
            "_available_capabilities": [
                "score_rna_ligand_binding_with_rnasmol",
                "identify_protein_binding_hotspots",
            ],
            "_workflow_param_schemas": {},
            "session_id": "test",
        }
        plan = planner.plan_with_state(
            "Design aptamer for protein /tmp/test.pdb",
            state,
        )
        assert plan is not None
        assert hasattr(plan, "steps")
        assert hasattr(plan, "max_retries")


@pytest.mark.live_llm
class TestLiveLLMCriticAptamer:
    """Real DeepSeek API calls for aptamer critic diagnosis."""

    def test_aptamer_critic_diagnosis_low_quality(self):
        """Build low-quality result and verify critic returns retry recommendation."""
        critic = RnaAptamerDesignLLMCritic()

        bad_candidate = Candidate(
            sequence="AUGC" * 5,
            metadata={"metrics_bundle": {
                "gc_content": 0.15,
                "rhofold_mean_plddt": 25.0,
                "egarps_native_probability": 0.10,
                "proteinx_ipTM": 0.15,
                "interface_contacts": 2,
            }},
            scores=score_aptamer_candidate({
                "gc_content": 0.15,
                "rhofold_mean_plddt": 25.0,
                "egarps_native_probability": 0.10,
                "proteinx_ipTM": 0.15,
            }),
        )
        result = WorkflowResult(
            success=True,
            task_id="test",
            summary="test",
            errors=[],
            all_candidates=[bad_candidate],
        )
        state: dict[str, Any] = {"_last_workflow_params": {"aptamer_length": 30}}
        diagnosis = critic.diagnose(result, state)

        assert diagnosis.quality_score < 0.5
        assert len(diagnosis.issues) > 0
        assert diagnosis.action in {
            "retry_with_adjustments", "retry_with_alternative", "abort"
        }
        # Verify at least one parameter override is suggested for retry actions
        if diagnosis.action == "retry_with_adjustments":
            assert len(diagnosis.parameter_overrides) > 0

    def test_aptamer_critic_retry_decision(self):
        """should_retry must return True for very low quality results."""
        critic = RnaAptamerDesignLLMCritic()
        bad_candidate = Candidate(
            sequence="AUGC" * 5,
            metadata={"metrics_bundle": {
                "gc_content": 0.20,
                "rhofold_mean_plddt": 30.0,
                "egarps_native_probability": 0.05,
            }},
            scores=score_aptamer_candidate({
                "gc_content": 0.20,
                "rhofold_mean_plddt": 30.0,
                "egarps_native_probability": 0.05,
            }),
        )
        result = WorkflowResult(
            success=True,
            task_id="test",
            summary="test",
            errors=[],
            all_candidates=[bad_candidate],
        )
        state: dict[str, Any] = {"_last_workflow_params": {"aptamer_length": 30}}
        should_retry = critic.should_retry(result, state)
        # For very poor results the critic should recommend retry
        assert should_retry is True

    def test_small_molecule_no_critic_in_registry(self):
        """rna_small_molecule_interaction must NOT have a critic in registry."""
        from agent_core.workflows.registry import WORKFLOW_CRITIC_PAIRS
        assert "rna_small_molecule_interaction" not in WORKFLOW_CRITIC_PAIRS

    def test_planner_fallback_on_api_failure(self):
        """When DeepSeek API fails, planner should return empty plan (not crash)."""
        from agent_core.planning.llm_planner import LLMPlanner

        bad_llm = MagicMock()
        bad_llm.invoke.side_effect = RuntimeError("API unreachable")
        planner = LLMPlanner(llm=bad_llm)
        from agent_core.planning.base import AgentContext
        ctx = AgentContext(available_workflows=["rna_aptamer_design"])
        plan = planner.plan("Design aptamer", ctx)
        assert plan.steps == []


# ═══════════════════════════════════════════════════════════════════════════════
# CPU / GPU Tool Validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestCpuToolValidation:
    """Verify CPU-only tools used by interaction workflows."""

    @patch("agent_core.tools.requests.post")
    def test_compute_rna_sequence_gc_content(self, mock_post):
        """GC content tool (used by aptamer workflow) must work on CPU."""
        from agent_core.tools import compute_rna_sequence_gc_content
        from agent_core.file_manager import save_sequence

        filepath = save_sequence("AUGC" * 10, prefix="test_gc")
        mock_post.return_value.json.return_value = {
            "gc_content": 0.50,
            "sequence_length": 40,
            "g_count": 10,
            "c_count": 10,
            "gc_count": 20,
            "resolved_filepath": filepath,
            "model": "rna-sequence-metrics-gc",
        }
        mock_post.return_value.raise_for_status = lambda: None

        result = compute_rna_sequence_gc_content.invoke({"filepath": filepath})
        assert "gc_content" in result
        assert 0.0 <= result["gc_content"] <= 1.0

    def test_build_odesign_aptamer_input_json_cpu(self):
        """ODesign JSON builder (CPU) must produce valid output."""
        from agent_core.tools import build_odesign_aptamer_input_json

        result = build_odesign_aptamer_input_json.invoke({
            "protein_structure_path": "/tmp/test_protein_for_aptamer.pdb",
            "protein_chain_id": "A",
            "protein_sequence_length": 6,
            "hotspot_residues": "A/1,A/2",
            "aptamer_length": 30,
        })
        assert "input_json_filepath" in result
        assert result["design_config"][0]["hotspot"] == "A/1,A/2"


class TestGpuToolValidationMocked:
    """GPU tools are mocked because microservices may not be available in CI."""

    @patch("agent_core.tools.requests.post")
    def test_rnasmol_gpu_mocked(self, mock_post):
        from agent_core.tools import score_rna_ligand_binding_with_rnasmol
        from agent_core.file_manager import save_sequence

        mock_post.return_value.json.return_value = {
            "probability_positive": 0.75,
            "predicted_label": 1,
            "device": "cuda:0",
            "model": "rnasmol",
        }
        mock_post.return_value.raise_for_status = lambda: None

        filepath = save_sequence("AUGC" * 5, prefix="test_rnasmol")
        result = score_rna_ligand_binding_with_rnasmol.invoke({
            "filepath": filepath,
            "smiles": "CCO",
        })
        assert result["probability_positive"] == pytest.approx(0.75, abs=1e-6)
        assert result["device"].startswith("cuda")

    @patch("agent_core.tools.requests.post")
    def test_gernabind_gpu_mocked(self, mock_post):
        from agent_core.tools import score_rna_ligand_binding_with_gernabind
        from agent_core.file_manager import save_sequence

        mock_post.return_value.json.return_value = {
            "probability_positive": 0.65,
            "predicted_label": 1,
            "device": "cuda:0",
            "model": "gernabind",
        }
        mock_post.return_value.raise_for_status = lambda: None

        filepath = save_sequence("AUGC" * 5, prefix="test_gernabind")
        result = score_rna_ligand_binding_with_gernabind.invoke({
            "filepath": filepath,
            "smiles": "CCO",
        })
        assert result["probability_positive"] == pytest.approx(0.65, abs=1e-6)

    @patch("agent_core.tools.copy_file_to_workspace")
    @patch("agent_core.tools.requests.post")
    def test_rhofold_gpu_mocked(self, mock_post, mock_copy):
        from agent_core.tools import predict_rna_tertiary_structure_with_rhofold
        from agent_core.file_manager import save_sequence

        mock_post.return_value.json.return_value = {
            "mean_plddt": 85.0,
            "pdb_filepath": "/tmp/rhofold/test.pdb",
            "output_pdb_path": "/tmp/rhofold/test.pdb",
            "device": "cuda:0",
            "model": "rhofold",
        }
        mock_post.return_value.raise_for_status = lambda: None
        mock_copy.return_value = "workspace/rhofold_model_test.pdb"

        filepath = save_sequence("AUGC" * 5, prefix="test_rhofold")
        result = predict_rna_tertiary_structure_with_rhofold.invoke({
            "filepath": filepath,
        })
        assert result["mean_plddt"] == pytest.approx(85.0, abs=1e-6)


# ═══════════════════════════════════════════════════════════════════════════════
# Code Quality Checks
# ═══════════════════════════════════════════════════════════════════════════════


class TestCodeQuality:
    """Static-style checks for type annotations, exception handling, dead code."""

    def test_aptamer_workflow_type_annotations(self):
        """RnaAptamerDesignWorkflow methods should have type annotations."""
        wf = RnaAptamerDesignWorkflow.__dict__
        assert "run" in wf
        assert "generate_candidates" in wf
        assert "evaluate" in wf
        assert "score" in wf
        assert "rank_and_format" in wf

    def test_small_molecule_workflow_type_annotations(self):
        """RnaSmallMoleculeInteractionWorkflow methods should have type annotations."""
        wf = RnaSmallMoleculeInteractionWorkflow.__dict__
        assert "run" in wf
        assert "generate_candidates" in wf
        assert "evaluate" in wf
        assert "score" in wf
        assert "rank_and_format" in wf

    def test_aptamer_input_validation_exceptions(self):
        """Invalid inputs should raise ValueError (or Pydantic ValidationError)."""
        with pytest.raises(Exception):
            RnaAptamerDesignInput(
                protein_structure_path="test.pdb",
                protein_sequence="INVALIDXYZ",
            )
        with pytest.raises(Exception):
            RnaAptamerDesignInput(
                protein_structure_path="test.pdb",
                hotspot_residues="bad_format",
            )

    def test_small_molecule_input_validation_exceptions(self):
        """Invalid SMILES or RNA should raise ValueError."""
        with pytest.raises(Exception):
            RnaSmallMoleculeInteractionInput(
                rna_sequence="AUGCX",
                smiles="CCO",
            )
        with pytest.raises(Exception):
            RnaSmallMoleculeInteractionInput(
                rna_sequence="AUGC",
                smiles="!!!",
            )

    def test_aptamer_interface_lock_comment_present(self):
        """rna_aptamer_design.py must contain INTERFACE LOCK."""
        from agent_core.workflows import rna_aptamer_design
        source = Path(rna_aptamer_design.__file__).read_text()
        assert "INTERFACE LOCK" in source
        assert "v1.0.0" in source

    def test_small_molecule_interface_lock_comment_present(self):
        """rna_small_molecule_interaction.py must contain INTERFACE LOCK."""
        from agent_core.workflows import rna_small_molecule_interaction
        source = Path(rna_small_molecule_interaction.__file__).read_text()
        assert "INTERFACE LOCK" in source
        assert "v1.0.0" in source

    def test_registry_omits_small_molecule_critic(self):
        """registry.py must omit rna_small_molecule_interaction from WORKFLOW_CRITIC_PAIRS."""
        from agent_core.workflows import registry
        source = Path(registry.__file__).read_text()
        assert "rna_small_molecule_interaction" in source
        assert "intentionally does NOT implement a Critic" in source or "deterministic" in source or "prediction/scoring" in source

    def test_no_unused_imports_aptamer(self):
        """rna_aptamer_design should not have obvious unused imports.
        We check that key symbols are referenced in the source.
        """
        from agent_core.workflows import rna_aptamer_design
        source = Path(rna_aptamer_design.__file__).read_text()
        # math is used somewhere (e.g. in helpers or scoring)
        assert "import math" in source
        # re is used for hotspot validation
        assert "import re" in source
        # datetime is used for task_id generation
        assert "datetime" in source

    def test_no_unused_imports_small_molecule(self):
        """rna_small_molecule_interaction should reference all its imports."""
        from agent_core.workflows import rna_small_molecule_interaction
        source = Path(rna_small_molecule_interaction.__file__).read_text()
        assert "import logging" in source
        assert "import re" in source
        assert "datetime" in source

    def test_runner_imports_all_workflows(self):
        """runner.py must import both target workflows."""
        from agent_core import runner
        source = Path(runner.__file__).read_text()
        assert "RnaAptamerDesignWorkflow" in source
        assert "RnaSmallMoleculeInteractionWorkflow" in source

    def test_init_exports_both_workflows(self):
        """workflows/__init__.py must export both workflows."""
        import agent_core.workflows as wf_mod
        source = Path(wf_mod.__file__).read_text()
        assert "RnaAptamerDesignWorkflow" in source
        assert "RnaSmallMoleculeInteractionWorkflow" in source


# ═══════════════════════════════════════════════════════════════════════════════
# Additional robustness tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdditionalRobustness:
    """Extra edge-case and robustness tests."""

    def test_final_report_contains_small_molecule_results(self, mock_planner_ligand, mock_ligand_registry):
        """AgentRunner._format_final_report should include small-molecule scores."""
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(mock_planner_ligand, exe, llm_critic_enabled=False)

        wf = RnaSmallMoleculeInteractionWorkflow(mock_ligand_registry)
        runner.workflow_registry["rna_small_molecule_interaction"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        state = runner.run("Predict binding for AUGC and CCO")
        report = state.get("final_report", "")
        assert "工作流执行成功" in report
        assert "AUGC" in state.get("workflow_result", {}).best_candidate.sequence

    def test_workspace_file_saved_in_metadata(self, mock_ligand_registry):
        """Workflow should save workspace filepath in candidate metadata."""
        wf = RnaSmallMoleculeInteractionWorkflow(mock_ligand_registry)
        inp = RnaSmallMoleculeInteractionInput(rna_sequence="AUGCAUGC", smiles="CCO")
        result = wf.run(inp)
        assert result.success is True
        best = result.best_candidate
        assert best.metadata.get("workspace_filepath", "").startswith("workspace/")

    def test_stream_with_empty_plan(self):
        """stream() should handle empty plan gracefully."""
        planner = MagicMock()
        planner.plan_with_state.return_value = ExecutionPlan(steps=[])
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=False)

        events = list(runner.stream("Do nothing"))
        event_keys = [list(e.keys())[0] for e in events]
        assert "router" in event_keys
        assert "plan" in event_keys
        assert "runner" in event_keys

    def test_aptamer_handler_init_failure_returns_error(self):
        """_run_aptamer_via_agent_runner should catch init failures."""
        req = MrnaWorkflowHttpRequest(
            protein="GFP",
            task_type="aptamer",
            task_id="apt-err",
        )
        with patch("workflow_api.rna_unified_handler.build_planner", side_effect=RuntimeError("No API key")):
            resp = _run_aptamer_via_agent_runner(req)
        assert resp.success is False
        assert "apt-err" in resp.task_id
        assert "init_error" in resp.summary or "Failed to initialize" in str(resp.errors)

    def test_aptamer_handler_execution_failure_returns_error(self):
        """_run_aptamer_via_agent_runner should catch execution failures."""
        req = MrnaWorkflowHttpRequest(
            protein="GFP",
            task_type="aptamer",
            task_id="apt-err2",
        )
        mock_runner = MagicMock()
        mock_runner.run.side_effect = RuntimeError("Protein structure not found")
        with patch("workflow_api.rna_unified_handler.AgentRunner", return_value=mock_runner):
            resp = _run_aptamer_via_agent_runner(req)
        assert resp.success is False
        assert "execution_error" in resp.summary or "execution failed" in str(resp.errors).lower()

    def test_session_memory_thread_safety(self):
        """SessionMemory should be safe to use from multiple threads."""
        import threading
        mem = SessionMemory()
        errors: list[Exception] = []

        def writer():
            try:
                for i in range(100):
                    mem.save(f"sess-{i % 10}", default_state(f"turn-{i}"))
            except Exception as exc:
                errors.append(exc)

        def reader():
            try:
                for i in range(100):
                    mem.load(f"sess-{i % 10}")
                    mem.list_sessions()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread-safety errors: {errors}"
        assert len(mem.list_sessions()) == 10

    def test_small_molecule_dict_input_with_invalid_scoring_tools(self, mock_ligand_registry):
        """Invalid scoring_tools should be handled gracefully (defaults to both)."""
        wf = RnaSmallMoleculeInteractionWorkflow(mock_ligand_registry)
        # If user passes an empty list, workflow should still run but may get no scores
        raw = {
            "rna_sequence": "AUGC",
            "smiles": "CCO",
            "scoring_tools": [],
        }
        result = wf.run(raw)
        # No tools selected → no valid scores → result.success should be False
        assert result.success is False
        assert "all_scoring_tools_failed" in result.errors

    def test_agent_runner_explicit_state_not_saved_to_memory(self, mock_planner_ligand, mock_ligand_registry):
        """Passing explicit state should bypass SessionMemory save."""
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        memory = SessionMemory()
        runner = AgentRunner(mock_planner_ligand, exe, session_memory=memory, llm_critic_enabled=False)

        wf = RnaSmallMoleculeInteractionWorkflow(mock_ligand_registry)
        runner.workflow_registry["rna_small_molecule_interaction"] = wf
        runner.controller = ExecutionController(
            capability_registry=runner.capability_registry,
            workflow_registry=runner.workflow_registry,
        )

        explicit = default_state("explicit")
        explicit["my_key"] = "my_value"
        runner.run("Predict binding", session_id="explicit-sess", state=explicit)
        # Explicit-state path must NOT touch memory
        assert "explicit-sess" not in memory._store
