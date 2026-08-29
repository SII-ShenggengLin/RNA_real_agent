#!/usr/bin/env python3
"""Experiment 15 (paper §2.3, Fig. 3h; user sequence §2.3-实验7): RNAsmol
deployment-artifact fidelity — the platform's default agent tool path versus
the fidelity-correct service-endpoint path, both measured live on the same
deployed oracle over its own official held-out test splits.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2)
-----------------------------------------------------
* Question: does the platform's shipped integration path deliver the
  oracle's published held-out performance, and what does the
  fidelity-correct path deliver on identical inputs?
* Arms (fixed before any run; both hit the SAME running service):
  1. ``tool_layer`` (defect-class arm — the platform's production default):
     every pair scored through ``ToolExecutor.run_tool(
     "score_rna_ligand_binding_with_rnasmol", ...)`` with the verbatim
     source sequence written to a scratch file and the registered
     checkpoint auto-selection hints. The tool wrapper applies
     ``_normalize_nucleic_sequence`` (uppercase + T→U + strip non-A-Z,
     tools.py) to its input — the live equivalent of the v0.2.0
     deployment-fidelity defect class: the official splits encode
     modified bases in lowercase and the upstream vocab is case-sensitive.
     ``RNADA_CAPGATE=advisory`` (driver default; the documented regression
     convention), audit runtime active via ``runtime_from_env()`` so every
     call lands in ``workspace/audit/platform_audit.jsonl``.
  2. ``service_endpoint`` (fidelity-correct arm — exp7's registered
     protocol): case-preserving verbatim ``POST /score`` with the same
     hints, no tool-layer normalization.
* Inputs — the two official upstream held-out test splits, verbatim
  (order = source-file order; no sampling, no exclusions):
  - ``robin_test`` — ``external_repos/RNAsmol/rnasmol/data/
    robin_molperturbation/raw/data_test.csv`` (n = 1492; 763 positives /
    729 negatives; ROBIN-derived RNA–small-molecule pairs,
    molecule-perturbation decoys; 29,250 lowercase nucleotides).
  - ``pdb_test`` — ``.../pdb_molperturbation/raw/data_test.csv``
    (n = 170; 87/83; PDB-derived pairs; 37,209 lowercase nucleotides;
    44 sequences >500 nt, truncated service-side, counted and reported).
  Not in scope: the FMN/MALAT1 decoy case studies and the OOD aptamer
  panel (Fig. 2g evidence; their inputs are all-uppercase, so the two
  integration paths are indistinguishable on them — no contrast).
* Instrument — no platform intervention: the deployed RNAsmol
  microservice exactly as the platform ships it
  (``microservices/rnasmol_service/start.sh``, CPU per the packaged
  default, port 8007). No ``checkpoint_path``/``device`` overrides;
  dataset + perturbation_type hints only (robin+molperturbation /
  pdb+molperturbation — the retained evidence's resolution). No
  thresholds, no preprocessing knobs, no retries with changed
  parameters; HTTP 400s (degenerate SMILES graphs) are recorded as
  failures and reported as-is.
* Historical reference (context only, never gated on): the v0.2.0-era
  service (uppercased vocab) measured AUROC 0.7864 / 0.4103 on these
  splits; the upstream-official pipeline and the v0.3.0 repaired service
  measure 0.9744 / 0.9828, reproduced exactly by the exp7 reset re-run
  (2026-08-26, ``results/exp7_rnasmol_boundary/``). The live tool-layer
  arm is the same defect class but is NOT expected to be bit-identical
  to the v0.2.0 numbers (that defect lived service-side; this arm is
  agent-side normalization on the current stack).
* Primary metrics: per (arm, split), AUROC of ``probability_positive``
  (midrank Mann–Whitney, ties = half credit); stratified bootstrap over
  pairs, 10,000 replicates, ``numpy`` default_rng seed 20260829,
  percentile 95% CI; two-sided Mann–Whitney P; Cliff's δ = 2·AUROC − 1.
  Descriptive: pdb ≤500-nt subset AUROC per arm.
* Registered fidelity checks:
  1. Arm B reproduces the exp7 numbers of record to 4 decimals on both
     splits; per-pair |Δprobability| vs the exp7 JSONL reported
     (order-matched by CSV row index; >1e-3 carried as a
     backend-arithmetic warning line only, per exp7's registered
     amendment — per-pair bit-identity is not expected across
     inference backends).
  2. Arm A normalization verified per record: the tool-echoed
     ``rna_sequence`` equals uppercase+T→U+strip of the verbatim source
     (any mismatch is reported as a premise failure).
  3. Checkpoint resolution identical across arms per pair (echoed
     checkpoint names must match).
* Defect-class criterion (primary): arm A falls below the 0.8 screening
  gate on both splits while arm B clears it on both — the silent
  fidelity gap demonstrated live, as a class (direction and gate), not
  gated on the historical 0.7864/0.4103 values.
* Go/no-go: pilot = first 5 rows of each split × each arm (20 calls);
  every pilot call must return a recorded probability before the full
  run. Full-run scoring failures are reported as-is (no re-runs, no
  exclusions).
* Compute: the RNAsmol service is CPU-pinned by its platform start
  script — no GPU allocation (GPUs 0–2 untouched).
* Budget: one call per pair per arm = 3,324 scoring calls; ``--resume``
  skips (arm, split, key) records already successful on disk.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp15_rnasmol_fidelity.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp15_rnasmol_fidelity.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp15_rnasmol_fidelity.py --summary

Outputs under ``experiments/results/exp15_rnasmol_fidelity/``:
    scoring_runs.jsonl, summary.json, scratch/ (arm-A sequence files)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import os

os.environ.setdefault("RNADA_CAPGATE", "advisory")

RNASMOL_REPO = PROJECT_ROOT / "external_repos" / "RNAsmol" / "rnasmol" / "data"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp15_rnasmol_fidelity"
RUNS_JSONL = RESULTS_DIR / "scoring_runs.jsonl"
SCRATCH_DIR = RESULTS_DIR / "scratch"
EXP7_RESULTS = PROJECT_ROOT / "experiments" / "results" / "exp7_rnasmol_boundary"

SERVICE_URL = "http://127.0.0.1:8007/score"
HEALTH_URL = "http://127.0.0.1:8007/health"
SERVICE_START = PROJECT_ROOT / "microservices" / "rnasmol_service" / "start.sh"

TOOL = "score_rna_ligand_binding_with_rnasmol"

# Split → (raw CSV, checkpoint provenance hints). Registered verbatim from
# the retained evidence's per-record checkpoint resolution (exp7).
SPLITS: dict[str, tuple[Path, dict[str, str]]] = {
    "robin_test": (RNASMOL_REPO / "robin_molperturbation" / "raw" / "data_test.csv",
                   {"dataset": "robin", "perturbation_type": "molperturbation"}),
    "pdb_test": (RNASMOL_REPO / "pdb_molperturbation" / "raw" / "data_test.csv",
                 {"dataset": "pdb", "perturbation_type": "molperturbation"}),
}
ARMS = ("tool_layer", "service_endpoint")

BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20260829
PILOT_CSV_ROWS = 5
RNA_TRUNCATION_LENGTH = 500  # service-side pad/truncate length (platform default)

_EXP7_SUMMARY: dict[str, Any] | None = None


# --------------------------------------------------------------------- inputs

def load_split(split: str) -> list[dict[str, Any]]:
    """Load one split's pairs verbatim; order is the source-file order."""
    csv_path, _ = SPLITS[split]
    with csv_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [
        {
            "split": split,
            "key": str(i),
            "smiles": r["compound_iso_smiles"],
            "rna_sequence": r["target_sequence"],
            "label": float(r["affinity"]),
        }
        for i, r in enumerate(rows)
    ]


