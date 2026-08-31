#!/usr/bin/env python3
"""Experiment 16 (paper §2.3 experiment 8, Fig. 3i): confounded improvement —
the coordination-loop apparent effect under budget-matched and
fixed-resampling controls (third programme reset, 2026-08-29).

Pre-registration
----------------
* Question. The platform's removed coordination loop ("BMC", bounded
  multi-round coordination) had shown an apparent main effect on the aptamer
  workflow — EGARPS component best-of-pool, paired Wilcoxon P = 2.1e-4,
  Cliff's δ = +0.46 — that dissolved under two pre-registered controls
  (budget matching δ = 0.278 NS; fixed resampling δ = 0.222 NS), motivating
  the framework's removal (DECISIONS (a)/(f)/(m)). This run re-measures the
  whole falsification arc live on the reset platform, at the user-confirmed
  full-panel scale.
* Legacy protocol (recovered verbatim from git 1b45138~1 after the
  2026-08-18/25 deletions; drivers `run_bmc_type2_ablation.py`,
  `run_budget_matched_control.py`, `run_p3_guided_vs_unguided.py`):
  aptamer_length=30, odesign_seeds = SEED_SETS[i] with
  SEED_SETS = [[42,123],[7,99],[2024,31415]], Serial = one pass
  n_odesign_samples=8; BMCx1 = pass 1 (n=8) -> deterministic coordinator
  diagnosis -> regeneration -> union pool ~16; serial_ext16 = one pass
  n=16, same seeds; P3 unguided_2pass = forced content-free regeneration
  (seeds+1, n=8, unchanged hotspot/length). Coordinator = the removed
  AptamerCoordinator, rule-based by design (intentionally NOT an LLM):
  utopian reference point over the pool's three objective components
  (egarps/rhofold/iptm, all maximized), min-max normalized (utopian -> 1.0
  per dim); diagnosis set = ASF best + per-objective leaders; issues =
  normalized gaps, merged max-violation per type with source metrics;
  feedback: EGARPS/IPTM gap -> Target hotspot_expansion (+2, window clamp
  [3,10]) AND Aptamer n_samples+5 / seeds+1; RHOFOLD gap -> Aptamer length
  +10 (source pLDDT < 60) else +5, seeds+1; Target branch preempts Aptamer
  when the expanded hotspot differs, regenerating 8 with unchanged params.
* Registered legacy numbers this run re-measures (PAPER_FACT_SHEET §2/§3):
  Fig 4 headline δ = +0.4570637, p = 2.098e-4 (n = 19 targets; Ferritin =
  registered zero-output boundary); P0 δ = 0.2777778, p = 0.1293945,
  bmc wins 9/12 (4 targets × 3 seeds); P3 δ = 0.2222222, p = 0.1098633,
  guided wins 9/12; E2 self-audit survival 0/2 vs the 70% threshold.
* Reconstruction scope. The BMC framework is gone from the platform and
  stays gone: the loop above is rebuilt HERE, at the driver level, as the
  object of study. The platform itself is untouched; every generation and
  evaluation call goes through the production Layer-2 workflow in-process
  (RnaAptamerDesignWorkflow with its capability registry, auto service
  pre-flight, CapGate advisory per the registered regression convention,
  every ToolExecutor call audited to the platform audit trail).
* Arms (each cell = (target, seed_idx); panel = all 20 RNA-BioBench-Aptamer
  targets × 3 seed sets = 60 cells/arm, user-confirmed 2026-08-29):
  - serial8  : legacy Serial (naive baseline, pool 8).
  - loop16   : legacy BMCx1 reconstructed (pool 8 + 8/13, or early stop at
               pool 8 on zero violation — the legacy no_violation semantics).
  - serial16 : legacy serial_ext16 (budget-matched one-pass pool 16).
  - fixed16  : legacy P3 unguided_2pass (forced seeds+1 second pass, pool 16).
  Fresh workflow instance per cell (the workflow caches resolved hotspots in
  `_workflow_state._cached_hotspot`; reuse would leak a target's hotspot into
  the next cell).
* Primary metric: egarps_component best-of-pool per cell — the legacy
  headline metric and precisely the oracle that profiling decertified
  (SelfModel: egarps_native_probability screening/ranking/docking all
  `failed`); measuring the confound on it is the point. Secondary:
  rhofold/iptm best-of-pool, realized pool sizes, loop branch/stop trace.
* Hypotheses (direction pre-registered):
  H1 apparent effect   : loop16 > serial8, δ >= 0.3 (budget confound present).
  H2 budget-matched    : loop16 vs serial16, δ < 0.3 and Wilcoxon NS.
  H3 fixed-resampling  : loop16 vs fixed16, δ < 0.3 and Wilcoxon NS.
  Gate (P0/P3 convention): GO iff δ >= 0.3.
* Statistics: cells paired by (target_id, seed_idx); paired Wilcoxon
  (two-sided, exact where scipy chooses) + two-sample Cliff's δ (the legacy
  convention — all cross pairs); sign-flip permutation null (10^4) for δ;
  target-level aggregation (mean over seeds) as sensitivity. Pairs where
  either side lacks the primary metric are dropped and disclosed; Ferritin
  cells are expected to fail generation (registered boundary) and drop out
  of both sides symmetrically.
* Self-audit (E2 four-step protocol re-run on the re-measured numbers):
  claim 1 "coordination improves aptamer design" and claim 2 "designed
  candidates beat the pegaptanib literature anchor" → declare capability
  dependencies → re-check against the packaged SelfModel (structure-oracle
  grades) → confound control (H2/H3 re-measured) → gated verdict; survival
  threshold 70% (registered). Deterministic — no LLM adjudication.
* Zero-intervention rule: no thresholds, no parameter sweeps beyond the
  legacy-fixed values above, no platform modifications; services pre-warmed
  on GPUs 0-2 and left untouched; inputs verbatim from the benchmark JSONs
  (structure + chain + known hotspots where present; auto hotspot
  identification otherwise — the production path).

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp16_confounded_improvement.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp16_confounded_improvement.py --resume
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp16_confounded_improvement.py --analyze-only
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("RNADA_CAPGATE", "advisory")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "targets"
STRUCT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp16_confounded_improvement"

SEED_SETS = [[42, 123], [7, 99], [2024, 31415]]
OBJECTIVE_KEYS = ["egarps_component", "rhofold_component", "iptm_component"]
ARMS = ["serial8", "loop16", "serial16", "fixed16"]
COMPARISONS = [
    ("apparent", "loop16", "serial8"),
    ("budget_matched", "loop16", "serial16"),
    ("fixed_resampling", "loop16", "fixed16"),
]
GATE_DELTA = 0.3
N_PERMUTATIONS = 10_000
PILOT_TARGETS = ["Lysozyme", "Thrombin"]

LEGACY_REFERENCE = {
    "fig4_headline": {"delta": 0.45706371191135736, "p": 2.09808349609375e-04,
                      "n": 19, "note": "egarps_component best-of-pool, BMCx1 vs Serial"},
    "p0_budget_matched": {"delta": 0.2777777777777778, "p": 0.12939453125,
                          "wins": "9/12", "gate": GATE_DELTA, "verdict": "NO-GO"},
    "p3_fixed_resampling": {"delta": 0.2222222222222222, "p": 0.10986328125,
                            "wins": "9/12", "gate": GATE_DELTA, "verdict": "NO-GO"},
    "e2_self_audit": {"survival": "0/2", "threshold": 0.7},
    "source": "git 1b45138~1 (drivers deleted 2026-08-18) + PAPER_FACT_SHEET §2/§3",
}


# ─────────────────────────── target helpers ─────────────────────────────

def find_structure(pdb_id: str) -> Path | None:
    """Locate the target's structure file (case-tolerant) under structures/."""
    for pattern in (f"{pdb_id.lower()}*.pdb", f"{pdb_id.upper()}*.pdb",
                    f"*{pdb_id.lower()}*", f"*{pdb_id}*"):
        for cand in STRUCT_DIR.glob(pattern):
            return cand
    return None


