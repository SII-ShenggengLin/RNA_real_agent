"""Mock off-target check microservice."""

from random import randint

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(
    title="Mock Off-target BLAST Service",
    description="Return a mock off-target hit count for a sequence.",
    version="0.1.0",
)


class OffTargetRequest(BaseModel):
    sequence: str = Field(
        ...,
        min_length=5,
        description="Input sequence for mock off-target assessment.",
        examples=["AUGCUAACGUAGCUA"],
    )


class OffTargetResponse(BaseModel):
    sequence: str
    off_target_genes: int = Field(
        ...,
        ge=0,
        le=2,
        description="Mock number of off-target genes (0-2).",
    )
    model: str = "mock_blast_v1"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/check", response_model=OffTargetResponse)
def check_off_target(payload: OffTargetRequest) -> OffTargetResponse:
    return OffTargetResponse(
        sequence=payload.sequence,
        off_target_genes=randint(0, 2),
    )
