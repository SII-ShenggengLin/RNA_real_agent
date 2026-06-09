"""Tests for IRES prediction & validation workflow.

Covers:
1. Coordinate parsing & window merging helpers
2. Critic confidence assignment (evaluation-only, no retry)
3. Input validation
4. Scoring formula
5. Workflow integration with mocked capabilities
"""

from __future__ import annotations

from tests.helpers import make_mock_capability

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.ires_prediction import (
    IresPredictionCritic,
    IresPredictionInput,
    IresPredictionWorkflow,
    _merge_overlapping_windows,
    _parse_fragment_coords,
    assign_confidence,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Helper unit tests
# ─────────────────────────────────────────────────────────────────────────────


def test_parse_fragment_coords_mode2():
    assert _parse_fragment_coords("query_1_174") == (1, 174)
    assert _parse_fragment_coords("query_51_224") == (51, 224)
    assert _parse_fragment_coords("seq_A_100_274") == (100, 274)


def test_parse_fragment_coords_mode1():
    assert _parse_fragment_coords("record_50_200") == (50, 200)


def test_parse_fragment_coords_no_coords():
    assert _parse_fragment_coords("query") is None
    assert _parse_fragment_coords("") is None


def test_merge_overlapping_windows_empty():
    assert _merge_overlapping_windows([]) == []


def test_merge_overlapping_windows_no_positives():
    preds = [
        {"fragment_id": "q_1_174", "score": 0.3, "predicted_label": "non-IRES"},
    ]
    assert _merge_overlapping_windows(preds) == []


def test_merge_overlapping_windows_single():
    preds = [
        {"fragment_id": "q_1_174", "score": 0.7, "predicted_label": "IRES"},
    ]
    merged = _merge_overlapping_windows(preds)
    assert len(merged) == 1
    assert merged[0]["start"] == 1
    assert merged[0]["end"] == 174
    assert merged[0]["max_score"] == pytest.approx(0.7)


def test_merge_overlapping_windows_overlap():
    """Two overlapping windows should merge into one region with max score."""
    preds = [
        {"fragment_id": "q_1_174", "score": 0.6, "predicted_label": "IRES"},
        {"fragment_id": "q_51_224", "score": 0.8, "predicted_label": "IRES"},
    ]
    merged = _merge_overlapping_windows(preds)
    assert len(merged) == 1
    assert merged[0]["start"] == 1
    assert merged[0]["end"] == 224
    assert merged[0]["max_score"] == pytest.approx(0.8)


def test_merge_overlapping_windows_separate():
    """Non-overlapping windows should stay separate."""
    preds = [
        {"fragment_id": "q_1_174", "score": 0.6, "predicted_label": "IRES"},
        {"fragment_id": "q_300_473", "score": 0.7, "predicted_label": "IRES"},
    ]
    merged = _merge_overlapping_windows(preds)
    assert len(merged) == 2


def test_merge_overlapping_windows_mode0():
    """Mode-0 (whole-sequence) fragments without coordinates."""
    preds = [
        {"fragment_id": "query", "score": 0.9, "predicted_label": "IRES"},
    ]
    merged = _merge_overlapping_windows(preds)
    assert len(merged) == 1
    assert merged[0].get("mode0") is True
    assert merged[0]["max_score"] == pytest.approx(0.9)


def test_merge_overlapping_windows_mixed():
    """Coordinate-based + mode-0 should produce both types."""
    preds = [
        {"fragment_id": "q_1_174", "score": 0.6, "predicted_label": "IRES"},
        {"fragment_id": "query", "score": 0.9, "predicted_label": "IRES"},
    ]
    merged = _merge_overlapping_windows(preds)
    assert len(merged) == 2
    mode0 = [m for m in merged if m.get("mode0")]
    coord = [m for m in merged if not m.get("mode0")]
    assert len(mode0) == 1
    assert len(coord) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 2. Critic tests
# ─────────────────────────────────────────────────────────────────────────────


def test_critic_never_retries():
    critic = IresPredictionCritic()
    result = WorkflowResult(success=True, task_id="t1")
    state: dict[str, Any] = {"_llm_critic_enabled": False}
    assert critic.should_retry(result, state) is False


def test_critic_confidence_high():
    assert assign_confidence(0.85, 0.5) == "high"
    assert assign_confidence(0.81, 0.3) == "high"
    assert assign_confidence(0.81, 0.7) == "high"


def test_critic_confidence_medium():
    assert assign_confidence(0.65, 0.5) == "medium"
    assert assign_confidence(0.65, 0.2) == "medium"
    assert assign_confidence(0.65, 0.8) == "medium"


def test_critic_confidence_low():
    assert assign_confidence(0.55, 0.5) == "low"
    assert assign_confidence(0.55, 0.1) == "low"
    assert assign_confidence(0.55, 0.9) == "low"


def test_critic_confidence_rejected():
    assert assign_confidence(0.45, 0.5) == "rejected"
    assert assign_confidence(0.50, 0.5) == "low"  # boundary


def test_critic_confidence_no_structural_data():
    """Missing structural data downgrades one tier."""
    assert assign_confidence(0.85, None) == "medium"
    assert assign_confidence(0.65, None) == "low"
    assert assign_confidence(0.55, None) == "rejected"
    assert assign_confidence(0.45, None) == "rejected"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Input validation tests
# ─────────────────────────────────────────────────────────────────────────────


def test_input_defaults():
    inp = IresPredictionInput(sequence_filepath="test.fasta")
    assert inp.iresfinder_mode == 0
    assert inp.probability_threshold == pytest.approx(0.5)
    assert inp.window_size == 174
    assert inp.step_size == 50
    assert inp.top_n_candidates == 5
    assert inp.run_structural_validation is True


def test_input_valid_modes():
    for mode in (0, 1, 2):
        inp = IresPredictionInput(sequence_filepath="test.fasta", iresfinder_mode=mode)
        assert inp.iresfinder_mode == mode


def test_input_invalid_mode():
    with pytest.raises(Exception):
        IresPredictionInput(sequence_filepath="test.fasta", iresfinder_mode=3)


def test_input_threshold_bounds():
    with pytest.raises(Exception):
        IresPredictionInput(sequence_filepath="test.fasta", probability_threshold=1.5)
    with pytest.raises(Exception):
        IresPredictionInput(sequence_filepath="test.fasta", probability_threshold=-0.1)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Scoring tests
# ─────────────────────────────────────────────────────────────────────────────


def test_score_with_structural_data():
    wf = IresPredictionWorkflow(MagicMock())
    # Score is driven solely by IRESfinder probability.
    metrics = {"ires_probability": 0.8, "mean_unpaired_fraction": 0.5}
    scores = wf.score(metrics)
    assert scores["ires_probability"] == pytest.approx(0.8)
    assert scores["composite_score"] == pytest.approx(0.8)


def test_score_ignores_structure():
    wf = IresPredictionWorkflow(MagicMock())
    # Structural metrics do not affect the score.
    metrics_paired = {"ires_probability": 0.8, "mean_unpaired_fraction": 0.0}
    metrics_unpaired = {"ires_probability": 0.8, "mean_unpaired_fraction": 1.0}
    metrics_none = {"ires_probability": 0.8, "mean_unpaired_fraction": None}
    assert wf.score(metrics_paired) == pytest.approx(
        {"ires_probability": 0.8, "composite_score": 0.8}
    )
    assert wf.score(metrics_unpaired) == pytest.approx(
        {"ires_probability": 0.8, "composite_score": 0.8}
    )
    assert wf.score(metrics_none) == pytest.approx(
        {"ires_probability": 0.8, "composite_score": 0.8}
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. rank_and_format tests
# ─────────────────────────────────────────────────────────────────────────────


def test_rank_and_format_empty():
    wf = IresPredictionWorkflow(MagicMock())
    result = wf.rank_and_format([])
    assert result.success is True
    assert result.errors == []
    assert result.all_candidates == []


def test_rank_and_format_with_candidates():
    wf = IresPredictionWorkflow(MagicMock())
    cands = [
        Candidate(
            sequence="ACGTACGT",
            scores={"composite_score": 0.7, "ires_probability": 0.8},
            metadata={"metrics_bundle": {"start": 1, "end": 174, "region_length": 174, "mean_unpaired_fraction": 0.5}},
        ),
        Candidate(
            sequence="TGCATGCA",
            scores={"composite_score": 0.4, "ires_probability": 0.6},
            metadata={"metrics_bundle": {"start": 200, "end": 374, "region_length": 175, "mean_unpaired_fraction": 0.3}},
        ),
    ]
    result = wf.rank_and_format(cands)
    assert result.success is True
    assert result.best_candidate is not None
    assert result.best_candidate.scores["composite_score"] == pytest.approx(0.7)
    assert result.best_candidate.metadata.get("confidence") == "high"
    assert len(result.all_candidates) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 6. Workflow integration with mocked capabilities
# ─────────────────────────────────────────────────────────────────────────────


def _make_registry_for_ires(structural: bool = True) -> MagicMock:
    """Build a mock registry with IRESfinder and optional structural tools."""
    reg = MagicMock()

    caps: dict[str, Any] = {}

    # IRESfinder
    caps["predict_putative_ires_with_iresfinder"] = make_mock_capability({
        "predictions": [
            {"fragment_id": "q_1_174", "score": 0.7, "predicted_label": "IRES"},
            {"fragment_id": "q_51_224", "score": 0.6, "predicted_label": "IRES"},
            {"fragment_id": "q_101_274", "score": 0.3, "predicted_label": "non-IRES"},
        ],
        "max_score": 0.7,
        "has_putative_ires": True,
    })

    if structural:
        # ViennaRNA fold
        caps["predict_rna_secondary_structure"] = make_mock_capability({
            "structure": "((((....))))",
            "mfe_kcal_per_mol": -15.0,
        })
        # RNAplfold
        caps["predict_rna_local_accessibility_profile_vienna"] = make_mock_capability({
            "mean_unpaired_prob_1nt": 0.45,
            "lunp_profile_tsv_filepath": "workspace/test_profile.tsv",
        })
        # Unpaired fraction
        caps["compute_dot_bracket_unpaired_fraction"] = make_mock_capability({
            "unpaired_fraction": 0.333,
        })

    def _has(name: str) -> bool:
        return name in caps

    def _get(name: str) -> Any:
        return caps[name]

    reg.has = _has
    reg.get = _get
    return reg


@patch("agent_core.workflows.ires_prediction.read_sequence")
def test_workflow_end_to_end(mock_read_seq):
    mock_read_seq.return_value = ">query\n" + "ACGT" * 100  # 400 nt

    reg = _make_registry_for_ires(structural=True)
    wf = IresPredictionWorkflow(reg)

    inp = IresPredictionInput(
        sequence_filepath="dummy.fasta",
        iresfinder_mode=2,
        probability_threshold=0.5,
        top_n_candidates=5,
        run_structural_validation=True,
    )

    result = wf.run(inp)
    assert result.success is True
    assert len(result.all_candidates) > 0
    best = result.best_candidate
    assert best is not None
    assert "ires_probability" in best.scores
    assert "composite_score" in best.scores
    assert best.metadata.get("confidence") in {"high", "medium", "low", "rejected"}


@patch("agent_core.workflows.ires_prediction.read_sequence")
def test_workflow_no_structural_validation(mock_read_seq):
    mock_read_seq.return_value = ">query\n" + "ACGT" * 100

    reg = _make_registry_for_ires(structural=False)
    wf = IresPredictionWorkflow(reg)

    inp = IresPredictionInput(
        sequence_filepath="dummy.fasta",
        iresfinder_mode=2,
        run_structural_validation=False,
    )

    result = wf.run(inp)
    assert result.success is True
    best = result.best_candidate
    assert best is not None
    # Score is driven solely by probability; structural data is reported but not scored.
    assert best.scores["composite_score"] == pytest.approx(best.scores["ires_probability"])


@patch("agent_core.workflows.ires_prediction.read_sequence")
def test_workflow_no_positives(mock_read_seq):
    mock_read_seq.return_value = ">query\n" + "ACGT" * 50

    reg = MagicMock()
    cap_ires = make_mock_capability({
        "predictions": [
            {"fragment_id": "q_1_174", "score": 0.3, "predicted_label": "non-IRES"},
        ],
        "max_score": 0.3,
        "has_putative_ires": False,
    })
    caps = {"predict_putative_ires_with_iresfinder": cap_ires}
    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]

    wf = IresPredictionWorkflow(reg)
    inp = IresPredictionInput(sequence_filepath="dummy.fasta")
    result = wf.run(inp)
    assert result.success is True
    assert result.errors == []
    assert result.all_candidates == []


@patch("agent_core.workflows.ires_prediction.read_sequence")
def test_workflow_mode0(mock_read_seq):
    mock_read_seq.return_value = ">query\n" + "ACGT" * 50

    reg = MagicMock()
    cap_ires = make_mock_capability({
        "predictions": [
            {"fragment_id": "query", "score": 0.9, "predicted_label": "IRES"},
        ],
        "max_score": 0.9,
        "has_putative_ires": True,
    })
    cap_fold = make_mock_capability({
        "structure": "....",
        "mfe_kcal_per_mol": -5.0,
    })
    cap_unp = make_mock_capability({"unpaired_fraction": 0.5})
    cap_plf = make_mock_capability({
        "mean_unpaired_prob_1nt": 0.5,
        "lunp_profile_tsv_filepath": "workspace/test.tsv",
    })
    caps = {
        "predict_putative_ires_with_iresfinder": cap_ires,
        "predict_rna_secondary_structure": cap_fold,
        "compute_dot_bracket_unpaired_fraction": cap_unp,
        "predict_rna_local_accessibility_profile_vienna": cap_plf,
    }
    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]

    wf = IresPredictionWorkflow(reg)
    inp = IresPredictionInput(sequence_filepath="dummy.fasta", iresfinder_mode=0)
    result = wf.run(inp)
    assert result.success is True
    best = result.best_candidate
    assert best is not None
    assert best.metadata.get("start") == 1
    assert best.metadata.get("end") == 200  # 50 * 4 = 200 nt
    assert best.metadata.get("ires_probability") == pytest.approx(0.9)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Layer 3 integration tests
