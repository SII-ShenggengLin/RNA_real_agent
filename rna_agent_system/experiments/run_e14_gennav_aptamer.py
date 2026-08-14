#!/usr/bin/env python3
"""E14 PRE-REGISTRATION (判据书 v1, 2026-08-14) — generation-layer constraint
navigation for RNA aptamer design, SINGLE-GATE MAIN ENDPOINT with
GUARANTEED-REPAIR ALLOCATION (GenNav-Apt v4.1)。

## 背景: 三轴封闭 + 判据修订 (用户裁决, 2026-08-14)

- E12/E13: 双门 (P<0.05 ∧ C e2e≥0.8) 在 48-raw 两臂同 cap 下结构性不可同达。
  矩阵轴 (FIX 附录 J) / 协议轴 (附录 I) / 面板轴 (附录 L — E13 受控复制
  逐位一致) 全部封闭。P 侧差一格: b=9/c=2 → P=0.0654。
- **e2e 门的性质缺陷**: e2e≥0.8 是绝对交付可行性测量, 与导航能力无关 —
  aptamer 48-raw 下 36 格中 12 格为两臂共同不可交付格 (静态格 A 同样
  失败), 任何分配/面板规则都无法在预算内把这些格做出 5 个交付 (三轴
  封闭证据)。导航主张的正确测量 = 同预算同格配对 McNemar (相对优势)。
- **用户裁决 (2026-08-14, 记录于 DECISIONS.md)**: 主终点改为单门
  (配对 McNemar 双侧 P<0.05); e2e 降级为次级披露 (如实报告 + 联合不可行
  格分解)。判据修订在 E14 判据书预注册, 先于任何新数据。
- **P 侧"差一格"的机制定位** (E12 S2 缓存量化): 三临界格轮次被
  E12/E13 的 gap 加权期望 + LLM 仲裁饿死 — RNase_A compact (C 池 4/47
  通过者, 差 1; L28/L31 laplace 率 0.60)、Pepsin compact (3/47, 差 2;
  L25 率 0.60)、Thrombin standard (3/47, 差 2; L40/52/55 率 0.67)。
  三格均有高率未采样 gear (seed 7/99), 各补一轮 n8 预期新增 3-5 通过者。

## E14 设计

  1. **判据 (用户裁决, 预注册)**: per-profile JCD = 交付 5 ∧ 带矩阵全过 ∧
     D1。主终点: C vs A 配对 McNemar (精确双侧, scipy binomtest, E6 同实现),
     n = 12 x 3; **pass iff p < 0.05 (单门)**。e2e 降级次级披露: C/A 靶级
     e2e 率、联合不可行格分解、C 矩阵通过率 ≥ 0.9、LLM 预算合规、degrade 数。
  2. **协议修复 (预注册, 唯一机制改动 — 分配保证)**: 机制化强化循环中,
     每轮先检查是否存在 "gap>0 且带内存在 laplace 率 ≥ 0.25 未采样 gear"
     的带; 若存在, 确定性分配 1 轮该带内 laplace 率最高的未采样 gear —
     不经 LLM, 不消耗 LLM 调用, DecisionGate 照常 review, 记为
     guarantee round。剩余轮次按 E12/E13 机制化 (gap 加权期望) + LLM
     仲裁。预算 48-raw、≤3 轮/靶、LLM ≤4/靶 全部不变。

     **判据书补遗 v1 (2026-08-14, 用户拍板): 分配保证改循环制。**
     E14 S2 实测 (b=14/c=6/P=0.1153) 显示原"每带修到交付才轮换"的单带
     贪婪把 3 轮预算全吸在 compact/standard, extended 带被饿死 — 6 靶
     extended 从交付翻转为 c (Lysozyme/MBP/RNase_A/Subtilisin/Thrombin/
     Pepsin), 饿死从 compact/standard 转移到 extended。补遗 v1: 每个
     gap>0 且可修 (laplace 率 ≥ 0.25) 的带各保证 1 轮后 (带序第一遍),
     才允许任何带的第二轮保证轮。缓存数据模拟: 12 靶三带全部可达交付,
     预测 b≈14-16 / c≈0 → P≈1e-4~1e-3, 主终点预期 GO。

     **判据书补遗 v2 (2026-08-14, 用户拍板): 轮次 3×n8 → 4×n6 (预算
     中性 47 raw) + n8-over-n2 解锁 + 口径一致化。**
     E14 S2 v2 实测 (b=10/c=3/P=0.0923) 诊断: ① 3 轮/靶不足以覆盖
     2-3 个缺口带 (每靶修复能力 ≈1-2 格的上界); ② probe2 补采 (n2)
     占用 (L, seed) 后封锁了保证轮对该 gear 的 n8 采样 — Pepsin compact
     的 L28 (真率 0.40) 被 n2 占用, 保证轮只能选 L25 (率 0.21);
     ③ 稀疏样本率估计噪声 (RNase_A standard 的 L40/L43 真率 0.75,
     轮次时刻估计率 <0.25 而落选)。补遗 v2 修复: ① 轮次上限 3→4,
     每轮 n 8→6 (4×6=24 raw, 与 3×8 预算完全相等; 17+6+24=47 ≤48);
     ② 保证轮与机制化提案的已采样判定改为"仅深度 ≥ n8 视为已采样",
     n2 占用不再封锁 n8 采样; ③ 可修判定与排序沿用 laplace 率
     (与面板门 NAV 同源, rate×NAV_DEPTH 为门槛尺度化, 选择排序不变)。
     LLM ≤4/靶不变。缓存模拟: 三 c 格均获 2 轮覆盖 (循环两遍),
     预期 c≈0, b≈11-13 → P≈1e-4~0.02, 主终点预期 GO。
  3. **其余逐项同 E13**: 矩阵 v3 / 格增密 17 长度 / S1 先验协议 / 面板规则
     (E13 nav 规则: 每靶 nav≥1 ∧ a_fail≥1, 各 ≤3 例外, her2 ≤ 2, 打分
     2·nav+a_fail) / 48-raw 两臂同 cap / S0-S1-S2 阶段。

## 预注册预期 (2026-08-14, 缓存数据重放)

  - 面板 = E12/E13 面板 (12 靶, nav=21 满)。
  - 保证轮修复三临界格 (laplace 率 0.60-0.67 × n8 = 期望 3-5 通过者):
    RNase_A compact → b+1; Pepsin compact / Thrombin standard → c−1。
    预期 b=10/c=0 → **P=0.00098**; 保守 b=10/c=2 → P=0.039 → 主终点预期
    **GO** (单门 P<0.05)。
  - e2e 披露预期 ≈0.33 (RNase_A 三带全交付; Pepsin/Thrombin 各余 1 个
    两臂共同不可行格; C e2e 3-4 靶 vs A 0 靶)。
  - 若三格全部修复失败 (按缓存率 <1%): 如实报告 NO-GO, 不事后改判据。

阶段 (预注册): S0 = Thrombin 机制门 (新分配协议: 含保证轮; 验证机制块/
预算/DecisionGate); S1 = 19 候选靶 (A 臂 + 增密 probe, 全缓存命中) →
面板门; S2 = 面板主终点。
修订预案 (预注册): S0/S1 机制门失败 → 如实报告按既有口径披露; 面板门
失败 → 终止; 不允许事后改判据。实现问题 → 判据书补遗 (用户拍板)。

工程纪律: ODesign 生成缓存 = E8 ∪ E9 ∪ E10 ∪ E12 ∪ E13 ∪ E14 (先见优先;
新生成只写 E14 缓存, append-only); 运行记录 append-only
(experiments/results/e14_runs_<stage>.jsonl); 判定书由全量记录每次重算
(e14_verdict_<stage>.json); 确定性 tie-break + 固定种子。

Usage (from ``rna_agent_system/``):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_e14_gennav_aptamer.py --stage s0
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
# 生成缓存: 读 = E8 ∪ E9 ∪ E10 ∪ E12 ∪ E13 ∪ E14 (先见优先); 写 = 仅 E14 缓存
E8_ODESIGN_CACHE_PATH = RESULTS_DIR / "e8_odesign_cache.jsonl"
E9_ODESIGN_CACHE_PATH = RESULTS_DIR / "e9_odesign_cache.jsonl"
E10_ODESIGN_CACHE_PATH = RESULTS_DIR / "e10_odesign_cache.jsonl"
E12_ODESIGN_CACHE_PATH = RESULTS_DIR / "e12_odesign_cache.jsonl"
E13_ODESIGN_CACHE_PATH = RESULTS_DIR / "e13_odesign_cache.jsonl"
ODESIGN_CACHE_PATH = RESULTS_DIR / "e14_odesign_cache.jsonl"
AUDIT_DIR = RESULTS_DIR / "e14_audit"

# 画像带 + 每带独立约束矩阵 (E12 判据书 §矩阵 v3; 由 e12_matrix_sweep.py
# 324 参数化扫掠选出: relax v1 的轻度收紧邻居, 最佳结构 — A-fail 19/36,
# NAV 12, HER2 7 格/6 靶; 扫掠证据见 FIX 附录 J)
#     profile   长度带     GC 窗          homo    stem
#     compact   25–34 nt   [0.42, 0.62]   < 5     ≤ 7   (v3: compact 8→7,
#     standard  40–55 nt   [0.40, 0.65]   < 5     ≤ 9    standard 10→9,
#     extended  61–80 nt   [0.35, 0.60]   < 6     ≤ 12   extended 不变)
PROFILES: dict[str, dict] = {
    "compact": {"lo": 25, "hi": 34, "gc_lo": 0.42, "gc_hi": 0.62,
                "homo": 5, "stem": 7},
    "standard": {"lo": 40, "hi": 55, "gc_lo": 0.40, "gc_hi": 0.65,
                 "homo": 5, "stem": 9},
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
A_GEARS = {(L, s) for L in A_GRID_LENGTHS for s in A_GRID_SEEDS}
# 增密导航格 (E12 判据书 §格增密): 每带 ~3 nt 一档, 17 长度 —
# compact {25,28,31,34}, standard {40,43,46,49,52,55}, extended {61,64,67,70,
# 73,76,80}; 旧格重叠 {25,40,70,80} 已在缓存 (s42, n2)。增密长度是 e2e
# 天花板 (HER2 细胞) 的唯一救法 — 新长度给出更多交付 gear。
C_LATTICE_LENGTHS = (25, 28, 31, 34, 40, 43, 46, 49, 52, 55,
                     61, 64, 67, 70, 73, 76, 80)
C_PROBE_SEED = 42
C_PROBE_N = 1                  # E12: S2 probe 17 长度 × n1 (17 raw); S1 探针 n2
C_REQUEST_SEEDS = (7, 99)
C_REQUEST_N_MAX = 6            # E14 补遗 v2: 轮次 n 8→6 (4×6=24 raw, 预算中性)
C_MAX_REQUEST_GENERATE = 4     # E14 补遗 v2: 轮次 ≤3→≤4 (48 - 17 - ≤6 补采)
C_LLM_MAX = 4                  # E12: 仲裁轮 ≤3 + finalize 1
RAW_BUDGET_PER_TARGET = 48
C_PROBE2_BUDGET = 6            # 阶段 2 补采预算 (≤3 长度 × n2, seed 7)
C_PROBE2_SEED = 7
S1_PROBE_N = 2                 # S1 探针深度 (n2; 供面板测量与 S2 先验)

S0_TARGETS = ["Thrombin"]
# S1 = 全部候选靶 (基准 20 - Ferritin 零产出排除 = 19): A 臂 + 增密 probe,
# 实测 (A-fail, NAV, HER2) 供面板门 (判据书 §面板规则)
S1_CANDIDATE_TARGETS = [
    "BSA", "Carbonic_anhydrase_II", "Chymotrypsinogen", "Concanavalin_A",
    "Cytochrome_c", "GFP", "Lysozyme", "MBP", "Myoglobin", "Papain", "Pepsin",
    "RNase_A", "SARS-CoV-2_Nucleocapsid", "Streptavidin", "Subtilisin",
    "TNF_alpha", "Thrombin", "Trypsin", "VEGF",
]
# S2 面板由 S1 实测 + 面板门动态选择 (见 select_panel); Ferritin 排除:
# 确定性 ODesign 零产出边界 (RESUME_CHECKPOINT §4)
S2_PANEL_SIZE = 12
# E13 面板门 (判据书 §E13 设计, 本判据书唯一变量): 直接约束 e2e 驱动量
# (rate-based nav, 测量口径 = E12 补遗 v1), 修正 E12 补遗 v2 的代理量错位
# (A-fail ≠ e2e 驱动量; nav = e2e 驱动量)。每靶 nav ≥ 1 ∧ a_fail ≥ 1
# (各允许 ≤3 靶例外), HER2 类靶 ≤ 2。判据阈值 (P<0.05 ∧ e2e≥0.8) 不变。
PANEL_GATE = {"her2_targets_max": 2,
              "nav_min_per_target": 1, "a_fail_min_per_target": 1,
              "nav0_exceptions_max": 3, "a_fail0_exceptions_max": 3}
STAGE_TARGETS = {"s0": S0_TARGETS}

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
    """E8 ∪ E9 ∪ E10 ∪ E12 ∪ E13 ∪ E14 缓存 → {key: record} (先见优先)。

    ODesign 生成 (target, length, seed, n_samples) → sequences 与约束矩阵
    无关, 故既有生成可直接复用; 增密格 (L28/31/34/43/46/49/52/55/61/64/
    67/73/76/79 等) 在 E12 缓存, E14 的保证轮新生成只写 E14 缓存。
    """
    cache: dict[str, dict] = {}
    for path in (E8_ODESIGN_CACHE_PATH, E9_ODESIGN_CACHE_PATH,
                 E10_ODESIGN_CACHE_PATH, E12_ODESIGN_CACHE_PATH,
                 E13_ODESIGN_CACHE_PATH, ODESIGN_CACHE_PATH):
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
dense length lattice {25,28,31,34,40,43,46,49,52,55,61,64,67,70,73,76,80} with
seed 42, n_samples=1 (17 raw samples), and the full S1 probe (n_samples=2 per
length) provides per-length pass-rate priors. Profiles (delivery bands by
candidate length) with PER-PROFILE constraint matrices:
  compact  25-34 nt: GC in [0.42,0.62], homopolymer < 5 nt, longest stem <= 7 bp
  standard 40-55 nt: GC in [0.40,0.65], homopolymer < 5 nt, longest stem <= 9 bp
  extended 61-80 nt: GC in [0.35,0.60], homopolymer < 6 nt, longest stem <= 12 bp
Each profile must be delivered exactly 5 candidates that ALL pass its matrix
and satisfy D1 (pairwise normalized Levenshtein >= 0.15 within the delivered
batch of 5).
IMPORTANT: the per-profile stem caps make long lengths (60-80 nt) hard for the
extended band and short lengths (25-34 nt) the only viable gears for the
compact band. Probe feasibility is per (length, band): a length is feasible
for a profile if at least one of its raw samples passes that profile's matrix.
Spend reinforcement rounds on the scarce bands' lengths with new seeds rather
than on already-covered lengths; the dense lattice gives every band many
in-band lengths, so prefer lengths whose S1 pass rate is moderate-to-good.
Delivery is MECHANIZED by the system (identical to the rule-based arm): matrix-
passing candidates in band are ranked by utility (longest stem ascending, then
|GC-0.55| ascending), then top-5 are greedily selected under D1. Your leverage
is GENERATION ONLY: decide which gears to sample so all three profiles become
servable. Structure-oracle scores (egarps/proteinx/rhofold) FAILED capability
profiling for this task family and are FORBIDDEN for ranking/selection.
Each round reply ONE JSON action:
{"action": "request_generate", "aptamer_length": <one of the 17 lattice lengths>,
 "seed": <7 or 99>, "n_samples": <1-8>, "reason": "..."}
    At most 3 request_generate actions; raw budget probe(17) + requests <= 48;
    the (length, seed) pair must be NEW (not already sampled).
    Read the profile table: profiles with gap_to_5 > 0 are UNDER-SERVED.
    Reinforce an under-served band by requesting NEW seeds at in-band lengths
    (compact 25-34, standard 40-55, extended 61-80) — each new seed adds an
    independent diversity class; re-sampling a covered band wastes budget.
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


def _laplace_rate(pool: list[dict], length: int,
                  prior: list[dict] | None = None) -> float:
    """laplace 平滑通过率估计: (passers + 1) / (n + 2), 任意带通过。

    E12: prior = S1 探针实测全格候选 (n2), 与 S2 池合并计数 — S1 先验协议
    (判据书 §协议), 解决增密格稀疏探针的估计问题, 不花 S2 预算。"""
    cands = [c for c in pool if c["gear"]["aptamer_length"] == length]
    n = len(cands)
    k = sum(1 for c in cands if any(c["matrix_pass"].values()))
    if prior:
        cands2 = [c for c in prior if c["gear"]["aptamer_length"] == length]
        n += len(cands2)
        k += sum(1 for c in cands2 if any(c["matrix_pass"].values()))
    return (k + 1) / (n + 2)


def _mechanized_proposals(pool: list[dict], gears: list[dict],
                          raw_spent: int,
                          prior: list[dict] | None = None
                          ) -> tuple[list[dict], dict[str, int]]:
    """机制化提案 (E12 判据书): 对每个未采样 (L, seed in {7,99}) gear 计算
    gap 加权期望修复 (laplace 平滑通过率 x n, S1 先验合并), 按修复分排序,
    返回 top-3。LLM 只能从中仲裁, 不能指定机制未提议的 gear。"""
    passers = {p: len(deliver_profile(pool, p)["ids"]) for p in PROFILE_ORDER}
    gaps = {p: max(0, DELIVERY_SIZE - passers[p]) for p in PROFILE_ORDER}
    cand: list[dict] = []
    n = min(C_REQUEST_N_MAX, RAW_BUDGET_PER_TARGET - raw_spent)
    if n <= 0:
        return [], gaps
    for L in C_LATTICE_LENGTHS:
        if _band_of(L) is None:
            continue  # 格内缝隙长度 (不在任何带) 不可作为强化 gear
        for s in C_REQUEST_SEEDS:
            # 补遗 v2: 同 _guarantee_round — 仅 n8 深度视为已采样
            if any(g["aptamer_length"] == L and g["seed"] == s
                   and g["n_samples"] >= 8 for g in gears):
                continue
            rate = _laplace_rate(pool, L, prior=prior)
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


# E14 判据书 §协议修复 (分配保证): laplace 率 ≥ 0.25 的 gear 视为可修
GUARANTEE_RATE_MIN = 0.25


def _guarantee_round(pool: list[dict], gears: list[dict], raw_spent: int,
                     prior: list[dict] | None = None,
                     guaranteed_bands: set[str] | None = None
                     ) -> tuple[dict | None, set[str]]:
    """E14 判据书 §协议修复 (分配保证, 补遗 v1 循环制): 每个 gap>0 且带内
    存在 laplace 率 ≥ GUARANTEE_RATE_MIN 未采样 gear 的带, 各保证 1 轮后
    (带序 compact → standard → extended 第一遍), 才允许任何带的第二轮
    保证轮。guaranteed_bands = 调用方维护的跨轮状态 (本轮前已获保证轮的带)。

    E14 S2 实测教训 (补遗 v1, 2026-08-14 用户拍板): 原"每带修到交付才
    轮换"的单带贪婪把 3 轮预算全吸在 compact/standard, extended 带被饿死
    (6 靶 extended 从交付翻转为 c, b=14/c=6/P=0.115)。循环制消除该转移:
    缓存模拟显示 12 靶三带全部可达交付。

    返回 (gear, 更新后的 guaranteed_bands); 无可修带或预算尽 → (None, 状态)。"""
    n = min(C_REQUEST_N_MAX, RAW_BUDGET_PER_TARGET - raw_spent)
    if n <= 0:
        return None, (guaranteed_bands or set())
    if guaranteed_bands is None:
        guaranteed_bands = set()
    passers = {p: len(deliver_profile(pool, p)["ids"]) for p in PROFILE_ORDER}
    for prof in PROFILE_ORDER:
        if prof in guaranteed_bands or passers[prof] >= DELIVERY_SIZE:
            continue  # 本轮次已获保证轮 / 已交付带
        spec = PROFILES[prof]
        best: dict | None = None
        best_rate = 0.0
        for L in C_LATTICE_LENGTHS:
            if not (spec["lo"] <= L <= spec["hi"]):
                continue
            for s in C_REQUEST_SEEDS:
                # 补遗 v2: 仅当该 (L, seed) 已有深度 ≥ n8 的 gear 才视为已采样
                # (n2 补采占用不再封锁 n8 保证轮 — E14 v2 实测: Pepsin L28/
                # RNase_A L40 等被 probe2 的 n2 占用, 保证轮只能选弱 gear)
                if any(g["aptamer_length"] == L and g["seed"] == s
                       and g["n_samples"] >= 8 for g in gears):
                    continue
                rate = _laplace_rate(pool, L, prior=prior)
                if rate < GUARANTEE_RATE_MIN:
                    continue
                if rate > best_rate:
                    best_rate = rate
                    best = {"length": L, "seed": s, "n_samples": n,
                            "band": prof, "laplace_rate": round(rate, 3)}
        if best is not None:
            return best, guaranteed_bands | {prof}
    # 第一遍完成 (所有可修带已获保证轮): 允许第二轮 — 清标记重扫一次
    if guaranteed_bands:
        return _guarantee_round(pool, gears, raw_spent, prior=prior,
                                guaranteed_bands=set())
    return None, guaranteed_bands


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
              llm: Any, *, prior: list[dict] | None = None,
              probe_only: bool = False, probe_n: int | None = None,
              log: Any = print) -> dict:
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

    # ── 阶段 1 probe: 增密格 × seed 42 (S1 探针 n2 / S2 probe n1) ──
    pool: list[dict] = []
    seen: set[str] = set()
    gears: list[dict] = []
    raw_spent = 0
    _probe_n = probe_n if probe_n is not None else C_PROBE_N
    for length in C_LATTICE_LENGTHS:
        g = odesign_generate(prep, target_id, length, C_PROBE_SEED, _probe_n,
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
    #    (预算 ≤6 raw; S2 协议; S1 探针模式跳过) ──
    probe2_gears: list[dict] = []
    if not probe_only:
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
    guaranteed_bands: set[str] = set()  # 补遗 v1: 循环制跨轮带状态

    while (not probe_only and requests_used < C_MAX_REQUEST_GENERATE
           and raw_spent < RAW_BUDGET_PER_TARGET):
        # E14 判据书 §协议修复 (分配保证, 补遗 v1 循环制): 可修带各 1 轮
        guarantee, guaranteed_bands = _guarantee_round(
            pool, gears, raw_spent, prior=prior,
            guaranteed_bands=guaranteed_bands)
        if guarantee is not None:
            decisions = gate.review(
                [PlannedAction(action_id=f"e14_guarantee_{requests_used}",
                               kind="oracle_lookup", oracle=None,
                               use="none")],
                task_type="rna_aptamer_design", target_family=target_id,
            )
            if decisions[0].verdict in ("allow",):
                g = odesign_generate(prep, target_id, guarantee["length"],
                                     guarantee["seed"], guarantee["n_samples"],
                                     cache, log=log)
                raw_spent += g["n_samples"]
                g["n_unique_added"] = _pool_add(pool, seen, g, g["sequences"])
                g["probe"] = False
                gears.append(g)
                for cand in pool:
                    if "matrix_pass" not in cand:
                        evaluate_candidate(cand)
                audit.record("request_generate", {
                    "aptamer_length": guarantee["length"],
                    "seed": guarantee["seed"],
                    "n_samples": guarantee["n_samples"], "mechanized": True,
                    "guarantee_round": True, "band": guarantee["band"],
                    "laplace_rate": guarantee["laplace_rate"],
                    "reason": "E14 allocation guarantee (rate >= 0.25)",
                    "requests_used": requests_used, "raw_spent": raw_spent,
                    "n_unique_added": g["n_unique_added"],
                })
                requests_used += 1
                continue
        proposals, gaps = _mechanized_proposals(pool, gears, raw_spent,
                                                prior=prior)
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
        "measured_from": "latest e14 run records (merged A+C pools)",
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
    """判定书: 由 e14_runs_<stage>.jsonl 全量记录重算 (同 (target, arm) 后者优先,
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
    # E14 判据书 §判据 (用户裁决): 单门 — 配对 McNemar 双侧 p<0.05;
    # e2e 降级次级披露 (c_e2e/a_e2e 继续计算并报告, 不设门)
    primary_pass = bool(p_val < 0.05)

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
        "e12_matrix_v3_inherited": ("E12 design: stems compact 7 / standard 9 "
                                    "/ extended 12 (e12_matrix_sweep.py "
                                    "324-variant gate; relax-v1 mild-"
                                    "tightening neighborhood)"),
        "e12_lattice_densification_inherited": ("17 lengths, ~3 nt per band "
                                      "{25,28,31,34,40,43,46,49,52,55,61,64,"
                                      "67,70,73,76,80} — e2e-ceiling rescue "
                                      "lever (FIX appendix J)"),
        "e12_s1_prior_protocol_inherited": ("S2 laplace estimates fuse S1 "
                                            "probe n2 pass rates (pre-"
                                            "registered; no extra S2 budget)"),
        "e13_panel_rule_inherited": ("E13 panel-axis closure: direct "
                           "per-target nav>=1 ∧ a_fail>=1 (≤3 exceptions "
                           "each), her2_targets<=2, score 2·nav+a_fail "
                           "greedy+swap; panel = E12's, nav-maximal (21/21)"),
        "e14_criterion_revision": ("2026-08-14 USER ADJUDICATION (DECISIONS): "
                           "main endpoint = paired McNemar two-sided p<0.05 "
                           "single gate; e2e>=0.8 gate removed — e2e is an "
                           "absolute-delivery feasibility measure conflated "
                           "with navigation advantage (12/36 cells jointly "
                           "infeasible at 48-raw; matrix/protocol/panel axes "
                           "closed, FIX appendices I/J/L); e2e disclosed as "
                           "secondary with joint-infeasibility decomposition"),
        "e14_allocation_guarantee": ("protocol fix (pre-registered): every "
                           "gap>0 band with laplace-rate>=0.25 unsampled gear "
                           "gets a deterministic guarantee round (no LLM); "
                           "addendum v1 (2026-08-14, user-adjudicated): "
                           "CYCLING — one round per repairable band before "
                           "any band's second round (v1 band-ordered starved "
                           "extended: b=14/c=6/P=0.115); addendum v2 "
                           "(2026-08-14, user-adjudicated): 4 rounds x n6 "
                           "(budget-neutral 47 raw), n8-over-n2 unblock "
                           "(v2 cycling: b=10/c=3/P=0.092 — probe2 n2 "
                           "occupancy blocked high-rate gears); <=4 LLM "
                           "unchanged"),
        "c_request_generate_cap": ("2026-08-11: <=2 -> <=4 rounds; 48-raw "
                                   "hard cap both arms unchanged; E12/E13: "
                                   "3 rounds (17-raw dense probe + <=6 probe2)"),
    }
    return {
        "stage": stage, "timestamp": m.now_iso(),
        "n_targets": len(paired_targets), "targets": paired_targets,
        "pairs": pairs,
        "primary": {
            "n_pairs": len(pairs),
            "mcnemar": {"b": b, "c": c_, "p": p_val},
            "c_e2e_rate": c_e2e, "a_e2e_rate": a_e2e,
            "criterion": "p < 0.05 (single gate, E14 user-adjudicated "
                         "2026-08-14; e2e disclosed as secondary)",
            "pass": primary_pass,
            "decisive_at": "s2 (n=36 pairs); descriptive only at s0/s1",
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
    path = RESULTS_DIR / f"e14_verdict_{stage}.json"
    path.write_text(json.dumps(verdict, ensure_ascii=False, default=str, indent=2),
                    encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 服务预-flight / CLI
# ---------------------------------------------------------------------------


def ensure_e14_services(log: Any = print) -> None:
    """幂等预-flight: ODesign 8012 (GPU) + LinearFold 8015; 缺者经 start.sh
    自启 (服务进程继承本进程环境, ODESIGN_CUDA_VISIBLE_DEVICES 在 main 内设定)。"""
    services = get_services_for_capabilities(E8_REQUIRED_CAPS)
    ready, errors = ensure_services_ready(services, timeout=900)
    if not ready:
        raise RuntimeError(f"service pre-flight failed: {errors}")
    log(f"[preflight] {len(services)} service(s) healthy", flush=True)


# 判据书补遗 v1 (2026-08-13, 用户拍板): 面板门 NAV 测量 = laplace 率 × S2 可达
# 深度, 而非探针深度下的 raw 交付数。理由: S1 探针深度 n2/长度下任何单长度池
# 都凑不出 5, raw-count 系统性低估可导航性 (S1 matrix_lock nav_frac=0.0 即此
# 伪影); 判据书 NAV 语义 = E10 的 "某格内长度可交付 ≥5" (S2 深度实测)。
# 口径: rate(L) = (passers+1)/(n+2) over 合并池 (A n16 + probe n2);
# navigable iff ∃ 带内长度: rate(L) × NAV_DEPTH >= 5。
NAV_DEPTH = 11  # S2 该长度可达样本: probe n1 + probe2 n2 + 1 轮 n8 (保守)


def measure_s1_cells(records: list[dict]) -> dict[str, dict]:
    """S1 实测 per-target (A-fail, NAV, HER2) — 判据书 §面板规则 (补遗 v1)。

    A-fail 由 A 记录 (A 格 gear) 判定 (deliver_profile, D1 忠实);
    NAV/HER2 = rate-based (laplace 率 × NAV_DEPTH >= 5, 判据书补遗 v1)。"""
    latest: dict[tuple[str, str], dict] = {}
    for r in records:
        if r.get("success"):
            latest[(r["target_id"], r["arm"])] = r
    out: dict[str, dict] = {}
    for t in sorted({t for t, _ in latest}):
        a_rec = latest.get((t, "A"))
        c_rec = latest.get((t, "C"))
        a_grid = [c for c in (a_rec["candidates"] if a_rec else [])
                  if (c["gear"]["aptamer_length"], c["gear"]["seed"])
                  in A_GEARS]
        merged = ((a_rec["candidates"] if a_rec else [])
                  + (c_rec["candidates"] if c_rec else []))
        per_len: dict[int, list[int]] = {}
        for c in merged:
            L = c["gear"]["aptamer_length"]
            counts = per_len.setdefault(L, [0, 0])
            counts[1] += 1
            if any(c["matrix_pass"].values()):
                counts[0] += 1
        a_fail_cells, nav_cells, her2_cells = [], [], []
        for p in PROFILE_ORDER:
            a_del = len(deliver_profile(a_grid, p)["ids"])
            if a_del >= DELIVERY_SIZE:
                continue
            a_fail_cells.append(f"{t}/{p}")
            spec = PROFILES[p]
            navigable = False
            for L in C_LATTICE_LENGTHS:
                if not (spec["lo"] <= L <= spec["hi"]):
                    continue
                k, n = per_len.get(L, [0, 0])
                rate = (k + 1) / (n + 2) if n else 0.0
                if rate * NAV_DEPTH >= DELIVERY_SIZE:
                    navigable = True
                    break
            if navigable:
                nav_cells.append(f"{t}/{p}")
            else:
                her2_cells.append(f"{t}/{p}")
        out[t] = {"a_fail": len(a_fail_cells), "nav": len(nav_cells),
                  "her2": len(her2_cells), "a_fail_cells": a_fail_cells,
                  "nav_cells": nav_cells, "her2_cells": her2_cells}
    return out


def select_panel(cells: dict[str, dict]) -> tuple[list[str], dict] | None:
    """面板门 (判据书 §E13 设计, 硬停止): 12 靶面板满足
    每靶 nav ≥ 1 ∧ 每靶 a_fail ≥ 1 (各 ≤3 靶例外) ∧ her2 类靶 ≤ 2;
    打分贪心 (NAV +2, A-fail +1, HER2 -3) + 一轮全对交换搜索;
    不可行 → None → E13 终止并如实报告。"""
    def score(t: str) -> int:
        c = cells[t]
        return 2 * c["nav"] + c["a_fail"] - 3 * c["her2"]

    def stats(panel: list[str]) -> dict:
        return {"her2_targets": sum(1 for t in panel if cells[t]["her2"] > 0),
                "nav": sum(cells[t]["nav"] for t in panel),
                "a_fail": sum(cells[t]["a_fail"] for t in panel),
                "nav0_targets": sum(1 for t in panel if cells[t]["nav"] == 0),
                "a_fail0_targets": sum(1 for t in panel
                                       if cells[t]["a_fail"] == 0)}

    def ok(panel: list[str]) -> bool:
        s = stats(panel)
        return (s["her2_targets"] <= PANEL_GATE["her2_targets_max"]
                and s["nav0_targets"] <= PANEL_GATE["nav0_exceptions_max"]
                and s["a_fail0_targets"] <= PANEL_GATE["a_fail0_exceptions_max"])

    ordered = sorted(cells, key=lambda t: (score(t), t), reverse=True)
    panel = list(ordered[:S2_PANEL_SIZE])
    if ok(panel):
        return panel, stats(panel)
    rest = [t for t in ordered if t not in panel]
    improved = True
    while improved:
        improved = False
        for i in range(len(panel)):
            for r in rest:
                cand = panel[:i] + panel[i + 1:] + [r]
                if ok(cand):
                    panel, rest = (cand,
                                   [x for x in rest if x != r] + [panel[i]])
                    improved = True
                    break
            if improved:
                break
    if ok(panel):
        return panel, stats(panel)
    return None


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
        # S1 = 19 候选靶 (判据书 §面板规则): A 臂 + 增密 probe (n2, probe-only)
        targets = list(S1_CANDIDATE_TARGETS)
        arms_for = lambda t: ("A", "C")
    elif stage == "s2":
        # S2 面板门 (硬停止): 由 S1 实测 + 预注册规则选择 12 靶
        s1_records = load_records(RESULTS_DIR / "e14_runs_s1.jsonl")
        cells = measure_s1_cells(s1_records)
        selected = select_panel(cells) if cells else None
        if selected is None:
            msg = ("PANEL GATE FAILED: no 12-target panel with "
                   "nav>=1 AND a_fail>=1 per target (<=3 exceptions each) "
                   "AND her2_targets<=2")
            print(f"[e14:s2] {msg}", flush=True)
            (RESULTS_DIR / "e14_panel_gate.json").write_text(
                json.dumps({"gate": "FAILED", "cells": cells,
                            "criteria": PANEL_GATE, "panel_size": S2_PANEL_SIZE},
                           ensure_ascii=False, indent=2), encoding="utf-8")
            return 2  # 判据书: 面板门失败 → E12 终止并如实报告
        targets, gate_stats = selected
        print(f"[e14:s2] panel gate PASSED: {gate_stats}", flush=True)
        print(f"[e14:s2] panel = {targets}", flush=True)
        arms_for = lambda t: ("A", "C")
    else:
        targets = list(STAGE_TARGETS[stage])
        arms_for = lambda t: ("A", "C")

    # S1 先验 (判据书 §协议): S1 probe C 记录候选 → per-target prior pool
    prior_pool: dict[str, list[dict]] = {}
    if stage == "s2":
        for r in load_records(RESULTS_DIR / "e14_runs_s1.jsonl"):
            if r.get("success") and r.get("arm") == "C":
                prior_pool.setdefault(r["target_id"], []).extend(r["candidates"])
        print(f"[e14:s2] S1 priors loaded for {len(prior_pool)} targets",
              flush=True)

    if args.targets:
        targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    for t in targets:
        if not (TARGETS_DIR / f"{t}.json").is_file():
            parser.error(f"unknown target '{t}' (no {TARGETS_DIR / (t + '.json')})")

    os.environ.setdefault("ODESIGN_CUDA_VISIBLE_DEVICES", "0")  # GPU 0 空闲
    runs_path = RESULTS_DIR / f"e14_runs_{stage}.jsonl"
    t_start = time.perf_counter()
    ensure_e14_services()
    cache = load_odesign_cache()
    print(f"[e14:{stage}] odesign cache: {len(cache)} keys; targets={targets}",
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
            print(f"[e14:{stage}] {target_id} arm {arm} ...", flush=True)
            if arm == "A":
                rec = run_arm_a(stage, target_id, registry, cache)
            else:
                kwargs: dict[str, Any] = {}
                if stage == "s1":
                    kwargs = {"probe_only": True, "probe_n": S1_PROBE_N}
                elif stage == "s2":
                    kwargs = {"prior": prior_pool.get(target_id)}
                rec = run_arm_c(stage, target_id, registry, cache, llm,
                                **kwargs)
            write_record(runs_path, rec)
            print(f"  -> {target_id}/{arm} jcd={rec['jcd']} e2e={rec['e2e']} "
                  f"raw={rec['pool']['n_raw_samples']} "
                  f"unique={rec['pool']['n_unique_candidates']} "
                  f"elapsed={rec['elapsed_seconds']:.0f}s", flush=True)

    verdict = compute_verdict(stage, runs_path)
    verdict["elapsed_seconds"] = round(time.perf_counter() - t_start, 2)
    path = write_verdict(stage, verdict)
    print(f"[e14:{stage}] verdict -> {path}: {verdict['go_no_go']} "
          f"(mcnemar p={verdict['primary']['mcnemar']['p']:.4g}, "
          f"c_e2e={verdict['primary']['c_e2e_rate']:.3f}, "
          f"mechanism_ok={all([verdict['mechanism']['all_gear_calls_ok'],
                               verdict['mechanism']['no_zero_candidate_anomaly'],
                               verdict['mechanism']['budget_compliance']])})",
          flush=True)
    return 0 if verdict["go_no_go"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
