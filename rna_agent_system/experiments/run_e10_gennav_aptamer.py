#!/usr/bin/env python3
"""E10 PRE-REGISTRATION (判据书 v1, 2026-08-12) — generation-layer constraint
navigation for RNA aptamer design, MECHANIZED ALLOCATION (GenNav-Apt v3).

背景: E9 (relax v1 矩阵, 9 长度格) 主终点 NO-GO (b=6, c=8, P=0.79) —
失败定位为 LLM 强化决策质量 (probe n2 噪声误导 gear 选择; standard 带零预算
反失), 而非机制失效 (mechanism 块全过, 矩阵稀缺结构成立: A-fail 11/30)。
E10 可行性模拟 (experiments/analysis/e9_mechanized_sim.py, E9 真实缓存):
机制化强化分配 (确定性贪心, 缺口加权 × laplace 平滑通过率估计) 把 c 从 8
压到 2; 剩余功效缺口 (b<=8 vs 需要 9) 由两阶段 probe 与面板扩充补足。

设计 (标准全部不动: 判据 / 48-raw 两臂同 cap / relax v1 矩阵 / S0-S1-S2 阶段):
  C 臂 = 两阶段 probe + 机制化强化分配 + LLM 仲裁:
  1. 阶段 1 probe: 长度格 {25,30,35,40,50,60,65,70,80} × seed 42 × n=2 (18 raw)
  2. 阶段 2 补采 (机制化, 无 LLM): 对 gap>0 的带, 带内 "通过者<2" 的长度用
     seed 7 补 n=2 (预算 <= 8 raw) — 提高边际长度通过率估计精度
  3. 机制化强化 (<=3 轮; 预算 48 - 18 - 补采): 每轮对未采样 (length, seed
     in {7,99}) gear 计算 gap 加权期望修复 (laplace 平滑通过率 x n), 选
     top-3 提交 LLM; LLM 从中仲裁选 1 (或 degrade / finalize)。LLM 不能
     指定机制未提议的 gear — 强化决策机制化, agent 保留仲裁与退化声明
     (E6 "ranking is mechanized; LLM arbitrates ties only" 同哲学)。
  4. 机械化交付 (与 A 臂同一 deliver_profile)。
  LLM 调用 <= 4/靶 (仲裁轮 + finalize), 低于 E8/E9 的 <= 9。

判据 (与 E9 相同):
  per-profile JCD = 交付 5 ∧ 带矩阵全过 ∧ D1。主终点: C vs A 配对 McNemar
  (精确双侧), n = 靶数 x 3; pass iff p < 0.05 ∧ C e2e >= 0.8。次级披露:
  C 矩阵通过率 >= 0.9 / LLM 预算合规 / degrade 数。S0/S1 机制门, S2 主终点。

靶点与面板规则 (预注册):
  S0 = Thrombin; S1 = Thrombin, VEGF, SARS-CoV-2_Nucleocapsid (机制验证)
  + 新靶点探针 (CAII, Cytochrome_c, Myoglobin, Papain, Pepsin 只跑 A 臂
  与 C 臂 probe, 测量新靶点 A-fail 密度)。
  S2 面板: 新靶点 A-fail 率 (探针) < 30% 时 15 靶 (10 旧 + 5 新);
  否则 12 靶 (10 旧 + A-fail 密度最高的 2 新), 并如实报告。
  Ferritin 排除 (确定性 ODesign 零产出边界)。

修订预案 (预注册): 若 S0/S1 显示机制化分配 + 两阶段 probe 的机制门失败
(service/零候选/JCD 逻辑/预算/DecisionGate), 如实报告并按 E9 同口径披露;
不允许事后改判据。

工程纪律: ODesign 生成缓存 = E8 ∪ E9 ∪ E10 (先见优先; 新生成只写 E10
缓存, append-only); 运行记录 append-only (experiments/results/e10_runs_<stage>.jsonl);
判定书由全量记录每次重算 (e10_verdict_<stage>.json); 确定性 tie-break + 固定种子。

Usage (from ``rna_agent_system/``):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e10_gennav_aptamer.py --stage s0
    ... --stage s1 --resume
    ... --stage s2 --resume
"""
from __future__ import annotations

import argparse
import json
import os
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
from agent_core.calibrated.models import (  # noqa: E402
    CapabilityAssessment,
    CapabilityRecord,
    EvidencePointer,
    PlannedAction,
)
from agent_core.calibrated.self_model import SelfModel  # noqa: E402
from agent_core.llm_config import get_deepseek_llm  # noqa: E402
from agent_core.services.service_manager import (  # noqa: E402
    ensure_services_ready,
    get_services_for_capabilities,
)
from agent_core.workflows.rna_aptamer_design import (  # noqa: E402
    RnaAptamerDesignInput,
    RnaAptamerDesignWorkflow,
)

# ---------------------------------------------------------------------------
# 路径与固定设计常量 (pre-registered, 见 docstring)
# ---------------------------------------------------------------------------

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "targets"
STRUCT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
E1_SUMMARY = RESULTS_DIR / "e1_capability_summary_v2.json"
# 生成缓存: 读 = E8 ∪ E9 ∪ E10 缓存 (先见优先); 写 = 仅 E10 缓存 (append-only)
E8_ODESIGN_CACHE_PATH = RESULTS_DIR / "e8_odesign_cache.jsonl"
E9_ODESIGN_CACHE_PATH = RESULTS_DIR / "e9_odesign_cache.jsonl"
ODESIGN_CACHE_PATH = RESULTS_DIR / "e10_odesign_cache.jsonl"
AUDIT_DIR = RESULTS_DIR / "e10_audit"

# 画像带 + 每带独立约束矩阵 (E9 判据书 §约束矩阵; profile-orthogonal axes 的
# aptamer 版: 带内仅锚定长度可行 — compact→L25/L35, standard→L40/L50,
# extended→L65/L70)
#     profile   长度带     GC 窗          homo    stem
#     compact   25–34 nt   [0.42, 0.62]   < 5     ≤ 8   (RELAX v1 2026-08-12:
#     standard  40–55 nt   [0.40, 0.65]   < 5     ≤ 10   S0 探测显示 stem≤6 在
#     extended  61–80 nt   [0.35, 0.60]   < 6     ≤ 12   Thrombin compact 过严,
#                                                         修订预案第一档 stem+2;
#                                                         relax 后 C 臂 L25 可交付
#                                                         5/5 而 A 臂 L30 仍 4/5)
PROFILES: dict[str, dict] = {
    "compact": {"lo": 25, "hi": 34, "gc_lo": 0.42, "gc_hi": 0.62,
                "homo": 5, "stem": 8},
    "standard": {"lo": 40, "hi": 55, "gc_lo": 0.40, "gc_hi": 0.65,
                 "homo": 5, "stem": 10},
    "extended": {"lo": 61, "hi": 80, "gc_lo": 0.35, "gc_hi": 0.60,
                 "homo": 6, "stem": 12},
}
PROFILE_ORDER = ["compact", "standard", "extended"]

# 修订预案 (预注册): 锁定规则未达时的带内放松档 (stem +2 bp 或 GC 窗放宽 0.02)
RELAX_OPTIONS = [
    {"stem": +2, "gc": 0.0},
    {"stem": +2, "gc": 0.02},
]

D1_MIN_PAIRWISE = 0.15               # 交付级 D1: 两两归一化 Levenshtein ≥ 0.15
GC_UTILITY_TARGET = 0.55             # 效用: |GC − 0.55| 升
DELIVERY_SIZE = 5

# A 臂静态格 / C 臂探测格与预算 (铁律: 两臂每靶原始生成 ≤ 48)
A_GRID_LENGTHS = (30, 50, 80)
A_GRID_SEEDS = (42, 123)
A_N_SAMPLES = 8
# 加宽导航格 (E9 判据书): 每带 ≥2 个格点 — compact 25/30/35, standard 40/50/60,
# extended 65/70/80 (E6 λ bisect 的格增长同机制)
C_LATTICE_LENGTHS = (25, 30, 35, 40, 50, 60, 65, 70, 80)
C_PROBE_SEED = 42
C_PROBE_N = 2
C_REQUEST_SEEDS = (7, 99)
C_REQUEST_N_MAX = 8
C_MAX_REQUEST_GENERATE = 3  # E10: 机制化强化 ≤3 轮 (48 - 18 probe - ≤8 补采)
C_LLM_MAX = 4                 # E10: 仲裁轮 ≤3 + finalize 1
RAW_BUDGET_PER_TARGET = 48
C_PROBE2_BUDGET = 8           # 阶段 2 补采预算 (≤4 长度 × n2, seed 7)
C_PROBE2_SEED = 7

