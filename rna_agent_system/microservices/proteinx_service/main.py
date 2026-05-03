"""ProteinX (Protenix) microservice for protein tertiary structure prediction.

INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
- agent_core/tools.py :: ProteinXProteinInput / predict_protein_structure_with_proteinx
- agent_core/tool_specs.py :: ProteinXProteinOutput / ToolSpec
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_WORKDIR = PROJECT_ROOT / "workspace" / "proteinx_service_runs"
SERVICE_WORKDIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="ProteinX Service",
    description="Predict protein 3D structure from sequence using Protenix.",
    version="0.1.0",
)


def _resolve_host_path(raw: str) -> Path:
    """Resolve repo-relative or absolute paths as seen from the Linux server."""
    text = raw.strip().strip('"').strip("'")
    p = Path(text).expanduser()
    if p.is_absolute():
        return p.resolve()
    candidate = (PROJECT_ROOT / text).resolve()
    if candidate.exists():
        return candidate
    return Path(text).resolve()


def _fasta_to_sequences(filepath: str) -> List[Dict[str, Any]]:
    """Parse a FASTA file and return Protenix sequences list."""
    path = _resolve_host_path(filepath)
    if not path.is_file():
        raise ValueError(f"FASTA file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    sequences: List[Dict[str, Any]] = []
    current_header = ""
    current_seq = ""
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_seq:
                sequences.append(
                    {
                        "proteinChain": {
                            "count": 1,
                            "sequence": current_seq.upper(),
                            "modifications": [],
                        }
                    }
                )
            current_header = line[1:].strip().split()[0]
            current_seq = ""
        else:
            current_seq += re.sub(r"[^A-Za-z]", "", line)
    if current_seq:
        sequences.append(
            {
                "proteinChain": {
                    "count": 1,
                    "sequence": current_seq.upper(),
                    "modifications": [],
                }
            }
        )
    if not sequences:
        raise ValueError(f"No protein sequences found in {path}")
    return sequences


class ProteinXPredictRequest(BaseModel):
    """ProteinX prediction request schema.

    INTERFACE LOCK (v0.1.0): Locked schema.
    """

    sequence_filepath: str = Field(
        ...,
        description="Path to FASTA file containing protein sequence(s).",
    )
    num_models: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Number of inference samples to generate.",
    )
    num_recycles: int = Field(
        default=10,
        ge=1,
        le=12,
        description="Number of Pairformer cycles (ignored if use_default_params=true).",
    )
    stop_at_score: float = Field(
        default=100,
        ge=0,
        description="Early stopping threshold (not directly supported by Protenix; kept for interface compat).",
    )
    msa_mode: str = Field(
        default="none",
        description="MSA generation mode. 'none' disables MSA; 'protenix' enables Protenix MSA server.",
    )
    model_name: str = Field(
        default="protenix_base_default_v1.0.0",
        description="Protenix model name to use. Default is protenix_base_default_v1.0.0. protenix-v2 requires additional download permissions.",
    )
    use_default_params: bool = Field(
        default=True,
        description="Use recommended default params for the selected model.",
    )


class ProteinXPredictResponse(BaseModel):
    """ProteinX prediction response schema.

    INTERFACE LOCK (v0.1.0): Locked schema.
    """

    pdb_filepath: str = ""
    mean_pae: float = 0.0
    mean_plddt: float = 0.0
    ranking_confidence: float = 0.0
    model_scores: List[Dict[str, Any]] = Field(default_factory=list)
    model: str = "proteinx"
    note: str = ""


def _find_protenix_cli() -> str:
    """Locate the protenix CLI executable."""
    exe = shutil.which("protenix")
    if exe:
        return exe
    # Fallback: try to invoke via python module
    return "python3 -m runner.batch_inference"


def _parse_best_result(dump_dir: Path, sample_name: str) -> Dict[str, Any]:
    """Parse the best-ranked prediction from Protenix output directory."""
    predictions_dir = dump_dir / sample_name / "seed_101" / "predictions"
    if not predictions_dir.exists():
        # Try other seed dirs
        for seed_dir in (dump_dir / sample_name).iterdir():
            if seed_dir.is_dir() and seed_dir.name.startswith("seed_"):
                predictions_dir = seed_dir / "predictions"
                if predictions_dir.exists():
                    break

    if not predictions_dir.exists():
        raise FileNotFoundError(f"Predictions directory not found in {dump_dir}")

    # Best model is sample_0 (ranked by ranking_score)
    best_cif = predictions_dir / f"{sample_name}_sample_0.cif"
    best_conf = predictions_dir / f"{sample_name}_summary_confidence_sample_0.json"

    if not best_cif.exists():
        # Fallback: find any .cif file
        cif_files = sorted(predictions_dir.glob("*.cif"))
        if cif_files:
            best_cif = cif_files[0]
        else:
            raise FileNotFoundError(f"No CIF output found in {predictions_dir}")

    if not best_conf.exists():
        conf_files = sorted(predictions_dir.glob("*summary_confidence*.json"))
        if conf_files:
            best_conf = conf_files[0]
        else:
            best_conf = None

    result: Dict[str, Any] = {
        "pdb_filepath": str(best_cif),
        "mean_pae": 0.0,
        "mean_plddt": 0.0,
        "ranking_confidence": 0.0,
        "model_scores": [],
    }

    # Parse confidence for best model
    if best_conf and best_conf.exists():
        with open(best_conf, "r", encoding="utf-8") as f:
            conf = json.load(f)
        result["mean_plddt"] = float(conf.get("plddt", 0.0))
        result["ranking_confidence"] = float(conf.get("ranking_score", 0.0))

    # Collect scores for all samples
    if predictions_dir.exists():
        for conf_file in sorted(predictions_dir.glob("*summary_confidence_*.json")):
            with open(conf_file, "r", encoding="utf-8") as f:
                c = json.load(f)
            result["model_scores"].append(
                {
                    "plddt": float(c.get("plddt", 0.0)),
                    "ptm": float(c.get("ptm", 0.0)),
                    "iptm": float(c.get("iptm", 0.0)),
                    "ranking_score": float(c.get("ranking_score", 0.0)),
                    "gpde": float(c.get("gpde", 0.0)),
                    "has_clash": bool(c.get("has_clash", False)),
                }
            )

    return result


@app.post("/predict/protein", response_model=ProteinXPredictResponse)
async def predict_protein(request: ProteinXPredictRequest) -> ProteinXPredictResponse:
    """Run ProteinX protein structure prediction."""
    # Validate input file
    try:
        sequences = _fasta_to_sequences(request.sequence_filepath)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Build Protenix input JSON
    sample_name = "proteinx_pred"
    protenix_input = [
        {
            "name": sample_name,
            "covalent_bonds": [],
            "sequences": sequences,
        }
    ]

    run_dir = tempfile.mkdtemp(prefix="proteinx_run_", dir=SERVICE_WORKDIR)
    input_json_path = Path(run_dir) / "input.json"
    with open(input_json_path, "w", encoding="utf-8") as f:
        json.dump(protenix_input, f, indent=2)

    dump_dir = Path(run_dir) / "output"
    dump_dir.mkdir(parents=True, exist_ok=True)

    use_msa = request.msa_mode.lower() not in ("", "none", "false", "no")

    cmd = [
        "protenix",
        "pred",
        "-i", str(input_json_path),
        "-o", str(dump_dir),
        "-s", "101",
        "-n", request.model_name,
        "--use_msa", str(use_msa).lower(),
        "--use_default_params", str(request.use_default_params).lower(),
        "--sample", str(request.num_models),
    ]
    if not request.use_default_params:
        cmd.extend(["--cycle", str(request.num_recycles)])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Protenix CLI not found. Ensure protenix is installed: {exc}",
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Protenix inference timed out after 3600 seconds.",
        )

    if proc.returncode != 0:
        err_detail = proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr
        raise HTTPException(
            status_code=500,
            detail=f"Protenix inference failed (rc={proc.returncode}): {err_detail}",
        )

    try:
        result = _parse_best_result(dump_dir, sample_name)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Output parsing failed: {exc}. stderr: {proc.stderr[-1000:]}",
        )

    return ProteinXPredictResponse(
        pdb_filepath=result["pdb_filepath"],
        mean_pae=result["mean_pae"],
        mean_plddt=result["mean_plddt"],
        ranking_confidence=result["ranking_confidence"],
        model_scores=result["model_scores"],
        model=request.model_name,
        note="",
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    cli_ok = shutil.which("protenix") is not None
    return {
        "status": "ok" if cli_ok else "cli_missing",
        "service": "proteinx",
        "protenix_cli": "available" if cli_ok else "not_found",
    }
