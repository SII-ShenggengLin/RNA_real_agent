#!/usr/bin/env python3
"""Experiment 41 (user-directed revision batch 7, Discussion ¶2 evidence):
per-agent ablation of the Layer-4 multi-agent execution layer — every retained
agent's contribution is measured rather than assumed.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2; zero-intervention rule)
---------------------------------------------------------------------------
* Question (this experiment's own): what is the measured marginal contribution
  of each Layer-4 agent — QualityAgent (advisory review), SpecialistAgent
  (per-workflow strategy wrapper + hard-failure retry), PipelineAgent
  (deterministic multi-node scheduling) and SynthesisAgent (multi-node report
  synthesis + ClaimGate) — on (i) task outcomes of the full process-aware
  regression suite and (ii) two pre-registered multi-node pipelines? The
  paper's Discussion states that each agent's contribution is quantified and
  mechanisms whose measured gain does not survive are demoted (the removed
  coordination loop, Exp 16 / Fig. 3f); this experiment supplies the per-agent
  numbers for the four retained agents.
* BLOCK A (form suite): the full current PA suite — PA_006–PA_036, 31 form
  sessions / 96 user turns, 72 turns on the 8 QualityAgent-reviewed workflows
  and 24 on the 3 deterministic-exempt ones (the Exp-25 registration; PA_028
  GenNav and PA_036 included; PA_023 runs on the restored canonical fixture,
  the Exp-25b state). Arms, each (arm, session) a fresh CLI subprocess per
  turn through the user form entry (``cli/form_chat.py --workflow
  --params-file --session-id``), inputs verbatim from ``pa_benchmarks.json``,
  CapGate advisory (the PA regression convention):
  - ``full``:     production default (all four agents; review on).
  - ``noquality``:``RNADA_QUALITY_REVIEW=off`` — QualityAgent ablated (no LLM
    review call; the in-loop review path is unreachable so no retry can be
    triggered by review either).
  - ``noretry``:  ``RNADA_SPECIALIST_MAX_RETRIES=0`` — SpecialistAgent's retry
    loop ablated; the advisory review still runs (exactly the final review per
    reviewed turn).
  DISCLOSED platform wiring (the RNADA_QUALITY_REVIEW precedent): the two new
  env knobs follow the RNADA_CAPGATE env-knob convention and are added for
  this experiment's registered arms — ``RNADA_SPECIALIST_MAX_RETRIES``
  (SpecialistAgent.run) and ``RNADA_SYNTHESIS_LLM`` (AgentRunner, Block B);
  interactive defaults unchanged. Unit tests added alongside.
  PipelineAgent and SynthesisAgent are exercised structurally on every
  single-node form turn (scheduling one node; deterministic pass-through
  report — zero LLM); their multi-node roles are measured in Block B.
* BLOCK B (multi-node probes): two pre-registered two-node pipelines built
  from PA benchmark inputs VERBATIM (registered inputs, no new task content;
  the ligand pairing is mechanism-motivated, not biologically motivated —
  disclosed):
  - ``pb1_secstruct_smol``: node ``design`` = rna_secondary_structure_design
    (PA_018 turn-1 params) → node ``smol`` = rna_small_molecule_interaction
    (smiles + scoring_tools from PA_010 turn-1 verbatim;
    ``rna_sequence ← $design.best_candidate.sequence``).
  - ``pb2_aptamer_smol``: node ``design`` = rna_aptamer_design (PA_020 turn-1
    params; GPU class) → node ``smol`` = same second node as pb1.
  Arms:
  - ``full``: production CLI subprocess ``cli/form_chat.py --pipeline-file``
    (PipelineAgent scheduling + SpecialistAgent + QualityAgent + SynthesisAgent
    LLM synthesis + ClaimGate verdicts; DECISIONS (s): ClaimGate mounts only on
    the multi-node synthesis).
  - ``nosynth``: same subprocess + ``RNADA_SYNTHESIS_LLM=off`` — SynthesisAgent
    ablated to its deterministic report (no synthesis LLM call, no claim
    extraction, no ClaimGate block).
  - ``sequential``: driver-level in-process execution with NO Layer-4 agents —
    node workflows run directly from the production AgentRunner workflow
    registry (auto-start services, ToolExecutor path, audit on) with the
    binding applied by the driver; PipelineAgent ablated (disclosed as the
    Exp-16/23 in-process instrument convention).
* Metrics (Block A, per turn — the Exp-25 convention): subprocess exit code;
  workflow ``success``; ``retry_count``; successful review calls =
  ``len(_diagnosis_history)``; failed review calls = occurrences of the
  QualityAgent ERROR log line. Turn success = exit 0 AND saved JSON
  ``success`` true. (Block B): exit code; plan success; per-node success;
  within-run binding correctness (node-2 ``rna_sequence`` equals node-1
  best-candidate sequence); presence of the ``Gated claims (ClaimGate):``
  block in the saved final report and its verdict-line classes.
* Expected outcomes (structural, pre-registered):
  (1) Block A primary endpoint: every session's per-turn outcome tuple is
      IDENTICAL across the three arms (the deterministic spine); deviations
      can only arise from stochastic hard failures that ``full`` retries and
      an ablated arm cannot — expected ≤ 2 turns on the frozen-corpora
      precedent (Exp 25: 1 retry in 93 sessions; Exp 24 PA corpus), each
      disclosed as measured;
  (2) ``noquality``: zero review calls and zero retries on every turn;
  (3) ``noretry``: zero retries; exactly ONE review call per reviewed-workflow
      turn (the final review), i.e. 72 across the suite;
  (4) ``full``: ≥ 1 review call on every reviewed-workflow turn (structurally
      2 per passing turn — in-loop + final — plus one per retry round), zero
      on the 24 exempt turns;
  (5) Block B: all six (probe × arm) runs complete; both nodes succeed in
      every arm; within-run binding correct; per-node outcomes equal across
      arms (pb2's diffusion node makes cross-arm SEQUENCES incomparable —
      outcome equality only, disclosed);
  (6) Block B ``full``: the saved report carries the ClaimGate block (≥ 0
      gated claims, verdict classes counted); ``nosynth``: deterministic
      report, no ClaimGate block; ``sequential``: no report synthesis (node
      outcomes recorded by the driver only).
* Scheduling (disclosed; wall-time convention only — timing is NOT a metric):
  Block A global pool ≤ 6 concurrent sessions, GPU-class workflows
  (rna_aptamer_design, rna_tertiary_structure_design) capped at 3 (the
  Exp-25 convention); Block B runs serially (GPU contention). Machine state
  2026-09-13: GPU 0 free / GPU 1 occupied by another user — services take
  their default device placement (cuda:0 first).
* Timeout: 7200 s per Block-A turn subprocess; 10,800 s per Block-B run;
  whole-process-group kill on expiry (the exp8 PA_028 orphan lesson).
* Re-run convention (exp24 amendment convention): a run demonstrably killed
  by infrastructure (timeout/OOM) may be re-run ONCE under a fresh session
  id, the censored record retained and disclosed; workflow-logic failures
  are reported as measured, never re-run.
* Pilot (Block A): 3 arms × {PA_014 (deterministic-exempt, fastest) +
  PA_012 (reviewed, fast)} = 6 sessions under ``exp41_pilot_`` ids — excluded
  from the full corpus by construction. Pilot (Block B): pb1 × ``full`` arm.
  Pilot gate: 6/6 + pb1-full complete AND expectations (2)–(4) on the pilot
  subset + the pb1 ClaimGate block present.
* Contamination control: fresh session ids per run; every tool call lands in
  the shared platform audit trail under its session stamp; the driver never
  mutates benchmark inputs.
* Determinism: ``--analyze``/``--verify`` recompute every headline number
  from the frozen ``blockA/records.jsonl`` + ``blockB/records.jsonl``
  byte-identically.

Usage:
    PYTHONPATH=. python experiments/exp41_agent_ablation.py --pilot-a
    PYTHONPATH=. python experiments/exp41_agent_ablation.py --pilot-b
    PYTHONPATH=. python experiments/exp41_agent_ablation.py --full-a [--resume]
    PYTHONPATH=. python experiments/exp41_agent_ablation.py --full-b
    PYTHONPATH=. python experiments/exp41_agent_ablation.py --analyze
    PYTHONPATH=. python experiments/exp41_agent_ablation.py --verify
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp41_agent_ablation"
BLOCKA_DIR = RESULTS_DIR / "blockA"
BLOCKB_DIR = RESULTS_DIR / "blockB"
LOGS_DIR = BLOCKA_DIR / "logs"
PIPELINE_DIR = BLOCKB_DIR / "pipelines"
BLOCKA_RECORDS = BLOCKA_DIR / "records.jsonl"
BLOCKA_PILOT = BLOCKA_DIR / "pilot.jsonl"
BLOCKB_RECORDS = BLOCKB_DIR / "records.jsonl"

PA_BENCHMARKS = PROJECT_ROOT / "pa_benchmarks.json"

EXEMPT_WORKFLOWS = {
    "mrna_sequence_scoring",
    "aso_target_screening",
    "rna_small_molecule_interaction",
}
GPU_CLASS_WORKFLOWS = {
    "rna_aptamer_design",
    "rna_tertiary_structure_design",
}

BLOCKA_ARMS: dict[str, dict[str, str]] = {
    "full": {},
    "noquality": {"RNADA_QUALITY_REVIEW": "off"},
    "noretry": {"RNADA_SPECIALIST_MAX_RETRIES": "0"},
}

TURN_TIMEOUT_S = 7200
BLOCKB_TIMEOUT_S = 10800
MAX_CONCURRENT_SESSIONS = 6
MAX_CONCURRENT_GPU_CLASS = 3

SAVED_RESULTS_RE = re.compile(r"^\[Saved\] 完整结果已保存: (\S+)$", re.M)
SAVED_PIPELINE_RE = re.compile(r"^\[Saved\] Pipeline 完整结果已保存: (\S+)$", re.M)
REVIEW_FAIL_LOG_LINE = "QualityAgent LLM diagnosis failed"
CLAIM_BLOCK_MARKER = "Gated claims (ClaimGate):"
# Verdict lines the SynthesisAgent appends: "- PASS: ..." and "- [REJECTED: ...]";
# a downgrade is emitted as its rewritten text (no marker) — not countable.
CLAIM_PASS_RE = re.compile(r"^- PASS: ", re.M)
CLAIM_REJECTED_RE = re.compile(r"^- \[REJECTED: ", re.M)

_print_lock = threading.Lock()
_gpu_class_semaphore = threading.Semaphore(MAX_CONCURRENT_GPU_CLASS)


def _log(msg: str) -> None:
    with _print_lock:
        print(f"[exp41 {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_pa_benchmarks() -> dict[str, dict[str, Any]]:
    return json.loads(PA_BENCHMARKS.read_text(encoding="utf-8"))


def _base_env(extra: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    env.setdefault("RNADA_CAPGATE", "advisory")
    env.update(extra)
    return env


# ---------------------------------------------------------------------------
# Block A — form-suite arms (the Exp-25 instrument, per-agent arm set)
# ---------------------------------------------------------------------------

def _run_turn_subprocess(
    arm: str,
    pa_id: str,
    workflow: str,
    params: dict[str, Any],
    turn: int,
    session_id: str,
    turn_log_path: Path,
) -> dict[str, Any]:
    """Run one form turn as a production CLI subprocess; return the turn record."""
    params_file = turn_log_path.parent / f"params_turn{turn}.json"
    params_file.parent.mkdir(parents=True, exist_ok=True)
    params_file.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "cli" / "form_chat.py"),
        "--workflow", workflow,
        "--params-file", str(params_file),
        "--session-id", session_id,
    ]

    started = time.monotonic()
    timed_out = False
    with turn_log_path.open("w", encoding="utf-8", errors="replace") as log_fp:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=_base_env(BLOCKA_ARMS[arm]),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,
        )
        try:
            stdout, _ = proc.communicate(timeout=TURN_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(os.getpgid(proc.pid), 15)
            except ProcessLookupError:
                pass
            try:
                stdout, _ = proc.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), 9)
                stdout, _ = proc.communicate()
            stdout = stdout or ""
            stdout += f"\n[exp41] TURN TIMED OUT after {TURN_TIMEOUT_S}s (process group killed)"
        log_fp.write(stdout)
    elapsed = time.monotonic() - started

    record: dict[str, Any] = {
        "turn": turn,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 1),
        "workflow_success": None,
        "retry_count": None,
        "successful_review_calls": 0,
        "failed_review_calls": stdout.count(REVIEW_FAIL_LOG_LINE),
        "review_error": None,
        "results_json": None,
    }

    m = SAVED_RESULTS_RE.search(stdout)
    if m:
        results_path = Path(m.group(1))
        record["results_json"] = str(results_path)
        try:
            data = json.loads(results_path.read_text(encoding="utf-8"))
            record["workflow_success"] = bool(data.get("success"))
            record["retry_count"] = int(data.get("retry_count", 0) or 0)
            record["successful_review_calls"] = len(data.get("_diagnosis_history") or [])
            err = data.get("_quality_review_error")
            if isinstance(err, dict):
                record["review_error"] = {"type": err.get("type"), "message": str(err.get("message"))[:300]}
        except Exception as exc:  # unreadable/corrupt results file — record as measured
            record["results_json_error"] = f"{type(exc).__name__}: {exc}"

    record["turn_success"] = (
        record["exit_code"] == 0
        and not timed_out
        and record["workflow_success"] is True
    )
    return record


def run_session(arm: str, pa_id: str, entry: dict[str, Any], *, pilot: bool) -> dict[str, Any]:
    workflow = entry["workflow"]
    params_by_turn = entry["params_by_turn"]
    prefix = "exp41_pilot" if pilot else "exp41"
    session_id = f"{prefix}_{arm}_pa{pa_id}_{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"

    record: dict[str, Any] = {
        "arm": arm,
        "pa_id": pa_id,
        "workflow": workflow,
        "reviewed_workflow": workflow not in EXEMPT_WORKFLOWS,
        "session_id": session_id,
        "pilot": pilot,
        "n_turns": len(params_by_turn),
        "turns": [],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    log_dir = LOGS_DIR / ("pilot" if pilot else "full") / arm / f"pa{pa_id}"
    log_dir.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    gpu_class = workflow in GPU_CLASS_WORKFLOWS
    if gpu_class:
        _gpu_class_semaphore.acquire()
    try:
        for turn, params in enumerate(params_by_turn, start=1):
            turn_log = log_dir / f"turn{turn}_{time.strftime('%Y%m%d_%H%M%S')}.log"
            rec = _run_turn_subprocess(arm, pa_id, workflow, params, turn, session_id, turn_log)
            record["turns"].append(rec)
            _log(
                f"A/{arm}/PA_{pa_id} turn {turn}/{len(params_by_turn)} "
                f"ok={rec['turn_success']} exit={rec['exit_code']} "
                f"reviews(ok/fail)={rec['successful_review_calls']}/{rec['failed_review_calls']} "
                f"retries={rec['retry_count']} {rec['elapsed_seconds']:.0f}s"
            )
    finally:
        if gpu_class:
            _gpu_class_semaphore.release()
    record["wall_seconds"] = round(time.monotonic() - started, 1)
    record["failed_turns"] = sum(1 for t in record["turns"] if not t["turn_success"])
    record["total_retry_count"] = sum(t["retry_count"] or 0 for t in record["turns"])
    record["total_successful_review_calls"] = sum(t["successful_review_calls"] for t in record["turns"])
    record["total_failed_review_calls"] = sum(t["failed_review_calls"] for t in record["turns"])
    record["session_success"] = record["failed_turns"] == 0
    return record


PILOT_PAS = ["014", "012"]  # PA_014 deterministic-exempt (fastest) + PA_012 reviewed (fast)


def run_batch_a(pa_ids: list[str], *, pilot: bool, resume: bool) -> None:
    benchmarks = load_pa_benchmarks()
    out_path = BLOCKA_PILOT if pilot else BLOCKA_RECORDS
    done: set[tuple[str, str]] = set()
    if resume and not pilot:
        done = {
            (r["arm"], r["pa_id"])
            for r in _load_records(BLOCKA_RECORDS)
            if r.get("session_success")
        }
        _log(f"A resume: {len(done)} (arm, pa) already successful — skipped")

    jobs = [(arm, pa) for arm in BLOCKA_ARMS for pa in pa_ids if (arm, pa) not in done]
    _log(f"A: launching {len(jobs)} sessions (3 arms, {len(pa_ids)} PA ids, pilot={pilot})")

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SESSIONS) as pool:
        futures = {
            pool.submit(run_session, arm, pa, benchmarks[pa], pilot=pilot): (arm, pa)
            for arm, pa in jobs
        }
        for fut in as_completed(futures):
            arm, pa = futures[fut]
            try:
                record = fut.result()
            except Exception as exc:
                record = {
                    "arm": arm, "pa_id": pa, "pilot": pilot,
                    "session_success": False,
                    "driver_exception": f"{type(exc).__name__}: {exc}",
                }
            _append_record(out_path, record)
            _log(f"A DONE {arm}/PA_{pa} success={record.get('session_success')} → {out_path.name}")


# ---------------------------------------------------------------------------
# Block B — multi-node probes (PipelineAgent / SynthesisAgent roles)
# ---------------------------------------------------------------------------

def _build_pipeline_files() -> dict[str, Path]:
    """Write the two pre-registered two-node pipeline JSONs from PA inputs verbatim."""
    benchmarks = load_pa_benchmarks()
    smol_params = benchmarks["010"]["params_by_turn"][0]
    smol_static = {"smiles": smol_params["smiles"], "scoring_tools": smol_params["scoring_tools"]}

    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    probes: dict[str, Path] = {}

    pb1 = {
        "plan_id": "pb1_secstruct_smol",
        "nodes": [
            {
                "node_id": "design",
                "workflow": "rna_secondary_structure_design",
                "static_params": benchmarks["018"]["params_by_turn"][0],
                "output_alias": "design",
            },
            {
                "node_id": "smol",
                "workflow": "rna_small_molecule_interaction",
                "static_params": smol_static,
                "input_bindings": {"rna_sequence": "$design.best_candidate.sequence"},
                "output_alias": "smol",
            },
        ],
        "edges": [{"source": "design", "target": "smol"}],
    }
    probes["pb1_secstruct_smol"] = PIPELINE_DIR / "pb1_secstruct_smol.json"
    probes["pb1_secstruct_smol"].write_text(json.dumps(pb1, ensure_ascii=False, indent=2), encoding="utf-8")

    pb2 = {
        "plan_id": "pb2_aptamer_smol",
        "nodes": [
            {
                "node_id": "design",
                "workflow": "rna_aptamer_design",
                "static_params": benchmarks["020"]["params_by_turn"][0],
                "output_alias": "design",
            },
            {
                "node_id": "smol",
                "workflow": "rna_small_molecule_interaction",
                "static_params": smol_static,
                "input_bindings": {"rna_sequence": "$design.best_candidate.sequence"},
                "output_alias": "smol",
            },
        ],
        "edges": [{"source": "design", "target": "smol"}],
    }
    probes["pb2_aptamer_smol"] = PIPELINE_DIR / "pb2_aptamer_smol.json"
    probes["pb2_aptamer_smol"].write_text(json.dumps(pb2, ensure_ascii=False, indent=2), encoding="utf-8")
    return probes


BLOCKB_ARMS: dict[str, dict[str, str]] = {
    "full": {},
    "nosynth": {"RNADA_SYNTHESIS_LLM": "off"},
    # "sequential" is driver-level in-process (no env arm)
}


def _run_blockb_subprocess(arm: str, probe: str, plan_path: Path, session_id: str, *, pilot: bool) -> dict[str, Any]:
    log_path = BLOCKB_DIR / "logs" / f"{arm}_{probe}_{session_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "cli" / "form_chat.py"),
        "--pipeline-file", str(plan_path),
        "--session-id", session_id,
    ]
    started = time.monotonic()
    timed_out = False
    with log_path.open("w", encoding="utf-8", errors="replace") as log_fp:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=_base_env(BLOCKB_ARMS[arm]),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,
        )
        try:
            stdout, _ = proc.communicate(timeout=BLOCKB_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(os.getpgid(proc.pid), 15)
            except ProcessLookupError:
                pass
            stdout = ""
        log_fp.write(stdout or "")
    elapsed = time.monotonic() - started

    record: dict[str, Any] = {
        "arm": arm,
        "probe": probe,
        "session_id": session_id,
        "pilot": pilot,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 1),
        "plan_success": None,
        "nodes": {},
        "claim_block_present": False,
        "claim_pass_lines": 0,
        "claim_rejected_lines": 0,
        "results_json": None,
    }
    m = SAVED_PIPELINE_RE.search(stdout or "")
    if m:
        results_path = Path(m.group(1))
        record["results_json"] = str(results_path)
        try:
            data = json.loads(results_path.read_text(encoding="utf-8"))
            record["plan_success"] = bool(data.get("success"))
            report = str(data.get("final_report") or "")
            record["claim_block_present"] = CLAIM_BLOCK_MARKER in report
            record["claim_pass_lines"] = len(CLAIM_PASS_RE.findall(report))
            record["claim_rejected_lines"] = len(CLAIM_REJECTED_RE.findall(report))
            pr = data.get("pipeline_result") or {}
            for node_id, node_dump in (pr.get("node_results") or {}).items():
                wf_result = node_dump.get("workflow_result") or {}
                best = wf_result.get("best_candidate") or {}
                record["nodes"][node_id] = {
                    "workflow": node_dump.get("workflow"),
                    "success": node_dump.get("success"),
                    "best_sequence": best.get("sequence"),
                }
        except Exception as exc:
            record["results_json_error"] = f"{type(exc).__name__}: {exc}"
    record["run_success"] = (
        record["exit_code"] == 0 and not timed_out and record["plan_success"] is True
    )
    return record


def _run_blockb_sequential(probe: str, plan_path: Path, session_id: str, *, pilot: bool) -> dict[str, Any]:
    """Driver-level sequential execution with NO Layer-4 agents (disclosed arm).

    The node workflows are the production AgentRunner registry objects (auto
    service start, ToolExecutor path, audit on); the binding is applied by the
    driver instead of PipelineAgent's BindingResolver.
    """
    from agent_core.file_manager import _SESSION_ID_CTX
    from agent_core.runner import AgentRunner
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    started = time.monotonic()

    record: dict[str, Any] = {
        "arm": "sequential",
        "probe": probe,
        "session_id": session_id,
        "pilot": pilot,
        "exit_code": None,
        "timed_out": False,
        "elapsed_seconds": None,
        "plan_success": None,
        "nodes": {},
        "claim_block_present": False,
        "claim_pass_lines": 0,
        "claim_rejected_lines": 0,
        "results_json": None,
        "driver_exception": None,
    }
    try:
        runner = AgentRunner(executor=ToolExecutor(build_default_tool_registry()))
        token = _SESSION_ID_CTX.set(session_id)
        try:
            resolved: dict[str, Any] = {}
            for node in plan["nodes"]:
                params = dict(node.get("static_params") or {})
                for name, binding in (node.get("input_bindings") or {}).items():
                    assert binding.startswith("$")
                    body = binding[1:]
                    ref, path = body.split(".", 1)
                    value = resolved[ref]
                    for part in path.split("."):
                        value = value[part]
                    params[name] = value
                workflow = runner.workflow_registry[node["workflow"]]
                inp = workflow.input_model(**params) if workflow.input_model else params
                wf_result = workflow.run(inp)
                best = wf_result.best_candidate
                resolved[node.get("output_alias") or node["node_id"]] = {
                    "best_candidate": {
                        "sequence": best.sequence if best is not None else None,
                    }
                }
                record["nodes"][node["node_id"]] = {
                    "workflow": node["workflow"],
                    "success": bool(wf_result.success),
                    "best_sequence": best.sequence if best is not None else None,
                }
        finally:
            _SESSION_ID_CTX.reset(token)
        record["plan_success"] = all(n["success"] for n in record["nodes"].values()) and len(record["nodes"]) == len(plan["nodes"])
    except Exception as exc:
        record["driver_exception"] = f"{type(exc).__name__}: {exc}"
        record["plan_success"] = False
    record["elapsed_seconds"] = round(time.monotonic() - started, 1)
    record["run_success"] = record["plan_success"] is True
    return record


def run_block_b(probes: list[str], arms: list[str], *, pilot: bool, rerun: bool = False) -> None:
    plan_paths = _build_pipeline_files()
    BLOCKB_DIR.mkdir(parents=True, exist_ok=True)
    for probe in probes:
        for arm in arms:
            session_id = f"exp41_{arm}_{probe}_{time.strftime('%Y%m%d_%H%M%S')}"
            _log(f"B: running {arm}/{probe} ({session_id}{', rerun' if rerun else ''})")
            if arm == "sequential":
                record = _run_blockb_sequential(probe, plan_paths[probe], session_id, pilot=pilot)
            else:
                record = _run_blockb_subprocess(arm, probe, plan_paths[probe], session_id, pilot=pilot)
            if rerun:
                record["rerun_of_censored"] = True
            _append_record(BLOCKB_RECORDS, record)
            _log(
                f"B DONE {arm}/{probe} success={record.get('run_success')} "
                f"nodes={ {k: v['success'] for k, v in record.get('nodes', {}).items()} } "
                f"claims_block={record.get('claim_block_present')} "
                f"{record.get('elapsed_seconds', 0):.0f}s"
            )


# ---------------------------------------------------------------------------
# Records + analysis — every headline number recomputed from the frozen records.
# ---------------------------------------------------------------------------

def _append_record(path: Path, record: dict[str, Any]) -> None:
    with _print_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def analyze_block_a(records: list[dict[str, Any]], *, pilot: bool) -> dict[str, Any]:
    # AMENDMENT (registered 2026-09-13, before any Block-A analysis): dedupe
    # per (arm, pa_id) with latest-record-wins — a pair re-run under the
    # registered infrastructure-re-run convention (e.g. a service-swap
    # casualty) appends a second record; the censored one stays in
    # records.jsonl and is disclosed, but must not inflate the counts.
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for r in records:
        if r.get("pilot") != pilot or "arm" not in r or "pa_id" not in r:
            continue
        deduped[(r["arm"], r["pa_id"])] = r
    records = list(deduped.values())
    by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in BLOCKA_ARMS}
    for r in records:
        if r["arm"] in by_arm:
            by_arm[r["arm"]].append(r)

    summary: dict[str, Any] = {
        "pilot": pilot,
        "n_sessions_expected": len(PILOT_PAS) if pilot else 31,
        "arms": {},
    }
    for arm, recs in by_arm.items():
        turns = [t for r in recs for t in r.get("turns", [])]
        reviewed_turns = [t for r in recs if r.get("reviewed_workflow") for t in r.get("turns", [])]
        exempt_turns = [t for r in recs if not r.get("reviewed_workflow") for t in r.get("turns", [])]

        def _workflow(r: dict[str, Any]) -> bool:
            ts = r.get("turns", [])
            return bool(ts) and all(
                t.get("exit_code") == 0 and not t.get("timed_out") and t.get("workflow_success") is True
                for t in ts
            )

        def _outcome_tuple(r: dict[str, Any]) -> tuple:
            return tuple(bool(t.get("workflow_success")) for t in r.get("turns", []))

        arm_summary = {
            "n_sessions": len(recs),
            "n_session_workflow_success": sum(1 for r in recs if _workflow(r)),
            "n_turns": len(turns),
            "n_turn_workflow_success": sum(1 for t in turns if t.get("workflow_success") is True),
            "total_retry_count": sum(r.get("total_retry_count", 0) for r in recs),
            "sessions_with_retries": sorted(
                r["pa_id"] for r in recs if r.get("total_retry_count", 0) > 0
            ),
            "total_successful_review_calls": sum(r.get("total_successful_review_calls", 0) for r in recs),
            "total_failed_review_calls": sum(r.get("total_failed_review_calls", 0) for r in recs),
            "workflow_failed_sessions": sorted(r["pa_id"] for r in recs if not _workflow(r)),
            "outcome_tuples": {r["pa_id"]: _outcome_tuple(r) for r in recs},
            "checks": {},
        }
        if arm == "noquality":
            arm_summary["checks"]["zero_review_calls"] = all(
                t.get("successful_review_calls", 0) == 0 for t in turns
            )
            arm_summary["checks"]["zero_retries"] = arm_summary["total_retry_count"] == 0
        if arm == "noretry":
            arm_summary["checks"]["zero_retries"] = arm_summary["total_retry_count"] == 0
            arm_summary["checks"]["exactly_one_review_per_reviewed_turn"] = bool(reviewed_turns) and all(
                t.get("successful_review_calls", 0) == 1 for t in reviewed_turns
            )
            arm_summary["checks"]["exempt_turns_zero_reviews"] = all(
                t.get("successful_review_calls", 0) == 0 for t in exempt_turns
            )
        if arm == "full":
            arm_summary["checks"]["reviewed_turns_have_review"] = bool(reviewed_turns) and all(
                t.get("successful_review_calls", 0) >= 1 for t in reviewed_turns
            )
            arm_summary["checks"]["exempt_turns_zero_reviews"] = all(
                t.get("successful_review_calls", 0) == 0 for t in exempt_turns
            )
        summary["arms"][arm] = arm_summary

    # Primary endpoint: paired per-turn outcome identity across the three arms.
    common_pas = set.intersection(
        *(set(summary["arms"][a]["outcome_tuples"]) for a in BLOCKA_ARMS if summary["arms"][a]["outcome_tuples"])
    ) if all(summary["arms"][a]["outcome_tuples"] for a in BLOCKA_ARMS) else set()
    mismatched = sorted(
        pa for pa in common_pas
        if len({summary["arms"][a]["outcome_tuples"][pa] for a in BLOCKA_ARMS}) > 1
    )
    summary["headline"] = {
        "n_sessions_per_arm": len(common_pas),
        "workflow_success_counts": {
            arm: summary["arms"][arm]["n_session_workflow_success"] for arm in BLOCKA_ARMS
        },
        "paired_outcome_identity": not mismatched,
        "paired_outcome_mismatches": mismatched,
        "retry_counts": {arm: summary["arms"][arm]["total_retry_count"] for arm in BLOCKA_ARMS},
        "review_call_counts": {
            arm: summary["arms"][arm]["total_successful_review_calls"] for arm in BLOCKA_ARMS
        },
    }
    return summary


def analyze_block_b(records: list[dict[str, Any]], *, pilot: bool) -> dict[str, Any]:
    recs = [r for r in records if r.get("pilot") == pilot]
    # Latest-record-wins per (arm, probe); superseded (censored) records are
    # disclosed in the summary — the registered re-run convention.
    latest: dict[str, dict[str, Any]] = {}
    superseded: list[dict[str, Any]] = []
    for r in recs:
        key = f"{r['arm']}/{r['probe']}"
        if key in latest:
            superseded.append(
                {
                    "key": key,
                    "superseded_session_id": latest[key].get("session_id"),
                    "superseded_run_success": latest[key].get("run_success"),
                    "kept_session_id": r.get("session_id"),
                }
            )
        latest[key] = r
    summary: dict[str, Any] = {"pilot": pilot, "runs": {}, "superseded_runs": superseded, "headline": {}}
    for key, r in latest.items():
        nodes = r.get("nodes", {})
        binding_ok = None
        if "design" in nodes and "smol" in nodes:
            seqs = [nodes["design"].get("best_sequence"), nodes["smol"].get("best_sequence")]
            binding_ok = bool(seqs[0]) and seqs[0] == seqs[1]
        summary["runs"][key] = {
            "run_success": r.get("run_success"),
            "plan_success": r.get("plan_success"),
            "node_success": {k: v.get("success") for k, v in nodes.items()},
            "binding_correct": binding_ok,
            "claim_block_present": r.get("claim_block_present"),
            "claim_pass_lines": r.get("claim_pass_lines"),
            "claim_rejected_lines": r.get("claim_rejected_lines"),
            "elapsed_seconds": r.get("elapsed_seconds"),
        }
    runs = summary["runs"]
    summary["headline"] = {
        "n_runs": len(runs),
        "all_runs_success": bool(runs) and all(v["run_success"] for v in runs.values()),
        "full_arm_claim_blocks": sorted(
            k for k, v in runs.items() if k.startswith("full/") and v["claim_block_present"]
        ),
        "nosynth_claim_blocks": sorted(
            k for k, v in runs.items() if k.startswith("nosynth/") and v["claim_block_present"]
        ),
    }
    return summary


def cmd_analyze(pilot: bool) -> int:
    block_a = analyze_block_a(_load_records(BLOCKA_PILOT if pilot else BLOCKA_RECORDS), pilot=pilot)
    block_b = analyze_block_b(_load_records(BLOCKB_RECORDS), pilot=pilot)
    summary = {"blockA": block_a, "blockB": block_b}
    out = RESULTS_DIR / ("pilot_summary.json" if pilot else "summary.json")
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    gate_a = block_a["headline"]["paired_outcome_identity"] and all(
        all(v for k, v in arm.get("checks", {}).items()) for arm in block_a["arms"].values()
    )
    gate_b = block_b["headline"]["all_runs_success"]
    print(f"\n[exp41] gate A={'PASS' if gate_a else 'FAIL'} B={'PASS' if gate_b else 'FAIL'} → {out}")
    return 0 if (gate_a and gate_b) else 1


def cmd_verify() -> int:
    """Recompute the frozen summary from the records; byte-identical check."""
    summary = {
        "blockA": analyze_block_a(_load_records(BLOCKA_RECORDS), pilot=False),
        "blockB": analyze_block_b(_load_records(BLOCKB_RECORDS), pilot=False),
    }
    frozen = json.loads((RESULTS_DIR / "summary.json").read_text(encoding="utf-8"))
    ok = json.dumps(summary, sort_keys=True) == json.dumps(frozen, sort_keys=True)
    print(f"[exp41] --verify recomputation byte-identical: {ok}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--pilot-a", action="store_true", help="Block A pilot: 3 arms × PA_014+PA_012")
    parser.add_argument("--pilot-b", action="store_true", help="Block B pilot: pb1 × full arm")
    parser.add_argument("--full-a", action="store_true", help="Block A full: 31 PA sessions × 3 arms")
    parser.add_argument("--full-b", action="store_true", help="Block B full: 2 probes × 3 arms")
    parser.add_argument(
        "--rerun-b-sequential",
        action="store_true",
        help="Block B sequential-arm re-run (registered re-run convention)",
    )
    parser.add_argument("--resume", action="store_true", help="skip (arm, pa) already successful (Block A full only)")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--analyze-pilot", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # AMENDMENT (registered 2026-09-13, from the first production Block-B run,
    # BEFORE any cross-arm analysis): the driver process itself must carry the
    # same RNADA_CAPGATE=advisory convention as the subprocess arms — the
    # in-process sequential arm otherwise constructs its AgentRunner under the
    # platform's default enforce policy, and its small-molecule scoring calls
    # are rejected by the DecisionGate (the registered short-aptamer OOD
    # boundary, Exp 7) — an arm asymmetry, not a measurement. The censored
    # sequential records are retained in records.jsonl and the arms re-run
    # once under this fix (--rerun-b-sequential).
    os.environ.setdefault("RNADA_CAPGATE", "advisory")

    if args.pilot_a:
        run_batch_a(PILOT_PAS, pilot=True, resume=False)
        return 0
    if args.pilot_b:
        run_block_b(["pb1_secstruct_smol"], ["full"], pilot=True)
        return 0
    if args.full_a:
        pa_ids = sorted(load_pa_benchmarks().keys())
        run_batch_a(pa_ids, pilot=False, resume=args.resume)
        return 0
    if args.full_b:
        run_block_b(
            ["pb1_secstruct_smol", "pb2_aptamer_smol"],
            ["full", "nosynth", "sequential"],
            pilot=False,
        )
        return 0
    if args.rerun_b_sequential:
        run_block_b(
            ["pb1_secstruct_smol", "pb2_aptamer_smol"],
            ["sequential"],
            pilot=False,
            rerun=True,
        )
        return 0
    if args.analyze_pilot:
        return cmd_analyze(pilot=True)
    if args.analyze:
        return cmd_analyze(pilot=False)
    if args.verify:
        return cmd_verify()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
