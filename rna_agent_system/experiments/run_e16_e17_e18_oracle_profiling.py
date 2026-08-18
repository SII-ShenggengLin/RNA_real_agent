#!/usr/bin/env python3
"""E16/E17/E18 PRE-REGISTRATION (2026-08-18) — capability profiling of the
three runnable pending oracles on assertion-curated anchor sets.

The E16+ backlog from DECISIONS.md (j): pending-governance oracles are
profiled; each flips to enforce once a SelfModel record exists, whatever the
grade (a failed grade blocks the oracle in production — accepted user
decision 2026-08-18). CRISOT-Score and CRGPT remain pending: no labeled
anchor set exists on disk (registered data gap, DECISIONS.md (l)).

CAMPAIGNS
---------
  E16 IRESfinder (oracle iresfinder_score, task ires_prediction)
      Service :8013 POST /predict {fasta_content, mode:0} -> max_score.
      Anchors: e16_ires_anchor_set.json (3 families, binary labels).
      Grades: screening per family (AUROC > 0.8, 10k bootstrap CI seed 0).
  E17 GerNA-Bind (oracle gernabind_probability, task rna_small_molecule)
      Service :8010 POST /score {rna_sequence, smiles} -> probability_positive.
      Anchors: e17_gernabind_anchor_set.json (1 family, 4 binder/13 non).
      Grades: screening (AUROC > 0.8).
  E18 RNASTOP (oracle rnastop_stability, task full_length_mrna)
      Service :8009 POST /predict/stability {sequence} -> overall_stability
      (the exact field the deployed RNASTOPEvaluator consumes).
      Anchors: e18_rnastop_anchor_set.json (1 family, 400 x 107 nt,
      tiers 60/60 + 120 ranking-eligible).
      Grades: screening (tier AUROC > 0.8) AND ranking (Spearman rho >= 0.6
      on the 120 ranking-eligible anchors vs measured overall degradation).

GATES (identical to E1/E7; no directional pre-commitment on any family —
a failed family is a registered capability boundary, not a bug)
------------------------------------------------------------------
  Screening pass: per-family AUROC(predicted score, binder-vs-negative) > 0.8.
  Ranking pass (E18 only): Spearman rho >= 0.6 on ranking_eligible anchors.
  Cell verified iff its gate passes; GO (oracle citable as verified for the
  task) iff >= 1 family passes all applicable gates for that family.

DESIGN
------
  Step 1 (profile): score every anchor once through the service; raw
    responses cached per campaign to experiments/results/e16_e17_e18/
    <campaign>_scoring.jsonl (append-only, idempotent resume by entry id).
  Step 2 (grade + register): per-family metrics from the cache; grades via
    the calibrated stack's thresholds (profiling_metrics AUROC_PASS/RHO_PASS);
    CapabilityRecords registered through the SelfModel public API to
    experiments/results/e16_e17_e18/self_model.json.
  Step 3 (verdict): experiments/results/e16_e17_e18/verdict.json — per-family
    metrics, grades, go flags, plus the governance-flip instruction per
    oracle (pending -> enforce; build_default_self_model.py picks this up).

STAGING
-------
  S0: small sanity subset per campaign (E16: 12 anchors of family 1; E17: all
    17; E18: 12 spanning tiers). STOP on any service error or sign error
    (mean positive score <= mean negative score).
  S2: full anchor sets + grade + register + verdict.

ENGINEERING DISCIPLINE
----------------------
  Services expected running (start via microservices/*/start.sh or the
  platform service manager). Retries: 2 per call, then the row is recorded
    failed and the stage aborts (S0) or the cell registers the failure (S2).
  Zero LLM calls.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e16_e17_e18_oracle_profiling.py \
        [--campaign e16|e17|e18|all] [--stage s0|s2|all]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from scipy.stats import spearmanr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_core.calibrated.models import (  # noqa: E402
    CapabilityAssessment,
    CapabilityRecord,
    EvidencePointer,
)
from agent_core.calibrated.profiling_metrics import AUROC_PASS, RHO_PASS  # noqa: E402
from agent_core.calibrated.self_model import SelfModel  # noqa: E402
from experiments.analysis.stats_utils import bootstrap_auroc_ci  # noqa: E402

ANCHORS = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors"
RESULTS = PROJECT_ROOT / "experiments" / "results" / "e16_e17_e18"
CACHE: dict[str, Path] = {}
for _c in ("e16", "e17", "e18"):
    CACHE[_c] = RESULTS / f"{_c}_scoring.jsonl"


def _http_json(url: str, payload: dict[str, Any], timeout: int = 300) -> dict[str, Any]:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _score_e16(entry: dict[str, Any], base: str) -> float:
    out = _http_json(f"{base}/predict", {"fasta_content": entry["sequence"], "mode": 0})
    return float(out["max_score"])


def _score_e17(entry: dict[str, Any], base: str) -> float:
    out = _http_json(f"{base}/score", {"rna_sequence": entry["sequence"], "smiles": entry["smiles"]})
    return float(out["probability_positive"])


def _score_e18(entry: dict[str, Any], base: str) -> float:
    out = _http_json(f"{base}/predict/stability", {"sequence": entry["sequence"]})
    return float(out["overall_stability"])


CAMPAIGNS: dict[str, dict[str, Any]] = {
    "e16": {
        "oracle": "iresfinder_score", "task_type": "ires_prediction",
        "anchor_set": ANCHORS / "ires" / "e16_ires_anchor_set.json",
        "base_url": "http://127.0.0.1:8013", "scorer": _score_e16, "score_field": "max_score",
        "ranking": False, "s0_count": 12,
    },
    "e17": {
        "oracle": "gernabind_probability", "task_type": "rna_small_molecule",
        "anchor_set": ANCHORS / "small_molecule" / "e17_gernabind_anchor_set.json",
        "base_url": "http://127.0.0.1:8010", "scorer": _score_e17, "score_field": "probability_positive",
        "ranking": False, "s0_count": 17,
    },
    "e18": {
        "oracle": "rnastop_stability", "task_type": "full_length_mrna",
        "anchor_set": ANCHORS / "mrna_stability" / "e18_rnastop_anchor_set.json",
        "base_url": "http://127.0.0.1:8009", "scorer": _score_e18, "score_field": "overall_stability",
        "ranking": True, "s0_count": 12,
    },
}


def _load_cache(path: Path) -> dict[str, float]:
    scores: dict[str, float] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("ok"):
                scores[row["id"]] = float(row["score"])
    return scores


def _score_entries(campaign: str, entries: list[dict[str, Any]], *, retries: int = 2) -> dict[str, float]:
    cfg = CAMPAIGNS[campaign]
    cache_path = CACHE[campaign]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    scores = _load_cache(cache_path)
    with cache_path.open("a", encoding="utf-8") as fh:
        for i, entry in enumerate(entries, 1):
            if entry["id"] in scores:
                continue
            last_err = ""
            for attempt in range(retries + 1):
                try:
                    t0 = time.perf_counter()
                    score = cfg["scorer"](entry, cfg["base_url"])
                    elapsed = round(time.perf_counter() - t0, 3)
                    fh.write(json.dumps({"id": entry["id"], "ok": True, "score": score, "elapsed": elapsed}) + "\n")
                    fh.flush()
                    scores[entry["id"]] = score
                    last_err = ""
                    break
                except Exception as exc:  # noqa: BLE001
                    last_err = f"{type(exc).__name__}: {exc}"
                    time.sleep(1.0)
            if last_err:
                fh.write(json.dumps({"id": entry["id"], "ok": False, "error": last_err}) + "\n")
                fh.flush()
                raise RuntimeError(f"{campaign}: anchor {entry['id']} failed after {retries + 1} attempts: {last_err}")
            if i % 25 == 0:
                print(f"  {campaign}: {i}/{len(entries)} scored", flush=True)
    return scores


def _s0_subset(campaign: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cfg = CAMPAIGNS[campaign]
    if campaign == "e17":
        return entries
    if campaign == "e16":
        fam = sorted({e["target"] for e in entries})[0]
        pos = [e for e in entries if e["target"] == fam and e["role"] == "binder"][:6]
        neg = [e for e in entries if e["target"] == fam and e["role"] == "negative"][:6]
        return pos + neg
    # e18: 6 binder-tier + 6 negative-tier of the single family
    pos = [e for e in entries if e["role"] == "binder"][:6]
    neg = [e for e in entries if e["role"] == "negative"][:6]
    return pos + neg


def _grade_campaign(campaign: str, entries: list[dict[str, Any]], scores: dict[str, float]) -> dict[str, Any]:
    cfg = CAMPAIGNS[campaign]
    families = sorted({e["target"] for e in entries})
    cells: dict[str, dict[str, Any]] = {}
    for fam in families:
        fam_entries = [e for e in entries if e["target"] == fam]
        pos = [scores[e["id"]] for e in fam_entries if e["role"] == "binder"]
        neg = [scores[e["id"]] for e in fam_entries if e["role"] == "negative"]
        auroc, lo, hi = bootstrap_auroc_ci(pos, neg)
        cell: dict[str, Any] = {
            "n_binder": len(pos), "n_negative": len(neg),
            "auroc": round(auroc, 4), "auroc_ci": [round(lo, 4), round(hi, 4)],
            "screening_pass": bool(auroc > AUROC_PASS),
        }
        if cfg["ranking"]:
            ranked = [(scores[e["id"]], e["measured_overall_stability"])
                      for e in fam_entries if e.get("ranking_eligible")]
            rho, pval = spearmanr([p for p, _ in ranked], [m for _, m in ranked])
            cell.update({
                "n_ranking": len(ranked),
                "spearman_rho": round(float(rho), 4), "spearman_p": float(pval),
                "ranking_pass": bool(rho >= RHO_PASS),
            })
            cell["all_gates_pass"] = bool(cell["screening_pass"] and cell["ranking_pass"])
        else:
            cell["all_gates_pass"] = cell["screening_pass"]
        cells[fam] = cell
    return {
        "campaign": campaign, "oracle": cfg["oracle"], "task_type": cfg["task_type"],
        "score_field": cfg["score_field"], "graded_at": datetime.now(timezone.utc).isoformat(),
        "cells": cells,
        "go": any(c["all_gates_pass"] for c in cells.values()),
        "governance_flip": "pending -> enforce (record exists; grade whatever it is)",
    }


def _register_self_model(verdicts: list[dict[str, Any]]) -> Path:
    model = SelfModel()
    for v in verdicts:
        for fam, cell in v["cells"].items():
            caps: dict[str, CapabilityAssessment] = {
                "screening": CapabilityAssessment(
                    grade="verified" if cell["screening_pass"] else "failed",
                    confidence=1.0,
                    metrics={"auroc": cell["auroc"], "auroc_ci_lo": cell["auroc_ci"][0], "auroc_ci_hi": cell["auroc_ci"][1]},
                    evidence=[
                        EvidencePointer(kind="jsonl", path=str(CACHE[v["campaign"]].relative_to(PROJECT_ROOT)),
                                        note=f"{v['campaign']} raw oracle responses ({v['score_field']})"),
                        EvidencePointer(kind="summary_json", path=str((RESULTS / "verdict.json").relative_to(PROJECT_ROOT)),
                                        note=f"{v['campaign']} verdict (gates identical to E1/E7)"),
                    ],
                    profiled_at=v["graded_at"],
                )
            }
            if "spearman_rho" in cell:
                caps["ranking"] = CapabilityAssessment(
                    grade="verified" if cell["ranking_pass"] else "failed",
                    confidence=1.0,
                    metrics={"spearman_rho": cell["spearman_rho"], "spearman_p": cell["spearman_p"]},
                    evidence=caps["screening"].evidence,
                    profiled_at=v["graded_at"],
                )
            model.update(CapabilityRecord(
                oracle=v["oracle"], task_type=v["task_type"], target_family=fam, capabilities=caps,
            ))
    out = RESULTS / "self_model.json"
    out.write_text(json.dumps(model.to_dict(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def run(campaign: str, stage: str) -> None:
    cfg = CAMPAIGNS[campaign]
    entries = json.loads(cfg["anchor_set"].read_text(encoding="utf-8"))["entries"]
    if stage == "s0":
        subset = _s0_subset(campaign, entries)
        scores = _score_entries(campaign, subset)
        pos = [scores[e["id"]] for e in subset if e["role"] == "binder"]
        neg = [scores[e["id"]] for e in subset if e["role"] == "negative"]
        mean_pos, mean_neg = sum(pos) / len(pos), sum(neg) / len(neg)
        print(f"{campaign} S0: n={len(subset)} mean_binder={mean_pos:.4f} mean_negative={mean_neg:.4f}")
        if mean_pos <= mean_neg:
            raise SystemExit(f"{campaign} S0 SIGN ERROR: binder mean <= negative mean — stop before S2")
        print(f"{campaign} S0 OK")
        return

    # s2: full campaign
    scores = _score_entries(campaign, entries)
    verdict = _grade_campaign(campaign, entries, scores)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{campaign}_verdict.json").write_text(
        json.dumps(verdict, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(verdict["cells"], indent=1))
    print(f"{campaign} go={verdict['go']}")


def finalize() -> None:
    verdicts = [json.loads((RESULTS / f"{c}_verdict.json").read_text(encoding="utf-8"))
                for c in ("e16", "e17", "e18")]
    combined = {
        "preregistration": "experiments/run_e16_e17_e18_oracle_profiling.py docstring (E16-E18 PRE-REGISTRATION, 2026-08-18)",
        "graded_at": datetime.now(timezone.utc).isoformat(),
        "campaigns": verdicts,
        "notes": [
            "CRISOT-Score (crisot_off_target_score) and CRGPT (crgpt_handle_score) remain governance=pending: "
            "no labeled anchor set exists on disk (registered data gap, DECISIONS.md (l)).",
        ],
    }
    (RESULTS / "verdict.json").write_text(json.dumps(combined, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    model_path = _register_self_model(verdicts)
    print(f"combined verdict -> {RESULTS / 'verdict.json'}")
    print(f"SelfModel -> {model_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", choices=["e16", "e17", "e18", "all", "finalize"], default="all")
    parser.add_argument("--stage", choices=["s0", "s2", "all"], default="all")
    args = parser.parse_args()

    if args.campaign == "finalize":
        finalize()
        return 0

    campaigns = ["e16", "e17", "e18"] if args.campaign == "all" else [args.campaign]
    for c in campaigns:
        stages = ["s0", "s2"] if args.stage == "all" else [args.stage]
        for s in stages:
            run(c, s)
    if args.campaign == "all" and args.stage in ("s2", "all"):
        finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