S0_TARGETS = ["Thrombin"]
S1_TARGETS = ["Thrombin", "VEGF", "SARS-CoV-2_Nucleocapsid"]
# S1 新靶点探针 (只跑 A 臂 + C 臂 probe, 测量 A-fail 密度; 判据书 §靶点与面板规则)
S1_PROBE_TARGETS = ["Carbonic_anhydrase_II", "Cytochrome_c", "Myoglobin",
                    "Papain", "Pepsin"]
# S2 面板: 新靶点 A-fail 率 < 30% → 15 靶; 否则 12 靶 (10 旧 + A-fail 密度
# 最高的 2 新; 预注册规则, 见 compute_verdict / main)
S2_NEW_TARGETS = ["Carbonic_anhydrase_II", "Cytochrome_c", "Myoglobin",
                  "Papain", "Pepsin"]
# Ferritin 排除: 确定性 ODesign 零产出边界 (RESUME_CHECKPOINT §4)
# 修订⑤ 2026-08-11: 8 → 10 靶 (+Concanavalin_A, +Chymotrypsinogen)
S2_TARGETS = [
    "Thrombin", "VEGF", "SARS-CoV-2_Nucleocapsid", "Lysozyme",
    "BSA", "MBP", "TNF_alpha", "Trypsin",
    "Concanavalin_A", "Chymotrypsinogen",
]
STAGE_TARGETS = {"s0": S0_TARGETS, "s1": S1_TARGETS, "s2": S2_TARGETS}

E8_REQUIRED_CAPS = [
    "run_odesign_inference",                            # 8012 (GPU)
    "predict_rna_secondary_structure_with_linearfold",  # 8015
]

_FOLD_CACHE: dict[str, dict] = {}
_FIRST_CALL = {"done": False, "seconds": None}  # 进程内首个 ODesign 真实调用墙时


# ---------------------------------------------------------------------------
# 纯函数: 序列约束 (C2/C3/C4 + Levenshtein; C1 为画像带判定)
# ---------------------------------------------------------------------------


def max_homopolymer_run(seq: str) -> int:
    """最长同聚物 run 长度 (nt)。"""
    seq = m._rna(seq)
    best = cur = 0
    prev = ""
    for ch in seq:
        cur = cur + 1 if ch == prev else 1
        prev = ch
        best = max(best, cur)
    return best


def fold(seq: str) -> dict:
    """LinearFold 8015 折叠 (进程内缓存; 复用 E5 同一路径)。"""
    if seq not in _FOLD_CACHE:
        _FOLD_CACHE[seq] = m.linearfold(seq)
    return _FOLD_CACHE[seq]


def _levenshtein(a: str, b: str) -> int:
    """标准 Levenshtein 编辑距离 (DP; 序列 ≤85 nt, 开销可忽略)。"""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (0 if ca == b[j - 1] else 1))
        prev = cur
    return prev[lb]


def normalized_levenshtein(a: str, b: str) -> float:
    """归一化 Levenshtein 距离 = 编辑距离 / max(len(a), len(b))。"""
    a, b = m._rna(a), m._rna(b)
    denom = max(len(a), len(b))
    if denom == 0:
        return 0.0
    return _levenshtein(a, b) / denom


def evaluate_candidate(cand: dict) -> None:
    """单候选约束矩阵评估 (C2/C3/C4 按画像带参数化; C1 按画像带; 就地回填)。"""
    seq = cand["sequence"]
    f = fold(seq)
    gc = m.gc_fraction(seq)
    homo = max_homopolymer_run(seq)
    stem = m.longest_stem_bp(f["structure"])
    cand["length"] = len(seq)
    cand["gc"] = round(gc, 4)
    cand["max_homopolymer_run"] = homo
    cand["longest_stem_bp"] = stem
    cand["mfe"] = float(f["mfe"])
    # 每带独立矩阵 (E9): C1 长度带 ∧ C2 带 GC 窗 ∧ C3 带 homo ∧ C4 带 stem
    cand["constraints"] = {
        "gc": gc, "homopolymer_run": homo, "longest_stem_bp": stem
    }
    cand["matrix_pass"] = {
        prof: (spec["lo"] <= len(seq) <= spec["hi"]
               and spec["gc_lo"] <= gc <= spec["gc_hi"]
               and homo < spec["homo"] and stem <= spec["stem"])
        for prof, spec in PROFILES.items()
    }


def _utility_key(cand: dict) -> tuple:
    """固定效用排序键: 最长 stem 升 → |GC−0.55| 升 → id 升 (确定性 tie-break)。"""
    return (cand["longest_stem_bp"], abs(cand["gc"] - GC_UTILITY_TARGET),
            cand["id"])


def deliver_profile(candidates: list[dict], profile: str) -> dict:
    """机械化交付 (A/C 同一函数 — 同规则铁律): 矩阵通过过滤 → 效用排序 →
    D1 贪心取 top-5; 不足 5 显式 degrade 声明。"""
    passing = [c for c in candidates if c["matrix_pass"][profile]]
    ordered = sorted(passing, key=_utility_key)
    selected: list[dict] = []
    for cand in ordered:
        if all(normalized_levenshtein(cand["sequence"], s["sequence"])
               >= D1_MIN_PAIRWISE for s in selected):
            selected.append(cand)
        if len(selected) == DELIVERY_SIZE:
            break
    dists = [
        normalized_levenshtein(selected[i]["sequence"], selected[j]["sequence"])
        for i in range(len(selected)) for j in range(i + 1, len(selected))
    ]
    min_dist = min(dists) if dists else None
    all_pass = all(c["matrix_pass"][profile] for c in selected)
    d1_pass = bool(min_dist is not None and min_dist >= D1_MIN_PAIRWISE - 1e-12)
    jcd = bool(len(selected) == DELIVERY_SIZE and all_pass and d1_pass)
    degraded = len(selected) < DELIVERY_SIZE
    if degraded:
        # 修订④ 2026-08-11: reason 报告 post-D1 可交付数 (而非仅矩阵通过数)
        spec = PROFILES[profile]
        reason = (f"post-D1 deliverable {len(selected)}/{DELIVERY_SIZE} "
                  f"({len(passing)} matrix-passing in band "
                  f"{spec['lo']}-{spec['hi']}; "
                  f"D1>={D1_MIN_PAIRWISE} greedy keeps {len(selected)}) "
                  f"after budget exhaustion")
    else:
        reason = ""
    return {
        "profile": profile,
        "ids": [c["id"] for c in selected],
        "candidates": [{
            "id": c["id"], "sequence": c["sequence"], "length": c["length"],
            "gc": c["gc"], "longest_stem_bp": c["longest_stem_bp"],
            "abs_gc_dev": round(abs(c["gc"] - GC_UTILITY_TARGET), 4),
        } for c in selected],
        "n_passing_in_band": len(passing),
        "all_pass_matrix": all_pass,
        "d1_min_dist": (round(min_dist, 4) if min_dist is not None else None),
        "d1_pass": d1_pass,
        "jcd_pass": jcd,
        "degraded": degraded,
        "degrade_reason": reason,
    }


# ---------------------------------------------------------------------------
# ODesign 生成 (精确镜像 rna_aptamer_design 工作流路径; 缓存优先)
# ---------------------------------------------------------------------------


def load_odesign_cache() -> dict[str, dict]:
    """E8 缓存合并 E9 缓存 → {key: record} (append-only; 先见优先)。

    ODesign 生成 (target, length, seed, n_samples) → sequences 与约束矩阵
    无关, 故 E8 的既有生成可直接复用; 新格 (L35/L60/L70) 与种子只在 E9
    缓存中, 新生成只写 E9 缓存。
    """
    cache: dict[str, dict] = {}
    for path in (E8_ODESIGN_CACHE_PATH, E9_ODESIGN_CACHE_PATH, ODESIGN_CACHE_PATH):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cache.setdefault(rec["key"], rec)
    return cache


