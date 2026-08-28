#!/usr/bin/env python3
"""Experiment 11 (paper §2.3 E1, Fig. 3c): structure-oracle ranking-power
profile — 3 oracles × 6 aptamer targets, per-cell Spearman ρ of oracle score
against measured Kd on the within-target affinity series.

Pre-registration (reset campaign, 2026-08-27; protocol re-registered from the
retained E1 v2 Part-A evidence after the experiment-programme reset)
---------------------------------------------------------------------
* Question: what ranking power (within-target affinity ordering) do the
  deployed structure oracles actually have for RNA–protein aptamers, per
  target?  Oracles: EGARPS+ ``native_probability`` (RNA–protein complex
  scoring), ProteinX ``ipTM`` (complex interface confidence), RhoFold
  ``mean pLDDT`` (folding confidence).  Targets: the six anchor-set targets
  (Thrombin, VEGF, PDGF-BB, IL-17A, Angiopoietin-2, SARS-CoV-2 N).
* Hypothesis (H1, direction pre-registered): no oracle shows RELIABLE ranking
  power across targets — per-cell Spearman ρ ≥ 0.6 passes are absent, or
  confined to n = 3 subsets whose uncertainty is vacuous (descriptive only).
  A small-n borderline cell is NOT an unlock.  Wording discipline:
  conclusions are phrased as "no oracle shows reliable ranking power across
  targets", never as an absolute impossibility claim.
* Anchor set (user-confirmed 2026-08-27): ``data/benchmarks/external_anchors/
  aptamers/e1_anchor_set_v2.json`` verbatim — 66 entries, 6 targets,
  assertion-first curated 2026-08-04.  Ranking subsets, pre-registered as the
  retained evidence's rule (verified 2026-08-27 by recomputation: the nine
  v2-target cells re-derive from the retained ``e1_oracle_scoring_v2.jsonl``
  with max |Δρ| = 0): per target, entries with role ``binder``/``binder_no_kd``
  that carry a measured ``kd_nm``, gated by the ``ranking_eligible`` flag
  where present — the flag is ABSENT on the pilot-3 targets (Thrombin n=6,
  VEGF n=8, PDGF-BB n=5 — every Kd binder counts) and explicitly False on
  the registered exclusions of the v2 targets (IL-17A Apt21-2 transcribed
  citation → n=6 FP subset; Ang2 cross-assay entries → n=3 SPR subset;
  SARS-CoV-2 N streptavidin/full-length orientation → n=6 BLI subset).
  34 entries total.  Known limitations carried from the anchor set: the
  Thrombin series mixes Kd assay methods (ρ treats Kd as ordinal only);
  PDGF-BB spans one order of magnitude (underpowered); Ang2's same-assay
  subset spans 0.14 orders (ranking decorative).
* ρ convention: Spearman(oracle score, −log10 Kd) — positive ρ means tighter
  binders scored higher; ties by average ranks (scipy); the pre-registered
  ranking gate ρ ≥ 0.6 is an analysis-side read-out only — nothing is
  injected into the platform.
* Instrument (zero-intervention rule, identical to the Exp-10 screening
  run): the platform's production tool path — ``ToolExecutor.run_tool``
  through the ``ToolRegistry`` (schema-validated LangChain ``.invoke``) —
  against the deployed microservice instances already healthy at run start
  (rhofold 8005 / proteinx 8022 / egarps 8023, GPU-pinned 0/1/2 by the
  experiment bring-up script; placement inherited and left untouched).
  No threshold presets, no parameter sweeps; the only call arguments beyond
  defaults are the protocol's fixed ``num_models=1`` and EGARPS
  ``academic=False`` (platform default), i.e. the retained evidence's exact
  call semantics.  Per-entry protocol: RhoFold structure prediction →
  ProteinX complex prediction from the target-protein fasta + aptamer fasta
  → gemmi CIF→PDB conversion (the registered EGARPS-substrate path; basename
  guarded against the 'protein'/'rna' substring hazard) → EGARPS scoring.
  Each entry scores in its own isolated scratch directory (EGARPS reuses a
  stale ``<basename>_fix.pdb`` if one exists — the pitfall register), wiped
  before any retry of the same entry.
* Fresh scoring pass (self-contained figure evidence, the exp5/6/7/10
  pattern): the same 34 ids were also scored by the Exp-10 full-anchor
  screening run — per-entry score deltas against the Exp-10 records are
  recorded as a realization-variance cross-check (RhoFold expected
  bit-identical; ProteinX/EGARPS realization variance expected, as
  disclosed there).
* Protein sources are the anchor set's own: ``benchmark_pdb`` entries use
  the benchmark structure's chain (1HAO:H Thrombin, 1VPF:A VEGF; protein
  sequence extracted from the PDB), ``uniprot_fasta`` entries use the
  generator-sliced mature-chain fastas under ``data/benchmarks/
  external_anchors/aptamers/proteins/``.
* Metrics: per oracle × target (18 cells) Spearman ρ on the affinity subset
  with the pre-registered gate ρ ≥ 0.6 and threshold-sensitivity grid
  ρ ∈ {0.4, 0.5, 0.6, 0.7}; secondary (recorded, not figured): percentile
  bootstrap 95% CI for ρ (10⁴ resamples of the score–affinity pairs,
  per-cell crc32-fixed seed) — descriptive only, the subsets are too small
  for p values.  Comparison tables: per-cell Δρ vs the retained
  ``e1_capability_summary_v2.json`` and per-entry Δscore vs the Exp-10
  records.
* CapGate policy: ``RNADA_CAPGATE=advisory`` — the documented regression
  convention (run_pa_test.py, exp1–exp10).  Under the default enforce
  policy these three oracles are SelfModel-governed for aptamer design (all
  18 cells graded failed from the retained evidence this experiment
  re-derives) and the calls would be blocked; advisory lets the profiling
  instrument reach the oracles while every call still lands in the platform
  audit trail.  Gating is a pre-call decision layer and cannot modify tool
  outputs.
* Pilot: 4 entries — ``tba_thrombin`` (benchmark_pdb protein source, DNA,
  15 nt), ``pdgf36t_pdgfbb`` (uniprot fasta), ``il17_9cs2`` (uniprot fasta,
  ranking-flagged), ``n_tnsp9`` (uniprot fasta, ranking-flagged): both
  protein-source types, flagged and unflagged subsets, DNA alphabet,
  length 15–100 nt.  Pilot pass = 4/4 records with all three oracle scores
  non-null.  The two ids that also exist in the retained
  ``e1_oracle_scoring_v2.jsonl`` are cross-checked informationally (GPU
  nondeterminism may yield small differences; no tolerance gate).
* Budget: one pass over the 34 ranking-subset entries (~2.5–3 min each,
  ≈ 1.5 h wall); ``--resume`` skips entries with a successful record on
  disk.  No arm comparison — per-entry compute is fixed by the anchor set.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp11_oracle_ranking_power.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp11_oracle_ranking_power.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp11_oracle_ranking_power.py --summary

Outputs under ``experiments/results/exp11_oracle_ranking_power/``:
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
ANCHOR_JSON_DEFAULT = (
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers" / "e1_anchor_set_v2.json"
)
# v3 re-run (user-approved 2026-08-28): --anchor-set overrides the registered
# default; pilot defaults unchanged (ANCHORS.md §5.6)
ANCHOR_JSON = ANCHOR_JSON_DEFAULT
if os.environ.get("EXP_ANCHOR_SET"):
    ANCHOR_JSON = Path(os.environ["EXP_ANCHOR_SET"]).resolve()
PROTEIN_DIR = ANCHOR_JSON.parent / "proteins"
STRUCT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp11_oracle_ranking_power"
# v3 re-run: results land in a sibling _v3 directory when the anchor
# set is overridden, so the registered v2-run records are never touched
if ANCHOR_JSON != ANCHOR_JSON_DEFAULT:
    RESULTS_DIR = RESULTS_DIR.with_name(RESULTS_DIR.name + "_v3")
RETAINED_JSONL = PROJECT_ROOT / "experiments" / "results" / "e1_oracle_scoring_v2.jsonl"
RETAINED_SUMMARY = PROJECT_ROOT / "experiments" / "results" / "e1_capability_summary_v2.json"
EXP10_RECORDS = (
    PROJECT_ROOT / "experiments" / "results" / "exp10_structure_oracle_screening" / "records.jsonl"
)
if ANCHOR_JSON != ANCHOR_JSON_DEFAULT:
    EXP10_RECORDS = Path(str(EXP10_RECORDS).replace(
        "exp10_structure_oracle_screening", "exp10_structure_oracle_screening_v3"))

ORACLES = ["egarps_native_probability", "proteinx_ipTM", "rhofold_mean_plddt"]
ORACLE_LABELS = {
    "egarps_native_probability": "EGARPS native probability",
    "proteinx_ipTM": "ProteinX ipTM",
    "rhofold_mean_plddt": "RhoFold mean pLDDT",
}
TARGETS = ["Thrombin", "VEGF", "PDGF-BB", "IL-17A", "Angiopoietin-2", "SARS-CoV-2 N"]
# v3 re-run: target list extended from the anchor set actually loaded
if ANCHOR_JSON != ANCHOR_JSON_DEFAULT:
    _extra = []
    for _e in json.loads(ANCHOR_JSON.read_text())["entries"]:
        if _e["target"] not in TARGETS and _e["target"] not in _extra:
            _extra.append(_e["target"])
    TARGETS = TARGETS + _extra
RANK_GATE = 0.6
RHO_GRID = [0.4, 0.5, 0.6, 0.7]
N_BOOT = 10_000
PILOT_IDS = ["tba_thrombin", "pdgf36t_pdgfbb", "il17_9cs2", "n_tnsp9"]

AA3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q",
    "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V",
}


# ── ranking-subset rule (pre-registered; see docstring) ───────────────────────

def in_ranking_subset(entry: dict) -> bool:
    """The retained evidence's rule: binder with measured Kd, gated by the
    ranking_eligible flag where present (absent flag defaults True — the
    pilot-3 targets carry no flags; explicit False = registered exclusion)."""
    if not entry.get("role", "").startswith("binder"):
        return False
    if entry.get("kd_nm") is None:
        return False
    return bool(entry.get("ranking_eligible", True))


V2_RANKING_N = {"Thrombin": 6, "VEGF": 8, "PDGF-BB": 5, "IL-17A": 6,
                 "Angiopoietin-2": 3, "SARS-CoV-2 N": 6}


def ranking_entries(entries: list[dict]) -> list[dict]:
    sub = [e for e in entries if in_ranking_subset(e)]
    per = {t: sum(1 for e in sub if e["target"] == t) for t in TARGETS}
    # the six v2 targets must reproduce their pre-registered subset counts
    # verbatim (invariance check); v3-added targets record their counts
    for t, n in V2_RANKING_N.items():
        assert per.get(t) == n, (
            f"v2 target {t} ranking-subset count deviates: {per.get(t)} != {n}")
    return sub


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
        "ranking_subset": in_ranking_subset(entry),
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

def cell_seed(oracle: str, target: str) -> int:
    return zlib.crc32(f"{oracle}|{target}".encode()) % (2**31)


def rho_ci(xs, ys, seed: int, n_boot: int = N_BOOT) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for Spearman ρ (resampling score–affinity
    pairs with replacement; descriptive only — subsets are too small for p
    values)."""
    from scipy.stats import spearmanr

    rng = np.random.default_rng(seed)
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(xs), len(xs))
        vals.append(spearmanr(xs[idx], ys[idx])[0])
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


