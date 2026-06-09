"""CRISOT microservice for CRISPR off-target scoring, specificity, optimization, and fingerprinting.

INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
关联文件清单（修改时必须全部同步）：
  - microservices/crisot_service/main.py  ← 本文件
  - agent_core/tools.py
  - agent_core/tool_specs.py
  - agent_core/state.py
  - cli/ entrypoints
  - docs/RNA_AGENT_SYSTEM_GUIDE.md
规则：任何字段增删、端点路径变更、Request/Response 模型变动、
      返回值结构调整，必须同时更新上述全部文件并重新跑通端到端测试。
      违反此规则的提交将被回退。
本次修改的基准日期：2026-04-24。
"""

from __future__ import annotations

import os
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
CRISOT_FALLBACK_MODELS_DIR = PROJECT_ROOT / "assets" / "crisot"
CRISOT_SCRIPT_DIR = CRISOT_ROOT / "script"
CRISOT_DATA_DIR = CRISOT_ROOT / "data"
CRISOT_SCORE_PARAM_PATH = CRISOT_MODELS_DIR / "crisot_score_param.pkl"
CRISOT_FP_ENCODING_PATH = CRISOT_MODELS_DIR / "crisot_fingerprint_encoding.pkl"
CRISOT_SERVICE_OUTPUT_DIR = PROJECT_ROOT / "workspace" / "crisot_service"


def _resolve_xgb_model_path(model_name: str) -> Path:
    """Resolve XGBoost model path, preferring CRISOT submodule dir then fallback assets dir."""
    if model_name == "Circle-seq":
        filename = "circleseq_xgb_models.pkl"
    elif model_name == "Site-seq":
        filename = "siteseq_xgb_models.pkl"
    elif model_name == "Change-seq":
        filename = "changeseq_xgb_models.pkl"
    else:
        raise ValueError(f"Unsupported xgb_model: {model_name}")
    primary = CRISOT_MODELS_DIR / filename
    if primary.exists():
        return primary
    fallback = CRISOT_FALLBACK_MODELS_DIR / filename
    if fallback.exists():
        return fallback
    return primary
DEFAULT_DEVICE = "G0"
DEFAULT_MISMATCHES = 6
DEFAULT_MODEL_NAME = "CRISOT-Score"
DEFAULT_REF_GENOME_ENV_VAR = "CRISOT_DEFAULT_REF_GENOME"

