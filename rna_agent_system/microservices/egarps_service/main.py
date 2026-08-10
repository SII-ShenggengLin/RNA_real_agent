"""EGARPS+ microservice for scoring RNA-protein complex structures.

INTERFACE LOCK (v0.1.0)
关联文件清单：
  - microservices/egarps_service/main.py  ← 本文件
  - agent_core/tools.py :: score_rna_protein_complex_with_egarps
  - agent_core/tool_specs.py :: EGARPSOutput / score_rna_protein_complex_with_egarps ToolSpec
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


APP_DIR = Path(__file__).resolve().parent
_RNA_AGENT_SYSTEM_ROOT = APP_DIR.parents[1]

_EGARPS_ROOT = (_RNA_AGENT_SYSTEM_ROOT / "external_repos" / "EGARPS").resolve()
_EGARPS_SCRIPTS = _EGARPS_ROOT / "scripts"
_EGARPS_PREDICT = _EGARPS_SCRIPTS / "predict.py"
_CONDA_ENV = "egarps_env"


app = FastAPI(
    title="EGARPS+ Service (Port 8023)",
    description="Score RNA-protein complex structures with EGARPS+.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


class EGARPSRequest(BaseModel):
    pdb_path: str = Field(..., description="Absolute path to the PDB file to score.")
    academic: bool = Field(
        default=False,
        description="If True, use full academic mode (requires DSSR and NACCESS licenses). "
                    "If False, use non-academic mode with reduced features.",
    )


class EGARPSResponse(BaseModel):
    complex_id: str
    native_probability: float
    model: str = "EGARPS+"
    academic: bool
    pdb_path: str


def _run_egarps(pdb_path: str, academic: bool) -> dict[str, Any]:
    """Run EGARPS+ predict.py and parse the result.

    WARNING (2026-07-27 campaign): `pdb_path` must be a REAL `.pdb` file.
    The EGARPS pipeline (external_repos/EGARPS/scripts/ins.py) derives its
    cache paths with `pdb.replace('.pdb', ...)`, so any input whose filename
    lacks '.pdb' (e.g. a Protenix .cif) is OVERWRITTEN by its own pickle
    caches; and its CIF reader rejects Protenix OP3 atoms. Its chain typing
    also keys on substrings of the basename — basenames containing 'protein'
    (e.g. 'proteinx') misroute RNA chains. See NOTEs in
    external_repos/EGARPS/scripts/{ins.py,feature_residue.py}.
    """
    pdb_path_obj = Path(pdb_path)
    if not pdb_path_obj.exists():
        raise FileNotFoundError(f"PDB file not found: {pdb_path}")

    work_dir = pdb_path_obj.parent
    result_file = work_dir / "result.txt"

    # Remove old result.txt if exists
    if result_file.exists():
        result_file.unlink()

    cmd = [
        "conda", "run", "-n", _CONDA_ENV,
        "python", str(_EGARPS_PREDICT),
    ]
    if not academic:
        cmd.append("-non-academic")
    cmd.append(str(pdb_path_obj))

    env = os.environ.copy()
    # Ensure CUDA is visible
    env["CUDA_VISIBLE_DEVICES"] = env.get("CUDA_VISIBLE_DEVICES", "0")

    process = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(work_dir),
        env=env,
        check=False,
    )

    # EGARPS prints success/failure to stdout; we inspect result.txt
    if not result_file.exists():
        raise RuntimeError(
            f"EGARPS did not produce result.txt. "
            f"returncode={process.returncode}; stdout={process.stdout.strip()}; stderr={process.stderr.strip()}"
        )

    with open(result_file, "r") as f:
        lines = f.readlines()

    if not lines:
        raise RuntimeError("EGARPS result.txt is empty.")

    # result.txt format: <complex_id>\t<native_probability>
    parts = lines[0].strip().split("\t")
    if len(parts) < 2:
        raise RuntimeError(f"Unexpected result.txt format: {lines[0].strip()}")

    complex_id = parts[0]
    try:
        native_probability = float(parts[1])
    except ValueError as exc:
        raise RuntimeError(f"Cannot parse native probability: {parts[1]}") from exc

    return {
        "complex_id": complex_id,
        "native_probability": native_probability,
        "academic": academic,
        "pdb_path": str(pdb_path_obj),
    }


@app.post("/score", response_model=EGARPSResponse)
async def score_complex(request: EGARPSRequest) -> EGARPSResponse:
    try:
        result = _run_egarps(request.pdb_path, request.academic)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")

    return EGARPSResponse(
        complex_id=result["complex_id"],
        native_probability=result["native_probability"],
        academic=result["academic"],
        pdb_path=result["pdb_path"],
    )
