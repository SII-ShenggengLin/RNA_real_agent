"""ViennaRNA microservice: RNAfold, RNAcofold, RNAup, RNAplfold, RNAinverse.

Exposes the five core ViennaRNA tools with parameter parity to the upstream CLI.
Uses Python RNAlib when available, otherwise falls back to ViennaRNA CLI binaries.

"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

try:
    import RNA  # type: ignore

    _HAS_RNALIB = True
except ImportError:
    RNA = None  # type: ignore
    _HAS_RNALIB = False

_RNAFOLD_EXE = shutil.which("RNAfold")
_RNACOFOLD_EXE = shutil.which("RNAcofold")
_RNAUP_EXE = shutil.which("RNAup")
_RNAPLFOLD_EXE = shutil.which("RNAplfold")
_RNAEVAL_EXE = shutil.which("RNAeval")
_RNAINVERSE_EXE = shutil.which("RNAinverse")

# Regex for RNAfold / RNAcofold stdout structure line.
_STRUCTURE_LINE = re.compile(
    r"^([.()[\]{}<>&]+)\s+\(\s*(-?\d+(?:\.\d+)?)\s*\)\s*$"
)

# Upper bound on sequence length for whole-sequence RNAplfold profiles.
_MAX_PLFOLD_PROFILE_SEQ_LEN = 8000


# ═══════════════════════════════════════════════════════════════════════════════
# Shared Pydantic models
# ═══════════════════════════════════════════════════════════════════════════════


class ViennaModelParams(BaseModel):
    """Model-detail parameters shared across all ViennaRNA tools.

    Mirrors the upstream ``vrna_md_t`` / command-line energy-model flags.
    """

    temp_c: float = Field(default=37.0, description="Rescale energy parameters to this temperature (C).")
    dangles: int = Field(default=2, ge=0, le=3, description="Dangling-end model: 0, 1, 2, or 3.")
    noLP: bool = Field(default=False, description="Disallow lonely pairs (helices of length 1).")
    noGU: bool = Field(default=False, description="Do not allow GU pairs.")
    noClosingGU: bool = Field(default=False, description="Do not allow GU pairs at the end of helices.")
    salt: Optional[float] = Field(default=None, description="Salt concentration in molar (M).")
    noTetra: bool = Field(default=False, description="Omit special stabilizing energies for tri-/tetra-/hexaloops.")
    energyModel: Optional[int] = Field(default=None, description="Set energy model (rarely used).")
    nsp: Optional[str] = Field(default=None, description="Allow non-standard pairs, e.g. '-GA'.")
    paramFile: Optional[str] = Field(default=None, description="Custom energy parameter file path (or 'DNA').")


class FoldRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence (plain or FASTA).")
    params: ViennaModelParams = Field(default_factory=ViennaModelParams)
    constraint: Optional[str] = Field(default=None, description="Hard constraint dot-bracket string.")
    shape_file: Optional[str] = Field(default=None, description="Path to SHAPE reactivity data file.")
    shape_method: str = Field(default="D", description="SHAPE method: D, Z, or W.")
    partfunc: bool = Field(default=False, description="Compute partition function and centroid.")
    circ: bool = Field(default=False, description="Assume circular RNA.")
    gquad: bool = Field(default=False, description="Include G-quadruplex formation.")


class FoldResponse(BaseModel):
    sequence: str
    structure: str
    mfe: float
    backend: str
    model: str = "ViennaRNA-RNAfold"
    ensemble_free_energy: Optional[float] = None
    centroid_structure: Optional[str] = None
    centroid_distance: Optional[float] = None
    mea_structure: Optional[str] = None
    mea_score: Optional[float] = None
    mea_gamma: Optional[float] = None


class SirnaDuplexRequest(BaseModel):
    sense: Optional[str] = Field(default=None, description="Sense strand 5'→3'.")
    antisense: Optional[str] = Field(default=None, description="Antisense strand 5'→3'.")
    fasta_content: Optional[str] = Field(default=None, description="Two FASTA records: sense then antisense.")
    params: ViennaModelParams = Field(default_factory=ViennaModelParams)
    constraint: Optional[str] = Field(default=None, description="Hard constraint dot-bracket string.")
    shape_file: Optional[str] = Field(default=None, description="Path to SHAPE reactivity data file.")
    shape_method: str = Field(default="D", description="SHAPE method: D, Z, or W.")
    concentrations: bool = Field(default=False, description="Compute equilibrium concentrations (requires conc_A / conc_B).")
    conc_A: Optional[float] = Field(default=None, description="Initial monomer A concentration [mol/L].")
    conc_B: Optional[float] = Field(default=None, description="Initial monomer B concentration [mol/L].")
    partfunc: bool = Field(default=False, description="Compute partition function for dimer.")

    @model_validator(mode="after")
    def _check_seq_source(self) -> "SirnaDuplexRequest":
        if not self.fasta_content and (self.sense is None or self.antisense is None):
            raise ValueError("Provide either (sense + antisense) or fasta_content.")
        if self.concentrations and (self.conc_A is None or self.conc_B is None):
            raise ValueError("concentrations=True requires both conc_A and conc_B.")
        return self


class SirnaDuplexResponse(BaseModel):
    sense: str
    antisense: str
    cofold_sequence: str
    structure: str
    mfe: float
    backend: str
    model: str = "ViennaRNA-RNAcofold"
    ensemble_free_energy: Optional[float] = None
    equilibrium_concentrations: Optional[Dict[str, float]] = None
    # End-thermodynamic asymmetry (additive, v0.5.0); None when no evaluation
    # backend is available (older service instances simply omit these keys).
    dg_sense_5p_end_kcal_per_mol: Optional[float] = None
    dg_antisense_5p_end_kcal_per_mol: Optional[float] = None
    asymmetry_kcal_per_mol: Optional[float] = None
    asymmetry_convention: Optional[str] = None


class RnaUpRequest(BaseModel):
    sequence1: str = Field(..., min_length=1, description="First RNA sequence (target, typically longer).")
    sequence2: str = Field(..., min_length=1, description="Second RNA sequence (probe / small RNA).")
    params: ViennaModelParams = Field(default_factory=ViennaModelParams)
    ulength: int = Field(default=4, ge=1, le=100, description="Length of unstructured region in output (-u).")
    window: int = Field(default=25, ge=1, le=1000, description="Maximal length of interaction region (-w).")
    include_both: bool = Field(default=False, description="Include unpaired probabilities in both RNAs (-b).")
    extend5: int = Field(default=0, ge=0, description="Extend interaction on 5' side of target (-5).")
    extend3: int = Field(default=0, ge=0, description="Extend interaction on 3' side of target (-3).")
    contributions: str = Field(default="S", description="Contributions to output: S, H, I, M, E or any combination (-c).")
    constraint1: Optional[str] = Field(default=None, description="Hard constraint for sequence1.")
    constraint2: Optional[str] = Field(default=None, description="Hard constraint for sequence2.")


class RnaUpResponse(BaseModel):
    sequence1: str
    sequence2: str
    interaction_energy: Optional[float] = None
    interaction_structure: Optional[str] = None
    raw_stdout: str
    backend: str
    model: str = "ViennaRNA-RNAup"


class AsoAccessibilityRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="Full target RNA in plain or FASTA text.")
    region_start: int = Field(..., ge=1, description="1-based inclusive start of binding region.")
    region_end: int = Field(..., ge=1, description="1-based inclusive end of binding region.")
    aso_oligo_length: int = Field(default=18, ge=1, le=500, description="ASO length for joint unpaired probability.")
    params: ViennaModelParams = Field(default_factory=ViennaModelParams)
    winsize: int = Field(default=70, ge=3, le=800, description="RNAplfold -W window size.")
    span: int = Field(default=70, ge=2, le=800, description="RNAplfold -L max pair span.")
    unpaired_ulength: int = Field(default=25, ge=1, le=500, description="RNAplfold -u upper bound.")
    cutoff: Optional[float] = Field(default=None, description="RNAplfold -c probability cutoff.")
    opening_energies: bool = Field(default=False, description="RNAplfold -O: return logarithms (opening energies).")


class AsoAccessibilityResponse(BaseModel):
    sequence_length: int
    region_start: int
    region_end: int
    mean_unpaired_prob_single_nt: Optional[float] = None
    joint_unpaired_prob_stretch_ending_at_region_end: Optional[float] = None
    aso_oligo_length_used: int
    winsize: int
    span: int
    unpaired_ulength: int
    backend: str
    model: str = "ViennaRNA-RNAplfold"


class PlfoldProfilesRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence (plain or FASTA body).")
    params: ViennaModelParams = Field(default_factory=ViennaModelParams)
    winsize: int = Field(default=70, ge=3, le=800, description="RNAplfold -W window size.")
    span: int = Field(default=70, ge=2, le=800, description="RNAplfold -L max pair span.")
    unpaired_ulength: int = Field(default=25, ge=1, le=500, description="RNAplfold -u upper bound.")
    cutoff: Optional[float] = Field(default=None, description="RNAplfold -c probability cutoff.")
    opening_energies: bool = Field(default=False, description="RNAplfold -O: return logarithms (opening energies).")


class PlfoldProfilesResponse(BaseModel):
    sequence_length: int
    positions: List[int] = Field(..., description="1-based positions with lunp rows.")
    unpaired_prob_1nt: List[float] = Field(..., description="Local unpaired probability per position.")
    winsize: int
    span: int
    unpaired_ulength_effective: int
    mean_unpaired_prob_1nt: float
    min_unpaired_prob_1nt: float
    max_unpaired_prob_1nt: float
    backend: str
    model: str = "ViennaRNA-RNAplfold"


class InverseFoldRequest(BaseModel):
    structure: str = Field(..., min_length=1, description="Target secondary structure in dot-bracket notation.")
    start_sequence: str = Field(default="", description="Optional IUPAC hint; N = randomizable. Empty = all-N.")
    params: ViennaModelParams = Field(default_factory=ViennaModelParams)
    repeats: int = Field(default=1, ge=1, le=500, description="RNAinverse -R repeats.")
    function_mode: str = Field(default="m", description="RNAinverse -F: m (MFE), p (partition), or mp.")
    final_cost: Optional[float] = Field(default=None, description="RNAinverse -f: stop threshold for -Fp.")
    alphabet: Optional[str] = Field(default=None, description="RNAinverse -a: custom nucleotide alphabet.")


class InverseFoldResponse(BaseModel):
    structure: str
    best_sequence: str
    hamming_distance: Optional[int] = None
    partition_probability: Optional[float] = None
    backend: str
    model: str = "ViennaRNA-RNAinverse"


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _normalize_rna(seq: str) -> str:
    merged = "".join(seq.split()).upper().replace("T", "U")
    return "".join(ch for ch in merged if ch in "AUGC")


def _seq_from_text(text: str) -> str:
    """Extract sequence from plain or FASTA text."""
    return _normalize_rna(
        "".join(
            ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith(">")
        )
    )


def _run_cli(cmd: List[str], stdin: Optional[str] = None, cwd: Optional[str] = None) -> Tuple[str, str, int]:
    proc = subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )
    return proc.stdout, proc.stderr, proc.returncode


def _apply_md_params(params: ViennaModelParams) -> Any:
    """Build an RNA.md() object from ViennaModelParams."""
    if not _HAS_RNALIB:
        return None
    md = RNA.md()
    md.temperature = params.temp_c
    md.dangles = params.dangles
    if params.noLP:
        md.noLP = 1
    if params.noGU:
        md.noGU = 1
    if params.noClosingGU:
        md.noClosingGU = 1
    if params.salt is not None:
        md.salt = params.salt
    if params.noTetra:
        md.special_hp = 0
    if params.energyModel is not None:
        md.energy_set = params.energyModel
    if params.nsp is not None:
        md.nsp = params.nsp
    return md


def _build_rnafold_cli_args(params: ViennaModelParams, constraint: Optional[str], shape_file: Optional[str], shape_method: str, partfunc: bool, circ: bool, gquad: bool) -> List[str]:
    cmd: List[str] = [_RNAFOLD_EXE, "--noPS"]
    cmd += ["-T", str(params.temp_c)]
    cmd += ["-d", str(params.dangles)]
    if params.noLP:
        cmd.append("--noLP")
    if params.noGU:
        cmd.append("--noGU")
    if params.noClosingGU:
        cmd.append("--noClosingGU")
    if params.salt is not None:
        cmd += ["--salt", str(params.salt)]
    if params.noTetra:
        cmd.append("-4")
    if params.energyModel is not None:
        cmd += ["--energyModel", str(params.energyModel)]
    if params.nsp is not None:
        cmd += ["--nsp", params.nsp]
    if params.paramFile is not None:
        cmd += ["-P", params.paramFile]
    if constraint is not None:
        cmd.append("-C")
    if shape_file is not None:
        cmd += ["--shape", shape_file, "--shapeMethod", shape_method]
    if partfunc:
        cmd.append("-p")
    if circ:
        cmd.append("--circ")
    if gquad:
        cmd.append("--gquad")
    return cmd


def _build_rnacofold_cli_args(params: ViennaModelParams, constraint: Optional[str], shape_file: Optional[str], shape_method: str, concentrations: bool, partfunc: bool) -> List[str]:
    cmd: List[str] = [_RNACOFOLD_EXE, "--noPS"]
    cmd += ["-T", str(params.temp_c)]
    cmd += ["-d", str(params.dangles)]
    if params.noLP:
        cmd.append("--noLP")
    if params.noGU:
        cmd.append("--noGU")
    if params.noClosingGU:
        cmd.append("--noClosingGU")
    if params.salt is not None:
        cmd += ["--salt", str(params.salt)]
    if params.noTetra:
        cmd.append("-4")
    if params.energyModel is not None:
        cmd += ["--energyModel", str(params.energyModel)]
    if params.nsp is not None:
        cmd += ["--nsp", params.nsp]
    if params.paramFile is not None:
        cmd += ["-P", params.paramFile]
    if constraint is not None:
        cmd.append("-C")
    if shape_file is not None:
        cmd += ["--shape", shape_file, "--shapeMethod", shape_method]
    if concentrations:
        cmd.append("-c")
    if partfunc:
        cmd.append("-p")
    return cmd


def _build_rnaup_cli_args(params: ViennaModelParams, ulength: int, window: int, include_both: bool, extend5: int, extend3: int, contributions: str) -> List[str]:
    cmd: List[str] = [_RNAUP_EXE, "--no_output_file"]
    cmd += ["-T", str(params.temp_c)]
    cmd += ["-d", str(params.dangles)]
    if params.noLP:
        cmd.append("--noLP")
    if params.noGU:
        cmd.append("--noGU")
    if params.noClosingGU:
        cmd.append("--noClosingGU")
    if params.salt is not None:
        cmd += ["--salt", str(params.salt)]
    if params.noTetra:
        cmd.append("-4")
    if params.energyModel is not None:
        cmd += ["--energyModel", str(params.energyModel)]
    if params.nsp is not None:
        cmd += ["--nsp", params.nsp]
    if params.paramFile is not None:
        cmd += ["-P", params.paramFile]
    cmd += ["-u", str(ulength)]
    cmd += ["-w", str(window)]
    if include_both:
        cmd.append("-b")
    if extend5:
        cmd += ["-5", str(extend5)]
    if extend3:
        cmd += ["-3", str(extend3)]
    cmd += ["-c", contributions]
    return cmd


def _build_rnaplfold_cli_args(params: ViennaModelParams, winsize: int, span: int, ulength: int, cutoff: Optional[float], opening_energies: bool) -> List[str]:
    cmd: List[str] = [_RNAPLFOLD_EXE]
    cmd += ["-T", str(params.temp_c)]
    cmd += ["-d", str(params.dangles)]
    if params.noLP:
        cmd.append("--noLP")
    if params.noGU:
        cmd.append("--noGU")
    if params.noClosingGU:
        cmd.append("--noClosingGU")
    if params.salt is not None:
        cmd += ["--salt", str(params.salt)]
    if params.noTetra:
        cmd.append("-4")
    if params.energyModel is not None:
        cmd += ["--energyModel", str(params.energyModel)]
    if params.nsp is not None:
        cmd += ["--nsp", params.nsp]
    if params.paramFile is not None:
        cmd += ["-P", params.paramFile]
    cmd += ["-W", str(winsize)]
    cmd += ["-L", str(span)]
    cmd += ["-u", str(ulength)]
    if cutoff is not None:
        cmd += ["-c", str(cutoff)]
    if opening_energies:
        cmd.append("-O")
    return cmd


def _build_rnainverse_cli_args(params: ViennaModelParams, function_mode: str, repeats: int, final_cost: Optional[float], alphabet: Optional[str]) -> List[str]:
    cmd: List[str] = [_RNAINVERSE_EXE]
    cmd += ["-T", str(params.temp_c)]
    cmd += ["-d", str(params.dangles)]
    if params.noGU:
        cmd.append("--noGU")
    if params.noClosingGU:
        cmd.append("--noClosingGU")
    if params.salt is not None:
        cmd += ["--salt", str(params.salt)]
    if params.noTetra:
        cmd.append("-4")
    if params.energyModel is not None:
        cmd += ["--energyModel", str(params.energyModel)]
    if params.nsp is not None:
        cmd += ["--nsp", params.nsp]
    if params.paramFile is not None:
        cmd += ["-P", params.paramFile]
    cmd += [f"-F{function_mode}"]
    cmd += [f"-R{repeats}"]
    if final_cost is not None:
        cmd += ["-f", str(final_cost)]
    if alphabet is not None:
        cmd += ["-a", alphabet]
    return cmd


# ═══════════════════════════════════════════════════════════════════════════════
# RNAfold
# ═══════════════════════════════════════════════════════════════════════════════


def _fold_sequence_rnafold_cli(sequence: str, params: ViennaModelParams, constraint: Optional[str] = None, shape_file: Optional[str] = None, shape_method: str = "D", partfunc: bool = False, circ: bool = False, gquad: bool = False) -> Dict[str, Any]:
    if not _RNAFOLD_EXE:
        raise RuntimeError("`RNAfold` executable not found in PATH.")
    cmd = _build_rnafold_cli_args(params, constraint, shape_file, shape_method, partfunc, circ, gquad)
    stdin = sequence + "\n"
    if constraint is not None:
        stdin += constraint + "\n"
    stdout, stderr, rc = _run_cli(cmd, stdin=stdin)
    if rc != 0:
        err = (stderr or stdout or "").strip()
        raise RuntimeError(f"RNAfold failed (exit {rc}): {err}")

    result: Dict[str, Any] = {"backend": "RNAfold-cli"}
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    for line in reversed(lines):
        if line.startswith(">"):
            continue
        m = _STRUCTURE_LINE.match(line)
        if m:
            result["structure"] = m.group(1)
            result["mfe"] = float(m.group(2))
            break
    if "structure" not in result:
        raise RuntimeError("Could not parse RNAfold output.")
    for line in lines:
        if line.startswith("[") and "=" in line:
            mea_match = re.search(r"=\s*(-?\d+(?:\.\d+)?)\s*\(gamma=\s*([\d.]+)\)", line)
            if mea_match:
                result["mea_structure"] = line.split()[0]
                result["mea_score"] = float(mea_match.group(1))
                result["mea_gamma"] = float(mea_match.group(2))
        elif "free energy of ensemble" in line:
            fe_match = re.search(r"=\s*(-?\d+(?:\.\d+)?)", line)
            if fe_match:
                result["ensemble_free_energy"] = float(fe_match.group(1))
        elif line.startswith("{") and "distance" in line:
            cd_match = re.search(r"\{\s*([.()[\]{}<>]+)\s*\}\s*\(\s*(-?\d+(?:\.\d+)?)\s*\)\s+distance\s*=\s*([\d.]+)", line)
            if cd_match:
                result["centroid_structure"] = cd_match.group(1)
                result["centroid_free_energy"] = float(cd_match.group(2))
                result["centroid_distance"] = float(cd_match.group(3))
    return result


def _fold_sequence_rnalib(sequence: str, params: ViennaModelParams, constraint: Optional[str] = None, partfunc: bool = False, circ: bool = False, gquad: bool = False) -> Dict[str, Any]:
    if not _HAS_RNALIB:
        raise RuntimeError("RNAlib is not available.")
    md = _apply_md_params(params)
    if circ:
        md.circ = 1
    if gquad:
        md.gquad = 1
    fc = RNA.fold_compound(sequence, md)
    if constraint is not None:
        fc.hc_add_from_db(constraint)
    structure, mfe = fc.mfe()
    result: Dict[str, Any] = {
        "structure": str(structure),
        "mfe": float(mfe),
        "backend": "RNAlib",
    }
    if partfunc:
        try:
            fc.pf()
            result["ensemble_free_energy"] = float(fc.pf()[1])
            centroid_struct, centroid_dist = fc.centroid()
            result["centroid_structure"] = str(centroid_struct)
            result["centroid_distance"] = float(centroid_dist)
        except Exception:
            pass
    return result


def _fold_sequence(sequence: str, params: ViennaModelParams, constraint: Optional[str] = None, shape_file: Optional[str] = None, shape_method: str = "D", partfunc: bool = False, circ: bool = False, gquad: bool = False) -> Dict[str, Any]:
    if _HAS_RNALIB:
        return _fold_sequence_rnalib(sequence, params, constraint, partfunc, circ, gquad)
    return _fold_sequence_rnafold_cli(sequence, params, constraint, shape_file, shape_method, partfunc, circ, gquad)


# ═══════════════════════════════════════════════════════════════════════════════
# RNAcofold
# ═══════════════════════════════════════════════════════════════════════════════


def _cofold_duplex_cli(sense: str, antisense: str, params: ViennaModelParams, constraint: Optional[str] = None, shape_file: Optional[str] = None, shape_method: str = "D", concentrations: bool = False, partfunc: bool = False, conc_A: Optional[float] = None, conc_B: Optional[float] = None) -> Dict[str, Any]:
    if not _RNACOFOLD_EXE:
        raise RuntimeError("`RNAcofold` executable not found in PATH.")
    cmd = _build_rnacofold_cli_args(params, constraint, shape_file, shape_method, concentrations, partfunc)
    combined = f"{sense}&{antisense}"
    stdin = combined + "\n"
    if constraint is not None:
        stdin += constraint + "\n"
    if concentrations and conc_A is not None and conc_B is not None:
        stdin += f"{conc_A} {conc_B}\n"
    stdout, stderr, rc = _run_cli(cmd, stdin=stdin)
    if rc != 0:
        err = (stderr or stdout or "").strip()
        raise RuntimeError(f"RNAcofold failed (exit {rc}): {err}")

    result: Dict[str, Any] = {"backend": "RNAcofold-cli", "sense": sense, "antisense": antisense, "cofold_sequence": combined}
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    for line in reversed(lines):
        if line.startswith(">"):
            continue
        m = _STRUCTURE_LINE.match(line)
        if m:
            result["structure"] = m.group(1)
            result["mfe"] = float(m.group(2))
            break
    if "structure" not in result:
        raise RuntimeError("Could not parse RNAcofold output.")
    if concentrations:
        equi: Dict[str, float] = {}
        # Try old "AA = 0.5" format first
        for line in lines:
            for species in ["AA", "AB", "BB", "A", "B"]:
                mm = re.search(rf"{species}\s*=\s*([\d.eE+-]+)", line)
                if mm:
                    equi[species] = float(mm.group(1))
        # ViennaRNA >=2.7 prints tabular equilibrium concentrations
        if not equi:
            header_idx: Optional[int] = None
            for i, line in enumerate(lines):
                if "relative Equilibrium concentrations" in line or "Equilibrium concentrations" in line:
                    header_idx = i
                    break
            if header_idx is not None and header_idx + 2 < len(lines):
                header_parts = [p.strip() for p in lines[header_idx + 1].split("\t") if p.strip()]
                value_parts = [p.strip() for p in lines[header_idx + 2].split("\t") if p.strip()]
                # Map each species to its rightmost occurrence (equilibrium values come after initial)
                for species in ["A", "B", "AB", "AA", "BB"]:
                    for h, v in zip(reversed(header_parts), reversed(value_parts)):
                        if h == species:
                            try:
                                equi[species] = float(v)
                            except ValueError:
                                pass
                            break
        if equi:
            result["equilibrium_concentrations"] = equi
    return result


def _cofold_duplex_rnalib(sense: str, antisense: str, params: ViennaModelParams, constraint: Optional[str] = None, partfunc: bool = False) -> Dict[str, Any]:
    if not _HAS_RNALIB:
        raise RuntimeError("RNAlib is not available.")
    md = _apply_md_params(params)
    combined = f"{sense}&{antisense}"
    fc = RNA.fold_compound(combined, md)
    if constraint is not None:
        fc.hc_add_from_db(constraint)
    structure, mfe = fc.mfe_dimer()
    result: Dict[str, Any] = {
        "structure": str(structure),
        "mfe": float(mfe),
        "backend": "RNAlib",
        "sense": sense,
        "antisense": antisense,
        "cofold_sequence": combined,
    }
    if partfunc:
        try:
            pf_result = fc.pf_dimer()
            result["ensemble_free_energy"] = float(pf_result[2]) if len(pf_result) > 2 else None
        except Exception:
            pass
    return result


def _cofold_duplex(sense: str, antisense: str, params: ViennaModelParams, constraint: Optional[str] = None, shape_file: Optional[str] = None, shape_method: str = "D", concentrations: bool = False, partfunc: bool = False, conc_A: Optional[float] = None, conc_B: Optional[float] = None) -> Dict[str, Any]:
    # RNAlib does not support equilibrium concentration calculations.
    # Fall back to CLI whenever concentrations are requested.
    if _HAS_RNALIB and not concentrations:
        return _cofold_duplex_rnalib(sense, antisense, params, constraint, partfunc)
    return _cofold_duplex_cli(sense, antisense, params, constraint, shape_file, shape_method, concentrations, partfunc, conc_A, conc_B)


def _eval_miniduplex_kcal(seq_a: str, seq_b: str, params: ViennaModelParams) -> Optional[float]:
    """Energy (kcal/mol) of the fully paired mini-duplex ``seq_a&seq_b``.

    Nearest-neighbour table evaluation only (no folding). Both termini of an
    end-stability comparison are evaluated with this identical method, so the
    systematic initiation terms cancel in the difference. RNAlib first,
    RNAeval CLI fallback, ``None`` when neither backend is available.
    """
    k = len(seq_a)
    seq = f"{seq_a}&{seq_b}"
    struct = "(" * k + "&" + ")" * k
    if _HAS_RNALIB:
        try:
            return float(RNA.eval_structure_simple(seq, struct, temperature=params.temp_c))
        except Exception:
            pass
    if _RNAEVAL_EXE:
        try:
            out, _err, rc = _run_cli(
                [_RNAEVAL_EXE, "--temp", str(params.temp_c)],
                stdin=f"{seq}\n{struct}\n",
            )
            if rc == 0:
                m = re.search(r"\(\s*(-?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*\)", out)
                if m:
                    return float(m.group(1))
        except Exception:
            return None
    return None


def _duplex_end_asymmetry(
    sense: str, antisense: str, params: ViennaModelParams, end_nt: int = 5
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Thermodynamic end asymmetry of a (near-fully-paired) siRNA duplex.

    Classical RISC-loading criterion (Khvorova et al. 2003; Schwarz et al.
    2003): the strand whose 5' end is less stable is preferentially loaded as
    the guide. Returns ``(dg_sense_5p, dg_antisense_5p, asymmetry)`` where
    each end dG is the NN evaluation of the terminal ``end_nt`` base pairs
    (5 nt of each strand, antiparallel) and
    ``asymmetry = dg_antisense_5p - dg_sense_5p``; **higher = better** (the
    antisense 5' end is the less stable one, so the antisense strand wins
    strand selection). ``None`` components when the strands are shorter than
    ``end_nt`` or no evaluation backend is available.
    """
    if len(sense) < end_nt or len(antisense) < end_nt:
        return None, None, None
    dg_sense_5p = _eval_miniduplex_kcal(sense[:end_nt], antisense[-end_nt:], params)
    dg_anti_5p = _eval_miniduplex_kcal(antisense[:end_nt], sense[-end_nt:], params)
    if dg_sense_5p is None or dg_anti_5p is None:
        return None, None, None
    return dg_sense_5p, dg_anti_5p, round(dg_anti_5p - dg_sense_5p, 4)


