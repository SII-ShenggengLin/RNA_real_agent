#!/usr/bin/env python3
"""Fig 4c/d driver: known-aptamer validation for the RNA aptamer workflow.

Implements `docs/MANUSCRIPT.md` §6.2 run matrix B:

1. ``workflow_run`` (panel c): run ``rna_aptamer_design`` once (BMC×1) for
   Thrombin (1HAO) and SARS-CoV-2 N (6M3M) and collect the designed
   candidates' three-component score distributions (``pool_objectives``,
   same style as ``run_bmc_type2_ablation.py``).
2. ``known_aptamer_score``: score the known aptamer sequences
   (``known_aptamer_reference.sequence``; DNA alphabet is converted T→U)
   through the same chain via *direct capability calls* (in the style of
   ``score_literature_mrna_anchors.py``):
   RhoFold (``predict_rna_tertiary_structure_with_rhofold``) →
   ProteinX complex (``predict_rna_protein_complex_with_proteinx``) →
   EGARPS (``score_rna_protein_complex_with_egarps``) on the ProteinX
   complex PDB. Components are computed with the workflow's own
   ``score_aptamer_candidate`` so the numbers are directly comparable to
   the designed-candidate pool.
3. ``hotspot_recovery``: parse the identified hotspot residues from the
   block-1 run (trace step ``identify_protein_binding_hotspots``, falling
   back to candidate ``metadata.hotspot_residues``) and compute overlap
   with ``known_hotspot_residues``:
     - Jaccard on exact ``chain/resnum`` strings;
     - structural contact overlap: a known residue counts as recovered when
       its CA lies within ``--contact-cutoff`` Å (default 10 Å, the DBSCAN
       eps of the identification algorithm) of any identified residue's CA
       in the target PDB (and symmetrically for identified-vs-known).
       Residue numbering follows the benchmark PDB files.
4. ``vegf_case`` (panel d): run the workflow once on VEGF (1VPF), extract
   the identified hotspot + per-candidate interface-contact stats, compare
   against the curated pegaptanib site from
   ``external_anchors/aptamers/pegaptanib.json`` (currently ``null`` →
   reported as a data gap), and score the pegaptanib sequence through the
   same direct chain. The pegaptanib anchor stores the *unmodified* parent
   base sequence (the drug carries 2'-F pyrimidines / 2'-O-Me purines /
   5'-PEG, see pegaptanib.json notes); it is scored as plain RNA.

Output: JSONL, one record per block, default
``experiments/results/fig4_known_aptamers.jsonl`` (spec §6.2 names the
artifact ``fig4_known_aptamers.json``; JSONL-per-block is the recommended
layout, so the ``.jsonl`` extension is used — pass ``--output`` to
override). ``--resume`` skips ``(block, target_id)`` pairs that already
have a successful record. A failing block is recorded with
``success=false`` and never aborts the remaining blocks.

Usage (from ``rna_agent_system/``):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_known_aptamer_validation.py \
        [--targets Thrombin,SARS-CoV-2_Nucleocapsid,VEGF] [--resume] \
        [--timeout SEC] [--dry-run] [--output PATH]
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

EXPERIMENTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXPERIMENTS_DIR.parent
sys.path.insert(0, str(EXPERIMENTS_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from run_platform_quality_benchmark import find_results_file, run_task_dict  # noqa: E402
from run_bmc_type2_ablation import find_structure  # noqa: E402

TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "targets"
ANCHORS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "aptamers"
SESSIONS_DIR = PROJECT_ROOT / "workspace" / "sessions"
WORK_DIR = PROJECT_ROOT / "workspace" / "fig4_known_aptamers"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig4_known_aptamers.jsonl"

# Targets with both a known aptamer reference and known hotspot residues.
SCORED_TARGETS = ["Thrombin", "SARS-CoV-2_Nucleocapsid"]
VEGF_TARGET = "VEGF"
ALL_TARGETS = SCORED_TARGETS + [VEGF_TARGET]

# Fig-4 common params (MANUSCRIPT §6.1); this matrix fixes bmc_max_rounds=1.
WORKFLOW_PARAMS = {
    "aptamer_length": 30,
    "n_odesign_samples": 8,
    "odesign_seeds": [42, 123],
    "bmc_max_rounds": 1,
    "bmc_improvement_threshold": 0.05,
}
SESSION_PREFIX = "fig4kav"

# Candidate ``scores`` keys copied into pool_objectives (components + raw
# values + interface contacts, all stored inside candidate.scores).
POOL_SCORE_KEYS = [
    "egarps_component",
    "rhofold_component",
    "iptm_component",
    "egarps_native_probability",
    "rhofold_mean_plddt",
    "proteinx_ipTM",
    "interface_contacts",
    "asf_distance",
]

AA3_TO_1 = {
    "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
    "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
    "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
    "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
}


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested in test_known_aptamer_validation.py)
# ---------------------------------------------------------------------------


def dna_to_rna(seq: str) -> str:
    """Return the RNA alphabet form of a nucleic-acid sequence (T→U).

    Known aptamer references may be stored as DNA (e.g. TBA
    ``GGTTGGTGTGGTTGG``) or RNA; the scoring chain expects RNA.
    """
    return "".join(seq.split()).upper().replace("T", "U")


def parse_hotspot_string(hotspot: Optional[str], default_chain: str = "") -> list[str]:
    """Normalise a hotspot string to a sorted list of ``CHAIN/NUM`` entries.

    Accepts ``"H/46,H/67"`` or bare numbers ``"46,67"`` (then
    *default_chain* is prepended). Empty/None input yields ``[]``.
    """
    if not hotspot:
        return []
    out: set[str] = set()
    for part in str(hotspot).split(","):
        part = part.strip()
        if not part:
            continue
        if "/" in part:
            chain, _, num = part.partition("/")
            chain, num = chain.strip(), num.strip()
        else:
            chain, num = default_chain.strip(), part
        if not num.isdigit():
            continue
        out.add(f"{chain}/{int(num)}")
    return sorted(out)


def jaccard(a: set, b: set) -> float:
    """Jaccard index; both-empty is defined as 1.0 (identical empty sets)."""
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _ca_coords(pdb_path: Path, entries: list[str]) -> dict[str, tuple[float, float, float]]:
    """Map ``CHAIN/NUM`` entries to CA coordinates found in *pdb_path*.

    Entries missing from the structure (or without a CA atom) are omitted;
    callers diff the key sets to report them.
    """
    from Bio.PDB import PDBParser

    wanted: dict[str, set[int]] = {}
    for e in entries:
        chain, _, num = e.partition("/")
        wanted.setdefault(chain, set()).add(int(num))
    structure = PDBParser(QUIET=True).get_structure("target", str(pdb_path))
    coords: dict[str, tuple[float, float, float]] = {}
    for model in structure:
        for chain in model:
            if chain.id not in wanted:
                continue
            for residue in chain:
                if residue.id[0].strip():
                    continue
                resnum = residue.id[1]
                if resnum in wanted[chain.id] and "CA" in residue:
                    coords[f"{chain.id}/{resnum}"] = tuple(float(x) for x in residue["CA"].coord)
        break  # first model only
    return coords


def structural_contact_overlap(
    pdb_path: Path,
    identified: list[str],
    known: list[str],
    cutoff: float = 10.0,
) -> dict[str, Any]:
    """Structure-based hotspot overlap (see module docstring, block 3).

    A known residue is *contact-recovered* when its CA is within *cutoff* Å
    of any identified residue's CA; symmetrically an identified residue is
    *contact-relevant* when within *cutoff* Å of any known residue's CA.
    Residues absent from the PDB are listed under ``*_missing_in_structure``
    and excluded from the fractions' numerators and denominators.
    """
    kc = _ca_coords(pdb_path, known)
    ic = _ca_coords(pdb_path, identified)
    known_hits: dict[str, float] = {}
    for k, (kx, ky, kz) in kc.items():
        best = min(
            (((kx - ix) ** 2 + (ky - iy) ** 2 + (kz - iz) ** 2) ** 0.5)
            for (ix, iy, iz) in ic.values()
        ) if ic else None
        if best is not None and best <= cutoff:
            known_hits[k] = round(best, 2)
    identified_hits = 0
    for (ix, iy, iz) in ic.values():
        best = min(
            (((kx - ix) ** 2 + (ky - iy) ** 2 + (kz - iz) ** 2) ** 0.5)
            for (kx, ky, kz) in kc.values()
        ) if kc else None
        if best is not None and best <= cutoff:
            identified_hits += 1
    return {
        "definition": (
            f"CA-CA distance <= {cutoff} A in target PDB "
            "(cutoff = DBSCAN eps of identify_protein_binding_hotspots); "
            "known_recovery = |known within cutoff of any identified| / |known present in structure|; "
            "identified_precision = |identified within cutoff of any known| / |identified present in structure|"
        ),
        "cutoff_angstrom": cutoff,
        "known_recovery_count": len(known_hits),
        "known_recovery_frac": round(len(known_hits) / len(kc), 4) if kc else None,
        "known_recovered_min_distances": known_hits,
        "identified_precision_count": identified_hits,
        "identified_precision_frac": round(identified_hits / len(ic), 4) if ic else None,
        "known_missing_in_structure": sorted(set(known) - set(kc)),
        "identified_missing_in_structure": sorted(set(identified) - set(ic)),
    }


def extract_hotspot_from_results(results: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Pull the auto-identified hotspot string out of a workflow_results dict.

    Primary source: the trace step ``identify_protein_binding_hotspots``.
    Its ``output_summary`` is a Python-dict repr *truncated at 500 chars*,
    so after ``ast.literal_eval`` we fall back to a regex that recovers the
    ``hotspot_residues`` value even from a truncated repr; when the value
    itself is cut mid-string, the final (possibly half-written) entry is
    dropped and the source is marked ``|truncated``.
    Fallback source: the hotspot a round-0 candidate actually used
    (``metadata.hotspot_residues``; ``hotspot_before`` when a BMC expansion
    rewrote it). Returns ``(hotspot_string, source)`` or ``(None, None)``.
    """
    for step in results.get("trace") or []:
        if not isinstance(step, dict):
            continue
        if step.get("tool_name") != "identify_protein_binding_hotspots":
            continue
        if not step.get("success", True):
            continue
        summary = step.get("output_summary") or ""
        try:
            out = ast.literal_eval(summary)
        except (ValueError, SyntaxError):
            out = None
        if isinstance(out, dict):
            hotspot = out.get("hotspot_residues")
            if hotspot:
                return str(hotspot), "trace:identify_protein_binding_hotspots"
            continue
        match = re.search(r"hotspot_residues['\"]?\s*:\s*['\"]([^'\"]*)(['\"]?)", summary)
        if match and match.group(1).strip():
            value, closed = match.group(1), bool(match.group(2))
            entries = [e for e in value.split(",") if e.strip()]
            source = "trace:identify_protein_binding_hotspots"
            if not closed and len(entries) > 1:
                entries = entries[:-1]  # last entry may be cut mid-number
                source += "|truncated"
            hotspot = ",".join(entries)
            if parse_hotspot_string(hotspot):
                return hotspot, source
    for cand in results.get("candidates") or []:
        md = (cand or {}).get("metadata") or {}
        if md.get("bmc_round") not in (None, 0):
            continue
        hotspot = md.get("hotspot_before") or md.get("hotspot_residues")
        if hotspot:
            return str(hotspot), "candidate_metadata"
    return None, None


