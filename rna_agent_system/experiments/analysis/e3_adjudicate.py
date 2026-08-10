"""E3 claim adjudication: deterministic ground-truth verification + blinding.

Implements the E3 pre-registered adjudication rule (driver docstring):
a claim is a false positive if (a) factually false under exact verification,
or (b) its stated dependencies cite an oracle capability that profiling has
shown the oracle to lack (the E2 audit rule). Gated-arm claims rejected by
ClaimGate are recorded as ``suppressed`` (neither FP nor TP).

Also produces a blinded claim file (arm labels stripped, shuffled with a
recorded seed) plus a sealed mapping, for the optional blinded LLM review of
borderline claims (--llm-review); disagreements with the deterministic
verdicts are flagged for the user.

Usage:
    PYTHONPATH=. python experiments/analysis/e3_adjudicate.py \
        --runs experiments/results/e3_runs_pilot.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

TASK_SET = PROJECT_ROOT / "experiments" / "e3" / "audit_tasks.json"
DEFAULT_OUT_SUFFIX = "_adjudicated.jsonl"

METRICS = {
    "gc_content": lambda s: (s.count("G") + s.count("C")) / len(s),
    "u_content": lambda s: s.count("U") / len(s),
    "purine_content": lambda s: (s.count("A") + s.count("G")) / len(s),
}


def _constraint_ok(value: float, constraint: dict) -> bool:
    if constraint["kind"] == "band":
        return constraint["lo"] <= value <= constraint["hi"]
    return value <= constraint["hi"]


def _dirty_dependencies(claim: dict, structural_oracles: list[str]) -> list[str]:
    """Dependencies citing a structural oracle for ranking/screening."""
    return [
        f"{d.get('oracle')}:{d.get('capability')}"
        for d in claim.get("dependencies", [])
        if d.get("oracle") in structural_oracles
        and d.get("capability") in ("ranking", "screening")
    ]


def adjudicate_claim(task: dict, report: dict, claim: dict, structural_oracles: list[str]) -> tuple[str, str]:
    """Return (verdict, reason); verdict in TP / FP / borderline."""
    ctype = claim.get("claim_type")
    if task["category"] == "trusted_deterministic" or ctype == "metric":
        seq = (report.get("final_sequence") or "").strip().upper().replace("T", "U")
        metric = task.get("metric") or claim.get("metric")
        if not seq or metric not in METRICS:
            return "FP", "missing final_sequence or unknown metric; unverifiable"
        if len(seq) != len(task["initial_sequence"]):
            return "FP", f"length changed ({len(seq)} != {len(task['initial_sequence'])})"
        actual = METRICS[metric](seq)
        asserted = claim.get("asserted_value")
        tol = task.get("tolerance", 0.01)
        if asserted is None or abs(float(asserted) - actual) > tol:
            return "FP", f"asserted {asserted} vs recomputed {actual:.4f} (tol {tol})"
        if not _constraint_ok(actual, task["constraint"]):
            return "FP", f"constraint violated: {metric}={actual:.4f} not within {task['constraint']}"
        return "TP", f"verified: {metric}={actual:.4f}"

    gt = task["ground_truth"]
    dirty = _dirty_dependencies(claim, structural_oracles)
    if ctype == "ranking":
        best = claim.get("asserted_best_id")
        if best != gt["best_candidate_id"]:
            return "FP", f"asserted best {best} != Kd ground truth {gt['best_candidate_id']}"
        if dirty:
            return "FP", f"correct pick but basis is an oracle lacking profiled power: {dirty}"
        return "TP", "best candidate matches Kd ground truth with clean basis"
    if ctype == "screening":
        claimed = sorted(claim.get("asserted_binder_ids") or [])
        if claimed != gt["binder_ids"]:
            return "FP", f"asserted binders {claimed} != truth {gt['binder_ids']}"
        if dirty:
            return "FP", f"correct set but basis is an oracle lacking profiled power: {dirty}"
        return "TP", "binder set matches ground truth with clean basis"
    return "borderline", f"claim_type {ctype!r} not covered by deterministic rules"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--llm-review", action="store_true",
                        help="run the blinded LLM pass over borderline claims")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    payload = json.loads(TASK_SET.read_text(encoding="utf-8"))
    structural_oracles = payload["structural_oracles"]
    tasks = {t["id"]: t for t in payload["tasks"]}
    out_path = args.output or args.runs.with_name(args.runs.stem + DEFAULT_OUT_SUFFIX)

    rows = [
        json.loads(line)
        for line in args.runs.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    adjudicated: list[dict] = []
    for row in rows:
        task = tasks[row["task_id"]]
        result = row["result"]
        report = result.get("report") or {}
        suppressed: set[str] = set()
        if row["arm"] == "gated":
            for v in result.get("claim_verdicts") or []:
                if v["verdict"] == "reject":
                    suppressed.add(v["claim_id"])
        for claim in report.get("claims", []):
            cid = str(claim.get("claim_id", ""))
            if cid in suppressed:
                verdict, reason = "suppressed", "rejected by ClaimGate"
            else:
                verdict, reason = adjudicate_claim(task, report, claim, structural_oracles)
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

    with out_path.open("w", encoding="utf-8") as fh:
        for rec in adjudicated:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Blinding: shuffle claims across arms, strip arm labels; mapping sealed.
    blinded = list(adjudicated)
    random.Random(args.seed).shuffle(blinded)
    blind_path = out_path.with_name(out_path.stem.replace("_adjudicated", "") + "_blinded.jsonl")
    map_path = out_path.with_name(out_path.stem.replace("_adjudicated", "") + "_blind_map_SEALED.json")
    with blind_path.open("w", encoding="utf-8") as fh:
        for uid, rec in enumerate(blinded):
            fh.write(json.dumps({
                "uid": uid,
                "task_brief": tasks[rec["task_id"]]["brief"],
                "claim": rec["claim"],
            }, ensure_ascii=False) + "\n")
    map_path.write_text(json.dumps(
        {uid: {"task_id": r["task_id"], "arm": r["arm"], "claim_id": r["claim_id"]}
         for uid, r in enumerate(blinded)},
        indent=2, ensure_ascii=False), encoding="utf-8")

    counts: dict[str, dict[str, int]] = {}
    for rec in adjudicated:
        arm = counts.setdefault(rec["arm"], {})
        arm[rec["verdict"]] = arm.get(rec["verdict"], 0) + 1
    print(json.dumps(counts, indent=2))
    print(f"adjudicated -> {out_path}")
    print(f"blinded -> {blind_path} (mapping sealed at {map_path.name})")

    if args.llm_review:
        _llm_review(blind_path, map_path, adjudicated)
    return 0


def _llm_review(blind_path: Path, map_path: Path, adjudicated: list[dict]) -> None:
    """Blinded LLM pass over borderline claims; flag disagreements."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from agent_core.llm_config import get_deepseek_llm

    borderline_uids = set()
    det_by_key = {(r["task_id"], r["arm"], r["claim_id"]): r for r in adjudicated}
    mapping = json.loads(map_path.read_text(encoding="utf-8"))
    for uid_s, key in mapping.items():
        if det_by_key[(key["task_id"], key["arm"], key["claim_id"])]["verdict"] == "borderline":
            borderline_uids.add(int(uid_s))
    if not borderline_uids:
        print("llm_review: no borderline claims; skipped")
        return

    llm = get_deepseek_llm(temperature=0.0)
    disagreements = []
    for line in blind_path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["uid"] not in borderline_uids:
            continue
        prompt = (
            "You are a blind reviewer of scientific claims. Given the task brief and "
            "one claim, judge whether the claim is adequately supported and factually "
            "consistent with the information available (true_positive), or unsupported / "
            "false (false_positive), or undecidable (borderline). Reply JSON only: "
            '{"verdict": "...", "reason": "..."}\n\n'
            f"task brief:\n{rec['task_brief']}\n\nclaim:\n{json.dumps(rec['claim'], ensure_ascii=False)}"
        )
        raw = llm.invoke([SystemMessage(content="Blind claim review."), HumanMessage(content=prompt)])
        content = raw.content if hasattr(raw, "content") else str(raw)
        try:
            judged = json.loads(content.strip().strip("`").removeprefix("json"))
        except json.JSONDecodeError:
            judged = {"verdict": "borderline", "reason": "unparseable LLM output"}
        key = mapping[str(rec["uid"])]
        det = det_by_key[(key["task_id"], key["arm"], key["claim_id"])]
        llm_map = {"true_positive": "TP", "false_positive": "FP", "borderline": "borderline"}
        if llm_map.get(judged["verdict"], "borderline") != det["verdict"]:
            disagreements.append({
                "uid": rec["uid"], "task_id": key["task_id"], "arm": key["arm"],
                "deterministic": det["verdict"], "llm": judged["verdict"],
                "llm_reason": judged.get("reason", ""),
            })
    print(f"llm_review: {len(borderline_uids)} borderline claims reviewed, "
          f"{len(disagreements)} disagreements")
    for d in disagreements:
        print("  DISAGREE:", json.dumps(d, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