app = FastAPI(
    title="CRISOT Service",
    description="CRISPR-Cas9 off-target scoring, specificity analysis, and sgRNA optimization powered by CRISOT.",
    version="0.2.0",
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


# ═══════════════════════════════════════════════════════════════════════════════
# Request / Response models
# ═══════════════════════════════════════════════════════════════════════════════

class CrisotScoreRequest(BaseModel):
    sgrna: str = Field(
        ...,
        description="sgRNA sequence, expected to be 23 nt including PAM.",
    )
    target_sequence: str = Field(
        ...,
        description="Target DNA sequence, expected to be 23 nt including PAM.",
    )
    ref_genome: Optional[str] = Field(
        default=None,
        description="Optional reference genome path (affects model cache key only for score).",
    )


class CrisotScoreResponse(BaseModel):
    sgrna: str
    target_sequence: str
    crisot_score: float
    model: str = DEFAULT_MODEL_NAME


class CrisotScoresRequest(BaseModel):
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


class CrisotScoresResponse(BaseModel):
    csv_path: str
    on_item: str
    off_item: str
    row_count: int
    scored_csv_path: str
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


class CrisotRescoreRequest(BaseModel):
    txt_path: str = Field(
        ...,
        description="TXT file containing one sgRNA sequence per line.",
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


class CrisotRescoreResponse(BaseModel):
    txt_path: str
    genome_path: str
    mismatches: int
    device: str
    sgrna_count: int
    rescore_csv_path: str
    cas_offinder_available: bool
    model: str = "CRISOT-Rescore"


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


class CrisotFpRequest(BaseModel):
    csv_path: str = Field(
        ...,
        description="CSV path containing sgRNA and off-target sequences.",
    )
    xgb_model: str = Field(
        default="Circle-seq",
        description="XGBoost model name: Circle-seq, Site-seq, or Change-seq.",
    )
    on_item: str = Field(
        default="On",
        description="CSV column name for sgRNA/on-target sequences.",
    )
    off_item: str = Field(
        default="Off",
        description="CSV column name for off-target sequences.",
    )


class CrisotFpResponse(BaseModel):
    csv_path: str
    xgb_model: str
    on_item: str
    off_item: str
    row_count: int
    fp_csv_path: str
    model: str = "CRISOT-FP"


class CrisotGenFpRequest(BaseModel):
    sgrna: str = Field(
        ...,
        description="sgRNA sequence, expected to be 23 nt including PAM.",
    )
    target_sequence: str = Field(
        ...,
        description="Target DNA sequence, expected to be 23 nt including PAM.",
    )


class CrisotGenFpResponse(BaseModel):
    sgrna: str
    target_sequence: str
    fp_csv_path: str
    model: str = "CRISOT-FP-Encoding"


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

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
    override_path = os.getenv(DEFAULT_REF_GENOME_ENV_VAR, "").strip()
    if override_path:
        return str(_resolve_repo_relative_path(override_path))
    hg38_path = CRISOT_SCRIPT_DIR / "hg38.fa"
    if hg38_path.exists():
        return str(hg38_path.resolve())
    test_genome_path = CRISOT_DATA_DIR / "test_genome.fa"
    if test_genome_path.exists():
        return str(test_genome_path.resolve())
    return str(hg38_path.resolve())


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


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health() -> Dict[str, Any]:
    score_param_exists = CRISOT_SCORE_PARAM_PATH.exists()
    fp_encoding_exists = CRISOT_FP_ENCODING_PATH.exists()
    default_ref_genome = Path(_default_ref_genome())
    default_ref_genome_exists = default_ref_genome.exists()
    repo_exists = CRISOT_ROOT.exists()
    missing_requirements = []
    warnings = []
    if not repo_exists:
        missing_requirements.append(f"missing_repo:{CRISOT_ROOT}")
    if not score_param_exists:
        missing_requirements.append(f"missing_score_param:{CRISOT_SCORE_PARAM_PATH}")
    if not fp_encoding_exists:
        warnings.append(f"missing_fp_encoding:{CRISOT_FP_ENCODING_PATH}")
    if not default_ref_genome_exists:
        warnings.append(f"missing_default_ref_genome:{default_ref_genome}")
    status = "ok" if not missing_requirements else "degraded"

    return {
        "status": status,
        "repo_exists": repo_exists,
        "score_param_path": str(CRISOT_SCORE_PARAM_PATH),
        "score_param_exists": score_param_exists,
        "fp_encoding_path": str(CRISOT_FP_ENCODING_PATH),
        "fp_encoding_exists": fp_encoding_exists,
        "default_ref_genome_env_var": DEFAULT_REF_GENOME_ENV_VAR,
        "default_ref_genome_env_value": os.getenv(DEFAULT_REF_GENOME_ENV_VAR, ""),
        "default_ref_genome": str(default_ref_genome),
        "default_ref_genome_exists": default_ref_genome_exists,
        "cas_offinder_available": _cas_offinder_available(),
        "missing_requirements": missing_requirements,
        "warnings": warnings,
        "service_output_dir": str(CRISOT_SERVICE_OUTPUT_DIR),
        "supports_optimize": True,
        "supports_rescore": True,
        "supports_crisot_fp": True,
        "supports_gen_fp": True,
    }


@app.post("/score", response_model=CrisotScoreResponse)
def score_crisot(payload: CrisotScoreRequest) -> CrisotScoreResponse:
    sgrna = _normalize_crisot_sequence(payload.sgrna, "sgrna")
    target_sequence = _normalize_crisot_sequence(payload.target_sequence, "target_sequence")
    ref_genome = _default_ref_genome()
    if payload.ref_genome:
        ref_genome = str(_resolve_repo_relative_path(payload.ref_genome))
    model = _load_model(ref_genome)
    try:
        score = float(model.single_score_(sgrna, target_sequence))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CRISOT scoring failed: {exc}") from exc
    return CrisotScoreResponse(
        sgrna=sgrna,
        target_sequence=target_sequence,
        crisot_score=score,
    )


@app.post("/scores", response_model=CrisotScoresResponse)
def scores_crisot(payload: CrisotScoresRequest) -> CrisotScoresResponse:
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
        scores = model.score(data_df=dataframe.copy(), On=payload.on_item, Off=payload.off_item)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CRISOT batch scoring failed: {exc}") from exc

    dataframe["CRISOT-Score"] = scores
    scored_csv_path = _save_dataframe_artifact(
        dataframe,
        prefix=f"crisot_scores_{csv_path.stem}",
    )
    return CrisotScoresResponse(
        csv_path=str(csv_path),
        on_item=payload.on_item,
        off_item=payload.off_item,
        row_count=int(dataframe.shape[0]),
        scored_csv_path=scored_csv_path,
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


@app.post("/rescore", response_model=CrisotRescoreResponse)
def rescore_sgrnas(payload: CrisotRescoreRequest) -> CrisotRescoreResponse:
    txt_path = _resolve_repo_relative_path(payload.txt_path)
    if not txt_path.exists():
        raise HTTPException(status_code=400, detail=f"TXT path does not exist: {txt_path}")
    genome_path = _resolve_repo_relative_path(payload.genome_path)
    if not genome_path.exists():
        raise HTTPException(status_code=400, detail=f"Genome path does not exist: {genome_path}")
    if not _cas_offinder_available():
        raise HTTPException(
            status_code=503,
            detail="`cas-offinder` is not available in PATH. It is required for CRISOT rescore.",
        )

    try:
        df_txt = pd.read_csv(txt_path, header=None, index_col=None)
        targets = df_txt.iloc[:, 0].values.tolist()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read TXT: {exc}") from exc

    model = _load_model(str(genome_path))
    try:
        rescore_df = model.rescore(
            targets=targets,
            mm=payload.mismatches,
            dev=payload.device,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CRISOT rescore failed: {exc}") from exc

    rescore_csv_path = _save_dataframe_artifact(
        rescore_df,
        prefix=f"crisot_rescore_{txt_path.stem}",
    )
    return CrisotRescoreResponse(
        txt_path=str(txt_path),
        genome_path=str(genome_path),
        mismatches=payload.mismatches,
        device=payload.device,
        sgrna_count=len(targets),
        rescore_csv_path=rescore_csv_path,
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
    model.opti_th = payload.threshold
    try:
        optimization_df = model.opti(
            target=target_sequence,
            mm=payload.mismatches,
            dev=payload.device,
        )
    except Exception as exc:
        # Gracefully handle empty off-target search results (e.g. Cas-OFFinder finds no matches)
        if "No columns to parse from file" in str(exc):
            optimization_df = pd.DataFrame()
        else:
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


@app.post("/crisot-fp", response_model=CrisotFpResponse)
def crisot_fp(payload: CrisotFpRequest) -> CrisotFpResponse:
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

    xgb_model = payload.xgb_model
    try:
        model_path = _resolve_xgb_model_path(xgb_model)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"xgb_model must be one of Circle-seq, Site-seq, Change-seq; got {xgb_model}",
        ) from exc
    if not model_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"XGBoost model file missing: {model_path}. Please ensure trained_models.zip is unzipped or models are placed under {CRISOT_FALLBACK_MODELS_DIR}.",
        )

    _ensure_upstream_repo_available()
    repo_path = str(CRISOT_ROOT)
    if repo_path not in sys.path:
        sys.path.insert(0, repo_path)
    try:
        from utils import CRISOT_FP
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to import CRISOT-FP utils: {exc}") from exc

    try:
        dataframe["CRISOT_FP"] = CRISOT_FP(
            model_path=str(model_path),
            dataread=dataframe.copy(),
            On=payload.on_item,
            Off=payload.off_item,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CRISOT-FP prediction failed: {exc}") from exc

    fp_csv_path = _save_dataframe_artifact(
        dataframe,
        prefix=f"crisot_fp_{csv_path.stem}",
    )
    return CrisotFpResponse(
        csv_path=str(csv_path),
        xgb_model=xgb_model,
        on_item=payload.on_item,
        off_item=payload.off_item,
        row_count=int(dataframe.shape[0]),
        fp_csv_path=fp_csv_path,
    )


@app.post("/gen-fp", response_model=CrisotGenFpResponse)
def gen_fp(payload: CrisotGenFpRequest) -> CrisotGenFpResponse:
    sgrna = _normalize_crisot_sequence(payload.sgrna, "sgrna")
    target_sequence = _normalize_crisot_sequence(payload.target_sequence, "target_sequence")

    _ensure_upstream_repo_available()
    repo_path = str(CRISOT_ROOT)
    if repo_path not in sys.path:
        sys.path.insert(0, repo_path)
    try:
        from utils import FP_Encode_df
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to import CRISOT-FP utils: {exc}") from exc

    try:
        fp_df = FP_Encode_df(sgrna, target_sequence)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CRISOT-FP encoding failed: {exc}") from exc

    fp_csv_path = _save_dataframe_artifact(
        fp_df,
        prefix=f"crisot_genfp_{sgrna[:10]}_{target_sequence[:10]}",
    )
    return CrisotGenFpResponse(
        sgrna=sgrna,
        target_sequence=target_sequence,
        fp_csv_path=fp_csv_path,
    )
