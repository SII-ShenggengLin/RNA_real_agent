"""FastAPI wrapper for codonw-slim (CodonW metrics on coding sequences)."""

from __future__ import annotations

import math
import re
from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from codonw import CodonSeq
except ImportError as exc:  # pragma: no cover - exercised when env not built
    CodonSeq = None  # type: ignore[misc, assignment]
    _IMPORT_ERROR = str(exc)
else:
    _IMPORT_ERROR = ""

def _finite_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


app = FastAPI(
    title="codonw-slim service",
    description=(
        "REST bridge to smsaladi/codonw-slim: CAI, Fop, CBI, Nc (ENC), "
        "hydropathy, aromaticity, base composition, RSCU, etc."
    ),
    version="0.1.0",
)


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, pd.Series):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, pd.DataFrame):
        return obj.astype(float).replace({np.nan: None}).to_dict(orient="split")
    if isinstance(obj, (np.floating, float)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    return str(obj)


def _normalize_cds_dna(raw: str) -> tuple[str, str]:
    """Return (dna_cds, note) with FASTA/plain handling; U->T; length multiple of 3."""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.lstrip().startswith(">")]
    merged = "".join(lines).upper().replace("U", "T")
    seq = re.sub(r"[^ACGT]", "", merged)
    if not seq:
        raise ValueError("No A/C/G/T nucleotides found after normalization.")
    note = ""
    if len(seq) % 3 != 0:
        drop = len(seq) % 3
        seq = seq[:-drop]
        note = f"trimmed_{drop}_terminal_nt_to_multiple_of_three"
    if len(seq) < 9:
        raise ValueError("CDS must be at least 9 nt (3 codons) after normalization.")
    return seq, note


class CodonwAnalyzeRequest(BaseModel):
    sequence: str = Field(
        ...,
        min_length=3,
        description="Coding DNA sequence (ATGC) or RNA (AUGC); FASTA allowed.",
    )
    genetic_code: int = Field(
        default=0,
        ge=0,
        le=7,
        description="CodonSeq genetic_code index (0=universal nuclear, see codonw docs).",
    )
    cai_ref: int = Field(default=0, ge=0, le=2, description="Reference set index for CAI/CBI/Fop.")
    fop_ref: int = Field(default=0, ge=0, le=7, description="Fop reference species index.")
    factor_in_rare: bool = Field(default=False, description="Passed to CodonSeq.fop().")
    include_codon_tables: bool = Field(
        default=False,
        description="If true, include codon_usage and rscu dicts (can be large).",
    )
    include_dinucleotide: bool = Field(default=False, description="If true, include dinuc frame tables.")


class CodonwAnalyzeResponse(BaseModel):
    genetic_code: int
    cds_length_nt: int
    cds_length_codons: int
    normalization_note: str
    cai: Optional[float] = None
    fop: Optional[float] = None
    cbi: Optional[float] = None
    enc: Optional[float] = None
    hydropathy: Optional[float] = None
    aromaticity: Optional[float] = None
    silent_base_usage: dict[str, Any]
    bases2: dict[str, Any]
    codon_usage: Optional[dict[str, Any]] = None
    rscu: Optional[dict[str, Any]] = None
    dinuc: Optional[dict[str, Any]] = None
    model: str = "codonw-slim"


@app.get("/health")
def health() -> dict[str, Any]:
    ready = CodonSeq is not None
    return {
        "status": "ok" if ready else "degraded",
        "codonw_import_ok": ready,
        "import_error": _IMPORT_ERROR if not ready else None,
        "service": "codonw_slim_service",
        "port": 8018,
    }


@app.post("/analyze/cds", response_model=CodonwAnalyzeResponse)
def analyze_cds(body: CodonwAnalyzeRequest) -> CodonwAnalyzeResponse:
    if CodonSeq is None:
        raise HTTPException(
            status_code=503,
            detail=f"codonw-slim not importable: {_IMPORT_ERROR}. Rebuild the conda env with -e ../../external_repos/codonw-slim.",
        )
    try:
        dna, note = _normalize_cds_dna(body.sequence)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        cseq = CodonSeq(dna, genetic_code=body.genetic_code)
    except Exception as exc:  # noqa: BLE001 - surface C-layer failures clearly
        raise HTTPException(status_code=400, detail=f"CodonSeq failed: {exc}") from exc

    silent = _jsonable(cseq.silent_base_usage())
    bases2 = _jsonable(cseq.bases2())

    codon_usage: Optional[dict[str, Any]] = None
    rscu: Optional[dict[str, Any]] = None
    dinuc: Optional[dict[str, Any]] = None
    if body.include_codon_tables:
        codon_usage = _jsonable(cseq.codon_usage())
        rscu = _jsonable(cseq.rscu())
    if body.include_dinucleotide:
        dinuc = _jsonable(cseq.dinuc(pct=True))

    return CodonwAnalyzeResponse(
        genetic_code=body.genetic_code,
        cds_length_nt=len(dna),
        cds_length_codons=len(dna) // 3,
        normalization_note=note,
        cai=_finite_float(cseq.cai(body.cai_ref)),
        fop=_finite_float(cseq.fop(body.factor_in_rare, body.fop_ref)),
        cbi=_finite_float(cseq.cbi(body.cai_ref)),
        enc=_finite_float(cseq.enc()),
        hydropathy=_finite_float(cseq.hydropathy()),
        aromaticity=_finite_float(cseq.aromaticity()),
        silent_base_usage=silent if isinstance(silent, dict) else {},
        bases2=bases2 if isinstance(bases2, dict) else {},
        codon_usage=codon_usage,
        rscu=rscu,
        dinuc=dinuc,
    )