# ─────────────────────────────────────────────────────────────────────────────


@patch("agent_core.workflows.ires_prediction.read_sequence")
def test_execution_controller_ires(mock_read_seq):
    """Test ExecutionController end-to-end with IresPredictionWorkflow."""
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep

    mock_read_seq.return_value = ">query\n" + "ACGT" * 100

    reg = _make_registry_for_ires(structural=True)
    wf = IresPredictionWorkflow(reg)
    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry={"ires_prediction": wf},
    )
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="ires_prediction",
                input_binding={"sequence_filepath": "dummy.fasta", "iresfinder_mode": 2},
                output_key="ires_result",
                description="Predict IRES regions",
            )
        ]
    )
    state: dict = {}
    result_state = controller.execute(plan, state)

    assert result_state.get("workflow_result") is not None
    assert result_state["workflow_result"].success is True
    assert result_state.get("_plan_executed") is True
    assert result_state.get("ires_result") is not None


@patch("agent_core.workflows.ires_prediction.read_sequence")
def test_execution_controller_ires_progress_callback(mock_read_seq):
    """progress_callback should receive step-level and workflow-level events."""
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep

    mock_read_seq.return_value = ">query\n" + "ACGT" * 100

    events: list[dict] = []

    def _cb(entry: dict) -> None:
        events.append(entry)

    reg = _make_registry_for_ires(structural=True)
    wf = IresPredictionWorkflow(reg)
    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry={"ires_prediction": wf},
    )
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="ires_prediction",
                input_binding={"sequence_filepath": "dummy.fasta", "iresfinder_mode": 2},
                output_key="ires_result",
                description="Predict IRES regions",
            )
        ]
    )
    state: dict = {}
    controller.execute(plan, state, progress_callback=_cb)

    event_names = [e["event"] for e in events]
    assert "step_start" in event_names
    assert "step_done" in event_names
    assert "plan_complete" in event_names
    assert "generate_complete" in event_names
    assert "evaluate_progress" in event_names


