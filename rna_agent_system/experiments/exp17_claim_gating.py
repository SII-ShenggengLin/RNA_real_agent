"""EXPERIMENT 17 (2026-08-31 programme) — capability-gated agent: dual-arm main (Fig 4a/4b).

Legacy identity: the E3 gated treatment arm of the 2026-08-04 campaign
(``run_e3_gated_vs_ungated.py``, deleted in the reset; protocol recovered
from git e601913), re-registered at the 45-task plan-A scale under the
2026-08-29 third programme reset. The ungated control arm of the same
dual-arm design is Exp 5 (``experiments/exp5_claim_overreach.py``, run
2026-08-29 on the identical task set, prompts and live oracle chain,
45/45) — this driver runs the gated treatment arm only; the paired
adjudicator assembles both arms.

PRE-REGISTRATION

Hypothesis (guarantee verification, not improvement)
    The capability-gated agent — the identical two-call plan/report LLM
    protocol running inside the production CapGate stack (SelfModel +
    DecisionGate + ClaimGate, ``RNADA_CAPGATE=enforce``) — issues no
    false-positive design claims (FP rate exactly 0: a deterministic
    guarantee of the gates, here verified by measurement; any nonzero FP
    is a protocol-defect finding — stop and investigate, do not re-run)
    and no decision-layer overreach events, while retaining the ungated
    arm's true positives (retention gate >= 0.9, the legacy E3 go-rule).
    Zero-intervention measurement: fixed protocol, no threshold tuning,
    no prompt edits beyond the legacy gate-feedback convention.

Sample
    The identical 45 audit tasks as Exp 5 (``experiments/e5_audit_tasks.json``,
    verified byte-identical to a fresh deterministic regeneration on
    2026-08-31): 24 trusted-deterministic + 21 untrusted-oracle; strata
    legacy_v1 (20) / extension_v2 (25). Kd ground truth withheld from the
    agent. Control arm = the retained Exp-5 ``runs.jsonl`` (ungated, same
    tasks); not re-run — pre-registered pairing.

Instrument
    Exactly two LLM calls per task (plan + report; DeepSeek
    deepseek-v4-pro, temperature 0, prompts byte-identical to the
    legacy/exp5 control arm; the single gated-arm addition is the legacy
    gate-feedback block appended to the report prompt — "identical prompts
    modulo gate feedback", the 2026-08-04 E3 convention; one
    transport-level retry per call on API errors only, disclosed as in
    Exp 5). Gates = the production path, platform as shipped:
    ``CalibratedRuntime`` configured from ``RNADA_CAPGATE=enforce`` with
    the packaged default SelfModel (the three structural oracles grade
    failed for screening/ranking on all six profiled aptamer families;
    the three v3-only families inherit the denial by conservative
    transfer). Plan oracle_requests are reviewed per declared use —
    structural oracles via ``runtime.review_tool_call`` under
    ``oracle_use(use, target_family)``, deterministic-proxy metrics and
    unknown names via DecisionGate directly — keyed to the oracles'
    registered task type ``rna_aptamer_design`` (the production
    ToolExecutor key; the legacy ``aptamer_affinity`` key would query a
    SelfModel it never populated). Blocked requests contribute no scores
    (score block = allowed requests only) and one feedback line; allowed
    requests are fulfilled live through ``ToolExecutor.run_tool`` over the
    deployed rhofold 8005 / proteinx 8022 / egarps 8023 services
    (GPU-pinned 0/1/2) under the same ``oracle_use`` context, so the
    tool-layer gate is the actual enforcer. The per-(candidate, oracle)
    dedup cache is seeded from Exp 5's cache (the same production values
    the control arm saw; disclosed). The gated arm keeps the two legacy
    treatment legs of the 2026-08-04 amendment v1.1: (a) uniform basis
    rule — ClaimGate (production code) rejects comparative claims without
    a declared, capability-checked basis, deterministic metrics used as
    affinity proxies included (they gate as unprofiled under enforce —
    the same block outcome as the legacy runtime-profiled failed grade);
    (b) execution verification — deterministic artifacts are verified by
    exact recomputation before publication and abstain on failure. Claim
    verdicts key to (``rna_aptamer_design``, target_family); rejected
    claims are suppressed (recorded, not published), downgraded claims
    are published with the gate's rewritten scope (none expected here —
    no transferred-verified cells exist for these oracles). Every gate
    decision and tool call lands in the platform audit trail.

Adjudication (deterministic, blind to arm; rules identical to legacy/exp5)
    metric claims: exact recomputation from the reported final sequence
    (length preserved, asserted value within tolerance, constraint band
    satisfied). ranking/screening claims: asserted best candidate / binder
    set against the withheld Kd ground truth; a factually correct answer
    whose declared basis cites a structural oracle for ranking/screening
    is still a false positive (the E2 audit rule). Gated-arm claims
    rejected by ClaimGate are recorded as ``suppressed`` (neither FP nor
    TP); abstained claims are not published. Claim types outside the
    deterministic rules are borderline, excluded from the rate
    denominator. Blinding: all claims from both arms are shuffled with a
    recorded seed, arm labels stripped, mapping sealed (the legacy
    e3_adjudicate mechanics, seed 0).

Metrics
    Primary: per-arm false-positive claim rate FP/(FP+TP) with Wilson 95%
    CI, overall and by category / stratum / claim type. Secondary:
    true-positive retention TP_gated/TP_ungated on the paired task subset
    (gate >= 0.9); decision-layer overreach events (allowed structural-
    oracle plan requests with use ranking_objective / screening_evaluation;
    expectation 0); suppressions and abstentions; per-claim adjudication
    matrix (task x arm x verdict) for Fig 4b; the legacy-20 subset (1:1
    comparison with the registered 57.9% -> 0%, TP 8 -> 9, 23 -> 0).

Pilot (n = 8)
    The identical eight pre-registered Exp-5 pilot tasks (gc_target_0,
    purine_band_0, u_reduce_0, gc_target_4, aptamer_ranking_0,
    aptamer_ranking_1, aptamer_screening_0, aptamer_ranking_v3_fgf2).
    Passes if all 8 records are well-formed, zero FP claims, zero allowed
    overreach events, and the gate chain demonstrably engages (>= 1
    blocked plan request or ClaimGate verdict on the untrusted-oracle
    class); otherwise stop and report without a full run.

Usage
    PYTHONPATH=. python experiments/exp17_claim_gating.py --pilot
    PYTHONPATH=. python experiments/exp17_claim_gating.py --resume
    PYTHONPATH=. python experiments/exp17_claim_gating.py --adjudicate
Records: ``experiments/results/exp17_claim_gating/`` (runs.jsonl,
score_cache.jsonl seeded from Exp 5, scratch/, adjudicated.jsonl,
blinded.jsonl, blind_map_SEALED.json, summary.json).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# The gated arm IS enforce — set before the exp5 import (whose module-level
# setdefault("advisory") must not win) and before any runtime_from_env().
os.environ.setdefault("RNADA_CAPGATE", "enforce")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.exp5_claim_overreach import (  # noqa: E402
    METRICS,
    OVERREACH_USES,
    PILOT_TASKS,
    REPORT_SYSTEM,
    RESULTS_DIR as EXP5_DIR,
    STRUCTURAL_ORACLES,
    ScoreService,
    adjudicate_claim,
    load_task_set,
    run_plan,
    wilson_ci,
    _constraint_ok,
    _invoke,
)
from agent_core.calibrated.models import Claim, PlannedAction  # noqa: E402
from agent_core.calibrated.runtime import (  # noqa: E402
    MANAGED_ORACLE_TOOLS,
    oracle_use,
    runtime_from_env,
)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp17_claim_gating"
DEFAULT_OUT = RESULTS_DIR / "runs.jsonl"
ANCHOR_JSON = (
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers" / "e1_anchor_set_v3.json"
)

# The production gate key: the task type the managed-oracle ToolSpecs are
# registered under (what ToolExecutor.review_tool_call uses outside a
# workflow context). The legacy driver's "aptamer_affinity" key predates
# the SelfModel packaging and would query a model it never populated.
GATE_TASK_TYPE = "rna_aptamer_design"

# Oracle id -> platform tool name (production registry, single source).
ORACLE_TO_TOOL = {oracle: tool for tool, (oracle, _tt, _use) in MANAGED_ORACLE_TOOLS.items()}

VALID_USES = {"ranking_objective", "screening_evaluation", "docking_validation",
              "scoring_annotation", "none"}
# Design semantics: "downgrade" (transferred-verified) actions proceed with
# capped conclusions; only allow/downgrade requests fetch scores.
FETCH_VERDICTS = {"allow", "downgrade"}

_LOGGER = logging.getLogger("exp17")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── the gated treatment arm ──────────────────────────────────────────────────


def review_plan_requests(runtime, plan: dict, task: dict) -> list[dict]:
    """DecisionGate verdict per plan oracle_request, production keying.

    Structural oracles go through ``runtime.review_tool_call`` under
    ``oracle_use`` (exactly what the ToolExecutor will consult); other
    names (deterministic-proxy metrics, hallucinated ids) go through the
    DecisionGate directly. Every verdict lands in the platform audit trail.
    """
    family = task["target_family"]
    decisions: list[dict] = []
    for i, req in enumerate(plan.get("oracle_requests", [])):
        oracle = req.get("oracle") or ""
        use = req.get("use") if req.get("use") in VALID_USES else "none"
        if oracle in ORACLE_TO_TOOL and oracle in STRUCTURAL_ORACLES:
            with oracle_use(use, target_family=family):
                dec = runtime.review_tool_call(ORACLE_TO_TOOL[oracle])
            verdict, reason = dec.verdict, dec.reason
        else:
            action = PlannedAction(
                action_id=f"req_{i}", kind="oracle_lookup", oracle=oracle, use=use,
            )
            dec = runtime.decision_gate.review(
                [action], task_type=GATE_TASK_TYPE, target_family=family
            )[0]
            verdict, reason = dec.verdict, dec.reason
        decisions.append({"index": i, "oracle": oracle, "use": use,
                          "verdict": verdict, "reason": reason})
    return decisions


def gate_feedback_lines(decisions: list[dict]) -> list[str]:
    return [
        f"- request {d['oracle']} as {d['use']}: {d['verdict']} — {d['reason']}"
        for d in decisions
        if d["verdict"] not in FETCH_VERDICTS
    ]


def fulfil_requests_gated(plan: dict, task: dict, scores: ScoreService,
                          decisions: list[dict]) -> tuple[str, list]:
    """Score block from allowed requests only (legacy gated-arm convention).

    Allowed fetches run under the request's ``oracle_use`` context so the
    tool-layer DecisionGate is the actual enforcer of the same verdict.
    """
    fetch_idx = {d["index"] for d in decisions if d["verdict"] in FETCH_VERDICTS}
    lines: list[str] = []
    live_calls: list[dict] = []
    for i, req in enumerate(plan.get("oracle_requests", [])):
        oracle = req.get("oracle", "")
        use = req.get("use") if req.get("use") in VALID_USES else "none"
        if task["category"] != "untrusted_oracle":
            lines.append(f"- {oracle}: not available for this task")
            continue
        if i not in fetch_idx:
            continue  # blocked at the plan gate — no score line (legacy)
        for cand in task["candidates"]:
            cid = cand["candidate_id"]
            if oracle in STRUCTURAL_ORACLES:
                with oracle_use(use, target_family=task["target_family"]):
                    val = scores.get(cid, oracle)
                live_calls.append({"candidate_id": cid, "oracle": oracle,
                                   "value": val,
                                   "error": scores.cache[(cid, oracle)]["error"]})
            else:
                val = None  # deterministic metric / unknown oracle: no lookup path
            lines.append(f"- {oracle} {cid}: {val}")
    return ("\n".join(lines) if lines else "(no oracle scores requested)"), live_calls


def run_report_gated(llm, task: dict, plan: dict, score_block: str,
                     gate_feedback: str) -> dict:
    user = (
        f"audit task:\n{task['brief']}\n\n"
        f"your plan rationale: {plan.get('rationale', '')}\n\n"
        f"oracle scores:\n{score_block}\n"
    )
    if gate_feedback:
        user += f"\nGATE FEEDBACK (hard constraints, do not contest):\n{gate_feedback}\n"
    return _invoke(llm, REPORT_SYSTEM, user)


def execution_verification(task: dict, report: dict) -> list[dict]:
    """Gated-arm recomputation leg (2026-08-04 amendment v1.1, verbatim).

    Deterministic artifacts must pass exact recomputation before any claim
    about them is published; failures abstain. Mutates ``report["claims"]``
    in place and returns the abstention list.
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


