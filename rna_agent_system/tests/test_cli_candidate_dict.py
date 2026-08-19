"""Tests for CLI Candidate JSON serialization helpers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

CLI_DIR = APP_ROOT / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from cli import form_chat
from agent_core.workflow_models import Candidate


def test_candidate_to_dict_merges_metrics_into_scores():
    """Raw metrics from metrics_bundle should also appear in the scores dict."""
    c = Candidate(
        id="cand_abc",
        sequence="GGCAAGGUUCUGCCCGGGGGGCGUCUUGCC",
        source="odesign",
        scores={
            "total_score": 0.7289,
            "egarps_component": 0.6213,
            "rhofold_component": 0.8366,
            "iptm_component": 0.3312,
        },
        metadata={
            "metrics_bundle": {
                "rhofold_mean_plddt": 83.66,
                "egarps_native_probability": 0.6213,
                "proteinx_ipTM": 0.3312,
                "interface_contacts": 13,
                "buried_sasa": 0.0,
                "hydrogen_bonds": 8,
                "salt_bridges": 0,
                "gc_content": 0.733,
            }
        },
    )
    d = form_chat._candidate_to_dict(c)

    # Score components and total must be preserved.
    assert d["scores"]["total_score"] == pytest.approx(0.7289, abs=1e-6)
    assert d["scores"]["egarps_component"] == pytest.approx(0.6213, abs=1e-6)
    assert d["scores"]["rhofold_component"] == pytest.approx(0.8366, abs=1e-6)

    # Raw metrics should be merged into scores for self-contained audit records.
    assert d["scores"]["rhofold_mean_plddt"] == pytest.approx(83.66, abs=1e-6)
    assert d["scores"]["egarps_native_probability"] == pytest.approx(0.6213, abs=1e-6)
    assert d["scores"]["proteinx_ipTM"] == pytest.approx(0.3312, abs=1e-6)
    assert d["scores"]["interface_contacts"] == 13
    assert d["scores"]["buried_sasa"] == pytest.approx(0.0, abs=1e-6)
    assert d["scores"]["hydrogen_bonds"] == 8
    assert d["scores"]["salt_bridges"] == 0

    # The dedicated metrics bucket must still be present.
    assert "metrics" in d
    assert d["metrics"]["rhofold_mean_plddt"] == pytest.approx(83.66, abs=1e-6)


def test_candidate_to_dict_does_not_overwrite_score_components():
    """Metrics with keys that collide with score components must not overwrite."""
    c = Candidate(
        id="cand_def",
        sequence="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        source="odesign",
        scores={"total_score": 0.5},
        metadata={"metrics_bundle": {"total_score": 999.0}},
    )
    d = form_chat._candidate_to_dict(c)
    # total_score in scores comes from candidate.scores, not metrics_bundle.
    assert d["scores"]["total_score"] == pytest.approx(0.5, abs=1e-6)
    assert d["metrics"]["total_score"] == pytest.approx(999.0, abs=1e-6)


def test_candidate_to_dict_handles_empty_metadata():
    """Candidates without metrics_bundle should still serialize."""
    c = Candidate(
        id="cand_ghi",
        sequence="GGGAAACCCUUUGGGAAACCCUUUGGGAAA",
        source="odesign",
        scores={"total_score": 0.3},
        metadata={},
    )
    d = form_chat._candidate_to_dict(c)
    assert d["scores"] == {"total_score": 0.3}
    assert d["metrics"] == {}


def test_save_workflow_results_persists_gennav_trace(tmp_path, monkeypatch):
    """Navigation-mode runs persist ``_gennav_trace`` in the CLI JSON artifact."""
    from agent_core.workflow_models import WorkflowResult

    wf = WorkflowResult(
        success=True,
        task_id="aptamer_test",
        summary="candidates=1",
        best_candidate=Candidate(id="c1", sequence="AUGCGCAUGCUGCAUGCUAGC"),
        all_candidates=[Candidate(id="c1", sequence="AUGCGCAUGCUGCAUGCUAGC")],
    )
    wf._state_writeback = {
        "_workflow_params": {"navigation": True},
        "_gennav_trace": {"raw_spent": 41, "raw_budget": 48, "rounds": []},
    }

    saved = {}
    monkeypatch.setattr(
        form_chat, "save_text_file",
        lambda content, **kw: saved.update(json.loads(content)) or "workflow_results_x.json",
    )
    out = form_chat._save_workflow_results({"workflow_result": wf}, "sess_test")
    assert out is not None
    assert saved["_gennav_trace"]["raw_spent"] == 41
    assert saved["workflow_input"] == {"navigation": True}
