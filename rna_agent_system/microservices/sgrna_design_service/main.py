"""sgRNA handle design microservice based on upstream sgrna_design model assets."""

from __future__ import annotations

import json
import math
import os
import random
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, GPT2Tokenizer


APP_DIR = Path(__file__).resolve().parent
_RNA_AGENT_SYSTEM_ROOT = APP_DIR.parents[1]
_DEFAULT_UPSTREAM_ROOT = (_RNA_AGENT_SYSTEM_ROOT / "external_repos" / "sgrna_design").resolve()
_OUTPUT_DIR = (_RNA_AGENT_SYSTEM_ROOT / "workspace" / "sgrna_design_service").resolve()
_DEFAULT_MODEL_PATH = "trained_model/crgen_small"
_DEFAULT_WILDTYPE = "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG"
_FIXED_BASES = {
    6: "G",
    22: "G",
    23: "T",
    30: "A",
    32: "G",
}
_CANONICAL_DNA = {"A", "C", "G", "T"}
_ACTUAL_STRUCTURE = "((((((..((((....))))....))))))..(((..).)).......((((....))))."
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    import RNA as _RNA_LIB  # type: ignore
except Exception:  # pragma: no cover - optional dependency for structure score
    _RNA_LIB = None


class DesignRequest(BaseModel):
    """Request schema for sgRNA handle design."""

    seed_sequence: Optional[str] = Field(
        default=None,
        description="Optional seed/wildtype sgRNA handle sequence (DNA or RNA letters).",
    )
    n_samples: int = Field(default=10, ge=1, le=200)
    mutation_number: int = Field(
        default=22,
        ge=1,
        le=40,
        description="Maximum number of mutations allowed relative to seed sequence.",
    )
    temperature: float = Field(default=1.0, gt=0.0, le=5.0)
    max_overlap: int = Field(
        default=21,
        ge=1,
        le=60,
        description="Maximum longest-common-substring overlap among accepted sequences.",
    )
    path_to_model: Optional[str] = Field(
        default=None,
        description="Optional model directory (relative to sgrna_design root or absolute path).",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device override such as `cuda:0` or `cpu`.",
    )


class CandidateRecord(BaseModel):
    name: str
    sequence: str
    mutation_count: int
    nn_score: float
    structure_distance: Optional[int] = None
    mfe: Optional[float] = None


class DesignResponse(BaseModel):
    input_seed: str
    normalized_seed: str
    generated_count: int
    model_path: str
    device: str
    has_vienna_rna: bool
    output_fasta_path: str
    summary_json_path: str
    candidates: List[CandidateRecord]
    notes: List[str]
    model: str = "sgrna_design_crgpt"


