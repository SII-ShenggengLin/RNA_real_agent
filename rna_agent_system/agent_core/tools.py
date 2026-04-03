"""LangChain tools wrapping mock RNA microservices."""

from __future__ import annotations

from typing import Any

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class SirnaEfficiencyInput(BaseModel):
    """Input schema for siRNA efficiency prediction tool."""

    sequence: str = Field(
        ...,
        min_length=5,
        description="Candidate siRNA sequence to evaluate.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8001/predict",
        description="Full URL for the mock AttSiOff prediction API endpoint.",
    )


class OffTargetCheckInput(BaseModel):
    """Input schema for off-target check tool."""

    sequence: str = Field(
        ...,
        min_length=5,
        description="Candidate siRNA sequence to evaluate for off-target risk.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8002/check",
        description="Full URL for the mock off-target API endpoint.",
    )


@tool(args_schema=SirnaEfficiencyInput)
def predict_sirna_efficiency(sequence: str, service_url: str = "http://127.0.0.1:8001/predict") -> dict[str, Any]:
    """Predict mock siRNA efficiency using microservice API.

    Args:
        sequence: Candidate siRNA sequence. Use RNA alphabet (A/U/G/C).
        service_url: Endpoint URL for the mock siRNA service.

    Returns:
        Dict containing sequence, efficiency_score (0-1), and model name.

    Raises:
        ValueError: If the HTTP request fails or response payload is invalid.
    """
    try:
        response = requests.post(
            service_url,
            json={"sequence": sequence},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if "efficiency_score" not in payload:
            raise ValueError("Missing `efficiency_score` in siRNA service response.")
        return payload
    except requests.RequestException as exc:
        raise ValueError(f"siRNA service request failed: {exc}") from exc


@tool(args_schema=OffTargetCheckInput)
def check_off_target(sequence: str, service_url: str = "http://127.0.0.1:8002/check") -> dict[str, Any]:
    """Check mock off-target risk using microservice API.

    Args:
        sequence: Candidate siRNA sequence. Usually same sequence from design step.
        service_url: Endpoint URL for the mock off-target service.

    Returns:
        Dict containing sequence, off_target_genes (0/1/2), and model name.

    Raises:
        ValueError: If the HTTP request fails or response payload is invalid.
    """
    try:
        response = requests.post(
            service_url,
            json={"sequence": sequence},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if "off_target_genes" not in payload:
            raise ValueError("Missing `off_target_genes` in off-target service response.")
        return payload
    except requests.RequestException as exc:
        raise ValueError(f"Off-target service request failed: {exc}") from exc
