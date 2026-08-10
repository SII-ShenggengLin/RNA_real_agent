#!/usr/bin/env python3
"""Fig 2 summary statistics (docs/MANUSCRIPT.md §4).

Aggregates the Fig-2 JSONLs into `experiments/results/fig2_summary.json`:
- per-workflow coverage / latency
- CDS nulls comparison (WT vs random-synonymous vs CAI-only)
- 2D / 3D structure design quality
- siRNA off-target profile
- aptamer objective distributions
- small-molecule and IRES AUROCs with bootstrap CIs

Usage (from `rna_agent_system/`):
    python experiments/analysis/summarize_fig2.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats_utils import auroc, bh_fdr, bootstrap_auroc_ci, cliffs_delta, mannwhitney_p, wilcoxon_paired  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "experiments" / "results"


def load_latest(path: Path) -> list[dict]:
    """Load a JSONL, keeping the latest record per task_id (or per arm key)."""
    if not path.exists():
        return []
    latest: dict = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        latest[r.get("task_id") or (r.get("target_id"), r.get("arm"), r.get("rep"))] = r
    return list(latest.values())


def get_metric(record: dict, key: str):
    best = record.get("best_candidate") or {}
    for container in (best.get("scores") or {}, best.get("metrics") or {}):
        if key in container:
            return container[key]
    return None


def main() -> int:
    summary: dict = {"generated_by": "experiments/analysis/summarize_fig2.py"}

    # ---------------- coverage ----------------
    recs = (
        load_latest(RESULTS / "fig2_cpu_a.jsonl")
        + load_latest(RESULTS / "fig2_cpu_b.jsonl")
        + load_latest(RESULTS / "fig2_gpu.jsonl")
    )
    by_wf: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        by_wf[r["workflow"]].append(r)
    coverage = {}
    for wf, rs in sorted(by_wf.items()):
        ok = [r for r in rs if r["success"]]
        coverage[wf] = {
            "n_tasks": len(rs),
            "n_success": len(ok),
            "median_elapsed_s": round(st.median(r["elapsed_seconds"] for r in rs), 1),
            "notes": ([r["task_id"] for r in rs if not r["success"]] or None),
        }
    summary["coverage"] = coverage
    summary["total"] = {"n_tasks": len(recs), "n_success": sum(1 for r in recs if r["success"])}

    # ---------------- Fig 2a: CDS nulls ----------------
    nulls = load_latest(RESULTS / "fig2_cds_nulls.jsonl")
    arms: dict[str, list[dict]] = defaultdict(list)
    for r in nulls:
        if r["success"] and r.get("cai_score") is not None:
            arms[r["arm"]].append(r)
    nulls_out: dict = {"n": {a: len(v) for a, v in arms.items()}}
    for metric in ("cai_score", "mfe_per_nt", "gc_content"):
        groups = {a: [r[metric] for r in v if r.get(metric) is not None] for a, v in arms.items()}
        nulls_out[metric] = {
            a: {"median": st.median(v) if v else None} for a, v in groups.items()
        }
        if groups.get("wt") and groups.get("random_syn"):
            nulls_out[metric]["wt_vs_random"] = {
                "mannwhitney_p": mannwhitney_p(groups["wt"], groups["random_syn"]),
                "cliffs_delta": cliffs_delta(groups["wt"], groups["random_syn"]),
            }
    # paired per-target WT vs mean(random)
    wt_by_t = {r["target_id"]: r for r in arms.get("wt", [])}
    rnd_by_t: dict[str, list[dict]] = defaultdict(list)
    for r in arms.get("random_syn", []):
        rnd_by_t[r["target_id"]].append(r)
    paired_targets = [t for t in wt_by_t if t in rnd_by_t]
    wins_cai = sum(
        1 for t in paired_targets
        if wt_by_t[t]["cai_score"] > st.mean(x["cai_score"] for x in rnd_by_t[t])
    )
    nulls_out["paired_wt_beats_random_cai"] = f"{wins_cai}/{len(paired_targets)}"
    summary["fig2a_cds_nulls"] = nulls_out

    # ---------------- Fig 2e: secondary structure design ----------------
    ss = [r for r in by_wf.get("rna_secondary_structure_design", []) if r["success"]]
    dists = [get_metric(r, "structure_distance") for r in ss]
    dists = [d for d in dists if d is not None]
    summary["fig2e_secondary_design"] = {
        "n": len(dists),
        "exact_match": sum(1 for d in dists if d == 0),
        "exact_match_rate": round(sum(1 for d in dists if d == 0) / len(dists), 3) if dists else None,
        "median_distance": st.median(dists) if dists else None,
    }

    # ---------------- Fig 2f: tertiary design ----------------
    ter = [r for r in by_wf.get("rna_tertiary_structure_design", []) if r["success"]]
    plddt = [get_metric(r, "rhofold_component") for r in ter]
    plddt = [p for p in plddt if p is not None]
    summary["fig2f_tertiary_design"] = {
        "n": len(plddt),
        "median_plddt_component": round(st.median(plddt), 3) if plddt else None,
    }

    # ---------------- Fig 2c: siRNA ----------------
    sir = [r for r in by_wf.get("sirna_design", []) if r["success"]]
    ot = [get_metric(r, "off_target_count") for r in sir]
    ot = [x for x in ot if x is not None]
    summary["fig2c_sirna"] = {
        "n": len(ot),
        "median_off_target": st.median(ot) if ot else None,
        "zero_off_target": f"{sum(1 for x in ot if x == 0)}/{len(ot)}",
        "quality_abort_cases": [r["task_id"] for r in by_wf.get("sirna_design", []) if not r["success"]],
    }

    # ---------------- panels ----------------
    panels_path = RESULTS / "fig2_literature_panels.jsonl"
    if panels_path.exists():
        panels = [json.loads(l) for l in panels_path.read_text().splitlines() if l.strip()]
        ires = [r for r in panels if r["panel"] == "ires" and r["success"] and r.get("best_ires_probability") is not None]
        pos = [r["best_ires_probability"] for r in ires if r["label"] == "positive"]
        neg = [r["best_ires_probability"] for r in ires if r["label"] == "negative"]
        point, lo, hi = bootstrap_auroc_ci(pos, neg)
        summary["fig2i_ires"] = {
            "n_pos": len(pos), "n_neg": len(neg),
            "positives": {r["seq_id"]: r["best_ires_probability"] for r in ires if r["label"] == "positive"},
            "auroc": round(point, 3), "auroc_ci95": [round(lo, 3), round(hi, 3)],
        }
        smol = [r for r in panels if r["panel"] == "small_mol" and r["success"] and r.get("total_score") is not None]
        b = [r["total_score"] for r in smol if r["expected"] == "binder"]
        nc = [r["total_score"] for r in smol if r.get("negative_class") == "near_cognate"]
        rc = [r["total_score"] for r in smol if r.get("negative_class") == "random_chemistry"]
        summary["fig2h_small_molecule"] = {
            "n_binders": len(b), "n_near_cognate": len(nc), "n_random_chem": len(rc),
            "auroc_vs_random_chem": round(auroc(b, rc), 3),
            "auroc_vs_near_cognate": round(auroc(b, nc), 3),
            "note": "scores reflect the underlying RNAsmol/GerNA-Bind models on short aptamers "
                    "(out-of-training-distribution); reported as a tool-boundary finding",
        }

    out_path = RESULTS / "fig2_summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n-> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
