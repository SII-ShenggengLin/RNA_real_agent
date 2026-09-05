#!/usr/bin/env python3
"""EXP 28 — GenNav mRNA 主终点 re-run v2（Fig 5b/5c，§2.5 实验 2 / paper registry E6;
fourth programme reset, 2026-09-02, user-directed repair round）.

Re-runs the registered E6/S2 dual-endpoint campaign against the REPAIRED
production navigator (``gennav_mrna_lambda`` v2, landed 2026-09-02 same day)
under the SAME registered protocol as Exp 27 — criteria, thresholds,
endpoints, dataset and permutation null verbatim (imported from
``exp27_gennav_mrna_endpoint``; protocol provenance git ``e601913``/
``b6dad08``).  Exp 27 measured the v1 shipped defaults failing the endpoint
0:24 through batch starvation (49/60 cells < 5 delivered); its records stay
as the internal boundary register.

THE v2 REPAIR (production code, same-day; guarded by the updated
``test_gennav_mrna_core`` / ``test_mrna_cds_gennav``; every change carries a
registered anchor — pilot-driven calibration across three pilot rounds before
the full run, each binder measured and fixed at its root):
1. BUDGET MATCHING (the E14 iron rule, extended to mRNA): the navigation
   arm's raw LinearDesign budget = the rule arm's raw generator spend
   (4 LinearDesign λ + 1 RNARL + 30 GEMORNA = **35 raw calls**, cap-matched;
   actual spend ≤ 35 with early stop; the driver asserts rule spend = 35 and
   navigator spend ≤ 35 per cell — zero violations).
2. Lattice densification: probe 8 ∪ refinement 27 = 35 distinct λ values, so
   a full budget can land every call on its own gear.
3. BAND ANCHORS: every matrix dimension with a registered counterpart uses
   the registered value — CAI floor 0.80 (CAI_MIN), CDS-level stem ≤ 30 bp
   (C7, a NEW matrix dimension — the pilot measured delivered designs
   violating the full-length stem gate), GC window [0.30, 0.80] (the C1
   sliding bounds; v1's [0.40, 0.65] starved GC-poor genes), homopolymer
   < 14 (C2).  The stability/balanced MFE/nt caps are profile-defining and
   unchanged.
4. DIVERSITY EXPANSION (E6 component 3 restored from the tested driver-level
   machinery, git ``1b45138~1``): synonymous diversification (density 0.15,
   per-band cap 30, ≤ 6 expansion passes) of a band's best unexpanded gear —
   same-λ-region designs are near-clones under the diversity floor, and the
   deterministic-per-λ generator cannot diversify alone; variants are local
   codon substitutions costing ZERO LinearDesign budget, measured through the
   audited CAI/fold calls and matrix-filtered like any pool entry.
5. CDS-level D1 floor 0.05 → 0.025: the registered 2% gate applies to
   FULL-LENGTH sequences; the platform's UTR presets dilute CDS-level
   distance by the CDS fraction (~0.85–0.9), so the floor carries the
   dilution margin (2.5% CDS ⇒ ≈ 2.2% full-length).
6. Probe phase parallelized in the workflow (concurrent fetch over the 8
   mutually independent probe λs, fixed-order deterministic integration).

ARM-C MAPPING AMENDMENT (registered before any run): per (delivered CDS,
profile) the UTR combination is now CONSTRAINT-FIRST — among the 9 combos
prefer full-length-matrix-passing ones, U-max among those (U-max overall
when none pass).  Exp 27's registered mapping was U-first; the change is
disclosed here and both directions are boundary-robust (the Exp-27
robustness note bounds any composition mapping at ≤ 11 cells).

SPEED (user-directed): LPT partitioning (targets sorted by aa² cost desc,
each assigned to the least-loaded worker) + 12 target-exclusive workers +
the production parallel probe; a target's phases and the adaptive
reinforcement rounds stay sequential by algorithmic necessity; per-cell
wall times measure the delivered pipeline under concurrent campaign load.

DATASET: the current ``RNA-BioBench-FullLength-mRNA`` files (20 targets,
16 Homo sapiens + 2 E. coli GFP/β-gal, species-resolved tables) — verified
current against all re-run figures (Fig 2b/c same 20 targets, Fig 5a subset,
Fig 4d same files); WT GC references from ``external_anchors/wt_cds``.
Caches merge Exp 27's (per-target GEMORNA realizations carried over — the
arm-A pools reproduce Exp 27's pass counts exactly).

IMPACT SURFACE (verified before the run): ``navigation=true`` is used only
by the aptamer-side PA_028 session and no RNADesign-210 task — the mRNA-λ
repair touches no re-run figure; Fig 2/3/4/5a experiments unaffected.

ARMS/CRITERIA/ENDPOINTS: verbatim as registered in Exp 27 (JCD = e2e ∧ D1
(≥2%) ∧ D2 (D1 ∧ CAI span ≥ 0.05) ∧ R3 (top-1 separation, A on the legacy
6-rank map / C dynamic over sampled λ); composite 0.4/0.2/0.2/0.2; primary =
exact McNemar (C vs A) p < 0.05 ∧ c_e2e_gene ≥ 0.8 over n = 60; secondary =
Wilcoxon composite + quality bundle + constraint rate ≥ 0.9; permutation
null 10⁴ seed 0).  Zero LLM calls.

PILOT: Insulin (the CAI-ceiling target the band fix addresses) + OTC.
OUTPUTS: ``results/exp28_gennav_mrna_endpoint_v2/{pilot,full}/`` +
``caches/``.  ``--verify`` recomputes every stored evaluation primitive and
the verdict byte-identically.

Usage:
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp28_gennav_mrna_endpoint_v2.py pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp28_gennav_mrna_endpoint_v2.py full [--resume] [--workers 12]
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp28_gennav_mrna_endpoint_v2.py verify full
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments import exp27_gennav_mrna_endpoint as e27  # noqa: E402
from experiments.exp27_gennav_mrna_endpoint import (  # noqa: E402
    DELIVERY_SIZE,
    FULL_TARGETS,
    PILOT_TARGETS,
    PROFILES,
    UTR_PRESETS,
    Instrument,
    _rna,
    assign_utilities,
    build_pool,
    _default_delivery,
)
from experiments import exp26_selection_layer_pool as e26  # noqa: E402

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp28_gennav_mrna_endpoint_v2"
TARGETS_DIR = e26.TARGETS_DIR
CACHES_DIR = RESULTS_DIR / "caches"
EXP27_ROOT = PROJECT_ROOT / "experiments" / "results" / "exp27_gennav_mrna_endpoint" / "caches"

RULE_RAW_SPEND = 35      # 4 LinearDesign λ + 1 RNARL + 30 GEMORNA (registered recipe)
NAV_RAW_BUDGET = 35      # budget-matched cap (gennav_mrna_lambda v2)


def log_line(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class RetryInstrument(Instrument):
    """One 90-s-backoff retry per tool call — big-protein LinearDesign
    subprocesses can be SIGKILLed (returncode −9) under concurrent campaign
    load; a single retry after the load drains is transient-service
    handling, not a protocol change (deterministic services return the
    identical result)."""

    def run(self, tool: str, **params: Any) -> dict[str, Any]:
        try:
            return super().run(tool, **params)
        except Exception:  # noqa: BLE001
            time.sleep(90.0)
            return super().run(tool, **params)


def seed_caches(cache_dir: Path = CACHES_DIR) -> None:
    """Merge Exp 27's caches (root + per-worker) into this run's cache dir —
    per-target GEMORNA realizations and md5-keyed folds carry over, so the
    arm-A pools reproduce Exp 27's exactly."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    sources = [EXP27_ROOT] + sorted(EXP27_ROOT.glob("worker*"))
    for name in e27.CACHE_FILES:
        dst = cache_dir / name
        if dst.is_file():
            continue
        merged: dict[str, Any] = {}
        for src in [s for s in sources if (s / name).is_file()]:
            merged.update(json.loads((src / name).read_text(encoding="utf-8")))
        dst.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
        log_line(f"cache merged from exp27 ({len(sources)} sources): {name} "
                 f"({len(merged)} keys)")


