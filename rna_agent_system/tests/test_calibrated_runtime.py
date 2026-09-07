"""Platform CapGate runtime: ToolExecutor audit/gating + conservative transfer + ClaimGate wiring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.tools import tool

from agent_core.calibrated.models import (
    CapabilityAssessment,
    CapabilityRecord,
    Claim,
    ClaimDependency,
)
from agent_core.calibrated.runtime import (
    CalibratedRuntime,
    oracle_use,
)
from agent_core.calibrated.self_model import SelfModel
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry


@tool
def score_rna_protein_complex_with_egarps(sequence: str) -> dict:
    """Stub EGARPS oracle tool for gating tests (never invoked when blocked)."""
    return {"native_probability": 0.5}


def _runtime(tmp_path: Path, *, policy: str = "enforce") -> CalibratedRuntime:
    return CalibratedRuntime.configure(
        audit_path=tmp_path / "audit.jsonl", policy=policy
    )


# --------------------------------------------------------------------- default model


def test_default_self_model_grades(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    # E1: structure oracles failed profiling on the aptamer task.
    d = runtime.review_tool_call("score_rna_protein_complex_with_egarps")
    assert d is not None and d.verdict == "reject"
    d = runtime.review_tool_call("predict_rna_protein_complex_with_proteinx")
    assert d is not None and d.verdict == "reject"
    # E7: MRL oracle verified on its families -> transferred (downgrade) elsewhere.
    d = runtime.review_tool_call("predict_5utr_mrl_with_gemorna")
    assert d is not None and d.verdict == "downgrade"
    # DECISIONS (bb): the 3'UTR oracle's declared use is scoring_annotation
    # (demoted from ranking_objective) — unprofiled annotation use is allowed;
    # the demotion lives in the workflow's ASF objective set instead.
    d = runtime.review_tool_call("predict_3utr_stability_with_gemorna")
    assert d is not None and d.verdict == "allow"
    # Non-managed tools are never reviewed at the executor.
    assert runtime.review_tool_call("compute_rna_sequence_gc_content") is None
    CalibratedRuntime.clear()


def test_default_self_model_file_exists() -> None:
    from agent_core.calibrated.runtime import DEFAULT_SELF_MODEL_PATH

    payload = json.loads(DEFAULT_SELF_MODEL_PATH.read_text())
    oracles = {r["oracle"] for r in payload["records"]}
    assert {"gemorna_5utr_mrl", "rnasmol"} <= oracles
    assert {
        "egarps_native_probability",
        "proteinx_ipTM",
        "rhofold_mean_plddt",
    } <= oracles


# ------------------------------------------------------------------ executor gating


def _executor() -> ToolExecutor:
    registry = ToolRegistry()
    registry.register_many([score_rna_protein_complex_with_egarps])
    return ToolExecutor(registry)


def test_executor_blocks_failed_oracle_under_enforce(tmp_path: Path) -> None:
    _runtime(tmp_path, policy="enforce")
    result = _executor().run_tool(
        "score_rna_protein_complex_with_egarps", sequence="GGG"
    )
    assert not result.success
    assert result.error["type"] == "GatedActionError"
    assert result.error["verdict"] == "reject"
    events = [e for e in _audit_events(tmp_path) if e["event_type"] == "tool_call"]
    assert events and events[-1]["payload"]["gated"] is True
    CalibratedRuntime.clear()


def test_executor_advisory_policy_records_but_allows(tmp_path: Path) -> None:
    _runtime(tmp_path, policy="advisory")
    result = _executor().run_tool(
        "score_rna_protein_complex_with_egarps", sequence="GGG"
    )
    assert result.success
    events = [e for e in _audit_events(tmp_path) if e["event_type"] == "tool_call"]
    assert events and events[-1]["payload"]["success"] is True
    gate = [e for e in _audit_events(tmp_path) if e["event_type"] == "gate_decision"]
    assert gate, "advisory policy still records the gate decision"
    CalibratedRuntime.clear()


def test_oracle_use_context_permits_profiling(tmp_path: Path) -> None:
    _runtime(tmp_path, policy="enforce")
    with oracle_use("scoring_annotation"):
        result = _executor().run_tool(
            "score_rna_protein_complex_with_egarps", sequence="GGG"
        )
    assert result.success, "annotation use must not be gated"
    CalibratedRuntime.clear()


def test_audit_records_unmanaged_calls(tmp_path: Path) -> None:
    _runtime(tmp_path, policy="enforce")

    @tool
    def compute_rna_sequence_gc_content(sequence: str) -> dict:
        """Stub deterministic tool."""
        return {"gc_content": 0.5}

    registry = ToolRegistry()
    registry.register_many([compute_rna_sequence_gc_content])
    result = ToolExecutor(registry).run_tool(
        "compute_rna_sequence_gc_content", sequence="GGCC"
    )
    assert result.success
    events = [e for e in _audit_events(tmp_path) if e["event_type"] == "tool_call"]
    assert events[-1]["payload"]["tool_name"] == "compute_rna_sequence_gc_content"
    CalibratedRuntime.clear()


def _audit_events(tmp_path: Path) -> list[dict]:
    path = tmp_path / "audit.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ----------------------------------------------------------- conservative transfer


def _record(family: str, ranking: str) -> CapabilityRecord:
    return CapabilityRecord(
        oracle="oracle_x",
        task_type="task",
        target_family=family,
        capabilities={"ranking": CapabilityAssessment(grade=ranking, confidence=0.9)},
    )


def test_transfer_mixed_donors_inherit_worst_grade() -> None:
    model = SelfModel([_record("family_a", "verified"), _record("family_b", "failed")])
    transferred = model.query("oracle_x", "task", "never_profiled")
    cell = transferred.assessment("ranking")
    assert cell.grade == "transferred"
    assert cell.transferred_from_grade == "failed"


def test_transfer_all_verified_donors_downgrade() -> None:
    model = SelfModel([_record("family_a", "verified")])
    transferred = model.query("oracle_x", "task", "never_profiled")
    cell = transferred.assessment("ranking")
    assert cell.grade == "transferred"
    assert cell.transferred_from_grade == "verified"


def test_no_donor_is_unprofiled() -> None:
    model = SelfModel([_record("family_a", "verified")])
    empty = model.query("oracle_y", "task", "any")
    assert empty.assessment("ranking").grade == "unprofiled"


# -------------------------------------------------------------------- ClaimGate path


class _StubLLM:
    """Every invoke returns the extracted-claims JSON payload."""

    def __init__(self, claims_payload: str) -> None:
        self._claims_payload = claims_payload
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1

        class _Raw:
            content = self._claims_payload

        return _Raw()


def test_synthesis_claims_gated(tmp_path: Path) -> None:
    from agent_core.agents.synthesis_agent import SynthesisAgent

    _runtime(tmp_path, policy="enforce")
    claims_json = json.dumps(
        [
            {
                "text": "Candidate A binds the target best",
                "claim_type": "ranking",
                "scope": "absolute",
                "dependencies": [
                    {"oracle": "egarps_native_probability", "capability": "ranking"}
                ],
            },
            {
                "text": "Candidate A satisfies all sequence constraints",
                "claim_type": "descriptive",
                "scope": "absolute",
                "dependencies": [],
            },
        ]
    )
    agent = SynthesisAgent(llm=_StubLLM(claims_json))
    report = agent._gate_report_claims("Candidate A is best.")
    assert "REJECTED" in report  # egarps failed profiling -> rejected
    assert "PASS" in report  # deterministic-content claim passes
    verdicts = [e for e in _audit_events(tmp_path) if e["event_type"] == "claim_verdict"]
    assert len(verdicts) == 2
    CalibratedRuntime.clear()


def test_synthesis_claim_extraction_failure_is_best_effort(tmp_path: Path) -> None:
    from agent_core.agents.synthesis_agent import SynthesisAgent

    _runtime(tmp_path, policy="enforce")

    class _BadLLM(_StubLLM):
        def __init__(self):
            super().__init__("[]")

        def invoke(self, messages):
            class _Raw:
                content = "not json at all"

            return _Raw()

    agent = SynthesisAgent(llm=_BadLLM())
    report = agent._gate_report_claims("Original report text.")
    assert report == "Original report text."  # unchanged on extraction failure
    CalibratedRuntime.clear()


# -------------------------------------------------------------- runtime_from_env


def test_runtime_from_env_off(monkeypatch, tmp_path: Path) -> None:
    from agent_core.calibrated.runtime import runtime_from_env

    monkeypatch.setenv("RNADA_CAPGATE", "off")
    monkeypatch.setenv("RNADA_CAPGATE_AUDIT", str(tmp_path / "a.jsonl"))
    assert runtime_from_env() is None
    assert CalibratedRuntime.instance() is None


def test_runtime_from_env_advisory(monkeypatch, tmp_path: Path) -> None:
    from agent_core.calibrated.runtime import runtime_from_env

    monkeypatch.setenv("RNADA_CAPGATE", "advisory")
    monkeypatch.setenv("RNADA_CAPGATE_AUDIT", str(tmp_path / "a.jsonl"))
    rt = runtime_from_env()
    assert rt is not None and rt.policy == "advisory"
    CalibratedRuntime.clear()
