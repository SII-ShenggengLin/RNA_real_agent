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


