"""LangChain tools wrapping mock RNA microservices."""

from __future__ import annotations

import time
from typing import Any

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from agent_core.file_manager import read_sequence, save_sequence


class SirnaEfficiencyInput(BaseModel):
    """Input schema for siRNA efficiency prediction tool."""

    filepath: str = Field(
        ...,
        description="Path to RNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8001/predict",
        description="Full URL for the mock AttSiOff prediction API endpoint.",
    )


class OffTargetCheckInput(BaseModel):
    """Input schema for off-target check tool."""

    filepath: str = Field(
        ...,
        description="Path to RNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8002/check",
        description="Full URL for the mock off-target API endpoint.",
    )


@tool(args_schema=SirnaEfficiencyInput)
def predict_sirna_efficiency(filepath: str, service_url: str = "http://127.0.0.1:8001/predict") -> dict[str, Any]:
    """Predict mock siRNA efficiency using microservice API.

    Args:
        filepath: Workspace file path holding sequence content.
            IMPORTANT: You must pass a filepath in workspace, NOT raw sequence text.
        service_url: Endpoint URL for the mock siRNA service.

    Returns:
        Dict containing filepath, sequence, efficiency_score (0-1), and model name.

    Raises:
        ValueError: If the HTTP request fails or response payload is invalid.
    """
    sequence = read_sequence(filepath).strip()
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
        payload["filepath"] = filepath
        return payload
    except requests.RequestException as exc:
        raise ValueError(f"siRNA service request failed: {exc}") from exc


@tool(args_schema=OffTargetCheckInput)
def check_off_target(filepath: str, service_url: str = "http://127.0.0.1:8002/check") -> dict[str, Any]:
    """Check mock off-target risk using microservice API.

    Args:
        filepath: Workspace file path holding sequence content.
            IMPORTANT: You must pass a filepath in workspace, NOT raw sequence text.
        service_url: Endpoint URL for the mock off-target service.

    Returns:
        Dict containing filepath, sequence, off_target_genes (0/1/2), and model name.

    Raises:
        ValueError: If the HTTP request fails or response payload is invalid.
    """
    sequence = read_sequence(filepath).strip()
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
        payload["filepath"] = filepath
        return payload
    except requests.RequestException as exc:
        raise ValueError(f"Off-target service request failed: {exc}") from exc


class MrnaToolInput(BaseModel):
    """Input schema for mock mRNA tools."""

    filepath: str = Field(
        ...,
        description="Path to mRNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.",
    )


class GemornaCdsInput(BaseModel):
    """Input schema for GEMORNA CDS design tool."""

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace file containing a protein sequence for GEMORNA CDS design. "
            "Do not pass raw sequence text directly."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8004/generate/cds",
        description="REST endpoint for the GEMORNA CDS generation microservice.",
    )


@tool(args_schema=MrnaToolInput)
def mock_codon_optimization(filepath: str) -> dict[str, Any]:
    """Mock codon optimization for mRNA sequence.

    Args:
        filepath: Workspace file path holding mRNA sequence.
            IMPORTANT: pass workspace filepath only, never inline long sequence in tool args.

    Returns:
        Dict with cai_score and optimized sequence filepath in workspace.
    """
    sequence = read_sequence(filepath).strip().upper().replace("T", "U")
    time.sleep(0.3)
    optimized = sequence.replace("UUU", "UUC").replace("UUA", "CUG")
    optimized_filepath = save_sequence(optimized, prefix="mrna_opt")
    return {
        "input_filepath": filepath,
        "optimized_filepath": optimized_filepath,
        "cai_score": 0.88,
        "model": "mock_codon_optimizer_v1",
    }


@tool(args_schema=MrnaToolInput)
def predict_rna_secondary_structure(
    filepath: str, service_url: str = "http://localhost:8003/fold"
) -> str:
    """Predict RNA secondary structure and MFE using ViennaRNA service.

    Args:
        filepath: Workspace file path containing RNA sequence content.
            IMPORTANT: You must pass a filepath in workspace, NOT raw sequence text.
        service_url: REST endpoint for ViennaRNA fold microservice.

    Returns:
        Formatted string that contains RNA secondary structure and MFE.

    Raises:
        ValueError: If ViennaRNA API request fails or response payload is invalid.
    """
    sequence = read_sequence(filepath).strip()
    try:
        response = requests.post(
            service_url,
            json={"sequence": sequence},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if "structure" not in payload or "mfe" not in payload:
            raise ValueError("Missing `structure` or `mfe` in ViennaRNA response.")
        return (
            f"filepath={filepath}; "
            f"structure={payload['structure']}; "
            f"mfe={payload['mfe']}"
        )
    except requests.RequestException as exc:
        raise ValueError(f"ViennaRNA service request failed: {exc}") from exc


@tool(args_schema=GemornaCdsInput)
def design_mrna_cds_with_gemorna(
    filepath: str, service_url: str = "http://127.0.0.1:8004/generate/cds"
) -> dict[str, Any]:
    """Design an mRNA CDS sequence from a protein sequence using GEMORNA.

    Args:
        filepath: Workspace file path containing the input protein sequence.
            IMPORTANT: You must pass a workspace filepath, not the sequence itself.
        service_url: REST endpoint for the GEMORNA microservice.

    Returns:
        Dict containing the generated CDS sequence, raw GEMORNA stdout, and a new workspace filepath.

    Raises:
        ValueError: If the GEMORNA service is unreachable or returns an invalid payload.
    """
    protein_sequence = read_sequence(filepath).strip()
    try:
        response = requests.post(
            service_url,
            json={"protein_sequence": protein_sequence},
            timeout=300,
        )
        response.raise_for_status()
        payload = response.json()
        if "generated_sequence" not in payload:
            raise ValueError("Missing `generated_sequence` in GEMORNA response.")
        output_filepath = save_sequence(payload["generated_sequence"], prefix="gemorna_cds")
        return {
            "input_filepath": filepath,
            "output_filepath": output_filepath,
            "generated_sequence": payload["generated_sequence"],
            "raw_output": payload.get("raw_output", ""),
            "model": payload.get("model", "GEMORNA-cds"),
        }
    except requests.RequestException as exc:
        raise ValueError(f"GEMORNA service request failed: {exc}") from exc