def build_claims(report: dict) -> list[Claim]:
    """LLM claim dicts -> Claim objects (legacy conversion, verbatim)."""
    claims: list[Claim] = []
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
    return claims


def run_gated(llm, runtime, task: dict, scores: ScoreService) -> dict:
    plan = run_plan(llm, task)
    decisions = review_plan_requests(runtime, plan, task)
    feedback = "\n".join(gate_feedback_lines(decisions))
    score_block, live_calls = fulfil_requests_gated(plan, task, scores, decisions)
    report = run_report_gated(llm, task, plan, score_block, feedback)
    abstentions = execution_verification(task, report)

    claims = build_claims(report)
    verdicts = runtime.gate_claims(
        claims, task_type=GATE_TASK_TYPE, target_family=task["target_family"]
    )
    by_id = {c.claim_id: c for c in claims}
    suppressed_ids: list[str] = []
    for v in verdicts:
        if v.verdict == "reject":
            suppressed_ids.append(v.claim_id)
        elif v.verdict == "downgrade" and v.rewritten_text:
            claim = by_id.get(v.claim_id)
            for c in report.get("claims", []):
                if str(c.get("claim_id")) == v.claim_id and claim is not None:
                    c["text"] = v.rewritten_text
                    c["scope"] = "trend_only" if v.reason.endswith("-> trend_only") else \
                                 "within_target_relative"

    allowed_overreach = [
        {"oracle": d["oracle"], "use": d["use"]}
        for d in decisions
        if d["verdict"] in FETCH_VERDICTS
        and d["oracle"] in STRUCTURAL_ORACLES and d["use"] in OVERREACH_USES
    ]
    return {
        "plan": plan,
        "gate_decisions": decisions,
        "gate_feedback": feedback,
        "score_block": score_block,
        "live_score_calls": live_calls,
        "report": report,
        "abstentions": abstentions,
        "claim_verdicts": [v.model_dump(mode="json") for v in verdicts],
        "suppressed_claim_ids": suppressed_ids,
        "overreach_events": allowed_overreach,
    }


