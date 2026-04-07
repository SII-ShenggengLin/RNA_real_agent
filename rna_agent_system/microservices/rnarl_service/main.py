"""RNARL microservice for protein-to-mRNA CDS generation."""

from __future__ import annotations

import os
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

if str(RNARL_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(RNARL_SCRIPTS_DIR))

from utils import ActorModel_encoder_esm2, BiologicalMappings, Tokenizer  # type: ignore  # noqa: E402

DEFAULT_ACTOR_CHECKPOINT = RNARL_ROOT / "actor.pt"
DEFAULT_ESM2_MODEL_DIR = RNARL_ROOT / "esm2_model_t33_650M_UR50D"
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
    version="0.1.0",
)

_MODEL_CACHE: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
_CACHE_LOCK = Lock()


class CdsDesignRequest(BaseModel):
    protein_sequence: str = Field(
        ...,
        min_length=1,
        description="Protein sequence used by RNARL to generate an RNA CDS.",
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional override for RNARL actor checkpoint path.",
    )
    esm2_model_path: Optional[str] = Field(
        default=None,
        description="Optional override for local ESM-2 model directory.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Torch device string such as `cuda:0` or `cpu`.",
    )


class CdsDesignResponse(BaseModel):
    protein_sequence: str
    generated_sequence: str
    checkpoint_path: str
    esm2_model_path: str
    device: str
    model: str = "RNARL-actor"


def _normalize_protein_sequence(raw_text: str) -> str:
    sequence = re.sub(r"[^A-Za-z*]", "", raw_text).upper()
    if not sequence:
        raise HTTPException(status_code=400, detail="Protein sequence is empty after normalization.")
    if "*" in sequence:
        raise HTTPException(
            status_code=400,
            detail="RNARL service currently expects a protein sequence without `*` stop symbols.",
        )
    invalid_chars = sorted(set(ch for ch in sequence if ch not in set("ARNDCQEGHILKMFPSTWYV")))
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


def _resolve_device(device_override: Optional[str]) -> str:
    if device_override:
        return device_override
    env_device = os.environ.get("RNARL_DEVICE")
    if env_device:
        return env_device
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def _resolve_checkpoint_path(path_override: Optional[str]) -> Path:
    candidate = path_override or os.environ.get("RNARL_ACTOR_CHECKPOINT_PATH") or str(DEFAULT_ACTOR_CHECKPOINT)
    return Path(candidate).expanduser().resolve()


def _resolve_esm2_path(path_override: Optional[str]) -> Path:
    candidate = path_override or os.environ.get("RNARL_ESM2_MODEL_PATH") or str(DEFAULT_ESM2_MODEL_DIR)
    return Path(candidate).expanduser().resolve()


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
                "RNARL runtime assets are missing. "
                "Expected repository clone, actor checkpoint, and local ESM-2 model directory. "
                f"Missing: {missing}"
            ),
        )


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
            vocab_size=len(tokenizer.tokens),
            device=device,
            **MODEL_CONFIG,
        ).to(device)
        state_dict = torch.load(str(checkpoint_path), map_location=device)
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


def _decode_logits_to_sequence(
    logits: torch.Tensor,
    tokenizer: Tokenizer,
    protein_sequence: str,
) -> str:
    amino_acid_to_codon = BiologicalMappings.get_amino_acid_to_codon()
    predicted_ids = torch.argmax(logits, dim=-1).tolist()
    codons = []
    for position, amino_acid in enumerate(protein_sequence, start=1):
        token_id = predicted_ids[position]
        token = tokenizer.id_to_token.get(token_id, "")
        if len(token) != 3:
            token = amino_acid_to_codon[amino_acid][0]
        codons.append(token.replace("T", "U"))
    return "".join(codons)


@app.get("/health")
def health() -> dict[str, Any]:
    checkpoint_path = _resolve_checkpoint_path(None)
    esm2_model_path = _resolve_esm2_path(None)
    return {
        "status": "ok",
        "repo_exists": RNARL_ROOT.exists(),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_exists": checkpoint_path.exists(),
        "esm2_model_path": str(esm2_model_path),
        "esm2_model_exists": esm2_model_path.exists(),
        "ready": RNARL_ROOT.exists() and checkpoint_path.exists() and esm2_model_path.exists(),
        "note": (
            "RNARL upstream repo is training-oriented. "
            "This service provides a project-local inference wrapper around the actor model."
        ),
    }


@app.post("/generate/cds", response_model=CdsDesignResponse)
def generate_cds(payload: CdsDesignRequest) -> CdsDesignResponse:
    protein_sequence = _normalize_protein_sequence(payload.protein_sequence)
    checkpoint_path = _resolve_checkpoint_path(payload.checkpoint_path)
    esm2_model_path = _resolve_esm2_path(payload.esm2_model_path)
    device_name = _resolve_device(payload.device)
    runtime = _load_runtime(checkpoint_path, esm2_model_path, device_name)

    tokenizer = runtime["tokenizer"]
    esm2_tokenizer = runtime["esm2_tokenizer"]
    esm2_model = runtime["esm2_model"]
    actor_model = runtime["actor_model"]
    device = runtime["device"]

    with torch.no_grad():
        encoded_protein = torch.tensor(
            [tokenizer.encode_pro(protein_sequence, len(protein_sequence) + 2)],
            dtype=torch.long,
            device=device,
        )
        esm_inputs = esm2_tokenizer(
            [protein_sequence],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=len(protein_sequence) + 2,
        ).to(device)
        esm_embeddings = esm2_model(**esm_inputs).last_hidden_state
        logits, _, _ = actor_model(encoded_protein, esm_embeddings)
        generated_sequence = _decode_logits_to_sequence(logits[0], tokenizer, protein_sequence)

    return CdsDesignResponse(
        protein_sequence=protein_sequence,
        generated_sequence=generated_sequence,
        checkpoint_path=str(checkpoint_path),
        esm2_model_path=str(esm2_model_path),
        device=str(device),
    )
