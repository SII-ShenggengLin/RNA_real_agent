"""Unit tests for CoordinatorAgent BMC orchestration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_core.agents.coordinator_agent import CoordinatorAgent
from agent_core.workflow_models import Candidate, WorkflowResult


class _SimpleWorkflow:
    """Non-BMC workflow used for fallback tests."""

    name = "simple_workflow"

    def run(self, inp: Any, *, progress_callback: Any | None = None) -> WorkflowResult:
        return WorkflowResult(success=True, task_id="t1", summary="ok")


class TestCoordinatorAgent:
    def test_non_bmc_workflow_delegates_to_run(self):
        """A workflow without the BMC interface is run directly."""
        workflow = _SimpleWorkflow()

        agent = CoordinatorAgent(workflow)
        result = agent.run({"param": 1}, progress_callback=None)

        assert result.success is True
        assert result.summary == "ok"

    def test_bmc_capable_workflow_zero_rounds(self):
        """When max_rounds is 0, only initial run and finalize execute."""
        workflow = MagicMock(spec=["name", "run_initial", "bmc_prepare", "bmc_run_round", "bmc_finalize"])
        workflow.name = "bmc_workflow"

        initial_result = WorkflowResult(
            success=True,
            task_id="t1",
            summary="initial",
            all_candidates=[Candidate(sequence="AAA", sequence_type="rna")],
        )
        workflow.run_initial.return_value = initial_result
        workflow.bmc_prepare.return_value = {"max_rounds": 0}
        workflow.bmc_finalize.return_value = initial_result

        agent = CoordinatorAgent(workflow)
        result = agent.run({"param": 1}, progress_callback=None)

        assert result.success is True
        workflow.run_initial.assert_called_once_with({"param": 1}, progress_callback=None)
        workflow.bmc_prepare.assert_called_once_with(initial_result)
        workflow.bmc_run_round.assert_not_called()
        workflow.bmc_finalize.assert_called_once_with(initial_result)

    def test_bmc_capable_workflow_runs_rounds_until_convergence(self):
        """The agent loops over bmc_run_round until should_stop is True."""
        workflow = MagicMock(spec=["name", "run_initial", "bmc_prepare", "bmc_run_round", "bmc_finalize"])
        workflow.name = "bmc_workflow"

        initial_result = WorkflowResult(
            success=True,
            task_id="t1",
            summary="initial",
            all_candidates=[Candidate(sequence="AAA", sequence_type="rna")],
        )
        workflow.run_initial.return_value = initial_result
        bmc_state = {"max_rounds": 5}
        workflow.bmc_prepare.return_value = bmc_state

        # First round says continue, second round says stop.
        round1_result = WorkflowResult(
            success=True,
            task_id="t1",
            summary="round1",
            all_candidates=[Candidate(sequence="BBB", sequence_type="rna")],
        )
        round2_result = WorkflowResult(
            success=True,
            task_id="t1",
            summary="round2",
            all_candidates=[Candidate(sequence="CCC", sequence_type="rna")],
        )
        workflow.bmc_run_round.side_effect = [
            (round1_result, bmc_state, False, "improved"),
            (round2_result, bmc_state, True, "converged"),
        ]
        workflow.bmc_finalize.return_value = round2_result

        agent = CoordinatorAgent(workflow)
        result = agent.run({"param": 1}, progress_callback=None)

        assert result.summary == "round2"
        assert workflow.bmc_run_round.call_count == 2
        workflow.bmc_finalize.assert_called_once_with(round2_result)

    def test_bmc_early_exit_on_initial_failure(self):
        """If the initial run fails, finalize is called without BMC rounds."""
        workflow = MagicMock(spec=["name", "run_initial", "bmc_prepare", "bmc_run_round", "bmc_finalize"])
        workflow.name = "bmc_workflow"

        initial_result = WorkflowResult(
            success=False,
            task_id="t1",
            summary="failed",
            errors=["boom"],
        )
        workflow.run_initial.return_value = initial_result
        workflow.bmc_finalize.return_value = initial_result

        agent = CoordinatorAgent(workflow)
        result = agent.run({"param": 1})

        assert result.success is False
        workflow.bmc_prepare.assert_not_called()
        workflow.bmc_run_round.assert_not_called()
        workflow.bmc_finalize.assert_called_once_with(initial_result)

    def test_bmc_early_exit_on_empty_candidates(self):
        """If the initial run has no candidates, finalize is called without rounds."""
        workflow = MagicMock(spec=["name", "run_initial", "bmc_prepare", "bmc_run_round", "bmc_finalize"])
        workflow.name = "bmc_workflow"

        initial_result = WorkflowResult(
            success=True,
            task_id="t1",
            summary="empty",
            all_candidates=[],
        )
        workflow.run_initial.return_value = initial_result
        workflow.bmc_finalize.return_value = initial_result

        agent = CoordinatorAgent(workflow)
        result = agent.run({"param": 1})

        assert result.success is True
        workflow.bmc_prepare.assert_not_called()
        workflow.bmc_run_round.assert_not_called()
        workflow.bmc_finalize.assert_called_once_with(initial_result)

    def test_progress_callback_passed_through(self):
        """progress_callback is forwarded to run_initial and each BMC round."""
        workflow = MagicMock(spec=["name", "run_initial", "bmc_prepare", "bmc_run_round", "bmc_finalize"])
        workflow.name = "bmc_workflow"

        initial_result = WorkflowResult(
            success=True,
            task_id="t1",
            summary="initial",
            all_candidates=[Candidate(sequence="AAA", sequence_type="rna")],
        )
        workflow.run_initial.return_value = initial_result
        bmc_state = {"max_rounds": 1}
        workflow.bmc_prepare.return_value = bmc_state
        workflow.bmc_run_round.return_value = (initial_result, bmc_state, True, "ok")
        workflow.bmc_finalize.return_value = initial_result

        callback = MagicMock()
        agent = CoordinatorAgent(workflow)
        agent.run({"param": 1}, progress_callback=callback)

        workflow.run_initial.assert_called_once_with({"param": 1}, progress_callback=callback)
        workflow.bmc_run_round.assert_called_once_with(
            1, initial_result, bmc_state, progress_callback=callback
        )
