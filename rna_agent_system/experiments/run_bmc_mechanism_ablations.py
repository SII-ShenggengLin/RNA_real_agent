#!/usr/bin/env python3
"""Fig 5 driver: BMC mechanism ablations (panels b-f).

Implements `docs/MANUSCRIPT.md` §7. Panel a reuses Fig 3A / 4A data (analysis
only) and is therefore not part of this driver.

- **Panel b** (Type-II, source-aware vs pool-average feedback):
  10 targets x feedback_mode {source_aware, pool_average} x 3 seed sets = 60
  `rna_aptamer_design` runs. The mode is injected into the CLI subprocess via
  the ``APTAMER_FEEDBACK_MODE`` env var (see
  `agent_core/workflows/coordinator.py`; `pool_average` makes
  `AptamerCoordinator.broadcast_feedback` derive adjustments from candidate-pool
  mean metrics instead of worst-violation source metrics).
- **Panel c** (Type-II, reference-point vs fixed-threshold diagnosis):
  same 10 targets x 2 arms x 3 seed sets = 60 runs. Arm 1 utopian
  (`reference_point` omitted); arm 2 one fixed `reference_point`
  (egarps=0.5, rhofold=0.7, iptm=0.6) mimicking hard thresholds. No code
  change required; `reference_point` is a plain dict in the params JSON
  (same format as pa_benchmarks 009/020).
- **Panel d** (Type-I, bounded adjustment drift demonstration):
  3 small targets (Insulin, Growth_hormone, EPO) x bmc_max_rounds=1 x 3 reps
  = 9 `full_length_mrna_design` runs with an extreme start `lambda_value=18`.
  The lambda trajectory is reconstructed from the `_bmc_trace` (see
  `_reconstruct_lambda_trajectory`; the trace records the coordinator's
  `ParamAdjustment`s, not the applied lambda value, so deltas are replayed
  through the same [0, 20] clamp used by
  `FullLengthMrnaDesignWorkflow._adjust_input_from_feedback`).
- **Panel e** (negative results, BMC ~= Serial expected):
  - e_type1: Insulin / Growth_hormone / EPO with `utr_mode="short"` x
    rounds {0, 1} x 3 reps = 18 runs.
  - e_type2: aptamer targets with explicit `known_hotspot_residues` in their
    target JSON, run with that explicit `hotspot_residues` string x
    rounds {0, 1} x 3 seed sets. NOTE: MANUSCRIPT §7 panel e expects ~5 such
    targets, but only **2** target JSONs actually carry
    `known_hotspot_residues` (Thrombin 1HAO chain H, SARS-CoV-2_Nucleocapsid
    6M3M chain A; verified 2026-07-20), so e_type2 is 2 x 2 x 3 = 12 runs.
- **Panel f** (evaluator-only partial rerun savings): `partial_rerun()` IS
  implemented (`BaseDomainWorkflow.partial_rerun`, `agent_core/workflows/base.py`;
  both BMC workflows inherit it). Because timing it requires real (GPU-heavy)
  workflow runs, this panel never runs as part of the batch: select
  `--panel f` and the driver prints instructions; only `--panel f --do-it`
  actually executes the timing via the Python API (no CLI).

Target set for panels b/c: the first 10 of the 20 Fig-4 targets in the sorted
order used by `experiments/run_bmc_type2_ablation.py`
(`sorted(targets/*.json)`); all 10 verified to have structure files under
`structures/`. Hard-coded below so the subset is stable even if the benchmark
directory changes.

Output: JSONL appended incrementally (default
`experiments/results/fig5_ablations.jsonl`), one record per run with
`task_id / panel / condition / target_id / params / session_id / success /
error / elapsed_seconds` plus panel-specific extractions (`best`,
`pool_objectives`, `bmc_trace`, `lambda_trajectory`, ...). A failed run is
recorded with `success=false` and never aborts the batch. `--resume` skips
task_ids that already have a successful record.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_mechanism_ablations.py \
        [--panel b,c,d,e,f] [--resume] [--dry-run] [--timeout SEC] [--limit N]

    # Panel f (manual, machine idle):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_mechanism_ablations.py \
        --panel f --do-it [--f-reps 10]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT, run_task_dict  # noqa: E402

APTAMER_TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "targets"
APTAMER_STRUCT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
MRNA_TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig5_ablations.jsonl"

SEED_SETS = [[42, 123], [7, 99], [2024, 31415]]
OBJECTIVE_KEYS = ["egarps_component", "rhofold_component", "iptm_component"]

# Panels b/c: first 10 Fig-4 targets (sorted order of run_bmc_type2_ablation.py),
# all with verified structure files (3v03, 1ca2, 2cga, 3cna, 1hrc, 1fha, 1gfl,
# 6lyz, 1anf, 1mbo).
PANEL_BC_TARGETS = [
    "BSA",
    "Carbonic_anhydrase_II",
    "Chymotrypsinogen",
    "Concanavalin_A",
    "Cytochrome_c",
    "Ferritin",
    "GFP",
    "Lysozyme",
    "MBP",
    "Myoglobin",
]

# Panels d/e_type1: the three small therapeutic proteins of MANUSCRIPT §7.
PANEL_D_E1_TARGETS = ["Insulin", "Growth_hormone", "EPO"]

# NOTE (2026-07-28, do not revert): Ferritin (1FHA) is a confirmed ODesign
# target-side boundary — Fig 4 Type-II failed all 12 matrix cells + 3 retries
# with `no_sequences_extracted_from_odesign_output` (RESUME_CHECKPOINT §4),
# and the first fig5 pass failed all six fig5b_Ferritin_* cells identically
# (`cli_failure` records in fig5_ablations.jsonl). Candidate generation dies
# before feedback mode (panel b) or reference point (panel c) can matter, so
# every Ferritin job in panels b/c fails deterministically. Skip them here
# and report the cells as boundary cases in the analysis instead of burning
# GPU hours on retries.
FERRITIN_BOUNDARY_PANELS = frozenset({"b", "c"})

# NOTE (2026-07-30, do not revert): panel e_type2 on SARS-CoV-2_Nucleocapsid
# (6M3M) is also a deterministic boundary — all 6 cells (r0/r1 x s0/s1/s2)
# failed with `no_sequences_extracted_from_odesign_output` while all 6
# Thrombin cells succeeded and Fig-4 Nucleocapsid runs (no explicit hotspot)
# were fine. The e2 jobs pass `hotspot_residues="A/44,A/45,A/46,A/47,A/48"`,
# which fig4kav's hotspot_recovery record shows are all missing from the
# 6M3M chain-A structure (`known_missing_in_structure=[A/44..A/48]`) — an
# out-of-range explicit binding site leaves ODesign no valid target region.
# Report as a boundary case; do not retry.
NUCLEOCAPSID_E2_BOUNDARY = frozenset({"e_type2"})

# Panel c arm 2: one fixed reference point for all targets (hard-threshold mimic).
FIXED_REFERENCE_POINT = {
    "egarps_component": 0.5,
    "rhofold_component": 0.7,
    "iptm_component": 0.6,
}

# Panel f: small protein for the partial-vs-full timing (manual --do-it only).
PANEL_F_TARGET = "Insulin"

# Same best-candidate score keys as experiments/run_bmc_type1_ablation.py.
TYPE1_BEST_SCORE_KEYS = [
    "asf_distance", "cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score",
    "junction_5utr_cds_score", "junction_cds_3utr_score",
    "cds_cai", "cds_mfe", "full_length_mfe", "full_mfe_per_nt",
    "utr5_predicted_mrl", "utr3_predicted_stability",
    "junction_5utr_cds_mfe", "junction_5utr_cds_mfe_per_nt",
    "junction_cds_3utr_mfe", "junction_cds_3utr_mfe_per_nt",
    "junction_5utr_cds_gc_diff", "junction_cds_3utr_gc_diff",
    "junction_5utr_cds_aug_buried", "junction_5utr_cds_kozak_buried",
]

PANEL_F_MANUAL_MESSAGE = """\
[panel f] Evaluator-only partial-rerun timing performs REAL workflow runs
(GPU-heavy microservices) through the Python API. It is intentionally not part
of the batch. When the machine is idle, run manually:
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_mechanism_ablations.py --panel f --do-it
(use --f-reps 10 for the MANUSCRIPT §7 panel-f budget of 10 targeted retries)
Skipping panel f."""


# ─────────────────────────────────────────────────────────────────────────────
# Target metadata helpers
# ─────────────────────────────────────────────────────────────────────────────


def find_structure(pdb_id: str) -> Path | None:
    """Locate the target's structure file (case-tolerant) under structures/."""
    for cand in APTAMER_STRUCT_DIR.glob(f"{pdb_id.lower()}*.pdb"):
        return cand
    for cand in APTAMER_STRUCT_DIR.glob(f"{pdb_id.upper()}*.pdb"):
        return cand
    for cand in APTAMER_STRUCT_DIR.glob(f"*{pdb_id.lower()}*"):
        return cand
    return None