# ─────────────────────── production workflow runner ─────────────────────

def run_pass(params: dict) -> dict:
    """One production RnaAptamerDesignWorkflow run (fresh instance: the
    workflow caches the auto-identified hotspot in workflow state)."""
    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.rna_aptamer_design import (
        RnaAptamerDesignInput,
        RnaAptamerDesignWorkflow,
    )

    executor = ToolExecutor(build_default_tool_registry())
    registry = build_default_capability_registry(executor)
    wf = RnaAptamerDesignWorkflow(registry)
    wf.auto_start_services = True

    inp = RnaAptamerDesignInput(**params)
    result = wf.run(inp)

    candidates = []
    for c in result.all_candidates or []:
        scores = {k: (None if c.scores.get(k) is None else float(c.scores[k]))
                  for k in OBJECTIVE_KEYS}
        metrics = c.metadata.get("metrics_bundle") or {}
        candidates.append({
            "id": c.id,
            "sequence": c.sequence,
            "scores": scores,
            "rhofold_mean_plddt": metrics.get("rhofold_mean_plddt"),
        })
    return {
        "workflow_success": bool(result.success),
        "errors": [str(e) for e in (result.errors or [])],
        "candidates": candidates,
        "resolved_hotspot": wf._workflow_state.get("_cached_hotspot"),
    }


