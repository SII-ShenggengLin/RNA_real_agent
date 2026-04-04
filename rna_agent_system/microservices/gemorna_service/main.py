"""GEMORNA microservice for mRNA CDS design."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GEMORNA_ROOT = PROJECT_ROOT / "external_repos" / "GEMORNA"
CHECKPOINT_DIR = GEMORNA_ROOT / "checkpoints"

app = FastAPI(
    title="GEMORNA Service",
    description="Run GEMORNA generation scripts through a FastAPI microservice.",
    version="0.1.0",
)


class CdsDesignRequest(BaseModel):
    protein_sequence: str = Field(
        ...,
        min_length=1,
        description="Protein sequence used by GEMORNA to generate CDS candidates.",
    )


class CdsDesignResponse(BaseModel):
    protein_sequence: str
    generated_sequence: str
    raw_output: str
    model: str = "GEMORNA-cds"


def _is_lfs_pointer(path: Path) -> bool:
    if not path.exists():
        return True
    prefix = path.read_bytes()[:64]
    return prefix.startswith(b"version https://git-lfs.github.com/spec/v1")


def _require_runtime_assets() -> None:
    required_paths = [
        GEMORNA_ROOT / "src" / "generate.py",
        GEMORNA_ROOT / "vocab" / "prot_vocab.pkl",
        GEMORNA_ROOT / "vocab" / "cds_vocab.pkl",
        CHECKPOINT_DIR / "gemorna_cds.pt",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise HTTPException(status_code=500, detail=f"Missing GEMORNA assets: {missing}")
    if _is_lfs_pointer(CHECKPOINT_DIR / "gemorna_cds.pt"):
        raise HTTPException(
            status_code=503,
            detail="GEMORNA checkpoint is still a Git LFS pointer. Run `git lfs pull` first.",
        )


def _extract_generated_sequence(stdout: str) -> str:
    matches = re.findall(r"[ACGTUNacgtun]{30,}", stdout)
    if not matches:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to parse GEMORNA output sequence from stdout: {stdout}",
        )
    return max(matches, key=len).upper().replace("T", "U")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate/cds", response_model=CdsDesignResponse)
def generate_cds(payload: CdsDesignRequest) -> CdsDesignResponse:
    _require_runtime_assets()
    command = [
        sys.executable,
        "src/generate.py",
        "--mode",
        "cds",
        "--ckpt_path",
        "checkpoints/gemorna_cds.pt",
        "--protein_seq",
        payload.protein_sequence.strip(),
    ]
    result = subprocess.run(
        command,
        cwd=GEMORNA_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "GEMORNA CDS generation failed.",
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
    generated_sequence = _extract_generated_sequence(result.stdout)
    return CdsDesignResponse(
        protein_sequence=payload.protein_sequence,
        generated_sequence=generated_sequence,
        raw_output=result.stdout.strip(),
    )
