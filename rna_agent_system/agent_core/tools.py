"""LangChain tools wrapping mock RNA microservices."""

from __future__ import annotations

import time
from typing import Any, Optional

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from agent_core.file_manager import (
    copy_file_to_workspace,
    read_sequence,
    save_sequence,
    save_text_file,
)


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


class RhoFoldInput(BaseModel):
    """Input schema for RhoFold tertiary structure prediction."""

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace file containing an RNA sequence for RhoFold. "
            "Do not pass raw sequence text directly."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8005/predict",
        description="REST endpoint for the RhoFold prediction microservice.",
    )
    relax_steps: int = Field(
        default=0,
        ge=0,
        description="Amber relaxation steps. Use 0 to skip relaxation and reduce runtime.",
    )


class RhoDesignInput(BaseModel):
    """Input schema for RhoDesign structure-to-sequence design."""

    pdb_filepath: str = Field(
        ...,
        description=(
            "Path to the input PDB or CIF structure file for RhoDesign. "
            "This can be an absolute path or a repo-relative path."
        ),
    )
    secondary_structure_filepath: Optional[str] = Field(
        default=None,
        description=(
            "Optional path to a secondary-structure contact map `.npy` file. "
            "Provide it when using the with-2D RhoDesign mode."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8006/design/from-structure",
        description="REST endpoint for the RhoDesign microservice.",
    )
    temperature: float = Field(
        default=1e-5,
        gt=0.0,
        description="Sampling temperature passed through to RhoDesign.",
    )
    device: int = Field(
        default=0,
        ge=0,
        description="CUDA device index for the upstream RhoDesign script.",
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


@tool(args_schema=RhoFoldInput)
def predict_rna_tertiary_structure_with_rhofold(
    filepath: str,
    service_url: str = "http://127.0.0.1:8005/predict",
    relax_steps: int = 0,
) -> dict[str, Any]:
    """Predict RNA tertiary structure using the RhoFold microservice.

    Args:
        filepath: Workspace file path containing the input RNA sequence.
            IMPORTANT: You must pass a workspace filepath, not the sequence itself.
        service_url: REST endpoint for the RhoFold microservice.
        relax_steps: Amber relaxation iterations. Default 0 keeps inference lighter.

    Returns:
        Dict containing workspace paths for generated artifacts and a mean pLDDT summary.

    Raises:
        ValueError: If the RhoFold service is unreachable or returns an invalid payload.
    """
    sequence = read_sequence(filepath).strip()
    try:
        response = requests.post(
            service_url,
            json={
                "sequence": sequence,
                "single_seq_pred": True,
                "relax_steps": relax_steps,
            },
            timeout=1800,
        )
        response.raise_for_status()
        payload = response.json()
        if "output_pdb_path" not in payload:
            raise ValueError("Missing `output_pdb_path` in RhoFold response.")

        mean_plddt = payload.get("mean_plddt")
        output_pdb_filepath = copy_file_to_workspace(payload["output_pdb_path"], prefix="rhofold_model")
        result: dict[str, Any] = {
            "input_filepath": filepath,
            "output_pdb_filepath": output_pdb_filepath,
            "mean_plddt": float(mean_plddt) if mean_plddt is not None else 0.0,
            "model": payload.get("model", "RhoFold+"),
            "service_output_dir": payload.get("service_output_dir", ""),
        }

        secondary_ct_path = payload.get("secondary_structure_ct_path")
        if secondary_ct_path:
            result["secondary_structure_ct_filepath"] = copy_file_to_workspace(
                secondary_ct_path,
                prefix="rhofold_ss",
            )

        results_npz_path = payload.get("results_npz_path")
        if results_npz_path:
            result["results_npz_filepath"] = copy_file_to_workspace(
                results_npz_path,
                prefix="rhofold_results",
            )

        log_path = payload.get("log_path")
        if log_path:
            result["log_filepath"] = copy_file_to_workspace(log_path, prefix="rhofold_log")

        if payload.get("stdout"):
            result["stdout_filepath"] = save_text_file(
                str(payload["stdout"]),
                prefix="rhofold_stdout",
                suffix=".log",
            )
        if payload.get("stderr"):
            result["stderr_filepath"] = save_text_file(
                str(payload["stderr"]),
                prefix="rhofold_stderr",
                suffix=".log",
            )
        return result
    except requests.RequestException as exc:
        raise ValueError(f"RhoFold service request failed: {exc}") from exc


@tool(args_schema=RhoDesignInput)
def design_rna_sequence_with_rhodesign(
    pdb_filepath: str,
    secondary_structure_filepath: Optional[str] = None,
    service_url: str = "http://127.0.0.1:8006/design/from-structure",
    temperature: float = 1e-5,
    device: int = 0,
) -> dict[str, Any]:
    """Design an RNA sequence from a structure file using the RhoDesign microservice.

    Args:
        pdb_filepath: Path to the input PDB/CIF structure file.
        secondary_structure_filepath: Optional `.npy` contact-map path for the 2D-assisted mode.
        service_url: REST endpoint for the RhoDesign microservice.
        temperature: Sampling temperature for sequence generation.
        device: CUDA device index used by the upstream RhoDesign script.

    Returns:
        Dict containing the designed RNA sequence, a new workspace sequence filepath,
        copied FASTA/log artifacts when available, and summary metadata.

    Raises:
        ValueError: If the RhoDesign service is unreachable or returns an invalid payload.
    """
    try:
        response = requests.post(
            service_url,
            json={
                "pdb_path": pdb_filepath,
                "secondary_structure_path": secondary_structure_filepath,
                "temperature": temperature,
                "device": device,
            },
            timeout=3600,
        )
        response.raise_for_status()
        payload = response.json()
        if "predicted_sequence" not in payload or "output_fasta_path" not in payload:
            raise ValueError(
                "Missing `predicted_sequence` or `output_fasta_path` in RhoDesign response."
            )

        output_filepath = save_sequence(payload["predicted_sequence"], prefix="rhodesign_seq")
        result: dict[str, Any] = {
            "input_pdb_filepath": pdb_filepath,
            "output_filepath": output_filepath,
            "predicted_sequence": payload["predicted_sequence"],
            "used_secondary_structure": bool(payload.get("used_secondary_structure", False)),
            "model": payload.get("model", "RhoDesign"),
            "service_output_dir": payload.get("service_output_dir", ""),
            "checkpoint_path": payload.get("checkpoint_path", ""),
        }

        recovery_rate = payload.get("recovery_rate")
        if recovery_rate is not None:
            result["recovery_rate"] = float(recovery_rate)

        if secondary_structure_filepath:
            result["secondary_structure_filepath"] = secondary_structure_filepath

        output_fasta_path = payload.get("output_fasta_path")
        if output_fasta_path:
            result["output_fasta_filepath"] = copy_file_to_workspace(
                output_fasta_path,
                prefix="rhodesign_fasta",
            )

        if payload.get("stdout"):
            result["stdout_filepath"] = save_text_file(
                str(payload["stdout"]),
                prefix="rhodesign_stdout",
                suffix=".log",
            )
        if payload.get("stderr"):
            result["stderr_filepath"] = save_text_file(
                str(payload["stderr"]),
                prefix="rhodesign_stderr",
                suffix=".log",
            )
        return result
    except requests.RequestException as exc:
        detail = ""
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            try:
                detail = str(response_obj.json())
            except ValueError:
                detail = response_obj.text
        suffix = f"; detail={detail}" if detail else ""
        raise ValueError(f"RhoDesign service request failed: {exc}{suffix}") from exc
