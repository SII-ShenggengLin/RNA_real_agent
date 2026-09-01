"""Exp 23 — selective gating decision matrix (paper §2.4 实验 4, Fig 4e).

PRE-REGISTERED 2026-09-01 before any cell was run (reset convention: newly
written code, pilot first, zero-intervention production path, frozen results).

PURPOSE
  Measure, cell by cell, that capability gating on a certified oracle is
  SELECTIVE rather than prohibitive. The same production gate stack must
  (a) ALLOW ranking by gemorna_5utr_mrl on the three families where
  Exp-14 profiling certified it, (b) DOWNGRADE the same action on a
  never-profiled family of the same oracle (conservative transfer with
  decayed confidence — conclusions capped at within-target relative), and
  (c) BLOCK ranking by gemorna_3utr_stability outright (no measured anchor
  set exists — unprofiled by design), plus the matching ClaimGate scope
  ladder (pass / downgrade / reject).

RELATION TO LEGACY
  Re-run of the legacy E7 gate demonstration (``e7_gate_demo.jsonl``,
  2026-08-11; the asset was deleted with the legacy campaign — outcomes
  retained in the never-delete ``e7_mrna_oracle_profile_summary.json``).
  Differences vs legacy, all disclosed here before running:
  - legacy demoed ONE verified family (sorted-first); this run measures
    all three certified families;
  - legacy's never-profiled family was the synthetic label
    ``unprofiled_novel_utr_family``; this run uses the production key
    ``novel_utr_family_7`` with its real 50-nt candidates from the Exp-18
    mRNA audit set (the same key the production gated arm queried);
  - legacy consulted the SelfModel it built in-run; this run queries the
    packaged default SelfModel as shipped
    (``agent_core/calibrated/default_self_model.json``) — the exact
    instrument the Exp-17/18 gated arms used, whose MRL profile Exp 14
    re-certified 706/706 bit-identical;
  - NEW enforcement layer: one representative cell per verdict class is
    executed through the real ``ToolExecutor.run_tool`` under the same
    ``oracle_use`` context, so allow/downgrade demonstrably reach the live
    GEMORNA service and require_profiling demonstrably does not
    (GatedActionError raised before invocation).

INSTRUMENT (production path, zero intervention)
  - ``CalibratedRuntime`` configured from ``RNADA_CAPGATE=enforce`` with the
    packaged default SelfModel; every gate decision, claim verdict and tool
    call lands in the platform audit trail (``workspace/audit/
    platform_audit.jsonl`` — run this driver from ``rna_agent_system/``).
  - DecisionGate cells via ``runtime.review_tool_call(<managed tool>)``
    under ``oracle_use("ranking_objective", target_family=<family>)`` —
    exactly the review ToolExecutor consults; the executor's own enforcing
    behaviour is measured separately in the enforcement layer.
  - ClaimGate cells via ``runtime.claim_gate.review`` (deterministic scope
    templates, LLM polish off — ZERO LLM calls in this experiment).
  - Live service: GEMORNA 8004 (health-checked before the enforcement
    layer; GPU 0/1/2 placement inherited, untouched).

DATASETS (latest re-run alignment, user-confirmed 2026-09-01)
  - Certified families: ``data/benchmarks/external_anchors/utr_mrl/
    e7_mrl_anchor_set.json`` (706 entries / 3 families; Sample et al. 2019
    MPRA, GEO GSE114002) — the same file Fig 3f (Exp 14) re-certified and
    Fig 4d (Exp 18) used as MRL ground truth. sha256 frozen in the summary.
  - Never-profiled family key + candidates: ``e18_audit_tasks_mrna.json``
    cross_family_expression task (novel_utr_family_7; novel_utr7_a/b/c).
  - 3'UTR sequence for the blocked cell: the Insulin construct 3'UTR from
    the same e18 task set (production full-length design output).
  - E1 cross-check oracle: the retained ``e7_mrl_scoring.jsonl`` (Exp 14
    verified it 706/706 bit-identical through this same tool path).

CELLS AND PRE-REGISTERED EXPECTATIONS
  DecisionGate (pre-action; use = ranking_objective throughout):
    D1 mrl × sample2019_egfp_random50         -> allow,  not blocked
    D2 mrl × sample2019_varying_length_random -> allow,  not blocked
    D3 mrl × sample2019_varying_length_human  -> allow,  not blocked
    D4 mrl × novel_utr_family_7               -> downgrade (transferred,
       transferred_from_grade=verified, confidence exactly 0.5 = 1.0 × the
       0.5 transfer decay), not blocked
    D5 utr3 × sample2019_egfp_random50        -> require_profiling, BLOCKED
    D6 utr3 × novel_utr_family_7              -> require_profiling, BLOCKED
  ClaimGate (pre-publication; absolute-scope ranking claims):
    C1 dep(gemorna_5utr_mrl, ranking) × certified family -> pass
    C2 dep(gemorna_5utr_mrl, ranking) × novel family     -> downgrade,
       scope absolute -> within_target_relative, deterministic rewritten
       text carrying the [DOWNGRADED: ...] marker
    C3 dep(gemorna_3utr_stability, ranking) × novel family -> reject
  Enforcement (ToolExecutor.run_tool, live service):
    E1 allow executes:     MRL tool on the first ranking-eligible anchor
       (by id) of sample2019_egfp_random50 -> success AND predicted_mrl
       exactly equals the Exp-14 cached value for that anchor
    E2 downgrade executes: MRL tool on novel_utr7_a under
       novel_utr_family_7 -> success (the call is not blocked; capping the
       conclusion's scope is the ClaimGate's job, demonstrated by C2)
    E3 block holds:        3'UTR tool on the e18 Insulin 3'UTR under a
       certified family -> ToolResult success=False, error.type
       GatedActionError, error.verdict require_profiling, gated=true audit
       row; the service is never invoked

GO/NO-GO: mechanism verification — GO iff all 12 cells meet their
  pre-registered expectation. Any deviation is recorded honestly (legacy
  convention: ``expectation_met`` false) and fails the stage.

STAGING
  pilot: D1, D4, D5, C1, C2, C3 — one cell per verdict class per gate
    layer; no service needed. STOP on any expectation miss.
  full:  all 12 cells (needs GEMORNA 8004 up); freezes ``cells.jsonl`` +
    ``summary.json`` under ``experiments/results/exp23_selective_gating/``.

Usage (from ``rna_agent_system/``):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp23_selective_gating.py --stage pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp23_selective_gating.py --stage full
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# This experiment measures the ENFORCING stack — set before any
# runtime_from_env() so the packaged default SelfModel gates under enforce.
os.environ.setdefault("RNADA_CAPGATE", "enforce")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_core.calibrated.models import Claim, ClaimDependency  # noqa: E402
from agent_core.calibrated.runtime import (  # noqa: E402
    ORACLE_GOVERNANCE,
    oracle_use,
    runtime_from_env,
)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp23_selective_gating"
CELLS_JSONL = RESULTS_DIR / "cells.jsonl"
SUMMARY_JSON = RESULTS_DIR / "summary.json"
RUN_LOG = RESULTS_DIR / "run.log"

MRL_ANCHORS = (
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "utr_mrl" / "e7_mrl_anchor_set.json"
)
EXP14_CACHE = PROJECT_ROOT / "experiments" / "results" / "e7_mrl_scoring.jsonl"
E18_TASKS = PROJECT_ROOT / "experiments" / "e18_audit_tasks_mrna.json"

GATE_TASK_TYPE = "full_length_mrna"  # the ToolSpec default both GEMORNA oracles register under
MRL_TOOL = "predict_5utr_mrl_with_gemorna"
UTR3_TOOL = "predict_3utr_stability_with_gemorna"
MRL_ORACLE = "gemorna_5utr_mrl"
UTR3_ORACLE = "gemorna_3utr_stability"
USE = "ranking_objective"

CERTIFIED_FAMILIES = [
    "sample2019_egfp_random50",
    "sample2019_varying_length_random",
    "sample2019_varying_length_human",
]
NOVEL_FAMILY = "novel_utr_family_7"  # production key from the Exp-18 cross-family tasks
TRANSFER_DECAY = 0.5  # SelfModel.TRANSFER_CONFIDENCE_DECAY (design doc §2.3 step 1)

CLAIM_TEXT_MRL = (
    "5'UTR candidate A will drive higher protein expression than candidate B "
    "in the final mRNA."
)
CLAIM_TEXT_UTR3 = (
    "The construct carrying 3'UTR candidate A will persist longer than the "
    "construct carrying candidate B."
)

_PILOT_CELLS = {"D1", "D4", "D5", "C1", "C2", "C3"}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _log(fh, msg: str) -> None:
    line = f"[{_utc_iso()}] {msg}"
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def _load_novel_family_inputs() -> tuple[str, str]:
    """novel family key + one real candidate sequence, from the Exp-18 set."""
    tasks = json.loads(E18_TASKS.read_text(encoding="utf-8"))
    tasks = tasks["tasks"] if isinstance(tasks, dict) else tasks
    cross = [t for t in tasks if t.get("target_family") == NOVEL_FAMILY]
    assert cross, f"e18 task set carries no {NOVEL_FAMILY} task"
    cands = sorted(cross[0]["candidates"], key=lambda c: c["candidate_id"])
    return cross[0]["target_family"], cands[0]["sequence"]


def _load_utr3_sequence() -> tuple[str, str]:
    """A production-designed 3'UTR from the e18 utr3 task (candidate id, seq)."""
    tasks = json.loads(E18_TASKS.read_text(encoding="utf-8"))
    tasks = tasks["tasks"] if isinstance(tasks, dict) else tasks
    utr3 = [t for t in tasks if t.get("task_family") == "utr3_stability_rank"]
    assert utr3, "e18 task set carries no utr3_stability_rank task"
    task = sorted(utr3, key=lambda t: t["id"])[0]
    cand = sorted(task["candidates"], key=lambda c: c["candidate_id"])[0]
    return cand["candidate_id"], cand["sequence"]


