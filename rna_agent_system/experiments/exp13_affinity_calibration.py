#!/usr/bin/env python3
"""Experiment 13 (paper §2.3, Fig. 3e): EGARPS affinity-calibration profile
on the full v3 anchor set — within-target Kd ordering (thrombin series) and
cross-target binder-vs-negative separation (pooled), the retained P2 pilot's
question re-registered at anchor-set scale after the experiment-programme
reset.

PRE-REGISTRATION (reset campaign, 2026-08-28; protocol re-registered from the
retained P2 aptamer-calibration pilot evidence of 2026-08-03, deleted in the
2026-08-25 reset and recovered from git e601913 for the 1:1 reproduction
check; user-confirmed v3 full-set scope the same day)
---------------------------------------------------------------------
* Question: does the deployed complex-scoring oracle (EGARPS+
  ``native_probability``) track measured binding affinity for known
  aptamers, (i) within the thrombin Kd series and (ii) across targets as
  binder-vs-negative separation?  This is the calibration the aptamer
  workflow's ranking implicitly relies on.
* Hypothesis (H1, direction pre-registered): the oracle remains uncalibrated
  — thrombin-series Spearman ρ < 0.6 AND pooled binder-vs-negative AUROC
  fails to exceed 0.8 (the retained P2 gates); the retained direction
  inversion (binders scoring below negatives on average, the marketed
  pegaptanib near 2e-6 vs random 30-mers near 0.95) is expected to
  reproduce in class.  Wording discipline: conclusions are phrased as "no
  validated affinity calibration for RNA-protein aptamers" and "directionally
  inverted on this panel" — descriptive, never an absolute impossibility
  claim.
* Anchor set (user-confirmed 2026-08-28, the Fig-3b/c/d v3 data source):
  ``data/benchmarks/external_anchors/aptamers/e1_anchor_set_v3.json``
  verbatim — 95 entries / 9 targets (62 Kd binders + 5 binder_no_kd + 28
  negatives); assertion-first curated, deterministic generator.  No entry is
  modified; DNA aptamers are scored as RNA via T→U (the registered
  convention, identical to exp10–exp12).
* Legacy-P2 mapping (1:1 reproduction check): 12 of the retained pilot's 15
  ids live in v3 byte-consistent (same id, same Kd, same role); the IgE pair
  (d17_4_ige, random37_a) and the legacy sarsn_aptamer were dropped/re-curated
  during anchor-set evolution — disclosed, and the 1:1 statistics are
  therefore recomputed on the shared-12 submatrix (7 binders vs 4 negatives
  for the pooled AUROC; the 4-point thrombin series is fully shared and
  recomputes exactly).  The retained pilot's 15-record scores are embedded
  below as LEGACY_P2 (recovered from git e601913; the file itself was deleted
  in the 2026-08-25 reset).
* Instrument (zero-intervention rule, identical to the Exp-10/11 runs): the
  platform's production tool path — ``ToolExecutor.run_tool`` through the
  ``ToolRegistry`` (schema-validated LangChain ``.invoke``) — against the
  deployed microservice instances already healthy at run start (rhofold 8005
  / proteinx 8022 / egarps 8023, GPU-pinned 0/1/2 by the experiment bring-up
  script; placement inherited and left untouched).  No threshold presets, no
  parameter sweeps; the only call arguments beyond defaults are the
  protocol's fixed ``num_models=1`` and EGARPS ``academic=False`` (platform
  default), i.e. the retained evidence's exact call semantics.  Per-entry
  protocol: RhoFold structure prediction → ProteinX complex prediction from
  the target-protein fasta + aptamer fasta → gemmi CIF→PDB conversion (the
  registered EGARPS-substrate path; basename guarded against the
  'protein'/'rna' substring hazard) → EGARPS scoring.  Each entry scores in
  its own isolated scratch directory (EGARPS reuses a stale
  ``<basename>_fix.pdb`` if one exists — the pitfall register), wiped before
  any retry of the same entry.
* Protein sources are the anchor set's own: ``benchmark_pdb`` entries use
  the benchmark structure's chain (1HAO:H Thrombin, 1VPF:A VEGF; protein
  sequence extracted from the PDB), ``uniprot_fasta`` entries use the
  generator-sliced mature-chain fastas under ``data/benchmarks/
  external_anchors/aptamers/proteins/``.
* Metrics (all analysis-side read-outs — nothing is injected into the
  platform):
  (1) Thrombin Kd series (6 points, 0.33–25 nM): Spearman(np, −log10 Kd),
      pre-registered gate ρ ≥ 0.6; percentile bootstrap 95% CI (10⁴
      resamples, crc32-fixed seed; descriptive — n too small for p values).
      Sub-analysis: the retained 4-point series recomputed 1:1.
  (2) Pooled binder-vs-negative AUROC (the retained P2 convention: pos =
      role ``binder`` with measured Kd, n = 62; neg = role ``negative``,
      n = 28 — cross-target pooled, matching the pilot's framing):
      tie-corrected midrank AUROC, stratified bootstrap 95% CI (10⁴,
      crc32-fixed seed), gate AUROC ≥ 0.8.  Secondary (recorded, not
      figured): the all-binders variant (role binder + binder_no_kd, n = 67)
      and the same two statistics for ProteinX ipTM / RhoFold mean pLDDT.
  (3) Extreme contrast (the retained inversion detail): pegaptanib np vs
      the random-sequence negative class and scrambled TBA; per-group np
      medians and the binder/negative median ratio.
  (4) Ridgeline groups for Fig. 3e (pre-registered split rule): binders
      (67 = 62 Kd + 5 no-Kd) / literature negatives (11 — experimentally
      characterized non-binders and composition-matched scrambles) /
      random-sequence negatives (17 — the anchor set's in-silico fixed-seed
      random class; ``'rand' in id`` over role ``negative``, asserted to
      partition 28 = 11 + 17).
  (5) Legacy-P2 1:1 reproduction: per-entry |Δnp| on the shared-12 ids;
      thrombin 4-point ρ new vs retained (0.39999999999999997); pooled AUROC
      new vs retained recomputed on the same shared 7-vs-4 submatrix (the
      retained full-matrix 0.3556 on 9-vs-5 is quoted as context).
  (6) Cross-check vs the Exp-10 v3 records (same 95 ids scored by the
      screening run): per-entry per-oracle |Δscore| medians — the
      realization-variance disclosure of exp10/exp11.
* CapGate policy: ``RNADA_CAPGATE=advisory`` — the documented regression
  convention (run_pa_test.py, exp1–exp12).  Under the default enforce policy
  the three oracles are SelfModel-governed for aptamer design (graded failed
  from the retained evidence this campaign re-derives) and the calls would
  be blocked; advisory lets the profiling instrument reach the oracles while
  every call still lands in the platform audit trail (the driver activates
  the audit runtime via ``runtime_from_env()``).  Gating is a pre-call
  decision layer and cannot modify tool outputs.
* Pilot: 6 entries — ``tba_thrombin``, ``hd22_thrombin``, ``random30_a``,
  ``v7t1_vegf``, ``il17_9cs2``, ``n_tnsp9`` (the exp10 pilot subset: both
  protein-source types, binder + negative roles, DNA alphabet, length
  15–100 nt).  Pilot pass = 6/6 records with all three oracle scores
  non-null.  The four ids that also exist in the retained P2 pilot records
  are cross-checked informationally (GPU nondeterminism may yield small
  differences; no tolerance gate).
* Budget: one pass over the anchor set (95 entries, ~2.5–3 min each,
  ≈ 4–4.5 h wall); ``--resume`` skips entries with a successful record on
  disk.  No arm comparison — per-entry compute is fixed by the anchor set.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp13_affinity_calibration.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp13_affinity_calibration.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp13_affinity_calibration.py --summary

Outputs under ``experiments/results/exp13_affinity_calibration/``:
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
    PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers" / "e1_anchor_set_v3.json"
)
PROTEIN_DIR = ANCHOR_JSON.parent / "proteins"
STRUCT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp13_affinity_calibration"
EXP10_V3_RECORDS = (
    PROJECT_ROOT / "experiments" / "results" / "exp10_structure_oracle_screening_v3" / "records.jsonl"
)

ORACLES = ["egarps_native_probability", "proteinx_ipTM", "rhofold_mean_plddt"]
ORACLE_LABELS = {
    "egarps_native_probability": "EGARPS native probability",
    "proteinx_ipTM": "ProteinX ipTM",
    "rhofold_mean_plddt": "RhoFold mean pLDDT",
}
PRIMARY_ORACLE = "egarps_native_probability"
RANK_GATE = 0.6          # retained P2 pre-registration
AUROC_GATE = 0.8         # retained P2 pre-registration
N_BOOT = 10_000
PILOT_IDS = ["tba_thrombin", "hd22_thrombin", "random30_a", "v7t1_vegf", "il17_9cs2", "n_tnsp9"]
LEGACY_THROMBIN_4PT = ["hd22_thrombin", "toggle25t_thrombin", "hd22_t27_thrombin", "tba_thrombin"]
LEGACY_THROMBIN_4PT_RHO = 0.39999999999999997
LEGACY_FULL_AUROC = 0.35555555555555557   # 9 binders vs 5 negatives (retained P2)
EXPECTED_V3 = {
    "n_entries": 95, "n_binder_kd": 62, "n_binder_no_kd": 5, "n_negative": 28,
    "n_negative_random": 17, "n_negative_literature": 11,
}

# Retained P2 pilot records (2026-08-03), recovered from git e601913 after the
# 2026-08-25 reset deleted the evidence files — the 1:1 reproduction reference.
LEGACY_P2: dict[str, dict] = {
    "hd22_thrombin":     {"target": "Thrombin", "role": "binder", "kd_nm": 0.5,
                          "np": 0.24883497, "ipTM": 0.3707660138607025, "plddt": 48.55255555555562},
    "hd22_t27_thrombin": {"target": "Thrombin", "role": "binder", "kd_nm": 0.7,
                          "np": 0.8832092, "ipTM": 0.3104698657989502, "plddt": 39.166071428571534},
    "toggle25t_thrombin": {"target": "Thrombin", "role": "binder", "kd_nm": 0.54,
                           "np": 0.0042375694, "ipTM": 0.29740023612996074, "plddt": 76.66557835820933},
    "tba_thrombin":      {"target": "Thrombin", "role": "binder", "kd_nm": 25.0,
                          "np": 0.0008617156, "ipTM": 0.23769190907478333, "plddt": 52.387981651375945},
    "nu172_thrombin":    {"target": "Thrombin", "role": "binder_no_kd", "kd_nm": None,
                          "np": 0.99915123, "ipTM": 0.31943222880363464, "plddt": 68.61464664310961},
    "pegaptanib_vegf":   {"target": "VEGF", "role": "binder", "kd_nm": 0.049,
                          "np": 1.9145918e-06, "ipTM": 0.4191020727157593, "plddt": 41.95665505226491},
    "pdgf36t_pdgfbb":    {"target": "PDGF-BB", "role": "binder", "kd_nm": 0.094,
                          "np": 1.5003673e-08, "ipTM": 0.5326549410820007, "plddt": 55.22371764705836},
    "pdgf41t_pdgfbb":    {"target": "PDGF-BB", "role": "binder", "kd_nm": 0.1,
                          "np": 1.0413441e-07, "ipTM": 0.6216961145401001, "plddt": 71.15531737773165},
    "d17_4_ige":         {"target": "IgE", "role": "binder", "kd_nm": 10.0,
                          "np": 0.0011727829, "ipTM": 0.22067779302597046, "plddt": 76.90902439024397},
    "sarsn_aptamer":     {"target": "SARS-CoV-2_Nucleocapsid", "role": "binder", "kd_nm": 15.2,
                          "np": 0.00030784257, "ipTM": 0.3439827561378479, "plddt": 54.417835990888385},
    "scrambled_tba":     {"target": "Thrombin", "role": "negative", "kd_nm": None,
                          "np": 0.9868873, "ipTM": 0.21956339478492737, "plddt": 60.236574923547444},
    "random30_a":        {"target": "Thrombin", "role": "negative", "kd_nm": None,
                          "np": 0.95213646, "ipTM": 0.3633504807949066, "plddt": 53.77088748019038},
    "random30_b":        {"target": "PDGF-BB", "role": "negative", "kd_nm": None,
                          "np": 7.9934637e-07, "ipTM": 0.43194878101348877, "plddt": 47.60844827586236},
    "random45_a":        {"target": "PDGF-BB", "role": "negative", "kd_nm": None,
                          "np": 2.4767326e-08, "ipTM": 0.3604114055633545, "plddt": 46.12236479321296},
    "random37_a":        {"target": "IgE", "role": "negative", "kd_nm": None,
                          "np": 0.54285866, "ipTM": 0.2716248631477356, "plddt": 46.8195483061481},
}

AA3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q",
    "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V",
}


# ── anchor-set loading with pre-registered composition assertions ────────────

def is_random_negative(entry: dict) -> bool:
    """Ridgeline split rule: negatives carrying the anchor set's in-silico
    fixed-seed random-sequence marker ('rand' in the entry id)."""
    return entry["role"] == "negative" and "rand" in entry["id"]


def load_anchor() -> dict:
    anchor = json.loads(ANCHOR_JSON.read_text())
    entries = anchor["entries"]
    assert anchor["n_entries"] == len(entries) == EXPECTED_V3["n_entries"], \
        f"anchor n_entries assertion: {len(entries)} != {EXPECTED_V3['n_entries']}"
    assert len({e["id"] for e in entries}) == len(entries), "anchor id uniqueness"
    n_binder_kd = sum(1 for e in entries if e["role"] == "binder")
    n_binder_no_kd = sum(1 for e in entries if e["role"] == "binder_no_kd")
    n_negative = sum(1 for e in entries if e["role"] == "negative")
    n_rand = sum(1 for e in entries if is_random_negative(e))
    assert n_binder_kd == EXPECTED_V3["n_binder_kd"], f"binder count {n_binder_kd}"
    assert n_binder_no_kd == EXPECTED_V3["n_binder_no_kd"], f"binder_no_kd count {n_binder_no_kd}"
    assert n_negative == EXPECTED_V3["n_negative"], f"negative count {n_negative}"
    assert n_rand == EXPECTED_V3["n_negative_random"], f"random-negative count {n_rand}"
    assert n_negative - n_rand == EXPECTED_V3["n_negative_literature"], "literature-negative count"
    shared = [i for i in LEGACY_P2 if i in {e["id"] for e in entries}]
    assert len(shared) == 12, f"legacy shared-12 assertion: {len(shared)}"
    for e in entries:  # legacy-shared ids carry identical Kd/role (byte-consistency)
        if e["id"] in LEGACY_P2:
            leg = LEGACY_P2[e["id"]]
            assert e["role"] == leg["role"], f"role drift on {e['id']}"
            assert e.get("kd_nm") == leg["kd_nm"], f"kd drift on {e['id']}"
    return anchor


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
        "random_negative": is_random_negative(entry),
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


def rho_ci(xs, ys, seed: int, n_boot: int = N_BOOT) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for Spearman ρ (descriptive — the series
    is too small for p values)."""
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


