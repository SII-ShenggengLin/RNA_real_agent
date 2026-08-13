#!/usr/bin/env python3
"""E4 PRE-REGISTRATION (full matrix) — learning curve of memory-augmented campaigns.

Design doc: ``docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md`` §3 E4.
Decision memo: ``experiments/results/HANDOFF_2026-08-04_P2NOGO_E4DECISION.md``.
Pilot verdict (pipeline GO, 12/12): ``experiments/results/e4_pilot_summary.json``.
Amendments from the pilot (2026-08-05, user-approved, HANDOFF §2):
matrix 12 → 120; ``bmc_max_rounds`` default 1 → 2; fresh CaseMemory root
``workspace/e4_full/case_memory``; seed groups {A,B} → {A,B,C}; expected-failure
cells pre-declared (Zika_E_protein, Factor_VIII). Dual-endpoint thresholds
unchanged from the pilot.

Hypothesis
    A campaign agent whose per-campaign knobs are conditioned on a shared,
    sequentially accumulated CaseMemory reaches equivalent design quality with
    fewer candidate evaluations than the identical agent without memory
    (learning curve: design gain vs evaluation budget over campaign index).

Full matrix (pre-registered, do not change without an amendment)
    20 targets (all of
    ``data/benchmarks/RNA-BioBench-FullLength-mRNA/targets/``: A1AT, Albumin,
    Beta_galactosidase, EPO, Factor_VIII, GFP, Growth_hormone, HER2,
    HIV-1_Env_gp120, HPV16_L1, IFN_alpha_2a, IL-2, Influenza_HA_H1N1, Insulin,
    Luciferase, Ovalbumin, RSV_F_protein, SARS-CoV-2_Spike_WT, Transferrin,
    Zika_E_protein)
    × 2 arms (``memory`` / ``nomem``)
    × 3 seed groups (``A`` seed 0, ``B`` seed 1, ``C`` seed 2; each seed
    deterministically permutes the target order via
    ``random.Random(seed).sample``)
    = 120 campaigns. Executor: ``FullLengthMrnaDesignWorkflow`` via the CLI
    subprocess primitive ``run_task_dict`` (Fig 2/Fig 3 drivers).

Arms
    - ``nomem`` = Fig 3 defaults: ``design_tool="all"`` (LinearDesign λ grid
      {0,1,4,10} + RNARL + GEMORNA), ``lambda_value=2.0`` (ignored by the grid
      generator; it is the BMC λ-adjustment starting point, exactly as Fig 3),
      ``utr_mode="all"``, ``bmc_max_rounds=2``, ``bmc_improvement_threshold=0.05``,
      ``reference_point`` omitted (utopian), ``cai_species`` from the target
      JSON. CaseMemory is never touched.
      ``bmc_max_rounds=2`` (2026-08-05 decision): Fig 3 measured
      ``bmc_rounds_executed`` 113+123 times at 0–1 rounds, only 4 times at 2 —
      BMC early-stops, so a higher cap costs ≈0; with default 1, knob 3 of the
      injection mapping is structurally a no-op, while with default 2 the
      typical injection (median rounds ≈ 1) prunes the budget downward — the
      efficiency story's direction.
    - ``memory`` = same defaults, but before each campaign the driver queries
      the seed-group CaseMemory root
      (``workspace/e4_full/case_memory/<group>/``; shared within a seed group,
      accumulated in campaign order, isolated across groups; rebuilt from this
      driver's JSONL on every start so ``--resume`` is idempotent):
      ``similar(task_type="full_length_mrna",
      target_features={"cds_length_nt": ..., "species": ...}, k=3)``.
      Cold start (no similar campaigns) → parameters bitwise identical to
      ``nomem``. Otherwise the pre-registered injection mapping below fires.

Injection mapping (pre-registered; pure function ``_memory_overrides``)
    Archive fields per retrieved campaign (from ``CampaignRecord.outcomes``):
    ``final_lambda`` (float|None), ``bmc_rounds_executed`` (int),
    ``utr_family`` (short|medium|long|None).
    1. λ-grid narrowing: consider retrieved campaigns with a traceable
       ``final_lambda``. If ≥2 such campaigns exist and (max − min) ≤ 6.0,
       set ``design_tool="lineardesign"`` + ``lambda_value`` = median of those
       final λ values. Otherwise keep ``design_tool="all"``.
    2. UTR-mode narrowing: if one ``utr_family`` value is shared by ≥2
       retrieved campaigns AND by ≥2/3 of all retrieved campaigns, set
       ``utr_mode`` to that family. Otherwise keep ``utr_mode="all"``.
    3. ``bmc_max_rounds`` = round(median of retrieved ``bmc_rounds_executed``),
       clamped to [1, 2] (= DEFAULT_BMC_MAX_ROUNDS). With the full-matrix
       default of 2, an executed-rounds median of 1 (Fig 3 measured ≈1) injects
       ``bmc_max_rounds=1`` — a downward budget prune, so the knob fires.
    A knob "fires" iff the injected value differs from the arm default
    (``design_tool!="all"`` or ``utr_mode!="all"`` or ``bmc_max_rounds!=2``).

Campaign archive (memory arm only; successful campaigns only)
    After each successful memory-arm campaign the driver appends a
    ``CampaignRecord`` (schema: ``agent_core/calibrated/models.py``):
    ``target_features={cds_length_nt, species}``,
    ``outcomes={final_lambda, bmc_rounds_executed, best_utr5_preset,
    best_utr3_preset, utr_family, best_cai, best_full_length_mfe,
    best_utr5_mrl, best_asf_distance}``, ``budget={eval_count,
    bmc_max_rounds, elapsed_seconds}``, ``interventions`` = fired knobs.
    - ``final_lambda``: reconstructed from ``_bmc_trace`` by applying each
      round's CDS ``lambda_value`` adjustments cumulatively to the input
      ``lambda_value`` (2.0; heuristic start 2.0 when None), clamped to
      [0, 20]. ``None`` when no round emitted a λ adjustment (the CDS grid was
      never narrowed during the campaign).
    - ``bmc_rounds_executed`` = ``len(_bmc_trace)`` (rounds that produced new
      candidates; early-stop rounds without regeneration leave no trace entry).
    - ``utr_family`` = best candidate's ``utr5_preset`` when
      ``utr5_preset == utr3_preset``, else ``None`` (mixed pair = no family).

Evaluation-count reduction (pre-registered endpoint currency)
    1 eval = 1 full-length candidate evaluation. Every candidate surviving the
    pre-evaluation dedup is evaluated exactly once (initial pool in
    ``generate_candidates``; per-round additions in ``bmc_run_round``), so:
        eval_count = len(all_candidates) in the campaign result JSON.
    Candidate temporal order (for budget matching) is reconstructed by the
    pre-registered surrogate: all candidates WITHOUT
    ``metadata.bmc_regenerated`` (initial pool) in saved order, followed by all
    candidates WITH ``metadata.bmc_regenerated`` (BMC additions) in saved
    order. (The full-length workflow does not tag the round index per
    candidate; intra-group order is the ASF-ranked saved order.)
    Driver cross-check: ``eval_count == candidate_count`` from the results
    JSON and ``eval_count == n_initial + n_regenerated``.
    Analysis double-reduction (pass criterion ③): recomputed independently
    from the persisted session artifact ``workflow_results_*.json``.

Budget-matching truncation (pre-registered)
    Per cell (seed_group × target): let K = min(eval_count_memory,
    eval_count_nomem). Each arm's pool is truncated to the first K candidates
    in the surrogate temporal order; the design-gain endpoint (full matrix) is
    best-of-pool (min ASF distance) over the truncated pool. If either arm is
    missing/failed, or post-truncation counts differ, the cell is marked
    ``invalid`` (valid only when the failure is a pre-declared acceptable
    mode).

Pre-declared acceptable failure modes (anything else fails the run)
    - subprocess timeout (``error == "timeout"``);
    - LinearDesign OOM: CLI failure whose session ``driver.log`` mentions
      out-of-memory / bad_alloc;
    - Expected-failure cells (pre-declared): Zika_E_protein and Factor_VIII —
      their ~7kb+ CDS can SIGKILL LinearDesign with OOM (Fig 2 empty-run
      diagnosis). These cells are invalidated in the analysis and listed in
      the verdict; they are excluded from paired endpoints and budget savings.

Dual endpoints (pre-registered; ANY endpoint passing → GO)
    Efficiency endpoint (passes iff BOTH components hold):
        (a) memory-arm learning-curve slope significantly negative: per seed
            group per arm, numpy univariate regression of truncated
            best-of-pool ASF distance (y) vs cumulative eval_count (x, summed
            over successful campaigns in campaign order); the 3 memory-arm
            slopes tested vs 0 with a one-sample t-test (one-sided less,
            p < 0.05). Paired contrast memory − nomem within each seed group
            is reported descriptively.
        (b) 20-target cumulative budget saving ≥ 25%: 1 − sum(memory
            eval_count) / sum(nomem eval_count) over cells where both arms
            succeeded, ≥ 0.25.
    Design-gain endpoint (passes iff ANY validated metric passes):
        per valid cell, the budget-matched truncated pool's best-of-pool
        candidate (min ASF) is scored on the pre-registered VALIDATED metrics
        (ASF itself and any unprofiled oracle are banned per REDESIGN §3):
        - ``cds_cai`` (higher is better);
        - ``full_length_mfe`` (lower is better);
        - junction mfe/nt = mean of ``junction_5utr_cds_mfe_per_nt`` and
          ``junction_cds_3utr_mfe_per_nt`` (lower is better);
        - ``utr5_predicted_mrl`` (GemORNA; higher is better).
        Per metric: paired Wilcoxon (memory vs nomem,
        ``stats_utils.wilcoxon_paired``) with BH-FDR across the 4 metrics
        (``stats_utils.bh_fdr``) and Cliff's delta (``stats_utils.cliffs_delta``);
        the metric passes iff q < 0.05 AND |delta| ≥ 0.3 in the favourable
        direction (memory better). Endpoint passes iff ≥ 1 metric passes.

Sharding (2026-08-05 decision; per-seed-group memory order semantics cannot be
    split across shards): shard A = seed groups A+B (80 campaigns), shard B =
    seed group C (40 campaigns). The two shards run concurrently (memory
    concurrency ≤ 2), each appending its own JSONL
    (``e4_full_shard_a.jsonl`` / ``e4_full_shard_b.jsonl``); ``--resume`` is
    idempotent per shard (done-key = (seed_group, arm, target_id)).

Analysis notes: a task may appear multiple times in a JSONL after a resumed
    run; the analysis takes the LATEST record per (seed_group, arm, target_id)
    (``experiments/analysis/e4_analysis.py`` ``_latest_per_key``).

Usage (from ``rna_agent_system/``):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py --dry-run
    # shard A (80 campaigns): seed groups A,B
    setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py \
      --targets A1AT,...,Zika_E_protein --seed-groups A,B --timeout 9000 --resume \
      --output experiments/results/e4_full_shard_a.jsonl > experiments/results/e4_full_shard_a.log 2>&1 &
    # shard B (40 campaigns): seed group C
    setsid nohup env PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e4_learning_curve.py \
      --targets A1AT,...,Zika_E_protein --seed-groups C --timeout 9000 --resume \
      --output experiments/results/e4_full_shard_b.jsonl > experiments/results/e4_full_shard_b.log 2>&1 &

Records: ``experiments/results/e4_full_shard_{a,b}.jsonl`` (append; ``--resume``
skips completed (seed_group, arm, target_id) done-keys).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT, run_task_dict  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT))
from agent_core.calibrated.case_memory import CaseMemory  # noqa: E402
from agent_core.calibrated.models import CampaignRecord  # noqa: E402

TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "e4_full_runs.jsonl"
CASE_MEMORY_ROOT = PROJECT_ROOT / "workspace" / "e4_full" / "case_memory"

# Pre-registered full matrix (all 20 benchmark targets at campaign time, see docstring).
# NOTE (2026-08-11): this is E4's historical target list — its concluded results
# reference Zika_E_protein / Factor_VIII cells. The benchmark directory has since
# swapped those two oversized targets for OTC / PDGFB; do not "sync" this list.
FULL_TARGETS = [
    "A1AT", "Albumin", "Beta_galactosidase", "EPO", "Factor_VIII", "GFP",
    "Growth_hormone", "HER2", "HIV-1_Env_gp120", "HPV16_L1", "IFN_alpha_2a",
    "IL-2", "Influenza_HA_H1N1", "Insulin", "Luciferase", "Ovalbumin",
    "RSV_F_protein", "SARS-CoV-2_Spike_WT", "Transferrin", "Zika_E_protein",
]
SEED_GROUPS: dict[str, int] = {"A": 0, "B": 1, "C": 2}
ARMS = ("nomem", "memory")

# Arm defaults (= Fig 3 driver parameters).
DEFAULT_DESIGN_TOOL = "all"
DEFAULT_LAMBDA_VALUE = 2.0  # grid-ignored; BMC λ-adjustment start, as in Fig 3
DEFAULT_UTR_MODE = "all"
DEFAULT_BMC_MAX_ROUNDS = 2  # 2026-08-05 decision (see docstring); clamp upper bound
DEFAULT_BMC_IMPROVEMENT_THRESHOLD = 0.05

# Injection-mapping thresholds (pre-registered).
LAMBDA_SPAN_THRESHOLD = 6.0
LAMBDA_MIN_CAMPAIGNS = 2
UTR_CONSENSUS_MIN_VOTES = 2
UTR_CONSENSUS_MIN_FRACTION = 2.0 / 3.0
SIMILAR_K = 3
TASK_TYPE = "full_length_mrna"


# --------------------------------------------------------------------- seeds


def seed_group_order(seed: int, targets: list[str] | None = None) -> list[str]:
    """Deterministic target order for one seed group."""
    return random.Random(seed).sample(list(targets or FULL_TARGETS),
                                      len(targets or FULL_TARGETS))


def expected_matrix(
    targets: list[str] | None = None, groups: list[str] | None = None
) -> list[dict[str, Any]]:
    """The pre-registered (seed_group, arm, campaign_index, target) cells.

    ``groups`` selects a subset of seed groups (sharding); default = all
    SEED_GROUPS (full matrix: 20 targets × 2 arms × 3 groups = 120 cells).
    """
    groups = groups or list(SEED_GROUPS)
    matrix = []
    for group in groups:
        seed = SEED_GROUPS[group]
        for arm in ARMS:
            for idx, target_id in enumerate(seed_group_order(seed, targets), start=1):
                matrix.append({
                    "seed_group": group,
                    "arm": arm,
                    "campaign_index": idx,
                    "target_id": target_id,
                })
    return matrix


# ------------------------------------------------------- pure reduction fns


def final_lambda_from_trace(
    bmc_trace: list[dict[str, Any]] | None,
    start_lambda: float | None = DEFAULT_LAMBDA_VALUE,
) -> float | None:
    """Reconstruct the final LinearDesign λ from a ``_bmc_trace``.

    Applies each round's CDS ``lambda_value`` adjustments cumulatively
    (heuristic start 2.0 when the input λ is None), clamped to [0, 20].
    Returns ``None`` when no round emitted a λ adjustment.
    """
    lam = start_lambda
    fired = False
    for round_rec in bmc_trace or []:
        cds_fb = (round_rec.get("feedback_dispatched") or {}).get("CDS") or {}
        for adj in cds_fb.get("adjustments") or []:
            if adj.get("param") == "lambda_value":
                base = lam if lam is not None else 2.0
                lam = max(0.0, min(20.0, base + float(adj.get("delta", 0.0))))
                fired = True
    return lam if fired else None


def utr_family(utr5_preset: str | None, utr3_preset: str | None) -> str | None:
    """UTR preset family of a candidate: the preset iff 5' and 3' agree."""
    if utr5_preset and utr5_preset == utr3_preset:
        return utr5_preset
    return None


def is_regenerated(candidate: dict[str, Any]) -> bool:
    return bool((candidate.get("metadata") or {}).get("bmc_regenerated"))


def surrogate_temporal_order(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pre-registered temporal surrogate: initial pool first, BMC additions last.

    Stable within each group (saved = ASF-ranked order).
    """
    initial = [c for c in candidates if not is_regenerated(c)]
    regenerated = [c for c in candidates if is_regenerated(c)]
    return initial + regenerated