def base_params(meta: dict, struct: Path, seed_idx: int, n_samples: int, *,
                hotspot: str | None = None, seeds_shift: int = 0,
                aptamer_length: int | None = None) -> dict:
    seeds = [s + seeds_shift for s in SEED_SETS[seed_idx]]
    d = {
        "protein_structure_path": str(struct),
        "chain_id": meta.get("pdb_chain") or "A",
        "aptamer_length": aptamer_length if aptamer_length is not None else 30,
        "n_odesign_samples": n_samples,
        "odesign_seeds": seeds,
    }
    if hotspot:
        d["hotspot_residues"] = hotspot
    return d


# ─────────── deterministic coordinator reconstruction (legacy) ──────────

def diagnose_pool(candidates: list[dict]) -> dict:
    """Legacy AptamerCoordinator diagnosis, verbatim rules.

    Utopian reference over the pool's three components; min-max normalized
    (utopian -> 1.0 per dim, degenerate span -> 0.5). Diagnosis set = ASF
    best (equal weights, rho = 1e-3) + per-objective leaders. Issues = gaps
    of the diagnosed candidates, merged max-violation per type.
    Returns {issue_type: {"violation": g, "source_index": i}}.
    """
    bounds: dict[str, tuple[float, float]] = {}
    for k in OBJECTIVE_KEYS:
        vals = [c["scores"][k] for c in candidates if c["scores"].get(k) is not None]
        if vals:
            bounds[k] = (min(vals), max(vals))

    def norm(k: str, v: float) -> float:
        lo, hi = bounds[k]
        return 0.5 if hi == lo else (v - lo) / (hi - lo)

    ref = {k: 1.0 for k in bounds}

    def asf(c: dict) -> float:
        diffs = [ref[k] - norm(k, c["scores"][k])
                 for k in bounds if c["scores"].get(k) is not None]
        if not diffs:
            return float("inf")
        return max(diffs) + 1e-3 * sum(abs(d) for d in diffs)

    diag_idx: set[int] = set()
    scoreable = [i for i, c in enumerate(candidates)
                 if any(c["scores"].get(k) is not None for k in bounds)]
    if scoreable:
        diag_idx.add(min(scoreable, key=lambda i: asf(candidates[i])))
    for k in bounds:
        contenders = [i for i, c in enumerate(candidates) if c["scores"].get(k) is not None]
        if contenders:
            diag_idx.add(max(contenders, key=lambda i: candidates[i]["scores"][k]))

    issues: dict[str, dict] = {}
    for i in diag_idx:
        c = candidates[i]
        for k in bounds:
            if c["scores"].get(k) is None:
                continue
            gap = ref[k] - norm(k, c["scores"][k])
            if gap > 0.0:
                t = f"{k.upper()}_BELOW_REFERENCE"
                if t not in issues or gap > issues[t]["violation"]:
                    issues[t] = {"violation": gap, "source_index": i}
    return issues


def expand_hotspot(protein_path: str, chain_id: str, hotspot: str, window: int) -> str:
    """Legacy `_expand_hotspot_residues`, verbatim semantics: add ±window
    adjacent residues that exist in the structure; keep the chain's format."""
    try:
        from Bio.PDB import MMCIFParser, PDBParser
    except ImportError:
        return hotspot
    suffix = Path(protein_path).suffix.lower()
    try:
        parser = MMCIFParser(QUIET=True) if suffix in {".cif", ".mmcif"} else PDBParser(QUIET=True)
        structure = parser.get_structure("prot", protein_path)
    except Exception:
        return hotspot

    existing: set[int] = set()
    for model in structure:
        for ch in model:
            if ch.id == chain_id:
                for residue in ch:
                    if not residue.id[0].strip():
                        existing.add(residue.id[1])
    if not existing:
        return hotspot

    expanded: set[str] = set()
    for part in hotspot.split(","):
        part = part.strip()
        if not part:
            continue
        if "/" in part:
            cid, num_str = part.split("/", 1)
        else:
            cid, num_str = chain_id, part
        try:
            num = int(num_str)
        except ValueError:
            expanded.add(f"{cid}/{num_str}")
            continue
        for n in range(num - window, num + window + 1):
            if n in existing:
                expanded.add(f"{cid}/{n}")
    return ",".join(sorted(expanded, key=lambda s: (s.split("/", 1)[0], s.split("/", 1)[1])))


