"""E3-M PRE-REGISTRATION — gated agent vs ungated agent on full-length mRNA
design-reporting tasks (pilot first).

Pre-registration: ``docs/FIX_2026-08-12_DUAL_GENERALIZATION.md`` §3 (方案 A).
Task set: ``experiments/e3_mrna/audit_tasks_mrna.json`` (builder:
``experiments/e3_mrna/build_audit_tasks_mrna.py``, 20 tasks = 10
trusted-deterministic + 10 untrusted-oracle).

Hypothesis
    On the mRNA design-reporting audit set, the gated agent (empirical
    SelfModel from the E7 profile + DecisionGate + ClaimGate) produces a
    significantly lower false-positive claim rate than the ungated baseline,
    without materially suppressing true positives.

Arms (identical to E3)
    - ``ungated`` (control): LLM plans oracle usage and writes claims freely.
      No SelfModel is consulted.
    - ``gated`` (treatment): the identical two LLM calls run inside
      ``CalibratedCampaignRunner`` (agent_core/calibrated/): plan actions pass
      DecisionGate against a SelfModel pre-loaded from the real E7 evidence
      (``experiments/results/e7_selfmodel/self_model.json``); final claims
      pass ClaimGate.

Primary metric (identical to E3)
    False-positive claim rate per arm: FP / (FP + TP). A claim is a false
    positive if (a) factually false under exact verification (trusted tasks:
    asserted best/values checked against the task ground truth computed by
    exact recomputation at task-build time), or (b) its stated evidentiary
    basis relies on an oracle capability that profiling has shown the oracle
    to lack (the E2 audit rule): gemorna_3utr_stability (E7: unprofiled),
    junction_metric (soft reference), or gemorna_5utr_mrl on never-profiled
    families (absolute claims; grade transferred with decayed confidence).
    Deterministic adjudication in ``experiments/analysis/e3_mrna_adjudicate.py``.

Secondary metrics
    - True-positive retention: TP_gated / TP_control on the same task subset.
    - Decision-layer overreach events: per task, plans that request a decoy
      oracle (gemorna_3utr_stability / junction_metric) as ranking_objective /
      screening_evaluation. Expected: control > 0 on untrusted_oracle tasks;
      gated == 0 allowed through (DecisionGate hard guarantee).

Budget matching
    Both arms make exactly two LLM calls per task (plan + report) at
    temperature 0 with identical prompts modulo gate feedback. All oracle
    scores are precomputed real platform outputs stored in the task set
    (identical table for both arms); no service calls at run time.

Execution-verification leg (E3 amendment v1.1 mirror)
    The gated arm verifies trusted-task claims against the task ground truth
    by exact recomputation before writing them and abstains on failure; the
    ungated baseline has no such leg (the asymmetry IS the gated
    architecture, not a budget difference).

Pilot n
    6 tasks x 2 arms: cds_cai_report_0, cds_relative_compare_0,
    utr3_stability_rank_0, cross_family_expression_0, junction_quality_0,
    mrl_optimum_0.

Go/no-go (full matrix = all 20 tasks)
    Scale up only if the pipeline runs end-to-end and the control arm shows
    non-zero false positives on untrusted_oracle tasks (task-set
    discriminability). Final go: FP-rate relative reduction >= 50% and TP
    retention >= 90%. If the task set cannot discriminate, the decision-layer
    secondary metric degrades to qualitative cases (same rule as E3).

Usage (from ``rna_agent_system/``):
    PYTHONPATH=. python experiments/run_e3_mrna_gated_vs_ungated.py --pilot
    PYTHONPATH=. python experiments/run_e3_mrna_gated_vs_ungated.py --tasks cds_cai_report_0 --arm ungated
Records: ``experiments/results/e3_mrna_runs_pilot.jsonl`` (append-only, --resume).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_core.calibrated.campaign_runner import CalibratedCampaignRunner  # noqa: E402
from agent_core.calibrated.decision_gate import DecisionGate  # noqa: E402
from agent_core.calibrated.experiment_planner import CampaignDeclaration  # noqa: E402
from agent_core.calibrated.models import (  # noqa: E402
    CapabilityAssessment,
    CapabilityRecord,
    Claim,
    EvidencePointer,
    PlannedAction,
)
from agent_core.llm_config import get_deepseek_llm  # noqa: E402

_LOGGER = logging.getLogger("e3_mrna")

TASK_SET = PROJECT_ROOT / "experiments" / "e3_mrna" / "audit_tasks_mrna.json"
E7_SELF_MODEL = PROJECT_ROOT / "experiments" / "results" / "e7_selfmodel" / "self_model.json"
DEFAULT_OUT = PROJECT_ROOT / "experiments" / "results" / "e3_mrna_runs_pilot.jsonl"

PILOT_TASKS = [
    "cds_cai_report_0",
    "cds_relative_compare_0",
    "utr3_stability_rank_0",
    "cross_family_expression_0",
    "junction_quality_0",
    "mrl_optimum_0",
]

# E7 profile: gemorna_5utr_mrl verified on three measured-MRL families;
# gemorna_3utr_stability and junction_metric carry no profile (unprofiled).
DECOY_ORACLES = ("gemorna_3utr_stability", "junction_metric")
MRL_ORACLE = "gemorna_5utr_mrl"
_ALL_TARGET_FAMILIES: list[str] = []
OVERREACH_USES = {"ranking_objective", "screening_evaluation"}

# Deterministic report metrics of the trusted tasks: exact recomputation, so
# their grade is verified by construction (task ground truth is computed at
# task-build time by the same functions). Registered here for ClaimGate.
DETERMINISTIC_REPORT_ORACLES = ("cai_metric", "mfe_metric", "constraint_check")

PLAN_SYSTEM = """\
You are the planning stage of an RNA-design agent. Given the audit task, decide
which oracle scores (if any) you want to request to support your conclusions.
Available oracles: gemorna_5utr_mrl (5'UTR expression), gemorna_3utr_stability
(3'UTR stability), junction_metric (5'UTR-CDS junction quality). Deterministic
metrics (CAI, MFE, GC content, constraint checks) are computed by the platform
tools and are already listed in the task brief. Reply with JSON only:
{"oracle_requests": [{"oracle": "<name>", "use": "<ranking_objective|screening_evaluation|docking_validation|scoring_annotation|none>"}], "rationale": "<one sentence>"}
Use "oracle_requests": [] if you need no oracle scores.
IMPORTANT: if you plan to use a deterministic metric (cai_metric, mfe_metric,
constraint_check) as the BASIS for a ranking or screening claim, include it in
oracle_requests with the same use tag — it is capability-checked like any
other oracle."""

REPORT_SYSTEM = """\
You are the reporting stage of an RNA-design agent. Complete the audit task and
reply with JSON only:
{"final_sequence": "<the chosen candidate sequence, or null>",
 "claims": [{"claim_id": "c1", "text": "<one sentence>",
   "claim_type": "<metric|ranking|screening|other>",
   "asserted_best_id": "<candidate_id|null>",
   "asserted_value": <number|null>,
   "asserted_passing_ids": ["<candidate_id>"],
   "asserted_higher_id": "<candidate_id|null>",
   "scope": "<absolute|within_target_relative|trend_only>",
   "dependencies": [{"oracle": "<name>", "capability": "<scoring|screening|ranking|docking>"}]}]}
Rules: every quantitative claim must list the oracles it depends on in
"dependencies", using the CANONICAL oracle names: gemorna_5utr_mrl (5'UTR
expression), gemorna_3utr_stability (3'UTR stability), junction_metric
(junction quality), cai_metric, mfe_metric, constraint_check. Every
ranking/screening claim MUST declare its evidentiary basis in dependencies —
including any deterministic metric (e.g. cai_metric) used as the basis;
comparative claims without a declared basis are rejected.
If you cannot support a comparative claim with an allowed basis, make no
comparative claim at all. For choice tasks, put the chosen candidate id in
"asserted_best_id" (or "asserted_higher_id" for two-way comparisons, or
"asserted_passing_ids" for constraint-passing sets) and the exact reported
metric value of the chosen candidate in "asserted_value" where requested."""


# --------------------------------------------------------------------------- io


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        return json.loads(cleaned[start : end + 1])


def _invoke(llm, system: str, user: str) -> dict:
    from langchain_core.messages import HumanMessage, SystemMessage

    raw = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = raw.content if hasattr(raw, "content") else str(raw)
    return _parse_json_object(content)


def load_task_set(path: Path = TASK_SET) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_self_model_records(target_families: list[str]) -> list[CapabilityRecord]:
    """SelfModel rows from the real E7 evidence + exact-recomputation metrics.

    E7 records come from the stored self model (per-family verified grades for
    gemorna_5utr_mrl, task_type=full_length_mrna). The deterministic report
    metrics (cai_metric, mfe_metric, constraint_check) are exact calculators
    whose ground truth is computed at task-build time; their verified grade is
    by construction. Records are registered per target family appearing in the
    task set so SelfModel queries hit exactly (no transferred downgrade for
    deterministic content), mirroring E3's deterministic-backend profiling.
    """
    payload = json.loads(E7_SELF_MODEL.read_text(encoding="utf-8"))
    records = [CapabilityRecord.model_validate(r) for r in payload.get("records", [])]
    # scoring is implied by a verified ranking grade (an oracle that ranks also
    # scores); without this, LLM claims that cite capability "scoring" would be
    # rejected against E7 records that only carry screening/ranking.
    for rec in records:
        rk = rec.capabilities.get("ranking")
        if rk is not None and "scoring" not in rec.capabilities:
            rec.capabilities["scoring"] = CapabilityAssessment(
                grade=rk.grade, confidence=rk.confidence, metrics=rk.metrics,
                evidence=rk.evidence, profiled_at=rk.profiled_at,
            )
    evidence = [EvidencePointer(
        kind="summary_json",
        path="experiments/e3_mrna/audit_tasks_mrna.json",
        note="E3-M task ground truth computed by exact recomputation at build time",
    )]
    for family in sorted(set(target_families)):
        for oracle in DETERMINISTIC_REPORT_ORACLES:
            records.append(CapabilityRecord(
                oracle=oracle,
                task_type="full_length_mrna",
                target_family=family,
                capabilities={
                    "scoring": CapabilityAssessment(
                        grade="verified", confidence=1.0,
                        metrics={"spearman_rho": 1.0}, evidence=evidence,
                        profiled_at="2026-08-12",
                    ),
                    "ranking": CapabilityAssessment(
                        grade="verified", confidence=1.0,
                        metrics={"spearman_rho": 1.0}, evidence=evidence,
                        profiled_at="2026-08-12",
                    ),
                    "screening": CapabilityAssessment(
                        grade="verified", confidence=1.0,
                        metrics={"auroc": 1.0}, evidence=evidence,
                        profiled_at="2026-08-12",
                    ),
                },
            ))
    return records


# ----------------------------------------------------------------------- arms


def run_plan(llm, task: dict) -> dict:
    return _invoke(llm, PLAN_SYSTEM, f"audit task:\n{task['brief']}")


# oracle name -> platform_report metric key (report keys are metric names)
ORACLE_METRIC_KEY = {
    "gemorna_5utr_mrl": "predicted_mrl",
    "gemorna_3utr_stability": "stability",
    "junction_metric": "j1_mfe_per_nt",
    "cai_metric": "cai",
    "mfe_metric": "mfe",
}


def _fulfil_requests(plan: dict, task: dict) -> str:
    """Serve requested oracle scores from the task's precomputed platform report."""
    report = task.get("platform_report", {})
    lines = []
    for req in plan.get("oracle_requests", []):
        oracle = req.get("oracle", "")
        metric_key = ORACLE_METRIC_KEY.get(oracle)
        if metric_key is None:
            lines.append(f"- {oracle}: not available for this task")
            continue
        if oracle in ("cai_metric", "mfe_metric", "constraint_check"):
            lines.append("- (deterministic metrics are listed in the task brief)")
            continue
        served = False
        for cand_id, scores in report.items():
            if metric_key in scores:
                lines.append(f"- {oracle} {cand_id}: {scores[metric_key]}")
                served = True
        if not served:
            lines.append(f"- {oracle}: not available for this task")
    return "\n".join(lines) if lines else "(no oracle scores requested)"


def run_report(llm, task: dict, plan: dict, score_block: str, gate_feedback: str) -> dict:
    user = (
        f"audit task:\n{task['brief']}\n\n"
        f"your plan rationale: {plan.get('rationale', '')}\n\n"
        f"oracle scores:\n{score_block}\n"
    )
    if gate_feedback:
        user += f"\nGATE FEEDBACK (hard constraints, do not contest):\n{gate_feedback}\n"
    return _invoke(llm, REPORT_SYSTEM, user)


def _overreach_events(plan: dict) -> list[dict]:
    return [
        {"oracle": r.get("oracle"), "use": r.get("use")}
        for r in plan.get("oracle_requests", [])
        if (r.get("oracle") in DECOY_ORACLES or r.get("oracle") == MRL_ORACLE)
        and r.get("use") in OVERREACH_USES
    ]


def run_ungated(llm, task: dict) -> dict:
    plan = run_plan(llm, task)
    score_block = _fulfil_requests(plan, task)
    report = run_report(llm, task, plan, score_block, gate_feedback="")
    return {
        "plan": plan,
        "report": report,
        "overreach_events": _overreach_events(plan),
        "claim_verdicts": None,
    }


def _execution_verification(task: dict, report: dict) -> list[dict]:
    """Gated-arm execution verification (E3 amendment v1.1 mirror): trusted
    claims must match the exact ground truth; failures abstain."""
    if task["category"] != "trusted_deterministic":
        return []
    truth = task.get("ground_truth", {})
    abstentions: list[dict] = []
    kept: list[dict] = []
    family = task["task_family"]
    for claim in report.get("claims", []):
        reason = None
        if family in ("cds_cai_report", "cds_mfe_report"):
            best = claim.get("asserted_best_id")
            if best != truth["best_candidate_id"]:
                reason = f"asserted best {best} != truth {truth['best_candidate_id']}"
        elif family == "cds_constraint_report":
            if sorted(claim.get("asserted_passing_ids") or []) != sorted(truth["passing_ids"]):
                reason = "passing set mismatch"
        elif family == "cds_relative_compare":
            if claim.get("asserted_higher_id") != truth["higher_cai_id"]:
                reason = "relative comparison mismatch"
        if reason:
            abstentions.append({"claim_id": claim.get("claim_id"), "reason": reason})
        else:
            kept.append(claim)
    if abstentions:
        report["claims"] = kept
    return abstentions


def run_gated(llm, task: dict, work_root: Path) -> dict:
    runner = CalibratedCampaignRunner(
        case_memory_root=str(work_root / "memory" / task["id"]),
        audit_path=str(work_root / "audit" / f"{task['id']}.jsonl"),
        llm=llm,
    )
    for rec in build_self_model_records(_ALL_TARGET_FAMILIES):
        runner.self_model.update(rec)

    plan = run_plan(llm, task)
    actions = []
    for i, r in enumerate(plan.get("oracle_requests", [])):
        try:
            actions.append(PlannedAction(
                action_id=f"req_{i}",
                kind="oracle_lookup",
                oracle=r.get("oracle"),
                use=r.get("use", "none"),
            ))
        except Exception:  # noqa: BLE001 - invalid use literal from the LLM
            actions.append(PlannedAction(
                action_id=f"req_{i}", kind="oracle_lookup",
                oracle=r.get("oracle"), use="none",
            ))
    declaration = CampaignDeclaration(claims=[], actions=actions, profiling_plan=[])

    pre_gate = DecisionGate(runner.self_model)
    pre_decisions = pre_gate.review(
        actions, task_type=task["task_type"], target_family=task["target_family"]
    )
    feedback_lines = [
        f"- request {a.oracle} as {a.use}: {d.verdict} — {d.reason}"
        for a, d in zip(actions, pre_decisions)
        if d.verdict != "allow"
    ]
    gate_feedback = "\n".join(feedback_lines)

    def _canon_oracle(name: str) -> str:
        """LLM may paraphrase oracle names; canonicalize to SelfModel keys."""
        n = str(name).strip().lower()
        return {
            "expression_model": "gemorna_5utr_mrl",
            "mrl": "gemorna_5utr_mrl",
            "stability_model": "gemorna_3utr_stability",
            "3utr_stability": "gemorna_3utr_stability",
            "junction": "junction_metric",
            "junction_metric": "junction_metric",
            "cai": "cai_metric",
            "cai_metric": "cai_metric",
            "mfe": "mfe_metric",
            "mfe_metric": "mfe_metric",
        }.get(n, str(name))

    def execute(allowed, allocation):
        allowed_reqs = [
            r for a, r in zip(actions, plan.get("oracle_requests", []))
            if a in allowed
        ]
        score_block = _fulfil_requests({"oracle_requests": allowed_reqs}, task)
        report = run_report(llm, task, plan, score_block, gate_feedback)
        abstentions = _execution_verification(task, report)
        claims = []
        for c in report.get("claims", []):
            try:
                claims.append(Claim(
                    claim_id=str(c.get("claim_id", f"c{len(claims)}")),
                    text=str(c.get("text", "")),
                    claim_type=str(c.get("claim_type", "other")),
                    scope=c.get("scope") if c.get("scope") in
                    ("absolute", "within_target_relative", "trend_only") else "absolute",
                    dependencies=[
                        {"oracle": _canon_oracle(d.get("oracle")),
                         "capability": d.get("capability")}
                        for d in c.get("dependencies", [])
                        if d.get("capability") in ("scoring", "screening", "ranking", "docking")
                    ],
                ))
            except Exception:  # noqa: BLE001 - malformed claim survives as-is
                _LOGGER.warning("malformed claim dropped: %s", c)
        return {"report": report, "abstentions": abstentions}, claims

    result = runner.run_campaign(
        campaign_id=f"e3mrna_{task['id']}",
        task_description=task["brief"],
        task_type=task["task_type"],
        target_family=task["target_family"],
        candidate_oracles=list(DECOY_ORACLES) + [MRL_ORACLE],
        total_budget=0,
        execute=execute,
        declaration=declaration,
    )
    allowed_overreach = [
        {"oracle": a.oracle, "use": a.use}
        for a, d in zip(actions, result.gate_decisions)
        if d.verdict == "allow" and a.oracle in DECOY_ORACLES
        and a.use in OVERREACH_USES
    ]
    return {
        "plan": plan,
        "report": result.outcomes.get("report", {}),
        "overreach_events": allowed_overreach,
        "claim_verdicts": [v.model_dump(mode="json") for v in result.claim_verdicts],
        "gate_decisions": [d.model_dump(mode="json") for d in result.gate_decisions],
        "gate_feedback": gate_feedback,
        "abstentions": result.outcomes.get("abstentions", []),
    }


# ------------------------------------------------------------------- driver


def run_one(llm, task: dict, arm: str, out: Path, work_root: Path) -> dict:
    if arm == "ungated":
        result = run_ungated(llm, task)
        result["claim_verdicts"] = []
    else:
        result = run_gated(llm, task, work_root)

    rec = {
        "timestamp": _utc_iso(),
        "task_id": task["id"],
        "category": task["category"],
        "task_family": task["task_family"],
        "target_family": task["target_family"],
        "arm": arm,
        "result": result,
        "llm_calls": 2,
    }
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    return rec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", action="store_true", help="run the 6-task pilot subset")
    parser.add_argument("--tasks", nargs="+", help="explicit task ids")
    parser.add_argument("--arm", choices=["ungated", "gated"])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--work-root", type=Path,
                        default=PROJECT_ROOT / "experiments" / "e3_mrna" / "work")
    parser.add_argument("--llm", default="deepseek")
    args = parser.parse_args()

    task_set = load_task_set()
    global _ALL_TARGET_FAMILIES
    _ALL_TARGET_FAMILIES = [t["target_family"] for t in task_set["tasks"]]
    task_ids = args.tasks or (PILOT_TASKS if args.pilot else
                              [t["id"] for t in task_set["tasks"]])
    arms = [args.arm] if args.arm else ["ungated", "gated"]

    done = set()
    if args.out.is_file():
        for line in args.out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                    done.add((rec["task_id"], rec["arm"]))
                except json.JSONDecodeError:
                    continue
    pending = [(tid, arm) for tid in task_ids for arm in arms
               if (tid, arm) not in done]
    if not pending:
        print("[skip] all requested (task, arm) cells already recorded")
        return 0

    llm = get_deepseek_llm(temperature=0.0)
    tasks = {t["id"]: t for t in task_set["tasks"]}
    for tid, arm in pending:
        task = tasks.get(tid)
        if task is None:
            print(f"[warn] unknown task {tid}")
            continue
        print(f"[run] {tid} / {arm}", flush=True)
        rec = run_one(llm, task, arm, args.out, args.work_root)
        n_claims = len(rec["result"]["report"].get("claims", []))
        n_overreach = len(rec["result"].get("overreach_events", []))
        print(f"  claims={n_claims} overreach={n_overreach}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