def _cache_key(target_id: str, length: int, seed: int, n_samples: int) -> str:
    return f"{target_id}|L{length}|s{seed}|n{n_samples}"


def _cache_append(rec: dict) -> None:
    ODESIGN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ODESIGN_CACHE_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def _structure_residue_numbers(pdb_path: Path, chain_id: str) -> set[int]:
    """结构链的实际残基编号集合 (biopython; 与 _resolve_protein_length 同解析口径)。"""
    from Bio.PDB import PDBParser

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("prot", str(pdb_path))
    for model in structure:
        for chain in model:
            if chain.id.strip() == (chain_id or "").strip():
                return {r.id[1] for r in chain if not r.id[0].strip()}
    return set()


def prepare_target(target_id: str, registry: Any) -> dict:
    """工作流 Module-1 镜像: 结构解析 + hotspot (JSON known_hotspot_residues
    优先, 否则 identify_protein_binding_hotspots 自动识别) + 蛋白长度。

    修订 (2026-08-11, S1 诊断拍板): JSON known_hotspot_residues 与结构链残基
    编号零交集时 (SARS-CoV-2_Nucleocapsid: 6m3m/A 残基 49..174 vs JSON
    A/44-48 → ODesign 断言 'No hotspot is provided' 确定性零产出, fig5 已标记
    该靶为 explicit-hotspot 边界), 回退为工作流自动识别 (fig4 同路径);
    hotspot_source 记入 prep 与运行记录。仅 Thrombin/Nucleocapsid 两个靶的
    JSON 带 known_hotspot_residues; Thrombin 5/5 在链内, 不受影响。"""
    meta = json.loads((TARGETS_DIR / f"{target_id}.json").read_text(encoding="utf-8"))
    struct = STRUCT_DIR / f"{meta['pdb_id'].lower()}.pdb"
    if not struct.is_file():
        raise FileNotFoundError(f"structure missing for {target_id}: {struct}")
    inp_kwargs: dict[str, Any] = {
        "protein_structure_path": str(struct),
        "chain_id": meta.get("pdb_chain") or "A",
    }
    hotspot_source = "auto_identify"
    known = meta.get("known_hotspot_residues")
    if known:
        known_nums = [int(x.split("/")[1]) for x in known.split(",")]
        resnums = _structure_residue_numbers(struct, inp_kwargs["chain_id"])
        if any(n in resnums for n in known_nums):
            inp_kwargs["hotspot_residues"] = known
            hotspot_source = "known_json"
        else:
            hotspot_source = "auto_identify_fallback_known_out_of_structure"
    inp = RnaAptamerDesignInput(**inp_kwargs)
    wf = RnaAptamerDesignWorkflow(registry)
    protein_path, hotspot, seq_len = wf._prepare_target_module(inp)
    if not protein_path or not hotspot:
        raise RuntimeError(f"target preparation failed for {target_id} "
                           f"(structure/hotspot/length)")
    return {"meta": meta, "wf": wf, "inp": inp, "protein_path": protein_path,
            "hotspot": hotspot, "protein_seq_len": seq_len,
            "hotspot_source": hotspot_source}


def odesign_generate(prep: dict, target_id: str, length: int, seed: int,
                     n_samples: int, cache: dict[str, dict],
                     *, log: Any = print) -> dict:
    """一次 ODesign 生成 (工作流 Module-2 镜像, 缓存优先)。

    缓存键 = (target, aptamer_length, seed, n_samples); 命中即返序列 (零服务
    调用)。未命中走 _generate_aptamer_module (build_odesign_aptamer_input_json
    → run_odesign_inference → extract_rna_sequence_from_cif → dedupe) 并落缓存。
    """
    key = _cache_key(target_id, length, seed, n_samples)
    if key in cache:
        rec = cache[key]
        log(f"    [cache] {key}: {len(rec['sequences'])} seqs (hit)", flush=True)
        return {"key": key, "aptamer_length": length, "seed": seed,
                "n_samples": n_samples, "sequences": list(rec["sequences"]),
                "wall_seconds": 0.0, "cache_hit": True, "error": None}
    t0 = time.perf_counter()
    error = None
    sequences: list[str] = []
    try:
        cands = prep["wf"]._generate_aptamer_module(
            prep["protein_path"], prep["hotspot"], prep["inp"],
            protein_seq_len=prep["protein_seq_len"],
            length_override=length, seeds_override=[seed],
            samples_override=n_samples,
        )
        sequences = [m._rna(c.sequence) for c in cands]
    except Exception as exc:  # noqa: BLE001 - 单次生成失败不阻断, 记录为异常
        error = f"{type(exc).__name__}: {exc}"
        log(f"    [error] {key}: {error}", flush=True)
    wall = time.perf_counter() - t0
    if not _FIRST_CALL["done"]:
        _FIRST_CALL["done"] = True
        _FIRST_CALL["seconds"] = wall
        log(f"    [timing] FIRST ODesign call {key}: {wall:.1f}s", flush=True)
    rec = {"key": key, "target_id": target_id, "aptamer_length": length,
           "seed": seed, "n_samples": n_samples, "n_sequences": len(sequences),
           "sequences": sequences, "wall_seconds": round(wall, 2),
           "error": error, "timestamp": m.now_iso()}
    _cache_append(rec)
    cache[key] = rec
    log(f"    [odesign] {key}: {len(sequences)} seqs in {wall:.1f}s", flush=True)
    return {"key": key, "aptamer_length": length, "seed": seed,
            "n_samples": n_samples, "sequences": sequences,
            "wall_seconds": round(wall, 2), "cache_hit": False, "error": error}


def _pool_add(pool: list[dict], seen: set[str], gear: dict,
              sequences: list[str]) -> int:
    """序列去重入池 (keep-first, 确定性); 返回新增 unique 数。"""
    added = 0
    for idx, seq in enumerate(sequences):
        if not seq or seq in seen:
            continue
        seen.add(seq)
        pool.append({
            "id": f"L{gear['aptamer_length']}s{gear['seed']}n{gear['n_samples']}"
                  f"i{idx}",
            "sequence": seq,
            "gear": {"aptamer_length": gear["aptamer_length"],
                     "seed": gear["seed"], "n_samples": gear["n_samples"],
                     "sample_idx": idx},
        })
        added += 1
    return added


# ---------------------------------------------------------------------------
# E1 证据预载 + DecisionGate 演示 (C 臂; task_type="rna_aptamer_design")
# ---------------------------------------------------------------------------


def build_e10_self_model_records() -> list[CapabilityRecord]:
    """SelfModel 行: E1 v2 真实证据 (3 结构 oracle × 6 靶, 全部 ranking/screening
    FAILED), task_type 固定 "rna_aptamer_design" (E8 任务族)。"""
    summary = json.loads(E1_SUMMARY.read_text(encoding="utf-8"))
    evidence = [EvidencePointer(
        kind="summary_json",
        path="experiments/results/e1_capability_summary_v2.json",
        note="E1 v2 oracle capability profiling (aptamer task family)",
    )]
    records: dict[tuple[str, str], CapabilityRecord] = {}
    for cell_key, cell in summary["part_a_per_oracle_target"].items():
        oracle, target = [part.strip() for part in cell_key.split("|")]
        rec = records.setdefault(
            (oracle, target),
            CapabilityRecord(oracle=oracle, task_type="rna_aptamer_design",
                             target_family=target),
        )
        rec.capabilities["screening"] = CapabilityAssessment(
            grade="verified" if cell["screening_pass"] else "failed",
            confidence=1.0,
            metrics={"auroc": cell["screening_auroc"]},
            evidence=evidence,
            profiled_at=summary.get("date", ""),
        )
        rec.capabilities["ranking"] = CapabilityAssessment(
            grade="verified" if cell["ranking_pass"] else "failed",
            confidence=1.0,
            metrics={"spearman_rho": cell["ranking_spearman_rho"]},
            evidence=evidence,
            profiled_at=summary.get("date", ""),
        )
    return list(records.values())


