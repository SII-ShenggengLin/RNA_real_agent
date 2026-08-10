#!/usr/bin/env python3
"""Fig 6 panel b/c driver: cross-LLM-backend robustness over the PA suite.

Implements `docs/MANUSCRIPT.md` §8.1 ("Backend plan") / §8.2 item 2:

- for each backend in the §8.1 matrix, builds an ``AgentRunner`` whose LLM
  touchpoints (planner, ``QualityAgent``, ``SynthesisAgent``) all use that
  provider, then runs the PA tasks turn-by-turn via the Python API
  (``AgentRunner.run_form`` — no CLI subprocess);
- cheap backends run every task in ``pa_benchmarks.json``; premium backends
  (GPT-4, Claude-3.5-Sonnet) run the 10-task ``PREMIUM_SUBSET`` only;
- collects per-turn task success, quality-report action distribution, latency,
  and token usage (read from the LangChain client's
  ``response_metadata["token_usage"]`` / ``usage_metadata`` when the provider
  returns them; counters stay at 0 with ``usage_available=false`` otherwise,
  and cost then falls back to the §8.1 table estimates)
  -> ``experiments/results/fig6_backends.jsonl``.

Provider injection is zero-code (INTERFACE_LOCKS §19 keeps provider selection
outside ``AgentRunner``): ``QualityAgent`` / ``SynthesisAgent`` already accept
an ``llm`` constructor argument, so the driver constructs them with a
provider-specific ``ChatOpenAI`` and rebuilds the ``PipelineAgent`` with the
same specialist registry. ``agent_core`` is not modified and its default
behaviour is untouched.

Budget guardrail (§8.1 "fits ¥1 000"): before running, the driver prints the
planned task-runs and an LLM-call estimate; if the matrix exceeds the §8.1
scale (``PLANNED_MAX_TASK_RUNS`` / ``PLANNED_MAX_LLM_CALLS``) it refuses to
continue unless ``--yes-i-know`` is given.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_llm_backend_comparison.py \
        [--backends deepseek-v4-pro,gpt-4] [--tasks 006,009] [--limit N] \
        [--resume] [--dry-run] [--timeout SEC] [--yes-i-know]

Options:
    --backends LIST  comma-separated backend names (default: all 6 in BACKENDS)
    --tasks LIST     comma-separated PA numbers (default: all tasks each backend covers)
    --limit N        run at most N (backend, task) jobs (after filtering)
    --resume         skip (backend, task_id) pairs that already have a successful record
    --dry-run        list the (backend, task) matrix plus the budget estimate, then exit
    --timeout SEC    per-turn wall-clock limit (default: 3600)
    --yes-i-know     override the budget guardrail
    --output PATH    output JSONL path (default: experiments/results/fig6_backends.jsonl)

Notes:
- Records are appended; analysis should take the *latest* record per
  (backend, task_id).
- ``pa_benchmarks.json`` entries carry no ``evaluation_rubric`` (unlike the
  RNA-BioBench-Platform task JSONs), so the §8.2 "evaluation_rubric.round1/2/3"
  scoring is recorded as ``rubric_scores=null``; per-turn success, quality
  actions and retry counts are the auditable signals for PA tasks.
- A backend whose API key is missing is skipped with a warning (the batch
  continues); a failed task is recorded with ``success=false``.
- Importing this module has no side effects: all ``agent_core`` imports are
  deferred to the run path, and nothing executes outside ``main()``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_quality_ablation import (  # noqa: E402
    PROJECT_ROOT,
    build_task_record,
    load_pa_tasks,
    load_successful_keys,
    run_pa_task,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig6_backends.jsonl"

# Backend matrix per docs/MANUSCRIPT.md §8.1 ("Backend plan"). provider/model
# resolution goes through agent_core.llm_config.get_llm_for_provider;
# model=None keeps the provider default (deepseek-v4-pro / qwen2.5-72b-instruct
# / gemma-2-27b-it / claude-3-5-sonnet-20241022). scope="all" runs every PA
# task; scope="subset" runs PREMIUM_SUBSET only (cost cap in §8.1).
#
# NOTE (2026-07-27 incident): before trusting a backend arm's records, verify
# the endpoint actually serves the configured model id. The environment's
# ANTHROPIC_BASE_URL was a Kimi relay (kimi-for-coding/k3 only) that 404s
# claude-3-5-sonnet-20241022 — those 8 failure records are ENDPOINT
# MISCONFIG, not backend data (the two claude "successes", PA_010/011, are
# deterministic tasks needing no LLM call). `--resume` retries them once a
# real Anthropic/OpenRouter key is supplied. Relay models must never be
# relabeled as the arm's nominal backend.
BACKENDS: dict[str, dict[str, Any]] = {
    "deepseek-v4-pro":   {"provider": "deepseek",  "model": None,            "scope": "all"},
    "qwen2.5-72b":       {"provider": "alibaba",   "model": None,            "scope": "all"},
    "gemma-2-27b":       {"provider": "google",    "model": None,            "scope": "all"},
    "gpt-3.5-turbo":     {"provider": "openai",    "model": "gpt-3.5-turbo", "scope": "all"},
    "gpt-4":             {"provider": "openai",    "model": "gpt-4",         "scope": "subset"},
    "claude-3.5-sonnet": {"provider": "anthropic", "model": None,            "scope": "subset"},
}

# 10-task subset for premium backends (§8.1: GPT-4 / Claude on a 10-task
# subset). Rationale: cover 10 of the 11 distinct workflows in
# pa_benchmarks.json — mrna_sequence_scoring (PA_014) is omitted because it is
# a deterministic scorer with no quality review and near-zero diagnostic value
# for backend comparison — while keeping both BMC-coupled workflows
# (rna_aptamer_design PA_009, full_length_mrna_design PA_019), the three
# deterministic tasks (PA_010/011 + one would-be scorer slot) and a mix of
# GPU-backed (PA_009/013/019) and CPU-only tasks. The first (canonical) PA id
# per workflow is used.
PREMIUM_SUBSET = ("006", "007", "009", "010", "011", "012", "013", "015", "018", "019")

# Workflows whose QualityProfile has non-empty evaluation_dimensions (the
# QualityAgent makes real LLM calls); the other three PA workflows
# (aso_target_screening, mrna_sequence_scoring, rna_small_molecule_interaction)
# are deterministic and the review short-circuits without an LLM call.
# Mirrors agent_core.quality_profiles.QUALITY_PROFILES.
QUALITY_REVIEWED_WORKFLOWS = frozenset({
    "full_length_mrna_design", "ires_prediction", "mrna_cds_design",
    "rna_aptamer_design", "rna_secondary_structure_design",
    "rna_tertiary_structure_design", "sgrna_design", "sirna_design",
})

# Budget guardrail constants (§8.1): the planned matrix is 4 cheap backends x
# 26 tasks + 2 premium backends x 10 tasks <= 130 task-runs. LLM calls per
# task-run: turns x 2 QualityAgent reviews (initial + final) for
# quality-reviewed workflows, 0 for deterministic ones; the form-driven path
# never invokes the planner LLM and single-node plans skip SynthesisAgent.
# The hard cap assumes the worst case: (2 + max_retries=2) calls x 4 turns x
# 130 runs.
PLANNED_MAX_TASK_RUNS = 130
PLANNED_MAX_LLM_CALLS = 2080
MAX_RETRIES_PER_TURN = 2  # QualityProfile.max_retries for all reviewed workflows


class UsageTrackingLLM:
    """Proxy around a LangChain chat model accumulating latency and token usage.

    ``ChatOpenAI.invoke`` returns an ``AIMessage`` whose
    ``response_metadata["token_usage"]`` (OpenAI-style
    ``{prompt_tokens, completion_tokens, total_tokens}``) and/or standard
    ``usage_metadata`` (``{input_tokens, output_tokens, total_tokens}``) carry
    the provider's usage report. Providers that omit usage leave the counters
    at 0 with ``usage_available=False``; their cost falls back to the §8.1
    table estimates. Unknown attributes delegate to the wrapped model so the
    proxy is a drop-in for QualityAgent/SynthesisAgent (which only call
    ``.invoke()``).
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.reset()

    def reset(self) -> None:
        self.calls = 0
        self.latency_seconds = 0.0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.usage_available = False

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        started = time.monotonic()
        try:
            raw = self._inner.invoke(*args, **kwargs)
        finally:
            self.latency_seconds += time.monotonic() - started
        self.calls += 1
        meta = getattr(raw, "response_metadata", None) or {}
        tu = meta.get("token_usage") or {}
        um = getattr(raw, "usage_metadata", None) or {}
        prompt = tu.get("prompt_tokens") or um.get("input_tokens")
        completion = tu.get("completion_tokens") or um.get("output_tokens")
        total = tu.get("total_tokens") or um.get("total_tokens")
        if prompt is not None or completion is not None or total is not None:
            self.usage_available = True
            self.prompt_tokens += int(prompt or 0)
            self.completion_tokens += int(completion or 0)
            self.total_tokens += int(total or (prompt or 0) + (completion or 0))
        return raw

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "latency_seconds": self.latency_seconds,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "usage_available": self.usage_available,
        }

    def delta_since(self, mark: dict[str, Any]) -> dict[str, Any]:
        cur = self.snapshot()
        return {
            "calls": cur["calls"] - mark["calls"],
            "latency_seconds": round(cur["latency_seconds"] - mark["latency_seconds"], 4),
            "prompt_tokens": cur["prompt_tokens"] - mark["prompt_tokens"],
            "completion_tokens": cur["completion_tokens"] - mark["completion_tokens"],
            "total_tokens": cur["total_tokens"] - mark["total_tokens"],
            "usage_available": cur["usage_available"],
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _UsageObserver:
    """turn_observer hook attaching per-turn LLM usage deltas to turn records."""

    def __init__(self, trackers: dict[str, UsageTrackingLLM]) -> None:
        self._trackers = trackers
        self._marks: dict[str, dict[str, Any]] = {}

    def before_turn(self, turn_index: int) -> None:
        self._marks = {k: t.snapshot() for k, t in self._trackers.items()}

    def after_turn(self, record: dict[str, Any]) -> None:
        record["llm_usage"] = {
            k: t.delta_since(self._marks[k]) for k, t in self._trackers.items()
        }


def build_backend_runner(backend_name: str, spec: dict[str, Any]) -> tuple[Any, dict[str, UsageTrackingLLM]]:
    """Build an AgentRunner whose LLM touchpoints all use *spec*'s provider.

    Returns ``(runner, trackers)``. Raises ``RuntimeError`` when the provider
    API key is missing (from ``get_llm_for_provider``).
    """
    from agent_core.agents.pipeline_agent import PipelineAgent
    from agent_core.agents.quality_agent import QualityAgent
    from agent_core.agents.synthesis_agent import SynthesisAgent
    from agent_core.llm_config import get_llm_for_provider
    from agent_core.runner import AgentRunner
    from agent_core.session_memory import SessionMemory
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    provider, model = spec["provider"], spec["model"]
    # Temperatures match the agent_core defaults (QualityAgent 0.2,
    # SynthesisAgent 0.3) so backend is the only varied factor.
    quality_tracker = UsageTrackingLLM(get_llm_for_provider(provider, model=model, temperature=0.2))
    synthesis_tracker = UsageTrackingLLM(get_llm_for_provider(provider, model=model, temperature=0.3))
    runner = AgentRunner(
        executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
        session_memory=SessionMemory(),
        quality_review_enabled=True,
        quality_auto_retry=False,  # advisory mode (INTERFACE_LOCKS §19 default)
    )
    runner.quality_agent = QualityAgent(llm=quality_tracker)
    runner.synthesis_agent = SynthesisAgent(llm=synthesis_tracker)
    runner.pipeline_agent = PipelineAgent(
        specialist_registry=runner.specialist_registry,
        quality_agent=runner.quality_agent,
        synthesis_agent=runner.synthesis_agent,
    )
    return runner, {"quality": quality_tracker, "synthesis": synthesis_tracker}


def estimate_llm_calls(jobs: list[tuple[str, dict[str, Any]]]) -> tuple[int, int]:
    """(typical, worst-case) QualityAgent LLM calls for the planned jobs."""
    typical = worst = 0
    for _backend, task in jobs:
        if task["workflow"] not in QUALITY_REVIEWED_WORKFLOWS:
            continue
        n_turns = len(task["params_by_turn"])
        typical += 2 * n_turns  # initial + final review per turn
        worst += (2 + MAX_RETRIES_PER_TURN) * n_turns
    return typical, worst


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--backends", default=None, help="comma-separated backend names (default: all)")
    parser.add_argument("--tasks", default=None, help="comma-separated PA numbers (default: all per backend scope)")
    parser.add_argument("--limit", type=int, default=None, help="max number of (backend, task) jobs")
    parser.add_argument("--resume", action="store_true", help="skip (backend, task_id) already successful")
    parser.add_argument("--dry-run", action="store_true", help="list the backend x task matrix and exit")
    parser.add_argument("--timeout", type=int, default=3600, help="per-turn timeout in seconds")
    parser.add_argument("--yes-i-know", action="store_true", help="override the budget guardrail")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    all_tasks = load_pa_tasks()
    task_filter: set[str] | None = None
    if args.tasks:
        task_filter = {t.strip().upper().replace("PA_", "") for t in args.tasks.split(",")}

    backend_names = list(BACKENDS)
    if args.backends:
        backend_names = [b.strip() for b in args.backends.split(",")]
        unknown = [b for b in backend_names if b not in BACKENDS]
        if unknown:
            print(f"[fig6b] Unknown backends: {', '.join(unknown)}", file=sys.stderr)
            print(f"[fig6b] Available: {', '.join(BACKENDS)}", file=sys.stderr)
            return 2

    jobs: list[tuple[str, dict[str, Any]]] = []
    for backend in backend_names:
        spec = BACKENDS[backend]
        for task in all_tasks:
            if spec["scope"] == "subset" and task["pa"] not in PREMIUM_SUBSET:
                continue
            if task_filter is not None and task["pa"] not in task_filter:
                continue
            jobs.append((backend, task))
    if args.resume:
        done = load_successful_keys(args.output, ("backend", "task_id"))
        jobs = [(b, t) for (b, t) in jobs if (b, t["task_id"]) not in done]
    if args.limit is not None:
        jobs = jobs[: args.limit]

    typical, worst = estimate_llm_calls(jobs)
    budget_lines = [
        f"[budget] task-runs={len(jobs)} (planned <= {PLANNED_MAX_TASK_RUNS})",
        f"[budget] estimated LLM calls: typical={typical}, worst-case={worst} (cap {PLANNED_MAX_LLM_CALLS})",
    ]

    if args.dry_run:
        for backend, task in jobs:
            print(f"{backend}\t{task['task_id']}\t{task['workflow']}\tturns={len(task['params_by_turn'])}")
        per_backend: dict[str, int] = {}
        for backend, _task in jobs:
            per_backend[backend] = per_backend.get(backend, 0) + 1
        for line in budget_lines:
            print(line)
        print(f"# {len(jobs)} runs: " + ", ".join(f"{b}={n}" for b, n in sorted(per_backend.items())))
        return 0

    for line in budget_lines:
        print(line, flush=True)
    if (len(jobs) > PLANNED_MAX_TASK_RUNS or worst > PLANNED_MAX_LLM_CALLS) and not args.yes_i_know:
        print(
            "[budget] Planned matrix exceeds the §8.1 scale; refusing to run. "
            "Re-run with --yes-i-know to override.",
            file=sys.stderr,
        )
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    runners: dict[str, tuple[Any, dict[str, UsageTrackingLLM]]] = {}
    skip_backends: set[str] = set()

    n_ok = n_fail = n_skip = 0
    total = len(jobs)
    batch_start = time.monotonic()
    for i, (backend, task) in enumerate(jobs, start=1):
        if backend in skip_backends:
            n_skip += 1
            continue
        session_id = f"fig6b_{backend.replace('.', '_').replace('-', '_')}_{task['pa']}"
        print(f"[{i}/{total}] {backend} x {task['task_id']} ({task['workflow']}) ...", flush=True)
        if backend not in runners:
            try:
                runners[backend] = build_backend_runner(backend, BACKENDS[backend])
            except RuntimeError as exc:
                # Missing API key (or endpoint misconfiguration): skip every
                # remaining job of this backend, keep the batch going.
                print(f"      -> SKIP backend {backend}: {exc}", flush=True)
                skip_backends.add(backend)
                n_fail += 1
                continue
        runner, trackers = runners[backend]
        for tracker in trackers.values():
            tracker.reset()  # per-task usage totals (turn deltas via observer)
        observer = _UsageObserver(trackers)
        started = time.monotonic()
        turns, errors = run_pa_task(
            runner,
            task,
            session_id=session_id,
            turn_timeout=args.timeout,
            turn_observer=observer,
        )
        record = build_task_record(
            task, "quality_on", turns, errors,
            session_id=session_id, elapsed=time.monotonic() - started,
        )
        # Re-key the shared record for the backend matrix and attach usage.
        record.pop("arm", None)
        record.pop("quality_review_enabled", None)
        quality_snap = trackers["quality"].snapshot()
        synthesis_snap = trackers["synthesis"].snapshot()
        record.update({
            "backend": backend,
            "provider": BACKENDS[backend]["provider"],
            "model": getattr(trackers["quality"]._inner, "model_name", BACKENDS[backend]["model"]),
            "llm_usage_totals": {"quality": quality_snap, "synthesis": synthesis_snap},
            "llm_calls": quality_snap["calls"] + synthesis_snap["calls"],
            "prompt_tokens": quality_snap["prompt_tokens"] + synthesis_snap["prompt_tokens"],
            "completion_tokens": quality_snap["completion_tokens"] + synthesis_snap["completion_tokens"],
            "token_usage_available": quality_snap["usage_available"] or synthesis_snap["usage_available"],
            "llm_latency_seconds": round(
                quality_snap["latency_seconds"] + synthesis_snap["latency_seconds"], 2
            ),
            # See module docstring: pa_benchmarks.json defines no rubrics.
            "rubric_scores": None,
        })
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        if record["success"]:
            n_ok += 1
        else:
            n_fail += 1
        status = "OK" if record["success"] else f"FAIL({'; '.join(errors) or 'turn_failed'})"
        print(
            f"      -> {status} in {record['elapsed_seconds']:.1f}s "
            f"(llm_calls={record['llm_calls']}, actions={record['quality_action_counts']})",
            flush=True,
        )

    wall = time.monotonic() - batch_start
    print(
        f"\nDone: {n_ok} succeeded, {n_fail} failed, {n_skip} skipped "
        f"(missing API key), {total} total, wall {wall / 60:.1f} min"
    )
    print(f"Records -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
