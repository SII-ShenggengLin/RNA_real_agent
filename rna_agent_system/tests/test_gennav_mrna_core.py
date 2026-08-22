"""Pure-function invariants of the GenNav-λ core (gennav_mrna_lambda).

Pins the mRNA-side navigation machinery — constraint matrix, Laplace
pass-rate, band-gap-first reinforcement, cycling guarantee, per-profile
mechanized delivery — mirroring ``tests/test_gennav_aptamer_core.py``.
"""

from __future__ import annotations

from agent_core.generation.gennav_mrna_lambda import (
    MrnaNavConfig,
    combined_per_nt,
    deliver_profile,
    evaluate_matrix,
    gc_fraction,
    guarantee_round,
    laplace_pass_rate,
    max_homopolymer_run,
    mechanized_proposals,
    normalized_levenshtein,
    profile_gaps,
)

CONFIG = MrnaNavConfig()

# Mutually distant 8-mer units (pairwise normalized Levenshtein ≥ 0.4) so
# D1-diversity delivery tests are about the rule, not accidental similarity.
_UNITS = ["GCUAGCUA", "GGCCAAUU", "GCAUGCAU", "AAUGGUCC"]


def mkseq(i: int, reps: int = 6) -> str:
    return _UNITS[i % len(_UNITS)] * reps


def _cand(cid: str, lam: float, cai, mfe_per_nt, gc=0.50, seq=None) -> dict:
    return {
        "id": cid,
        "sequence": seq or (f"GCUA" * 12),
        "gear": {"lambda": lam},
        "cai": cai,
        "mfe_per_nt": mfe_per_nt,
        "gc": gc,
        "max_homopolymer_run": 3,
        "matrix_pass": evaluate_matrix(cai, mfe_per_nt, gc, 3, CONFIG),
    }


# ── constraints ──────────────────────────────────────────────────────────────


def test_matrix_expression_requires_cai_floor():
    v = evaluate_matrix(0.849, -0.30, 0.50, 3, CONFIG)
    assert v["expression"] is False
    v = evaluate_matrix(0.851, -0.10, 0.50, 3, CONFIG)
    assert v["expression"] is True
    assert v["stability"] is False  # MFE/nt above the −0.25 band


def test_matrix_stability_requires_mfe_band():
    v = evaluate_matrix(0.99, -0.25, 0.50, 3, CONFIG)
    assert v["stability"] is True
    v = evaluate_matrix(0.99, -0.2499, 0.50, 3, CONFIG)
    assert v["stability"] is False


def test_matrix_missing_measurement_never_passes():
    v = evaluate_matrix(None, -0.40, 0.50, 3, CONFIG)
    assert not any([v["expression"], v["balanced"]])  # CAI bands fail
    assert v["stability"] is True  # CAI-free band unaffected
    v = evaluate_matrix(0.95, None, 0.50, 3, CONFIG)
    assert not any([v["stability"], v["balanced"]])
    assert v["expression"] is True


def test_matrix_gc_window_and_homopolymer():
    assert evaluate_matrix(0.95, -0.30, 0.39, 3, CONFIG)["expression"] is False
    assert evaluate_matrix(0.95, -0.30, 0.66, 3, CONFIG)["expression"] is False
    assert evaluate_matrix(0.95, -0.30, 0.50, 10, CONFIG)["expression"] is False


def test_sequence_utils():
    assert gc_fraction("GCGCAUAU") == 0.5
    assert max_homopolymer_run("GCUAAAAGCU") == 4
    assert normalized_levenshtein("GCGC", "GCGC") == 0.0


# ── allocation ───────────────────────────────────────────────────────────────


def test_gaps_empty_pool_all_full():
    gaps = profile_gaps([], CONFIG)
    assert gaps == {p: CONFIG.delivery_size for p in CONFIG.profile_order}


def test_laplace_unsampled_is_uninformed_prior():
    assert laplace_pass_rate([], 4.0) == 0.5


def test_laplace_sampled_pass_and_fail():
    pool = [_cand("a", 4.0, 0.95, -0.30)]  # passes expression + stability
    assert abs(laplace_pass_rate(pool, 4.0) - 2 / 3) < 1e-9
    pool = [_cand("b", 4.0, 0.10, -0.05)]  # passes nothing
    assert abs(laplace_pass_rate(pool, 4.0) - 1 / 3) < 1e-9


