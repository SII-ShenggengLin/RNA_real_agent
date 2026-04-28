"""Tests that MrnaSpecialist respects next_constraints when replanning."""

from __future__ import annotations

from typing import Any

import pytest

from agent_core.planning.rule_based.specialists.mrna_specialist import MrnaSpecialist


@pytest.fixture
def specialist() -> MrnaSpecialist:
    return MrnaSpecialist()


def test_plan_protein_to_cds_default(specialist: MrnaSpecialist) -> None:
    state: dict[str, Any] = {}
    plan = specialist._plan_protein_to_cds("LinearDesign for protein MVSKGEELFTGV", state)
    assert len(plan.steps) == 1
    binding = plan.steps[0].input_binding
    assert binding["design_tool"] == "lineardesign"
    assert binding["lambda_value"] == 0.0


def test_plan_prioritize_stability_increases_lambda(specialist: MrnaSpecialist) -> None:
    state: dict[str, Any] = {"next_constraints": {"prioritize_stability": True}}
    plan = specialist._plan_protein_to_cds("LinearDesign for protein MVSKGEELFTGV", state)
    binding = plan.steps[0].input_binding
    assert binding["design_tool"] == "lineardesign"
    assert binding["lambda_value"] == 0.5


def test_plan_increase_diversity_rotates_tool(specialist: MrnaSpecialist) -> None:
    state: dict[str, Any] = {"next_constraints": {"increase_diversity": True}}
    plan = specialist._plan_protein_to_cds("LinearDesign for protein MVSKGEELFTGV", state)
    binding = plan.steps[0].input_binding
    # Default is lineardesign; diversity rotates to rnarl
    assert binding["design_tool"] == "rnarl"


def test_plan_target_gc_mid_passed_through(specialist: MrnaSpecialist) -> None:
    state: dict[str, Any] = {"next_constraints": {"target_gc_mid": 0.55}}
    plan = specialist._plan_protein_to_cds("LinearDesign for protein MVSKGEELFTGV", state)
    binding = plan.steps[0].input_binding
    assert binding["target_gc_mid"] == 0.55


def test_plan_combined_constraints(specialist: MrnaSpecialist) -> None:
    state: dict[str, Any] = {
        "next_constraints": {
            "increase_diversity": True,
            "prioritize_stability": True,
            "target_gc_mid": 0.52,
        }
    }
    plan = specialist._plan_protein_to_cds("LinearDesign for protein MVSKGEELFTGV", state)
    binding = plan.steps[0].input_binding
    assert binding["design_tool"] == "rnarl"
    assert binding["lambda_value"] == 0.5
    assert binding["target_gc_mid"] == 0.52
