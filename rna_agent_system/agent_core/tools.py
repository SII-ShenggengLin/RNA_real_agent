"""LangChain tools wrapping mock RNA microservices."""

from __future__ import annotations

import json
import re
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


def _normalize_nucleic_sequence(raw_text: str) -> str:
    """Normalize plain-text or FASTA-like nucleotide input for downstream tools."""
    sequence_lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    merged = "".join(sequence_lines).upper().replace("T", "U")
    return re.sub(r"[^A-Z]", "", merged)


def _normalize_crisot_sequence(raw_text: str) -> str:
    """Normalize CRISOT input to uppercase DNA-like sequence with optional N bases."""
    sequence_lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    merged = "".join(sequence_lines).upper().replace("U", "T")
    sequence = re.sub(r"[^A-Z]", "", merged)
    invalid_chars = sorted(set(ch for ch in sequence if ch not in {"A", "C", "G", "T", "N"}))
    if invalid_chars:
        raise ValueError(
            "CRISOT supports only A/C/G/T/U/N input. "
            f"Unsupported characters: {''.join(invalid_chars)}"
        )
    if len(sequence) != 23:
        raise ValueError(f"CRISOT expects 23-nt sgRNA/target sequences; got {len(sequence)} nt.")
    return sequence


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


class CrisotScoreInput(BaseModel):
    """Input schema for CRISOT score prediction."""

    filepath: str = Field(
        ...,
        description="Path to a workspace or repo-relative file containing the sgRNA sequence.",
    )
    target_sequence: str = Field(
        ...,
        description="Target DNA sequence for CRISOT scoring. Expected length is 23 nt.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8011/score",
        description="REST endpoint for the CRISOT score microservice.",
    )


class CrisotSpecInput(BaseModel):
    """Input schema for CRISOT specificity calculation from a CSV file."""

    csv_filepath: str = Field(
        ...,
        description="Path to a CSV file containing sgRNA and off-target sequences.",
    )
    on_item: str = Field(
        default="On",
        description="CSV column name for sgRNA/on-target sequences.",
    )
    off_item: str = Field(
        default="Off",
        description="CSV column name for off-target sequences.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8011/spec",
        description="REST endpoint for the CRISOT specificity microservice.",
    )


class CrisotOffSpecInput(BaseModel):
    """Input schema for CRISOT genome-wide specificity search."""

    filepath: str = Field(
        ...,
        description="Path to a workspace or repo-relative file containing the sgRNA sequence.",
    )
    target_sequence: str = Field(
        ...,
        description="Target DNA sequence for CRISOT off-spec analysis. Expected length is 23 nt.",
    )
    genome_path: str = Field(
        ...,
        description="Reference genome FASTA path passed through to CRISOT and Cas-OFFinder.",
    )
    mismatches: int = Field(
        default=6,
        ge=0,
        le=10,
        description="Mismatch tolerance passed through to Cas-OFFinder.",
    )
    device: str = Field(
        default="C",
        description="Cas-OFFinder device flag such as `C` or `G0`.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8011/off-spec",
        description="REST endpoint for the CRISOT off-spec microservice.",
    )


