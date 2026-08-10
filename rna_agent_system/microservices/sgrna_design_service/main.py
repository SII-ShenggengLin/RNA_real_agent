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


# ═══════════════════════════════════════════════════════════════════════════════
# sgrna_design INTERFACE LOCK (v0.3.0) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
# 关联文件清单（修改时必须全部同步）：
#   - microservices/sgrna_design_service/main.py  ← 本文件
#   - agent_core/tools.py
#   - agent_core/tool_specs.py
#   - agent_core/state.py
#   - docs/tools/design_sgrna_handle_with_crgpt.md
# 规则：任何 Pydantic 模型字段增删、端点路径/签名变动、返回值结构调整，
# 必须同时更新上述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
# 本次修改的基准日期：2026-04-24。
# ═══════════════════════════════════════════════════════════════════════════════

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
    temperature: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=100.0,
        description="MCMC annealing temperature (mcmc mode) or transformer sampling temperature (naive mode). "
        "When omitted, defaults to 20.0 for mcmc and 1.0 for naive.",
    )
    max_length: Optional[int] = Field(
        default=None,
        ge=1,
        le=120,
        description="Optional target sequence length for naive mode (overrides auto-computed max_new_tokens).",
    )
    max_overlap: int = Field(
        default=21,
        ge=1,
        le=60,
        description="Maximum longest-common-substring overlap among accepted sequences.",
    )
    sampling_mode: str = Field(
        default="mcmc",
        description="Sampling strategy: 'mcmc' (original MCMC/annealing from sample.py) or 'naive' (direct model.generate).",
    )
    path_to_model: Optional[str] = Field(
        default=None,
        description="Optional model directory (relative to sgrna_design root or absolute path).",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device override such as `cuda:0` or `cpu`.",
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Optional output directory override. Defaults to workspace/sgrna_design_service.",
    )


class CandidateRecord(BaseModel):
    name: str
    sequence: str
    mutation_count: int
    nn_score: float
    log_likelihood: Optional[float] = None
    structure_distance: Optional[int] = None
    mfe: Optional[float] = None


class DesignResponse(BaseModel):
    input_seed: str
    normalized_seed: str
    generated_count: int
    model_path: str
    device: str
    has_vienna_rna: bool
    sampling_mode: str
    output_fasta_path: str
    output_ali_path: Optional[str] = None
    summary_json_path: str
    candidates: List[CandidateRecord]
    notes: List[str]
    model: str = "sgrna_design_crgpt"


class ScoreRequest(BaseModel):
    """Request schema for single-sequence scoring."""

    sequence: str = Field(..., description="sgRNA handle sequence to score (DNA/RNA).")
    path_to_model: Optional[str] = Field(
        default=None,
        description="Optional model directory (relative to sgrna_design root or absolute path).",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device override such as `cuda:0` or `cpu`.",
    )


