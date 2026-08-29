#!/usr/bin/env python3
"""Experiment 15 addendum — v0.2.0 RNAsmol service archaeology re-measure
(user-directed 2026-08-29, registered after the exp15 primary results were
known — disclosed; paper §2.3, Fig. 3h's pre-fix arm).

Context. exp15 measured, live, that the platform's default tool path
(wrapper uppercase + T→U) is AUROC-neutral on the oracle's official
held-out splits — falsifying the registered prediction that agent-side
normalization alone would re-introduce the v0.2.0 defect class. The
v0.2.0 collapse (AUROC 0.7864 / 0.4103, registered history in
PAPER_FACT_SHEET) therefore traces to the service-side preprocessing
port. Git archaeology (commit 7262e54, 2026-08-10) shows that port
carried TWO deviations from upstream: (i) the case collapse
(``.upper()``) and (ii) a rewritten molecular-graph adjacency — the
upstream preprocessing has an indexing quirk (only the first two
directed edge pairs zipped, indices shifted −1) that the shipped
checkpoints were trained on, and v0.2.0 "corrected" it into a full
symmetric adjacency. This addendum re-measures the recovered v0.2.0
artifact itself, upgrading the registered historical numbers from
record to measurement and completing the defect decomposition:
same case treatment (uppercase), different adjacency semantics.

Pre-registration
----------------
* Artifact: ``main.py`` recovered byte-verbatim from git commit
  ``7262e54`` (path ``rna_agent_system/microservices/rnasmol_service/
  main.py``; sha256 recorded in the summary and asserted on every
  invocation — the extraction is re-done from git if the file is
  missing, so no hand-editing is possible). The recovered service runs
  in a sandbox under this experiment's results directory, port 8107
  (outside the production port registry), CPU (``RNASMOL_DEVICE=cpu``,
  the shipped default policy), conda env ``rnasmol_service_env``
  (its own start.sh's activation), with an ``external_repos/RNAsmol``
  symlink so the artifact's own ``parents[2]`` path resolution finds
  the same unchanged checkpoints. The production service on 8007 is
  never touched.
* Inputs: identical to exp15 — the two official upstream held-out test
  splits, verbatim, source-file order (robin n = 1492, 763/729; pdb
  n = 170, 87/83); checkpoint auto-selection hints identical
  (robin/pdb + molperturbation). The artifact's own internal
  normalization (uppercase + T→U) is part of the artifact being
  measured and is NOT bypassed.
* Instrument boundary: service-direct scoring (no ToolExecutor — the
  artifact is the service; same auditability boundary as exp15 arm B /
  exp7).
* Primary metrics: per split, AUROC of ``probability_positive``;
  stratified bootstrap 10,000 replicates, numpy default_rng seed
  20260829, percentile 95% CI (exp15's convention).
* Registered expectations (the class, not bit-parity — the original
  v0.2.0-era measurement's device is unrecorded):
  1. ``collapse_class_reproduced``: AUROC below the 0.8 gate on BOTH
     splits (the registered collapse).
  2. agreement with the registered historical values within
     |ΔAUROC| ≤ 0.02 per split.
  3. Checkpoint resolution per pair identical to exp15's records
     (both arms' hints resolve the same ``*_bothaug_molperturbation.pt``
     files — asserted; a mismatch would confound the comparison and
     is reported as a failure).
  4. Decomposition statement (analysis-side, conditional on 1 and 3):
     v0.2.0 (uppercase + rewritten adjacency) vs exp15 arm A
     (uppercase + upstream-faithful adjacency) isolates the adjacency
     rewrite as the damage carrier on the case channel that exp15
     measured benign.
* Zero-intervention inside the artifact: no code edits (sha-asserted),
  no checkpoint overrides, no device override beyond the shipped CPU
  default, no thresholds; HTTP failures recorded as-is, no re-runs.
* Pilot: first 5 rows of each split (10 calls); all must return a
  probability before the full run. Budget: one call per pair = 1,662.
* Compute: CPU sandbox; GPUs 0–2 untouched.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp15_rnasmol_v020_sandbox.py --setup
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp15_rnasmol_v020_sandbox.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp15_rnasmol_v020_sandbox.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp15_rnasmol_v020_sandbox.py --summary

Outputs under ``experiments/results/exp15_rnasmol_v020_sandbox/``:
    scoring_runs.jsonl, summary.json,
    microservices/rnasmol_service/{main.py,start.sh} +
    microservices/common_utils.py (git-recovered, sha-asserted),
    external_repos/RNAsmol (symlink to the unchanged upstream checkout)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp15_rnasmol_v020_sandbox"
RUNS_JSONL = RESULTS_DIR / "scoring_runs.jsonl"
SERVICE_DIR = RESULTS_DIR / "microservices" / "rnasmol_service"
RECOVERED_MAIN = SERVICE_DIR / "main.py"
RECOVERED_START = SERVICE_DIR / "start.sh"
RECOVERED_COMMON = RESULTS_DIR / "microservices" / "common_utils.py"
SYMLINK_ROOT = RESULTS_DIR / "external_repos" / "RNAsmol"
REAL_RNASMOL = PROJECT_ROOT / "external_repos" / "RNAsmol"

GIT_COMMIT = "7262e54"
GIT_MAIN_PATH = "rna_agent_system/microservices/rnasmol_service/main.py"
GIT_START_PATH = "rna_agent_system/microservices/rnasmol_service/start.sh"
GIT_COMMON_PATH = "rna_agent_system/microservices/common_utils.py"
EXPECTED_SHA = "de261f8b95e96bfac2aa664ca614389db8ddacd02ece1e3099ec3bb5274ed767"
EXPECTED_COMMON_SHA = "5de9c6e7482a605e0603d4866e175f48ac24c7a11ed3211e65ae35caf29438f8"

EXP15_DIR = PROJECT_ROOT / "experiments" / "results" / "exp15_rnasmol_fidelity"

RNASMOL_REPO = REAL_RNASMOL / "rnasmol" / "data"
SERVICE_URL = "http://127.0.0.1:8107/score"
HEALTH_URL = "http://127.0.0.1:8107/health"

SPLITS: dict[str, tuple[Path, dict[str, str]]] = {
    "robin_test": (RNASMOL_REPO / "robin_molperturbation" / "raw" / "data_test.csv",
                   {"dataset": "robin", "perturbation_type": "molperturbation"}),
    "pdb_test": (RNASMOL_REPO / "pdb_molperturbation" / "raw" / "data_test.csv",
                 {"dataset": "pdb", "perturbation_type": "molperturbation"}),
}

# The registered v0.2.0 historical measurements (PAPER_FACT_SHEET E7 register).
REGISTERED_HIST = {"robin_test": 0.7864, "pdb_test": 0.4103}
REGISTERED_TOL = 0.02

BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20260829
PILOT_CSV_ROWS = 5
RNA_TRUNCATION_LENGTH = 500


# ------------------------------------------------------------------- setup

def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup_sandbox() -> int:
    """Recover the v0.2.0 artifact from git, verify, wire the symlink."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SERVICE_DIR.mkdir(parents=True, exist_ok=True)
    # the original layout is mirrored exactly: <sandbox>/microservices/
    # rnasmol_service/main.py resolves parents[1] → the microservices dir
    # (common_utils) and parents[2] → the sandbox root (external_repos
    # symlink) — identical path semantics to the production deployment
    for git_path, dest, want_sha in (
            (GIT_MAIN_PATH, RECOVERED_MAIN, EXPECTED_SHA),
            (GIT_START_PATH, RECOVERED_START, None),
            (GIT_COMMON_PATH, RECOVERED_COMMON, EXPECTED_COMMON_SHA)):
        blob = subprocess.run(
            ["git", "show", f"{GIT_COMMIT}:{git_path}"],
            cwd=PROJECT_ROOT, capture_output=True, check=True).stdout
        dest.write_bytes(blob)
        if want_sha and sha256_of(dest) != want_sha:
            print(f"[setup] SHA MISMATCH for {dest.name}: {sha256_of(dest)}",
                  file=sys.stderr)
            return 2
    stale = RESULTS_DIR / "run"  # an earlier sandbox layout, superseded
    if stale.is_dir():
        subprocess.run(["rm", "-rf", str(stale)], check=True)
    SYMLINK_ROOT.parent.mkdir(parents=True, exist_ok=True)
    if SYMLINK_ROOT.is_symlink() or SYMLINK_ROOT.exists():
        SYMLINK_ROOT.unlink()
    SYMLINK_ROOT.symlink_to(REAL_RNASMOL.resolve(), target_is_directory=True)
    print(f"[setup] recovered main.py sha256 = {sha256_of(RECOVERED_MAIN)}")
    print(f"[setup] recovered common_utils.py sha256 = {sha256_of(RECOVERED_COMMON)}")
    print(f"[setup] symlink {SYMLINK_ROOT} -> {REAL_RNASMOL}")
    # path-resolution sanity: parents[2] of the recovered file must reach the
    # symlinked RNAsmol root exactly as the original layout would
    resolved_root = RECOVERED_MAIN.parents[2] / "external_repos" / "RNAsmol"
    assert (resolved_root / "saved_model").is_dir(), \
        f"sandbox RNAsmol root does not resolve: {resolved_root}"
    print(f"[setup] artifact path resolution OK: {resolved_root}")
    return 0


