"""Tests for LLMPlanner.

Covers:
1. _parse_json_from_content edge cases
2. _build_system_prompt content verification
3. plan() fallback when LLM fails
4. plan_with_state() using shared state
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_core.planning.llm_planner import LLMPlanner
from agent_core.planning.base import AgentContext, ExecutionPlan


# ─────────────────────────────────────────────────────────────────────────────
# 1. _parse_json_from_content
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def planner() -> LLMPlanner:
    return LLMPlanner(llm=MagicMock())


@pytest.mark.parametrize(
    "content,expected",
    [
        ("", {}),
        ('{"steps":[]}', {"steps": []}),
        ('```json\n{"steps":[]}\n```', {"steps": []}),
        ('```\n{"steps":[]}\n```', {"steps": []}),
        ('Here is the plan:\n{"steps":[]}', {"steps": []}),
        ('{"steps":[]}\nHope this helps!', {"steps": []}),
        ('Plan:\n{"steps":[]}\nDone.', {"steps": []}),
        ('{"reasoning":"Use {x:1}","steps":[]}', {"reasoning": "Use {x:1}", "steps": []}),
        (
            '{"steps":[{"type":"workflow","target":"rna_aptamer_design"}]}',
            {"steps": [{"type": "workflow", "target": "rna_aptamer_design"}]},
        ),
    ],
)
def test_parse_json_from_content_valid(planner: LLMPlanner, content: str, expected: dict[str, Any]):
    assert planner._parse_json_from_content(content) == expected


@pytest.mark.parametrize(
    "content",
    [
        "No JSON here at all",
        '{"steps": [}',  # unmatched braces
    ],
)
def test_parse_json_from_content_invalid(planner: LLMPlanner, content: str):
    with pytest.raises(Exception):
        planner._parse_json_from_content(content)


def test_parse_json_from_content_whitespace_only_returns_empty(planner: LLMPlanner):
    """Whitespace-only content should return an empty dict, not raise."""
    assert planner._parse_json_from_content("   ") == {}


# ─────────────────────────────────────────────────────────────────────────────
# 2. _build_system_prompt
# ─────────────────────────────────────────────────────────────────────────────


def test_build_system_prompt_includes_workflows(planner: LLMPlanner):
    ctx = AgentContext(
        available_workflows=["rna_aptamer_design", "rna_small_molecule_interaction"],
        available_capabilities=["compute_rna_sequence_gc_content"],
    )
    prompt = planner._build_system_prompt(ctx)
    assert "rna_aptamer_design" in prompt
    assert "rna_small_molecule_interaction" in prompt
    assert "compute_rna_sequence_gc_content" in prompt


def test_build_system_prompt_no_workflows(planner: LLMPlanner):
    ctx = AgentContext(
        available_workflows=[],
        available_capabilities=["cap_a"],
    )
    prompt = planner._build_system_prompt(ctx)
    assert "## Available Workflows" not in prompt
    assert "cap_a" in prompt


def test_build_system_prompt_sorted(planner: LLMPlanner):
    ctx = AgentContext(
        available_workflows=["zebra", "alpha"],
        available_capabilities=["z_cap", "a_cap"],
    )
    prompt = planner._build_system_prompt(ctx)
    # Verify order by finding positions
    alpha_pos = prompt.find("alpha")
    zebra_pos = prompt.find("zebra")
    assert alpha_pos < zebra_pos
    a_cap_pos = prompt.find("a_cap")
    z_cap_pos = prompt.find("z_cap")
    assert a_cap_pos < z_cap_pos


# ─────────────────────────────────────────────────────────────────────────────
# 3. plan() — mock LLM success
# ─────────────────────────────────────────────────────────────────────────────


def test_plan_success_with_mock_llm(planner: LLMPlanner):
    mock_response = MagicMock()
    mock_response.content = (
        '{"reasoning":"Design aptamer","steps":['
        '{"step_id":"s1","type":"workflow","target":"rna_aptamer_design",'
        '"input_binding":{"protein_structure_path":"test.pdb"},'
        '"output_key":"result","description":"Design aptamer"}]}'
    )
    planner.llm.invoke.return_value = mock_response

    ctx = AgentContext(
        available_workflows=["rna_aptamer_design"],
        available_capabilities=[],
    )
    plan = planner.plan("Design an aptamer for protein X", ctx)

    assert isinstance(plan, ExecutionPlan)
    assert len(plan.steps) == 1
    assert plan.steps[0].target == "rna_aptamer_design"
    assert plan.steps[0].type == "workflow"
    assert plan.steps[0].output_key == "result"


def test_plan_success_with_markdown_fence(planner: LLMPlanner):
    mock_response = MagicMock()
    mock_response.content = (
        '```json\n'
        '{"reasoning":"Predict binding","steps":['
        '{"step_id":"s1","type":"workflow","target":"rna_small_molecule_interaction",'
        '"input_binding":{"rna_sequence":"AUGC","smiles":"CCO"},'
        '"output_key":"result","description":"Predict"}]}'
        '\n```'
    )
    planner.llm.invoke.return_value = mock_response

    ctx = AgentContext(
        available_workflows=["rna_small_molecule_interaction"],
        available_capabilities=[],
    )
    plan = planner.plan("Predict RNA-ligand binding", ctx)

    assert isinstance(plan, ExecutionPlan)
    assert len(plan.steps) == 1
    assert plan.steps[0].target == "rna_small_molecule_interaction"


# ─────────────────────────────────────────────────────────────────────────────
# 4. plan() — fallback on LLM failure
# ─────────────────────────────────────────────────────────────────────────────


def test_plan_fallback_on_json_decode_error(planner: LLMPlanner):
    mock_response = MagicMock()
    mock_response.content = "This is not JSON"
    planner.llm.invoke.return_value = mock_response

    ctx = AgentContext(available_workflows=[], available_capabilities=[])
    plan = planner.plan("Do something", ctx)

    assert isinstance(plan, ExecutionPlan)
    assert plan.steps == []


def test_plan_fallback_on_validation_error(planner: LLMPlanner):
    mock_response = MagicMock()
    mock_response.content = '{"reasoning":"bad","steps":"not_a_list"}'
    planner.llm.invoke.return_value = mock_response

    ctx = AgentContext(available_workflows=[], available_capabilities=[])
    plan = planner.plan("Do something", ctx)

    assert isinstance(plan, ExecutionPlan)
    assert plan.steps == []


def test_plan_fallback_on_llm_exception(planner: LLMPlanner):
    planner.llm.invoke.side_effect = RuntimeError("LLM service unreachable")

    ctx = AgentContext(available_workflows=[], available_capabilities=[])
    plan = planner.plan("Do something", ctx)

    assert isinstance(plan, ExecutionPlan)
    assert plan.steps == []


# ─────────────────────────────────────────────────────────────────────────────
# 5. plan_with_state
# ─────────────────────────────────────────────────────────────────────────────


def test_plan_with_state_injects_snapshot(planner: LLMPlanner):
    mock_response = MagicMock()
    mock_response.content = '{"reasoning":"use state","steps":[]}'
    planner.llm.invoke.return_value = mock_response

    state = {
        "session_id": "sess_123",
        "_available_capabilities": ["cap_a"],
        "_available_workflows": ["wf_a"],
        "previous_result": "x" * 300,  # long value should be truncated
    }
    plan = planner.plan_with_state("Continue", state)

    assert isinstance(plan, ExecutionPlan)
    # Verify llm.invoke was called with a message containing the state snapshot
    call_args = planner.llm.invoke.call_args
    messages = call_args[0][0]
    user_msg = [m for m in messages if hasattr(m, "content") and "User request" in m.content][0]
    assert "sess_123" in user_msg.content or "<str len=" in user_msg.content


# ─────────────────────────────────────────────────────────────────────────────
# 6. factory
# ─────────────────────────────────────────────────────────────────────────────


def test_build_planner_default():
    from agent_core.planning.factory import build_planner
    p = build_planner()
    assert isinstance(p, LLMPlanner)


def test_build_planner_unsupported_backend():
    from agent_core.planning.factory import build_planner
    with pytest.raises(ValueError, match="Unsupported planner backend"):
        build_planner("unsupported")
