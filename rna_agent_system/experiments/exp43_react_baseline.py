"""EXPERIMENT 43 (2026-09-14 programme) — E22 same-tools ReAct baseline arm.

Registered identity: DECISIONS.md Part 4 "E22 — ReAct arm (same 41 tools,
generic agent loop) vs the platform", execution + budget-tier registration
2026-09-14 (user-approved). Shared harness:
``experiments/e21_e22_baseline_harness.py``.

PRE-REGISTRATION

Hypothesis (measurement, not improvement)
    A thin generic ReAct loop driving the same 41 platform tools through the
    same audited ``ToolExecutor`` (same LLM: deepseek-v4-pro, temperature 0)
    under-references the platform arm: lower per-turn delivered validity at
    the platform-matched budget, and — where it succeeds — natural-language
    claims whose ungated false-positive rate approaches the ungated-control
    class (the ~54.5% registered rate) instead of the gated platform's zero.
    Pre-registered expectation: the platform wins through deterministic
    workflows + CapGate governance, not LLM cleverness.

Budget tiers (registered amendment, user direction 2026-09-14)
    Primary "matched": per-session LLM cap = the platform arm's measured
    LLM calls (frozen Exp-41 Block A; 0 for the eight deterministic-workflow
    sessions — degenerate by construction, recorded as the measured floor).
    Disclosed generous tiers 3x and 10x of the tier base
    ``max(platform_llm_calls, 2 x n_turns)``. The session LLM budget is
    allocated evenly across the session's turns. Candidate budget at every
    tier = the platform evaluated-candidate count (generator-requested
    sample counts are summed and further generator calls blocked at the cap).

Sample
    The current 31-session PA suite (all 11 workflows, all turns), x three
    tiers = 93 arm-sessions. Identical turn briefs to E21 / the platform arm.

Instrument
    Text-JSON ReAct protocol: each model reply is
    ``{"thought", "action", "action_input"}``; action = a tool name or
    ``submit`` (carrying the OUTPUT-CONTRACT final answer). Tools execute
    via ``ToolExecutor.run_tool`` — every call lands in the platform audit
    trail; ``RNADA_CAPGATE=advisory`` (identical governance setting to the
    platform PA arm). Observations are returned to the model truncated
    (2,000 chars). One transport-level retry per LLM call (disclosed). No
    other scaffolding: no planning stage, no retries on tool failure beyond
    the model's own next action, no oracle gating of the model's claims.

Adjudication (deterministic, harness rules — identical to E21)
    Per-turn delivery = OUTPUT-CONTRACT JSON with >= 1 structurally valid
    candidate / valid metric block; claims by the generalized e3 blind
    adjudicator (recomputable metrics recomputed; affinity/binding/MRL/
    IRES-probability unverifiable for every arm symmetrically).

Metrics
    Primary: per-turn delivered validity by workflow x tier, paired against
    the platform arm (frozen Exp-41) on the same sessions. Secondary:
    FP/(FP+TP) with Wilson 95% CI; unverifiable-claim share; LLM calls;
    tool-call counts and failure rate; wall-clock.

Pilot (n = 6 sessions, 10x tier)
    PA_006 (siRNA), PA_009 (aptamer), PA_013 (tertiary), PA_015 (CDS),
    PA_018 (secondary structure), PA_024 (full-length). Go-rule (the
    registered E22 gate): scale to the full matrix only if the pilot effect
    is in the expected direction (platform >= ReAct on delivered validity)
    on >= 4/6 sessions; otherwise record the boundary and stop.

Usage
    PYTHONPATH=. python experiments/exp43_react_baseline.py --pilot
    PYTHONPATH=. python experiments/exp43_react_baseline.py --resume
    PYTHONPATH=. python experiments/exp43_react_baseline.py --tier matched
    PYTHONPATH=. python experiments/exp43_react_baseline.py --adjudate
Records: ``experiments/results/exp43_react_baseline/`` (runs.jsonl,
adjudicated.jsonl, summary.json, scratch/, traces/).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.e21_e22_baseline_harness import (  # noqa: E402
    CONTRACT_BY_WORKFLOW,
    OUTPUT_CONTRACTS,
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

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp43_react_baseline"
RUNS = RESULTS_DIR / "runs.jsonl"

PILOT_TASKS = ["006", "009", "013", "015", "018", "024"]
TIERS = ("matched", "3x", "10x")
TURN_WALL_CAP_S = 3600.0  # Exp-8 amended per-run convention
OBSERVATION_CHARS = 2000

# Lanes: same-workflow sessions never overlap (Exp-24 convention);
# GPU-heavy workflow classes additionally limited (Exp-25 scheduler).
GPU_CLASS = {
    "rna_aptamer_design",
    "rna_tertiary_structure_design",
    "full_length_mrna_design",
    "mrna_cds_design",
}
GLOBAL_SEM = threading.Semaphore(6)
GPU_SEM = threading.Semaphore(3)

SYSTEM_TEMPLATE = """\
You are a ReAct-style RNA design agent. You complete RNA design/scoring
tasks by calling tools and reasoning over the observations.