def detect_chains_in_pdb(pdb_path: Path) -> tuple[str, str]:
    """Detect (protein_chain, rna_chain) in a complex PDB.

    Mirrors ``RnaAptamerDesignWorkflow._detect_chains_in_pdb``: protein =
    chain with most amino-acid residues, RNA = other chain with most
    nucleotide residues; falls back to ("A", "B").
    """
    try:
        from Bio.PDB import PDBParser
        structure = PDBParser(QUIET=True).get_structure("complex", str(pdb_path))
    except Exception:
        return "A", "B"
    candidates: list[tuple[str, int, int]] = []
    for model in structure:
        for chain in model:
            prot = nuc = 0
            for residue in chain:
                if residue.id[0].strip():
                    continue
                resname = residue.resname.strip().upper()
                if resname in AA3_TO_1:
                    prot += 1
                elif resname in {"A", "U", "G", "C", "DA", "DT", "DG", "DC"}:
                    nuc += 1
            candidates.append((chain.id, prot, nuc))
        break
    if not candidates:
        return "A", "B"
    candidates.sort(key=lambda x: (x[1], -x[2]), reverse=True)
    protein_chain = candidates[0][0]
    rna_candidates = [c for c in candidates if c[0] != protein_chain]
    rna_candidates.sort(key=lambda x: x[2], reverse=True)
    rna_chain = rna_candidates[0][0] if rna_candidates else "B"
    return protein_chain, rna_chain


