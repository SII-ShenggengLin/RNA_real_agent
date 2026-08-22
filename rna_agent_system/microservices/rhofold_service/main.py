"""RhoFold microservice for RNA tertiary structure prediction."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RHOFOLD_ROOT = PROJECT_ROOT / "external_repos" / "RhoFold"
DEFAULT_CHECKPOINT_CANDIDATES = [
    RHOFOLD_ROOT / "pretrained" / "RhoFold_pretrained.pt",
    RHOFOLD_ROOT / "pretrained" / "rhofold_pretrained_params.pt",
    RHOFOLD_ROOT / "pretrained" / "model_20221010_params.pt",
]
SERVICE_WORKDIR = PROJECT_ROOT / "workspace" / "rhofold_service_runs"

app = FastAPI(
    title="RhoFold Service",
    description=(
        "Predict RNA tertiary structure with RhoFold+. "
        "Default deployment mode uses single-sequence prediction to avoid local MSA databases."
    ),
    version="0.1.0",
)


class RhoFoldPredictRequest(BaseModel):
    """RhoFold prediction request schema.

    """

    sequence: str = Field(..., min_length=1, description="RNA sequence (A/U/G/C).")
    single_seq_pred: bool = Field(
        default=True,
        description="Use sequence-only mode. Keep true unless you explicitly provide an A3M file.",
    )
    input_a3m_path: Optional[str] = Field(
        default=None,
        description="Optional absolute or repo-relative A3M path. Used only when single_seq_pred is false.",
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional checkpoint path. If omitted, common pretrained paths are checked.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional device string such as cpu, cuda, or cuda:0.",
    )
    relax_steps: int = Field(
        default=0,
        ge=0,
        description="Amber relaxation iterations. Set to 0 to skip relaxation and reduce runtime.",
    )
    timeout_seconds: int = Field(
        default=7200,
        ge=60,
        le=21600,
        description="Subprocess timeout for one prediction run.",
    )


class RhoFoldPredictResponse(BaseModel):
    """RhoFold prediction response schema.

    """

    sequence: str
    output_pdb_path: str
    secondary_structure_ct_path: Optional[str] = None
    results_npz_path: Optional[str] = None
    log_path: Optional[str] = None
    service_output_dir: str
    mean_plddt: Optional[float] = None
    model: str = "RhoFold+"
    stdout: str = ""
    stderr: str = ""


def _resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _normalize_sequence(sequence: str) -> str:
    normalized = sequence.strip().upper().replace("T", "U").replace("\n", "").replace(" ", "")
    if not normalized:
        raise HTTPException(status_code=400, detail="Sequence is empty after normalization.")
    invalid_chars = sorted({ch for ch in normalized if ch not in {"A", "U", "G", "C"}})
    if invalid_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Sequence contains invalid RNA characters: {''.join(invalid_chars)}",
        )
    return normalized


def _resolve_checkpoint_path(checkpoint_path: Optional[str]) -> Path:
    """Resolve checkpoint path with strict local-first policy.

    Never return a non-existent path to the downstream inference.py,
    because inference.py would trigger a HuggingFace download.
    """
    if checkpoint_path:
        resolved = _resolve_repo_path(checkpoint_path)
        if not resolved.exists():
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Requested RhoFold checkpoint does not exist: {resolved}. "
                    "Please place the checkpoint on the Linux server first."
                ),
            )
        return resolved

    for candidate in DEFAULT_CHECKPOINT_CANDIDATES:
        if candidate.exists():
            return candidate

    candidates_str = ", ".join(str(c) for c in DEFAULT_CHECKPOINT_CANDIDATES)
    raise HTTPException(
        status_code=500,
        detail=(
            "No local RhoFold checkpoint found. "
            f"Searched: {candidates_str}. "
            "Please download the pretrained weights to one of the above paths."
        ),
    )


def _mean_plddt_from_pdb(pdb_path: Path) -> Optional[float]:
    scores: List[float] = []
    with pdb_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("ATOM"):
                try:
                    scores.append(float(line[60:66].strip()))
                except ValueError:
                    continue
    if not scores:
        return None
    return sum(scores) / len(scores)


def _require_runtime_assets() -> None:
    required_paths = [
        RHOFOLD_ROOT / "inference.py",
        RHOFOLD_ROOT / "setup.py",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise HTTPException(status_code=500, detail=f"Missing RhoFold assets: {missing}")


@app.get("/health")
def health() -> dict:
    checkpoint_exists = any(candidate.exists() for candidate in DEFAULT_CHECKPOINT_CANDIDATES)
    return {
        "status": "ok",
        "repo_exists": RHOFOLD_ROOT.exists(),
        "checkpoint_present": checkpoint_exists,
        "default_single_seq_pred": True,
    }


@app.post("/predict", response_model=RhoFoldPredictResponse)
def predict(payload: RhoFoldPredictRequest) -> RhoFoldPredictResponse:
    _require_runtime_assets()

    sequence = _normalize_sequence(payload.sequence)
    checkpoint_path = _resolve_checkpoint_path(payload.checkpoint_path)
    SERVICE_WORKDIR.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="rhofold_", dir=SERVICE_WORKDIR))
    input_fasta = run_dir / "input.fasta"
    output_dir = run_dir / "output"
    input_fasta.write_text(f">query\n{sequence}\n", encoding="utf-8")

    command = [
        "python",
        "inference.py",
        "--input_fas",
        str(input_fasta),
        "--output_dir",
        str(output_dir),
        "--ckpt",
        str(checkpoint_path),
        "--relax_steps",
        str(payload.relax_steps),
    ]

    if payload.device:
        command.extend(["--device", payload.device])

    if payload.single_seq_pred:
        command.extend(["--single_seq_pred", "True"])
    elif payload.input_a3m_path:
        command.extend(["--input_a3m", str(_resolve_repo_path(payload.input_a3m_path))])

    result = subprocess.run(
        command,
        cwd=RHOFOLD_ROOT,
        capture_output=True,
        text=True,
        timeout=payload.timeout_seconds,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "RhoFold inference failed.",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command,
                "run_dir": str(run_dir),
            },
        )

    unrelaxed_model = output_dir / "unrelaxed_model.pdb"
    relaxed_model = output_dir / f"relaxed_{payload.relax_steps}_model.pdb"
    output_pdb_path = relaxed_model if payload.relax_steps > 0 and relaxed_model.exists() else unrelaxed_model

    if not output_pdb_path.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "RhoFold finished without producing the expected PDB output. "
                f"Checked: {output_pdb_path}"
            ),
        )

    ct_path = output_dir / "ss.ct"
    npz_path = output_dir / "results.npz"
    log_path = output_dir / "log.txt"

    return RhoFoldPredictResponse(
        sequence=sequence,
        output_pdb_path=str(output_pdb_path),
        secondary_structure_ct_path=str(ct_path) if ct_path.exists() else None,
        results_npz_path=str(npz_path) if npz_path.exists() else None,
        log_path=str(log_path) if log_path.exists() else None,
        service_output_dir=str(output_dir),
        mean_plddt=_mean_plddt_from_pdb(output_pdb_path),
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
    )