Available tools ({n_tools} total):
{tool_list}

Protocol — reply with ONE JSON object per step:
{{"thought": "<one short sentence>", "action": "<tool name>", "action_input": {{<tool arguments as JSON>}}}}
When you have the final answer, reply:
{{"thought": "<one short sentence>", "action": "submit", "final_answer": {{<the OUTPUT CONTRACT JSON>}}}}

Rules: one action per step; wait for each OBSERVATION before the next step;
the final answer must follow the OUTPUT CONTRACT given in the task message;
you have a limited number of reasoning steps for this task — spend them on
the tool calls that matter."""


def build_llm():
    from agent_core.llm_config import get_deepseek_llm

    return get_deepseek_llm(model="deepseek-v4-pro", temperature=0)


def build_executor():
    from agent_core.calibrated.runtime import runtime_from_env
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from langchain_core.tools import tool as lc_tool

    runtime_from_env()
    registry = build_default_tool_registry()

    # Registered environment primitive (2026-09-14 amendment, DECISIONS Part 4):
    # the 41 production tools take `filepath` inputs that the platform's
    # workflows materialize internally; a generic tool-using scaffold cannot
    # operate without the same I/O capability. One utility tool, no oracle
    # semantics, no claim path; every call lands in the audit trail.
    @lc_tool
    def write_workspace_file(path: str, content: str) -> dict:
        """Write text content to a file under the workspace directory.

        Use this to materialize sequence/structure inputs that other tools
        require as files (e.g., a FASTA of a target sequence given in the
        task). Paths are resolved relative to workspace/; absolute paths
        outside workspace/ are rejected.
        """
        root = (PROJECT_ROOT / "workspace").resolve()
        p = Path(path)
        if not p.is_absolute():
            p = PROJECT_ROOT / "workspace" / p
        p = p.resolve()
        if root not in p.parents:
            return {"error": "path must stay under workspace/"}
        if len(content) > 5_000_000:
            return {"error": "content too large (5 MB limit)"}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "bytes_written": len(content.encode("utf-8"))}

    registry.register(write_workspace_file)
    return ToolExecutor(registry)


def tool_catalog() -> tuple[list[dict], str]:
    """(catalog entries, rendered system-prompt tool list)."""
    from agent_core import tools as tools_mod

    entries = []
    lines = []
    for t in tools_mod.ALL_LANGCHAIN_AGENT_TOOLS:
        args = json.dumps(t.args, ensure_ascii=True, default=str)
        if len(args) > 600:
            args = args[:600] + "...(truncated)"
        entries.append({"name": t.name, "description": t.description, "args": t.args})
        lines.append(f"- {t.name}: {t.description}\n  args: {args}")
    write_desc = (
        "Write text content to a file under the workspace directory. "
        "Materialize sequence/structure inputs that other tools require as "
        "files (e.g., a FASTA of a target sequence given in the task). "
        "Paths resolve relative to workspace/."
    )
    write_args = json.dumps(
        {
            "path": {"type": "string", "description": "relative path under workspace/"},
            "content": {"type": "string", "description": "file text content"},
        }
    )
    entries.append({"name": "write_workspace_file", "description": write_desc, "args": write_args})
    lines.append(
        f"- write_workspace_file (environment I/O primitive): {write_desc}\n  args: {write_args}"
    )
    return entries, "\n".join(lines)


_GENERATOR_HINT = re.compile(r"^(design_|build_)")
_REQUEST_KEYS = re.compile(r"^(n_samples|candidate_count|top_n|num_invocations|repeats)")


def _requested_candidates(args: dict) -> int:
    n = 0
    for k, v in args.items():
        if _REQUEST_KEYS.match(k) and isinstance(v, int):
            n += v
    return n or 1


def _result_candidates_count(result) -> int:
    try:
        raw = result.artifacts.get("result")
        if isinstance(raw, dict):
            for key in ("candidates", "sequences", "designed_sequences", "samples"):
                v = raw.get(key)
                if isinstance(v, list):
                    return len(v)
    except Exception:  # noqa: BLE001
        pass
    return 0


def observation_text(result) -> str:
    try:
        payload = {
            "success": result.success,
            "metrics": result.metrics,
            "error": result.error,
            "result": result.artifacts.get("result"),
        }
        text = json.dumps(payload, ensure_ascii=True, default=str)
    except Exception:  # noqa: BLE001
        text = str(result.artifacts)[:OBSERVATION_CHARS]
    if len(text) > OBSERVATION_CHARS:
        text = text[:OBSERVATION_CHARS] + "...(truncated)"
    return text


def tier_caps(task: dict, budget: dict) -> dict[str, int]:
    """Per-tier session LLM caps (registered formula)."""
    pl = budget.get("llm_calls", 0)
    n_turns = len(task["turns"])
    base = max(pl, 2 * n_turns)
    return {"matched": pl, "3x": 3 * base, "10x": 10 * base}


def run_turn(
    llm,
    executor,
    catalog_by_name: dict,
    messages: list,
    turn_llm_cap: int,
    cand_budget: int,
    cand_spent: int,
    trace: list,
) -> tuple[dict | None, int, int, list[dict]]:
    """One ReAct turn. Returns (final_answer, llm_calls, cand_spent, tool_log)."""
    from langchain_core.messages import AIMessage, HumanMessage

    llm_calls = 0
    tool_log: list[dict] = []
    while llm_calls < turn_llm_cap:
        try:
            raw = llm.invoke(messages)
        except Exception as exc:  # noqa: BLE001
            time.sleep(5)
            try:
                raw = llm.invoke(messages)
            except Exception as exc2:  # noqa: BLE001
                trace.append({"step": "llm_error", "error": str(exc2)})
                return None, llm_calls, cand_spent, tool_log
        llm_calls += 1
        content = raw.content if hasattr(raw, "content") else str(raw)
        action = parse_json_object(content)
        if action.get("_parse_error"):
            messages.append(AIMessage(content=content[:4000]))
            messages.append(
                HumanMessage(
                    content="OBSERVATION: your last reply was not a single JSON object. "
                    "Reply with exactly one JSON object per the protocol."
                )
            )
            trace.append({"step": "parse_error"})
            continue
        messages.append(AIMessage(content=json.dumps(action, ensure_ascii=True)[:4000]))
        act = action.get("action")
        if act == "submit":
            return action.get("final_answer"), llm_calls, cand_spent, tool_log
        if act not in catalog_by_name:
            messages.append(
                HumanMessage(
                    content=f"OBSERVATION: unknown action {act!r}. Use a tool name from the "
                    f"list or 'submit'."
                )
            )
            trace.append({"step": "unknown_action", "action": act})
            continue
        args = action.get("action_input") or {}
        if not isinstance(args, dict):
            args = {}
        # candidate budget enforcement (registered rule)
        if _GENERATOR_HINT.match(act):
            need = _requested_candidates(args)
            if cand_spent + need > cand_budget:
                messages.append(
                    HumanMessage(
                        content="OBSERVATION: candidate budget exhausted — you may not "
                        "generate more candidates. Proceed with what you have "
                        "(action 'submit')."
                    )
                )
                trace.append({"step": "generator_blocked", "action": act, "need": need})
                continue
        t0 = time.perf_counter()
        result = executor.run_tool(act, **args)
        elapsed = round(time.perf_counter() - t0, 3)
        if _GENERATOR_HINT.match(act):
            got = max(_requested_candidates(args), _result_candidates_count(result))
            cand_spent += got
        tool_log.append(
            {"tool": act, "success": result.success, "elapsed_seconds": elapsed}
        )
        messages.append(HumanMessage(content="OBSERVATION: " + observation_text(result)))
        trace.append({"step": "tool", "action": act, "success": result.success})
    # budget exhausted without submit (registered: recorded floor, no rescue call)
    trace.append({"step": "budget_exhausted"})
    return None, llm_calls, cand_spent, tool_log


def run_session(task: dict, tier: str, budgets: dict) -> list[dict]:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    llm = build_llm()
    executor = build_executor()
    catalog, tool_list = tool_catalog()
    catalog_by_name = {c["name"]: c for c in catalog}
    system = SYSTEM_TEMPLATE.format(n_tools=len(catalog), tool_list=tool_list)

    caps = tier_caps(task, budgets.get(task["pa_id"], {}))
    session_cap = caps[tier]
    n_turns = len(task["turns"])
    per_turn_cap = session_cap // n_turns if session_cap > 0 else 0
    cand_budget = budgets.get(task["pa_id"], {}).get("evaluated_candidates", 0)
    cand_spent = 0

    session_id = f"exp43_{tier}_{task['pa_id'].lower()}"
    records: list[dict] = []
    messages: list = [SystemMessage(content=system)]

    for turn_idx, params in enumerate(task["turns"], start=1):
        brief = render_turn_brief(task["workflow"], turn_idx, params)
        messages.append(HumanMessage(content=brief))
        trace: list[dict] = []
        t0 = time.perf_counter()
        final_answer, llm_calls, cand_spent, tool_log = run_turn(
            llm,
            executor,
            catalog_by_name,
            messages,
            per_turn_cap,
            cand_budget,
            cand_spent,
            trace,
        )
        elapsed = round(time.perf_counter() - t0, 3)
        submitted = final_answer if isinstance(final_answer, dict) else None
        messages.append(
            AIMessage(content=json.dumps(submitted, ensure_ascii=True)[:4000] if submitted else "(no final answer)")
        )
        records.append(
            {
                "session_id": session_id,
                "pa_id": task["pa_id"],
                "workflow": task["workflow"],
                "tier": tier,
                "turn": turn_idx,
                "turn_llm_cap": per_turn_cap,
                "llm_calls": llm_calls,
                "candidate_budget": cand_budget,
                "candidates_spent": cand_spent,
                "tool_calls": len(tool_log),
                "tool_log": tool_log[:60],
                "budget_exhausted": trace[-1].get("step") == "budget_exhausted" if trace else False,
                "submitted": submitted,
                "submitted_parse_failed": final_answer is not None and submitted is None,
                "trace_summary": trace[:120],
                "elapsed_seconds": elapsed,
                "platform_llm_budget": budgets.get(task["pa_id"], {}).get("llm_calls"),
                "timestamp": utc_iso(),
            }
        )
        # keep the conversation bounded: drop middle tool chatter, keep system + turns
        if len(messages) > 40:
            messages = [messages[0]] + messages[-30:]
    return records


def run_units(units: list[tuple[dict, str]], budgets: dict, workers: int) -> None:
    done = {r["session_id"] for r in load_jsonl(RUNS)}
    todo = [(t, tier) for (t, tier) in units if f"exp43_{tier}_{t['pa_id'].lower()}" not in done]
    print(f"units to run: {len(todo)} (skipped {len(units) - len(todo)} already recorded)", flush=True)
    # lanes: same-workflow sessions never overlap
    lanes: dict[str, list[tuple[dict, str]]] = {}
    for t, tier in todo:
        lanes.setdefault(t["workflow"], []).append((t, tier))

    def lane_runner(items: list[tuple[dict, str]]):
        for t, tier in items:
            gpu = t["workflow"] in GPU_CLASS
            GLOBAL_SEM.acquire()
            if gpu:
                GPU_SEM.acquire()
            try:
                recs = run_session(t, tier, budgets)
                for r in recs:
                    append_jsonl(RUNS, r)
                print(f"  done {t['pa_id']} {tier}: {len(recs)} turns", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"  FAILED {t['pa_id']} {tier}: {exc}", flush=True)
            finally:
                if gpu:
                    GPU_SEM.release()
                GLOBAL_SEM.release()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(lane_runner, items) for items in lanes.values()]
        for f in as_completed(futures):
            f.result()


def cmd_adjudate() -> int:
    executor = build_executor()
    scratch = RESULTS_DIR / "scratch"
    tasks = {t["pa_id"]: t for t in load_pa_tasks()}
    from experiments.e21_e22_baseline_harness import platform_reference_quality

    refs = platform_reference_quality()
    rows = load_jsonl(RUNS)
    out_rows: list[dict] = []
    for r in rows:
        task = tasks[r["pa_id"]]
        params = task["turns"][r["turn"] - 1]
        submitted = r.get("submitted") or {}
        checks = check_response(task["workflow"], params, submitted)
        if r.get("submitted_parse_failed") or (r.get("budget_exhausted") and not submitted):
            checks = {
                "delivered": False,
                "envelope_reasons": ["budget exhausted without submit" if r.get("budget_exhausted") else "submit payload unparseable"],
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
                executor, task["workflow"], params, checks, submitted, scratch, ref_turn=ref_turn
            )
        claims = adjudicate_claims(task["workflow"], params, submitted, checks) if submitted else []
        row = dict(r)
        row.pop("tool_log", None)
        row.pop("trace_summary", None)
        row["checks"] = checks
        row["claim_verdicts"] = claims
        out_rows.append(row)

    out = RESULTS_DIR / "adjudicated.jsonl"
    out.write_text(
        "".join(json.dumps(r, ensure_ascii=True, default=str) + "\n" for r in out_rows),
        encoding="utf-8",
    )
    _write_summary(out_rows, RESULTS_DIR / "summary.json")
    print(f"adjudicated -> {out}")
    return 0


def _wilson(k: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return None, None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return round(centre - half, 4), round(centre + half, 4)


def _write_summary(rows: list[dict], path: Path) -> None:
    from collections import defaultdict

    by_wf_tier: dict[tuple[str, str], dict] = defaultdict(lambda: {"turns": 0, "delivered": 0})
    for r in rows:
        key = (r["workflow"], r["tier"])
        by_wf_tier[key]["turns"] += 1
        by_wf_tier[key]["delivered"] += int(bool(r["checks"]["delivered"]))
    claims = [c for r in rows for c in r["claim_verdicts"]]
    denom = [c for c in claims if c["verdict"] in ("TP", "FP")]
    n_fp = sum(1 for c in denom if c["verdict"] == "FP")
    summary = {
        "n_turn_records": len(rows),
        "delivery_by_workflow_tier": {
            f"{wf}|{tier}": v for (wf, tier), v in by_wf_tier.items()
        },
        "budget_exhausted_turns": sum(1 for r in rows if r.get("budget_exhausted")),
        "tool_calls_total": sum(r.get("tool_calls", 0) for r in rows),
        "llm_calls_total": sum(r.get("llm_calls", 0) for r in rows),
        "claims": {
            "n": len(claims),
            "tp": sum(1 for c in claims if c["verdict"] == "TP"),
            "fp": n_fp,
            "unverifiable": sum(1 for c in claims if c["verdict"] == "unverifiable"),
            "fp_rate": round(n_fp / len(denom), 4) if denom else None,
            "fp_rate_ci": _wilson(n_fp, len(denom)),
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
    ap.add_argument("--tier", choices=TIERS, default=None)
    ap.add_argument("--workers", type=int, default=11)
    args = ap.parse_args()

    if args.adjudate:
        return cmd_adjudate()

    budgets = platform_budgets()
    tasks = load_pa_tasks(only=PILOT_TASKS if args.pilot else None)
    tiers = (args.tier,) if args.tier else (("10x",) if args.pilot else TIERS)
    units = [(t, tier) for t in tasks for tier in tiers]
    run_units(units, budgets, args.workers)
    if args.pilot:
        print("pilot complete — adjudate with --adjudate before judging the ≥4/6 gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