def load_aptamer_meta(target_id: str) -> dict[str, Any]:
    return json.loads((APTAMER_TARGETS_DIR / f"{target_id}.json").read_text())


def load_mrna_meta(target_id: str) -> dict[str, Any]:
    return json.loads((MRNA_TARGETS_DIR / f"{target_id}.json").read_text())


def hotspot_target_ids() -> list[str]:
    """Aptamer targets whose JSON carries an explicit known_hotspot_residues."""
    out = []
    for p in sorted(APTAMER_TARGETS_DIR.glob("*.json")):
        meta = json.loads(p.read_text())
        if meta.get("known_hotspot_residues"):
            out.append(meta["target_id"])
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Job construction
# ─────────────────────────────────────────────────────────────────────────────


def _aptamer_params(meta: dict[str, Any], seeds: list[int], rounds: int) -> dict[str, Any]:
    struct = find_structure(meta["pdb_id"])
    if struct is None:
        raise FileNotFoundError(f"no structure for {meta['pdb_id']}")
    return {
        "protein_structure_path": str(struct.relative_to(PROJECT_ROOT)),
        "chain_id": meta.get("pdb_chain") or "A",
        "aptamer_length": 30,
        "n_odesign_samples": 8,
        "odesign_seeds": seeds,
        "bmc_max_rounds": rounds,
        "bmc_improvement_threshold": 0.05,
    }


