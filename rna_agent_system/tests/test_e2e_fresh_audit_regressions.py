"""Regressions pinned by the 2026-08-22 full-platform E2E fresh-data audit.

Evidence: workspace/e2e_fresh_audit_2026-08-22/ (fetch_fresh_data.py,
run_e2e_audit.py, run_e2e_retry.py, run_e2e_fixup.py, audit_report.json —
56/56 checks). Three platform defects found on live-fetched data (IL4
NM_000589.4, CXCL8 NM_000584.4, CSFV NC_002657.1, Rfam RF00059, RCSB 1PGB,
RCSB 12CI, PubChem kanamycin A) are pinned here:

1. ``SgRnaDesignWorkflow`` hid a missing seed behind the generic
   empty-candidate failure ("No sgRNA handle candidates produced") — the
   documented XOR contract ("exactly one of seed_sequence/filepath") now
   raises a clear ValueError naming the missing input.
2. ``AgentRunner.stream_form`` raised ``RuntimeError`` out of the stream
   when the workflow hard-failed (empty candidates), while ``run_form``
   degrades gracefully — the stream now yields a final runner event
   carrying the failed state; only worker-thread exceptions still raise.
3. The ViennaRNA inverse-fold service accepted pseudoknot brackets
   (``[]{}<>``) at charset validation, but RNAinverse cannot parse them —
   in the packaged service env the binary crashed with SIGSEGV (exit -11)
   instead of erroring. The endpoint now rejects them up-front with an
   actionable message.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ═══════════════════════════════════════════════════════════════════════════════
# 1 — sgRNA design without a seed fails with a clear message
# ═══════════════════════════════════════════════════════════════════════════════


def test_sgrna_design_no_seed_raises_clear_error():
    """No seed → ValueError naming seed_sequence/seed_filepath (was: silent [])."""
    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.sgrna_design import (
        SgRnaDesignInput,
        SgRnaDesignWorkflow,
    )

    registry = build_default_capability_registry(
        ToolExecutor(build_default_tool_registry(include_demo=False))
    )
    wf = SgRnaDesignWorkflow(registry)
    inp = SgRnaDesignInput(target_sequence="A" * 60, off_target_sequences=[])

    with pytest.raises(ValueError, match="seed_sequence or seed_filepath is required"):
        wf.generate_candidates(inp)


def test_sgrna_design_run_surfaces_seed_error_in_summary():
    """The clear seed error survives base.run() into the WorkflowResult summary."""
    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.sgrna_design import (
        SgRnaDesignInput,
        SgRnaDesignWorkflow,
    )

    registry = build_default_capability_registry(
        ToolExecutor(build_default_tool_registry(include_demo=False))
    )
    wf = SgRnaDesignWorkflow(registry)
    # Bypass service pre-flight so the test does not depend on the CRGPT
    # service being up; the seed check happens inside generate_candidates.
    object.__setattr__(wf, "_service_preflight_result", lambda: None)
    inp = SgRnaDesignInput(target_sequence="A" * 60, off_target_sequences=[])

    result = wf.run(inp)
    assert result.success is False
    assert "seed_sequence or seed_filepath is required" in result.summary
    assert any(
        "seed_sequence or seed_filepath is required" in e for e in result.errors
    )
    assert "empty_candidate_list" not in result.errors


# ═══════════════════════════════════════════════════════════════════════════════
# 2 — stream_form degrades gracefully on workflow hard failure
# ═══════════════════════════════════════════════════════════════════════════════


class _HardFailingWorkflow:
    """Minimal workflow whose run() always hard-fails (empty candidates)."""

    name = "mock_hard_fail"
    input_model = None

    def run(self, inp, *, progress_callback=None):
        from agent_core.workflow_models import WorkflowResult

        return WorkflowResult(
            success=False,
            task_id="",
            summary="No candidates produced.",
            errors=["empty_candidate_list"],
        )


@pytest.fixture
def stream_runner():
    from agent_core.agents.quality_agent import QualityProfile, QualityReport
    from agent_core.agents.specialist_agent import SpecialistAgent
    from agent_core.runner import AgentRunner
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    runner = AgentRunner(
        executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
        quality_review_enabled=False,
    )
    runner.specialist_registry["mock_hard_fail"] = SpecialistAgent(
        _HardFailingWorkflow(),
        QualityProfile(workflow_name="mock_hard_fail", max_retries=0),
    )
    # Stub the LLM-coupled agents so the test stays offline and deterministic.
    # quality_reports entries are validated into QualityReport models by
    # PipelineResult, so return a real instance (dict would also validate).
    passing_report = QualityReport(
        overall_assessment="stub", quality_score=1.0, action="pass"
    )
    runner.pipeline_agent.quality_agent = SimpleNamespace(
        review=lambda *a, **k: passing_report
    )
    runner.pipeline_agent.synthesis_agent = SimpleNamespace(
        synthesize=lambda *a, **k: "report"
    )
    return runner


def test_stream_form_hard_failure_yields_final_runner_event(stream_runner):
    """A hard-failing workflow must not raise out of the stream (run_form parity).

    Pre-fix: RuntimeError('执行失败: empty_candidate_list') escaped stream_form
    and the caller never received the runner event / failed state.
    """
    events: list[str] = []
    final_state = None
    for ev in stream_runner.stream_form(
        {"seq": "AUGCGC"},
        session_id="test_stream_hard_fail",
        explicit_workflow="mock_hard_fail",
    ):
        for node_name, node_state in ev.items():
            events.append(node_name)
            if node_name == "runner":
                final_state = node_state

    assert events, "stream produced no events"
    assert events[-1] == "runner"
    assert final_state is not None
    wf = final_state.get("workflow_result")
    assert wf is not None and getattr(wf, "success", True) is False
    assert getattr(wf, "errors", None) == ["empty_candidate_list"]


def test_stream_form_worker_exception_still_raises(stream_runner, monkeypatch):
    """Genuine worker-thread crashes still raise out of the stream."""

    def _explode(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(stream_runner.pipeline_agent, "execute", _explode)
    with pytest.raises(RuntimeError, match="执行失败: boom"):
        list(
            stream_runner.stream_form(
                {"seq": "AUGCGC"},
                session_id="test_stream_exc",
                explicit_workflow="mock_hard_fail",
            )
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3 — ViennaRNA inverse-fold rejects pseudoknot brackets up-front
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def viennarna_main():
    spec = importlib.util.spec_from_file_location(
        "viennarna_fold_main_test", PROJECT_ROOT / "microservices" / "viennarna_fold" / "main.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def viennarna_params(viennarna_main):
    """Duck-typed stand-in for ViennaModelParams (pydantic forward refs do not
    resolve under the synthetic module name; the CLI builder only reads attrs)."""
    return SimpleNamespace(
        temp_c=37.0, dangles=2, noGU=False, noClosingGU=False, salt=None,
        noTetra=False, energyModel=None, nsp=None, paramFile=None,
    )


@pytest.mark.parametrize(
    "structure",
    ["((..))..[[", "(((..)))<<..>>", "..{..}.."],
)
def test_inverse_fold_rejects_pseudoknot_brackets(viennarna_main, monkeypatch, structure):
    """Pseudoknot brackets must be rejected before RNAinverse is invoked.

    Pre-fix: the charset check allowed []{}<>, RNAinverse then crashed with
    SIGSEGV (exit -11) in the packaged service env and surfaced as an opaque
    503. The sentinel _run_cli proves no subprocess is reached.
    """
    monkeypatch.setattr(viennarna_main, "_RNAINVERSE_EXE", "/usr/bin/RNAinverse")

    def _no_cli(*a, **k):
        raise AssertionError("RNAinverse CLI must not be invoked for pseudoknot input")

    monkeypatch.setattr(viennarna_main, "_run_cli", _no_cli)
    with pytest.raises(ValueError, match="pseudoknot"):
        viennarna_main._inverse_fold_cli(structure, "", None, 1, "m")


def test_inverse_fold_plain_dot_bracket_passes_charset(viennarna_main, viennarna_params, monkeypatch):
    """Plain dot-bracket input passes the pseudoknot gate and reaches the CLI."""
    monkeypatch.setattr(viennarna_main, "_RNAINVERSE_EXE", "/usr/bin/RNAinverse")

    def _sentinel_cli(*a, **k):
        raise RuntimeError("cli-reached")

    monkeypatch.setattr(viennarna_main, "_run_cli", _sentinel_cli)
    with pytest.raises(RuntimeError, match="cli-reached"):
        viennarna_main._inverse_fold_cli("((..))..((..))", "", viennarna_params, 1, "m")