def test_mechanized_proposals_only_unsampled_and_gap_first():
    # stability band full (CAI-poor, strongly structured candidates);
    # expression + balanced gapped (CAI below both floors)
    pool = [_cand(f"s{i}", 0.5 * i, 0.50, -0.45, seq=mkseq(i)) for i in range(6)]
    gears = [{"lambda": 0.5 * i} for i in range(6)]
    proposals, gaps = mechanized_proposals(pool, gears, 8, CONFIG)
    assert gaps["stability"] == 0
    assert gaps["expression"] == CONFIG.delivery_size
    assert gaps["balanced"] == CONFIG.delivery_size
    assert proposals, "gapped-region λs must be proposed"
    assert all(p["lambda"] not in {g["lambda"] for g in gears} for p in proposals)


def test_mechanized_proposals_budget_exhausted():
    proposals, _ = mechanized_proposals([], [], CONFIG.raw_budget, CONFIG)
    assert proposals == []


def test_guarantee_round_cycles_profiles_in_order():
    # every band gapped; refinement λs available in each region
    pool: list[dict] = []
    gears: list[dict] = []
    first, bands = guarantee_round(pool, gears, 0, CONFIG)
    assert first["region"] == CONFIG.profile_order[0]
    assert bands == {CONFIG.profile_order[0]}
    gears.append({"lambda": first["lambda"]})
    second, bands = guarantee_round(pool, gears, 1, CONFIG, guaranteed_bands=bands)
    assert second["region"] == CONFIG.profile_order[1]
    assert bands == set(CONFIG.profile_order[:2])


def test_guarantee_round_budget_exhausted():
    gear, bands = guarantee_round([], [], CONFIG.raw_budget, CONFIG)
    assert gear is None and bands == set()


# ── delivery ─────────────────────────────────────────────────────────────────


def test_delivery_filters_matrix_and_orders_by_profile_utility():
    # expression band: three passing candidates with distinct CAI
    pool = [
        _cand("lo", 10.0, 0.86, -0.05, seq=mkseq(0)),
        _cand("mid", 12.0, 0.90, -0.06, seq=mkseq(1)),
        _cand("hi", 15.0, 0.95, -0.07, seq=mkseq(2)),
        _cand("fail", 0.0, 0.70, -0.40),  # stability-only passer
    ]
    d = deliver_profile(pool, "expression", CONFIG)
    assert d["ids"] == ["hi", "mid", "lo"]
    assert d["degraded"] is True  # 3 < 5
    assert "post-D1 deliverable 3/5" in d["degrade_reason"]


def test_delivery_stability_orders_by_most_negative_mfe():
    pool = [
        _cand("m1", 0.0, 0.99, -0.26, seq=mkseq(0)),
        _cand("m2", 0.5, 0.99, -0.45, seq=mkseq(1)),
        _cand("m3", 1.0, 0.99, -0.35, seq=mkseq(2)),
    ]
    d = deliver_profile(pool, "stability", CONFIG)
    assert d["ids"] == ["m2", "m3", "m1"]


def test_delivery_balanced_uses_combined_score():
    # same CAI; b2 has stronger MFE → higher combined per nt
    pool = [
        _cand("b1", 4.0, 0.85, -0.21, seq=mkseq(0)),
        _cand("b2", 6.0, 0.85, -0.30, seq=mkseq(1)),
    ]
    d = deliver_profile(pool, "balanced", CONFIG)
    assert d["ids"] == ["b2", "b1"]
    assert combined_per_nt(pool[1]) > combined_per_nt(pool[0])


def test_delivery_d1_diversity_floor():
    # near-identical sequences: only the first of each ≥0.15-distance clique fits
    # (x1 has the stronger MFE so the utility order admits it first)
    base = "GCGCGCGCAUAUAUAU" * 3
    pool = [
        _cand("x1", 0.0, 0.99, -0.46, seq=base),
        _cand("x2", 0.5, 0.99, -0.45, seq=base[:-1] + "C"),
        _cand("far", 1.0, 0.98, -0.44, seq="AAUGGUCC" * 6),
    ]
    d = deliver_profile(pool, "stability", CONFIG)
    assert "x1" in d["ids"] and "far" in d["ids"]
    assert len([i for i in d["ids"] if i.startswith("x")]) == 1


def test_delivery_deterministic():
    pool = [_cand(f"c{i}", 0.5 * i, 0.80 + 0.02 * i, -0.45 + 0.02 * i,
                  seq=mkseq(i)) for i in range(6)]
    d1 = deliver_profile(pool, "balanced", CONFIG)
    d2 = deliver_profile(pool, "balanced", CONFIG)
    assert d1["ids"] == d2["ids"]
