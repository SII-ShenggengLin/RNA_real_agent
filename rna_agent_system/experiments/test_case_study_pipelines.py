#!/usr/bin/env python3
"""Pure-function tests for experiments/run_case_study_pipelines.py.

Uses real session artifacts as fixtures (fig2/fig3/fig4 sessions and
fig3_anchors.json). Run from rna_agent_system/:
    PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest experiments/test_case_study_pipelines.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_case_study_pipelines import (  # noqa: E402
    PROJECT_ROOT,
    SIRNA_GC_WINDOW,
    build_anchor_overlay,
    check_sirna_rules,
    extract_designed_mrna_metrics,
    extract_interface_outputs,
    extract_sirna_safety_table,
    latest_workflow_results,
    load_done_nodes,
    pa016_turn1_params,
)

SESSIONS = PROJECT_ROOT / "workspace" / "sessions"


def _latest(session_prefix: str) -> dict:
    dirs = sorted(SESSIONS.glob(f"{session_prefix}*"))
    assert dirs, f"no session fixture matching {session_prefix}"
    for d in reversed(dirs):
        res = latest_workflow_results(d.name)
        if res is not None:
            return res
    raise AssertionError(f"no readable workflow_results under {session_prefix}")


def test_extract_designed_mrna_metrics_real_fig3_session():
    res = _latest("fig3t1_")
    m = extract_designed_mrna_metrics(res)
    assert m["cds_cai"] is not None and 0 < m["cds_cai"] <= 1
    assert m["cds_mfe"] is not None and m["cds_mfe"] < 0
    assert m["full_mfe_per_nt"] is not None
    assert "junction_5utr_cds_aug_buried" in m


def test_build_anchor_overlay_rows():
    anchors_path = PROJECT_ROOT / "experiments" / "results" / "fig3_anchors.json"
    anchors = json.loads(anchors_path.read_text())
    designed = extract_designed_mrna_metrics(_latest("fig3t1_"))
    rows = build_anchor_overlay(designed, anchors)
    assert rows[0]["molecule"] == "designed_case_a"
    names = {r["molecule"] for r in rows}
    assert "bnt162b2" in names and "mrna1273" in names
    bnt = next(r for r in rows if r["molecule"] == "bnt162b2")
    assert bnt["cds_cai"] == pytest.approx(0.9515, abs=1e-3)
    assert bnt["utr5_mrl"] is not None


def test_check_sirna_rules_gc_window():
    ok = check_sirna_rules({"gc_content": 0.45, "duplex_mfe": -35.0,
                            "off_target_count": 0, "specificity_score": 1.0})
    assert ok["gc_in_30_60_pct"] is True
    hi = check_sirna_rules({"gc_content": 0.75})
    assert hi["gc_in_30_60_pct"] is False
    none = check_sirna_rules({})
    assert none["gc_in_30_60_pct"] is None
    assert SIRNA_GC_WINDOW == (0.30, 0.60)


def test_extract_sirna_safety_table_real_fig2_session():
    res = _latest("fig2_04_sirna_design_003")
    table = extract_sirna_safety_table(res)
    assert table, "expected siRNA candidates in fixture session"
    for row in table:
        assert "gc_in_30_60_pct" in row and "off_target_count" in row
    ranks = [r.get("total_rank") for r in table if r.get("total_rank") is not None]
    assert ranks == sorted(ranks)


def test_extract_interface_outputs_real_fig4_session():
    res = _latest("fig4t2_")
    out = extract_interface_outputs(res)
    top = out["top_candidate"]
    assert top["sequence"], "top candidate should carry a sequence"
    assert top["egarps_component"] is not None
    assert out["candidate_count"]


def test_pa016_turn1_params_verbatim_shape():
    params = pa016_turn1_params()
    assert params["mode"] == "antiviral"
    assert params["target_sequence"].startswith("GAAACUG")
    assert "bowtie2" in json.dumps(params)


def test_load_done_nodes_skips_success_only(tmp_path):
    p = tmp_path / "nodes.jsonl"
    p.write_text(
        json.dumps({"node_id": "design", "success": True}) + "\n"
        + json.dumps({"node_id": "scan", "success": False}) + "\n"
    )
    done = load_done_nodes(p)
    assert done == {"design"}
