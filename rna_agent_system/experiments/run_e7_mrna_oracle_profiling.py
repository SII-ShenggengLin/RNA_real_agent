#!/usr/bin/env python3
"""E7 PRE-REGISTRATION (2026-08-11) — capability profiling of the mRNA
workflow's expression oracle (GEMORNA 5'UTR MRL) on measured-MRL anchor sets.

The mRNA-side counterpart of the E1 aptamer-oracle profiling
(`run_e1_capability_profiling.py`). Zero LLM calls.

QUESTION
--------
What screening/ranking capabilities does the deployed 5'UTR expression
oracle actually have for full-length mRNA design campaigns, measured
against EXPERIMENTAL mean ribosome load (MRL) anchors?
  Oracle: gemorna_5utr_mrl (GEMORNA 5'UTR MRL predictor; microservice
    :8004, POST /predict/5utr_mrl {"sequence": ...} -> {"predicted_mrl"};
    DNA anchors scored as RNA via T->U service-side, same convention as E1).
  Anchor set: data/benchmarks/external_anchors/utr_mrl/e7_mrl_anchor_set.json
    (706 entries, 3 families; generator: experiments/curate_e7_mrl_anchor_set.py).
  Families (Sample et al. 2019 Nat Biotechnol 37:803-809, GEO GSE114002;
  MPRA polysome profiling, EGFP reporter, unmodified RNA, HEK293T):
    - sample2019_egfp_random50        (GSM3130435, random 50-nt library;
      IN-TRAINING-DISTRIBUTION: GEMORNA's MRL head was trained on this assay)
    - sample2019_varying_length_random (GSM4084997 set=random, 25-100 nt)
    - sample2019_varying_length_human  (GSM4084997 set=human, endogenous)

PRE-REGISTERED HYPOTHESIS
-------------------------
The in-training-distribution family (sample2019_egfp_random50) PASSES both
gates — the positive contrast to the E1 aptamer oracles (all failed). The
two varying-length families are the registered boundary probe: no
directional pre-commitment; a failed family is a registered capability
boundary, not a bug.

GATES (identical to E1)
-----------------------
  Screening pass: per-family AUROC(predicted_mrl, high- vs low-MRL tier)
    > 0.8; 95% CI by 10,000-fold bootstrap, seed 0
    (experiments/analysis/stats_utils.bootstrap_auroc_ci defaults).
  Ranking pass: per-family Spearman rho >= 0.6 of predicted_mrl vs measured
    rl on the 120 ranking_eligible anchors.
  Grading: each (oracle, family) cell graded verified/failed per gate via
  the calibrated stack's thresholds (profiling_metrics AUROC_PASS/RHO_PASS).
  The stack's own profiling_metrics.ranking_metrics expects kd_nm, so E7
  computes AUROC/Spearman in this driver and registers the resulting grades
  through the stack's public API only (no calibrated-stack modifications).
  GO: >= 1 family passes BOTH gates -> the mRNA workflow has at least one
  verified expression-oracle capability cell (contrast to E1's all-fail).

DESIGN
------
  Step 1 (profile): score every anchor once through the service; raw
    responses cached to experiments/results/e7_mrl_scoring.jsonl
    (idempotent resume by entry id). Per-family screening AUROC + CI and
    ranking Spearman computed from the cache; cells graded per gate.
  Step 2 (register): CapabilityRecord(s) for oracle gemorna_5utr_mrl,
    task_type full_length_mrna, target_family per family, written into a
    SelfModel persisted at experiments/results/e7_selfmodel/self_model.json
    (SelfModel/CapabilityRecord public API only).
  Step 3 (gate demonstration, experiments/results/e7_gate_demo.jsonl):
    (a) PlannedAction ranking 5'UTR candidates by gemorna_5utr_mrl on a
        verified family -> DecisionGate ALLOWED.
    (b) the same action on an unprofiled family -> pre-registered
        expectation: require_profiling. NOTE (registered before running):
        SelfModel.query transfers same-(oracle, task_type) grades across
        families with decayed confidence (design doc §2.3 step 1), so the
        actual verdict for a never-profiled family is the transfer verdict
        (downgrade from a verified donor / reject from a failed donor);
        the plain require_profiling path is demonstrated by (c).
    (c) PlannedAction ranking by gemorna_3utr_stability (no measured anchor
        set exists; unprofiled by design) -> require_profiling.
    (d) ClaimGate: an absolute-scope expression claim depending on
        gemorna_5utr_mrl ranking on the unprofiled family -> downgrade to
        within_target_relative (transferred verified grade).
  Step 4 (verdict): experiments/results/e7_mrna_oracle_profile_summary.json
    with per-family AUROC/CI/rho, grades, gate-demo outcomes, and go.

STAGING
-------
  S0: 12 anchors (6 high / 6 low of sample2019_egfp_random50) sanity +
    timing. STOP if any service error, or mean predicted MRL of the high
    tier <= low tier (sign error), or 12-point Spearman <= 0.
  S1: family 1 full (238 anchors). STOP on any service error.
  S2: all families + register + gate demo + verdict.

ENGINEERING DISCIPLINE
----------------------
  - The service is expected already running at http://127.0.0.1:8004
    (~0.1 s/call; ~706 calls total). Retries: 2 per call, then the row is
    recorded failed and the stage aborts (S0/S1) or the cell is recorded
    with the failure (S2, registered boundary).
  - Scoring cache is append-only jsonl; re-running is idempotent (success
    rows are not re-scored).

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e7_mrna_oracle_profiling.py \
        [--stage s0|s1|s2|all] [--service-url URL] [--anchor-set PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from scipy.stats import spearmanr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_core.calibrated.claim_gate import ClaimGate  # noqa: E402
from agent_core.calibrated.decision_gate import DecisionGate  # noqa: E402
from agent_core.calibrated.models import (  # noqa: E402
    CapabilityAssessment,
    CapabilityRecord,
    Claim,
    ClaimDependency,
    EvidencePointer,
    PlannedAction,
)
from agent_core.calibrated.profiling_metrics import AUROC_PASS, RHO_PASS  # noqa: E402
from agent_core.calibrated.self_model import SelfModel  # noqa: E402
from experiments.analysis.stats_utils import bootstrap_auroc_ci  # noqa: E402

ANCHOR_SET = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "utr_mrl" / "e7_mrl_anchor_set.json"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
SCORING_JSONL = RESULTS_DIR / "e7_mrl_scoring.jsonl"
GATE_DEMO_JSONL = RESULTS_DIR / "e7_gate_demo.jsonl"
SUMMARY_JSON = RESULTS_DIR / "e7_mrna_oracle_profile_summary.json"
SELFMODEL_DIR = RESULTS_DIR / "e7_selfmodel"

ORACLE = "gemorna_5utr_mrl"
UNPROFILED_ORACLE = "gemorna_3utr_stability"  # no measured anchor set exists — unprofiled by design
TASK_TYPE = "full_length_mrna"
UNPROFILED_FAMILY = "unprofiled_novel_utr_family"
PROFILE_DATE = "2026-08-11"
DEFAULT_SERVICE_URL = "http://127.0.0.1:8004/predict/5utr_mrl"
FAMILY1 = "sample2019_egfp_random50"

EVIDENCE = [
    EvidencePointer(
        kind="jsonl",
        path="experiments/results/e7_mrl_scoring.jsonl",
        note="E7 raw gemorna_5utr_mrl oracle responses per anchor (706 entries, 3 families)",
    ),
    EvidencePointer(
        kind="summary_json",
        path="experiments/results/e7_mrna_oracle_profile_summary.json",
        note="E7 profiling verdict summary (gates identical to E1: AUROC>0.8, rho>=0.6)",
    ),
]


# ── scoring ──────────────────────────────────────────────────────────────────

def score_anchor(entry: dict, service_url: str, retries: int = 2) -> dict:
    """One oracle call; the raw service response is preserved verbatim."""
    req = {"sequence": entry["sequence"]}
    body = json.dumps(req).encode("utf-8")
    t0 = time.perf_counter()
    resp: dict | None = None
    error: str | None = None
    for attempt in range(retries + 1):
        try:
            http_req = urllib.request.Request(
                service_url, data=body, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(http_req, timeout=30) as fh:
                resp = json.loads(fh.read().decode("utf-8"))
            error = None
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            error = f"{type(exc).__name__}: {exc}"[:300]
            time.sleep(0.5 * (attempt + 1))
    elapsed = time.perf_counter() - t0
    pred = resp.get("predicted_mrl") if resp else None
    return {
        "id": entry["id"],
        "target": entry["target"],
        "role": entry["role"],
        "ranking_eligible": entry["ranking_eligible"],
        "measured_mrl": entry["measured_mrl"],
        "total_reads": entry["total_reads"],
        "length_nt": entry["length_nt"],
        "alphabet": entry["alphabet"],
        "oracle": ORACLE,
        "request": req,
        "response": resp,
        "predicted_mrl": pred,
        "success": resp is not None and pred is not None,
        "error": error if error is not None else (None if pred is not None else "no predicted_mrl in response"),
        "elapsed_seconds": round(elapsed, 3),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def load_cache(path: Path) -> dict[str, dict]:
    done: dict[str, dict] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("success"):
                done[row["id"]] = row
    return done


def score_entries(entries: list[dict], service_url: str, cache: dict[str, dict]) -> tuple[int, int]:
    """Score all entries not already in *cache*; append rows to SCORING_JSONL."""
    n_ok = n_fail = 0
    with SCORING_JSONL.open("a", encoding="utf-8") as fh:
        for i, entry in enumerate(entries, 1):
            if entry["id"] in cache:
                continue
            row = score_anchor(entry, service_url)
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            if row["success"]:
                cache[entry["id"]] = row
                n_ok += 1
            else:
                n_fail += 1
                print(f"    SERVICE ERROR {entry['id']}: {row['error']}", flush=True)
            if i % 60 == 0 or i == len(entries):
                print(f"    scored {i}/{len(entries)}", flush=True)
    return n_ok, n_fail


# ── metrics (computed in this driver; the stack's ranking metric expects kd_nm) ──

def family_metrics(rows: list[dict]) -> dict:
    pos = [r["predicted_mrl"] for r in rows if r["role"] == "binder"]
    neg = [r["predicted_mrl"] for r in rows if r["role"] == "negative"]
    auroc, ci_lo, ci_hi = bootstrap_auroc_ci(pos, neg)  # 10,000-fold, seed 0 (defaults)
    rk = [(r["predicted_mrl"], r["measured_mrl"]) for r in rows if r["ranking_eligible"]]
    rho = float("nan")
    if len(rk) >= 3:
        rho = float(spearmanr([p for p, _ in rk], [m for _, m in rk]).statistic)
    return {
        "n_scored": len(rows),
        "screening": {
            "auroc": auroc, "auroc_ci_lo": ci_lo, "auroc_ci_hi": ci_hi,
            "n_pos": len(pos), "n_neg": len(neg),
            "grade": "verified" if auroc > AUROC_PASS else "failed",
        },
        "ranking": {
            "spearman_rho": rho, "n": len(rk),
            "grade": "verified" if rho >= RHO_PASS else "failed",
        },
    }


def print_family_metrics(family: str, m: dict) -> None:
    s, r = m["screening"], m["ranking"]
    print(f"  {family}: AUROC {s['auroc']:.4f} [95% CI {s['auroc_ci_lo']:.4f}-{s['auroc_ci_hi']:.4f}] "
          f"(n={s['n_pos']}v{s['n_neg']}) -> {s['grade']}; Spearman {r['spearman_rho']:.4f} "
          f"(n={r['n']}) -> {r['grade']}", flush=True)


# ── stages ───────────────────────────────────────────────────────────────────

def stage_s0(entries: list[dict], service_url: str) -> bool:
    fam1 = [e for e in entries if e["target"] == FAMILY1]
    high = sorted((e for e in fam1 if e["role"] == "binder"), key=lambda e: -e["measured_mrl"])[:6]
    low = sorted((e for e in fam1 if e["role"] == "negative"), key=lambda e: e["measured_mrl"])[:6]
    cohort = high + low
    print(f"S0 sanity: {len(cohort)} anchors (6 high / 6 low, {FAMILY1})", flush=True)
    cache = load_cache(SCORING_JSONL)
    n_ok, n_fail = score_entries(cohort, service_url, cache)
    rows = [cache[e["id"]] for e in cohort if e["id"] in cache]
    if n_fail or len(rows) != len(cohort):
        print(f"S0 STOP: {n_fail} service errors / {len(rows)}/{len(cohort)} scored", flush=True)
        return False
    high_pred = [r["predicted_mrl"] for r in rows if r["role"] == "binder"]
    low_pred = [r["predicted_mrl"] for r in rows if r["role"] == "negative"]
    for r in rows:
        print(f"    {r['id']}: measured={r['measured_mrl']:.3f} predicted={r['predicted_mrl']:.3f} "
              f"({r['elapsed_seconds']:.2f}s)", flush=True)
    times = sorted(r["elapsed_seconds"] for r in rows)
    rho = float(spearmanr([r["predicted_mrl"] for r in rows], [r["measured_mrl"] for r in rows]).statistic)
    print(f"  mean predicted MRL: high tier {sum(high_pred) / len(high_pred):.3f} vs "
          f"low tier {sum(low_pred) / len(low_pred):.3f}; 12-point Spearman {rho:.3f}; "
          f"per-call seconds min/med/max {times[0]:.2f}/{times[len(times) // 2]:.2f}/{times[-1]:.2f}",
          flush=True)
    if sum(high_pred) <= sum(low_pred):
        print("S0 STOP: sign error — high-tier mean prediction <= low-tier mean", flush=True)
        return False
    if rho <= 0:
        print("S0 STOP: predictions uncorrelated with measurement (rho <= 0)", flush=True)
        return False
    print("S0 PASS", flush=True)
    return True


def stage_s1(entries: list[dict], service_url: str) -> bool:
    fam1 = [e for e in entries if e["target"] == FAMILY1]
    print(f"S1: family {FAMILY1} full ({len(fam1)} anchors)", flush=True)
    cache = load_cache(SCORING_JSONL)
    _, n_fail = score_entries(fam1, service_url, cache)
    if n_fail:
        print(f"S1 STOP: {n_fail} service errors", flush=True)
        return False
    rows = [cache[e["id"]] for e in fam1]
    m = family_metrics(rows)
    print_family_metrics(FAMILY1, m)
    print("S1 done", flush=True)
    return True


def register_self_model(per_family: dict[str, dict]) -> SelfModel:
    records: list[CapabilityRecord] = []
    for family in sorted(per_family):
        m = per_family[family]
        caps = {
            "screening": CapabilityAssessment(
                grade=m["screening"]["grade"], confidence=1.0,
                metrics={"auroc": m["screening"]["auroc"],
                         "auroc_ci_lo": m["screening"]["auroc_ci_lo"],
                         "auroc_ci_hi": m["screening"]["auroc_ci_hi"]},
                evidence=EVIDENCE, profiled_at=PROFILE_DATE,
            ),
            "ranking": CapabilityAssessment(
                grade=m["ranking"]["grade"], confidence=1.0,
                metrics={"spearman_rho": m["ranking"]["spearman_rho"]},
                evidence=EVIDENCE, profiled_at=PROFILE_DATE,
            ),
        }
        records.append(CapabilityRecord(
            oracle=ORACLE, task_type=TASK_TYPE, target_family=family, capabilities=caps,
        ))
    self_model = SelfModel(records)
    SELFMODEL_DIR.mkdir(parents=True, exist_ok=True)
    out = SELFMODEL_DIR / "self_model.json"
    out.write_text(json.dumps(self_model.to_dict(), indent=1, ensure_ascii=False) + "\n")
    print(f"  SelfModel persisted: {out} ({len(records)} records)", flush=True)
    return self_model


def run_gate_demo(self_model: SelfModel, per_family: dict[str, dict]) -> list[dict]:
    verified = [f for f in sorted(per_family)
                if per_family[f]["screening"]["grade"] == "verified"
                and per_family[f]["ranking"]["grade"] == "verified"]
    gate = DecisionGate(self_model)
    claim_gate = ClaimGate(self_model)  # deterministic templates; no LLM polish
    demos: list[dict] = []

    def log(demo: dict) -> None:
        demos.append(demo)
        with GATE_DEMO_JSONL.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(demo, ensure_ascii=False, default=str) + "\n")

    # (a) ranking action by gemorna_5utr_mrl on a verified family -> allow
    if verified:
        fam = verified[0]
        action = PlannedAction(action_id="e7_demo_a", kind="oracle_lookup",
                               oracle=ORACLE, use="ranking_objective")
        d = gate.review([action], task_type=TASK_TYPE, target_family=fam)[0]
        log({"demo": "a_ranking_action_on_verified_family", "gate": "DecisionGate",
             "action": action.model_dump(mode="json"), "task_type": TASK_TYPE, "target_family": fam,
             "expected_verdict": "allow", "actual_verdict": d.verdict,
             "expectation_met": d.verdict == "allow", "decision": d.model_dump(mode="json")})
    else:
        log({"demo": "a_ranking_action_on_verified_family", "gate": "DecisionGate",
             "expected_verdict": "allow", "actual_verdict": None, "expectation_met": False,
             "note": "no family passed both gates; demo (a) not runnable"})

    # (b) same action on an unprofiled family. Pre-registered expectation was
    # require_profiling; the stack's transfer semantics (SelfModel.query
    # migrates same-(oracle, task_type) grades across families) make the
    # actual verdict the transfer verdict. Recorded honestly both ways.
    action = PlannedAction(action_id="e7_demo_b", kind="oracle_lookup",
                           oracle=ORACLE, use="ranking_objective")
    d = gate.review([action], task_type=TASK_TYPE, target_family=UNPROFILED_FAMILY)[0]
    log({"demo": "b_ranking_action_on_unprofiled_family", "gate": "DecisionGate",
         "action": action.model_dump(mode="json"), "task_type": TASK_TYPE,
         "target_family": UNPROFILED_FAMILY,
         "expected_verdict": "require_profiling", "actual_verdict": d.verdict,
         "expectation_met": d.verdict == "require_profiling",
         "note": ("SelfModel transfers same-(oracle, task_type) grades across families with "
                  "decayed confidence (design doc 2.3 step 1); a never-profiled family therefore "
                  "yields the transfer verdict (downgrade from a verified donor / reject from a "
                  "failed donor), not require_profiling. The plain require_profiling path is "
                  "demonstrated by demo (c)."),
         "decision": d.model_dump(mode="json")})

    # (c) ranking action by gemorna_3utr_stability (no measured anchor set
    # exists — unprofiled by design) -> require_profiling
    if verified:
        fam = verified[0]
        action = PlannedAction(action_id="e7_demo_c", kind="oracle_lookup",
                               oracle=UNPROFILED_ORACLE, use="ranking_objective")
        d = gate.review([action], task_type=TASK_TYPE, target_family=fam)[0]
        log({"demo": "c_ranking_action_unprofiled_oracle_3utr_stability", "gate": "DecisionGate",
             "action": action.model_dump(mode="json"), "task_type": TASK_TYPE, "target_family": fam,
             "expected_verdict": "require_profiling", "actual_verdict": d.verdict,
             "expectation_met": d.verdict == "require_profiling",
             "decision": d.model_dump(mode="json")})

    # (d) ClaimGate: absolute expression claim depending on gemorna_5utr_mrl
    # ranking on the unprofiled family -> downgrade absolute ->
    # within_target_relative (transferred verified grade)
    claim = Claim(
        claim_id="e7_demo_d",
        text="5'UTR candidate A will drive higher protein expression than candidate B in the final mRNA.",
        claim_type="ranking", scope="absolute",
        dependencies=[ClaimDependency(oracle=ORACLE, capability="ranking")],
    )
    v = claim_gate.review([claim], task_type=TASK_TYPE, target_family=UNPROFILED_FAMILY)[0]
    log({"demo": "d_absolute_expression_claim_downgrade", "gate": "ClaimGate",
         "claim": claim.model_dump(mode="json"), "task_type": TASK_TYPE,
         "target_family": UNPROFILED_FAMILY,
         "expected_verdict": "downgrade", "expected_scope": "within_target_relative",
         "actual_verdict": v.verdict,
         "expectation_met": v.verdict == "downgrade",
         "verdict_detail": v.model_dump(mode="json")})
    return demos


def stage_s2(entries: list[dict], service_url: str) -> bool:
    families = sorted({e["target"] for e in entries})
    print(f"S2: all families {families}", flush=True)
    cache = load_cache(SCORING_JSONL)
    fails = 0
    for fam in families:
        fam_entries = [e for e in entries if e["target"] == fam]
        _, n_fail = score_entries(fam_entries, service_url, cache)
        fails += n_fail
    if fails:
        print(f"S2 WARNING: {fails} service errors (failed rows excluded from metrics)", flush=True)

    per_family: dict[str, dict] = {}
    for fam in families:
        rows = [cache[e["id"]] for e in entries if e["target"] == fam and e["id"] in cache]
        per_family[fam] = family_metrics(rows)
        print_family_metrics(fam, per_family[fam])

    print("Step 2: registering CapabilityRecords into SelfModel ...", flush=True)
    self_model = register_self_model(per_family)

    print("Step 3: gate demonstration ...", flush=True)
    demos = run_gate_demo(self_model, per_family)
    for d in demos:
        print(f"  {d['demo']}: expected={d.get('expected_verdict')} actual={d.get('actual_verdict')} "
              f"met={d.get('expectation_met')}", flush=True)

    go = any(m["screening"]["grade"] == "verified" and m["ranking"]["grade"] == "verified"
             for m in per_family.values())
    summary = {
        "experiment": "E7 — capability profiling of the mRNA workflow's expression oracle "
                      "(gemorna_5utr_mrl) on measured-MRL anchor sets",
        "date": PROFILE_DATE,
        "oracle": ORACLE,
        "task_type": TASK_TYPE,
        "anchor_set": "data/benchmarks/external_anchors/utr_mrl/e7_mrl_anchor_set.json",
        "preregistration": "experiments/run_e7_mrna_oracle_profiling.py docstring (2026-08-11)",
        "gates": {
            "screening": f"AUROC > {AUROC_PASS} (10,000-fold bootstrap 95% CI, seed 0)",
            "ranking": f"Spearman rho >= {RHO_PASS} on ranking_eligible vs measured rl",
        },
        "per_family": per_family,
        "self_model": "experiments/results/e7_selfmodel/self_model.json",
        "gate_demo": demos,
        "go": go,
        "notes": [
            "sample2019_egfp_random50 is in-training-distribution for GEMORNA's MRL head "
            "(trained on this assay); a pass there is the pre-registered positive control.",
            "A failed family is a registered capability boundary, not a bug.",
            "gemorna_3utr_stability remains unprofiled by design (no measured anchor set).",
        ],
        "service_errors": fails,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n")
    print(f"\nStep 4 verdict: go={go} -> {SUMMARY_JSON}", flush=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", choices=["s0", "s1", "s2", "all"], default="all")
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    parser.add_argument("--anchor-set", type=Path, default=ANCHOR_SET)
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    doc = json.loads(args.anchor_set.read_text(encoding="utf-8"))
    entries = doc["entries"]
    print(f"E7 driver: {len(entries)} anchors, oracle {ORACLE}, stage {args.stage}", flush=True)

    if args.stage in ("s0", "all"):
        if not stage_s0(entries, args.service_url):
            return 2
    if args.stage in ("s1", "all"):
        if not stage_s1(entries, args.service_url):
            return 2
    if args.stage in ("s2", "all"):
        if not stage_s2(entries, args.service_url):
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