def plan_regeneration(issues: dict, candidates: list[dict], struct: Path,
                      chain_id: str, hotspot: str) -> dict:
    """Legacy broadcast_feedback + _regenerate_modules, verbatim rules."""
    types = set(issues)
    target_fb = bool(types & {"EGARPS_COMPONENT_BELOW_REFERENCE",
                              "IPTM_COMPONENT_BELOW_REFERENCE"})
    rhofold_fb = "RHOFOLD_COMPONENT_BELOW_REFERENCE" in types

    plan = {"branch": None, "hotspot": hotspot, "n_samples": 8,
            "seeds_shift": 0, "aptamer_length": None}

    if target_fb:
        window = max(3, min(3 + 2, 10))  # hotspot_expansion delta = 2.0, clamp [3, 10]
        expanded = expand_hotspot(str(struct), chain_id, hotspot, window)
        if expanded and expanded != hotspot:
            # Target branch: regenerate 8 with expanded hotspot, all else unchanged.
            plan.update(branch="target", hotspot=expanded)
            return plan
        # legacy fallback: expansion produced no change -> Aptamer branch
    if target_fb or rhofold_fb:
        plan["branch"] = "aptamer"
        plan["seeds_shift"] = 1  # seed_change
        if target_fb:
            plan["n_samples"] = min(20, 8 + 5)  # n_samples_delta = 5
        if rhofold_fb:
            src = candidates[issues["RHOFOLD_COMPONENT_BELOW_REFERENCE"]["source_index"]]
            plddt = src.get("rhofold_mean_plddt")
            delta_len = 10 if (plddt is not None and float(plddt) < 60.0) else 5
            plan["aptamer_length"] = min(200, 30 + delta_len)
    return plan


# ─────────────────────────── cell runners ───────────────────────────────

def _pool_objectives(pool: list[dict]) -> list[dict]:
    return [{k: c["scores"][k] for k in OBJECTIVE_KEYS} for c in pool]


def _best_of(pool: list[dict], key: str) -> float | None:
    vals = [c["scores"][key] for c in pool if c["scores"].get(key) is not None]
    return max(vals) if vals else None