def seed_of(label: str) -> int:
    return zlib.crc32(label.encode()) % (2**31)


# ── analysis ─────────────────────────────────────────────────────────────────

def analyze(records: list[dict], mode_label: str) -> dict:
    from scipy.stats import spearmanr

    ok = [r for r in records if r["success"]]
    by_id = {r["id"]: r for r in ok}
    np_of = lambda r: r["raw"]["egarps_native_probability"]  # noqa: E731

    # (1) thrombin Kd series
    series = sorted(
        (r for r in ok if r["target"] == "Thrombin" and r["role"] == "binder" and r["kd_nm"]),
        key=lambda r: r["kd_nm"])
    pts = [(r["id"], r["kd_nm"], np_of(r)) for r in series]
    xs = [p[2] for p in pts]
    ys = [-np.log10(p[1]) for p in pts]
    rho = float(spearmanr(xs, ys)[0])
    lo, hi = rho_ci(xs, ys, seed_of("thrombin_series"))
    thrombin_block = {
        "n_points": len(pts),
        "points": [{"id": i, "kd_nm": kd, "native_probability": np} for i, kd, np in pts],
        "kd_span_orders": round(float(np.log10(pts[-1][1]) - np.log10(pts[0][1])), 3),
        "spearman_rho_vs_neglog_kd": round(rho, 4),
        "rho_ci95_descriptive": [round(lo, 4), round(hi, 4)],
        "ranking_gate": RANK_GATE,
        "ranking_pass": bool(rho >= RANK_GATE),
    }
    leg4 = [by_id[i] for i in LEGACY_THROMBIN_4PT if i in by_id]
    if len(leg4) == 4:
        rho4 = float(spearmanr([np_of(r) for r in leg4],
                               [-np.log10(r["kd_nm"]) for r in leg4])[0])
        thrombin_block["legacy_4point_reproduction"] = {
            "n": 4,
            "rho_new": round(rho4, 4),
            "rho_retained": LEGACY_THROMBIN_4PT_RHO,
            "delta": round(rho4 - LEGACY_THROMBIN_4PT_RHO, 4),
        }

    # (2) pooled binder-vs-negative AUROC
    pooled: dict[str, dict] = {}
    binder_kd = [r for r in ok if r["role"] == "binder"]
    binder_all = [r for r in ok if r["role"] in ("binder", "binder_no_kd")]
    negatives = [r for r in ok if r["role"] == "negative"]
    for oracle in ORACLES:
        pos = [r["raw"][oracle] for r in binder_kd if r["raw"][oracle] is not None]
        neg = [r["raw"][oracle] for r in negatives if r["raw"][oracle] is not None]
        a = auroc(pos, neg)
        clo, chi = auroc_ci(pos, neg, seed_of(f"pooled|{oracle}"))
        blk = {
            "n_binders": len(pos), "n_negatives": len(neg),
            "auroc": round(a, 4),
            "auroc_ci95": [round(clo, 4), round(chi, 4)],
            "ci_covers_chance": bool(clo <= 0.5 <= chi),
            "screening_gate": AUROC_GATE,
            "screening_pass": bool(a >= AUROC_GATE),
        }
        pos_all = [r["raw"][oracle] for r in binder_all if r["raw"][oracle] is not None]
        a_all = auroc(pos_all, neg)
        blk["auroc_all_binders_variant"] = round(a_all, 4)
        pooled[oracle] = blk

    # (3) extreme contrast
    rand_neg = [r for r in ok if r.get("random_negative")]
    lit_neg = [r for r in ok if r["role"] == "negative" and not r.get("random_negative")]
    peg = by_id.get("pegaptanib_vegf")
    contrast = {
        "pegaptanib_np": np_of(peg) if peg else None,
        "pegaptanib_kd_nm": peg["kd_nm"] if peg else None,
        "scrambled_tba_np": np_of(by_id["scrambled_tba"]) if "scrambled_tba" in by_id else None,
        "random30_a_np": np_of(by_id["random30_a"]) if "random30_a" in by_id else None,
        "random_class_np_median": round(float(np.median([np_of(r) for r in rand_neg])), 6) if rand_neg else None,
        "random_class_np_min": round(float(min(np_of(r) for r in rand_neg)), 8) if rand_neg else None,
        "random_class_np_max": round(float(max(np_of(r) for r in rand_neg)), 6) if rand_neg else None,
        "binder_np_median": round(float(np.median([np_of(r) for r in binder_all])), 6) if binder_all else None,
        "negative_np_median": round(float(np.median([np_of(r) for r in negatives])), 6) if negatives else None,
        "binders_below_negatives_median": bool(
            np.median([np_of(r) for r in binder_all]) < np.median([np_of(r) for r in negatives]))
        if binder_all and negatives else None,
    }

    # (4) ridgeline groups
    def group_stats(rs: list[dict]) -> dict:
        vals = [np_of(r) for r in rs if np_of(r) is not None]
        sig = lambda v: float(f"{v:.3e}")  # 3 significant digits — np spans 9 orders
        return {
            "n": len(vals),
            "median": sig(float(np.median(vals))),
            "q1": sig(float(np.percentile(vals, 25))),
            "q3": sig(float(np.percentile(vals, 75))),
            "min": sig(float(min(vals))),
            "max": sig(float(max(vals))),
        }

    ridgeline = {
        "split_rule": "role negative; 'rand' in id -> random-sequence class, else literature class",
        "binders": group_stats(binder_all),
        "literature_negatives": group_stats(lit_neg),
        "random_negatives": group_stats(rand_neg),
    }

    # (5) legacy-P2 1:1 reproduction
    shared_ids = [i for i in LEGACY_P2 if i in by_id]
    repro_entries = {
        i: {
            "legacy_np": LEGACY_P2[i]["np"],
            "new_np": np_of(by_id[i]),
            "abs_delta_np": round(abs(np_of(by_id[i]) - LEGACY_P2[i]["np"]), 8),
        } for i in shared_ids if np_of(by_id[i]) is not None
    }
    dts = [v["abs_delta_np"] for v in repro_entries.values()]
    legacy_shared_pos = [LEGACY_P2[i]["np"] for i in shared_ids if LEGACY_P2[i]["role"] == "binder"]
    legacy_shared_neg = [LEGACY_P2[i]["np"] for i in shared_ids if LEGACY_P2[i]["role"] == "negative"]
    new_shared_pos = [np_of(by_id[i]) for i in shared_ids
                      if LEGACY_P2[i]["role"] == "binder" and np_of(by_id[i]) is not None]
    new_shared_neg = [np_of(by_id[i]) for i in shared_ids
                      if LEGACY_P2[i]["role"] == "negative" and np_of(by_id[i]) is not None]
    repro = {
        "n_shared": len(shared_ids),
        "missing_from_v3": [i for i in LEGACY_P2 if i not in by_id],
        "per_entry": repro_entries,
        "median_abs_delta_np": round(float(np.median(dts)), 8) if dts else None,
        "max_abs_delta_np": round(float(max(dts)), 8) if dts else None,
        "shared12_auroc_new": round(auroc(new_shared_pos, new_shared_neg), 4)
        if new_shared_pos and new_shared_neg else None,
        "shared12_auroc_legacy": round(auroc(legacy_shared_pos, legacy_shared_neg), 4)
        if legacy_shared_pos and legacy_shared_neg else None,
        "legacy_full_auroc_context": LEGACY_FULL_AUROC,
        "legacy_full_matrix_note": "retained 9-vs-5 pooled AUROC quoted as context; the "
                                   "shared-12 submatrix (7 vs 4) is the 1:1 comparison basis",
    }
    if repro["shared12_auroc_new"] is not None and repro["shared12_auroc_legacy"] is not None:
        repro["shared12_delta"] = round(
            repro["shared12_auroc_new"] - repro["shared12_auroc_legacy"], 4)

    # (6) cross-check vs exp10 v3 records
    cross_check = None
    if EXP10_V3_RECORDS.exists():
        exp10 = {}
        for l in EXP10_V3_RECORDS.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                exp10[r["id"]] = r
        deltas = {o: [] for o in ORACLES}
        for r in ok:
            e10 = exp10.get(r["id"])
            if not e10 or not e10.get("success"):
                continue
            for o in ORACLES:
                a, b = r["raw"][o], e10["raw"][o]
                if a is not None and b is not None:
                    deltas[o].append(abs(a - b))
        cross_check = {
            o: {"n_pairs": len(v),
                "median_abs_delta": round(float(np.median(v)), 6) if v else None,
                "max_abs_delta": round(float(np.max(v)), 6) if v else None}
            for o, v in deltas.items()
        }

    prim = pooled[PRIMARY_ORACLE]
    gate_rank = thrombin_block["ranking_pass"]
    gate_screen = prim["screening_pass"]
    summary = {
        "analysis": "Exp13 EGARPS affinity-calibration profile (reset run; retained P2 re-registered)",
        "mode": mode_label,
        "anchor_set": {
            "path": str(ANCHOR_JSON.relative_to(PROJECT_ROOT)),
            "n_entries": len(records),
            "composition": EXPECTED_V3,
            "convention": "DNA aptamers scored as RNA via T->U (anchor-set convention)",
        },
        "conventions": {
            "instrument": "ToolExecutor.run_tool (ToolRegistry, schema-validated .invoke) -> deployed microservices as shipped",
            "services": {"rhofold": 8005, "proteinx": 8022, "egarps": 8023},
            "gpu_map": "deployed instances GPU-pinned 0/1/2 (placement inherited, untouched — zero intervention)",
            "capgate_policy": os.environ.get("RNADA_CAPGATE", "enforce"),
            "zero_intervention": "anchor entries verbatim; no threshold presets; fixed protocol args only (num_models=1, academic=False)",
            "primary_oracle": PRIMARY_ORACLE,
            "rho": "Spearman(np, -log10 Kd); positive = tighter binder scored higher; average-rank ties",
            "auroc": "pooled cross-target: role binder (measured Kd) vs role negative — the retained P2 convention; midrank tie-corrected",
            "gates": {"rho": RANK_GATE, "auroc": AUROC_GATE, "source": "retained P2 pre-registration (2026-08-03)"},
            "bootstrap": f"percentile 95% CI, {N_BOOT} resamples, crc32-fixed seeds (descriptive)",
        },
        "n_records": len(records),
        "n_success": len(ok),
        "n_failed": len(records) - len(ok),
        "failed_ids": [r["id"] for r in records if not r["success"]],
        "thrombin_series": thrombin_block,
        "pooled_binder_vs_negative": pooled,
        "extreme_contrast": contrast,
        "ridgeline_groups": ridgeline,
        "legacy_p2_reproduction": repro,
        "comparison_vs_exp10_v3": cross_check,
        "decision_bits": [
            f"thrombin {thrombin_block['n_points']}-point Kd series: rho={thrombin_block['spearman_rho_vs_neglog_kd']:+.4f} "
            f"(CI {thrombin_block['rho_ci95_descriptive']}) — ranking gate rho>={RANK_GATE}: "
            f"{'PASS' if gate_rank else 'FAIL'}",
            f"pooled binder-vs-negative AUROC={prim['auroc']:.4f} "
            f"(CI {prim['auroc_ci95']}, n={prim['n_binders']} vs {prim['n_negatives']}) — "
            f"screening gate >= {AUROC_GATE}: {'PASS' if gate_screen else 'FAIL'}; "
            f"CI covers chance: {prim['ci_covers_chance']}",
            f"inversion read-out: binders-below-negatives median = {contrast['binders_below_negatives_median']} "
            f"(binder median {contrast['binder_np_median']} vs negative median {contrast['negative_np_median']})",
            f"retained-P2 1:1: shared {repro['n_shared']}/15, median |dnp| = {repro['median_abs_delta_np']}, "
            f"shared-12 AUROC new {repro.get('shared12_auroc_new')} vs legacy {repro.get('shared12_auroc_legacy')} "
            f"(retained full 0.3556, 9v5)",
            "P2 verdict gates (rho>=0.6 AND auroc>=0.8): "
            + ("GO" if (gate_rank and gate_screen) else "NO-GO — EGARPS np remains uncalibrated "
               "(analysis-side; wording: 'no validated affinity calibration')"),
        ],
        "wording_discipline": "conclusions phrased as 'no validated affinity calibration for RNA-protein aptamers'; "
                              "inversion described as observed on this panel, never as an absolute claim",
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
    mode.add_argument("--pilot", action="store_true", help="score the 6-entry pilot subset")
    mode.add_argument("--run", action="store_true", help="score the full 95-entry anchor set")
    mode.add_argument("--summary", action="store_true", help="write summary.json")
    parser.add_argument("--resume", action="store_true",
                        help="skip entries with a successful record on disk")
    parser.add_argument("--timeout", type=int, default=1800,
                        help="per-entry protocol timeout ceiling (s)")
    args = parser.parse_args()

    anchor = load_anchor()
    entries = anchor["entries"]

    if args.pilot:
        subset = [e for e in entries if e["id"] in PILOT_IDS]
        assert len(subset) == len(PILOT_IDS), "pilot ids missing from anchor set"
        return run_mode("pilot", subset, args.timeout, args.resume)
    if args.run:
        return run_mode("records", entries, args.timeout, args.resume)
    if args.summary:
        recs = []
        p = RESULTS_DIR / "records.jsonl"
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
