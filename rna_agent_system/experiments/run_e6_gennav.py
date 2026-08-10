#!/usr/bin/env python3
"""E6 PRE-REGISTRATION (判据书 v8, user-approved 2026-08-09) — constraint-navigation
GENERATOR for full-length mRNA design: 约束导航从"选择层"下沉到"生成层"。

背景链: E5 S1(r4/r5)整体 NO-GO → 全部剩余失败因子归因至生成方法层结构性:
  R3 偏好 λ 档 0-pass → 档距 1<2 结构性不可达;
  D1 λ 饱和趋同(Insulin 0.0082); D2 可行档仅 2; S2 显著性三臂共享池平局(p=1.0)。
共同根源 = 生成与选择分离 → E6 四组件统一 FAD 生成格(GenerationLattice):
  C1 可行性优先自适应生成(动态档序/取档计划/动态 U)
  C2 画像正交方向轴(cai_max / frac / cai_floor; 拍板②标定)
  C3 多样度扩展器(生成时 pairwise≥3%; D1 构造保证)
  C4 物种密码子上下文(CodonContextResolver; 显式失败)
方法学命题(拟 Nature Methods): 可行性探测/画像主轴/多样度阈值/物种上下文
同时编码进生成目标 —— R3/D1/D2 由构造保证, S2 显著性由质量差分承载。

三臂分层池(拍板 C1):
  A 臂: 规则交付作用于**静态配方池**(λ{0,1,4,10}×9UTR, B0 同 r5)
  B 臂: 无门控 LLM 作用于静态池(2–4 次/基因, request_generate ≤1)
  C 臂: 门控约束导航作用于**导航生成格**(5–9 次/基因, request_generate ≤2)

判据书 v8(拍板记录 2026-08-09, 见 HANDOFF_2026-08-09_E6_PROBED_PENDING.md):
  ① D2 修订(拍板①, 选项 A): D2 = 交付多样度复合判据 = D1 ∧ 交付内 CAI 跨度 ≥ 0.05;
     C 臂 λ 档覆盖改由 E14_gen_lattice 格级声明(格内 LD 档数 ≥ 3)。
  ② frac/floor 轴标定(拍板②): frac = 半倾斜混合 + 接受重试 [0.88, 0.92];
     floor 目标 0.85(硬约束 CAI_MIN 0.8 与分离阈值 0.05 不变)。
  ③ R3 轴内语义(拍板③): top-1 按轴锁定交付取, 分离由构造保证。
  S1 六项: ①e2e C≥0.8 且 C≥A 平局算过 ②约束率 C≥0.9 ③R1–R4(R3 注记 E13_gen_axis)
           ④D1–D3(D2 复合判据; E14_gen_lattice 格级声明)⑤方向性 C≥A 4/5 ⑥预算记录
  S2 双终点(拍板 C2): 主 = per-profile JCD-pass(e2e∧D1∧D2∧R3)配对 McNemar(n=54)
    + c_e2e_gene ≥0.8; 辅 = 连续复合得分(0.4×e2e+0.2×约束率+0.2×D1/D2+0.2×R3)
    配对 Wilcoxon + 质量判据(R1–R4/D1–D3/约束率 ≥0.9)。

复用(import 零复制, 旧链路零改动): run_e5_constraint_nav 约束判定/档案/U;
probe_e5_generation_optimization 探针方法论; gennav_core 组件 1–4 纯函数。

纪律: git 操作先问用户; 判据/阈值/处置变更须拍板 + 同步 PREREG §20 与
MODEL_API_USAGE §2; 勿动旧链路(run_e5_constraint_nav / codon_tables /
sequence_utils / mrna_cds_design / lineardesign_service); 探针产物与缓存
只读(/tmp/e5_probe_carm/e6_* 是 E6 运行缓存种子); 本驱动产物写
experiments/results/e6_*。

Usage (from ``rna_agent_system/``):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e6_gennav.py s0 \\
        --targets Insulin --repeat 3 --output experiments/results/e6_s0_runs.jsonl
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e6_gennav.py s1 \\
        --targets A1AT,Insulin,EPO,GFP,IL-2 --output experiments/results/e6_s1_runs.jsonl
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e6_gennav.py s2 \\
        --output experiments/results/e6_s2_runs.jsonl
判定书: experiments/results/e6_verdict_<stage>.json; 记录 append JSONL。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scipy import stats as scipy_stats  # noqa: E402

from experiments import run_e5_constraint_nav as m  # noqa: E402
from agent_core.calibrated.audit_trail import AuditTrail  # noqa: E402
from agent_core.calibrated.decision_gate import DecisionGate  # noqa: E402
from agent_core.calibrated.models import PlannedAction  # noqa: E402
from agent_core.calibrated.self_model import SelfModel  # noqa: E402
from agent_core.generation.gennav_core import (  # noqa: E402
    AXES,
    CAI_FLOOR_TARGET,
    DIVERSITY_DENSITY,
    DIVERSITY_N_VARIANTS,
    PROBE_LAMBDAS,
    PROFILE_TO_AXIS,
    SOURCE_SPECIES_NOTES,
    STATIC_LAMBDAS,
    CodonContextResolver,
    assign_utilities_dyn,
    axis_apply_frac,
    axis_cai_floor,
    axis_cai_max,
    cai_local,
    d2_composite,
    delivery_cai_span,
    dynamic_pref_ranks,
    dynamic_rank_map,
    gear_selection_plan,
    lattice_gear_declaration,
    synonymous_diversify,
    _seed,
)
from agent_core.llm_config import get_deepseek_llm  # noqa: E402
from agent_core.sequence_utils import export_codon_usage_csv  # noqa: E402
from agent_core.workflows.mrna_cds_design import (  # noqa: E402
    MrnaCdsDesignInput,
    MrnaCdsDesignWorkflow,
)

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------

RESULTS_DIR = m.RESULTS_DIR
TARGETS_DIR = m.TARGETS_DIR
E6_LD_CACHE_PATH = RESULTS_DIR / "e6_ld_cds_cache.json"        # 键 {target}|{lam}|{csv_hash}
E6_GM_CDS_CACHE_PATH = RESULTS_DIR / "e6_gemorna_cds_cache.json"
E6_GM_CDS_SRC = RESULTS_DIR / "e5_gemorna_cds_cache.json"      # 种子源(只读)
GM_UTR_CACHE_PATH = RESULTS_DIR / "e5_gemorna_cache.json"      # UTR 复用(只读)
SURVEY_PATH = RESULTS_DIR / "e5_pool_survey.json"
RUNS_PATH = RESULTS_DIR / "e5_s1_runs.jsonl"
PROBE_LD_CACHE = Path("/tmp/e5_probe_carm/e6_ld_probe_cache.json")  # 探针缓存种子
B0_VERIFY_DIR = Path("/tmp/e5_probe_carm")
CODON_TABLE_OUT = RESULTS_DIR / "codon_tables_e6"

S1_TARGETS = ["A1AT", "Insulin", "EPO", "GFP", "IL-2"]
HUMAN = "Homo sapiens"
ECOLI_SPECIES = "E. coli"
GEMORNA_LATTICE_ROWS = 8          # 独立来源行(排 LD 后; 缓存零新调用)
LATTICE_CAND_TABLE_CAP = 250      # LLM 观察表行数上限(确定性截断)

# 预算(§: LD 探测 5/靶 + 二分 1 + request_generate C≤2/B≤1; LD 总 C≤3/基因)
B_LLM_MIN, B_LLM_MAX = 2, 4
C_LLM_MIN, C_LLM_MAX = 5, 9
C_MAX_REPAIR_ROUNDS = 2
MAX_EXTRA_LINEARDESIGN = 1        # B 臂 lineardesign ≤1 且 request_generate ≤1(共享档)
C_MAX_REQUEST_GENERATE = 2        # C 臂 request_generate ≤2
C_MAX_LD_TOTAL = 3                # C 臂 LD 总(二分 + λ 请求)≤3/基因
REQUEST_DIVERSITY_MIN, REQUEST_DIVERSITY_MAX = 0.02, 0.25

S0_TIME_BUDGET_S = 40 * 60
S1_TIME_BUDGET_S = 3 * 3600
S2_TIME_BUDGET_S = 6 * 3600

# 缓存键口径(与探针一致): 后缀 = E. coli CSV 内容 hash, 跨靶统一 —— 探针
# _csv_hash() 对全部靶用同一 B0 CSV hash(人类靶 human 表生成, 键后缀不变)。
# 键语义 = "该靶实际生成口径下的 CDS"(复现锚点: 键 = {target}|{lam}|{suffix})。
PROBE_CSV_HASH = "26308b892d84"

_FOLD_CACHE: dict[tuple[str, str, str], dict] = {}

# ---------------------------------------------------------------------------
# 缓存装载/种子
# ---------------------------------------------------------------------------


def _cache_suffix() -> str:
    """缓存键后缀(探针口径统一 E. coli CSV hash; seed 时验证字节一致)。"""
    return PROBE_CSV_HASH


def _verify_probe_csv_hash(log: Any = print) -> None:
    """验证 E. coli CSV 导出字节与探针 B0 CSV 一致(键跨进程稳定前提)。"""
    path = CODON_TABLE_OUT / "Escherichia_coli_K-12_ctxt.csv"
    try:
        export_codon_usage_csv(ECOLI_SPECIES, path)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        if actual == PROBE_CSV_HASH:
            log(f"[seed] E. coli CSV hash {actual} == probe {PROBE_CSV_HASH} (键口径一致)")
        else:
            log(f"[warn] E. coli CSV hash {actual} != probe {PROBE_CSV_HASH}: "
                f"探针缓存键将 miss(自动降级为新生成; 请核查字节级格式差异)")
    except KeyError as e:
        log(f"[warn] E. coli table 不可导出: {e}")


def _csv_hash(path: Path | None) -> str:
    if path is None or not Path(path).is_file():
        return "none"
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def _load_json(path: Path, default=None):
    if not Path(path).is_file():
        return default
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")


def _ld_cache_read(key: str) -> str | None:
    return (_load_json(E6_LD_CACHE_PATH) or {}).get(key)


def _ld_cache_write(key: str, cds: str) -> None:
    cache = _load_json(E6_LD_CACHE_PATH) or {}
    cache[key] = cds
    _save_json(E6_LD_CACHE_PATH, cache)


def seed_e6_caches(log: Any = print) -> None:
    """复现锚点种子: 探针 LD 缓存 + GFP b0_verify/runs 提取 + e5 GEMORNA CDS 缓存。

    探针产物(勿删): /tmp/e5_probe_carm/e6_ld_probe_cache.json(20 键)是 E6
    运行缓存种子; GFP λ4/λ10/λ50 从 b0_verify JSON 与 e5_s1_runs.jsonl 提取
    (E. coli CSV 口径, 与探针 P1 一致)。键后缀 = _cache_suffix()(探针口径)。
    幂等: 已存在键不覆盖。
    """
    _verify_probe_csv_hash(log=log)
    ld = _load_json(E6_LD_CACHE_PATH) or {}
    probe = _load_json(PROBE_LD_CACHE) or {}
    added = 0
    for k, v in probe.items():
        if k not in ld:
            ld[k] = str(v)
            added += 1
    # GFP λ10/λ50(b0_verify; E. coli CSV 口径)
    for lam, fname in ((10.0, "b0_verify_l10.json"), (50.0, "b0_verify_l50.json")):
        fp = B0_VERIFY_DIR / fname
        if not fp.is_file():
            continue
        cds = _load_json(fp, {}).get("generated_sequence", "")
        if cds:
            key = f"GFP|{lam}|{_cache_suffix()}"
            if key not in ld:
                ld[key] = m._rna(str(cds))
                added += 1
    # GFP λ4(r5 交付提取; E. coli CSV 口径)
    lam4 = _gfp_lambda4_from_runs()
    if lam4:
        key = f"GFP|4.0|{_cache_suffix()}"
        if key not in ld:
            ld[key] = m._rna(lam4)
            added += 1
    if ld:
        _save_json(E6_LD_CACHE_PATH, ld)
    # GEMORNA CDS 缓存(e6 工作缓存 ← e5 种子; 零新调用)
    gm = _load_json(E6_GM_CDS_CACHE_PATH) or {}
    src = _load_json(E6_GM_CDS_SRC) or {}
    for k, v in src.items():
        gm.setdefault(k, v)
    if gm:
        _save_json(E6_GM_CDS_CACHE_PATH, gm)
    log(f"[seed] e6_ld_cds_cache: {len(ld)} keys ({added} new from probe/b0/runs); "
        f"e6_gemorna_cds_cache: {len(gm)} keys")


def _gfp_lambda4_from_runs() -> str | None:
    """r5 GFP 交付中提取 λ4 CDS(E. coli CSV 路径, 与 B0 一致)。"""
    runs_path = Path(RUNS_PATH)
    if not runs_path.is_file():
        return None
    runs = []
    with runs_path.open(encoding="utf-8") as fh:  # JSONL(逐行 JSON)
        for line in fh:
            line = line.strip()
            if line:
                runs.append(json.loads(line))
    for r in runs[-5:]:
        if r.get("target_id") != "GFP":
            continue
        ar = r.get("arm_results") or {}
        items = [ar.get("A"), ar.get("B")] + list(ar.get("C_runs") or [])
        for it in items:
            for prof, dl in (it.get("deliveries") or {}).items():
                for c in dl:
                    if c.get("source") == "ld" and float(c.get("lambda", -1)) == 4.0 \
                            and c.get("cds"):
                        return str(c["cds"])
    return None


# ---------------------------------------------------------------------------
# 序列/约束(复用 m 纯函数; 分层判定: 本地零 fold 过滤 → 通过者才 fold)
# ---------------------------------------------------------------------------


def _local_check(full: str, utr5: str, cds: str, utr3: str,
                 cai: float, rare: set[str]) -> dict:
    """本地约束 C1/C2/M1/CAI(零 fold; 组件 1 分层判定第一层)。"""
    return {
        "C1": not m.sliding_window_gc_out_of_bounds(full),
        "C2": not m.has_homopolymer(full),
        "M1": m.boundary_gc_ok(utr5, cds, utr3),
        "CAI": cai >= m.CAI_MIN,
    }


def _fold_check(utr5: str, cds: str, utr3: str) -> dict:
    """C6/C7(线性折叠 8015; 调用方保证本地已过)。进程内缓存。"""
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
        "C6_start_open": m.unpaired_fraction(win),
        "E7_pair_ratio": m.pair_ratio(full["structure"]),
        "E2_full_mfe": float(full["mfe"]),
    }
    _FOLD_CACHE[key] = res
    return res


def _ld_generate(registry, protein: str, species: str, lam: float,
                 csv_path: str | None) -> str | None:
    """LD 8014 生成(与 build_pool/探针同路径); 失败返回 None。"""
    kwargs = dict(protein_sequence=protein, design_tool="lineardesign",
                  lambda_value=lam, cai_species=species,
                  run_fold=False, run_gc=False)
    if csv_path:
        kwargs["lineardesign_codon_usage_path"] = csv_path
    try:
        cds_wf = MrnaCdsDesignWorkflow(registry)
        cands = cds_wf.generate_candidates(MrnaCdsDesignInput(**kwargs))
        return m._rna(cands[0].sequence) if cands else None
    except Exception as e:  # noqa: BLE001 - 单 λ 失败不阻断
        print(f"    [warn] LD λ={lam} csv={bool(csv_path)} failed: {e}", flush=True)
        return None


def cds_for_lambda(target_id: str, meta: dict, registry, lam: float,
                   csv_path: str | None, data: dict,
                   count_ld: list[int] | None = None) -> str | None:
    """CDS 获取(缓存优先): e6_ld_cds_cache → survey(human 靶) → LD 生成(落缓存)。

    键后缀 = _cache_suffix()(探针口径 E. coli CSV hash, 跨靶统一 —— 探针瑕疵
    保持一致 = 复现锚点); survey CDS 仅对 human 靶有效(B0 前 human 表生成;
    非 human 靶口径不符, 探针 P1 排除)。count_ld 非空则统计真实 LD 调用数。"""
    key = f"{target_id}|{lam}|{_cache_suffix()}"
    cached = _ld_cache_read(key)
    if cached:
        return cached
    if csv_path is None and data is not None:
        for t in (data.get("survey") or {}).get("targets", []):
            if t["target_id"] != target_id:
                continue
            for c in t["candidates"]:
                if float(c["lambda"]) == lam and c.get("cds_seq"):
                    return str(c["cds_seq"])
            break
    if count_ld is not None:
        count_ld[0] += 1
    protein = meta["protein_sequence"].upper()
    species = meta.get("species_for_codon_optimization") or "human"
    cds = _ld_generate(registry, protein, species, lam, csv_path)
    if cds:
        _ld_cache_write(key, cds)
    return cds


# ---------------------------------------------------------------------------
# 组件 1 驱动: 可行性优先 λ 探测(P1 口径)
# ---------------------------------------------------------------------------


def probe_feasibility(target_id: str, meta: dict, registry, data: dict,
                      ctx: CodonContextResolver, *, log: Any = print) -> dict:
    """每靶 λ∈{PROBE_LAMBDAS ∪ survey λ{0,1,4,10}} 本地 + fold → 可行档集合。

    分层判定(组件 1): 本地约束(C1/C2/M1/CAI)零 fold 过滤 → 通过者才 fold C6/C7。
    可行 = 任一 UTR 组合全约束过。返回 lambda_curve + feasible_gears + ld_calls。"""
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    weights = ctx.weights
    rare = m.rare_codon_set(species)
    u5, u3 = _gm_utr_cache(data, target_id)
    csv = ctx.codon_usage_csv(CODON_TABLE_OUT)
    n_ld = [0]
    rows: dict[float, dict] = {}
    lams = sorted(set(PROBE_LAMBDAS) | set(STATIC_LAMBDAS))
    for lam in lams:
        cds = cds_for_lambda(target_id, meta, registry, lam, csv, data,
                             count_ld=n_ld)
        if cds is None:
            rows[lam] = {"lambda": lam, "cai": None, "passed": False, "ld_failed": True}
            continue
        cai = cai_local(cds, weights)
        pass9 = []
        for u5p in m.UTR_PRESETS:
            for u3p in m.UTR_PRESETS:
                full = u5[u5p] + cds + u3[u3p]
                local = _local_check(full, u5[u5p], cds, u3[u3p], cai, rare)
                if all(local.values()):
                    fold = _fold_check(u5[u5p], cds, u3[u3p])
                    pass9.append(all(fold.get(k) for k in ("C6", "C7")))
        rows[lam] = {"lambda": lam, "cai": round(cai, 4),
                     "passed": any(pass9) if pass9 else False,
                     "n_utr_pass": sum(pass9)}
    feasible = sorted(lam for lam, r in rows.items() if r["passed"])
    out = {
        "target_id": target_id, "species": species,
        "lambda_curve": [{"lambda": lam, "cai": r.get("cai"), "passed": r["passed"],
                          "n_utr_pass": r.get("n_utr_pass", 0)}
                         for lam, r in sorted(rows.items())],
        "feasible_gears": feasible,
        "n_feasible": len(feasible),
        "ld_calls": n_ld[0],
        "plan": gear_selection_plan(feasible),
    }
    log(f"[probe:{target_id}] feasible={feasible} tier={len(feasible)} "
        f"ld_calls={n_ld[0]} plan_mode={out['plan']['mode']}", flush=True)
    return out


def _lambda_feasible(target_id: str, cds: str, u5: dict, u3: dict,
                     weights: dict, rare: set[str]) -> bool:
    """λ 档可行性: 任一 UTR 组合全约束过(组件 1 分层判定)。"""
    cai = cai_local(cds, weights)
    for u5p in m.UTR_PRESETS:
        for u3p in m.UTR_PRESETS:
            full = u5[u5p] + cds + u3[u3p]
            local = _local_check(full, u5[u5p], cds, u3[u3p], cai, rare)
            if all(local.values()):
                fold = _fold_check(u5[u5p], cds, u3[u3p])
                if all(fold.get(k) for k in ("C6", "C7")):
                    return True
    return False


def _gm_utr_cache(data: dict, target_id: str) -> tuple[dict[str, str], dict[str, str]]:
    u5, u3 = {}, {}
    for preset in m.UTR_PRESETS:
        u5[preset] = str((data.get("gm_utr") or {}).get(f"{target_id}|5utr|{preset}", ""))
        u3[preset] = str((data.get("gm_utr") or {}).get(f"{target_id}|3utr|{preset}", ""))
    return u5, u3


def _gm_cds_rows(target_id: str, n: int = GEMORNA_LATTICE_ROWS) -> list[tuple[int, str]]:
    gm = _load_json(E6_GM_CDS_CACHE_PATH) or {}
    return [(i, str(gm[f"{target_id}#{i}"])) for i in range(n)
            if gm.get(f"{target_id}#{i}")]


# ---------------------------------------------------------------------------
# 静态配方池(A/B 臂; λ{0,1,4,10}×9UTR = 36 候选, B0 同 r5)
# ---------------------------------------------------------------------------


def build_static_pool(target_id: str, meta: dict, registry, data: dict,
                      ctx: CodonContextResolver, *, log: Any = print) -> dict:
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    csv = ctx.codon_usage_csv(CODON_TABLE_OUT)
    u5, u3 = _gm_utr_cache(data, target_id)
    weights = ctx.weights
    rare = m.rare_codon_set(species)
    wt_gc = m._wt_cds_gc(target_id)
    t0 = time.perf_counter()

    cds_items: list[tuple[str, float, int, str]] = []
    for lam in STATIC_LAMBDAS:
        cds = cds_for_lambda(target_id, meta, registry, lam, csv, data)
        if cds:
            cds_items.append(("ld", lam, 0, cds))
    if not cds_items:
        raise RuntimeError(f"static pool generation failed: no CDS for {target_id}")

    # 池级: CAI 缓存 + GEMORNA UTR 预测(每唯一 UTR 一次)
    cai_cache = {cds: cai_local(cds, weights) for _, _, _, cds in cds_items}
    mrl_cache = {p: m.gemorna_predict_mrl(u5[p]) for p in m.UTR_PRESETS}
    stab_cache = {p: m.gemorna_predict_stability(u3[p]) for p in m.UTR_PRESETS}

    candidates = []
    for source, lam, idx, cds_seq in cds_items:
        for u5p in m.UTR_PRESETS:
            for u3p in m.UTR_PRESETS:
                cand = m.make_candidate(cds_seq, u5[u5p], u3[u3p], lam, u5p, u3p,
                                        species, source=source, idx=idx)
                _evaluate_candidate(cand, cds_seq, u5[u5p], u3[u3p], cai_cache[cds_seq],
                                    mrl_cache, stab_cache, wt_gc, rare, species)
                candidates.append(cand)
    pool = {"target_id": target_id, "species": species, "protein": protein,
            "cds_by_lambda": {lam: cds for _, lam, _, cds in cds_items},
            "utr5_cache": u5, "utr3_cache": u3, "cai_cache": cai_cache,
            "mrl_cache": mrl_cache, "stab_cache": stab_cache,
            "wt_cds_gc": wt_gc, "candidates": candidates, "registry": registry,
            "generation_seconds": time.perf_counter() - t0,
            "pool_kind": "static"}
    m.assign_utilities(pool)
    n_pass = sum(1 for c in candidates if c["flags"]["passed"])
    log(f"  [static:{target_id}] {len(candidates)} candidates, {n_pass} pass, "
        f"{pool['generation_seconds']:.0f}s", flush=True)
    return pool


def _evaluate_candidate(cand: dict, cds_seq: str, utr5: str, utr3: str,
                        cai: float, mrl_cache: dict, stab_cache: dict,
                        wt_gc: float, rare: set[str], species: str) -> None:
    """单候选全量评估(约束 + 档案; 池内复用)。"""
    full = cand["sequence"]
    local = _local_check(full, utr5, cds_seq, utr3, cai, rare)
    fold = _fold_check(utr5, cds_seq, utr3)
    cand["constraints"] = {**local, "C6": fold["C6"], "C7": fold["C7"]}
    cand["flags"]["passed"] = all(cand["constraints"].values())
    cand["flags"]["no_constraint_solution"] = not cand["flags"]["passed"]
    cds_struct = None  # 复用 E5 档案; CDS 结构段由调用方按需补(见 _full_struct)
    cand["archive"] = {
        "C3_polya_signal_count": m.polya_signal_count(cds_seq),
        "C4_restriction_hits": m.restriction_site_hits(full),
        "C5_splice_motif_count": m.splice_motif_count(cds_seq),
        "C8_uAUG_count": utr5.count("AUG"),
        "E1_cai": cai,
        "E2_full_mfe": fold["E2_full_mfe"],
        "E3_junction_mfe_per_nt": None,
        "E4_utr5_mrl": mrl_cache[cand["utr5_preset"]],
        "E5_utr3_stability": stab_cache[cand["utr3_preset"]],
        "E6_rare_codons": m.rare_codon_count(cds_seq, species, rare),
        "E7_pair_ratio": fold["E7_pair_ratio"],
        "E8_delta_gc": abs(m.gc_fraction(full) - wt_gc),
        "E9_are_count": m.are_count(utr3),
        "E10_kozak": m.kozak_score(utr5, cds_seq),
        "E11_ld_lambda": float(cand["lambda"]),
        "E11_utility_lambda": None,
        "E12_motivation": "",
        "C6_start_open": fold["C6_start_open"],
        "C7_longest_stem": fold["C7_stem"],
        "CDS_unpaired": 0.0,
        "full_gc": m.gc_fraction(full),
        "E13_gen_axis": None,
        "E14_gen_lattice": None,
    }
    cand["full_structure"] = None


def _full_struct_archive(cand: dict) -> None:
    """补 CDS_unpaired(需要全长 structure; 池级少调用路径用)。"""
    if cand.get("full_structure"):
        utr5, cds_seq = cand["utr5"], cand["cds"]
        struct = cand["full_structure"]
        cds_struct = struct[len(utr5): len(utr5) + len(cds_seq)]
        cand["archive"]["CDS_unpaired"] = m.unpaired_fraction(cds_struct)


# ---------------------------------------------------------------------------
# 导航生成格(C 臂; 可行档 × 3 方向轴 × 9 UTR + 独立来源行)
# ---------------------------------------------------------------------------


def build_lattice(target_id: str, meta: dict, registry, data: dict,
                  ctx: CodonContextResolver, feas: dict,
                  *, density: float = DIVERSITY_DENSITY,
                  log: Any = print) -> dict:
    """C 臂导航生成格: 行 = 可行 λ 档 ∪ 独立来源行(GM ≤8, 排 LD 后),
    列 = 三方向轴, × 9 UTR。每格 CDS = 方向轴编码 + 多样度扩展器(格种子)。

    轴种子含源 idx(同 λ 的 GM 行彼此不碰撞, P2 修复 3); frac 轴在源 CDS 上
    应用(0.5 保留档位结构特征)。lattice_plan 快照入池(复现锚点)。"""
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    weights = ctx.weights
    syn = ctx.synonyms
    u5, u3 = _gm_utr_cache(data, target_id)
    rare = m.rare_codon_set(species)
    wt_gc = m._wt_cds_gc(target_id)
    csv = ctx.codon_usage_csv(CODON_TABLE_OUT)
    t0 = time.perf_counter()

    plan = feas["plan"]
    gears = plan["gears"]
    if plan["mode"] == "bisect" and plan["bisect_lambda"] is not None:
        mid = plan["bisect_lambda"]
        cds = cds_for_lambda(target_id, meta, registry, mid, csv, data)
        if cds and _lambda_feasible(target_id, cds, u5, u3, weights, rare):
            gears = sorted(set(gears) | {mid})
            feas = dict(feas)
            feas["feasible_gears"] = sorted(feas["feasible_gears"] + [mid])
            plan = {"gears": gears, "mode": "bisect_ok", "bisect_lambda": mid}
    rank_map = dynamic_rank_map(gears)
    pref_ranks = dynamic_pref_ranks(rank_map)
    span = max(2, len(rank_map) + 1)

    # 源 CDS 表: (source, lam, idx, base_cds)
    sources = []
    for lam in gears:
        cds = cds_for_lambda(target_id, meta, registry, lam, csv, data)
        if cds:
            sources.append(("ld", lam, 0, cds))
    for i, cds in _gm_cds_rows(target_id):
        sources.append(("gemorna", m.LAMBDA_GEMORNA, i, cds))
    n_indep = sum(1 for s, *_ in sources if s != "ld")

    candidates = []
    for src, lam, idx, base_cds in sources:
        for axis in AXES:
            cell_seed = _seed(f"{target_id}|{src}|{lam}|{idx}|{axis}")
            axis_cds = _axis_encode(axis, protein, base_cds, syn, weights,
                                    target_id, src, lam, idx, rng_seed=None,
                                    density=density)
            cai = cai_local(axis_cds, weights)
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
                    cand["id"] = _lattice_id(src, lam, idx, axis, cell_seed,
                                             u5p, u3p)
                    cand["lambda_rank"] = rank_map.get(lam, span)
                    cand["axis"] = axis
                    cand["constraints"] = dict(local)
                    cand["constraints"].update({"C6": c6, "C7": c7})
                    cand["flags"]["passed"] = all(cand["constraints"].values())
                    cand["archive"] = {
                        "C3_polya_signal_count": m.polya_signal_count(axis_cds),
                        "C4_restriction_hits": m.restriction_site_hits(full),
                        "C5_splice_motif_count": m.splice_motif_count(axis_cds),
                        "C8_uAUG_count": u5[u5p].count("AUG"),
                        "E1_cai": cai,
                        "E2_full_mfe": fold["E2_full_mfe"],
                        "E3_junction_mfe_per_nt": None,
                        "E4_utr5_mrl": 0.0, "E5_utr3_stability": 0.0,
                        "E6_rare_codons": m.rare_codon_count(axis_cds, species, rare),
                        "E7_pair_ratio": fold["E7_pair_ratio"],
                        "E8_delta_gc": abs(m.gc_fraction(full) - wt_gc),
                        "E9_are_count": m.are_count(u3[u3p]),
                        "E10_kozak": m.kozak_score(u5[u5p], axis_cds),
                        "E11_ld_lambda": float(lam),
                        "E11_utility_lambda": None,
                        "E12_motivation": "",
                        "C6_start_open": fold["C6_start_open"],
                        "C7_longest_stem": fold["C7_stem"],
                        "CDS_unpaired": 0.0, "full_gc": m.gc_fraction(full),
                        "E13_gen_axis": axis,
                        "E14_gen_lattice": {"cell_seed": cell_seed,
                                            "src": src, "idx": idx},
                    }
                    candidates.append(cand)
    # E4/E5 池级预测(每唯一 UTR 一次; 与静态池一致)
    mrl_cache = {p: m.gemorna_predict_mrl(u5[p]) for p in m.UTR_PRESETS}
    stab_cache = {p: m.gemorna_predict_stability(u3[p]) for p in m.UTR_PRESETS}
    for c in candidates:
        c["archive"]["E4_utr5_mrl"] = mrl_cache[c["utr5_preset"]]
        c["archive"]["E5_utr3_stability"] = stab_cache[c["utr3_preset"]]

    pool = {"target_id": target_id, "species": species, "protein": protein,
            "candidates": candidates, "registry": registry,
            "rank_map": rank_map, "pref_ranks": pref_ranks, "rank_span": span,
            "feasible_gears": feas["feasible_gears"], "ld_gears": gears,
            "n_independent_rows": n_indep,
            "density": density, "generation_seconds": time.perf_counter() - t0,
            "pool_kind": "lattice",
            "lattice_plan": {
                "target_id": target_id,
                "feasible_gears": feas["feasible_gears"],
                "gears_selected": gears,
                "mode": plan["mode"],
                "n_ld_gears": len(rank_map),
                "n_independent_rows": n_indep,
                "density": density,
                "axes": list(AXES),
                "rank_map": rank_map,
                "pref_ranks": pref_ranks,
                "rank_span": span,
                "e14_declaration": lattice_gear_declaration(rank_map),
            }}
    assign_utilities_dyn(pool)
    n_pass = sum(1 for c in candidates if c["flags"]["passed"])
    log(f"  [lattice:{target_id}] {len(candidates)} cells, {n_pass} pass "
        f"(gears={gears} src={len(sources)} incl {n_indep} indep), "
        f"{pool['generation_seconds']:.0f}s", flush=True)
    return pool


def _axis_encode(axis: str, protein: str, base_cds: str, syn: dict,
                 weights: dict, target_id: str, src: str, lam: float, idx: int,
                 *, rng_seed: int | None, density: float) -> str:
    """方向轴编码 + 多样度扩展器(格种子; rng_seed 覆盖时用于请求重派生)。

    轴种子含源 idx(同 λ 的 GM 行彼此不碰撞, P2 修复 3); frac 轴在源 CDS 上
    应用(0.5 保留档位结构特征, P2 修复 1/3)。"""
    cell_seed = _seed(f"{target_id}|{src}|{lam}|{idx}|{axis}") \
        if rng_seed is None else rng_seed
    rng = random.Random(cell_seed)
    if axis == "cai_max":
        axis_cds = axis_cai_max(protein, syn)
    elif axis == "frac":
        axis_cds = axis_apply_frac(base_cds, syn, rng)
    else:
        axis_cds = axis_cai_floor(protein, syn, weights, rng,
                                  floor_target=CAI_FLOOR_TARGET)
    if density > 0:
        vars_ = synonymous_diversify(axis_cds, weights, syn, density,
                                     n=DIVERSITY_N_VARIANTS, seed=cell_seed)
        axis_cds = vars_[0]
    return axis_cds


def _lattice_id(src: str, lam: float, idx: int, axis: str, cell_seed: int,
                u5p: str, u3p: str) -> str:
    ax = {"cai_max": "mx", "frac": "fr", "cai_floor": "fl"}[axis]
    if src == "ld":
        pre = f"ld{int(lam)}"
    else:
        pre = f"gm{idx}"
    return f"{pre}_{ax}_{cell_seed % 100000}_u5{u5p[0]}_u3{u3p[0]}"


def regenerate_cells(pool: dict, meta: dict, registry, data: dict,
                     ctx: CodonContextResolver, *, axis: str,
                     lambda_hint: float | None, diversity_target: float,
                     request_id: int) -> tuple[list[dict], list[float]]:
    """request_generate 执行: 方向轴重派生(零 LD, 新种子偏移)或指定 λ 档重生成。

    - lambda_hint ∈ 可行区间(gate 保证): 非格档 → 1 LD(缓存)探测, 可行则并入
      格(feasible_gears 由调用方同步);
    - 目标行 = 指定 λ 的 LD 行(或全部 LD 行), 在指定轴上按新种子偏移重派生
      + 多样度扩展(density=diversity_target) → 新候选(全量评估)入池;
    - 新档并入后档序重排(按 λ 排序, U 语义保持)回填池。
    返回 (新增候选, 新并入可行档列表)。"""
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    weights = ctx.weights
    syn = ctx.synonyms
    target_id = pool["target_id"]
    u5, u3 = _gm_utr_cache(data, target_id)
    rare = m.rare_codon_set(species)
    wt_gc = m._wt_cds_gc(target_id)
    csv = ctx.codon_usage_csv(CODON_TABLE_OUT)
    added_lams: list[float] = []

    # 1) λ 档: 非格档 → 1 LD 探测(缓存); 可行则新增来源行
    lams = list(pool["ld_gears"])
    if lambda_hint is not None and lambda_hint not in lams:
        cds = cds_for_lambda(target_id, meta, registry, lambda_hint, csv, data)
        if cds and _lambda_feasible(target_id, cds, u5, u3, weights, rare):
            added_lams.append(lambda_hint)
            lams = sorted(set(lams) | {lambda_hint})
    # 2) 目标行(指定 λ 或全部 LD 行)
    targets: list[tuple[str, float, int, str]] = []
    if lambda_hint is not None:
        cds = cds_for_lambda(target_id, meta, registry, lambda_hint, csv, data)
        if cds:
            targets.append(("ld", lambda_hint, 0, cds))
    else:
        for lam in pool["ld_gears"]:
            cds = cds_for_lambda(target_id, meta, registry, lam, csv, data)
            if cds:
                targets.append(("ld", lam, 0, cds))
    if not targets:
        return [], added_lams
    # 档序重排回填池(新档并入后按 λ 排序, U 语义保持)
    rank_map = dynamic_rank_map(lams)
    pref_ranks = dynamic_pref_ranks(rank_map)
    span = max(2, len(rank_map) + 1)
    pool["ld_gears"] = lams
    pool["rank_map"] = rank_map
    pool["pref_ranks"] = pref_ranks
    pool["rank_span"] = span

    new_cands = []
    for src, lam, idx, base_cds in targets:
        cell_seed = _seed(f"{target_id}|{src}|{lam}|{idx}|{axis}|r{request_id}")
        axis_cds = _axis_encode(axis, protein, base_cds, syn, weights,
                                target_id, src, lam, idx, rng_seed=cell_seed,
                                density=diversity_target)
        cai = cai_local(axis_cds, weights)
        for u5p in m.UTR_PRESETS:
            for u3p in m.UTR_PRESETS:
                full = u5[u5p] + axis_cds + u3[u3p]
                local = _local_check(full, u5[u5p], axis_cds, u3[u3p], cai, rare)
                if not all(local.values()):
                    continue
                fold = _fold_check(u5[u5p], axis_cds, u3[u3p])
                cand = m.make_candidate(axis_cds, u5[u5p], u3[u3p], lam, u5p, u3p,
                                        species, source=src, idx=idx)
                cand["id"] = _lattice_id(src, lam, idx, axis, cell_seed, u5p, u3p)
                cand["lambda_rank"] = rank_map.get(lam, span)
                cand["axis"] = axis
                cand["constraints"] = dict(local)
                cand["constraints"].update({"C6": fold["C6"], "C7": fold["C7"]})
                cand["flags"]["passed"] = all(cand["constraints"].values())
                cand["archive"] = {
                    "C3_polya_signal_count": m.polya_signal_count(axis_cds),
                    "C4_restriction_hits": m.restriction_site_hits(full),
                    "C5_splice_motif_count": m.splice_motif_count(axis_cds),
                    "C8_uAUG_count": u5[u5p].count("AUG"),
                    "E1_cai": cai,
                    "E2_full_mfe": fold["E2_full_mfe"],
                    "E3_junction_mfe_per_nt": None,
                    "E4_utr5_mrl": 0.0, "E5_utr3_stability": 0.0,
                    "E6_rare_codons": m.rare_codon_count(axis_cds, species, rare),
                    "E7_pair_ratio": fold["E7_pair_ratio"],
                    "E8_delta_gc": abs(m.gc_fraction(full) - wt_gc),
                    "E9_are_count": m.are_count(u3[u3p]),
                    "E10_kozak": m.kozak_score(u5[u5p], axis_cds),
                    "E11_ld_lambda": float(lam),
                    "E11_utility_lambda": None,
                    "E12_motivation": "",
                    "C6_start_open": fold["C6_start_open"],
                    "C7_longest_stem": fold["C7_stem"],
                    "CDS_unpaired": 0.0, "full_gc": m.gc_fraction(full),
                    "E13_gen_axis": axis,
                    "E14_gen_lattice": {"cell_seed": cell_seed,
                                        "src": src, "idx": idx,
                                        "request_id": request_id},
                }
                new_cands.append(cand)
    # E4/E5 补(池级缓存)
    mrl_cache = pool.get("mrl_cache") or {p: m.gemorna_predict_mrl(u5[p])
                                          for p in m.UTR_PRESETS}
    stab_cache = pool.get("stab_cache") or {p: m.gemorna_predict_stability(u3[p])
                                            for p in m.UTR_PRESETS}
    pool["mrl_cache"], pool["stab_cache"] = mrl_cache, stab_cache
    for c in new_cands:
        c["archive"]["E4_utr5_mrl"] = mrl_cache[c["utr5_preset"]]
        c["archive"]["E5_utr3_stability"] = stab_cache[c["utr3_preset"]]
    return new_cands, added_lams


# ---------------------------------------------------------------------------
# 观察(LLM 输入)
# ---------------------------------------------------------------------------


def _lattice_overview(pool: dict) -> str:
    passed = [c for c in pool["candidates"] if c["flags"]["passed"]]
    by_axis: dict[str, list] = {}
    for c in pool["candidates"]:
        by_axis.setdefault(c.get("axis", "?"), []).append(c)
    lines = [
        f"Generation lattice: {len(pool['candidates'])} cells "
        f"({len(passed)} pass ALL {len(m.CONSTRAINT_IDS)} constraints) for target "
        f"{pool['target_id']} (species={pool['species']}).",
        f"Rows: LD gears {pool['ld_gears']} (lambda_rank {dict(pool['rank_map'])}) "
        f"+ {pool['n_independent_rows']} independent source rows (rank after LD).",
        f"Columns: 3 direction axes x 9 GEMORNA UTR combos: "
        f"{', '.join(f'{ax}={len(v)} cells' for ax, v in sorted(by_axis.items()))}.",
        f"Lattice gear declaration (E14): {pool['lattice_plan']['e14_declaration']}.",
        "Axes: cai_max(expression, CAI plateau) / frac(balanced, CAI~0.90) / "
        "cai_floor(stability, CAI~0.85) — separation by construction.",
        "Profiles: expression(小λ CAI优先), stability(大λ 稳定优先), "
        "balanced(中λ 均等). U=0.8*regional+0.2*global(MFE)+0.8*lambda-pref.",
    ]
    return "\n".join(lines)


def _lattice_candidate_table(pool: dict, cap: int = LATTICE_CAND_TABLE_CAP) -> str:
    passing = [c for c in pool["candidates"] if c["flags"]["passed"]]
    ucol = " | ".join(f"U({p})" for p in m.PROFILES)
    header = (f"id | axis | lambda | utr5 | utr3 | {'/'.join(m.CONSTRAINT_IDS)}"
              f" | {ucol} | CAI | MFE | rare | pair% | stem | ARE")
    rows = [
        f"# Candidate table: {len(passing)}/{len(pool['candidates'])} lattice cells "
        f"pass all constraints (non-passing rows omitted). "
        f"axis in {{cai_max,frac,cai_floor}}; lambda<0 = independent source.",
        header,
    ]
    for c in passing[:cap]:
        cs = "".join("1" if c["constraints"][k] else "0" for k in m.CONSTRAINT_IDS)
        a = c["archive"]
        us = " | ".join(f"{c['utility'][p]:.3f}" for p in m.PROFILES)
        rows.append(
            f"{c['id']} | {c.get('axis', '-')} | {c['lambda']} | {c['utr5_preset']} "
            f"| {c['utr3_preset']} | {cs} | {us} | {a['E1_cai']:.3f} | "
            f"{a['E2_full_mfe']:.1f} | {a['E6_rare_codons']} | "
            f"{a['E7_pair_ratio']:.1f} | {a['C7_longest_stem']} | {a['E9_are_count']}")
    if len(passing) > cap:
        rows.append(f"... (+{len(passing) - cap} more, deterministic truncation)")
    return "\n".join(rows)


def _static_overview(pool: dict) -> str:
    """静态配方池概览(arm B; λ{0,1,4,10}×9UTR, B0 同 r5 口径)。"""
    passed = [c for c in pool["candidates"] if c["flags"]["passed"]]
    by_lam: dict[float, int] = {}
    for c in pool["candidates"]:
        by_lam[c["lambda"]] = by_lam.get(c["lambda"], 0) + 1
    lines = [
        f"Static recipe pool: {len(pool['candidates'])} candidates "
        f"({len(passed)} pass ALL {len(m.CONSTRAINT_IDS)} constraints) for target "
        f"{pool['target_id']} (species={pool['species']}).",
        f"Rows: LD lambda {sorted(by_lam)} x 9 GEMORNA UTR combos "
        f"(lambda_rank {dict(pool['rank_map']) if 'rank_map' in pool else 'static rank'}).",
        f"Candidates per lambda: {', '.join(f'{lam}={n}' for lam, n in sorted(by_lam.items()))}.",
        "Profiles: expression(小λ CAI优先), stability(大λ 稳定优先), "
        "balanced(中λ 均等). U=0.8*regional+0.2*global(MFE)+0.8*lambda-pref.",
        "NOTE: static pool = E5 r5 同口径; 多样化不足时可 request_generate 新 lambda "
        "(≤1 次, 与 lineardesign 共享档位).",
    ]
    return "\n".join(lines)


def _observation(pool: dict, history: list[dict], gate_feedback: str = "") -> str:
    if pool.get("pool_kind") == "static":
        overview = _static_overview(pool)
    else:
        overview = _lattice_overview(pool)
    return (
        overview
        + "\n\nCandidate table:\n"
        + _lattice_candidate_table(pool)
        + "\n\nRound history:\n"
        + (json.dumps(history, ensure_ascii=False) if history else "(none)")
        + (f"\n\nGATE FEEDBACK (hard constraints, do not contest):\n{gate_feedback}"
           if gate_feedback else "")
    )


ACTION_SYSTEM = """\
You are the constraint-navigation agent of an RNA full-length mRNA design system
operating on a GENERATION LATTICE (rows = lambda gears, columns = 3 direction axes,
x 9 UTR combos; fully generated and evaluated). Each round reply ONE JSON action:
{"action": "select", "profiles": {"<profile>": ["<candidate_id>", ...5 ids]},
 "rationale": "..."}
    Choose exactly 5 constraint-passing candidate ids per profile for delivery.
{"action": "sort", "profiles": {"<profile>": {"ranking": ["<5 ids>"],
 "arbitration": [{"pair": ["<idA>", "<idB>"], "layer": 1|2|3|4,
 "evidence": "<archive metric key(s) cited>"}]}}, "rationale": "..."}
    Order your 5 candidates per profile as tie-break arbitration ONLY; the system
    re-orders them by U descending (mechanized, consistency R1). Layers:
    1=immunogenicity (C7_longest_stem, E9_are_count), 2=stability (E2_full_mfe,
    E7_pair_ratio), 3=translation start (E4_utr5_mrl, C6_start_open),
    4=codon preference (E1_cai, E6_rare_codons).
{"action": "repair", "profile": "<profile>", "replace": {"drop": "<id>", "add": "<id>"},
 "reason": "..."}  // max 2 rounds
{"action": "lineardesign", "lambda": <float>, "reason": "..."}  // extra LD CDS (<=2)
{"action": "request_generate", "axis": "cai_max|frac|cai_floor",
 "lambda_hint": <float|null>, "diversity_target": <0.02-0.25>, "reason": "..."}
    Request regeneration: re-derive direction-axis cells (zero LD) and/or probe a
    lambda inside the feasible interval report (1 LD, cached). Diversity target in
    [0.02, 0.25]. At most 2 requests per gene.
{"action": "finalize", "deliveries": {"<profile>": {"ranking": ["<5 ids>"],
 "notes": {"<candidate_id>": "<mRNAdesigner-inspired motivation for E12>"}}},
 "rationale": "..."}
    Final delivery: exactly 5 constraint-passing candidates per profile. Deliveries
    must span >=2 direction axes (diversity D2: delivery CAI span >= 0.05) where
    the lattice allows; lambda-gear coverage is declared at lattice level (E14).
    Ranking is mechanized (re-ordered by U descending); use ranking to arbitrate
    U ties only.
