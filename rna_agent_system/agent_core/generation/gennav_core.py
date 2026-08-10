"""E6「约束导航生成器」核心(组件 1–4 纯函数, 2026-08-09 拍板口径)。

E5 S1 整体 NO-GO 的剩余失败因子(R3 档距结构性不可达 / D1 λ 饱和趋同 /
D2 可行档不足 / S2 显著性平局)共同根源 = **生成与选择分离**: agent 只能在
固定配方池上被动选择, 判据需要的性质(分离/多样/覆盖)在生成时不存在。
E6 = 约束导航下沉到生成层 —— 四组件统一为 FAD 生成格(GenerationLattice):

  组件 1 可行性优先自适应生成: 动态档序(按生成 λ 排序赋值)、动态 λ 偏好查表、
          取档计划(≥3 档取 3–5 / 2 档二分插 1 / ≤1 档方向轴降级)、动态 U。
  组件 2 画像正交方向轴: cai_max(确定性 plateau) / frac(半倾斜混合+接受重试,
          拍板② [0.88, 0.92]) / cai_floor(逆加权+逐位贪心修复, 拍板② floor_target=0.85)。
  组件 3 多样度扩展器: 全 CDS 同义多样化(排除 AUG/stop/单同义位点), 生成时接受
          (CAI≥CAI_MIN ∧ 本地约束零 fold 过 ∧ 与已选 pairwise ≥ 3%)。
  组件 4 物种密码子上下文: CodonContextResolver(表达宿主优先 + 显式失败决议记录)。

拍板记录(2026-08-09 用户, 依据 HANDOFF_2026-08-09_E6_PROBED_PENDING.md):
  ① D2 修订 = 交付多样度复合判据 = D1 ∧ 交付内 CAI 跨度 ≥ 0.05;
     C 臂 λ 档覆盖改由 E14_gen_lattice 格级声明(格内 LD 档数 ≥ 3)。
  ② frac 轴标定 = 半倾斜混合 + 接受重试 CAI∈[0.88, 0.92]; cai_floor 目标 0.85
     (硬约束 CAI_MIN 0.8 与 R3 分离阈值 0.05 均不变)。
  ③ R3 轴内语义 = top-1 按轴锁定交付取, 分离由构造保证。

复用 run_e5_constraint_nav 纯函数(import 零复制): 约束判定 / 档案 / U 组件;
旧链路(该文件 / codon_tables / sequence_utils / mrna_cds_design / lineardesign
服务)零改动。本模块全部函数纯(无 IO/无服务), 由 experiments/run_e6_gennav.py
驱动; 轴函数从探针 probe_e6_gennav.py 升格并按拍板②口径正式化。
"""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

from experiments import run_e5_constraint_nav as m  # noqa: E402
from agent_core.sequence_utils import (  # noqa: E402
    _load_builtin_codon_tables,
    build_cai_weights,
    compute_cai,
    export_codon_usage_csv,
    resolve_species_name,
)

# ---------------------------------------------------------------------------
# 组件 1 参数(粗探网格与档序语义; 驱动侧在 run_e6_gennav.py 提供探测服务)
# ---------------------------------------------------------------------------

# 粗探网格(P1 实证: 5 靶可行档全部出自该网格 ∪ survey {0,1,4,10})
PROBE_LAMBDAS: tuple[float, ...] = (0.0, 2.0, 8.0, 20.0, 50.0)
# 静态配方池 λ(E5 r5 语义, A/B 臂)
STATIC_LAMBDAS: tuple[float, ...] = (0.0, 1.0, 4.0, 10.0)
# 取档计划上限(组件 1: ≥3 档时取 3–5 档)
MAX_GEARS = 5

# ---------------------------------------------------------------------------
# 组件 2 方向轴定义(拍板②标定)
# ---------------------------------------------------------------------------

AXES: tuple[str, ...] = ("cai_max", "frac", "cai_floor")
AXIS_TO_PROFILE: dict[str, str] = {
    "cai_max": "expression", "frac": "balanced", "cai_floor": "stability",
}
PROFILE_TO_AXIS: dict[str, str] = {v: k for k, v in AXIS_TO_PROFILE.items()}

# 【拍板② 2026-08-09】frac 轴 = 半倾斜混合(mix_p=0.5) + 接受重试 CAI∈[0.88, 0.92]
# (纯 fraction 加权在 A1AT 0.77/Insulin 0.69 结构性低于 CAI_MIN, P2 实证)。
FRAC_MIX_P = 0.5
FRAC_TARGET_LO, FRAC_TARGET_HI = 0.88, 0.92
FRAC_MAX_TRY = 64
# 【拍板② 2026-08-09】cai_floor 目标 0.85(留 ≥0.05 多样度扩展余量;
# 硬约束 CAI_MIN=0.8 与 R3 分离阈值 0.05 不变)。
CAI_FLOOR_TARGET = 0.85
# R3 分离阈值(不变, 拍板③确认)
R3_CAI_SEP = 0.05
R3_RANK_SEP = 2