def _load_e1_anchor() -> dict:
    """First ranking-eligible anchor by id in the demo family (legacy rule)."""
    entries = json.loads(MRL_ANCHORS.read_text(encoding="utf-8"))["entries"]
    pool = sorted(
        (e for e in entries
         if e["target"] == CERTIFIED_FAMILIES[0] and e.get("ranking_eligible")),
        key=lambda e: e["id"],
    )
    assert pool, f"no ranking-eligible anchors in {CERTIFIED_FAMILIES[0]}"
    return pool[0]


def _load_exp14_cache(anchor_id: str) -> dict:
    for line in EXP14_CACHE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("id") == anchor_id:
            return row
    raise AssertionError(f"anchor {anchor_id} missing from the Exp-14 cache")


def _service_health(url: str = "http://127.0.0.1:8004/health", timeout: float = 5.0) -> str:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace").strip()
    except Exception as exc:  # noqa: BLE001
        return f"UNREACHABLE: {type(exc).__name__}: {exc}"


def _audit_lines(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("rb"))
    except FileNotFoundError:
        return 0


# ── cell implementations ─────────────────────────────────────────────────────


def cell_decision(runtime, cell_id: str, tool: str, family: str, expected: str,
                  expect_confidence: float | None = None) -> dict:
    """DecisionGate review of one managed tool under the production keying."""
    with oracle_use(USE, target_family=family):
        dec = runtime.review_tool_call(tool)
    assert dec is not None, f"{tool} is not a managed oracle tool"
    blocked = runtime.should_block(dec, tool)
    oracle = dec.oracle
    cell = runtime.self_model.query(oracle, GATE_TASK_TYPE, family).assessment("ranking")
    met = dec.verdict == expected and blocked == (expected in ("reject", "require_profiling"))
    detail: dict = {
        "grade": cell.grade,
        "confidence": cell.confidence,
        "transferred_from_grade": cell.transferred_from_grade,
        "source_case_id": cell.source_case_id,
        "reason": dec.reason,
        "required_capability": dec.required_capability,
        "n_evidence": len(dec.evidence),
        "should_block": blocked,
        "governance": ORACLE_GOVERNANCE.get(tool),
    }
    if expect_confidence is not None:
        met = met and cell.confidence == expect_confidence
    return {
        "cell": cell_id, "layer": "decision_gate", "tool": tool, "oracle": oracle,
        "use": USE, "task_type": GATE_TASK_TYPE, "target_family": family,
        "expected_verdict": expected, "actual_verdict": dec.verdict,
        "expectation_met": met, "detail": detail,
    }