def decision_gate_demonstration(gate: DecisionGate, target_id: str) -> dict:
    """E8 必演: 动作 'rank candidates by egarps_native_probability'
    (use=ranking_objective) 在 E1 证据预载的 SelfModel 下必须 forbidden
    (verdict=reject)。DecisionGate.review 自动落 audit 'gate_decision'。"""
    action = PlannedAction(
        action_id="e9_demo_rank_by_egarps_native_probability",
        kind="oracle_lookup",
        oracle="egarps_native_probability",
        use="ranking_objective",
    )
    decision = gate.review([action], task_type="rna_aptamer_design",
                           target_family=target_id)[0]
    return {
        "action": "rank candidates by egarps_native_probability",
        "use": "ranking_objective",
        "oracle": "egarps_native_probability",
        "task_type": "rna_aptamer_design",
        "target_family": target_id,
        "verdict": decision.verdict,
        "reason": decision.reason,
        "forbidden": decision.verdict == "reject",
    }


# ---------------------------------------------------------------------------
# 臂 A: 规则交付作用于静态格 (零 LLM)
# ---------------------------------------------------------------------------


def run_arm_a(stage: str, target_id: str, registry: Any,
              cache: dict[str, dict], *, log: Any = print) -> dict:
    t0 = time.perf_counter()
    prep = prepare_target(target_id, registry)
    pool: list[dict] = []
    seen: set[str] = set()
    gears: list[dict] = []
    raw_spent = 0
    for length in A_GRID_LENGTHS:          # 首个调用 = (L30, s42, n8) 计时锚点
        for seed in A_GRID_SEEDS:
            g = odesign_generate(prep, target_id, length, seed, A_N_SAMPLES,
                                 cache, log=log)
            raw_spent += g["n_samples"]
            g["n_unique_added"] = _pool_add(pool, seen, g, g["sequences"])
            gears.append(g)
    for cand in pool:
        evaluate_candidate(cand)
    deliveries = {p: deliver_profile(pool, p) for p in PROFILE_ORDER}
    jcd_bits = {p: deliveries[p]["jcd_pass"] for p in PROFILE_ORDER}
    log(f"  [A:{target_id}] raw={raw_spent} unique={len(pool)} "
        f"jcd={jcd_bits}", flush=True)
    return {
        "stage": stage, "target_id": target_id, "arm": "A", "success": True,
        "timestamp": m.now_iso(),
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
        "errors": [g["error"] for g in gears if g["error"]],
        "hotspot_residues": prep["hotspot"],
        "hotspot_source": prep["hotspot_source"],
        "pool": {
            "gears": gears, "n_raw_samples": raw_spent,
            "n_unique_candidates": len(pool),
            "first_odesign_call_seconds": _FIRST_CALL["seconds"],
        },
        "candidates": pool,
        "deliveries": deliveries,
        "jcd": {p: deliveries[p]["jcd_pass"] for p in PROFILE_ORDER},
        "e2e": all(deliveries[p]["jcd_pass"] for p in PROFILE_ORDER),
        "degraded_profiles": [
            {"profile": p, "reason": deliveries[p]["degrade_reason"],
             "delivered": len(deliveries[p]["ids"]), "source": "rule"}
            for p in PROFILE_ORDER if deliveries[p]["degraded"]
        ],
        "llm_calls": 0, "llm_log": [], "request_generate_calls": 0,
    }


# ---------------------------------------------------------------------------
# 臂 C: 门控约束导航 (探测 → LLM 靶向生成 ≤2 轮 → 机械化交付)
# ---------------------------------------------------------------------------

ACTION_SYSTEM = """\
You are the constraint-navigation agent of an RNA aptamer design system operating
at the GENERATION layer. The generator is ODesign (structure-guided); its gears
are (aptamer_length, seed, n_samples). A static probe has already sampled the
length lattice {25,30,35,40,50,60,65,70,80} with seed 42, n_samples=2 (18 raw
samples). Profiles (delivery bands by candidate length) with PER-PROFILE
constraint matrices:
  compact  25-34 nt: GC in [0.42,0.62], homopolymer < 5 nt, longest stem <= 6 bp
  standard 40-55 nt: GC in [0.40,0.65], homopolymer < 5 nt, longest stem <= 10 bp
  extended 61-80 nt: GC in [0.35,0.60], homopolymer < 6 nt, longest stem <= 12 bp
Each profile must be delivered exactly 5 candidates that ALL pass its matrix
and satisfy D1 (pairwise normalized Levenshtein >= 0.15 within the delivered
batch of 5).
IMPORTANT: the per-profile stem caps make long lengths (60-80 nt) hard for the
extended band and short lengths (25-35 nt) the only viable gears for the
compact band. Probe feasibility is per (length, band): a length is feasible
for a profile if at least one of its raw samples passes that profile's matrix.
Spend reinforcement rounds on the scarce bands' ANCHOR lengths (compact: 25/35,
extended: 65/70) with new seeds rather than on already-covered lengths.
Delivery is MECHANIZED by the system (identical to the rule-based arm): matrix-
passing candidates in band are ranked by utility (longest stem ascending, then
|GC-0.55| ascending), then top-5 are greedily selected under D1. Your leverage
is GENERATION ONLY: decide which gears to sample so all three profiles become
servable. Structure-oracle scores (egarps/proteinx/rhofold) FAILED capability
profiling for this task family and are FORBIDDEN for ranking/selection.
Each round reply ONE JSON action:
{"action": "request_generate", "aptamer_length": <one of 25,30,35,40,50,60,65,70,80>,
 "seed": <7 or 99>, "n_samples": <1-8>, "reason": "..."}
    At most 4 request_generate actions; raw budget probe(18) + requests <= 48;
    the (length, seed) pair must be NEW (not already sampled).
    Read the profile table: profiles with gap_to_5 > 0 are UNDER-SERVED.
    Reinforce an under-served band by requesting NEW seeds at lengths inside
    that band (compact 25-34, standard 40-55, extended 61-80), preferring the
    band's anchor lengths (compact 25/35, standard 40/50/60, extended 65/70) —
    each new seed adds an independent diversity class; re-sampling a covered
    band wastes budget.
{"action": "select", "profiles": {"<profile>": ["<candidate_id>", ...5 ids]},
 "rationale": "..."}
    Optional preference expression; ids MUST pass the matrix for that profile
    (constraint gate). Final delivery is re-derived mechanistically regardless.
{"action": "sort", "profiles": {"<profile>": {"ranking": ["<5 ids>"],
 "arbitration": [{"pair": ["<idA>", "<idB>"], "layer": 1|2,
 "evidence": "<metric key(s) cited>"}]}}, "rationale": "..."}
    Tie-break arbitration only. Layers: 1=secondary structure (C4_longest_stem),
    2=sequence composition (C2_gc, C3_max_homopolymer_run).
{"action": "degrade", "profile": "<profile>", "reason": "..."}
    Explicitly declare a profile unservable (only after budget exhaustion).
{"action": "finalize", "rationale": "..."}
    End navigation; mechanized delivery is computed for all profiles.
IMPORTANT: reply with JSON only, no prose outside the JSON object.
"""


def _band_of(length: int) -> str | None:
    """长度所属画像带 (无归属返回 None; 格内长度必有所属)。"""
    for p, spec in PROFILES.items():
        if spec["lo"] <= length <= spec["hi"]:
            return p
    return None


def _gear_table(pool: list[dict], gears: list[dict]) -> str:
    """修订③: 每 gear 按带归类并给出带内矩阵通过数 (已试产出可见)。"""
    rows = ["gear (L=len,s=seed,n=n_samples) | band | raw | unique_added | "
            "band_matrix_passing"]
    for g in gears:
        length, seed, n = g["aptamer_length"], g["seed"], g["n_samples"]
        band = _band_of(length)
        cands = [c for c in pool
                 if c["gear"]["aptamer_length"] == length
                 and c["gear"]["seed"] == seed and c["gear"]["n_samples"] == n]
        n_pass = sum(1 for c in cands
                     if band and c["matrix_pass"][band])
        rows.append(f"L{length}s{seed}n{n} | {band} | {n} | "
                    f"{g.get('n_unique_added', 0)} | {n_pass}")
    return "\n".join(rows)


