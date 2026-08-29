#!/usr/bin/env python3
"""Experiment 2+3 (paper §2.2, Figs. 2b & 2c): CDS null model — designed vs
wild-type vs random-synonymous CDSs on CAI and folding energy.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2)
-----------------------------------------------------
* Hypothesis (Fig. 2b, primary): the platform's CDS-design golden path —
  ``mrna_cds_design`` with ``design_tool="all"`` (LinearDesign λ∈{0,1,4,10} +
  RNARL + GEMORNA → fold/GC/CAI evaluation → scoring → ranking), i.e. the
  system as designed, no objective tuning — delivers CDSs whose CAI exceeds
  both wild-type CDSs and random-synonymous controls, and WT exceeds random
  (the platform reproduces the direction of natural selection on codon use).
* Hypothesis (Fig. 2c, secondary; user-directed three-arm extension of the
  legacy WT-vs-random control): designed CDSs achieve more favourable (more
  negative) MFE/nt than both controls — the system's ranking balances codon
  adaptation against structure, so both dimensions should beat the nulls.
  WT-vs-random MFE/nt is reported as measured (legacy: NS, P = 0.23; no
  direction pre-registered for this pair).
* Primary metric: CAI (platform tool ``compute_cai_for_cds_sequence``,
  Kazusa tables, species-resolved per target). Secondary: MFE/nt (LinearFold,
  the platform's fold of record, via ``mrna_sequence_scoring``).
* Expected effect size: legacy CAI medians 0.745/0.729/0.672 (WT vs random
  Mann–Whitney P ≈ 4e-7, Cliff's δ ≈ 0.69) — historical reference only, the
  reset run re-derives every number (the legacy designed arm's generator
  configuration is not reconstructible; this run registers the golden-path
  configuration above as the designed arm).
* Arms: designed = best-ranked golden-path candidate per target (n = 20);
  WT = NCBI RefSeq wild-type CDS anchors (n = 20); random = 10 seeded
  synonymous resamples of each WT (n = 200; uniform choice over the standard
  genetic code's synonymous set, ``random.Random("exp2:<target>:<draw>")``,
  deterministic across runs). Random draws are generated from the WT CDS
  itself, so the three targets whose WT translation deviates slightly from
  the benchmark protein stay honest WT-synonymous nulls.
* Species-correct design (2026-08-25 platform fix, re-run): LinearDesign now
  designs against the ``cai_species``-resolved platform codon table (same
  Kazusa source the CAI evaluator uses) on both the golden path and the
  navigation path; unresolvable species fail at the input layer. The first
  run of this driver pre-dates the fix (archived at
  ``experiments/results/exp2_cds_nulls_prefix/`` — its E. coli targets were
  designed against LinearDesign's default human table); session prefixes are
  ``exp2rd_/exp2rs_`` to keep the two runs' session artifacts disjoint.
* Scoring: every sequence in every arm goes through the same
  ``mrna_sequence_scoring`` workflow call (CAI + GC + LinearFold MFE,
  ``cai_species`` per target) — one code path for all three arms.
* Gate: pilot 3/3 targets complete with all arms scored before the full
  matrix. Full-run CAI ordering (designed > WT > random) is assessed and
  reported; a violated ordering is reported, never dropped.
* CapGate policy: ``RNADA_CAPGATE=advisory`` (the documented regression
  convention; deterministic CAI/GC/MFE tools are not gated).
* Budget: one design run per target, one scoring run per sequence;
  ``--resume`` skips records already successful on disk.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp2_cds_null_model.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp2_cds_null_model.py --design
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp2_cds_null_model.py --score
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp2_cds_null_model.py --summary

Outputs under ``experiments/results/exp2_cds_nulls/``:
    design_runs.jsonl, fig2_cds_nulls.jsonl, summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
WT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "wt_cds"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp2_cds_nulls"

DESIGN_RUNS = RESULTS_DIR / "design_runs.jsonl"
SCORING_RUNS = RESULTS_DIR / "fig2_cds_nulls.jsonl"

N_RANDOM_DRAWS = 10
PILOT_TARGETS = ["Insulin", "GFP", "A1AT"]  # human+E. coli tables, small→mid size

# Standard genetic code: codon (RNA) → amino acid; '*' = stop. Blocks follow
# the (first, second)-base order AA, AU, AG, AC, UA, UU, UG, UC, GA, GU, GG,
# GC, CA, CU, CG, CC; within a block the third base runs A, U, G, C — exactly
# the enumeration order below.
_BASES = "AUGC"
_AAS = "".join([
    "KNKN",  # AAx
    "IIMI",  # AUx  (AUG = Met)
    "RSRS",  # AGx  (AGA/AGG = Arg; AGU/AGC = Ser)
    "TTTT",  # ACx
    "*Y*Y",  # UA UAA UAU UAG UAC
    "LFLF",  # UUx  (UUA/UUG = Leu)
    "*CWC",  # UG UGA UGU UGG UGC (UGG = Trp)
    "SSSS",  # UCx
    "EDED",  # GAx
    "VVVV",  # GUx
    "GGGG",  # GGx
    "AAAA",  # GCx
    "QHQH",  # CAx
    "LLLL",  # CUx
    "RRRR",  # CGx
    "PPPP",  # CCx
])
CODON_TABLE: dict[str, str] = {
    b1 + b2 + b3: _AAS[i]
    for i, (b1, b2, b3) in enumerate(
        (x, y, z) for x in _BASES for y in _BASES for z in _BASES
    )
}
SYNONYMOUS_CODONS: dict[str, list[str]] = {}
for _codon, _aa in CODON_TABLE.items():
    if _aa == "*":
        continue
    SYNONYMOUS_CODONS.setdefault(_aa, []).append(_codon)
STOPS = {"UAA", "UAG", "UGA"}


# --------------------------------------------------------------------- inputs

def load_targets(only: list[str] | None = None) -> list[dict[str, Any]]:
    targets = []
    for p in sorted(TARGETS_DIR.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if only is None or d["target_id"] in only:
            targets.append(d)
    if only is not None:
        missing = set(only) - {t["target_id"] for t in targets}
        if missing:
            raise SystemExit(f"unknown pilot targets: {sorted(missing)}")
    return targets


def read_fasta(path: Path) -> str:
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.lstrip().startswith(">")]
    return "".join(lines).upper().replace("T", "U")


def load_wt_cds(target_id: str) -> dict[str, Any]:
    """Load the WT CDS anchor, strip the terminal stop, validate."""
    seq = read_fasta(WT_DIR / f"{target_id}.fa")
    if len(seq) % 3 != 0:
        raise ValueError(f"{target_id}: WT CDS length {len(seq)} not multiple of 3")
    codons = [seq[i:i + 3] for i in range(0, len(seq), 3)]
    internal_stops = [i for i, c in enumerate(codons[:-1]) if c in STOPS]
    if internal_stops:
        raise ValueError(f"{target_id}: internal stop codons at {internal_stops[:5]}")
    if codons and codons[-1] in STOPS:
        codons = codons[:-1]
    return {
        "target_id": target_id,
        "cds": "".join(codons),
        "length_nt": 3 * len(codons),
        "terminal_stop_stripped": True,
    }


def random_synonymous(wt_cds: str, target_id: str, draw: int) -> str:
    """Uniform synonymous resample of the WT CDS (standard code, seeded)."""
    rng = random.Random(f"exp2:{target_id}:{draw}")
    out = []
    for i in range(0, len(wt_cds), 3):
        codon = wt_cds[i:i + 3]
        out.append(rng.choice(SYNONYMOUS_CODONS[CODON_TABLE[codon]]))
    return "".join(out)


# ------------------------------------------------------------------ CLI runs

def find_results_file(session_dir: Path) -> Path | None:
    candidates = sorted(
        session_dir.glob("workflow_results_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def run_cli(
    workflow: str,
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
        "--workflow", workflow,
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
    results_file = find_results_file(session_dir)
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


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def load_successful_keys(path: Path, key_of: Any) -> set[str]:
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
            done.add(key_of(rec))
    return done


# --------------------------------------------------------------- design arm

def design_one(target: dict[str, Any], *, capgate: str) -> dict[str, Any]:
    tid = target["target_id"]
    aa_len = len(target["protein_sequence"])
    params = {
        "protein_sequence": target["protein_sequence"],
        "design_tool": "all",
        "cai_species": target["species_for_codon_optimization"],
        "run_fold": True,
        "run_gc": True,
    }
    timeout = int(max(1800, 900 + 2.5 * aa_len))
    session_id = f"exp2rd_{tid}"
    print(f"[design] {tid} ({aa_len} aa, timeout={timeout}s) ...", flush=True)
    results, exit_code, elapsed, error = run_cli(
        "mrna_cds_design", params,
        session_id=session_id, timeout=timeout, capgate=capgate,
    )
    record: dict[str, Any] = {
        "target_id": tid,
        "species": target["species_for_codon_optimization"],
        "aa_length": aa_len,
        "session_id": session_id,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error,
        "success": False,
    }
    if results is not None:
        best = results.get("best_candidate") or {}
        record["workflow_success"] = bool(results.get("success"))
        record["candidate_count"] = len(results.get("candidates") or results.get("all_candidates") or [])
        record["best_source"] = best.get("source")
        record["best_scores"] = best.get("scores") or {}
        seq = (best.get("sequence") or "").upper().replace("T", "U")
        record["designed_cds"] = seq or None
        record["designed_length_nt"] = len(seq) or None
        record["success"] = bool(results.get("success")) and bool(seq)
        if not record["success"] and error is None:
            record["error"] = "no_best_candidate_sequence"
    print(f"          -> {'OK' if record['success'] else 'FAIL(%s)' % record['error']} "
          f"in {record['elapsed_seconds']:.1f}s (best={record.get('best_source')})", flush=True)
    return record


def run_design(targets: list[dict[str, Any]], *, capgate: str, resume: bool, workers: int) -> int:
    done = load_successful_keys(DESIGN_RUNS, lambda r: r["target_id"]) if resume else set()
    todo = [t for t in targets if t["target_id"] not in done]
    if not todo:
        print("design arm already complete (resume)")
        return 0
    n_fail = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(design_one, t, capgate=capgate): t for t in todo}
        for fut in as_completed(futures):
            rec = fut.result()
            append_record(DESIGN_RUNS, rec)
            n_fail += not rec["success"]
    print(f"design arm: {len(todo) - n_fail}/{len(todo)} succeeded")
    return 0 if n_fail == 0 else 1


# -------------------------------------------------------------- scoring arm

def metric_bundle(best: dict[str, Any]) -> dict[str, Any]:
    bundle = ((best.get("metadata") or {}).get("metrics_bundle")) or {}
    scores = best.get("scores") or {}
    metrics = best.get("metrics") or {}
    def pick(key, *alts):
        for src in (bundle, scores, metrics):
            for k in (key, *alts):
                if src.get(k) is not None:
                    return src[k]
        return None
    return {
        "cai_score": pick("cai_score", "cai"),
        "mfe_kcal_per_mol": pick("mfe_kcal_per_mol", "mfe"),
        "mfe_per_nt": pick("mfe_per_nt"),
        "gc_content": pick("gc_content"),
    }


def score_one(job: dict[str, Any], *, capgate: str) -> dict[str, Any]:
    tid = job["target_id"]
    sid = job["session_id"]
    params = {
        "sequence": job["sequence"],
        "cai_species": job["species"],
        "run_gc_tool": True,
        "run_fold_tool": True,
    }
    results, exit_code, elapsed, error = run_cli(
        "mrna_sequence_scoring", params,
        session_id=sid, timeout=900, capgate=capgate,
    )
    record: dict[str, Any] = {
        "target_id": tid,
        "species": job["species"],
        "arm": job["arm"],           # designed | wt | random
        "draw": job.get("draw"),
        "source": job.get("source"),
        "length_nt": len(job["sequence"]),
        "session_id": sid,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error,
        "success": False,
    }
    if results is not None:
        best = results.get("best_candidate") or {}
        vals = metric_bundle(best)
        record.update(vals)
        if vals["mfe_per_nt"] is None and vals["mfe_kcal_per_mol"] is not None:
            record["mfe_per_nt"] = vals["mfe_kcal_per_mol"] / len(job["sequence"])
        record["success"] = bool(
            results.get("success") and vals["cai_score"] is not None
        )
        if not record["success"] and error is None:
            record["error"] = "missing_cai_in_result"
    return record


def build_scoring_jobs(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """All scoring jobs: designed (from design records) + WT + random draws."""
    design_by_id: dict[str, dict[str, Any]] = {}
    if DESIGN_RUNS.exists():
        for line in DESIGN_RUNS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("success"):
                design_by_id[rec["target_id"]] = rec  # latest successful wins

    jobs: list[dict[str, Any]] = []
    for t in targets:
        tid = t["target_id"]
        species = t["species_for_codon_optimization"]
        drec = design_by_id.get(tid)
        if drec:
            jobs.append({
                "target_id": tid, "species": species, "arm": "designed",
                "draw": None, "source": drec.get("best_source"),
                "sequence": drec["designed_cds"],
                "session_id": f"exp2rs_designed_{tid}",
            })
        else:
            print(f"[warn] no successful design record for {tid} — designed point skipped")
        wt = load_wt_cds(tid)
        jobs.append({
            "target_id": tid, "species": species, "arm": "wt",
            "draw": None, "source": "wt_cds_anchor",
            "sequence": wt["cds"],
            "session_id": f"exp2rs_wt_{tid}",
        })
        for draw in range(N_RANDOM_DRAWS):
            jobs.append({
                "target_id": tid, "species": species, "arm": "random",
                "draw": draw, "source": "random_synonymous",
                "sequence": random_synonymous(wt["cds"], tid, draw),
                "session_id": f"exp2rs_random_{tid}_{draw}",
            })
    return jobs


def run_scoring(targets: list[dict[str, Any]], *, capgate: str, resume: bool, workers: int) -> int:
    jobs = build_scoring_jobs(targets)
    done = load_successful_keys(
        SCORING_RUNS, lambda r: f"{r['arm']}:{r['target_id']}:{r['draw']}"
    ) if resume else set()
    todo = [j for j in jobs if f"{j['arm']}:{j['target_id']}:{j.get('draw')}" not in done]
    print(f"scoring arm: {len(todo)} sequences to score ({len(jobs)} total jobs)")
    if not todo:
        return 0
    n_fail = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(score_one, j, capgate=capgate): j for j in todo}
        for i, fut in enumerate(as_completed(futures), start=1):
            rec = fut.result()
            append_record(SCORING_RUNS, rec)
            n_fail += not rec["success"]
            if i % 20 == 0 or i == len(todo):
                print(f"[score] {i}/{len(todo)} done ({n_fail} failed)", flush=True)
    print(f"scoring arm: {len(todo) - n_fail}/{len(todo)} succeeded")
    return 0 if n_fail == 0 else 1


# -------------------------------------------------------------------- stats

def cliffs_delta(x: list[float], y: list[float]) -> float:
    gt = sum(1 for a in x for b in y if a > b)
    lt = sum(1 for a in x for b in y if a < b)
    return (gt - lt) / (len(x) * len(y))


def pairwise(values: dict[str, list[float]], a: str, b: str) -> dict[str, Any]:
    from scipy.stats import mannwhitneyu
    x, y = values[a], values[b]
    if len(x) < 2 or len(y) < 2:
        return {"n_x": len(x), "n_y": len(y)}
    u = mannwhitneyu(x, y, alternative="two-sided")
    return {
        "n_x": len(x), "n_y": len(y),
        "median_x": round(statistics.median(x), 4),
        "median_y": round(statistics.median(y), 4),
        "mannwhitney_p": float(u.pvalue),
        "cliffs_delta": round(cliffs_delta(x, y), 4),
    }


def write_summary() -> int:
    records: dict[str, dict[str, Any]] = {}
    if SCORING_RUNS.exists():
        for line in SCORING_RUNS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = f"{rec['arm']}:{rec['target_id']}:{rec.get('draw')}"
            records[key] = rec  # latest wins

    ok = [r for r in records.values() if r.get("success")]
    cai: dict[str, list[float]] = {}
    mfe: dict[str, list[float]] = {}
    gc: dict[str, list[float]] = {}
    for r in ok:
        if r.get("cai_score") is not None:
            cai.setdefault(r["arm"], []).append(float(r["cai_score"]))
        if r.get("mfe_per_nt") is not None:
            mfe.setdefault(r["arm"], []).append(float(r["mfe_per_nt"]))
        if r.get("gc_content") is not None:
            gc.setdefault(r["arm"], []).append(float(r["gc_content"]))

    def arm_stats(values: dict[str, list[float]]) -> dict[str, Any]:
        out = {}
        for arm in ("designed", "wt", "random"):
            v = values.get(arm) or []
            out[arm] = {
                "n": len(v),
                "median": round(statistics.median(v), 4) if v else None,
                "q1": round(statistics.quantiles(v, n=4)[0], 4) if len(v) >= 4 else None,
                "q3": round(statistics.quantiles(v, n=4)[2], 4) if len(v) >= 4 else None,
            }
        return out

    summary = {
        "experiment": "exp2_cds_null_model",
        "panels": ["fig2b_cai", "fig2c_mfe_per_nt"],
        "generated": datetime.now().isoformat(timespec="seconds"),
        "capgate_policy_primary_arm": "advisory",
        "designed_arm_config": "mrna_cds_design design_tool=all (LinearDesign λ∈{0,1,4,10}"
                               " + RNARL + GEMORNA → evaluate → score → rank), best-ranked",
        "random_arm": f"{N_RANDOM_DRAWS} seeded synonymous draws per WT "
                      "(uniform, standard code, seed 'exp2:<target>:<draw>')",
        "n_scored_records": len(ok),
        "cai": {
            "arms": arm_stats(cai),
            "designed_vs_wt": pairwise(cai, "designed", "wt"),
            "wt_vs_random": pairwise(cai, "wt", "random"),
            "designed_vs_random": pairwise(cai, "designed", "random"),
        },
        "mfe_per_nt": {
            "arms": arm_stats(mfe),
            "designed_vs_wt": pairwise(mfe, "designed", "wt"),
            "wt_vs_random": pairwise(mfe, "wt", "random"),
            "designed_vs_random": pairwise(mfe, "designed", "random"),
        },
        "gc_content_control": {"arms": arm_stats(gc)},
        "failures": [
            {"key": k, "error": r.get("error")}
            for k, r in records.items() if not r.get("success")
        ][:50],
    }
    cai_gate = None
    if all(cai.get(a) for a in ("designed", "wt", "random")):
        cai_gate = (
            statistics.median(cai["designed"]) > statistics.median(cai["wt"]) >
            statistics.median(cai["random"])
        )
    summary["cai_ordering_gate_designed_gt_wt_gt_random"] = cai_gate

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["cai"], indent=2))
    print(json.dumps(summary["mfe_per_nt"], indent=2))
    print(f"CAI ordering gate (designed > WT > random): {cai_gate}")
    print(f"summary -> {out}")
    return 0


# ---------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true",
                      help=f"design+score the pilot targets {PILOT_TARGETS}")
    mode.add_argument("--design", action="store_true", help="run the design arm (20 targets)")
    mode.add_argument("--score", action="store_true",
                      help="run the scoring arm (designed+WT+random)")
    mode.add_argument("--summary", action="store_true", help="write summary.json + stats")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=2,
                        help="concurrent CLI subprocesses (default 2)")
    parser.add_argument("--score-workers", dest="score_workers", type=int, default=4)
    parser.add_argument("--capgate", default="advisory", choices=["advisory", "enforce", "off"])
    args = parser.parse_args()

    if args.summary:
        return write_summary()

    if args.pilot:
        targets = load_targets(PILOT_TARGETS)
        rc1 = run_design(targets, capgate=args.capgate, resume=args.resume,
                         workers=args.workers)
        rc2 = run_scoring(targets, capgate=args.capgate, resume=args.resume,
                          workers=args.score_workers)
        return max(rc1, rc2)

    if args.design:
        return run_design(load_targets(), capgate=args.capgate,
                          resume=args.resume, workers=args.workers)
    return run_scoring(load_targets(), capgate=args.capgate,
                       resume=args.resume, workers=args.score_workers)


if __name__ == "__main__":
    sys.exit(main())
