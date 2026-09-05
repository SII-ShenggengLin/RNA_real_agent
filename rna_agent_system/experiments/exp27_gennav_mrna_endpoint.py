#!/usr/bin/env python3
"""EXP 27 — GenNav mRNA 主终点 re-run（Fig 5b/5c，§2.5 实验 2 / paper registry E6）.

Fourth programme reset (2026-09-02): the E6 S2 dual-endpoint campaign re-run
with newly written code on the CURRENT production platform, one experiment at
a time.  Legacy E6 assets were already absent from disk at reset time
(machinery deleted 2026-08-18; verdict JSONs dropped in later resets) — the
protocol below was recovered VERBATIM from git ``e601913``
(``experiments/run_e6_gennav.py`` + ``agent_core/generation/gennav_core.py``,
importing ``run_e5_constraint_nav.py`` from ``b6dad08``) before any run.

SCOPE AMENDMENT (user-directed 2026-09-02, registered before any run):
20 targets = the legacy registered 18 (FULL_TARGETS) + OTC + PDGFB, i.e. the
FULL current ``targets/*.json`` set; primary-endpoint pairs n = 60 (legacy 54).
OTC (354 aa) / PDGFB (241 aa) sat outside the legacy S2 scope only because the
legacy 20-target manifest of its era carried Factor_VIII/Zika_E instead; both
are regular current-dataset targets (Fig-2b/c designed them 20/20).

DATASET: the current ``data/benchmarks/RNA-BioBench-FullLength-mRNA`` target
files (20 JSONs: 16 Homo sapiens + 2 E. coli GFP/Beta_galactosidase — species-
resolved codon tables, the current registration), WT GC references from
``external_anchors/wt_cds/<target>.fa``.  One dataset across figures (Fig 2b/c
same 20 targets; Fig 5a S1 five-target subset ⊂ this set; Fig 4d same files).

ARMS (both through the production path, zero intervention):
- A (rule-based static): the registered static recipe pool built by the
  Exp-26 instrument verbatim — LinearDesign λ∈{0,1,4,10} (species-resolved
  CSV) + RNARL 1 + GEMORNA CDS 30 samples = 35 CDS × 9 GEMORNA UTR presets
  (3 5′ × 3 3′) = 315 full-length constructs; hard constraints C1 (100-nt
  sliding GC 30–80) / C2 (homopolymer <14) / C6 (start-region stem ≤12 bp over
  utr5+cds[:30]) / C7 (full-length stem ≤30 bp) / M1 (boundary GC 20–80,
  30-nt flanks) / CAI ≥ 0.8 (species table); archive E-metrics and the §5
  utility U = (0.8×regional + 0.2×global + 0.8×λ-pref)/(1.8); per-profile
  rule delivery ``_default_delivery`` verbatim (λ-pref top-1, cross-λ spread,
  U fill, U-ordered) on pool-build utilities.
- C (gated navigation): the SHIPPED production GenNav-λ —
  ``MrnaCdsDesignWorkflow(navigation=True)`` fresh in-process per target
  (probe λ-curve {0,1,2,4,8,10,20,50} → guaranteed-repair + mechanized
  interstitial reinforcement ≤16 raw LinearDesign calls → per-profile matrix
  delivery expression/stability/balanced × 5 with CDS-level D1 greedy 0.05).
  Deterministic, zero LLM.  The navigator owns CDS selection per band; the
  driver composes every delivered CDS with the SAME per-target 9 UTR presets,
  evaluates it under the identical full-length matrix/archive/utility stack,
  and delivers, per profile, the navigator's rank order with each CDS mapped
  to its per-profile U-max full-length combination.

ARCHITECTURE-CHANGE DISCLOSURES (the fourth reset's object of study):
1. The legacy C-arm's LLM ``request_generate`` loop and its GEMORNA
   independent-row lattice fallback no longer exist in production; the
   shipped navigator is deterministic/zero-LLM (LLM usage 0 vs legacy 43) and
   has no GEMORNA fallback — a HER2-class zero-feasible target degrades with
   an explicitly short delivery instead of being rescued by lattice rows.
   Measured, not recreated.
2. The shipped workflow exposes only the delivered candidate set (the raw
   navigation pool stays workflow-private); the C-arm pool behind the
   delivery = distinct delivered CDS × 9 UTR combos (R4's argmax basis).
3. E3 junction at delivery via the CURRENT platform ``JunctionEvaluator``
   (MFE/nt, mean of the 5′|CDS and CDS|3′ junctions; ddG report-only) —
   utilities reassigned pool-wide after E3 write-back (the legacy ordering:
   deliveries selected on pool-build U, evaluation on junction-ful U).
4. GEMORNA sampling non-idempotent; caches SEeded from the Exp-26 full run
   for its five targets (A1AT/Insulin/EPO/GFP/IL-2 share the Fig-5a
   realization — cross-figure consistency) and realized afresh in-run for the
   other 15 (measured, not recreated).
5. GFP / Beta_galactosidase design + scoring on the species-resolved
   E. coli table in both arms (current registration; the pre-B0 human-table
   defect was Exp 26's exhibit).

CRITERIA (v8 book, ported verbatim; per target × profile):
JCD-pass = e2e ∧ D1 ∧ D2 ∧ R3 where
- e2e  = exactly 5 delivered ∧ all pass the full-length constraint matrix;
- D1   = min pairwise diversity distance of the delivered five ≥ 2%;
- D2   = D1 ∧ delivered CAI span ≥ 0.05 (decision-① composite semantics);
- R3   = arm-level: pairwise top-1 separation (|ΔCAI| ≥ 0.05 or |Δλ-rank| ≥ 2)
         over ≥ 1/3 of the three profile pairs — A on the legacy 6-rank
         LAMBDA_RANK map, C on a dynamic rank map over the navigator's
         sampled λ values (the legacy C-arm convention);
secondary bundle = R1 (delivery U-ordered, Spearman ≥ 1) ∧ R4 (top-1 =
argmax-U among passing with max-constraints tiebreak) ∧ R3 ∧ D1 ∧ D2 ∧ D3
(pair-ratio range ≥ 3 or stem range ≥ 5) on every target × profile, ∧ C-arm
gear declaration ge_3 (≥ 3 distinct λ gears among delivered CDS) on every
target, ∧ constraint rate ≥ 0.9.
Composite score = 0.4×e2e + 0.2×rate + 0.2×(0.5×min(D1_dist/0.02,1) +
0.5×(D1 ? min(CAI_span/0.05,1) : 0)) + 0.2×R3 (verbatim).

ENDPOINTS (verbatim; S2 book §20):
- primary  = paired EXACT McNemar (two-sided) on JCD pass/fail C vs A over
             n = 20 × 3 = 60 pairs, p < 0.05  ∧  c_e2e_gene ≥ 0.8;
- secondary= paired Wilcoxon on composite scores (C vs A) p < 0.05 ∧ quality
             bundle ∧ constraint rate C ≥ 0.9; GO = either endpoint;
             primary-pass/secondary-fail disclosed.
- permutation null (figure inset): 10⁴ draws, seed 0 — the directions of the
  observed discordant pairs sign-flipped under H₀ (b ~ Bin(b+c, 0.5));
  statistic b = C-favouring discordants, observed value marked.

PARALLEL AMENDMENT (user-directed 2026-09-02, registered before re-launch —
the Exp-24 convention): ``--workers N`` launches N target-exclusive parallel
workers (subprocesses).  Each target is processed by exactly one worker (the
per-target GEMORNA realization stays single-realized), a target's phases stay
sequential (the navigation algorithm is inherently sequential), and every
worker owns its cache dir and record file (no write races).  Determinism is
unaffected (LinearDesign deterministic per protein/table/λ); per-cell wall
times measure the delivered pipeline under concurrent campaign load —
disclosed wherever elapsed times are cited.

INSTRUMENT: production tool path (ToolExecutor.run_tool via the Exp-26
Instrument for pools/composition; the shipped workflow in-process for the
navigation arm), ``RNADA_CAPGATE=advisory``, platform audit trail on, every
call audited.  Services GPU-pinned 0/1/2 via exp1_bring_up_services.sh
(GEMORNA 8004 / RNARL 8008 / RNASTOP 8009 / LinearDesign 8014 CPU /
LinearFold 8015 / metrics 8020).  Zero LLM calls.

PILOT: Insulin (legacy S0 target) + OTC (amended-scope target), 2 cells ×
A/C arms; criteria: both cells complete with JCD evaluations on all six
profile cells each, records verifiable.

OUTPUTS: ``results/exp27_gennav_mrna_endpoint/{pilot,full}/runs.jsonl`` +
``verdict.json`` (+ caches/ seeded from exp26).  ``--verify`` recomputes
every stored evaluation primitive (D1 distances, D2 spans, R3 separations,
JCD, composite) and the full verdict — including the permutation null — from
the stored records byte-identically.

Usage:
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp27_gennav_mrna_endpoint.py pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp27_gennav_mrna_endpoint.py full [--resume]
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp27_gennav_mrna_endpoint.py verify full
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any

os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scipy import stats as scipy_stats  # noqa: E402

from experiments import exp26_selection_layer_pool as e26  # noqa: E402
from experiments.exp26_selection_layer_pool import (  # noqa: E402
    CONSTRAINT_IDS,
    DIVERSITY_GATE,
    LAMBDA_RANK,
    PROFILES,
    UTR_PRESETS,
    Instrument,
    _default_delivery,
    _rna,
    assign_utilities,
    build_pool,
    diversity_distance,
    evaluate_delivery,
)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp27_gennav_mrna_endpoint"
TARGETS_DIR = e26.TARGETS_DIR
CACHES_DIR = RESULTS_DIR / "caches"
EXP26_FULL = PROJECT_ROOT / "experiments" / "results" / "exp26_selection_layer_pool" / "full"

# SCOPE AMENDMENT (user-directed 2026-09-02): legacy FULL_TARGETS 18 + OTC + PDGFB
FULL_TARGETS: list[str] = [
    "A1AT", "Albumin", "Beta_galactosidase", "EPO", "GFP",
    "Growth_hormone", "HER2", "HIV-1_Env_gp120", "HPV16_L1", "IFN_alpha_2a",
    "IL-2", "Influenza_HA_H1N1", "Insulin", "Luciferase", "OTC",
    "Ovalbumin", "PDGFB", "RSV_F_protein", "SARS-CoV-2_Spike_WT",
    "Transferrin",
]
PILOT_TARGETS: list[str] = ["Insulin", "OTC"]

D2_CAI_SPAN_MIN = 0.05          # decision-① composite D2
R3_CAI_SEP = 0.05               # R3 top-1 separation, CAI arm
R3_LAMBDA_RANK_SEP = 2          # R3 top-1 separation, λ-rank arm
R3_PAIR_FRACTION = 1.0 / 3.0
D3_PAIR_RATIO_RANGE = 3.0
D3_STEM_RANGE = 5.0
PERM_DRAWS = 10_000
PERM_SEED = 0
DELIVERY_SIZE = 5


# ── E6 decision-① amendment pure functions (ported verbatim) ────────────────
def delivery_cai_span(cais: list[float]) -> float:
    return (max(cais) - min(cais)) if len(cais) >= 2 else 0.0


def d2_composite(d1: bool, cais: list[float]) -> bool:
    return bool(d1 and delivery_cai_span(cais) >= D2_CAI_SPAN_MIN)


def jcd_pass(ev: dict[str, Any]) -> bool:
    return bool(ev["e2e_pass"] and ev["D1"] and ev["D2"] and ev.get("R3", False))


def composite_score(ev: dict[str, Any]) -> float:
    e2e = 1.0 if ev["e2e_pass"] else 0.0
    rate = ev["constraint_rate"]
    d1 = min(ev["D1_min_dist"] / DIVERSITY_GATE, 1.0)
    d2 = min(ev.get("D2_cai_span", 0.0) / D2_CAI_SPAN_MIN, 1.0) if ev["D1"] else 0.0
    r3 = 1.0 if ev.get("R3", False) else 0.0
    return 0.4 * e2e + 0.2 * rate + 0.2 * (0.5 * d1 + 0.5 * d2) + 0.2 * r3


def log_line(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ── Arm C: the shipped production GenNav-λ navigation ───────────────────────
def run_navigation(target_id: str, meta: dict[str, Any], log=log_line) -> dict[str, Any]:
    """One fresh production ``mrna_cds_design(navigation=True)`` run.

    Returns the verbatim ``_gennav_trace`` (whose per-profile ``deliveries``
    carry the navigator's ranked pool candidates) plus run-level facts.
    """
    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.mrna_cds_design import (
        MrnaCdsDesignInput,
        MrnaCdsDesignWorkflow,
    )

    registry = build_default_capability_registry(
        ToolExecutor(build_default_tool_registry()))
    wf = MrnaCdsDesignWorkflow(registry)
    wf.auto_start_services = True
    inp = MrnaCdsDesignInput(
        protein_sequence=meta["protein_sequence"].upper(),
        cai_species=meta.get("species_for_codon_optimization") or "Homo sapiens",
        navigation=True,
    )
    t0 = time.perf_counter()
    result = wf.run(inp)
    elapsed = time.perf_counter() - t0
    trace = dict(getattr(result, "_state_writeback", {}) or {}).get("_gennav_trace") or {}
    return {
        "success": bool(result.success),
        "errors": list(result.errors or []),
        "elapsed_seconds": elapsed,
        "trace": json.loads(json.dumps(trace, default=str)),  # plain-copyable
        "n_result_candidates": len(result.all_candidates or []),
    }


# ── Arm C composition: delivered CDS × the same 9 UTR presets ───────────────
def evaluate_full_length(
    cds_items: list[tuple[float, str]],
    utr5_cache: dict[str, str],
    utr3_cache: dict[str, str],
    target_id: str,
    meta: dict[str, Any],
    inst: Instrument,
    log=log_line,
) -> list[dict[str, Any]]:
    """Compose CDS × 9 UTR presets and evaluate — the Exp-26 evaluation block
    (constraints + archive) applied to a smaller CDS set; identical semantics.

    ``cds_items`` = [(lambda, cds_sequence)]; ids are ``nav<λ>_u5?_u3?``.
    """
    species = meta.get("species_for_codon_optimization") or "Homo sapiens"
    rare = e26.rare_codon_set(species)

    fa = e26.WT_CDS_DIR / f"{target_id}.fa"
    if fa.is_file():
        lines = [ln.strip() for ln in fa.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.lstrip().startswith(">")]
        wt_gc = e26.gc_fraction("".join(lines))
    else:
        wt_gc = 0.0

    candidates: list[dict[str, Any]] = []
    for lam, cds_seq in cds_items:
        for u5p in UTR_PRESETS:
            for u3p in UTR_PRESETS:
                cand = e26.make_candidate(cds_seq, utr5_cache[u5p], utr3_cache[u3p],
                                          lam, u5p, u3p, species, source="ld")
                cand["id"] = f"nav{lam:g}_u5{u5p[0]}_u3{u3p[0]}"
                candidates.append(cand)

    cai_cache = {seq: inst.cai(seq, species) for _, seq in cds_items}
    mrl_cache = {p: inst.predict_mrl(utr5_cache[p]) for p in UTR_PRESETS}
    stab_cache = {p: inst.predict_stability(utr3_cache[p]) for p in UTR_PRESETS}

    window_fold_cache: dict[tuple[str, str], str] = {}
    for cand in candidates:
        cds_seq, utr5, utr3 = cand["cds"], cand["utr5"], cand["utr3"]
        window_key = (utr5, cds_seq)
        if window_key not in window_fold_cache:
            win_seq = utr5 + cds_seq[:e26.START_REGION_CDS_PREFIX]
            window_fold_cache[window_key] = inst.fold(win_seq)["structure"]
        win_struct = window_fold_cache[window_key]
        folded = inst.fold(cand["sequence"])
        full_struct = folded["structure"]

        cand["constraints"] = {
            "C1": not e26.sliding_window_gc_out_of_bounds(cand["sequence"]),
            "C2": not e26.has_homopolymer(cand["sequence"]),
            "C6": e26.longest_stem_bp(win_struct) <= e26.START_REGION_MAX_STEM,
            "C7": e26.longest_stem_bp(full_struct) <= e26.FULL_MAX_STEM,
            "M1": e26.boundary_gc_ok(utr5, cds_seq, utr3),
            "CAI": cai_cache[cds_seq] >= e26.CAI_MIN,
        }
        cand["flags"]["passed"] = all(cand["constraints"].values())
        cds_struct = full_struct[len(utr5): len(utr5) + len(cds_seq)]
        cand["archive"] = {
            "C3_polya_signal_count": e26.polya_signal_count(cds_seq),
            "C4_restriction_hits": e26.restriction_site_hits(cand["sequence"]),
            "C5_splice_motif_count": e26.splice_motif_count(cds_seq),
            "C8_uAUG_count": utr5.count("AUG"),
            "E1_cai": cai_cache[cds_seq],
            "E2_full_mfe": folded["mfe"],
            "E3_junction_mfe_per_nt": None,
            "E4_utr5_mrl": mrl_cache[cand["utr5_preset"]],
            "E5_utr3_stability": stab_cache[cand["utr3_preset"]],
            "E6_rare_codons": e26.rare_codon_count(cds_seq, rare),
            "E7_pair_ratio": e26.pair_ratio(full_struct),
            "E8_delta_gc": abs(e26.gc_fraction(cand["sequence"]) - wt_gc),
            "E9_are_count": e26.are_count(utr3),
            "E10_kozak": e26.kozak_score(utr5, cds_seq),
            "C6_start_open": e26.unpaired_fraction(win_struct),
            "C7_longest_stem": e26.longest_stem_bp(full_struct),
            "CDS_unpaired": e26.unpaired_fraction(cds_struct),
            "full_gc": e26.gc_fraction(cand["sequence"]),
        }
        cand["wt_gc_reference"] = wt_gc
    log(f"  [compose:{target_id}] {len(candidates)} full-length candidates, "
        f"{sum(1 for c in candidates if c['flags']['passed'])} pass")
    return candidates


def junction_at_delivery(
    pool_candidates: list[dict[str, Any]],
    deliveries: dict[str, list[dict[str, Any]]],
    target_id: str,
    log=log_line,
) -> None:
    """Delivery-level E3 junction MFE/nt via the current JunctionEvaluator
    (mean of the 5′|CDS and CDS|3′ junctions), written back into the pool.
    """
    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflow_models import Candidate
    from agent_core.workflows.evaluators import JunctionEvaluator

    registry = build_default_capability_registry(
        ToolExecutor(build_default_tool_registry()))
    evaluator = JunctionEvaluator(registry)
    by_id = {c["id"]: c for c in pool_candidates}
    seen: set[str] = set()
    n = 0
    for profile in PROFILES:
        for c in deliveries.get(profile, []):
            if c["id"] in seen:
                continue
            seen.add(c["id"])
            cand = Candidate(
                id=c["id"], sequence=c["sequence"],
                metadata={"utr5_sequence": c["utr5"], "cds_sequence": c["cds"],
                          "utr3_sequence": c["utr3"]},
            )
            metrics = evaluator.evaluate(cand, {"workflow_state": {}})
            j5 = metrics.get("junction_5utr_cds_mfe_per_nt")
            j3 = metrics.get("junction_cds_3utr_mfe_per_nt")
            vals = [v for v in (j5, j3) if v is not None]
            host = by_id.get(c["id"])
            e3 = (sum(vals) / len(vals) if vals else None)
            c["archive"]["E3_junction_mfe_per_nt"] = e3
            if host is not None:
                host["archive"]["E3_junction_mfe_per_nt"] = e3
            n += 1
    log(f"  [junction:{target_id}] {n} delivered candidates evaluated")


# ── Arm-level R3 + evaluation assembly (E6 semantics) ───────────────────────
def r3_top1_separation(deliveries: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tops = {p: (deliveries.get(p) or [None])[0] for p in PROFILES}
    pairs, separated = [], 0
    for i in range(len(PROFILES)):
        for j in range(i + 1, len(PROFILES)):
            a, b = tops[PROFILES[i]], tops[PROFILES[j]]
            if a is None or b is None:
                continue
            pairs.append((PROFILES[i], PROFILES[j]))
            d_cai = abs(a["archive"]["E1_cai"] - b["archive"]["E1_cai"])
            d_lam = abs(a["lambda_rank"] - b["lambda_rank"])
            if d_cai >= R3_CAI_SEP or d_lam >= R3_LAMBDA_RANK_SEP:
                separated += 1
    return {
        "separated": separated, "pairs": len(pairs),
        "R3": (separated / len(pairs) >= R3_PAIR_FRACTION) if pairs else False,
        "tops": [{"profile": p,
                  "id": (tops[p] or {}).get("id"),
                  "E1_cai": (tops[p] or {}).get("archive", {}).get("E1_cai"),
                  "lambda_rank": (tops[p] or {}).get("lambda_rank")}
                 for p in PROFILES],
    }


def evaluate_arm(
    deliveries: dict[str, list[dict[str, Any]]],
    pool_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Per-profile evaluation with the E6 decision-① D2 composite + arm R3."""
    r3 = r3_top1_separation(deliveries)
    per_profile = []
    for profile in PROFILES:
        ev = evaluate_delivery(deliveries.get(profile, []), profile, pool_candidates)
        cais = [c["archive"]["E1_cai"] for c in deliveries.get(profile, [])]
        ev["D2_cai_span"] = delivery_cai_span(cais)
        ev["D2"] = d2_composite(ev["D1"], cais)   # decision-① override
        ev["R3"] = r3["R3"]
        ev["JCD"] = jcd_pass(ev)
        ev["composite"] = composite_score(ev)
        per_profile.append(ev)
    return {
        "profiles": per_profile,
        "R3": r3["R3"],
        "R3_separated_pairs": r3["separated"],
        "R3_total_pairs": r3["pairs"],
        "R3_tops": r3["tops"],
        "c_e2e_profiles": mean(p["e2e_pass"] for p in per_profile) if per_profile else 0.0,
    }


# ── One (target × A/C) cell ──────────────────────────────────────────────────
def _delivery_snapshot(delivery: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "id": c["id"], "sequence": c["sequence"], "lambda": c["lambda"],
        "lambda_rank": c["lambda_rank"],
        "constraints": dict(c["constraints"]),
        "archive": dict(c["archive"]),
        "utility": dict(c["utility"]),
    } for c in delivery]


