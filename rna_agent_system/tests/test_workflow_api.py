"""Tests for the FastAPI workflow endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from workflow_api import app as workflow_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(workflow_app.app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_unknown_workflow(client: TestClient) -> None:
    response = client.post("/v1/agent/run", json={"workflow": "not_a_workflow", "params": {}})
    assert response.status_code == 422


def test_pipeline_endpoint_validation_error(client: TestClient) -> None:
    """An invalid PipelinePlan body must return 422."""
    response = client.post("/v1/agent/pipeline", json={"plan": {"invalid": "plan"}})
    assert response.status_code == 422
    assert "Invalid pipeline plan" in response.json()["detail"]


def test_pipeline_endpoint_success(client: TestClient) -> None:
    """A valid pipeline plan should be executed and returned as JSON."""
    from agent_core.agents.base import AgentResult
    from agent_core.agents.quality_agent import QualityReport
    from agent_core.pipeline.models import PipelineResult
    from agent_core.workflow_models import Candidate, WorkflowResult

    mock_result = PipelineResult(
        plan_id="test_plan",
        success=True,
        node_results={
            "n1": AgentResult(
                node_id="n1",
                workflow="mrna_sequence_scoring",
                success=True,
                workflow_result=WorkflowResult(
                    success=True,
                    task_id="t1",
                    best_candidate=Candidate(sequence="AUGC", source="test"),
                    all_candidates=[Candidate(sequence="AUGC", source="test")],
                ),
                metadata={"quality_report": QualityReport(
                    overall_assessment="ok",
                    quality_score=1.0,
                    action="pass",
                    reasoning="fine",
                )},
            )
        },
        final_report="Pipeline completed successfully.",
    )

    plan_payload = {
        "plan_id": "test_plan",
        "nodes": [
            {
                "node_id": "n1",
                "workflow": "mrna_sequence_scoring",
                "static_params": {"rna_sequence": "AUGC"},
                "output_alias": "result",
            }
        ],
        "edges": [],
    }

    with patch.object(workflow_app._agent_runner, "run_pipeline", return_value=mock_result):
        response = client.post("/v1/agent/pipeline", json={"plan": plan_payload})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["plan_id"] == "test_plan"
    assert data["final_report"] == "Pipeline completed successfully."
    assert "pipeline_result" in data
    assert data["pipeline_result"]["node_results"]["n1"]["workflow"] == "mrna_sequence_scoring"
