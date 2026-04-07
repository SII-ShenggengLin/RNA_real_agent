"""RNARL microservice for protein-to-mRNA CDS generation."""

from __future__ import annotations

import os
import pickle
import re
import sys
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, EsmModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RNARL_ROOT = PROJECT_ROOT / "external_repos" / "RNARL"
RNARL_SCRIPTS_DIR = RNARL_ROOT / "scripts"
CHECKPOINTS_DIR = RNARL_ROOT / "checkpoints"
DEFAULT_ESM2_MODEL_DIR = RNARL_ROOT / "esm2_model_t33_650M_UR50D"

if str(RNARL_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(RNARL_SCRIPTS_DIR))

from utils import ActorModel_encoder_esm2, Tokenizer  # type: ignore  # noqa: E402

MODEL_TYPE_TO_CHECKPOINT = {
    "Homo sapiens mRNA": "homo_mrna.pt",
    "Homo sapiens circular RNA": "homo_circ.pt",
    "Arabidopsis thaliana mRNA": "Arabidopsis.pt",
    "Escherichia coli mRNA": "EscherichiaColi.pt",
    "Penicillium chrysogenum mRNA": "PC.pt",
    "Chlamydomonas reinhardtii mRNA": "CR.pt",
    "Thermococcus kodakarensis KOD1 mRNA": "TK.pt",
}
DEFAULT_MODEL_TYPE = "Homo sapiens mRNA"
MAX_PROTEIN_LENGTH = 1308
MODEL_CONFIG: Dict[str, Any] = {
    "d_model": 768,
    "nhead": 8,
    "num_encoder_layers": 8,
    "dim_feedforward": 1536,
    "dropout": 0.3,
    "num_experts": 6,
    "top_k_experts": 2,
    "esm2_dim": 1280,
}

app = FastAPI(
    title="RNARL Service",
    description="Run RNARL actor inference through a FastAPI microservice.",
    version="0.2.0",
)

_MODEL_CACHE: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
_CACHE_LOCK = Lock()


class CdsDesignRequest(BaseModel):
    protein_sequence: str = Field(
        ...,
        min_length=1,
        description="Protein sequence used by RNARL to generate an RNA CDS.",
    )
    model_type: str = Field(
        default=DEFAULT_MODEL_TYPE,
        description="RNARL model type from the author notebook, such as `Homo sapiens mRNA`.",
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional override for a specific RNARL checkpoint path.",
    )
    esm2_model_path: Optional[str] = Field(
        default=None,
        description="Optional override for a local ESM-2 model directory.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Torch device string such as `cuda:0` or `cpu`.",
    )


class CdsDesignResponse(BaseModel):
    protein_sequence: str
    generated_sequence: str
    model_type: str
    checkpoint_path: str
    esm2_model_path: str
    device: str
    model: str = "RNARL-actor"


def _normalize_protein_sequence(raw_text: str) -> str:
    sequence = re.sub(r"[^A-Za-z*]", "", raw_text).upper()
    if not sequence:
        raise HTTPException(status_code=400, detail="Protein sequence is empty after normalization.")
    valid_residues = set("ARNDCQEGHILKMFPSTWYV*")
    invalid_chars = sorted(set(ch for ch in sequence if ch not in valid_residues))
    if invalid_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Protein sequence contains unsupported residue(s): {''.join(invalid_chars)}",
        )
    if len(sequence) > MAX_PROTEIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Protein sequence length {len(sequence)} exceeds RNARL max supported length "
                f"{MAX_PROTEIN_LENGTH}."
            ),
        )
    return sequence


def _normalize_model_type(model_type: str) -> str:
    normalized = model_type.strip()
    if normalized in MODEL_TYPE_TO_CHECKPOINT:
        return normalized
    supported = ", ".join(MODEL_TYPE_TO_CHECKPOINT)
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported RNARL model_type `{model_type}`. Supported values: {supported}",
    )