def _pool_summary(pool: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [c for c in pool if c["flags"]["passed"]]
    return {
        "n_candidates": len(pool),
        "n_pass": len(passed),
        "pass_counts_by_constraint": {
            k: sum(1 for c in pool if c["constraints"].get(k)) for k in CONSTRAINT_IDS},
        "max_u_passed": {
            p: (max((c["utility"][p] for c in passed), default=None)) for p in PROFILES},
        "max_constraint_count_passed": (
            max((sum(1 for v in c["constraints"].values() if v) for c in passed),
                default=None)),
    }


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

    # ── Arm C: the shipped production navigation
    log(f"[{stage}:{target_id}] arm C — running production GenNav-λ ...")
    nav = run_navigation(target_id, meta, log=log)
    trace = nav["trace"]
    nav_pool_cds: list[tuple[float, str]] = []
    delivered_by_profile: dict[str, list[str]] = {}
    if nav["success"]:
        for profile in PROFILES:
            recs = ((trace.get("deliveries") or {}).get(profile) or {}).get("candidates") or []
            delivered_by_profile[profile] = []
            for rec in recs:
                seq = _rna(str(rec.get("sequence", "")))
                lam = float(rec.get("lambda", 0.0))  # slim trace record: top-level λ
                if seq and (lam, seq) not in nav_pool_cds:
                    nav_pool_cds.append((lam, seq))
                delivered_by_profile[profile].append(seq)
    sampled_lambdas = sorted({lam for lam, _ in nav_pool_cds})
    rank_map_c = {lam: i for i, lam in enumerate(sampled_lambdas)}  # dynamic rank

    pool_c: list[dict[str, Any]] = []
    if nav_pool_cds:
        utr5_cache = {p: inst.gemorna_utr("5utr", p, target_id) for p in UTR_PRESETS}
        utr3_cache = {p: inst.gemorna_utr("3utr", p, target_id) for p in UTR_PRESETS}
        pool_c = evaluate_full_length(nav_pool_cds, utr5_cache, utr3_cache,
                                      target_id, meta, inst, log=log)
        for cand in pool_c:
            cand["lambda_rank"] = rank_map_c.get(cand["lambda"], 0)
        assign_utilities(pool_c)

    # per-profile C delivery: navigator rank order → each CDS's U-max combo
    by_cds: dict[str, list[dict[str, Any]]] = {}
    for cand in pool_c:
        by_cds.setdefault(cand["cds"], []).append(cand)
    deliveries_c: dict[str, list[dict[str, Any]]] = {}
    for profile in PROFILES:
        dl: list[dict[str, Any]] = []
        for seq in delivered_by_profile.get(profile, []):
            combos = by_cds.get(seq) or []
            if not combos:
                continue
            dl.append(max(combos, key=lambda c: c["utility"][profile]))
        deliveries_c[profile] = dl[:DELIVERY_SIZE]
        for c in deliveries_c[profile]:
            c["flags"]["delivered"] = True

    # ── Delivery-level junction E3 → pool-wide utility reassign (legacy order)
    junction_at_delivery(pool_a, deliveries_a, target_id, log=log)
    if pool_c:
        junction_at_delivery(pool_c, deliveries_c, target_id, log=log)
    assign_utilities(pool_a)
    if pool_c:
        assign_utilities(pool_c)

    # ── Evaluations (identical criteria both arms)
    ev_a = evaluate_arm(deliveries_a, pool_a)
    ev_c = evaluate_arm(deliveries_c, pool_c) if pool_c else {
        "profiles": [], "R3": False, "R3_separated_pairs": 0,
        "R3_total_pairs": 0, "R3_tops": [], "c_e2e_profiles": 0.0,
        "navigation_failed": True,
    }
    ge_3 = len(sampled_lambdas) >= 3  # C-arm gear declaration (E14 semantics)

    rec = {
        "stage": stage,
        "target_id": target_id,
        "species": meta.get("species_for_codon_optimization"),
        "protein_length_aa": meta.get("protein_length_aa"),
        "success": bool(nav["success"]) and len(ev_a["profiles"]) == len(PROFILES),
        "navigation": {
            "success": nav["success"], "errors": nav["errors"],
            "elapsed_seconds": nav["elapsed_seconds"],
            "n_result_candidates": nav["n_result_candidates"],
            "raw_spent": trace.get("raw_spent"),
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
            "pool": _pool_summary(pool_a),
            "deliveries": {p: _delivery_snapshot(dl) for p, dl in deliveries_a.items()},
        },
        "arm_c": {
            "pool": _pool_summary(pool_c) if pool_c else None,
            "dynamic_lambda_rank": {str(k): v for k, v in rank_map_c.items()},
            "deliveries": {p: _delivery_snapshot(dl) for p, dl in deliveries_c.items()},
        },
        "evaluations": {"A": ev_a, "C": ev_c},
        "elapsed_seconds": time.perf_counter() - t0,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    jcds_a = [p["JCD"] for p in ev_a["profiles"]]
    jcds_c = [p["JCD"] for p in ev_c["profiles"]] if ev_c.get("profiles") else [False] * 3
    log(f"[{stage}:{target_id}] done in {rec['elapsed_seconds']:.0f}s — "
        f"JCD A={sum(jcds_a)}/3 C={sum(jcds_c)}/3 "
        f"(nav raw_spent={trace.get('raw_spent')}, pool A pass "
        f"{rec['arm_a']['pool']['n_pass']}/{rec['arm_a']['pool']['n_candidates']})")
    return rec


# ── Endpoints (S2 book §20, verbatim; n = 60) ───────────────────────────────
def aggregate_verdict(records: list[dict[str, Any]]) -> dict[str, Any]:
    targets = [r["target_id"] for r in records]
    ev = {r["target_id"]: r["evaluations"] for r in records}

    def paired(arm_x: str, arm_y: str) -> tuple[list[bool], list[bool],
                                                 list[float], list[float]]:
        jx, jy, cx, cy = [], [], [], []
        for t in targets:
            for p in range(len(PROFILES)):
                ex = ev[t].get(arm_x, {}).get("profiles", [{}])
                ey = ev[t].get(arm_y, {}).get("profiles", [{}])
                ex = ex[p] if len(ex) > p else {}
                ey = ey[p] if len(ey) > p else {}
                jx.append(jcd_pass(ex))
                jy.append(jcd_pass(ey))
                cx.append(composite_score(ex))
                cy.append(composite_score(ey))
        return jx, jy, cx, cy

    def mcnemar(x: list[bool], y: list[bool]) -> dict[str, Any]:
        b = sum(1 for a, c in zip(x, y) if a and not c)
        c_ = sum(1 for a, c in zip(x, y) if not a and c)
        p = float(scipy_stats.binomtest(min(b, c_), b + c_, 0.5,
                                        alternative="two-sided").pvalue) \
            if b + c_ > 0 else 1.0
        return {"b": b, "c": c_, "p": p}

    def wilcoxon_p(x: list[float], y: list[float]) -> float:
        diffs = [b - a for a, b in zip(x, y) if abs(b - a) > 1e-12]
        if len(diffs) < 2:
            return 1.0
        return float(scipy_stats.wilcoxon(diffs).pvalue)

    j_c, j_a, cx_ca, cy_ca = paired("C", "A")
    mc_ca = mcnemar(j_c, j_a)
    w_ca = wilcoxon_p(cx_ca, cy_ca)

    # permutation null on the discordance directions (figure inset): 10⁴, seed 0
    rng = random.Random(PERM_SEED)
    n_disc = mc_ca["b"] + mc_ca["c"]
    null_b = [sum(1 for _ in range(n_disc) if rng.random() < 0.5)
              for _ in range(PERM_DRAWS)]

    c_arms = [ev[t].get("C") for t in targets]
    c_e2e_gene = mean(all(p["e2e_pass"] for p in e["profiles"])
                      for e in c_arms if e and e.get("profiles")) \
        if any(e and e.get("profiles") for e in c_arms) else 0.0
    quality = bool(c_arms) and all(
        e is not None and e.get("profiles")
        and all(p["R1"] and p["R4"] and p["D1"] and p["D2"] and p["D3"]
                for p in e["profiles"])
        and e["R3"]
        for e in c_arms
    ) and all(r["navigation"]["ge_3"] for r in records)
    crit_constraint = (mean(mean(p["constraint_rate"] for p in e["profiles"])
                            for e in c_arms if e and e.get("profiles")) >= 0.9) \
        if any(e and e.get("profiles") for e in c_arms) else False

    endpoint1 = bool(mc_ca["p"] < 0.05 and c_e2e_gene >= 0.8)
    endpoint2 = bool(w_ca < 0.05 and quality and crit_constraint)
    go = endpoint1 or endpoint2

    return {
        "n_pairs": len(j_c),
        "n_targets": len(targets),
        "mcnemar_C_vs_A": mc_ca,
        "wilcoxon_C_vs_A_p": w_ca,
        "permutation_null": {
            "draws": PERM_DRAWS, "seed": PERM_SEED,
            "n_discordant": n_disc, "observed_b": mc_ca["b"],
            "null_b_histogram": {
                str(k): null_b.count(k) for k in range(n_disc + 1)},
            "null_b_mean": mean(null_b),
        },
        "c_e2e_gene": c_e2e_gene,
        "a_e2e_gene": mean(all(p["e2e_pass"] for p in ev[t]["A"]["profiles"])
                           for t in targets),
        "quality_bundle": quality,
        "constraint_rate_C_ge_0.9": crit_constraint,
        "endpoint1_jcd_mcnemar": endpoint1,
        "endpoint2_composite_wilcoxon": endpoint2,
        "endpoint2_not_passed_disclosed": bool(endpoint1 and not endpoint2),
        "go_no_go": "GO" if go else "NO-GO",
    }


# ── Orchestration ────────────────────────────────────────────────────────────
def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


CACHE_FILES = ("gemorna_cds.json", "gemorna_utr.json", "folds.json")


def seed_caches(cache_dir: Path = CACHES_DIR) -> None:
    """Seed a cache dir: exp26's caches first (the Fig-5a realization for its
    five targets), then any entries already accumulated at the shared root."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for name in CACHE_FILES:
        dst = cache_dir / name
        if dst.is_file():
            continue
        src = CACHES_DIR / name if cache_dir != CACHES_DIR else None
        if src is not None and src.is_file():
            dst.write_text(src.read_text(encoding="utf-8"))
            continue
        base = EXP26_FULL / name
        if base.is_file():
            dst.write_text(base.read_text(encoding="utf-8"))
            log_line(f"cache seeded from exp26: {name}")


# ── Orchestration ────────────────────────────────────────────────────────────
def run_stage(stage: str, targets: list[str], *, resume: bool,
              workers: int = 1, worker_id: int | None = None) -> int:
    stage_dir = RESULTS_DIR / stage
    stage_dir.mkdir(parents=True, exist_ok=True)

    # ── worker subprocess mode: own caches + own record file, no write races
    if worker_id is not None:
        out = stage_dir / f"runs_worker{worker_id}.jsonl"
        cache_dir = CACHES_DIR / f"worker{worker_id}"
        seed_caches(cache_dir)
        done = {r["target_id"] for r in load_records(out)}
        inst = Instrument(cache_dir)
        failures = 0
        for target_id in targets:
            if target_id in done:
                log_line(f"[{stage}:w{worker_id}] {target_id} done — skip")
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

    # ── parallel amendment (user-directed 2026-09-02, registered before
    #    re-launch; the Exp-24 convention): target-exclusive workers — each
    #    target is processed by exactly one worker (GEMORNA realization keyed
    #    per target stays single-realized), a target's phases stay sequential
    #    (the navigation algorithm is inherently sequential), per-worker
    #    caches and record files eliminate write races; per-cell wall times
    #    measure the delivered pipeline under concurrent campaign load.
    if workers > 1:
        done: set[str] = set()
        record_files = [stage_dir / "runs.jsonl"]
        record_files += sorted(stage_dir.glob("runs_worker*.jsonl"))
        for path in record_files:
            done |= {r["target_id"] for r in load_records(path)
                     if r.get("success")}
        remaining = [t for t in targets if t not in done]
        chunks: list[list[str]] = [[] for _ in range(workers)]
        for i, t in enumerate(remaining):
            chunks[i % workers].append(t)
        log_line(f"[{stage}] parallel relaunch: {len(done)} done, "
                 f"{len(remaining)} remaining across {workers} workers "
                 f"{[len(c) for c in chunks]}")
        import subprocess
        procs = []
        for k, chunk in enumerate(chunks):
            if not chunk:
                continue
            log_path = stage_dir / f"worker{k}.log"
            lf = log_path.open("w", encoding="utf-8")
            procs.append((k, subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), stage,
                 "--targets", ",".join(chunk), "--worker-id", str(k),
                 "--resume"],
                env={**os.environ, "PYTHONPATH": f"{PROJECT_ROOT}"
                     f":{os.environ.get('PYTHONPATH', '')}"},
                stdout=lf, stderr=subprocess.STDOUT), lf))
        bad = 0
        for k, proc, lf in procs:
            rc = proc.wait()
            lf.close()
            log_line(f"[{stage}] worker{k} exit={rc}")
            bad += (rc != 0)
        # merge: first successful record per target, registered target order
        merged: dict[str, dict[str, Any]] = {}
        for path in record_files + sorted(stage_dir.glob("runs_worker*.jsonl")):
            for r in load_records(path):
                if r.get("success") and r["target_id"] not in merged:
                    merged[r["target_id"]] = r
        ordered = [merged[t] for t in targets if t in merged]
        with (stage_dir / "runs.jsonl").open("w", encoding="utf-8") as fh:
            for r in ordered:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        n_ok = len(ordered)
        log_line(f"[{stage}] merged {n_ok}/{len(targets)} successful records")
        if n_ok < len(targets):
            return 1
        verdict = aggregate_verdict(ordered)
        (stage_dir / "verdict.json").write_text(
            json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        mc = verdict["mcnemar_C_vs_A"]
        log_line(f"[{stage}] verdict: {verdict['go_no_go']} "
                 f"(McNemar p={mc['p']:.3e}, b:c={mc['b']}:{mc['c']}, "
                 f"c_e2e_gene={verdict['c_e2e_gene']:.3f}, "
                 f"n={verdict['n_pairs']})")
        return 0

    # ── sequential mode (the original registration)
    seed_caches()
    out = stage_dir / "runs.jsonl"
    done = {r["target_id"] for r in load_records(out)} if resume else set()
    if done and not resume:
        out.write_text("")
        done = set()
    inst = Instrument(CACHES_DIR)

    records: list[dict[str, Any]] = []
    failures = 0
    for target_id in targets:
        if target_id in done:
            log_line(f"[{stage}] {target_id} already done — skip")
            records.extend(load_records(out))
            continue
        try:
            rec = run_cell(target_id, stage, inst)
        except Exception as exc:  # noqa: BLE001 — record honestly, continue
            failures += 1
            log_line(f"[{stage}:{target_id}] FAILURE: {exc!r}")
            rec = {"stage": stage, "target_id": target_id, "success": False,
                   "error": repr(exc),
                   "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if rec.get("success"):
            records.append(rec)
    records = [r for r in load_records(out) if r.get("success")]

    if not records:
        log_line(f"[{stage}] no successful records — no verdict")
        return 1
    verdict = aggregate_verdict(records)
    verdict_path = stage_dir / "verdict.json"
    verdict_path.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    log_line(f"[{stage}] verdict -> {verdict_path}: {verdict['go_no_go']} "
             f"(McNemar p={verdict['mcnemar_C_vs_A']['p']:.3e}, "
             f"b:c={verdict['mcnemar_C_vs_A']['b']}:{verdict['mcnemar_C_vs_A']['c']}, "
             f"c_e2e_gene={verdict['c_e2e_gene']:.3f}, n={verdict['n_pairs']})")
    return 0 if failures == 0 else 2


# ── Verify: recompute everything from stored records ────────────────────────
def _recompute_cell(rec: dict[str, Any]) -> dict[str, Any]:
    """Recompute per-cell evaluation primitives from the stored snapshots."""
    out: dict[str, Any] = {"target_id": rec["target_id"]}
    for arm in ("A", "C"):
        per = []
        deliveries = rec[f"arm_{arm.lower()}"]["deliveries"]
        for profile in PROFILES:
            dl = deliveries.get(profile, [])
            ids = [c["id"] for c in dl]
            uvals = [c["utility"][profile] for c in dl]
            u_rank = [c["id"] for c in sorted(
                dl, key=lambda c: c["utility"][profile], reverse=True)]
            shared = [i for i in ids if i in u_rank]
            rho = 1.0 if len(shared) < 2 else float(scipy_stats.spearmanr(
                [shared.index(i) for i in shared],
                [u_rank.index(i) for i in shared]).statistic)
            min_dist = min(
                diversity_distance({"sequence": dl[i]["sequence"]},
                                   {"sequence": dl[j]["sequence"]})
                for i in range(len(dl)) for j in range(i + 1, len(dl))
            ) if len(dl) >= 2 else 0.0
            cais = [c["archive"]["E1_cai"] for c in dl]
            ev = {
                "profile": profile,
                "delivered_ids": ids,
                "e2e_pass": len(dl) == DELIVERY_SIZE and all(
                    all(c["constraints"].values()) for c in dl),
                "constraint_rate": mean(
                    sum(1 for v in c["constraints"].values() if v) / len(CONSTRAINT_IDS)
                    for c in dl) if dl else 0.0,
                "R1": rho >= 1.0 - 1e-6,
                "D1_min_dist": min_dist, "D1": min_dist >= DIVERSITY_GATE,
                "D2_cai_span": delivery_cai_span(cais),
            }
            ev["D2"] = d2_composite(ev["D1"], cais)
            prs = [c["archive"]["E7_pair_ratio"] for c in dl]
            stems = [c["archive"]["C7_longest_stem"] for c in dl]
            ev["D3"] = ((max(prs) - min(prs)) >= D3_PAIR_RATIO_RANGE or
                        (max(stems) - min(stems)) >= D3_STEM_RANGE) if dl else False
            per.append(ev)
        tops = {p: (deliveries.get(p) or [None])[0] for p in PROFILES}
        pairs = separated = 0
        for i in range(len(PROFILES)):
            for j in range(i + 1, len(PROFILES)):
                a, b = tops[PROFILES[i]], tops[PROFILES[j]]
                if a is None or b is None:
                    continue
                pairs += 1
                if (abs(a["archive"]["E1_cai"] - b["archive"]["E1_cai"]) >= R3_CAI_SEP
                        or abs(a["lambda_rank"] - b["lambda_rank"]) >= R3_LAMBDA_RANK_SEP):
                    separated += 1
        r3 = (separated / pairs >= R3_PAIR_FRACTION) if pairs else False
        for ev in per:
            ev["R3"] = r3
            ev["JCD"] = jcd_pass(ev)
            ev["composite"] = composite_score(ev)
        out[arm] = {"profiles": per, "R3": r3,
                    "R3_separated_pairs": separated, "R3_total_pairs": pairs}
    return out


def verify(stage: str) -> int:
    stage_dir = RESULTS_DIR / stage
    records = [r for r in load_records(stage_dir / "runs.jsonl") if r.get("success")]
    assert records, "no successful records"
    mismatches = 0
    for rec in records:
        recomputed = _recompute_cell(rec)
        for arm in ("A", "C"):
            stored = rec["evaluations"].get(arm) or {}
            if not stored.get("profiles"):
                continue
            for p_new, p_old in zip(recomputed[arm]["profiles"], stored["profiles"]):
                for key in ("e2e_pass", "constraint_rate", "D1_min_dist", "D1",
                            "D2_cai_span", "D2", "D3", "R3", "JCD"):
                    if p_new[key] != p_old.get(key):
                        mismatches += 1
                        log_line(f"VERIFY MISMATCH {rec['target_id']} {arm} "
                                 f"{p_new['profile']}.{key}: "
                                 f"{p_new[key]!r} != {p_old.get(key)!r}")
                if abs(p_new["composite"] - p_old["composite"]) > 1e-12:
                    mismatches += 1
                    log_line(f"VERIFY MISMATCH {rec['target_id']} {arm} "
                             f"{p_new['profile']}.composite")
    verdict = aggregate_verdict(records)
    stored_verdict = json.loads((stage_dir / "verdict.json").read_text(encoding="utf-8"))
    canon = json.dumps(verdict, sort_keys=True)
    stored_canon = json.dumps(stored_verdict, sort_keys=True)
    if canon != stored_canon:
        mismatches += 1
        log_line("VERIFY MISMATCH: verdict differs")
    log_line(f"[verify:{stage}] {'BYTE-IDENTICAL' if mismatches == 0 else f'{mismatches} MISMATCHES'} "
             f"over {len(records)} records + verdict")
    return 0 if mismatches == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["pilot", "full", "verify"])
    parser.add_argument("stage", nargs="?", default=None,
                        help="stage dir for verify (pilot|full)")
    parser.add_argument("--targets", default=None,
                        help="comma-separated target override")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=1,
                        help="target-exclusive parallel workers (parallel speed "
                             "amendment, user-directed 2026-09-02)")
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