def extract_protein_sequence(pdb_path: Path, chain_id: Optional[str] = None) -> tuple[str, str]:
    """Extract an amino-acid sequence from a PDB.

    With *chain_id* given, that chain is tried first; if it yields no
    protein residues (e.g. it is DNA/RNA), the remaining chains are scanned
    in file order for the first protein-like chain. With ``chain_id=None``
    the first chain is used — mirroring the workflow's
    ``_extract_protein_sequence_from_structure``. Returns
    ``(sequence, "chain:<id>")``; ``("", "")`` when nothing is found.
    """
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
        break  # first model only
    if chain_id is None:
        for cid, seq in chains[:1]:
            return seq, f"chain:{cid}"
        return "", ""
    for cid, seq in chains:
        if cid == chain_id and seq:
            return seq, f"chain:{cid}"
    for cid, seq in chains:
        if seq:
            return seq, f"chain:{cid}:fallback"
    return "", ""


# ---------------------------------------------------------------------------
# Data loading / planning
# ---------------------------------------------------------------------------


def load_target_meta(target_id: str) -> dict[str, Any]:
    path = TARGETS_DIR / f"{target_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_known_aptamers() -> dict[str, Any]:
    return json.loads((ANCHORS_DIR / "known_aptamers.json").read_text(encoding="utf-8"))


def load_pegaptanib() -> dict[str, Any]:
    return json.loads((ANCHORS_DIR / "pegaptanib.json").read_text(encoding="utf-8"))


def workflow_params_for(meta: dict[str, Any]) -> dict[str, Any]:
    struct = find_structure(meta["pdb_id"])
    if struct is None:
        raise FileNotFoundError(f"no structure file for {meta['pdb_id']}")
    params = {
        "protein_structure_path": str(struct.relative_to(PROJECT_ROOT)),
        "chain_id": meta.get("pdb_chain") or "A",
    }
    params.update(WORKFLOW_PARAMS)
    return params


def session_id_for(target_id: str) -> str:
    return f"{SESSION_PREFIX}_known_{target_id}"