@patch("agent_core.workflows.ires_prediction.read_sequence")
def test_execution_controller_ires_state_writeback(mock_read_seq):
    """Workflow _state_writeback should be merged into outer state without error."""
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep

    mock_read_seq.return_value = ">query\n" + "ACGT" * 100

    reg = _make_registry_for_ires(structural=True)
    wf = IresPredictionWorkflow(reg)
    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry={"ires_prediction": wf},
    )
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="ires_prediction",
                input_binding={"sequence_filepath": "dummy.fasta", "iresfinder_mode": 2},
                output_key="ires_result",
                description="Predict IRES regions",
            )
        ]
    )
    state: dict = {}
    result_state = controller.execute(plan, state)

    assert result_state.get("_plan_executed") is True
    assert result_state.get("workflow_result") is not None


@patch("agent_core.workflows.ires_prediction.read_sequence")
def test_execution_controller_ires_critic_disabled_no_retry(mock_read_seq):
    """When LLM Critic is explicitly disabled, no retry is triggered."""
    from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep

    mock_read_seq.return_value = ">query\n" + "ACGT" * 100

    reg = _make_registry_for_ires(structural=True)
    wf = IresPredictionWorkflow(reg)
    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry={"ires_prediction": wf},
    )
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="ires_prediction",
                input_binding={"sequence_filepath": "dummy.fasta", "iresfinder_mode": 2},
                output_key="ires_result",
                description="Predict IRES regions",
            )
        ],
        max_retries=1,
    )
    state: dict = {"_llm_critic_enabled": False}
    result_state = controller.execute(plan, state)

    assert result_state.get("retry_count", 0) == 0
    assert "_critic_should_retry" not in result_state
    assert result_state.get("_plan_executed") is True


