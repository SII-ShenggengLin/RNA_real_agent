"""ViennaRNA RNAfold microservice."""

from fastapi import FastAPI
from pydantic import BaseModel, Field
import RNA


app = FastAPI(
    title="ViennaRNA Fold Service (Port 8003 Deployment)",
    description=(
        "Predict RNA secondary structure and MFE using ViennaRNA. "
        "Standard deployment port: 8003."
    ),
    version="0.1.1-port8003",
)


class FoldRequest(BaseModel):
    sequence: str = Field(..., min_length=1, description="RNA sequence (A/U/G/C).")


class FoldResponse(BaseModel):
    sequence: str
    structure: str
    mfe: float
    model: str = "ViennaRNA-RNAfold"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/fold", response_model=FoldResponse)
def fold(payload: FoldRequest) -> FoldResponse:
    sequence = payload.sequence.strip().upper().replace("T", "U")
    fc = RNA.fold_compound(sequence)
    structure, mfe = fc.mfe()
    return FoldResponse(sequence=sequence, structure=structure, mfe=float(mfe))