def _profile_status(pool: list[dict]) -> str:
    """修订③: 每画像 in-band 总数 / 矩阵通过数 / 当前 D1 可交付数 / gap_to_5。"""
    rows = ["profile | band | in_band | matrix_passing | D1_deliverable_now | "
            "gap_to_5"]
    for p in PROFILE_ORDER:
        spec = PROFILES[p]
        lo, hi = spec["lo"], spec["hi"]
        in_band = sum(1 for c in pool if lo <= c["length"] <= hi)
        d = deliver_profile(pool, p)
        gap = max(0, DELIVERY_SIZE - len(d["ids"]))
        rows.append(f"{p} | {lo}-{hi} | {in_band} | "
                    f"{d['n_passing_in_band']} | {len(d['ids'])} | {gap}")
    return "\n".join(rows)


def _candidate_table(pool: list[dict]) -> str:
    rows = ["id | len | gc | homo_run | stem_bp | mfe | "
            "pass_compact/standard/extended"]
    for c in sorted(pool, key=lambda x: x["id"]):
        pb = "/".join("1" if c["matrix_pass"][p] else "0" for p in PROFILE_ORDER)
        rows.append(f"{c['id']} | {c['length']} | {c['gc']:.3f} | "
                    f"{c['max_homopolymer_run']} | {c['longest_stem_bp']} | "
                    f"{c['mfe']:.1f} | {pb}")
    return "\n".join(rows)


def _observation_c(target_id: str, pool: list[dict], gears: list[dict],
                   raw_spent: int, requests_used: int, llm_calls: int,
                   history: list[dict], gate_feedback: str) -> str:
    return (
        f"Target {target_id}. Round {len(history) + 1}.\n"
        f"Delivery rule (mechanized, same as rule arm): exactly {DELIVERY_SIZE} "
        f"candidates per profile, utility-ranked (longest stem asc, then "
        f"|GC-0.55| asc), D1>={D1_MIN_PAIRWISE} greedy selection.\n"
        f"Budget: raw samples {raw_spent}/{RAW_BUDGET_PER_TARGET} remaining "
        f"{RAW_BUDGET_PER_TARGET - raw_spent}; "
        f"request_generate {requests_used}/{C_MAX_REQUEST_GENERATE} "
        f"(new seeds only {list(C_REQUEST_SEEDS)}, n_samples<= {C_REQUEST_N_MAX}, "
        f"length in {list(C_LATTICE_LENGTHS)}); "
        f"LLM calls {llm_calls}/{C_LLM_MAX}.\n\n"
        f"Gear table (yields by band):\n{_gear_table(pool, gears)}\n\n"
        f"Profile servability (gap_to_5 > 0 = under-served):\n"
        f"{_profile_status(pool)}\n\n"
        f"Candidate table:\n{_candidate_table(pool)}\n\n"
        f"Round history:\n"
        + (json.dumps(history, ensure_ascii=False) if history else "(none)")
        + (f"\n\nGATE FEEDBACK (hard constraints, do not contest):\n{gate_feedback}"
           if gate_feedback else "")
    )


def _laplace_rate(pool: list[dict], length: int) -> float:
    """laplace 平滑通过率估计: (passers + 1) / (n + 2), 任意带通过。"""
    cands = [c for c in pool if c["gear"]["aptamer_length"] == length]
    n = len(cands)
    k = sum(1 for c in cands if any(c["matrix_pass"].values()))
    return (k + 1) / (n + 2)


def _mechanized_proposals(pool: list[dict], gears: list[dict],
                          raw_spent: int) -> tuple[list[dict], dict[str, int]]:
    """机制化提案 (E10 判据书): 对每个未采样 (L, seed in {7,99}) gear 计算
    gap 加权期望修复 (laplace 平滑通过率 x n), 按修复分排序, 返回 top-3。
    LLM 只能从中仲裁, 不能指定机制未提议的 gear。"""
    passers = {p: len(deliver_profile(pool, p)["ids"]) for p in PROFILE_ORDER}
    gaps = {p: max(0, DELIVERY_SIZE - passers[p]) for p in PROFILE_ORDER}
    cand: list[dict] = []
    n = min(C_REQUEST_N_MAX, RAW_BUDGET_PER_TARGET - raw_spent)
    if n <= 0:
        return [], gaps
    for L in C_LATTICE_LENGTHS:
        if _band_of(L) is None:
            continue  # 格内缝隙长度 (L60 不在任何带) 不可作为强化 gear
        for s in C_REQUEST_SEEDS:
            if any(g["aptamer_length"] == L and g["seed"] == s for g in gears):
                continue
            rate = _laplace_rate(pool, L)
            exp_new = rate * n
            score = 0.0
            for prof, spec in PROFILES.items():
                if spec["lo"] <= L <= spec["hi"]:
                    score += min(gaps[prof], exp_new)
            cand.append({
                "length": L, "seed": s, "n_samples": n,
                "expected_passers": round(exp_new, 2),
                "repair_score": round(score, 2),
                "band": _band_of(L),
            })
    # 带优先排序 (E10 S0 教训): 先修缺口最大的带, 带内选期望修复最高 —
    # 跨带比较期望值会把预算吸到"期望高"的带, 饿死缺口大但通过率低的带
    # (E9 c=8 的预算竞争在机制化里的重演)。
    cand.sort(key=lambda g: (-gaps[g["band"]], -g["repair_score"],
                             -g["expected_passers"], g["length"], g["seed"]))
    return cand[:3], gaps


E10_ARBITRATION_SYSTEM = """\
You are the arbitration stage of an RNA aptamer constraint-navigation system.
A mechanized allocator proposes reinforcement gears, ranked by expected repair
of the under-served profiles (per-profile matrix pass rates estimated from the
probe). Your role is NARROW: approve one proposal, or declare a profile
unservable, or finalize. You may NOT propose your own (length, seed) gears.
Current state and proposals are given below.
Reply ONE JSON action:
{"action": "approve", "proposal_index": 0|1|2, "reason": "<one sentence>"}
{"action": "degrade", "profile": "<compact|standard|extended>", "reason": "<one sentence>"}
{"action": "finalize", "reason": "<one sentence>"}
Rules: the proposals are ALREADY ranked by the mechanized allocator (largest
remaining gap first, then expected repair). Default to proposal_index 0;
choose a different index only with a concrete reason (e.g. that band's probe
pass rate is near zero). Degrade only when every length of that band shows
near-zero probe pass rate; finalize when all profiles are servable or budget
is exhausted."""


