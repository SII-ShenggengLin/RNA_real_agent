"""Unit tests for the E4 learning-curve full-matrix driver (fully mocked).

Covers the pre-registered pure functions in
``experiments/run_e4_learning_curve.py``:
- injection mapping ``_memory_overrides`` (cold start / lambda consensus /
  UTR consensus / bmc_max_rounds clamping to [1, 2]),
- the pre-registered full matrix (120 campaigns, 3 seed groups, 20 targets),
- shard selection via ``expected_matrix(groups=...)``,
- ``final_lambda_from_trace`` reconstruction,
- evaluation-count reduction vs manual counts on a synthetic campaign,
- candidate projection with the validated metrics (design-gain endpoint),
- budget-matching truncation equality,
- ``--resume`` done-key logic.

No services, no subprocesses, no LLM calls.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from run_e4_learning_curve import (  # noqa: E402
    DEFAULT_BMC_MAX_ROUNDS,
    FULL_TARGETS,
    SEED_GROUPS,
    TARGETS_DIR,
    _memory_overrides,
    best_of_pool,
    build_case_archive,
    candidate_index,
    done_key,
    eval_count,
    expected_matrix,
    extract_campaign_outcome,
    final_lambda_from_trace,
    junction_mfe_per_nt,
    load_done_keys,
    seed_group_order,
    surrogate_temporal_order,
    truncate_to_budget,
    utr_family,
)


# --------------------------------------------------------------------- helpers


def _cand(cid: str, asf: float, regenerated: bool = False) -> dict:
    metadata = {"utr5_preset": "short", "utr3_preset": "short"}
    if regenerated:
        metadata["bmc_regenerated"] = True
    return {"id": cid, "scores": {"asf_distance": asf}, "metadata": metadata}


def _lambda_trace(rounds: list[list[float]]) -> list[dict]:
    """Fake _bmc_trace: each inner list = CDS lambda deltas of one round."""
    return [
        {
            "round_num": i + 1,
            "feedback_dispatched": {
                "CDS": {"priority": "medium",
                        "adjustments": [{"param": "lambda_value", "delta": d} for d in deltas]}
            },
        }
        for i, deltas in enumerate(rounds)
    ]


def _archive(final_lambda, rounds, family):
    return {"final_lambda": final_lambda,
            "bmc_rounds_executed": rounds,
            "utr_family": family}


# ------------------------------------------------------------------ injection


class TestMemoryOverrides:
    def test_cold_start_returns_bitwise_nomem(self):
        overrides, fired = _memory_overrides([])
        assert overrides == {}
        assert fired == []

    def test_lambda_consensus_narrows_to_lineardesign_median(self):
        similar = [_archive(0.0, 1, None), _archive(6.0, 1, None), _archive(2.0, 1, None)]
        overrides, fired = _memory_overrides(similar)
        assert overrides["design_tool"] == "lineardesign"
        assert overrides["lambda_value"] == 2.0  # median of {0, 2, 6}
        assert "design_tool+lambda_value" in fired

    def test_lambda_span_above_threshold_keeps_grid(self):
        similar = [_archive(0.0, 1, None), _archive(10.0, 1, None), _archive(6.0, 1, None)]
        overrides, fired = _memory_overrides(similar)
        assert "design_tool" not in overrides
        assert "lambda_value" not in overrides

    def test_lambda_span_exactly_at_threshold_fires(self):
        similar = [_archive(0.0, 1, None), _archive(6.0, 1, None)]
        overrides, _ = _memory_overrides(similar)
        assert overrides["design_tool"] == "lineardesign"
        assert overrides["lambda_value"] == 3.0

    def test_lambda_single_traceable_campaign_does_not_fire(self):
        similar = [_archive(0.0, 1, None), _archive(None, 1, None), _archive(None, 0, None)]
        overrides, _ = _memory_overrides(similar)
        assert "design_tool" not in overrides

    def test_utr_consensus_two_of_three_fires(self):
        similar = [_archive(None, 1, "short"), _archive(None, 1, "short"), _archive(None, 1, "long")]
        overrides, fired = _memory_overrides(similar)
        assert overrides["utr_mode"] == "short"
        assert "utr_mode" in fired

    def test_utr_no_consensus_keeps_all(self):
        similar = [_archive(None, 1, "short"), _archive(None, 1, "medium"), _archive(None, 1, "long")]
        overrides, _ = _memory_overrides(similar)
        assert "utr_mode" not in overrides

    def test_utr_mixed_pairs_have_no_family(self):
        similar = [_archive(None, 1, None), _archive(None, 1, None), _archive(None, 1, None)]
        overrides, _ = _memory_overrides(similar)
        assert "utr_mode" not in overrides

    def test_rounds_median_at_default_is_noop(self):
        # Median 2 == DEFAULT_BMC_MAX_ROUNDS (2) -> no override.
        similar = [_archive(None, 2, None), _archive(None, 3, None), _archive(None, 1, None)]
        overrides, fired = _memory_overrides(similar)
        assert "bmc_max_rounds" not in overrides
        assert "bmc_max_rounds" not in fired

    def test_rounds_median_three_clamped_to_default_is_noop(self):
        # Median 3 clamped to [1, 2] -> 2 == default -> no override.
        similar = [_archive(None, 3, None), _archive(None, 3, None), _archive(None, 4, None)]
        overrides, fired = _memory_overrides(similar)
        assert "bmc_max_rounds" not in overrides
        assert "bmc_max_rounds" not in fired

    def test_rounds_median_one_fires_below_default_two(self):
        # Median 1 < default 2 -> downward budget prune fires (efficiency story).
        similar = [_archive(None, 0, None), _archive(None, 0, None), _archive(None, 1, None)]
        overrides, fired = _memory_overrides(similar)
        assert overrides["bmc_max_rounds"] == 1
        assert "bmc_max_rounds" in fired

    def test_rounds_median_one_fires_even_with_two_of_three(self):
        similar = [_archive(None, 1, None), _archive(None, 1, None), _archive(None, 2, None)]
        overrides, fired = _memory_overrides(similar)
        assert overrides["bmc_max_rounds"] == 1
        assert "bmc_max_rounds" in fired

    def test_all_three_knobs_can_fire_together(self):
        similar = [
            _archive(0.0, 1, "medium"),
            _archive(4.0, 1, "medium"),
            _archive(2.0, 1, "long"),
        ]
        overrides, fired = _memory_overrides(similar)
        assert overrides["design_tool"] == "lineardesign"
        assert overrides["lambda_value"] == 2.0
        assert overrides["utr_mode"] == "medium"
        assert overrides["bmc_max_rounds"] == 1  # median 1 < default 2
        assert set(fired) == {"design_tool+lambda_value", "utr_mode", "bmc_max_rounds"}


# ------------------------------------------------------------------ final λ


class TestFinalLambdaFromTrace:
    def test_no_trace_returns_none(self):
        assert final_lambda_from_trace(None) is None
        assert final_lambda_from_trace([]) is None

    def test_no_lambda_adjustment_returns_none(self):
        trace = [{"round_num": 1, "feedback_dispatched": {"CDS": {"adjustments": []}}}]
        assert final_lambda_from_trace(trace) is None

    def test_single_round_cumulative_deltas(self):
        assert final_lambda_from_trace(_lambda_trace([[-2.0, -2.0]]), 2.0) == 0.0

    def test_multi_round_accumulation(self):
        trace = _lambda_trace([[-2.0], [4.0]])
        assert final_lambda_from_trace(trace, 2.0) == 4.0

    def test_clamped_to_zero_and_twenty(self):
        assert final_lambda_from_trace(_lambda_trace([[-50.0]]), 2.0) == 0.0
        assert final_lambda_from_trace(_lambda_trace([[50.0]]), 2.0) == 20.0

    def test_none_start_uses_heuristic_two(self):
        assert final_lambda_from_trace(_lambda_trace([[4.0]]), None) == 6.0


# ------------------------------------------------------------------ utr family


class TestUtrFamily:
    def test_matching_pair(self):
        assert utr_family("short", "short") == "short"

    def test_mixed_pair_has_no_family(self):
        assert utr_family("short", "long") is None
        assert utr_family(None, "short") is None


# ------------------------------------------------------- eval-count reduction


class TestEvalCountReduction:
    """Reduction must match a manual count on a synthetic campaign."""

    def _fake_record(self) -> dict:
        # Manual model: initial pool of 4 + BMC round adding 3 = 7 evals.
        initial = [_cand(f"init_{i}", asf=0.1 * i) for i in range(4)]
        regenerated = [_cand(f"bmc_{i}", asf=0.05 * i, regenerated=True) for i in range(3)]
        # Saved order is ASF-ranked (not temporal) on purpose.
        ranked = sorted(initial + regenerated,
                        key=lambda c: c["scores"]["asf_distance"])
        return {
            "candidate_count": 7,
            "candidates": ranked,
            "bmc_rounds": 1,
            "bmc_trace": _lambda_trace([[-2.0]]),
            "best_candidate": {
                "metadata": {"utr5_preset": "medium", "utr3_preset": "medium"},
                "scores": {"cds_cai": 0.9, "full_length_mfe": -500.0,
                           "utr5_predicted_mrl": 5.5, "asf_distance": 0.0},
            },
        }

    def test_eval_count_equals_manual_count(self):
        outcome = extract_campaign_outcome(self._fake_record())
        assert outcome["eval_count"] == 7  # 4 initial + 3 regenerated
        assert outcome["n_initial"] == 4
        assert outcome["n_regenerated"] == 3
        assert outcome["eval_count"] == outcome["n_initial"] + outcome["n_regenerated"]
        assert outcome["eval_count"] == outcome["candidate_count"]

    def test_surrogate_temporal_order_initial_first(self):
        outcome = extract_campaign_outcome(self._fake_record())
        ordered_ids = [c["id"] for c in outcome["candidate_index"]]
        assert ordered_ids[:4] == [f"init_{i}" for i in range(4)]
        assert all(i.startswith("bmc_") for i in ordered_ids[4:])

    def test_outcome_fields(self):
        outcome = extract_campaign_outcome(self._fake_record())
        assert outcome["bmc_rounds_executed"] == 1
        assert outcome["final_lambda"] == 0.0  # 2.0 - 2.0
        assert outcome["utr_family"] == "medium"
        assert outcome["best_cai"] == 0.9

    def test_candidate_index_carries_validated_metrics(self):
        cands = [
            {"id": "x",
             "scores": {"asf_distance": 0.1, "cds_cai": 0.9, "full_length_mfe": -500.0,
                        "junction_5utr_cds_mfe_per_nt": -0.5,
                        "junction_cds_3utr_mfe_per_nt": -0.3,
                        "utr5_predicted_mrl": 5.5},
             "metadata": {}},
            {"id": "y", "scores": {"asf_distance": 0.2}, "metadata": {}},
        ]
        idx = candidate_index(cands)
        assert idx[0]["cds_cai"] == 0.9
        assert idx[0]["junction_mfe_per_nt"] == -0.4  # mean of the two junctions
        assert idx[0]["utr5_predicted_mrl"] == 5.5
        assert idx[1]["junction_mfe_per_nt"] is None
        assert idx[1]["cds_cai"] is None

    def test_junction_mfe_per_nt_is_mean_of_both_junctions(self):
        assert junction_mfe_per_nt({
            "scores": {"junction_5utr_cds_mfe_per_nt": -0.5,
                       "junction_cds_3utr_mfe_per_nt": -0.3}}) == -0.4
        assert junction_mfe_per_nt({"scores": {}}) is None
        assert junction_mfe_per_nt(
            {"scores": {"junction_5utr_cds_mfe_per_nt": -0.5}}) == -0.5


# ------------------------------------------------------------ truncation


class TestBudgetMatchingTruncation:
    def test_truncation_equalises_arm_counts(self):
        mem_pool = [_cand(f"m{i}", 0.1 * i) for i in range(6)]
        nomem_pool = ([_cand(f"n{i}", 0.1 * i) for i in range(40)]
                      + [_cand(f"nb{i}", 0.2 * i, regenerated=True) for i in range(14)])
        budget = min(eval_count(mem_pool), eval_count(nomem_pool))
        assert budget == 6
        assert len(truncate_to_budget(mem_pool, budget)) == 6
        assert len(truncate_to_budget(nomem_pool, budget)) == 6

    def test_truncation_drops_latest_regenerated_first(self):
        pool = ([_cand(f"i{i}", 0.5 + 0.01 * i) for i in range(3)]
                + [_cand(f"r{i}", 0.01 * i, regenerated=True) for i in range(3)])
        truncated = truncate_to_budget(pool, 4)
        # Surrogate order = initial first; the last regenerated candidate drops.
        assert [c["id"] for c in truncated] == ["i0", "i1", "i2", "r0"]

    def test_best_of_pool_after_truncation(self):
        pool = ([_cand("a", 0.9), _cand("b", 0.8)]
                + [_cand("c", 0.1, regenerated=True)])
        assert best_of_pool(truncate_to_budget(pool, 3))["id"] == "c"
        assert best_of_pool(truncate_to_budget(pool, 2))["id"] == "b"

    def test_empty_pool(self):
        assert truncate_to_budget([], 5) == []
        assert best_of_pool([]) is None


# --------------------------------------------------------------- resume logic


class TestResumeDoneKey:
    def test_done_keys_only_from_successful_records(self, tmp_path):
        output = tmp_path / "runs.jsonl"
        rows = [
            {"seed_group": "A", "arm": "nomem", "target_id": "Insulin", "success": True},
            {"seed_group": "A", "arm": "memory", "target_id": "Insulin", "success": False},
            {"seed_group": "A", "arm": "memory", "target_id": "EPO", "success": True},
        ]
        output.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        done = load_done_keys(output)
        assert done == {("A", "nomem", "Insulin"), ("A", "memory", "EPO")}
        assert ("A", "memory", "Insulin") not in done

    def test_done_key_idempotent_reload(self, tmp_path):
        output = tmp_path / "runs.jsonl"
        row = {"seed_group": "B", "arm": "memory", "target_id": "IL-2", "success": True}
        output.write_text(json.dumps(row) + "\n")
        first = load_done_keys(output)
        # Simulate a rerun that appends the identical completed record again:
        # the done-key set is unchanged and skip logic stays stable.
        with output.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        assert load_done_keys(output) == first == {("B", "memory", "IL-2")}

    def test_corrupt_lines_are_ignored(self, tmp_path):
        output = tmp_path / "runs.jsonl"
        output.write_text(
            '{"seed_group": "A", "arm": "nomem", "target_id": "EPO", "success": true}\n'
            "not-json\n\n"
        )
        assert load_done_keys(output) == {("A", "nomem", "EPO")}

    def test_missing_file_gives_empty_set(self, tmp_path):
        assert load_done_keys(tmp_path / "nope.jsonl") == set()


# -------------------------------------------------------------------- seeds


class TestSeedGroups:
    def test_order_is_deterministic_and_a_permutation(self):
        order_a1 = seed_group_order(0)
        order_a2 = seed_group_order(0)
        assert order_a1 == order_a2
        assert sorted(order_a1) == sorted(FULL_TARGETS)

    def test_distinct_seeds_cover_targets(self):
        for seed in SEED_GROUPS.values():
            assert len(set(seed_group_order(seed))) == len(FULL_TARGETS)

    def test_three_seed_groups(self):
        assert list(SEED_GROUPS) == ["A", "B", "C"]
        assert SEED_GROUPS == {"A": 0, "B": 1, "C": 2}


# ----------------------------------------------------------------- full matrix


class TestFullMatrix:
    def test_full_targets_match_benchmark_dir(self):
        files = sorted(p.stem for p in TARGETS_DIR.glob("*.json"))
        assert sorted(FULL_TARGETS) == files
        assert len(FULL_TARGETS) == 20

    def test_full_matrix_has_120_campaigns(self):
        matrix = expected_matrix()
        assert len(matrix) == 120  # 20 targets x 2 arms x 3 seed groups
        keys = {(c["seed_group"], c["arm"], c["target_id"]) for c in matrix}
        assert len(keys) == 120  # all cells distinct
        for group in SEED_GROUPS:
            assert {c["target_id"] for c in matrix if c["seed_group"] == group} == set(FULL_TARGETS)

    def test_shard_a_seed_groups_ab_has_80_campaigns(self):
        matrix = expected_matrix(groups=["A", "B"])
        assert len(matrix) == 80  # 20 x 2 x 2
        assert {c["seed_group"] for c in matrix} == {"A", "B"}
        for group in ("A", "B"):
            assert len([c for c in matrix if c["seed_group"] == group]) == 40

    def test_shard_b_seed_group_c_has_40_campaigns(self):
        matrix = expected_matrix(groups=["C"])
        assert len(matrix) == 40  # 20 x 2 x 1
        assert {c["seed_group"] for c in matrix} == {"C"}

    def test_campaign_index_is_within_group_order(self):
        matrix = expected_matrix(groups=["C"])
        for group in ("C",):
            idxs = [c["campaign_index"] for c in matrix if c["seed_group"] == group]
            assert idxs == list(range(1, 21)) * 2  # 1..20 per arm, both arms


# ------------------------------------------------------------- case archive


class TestCaseArchive:
    def test_archive_payload_validates_against_campaign_record(self):
        from agent_core.calibrated.models import CampaignRecord

        meta = {"protein_sequence": "MKT", "species_for_codon_optimization": "Homo sapiens"}
        outcome = {
            "eval_count": 7, "candidate_count": 7, "n_initial": 4, "n_regenerated": 3,
            "bmc_rounds_executed": 1, "final_lambda": 0.0,
            "best_utr5_preset": "medium", "best_utr3_preset": "medium",
            "utr_family": "medium", "best_cai": 0.9, "best_full_length_mfe": -500.0,
            "best_utr5_mrl": 5.5, "best_asf_distance": 0.0,
        }
        payload = build_case_archive(
            "e4_A_memory_c1_Insulin", meta, outcome, ["utr_mode"],
            {"bmc_max_rounds": 1}, 123.0,
        )
        rec = CampaignRecord.model_validate(payload)
        assert rec.task_type == "full_length_mrna"
        assert rec.target_features["cds_length_nt"] == 9.0
        assert rec.outcomes["final_lambda"] == 0.0
        assert rec.budget["eval_count"] == 7
