"""FastAPI microservice wrapping Bowtie2 for short-sequence alignment.

"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# rna_agent_system/microservices/bowtie2_service/main.py -> parents[2] == rna_agent_system
RNA_AGENT_SYSTEM_ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(
    title="Bowtie2 short-alignment service",
    description="Run bowtie2 --local for fast short-sequence (e.g. siRNA) alignment against a subject FASTA or pre-built index.",
    version="0.1.0",
)


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _resolve_host_path(raw: str) -> Path:
    """Resolve repo-relative or absolute paths as seen from the Linux server."""
    text = raw.strip().strip('"').strip("'")
    p = Path(text).expanduser()
    if p.is_absolute():
        return p.resolve()
    root_name = RNA_AGENT_SYSTEM_ROOT.name
    if text.startswith(f"{root_name}/"):
        text = text[len(f"{root_name}/"):]
    candidate = (RNA_AGENT_SYSTEM_ROOT / text).resolve()
    if candidate.exists() or candidate.parent.exists():
        return candidate
    rel = Path(text).resolve()
    return rel


def _fasta_from_sequence_text(raw: str, default_id: str = "query") -> str:
    """Build a one-entry FASTA from plain or FASTA-like text; normalize RNA U to DNA T for bowtie2."""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.lstrip().startswith(">")]
    seq = "".join(lines).upper().replace("U", "T")
    seq = re.sub(r"[^ACGTN]", "", seq)
    if not seq:
        raise ValueError("No nucleotide letters found in query after normalization.")
    header_lines = [ln for ln in raw.splitlines() if ln.strip().startswith(">")]
    header = header_lines[0].lstrip(">").strip() if header_lines else default_id
    return f">{header}\n{seq}\n"


class Bowtie2AlignRequest(BaseModel):
    query_filepath: str = Field(
        ...,
        description="Absolute or rna_agent_system-relative path to query FASTA or plain sequence file.",
    )
    subject_fasta_path: Optional[str] = Field(
        default=None,
        description="Subject multi-FASTA to index with bowtie2-build (mutually exclusive with subject_index).",
    )
    subject_index: Optional[str] = Field(
        default=None,
        description="Existing bowtie2 index prefix (mutually exclusive with subject_fasta_path).",
    )
    mode: str = Field(
        default="local",
        description="local | end-to-end. 'local' allows soft-clipping and is preferred for short oligos.",
    )
    k: int = Field(default=50, ge=1, le=10000, description="Report up to <int> alignments per read.")
    score_min: str = Field(
        default="G,20,8",
        description="bowtie2 --score-min function (default G,20,8).",
    )
    bowtie2_timeout_sec: int = Field(default=300, ge=10, le=86400)


class Bowtie2AlignResponse(BaseModel):
    hit_count: int
    hits_preview: str
    preview_truncated: bool
    tabular_output: str = Field(
        default="",
        description="Full bowtie2 tabular output (SAM-like simplified).",
    )
    tabular_output_truncated: bool = False
    bowtie2_command: str
    bowtie2_build_command: Optional[str] = None
    stderr: str
    subject_mode: str
    resolved_query_path: str
    resolved_subject: str
    model: str = "bowtie2"


@app.get("/health")
def health() -> dict[str, Any]:
    bowtie2 = _which("bowtie2")
    bowtie2_build = _which("bowtie2-build")
    ok = bool(bowtie2 and bowtie2_build)
    return {
        "status": "ok" if ok else "degraded",
        "bowtie2": bowtie2 or "",
        "bowtie2_build": bowtie2_build or "",
        "rna_agent_system_root": str(RNA_AGENT_SYSTEM_ROOT),
    }


@app.post("/align", response_model=Bowtie2AlignResponse)
def run_bowtie2(payload: Bowtie2AlignRequest) -> Bowtie2AlignResponse:
    if not payload.subject_fasta_path and not payload.subject_index:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of subject_fasta_path or subject_index.",
        )
    if payload.subject_fasta_path and payload.subject_index:
        raise HTTPException(
            status_code=400,
            detail="Provide only one of subject_fasta_path or subject_index.",
        )

    bowtie2_bin = _which("bowtie2")
    bowtie2_build_bin = _which("bowtie2-build")
    if not bowtie2_bin:
        raise HTTPException(status_code=503, detail="bowtie2 not found in PATH.")
    if payload.subject_fasta_path and not bowtie2_build_bin:
        raise HTTPException(status_code=503, detail="bowtie2-build not found in PATH (required for subject FASTA).")

    qpath = _resolve_host_path(payload.query_filepath)
    if not qpath.is_file():
        raise HTTPException(status_code=400, detail=f"Query file not found: {qpath}")

    raw_query = qpath.read_text(encoding="utf-8", errors="replace")
    query_fasta = _fasta_from_sequence_text(raw_query, default_id=qpath.stem)

    mode = payload.mode.lower().strip()
    if mode not in {"local", "end-to-end"}:
        raise HTTPException(status_code=400, detail="mode must be local or end-to-end.")

    bowtie2_build_cmd: Optional[str] = None
    index_prefix: str

    with tempfile.TemporaryDirectory(prefix="bowtie2svc_") as tmp:
        tmp_path = Path(tmp)
        query_file = tmp_path / "query.fa"
        query_file.write_text(query_fasta, encoding="utf-8")

        if payload.subject_index:
            idx_path = _resolve_host_path(payload.subject_index)
            index_prefix = str(idx_path)
        else:
            assert payload.subject_fasta_path is not None
            subj_path = _resolve_host_path(payload.subject_fasta_path)
            if not subj_path.is_file():
                raise HTTPException(status_code=400, detail=f"Subject FASTA not found: {subj_path}")
            index_prefix = str(tmp_path / "subject_idx")
            bowtie2_build_cmd = " ".join(
                [bowtie2_build_bin, str(subj_path), index_prefix]
            )
            mb = subprocess.run(
                [bowtie2_build_bin, str(subj_path), index_prefix],
                capture_output=True,
                text=True,
                timeout=3600,
                check=False,
            )
            if mb.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"bowtie2-build failed (exit {mb.returncode}): {mb.stderr or mb.stdout}",
                )

        bt2_args: list[str] = [
            bowtie2_bin,
            f"--{mode}",
            "-x", index_prefix,
            "-f", str(query_file),
            "-k", str(int(payload.k)),
            "--score-min", payload.score_min.strip(),
            "--no-unal",
            "--quiet",
        ]

        bowtie2_command = " ".join(bt2_args)
        proc = subprocess.run(
            bt2_args,
            capture_output=True,
            text=True,
            timeout=int(payload.bowtie2_timeout_sec),
            check=False,
        )
        # bowtie2 returns 0 even when some reads don't align (because of --no-unal)
        # but returns non-zero for actual errors when --no-unal is used? Actually
        # bowtie2 exit code 0 = success, 1 = reads failed to align (ok with --no-unal)
        if proc.returncode not in (0, 1):
            raise HTTPException(
                status_code=500,
                detail=f"bowtie2 failed (exit {proc.returncode}): {proc.stderr or proc.stdout}",
            )

        stdout = proc.stdout or ""
        lines = [ln for ln in stdout.splitlines() if ln.strip() and not ln.startswith("@")]
        hit_count = len(lines)
        preview_lines = lines[:30]
        hits_preview = "\n".join(preview_lines)
        preview_truncated = hit_count > len(preview_lines)
        max_tab = 500_000
        tab_body = stdout
        tab_trunc = len(tab_body) > max_tab
        if tab_trunc:
            tab_body = tab_body[:max_tab]

    return Bowtie2AlignResponse(
        hit_count=hit_count,
        hits_preview=hits_preview,
        preview_truncated=preview_truncated,
        tabular_output=tab_body,
        tabular_output_truncated=tab_trunc,
        bowtie2_command=bowtie2_command,
        bowtie2_build_command=bowtie2_build_cmd,
        stderr=(proc.stderr or "")[:8000],
        subject_mode="fasta" if payload.subject_fasta_path else "index",
        resolved_query_path=str(qpath),
        resolved_subject=str(_resolve_host_path(payload.subject_fasta_path or payload.subject_index or "")),
        model="bowtie2",
    )