def expected_tool_normalization(source: str) -> str:
    """What the tool layer's _normalize_nucleic_sequence must produce."""
    return re.sub(r"[^A-Z]", "", source.upper()).replace("T", "U")


# ------------------------------------------------------------------- service

def ensure_service(timeout_s: int = 300) -> bool:
    """Health-check the deployed service; start it via the platform script."""
    import requests
    try:
        requests.get(HEALTH_URL, timeout=3).raise_for_status()
        return True
    except requests.RequestException:
        pass
    print("[service] starting RNAsmol via the platform start.sh (CPU default) ...",
          flush=True)
    subprocess.Popen(
        ["bash", str(SERVICE_START)],
        cwd=SERVICE_START.parent,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            requests.get(HEALTH_URL, timeout=3).raise_for_status()
            return True
        except requests.RequestException:
            time.sleep(3.0)
    return False


def build_executor():
    from agent_core.calibrated.runtime import runtime_from_env
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    # AgentRunner's own startup step: configures the CalibratedRuntime from
    # RNADA_CAPGATE so every tool call lands in the platform audit trail
    # (advisory reviews, never blocks — see docstring).
    runtime_from_env()
    return ToolExecutor(build_default_tool_registry())


# ------------------------------------------------------------------ arm A/B

_EXECUTOR = None


def score_tool_layer(entry: dict[str, Any]) -> dict[str, Any]:
    """Arm A — the platform's production tool path (wrapper normalizes)."""
    global _EXECUTOR
    if _EXECUTOR is None:
        _EXECUTOR = build_executor()
    split = entry["split"]
    _, hints = SPLITS[split]
    seq_file = SCRATCH_DIR / split / f"{int(entry['key']):04d}.txt"
    seq_file.parent.mkdir(parents=True, exist_ok=True)
    seq_file.write_text(entry["rna_sequence"], encoding="utf-8")  # verbatim bytes
    started = time.monotonic()
    response: dict[str, Any] | None = None
    error: str | None = None
    try:
        res = _EXECUTOR.run_tool(
            TOOL,
            filepath=str(seq_file.relative_to(PROJECT_ROOT)),
            smiles=entry["smiles"],
            **hints,
        )
        if not res.success:
            raise RuntimeError(f"{TOOL} failed: {res.error}")
        raw = res.artifacts.get("result")
        if not isinstance(raw, dict) or raw.get("probability_positive") is None:
            raise RuntimeError(f"{TOOL} returned no probability_positive")
        response = raw
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"[:400]
    ok = response is not None
    record: dict[str, Any] = {
        "arm": "tool_layer",
        "split": split,
        "key": entry["key"],
        "label": entry["label"],
        "rna_len": len(entry["rna_sequence"]),
        "rna_has_lowercase": entry["rna_sequence"] != entry["rna_sequence"].upper(),
        "rna_truncated_at_500nt": len(entry["rna_sequence"]) > RNA_TRUNCATION_LENGTH,
        "elapsed_ms": round((time.monotonic() - started) * 1000.0, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "success": ok,
        "error": error,
    }
    if ok:
        record.update({
            "probability_positive": float(response["probability_positive"]),
            "predicted_label": int(response["predicted_label"]),
            "checkpoint": Path(response["checkpoint_path"]).name,
            "echoed_rna_sequence": response.get("rna_sequence"),
            "normalization_applied": (
                response.get("rna_sequence") != entry["rna_sequence"]),
        })
    return record


def score_service_endpoint(entry: dict[str, Any]) -> dict[str, Any]:
    """Arm B — case-preserving verbatim POST /score (exp7's protocol)."""
    import requests
    split = entry["split"]
    _, hints = SPLITS[split]
    payload: dict[str, Any] = {
        "rna_sequence": entry["rna_sequence"],
        "smiles": entry["smiles"],
        **hints,
    }
    started = time.monotonic()
    try:
        resp = requests.post(SERVICE_URL, json=payload, timeout=300)
        resp.raise_for_status()
        body = resp.json()
        return {
            "arm": "service_endpoint",
            "split": split,
            "key": entry["key"],
            "label": entry["label"],
            "rna_len": len(entry["rna_sequence"]),
            "rna_has_lowercase": entry["rna_sequence"] != entry["rna_sequence"].upper(),
            "rna_truncated_at_500nt": len(entry["rna_sequence"]) > RNA_TRUNCATION_LENGTH,
            "probability_positive": float(body["probability_positive"]),
            "predicted_label": int(body["predicted_label"]),
            "checkpoint": Path(body["checkpoint_path"]).name,
            "elapsed_ms": round((time.monotonic() - started) * 1000.0, 2),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "success": True,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "arm": "service_endpoint",
            "split": split,
            "key": entry["key"],
            "label": entry["label"],
            "rna_len": len(entry["rna_sequence"]),
            "rna_has_lowercase": entry["rna_sequence"] != entry["rna_sequence"].upper(),
            "rna_truncated_at_500nt": len(entry["rna_sequence"]) > RNA_TRUNCATION_LENGTH,
            "elapsed_ms": round((time.monotonic() - started) * 1000.0, 2),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "success": False,
            "error": f"{type(exc).__name__}: {exc}"[:400],
        }


def score_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [score_tool_layer(entry), score_service_endpoint(entry)]


# ------------------------------------------------------------------- records

def append_record(record: dict[str, Any]) -> None:
    RUNS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_records() -> dict[tuple[str, str, str], dict[str, Any]]:
    records: dict[tuple[str, str, str], dict[str, Any]] = {}
    if not RUNS_JSONL.exists():
        return records
    for line in RUNS_JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        records[(rec["arm"], rec["split"], rec["key"])] = rec  # later wins
    return records


# ---------------------------------------------------------------- statistics

def auroc(pos: list[float], neg: list[float]) -> float:
    """Rank-based AUROC (Mann–Whitney), ties get half credit."""
    import numpy as np
    from scipy.stats import rankdata
    allv = np.asarray(pos + neg, dtype=float)
    ranks = rankdata(allv)
    n_pos, n_neg = len(pos), len(neg)
    u = float(ranks[:n_pos].sum()) - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def bootstrap_auroc_ci(pos: list[float], neg: list[float]) -> dict[str, Any]:
    import numpy as np
    from scipy.stats import mannwhitneyu
    pos_a = np.asarray(pos, dtype=float)
    neg_a = np.asarray(neg, dtype=float)
    point = auroc(pos, neg)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot = np.empty(BOOTSTRAP_N)
    for b in range(BOOTSTRAP_N):
        bp = rng.choice(pos_a, size=len(pos_a), replace=True)
        bn = rng.choice(neg_a, size=len(neg_a), replace=True)
        boot[b] = auroc(bp.tolist(), bn.tolist())
    ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
    mw = mannwhitneyu(pos_a, neg_a, alternative="two-sided")
    return {
        "point_auroc": round(point, 4),
        "auroc_ci95": [round(ci[0], 4), round(ci[1], 4)],
        "mannwhitney_p_two_sided": float(mw.pvalue),
        "cliffs_delta": round(2 * point - 1, 4),
        "ci_includes_chance_0.5": bool(ci[0] <= 0.5 <= ci[1]),
    }


# ------------------------------------------------------------ cross-checks

def exp7_summary() -> dict[str, Any]:
    global _EXP7_SUMMARY
    if _EXP7_SUMMARY is None:
        path = EXP7_RESULTS / "summary.json"
        _EXP7_SUMMARY = json.loads(path.read_text(encoding="utf-8"))
    return _EXP7_SUMMARY


def cross_check_exp7(records: dict[tuple[str, str, str], dict[str, Any]]
                     ) -> dict[str, Any]:
    """Arm B vs the exp7 numbers of record: 4-decimal AUROC + per-pair |Δp|."""
    out: dict[str, Any] = {"available": bool(EXP7_RESULTS.joinpath("summary.json").exists()),
                           "splits": {}}
    if not out["available"]:
        return out
    exp7_runs = EXP7_RESULTS / "scoring_runs.jsonl"
    exp7_by_key: dict[str, dict[str, Any]] = {}
    if exp7_runs.exists():
        for line in exp7_runs.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("arm") in SPLITS and rec.get("success"):
                exp7_by_key[(rec["arm"], rec["key"])] = rec
    for split in SPLITS:
        ref = exp7_summary().get(split, {})
        diffs, matched = [], 0
        for (key_s, key), ref_rec in exp7_by_key.items():
            if key_s != split:
                continue
            mine = records.get(("service_endpoint", split, key))
            if mine is None or not mine.get("success"):
                continue
            diffs.append(abs(mine["probability_positive"]
                             - float(ref_rec["probability_positive"])))
            matched += 1
        block: dict[str, Any] = {
            "exp7_point_auroc": ref.get("point_auroc"),
            "exp7_ci95": ref.get("auroc_ci95"),
            "matched_pairs": matched,
            "expected_pairs": sum(1 for (s, _), r in exp7_by_key.items() if s == split),
        }
        if diffs:
            srt = sorted(diffs)
            n = len(srt)
            block.update({
                "max_abs_prob_delta": max(diffs),
                "median_abs_prob_delta": srt[n // 2] if n % 2
                    else 0.5 * (srt[n // 2 - 1] + srt[n // 2]),
                "n_over_1e-3": sum(1 for d in diffs if d > 1e-3),
            })
        out["splits"][split] = block
    out["note"] = (
        "Per-pair bit-identity is not expected across inference backends "
        "(exp7's registered amendment); the registered criterion is "
        "4-decimal AUROC agreement, checked in the verdict block."
    )
    return out


def cross_check_normalization(records: dict[tuple[str, str, str], dict[str, Any]],
                              entries_by_split: dict[str, list[dict[str, Any]]]
                              ) -> dict[str, Any]:
    """Arm A: echoed sequence == uppercase+T→U+strip of the verbatim source."""
    src_by_key = {s: {e["key"]: e["rna_sequence"] for e in lst}
                  for s, lst in entries_by_split.items()}
    checked = mismatches = normalized = 0
    for (arm, split, key), rec in records.items():
        if arm != "tool_layer" or not rec.get("success"):
            continue
        source = src_by_key.get(split, {}).get(key)
        echoed = rec.get("echoed_rna_sequence")
        if source is None or echoed is None:
            continue
        checked += 1
        if echoed != source:
            normalized += 1
        if echoed != expected_tool_normalization(source):
            mismatches += 1
    total_lower = sum(
        1 for lst in entries_by_split.values() for e in lst
        if e["rna_sequence"] != e["rna_sequence"].upper())
    return {
        "records_checked": checked,
        "echo_matches_expected_normalization": mismatches == 0,
        "normalization_mismatches": mismatches,
        "pairs_where_echo_differs_from_source": normalized,
        "pairs_with_lowercase_in_source": total_lower,
    }


def cross_check_checkpoints(records: dict[tuple[str, str, str], dict[str, Any]]
                            ) -> dict[str, Any]:
    """Checkpoint resolution must agree between arms for the same pair."""
    agree = disagree = 0
    per_split: dict[str, set[str]] = {}
    for split in SPLITS:
        for key in {k for (a, s, k) in records if s == split}:
            a = records.get(("tool_layer", split, key))
            b = records.get(("service_endpoint", split, key))
            if a and b and a.get("success") and b.get("success"):
                if a["checkpoint"] == b["checkpoint"]:
                    agree += 1
                else:
                    disagree += 1
        per_split[split] = sorted({
            r["checkpoint"] for (a, s, k), r in records.items()
            if s == split and a == "service_endpoint" and r.get("success")})
    return {"pairs_agree": agree, "pairs_disagree": disagree,
            "checkpoints_per_split": per_split}


# ------------------------------------------------------------------- summary

def write_summary() -> int:
    records = load_records()
    entries_by_split = {s: load_split(s) for s in SPLITS}

    summary: dict[str, Any] = {
        "experiment": "exp15_rnasmol_fidelity",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "protocol": {
            "instrument": "deployed RNAsmol microservice (microservices/rnasmol_service/start.sh, CPU default, port 8007) — both arms hit the same running service",
            "arm_A_tool_layer": "ToolExecutor.run_tool(score_rna_ligand_binding_with_rnasmol) — the platform production path; the tool wrapper uppercases + T→U-converts its input (the v0.2.0 defect class, live)",
            "arm_B_service_endpoint": "case-preserving verbatim POST /score (exp7's registered protocol)",
            "inputs": "the two official upstream held-out test splits, verbatim, source-file order",
            "checkpoint_hints": {s: h for s, (_, h) in SPLITS.items()},
            "capgate_policy": os.environ.get("RNADA_CAPGATE", "enforce"),
            "thresholds_or_tuning": "none — raw probability_positive throughout",
            "rna_truncation": f"service pads/truncates to {RNA_TRUNCATION_LENGTH} nt (platform default; counted per cell)",
            "statistics": f"stratified bootstrap {BOOTSTRAP_N} replicates, numpy default_rng seed {BOOTSTRAP_SEED}, percentile 95% CI",
        },
        "failures": [],
    }

    for arm in ARMS:
        for split in SPLITS:
            recs = [r for (a, s, _), r in sorted(records.items())
                    if a == arm and s == split]
            ok = [r for r in recs if r["success"]]
            bad = [r for r in recs if not r["success"]]
            summary["failures"].extend(
                {"arm": arm, "split": split, "key": r["key"], "error": r["error"]}
                for r in bad)
            block: dict[str, Any] = {
                "n_scored": len(ok),
                "n_failed": len(bad),
                "n_pos": sum(1 for r in ok if r["label"] == 1.0),
                "n_neg": sum(1 for r in ok if r["label"] == 0.0),
                "n_rna_over_500nt_truncated": sum(
                    1 for r in ok if r["rna_truncated_at_500nt"]),
                "n_source_with_lowercase": sum(
                    1 for r in ok if r.get("rna_has_lowercase")),
                "checkpoint": sorted({r["checkpoint"] for r in ok}),
            }
            pos = [r["probability_positive"] for r in ok if r["label"] == 1.0]
            neg = [r["probability_positive"] for r in ok if r["label"] == 0.0]
            if pos and neg:
                block.update(bootstrap_auroc_ci(pos, neg))
                block["auroc_gate_0.8_pass"] = block["point_auroc"] > 0.8
                if split == "pdb_test":  # ≤500-nt sensitivity subset (descriptive)
                    sub = [r for r in ok if not r["rna_truncated_at_500nt"]]
                    sp = [r["probability_positive"] for r in sub if r["label"] == 1.0]
                    sn = [r["probability_positive"] for r in sub if r["label"] == 0.0]
                    if sp and sn:
                        block["subset_le500nt"] = {"n": len(sub),
                                                   **bootstrap_auroc_ci(sp, sn)}
            summary[f"{arm}::{split}"] = block

    summary["cross_checks"] = {
        "armB_vs_exp7": cross_check_exp7(records),
        "armA_normalization": cross_check_normalization(records, entries_by_split),
        "checkpoint_agreement": cross_check_checkpoints(records),
    }

    def cell(arm: str, split: str) -> dict[str, Any]:
        return summary.get(f"{arm}::{split}", {})

    xc7 = summary["cross_checks"]["armB_vs_exp7"]
    repro_ok = all(
        cell("service_endpoint", s).get("point_auroc")
        == xc7["splits"].get(s, {}).get("exp7_point_auroc")
        for s in SPLITS
    ) if xc7.get("available") else None
    summary["verdict"] = {
        "armB_gate_0.8_both_splits": all(
            cell("service_endpoint", s).get("auroc_gate_0.8_pass") for s in SPLITS),
        "armA_below_gate_both_splits": all(
            not cell("tool_layer", s).get("auroc_gate_0.8_pass") for s in SPLITS),
        "armB_reproduces_exp7_4decimals": repro_ok,
        "armA_normalization_verified": summary["cross_checks"]["armA_normalization"]
            .get("echo_matches_expected_normalization"),
        "checkpoints_agree_across_arms": summary["cross_checks"]
            ["checkpoint_agreement"].get("pairs_disagree") == 0,
    }
    summary["verdict"]["defect_class_demonstrated"] = all(
        v is True for k, v in summary["verdict"].items() if k != "armA_below_gate_both_splits"
    ) and summary["verdict"]["armA_below_gate_both_splits"]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    for arm in ARMS:
        for split in SPLITS:
            b = cell(arm, split)
            if "point_auroc" in b:
                print(f"[{arm}::{split}] AUROC = {b['point_auroc']:.4f} "
                      f"(95% CI {b['auroc_ci95'][0]:.4f}-{b['auroc_ci95'][1]:.4f}); "
                      f"P = {b['mannwhitney_p_two_sided']:.3g}; n = {b['n_scored']} "
                      f"({b['n_pos']} pos / {b['n_neg']} neg; "
                      f"{b['n_rna_over_500nt_truncated']} truncated; "
                      f"{b['n_source_with_lowercase']} with lowercase)")
    xcn = summary["cross_checks"]["armA_normalization"]
    print(f"[armA normalization] checked {xcn['records_checked']}, "
          f"mismatches {xcn['normalization_mismatches']}, "
          f"echo differs from source on {xcn['pairs_where_echo_differs_from_source']} "
          f"(source lowercase on {xcn['pairs_with_lowercase_in_source']})")
    for split, c in xc7["splits"].items():
        print(f"[armB vs exp7 {split}] exp7 AUROC {c['exp7_point_auroc']}, "
              f"matched {c['matched_pairs']}/{c['expected_pairs']}, "
              f"max|Δp| = {c.get('max_abs_prob_delta')}")
    print(f"verdict: {summary['verdict']}")
    print(f"failures: {len(summary['failures'])}")
    return 0 if not summary["failures"] else 1


# ------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pilot", action="store_true",
                        help=f"first {PILOT_CSV_ROWS} rows of each split, both arms")
    parser.add_argument("--run", action="store_true",
                        help="score every pair of both splits in both arms")
    parser.add_argument("--summary", action="store_true",
                        help="compute AUROC / CI / cross-checks / verdict")
    parser.add_argument("--resume", action="store_true",
                        help="skip (arm, split, key) records already successful on disk")
    args = parser.parse_args()
    if not (args.pilot or args.run or args.summary):
        parser.error("choose --pilot, --run or --summary")
    if args.summary:
        return write_summary()

    if not ensure_service():
        print("[service] FAILED to bring up the RNAsmol service", file=sys.stderr)
        return 2

    todo: list[dict[str, Any]] = []
    for split in SPLITS:
        entries = load_split(split)
        if args.pilot:
            entries = entries[:PILOT_CSV_ROWS]
        todo.extend(entries)

    done = load_records() if args.resume else {}
    n_run = n_skip = 0
    for entry in todo:
        for rec in score_entry(entry):
            prior = done.get((rec["arm"], rec["split"], rec["key"]))
            if args.resume and prior is not None and prior.get("success"):
                n_skip += 1
                continue
            append_record(rec)
            n_run += 1
            flag = "OK" if rec["success"] else "FAIL"
            prob = rec.get("probability_positive")
            print(f"[{rec['arm']}::{rec['split']}] {rec['key']}: {flag} p={prob}"
                  + (f" err={rec['error']}" if rec["error"] else ""), flush=True)
    print(f"scored {n_run} pairs ({n_skip} skipped as already successful)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
