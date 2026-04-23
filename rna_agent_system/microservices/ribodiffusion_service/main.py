"""RiboDiffusion microservice: PDB-conditioned RNA inverse folding via diffusion."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Ensure microservices/ is on sys.path for shared common_utils
_MICROSERVICES_DIR = Path(__file__).resolve().parents[1]
if str(_MICROSERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(_MICROSERVICES_DIR))

from common_utils import PathResolver, parse_recovery_rate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
_resolver = PathResolver(PROJECT_ROOT, REPO_ROOT)
RIBODIFFUSION_ROOT = PROJECT_ROOT / "external_repos" / "RiboDiffusion"
DEFAULT_CHECKPOINT = RIBODIFFUSION_ROOT / "ckpts" / "exp_inf.pth"
SERVICE_WORKDIR = PROJECT_ROOT / "workspace" / "ribodiffusion_service_runs"

app = FastAPI(
    title="RiboDiffusion Service",
    description=(
        "RNA inverse folding from tertiary structure using RiboDiffusion "
        "(third-party repo under external_repos/RiboDiffusion)."
    ),
    version="0.1.0",
)


class RiboDiffusionRequest(BaseModel):
    pdb_path: str = Field(
        ...,
        description="Absolute path or repo-relative path to an RNA-containing PDB file.",
    )
    n_samples: int = Field(default=1, ge=1, le=64)
    sampling_steps: int = Field(default=50, ge=1, le=500)
    cond_scale: float = Field(
        default=-1.0,
        ge=-1.0,
        description=(
            "Classifier-free guidance-style conditional scale; "
            "use -1 (default upstream) to disable. Typical alternative: 0.4 per paper README."
        ),
    )
    dynamic_threshold: bool = Field(
        default=False,
        description="Enable dynamic thresholding during sampling (see upstream README).",
    )
    deterministic: bool = Field(
        default=True,
        description="If True, upstream sets a fixed random seed for reproducibility.",
    )
    device: int = Field(default=0, ge=0, description="Logical CUDA device index (CUDA_VISIBLE_DEVICES).")
    timeout_seconds: int = Field(default=7200, ge=300, le=28800)


class RiboDiffusionResponse(BaseModel):
    input_pdb_path: str
    pdb_id: str
    predicted_sequence: str
    generated_sequences: list[str]
    output_fasta_paths: list[str]
    recovery_rate: Optional[float] = None
    checkpoint_path: str
    service_output_dir: str
    fasta_dir: str
    model: str = "RiboDiffusion"
    stdout: str = ""
    stderr: str = ""


def _require_checkpoint() -> Path:
    if not DEFAULT_CHECKPOINT.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                f"Missing RiboDiffusion checkpoint: {DEFAULT_CHECKPOINT}. "
                "Download `exp_inf.pth` from the upstream README link into `ckpts/` on the server."
            ),
        )
    return DEFAULT_CHECKPOINT


def _read_fasta_sequence(fasta_path: Path) -> str:
    lines = [
        line.strip()
        for line in fasta_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith(">")
    ]
    if not lines:
        raise HTTPException(
            status_code=500,
            detail=f"Empty or invalid FASTA (no sequence lines): {fasta_path}",
        )
    return "".join(lines).upper().replace("T", "U")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "repo_exists": RIBODIFFUSION_ROOT.exists(),
        "main_py": (RIBODIFFUSION_ROOT / "main.py").exists(),
        "default_checkpoint_present": DEFAULT_CHECKPOINT.exists(),
        "default_checkpoint_path": str(DEFAULT_CHECKPOINT),
        "service_workdir": str(SERVICE_WORKDIR),
    }


@app.post("/design/from-pdb", response_model=RiboDiffusionResponse)
def design_from_pdb(payload: RiboDiffusionRequest) -> RiboDiffusionResponse:
    _require_checkpoint()
    if not (RIBODIFFUSION_ROOT / "main.py").exists():
        raise HTTPException(status_code=500, detail=f"RiboDiffusion repo missing at {RIBODIFFUSION_ROOT}")

    pdb_path = _resolver.require_existing(payload.pdb_path, "PDB input")
    pdb_stem = pdb_path.name.replace(".pdb", "").replace(".PDB", "")
    if "/" in pdb_stem:
        pdb_stem = pdb_stem.split("/")[-1]

    SERVICE_WORKDIR.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="ribodiffusion_", dir=SERVICE_WORKDIR))
    save_folder = run_root / "exp_inf"

    cmd: list[str] = [
        sys.executable,
        "main.py",
        "--PDB_file",
        str(pdb_path),
        "--save_folder",
        str(save_folder),
        "--deterministic=true" if payload.deterministic else "--deterministic=false",
        f"--config.eval.n_samples={payload.n_samples}",
        f"--config.eval.sampling_steps={payload.sampling_steps}",
    ]
    if payload.cond_scale >= 0.0:
        cmd.append(f"--config.eval.cond_scale={payload.cond_scale}")
    if payload.dynamic_threshold:
        cmd.append("--config.eval.dynamic_threshold=true")

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(payload.device)

    result = subprocess.run(
        cmd,
        cwd=str(RIBODIFFUSION_ROOT),
        capture_output=True,
        text=True,
        timeout=payload.timeout_seconds,
        env=env,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "RiboDiffusion inference failed.",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": cmd,
                "cwd": str(RIBODIFFUSION_ROOT),
                "run_root": str(run_root),
            },
        )

    fasta_dir = save_folder / "fasta"
    if not fasta_dir.is_dir():
        raise HTTPException(
            status_code=500,
            detail=(
                "RiboDiffusion did not produce a fasta/ directory. "
                f"save_folder={save_folder}; stdout={result.stdout}; stderr={result.stderr}"
            ),
        )

    fasta_files = sorted(fasta_dir.glob("*.fasta"))
    if not fasta_files:
        raise HTTPException(
            status_code=500,
            detail=f"No .fasta files under {fasta_dir}; stdout={result.stdout}; stderr={result.stderr}",
        )

    sequences = [_read_fasta_sequence(fp) for fp in fasta_files]
    paths_str = [str(fp) for fp in fasta_files]

    return RiboDiffusionResponse(
        input_pdb_path=str(pdb_path),
        pdb_id=pdb_stem,
        predicted_sequence=sequences[0],
        generated_sequences=sequences,
        output_fasta_paths=paths_str,
        recovery_rate=parse_recovery_rate(result.stdout),
        checkpoint_path=str(DEFAULT_CHECKPOINT),
        service_output_dir=str(run_root),
        fasta_dir=str(fasta_dir),
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
    )