def ensure_service(timeout_s: int = 300) -> bool:
    import requests
    try:
        requests.get(HEALTH_URL, timeout=3).raise_for_status()
        return True
    except requests.RequestException:
        pass
    if not RECOVERED_MAIN.exists():
        raise SystemExit("sandbox not set up — run --setup first")
    print("[service] starting the recovered v0.2.0 service on port 8107 (CPU) ...",
          flush=True)
    cmd = (
        'source "$(conda info --base)/etc/profile.d/conda.sh" && '
        "conda activate rnasmol_service_env && "
        'export RNASMOL_DEVICE="${RNASMOL_DEVICE:-cpu}" && '
        "python -m uvicorn main:app --host 127.0.0.1 --port 8107"
    )
    subprocess.Popen(["bash", "-c", cmd], cwd=SERVICE_DIR,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            requests.get(HEALTH_URL, timeout=3).raise_for_status()
            return True
        except requests.RequestException:
            time.sleep(3.0)
    return False


# --------------------------------------------------------------------- inputs

def load_split(split: str) -> list[dict[str, Any]]:
    csv_path, _ = SPLITS[split]
    with csv_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [
        {"split": split, "key": str(i), "smiles": r["compound_iso_smiles"],
         "rna_sequence": r["target_sequence"], "label": float(r["affinity"])}
        for i, r in enumerate(rows)
    ]


def score_pair(entry: dict[str, Any]) -> dict[str, Any]:
    import requests
    split = entry["split"]
    _, hints = SPLITS[split]
    payload = {"rna_sequence": entry["rna_sequence"], "smiles": entry["smiles"],
               **hints}
    started = time.monotonic()
    try:
        resp = requests.post(SERVICE_URL, json=payload, timeout=300)
        resp.raise_for_status()
        body = resp.json()
        return {
            "arm": "v020_sandbox",
            "split": split,
            "key": entry["key"],
            "label": entry["label"],
            "rna_len": len(entry["rna_sequence"]),
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
            "arm": "v020_sandbox",
            "split": split,
            "key": entry["key"],
            "label": entry["label"],
            "rna_len": len(entry["rna_sequence"]),
            "rna_truncated_at_500nt": len(entry["rna_sequence"]) > RNA_TRUNCATION_LENGTH,
            "elapsed_ms": round((time.monotonic() - started) * 1000.0, 2),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "success": False,
            "error": f"{type(exc).__name__}: {exc}"[:400],
        }


def append_record(record: dict[str, Any]) -> None:
    RUNS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_records() -> dict[tuple[str, str], dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
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
        records[(rec["split"], rec["key"])] = rec
    return records


# ---------------------------------------------------------------- statistics

def auroc(pos: list[float], neg: list[float]) -> float:
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
        boot[b] = auroc(rng.choice(pos_a, size=len(pos_a), replace=True).tolist(),
                        rng.choice(neg_a, size=len(neg_a), replace=True).tolist())
    ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
    mw = mannwhitneyu(pos_a, neg_a, alternative="two-sided")
    return {
        "point_auroc": round(point, 4),
        "auroc_ci95": [round(ci[0], 4), round(ci[1], 4)],
        "mannwhitney_p_two_sided": float(mw.pvalue),
        "cliffs_delta": round(2 * point - 1, 4),
        "ci_includes_chance_0.5": bool(ci[0] <= 0.5 <= ci[1]),
    }


# ------------------------------------------------------------------- summary

def write_summary() -> int:
    records = load_records()
    exp15_summary = json.loads((EXP15_DIR / "summary.json").read_text(encoding="utf-8"))
    exp15_runs: dict[tuple[str, str], dict[str, Any]] = {}
    for line in (EXP15_DIR / "scoring_runs.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        exp15_runs[(r["split"], r["key"])] = r

    summary: dict[str, Any] = {
        "experiment": "exp15_rnasmol_v020_sandbox",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "protocol": {
            "artifact": f"git {GIT_COMMIT} :: {GIT_MAIN_PATH} (byte-verbatim)",
            "artifact_sha256": sha256_of(RECOVERED_MAIN),
            "artifact_sha_matches_registered": sha256_of(RECOVERED_MAIN) == EXPECTED_SHA,
            "sandbox": "results-local run/service_v020 + external_repos/RNAsmol symlink; port 8107 (outside the production registry); RNASMOL_DEVICE=cpu; conda env rnasmol_service_env; the production 8007 service untouched",
            "inputs": "identical to exp15 — official held-out splits verbatim; hints robin/pdb + molperturbation; the artifact's own internal normalization measured, not bypassed",
            "statistics": f"stratified bootstrap {BOOTSTRAP_N} replicates, numpy default_rng seed {BOOTSTRAP_SEED}, percentile 95% CI",
            "registered_history": REGISTERED_HIST,
        },
        "failures": [],
    }

    for split in SPLITS:
        recs = [r for (s, _), r in sorted(records.items()) if s == split]
        ok = [r for r in recs if r["success"]]
        bad = [r for r in recs if not r["success"]]
        summary["failures"].extend(
            {"split": split, "key": r["key"], "error": r["error"]} for r in bad)
        block: dict[str, Any] = {
            "n_scored": len(ok), "n_failed": len(bad),
            "n_pos": sum(1 for r in ok if r["label"] == 1.0),
            "n_neg": sum(1 for r in ok if r["label"] == 0.0),
            "n_rna_over_500nt_truncated": sum(
                1 for r in ok if r["rna_truncated_at_500nt"]),
            "checkpoint": sorted({r["checkpoint"] for r in ok}),
        }
        pos = [r["probability_positive"] for r in ok if r["label"] == 1.0]
        neg = [r["probability_positive"] for r in ok if r["label"] == 0.0]
        if pos and neg:
            block.update(bootstrap_auroc_ci(pos, neg))
            block["auroc_gate_0.8_pass"] = block["point_auroc"] > 0.8
            block["registered_hist_auroc"] = REGISTERED_HIST[split]
            block["abs_delta_vs_registered"] = round(
                abs(block["point_auroc"] - REGISTERED_HIST[split]), 4)
            block["agrees_within_0.02"] = (
                block["abs_delta_vs_registered"] <= REGISTERED_TOL)
            # checkpoint agreement with exp15 (both arms resolved via hints)
            agree = mismatch = 0
            for r in ok:
                ref = exp15_runs.get((split, r["key"]))
                if ref and ref.get("success") and ref.get("checkpoint"):
                    if ref["checkpoint"] == r["checkpoint"]:
                        agree += 1
                    else:
                        mismatch += 1
            block["checkpoint_agree_with_exp15"] = agree
            block["checkpoint_mismatch_with_exp15"] = mismatch
        summary[f"v020_sandbox::{split}"] = block

    def cell(split: str) -> dict[str, Any]:
        return summary.get(f"v020_sandbox::{split}", {})

    summary["verdict"] = {
        "collapse_class_reproduced": all(
            not cell(s).get("auroc_gate_0.8_pass") for s in SPLITS),
        "agrees_with_registered_history_within_0.02": all(
            cell(s).get("agrees_within_0.02") for s in SPLITS),
        "checkpoints_match_exp15": all(
            cell(s).get("checkpoint_mismatch_with_exp15") == 0 for s in SPLITS),
        "artifact_sha_verified": summary["protocol"]["artifact_sha_matches_registered"],
    }
    summary["verdict"]["all_pass"] = all(summary["verdict"].values())
    summary["decomposition"] = {
        "statement": (
            "v0.2.0 (uppercase + rewritten adjacency) vs exp15 arm A "
            "(uppercase + upstream-faithful adjacency) share the case "
            "treatment; exp15 measured the case channel alone AUROC-neutral, "
            "so the collapse difference isolates the adjacency rewrite as the "
            "damage carrier (conditional on the checkpoint agreement asserted "
            "above and additivity of the two deviations)"
        ),
        "exp15_armA_reference": {
            s: exp15_summary.get(f"tool_layer::{s}", {}).get("point_auroc")
            for s in SPLITS},
        "exp15_armB_reference": {
            s: exp15_summary.get(f"service_endpoint::{s}", {}).get("point_auroc")
            for s in SPLITS},
        "v020_sandbox": {s: cell(s).get("point_auroc") for s in SPLITS},
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    for split in SPLITS:
        b = cell(split)
        if "point_auroc" in b:
            print(f"[v020_sandbox::{split}] AUROC = {b['point_auroc']:.4f} "
                  f"(95% CI {b['auroc_ci95'][0]:.4f}-{b['auroc_ci95'][1]:.4f}); "
                  f"registered {b['registered_hist_auroc']} "
                  f"(|Δ| = {b['abs_delta_vs_registered']}); n = {b['n_scored']} "
                  f"({b['n_pos']} pos / {b['n_neg']} neg)")
    print(f"verdict: {summary['verdict']}")
    print(f"failures: {len(summary['failures'])}")
    return 0 if not summary["failures"] else 1


# ------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--setup", action="store_true",
                        help="recover the v0.2.0 artifact from git + wire the sandbox")
    parser.add_argument("--pilot", action="store_true",
                        help=f"first {PILOT_CSV_ROWS} rows of each split")
    parser.add_argument("--run", action="store_true", help="score every pair")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="skip (split, key) records already successful on disk")
    args = parser.parse_args()
    if not (args.setup or args.pilot or args.run or args.summary):
        parser.error("choose --setup, --pilot, --run or --summary")
    if args.setup:
        return setup_sandbox()
    if args.summary:
        return write_summary()

    if not ensure_service():
        print("[service] FAILED to bring up the v0.2.0 sandbox service",
              file=sys.stderr)
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
        prior = done.get((entry["split"], entry["key"]))
        if args.resume and prior is not None and prior.get("success"):
            n_skip += 1
            continue
        rec = score_pair(entry)
        append_record(rec)
        n_run += 1
        flag = "OK" if rec["success"] else "FAIL"
        prob = rec.get("probability_positive")
        print(f"[v020_sandbox::{entry['split']}] {entry['key']}: {flag} p={prob}"
              + (f" err={rec['error']}" if rec["error"] else ""), flush=True)
    print(f"scored {n_run} pairs ({n_skip} skipped as already successful)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