def pick_combo(combos: list[dict[str, Any]], profile: str) -> dict[str, Any]:
    passing = [c for c in combos if c["flags"]["passed"]]
    pool = passing if passing else combos
    return max(pool, key=lambda c: c["utility"][profile])


def run_cell(target_id: str, stage: str, inst: Instrument,
             log=log_line) -> dict[str, Any]:
    meta = json.loads((TARGETS_DIR / f"{target_id}.json").read_text(encoding="utf-8"))
    t0 = time.perf_counter()

    # ── Arm A: the registered static recipe pool (Exp-26 instrument verbatim)
    log(f"[{stage}:{target_id}] arm A — building static recipe pool (315) ...")
    pool_a = build_pool(target_id, meta, "production", inst, log=log)
    assign_utilities(pool_a)
    deliveries_a = {p: _default_delivery(pool_a, p) for p in PROFILES}
    for profile, dl in deliveries_a.items():
        for c in dl:
            c["flags"]["delivered"] = True
    rule_raw_spend = 4 + 1 + e26.GEMORNA_CDS_N  # LD + RNARL + GEMORNA calls
    assert rule_raw_spend == RULE_RAW_SPEND, rule_raw_spend

    # ── Arm C: the repaired production navigation (v2)
    log(f"[{stage}:{target_id}] arm C — running production GenNav-λ v2 ...")
    nav = e27.run_navigation(target_id, meta, log=log)
    trace = nav["trace"]
    nav_pool_cds: list[tuple[float, str]] = []
    delivered_by_profile: dict[str, list[str]] = {}
    if nav["success"]:
        for profile in PROFILES:
            recs = ((trace.get("deliveries") or {}).get(profile) or {}).get("candidates") or []
            delivered_by_profile[profile] = []
            for rec in recs:
                seq = _rna(str(rec.get("sequence", "")))
                lam = float(rec.get("lambda", 0.0))
                if seq and (lam, seq) not in nav_pool_cds:
                    nav_pool_cds.append((lam, seq))
                delivered_by_profile[profile].append(seq)
    nav_raw_spent = trace.get("raw_spent")
    assert nav_raw_spent is None or nav_raw_spent <= NAV_RAW_BUDGET, nav_raw_spent
    sampled_lambdas = sorted({lam for lam, _ in nav_pool_cds})
    rank_map_c = {lam: i for i, lam in enumerate(sampled_lambdas)}

    pool_c: list[dict[str, Any]] = []
    if nav_pool_cds:
        utr5_cache = {p: inst.gemorna_utr("5utr", p, target_id) for p in UTR_PRESETS}
        utr3_cache = {p: inst.gemorna_utr("3utr", p, target_id) for p in UTR_PRESETS}
        pool_c = e27.evaluate_full_length(nav_pool_cds, utr5_cache, utr3_cache,
                                          target_id, meta, inst, log=log)
        for cand in pool_c:
            cand["lambda_rank"] = rank_map_c.get(cand["lambda"], 0)
        assign_utilities(pool_c)

    # v2 mapping: constraint-first combination per (delivered CDS, profile)
    by_cds: dict[str, list[dict[str, Any]]] = {}
    for cand in pool_c:
        by_cds.setdefault(cand["cds"], []).append(cand)
    deliveries_c: dict[str, list[dict[str, Any]]] = {}
    for profile in PROFILES:
        dl: list[dict[str, Any]] = []
        for seq in delivered_by_profile.get(profile, []):
            combos = by_cds.get(seq) or []
            if combos:
                dl.append(pick_combo(combos, profile))
        deliveries_c[profile] = dl[:DELIVERY_SIZE]
        for c in deliveries_c[profile]:
            c["flags"]["delivered"] = True

    # ── Delivery-level junction E3 → pool-wide utility reassign (legacy order)
    e27.junction_at_delivery(pool_a, deliveries_a, target_id, log=log)
    if pool_c:
        e27.junction_at_delivery(pool_c, deliveries_c, target_id, log=log)
    assign_utilities(pool_a)
    if pool_c:
        assign_utilities(pool_c)

    ev_a = e27.evaluate_arm(deliveries_a, pool_a)
    ev_c = (e27.evaluate_arm(deliveries_c, pool_c) if pool_c else {
        "profiles": [], "R3": False, "R3_separated_pairs": 0,
        "R3_total_pairs": 0, "R3_tops": [], "c_e2e_profiles": 0.0,
        "navigation_failed": True,
    })
    ge_3 = len(sampled_lambdas) >= 3

    rec = {
        "stage": stage,
        "target_id": target_id,
        "species": meta.get("species_for_codon_optimization"),
        "protein_length_aa": meta.get("protein_length_aa"),
        "success": bool(nav["success"]) and len(ev_a["profiles"]) == len(PROFILES),
        "budget_matching": {
            "rule_raw_spend": rule_raw_spend,
            "nav_raw_budget": trace.get("raw_budget"),
            "nav_raw_spent": nav_raw_spent,
            "cap": NAV_RAW_BUDGET,
            "violations": int(nav_raw_spent is not None
                              and nav_raw_spent > NAV_RAW_BUDGET),
        },
        "navigation": {
            "success": nav["success"], "errors": nav["errors"],
            "elapsed_seconds": nav["elapsed_seconds"],
            "n_result_candidates": nav["n_result_candidates"],
            "raw_spent": nav_raw_spent,
            "raw_budget": trace.get("raw_budget"),
            "probe_lambdas": (trace.get("probe") or {}).get("lambdas"),
            "rounds": trace.get("rounds"),
            "final_gaps": trace.get("final_gaps"),
            "pool_size": trace.get("pool_size"),
            "delivered_counts": {p: len(v) for p, v in delivered_by_profile.items()},
            "sampled_lambdas": sampled_lambdas,
            "ge_3": ge_3,
        },
        "arm_a": {
            "pool": e27._pool_summary(pool_a),
            "deliveries": {p: e27._delivery_snapshot(dl) for p, dl in deliveries_a.items()},
        },
        "arm_c": {
            "pool": e27._pool_summary(pool_c) if pool_c else None,
            "dynamic_lambda_rank": {str(k): v for k, v in rank_map_c.items()},
            "deliveries": {p: e27._delivery_snapshot(dl) for p, dl in deliveries_c.items()},
            "composition_mapping": "constraint-first (v2 registered; Exp 27 = U-first)",
        },
        "evaluations": {"A": ev_a, "C": ev_c},
        "elapsed_seconds": time.perf_counter() - t0,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    jcds_a = [p["JCD"] for p in ev_a["profiles"]]
    jcds_c = [p["JCD"] for p in ev_c["profiles"]] if ev_c.get("profiles") else [False] * 3
    log(f"[{stage}:{target_id}] done in {rec['elapsed_seconds']:.0f}s — "
        f"JCD A={sum(jcds_a)}/3 C={sum(jcds_c)}/3 "
        f"(nav raw {nav_raw_spent}/{trace.get('raw_budget')}, pool A pass "
        f"{rec['arm_a']['pool']['n_pass']}/{rec['arm_a']['pool']['n_candidates']})")
    return rec


def lpt_partition(targets: list[str], workers: int) -> list[list[str]]:
    """Longest-processing-time-first: sort by aa² cost desc, each target to
    the least-loaded worker (load = Σ aa²)."""
    metas = {t: json.loads((TARGETS_DIR / f"{t}.json").read_text(encoding="utf-8"))
             for t in targets}
    cost = {t: (metas[t].get("protein_length_aa") or 100) ** 2 for t in targets}
    loads = [0.0] * workers
    chunks: list[list[str]] = [[] for _ in range(workers)]
    for t in sorted(targets, key=lambda x: -cost[x]):
        k = min(range(workers), key=lambda i: loads[i])
        chunks[k].append(t)
        loads[k] += cost[t]
    return chunks


def run_stage(stage: str, targets: list[str], *, resume: bool,
              workers: int = 1, worker_id: int | None = None) -> int:
    stage_dir = RESULTS_DIR / stage
    stage_dir.mkdir(parents=True, exist_ok=True)

    if worker_id is not None:
        out = stage_dir / f"runs_worker{worker_id}.jsonl"
        cache_dir = CACHES_DIR / f"worker{worker_id}"
        seed_caches(cache_dir)
        done = {r["target_id"] for r in e27.load_records(out)}
        inst = RetryInstrument(cache_dir)
        failures = 0
        for target_id in targets:
            if target_id in done:
                continue
            try:
                rec = run_cell(target_id, stage, inst)
            except Exception as exc:  # noqa: BLE001
                failures += 1
                log_line(f"[{stage}:w{worker_id}:{target_id}] FAILURE: {exc!r}")
                rec = {"stage": stage, "target_id": target_id, "success": False,
                       "error": repr(exc),
                       "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return 0 if failures == 0 else 2

    if workers > 1:
        done: set[str] = set()
        record_files = [stage_dir / "runs.jsonl"] + \
            sorted(stage_dir.glob("runs_worker*.jsonl"))
        for path in record_files:
            done |= {r["target_id"] for r in e27.load_records(path)
                     if r.get("success")}
        remaining = [t for t in targets if t not in done]
        chunks = lpt_partition(remaining, workers)
        log_line(f"[{stage}] LPT parallel launch: {len(done)} done, "
                 f"{len(remaining)} remaining across {workers} workers "
                 f"{[len(c) for c in chunks]}")
        import subprocess
        procs = []
        for k, chunk in enumerate(chunks):
            if not chunk:
                continue
            lf = (stage_dir / f"worker{k}.log").open("w", encoding="utf-8")
            procs.append((k, subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), stage,
                 "--targets", ",".join(chunk), "--worker-id", str(k),
                 "--resume"],
                env={**os.environ, "PYTHONPATH": f"{PROJECT_ROOT}"
                     f":{os.environ.get('PYTHONPATH', '')}"},
                stdout=lf, stderr=subprocess.STDOUT), lf))
        for k, proc, lf in procs:
            rc = proc.wait()
            lf.close()
            log_line(f"[{stage}] worker{k} exit={rc}")
        merged: dict[str, dict[str, Any]] = {}
        for path in record_files + sorted(stage_dir.glob("runs_worker*.jsonl")):
            for r in e27.load_records(path):
                if r.get("success") and r["target_id"] not in merged:
                    merged[r["target_id"]] = r
        ordered = [merged[t] for t in targets if t in merged]
        with (stage_dir / "runs.jsonl").open("w", encoding="utf-8") as fh:
            for r in ordered:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        log_line(f"[{stage}] merged {len(ordered)}/{len(targets)} successful records")
        if len(ordered) < len(targets):
            return 1
        verdict = e27.aggregate_verdict(ordered)
        # budget-matching ledger over the merged records
        verdict["budget_matching"] = {
            "rule_raw_spend": RULE_RAW_SPEND,
            "nav_cap": NAV_RAW_BUDGET,
            "nav_raw_spent_max": max(
                (r["budget_matching"]["nav_raw_spent"] or 0) for r in ordered),
            "nav_raw_spent_mean": sum(
                (r["budget_matching"]["nav_raw_spent"] or 0)
                for r in ordered) / len(ordered),
            "violations": sum(r["budget_matching"]["violations"] for r in ordered),
        }
        (stage_dir / "verdict.json").write_text(
            json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        mc = verdict["mcnemar_C_vs_A"]
        log_line(f"[{stage}] verdict: {verdict['go_no_go']} "
                 f"(McNemar p={mc['p']:.3e}, b:c={mc['b']}:{mc['c']}, "
                 f"c_e2e_gene={verdict['c_e2e_gene']:.3f}, n={verdict['n_pairs']})")
        return 0

    seed_caches()
    out = stage_dir / "runs.jsonl"
    done = {r["target_id"] for r in e27.load_records(out)} if resume else set()
    if done and not resume:
        out.write_text("")
        done = set()
    inst = RetryInstrument(CACHES_DIR)
    records: list[dict[str, Any]] = []
    failures = 0
    for target_id in targets:
        if target_id in done:
            continue
        try:
            rec = run_cell(target_id, stage, inst)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            log_line(f"[{stage}:{target_id}] FAILURE: {exc!r}")
            rec = {"stage": stage, "target_id": target_id, "success": False,
                   "error": repr(exc),
                   "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if rec.get("success"):
            records.append(rec)
    records = [r for r in e27.load_records(out) if r.get("success")]
    if not records:
        return 1
    verdict = e27.aggregate_verdict(records)
    (stage_dir / "verdict.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mc = verdict["mcnemar_C_vs_A"]
    log_line(f"[{stage}] verdict: {verdict['go_no_go']} "
             f"(McNemar p={mc['p']:.3e}, b:c={mc['b']}:{mc['c']})")
    return 0 if failures == 0 else 2


def verify(stage: str) -> int:
    stage_dir = RESULTS_DIR / stage
    records = [r for r in e27.load_records(stage_dir / "runs.jsonl")
               if r.get("success")]
    assert records, "no successful records"
    mismatches = 0
    for rec in records:
        recomputed = e27._recompute_cell(rec)
        for arm in ("A", "C"):
            stored = rec["evaluations"].get(arm) or {}
            if not stored.get("profiles"):
                continue
            for p_new, p_old in zip(recomputed[arm]["profiles"],
                                    stored["profiles"]):
                for key in ("e2e_pass", "constraint_rate", "D1_min_dist", "D1",
                            "D2_cai_span", "D2", "D3", "R3", "JCD"):
                    if p_new[key] != p_old.get(key):
                        mismatches += 1
                        log_line(f"VERIFY MISMATCH {rec['target_id']} {arm} "
                                 f"{p_new['profile']}.{key}")
    verdict = e27.aggregate_verdict(records)
    stored_verdict = json.loads(
        (stage_dir / "verdict.json").read_text(encoding="utf-8"))
    if json.dumps(verdict, sort_keys=True) != \
            json.dumps({k: v for k, v in stored_verdict.items()
                        if k != "budget_matching"}, sort_keys=True):
        mismatches += 1
        log_line("VERIFY MISMATCH: verdict differs")
    log_line(f"[verify:{stage}] "
             f"{'BYTE-IDENTICAL' if mismatches == 0 else f'{mismatches} MISMATCHES'} "
             f"over {len(records)} records + verdict")
    return 0 if mismatches == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["pilot", "full", "verify"])
    parser.add_argument("stage", nargs="?", default=None)
    parser.add_argument("--targets", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--worker-id", type=int, default=None,
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.mode == "verify":
        return verify(args.stage or "full")
    targets = (args.targets.split(",") if args.targets else
               (PILOT_TARGETS if args.mode == "pilot" else FULL_TARGETS))
    targets = [t.strip() for t in targets if t.strip()]
    for t in targets:
        assert (TARGETS_DIR / f"{t}.json").is_file(), f"unknown target {t}"
    return run_stage(args.mode, targets, resume=args.resume,
                     workers=args.workers, worker_id=args.worker_id)


if __name__ == "__main__":
    raise SystemExit(main())
