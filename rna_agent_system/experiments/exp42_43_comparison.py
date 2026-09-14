"""E21/E22 three-arm comparison analysis (2026-09-14 programme).

Reads the adjudicated baseline records (Exp 42 bare-LLM, Exp 43 ReAct) and
the frozen platform arm (Exp 41 Block A records + session
``workflow_results_*.json``), applies the SAME harness validity rules to all
three arms (the registered symmetric-validity move), and emits the
comparison tables + paired statistics.

Deterministic: given the adjudicated JSONL files, the summary is recomputed
identically (``--verify`` asserts byte-identity).

Usage
    PYTHONPATH=. python experiments/exp42_43_comparison.py
    PYTHONPATH=. python experiments/exp42_43_comparison.py --verify
Records: ``experiments/results/exp42_43_comparison/`` (comparison.json,
table.md).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.e21_e22_baseline_harness import (  # noqa: E402
    check_response,
    load_jsonl,
    load_pa_tasks,
    platform_budgets,
)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
OUT_DIR = RESULTS_DIR / "exp42_43_comparison"

EXP42_ADJ = RESULTS_DIR / "exp42_bare_llm_baseline" / "adjudicated.jsonl"
EXP43_ADJ = RESULTS_DIR / "exp43_react_baseline" / "adjudicated.jsonl"


# ── platform arm: envelope mapping + symmetric re-adjudication ───────────────


def platform_envelope(workflow: str, d: dict) -> dict:
    """Map a frozen platform workflow result into the arm output contract."""
    cands = d.get("candidates") or []
    if workflow == "rna_tertiary_structure_design":
        return {
            "candidates": [
                {
                    "id": c.get("id"),
                    "structure": (c.get("metadata") or {}).get("structure_path")
                    or (c.get("scores") or {}).get("rhofold_pdb_path")
                    or "",
                }
                for c in cands
            ]
        }
    if workflow == "ires_prediction":
        preds = []
        for c in cands:
            md = c.get("metadata") or {}
            sc = c.get("scores") or {}
            prob = sc.get("ires_probability", sc.get("probability", 0.5))
            preds.append(
                {"sequence_id": md.get("sequence_id") or c.get("id"), "probability": prob}
            )
        return {"predictions": preds, "claims": []}
    if workflow == "mrna_sequence_scoring":
        sc = (cands[0].get("scores") or {}) if cands else {}
        return {
            "metrics": {
                "cai": sc.get("cai", sc.get("cai_score")),
                "gc_content": sc.get("gc_content"),
                "mfe_kcal_mol": sc.get("mfe", sc.get("vienna_mfe")),
            },
            "claims": [],
        }
    if workflow == "rna_small_molecule_interaction":
        sc = (cands[0].get("scores") or {}) if cands else {}
        key = next(
            (k for k in sc if "rnasmol" in k or "binding" in k or "prob" in k), None
        )
        return {
            "metrics": {"binding_probability": sc.get(key) if key else 0.5},
            "claims": [],
        }
    return {
        "candidates": [{"id": c.get("id"), "sequence": c.get("sequence", "")} for c in cands],
        "claims": [],
    }


def platform_arm_turns() -> dict[tuple[str, int], dict]:
    """{(pa_id, turn): record} for the frozen platform arm."""
    tasks = {t["pa_id"]: t for t in load_pa_tasks()}
    out: dict[tuple[str, int], dict] = {}
    for pa_id, t in tasks.items():
        num = pa_id.lower().split("_")[1]
        files = []
        for sd in sorted((PROJECT_ROOT / "workspace" / "sessions").glob(f"exp41_full_pa{num}_*")):
            files.extend(sd.glob("workflow_results_*.json"))
        loaded = []
        for f in files:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            loaded.append((d.get("timestamp") or "", d))
        loaded.sort(key=lambda x: x[0])
        for i, (_, d) in enumerate(loaded):
            if i >= len(t["turns"]):
                break
            env = platform_envelope(t["workflow"], d)
            has_payload = bool(env.get("candidates") or env.get("predictions") or env.get("metrics"))
            if not has_payload:
                # Registered recovery (2026-09-14, unified n=96): a successful
                # platform turn with no candidates on a prediction workflow is
                # a valid NEGATIVE answer ("no IRES candidate regions found"
                # — the frozen record's own summary), mapped to the harness's
                # symmetric negative-answer form.
                if d.get("success") and t["workflow"] == "ires_prediction":
                    env = {"predictions": [], "negative_answer": True}
                else:
                    continue
            checks = check_response(t["workflow"], t["turns"][i], env)
            if env.get("negative_answer"):
                checks["envelope_reasons"] = [
                    "platform negative answer (workflow success; frozen summary: "
                    + str(d.get("summary", ""))[:80] + ")"
                ]
            out[(pa_id, i + 1)] = {
                "pa_id": pa_id,
                "workflow": t["workflow"],
                "arm": "platform",
                "turn": i + 1,
                "checks": checks,
            }
    return out


# ── statistics ────────────────────────────────────────────────────────────────


def wilson_ci(k: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return None, None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return round(centre - half, 4), round(centre + half, 4)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact binomial McNemar p on discordant counts (b, c)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2**n)
    return min(1.0, 2 * tail)


def arm_turns(rows: list[dict], arm_key: str, arm_val: str) -> dict[tuple[str, int], dict]:
    out = {}
    for r in rows:
        if r.get(arm_key) != arm_val:
            continue
        out[(r["pa_id"], r["turn"])] = r
    return out


def delivery_rate(turns: dict[tuple[str, int], dict]) -> tuple[int, int]:
    n = len(turns)
    k = sum(1 for r in turns.values() if r["checks"]["delivered"])
    return k, n


def claims_block(rows: list[dict], arm_key: str, arm_val: str) -> dict:
    claims = [
        c for r in rows if r.get(arm_key) == arm_val for c in r.get("claim_verdicts", [])
    ]
    denom = [c for c in claims if c["verdict"] in ("TP", "FP")]
    n_fp = sum(1 for c in denom if c["verdict"] == "FP")
    n_tp = len(denom) - n_fp
    unver = sum(1 for c in claims if c["verdict"] == "unverifiable")
    return {
        "n_claims": len(claims),
        "tp": n_tp,
        "fp": n_fp,
        "unverifiable": unver,
        "fp_rate": round(n_fp / len(denom), 4) if denom else None,
        "fp_rate_ci": wilson_ci(n_fp, len(denom)),
        "unverifiable_share": round(unver / len(claims), 4) if claims else None,
    }


def build_comparison() -> dict:
    tasks = {t["pa_id"]: t for t in load_pa_tasks()}
    budgets = platform_budgets()
    platform = platform_arm_turns()
    exp42 = load_jsonl(EXP42_ADJ)
    exp43 = load_jsonl(EXP43_ADJ)

    arms: dict[str, dict[tuple[str, int], dict]] = {"platform": platform}
    arms["bare_zeroshot"] = arm_turns(exp42, "regime", "zeroshot")
    arms["bare_fewshot"] = arm_turns(exp42, "regime", "fewshot")
    for tier in ("matched", "3x", "10x"):
        arms[f"react_{tier}"] = arm_turns(exp43, "tier", tier)

    by_wf: dict[str, dict[str, tuple[int, int]]] = defaultdict(dict)
    for arm, turns in arms.items():
        wf_agg: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for r in turns.values():
            wf_agg[r["workflow"]][0] += int(r["checks"]["delivered"])
            wf_agg[r["workflow"]][1] += 1
        for wf, (k, n) in wf_agg.items():
            by_wf[wf][arm] = (k, n)

    paired = {}
    for arm in ("bare_zeroshot", "bare_fewshot", "react_matched", "react_3x", "react_10x"):
        common = set(platform) & set(arms[arm])
        b = sum(1 for k in common if platform[k]["checks"]["delivered"] and not arms[arm][k]["checks"]["delivered"])
        c = sum(1 for k in common if not platform[k]["checks"]["delivered"] and arms[arm][k]["checks"]["delivered"])
        paired[arm] = {
            "n_common_turns": len(common),
            "platform_only_delivered": b,
            "baseline_only_delivered": c,
            "mcnemar_p": round(mcnemar_exact(b, c), 6),
        }

    # bare-LLM vs ReAct-10x paired (the reader-facing "why does bare tie ReAct" check)
    bz, r10 = arms["bare_zeroshot"], arms["react_10x"]
    common = set(bz) & set(r10)
    b = sum(1 for k in common if bz[k]["checks"]["delivered"] and not r10[k]["checks"]["delivered"])
    c = sum(1 for k in common if not bz[k]["checks"]["delivered"] and r10[k]["checks"]["delivered"])
    paired["react_10x_vs_bare_zeroshot"] = {
        "n_common_turns": len(common),
        "bare_only_delivered": b,
        "react_only_delivered": c,
        "mcnemar_p": round(mcnemar_exact(b, c), 6),
    }

    # failure-mode decomposition (why a turn is not delivered)
    def fail_mode(r: dict) -> str:
        chk = r["checks"]
        if chk["delivered"]:
            return "delivered"
        if r.get("budget_exhausted") and not r.get("submitted"):
            return "budget_exhausted_no_answer"
        if r.get("api_error") or r.get("parse_error") or r.get("submitted_parse_failed"):
            return "no_parseable_answer"
        if any("parity bar" in x or "platform candidates are" in x for x in chk.get("envelope_reasons", [])):
            return "answered_below_platform_quality_parity"
        return "answered_structurally_invalid"

    fail_modes: dict[str, dict[str, int]] = {}
    for arm in ("bare_zeroshot", "bare_fewshot", "react_matched", "react_3x", "react_10x"):
        agg: dict[str, int] = defaultdict(int)
        for r in arms[arm].values():
            agg[fail_mode(r)] += 1
        fail_modes[arm] = dict(agg)

    # design-only subaggregate (prediction-type turns deliver at schema level
    # for every arm; the design workflows carry the structural signal)
    PREDICTION_WFS = {"ires_prediction", "rna_small_molecule_interaction", "mrna_sequence_scoring"}
    design_only = {}
    for arm, turns in arms.items():
        k = sum(1 for r in turns.values() if r["workflow"] not in PREDICTION_WFS and r["checks"]["delivered"])
        n = sum(1 for r in turns.values() if r["workflow"] not in PREDICTION_WFS)
        design_only[arm] = {"delivered": k, "turns": n}

    summary = {
        "delivery_by_workflow": {
            wf: {arm: {"delivered": k, "turns": n} for arm, (k, n) in regs.items()}
            for wf, regs in by_wf.items()
        },
        "overall_delivery": {
            arm: dict(zip(("delivered", "turns"), delivery_rate(turns))) for arm, turns in arms.items()
        },
        "design_only_delivery": design_only,
        "failure_modes": fail_modes,
        "paired_vs_platform": paired,
        "claims": {
            "platform": {
                "note": "single-workflow PA sessions publish 0 claims by construction "
                "(ClaimGate is pipeline-synthesis-only; see Exp-41 Block B)",
                "n_claims": 0,
            },
            "bare_zeroshot": claims_block(exp42, "regime", "zeroshot"),
            "bare_fewshot": claims_block(exp42, "regime", "fewshot"),
            **{f"react_{t}": claims_block(exp43, "tier", t) for t in ("matched", "3x", "10x")},
        },
        "efficiency": {
            "platform": {
                "llm_calls_total": sum(v["llm_calls"] for v in budgets.values()),
                "note": "frozen Exp-41 Block A; wall-time under the disclosed concurrent-load convention",
            },
            "bare_llm": {
                "llm_calls_total": len(exp42),
                "wall_seconds_total": round(sum(r.get("elapsed_seconds", 0) for r in exp42), 1),
            },
            "react": {
                tier: {
                    "llm_calls_total": sum(
                        r.get("llm_calls", 0) for r in exp43 if r.get("tier") == tier
                    ),
                    "tool_calls_total": sum(
                        r.get("tool_calls", 0) for r in exp43 if r.get("tier") == tier
                    ),
                    "wall_seconds_total": round(
                        sum(r.get("elapsed_seconds", 0) for r in exp43 if r.get("tier") == tier), 1
                    ),
                }
                for tier in ("matched", "3x", "10x")
            },
        },
        "n_exp42_rows": len(exp42),
        "n_exp43_rows": len(exp43),
        "n_platform_turns": len(platform),
    }
    return summary


def write_outputs(summary: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "comparison.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, default=str), encoding="utf-8"
    )
    lines = [
        "# E21/E22 three-arm comparison (Exp 41 platform / Exp 42 bare-LLM / Exp 43 ReAct)",
        "",
        "Per-turn delivered validity by workflow (delivered/turns):",
        "",
        "| workflow | platform | bare zero | bare few | ReAct matched | ReAct 3x | ReAct 10x |",
        "|---|---|---|---|---|---|---|",
    ]
    for wf in sorted(summary["delivery_by_workflow"]):
        cells = []
        for arm in ("platform", "bare_zeroshot", "bare_fewshot", "react_matched", "react_3x", "react_10x"):
            cell = summary["delivery_by_workflow"][wf].get(arm)
            cells.append(f"{cell['delivered']}/{cell['turns']}" if cell else "—")
        lines.append(f"| {wf} | " + " | ".join(cells) + " |")
    lines += ["", "Design-workflow turns only (prediction-type turns excluded):", ""]
    lines.append("| arm | delivered/turns |")
    lines.append("|---|---|")
    for arm, d in summary["design_only_delivery"].items():
        lines.append(f"| {arm} | {d['delivered']}/{d['turns']} |")
    lines += ["", "Non-delivery decomposition:", ""]
    lines.append("| arm | budget-exhausted | no parseable answer | below platform quality parity | structurally invalid |")
    lines.append("|---|---|---|---|---|")
    for arm, m in summary["failure_modes"].items():
        lines.append(
            f"| {arm} | {m.get('budget_exhausted_no_answer', 0)} | {m.get('no_parseable_answer', 0)} | "
            f"{m.get('answered_below_platform_quality_parity', 0)} | {m.get('answered_structurally_invalid', 0)} |"
        )
    lines += ["", "Paired vs platform (exact McNemar on per-turn delivery):", ""]
    for arm, p in summary["paired_vs_platform"].items():
        if "react_10x_vs_bare_zeroshot" in arm:
            lines.append(
                f"- {arm}: bare-only {p['bare_only_delivered']}, react-only "
                f"{p['react_only_delivered']}, n = {p['n_common_turns']}, p = {p['mcnemar_p']}"
            )
        else:
            lines.append(
                f"- {arm}: platform-only {p['platform_only_delivered']}, baseline-only "
                f"{p['baseline_only_delivered']}, n = {p['n_common_turns']}, p = {p['mcnemar_p']}"
            )
    (OUT_DIR / "table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"comparison -> {OUT_DIR / 'comparison.json'}")
    print(f"table -> {OUT_DIR / 'table.md'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    summary = build_comparison()
    if args.verify:
        again = build_comparison()
        a = json.dumps(summary, sort_keys=True, default=str)
        b = json.dumps(again, sort_keys=True, default=str)
        assert a == b, "verify: recomputation mismatch"
        print("verify: byte-identical recomputation OK")
    write_outputs(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
