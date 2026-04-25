"""FastAPI microservice: RNA GC content and dot-bracket unpaired ('.') fraction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Import shared utilities so the microservice stays consistent with agent-core stubs.
from agent_core.sequence_utils import (
    compute_dot_bracket_unpaired_fraction,
    compute_gc_content,
    extract_dot_bracket,
    normalize_rna_sequence,
    validate_dot_bracket,
)

# rna_agent_system/microservices/rna_sequence_metrics_service/main.py -> parents[2] == rna_agent_system
RNA_AGENT_SYSTEM_ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(
    title="RNA sequence metrics",
    description="GC content from sequence files; unpaired-base fraction from dot-bracket secondary structure.",
    version="0.1.0",
)


def _resolve_host_path(raw: str) -> Path:
    text = raw.strip().strip('"').strip("'")
    p = Path(text).expanduser()
    if p.is_absolute():
        return p.resolve()
    candidate = (RNA_AGENT_SYSTEM_ROOT / text).resolve()
    if candidate.exists():
        return candidate
    return Path(text).resolve()


# ═══════════════════════════════════════════════════════════════════════════════
# GC Content
# ═══════════════════════════════════════════════════════════════════════════════


class GcContentRequest(BaseModel):
    sequence_filepath: str = Field(
        ...,
        description="Absolute or rna_agent_system-relative path to plain RNA/DNA or FASTA.",
    )


class GcContentResponse(BaseModel):
    input_filepath: str
    resolved_filepath: str
    sequence_length: int
    g_count: int
    c_count: int
    gc_count: int
    gc_content: float
    model: str = "rna-sequence-metrics-gc"


@app.post("/gc-content", response_model=GcContentResponse)
def gc_content(payload: GcContentRequest) -> GcContentResponse:
    path = _resolve_host_path(payload.sequence_filepath)
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"sequence_filepath not found: {path}")
    raw = path.read_text(encoding="utf-8")
    seq = normalize_rna_sequence(raw)
    metrics = compute_gc_content(seq)
    if metrics["sequence_length"] == 0:
        raise HTTPException(status_code=400, detail="No A/U/G/C nucleotides found after normalization.")
    return GcContentResponse(
        input_filepath=payload.sequence_filepath,
        resolved_filepath=str(path),
        sequence_length=metrics["sequence_length"],
        g_count=metrics["g_count"],
        c_count=metrics["c_count"],
        gc_count=metrics["gc_count"],
        gc_content=metrics["gc_content"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Dot-bracket unpaired fraction
# ═══════════════════════════════════════════════════════════════════════════════


class UnpairedFractionRequest(BaseModel):
    structure_filepath: str = Field(
        ...,
        description="Absolute or rna_agent_system-relative path to dot-bracket structure (one line typical).",
    )


class UnpairedFractionResponse(BaseModel):
    input_filepath: str
    resolved_filepath: str
    structure_length: int
    dot_count: int
    unpaired_fraction: float
    model: str = "rna-sequence-metrics-unpaired"


@app.post("/unpaired-fraction", response_model=UnpairedFractionResponse)
def unpaired_fraction(payload: UnpairedFractionRequest) -> UnpairedFractionResponse:
    path = _resolve_host_path(payload.structure_filepath)
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"structure_filepath not found: {path}")
    raw = path.read_text(encoding="utf-8")
    struct = extract_dot_bracket(raw)
    try:
        metrics = compute_dot_bracket_unpaired_fraction(struct)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return UnpairedFractionResponse(
        input_filepath=payload.structure_filepath,
        resolved_filepath=str(path),
        structure_length=metrics["structure_length"],
        dot_count=metrics["dot_count"],
        unpaired_fraction=metrics["unpaired_fraction"],
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "rna_agent_system_root": str(RNA_AGENT_SYSTEM_ROOT)}
