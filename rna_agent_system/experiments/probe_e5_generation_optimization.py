"""E5 生成方法优化探针(2026-08-08): 高 λ LD 网格 + 采样密度 + B0 物种表 CSV 预演。

背景: S1 重跑(r4)整体 NO-GO(3/5)。失败全部在池/生成层:
  - GFP  0/315 空交付: E5 按 Kazusa E. coli 表计 CAI, LD 服务默认 human CSV 生成
    → λ→∞ 天花板 ≈0.70(结构性)。蛋白化学可达(Kazusa-max CAI=1.0)。
  - A1AT/Insulin R3 档距不可达: 通过约束的 LD 档位退化 {λ4(rank2), λ10(rank3)}
    (λ0 CAI<0.8、λ1 C7 长茎) → 档距≤1 <2。
  - Insulin D1=0.0082: 短蛋白 LD λ4 vs λ10 只差 4/330nt。
  - C1 GC 滑窗淘汰多数 GEMORNA 采样。

本探针(零代码改动, 产物只写 /tmp/e5_probe_carm/):
  1) 5 靶 × λ∈{20,50,100,200} 真实 LD 生成(8014), 全约束本地判定 + 8015 fold;
  2) 复算 r4 口径(sanity): 60/92/0/306/192(含 rnarl 重建), 不一致 = 探针 bug;
  3) GFP 天花板: λ 实测 vs LD表最优(Kazusa 计分) vs Kazusa-max;
  4) R3 可达性模拟(两口径: 序数重映射 / 并入 6 档; 标注模拟非判据);
  5) Insulin D1: 过约束 λ 档 CDS pairwise 距离 + λ 饱和诊断;
  6) gm 采样 C1 淘汰率(缓存统计, 零 API);
  7) B0: GFP + E. coli Kazusa CSV(codon_usage_path, 服务现有参数) 2 次 LD 预演。

用法: cd rna_agent_system && python experiments/probe_e5_generation_optimization.py
       [--targets A1AT,Insulin,EPO,GFP,IL-2] [--lambdas 20,50,100,200]
       [--no-kazusa-csv] [--no-sanity] [--dry-run]
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments import run_e5_constraint_nav as m  # noqa: E402
from agent_core.sequence_utils import (  # noqa: E402
    _load_builtin_codon_tables,
    build_cai_weights,
    compute_cai,
    resolve_species_name,
)

SCRATCH = Path("/tmp/e5_probe_carm")
SCRATCH.mkdir(parents=True, exist_ok=True)
OUT_JSON = SCRATCH / "e5_probe_genopt.json"
B0_CSV = SCRATCH / "kazusa_Escherichia_coli_K-12.csv"

RESULTS = Path(__file__).resolve().parent / "results"
SURVEY_PATH = RESULTS / "e5_pool_survey.json"
GM_CDS_CACHE = RESULTS / "e5_gemorna_cds_cache.json"
GM_UTR_CACHE = RESULTS / "e5_gemorna_cache.json"
RUNS_PATH = RESULTS / "e5_s1_runs.jsonl"

# r4 全池通过数(含 rnarl; 探针 sanity 基准)
R4_PASS = {"A1AT": 60, "Insulin": 92, "EPO": 306, "GFP": 0, "IL-2": 192}

_tables = {}          # -> {target: {...}}
_cache = {}           # 运行时缓存(folds / predictions)


def load_cache_data() -> dict:
    """一次性加载 survey / gemorna 缓存 / r4 runs(只读)。"""
    survey = json.loads(SURVEY_PATH.read_text(encoding="utf-8"))
    gm_cds = json.loads(GM_CDS_CACHE.read_text(encoding="utf-8"))
    gm_utr = json.loads(GM_UTR_CACHE.read_text(encoding="utf-8"))
    runs = []
    for line in RUNS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            runs.append(json.loads(line))
    return {"survey": survey, "gm_cds": gm_cds, "gm_utr": gm_utr, "runs": runs}


def survey_ld_cds(data: dict, target_id: str) -> dict[float, str]:
    """survey 中该靶的 LD CDS(与 r4 逐位一致): {lambda: cds}。"""
    out = {}
    for t in data["survey"]["targets"]:
        if t["target_id"] != target_id:
            continue
        for c in t["candidates"]:
            out.setdefault(float(c["lambda"]), c["cds_seq"])
        break
    return out


def gm_cds_list(data: dict, target_id: str, n: int = 30) -> list[str]:
    return [str(data["gm_cds"].get(f"{target_id}#{i}", "")) for i in range(n)]


def gm_utr_cache(data: dict, target_id: str) -> tuple[dict[str, str], dict[str, str]]:
    """该靶 9 条 UTR(5utr/3utr × preset)。"""
    u5, u3 = {}, {}
    for preset in m.UTR_PRESETS:
        u5[preset] = str(data["gm_utr"].get(f"{target_id}|5utr|{preset}", ""))
        u3[preset] = str(data["gm_utr"].get(f"{target_id}|3utr|{preset}", ""))
    return u5, u3


def rnarl_cds_from_r4(data: dict, target_id: str) -> str | None:
    """r4 交付档案中重建 rnarl CDS(1 CDS × 9 UTR; 未交付过则 None)。"""
    for r in data["runs"][-5:]:
        if r.get("target_id") != target_id:
            continue
        ar = r.get("arm_results") or {}
        items = [ar.get("A"), ar.get("B")] + list(ar.get("C_runs") or [])
        for it in items:
            for prof, dl in (it.get("deliveries") or {}).items():
                for c in dl:
                    if c.get("source") == "rnarl" and c.get("cds"):
                        return str(c["cds"])
    return None


def kazusa_weights(species: str) -> dict[str, float]:
    """E5 口径 CAI 权重(本地, 零 API): species → Kazusa 表 → Sharp&Li 权重。"""
    canonical = resolve_species_name(species)
    tables = _load_builtin_codon_tables()
    if canonical not in tables:
        raise KeyError(f"no builtin Kazusa table for species={species!r} ({canonical!r})")
    return build_cai_weights(tables[canonical])


def cai_local(cds: str, weights: dict[str, float]) -> float:
    return float(compute_cai(m._rna(cds), weights)["cai_score"])


def kazusa_csv_for_species(species: str, out_path: Path) -> Path:
    """导出 LD 格式 codon-usage CSV(fraction 0.0 → 1e-6 钳制, 防 ln(0))。
    LD 解析: `codon,aa,fraction` 三字段, stop 用 `*`(Utils/codon.h)。"""
    canonical = resolve_species_name(species)
    table = _load_builtin_codon_tables()[canonical]
    lines = ["#,,"]  # LD C++ 解析无条件跳过第一行(当 header), 缺 header 会少 1 密码子 → exit(1)
    for codon in sorted(table):
        info = table[codon]
        aa = info["aa"] if info["aa"] not in ("*", "") else "*"
        frac = max(float(info["fraction"]), 1e-6)
        lines.append(f"{codon},{aa},{frac:.8f}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def ld_generate(registry, protein: str, species: str, lam: float,
                codon_usage_path: str | None = None) -> str | None:
    """LD 8014 生成(与 build_pool L759-774 同路径); 失败返回 None。"""
    kwargs = dict(protein_sequence=protein, design_tool="lineardesign",
                  lambda_value=lam, cai_species=species,
                  run_fold=False, run_gc=False)
    if codon_usage_path:
        kwargs["lineardesign_codon_usage_path"] = codon_usage_path
    try:
        cds_wf = m.MrnaCdsDesignWorkflow(registry)
        cands = cds_wf.generate_candidates(m.MrnaCdsDesignInput(**kwargs))
        return m._rna(cands[0].sequence) if cands else None
    except Exception as e:  # noqa: BLE001
        print(f"    [warn] LD λ={lam} cds_path={bool(codon_usage_path)} failed: {e}", flush=True)
        return None


def fold_full(seq: str) -> dict:
    """全长 fold(8015): structure + mfe 一次调用。结果缓存。"""
    if seq not in _cache.setdefault("fold_full", {}):
        _cache["fold_full"][seq] = m.linearfold(seq)
    return _cache["fold_full"][seq]


def fold_window(utr5: str, cds: str) -> str:
    key = (utr5, cds)
    if key not in _cache.setdefault("fold_win", {}):
        win_seq = utr5 + cds[: m.START_REGION_CDS_PREFIX]
        _cache["fold_win"][key] = m.linearfold(win_seq)["structure"]
    return _cache["fold_win"][key]


def eval_local(full: str, utr5: str, cds: str, utr3: str,
               cai: float, wt_gc: float, rare: set[str], species: str) -> dict:
    """本地约束(C1/C2/M1/CAI) + 档案里无需 fold 的部分。"""
    c1 = not m.sliding_window_gc_out_of_bounds(full)
    c2 = not m.has_homopolymer(full)
    m1 = m.boundary_gc_ok(utr5, cds, utr3)
    cai_ok = cai >= m.CAI_MIN
    local = {"C1": c1, "C2": c2, "M1": m1, "CAI": cai_ok}
    arch = {
        "C3_polya_signal_count": m.polya_signal_count(cds),
        "C4_restriction_hits": m.restriction_site_hits(full),
        "C5_splice_motif_count": m.splice_motif_count(cds),
        "C8_uAUG_count": utr5.count("AUG"),
        "E1_cai": cai,
        "E6_rare_codons": m.rare_codon_count(cds, species, rare),
        "E8_delta_gc": abs(m.gc_fraction(full) - wt_gc),
        "E9_are_count": m.are_count(utr3),
        "E10_kozak": m.kozak_score(utr5, cds),
        "full_gc": m.gc_fraction(full),
    }
    return {"local": local, "arch": arch}


def make_mini_pool(data: dict, target_id: str, meta: dict, registry,
                   new_lams: list[float],
                   rank_map: dict[float, int], rank_span: int,
                   *, include_gm: bool = True, include_rn: bool = True,
                   gen_new: bool = True) -> dict:
    """候选 = (survey 4 λ + 新 λ + [rnarl] + [gm 30]) × 9 UTR。
    rank_map/rank_span 注入 R3 模拟口径。先本地约束, 只 fold 本地通过者。"""
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    weights = kazusa_weights(species)
    rare = m.rare_codon_set(species)
    wt_gc = m._wt_cds_gc(target_id)
    u5, u3 = gm_utr_cache(data, target_id)

    cds_items = []  # (source, lambda, idx, cds)
    for lam, cds in sorted(survey_ld_cds(data, target_id).items()):
        cds_items.append(("ld", lam, 0, cds))
    if gen_new:
        for lam in new_lams:
            cds = ld_generate(registry, protein, species, lam)
            if cds:
                cds_items.append(("ld", lam, 0, cds))
            else:
                print(f"    [warn] {target_id} LD λ={lam} produced no CDS", flush=True)
    rn = rnarl_cds_from_r4(data, target_id) if include_rn else None
    if rn:
        cds_items.append(("rnarl", m.LAMBDA_RNARL, 0, rn))
    if include_gm:
        for i, cds in enumerate(gm_cds_list(data, target_id)):
            cds_items.append(("gemorna", m.LAMBDA_GEMORNA, i, cds))

    # E4/E5: GEMORNA predict 每 preset 一次(评分调用, 非生成)
    mrl = {p: m.gemorna_predict_mrl(u5[p]) for p in m.UTR_PRESETS}
    stab = {p: m.gemorna_predict_stability(u3[p]) for p in m.UTR_PRESETS}

    candidates = []
    for source, lam, idx, cds_seq in cds_items:
        cai = cai_local(cds_seq, weights)
        for u5p in m.UTR_PRESETS:
            for u3p in m.UTR_PRESETS:
                cand = m.make_candidate(cds_seq, u5[u5p], u3[u3p], lam, u5p, u3p, species,
                                        source=source, idx=idx)
                cand["lambda_rank"] = rank_map.get(lam, rank_map.get(m.LAMBDA_GEMORNA, 0))
                full = cand["sequence"]
                local_res = eval_local(full, cand["utr5"], cds_seq, cand["utr3"],
                                       cai, wt_gc, rare, species)
                cand["constraints"] = dict(local_res["local"])
                cand["archive"] = dict(local_res["arch"])
                if all(cand["constraints"].values()):
                    win_struct = fold_window(cand["utr5"], cds_seq)
                    full_fold = fold_full(full)
                    full_struct = full_fold["structure"]
                    c6 = m.longest_stem_bp(win_struct) <= m.START_REGION_MAX_STEM
                    c7 = m.longest_stem_bp(full_struct) <= m.FULL_MAX_STEM
                    cand["constraints"]["C6"] = c6
                    cand["constraints"]["C7"] = c7
                    cds_struct = full_struct[len(cand["utr5"]): len(cand["utr5"]) + len(cds_seq)]
                    cand["archive"].update({
                        "E2_full_mfe": float(full_fold["mfe"]),
                        "E4_utr5_mrl": mrl[u5p],
                        "E5_utr3_stability": stab[u3p],
                        "E7_pair_ratio": m.pair_ratio(full_struct),
                        "E11_ld_lambda": float(lam),
                        "C6_start_open": m.unpaired_fraction(win_struct),
                        "C7_longest_stem": m.longest_stem_bp(full_struct),
                        "CDS_unpaired": m.unpaired_fraction(cds_struct),
                    })
                else:
                    # 本地失败: fold 依赖字段置 None(pool_normalizers 跳过)
                    cand["constraints"]["C6"] = False
                    cand["constraints"]["C7"] = False
                    cand["archive"].update({
                        "E2_full_mfe": None, "E4_utr5_mrl": mrl[u5p],
                        "E5_utr3_stability": stab[u3p], "E7_pair_ratio": None,
                        "E11_ld_lambda": float(lam),
                        "C6_start_open": None, "C7_longest_stem": None,
                        "CDS_unpaired": None,
                    })
                cand["flags"]["passed"] = all(cand["constraints"].values())
                cand["flags"]["no_constraint_solution"] = not cand["flags"]["passed"]
                cand["full_structure"] = None
                candidates.append(cand)

    pool = {"target_id": target_id, "species": species, "protein": protein,
            "candidates": candidates}
    m.assign_utilities(pool)
    return pool


def sim_r3(pool: dict, profiles: list[str] = list(m.PROFILES)) -> dict:
    """模拟 3 画像 A 臂 top-1 的 R3 分离(与 evaluate_arm L1172-1187 同口径)。"""
    deliveries = {p: m._default_delivery(pool, p) for p in profiles}
    tops = [deliveries[p][0] if deliveries[p] else None for p in profiles]
    pairs, separated = [], 0
    for i in range(len(tops)):
        for j in range(i + 1, len(tops)):
            if tops[i] is None or tops[j] is None:
                continue
            pairs.append((profiles[i], profiles[j]))
            d_cai = abs(tops[i]["archive"]["E1_cai"] - tops[j]["archive"]["E1_cai"])
            d_lam = abs(tops[i]["lambda_rank"] - tops[j]["lambda_rank"])
            if d_cai >= 0.05 or d_lam >= 2:
                separated += 1
    return {
        "separated": separated, "pairs": len(pairs),
        "r3": (separated / len(pairs) >= 1 / 3) if pairs else False,
        "tops": [{"profile": p, "id": (t["id"] if t else None),
                  "lambda": (t["lambda"] if t else None),
                  "lambda_rank": (t["lambda_rank"] if t else None),
                  "E1_cai": (t["archive"]["E1_cai"] if t else None),
                  "U": (t["utility"][p] if t else None)} for p, t in zip(profiles, tops)],
    }


# ── 表 1: λ × 约束 ─────────────────────────────────────────────────────────────


def table1(pool: dict, meta: dict, r4_n_pass: int, sanity_ok: bool,
           new_lams: list[float]) -> dict:
    rows = []
    by_lam: dict[float, list] = {}
    for c in pool["candidates"]:
        by_lam.setdefault(c["lambda"], []).append(c)
    for lam in sorted(by_lam):
        cs = by_lam[lam]
        n_local = sum(1 for c in cs if all(c["constraints"][k] for k in ("C1", "C2", "M1", "CAI")))
        n_pass = sum(1 for c in cs if c["flags"]["passed"])
        cais = [c["archive"]["E1_cai"] for c in cs]
        src = {c["source"] for c in cs}
        rows.append({
            "lambda": lam, "n_cands": len(cs),
            "passing_utr_combos": n_pass, "local_pass": n_local,
            "cai_min": min(cais), "cai_max": max(cais),
            "sources": sorted(src),
        })
    return {
        "table1_lambda_constraints": rows,
        "n_pass_all": sum(1 for c in pool["candidates"] if c["flags"]["passed"]),
        "r4_n_pass": r4_n_pass, "sanity_ok": sanity_ok,
        "new_lambdas": new_lams,
    }


# ── 表 2: GFP 天花板 ──────────────────────────────────────────────────────────


def table2_gfp_ceiling(data: dict, pool: dict, meta: dict) -> dict:
    """LD 表最优 vs Kazusa 表最优 vs λ 实测(全部本地计算)。"""
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    wt = kazusa_weights(species)                     # E5 计分表
    ld_csv = Path(__file__).resolve().parent.parent / "external_repos" / "LinearDesign" / "codon_usage_freq_table_human.csv"
    ld_weights: dict[str, float] = {}
    aa_of: dict[str, str] = {}
    if ld_csv.is_file():
        for line in ld_csv.read_text(encoding="utf-8-sig").splitlines():
            parts = line.strip().split(",")
            if (len(parts) == 3 and len(parts[0]) == 3
                    and set(parts[0]) <= set("ACGTU")):
                codon = parts[0].upper().replace("T", "U")
                ld_weights[codon] = float(parts[2])
                aa_of[codon] = parts[1]
    # LD 表最优序列(按氨基酸取 LD 表 fraction 最大密码子)
    aa2codons: dict[str, list[tuple[str, float]]] = {}
    for codon, aa in aa_of.items():
        aa2codons.setdefault(aa, []).append((codon, ld_weights[codon]))
    ld_max = "".join(
        max(aa2codons.get(aa, [("UUU", 1e-9)]), key=lambda kv: kv[1])[0]
        for aa in protein
    )
    # Kazusa 表最优序列
    tables = _load_builtin_codon_tables()
    ec = tables[resolve_species_name(species)]
    kz_groups: dict[str, list[tuple[str, float]]] = {}
    for codon, info in ec.items():
        kz_groups.setdefault(info["aa"], []).append((codon, float(info["fraction"])))
    kz_max = "".join(
        max(kz_groups.get(aa, [("UUU", 1e-9)]), key=lambda kv: kv[1])[0]
        for aa in protein
    )
    measured = {str(c["lambda"]): c["archive"]["E1_cai"]
                for c in pool["candidates"] if c["source"] == "ld"}
    return {
        "table2_gfp_ceiling": {
            "measured_by_lambda": {k: round(v, 4) for k, v in sorted(measured.items())},
            "ld_table_max_scored_by_kazusa": round(cai_local(ld_max, wt), 4),
            "kazusa_max_scored_by_kazusa": round(cai_local(kz_max, wt), 4),
            "kazusa_max_gc": round(m.gc_fraction(kz_max), 4),
            "note": "λ→∞ 上界 ≈ LD表最优按计分表计分; 若 < CAI_MIN, 推高 λ 无法达 0.8",
        },
    }


# ── 表 4: D1 距离(过约束 λ 档 CDS) ────────────────────────────────────────────


def table4_d1(pool: dict) -> dict:
    lds = {}
    for c in pool["candidates"]:
        if c["source"] == "ld" and c["flags"]["passed"]:
            lds.setdefault(c["lambda"], c["cds"])
    lams = sorted(lds)
    dists = {}
    for i in range(len(lams)):
        for j in range(i + 1, len(lams)):
            a, b = lds[lams[i]], lds[lams[j]]
            if len(a) != len(b):
                dists[f"{lams[i]}v{lams[j]}"] = None
                continue
            n_diff = sum(1 for x, y in zip(a, b) if x != y)
            dists[f"{lams[i]}v{lams[j]}"] = round(n_diff / len(a), 4)
    return {"table4_d1_pairwise": dists, "lambda_set": lams}


# ── 表 5: gm C1 淘汰率 ────────────────────────────────────────────────────────


def table5_gm_c1(data: dict, target_id: str, meta: dict) -> dict:
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    u5, u3 = gm_utr_cache(data, target_id)
    wt = kazusa_weights(species)
    rare = m.rare_codon_set(species)
    wt_gc = m._wt_cds_gc(target_id)
    n_all9_killed = 0
    per_source = []
    for i, cds in enumerate(gm_cds_list(data, target_id)):
        cai = cai_local(cds, wt)
        n_c1_pass = 0
        for p in m.UTR_PRESETS:
            for q in m.UTR_PRESETS:
                full = u5[p] + cds + u3[q]
                if not m.sliding_window_gc_out_of_bounds(full):
                    n_c1_pass += 1
        killed = n_c1_pass == 0
        if killed:
            n_all9_killed += 1
        per_source.append({"idx": i, "cai": round(cai, 4), "n_c1_pass": n_c1_pass})
    return {"table5_gm_c1": {"n_all9_killed": n_all9_killed, "total": 30,
                             "per_source": per_source}}


# ── 表 6: B0 GFP + E.coli CSV ─────────────────────────────────────────────────


def table6_b0(registry, meta: dict, lam_list: list[float]) -> dict:
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    csv_path = kazusa_csv_for_species(species, B0_CSV)
    wt = kazusa_weights(species)
    rows = []
    for lam in lam_list:
        cds = ld_generate(registry, protein, species, lam, codon_usage_path=str(csv_path))
        if not cds:
            rows.append({"lambda": lam, "cds": None})
            continue
        cai = cai_local(cds, wt)
        gc = m.gc_fraction(cds)
        c1_ok = not m.sliding_window_gc_out_of_bounds(cds)
        rows.append({"lambda": lam, "cds_len": len(cds), "cai": round(cai, 4),
                     "gc": round(gc, 4), "cds_c1_ok": c1_ok})
    return {"table6_b0_kazusa_csv": {"csv": str(csv_path), "rows": rows}}


# ── main ──────────────────────────────────────────────────────────────────────


def run_target(target_id: str, args, data, registry) -> dict:
    meta = json.loads((m.TARGETS_DIR / f"{target_id}.json").read_text(encoding="utf-8"))
    species = meta.get("species_for_codon_optimization") or "human"
    print(f"\n{'='*78}\n=== {target_id} (species={species}, {meta['protein_length_aa']}aa) ===", flush=True)

    t0 = time.perf_counter()
    # 口径 (i): 序数重映射(新 λ 排 4..7, gm=8, rn=9)
    rank_i = {0: 0, 1: 1, 4: 2, 10: 3}
    rank_i.update({float(lam): i for i, lam in enumerate(args.lambdas, start=4)})
    rank_i[m.LAMBDA_GEMORNA] = 8
    rank_i[m.LAMBDA_RNARL] = 9
    # 口径 (ii): 并入既有 6 档(新 λ 同 λ10 → rank 3)
    rank_ii = dict(rank_i)
    for lam in args.lambdas:
        rank_ii[float(lam)] = 3

    pool_i = make_mini_pool(data, target_id, meta, registry, args.lambdas,
                            rank_map=rank_i, rank_span=9,
                            include_gm=True, include_rn=True, gen_new=True)
    n_pass_i = sum(1 for c in pool_i["candidates"] if c["flags"]["passed"])
    n_cands_i = len(pool_i["candidates"])
    # sanity: r4 基准是全池通过数(含 gemorna/rnarl 档); 剔除新 λ 档(20/50/100/200)
    r4_lams = {0.0, 1.0, 4.0, 10.0, m.LAMBDA_GEMORNA, m.LAMBDA_RNARL}
    n_pass_legacy = sum(1 for c in pool_i["candidates"]
                        if c["flags"]["passed"] and c["lambda"] in r4_lams)
    r4_n = R4_PASS.get(target_id)
    # 注意: 探针池含 rnarl(重建) + gm, 与 r4 完全同构成
    # (r4 无新 λ; 无 rn 重建的靶 Insulin/GFP 的 rn 在 r4 贡献 0 通过)
    sanity_ok = n_pass_legacy == r4_n
    print(f"  pool: {n_cands_i} candidates, n_pass={n_pass_i} (legacy-only {n_pass_legacy}, "
          f"r4={r4_n}) | {time.perf_counter()-t0:.0f}s", flush=True)
    print(f"  SANITY: {'OK' if sanity_ok else 'MISMATCH!!'} (legacy {n_pass_legacy} vs r4 {r4_n})", flush=True)

    tbl = {"sanity_ok": sanity_ok, "n_pass": n_pass_i, "n_cands": n_cands_i,
           "n_pass_legacy": n_pass_legacy, "r4_n_pass": r4_n,
           "elapsed_s": round(time.perf_counter() - t0, 1)}

    # 表 1
    t1 = table1(pool_i, meta, r4_n, sanity_ok, args.lambdas)
    tbl.update(t1)
    for row in t1["table1_lambda_constraints"]:
        print(f"  λ={row['lambda']:<6} pass={row['passing_utr_combos']}/9 "
              f"local={row['local_pass']} CAI[{row['cai_min']:.3f},{row['cai_max']:.3f}] "
              f"src={row['sources']}", flush=True)

    # 表 2(GFP)/ 表 4(D1)/ 表 5(gm)
    if target_id == "GFP":
        t2 = table2_gfp_ceiling(data, pool_i, meta)
        tbl.update(t2)
        print(f"  GFP ceiling: {json.dumps(t2['table2_gfp_ceiling'], ensure_ascii=False)}", flush=True)
    t4 = table4_d1(pool_i)
    tbl.update(t4)
    print(f"  D1 pairwise (passing LD CDS): {t4['table4_d1_pairwise']} λset={t4['lambda_set']}", flush=True)
    t5 = table5_gm_c1(data, target_id, meta)
    tbl.update(t5)
    print(f"  gm C1 all-9-killed: {t5['table5_gm_c1']['n_all9_killed']}/30", flush=True)

    # 表 3: R3 模拟(两口径; 重建候选以应用不同 rank 映射)
    # 注: _lambda_pref_comp/utility 读模块级 LAMBDA_RANK_SPAN, 模拟前 patch, 用后恢复。
    sims = {}
    for name, rank_map, span in (("rank_i_renumbered", rank_i, 9),
                                 ("rank_ii_merged6", rank_ii, 5)):
        old_span = m.LAMBDA_RANK_SPAN
        m.LAMBDA_RANK_SPAN = span
        try:
            pool_s = make_mini_pool(data, target_id, meta, registry, args.lambdas,
                                    rank_map=rank_map, rank_span=span,
                                    include_gm=True, include_rn=True, gen_new=False)
            sim = sim_r3(pool_s)
        finally:
            m.LAMBDA_RANK_SPAN = old_span
        sims[name] = sim

        def _fmt_top(t: dict | None) -> str:
            if t is None:
                return "None(空交付)"
            cai = f"{t['E1_cai']:.3f}" if t["E1_cai"] is not None else "None"
            return f"{t['profile']}:{t['id']}(λ={t['lambda']},r={t['lambda_rank']},CAI={cai})"

        tops = "; ".join(_fmt_top(t) for t in sim["tops"])
        print(f"  R3 sim[{name}]: {sim['separated']}/{sim['pairs']} separated → "
              f"R3={'PASS' if sim['r3'] else 'fail'} | {tops}", flush=True)
    tbl["table3_r3_sim"] = sims

    # 表 6: B0(GFP + E.coli CSV)
    if target_id == "GFP" and not args.no_kazusa_csv:
        t6 = table6_b0(registry, meta, [10.0, 50.0])
        tbl.update(t6)
        print(f"  B0: {json.dumps(t6['table6_b0_kazusa_csv'], ensure_ascii=False)}", flush=True)

    return tbl


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="A1AT,Insulin,EPO,GFP,IL-2")
    ap.add_argument("--lambdas", default="20,50,100,200")
    ap.add_argument("--no-kazusa-csv", action="store_true", help="跳过 GFP B0 维度")
    ap.add_argument("--no-sanity", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="只打印矩阵, 不调服务")
    args = ap.parse_args()
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    args.lambdas = [float(x) for x in args.lambdas.split(",") if x.strip()]

    if args.dry_run:
        print("DRY-RUN matrix:")
        for t in targets:
            print(f"  {t}: survey λ 0/1/4/10 + new {args.lambdas} + rn(重建/缺省) + gm30 "
                  f"× 9 UTR; LD {1 + len(args.lambdas)} 新调用/靶 "
                  f"({len(args.lambdas)} 新 λ) + fold(本地过者)")
        return

    registry, _executor = m.make_runner()
    data = load_cache_data()
    print(f"services: LD 8014 / LinearFold 8015 preflight ...", flush=True)
    for target_id in targets:
        try:
            _tables[target_id] = run_target(target_id, args, data, registry)
        except Exception as e:  # noqa: BLE001 - 逐靶失败不崩全盘
            print(f"[ERROR] {target_id}: {e}", flush=True)
            _tables[target_id] = {"error": str(e)}

    OUT_JSON.write_text(json.dumps(_tables, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nDONE -> {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()
