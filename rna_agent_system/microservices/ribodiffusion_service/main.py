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
CKPT_DIR = RIBODIFFUSION_ROOT / "ckpts"
DEFAULT_CHECKPOINT_NAME = "exp_inf"
SERVICE_WORKDIR = PROJECT_ROOT / "workspace" / "ribodiffusion_service_runs"

app = FastAPI(
    title="RiboDiffusion Service",
    description=(
        "RNA inverse folding from tertiary structure using RiboDiffusion "
        "(third-party repo under external_repos/RiboDiffusion)."
    ),
    version="0.2.0",
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
    checkpoint_name: str = Field(
        default=DEFAULT_CHECKPOINT_NAME,
        description=(
            "Checkpoint basename without extension. "
            "Supported: 'exp_inf' (default), 'exp_inf_large'."
        ),
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


# Mapping from common RNA modified nucleotides (HETATM residue names)
# to canonical residue names so that the RiboDiffusion parser reads all
# residues as standard ATOM records.
_RNA_MODIFIED_RESIDUE_MAP: dict[str, str] = {
    # G derivatives
    "2MG": "  G",
    "M2G": "  G",
    "7MG": "  G",
    "OMG": "  G",
    "YYG": "  G",
    # C derivatives
    "5MC": "  C",
    "OMC": "  C",
    # U derivatives
    "PSU": "  U",
    "5MU": "  U",
    "H2U": "  U",
    # A derivatives
    "1MA": "  A",
}

# Standard RNA residue names that may appear in HETATM records of already-
# canonicalized PDB files (e.g., *_clean.pdb from the benchmark set).
_RNA_STANDARD_RESIDUES: set[str] = {"  A", "  C", "  G", "  U"}


def _preprocess_pdb_for_ribodiffusion(pdb_path: Path) -> tuple[Path, int]:
    """Rewrite HETATM modified RNA residues as ATOM canonical residues.

    RiboDiffusion's parser only reads ATOM lines, so modified nucleotides
    (e.g., 2MG, PSU) are dropped and the resulting sequence is shorter than
    the target. This function creates a temporary PDB where those residues
    are converted to standard A/C/G/U ATOM records.

    Returns:
        Tuple of (path to use for upstream inference, number of modified
        residue records that were canonicalized).
    """
    original_text = pdb_path.read_text(encoding="utf-8")
    modified_count = 0
    lines_out: list[str] = []
    for line in original_text.splitlines(keepends=True):
        if not (line.startswith("ATOM") or line.startswith("HETATM")):
            lines_out.append(line)
            continue
        record = line[:6]
        resi_name = line[17:20]
        if record == "HETATM" and (
            resi_name in _RNA_MODIFIED_RESIDUE_MAP
            or resi_name in _RNA_STANDARD_RESIDUES
        ):
            canonical = _RNA_MODIFIED_RESIDUE_MAP.get(resi_name, resi_name)
            new_line = "ATOM  " + line[6:17] + canonical + line[20:]
            lines_out.append(new_line)
            modified_count += 1
        else:
            lines_out.append(line)

    if modified_count == 0:
        return pdb_path, 0

    SERVICE_WORKDIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="ribodiffusion_pdb_", dir=SERVICE_WORKDIR))
    preprocessed_path = tmp_dir / f"{pdb_path.stem}_canonical.pdb"
    preprocessed_path.write_text("".join(lines_out), encoding="utf-8")
    return preprocessed_path, modified_count


def _resolve_checkpoint(checkpoint_name: str) -> Path:
    """Return absolute checkpoint path and verify existence."""
    ckpt_path = CKPT_DIR / f"{checkpoint_name}.pth"
    if not ckpt_path.exists():
        available = sorted(CKPT_DIR.glob("*.pth"))
        raise HTTPException(
            status_code=500,
            detail=(
                f"Missing RiboDiffusion checkpoint: {ckpt_path}. "
                f"Available checkpoints: {[p.name for p in available]}. "
                "Download from the upstream README link into `ckpts/` on the server."
            ),
        )
    return ckpt_path


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
        "default_checkpoint_present": (CKPT_DIR / f"{DEFAULT_CHECKPOINT_NAME}.pth").exists(),
        "default_checkpoint_path": str(CKPT_DIR / f"{DEFAULT_CHECKPOINT_NAME}.pth"),
        "available_checkpoints": [p.name for p in CKPT_DIR.glob("*.pth")],
        "service_workdir": str(SERVICE_WORKDIR),
    }


@app.post("/design/from-pdb", response_model=RiboDiffusionResponse)
def design_from_pdb(payload: RiboDiffusionRequest) -> RiboDiffusionResponse:
    ckpt_path = _resolve_checkpoint(payload.checkpoint_name)
    if not (RIBODIFFUSION_ROOT / "main.py").exists():
        raise HTTPException(status_code=500, detail=f"RiboDiffusion repo missing at {RIBODIFFUSION_ROOT}")

    pdb_path = _resolver.require_existing(payload.pdb_path, "PDB input")
    preprocessed_path, modified_count = _preprocess_pdb_for_ribodiffusion(pdb_path)
    pdb_stem = pdb_path.name.replace(".pdb", "").replace(".PDB", "")
    if "/" in pdb_stem:
        pdb_stem = pdb_stem.split("/")[-1]

    SERVICE_WORKDIR.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="ribodiffusion_", dir=SERVICE_WORKDIR))
    save_folder = run_root / payload.checkpoint_name

    cmd: list[str] = [
        sys.executable,
        "main.py",
        "--PDB_file",
        str(preprocessed_path),
        "--save_folder",
        str(save_folder),
        "--deterministic" if payload.deterministic else "--nodeterministic",
        f"--config.eval.n_samples={payload.n_samples}",
        f"--config.eval.sampling_steps={payload.sampling_steps}",
        f"--config.eval.model_path={ckpt_path}",
    ]
    if payload.cond_scale >= 0.0:
        cmd.append(f"--config.eval.cond_scale={payload.cond_scale}")
    if payload.dynamic_threshold:
        cmd.append("--config.eval.dynamic_threshold=True")

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

    preprocessed_annotation = ""
    if modified_count > 0:
        preprocessed_annotation = (
            f"[RiboDiffusionService] Preprocessed PDB: {preprocessed_path}; "
            f"canonicalized {modified_count} modified residue records.\n"
        )

    return RiboDiffusionResponse(
        input_pdb_path=str(pdb_path),
        pdb_id=pdb_stem,
        predicted_sequence=sequences[0],
        generated_sequences=sequences,
        output_fasta_paths=paths_str,
        recovery_rate=parse_recovery_rate(result.stdout),
        checkpoint_path=str(ckpt_path),
        service_output_dir=str(run_root),
        fasta_dir=str(fasta_dir),
        stdout=preprocessed_annotation + result.stdout.strip(),
        stderr=result.stderr.strip(),
    )