def run_arm_c(stage: str, target_id: str, registry: Any, cache: dict[str, dict],
              llm: Any, *, log: Any = print) -> dict:
    t0 = time.perf_counter()
    prep = prepare_target(target_id, registry)

    audit = AuditTrail(AUDIT_DIR / f"{stage}_{target_id}_C.jsonl")
    self_model = SelfModel(audit=audit)
    for rec in build_e10_self_model_records():
        self_model.update(rec)  # E1 v2 判据预载 (audit: self_model_update)
    gate = DecisionGate(self_model, audit=audit)
    demo = decision_gate_demonstration(gate, target_id)
    log(f"  [C:{target_id}] DecisionGate demo: "
        f"'{demo['action']}' -> {demo['verdict']} "
        f"(forbidden={demo['forbidden']})", flush=True)

    # ── 阶段 1 probe: 长度格 × seed 42 × n=2 (18 raw) ──
    pool: list[dict] = []
    seen: set[str] = set()
    gears: list[dict] = []
    raw_spent = 0
    for length in C_LATTICE_LENGTHS:
        g = odesign_generate(prep, target_id, length, C_PROBE_SEED, C_PROBE_N,
                             cache, log=log)
        raw_spent += g["n_samples"]
        g["n_unique_added"] = _pool_add(pool, seen, g, g["sequences"])
        g["probe"] = True
        gears.append(g)
    for cand in pool:
        evaluate_candidate(cand)
    probe_feasibility = [
        {"aptamer_length": g["aptamer_length"], "seed": g["seed"],
         "n_samples": g["n_samples"],
         "n_passing_any_band": sum(
             1 for c in pool
             if c["gear"]["aptamer_length"] == g["aptamer_length"]
             and c["gear"]["seed"] == g["seed"]
             and any(c["matrix_pass"].values())),
         "feasible": any(
             any(c["matrix_pass"].values()) for c in pool
             if c["gear"]["aptamer_length"] == g["aptamer_length"]
             and c["gear"]["seed"] == g["seed"])}
        for g in gears
    ]
    log(f"  [C:{target_id}] probe1: raw={raw_spent} unique={len(pool)} "
        f"feasible={[f['aptamer_length'] for f in probe_feasibility if f['feasible']]}",
        flush=True)

    # ── 强化轮 0 (机制化补采, 无 LLM): gap>0 带内通过者<2 的长度 × s7 × n2
    #    (预算 ≤8 raw; 并入强化预算, 与可行性模拟的 18+30 划分一致) ──
    probe2_gears: list[dict] = []
    for prof in PROFILE_ORDER:
        spec = PROFILES[prof]
        in_band_lens = [L for L in C_LATTICE_LENGTHS
                        if spec["lo"] <= L <= spec["hi"]]
        for L in in_band_lens:
            if raw_spent + 2 > RAW_BUDGET_PER_TARGET:
                break
            if len(probe2_gears) >= C_PROBE2_BUDGET // 2:
                break
            passers_L = sum(1 for c in pool
                            if c["gear"]["aptamer_length"] == L
                            and any(c["matrix_pass"].values()))
            if passers_L >= 2:
                continue
            g = odesign_generate(prep, target_id, L, C_PROBE2_SEED, 2,
                                 cache, log=log)
            raw_spent += g["n_samples"]
            g["n_unique_added"] = _pool_add(pool, seen, g, g["sequences"])
            g["probe2"] = True
            gears.append(g)
            probe2_gears.append({"aptamer_length": L, "seed": g["seed"],
                                 "n_samples": g["n_samples"]})
            for cand in pool:
                if "matrix_pass" not in cand:
                    evaluate_candidate(cand)
    log(f"  [C:{target_id}] reinforce0 (mechanized probe2): "
        f"{len(probe2_gears)} lengths "
        f"({[g['aptamer_length'] for g in probe2_gears]}) raw={raw_spent}",
        flush=True)

    # ── 机制化强化循环 (≤3 轮; LLM 仲裁 ≤4 调用) ──
    history: list[dict] = []
    llm_log: list[dict] = []
    llm_degrades: list[dict] = []
    llm_calls = 0
    requests_used = 0
    feedback = ""

    while requests_used < C_MAX_REQUEST_GENERATE and raw_spent < RAW_BUDGET_PER_TARGET:
        proposals, gaps = _mechanized_proposals(pool, gears, raw_spent)
        if not proposals or all(g <= 0 for g in gaps.values()):
            break
        if llm_calls >= C_LLM_MAX:
            break
        observation = (
            f"profiles status (delivered/gap): "
            + ", ".join(f"{p}: {DELIVERY_SIZE - gaps[p]}/5 (gap {gaps[p]})"
                        for p in PROFILE_ORDER)
            + f"\nraw spent: {raw_spent}/{RAW_BUDGET_PER_TARGET}; "
            f"reinforcement rounds used: {requests_used}/{C_MAX_REQUEST_GENERATE}"
        )
        proposals_txt = "\n".join(
            f"[{i}] L{p['length']} seed {p['seed']} n={p['n_samples']} "
            f"band={p['band']} expected_passers={p['expected_passers']} "
            f"repair_score={p['repair_score']}"
            for i, p in enumerate(proposals))
        action = m._llm_invoke(
            llm, E10_ARBITRATION_SYSTEM,
            f"current state:\n{observation}\n\nmechanized proposals:\n"
            f"{proposals_txt}\n\n{feedback}",
        )
        llm_calls += 1
        kind = str(action.get("action", ""))
        llm_log.append({"round": llm_calls, "action": kind, "payload": action,
                        "proposals": proposals})
        history.append({"action": kind, "payload": action})
        if kind == "approve":
            try:
                idx = int(action.get("proposal_index", -1))
                prop = proposals[idx]
            except (TypeError, ValueError, IndexError):
                feedback = ("approve requires proposal_index in "
                            f"[0, {len(proposals) - 1}]")
                continue
            # 闸 5 校验 (机制化 gear 必过; 防御性保留)
            if any(g["aptamer_length"] == prop["length"] and g["seed"] == prop["seed"]
                   for g in gears):
                feedback = "proposal already sampled; re-arbitrate"
                continue
            if raw_spent + prop["n_samples"] > RAW_BUDGET_PER_TARGET:
                feedback = "proposal exceeds remaining raw budget"
                continue
            decisions = gate.review(
                [PlannedAction(action_id=f"e10_req_{requests_used}",
                               kind="oracle_lookup", oracle=None, use="none")],
                task_type="rna_aptamer_design", target_family=target_id,
            )
            if decisions[0].verdict not in ("allow",):
                feedback = f"DecisionGate: {decisions[0].verdict}"
                continue
            g = odesign_generate(prep, target_id, prop["length"], prop["seed"],
                                 prop["n_samples"], cache, log=log)
            raw_spent += g["n_samples"]
            g["n_unique_added"] = _pool_add(pool, seen, g, g["sequences"])
            g["probe"] = False
            gears.append(g)
            for cand in pool:
                if "matrix_pass" not in cand:
                    evaluate_candidate(cand)
            audit.record("request_generate", {
                "aptamer_length": prop["length"], "seed": prop["seed"],
                "n_samples": prop["n_samples"], "mechanized": True,
                "reason": str(action.get("reason", "")),
                "requests_used": requests_used, "raw_spent": raw_spent,
                "n_unique_added": g["n_unique_added"],
            })
            requests_used += 1
            feedback = ""
        elif kind == "degrade":
            llm_degrades.append({"profile": action.get("profile"),
                                 "reason": str(action.get("reason", ""))})
            audit.record("budget_event", {"kind": "degrade_declared_by_llm",
                                          "profile": action.get("profile"),
                                          "reason": str(action.get("reason", ""))})
            feedback = ""
        elif kind == "finalize":
            break
        else:
            feedback = ("invalid action; must be approve | degrade | finalize")

    # ── 机械化交付 (与 A 臂同一函数) + 显式 degrade 声明 ──
    deliveries = {p: deliver_profile(pool, p) for p in PROFILE_ORDER}
    degraded = []
    for p in PROFILE_ORDER:
        if deliveries[p]["degraded"]:
            llm_declared = any(d["profile"] == p for d in llm_degrades)
            degraded.append({
                "profile": p, "reason": deliveries[p]["degrade_reason"],
                "declared_by_llm": llm_declared,
            })
    jcd_bits = {p: deliveries[p]["jcd_pass"] for p in PROFILE_ORDER}
    log(f"  [C:{target_id}] jcd={jcd_bits} raw={raw_spent} unique={len(pool)} "
        f"llm={llm_calls} req={requests_used}", flush=True)
    return {
        "stage": stage, "target_id": target_id, "arm": "C", "success": True,
        "timestamp": m.now_iso(),
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
        "errors": [g["error"] for g in gears if g["error"]],
        "hotspot_residues": prep["hotspot"],
        "hotspot_source": prep["hotspot_source"],
        "pool": {
            "gears": gears, "n_raw_samples": raw_spent,
            "n_unique_candidates": len(pool),
            "first_odesign_call_seconds": _FIRST_CALL["seconds"],
            "probe2_gears": probe2_gears,
        },
        "candidates": pool,
        "deliveries": deliveries,
        "jcd": jcd_bits,
        "e2e": all(deliveries[p]["jcd_pass"] for p in PROFILE_ORDER),
        "degraded_profiles": degraded,
        "llm_calls": llm_calls,
        "llm_log": llm_log,
        "history": history,
        "request_generate_calls": requests_used,
        "decision_gate_demonstration": demo,
        "probe_feasibility": probe_feasibility,
    }


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


