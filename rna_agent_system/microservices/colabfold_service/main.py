"""ColabFold microservice for protein tertiary structure prediction.

This is a framework implementation. The full ColabFold stack requires:
  - CUDA-capable GPU
  - JAX with CUDA support
  - AlphaFold2 parameters (~3-5 GB download)
  - MMseqs2 for MSA generation

Until those dependencies are satisfied, the endpoints return 501 Not Implemented.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_WORKDIR = PROJECT_ROOT / "workspace" / "colabfold_service_runs"

app = FastAPI(
    title="ColabFold Service",
    description=(
        "Predict protein 3D structure from sequence using ColabFold (AlphaFold2 + MMseqs2). "
        "Framework mode: full deployment requires GPU + JAX + AlphaFold weights."
    ),
    version="0.1.0",
)


class ColabFoldPredictRequest(BaseModel):
    """ColabFold prediction request schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: ColabFoldProteinInput / predict_protein_structure_with_colabfold
    - agent_core/tool_specs.py :: ColabFoldProteinOutput / ToolSpec
    """

    sequence_filepath: str = Field(
        ...,
        description="Path to FASTA file containing protein sequence(s).",
    )
    num_models: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Number of AlphaFold2 models to use.",
    )
    num_recycles: int = Field(
        default=3,
        ge=1,
        le=12,
        description="Number of recycling iterations.",
    )
    stop_at_score: float = Field(
        default=100,
        ge=0,
        description="Early stopping threshold (pLDDT).",
    )
    msa_mode: str = Field(
        default="mmseqs2_uniref_env",
        description="MSA generation mode.",
    )


class ColabFoldPredictResponse(BaseModel):
    """ColabFold prediction response schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: predict_protein_structure_with_colabfold (wrapper return dict)
    - agent_core/tool_specs.py :: ColabFoldProteinOutput
    """

    pdb_filepath: str = ""
    mean_pae: float = 0.0
    mean_plddt: float = 0.0
    ranking_confidence: float = 0.0
    model_scores: List[Dict[str, Any]] = Field(default_factory=list)
    model: str = "colabfold"
    note: str = ""


@app.post("/predict/protein", response_model=ColabFoldPredictResponse)
async def predict_protein(request: ColabFoldPredictRequest) -> ColabFoldPredictResponse:
    """Run ColabFold protein structure prediction."""
    raise HTTPException(
        status_code=501,
        detail="ColabFold microservice is not yet fully deployed. "
               "Install JAX + ColabFold + AlphaFold weights to enable this endpoint.",
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "framework_mode", "service": "colabfold"}