# ═══════════════════════════════════════════════════════════════════════════════
# RNAup
# ═══════════════════════════════════════════════════════════════════════════════


def _run_rnaup_cli(seq1: str, seq2: str, params: ViennaModelParams, ulength: int, window: int, include_both: bool, extend5: int, extend3: int, contributions: str, constraint1: Optional[str] = None, constraint2: Optional[str] = None) -> Dict[str, Any]:
    if not _RNAUP_EXE:
        raise RuntimeError("`RNAup` executable not found in PATH.")
    cmd = _build_rnaup_cli_args(params, ulength, window, include_both, extend5, extend3, contributions)
    stdin = f"{seq1}&{seq2}\n"
    if constraint1 is not None:
        stdin += constraint1 + "\n"
    if constraint2 is not None:
        stdin += constraint2 + "\n"
    stdout, stderr, rc = _run_cli(cmd, stdin=stdin)
    if rc != 0:
        err = (stderr or stdout or "").strip()
        raise RuntimeError(f"RNAup failed (exit {rc}): {err}")

    result: Dict[str, Any] = {
        "sequence1": seq1,
        "sequence2": seq2,
        "backend": "RNAup-cli",
        "raw_stdout": stdout,
    }
    best_energy: Optional[float] = None
    best_struct: Optional[str] = None
    for line in stdout.splitlines():
        line = line.strip()
        # RNAup pairwise mode prints structure line first:
        #   (((((((((&)))))))))   1,9   :   1,9   (-13.88 = -15.50 + 1.62)
        # followed by sequence line:
        #   GGGAAACCC&GGGUUUCCC
        m = re.search(r"([.()[\]{}<>]+&[.()[\]{}<>]+)\s+.*?\(\s*(-?\d+(?:\.\d+)?)\s*=", line)
        if m:
            best_struct = m.group(1)
            best_energy = float(m.group(2))
            continue
        # Fallback: try standard structure+energy line
        if not line.startswith("#") and not line.startswith(">"):
            mm = _STRUCTURE_LINE.match(line)
            if mm:
                best_struct = mm.group(1)
                best_energy = float(mm.group(2))
    if best_energy is not None:
        result["interaction_energy"] = best_energy
    if best_struct is not None:
        result["interaction_structure"] = best_struct
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# RNAplfold
# ═══════════════════════════════════════════════════════════════════════════════


