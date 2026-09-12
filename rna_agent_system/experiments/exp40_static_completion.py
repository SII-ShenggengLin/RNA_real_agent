#!/usr/bin/env python3
"""EXP 40 — Static-arm completion on the Exp-30 deployment targets + the
pooled 25/26-target two-arm analysis (user-directed merge, 2026-09-12;
§2.5 revision batch 5).

WHY: the paper's deployment-validation paragraph (Fig. 5h, Exp 30) ran the
NAVIGATION arm only on 11 new targets through the user-form production entry
— no static comparison arm exists for them.  The user-directed revision folds
those targets into the main results (mRNA 20 + 5 = 25 targets; aptamer 20 + 6
= 26 targets), which requires completing the missing static arm under the
identical budget-matched protocols, then pooling.

ARMS (the static sides; navigation sides are NOT re-run — frozen verbatim):
- mRNA static arm (5 targets: PTH, LEP, CSF3, THPO, PLAT — the Exp-30
  curated list, ``curated_mrna_targets.json``, status USER_CONFIRMED): the
  Exp-28 instrument verbatim — ``build_pool`` = 4 LinearDesign λ{0,1,4,10} +
  1 RNARL + 30 GEMORNA CDS samples = 35 raw calls × 9 GEMORNA UTR presets =
  315 full-length constructs per target, hard matrix C1/C2/C6/C7/M1/CAI,
  per-profile ``_default_delivery`` rule deliveries (λ-pref top-1, cross-λ
  spread, U fill).  Rule raw spend asserted exactly 35.
- mRNA navigation side: the frozen Exp-30 form-session ``_gennav_trace``
  (per-profile delivered CDS + λ) loaded from the session's saved
  ``workflow_results_*.json``; composed with the SAME per-target 9 UTR
  presets and evaluated under the identical full-length matrix / archive /
  utility stack as Exp 28 (constraint-first combination mapping, the
  registered v2 amendment).  The Exp-30 sessions ran the production
  ``mrna_cds_design(navigation=True)`` shipped mode at the 35-raw cap.
- aptamer static arm (6 targets: Angiopoietin-2, FGF2, IFN-gamma, IL-17A,
  PDGF-BB, Influenza H3N2 (swine) HA — the Exp-30 anchor-fasta list): the
  Exp-29 ``static_grid`` verbatim — six fixed gears (30,42,8)(30,123,8)
  (47,42,8)(47,123,8)(70,42,8)(70,123,8) = exactly 48 raw, matrix v3
  (production scarcity), the SAME structure file the paired Exp-30 session
  used (the 2026-09-05 fold-reuse resolver; ``structure_reused`` echoed per
  record) and the deterministic auto-hotspot from it.  Static raw spend
  asserted exactly 48.
- aptamer navigation side: the frozen Exp-30 ``cells_pass`` per profile
  (5/5 post-D1 non-degraded delivery — the identical cell definition as the
  Exp-29 segments), echoed verbatim with session provenance.

PROTOCOL DISCLOSURE (registered before any run): the Exp-30 aptamer
navigation runs span two shipped-navigator vintages by run date — FGF2,
Angiopoietin-2 and IFN-gamma ran the pre-2026-09-05 shipped mode
(``e14_production_v1``), IL-17A, PDGF-BB and swine H3 HA the current one
(``e14_production_v4``); each run used the then-current shipped production
mode (that is what production deployment validates) and the vintage is
echoed per record.  The static grid is vintage-free.  Per DECISIONS (i) the
aptamer pooled statistic is a SUMMARY over the pooled cohorts — the
registered 20-pool endpoint verdicts (seg3/seg4, frozen) remain the
inferential backbone and are reported alongside; nothing here re-opens the
aptamer primary endpoint.

POOLED ANALYSIS (pre-registered):
- mRNA, n = 75 pairs = 25 targets × 3 profiles (expression/stability/
  balanced): exact McNemar on JCD pass/fail (C vs A) + the registered
  secondary bundle (gene-level e2e conjunct, constraint rate ≥ 0.9,
  composite Wilcoxon, permutation null 10⁴ seed 0) via the Exp-27 verdict
  machinery verbatim; cohort split disclosed (the frozen Exp-28 20-target
  registered cohort verdict unchanged; the 5-target deployment cohort
  reported alongside).  Budget ledger over 25 targets.
- aptamer, n = 78 cells = 26 targets × 3 profiles (compact/standard/
  extended): pooled delivered cells per arm, pooled exact McNemar on the
  discordant cells, e2e target counts, spend stats; cohort split disclosed
  (frozen seg3 36 + seg4 24 + deployment 18).
- secondary panel data (the Fig-5d successor) over the 75 mRNA pairs:
  composite Δ sign counts + Wilcoxon p, gene-e2e value, constraint rate,
  budget ledger — written to ``pooled/mrna_secondary_panel.json``.

PILOT (PTH + FGF2, one target per side): both static arms complete, budget
assertions hold (35 / 48 exactly), records verifiable, pooled machinery
runs.  Full run only after pilot gates pass.

PARALLELIZATION (user-directed 2026-09-12): all CPUs + GPU 0 only.
mRNA: target-exclusive workers (the Exp-28 convention; per-worker caches,
no write races).  aptamer: concurrent gear fetches (EXP29_FETCH_POOL)
against the resident ODesign replica fleet on GPU 0
(EXP29_ODESIGN_URLS round-robin steering, the Exp-29 convention).

Zero LLM calls.  ``--verify`` recomputes every stored evaluation primitive
and every verdict (cohort + pooled) byte-identically from the stored
records.

OUTPUTS: ``results/exp40_static_completion/{mrna,aptamer}/runs.jsonl`` +
``{mrna,aptamer}/verdict.json`` (deployment-cohort verdicts) +
``pooled/{mrna_pooled_verdict.json, aptamer_pooled_verdict.json,
mrna_secondary_panel.json}`` + ``targets_mrna/`` (the five curated target
JSONs, written from the Exp-30 curation verbatim) + ``caches/``.

Usage:
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp40_static_completion.py pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp40_static_completion.py full-mrna [--workers 5]
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp40_static_completion.py full-aptamer [--threads 3]
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp40_static_completion.py pool
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp40_static_completion.py verify [mrna|aptamer|pool|all]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any, Optional

os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments import exp26_selection_layer_pool as e26  # noqa: E402
from experiments.exp26_selection_layer_pool import (  # noqa: E402
    PROFILES,
    UTR_PRESETS,
    Instrument,
    _default_delivery,
    _rna,
    assign_utilities,
    build_pool,
)
from experiments import exp27_gennav_mrna_endpoint as e27  # noqa: E402
from experiments import exp29_aptamer_campaign_arc as e29  # noqa: E402
from experiments import exp30_production_navigation_live as e30  # noqa: E402
from experiments.exp28_gennav_mrna_endpoint_v2 import (  # noqa: E402
    NAV_RAW_BUDGET,
    RULE_RAW_SPEND,
    RetryInstrument,
    pick_combo,
)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp40_static_completion"
MRNA_DIR = RESULTS_DIR / "mrna"
APT_DIR = RESULTS_DIR / "aptamer"
POOLED_DIR = RESULTS_DIR / "pooled"
TARGETS_MRNA_DIR = RESULTS_DIR / "targets_mrna"
MRNA_CACHES = RESULTS_DIR / "caches" / "mrna"
APT_CACHES = RESULTS_DIR / "caches" / "aptamer"

EXP28_FULL = (PROJECT_ROOT / "experiments" / "results"
              / "exp28_gennav_mrna_endpoint_v2" / "full")
EXP29_ROOT = PROJECT_ROOT / "experiments" / "results" / "exp29_aptamer_campaign_arc"
EXP30_ROOT = PROJECT_ROOT / "experiments" / "results" / "exp30_production_navigation_live"

APTAMER_SEGMENTS = ("seg3_decisive", "seg4_confirmation")


def log_line(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ── target registration ─────────────────────────────────────────────────────

def mrna_targets() -> list[dict[str, Any]]:
    """The five curated Exp-30 deployment targets, written once as
    benchmark-schema JSONs (sequence verbatim from the USER_CONFIRMED
    curation; no new curation happens here)."""
    doc = json.loads((EXP30_ROOT / "curated_mrna_targets.json")
                     .read_text(encoding="utf-8"))
    assert doc.get("status") == "USER_CONFIRMED", doc.get("status")
    TARGETS_MRNA_DIR.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    for t in doc["targets"]:
        path = TARGETS_MRNA_DIR / f"{t['gene']}.json"
        meta = {
            "target_id": t["gene"],
            "target_name": t["display"],
            "target_type": "therapeutic",
            "source_database": "UniProt",
            "accession": t["uniprot"],
            "species_for_codon_optimization": t["species_for_codon_optimization"],
            "protein_sequence": t["protein_sequence"],
            "protein_length_aa": t["protein_length_aa"],
            "provenance": ("Exp-30 curated deployment target (USER_CONFIRMED "
                           f"{doc['created']}); Exp-40 static-arm completion"),
        }
        if not path.is_file():
            path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        out.append(json.loads(path.read_text(encoding="utf-8")))
    return out


def load_exp30_records(stage: str) -> dict[str, dict[str, Any]]:
    recs = [json.loads(ln) for ln
            in (EXP30_ROOT / stage / "runs.jsonl").read_text(
                encoding="utf-8").splitlines() if ln.strip()]
    return {r["target_id"]: r for r in recs}


# ── mRNA side: static arm + evaluation of the frozen navigation trace ───────

def run_mrna_cell(target_id: str, stage: str, inst: Instrument,
                  log=log_line) -> dict[str, Any]:
    meta = json.loads((TARGETS_MRNA_DIR / f"{target_id}.json")
                      .read_text(encoding="utf-8"))
    exp30_rec = load_exp30_records("mrna")[target_id]
    wf_path = Path(exp30_rec["workflow_results_path"])
    assert wf_path.is_file(), f"missing exp30 workflow results: {wf_path}"
    t0 = time.perf_counter()

    # ── Arm A: the registered static recipe pool (Exp-26/28 instrument)
    log(f"[{stage}:{target_id}] arm A — building static recipe pool (315) ...")
    pool_a = build_pool(target_id, meta, "production", inst, log=log)
    assign_utilities(pool_a)
    deliveries_a = {p: _default_delivery(pool_a, p) for p in PROFILES}
    for profile, dl in deliveries_a.items():
        for c in dl:
            c["flags"]["delivered"] = True
    rule_raw_spend = 4 + 1 + e26.GEMORNA_CDS_N
    assert rule_raw_spend == RULE_RAW_SPEND, rule_raw_spend

    # ── Arm C: the FROZEN Exp-30 form-session navigation trace (no re-run)
    wf = json.loads(wf_path.read_text(encoding="utf-8"))
    trace = dict(wf.get("_gennav_trace") or {})
    assert trace.get("deliveries"), f"no gennav trace deliveries for {target_id}"
    log(f"[{stage}:{target_id}] arm C — frozen exp30 trace "
        f"(raw {trace.get('raw_spent')}/{trace.get('raw_budget')}, session "
        f"{exp30_rec['session_id']})")
    nav_pool_cds: list[tuple[float, str]] = []
    delivered_by_profile: dict[str, list[str]] = {}
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

    # constraint-first combination per (delivered CDS, profile) — v2 registered
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
        deliveries_c[profile] = dl[: e27.DELIVERY_SIZE]
        for c in deliveries_c[profile]:
            c["flags"]["delivered"] = True

    # delivery-level junction E3 → pool-wide utility reassign (legacy order)
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
        "success": len(ev_a["profiles"]) == len(PROFILES)
                   and len(ev_c["profiles"]) == len(PROFILES),
        "budget_matching": {
            "rule_raw_spend": rule_raw_spend,
            "nav_raw_budget": trace.get("raw_budget"),
            "nav_raw_spent": nav_raw_spent,
            "cap": NAV_RAW_BUDGET,
            "violations": int(nav_raw_spent is not None
                              and nav_raw_spent > NAV_RAW_BUDGET),
        },
        "navigation": {
            "success": bool(exp30_rec.get("success")),
            "errors": [],
            "elapsed_seconds": exp30_rec.get("elapsed_seconds"),
            "n_result_candidates": exp30_rec.get("pool_size"),
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
        "nav_source": {
            "experiment": "exp30_production_navigation_live",
            "entry": "user-form production CLI (one subprocess per session)",
            "session_id": exp30_rec["session_id"],
            "workflow_results_path": str(wf_path),
            "trace_protocol": trace.get("protocol"),
            "form_elapsed_seconds": exp30_rec.get("elapsed_seconds"),
            "workflow_cells_pass": exp30_rec.get("cells_pass"),
        },
        "elapsed_seconds": time.perf_counter() - t0,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    jcds_a = [p["JCD"] for p in ev_a["profiles"]]
    jcds_c = [p["JCD"] for p in ev_c["profiles"]]
    log(f"[{stage}:{target_id}] done in {rec['elapsed_seconds']:.0f}s — "
        f"JCD A={sum(jcds_a)}/3 C={sum(jcds_c)}/3 "
        f"(nav raw {nav_raw_spent}/{trace.get('raw_budget')}, pool A pass "
        f"{rec['arm_a']['pool']['n_pass']}/{rec['arm_a']['pool']['n_candidates']})")
    return rec


def run_mrna_stage(stage: str, targets: list[str], *, workers: int = 1,
                   worker_id: Optional[int] = None) -> int:
    stage_dir = MRNA_DIR if stage == "full" else RESULTS_DIR / stage
    stage_dir.mkdir(parents=True, exist_ok=True)

    if worker_id is not None:
        out = stage_dir / f"runs_worker{worker_id}.jsonl"
        cache_dir = MRNA_CACHES / f"{stage}_w{worker_id}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        inst = RetryInstrument(cache_dir)
        failures = 0
        for target_id in targets:
            try:
                rec = run_mrna_cell(target_id, stage, inst)
            except Exception as exc:  # noqa: BLE001
                failures += 1
                log_line(f"[{stage}:w{worker_id}:{target_id}] FAILURE: {exc!r}")
                rec = {"stage": stage, "target_id": target_id, "success": False,
                       "error": repr(exc),
                       "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return 0 if failures == 0 else 2

    record_files = [stage_dir / "runs.jsonl"] + \
        sorted(stage_dir.glob("runs_worker*.jsonl"))
    done: set[str] = set()
    for path in record_files:
        done |= {r["target_id"] for r in e27.load_records(path)
                 if r.get("success")}
    remaining = [t for t in targets if t not in done]
    if workers > 1 and remaining:
        import subprocess
        chunks: list[list[str]] = [[] for _ in range(workers)]
        metas = {m["target_id"]: m for m in mrna_targets()}
        cost = {t: (metas[t].get("protein_length_aa") or 100) ** 2 for t in remaining}
        loads = [0.0] * workers
        for t in sorted(remaining, key=lambda x: -cost[x]):  # LPT, exp28 convention
            k = min(range(workers), key=lambda i: loads[i])
            chunks[k].append(t)
            loads[k] += cost[t]
        log_line(f"[{stage}] LPT parallel launch: {len(done)} done, "
                 f"{len(remaining)} remaining across {workers} workers "
                 f"{[len(c) for c in chunks]}")
        procs = []
        for k, chunk in enumerate(chunks):
            if not chunk:
                continue
            lf = (stage_dir / f"worker{k}.log").open("w", encoding="utf-8")
            procs.append((k, subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "full-mrna",
                 "--targets", ",".join(chunk), "--worker-id", str(k)],
                env={**os.environ, "PYTHONPATH": f"{PROJECT_ROOT}"
                     f":{os.environ.get('PYTHONPATH', '')}"},
                stdout=lf, stderr=subprocess.STDOUT), lf))
        for k, proc, lf in procs:
            rc = proc.wait()
            lf.close()
            log_line(f"[{stage}] worker{k} exit={rc}")
    elif remaining:
        cache_dir = MRNA_CACHES / stage
        cache_dir.mkdir(parents=True, exist_ok=True)
        inst = RetryInstrument(cache_dir)
        for target_id in remaining:
            try:
                rec = run_mrna_cell(target_id, stage, inst)
            except Exception as exc:  # noqa: BLE001
                log_line(f"[{stage}:{target_id}] FAILURE: {exc!r}")
                rec = {"stage": stage, "target_id": target_id, "success": False,
                       "error": repr(exc),
                       "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
            with (stage_dir / "runs.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

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
    verdict["budget_matching"] = {
        "rule_raw_spend": RULE_RAW_SPEND,
        "nav_cap": NAV_RAW_BUDGET,
        "nav_raw_spent_max": max(r["budget_matching"]["nav_raw_spent"] or 0
                                 for r in ordered),
        "nav_raw_spent_mean": mean(r["budget_matching"]["nav_raw_spent"] or 0
                                   for r in ordered),
        "violations": sum(r["budget_matching"]["violations"] for r in ordered),
    }
    verdict["cohort"] = ("exp30 deployment targets, static-arm completion "
                         "(navigation cells from the frozen form-session traces)")
    (stage_dir / "verdict.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mc = verdict["mcnemar_C_vs_A"]
    log_line(f"[{stage}] deployment-cohort verdict: {verdict['go_no_go']} "
             f"(McNemar p={mc['p']:.3e}, b:c={mc['b']}:{mc['c']}, "
             f"c_e2e_gene={verdict['c_e2e_gene']:.3f}, n={verdict['n_pairs']})")
    return 0


# ── aptamer side: static grid against the frozen navigation cells ───────────

def run_aptamer_cell(key: str, display: str, caches: "e29.Caches",
                     log=log_line) -> dict[str, Any]:
    exp30_rec = load_exp30_records("aptamer")[display]
    struct_path = (exp30_rec.get("structure_reused")
                   or e30.resolve_reused_structure(key))
    assert struct_path and Path(struct_path).is_file(), \
        f"no reusable structure for {display} ({key})"
    t0 = time.perf_counter()
    inst = e29.Instrument(caches)
    meta = {"_target_id": display,
            "protein_sequence": e30.read_anchor_sequence(key)}
    ctx = inst.resolve_cell_context(meta, Path(struct_path))
    assert ctx["protein_path"] and ctx["hotspot"], "target_preparation_failed"

    config = e29._make_config(e29._MATRIX_V3(), e29._DENSE_LATTICE())
    log(f"[aptamer:{display}] static grid (48 raw, matrix v3) ...")
    grid = e29.static_grid(inst, ctx, config, log=log)
    assert grid["raw_spent"] == e29.RAW_CAP, grid["raw_spent"]
    deliveries_a = e29._deliveries(grid["pool"], config)
    arm_a = e29._arm_record("static_grid", grid, deliveries_a, pool=grid["pool"])

    # frozen navigation cells, echoed verbatim with provenance
    wf_path = Path(exp30_rec["workflow_results_path"])
    wf = json.loads(wf_path.read_text(encoding="utf-8"))
    trace = dict(wf.get("_gennav_trace") or {})
    cells = dict(exp30_rec["cells_pass"])
    arm_c = {
        "kind": "nav_production_exp30_frozen",
        "raw_budget": trace.get("raw_budget"),
        "raw_spent": trace.get("raw_spent"),
        "budget_violation": int((trace.get("raw_spent") or 0)
                                > e29.RAW_CAP),
        "cells_pass": cells,
        "e2e": all(cells.get(p, False) for p in e29.PROFILE_ORDER),
        "deliveries": {p: {"n": exp30_rec["delivered_counts"].get(p),
                           "degraded": not cells.get(p, False)}
                       for p in e29.PROFILE_ORDER},
        "trace_protocol": trace.get("protocol"),
        "session_id": exp30_rec["session_id"],
        "workflow_results_path": str(wf_path),
        "elapsed_seconds": exp30_rec.get("elapsed_seconds"),
    }

    rec = {
        "target_id": display,
        "anchor_key": key,
        "structure_path": str(struct_path),
        "matrix": "v3",
        "success": True,
        "static": arm_a,
        "nav_frozen": arm_c,
        "llm_calls": 0,
        "elapsed_seconds": round(time.perf_counter() - t0, 1),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    ca, cc = arm_a["cells_pass"], cells
    log(f"[aptamer:{display}] done in {rec['elapsed_seconds']:.0f}s — "
        f"cells A={sum(ca.values())}/3 C={sum(cc.values())}/3 "
        f"(static raw {arm_a['raw_spent']}/48)")
    return rec


def run_aptamer_stage(targets: list[tuple[str, str]], *, threads: int = 1) -> int:
    APT_DIR.mkdir(parents=True, exist_ok=True)
    caches = e29.Caches(APT_CACHES)
    out = APT_DIR / "runs.jsonl"
    done = {json.loads(ln)["target_id"]
            for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()} \
        if out.is_file() else set()
    jobs = [(k, d) for k, d in targets if d not in done]
    write_lock = __import__("threading").Lock()

    def _one(job: tuple[str, str]) -> None:
        key, display = job
        try:
            rec = run_aptamer_cell(key, display, caches)
        except Exception as exc:  # noqa: BLE001
            log_line(f"[aptamer:{display}] FAILURE: {exc!r}")
            rec = {"target_id": display, "anchor_key": key, "success": False,
                   "error": repr(exc),
                   "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with write_lock:
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if threads > 1 and len(jobs) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=threads) as pool:
            list(pool.map(_one, jobs))
    else:
        for job in jobs:
            _one(job)
    caches.flush()

    records = [json.loads(ln) for ln
               in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ordered = sorted(records, key=lambda r: [d for _, d in targets].index(r["target_id"]))
    with out.open("w", encoding="utf-8") as fh:
        for r in ordered:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = [r for r in ordered if r.get("success")]
    if not ok:
        return 1
    verdict = aptamer_verdict(ok, cohort="exp30 deployment targets (static "
                                          "completion vs frozen nav cells)")
    (APT_DIR / "verdict.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mc = verdict["mcnemar_nav_vs_static"]
    log_line(f"[aptamer] deployment-cohort verdict: delivered "
             f"{verdict['delivered_nav']}:{verdict['delivered_static']}, "
             f"b:c={mc['b']}:{mc['c']}, p={mc['p']:.4f}")
    return 0 if len(ok) == len(targets) else 2


def aptamer_cells_from_record(rec: dict[str, Any], arm: str) -> dict[str, bool]:
    if arm == "static":
        if "static" in rec:
            return dict(rec["static"]["cells_pass"])
        return dict(rec["arms"]["A"]["cells_pass"])
    if rec.get("nav_frozen"):
        return dict(rec["nav_frozen"]["cells_pass"])
    return dict(rec["arms"]["C"]["cells_pass"])


def aptamer_verdict(records: list[dict[str, Any]], *, cohort: str) -> dict[str, Any]:
    """Pooled aptamer summary: delivered cells + exact McNemar on the
    discordant cells (nav vs static)."""
    order = list(e29.PROFILE_ORDER)
    nav = static = 0
    b = c_ = 0
    per_target: list[dict[str, Any]] = []
    for rec in records:
        cn, cs = aptamer_cells_from_record(rec, "nav"), aptamer_cells_from_record(rec, "static")
        t_nav = t_static = 0
        for p in order:
            n_pass, s_pass = bool(cn.get(p)), bool(cs.get(p))
            nav += n_pass
            static += s_pass
            t_nav += n_pass
            t_static += s_pass
            if n_pass and not s_pass:
                b += 1
            elif s_pass and not n_pass:
                c_ += 1
        per_target.append({
            "target_id": rec["target_id"],
            "nav_cells": t_nav, "static_cells": t_static,
            "nav_e2e": t_nav == 3, "static_e2e": t_static == 3,
            "nav_spend": (rec.get("nav_frozen") or rec["arms"]["C"]).get("raw_spent"),
            "static_spend": (rec.get("static") or rec["arms"]["A"]).get("raw_spent"),
        })
    return {
        "cohort": cohort,
        "n_targets": len(records),
        "n_cells": len(records) * 3,
        "delivered_nav": nav,
        "delivered_static": static,
        "e2e_nav": sum(1 for t in per_target if t["nav_e2e"]),
        "e2e_static": sum(1 for t in per_target if t["static_e2e"]),
        "mcnemar_nav_vs_static": {"b": b, "c": c_,
                                  "p": e29.exact_mcnemar(b, c_)},
        "budget": {
            "static_raw_spend": 48,
            "static_violations": sum(
                int((r.get("static") or r["arms"]["A"])["raw_spent"] > e29.RAW_CAP)
                for r in records),
            "nav_violations": sum(
                int(((r.get("nav_frozen") or r["arms"]["C"]).get("raw_spent") or 0)
                    > e29.RAW_CAP) for r in records),
            "nav_spend_mean": mean(
                (r.get("nav_frozen") or r["arms"]["C"]).get("raw_spent") or 0
                for r in records),
        },
        "per_target": per_target,
    }


# ── pooled analysis (25 mRNA / 26 aptamer targets) ──────────────────────────

def pooled_mrna() -> dict[str, Any]:
    e28_records = [r for r in e27.load_records(EXP28_FULL / "runs.jsonl")
                   if r.get("success")]
    e40_records = [r for r in e27.load_records(MRNA_DIR / "runs.jsonl")
                   if r.get("success")]
    assert len(e28_records) == 20, len(e28_records)
    assert len(e40_records) == 5, len(e40_records)
    records = e28_records + e40_records
    pooled = e27.aggregate_verdict(records)
    pooled["budget_matching"] = {
        "rule_raw_spend": RULE_RAW_SPEND,
        "nav_cap": NAV_RAW_BUDGET,
        "nav_raw_spent_max": max(r["budget_matching"]["nav_raw_spent"] or 0
                                 for r in records),
        "nav_raw_spent_mean": mean(r["budget_matching"]["nav_raw_spent"] or 0
                                   for r in records),
        "violations": sum(r["budget_matching"]["violations"] for r in records),
    }
    pooled["cohorts"] = {
        "registered_20": {
            "source": "exp28_gennav_mrna_endpoint_v2/full/verdict.json (frozen)",
            "mcnemar": "17:6, p=0.0347 (frozen)",
        },
        "deployment_5": json.loads((MRNA_DIR / "verdict.json").read_text(
            encoding="utf-8")),
    }
    pooled["n_pairs"] = len(records) * 3
    pooled["n_targets"] = len(records)
    pooled["deployment_nav_source"] = (
        "the five deployment navigation cells are the frozen Exp-30 user-form "
        "session traces (production mrna_cds_design navigation=True, 35-raw "
        "cap), composed and evaluated here under the identical full-length "
        "matrix/utility stack")

    # jcd target counts + gene-e2e target list (figure/text inputs)
    deployment_ids = {m["target_id"] for m in mrna_targets()}
    jcd_counts = []
    gene_e2e_targets = []
    for r in records:
        jcd_counts.append({
            "target_id": r["target_id"],
            "nav_jcd": sum(1 for p in r["evaluations"]["C"]["profiles"] if p["JCD"]),
            "rule_jcd": sum(1 for p in r["evaluations"]["A"]["profiles"] if p["JCD"]),
            "cohort": "deployment_5" if r["target_id"] in deployment_ids
                      else "registered_20",
        })
        if all(p["e2e_pass"] for p in r["evaluations"]["C"]["profiles"]):
            gene_e2e_targets.append(r["target_id"])
    pooled["jcd_target_counts"] = jcd_counts
    pooled["gene_e2e_targets"] = gene_e2e_targets
    return pooled


def pooled_secondary_panel(pooled: dict[str, Any]) -> dict[str, Any]:
    """The Fig-5d successor panel data over the 75 pooled pairs."""
    e28_records = [r for r in e27.load_records(EXP28_FULL / "runs.jsonl")
                   if r.get("success")]
    e40_records = [r for r in e27.load_records(MRNA_DIR / "runs.jsonl")
                   if r.get("success")]
    deltas: list[float] = []
    nav_scores: list[float] = []
    rule_scores: list[float] = []
    for r in e28_records + e40_records:
        for pc, pa in zip(r["evaluations"]["C"]["profiles"],
                          r["evaluations"]["A"]["profiles"]):
            deltas.append(pc["composite"] - pa["composite"])
            nav_scores.append(pc["composite"])
            rule_scores.append(pa["composite"])
    n_pos = sum(1 for d in deltas if d > 1e-12)
    n_neg = sum(1 for d in deltas if d < -1e-12)
    return {
        "n_pairs": len(deltas),
        "composite_delta": {
            "deltas": deltas,
            "n_pos": n_pos,
            "n_zero": len(deltas) - n_pos - n_neg,
            "n_neg": n_neg,
            "wilcoxon_p": pooled["wilcoxon_C_vs_A_p"],
            "nav_mean": mean(nav_scores),
            "rule_mean": mean(rule_scores),
        },
        "gene_e2e": {
            "value": pooled["c_e2e_gene"],
            "n_targets": pooled["n_targets"],
            "gate": 0.8,
            "targets": pooled["gene_e2e_targets"],
            "rule_context": pooled["a_e2e_gene"],
        },
        "constraint_rate": {
            "value": _pooled_constraint_rate(e28_records + e40_records),
            "gate": 0.9,
        },
        "budget": {
            "rule_raw_spend": RULE_RAW_SPEND,
            "nav_spend_mean": pooled["budget_matching"]["nav_raw_spent_mean"],
            "nav_cap": NAV_RAW_BUDGET,
            "violations": pooled["budget_matching"]["violations"],
            "nav_spend_multiset": sorted(
                r["budget_matching"]["nav_raw_spent"] or 0
                for r in e28_records + e40_records),
            "llm_calls": 0,
        },
        "notes": ("pooled over the frozen Exp-28 registered 20-target cohort "
                  "+ the Exp-40 completion of the Exp-30 deployment cohort; "
                  "deployment navigation cells = frozen form-session traces"),
    }


def _pooled_constraint_rate(records: list[dict[str, Any]]) -> float:
    vals = [p["constraint_rate"] for r in records
            for p in r["evaluations"]["C"]["profiles"]]
    return mean(vals) if vals else 0.0


def pooled_aptamer() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    cohorts: dict[str, int] = {}
    for seg in APTAMER_SEGMENTS:
        seg_records = [json.loads(ln) for ln
                       in (EXP29_ROOT / seg / "runs.jsonl").read_text(
                           encoding="utf-8").splitlines() if ln.strip()]
        assert all(r.get("success") for r in seg_records), seg
        records.extend(seg_records)
        cohorts[seg] = len(seg_records)
    dep = [r for r in e27.load_records(APT_DIR / "runs.jsonl") if r.get("success")]
    assert len(dep) == 6, len(dep)
    records.extend(dep)
    cohorts["deployment"] = len(dep)

    pooled = aptamer_verdict(records, cohort=(
        "frozen seg3_decisive (12) + seg4_confirmation (8) + exp40 deployment "
        "completion (6) — matrix v3, cap 48, static grid vs production "
        "navigation"))
    pooled["cohorts"] = cohorts
    pooled["cohort_splits"] = {}
    for name, sub in (("seg3_decisive", APTAMER_SEGMENTS[0]),
                      ("seg4_confirmation", APTAMER_SEGMENTS[1]),
                      ("deployment_6", None)):
        if sub is not None:
            sub_records = [json.loads(ln) for ln
                           in (EXP29_ROOT / sub / "runs.jsonl").read_text(
                               encoding="utf-8").splitlines() if ln.strip()]
        else:
            sub_records = dep
        v = aptamer_verdict(sub_records, cohort=name)
        pooled["cohort_splits"][name] = {
            "delivered_nav": v["delivered_nav"],
            "delivered_static": v["delivered_static"],
            "mcnemar": v["mcnemar_nav_vs_static"],
            "e2e_nav": v["e2e_nav"], "e2e_static": v["e2e_static"],
        }
    pooled["nav_vintage_disclosure"] = (
        "deployment navigation cells are the frozen Exp-30 runs: FGF2, "
        "Angiopoietin-2 and IFN-gamma on the pre-2026-09-05 shipped mode "
        "(e14_production_v1), IL-17A, PDGF-BB and swine H3 HA on the current "
        "one (e14_production_v4); the static grid is vintage-free")
    pooled["register_note"] = (
        "pooled summary per DECISIONS (i): the registered 20-pool endpoint "
        "verdicts (seg3/seg4) remain the inferential backbone; this pooled "
        "statistic does not re-open the aptamer primary endpoint")
    return pooled


def run_pool() -> int:
    POOLED_DIR.mkdir(parents=True, exist_ok=True)
    pooled_m = pooled_mrna()
    (POOLED_DIR / "mrna_pooled_verdict.json").write_text(
        json.dumps(pooled_m, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    panel = pooled_secondary_panel(pooled_m)
    (POOLED_DIR / "mrna_secondary_panel.json").write_text(
        json.dumps(panel, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pooled_a = pooled_aptamer()
    (POOLED_DIR / "aptamer_pooled_verdict.json").write_text(
        json.dumps(pooled_a, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mc_m = pooled_m["mcnemar_C_vs_A"]
    mc_a = pooled_a["mcnemar_nav_vs_static"]
    log_line(f"[pool] mRNA 25 targets: b:c={mc_m['b']}:{mc_m['c']} "
             f"p={mc_m['p']:.4e}, c_e2e_gene={pooled_m['c_e2e_gene']:.3f}, "
             f"JCD nav {sum(t['nav_jcd'] for t in pooled_m['jcd_target_counts'])}/75")
    log_line(f"[pool] aptamer 26 targets: delivered "
             f"{pooled_a['delivered_nav']}:{pooled_a['delivered_static']}, "
             f"b:c={mc_a['b']}:{mc_a['c']} p={mc_a['p']:.4f}")
    return 0


# ── verify ──────────────────────────────────────────────────────────────────

def verify(which: str) -> int:
    mismatches = 0
    if which in ("mrna", "all"):
        for stage_dir in (MRNA_DIR, RESULTS_DIR / "pilot"):
            path = stage_dir / "runs.jsonl"
            if not path.is_file():
                continue
            for rec in [r for r in e27.load_records(path) if r.get("success")]:
                recomputed = e27._recompute_cell(rec)
                for arm in ("A", "C"):
                    stored = rec["evaluations"].get(arm) or {}
                    if not stored.get("profiles"):
                        continue
                    for p_new, p_old in zip(recomputed[arm]["profiles"],
                                            stored["profiles"]):
                        for key in ("e2e_pass", "constraint_rate", "D1_min_dist",
                                    "D1", "D2_cai_span", "D2", "D3", "R3", "JCD"):
                            if p_new[key] != p_old.get(key):
                                mismatches += 1
                                log_line(f"VERIFY MISMATCH {rec['target_id']} "
                                         f"{arm} {p_new['profile']}.{key}")
                        if abs(p_new["composite"] - p_old["composite"]) > 1e-12:
                            mismatches += 1
        stored = json.loads((MRNA_DIR / "verdict.json").read_text(encoding="utf-8"))
        fresh = e27.aggregate_verdict(
            [r for r in e27.load_records(MRNA_DIR / "runs.jsonl") if r.get("success")])
        if json.dumps(fresh, sort_keys=True) != json.dumps(
                {k: v for k, v in stored.items() if k != "budget_matching"
                 and k != "cohort"}, sort_keys=True):
            mismatches += 1
            log_line("VERIFY MISMATCH: mrna deployment verdict differs")
        log_line(f"[verify:mrna] {'OK' if mismatches == 0 else f'{mismatches} MISMATCHES'}")

    if which in ("aptamer", "all"):
        from agent_core.generation.gennav_aptamer import (
            evaluate_matrix, gc_fraction, longest_stem_bp,
        )
        config = e29._make_config(e29._MATRIX_V3(), e29._DENSE_LATTICE())
        for rec in [r for r in e27.load_records(APT_DIR / "runs.jsonl")
                    if r.get("success")]:
            # recompute matrix_pass + deliveries from the stored pool snapshot
            pool = []
            for cand in rec["static"]["pool"]:
                seq = cand["sequence"]
                pool.append({**cand,
                             "matrix_pass": evaluate_matrix(
                                 seq, gc_fraction(seq),
                                 cand.get("longest_stem_bp") or 0, config)})
            deliveries = e29._deliveries(pool, config)
            cells = e29._cells_pass(deliveries)
            if cells != rec["static"]["cells_pass"]:
                mismatches += 1
                log_line(f"VERIFY MISMATCH {rec['target_id']} static cells")
            if rec["static"]["raw_spent"] != 48:
                mismatches += 1
                log_line(f"VERIFY MISMATCH {rec['target_id']} static spend")
            # nav echo must equal the frozen exp30 record byte-for-byte
            exp30_rec = load_exp30_records("aptamer")[rec["target_id"]]
            if rec["nav_frozen"]["cells_pass"] != exp30_rec["cells_pass"]:
                mismatches += 1
                log_line(f"VERIFY MISMATCH {rec['target_id']} nav echo")
        stored = json.loads((APT_DIR / "verdict.json").read_text(encoding="utf-8"))
        fresh = aptamer_verdict(
            [r for r in e27.load_records(APT_DIR / "runs.jsonl") if r.get("success")],
            cohort=stored.get("cohort", ""))
        for key in ("delivered_nav", "delivered_static", "mcnemar_nav_vs_static"):
            if json.dumps(fresh[key], sort_keys=True) != \
                    json.dumps(stored[key], sort_keys=True):
                mismatches += 1
                log_line(f"VERIFY MISMATCH: aptamer verdict {key}")
        log_line(f"[verify:aptamer] "
                 f"{'OK' if mismatches == 0 else f'{mismatches} MISMATCHES'}")

    if which in ("pool", "all"):
        pooled_m = pooled_mrna()
        stored = json.loads((POOLED_DIR / "mrna_pooled_verdict.json")
                            .read_text(encoding="utf-8"))
        if json.dumps(pooled_m, sort_keys=True) != json.dumps(stored, sort_keys=True):
            mismatches += 1
            log_line("VERIFY MISMATCH: mrna pooled verdict differs")
        panel = pooled_secondary_panel(pooled_m)
        stored_panel = json.loads((POOLED_DIR / "mrna_secondary_panel.json")
                                  .read_text(encoding="utf-8"))
        if json.dumps(panel, sort_keys=True) != \
                json.dumps(stored_panel, sort_keys=True):
            mismatches += 1
            log_line("VERIFY MISMATCH: mrna secondary panel differs")
        pooled_a = pooled_aptamer()
        stored_a = json.loads((POOLED_DIR / "aptamer_pooled_verdict.json")
                              .read_text(encoding="utf-8"))
        if json.dumps(pooled_a, sort_keys=True) != json.dumps(stored_a, sort_keys=True):
            mismatches += 1
            log_line("VERIFY MISMATCH: aptamer pooled verdict differs")
        log_line(f"[verify:pool] "
                 f"{'BYTE-IDENTICAL' if mismatches == 0 else f'{mismatches} MISMATCHES'}")
    return 0 if mismatches == 0 else 1


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["pilot", "full-mrna", "full-aptamer",
                                         "pool", "verify"])
    parser.add_argument("--targets", default=None,
                        help="comma-separated mRNA target override")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--worker-id", type=int, default=None,
                        help=argparse.SUPPRESS)
    args = parser.parse_args()

    mrna_targets()
    if args.mode == "verify":
        return verify(args.targets or "all")
    if args.mode == "pool":
        return run_pool()
    if args.mode == "pilot":
        targets = (args.targets.split(",") if args.targets else ["PTH"])
        rc_m = run_mrna_stage("pilot", [t.strip() for t in targets if t.strip()],
                              workers=1)
        rc_a = run_aptamer_stage([("fgf2", "FGF2")], threads=1)
        return rc_m or rc_a
    if args.mode == "full-mrna":
        targets = (args.targets.split(",") if args.targets
                   else [m["target_id"] for m in mrna_targets()])
        return run_mrna_stage("full", [t.strip() for t in targets if t.strip()],
                              workers=args.workers, worker_id=args.worker_id)
    if args.mode == "full-aptamer":
        return run_aptamer_stage(list(e30.APTAMER_NEW_TARGETS), threads=args.threads)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
