"""LinearFold RNA secondary-structure prediction microservice."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


APP_DIR = Path(__file__).resolve().parent
_RNA_AGENT_SYSTEM_ROOT = APP_DIR.parents[1]

_STRUCTURE_LINE = re.compile(
    r"^([.()]+)\s+\(\s*(-?\d+(?:\.\d+)?)\s*\)\s*$"
)


def _canonical_linearfold_root() -> Path:
    return (_RNA_AGENT_SYSTEM_ROOT / "external_repos" / "LinearFold").resolve()


def _resolve_linearfold_root() -> Path:
    override = os.environ.get("LINEARFOLD_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _canonical_linearfold_root()


def _linearfold_binaries_exist(root: Path) -> Tuple[bool, str]:
    c = root / "bin" / "linearfold_c"
    v = root / "bin" / "linearfold_v"
    script = root / "linearfold"
    if not script.is_file():
        return False, f"Missing {script} (clone LinearFold and run make)."
    if not c.is_file() or not v.is_file():
        return False, f"Missing {c} or {v}; run `make` under {root}."
    return True, "ok"


def _normalize_sequence(raw: str) -> str:
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    merged = "".join(lines).upper().replace("T", "U")
    return re.sub(r"[^AUGC]", "", merged)


def _parse_linearfold_stdout(stdout: str) -> Tuple[str, float, str]:
    """Return (structure, mfe, sequence) from last prediction block."""
    lines = [ln.rstrip() for ln in stdout.splitlines() if ln.strip()]
    seq = ""
    structure = ""
    mfe = 0.0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            m = _STRUCTURE_LINE.match(nxt)
            if m and re.fullmatch(r"[AUGC]+", line.upper()):
                seq = line.upper()
                structure = m.group(1)
                mfe = float(m.group(2))
                i += 2
                continue
        i += 1
    if not structure:
        raise ValueError(
            "Could not parse LinearFold output; expected sequence line followed by "
            "'dot-bracket (energy)'."
        )
    return structure, mfe, seq


def _run_linearfold(
    root: Path,
    sequence: str,
    beam_size: int,
    use_vienna: bool,
    dangles: int,
) -> Tuple[str, float, str, str]:
    ok, msg = _linearfold_binaries_exist(root)
    if not ok:
        raise RuntimeError(msg)

    cmd = [
        sys.executable,
        str(root / "linearfold"),
        "-b",
        str(beam_size),
        "-d",
        str(dangles),
    ]
    if use_vienna:
        cmd.append("-V")

    proc = subprocess.run(
        cmd,
        cwd=str(root),
        input=sequence + "\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"LinearFold exited {proc.returncode}: {err}")

    structure, mfe, out_seq = _parse_linearfold_stdout(proc.stdout)
    backend = "LinearFold-V" if use_vienna else "LinearFold-C"
    if out_seq and out_seq != sequence:
        # Should not happen for single-sequence stdin; keep requested sequence in response.
        pass
    return structure, mfe, sequence, backend


app = FastAPI(
    title="LinearFold Service (Port 8015)",
    description="Linear-time RNA secondary structure prediction via LinearFold.",
    version="0.1.0-port8015",
)


class FoldRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence (plain or FASTA body).")
    beam_size: int = Field(default=100, ge=0, le=10000, description="Beam size; 0 means infinite beam.")
    use_vienna: bool = Field(
        default=False,
        description="If true, use LinearFold-V (Vienna parameters); else LinearFold-C.",
    )
    dangles: int = Field(default=2, description="0 or 2; passed to LinearFold --dangles.")


class FoldResponse(BaseModel):
    sequence: str
    structure: str
    mfe: float
    backend: str
    model: str = "LinearFold"


@app.get("/health")
def health() -> dict[str, str | bool]:
    root = _resolve_linearfold_root()
    ok, msg = _linearfold_binaries_exist(root)
    return {
        "status": "ok" if ok else "degraded",
        "linearfold_root": str(root),
        "binaries_ready": ok,
        "detail": msg if not ok else "LinearFold script and bin/linearfold_c|v present.",
    }


@app.post("/fold", response_model=FoldResponse)
def fold(payload: FoldRequest) -> FoldResponse:
    if payload.dangles not in (0, 2):
        raise HTTPException(status_code=400, detail="dangles must be 0 or 2.")

    root = _resolve_linearfold_root()
    sequence = _normalize_sequence(payload.sequence)
    if not sequence:
        raise HTTPException(status_code=400, detail="No RNA sequence after normalization.")

    try:
        structure, mfe, seq_out, backend = _run_linearfold(
            root,
            sequence,
            payload.beam_size,
            payload.use_vienna,
            payload.dangles,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if len(structure) != len(seq_out):
        raise HTTPException(
            status_code=500,
            detail="Structure length mismatch vs sequence.",
        )

    return FoldResponse(
        sequence=seq_out,
        structure=structure,
        mfe=mfe,
        backend=backend,
    )