def build_jobs(panels: list[str]) -> list[dict[str, Any]]:
    """Build the full job list for the requested panels (f excluded)."""
    jobs: list[dict[str, Any]] = []

    # ── Panel b: feedback mode ablation (Type-II) ───────────────────────────
    if "b" in panels:
        for target_id in PANEL_BC_TARGETS:
            meta = load_aptamer_meta(target_id)
            for mode in ("source_aware", "pool_average"):
                for si, seeds in enumerate(SEED_SETS):
                    params = _aptamer_params(meta, seeds, rounds=1)
                    jobs.append({
                        "task_id": f"fig5b_{target_id}_{mode}_s{si}",
                        "panel": "b",
                        "condition": mode,
                        "target_id": target_id,
                        "seed_idx": si,
                        "seeds": seeds,
                        "workflow": "rna_aptamer_design",
                        "params": params,
                        "env_overrides": {"APTAMER_FEEDBACK_MODE": mode},
                        "description": f"fig5b {target_id} feedback_mode={mode} seed_set={si}",
                    })

    # ── Panel c: reference-point vs fixed-threshold (Type-II) ───────────────
    if "c" in panels:
        for target_id in PANEL_BC_TARGETS:
            meta = load_aptamer_meta(target_id)
            for arm in ("utopian", "fixed_reference"):
                for si, seeds in enumerate(SEED_SETS):
                    params = _aptamer_params(meta, seeds, rounds=1)
                    if arm == "fixed_reference":
                        params["reference_point"] = dict(FIXED_REFERENCE_POINT)
                    jobs.append({
                        "task_id": f"fig5c_{target_id}_{arm}_s{si}",
                        "panel": "c",
                        "condition": arm,
                        "target_id": target_id,
                        "seed_idx": si,
                        "seeds": seeds,
                        "workflow": "rna_aptamer_design",
                        "params": params,
                        # Pin the default feedback mode so a stray
                        # APTAMER_FEEDBACK_MODE in the caller's shell cannot
                        # leak into panel-c runs (panel b sets it explicitly).
                        "env_overrides": {"APTAMER_FEEDBACK_MODE": "source_aware"},
                        "description": f"fig5c {target_id} arm={arm} seed_set={si}",
                    })

    # ── Panel d: bounded-adjustment drift demonstration (Type-I) ────────────
    if "d" in panels:
        for target_id in PANEL_D_E1_TARGETS:
            meta = load_mrna_meta(target_id)
            for rep in range(3):
                params = {
                    "protein_sequence": meta["protein_sequence"].upper(),
                    "design_tool": "all",
                    "lambda_value": 18.0,  # extreme start (drift demonstration)
                    "cai_species": meta.get("species_for_codon_optimization") or "human",
                    "utr_mode": "all",
                    "bmc_max_rounds": 1,
                    "bmc_improvement_threshold": 0.05,
                }
                jobs.append({
                    "task_id": f"fig5d_{target_id}_r{rep}",
                    "panel": "d",
                    "condition": "drift_lambda18_bmc1",
                    "target_id": target_id,
                    "rep": rep,
                    "workflow": "full_length_mrna_design",
                    "params": params,
                    "env_overrides": {},
                    "description": f"fig5d {target_id} lambda=18 bmc1 rep{rep}",
                })

    # ── Panel e Type-I: small proteins with short UTRs (negative result) ────
    if "e" in panels or "e_type1" in panels:
        for target_id in PANEL_D_E1_TARGETS:
            meta = load_mrna_meta(target_id)
            for rounds in (0, 1):
                for rep in range(3):
                    params = {
                        "protein_sequence": meta["protein_sequence"].upper(),
                        "design_tool": "all",
                        "lambda_value": 2.0,
                        "cai_species": meta.get("species_for_codon_optimization") or "human",
                        "utr_mode": "short",
                        "bmc_max_rounds": rounds,
                        "bmc_improvement_threshold": 0.05,
                    }
                    jobs.append({
                        "task_id": f"fig5e1_{target_id}_r{rounds}_rep{rep}",
                        "panel": "e_type1",
                        "condition": "serial" if rounds == 0 else "bmc1",
                        "target_id": target_id,
                        "rep": rep,
                        "workflow": "full_length_mrna_design",
                        "params": params,
                        "env_overrides": {},
                        "description": f"fig5e_type1 {target_id} utr=short rounds={rounds} rep{rep}",
                    })

    # ── Panel e Type-II: explicit known hotspots (negative result) ──────────
    if "e" in panels or "e_type2" in panels:
        for target_id in hotspot_target_ids():
            meta = load_aptamer_meta(target_id)
            for rounds in (0, 1):
                for si, seeds in enumerate(SEED_SETS):
                    params = _aptamer_params(meta, seeds, rounds)
                    # known_hotspot_residues is already in the workflow's
                    # "A/18,A/90" string format (verified in target JSONs).
                    params["hotspot_residues"] = meta["known_hotspot_residues"]
                    jobs.append({
                        "task_id": f"fig5e2_{target_id}_r{rounds}_s{si}",
                        "panel": "e_type2",
                        "condition": "serial" if rounds == 0 else "bmc1",
                        "target_id": target_id,
                        "seed_idx": si,
                        "seeds": seeds,
                        "workflow": "rna_aptamer_design",
                        "params": params,
                        "env_overrides": {"APTAMER_FEEDBACK_MODE": "source_aware"},
                        "description": f"fig5e_type2 {target_id} explicit_hotspot rounds={rounds} seed_set={si}",
                    })

    # Ferritin panels-b/c jobs are skipped as a confirmed boundary (see NOTE
    # near FERRITIN_BOUNDARY_PANELS); their fig5b failure records from the
    # first pass already document the boundary in fig5_ablations.jsonl.
    # Nucleocapsid e_type2 jobs are likewise skipped (NUCLEOCAPSID_E2_BOUNDARY).
    return [
        j for j in jobs
        if not (j["target_id"] == "Ferritin" and j["panel"] in FERRITIN_BOUNDARY_PANELS)
        and not (j["target_id"] == "SARS-CoV-2_Nucleocapsid" and j["panel"] in NUCLEOCAPSID_E2_BOUNDARY)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Record extraction
# ─────────────────────────────────────────────────────────────────────────────


def _reconstruct_lambda_trajectory(
    initial_lambda: float | None,
    bmc_trace: list[dict[str, Any]] | None,
) -> list[float | None]:
    """Replay CDS lambda_value adjustments through the [0, 20] clamp.

    `_bmc_trace` records the coordinator's `ParamAdjustment`s (per round,
    `feedback_dispatched.CDS.adjustments`) but not the lambda value actually
    applied to the regenerated input; the trajectory is therefore reconstructed
    by replaying the deltas through the same clamp used by
    `FullLengthMrnaDesignWorkflow._adjust_input_from_feedback`
    (agent_core/workflows/full_length_mrna_design.py). Entry i is the lambda
    used for round i's regeneration; entry 0 is the extreme start.
    """
    trajectory: list[float | None] = [initial_lambda]
    lam = initial_lambda
    for rnd in bmc_trace or []:
        cds_fb = (rnd.get("feedback_dispatched") or {}).get("CDS") or {}
        for adj in cds_fb.get("adjustments") or []:
            if adj.get("param") == "lambda_value":
                base = lam if lam is not None else 2.0
                lam = max(0.0, min(20.0, base + float(adj.get("delta", 0.0))))
        trajectory.append(lam)
    return trajectory


def build_output_record(job: dict[str, Any], rec: dict[str, Any]) -> dict[str, Any]:
    """Assemble the JSONL record for one finished run."""
    out: dict[str, Any] = {
        "task_id": job["task_id"],
        "panel": job["panel"],
        "condition": job["condition"],
        "target_id": job["target_id"],
        "session_id": rec.get("session_id"),
        "success": rec["success"],
        "error": rec.get("error"),
        "elapsed_seconds": rec.get("elapsed_seconds"),
        "params": job["params"],
        "candidate_count": rec.get("candidate_count"),
        "pareto_frontier_size": rec.get("pareto_frontier_size"),
        "bmc_rounds_executed": rec.get("bmc_rounds"),
        "bmc_trace": rec.get("bmc_trace"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    if "seed_idx" in job:
        out["seed_idx"] = job["seed_idx"]
        out["seeds"] = job["seeds"]
    if "rep" in job:
        out["rep"] = job["rep"]

    best_scores = ((rec.get("best_candidate") or {}).get("scores")) or {}
    if job["workflow"] == "rna_aptamer_design":
        out["best"] = {k: best_scores.get(k) for k in OBJECTIVE_KEYS + ["asf_distance"]}
        out["pool_objectives"] = [
            {k: (c.get("scores") or {}).get(k) for k in OBJECTIVE_KEYS}
            for c in (rec.get("candidates") or [])
        ]
    else:
        out["best"] = {k: best_scores.get(k) for k in TYPE1_BEST_SCORE_KEYS}
        if job["panel"] == "d":
            out["lambda_trajectory"] = _reconstruct_lambda_trajectory(
                job["params"].get("lambda_value"), rec.get("bmc_trace")
            )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Panel f (manual --do-it only)
# ─────────────────────────────────────────────────────────────────────────────


def run_panel_f(args: argparse.Namespace, done: set[str]) -> int:
    """Time partial_rerun() vs full run() for the same evaluation-side change.

    Uses the real Python API (no CLI subprocess): one Serial full run produces
    the candidate pool; the evaluation-side parameter change (adding a
    `reference_point`, which does not affect generation) is then applied via
    `partial_rerun()` (evaluate -> score -> rank on the existing candidates)
    and via a second full `run()` (regenerate + evaluate). The saving is the
    avoided candidate-generation time. Requires GPU microservices; run only
    when the machine is idle.
    """
    if not args.do_it:
        print(PANEL_F_MANUAL_MESSAGE)
        return 0

    # Lazy imports so --help/--dry-run work without agent_core on PYTHONPATH.
    from agent_core.capabilities.base import build_default_capability_registry
    from agent_core.tool_executor import ToolExecutor
    from agent_core.tool_registry import build_default_tool_registry
    from agent_core.workflows.full_length_mrna_design import (
        FullLengthMrnaDesignInput,
        FullLengthMrnaDesignWorkflow,
    )

    meta = load_mrna_meta(PANEL_F_TARGET)
    base_params: dict[str, Any] = {
        "protein_sequence": meta["protein_sequence"].upper(),
        "design_tool": "all",
        "lambda_value": 2.0,
        "cai_species": meta.get("species_for_codon_optimization") or "human",
        "utr_mode": "all",
        "bmc_max_rounds": 0,  # Serial: the timing isolates generate vs evaluate
        "bmc_improvement_threshold": 0.05,
    }
    # Evaluation-side change only: a reference point does not alter candidate
    # generation, so partial_rerun reuses the pool legitimately.
    changed_params = dict(base_params)
    changed_params["reference_point"] = {
        "utr5_mrl": 6.0,
        "utr3_stability": 0.8,
        "full_mfe_score": 40.0,
    }

    executor = ToolExecutor(build_default_tool_registry(include_demo=False))
    registry = build_default_capability_registry(executor)
    wf = FullLengthMrnaDesignWorkflow(registry)
    wf.auto_start_services = True

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_ok = n_fail = 0
    for rep in range(args.f_reps):
        task_id = f"fig5f_{PANEL_F_TARGET}_rep{rep}"
        if task_id in done:
            print(f"[panel f] {task_id}: resumed-skip", flush=True)
            continue
        print(f"[panel f] {task_id}: full run #1 ...", flush=True)
        record: dict[str, Any] = {
            "task_id": task_id,
            "panel": "f",
            "condition": "partial_rerun_vs_full",
            "target_id": PANEL_F_TARGET,
            "rep": rep,
            "session_id": None,  # in-process Python API: no CLI session
            "params": {"initial": base_params, "changed": changed_params},
            "success": False,
            "error": None,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            t0 = time.monotonic()
            result1 = wf.run(FullLengthMrnaDesignInput(**base_params))
            t_full1 = time.monotonic() - t0
            if not result1.success or not result1.all_candidates:
                raise RuntimeError(f"initial run failed: {result1.errors}")

            t0 = time.monotonic()
            partial = wf.partial_rerun(
                FullLengthMrnaDesignInput(**changed_params),
                list(result1.all_candidates),
            )
            t_partial = time.monotonic() - t0

            t0 = time.monotonic()
            result2 = wf.run(FullLengthMrnaDesignInput(**changed_params))
            t_full2 = time.monotonic() - t0

            record.update({
                "success": bool(partial is not None and result2.success),
                "error": None if (partial is not None and result2.success) else "partial_or_full_run_failed",
                "full_run_initial_seconds": round(t_full1, 2),
                "partial_rerun_seconds": round(t_partial, 2),
                "full_run_changed_seconds": round(t_full2, 2),
                "saved_seconds": round(t_full2 - t_partial, 2),
                "saved_fraction_of_full_run": round(
                    (t_full2 - t_partial) / t_full2, 4
                ) if t_full2 > 0 else None,
                "elapsed_seconds": round(t_full1 + t_partial + t_full2, 2),
                "candidate_count": len(result1.all_candidates),
            })
        except Exception as exc:  # batch must not abort on a single failure
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["elapsed_seconds"] = None
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        n_ok += int(record["success"])
        n_fail += int(not record["success"])
        print(f"      -> {'OK' if record['success'] else 'FAIL(' + str(record['error']) + ')'}",
              flush=True)

    print(f"\nPanel f done: {n_ok} ok, {n_fail} failed -> {args.output}")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Main batch loop
# ─────────────────────────────────────────────────────────────────────────────


def load_done_task_ids(output: Path) -> set[str]:
    done: set[str] = set()
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("success"):
                done.add(r["task_id"])
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--panel", default="b,c,d,e,f",
                        help="comma-separated subset of {b,c,d,e,f}; 'e' covers both "
                             "e_type1 and e_type2 (default: all)")
    parser.add_argument("--resume", action="store_true", help="skip task_ids with a successful record")
    parser.add_argument("--dry-run", action="store_true", help="list the jobs that would run, then exit")
    parser.add_argument("--timeout", type=int, default=3600,
                        help="per-run subprocess timeout in seconds (default 3600; use 5400 for slow GPU runs)")
    parser.add_argument("--limit", type=int, default=None, help="max number of jobs (after filtering)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--do-it", action="store_true",
                        help="panel f only: actually perform the real partial-vs-full timing runs")
    parser.add_argument("--f-reps", type=int, default=3,
                        help="panel f repetitions (default 3; MANUSCRIPT budget is 10)")
    args = parser.parse_args()

    panels = [p.strip() for p in args.panel.split(",") if p.strip()]
    valid = {"b", "c", "d", "e", "e_type1", "e_type2", "f"}
    unknown = [p for p in panels if p not in valid]
    if unknown:
        parser.error(f"unknown panel(s): {unknown}; valid: {sorted(valid)}")

    done = load_done_task_ids(args.output) if args.resume else set()

    jobs = build_jobs([p for p in panels if p != "f"])
    if args.resume:
        jobs = [j for j in jobs if j["task_id"] not in done]
    if args.limit:
        jobs = jobs[: args.limit]

    if args.dry_run:
        for j in jobs:
            env_note = " ".join(f"{k}={v}" for k, v in j["env_overrides"].items())
            print(f"{j['task_id']}\t{j['panel']}\t{j['condition']}\t{j['workflow']}"
                  f"{chr(9)}{env_note or '-'}")
        print(f"# {len(jobs)} jobs"
              + ("; panel f: manual --do-it only" if "f" in panels else ""))
        return 0

    base_env = os.environ.copy()
    base_env["PYTHONPATH"] = f"{PROJECT_ROOT}:{base_env.get('PYTHONPATH', '')}"
    args.output.parent.mkdir(parents=True, exist_ok=True)

    n_ok = n_fail = 0
    total = len(jobs)
    for i, job in enumerate(jobs, 1):
        env = base_env.copy()
        env.update(job["env_overrides"])
        task = {
            "task_id": job["task_id"],
            "workflow": job["workflow"],
            "category": f"fig5_{job['panel']}",
            "description": job["description"],
            "input": job["params"],
            "evaluation_rubric": None,
        }
        print(f"[{i}/{total}] {job['description']} ...", flush=True)
        rec = run_task_dict(task, timeout=args.timeout, env=env, session_prefix="fig5")
        out = build_output_record(job, rec)
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
        n_ok += int(rec["success"])
        n_fail += int(not rec["success"])
        print(f"      -> {'OK' if rec['success'] else 'FAIL(' + str(rec.get('error')) + ')'} "
              f"in {rec.get('elapsed_seconds', 0):.0f}s", flush=True)

    print(f"\nBatch done: {n_ok} ok, {n_fail} failed, {total} jobs -> {args.output}")

    if "f" in panels:
        run_panel_f(args, done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