# ---------------------------------------------------------------------------
# 组件 3 多样度扩展器参数(P3 标定: 密度 0.10, 两靶 pairwise≥3%)
# ---------------------------------------------------------------------------

DIVERSITY_MIN_PAIRWISE = 0.03      # 判据 2% 留 1pp 余量
DIVERSITY_DENSITY = 0.10           # P3 标定值(上限 0.30)
DIVERSITY_N_VARIANTS = 4           # 格内每轴 CDS 取扩展器第 1 变体
D2_CAI_SPAN_MIN = 0.05             # 【拍板① 2026-08-09】D2 复合判据 CAI 跨度下界

# ---------------------------------------------------------------------------
# 组件 4 自然来源物种注记(target_id → 自然来源; host-based approximation 注记)
# ---------------------------------------------------------------------------

SOURCE_SPECIES_NOTES: dict[str, str] = {
    "GFP": "Aequorea victoria",
    "Luciferase": "Photinus pyralis",
    "Ovalbumin": "Gallus gallus",
}

# ---------------------------------------------------------------------------
# 公共纯函数
# ---------------------------------------------------------------------------


def _seed(s: str) -> int:
    """确定性种子(md5; 跨进程可复现, 替代进程盐化 hash())。"""
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % (2**31)


def _rna(seq: str) -> str:
    return m._rna(seq)


def aa_synonyms(table: dict) -> dict[str, list[tuple[str, float]]]:
    """aa -> [(codon, fraction), ...](排除 stop); fraction 为 Kazusa 原始值。"""
    out: dict[str, list[tuple[str, float]]] = {}
    for codon, info in table.items():
        aa = info["aa"]
        if aa in ("*", ""):
            continue
        out.setdefault(aa, []).append((codon, float(info["fraction"])))
    return out


def cai_local(cds: str, weights: dict[str, float]) -> float:
    return float(compute_cai(_rna(cds), weights)["cai_score"])


# ---------------------------------------------------------------------------
# 组件 1: 可行性优先自适应生成(纯逻辑; LD 探测服务由驱动提供)
# ---------------------------------------------------------------------------


def dynamic_rank_map(ld_gears: list[float]) -> dict[float, int]:
    """动态档序: LD 可行档按 λ 升序赋 0..n-1(替代 E5 静态 LAMBDA_RANK)。

    独立来源行(RNARL/GEMORNA)排 LD 后: 档位 = len(ld_gears)(单一档层)。
    GFP {λ4, λ10, λ50} → 档 0/1/2 → D2(格级)构造可达。
    """
    return {lam: i for i, lam in enumerate(sorted(ld_gears))}


def independent_rank(ld_gears: list[float]) -> int:
    """独立来源行档位(排 LD 后; E5 语义 GEMORNA 同档、RNARL 更后)。"""
    return len(ld_gears)


