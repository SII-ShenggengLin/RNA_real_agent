#!/usr/bin/env python3
"""Repair protein structures with missing CB atoms (ODesign featurization blocker).

Context: ODesign's `add_distogram_rep_atom_mask` asserts one representative atom
per token; any non-glycine residue with CA but no CB aborts featurization
(found on 3v03 BSA: LYS-316, ALA-367 are backbone-only).

This script scans `data/benchmarks/RNA-BioBench-Aptamer/structures/*.pdb`,
and for every non-GLY residue missing CB, reconstructs an idealized CB from the
N-CA-C backbone geometry (tetrahedral constraint, |CA-CB| = 1.54 Å, chirality
sign taken from the chain's own intact residues), inserts the atom after CA,
and writes a repaired PDB. Originals are preserved under `structures/originals/`.

CAVEAT: inserted CB lines reuse the CA line's atom serial (serials are not
renumbered). biotite/ODesign and the structure stack here tolerate duplicate
serials; re-run with a renumbering pass if a stricter downstream parser appears.

Usage (from `rna_agent_system/`):
    python experiments/repair_structure_cb.py
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path

import numpy as np

STRUCT_DIR = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
ORIG_DIR = STRUCT_DIR / "originals"
CB_BOND = 1.54


def parse_pdb(path: Path):
    lines = path.read_text().splitlines()
    atoms = []  # (line_idx, chain, resnum, icode, resname, atom_name, xyz)
    for i, line in enumerate(lines):
        if line.startswith(("ATOM", "HETATM")):
            atoms.append({
                "idx": i,
                "chain": line[21],
                "resnum": line[22:26],
                "icode": line[26],
                "resname": line[17:20],
                "atom": line[12:16].strip(),
                "xyz": np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])]),
                "line": line,
            })
    return lines, atoms


def dihedral(p0, p1, p2, p3) -> float:
    b0 = -(p1 - p0)
    b1 = p2 - p1
    b2 = p3 - p2
    b1 /= np.linalg.norm(b1)
    v = b0 - np.dot(b0, b1) * b1
    w = b2 - np.dot(b2, b1) * b1
    x = np.dot(v, w)
    y = np.dot(np.cross(b1, v), w)
    return math.degrees(math.atan2(y, x))


def reconstruct_cb(n, ca, c, sign):
    """Idealized CB: |CB|=1.54 Å, angle(CA_N, CB)=angle(CA_C, CB)=109.47°."""
    u = (n - ca) / np.linalg.norm(n - ca)
    v = (c - ca) / np.linalg.norm(c - ca)
    ctheta = float(np.dot(u, v))
    a = (-1.0 / 3.0) / (1.0 + ctheta)
    w_parallel = a * (u + v)
    p = np.cross(u, v)
    pn = np.linalg.norm(p)
    if pn < 1e-8:
        return None
    p /= pn
    d2 = 1.0 - float(np.dot(w_parallel, w_parallel))
    if d2 <= 0:
        return None
    w = w_parallel + sign * math.sqrt(d2) * p
    return ca + CB_BOND * w


def cb_line(template: str, xyz) -> str:
    """Format a CB ATOM line based on the CA line's metadata."""
    return (
        template[:12]
        + " CB "
        + template[16:30]
        + f"{xyz[0]:8.3f}{xyz[1]:8.3f}{xyz[2]:8.3f}"
        + template[54:]
    )


def repair_file(path: Path) -> tuple[int, list[str]]:
    lines, atoms = parse_pdb(path)
    by_res: dict = {}
    for a in atoms:
        by_res.setdefault((a["chain"], a["resnum"], a["icode"], a["resname"]), []).append(a)

    # chirality sign from intact residues of the same structure
    intact_signs = []
    for key, group in by_res.items():
        names = {a["atom"] for a in group}
        if {"N", "CA", "C", "CB"} <= names:
            g = {a["atom"]: a["xyz"] for a in group}
            intact_signs.append(dihedral(g["N"], g["C"], g["CA"], g["CB"]))
    median_dih = float(np.median(intact_signs)) if intact_signs else 120.0
    sign = 1.0 if median_dih >= 0 else -1.0

    # per-residue missing CB
    insertions: list[tuple[int, str]] = []
    fixed_residues: list[str] = []
    for (chain, resnum, icode, resname), group in by_res.items():
        names = {a["atom"] for a in group}
        if resname == "GLY" or "CB" in names or not {"N", "CA", "C"} <= names:
            continue
        g = {a["atom"]: a["xyz"] for a in group}
        cb = reconstruct_cb(g["N"], g["CA"], g["C"], sign)
        if cb is None:
            continue
        # sanity: dihedral should match chain chirality
        if dihedral(g["N"], g["C"], g["CA"], cb) * sign < 0:
            cb2 = reconstruct_cb(g["N"], g["CA"], g["C"], -sign)
            if cb2 is not None:
                cb = cb2
        ca_line = next(a for a in group if a["atom"] == "CA")
        insertions.append((ca_line["idx"], cb_line(ca_line["line"], cb)))
        fixed_residues.append(f"{resname}{resnum.strip()}:{chain}")

    if not insertions:
        return 0, []
    for idx, newline in sorted(insertions, reverse=True):
        lines.insert(idx + 1, newline)
    ORIG_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, ORIG_DIR / path.name)
    path.write_text("\n".join(lines) + "\n")
    return len(insertions), fixed_residues


def main() -> None:
    for pdb in sorted(STRUCT_DIR.glob("*.pdb")):
        n, residues = repair_file(pdb)
        tag = f"FIXED {n} CB -> {residues}" if n else "ok"
        print(f"{pdb.name}: {tag}")


if __name__ == "__main__":
    main()
