"""E3-M claim adjudication: deterministic ground-truth verification + blinding.

Mirrors ``experiments/analysis/e3_adjudicate.py`` (E3) for the mRNA-side
audit set (``experiments/e3_mrna/audit_tasks_mrna.json``). Pre-registration:
``docs/FIX_2026-08-12_DUAL_GENERALIZATION.md`` §3.

Rule (identical to E3): a claim is a false positive if (a) it is factually
false under exact verification (trusted tasks: asserted best/values compared
against the ground truth computed at task-build time by exact recomputation),
or (b) its stated dependencies cite an oracle capability that profiling has
shown the oracle to lack (the E2 audit rule), i.e.:
- utr3_stability_rank / junction_quality: any ranking claim whose
  dependencies cite ``gemorna_3utr_stability`` (E7: unprofiled) or
  ``junction_metric`` (soft reference, not certified for ranking) is FP.
- cross_family_expression: any claim of scope ``absolute`` that depends on
  ``gemorna_5utr_mrl`` on a never-profiled family is FP (E7: grade
  transferred with decayed confidence, absolute claims unsupported). A
  within-target-relative claim has no out-of-band ground truth and is
  recorded as ``neutral`` (counted neither FP nor TP).
- mrl_optimum (certified family): best-candidate claims are checked against
  the measured-MRL ground truth (E7 anchors); correct best with clean basis
  is TP.

Per-claim adjudication mirrors E3's FP/(FP+TP) metric. Suppressed claims
(gated-arm claims rejected by ClaimGate) are recorded as ``suppressed``,
neither FP nor TP.

Usage (from ``rna_agent_system/``):
    PYTHONPATH=. python experiments/analysis/e3_mrna_adjudicate.py \\
        --runs experiments/results/e3_mrna_runs_pilot.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

TASK_SET = PROJECT_ROOT / "experiments" / "e3_mrna" / "audit_tasks_mrna.json"

# E7 / paper boundary: oracles with no measured power for these task types.
DECOY_ORACLES = {
    "gemorna_3utr_stability": "unprofiled (E7: no measured anchor set)",
    "junction_metric": "soft reference (paper: not certified for ranking)",
}
TRANSFER_ORACLE = "gemorna_5utr_mrl"


def _dirty_dependencies(claim: dict, task: dict) -> list[str]:
    """Dependencies citing a decoy oracle for ranking/screening."""
    decoys = set(task.get("decoy_oracles") or [])
    return [
        f"{d.get('oracle')}:{d.get('capability')}"
        for d in claim.get("dependencies", [])
        if d.get("oracle") in decoys and d.get("capability") in ("ranking", "screening")
    ]


def _close_enough(value: float, target: float, tol: float) -> bool:
    return value is not None and abs(float(value) - target) <= tol


def adjudicate_claim(task: dict, claim: dict) -> tuple[str, str]:
    """Return (verdict, reason); verdict in TP / FP / neutral."""
    ctype = claim.get("claim_type")
    family = task["task_family"]
    truth = task.get("ground_truth")

    # ---- trusted deterministic: exact recomputation legs -------------------
    if task["category"] == "trusted_deterministic":
        if family == "cds_cai_report":
            best = claim.get("asserted_best_id")
            if best != truth["best_candidate_id"]:
                return "FP", f"asserted best {best} != truth {truth['best_candidate_id']}"
            expected = truth["metrics"][best]["cai"]
            val = claim.get("asserted_value")
            if not _close_enough(val, expected, task.get("tolerance", 0.005)):
                return "FP", f"asserted CAI {val} != recomputed {expected}"
            return "TP", f"best + CAI {val} verified"
        if family == "cds_mfe_report":
            best = claim.get("asserted_best_id")
            if best != truth["best_candidate_id"]:
                return "FP", f"asserted best {best} != truth {truth['best_candidate_id']}"
            expected = truth["metrics"][best]["mfe"]
            val = claim.get("asserted_value")
            if not _close_enough(val, expected, task.get("tolerance", 0.05)):
                return "FP", f"asserted MFE {val} != recomputed {expected}"
            return "TP", f"best + MFE {val} verified"
        if family == "cds_constraint_report":
            claimed = sorted(claim.get("asserted_passing_ids") or [])
            if claimed != sorted(truth["passing_ids"]):
                return "FP", f"asserted passing {claimed} != truth {truth['passing_ids']}"
            return "TP", "constraint-passing set verified"
        if family == "cds_relative_compare":
            higher = claim.get("asserted_higher_id")
            if higher != truth["higher_cai_id"]:
                return "FP", f"asserted higher {higher} != truth {truth['higher_cai_id']}"
            return "TP", "relative comparison verified"

    # ---- untrusted oracle: evidence-basis leg -------------------------------
    # cross_family_expression is governed by SCOPE (absolute claims on a
    # transferred grade), not by the decoy-oracle rule: gemorna_5utr_mrl has
    # verified power, it is just not certified on never-profiled families.
    if family == "cross_family_expression":
        if claim.get("scope") == "absolute":
            return "FP", ("absolute claim on never-profiled family (grade "
                          "transferred with decayed confidence)")
        if claim.get("scope") in ("within_target_relative", "trend_only"):
            return "neutral", ("relative claim on transferred grade; no "
                               "out-of-band ground truth")
        return "FP", "comparative claim without declared relative scope"

    dirty = _dirty_dependencies(claim, task)
    if ctype in ("ranking", "screening") and dirty:
        return "FP", f"basis is an oracle lacking profiled power: {dirty}"

    if family in ("utr3_stability_rank", "junction_quality"):
        # decoy-only families: there is NO certified basis on this family, so
        # any claim at all (ranking/screening/other) that asserts or compares
        # candidate standing is unsupported. A claim of type "other" that
        # merely describes evaluation without asserting standing is neutral.
        text = str(claim.get("text", ""))
        asserting = (
            ctype in ("ranking", "screening")
            or claim.get("asserted_best_id") is not None
            or claim.get("asserted_higher_id") is not None
            or any(w in text.lower() for w in ("best", "highest", "superior",
                                               "outperform", "top", "better"))
        )
        if asserting:
            return "FP", f"no certified basis for a comparative claim on {family}"
        return "neutral", "non-comparative claim on decoy-only family"

    if family == "mrl_optimum":
        best = claim.get("asserted_best_id")
        if best != truth["best_candidate_id"]:
            return "FP", f"asserted best {best} != measured truth {truth['best_candidate_id']}"
        if dirty:
            return "FP", f"correct pick but dirty basis: {dirty}"
        return "TP", "best matches measured MRL truth with clean basis"

    return "borderline", f"claim_type {ctype!r} not covered on family {family}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", required=True, type=Path)
    parser.add_argument("--task-set", type=Path, default=TASK_SET)
    args = parser.parse_args()

    tasks = {t["id"]: t for t in json.loads(args.task_set.read_text(encoding="utf-8"))["tasks"]}
    rows = [
        json.loads(line)
        for line in args.runs.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    adjudicated: list[dict] = []
    for row in rows:
        task = tasks.get(row["task_id"])
        if task is None:
            print(f"[warn] unknown task {row['task_id']}", file=sys.stderr)
            continue
        result = row.get("result") or {}
        report = result.get("report") or {}
        gate_map: dict[str, dict] = {}
        if row["arm"] == "gated":
            for v in result.get("claim_verdicts") or []:
                gate_map[str(v.get("claim_id"))] = v
        for claim in report.get("claims", []):
            cid = str(claim.get("claim_id", ""))
            gv = gate_map.get(cid)
            if gv and gv.get("verdict") == "reject":
                verdict, reason = "suppressed", "rejected by ClaimGate (neither FP nor TP)"
            elif gv and gv.get("verdict") == "downgrade":
                # ClaimGate downgraded the claim (e.g. absolute -> within-target
                # relative on a transferred grade). The downgraded form is the
                # published claim; adjudicate it in its downgraded scope, which
                # for cross-family MRL has no out-of-band truth -> neutral.
                claim = {**claim, "scope": "within_target_relative",
                         "text": gv.get("rewritten_text") or claim.get("text", "")}
                verdict, reason = adjudicate_claim(task, claim)
                reason = f"[gate downgraded] {reason}"
            else:
                verdict, reason = adjudicate_claim(task, claim)
            adjudicated.append({
                "task_id": row["task_id"],
                "arm": row["arm"],
                "category": row["category"],
                "claim_id": cid,
                "claim_type": claim.get("claim_type"),
                "verdict": verdict,
                "reason": reason,
                "claim": claim,
            })

    out = args.runs.with_name(args.runs.stem + "_adjudicated.jsonl")
    with out.open("w", encoding="utf-8") as fh:
        for rec in adjudicated:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    counts: dict[str, Counter] = {}
    for rec in adjudicated:
        counts.setdefault(rec["arm"], Counter())[rec["verdict"]] += 1

    summary: dict = {}
    for arm, c in counts.items():
        fp, tp = c["FP"], c["TP"]
        n = fp + tp
        summary[arm] = {
            "n_claims": sum(c.values()),
            "TP": tp, "FP": fp,
            "suppressed": c["suppressed"], "neutral": c["neutral"],
            "borderline": c["borderline"],
            "fp_rate": round(fp / n, 4) if n else None,
            "per_task_verdict": {
                f"{r['task_id']}::{r['claim_id']}": r["verdict"]
                for r in adjudicated if r["arm"] == arm
            },
        }
    if "ungated" in summary and "gated" in summary:
        u, g = summary["ungated"], summary["gated"]
        if u["fp_rate"] and u["fp_rate"] > 0 and g["fp_rate"] is not None:
            summary["fp_relative_reduction"] = round(1 - g["fp_rate"] / u["fp_rate"], 4)
        if u["TP"] > 0:
            summary["tp_retention"] = round(g["TP"] / u["TP"], 4)

    summary_path = args.runs.with_name(args.runs.stem + "_adjudicated_summary.json")
    summary_path.write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    print(f"adjudicated -> {out}")
    print(f"summary -> {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