def _resolve_device(device_override: Optional[str]) -> str:
    if device_override:
        return device_override
    env_device = os.environ.get("RNARL_DEVICE")
    if env_device:
        return env_device
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def _resolve_checkpoint_path(model_type: str, path_override: Optional[str]) -> Path:
    candidate = path_override or os.environ.get("RNARL_ACTOR_CHECKPOINT_PATH")
    if candidate:
        return Path(candidate).expanduser().resolve()
    return (CHECKPOINTS_DIR / MODEL_TYPE_TO_CHECKPOINT[model_type]).resolve()


def _resolve_esm2_path(path_override: Optional[str]) -> Path:
    candidate = path_override or os.environ.get("RNARL_ESM2_MODEL_PATH")
    if candidate:
        return Path(candidate).expanduser().resolve()
    return DEFAULT_ESM2_MODEL_DIR.resolve()


def _ensure_runtime_assets(checkpoint_path: Path, esm2_model_path: Path) -> None:
    required_paths = [
        RNARL_ROOT,
        RNARL_SCRIPTS_DIR,
        RNARL_SCRIPTS_DIR / "utils.py",
        RNARL_SCRIPTS_DIR / "transformer_encoder_MoE.py",
        checkpoint_path,
        esm2_model_path,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=(
                "RNARL runtime assets are missing. Expected repository clone, a model-specific checkpoint, "
                "and a local ESM-2 model directory. Missing: "
                f"{missing}"
            ),
        )


def _extract_state_dict(loaded_checkpoint: Any) -> Dict[str, torch.Tensor]:
    if isinstance(loaded_checkpoint, dict):
        if loaded_checkpoint and all(torch.is_tensor(value) for value in loaded_checkpoint.values()):
            return loaded_checkpoint
        for key in ("state_dict", "model_state_dict", "model"):
            nested = loaded_checkpoint.get(key)
            if isinstance(nested, dict) and nested and all(torch.is_tensor(value) for value in nested.values()):
                return nested
    raise HTTPException(
        status_code=500,
        detail=(
            "RNARL checkpoint loaded successfully but did not contain a recognizable state_dict. "
            "Expected either a raw state_dict or one nested under `state_dict` / `model_state_dict` / `model`."
        ),
    )


def _load_checkpoint_state_dict(checkpoint_path: Path) -> Dict[str, torch.Tensor]:
    try:
        loaded_checkpoint = torch.load(str(checkpoint_path), map_location="cpu", weights_only=True)
    except (pickle.UnpicklingError, RuntimeError, TypeError, ValueError):
        # The author-provided RNARL checkpoints can use an older pickle-based format.
        # These files are treated as trusted runtime assets supplied by the user.
        loaded_checkpoint = torch.load(str(checkpoint_path), map_location="cpu", weights_only=False)
    return _extract_state_dict(loaded_checkpoint)


def _load_runtime(checkpoint_path: Path, esm2_model_path: Path, device_name: str) -> Dict[str, Any]:
    cache_key = (str(checkpoint_path), str(esm2_model_path), device_name)
    cached = _MODEL_CACHE.get(cache_key)
    if cached is not None:
        return cached

    with _CACHE_LOCK:
        cached = _MODEL_CACHE.get(cache_key)
        if cached is not None:
            return cached

        _ensure_runtime_assets(checkpoint_path, esm2_model_path)
        device = torch.device(device_name)
        tokenizer = Tokenizer()
        actor_model = ActorModel_encoder_esm2(
            len(tokenizer.tokens),
            MODEL_CONFIG["d_model"],
            MODEL_CONFIG["nhead"],
            MODEL_CONFIG["num_encoder_layers"],
            MODEL_CONFIG["dim_feedforward"],
            MODEL_CONFIG["esm2_dim"],
            MODEL_CONFIG["dropout"],
            MODEL_CONFIG["num_experts"],
            MODEL_CONFIG["top_k_experts"],
            device,
        ).to(device)
        state_dict = _load_checkpoint_state_dict(checkpoint_path)
        actor_model.load_state_dict(state_dict, strict=True)
        actor_model.eval()

        esm2_tokenizer = AutoTokenizer.from_pretrained(str(esm2_model_path), local_files_only=True)
        esm2_model = EsmModel.from_pretrained(str(esm2_model_path), local_files_only=True).to(device)
        esm2_model.eval()
        for parameter in esm2_model.parameters():
            parameter.requires_grad = False

        runtime = {
            "tokenizer": tokenizer,
            "esm2_tokenizer": esm2_tokenizer,
            "esm2_model": esm2_model,
            "actor_model": actor_model,
            "device": device,
        }
        _MODEL_CACHE[cache_key] = runtime
        return runtime