def test_registry_has_ires_critic():
    from agent_core.workflows.registry import get_critic_for_workflow

    critic = get_critic_for_workflow("ires_prediction")
    assert critic is not None
    assert isinstance(critic, IresPredictionCritic)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Critic _build_context tests
# ─────────────────────────────────────────────────────────────────────────────


def test_critic_build_context_empty_candidates():
    """_build_context with no candidates should return empty stats."""
    from agent_core.workflow_models import WorkflowResult

    critic = IresPredictionCritic()
    result = WorkflowResult(success=True, task_id="t1")
    state: dict[str, Any] = {}
    ctx = critic._build_context(result, state)

    assert "ires_stats" in ctx
    stats = ctx["ires_stats"]
    assert stats["probability_range"]["count"] == 0
    assert stats["mfe_range"]["count"] == 0
    assert stats["coverage"]["min_start"] is None


def test_critic_build_context_with_candidates():
    """_build_context should aggregate IRES-specific statistics."""
    from agent_core.workflow_models import WorkflowResult

    critic = IresPredictionCritic()
    cands = [
        Candidate(
            sequence="ACGTACGT",
            scores={"composite_score": 0.7, "ires_probability": 0.8},
            metadata={
                "iresfinder_mode": 2,
                "metrics_bundle": {
                    "start": 1,
                    "end": 174,
                    "region_length": 174,
                    "ires_probability": 0.8,
                    "mfe_kcal_per_mol": -15.0,
                    "mean_unpaired_fraction": 0.5,
                    "mean_unpaired_prob_1nt": 0.45,
                },
            },
        ),
        Candidate(
            sequence="TGCATGCA",
            scores={"composite_score": 0.4, "ires_probability": 0.6},
            metadata={
                "iresfinder_mode": 2,
                "metrics_bundle": {
                    "start": 200,
                    "end": 374,
                    "region_length": 175,
                    "ires_probability": 0.6,
                    "mfe_kcal_per_mol": -10.0,
                    "mean_unpaired_fraction": 0.3,
                    "mean_unpaired_prob_1nt": 0.35,
                },
            },
        ),
    ]
    result = WorkflowResult(success=True, task_id="t1", all_candidates=cands)
    state: dict[str, Any] = {}
    ctx = critic._build_context(result, state)

    stats = ctx["ires_stats"]
    assert stats["probability_range"]["count"] == 2
    assert stats["probability_range"]["min"] == pytest.approx(0.6)
    assert stats["probability_range"]["max"] == pytest.approx(0.8)
    assert stats["mfe_range"]["count"] == 2
    assert stats["mfe_range"]["min"] == pytest.approx(-15.0)
    assert stats["unpaired_fraction_range"]["count"] == 2
    assert stats["plfold_range"]["count"] == 2
    assert stats["region_length_range"]["count"] == 2
    assert stats["coverage"]["min_start"] == 1
    assert stats["coverage"]["max_end"] == 374
    assert stats["mode_distribution"] == {"2": 2}


def test_critic_should_retry_when_disabled():
    """Critic should not retry when _llm_critic_enabled is False."""
    from agent_core.workflow_models import WorkflowResult

    critic = IresPredictionCritic()
    result = WorkflowResult(success=True, task_id="t1")
    state: dict[str, Any] = {"_llm_critic_enabled": False}
    assert critic.should_retry(result, state) is False
