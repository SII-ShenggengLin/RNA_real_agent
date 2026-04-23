"""IRESfinder microservice rebuilt for Python 3 deployment.

INTERFACE LOCK (v0.2.0): Locked implementation. The canonical reference for this
service's behaviour is the state after the 2026-04-23 refactor. Any change to
feature engineering, preprocessing, or IO schemas must be synchronized with:
- agent_core/tools.py :: IRESfinderPredictionInput / predict_putative_ires_with_iresfinder
- agent_core/tool_specs.py :: IRESfinderPredictionOutput / TOOL_SPECS
- agent_core/state.py :: iresfinder_* fields
- agent_core/nodes.py :: tool_execution_node / critic_node IRESfinder branches
- docs/tools/predict_putative_ires_with_iresfinder.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, List, Optional, Sequence, Tuple
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sklearn.linear_model import LogisticRegressionCV
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IRESFINDER_ROOT = PROJECT_ROOT / "external_repos" / "IRESfinder"
IRESFINDER_TRAIN_DATA = IRESFINDER_ROOT / "module" / "train.data"
IRESFINDER_SERVICE_OUTPUT_DIR = PROJECT_ROOT / "workspace" / "iresfinder_service"
DEFAULT_WINDOW_SIZE = 174
DEFAULT_STEP_SIZE = 50
DEFAULT_THRESHOLD = 0.5
SELECTED_FEATURE_INDICES = [
    0,
    50,
    1774,
    382,
    339,
    872,
    2069,
    197,
    250,
    119,
    98,
    13,
    591,
    1257,
    92,
    1117,
    822,
    258,
    1467,
]
MODEL_NAME = "IRESfinder-logreg-py3"
WILDCARD_TOKEN = "[TCGA]"

app = FastAPI(
    title="IRESfinder Service",
    description=(
        "Identify putative internal ribosome entry sites from FASTA input using "
        "a Python 3 reimplementation of the published IRESfinder pipeline."
    ),
    version="0.1.0",
)


class IRESfinderPredictRequest(BaseModel):
    fasta_content: str = Field(
        ...,
        min_length=1,
        description="FASTA content or plain sequence text to score with IRESfinder.",
    )
    mode: int = Field(
        default=0,
        ge=0,
        le=2,
        description="IRESfinder mode: 0=full sequence, 1=header-specified subsequence, 2=sliding window.",
    )
    window_size: int = Field(
        default=DEFAULT_WINDOW_SIZE,
        ge=20,
        le=5000,
        description="Sliding-window size used only in mode 2.",
    )
    step_size: int = Field(
        default=DEFAULT_STEP_SIZE,
        ge=1,
        le=5000,
        description="Sliding-window step size used only in mode 2.",
    )
    decision_threshold: float = Field(
        default=DEFAULT_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Probability threshold used to label a fragment as IRES/non-IRES.",
    )


class IRESfinderPredictionRow(BaseModel):
    fragment_id: str
    predicted_label: str
    score: float


class IRESfinderPredictResponse(BaseModel):
    mode: int
    window_size: int
    step_size: int
    decision_threshold: float
    fragment_count: int
    positive_count: int
    has_putative_ires: bool
    best_fragment_id: str
    max_score: float
    result_tsv_path: str
    model: str = MODEL_NAME
    predictions: List[IRESfinderPredictionRow]


@dataclass
class ModelArtifacts:
    scaler: StandardScaler
    active_column_indices: np.ndarray
    classifier: LogisticRegressionCV


_MODEL_CACHE: Optional[ModelArtifacts] = None
_CACHE_LOCK = Lock()
_KMER_PATTERNS: Optional[List[str]] = None


def _ensure_upstream_repo_available() -> None:
    if not IRESFINDER_ROOT.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "IRESfinder upstream repository is missing. Expected it at "
                f"`{IRESFINDER_ROOT}`. Clone it on the Linux server before starting this service."
            ),
        )
    if not IRESFINDER_TRAIN_DATA.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "IRESfinder training data is missing. Expected "
                f"`{IRESFINDER_TRAIN_DATA}` from the upstream repository."
            ),
        )


def _ensure_output_dir() -> Path:
    IRESFINDER_SERVICE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return IRESFINDER_SERVICE_OUTPUT_DIR


def _is_fasta_like(text: str) -> bool:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        return line.startswith(">")
    return False


def _normalize_sequence(raw_sequence: str) -> str:
    sequence = "".join(raw_sequence.split()).upper().replace("U", "T")
    if not sequence:
        raise HTTPException(status_code=400, detail="Encountered an empty sequence record.")
    invalid_chars = sorted(set(ch for ch in sequence if ch not in {"A", "C", "G", "T"}))
    if invalid_chars:
        raise HTTPException(
            status_code=400,
            detail=(
                "IRESfinder supports only A/C/G/T/U characters after normalization. "
                f"Unsupported characters: {''.join(invalid_chars)}"
            ),
        )
    return sequence


def _parse_fasta_content(fasta_content: str) -> List[Tuple[str, str]]:
    stripped = fasta_content.strip()
    if not stripped:
        raise HTTPException(status_code=400, detail="`fasta_content` is empty.")

    if not _is_fasta_like(stripped):
        return [("query", _normalize_sequence(stripped))]

    records: List[Tuple[str, str]] = []
    current_id: Optional[str] = None
    current_sequence_parts: List[str] = []
    for raw_line in stripped.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_id is not None:
                records.append((current_id, _normalize_sequence("".join(current_sequence_parts))))
            current_id = line[1:].strip() or f"record_{len(records) + 1}"
            current_sequence_parts = []
        else:
            current_sequence_parts.append(line)

    if current_id is not None:
        records.append((current_id, _normalize_sequence("".join(current_sequence_parts))))

    if not records:
        raise HTTPException(status_code=400, detail="No valid FASTA records were found.")
    return records


def _extract_mode1_bounds(record_id: str) -> Tuple[int, int]:
    fields = record_id.split()
    if len(fields) < 3:
        return 0, 0
    try:
        start = int(fields[-2])
        end = int(fields[-1])
    except ValueError:
        return 0, 0
    return start, end


def _preprocess_records(
    records: Sequence[Tuple[str, str]],
    mode: int,
    window_size: int,
    step_size: int,
) -> List[Tuple[str, str]]:
    prepared: List[Tuple[str, str]] = []
    for record_id, sequence in records:
        if mode == 2:
            sequence_length = len(sequence)
            if sequence_length <= window_size:
                prepared.append((record_id, sequence))
                continue
            start = 0
            while start + window_size < sequence_length:
                end = start + window_size
                prepared.append((f"{record_id}_{start + 1}_{end}", sequence[start:end]))
                start += step_size
            final_start = sequence_length - window_size
            prepared.append((f"{record_id}_{final_start + 1}_{sequence_length}", sequence[final_start:]))
            continue

        if mode == 1:
            start, end = _extract_mode1_bounds(record_id)
            normalized_id = "_".join(record_id.split())
            if start > 0 and end > start:
                zero_based_start = start - 1
                adjusted_end = min(end, len(sequence))
                prepared.append((normalized_id, sequence[zero_based_start:adjusted_end]))
            else:
                prepared.append((normalized_id, sequence))
            continue

        normalized_id = record_id.split()[0] if record_id.split() else record_id
        prepared.append((normalized_id, sequence))

    if not prepared:
        raise HTTPException(status_code=400, detail="No fragments were produced after preprocessing.")
    return prepared


def _build_kmer_patterns() -> List[str]:
    global _KMER_PATTERNS
    if _KMER_PATTERNS is not None:
        return _KMER_PATTERNS

    nucleotides = ["T", "C", "G", "A"]
    kmers: List[str] = list(nucleotides)
    mers: List[str] = list(nucleotides)
    nucleotide_plus_wildcard: List[str] = nucleotides + [WILDCARD_TOKEN]
    running_patterns: List[str] = list(nucleotide_plus_wildcard)

    tmp_patterns: List[str] = []
    for added_base in nucleotides:
        for existing_pattern in mers:
            tmp_patterns.append(existing_pattern + added_base)
    mers = tmp_patterns
    kmers.extend(mers)

    for _ in range(3, 6):
        for added_base in nucleotides:
            for middle_pattern in running_patterns:
                prefix = added_base + middle_pattern
                for terminal_base in nucleotides:
                    kmers.append(prefix + terminal_base)

        next_running_patterns: List[str] = []
        for left_pattern in running_patterns:
            for right_pattern in nucleotide_plus_wildcard:
                next_running_patterns.append(left_pattern + right_pattern)
        running_patterns = next_running_patterns

    _KMER_PATTERNS = kmers
    return _KMER_PATTERNS


def _infer_pattern_length(pattern_index: int) -> int:
    if 20 < pattern_index < 101:
        return 3
    if pattern_index < 501:
        return 4
    return 5


def _count_non_overlapping_kmer(sequence: str, pattern: str) -> int:
    """Count non-overlapping occurrences of *pattern* in *sequence*.

    This matches the original Perl ``calculate_features.pl`` behaviour:
    ``$num = ($str =~ s/$_/$_/g);`` performs a non-overlapping global
    substitution/count.
    """
    kmer_length = len(pattern)
    if len(sequence) < kmer_length:
        return 0
    count = 0
    i = 0
    while i <= len(sequence) - kmer_length:
        if sequence[i : i + kmer_length] == pattern:
            count += 1
            i += kmer_length
        else:
            i += 1
    return count


def _count_wildcard_kmer(sequence: str, regex_pattern: re.Pattern[str], kmer_length: int) -> int:
    if len(sequence) < kmer_length:
        return 0
    count = 0
    for start in range(0, len(sequence) - kmer_length + 1):
        if regex_pattern.fullmatch(sequence[start : start + kmer_length]):
            count += 1
    return count


def _calculate_feature_vector(sequence: str) -> List[float]:
    patterns = _build_kmer_patterns()
    feature_values: List[float] = []
    compiled_patterns: dict[str, re.Pattern[str]] = {}

    for pattern_index, pattern in enumerate(patterns, start=1):
        if WILDCARD_TOKEN not in pattern:
            kmer_length = len(pattern)
            count = _count_non_overlapping_kmer(sequence, pattern)
        else:
            kmer_length = _infer_pattern_length(pattern_index)
            regex_pattern = compiled_patterns.get(pattern)
            if regex_pattern is None:
                regex_pattern = re.compile(pattern)
                compiled_patterns[pattern] = regex_pattern
            count = _count_wildcard_kmer(sequence, regex_pattern, kmer_length)

        denominator = len(sequence) - kmer_length + 1
        feature_values.append(float(count) / float(denominator) if denominator > 0 else 0.0)

    return feature_values


def _load_model_artifacts() -> ModelArtifacts:
    global _MODEL_CACHE
    cached = _MODEL_CACHE
    if cached is not None:
        return cached

    with _CACHE_LOCK:
        cached = _MODEL_CACHE
        if cached is not None:
            return cached

        _ensure_upstream_repo_available()
        try:
            training_matrix = np.loadtxt(str(IRESFINDER_TRAIN_DATA))
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load IRESfinder training data from `{IRESFINDER_TRAIN_DATA}`: {exc}",
            ) from exc

        training_labels = training_matrix[:, 0]
        training_features = training_matrix[:, 1:]
        scaler = StandardScaler().fit(training_features)
        scaled_training_features = scaler.transform(training_features)
        active_column_indices = np.asarray(
            [
                idx
                for idx in range(scaled_training_features.shape[1])
                if float(np.mean(scaled_training_features[:, idx] > 0)) > 0.1
            ],
            dtype=int,
        )
        reduced_training_features = scaled_training_features[:, active_column_indices]
        classifier = LogisticRegressionCV(
            cv=3,
            solver="liblinear",
            max_iter=2000,
            random_state=0,
        ).fit(reduced_training_features[:, SELECTED_FEATURE_INDICES], training_labels)

        _MODEL_CACHE = ModelArtifacts(
            scaler=scaler,
            active_column_indices=active_column_indices,
            classifier=classifier,
        )
        return _MODEL_CACHE


def _score_fragments(fragments: Sequence[Tuple[str, str]], decision_threshold: float) -> List[Tuple[str, float, str]]:
    artifacts = _load_model_artifacts()
    feature_matrix = np.asarray([_calculate_feature_vector(sequence) for _, sequence in fragments], dtype=float)
    scaled_matrix = artifacts.scaler.transform(feature_matrix)
    reduced_matrix = scaled_matrix[:, artifacts.active_column_indices]
    selected_matrix = reduced_matrix[:, SELECTED_FEATURE_INDICES]
    probabilities = artifacts.classifier.predict_proba(selected_matrix)[:, 1]

    scored_rows: List[Tuple[str, float, str]] = []
    for (fragment_id, _), score in zip(fragments, probabilities):
        label = "IRES" if float(score) >= decision_threshold else "non-IRES"
        scored_rows.append((fragment_id, float(score), label))
    return scored_rows


def _write_result_tsv(scored_rows: Sequence[Tuple[str, float, str]]) -> str:
    output_dir = _ensure_output_dir()
    output_path = output_dir / f"iresfinder_result_{uuid4().hex[:10]}.tsv"
    lines = ["ID\tIndex\tScore"]
    for fragment_id, score, label in scored_rows:
        lines.append(f"{fragment_id}\t{label}\t{score}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(output_path)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "repo_exists": IRESFINDER_ROOT.exists(),
        "train_data_path": str(IRESFINDER_TRAIN_DATA),
        "train_data_exists": IRESFINDER_TRAIN_DATA.exists(),
        "service_output_dir": str(IRESFINDER_SERVICE_OUTPUT_DIR),
        "python_rebuild": True,
        "requires_python2": False,
    }


@app.post("/predict", response_model=IRESfinderPredictResponse)
def predict_ires(payload: IRESfinderPredictRequest) -> IRESfinderPredictResponse:
    if payload.mode == 2 and payload.step_size > payload.window_size:
        raise HTTPException(
            status_code=400,
            detail="`step_size` should not exceed `window_size` in sliding-window mode.",
        )

    parsed_records = _parse_fasta_content(payload.fasta_content)
    fragments = _preprocess_records(
        parsed_records,
        mode=payload.mode,
        window_size=payload.window_size,
        step_size=payload.step_size,
    )
    scored_rows = _score_fragments(fragments, decision_threshold=payload.decision_threshold)
    result_tsv_path = _write_result_tsv(scored_rows)
    best_fragment_id, max_score, _ = max(scored_rows, key=lambda item: item[1])
    positive_count = sum(1 for _, _, label in scored_rows if label == "IRES")

    return IRESfinderPredictResponse(
        mode=payload.mode,
        window_size=payload.window_size,
        step_size=payload.step_size,
        decision_threshold=payload.decision_threshold,
        fragment_count=len(scored_rows),
        positive_count=positive_count,
        has_putative_ires=positive_count > 0,
        best_fragment_id=best_fragment_id,
        max_score=float(max_score),
        result_tsv_path=result_tsv_path,
        predictions=[
            IRESfinderPredictionRow(
                fragment_id=fragment_id,
                predicted_label=label,
                score=float(score),
            )
            for fragment_id, score, label in scored_rows
        ],
    )
