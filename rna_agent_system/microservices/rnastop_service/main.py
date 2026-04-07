"""RNASTOP microservice for mRNA stability prediction."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import RNA
import fm
import numpy as np
import torch
import torch.nn as nn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModel, AutoTokenizer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RNASTOP_ROOT = PROJECT_ROOT / "external_repos" / "RNASTOP"
RNASTOP_MODELS_DIR = RNASTOP_ROOT / "models"
RNASTOP_DNABERT_DIR = RNASTOP_ROOT / "DNABERT6"
RNASTOP_SCRIPTS_DNABERT_DIR = RNASTOP_ROOT / "scripts" / "DNABERT6"
RNASTOP_RNAFM_PRETRAINED_DIR = RNASTOP_ROOT / "RNA-FM-main" / "pretrained"
RNASTOP_SCRIPTS_RNAFM_PRETRAINED_DIR = RNASTOP_ROOT / "scripts" / "RNA-FM-main" / "pretrained"
RNASTOP_RNAFM_FILENAME = "RNA-FM_pretrained.pth"

MAX_SEQUENCE_LENGTH = 1022
DEFAULT_MODEL_NAME = "RNASTOP"
DEFAULT_CHECKPOINT_NAME = "best_model_weights"
DEFAULT_DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

TOKENS = "ACGU().BEHIMSXDF"
VOCAB_SIZE = len(TOKENS)

CONV_KERNEL = 7
DROPOUT = 0.3
EMBEDDING_DIM = 128
NHEAD = 4
NUM_ENCODER_LAYERS = 4
N_STR_DIM = 8
PREDICTION_COLUMNS = ("reactivity", "deg_Mg_pH10", "deg_Mg_50C")

app = FastAPI(
    title="RNASTOP Service",
    description="Predict mRNA degradation and stability-related summary scores with RNASTOP.",
    version="0.1.0",
)

_RUNTIME_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}
_CACHE_LOCK = Lock()


class StabilityPredictionRequest(BaseModel):
    sequence: str = Field(
        ...,
        min_length=1,
        description="RNA sequence to evaluate. FASTA-like text is accepted.",
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional override for the RNASTOP checkpoint path.",
    )
    rnafm_model_path: Optional[str] = Field(
        default=None,
        description="Optional override for the local RNA-FM checkpoint `.pth` file.",
    )
    dnabert_model_path: Optional[str] = Field(
        default=None,
        description="Optional override for the local DNABERT model directory.",
    )
    structure: Optional[str] = Field(
        default=None,
        description="Optional dot-bracket structure. If omitted, ViennaRNA MFE structure is used.",
    )
    loop_type: Optional[str] = Field(
        default=None,
        description="Optional loop annotation string. If omitted, it is derived from the structure.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device string such as `cuda:0` or `cpu`.",
    )


class StabilityPredictionResponse(BaseModel):
    sequence: str
    used_sequence: str
    sequence_length: int
    used_length: int
    truncated: bool
    structure: str
    loop_type: str
    mfe: float
    mean_reactivity: float
    mean_deg_Mg_pH10: float
    mean_deg_Mg_50C: float
    per_position_predictions: Dict[str, List[float]]
    checkpoint_path: str
    rnafm_model_path: str
    dnabert_model_path: str
    use_dnabert: bool
    device: str
    model: str = DEFAULT_MODEL_NAME


class RNASTOPModel(nn.Module):
    """Inference-only RNASTOP architecture aligned to the full-length prediction script."""

    def __init__(self) -> None:
        super().__init__()
        self.embeddingSeq_fm = nn.Sequential(
            nn.Linear(640, 320),
            nn.LayerNorm(320),
            nn.ReLU(),
            nn.Dropout(DROPOUT),
            nn.Linear(320, EMBEDDING_DIM),
        )
        # Keep this layer for checkpoint compatibility even though the service does not use DNABERT.
        self.embeddingSeq_dnapt2 = nn.Sequential(
            nn.Linear(768, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(DROPOUT),
            nn.Linear(256, EMBEDDING_DIM),
        )
        self.embeddingloop = nn.Embedding(VOCAB_SIZE, EMBEDDING_DIM)

        self.embeddingstr = nn.Sequential(
            nn.Conv2d(N_STR_DIM, EMBEDDING_DIM, 1),
            nn.BatchNorm2d(EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
            nn.AdaptiveAvgPool2d((None, 1)),
        )

        encoder_layer_share = nn.TransformerEncoderLayer(
            d_model=EMBEDDING_DIM,
            nhead=NHEAD,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.transformer_encoder_share = nn.TransformerEncoder(
            encoder_layer_share,
            num_layers=NUM_ENCODER_LAYERS,
        )

        encoder_layer_seq_fm = nn.TransformerEncoderLayer(
            d_model=EMBEDDING_DIM,
            nhead=NHEAD,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.transformer_encoder_seq_fm = nn.TransformerEncoder(
            encoder_layer_seq_fm,
            num_layers=NUM_ENCODER_LAYERS,
        )
        self.conv_encoder_seq_fm = nn.Sequential(
            nn.Conv1d(EMBEDDING_DIM, EMBEDDING_DIM, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
            nn.ConvTranspose1d(EMBEDDING_DIM, EMBEDDING_DIM, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
        )
        encoder_layer_seq_dnapt2 = nn.TransformerEncoderLayer(
            d_model=EMBEDDING_DIM,
            nhead=NHEAD,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.transformer_encoder_seq_dnapt2 = nn.TransformerEncoder(
            encoder_layer_seq_dnapt2,
            num_layers=NUM_ENCODER_LAYERS,
        )
        self.conv_encoder_seq_dnapt2 = nn.Sequential(
            nn.Conv1d(EMBEDDING_DIM, EMBEDDING_DIM, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
            nn.ConvTranspose1d(EMBEDDING_DIM, EMBEDDING_DIM, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
        )

        encoder_layer_loop = nn.TransformerEncoderLayer(
            d_model=EMBEDDING_DIM,
            nhead=NHEAD,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.transformer_encoder_loop = nn.TransformerEncoder(
            encoder_layer_loop,
            num_layers=NUM_ENCODER_LAYERS,
        )
        self.conv_encoder_loop = nn.Sequential(
            nn.Conv1d(EMBEDDING_DIM, EMBEDDING_DIM, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
            nn.ConvTranspose1d(EMBEDDING_DIM, EMBEDDING_DIM, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
        )

        encoder_layer_str = nn.TransformerEncoderLayer(
            d_model=EMBEDDING_DIM,
            nhead=NHEAD,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.transformer_encoder_str = nn.TransformerEncoder(
            encoder_layer_str,
            num_layers=NUM_ENCODER_LAYERS,
        )
        self.conv_encoder_str = nn.Sequential(
            nn.Conv1d(EMBEDDING_DIM, EMBEDDING_DIM, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
            nn.ConvTranspose1d(EMBEDDING_DIM, EMBEDDING_DIM, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
        )

        encoder_layer_fustrans = nn.TransformerEncoderLayer(
            d_model=EMBEDDING_DIM,
            nhead=NHEAD,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.transformer_encoder_fustrans = nn.TransformerEncoder(
            encoder_layer_fustrans,
            num_layers=NUM_ENCODER_LAYERS,
        )
        self.conv_encoder_fusconv = nn.Sequential(
            nn.Conv1d(EMBEDDING_DIM, EMBEDDING_DIM * 2, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM * 2),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
            nn.ConvTranspose1d(EMBEDDING_DIM * 2, EMBEDDING_DIM, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
        )
        self.conv_encoder_finfus = nn.Sequential(
            nn.Conv1d(EMBEDDING_DIM * 2, EMBEDDING_DIM * 4, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM * 4),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
            nn.ConvTranspose1d(EMBEDDING_DIM * 4, EMBEDDING_DIM * 2, CONV_KERNEL),
            nn.BatchNorm1d(num_features=EMBEDDING_DIM * 2),
            nn.ReLU(inplace=True),
            nn.Dropout(DROPOUT),
        )
        self.pre = nn.Sequential(
            nn.Linear(EMBEDDING_DIM * 2, EMBEDDING_DIM),
            nn.LayerNorm(EMBEDDING_DIM),
            nn.ReLU(),
            nn.Dropout(DROPOUT),
            nn.Linear(EMBEDDING_DIM, 5),
        )

    def forward(
        self,
        loop: torch.Tensor,
        features: torch.Tensor,
        fm_seq: torch.Tensor,
        dnapt2_seq: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        embedded_seq_fm = self.embeddingSeq_fm(fm_seq)
        embedded_loop = self.embeddingloop(loop)

        embedded_features = self.embeddingstr(features.permute(0, 3, 1, 2))
        embedded_features = embedded_features.squeeze(-1).transpose(1, 2)

        embedded_seq_fm_share = self.transformer_encoder_share(embedded_seq_fm)
        embedded_seq_fm_1 = self.transformer_encoder_seq_fm(embedded_seq_fm_share)
        embedded_seq_fm_2 = self.conv_encoder_seq_fm(embedded_seq_fm_share.transpose(1, 2)).transpose(1, 2)
        embedded_seq_dnapt2_1 = None
        embedded_seq_dnapt2_2 = None
        if dnapt2_seq is not None:
            embedded_seq_dnapt2 = self.embeddingSeq_dnapt2(dnapt2_seq)
            embedded_seq_dnapt2_share = self.transformer_encoder_share(embedded_seq_dnapt2)
            embedded_seq_dnapt2_1 = self.transformer_encoder_seq_dnapt2(embedded_seq_dnapt2_share)
            embedded_seq_dnapt2_2 = self.conv_encoder_seq_dnapt2(
                embedded_seq_dnapt2_share.transpose(1, 2)
            ).transpose(1, 2)

        embedded_loop = self.transformer_encoder_share(embedded_loop)
        embedded_loop_1 = self.transformer_encoder_loop(embedded_loop)
        embedded_loop_2 = self.conv_encoder_loop(embedded_loop.transpose(1, 2)).transpose(1, 2)

        embedded_features = self.transformer_encoder_share(embedded_features)
        embedded_str_1 = self.transformer_encoder_str(embedded_features)
        embedded_str_2 = self.conv_encoder_str(embedded_features.transpose(1, 2)).transpose(1, 2)

        embedded_fus_trans = embedded_seq_fm_1 + embedded_loop_1 + embedded_str_1
        embedded_fus_conv = embedded_seq_fm_2 + embedded_loop_2 + embedded_str_2
        if embedded_seq_dnapt2_1 is not None and embedded_seq_dnapt2_2 is not None:
            embedded_fus_trans = embedded_fus_trans + embedded_seq_dnapt2_1
            embedded_fus_conv = embedded_fus_conv + embedded_seq_dnapt2_2

        embedded_fus_trans = self.transformer_encoder_fustrans(embedded_fus_trans)
        embedded_fus_conv = self.conv_encoder_fusconv(embedded_fus_conv.transpose(1, 2)).transpose(1, 2)

        embedded_cat = torch.cat((embedded_fus_trans, embedded_fus_conv), dim=2)
        embedded_cat = self.conv_encoder_finfus(embedded_cat.transpose(1, 2)).transpose(1, 2)
        return self.pre(embedded_cat)


def _normalize_rna_sequence(raw_text: str) -> str:
    sequence_lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    merged = "".join(sequence_lines).upper().replace("T", "U")
    sequence = re.sub(r"[^A-Z]", "", merged)
    if not sequence:
        raise HTTPException(status_code=400, detail="RNA sequence is empty after normalization.")
    invalid_chars = sorted(set(ch for ch in sequence if ch not in {"A", "U", "G", "C"}))
    if invalid_chars:
        raise HTTPException(
            status_code=400,
            detail=f"RNASTOP supports only A/U/G/C input. Unsupported characters: {''.join(invalid_chars)}",
        )
    return sequence


def _resolve_device(device_override: Optional[str]) -> str:
    if device_override:
        return device_override
    env_device = os.environ.get("RNASTOP_DEVICE")
    if env_device:
        return env_device
    return DEFAULT_DEVICE


def _checkpoint_candidates() -> List[Path]:
    candidates: List[Path] = []
    env_override = os.environ.get("RNASTOP_CHECKPOINT_PATH")
    if env_override:
        candidates.append(Path(env_override).expanduser().resolve())
    candidates.extend(
        [
            (RNASTOP_MODELS_DIR / DEFAULT_CHECKPOINT_NAME).resolve(),
            (RNASTOP_MODELS_DIR / "best_model_weights_withoutDNABERT").resolve(),
            (RNASTOP_ROOT / "scripts" / DEFAULT_CHECKPOINT_NAME).resolve(),
            (RNASTOP_ROOT / "scripts" / "best_model_weights_withoutDNABERT").resolve(),
        ]
    )
    return candidates


def _resolve_checkpoint_path(path_override: Optional[str]) -> Path:
    if path_override:
        return Path(path_override).expanduser().resolve()
    for candidate in _checkpoint_candidates():
        if candidate.exists():
            return candidate
    return _checkpoint_candidates()[0]


def _rnafm_candidates() -> List[Path]:
    candidates: List[Path] = []
    env_override = os.environ.get("RNASTOP_RNAFM_PATH")
    if env_override:
        candidates.append(Path(env_override).expanduser().resolve())
    candidates.extend(
        [
            (RNASTOP_RNAFM_PRETRAINED_DIR / RNASTOP_RNAFM_FILENAME).resolve(),
            (RNASTOP_SCRIPTS_RNAFM_PRETRAINED_DIR / RNASTOP_RNAFM_FILENAME).resolve(),
            (RNASTOP_ROOT / "pretrained" / RNASTOP_RNAFM_FILENAME).resolve(),
            (RNASTOP_ROOT / RNASTOP_RNAFM_FILENAME).resolve(),
        ]
    )
    return candidates


def _resolve_rnafm_path(path_override: Optional[str]) -> Path:
    if path_override:
        return Path(path_override).expanduser().resolve()
    for candidate in _rnafm_candidates():
        if candidate.exists():
            return candidate
    return _rnafm_candidates()[0]


def _dnabert_candidates() -> List[Path]:
    candidates: List[Path] = []
    env_override = os.environ.get("RNASTOP_DNABERT_PATH")
    if env_override:
        candidates.append(Path(env_override).expanduser().resolve())
    candidates.extend(
        [
            RNASTOP_DNABERT_DIR.resolve(),
            RNASTOP_SCRIPTS_DNABERT_DIR.resolve(),
        ]
    )
    return candidates


def _resolve_dnabert_path(path_override: Optional[str]) -> Path:
    if path_override:
        return Path(path_override).expanduser().resolve()
    for candidate in _dnabert_candidates():
        if candidate.exists():
            return candidate
    return _dnabert_candidates()[0]


def _checkpoint_uses_dnabert(checkpoint_path: Path) -> bool:
    checkpoint_name = checkpoint_path.name.lower()
    if "withoutstrloopdnabert" in checkpoint_name:
        raise HTTPException(
            status_code=400,
            detail=(
                "The `best_model_weights_withoutstrloopdnabert` checkpoint is not supported by "
                "this stability-prediction endpoint because it corresponds to a different inference path."
            ),
        )
    return "withoutdnabert" not in checkpoint_name


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
            "RNASTOP checkpoint loaded successfully but did not contain a recognizable state_dict. "
            "Expected either a raw state_dict or one nested under `state_dict` / `model_state_dict` / `model`."
        ),
    )


def _load_checkpoint_state_dict(checkpoint_path: Path) -> Dict[str, torch.Tensor]:
    try:
        loaded_checkpoint = torch.load(str(checkpoint_path), map_location="cpu", weights_only=True)
    except (RuntimeError, TypeError, ValueError):
        loaded_checkpoint = torch.load(str(checkpoint_path), map_location="cpu", weights_only=False)
    return _extract_state_dict(loaded_checkpoint)


def _ensure_runtime_assets(
    checkpoint_path: Path,
    rnafm_model_path: Path,
    use_dnabert: bool,
    dnabert_model_path: Path,
) -> None:
    required_paths = [RNASTOP_ROOT, checkpoint_path, rnafm_model_path]
    if use_dnabert:
        required_paths.append(dnabert_model_path)
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=(
                "RNASTOP runtime assets are missing. Expected the upstream repository clone and a "
                "downloaded checkpoint such as `best_model_weights` or `best_model_weights_withoutDNABERT`. "
                "Missing: "
                f"{missing}"
            ),
        )


def _load_runtime(
    checkpoint_path: Path,
    rnafm_model_path: Path,
    dnabert_model_path: Path,
    device_name: str,
) -> Dict[str, Any]:
    use_dnabert = _checkpoint_uses_dnabert(checkpoint_path)
    cache_key = (str(checkpoint_path), f"{rnafm_model_path}|{dnabert_model_path}|{device_name}")
    cached = _RUNTIME_CACHE.get(cache_key)
    if cached is not None:
        return cached

    with _CACHE_LOCK:
        cached = _RUNTIME_CACHE.get(cache_key)
        if cached is not None:
            return cached

        _ensure_runtime_assets(checkpoint_path, rnafm_model_path, use_dnabert, dnabert_model_path)
        device = torch.device(device_name)

        model = RNASTOPModel().to(device)
        state_dict = _load_checkpoint_state_dict(checkpoint_path)
        model.load_state_dict(state_dict, strict=use_dnabert)
        model.eval()

        try:
            fm_model, fm_alphabet = fm.pretrained.rna_fm_t12(str(rnafm_model_path))
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Failed to initialize RNA-FM from the configured local checkpoint. "
                    f"path={rnafm_model_path}; error={exc}"
                ),
            ) from exc
        fm_batch_converter = fm_alphabet.get_batch_converter()
        fm_model = fm_model.to(device)
        fm_model.eval()
        for parameter in fm_model.parameters():
            parameter.requires_grad = False

        dnabert_tokenizer = None
        dnabert_model = None
        if use_dnabert:
            try:
                dnabert_tokenizer = AutoTokenizer.from_pretrained(
                    str(dnabert_model_path),
                    local_files_only=True,
                )
                dnabert_model = AutoModel.from_pretrained(
                    str(dnabert_model_path),
                    local_files_only=True,
                ).to(device)
            except Exception as exc:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Failed to initialize DNABERT from the configured local directory. "
                        f"path={dnabert_model_path}; error={exc}"
                    ),
                ) from exc
            dnabert_model.eval()
            for parameter in dnabert_model.parameters():
                parameter.requires_grad = False

        runtime = {
            "model": model,
            "fm_model": fm_model,
            "fm_batch_converter": fm_batch_converter,
            "rnafm_model_path": str(rnafm_model_path),
            "dnabert_tokenizer": dnabert_tokenizer,
            "dnabert_model": dnabert_model,
            "dnabert_model_path": str(dnabert_model_path),
            "use_dnabert": use_dnabert,
            "device": device,
        }
        _RUNTIME_CACHE[cache_key] = runtime
        return runtime


def _preprocess_tokens(text: str) -> np.ndarray:
    return np.array([TOKENS.index(symbol) for symbol in text], dtype=np.int64)


def _get_structure_adj(seq_length: int, structure: str, sequence: str) -> np.ndarray:
    cue: List[int] = []
    a_structures = {
        ("A", "U"): np.zeros([seq_length, seq_length], dtype=np.float32),
        ("C", "G"): np.zeros([seq_length, seq_length], dtype=np.float32),
        ("U", "G"): np.zeros([seq_length, seq_length], dtype=np.float32),
        ("U", "A"): np.zeros([seq_length, seq_length], dtype=np.float32),
        ("G", "C"): np.zeros([seq_length, seq_length], dtype=np.float32),
        ("G", "U"): np.zeros([seq_length, seq_length], dtype=np.float32),
    }

    for index in range(seq_length):
        if structure[index] == "(":
            cue.append(index)
        elif structure[index] == ")":
            if not cue:
                continue
            start = cue.pop()
            left_key = (sequence[start], sequence[index])
            right_key = (sequence[index], sequence[start])
            if left_key in a_structures:
                a_structures[left_key][start, index] = 1.0
            if right_key in a_structures:
                a_structures[right_key][index, start] = 1.0

    stacked = np.stack([matrix for matrix in a_structures.values()], axis=2)
    return np.sum(stacked, axis=2, keepdims=True).astype(np.float32)


def _get_distance_matrix(base_pair_probs: np.ndarray) -> np.ndarray:
    idx = np.arange(base_pair_probs.shape[0])
    distances = np.abs(idx[:, None] - idx[None, :]) + 1
    inv_distances = 1.0 / distances.astype(np.float32)
    return np.stack([inv_distances**power for power in (1, 2, 4)], axis=2)


def _calc_neighbor(distances: np.ndarray, dim: int, distance_value: int) -> np.ndarray:
    loc_x, loc_y = np.where(distances == distance_value)
    for idx, x in enumerate(loc_x):
        y = loc_y[idx]
        if x + 1 < dim:
            distances[x + 1, y] = min(distances[x + 1, y], distance_value + 1)
        if y + 1 < dim:
            distances[x, y + 1] = min(distances[x, y + 1], distance_value + 1)
        if x - 1 >= 0:
            distances[x - 1, y] = min(distances[x - 1, y], distance_value + 1)
        if y - 1 >= 0:
            distances[x, y - 1] = min(distances[x, y - 1], distance_value + 1)
    return distances


def _get_distance_matrix_2d(structure_adj: np.ndarray) -> np.ndarray:
    dim = structure_adj.shape[0]
    structure_matrix = structure_adj[:, :, 0]
    distances = 10 + np.zeros_like(structure_matrix, dtype=np.float32)
    distances[structure_matrix == 1] = 1
    for index in range(dim):
        distances[index, index] = 0
    for distance_value in range(0, 9):
        distances = _calc_neighbor(distances, dim, distance_value)
    distances = distances + 1
    inv_distances = 1.0 / distances
    return np.stack([inv_distances**power for power in (1, 2, 4)], axis=2)


def _fallback_loop_type(structure: str) -> str:
    return "".join("S" if symbol in "()" else "E" for symbol in structure)


def _derive_loop_type(structure: str) -> str:
    converter = getattr(RNA, "db_to_element_string", None)
    if converter is not None:
        try:
            loop_type = converter(structure)
            if isinstance(loop_type, str) and len(loop_type) == len(structure):
                return loop_type
        except Exception:
            pass
    return _fallback_loop_type(structure)


def _extract_bpp_matrix(fc: Any, sequence: str, structure: str) -> np.ndarray:
    sequence_length = len(sequence)
    matrix = np.zeros((sequence_length, sequence_length), dtype=np.float32)
    bpp_accessor = getattr(fc, "bpp", None)
    if callable(bpp_accessor):
        try:
            for i in range(1, sequence_length + 1):
                for j in range(i + 1, sequence_length + 1):
                    probability = float(bpp_accessor(i, j))
                    matrix[i - 1, j - 1] = probability
                    matrix[j - 1, i - 1] = probability
            return matrix
        except TypeError:
            try:
                raw = bpp_accessor()
                if isinstance(raw, np.ndarray) and raw.shape == (sequence_length, sequence_length):
                    return raw.astype(np.float32)
                if isinstance(raw, list):
                    raw_array = np.asarray(raw, dtype=np.float32)
                    if raw_array.shape == (sequence_length, sequence_length):
                        return raw_array
            except Exception:
                pass
        except Exception:
            pass

    return _get_structure_adj(sequence_length, structure, sequence)[:, :, 0]


def _prepare_structure_features(
    sequence: str,
    structure_override: Optional[str],
    loop_override: Optional[str],
) -> Tuple[str, str, float, np.ndarray]:
    fc = RNA.fold_compound(sequence)
    structure, mfe = fc.mfe()

    if structure_override:
        structure = structure_override.strip()
    if len(structure) != len(sequence):
        raise HTTPException(
            status_code=400,
            detail="RNASTOP structure length must match the normalized RNA sequence length.",
        )

    fc.exp_params_rescale(mfe)
    fc.pf()
    bpp_matrix = _extract_bpp_matrix(fc, sequence, structure)

    loop_type = loop_override.strip() if loop_override else _derive_loop_type(structure)
    if len(loop_type) != len(sequence):
        raise HTTPException(
            status_code=400,
            detail="RNASTOP loop_type length must match the normalized RNA sequence length.",
        )
    unsupported_loop_chars = sorted(set(ch for ch in loop_type if ch not in TOKENS))
    if unsupported_loop_chars:
        raise HTTPException(
            status_code=400,
            detail=(
                "RNASTOP loop_type contains unsupported characters: "
                f"{''.join(unsupported_loop_chars)}"
            ),
        )

    structure_adj = _get_structure_adj(len(sequence), structure, sequence)
    distance_1d = _get_distance_matrix(bpp_matrix)
    distance_2d = _get_distance_matrix_2d(structure_adj)
    features = np.concatenate(
        [bpp_matrix[:, :, None], structure_adj, distance_1d, distance_2d],
        axis=2,
    ).astype(np.float32)
    return structure, loop_type, float(mfe), features


def _encode_with_rna_fm(sequence: str, runtime: Dict[str, Any]) -> torch.Tensor:
    batch_converter = runtime["fm_batch_converter"]
    fm_model = runtime["fm_model"]
    device = runtime["device"]
    _, _, batch_tokens = batch_converter([("RNA", sequence)])
    with torch.no_grad():
        fm_results = fm_model(batch_tokens.to(device), repr_layers=[12])
    return fm_results["representations"][12][:, 1:-1, :]


def _encode_with_dnabert(sequence: str, runtime: Dict[str, Any]) -> Optional[torch.Tensor]:
    if not runtime.get("use_dnabert"):
        return None
    tokenizer = runtime["dnabert_tokenizer"]
    model = runtime["dnabert_model"]
    device = runtime["device"]
    if tokenizer is None or model is None:
        return None

    input_ids = tokenizer(sequence, return_tensors="pt")["input_ids"].tolist()[0]
    if len(input_ids) < len(sequence):
        input_ids = input_ids + [3] * (len(sequence) - len(input_ids))
    elif len(input_ids) > len(sequence):
        input_ids = input_ids[: len(sequence)]
    input_tensor = torch.as_tensor(np.array([input_ids]), device=device)
    with torch.no_grad():
        return model(input_tensor)[0]


def _predict_profile(
    sequence: str,
    structure: str,
    loop_type: str,
    features: np.ndarray,
    runtime: Dict[str, Any],
) -> np.ndarray:
    del structure
    device = runtime["device"]
    model = runtime["model"]
    fm_seq = _encode_with_rna_fm(sequence, runtime)
    dnabert_seq = _encode_with_dnabert(sequence, runtime)

    loop_tensor = torch.tensor(_preprocess_tokens(loop_type), dtype=torch.long, device=device).unsqueeze(0)
    features_tensor = torch.tensor(features, dtype=torch.float32, device=device).unsqueeze(0)

    with torch.no_grad():
        predictions = model(loop_tensor, features_tensor, fm_seq, dnapt2_seq=dnabert_seq)
    return predictions[0, :, :3].detach().cpu().numpy()


@app.get("/health")
def health() -> dict[str, Any]:
    checkpoint_path = _resolve_checkpoint_path(None)
    rnafm_model_path = _resolve_rnafm_path(None)
    dnabert_model_path = _resolve_dnabert_path(None)
    return {
        "status": "ok",
        "repo_exists": RNASTOP_ROOT.exists(),
        "default_checkpoint_path": str(checkpoint_path),
        "default_checkpoint_exists": checkpoint_path.exists(),
        "default_rnafm_model_path": str(rnafm_model_path),
        "default_rnafm_model_exists": rnafm_model_path.exists(),
        "default_use_dnabert": _checkpoint_uses_dnabert(checkpoint_path),
        "default_dnabert_model_path": str(dnabert_model_path),
        "default_dnabert_model_exists": dnabert_model_path.exists(),
        "max_sequence_length": MAX_SEQUENCE_LENGTH,
        "default_device": DEFAULT_DEVICE,
        "prediction_columns": list(PREDICTION_COLUMNS),
    }


@app.post("/predict/stability", response_model=StabilityPredictionResponse)
def predict_stability(payload: StabilityPredictionRequest) -> StabilityPredictionResponse:
    sequence = _normalize_rna_sequence(payload.sequence)
    truncated = len(sequence) > MAX_SEQUENCE_LENGTH
    used_sequence = sequence[:MAX_SEQUENCE_LENGTH]
    checkpoint_path = _resolve_checkpoint_path(payload.checkpoint_path)
    rnafm_model_path = _resolve_rnafm_path(payload.rnafm_model_path)
    dnabert_model_path = _resolve_dnabert_path(payload.dnabert_model_path)
    runtime = _load_runtime(
        checkpoint_path,
        rnafm_model_path,
        dnabert_model_path,
        _resolve_device(payload.device),
    )

    structure, loop_type, mfe, features = _prepare_structure_features(
        used_sequence,
        payload.structure,
        payload.loop_type,
    )
    predictions = _predict_profile(used_sequence, structure, loop_type, features, runtime)

    mean_reactivity = float(np.mean(predictions[:, 0]))
    mean_deg_mg_ph10 = float(np.mean(predictions[:, 1]))
    mean_deg_mg_50c = float(np.mean(predictions[:, 2]))

    return StabilityPredictionResponse(
        sequence=sequence,
        used_sequence=used_sequence,
        sequence_length=len(sequence),
        used_length=len(used_sequence),
        truncated=truncated,
        structure=structure,
        loop_type=loop_type,
        mfe=mfe,
        mean_reactivity=mean_reactivity,
        mean_deg_Mg_pH10=mean_deg_mg_ph10,
        mean_deg_Mg_50C=mean_deg_mg_50c,
        per_position_predictions={
            "reactivity": predictions[:, 0].astype(float).tolist(),
            "deg_Mg_pH10": predictions[:, 1].astype(float).tolist(),
            "deg_Mg_50C": predictions[:, 2].astype(float).tolist(),
        },
        checkpoint_path=str(checkpoint_path),
        rnafm_model_path=str(runtime.get("rnafm_model_path", "")),
        dnabert_model_path=str(runtime.get("dnabert_model_path", "")),
        use_dnabert=bool(runtime.get("use_dnabert", False)),
        device=str(runtime["device"]),
    )