def run_cell(arm: str, meta: dict, struct: Path, seed_idx: int) -> dict:
    t0 = time.perf_counter()
    rec: dict = {
        "arm": arm, "target_id": meta["target_id"], "pdb_id": meta["pdb_id"],
        "seed_idx": seed_idx, "seeds": SEED_SETS[seed_idx],
        "success": False, "error": None,
    }
    try:
        if arm == "serial8":
            p1 = run_pass(base_params(meta, struct, seed_idx, 8))
            pool = p1["candidates"]
            trace = {"passes": 1, "stop": None, "branch": None}
            passes_ok = p1["workflow_success"]
        elif arm == "serial16":
            p1 = run_pass(base_params(meta, struct, seed_idx, 16))
            pool = p1["candidates"]
            trace = {"passes": 1, "stop": None, "branch": None}
            passes_ok = p1["workflow_success"]
        elif arm == "loop16":
            p1 = run_pass(base_params(meta, struct, seed_idx, 8))
            pool = list(p1["candidates"])
            trace = {"passes": 1, "stop": None, "branch": None, "issues": None}
            passes_ok = p1["workflow_success"]
            hotspot = (p1["resolved_hotspot"]
                       or meta.get("known_hotspot_residues") or None)
            if p1["workflow_success"] and pool and hotspot:
                issues = diagnose_pool(pool)
                trace["issues"] = {k: round(v["violation"], 4) for k, v in issues.items()}
                if not issues:
                    trace["stop"] = "no_violation"  # legacy early stop, pool stays 8
                else:
                    plan = plan_regeneration(issues, pool, struct,
                                             meta.get("pdb_chain") or "A", hotspot)
                    p2 = run_pass(base_params(
                        meta, struct, seed_idx, plan["n_samples"],
                        hotspot=plan["hotspot"],
                        seeds_shift=plan["seeds_shift"],
                        aptamer_length=plan["aptamer_length"]))
                    pool = pool + p2["candidates"]
                    passes_ok = passes_ok and p2["workflow_success"]
                    trace.update(passes=2, branch=plan["branch"],
                                 stop="max_rounds_reached (1)",
                                 regenerated_n=plan["n_samples"],
                                 length_override=plan["aptamer_length"],
                                 hotspot_changed=(plan["hotspot"] != hotspot))
            elif p1["workflow_success"]:
                trace["stop"] = "missing_hotspot"
        elif arm == "fixed16":
            p1 = run_pass(base_params(meta, struct, seed_idx, 8))
            hotspot = (p1["resolved_hotspot"]
                       or meta.get("known_hotspot_residues") or None)
            p2 = run_pass(base_params(meta, struct, seed_idx, 8,
                                      hotspot=hotspot, seeds_shift=1))
            pool = list(p1["candidates"]) + list(p2["candidates"])
            trace = {"passes": 2, "stop": "forced", "branch": "fixed_resample"}
            passes_ok = p1["workflow_success"] and p2["workflow_success"]
        else:
            raise ValueError(f"unknown arm {arm}")

        rec.update({
            "success": bool(passes_ok and pool),
            "primary": _best_of(pool, "egarps_component"),
            "best": {k: _best_of(pool, k) for k in OBJECTIVE_KEYS},
            "pool_size": len(pool),
            "pool_objectives": _pool_objectives(pool),
            "trace": trace,
        })
    except Exception as exc:  # record and continue
        rec["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        rec["elapsed_seconds"] = round(time.perf_counter() - t0, 1)
    return rec


# ─────────────────────────── statistics ─────────────────────────────────

def cliffs_delta_two_sample(x: list[float], y: list[float]) -> float:
    """Cliff's δ over all cross pairs (the legacy convention)."""
    gt = sum(1 for a in x for b in y if a > b)
    lt = sum(1 for a in x for b in y if a < b)
    return (gt - lt) / (len(x) * len(y))


def paired_analysis(records: list[dict], name: str, arm_a: str, arm_b: str,
                    key: str = "egarps_component") -> dict:
    from scipy import stats

    by_cell: dict[tuple, dict] = {}
    for r in records:
        if r.get("arm") in (arm_a, arm_b) and r.get("primary") is not None:
            by_cell.setdefault((r["target_id"], r["seed_idx"]), {})[r["arm"]] = r
    pairs = [v for v in by_cell.values() if arm_a in v and arm_b in v]
    a = [p[arm_a]["best"][key] for p in pairs]
    b = [p[arm_b]["best"][key] for p in pairs]
    n = len(pairs)
    out: dict = {"comparison": name, "arm_a": arm_a, "arm_b": arm_b, "metric": key,
                 "n_pairs": n, "dropped_cells": len(by_cell) - n,
                 "a_wins": sum(1 for x, y in zip(a, b) if x > y),
                 "ties": sum(1 for x, y in zip(a, b) if x == y)}
    if n == 0:
        return out
    out["median_a"] = sorted(a)[n // 2] if n % 2 else (sorted(a)[n // 2 - 1] + sorted(a)[n // 2]) / 2
    out["median_b"] = sorted(b)[n // 2] if n % 2 else (sorted(b)[n // 2 - 1] + sorted(b)[n // 2]) / 2
    out["delta"] = cliffs_delta_two_sample(a, b)
    if n >= 6 and len(set(a)) > 1 or len(set(b)) > 1:
        try:
            res = stats.wilcoxon(a, b, alternative="two-sided")
            out["p_wilcoxon"] = float(res.pvalue)
        except ValueError:
            out["p_wilcoxon"] = 1.0

    # Sign-flip permutation null for delta (paired exchangeability).
    import random as _random
    rng = _random.Random(20260829)
    diffs_null = []
    base_pairs = list(zip(a, b))
    for _ in range(N_PERMUTATIONS):
        xa, xb = [], []
        for x, y in base_pairs:
            if rng.random() < 0.5:
                xa.append(y); xb.append(x)
            else:
                xa.append(x); xb.append(y)
        diffs_null.append(cliffs_delta_two_sample(xa, xb))
    diffs_null.sort()
    out["perm_null"] = {"n": N_PERMUTATIONS, "mean": sum(diffs_null) / len(diffs_null),
                        "p_perm": sum(1 for d in diffs_null if abs(d) >= abs(out["delta"])) / len(diffs_null),
                        "q025": diffs_null[int(0.025 * len(diffs_null))],
                        "q975": diffs_null[int(0.975 * len(diffs_null)) - 1],
                        "hist": _histogram(diffs_null)}
    out["gate_pass"] = bool(out["delta"] >= GATE_DELTA)
    out["verdict"] = "GO" if out["gate_pass"] else "NO-GO"

    # Sensitivity: target-level aggregation (mean over seeds).
    by_target: dict[str, dict] = {}
    for p in pairs:
        tid = p[arm_a]["target_id"]
        by_target.setdefault(tid, {"a": [], "b": []})
        by_target[tid]["a"].append(p[arm_a]["best"][key])
        by_target[tid]["b"].append(p[arm_b]["best"][key])
    ta = [sum(v["a"]) / len(v["a"]) for v in by_target.values()]
    tb = [sum(v["b"]) / len(v["b"]) for v in by_target.values()]
    out["target_level"] = {"n": len(ta),
                           "delta": cliffs_delta_two_sample(ta, tb) if ta else None}
    return out


def _histogram(values: list[float], bins: int = 41) -> list[list[float]]:
    lo, hi = min(values), max(values)
    if lo == hi:
        return [[lo, len(values)]]
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        idx = min(bins - 1, int((v - lo) / width))
        counts[idx] += 1
    return [[round(lo + (i + 0.5) * width, 4), c] for i, c in enumerate(counts)]


# ─────────────────────────── self-audit ─────────────────────────────────

def self_audit(analyses: dict[str, dict]) -> dict:
    """E2 four-step protocol, deterministic, re-run on the re-measured numbers."""
    self_model_path = PROJECT_ROOT / "agent_core" / "calibrated" / "default_self_model.json"
    sm = json.loads(self_model_path.read_text())
    grades: dict[str, dict] = {}
    for rec in sm.get("records", []):
        if rec.get("task_type") == "rna_aptamer_design" and rec["oracle"] in (
                "egarps_native_probability", "rhofold_mean_plddt", "proteinx_ipTM"):
            for cap, info in rec["capabilities"].items():
                grades.setdefault(rec["oracle"], {})[cap] = info["grade"]

    bm = analyses.get("budget_matched", {})
    fr = analyses.get("fixed_resampling", {})
    ap = analyses.get("apparent", {})

    claims = []

    # Claim 1: "coordination improves aptamer design (Fig 4)"
    c1_deps = ["egarps_native_probability (primary metric)", "rhofold_mean_plddt", "proteinx_ipTM"]
    c1_profile_ok = all(g == "verified" for caps in grades.values() for g in caps.values())
    c1_confound_ok = bool(bm.get("gate_pass")) or bool(fr.get("gate_pass"))
    claims.append({
        "claim": "coordination improves aptamer design (legacy Fig 4 main effect)",
        "step1_dependencies": c1_deps,
        "step2_profile_recheck": {o: grades.get(o) for o in
                                  ("egarps_native_probability", "rhofold_mean_plddt", "proteinx_ipTM")},
        "step2_pass": c1_profile_ok,
        "step3_confound_control": {
            "apparent_delta": ap.get("delta"), "apparent_p": ap.get("p_wilcoxon"),
            "budget_matched_delta": bm.get("delta"), "budget_matched_p": bm.get("p_wilcoxon"),
            "fixed_resampling_delta": fr.get("delta"), "fixed_resampling_p": fr.get("p_wilcoxon"),
        },
        "step3_pass": c1_confound_ok,
        "step4_verdict": "survives" if (c1_profile_ok and c1_confound_ok) else "retired",
    })

    # Claim 2: "designed candidates beat the pegaptanib literature anchor (Fig 7B)"
    c2_profile_ok = grades.get("egarps_native_probability", {}).get("screening") == "verified"
    claims.append({
        "claim": "designed candidates beat the pegaptanib literature anchor (legacy Fig 7B)",
        "step1_dependencies": ["egarps_native_probability (cross-source complex scoring)"],
        "step2_profile_recheck": {"egarps_native_probability": grades.get("egarps_native_probability")},
        "step2_pass": c2_profile_ok,
        "step3_confound_control": {
            "basis": "cross-complex-source comparability (ODesign complexes vs PDB 4QXX) "
                     "+ unrepresentable 2'-F/PEG modifications — registered in E2; unchanged",
        },
        "step3_pass": False,
        "step4_verdict": "survives" if (c2_profile_ok) else "retired",
    })

    survived = sum(1 for c in claims if c["step4_verdict"] == "survives")
    return {"protocol": "declare dependencies -> profile re-check -> confound control -> gated verdict",
            "survival": f"{survived}/{len(claims)}",
            "survival_fraction": survived / len(claims),
            "threshold": 0.7, "threshold_met": (survived / len(claims)) >= 0.7,
            "claims": claims}


# ─────────────────────────── orchestration ──────────────────────────────

def record_files() -> list[Path]:
    """All record shards: the single-process file plus every parallel worker's."""
    return [RESULTS_DIR / "records.jsonl"] + sorted(
        RESULTS_DIR.glob("records_worker*.jsonl"))


def load_all_records() -> list[dict]:
    """Merged records across shards, deduped per (arm, target, seed), latest wins
    (the legacy P3 same-job dedupe convention; duplicates can only arise from a
    stolen stale claim whose original worker later finished)."""
    merged: dict[tuple, dict] = {}
    for p in record_files():
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            merged[(r["arm"], r["target_id"], r["seed_idx"])] = r
    return list(merged.values())


def load_done() -> set[tuple]:
    done = set()
    for r in load_all_records():
        if r.get("success"):
            done.add((r["arm"], r["target_id"], r["seed_idx"]))
    return done


# ── claim-based cell-level parallelism (multiple identical driver processes;
#    the platform is untouched — concurrent workers are concurrent production
#    users of the same HTTP services; audit appends are O_APPEND single-line) ──

CLAIMS_DIR = RESULTS_DIR / "claims"
STEAL_AFTER_S = 14400  # slowest observed cell ~1 h; steal a stale claim after 4 h


def try_claim(cell_key: str, worker_id: int) -> bool:
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    d = CLAIMS_DIR / cell_key
    try:
        d.mkdir()
    except FileExistsError:
        try:
            age = time.time() - d.stat().st_mtime
        except OSError:
            return False
        if age > STEAL_AFTER_S:
            shutil.rmtree(d, ignore_errors=True)
            try:
                d.mkdir()
            except FileExistsError:
                return False
        else:
            return False
    (d / "meta.json").write_text(
        json.dumps({"worker": worker_id, "claimed_at": time.time()}))
    return True


def summarize(records: list[dict]) -> dict:
    analyses = {name: paired_analysis(records, name, a, b)
                for name, a, b in COMPARISONS}
    by_arm: dict[str, dict] = {}
    for arm in ARMS:
        rs = [r for r in records if r.get("arm") == arm]
        ok = [r for r in rs if r.get("success")]
        by_arm[arm] = {
            "cells_run": len(rs), "cells_ok": len(ok),
            "pool_size_median": _median([r["pool_size"] for r in ok]) if ok else None,
            "elapsed_median_s": _median([r["elapsed_seconds"] for r in ok]) if ok else None,
            "primary_median": _median([r["primary"] for r in ok if r.get("primary") is not None]),
        }
    failures = [{"arm": r["arm"], "target_id": r["target_id"], "seed_idx": r["seed_idx"],
                 "error": r.get("error") or r.get("trace", {}).get("stop")}
                for r in records if not r.get("success")]
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "capgate_policy": os.environ.get("RNADA_CAPGATE", "enforce"),
        "deployment_topology": {
            "egarps_url": os.environ.get("EXP16_EGARPS_URL", "default (127.0.0.1:8023, GPU0)"),
            "proteinx_url": os.environ.get("EXP16_PROTEINX_URL", "default (127.0.0.1:8022, GPU0)"),
            "note": "replicas of the same service code+checkpoints on GPU1/2 to relieve the "
                    "GPU0 bottleneck; device placement does not affect scores (exp10 convention)",
        },
        "gate_delta": GATE_DELTA,
        "legacy_reference": LEGACY_REFERENCE,
        "n_records": len(records),
        "arms": by_arm,
        "failures": failures,
        "analyses": analyses,
        "self_audit": self_audit(analyses),
    }


def _median(vals: list) -> float | None:
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


# ── deployment-topology steering (experiment layer; zero platform change) ──
#
# The aptamer chain's heavy services all sit on GPU0 (odesign/egarps/proteinx;
# audited share of tool time: egarps 51%, proteinx 25%, odesign 9%) while
# GPU1 hosts only RhoFold (14%) and GPU2 nothing. With EXP16_EGARPS_URL /
# EXP16_PROTEINX_URL set, the production tools' funcs are wrapped so calls
# aimed at the DEFAULT endpoint are redirected to a replica instance of the
# same service (same code, same checkpoints, different GPU device — device
# placement does not affect scores per the platform's own measurement
# convention, exp10; the topology is recorded in the run summary). Two
# safeguards: the EGARPS wrapper copies the input PDB into a per-worker
# directory first (EGARPS+ writes its result.txt beside the input, and the
# single-instance serialization that keeps that safe today does not hold
# across instances), and a failed steered call falls back once to the default
# endpoint so replica downtime cannot lose a cell.

def _steer_tool_endpoints() -> dict[str, str]:
    from agent_core import tools as T

    worker_id = os.environ.get("EXP16_WORKER_ID", "0")

    def _wrap(tool, param: str, new_url: str, isolate: bool):
        orig_func = tool.func
        orig_default = tool.args_schema.model_fields[param].default
        isolate_dir = PROJECT_ROOT / "workspace" / f"exp16_egarps_w{worker_id}"

        def wrapper(*a, **kw):
            if kw.get(param, orig_default) != orig_default:
                return orig_func(*a, **kw)
            fallback = dict(kw)
            if isolate and kw.get("filepath"):
                src = Path(kw["filepath"])
                if not src.is_absolute():
                    src = PROJECT_ROOT / src
                if src.exists():
                    isolate_dir.mkdir(parents=True, exist_ok=True)
                    dst = isolate_dir / src.name
                    shutil.copy2(src, dst)
                    kw = dict(kw, filepath=str(dst))
            steered = dict(kw, **{param: new_url})
            try:
                return orig_func(*a, **steered)
            except Exception:
                return orig_func(*a, **fallback)

        tool.func = wrapper

    steering: dict[str, str] = {}
    if os.environ.get("EXP16_EGARPS_URL"):
        _wrap(T.score_rna_protein_complex_with_egarps, "service_url",
              os.environ["EXP16_EGARPS_URL"], isolate=True)
        steering["egarps"] = os.environ["EXP16_EGARPS_URL"]
    if os.environ.get("EXP16_PROTEINX_URL"):
        _wrap(T.predict_rna_protein_complex_with_proteinx, "service_url",
              os.environ["EXP16_PROTEINX_URL"], isolate=False)
        steering["proteinx"] = os.environ["EXP16_PROTEINX_URL"]
    if os.environ.get("EXP16_RHOFOLD_URL"):
        _wrap(T.predict_rna_tertiary_structure_with_rhofold, "service_url",
              os.environ["EXP16_RHOFOLD_URL"], isolate=False)
        steering["rhofold"] = os.environ["EXP16_RHOFOLD_URL"]
    if os.environ.get("EXP16_ODESIGN_URL"):
        _wrap(T.run_odesign_inference, "service_url",
              os.environ["EXP16_ODESIGN_URL"], isolate=False)
        steering["odesign"] = os.environ["EXP16_ODESIGN_URL"]
    return steering


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pilot", action="store_true",
                        help=f"pilot: {PILOT_TARGETS} x seed 0 x 4 arms")
    parser.add_argument("--targets", default=None, help="comma-separated target ids (default: all 20)")
    parser.add_argument("--arms", default=",".join(ARMS))
    parser.add_argument("--seed-sets", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--worker-id", type=int, default=0,
                        help="parallel worker id; >0 writes records_worker<id>.jsonl "
                             "(launch several identical processes — cells are "
                             "distributed by atomic directory claims)")
    parser.add_argument("--timeout-per-cell", type=float, default=7200)
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    records_path = (RESULTS_DIR / ("pilot.jsonl" if args.pilot else "records.jsonl")
                    if args.worker_id == 0
                    else RESULTS_DIR / f"records_worker{args.worker_id}.jsonl")
    summary_path = RESULTS_DIR / ("pilot_summary.json" if args.pilot else "summary.json")

    if args.analyze_only:
        records = load_all_records()
        summary_path.write_text(json.dumps(summarize(records), indent=1, default=str))
        print(json.dumps(json.loads(summary_path.read_text())["analyses"], indent=1)[:2000])
        return 0

    # Activate the audit runtime so every ToolExecutor call lands in the
    # platform audit trail (the exp10 convention).
    from agent_core.calibrated.runtime import runtime_from_env
    runtime_from_env()
    steering = _steer_tool_endpoints()
    if steering:
        print(f"[worker {args.worker_id}] endpoint steering: {steering}", flush=True)

    if args.pilot:
        targets = PILOT_TARGETS
        arms, seed_sets = ARMS, [0]
    else:
        targets = ([t.strip() for t in args.targets.split(",")] if args.targets
                   else sorted(p.stem for p in TARGETS_DIR.glob("*.json")))
        arms = [a.strip() for a in args.arms.split(",")]
        seed_sets = list(range(min(args.seed_sets, len(SEED_SETS))))

    done = load_done() if args.resume else set()
    jobs = []
    for tid in targets:
        tf = TARGETS_DIR / f"{tid}.json"
        if not tf.exists():
            print(f"[skip] {tid}: no target file")
            continue
        meta = json.loads(tf.read_text())
        struct = find_structure(meta["pdb_id"])
        if struct is None:
            print(f"[skip] {tid}: no structure for {meta['pdb_id']}")
            continue
        jobs.append((meta, struct))
    cells = [(meta, struct, arm, si)
             for meta, struct in jobs for arm in arms for si in seed_sets]

    n_ok = n_fail = n_skip = 0
    for i, (meta, struct, arm, si) in enumerate(cells, 1):
        key = (arm, meta["target_id"], si)
        if key in done:
            n_skip += 1
            continue
        if not try_claim(f"{arm}__{meta['target_id']}__{si}", args.worker_id):
            n_skip += 1
            continue
        print(f"[w{args.worker_id} {i}/{len(cells)}] {meta['target_id']} {arm} "
              f"seed_idx={si} seeds={SEED_SETS[si]} ...", flush=True)
        rec = run_cell(arm, meta, struct, si)
        rec["timestamp"] = datetime.now().isoformat(timespec="seconds")
        with records_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        if rec["success"]:
            n_ok += 1
        else:
            n_fail += 1
        trace = rec.get("trace") or {}
        print(f"      -> {'OK' if rec['success'] else 'FAIL'} "
              f"pool={rec.get('pool_size')} primary={rec.get('primary')} "
              f"branch={trace.get('branch')} stop={trace.get('stop')} "
              f"in {rec.get('elapsed_seconds', 0):.0f}s", flush=True)

    records = load_all_records()
    summary = summarize(records)
    summary["run_counts"] = {"ok": n_ok, "fail": n_fail, "skip": n_skip}
    summary_path.write_text(json.dumps(summary, indent=1, default=str))
    print(f"\nDone (worker {args.worker_id}): {n_ok} ok, {n_fail} failed, "
          f"{n_skip} claimed-elsewhere/resumed -> merged {len(records)} records")
    for name, an in summary["analyses"].items():
        print(f"  {name}: delta={an.get('delta')} p={an.get('p_wilcoxon')} "
              f"n={an.get('n_pairs')} gate={'PASS' if an.get('gate_pass') else 'FAIL'}")
    print(f"  self-audit survival: {summary['self_audit']['survival']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