class _ModelRuntime:
    """Runtime cache for tokenizer+model to avoid repeated loading."""

    def __init__(self) -> None:
        self.model_path: Optional[str] = None
        self.device: Optional[str] = None
        self.tokenizer: Optional[GPT2Tokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None

    def _load_tokenizer(self, upstream_root: Path) -> GPT2Tokenizer:
        tokenizer = GPT2Tokenizer(
            str((upstream_root / "crgen" / "dna.json").resolve()),
            str((upstream_root / "crgen" / "merges.txt").resolve()),
        )
        tokenizer.eos_token = "e"
        tokenizer.bos_token = "e"
        tokenizer.unk_token = "e"
        tokenizer.pad_token = "e"
        return tokenizer

    def ensure_loaded(self, model_path: str, device: str, upstream_root: Path) -> None:
        if self.model is not None and self.tokenizer is not None:
            if self.model_path == model_path and self.device == device:
                return
        tokenizer = self._load_tokenizer(upstream_root)
        model = AutoModelForCausalLM.from_pretrained(model_path)
        model.eval().to(device)
        self.tokenizer = tokenizer
        self.model = model
        self.model_path = model_path
        self.device = device

    def score_sequence(self, sequence: str) -> float:
        if self.model is None or self.tokenizer is None or self.device is None:
            raise RuntimeError("Model runtime has not been initialized.")
        wrapped = f"e{sequence}e"
        with torch.no_grad():
            input_ids = torch.tensor(self.tokenizer(wrapped)["input_ids"], device=self.device)
            output = self.model(input_ids=input_ids, labels=input_ids)
            loss = float(output["loss"].item())
        return float(math.exp(loss))

    def generate_batch(
        self,
        prompt_seed: str,
        batch_size: int,
        temperature: float,
        max_new_tokens: int,
    ) -> List[str]:
        if self.model is None or self.tokenizer is None or self.device is None:
            raise RuntimeError("Model runtime has not been initialized.")
        encoded = self.tokenizer(prompt_seed, return_tensors="pt")
        input_ids = encoded["input_ids"].to(self.device)
        prompt_len = int(input_ids.shape[-1])
        attention_mask = encoded.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device)
        eos_token_id = self.tokenizer.eos_token_id
        if eos_token_id is None:
            eos_token_id = 0
        max_positions = int(
            getattr(self.model.config, "n_positions", 0)
            or getattr(self.model.config, "max_position_embeddings", 0)
            or 64
        )
        safe_max_new_tokens = min(int(max_new_tokens), max(1, max_positions - prompt_len))
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                do_sample=True,
                num_return_sequences=batch_size,
                max_new_tokens=safe_max_new_tokens,
                temperature=temperature,
                eos_token_id=eos_token_id,
                pad_token_id=eos_token_id,
            )
        decoded = [self.tokenizer.decode(seq, skip_special_tokens=False) for seq in outputs]
        return decoded


_RUNTIME = _ModelRuntime()