def cell_claim(runtime, cell_id: str, oracle: str, family: str, text: str,
               expected: str, expect_scope: str | None = None) -> dict:
    """ClaimGate review of one absolute-scope ranking claim."""
    claim = Claim(
        claim_id=cell_id,
        text=text,
        claim_type="ranking",
        scope="absolute",
        dependencies=[ClaimDependency(oracle=oracle, capability="ranking")],
    )
    v = runtime.claim_gate.review([claim], task_type=GATE_TASK_TYPE, target_family=family)[0]
    met = v.verdict == expected
    if expect_scope is not None:
        met = met and expect_scope in v.reason
    if expected == "downgrade":
        met = met and (v.rewritten_text or "").startswith("[DOWNGRADED:")
    return {
        "cell": cell_id, "layer": "claim_gate", "oracle": oracle,
        "claim_text": text, "task_type": GATE_TASK_TYPE, "target_family": family,
        "expected_verdict": expected, "actual_verdict": v.verdict,
        "expectation_met": met,
        "detail": {
            "reason": v.reason,
            "rewritten_text": v.rewritten_text,
            "dependency_grades": {d.oracle: d.grade for d in v.dependencies},
        },
    }


def _write_seq(scratch: Path, name: str, sequence: str) -> str:
    f = scratch / f"{name}.txt"
    f.write_text(sequence, encoding="utf-8")
    return str(f.relative_to(PROJECT_ROOT))


