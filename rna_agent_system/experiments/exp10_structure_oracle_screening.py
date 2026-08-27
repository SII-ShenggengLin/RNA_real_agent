#!/usr/bin/env python3
"""Experiment 10 (paper §2.3 E1, Fig. 3b): structure-oracle screening-power
profile — 3 oracles × 6 aptamer targets, per-cell binder-vs-negative AUROC.

Pre-registration (reset campaign, 2026-08-27; protocol re-registered from the
retained E1 v2 Part-A evidence after the experiment-programme reset)
---------------------------------------------------------------------
* Question: what screening power do the deployed structure oracles actually
  have for RNA–protein aptamers, per target?  Oracles: EGARPS+
  ``native_probability`` (RNA–protein complex scoring), ProteinX ``ipTM``
  (complex interface confidence), RhoFold ``mean pLDDT`` (folding
  confidence).  Targets: the six anchor-set targets (Thrombin, VEGF,
  PDGF-BB, IL-17A, Angiopoietin-2, SARS-CoV-2 N).
* Hypothesis (H1, direction pre-registered): no oracle shows RELIABLE
  screening power across targets — per-cell AUROC > 0.8 passes remain
  absent, or isolated with the 95% CI covering chance (0.5).  A single
  borderline cell with a wide CI is NOT an unlock.  Wording discipline:
  conclusions are phrased as "no oracle shows reliable screening power
  across targets", never as an absolute impossibility claim.
* Anchor set (user-confirmed 2026-08-27 after the target-count review):
  ``data/benchmarks/external_anchors/aptamers/e1_anchor_set_v2.json``
  verbatim — 66 entries, 6 targets, assertion-first curated 2026-08-04;
  per target ≥4 Kd-binders + ≥3 negatives.  No entry is modified.  DNA
  aptamers are scored as RNA via T→U (the anchor set's registered
  convention, identical to the retained evidence's protocol).
* Instrument (zero-intervention rule): the platform's production tool path
  — ``ToolExecutor.run_tool`` through the ``ToolRegistry`` (schema-validated
  LangChain ``.invoke``) — against the deployed microservice instances
  already healthy at run start (rhofold 8005 / proteinx 8022 / egarps 8023;
  service GPU placement inherited from the running deployment and left
  untouched — scores do not depend on device placement).  No threshold
  presets, no parameter sweeps; the only call arguments beyond defaults are
  the protocol's fixed ``num_models=1`` and EGARPS ``academic=False``
  (platform default), i.e.  the retained evidence's exact call semantics.  Per-entry protocol:
  RhoFold structure prediction → ProteinX complex prediction from the
  target-protein fasta + aptamer fasta → gemmi CIF→PDB conversion (the
  registered EGARPS-substrate path; basename guarded against the
  'protein'/'rna' substring hazard) → EGARPS scoring.  Each entry scores in
  its own isolated scratch directory (EGARPS reuses a stale
  ``<basename>_fix.pdb`` if one exists — the pitfall register), wiped
  before any retry of the same entry.
* Protein sources are the anchor set's own: ``benchmark_pdb`` entries use
  the benchmark structure's chain (1HAO:H Thrombin, 1VPF:A VEGF; protein
  sequence extracted from the PDB), ``uniprot_fasta`` entries use the
  generator-sliced mature-chain fastas under
  ``data/benchmarks/external_anchors/aptamers/proteins/``.
* Metrics: per oracle × target (18 cells) screening AUROC (binders =
  role ``binder``/``binder_no_kd``; negatives = role ``negative``) with
  stratified-bootstrap 95% CI (10⁴ resamples, per-cell crc32-fixed seed),
  CI-covers-chance flag, and the pre-registered screening gate AUROC > 0.8
  (analysis-side read-out only — nothing is injected into the platform).
  Secondary (recorded, not figured): ranking Spearman ρ on
  ``ranking_eligible`` binders (oracle score vs −log10 Kd; gate 0.6),
  enrichment EF@top-3 / EF@25%, threshold-sensitivity grids AUROC
  {0.6, 0.7, 0.8, 0.9} and ρ {0.4, 0.5, 0.6, 0.7}.
* CapGate policy: ``RNADA_CAPGATE=advisory`` — the documented regression
  convention (run_pa_test.py, exp1–exp9).  Under the default enforce policy
  these three oracles are SelfModel-governed for aptamer design (all 18
  cells graded failed from the retained evidence this experiment
  re-derives) and the calls would be blocked; advisory lets the profiling
  instrument reach the oracles while every call still lands in the platform
  audit trail.  Gating is a pre-call decision layer and cannot modify tool
  outputs.
* Pilot: 6 entries — ``tba_thrombin``, ``hd22_thrombin``, ``random30_a``,
  ``v7t1_vegf``, ``il17_9cs2``, ``n_tnsp9`` (both protein-source types,
  binder + negative roles, DNA alphabet, length 15–100 nt).  Pilot pass =
  6/6 records with all three oracle scores non-null.  The two ids that
  also exist in the retained ``e1_oracle_scoring_v2.jsonl`` are
  cross-checked informationally (GPU nondeterminism may yield small
  differences; no tolerance gate).
* Budget: one pass over the anchor set (66 entries, ~2.5–3 min each,
  ≈ 3 h wall); ``--resume`` skips entries with a successful record on disk.
  No arm comparison — per-entry compute is fixed by the anchor set.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp10_structure_oracle_screening.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp10_structure_oracle_screening.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp10_structure_oracle_screening.py --summary

Outputs under ``experiments/results/exp10_structure_oracle_screening/``:
    pilot.jsonl, records.jsonl, summary.json, scratch/<mode>/<entry_id>/
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Registered regression convention — set before any agent_core import so the
# lazily-configured CalibratedRuntime picks it up (see docstring).
os.environ.setdefault("RNADA_CAPGATE", "advisory")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANCHOR_JSON = (
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers" / "e1_anchor_set_v2.json"
)
PROTEIN_DIR = ANCHOR_JSON.parent / "proteins"
STRUCT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp10_structure_oracle_screening"
RETAINED_JSONL = PROJECT_ROOT / "experiments" / "results" / "e1_oracle_scoring_v2.jsonl"
RETAINED_SUMMARY = PROJECT_ROOT / "experiments" / "results" / "e1_capability_summary_v2.json"

ORACLES = ["egarps_native_probability", "proteinx_ipTM", "rhofold_mean_plddt"]
ORACLE_LABELS = {
    "egarps_native_probability": "EGARPS native probability",
    "proteinx_ipTM": "ProteinX ipTM",
    "rhofold_mean_plddt": "RhoFold mean pLDDT",
}
TARGETS = ["Thrombin", "VEGF", "PDGF-BB", "IL-17A", "Angiopoietin-2", "SARS-CoV-2 N"]
SCREEN_GATE = 0.8
RANK_GATE = 0.6
AUROC_GRID = [0.6, 0.7, 0.8, 0.9]
RHO_GRID = [0.4, 0.5, 0.6, 0.7]
N_BOOT = 10_000
PILOT_IDS = ["tba_thrombin", "hd22_thrombin", "random30_a", "v7t1_vegf", "il17_9cs2", "n_tnsp9"]

AA3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q",
    "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V",
}


# ── input preparation (legacy protocol helpers, re-implemented verbatim) ─────

def dna_to_rna(seq: str) -> str:
    """RNA alphabet form of a nucleic-acid sequence (anchor-set convention)."""
    return "".join(seq.split()).upper().replace("T", "U")


def find_structure(pdb_id: str) -> Path | None:
    """Locate a benchmark structure (case-tolerant) under structures/."""
    for pat in (f"{pdb_id.lower()}*.pdb", f"{pdb_id.upper()}*.pdb", f"*{pdb_id.lower()}*"):
        for cand in STRUCT_DIR.glob(pat):
            return cand
    return None


def extract_protein_sequence(pdb_path: Path, chain_id: str | None) -> tuple[str, str]:
    """Protein sequence of a PDB chain; falls back to the first protein-like
    chain when the requested chain yields no standard residues (legacy
    semantics — first model only, standard residues only)."""
    from Bio.PDB import PDBParser

    structure = PDBParser(QUIET=True).get_structure("prot", str(pdb_path))
    chains: list[tuple[str, str]] = []
    for model in structure:
        for chain in model:
            seq = "".join(
                AA3_TO_1[r.resname.strip().upper()]
                for r in chain
                if not r.id[0].strip() and r.resname.strip().upper() in AA3_TO_1
            )
            chains.append((chain.id, seq))
        break
    if not chains:
        return "", ""
    if chain_id:
        for cid, seq in chains:
            if cid == chain_id and seq:
                return seq, f"chain:{cid}"
    for cid, seq in chains:
        if seq:
            return seq, f"chain:{cid}"
    return "", ""


def protein_input_for(entry: dict) -> tuple[str, str, str]:
    """(protein sequence, source label, error) for an anchor entry."""
    prot = entry["protein"]
    if prot["type"] == "benchmark_pdb":
        struct = find_structure(prot["pdb_id"])
        if struct is None:
            return "", "", f"no structure for {prot['pdb_id']}"
        seq, src = extract_protein_sequence(struct, prot.get("chain"))
        label = f"pdb:{prot['pdb_id']}|{src}" if src else f"pdb:{prot['pdb_id']}"
        return seq, label, ""
    fa = ANCHOR_JSON.parent / prot["fasta"]
    seq = "".join(l for l in fa.read_text().splitlines() if not l.startswith(">"))
    return seq, f"uniprot:{prot['uniprot']}:{prot['range']}", ""


def px_cif_to_pdb(cif_path: Path, out_pdb: Path) -> Path:
    """Gemmi CIF→PDB copy of the ProteinX complex for the EGARPS substrate.

    Basename must avoid the substrings 'protein'/'rna' (EGARPS feature-path
    typing hazard) and the copy gives EGARPS's cache derivation a real
    ``.pdb`` to key on (pitfall register, 2026-07-27).
    """
    import gemmi

    safe = out_pdb.stem.replace("protein", "px").replace("rna", "x")
    out_pdb = out_pdb.with_name(f"{safe}_px.pdb")
    gemmi.read_structure(str(cif_path)).write_pdb(str(out_pdb))
    return out_pdb


# ── scoring chain (platform production path) ─────────────────────────────────

def build_executor():
    from agent_core.calibrated.runtime import runtime_from_env
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    # AgentRunner's own startup step: configures the CalibratedRuntime from
    # RNADA_CAPGATE so every tool call lands in the platform audit trail
    # (advisory reviews, never blocks — see docstring).
    runtime_from_env()
    return ToolExecutor(build_default_tool_registry())


def run_tool(executor, name: str, **kwargs) -> dict:
    res = executor.run_tool(name, **kwargs)
    if not res.success:
        raise RuntimeError(f"{name} failed: {res.error}")
    raw = res.artifacts.get("result")
    if not isinstance(raw, dict):
        raise RuntimeError(f"{name} returned no result dict")
    return raw


def score_entry(entry: dict, executor, scratch_root: Path, timeout: int) -> dict:
    started = time.monotonic()
    name = entry["id"]
    raw = {o: None for o in ORACLES}
    steps: dict[str, str] = {}

    entry_dir = scratch_root / name
    if entry_dir.exists():
        shutil.rmtree(entry_dir)  # EGARPS stale <basename>_fix.pdb pitfall
    entry_dir.mkdir(parents=True)

    protein_seq, protein_src, err = protein_input_for(entry)
    if err or not protein_seq:
        return _record(entry, False, err or "no protein sequence", steps, raw,
                       protein_src, started)

    rna_seq = dna_to_rna(entry["sequence"])
    rna_fa = entry_dir / "aptamer.fa"
    protein_fa = entry_dir / "target.fa"
    rna_fa.write_text(f">{name}\n{rna_seq}\n", encoding="utf-8")
    protein_fa.write_text(f">{name}_target\n{protein_seq}\n", encoding="utf-8")
    rel = lambda p: str(p.relative_to(PROJECT_ROOT))  # noqa: E731

    try:
        rh = run_tool(executor, "predict_rna_tertiary_structure_with_rhofold",
                      filepath=rel(rna_fa))
        raw["rhofold_mean_plddt"] = rh.get("mean_plddt")
        steps["rhofold"] = "ok"
    except Exception as exc:  # noqa: BLE001
        steps["rhofold"] = f"failed: {exc}"
        return _record(entry, False, steps["rhofold"], steps, raw, protein_src, started)

    try:
        px = run_tool(executor, "predict_rna_protein_complex_with_proteinx",
                      protein_filepath=rel(protein_fa), rna_filepath=rel(rna_fa),
                      num_models=1, timeout_seconds=int(max(timeout, 600)))
        raw["proteinx_ipTM"] = px.get("ipTM")
        px_pdb = px.get("pdb_filepath") or None
        steps["proteinx_complex"] = "ok"
    except Exception as exc:  # noqa: BLE001
        steps["proteinx_complex"] = f"failed: {exc}"
        return _record(entry, False, steps["proteinx_complex"], steps, raw, protein_src, started)

    egarps_input = None
    if px_pdb:
        try:
            cif = Path(px_pdb)
            if not cif.is_absolute():
                cif = PROJECT_ROOT / cif
            egarps_input = px_cif_to_pdb(cif, entry_dir / f"{name}_complex.pdb")
            steps["cif_to_pdb"] = "ok"
        except Exception as exc:  # noqa: BLE001
            steps["cif_to_pdb"] = f"failed: {exc}"

    if egarps_input is None:
        return _record(entry, False, "no ProteinX complex artifact", steps, raw,
                       protein_src, started)
    try:
        eg = run_tool(executor, "score_rna_protein_complex_with_egarps",
                      filepath=rel(egarps_input), academic=False)
        raw["egarps_native_probability"] = eg.get("native_probability")
        steps["egarps"] = "ok"
    except Exception as exc:  # noqa: BLE001
        steps["egarps"] = f"failed: {exc}"

    ok = raw["egarps_native_probability"] is not None
    return _record(entry, ok, None if ok else "egarps chain incomplete", steps, raw,
                   protein_src, started)


def _record(entry, success, error, steps, raw, protein_src, started) -> dict:
    return {
        "id": entry["id"],
        "target": entry["target"],
        "role": entry["role"],
        "kd_nm": entry.get("kd_nm"),
        "ranking_eligible": bool(entry.get("ranking_eligible", False)),
        "length_nt": entry["length_nt"],
        "alphabet": entry["alphabet"],
        "success": bool(success),
        "error": error,
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "steps": steps,
        "raw": raw,
        "protein_src": protein_src,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── statistics ────────────────────────────────────────────────────────────────

def auroc(pos, neg) -> float:
    """AUROC via midrank Mann–Whitney U (tie-corrected)."""
    pos = np.asarray(pos, dtype=float)
    neg = np.asarray(neg, dtype=float)
    allv = np.concatenate([pos, neg])
    order = np.argsort(allv, kind="mergesort")
    sv = allv[order]
    ranks = np.arange(1.0, len(sv) + 1.0)
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2.0 + 1.0
        i = j + 1
    r = np.empty(len(sv))
    r[order] = ranks
    u = r[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2.0
    return float(u / (len(pos) * len(neg)))


def auroc_ci(pos, neg, seed: int, n_boot: int = N_BOOT) -> tuple[float, float]:
    """Stratified bootstrap percentile 95% CI (binders and negatives resampled
    separately with replacement)."""
    rng = np.random.default_rng(seed)
    pos = np.asarray(pos, dtype=float)
    neg = np.asarray(neg, dtype=float)
    vals = np.empty(n_boot)
    for b in range(n_boot):
        p = rng.choice(pos, size=len(pos), replace=True)
        q = rng.choice(neg, size=len(neg), replace=True)
        vals[b] = auroc(p, q)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def cell_seed(oracle: str, target: str) -> int:
    return zlib.crc32(f"{oracle}|{target}".encode()) % (2**31)


def ef_at_k(entries_scores: list[tuple[float, bool]], k: int) -> float | None:
    """Enrichment factor: (binder fraction among top-k by oracle score) /
    (binder base rate)."""
    if k < 1:
        return None
    ranked = sorted(entries_scores, key=lambda t: -t[0])
    base = sum(1 for _, b in ranked if b) / len(ranked)
    if base == 0:
        return None
    top = ranked[:k]
    frac = sum(1 for _, b in top if b) / len(top)
    return float(frac / base)


# ── analysis ─────────────────────────────────────────────────────────────────

def analyze(records: list[dict], mode_label: str) -> dict:
    from scipy.stats import spearmanr

    ok = [r for r in records if r["success"]]
    cells: dict[str, dict] = {}
    for target in TARGETS:
        tgt = [r for r in ok if r["target"] == target]
        binders = [r for r in tgt if r["role"] in ("binder", "binder_no_kd")]
        negatives = [r for r in tgt if r["role"] == "negative"]
        rank_elig = [r for r in binders if r["ranking_eligible"] and r["kd_nm"]]
        for oracle in ORACLES:
            pos = [r["raw"][oracle] for r in binders if r["raw"][oracle] is not None]
            neg = [r["raw"][oracle] for r in negatives if r["raw"][oracle] is not None]
            cell: dict = {
                "n_binder": len(binders), "n_negative": len(negatives),
                "n_scored_pos": len(pos), "n_scored_neg": len(neg),
            }
            if pos and neg:
                a = auroc(pos, neg)
                lo, hi = auroc_ci(pos, neg, cell_seed(oracle, target))
                cell.update({
                    "auroc": round(a, 4),
                    "auroc_ci95": [round(lo, 4), round(hi, 4)],
                    "ci_covers_chance": bool(lo <= 0.5 <= hi),
                    "screening_pass": bool(a > SCREEN_GATE),
                    "screening_pass_grid": {str(g): bool(a > g) for g in AUROC_GRID},
                })
            if rank_elig:
                xs = [r["raw"][oracle] for r in rank_elig if r["raw"][oracle] is not None]
                ys = [-np.log10(r["kd_nm"]) for r in rank_elig if r["raw"][oracle] is not None]
                if len(xs) >= 3:
                    rho, _ = spearmanr(xs, ys)
                    cell.update({
                        "n_ranking_eligible": len(xs),
                        "ranking_spearman_rho": round(float(rho), 4),
                        "ranking_pass": bool(rho >= RANK_GATE),
                        "ranking_pass_grid": {str(g): bool(rho >= g) for g in RHO_GRID},
                    })
            all_scores = [(r["raw"][oracle], r["role"] != "negative") for r in tgt
                          if r["raw"][oracle] is not None]
            if all_scores:
                n = len(all_scores)
                cell["ef_top3"] = ef_at_k(all_scores, min(3, n))
                cell["ef_25pct"] = ef_at_k(all_scores, max(1, int(round(0.25 * n))))
            cells[f"{oracle} | {target}"] = cell

    n_cells = sum(1 for c in cells.values() if "auroc" in c)
    n_pass = sum(1 for c in cells.values() if c.get("screening_pass"))
    n_rank_cells = sum(1 for c in cells.values() if "ranking_spearman_rho" in c)
    n_rank_pass = sum(1 for c in cells.values() if c.get("ranking_pass"))
    grid_counts = {str(g): sum(1 for c in cells.values() if c.get("screening_pass_grid", {}).get(str(g)))
                   for g in AUROC_GRID}
    small_n_rank_pass = [f"{k} (n={c['n_ranking_eligible']})"
                         for k, c in cells.items() if c.get("ranking_pass")]

    summary = {
        "analysis": "Exp10 structure-oracle screening-power profile (reset run)",
        "mode": mode_label,
        "anchor_set": {
            "path": str(ANCHOR_JSON.relative_to(PROJECT_ROOT)),
            "n_entries": len(records),
            "targets": TARGETS,
            "convention": "DNA aptamers scored as RNA via T->U (anchor-set convention)",
        },
        "conventions": {
            "instrument": "ToolExecutor.run_tool (ToolRegistry, schema-validated .invoke) -> deployed microservices as shipped",
            "services": {"rhofold": 8005, "proteinx": 8022, "egarps": 8023},
            "gpu_map": "deployed instances as running at start (placement inherited, untouched — zero intervention)",
            "capgate_policy": os.environ.get("RNADA_CAPGATE", "enforce"),
            "zero_intervention": "anchor entries verbatim; no threshold presets; fixed protocol args only (num_models=1, academic=False)",
            "screening_gate": SCREEN_GATE,
            "ranking_gate": RANK_GATE,
            "bootstrap": f"stratified percentile 95% CI, {N_BOOT} resamples, per-cell crc32 seed",
        },
        "n_records": len(records),
        "n_success": len(ok),
        "n_failed": len(records) - len(ok),
        "failed_ids": [r["id"] for r in records if not r["success"]],
        "cells": cells,
        "decision_bits": [
            f"cells with measured AUROC: {n_cells}/18; screening pass (AUROC>{SCREEN_GATE}): {n_pass}",
            f"threshold sensitivity (cells passing AUROC>g): {grid_counts}",
            f"ranking cells (rho>={RANK_GATE}, ranking-eligible subsets): {n_rank_pass}/{n_rank_cells}"
            + (f" — passing cells are small-n subsets {small_n_rank_pass}; descriptive only "
               "(n too small for p values, pre-registered)" if small_n_rank_pass else ""),
        ],
        "wording_discipline": "conclusions phrased as 'no oracle shows reliable screening power across targets'",
    }

    if RETAINED_SUMMARY.exists():
        legacy = json.loads(RETAINED_SUMMARY.read_text())
        comp = {}
        for key, cell in cells.items():
            if "auroc" in cell and key in legacy.get("part_a_per_oracle_target", {}):
                comp[key] = {
                    "retained_auroc": legacy["part_a_per_oracle_target"][key].get("screening_auroc"),
                    "new_auroc": cell["auroc"],
                    "delta": round(cell["auroc"] - legacy["part_a_per_oracle_target"][key]["screening_auroc"], 4),
                }
        summary["comparison_vs_retained"] = comp
    return summary


def load_done(out: Path) -> set[str]:
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("success"):
                done.add(r["id"])
    return done


def run_mode(mode: str, entries: list[dict], timeout: int, resume: bool) -> int:
    out = RESULTS_DIR / f"{mode}.jsonl"
    scratch = RESULTS_DIR / "scratch" / mode
    done = load_done(out) if resume else set()
    if not resume and out.exists():
        out.unlink()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    executor = build_executor()
    todo = [e for e in entries if e["id"] not in done]
    print(f"[{mode}] {len(todo)} to score ({len(done)} already done)", flush=True)
    with out.open("a", encoding="utf-8") as fh:
        for i, entry in enumerate(todo, 1):
            rec = score_entry(entry, executor, scratch, timeout)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{mode}] {i}/{len(todo)} {entry['id']} ok={rec['success']} "
                  f"{rec['elapsed_seconds']}s", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true", help="score the 6-entry pilot subset")
    mode.add_argument("--run", action="store_true", help="score the full 66-entry anchor set")
    mode.add_argument("--summary", action="store_true", help="write summary.json")
    parser.add_argument("--resume", action="store_true",
                        help="skip entries with a successful record on disk")
    parser.add_argument("--timeout", type=int, default=1800,
                        help="per-entry protocol timeout ceiling (s)")
    args = parser.parse_args()

    anchor = json.loads(ANCHOR_JSON.read_text())
    assert anchor["n_entries"] == len(anchor["entries"]), "anchor n_entries assertion"
    entries = anchor["entries"]

    if args.pilot:
        subset = [e for e in entries if e["id"] in PILOT_IDS]
        assert len(subset) == len(PILOT_IDS), "pilot ids missing from anchor set"
        return run_mode("pilot", subset, args.timeout, args.resume)
    if args.run:
        return run_mode("records", entries, args.timeout, args.resume)
    if args.summary:
        recs = []
        for name in ("records",):
            p = RESULTS_DIR / f"{name}.jsonl"
            if p.exists():
                recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        if not recs:
            print("no records.jsonl — run --run first", file=sys.stderr)
            return 1
        summary = analyze(recs, "full-run")
        out = RESULTS_DIR / "summary.json"
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print(json.dumps({k: summary[k] for k in ("n_records", "n_success", "n_failed",
                                                  "decision_bits")}, ensure_ascii=False, indent=1))
        print(f"summary -> {out}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
