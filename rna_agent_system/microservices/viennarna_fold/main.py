"""ViennaRNA RNAfold microservice."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    import RNA  # type: ignore

    _HAS_RNALIB = True
except ImportError:
    RNA = None  # type: ignore
    _HAS_RNALIB = False


_RNAFOLD_EXE = shutil.which("RNAfold")
_STRUCTURE_LINE = re.compile(
    r"^([.()[\]{}<>]+)\s+\(\s*(-?\d+(?:\.\d+)?)\s*\)\s*$"
)


def _fold_with_rnafold_cli(sequence: str) -> Tuple[str, float]:
    """Fold using the ``RNAfold`` executable (no Python RNAlib required)."""
    if not _RNAFOLD_EXE:
        raise RuntimeError("`RNAfold` executable not found in PATH.")

    proc = subprocess.run(
        [_RNAFOLD_EXE, "--noPS"],
        input=sequence + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"RNAfold failed (exit {proc.returncode}): {err}")

    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    for line in reversed(lines):
        if line.startswith(">"):
            continue
        m = _STRUCTURE_LINE.match(line)
        if m:
            return m.group(1), float(m.group(2))

    raise RuntimeError(
        "Could not parse RNAfold output; expected a line like "
        "'((((....))))) (-6.50)'."
    )


def _fold_sequence(sequence: str) -> Tuple[str, float, str]:
    """Return (structure, mfe, backend_label)."""
    if _HAS_RNALIB:
        fc = RNA.fold_compound(sequence)
        structure, mfe = fc.mfe()
        return str(structure), float(mfe), "RNAlib"
    structure, mfe = _fold_with_rnafold_cli(sequence)
    return structure, mfe, "RNAfold-cli"


app = FastAPI(
    title="ViennaRNA Fold Service (Port 8003 Deployment)",
    description=(
        "Predict RNA secondary structure and MFE using ViennaRNA. "
        "Uses Python RNAlib when available, otherwise the RNAfold CLI. "
        "Standard deployment port: 8003."
    ),
    version="0.1.2-port8003",
)


class FoldRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence (A/U/G/C).")


class FoldResponse(BaseModel):
    sequence: str
    structure: str
    mfe: float
    model: str = "ViennaRNA-RNAfold"
    backend: str = Field(
        ...,
        description="RNAlib (conda/pip Python module) or RNAfold-cli (standalone binary).",
    )


@app.get("/health")
def health() -> dict[str, Any]:
    ok = _HAS_RNALIB or bool(_RNAFOLD_EXE)
    return {
        "status": "ok" if ok else "degraded",
        "rnalib": _HAS_RNALIB,
        "rnafold_cli": bool(_RNAFOLD_EXE),
    }


@app.post("/fold", response_model=FoldResponse)
def fold(payload: FoldRequest) -> FoldResponse:
    sequence = payload.sequence.strip().upper().replace("T", "U")
    if not _HAS_RNALIB and not _RNAFOLD_EXE:
        raise HTTPException(
            status_code=503,
            detail=(
                "ViennaRNA is not available: install the `viennarna` conda package "
                "(recommended) or ensure `RNAfold` is on PATH. "
                "See rna_agent_system/microservices/viennarna_fold/environment.yml "
                "and optional build_from_submodule_linux.sh on the server."
            ),
        )
    try:
        structure, mfe, backend = _fold_sequence(sequence)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface unexpected fold errors
        raise HTTPException(status_code=503, detail=f"Fold failed: {exc}") from exc

    return FoldResponse(
        sequence=sequence,
        structure=structure,
        mfe=mfe,
        backend=backend,
    )