IMPORTANT: reply with JSON only, no prose outside the JSON object.
"""

ACTION_SYSTEM_B = """\
You are the RNA full-length mRNA design agent operating on a STATIC recipe pool
(lambda {0,1,4,10} x 9 GEMORNA UTR combos; fully generated and evaluated).
Each round reply ONE JSON action:
{"action": "select", "profiles": {"<profile>": ["<candidate_id>", ...5 ids]},
 "rationale": "..."}
{"action": "sort", "profiles": {"<profile>": {"ranking": ["<5 ids>"],
 "arbitration": [{"pair": ["<idA>", "<idB>"], "layer": 1|2|3|4,
 "evidence": "<archive metric key(s) cited>"}]}}, "rationale": "..."}
{"action": "repair", "profile": "<profile>", "replace": {"drop": "<id>", "add": "<id>"},
 "reason": "..."}  // max 2 rounds
{"action": "lineardesign", "lambda": <float>, "reason": "..."}  // extra LD CDS (<=1)
{"action": "request_generate", "lambda_hint": <float>, "reason": "..."}
    Re-derive one lambda gear on the static pool (1 LD, cached; <=1 per gene).
    lambda_hint must be a NEW gear (not in {0,1,4,10}).
{"action": "finalize", "deliveries": {"<profile>": {"ranking": ["<5 ids>"],
 "notes": {"<candidate_id>": "<mRNAdesigner-inspired motivation for E12>"}}},
 "rationale": "..."}
    Final delivery: exactly 5 constraint-passing candidates per profile; ranking is
    mechanized (re-ordered by U descending); use ranking to arbitrate U ties only.