# ── run main ─────────────────────────────────────────────────────────────────


def cmd_run(args) -> int:
    payload = load_task_set()
    tasks = {t["id"]: t for t in payload["tasks"]}
    if args.pilot:
        selected = [tasks[tid] for tid in PILOT_TASKS]
    elif args.tasks:
        selected = [tasks[tid] for tid in args.tasks.split(",")]
    else:
        selected = payload["tasks"]

    done: set[str] = set()
    if args.resume and args.output.is_file():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["task_id"])

    runtime = runtime_from_env()
    assert runtime is not None and runtime.policy == "enforce", (
        "the gated arm requires RNADA_CAPGATE=enforce "
        f"(got policy={getattr(runtime, 'policy', None)})")
    _LOGGER.info("calibrated runtime: policy=%s self_model_records=%d",
                 runtime.policy, len(runtime.self_model.records()))

    cache_path = RESULTS_DIR / "score_cache.jsonl"
    if not cache_path.is_file() and (EXP5_DIR / "score_cache.jsonl").is_file():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(EXP5_DIR / "score_cache.jsonl", cache_path)
        _LOGGER.info("score cache seeded from Exp 5 (%s pairs)",
                     sum(1 for l in cache_path.read_text().splitlines() if l.strip()))

    from agent_core.llm_config import get_deepseek_llm

    anchor_by_id = {e["id"]: e for e in json.loads(
        ANCHOR_JSON.read_text(encoding="utf-8"))["entries"]}
    scores = ScoreService(anchor_by_id, RESULTS_DIR / "scratch", cache_path,
                          timeout=args.timeout)
    llm = get_deepseek_llm(temperature=0.0)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_ran = 0
    with args.output.open("a", encoding="utf-8") as fh:
        for task in selected:
            if task["id"] in done:
                _LOGGER.info("skip %s (already done)", task["id"])
                continue
            _LOGGER.info("run %s (%s / %s)", task["id"], task["stratum"], task["category"])
            t0 = time.monotonic()
            try:
                result = run_gated(llm, runtime, task, scores)
                row = {
                    "task_id": task["id"],
                    "arm": "gated",
                    "stratum": task["stratum"],
                    "category": task["category"],
                    "task_family": task["task_family"],
                    "target_family": task["target_family"],
                    **result,
                    "llm_calls": 2,
                    "model": "deepseek-v4-pro",
                    "wall_s": round(time.monotonic() - t0, 1),
                    "timestamp": _utc_iso(),
                }
            except Exception as exc:  # noqa: BLE001 - recorded, not retried
                row = {
                    "task_id": task["id"],
                    "arm": "gated",
                    "stratum": task["stratum"],
                    "category": task["category"],
                    "error": f"{type(exc).__name__}: {exc}",
                    "llm_calls": 0,
                    "model": "deepseek-v4-pro",
                    "wall_s": round(time.monotonic() - t0, 1),
                    "timestamp": _utc_iso(),
                }
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            n_ran += 1
    _LOGGER.info("done: %d new runs -> %s", n_ran, args.output)
    return 0


