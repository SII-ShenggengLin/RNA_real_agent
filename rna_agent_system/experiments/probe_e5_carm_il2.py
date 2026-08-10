"""E5 真实 C 臂探针(2026-08-08, v5 拍板后, v6 阈值): 单靶跑真实 LLM C 臂 agentic 循环
(新 U: λ 偏好权重 0.8; 新约束 v6 最终形态: B1 CAI≥0.8 + C1 GC 30–80), 检验真实 LLM
看到 λ 倾斜 U 后的选集是否满足 C 臂 R3/R4——预演回放(round-3 LLM 选集)的局限
即"LLM 未看到新 U"。

用法: cd rna_agent_system && python experiments/probe_e5_carm_il2.py [target]
产物: 仅 stdout; audit/records 写 scratch(/tmp/e5_probe_carm/), 不污染 experiments/results/。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments import run_e5_constraint_nav as m  # noqa: E402

TARGET = sys.argv[1] if len(sys.argv) > 1 else "IL-2"
SCRATCH = Path("/tmp/e5_probe_carm")
SCRATCH.mkdir(parents=True, exist_ok=True)


def main() -> int:
    m.RESULTS_DIR = SCRATCH  # audit/verdict → scratch; GEMORNA 缓存路径 import 时已绑定 → 复用
    llm = m.get_deepseek_llm(temperature=0.0)
    print(f"[probe:{TARGET}] real C arm, RESULTS_DIR->{SCRATCH}", flush=True)
    try:
        rec = m.run_one_cell("s1", TARGET, ["C"], llm,
                             out=SCRATCH / "probe_runs.jsonl", repeat=1, log=print)
    except Exception as e:  # 池 0 pass / 空交付等数据问题: 打印证据后继续下一靶
        print(f"  PROBE_CRASH {type(e).__name__}: {e}", flush=True)
        return 2
    ev = rec["evaluations"]["C"]
    c_arm = rec.get("arm_results", {}).get("C", {})
    elapsed = c_arm.get("elapsed_seconds", 0.0)
    print(f"\n=== {TARGET} C arm real-LLM evaluation (post-junction U) ===", flush=True)
    print(f"  R3: {ev['R3']}", flush=True)
    for i, p in enumerate(m.PROFILES):
        e = ev["profiles"][i]
        dl = e.get("delivered_ids") or []
        print(f"  {p}: e2e={e['e2e_pass']} R1={e['R1']} R4={e['R4']} "
              f"D1={e['D1']}({e.get('D1_min_dist', 0):.4f}) "
              f"D2={e['D2']}(ranks {e.get('D2_lambda_ranks')}) "
              f"D3={e['D3']}(pr {e.get('D3_pair_ratio_range', 0):.1f}pp/stem {e.get('D3_stem_range', 0)}bp) "
              f"constraint_rate={e['constraint_rate']:.2f} | ids={dl}", flush=True)
    print(f"  llm_calls={c_arm.get('llm_calls', ev.get('llm_calls', 0))} elapsed={elapsed:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