def _parse_lunp_row(line: str) -> Optional[Tuple[int, List[float]]]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = stripped.split()
    try:
        pos = int(parts[0])
    except ValueError:
        return None
    probs: List[float] = []
    for p in parts[1:]:
        try:
            probs.append(float(p))
        except ValueError:
            # RNAplfold prints "NA" for unavailable lengths; skip them
            continue
    return pos, probs


def _run_plfold_accessibility_cli(sequence: str, params: ViennaModelParams, winsize: int, span: int, ulength: int, cutoff: Optional[float] = None, opening_energies: bool = False) -> Tuple[List[Tuple[int, List[float]]], str]:
    seq = _normalize_rna(sequence)
    if len(seq) < 10:
        raise ValueError("sequence too short for meaningful RNAplfold accessibility (need at least ~10 nt).")
    winsize = max(3, min(winsize, len(seq)))
    span = max(2, min(span, winsize))
    ulength = max(1, min(ulength, len(seq), 400))

    if not _RNAPLFOLD_EXE:
        raise RuntimeError("`RNAplfold` not found in PATH.")

    with tempfile.TemporaryDirectory(prefix="vienna_plfold_") as tmp:
        tdir = Path(tmp)
        fasta_path = tdir / "query.fa"
        fasta_path.write_text(f">query\n{seq}\n", encoding="utf-8")
        cmd = _build_rnaplfold_cli_args(params, winsize, span, ulength, cutoff, opening_energies)
        stdout, stderr, rc = _run_cli(cmd, stdin=fasta_path.read_text(encoding="utf-8"), cwd=str(tdir))
        if rc != 0:
            err = (stderr or stdout or "").strip()
            raise RuntimeError(f"RNAplfold failed (exit {rc}): {err}")
        lunp_path = tdir / "query_lunp"
        if not lunp_path.is_file():
            raise RuntimeError(
                f"RNAplfold did not produce expected `query_lunp` in temp dir (files: {list(tdir.iterdir())})."
            )
        rows_out: List[Tuple[int, List[float]]] = []
        for line in lunp_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_lunp_row(line)
            if parsed:
                rows_out.append(parsed)
        return rows_out, "RNAplfold-cli"


