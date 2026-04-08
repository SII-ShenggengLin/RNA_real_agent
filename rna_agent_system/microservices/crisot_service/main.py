"""CRISOT microservice for CRISPR off-target scoring, specificity, and optimization."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CRISOT_ROOT = PROJECT_ROOT / "external_repos" / "CRISOT"
CRISOT_MODELS_DIR = CRISOT_ROOT / "models"
CRISOT_SCRIPT_DIR = CRISOT_ROOT / "script"
CRISOT_SCORE_PARAM_PATH = CRISOT_MODELS_DIR / "crisot_score_param.pkl"
CRISOT_SERVICE_OUTPUT_DIR = PROJECT_ROOT / "workspace" / "crisot_service"
DEFAULT_DEVICE = "C"
DEFAULT_MISMATCHES = 6
DEFAULT_MODEL_NAME = "CRISOT-Score"

app = FastAPI(
    title="CRISOT Service",
    description="CRISPR-Cas9 off-target scoring and specificity analysis powered by CRISOT.",
    version="0.1.0",
)

_MODEL_CACHE: Dict[str, Any] = {}
_CACHE_LOCK = Lock()


def _ensure_pandas_append_compatibility() -> None:
    """Provide a pandas>=2 compatible replacement for deprecated DataFrame.append."""
    if hasattr(pd.DataFrame, "append"):
        return

    def _append_compat(
        self: pd.DataFrame,
        other: Any,
        ignore_index: bool = False,
        verify_integrity: bool = False,
        sort: bool = False,
    ) -> pd.DataFrame:
        if isinstance(other, pd.Series):
            other_df = other.to_frame().T
        elif isinstance(other, dict):
            other_df = pd.DataFrame([other])
        else:
            other_df = other
        return pd.concat(
            [self, other_df],
            ignore_index=ignore_index,
            verify_integrity=verify_integrity,
            sort=sort,
        )

    pd.DataFrame.append = _append_compat  # type: ignore[attr-defined]


_ensure_pandas_append_compatibility()


class CrisotScoreRequest(BaseModel):
    sgrna: str = Field(
        ...,
        description="sgRNA sequence, expected to be 23 nt including PAM.",
    )
    target_sequence: str = Field(
        ...,
        description="Target DNA sequence, expected to be 23 nt including PAM.",
    )


class CrisotScoreResponse(BaseModel):
    sgrna: str
    target_sequence: str
    crisot_score: float
    model: str = DEFAULT_MODEL_NAME


class CrisotSpecRequest(BaseModel):
    csv_path: str = Field(
        ...,
        description="CSV path containing sgRNA and off-target sequences.",
    )
    on_item: str = Field(
        default="On",
        description="CSV column name for sgRNA/on-target sequences.",
    )
    off_item: str = Field(
        default="Off",
        description="CSV column name for off-target sequences.",
    )


class CrisotSpecResponse(BaseModel):
    csv_path: str
    on_item: str
    off_item: str
    row_count: int
    crisot_spec: float
    scored_csv_path: str
    model: str = DEFAULT_MODEL_NAME


class CrisotOffSpecRequest(BaseModel):
    sgrna: str = Field(
        ...,
        description="sgRNA sequence, expected to be 23 nt including PAM.",
    )
    target_sequence: str = Field(
        ...,
        description="Target DNA sequence, expected to be 23 nt including PAM.",
    )
    genome_path: str = Field(
        ...,
        description="Reference genome FASTA path used by Cas-OFFinder.",
    )
    mismatches: int = Field(
        default=DEFAULT_MISMATCHES,
        ge=0,
        le=10,
        description="Mismatch tolerance passed to Cas-OFFinder.",
    )
    device: str = Field(
        default=DEFAULT_DEVICE,
        description="Cas-OFFinder device flag, for example `C` or `G0`.",
    )


class CrisotOffSpecResponse(BaseModel):
    sgrna: str
    target_sequence: str
    genome_path: str
    mismatches: int
    device: str
    off_target_count: int
    crisot_spec: float
    scored_csv_path: str
    cas_offinder_available: bool
    model: str = DEFAULT_MODEL_NAME


class CrisotOptimizeRequest(BaseModel):
    target_sequence: str = Field(
        ...,
        description="Target DNA sequence to optimize against, expected to be 23 nt including PAM.",
    )
    genome_path: str = Field(
        ...,
        description="Reference genome FASTA path used by Cas-OFFinder during optimization.",
    )
    threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum CRISOT-Score retained for mutated guides.",
    )
    mismatches: int = Field(
        default=DEFAULT_MISMATCHES,
        ge=0,
        le=10,
        description="Mismatch tolerance passed to Cas-OFFinder.",
    )
    device: str = Field(
        default=DEFAULT_DEVICE,
        description="Cas-OFFinder device flag, for example `C` or `G0`.",
    )


class CrisotOptimizeResponse(BaseModel):
    target_sequence: str
    genome_path: str
    threshold: float
    mismatches: int
    device: str
    optimization_csv_path: str
    optimized_available: bool
    best_sgrna: str
    best_mutation: str
    best_crisot_score: float
    best_crisot_spec: float
    best_delta_spec: float
    cas_offinder_available: bool
    model: str = "CRISOT-Opti"


def _normalize_crisot_sequence(raw_text: str, field_name: str) -> str:
    sequence_lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    sequence = "".join(sequence_lines).upper().replace("U", "T")
    sequence = "".join(ch for ch in sequence if ch.isalpha())
    if not sequence:
        raise HTTPException(status_code=400, detail=f"`{field_name}` is empty after normalization.")
    invalid_chars = sorted(set(ch for ch in sequence if ch not in {"A", "C", "G", "T", "N"}))
    if invalid_chars:
        raise HTTPException(
            status_code=400,
            detail=(
                f"`{field_name}` supports only A/C/G/T/U/N characters. "
                f"Unsupported characters: {''.join(invalid_chars)}"
            ),
        )
    if len(sequence) != 23:
        raise HTTPException(
            status_code=400,
            detail=f"`{field_name}` must be 23 nt long after normalization; got {len(sequence)}.",
        )
    return sequence


def _resolve_repo_relative_path(input_path: str) -> Path:
    path_obj = Path(input_path).expanduser()
    if path_obj.is_absolute():
        return path_obj.resolve()
    return (PROJECT_ROOT / path_obj).resolve()


def _ensure_upstream_repo_available() -> None:
    if not CRISOT_ROOT.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "CRISOT upstream repository is missing. Expected it at "
                f"`{CRISOT_ROOT}`. Make sure the submodule is initialized."
            ),
        )
    if not CRISOT_SCORE_PARAM_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "CRISOT score parameters are missing. Expected "
                f"`{CRISOT_SCORE_PARAM_PATH}` from the upstream repository."
            ),
        )


def _import_crisot_core() -> Tuple[Any, Any]:
    _ensure_upstream_repo_available()
    repo_path = str(CRISOT_ROOT)
    if repo_path not in sys.path:
        sys.path.insert(0, repo_path)
    try:
        from crisot_modules import CRISOT as CRISOTCore, load_pkl
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to import CRISOT core modules from `{CRISOT_ROOT}`: {exc}",
        ) from exc
    return CRISOTCore, load_pkl


def _load_model(ref_genome: str) -> Any:
    cached = _MODEL_CACHE.get(ref_genome)
    if cached is not None:
        return cached

    with _CACHE_LOCK:
        cached = _MODEL_CACHE.get(ref_genome)
        if cached is not None:
            return cached

        CRISOTCore, load_pkl = _import_crisot_core()
        try:
            paramread, a_b, bins, weights = load_pkl(str(CRISOT_SCORE_PARAM_PATH))
            model = CRISOTCore(
                param=paramread,
                ref_genome=ref_genome,
                a_b=a_b,
                bins=bins,
                prob_weight=weights,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize CRISOT runtime: {exc}",
            ) from exc

        _MODEL_CACHE[ref_genome] = model
        return model


def _default_ref_genome() -> str:
    return str((CRISOT_SCRIPT_DIR / "hg38.fa").resolve())


def _ensure_output_dir() -> Path:
    CRISOT_SERVICE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return CRISOT_SERVICE_OUTPUT_DIR


def _save_dataframe_artifact(dataframe: pd.DataFrame, prefix: str) -> str:
    output_dir = _ensure_output_dir()
    output_path = output_dir / f"{prefix}_{uuid4().hex[:10]}.csv"
    dataframe.to_csv(output_path, index=False)
    return str(output_path)


def _cas_offinder_available() -> bool:
    return shutil.which("cas-offinder") is not None


def _select_best_optimized_row(dataframe: pd.DataFrame) -> Optional[pd.Series]:
    if dataframe.empty:
        return None
    if "Mutation" not in dataframe.columns:
        return None
    candidate_rows = dataframe.loc[
        dataframe["Mutation"].astype(str).str.upper() != "WT"
    ]
    candidate_rows = candidate_rows.loc[
        ~candidate_rows["Mutation"].astype(str).str.contains("Optimization unavailable", na=False)
    ]
    if candidate_rows.empty:
        return None
    return candidate_rows.iloc[0]


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "repo_exists": CRISOT_ROOT.exists(),
        "score_param_path": str(CRISOT_SCORE_PARAM_PATH),
        "score_param_exists": CRISOT_SCORE_PARAM_PATH.exists(),
        "default_ref_genome": _default_ref_genome(),
        "default_ref_genome_exists": Path(_default_ref_genome()).exists(),
        "cas_offinder_available": _cas_offinder_available(),
        "service_output_dir": str(CRISOT_SERVICE_OUTPUT_DIR),
        "supports_optimize": True,
    }


@app.post("/score", response_model=CrisotScoreResponse)
def score_crisot(payload: CrisotScoreRequest) -> CrisotScoreResponse:
    sgrna = _normalize_crisot_sequence(payload.sgrna, "sgrna")
    target_sequence = _normalize_crisot_sequence(payload.target_sequence, "target_sequence")
    model = _load_model(_default_ref_genome())
    try:
        score = float(model.single_score_(sgrna, target_sequence))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CRISOT scoring failed: {exc}") from exc
    return CrisotScoreResponse(
        sgrna=sgrna,
        target_sequence=target_sequence,
        crisot_score=score,
    )


@app.post("/spec", response_model=CrisotSpecResponse)
def calculate_spec(payload: CrisotSpecRequest) -> CrisotSpecResponse:
    csv_path = _resolve_repo_relative_path(payload.csv_path)
    if not csv_path.exists():
        raise HTTPException(status_code=400, detail=f"CSV path does not exist: {csv_path}")
    try:
        dataframe = pd.read_csv(csv_path, header=0, index_col=None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {exc}") from exc
    required_columns = {payload.on_item, payload.off_item}
    missing_columns = required_columns - set(dataframe.columns)
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {sorted(missing_columns)}",
        )

    model = _load_model(_default_ref_genome())
    try:
        spec, scored_dataframe = model.spec(
            data_df=dataframe.copy(),
            On=payload.on_item,
            Off=payload.off_item,
            out_df=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CRISOT spec calculation failed: {exc}") from exc

    scored_csv_path = _save_dataframe_artifact(
        scored_dataframe,
        prefix=f"crisot_spec_{csv_path.stem}",
    )
    return CrisotSpecResponse(
        csv_path=str(csv_path),
        on_item=payload.on_item,
        off_item=payload.off_item,
        row_count=int(scored_dataframe.shape[0]),
        crisot_spec=float(spec),
        scored_csv_path=scored_csv_path,
    )


@app.post("/off-spec", response_model=CrisotOffSpecResponse)
def calculate_off_spec(payload: CrisotOffSpecRequest) -> CrisotOffSpecResponse:
    sgrna = _normalize_crisot_sequence(payload.sgrna, "sgrna")
    target_sequence = _normalize_crisot_sequence(payload.target_sequence, "target_sequence")
    genome_path = _resolve_repo_relative_path(payload.genome_path)
    if not genome_path.exists():
        raise HTTPException(status_code=400, detail=f"Genome path does not exist: {genome_path}")
    if not _cas_offinder_available():
        raise HTTPException(
            status_code=503,
            detail="`cas-offinder` is not available in PATH. It is required for CRISOT off-spec analysis.",
        )

    model = _load_model(str(genome_path))
    try:
        spec, scored_dataframe = model.CasoffinderSpec_(
            sgrna,
            target_sequence,
            out_df=True,
            mm=payload.mismatches,
            dev=payload.device,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CRISOT off-spec calculation failed: {exc}") from exc

    scored_csv_path = _save_dataframe_artifact(
        scored_dataframe,
        prefix=f"crisot_offspec_{target_sequence}",
    )
    off_target_count = max(int(scored_dataframe.shape[0]) - 1, 0)
    return CrisotOffSpecResponse(
        sgrna=sgrna,
        target_sequence=target_sequence,
        genome_path=str(genome_path),
        mismatches=payload.mismatches,
        device=payload.device,
        off_target_count=off_target_count,
        crisot_spec=float(spec),
        scored_csv_path=scored_csv_path,
        cas_offinder_available=True,
    )


@app.post("/optimize", response_model=CrisotOptimizeResponse)
def optimize_sgrna(payload: CrisotOptimizeRequest) -> CrisotOptimizeResponse:
    target_sequence = _normalize_crisot_sequence(payload.target_sequence, "target_sequence")
    genome_path = _resolve_repo_relative_path(payload.genome_path)
    if not genome_path.exists():
        raise HTTPException(status_code=400, detail=f"Genome path does not exist: {genome_path}")
    if not _cas_offinder_available():
        raise HTTPException(
            status_code=503,
            detail="`cas-offinder` is not available in PATH. It is required for CRISOT optimization.",
        )

    model = _load_model(str(genome_path))
    try:
        optimization_df = model.opti(
            target=target_sequence,
            threshold=payload.threshold,
            mm=payload.mismatches,
            dev=payload.device,
        )
    except TypeError:
        try:
            model.opti_th = payload.threshold
            optimization_df = model.opti(
                target=target_sequence,
                mm=payload.mismatches,
                dev=payload.device,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"CRISOT optimization failed: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CRISOT optimization failed: {exc}") from exc

    optimization_csv_path = _save_dataframe_artifact(
        optimization_df,
        prefix=f"crisot_optimize_{target_sequence}",
    )
    best_row = _select_best_optimized_row(optimization_df)
    optimized_available = best_row is not None
    return CrisotOptimizeResponse(
        target_sequence=target_sequence,
        genome_path=str(genome_path),
        threshold=payload.threshold,
        mismatches=payload.mismatches,
        device=payload.device,
        optimization_csv_path=optimization_csv_path,
        optimized_available=optimized_available,
        best_sgrna="" if best_row is None else str(best_row.get("sgRNA", "")),
        best_mutation="" if best_row is None else str(best_row.get("Mutation", "")),
        best_crisot_score=0.0 if best_row is None else float(best_row.get("CRISOT-Score", 0.0)),
        best_crisot_spec=0.0 if best_row is None else float(best_row.get("CRISOT-Spec", 0.0)),
        best_delta_spec=0.0 if best_row is None else float(best_row.get("delta_Spec", 0.0)),
        cas_offinder_available=True,
    )
