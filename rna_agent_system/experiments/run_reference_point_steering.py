#!/usr/bin/env python3
"""Fig 3d driver: reference-point steering on full-length mRNA design.

Implements `docs/MANUSCRIPT.md` §5.2 run matrix B:
2 targets (`SARS-CoV-2_Spike_WT`, `EPO`) × 3 steering profiles × 3 repeats = 18
`full_length_mrna_design` runs with `bmc_max_rounds=1`.

Profile construction (programmatic, from a Serial pilot pool per target):

| Profile           | reference_point construction                                        |
|-------------------|---------------------------------------------------------------------|
| translation-first | utr5_mrl = pool max; target_cds_cai = 0.95; target_cds_mfe = median |
| stability-first   | full_mfe_score = pool max; utr3_stability = pool max;               |
|                   | target_cds_mfe = pool min (most negative); target_cds_cai = median  |
| balanced          | every dimension at its pool best (≈ utopian)                        |

The pilot pool is extracted from existing Serial ablation records
(`bmc_max_rounds=0`, `success=true`) in the Fig-3 Type-I shard JSONLs — pass
one or more via `--pool-jsonl` (defaults to the shard files that exist).
`--pool-json <file>` overrides JSONL extraction with a handmade pool:
``{"<target_id>": {"<dim>": [v1, v2, ...] or scalar}}`` where ``<dim>`` is one
of ``utr5_mrl, utr3_stability, full_mfe_score, target_cds_mfe, target_cds_cai``.

Key-name mapping (verified against
`agent_core/workflows/full_length_mrna_design.py`):
- workflow input ``reference_point`` is a dict accepting ONLY
  ``utr5_mrl``, ``utr3_stability``, ``full_mfe_score`` (all maximized);
- CDS objectives go in as top-level params ``target_cds_mfe`` +
  ``target_cds_cai`` (required together) and are converted by the workflow
  into the internal ``cds_component`` =
  ``(-target_cds_mfe + codon_count*log(target_cds_cai)) / cds_length_nt``.
- ``cds_mfe`` is a minimization dimension (more negative = more stable), so
  its "pool best" is the raw minimum; profile "pool min" values are raw mins.

Output: `experiments/results/fig3_steering.jsonl` — one record per run.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_reference_point_steering.py \
        [--targets T1,T2] [--profiles P1,P2] [--reps 3] [--limit N] [--resume] \
        [--timeout SEC] [--pool-jsonl F ...] [--pool-json F] [--dry-run] [--self-test]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT, run_task_dict  # noqa: E402
from run_bmc_type1_ablation import BEST_SCORE_KEYS  # noqa: E402

TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig3_steering.jsonl"
DEFAULT_POOL_JSONL = [
    PROJECT_ROOT / "experiments" / "results" / "fig3_type1_shard_a.jsonl",
    PROJECT_ROOT / "experiments" / "results" / "fig3_type1_shard_b.jsonl",
]

DEFAULT_TARGETS = ["SARS-CoV-2_Spike_WT", "EPO"]
PROFILES = ["translation-first", "stability-first", "balanced"]

# Manuscript semantic dimension -> (pool source key in the ablation record's
# `best` dict, direction).  cds_mfe is "more negative = better" (minimize);
# every other dimension is maximized.
DIMENSIONS: dict[str, tuple[str, str]] = {
    "utr5_mrl": ("utr5_mrl", "maximize"),
    "utr3_stability": ("utr3_stability", "maximize"),
    "full_mfe_score": ("full_mfe_score", "maximize"),
    "target_cds_mfe": ("cds_mfe", "minimize"),
    "target_cds_cai": ("cds_cai", "maximize"),
}

# Keys the workflow's `reference_point` dict accepts directly; CDS objectives
# are sent as top-level target_cds_mfe / target_cds_cai params instead.
REFERENCE_POINT_KEYS = {"utr5_mrl", "utr3_stability", "full_mfe_score"}

FIXED_TRANSLATION_FIRST_CAI = 0.95


# --------------------------------------------------------------------------
# Pool construction (pure functions — unit-tested via --self-test)
# --------------------------------------------------------------------------

def pool_stats(values: list[float], direction: str) -> dict[str, float]:
    """Summarize one pool dimension.

    Returns raw ``min``/``median``/``max`` plus direction-aware ``best``
    (raw max for maximized dims, raw min = most negative for cds_mfe).
    """
    vals = [float(v) for v in values]
    if not vals:
        raise ValueError("empty pool dimension")
    stats = {
        "min": min(vals),
        "median": statistics.median(vals),
        "max": max(vals),
    }
    stats["best"] = stats["max"] if direction == "maximize" else stats["min"]
    return stats


def build_metric_pool(records: list[dict]) -> dict[str, dict[str, float]]:
    """Build per-dimension pool stats from Serial ablation records.

    Each record must carry a ``best`` dict with the BEST_SCORE_KEYS scores.
    Dimensions with no non-None values are absent from the result.
    """
    per_dim: dict[str, list[float]] = {dim: [] for dim in DIMENSIONS}
    for rec in records:
        best = rec.get("best") or {}
        for dim, (src_key, _direction) in DIMENSIONS.items():
            v = best.get(src_key)
            if v is None:
                continue
            per_dim[dim].append(float(v))
    return {
        dim: pool_stats(vals, DIMENSIONS[dim][1])
        for dim, vals in per_dim.items()
        if vals
    }


def build_reference_point(profile: str, pool: dict[str, dict[str, float]]) -> dict[str, float]:
    """Construct the semantic reference point for one steering profile.

    Args:
        profile: one of ``translation-first``, ``stability-first``, ``balanced``.
        pool: per-dimension stats from :func:`build_metric_pool`
            (must contain every dimension the profile needs).

    Returns:
        dict with semantic keys: a subset of ``utr5_mrl``, ``utr3_stability``,
        ``full_mfe_score`` plus always ``target_cds_mfe`` + ``target_cds_cai``
        (the workflow requires the CDS pair together).

    Raises:
        ValueError: unknown profile or a required pool dimension is missing.
    """
    def need(dim: str) -> dict[str, float]:
        if dim not in pool:
            raise ValueError(
                f"profile '{profile}' requires pool dimension '{dim}', "
                f"available: {sorted(pool)}"
            )
        return pool[dim]

    if profile == "translation-first":
        return {
            "utr5_mrl": need("utr5_mrl")["max"],
            "target_cds_cai": FIXED_TRANSLATION_FIRST_CAI,
            "target_cds_mfe": need("target_cds_mfe")["median"],
        }
    if profile == "stability-first":
        return {
            "full_mfe_score": need("full_mfe_score")["max"],
            "utr3_stability": need("utr3_stability")["max"],
            # minimization dim: "pool min (most negative)" = raw minimum
            "target_cds_mfe": need("target_cds_mfe")["min"],
            "target_cds_cai": need("target_cds_cai")["median"],
        }
    if profile == "balanced":
        # ≈ utopian: every dimension at its pool best. For cds_mfe
        # (minimize), best = raw min (most negative).
        return {
            "utr5_mrl": need("utr5_mrl")["best"],
            "utr3_stability": need("utr3_stability")["best"],
            "full_mfe_score": need("full_mfe_score")["best"],
            "target_cds_cai": need("target_cds_cai")["best"],
            "target_cds_mfe": need("target_cds_mfe")["best"],
        }
    raise ValueError(f"unknown profile: {profile!r} (choose from {PROFILES})")


def reference_point_to_params(ref: dict[str, float]) -> dict[str, object]:
    """Split a semantic reference point into workflow input params.

    ``utr5_mrl`` / ``utr3_stability`` / ``full_mfe_score`` go into the
    ``reference_point`` dict; ``target_cds_mfe`` / ``target_cds_cai`` become
    top-level params (the workflow converts them to ``cds_component``).
    """
    params: dict[str, object] = {}
    rp = {k: v for k, v in ref.items() if k in REFERENCE_POINT_KEYS}
    if rp:
        params["reference_point"] = rp
    if "target_cds_mfe" in ref:
        params["target_cds_mfe"] = ref["target_cds_mfe"]
    if "target_cds_cai" in ref:
        params["target_cds_cai"] = ref["target_cds_cai"]
    return params


# --------------------------------------------------------------------------
# Pool loading from ablation JSONL shards
# --------------------------------------------------------------------------

def load_serial_records(pool_jsonl: list[Path]) -> dict[str, list[dict]]:
    """Collect successful Serial (bmc_max_rounds=0) records per target.

    For the same job (target_id, rep) only the latest successful record is
    kept (files are read in order; later lines overwrite earlier ones).
    """
    latest: dict[str, dict[object, dict]] = {}
    for path in pool_jsonl:
        if not path.exists():
            print(f"WARNING: pool jsonl not found, skipped: {path}", flush=True)
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("bmc_max_rounds") != 0 or not r.get("success"):
                continue
            tid = r.get("target_id")
            if not tid:
                continue
            latest.setdefault(tid, {})[r.get("rep")] = r
    return {tid: list(jobs.values()) for tid, jobs in latest.items()}


def load_pool_json(path: Path) -> dict[str, dict[str, dict[str, float]]]:
    """Load a handmade pool file, overriding JSONL extraction.

    Format: ``{"<target_id>": {"<dim>": [values...] or scalar}}`` with dims
    from :data:`DIMENSIONS` (semantic keys, e.g. ``target_cds_mfe`` /
    ``target_cds_cai``).
    """
    raw = json.loads(path.read_text())
    pools: dict[str, dict[str, dict[str, float]]] = {}
    for tid, dims in raw.items():
        per_dim: dict[str, list[float]] = {}
        for dim, vals in dims.items():
            if dim not in DIMENSIONS:
                raise ValueError(f"pool json: unknown dimension {dim!r} for target {tid!r}")
            if isinstance(vals, (int, float)):
                vals = [vals]
            per_dim[dim] = [float(v) for v in vals]
        pools[tid] = {
            dim: pool_stats(vals, DIMENSIONS[dim][1]) for dim, vals in per_dim.items()
        }
    return pools


def build_pools(
    targets: list[str],
    pool_jsonl: list[Path],
    pool_json: Path | None,
) -> tuple[dict[str, dict[str, dict[str, float]]], list[str]]:
    """Return (pools per target, missing target ids)."""
    if pool_json is not None:
        pools = load_pool_json(pool_json)
    else:
        records = load_serial_records(pool_jsonl)
        pools = {tid: build_metric_pool(recs) for tid, recs in records.items()}
    missing = [t for t in targets if t not in pools or not pools[t]]
    return pools, missing


# --------------------------------------------------------------------------
# Resume helper
# --------------------------------------------------------------------------

def load_done_keys(output: Path) -> set[tuple]:
    done = set()
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("success"):
                done.add((r["target_id"], r["profile"], r["rep"]))
    return done


# --------------------------------------------------------------------------
# Job assembly
# --------------------------------------------------------------------------

def build_jobs(
    targets: list[str],
    profiles: list[str],
    reps: int,
    pools: dict[str, dict[str, dict[str, float]]],
) -> list[dict]:
    jobs = []
    for tid in targets:
        tf = TARGETS_DIR / f"{tid}.json"
        if not tf.exists():
            raise FileNotFoundError(f"target JSON not found: {tf}")
        meta = json.loads(tf.read_text())
        for profile in profiles:
            ref = build_reference_point(profile, pools[tid])
            for rep in range(reps):
                jobs.append({
                    "target_id": tid,
                    "meta": meta,
                    "profile": profile,
                    "rep": rep,
                    "reference_point": ref,
                })
    return jobs


def format_ref(ref: dict[str, float]) -> str:
    return json.dumps({k: round(v, 6) for k, v in ref.items()}, ensure_ascii=False)


# --------------------------------------------------------------------------
# Self test (pure functions only — no workflow runs)
# --------------------------------------------------------------------------

def _self_test() -> int:
    # Handmade pool: 3 serial reps worth of raw values per dimension.
    raw_pool = {
        "utr5_mrl": [4.0, 5.0, 6.0],
        "utr3_stability": [0.60, 0.70, 0.80],
        "full_mfe_score": [-0.30, -0.25, -0.20],
        "target_cds_mfe": [-500.0, -400.0, -300.0],  # more negative = better
        "target_cds_cai": [0.80, 0.85, 0.90],
    }
    pool = {
        dim: pool_stats(vals, DIMENSIONS[dim][1]) for dim, vals in raw_pool.items()
    }
    assert pool["target_cds_mfe"]["best"] == -500.0, pool["target_cds_mfe"]
    assert pool["utr5_mrl"]["best"] == 6.0

    tf = build_reference_point("translation-first", pool)
    assert tf == {
        "utr5_mrl": 6.0,
        "target_cds_cai": 0.95,
        "target_cds_mfe": -400.0,
    }, tf

    sf = build_reference_point("stability-first", pool)
    assert sf == {
        "full_mfe_score": -0.20,
        "utr3_stability": 0.80,
        "target_cds_mfe": -500.0,   # raw min = most negative
        "target_cds_cai": 0.85,
    }, sf

    bal = build_reference_point("balanced", pool)
    assert bal == {
        "utr5_mrl": 6.0,
        "utr3_stability": 0.80,
        "full_mfe_score": -0.20,
        "target_cds_cai": 0.90,
        "target_cds_mfe": -500.0,   # utopian for a minimization dim = raw min
    }, bal

    # Params split: only allowed keys land in reference_point; CDS pair goes
    # to top-level target_cds_mfe / target_cds_cai.
    params = reference_point_to_params(bal)
    assert params["reference_point"] == {
        "utr5_mrl": 6.0, "utr3_stability": 0.80, "full_mfe_score": -0.20,
    }, params
    assert params["target_cds_mfe"] == -500.0
    assert params["target_cds_cai"] == 0.90
    assert set(params["reference_point"]) <= REFERENCE_POINT_KEYS

    # Missing dimension -> clear error.
    try:
        build_reference_point("stability-first", {"utr3_stability": pool["utr3_stability"]})
    except ValueError as exc:
        assert "full_mfe_score" in str(exc), exc
    else:
        raise AssertionError("expected ValueError for missing pool dimension")

    # Unknown profile -> clear error.
    try:
        build_reference_point("nonsense", pool)
    except ValueError as exc:
        assert "unknown profile" in str(exc), exc
    else:
        raise AssertionError("expected ValueError for unknown profile")

    # build_metric_pool skips None values.
    recs = [
        {"best": {"utr5_mrl": 1.0, "cds_mfe": -100.0, "cds_cai": None}},
        {"best": {"utr5_mrl": 2.0, "cds_mfe": -200.0}},
    ]
    p2 = build_metric_pool(recs)
    assert p2["utr5_mrl"]["max"] == 2.0
    assert p2["target_cds_mfe"]["min"] == -200.0
    assert "target_cds_cai" not in p2

    print("self-test OK: profile construction, params split, pool stats all pass")
    return 0


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--targets", default=None,
                        help=f"comma-separated target ids (default: {','.join(DEFAULT_TARGETS)})")
    parser.add_argument("--profiles", default=None,
                        help=f"comma-separated profiles (default: {','.join(PROFILES)})")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None, help="max number of runs (after filtering)")
    parser.add_argument("--resume", action="store_true",
                        help="skip (target_id, profile, rep) already successful in the output file")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pool-jsonl", type=Path, nargs="*", default=None,
                        help="Serial ablation JSONL(s) to extract the pilot pool from "
                             "(default: fig3_type1_shard_a/b.jsonl that exist)")
    parser.add_argument("--pool-json", type=Path, default=None,
                        help="handmade pool JSON; overrides --pool-jsonl extraction")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the reference points and job list without running anything")
    parser.add_argument("--self-test", action="store_true",
                        help="run pure-function self tests and exit")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    targets = args.targets.split(",") if args.targets else list(DEFAULT_TARGETS)
    profiles = args.profiles.split(",") if args.profiles else list(PROFILES)
    unknown_profiles = set(profiles) - set(PROFILES)
    if unknown_profiles:
        print(f"ERROR: unknown profiles {sorted(unknown_profiles)}; choose from {PROFILES}")
        return 2

    pool_jsonl = args.pool_jsonl
    if pool_jsonl is None:
        pool_jsonl = [p for p in DEFAULT_POOL_JSONL if p.exists()]

    pools, missing = build_pools(targets, pool_jsonl, args.pool_json)
    if missing:
        src = str(args.pool_json) if args.pool_json else ", ".join(str(p) for p in pool_jsonl)
        print(
            f"ERROR: no Serial pilot pool data for target(s): {missing}.\n"
            f"  Looked in: {src}\n"
            f"  The pool requires successful bmc_max_rounds=0 records for the target "
            f"(Fig-3 Type-I Serial arm). Either wait for the shard to finish, pass the "
            f"shard file containing them via --pool-jsonl, or provide a handmade pool "
            f"via --pool-json.",
            flush=True,
        )
        if not args.dry_run:
            return 1
        # dry-run: drop missing targets and continue with what we have
        targets = [t for t in targets if t not in missing]
        if not targets:
            return 1

    try:
        jobs = build_jobs(targets, profiles, args.reps, pools)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    done = load_done_keys(args.output) if args.resume else set()
    pending = [j for j in jobs if (j["target_id"], j["profile"], j["rep"]) not in done]
    if args.limit:
        pending = pending[: args.limit]

    print(f"Pool summary per target (from {'pool-json' if args.pool_json else 'jsonl extraction'}):")
    for tid in targets:
        print(f"  {tid}:")
        for dim, stats in sorted(pools[tid].items()):
            print(f"    {dim:16s} min={stats['min']:.6g} median={stats['median']:.6g} "
                  f"max={stats['max']:.6g} best={stats['best']:.6g}")
    print(f"\nReference points ({len(targets)} targets x {len(profiles)} profiles):")
    for tid in targets:
        for profile in profiles:
            ref = build_reference_point(profile, pools[tid])
            print(f"  {tid} / {profile}: {format_ref(ref)}")
            print(f"      -> workflow params: {json.dumps(reference_point_to_params(ref), default=str)}")

    print(f"\nJobs: {len(pending)} pending / {len(jobs)} total (reps={args.reps}):")
    for j in pending:
        print(f"  {j['target_id']} {j['profile']} rep{j['rep']}")

    if args.dry_run:
        print("\n--dry-run: nothing executed.")
        return 0

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    args.output.parent.mkdir(parents=True, exist_ok=True)

    n_ok = n_fail = 0
    for i, job in enumerate(pending, 1):
        meta = job["meta"]
        ref = job["reference_point"]
        params = {
            "protein_sequence": meta["protein_sequence"].upper(),
            "design_tool": "all",
            "lambda_value": 2.0,
            "cai_species": meta.get("species_for_codon_optimization") or "human",
            "utr_mode": "all",
            "bmc_max_rounds": 1,
            "bmc_improvement_threshold": 0.05,
        }
        params.update(reference_point_to_params(ref))
        task = {
            "task_id": f"steer_{job['target_id']}_{job['profile']}_rep{job['rep']}",
            "workflow": "full_length_mrna_design",
            "category": "reference_point_steering",
            "description": f"{job['target_id']} {job['profile']} rep{job['rep']}",
            "input": params,
            "evaluation_rubric": None,
        }
        print(f"[{i}/{len(pending)}] {job['target_id']} {job['profile']} rep={job['rep']} ...", flush=True)
        rec = run_task_dict(task, timeout=args.timeout, env=env, session_prefix="fig3steer")
        best = rec.get("best_candidate") or {}
        best_scores = best.get("scores") or {}
        out = {
            "target_id": job["target_id"],
            "profile": job["profile"],
            "rep": job["rep"],
            "reference_point": ref,
            "success": rec["success"],
            "error": rec.get("error"),
            "elapsed_seconds": rec.get("elapsed_seconds"),
            "best": {k: best_scores.get(k) for k in BEST_SCORE_KEYS},
            "bmc_trace": rec.get("bmc_trace"),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
        if rec["success"]:
            n_ok += 1
        else:
            n_fail += 1
        print(f"      -> {'OK' if rec['success'] else 'FAIL(' + str(rec.get('error')) + ')'} "
              f"in {rec.get('elapsed_seconds', 0):.0f}s, asf={best_scores.get('asf_distance')}", flush=True)

    print(f"\nDone: {n_ok} ok, {n_fail} failed -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