def plan_blocks(targets: list[str]) -> list[dict[str, Any]]:
    """Build the execution plan (also printed by --dry-run)."""
    known = load_known_aptamers()
    peg = load_pegaptanib()
    blocks: list[dict[str, Any]] = []
    for tid in targets:
        meta = load_target_meta(tid)
        struct = find_structure(meta["pdb_id"])
        params = None
        if struct is not None:
            try:
                params = workflow_params_for(meta)
            except FileNotFoundError:
                params = None
        anchor = known.get(tid) or {}
        if tid in SCORED_TARGETS:
            blocks.append({
                "block": "workflow_run", "target_id": tid,
                "pdb_id": meta["pdb_id"], "chain_id": meta.get("pdb_chain"),
                "structure": str(struct.relative_to(PROJECT_ROOT)) if struct else None,
                "params": params, "session_id": session_id_for(tid),
            })
            blocks.append({
                "block": "known_aptamer_score", "target_id": tid,
                "pdb_id": meta["pdb_id"], "chain_id": meta.get("pdb_chain"),
                "sequence": anchor.get("sequence"),
                "sequence_rna": dna_to_rna(anchor["sequence"]) if anchor.get("sequence") else None,
                "kd_nm": anchor.get("kd_nm"), "reference": anchor.get("reference"),
                "chain": ["rhofold", "proteinx_complex", "egarps", "interface_analysis"],
            })
            blocks.append({
                "block": "hotspot_recovery", "target_id": tid,
                "pdb_id": meta["pdb_id"], "chain_id": meta.get("pdb_chain"),
                "known_hotspot_residues": parse_hotspot_string(meta.get("known_hotspot_residues")),
            })
        elif tid == VEGF_TARGET:
            blocks.append({
                "block": "vegf_case", "target_id": tid,
                "pdb_id": meta["pdb_id"], "chain_id": meta.get("pdb_chain"),
                "structure": str(struct.relative_to(PROJECT_ROOT)) if struct else None,
                "params": params, "session_id": session_id_for(tid),
                "known_hotspot_residues": parse_hotspot_string(meta.get("known_hotspot_residues")),
                "pegaptanib_sequence_rna": dna_to_rna(peg["sequence"]) if peg.get("sequence") else None,
                "pegaptanib_binding_site_residues": peg.get("binding_site_residues"),
                "pegaptanib_data_gap": peg.get("binding_site_residues") is None,
            })
    return blocks


def load_done_blocks(output: Path) -> set[tuple[str, str]]:
    done: set[tuple[str, str]] = set()
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("success"):
                done.add((r.get("block"), r.get("target_id")))
    return done


