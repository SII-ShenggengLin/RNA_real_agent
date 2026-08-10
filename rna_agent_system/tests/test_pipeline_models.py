"""Tests for PipelinePlan, PipelineNode, PipelineEdge, and PipelineResult."""

from __future__ import annotations

import pytest

from agent_core.pipeline.models import PipelineEdge, PipelineNode, PipelinePlan


def test_single_workflow_plan() -> None:
    plan = PipelinePlan.single(
        "mrna_cds_design",
        {"protein_sequence": "MTEYK"},
        plan_id="test_single",
        output_alias="cds",
    )
    assert plan.plan_id == "test_single"
    assert len(plan.nodes) == 1
    assert plan.nodes[0].node_id == "n1"
    assert plan.nodes[0].workflow == "mrna_cds_design"
    assert plan.nodes[0].output_alias == "cds"
    assert plan.topological_order() == ["n1"]


def test_default_alias() -> None:
    node = PipelineNode(node_id="a", workflow="mrna_cds_design")
    assert node.output_alias == "a"


def test_multi_node_plan() -> None:
    plan = PipelinePlan(
        plan_id="chain",
        nodes=[
            PipelineNode(
                node_id="cds",
                workflow="mrna_cds_design",
                static_params={"protein_sequence": "M"},
                output_alias="cds",
            ),
            PipelineNode(
                node_id="fold",
                workflow="rna_secondary_structure_design",
                input_bindings={"rna_sequence": "$cds.best_candidate.sequence"},
                output_alias="fold",
            ),
        ],
        edges=[PipelineEdge(source="cds", target="fold")],
    )
    assert plan.topological_order() == ["cds", "fold"]


def test_unknown_edge_source() -> None:
    with pytest.raises(ValueError, match="unknown source"):
        PipelinePlan(
            plan_id="bad",
            nodes=[
                PipelineNode(node_id="a", workflow="mrna_cds_design"),
            ],
            edges=[PipelineEdge(source="b", target="a")],
        )


def test_unknown_binding_reference() -> None:
    with pytest.raises(ValueError, match="unknown node/alias"):
        PipelinePlan(
            plan_id="bad",
            nodes=[
                PipelineNode(
                    node_id="a",
                    workflow="mrna_cds_design",
                    input_bindings={"x": "$missing.value"},
                ),
            ],
            edges=[],
        )


def test_cycle_detection() -> None:
    with pytest.raises(ValueError, match="cycle"):
        PipelinePlan(
            plan_id="cycle",
            nodes=[
                PipelineNode(node_id="a", workflow="mrna_cds_design"),
                PipelineNode(node_id="b", workflow="rna_secondary_structure_design"),
            ],
            edges=[
                PipelineEdge(source="a", target="b"),
                PipelineEdge(source="b", target="a"),
            ],
        )


def test_self_loop_rejected() -> None:
    with pytest.raises(ValueError, match="Self-loop"):
        PipelinePlan(
            plan_id="self",
            nodes=[PipelineNode(node_id="a", workflow="mrna_cds_design")],
            edges=[PipelineEdge(source="a", target="a")],
        )


def test_binding_must_reference_upstream_node() -> None:
    with pytest.raises(ValueError, match="not an upstream node/alias"):
        PipelinePlan(
            plan_id="bad_binding",
            nodes=[
                PipelineNode(
                    node_id="a",
                    workflow="mrna_cds_design",
                    input_bindings={"x": "$b.value"},
                ),
                PipelineNode(node_id="b", workflow="rna_secondary_structure_design"),
            ],
            edges=[],
        )


def test_binding_to_later_node_rejected() -> None:
    with pytest.raises(ValueError, match="not an upstream node/alias"):
        PipelinePlan(
            plan_id="bad_order",
            nodes=[
                PipelineNode(node_id="a", workflow="mrna_cds_design"),
                PipelineNode(
                    node_id="b",
                    workflow="rna_secondary_structure_design",
                    input_bindings={"rna_sequence": "$a.best_candidate.sequence"},
                ),
            ],
            edges=[PipelineEdge(source="b", target="a")],
        )


def test_duplicate_node_id_rejected() -> None:
    with pytest.raises(ValueError, match="Duplicate node_id"):
        PipelinePlan(
            plan_id="dup",
            nodes=[
                PipelineNode(node_id="a", workflow="mrna_cds_design"),
                PipelineNode(node_id="a", workflow="rna_secondary_structure_design"),
            ],
            edges=[],
        )
