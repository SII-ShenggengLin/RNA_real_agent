"""ODesign microservice for biomolecular design inference."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
ODESIGN_ROOT = PROJECT_ROOT / "external_repos" / "ODesign"
DEFAULT_CKPT_ROOT = ODESIGN_ROOT / "ckpt"
DEFAULT_DATA_ROOT = ODESIGN_ROOT / "data"
OUTPUTS_ROOT = ODESIGN_ROOT / "outputs"

COMPONENT_CIF = "components.v20240608.cif"
COMPONENT_PKL = "components.v20240608.cif.rdkit_mol.pkl"

try:
    import torch
except Exception:  # pragma: no cover - best effort health reporting only
    torch = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common_utils import PathResolver, _is_lfs_pointer  # noqa: E402

path_resolver = PathResolver(PROJECT_ROOT, REPO_ROOT)


app = FastAPI(
    title="ODesign Service",
    description=(
        "Run ODesign inference through a FastAPI microservice. "
        "This wrapper is intended for Linux + CUDA deployment on the server."
    ),
    version="0.1.0",
)


class ODesignInferenceRequest(BaseModel):
    """ODesign inference request schema.

    """
    input_json_path: str = Field(
        ...,
        description=(
            "Absolute path or repo-relative path to an ODesign input JSON file. "
            "The JSON should follow the upstream ODesign examples format."
        ),
    )
    infer_model_name: str = Field(
        default="odesign_base_na_rigid",
        description=(
            "Upstream ODesign model name, for example `odesign_base_na_rigid` or "
            "`odesign_base_prot_flex`."
        ),
    )
    design_modality: str = Field(
        default="rna",
        description="Design modality: `protein`, `ligand`, `dna`, or `rna`.",
    )
    exp_name: Optional[str] = Field(
        default=None,
        description="Optional custom experiment name. A unique name is generated when omitted.",
    )
    ckpt_root_dir: Optional[str] = Field(
        default=None,
        description="Optional checkpoint root directory override.",
    )
    data_root_dir: Optional[str] = Field(
        default=None,
        description="Optional inference data root directory override.",
    )
    seeds_json: str = Field(
        default="[42]",
        description="JSON list string of integer seeds, for example `[42]` or `[42, 123]`.",
    )
    n_sample: int = Field(
        default=1,
        ge=1,
        le=50,
        description="Number of generated samples per seed.",
    )
    use_msa: bool = Field(
        default=False,
        description="Whether the input JSON provides MSA features for ODesign inference.",
    )
    num_workers: int = Field(
        default=2,
        ge=0,
        le=32,
        description="Dataloader worker count passed through to ODesign.",
    )
    cuda_visible_devices: Optional[str] = Field(
        default=None,
        description="Optional CUDA_VISIBLE_DEVICES override, for example `0` or `0,1`.",
    )
    enable_partial_diff: bool = Field(
        default=False,
        description="Whether to enable ODesign partial diffusion mode.",
    )
    snr: float = Field(
        default=0.1,
        gt=0.0,
        description="Partial diffusion signal-to-noise ratio.",
    )
    invfold_topk: int = Field(
        default=1,
        ge=1,
        le=20,
        description="Number of designed sequences per backbone structure (inverse folding top-k).",
    )
    invfold_temp: float = Field(
        default=1.0,
        gt=0.0,
        description="Inverse folding sampling temperature.",
    )
    invfold_use_beam: bool = Field(
        default=True,
        description="Whether to use beam search in inverse folding.",
    )
    timeout_seconds: int = Field(
        default=14400,
        ge=300,
        le=86400,
        description="Subprocess timeout for one ODesign inference request.",
    )


class ODesignInferenceResponse(BaseModel):
    """ODesign inference response schema.

    """
    input_json_path: str
    infer_model_name: str
    design_modality: str
    exp_name: str
    ckpt_root_dir: str
    data_root_dir: str
    output_dir: str
    prediction_filepaths: list[str]
    sample_names: list[str]
    run_log_path: Optional[str] = None
    error_filepaths: list[str]
    stdout: str = ""
    stderr: str = ""
    timeout_seconds: int = 14400
    model: str = "ODesign"


def _normalize_exp_name(exp_name: Optional[str], infer_model_name: str) -> str:
    if exp_name:
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in exp_name.strip())
        return safe or f"odesign_{infer_model_name}_{uuid4().hex[:8]}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"odesign_{infer_model_name}_{timestamp}_{uuid4().hex[:6]}"


def _resolve_runtime_dir(path_str: Optional[str], default_path: Path) -> Path:
    if path_str:
        return path_resolver.resolve(path_str)
    return default_path


def _parse_seeds_json(seeds_json: str) -> list[int]:
    import json

    try:
        parsed = json.loads(seeds_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid seeds_json: {exc}") from exc
    if not isinstance(parsed, list) or not parsed:
        raise HTTPException(status_code=400, detail="seeds_json must be a non-empty JSON list.")
    seeds: list[int] = []
    for item in parsed:
        if not isinstance(item, int):
            raise HTTPException(status_code=400, detail="seeds_json must contain integers only.")
        seeds.append(int(item))
    return seeds


def _require_runtime_assets(
    infer_model_name: str,
    design_modality: str,
    ckpt_root_dir: Path,
    data_root_dir: Path,
) -> None:
    required_paths = [
        ODESIGN_ROOT / "scripts" / "inference.py",
        ODESIGN_ROOT / "configs" / "inference.yaml",
        ckpt_root_dir / f"{infer_model_name}.pt",
        ckpt_root_dir / f"oinvfold_{design_modality}.ckpt",
        data_root_dir / COMPONENT_CIF,
        data_root_dir / COMPONENT_PKL,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing ODesign runtime assets. On the Linux server, place the required "
                f"checkpoints and data files before running inference: {missing}"
            ),
        )

    pointer_candidates = [
        ckpt_root_dir / f"{infer_model_name}.pt",
        ckpt_root_dir / f"oinvfold_{design_modality}.ckpt",
    ]
    pointer_paths = [str(path) for path in pointer_candidates if _is_lfs_pointer(path)]
    if pointer_paths:
        raise HTTPException(
            status_code=503,
            detail=(
                "One or more ODesign checkpoints are still Git LFS pointers. "
                f"Download the real files before inference: {pointer_paths}"
            ),
        )


def _list_run_dirs(exp_name: str) -> list[Path]:
    run_root = OUTPUTS_ROOT / exp_name
    if not run_root.exists():
        return []
    return [path for path in run_root.iterdir() if path.is_dir()]


def _locate_output_dir(exp_name: str, before_dirs: list[Path]) -> Path:
    after_dirs = _list_run_dirs(exp_name)
    before_set = {path.resolve() for path in before_dirs}
    new_dirs = [path for path in after_dirs if path.resolve() not in before_set]
    candidates = new_dirs or after_dirs
    if not candidates:
        raise HTTPException(
            status_code=500,
            detail=(
                "ODesign completed but no output directory was found under "
                f"{OUTPUTS_ROOT / exp_name}"
            ),
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _collect_prediction_files(output_dir: Path) -> list[Path]:
    return sorted(output_dir.glob("**/predictions/*.cif"))


def _collect_error_files(output_dir: Path) -> list[Path]:
    error_dir = output_dir / "errors"
    if not error_dir.exists():
        return []
    return sorted(error_dir.glob("*.txt"))


@app.get("/health")
def health() -> dict[str, object]:
    cuda_available = bool(torch.cuda.is_available()) if torch is not None else False
    torch_version = getattr(torch, "__version__", None) if torch is not None else None
    return {
        "status": "ok",
        "repo_exists": ODESIGN_ROOT.exists(),
        "outputs_root": str(OUTPUTS_ROOT),
        "default_ckpt_root": str(DEFAULT_CKPT_ROOT),
        "default_data_root": str(DEFAULT_DATA_ROOT),
        "default_na_checkpoint_present": (DEFAULT_CKPT_ROOT / "odesign_base_na_rigid.pt").exists(),
        "default_rna_invfold_checkpoint_present": (
            DEFAULT_CKPT_ROOT / "oinvfold_rna.ckpt"
        ).exists(),
        "components_cif_present": (DEFAULT_DATA_ROOT / COMPONENT_CIF).exists(),
        "components_rdkit_pickle_present": (DEFAULT_DATA_ROOT / COMPONENT_PKL).exists(),
        "cuda_available": cuda_available,
        "torch_version": torch_version,
    }


@app.post("/design/from-json", response_model=ODesignInferenceResponse)
def design_from_json(payload: ODesignInferenceRequest) -> ODesignInferenceResponse:
    if payload.design_modality not in {"protein", "ligand", "dna", "rna"}:
        raise HTTPException(
            status_code=400,
            detail="design_modality must be one of: protein, ligand, dna, rna.",
        )

    if torch is None or not torch.cuda.is_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "ODesign currently requires a CUDA-enabled Linux environment. "
                "Please run this service on your GPU server."
            ),
        )

    input_json_path = path_resolver.require_existing(payload.input_json_path, "Input JSON")
    ckpt_root_dir = _resolve_runtime_dir(
        payload.ckpt_root_dir or os.getenv("ODESIGN_CKPT_ROOT"),
        DEFAULT_CKPT_ROOT,
    )
    data_root_dir = _resolve_runtime_dir(
        payload.data_root_dir or os.getenv("ODESIGN_DATA_ROOT"),
        DEFAULT_DATA_ROOT,
    )
    exp_name = _normalize_exp_name(payload.exp_name, payload.infer_model_name)
    _parse_seeds_json(payload.seeds_json)
    _require_runtime_assets(
        infer_model_name=payload.infer_model_name,
        design_modality=payload.design_modality,
        ckpt_root_dir=ckpt_root_dir,
        data_root_dir=data_root_dir,
    )

    before_dirs = _list_run_dirs(exp_name)
    env = os.environ.copy()
    env["DATA_ROOT_DIR"] = str(data_root_dir)
    env["CKPT_ROOT_DIR"] = str(ckpt_root_dir)
    cuda_visible_devices = (
        payload.cuda_visible_devices
        or env.get("ODESIGN_CUDA_VISIBLE_DEVICES")
        or env.get("CUDA_VISIBLE_DEVICES")
        or "0"
    )
    env["CUDA_VISIBLE_DEVICES"] = cuda_visible_devices

    command = [
        sys.executable,
        "./scripts/inference.py",
        f"exp=train_{payload.infer_model_name}",
        f"data_root_dir={data_root_dir}",
        f"ckpt_root_dir={ckpt_root_dir}",
        f"exp.infer_model_name={payload.infer_model_name}",
        f"exp.design_modality={payload.design_modality}",
        f"exp.input_json_path={input_json_path}",
        f"exp.exp_name={exp_name}",
        f"exp.seeds={payload.seeds_json}",
        f"exp.model.sample_diffusion.N_sample={payload.n_sample}",
        f"exp.use_msa={str(payload.use_msa).lower()}",
        f"exp.num_workers={payload.num_workers}",
        "exp.model.inference_noise_schedulers.coordinate.partial_diffusion.enable="
        + str(payload.enable_partial_diff).lower(),
        "exp.model.inference_noise_schedulers.coordinate.partial_diffusion.snr="
        + str(payload.snr),
        f"exp.invfold_topk={payload.invfold_topk}",
        f"exp.invfold_temp={payload.invfold_temp}",
        f"exp.invfold_use_beam={str(payload.invfold_use_beam).lower()}",
    ]

    result = subprocess.run(
        command,
        cwd=ODESIGN_ROOT,
        capture_output=True,
        text=True,
        timeout=payload.timeout_seconds,
        env=env,
    )

    output_dir: Optional[Path] = None
    try:
        output_dir = _locate_output_dir(exp_name, before_dirs)
    except HTTPException:
        if result.returncode == 0:
            raise

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "ODesign inference failed.",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command,
                "exp_name": exp_name,
                "output_dir": str(output_dir) if output_dir else "",
            },
        )

    if output_dir is None:
        output_dir = _locate_output_dir(exp_name, before_dirs)

    prediction_files = _collect_prediction_files(output_dir)
    error_files = _collect_error_files(output_dir)
    run_log_path = output_dir / "run.log"
    # ODesign output structure: <exp_name>/<timestamp>/<sample_name>/<seed>/predictions/*.cif
    sample_names = sorted({path.parent.parent.parent.name for path in prediction_files})

    return ODesignInferenceResponse(
        input_json_path=str(input_json_path),
        infer_model_name=payload.infer_model_name,
        design_modality=payload.design_modality,
        exp_name=exp_name,
        ckpt_root_dir=str(ckpt_root_dir),
        data_root_dir=str(data_root_dir),
        output_dir=str(output_dir),
        prediction_filepaths=[str(path) for path in prediction_files],
        sample_names=sample_names,
        run_log_path=str(run_log_path) if run_log_path.exists() else None,
        error_filepaths=[str(path) for path in error_files],
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
        timeout_seconds=payload.timeout_seconds,
    )
