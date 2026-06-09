"""Evitar microservice wrapper for siRNA/Cas13 design.

INTERFACE LOCK (v0.2.0): This microservice's request/response schemas are the
canonical contract. Any addition/removal must be synchronized with:
- agent_core/tools.py :: EvitarDesignInput / design_sirna_with_evitar
- agent_core/tool_specs.py :: EvitarDesignOutput / design_sirna_with_evitar ToolSpec
- agent_core/state.py :: evitar_* fields
- docs/tools/design_sirna_with_evitar.md

Deployment notes:
    - CRISPR mode (--predict CRISPR) requires R (>=3.4) runtime on server.
    - Off-target analysis requires user-provided transcriptome / 3'UTR FASTA.
    - Tissue-specific weights are available under Evitar/GenomeData/weightedgene/.
"""

from __future__ import annotations

import csv
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


APP_DIR = Path(__file__).resolve().parent
_RNA_AGENT_SYSTEM_ROOT = APP_DIR.parents[1]
_DEFAULT_EVITAR_ROOT = (_RNA_AGENT_SYSTEM_ROOT / "external_repos" / "Evitar").resolve()
_SERVICE_OUTPUT_DIR = (_RNA_AGENT_SYSTEM_ROOT / "workspace" / "evitar_service").resolve()
_EVITAR_REQUIRED_BINARIES = (
    "RNAplfold",
    "RNAfold",
    "RNAduplex",
    "muscle3.8.31_i86linux64",
)


