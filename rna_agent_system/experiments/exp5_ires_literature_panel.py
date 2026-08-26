#!/usr/bin/env python3
"""Experiment 5 (paper §2.2, Fig. 2e): IRES literature-panel prediction —
threshold-free ROC/AUROC of the ``ires_prediction`` workflow.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2)
-----------------------------------------------------
* Panel (fixed before any run; user-approved expansion 2026-08-25):
  positives = all 9 entries of ``data/benchmarks/external_anchors/ires/
  ires_positive.fa`` (6 viral IRES 5′UTRs — EMCV, HCV, poliovirus, FMDV,
  HRV-A1, BVDV-1 — covering picornavirus types I/II and the pestivirus
  HCV-like class, plus 3 cellular IRES 5′UTRs — c-myc, VEGF-A, Bip/GRP78;
  provenance in the anchor ``SOURCES.md``); negatives = all 50 entries of
  ``utr_negative.fa`` (random human 5′-terminal 200-nt windows, GENCODE v46,
  seed 0). n = 59, no sequence excluded.
* Protocol — no platform intervention: every sequence goes through the
  platform's ``ires_prediction`` workflow (form-driven CLI, full generate →
  evaluate → score → rank path with structural validation at defaults).
  The ONLY parameter set differently from the workflow defaults is
  ``probability_threshold=0.0``: the threshold is a labelling knob (the
  service computes every fragment's probability regardless), and 0.0 merely
  disables the label filter so the raw probability reaches the workflow's
  scoring/ranking layer for below-default-threshold sequences. One fixed
  setting for all 59 sequences, chosen before the pilot, never tuned. Mode,
  window, step, top_n and structural validation are left at their defaults
  (mode 0 = full-sequence scoring).
* Primary metric: AUROC of the workflow's ``best_candidate`` IRESfinder
  probability (``scores.ires_probability``; with mode 0 this is the
  whole-sequence model probability) — 9 positives vs 50 negatives.
* Statistics: stratified bootstrap over sequences (resample positives and
  negatives with replacement), 10,000 replicates, ``numpy`` default_rng seed
  20260825; reported 95% percentile CI for AUROC and a pointwise 95% TPR
  band on an FPR grid (0:0.02:1) for the ROC curve. Two-sided Mann–Whitney P
  reported alongside (AUROC is the effect size; Cliff's δ = 2·AUROC − 1).
* Historical reference only, not a gate: the legacy 3-positive panel scored
  AUROC 0.762 (CI 0.43–0.98). This run re-derives every number on the
  expanded panel.
* Addendum arm (registered 2026-08-25 AFTER the mode-0 primary result was
  known — disclosed post-hoc, never substituted for the primary): mode-2
  sliding-window scanning (``iresfinder_mode=2``; window 174 / step 50 left
  at defaults — the upstream scanning regime and the path used by the
  Platform's mode-2 IRES tasks). Rationale: mode 0 scores the whole sequence
  with k-mer features, so 341–1058-nt viral 5′UTRs sit far outside the
  model's ~174-nt window regime while the 200-nt negatives sit inside it —
  a length confound the scanning mode removes. Same protocol otherwise
  (threshold 0.0, all defaults, one run per sequence); recorded in
  ``panel_runs_mode2.jsonl`` and reported as a separate arm.
* Re-registration (2026-08-26, user direction): **the mode-2 scanning arm is
  the Fig 2e figure endpoint** — it is the legacy panel's protocol (legacy
  per-sequence scores match this arm exactly) and the oracle's native window
  regime. The mode-0 default-path result stays the pre-registered primary
  analysis record and renders as the archived variant
  ``fig2e_ires_roc_mode0.*``; no scores were recomputed.
* Go/no-go: pilot = first 3 positives + first 3 negatives must all complete
  with a recorded raw score before the full panel runs. Full-panel scoring
  failures are reported as-is (no re-runs, no exclusions).
* CapGate policy: ``RNADA_CAPGATE=advisory`` (the documented regression
  convention; the IRESfinder oracle is enforce-gated by registered design,
  E16–E18 / DECISIONS (j)/(l)).
* Compute: the ``ires_prediction`` service chain (IRESfinder log-reg,
  LinearFold/ViennaRNA, RNAplfold, unpaired-fraction) is CPU-only — no GPU
  allocation (GPUs 0–2 remain free for the platform's GPU services).
* Budget: one workflow run per sequence; ``--resume`` skips records already
  successful on disk.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp5_ires_literature_panel.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp5_ires_literature_panel.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp5_ires_literature_panel.py --summary

Outputs under ``experiments/results/exp5_ires_panel/``:
    inputs/*.fa, panel_runs.jsonl, summary.json, roc_points.csv
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ANCHORS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "ires"
POS_FASTA = ANCHORS_DIR / "ires_positive.fa"
NEG_FASTA = ANCHORS_DIR / "utr_negative.fa"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp5_ires_panel"
INPUTS_DIR = RESULTS_DIR / "inputs"
RUNS_JSONL = RESULTS_DIR / "panel_runs.jsonl"
RUNS_JSONL_MODE2 = RESULTS_DIR / "panel_runs_mode2.jsonl"

BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20260825
FPR_GRID_STEP = 0.02
PILOT_POS, PILOT_NEG = 3, 3
PER_SEQUENCE_TIMEOUT_S = 900


# --------------------------------------------------------------------- inputs

def parse_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(chunks)))
            header, chunks = line[1:], []
        else:
            chunks.append(line)
    if header is not None:
        records.append((header, "".join(chunks)))
    return records


def slugify(header: str, role: str, index: int) -> str:
    name = header.split("|")[0].strip().lower()
    name = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
    return f"{role}_{index:02d}_{name}"


def stage_panel(only_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Write one single-record FASTA per panel sequence; return the manifest."""
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    for role, fasta in (("pos", POS_FASTA), ("neg", NEG_FASTA)):
        for i, (header, seq) in enumerate(parse_fasta(fasta)):
            pid = slugify(header, role, i)
            if only_ids is not None and pid not in only_ids:
                continue
            fp = INPUTS_DIR / f"{pid}.fa"
            if not fp.exists():
                fp.write_text(f">{pid} {header}\n{seq}\n", encoding="utf-8")
            manifest.append({
                "panel_id": pid,
                "label": 1 if role == "pos" else 0,
                "length_nt": len(seq),
                "fasta_header": header,
                "input_filepath": str(fp.relative_to(PROJECT_ROOT)),
            })
    return manifest


