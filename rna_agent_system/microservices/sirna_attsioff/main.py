"""Mock siRNA efficiency prediction microservice."""

from random import random

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(
    title="Mock siRNA AttSiOff Service",
    description="Return a mock siRNA efficiency score between 0 and 1.",
    version="0.1.0",
)


class SirnaPredictRequest(BaseModel):
    sequence: str = Field(
        ...,
        min_length=5,
        description="Input siRNA sequence for mock prediction.",
        examples=["AUGCUAACGUAGCUA"],
    )


class SirnaPredictResponse(BaseModel):
    sequence: str
    efficiency_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Mock efficiency score, generated randomly.",
    )
    model: str = "mock_attsioff_v1"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=SirnaPredictResponse)
def predict_efficiency(payload: SirnaPredictRequest) -> SirnaPredictResponse:
    return SirnaPredictResponse(
        sequence=payload.sequence,
        efficiency_score=round(random(), 4),
    )
