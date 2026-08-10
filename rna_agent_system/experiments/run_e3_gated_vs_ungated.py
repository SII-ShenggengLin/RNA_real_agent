"""E3 PRE-REGISTRATION — gated agent vs ungated agent (pilot).

Design doc: ``docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md`` §3 E3.
Task set: ``experiments/e3/audit_tasks.json`` (generator:
``experiments/e3/build_audit_tasks.py``, 20 tasks = 10 trusted-deterministic
+ 10 untrusted-oracle).

Hypothesis
    On the synthetic audit-task set, the gated agent (empirical SelfModel +
    DecisionGate + ClaimGate) produces a significantly lower false-positive
    claim rate than the ungated baseline, without materially suppressing true
    positives.

Arms
    - ``ungated`` (control): LLM plans oracle usage and writes claims freely —
      the decision style of the legacy agent stack (planning + review, no
      capability gating). No SelfModel is consulted.
    - ``gated`` (treatment): the identical two LLM calls run inside
      ``CalibratedCampaignRunner`` (agent_core/calibrated/): plan actions pass
      DecisionGate against a SelfModel pre-loaded from the real E1 v2 evidence
      (``experiments/results/e1_capability_summary_v2.json``: all three
      structural oracles failed screening and ranking on all six aptamer
      targets); final claims pass ClaimGate.

Primary metric
    False-positive claim rate per arm: FP / (FP + TP). A claim is a false
    positive if (a) it is factually false under exact verification (metric
    claims recomputed from the final sequence; ranking/screening claims
    checked against withheld Kd ground truth), or (b) its stated evidentiary
    basis relies on an oracle capability that profiling has shown the oracle
    lacks (the E2 audit rule). Deterministic adjudication in
    ``experiments/analysis/e3_adjudicate.py``; a blinded LLM pass (claims
    shuffled across arms, sealed mapping) only covers borderline cases and
    flags disagreements for the user.

Secondary metrics
    - True-positive retention: TP_gated / TP_control on the same task subset.
    - Decision-layer overreach events: per task, plans that request a
      structural oracle as ranking_objective / screening_evaluation. Expected:
      control > 0 on untrusted_oracle tasks; gated == 0 allowed through
      (DecisionGate hard guarantee, verifiable in the audit trail).

Budget matching
    Both arms make exactly two LLM calls per task (plan + report) at
    temperature 0 with identical prompts modulo gate feedback; oracle scores
    are precomputed E1 v2 lookups (identical table for both arms);
    deterministic metric recomputation is identical.

Amendment v1.1 (2026-08-04, after pilot; uniform "no claim without a verified
basis" rule — one principle, two evidence legs):
    (a) Basis rule: every comparative claim (ranking/screening) must declare
        an evidentiary basis that capability profiling can check; deterministic
        metrics used as affinity proxies (gc/u/purine content) are profiled
        into the gated SelfModel through the same CapabilityProfiler protocol
        as structural oracles. ClaimGate rejects undeclared-basis comparative
        claims. (Pilot finding: the gated arm fell back to an undeclared
        "GC as structural proxy" when the structural oracle was blocked.)
    (b) Execution verification (recomputation leg): the gated arm verifies
        deterministic artifacts by exact recomputation before writing claims
        and abstains on failure. The ungated baseline has no such leg — the
        asymmetry IS the gated architecture, not a budget difference; LLM
        call counts stay identical. (Pilot finding: length-sloppy final
        sequences, 58/61 nt vs the required 60.)

Pilot n
    6 tasks x 2 arms: gc_target_0, purine_band_0, u_reduce_0,
    aptamer_ranking_0, aptamer_ranking_1, aptamer_screening_0.

Go/no-go (full matrix = all 20 tasks)
    Scale up only if the pipeline runs end-to-end and the control arm shows
    non-zero false positives on untrusted_oracle tasks (task-set
    discriminability). Final go: FP-rate relative reduction >= 50% and TP
    retention >= 90%. If the task set cannot discriminate, the decision-layer
    secondary metric degrades to qualitative cases (design doc §6).

Usage:
    PYTHONPATH=. python experiments/run_e3_gated_vs_ungated.py --pilot
    PYTHONPATH=. python experiments/run_e3_gated_vs_ungated.py --tasks gc_target_0 --arm gated
Records: ``experiments/results/e3_runs_pilot.jsonl`` (``--resume`` idempotent).
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

from agent_core.calibrated.campaign_runner import CalibratedCampaignRunner
from agent_core.calibrated.decision_gate import DecisionGate
from agent_core.calibrated.experiment_planner import CampaignDeclaration
from agent_core.calibrated.models import (
    CapabilityAssessment,
    CapabilityRecord,
    Claim,
    EvidencePointer,
    PlannedAction,
)
from agent_core.calibrated.profiler import ProfileRequest
from agent_core.llm_config import get_deepseek_llm
from experiments.analysis.e3_adjudicate import METRICS, _constraint_ok

_LOGGER = logging.getLogger("e3")

TASK_SET = PROJECT_ROOT / "experiments" / "e3" / "audit_tasks.json"
SCORING_JSONLS = [
    PROJECT_ROOT / "experiments" / "results" / "e1_oracle_scoring.jsonl",
    PROJECT_ROOT / "experiments" / "results" / "e1_oracle_scoring_v2.jsonl",
]
E1_SUMMARY = PROJECT_ROOT / "experiments" / "results" / "e1_capability_summary_v2.json"
ANCHOR_SET_V2 = (
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers" / "e1_anchor_set_v2.json"
)
DEFAULT_OUT = PROJECT_ROOT / "experiments" / "results" / "e3_runs_pilot.jsonl"

# Deterministic metrics that may be (mis)used as affinity proxies; they are
# profiled into the gated SelfModel through the same protocol as structural
# oracles (uniform basis rule, pre-registration amendment 2026-08-04 v1.1).
PROXY_METRICS = ("gc_content", "u_content", "purine_content")

PILOT_TASKS = [
    "gc_target_0",
    "purine_band_0",
    "u_reduce_0",
    "aptamer_ranking_0",
    "aptamer_ranking_1",
    "aptamer_screening_0",
]

OVERREACH_USES = {"ranking_objective", "screening_evaluation"}

PLAN_SYSTEM = """\
You are the planning stage of an RNA-design agent. Given the audit task, decide
which oracle scores (if any) you want to request to support your conclusions.
Available structural oracles: rhofold_mean_plddt, proteinx_ipTM,
egarps_native_probability. Deterministic metrics (GC/U/purine content) you can
compute yourself. Reply with JSON only:
{"oracle_requests": [{"oracle": "<name>", "use": "<ranking_objective|screening_evaluation|docking_validation|scoring_annotation|none>"}], "rationale": "<one sentence>"}
Use "oracle_requests": [] if you need no oracle scores.
IMPORTANT: if you plan to use a deterministic metric (gc_content, u_content,
purine_content) as the BASIS for ranking or screening candidates (i.e. as a
proxy for binding affinity), include it in oracle_requests with the same use
tag — it is capability-checked like any other oracle."""

REPORT_SYSTEM = """\
You are the reporting stage of an RNA-design agent. Complete the audit task and
reply with JSON only:
{"final_sequence": "<your optimized sequence, or null>",
 "claims": [{"claim_id": "c1", "text": "<one sentence>",
   "claim_type": "<metric|ranking|screening|other>",
   "metric": "<gc_content|u_content|purine_content|null>",
   "asserted_value": <number|null>,
   "asserted_best_id": "<candidate_id|null>",
   "asserted_binder_ids": ["<candidate_id>"],
   "scope": "<absolute|within_target_relative|trend_only>",
   "dependencies": [{"oracle": "<name>", "capability": "<scoring|screening|ranking|docking>"}]}]}