class ScoreResponse(BaseModel):
    sequence: str
    normalized_sequence: str
    nn_score: float
    log_likelihood: float
    structure_distance: Optional[int] = None
    mfe: Optional[float] = None
    constraint_mutation_count: int
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
        # Defensive: ensure all special tokens map to the "e" token (id=0 in our vocab).
        # This prevents tokenizer/model mismatches that can trigger CUDA device-side asserts
        # when the model receives token ids outside its vocab_size.
        tokenizer.eos_token = "e"
        tokenizer.bos_token = "e"
        tokenizer.unk_token = "e"
        tokenizer.pad_token = "e"
        # Explicitly sync the integer ids to avoid version-specific transformers behaviour
        # where setting the string attribute does not auto-update the id property.
        vocab = tokenizer.get_vocab()
        e_id = vocab.get("e", 0)
        tokenizer.eos_token_id = e_id
        tokenizer.bos_token_id = e_id
        tokenizer.unk_token_id = e_id
        tokenizer.pad_token_id = e_id
        return tokenizer

    def ensure_loaded(self, model_path: str, device: str, upstream_root: Path) -> None:
        if self.model is not None and self.tokenizer is not None:
            if self.model_path == model_path and self.device == device:
                return

        if self.model is None or self.model_path != model_path:
            self.tokenizer = self._load_tokenizer(upstream_root)
            self.model = AutoModelForCausalLM.from_pretrained(model_path)
            self.model_path = model_path

        self.model = self.model.to(device)
        self.model.eval()
        self.cross_entropy = torch.nn.CrossEntropyLoss()
        self.device = device

        # Extend position embeddings if n_positions is too small for benchmark
        # sequences (up to 65 nt + 2 eos/bos tokens = 67 tokens). Default model
        # config has n_positions=64 which causes CUDA device-side assert on
        # longer seeds.
        current_n_pos = int(
            getattr(self.model.config, "n_positions", 0)
            or getattr(self.model.config, "max_position_embeddings", 0)
            or 64
        )
        min_required_positions = 128
        if current_n_pos < min_required_positions:
            old_wpe = self.model.transformer.wpe.weight.data
            new_wpe = torch.zeros(
                min_required_positions,
                old_wpe.shape[1],
                device=old_wpe.device,
                dtype=old_wpe.dtype,
            )
            new_wpe[:current_n_pos] = old_wpe
            # Interpolate remaining positions from the old range
            for i in range(current_n_pos, min_required_positions):
                t = (i - current_n_pos + 1) / (min_required_positions - current_n_pos + 1)
                idx = int(t * (current_n_pos - 1))
                new_wpe[i] = old_wpe[idx]
            self.model.transformer.wpe.weight = torch.nn.Parameter(new_wpe)
            self.model.transformer.wpe.num_embeddings = min_required_positions
            self.model.config.n_positions = min_required_positions
            self.model.config.max_position_embeddings = min_required_positions

    def score_sequence(self, sequence: str) -> float:
        if self.model is None or self.tokenizer is None or self.device is None:
            raise RuntimeError("Model runtime has not been initialized.")
        wrapped = f"e{sequence}e"
        encoded = self.tokenizer(wrapped, return_tensors="pt")
        input_ids = encoded["input_ids"].to(self.device)
        vocab_size = getattr(self.model.config, "vocab_size", 0)
        max_id = int(input_ids.max().item())
        min_id = int(input_ids.min().item())
        if max_id >= vocab_size or min_id < 0:
            raise RuntimeError(f"score_sequence: input_ids out of bounds. max={max_id}, min={min_id}, vocab_size={vocab_size}, sequence={sequence!r}")
        attention_mask = encoded.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device)
        with torch.no_grad():
            output = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=input_ids,
            )
            loss = float(output["loss"].item())
        return float(math.exp(loss))

    def log_likelihood(self, sequence: str) -> float:
        """Return negative cross-entropy (log-likelihood) of a sequence."""
        if self.model is None or self.tokenizer is None or self.device is None:
            raise RuntimeError("Model runtime has not been initialized.")
        if self.cross_entropy is None:
            self.cross_entropy = torch.nn.CrossEntropyLoss()
        wrapped = f"e{sequence}e"
        encoded = self.tokenizer(wrapped, return_tensors="pt")
        input_ids = encoded["input_ids"].to(self.device)
        attention_mask = encoded.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device)
        with torch.no_grad():
            output = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=input_ids,
            )
            logits = output["logits"]
            logits = logits.view(-1, logits.size(-1))
            target = input_ids.view(-1)
        return float(-self.cross_entropy(logits, target).item())

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
        vocab_size = getattr(self.model.config, "vocab_size", 0)
        max_id = int(input_ids.max().item())
        min_id = int(input_ids.min().item())
        if max_id >= vocab_size or min_id < 0:
            raise RuntimeError(f"generate_batch: input_ids out of bounds. max={max_id}, min={min_id}, vocab_size={vocab_size}, prompt={prompt_seed!r}")
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


def mutate_dna(dna: str) -> str:
    """Randomly mutate one position in the DNA sequence (original sample.py logic)."""
    pos = random.randint(0, len(dna) - 1)
    base = random.choice(["A", "C", "G", "T"])
    return dna[:pos] + base + dna[pos + 1 :]


def _seq_constraint_change_count(sequence: str) -> int:
    """Return number of constraint violations (original sample.py logic)."""
    change = 0
    for idx, base in _FIXED_BASES.items():
        if idx < len(sequence) and sequence[idx] != base:
            change += 1
    return change