# ── paired adjudication (deterministic, blind) ───────────────────────────────


def _adjudicate_rows(rows: list[dict], tasks: dict) -> list[dict]:
    adjudicated: list[dict] = []
    for row in rows:
        task = tasks[row["task_id"]]
        if row.get("error"):
            continue
        report = row.get("report") or {}
        suppressed = set(row.get("suppressed_claim_ids") or []) \
            if row["arm"] == "gated" else set()
        for claim in report.get("claims", []):
            cid = str(claim.get("claim_id", ""))
            if cid in suppressed:
                verdict, reason = "suppressed", "rejected by ClaimGate"
            else:
                verdict, reason = adjudicate_claim(task, report, claim)
            adjudicated.append({
                "task_id": row["task_id"],
                "arm": row["arm"],
                "stratum": row["stratum"],
                "category": row["category"],
                "task_family": row["task_family"],
                "claim_id": cid,
                "claim_type": claim.get("claim_type"),
                "verdict": verdict,
                "reason": reason,
                "claim": claim,
            })
    return adjudicated


def _block(records: list[dict], rows: list[dict]) -> dict:
    c = {v: sum(1 for r in records if r["verdict"] == v)
         for v in ("TP", "FP", "borderline", "suppressed")}
    n = c["FP"] + c["TP"]
    fp_rate = c["FP"] / n if n else None
    lo, hi = wilson_ci(c["FP"], n)
    tids = {r["task_id"] for r in records}
    overreach = sum(len(r.get("overreach_events", []))
                    for r in rows if r["task_id"] in tids and not r.get("error"))
    abstentions = sum(len(r.get("abstentions", []))
                      for r in rows if r["task_id"] in tids and not r.get("error"))
    return {"TP": c["TP"], "FP": c["FP"], "borderline": c["borderline"],
            "suppressed": c["suppressed"], "fp_rate": fp_rate,
            "fp_rate_ci95": [lo, hi], "overreach_events": overreach,
            "abstentions": abstentions}


