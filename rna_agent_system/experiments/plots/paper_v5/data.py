"""Data loaders for paper_v5 panels.

Every panel reads its numbers from the retained experiment evidence under
``experiments/results/`` (the PAPER_FACT_SHEET audit trail) - nothing is
hard-coded except file paths and small presentational constants.
"""

from __future__ import annotations

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[2] / "results"
SYSTEM = Path(__file__).resolve().parents[3]
PLOTS = Path(__file__).resolve().parent
PANELS = PLOTS  # per-figure dirs live beside this module


def load_json(name: str):
    with open(RESULTS / name) as f:
        return json.load(f)


def load_jsonl(name: str):
    rows = []
    with open(RESULTS / name) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------- fig 2 sources
def fig2_summary() -> dict:
    return load_json("fig2_summary.json")


def fig2_runtime_rows() -> list[dict]:
    rows = []
    for fn in ("fig2_cpu_a.jsonl", "fig2_cpu_b.jsonl", "fig2_gpu.jsonl",
               "fig2_cds_nulls.jsonl", "fig2_literature_panels.jsonl"):
        p = RESULTS / fn
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return [r for r in rows if r.get("success") and r.get("elapsed_seconds")
            and r.get("workflow")]


def pa_regression_rows() -> list[dict]:
    """Per-task rows of the two process-aware regression batches (2026-08-19)."""
    rows = []
    for d in ("pa_regression_2026-08-19", "pa_regression_batchB_2026-08-19"):
        p = RESULTS / d / "summary.tsv"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if not line or line.startswith("#") or line.startswith("pa\t"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            rows.append({"batch": d.split("_")[-1], "pa": parts[0],
                         "workflow": parts[1], "exit": int(parts[2]),
                         "failed_turns": int(parts[3]),
                         "duration_s": float(parts[4])})
    return rows


def audit_trail_stats() -> dict:
    """Composition of the production CapGate audit trail."""
    from collections import Counter
    p = SYSTEM / "workspace" / "audit" / "platform_audit.jsonl"
    tools = Counter(); verdicts = Counter(); ttypes = Counter()
    succ = fail = gated = 0
    sessions = set()
    with open(p) as f:
        for line in f:
            r = json.loads(line)
            pay = r["payload"]
            if r["event_type"] == "tool_call":
                tools[pay.get("tool") or pay.get("tool_name", "?")] += 1
                succ += bool(pay.get("success"))
                fail += not pay.get("success")
                gated += bool(pay.get("gated"))
                if pay.get("session_id"):
                    sessions.add(pay["session_id"])
                if pay.get("task_type"):
                    ttypes[pay["task_type"]] += 1
            else:
                verdicts[pay.get("verdict", "?")] += 1
    return {"n_tool_calls": succ + fail, "n_success": succ, "n_fail": fail,
            "n_gated": gated, "n_gate_decisions": sum(verdicts.values()),
            "verdicts": dict(verdicts), "n_tools": len(tools),
            "n_sessions": len(sessions), "n_task_types": len(ttypes),
            "top_tools": tools.most_common(10)}


# ---------------------------------------------------------------- fig 3 sources
def e1_capability() -> dict:
    return load_json("e1_capability_summary_v2.json")


def p2_calibration() -> dict:
    return load_json("p2_aptamer_calibration_summary.json")


def rnasmol_boundary() -> dict:
    return load_json("rnasmol_boundary_panel.json")


def e7_profile() -> dict:
    return load_json("e7_mrna_oracle_profile_summary.json")


def e3_runs() -> list[dict]:
    return load_jsonl("e3_runs_full.jsonl")


def p0_budget() -> dict:
    return load_json("p0_budget_matched_summary.json")


def p3_guided() -> dict:
    return load_json("p3_guided_vs_unguided_summary.json")


def fig4_ungated() -> dict:
    return load_json("fig4_summary.json")


# ---------------------------------------------------------------- fig 4 sources
def e3_summary() -> dict:
    return load_json("e3_runs_full_summary.json")


def quality_ablation_rows() -> list[dict]:
    return load_jsonl("fig6_quality_ablation.jsonl")


# ---------------------------------------------------------------- fig 5 sources
def e6_s2_verdict() -> dict:
    return load_json("e6_s2_verdict_aggregated.json")


def e6_s2_runs() -> list[dict]:
    return load_jsonl("e6_s2_runs.jsonl")


def e5_report_numbers() -> dict:
    """Key E5 selection-layer numbers quoted in the manuscript (report-backed)."""
    return {
        "insulin_batch_diversity": 0.0082,     # D1 edit distance < 2% gate
        "diversity_gate": 0.02,
        "gfp_pool_pass_before": 0, "gfp_pool_size": 315,
        "gfp_pool_pass_after_ecoli_table": 12,
        "a1at_pool_pass": 60, "insulin_pool_pass": 92, "epo_pool_pass": 306,
        "il2_pool_pass": 192,
    }


def aptamer_verdict(stage: str) -> dict:
    return load_json(f"e{stage}_verdict_s2.json")


def gennav_production_runs() -> list[dict]:
    """Production navigation runs (platform wiring verification, 2026-08-19)."""
    out = []
    base = RESULTS / "pa_regression_batchB_2026-08-19"
    for fn, label in (("gennav_1ca2_navigation_result.json", "1CA2"),
                      ("gennav_3cna_navigation_result.json", "3CNA")):
        p = base / fn
        if p.exists():
            out.append({"target": label, "data": json.loads(p.read_text())})
    p = RESULTS / "gennav_live_verification_2026-08-19" / "vegf_1vpf_navigation_result.json"
    if p.exists():
        out.append({"target": "VEGF", "data": json.loads(p.read_text())})
    return out


# ---------------------------------------------------------------- fig 6 sources
def junction_summaries() -> dict:
    return {
        "p1": load_json("p1_junction_optimizer_summary.json"),
        "p1v2": load_json("p1_v2_stability_sweep_summary.json"),
        "integrated": load_json("junction_integrated_optimizer_summary.json"),
        "ddg": load_json("junction_ddg_pilot_summary.json"),
    }


def e4_memory() -> dict:
    return load_json("e4_full_summary.json")


def failure_taxonomy() -> dict:
    return load_json("failure_taxonomy.json")


def fig3_summary() -> dict:
    return load_json("fig3_summary.json")
