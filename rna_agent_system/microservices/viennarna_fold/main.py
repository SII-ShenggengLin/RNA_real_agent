"""ViennaRNA microservice: folding, siRNA duplex (cofold), RNAplfold local accessibility, inverse fold."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    import RNA  # type: ignore

    _HAS_RNALIB = True
except ImportError:
    RNA = None  # type: ignore
    _HAS_RNALIB = False


_RNAFOLD_EXE = shutil.which("RNAfold")
_RNACOFOLD_EXE = shutil.which("RNAcofold")
_RNAPLFOLD_EXE = shutil.which("RNAplfold")
_RNAINVERSE_EXE = shutil.which("RNAinverse")

# Structure line from RNAfold / RNAcofold stdout (allows '&' for cofold).
_STRUCTURE_LINE = re.compile(
    r"^([.()[\]{}<>&]+)\s+\(\s*(-?\d+(?:\.\d+)?)\s*\)\s*$"
)


def _normalize_rna(seq: str) -> str:
    merged = "".join(seq.split()).upper().replace("T", "U")
    return "".join(ch for ch in merged if ch in "AUGC")


def _fold_with_rnafold_cli(sequence: str) -> Tuple[str, float]:
    """Fold using the ``RNAfold`` executable (no Python RNAlib required)."""
    if not _RNAFOLD_EXE:
        raise RuntimeError("`RNAfold` executable not found in PATH.")

    proc = subprocess.run(
        [_RNAFOLD_EXE, "--noPS"],
        input=sequence + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"RNAfold failed (exit {proc.returncode}): {err}")

    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    for line in reversed(lines):
        if line.startswith(">"):
            continue
        m = _STRUCTURE_LINE.match(line)
        if m:
            return m.group(1), float(m.group(2))

    raise RuntimeError(
        "Could not parse RNAfold output; expected a line like "
        "'((((....))))) (-6.50)'."
    )


def _fold_sequence(sequence: str) -> Tuple[str, float, str]:
    """Return (structure, mfe, backend_label)."""
    if _HAS_RNALIB:
        fc = RNA.fold_compound(sequence)
        structure, mfe = fc.mfe()
        return str(structure), float(mfe), "RNAlib"
    structure, mfe = _fold_with_rnafold_cli(sequence)
    return structure, mfe, "RNAfold-cli"


def _cofold_duplex(sense: str, antisense: str) -> Tuple[str, float, str]:
    """Cofold sense & antisense (5'→3' each); returns (structure, mfe, backend)."""
    sense_n = _normalize_rna(sense)
    anti_n = _normalize_rna(antisense)
    if not sense_n or not anti_n:
        raise ValueError("sense and antisense must contain at least one A/C/G/U after normalization.")
    combined = f"{sense_n}&{anti_n}"
    if _HAS_RNALIB:
        fc = RNA.fold_compound(combined)
        structure, mfe = fc.mfe()
        return str(structure), float(mfe), "RNAlib"
    if not _RNACOFOLD_EXE:
        raise RuntimeError(
            "`RNAcofold` executable not found in PATH and RNAlib cofold is unavailable."
        )
    proc = subprocess.run(
        [_RNACOFOLD_EXE, "--noPS"],
        input=combined + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"RNAcofold failed (exit {proc.returncode}): {err}")
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    for line in reversed(lines):
        if line.startswith(">"):
            continue
        m = _STRUCTURE_LINE.match(line)
        if m:
            return m.group(1), float(m.group(2)), "RNAcofold-cli"
    raise RuntimeError("Could not parse RNAcofold output for duplex MFE.")


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
            return None
    return pos, probs


def _run_plfold_accessibility(
    sequence: str,
    winsize: int,
    span: int,
    ulength: int,
    temp_c: float,
) -> Tuple[List[Tuple[int, List[float]]], str]:
    """Run RNAplfold in a temp dir; return parsed lunp rows and backend label."""
    seq = _normalize_rna(sequence)
    if len(seq) < 10:
        raise ValueError("sequence too short for meaningful RNAplfold accessibility (need at least ~10 nt).")
    winsize = max(3, min(winsize, len(seq)))
    span = max(2, min(span, winsize))
    ulength = max(1, min(ulength, len(seq), 400))

    if not _RNAPLFOLD_EXE:
        raise RuntimeError(
            "`RNAplfold` not found in PATH and RNAlib local plfold is unavailable."
        )

    with tempfile.TemporaryDirectory(prefix="vienna_plfold_") as tmp:
        tdir = Path(tmp)
        fasta_path = tdir / "query.fa"
        fasta_path.write_text(f">query\n{seq}\n", encoding="utf-8")
        # Note: do not pass ``--noPS`` here; some ViennaRNA builds ship RNAplfold
        # without that flag (it would exit 1 with "unrecognized option --noPS").
        cmd = [
            _RNAPLFOLD_EXE,
            "-W",
            str(winsize),
            "-L",
            str(span),
            "-u",
            str(ulength),
            "-T",
            str(temp_c),
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(tdir),
            input=fasta_path.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"RNAplfold failed (exit {proc.returncode}): {err}")
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


def _region_accessibility_from_lunp(
    rows: List[Tuple[int, List[float]]],
    region_start: int,
    region_end: int,
    aso_length: int,
) -> dict[str, Any]:
    """region_* are 1-based inclusive on the folded sequence."""
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


def _inverse_fold_cli(
    structure: str,
    start_sequence: str,
    repeats: int,
    temp_c: float,
    function_mode: str,
) -> Tuple[str, Optional[int], str]:
    """Run RNAinverse; return (best_sequence, hamming, backend)."""
    if not _RNAINVERSE_EXE:
        raise RuntimeError("`RNAinverse` executable not found in PATH.")
    struct = structure.strip()
    if not struct:
        raise ValueError("structure must be non-empty dot-bracket string.")
    allowed = set(".()[]{}<>")
    if any(ch not in allowed for ch in struct):
        raise ValueError("structure contains characters outside dot-bracket notation.")
    start = start_sequence.strip() if start_sequence else ""
    if not start:
        start = "N" * len(struct)
    elif len(start) < len(struct):
        start = start + "N" * (len(struct) - len(start))
    elif len(start) > len(struct):
        start = start[: len(struct)]

    fm = function_mode if function_mode in {"m", "p", "mp"} else "m"
    cmd = [_RNAINVERSE_EXE, f"-F{fm}", "-d2", "-T", str(temp_c), f"-R{repeats}"]
    stdin = f"{struct}\n{start}\n@\n"
    proc = subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"RNAinverse failed (exit {proc.returncode}): {err}")
    out_lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not out_lines:
        raise RuntimeError("RNAinverse produced no stdout.")
    first = out_lines[0]
    parts = first.split()
    if not parts or not re.fullmatch(r"[AUGCaugc]+", parts[0]):
        raise RuntimeError(f"Unexpected RNAinverse output line: {first!r}")
    best_seq = parts[0].upper().replace("T", "U")
    hamming: Optional[int] = None
    if len(parts) > 1 and parts[1].isdigit():
        hamming = int(parts[1])
    return best_seq, hamming, "RNAinverse-cli"


app = FastAPI(
    title="ViennaRNA Fold Service (Port 8003 Deployment)",
    description=(
        "Predict RNA secondary structure (RNAfold), siRNA duplex thermodynamics (RNAcofold), "
        "local accessibility via RNAplfold (whole-sequence profiles and ASO regions), and inverse folding (RNAinverse). "
        "Uses Python RNAlib when available, otherwise ViennaRNA CLI tools."
    ),
    version="0.3.0-port8003",
)

# Upper bound on sequence length for whole-sequence RNAplfold profiles (memory / JSON payload).
_MAX_PLFOLD_PROFILE_SEQ_LEN = 8000


class FoldRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence (A/U/G/C).")


class FoldResponse(BaseModel):
    sequence: str
    structure: str
    mfe: float
    model: str = "ViennaRNA-RNAfold"
    backend: str = Field(
        ...,
        description="RNAlib (conda/pip Python module) or RNAfold-cli (standalone binary).",
    )


class SirnaDuplexRequest(BaseModel):
    sense: Optional[str] = Field(
        default=None,
        description="Sense strand RNA 5'→3'. Provide this and antisense, or use fasta_content.",
    )
    antisense: Optional[str] = Field(
        default=None,
        description="Antisense strand RNA 5'→3'.",
    )
    fasta_content: Optional[str] = Field(
        default=None,
        description="Two FASTA records: first = sense, second = antisense.",
    )


class SirnaDuplexResponse(BaseModel):
    sense: str
    antisense: str
    cofold_sequence: str
    structure: str
    mfe: float
    backend: str
    model: str = "ViennaRNA-RNAcofold"


class AsoAccessibilityRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="Full target RNA (e.g. mRNA) in plain or FASTA text.")
    region_start: int = Field(..., ge=1, description="1-based inclusive start of ASO binding region.")
    region_end: int = Field(..., ge=1, description="1-based inclusive end of ASO binding region.")
    aso_oligo_length: int = Field(
        default=18,
        ge=1,
        le=500,
        description="Oligo length used for joint unpaired probability (RNAplfold -u column).",
    )
    winsize: int = Field(default=70, ge=3, le=800, description="RNAplfold -W window size.")
    span: int = Field(default=70, ge=2, le=800, description="RNAplfold -L max pair span.")
    unpaired_ulength: int = Field(
        default=25,
        ge=1,
        le=500,
        description="Max stretch length for unpaired probabilities (RNAplfold -u).",
    )
    temp_c: float = Field(default=37.0, description="Temperature in Celsius.")


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


class InverseFoldRequest(BaseModel):
    structure: str = Field(..., min_length=1, description="Target secondary structure in dot-bracket notation.")
    start_sequence: str = Field(
        default="",
        description="Optional IUPAC / wildcards; N = randomizable. Empty = all-N start.",
    )
    repeats: int = Field(default=1, ge=1, le=500, description="RNAinverse -R repeats.")
    temp_c: float = Field(default=37.0, description="Temperature in Celsius.")
    function_mode: str = Field(
        default="m",
        description="RNAinverse -F mode: m (MFE), p (partition), or mp (both).",
    )


class InverseFoldResponse(BaseModel):
    structure: str
    best_sequence: str
    hamming_distance: Optional[int] = None
    partition_probability_note: Optional[float] = None
    backend: str
    model: str = "ViennaRNA-RNAinverse"


class PlfoldProfilesRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence (plain or FASTA body).")
    winsize: int = Field(default=70, ge=3, le=800, description="RNAplfold -W window size.")
    span: int = Field(default=70, ge=2, le=800, description="RNAplfold -L max pair span.")
    unpaired_ulength: int = Field(
        default=25,
        ge=1,
        le=500,
        description="RNAplfold -u: max stretch length for unpaired probabilities in lunp output.",
    )
    temp_c: float = Field(default=37.0, description="Temperature in Celsius.")


class PlfoldProfilesResponse(BaseModel):
    sequence_length: int
    positions: List[int] = Field(
        ...,
        description="1-based sequence positions with RNAplfold lunp rows (same order as query_lunp).",
    )
    unpaired_prob_1nt: List[float] = Field(
        ...,
        description="Local probability that the base at each position is unpaired (first lunp column).",
    )
    winsize: int
    span: int
    unpaired_ulength_effective: int
    mean_unpaired_prob_1nt: float
    min_unpaired_prob_1nt: float
    max_unpaired_prob_1nt: float
    backend: str
    model: str = "ViennaRNA-RNAplfold"


@app.get("/health")
def health() -> dict[str, Any]:
    fold_ok = _HAS_RNALIB or bool(_RNAFOLD_EXE)
    duplex_ok = _HAS_RNALIB or bool(_RNACOFOLD_EXE)
    plfold_ok = bool(_RNAPLFOLD_EXE)
    inverse_ok = bool(_RNAINVERSE_EXE)
    extensions_ok = duplex_ok and plfold_ok and inverse_ok
    return {
        "status": "ok" if fold_ok else "degraded",
        "rnalib": _HAS_RNALIB,
        "rnafold_cli": bool(_RNAFOLD_EXE),
        "rnacofold_cli": bool(_RNACOFOLD_EXE),
        "rnaplfold_cli": bool(_RNAPLFOLD_EXE),
        "rnainverse_cli": bool(_RNAINVERSE_EXE),
        "extensions_ready": extensions_ok,
    }


@app.post("/fold", response_model=FoldResponse)
def fold(payload: FoldRequest) -> FoldResponse:
    sequence = _normalize_rna(payload.sequence)
    if not sequence:
        raise HTTPException(status_code=400, detail="No RNA letters after normalization.")
    if not _HAS_RNALIB and not _RNAFOLD_EXE:
        raise HTTPException(
            status_code=503,
            detail=(
                "ViennaRNA is not available: install the `viennarna` conda package "
                "(recommended) or ensure `RNAfold` is on PATH."
            ),
        )
    try:
        structure, mfe, backend = _fold_sequence(sequence)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Fold failed: {exc}") from exc

    return FoldResponse(sequence=sequence, structure=structure, mfe=mfe, backend=backend)


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
            raise HTTPException(
                status_code=400,
                detail="fasta_content must contain at least two FASTA records (sense then antisense).",
            )
        sense, anti = records[0][1], records[1][1]
    elif payload.sense is not None and payload.antisense is not None:
        sense = _normalize_rna(payload.sense)
        anti = _normalize_rna(payload.antisense)
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either (sense + antisense) or fasta_content with two FASTA records.",
        )
    if not sense or not anti:
        raise HTTPException(status_code=400, detail="sense and antisense must be non-empty RNA sequences.")
    if not _HAS_RNALIB and not _RNACOFOLD_EXE:
        raise HTTPException(
            status_code=503,
            detail="Duplex prediction needs RNAlib or RNAcofold on PATH.",
        )
    try:
        structure, mfe, backend = _cofold_duplex(sense, anti)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Duplex cofold failed: {exc}") from exc
    return SirnaDuplexResponse(
        sense=sense,
        antisense=anti,
        cofold_sequence=f"{sense}&{anti}",
        structure=structure,
        mfe=mfe,
        backend=backend,
    )


@app.post("/aso-accessibility", response_model=AsoAccessibilityResponse)
def aso_accessibility(payload: AsoAccessibilityRequest) -> AsoAccessibilityResponse:
    seq = _normalize_rna(
        "".join(
            ln
            for ln in payload.sequence.splitlines()
            if ln.strip() and not ln.lstrip().startswith(">")
        )
    )
    if not seq:
        raise HTTPException(status_code=400, detail="No RNA sequence after normalization.")
    if payload.region_end > len(seq):
        raise HTTPException(
            status_code=400,
            detail=f"region_end={payload.region_end} exceeds sequence length {len(seq)}.",
        )
    rlen = payload.region_end - payload.region_start + 1
    ulen = max(payload.unpaired_ulength, payload.aso_oligo_length, rlen)
    try:
        rows, backend = _run_plfold_accessibility(
            seq,
            payload.winsize,
            payload.span,
            ulen,
            payload.temp_c,
        )
        stats = _region_accessibility_from_lunp(
            rows,
            payload.region_start,
            payload.region_end,
            payload.aso_oligo_length,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"RNAplfold accessibility failed: {exc}") from exc

    return AsoAccessibilityResponse(
        sequence_length=len(seq),
        region_start=payload.region_start,
        region_end=payload.region_end,
        mean_unpaired_prob_single_nt=stats.get("mean_unpaired_prob_single_nt"),
        joint_unpaired_prob_stretch_ending_at_region_end=stats.get(
            "joint_unpaired_prob_stretch_ending_at_region_end"
        ),
        aso_oligo_length_used=int(stats.get("aso_oligo_length_used", payload.aso_oligo_length)),
        winsize=min(payload.winsize, len(seq)),
        span=min(payload.span, min(payload.winsize, len(seq))),
        unpaired_ulength=ulen,
        backend=backend,
    )


@app.post("/plfold-profiles", response_model=PlfoldProfilesResponse)
def plfold_profiles(payload: PlfoldProfilesRequest) -> PlfoldProfilesResponse:
    """Whole-sequence local unpaired accessibility via ViennaRNA ``RNAplfold`` (lunp, single-nt column)."""
    seq = _normalize_rna(
        "".join(
            ln
            for ln in payload.sequence.splitlines()
            if ln.strip() and not ln.lstrip().startswith(">")
        )
    )
    if not seq:
        raise HTTPException(status_code=400, detail="No RNA sequence after normalization.")
    if len(seq) > _MAX_PLFOLD_PROFILE_SEQ_LEN:
        raise HTTPException(
            status_code=400,
            detail=(
                f"sequence length {len(seq)} exceeds server limit {_MAX_PLFOLD_PROFILE_SEQ_LEN} "
                "for /plfold-profiles; shorten the input or increase the limit in the service code."
            ),
        )
    ulen = max(1, min(payload.unpaired_ulength, len(seq), 500))
    try:
        rows, backend = _run_plfold_accessibility(
            seq,
            payload.winsize,
            payload.span,
            ulen,
            payload.temp_c,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
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
        best, ham, backend = _inverse_fold_cli(
            payload.structure,
            payload.start_sequence,
            payload.repeats,
            payload.temp_c,
            payload.function_mode,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Inverse fold failed: {exc}") from exc
    return InverseFoldResponse(
        structure=payload.structure.strip(),
        best_sequence=best,
        hamming_distance=ham,
        partition_probability_note=None,
        backend=backend,
    )