# ── analysis ─────────────────────────────────────────────────────────────────

def analyze(records: list[dict], mode_label: str) -> dict:
    from scipy.stats import spearmanr

    ok = [r for r in records if r["success"]]
    sub = [r for r in ok if r.get("ranking_subset") and r["kd_nm"]]
    cells: dict[str, dict] = {}
    for target in TARGETS:
        tgt = [r for r in sub if r["target"] == target]
        for oracle in ORACLES:
            pairs = [(r["raw"][oracle], -np.log10(r["kd_nm"])) for r in tgt
                     if r["raw"][oracle] is not None]
            cell: dict = {
                "n_affinity_series": len(pairs),
                "kd_span_orders": round(float(np.log10(max(r["kd_nm"] for r in tgt))
                                              - np.log10(min(r["kd_nm"] for r in tgt))), 3)
                if tgt else None,
            }
            if len(pairs) >= 3:
                xs = [p[0] for p in pairs]
                ys = [p[1] for p in pairs]
                rho = float(spearmanr(xs, ys)[0])
                lo, hi = rho_ci(xs, ys, cell_seed(oracle, target))
                cell.update({
                    "ranking_spearman_rho": round(rho, 4),
                    "rho_ci95_descriptive": [round(lo, 4), round(hi, 4)],
                    "ranking_pass": bool(rho >= RANK_GATE),
                    "ranking_pass_grid": {str(g): bool(rho >= g) for g in RHO_GRID},
                })
            cells[f"{oracle} | {target}"] = cell

    n_cells = sum(1 for c in cells.values() if "ranking_spearman_rho" in c)
    n_pass = sum(1 for c in cells.values() if c.get("ranking_pass"))
    grid_counts = {str(g): sum(1 for c in cells.values() if c.get("ranking_pass_grid", {}).get(str(g)))
                   for g in RHO_GRID}
    measured = [(k, c["ranking_spearman_rho"], c["n_affinity_series"])
                for k, c in cells.items() if "ranking_spearman_rho" in c]
    best_key, best_rho, best_n = max(measured, key=lambda t: t[1])
    small_n_pass = [f"{k} (n={c['n_affinity_series']})" for k, c in cells.items() if c.get("ranking_pass")]

    summary = {
        "analysis": "Exp11 structure-oracle ranking-power profile (reset run)",
        "mode": mode_label,
        "anchor_set": {
            "path": str(ANCHOR_JSON.relative_to(PROJECT_ROOT)),
            "n_ranking_subset_entries": len(sub),
            "targets": TARGETS,
            "subset_rule": ("binders with measured kd_nm; ranking_eligible flag "
                            "defaults True when absent, explicit False excluded "
                            "(pre-registered; retained per-target n 6/8/5/6/3/6)"),
            "convention": "DNA aptamers scored as RNA via T->U (anchor-set convention)",
        },
        "conventions": {
            "instrument": "ToolExecutor.run_tool (ToolRegistry, schema-validated .invoke) -> deployed microservices as shipped",
            "services": {"rhofold": 8005, "proteinx": 8022, "egarps": 8023},
            "gpu_map": "deployed instances GPU-pinned 0/1/2 (placement inherited, untouched — zero intervention)",
            "capgate_policy": os.environ.get("RNADA_CAPGATE", "enforce"),
            "zero_intervention": "anchor entries verbatim; no threshold presets; fixed protocol args only (num_models=1, academic=False)",
            "rho": "Spearman(oracle score, -log10 Kd); positive = tighter binder scored higher; average-rank ties",
            "ranking_gate": RANK_GATE,
            "bootstrap": f"percentile 95% CI, {N_BOOT} resamples, per-cell crc32 seed (descriptive)",
        },
        "n_records": len(records),
        "n_success": len(ok),
        "n_failed": len(records) - len(ok),
        "failed_ids": [r["id"] for r in records if not r["success"]],
        "cells": cells,
        "decision_bits": [
            f"cells with measured rho: {n_cells}/{len(cells)}; ranking pass (rho>={RANK_GATE}): {n_pass}"
            + (f" — passing cells are small-n subsets {small_n_pass}; descriptive only "
               "(n too small for p values, pre-registered)" if small_n_pass else ""),
            f"threshold sensitivity (cells passing rho>=g): {grid_counts}",
            f"best cell: {best_key} rho={best_rho:+.4f} (n={best_n})",
        ],
        "wording_discipline": "conclusions phrased as 'no oracle shows reliable ranking power across targets'",
    }

    if RETAINED_SUMMARY.exists():
        legacy = json.loads(RETAINED_SUMMARY.read_text())
        comp = {}
        for key, cell in cells.items():
            if "ranking_spearman_rho" in cell and key in legacy.get("part_a_per_oracle_target", {}):
                lrho = legacy["part_a_per_oracle_target"][key].get("ranking_spearman_rho")
                comp[key] = {
                    "retained_rho": lrho,
                    "new_rho": cell["ranking_spearman_rho"],
                    "delta": round(cell["ranking_spearman_rho"] - lrho, 4),
                    "retained_n": legacy["part_a_per_oracle_target"][key].get("n_ranking_eligible"),
                }
        summary["comparison_vs_retained"] = comp
        if comp:
            identical = sum(1 for v in comp.values() if abs(v["delta"]) < 5e-4)
            summary["decision_bits"].append(
                f"vs retained evidence: {identical}/{len(comp)} ranking cells identical "
                "(|drho| < 5e-4); remainder shifted by ProteinX-complex realization variance")
    if EXP10_RECORDS.exists():
        exp10 = {json.loads(l)["id"]: json.loads(l) for l in EXP10_RECORDS.read_text().splitlines()
                 if l.strip()}
        deltas = {o: [] for o in ORACLES}
        for r in ok:
            e10 = exp10.get(r["id"])
            if not e10 or not e10.get("success"):
                continue
            for o in ORACLES:
                a, b = r["raw"][o], e10["raw"][o]
                if a is not None and b is not None:
                    deltas[o].append(abs(a - b))
        summary["comparison_vs_exp10_scores"] = {
            o: {"n_pairs": len(v),
                "median_abs_delta": round(float(np.median(v)), 6) if v else None,
                "max_abs_delta": round(float(np.max(v)), 6) if v else None}
            for o, v in deltas.items()
        }
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
    mode.add_argument("--pilot", action="store_true", help="score the 4-entry pilot subset")
    mode.add_argument("--run", action="store_true", help="score the full 34-entry ranking subset")
    mode.add_argument("--summary", action="store_true", help="write summary.json")
    parser.add_argument("--resume", action="store_true",
                        help="skip entries with a successful record on disk")
    parser.add_argument("--timeout", type=int, default=1800,
                        help="per-entry protocol timeout ceiling (s)")
    args = parser.parse_args()

    anchor = json.loads(ANCHOR_JSON.read_text())
    assert anchor["n_entries"] == len(anchor["entries"]), "anchor n_entries assertion"
    entries = ranking_entries(anchor["entries"])

    if args.pilot:
        subset = [e for e in entries if e["id"] in PILOT_IDS]
        assert len(subset) == len(PILOT_IDS), "pilot ids missing from ranking subset"
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
