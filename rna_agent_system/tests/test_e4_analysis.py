"""Unit tests for the E4 full-matrix dual-endpoint analysis (fully mocked).

Covers ``experiments/analysis/e4_analysis.py``:
- per-group-per-arm learning-curve regression slopes (numpy univariate),
- cumulative budget saving over paired cells,
- efficiency endpoint (slope significant negative AND saving >= 25%),
- design-gain endpoint (paired Wilcoxon + BH-FDR + Cliff's delta on the
  pre-registered VALIDATED metrics, favourable direction).

No services, no subprocesses, no LLM calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from analysis.e4_analysis import (  # noqa: E402
    VALIDATED_METRICS,
    _budget_savings,
    _cell_verdict,
    _slopes_by_group_arm,
    regression_slope_endpoint,
    wilcoxon_quality_endpoint,
)
from run_e4_learning_curve import ARMS, SEED_GROUPS  # noqa: E402


# --------------------------------------------------------------------- helpers


def _cand(cid: str, asf: float, cai: float | None = None, mfe: float | None = None,
          jmfe: float | None = None, mrl: float | None = None,
          regenerated: bool = False) -> dict:
    scores = {"asf_distance": asf}
    if cai is not None:
        scores["cds_cai"] = cai
    if mfe is not None:
        scores["full_length_mfe"] = mfe
    if jmfe is not None:
        scores["junction_mfe_per_nt"] = jmfe
    if mrl is not None:
        scores["utr5_predicted_mrl"] = mrl
    metadata = {"bmc_regenerated": regenerated}
    return {"id": cid, "scores": scores, "metadata": metadata}


def _make_cell(group: str, target: str, idx: int, *,
               mem_evals: int, nomem_evals: int,
               mem_asf: float, nomem_asf: float,
               mem_cai: float | None, nomem_cai: float | None,
               mem_mrl: float | None, nomem_mrl: float | None) -> dict:
    """A valid cell with candidate projections for both arms."""
    pool_mem = [_cand("m0", mem_asf, cai=mem_cai, mrl=mem_mrl)]
    pool_nom = [_cand("n0", nomem_asf, cai=nomem_cai, mrl=nomem_mrl)]
    rec_mem = {"success": True, "eval_count": mem_evals,
               "candidate_index": [{"id": c["id"],
                                    "asf_distance": c["scores"]["asf_distance"],
                                    "cds_cai": c["scores"].get("cds_cai"),
                                    "full_length_mfe": c["scores"].get("full_length_mfe"),
                                    "junction_mfe_per_nt": c["scores"].get("junction_mfe_per_nt"),
                                    "utr5_predicted_mrl": c["scores"].get("utr5_predicted_mrl"),
                                    "bmc_regenerated": False} for c in pool_mem]}
    rec_nom = {"success": True, "eval_count": nomem_evals,
               "candidate_index": [{"id": c["id"],
                                    "asf_distance": c["scores"]["asf_distance"],
                                    "cds_cai": c["scores"].get("cds_cai"),
                                    "full_length_mfe": c["scores"].get("full_length_mfe"),
                                    "junction_mfe_per_nt": c["scores"].get("junction_mfe_per_nt"),
                                    "utr5_predicted_mrl": c["scores"].get("utr5_predicted_mrl"),
                                    "bmc_regenerated": False} for c in pool_nom]}
    return _cell_verdict(group, target, idx, rec_mem, rec_nom)


def _slope_cells() -> list[dict]:
    """3 groups x 20 campaigns: memory saves budget (21 vs 30 evals -> ~30%)
    and improves ASF per cumulative eval; nomem is near-flat. Built for
    regression-slope tests."""
    cells = []
    for group in SEED_GROUPS:
        for ci in range(1, 21):
            mem_asf = 0.9 - 0.02 * ci  # quality improves with campaign index
            nomem_asf = 0.9 - 0.001 * ci  # near-flat
            cells.append(_make_cell(
                group, f"T{ci:02d}", ci,
                mem_evals=21, nomem_evals=30,
                mem_asf=mem_asf, nomem_asf=nomem_asf,
                mem_cai=0.9, nomem_cai=0.85,
                mem_mrl=6.0, nomem_mrl=5.0,
            ))
    return cells


# ------------------------------------------------------------- budget saving


class TestBudgetSavings:
    def test_saving_is_cumulative_ratio_over_paired_cells(self):
        cells = [
            _make_cell("A", "T1", 1, mem_evals=10, nomem_evals=20,
                       mem_asf=0.5, nomem_asf=0.5, mem_cai=0.9, nomem_cai=0.9,
                       mem_mrl=5.0, nomem_mrl=5.0),
            _make_cell("A", "T2", 2, mem_evals=10, nomem_evals=20,
                       mem_asf=0.5, nomem_asf=0.5, mem_cai=0.9, nomem_cai=0.9,
                       mem_mrl=5.0, nomem_mrl=5.0),
        ]
        saving = _budget_savings(cells)
        assert saving["memory_total"] == 20.0
        assert saving["nomem_total"] == 40.0
        assert saving["saving_fraction"] == 0.5
        assert saving["n_paired_cells"] == 2
        assert saving["pass"]  # 50% >= 25%

    def test_failed_arm_cell_excluded_from_pairs(self):
        good = _make_cell("A", "T1", 1, mem_evals=10, nomem_evals=20,
                          mem_asf=0.5, nomem_asf=0.5, mem_cai=0.9, nomem_cai=0.9,
                          mem_mrl=5.0, nomem_mrl=5.0)
        failed = _make_cell("A", "T2", 2, mem_evals=10, nomem_evals=20,
                            mem_asf=0.5, nomem_asf=0.5, mem_cai=0.9, nomem_cai=0.9,
                            mem_mrl=5.0, nomem_mrl=5.0)
        failed["eval_counts"]["memory"] = None  # simulate missing arm
        saving = _budget_savings([good, failed])
        assert saving["n_paired_cells"] == 1
        assert saving["memory_total"] == 10.0


# ---------------------------------------------------------------- regression


class TestRegressionSlopes:
    def test_slope_of_perfectly_linear_data(self):
        cells = [
            _make_cell("A", "T1", 1, mem_evals=10, nomem_evals=10,
                       mem_asf=1.0, nomem_asf=1.0, mem_cai=0.9, nomem_cai=0.9,
                       mem_mrl=5.0, nomem_mrl=5.0),
            _make_cell("A", "T2", 2, mem_evals=10, nomem_evals=10,
                       mem_asf=0.5, nomem_asf=0.5, mem_cai=0.9, nomem_cai=0.9,
                       mem_mrl=5.0, nomem_mrl=5.0),
            _make_cell("A", "T3", 3, mem_evals=10, nomem_evals=10,
                       mem_asf=0.0, nomem_asf=0.0, mem_cai=0.9, nomem_cai=0.9,
                       mem_mrl=5.0, nomem_mrl=5.0),
        ]
        slopes = _slopes_by_group_arm(cells)
        s = slopes["A"]["memory"]
        assert s["n"] == 3
        # x = cumsum(10,10,10) = [10,20,30], y = [1.0,0.5,0.0] -> slope -0.05
        assert s["slope"] == pytest.approx(-0.05, abs=1e-9)
        assert s["r2"] == pytest.approx(1.0, abs=1e-9)

    def test_memory_slope_negative_nomem_flat(self):
        cells = _slope_cells()
        slopes = _slopes_by_group_arm(cells)
        for group in SEED_GROUPS:
            assert slopes[group]["memory"]["slope"] < 0
            assert abs(slopes[group]["nomem"]["slope"]) < abs(slopes[group]["memory"]["slope"])

    def test_too_few_points_is_nan(self):
        cells = [_make_cell("A", "T1", 1, mem_evals=10, nomem_evals=10,
                            mem_asf=0.5, nomem_asf=0.5, mem_cai=0.9, nomem_cai=0.9,
                            mem_mrl=5.0, nomem_mrl=5.0)]
        slopes = _slopes_by_group_arm(cells)
        assert slopes["A"]["memory"]["slope"] != slopes["A"]["memory"]["slope"]  # NaN


# --------------------------------------------------------- efficiency endpoint


class TestEfficiencyEndpoint:
    def test_pass_when_slope_negative_and_saving_high(self):
        cells = _slope_cells()  # memory: slope<0, evals 27-30 vs 30 -> saving
        endpoint = regression_slope_endpoint(cells)
        assert endpoint["slope_significantly_negative"]
        assert endpoint["cumulative_budget_saving"]["saving_fraction"] > 0.25
        assert endpoint["pass"]

    def test_fail_when_no_slope_signal(self):
        cells = _slope_cells()
        # Oscillating ASF (no trend), phase shifted per group so the slopes
        # scatter around 0 -> not significantly negative.
        group_phase = {g: i for i, g in enumerate(SEED_GROUPS)}
        for c in cells:
            phase = group_phase[c["seed_group"]]
            ci = c["campaign_index"]
            c["best_asf_after_truncation"]["memory"] = 0.5 + 0.01 * (-1.0) ** (ci % 2 + phase)
        endpoint = regression_slope_endpoint(cells)
        assert not endpoint["slope_significantly_negative"]
        assert not endpoint["pass"]

    def test_fail_when_saving_below_threshold(self):
        cells = _slope_cells()
        for c in cells:
            c["eval_counts"]["memory"] = 30.0  # equal to nomem -> 0% saving
        endpoint = regression_slope_endpoint(cells)
        assert endpoint["slope_significantly_negative"]
        assert endpoint["cumulative_budget_saving"]["saving_fraction"] == pytest.approx(0.0)
        assert not endpoint["pass"]


# ------------------------------------------------------- design-gain endpoint


class TestDesignGainEndpoint:
    def test_pass_when_memory_better_on_cai_and_mrl(self):
        cells = []
        for gi, group in enumerate(SEED_GROUPS):
            for ci in range(1, 21):
                cells.append(_make_cell(
                    group, f"T{ci:02d}", ci,
                    mem_evals=20, nomem_evals=20,
                    mem_asf=0.5, nomem_asf=0.5,
                    mem_cai=0.95, nomem_cai=0.90,   # memory strictly better
                    mem_mrl=6.5, nomem_mrl=5.5,     # memory strictly better
                ))
        endpoint = wilcoxon_quality_endpoint(cells)
        cai = next(r for r in endpoint["metrics"] if r["key"] == "cds_cai")
        mrl = next(r for r in endpoint["metrics"] if r["key"] == "utr5_predicted_mrl")
        assert cai["n_pairs"] == 60
        assert cai["q_bh"] < 0.05
        assert cai["cliffs_delta"] == pytest.approx(1.0)  # all memory > nomem
        assert cai["pass"]
        assert mrl["pass"]
        assert endpoint["pass"]

    def test_fail_when_no_difference(self):
        cells = []
        for group in SEED_GROUPS:
            for ci in range(1, 21):
                cells.append(_make_cell(
                    group, f"T{ci:02d}", ci,
                    mem_evals=20, nomem_evals=20,
                    mem_asf=0.5, nomem_asf=0.5,
                    mem_cai=0.9, nomem_cai=0.9,
                    mem_mrl=5.5, nomem_mrl=5.5,
                ))
        endpoint = wilcoxon_quality_endpoint(cells)
        for r in endpoint["metrics"]:
            assert not r["pass"]
        assert not endpoint["pass"]

    def test_lower_is_better_metric_direction(self):
        # full_length_mfe: memory much more negative -> favourable.
        cells = []
        for group in SEED_GROUPS:
            for ci in range(1, 21):
                cells.append(_make_cell(
                    group, f"T{ci:02d}", ci,
                    mem_evals=20, nomem_evals=20,
                    mem_asf=0.5, nomem_asf=0.5, mem_cai=0.9, nomem_cai=0.9,
                    mem_mrl=5.0, nomem_mrl=5.0,
                ))
        # Rebuild with full_length_mfe via direct score injection.
        for c in cells:
            bm = c["best_validated_after_truncation"]["memory"]
            bn = c["best_validated_after_truncation"]["nomem"]
            bm["full_length_mfe"] = -600.0
            bn["full_length_mfe"] = -300.0
        endpoint = wilcoxon_quality_endpoint(cells)
        mfe = next(r for r in endpoint["metrics"] if r["key"] == "full_length_mfe")
        assert mfe["cliffs_delta"] == pytest.approx(-1.0)  # memory lower
        assert mfe["favourable_direction"]
        assert mfe["pass"]
        assert endpoint["pass"]

    def test_metric_list_is_the_pre_registered_four(self):
        assert [m["key"] for m in VALIDATED_METRICS] == [
            "cds_cai", "full_length_mfe", "junction_mfe_per_nt", "utr5_predicted_mrl",
        ]
