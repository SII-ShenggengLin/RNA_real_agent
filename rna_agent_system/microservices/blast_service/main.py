"""FastAPI microservice wrapping NCBI BLAST+ blastn (and makeblastdb for FASTA subjects).

"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from microservices.service_kit import (
    create_service_app,
    fasta_from_sequence_text,
    health_response,
    require_binary,
    resolve_host_path,
    run_subprocess,
)

# In-memory cache for makeblastdb results: resolved subject path -> (mtime, db_prefix)
_MAKEBLASTDB_CACHE: dict[str, tuple[float, str]] = {}

RNA_AGENT_SYSTEM_ROOT = Path(__file__).resolve().parents[2]

app = create_service_app(
    title="BLAST+ blastn service",
    description="Run blastn against a subject FASTA (indexed on the fly) or an existing nucleotide BLAST database.",
    version="0.1.0",
)


class BlastnRequest(BaseModel):
    query_filepath: str = Field(
        ...,
        description="Absolute or rna_agent_system-relative path to query FASTA or plain sequence file.",
    )
    subject_fasta_path: Optional[str] = Field(
        default=None,
        description="Subject multi-FASTA to index with makeblastdb (mutually exclusive with subject_db).",
    )
    subject_db: Optional[str] = Field(
        default=None,
        description="Existing BLAST nucleotide DB prefix (mutually exclusive with subject_fasta_path).",
    )
    task: str = Field(
        default="blastn-short",
        description="blastn -task: blastn-short | blastn | megablast | dc-megablast.",
    )
    evalue: float = Field(default=10.0, gt=0.0)
    word_size: Optional[int] = Field(default=None, ge=4, le=50)
    max_target_seqs: int = Field(default=50, ge=1, le=10000)
    perc_identity: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    strand: str = Field(default="both", description="both | plus | minus")
    outfmt: str = Field(
        default="6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore",
        description="blastn -outfmt argument (default tabular).",
    )
    blastn_timeout_sec: int = Field(default=600, ge=30, le=86400)


class BlastnResponse(BaseModel):
    hit_count: int
    hits_preview: str
    preview_truncated: bool
    tabular_output: str = Field(
        default="",
        description="Full blastn -outfmt tabular lines (may be truncated for very large responses).",
    )
    tabular_output_truncated: bool = False
    blastn_command: str
    makeblastdb_command: Optional[str]
    stderr: str
    subject_mode: str
    resolved_query_path: str
    resolved_subject: str
    model: str = "ncbi-blastn"


@app.get("/health")
def health() -> dict[str, Any]:
    blastn = shutil.which("blastn")
    makeblastdb = shutil.which("makeblastdb")
    ok = bool(blastn and makeblastdb)
    return health_response(
        "ok" if ok else "degraded",
        blastn=blastn or "",
        makeblastdb=makeblastdb or "",
        rna_agent_system_root=str(RNA_AGENT_SYSTEM_ROOT),
    )


@app.post("/blastn", response_model=BlastnResponse)
def run_blastn(payload: BlastnRequest) -> BlastnResponse:
    if not payload.subject_fasta_path and not payload.subject_db:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of subject_fasta_path or subject_db.",
        )
    if payload.subject_fasta_path and payload.subject_db:
        raise HTTPException(
            status_code=400,
            detail="Provide only one of subject_fasta_path or subject_db.",
        )

    blastn_bin = require_binary("blastn")
    makeblastdb_bin = shutil.which("makeblastdb")
    if payload.subject_fasta_path and not makeblastdb_bin:
        raise HTTPException(status_code=503, detail="makeblastdb not found in PATH (required for subject FASTA).")

    qpath = resolve_host_path(payload.query_filepath, RNA_AGENT_SYSTEM_ROOT)
    if not qpath.is_file():
        raise HTTPException(status_code=400, detail=f"Query file not found: {qpath}")

    raw_query = qpath.read_text(encoding="utf-8", errors="replace")
    query_fasta = fasta_from_sequence_text(raw_query, default_id=qpath.stem)

    strand = payload.strand.lower().strip()
    if strand not in {"both", "plus", "minus"}:
        raise HTTPException(status_code=400, detail="strand must be both, plus, or minus.")

    makeblastdb_cmd: Optional[str] = None
    db_prefix: str

    with tempfile.TemporaryDirectory(prefix="blastsvc_") as tmp:
        tmp_path = Path(tmp)
        query_file = tmp_path / "query.fa"
        query_file.write_text(query_fasta, encoding="utf-8")

        if payload.subject_db:
            db_path = resolve_host_path(payload.subject_db, RNA_AGENT_SYSTEM_ROOT)
            db_prefix = str(db_path)
        else:
            assert payload.subject_fasta_path is not None
            subj_path = resolve_host_path(payload.subject_fasta_path, RNA_AGENT_SYSTEM_ROOT)
            if not subj_path.is_file():
                raise HTTPException(status_code=400, detail=f"Subject FASTA not found: {subj_path}")

            # ── Cached makeblastdb ────────────────────────────────────────────
            cache_key = str(subj_path.resolve())
            current_mtime = subj_path.stat().st_mtime
            cached = _MAKEBLASTDB_CACHE.get(cache_key)
            if cached and cached[0] == current_mtime:
                # Verify cached DB files still exist
                if Path(cached[1] + ".nhr").exists():
                    db_prefix = cached[1]
                    makeblastdb_cmd = None
                else:
                    cached = None

            if not cached or cached[0] != current_mtime:
                cache_dir = Path(tempfile.gettempdir()) / "blastdb_cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                mtime_hash = hashlib.md5(f"{cache_key}:{current_mtime}".encode()).hexdigest()[:12]
                db_prefix = str(cache_dir / f"{subj_path.stem}_{mtime_hash}" / "subject_db")
                Path(db_prefix).parent.mkdir(parents=True, exist_ok=True)

                makeblastdb_cmd = " ".join(
                    [makeblastdb_bin, "-in", str(subj_path), "-dbtype", "nucl", "-out", db_prefix, "-title", "subject"]
                )
                _, stderr, rc = run_subprocess(
                    [makeblastdb_bin, "-in", str(subj_path), "-dbtype", "nucl", "-out", db_prefix, "-title", "subject"],
                    timeout=3600,
                    check=False,
                )
                if rc != 0:
                    raise HTTPException(
                        status_code=500,
                        detail=f"makeblastdb failed (exit {rc}): {stderr}",
                    )
                _MAKEBLASTDB_CACHE[cache_key] = (current_mtime, db_prefix)
            # ── End cache ─────────────────────────────────────────────────────

        blast_args: list[str] = [
            blastn_bin,
            "-query", str(query_file),
            "-db", db_prefix,
            "-task", payload.task.strip(),
            "-evalue", str(payload.evalue),
            "-max_target_seqs", str(payload.max_target_seqs),
            "-outfmt", payload.outfmt.strip(),
            "-strand", strand,
        ]
        if payload.word_size is not None:
            blast_args.extend(["-word_size", str(int(payload.word_size))])
        if payload.perc_identity is not None:
            blast_args.extend(["-perc_identity", str(float(payload.perc_identity))])

        blastn_command = " ".join(blast_args)
        stdout, stderr, rc = run_subprocess(
            blast_args,
            timeout=int(payload.blastn_timeout_sec),
            check=False,
        )
        if rc != 0:
            raise HTTPException(
                status_code=500,
                detail=f"blastn failed (exit {rc}): {stderr}",
            )

        lines = [ln for ln in stdout.splitlines() if ln.strip()]
        hit_count = len(lines)
        preview_lines = lines[:30]
        hits_preview = "\n".join(preview_lines)
        preview_truncated = hit_count > len(preview_lines)
        max_tab = 500_000
        tab_body = stdout
        tab_trunc = len(tab_body) > max_tab
        if tab_trunc:
            tab_body = tab_body[:max_tab]

    return BlastnResponse(
        hit_count=hit_count,
        hits_preview=hits_preview,
        preview_truncated=preview_truncated,
        tabular_output=tab_body,
        tabular_output_truncated=tab_trunc,
        blastn_command=blastn_command,
        makeblastdb_command=makeblastdb_cmd,
        stderr=(stderr or "")[:8000],
        subject_mode="fasta" if payload.subject_fasta_path else "db",
        resolved_query_path=str(qpath),
        resolved_subject=str(
            resolve_host_path(payload.subject_fasta_path or payload.subject_db or "", RNA_AGENT_SYSTEM_ROOT)
        ),
    )