def cell_enforce_allow(executor, anchor: dict, cached: dict, scratch: Path) -> dict:
    """E1: the allow verdict lets the call reach the live service; the score
    must reproduce the Exp-14 cached prediction exactly."""
    rel = _write_seq(scratch, f"e1_{anchor['id']}", anchor["sequence"])
    with oracle_use(USE, target_family=CERTIFIED_FAMILIES[0]):
        res = executor.run_tool(MRL_TOOL, filepath=rel)
    ok = bool(res.success)
    got = None
    if ok:
        got = res.artifacts.get("result", {}).get("predicted_mrl")
    want = cached["response"]["predicted_mrl"]
    met = ok and got == want
    return {
        "cell": "E1", "layer": "enforcement", "tool": MRL_TOOL,
        "use": USE, "task_type": GATE_TASK_TYPE,
        "target_family": CERTIFIED_FAMILIES[0],
        "anchor_id": anchor["id"], "anchor_measured_mrl": anchor.get("measured_mrl"),
        "expected_verdict": "executed+bit_identical",
        "actual_verdict": "executed" if ok else "failed",
        "expectation_met": met,
        "detail": {
            "predicted_mrl": got, "exp14_cached_mrl": want,
            "exact_match": got == want if got is not None else False,
            "service_echo": res.artifacts.get("result", {}).get("input_sequence") if ok else None,
            "error": res.error,
        },
    }