class CrisotOptimizeInput(BaseModel):
    """Input schema for CRISOT sgRNA optimization."""

    filepath: str = Field(
        ...,
        description="Path to a workspace or repo-relative file containing the target/guide sequence.",
    )
    genome_path: str = Field(
        ...,
        description="Reference genome FASTA path passed through to CRISOT optimization.",
    )
    threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum retained CRISOT-Score threshold for optimized guides.",
    )
    mismatches: int = Field(
        default=6,
        ge=0,
        le=10,
        description="Mismatch tolerance passed through to Cas-OFFinder.",
    )
    device: str = Field(
        default="C",
        description="Cas-OFFinder device flag such as `C` or `G0`.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8011/optimize",
        description="REST endpoint for the CRISOT optimization microservice.",
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


@tool(args_schema=CrisotScoreInput)
def score_crispr_off_target_with_crisot(
    filepath: str,
    target_sequence: str,
    service_url: str = "http://127.0.0.1:8011/score",
) -> dict[str, Any]:
    """Score one sgRNA-target pair with CRISOT.

    Args:
        filepath: Path to a file containing the sgRNA sequence.
            IMPORTANT: pass a filepath rather than inline guide sequence text.
        target_sequence: Target DNA sequence paired with the sgRNA.
        service_url: REST endpoint for the CRISOT score microservice.

    Returns:
        Dict with normalized sgRNA/target sequences and the CRISOT score.

    Raises:
        ValueError: If the CRISOT service is unreachable or returns an invalid payload.
    """
    sgrna = _normalize_crisot_sequence(read_sequence(filepath))
    normalized_target = _normalize_crisot_sequence(target_sequence)
    try:
        response = requests.post(
            service_url,
            json={"sgrna": sgrna, "target_sequence": normalized_target},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if "crisot_score" not in payload:
            raise ValueError("Missing `crisot_score` in CRISOT score response.")
        payload["input_filepath"] = filepath
        payload["sgrna"] = sgrna
        payload["target_sequence"] = normalized_target
        return payload
    except requests.RequestException as exc:
        detail = ""
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            try:
                detail = str(response_obj.json())
            except ValueError:
                detail = response_obj.text
        suffix = f"; detail={detail}" if detail else ""
        raise ValueError(f"CRISOT score request failed: {exc}{suffix}") from exc


@tool(args_schema=CrisotSpecInput)
def calculate_crispr_specificity_with_crisot(
    csv_filepath: str,
    on_item: str = "On",
    off_item: str = "Off",
    service_url: str = "http://127.0.0.1:8011/spec",
) -> dict[str, Any]:
    """Calculate CRISOT specificity from a CSV of one sgRNA and its candidate off-targets.

    Args:
        csv_filepath: Path to the input CSV. On-target row should appear first.
        on_item: Input column name for sgRNA/on-target sequences.
        off_item: Input column name for off-target sequences.
        service_url: REST endpoint for the CRISOT specificity microservice.

    Returns:
        Dict with CRISOT-Spec and an optional scored CSV copied into workspace.

    Raises:
        ValueError: If the CRISOT service is unreachable or returns an invalid payload.
    """
    try:
        response = requests.post(
            service_url,
            json={
                "csv_path": csv_filepath,
                "on_item": on_item,
                "off_item": off_item,
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        if "crisot_spec" not in payload:
            raise ValueError("Missing `crisot_spec` in CRISOT specificity response.")
        result: dict[str, Any] = {
            "input_csv_filepath": csv_filepath,
            "on_item": on_item,
            "off_item": off_item,
            "crisot_spec": float(payload["crisot_spec"]),
            "row_count": int(payload.get("row_count", 0)),
            "model": payload.get("model", "CRISOT-Score"),
        }
        scored_csv_path = payload.get("scored_csv_path")
        if scored_csv_path:
            result["scored_csv_filepath"] = copy_file_to_workspace(
                str(scored_csv_path),
                prefix="crisot_spec",
                suffix=".csv",
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
        raise ValueError(f"CRISOT spec request failed: {exc}{suffix}") from exc


@tool(args_schema=CrisotOffSpecInput)
def search_crispr_off_targets_with_crisot(
    filepath: str,
    target_sequence: str,
    genome_path: str,
    mismatches: int = 6,
    device: str = "C",
    service_url: str = "http://127.0.0.1:8011/off-spec",
) -> dict[str, Any]:
    """Run CRISOT genome-wide off-target specificity search using Cas-OFFinder.

    Args:
        filepath: Path to a file containing the sgRNA sequence.
            IMPORTANT: pass a filepath rather than inline guide sequence text.
        target_sequence: Target DNA sequence paired with the sgRNA.
        genome_path: Reference genome FASTA path.
        mismatches: Cas-OFFinder mismatch tolerance.
        device: Cas-OFFinder device selector such as `C` or `G0`.
        service_url: REST endpoint for the CRISOT off-spec microservice.

    Returns:
        Dict with CRISOT-Spec, off-target count, and an optional scored CSV artifact.

    Raises:
        ValueError: If the CRISOT service is unreachable or returns an invalid payload.
    """
    sgrna = _normalize_crisot_sequence(read_sequence(filepath))
    normalized_target = _normalize_crisot_sequence(target_sequence)
    try:
        response = requests.post(
            service_url,
            json={
                "sgrna": sgrna,
                "target_sequence": normalized_target,
                "genome_path": genome_path,
                "mismatches": mismatches,
                "device": device,
            },
            timeout=1800,
        )
        response.raise_for_status()
        payload = response.json()
        if "crisot_spec" not in payload:
            raise ValueError("Missing `crisot_spec` in CRISOT off-spec response.")
        result: dict[str, Any] = {
            "input_filepath": filepath,
            "sgrna": sgrna,
            "target_sequence": normalized_target,
            "genome_path": genome_path,
            "mismatches": int(payload.get("mismatches", mismatches)),
            "device": str(payload.get("device", device)),
            "off_target_count": int(payload.get("off_target_count", 0)),
            "crisot_spec": float(payload["crisot_spec"]),
            "model": payload.get("model", "CRISOT-Score"),
        }
        scored_csv_path = payload.get("scored_csv_path")
        if scored_csv_path:
            result["scored_csv_filepath"] = copy_file_to_workspace(
                str(scored_csv_path),
                prefix="crisot_offspec",
                suffix=".csv",
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
        raise ValueError(f"CRISOT off-spec request failed: {exc}{suffix}") from exc


@tool(args_schema=CrisotOptimizeInput)
def optimize_sgrna_with_crisot(
    filepath: str,
    genome_path: str,
    threshold: float = 0.8,
    mismatches: int = 6,
    device: str = "C",
    service_url: str = "http://127.0.0.1:8011/optimize",
) -> dict[str, Any]:
    """Optimize one sgRNA with CRISOT-Opti.

    Args:
        filepath: Path to a file containing the target/guide sequence.
            IMPORTANT: pass a filepath rather than inline guide sequence text.
        genome_path: Reference genome FASTA path used by Cas-OFFinder.
        threshold: Minimum retained CRISOT-Score for optimized guides.
        mismatches: Cas-OFFinder mismatch tolerance.
        device: Cas-OFFinder device selector such as `C` or `G0`.
        service_url: REST endpoint for the CRISOT optimization microservice.

    Returns:
        Dict with the best optimized sgRNA, summary metrics, and CSV artifacts.

    Raises:
        ValueError: If the CRISOT service is unreachable or returns an invalid payload.
    """
    target_sequence = _normalize_crisot_sequence(read_sequence(filepath))
    try:
        response = requests.post(
            service_url,
            json={
                "target_sequence": target_sequence,
                "genome_path": genome_path,
                "threshold": threshold,
                "mismatches": mismatches,
                "device": device,
            },
            timeout=3600,
        )
        response.raise_for_status()
        payload = response.json()
        if "optimization_csv_path" not in payload:
            raise ValueError("Missing `optimization_csv_path` in CRISOT optimization response.")

        result: dict[str, Any] = {
            "input_filepath": filepath,
            "target_sequence": target_sequence,
            "genome_path": genome_path,
            "threshold": float(payload.get("threshold", threshold)),
            "mismatches": int(payload.get("mismatches", mismatches)),
            "device": str(payload.get("device", device)),
            "optimized_available": bool(payload.get("optimized_available", False)),
            "best_sgrna": str(payload.get("best_sgrna", "")),
            "best_mutation": str(payload.get("best_mutation", "")),
            "best_crisot_score": float(payload.get("best_crisot_score", 0.0)),
            "best_crisot_spec": float(payload.get("best_crisot_spec", 0.0)),
            "best_delta_spec": float(payload.get("best_delta_spec", 0.0)),
            "model": payload.get("model", "CRISOT-Opti"),
        }
        optimization_csv_path = payload.get("optimization_csv_path")
        if optimization_csv_path:
            result["optimization_csv_filepath"] = copy_file_to_workspace(
                str(optimization_csv_path),
                prefix="crisot_optimize",
                suffix=".csv",
            )
        best_sgrna = result["best_sgrna"]
        if best_sgrna:
            result["optimized_sgrna_filepath"] = save_sequence(best_sgrna, prefix="crisot_optimized_sgrna")
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
        raise ValueError(f"CRISOT optimize request failed: {exc}{suffix}") from exc


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


class RNARLCdsInput(BaseModel):
    """Input schema for RNARL CDS design tool."""

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace file containing a protein sequence for RNARL CDS design. "
            "Do not pass raw sequence text directly."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8008/generate/cds",
        description="REST endpoint for the RNARL CDS generation microservice.",
    )
    model_type: str = Field(
        default="Homo sapiens mRNA",
        description=(
            "RNARL model type, for example `Homo sapiens mRNA`, "
            "`Arabidopsis thaliana mRNA`, or `Homo sapiens circular RNA`."
        ),
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional override for the RNARL actor checkpoint path.",
    )
    esm2_model_path: Optional[str] = Field(
        default=None,
        description="Optional override for the local ESM-2 model directory.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device override such as `cuda:0` or `cpu`.",
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


class RNAsmolScoreInput(BaseModel):
    """Input schema for RNAsmol RNA-ligand scoring."""

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace or repo-relative file containing the RNA sequence. "
            "Do not pass raw RNA sequence text directly."
        ),
    )
    smiles: str = Field(
        ...,
        min_length=1,
        description="Ligand SMILES string scored by RNAsmol.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8007/score",
        description="REST endpoint for the RNAsmol microservice.",
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional checkpoint path passed through to RNAsmol. "
            "Use this when the service should not rely on its default checkpoint lookup."
        ),
    )


class GerNABindScoreInput(BaseModel):
    """Input schema for GerNA-Bind RNA-ligand scoring."""

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace or repo-relative file containing the RNA sequence. "
            "Do not pass raw RNA sequence text directly."
        ),
    )
    smiles: str = Field(
        ...,
        min_length=1,
        description="Ligand SMILES string scored by GerNA-Bind.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8010/score",
        description="REST endpoint for the GerNA-Bind microservice.",
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional checkpoint path passed through to GerNA-Bind.",
    )
    pdb_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional absolute or repo-relative RNA structure path passed through to GerNA-Bind. "
            "When provided, the service can skip the RhoFold preprocessing step."
        ),
    )
    secondary_structure: Optional[str] = Field(
        default=None,
        description=(
            "Optional dot-bracket RNA secondary structure passed through to GerNA-Bind. "
            "When provided, the service can skip 2D structure prediction."
        ),
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device override such as `cuda:0` or `cpu`.",
    )