def write_record(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def done_keys(records: list[dict]) -> set[tuple[str, str, str]]:
    return {(r["stage"], r["target_id"], r["arm"]) for r in records
            if r.get("success")}


def _deliverable_count(cands: list[dict], profile: str) -> int:
    """合并池某长度子集在 *profile* 矩阵下可交付候选数 (D1 贪心同 deliver_profile)。"""
    return len(deliver_profile(cands, profile)["ids"])


def matrix_lock_measure(latest: dict) -> dict:
    """矩阵锁定测量 (判据书 §锁定规则): 对每个 (target, profile) 计算
    A 格可交付数 (A 臂全池, 即 {30,50,80} 格) 与合并池 (A+C 全部 gear) 各格内
    长度的最佳可交付数。预注册判据:
      (a) A 格失败 ≥ 8/30; (b) A-fail 中 ≥ 80% 可导航 (某格内长度可交付 ≥ 5);
      (c) HER2 类 (A-fail 且不可导航) 替换或披露。
    未达 → 修订预案 RELAX_OPTIONS (带内 stem +2 bp / GC 窗 +0.02) 逐档放松重测。
    """
    targets = sorted({t for t, _ in latest})
    cells = []
    for t in targets:
        a_cands = latest[(t, "A")]["candidates"] if (t, "A") in latest else []
        c_cands = latest[(t, "C")]["candidates"] if (t, "C") in latest else []
        merged = a_cands + c_cands
        for prof in PROFILE_ORDER:
            a_del = _deliverable_count(a_cands, prof)
            best, best_L = 0, None
            for L in C_LATTICE_LENGTHS:
                d = _deliverable_count(
                    [c for c in merged if c["gear"]["aptamer_length"] == L], prof)
                if d > best:
                    best, best_L = d, L
            cells.append({
                "target_id": t, "profile": prof,
                "a_deliverable": a_del,
                "best_lattice_length": best_L, "best_deliverable": best,
                "navigable": best >= DELIVERY_SIZE,
            })
    a_fail = [c for c in cells if c["a_deliverable"] < DELIVERY_SIZE]
    navigable = [c for c in a_fail if c["navigable"]]
    her2 = [c for c in a_fail if not c["navigable"]]
    n_fail = len(a_fail)
    nav_frac = len(navigable) / n_fail if n_fail else 1.0
    crit_a = n_fail >= 8
    crit_b = nav_frac >= 0.8
    if crit_a and crit_b:
        action = "lock"
    elif crit_a or crit_b:
        action = f"relax -> {RELAX_OPTIONS[0]}"
    else:
        action = f"relax -> {RELAX_OPTIONS[1]}"
    return {
        "measured_from": "latest e9 run records (merged A+C pools)",
        "matrix": {prof: {k: v for k, v in spec.items()}
                   for prof, spec in PROFILES.items()},
        "a_fail_cells": n_fail, "n_cells": len(cells),
        "navigable_repairs": len(navigable),
        "navigable_fraction_of_afail": round(nav_frac, 3),
        "her2_class_cells": [f"{c['target_id']}/{c['profile']}"
                             for c in her2],
        "criteria": {"a_fail_ge_8": crit_a,
                     "navigable_ge_0.8_of_afail": crit_b},
        "recommended_action": action,
        "per_cell": cells,
    }


def compute_verdict(stage: str, runs_path: Path) -> dict:
    """判定书: 由 e10_runs_<stage>.jsonl 全量记录重算 (同 (target, arm) 后者优先,
    确定性按文件序)。"""
    records = load_records(runs_path)
    latest: dict[tuple[str, str], dict] = {}
    for r in records:
        if r.get("success") and r.get("stage") == stage:
            latest[(r["target_id"], r["arm"])] = r
    targets = sorted({t for t, _ in latest})
    paired_targets = [t for t in targets
                      if (t, "A") in latest and (t, "C") in latest]

    # ── 主终点: per-profile JCD C vs A 配对 McNemar (精确, 双侧) ──
    pairs = []
    for t in paired_targets:
        for p in PROFILE_ORDER:
            pairs.append({
                "target_id": t, "profile": p,
                "A_jcd": bool(latest[(t, "A")]["jcd"].get(p)),
                "C_jcd": bool(latest[(t, "C")]["jcd"].get(p)),
            })
    b = sum(1 for pr in pairs if pr["C_jcd"] and not pr["A_jcd"])
    c_ = sum(1 for pr in pairs if not pr["C_jcd"] and pr["A_jcd"])
    p_val = float(scipy_stats.binomtest(min(b, c_), b + c_, 0.5,
                                        alternative="two-sided").pvalue) \
        if b + c_ > 0 else 1.0
    c_e2e = mean(bool(latest[(t, "C")]["e2e"]) for t in paired_targets) \
        if paired_targets else 0.0
    a_e2e = mean(bool(latest[(t, "A")]["e2e"]) for t in paired_targets) \
        if paired_targets else 0.0
    primary_pass = bool(p_val < 0.05 and c_e2e >= 0.8)

    # ── 次级 (披露) ──
    c_delivered_pass = c_delivered_total = 0
    for t in paired_targets:
        rec = latest[(t, "C")]
        by_id = {cd["id"]: cd for cd in rec["candidates"]}
        for p in PROFILE_ORDER:
            for cid in rec["deliveries"][p]["ids"]:
                c_delivered_total += 1
                if by_id[cid]["matrix_pass"][p]:
                    c_delivered_pass += 1
    c_matrix_rate = (c_delivered_pass / c_delivered_total) \
        if c_delivered_total else None
    budget_violations = []
    for t in paired_targets:
        rec = latest[(t, "C")]
        if rec["llm_calls"] > C_LLM_MAX:
            budget_violations.append(f"{t}: llm_calls {rec['llm_calls']} > {C_LLM_MAX}")
        if rec["request_generate_calls"] > C_MAX_REQUEST_GENERATE:
            budget_violations.append(
                f"{t}: request_generate {rec['request_generate_calls']} > "
                f"{C_MAX_REQUEST_GENERATE}")
        if rec["pool"]["n_raw_samples"] > RAW_BUDGET_PER_TARGET:
            budget_violations.append(
                f"{t}: C raw {rec['pool']['n_raw_samples']} > "
                f"{RAW_BUDGET_PER_TARGET}")
        ra = latest[(t, "A")]
        if ra["pool"]["n_raw_samples"] > RAW_BUDGET_PER_TARGET:
            budget_violations.append(
                f"{t}: A raw {ra['pool']['n_raw_samples']} > "
                f"{RAW_BUDGET_PER_TARGET}")
    degraded_total = sum(len(latest[(t, "C")]["degraded_profiles"])
                         for t in paired_targets)

    # ── 机制块 (S0/S1 staging 判据) ──
    gear_errors = [f"{t}/{a}: {e}" for (t, a), r in sorted(latest.items())
                   for e in r.get("errors", [])]
    zero_candidate = [t for t in paired_targets
                      if latest[(t, "A")]["pool"]["n_unique_candidates"] == 0]
    demos = [{"target_id": t,
              "verdict": latest[(t, "C")]["decision_gate_demonstration"]["verdict"],
              "forbidden": latest[(t, "C")]["decision_gate_demonstration"]["forbidden"]}
             for t in paired_targets]
    demo_ok = bool(demos) and all(d["forbidden"] for d in demos)
    first_call = next(
        (r["pool"].get("first_odesign_call_seconds")
         for (_, _), r in sorted(latest.items())
         if r["pool"].get("first_odesign_call_seconds") is not None), None)
    if first_call is None:
        # 回退: 缓存记录内的墙时 (resume/缓存命中场景下进程内锚点为 None)
        cache_rec = load_odesign_cache().get(
            _cache_key("Thrombin", 30, 42, A_N_SAMPLES))
        if cache_rec:
            first_call = cache_rec.get("wall_seconds")
    mechanism = {
        "all_gear_calls_ok": not gear_errors,
        "gear_errors": gear_errors,
        "zero_candidate_targets": zero_candidate,
        "no_zero_candidate_anomaly": not zero_candidate,
        "budget_violations": budget_violations,
        "budget_compliance": not budget_violations,
        "decision_gate_demonstrations": demos,
        "decision_gate_demo_forbidden": demo_ok,
        "first_odesign_call_seconds": first_call,
    }
    mechanism_ok = (mechanism["all_gear_calls_ok"]
                    and mechanism["no_zero_candidate_anomaly"]
                    and mechanism["budget_compliance"]
                    and (demo_ok or not demos))

    # S0/S1 = 机制门 (主终点统计不足力, 仅描述性); S2 = 主终点判定
    go = mechanism_ok if stage in ("s0", "s1") else (mechanism_ok and primary_pass)
    # 修订注记汇总 (判定书携带; 详见驱动 docstring)
    hotspot_notes = {t: latest[(t, a)]["hotspot_source"]
                     for (t, a) in sorted(latest)
                     if str(latest[(t, a)].get("hotspot_source", ""))
                     .startswith("auto_identify_fallback")}
    notes = {
        "ferritin_excluded": ("deterministic ODesign zero-output boundary "
                              "(experiments/results/RESUME_CHECKPOINT.md §4)"),
        "hotspot_fallbacks": hotspot_notes,
        "s2_matrix_expansion": ("2026-08-11: 8 -> 10 targets "
                                "(+Concanavalin_A, +Chymotrypsinogen); "
                                "primary endpoint n = 30 pairs"),
        "c_request_generate_cap": ("2026-08-11: <=2 -> <=4 rounds; 48-raw "
                                   "hard cap both arms unchanged"),
    }
    return {
        "stage": stage, "timestamp": m.now_iso(),
        "n_targets": len(paired_targets), "targets": paired_targets,
        "pairs": pairs,
        "primary": {
            "n_pairs": len(pairs),
            "mcnemar": {"b": b, "c": c_, "p": p_val},
            "c_e2e_rate": c_e2e, "a_e2e_rate": a_e2e,
            "criterion": "p < 0.05 AND c_e2e_rate >= 0.8",
            "pass": primary_pass,
            "decisive_at": "s2 (n=30 pairs); descriptive only at s0/s1",
        },
        "matrix_lock": matrix_lock_measure(latest),
        "secondary": {
            "c_delivered_matrix_pass_rate": c_matrix_rate,
            "criterion_rate_ge_0.9": (c_matrix_rate is not None
                                      and c_matrix_rate >= 0.9),
            "llm_budget_compliance": not budget_violations,
            "llm_calls_per_target": {t: latest[(t, "C")]["llm_calls"]
                                     for t in paired_targets},
            "request_generate_per_target": {
                t: latest[(t, "C")]["request_generate_calls"]
                for t in paired_targets},
            "degraded_profiles_total": degraded_total,
        },
        "mechanism": mechanism,
        "notes": notes,
        "go_no_go": "GO" if go else "NO-GO",
        "go_rule": ("mechanism gate (s0/s1 staging)" if stage in ("s0", "s1")
                    else "mechanism AND primary endpoint (s2)"),
    }


def write_verdict(stage: str, verdict: dict) -> Path:
    path = RESULTS_DIR / f"e10_verdict_{stage}.json"
    path.write_text(json.dumps(verdict, ensure_ascii=False, default=str, indent=2),
                    encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 服务预-flight / CLI
# ---------------------------------------------------------------------------


def ensure_e10_services(log: Any = print) -> None:
    """幂等预-flight: ODesign 8012 (GPU) + LinearFold 8015; 缺者经 start.sh
    自启 (服务进程继承本进程环境, ODESIGN_CUDA_VISIBLE_DEVICES 在 main 内设定)。"""
    services = get_services_for_capabilities(E8_REQUIRED_CAPS)
    ready, errors = ensure_services_ready(services, timeout=900)
    if not ready:
        raise RuntimeError(f"service pre-flight failed: {errors}")
    log(f"[preflight] {len(services)} service(s) healthy", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", required=True, choices=["s0", "s1", "s2"])
    parser.add_argument("--targets", default=None,
                        help="comma-separated target ids (default: stage list)")
    parser.add_argument("--resume", action="store_true",
                        help="skip (stage, target, arm) with a successful record; "
                             "ODesign calls are cache-served regardless")
    args = parser.parse_args()
    stage = args.stage

    if stage == "s1":
        # S1 = 机制验证 (3 旧靶点 A+C) + 新靶点密度探针 (5 新靶点只跑 A 臂)
        targets = list(S1_TARGETS) + list(S1_PROBE_TARGETS)
        probe_only = set(S1_PROBE_TARGETS)
        arms_for = lambda t: ("A",) if t in probe_only else ("A", "C")
    elif stage == "s2":
        # S2 面板 (判据书 §靶点与面板规则): 新靶点 A-fail 率 (S1 探针) < 30%
        # → 15 靶; 否则 12 靶 (10 旧 + A-fail 密度最高的 2 新)
        targets = list(S2_TARGETS)
        try:
            probe_recs = load_records(RESULTS_DIR / "e10_runs_s1.jsonl")
            dens = {}
            for r in probe_recs:
                t, arm = r["target_id"], r["arm"]
                if t in S1_PROBE_TARGETS and arm == "A" and t not in dens:
                    dens[t] = sum(1 for p in PROFILE_ORDER if not r["jcd"][p])
            if dens:
                frac = sum(1 for t in S1_PROBE_TARGETS
                           if t in dens and dens[t] >= 1) / len(S1_PROBE_TARGETS)
                if frac >= 0.3:
                    # 12 靶: 10 旧 + A-fail cell 最多的 2 个新靶点 (预注册规则)
                    extra = sorted(S1_PROBE_TARGETS,
                                   key=lambda t: dens.get(t, 0), reverse=True)[:2]
                    targets = list(S2_TARGETS) + extra
                    print(f"[s2] new-target probe A-fail frac {frac:.2f} >= 0.3 "
                          f"-> 12-target panel: {targets}", flush=True)
                else:
                    targets = list(S2_TARGETS) + list(S2_NEW_TARGETS)
                    print(f"[s2] new-target probe A-fail frac {frac:.2f} < 0.3 "
                          f"-> 15-target panel", flush=True)
            else:
                print("[s2] WARNING: no S1 probe records; using 15-target panel",
                      flush=True)
                targets = list(S2_TARGETS) + list(S2_NEW_TARGETS)
        except FileNotFoundError:
            print("[s2] WARNING: no S1 probe file; using 15-target panel",
                  flush=True)
            targets = list(S2_TARGETS) + list(S2_NEW_TARGETS)
        arms_for = lambda t: ("A", "C")
    else:
        targets = list(STAGE_TARGETS[stage])
        arms_for = lambda t: ("A", "C")

    for t in targets:
        if not (TARGETS_DIR / f"{t}.json").is_file():
            parser.error(f"unknown target '{t}' (no {TARGETS_DIR / (t + '.json')})")

    os.environ.setdefault("ODESIGN_CUDA_VISIBLE_DEVICES", "0")  # GPU 0 空闲
    runs_path = RESULTS_DIR / f"e10_runs_{stage}.jsonl"
    t_start = time.perf_counter()
    ensure_e10_services()
    cache = load_odesign_cache()
    print(f"[e10:{stage}] odesign cache: {len(cache)} keys; targets={targets}",
          flush=True)
    registry, _executor = m.make_runner()
    llm = get_deepseek_llm(temperature=0.0)
    done = done_keys(load_records(runs_path)) if args.resume else set()

    for target_id in targets:
        for arm in arms_for(target_id):  # A 先: 首个 ODesign 调用计时锚点
            key = (stage, target_id, arm)
            if key in done:
                print(f"  skip {target_id}/{arm} (done)", flush=True)
                continue
            print(f"[e10:{stage}] {target_id} arm {arm} ...", flush=True)
            if arm == "A":
                rec = run_arm_a(stage, target_id, registry, cache)
            else:
                rec = run_arm_c(stage, target_id, registry, cache, llm)
            write_record(runs_path, rec)
            print(f"  -> {target_id}/{arm} jcd={rec['jcd']} e2e={rec['e2e']} "
                  f"raw={rec['pool']['n_raw_samples']} "
                  f"unique={rec['pool']['n_unique_candidates']} "
                  f"elapsed={rec['elapsed_seconds']:.0f}s", flush=True)

    verdict = compute_verdict(stage, runs_path)
    verdict["elapsed_seconds"] = round(time.perf_counter() - t_start, 2)
    path = write_verdict(stage, verdict)
    print(f"[e10:{stage}] verdict -> {path}: {verdict['go_no_go']} "
          f"(mcnemar p={verdict['primary']['mcnemar']['p']:.4g}, "
          f"c_e2e={verdict['primary']['c_e2e_rate']:.3f}, "
          f"mechanism_ok={all([verdict['mechanism']['all_gear_calls_ok'],
                               verdict['mechanism']['no_zero_candidate_anomaly'],
                               verdict['mechanism']['budget_compliance']])})",
          flush=True)
    return 0 if verdict["go_no_go"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