def cell_enforce_downgrade(executor, novel_family: str, novel_seq: str, scratch: Path) -> dict:
    """E2: the downgrade verdict does NOT block the call (transferred grades
    stay usable with capped conclusions); the service executes."""
    rel = _write_seq(scratch, "e2_novel_utr7_a", novel_seq)
    with oracle_use(USE, target_family=novel_family):
        res = executor.run_tool(MRL_TOOL, filepath=rel)
    ok = bool(res.success)
    got = res.artifacts.get("result", {}).get("predicted_mrl") if ok else None
    return {
        "cell": "E2", "layer": "enforcement", "tool": MRL_TOOL,
        "use": USE, "task_type": GATE_TASK_TYPE, "target_family": novel_family,
        "sequence_source": "e18 cross_family_expression candidate (novel_utr7_a)",
        "expected_verdict": "executed", "actual_verdict": "executed" if ok else "failed",
        "expectation_met": ok,
        "detail": {"predicted_mrl": got, "error": res.error},
    }


def cell_enforce_block(executor, cand_id: str, utr3_seq: str, scratch: Path,
                       audit_path: Path) -> dict:
    """E3: the require_profiling verdict blocks at the tool layer —
    GatedActionError before invocation, gated=true audit row, no service hit."""
    rel = _write_seq(scratch, f"e3_{cand_id[:12]}", utr3_seq)
    with oracle_use(USE, target_family=CERTIFIED_FAMILIES[0]):
        res = executor.run_tool(UTR3_TOOL, filepath=rel)
    err = res.error or {}
    gated_row = None
    tail = []
    try:
        with audit_path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 200_000))
            tail = fh.read().decode("utf-8", "replace").splitlines()
        for line in reversed(tail):
            if '"tool_name": "predict_3utr_stability_with_gemorna"' in line and '"gated": true' in line:
                gated_row = json.loads(line)
                break
    except Exception:  # noqa: BLE001 - corroboration only
        pass
    met = (
        (not res.success)
        and err.get("type") == "GatedActionError"
        and err.get("verdict") == "require_profiling"
        and gated_row is not None
    )
    return {
        "cell": "E3", "layer": "enforcement", "tool": UTR3_TOOL,
        "use": USE, "task_type": GATE_TASK_TYPE,
        "target_family": CERTIFIED_FAMILIES[0],
        "sequence_source": f"e18 utr3_stability_rank candidate {cand_id} (production 3'UTR)",
        "expected_verdict": "blocked", "actual_verdict": err.get("type", "executed"),
        "expectation_met": met,
        "detail": {
            "error": err, "elapsed_s": round(res.elapsed_time, 6),
            "audit_gated_row_found": gated_row is not None,
            "audit_row_event_type": (gated_row or {}).get("event_type"),
        },
    }


# ── stages ───────────────────────────────────────────────────────────────────