class RNASTOPPredictionInput(BaseModel):
    """Input schema for RNASTOP stability prediction."""

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace or repo-relative file containing the RNA sequence. "
            "Do not pass raw RNA sequence text directly."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8009/predict/stability",
        description="REST endpoint for the RNASTOP stability prediction microservice.",
    )
    checkpoint_path: Optional[str] = Field(
        default=None,
        description="Optional checkpoint override for the RNASTOP service.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device override such as `cuda:0` or `cpu`.",
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


@tool(args_schema=RNARLCdsInput)
def design_mrna_cds_with_rnarl(
    filepath: str,
    service_url: str = "http://127.0.0.1:8008/generate/cds",
    model_type: str = "Homo sapiens mRNA",
    checkpoint_path: Optional[str] = None,
    esm2_model_path: Optional[str] = None,
    device: Optional[str] = None,
) -> dict[str, Any]:
    """Design an mRNA CDS sequence from a protein sequence using RNARL.

    Args:
        filepath: Workspace file path containing the input protein sequence.
            IMPORTANT: You must pass a workspace filepath, not the sequence itself.
        service_url: REST endpoint for the RNARL microservice.
        model_type: RNARL model type matching the author notebook checkpoints.
        checkpoint_path: Optional actor checkpoint override for the RNARL service.
        esm2_model_path: Optional local ESM-2 model directory override.
        device: Optional torch device override passed to the RNARL service.

    Returns:
        Dict containing the generated CDS sequence, runtime metadata, and a new workspace filepath.

    Raises:
        ValueError: If the RNARL service is unreachable or returns an invalid payload.
    """
    protein_sequence = read_sequence(filepath).strip()
    try:
        request_payload: dict[str, Any] = {
            "protein_sequence": protein_sequence,
            "model_type": model_type,
        }
        if checkpoint_path:
            request_payload["checkpoint_path"] = checkpoint_path
        if esm2_model_path:
            request_payload["esm2_model_path"] = esm2_model_path
        if device:
            request_payload["device"] = device

        response = requests.post(
            service_url,
            json=request_payload,
            timeout=600,
        )
        response.raise_for_status()
        payload = response.json()
        if "generated_sequence" not in payload:
            raise ValueError("Missing `generated_sequence` in RNARL response.")
        output_filepath = save_sequence(payload["generated_sequence"], prefix="rnarl_cds")
        return {
            "input_filepath": filepath,
            "output_filepath": output_filepath,
            "generated_sequence": payload["generated_sequence"],
            "model_type": payload.get("model_type", model_type),
            "checkpoint_path": payload.get("checkpoint_path", checkpoint_path or ""),
            "esm2_model_path": payload.get("esm2_model_path", esm2_model_path or ""),
            "device": payload.get("device", device or ""),
            "model": payload.get("model", "RNARL-actor"),
        }
    except requests.RequestException as exc:
        detail = ""
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            try:
                detail = str(response_obj.json())
            except ValueError:
                detail = response_obj.text
        suffix = f"; detail={detail}" if detail else ""
        raise ValueError(f"RNARL service request failed: {exc}{suffix}") from exc


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


@tool(args_schema=RNAsmolScoreInput)
def score_rna_ligand_binding_with_rnasmol(
    filepath: str,
    smiles: str,
    service_url: str = "http://127.0.0.1:8007/score",
    checkpoint_path: Optional[str] = None,
) -> dict[str, Any]:
    """Score RNA-ligand binding probability using the RNAsmol microservice.

    Args:
        filepath: Path to a file containing the RNA sequence.
            IMPORTANT: pass a filepath rather than long inline sequence text.
        smiles: Ligand SMILES string to score against the RNA sequence.
        service_url: REST endpoint for the RNAsmol microservice.
        checkpoint_path: Optional checkpoint override for the RNAsmol service.

    Returns:
        Dict with the positive-class probability, predicted label, and checkpoint metadata.

    Raises:
        ValueError: If the RNAsmol service is unreachable or returns an invalid payload.
    """
    sequence = _normalize_nucleic_sequence(read_sequence(filepath))
    try:
        request_payload: dict[str, Any] = {
            "rna_sequence": sequence,
            "smiles": smiles.strip(),
        }
        if checkpoint_path:
            request_payload["checkpoint_path"] = checkpoint_path

        response = requests.post(
            service_url,
            json=request_payload,
            timeout=300,
        )
        response.raise_for_status()
        payload = response.json()
        if "probability_positive" not in payload or "predicted_label" not in payload:
            raise ValueError(
                "Missing `probability_positive` or `predicted_label` in RNAsmol response."
            )
        payload["input_filepath"] = filepath
        payload["smiles"] = smiles.strip()
        payload["rna_sequence"] = sequence
        return payload
    except requests.RequestException as exc:
        detail = ""
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            try:
                detail = str(response_obj.json())
            except ValueError:
                detail = response_obj.text
        suffix = f"; detail={detail}" if detail else ""
        raise ValueError(f"RNAsmol service request failed: {exc}{suffix}") from exc


@tool(args_schema=GerNABindScoreInput)
def score_rna_ligand_binding_with_gernabind(
    filepath: str,
    smiles: str,
    service_url: str = "http://127.0.0.1:8010/score",
    checkpoint_path: Optional[str] = None,
    pdb_path: Optional[str] = None,
    secondary_structure: Optional[str] = None,
    device: Optional[str] = None,
) -> dict[str, Any]:
    """Score RNA-ligand binding probability using the GerNA-Bind microservice.

    Args:
        filepath: Path to a file containing the RNA sequence.
            IMPORTANT: pass a filepath rather than long inline sequence text.
        smiles: Ligand SMILES string to score against the RNA sequence.
        service_url: REST endpoint for the GerNA-Bind microservice.
        checkpoint_path: Optional checkpoint override for the GerNA-Bind service.
        pdb_path: Optional precomputed RNA structure path passed through to GerNA-Bind.
        secondary_structure: Optional dot-bracket secondary structure passed through to GerNA-Bind.
        device: Optional torch device override such as `cuda:0` or `cpu`.

    Returns:
        Dict with the positive-class probability, predicted label, checkpoint metadata,
        and preprocessing metadata such as the PDB used for feature generation.

    Raises:
        ValueError: If the GerNA-Bind service is unreachable or returns an invalid payload.
    """
    sequence = _normalize_nucleic_sequence(read_sequence(filepath))
    try:
        request_payload: dict[str, Any] = {
            "rna_sequence": sequence,
            "smiles": smiles.strip(),
        }
        if checkpoint_path:
            request_payload["checkpoint_path"] = checkpoint_path
        if pdb_path:
            request_payload["pdb_path"] = pdb_path
        if secondary_structure:
            request_payload["secondary_structure"] = secondary_structure
        if device:
            request_payload["device"] = device

        response = requests.post(
            service_url,
            json=request_payload,
            timeout=1800,
        )
        response.raise_for_status()
        payload = response.json()
        if "probability_positive" not in payload or "predicted_label" not in payload:
            raise ValueError(
                "Missing `probability_positive` or `predicted_label` in GerNA-Bind response."
            )
        payload["input_filepath"] = filepath
        payload["smiles"] = smiles.strip()
        payload["rna_sequence"] = sequence
        if pdb_path:
            payload["requested_pdb_path"] = pdb_path
        if secondary_structure:
            payload["requested_secondary_structure"] = secondary_structure
        return payload
    except requests.RequestException as exc:
        detail = ""
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            try:
                detail = str(response_obj.json())
            except ValueError:
                detail = response_obj.text
        suffix = f"; detail={detail}" if detail else ""
        raise ValueError(f"GerNA-Bind service request failed: {exc}{suffix}") from exc


@tool(args_schema=RNASTOPPredictionInput)
def predict_mrna_stability_with_rnastop(
    filepath: str,
    service_url: str = "http://127.0.0.1:8009/predict/stability",
    checkpoint_path: Optional[str] = None,
    device: Optional[str] = None,
) -> dict[str, Any]:
    """Predict mRNA degradation and stability summaries using the RNASTOP microservice.

    Args:
        filepath: Path to a file containing the RNA sequence.
            IMPORTANT: pass a filepath rather than long inline sequence text.
        service_url: REST endpoint for the RNASTOP microservice.
        checkpoint_path: Optional checkpoint override for the RNASTOP service.
        device: Optional torch device override such as `cuda:0` or `cpu`.

    Returns:
        Dict with per-sequence summary metrics and a workspace JSON artifact.

    Raises:
        ValueError: If the RNASTOP service is unreachable or returns an invalid payload.
    """
    sequence = _normalize_nucleic_sequence(read_sequence(filepath))
    try:
        request_payload: dict[str, Any] = {"sequence": sequence}
        if checkpoint_path:
            request_payload["checkpoint_path"] = checkpoint_path
        if device:
            request_payload["device"] = device

        response = requests.post(
            service_url,
            json=request_payload,
            timeout=1800,
        )
        response.raise_for_status()
        payload = response.json()
        required_fields = {
            "mean_reactivity",
            "mean_deg_Mg_pH10",
            "mean_deg_Mg_50C",
            "per_position_predictions",
        }
        if not required_fields.issubset(payload):
            raise ValueError(
                "RNASTOP response is missing one or more required fields: "
                f"{sorted(required_fields - set(payload))}"
            )

        prediction_filepath = save_text_file(
            json.dumps(payload, ensure_ascii=True, indent=2),
            prefix="rnastop_prediction",
            suffix=".json",
        )
        return {
            "input_filepath": filepath,
            "prediction_filepath": prediction_filepath,
            "sequence": payload.get("sequence", sequence),
            "used_sequence": payload.get("used_sequence", sequence),
            "sequence_length": int(payload.get("sequence_length", len(sequence))),
            "used_length": int(payload.get("used_length", len(sequence))),
            "truncated": bool(payload.get("truncated", False)),
            "structure": payload.get("structure", ""),
            "loop_type": payload.get("loop_type", ""),
            "mfe": float(payload.get("mfe", 0.0)),
            "mean_reactivity": float(payload["mean_reactivity"]),
            "mean_deg_mg_ph10": float(payload["mean_deg_Mg_pH10"]),
            "mean_deg_mg_50c": float(payload["mean_deg_Mg_50C"]),
            "checkpoint_path": str(payload.get("checkpoint_path", checkpoint_path or "")),
            "device": str(payload.get("device", device or "")),
            "model": payload.get("model", "RNASTOP"),
        }
    except requests.RequestException as exc:
        detail = ""
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            try:
                detail = str(response_obj.json())
            except ValueError:
                detail = response_obj.text
        suffix = f"; detail={detail}" if detail else ""
        raise ValueError(f"RNASTOP service request failed: {exc}{suffix}") from exc
