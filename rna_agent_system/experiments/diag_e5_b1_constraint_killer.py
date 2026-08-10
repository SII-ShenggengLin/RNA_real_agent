"""E5 B1 约束杀手诊断(2026-08-08): 探针显示 A1AT 9/315、Insulin/EPO/GFP 0/315 通过
B1(GC 35-70 + CAI≥0.8)。本脚本复用 build_pool(cache)定位:
  1) 各约束独立通过数(杀手约束)
  2) GC 窗口/CAI 阈值放宽敏感度(GC 30-75 / 30-80 / CAI 0.7)——供 B1 调整拍板
用法: cd rna_agent_system && python experiments/diag_e5_b1_constraint_killer.py [target...]
产物: 仅 stdout; 不写 experiments/results/。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments import run_e5_constraint_nav as m  # noqa: E402

TARGETS = sys.argv[1:] or ["A1AT", "Insulin", "EPO", "GFP"]

GC_WINDOWS = [(35.0, 70.0), (30.0, 75.0), (30.0, 80.0), (25.0, 80.0)]  # (min, max)
CAI_THRESHOLDS = [0.8, 0.7, 0.6]


def main() -> int:
    for target in TARGETS:
        meta = json.loads((m.TARGETS_DIR / f"{target}.json").read_text(encoding="utf-8"))
        registry, _executor = m.make_runner()
        print(f"=== {target} ===", flush=True)
        pool = m.build_pool(target, meta, registry)
        cands = pool["candidates"]
        print(f"  n_candidates={len(cands)}", flush=True)

        # 1) 各约束独立通过数 + 联合通过
        keys = list(cands[0]["constraints"].keys())
        print("  per-constraint pass counts:", flush=True)
        for k in keys:
            nk = sum(1 for c in cands if c["constraints"][k])
            print(f"    {k}: {nk}/{len(cands)}", flush=True)
        n_pass = sum(1 for c in cands if c["flags"]["passed"])
        print(f"  joint (all {len(keys)}): {n_pass}/{len(cands)}", flush=True)

        # 2) GC 滑动窗口放宽敏感度(C1 是 100nt 滑动窗口; 用同函数重算)
        print("  GC sliding-window relaxation sensitivity:", flush=True)
        for gmin, gmax in GC_WINDOWS:
            c1_ok = lambda c: not m.sliding_window_gc_out_of_bounds(  # noqa: E731
                c["sequence"], lo=gmin, hi=gmax)
            nrelax = sum(1 for c in cands
                         if all(c["constraints"][k] for k in keys if k != "C1")
                         and c1_ok(c))
            print(f"    GC [{gmin:.0f},{gmax:.0f}]: joint={nrelax}/{len(cands)}", flush=True)

        # 3) CAI 阈值放宽敏感度(只放宽 CAI, 其余照旧)
        print("  CAI-threshold relaxation sensitivity (GC 35-70 kept):", flush=True)
        for cai_t in CAI_THRESHOLDS:
            nrelax = sum(1 for c in cands
                         if all(c["constraints"][k] for k in keys if k != "CAI")
                         and c["archive"].get("E1_cai", 0.0) >= cai_t)
            print(f"    CAI>={cai_t}: joint={nrelax}/{len(cands)}", flush=True)
        print(flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