def run(stage: str) -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    scratch = RESULTS_DIR / "scratch"
    scratch.mkdir(exist_ok=True)
    started = time.monotonic()
    with RUN_LOG.open("a", encoding="utf-8") as log:
        _log(log, f"exp23 selective gating — stage={stage}")

        runtime = runtime_from_env()
        assert runtime is not None and runtime.policy == "enforce", (
            "this experiment measures the enforcing stack: RNADA_CAPGATE=enforce required"
        )
        audit_path = Path(runtime.audit.path)
        audit_start = _audit_lines(audit_path)
        mrl_records = [
            r for r in runtime.self_model.records()
            if r.oracle == MRL_ORACLE and r.task_type == GATE_TASK_TYPE
        ]
        utr3_records = [
            r for r in runtime.self_model.records() if r.oracle == UTR3_ORACLE
        ]
        assert len(mrl_records) == 3, f"packaged SelfModel MRL records: {len(mrl_records)} != 3"
        assert not utr3_records, "packaged SelfModel unexpectedly carries 3'UTR records"
        assert ORACLE_GOVERNANCE.get(MRL_TOOL) == "enforce"
        assert ORACLE_GOVERNANCE.get(UTR3_TOOL) == "enforce"
        drift = runtime.oracle_version_drift()
        _log(
            log,
            f"runtime: policy=enforce self_model_records={len(runtime.self_model.records())} "
            f"mrl_families={[r.target_family for r in mrl_records]} utr3_records=0 "
            f"version_drift={drift or 'none'} audit={audit_path}",
        )

        anchor = _load_e1_anchor()
        cached = _load_exp14_cache(anchor["id"])
        novel_family, novel_seq = _load_novel_family_inputs()
        utr3_cand, utr3_seq = _load_utr3_sequence()
        assert novel_family == NOVEL_FAMILY
        _log(
            log,
            f"inputs: e1_anchor={anchor['id']} (measured_mrl={anchor['measured_mrl']:.4f}) "
            f"novel_family={NOVEL_FAMILY} utr3_source={utr3_cand}",
        )

        cells: list[dict] = []

        # ── DecisionGate layer ────────────────────────────────────────────────
        d_specs = [
            ("D1", MRL_TOOL, CERTIFIED_FAMILIES[0], "allow", None),
            ("D2", MRL_TOOL, CERTIFIED_FAMILIES[1], "allow", None),
            ("D3", MRL_TOOL, CERTIFIED_FAMILIES[2], "allow", None),
            ("D4", MRL_TOOL, NOVEL_FAMILY, "downgrade", round(1.0 * TRANSFER_DECAY, 4)),
            ("D5", UTR3_TOOL, CERTIFIED_FAMILIES[0], "require_profiling", None),
            ("D6", UTR3_TOOL, NOVEL_FAMILY, "require_profiling", None),
        ]
        for cell_id, tool, fam, expected, conf in d_specs:
            if stage == "pilot" and cell_id not in _PILOT_CELLS:
                continue
            cells.append(cell_decision(runtime, cell_id, tool, fam, expected, conf))
            c = cells[-1]
            _log(log, f"  {cell_id}: {c['actual_verdict']} (expect {expected}) met={c['expectation_met']}")

        # ── ClaimGate layer ───────────────────────────────────────────────────
        c_specs = [
            ("C1", MRL_ORACLE, CERTIFIED_FAMILIES[0], CLAIM_TEXT_MRL, "pass", None),
            ("C2", MRL_ORACLE, NOVEL_FAMILY, CLAIM_TEXT_MRL, "downgrade", "within_target_relative"),
            ("C3", UTR3_ORACLE, NOVEL_FAMILY, CLAIM_TEXT_UTR3, "reject", None),
        ]
        for cell_id, oracle, fam, text, expected, scope in c_specs:
            if stage == "pilot" and cell_id not in _PILOT_CELLS:
                continue
            cells.append(cell_claim(runtime, cell_id, oracle, fam, text, expected, scope))
            c = cells[-1]
            _log(log, f"  {cell_id}: {c['actual_verdict']} (expect {expected}) met={c['expectation_met']}")

        # ── enforcement layer (full stage only; needs the live service) ──────
        if stage == "full":
            health = _service_health()
            _log(log, f"GEMORNA service health: {health}")
            assert '"ok"' in health, f"GEMORNA 8004 unreachable: {health}"
            from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

            executor = ToolExecutor(build_default_tool_registry())
            cells.append(cell_enforce_allow(executor, anchor, cached, scratch))
            _log(
                log,
                f"  E1: {cells[-1]['actual_verdict']} mrl={cells[-1]['detail']['predicted_mrl']} "
                f"cached={cells[-1]['detail']['exp14_cached_mrl']} met={cells[-1]['expectation_met']}",
            )
            cells.append(cell_enforce_downgrade(executor, novel_family, novel_seq, scratch))
            _log(log, f"  E2: {cells[-1]['actual_verdict']} met={cells[-1]['expectation_met']}")
            cells.append(cell_enforce_block(executor, utr3_cand, utr3_seq, scratch, audit_path))
            _log(log, f"  E3: {cells[-1]['actual_verdict']} met={cells[-1]['expectation_met']}")

        # ── freeze ────────────────────────────────────────────────────────────
        with CELLS_JSONL.open("w", encoding="utf-8") as fh:
            for c in cells:
                fh.write(json.dumps(c, ensure_ascii=False, default=str) + "\n")
        n_met = sum(1 for c in cells if c["expectation_met"])
        ok = n_met == len(cells)
        audit_end = _audit_lines(audit_path)
        summary = {
            "experiment": "exp23_selective_gating",
            "paper_ref": "§2.4 实验 4 / Fig 4e — selective gating decision matrix",
            "legacy_relation": "re-run of the legacy E7 gate demo (e7_gate_demo.jsonl, 2026-08-11)",
            "stage": stage,
            "timestamp_utc": _utc_iso(),
            "wall_s": round(time.monotonic() - started, 3),
            "cells_total": len(cells),
            "cells_expectation_met": n_met,
            "all_met": ok,
            "llm_calls": 0,
            "instrument": {
                "policy": runtime.policy,
                "self_model_path": "agent_core/calibrated/default_self_model.json",
                "self_model_sha256": _sha256(
                    PROJECT_ROOT / "agent_core" / "calibrated" / "default_self_model.json"
                ),
                "self_model_records": len(runtime.self_model.records()),
                "mrl_certified_families": [r.target_family for r in mrl_records],
                "utr3_records": 0,
                "oracle_version_drift": drift,
                "decision_gate_via": "runtime.review_tool_call under oracle_use(ranking_objective, family)",
                "claim_gate_via": "runtime.claim_gate.review (deterministic templates, polish off)",
                "enforcement_via": "ToolExecutor.run_tool (production registry)",
                "audit_trail": str(audit_path),
                "audit_lines_written_this_run": audit_end - audit_start,
                "service_health": _service_health() if stage == "full" else "not probed (pilot)",
            },
            "datasets": {
                "mrl_anchor_set": {
                    "path": str(MRL_ANCHORS.relative_to(PROJECT_ROOT)),
                    "sha256": _sha256(MRL_ANCHORS),
                    "n_entries": 706,
                    "certified_by": "Exp 14 (Fig 3f), 706/706 bit-identical",
                },
                "novel_family_source": {
                    "path": str(E18_TASKS.relative_to(PROJECT_ROOT)),
                    "sha256": _sha256(E18_TASKS),
                    "note": "Exp-18 (Fig 4d) cross_family_expression task: novel_utr_family_7",
                },
                "utr3_sequence_source": f"e18 utr3_stability_rank candidate {utr3_cand}",
                "e1_crosscheck_cache": {
                    "path": str(EXP14_CACHE.relative_to(PROJECT_ROOT)),
                    "sha256": _sha256(EXP14_CACHE),
                    "anchor_id": anchor["id"],
                },
            },
            "verdict_matrix": {
                c["cell"]: {
                    "layer": c["layer"],
                    "oracle": c.get("oracle") or c.get("tool"),
                    "family": c["target_family"],
                    "verdict": c["actual_verdict"],
                    "met": c["expectation_met"],
                }
                for c in cells
            },
        }
        SUMMARY_JSON.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        _log(
            log,
            f"stage {stage} complete: {n_met}/{len(cells)} cells met expectations "
            f"-> {'GO' if ok else 'NO-GO'}; results frozen to {RESULTS_DIR}",
        )
        return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", choices=["pilot", "full"], default="pilot")
    args = ap.parse_args()
    return run(args.stage)


if __name__ == "__main__":
    sys.exit(main())
