#!/usr/bin/env python
"""P2: junction-integrated LinearDesign optimizer — pre-registered GO/NO-GO evaluation.

Date: 2026-08-04. Follows the P1 v2 NO-GO (results/p1_v2_stability_sweep_summary.json):
post-hoc terminal-window proxies cannot control global stability, so the junction
term was moved INSIDE the generative tool (LinearDesign C++ JUNCTION-PATCH,
2026-08; microservice endpoint ``POST /generate/cds_junction_aware`` on port 8014).
This driver evaluates the integrated optimizer against the P1 serial baselines.

Pre-registered acceptance criteria (this docstring is the registration):
  1. Hard repair rate >= 2/3: of the hard-target cells whose baseline CDS has a
     buried AUG/Kozak context (P1 baseline: 7 hard-buried cells out of 9), the
     fraction whose designed CDS is no longer buried (JunctionFolder
     ``aug_buried``/``kozak_buried`` both False, same metrics as P1; baseline
     uses the shard keys junction_5utr_cds_aug_buried/kozak_buried) must be
     >= 2/3, for at least one w_jun.
  2. Median stability cost <= 0.011 kcal/mol/nt (= 0.5 x P1 v1 median
     0.021996110355454235). Cost per cell = designed full-construct mfe/nt minus
     baseline full-construct mfe/nt (both LinearFold folds of
     utr5 + CDS + utr3; positive = less stable = cost). Median over all 18 cells
     of the weight.
  3. Median CAI drop <= 0.02: baseline cds_cai minus designed cds_cai, median
     over all 18 cells of the weight.
  GO if at least one w_jun satisfies ALL three; otherwise NO-GO (report as-is).

Design matrix: 6 targets (hard: HER2, Beta_galactosidase, Influenza_HA_H1N1;
easy: Insulin, EPO, Growth_hormone) x 3 reps x w_jun in {0, 0.5, 1.0, 2.0}
= 72 cells. Seeds reuse the P1 serial sessions
``workspace/sessions/fig3t1_t1_<target>_r0_rep<k>`` via ``load_serial_seed``;
lambda_value is read from each session's params.json (all 2.0 at registration
time); the workflow default would be recorded if absent. Protein input is the
translation of the baseline CDS (cross-checked against session params.json).
UTR inputs are the task UTRs; the endpoint slices the junction-side 21 nt per
side (flank_nt=21) and folds them as fixed pseudo-codon flanks.

Degenerate arm (w_jun = 0) — pre-registered caveat: with flanks present, the
patched binary still folds the 21-nt pseudo-codon flanks (argc == 8 path), so
the w_jun=0 arm is NOT byte-guaranteed to equal the legacy no-flank endpoint.
Therefore the degenerate assertion is DETERMINISM: two independent w_jun=0
calls with identical payloads must return byte-identical CDSs (checked on
(Insulin, rep0)); any difference vs the legacy no-flank ``/generate/cds``
endpoint is recorded as an informational metric only.

Outputs:
  - results/junction_integrated_optimizer.jsonl (one row per cell)
  - results/junction_integrated_optimizer_summary.json (criteria, per-weight
    summary, decision, mechanism notes: w_jun responsiveness = fraction of
    (target, rep) groups whose designed CDSs differ across weights;
    junction_window_pair_count distribution per weight; stability cost spread;
    determinism + legacy-comparison probes)
  - results/MODEL_API_USAGE.md row (added manually after the run): no LLM
    calls; local services 8014 + 8015, zero GPU.

Services: 8014 (patched LinearDesign) and 8015 (LinearFold) are pre-flighted
and auto-started via ``ensure_services_ready`` — no manual launcher needed.

Runbook (single background worker, log on disk, pgrep before starting):
  cd rna_agent_system
  PYTHONPATH="$(pwd):$PYTHONPATH" setsid nohup python \
      experiments/junction_integrated_optimizer_eval.py --workers 8 \
      > experiments/results/junction_integrated_optimizer_eval.log 2>&1 &
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from junction_aware_codon_optimizer import (  # noqa: E402
    EASY_TARGETS,
    HARD_TARGETS,
    JunctionFolder,
    _genetic_code,
    load_serial_seed,
    load_shard_baselines,
)

LDS_URL = "http://127.0.0.1:8014"
FOLD_URL = "http://127.0.0.1:8015/fold"

DEFAULT_TARGETS = list(HARD_TARGETS) + list(EASY_TARGETS)
DEFAULT_REPS = [0, 1, 2]
DEFAULT_W_JUNS = [0.0, 0.5, 1.0, 2.0]

# Pre-registered thresholds (see docstring).
V1_MEDIAN_STABILITY_COST_PER_NT = 0.021996110355454235
STABILITY_COST_MAX = 0.5 * V1_MEDIAN_STABILITY_COST_PER_NT  # 0.010998... ~ 0.011
HARD_REPAIR_RATE_MIN = 2.0 / 3.0
CAI_DROP_MAX = 0.02
EXPECTED_HARD_BURIED_AT_BASELINE = 7

FALLBACK_LAMBDA = 0.0  # FullLengthMrnaDesignWorkflow / endpoint default; recorded if used.


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _translate_cds(cds_rna: str) -> str:
    """Translate RNA CDS with the same Biopython table P1 uses; stops -> '*'."""
    forward_table, stop_codons, _ = _genetic_code()
    cds = cds_rna.upper().replace("U", "T")
    aas = []
    for i in range(0, len(cds) - 2, 3):
        codon = cds[i : i + 3]
        aas.append("*" if codon in stop_codons else forward_table[codon])
    return "".join(aas)


def _session_lambda(target: str, rep: int) -> tuple[float, str]:
    """lambda_value from the session params.json; falls back to workflow default."""
    sess = PROJECT_ROOT / "workspace" / "sessions" / f"fig3t1_t1_{target}_r0_rep{rep}"
    params_files = sorted(glob.glob(str(sess / "params.json")))
    if params_files:
        try:
            value = json.loads(Path(params_files[-1]).read_text()).get("lambda_value")
            if value is not None:
                return float(value), "session_params"
        except Exception:
            pass
    return FALLBACK_LAMBDA, "workflow_default_fallback"


def _endpoint_timeout_seconds(protein: str, flank_nt: int = 42) -> float:
    """Mirror the service-side 0.8 s/nt + 180 s rule, plus HTTP headroom."""
    total_nt = 3 * len(protein) + flank_nt
    return max(300, int(total_nt * 0.8) + 180) + 300


def run_cell(
    target: str,
    rep: int,
    w_jun: float,
    folder: JunctionFolder,
    shard: dict,
) -> dict:
    """Run one (target, rep, w_jun) cell through the junction-aware endpoint."""
    row: dict = {
        "target_id": target,
        "target_class": "hard" if target in HARD_TARGETS else "easy",
        "rep": rep,
        "w_jun": w_jun,
        "success": False,
        "error": None,
    }
    t0 = time.time()
    seed = load_serial_seed(target, rep)
    if seed is None:
        row["error"] = "serial seed not found"
        return row
    utr5, utr3, seed_cds = seed["utr5_sequence"], seed["utr3_sequence"], seed["cds_sequence"]

    protein = _translate_cds(seed_cds).rstrip("*")
    lambda_value, lambda_source = _session_lambda(target, rep)
    row["lambda_value"] = lambda_value
    row["lambda_source"] = lambda_source
    row["seed"] = {
        "session_id": seed["session_id"],
        "protein_length": len(protein),
        "cds_length": len(seed_cds),
        "utr5_length": len(utr5),
        "utr3_length": len(utr3),
        "seed_cds": seed_cds,
    }

    baseline_row = shard.get((target, 0, rep)) or {}
    baseline_best = baseline_row.get("best") or {}
    baseline = {
        "best_candidate_id": baseline_row.get("best_candidate_id"),
        "cds_cai": baseline_best.get("cds_cai"),
        "full_mfe_per_nt": baseline_best.get("full_mfe_per_nt"),
        "junction_5utr_cds_aug_buried": baseline_best.get("junction_5utr_cds_aug_buried"),
        "junction_5utr_cds_kozak_buried": baseline_best.get("junction_5utr_cds_kozak_buried"),
    }
    row["baseline_serial"] = baseline

    try:
        payload = {
            "protein_sequence": protein,
            "lambda_value": lambda_value,
            "utr5_flank": utr5,
            "utr3_flank": utr3,
            "junction_weight": w_jun,
        }
        try:
            resp = _post_json(
                f"{LDS_URL}/generate/cds_junction_aware",
                payload,
                timeout=_endpoint_timeout_seconds(protein),
            )
        except urllib.error.HTTPError as http_exc:
            # Keep the service-side detail (e.g. LinearDesign returncode/stderr).
            body = http_exc.read().decode()[:500]
            raise RuntimeError(f"HTTP {http_exc.code}: {body}") from http_exc
        cds = resp["cds_sequence"]
        junction = folder.junction_metrics(utr5, cds, utr3)
        full_construct = utr5 + cds + utr3
        full_mfe = folder.fold(full_construct).get("mfe")
        full_mfe_per_nt = full_mfe / len(full_construct)

        row["design"] = {
            "cds_sequence": cds,
            "cds_cai": resp["cds_cai"],
            "mfe_objective": resp["mfe"],
            "mfe_thermo": resp["mfe_thermo"],
            "junction_window_pair_count": resp["junction_window_pair_count"],
            "utr5_flank_used": resp["utr5_flank"],
            "utr3_flank_used": resp["utr3_flank"],
            "flank_nt": resp["flank_nt"],
            "junction_window_nt": resp["junction_window_nt"],
        }
        row["metrics"] = {
            **junction,
            "full_construct_length": len(full_construct),
            "full_construct_mfe": full_mfe,
            "full_construct_mfe_per_nt": full_mfe_per_nt,
        }

        base_buried = bool(baseline.get("junction_5utr_cds_aug_buried")) or bool(
            baseline.get("junction_5utr_cds_kozak_buried")
        )
        new_buried = bool(junction.get("aug_buried")) or bool(
            junction.get("kozak_buried")
        )
        row["derived"] = {
            "baseline_buried": base_buried,
            "designed_buried": new_buried,
            "repaired": bool(base_buried and not new_buried),
            "stability_cost_per_nt": (
                None
                if baseline.get("full_mfe_per_nt") is None
                else full_mfe_per_nt - baseline["full_mfe_per_nt"]
            ),
            "delta_cai": (
                None
                if baseline.get("cds_cai") is None
                else baseline["cds_cai"] - resp["cds_cai"]
            ),
        }
        row["success"] = True
    except Exception as exc:  # noqa: BLE001 - record and continue the matrix
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["elapsed_seconds"] = round(time.time() - t0, 2)
    return row


def determinism_and_legacy_probes(folder: JunctionFolder) -> dict:
    """Pre-registered degenerate-arm probes on (Insulin, rep0).

    1) Determinism: two independent w_jun=0 calls must be byte-identical.
    2) Informational: legacy no-flank /generate/cds vs flanked w_jun=0 call.
    """
    seed = load_serial_seed("Insulin", 0)
    protein = _translate_cds(seed["cds_sequence"]).rstrip("*")
    lambda_value, _ = _session_lambda("Insulin", 0)
    payload = {
        "protein_sequence": protein,
        "lambda_value": lambda_value,
        "utr5_flank": seed["utr5_sequence"],
        "utr3_flank": seed["utr3_sequence"],
        "junction_weight": 0.0,
    }
    r1 = _post_json(f"{LDS_URL}/generate/cds_junction_aware", payload, timeout=600)
    r2 = _post_json(f"{LDS_URL}/generate/cds_junction_aware", payload, timeout=600)
    legacy = _post_json(
        f"{LDS_URL}/generate/cds",
        {"protein_sequence": protein, "lambda_value": lambda_value},
        timeout=600,
    )
    return {
        "cell": ["Insulin", 0, 0.0],
        "determinism_identical": r1["cds_sequence"] == r2["cds_sequence"],
        "legacy_matches_flanked_w0": legacy["generated_sequence"] == r1["cds_sequence"],
        "note": (
            "determinism_identical is the pre-registered degenerate assertion; "
            "legacy_matches_flanked_w0 is informational only (flanks still fold "
            "at w_jun=0 in the argc==8 path)."
        ),
    }


def smoke_test() -> None:
    """Tiny junction-aware call to verify the patched endpoint is live."""
    resp = _post_json(
        f"{LDS_URL}/generate/cds_junction_aware",
        {
            "protein_sequence": "MELAALCRWGLLLALLPPGAASTQVCTGTD",
            "lambda_value": 2.0,
            "utr5_flank": "AGGGGGAGGCGUGAGAGAAAG",
            "utr3_flank": "UGUAAAUGUAAAUGUAAAUGU",
            "junction_weight": 1.0,
        },
        timeout=600,
    )
    assert resp["cds_sequence"] and "junction_window_pair_count" in resp, resp
    print(
        "smoke ok: pair_count={} mfe={} mfe_thermo={}".format(
            resp["junction_window_pair_count"], resp["mfe"], resp["mfe_thermo"]
        ),
        flush=True,
    )


def _median(values: list[float]) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def build_summary(rows: list[dict], probes: dict | None, args: argparse.Namespace) -> dict:
    ok_rows = [r for r in rows if r.get("success")]
    per_weight: dict[str, dict] = {}
    for w in args.w_juns:
        cells = [r for r in ok_rows if r["w_jun"] == w]
        hard = [r for r in cells if r["target_class"] == "hard"]
        buried = [r for r in hard if r["derived"]["baseline_buried"]]
        repaired = [r for r in buried if r["derived"]["repaired"]]
        costs = [r["derived"]["stability_cost_per_nt"] for r in cells]
        dcai = [r["derived"]["delta_cai"] for r in cells]
        pairs = [r["design"]["junction_window_pair_count"] for r in cells]
        repair_rate = (len(repaired) / len(buried)) if buried else None
        med_cost = _median(costs)
        med_dcai = _median(dcai)
        per_weight[f"{w:g}"] = {
            "n_cells": len(cells),
            "n_failed": len([r for r in rows if r["w_jun"] == w]) - len(cells),
            "hard_buried_at_baseline": len(buried),
            "hard_repaired": len(repaired),
            "hard_repair_rate": repair_rate,
            "median_stability_cost_per_nt": med_cost,
            "median_delta_cai": med_dcai,
            "median_junction_window_pair_count": _median(pairs),
            "go": bool(
                repair_rate is not None
                and repair_rate >= HARD_REPAIR_RATE_MIN
                and med_cost is not None
                and med_cost <= STABILITY_COST_MAX
                and med_dcai is not None
                and med_dcai <= CAI_DROP_MAX
            ),
        }

    # w_jun responsiveness: do designed CDSs differ across weights per (target, rep)?
    groups: dict[tuple, set] = {}
    for r in ok_rows:
        groups.setdefault((r["target_id"], r["rep"]), set()).add(r["design"]["cds_sequence"])
    n_groups = len(groups)
    n_responsive = sum(1 for seqs in groups.values() if len(seqs) > 1)

    go_weights = [w for w, s in per_weight.items() if s["go"]]
    return {
        "analysis": "P2 junction-integrated LinearDesign optimizer go/no-go",
        "date": time.strftime("%Y-%m-%d"),
        "preregistration": (
            "junction_integrated_optimizer_eval.py docstring (P2, 2026-08-04); "
            "follows P1 v2 NO-GO mechanism (p1_v2_stability_sweep_summary.json)"
        ),
        "criteria": {
            "hard_repair_rate_min": HARD_REPAIR_RATE_MIN,
            "stability_cost_max_per_nt": STABILITY_COST_MAX,
            "cai_drop_max": CAI_DROP_MAX,
        },
        "expected_hard_buried_at_baseline": EXPECTED_HARD_BURIED_AT_BASELINE,
        "v1_median_stability_cost_per_nt": V1_MEDIAN_STABILITY_COST_PER_NT,
        "matrix": {
            "targets": args.targets.split(","),
            "reps": [int(x) for x in args.reps.split(",")],
            "w_juns": args.w_juns,
            "lambda": "per-cell session params.json (all 2.0 at registration)",
        },
        "per_weight": per_weight,
        "go_weights": go_weights,
        "decision": "GO" if go_weights else "NO-GO",
        "mechanism": {
            "w_jun_responsive_group_fraction": (
                (n_responsive / n_groups) if n_groups else None
            ),
            "n_target_rep_groups": n_groups,
            "probes": probes,
        },
        "n_rows": len(rows),
        "n_success": len(ok_rows),
    }


def load_done(output: Path) -> set[tuple]:
    """Cells already completed SUCCESSFULLY (failed rows are retried)."""
    done = set()
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("success"):
                done.add((r["target_id"], r["rep"], r["w_jun"]))
    return done


def load_latest_rows(output: Path) -> list[dict]:
    """All rows, deduplicated per (target, rep, w_jun); latest file row wins,
    so retried failures are superseded by their later rerun rows."""
    latest: dict[tuple, dict] = {}
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            latest[(r["target_id"], r["rep"], r["w_jun"])] = r
    return list(latest.values())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--targets", default=",".join(DEFAULT_TARGETS))
    ap.add_argument("--reps", default=",".join(str(r) for r in DEFAULT_REPS))
    ap.add_argument("--w-juns", default=",".join(f"{w:g}" for w in DEFAULT_W_JUNS),
                    dest="w_juns")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--output", default=str(RESULTS_DIR / "junction_integrated_optimizer.jsonl"))
    ap.add_argument("--summary", default=str(RESULTS_DIR / "junction_integrated_optimizer_summary.json"))
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    args.w_juns = [float(x) for x in args.w_juns.split(",")]

    # Service pre-flight: direct service calls bypass workflow pre-flight,
    # so pull up both microservices explicitly (P1 pattern).
    from agent_core.services.service_manager import (
        CAPABILITY_SERVICE_MAP,
        ensure_services_ready,
    )

    ok, msgs = ensure_services_ready(
        [
            CAPABILITY_SERVICE_MAP["design_mrna_cds_junction_aware_with_lineardesign"],
            CAPABILITY_SERVICE_MAP["predict_rna_secondary_structure_with_linearfold"],
        ]
    )
    print(f"service preflight: ok={ok} {msgs}", flush=True)
    if not ok:
        return 1
    smoke_test()

    folder = JunctionFolder(FOLD_URL, PROJECT_ROOT / "workspace" / "tmp")
    shard = load_shard_baselines()

    # Pre-registered degenerate-arm probes (cheap; always run).
    print("running determinism/legacy probes (Insulin rep0 w_jun=0)...", flush=True)
    probes = determinism_and_legacy_probes(folder)
    print(f"probes: {json.dumps({k: v for k, v in probes.items() if k != 'note'})}", flush=True)
    if not probes["determinism_identical"]:
        print("FATAL: w_jun=0 determinism assertion failed", flush=True)
        return 1

    targets = args.targets.split(",")
    reps = [int(x) for x in args.reps.split(",")]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(output) if args.resume else set()

    jobs = [(t, r, w) for t in targets for r in reps for w in args.w_juns]
    pending = [j for j in jobs if j not in done]
    print(f"matrix: {len(jobs)} cells, {len(done)} done, {len(pending)} pending", flush=True)

    lock = threading.Lock()
    rows_written = 0
    t_start = time.time()
    with output.open("a") as fh:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(run_cell, t, r, w, folder, shard): (t, r, w)
                for (t, r, w) in pending
            }
            for fut in as_completed(futures):
                t, r, w = futures[fut]
                row = fut.result()
                with lock:
                    fh.write(json.dumps(row) + "\n")
                    fh.flush()
                    rows_written += 1
                status = "ok" if row["success"] else f"FAIL {row['error']}"
                print(
                    f"[{rows_written}/{len(pending)}] {t} rep{r} w_jun={w:g} "
                    f"{status} elapsed={row.get('elapsed_seconds')}s",
                    flush=True,
                )

    all_rows = load_latest_rows(output)
    summary = build_summary(all_rows, probes, args)
    summary["runtime_hours"] = round((time.time() - t_start) / 3600.0, 3)
    Path(args.summary).write_text(json.dumps(summary, indent=1))
    print(f"decision: {summary['decision']} go_weights={summary['go_weights']}", flush=True)
    print(f"summary -> {args.summary}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