def _decode_rna_sequence(logits: torch.Tensor, tokenizer: Tokenizer, protein_length: int) -> str:
    pred_tokens = logits.argmax(dim=-1).detach().cpu().numpy()
    return tokenizer.decode(pred_tokens[1 : protein_length + 1]).replace("T", "U")


@app.get("/health")
def health() -> dict[str, Any]:
    default_checkpoint = _resolve_checkpoint_path(DEFAULT_MODEL_TYPE, None)
    esm2_model_path = _resolve_esm2_path(None)
    return {
        "status": "ok",
        "repo_exists": RNARL_ROOT.exists(),
        "checkpoints_dir": str(CHECKPOINTS_DIR),
        "default_checkpoint_path": str(default_checkpoint),
        "default_checkpoint_exists": default_checkpoint.exists(),
        "esm2_model_path": str(esm2_model_path),
        "esm2_model_exists": esm2_model_path.exists(),
        "available_model_types": list(MODEL_TYPE_TO_CHECKPOINT.keys()),
        "ready": RNARL_ROOT.exists() and default_checkpoint.exists() and esm2_model_path.exists(),
    }


@app.get("/models")
def list_models() -> dict[str, Any]:
    return {
        "default_model_type": DEFAULT_MODEL_TYPE,
        "models": [
            {
                "model_type": model_type,
                "checkpoint_filename": checkpoint_filename,
                "default_checkpoint_path": str((CHECKPOINTS_DIR / checkpoint_filename).resolve()),
            }
            for model_type, checkpoint_filename in MODEL_TYPE_TO_CHECKPOINT.items()
        ],
    }


@app.post("/generate/cds", response_model=CdsDesignResponse)
def generate_cds(payload: CdsDesignRequest) -> CdsDesignResponse:
    protein_sequence = _normalize_protein_sequence(payload.protein_sequence)
    model_type = _normalize_model_type(payload.model_type)
    checkpoint_path = _resolve_checkpoint_path(model_type, payload.checkpoint_path)
    esm2_model_path = _resolve_esm2_path(payload.esm2_model_path)
    device_name = _resolve_device(payload.device)
    runtime = _load_runtime(checkpoint_path, esm2_model_path, device_name)

    tokenizer = runtime["tokenizer"]
    esm2_tokenizer = runtime["esm2_tokenizer"]
    esm2_model = runtime["esm2_model"]
    actor_model = runtime["actor_model"]
    device = runtime["device"]

    with torch.no_grad():
        encoded_protein = [tokenizer.encode_pro(protein_sequence, 1310)]
        src = torch.tensor(encoded_protein, dtype=torch.long, device=device)
        esm_inputs = esm2_tokenizer(
            [protein_sequence],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1310,
        ).to(device)
        esm_embeddings = esm2_model(**esm_inputs).last_hidden_state
        outputs, _, _ = actor_model(src, esm_embeddings)
        generated_sequence = _decode_rna_sequence(outputs[0], tokenizer, len(protein_sequence))

    return CdsDesignResponse(
        protein_sequence=protein_sequence,
        generated_sequence=generated_sequence,
        model_type=model_type,
        checkpoint_path=str(checkpoint_path),
        esm2_model_path=str(esm2_model_path),
        device=str(device),
    )
