"""EXPERIMENT 42 (2026-09-14 programme) — E21 bare-LLM baseline arm (no tools).

Registered identity: DECISIONS.md Part 4 "E21 — Bare-LLM arm", execution
registration 2026-09-14 (user-approved). Shared harness:
``experiments/e21_e22_baseline_harness.py``.

PRE-REGISTRATION

Hypothesis (floor measurement, not improvement)
    The tool-free LLM (DeepSeek deepseek-v4-pro, temperature 0, zero- and
    few-shot prompting, no tool access) cannot deliver structurally valid RNA
    design outputs on most of the eleven workflows — expected near-zero
    delivery on structure/coordinate/long-optimization tasks, possibly
    non-zero on short-sequence composition — and emits quantitative claims
    at a high unverifiable rate (it cannot recompute what it asserts). A
    zero-everywhere result is a valid recorded floor, not a failed run.

Sample
    The current 31-session PA suite (PA_006–PA_036, all 11 workflows, all
    turns per session — identical inputs to the frozen Exp-41/Exp-24
    platform arm), x two prompting regimes (zero-shot, few-shot) = 62
    arm-sessions; every turn is one user message and one model answer
    (conversation accumulates within a session, mirroring the platform's
    multi-turn form interaction).

Instrument
    Exactly one LLM call per turn per regime (plus one transport-level retry
    on API errors only — the exp5 disclosed convention; it cannot alter the
    measured behaviour). No tools, no file access beyond the harness's
    registered fixture-inlining rule (<= 20 KB verbatim, else head-only).
    max_tokens 8192 (a coordinate-heavy tertiary answer that does not fit is
    itself part of the floor). Few-shot regime: two registered schema-shape
    worked examples (below, verbatim) — they demonstrate the JSON envelope
    only and contain no adjudication hints.

Adjudication (deterministic, harness rules — DECISIONS Part-4 registration)
    Delivery = the turn's parsed JSON satisfies the workflow's output
    contract with >= 1 structurally valid candidate (or a valid metric /
    prediction block); validity = per-workflow structural recomputation
    (length / alphabet / translation identity / complementarity / PAM
    adjacency / window substring / PDB parse). Claims: e3-blind-adjudicator
    rules generalized — metric claims recomputed exactly (GC/U locally; CAI
    via the audited local Kazusa tool pass; MFE via LinearFold where
    registered); affinity / binding / MRL / IRES-probability claims carry no
    admissible truth basis and are unverifiable for every arm symmetrically;
    IRES literature-anchor sequences carry literature ground-truth labels.

Metrics
    Primary: per-turn delivery rate by workflow x regime (the tool-free
    floor). Secondary: per-session success (all turns delivered);
    FP/(FP+TP) with Wilson 95% CI on recomputable claims; unverifiable-claim
    share; claim counts per turn; wall-clock and LLM calls.

Pilot (n = 6 sessions, 6 workflows)
    PA_006 (siRNA), PA_009 (aptamer), PA_013 (tertiary), PA_015 (CDS),
    PA_018 (secondary structure), PA_024 (full-length) — both regimes.
    Pilot passes if all records are well-formed (parsed or parse-errored
    with the raw retained) and the harness adjudicates without crashes;
    effect magnitude is NOT a pilot gate (a zero floor is a valid result).

Usage
    PYTHONPATH=. python experiments/exp42_bare_llm_baseline.py --pilot
    PYTHONPATH=. python experiments/exp42_bare_llm_baseline.py --resume
    PYTHONPATH=. python experiments/exp42_bare_llm_baseline.py --adjudate
Records: ``experiments/results/exp42_bare_llm_baseline/`` (runs.jsonl,
adjudicated.jsonl, summary.json, scratch/).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.e21_e22_baseline_harness import (  # noqa: E402
    adjudicate_claims,
    append_jsonl,
    check_response,
    complete_tool_metrics,
    load_jsonl,
    load_pa_tasks,
    parse_json_object,
    platform_budgets,
    render_turn_brief,
    utc_iso,
)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp42_bare_llm_baseline"
RUNS = RESULTS_DIR / "runs.jsonl"

PILOT_TASKS = ["006", "009", "013", "015", "018", "024"]
REGIMES = ("zeroshot", "fewshot")

SYSTEM_ZEROSHOT = (
    "You are an RNA design agent operating without any external tools. "
    "Complete the task exactly per the OUTPUT CONTRACT in the user message. "
    "Reply with a single JSON object and nothing else."
)

# Registered few-shot examples (schema-shape only; verbatim).
FEWSHOT_EXAMPLES = """Example task (schema demonstration):
TASK (RNA design agent benchmark, workflow: toy_gc_optimization)
PARAMETERS: initial_sequence: "GGUAUUGAUUC"; target GC band [0.45, 0.65]
Correct reply shape:
{"candidates": [{"id": "c1", "sequence": "GGCACUGGUCC"}],
 "claims": [{"claim_id": "c1", "text": "The delivered sequence has GC content 0.636.", "claim_type": "metric", "metric": "gc_content", "asserted_value": 0.636, "asserted_best_id": null, "scope": "absolute", "basis": "self_computation"}]}

