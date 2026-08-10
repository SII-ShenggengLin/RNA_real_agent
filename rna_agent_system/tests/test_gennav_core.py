"""Tests for agent_core.generation.gennav_core (E6 约束导航生成器, 组件 1–4 纯函数).

全部本地(零微服务依赖): 动态档序/取档计划/三方向轴确定性/多样度接受/
CodonContext 18 靶决议 fixture + 显式失败/D2 复合判据/格级声明。
基线 649 passed 保持; 本文件新增全绿。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agent_core.generation.gennav_core import (
    AXES,
    CAI_FLOOR_TARGET,
    DIVERSITY_DENSITY,
    DIVERSITY_MIN_PAIRWISE,
    DIVERSITY_N_VARIANTS,
    PROBE_LAMBDAS,
    PROFILE_TO_AXIS,
    SOURCE_SPECIES_NOTES,
    STATIC_LAMBDAS,
    CodonContextResolver,
    aa_synonyms,
    axis_apply_frac,
    axis_cai_floor,
    axis_cai_max,
    axis_frac_tuned,
    cai_local,
    d2_composite,
    delivery_cai_span,
    diversity_accept,
    dynamic_pref_ranks,
    dynamic_rank_map,
    gear_selection_plan,
    independent_rank,
    lattice_gear_declaration,
    min_pairwise,
    synonymous_diversify,
    _seed,
)

# 与探针 P2 同款靶(行为已知: frac 12–26 种子命中 [0.88,0.92]; floor 0.85)
INSULIN_AA = (
    "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVG"
    "QVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"
)
A1AT_AA = ("MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVG"
           "QVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN")  # 占位(仅档序测试用)

TARGETS_DIR = (Path(__file__).resolve().parents[1]
               / "data/benchmarks/RNA-BioBench-FullLength-mRNA/targets")
FULL_TARGETS = [
    "A1AT", "Albumin", "Beta_galactosidase", "EPO", "GFP",
    "Growth_hormone", "HER2", "HIV-1_Env_gp120", "HPV16_L1", "IFN_alpha_2a",
    "IL-2", "Influenza_HA_H1N1", "Insulin", "Luciferase", "Ovalbumin",
    "RSV_F_protein", "SARS-CoV-2_Spike_WT", "Transferrin",
]
# 复现锚点: 探针缓存键后缀(E. coli CSV 内容 hash, 跨靶统一口径)
PROBE_CSV_HASH = "26308b892d84"


@pytest.fixture(scope="module")
def ctx() -> CodonContextResolver:
    return CodonContextResolver("Homo sapiens")


# ═══════════════════════════════════════════════════════════════════════════════
# 组件 1: 动态档序 + 取档计划
# ═══════════════════════════════════════════════════════════════════════════════


def test_dynamic_rank_map_gfp_gears():
    """GFP 可行档 {4,10,50} → 档 0/1/2(静态 LAMBDA_RANK 替代)。"""
    rm = dynamic_rank_map([4.0, 10.0, 50.0])
    assert rm == {4.0: 0, 10.0: 1, 50.0: 2}


def test_dynamic_rank_map_sorted_input():
    """档序与输入顺序无关(按 λ 升序)。"""
    assert dynamic_rank_map([50.0, 4.0, 10.0]) == dynamic_rank_map([4.0, 10.0, 50.0])


def test_independent_rank_after_ld():
    """独立来源行(GEMORNA/RNARL)排 LD 后: 档位 = len(ld_gears)。"""
    assert independent_rank([4.0, 10.0]) == 2
    assert independent_rank([]) == 0


def test_dynamic_pref_ranks():
    """动态 λ 偏好查表: small→最小档, large→最大档, middle→中位档。"""
    pr = dynamic_pref_ranks({4.0: 0, 10.0: 1, 50.0: 2})
    assert pr == {"small": 0, "large": 2, "middle": 1}
    pr2 = dynamic_pref_ranks({2.0: 0, 8.0: 1, 20.0: 2, 50.0: 3})
    assert pr2["small"] == 0 and pr2["large"] == 3 and pr2["middle"] == 2
    assert dynamic_pref_ranks({}) == {"small": 0, "large": 0, "middle": 0}


def test_gear_selection_plan_full_under_cap():
    """≥3 档且 ≤5 → mode=full 全取, 无二分。"""
    plan = gear_selection_plan([2.0, 8.0, 20.0])
    assert plan["mode"] == "full"
    assert plan["gears"] == [2.0, 8.0, 20.0]
    assert plan["bisect_lambda"] is None


def test_gear_selection_plan_full_over_cap():
    """>5 档 → 保端点 + 均分点(跨度最大化, 取 ≤5)。"""
    plan = gear_selection_plan([1.0, 2.0, 4.0, 8.0, 10.0, 20.0, 50.0])
    assert plan["mode"] == "full"
    assert len(plan["gears"]) <= 5
    assert plan["gears"][0] == 1.0 and plan["gears"][-1] == 50.0  # 端点保留


def test_gear_selection_plan_bisect():
    """恰 2 档 → mode=bisect, 区间中点插 1 档(驱动探测)。"""
    plan = gear_selection_plan([4.0, 10.0])
    assert plan["mode"] == "bisect"
    assert plan["bisect_lambda"] == 7.0


def test_gear_selection_plan_degrade():
    """≤1 档 → mode=degrade(方向轴承担降级路径)。"""
    plan = gear_selection_plan([4.0])
    assert plan["mode"] == "degrade" and plan["bisect_lambda"] is None
    plan0 = gear_selection_plan([])
    assert plan0["mode"] == "degrade" and plan0["gears"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# 组件 2: 方向轴(拍板②口径: frac 半倾斜混合 + 接受重试; floor 目标 0.85)
# ═══════════════════════════════════════════════════════════════════════════════


def test_axis_cai_max_deterministic(ctx):
    """cai_max 轴: 每 aa 取 fraction 最高密码子 → 确定性(两次调用逐位一致)。"""
    a = axis_cai_max(INSULIN_AA, ctx.synonyms)
    b = axis_cai_max(INSULIN_AA, ctx.synonyms)
    assert a == b
    assert cai_local(a, ctx.weights) >= cai_local(
        axis_frac_tuned(INSULIN_AA, ctx.synonyms, ctx.weights, seed=12345),
        ctx.weights)


def test_axis_cai_max_plateau(ctx):
    """cai_max CAI 近 plateau(≥0.95; 与探针 A1AT 1.0 / Insulin 1.0 同量级)。"""
    cds = axis_cai_max(INSULIN_AA, ctx.synonyms)
    assert cai_local(cds, ctx.weights) >= 0.95


def test_axis_frac_tuned_calibration(ctx):
    """frac 轴(拍板②): 半倾斜混合 + 接受重试 → CAI ∈ [0.88, 0.92](±0.01 容差)。"""
    cds = axis_frac_tuned(INSULIN_AA, ctx.synonyms, ctx.weights, seed=12345)
    cai = cai_local(cds, ctx.weights)
    assert 0.87 <= cai <= 0.93, f"frac CAI {cai:.4f} 偏离标定窗口"
    assert len(cds) == 3 * len(INSULIN_AA)  # 同义保持长度(回归: i*3 双重索引 bug)


def test_axis_apply_frac_preserves_source_features(ctx):
    """frac 轴在源 CDS 上应用(0.5 保留源密码子, P2 修复 1): 与源编辑距离适度。"""
    base = axis_cai_max(INSULIN_AA, ctx.synonyms)
    import random as _r

    rng = _r.Random(_seed("frac-test"))
    out = axis_apply_frac(base, ctx.synonyms, rng)
    dist = sum(1 for x, y in zip(base, out) if x != y) / len(base)
    assert 0.05 <= dist <= 0.95  # 既非零(有混合)也非全换(保留源特征)
    assert cai_local(out, ctx.weights) >= 0.80  # 硬约束 CAI_MIN 不破


def test_axis_cai_floor_target(ctx):
    """floor 轴(拍板②): 目标 0.85(留扩展器余量), 硬约束 CAI_MIN 0.8 不破。"""
    cds = axis_cai_floor(INSULIN_AA, ctx.synonyms, ctx.weights,
                         rng=None, floor_target=CAI_FLOOR_TARGET)
    cai = cai_local(cds, ctx.weights)
    assert 0.83 <= cai <= 0.90, f"floor CAI {cai:.4f} 偏离目标 0.85"
    assert cai >= 0.80


def test_three_axes_separation_construction(ctx):
    """三轴 CAI 构造分离(≥0.05): cai_max plateau / frac ~0.90 / floor ~0.85。"""
    cais = [
        cai_local(axis_cai_max(INSULIN_AA, ctx.synonyms), ctx.weights),
        cai_local(axis_frac_tuned(INSULIN_AA, ctx.synonyms, ctx.weights,
                                  seed=12345), ctx.weights),
        cai_local(axis_cai_floor(INSULIN_AA, ctx.synonyms, ctx.weights,
                                 rng=None, floor_target=CAI_FLOOR_TARGET),
                  ctx.weights),
    ]
    assert cais[0] - cais[2] >= 0.05
    assert cais[0] >= cais[1] >= cais[2]


def test_profile_to_axis_mapping():
    """画像 → 轴映射(组件 2 正交): expression→cai_max, balanced→frac, stability→cai_floor。"""
    assert PROFILE_TO_AXIS["expression"] == "cai_max"
    assert PROFILE_TO_AXIS["balanced"] == "frac"
    assert PROFILE_TO_AXIS["stability"] == "cai_floor"
    assert set(AXES) == {"cai_max", "frac", "cai_floor"}


# ═══════════════════════════════════════════════════════════════════════════════
# 组件 3: 多样度扩展器 + 生成时接受
# ═══════════════════════════════════════════════════════════════════════════════


def test_min_pairwise(ctx):
    cds_a = axis_cai_max(INSULIN_AA, ctx.synonyms)
    cds_b = synonymous_diversify(cds_a, ctx.weights, ctx.synonyms,
                                 density=0.20, n=1, seed=7)[0]
    assert min_pairwise([cds_a, cds_b]) == min_pairwise([cds_b, cds_a]) > 0.0


def test_diversity_accept_thresholds(ctx):
    """生成时接受: CAI≥CAI_MIN ∧ local_ok ∧ pairwise≥3%(判据 2% 留 1pp 余量)。"""
    base = axis_cai_max(INSULIN_AA, ctx.synonyms)
    # 与自身距离 0 → 拒
    assert not diversity_accept(base, [base], cai_local(base, ctx.weights), True)
    # CAI 不足 → 拒
    assert not diversity_accept(base, [], 0.79, True)
    # 本地约束不满足 → 拒
    assert not diversity_accept(base, [], cai_local(base, ctx.weights), False)
    # 空已选集 → 收
    assert diversity_accept(base, [], cai_local(base, ctx.weights), True)
    # 同义变体 ≥3% → 收
    var = synonymous_diversify(base, ctx.weights, ctx.synonyms,
                               density=0.25, n=1, seed=11)[0]
    if min_pairwise([var, base]) >= DIVERSITY_MIN_PAIRWISE:
        assert diversity_accept(var, [base], cai_local(var, ctx.weights), True)
    else:
        assert not diversity_accept(var, [base], cai_local(var, ctx.weights), True)


def test_synonymous_diversify_keeps_constraints(ctx):
    """扩展器输出: 与源编辑距离 >0, CAI ≥ CAI_MIN(0.8 硬约束), 同义(长度一致)。"""
    base = axis_cai_max(INSULIN_AA, ctx.synonyms)
    for seed in range(3):
        var = synonymous_diversify(base, ctx.weights, ctx.synonyms,
                                   density=DIVERSITY_DENSITY, n=1, seed=seed)[0]
        assert len(var) == len(base)
        assert var != base
        assert cai_local(var, ctx.weights) >= 0.80
        assert min_pairwise([var, base]) >= 0.0


def test_density_calibration_insulin(ctx):
    """密度 0.10 标定(P3): Insulin 全 CDS 变体 pairwise ≥ 0.015(探针曲线 0.0177)。"""
    base = axis_cai_max(INSULIN_AA, ctx.synonyms)
    variants = synonymous_diversify(base, ctx.weights, ctx.synonyms,
                                    density=DIVERSITY_DENSITY,
                                    n=DIVERSITY_N_VARIANTS, seed=42)
    assert len(variants) == DIVERSITY_N_VARIANTS
    for v in variants:
        assert min_pairwise([v, base]) >= 0.015


def test_cell_seed_stability():
    """格种子稳定(同字符串同种子; 跨进程可复现)。"""
    assert _seed("Insulin|ld|2.0|0|frac") == _seed("Insulin|ld|2.0|0|frac")
    assert _seed("Insulin|ld|2.0|0|frac") != _seed("Insulin|ld|2.0|0|cai_max")
    assert _seed("Insulin|ld|2.0|0|frac") != _seed("Insulin|gm|1|0|frac")  # P2 修复 3


# ═══════════════════════════════════════════════════════════════════════════════
# 拍板① D2 复合判据 + E14 格级声明
# ═══════════════════════════════════════════════════════════════════════════════


def test_delivery_cai_span():
    assert delivery_cai_span([0.9, 0.85, 0.80]) == pytest.approx(0.1)
    assert delivery_cai_span([0.9]) == 0.0
    assert delivery_cai_span([]) == 0.0
    assert delivery_cai_span([0.9, 0.9]) == 0.0


def test_d2_composite():
    """【拍板①】D2 = D1 ∧ 交付内 CAI 跨度 ≥ 0.05。"""
    assert d2_composite(True, [0.9, 0.85, 0.80]) is True   # span 0.10
    assert d2_composite(True, [0.9, 0.87, 0.86]) is False  # span 0.04 < 0.05
    assert d2_composite(False, [0.9, 0.85, 0.80]) is False  # D1 不满足
    assert d2_composite(True, [0.9]) is False               # 单候选 span 0


def test_lattice_gear_declaration():
    """E14_gen_lattice 格级声明: 格内 LD 档数 ≥3 达标(档覆盖由格承担)。"""
    decl = lattice_gear_declaration({4.0: 0, 10.0: 1, 50.0: 2})
    assert decl == {"n_ld_gears": 3, "ge_3": True}
    assert lattice_gear_declaration({4.0: 0, 10.0: 1})["ge_3"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# 组件 4: CodonContextResolver(18 靶决议 fixture + 显式失败)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("target_id", FULL_TARGETS)
def test_context_resolver_18_targets(target_id):
    """18 靶全 host 表命中(表达宿主优先; P4 18/18)。"""
    meta = json.loads((TARGETS_DIR / f"{target_id}.json").read_text(encoding="utf-8"))
    species = meta["species_for_codon_optimization"]
    res = CodonContextResolver(species)
    assert res.resolution()["table_hit"] is True
    assert res.resolution()["resolution"] == "host"
    if target_id in ("GFP", "Beta_galactosidase"):
        assert res.canonical == "Escherichia coli K-12"
    else:
        assert res.canonical == "Homo sapiens"


def test_context_codon_usage_csv_human_none(ctx):
    """Homo sapiens → None(LD 默认表, 与 r5 逐位一致)。"""
    assert ctx.codon_usage_csv(Path("/tmp/e6_test_ctxt")) is None


def test_context_codon_usage_csv_ecoli_hash(tmp_path):
    """E. coli CSV 字节 hash == 探针键后缀(复现锚点; 键跨进程稳定)。"""
    ctx_e = CodonContextResolver("E. coli")
    path = ctx_e.codon_usage_csv(tmp_path)
    assert path is not None and path.is_file()
    h = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    assert h == PROBE_CSV_HASH, (
        f"E. coli CSV hash {h} != probe {PROBE_CSV_HASH}: 探针缓存键将 miss")


def test_context_explicit_failure():
    """表缺失显式失败(计划 C5): 构造抛 KeyError, 不静默回退 human。"""
    with pytest.raises(KeyError):
        CodonContextResolver("Homo neanderthalensis")


def test_source_species_notes():
    """P4 注记: GFP/Luciferase/Ovalbumin 源物种记录(host-based approximation)。"""
    assert SOURCE_SPECIES_NOTES == {
        "GFP": "Aequorea victoria",
        "Luciferase": "Photinus pyralis",
        "Ovalbumin": "Gallus gallus",
    }


def test_probe_lambdas_grid():
    """粗探网格与静态池 λ 网格(计划 §1; 探针 P1 口径)。"""
    assert PROBE_LAMBDAS == (0.0, 2.0, 8.0, 20.0, 50.0)
    assert STATIC_LAMBDAS == (0.0, 1.0, 4.0, 10.0)


def test_aa_synonyms_table(ctx):
    """同义位点表: 非 W/M 每 aa ≥2 密码子; 所有 codon 3nt 且 fraction ∈ (0,1]。"""
    for aa, codons in ctx.synonyms.items():
        if aa not in ("W", "M"):  # W(UGG)/M(AUG) 天然单同义
            assert len(codons) >= 2, f"{aa}: 单同义 {codons}"
        for codon, frac in codons:
            assert len(codon) == 3 and 0.0 < frac <= 1.0