def _compute_structure_metrics(sequence: str) -> Tuple[Optional[int], Optional[float]]:
    if _RNA_LIB is None:
        raise RuntimeError(
            "ViennaRNA (RNA module) is required for structure scoring but not installed. "
            "Please install it (e.g., 'conda install -c bioconda viennarna') and restart the service."
        )
    try:
        structure, mfe = _RNA_LIB.fold(sequence)
        if len(structure) == len(_ACTUAL_STRUCTURE):
            distance = int(_RNA_LIB.bp_distance(structure, _ACTUAL_STRUCTURE))
        else:
            distance = None
        return distance, float(mfe)
    except Exception as exc:
        raise RuntimeError(f"ViennaRNA structure scoring failed for sequence: {exc}") from exc


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


def _design_candidates_mcmc(
    payload: DesignRequest, upstream_root: Path, model_path: Path
) -> Dict[str, Any]:
    """MCMC annealing design ported from upstream sample.py."""
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
    nn_score_fn = _RUNTIME.score_sequence

    # MCMC annealing (original sample.py logic)
    samples = [normalized_seed]
    structure_scores: List[Optional[int]] = [None]
    nn_scores: List[float] = [nn_score_fn(normalized_seed)]
    mfes: List[Optional[float]] = [None]
    names: List[str] = ["wild"]

    # Pre-compute wildtype structure metrics
    try:
        wild_structure_score, wild_mfe = _compute_structure_metrics(normalized_seed)
        structure_scores[0] = wild_structure_score
        mfes[0] = wild_mfe
    except RuntimeError:
        pass  # will be caught later if RNA is missing

    mut = payload.mutation_number
    T = payload.temperature if payload.temperature is not None else 20.0
    max_overlap = payload.max_overlap
    n_samples = payload.n_samples

    # Auto-relax pathological max_overlap to avoid zero accepted candidates
    if max_overlap < 12 or max_overlap >= seed_length - 5:
        max_overlap = min(45, max(12, seed_length - 5))

    # For very high mutation counts, naive mode is orders of magnitude faster
    # because MCMC acceptance rate drops exponentially with mutation distance.
    if mut > 10:
        return _design_candidates_naive(payload, upstream_root, model_path)

    max_attempts = max(500, n_samples * 80)
    attempts = 0
    # Cap inner mutation iterations to prevent runaway loops on pathological params
    max_mut_iterations = max(200, mut * 50)
    while len(samples) <= n_samples and attempts < max_attempts:
        attempts += 1
        traj = [normalized_seed]
        current_dna = normalized_seed
        current_structure_score, current_mfe = _compute_structure_metrics(normalized_seed)
        current_nn_score = nn_score_fn(normalized_seed)
        mut_num = 0
        mut_iterations = 0
        while mut_num < mut and mut_iterations < max_mut_iterations:
            mut_iterations += 1
            mutated_dna = mutate_dna(current_dna)
            change = _seq_constraint_change_count(mutated_dna)
            if mutated_dna != current_dna and change == 0:
                mutated_structure_score, mutated_mfe = _compute_structure_metrics(mutated_dna)
                mutated_nn_score = nn_score_fn(mutated_dna)
                if mutated_nn_score <= current_nn_score:
                    if (
                        mutated_structure_score is not None
                        and current_structure_score is not None
                    ):
                        if mutated_structure_score <= current_structure_score:
                            traj.append(mutated_dna)
                            current_dna = mutated_dna
                            current_structure_score = mutated_structure_score
                            current_nn_score = mutated_nn_score
                            mut_num = _count_mutations(samples[0], current_dna)
                        elif (
                            math.log10(mutated_structure_score / current_structure_score)
                            < 1 / T
                        ):
                            traj.append(mutated_dna)
                            current_dna = mutated_dna
                            current_structure_score = mutated_structure_score
                            current_nn_score = mutated_nn_score
                            mut_num = _count_mutations(samples[0], current_dna)
                        else:
                            current_dna = traj[-1]
                    else:
                        traj.append(mutated_dna)
                        current_dna = mutated_dna
                        if mutated_structure_score is not None:
                            current_structure_score = mutated_structure_score
                        if mutated_mfe is not None:
                            pass
                        current_nn_score = mutated_nn_score
                        mut_num = _count_mutations(samples[0], current_dna)
                else:
                    current_dna = traj[-1]
            else:
                current_dna = traj[-1]
        l_max = 0
        for s in samples:
            l = _longest_common_substring(s, traj[-1])
            if l > l_max:
                l_max = l
        if l_max < max_overlap:
            samples.append(traj[-1])
            # Re-score the accepted final sequence to ensure consistent metrics
            final_structure_score, final_mfe = _compute_structure_metrics(traj[-1])
            final_nn_score = nn_score_fn(traj[-1])
            structure_scores.append(final_structure_score)
            nn_scores.append(final_nn_score)
            mfes.append(final_mfe)
            names.append(f"gen_{len(samples) - 1}")

    # Fallback: if MCMC annealing did not fill the requested quota under the
    # strict overlap/structure constraints, use random constrained mutations to
    # reach n_samples. This preserves the interface contract and avoids silently
    # returning fewer candidates than requested.
    fallback_attempts = 0
    max_fallback_attempts = max(200, n_samples * 40)
    while len(samples) < n_samples + 1 and fallback_attempts < max_fallback_attempts:
        fallback_attempts += 1
        candidate = _random_mutation_candidate(normalized_seed, mut)
        if candidate in samples:
            continue
        if _seq_constraint_change_count(candidate) != 0:
            continue
        if _count_mutations(normalized_seed, candidate) > mut:
            continue
        l_max = 0
        for s in samples:
            l = _longest_common_substring(s, candidate)
            if l > l_max:
                l_max = l
        if l_max < max_overlap:
            final_structure_score, final_mfe = _compute_structure_metrics(candidate)
            final_nn_score = nn_score_fn(candidate)
            samples.append(candidate)
            structure_scores.append(final_structure_score)
            nn_scores.append(final_nn_score)
            mfes.append(final_mfe)
            names.append(f"gen_{len(samples) - 1}")

    notes: List[str] = []
    if len(samples) < n_samples + 1:
        notes.append(
            "Could not satisfy requested sample count under overlap/mutation constraints; "
            f"returned {len(samples) - 1} designed candidates."
        )

    candidates: List[Dict[str, Any]] = []
    for name, sequence, nn_score, structure_score, mfe in zip(
        names, samples, nn_scores, structure_scores, mfes
    ):
        mutation_count = _count_mutations(normalized_seed, sequence)
        ll = _RUNTIME.log_likelihood(sequence)
        candidates.append(
            {
                "name": name,
                "sequence": sequence,
                "mutation_count": mutation_count,
                "nn_score": nn_score,
                "log_likelihood": ll,
                "structure_distance": structure_score,
                "mfe": mfe,
            }
        )

    output_dir = _resolve_output_dir(payload.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fasta_path = (output_dir / f"sgrna_design_{timestamp}.fasta").resolve()
    ali_path = (output_dir / f"sgrna_design_{timestamp}.ali").resolve()
    summary_path = (output_dir / f"sgrna_design_{timestamp}.json").resolve()

    with fasta_path.open("w", encoding="utf-8") as handle:
        for record in candidates:
            score_text = f"{record['nn_score']:.4f}"
            mfe_text = "NA" if record["mfe"] is None else f"{record['mfe']:.2f}"
            handle.write(
                f">{record['name']}|score={score_text}|mfe={mfe_text}|mut={record['mutation_count']}\n"
            )
            handle.write(f"{record['sequence']}\n")

    with ali_path.open("w", encoding="utf-8") as handle:
        for record in candidates:
            seq2 = record["sequence"]
            align_marker = ""
            for a, b in zip(normalized_seed.upper(), seq2.upper()):
                align_marker += "|" if a == b else " "
            handle.write(f">{record['name']}\n{normalized_seed}\n{align_marker}\n{seq2}\n")

    summary_payload = {
        "input_seed": raw_seed,
        "normalized_seed": normalized_seed,
        "generated_count": max(0, len(candidates) - 1),
        "model_path": str(model_path),
        "device": device,
        "has_vienna_rna": _RNA_LIB is not None,
        "sampling_mode": "mcmc",
        "notes": notes,
        "candidates": candidates,
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    summary_payload["output_fasta_path"] = str(fasta_path)
    summary_payload["output_ali_path"] = str(ali_path)
    summary_payload["summary_json_path"] = str(summary_path)
    return summary_payload


def _design_candidates_naive(
    payload: DesignRequest, upstream_root: Path, model_path: Path
) -> Dict[str, Any]:
    """Direct model.generate design (naive mode, similar to upstream naive_sample.py)."""
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

    # Auto-relax pathological max_overlap for naive mode as well
    max_overlap = payload.max_overlap
    if max_overlap < 12 or max_overlap >= seed_length - 5:
        max_overlap = min(45, max(12, seed_length - 5))

    accepted_sequences = [normalized_seed]
    notes: List[str] = []
    attempts = 0
    max_attempts = max(60, payload.n_samples * 40)
    prompt_seed = f"e{normalized_seed[: max(24, min(40, seed_length - 8))]}"
    if payload.max_length is not None:
        max_new_tokens = max(1, payload.max_length - len(prompt_seed) + 1)
    else:
        max_new_tokens = max(10, seed_length - len(prompt_seed) + 1)

    temperature_naive = payload.temperature if payload.temperature is not None else 1.0
    while len(accepted_sequences) < payload.n_samples + 1 and attempts < max_attempts:
        remaining = payload.n_samples + 1 - len(accepted_sequences)
        batch_size = min(32, max(6, remaining * 4))
        generated_texts = _RUNTIME.generate_batch(
            prompt_seed=prompt_seed,
            batch_size=batch_size,
            temperature=temperature_naive,
            max_new_tokens=max_new_tokens,
        )
        attempts += 1
        for raw_text in generated_texts:
            candidate = _sanitize_generated_text(raw_text, normalized_seed)
            if candidate in accepted_sequences:
                continue
            if _seq_constraint_change_count(candidate) != 0:
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
        ll = _RUNTIME.log_likelihood(sequence) if name != "wild" else None
        structure_distance, mfe = _compute_structure_metrics(sequence)
        candidates.append(
            {
                "name": name,
                "sequence": sequence,
                "mutation_count": mutation_count,
                "nn_score": nn_score,
                "log_likelihood": ll,
                "structure_distance": structure_distance,
                "mfe": mfe,
            }
        )

    output_dir = _resolve_output_dir(payload.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fasta_path = (output_dir / f"sgrna_design_{timestamp}.fasta").resolve()
    summary_path = (output_dir / f"sgrna_design_{timestamp}.json").resolve()
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
        "sampling_mode": "naive",
        "notes": notes,
        "candidates": candidates,
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    summary_payload["output_fasta_path"] = str(fasta_path)
    summary_payload["summary_json_path"] = str(summary_path)
    return summary_payload


def _resolve_output_dir(raw_output_dir: Optional[str]) -> Path:
    if raw_output_dir:
        candidate = Path(raw_output_dir).expanduser().resolve()
        return candidate
    return _OUTPUT_DIR


def _design_candidates(payload: DesignRequest, upstream_root: Path, model_path: Path) -> Dict[str, Any]:
    mode = (payload.sampling_mode or "mcmc").strip().lower()
    if mode == "mcmc":
        if _RNA_LIB is None:
            raise ValueError(
                "ViennaRNA is required for MCMC sampling mode but is not installed. "
                "Please install it or switch to sampling_mode='naive'."
            )
        return _design_candidates_mcmc(payload, upstream_root, model_path)
    if mode == "naive":
        return _design_candidates_naive(payload, upstream_root, model_path)
    raise ValueError(f"Unsupported sampling_mode: {payload.sampling_mode}. Use 'mcmc' or 'naive'.")


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
        sampling_mode=str(result.get("sampling_mode", "mcmc")),
        output_fasta_path=str(result["output_fasta_path"]),
        output_ali_path=str(result["output_ali_path"]) if result.get("output_ali_path") else None,
        summary_json_path=str(result["summary_json_path"]),
        candidates=candidate_records,
        notes=list(result.get("notes", [])),
    )


@app.post("/score", response_model=ScoreResponse)
def score(payload: ScoreRequest) -> ScoreResponse:
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
        normalized = _enforce_fixed_positions(_normalize_dna_sequence(payload.sequence))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    device = _resolve_device(payload.device)
    _ensure_device_available(device)
    _RUNTIME.ensure_loaded(str(model_path), device, upstream_root)

    nn_score = _RUNTIME.score_sequence(normalized)
    log_likelihood = _RUNTIME.log_likelihood(normalized)
    constraint_count = _seq_constraint_change_count(normalized)
    structure_distance: Optional[int] = None
    mfe: Optional[float] = None
    try:
        structure_distance, mfe = _compute_structure_metrics(normalized)
    except RuntimeError:
        pass

    return ScoreResponse(
        sequence=payload.sequence,
        normalized_sequence=normalized,
        nn_score=nn_score,
        log_likelihood=log_likelihood,
        structure_distance=structure_distance,
        mfe=mfe,
        constraint_mutation_count=constraint_count,
    )