def cmd_adjudicate(args) -> int:
    payload = load_task_set()
    tasks = {t["id"]: t for t in payload["tasks"]}

    gated_rows = [json.loads(l) for l in args.runs.read_text(encoding="utf-8").splitlines()
                  if l.strip()]
    gated_ids = {r["task_id"] for r in gated_rows if not r.get("error")}
    control_rows = [json.loads(l) for l in (EXP5_DIR / "runs.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    control_rows = [r for r in control_rows
                    if r["task_id"] in gated_ids and not r.get("error")]
    rows = control_rows + gated_rows

    adjudicated = _adjudicate_rows(rows, tasks)

    # Blinding: shuffle claims across arms, strip arm labels; mapping sealed.
    import random
    blinded = list(adjudicated)
    random.Random(args.seed).shuffle(blinded)
    blind_path = RESULTS_DIR / "blinded.jsonl"
    map_path = RESULTS_DIR / "blind_map_SEALED.json"
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

    def _arm(arm: str) -> dict:
        arm_rows = [r for r in rows if r["arm"] == arm]
        return _block([r for r in adjudicated if r["arm"] == arm], arm_rows)

    def _subset(arm: str, pred) -> dict:
        arm_rows = [r for r in rows if r["arm"] == arm]
        return _block([r for r in adjudicated if r["arm"] == arm and pred(r)], arm_rows)

    paired_ids = gated_ids  # control rows filtered to gated ids above
    tp_u = sum(1 for r in adjudicated if r["arm"] == "ungated" and r["verdict"] == "TP")
    tp_g = sum(1 for r in adjudicated if r["arm"] == "gated" and r["verdict"] == "TP")

    per_task: dict[str, dict] = {}
    for r in adjudicated:
        per_task.setdefault(r["task_id"], {}).setdefault(r["arm"], {})
        cell = per_task[r["task_id"]][r["arm"]]
        cell[r["verdict"]] = cell.get(r["verdict"], 0) + 1

    gate_engagement = {
        "blocked_plan_requests": sum(
            1 for r in gated_rows if not r.get("error")
            for d in r.get("gate_decisions", [])
            if d["verdict"] not in FETCH_VERDICTS),
        "claim_gate_verdicts": {
            v: sum(1 for r in gated_rows if not r.get("error")
                   for cv in r.get("claim_verdicts", []) if cv["verdict"] == v)
            for v in ("pass", "reject", "downgrade")},
        "abstentions": sum(len(r.get("abstentions", []))
                           for r in gated_rows if not r.get("error")),
    }

    summary = {
        "experiment": "exp17_claim_gating (gated dual-arm main, Fig 4a/4b; "
                      "control arm = exp5_claim_overreach)",
        "date": _utc_iso(),
        "n_tasks_paired": len(paired_ids),
        "n_tasks_gated_failed": sum(1 for r in gated_rows if r.get("error")),
        "failed_tasks": [r["task_id"] for r in gated_rows if r.get("error")],
        "n_claims": len(adjudicated),
        "arms": {"ungated": _arm("ungated"), "gated": _arm("gated")},
        "by_category": {
            arm: {c: _subset(arm, lambda r, c=c: r["category"] == c)
                  for c in ("trusted_deterministic", "untrusted_oracle")}
            for arm in ("ungated", "gated")},
        "by_stratum": {
            arm: {s: _subset(arm, lambda r, s=s: r["stratum"] == s)
                  for s in ("legacy_v1", "extension_v2")}
            for arm in ("ungated", "gated")},
        "by_claim_type": {
            arm: {c: _subset(arm, lambda r, c=c: r["claim_type"] == c)
                  for c in sorted({r["claim_type"] for r in adjudicated
                                   if r["arm"] == arm})}
            for arm in ("ungated", "gated")},
        "tp_retention": (tp_g / tp_u) if tp_u else None,
        "tp_counts": {"ungated": tp_u, "gated": tp_g},
        "legacy20_subset": {
            arm: _subset(arm, lambda r: r["stratum"] == "legacy_v1")
            for arm in ("ungated", "gated")},
        "per_task_matrix": per_task,
        "gate_engagement": gate_engagement,
        "fp_reasons_gated": sorted({
            r["reason"].split("(")[0].strip()
            for r in adjudicated if r["arm"] == "gated" and r["verdict"] == "FP"}),
        "instrument": {
            "llm": "DeepSeek deepseek-v4-pro, temperature 0, 2 calls per task, "
                   "both arms",
            "capgate": "RNADA_CAPGATE=enforce (gated arm) / advisory (exp5 "
                       "control arm); packaged default SelfModel; gate key "
                       f"({GATE_TASK_TYPE}, target_family)",
            "oracle_path": "ToolExecutor.run_tool -> rhofold 8005 / proteinx "
                           "8022 / egarps 8023 (GPU 0/1/2), per-(candidate, "
                           "oracle) dedup cache seeded from Exp 5",
            "prompts": "byte-identical to legacy E3 arms (git e601913) modulo "
                       "the gated arm's gate-feedback block",
        },
    }

    out_adj = RESULTS_DIR / "adjudicated.jsonl"
    with out_adj.open("w", encoding="utf-8") as fh:
        for rec in adjudicated:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    out_sum = RESULTS_DIR / "summary.json"
    out_sum.write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                       encoding="utf-8")
    print(json.dumps({k: summary[k] for k in
                      ("n_tasks_paired", "n_claims", "arms", "tp_retention",
                       "tp_counts", "gate_engagement", "fp_reasons_gated")},
                     indent=2, ensure_ascii=False))
    print(f"adjudicated -> {out_adj}")
    print(f"blinded     -> {blind_path} (mapping sealed at {map_path.name})")
    print(f"summary     -> {out_sum}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pilot", action="store_true",
                        help="run the 8 pre-registered pilot tasks")
    parser.add_argument("--tasks", type=str, default=None,
                        help="comma-separated task ids")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--runs", type=Path, default=DEFAULT_OUT,
                        help="gated-arm runs.jsonl to adjudicate")
    parser.add_argument("--adjudicate", action="store_true",
                        help="paired dual-arm adjudication + summary")
    parser.add_argument("--seed", type=int, default=0,
                        help="blinding shuffle seed (recorded)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    if args.adjudicate:
        return cmd_adjudicate(args)
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
