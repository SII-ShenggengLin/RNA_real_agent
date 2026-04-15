"""LinearDesign microservice for protein-to-mRNA CDS design."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


APP_DIR = Path(__file__).resolve().parent
# ``main.py`` lives at ``rna_agent_system/microservices/lineardesign_service/main.py``:
# parents[0] = microservices/, parents[1] = rna_agent_system/ (do NOT use parents[2] = repo root).
_RNA_AGENT_SYSTEM_ROOT = APP_DIR.parents[1]


def _canonical_lineardesign_root() -> Path:
    """Project-standard path: ``rna_agent_system/external_repos/LinearDesign``."""
    return (_RNA_AGENT_SYSTEM_ROOT / "external_repos" / "LinearDesign").resolve()


def _resolve_lineardesign_root() -> Path:
    """Resolve LinearDesign checkout: canonical path under ``rna_agent_system/external_repos/``,
    or ``LINEARDESIGN_ROOT`` when set (must contain ``bin/LinearDesign_2D`` after ``make``).
    """
    override = os.environ.get("LINEARDESIGN_ROOT", "").strip()
    if override:
        root = Path(override).expanduser().resolve()
        if (root / "bin" / "LinearDesign_2D").exists():
            return root

    canonical = _canonical_lineardesign_root()
    if (canonical / "bin" / "LinearDesign_2D").exists():
        return canonical

    return canonical


app = FastAPI(
    title="LinearDesign Service (Port 8014 Deployment)",
    description="Design mRNA CDS from a protein sequence via LinearDesign.",
    version="0.1.0-port8014",
)


class LinearDesignRequest(BaseModel):
    protein_sequence: str = Field(..., min_length=1, description="Input protein sequence.")
    lambda_value: float = Field(
        default=0.0,
        ge=0.0,
        description="LinearDesign lambda balancing MFE and CAI.",
    )
    codon_usage_path: Optional[str] = Field(
        default=None,
        description="Optional codon usage CSV path. Defaults to human table in LinearDesign repo.",
    )
    verbose: bool = Field(default=False, description="Enable verbose output in LinearDesign.")


class LinearDesignResponse(BaseModel):
    generated_sequence: str
    structure: str
    mfe: float
    cai_score: float
    lambda_value: float
    codon_usage_path: str
    model: str = "LinearDesign"
    raw_output: str
    stderr: str


def _resolve_codon_usage_path(lineardesign_root: Path, path_value: Optional[str]) -> Path:
    default_path = lineardesign_root / "codon_usage_freq_table_human.csv"
    if not path_value:
        return default_path

    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate

    under_ld = (lineardesign_root / candidate).resolve()
    if under_ld.exists():
        return under_ld

    repo_relative = (_RNA_AGENT_SYSTEM_ROOT / candidate).resolve()
    if repo_relative.exists():
        return repo_relative

    return under_ld


def _extract_output_fields(raw_output: str) -> tuple[str, str, float, float]:
    seq_match = re.search(r"mRNA sequence:\s*([AUGC]+)", raw_output)
    structure_match = re.search(r"mRNA structure:\s*([().]+)", raw_output)
    mfe_match = re.search(r"mRNA folding free energy:\s*([-+]?\d*\.?\d+)", raw_output)
    cai_match = re.search(r"mRNA CAI:\s*([-+]?\d*\.?\d+)", raw_output)

    if not seq_match or not structure_match or not mfe_match or not cai_match:
        raise ValueError(
            "LinearDesign output parsing failed. "
            "Expected mRNA sequence, structure, MFE, and CAI fields."
        )

    return (
        seq_match.group(1).strip(),
        structure_match.group(1).strip(),
        float(mfe_match.group(1)),
        float(cai_match.group(1)),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate/cds", response_model=LinearDesignResponse)
def generate_cds(payload: LinearDesignRequest) -> LinearDesignResponse:
    lineardesign_root = _resolve_lineardesign_root()
    lineardesign_bin = lineardesign_root / "bin" / "LinearDesign_2D"
    if not lineardesign_bin.exists():
        canonical = _canonical_lineardesign_root()
        raise HTTPException(
            status_code=500,
            detail=(
                f"LinearDesign binary not found: {lineardesign_bin}. "
                f"Expected checkout at {canonical} (run `make` there), "
                "or set LINEARDESIGN_ROOT to a directory that contains bin/LinearDesign_2D."
            ),
        )

    codon_usage_path = _resolve_codon_usage_path(lineardesign_root, payload.codon_usage_path)
    if not codon_usage_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Codon usage table not found: {codon_usage_path}",
        )

    protein_sequence = payload.protein_sequence.strip().upper()
    if not protein_sequence:
        raise HTTPException(status_code=400, detail="Protein sequence is empty.")

    cmd = [
        str(lineardesign_bin),
        f"{payload.lambda_value}",
        "1" if payload.verbose else "0",
        str(codon_usage_path),
    ]
    env = os.environ.copy()
    process = subprocess.run(
        cmd,
        input=protein_sequence + "\n",
        text=True,
        capture_output=True,
        cwd=str(lineardesign_root),
        env=env,
        check=False,
    )

    if process.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=(
                "LinearDesign execution failed. "
                f"returncode={process.returncode}; stderr={process.stderr.strip()}"
            ),
        )

    try:
        generated_sequence, structure, mfe, cai_score = _extract_output_fields(process.stdout)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return LinearDesignResponse(
        generated_sequence=generated_sequence,
        structure=structure,
        mfe=mfe,
        cai_score=cai_score,
        lambda_value=payload.lambda_value,
        codon_usage_path=str(codon_usage_path),
        raw_output=process.stdout,
        stderr=process.stderr,
    )
