"""E5 S1 档位 A 预演(2026-08-08): 重建单靶 pool(确定性), 用新 U(λ_pref 进 U)模拟
A 臂选点 + 回放第 3 轮 C 臂 LLM 选集, 校验 R3(分离)/R4(最优)/D1-D3 判据是否修复。
用法: cd rna_agent_system && python experiments/preflight_e5_s1_lambda_fix.py [target]
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments import run_e5_constraint_nav as m  # noqa: E402

TARGET = sys.argv[1] if len(sys.argv) > 1 else "IL-2"


def summarize_delivery(delivery, label: str) -> None:
    if not delivery:
        print(f"  {label}: EMPTY")
        return
    t = delivery[0]
    print(f"  {label} top1={t['id']} λ_rank={t['lambda_rank']} λ={t['lambda']} "
          f"CAI={t['archive'].get('E1_cai'):.4f} U={t['utility']['__prof__']:.4f}")


def run() -> None:
    meta = json.loads((m.TARGETS_DIR / f"{TARGET}.json").read_text(encoding="utf-8"))
    registry, _executor = m.make_runner()
    print(f"[preflight:{TARGET}] building pool (deterministic, cache reuse) ...", flush=True)
    pool = m.build_pool(TARGET, meta, registry)
    m.assign_utilities(pool)
    pool["registry"] = registry

    # ── 池级统计(v6 追加: B1 放宽后去饱和检验; n_pass 决定 crit1 C>A 是否可达)──
    n_pass = sum(1 for c in pool["candidates"] if c["flags"]["passed"])
    print(f"=== pool stats (B1 v6: C1 GC 30-80 + CAI>=0.8, {len(pool['candidates'])} candidates) ===")
    print(f"  n_pass={n_pass}/{len(pool['candidates'])} ({n_pass / len(pool['candidates']):.1%})")
    keys = list(pool["candidates"][0]["constraints"].keys())
    for k in keys:
        nk = sum(1 for c in pool["candidates"] if c["constraints"][k])
        print(f"    {k}: {nk}/{len(pool['candidates'])} pass")
    by_src: dict[str, list[int]] = {}
    for c in pool["candidates"]:
        by_src.setdefault(c["source"], []).append(1 if c["flags"]["passed"] else 0)
    for src, vals in sorted(by_src.items()):
        print(f"    src={src}: {sum(vals)}/{len(vals)} pass "
              f"(CAI range {min(c['archive']['E1_cai'] for c in pool['candidates'] if c['source'] == src):.3f}"
              f"-{max(c['archive']['E1_cai'] for c in pool['candidates'] if c['source'] == src):.3f})")

    # ── A 臂: 新 _default_delivery ──
    print("=== A arm (new selection) ===")
    a_deliveries = {}
    for prof in m.PROFILES:
        d = m._default_delivery(pool, prof)
        a_deliveries[prof] = d
        t = d[0]
        print(f"  {prof}: top1={t['id']} λ_rank={t['lambda_rank']} λ={t['lambda']} "
              f"CAI={t['archive'].get('E1_cai'):.4f} U={t['utility'][prof]:.4f} "
              f"| delivered ids={[c['id'] for c in d]}")
    # R3: 画像两两 top-1 分离
    tops = [a_deliveries[p][0] for p in m.PROFILES]
    pairs, separated = [], 0
    for i in range(len(m.PROFILES)):
        for j in range(i + 1, len(m.PROFILES)):
            d_cai = abs(tops[i]["archive"]["E1_cai"] - tops[j]["archive"]["E1_cai"])
            d_lam = abs(tops[i]["lambda_rank"] - tops[j]["lambda_rank"])
            pairs.append((m.PROFILES[i], m.PROFILES[j], d_cai, d_lam))
            if d_cai >= 0.05 or d_lam >= 2:
                separated += 1
    print(f"  R3 pairs: {[(p, f'cai={dca:.3f}', f'lam={dl}') for p, _, dca, dl in pairs]} "
          f"-> separated {separated}/{len(pairs)} (v4 判据 ≥1/3: {separated / max(len(pairs), 1) >= 1 / 3})")

    # ── C 臂回放: 第 3 轮 LLM 选集 + 新 U 机制化重排 ──
    print("=== C arm replay (round-3 LLM selections, new U re-sort) ===")
    runs_path = m.RESULTS_DIR / "e5_s1_runs.jsonl"
    recs = [json.loads(l) for l in runs_path.read_text(encoding="utf-8").splitlines()]
    rec = [r for r in recs if r["target_id"] == TARGET][0]
    c_runs = rec["arm_results"]["C_runs"]
    c_deliveries = {}
    for run in c_runs:
        for prof, deliv in run["deliveries"].items():
            ids = [c["id"] for c in deliv]
            by_id = {c["id"]: c for c in pool["candidates"]}
            found = [by_id[i] for i in ids if i in by_id]
            missing = [i for i in ids if i not in by_id]
            if missing:
                print(f"  WARN {prof}: {len(missing)} LLM 选集 id 不在重建池(extra-LD 候选): {missing[:3]}")
            # 机制化重排(方案 B 并行, 同 run_arm_c finish): 按新 U 降序
            c_deliveries[prof] = m.mechanize_delivery_order(found, prof)
            t = c_deliveries[prof][0]
            print(f"  {prof}: top1={t['id']} λ_rank={t['lambda_rank']} λ={t['lambda']} "
                  f"CAI={t['archive'].get('E1_cai'):.4f} U={t['utility'][prof]:.4f}")

    # ── 交付级 E3 junction + 二次 U(镜像 run_one_cell) ──
    for arm_rec in [{"arm": "A", "deliveries": a_deliveries}, {"arm": "C", "deliveries": c_deliveries}]:
        m.delivery_eval_junctions(pool, registry, arm_rec)
        m.assign_utilities(pool)

    # ── 判据评测 ──
    for arm_name, deliveries in (("A", a_deliveries), ("C", c_deliveries)):
        print(f"=== {arm_name} arm evaluations (post-junction U) ===")
        r3_ok = True
        tops = [deliveries[p][0] for p in m.PROFILES]
        separated = 0
        for i in range(len(m.PROFILES)):
            for j in range(i + 1, len(m.PROFILES)):
                d_cai = abs(tops[i]["archive"]["E1_cai"] - tops[j]["archive"]["E1_cai"])
                d_lam = abs(tops[i]["lambda_rank"] - tops[j]["lambda_rank"])
                if d_cai >= 0.05 or d_lam >= 2:
                    separated += 1
        r3_ok = separated / 3 >= 1 / 3
        print(f"  R3: {separated}/3 pairs separated (v4 ≥1/3) -> {'PASS' if r3_ok else 'FAIL'}")
        for prof in m.PROFILES:
            ev = m.evaluate_delivery(deliveries[prof], prof, pool,
                                     m.rank_by_utility(deliveries[prof], prof))
            print(f"  {prof}: e2e={ev['e2e_pass']} R1={ev['R1']} R4={ev['R4']} "
                  f"D1={ev['D1']}({ev['D1_min_dist']:.4f}) D2={ev['D2']}(ranks {ev['D2_lambda_ranks']}) "
                  f"D3={ev['D3']}(pr {ev['D3_pair_ratio_range']:.1f}pp/stem {ev['D3_stem_range']}bp) "
                  f"constraint_rate={ev['constraint_rate']:.2f}")


if __name__ == "__main__":
    run()