def eval_count(candidates: list[dict[str, Any]]) -> int:
    """1 eval = 1 full-length candidate evaluation; dedup happens pre-evaluation."""
    return len(candidates)


def truncate_to_budget(
    candidates: list[dict[str, Any]], budget: int
) -> list[dict[str, Any]]:
    """Keep the first *budget* candidates in surrogate temporal order."""
    return surrogate_temporal_order(candidates)[:budget]


def best_of_pool(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Best (min ASF distance) candidate of a (possibly truncated) pool."""
    best: dict[str, Any] | None = None
    for c in candidates:
        asf = (c.get("scores") or {}).get("asf_distance")
        if asf is None:
            continue
        if best is None or asf < (best.get("scores") or {}).get("asf_distance", float("inf")):
            best = c
    return best


def _memory_overrides(similar_campaigns: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """Pre-registered injection mapping (pure; unit-tested).

    Args:
        similar_campaigns: archive-outcome dicts with keys ``final_lambda``
            (float|None), ``bmc_rounds_executed`` (int|None), ``utr_family``
            (str|None), ordered by retrieval rank.

    Returns:
        (overrides, fired): ``overrides`` holds only the parameters that
        differ from the arm defaults (ready to merge into the task input);
        ``fired`` lists the knob names that changed.
    """
    overrides: dict[str, Any] = {}
    fired: list[str] = []
    if not similar_campaigns:
        return overrides, fired  # cold start → bitwise nomem

    # Rule 1 — λ-grid narrowing.
    lambdas = [
        float(c["final_lambda"]) for c in similar_campaigns
        if c.get("final_lambda") is not None
    ]
    if len(lambdas) >= LAMBDA_MIN_CAMPAIGNS and (max(lambdas) - min(lambdas)) <= LAMBDA_SPAN_THRESHOLD:
        overrides["design_tool"] = "lineardesign"
        overrides["lambda_value"] = float(median(lambdas))
        fired.append("design_tool+lambda_value")

    # Rule 2 — UTR-mode narrowing.
    families = [c.get("utr_family") for c in similar_campaigns if c.get("utr_family")]
    n_retrieved = len(similar_campaigns)
    for fam in ("short", "medium", "long"):
        votes = families.count(fam)
        if votes >= UTR_CONSENSUS_MIN_VOTES and votes / n_retrieved >= UTR_CONSENSUS_MIN_FRACTION:
            overrides["utr_mode"] = fam
            fired.append("utr_mode")
            break

    # Rule 3 — bmc_max_rounds = clamped median of executed rounds.
    rounds = [
        int(c["bmc_rounds_executed"]) for c in similar_campaigns
        if c.get("bmc_rounds_executed") is not None
    ]
    if rounds:
        value = max(1, min(int(round(median(rounds))), DEFAULT_BMC_MAX_ROUNDS))
        if value != DEFAULT_BMC_MAX_ROUNDS:
            overrides["bmc_max_rounds"] = value
            fired.append("bmc_max_rounds")

    return overrides, fired


# ----------------------------------------------------------- archive helpers


def build_base_params(meta: dict[str, Any]) -> dict[str, Any]:
    """Fig 3 default parameters for one target (nomem arm, bitwise)."""
    return {
        "protein_sequence": meta["protein_sequence"].upper(),
        "design_tool": DEFAULT_DESIGN_TOOL,
        "lambda_value": DEFAULT_LAMBDA_VALUE,
        "cai_species": meta.get("species_for_codon_optimization") or "human",
        "utr_mode": DEFAULT_UTR_MODE,
        "bmc_max_rounds": DEFAULT_BMC_MAX_ROUNDS,
        "bmc_improvement_threshold": DEFAULT_BMC_IMPROVEMENT_THRESHOLD,
    }


def target_features(meta: dict[str, Any]) -> dict[str, Any]:
    cds_nt = len(meta["protein_sequence"]) * 3
    return {
        "cds_length_nt": float(cds_nt),
        "species": meta.get("species_for_codon_optimization") or "human",
    }


def junction_mfe_per_nt(candidate: dict[str, Any]) -> float | None:
    """Pre-registered junction mfe/nt = mean of the two junction mfe_per_nt."""
    s = candidate.get("scores") or {}
    vals = [v for v in (s.get("junction_5utr_cds_mfe_per_nt"),
                        s.get("junction_cds_3utr_mfe_per_nt")) if v is not None]
    return sum(vals) / len(vals) if vals else None


def candidate_index(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact per-candidate projection stored in the JSONL record.

    Carries the pre-registered VALIDATED metrics (design-gain endpoint) plus
    the surrogate-order tag: asf_distance (budget matching / efficiency
    curve), cds_cai, full_length_mfe, junction_mfe_per_nt (mean of the two
    junction mfe/nt), utr5_predicted_mrl (GemORNA), bmc_regenerated.
    """
    return [
        {
            "id": c.get("id"),
            "asf_distance": (c.get("scores") or {}).get("asf_distance"),
            "cds_cai": (c.get("scores") or {}).get("cds_cai"),
            "full_length_mfe": (c.get("scores") or {}).get("full_length_mfe"),
            "junction_mfe_per_nt": junction_mfe_per_nt(c),
            "utr5_predicted_mrl": (c.get("scores") or {}).get("utr5_predicted_mrl"),
            "bmc_regenerated": is_regenerated(c),
        }
        for c in candidates
    ]


def extract_campaign_outcome(
    rec: dict[str, Any], start_lambda: float | None = DEFAULT_LAMBDA_VALUE
) -> dict[str, Any]:
    """Extract the archive/outcome fields from a ``run_task_dict`` record.

    ``start_lambda`` is the campaign's actual input λ (``params["lambda_value"]``,
    which the injection mapping may have overridden); ``final_lambda_from_trace``
    must reconstruct from that start, not the arm default (fix 2026-08-05: the
    injected campaigns' recorded final λ overstated the true value by
    ``default − input``).
    """
    candidates = rec.get("candidates") or []
    best = rec.get("best_candidate") or {}
    best_md = best.get("metadata") or {}
    best_scores = best.get("scores") or {}
    ordered = surrogate_temporal_order(candidates)
    return {
        "eval_count": eval_count(candidates),
        "candidate_count": rec.get("candidate_count"),
        "n_initial": sum(1 for c in ordered if not is_regenerated(c)),
        "n_regenerated": sum(1 for c in ordered if is_regenerated(c)),
        "bmc_rounds_executed": rec.get("bmc_rounds") or 0,
        "final_lambda": final_lambda_from_trace(rec.get("bmc_trace"), start_lambda=start_lambda),
        "best_utr5_preset": best_md.get("utr5_preset"),
        "best_utr3_preset": best_md.get("utr3_preset"),
        "utr_family": utr_family(best_md.get("utr5_preset"), best_md.get("utr3_preset")),
        "best_cai": best_scores.get("cds_cai"),
        "best_full_length_mfe": best_scores.get("full_length_mfe"),
        "best_utr5_mrl": best_scores.get("utr5_predicted_mrl"),
        "best_junction_mfe_per_nt": junction_mfe_per_nt(best),
        "best_asf_distance": best_scores.get("asf_distance"),
        "candidate_index": candidate_index(ordered),
    }


def build_case_archive(
    task_id: str,
    meta: dict[str, Any],
    outcome: dict[str, Any],
    fired: list[str],
    params: dict[str, Any],
    elapsed: float | None,
) -> dict[str, Any]:
    """The ``CampaignRecord`` payload appended to the seed-group CaseMemory."""
    return {
        "campaign_id": task_id,
        "task_type": TASK_TYPE,
        "target_family": meta.get("species_for_codon_optimization") or "human",
        "target_features": target_features(meta),
        "profiling_used": [],
        "interventions": list(fired),
        "budget": {
            "eval_count": outcome["eval_count"],
            "bmc_max_rounds": params.get("bmc_max_rounds"),
            "elapsed_seconds": elapsed,
        },
        "outcomes": {
            "final_lambda": outcome["final_lambda"],
            "bmc_rounds_executed": outcome["bmc_rounds_executed"],
            "best_utr5_preset": outcome["best_utr5_preset"],
            "best_utr3_preset": outcome["best_utr3_preset"],
            "utr_family": outcome["utr_family"],
            "best_cai": outcome["best_cai"],
            "best_full_length_mfe": outcome["best_full_length_mfe"],
            "best_utr5_mrl": outcome["best_utr5_mrl"],
            "best_asf_distance": outcome["best_asf_distance"],
        },
        "verdict": "success",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def archive_to_similar_dict(record: CampaignRecord) -> dict[str, Any]:
    """Projection of a ``CampaignRecord`` into ``_memory_overrides`` input."""
    o = record.outcomes or {}
    return {
        "campaign_id": record.campaign_id,
        "final_lambda": o.get("final_lambda"),
        "bmc_rounds_executed": o.get("bmc_rounds_executed"),
        "utr_family": o.get("utr_family"),
    }


# -------------------------------------------------------------- failure mode


def is_acceptable_failure(rec: dict[str, Any]) -> bool:
    """Pre-declared acceptable failure modes: timeout or LinearDesign OOM."""
    if rec.get("success"):
        return False
    if rec.get("error") == "timeout":
        return True
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / str(rec.get("session_id"))
    log_path = session_dir / "driver.log"
    if log_path.is_file():
        try:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-200_000:].lower()
        except OSError:
            return False
        return any(tag in tail for tag in ("out of memory", "bad_alloc", "oom"))
    return False


# ------------------------------------------------------------ done-key logic


def done_key(rec: dict[str, Any]) -> tuple[str, str, str]:
    return (rec["seed_group"], rec["arm"], rec["target_id"])


def load_done_keys(output: Path) -> set[tuple[str, str, str]]:
    done: set[tuple[str, str, str]] = set()
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("success"):
                done.add(done_key(rec))
    return done


def rebuild_case_memory(group: str, done_records: list[dict[str, Any]]) -> CaseMemory:
    """Rebuild the seed-group CaseMemory from driver JSONL archive payloads.

    Deterministic: the campaigns.jsonl is rewritten from completed memory-arm
    records (in campaign order), so a kill between the campaign run and the
    ``add_campaign`` append cannot desynchronise memory from the JSONL.
    """
    memory = CaseMemory(root=CASE_MEMORY_ROOT / group)
    archives = [
        rec["case_archive"]
        for rec in sorted(
            (r for r in done_records
             if r.get("arm") == "memory" and r.get("seed_group") == group
             and r.get("success") and r.get("case_archive")),
            key=lambda r: r.get("campaign_index", 0),
        )
    ]
    memory.root.mkdir(parents=True, exist_ok=True)
    with memory.campaigns_path.open("w", encoding="utf-8") as fh:
        for payload in archives:
            fh.write(json.dumps(payload, ensure_ascii=True, default=str) + "\n")
    return memory


# -------------------------------------------------------------------- driver


def run_campaign(
    cell: dict[str, Any],
    meta: dict[str, Any],
    memory: CaseMemory | None,
    *,
    env: dict[str, str],
    timeout: int,
) -> dict[str, Any]:
    """Run one (seed_group, arm, target) campaign and build the JSONL record."""
    group, arm, idx = cell["seed_group"], cell["arm"], cell["campaign_index"]
    target_id = cell["target_id"]
    task_id = f"e4_{group}_{arm}_c{idx}_{target_id}"

    params = build_base_params(meta)
    overrides: dict[str, Any] = {}
    fired: list[str] = []
    similar_ids: list[str] = []
    if arm == "memory" and memory is not None:
        feats = target_features(meta)
        similar = memory.similar(TASK_TYPE, target_features=feats, k=SIMILAR_K)
        similar_dicts = [archive_to_similar_dict(r) for r in similar]
        similar_ids = [r.campaign_id for r in similar]
        overrides, fired = _memory_overrides(similar_dicts)
        params.update(overrides)

    task = {
        "task_id": task_id,
        "workflow": "full_length_mrna_design",
        "category": "e4_learning_curve_pilot",
        "description": f"E4 pilot {group}/{arm} campaign {idx}: {target_id}",
        "input": params,
        "evaluation_rubric": None,
    }
    rec = run_task_dict(task, timeout=timeout, env=env, session_prefix="e4")

    record: dict[str, Any] = {
        "task_id": task_id,
        "seed_group": group,
        "arm": arm,
        "campaign_index": idx,
        "target_id": target_id,
        "params": params,
        "memory_overrides": {"fired": fired, "values": overrides},
        "similar_campaign_ids": similar_ids,
        "session_id": rec.get("session_id"),
        "success": rec.get("success"),
        "error": rec.get("error"),
        "elapsed_seconds": rec.get("elapsed_seconds"),
        "quality_actions": rec.get("quality_actions"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    if rec.get("success"):
        outcome = extract_campaign_outcome(rec, start_lambda=params.get("lambda_value"))
        record.update({k: v for k, v in outcome.items() if k != "candidate_index"})
        record["candidate_index"] = outcome["candidate_index"]
        # Reduction cross-check (criterion ③ driver leg).
        record["eval_count_consistent"] = (
            outcome["eval_count"] == outcome["candidate_count"]
            and outcome["eval_count"] == outcome["n_initial"] + outcome["n_regenerated"]
        )
        if arm == "memory" and memory is not None:
            archive = build_case_archive(
                task_id, meta, outcome, fired, params, rec.get("elapsed_seconds")
            )
            memory.add_campaign(CampaignRecord.model_validate(archive))
            record["case_archive"] = archive
    else:
        record["acceptable_failure"] = is_acceptable_failure(rec)
    return record


def load_records(output: Path) -> list[dict[str, Any]]:
    if not output.exists():
        return []
    out = []
    for line in output.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="print the campaign parameter matrix and exit")
    parser.add_argument("--targets", default=None,
                        help="comma-separated target ids (default: all 20 pre-registered targets)")
    parser.add_argument("--seed-groups", default=None,
                        help="comma-separated seed groups to run (default: A,B,C; "
                             "shard A uses A,B, shard B uses C)")
    parser.add_argument("--resume", action="store_true",
                        help="skip done-keys with a successful record in the output JSONL")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    targets = args.targets.split(",") if args.targets else FULL_TARGETS
    groups = args.seed_groups.split(",") if args.seed_groups else list(SEED_GROUPS)
    bad_groups = [g for g in groups if g not in SEED_GROUPS]
    if bad_groups:
        parser.error(f"unknown seed group(s): {bad_groups} (known: {list(SEED_GROUPS)})")
    metas = {t: json.loads((TARGETS_DIR / f"{t}.json").read_text()) for t in targets}
    matrix = expected_matrix(targets, groups)

    if args.dry_run:
        print(f"E4 full matrix: {len(matrix)} campaigns "
              f"({len(targets)} targets x {len(ARMS)} arms x {len(groups)} seed groups)")
        for cell in matrix:
            base = build_base_params(metas[cell["target_id"]])
            note = ""
            if cell["arm"] == "memory":
                note = ("cold start -> nomem defaults"
                        if cell["campaign_index"] == 1
                        else "+ memory overrides resolved at runtime from CaseMemory")
            display = {k: v for k, v in base.items() if k != "protein_sequence"}
            print(f"  [{cell['seed_group']}/{cell['arm']:6s}] campaign {cell['campaign_index']} "
                  f"{cell['target_id']:20s} params={json.dumps(display)} {note}")
        print(f"output -> {args.output}")
        print(f"case memory roots -> {CASE_MEMORY_ROOT}/<seed_group>")
        return 0

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    args.output.parent.mkdir(parents=True, exist_ok=True)

    done = load_done_keys(args.output) if args.resume else set()
    prior_records = load_records(args.output) if args.resume else []

    memories: dict[str, CaseMemory] = {}
    for group in groups:
        memories[group] = rebuild_case_memory(group, prior_records)

    n_ok = n_fail = n_skip = 0
    for i, cell in enumerate(matrix, 1):
        key = (cell["seed_group"], cell["arm"], cell["target_id"])
        if key in done:
            n_skip += 1
            print(f"[{i}/{len(matrix)}] skip {key} (done)", flush=True)
            continue
        meta = metas[cell["target_id"]]
        memory = memories[cell["seed_group"]] if cell["arm"] == "memory" else None
        print(f"[{i}/{len(matrix)}] {cell['seed_group']}/{cell['arm']} "
              f"campaign {cell['campaign_index']}: {cell['target_id']} ...", flush=True)
        record = run_campaign(cell, meta, memory, env=env, timeout=args.timeout)
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        if record["success"]:
            n_ok += 1
            print(f"      -> OK in {record.get('elapsed_seconds', 0):.0f}s, "
                  f"evals={record.get('eval_count')}, "
                  f"final_lambda={record.get('final_lambda')}, "
                  f"fired={record['memory_overrides']['fired']}", flush=True)
        else:
            n_fail += 1
            print(f"      -> FAIL({record.get('error')}) "
                  f"acceptable={record.get('acceptable_failure')}", flush=True)

    print(f"\nDone: {n_ok} ok, {n_fail} failed, {n_skip} skipped -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
