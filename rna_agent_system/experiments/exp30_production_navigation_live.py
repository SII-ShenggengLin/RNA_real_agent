#!/usr/bin/env python3
"""EXP 30 — 生产导航实跑（Fig 5h：成本-交付帕累托 + 突破阶梯 inset；fourth
programme reset, 2026-09-03, user-directed）.

AMENDMENT 2026-09-05 (user-directed, parallel re-launch of the stopped
campaign): (i) aptamer targets still pending reuse an existing ProteinX fold
of the SAME sequence — preferred source is the CIF referenced by that
target's own earlier exp30 session (resume-equivalent), fallback the latest
complete seed-101 fold on disk (the Exp-29 expanded-sweep folds); the reused
path is passed as ``protein_structure_path`` and echoed in the run record
(``structure_reused``). ProteinX folds are NOT byte-deterministic across
runs, so reuse is a disclosed protocol amendment (skip the fold), not a
byte-identical substitution. (ii) Infrastructure only, no production code
changes: the 8012 ODesign endpoint is fronted by a round-robin proxy over
the six resident replicas (2 per GPU on GPUs 0/1/2) and replicas are
CPU-pinned per GPU group. (iii) ``carry`` mode appends the completed pilot
record (IFN-gamma) to the aptamer-arm runs.jsonl so the arm covers all six
user-confirmed targets.

Live production-navigation campaigns through the USER FORM production entry
(the PA-benchmark path verbatim: one ``cli/form_chat.py`` subprocess per
session, ``--params-file`` JSON inputs, ``RNADA_CAPGATE=advisory``, quality
review ON = the shipped default), on NEW targets outside every re-run
dataset:

  Aptamer arm (6 targets, user-confirmed 2026-09-03) — the anchor-set v3
  ``uniprot_fasta`` targets with zero overlap against the RNA-BioBench-
  Aptamer 20-target pool: Angiopoietin-2, FGF2, IFN-gamma, IL-17A, PDGF-BB,
  Influenza H3N2 (swine) HA.  Form input = protein sequence (the production
  sequence-only path: ProteinX structure prediction -> auto-hotspot ->
  ODesign navigation, the shipped E14 mode, 48-raw cap).  Sequences are the
  SAME on-disk anchor assets behind Figs 3a-d (``external_anchors/aptamers/
  proteins/*.fa``, unmodified since the v3 curation commit 839289c).
  Thrombin / VEGF / SARS-CoV-2 N are excluded (20-pool overlap); ige_fc.fa
  is excluded (on disk but not v3-registered).

  mRNA arm (5 targets, curation list PRESENTED for user confirmation —
  held until confirmed): LEP, CSF3, THPO, PLAT, PTH — human therapeutic
  proteins absent from the FullLength-mRNA 20-target pool and from the
  aptamer sets, length spread 115-562 aa for lattice diversity; sequences
  fetched from UniProt with assertion checks (accession, length) and
  registered in ``curated_mrna_targets.json`` before any run.  Form input =
  protein sequence + ``cai_species=Homo sapiens`` + ``navigation=true``
  (the repaired GenNav-lambda shipped mode, 35-raw cap, Exp-28 navigator).

Per campaign (one form session) the driver records: workflow success, wall
time, LLM calls (quality-review records; navigation itself is zero-LLM),
raw spend vs cap (cap-hit / early-stop), delivered cells (0-3 profiles,
non-degraded deliveries from the ``_gennav_trace``), the full navigation
rounds (the step-line inset: cumulative raw spend vs delivered cells), and
the session workspace path.  ``--verify`` recomputes every stored primitive
from the session workflow_results JSONs byte-identically.

THROTTLING (concurrent with Exp 29, GPU 0 shared): sessions run strictly
sequentially — the production navigation path issues one ODesign request at
a time, so Exp 30 adds at most 1-2 in-flight GPU requests on top of Exp 29's
bounded fleet.

OUTPUTS: ``results/exp30_production_navigation_live/{pilot,aptamer,mrna}/``
(runs.jsonl + summary.json), ``curated_mrna_targets.json``, session
workspaces under ``workspace/sessions/exp30_*``.

Usage:
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp30_production_navigation_live.py pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp30_production_navigation_live.py aptamer
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp30_production_navigation_live.py curate   # mRNA list -> json (no runs)
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp30_production_navigation_live.py mrna      # after user confirms the list
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp30_production_navigation_live.py carry     # pilot record -> aptamer arm
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp30_production_navigation_live.py verify {pilot|aptamer|mrna|all}
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp30_production_navigation_live"
ANCHOR_PROTEINS_DIR = (PROJECT_ROOT / "data" / "benchmarks" / "external_anchors"
                       / "aptamers" / "proteins")
CURATED_MRNA_JSON = RESULTS_DIR / "curated_mrna_targets.json"

# anchor-set v3 uniprot_fasta targets with zero 20-pool overlap
# (fasta name -> display name); the *_full.fa variants carry the full
# unmodified UniProt sequence and are preferred (no truncation ambiguity).
APTAMER_NEW_TARGETS: list[tuple[str, str]] = [
    ("ang2", "Angiopoietin-2"),
    ("fgf2", "FGF2"),
    ("ifng", "IFN-gamma"),
    ("il17a", "IL-17A"),
    ("pdgfbb", "PDGF-BB"),
    ("swine_h3_ha", "Influenza H3N2 HA"),
]

# mRNA curation candidates (user confirmation pending; lengths verified at
# curate time against UniProt REST — the fetched sequence is authoritative)
MRNA_CANDIDATES: list[dict[str, str]] = [
    {"gene": "PTH",  "uniprot": "P01270", "display": "Parathyroid hormone",
     "rationale": "very-short extreme (preproprotein)"},
    {"gene": "LEP",  "uniprot": "P41159", "display": "Leptin",
     "rationale": "short cytokine-class therapeutic"},
    {"gene": "CSF3", "uniprot": "P09905", "display": "G-CSF",
     "rationale": "established biologic (filgrastim class)"},
    {"gene": "THPO", "uniprot": "P40225", "display": "Thrombopoietin",
     "rationale": "mid-length growth factor"},
    {"gene": "PLAT", "uniprot": "P00750", "display": "tPA",
     "rationale": "large serine protease"},
]

PROFILE_KEYS = {
    "rna_aptamer_design": ("compact", "standard", "extended"),
    "mrna_cds_design": ("expression", "stability", "balanced"),
}


def log_line(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def read_anchor_sequence(fasta_key: str) -> str:
    """Full UniProt sequence from the anchor ``<key>_full.fa``."""
    path = ANCHOR_PROTEINS_DIR / f"{fasta_key}_full.fa"
    if not path.is_file():
        path = ANCHOR_PROTEINS_DIR / f"{fasta_key}.fa"
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.startswith(">")]
    return "".join(lines).upper()


# ─────────────────── ProteinX fold reuse (2026-09-05 amendment) ───────────────────

def resolve_reused_structure(fasta_key: str) -> Optional[str]:
    """Existing ProteinX fold of the SAME sequence, or None.

    Preference order (both disclosed in the run record via
    ``structure_reused``): (1) the ref_file CIF referenced by this target's
    own earlier exp30 aptamer session — resume-equivalent, the fold the
    production sequence-only path had already computed for this campaign;
    (2) the latest complete seed-101 fold on disk matching the sequence
    (the Exp-29 expanded-sweep folds live in the same tree).
    """
    import glob as _glob
    import json as _json
    seq = read_anchor_sequence(fasta_key)
    # (1) earlier exp30 sessions whose saved protein fasta matches this
    # target's sequence — take the newest odesign input's ref_file
    # (resume-equivalent: the fold this campaign's sequence-only path had
    # already computed before the stop)
    ref: Optional[str] = None
    for sess in sorted(PROJECT_ROOT.glob("workspace/sessions/exp30_*")):
        fasta_hits = [
            f for f in sess.glob("protein_*.fasta")
            if "".join(ln.strip() for ln in f.read_text(encoding="utf-8")
                       .splitlines() if not ln.startswith(">")).upper() == seq
        ]
        if not fasta_hits:
            continue
        for inp_path in sorted(sess.glob("odesign_aptamer_input_*.json"),
                               key=lambda p: p.stat().st_mtime):
            try:
                doc = _json.loads(inp_path.read_text(encoding="utf-8"))
                cand = doc[0].get("ref_file", "") if isinstance(doc, list) else ""
            except Exception:  # noqa: BLE001
                continue
            if cand and Path(cand).is_file():
                ref = cand  # keep the newest match
    if ref:
        return ref
    # (2) latest complete fold of the same sequence anywhere in the
    # proteinx service run tree
    best: Optional[tuple[float, str]] = None
    for run_dir in PROJECT_ROOT.glob("workspace/proteinx_service_runs/"
                                     "proteinx_run_*"):
        inp = run_dir / "input.json"
        if not inp.is_file():
            continue
        try:
            body = inp.read_text(encoding="utf-8")
        except OSError:
            continue
        if seq[:60] not in body:
            continue
        for cif in (run_dir / "output" / "proteinx_pred").glob(
                "seed_*/predictions/proteinx_pred_sample_0.cif"):
            conf = cif.with_name("proteinx_pred_summary_confidence_sample_0.json")
            if conf.is_file():
                mtime = cif.stat().st_mtime
                if best is None or mtime > best[0]:
                    best = (mtime, str(cif))
    return best[1] if best else None


# ─────────────────────────── mRNA curation ───────────────────────────

def curate_mrna() -> dict[str, Any]:
    """Fetch the candidate proteins from UniProt REST, assertion-check
    (accession match, standard AA alphabet, expected length class), register
    in curated_mrna_targets.json.  NO runs are started (user confirmation
    gate)."""
    import urllib.request
    doc: dict[str, Any] = {
        "purpose": "Exp 30 mRNA-arm new targets (form-entry navigation campaigns)",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "PRESENTED_FOR_USER_CONFIRMATION",
        "selection_rule": ("human therapeutic proteins absent from the "
                           "FullLength-mRNA 20-target pool, the aptamer "
                           "20-target pool and the aptamer anchor 6; length "
                           "spread for lattice diversity; single UniProt "
                           "isoform; below the LinearDesign memory guard"),
        "targets": [],
    }
    for cand in MRNA_CANDIDATES:
        url = (f"https://rest.uniprot.org/uniprotkb/{cand['uniprot']}.fasta")
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                fasta = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            log_line(f"[curate] FAILED {cand['gene']}: {exc!r}")
            return doc
        seq = "".join(ln.strip() for ln in fasta.splitlines()
                      if not ln.startswith(">")).upper()
        header = fasta.splitlines()[0]
        assert cand["uniprot"] in header, f"accession mismatch: {header}"
        assert set(seq) <= set("ACDEFGHIKLMNPQRSTVWY"), f"alphabet: {cand['gene']}"
        assert 80 <= len(seq) <= 800, f"length out of class: {len(seq)}"
        doc["targets"].append({
            "gene": cand["gene"], "display": cand["display"],
            "uniprot": cand["uniprot"], "protein_sequence": seq,
            "protein_length_aa": len(seq),
            "species_for_codon_optimization": "Homo sapiens",
            "rationale": cand["rationale"],
        })
        log_line(f"[curate] {cand['gene']} {cand['uniprot']}: {len(seq)} aa OK")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CURATED_MRNA_JSON.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log_line(f"[curate] wrote {CURATED_MRNA_JSON} — awaiting user confirmation")
    return doc


# ─────────────────────────── form-entry campaign ───────────────────────────

def run_form_session(workflow: str, params: dict[str, Any], session_id: str
                     ) -> dict[str, Any]:
    """One production form session — the PA path verbatim (subprocess
    ``cli/form_chat.py``, params JSON, CapGate advisory default)."""
    from run_pa_form import run_form_round
    log_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    t0 = time.perf_counter()
    proc = run_form_round(workflow, params, session_id=session_id,
                          turn=1, log_dir=log_dir)
    elapsed = time.perf_counter() - t0
    return {"returncode": proc.returncode, "elapsed_seconds": elapsed,
            "session_id": session_id, "log_dir": str(log_dir)}


def extract_campaign(session_id: str, workflow: str) -> dict[str, Any]:
    """Pull the navigation trace and run facts from the session workspace."""
    sdir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    results = sorted(sdir.glob("workflow_results_*.json"))
    if not results:
        return {"found": False}
    data = json.loads(results[-1].read_text(encoding="utf-8"))
    wb = data.get("state_writeback") or data.get("_state_writeback") or {}
    trace = (data.get("_gennav_trace") or wb.get("_gennav_trace") or {})
    profiles = PROFILE_KEYS[workflow]
    deliveries = trace.get("deliveries") or {}
    cells: dict[str, bool] = {}
    for prof in profiles:
        d = deliveries.get(prof) or {}
        cells[prof] = bool(d) and not d.get("degraded", True)
    # quality-review / LLM usage from the saved result (top-level or
    # writeback keys, as the form path saves them)
    review = (data.get("_quality_review_error")
              or wb.get("_quality_review_error"))
    quality = (data.get("quality_review") or data.get("_quality_report")
               or wb.get("_quality_report"))
    return {
        "found": True,
        "success": data.get("success"),
        "raw_budget": trace.get("raw_budget"),
        "raw_spent": trace.get("raw_spent"),
        "rounds": trace.get("rounds"),
        "final_gaps": trace.get("final_gaps"),
        "pool_size": trace.get("pool_size"),
        "probe": trace.get("probe"),
        "delivered_counts": {p: len((deliveries.get(p) or {}).get("candidates") or [])
                             for p in profiles},
        "cells_pass": cells,
        "cells_pass_count": sum(cells.values()),
        "quality_review_present": bool(quality),
        "quality_review_error": review,
        "workflow_results_path": str(results[-1]),
    }


def campaign_record(workflow: str, target_id: str, params: dict[str, Any],
                    stage: str) -> dict[str, Any]:
    """One target's full form campaign + trace extraction."""
    session_id = f"exp30_{stage}_{target_id.lower()}_{time.strftime('%Y%m%d_%H%M%S')}"
    log_line(f"[{stage}:{target_id}] form session {session_id} ...")
    run = run_form_session(workflow, params, session_id)
    extracted = extract_campaign(session_id, workflow)
    rec = {
        "stage": stage,
        "workflow": workflow,
        "target_id": target_id,
        "params": {k: (v if k != "protein_sequence" else f"<{len(v)} aa>")
                   for k, v in params.items()},
        "structure_reused": params.get("protein_structure_path"),
        "session_id": session_id,
        "form_returncode": run["returncode"],
        "elapsed_seconds": round(run["elapsed_seconds"], 1),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    rec.update(extracted)
    if extracted.get("found"):
        budget = extracted.get("raw_budget")
        spent = extracted.get("raw_spent")
        rec["cap_hit"] = (budget is not None and spent is not None
                          and spent >= budget)
        rec["early_stop"] = (budget is not None and spent is not None
                             and spent < budget)
        log_line(f"[{stage}:{target_id}] done rc={run['returncode']} "
                 f"in {run['elapsed_seconds']:.0f}s — spend {spent}/{budget}, "
                 f"cells {extracted.get('cells_pass_count', 0)}/3, "
                 f"cap_hit={rec['cap_hit']}")
    else:
        log_line(f"[{stage}:{target_id}] WARNING: no workflow_results json "
                 f"found in session dir")
    return rec


def run_stage(stage: str, records_path: Path, concurrency: int = 1) -> int:
    if stage == "pilot":
        jobs = [("rna_aptamer_design", "IFN-gamma",
                 {"protein_sequence": read_anchor_sequence("ifng"),
                  "navigation": True})]
    elif stage == "aptamer":
        jobs = []
        for key, display in APTAMER_NEW_TARGETS:
            params: dict[str, Any] = {
                "protein_sequence": read_anchor_sequence(key),
                "navigation": True,
            }
            reused = resolve_reused_structure(key)
            if reused:
                # 2026-09-05 amendment: skip the ProteinX fold by reusing an
                # existing fold of the same sequence (disclosed per record)
                params["protein_structure_path"] = reused
            jobs.append(("rna_aptamer_design", display, params))
    elif stage == "mrna":
        doc = json.loads(CURATED_MRNA_JSON.read_text(encoding="utf-8"))
        assert doc.get("status") == "USER_CONFIRMED", (
            "mRNA target list not user-confirmed yet (curate + confirm first)")
        jobs = [("mrna_cds_design", t["gene"],
                 {"protein_sequence": t["protein_sequence"],
                  "cai_species": t["species_for_codon_optimization"],
                  "navigation": True})
                for t in doc["targets"]]
    else:
        raise ValueError(stage)

    done: set[str] = set()
    if records_path.is_file():
        done = {json.loads(ln)["target_id"]
                for ln in records_path.read_text(encoding="utf-8").splitlines()
                if ln.strip()}
    records_path.parent.mkdir(parents=True, exist_ok=True)
    pending = [(wf, tid, params) for wf, tid, params in jobs
               if tid not in done]
    for _, tid, _ in pending:
        log_line(f"[{stage}] {tid} pending"
                 if pending else f"[{stage}] {tid} already recorded — skip")

    write_lock = __import__("threading").Lock()

    def _one(job: tuple[str, str, dict[str, Any]]) -> None:
        workflow, target_id, params = job
        rec = campaign_record(workflow, target_id, params, stage)
        with write_lock:
            with records_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if concurrency > 1 and len(pending) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            list(pool.map(_one, pending))
    else:
        for job in pending:
            _one(job)
    return summarize(stage, records_path)


def carry_pilot_record() -> int:
    """2026-09-05 amendment: append the completed pilot record (IFN-gamma,
    fresh-fold sequence-only session) to the aptamer-arm runs.jsonl so the
    arm's summary covers all six user-confirmed targets. Idempotent."""
    pilot_path = RESULTS_DIR / "pilot" / "runs.jsonl"
    apt_path = RESULTS_DIR / "aptamer" / "runs.jsonl"
    pilot = [json.loads(ln) for ln
             in pilot_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    apt = [json.loads(ln) for ln
           in apt_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    have = {r["target_id"] for r in apt}
    added = 0
    for rec in pilot:
        if rec.get("target_id") in have:
            continue
        rec = dict(rec)
        rec["stage"] = "aptamer"
        rec["carried_from"] = "pilot"
        apt.append(rec)
        added += 1
        log_line(f"[carry] appended pilot record {rec['target_id']}")
    if added:
        apt_path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in apt),
            encoding="utf-8")
    summarize("aptamer", apt_path)
    return 0


def summarize(stage: str, records_path: Path) -> int:
    records = [json.loads(ln) for ln
               in records_path.read_text(encoding="utf-8").splitlines()
               if ln.strip()]
    found = [r for r in records if r.get("found")]
    summary = {
        "stage": stage,
        "n_campaigns": len(records),
        "n_with_trace": len(found),
        "raw_caps": sorted({r.get("raw_budget") for r in found}),
        "cap_hits": sum(1 for r in found if r.get("cap_hit")),
        "early_stops": sum(1 for r in found if r.get("early_stop")),
        "delivered_cells": {r["target_id"]: r.get("cells_pass_count")
                            for r in found},
        "total_delivered_cells": sum(r.get("cells_pass_count", 0) for r in found),
        "wall_seconds": {r["target_id"]: r.get("elapsed_seconds") for r in records},
        "spend": {r["target_id"]: [r.get("raw_spent"), r.get("raw_budget")]
                  for r in found},
        "budget_violations": sum(1 for r in found
                                 if (r.get("raw_spent") or 0) >
                                 (r.get("raw_budget") or 0)),
    }
    path = records_path.parent / "summary.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    log_line(f"[{stage}] summary: {len(found)}/{len(records)} traces, "
             f"cells {summary['total_delivered_cells']}, "
             f"violations {summary['budget_violations']}")
    return 0