def dynamic_pref_ranks(rank_map: dict[float, int]) -> dict[str, int]:
    """动态 λ 偏好查表: small → 最小可行档, large → 最大可行档, middle → 中位档。"""
    gears = sorted(rank_map)
    if not gears:
        return {"small": 0, "large": 0, "middle": 0}
    return {"small": rank_map[gears[0]],
            "large": rank_map[gears[-1]],
            "middle": rank_map[gears[len(gears) // 2]]}


def gear_selection_plan(feasible_gears: list[float],
                        max_gears: int = MAX_GEARS) -> dict:
    """取档计划(组件 1): 可行档集合 → (档位表, 模式, 二分插入 λ)。

    - ≥3 档 → mode=full, 取 3–5 档(超限时保端点+均分点, 最大化 λ 跨度);
    - 恰 2 档 → mode=bisect, 区间中点插 1 档(驱动探测 1 次 LD, 可行则并入);
    - ≤1 档 → mode=degrade, 方向轴承担(降级路径)。
    """
    gears = sorted(feasible_gears)
    if len(gears) >= 3:
        if len(gears) <= max_gears:
            return {"gears": gears, "mode": "full", "bisect_lambda": None}
        picks = sorted({0, len(gears) - 1, len(gears) // 2,
                        len(gears) // 4, (3 * len(gears)) // 4})
        return {"gears": [gears[i] for i in picks], "mode": "full",
                "bisect_lambda": None}
    if len(gears) == 2:
        return {"gears": gears, "mode": "bisect",
                "bisect_lambda": round((gears[0] + gears[1]) / 2.0, 1)}
    return {"gears": gears, "mode": "degrade", "bisect_lambda": None}


def utility_dyn(cand: dict, profile: str, norms: dict,
                rank_map: dict[float, int], rank_span: int,
                pref_ranks: dict[str, int] | None = None) -> float:
    """E6 U(镜像 E5 公式; 动态档序 + 动态 λ 偏好查表)。

    U = (0.8×regional + 0.2×global(MFE) + W_LAMBDA×λ 偏好) / (1+W_LAMBDA);
    公式与权重与 E5 utility() 逐位一致, 仅 λ 偏好档改动态查表。
    """
    pref = m.PROFILE_DEFS[profile]["lambda_pref"]
    if pref_ranks is None:
        pref_ranks = dynamic_pref_ranks(rank_map)
    pref_rank = pref_ranks.get(pref, 0)
    dist = abs(cand["lambda_rank"] - pref_rank)
    lam_comp = 1.0 - min(dist, rank_span) / rank_span
    regional = m.regional_metric(cand, profile, norms)["regional"]
    lo, hi = norms.get("E2_full_mfe", (0.0, 1.0))
    mfe_norm = 1.0 - m._norm(cand["archive"].get("E2_full_mfe"), lo, hi)
    base = m.W_REGIONAL * regional + m.W_GLOBAL * mfe_norm
    return (base + m.W_LAMBDA * lam_comp) / (1.0 + m.W_LAMBDA)


def assign_utilities_dyn(pool: dict) -> None:
    """格级 U 覆盖: E5 pool_normalizers + E6 动态 U(按格 rank_map/pref_ranks)。"""
    norms = m.pool_normalizers(pool)
    rank_map = pool["rank_map"]
    span = pool["rank_span"]
    pref_ranks = pool["pref_ranks"]
    for c in pool["candidates"]:
        c["scores"] = {pr: m.regional_metric(c, pr, norms) for pr in m.PROFILES}
        c["utility"] = {pr: utility_dyn(c, pr, norms, rank_map, span, pref_ranks)
                        for pr in m.PROFILES}
    pool["norms"] = norms


# ---------------------------------------------------------------------------
# 组件 2: 画像正交方向轴(拍板②口径)
# ---------------------------------------------------------------------------


def axis_cai_max(protein: str, syn: dict[str, list[tuple[str, float]]]) -> str:
    """方向轴 cai_max: 每 aa 取 fraction 最高密码子(确定性, CAI≈plateau)。

    收敛语义: 与源档 CDS 无关(任何源应用后收敛至同一序列);
    格内跨档多样度由多样度扩展器(种子含 λ/源 idx)承担。"""
    return "".join(max(syn[aa], key=lambda cf: cf[1])[0] for aa in protein)


def axis_frac(protein: str, syn: dict[str, list[tuple[str, float]]],
              rng: random.Random, mix_p: float = FRAC_MIX_P) -> str:
    """方向轴 frac(半倾斜混合): 每 aa 位 mix_p 概率取最高 fraction 密码子,
    否则 fraction 加权随机 —— CAI 落在 plateau 与 floor 之间(~0.85–0.90),
    避免纯 fraction 加权在部分靶结构性低于 CAI_MIN(P2 实证 A1AT 0.77/Insulin 0.69)。"""
    out = []
    for aa in protein:
        cs = syn[aa]
        if rng.random() < mix_p:
            out.append(max(cs, key=lambda cf: cf[1])[0])
        else:
            out.append(rng.choices([c for c, _ in cs],
                                   weights=[f for _, f in cs])[0])
    return "".join(out)


def axis_frac_tuned(protein: str, syn: dict[str, list[tuple[str, float]]],
                    weights: dict[str, float], seed: int,
                    lo: float = FRAC_TARGET_LO, hi: float = FRAC_TARGET_HI,
                    max_try: int = FRAC_MAX_TRY) -> str:
    """frac 轴目标定位【拍板②】: 接受重试至 CAI ∈ [lo, hi](种子化, 可复现)。

    组件 2×3 叠加的 CAI 余量保证: frac 目标 0.90(中间档), 多样度扩展(≈0.02
    降幅)后仍 ≥ CAI_MIN; 与 cai_max(≈1.0)/cai_floor(0.85) 两两差 ≥0.05
    → R3 分离由构造保证(3/3 pair)。理论不可达时退化为确定性 plateau(仍过硬约束)。
    """
    for s in range(seed, seed + max_try):
        cds = axis_frac(protein, syn, random.Random(s))
        if lo <= cai_local(cds, weights) <= hi:
            return cds
    return axis_cai_max(protein, syn)


def axis_apply_frac(cds: str, syn: dict[str, list[tuple[str, float]]],
                    rng: random.Random, mix_p: float = FRAC_MIX_P) -> str:
    """frac 轴在源档 CDS 上应用: 每 aa 位 mix_p 概率 fraction 加权随机替换,
    否则保留源密码子 —— 格内同轴跨档 CDS 保留 λ 档差异(源 CDS 上应用, P2 修复 3)。"""
    out = []
    for i in range(0, len(cds) - 2, 3):
        codon = cds[i:i + 3]
        aa = _codon_aa(codon, syn)
        if aa is None or aa == "*":
            out.append(codon)
            continue
        if rng.random() < mix_p:
            out.append(rng.choices([c for c, _ in syn[aa]],
                                   weights=[f for _, f in syn[aa]])[0])
        else:
            out.append(codon)
    return "".join(out)


def _codon_aa(codon: str, syn: dict[str, list[tuple[str, float]]]) -> str | None:
    for aa, cf in syn.items():
        for c, _f in cf:
            if c == codon:
                return aa
    return None


def axis_cai_floor(protein: str, syn: dict[str, list[tuple[str, float]]],
                   weights: dict[str, float], rng: random.Random,
                   floor_target: float = CAI_FLOOR_TARGET) -> str:
    """方向轴 cai_floor: fraction 逆加权(取最低) + 逐位贪心修复至 CAI ≥ floor_target。

    【拍板②】floor_target=0.85(下沿档, 留 ≥0.05 多样度扩展余量; 硬约束仍 0.8)。
    修复顺序: 按「提升 gain 降序」逐位替换为该 aa 的最高 fraction 密码子,
    直到整链 CAI ≥ floor_target —— 结构扰动最大化同时约束满足。
    rng 保留签名(种子化; 当前修复路径确定性, 供未来扩展)。
    """
    base = "".join(min(syn[aa], key=lambda cf: cf[1])[0] for aa in protein)
    if cai_local(base, weights) >= floor_target:
        return base
    cds = list(base)
    max_codons = {aa: max(syn[aa], key=lambda cf: cf[1])[0] for aa in syn}
    gains = []
    for i, aa in enumerate(protein):
        cur = base[i * 3:(i + 1) * 3]
        cur_f = dict(syn[aa])[cur] if cur in dict(syn[aa]) else 0.0
        max_f = max(f for _, f in syn[aa])
        gains.append((i, aa, cur, max_f / max(cur_f, 1e-9)))
    for i, aa, _cur, _g in sorted(gains, key=lambda g: g[3], reverse=True):
        cds[i * 3:(i + 1) * 3] = list(max_codons[aa])
        if cai_local("".join(cds), weights) >= floor_target:
            break
    return "".join(cds)


# ---------------------------------------------------------------------------
# 组件 3: 多样度扩展器(生成时多样度约束)
# ---------------------------------------------------------------------------


def synonymous_diversify(cds: str, weights: dict[str, float],
                         syn: dict[str, list[tuple[str, float]]],
                         density: float, n: int = 6, seed: int = 0) -> list[str]:
    """全 CDS 同义多样化(排除 AUG/stop/单同义位点; P3 标定密度 0.10)。

    density = 可变位点替换比例; 每变体 fraction 加权随机选同义密码子;
    返回 n 个变体(种子化, 可复现)。权重参数保留(接受器使用, 生成内不用)。"""
    positions = []
    for i in range(0, len(cds) - 2, 3):
        codon = cds[i:i + 3]
        if codon in ("AUG", "UAA", "UAG", "UGA"):
            continue  # 排除起始/终止
        aa = _codon_aa(codon, syn)
        if aa is None or aa == "*":
            continue
        syns = [c for c, _ in syn[aa] if c != codon]
        if len(syns) <= 1:
            continue  # 单同义位点
        positions.append((i, aa, codon, syn[aa]))
    n_mutate = max(1, round(len(positions) * density))
    rng = random.Random(seed)
    out = []
    seen = {cds}
    while len(out) < n and len(seen) < 1 + n * 10:
        seq_list = list(cds)
        for i, aa, orig, syns in rng.sample(positions, min(n_mutate, len(positions))):
            cands = [c for c, _ in syns if c != orig]
            seq_list[i:i + 3] = list(  # i 已是核苷酸索引(range(0, len-2, 3)); 勿再乘 3
                rng.choices(cands, weights=[f for c, f in syns if c != orig])[0])
        new = "".join(seq_list)
        if new in seen:
            continue
        seen.add(new)
        out.append(new)
    return out


def min_pairwise(cdss: list[str]) -> float:
    """两两归一化编辑距离最小值(等长逐位; 不等长退化为 1.0 保守)。"""
    best = 1.0
    for i in range(len(cdss)):
        for j in range(i + 1, len(cdss)):
            a, b = cdss[i], cdss[j]
            d = sum(1 for x, y in zip(a, b) if x != y) / len(a) if len(a) == len(b) else 1.0
            best = min(best, d)
    return best


def diversity_accept(new_cds: str, selected_cdss: list[str], cai: float,
                     local_ok: bool,
                     min_pairwise_threshold: float = DIVERSITY_MIN_PAIRWISE) -> bool:
    """生成时接受(组件 3): CAI ≥ CAI_MIN ∧ 本地约束零 fold 过 ∧ 与已选 pairwise ≥ 3%。"""
    if not local_ok or cai < m.CAI_MIN:
        return False
    if not selected_cdss:
        return True
    return min(min_pairwise([new_cds, s]) for s in selected_cdss) >= min_pairwise_threshold


# ---------------------------------------------------------------------------
# 拍板① D2 复合判据 + 格级声明(E14_gen_lattice)
# ---------------------------------------------------------------------------


def delivery_cai_span(cais: list[float]) -> float:
    """交付内 CAI 跨度(max − min); 空/单候选记 0.0。"""
    return (max(cais) - min(cais)) if len(cais) >= 2 else 0.0


def d2_composite(d1: bool, cais: list[float]) -> bool:
    """【拍板① 2026-08-09】D2 = 交付多样度复合判据 = D1 ∧ 交付内 CAI 跨度 ≥ 0.05。

    轴锁定交付下每画像交付集中偏好档(档数/跨度结构性不可达, P2 实证 D2 全 False);
    多样度由 D1(pairwise≥2%)+ 轴 CAI 梯度(0.85–1.0)承载 → 复合判据可构造满足;
    C 臂 λ 档覆盖改由格级声明(E14_gen_lattice: 格内 LD 档数 ≥3)承担。
    """
    return d1 and delivery_cai_span(cais) >= D2_CAI_SPAN_MIN


def lattice_gear_declaration(rank_map: dict[float, int]) -> dict:
    """E14_gen_lattice 格级声明: 格内 LD 档数(≥3 即档覆盖达标)。"""
    n_gears = len(rank_map)
    return {"n_ld_gears": n_gears, "ge_3": n_gears >= 3}


# ---------------------------------------------------------------------------
# 组件 4: 物种密码子上下文组件化(CodonContextResolver)
# ---------------------------------------------------------------------------


class CodonContextResolver:
    """组件 4: 表达宿主优先的密码子上下文(表/权重/同义位点 + 显式失败决议)。

    显式失败(计划 C5): 表缺失不再静默回退 human —— 构造时抛 KeyError,
    决议记录由 driver 写入档案(E15 字段)。薄封装 export_codon_usage_csv
    (sequence_utils.py:266-312 零改动), CSV 落盘带 context 哈希。
    """

    def __init__(self, species: str):
        self.species = species
        self.canonical = resolve_species_name(species)
        self._tables = _load_builtin_codon_tables()
        if self.canonical not in self._tables:
            raise KeyError(
                f"no builtin Kazusa table for species={species!r} "
                f"(resolved {self.canonical!r})")
        self.table = self._tables[self.canonical]
        self.weights = build_cai_weights(self.table)
        self.synonyms = aa_synonyms(self.table)

    # -- 决议记录(E15; host / host-based approximation 注记由 driver 按 target 合并) --
    def resolution(self) -> dict:
        return {
            "species": self.species,
            "canonical_table": self.canonical,
            "table_hit": True,
            "resolution": "host",
        }

    def codon_usage_csv(self, out_dir: Path) -> Path | None:
        """LD 格式 codon-usage CSV 路径(非 human 物种; context 哈希文件名)。

        Homo sapiens → None(LD 默认表, 与 r5 逐位一致); 其余物种导出
        <canonical>_<sha12>.csv —— 文件名含 CSV 内容哈希 → 同表同文件,
        LD 缓存键的 csv_hash 跨运行稳定。
        """
        if self.canonical == "Homo sapiens":
            return None
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.canonical.replace(' ', '_')}_ctxt.csv"
        export_codon_usage_csv(self.species, path)
        ctxt_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        final = out_dir / f"{self.canonical.replace(' ', '_')}_{ctxt_hash}.csv"
        if final != path:
            path.replace(final)
        return final
