"""RhoDesign microservice for RNA structure-to-sequence design."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RHODESIGN_ROOT = PROJECT_ROOT / "external_repos" / "RhoDesign"
RHODESIGN_SRC = RHODESIGN_ROOT / "src"
CHECKPOINT_DIR = RHODESIGN_ROOT / "checkpoint"
SERVICE_WORKDIR = PROJECT_ROOT / "workspace" / "rhodesign_service_runs"

WITH_2D_CHECKPOINT = CHECKPOINT_DIR / "ss_apexp_best.pth"
WITHOUT_2D_CHECKPOINT = CHECKPOINT_DIR / "no_ss_apexp_best.pth"

app = FastAPI(
    title="RhoDesign Service",
    description=(
        "Design RNA sequences from tertiary structure inputs with RhoDesign. "
        "Supports both PDB-only mode and PDB plus secondary-structure contact-map mode."
    ),
    version="0.1.0",
)


class RhoDesignRequest(BaseModel):
    pdb_path: str = Field(
        ...,
        description=(
            "Absolute path or repo-relative path to the input PDB structure file. "
            "In this project the file should normally live under workspace/."
        ),
    )
    secondary_structure_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional absolute path or repo-relative path to a secondary-structure "
            "contact map in .npy format. If omitted, the service uses PDB-only mode."
        ),
    )
    temperature: float = Field(
        default=1e-5,
        gt=0.0,
        description=(
            "Sampling temperature. Lower values favor higher recovery; higher values "
            "increase sequence diversity."
        ),
    )
    device: int = Field(
        default=0,
        ge=0,
        description="CUDA device index passed to upstream RhoDesign scripts.",
    )
    timeout_seconds: int = Field(
        default=3600,
        ge=60,
        le=21600,
        description="Subprocess timeout for one RhoDesign generation run.",
    )


class RhoDesignResponse(BaseModel):
    input_pdb_path: str
    secondary_structure_path: Optional[str] = None
    output_fasta_path: str
    predicted_sequence: str
    recovery_rate: Optional[float] = None
    used_secondary_structure: bool
    checkpoint_path: str
    service_output_dir: str
    model: str = "RhoDesign"
    stdout: str = ""
    stderr: str = ""


def _resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _require_existing_path(path_str: str, label: str) -> Path:
    path = _resolve_repo_path(path_str)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"{label} does not exist: {path}")
    return path


def _require_runtime_assets() -> None:
    required_paths = [
        RHODESIGN_SRC / "inference.py",
        RHODESIGN_SRC / "inference_without2d.py",
        RHODESIGN_SRC / "RhoDesign.py",
        RHODESIGN_SRC / "RhoDesign_without2d.py",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise HTTPException(status_code=500, detail=f"Missing RhoDesign assets: {missing}")


def _select_checkpoint(use_secondary_structure: bool) -> Path:
    checkpoint_path = WITH_2D_CHECKPOINT if use_secondary_structure else WITHOUT_2D_CHECKPOINT
    if not checkpoint_path.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                f"Missing RhoDesign checkpoint: {checkpoint_path}. "
                "Please place the real `.pth` file on the Linux server before running."
            ),
        )
    return checkpoint_path


def _parse_recovery_rate(stdout: str) -> Optional[float]:
    match = re.search(r"recovery rate:\s*([0-9]*\.?[0-9]+)", stdout)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _read_predicted_sequence(fasta_path: Path) -> str:
    lines = [
        line.strip()
        for line in fasta_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith(">")
    ]
    if not lines:
        raise HTTPException(
            status_code=500,
            detail=f"RhoDesign output FASTA does not contain a predicted sequence: {fasta_path}",
        )
    return "".join(lines).upper().replace("T", "U")


def _locate_output_fasta(output_dir: Path) -> Path:
    fasta_files = sorted(output_dir.glob("*.fasta"))
    if not fasta_files:
        raise HTTPException(
            status_code=500,
            detail=(
                "RhoDesign finished without producing a FASTA output file. "
                f"Checked directory: {output_dir}"
            ),
        )
    return max(fasta_files, key=lambda path: path.stat().st_mtime)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "repo_exists": RHODESIGN_ROOT.exists(),
        "with_2d_checkpoint_present": WITH_2D_CHECKPOINT.exists(),
        "without_2d_checkpoint_present": WITHOUT_2D_CHECKPOINT.exists(),
        "service_workdir": str(SERVICE_WORKDIR),
    }


@app.post("/design/from-structure", response_model=RhoDesignResponse)
def design_from_structure(payload: RhoDesignRequest) -> RhoDesignResponse:
    _require_runtime_assets()

    pdb_path = _require_existing_path(payload.pdb_path, "PDB input")
    use_secondary_structure = payload.secondary_structure_path is not None
    secondary_structure_path: Optional[Path] = None
    if payload.secondary_structure_path:
        secondary_structure_path = _require_existing_path(
            payload.secondary_structure_path,
            "Secondary-structure input",
        )

    checkpoint_path = _select_checkpoint(use_secondary_structure)

    SERVICE_WORKDIR.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="rhodesign_", dir=SERVICE_WORKDIR))
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    script_name = "inference.py" if use_secondary_structure else "inference_without2d.py"
    command = [
        sys.executable,
        script_name,
        "-pdb",
        str(pdb_path),
        "-save",
        str(output_dir),
        "-device",
        str(payload.device),
        "-temp",
        str(payload.temperature),
    ]
    if secondary_structure_path is not None:
        command.extend(["-ss", str(secondary_structure_path)])

    result = subprocess.run(
        command,
        cwd=RHODESIGN_SRC,
        capture_output=True,
        text=True,
        timeout=payload.timeout_seconds,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "RhoDesign inference failed.",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command,
                "run_dir": str(run_dir),
                "checkpoint_path": str(checkpoint_path),
            },
        )

    output_fasta_path = _locate_output_fasta(output_dir)
    predicted_sequence = _read_predicted_sequence(output_fasta_path)

    return RhoDesignResponse(
        input_pdb_path=str(pdb_path),
        secondary_structure_path=str(secondary_structure_path) if secondary_structure_path else None,
        output_fasta_path=str(output_fasta_path),
        predicted_sequence=predicted_sequence,
        recovery_rate=_parse_recovery_rate(result.stdout),
        used_secondary_structure=use_secondary_structure,
        checkpoint_path=str(checkpoint_path),
        service_output_dir=str(output_dir),
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
    )
