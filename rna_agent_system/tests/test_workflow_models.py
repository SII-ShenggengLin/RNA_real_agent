from __future__ import annotations

from agent_core.workflow_models import Candidate, StepRecord, TaskState, ToolCallRecord, sort_candidates_by_score


def test_step_record_is_alias_of_tool_call_record():
    assert StepRecord is ToolCallRecord


def test_candidate_creation_and_serialization():
    candidate = Candidate(
        sequence="AUGCUA",
        sequence_type="mrna",
        source="generator_step",
        scores={"stability": 0.8},
        metadata={"model": "mock"},
    )
    payload = candidate.model_dump(mode="json")
    assert payload["sequence"] == "AUGCUA"
    assert payload["sequence_type"] == "mrna"
    assert payload["scores"]["stability"] == 0.8
    assert payload["id"].startswith("cand_")


def test_candidate_append_tool_record():
    candidate = Candidate(sequence="AUGCUA")
    record = ToolCallRecord(
        step_name="evaluate",
        tool_name="predict_rna_secondary_structure",
        input_summary="filepath=workspace/x.fa",
        output_summary="mfe=-12.3",
        success=True,
        elapsed_time=0.12,
        metrics={"mfe": -12.3},
    )
    candidate.add_tool_record(record)
    assert len(candidate.tool_records) == 1
    assert candidate.tool_records[0].tool_name == "predict_rna_secondary_structure"


def test_sort_candidates_by_score_desc():
    c1 = Candidate(sequence="AAAA", scores={"fitness": 0.2})
    c2 = Candidate(sequence="CCCC", scores={"fitness": 0.9})
    c3 = Candidate(sequence="GGGG")
    ordered = sort_candidates_by_score([c1, c2, c3], score_key="fitness", descending=True)
    assert ordered[0].sequence == "CCCC"
    assert ordered[1].sequence == "AAAA"
    assert ordered[2].sequence == "GGGG"
    assert ordered[0].rank == 1
    assert ordered[1].rank == 2


def test_task_state_update_best_candidate():
    task_state = TaskState(task_type="mrna_design", input_payload={"protein": "MKT"})
    c1 = Candidate(sequence="AAAA", scores={"fitness": 0.4})
    c2 = Candidate(sequence="CCCC", scores={"fitness": 0.6})
    task_state.append_candidate(c1)
    task_state.append_candidate(c2)
    best = task_state.update_best_candidate(score_key="fitness", descending=True)
    assert best is not None
    assert best.sequence == "CCCC"
    assert task_state.best_candidate is not None
    assert task_state.best_candidate.sequence == "CCCC"


def test_task_state_json_roundtrip():
    task = TaskState(task_type="mrna_design", input_payload={"x": 1})
    dumped = task.model_dump(mode="json")
    restored = TaskState.model_validate(dumped)
    assert restored.task_type == "mrna_design"
    assert restored.input_payload == {"x": 1}
