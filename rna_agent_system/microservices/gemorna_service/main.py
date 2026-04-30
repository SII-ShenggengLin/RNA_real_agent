"""GEMORNA microservice for mRNA CDS / 5'UTR / 3'UTR design."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GEMORNA_ROOT = PROJECT_ROOT / "external_repos" / "GEMORNA"
CHECKPOINT_DIR = GEMORNA_ROOT / "checkpoints"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common_utils import _is_lfs_pointer  # noqa: E402

app = FastAPI(
    title="GEMORNA Service",
    description="Run GEMORNA generation scripts (CDS / 5UTR / 3UTR) through a FastAPI microservice.",
    version="0.2.0",
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CdsDesignRequest(BaseModel):
    """GEMORNA CDS generation request.

    INTERFACE LOCK (v0.2.0): Locked schema. Field changes must stay synchronized with:
    - agent_core/tools.py :: GemornaCdsInput + design_mrna_cds_with_gemorna wrapper
    - agent_core/tool_specs.py :: GemornaCdsOutput
    """

    protein_sequence: str = Field(
        ...,
        min_length=1,
        description="Protein sequence used by GEMORNA to generate CDS candidates.",
    )

    @field_validator("protein_sequence")
    @classmethod
    def _min_aa_length(cls, v: str) -> str:
        stripped = v.strip()
        canonical_aa = set("ACDEFGHIKLMNPQRSTVWY*")
        aa_only = "".join(ch for ch in stripped.upper() if ch in canonical_aa)
        if len(aa_only) < 10:
            raise ValueError(
                f"Protein sequence must contain at least 10 canonical amino acids "
                f"(ensuring CDS ≥ 30 nt for reliable extraction). Got {len(aa_only)}."
            )
        return stripped


class CdsDesignResponse(BaseModel):
    """GEMORNA CDS generation response.

    INTERFACE LOCK (v0.2.0): Locked schema. Field changes must stay synchronized with:
    - agent_core/tool_specs.py :: GemornaCdsOutput
    - agent_core/tools.py :: design_mrna_cds_with_gemorna wrapper return dict
    """

    protein_sequence: str
    generated_sequence: str
    raw_output: str
    model: str = "GEMORNA-cds"


class UtrDesignRequest(BaseModel):
    """GEMORNA UTR generation request (5'UTR / 3'UTR).

    INTERFACE LOCK (v0.2.0): Locked schema. Field changes must stay synchronized with:
    - agent_core/tools.py :: Gemorna5UtrInput / Gemorna3UtrInput + design_5utr_with_gemorna / design_3utr_with_gemorna wrappers
    - agent_core/tool_specs.py :: Gemorna5UtrOutput / Gemorna3UtrOutput
    """

    utr_length: str = Field(
        ...,
        description="UTR length category: short | medium | long.",
    )

    @field_validator("utr_length")
    @classmethod
    def _validate_utr_length(cls, v: str) -> str:
        allowed = {"short", "medium", "long"}
        lowered = v.strip().lower()
        if lowered not in allowed:
            raise ValueError(f"utr_length must be one of {allowed}, got '{v}'.")
        return lowered


class UtrDesignResponse(BaseModel):
    """GEMORNA UTR generation response (5'UTR / 3'UTR).

    INTERFACE LOCK (v0.2.0): Locked schema. Field changes must stay synchronized with:
    - agent_core/tool_specs.py :: Gemorna5UtrOutput / Gemorna3UtrOutput
    - agent_core/tools.py :: design_5utr_with_gemorna / design_3utr_with_gemorna wrapper return dicts
    """

    mode: str
    utr_length: str
    generated_sequence: str
    raw_output: str
    model: str


class UtrPredictionRequest(BaseModel):
    """GEMORNA UTR prediction request (5'UTR MRL / 3'UTR stability).

    INTERFACE LOCK (v0.1.0): Locked schema. Field changes must stay synchronized with:
    - agent_core/tools.py :: Gemorna5UtrPredictionInput / Gemorna3UtrPredictionInput
    - agent_core/tool_specs.py :: predict_5utr_mrl_with_gemorna / predict_3utr_stability_with_gemorna ToolSpec
    """

    sequence: str = Field(
        ...,
        min_length=10,
        description="RNA sequence to evaluate. Must contain only A/C/G/U (T is auto-converted to U).",
    )

    @field_validator("sequence")
    @classmethod
    def _validate_rna_sequence(cls, v: str) -> str:
        cleaned = v.strip().upper().replace("T", "U")
        valid = set("ACGU")
        invalid = [ch for ch in cleaned if ch not in valid]
        if invalid:
            raise ValueError(f"Sequence contains invalid characters: {invalid}. Only A/C/G/U/T allowed.")
        if len(cleaned) < 10:
            raise ValueError(f"Sequence must be at least 10 nt; got {len(cleaned)}.")
        return cleaned


class Utr5MrlPredictionResponse(BaseModel):
    """GEMORNA 5'UTR MRL prediction response.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must stay synchronized with:
    - agent_core/tool_specs.py :: Gemorna5UtrMrlPredictionOutput
    - agent_core/tools.py :: predict_5utr_mrl_with_gemorna wrapper return dict
    """

    input_sequence: str
    predicted_mrl: float
    model: str = "GEMORNA-5utr-mrl"


class Utr3StabilityPredictionResponse(BaseModel):
    """GEMORNA 3'UTR stability prediction response.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must stay synchronized with:
    - agent_core/tool_specs.py :: Gemorna3UtrStabilityPredictionOutput
    - agent_core/tools.py :: predict_3utr_stability_with_gemorna wrapper return dict
    """

    input_sequence: str
    predicted_stability: float
    model: str = "GEMORNA-3utr-stability"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_runtime_assets(mode: str) -> None:
    """Verify that required assets exist for the requested generation/prediction mode."""
    required_paths: list[Path] = []

    if mode == "cds":
        required_paths += [
            GEMORNA_ROOT / "src" / "generate.py",
            GEMORNA_ROOT / "vocab" / "prot_vocab.pkl",
            GEMORNA_ROOT / "vocab" / "cds_vocab.pkl",
            CHECKPOINT_DIR / "gemorna_cds.pt",
        ]
    elif mode == "5utr":
        required_paths += [
            GEMORNA_ROOT / "src" / "generate.py",
            CHECKPOINT_DIR / "gemorna_5utr.pt",
        ]
    elif mode == "3utr":
        required_paths += [
            GEMORNA_ROOT / "src" / "generate.py",
            CHECKPOINT_DIR / "gemorna_3utr.pt",
        ]
    elif mode == "pred_5utr":
        required_paths += [
            GEMORNA_ROOT / "src" / "main_pred5UTR.py",
            CHECKPOINT_DIR / "5utr.pt",
        ]
    elif mode == "pred_3utr":
        required_paths += [
            GEMORNA_ROOT / "src" / "main_pred3UTR.py",
            CHECKPOINT_DIR / "3utr.pt",
        ]
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported GEMORNA mode: {mode}")

    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise HTTPException(status_code=500, detail=f"Missing GEMORNA assets: {missing}")

    for pt in required_paths:
        if pt.suffix == ".pt" and _is_lfs_pointer(pt):
            raise HTTPException(
                status_code=503,
                detail=(
                    f"GEMORNA checkpoint {pt.name} is still a Git LFS pointer. "
                    "Run `git lfs pull` or manually copy real `.pt` files into "
                    "`external_repos/GEMORNA/checkpoints/`."
                ),
            )


def _extract_generated_sequence(stdout: str, min_length: int = 30) -> str:
    """Extract the longest contiguous nucleotide stretch from stdout.

    Args:
        stdout: Raw stdout from GEMORNA generate.py.
        min_length: Minimum number of contiguous nucleotide characters required.
                    Defaults to 30 (safe for CDS). UTR calls may pass 10.
    """
    pattern = rf"[ACGTUNacgtun]{{{min_length},}}"
    matches = re.findall(pattern, stdout)
    if matches:
        return max(matches, key=len).upper().replace("T", "U")

    # Fallback: try a shorter stretch before giving up
    fallback = re.findall(r"[ACGTUNacgtun]{10,}", stdout)
    if fallback:
        return max(fallback, key=len).upper().replace("T", "U")

    raise HTTPException(
        status_code=500,
        detail=f"Unable to parse GEMORNA output sequence from stdout: {stdout}",
    )


def _run_gemorna_utr(mode: str, utr_length: str) -> UtrDesignResponse:
    """Run GEMORNA UTR generation for 5utr or 3utr and return a response."""
    _require_runtime_assets(mode)
    ckpt = f"checkpoints/gemorna_{mode}.pt"
    command = [
        sys.executable,
        "src/generate.py",
        "--mode",
        mode,
        "--ckpt_path",
        ckpt,
        "--utr_length",
        utr_length,
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
                "message": f"GEMORNA {mode.upper()} generation failed.",
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
    generated_sequence = _extract_generated_sequence(result.stdout, min_length=10)
    return UtrDesignResponse(
        mode=mode,
        utr_length=utr_length,
        generated_sequence=generated_sequence,
        raw_output=result.stdout.strip(),
        model=f"GEMORNA-{mode}",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate/cds", response_model=CdsDesignResponse)
def generate_cds(payload: CdsDesignRequest) -> CdsDesignResponse:
    """GEMORNA CDS generation endpoint.

    INTERFACE LOCK (v0.2.0): The CLI invocation (--mode cds --protein_seq ...) and
    response schema are canonical. Do not change without updating wrapper + tool spec.
    """
    _require_runtime_assets("cds")
    command = [
        sys.executable,
        "src/generate.py",
        "--mode",
        "cds",
        "--ckpt_path",
        "checkpoints/gemorna_cds.pt",
        "--protein_seq",
        payload.protein_sequence,
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
    generated_sequence = _extract_generated_sequence(result.stdout, min_length=30)
    return CdsDesignResponse(
        protein_sequence=payload.protein_sequence,
        generated_sequence=generated_sequence,
        raw_output=result.stdout.strip(),
    )


@app.post("/generate/5utr", response_model=UtrDesignResponse)
def generate_5utr(payload: UtrDesignRequest) -> UtrDesignResponse:
    """GEMORNA 5'UTR generation endpoint.

    INTERFACE LOCK (v0.2.0): The CLI invocation (--mode 5utr --utr_length ...) and
    response schema are canonical. Do not change without updating wrapper + tool spec.
    """
    return _run_gemorna_utr("5utr", payload.utr_length)


@app.post("/generate/3utr", response_model=UtrDesignResponse)
def generate_3utr(payload: UtrDesignRequest) -> UtrDesignResponse:
    """GEMORNA 3'UTR generation endpoint.

    INTERFACE LOCK (v0.2.0): The CLI invocation (--mode 3utr --utr_length ...) and
    response schema are canonical. Do not change without updating wrapper + tool spec.
    """
    return _run_gemorna_utr("3utr", payload.utr_length)



def _extract_prediction_value(stdout: str) -> float:
    """Extract the numeric prediction from GEMORNA prediction stdout.

    Expected format: '{sequence} {value:.2f}'
    """
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in lines:
        # Try to find a floating point number at the end of the line
        parts = line.split()
        if parts:
            try:
                return float(parts[-1])
            except ValueError:
                continue
    raise HTTPException(
        status_code=500,
        detail=f"Unable to parse prediction value from stdout: {stdout}",
    )


def _run_gemorna_prediction(mode: str, sequence: str) -> float:
    """Run GEMORNA prediction for 5'UTR MRL or 3'UTR stability."""
    _require_runtime_assets(f"pred_{mode}")
    if mode == "5utr":
        script = "src/main_pred5UTR.py"
        ckpt = "checkpoints/5utr.pt"
    elif mode == "3utr":
        script = "src/main_pred3UTR.py"
        ckpt = "checkpoints/3utr.pt"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported prediction mode: {mode}")

    command = [
        sys.executable,
        script,
        "--sequence",
        sequence,
        "--ckpt_path",
        ckpt,
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
                "message": f"GEMORNA {mode.upper()} prediction failed.",
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
    return _extract_prediction_value(result.stdout)


@app.post("/predict/5utr_mrl", response_model=Utr5MrlPredictionResponse)
def predict_5utr_mrl(payload: UtrPredictionRequest) -> Utr5MrlPredictionResponse:
    """GEMORNA 5'UTR MRL prediction endpoint.

    INTERFACE LOCK (v0.1.0): The CLI invocation (--sequence ...) and
    response schema are canonical. Do not change without updating wrapper + tool spec.
    """
    predicted_mrl = _run_gemorna_prediction("5utr", payload.sequence)
    return Utr5MrlPredictionResponse(
        input_sequence=payload.sequence,
        predicted_mrl=predicted_mrl,
    )


@app.post("/predict/3utr_stability", response_model=Utr3StabilityPredictionResponse)
def predict_3utr_stability(payload: UtrPredictionRequest) -> Utr3StabilityPredictionResponse:
    """GEMORNA 3'UTR stability prediction endpoint.

    INTERFACE LOCK (v0.1.0): The CLI invocation (--sequence ...) and
    response schema are canonical. Do not change without updating wrapper + tool spec.
    """
    predicted_stability = _run_gemorna_prediction("3utr", payload.sequence)
    return Utr3StabilityPredictionResponse(
        input_sequence=payload.sequence,
        predicted_stability=predicted_stability,
    )