def append_record(output: Path, record: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


# ---------------------------------------------------------------------------
# Block 1: workflow runs
# ---------------------------------------------------------------------------


def block_workflow_run(plan: dict[str, Any], *, timeout: int, env: dict[str, str]) -> dict[str, Any]:
    tid = plan["target_id"]
    task = {
        "task_id": f"known_{tid}",
        "workflow": "rna_aptamer_design",
        "category": "known_aptamer_validation",
        "description": f"{tid} known-aptamer validation run (BMCx1)",
        "input": plan["params"],
        "evaluation_rubric": None,
    }
    rec = run_task_dict(task, timeout=timeout, env=env, session_prefix=SESSION_PREFIX)
    pool = [
        {k: (c.get("scores") or {}).get(k) for k in POOL_SCORE_KEYS}
        for c in (rec.get("candidates") or [])
    ]
    best = (rec.get("best_candidate") or {}).get("scores") or {}
    return {
        "block": "workflow_run",
        "target_id": tid,
        "pdb_id": plan["pdb_id"],
        "params": plan["params"],
        "session_id": rec.get("session_id"),
        "success": rec["success"],
        "error": rec.get("error"),
        "elapsed_seconds": rec.get("elapsed_seconds"),
        "candidate_count": rec.get("candidate_count"),
        "pareto_frontier_size": rec.get("pareto_frontier_size"),
        "bmc_rounds_executed": rec.get("bmc_rounds"),
        "best": {k: best.get(k) for k in POOL_SCORE_KEYS},
        "pool_objectives": pool,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------------------
# Block 2: score a known aptamer through the direct capability chain
# ---------------------------------------------------------------------------


def _write_fasta(name: str, header: str, seq: str) -> str:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    p = WORK_DIR / f"{name}.fa"
    p.write_text(f">{header}\n{seq}\n", encoding="utf-8")
    return str(p.relative_to(PROJECT_ROOT))


def _proteinx_cif_to_pdb(cif_path: str, name: str) -> str:
    """Convert a Protenix mmCIF complex to a PDB copy for EGARPS/interface.

    NOTE (2026-07-27, do not revert): feeding the raw Protenix ``.cif`` to
    EGARPS fails two ways. (1) EGARPS's CIF reader rejects the OP3 atoms
    Protenix writes (``OP3 not in STD_ATOM_NAMES``) while its PDB path
    (Bio.PDB/pymol) accepts them. (2) EGARPS's ``ins.py`` derives its pickle
    cache paths via ``pdb.replace('.pdb', ...)`` — a no-op for ``.cif``
    inputs — so its caches are dumped *over the input file itself*,
    destroying the Protenix artifact. A gemmi-converted ``.pdb`` copy avoids
    both: OP3 parses fine and caches become sidecar ``.pkl`` files.

    NOTE 2 (2026-07-27): the output basename must NOT contain the substring
    ``protein`` (nor ``rna``). EGARPS's ``feature_residue.get_ss_feat_for_dir``
    (and the torsion path) types chains with ``re.search('protein', key)``
    where ``key = <pdb basename>_rna_<chain>`` — a basename containing
    ``protein`` (e.g. "proteinx") hijacks the RNA chain into the protein
    DSSP feature path, producing 3-wide RNA ss rows vs the expected 7-wide
    and crashing ``np.row_stack`` in ``dataload._install_external_feat``.
    """
    import gemmi

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    safe = name.replace("protein", "px").replace("rna", "x")
    out = WORK_DIR / f"{safe}_px_complex.pdb"
    gemmi.read_structure(cif_path).write_pdb(str(out))
    return str(out.relative_to(PROJECT_ROOT))


def score_aptamer_through_chain(
    name: str,
    rna_seq: str,
    struct: Path,
    chain_id: str,
    *,
    timeout: int,
) -> dict[str, Any]:
    """Score one RNA aptamer: RhoFold → ProteinX complex → EGARPS → interface.

    Direct capability calls (``agent_core.tools.<fn>.func``), the same code
    paths the workflow uses; components are computed with the workflow's own
    ``score_aptamer_candidate``. The ProteinX complex PDB is the EGARPS
    substrate (the workflow scores the ODesign complex instead; recorded
    under ``chain_note``).

    Protein sequence for ProteinX is taken from the target chain of the
    benchmark PDB (``extract_protein_sequence(struct, chain_id)``). NOTE:
    the workflow itself extracts the *first* chain of the file; for 1HAO
    that is the DNA aptamer chain D, so workflow-designed Thrombin
    candidates get ``iptm_component = 0`` while this chain yields a real
    ipTM — see ``protein_sequence.workflow_note``.
    """
    started = time.monotonic()
    steps: dict[str, str] = {}
    raw: dict[str, Any] = {}
    artifacts: dict[str, Any] = {}
    interface: dict[str, Any] = {}
    error: Optional[str] = None

    protein_seq, protein_src = extract_protein_sequence(struct, chain_id)
    rna_fa = _write_fasta(f"{name}_aptamer", f"{name}_aptamer", rna_seq)
    protein_fa = (
        _write_fasta(f"{name}_protein", f"{name}_protein", protein_seq) if protein_seq else None
    )

    # Lazy imports: keep --dry-run and pure-function tests free of the
    # agent_core.tools dependency chain (and free of any service contact).
    from agent_core.tools import (
        analyze_rna_protein_interface,
        predict_rna_protein_complex_with_proteinx,
        predict_rna_tertiary_structure_with_rhofold,
        score_rna_protein_complex_with_egarps,
    )
    from agent_core.workflows.rna_aptamer_design import score_aptamer_candidate

    rhofold_pdb: Optional[str] = None
    try:
        rh = predict_rna_tertiary_structure_with_rhofold.func(filepath=rna_fa)
        raw["rhofold_mean_plddt"] = rh.get("mean_plddt")
        rhofold_pdb = rh.get("pdb_filepath")
        artifacts["rhofold_pdb"] = rhofold_pdb
        steps["rhofold"] = "ok"
    except Exception as exc:  # service down / bad payload — continue chain
        steps["rhofold"] = f"failed: {exc}"

    proteinx_pdb: Optional[str] = None
    if protein_fa:
        try:
            px = predict_rna_protein_complex_with_proteinx.func(
                protein_filepath=protein_fa,
                rna_filepath=rna_fa,
                num_models=1,
                timeout_seconds=float(max(timeout, 600)),
            )
            raw["proteinx_ipTM"] = px.get("ipTM")
            raw["proteinx_mean_plddt"] = px.get("mean_plddt")
            raw["proteinx_ranking_confidence"] = px.get("ranking_confidence")
            proteinx_pdb = px.get("pdb_filepath") or None
            artifacts["proteinx_pdb"] = proteinx_pdb
            steps["proteinx_complex"] = "ok"
        except Exception as exc:
            steps["proteinx_complex"] = f"failed: {exc}"
    else:
        steps["proteinx_complex"] = "skipped: no protein sequence extracted"

    egarps_input: Optional[str] = None
    if proteinx_pdb:
        try:
            egarps_input = str(
                PROJECT_ROOT / _proteinx_cif_to_pdb(str(Path(proteinx_pdb).resolve()), name)
            )
            artifacts["proteinx_complex_pdb"] = egarps_input
            steps["cif_to_pdb"] = "ok"
        except Exception as exc:
            steps["cif_to_pdb"] = f"failed: {exc}"

    if egarps_input:
        try:
            eg = score_rna_protein_complex_with_egarps.func(
                filepath=egarps_input, academic=False
            )
            raw["egarps_native_probability"] = eg.get("native_probability")
            steps["egarps"] = "ok"
        except Exception as exc:
            steps["egarps"] = f"failed: {exc}"
        try:
            p_chain, r_chain = detect_chains_in_pdb(Path(egarps_input))
            iface = analyze_rna_protein_interface.func(
                complex_pdb_filepath=egarps_input,
                protein_chain_id=p_chain,
                rna_chain_id=r_chain,
                contact_cutoff=5.0,
            )
            interface = {
                "protein_chain_id": p_chain,
                "rna_chain_id": r_chain,
                "interface_contacts": iface.get("interface_contacts"),
                "hydrogen_bonds": iface.get("hydrogen_bonds"),
                "salt_bridges": iface.get("salt_bridges"),
                "buried_sasa": iface.get("buried_sasa"),
            }
            steps["interface_analysis"] = "ok"
        except Exception as exc:
            steps["interface_analysis"] = f"failed: {exc}"
    else:
        steps.setdefault("egarps", "skipped: no ProteinX complex PDB")
        steps.setdefault("interface_analysis", "skipped: no ProteinX complex PDB")

    metrics = {
        "egarps_native_probability": raw.get("egarps_native_probability"),
        "rhofold_mean_plddt": raw.get("rhofold_mean_plddt"),
        "proteinx_ipTM": raw.get("proteinx_ipTM"),
    }
    components = score_aptamer_candidate(metrics)
    failed = {k: v for k, v in steps.items() if v.startswith("failed")}
    if failed:
        error = "; ".join(f"{k}={v}" for k, v in failed.items())
    return {
        "sequence_rna": rna_seq,
        "sequence_length": len(rna_seq),
        "protein_sequence": {
            "source": protein_src or None,
            "length": len(protein_seq),
            "workflow_note": (
                "The workflow extracts the FIRST chain of the structure file "
                "(_extract_protein_sequence_from_structure); for 1HAO the first "
                "chain is the DNA aptamer chain D, so workflow candidates get "
                "iptm_component=0. This record uses the target chain instead."
            ),
        },
        "components": components,
        "raw": raw,
        "interface": interface,
        "artifacts": artifacts,
        "steps": steps,
        "chain_note": (
            "EGARPS scores the ProteinX complex PDB here; the workflow scores "
            "the ODesign-generated complex. rhofold/iptm components use the "
            "identical inputs as workflow candidates (aptamer sequence; "
            "protein sequence + aptamer sequence)."
        ),
        "success": not failed,
        "error": error,
        "elapsed_seconds": round(time.monotonic() - started, 2),
    }


def block_known_aptamer_score(plan: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    tid = plan["target_id"]
    meta = load_target_meta(tid)
    struct = find_structure(meta["pdb_id"])
    if struct is None:
        raise FileNotFoundError(f"no structure file for {meta['pdb_id']}")
    seq = plan["sequence"]
    if not seq:
        raise ValueError(f"{tid}: no known aptamer sequence in anchors")
    result = score_aptamer_through_chain(
        f"known_{tid}", dna_to_rna(seq), struct, meta.get("pdb_chain") or "A", timeout=timeout
    )
    result.update({
        "block": "known_aptamer_score",
        "target_id": tid,
        "pdb_id": meta["pdb_id"],
        "chain_id": meta.get("pdb_chain"),
        "sequence_original": seq,
        "converted_dna_to_rna": "T" in seq.upper(),
        "kd_nm": plan.get("kd_nm"),
        "reference": plan.get("reference"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    return result


# ---------------------------------------------------------------------------
# Block 3: hotspot recovery
# ---------------------------------------------------------------------------


def find_hotspot_sessions(target_id: str) -> list[Path]:
    """Session dirs that may hold an identified hotspot for *target_id*.

    Order: this driver's own run first, then fig4t2 ablation sessions
    (BMC×1 seed set 0 first, then any round/seed) — the identification
    algorithm is deterministic given structure+chain, so a completed
    ablation run is a valid fallback source.
    """
    dirs: list[Path] = []
    own = SESSIONS_DIR / session_id_for(target_id)
    if own.is_dir():
        dirs.append(own)
    for pat in (f"fig4t2_t2_{target_id}_r1_s*", f"fig4t2_t2_{target_id}_r*_s*"):
        dirs.extend(sorted(SESSIONS_DIR.glob(pat)))
    seen: set[Path] = set()
    unique: list[Path] = []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique


def extract_identified_hotspot(target_id: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (hotspot_string, source, session_id) from available run records."""
    for sess in find_hotspot_sessions(target_id):
        results_file = find_results_file(sess)
        if results_file is None:
            continue
        try:
            results = json.loads(results_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        hotspot, source = extract_hotspot_from_results(results)
        if hotspot:
            return hotspot, f"{source}@{results.get('session_id', sess.name)}", results.get("session_id", sess.name)
    return None, None, None


def compute_hotspot_overlap(
    struct: Path,
    identified: list[str],
    known: list[str],
    *,
    cutoff: float,
) -> dict[str, Any]:
    overlap = {
        "jaccard": round(jaccard(set(identified), set(known)), 4),
        "identified_hotspot_residues": identified,
        "known_hotspot_residues": known,
        "exact_matches": sorted(set(identified) & set(known)),
    }
    overlap.update(structural_contact_overlap(struct, identified, known, cutoff))
    return overlap


def block_hotspot_recovery(plan: dict[str, Any], *, cutoff: float) -> dict[str, Any]:
    tid = plan["target_id"]
    meta = load_target_meta(tid)
    struct = find_structure(meta["pdb_id"])
    if struct is None:
        raise FileNotFoundError(f"no structure file for {meta['pdb_id']}")
    known = parse_hotspot_string(meta.get("known_hotspot_residues"))
    if not known:
        raise ValueError(f"{tid}: target JSON has no known_hotspot_residues")
    hotspot_str, source, session = extract_identified_hotspot(tid)
    if not hotspot_str:
        raise RuntimeError(f"{tid}: no identified hotspot found in any session record")
    identified = parse_hotspot_string(hotspot_str)
    overlap = compute_hotspot_overlap(struct, identified, known, cutoff=cutoff)
    return {
        "block": "hotspot_recovery",
        "target_id": tid,
        "pdb_id": meta["pdb_id"],
        "chain_id": meta.get("pdb_chain"),
        "hotspot_source": source,
        "hotspot_session_id": session,
        "success": True,
        "error": None,
        **overlap,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------------------
# Block 4: VEGF / pegaptanib case (panel d)
# ---------------------------------------------------------------------------


def block_vegf_case(plan: dict[str, Any], *, timeout: int, env: dict[str, str], cutoff: float) -> dict[str, Any]:
    tid = plan["target_id"]
    meta = load_target_meta(tid)
    peg = load_pegaptanib()
    struct = find_structure(meta["pdb_id"])
    if struct is None:
        raise FileNotFoundError(f"no structure file for {meta['pdb_id']}")

    record: dict[str, Any] = {
        "block": "vegf_case",
        "target_id": tid,
        "pdb_id": meta["pdb_id"],
        "chain_id": meta.get("pdb_chain"),
        "success": True,
        "error": None,
        "substatus": {},
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    # 1) workflow run (same params as block 1)
    run_rec = block_workflow_run(
        {**plan, "params": plan["params"]}, timeout=timeout, env=env
    )
    record["workflow_run"] = {k: run_rec.get(k) for k in (
        "session_id", "success", "error", "elapsed_seconds", "candidate_count",
        "pareto_frontier_size", "bmc_rounds_executed", "best", "pool_objectives", "params",
    )}
    record["substatus"]["workflow_run"] = "ok" if run_rec["success"] else f"failed: {run_rec.get('error')}"

    # 2) identified hotspot + per-candidate interface-contact stats
    hotspot_str, source, session = extract_identified_hotspot(tid)
    identified = parse_hotspot_string(hotspot_str)
    record["identified_hotspot"] = {
        "residues": identified,
        "source": source,
        "session_id": session,
    }
    contacts = [
        (c.get("scores") or {}).get("interface_contacts")
        for c in ((run_rec.get("pool_objectives")) or [])
    ]
    contacts = [c for c in contacts if isinstance(c, (int, float))]
    record["interface_contacts_stats"] = {
        "n_candidates_with_contacts": len(contacts),
        "min": min(contacts) if contacts else None,
        "median": sorted(contacts)[len(contacts) // 2] if contacts else None,
        "max": max(contacts) if contacts else None,
        "note": "from designed-candidate scores.interface_contacts (5 A cutoff, ODesign complex)",
    }
    record["substatus"]["hotspot_extraction"] = "ok" if identified else "not_found"

    # 3) curated pegaptanib site comparison
    curated_raw = peg.get("binding_site_residues")
    if curated_raw:
        curated = parse_hotspot_string(curated_raw, default_chain=meta.get("pdb_chain") or "A")
        record["pegaptanib_site_comparison"] = compute_hotspot_overlap(
            struct, identified, curated, cutoff=cutoff
        )
        record["substatus"]["site_comparison"] = "ok"
    else:
        record["pegaptanib_site_comparison"] = None
        record["data_gaps"] = [
            "pegaptanib.json binding_site_residues is null (TODO in anchor file: "
            "curate VEGF165 contact residues from Ruckman et al. 1998, J Mol Biol "
            "280:117); site comparison skipped. VEGF target JSON also has "
            "known_hotspot_residues=null, so no Jaccard/overlap is possible for "
            "this panel-d run."
        ]
        record["substatus"]["site_comparison"] = "skipped: curated site missing (data gap)"

    # 4) score pegaptanib (unmodified parent sequence) through the chain
    peg_seq = peg.get("sequence")
    if peg_seq:
        peg_score = score_aptamer_through_chain(
            "pegaptanib", dna_to_rna(peg_seq), struct, meta.get("pdb_chain") or "A",
            timeout=timeout,
        )
        peg_score.update({
            "sequence_original": peg_seq,
            "converted_dna_to_rna": "T" in peg_seq.upper(),
            "modification_note": (
                "Scored as the UNMODIFIED parent RNA base sequence; marketed "
                "pegaptanib carries 2'-fluoro pyrimidines, 2'-O-methyl purines "
                "and a 5' 40 kDa PEG (plus a 3'-3' dT cap) that the "
                "RhoFold/ProteinX/EGARPS chain cannot represent."
            ),
            "kd": peg.get("kd"),
            "anchor_name": peg.get("name"),
        })
        record["pegaptanib_score"] = peg_score
        record["substatus"]["pegaptanib_score"] = "ok" if peg_score["success"] else f"failed: {peg_score.get('error')}"

    failed = {k: v for k, v in record["substatus"].items() if str(v).startswith("failed")}
    if failed:
        record["success"] = False
        record["error"] = "; ".join(f"{k}={v}" for k, v in failed.items())
    return record


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--targets", default=",".join(ALL_TARGETS),
                        help="comma-separated subset of: " + ",".join(ALL_TARGETS))
    parser.add_argument("--resume", action="store_true",
                        help="skip (block, target_id) pairs with a successful record")
    parser.add_argument("--timeout", type=int, default=3600,
                        help="per-workflow-run subprocess timeout; also the ProteinX HTTP timeout")
    parser.add_argument("--contact-cutoff", type=float, default=10.0,
                        help="CA-CA distance cutoff (A) for structural hotspot overlap")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the blocks that would run, then exit")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    unknown = sorted(set(targets) - set(ALL_TARGETS))
    if unknown:
        print(f"ERROR: unknown targets {unknown}; choose from {ALL_TARGETS}", file=sys.stderr)
        return 2

    plan = plan_blocks(targets)

    if args.dry_run:
        print(f"# Fig 4c/d known-aptamer validation — dry run")
        print(f"# output: {args.output}  timeout: {args.timeout}s  contact_cutoff: {args.contact_cutoff} A")
        for b in plan:
            print(f"\n[{b['block']}] {b['target_id']} (pdb={b['pdb_id']}, chain={b.get('chain_id')})")
            if b["block"] == "workflow_run":
                print(f"  session_id: {b['session_id']}")
                print(f"  structure:  {b['structure']}")
                print(f"  params:     {json.dumps(b['params'])}")
            elif b["block"] == "known_aptamer_score":
                print(f"  sequence:        {b['sequence']}  (Kd={b['kd_nm']} nM, {b['reference']})")
                print(f"  sequence (RNA):  {b['sequence_rna']}")
                print(f"  chain:           {' -> '.join(b['chain'])}")
            elif b["block"] == "hotspot_recovery":
                print(f"  known_hotspot_residues: {b['known_hotspot_residues']}")
                print(f"  identified hotspot parsed from session records "
                      f"(own: {session_id_for(b['target_id'])}, fallback: fig4t2_t2_{b['target_id']}_r*_s*)")
            elif b["block"] == "vegf_case":
                print(f"  session_id: {b['session_id']}")
                print(f"  params:     {json.dumps(b['params'])}")
                print(f"  pegaptanib (unmodified parent, RNA): {b['pegaptanib_sequence_rna']}")
                if b["pegaptanib_data_gap"]:
                    print("  curated binding-site residues: MISSING (data gap) -> comparison skipped")
        print(f"\n# {len(plan)} blocks planned")
        return 0

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    done = load_done_blocks(args.output) if args.resume else set()

    n_ok = n_fail = n_skip = 0
    for i, b in enumerate(plan, 1):
        key = (b["block"], b["target_id"])
        if key in done:
            n_skip += 1
            print(f"[{i}/{len(plan)}] {b['block']}:{b['target_id']} resumed-skip", flush=True)
            continue
        print(f"[{i}/{len(plan)}] {b['block']}:{b['target_id']} ...", flush=True)
        started = time.monotonic()
        try:
            if b["block"] == "workflow_run":
                rec = block_workflow_run(b, timeout=args.timeout, env=env)
            elif b["block"] == "known_aptamer_score":
                rec = block_known_aptamer_score(b, timeout=args.timeout)
            elif b["block"] == "hotspot_recovery":
                rec = block_hotspot_recovery(b, cutoff=args.contact_cutoff)
            elif b["block"] == "vegf_case":
                rec = block_vegf_case(b, timeout=args.timeout, env=env, cutoff=args.contact_cutoff)
            else:
                raise ValueError(f"unknown block {b['block']}")
        except Exception as exc:
            rec = {
                "block": b["block"],
                "target_id": b["target_id"],
                "success": False,
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        append_record(args.output, rec)
        if rec.get("success"):
            n_ok += 1
        else:
            n_fail += 1
        print(f"      -> {'OK' if rec.get('success') else 'FAIL(' + str(rec.get('error')) + ')'}",
              flush=True)

    print(f"\nDone: {n_ok} ok, {n_fail} failed, {n_skip} resumed-skip -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