Example task (schema demonstration, scoring type):
TASK (RNA design agent benchmark, workflow: toy_sequence_scoring)
PARAMETERS: sequence: "AUGGCAAAG"
Correct reply shape:
{"metrics": {"cai": 0.71, "gc_content": 0.556, "mfe_kcal_mol": -2.3},
 "claims": [{"claim_id": "c1", "text": "The GC content of the sequence is 0.556.", "claim_type": "metric", "metric": "gc_content", "asserted_value": 0.556, "asserted_best_id": null, "scope": "absolute", "basis": "self_computation"}]}"""


def build_llm():
    from agent_core.llm_config import get_deepseek_llm

    return get_deepseek_llm(model="deepseek-v4-pro", temperature=0)


def invoke(llm, messages) -> str:
    last_exc: Exception | None = None
    for attempt in range(2):  # one transport-level retry only (disclosed)
        try:
            raw = llm.invoke(messages)
            return raw.content if hasattr(raw, "content") else str(raw)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt == 0:
                time.sleep(5)
    raise RuntimeError(f"LLM call failed after one retry: {last_exc}")


def run_session(task: dict, regime: str, budgets: dict) -> list[dict]:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    llm = build_llm()
    session_id = f"exp42_{regime}_{task['pa_id'].lower()}"
    records: list[dict] = []
    messages = [SystemMessage(content=SYSTEM_ZEROSHOT)]
    if regime == "fewshot":
        messages[0] = SystemMessage(content=SYSTEM_ZEROSHOT + "\n\n" + FEWSHOT_EXAMPLES)

    for turn_idx, params in enumerate(task["turns"], start=1):
        brief = render_turn_brief(task["workflow"], turn_idx, params)
        messages.append(HumanMessage(content=brief))
        started = time.perf_counter()
        api_error = None
        raw = ""
        try:
            raw = invoke(llm, messages)
        except Exception as exc:  # noqa: BLE001
            api_error = str(exc)
        elapsed = round(time.perf_counter() - started, 3)
        parsed = parse_json_object(raw) if raw else {}
        messages.append(AIMessage(content=raw if raw else "(no response)"))
        records.append(
            {
                "session_id": session_id,
                "pa_id": task["pa_id"],
                "workflow": task["workflow"],
                "regime": regime,
                "turn": turn_idx,
                "brief_chars": len(brief),
                "raw_response": raw[:20000],
                "parsed": parsed if not parsed.get("_parse_error") else None,
                "parse_error": bool(parsed.get("_parse_error")),
                "api_error": api_error,
                "llm_calls": 1,
                "elapsed_seconds": elapsed,
                "platform_llm_budget": budgets.get(task["pa_id"], {}).get("llm_calls"),
                "timestamp": utc_iso(),
            }
        )
    return records


def run_units(units: list[tuple[dict, str]], budgets: dict, workers: int) -> None:
    done = {(r["session_id"]) for r in load_jsonl(RUNS)}
    todo = [(t, rg) for (t, rg) in units if f"exp42_{rg}_{t['pa_id'].lower()}" not in done]
    print(f"units to run: {len(todo)} (skipped {len(units) - len(todo)} already recorded)")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_session, t, rg, budgets): (t["pa_id"], rg) for t, rg in todo}
        for fut in as_completed(futures):
            pa_id, rg = futures[fut]
            try:
                recs = fut.result()
                for r in recs:
                    append_jsonl(RUNS, r)
                print(f"  done {pa_id} {rg}: {len(recs)} turns", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"  FAILED {pa_id} {rg}: {exc}", flush=True)


def cmd_adjudate() -> int:
    from agent_core.calibrated.runtime import runtime_from_env
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    runtime_from_env()
    executor = ToolExecutor(build_default_tool_registry())
    scratch = RESULTS_DIR / "scratch"
    tasks = {t["pa_id"]: t for t in load_pa_tasks()}
    from experiments.e21_e22_baseline_harness import platform_reference_quality

    refs = platform_reference_quality()
    rows = load_jsonl(RUNS)
    out_rows: list[dict] = []
    for r in rows:
        task = tasks[r["pa_id"]]
        params = task["turns"][r["turn"] - 1]
        parsed = r.get("parsed") or {}
        checks = check_response(task["workflow"], params, parsed)
        if r.get("api_error") or r.get("parse_error"):
            checks = {
                "delivered": False,
                "envelope_reasons": ["api_error" if r.get("api_error") else "unparseable response"],
                "n_candidates": 0,
                "n_valid": 0,
                "candidates": [],
                "metrics": {},
                "predictions": [],
            }
        elif checks["delivered"] or checks["n_candidates"]:
            ref_list = refs.get(r["pa_id"]) or []
            ref_turn = ref_list[r["turn"] - 1] if r["turn"] - 1 < len(ref_list) else None
            complete_tool_metrics(
                executor, task["workflow"], params, checks, parsed, scratch, ref_turn=ref_turn
            )
        claims = adjudicate_claims(task["workflow"], params, parsed, checks) if parsed else []
        row = dict(r)
        row.pop("raw_response", None)
        row["checks"] = checks
        row["claim_verdicts"] = claims
        out_rows.append(row)

    out = RESULTS_DIR / "adjudicated.jsonl"
    out.write_text(
        "".join(json_line + "\n" for json_line in _dumps_rows(out_rows)), encoding="utf-8"
    )
    _write_summary(out_rows, RESULTS_DIR / "summary.json")
    print(f"adjudicated -> {out}")
    return 0


def _dumps_rows(rows: list[dict]) -> list[str]:
    import json

    return [json.dumps(r, ensure_ascii=True, default=str) for r in rows]


def _wilson(k: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return None, None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return round(centre - half, 4), round(centre + half, 4)


def _write_summary(rows: list[dict], path: Path) -> None:
    import json
    from collections import defaultdict

    by_wf: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        by_wf[r["workflow"]].setdefault(r["regime"], {"turns": 0, "delivered": 0})
        by_wf[r["workflow"]][r["regime"]]["turns"] += 1
        by_wf[r["workflow"]][r["regime"]]["delivered"] += int(bool(r["checks"]["delivered"]))

    claims = [c for r in rows for c in r["claim_verdicts"]]
    rate_denom = [c for c in claims if c["verdict"] in ("TP", "FP")]
    n_fp = sum(1 for c in rate_denom if c["verdict"] == "FP")
    summary = {
        "n_turn_records": len(rows),
        "n_api_errors": sum(1 for r in rows if r.get("api_error")),
        "n_parse_errors": sum(1 for r in rows if r.get("parse_error")),
        "delivery_by_workflow_regime": {
            wf: {rg: v for rg, v in regs.items()} for wf, regs in by_wf.items()
        },
        "overall_delivery": {
            rg: sum(v["delivered"] for wf in by_wf.values() for k, v in wf.items() if k == rg)
            for rg in REGIMES
        },
        "claims": {
            "n": len(claims),
            "tp": sum(1 for c in claims if c["verdict"] == "TP"),
            "fp": n_fp,
            "unverifiable": sum(1 for c in claims if c["verdict"] == "unverifiable"),
            "borderline": sum(1 for c in claims if c["verdict"] == "borderline"),
            "fp_rate": round(n_fp / len(rate_denom), 4) if rate_denom else None,
            "fp_rate_ci": _wilson(n_fp, len(rate_denom)),
            "unverifiable_share": round(
                sum(1 for c in claims if c["verdict"] == "unverifiable") / len(claims), 4
            ) if claims else None,
        },
        "wall_seconds_total": round(sum(r.get("elapsed_seconds", 0) for r in rows), 1),
    }
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=True, default=str), encoding="utf-8")
    print(f"summary -> {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--adjudate", action="store_true")
    ap.add_argument("--regime", choices=REGIMES, default=None)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    if args.adjudate:
        return cmd_adjudate()

    budgets = platform_budgets()
    tasks = load_pa_tasks(only=PILOT_TASKS if args.pilot else None)
    if args.regime:
        units = [(t, args.regime) for t in tasks]
    else:
        units = [(t, rg) for t in tasks for rg in REGIMES]
    run_units(units, budgets, args.workers)
    if args.pilot:
        print("pilot complete — adjudate with --adjudate before judging")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
