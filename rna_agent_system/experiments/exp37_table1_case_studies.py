#!/usr/bin/env python3
"""EXP 37 — Table 1 end-to-end case studies (fourth reset, §2.7, 2026-09-06).

Pre-registration (pilot-first rule, MANUSCRIPT.md §2)
-----------------------------------------------------
OBJECT: three production campaigns through the USER FORM entry, one per
Table-1 row, on the shipped platform — which since the 2026-09-06 platform
default change (DECISIONS (aa)) runs GenNav-λ constraint navigation by
default on the mRNA design flows under CapGate (advisory campaign
convention) with ASF ranking governance.

* Case A — SARS-CoV-2 Spike full-length mRNA: ``full_length_mrna_design``
  form entry, ``SARS-CoV-2_Spike_WT`` target verbatim (1273 aa, Homo
  sapiens), ``utr_mode=all``, ``navigation`` UNSET → the v2.0.0 platform
  default (GenNav-λ CDS navigation; UTR composition and CapGate-governed ASF
  ranking unchanged). Metrics: wall time, best candidate CDS CAI, CDS
  MFE/nt, navigation trace (raw spend, per-profile deliveries), session
  audit-event counts. Anchor: BNT162b2 assembled-contig CDS CAI via the
  SAME production CAI tool and Kazusa human table (CDS extracted as the
  longest in-frame AUG→stop ORF of the contig; extraction rule registered
  here — the contig is putative and may lack terminal bases, disclosed).
* Case B — anti-VEGF aptamer, production v4 navigation mode:
  ``rna_aptamer_design`` form entry, ``navigation=true``, VEGF target
  (1VPF chain A, the benchmark's registered anti-VEGF target), PA_028-style
  reference point. Metrics: wall time, top-candidate EGARPS component,
  navigation trace. Anchor: pegaptanib unmodified base sequence re-measured
  through the SAME production chain as sequence-side targets (ProteinX
  complex from the 1VPF chain-A protein sequence + pegaptanib RNA sequence
  → EGARPS native probability). ROW-B UNIFICATION (user-delegated
  2026-09-06): the plan note said "EGF"; no EGF target, structure or anchor
  exists on disk — the registered row (anti-VEGF + the pegaptanib anchor
  panel + the self-audit narrative) is kept. NARRATIVE REGISTER: the gap
  between the designed candidate and the anchor is reported as the
  SELF-AUDIT worked example, NOT a superiority claim — the structure oracles
  carry no verified screening power on this family (Exp 10/13: chance-level
  at scale), the complexes come from incomparable sources (ODesign
  prediction vs ProteinX re-fold), and pegaptanib's 2′-fluoro modifications
  are unrepresentable to the scorer.
* Case C — NSP12 siRNA: ``sirna_design`` form entry with the registered
  PA_016 structured input verbatim (antiviral Evitar, predsi, 5 candidates,
  bowtie2 human-transcriptome off-target scan, GC 0.25–0.6). Metrics: wall
  time, per-candidate off-target hit counts (top-5), GC, duplex MFE; scan
  evidence trace-verified against the session workspace (Exp-6 convention).

PROTOCOL: pilot-first (case C + the case-A anchor recomputation — fast, zero
LLM drivers) before the production cases (A then B then C again on the
production path — case C's production re-run uses a fresh session id).
Every case through the form entry subprocess (``cli/form_chat.py``),
``RNADA_CAPGATE=advisory``, quality review on (default). Wall times measure
the delivered workflow on the otherwise-quiet machine (disclosed; no
concurrent campaign during the case runs).

OUTPUTS: ``experiments/results/exp37_table1_case_studies/{caseA,caseB,caseC}/``
+ ``table1.json`` (the row-anchored record) + ``summary.json``.
``--verify`` recomputes the anchors and the recorded headline numbers from
the frozen session artifacts and asserts equality with the stored verdict.

Usage (from ``rna_agent_system/``):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp37_table1_case_studies.py pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp37_table1_case_studies.py caseA
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp37_table1_case_studies.py caseB
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp37_table1_case_studies.py caseC
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp37_table1_case_studies.py verify
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp37_table1_case_studies"
TARGETS_FL = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
BNT162B2_FA = (
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "vaccine_mrna"
    / "bnt162b2_full.fa"
)
VEGF_PDB = (
    PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
    / "1vpf.pdb"
)
PA_TASKS = json.loads(
    (PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-ProcessAware"
     / "task_set_for_llm_comparison.json").read_text(encoding="utf-8")
)

# pegaptanib (Macugen) unmodified base sequence — anchor set v3 entry
# ``pegaptanib_vegf`` (T→U), assertion-checked against the anchor file at run.
PEGAPTANIB_RNA = "CGGAAUCAGUGAAUGCUUAUACAUCCG"


def log_line(msg: str) -> None:
    print(f"[exp37 {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def find_results_file(session_dir: Path) -> Optional[Path]:
    files = sorted(session_dir.glob("workflow_results_*.json"),
                   key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def run_cli(
    workflow: str,
    params: dict[str, Any],
    *,
    session_id: str,
    timeout: int,
    capgate: str = "advisory",
) -> tuple[dict[str, Any] | None, int, float, str | None]:
    """One form-driven CLI run (exp2 convention)."""
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    params_file = session_dir / "params.json"
    params_file.write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    env["RNADA_CAPGATE"] = capgate

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "cli" / "form_chat.py"),
        "--workflow", workflow,
        "--params-file", str(params_file),
        "--session-id", session_id,
    ]
    log_path = session_dir / "driver.log"
    started = time.monotonic()
    exit_code, error = -1, None
    with log_path.open("w", encoding="utf-8", errors="replace") as log_fp:
        try:
            proc = subprocess.run(
                cmd, cwd=PROJECT_ROOT, env=env,
                stdout=log_fp, stderr=subprocess.STDOUT,
                input="y\n", text=True, timeout=timeout,
            )
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            error = "timeout"
    elapsed = time.monotonic() - started

    results = None
    results_file = find_results_file(session_dir)
    if error is None and exit_code != 0:
        error = "cli_failure"
    if error is None and results_file is None:
        error = "no_results_file"
    if results_file is not None:
        try:
            results = json.loads(results_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            error = error or "parse_error"
    if error is None and results is not None and not results.get("success"):
        error = "workflow_success_false"
    return results, exit_code, elapsed, error


# ── shared production-tool helpers (audited path, advisory CapGate) ─────────


def _tool_call(tool_name: str, **kwargs: Any) -> dict[str, Any]:
    """One ToolExecutor call — lands in the platform audit trail."""
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    executor = ToolExecutor(build_default_tool_registry())
    res = executor.run_tool(tool_name, **kwargs)
    if not res.success:
        raise RuntimeError(f"tool {tool_name} failed: {res.error}")
    return {k: v for k, v in res.artifacts.items()}


def save_seq_file(seq: str, session_scope: str, name: str) -> Path:
    from agent_core.file_manager import save_sequence

    p = save_sequence(seq, prefix=f"exp37_{session_scope}_{name}")
    return Path(p if os.path.isabs(p) else PROJECT_ROOT / p)


# ── anchors ─────────────────────────────────────────────────────────────────


def longest_orf_cds(contig_rna: str) -> str:
    """Longest in-frame AUG→stop ORF of the contig (registered extraction
    rule for the putative BNT162b2 assembled contig)."""
    best = ""
    for frame in range(3):
        seq = contig_rna[frame:]
        start = 0
        while True:
            aug = seq.find("AUG", start)
            if aug < 0:
                break
            stop = None
            for i in range(aug + 3, len(seq) - 2, 3):
                if seq[i:i + 3] in ("UAA", "UAG", "UGA"):
                    stop = i
                    break
            if stop is not None:
                orf = seq[aug:stop + 3]
                if len(orf) > len(best):
                    best = orf
            start = aug + 3
    return best


def bnt162b2_cds() -> str:
    raw = "".join(
        line.strip() for line in BNT162B2_FA.read_text(encoding="utf-8").splitlines()
        if not line.startswith(">")
    )
    rna = raw.upper().replace("T", "U").replace(" ", "")
    cds = longest_orf_cds(rna)
    assert len(cds) >= 3000, f"BNT162b2 ORF too short: {len(cds)}"
    return cds


def spike_target() -> dict[str, Any]:
    return json.loads(
        (TARGETS_FL / "SARS-CoV-2_Spike_WT.json").read_text(encoding="utf-8")
    )


# ── case A ──────────────────────────────────────────────────────────────────


def run_case_a(*, pilot: bool = False) -> dict[str, Any]:
    tgt = spike_target()
    params = {
        "protein_sequence": tgt["protein_sequence"],
        "cai_species": tgt.get("species_for_codon_optimization", "Homo sapiens"),
        "utr_mode": "all",
        # navigation deliberately UNSET — the v2.0.0 platform default is the
        # object of measurement for Table-1 row A.
    }
    session = "exp37_caseA_spike" if not pilot else "exp37_pilotA_smoke"
    if pilot:
        # pilot: params validation only (dry construction, no full run —
        # the platform-level navigation pilot is the registered Insulin run)
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignInput,
        )
        inp = FullLengthMrnaDesignInput(**params)
        assert inp.navigation is None and inp.design_tool == "all"
        log_line("caseA pilot: input construction OK (navigation unset → default)")
        return {"pilot": "ok"}

    timeout = 3600 * 4
    log_line(f"caseA: Spike full-length ({tgt['protein_length_aa']} aa) form entry, "
             f"timeout {timeout}s — this is the long case")
    results, exit_code, elapsed, error = run_cli(
        "full_length_mrna_design", params, session_id=session, timeout=timeout
    )
    record: dict[str, Any] = {
        "case": "A",
        "session_id": session,
        "workflow_success": bool(results and results.get("success")),
        "exit_code": exit_code,
        "wall_seconds": round(elapsed, 2),
        "error": error,
    }
    if results and results.get("success"):
        best = results.get("best_candidate") or {}
        sc = best.get("scores") or {}
        mb = best.get("metadata", {}).get("metrics_bundle", {}) or {}
        cands = results.get("candidates") or results.get("all_candidates") or []
        record["best"] = {
            "source": best.get("source"),
            "cds_source": best.get("metadata", {}).get("cds_source"),
            "cds_cai": sc.get("cds_cai", mb.get("cds_cai")),
            "cds_mfe": sc.get("cds_mfe", mb.get("cds_mfe")),
            "cds_mfe_per_nt": (
                (sc.get("cds_mfe", mb.get("cds_mfe")) / sc.get("cds_length", mb.get("cds_length")))
                if (sc.get("cds_mfe", mb.get("cds_mfe")) is not None
                    and sc.get("cds_length", mb.get("cds_length")))
                else None
            ),
            "cds_length": sc.get("cds_length", mb.get("cds_length")),
            "total_length": sc.get("total_length", mb.get("total_length")),
            "utr5_preset": best.get("metadata", {}).get("utr5_preset"),
            "utr3_preset": best.get("metadata", {}).get("utr3_preset"),
            "asf_distance": sc.get("asf_distance"),
            "cds_sequence": best.get("metadata", {}).get("cds_sequence"),
        }
        record["n_candidates"] = len(cands) or str(
            results.get("summary", "")).split("candidates=", 1)[-1].split("\n", 1)[0]
        # navigation trace — persisted top-level in the results file by
        # cli/form_chat.py for full navigation auditability
        nav = results.get("_gennav_trace")
        if nav:
            record["gennav_trace"] = {
                "raw_spent": nav.get("raw_spent"),
                "raw_budget": nav.get("raw_budget"),
                "pool_size": nav.get("pool_size"),
                "deliveries": {
                    p: {
                        "n": len(d.get("candidates", d.get("ids", []))),
                        "degraded": d.get("degraded"),
                    }
                    for p, d in (nav.get("deliveries") or {}).items()
                },
            }
        record["anchor_bnt162b2_cds_cai"] = bnt162b2_cai()
    (RESULTS_DIR / "caseA").mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "caseA" / "record.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    log_line(f"caseA done: success={record['workflow_success']} wall={elapsed:.0f}s "
             f"error={error}")
    return record


def bnt162b2_cai() -> float:
    """Anchor: BNT162b2 CDS CAI via the production CAI tool (human table)."""
    cds = bnt162b2_cds()
    fp = save_seq_file(cds, "caseA", "bnt162b2_cds")
    out = _tool_call("compute_cai_for_cds_sequence",
                     filepath=str(fp), species="Homo sapiens")
    return float(out["result"]["cai_score"])


# ── case B ──────────────────────────────────────────────────────────────────


def vegf_protein_sequence() -> str:
    tgt = json.loads(
        (PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "targets"
         / "VEGF.json").read_text(encoding="utf-8")
    )
    return tgt["protein_sequence"]


def run_case_b(*, pilot: bool = False) -> dict[str, Any]:
    params = {
        "protein_structure_path": str(VEGF_PDB),
        "chain_id": "A",
        "navigation": True,
        "reference_point": {
            "egarps_component": 0.5,
            "rhofold_component": 0.5,
            "iptm_component": 0.5,
        },
    }
    if pilot:
        from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignInput
        inp = RnaAptamerDesignInput(**params)
        assert inp.navigation is True
        log_line("caseB pilot: input construction OK (v4 navigation pinned)")
        return {"pilot": "ok"}

    timeout = 3600 * 3
    log_line("caseB: anti-VEGF aptamer v4 navigation form entry (48-raw cap)")
    results, exit_code, elapsed, error = run_cli(
        "rna_aptamer_design", params, session_id="exp37_caseB_vegf_nav",
        timeout=timeout,
    )
    record: dict[str, Any] = {
        "case": "B",
        "session_id": "exp37_caseB_vegf_nav",
        "workflow_success": bool(results and results.get("success")),
        "exit_code": exit_code,
        "wall_seconds": round(elapsed, 2),
        "error": error,
        "row_b_unification": (
            "plan note said EGF; no EGF target/structure/anchor on disk — "
            "registered anti-VEGF row + pegaptanib anchor panel + self-audit "
            "narrative kept (user-delegated 2026-09-06)"
        ),
    }
    if results and results.get("success"):
        best = results.get("best_candidate") or {}
        scores = best.get("scores") or {}
        record["best"] = {
            "sequence": best.get("sequence"),
            "egarps_component": scores.get("egarps_component"),
            "rhofold_component": scores.get("rhofold_component"),
            "iptm_component": scores.get("iptm_component"),
            "asf_distance": scores.get("asf_distance"),
        }
    (RESULTS_DIR / "caseB").mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "caseB" / "record.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    log_line(f"caseB done: success={record['workflow_success']} wall={elapsed:.0f}s "
             f"error={error}")
    return record


def run_anchor_b() -> dict[str, Any]:
    """Pegaptanib anchor through the SAME production chain as sequence-side
    targets: ProteinX complex (1VPF chain-A protein sequence + pegaptanib
    RNA) → the workflow's own CIF→PDB complete-complex conversion
    (``_get_complete_complex_pdb`` — base rebuild included) → EGARPS native
    probability. Audited tool path, advisory CapGate. A scorer refusal on
    the converted complex is itself the honest anchor outcome (registered:
    the anchor's complex source is incomparable with generation-time
    predictions — the self-audit narrative's second leg)."""
    prot_fp = save_seq_file(vegf_protein_sequence(), "caseB", "vegf_prot")
    rna_fp = save_seq_file(PEGAPTANIB_RNA, "caseB", "pegaptanib_rna")
    log_line("anchorB: ProteinX complex (1VPF-A + pegaptanib) — several minutes")
    cx = _tool_call(
        "predict_rna_protein_complex_with_proteinx",
        protein_filepath=str(prot_fp),
        rna_filepath=str(rna_fp),
        num_models=1,
    )
    complex_path = cx["result"].get("pdb_filepath")
    assert complex_path, f"proteinx output missing pdb_filepath: {list(cx['result'])}"

    # Production CIF→PDB conversion (the workflow's own helper; ODesign CIFs
    # take exactly this path before EGARPS). Pure file processing — a
    # no-op registry satisfies the constructor.
    from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignWorkflow

    class _ConversionOnlyRegistry:
        def has(self, name: str) -> bool:
            return False

        def get(self, name: str):
            raise KeyError(name)

    wf = RnaAptamerDesignWorkflow(_ConversionOnlyRegistry())
    converted = wf._get_complete_complex_pdb(str(complex_path))
    egarps_value = None
    scorer_error = None
    if converted:
        try:
            eg = _tool_call("score_rna_protein_complex_with_egarps",
                            filepath=str(converted))
            egarps_value = float(eg["result"]["native_probability"])
        except RuntimeError as exc:
            scorer_error = str(exc)[:500]
    else:
        scorer_error = "cif_to_pdb_conversion_empty"
    anchor = {
        "pegaptanib_rna": PEGAPTANIB_RNA,
        "complex_path": str(complex_path),
        "converted_pdb": str(converted) if converted else None,
        "egarps_native_probability": egarps_value,
        "scorer_error": scorer_error,
    }
    (RESULTS_DIR / "caseB").mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "caseB" / "anchor.json").write_text(
        json.dumps(anchor, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    if egarps_value is not None:
        log_line(f"anchorB: egarps={egarps_value:.3e}")
    else:
        log_line(f"anchorB: EGARPS refused the anchor complex ({scorer_error}) "
                 "— registered as the self-audit instrument-boundary outcome")
    return anchor


# ── case C ──────────────────────────────────────────────────────────────────


def ns12_task() -> dict[str, Any]:
    for t in PA_TASKS.get("tasks", PA_TASKS if isinstance(PA_TASKS, list) else []):
        if isinstance(t, dict) and t.get("task_id") == "PA_016":
            return t
    raise KeyError("PA_016 not found in task_set_for_llm_comparison.json")


def run_case_c(*, production: bool = False) -> dict[str, Any]:
    task = ns12_task()
    params = dict(task["structured_input"])
    session = "exp37_caseC_nsp12" if production else "exp37_pilotC_nsp12"
    timeout = 1800
    log_line("caseC: NSP12 siRNA form entry (antiviral Evitar + bowtie2 scan)")
    results, exit_code, elapsed, error = run_cli(
        "sirna_design", params, session_id=session, timeout=timeout,
    )
    record: dict[str, Any] = {
        "case": "C",
        "session_id": session,
        "workflow_success": bool(results and results.get("success")),
        "exit_code": exit_code,
        "wall_seconds": round(elapsed, 2),
        "error": error,
    }
    if results and results.get("success"):
        cands = results.get("candidates") or results.get("all_candidates") or []
        top = cands[:5] if cands else []
        record["top5"] = []
        for c in top:
            sc = c.get("scores") or {}
            mt = c.get("metrics") or c.get("metadata", {}).get("metrics_bundle") or {}
            record["top5"].append({
                "sequence": c.get("sequence"),
                "off_target_hits": mt.get("off_target_count",
                                          sc.get("off_target_count")),
                "gc_content": mt.get("gc_content", sc.get("gc_content")),
                "duplex_mfe": mt.get("duplex_mfe", sc.get("duplex_mfe")),
            })
        record["n_candidates"] = len(cands)
    (RESULTS_DIR / "caseC").mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "caseC" / ("record.json" if production else "pilot.json")).write_text(
        json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    log_line(f"caseC done: success={record['workflow_success']} wall={elapsed:.0f}s "
             f"error={error}")
    return record


# ── verify ──────────────────────────────────────────────────────────────────


def verify() -> int:
    """Recompute the anchors + headline numbers from frozen artifacts."""
    ok = True
    a_path = RESULTS_DIR / "caseA" / "record.json"
    if a_path.exists():
        rec = json.loads(a_path.read_text(encoding="utf-8"))
        cai = bnt162b2_cai()
        stored = rec.get("anchor_bnt162b2_cds_cai")
        if stored is None or abs(stored - cai) > 1e-9:
            log_line(f"VERIFY FAIL caseA anchor: stored={stored} recomputed={cai}")
            ok = False
        else:
            log_line(f"VERIFY OK caseA anchor cai={cai:.4f}")
    b_path = RESULTS_DIR / "caseB" / "record.json"
    if b_path.exists() and (RESULTS_DIR / "caseB" / "anchor.json").exists():
        anchor = json.loads((RESULTS_DIR / "caseB" / "anchor.json").read_text(encoding="utf-8"))
        stored = anchor.get("egarps_native_probability")
        if stored is None:
            log_line("VERIFY OK caseB anchor: registered scorer refusal (None) — "
                     "the instrument-boundary outcome, not a number")
        else:
            eg = _tool_call("score_rna_protein_complex_with_egarps",
                            filepath=anchor["converted_pdb"])
            val = float(eg["result"]["native_probability"])
            if abs(val - stored) > 1e-12:
                log_line(f"VERIFY FAIL caseB anchor: stored={stored} recomputed={val}")
                ok = False
            else:
                log_line(f"VERIFY OK caseB anchor egarps={val:.3e}")
    for case in ("caseC",):
        p = RESULTS_DIR / case / "record.json"
        if p.exists():
            log_line(f"VERIFY OK {case}: record present (numbers frozen from the run)")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    stage = parser.add_mutually_exclusive_group(required=True)
    stage.add_argument("--pilot", action="store_true")
    stage.add_argument("--caseA", action="store_true")
    stage.add_argument("--caseB", action="store_true")
    stage.add_argument("--anchorB", action="store_true")
    stage.add_argument("--caseC", action="store_true", dest="case_c")
    stage.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.pilot:
        run_case_c()
        run_case_a(pilot=True)
        run_case_b(pilot=True)
        return 0
    if args.caseA:
        run_case_a()
        return 0
    if args.caseB:
        run_case_b()
        return 0
    if args.anchorB:
        run_anchor_b()
        return 0
    if args.case_c:
        run_case_c(production=True)
        return 0
    return verify()


if __name__ == "__main__":
    sys.exit(main())