def _region_accessibility_from_lunp(rows: List[Tuple[int, List[float]]], region_start: int, region_end: int, aso_length: int) -> Dict[str, Any]:
    if region_start < 1 or region_end < region_start:
        raise ValueError("region_start must be >= 1 and region_end must be >= region_start.")
    rlen = region_end - region_start + 1
    row_map = {pos: probs for pos, probs in rows}
    singles: List[float] = []
    for pos in range(region_start, region_end + 1):
        probs = row_map.get(pos)
        if probs:
            singles.append(probs[0])
    mean_single = sum(singles) / len(singles) if singles else None
    joint: Optional[float] = None
    if aso_length <= 0:
        aso_length = rlen
    aso_length = min(aso_length, rlen)
    end_pos = region_end
    probs_end = row_map.get(end_pos)
    if probs_end and len(probs_end) >= aso_length:
        joint = probs_end[aso_length - 1]
    return {
        "region_nt_length": rlen,
        "aso_oligo_length_used": aso_length,
        "mean_unpaired_prob_single_nt": mean_single,
        "joint_unpaired_prob_stretch_ending_at_region_end": joint,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RNAinverse
# ═══════════════════════════════════════════════════════════════════════════════


def _inverse_fold_cli(structure: str, start_sequence: str, params: ViennaModelParams, repeats: int, function_mode: str, final_cost: Optional[float] = None, alphabet: Optional[str] = None) -> Dict[str, Any]:
    if not _RNAINVERSE_EXE:
        raise RuntimeError("`RNAinverse` executable not found in PATH.")
    struct = structure.strip()
    if not struct:
        raise ValueError("structure must be non-empty dot-bracket string.")
    allowed = set(".()[]{}<>")
    if any(ch not in allowed for ch in struct):
        raise ValueError("structure contains characters outside dot-bracket notation.")
    if any(ch not in ".()" for ch in struct):
        # RNAinverse cannot parse pseudoknot brackets: depending on the
        # ViennaRNA build it either exits with "Junk in structure" or crashes
        # outright (observed exit -11 in the packaged service env). Reject
        # up-front with an actionable message instead.
        raise ValueError(
            "RNAinverse does not support pseudoknot brackets ([]{}<>); "
            "provide a pseudoknot-free dot-bracket target (only '.' and '()')."
        )
    start = start_sequence.strip() if start_sequence else ""
    if not start:
        start = "N" * len(struct)
    elif len(start) < len(struct):
        start = start + "N" * (len(struct) - len(start))
    elif len(start) > len(struct):
        start = start[: len(struct)]

    fm = function_mode if function_mode in {"m", "p", "mp"} else "m"
    cmd = _build_rnainverse_cli_args(params, fm, repeats, final_cost, alphabet)
    stdin = f"{struct}\n{start}\n@\n"
    stdout, stderr, rc = _run_cli(cmd, stdin=stdin)
    if rc != 0:
        err = (stderr or stdout or "").strip()
        raise RuntimeError(f"RNAinverse failed (exit {rc}): {err}")
    out_lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    if not out_lines:
        raise RuntimeError("RNAinverse produced no stdout.")
    first = out_lines[0]
    parts = first.split()
    if not parts:
        raise RuntimeError(f"Unexpected RNAinverse output line: {first!r}")
    best_seq = parts[0].upper().replace("T", "U")
    hamming: Optional[int] = None
    partition_prob: Optional[float] = None
    if len(parts) > 1 and parts[1].isdigit():
        hamming = int(parts[1])
    if len(parts) > 2 and parts[2].startswith("("):
        pp_match = re.search(r"\(\s*([\d.eE+-]+)\s*\)", parts[2])
        if pp_match:
            partition_prob = float(pp_match.group(1))
    return {
        "best_sequence": best_seq,
        "hamming_distance": hamming,
        "partition_probability": partition_prob,
        "backend": "RNAinverse-cli",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI app
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ViennaRNA Service",
    description="RNAfold, RNAcofold, RNAup, RNAplfold, RNAinverse with full upstream parameter parity.",
    version="0.4.0-port8003",
)


@app.get("/health")
def health() -> dict[str, Any]:
    fold_ok = _HAS_RNALIB or bool(_RNAFOLD_EXE)
    return {
        "status": "ok" if fold_ok else "degraded",
        "rnalib": _HAS_RNALIB,
        "rnafold_cli": bool(_RNAFOLD_EXE),
        "rnacofold_cli": bool(_RNACOFOLD_EXE),
        "rnaup_cli": bool(_RNAUP_EXE),
        "rnaplfold_cli": bool(_RNAPLFOLD_EXE),
        "rnainverse_cli": bool(_RNAINVERSE_EXE),
    }


@app.post("/fold", response_model=FoldResponse)
def fold(payload: FoldRequest) -> FoldResponse:
    sequence = _seq_from_text(payload.sequence)
    if not sequence:
        raise HTTPException(status_code=400, detail="No RNA letters after normalization.")
    if not _HAS_RNALIB and not _RNAFOLD_EXE:
        raise HTTPException(status_code=503, detail="ViennaRNA is not available.")
    try:
        result = _fold_sequence(
            sequence,
            payload.params,
            constraint=payload.constraint,
            shape_file=payload.shape_file,
            shape_method=payload.shape_method,
            partfunc=payload.partfunc,
            circ=payload.circ,
            gquad=payload.gquad,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Fold failed: {exc}") from exc

    return FoldResponse(
        sequence=sequence,
        structure=result["structure"],
        mfe=result["mfe"],
        backend=result["backend"],
        ensemble_free_energy=result.get("ensemble_free_energy"),
        centroid_structure=result.get("centroid_structure"),
        centroid_distance=result.get("centroid_distance"),
        mea_structure=result.get("mea_structure"),
        mea_score=result.get("mea_score"),
        mea_gamma=result.get("mea_gamma"),
    )


@app.post("/sirna-duplex", response_model=SirnaDuplexResponse)
def sirna_duplex(payload: SirnaDuplexRequest) -> SirnaDuplexResponse:
    sense: Optional[str] = None
    anti: Optional[str] = None
    if payload.fasta_content:
        records: List[Tuple[str, str]] = []
        hdr: Optional[str] = None
        chunks: List[str] = []
        for line in payload.fasta_content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if hdr is not None and chunks:
                    records.append((hdr, _normalize_rna("".join(chunks))))
                hdr = line[1:].strip().split()[0] if len(line) > 1 else "seq"
                chunks = []
            else:
                chunks.append(line)
        if hdr is not None and chunks:
            records.append((hdr, _normalize_rna("".join(chunks))))
        if len(records) < 2:
            raise HTTPException(status_code=400, detail="fasta_content must contain at least two FASTA records.")
        sense, anti = records[0][1], records[1][1]
    elif payload.sense is not None and payload.antisense is not None:
        sense = _normalize_rna(payload.sense)
        anti = _normalize_rna(payload.antisense)
    else:
        raise HTTPException(status_code=400, detail="Provide either (sense + antisense) or fasta_content with two FASTA records.")

    if not sense or not anti:
        raise HTTPException(status_code=400, detail="sense and antisense must be non-empty RNA sequences.")
    if not _HAS_RNALIB and not _RNACOFOLD_EXE:
        raise HTTPException(status_code=503, detail="Duplex prediction needs RNAlib or RNAcofold on PATH.")
    try:
        result = _cofold_duplex(
            sense, anti, payload.params,
            constraint=payload.constraint,
            shape_file=payload.shape_file,
            shape_method=payload.shape_method,
            concentrations=payload.concentrations,
            partfunc=payload.partfunc,
            conc_A=payload.conc_A,
            conc_B=payload.conc_B,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Duplex cofold failed: {exc}") from exc
    dg_sense_5p, dg_anti_5p, asymmetry = _duplex_end_asymmetry(sense, anti, payload.params)
    return SirnaDuplexResponse(
        sense=sense,
        antisense=anti,
        cofold_sequence=result["cofold_sequence"],
        structure=result["structure"],
        mfe=result["mfe"],
        backend=result["backend"],
        ensemble_free_energy=result.get("ensemble_free_energy"),
        equilibrium_concentrations=result.get("equilibrium_concentrations"),
        dg_sense_5p_end_kcal_per_mol=dg_sense_5p,
        dg_antisense_5p_end_kcal_per_mol=dg_anti_5p,
        asymmetry_kcal_per_mol=asymmetry,
        asymmetry_convention=(
            "asymmetry = dg_antisense_5p - dg_sense_5p (terminal 5 bp, NN eval); higher = better"
            if asymmetry is not None else None
        ),
    )


@app.post("/rnaup", response_model=RnaUpResponse)
def rnaup(payload: RnaUpRequest) -> RnaUpResponse:
    seq1 = _normalize_rna(payload.sequence1)
    seq2 = _normalize_rna(payload.sequence2)
    if not seq1 or not seq2:
        raise HTTPException(status_code=400, detail="Both sequences must contain RNA letters after normalization.")
    if not _RNAUP_EXE:
        raise HTTPException(status_code=503, detail="RNAup executable not found on PATH.")
    try:
        result = _run_rnaup_cli(
            seq1, seq2, payload.params,
            ulength=payload.ulength,
            window=payload.window,
            include_both=payload.include_both,
            extend5=payload.extend5,
            extend3=payload.extend3,
            contributions=payload.contributions,
            constraint1=payload.constraint1,
            constraint2=payload.constraint2,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"RNAup failed: {exc}") from exc
    return RnaUpResponse(
        sequence1=seq1,
        sequence2=seq2,
        interaction_energy=result.get("interaction_energy"),
        interaction_structure=result.get("interaction_structure"),
        raw_stdout=result["raw_stdout"],
        backend=result["backend"],
    )


@app.post("/aso-accessibility", response_model=AsoAccessibilityResponse)
def aso_accessibility(payload: AsoAccessibilityRequest) -> AsoAccessibilityResponse:
    seq = _seq_from_text(payload.sequence)
    if not seq:
        raise HTTPException(status_code=400, detail="No RNA sequence after normalization.")
    if payload.region_end > len(seq):
        raise HTTPException(status_code=400, detail=f"region_end={payload.region_end} exceeds sequence length {len(seq)}.")
    rlen = payload.region_end - payload.region_start + 1
    ulen = max(payload.unpaired_ulength, payload.aso_oligo_length, rlen)
    try:
        rows, backend = _run_plfold_accessibility_cli(
            seq, payload.params, payload.winsize, payload.span, ulen,
            cutoff=payload.cutoff, opening_energies=payload.opening_energies,
        )
        stats = _region_accessibility_from_lunp(
            rows, payload.region_start, payload.region_end, payload.aso_oligo_length,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"RNAplfold accessibility failed: {exc}") from exc

    return AsoAccessibilityResponse(
        sequence_length=len(seq),
        region_start=payload.region_start,
        region_end=payload.region_end,
        mean_unpaired_prob_single_nt=stats.get("mean_unpaired_prob_single_nt"),
        joint_unpaired_prob_stretch_ending_at_region_end=stats.get("joint_unpaired_prob_stretch_ending_at_region_end"),
        aso_oligo_length_used=int(stats.get("aso_oligo_length_used", payload.aso_oligo_length)),
        winsize=min(payload.winsize, len(seq)),
        span=min(payload.span, min(payload.winsize, len(seq))),
        unpaired_ulength=ulen,
        backend=backend,
    )


@app.post("/plfold-profiles", response_model=PlfoldProfilesResponse)
def plfold_profiles(payload: PlfoldProfilesRequest) -> PlfoldProfilesResponse:
    seq = _seq_from_text(payload.sequence)
    if not seq:
        raise HTTPException(status_code=400, detail="No RNA sequence after normalization.")
    if len(seq) > _MAX_PLFOLD_PROFILE_SEQ_LEN:
        raise HTTPException(status_code=400, detail=f"sequence length {len(seq)} exceeds server limit {_MAX_PLFOLD_PROFILE_SEQ_LEN}.")
    ulen = max(1, min(payload.unpaired_ulength, len(seq), 500))
    try:
        rows, backend = _run_plfold_accessibility_cli(
            seq, payload.params, payload.winsize, payload.span, ulen,
            cutoff=payload.cutoff, opening_energies=payload.opening_energies,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"RNAplfold profile failed: {exc}") from exc

    positions: List[int] = []
    col0: List[float] = []
    for pos, probs in rows:
        if not probs:
            continue
        positions.append(pos)
        col0.append(float(probs[0]))
    if not col0:
        raise HTTPException(status_code=503, detail="RNAplfold produced no lunp data rows.")
    mean_u = sum(col0) / len(col0)
    return PlfoldProfilesResponse(
        sequence_length=len(seq),
        positions=positions,
        unpaired_prob_1nt=col0,
        winsize=min(payload.winsize, len(seq)),
        span=min(payload.span, min(payload.winsize, len(seq))),
        unpaired_ulength_effective=ulen,
        mean_unpaired_prob_1nt=float(mean_u),
        min_unpaired_prob_1nt=float(min(col0)),
        max_unpaired_prob_1nt=float(max(col0)),
        backend=backend,
    )


@app.post("/inverse-fold", response_model=InverseFoldResponse)
def inverse_fold(payload: InverseFoldRequest) -> InverseFoldResponse:
    if not _RNAINVERSE_EXE:
        raise HTTPException(status_code=503, detail="RNAinverse not found on PATH.")
    try:
        result = _inverse_fold_cli(
            payload.structure,
            payload.start_sequence,
            payload.params,
            payload.repeats,
            payload.function_mode,
            final_cost=payload.final_cost,
            alphabet=payload.alphabet,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Inverse fold failed: {exc}") from exc
    return InverseFoldResponse(
        structure=payload.structure.strip(),
        best_sequence=result["best_sequence"],
        hamming_distance=result.get("hamming_distance"),
        partition_probability=result.get("partition_probability"),
        backend=result["backend"],
    )
