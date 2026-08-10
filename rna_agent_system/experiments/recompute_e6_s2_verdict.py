#!/usr/bin/env python3
"""E6 S2 聚合复算判定。

语义(§20 拍板口径 + HANDOFF_2026-08-09):e6_verdict_s2.json 是逐靶覆盖的
单靶态判定书(中间 NO-GO 不算数);最终判定 = 以 e6_s2_runs.jsonl 全部 18 条
聚合复算,逻辑与 run_e6_gennav.py 的 run_s2 判定段逐行一致。

主终点 = per-profile JCD-pass(e2e∧D1∧D2∧R3)配对 McNemar(C vs A, n=54) p<0.05
         且 c_e2e_gene≥0.8
辅终点 = 连续复合得分(0.4×e2e+0.2×约束率+0.2×D1/D2+0.2×R3)配对 Wilcoxon
         (C vs A) p<0.05 且 质量判据(R1&R4&R3&D1&D2&D3 全过 + E14 ge_3)
         且 约束率 C≥0.9
go = 主或辅任一过;主过辅不过须披露(endpoint2_not_passed_disclosed)
C vs B 仅披露不参与 gate(S2 为 A/C 双臂)。

用法: cd rna_agent_system && python experiments/recompute_e6_s2_verdict.py
输出: 终端 + results/e6_s2_verdict_aggregated.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

import scipy.stats as scipy_stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # PROJECT_ROOT(同 run_e6_gennav.py:65)

from experiments import run_e5_constraint_nav as m
from experiments.run_e6_gennav import composite_score, jcd_pass

RESULTS = Path(__file__).resolve().parent.parent / "experiments" / "results"
RUNS = RESULTS / "e6_s2_runs.jsonl"
OUT = RESULTS / "e6_s2_verdict_aggregated.json"


def load_records(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def main() -> int:
    recs = load_records(RUNS)
    if len(recs) != 18:
        print(f"[recompute] FATAL: expected 18 records, got {len(recs)}", file=sys.stderr)
        return 2
    ev = {c["target_id"]: c["evaluations"] for c in recs}
    targets = list(ev)

    def paired(arm_x: str, arm_y: str) -> tuple[list[bool], list[bool], list[float], list[float]]:
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
        p = float(scipy_stats.binomtest(min(b, c_), b + c_, 0.5,
                                        alternative="two-sided").pvalue) if b + c_ > 0 else 1.0
        return {"b": b, "c": c_, "p": p}

    def wilcoxon_p(x: list[float], y: list[float]) -> float:
        diffs = [b - a for a, b in zip(x, y) if abs(b - a) > 1e-12]
        if len(diffs) < 2:
            return 1.0
        return float(scipy_stats.wilcoxon(diffs).pvalue)

    mc_ca = mcnemar(*paired("C", "A")[:2])
    # S2 为 A/C 双臂(§20),B 臂不存在 → C vs B 披露字段为空
    mc_cb = None
    _, _, cx_ca, cy_ca = paired("C", "A")
    w_ca = wilcoxon_p(cx_ca, cy_ca)

    c_arms = [ev[t].get("C") for t in targets]
    c_e2e_gene = mean(all(p["e2e_pass"] for p in e["profiles"]) for e in c_arms) if c_arms else 0.0
    quality = (bool(c_arms)
               and all(p["R1"] and p["R4"] for e in c_arms for p in e["profiles"])
               and all(e["R3"] for e in c_arms)
               and all(p["D1"] and p["D2"] and p["D3"] for e in c_arms
                       for p in e["profiles"])
               and all((e.get("lattice_plan") or {}).get("e14_declaration", {}).get(
                   "ge_3") for e in c_arms))
    crit_constraint = (mean(mean(p["constraint_rate"] for p in e["profiles"])
                            for e in c_arms) >= 0.9) if c_arms else False

    endpoint1 = (mc_ca is not None and mc_ca["p"] < 0.05 and c_e2e_gene >= 0.8)
    endpoint2 = (w_ca < 0.05 and quality and crit_constraint)
    disclosed = bool(endpoint1 and not endpoint2)
    go = endpoint1 or endpoint2

    verdict = {
        "stage": "s2", "aggregation": "recomputed from e6_s2_runs.jsonl (18 records)",
        "criteria": {
            "mcnemar_C_vs_A_p<0.05": (mc_ca or {}).get("p"),
            "mcnemar_C_vs_B_p<0.05": (mc_cb or {}).get("p"),
            "wilcoxon_C_vs_A_p<0.05": w_ca,
            "endpoint1_jcd_mcnemar": endpoint1,
            "endpoint2_composite_wilcoxon": endpoint2,
            "constraint_rate_C_ge_0.9": crit_constraint,
        },
        "observed": {
            "c_e2e_gene": c_e2e_gene,
            "mcnemar": {"C_vs_A": mc_ca, "C_vs_B": mc_cb},
            "wilcoxon": {"C_vs_A": w_ca},
            "n_pairs": len(targets) * len(m.PROFILE_DEFS),
            "quality": {
                "R1_R4_all_profiles": all(p["R1"] and p["R4"]
                                          for e in c_arms for p in e["profiles"]),
                "R3_all_arms": all(e["R3"] for e in c_arms),
                "D1_D2_D3_all_profiles": all(p["D1"] and p["D2"] and p["D3"]
                                             for e in c_arms for p in e["profiles"]),
                "E14_gen_lattice_ge3_all": all(
                    (e.get("lattice_plan") or {}).get("e14_declaration", {}).get("ge_3")
                    for e in c_arms),
            },
        },
        "endpoint1": endpoint1, "endpoint2": endpoint2,
        "endpoint2_not_passed_disclosed": disclosed,
        "go_no_go": "GO" if go else "NO-GO",
    }
    OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    print(f"\n[recompute] aggregated verdict -> {OUT}")
    return 0 if go else 1


if __name__ == "__main__":
    sys.exit(main())