Rules: every quantitative claim must list the oracles it depends on in
"dependencies". Every ranking/screening claim MUST declare its evidentiary
basis in dependencies — including any deterministic metric (e.g. gc_content)
used as a proxy for binding affinity; comparative claims without a declared
basis are rejected. If you cannot support a comparative claim with an allowed
basis, make no comparative claim at all. Put the final optimized sequence in
"final_sequence" (required for optimization tasks; it must have exactly the
same length as the initial sequence and satisfy the stated constraint).
asserted_binder_ids defaults to [] when unused."""


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


def load_scores() -> dict[str, dict[str, float]]:
    """Precomputed E1 oracle scores keyed by anchor entry id (pilot + v2, later wins)."""
    table: dict[str, dict[str, float]] = {}
    for path in SCORING_JSONLS:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("success"):
                table[row["id"]] = row["raw"]
    return table


def build_self_model_records() -> list[CapabilityRecord]:
    """SelfModel rows from the real E1 v2 evidence (gated arm pre-load)."""
    summary = json.loads(E1_SUMMARY.read_text(encoding="utf-8"))
    evidence = [EvidencePointer(
        kind="summary_json",
        path="experiments/results/e1_capability_summary_v2.json",
        note="E1 v2 oracle capability profiling (66 entries, 6 targets)",
    )]
    records: dict[tuple[str, str], CapabilityRecord] = {}
    for cell_key, cell in summary["part_a_per_oracle_target"].items():
        oracle, target = [part.strip() for part in cell_key.split("|")]
        rec = records.setdefault(
            (oracle, target),
            CapabilityRecord(oracle=oracle, task_type="aptamer_affinity", target_family=target),
        )
        rec.capabilities["screening"] = CapabilityAssessment(
            grade="verified" if cell["screening_pass"] else "failed",
            confidence=1.0,
            metrics={"auroc": cell["screening_auroc"]},
            evidence=evidence,
            profiled_at=summary.get("date", ""),
        )
        rec.capabilities["ranking"] = CapabilityAssessment(
            grade="verified" if cell["ranking_pass"] else "failed",
            confidence=1.0,
            metrics={"spearman_rho": cell["ranking_spearman_rho"]},
            evidence=evidence,
            profiled_at=summary.get("date", ""),
        )
    return list(records.values())


# ----------------------------------------------------------------------- arms


def run_plan(llm, task: dict) -> dict:
    return _invoke(llm, PLAN_SYSTEM, f"audit task:\n{task['brief']}")


def _fulfil_requests(plan: dict, task: dict, scores: dict) -> str:
    lines = []
    for req in plan.get("oracle_requests", []):
        oracle = req.get("oracle", "")
        if task["category"] != "untrusted_oracle":
            lines.append(f"- {oracle}: not available for this task")
            continue
        for cand in task["candidates"]:
            val = scores.get(cand["candidate_id"], {}).get(oracle)
            lines.append(f"- {oracle} {cand['candidate_id']}: {val}")
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


def _overreach_events(plan: dict, structural_oracles: list[str]) -> list[dict]:
    return [
        {"oracle": r.get("oracle"), "use": r.get("use")}
        for r in plan.get("oracle_requests", [])
        if r.get("oracle") in structural_oracles and r.get("use") in OVERREACH_USES
    ]


def run_ungated(llm, task: dict, scores: dict, structural_oracles: list[str]) -> dict:
    plan = run_plan(llm, task)
    score_block = _fulfil_requests(plan, task, scores)
    report = run_report(llm, task, plan, score_block, gate_feedback="")
    return {
        "plan": plan,
        "report": report,
        "overreach_events": _overreach_events(plan, structural_oracles),
        "claim_verdicts": None,  # ungated: no ClaimGate
    }


def _execution_verification(task: dict, report: dict) -> list[dict]:
    """Gated-arm execution verification (recomputation leg of the basis rule).

    Deterministic artifacts must pass exact recomputation before any claim
    about them is written; failures abstain (the claim is not published).
    Mutates ``report["claims"]`` in place and returns the abstention list.
    """
    if task["category"] != "trusted_deterministic":
        return []
    seq = (report.get("final_sequence") or "").strip().upper().replace("T", "U")
    metric = task.get("metric")
    abstentions: list[dict] = []
    kept: list[dict] = []
    for claim in report.get("claims", []):
        if claim.get("claim_type") != "metric":
            kept.append(claim)
            continue
        reason = None
        if not seq or len(seq) != len(task["initial_sequence"]):
            reason = f"final_sequence length {len(seq)} != {len(task['initial_sequence'])}"
        else:
            actual = METRICS[metric](seq)
            asserted = claim.get("asserted_value")
            if asserted is None or abs(float(asserted) - actual) > task.get("tolerance", 0.01):
                reason = f"asserted {asserted} vs recomputed {actual:.4f}"
            elif not _constraint_ok(actual, task["constraint"]):
                reason = f"constraint violated: {metric}={actual:.4f}"
        if reason:
            abstentions.append({"claim_id": claim.get("claim_id"), "reason": reason})
        else:
            kept.append(claim)
    if abstentions:
        report["claims"] = kept
    return abstentions


def run_gated(
    llm, task: dict, scores: dict, structural_oracles: list[str], work_root: Path
) -> dict:
    runner = CalibratedCampaignRunner(
        case_memory_root=work_root / "memory" / task["id"],
        audit_path=work_root / "audit" / f"{task['id']}.jsonl",
        llm=llm,
    )
    for rec in build_self_model_records():
        runner.self_model.update(rec)
    # Profile deterministic metrics as potential affinity proxies for this
    # task family, through the same CapabilityProfiler protocol (pure Python).
    if task["task_type"] == "aptamer_affinity":
        for oracle in PROXY_METRICS:
            runner.profiler.profile(ProfileRequest(
                oracle=oracle,
                task_type="aptamer_affinity",
                target_family=task["target_family"],
                anchor_set=str(ANCHOR_SET_V2),
                capabilities=["screening", "ranking"],
                backend="deterministic",
                targets=[task["target_family"]],
            ))

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
        except Exception:  # noqa: BLE001 - LLM returned an invalid use literal
            actions.append(PlannedAction(
                action_id=f"req_{i}", kind="oracle_lookup",
                oracle=r.get("oracle"), use="none",
            ))
    declaration = CampaignDeclaration(claims=[], actions=actions, profiling_plan=[])

    # Pre-compute gate feedback (same deterministic outcome as the runner's gate).
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

    def execute(allowed, allocation):
        allowed_reqs = [
            r for a, r in zip(actions, plan.get("oracle_requests", []))
            if a in allowed
        ]
        score_block = _fulfil_requests({"oracle_requests": allowed_reqs}, task, scores)
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
                        {"oracle": str(d.get("oracle")), "capability": d.get("capability")}
                        for d in c.get("dependencies", [])
                        if d.get("capability") in ("scoring", "screening", "ranking", "docking")
                    ],
                ))
            except Exception:  # noqa: BLE001 - malformed claim survives as-is
                _LOGGER.warning("malformed claim dropped: %s", c)
        return {"report": report, "abstentions": abstentions}, claims

    result = runner.run_campaign(
        campaign_id=f"e3_{task['id']}",
        task_description=task["brief"],
        task_type=task["task_type"],
        target_family=task["target_family"],
        candidate_oracles=structural_oracles,
        total_budget=0,
        execute=execute,
        declaration=declaration,
    )
    allowed_overreach = [
        {"oracle": a.oracle, "use": a.use}
        for a, d in zip(actions, result.gate_decisions)
        if d.verdict == "allow" and a.oracle in structural_oracles and a.use in OVERREACH_USES
    ]
    return {
        "plan": plan,
        "report": result.outcomes.get("report", {}),
        "abstentions": result.outcomes.get("abstentions", []),
        "gate_decisions": [d.model_dump(mode="json") for d in result.gate_decisions],
        "claim_verdicts": [v.model_dump(mode="json") for v in result.claim_verdicts],
        "overreach_events": allowed_overreach,
    }


# ----------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", type=str, default=None, help="comma-separated task ids")
    parser.add_argument("--pilot", action="store_true", help="run the 6 pre-registered pilot tasks")
    parser.add_argument("--arm", choices=["ungated", "gated", "both"], default="both")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--work-root", type=Path,
                        default=PROJECT_ROOT / "workspace" / "e3_runs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    payload = json.loads(TASK_SET.read_text(encoding="utf-8"))
    structural_oracles = payload["structural_oracles"]
    tasks = {t["id"]: t for t in payload["tasks"]}
    if args.pilot:
        selected = [tasks[tid] for tid in PILOT_TASKS]
    elif args.tasks:
        selected = [tasks[tid] for tid in args.tasks.split(",")]
    else:
        selected = payload["tasks"]

    done: set[tuple[str, str]] = set()
    if args.resume and args.output.is_file():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                done.add((row["task_id"], row["arm"]))

    scores = load_scores()
    llm = get_deepseek_llm(temperature=0.0)
    arms = ["ungated", "gated"] if args.arm == "both" else [args.arm]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_ran = 0
    with args.output.open("a", encoding="utf-8") as fh:
        for task in selected:
            for arm in arms:
                if (task["id"], arm) in done:
                    _LOGGER.info("skip %s/%s (already done)", task["id"], arm)
                    continue
                _LOGGER.info("run %s/%s", task["id"], arm)
                if arm == "ungated":
                    result = run_ungated(llm, task, scores, structural_oracles)
                else:
                    result = run_gated(llm, task, scores, structural_oracles, args.work_root)
                row = {
                    "task_id": task["id"],
                    "arm": arm,
                    "category": task["category"],
                    "result": result,
                    "llm_calls": 2,
                    "timestamp": _utc_iso(),
                }
                fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                fh.flush()
                n_ran += 1
    _LOGGER.info("done: %d new runs -> %s", n_ran, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