def _resolve_upstream_root() -> Path:
    override = os.environ.get("SGRNA_DESIGN_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _DEFAULT_UPSTREAM_ROOT


def _resolve_model_path(upstream_root: Path, raw_model_path: Optional[str]) -> Path:
    model_rel = (raw_model_path or _DEFAULT_MODEL_PATH).strip()
    candidate = Path(model_rel).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (upstream_root / candidate).resolve()


def _normalize_dna_sequence(raw_text: str) -> str:
    normalized = raw_text.strip().upper().replace("U", "T")
    sequence = re.sub(r"[^A-Z]", "", normalized)
    invalid = sorted(ch for ch in set(sequence) if ch not in _CANONICAL_DNA)
    if invalid:
        raise ValueError(
            "Sequence contains unsupported characters. "
            f"Only A/C/G/T/U are allowed; found: {''.join(invalid)}"
        )
    return sequence


def _enforce_fixed_positions(sequence: str) -> str:
    chars = list(sequence)
    for idx, base in _FIXED_BASES.items():
        if idx < len(chars):
            chars[idx] = base
    return "".join(chars)


def _seq_constraint(sequence: str) -> bool:
    return all(idx < len(sequence) and sequence[idx] == base for idx, base in _FIXED_BASES.items())


def _count_mutations(seed: str, sequence: str) -> int:
    return sum(1 for i in range(min(len(seed), len(sequence))) if seed[i] != sequence[i])


def _longest_common_substring(seq1: str, seq2: str) -> int:
    matcher = SequenceMatcher(None, seq1, seq2)
    return matcher.find_longest_match(0, len(seq1), 0, len(seq2)).size


def _sanitize_generated_text(raw_text: str, seed: str) -> str:
    cleaned = re.sub(r"[^ACGTacgt]", "", raw_text).upper().replace("U", "T")
    if cleaned.startswith("E"):
        cleaned = cleaned[1:]
    target_len = len(seed)
    if len(cleaned) < target_len:
        cleaned = (cleaned + seed[len(cleaned) :])[:target_len]
    else:
        cleaned = cleaned[:target_len]
    return _enforce_fixed_positions(cleaned)


def _random_mutation_candidate(seed: str, max_mutations: int) -> str:
    chars = list(_enforce_fixed_positions(seed))
    mutable_positions = [i for i in range(len(chars)) if i not in _FIXED_BASES]
    mutation_count = min(max_mutations, len(mutable_positions))
    target_mutations = random.randint(max(1, mutation_count // 3), max(1, mutation_count))
    random.shuffle(mutable_positions)
    for idx in mutable_positions[:target_mutations]:
        base_choices = [b for b in ("A", "C", "G", "T") if b != chars[idx]]
        chars[idx] = random.choice(base_choices)
    return _enforce_fixed_positions("".join(chars))


def _compute_structure_metrics(sequence: str) -> Tuple[Optional[int], Optional[float]]:
    if _RNA_LIB is None:
        return None, None
    try:
        structure, mfe = _RNA_LIB.fold(sequence)
        if len(structure) == len(_ACTUAL_STRUCTURE):
            distance = int(_RNA_LIB.bp_distance(structure, _ACTUAL_STRUCTURE))
        else:
            distance = None
        return distance, float(mfe)
    except Exception:
        return None, None


def _resolve_device(raw_device: Optional[str]) -> str:
    env_device = os.environ.get("SGRNA_DESIGN_DEVICE", "").strip()
    requested = (raw_device or env_device).strip()
    if requested:
        return requested
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def _ensure_device_available(device: str) -> None:
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise ValueError(
            f"Requested device `{device}` but CUDA is unavailable in current runtime."
        )


def _design_candidates(payload: DesignRequest, upstream_root: Path, model_path: Path) -> Dict[str, Any]:
    raw_seed = payload.seed_sequence or _DEFAULT_WILDTYPE
    normalized_seed = _enforce_fixed_positions(_normalize_dna_sequence(raw_seed))
    seed_length = len(normalized_seed)
    if seed_length < 40 or seed_length > 120:
        raise ValueError(
            f"Seed length should be in [40, 120] for current model; got {seed_length}."
        )
    if payload.max_overlap >= seed_length:
        raise ValueError(
            f"`max_overlap` must be smaller than seed length ({seed_length})."
        )

    device = _resolve_device(payload.device)
    _ensure_device_available(device)
    _RUNTIME.ensure_loaded(str(model_path), device, upstream_root)

    accepted_sequences = [normalized_seed]
    notes: List[str] = []
    attempts = 0
    max_attempts = max(60, payload.n_samples * 40)
    prompt_seed = f"e{normalized_seed[: max(24, min(40, seed_length - 8))]}"
    max_new_tokens = max(10, seed_length - len(prompt_seed) + 1)

    while len(accepted_sequences) < payload.n_samples + 1 and attempts < max_attempts:
        remaining = payload.n_samples + 1 - len(accepted_sequences)
        batch_size = min(32, max(6, remaining * 4))
        generated_texts = _RUNTIME.generate_batch(
            prompt_seed=prompt_seed,
            batch_size=batch_size,
            temperature=payload.temperature,
            max_new_tokens=max_new_tokens,
        )
        attempts += 1
        for raw_text in generated_texts:
            candidate = _sanitize_generated_text(raw_text, normalized_seed)
            if candidate in accepted_sequences:
                continue
            if not _seq_constraint(candidate):
                continue
            if _count_mutations(normalized_seed, candidate) > payload.mutation_number:
                continue
            overlap = 0
            for existing in accepted_sequences:
                overlap = max(overlap, _longest_common_substring(existing, candidate))
            if overlap >= payload.max_overlap:
                continue
            accepted_sequences.append(candidate)
            if len(accepted_sequences) >= payload.n_samples + 1:
                break

    while len(accepted_sequences) < payload.n_samples + 1 and attempts < max_attempts + 100:
        attempts += 1
        candidate = _random_mutation_candidate(normalized_seed, payload.mutation_number)
        if candidate in accepted_sequences:
            continue
        if _count_mutations(normalized_seed, candidate) > payload.mutation_number:
            continue
        overlap = 0
        for existing in accepted_sequences:
            overlap = max(overlap, _longest_common_substring(existing, candidate))
        if overlap >= payload.max_overlap:
            continue
        accepted_sequences.append(candidate)

    if len(accepted_sequences) < payload.n_samples + 1:
        notes.append(
            "Could not satisfy requested sample count under overlap/mutation constraints; "
            f"returned {len(accepted_sequences) - 1} designed candidates."
        )

    candidates: List[Dict[str, Any]] = []
    for idx, sequence in enumerate(accepted_sequences):
        name = "wild" if idx == 0 else f"gen_{idx}"
        mutation_count = _count_mutations(normalized_seed, sequence)
        nn_score = _RUNTIME.score_sequence(sequence)
        structure_distance, mfe = _compute_structure_metrics(sequence)
        candidates.append(
            {
                "name": name,
                "sequence": sequence,
                "mutation_count": mutation_count,
                "nn_score": nn_score,
                "structure_distance": structure_distance,
                "mfe": mfe,
            }
        )

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fasta_path = (_OUTPUT_DIR / f"sgrna_design_{timestamp}.fasta").resolve()
    summary_path = (_OUTPUT_DIR / f"sgrna_design_{timestamp}.json").resolve()
    with fasta_path.open("w", encoding="utf-8") as handle:
        for record in candidates:
            score_text = f"{record['nn_score']:.4f}"
            mfe_text = "NA" if record["mfe"] is None else f"{record['mfe']:.2f}"
            handle.write(
                f">{record['name']}|score={score_text}|mfe={mfe_text}|mut={record['mutation_count']}\n"
            )
            handle.write(f"{record['sequence']}\n")

    summary_payload = {
        "input_seed": raw_seed,
        "normalized_seed": normalized_seed,
        "generated_count": max(0, len(candidates) - 1),
        "model_path": str(model_path),
        "device": device,
        "has_vienna_rna": _RNA_LIB is not None,
        "notes": notes,
        "candidates": candidates,
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    summary_payload["output_fasta_path"] = str(fasta_path)
    summary_payload["summary_json_path"] = str(summary_path)
    return summary_payload


app = FastAPI(
    title="sgRNA Design Service",
    description="Design sgRNA handle candidates using upstream sgrna_design model assets.",
    version="0.1.0-port8017",
)


@app.get("/health")
def health() -> Dict[str, Any]:
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    upstream_root = _resolve_upstream_root()
    model_path = _resolve_model_path(upstream_root, None)
    dna_json = (upstream_root / "crgen" / "dna.json").resolve()
    merges = (upstream_root / "crgen" / "merges.txt").resolve()
    return {
        "status": "ok" if upstream_root.exists() and model_path.exists() else "degraded",
        "upstream_root": str(upstream_root),
        "upstream_exists": upstream_root.exists(),
        "model_path": str(model_path),
        "model_exists": model_path.exists(),
        "tokenizer_dna_json_exists": dna_json.exists(),
        "tokenizer_merges_exists": merges.exists(),
        "has_vienna_rna": _RNA_LIB is not None,
        "cuda_available": bool(torch.cuda.is_available()),
        "default_device": _resolve_device(None),
        "output_dir": str(_OUTPUT_DIR),
    }


@app.post("/design", response_model=DesignResponse)
def design(payload: DesignRequest) -> DesignResponse:
    upstream_root = _resolve_upstream_root()
    if not upstream_root.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "sgrna_design upstream repo not found. "
                f"Expected at: {upstream_root}. "
                "Clone it first or set SGRNA_DESIGN_ROOT."
            ),
        )
    model_path = _resolve_model_path(upstream_root, payload.path_to_model)
    if not model_path.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "Model path does not exist. "
                f"Resolved model path: {model_path}. "
                "Please ensure trained model files are available."
            ),
        )
    try:
        result = _design_candidates(payload, upstream_root, model_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=500, detail=f"sgrna_design service failed: {exc}") from exc

    candidate_records = [CandidateRecord(**record) for record in result["candidates"]]
    return DesignResponse(
        input_seed=str(result["input_seed"]),
        normalized_seed=str(result["normalized_seed"]),
        generated_count=int(result["generated_count"]),
        model_path=str(result["model_path"]),
        device=str(result["device"]),
        has_vienna_rna=bool(result["has_vienna_rna"]),
        output_fasta_path=str(result["output_fasta_path"]),
        summary_json_path=str(result["summary_json_path"]),
        candidates=candidate_records,
        notes=list(result.get("notes", [])),
    )