IMPORTANT: reply with JSON only, no prose outside the JSON object.
"""


_llm_invoke = m._llm_invoke  # 复用 E5 解析路径(零复制零漂移)


def _mark_delivery(delivery: list[dict], profile: str,
                   pool: dict, note: str) -> list[dict]:
    for c in delivery:
        c["flags"]["delivered"] = True
        c["archive"]["E11_utility_lambda"] = note
    return delivery


# ---------------------------------------------------------------------------
# 三臂(A/B 静态池; C 导航格)
# ---------------------------------------------------------------------------


def run_arm_a(pool: dict, target_id: str,
              profiles: list[str] = list(m.PROFILES)) -> dict:
    """A 臂: 规则交付作用于静态配方池(E5 _default_delivery 语义, 零 LLM)。"""
    t0 = time.perf_counter()
    deliveries = {}
    for profile in profiles:
        d = m._default_delivery(pool, profile)
        d = _mark_delivery(d, profile, pool, "rule: profile lambda preference")
        deliveries[profile] = d
    return {"arm": "A", "target_id": target_id, "deliveries": deliveries,
            "llm_calls": 0, "lineardesign_calls": 0, "audit_events": 0,
            "elapsed_seconds": time.perf_counter() - t0}


def run_arm_b(pool: dict, target_id: str, llm: Any, meta: dict, registry,
              data: dict, ctx: CodonContextResolver,
              profiles: list[str] = list(m.PROFILES),
              extra_gen: dict | None = None) -> dict:
    """B 臂: 无门控 LLM 作用于静态池(2–4 次/基因, request_generate ≤1)。

    request_generate 执行 = 指定新 λ 档在静态池上的重生成(1 LD, 缓存;
    _static_regenerate; 静态池无方向轴, 无动态档序, 新候选按 E5 静态 U)。"""
    t0 = time.perf_counter()
    extra_gen = {"requests": 0, "ld": 0} if extra_gen is None else extra_gen
    history: list[dict] = []
    deliveries: dict[str, list] = {}
    ranking: dict[str, list[str]] = {}
    notes: dict[str, str] = {}
    llm_calls = 0

    def finish():
        for profile in profiles:
            d = deliveries.get(profile, [])
            if d:
                d = m.mechanize_delivery_order(d, profile)
            d = _mark_delivery(d, profile, pool, "B-arm: LLM free choice")
            deliveries[profile] = d

    while llm_calls < B_LLM_MAX:
        action = _llm_invoke(
            llm, ACTION_SYSTEM_B,
            f"Target {target_id}. Round {len(history) + 1}. "
            f"POOL: static recipe pool (lambda {list(STATIC_LAMBDAS)} x 9 UTR).\n"
            f"{_observation(pool, history)}\nProfiles to cover: {', '.join(profiles)}.",
        )
        llm_calls += 1
        kind = action.get("action")
        history.append({"action": kind, "payload": action, "gate": "none (ungated)"})
        if kind == "select":
            for profile in profiles:
                ids = action.get("profiles", {}).get(profile, [])
                deliveries[profile] = [c for c in pool["candidates"] if c["id"] in ids]
        elif kind == "sort":
            for profile in profiles:
                rk = action.get("profiles", {}).get(profile, {}).get("ranking", [])
                if rk:
                    ranking[profile] = rk
                    cands = {c["id"]: c for c in pool["candidates"]}
                    deliveries[profile] = [cands[i] for i in rk if i in cands]
        elif kind == "lineardesign":
            if extra_gen["ld"] < MAX_EXTRA_LINEARDESIGN:
                extra_gen["ld"] += 1
                new_cands = _static_regenerate(pool, meta, registry, data, ctx,
                                               float(action.get("lambda", 4.0)))
                if new_cands:
                    pool["candidates"].extend(new_cands)
                    m.assign_utilities(pool, list(profiles))
        elif kind == "request_generate":
            if extra_gen["requests"] >= MAX_EXTRA_LINEARDESIGN:
                history.append({"action": kind, "payload": action,
                                "gate": "budget: request_generate <=1"})
                continue
            lam = action.get("lambda_hint")
            lam = float(lam) if lam is not None else None
            if lam is None or lam in STATIC_LAMBDAS:
                history.append({"action": kind, "payload": action,
                                "gate": "no-op: lambda_hint must be a NEW gear "
                                        f"(not in {list(STATIC_LAMBDAS)})"})
                continue
            extra_gen["requests"] += 1
            new_cands = _static_regenerate(pool, meta, registry, data, ctx, lam)
            if new_cands:
                pool["candidates"].extend(new_cands)
                m.assign_utilities(pool, list(profiles))
            history.append({"action": kind, "payload": action, "gate": "",
                            "added_candidates": len(new_cands)})
        elif kind == "finalize":
            for profile in profiles:
                rk = action.get("deliveries", {}).get(profile, {}).get("ranking", [])
                notes.update(action.get("deliveries", {}).get(profile, {}).get("notes", {}))
                if rk:
                    ranking[profile] = rk
                    cands = {c["id"]: c for c in pool["candidates"]}
                    sel = [cands[i] for i in rk if i in cands]
                    deliveries[profile] = m.mechanize_delivery_order(sel, profile)
            break
        if all(len(deliveries.get(p, [])) >= 5 for p in profiles) and llm_calls >= 2:
            break
    finish()
    for c in pool["candidates"]:
        if c["id"] in notes:
            c["archive"]["E12_motivation"] = notes[c["id"]]
    return {"arm": "B", "target_id": target_id, "deliveries": deliveries,
            "llm_calls": llm_calls,
            "lineardesign_calls": extra_gen["ld"],
            "request_generate_calls": extra_gen["requests"],
            "audit_events": 0, "elapsed_seconds": time.perf_counter() - t0,
            "history": history}


def _static_regenerate(pool: dict, meta: dict, registry, data: dict,
                       ctx: CodonContextResolver, lam: float) -> list[dict]:
    """静态池 λ 档重生成(≤1 次/基因; 缓存优先, 语义同 E5 _neighbour_redesign)。"""
    species = pool["species"]
    csv = ctx.codon_usage_csv(CODON_TABLE_OUT)
    cds = cds_for_lambda(pool["target_id"], meta, registry, lam, csv, data)
    if not cds:
        return []
    u5, u3 = pool["utr5_cache"], pool["utr3_cache"]
    cai = cai_local(cds, ctx.weights)
    rare = m.rare_codon_set(species)
    out = []
    for u5p in m.UTR_PRESETS:
        for u3p in m.UTR_PRESETS:
            c = m.make_candidate(cds, u5[u5p], u3[u3p], lam, u5p, u3p, species)
            c["id"] = f"x{int(lam)}_u5{u5p[0]}_u3{u3p[0]}"
            _evaluate_candidate(c, cds, u5[u5p], u3[u3p], cai,
                                pool["mrl_cache"], pool["stab_cache"],
                                pool["wt_cds_gc"], rare, species)
            out.append(c)
    return out


def run_arm_c(pool: dict, target_id: str, llm: Any, meta: dict, registry,
              data: dict, ctx: CodonContextResolver,
              audit: AuditTrail, gate: DecisionGate, self_model: SelfModel,
              profiles: list[str] = list(m.PROFILES),
              extra_gen: dict | None = None) -> dict:
    """C 臂: 门控约束导航作用于导航生成格(5–9 次/基因)。

    gate_action = 旧四道闸(动作集/DecisionGate/约束矩阵/仲裁) + 第 5 道闸
    request_generate(axis ∈ 方向集, lambda_hint ∈ 可行区间, diversity_target ∈
    [0.02,0.25], 预算: request ≤2 且 LD 总 ≤3/基因)。"""
    t0 = time.perf_counter()
    extra_gen = {"requests": 0, "ld": 0} if extra_gen is None else extra_gen
    history: list[dict] = []
    deliveries: dict[str, list] = {}
    ranking: dict[str, list[str]] = {}
    notes: dict[str, str] = {}
    llm_calls = 0
    audit_events = 0
    repair_rounds = 0

    def feasible_interval() -> tuple[float, float]:
        """可行 λ 区间(动态读池; request_generate 并入新档后实时更新)。"""
        feas = pool["feasible_gears"]
        return (min(feas), max(feas)) if feas else (0.0, 0.0)

    def audit_event(kind: str, payload: dict) -> None:
        nonlocal audit_events
        audit.record(kind, payload)
        audit_events += 1

    def gate_action(action: dict) -> str:
        """架构层门控(旧四道闸全保留 + 第 5 道闸 request_generate)。"""
        kind = action.get("action")
        if kind not in ("select", "sort", "repair", "lineardesign",
                        "request_generate", "finalize"):
            msg = (f"invalid action '{kind}' (allowed: select/sort/repair/"
                   "lineardesign/request_generate/finalize)")
            audit_event("gate_action_reject", {"action": kind, "reason": msg})
            return msg
        decisions = gate.review(
            [PlannedAction(action_id=f"e6_{kind}", kind="oracle_lookup",
                           oracle=None, use="none")],
            task_type="full_length_mrna", target_family=pool["species"],
        )
        audit_event("gate_decision", {
            "action": kind, "verdict": decisions[0].verdict,
            "reason": decisions[0].reason,
        })
        # 约束矩阵 gate(架构强制): select/repair/finalize 候选必须全过
        if kind in ("select", "repair", "finalize"):
            ids: list[str] = []
            if kind == "select":
                for p in profiles:
                    ids.extend(action.get("profiles", {}).get(p, []))
            elif kind == "repair":
                ids.append(action.get("replace", {}).get("add", ""))
            else:
                for p in profiles:
                    ids.extend(action.get("deliveries", {}).get(p, {}).get("ranking", []))
            cands = {c["id"]: c for c in pool["candidates"]}
            bad = []
            for i in ids:
                c = cands.get(i)
                if c is None:
                    bad.append(f"{i}:unknown")
                elif not c["flags"]["passed"]:
                    failed = [k for k, v in c["constraints"].items() if not v]
                    bad.append(f"{i}:{'/'.join(failed)}")
            if bad:
                msg = f"constraint gate: {len(bad)} candidate(s) not passing -> {bad}"
                audit_event("gate_constraint_reject", {"ids": ids, "reasons": bad})
                return msg
        # 第 5 道闸: request_generate
        if kind == "request_generate":
            axis = action.get("axis")
            if axis not in AXES:
                msg = f"request_generate gate: axis must be one of {list(AXES)}"
                audit_event("gate_request_gen_reject", {"reason": msg})
                return msg
            lam = action.get("lambda_hint")
            if lam is not None:
                lam_f = float(lam)
                lo, hi = feasible_interval()
                if not (lo <= lam_f <= hi):
                    msg = (f"request_generate gate: lambda_hint {lam_f} outside "
                           f"feasible interval [{lo}, {hi}]")
                    audit_event("gate_request_gen_reject", {"reason": msg})
                    return msg
            try:
                d_target = float(action.get("diversity_target", 0.10))
            except (TypeError, ValueError):
                msg = "request_generate gate: diversity_target must be numeric"
                audit_event("gate_request_gen_reject", {"reason": msg})
                return msg
            if not (REQUEST_DIVERSITY_MIN <= d_target <= REQUEST_DIVERSITY_MAX):
                msg = (f"request_generate gate: diversity_target {d_target} outside "
                       f"[{REQUEST_DIVERSITY_MIN}, {REQUEST_DIVERSITY_MAX}]")
                audit_event("gate_request_gen_reject", {"reason": msg})
                return msg
            if extra_gen["requests"] >= C_MAX_REQUEST_GENERATE:
                msg = f"request_generate gate: budget {C_MAX_REQUEST_GENERATE} reached"
                audit_event("gate_request_gen_reject", {"reason": msg})
                return msg
            if extra_gen["ld"] >= C_MAX_LD_TOTAL:
                msg = f"request_generate gate: LD budget {C_MAX_LD_TOTAL} reached"
                audit_event("gate_request_gen_reject", {"reason": msg})
                return msg
        return ""

    while llm_calls < C_LLM_MAX:
        feedback = ""
        lo, hi = feasible_interval()
        action = _llm_invoke(
            llm, ACTION_SYSTEM,
            f"Target {target_id}. Round {len(history) + 1}. "
            f"GATE RULES: select/repair/finalize candidates MUST pass all constraints; "
            f"request_generate: axis in {list(AXES)}, lambda_hint inside feasible "
            f"interval [{lo}, {hi}], diversity_target in "
            f"[{REQUEST_DIVERSITY_MIN}, {REQUEST_DIVERSITY_MAX}], "
            f"budget request<=2 / LD<=3.\n"
            f"{_observation(pool, history)}"
            f"\nProfiles to cover: {', '.join(profiles)}.",
        )
        llm_calls += 1
        kind = action.get("action", "")
        gate_fb = gate_action(action)
        if gate_fb:
            feedback = gate_fb
            history.append({"action": kind, "payload": action, "gate": gate_fb})
            continue
        if kind == "select":
            for profile in profiles:
                ids = action.get("profiles", {}).get(profile, [])
                deliveries[profile] = [c for c in pool["candidates"] if c["id"] in ids]
        elif kind == "sort":
            ok = True
            for profile in profiles:
                entry = action.get("profiles", {}).get(profile, {})
                rk = entry.get("ranking", [])
                arb = entry.get("arbitration", [])
                allowed = {1: ("C7_longest_stem", "E9_are_count"),
                           2: ("E2_full_mfe", "E7_pair_ratio"),
                           3: ("E4_utr5_mrl", "C6_start_open"),
                           4: ("E1_cai", "E6_rare_codons")}
                for rec in arb:
                    layer = rec.get("layer")
                    ev = str(rec.get("evidence", ""))
                    if layer not in allowed or not any(k in ev for k in allowed[layer]):
                        ok = False
                        break
                if not ok:
                    break
                if rk:
                    ranking[profile] = rk
                    cands = {c["id"]: c for c in pool["candidates"]}
                    deliveries[profile] = [cands[i] for i in rk if i in cands]
            if not ok:
                msg = ("arbitration gate: each arbitration record must cite archive "
                       "metrics of its layer (1:C7_longest_stem/E9_are_count, "
                       "2:E2_full_mfe/E7_pair_ratio, 3:E4_utr5_mrl/C6_start_open, "
                       "4:E1_cai/E6_rare_codons)")
                audit_event("gate_arbitration_reject", {"payload": action})
                history.append({"action": kind, "payload": action, "gate": msg})
                continue
        elif kind == "repair":
            if repair_rounds >= C_MAX_REPAIR_ROUNDS:
                audit_event("gate_repair_round_limit", {"rounds": repair_rounds})
                history.append({"action": kind, "payload": action,
                                "gate": "repair round limit reached"})
                continue
            repair_rounds += 1
            profile = action.get("profile", profiles[0])
            drop = action.get("replace", {}).get("drop")
            add = action.get("replace", {}).get("add")
            cur = deliveries.get(profile, [])
            cands = {c["id"]: c for c in pool["candidates"]}
            new_list = [c for c in cur if c["id"] != drop]
            if add in cands:
                new_list.append(cands[add])
            deliveries[profile] = new_list[:5]
            audit_event("repair_round", {"profile": profile, "drop": drop, "add": add})
        elif kind == "lineardesign":
            if extra_gen["ld"] < C_MAX_LD_TOTAL:
                extra_gen["ld"] += 1
                audit_event("lineardesign_extra", {"lambda": action.get("lambda")})
                # 格语义: 指定 λ 档在 frac 轴上重派生(request_generate 预算内)
                new_cands, added = regenerate_cells(
                    pool, meta, registry, data, ctx, axis="frac",
                    lambda_hint=float(action.get("lambda", 4.0)),
                    diversity_target=DIVERSITY_DENSITY,
                    request_id=100 + extra_gen["ld"])
                if added:
                    pool["feasible_gears"] = sorted(
                        set(pool["feasible_gears"]) | set(added))
                if new_cands:
                    pool["candidates"].extend(new_cands)
                    assign_utilities_dyn(pool)
                history.append({"action": kind, "payload": action, "gate": "",
                                "added_candidates": len(new_cands)})
        elif kind == "request_generate":
            extra_gen["requests"] += 1
            axis = action.get("axis", "frac")
            lam = action.get("lambda_hint")
            lam = float(lam) if lam is not None else None
            density = min(max(float(action.get("diversity_target", 0.10)),
                              REQUEST_DIVERSITY_MIN), REQUEST_DIVERSITY_MAX)
            if lam is not None and lam not in pool["ld_gears"]:
                extra_gen["ld"] += 1  # λ 探测(缓存优先)
            audit_event("request_generate",
                        {"axis": axis, "lambda_hint": lam,
                         "diversity_target": density,
                         "requests": extra_gen["requests"],
                         "ld_total": extra_gen["ld"]})
            new_cands, added = regenerate_cells(
                pool, meta, registry, data, ctx, axis=axis, lambda_hint=lam,
                diversity_target=density,
                request_id=extra_gen["requests"])
            if added:
                pool["feasible_gears"] = sorted(
                    set(pool["feasible_gears"]) | set(added))
            if new_cands:
                pool["candidates"].extend(new_cands)
                assign_utilities_dyn(pool)
            # 格级状态回填(regenerate_cells 已更新档序; 声明同步)
            pool["lattice_plan"]["gears_selected"] = pool["ld_gears"]
            pool["lattice_plan"]["n_ld_gears"] = len(pool["rank_map"])
            pool["lattice_plan"]["e14_declaration"] = lattice_gear_declaration(
                pool["rank_map"])
            history.append({"action": kind, "payload": action, "gate": "",
                            "added_candidates": len(new_cands)})
        elif kind == "finalize":
            for profile in profiles:
                entry = action.get("deliveries", {}).get(profile, {})
                rk = entry.get("ranking", [])
                notes.update(entry.get("notes", {}))
                if rk:
                    ranking[profile] = rk
                    cands = {c["id"]: c for c in pool["candidates"]}
                    sel = [cands[i] for i in rk if i in cands]
                    deliveries[profile] = m.mechanize_delivery_order(sel, profile)
            history.append({
                "event": "mechanized_reorder",
                "profiles": {p: [c["id"] for c in deliveries.get(p, [])]
                             for p in profiles},
            })
            break
        history.append({"action": kind, "payload": action, "gate": feedback})

    for profile in profiles:
        d = deliveries.get(profile, [])
        if d:
            d = m.mechanize_delivery_order(d, profile)
        d = _mark_delivery(d, profile, pool, "C-arm: gated lattice navigation")
        deliveries[profile] = d
    for c in pool["candidates"]:
        if c["id"] in notes:
            c["archive"]["E12_motivation"] = notes[c["id"]]
    return {"arm": "C", "target_id": target_id, "deliveries": deliveries,
            "llm_calls": llm_calls,
            "lineardesign_calls": extra_gen["ld"],
            "request_generate_calls": extra_gen["requests"],
            "audit_events": audit_events, "elapsed_seconds": time.perf_counter() - t0,
            "repair_rounds": repair_rounds, "history": history}


# ---------------------------------------------------------------------------
# 评测(判据书 v8; D2 复合判据 拍板① / R3 轴锁定 top-1 拍板③)
# ---------------------------------------------------------------------------


def axis_locked_delivery(pool: dict, profile: str) -> list[dict]:
    """轴锁定交付: 画像 → 方向轴切片内 passed 候选按 U 降序取 5(R3 取 top-1 用)。"""
    axis = PROFILE_TO_AXIS[profile]
    passed = [c for c in pool["candidates"]
              if c["flags"]["passed"] and c.get("axis") == axis]
    return sorted(passed, key=lambda c: c["utility"][profile], reverse=True)[:5]


def evaluate_delivery_e6(delivery: list[dict], profile: str,
                         pool: dict, u_rank: list[dict]) -> dict:
    """每画像交付评测(判据书 v8): R1/R4 + D1/D2(复合)/D3 + e2e/约束率 + E13/E14。"""
    delivery_rank_ids = [c["id"] for c in delivery]
    u_rank_ids = [c["id"] for c in u_rank]

    rho = m.spearman_rho_rankings(delivery_rank_ids, u_rank_ids)
    r1 = rho >= 1.0 - 1e-6

    passed_subset = [c for c in pool["candidates"] if c["flags"]["passed"]]
    top1 = delivery[0] if delivery else None
    r4_pass, r4_marked = False, False
    if top1 is not None:
        if passed_subset:
            max_u = max(c["utility"][profile] for c in passed_subset)
            max_n = max(sum(1 for v in c["constraints"].values() if v)
                        for c in passed_subset)
            r4_pass = (top1["utility"][profile] >= max_u - 1e-9
                       and sum(1 for v in top1["constraints"].values() if v) == max_n)
        else:
            pool_max = max(c["utility"][profile] for c in pool["candidates"])
            r4_pass = top1["utility"][profile] >= pool_max - 1e-9
            r4_marked = True

    min_dist = min(
        m.diversity_distance(delivery[i], delivery[j])
        for i in range(len(delivery)) for j in range(i + 1, len(delivery))
    ) if len(delivery) >= 2 else 0.0
    d1 = min_dist >= 0.02
    cais = [c["archive"]["E1_cai"] for c in delivery]
    # 【拍板①】D2 = 交付多样度复合判据 = D1 ∧ 交付内 CAI 跨度 ≥ 0.05
    d2 = d2_composite(d1, cais)
    prs = [c["archive"]["E7_pair_ratio"] for c in delivery]
    stems = [c["archive"]["C7_longest_stem"] for c in delivery]
    pr_range = (max(prs) - min(prs)) if prs else 0.0
    stem_range = (max(stems) - min(stems)) if stems else 0.0
    d3 = (pr_range >= 3.0) or (stem_range >= 5.0)

    axes = sorted({c.get("axis", "-") for c in delivery})
    return {
        "profile": profile,
        "delivered_ids": delivery_rank_ids,
        "e2e_pass": m.delivery_e2e_pass(delivery),
        "constraint_rate": m.constraint_satisfaction_rate(delivery),
        "R1_spearman": rho, "R1": r1,
        "R4": r4_pass, "R4_no_constraint_solution_marked": r4_marked,
        "D1_min_dist": min_dist, "D1": d1,
        "D2_cai_span": delivery_cai_span(cais), "D2": d2,
        "D3_pair_ratio_range": pr_range,
        "D3_stem_range": stem_range, "D3": d3,
        "E13_gen_axis": {  # R3 注记(拍板③: top-1 轴锁定, 分离由构造保证)
            "top1_axis": (top1.get("axis") if top1 else None),
            "top1_cai": (top1["archive"]["E1_cai"] if top1 else None),
        },
        "E14_gen_lattice": pool.get("lattice_plan", {}).get("e14_declaration"),
        "axes_covered": axes,
    }


def r3_axis_locked(pool: dict) -> dict:
    """R3(拍板③): 各画像 top-1 按轴锁定交付取, 分离由构造保证(CAI≥0.05 或档距≥2)。"""
    tops = {pr: (axis_locked_delivery(pool, pr)[0]
                 if axis_locked_delivery(pool, pr) else None)
            for pr in m.PROFILES}
    pairs, separated = [], 0
    for i in range(len(m.PROFILES)):
        for j in range(i + 1, len(m.PROFILES)):
            a, b = tops[m.PROFILES[i]], tops[m.PROFILES[j]]
            if a is None or b is None:
                continue
            pairs.append((m.PROFILES[i], m.PROFILES[j]))
            d_cai = abs(a["archive"]["E1_cai"] - b["archive"]["E1_cai"])
            d_lam = abs(a["lambda_rank"] - b["lambda_rank"])
            if d_cai >= 0.05 or d_lam >= 2:
                separated += 1
    return {
        "separated": separated, "pairs": len(pairs),
        "R3": (separated / len(pairs) >= 1 / 3) if pairs else False,
        "tops": [{"profile": pr, "axis": (t.get("axis") if t else None),
                  "lambda_rank": (t["lambda_rank"] if t else None),
                  "E1_cai": (t["archive"]["E1_cai"] if t else None),
                  "U": (t["utility"][pr] if t else None)}
                 for pr, t in tops.items()],
    }


def evaluate_arm_e6(arm: dict, pool: dict,
                    profiles: list[str] = list(m.PROFILES)) -> dict:
    """C 臂级评测(判据书 v8): per-profile + R3(轴锁定 top-1)。"""
    per_profile = []
    for profile in profiles:
        delivery = arm["deliveries"].get(profile, [])
        u_rank = m.rank_by_utility(delivery, profile) if delivery else []
        per_profile.append(evaluate_delivery_e6(delivery, profile, pool, u_rank))
    r3 = r3_axis_locked(pool)
    out = {
        "arm": arm["arm"], "target_id": arm["target_id"],
        "profiles": per_profile,
        "R3_separated_pairs": r3["separated"],
        "R3_total_pairs": r3["pairs"],
        "R3": r3["R3"],
        "R3_tops": r3["tops"],
        "llm_calls": arm.get("llm_calls", 0),
        "lineardesign_calls": arm.get("lineardesign_calls", 0),
        "request_generate_calls": arm.get("request_generate_calls", 0),
        "elapsed_seconds": arm.get("elapsed_seconds", 0.0),
        "audit_events": arm.get("audit_events", 0),
    }
    for p in per_profile:
        p["R3"] = r3["R3"]  # 供 S2 JCD 每画像引用
    return out


def _ab_ev_e6(ev_ab: dict, arm_rec: dict) -> dict:
    """A/B 臂评测补 E6 统一字段(拍板① D2 复合语义 + 臂级 R3): 三臂判据一致。

    E5 evaluate_delivery 的 D2 是 λ 档语义(≥3 档或跨度≥2)—— 对静态池 A/B 臂
    保留原口径(ev_ab 内), 但 JCD 与复合得分用拍板①复合判据(D2 = D1 ∧ CAI
    跨度≥0.05)。R3 用 E5 臂级交付 top-1 分离结果。"""
    ev_ab = copy.deepcopy(ev_ab)
    for p in ev_ab["profiles"]:
        dl = arm_rec["deliveries"].get(p["profile"], [])
        cais = [c["archive"]["E1_cai"] for c in dl]
        p["D2_cai_span"] = delivery_cai_span(cais)
        p["D2"] = d2_composite(p["D1"], cais)
        p["D2_lambda_ranks"] = sorted({c["lambda_rank"] for c in dl})
        p["R3"] = ev_ab.get("R3", False)
        p["axes_covered"] = []
        p["E13_gen_axis"] = None
        p["E14_gen_lattice"] = None
    return ev_ab


def jcd_pass(ev: dict) -> bool:
    """per-profile JCD-pass(e2e∧D1∧D2∧R3; S2 主终点配对)。"""
    return bool(ev["e2e_pass"] and ev["D1"] and ev["D2"] and ev.get("R3", False))


def composite_score(ev: dict) -> float:
    """连续复合得分(0.4×e2e + 0.2×约束率 + 0.2×D1/D2 + 0.2×R3)。

    D1/D2 槽连续编码(拍板①语义): 0.5×min(D1_dist/0.02,1) + 0.5×(D1 ?
    min(CAI跨度/0.05,1) : 0) —— D2 复合判据的连续对应。"""
    e2e = 1.0 if ev["e2e_pass"] else 0.0
    rate = ev["constraint_rate"]
    d1 = min(ev["D1_min_dist"] / 0.02, 1.0)
    d2 = min(ev.get("D2_cai_span", 0.0) / 0.05, 1.0) if ev["D1"] else 0.0
    r3 = 1.0 if ev.get("R3", False) else 0.0
    return 0.4 * e2e + 0.2 * rate + 0.2 * (0.5 * d1 + 0.5 * d2) + 0.2 * r3


# ---------------------------------------------------------------------------
# 阶段编排(S0/S1/S2)
# ---------------------------------------------------------------------------


def now_iso() -> str:
    return m.now_iso()


def load_records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def done_keys(records: list[dict]) -> set[tuple[str, str]]:
    return {(r["stage"], r["target_id"]) for r in records if r.get("success")}


def write_record(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def write_verdict(stage: str, cells: list[dict], verdict: dict) -> Path:
    path = RESULTS_DIR / f"e6_verdict_{stage}.json"
    payload = {"stage": stage, "timestamp": now_iso(),
               "cells": cells, "verdict": verdict}
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2),
                    encoding="utf-8")
    return path


def load_data() -> dict:
    return {
        "survey": _load_json(SURVEY_PATH, {}),
        "gm_utr": _load_json(GM_UTR_CACHE_PATH, {}),
    }


def make_runner() -> tuple[Any, Any]:
    return m.make_runner()


def ensure_e6_services(log: Any = print) -> None:
    m.ensure_e5_services(log=log)


def _pool_snapshot(pool: dict) -> dict:
    snap = {k: copy.deepcopy(v) for k, v in pool.items() if k != "registry"}
    snap["registry"] = pool["registry"]
    return snap


def _lattice_axis_signature(pool: dict) -> list[tuple]:
    """轴确定性签名: (axis, src, lam, idx, cds) 排序列表(S0 重复间比对)。"""
    return sorted(
        (c.get("axis"), c["source"], float(c["lambda"]), c.get("idx", 0), c["cds"])
        for c in pool["candidates"])


def run_one_cell(stage: str, target_id: str, arms: list[str],
                 llm: Any, out: Path, *, repeat: int = 1,
                 log: Any = print) -> dict:
    """One (target × arms) cell: 静态池(A/B) + 导航格(C), 独立池分层。"""
    ensure_e6_services(log=log)
    meta = json.loads((TARGETS_DIR / f"{target_id}.json").read_text(encoding="utf-8"))
    registry, _executor = make_runner()
    data = load_data()
    species = meta.get("species_for_codon_optimization") or "human"
    ctx = CodonContextResolver(species)
    source_note = (SOURCE_SPECIES_NOTES or {}).get(target_id)
    log(f"[{stage}:{target_id}] context={ctx.canonical} "
        f"res={ctx.resolution()} {source_note or ''}", flush=True)

    # 组件 1: 可行性探测(缓存优先; 每靶 ≤5 新 LD)
    feas = probe_feasibility(target_id, meta, registry, data, ctx, log=log)

    static_pool = None
    lattice_pool = None
    if "A" in arms or "B" in arms:
        log(f"[{stage}:{target_id}] building static recipe pool ...", flush=True)
        static_pool = build_static_pool(target_id, meta, registry, data, ctx, log=log)
    if "C" in arms:
        log(f"[{stage}:{target_id}] building navigation lattice ...", flush=True)
        lattice_pool = build_lattice(target_id, meta, registry, data, ctx, feas,
                                     log=log)

    audit = AuditTrail(RESULTS_DIR / "e6_audit" / f"{stage}_{target_id}.jsonl")
    self_model = SelfModel(audit=audit)
    gate = DecisionGate(self_model, audit=audit)

    arms_out: dict[str, dict] = {}
    c_runs: list[dict] = []
    extra_gen_b = {"requests": 0, "ld": 0}
    extra_gen_c = {"requests": 0, "ld": 0}
    if "A" in arms:
        arms_out["A"] = run_arm_a(static_pool, target_id)
    if "B" in arms:
        arms_out["B"] = run_arm_b(static_pool, target_id, llm, meta, registry,
                                  data, ctx, extra_gen=extra_gen_b)
    if "C" in arms:
        base_pool = _pool_snapshot(lattice_pool)
        for rep in range(repeat):
            log(f"[{stage}:{target_id}] C-arm repeat {rep + 1}/{repeat} ...",
                flush=True)
            rep_pool = copy.deepcopy(base_pool)
            c_runs.append(run_arm_c(rep_pool, target_id, llm, meta, registry, data,
                                    ctx, audit, gate, self_model,
                                    extra_gen=extra_gen_c))
            have = {c["id"] for c in lattice_pool["candidates"]}
            for c in rep_pool["candidates"]:
                if c["id"] not in have:
                    lattice_pool["candidates"].append(c)
                    have.add(c["id"])

    # 交付级 E3 接头评估(junction; 与 E5 同路径)后重算 U(含 E3 分量:
    # U 的 global 项在 E3 非 None 时 = 0.5×MFE + 0.5×E3norm; 各臂用自己池语义)
    for arm_rec in list(arms_out.values()) + c_runs:
        m.delivery_eval_junctions(static_pool or lattice_pool, registry, arm_rec)
    if lattice_pool:
        # C 臂重复交付是深拷贝副本 → E3 回传格对象后统一重算 U, 再回写副本
        # (R4/top-1 与格内 max U 比较的对象同一性)
        by_id = {c["id"]: c for c in lattice_pool["candidates"]}
        for arm_rec in c_runs:
            for dl in arm_rec["deliveries"].values():
                for c in dl:
                    host = by_id.get(c["id"])
                    if host is not None:
                        host["archive"]["E3_junction_mfe_per_nt"] = \
                            c["archive"]["E3_junction_mfe_per_nt"]
        assign_utilities_dyn(lattice_pool)
        for arm_rec in c_runs:
            for dl in arm_rec["deliveries"].values():
                for c in dl:
                    host = by_id.get(c["id"])
                    if host is not None:
                        c["utility"] = host["utility"]
                        c["scores"] = host["scores"]
    if static_pool:
        m.assign_utilities(static_pool)

    rec = {
        "stage": stage,
        "target_id": target_id,
        "arms": arms,
        "success": True,
        "context": {"species": species, "canonical": ctx.canonical,
                    "resolution": ctx.resolution(), "source_note": source_note},
        "pool": {
            "static": ({"n_candidates": len(static_pool["candidates"]),
                        "n_pass_all": sum(1 for c in static_pool["candidates"]
                                          if c["flags"]["passed"]),
                        "generation_seconds": static_pool["generation_seconds"]}
                       if static_pool else None),
            "lattice": ({"n_candidates": len(lattice_pool["candidates"]),
                         "n_pass_all": sum(1 for c in lattice_pool["candidates"]
                                           if c["flags"]["passed"]),
                         "generation_seconds": lattice_pool["generation_seconds"],
                         "lattice_plan": lattice_pool.get("lattice_plan")}
                        if lattice_pool else None),
            "feasibility": feas,
        },
        "arm_results": {},
        "evaluations": {},
        "timestamp": now_iso(),
    }
    for arm, arm_rec in arms_out.items():
        rec["arm_results"][arm] = arm_rec
        rec["evaluations"][arm] = _ab_ev_e6(
            m.evaluate_arm(arm_rec, static_pool), arm_rec)
    if c_runs:
        rec["arm_results"]["C_runs"] = c_runs
        base = dict(c_runs[0])
        base["arm"] = "C"
        base["deliveries"] = c_runs[0]["deliveries"]
        rec["evaluations"]["C"] = evaluate_arm_e6(base, lattice_pool)
        rec["evaluations"]["C"]["R2_tau_min"] = min(
            m.r2_stability(c_runs, p) for p in m.PROFILE_DEFS
        )
        rec["evaluations"]["C"]["R2_by_profile"] = {
            p: m.r2_stability(c_runs, p) for p in m.PROFILE_DEFS
        }
        rec["evaluations"]["C"]["llm_calls"] = sum(r["llm_calls"] for r in c_runs)
        # 轴确定性锚点(S0 判据: 同种子同缓存 → 签名跨重复稳定)
        rec["evaluations"]["C"]["lattice_axis_signature_sha"] = hashlib.sha256(
            json.dumps(_lattice_axis_signature(lattice_pool)).encode()).hexdigest()[:16]
        rec["evaluations"]["C"]["lattice_plan"] = lattice_pool.get("lattice_plan")
    return rec


# ── S0 机制验证: Insulin × C 臂 × 3 重复 ──
def run_s0(target_id: str, llm: Any, out: Path, *, repeat: int = 3,
           log: Any = print) -> int:
    t_start = time.perf_counter()
    rec = run_one_cell("s0", target_id, ["C"], llm, out, repeat=repeat, log=log)
    write_record(out, rec)
    ev = rec["evaluations"]["C"]
    criteria = {
        "output_format_complete": all(
            len(ev["profiles"][i]["delivered_ids"]) == 5
            for i in range(len(m.PROFILE_DEFS))),
        "R2_stability_tau_ge_0.8": ev.get("R2_tau_min", 0.0) >= 0.8,
        "axis_locked_r3": bool(ev.get("R3")),
        "no_crash": rec["success"],
        "elapsed_within_budget": (time.perf_counter() - t_start) < S0_TIME_BUDGET_S,
        "lattice_determinism_recorded": bool(ev.get("lattice_axis_signature_sha")),
    }
    verdict = {
        "criteria": criteria,
        "elapsed_seconds": time.perf_counter() - t_start,
        "time_budget_s": S0_TIME_BUDGET_S,
        "cell": {k: ev.get(k) for k in ("R2_tau_min", "R2_by_profile", "llm_calls",
                                        "R3", "R3_separated_pairs", "R3_total_pairs")},
        "lattice_plan": ev.get("lattice_plan"),
        "axis_signature_sha": ev.get("lattice_axis_signature_sha"),
    }
    ok = all(criteria.values())
    verdict["go_no_go"] = "GO" if ok else "NO-GO"
    path = write_verdict("s0", [rec], verdict)
    log(f"[s0] verdict -> {path}: {verdict['go_no_go']}")
    return 0 if ok else 1


# ── S1 小规模: 5 靶点 × 3 臂(判据书 v8 六项)──
def run_s1(targets: list[str], llm: Any, out: Path, *, arms: list[str] = ["A", "B", "C"],
           log: Any = print) -> int:
    t_start = time.perf_counter()
    cells = []
    for target_id in targets:
        rec = run_one_cell("s1", target_id, arms, llm, out, repeat=1, log=log)
        write_record(out, rec)
        cells.append(rec)
    ev = {c["target_id"]: c["evaluations"] for c in cells}
    c_arms = [ev[t].get("C") for t in targets if "C" in ev[t]]
    a_arms = [ev[t].get("A") for t in targets if "A" in ev[t]]

    # ① e2e C≥0.8 且 C≥A 平局算过(v7 语义保持; 分层池下 C>A 真实可达时如实报告)
    c_e2e_gene = mean(all(p["e2e_pass"] for p in e["profiles"]) for e in c_arms) \
        if c_arms else 0.0
    a_e2e_gene = mean(all(p["e2e_pass"] for p in e["profiles"]) for e in a_arms) \
        if a_arms else 0.0
    crit1 = (c_e2e_gene >= 0.8) and (c_e2e_gene >= a_e2e_gene)
    # ② 约束率 C≥0.9
    crit2 = (mean(mean(p["constraint_rate"] for p in e["profiles"]) for e in c_arms)
             >= 0.9) if c_arms else False
    # ③ R1–R4 全过(R3 注记 E13_gen_axis; 拍板③ 轴锁定 top-1)
    crit3 = (bool(c_arms)
             and all(p["R1"] and p["R4"] for e in c_arms for p in e["profiles"])
             and all(e["R3"] for e in c_arms))
    # ④ D1–D3 全过(D2 复合判据 拍板①; E14_gen_lattice 格级声明 ≥3 档)
    crit4 = (bool(c_arms)
             and all(p["D1"] and p["D2"] and p["D3"] for e in c_arms
                     for p in e["profiles"])
             and all((e.get("lattice_plan") or {}).get("e14_declaration", {}).get(
                 "ge_3") for e in c_arms))
    # ⑤ 方向性 C≥A 4/5(基因级 e2e)
    _c_beats_a = 0
    for _t in targets:
        _cev, _aev = ev[_t].get("C"), ev[_t].get("A")
        if not (_cev and _aev):
            continue
        _c_pass = all(p["e2e_pass"] for p in _cev["profiles"])
        _a_pass = all(p["e2e_pass"] for p in _aev["profiles"])
        if _c_pass >= _a_pass:
            _c_beats_a += 1
    crit5 = _c_beats_a >= 4
    # ⑥ 预算记录(描述性)
    budget_note = {
        "arm_llm_calls": {a: sum(ev[t][a]["llm_calls"] for t in targets if a in ev[t])
                          for a in arms if a in ("A", "B", "C")},
        "arm_request_generate": {a: sum(
            ev[t][a].get("request_generate_calls", 0) for t in targets if a in ev[t])
            for a in ("B", "C")},
        "ld_calls_total": sum(c["pool"]["feasibility"]["ld_calls"] for c in cells)
        + sum(len(STATIC_LAMBDAS) for c in cells)
        + sum((c["evaluations"].get("C") or {}).get("lineardesign_calls", 0)
              for c in cells),
    }
    verdict = {
        "criteria": {
            "e2e_pass_C_ge_0.8_and_C_ge_A_ties_pass": crit1,
            "constraint_rate_C_ge_0.9": crit2,
            "R1_R4_all_pass": crit3,
            "D1_D3_all_pass": crit4,
            "directional_C_ge_A_4of5": crit5,
            "budget_recorded": True,
        },
        "observed": {
            "c_e2e_gene": c_e2e_gene, "a_e2e_gene": a_e2e_gene,
            "c_constraint_rate": mean(
                mean(p["constraint_rate"] for p in e["profiles"]) for e in c_arms)
            if c_arms else None,
            "budget": budget_note,
        },
        "elapsed_seconds": time.perf_counter() - t_start,
        "go_no_go": "GO" if all([crit1, crit2, crit3, crit4, crit5, True]) else "NO-GO",
    }
    path = write_verdict("s1", cells, verdict)
    log(f"[s1] verdict -> {path}: {verdict['go_no_go']}")
    return 0 if verdict["go_no_go"] == "GO" else 1


# ── S2 全矩阵: 18 靶点 × 3 臂(双终点: JCD-pass McNemar 主 + 复合得分 Wilcoxon 辅)──
def run_s2(targets: list[str], llm: Any, out: Path, *, arms: list[str] = ["A", "B", "C"],
           log: Any = print) -> int:
    t_start = time.perf_counter()
    cells = []
    for target_id in targets:
        rec = run_one_cell("s2", target_id, arms, llm, out, repeat=1, log=log)
        write_record(out, rec)
        cells.append(rec)
    ev = {c["target_id"]: c["evaluations"] for c in cells}

    def paired(arm_x: str, arm_y: str) -> tuple[list[bool], list[float],
                                                list[float], list[float]]:
        """基因×画像级配对(n = 18×3 = 54): JCD-pass + 复合得分(C/A 双侧)。

        缺臂容错:任一臂在所有靶的 evaluations 中缺失时返回空配对
        (S2 按 §20 为 A/C 双臂;C vs B 仅作披露)。"""
        jx, jy, cx, cy = [], [], [], []
        if not all(arm_x in ev[t] and arm_y in ev[t] for t in targets):
            return jx, jy, cx, cy
        for t in targets:
            for p in range(len(m.PROFILE_DEFS)):
                ex = ev[t].get(arm_x, {}).get("profiles", [{}])[p]
                ey = ev[t].get(arm_y, {}).get("profiles", [{}])[p]
                jx.append(jcd_pass(ex))
                jy.append(jcd_pass(ey))
                cx.append(composite_score(ex))
                cy.append(composite_score(ey))
        return jx, jy, cx, cy

    def mcnemar(x: list[bool], y: list[bool]) -> dict:
        b = sum(1 for a, c in zip(x, y) if a and not c)
        c_ = sum(1 for a, cc in zip(x, y) if not a and cc)
        p = float(scipy_stats.binomtest(
            min(b, c_), b + c_, 0.5, alternative="two-sided").pvalue) if b + c_ > 0 else 1.0
        return {"b": b, "c": c_, "p": p}

    def wilcoxon_p(x: list[float], y: list[float]) -> float:
        diffs = [b - a for a, b in zip(x, y) if abs(b - a) > 1e-12]
        if len(diffs) < 2:
            return 1.0
        return float(scipy_stats.wilcoxon(diffs).pvalue)

    mc_ca = mcnemar(*paired("C", "A")[:2]) if "C" in arms and "A" in arms else None
    mc_cb = mcnemar(*paired("C", "B")[:2]) if "C" in arms and "B" in arms else None
    _, _, cx_ca, cy_ca = paired("C", "A")
    _, _, cx_cb, cy_cb = (paired("C", "B") if "C" in arms and "B" in arms
                          else ([], [], [], []))
    w_ca = wilcoxon_p(cx_ca, cy_ca) if "C" in arms and "A" in arms else 1.0
    w_cb = wilcoxon_p(cx_cb, cy_cb) if "C" in arms and "B" in arms else 1.0

    c_arms = [ev[t].get("C") for t in targets]
    c_e2e_gene = mean(all(p["e2e_pass"] for p in e["profiles"]) for e in c_arms) \
        if c_arms else 0.0
    quality = (bool(c_arms)
               and all(p["R1"] and p["R4"] for e in c_arms for p in e["profiles"])
               and all(e["R3"] for e in c_arms)
               and all(p["D1"] and p["D2"] and p["D3"] for e in c_arms
                       for p in e["profiles"])
               and all((e.get("lattice_plan") or {}).get("e14_declaration", {}).get(
                   "ge_3") for e in c_arms))
    crit_constraint = (mean(mean(p["constraint_rate"] for p in e["profiles"])
                            for e in c_arms) >= 0.9) if c_arms else False

    # 主终点(§20): JCD-pass 配对 McNemar(C vs A, n=54) + c_e2e_gene ≥0.8;
    # C vs B 仅作披露(§20 双终点均不含 B 臂对比)
    endpoint1 = (mc_ca is not None and mc_ca["p"] < 0.05
                 and c_e2e_gene >= 0.8)
    # 辅终点(§20): 连续复合得分配对 Wilcoxon(C vs A) + 质量判据
    endpoint2 = (w_ca < 0.05 and quality and crit_constraint)
    disclosed = bool(endpoint1 and not endpoint2)
    go = endpoint1 or endpoint2
    verdict = {
        "criteria": {
            "mcnemar_C_vs_A_p<0.05": (mc_ca or {}).get("p"),
            "mcnemar_C_vs_B_p<0.05": (mc_cb or {}).get("p"),
            "wilcoxon_C_vs_A_p<0.05": w_ca,
            "wilcoxon_C_vs_B_p<0.05": w_cb,
            "endpoint1_jcd_mcnemar": endpoint1,
            "endpoint2_composite_wilcoxon": endpoint2,
            "constraint_rate_C_ge_0.9": crit_constraint,
        },
        "observed": {
            "c_e2e_gene": c_e2e_gene,
            "mcnemar": {"C_vs_A": mc_ca, "C_vs_B": mc_cb},
            "wilcoxon": {"C_vs_A": w_ca, "C_vs_B": w_cb},
            "n_pairs": len(targets) * len(m.PROFILE_DEFS),
        },
        "endpoint1": endpoint1, "endpoint2": endpoint2,
        "endpoint2_not_passed_disclosed": disclosed,
        "go_no_go": "GO" if go else "NO-GO",
        "elapsed_seconds": time.perf_counter() - t_start,
    }
    path = write_verdict("s2", cells, verdict)
    log(f"[s2] verdict -> {path}: {verdict['go_no_go']}")
    return 0 if go else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="stage", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--targets", default=None, help="comma-separated target ids")
        p.add_argument("--arms", default=None,
                       help="comma-separated arms (A,B,C); default: C for s0, A,B,C otherwise")
        p.add_argument("--output", type=Path, default=None,
                       help="output JSONL path (default: results/e6_<stage>_runs.jsonl)")
        p.add_argument("--resume", action="store_true",
                       help="skip done-keys with a successful record")
        p.add_argument("--dry-run", action="store_true",
                       help="print the matrix and exit")

    p0 = sub.add_parser("s0", help="mechanism validation: 1 target x C arm x 3 repeats")
    add_common(p0)
    p0.add_argument("--repeat", type=int, default=3)
    p1 = sub.add_parser("s1", help="small scale: 5 targets x 3 arms (criteria v8)")
    add_common(p1)
    p2 = sub.add_parser("s2", help="full matrix: 18 targets x 3 arms (dual endpoints)")
    add_common(p2)

    args = parser.parse_args()
    stage = args.stage
    if args.arms is None:
        arms = ["C"] if stage == "s0" else list(m.ARMS)
    else:
        arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    bad_arms = [a for a in arms if a not in m.ARMS]
    if bad_arms:
        parser.error(f"unknown arm(s): {bad_arms} (known: {list(m.ARMS)})")

    targets = (args.targets.split(",") if args.targets
               else {"s0": ["Insulin"], "s1": S1_TARGETS, "s2": m.FULL_TARGETS}[stage])
    targets = [t.strip() for t in targets if t.strip()]
    for t in targets:
        if not (TARGETS_DIR / f"{t}.json").is_file():
            parser.error(f"unknown target '{t}' (no {TARGETS_DIR / t}.json)")

    out = args.output or (RESULTS_DIR / f"e6_{stage}_runs.jsonl")
    repeat = getattr(args, "repeat", 1)
    if args.dry_run:
        print(f"E6 {stage}: {len(targets)} targets x {len(arms)} arms "
              f"(repeat={repeat} for C) -> {out}")
        for t in targets:
            print(f"  {t}: static pool 36 (4 lambda x 9 UTR) + lattice "
                  f"(gears x 3 axes x 9 UTR + GM<=8)")
        return 0

    seed_e6_caches()
    llm = get_deepseek_llm(temperature=0.0)
    done = done_keys(load_records(out)) if args.resume else set()
    results = []
    for target_id in targets:
        key = (stage, target_id)
        if key in done:
            print(f"  skip {target_id} (done)", flush=True)
            continue
        if stage == "s0":
            rc = run_s0(target_id, llm, out, repeat=repeat)
        elif stage == "s1":
            rc = run_s1([target_id], llm, out, arms=arms)
        else:
            rc = run_s2([target_id], llm, out, arms=arms)
        results.append({"target_id": target_id, "stage": stage, "rc": rc})

    bad = [r for r in results if r["rc"] != 0]
    if bad:
        print(f"E6 {stage}: {len(bad)} cell(s) failed verdict -> "
              f"{[r['target_id'] for r in bad]}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