def _resolve_evitar_root() -> Path:
    override = os.environ.get("EVITAR_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _DEFAULT_EVITAR_ROOT


def _resolve_repo_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    as_repo_relative = (_RNA_AGENT_SYSTEM_ROOT / candidate).resolve()
    if as_repo_relative.exists():
        return as_repo_relative
    return candidate.resolve()


def _normalize_output_filename(raw_filename: str) -> str:
    basename = Path(raw_filename).name.strip()
    if not basename:
        raise HTTPException(status_code=400, detail="`output_filename` cannot be empty.")
    if not basename.endswith(".txt"):
        basename = f"{basename}.txt"
    return basename


def _collect_runtime_health(evitar_root: Path) -> dict[str, Any]:
    evitar_script = evitar_root / "Evitar.pl"
    perl_path = shutil.which("perl")
    system_name = platform.system()

    binaries: dict[str, dict[str, Any]] = {}
    for binary_name in _EVITAR_REQUIRED_BINARIES:
        binary_path = evitar_root / "bin" / binary_name
        binaries[binary_name] = {
            "path": str(binary_path),
            "exists": binary_path.exists(),
            "executable": os.access(binary_path, os.X_OK),
        }

    script_exists = evitar_script.exists()
    binaries_ready = all(item["exists"] and item["executable"] for item in binaries.values())
    linux_runtime = system_name == "Linux"
    status = "ok" if script_exists and perl_path and binaries_ready and linux_runtime else "degraded"
    return {
        "status": status,
        "system": system_name,
        "linux_runtime": linux_runtime,
        "perl_path": perl_path,
        "evitar_script": str(evitar_script),
        "evitar_script_exists": script_exists,
        "binaries": binaries,
        "workspace_output_dir": str(_SERVICE_OUTPUT_DIR),
    }


def _looks_like_runtime_failure(stderr_text: str) -> bool:
    lowered = stderr_text.lower()
    failure_markers = (
        "cannot execute binary file",
        "exec format error",
        "command not found",
        "no such file or directory",
    )
    return any(marker in lowered for marker in failure_markers)


def _parse_output_summary(output_path: Path) -> tuple[int, list[dict[str, str]]]:
    if not output_path.exists():
        return 0, []
    try:
        with output_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            rows: list[dict[str, str]] = []
            for idx, row in enumerate(reader):
                if idx < 10:
                    rows.append({str(k): str(v) for k, v in row.items()})
            return idx + 1 if "idx" in locals() else 0, rows
    except Exception:
        # Evitar output may vary by mode and environment; keep service robust.
        return 0, []


app = FastAPI(
    title="Evitar Service",
    description="Wrap Evitar Perl CLI for future/existing virus siRNA or Cas13 guide design.",
    version="0.1.0",
)


class EvitarDesignRequest(BaseModel):
    input_path: str = Field(..., description="Input FASTA path (repo-relative or absolute).")
    mode: Optional[str] = Field(
        default=None,
        description="Evitar mode. Use `predesign` for future-virus predesign; omit for existing-virus mode.",
    )
    output_filename: Optional[str] = Field(
        default=None,
        description="Optional output filename; defaults to an auto-generated .txt in workspace/evitar_service.",
    )
    predict: Optional[str] = Field(
        default=None,
        description="`predsi`, `rnaxs`, or `CRISPR`.",
    )
    strains_path: Optional[str] = Field(
        default=None,
        description="Required for existing-virus mode (repo-relative or absolute).",
    )
    ncores: int = Field(default=1, ge=1, le=128)
    off_target: bool = Field(default=False, description="Enable Evitar off-target analysis.")
    p3utr_path: Optional[str] = Field(default=None)
    transcriptome_path: Optional[str] = Field(default=None)
    weight_path: Optional[str] = Field(default=None)
    limitnum: Optional[int] = Field(default=None, ge=1)
    repeatnum: Optional[int] = Field(default=None, ge=1)
    sumtype: Optional[str] = Field(default=None, description="`SGAR` or `greedy`.")
    pmcuff: Optional[int] = Field(default=None, ge=0)
    umcuff: Optional[float] = Field(default=None, ge=0.0)
    mircuff: Optional[float] = Field(default=None, ge=0.0)
    maxgc: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    mingc: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    middlegc: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    allow_path: Optional[str] = Field(
        default=None,
        description="Text file with one allowed siRNA per line (no header).",
    )
    ban_path: Optional[str] = Field(
        default=None,
        description="Text file with one banned siRNA per line (no header).",
    )


class EvitarDesignResponse(BaseModel):
    mode: str
    predict: str
    input_path: str
    output_path: str
    result_count: int
    top_results: list[dict[str, str]]
    command: str
    stdout: str
    stderr: str
    model: str = "Evitar"


@app.get("/health")
def health() -> dict[str, Any]:
    evitar_root = _resolve_evitar_root()
    health_payload = _collect_runtime_health(evitar_root)
    health_payload["evitar_root"] = str(evitar_root)
    return health_payload


@app.post("/design", response_model=EvitarDesignResponse)
def design_with_evitar(payload: EvitarDesignRequest) -> EvitarDesignResponse:
    evitar_root = _resolve_evitar_root()
    evitar_script = evitar_root / "Evitar.pl"
    if not evitar_script.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "Evitar.pl not found. Expected upstream repo at "
                f"`{evitar_root}`. On Linux server, clone official Evitar and/or set EVITAR_ROOT."
            ),
        )

    input_path = _resolve_repo_path(payload.input_path)
    if not input_path.exists():
        raise HTTPException(status_code=400, detail=f"Input FASTA not found: {input_path}")

    mode = (payload.mode or "").strip().lower() or "existing"
    if mode not in {"existing", "predesign"}:
        raise HTTPException(status_code=400, detail="`mode` must be `predesign` or omitted/`existing`.")

    predict = (payload.predict or "predsi").strip()
    if predict not in {"predsi", "rnaxs", "CRISPR", "multifapredsi"}:
        raise HTTPException(status_code=400, detail="`predict` must be one of: predsi, rnaxs, CRISPR, multifapredsi.")

    _SERVICE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if payload.output_filename:
        safe_filename = _normalize_output_filename(payload.output_filename)
        output_path = (_SERVICE_OUTPUT_DIR / safe_filename).resolve()
    else:
        output_path = (_SERVICE_OUTPUT_DIR / f"evitar_{uuid4().hex[:12]}.txt").resolve()

    # Isolated temp dir per request to prevent concurrent writes to the
    # default .temptempsi/ directory (Evitar off-target race condition).
    # NOTE: Evitar sub-scripts reject absolute paths for --temp, so we use a
    # relative path from the Evitar root directory.
    temp_name = f".temp_{uuid4().hex[:12]}"
    request_temp = evitar_root / temp_name
    request_temp.mkdir(parents=True, exist_ok=True)

    cmd = ["perl", str(evitar_script), "--input", str(input_path), "--output", str(output_path)]
    cmd.extend(["--temp", temp_name])
    if mode == "predesign":
        cmd.extend(["--mode", "predesign"])
    else:
        # existing-virus mode: strains_path is optional for single-virus design,
        # but required if user wants cross-strain coverage.
        if payload.strains_path:
            strains_path = _resolve_repo_path(payload.strains_path)
            if not strains_path.exists():
                raise HTTPException(status_code=400, detail=f"Strains FASTA not found: {strains_path}")
            cmd.extend(["--strains", str(strains_path)])

    cmd.extend(["--predict", predict, "--ncores", str(payload.ncores)])
    if payload.off_target:
        cmd.append("--offtarget")

    optional_pairs = [
        ("--p3utr", payload.p3utr_path),
        ("--transcriptome", payload.transcriptome_path),
        ("--weight", payload.weight_path),
        ("--sumtype", payload.sumtype),
    ]
    for flag, value in optional_pairs:
        if value:
            resolved = _resolve_repo_path(value) if flag in {"--p3utr", "--transcriptome", "--weight"} else value
            cmd.extend([flag, str(resolved)])

    numeric_pairs = [
        ("--limitnum", payload.limitnum),
        ("--repeatnum", payload.repeatnum),
        ("--pmcuff", payload.pmcuff),
        ("--umcuff", payload.umcuff),
        ("--mircuff", payload.mircuff),
        ("--maxgc", payload.maxgc),
        ("--mingc", payload.mingc),
        ("--middlegc", payload.middlegc),
    ]
    for flag, value in numeric_pairs:
        if value is not None:
            cmd.extend([flag, str(value)])

    list_file_pairs = [
        ("--allow", payload.allow_path),
        ("--ban", payload.ban_path),
    ]
    for flag, value in list_file_pairs:
        if value:
            resolved = _resolve_repo_path(value)
            if not resolved.exists():
                raise HTTPException(status_code=400, detail=f"List file not found for {flag}: {resolved}")
            cmd.extend([flag, str(resolved)])

    try:
        process = subprocess.run(
            cmd,
            cwd=str(evitar_root),
            text=True,
            capture_output=True,
            check=False,
        )
        if process.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Evitar execution failed; "
                    f"returncode={process.returncode}; stderr={process.stderr.strip()}"
                ),
            )
        if _looks_like_runtime_failure(process.stderr):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Evitar runtime failed even though command exited with code 0. "
                    "This is usually caused by non-Linux runtime or incompatible Evitar `bin/` executables. "
                    f"stderr={process.stderr.strip()}"
                ),
            )

        result_count, top_results = _parse_output_summary(output_path)
        return EvitarDesignResponse(
            mode=mode,
            predict=predict,
            input_path=str(input_path),
            output_path=str(output_path),
            result_count=result_count,
            top_results=top_results,
            command=" ".join(cmd),
            stdout=process.stdout,
            stderr=process.stderr,
        )
    finally:
        # Always clean up the per-request temp directory.
        if request_temp.exists():
            shutil.rmtree(str(request_temp), ignore_errors=True)
