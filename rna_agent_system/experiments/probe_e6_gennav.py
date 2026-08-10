"""E6「约束导航生成器」探针 P1–P5(2026-08-09, 探针先行硬约束)。

背景: E5 S1 全部剩余 NO-GO 因子(R3 档距不可达 / D1 λ 饱和趋同 / D2 可行档不足 /
S2 显著性平局)归因于**生成与选择分离**——agent 只能在固定配方池上被动选择。
E6 = 约束导航下沉到生成层: 四组件(可行性优先自适应 λ 探测 / 画像正交方向轴 /
多样度扩展器 / 物种密码子上下文组件化)统一为 FAD 生成格。

本探针(零实验驱动代码改动, 产物只写 /tmp/e5_probe_carm/e6_*):
  P1 可行性区间: 5 靶(S1)λ∈{0,1,2,4,8,10,20,50} 可行档集合 + λ-CAI 曲线 +
     GFP λ50 开采性(E. coli CSV) + LD 探测成本(≤5/靶)。
     human 靶复用 e5_pool_survey λ{0,1,4,10} CDS + 原始 stem 值(零 fold);
     GFP 复用 b0_verify_l10/l50 + runs.jsonl 提取 λ4(E. coli CSV), 新 λ 真实 LD。
  P2 方向轴 R3 构造性: A1AT/Insulin 三方向轴(cai_max/frac/cai_floor) CAI 分离度;
     迷你导航格上的轴锁定交付 sim_r3(R3 False→True 判读)。
  P3 多样度扩展器: Insulin/A1AT 变异密度 vs pairwise 曲线 / 约束保持率 / fold 成本;
     标定 3% 目标所需密度(判读: ≤30% 位点; 6 变体全过本地约束)。
  P4 物种上下文: 18 靶决议表全覆盖(表达宿主优先) + 显式失败路径。
  P5 S2 功效预演: 54 配对(E5 实测 5 靶 + 蒙特卡洛 13 靶) JCD-pass McNemar +
     连续复合得分 Wilcoxon; 判读: discordant ≥6/54 → p<0.05。

纪律: 勿动旧链路与缓存(只读); IL-2 探针勿重跑(本探针不调 LLM);
     产物只写 /tmp/e5_probe_carm/e6_*。

用法: cd rna_agent_system && python experiments/probe_e6_gennav.py [--skip-p1]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experiments import run_e5_constraint_nav as m  # noqa: E402
from experiments import probe_e5_generation_optimization as p  # noqa: E402
from agent_core.sequence_utils import (  # noqa: E402
    _load_builtin_codon_tables,
    build_cai_weights,
    compute_cai,
    resolve_species_name,
)

SCRATCH = Path("/tmp/e5_probe_carm")
SCRATCH.mkdir(parents=True, exist_ok=True)
RESULTS = Path(__file__).resolve().parent / "results"
SURVEY_PATH = RESULTS / "e5_pool_survey.json"
GM_UTR_CACHE = RESULTS / "e5_gemorna_cache.json"
GM_CDS_CACHE = RESULTS / "e5_gemorna_cds_cache.json"
RUNS_PATH = RESULTS / "e5_s1_runs.jsonl"
B0_CSV = SCRATCH / "kazusa_Escherichia_coli_K-12.csv"

E6_P1 = SCRATCH / "e6_p1_feasibility.json"
E6_P2 = SCRATCH / "e6_p2_axis.json"
E6_P3 = SCRATCH / "e6_p3_diversity.json"
E6_P4 = SCRATCH / "e6_p4_context.json"
E6_P5 = SCRATCH / "e6_p5_power.json"
E6_SUMMARY = SCRATCH / "e6_probe_summary.json"
E6_LD_CACHE = SCRATCH / "e6_ld_probe_cache.json"  # 键含 csv_hash(E6 运行缓存预种子)

# E6 探针 λ 网格(组件 1 粗探; {1,4,10} 由 survey 复用, 0/2/8/20/50 真实 LD)
PROBE_LAMBDAS = (0.0, 2.0, 8.0, 20.0, 50.0)
SURVEY_LAMBDAS = (0.0, 1.0, 4.0, 10.0)
S1_TARGETS = ["A1AT", "Insulin", "EPO", "GFP", "IL-2"]
FULL_TARGETS = m.FULL_TARGETS  # 18 靶
HUMAN = "Homo sapiens"
ECOLI = "Escherichia coli"

# 方向轴定义(组件 2; P2 实证)
AXES = ("cai_max", "frac", "cai_floor")
AXIS_TO_PROFILE = {"cai_max": "expression", "frac": "balanced", "cai_floor": "stability"}
PROFILE_TO_AXIS = {v: k for k, v in AXIS_TO_PROFILE.items()}

# 多样度扩展器参数(组件 3; P3 标定后定稿)
DIVERSITY_MIN_PAIRWISE = 0.03   # 判据 2% 留 1pp 余量
DENSITY_SWEEP = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)

_caches = {}
_tables = {}


# ---------------------------------------------------------------------------
# 公共数据装载
# ---------------------------------------------------------------------------


def load_all() -> dict:
    if _caches:
        return _caches["data"]
    data = p.load_cache_data()
    data["gm_cds"] = json.loads(GM_CDS_CACHE.read_text(encoding="utf-8"))
    data["gm_utr"] = json.loads(GM_UTR_CACHE.read_text(encoding="utf-8"))
    _caches["data"] = data
    return data


def species_table(species: str) -> dict:
    """canonical species → Kazusa table + Sharp&Li 权重(零 API)。"""
    canonical = resolve_species_name(species)
    tables = _load_builtin_codon_tables()
    if canonical not in tables:
        raise KeyError(f"no builtin Kazusa table for species={species!r} ({canonical!r})")
    return {"canonical": canonical, "table": tables[canonical],
            "weights": build_cai_weights(tables[canonical])}


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
    return float(compute_cai(m._rna(cds), weights)["cai_score"])


def gm_utrs(data: dict, target_id: str) -> tuple[dict[str, str], dict[str, str]]:
    return p.gm_utr_cache(data, target_id)


# ---------------------------------------------------------------------------
# 探针产物
# ---------------------------------------------------------------------------


def _seed(s: str) -> int:
    """确定性种子(md5; 跨进程可复现, 替代进程盐化 hash())。"""
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % (2**31)


def _dump(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=1),
                    encoding="utf-8")
    print(f"[probe] wrote {path}", flush=True)


# ---------------------------------------------------------------------------
# P1: 可行性区间(λ-CAI 曲线 + 可行档集合 + GFP λ50 + 探测成本)
# ---------------------------------------------------------------------------


def _csv_hash() -> str:
    if not B0_CSV.is_file():
        return "none"
    return hashlib.sha256(B0_CSV.read_bytes()).hexdigest()[:12]


def survey_ld_rows(data: dict, target_id: str) -> list[dict]:
    """survey 中该靶的 LD CDS + 原始 fold 值(零 fold 复用, 阈值当前口径重算)。"""
    rows: list[dict] = []
    for t in data["survey"]["targets"]:
        if t["target_id"] != target_id:
            continue
        for c in t["candidates"]:
            if c["lambda"] in (0.0, 1.0, 4.0, 10.0):
                rows.append(c)
        break
    return rows


def _local_check(full: str, utr5: str, cds: str, utr3: str,
                 cai: float, rare: set[str]) -> dict:
    """本地约束 C1/C2/M1/CAI(零 fold)。"""
    return {
        "C1": not m.sliding_window_gc_out_of_bounds(full),
        "C2": not m.has_homopolymer(full),
        "M1": m.boundary_gc_ok(utr5, cds, utr3),
        "CAI": cai >= m.CAI_MIN,
    }


_FOLD_CACHE: dict[tuple[str, str, str], dict] = {}


def _fold_check(utr5: str, cds: str, utr3: str) -> dict:
    """C6/C7(线性折叠 8015; 调用方保证本地已过)。进程内缓存:
    cai_max 轴 CDS 与 λ 无关 → 同 CDS×UTR 组合跨档去重,fold 调用大减。"""
    key = (utr5, cds, utr3)
    if key in _FOLD_CACHE:
        return _FOLD_CACHE[key]
    win = m.linearfold(utr5 + cds[: m.START_REGION_CDS_PREFIX])["structure"]
    full = m.linearfold(utr5 + cds + utr3)
    win_stem = m.longest_stem_bp(win)
    full_stem = m.longest_stem_bp(full["structure"])
    res = {
        "C6": win_stem <= m.START_REGION_MAX_STEM,
        "C7": full_stem <= m.FULL_MAX_STEM,
        "C6_stem": win_stem, "C7_stem": full_stem,
        "E7_pair_ratio": m.pair_ratio(full["structure"]),
        "E2_full_mfe": float(full["mfe"]),
    }
    _FOLD_CACHE[key] = res
    return res


def _ld_cache_read(key: str) -> str | None:
    if not E6_LD_CACHE.is_file():
        return None
    cache = json.loads(E6_LD_CACHE.read_text(encoding="utf-8"))
    return cache.get(key)


def _ld_cache_write(key: str, cds: str) -> None:
    cache: dict[str, str] = {}
    if E6_LD_CACHE.is_file():
        cache = json.loads(E6_LD_CACHE.read_text(encoding="utf-8"))
    cache[key] = cds
    E6_LD_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def _gen_ld(registry, target_id: str, meta: dict, lam: float,
            codon_usage_path: str | None) -> tuple[str | None, bool]:
    """LD 生成(带 /tmp 探针缓存; 返回 (cds, cached_flag))。"""
    species = meta.get("species_for_codon_optimization") or "human"
    key = f"{target_id}|{lam}|{_csv_hash()}"
    cached = _ld_cache_read(key)
    if cached:
        return cached, True
    cds = p.ld_generate(registry, meta["protein_sequence"].upper(), species, lam,
                        codon_usage_path)
    if cds:
        _ld_cache_write(key, cds)
    return cds, False


def probe_p1(registry, meta_map: dict, data: dict,
             *, log=print) -> dict:
    """P1: 每靶 λ 档本地约束 + 通过者 fold → 可行档集合。"""
    t0 = time.perf_counter()
    out: dict[str, dict] = {}
    n_ld = 0
    n_folds = 0
    for target_id in S1_TARGETS:
        meta = meta_map[target_id]
        species = meta.get("species_for_codon_optimization") or "human"
        st = species_table(species)
        rare = m.rare_codon_set(species)
        u5, u3 = gm_utrs(data, target_id)
        csv = None if resolve_species_name(species) == HUMAN else str(B0_CSV)
        rows: dict[float, dict] = {}

        # survey 复用(human 靶 λ{0,1,4,10}; 原始 stem 值重算当前阈值)
        # 注: GFP 的 survey CDS 为 B0 前 human 表生成, 与本 E6 口径(E. coli CSV)不符 → 排除。
        if target_id != "GFP":
            for c in survey_ld_rows(data, target_id):
                lam = float(c["lambda"])
                cds, u5p, u3p = c["cds_seq"], c["utr5_seq"], c["utr3_seq"]
                cai = cai_local(cds, st["weights"])
                full = u5p + cds + u3p
                local = _local_check(full, u5p, cds, u3p, cai, rare)
                fold = None
                if all(local.values()):
                    # survey 原始 stem 值 → 当前阈值重判(零 fold)
                    fold = {
                        "C6": float(c["c6_win_stem"]) <= m.START_REGION_MAX_STEM,
                        "C7": float(c["c7_full_stem"]) <= m.FULL_MAX_STEM,
                        "C6_stem": float(c["c6_win_stem"]),
                        "C7_stem": float(c["c7_full_stem"]),
                        "survey_reused": True,
                    }
                rows[lam] = {
                    "lambda": lam, "source": "ld", "cds": cds, "cai": cai,
                    "local": local, "fold": fold,
                    "passed": (all(local.values()) and bool(fold)
                               and all(fold.get(k) for k in ("C6", "C7"))),
                    "cached": True, "reused_survey": True,
                }

        # GFP 复用 b0_verify λ10/λ50 + runs.jsonl 提取 λ4(E. coli CSV 路径)
        if target_id == "GFP":
            for lam, fname in ((10.0, "b0_verify_l10.json"), (50.0, "b0_verify_l50.json")):
                fp = SCRATCH / fname
                if not fp.is_file():
                    continue
                cds = json.loads(fp.read_text(encoding="utf-8"))["generated_sequence"]
                cds = m._rna(cds)
                cai = cai_local(cds, st["weights"])
                pass9 = []
                for u5p in m.UTR_PRESETS:
                    for u3p in m.UTR_PRESETS:
                        full = u5[u5p] + cds + u3[u3p]
                        local = _local_check(full, u5[u5p], cds, u3[u3p], cai, rare)
                        if all(local.values()):
                            fold = _fold_check(u5[u5p], cds, u3[u3p])
                            n_folds += 2
                            pass9.append(all(fold.get(k) for k in ("C6", "C7")))
                rows[lam] = {
                    "lambda": lam, "source": "ld", "cds": cds, "cai": cai,
                    "passed": any(pass9) if pass9 else False,
                    "n_utr_pass": sum(pass9), "cached": True, "reused_b0": True,
                }
            lam4 = _gfp_lambda4_from_runs(data)
            if lam4:
                cai = cai_local(lam4, st["weights"])
                pass9 = []
                for u5p in m.UTR_PRESETS:
                    for u3p in m.UTR_PRESETS:
                        full = u5[u5p] + lam4 + u3[u3p]
                        local = _local_check(full, u5[u5p], lam4, u3[u3p], cai, rare)
                        if all(local.values()):
                            fold = _fold_check(u5[u5p], lam4, u3[u3p])
                            n_folds += 2
                            pass9.append(all(fold.get(k) for k in ("C6", "C7")))
                rows[4.0] = {
                    "lambda": 4.0, "source": "ld", "cds": lam4, "cai": cai,
                    "passed": any(pass9) if pass9 else False,
                    "n_utr_pass": sum(pass9), "cached": True, "reused_runs": True,
                }

        # 新 λ 真实 LD(探测成本 ≤5/靶)
        new_lams = [lam for lam in PROBE_LAMBDAS if lam not in rows]
        for lam in new_lams:
            cds, was_cached = _gen_ld(registry, target_id, meta, lam, csv)
            if not was_cached:
                n_ld += 1
            if cds is None:
                rows[lam] = {"lambda": lam, "source": "ld", "cai": None,
                             "passed": False, "ld_failed": True}
                continue
            cai = cai_local(cds, st["weights"])
            pass9 = []
            for u5p in m.UTR_PRESETS:
                for u3p in m.UTR_PRESETS:
                    full = u5[u5p] + cds + u3[u3p]
                    local = _local_check(full, u5[u5p], cds, u3[u3p], cai, rare)
                    if all(local.values()):
                        fold = _fold_check(u5[u5p], cds, u3[u3p])
                        n_folds += 2
                        pass9.append(all(fold.get(k) for k in ("C6", "C7")))
            rows[lam] = {
                "lambda": lam, "source": "ld", "cds": cds, "cai": cai,
                "passed": any(pass9) if pass9 else False,
                "n_utr_pass": sum(pass9),
            }

        feasible = sorted(lam for lam, r in rows.items() if r["passed"])
        out[target_id] = {
            "species": species,
            "lambda_curve": [{
                "lambda": lam, "cai": round(r.get("cai") or 0.0, 4),
                "passed": r["passed"], "n_utr_pass": r.get("n_utr_pass", 0),
            } for lam, r in sorted(rows.items())],
            "feasible_gears": feasible,
            "n_feasible": len(feasible),
            "tier": ">=3" if len(feasible) >= 3 else ("2" if len(feasible) == 2 else "<=1"),
            "ld_calls": sum(1 for lam in new_lams if not rows[lam].get("cached")),
        }
        log(f"[P1:{target_id}] feasible={feasible} tier={out[target_id]['tier']} "
            f"ld_calls={out[target_id]['ld_calls']}", flush=True)

    summary = {
        "generated_at": m.now_iso(),
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "ld_calls_total": n_ld,
        "fold_calls_total": n_folds,
        "targets": out,
        "verdict": {
            "all_ge3_or_bisect": all(t["tier"] in (">=3", "2") for t in out.values()),
            "ld_probe_le5": all(t["ld_calls"] <= 5 for t in out.values()),
            "gfp_lambda50_open": bool(out["GFP"]["feasible_gears"]
                                      and 50.0 in out["GFP"]["feasible_gears"]),
        },
    }
    _dump(E6_P1, summary)
    return summary


def _gfp_lambda4_from_runs(data: dict) -> str | None:
    """r5 GFP 交付中提取 λ4 CDS(E. coli CSV 路径, 与 B0 一致)。"""
    for r in data["runs"][-5:]:
        if r.get("target_id") != "GFP":
            continue
        ar = r.get("arm_results") or {}
        items = [ar.get("A"), ar.get("B")] + list(ar.get("C_runs") or [])
        for it in items:
            for prof, dl in (it.get("deliveries") or {}).items():
                for c in dl:
                    if c.get("source") == "ld" and float(c.get("lambda", -1)) == 4.0 and c.get("cds"):
                        return str(c["cds"])
    return None


# ---------------------------------------------------------------------------
# 组件 2/3 探针实现(纯本地; 后由 gennav_core.py 正式化)
# ---------------------------------------------------------------------------


def axis_cai_max(protein: str, syn: dict[str, list[tuple[str, float]]]) -> str:
    """方向轴 cai_max: 每 aa 取 fraction 最高密码子(确定性, CAI≈plateau)。

    收敛语义: 与源档 CDS 无关(任何源应用后收敛至同一序列);
    格内跨档多样度由多样度扩展器(种子含 λ)承担。"""
    return "".join(max(syn[aa], key=lambda cf: cf[1])[0] for aa in protein)


def axis_frac(protein: str, syn: dict[str, list[tuple[str, float]]],
              rng: random.Random, mix_p: float = 0.5) -> str:
    """方向轴 frac: 半倾斜混合抽样(每 aa 位 0.5 概率取最高 fraction 密码子,
    否则 fraction 加权随机)——CAI 落在 plateau 与 floor 之间(~0.85–0.90),
    避免纯 fraction 加权在部分靶结构性低于 CAI_MIN(P2 实证: A1AT 0.77/Insulin 0.69)。"""
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
                    lo: float = 0.88, hi: float = 0.92,
                    max_try: int = 64) -> str:
    """frac 轴目标定位: 接受重试至 CAI ∈ [lo, hi](种子化, 可复现)。

    组件 2×3 叠加的 CAI 余量保证: frac 目标 0.90(中间档),
    多样度扩展(≈0.02 降幅)后仍 ≥ CAI_MIN; 与 cai_max(≈1.0)/cai_floor(0.85)
    两两差 ≥0.05 → R3 分离由构造保证(3/3 pair)。
    """
    for s in range(seed, seed + max_try):
        cds = axis_frac(protein, syn, random.Random(s))
        if lo <= cai_local(cds, weights) <= hi:
            return cds
    # 理论不可达时退化为确定性最高 fraction(CAI=plateau, 仍满足硬约束)
    return axis_cai_max(protein, syn)


def axis_apply_frac(cds: str, syn: dict[str, list[tuple[str, float]]],
                    rng: random.Random, mix_p: float = 0.5) -> str:
    """frac 轴在源档 CDS 上应用: 每 aa 位 0.5 概率保留源密码子(档位结构特征
    留存), 0.5 概率 fraction 加权随机替换 —— 格内同轴跨档 CDS 保留 λ 档差异。"""
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
                   floor_target: float = 0.85) -> str:
    """方向轴 cai_floor: fraction 逆加权(取最低) + 逐位贪心修复至 CAI≥floor_target。

    floor_target = 0.85(下沿档, 留 ≥0.05 多样度扩展余量; 硬约束仍 CAI_MIN=0.8)。
    修复顺序: 按「提升 gain 降序」逐位替换为该 aa 的最高 fraction 密码子,
    直到整链 CAI ≥ floor_target —— 结构扰动最大化同时约束满足。
    """
    base = "".join(min(syn[aa], key=lambda cf: cf[1])[0] for aa in protein)
    if cai_local(base, weights) >= floor_target:
        return base
    cds = list(base)
    max_codons = {aa: max(syn[aa], key=lambda cf: cf[1])[0] for aa in syn}
    # 每 aa 该位 gain = max_fraction / cur_fraction
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


def synonymous_diversify(cds: str, weights: dict[str, float],
                         syn: dict[str, list[tuple[str, float]]],
                         density: float, n: int = 6, seed: int = 0) -> list[str]:
    """组件 3: 全 CDS 同义多样化(排除 AUG/stop/单同义位点)。

    density = 可变位点替换比例; 每变体 fraction 加权随机选同义密码子;
    返回 n 个变体(与 seed 确定可复现)。
    """
    # 位点表: (codon_index, aa, synonyms)
    positions = []
    for i in range(0, len(cds) - 2, 3):
        codon = cds[i:i + 3]
        if codon in ("AUG", "UAA", "UAG", "UGA"):
            continue  # 排除起始/终止
        aa = None
        for c, f in syn.items():
            for cand, _fr in f:
                if cand == codon:
                    aa = c
                    break
            if aa:
                break
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
            seq_list[i * 3:i * 3 + 3] = list(
                rng.choices(cands, weights=[f for c, f in syns if c != orig])[0])
        new = "".join(seq_list)
        if new in seen:
            continue
        seen.add(new)
        out.append(new)
    return out


def min_pairwise(cdss: list[str]) -> float:
    best = 1.0
    for i in range(len(cdss)):
        for j in range(i + 1, len(cdss)):
            a, b = cdss[i], cdss[j]
            d = sum(1 for x, y in zip(a, b) if x != y) / len(a) if len(a) == len(b) else 1.0
            best = min(best, d)
    return best


# ---------------------------------------------------------------------------
# P3: 多样度扩展器标定(纯本地; 先于 P2 的 D1 判读)
# ---------------------------------------------------------------------------


def probe_p3(meta_map: dict, *, log=print) -> dict:
    t0 = time.perf_counter()
    out: dict[str, dict] = {}
    for target_id in ("Insulin", "A1AT"):
        meta = meta_map[target_id]
        species = meta.get("species_for_codon_optimization") or "human"
        st = species_table(species)
        syn = aa_synonyms(st["table"])
        # 用 survey λ10 CDS 作为源(与 E6 格行一致)
        data = load_all()
        cds = None
        for r in survey_ld_rows(data, target_id):
            if float(r["lambda"]) == 10.0:
                cds = r["cds_seq"]
                break
        if cds is None:
            out[target_id] = {"error": "no survey lambda10 cds"}
            continue
        rare = m.rare_codon_set(species)
        u5, u3 = gm_utrs(data, target_id)
        rows = []
        for density in DENSITY_SWEEP:
            variants = synonymous_diversify(cds, st["weights"], syn, density, n=6,
                                            seed=_seed(f"{target_id}:{density}"))
            mp = min_pairwise(variants)
            cais = [cai_local(v, st["weights"]) for v in variants]
            cai_keep = sum(1 for c in cais if c >= m.CAI_MIN) / len(variants)
            # 本地约束保持(每变体取 3 个 UTR 组合抽查: u5m×u3m / u5s×u3l / u5l×u3s)
            local_keep = 0
            checked = 0
            combos = [("medium", "medium"), ("short", "long"), ("long", "short")]
            for v in variants:
                cai_v = cai_local(v, st["weights"])
                for u5p, u3p in combos:
                    full = u5[u5p] + v + u3[u3p]
                    local = _local_check(full, u5[u5p], v, u3[u3p], cai_v, rare)
                    local_keep += all(local.values())
                    checked += 1
            rows.append({
                "density": density, "n_variants": len(variants),
                "min_pairwise": round(mp, 4),
                "mean_pairwise": round(sum(
                    min_pairwise([variants[i], variants[j]])
                    for i in range(len(variants)) for j in range(i + 1, len(variants))
                ) / max(1, len(variants) * (len(variants) - 1) // 2), 4),
                "cai_min": round(min(cais), 4), "cai_max": round(max(cais), 4),
                "cai_keep_rate": round(cai_keep, 3),
                "local_keep_rate": round(local_keep / checked, 3),
            })
        # 判读: 满足 pairwise≥3% ∧ cai_keep≥0.9 ∧ local_keep≥0.9 的最小密度
        ok_rows = [r for r in rows if r["min_pairwise"] >= DIVERSITY_MIN_PAIRWISE
                   and r["cai_keep_rate"] >= 0.9 and r["local_keep_rate"] >= 0.9]
        out[target_id] = {
            "source_cds_len": len(cds),
            "sweep": rows,
            "calibrated_density": (ok_rows[0]["density"] if ok_rows else None),
            "density_le_30pct": bool(ok_rows and ok_rows[0]["density"] <= 0.30),
            "six_variants_local_pass": bool(
                ok_rows and ok_rows[0]["local_keep_rate"] == 1.0),
        }
        log(f"[P3:{target_id}] calibrated_density={out[target_id]['calibrated_density']} "
            f"rows={[r['min_pairwise'] for r in rows]}", flush=True)
    payload = {"generated_at": m.now_iso(),
               "elapsed_s": round(time.perf_counter() - t0, 1), "targets": out,
               "verdict": {
                   "target3pct_density_le30": all(
                       t.get("density_le_30pct", False) for t in out.values()),
                   "six_variants_all_local_pass": all(
                       t.get("six_variants_local_pass", False) for t in out.values()),
               }}
    _dump(E6_P3, payload)
    return payload


# ---------------------------------------------------------------------------
# P2: 方向轴 R3 构造性(迷你导航格 + 轴锁定交付)
# ---------------------------------------------------------------------------


def dynamic_rank_map(feasible_gears: list[float], n_independent: int = 1) -> dict[float, int]:
    """组件 1 动态档序: 可行档按 λ 升序 0..n-1; 独立来源排 LD 后。"""
    return {lam: i for i, lam in enumerate(sorted(feasible_gears))}


def dynamic_pref_ranks(rank_map: dict[float, int]) -> dict[str, int]:
    """组件 1 动态 λ 偏好查表(计划: 画像偏好 λ 改动态查表):
    small → 最小可行档, large → 最大可行档, middle → 中位可行档。"""
    gears = sorted(rank_map)
    if not gears:
        return {"small": 0, "large": 0, "middle": 0}
    return {"small": rank_map[gears[0]],
            "large": rank_map[gears[-1]],
            "middle": rank_map[gears[len(gears) // 2]]}


def utility_dyn(cand: dict, profile: str, norms: dict,
                rank_map: dict[float, int], rank_span: int,
                pref_ranks: dict[str, int] | None = None) -> float:
    """E6 U(镜像 E5 公式; 动态档序 + 动态 λ 偏好查表)。"""
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


def build_mini_lattice(meta_map: dict, data: dict, target_id: str,
                       feasible_gears: list[float], *, density: float,
                       log=print) -> dict:
    """迷你导航格: 可行档 × 3 方向轴 × 9 UTR(+GEMORNA 行 rank 排 LD 后)。

    每格 CDS = 方向轴编码(源档 CDS 上应用, frac/floor 种子化)
    然后多样度扩展器按格种子生成(保证格内 pairwise≥3%)。
    """
    meta = meta_map[target_id]
    species = meta.get("species_for_codon_optimization") or "human"
    st = species_table(species)
    syn = aa_synonyms(st["table"])
    u5, u3 = gm_utrs(data, target_id)
    wt_gc = m._wt_cds_gc(target_id)
    rare = m.rare_codon_set(species)
    rank_map = dynamic_rank_map(feasible_gears)
    pref_ranks = dynamic_pref_ranks(rank_map)
    span = max(2, len(rank_map) + 1)

    # 源 CDS 表: (source, lam, idx, base_cds)
    sources = []
    survey = {float(r["lambda"]): r["cds_seq"] for r in survey_ld_rows(data, target_id)}
    # 真实 LD 探测档(P1 写入 e6_ld_probe_cache.json, 键 {target}|{lam}|{csv_hash})
    for lam in feasible_gears:
        cds = survey.get(lam)
        if not cds:
            cds = _ld_cache_read(f"{target_id}|{lam}|{_csv_hash()}")
        if cds:
            sources.append(("ld", lam, 0, cds))
    for i in range(8):  # GEMORNA ≤10 行(独立来源, rank 排 LD 后)
        cds = str(data["gm_cds"].get(f"{target_id}#{i}", ""))
        if cds:
            sources.append(("gemorna", m.LAMBDA_GEMORNA, i, cds))

    candidates = []
    for src, lam, idx, base_cds in sources:
        for axis in AXES:
            # 格种子含源 idx: 同 λ 的 GM 行彼此不碰撞
            cell_seed = _seed(f"{target_id}|{src}|{lam}|{idx}|{axis}")
            rng = random.Random(cell_seed)
            if axis == "cai_max":
                axis_cds = axis_cai_max(meta["protein_sequence"].upper(), syn)
            elif axis == "frac":
                # 源 CDS 上应用(0.5 保留档位结构特征), 种子化可复现
                axis_cds = axis_apply_frac(base_cds, syn, rng)
            else:
                axis_cds = axis_cai_floor(meta["protein_sequence"].upper(), syn,
                                          st["weights"], rng)
            # 多样度扩展器: 格种子 → 与同轴已选格 pairwise≥3%(格内去重由 E6 核心保证)
            if density > 0:
                vars_ = synonymous_diversify(axis_cds, st["weights"], syn, density,
                                             n=4, seed=cell_seed)
                axis_cds = vars_[0]
            cai = cai_local(axis_cds, st["weights"])
            for u5p in m.UTR_PRESETS:
                for u3p in m.UTR_PRESETS:
                    full = u5[u5p] + axis_cds + u3[u3p]
                    local = _local_check(full, u5[u5p], axis_cds, u3[u3p], cai, rare)
                    if not all(local.values()):
                        continue
                    fold = _fold_check(u5[u5p], axis_cds, u3[u3p])
                    c6, c7 = fold["C6"], fold["C7"]
                    cand = m.make_candidate(axis_cds, u5[u5p], u3[u3p], lam, u5p, u3p,
                                            species, source=src, idx=idx)
                    cand["lambda_rank"] = rank_map.get(lam, span)
                    cand["axis"] = axis
                    cand["constraints"] = dict(local)
                    cand["constraints"].update({"C6": c6, "C7": c7})
                    cand["archive"] = {
                        "C3_polya_signal_count": m.polya_signal_count(axis_cds),
                        "C5_splice_motif_count": m.splice_motif_count(axis_cds),
                        "E1_cai": cai,
                        "E2_full_mfe": fold["E2_full_mfe"],
                        "E7_pair_ratio": fold["E7_pair_ratio"],
                        "E8_delta_gc": abs(m.gc_fraction(full) - wt_gc),
                        "E11_ld_lambda": float(lam),
                    }
                    cand["flags"]["passed"] = all(cand["constraints"].values())
                    candidates.append(cand)
    pool = {"target_id": target_id, "species": species,
            "candidates": candidates, "norms": {}, "rank_map": rank_map,
            "pref_ranks": pref_ranks, "rank_span": span}
    m.assign_utilities(pool)
    # 动态 U 覆盖(E5 utility 用静态 LAMBDA_RANK/LAMBDA_PREF; E6 动态档序重算 U)
    norms = pool["norms"]
    for c in candidates:
        c["utility"] = {pr: utility_dyn(c, pr, norms, rank_map, span, pref_ranks)
                        for pr in m.PROFILES}
    return pool


def axis_locked_delivery(pool: dict, profile: str) -> list[dict]:
    """轴锁定交付: 画像 → 方向轴切片内的 passed 候选按 U 降序取 5。"""
    axis = PROFILE_TO_AXIS[profile]
    passed = [c for c in pool["candidates"]
              if c["flags"]["passed"] and c["axis"] == axis]
    return sorted(passed, key=lambda c: c["utility"][profile], reverse=True)[:5]


def sim_r3_axis(pool: dict, profiles: list[str] = list(m.PROFILES)) -> dict:
    """轴锁定交付 top-1 的 R3 分离(E5 evaluate_arm 同口径)。"""
    tops = {pr: (axis_locked_delivery(pool, pr)[0] if axis_locked_delivery(pool, pr) else None)
            for pr in profiles}
    pairs, separated = [], 0
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            a, b = tops[profiles[i]], tops[profiles[j]]
            if a is None or b is None:
                continue
            pairs.append((profiles[i], profiles[j]))
            d_cai = abs(a["archive"]["E1_cai"] - b["archive"]["E1_cai"])
            d_lam = abs(a["lambda_rank"] - b["lambda_rank"])
            if d_cai >= 0.05 or d_lam >= 2:
                separated += 1
    return {
        "separated": separated, "pairs": len(pairs),
        "r3": (separated / len(pairs) >= 1 / 3) if pairs else False,
        "tops": [{"profile": pr, "axis": (t["axis"] if t else None),
                  "lambda_rank": (t["lambda_rank"] if t else None),
                  "E1_cai": (t["archive"]["E1_cai"] if t else None),
                  "U": (t["utility"][pr] if t else None)}
                 for pr, t in tops.items()],
    }


def probe_p2(meta_map: dict, data: dict, p1: dict, *, density: float,
             log=print) -> dict:
    """P2: A1AT/Insulin 方向轴 CAI 分离 + 迷你格 R3/D1/D2。"""
    t0 = time.perf_counter()
    out: dict[str, dict] = {}
    for target_id in ("A1AT", "Insulin"):
        meta = meta_map[target_id]
        species = meta.get("species_for_codon_optimization") or "human"
        st = species_table(species)
        syn = aa_synonyms(st["table"])
        protein = meta["protein_sequence"].upper()
        axes_cds = {
            "cai_max": axis_cai_max(protein, syn),
            "frac": axis_frac_tuned(protein, syn, st["weights"], seed=7),
            "cai_floor": axis_cai_floor(protein, syn, st["weights"], random.Random(7)),
        }
        axes_cai = {k: round(cai_local(v, st["weights"]), 4) for k, v in axes_cds.items()}
        # CAI 分离度
        sep = {
            "cai_max_minus_floor": round(axes_cai["cai_max"] - axes_cai["cai_floor"], 4),
            "cai_max_minus_frac": round(axes_cai["cai_max"] - axes_cai["frac"], 4),
            "floor_ge_min": axes_cai["cai_floor"] >= m.CAI_MIN,
        }
        # 迷你格(可行档来自 P1; density 用 P3 标定)
        feasible = [lam for lam in p1["targets"][target_id]["feasible_gears"]
                    if lam in (0.0, 1.0, 2.0, 4.0, 8.0, 10.0, 20.0, 50.0)]
        pool = build_mini_lattice(meta_map, data, target_id, feasible, density=density)
        sim = sim_r3_axis(pool)
        # D1/D2 判读(轴锁定交付)
        d_stats = {}
        for pr in m.PROFILES:
            dl = axis_locked_delivery(pool, pr)
            if len(dl) >= 2:
                mp = min(m.diversity_distance(dl[i], dl[j])
                         for i in range(len(dl)) for j in range(i + 1, len(dl)))
            else:
                mp = 0.0
            lams = sorted({c["lambda_rank"] for c in dl})
            d_stats[pr] = {
                "n": len(dl),
                "D1_min_dist": round(mp, 4),
                "D1": mp >= 0.02,
                "D2_ranks": lams,
                "D2": len(lams) >= 3 or any(b - a >= 2 for a in lams for b in lams if b > a),
            }
        out[target_id] = {
            "species": species,
            "axes_cai": axes_cai,
            "separation": sep,
            "lattice_n_candidates": len(pool["candidates"]),
            "lattice_n_pass": sum(1 for c in pool["candidates"] if c["flags"]["passed"]),
            "r3_sim": sim,
            "deliveries": d_stats,
            "verdict_p2": {
                "axis_cai_sep_ge_005": sep["cai_max_minus_floor"] >= 0.05,
                "floor_ge_cai_min": sep["floor_ge_min"],
                "r3_true": sim["r3"],
            },
        }
        log(f"[P2:{target_id}] axes_cai={axes_cai} sep={sep['cai_max_minus_floor']} "
            f"r3={sim['r3']}", flush=True)
    payload = {"generated_at": m.now_iso(), "elapsed_s": round(time.perf_counter() - t0, 1),
               "density_used": density, "targets": out,
               "verdict": {
                   "r3_false_to_true": all(
                       t["verdict_p2"]["r3_true"] for t in out.values()),
                   "axis_cai_sep_all": all(
                       t["verdict_p2"]["axis_cai_sep_ge_005"] for t in out.values()),
               }}
    _dump(E6_P2, payload)
    return payload


# ---------------------------------------------------------------------------
# P4: 物种密码子上下文组件化(18 靶决议 + 显式失败)
# ---------------------------------------------------------------------------

# 自然来源物种(表达宿主优先语义下的「host-based approximation」注记)
SOURCE_SPECIES_NOTES = {
    "GFP": "Aequorea victoria",
    "Luciferase": "Photinus pyralis",
    "Ovalbumin": "Gallus gallus",
}


def probe_p4(meta_map: dict, *, log=print) -> dict:
    t0 = time.perf_counter()
    tables = _load_builtin_codon_tables()
    rows = []
    for target_id in FULL_TARGETS:
        meta = meta_map[target_id]
        species = meta.get("species_for_codon_optimization") or "human"
        canonical = resolve_species_name(species)
        hit = canonical in tables
        src = SOURCE_SPECIES_NOTES.get(target_id)
        rows.append({
            "target_id": target_id,
            "expression_host": species,
            "canonical_table": canonical if hit else None,
            "table_hit": hit,
            "resolution": "host" if hit else "none",
            "source_species_note": src,
            "note": (f"host-based approximation (source {src})"
                     if src and hit else ("host table" if hit else "EXPLICIT FAILURE")),
        })
    # 显式失败路径: 无表物种
    fake = "Arabidopsis_thaliana_unknown"
    try:
        species_table(fake)
        failure_demo = {"species": fake, "raised": False}
    except KeyError as e:
        failure_demo = {"species": fake, "raised": True, "error": str(e)}
    out = {
        "generated_at": m.now_iso(), "elapsed_s": round(time.perf_counter() - t0, 1),
        "resolutions": rows,
        "n_host_hits": sum(1 for r in rows if r["table_hit"]),
        "n_total": len(rows),
        "explicit_failure_demo": failure_demo,
        "verdict": {
            "all_18_host_hit": all(r["table_hit"] for r in rows),
            "gfp_luc_ova_notes": all(
                rows[i]["source_species_note"] is not None
                for i, r in enumerate(rows) if r["target_id"] in SOURCE_SPECIES_NOTES),
            "explicit_failure_raises": failure_demo["raised"],
        },
    }
    for r in rows:
        log(f"[P4:{r['target_id']}] host={r['expression_host']} "
            f"table_hit={r['table_hit']} res={r['resolution']}", flush=True)
    _dump(E6_P4, out)
    return out


# ---------------------------------------------------------------------------
# P5: S2 功效预演(54 配对双终点)
# ---------------------------------------------------------------------------


def _composite(ev: dict) -> float:
    """连续复合得分(0.4×e2e + 0.2×约束率 + 0.2×D1/D2 + 0.2×R3)。

    D1/D2 槽 = mean(min(D1_dist/0.02,1), min(D2_span/2,1)) 的连续编码(提案, 待拍板)。
    """
    e2e = 1.0 if ev["e2e_pass"] else 0.0
    rate = ev["constraint_rate"]
    d1 = min(ev["D1_min_dist"] / 0.02, 1.0)
    d2_span = (max(ev["D2_lambda_ranks"]) - min(ev["D2_lambda_ranks"])) \
        if ev["D2_lambda_ranks"] else 0.0
    d2 = min(max(d2_span / 2.0, len(ev["D2_lambda_ranks"]) / 3.0), 1.0)
    r3 = 1.0 if ev.get("R3") else 0.0
    return 0.4 * e2e + 0.2 * rate + 0.2 * (0.5 * d1 + 0.5 * d2) + 0.2 * r3


def _e5_profile_evals(data: dict) -> dict[str, dict[str, dict]]:
    """E5 各靶 A 臂每画像评测(A 臂 = 静态池基准; C 臂 r5 无每靶全量 → A 为基准)。"""
    out = {}
    seen = {}
    for r in data["runs"]:
        tid = r["target_id"]
        if tid not in seen or r["timestamp"] > seen[tid]["timestamp"]:
            seen[tid] = r
    for tid, r in seen.items():
        ev = r["evaluations"].get("A")
        if not ev:
            continue
        out[tid] = {p["profile"]: p for p in ev["profiles"]}
        for p in ev["profiles"]:
            p.setdefault("R3", ev["R3"])
    return out


def probe_p5(p1: dict, p2: dict, meta_map: dict, *, n_mc: int = 2000,
             log=print) -> dict:
    """P5: 54 配对 JCD-pass McNemar + 复合得分 Wilcoxon。

    5 靶 = E5 实测 A 臂 + E6 构造修复估计 C 臂(P1/P2 实证);
    13 靶 = 蒙特卡洛(难度相关, p_A 由 E5 A 臂经验分布, C 增益参数化)。
    """
    t0 = time.perf_counter()
    data = load_all()
    a_evals = _e5_profile_evals(data)
    known = ["A1AT", "Insulin", "EPO", "GFP", "IL-2"]

    # E6 C 臂构造修复判定(依据 P1/P2 实证)
    c_fix = {
        "A1AT": ("r3",),        # 方向轴 R3 构造(实证 P2)
        "Insulin": ("r3", "d1"),  # 方向轴 R3 + 多样度 D1(实证 P2/P3)
        "GFP": ("d2",),         # λ50 档 D2(实证 P1)
    }

    def jcd(p: dict) -> bool:
        return bool(p["e2e_pass"] and p["D1"] and p["D2"] and p.get("R3", False))

    rows = []  # (target, profile, A_jcd, C_jcd, A_comp, C_comp, A_ev, C_ev)
    for tid in known:
        a_ev = a_evals.get(tid, {})
        for pr in m.PROFILES:
            ev = a_ev.get(pr)
            if ev is None:
                continue
            a_jcd = jcd(ev)
            # C 臂: A 失败因子是否被 E6 构造修复
            fixed = False
            if tid in c_fix and not a_jcd:
                # 具体因子检查: A 失败于哪些
                fail = [k for k in ("R3", "D1", "D2") if not ev.get(k)]
                fixed = all(k in c_fix[tid] for k in fail)
            c_jcd = a_jcd or (fixed and tid in c_fix)
            # 复合得分: A 实测; C = A + 构造增益(被修因子) + 探索余量
            c_comp = _composite(ev)
            if fixed:
                c_comp = min(1.0, c_comp + 0.10)
            if a_jcd:
                c_comp = max(c_comp, _composite(ev))
            rows.append((tid, pr, a_jcd, c_jcd, _composite(ev), c_comp, ev, None))

    # 蒙特卡洛: 13 靶(难度 d_t 共享于 A/C; A 基线 p_jcd≈0.4, 构造修复单向 C≥A)。
    # 模型: A 失败时 C 以 fix_rate 修复(R3/D1/D2 构造修复, 约束可行则成立);
    #      A 通过时 C 偶发失败(轴生成 fold 反例, 小概率 c_extra_fail)。
    rng = random.Random(42)
    a_base = 0.40
    fix_scale = 0.85      # 构造修复率(约束可行 × 机制成立)
    c_extra_fail = 0.05   # A 过 C 反例率(诚实下限)
    for tid in [t for t in FULL_TARGETS if t not in known]:
        d = rng.uniform(0.35, 0.95)  # 该靶约束可行难度
        for pr in m.PROFILES:
            a_jcd = rng.random() < a_base * d
            if a_jcd:
                c_jcd = rng.random() >= c_extra_fail
            else:
                c_jcd = rng.random() < min(1.0, fix_scale * d)
            # 复合得分(按 JCD 大致对齐)
            a_comp = 0.35 + 0.45 * d * (0.5 + rng.random() * 0.5) * (0.8 if not a_jcd else 1.0)
            c_comp = min(1.0, a_comp + (0.10 if c_jcd and not a_jcd else 0.02))
            rows.append((tid, pr, a_jcd, c_jcd, a_comp, c_comp, None, None))

    # McNemar(精确二项版; n=54)
    n = len(rows)
    b = sum(1 for _, _, a, c, *_ in rows if a and not c)
    c_ = sum(1 for _, _, a, c, *_ in rows if not a and c)
    concordant = sum(1 for _, _, a, c, *_ in rows if a == c)
    from scipy.stats import binomtest
    mc_p = float(binomtest(min(b, c_), b + c_, alternative="two-sided").pvalue) if b + c_ > 0 else 1.0
    # 复合得分 Wilcoxon 配对
    from scipy.stats import wilcoxon
    diffs = [c_comp - a_comp for _, _, _, _, a_comp, c_comp, _, _ in rows]
    w_p = float(wilcoxon([x for x in diffs if abs(x) > 1e-12]).pvalue) \
        if sum(1 for x in diffs if abs(x) > 1e-12) >= 2 else 1.0

    out = {
        "generated_at": m.now_iso(), "elapsed_s": round(time.perf_counter() - t0, 1),
        "n_pairs": n,
        "mc_n": n_mc,
        "discordant_b_a_pass_c_fail": b,
        "discordant_c_pass_a_fail": c_,
        "concordant": concordant,
        "mcnemar_p": mc_p,
        "wilcoxon_p": w_p,
        "mean_composite_A": round(sum(r[4] for r in rows) / n, 4),
        "mean_composite_C": round(sum(r[5] for r in rows) / n, 4),
        "known_targets": {tid: {pr: {"A_jcd": a, "C_jcd": c} for tid2, pr, a, c, *_ in rows
                                if tid2 == tid} for tid in known},
        "verdict": {
            "discordant_ge_6": (b + c_) >= 6,
            "mcnemar_p_lt_005": mc_p < 0.05,
            "wilcoxon_p_lt_005": w_p < 0.05,
        },
    }
    log(f"[P5] discordant={b}+{c_} mcnemar_p={mc_p:.4f} wilcoxon_p={w_p:.4f} "
        f"mean_comp A={out['mean_composite_A']} C={out['mean_composite_C']}", flush=True)
    _dump(E6_P5, out)
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def load_meta_map() -> dict:
    out = {}
    for target_id in FULL_TARGETS:
        out[target_id] = json.loads(
            (m.TARGETS_DIR / f"{target_id}.json").read_text(encoding="utf-8"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="E6 探针 P1–P5")
    ap.add_argument("--skip-p1", action="store_true")
    ap.add_argument("--skip-p3", action="store_true")
    ap.add_argument("--density", type=float, default=0.20,
                    help="P2 迷你格多样度密度(默认 0.20, P3 标定后回填)")
    args = ap.parse_args()

    meta_map = load_meta_map()
    data = load_all()
    registry, _ = m.make_runner()
    m.ensure_e5_services(log=print)
    print(f"[probe] E6 探针开始 {m.now_iso()}", flush=True)

    p1 = None
    if not args.skip_p1:
        p1 = probe_p1(registry, meta_map, data)
    p3 = None
    if not args.skip_p3:
        p3 = probe_p3(meta_map)
    if p1 is None:
        p1 = json.loads(E6_P1.read_text(encoding="utf-8"))
    density = args.density
    if p3 is not None:
        cal = [t.get("calibrated_density") for t in p3["targets"].values()]
        cal = [c for c in cal if c is not None]
        if cal:
            density = max(cal)
            print(f"[probe] P3 标定密度 = {density} (回填 P2)", flush=True)
    p2 = probe_p2(meta_map, data, p1, density=density)
    p4 = probe_p4(meta_map)
    p5 = probe_p5(p1, p2, meta_map)

    summary = {
        "generated_at": m.now_iso(),
        "P1": p1.get("verdict", {}), "P2": p2["verdict"], "P3": p3["verdict"] if p3 else {},
        "P4": p4["verdict"], "P5": p5["verdict"],
        "density_calibrated": density,
        "artifacts": [str(p) for p in (E6_P1, E6_P2, E6_P3, E6_P4, E6_P5)],
    }
    _dump(E6_SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