# ─────────────────────────── verify ───────────────────────────

def verify(stage: str) -> int:
    stages = ["pilot", "aptamer", "mrna"] if stage == "all" else [stage]
    mismatches = 0
    for st in stages:
        records_path = RESULTS_DIR / st / "runs.jsonl"
        if not records_path.is_file():
            continue
        records = [json.loads(ln) for ln
                   in records_path.read_text(encoding="utf-8").splitlines()
                   if ln.strip()]
        for rec in records:
            if not rec.get("found"):
                continue
            fresh = extract_campaign(rec["session_id"], rec["workflow"])
            for key in ("raw_spent", "raw_budget", "cells_pass",
                        "cells_pass_count", "delivered_counts",
                        "final_gaps", "pool_size"):
                if json.dumps(fresh.get(key), sort_keys=True) != \
                        json.dumps(rec.get(key), sort_keys=True):
                    mismatches += 1
                    log_line(f"VERIFY MISMATCH {rec['target_id']} {key}")
            budget, spent = rec.get("raw_budget"), rec.get("raw_spent")
            if budget is not None and spent is not None:
                if rec.get("cap_hit") != (spent >= budget):
                    mismatches += 1
                    log_line(f"VERIFY MISMATCH {rec['target_id']} cap_hit")
        if (RESULTS_DIR / st / "summary.json").is_file():
            summarize(st, records_path)
    log_line(f"[verify:{stage}] "
             f"{'BYTE-IDENTICAL' if mismatches == 0 else f'{mismatches} MISMATCHES'}")
    return 0 if mismatches == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["pilot", "aptamer", "curate", "mrna",
                                         "carry", "verify"])
    parser.add_argument("stage", nargs="?", default=None)
    parser.add_argument("--concurrency", type=int, default=1,
                        help="concurrent form sessions (subprocesses); the "
                             "2026-09-04 3-GPU machine supports 2-3")
    args = parser.parse_args()
    if args.mode == "curate":
        curate_mrna()
        return 0
    if args.mode == "carry":
        return carry_pilot_record()
    if args.mode == "verify":
        return verify(args.stage or "all")
    return run_stage(args.mode, RESULTS_DIR / args.mode / "runs.jsonl",
                     concurrency=args.concurrency)


if __name__ == "__main__":
    raise SystemExit(main())