# ------------------------------------------------------------------- runs

def run_cli(
    params: dict[str, Any],
    *,
    session_id: str,
    timeout: int,
    capgate: str,
) -> tuple[dict[str, Any] | None, int, float, str | None]:
    """One form-driven CLI run; returns (workflow_results, exit_code, elapsed, error)."""
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    params_file = session_dir / "params.json"
    params_file.write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    env["RNADA_CAPGATE"] = capgate

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "cli" / "form_chat.py"),
        "--workflow", "ires_prediction",
        "--params-file", str(params_file),
        "--session-id", session_id,
    ]
    log_path = session_dir / "driver.log"
    started = time.monotonic()
    exit_code, error = -1, None
    with log_path.open("w", encoding="utf-8", errors="replace") as log_fp:
        try:
            proc = subprocess.run(
                cmd, cwd=PROJECT_ROOT, env=env,
                stdout=log_fp, stderr=subprocess.STDOUT,
                input="y\n", text=True, timeout=timeout,  # auto-answer pre-flight prompt
            )
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            error = "timeout"
    elapsed = time.monotonic() - started

    results = None
    results_file = None
    candidates = sorted(
        session_dir.glob("workflow_results_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    if candidates:
        results_file = candidates[-1]
    if error is None and exit_code != 0:
        error = "cli_failure"
    if error is None and results_file is None:
        error = "no_results_file"
    if results_file is not None:
        try:
            results = json.loads(results_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            error = error or "parse_error"
    if error is None and results is not None and not results.get("success"):
        error = "workflow_success_false"
    return results, exit_code, elapsed, error


def extract_raw_score(results: dict[str, Any]) -> tuple[float | None, str]:
    """Pull the raw IRESfinder probability out of the workflow result."""
    best = results.get("best_candidate") or {}
    scores = best.get("scores") or {}
    for key, where in (
        (scores.get("ires_probability"), "best_candidate.scores.ires_probability"),
        ((best.get("metadata") or {}).get("ires_probability"), "best_candidate.metadata.ires_probability"),
        (scores.get("composite_score"), "best_candidate.scores.composite_score"),
    ):
        if isinstance(key, (int, float)):
            return float(key), where
    return None, "missing"


def score_one(entry: dict[str, Any], *, capgate: str, arm: str = "mode0",
              out_path: Path = RUNS_JSONL,
              lock: "threading.Lock | None" = None) -> dict[str, Any]:
    pid = entry["panel_id"]
    params = {
        "sequence_filepath": entry["input_filepath"],
        # Sole pre-registered deviation from defaults (see docstring): disable
        # the labelling filter so raw probabilities flow to the score layer.
        "probability_threshold": 0.0,
    }
    if arm == "mode2":
        params["iresfinder_mode"] = 2  # window 174 / step 50 stay at defaults
    session_id = f"exp5{'m2' if arm == 'mode2' else ''}_{pid}"
    print(f"[{arm}] {pid} (len {entry['length_nt']}, label {entry['label']}) ...", flush=True)
    results, exit_code, elapsed, error = run_cli(
        params, session_id=session_id,
        timeout=PER_SEQUENCE_TIMEOUT_S, capgate=capgate,
    )
    record: dict[str, Any] = {
        "arm": arm,
        "panel_id": pid,
        "label": entry["label"],
        "length_nt": entry["length_nt"],
        "fasta_header": entry["fasta_header"],
        "session_id": session_id,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error,
        "success": False,
    }
    if results is not None:
        record["workflow_success"] = bool(results.get("success"))
        raw, where = extract_raw_score(results)
        record["raw_score"] = raw
        record["raw_score_field"] = where
        if raw is not None:
            record["success"] = True
    if lock is not None:
        with lock:
            append_record(out_path, record)
    else:
        append_record(out_path, record)
    print(f"      -> {'OK' if record['success'] else 'FAIL'} "
          f"score={record.get('raw_score')} err={error}", flush=True)
    return record


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def load_successful_ids(path: Path = RUNS_JSONL) -> set[str]:
    done: set[str] = set()
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("success"):
            done.add(rec["panel_id"])
    return done


# ---------------------------------------------------------------- statistics

def auroc(scores_pos: list[float], scores_neg: list[float]) -> float:
    """Rank-based AUROC (Mann–Whitney), ties get half credit."""
    import numpy as np
    from scipy.stats import rankdata
    allv = np.asarray(scores_pos + scores_neg, dtype=float)
    ranks = rankdata(allv)
    n_pos, n_neg = len(scores_pos), len(scores_neg)
    rank_sum_pos = float(ranks[:n_pos].sum())
    u = rank_sum_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def roc_curve_points(scores: list[float], labels: list[float]) -> list[tuple[float, float]]:
    """ROC points (fpr, tpr), thresholds descending, starting at (0, 0)."""
    import numpy as np
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=float)
    order = np.argsort(-s, kind="mergesort")
    s, y = s[order], y[order]
    tps = np.cumsum(y == 1)
    fps = np.cumsum(y == 0)
    tpr = np.concatenate([[0.0], tps]) / max((y == 1).sum(), 1)
    fpr = np.concatenate([[0.0], fps]) / max((y == 0).sum(), 1)
    return [(float(f), float(t)) for f, t in zip(fpr, tpr)]


def bootstrap_summary(scores: list[float], labels: list[int]) -> dict[str, Any]:
    import numpy as np
    pos = np.array([s for s, y in zip(scores, labels) if y == 1], dtype=float)
    neg = np.array([s for s, y in zip(scores, labels) if y == 0], dtype=float)
    point = auroc(pos.tolist(), neg.tolist())

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    grid = np.round(np.arange(0.0, 1.0 + 1e-9, FPR_GRID_STEP), 4)
    boot_aurocs = np.empty(BOOTSTRAP_N)
    boot_tpr = np.full((BOOTSTRAP_N, len(grid)), np.nan)
    for b in range(BOOTSTRAP_N):
        bp = rng.choice(pos, size=len(pos), replace=True)
        bn = rng.choice(neg, size=len(neg), replace=True)
        boot_aurocs[b] = auroc(bp.tolist(), bn.tolist())
        pts = roc_curve_points(np.concatenate([bp, bn]).tolist(),
                               [1] * len(bp) + [0] * len(bn))
        fprs = np.array([p[0] for p in pts])
        tprs = np.array([p[1] for p in pts])
        boot_tpr[b] = np.interp(grid, fprs, tprs, left=0.0, right=tprs[-1])

    ci = (float(np.percentile(boot_aurocs, 2.5)),
          float(np.percentile(boot_aurocs, 97.5)))
    band_lo = np.nanpercentile(boot_tpr, 2.5, axis=0)
    band_hi = np.nanpercentile(boot_tpr, 97.5, axis=0)
    return {
        "point_auroc": point,
        "auroc_ci95": [round(ci[0], 4), round(ci[1], 4)],
        "roc_fpr_grid": [float(g) for g in grid],
        "roc_band_tpr_lo": [round(float(v), 4) for v in band_lo],
        "roc_band_tpr_hi": [round(float(v), 4) for v in band_hi],
    }


def write_summary() -> int:
    from scipy.stats import mannwhitneyu
    arms: dict[str, dict[str, dict[str, Any]]] = {}
    failures: list[dict[str, Any]] = []
    for arm, path in (("mode0", RUNS_JSONL), ("mode2", RUNS_JSONL_MODE2)):
        if not path.exists():
            continue
        records: dict[str, dict[str, Any]] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            # later lines (failed retries) supersede earlier ones
            records[rec["panel_id"]] = rec
        arms[arm] = records
        failures.extend(
            {"arm": arm, "panel_id": r["panel_id"], "error": r.get("error"),
             "exit_code": r.get("exit_code")}
            for r in records.values() if not r.get("success")
        )

    summary: dict[str, Any] = {
        "experiment": "exp5_ires_literature_panel",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "panel": {
            "positives_planned": 9,
            "negatives_planned": 50,
            "failures": failures,
        },
        "protocol": {
            "workflow": "ires_prediction",
            "mode0": {"mode": 0, "probability_threshold": 0.0,
                      "role": "pre-registered primary"},
            "mode2": {"mode": 2, "window_size": 174, "step_size": 50,
                      "probability_threshold": 0.0,
                      "role": "addendum arm (registered after the mode-0 "
                              "result was known; disclosed post-hoc)"},
            "note": "defaults except the labelling threshold disabled to expose raw scores (pre-registered)",
            "capgate": "advisory",
        },
    }
    any_results = False
    for arm, records in arms.items():
        scored = [r for r in records.values() if r.get("success")]
        scores = [float(r["raw_score"]) for r in scored]
        labels = [int(r["label"]) for r in scored]
        pos = [s for s, y in zip(scores, labels) if y == 1]
        neg = [s for s, y in zip(scores, labels) if y == 0]
        summary["panel"].setdefault(f"positives_scored_{arm}", len(pos))
        summary["panel"].setdefault(f"negatives_scored_{arm}", len(neg))
        if not pos or not neg:
            continue
        any_results = True
        boot = bootstrap_summary(scores, labels)
        mw = mannwhitneyu(pos, neg, alternative="two-sided")
        point_roc = roc_curve_points(scores, labels)
        summary[f"results_{arm}"] = {
            **boot,
            "mannwhitney_p_two_sided": float(mw.pvalue),
            "cliffs_delta": round(2 * boot["point_auroc"] - 1, 4),
            "score_range_pos": [min(pos), max(pos)],
            "score_range_neg": [min(neg), max(neg)],
            "roc_points": [[round(f, 4), round(t, 4)] for f, t in point_roc],
            "per_sequence": [
                {"panel_id": r["panel_id"], "label": r["label"],
                 "score": float(r["raw_score"]), "length_nt": r["length_nt"],
                 "fasta_header": r["fasta_header"]}
                for r in sorted(scored, key=lambda r: (-float(r["raw_score"]), r["panel_id"]))
            ],
        }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    rc = 0
    for arm in ("mode0", "mode2"):
        res = summary.get(f"results_{arm}")
        if not res:
            continue
        npos = summary["panel"][f"positives_scored_{arm}"]
        nneg = summary["panel"][f"negatives_scored_{arm}"]
        print(f"[{arm}] AUROC = {res['point_auroc']:.3f} "
              f"(95% CI {res['auroc_ci95'][0]:.3f}-{res['auroc_ci95'][1]:.3f}); "
              f"Mann-Whitney P = {res['mannwhitney_p_two_sided']:.3g}; "
              f"n = {npos} pos / {nneg} neg")
        with (RESULTS_DIR / f"roc_points_{arm}.csv").open("w", encoding="utf-8") as fh:
            fh.write("fpr,tpr,band_lo,band_hi\n")
            grid = res["roc_fpr_grid"]
            lo, hi = res["roc_band_tpr_lo"], res["roc_band_tpr_hi"]
            roc = dict((f, t) for f, t in res["roc_points"])
            for g, l, h in zip(grid, lo, hi):
                t = roc.get(g)
                if t is None:  # snap grid fpr to the nearest measured point
                    t = min(res["roc_points"], key=lambda p: abs(p[0] - g))[1]
                fh.write(f"{g:.4f},{t:.4f},{l:.4f},{h:.4f}\n")
    if not any_results:
        print("No scored sequences yet — run --pilot / --run first.")
        rc = 1
    if failures:
        print(f"failures: {len(failures)}")
        rc = rc or 1
    return rc


# ------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pilot", action="store_true",
                        help=f"run the first {PILOT_POS} positives + {PILOT_NEG} negatives")
    parser.add_argument("--run", action="store_true", help="run the full panel")
    parser.add_argument("--summary", action="store_true", help="compute AUROC / CI / ROC band")
    parser.add_argument("--resume", action="store_true", help="skip already-successful records")
    parser.add_argument("--arm", default="mode0", choices=["mode0", "mode2"],
                        help="scoring arm: pre-registered mode-0 primary (default) "
                             "or the disclosed mode-2 scanning addendum")
    parser.add_argument("--workers", type=int, default=1,
                        help="concurrent CLI subprocesses (default 1)")
    parser.add_argument("--capgate", default="advisory", choices=["advisory", "enforce"])
    args = parser.parse_args()

    if not (args.pilot or args.run or args.summary):
        parser.error("choose --pilot, --run or --summary")

    if args.summary:
        return write_summary()

    out_path = RUNS_JSONL if args.arm == "mode0" else RUNS_JSONL_MODE2
    manifest = stage_panel()
    done = load_successful_ids(out_path) if args.resume else set()
    if args.pilot:
        pos_ids = [e["panel_id"] for e in manifest if e["label"] == 1][:PILOT_POS]
        neg_ids = [e["panel_id"] for e in manifest if e["label"] == 0][:PILOT_NEG]
        manifest = [e for e in manifest if e["panel_id"] in set(pos_ids + neg_ids)]
    todo = [e for e in manifest if not (args.resume and e["panel_id"] in done)]
    for entry in [e for e in manifest if args.resume and e["panel_id"] in done]:
        print(f"[skip] {entry['panel_id']} (already successful)")
    if args.workers <= 1:
        for entry in todo:
            score_one(entry, capgate=args.capgate, arm=args.arm, out_path=out_path)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        lock = threading.Lock()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(score_one, entry, capgate=args.capgate,
                            arm=args.arm, out_path=out_path, lock=lock)
                for entry in todo
            ]
            for fut in as_completed(futures):
                fut.result()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
