"""LangChain @tool wrappers for RNA design microservices."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
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


def _normalize_sgrna_design_sequence(raw_text: str) -> str:
    """Normalize sgRNA-handle DNA sequence input for sgrna_design service."""
    sequence_lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    merged = "".join(sequence_lines).upper().replace("U", "T")
    sequence = re.sub(r"[^A-Z]", "", merged)
    invalid_chars = sorted(set(ch for ch in sequence if ch not in {"A", "C", "G", "T"}))
    if invalid_chars:
        raise ValueError(
            "sgRNA design supports only A/C/G/T/U input. "
            f"Unsupported characters: {''.join(invalid_chars)}"
        )
    if len(sequence) < 40 or len(sequence) > 120:
        raise ValueError(
            "sgRNA design expects a handle/template sequence length between 40 and 120 nt; "
            f"got {len(sequence)} nt."
        )
    return sequence


class SirnaEfficiencyInput(BaseModel):
    """Input schema for the siRNA efficiency prediction tool."""

    filepath: str = Field(
        ...,
        description="Path to RNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8001/predict",
        description="Full URL for the AttSiOff prediction API endpoint.",
    )


class OffTargetCheckInput(BaseModel):
    """Input schema for off-target check tool."""

    filepath: str = Field(
        ...,
        description="Path to RNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8002/check",
        description="Full URL for the off-target checking API endpoint.",
    )


class BlastnSearchInput(BaseModel):
    """Input schema for NCBI BLAST+ blastn (microservice on port 8019)."""

    filepath: str = Field(
        ...,
        description="Query nucleotide sequence file (workspace path or absolute on the server).",
    )
    subject_fasta_path: Optional[str] = Field(
        default=None,
        description="Subject multi-FASTA path (server-side). Indexed with makeblastdb at runtime.",
    )
    subject_db: Optional[str] = Field(
        default=None,
        description="Existing nucleotide BLAST database prefix path (server-side), e.g. /data/nt/ref.",
    )
    task: str = Field(
        default="blastn-short",
        description="blastn -task: blastn-short | blastn | megablast | dc-megablast.",
    )
    evalue: float = Field(default=10.0, gt=0.0)
    word_size: Optional[int] = Field(
        default=None,
        description="Optional blastn -word_size (recommended for manual tuning of short queries).",
    )
    max_target_seqs: int = Field(default=50, ge=1, le=10000)
    perc_identity: Optional[float] = Field(
        default=None,
        description="Optional minimum percent identity filter passed to blastn.",
    )
    strand: str = Field(default="both", description="blastn -strand: both | plus | minus.")
    service_url: str = Field(
        default="http://127.0.0.1:8019/blastn",
        description="URL for the blast_service POST /blastn endpoint.",
    )


class EvitarDesignInput(BaseModel):
    """Input schema for Evitar siRNA/Cas13 design tool."""

    filepath: str = Field(
        ...,
        description="Path to input FASTA file in workspace or repo-relative path.",
    )
    mode: str = Field(
        default="existing",
        description="Evitar mode: `existing` or `predesign`.",
    )
    predict: str = Field(
        default="predsi",
        description="Evitar predict option: `predsi`, `rnaxs`, or `CRISPR`.",
    )
    strains_path: Optional[str] = Field(
        default=None,
        description="Required for existing-virus mode. FASTA path with multiple strains.",
    )
    off_target: bool = Field(
        default=False,
        description="Enable Evitar off-target pipeline.",
    )
    ncores: int = Field(
        default=1,
        ge=1,
        description="Number of threads for Evitar.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8016/design",
        description="REST endpoint for the Evitar microservice.",
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


class SgRNADesignInput(BaseModel):
    """Input schema for sgRNA handle design via sgrna_design_service."""

    filepath: str = Field(
        ...,
        description="Path to a workspace or repo-relative file containing sgRNA handle seed sequence.",
    )
    n_samples: int = Field(
        default=10,
        ge=1,
        le=200,
        description="Number of designed candidates to request from service.",
    )
    mutation_number: int = Field(
        default=22,
        ge=1,
        le=40,
        description="Maximum mutation count relative to the seed sequence.",
    )
    temperature: float = Field(
        default=1.0,
        gt=0.0,
        le=5.0,
        description="Sampling temperature passed through to service generation.",
    )
    max_overlap: int = Field(
        default=21,
        ge=1,
        le=60,
        description="Maximum longest-common-substring overlap among accepted candidates.",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device override such as `cuda:0` or `cpu`.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8017/design",
        description="REST endpoint for sgRNA design microservice.",
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


def _absolute_path_under_project(filepath: str) -> str:
    """Resolve workspace-relative paths to absolute paths on the server (blast microservice reads these)."""
    path_obj = Path(filepath.strip())
    if path_obj.is_absolute():
        return str(path_obj.resolve())
    project_root = Path(__file__).resolve().parents[1]
    return str((project_root / filepath).resolve())


@tool(args_schema=BlastnSearchInput)
def run_blastn_similarity_search(
    filepath: str,
    subject_fasta_path: Optional[str] = None,
    subject_db: Optional[str] = None,
    task: str = "blastn-short",
    evalue: float = 10.0,
    word_size: Optional[int] = None,
    max_target_seqs: int = 50,
    perc_identity: Optional[float] = None,
    strand: str = "both",
    service_url: str = "http://127.0.0.1:8019/blastn",
) -> dict[str, Any]:
    """Run NCBI blastn against a subject FASTA or an existing nucleotide BLAST database.

    Requires the ``blast_service`` microservice (port 8019) and BLAST+ on the server PATH.
    Provide exactly one of ``subject_fasta_path`` or ``subject_db``. The query is read from
    ``filepath`` (plain sequence or FASTA); nucleotides are normalized to DNA for blastn.

    Args:
        filepath: Query sequence file (typically under ``workspace/``).
        subject_fasta_path: Path to subject FASTA on the server (makeblastdb run in the service).
        subject_db: Prefix path of an existing BLAST nucleotide database.
        task: blastn task name (short oligos default ``blastn-short``).
        evalue: Expect value threshold.
        word_size: Optional word size.
        max_target_seqs: Maximum aligned subject sequences to report.
        perc_identity: Optional percent identity cutoff.
        strand: Query/subject strand option.
        service_url: POST endpoint for the blast microservice.

    Returns:
        Dict with hit counts, preview, paths to saved tabular output under ``workspace/``, and commands.

    Raises:
        ValueError: If arguments are inconsistent or the HTTP call fails.
    """
    if bool(subject_fasta_path) == bool(subject_db):
        raise ValueError("Provide exactly one of subject_fasta_path or subject_db.")
    read_sequence(filepath)  # validate readable before calling remote service
    query_abs = _absolute_path_under_project(filepath)
    payload: dict[str, Any] = {
        "query_filepath": query_abs,
        "task": task,
        "evalue": float(evalue),
        "max_target_seqs": int(max_target_seqs),
        "strand": strand,
    }
    if subject_fasta_path:
        payload["subject_fasta_path"] = (
            subject_fasta_path
            if Path(subject_fasta_path).is_absolute()
            else str((Path(__file__).resolve().parents[1] / subject_fasta_path).resolve())
        )
    else:
        assert subject_db is not None
        payload["subject_db"] = (
            subject_db
            if Path(subject_db).is_absolute()
            else str((Path(__file__).resolve().parents[1] / subject_db).resolve())
        )
    if word_size is not None:
        payload["word_size"] = int(word_size)
    if perc_identity is not None:
        payload["perc_identity"] = float(perc_identity)
    try:
        response = requests.post(service_url, json=payload, timeout=660)
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        raise ValueError(f"BLAST service request failed: {exc}") from exc

    tabular = str(body.get("tabular_output", "") or "")
    summary_path = ""
    if tabular.strip():
        summary_path = save_text_file(tabular, prefix="blastn_out", suffix=".tsv")

    meta = {
        "hit_count": int(body.get("hit_count", 0)),
        "hits_preview": str(body.get("hits_preview", "")),
        "preview_truncated": bool(body.get("preview_truncated", False)),
        "tabular_output_truncated": bool(body.get("tabular_output_truncated", False)),
        "blastn_command": str(body.get("blastn_command", "")),
        "makeblastdb_command": body.get("makeblastdb_command"),
        "stderr": str(body.get("stderr", ""))[:4000],
        "subject_mode": str(body.get("subject_mode", "")),
        "resolved_query_path": str(body.get("resolved_query_path", query_abs)),
        "resolved_subject": str(body.get("resolved_subject", "")),
        "model": str(body.get("model", "ncbi-blastn")),
        "query_filepath": filepath,
        "tabular_tsv_filepath": summary_path,
    }
    return meta


@tool(args_schema=EvitarDesignInput)
def design_sirna_with_evitar(
    filepath: str,
    mode: str = "existing",
    predict: str = "predsi",
    strains_path: Optional[str] = None,
    off_target: bool = False,
    ncores: int = 1,
    service_url: str = "http://127.0.0.1:8016/design",
) -> dict[str, Any]:
    """Design siRNAs/Cas13 guides via the Evitar microservice.

    Args:
        filepath: Path to an input FASTA file.
            IMPORTANT: pass a filepath rather than embedding long sequence text.
        mode: `existing` or `predesign`.
        predict: Evitar predictor `predsi`, `rnaxs`, or `CRISPR`.
        strains_path: FASTA path required for `existing` mode.
        off_target: Enable Evitar off-target analysis.
        ncores: Number of threads passed through to Evitar.
        service_url: REST endpoint for the Evitar microservice.

    Returns:
        Dict containing output filepath, candidate count, and top rows.

    Raises:
        ValueError: If Evitar service request fails or returns invalid fields.
    """
    request_payload: dict[str, Any] = {
        "input_path": filepath,
        "mode": mode,
        "predict": predict,
        "off_target": bool(off_target),
        "ncores": int(ncores),
    }
    if strains_path:
        request_payload["strains_path"] = strains_path

    try:
        response = requests.post(
            service_url,
            json=request_payload,
            timeout=3600,
        )
        response.raise_for_status()
        payload = response.json()
        required = {"output_path", "result_count", "top_results", "mode", "predict"}
        if not required.issubset(payload):
            raise ValueError(
                "Evitar response is missing required fields: "
                f"{sorted(required - set(payload))}"
            )

        output_path = str(payload["output_path"])
        workspace_output_path = output_path
        try:
            workspace_output_path = copy_file_to_workspace(output_path, prefix="evitar_result", suffix=".txt")
        except OSError:
            workspace_output_path = output_path

        return {
            "input_filepath": filepath,
            "output_filepath": workspace_output_path,
            "raw_output_path": output_path,
            "mode": str(payload["mode"]),
            "predict": str(payload["predict"]),
            "result_count": int(payload.get("result_count", 0)),
            "top_results": payload.get("top_results", []),
            "model": str(payload.get("model", "Evitar")),
            "command": str(payload.get("command", "")),
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
        raise ValueError(f"Evitar service request failed: {exc}{suffix}") from exc


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


@tool(args_schema=SgRNADesignInput)
def design_sgrna_handle_with_crgpt(
    filepath: str,
    n_samples: int = 10,
    mutation_number: int = 22,
    temperature: float = 1.0,
    max_overlap: int = 21,
    device: Optional[str] = None,
    service_url: str = "http://127.0.0.1:8017/design",
) -> dict[str, Any]:
    """Design sgRNA handle candidates through sgrna_design microservice.

    Args:
        filepath: Path to a file containing the seed sgRNA handle sequence.
            IMPORTANT: pass a filepath rather than inline long sequence text.
        n_samples: Number of designed candidates to request.
        mutation_number: Maximum mutation count relative to seed sequence.
        temperature: Sampling temperature for model generation.
        max_overlap: Maximum overlap constraint among candidates.
        device: Optional torch device override such as `cuda:0` or `cpu`.
        service_url: REST endpoint for the sgrna_design microservice.

    Returns:
        Dict containing best candidate summary and artifact filepaths copied into workspace.

    Raises:
        ValueError: If service request fails or response payload is invalid.
    """
    seed_sequence = _normalize_sgrna_design_sequence(read_sequence(filepath))
    request_payload: dict[str, Any] = {
        "seed_sequence": seed_sequence,
        "n_samples": int(n_samples),
        "mutation_number": int(mutation_number),
        "temperature": float(temperature),
        "max_overlap": int(max_overlap),
    }
    if device:
        request_payload["device"] = device

    try:
        response = requests.post(
            service_url,
            json=request_payload,
            timeout=3600,
        )
        response.raise_for_status()
        payload = response.json()
        required = {
            "generated_count",
            "output_fasta_path",
            "summary_json_path",
            "normalized_seed",
            "candidates",
        }
        if not required.issubset(payload):
            raise ValueError(
                "sgRNA design response is missing required fields: "
                f"{sorted(required - set(payload))}"
            )

        output_fasta_path = str(payload["output_fasta_path"])
        summary_json_path = str(payload["summary_json_path"])
        workspace_fasta_path = output_fasta_path
        workspace_summary_path = summary_json_path
        try:
            workspace_fasta_path = copy_file_to_workspace(
                output_fasta_path,
                prefix="sgrna_design_result",
                suffix=".fasta",
            )
        except OSError:
            workspace_fasta_path = output_fasta_path
        try:
            workspace_summary_path = copy_file_to_workspace(
                summary_json_path,
                prefix="sgrna_design_summary",
                suffix=".json",
            )
        except OSError:
            workspace_summary_path = summary_json_path

        candidates = payload.get("candidates", [])
        best_candidate = {}
        if isinstance(candidates, list):
            for candidate in candidates:
                if isinstance(candidate, dict) and str(candidate.get("name", "")).startswith("gen_"):
                    best_candidate = candidate
                    break
            if not best_candidate and candidates and isinstance(candidates[0], dict):
                best_candidate = candidates[0]

        best_sequence = str(best_candidate.get("sequence", ""))
        best_nn_score = float(best_candidate.get("nn_score", 0.0)) if best_candidate else 0.0
        best_mutation_count = int(best_candidate.get("mutation_count", 0)) if best_candidate else 0

        result = {
            "input_filepath": filepath,
            "seed_sequence": seed_sequence,
            "normalized_seed": str(payload.get("normalized_seed", seed_sequence)),
            "generated_count": int(payload.get("generated_count", 0)),
            "best_sequence": best_sequence,
            "best_nn_score": best_nn_score,
            "best_mutation_count": best_mutation_count,
            "output_fasta_filepath": workspace_fasta_path,
            "summary_json_filepath": workspace_summary_path,
            "raw_output_fasta_path": output_fasta_path,
            "raw_summary_json_path": summary_json_path,
            "device": str(payload.get("device", device or "")),
            "model_path": str(payload.get("model_path", "")),
            "has_vienna_rna": bool(payload.get("has_vienna_rna", False)),
            "notes": payload.get("notes", []),
            "model": str(payload.get("model", "sgrna_design_crgpt")),
        }
        if best_sequence:
            result["best_sequence_filepath"] = save_sequence(best_sequence, prefix="sgrna_design_best")
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
        raise ValueError(f"sgRNA design request failed: {exc}{suffix}") from exc


class MrnaToolInput(BaseModel):
    """Input schema for mock mRNA tools."""

    filepath: str = Field(
        ...,
        description="Path to mRNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.",
    )


class CodonwSlimAnalyzeInput(BaseModel):
    """Input schema for codonw-slim CDS codon-usage metrics."""

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace file containing a coding sequence (DNA ATGC or RNA AUGC; "
            "FASTA allowed). Length should be a multiple of three; trailing bases may be trimmed server-side."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8018/analyze/cds",
        description="REST endpoint for the codonw-slim microservice.",
    )
    genetic_code: int = Field(
        default=0,
        ge=0,
        le=7,
        description="Genetic code index passed to CodonSeq (0 = universal nuclear).",
    )
    cai_ref: int = Field(
        default=0,
        ge=0,
        le=2,
        description="Reference index for CAI / CBI (and shared Fop reference family where applicable).",
    )
    fop_ref: int = Field(
        default=0,
        ge=0,
        le=7,
        description="Fop reference species index.",
    )
    factor_in_rare: bool = Field(
        default=False,
        description="If true, pass factor_in_rare=True into CodonSeq.fop().",
    )
    include_codon_tables: bool = Field(
        default=False,
        description="If true, request full codon_usage and rscu tables (larger JSON).",
    )
    include_dinucleotide: bool = Field(
        default=False,
        description="If true, request dinucleotide composition tables.",
    )


class LinearFoldSecondaryInput(BaseModel):
    """Input schema for LinearFold secondary-structure prediction."""

    filepath: str = Field(
        ...,
        description="Path to a workspace file containing RNA sequence (plain or FASTA).",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8015/fold",
        description="REST endpoint for the LinearFold microservice.",
    )
    beam_size: int = Field(
        default=100,
        ge=0,
        le=10000,
        description="Beam size for LinearFold (0 = infinite beam).",
    )
    use_vienna: bool = Field(
        default=False,
        description="If true, request LinearFold-V (Vienna energy parameters).",
    )
    dangles: int = Field(
        default=2,
        description="Dangling-end model: 0 or 2 (LinearFold --dangles).",
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


class LinearDesignCdsInput(BaseModel):
    """Input schema for LinearDesign CDS design tool."""

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace file containing a protein sequence for LinearDesign CDS design. "
            "Do not pass raw sequence text directly."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8014/generate/cds",
        description="REST endpoint for the LinearDesign CDS generation microservice.",
    )
    lambda_value: float = Field(
        default=0.0,
        ge=0.0,
        description="LinearDesign lambda balancing MFE and CAI.",
    )
    codon_usage_path: Optional[str] = Field(
        default=None,
        description="Optional codon usage CSV path passed through to LinearDesign service.",
    )
    verbose: bool = Field(
        default=False,
        description="Whether to enable verbose output in LinearDesign.",
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


class IRESfinderPredictionInput(BaseModel):
    """Input schema for IRESfinder putative IRES scoring."""

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace or repo-relative file containing RNA/DNA sequence or FASTA. "
            "Do not pass raw sequence text directly."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8013/predict",
        description="REST endpoint for the IRESfinder microservice.",
    )
    mode: int = Field(
        default=0,
        ge=0,
        le=2,
        description="0=full sequence, 1=header coordinates, 2=sliding window (see upstream IRESfinder).",
    )
    window_size: int = Field(
        default=174,
        ge=20,
        le=5000,
        description="Sliding-window length for mode 2.",
    )
    step_size: int = Field(
        default=50,
        ge=1,
        le=5000,
        description="Sliding-window step for mode 2.",
    )
    decision_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Probability threshold for labeling a fragment as IRES.",
    )


class ODesignInferenceInput(BaseModel):
    """Input schema for ODesign inference."""

    input_json_filepath: str = Field(
        ...,
        description=(
            "Path to an ODesign input JSON file. Use a workspace filepath or a repo-relative path. "
            "For complex ODesign requests, prefer preparing the JSON first and passing its filepath."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8012/design/from-json",
        description="REST endpoint for the ODesign microservice.",
    )
    infer_model_name: str = Field(
        default="odesign_base_na_rigid",
        description="ODesign model name, for example `odesign_base_na_rigid`.",
    )
    design_modality: str = Field(
        default="rna",
        description="Design modality passed to ODesign, typically `rna` for this project.",
    )
    exp_name: Optional[str] = Field(
        default=None,
        description="Optional experiment name override for the ODesign output directory.",
    )
    seeds_json: str = Field(
        default="[42]",
        description="JSON list string of seeds such as `[42]` or `[42, 123]`.",
    )
    n_sample: int = Field(
        default=1,
        ge=1,
        le=50,
        description="Number of generated samples per seed.",
    )
    use_msa: bool = Field(
        default=False,
        description="Whether ODesign should expect MSA input in the JSON payload.",
    )
    num_workers: int = Field(
        default=2,
        ge=0,
        le=32,
        description="Dataloader worker count passed through to ODesign.",
    )
    cuda_visible_devices: Optional[str] = Field(
        default=None,
        description="Optional CUDA_VISIBLE_DEVICES override such as `0` or `0,1`.",
    )
    enable_partial_diff: bool = Field(
        default=False,
        description="Whether to enable ODesign partial diffusion mode.",
    )
    snr: float = Field(
        default=0.1,
        gt=0.0,
        description="Partial diffusion signal-to-noise ratio passed to ODesign.",
    )
    ckpt_root_dir: Optional[str] = Field(
        default=None,
        description="Optional checkpoint root directory override for the ODesign service.",
    )
    data_root_dir: Optional[str] = Field(
        default=None,
        description="Optional data root directory override for the ODesign service.",
    )


@tool(args_schema=CodonwSlimAnalyzeInput)
def analyze_cds_codon_metrics_with_codonw_slim(
    filepath: str,
    service_url: str = "http://127.0.0.1:8018/analyze/cds",
    genetic_code: int = 0,
    cai_ref: int = 0,
    fop_ref: int = 0,
    factor_in_rare: bool = False,
    include_codon_tables: bool = False,
    include_dinucleotide: bool = False,
) -> dict[str, Any]:
    """Compute codon usage / CAI / Nc (ENC) and related metrics via codonw-slim service.

    Wraps the `codonw-slim` library (CodonW) over HTTP. Input should be a **CDS**
    (in-frame coding sequence); RNA ``U`` is converted to ``T`` server-side.

    Args:
        filepath: Workspace path to CDS sequence (plain or FASTA).
        service_url: codonw_slim_service ``POST /analyze/cds`` URL.
        genetic_code: CodonSeq genetic code index (0--7).
        cai_ref: CAI/CBI reference set index (0--2).
        fop_ref: Fop reference index (0--7).
        factor_in_rare: Rare-codon adjustment flag for Fop.
        include_codon_tables: Request codon counts and RSCU tables.
        include_dinucleotide: Request dinucleotide tables.

    Returns:
        Summary dict including ``cai_score``, ``enc``, ``fop``, ``cbi``, and
        ``metrics_json_filepath`` pointing to a saved JSON artifact in ``workspace/``.
    """
    sequence = read_sequence(filepath)
    payload: dict[str, Any] = {
        "sequence": sequence,
        "genetic_code": genetic_code,
        "cai_ref": cai_ref,
        "fop_ref": fop_ref,
        "factor_in_rare": factor_in_rare,
        "include_codon_tables": include_codon_tables,
        "include_dinucleotide": include_dinucleotide,
    }
    try:
        response = requests.post(service_url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        detail = ""
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            try:
                detail = str(response_obj.json())
            except ValueError:
                detail = response_obj.text
        suffix = f"; detail={detail}" if detail else ""
        raise ValueError(f"codonw-slim service request failed: {exc}{suffix}") from exc

    metrics_json_filepath = save_text_file(
        json.dumps(data, indent=2, ensure_ascii=True),
        prefix="codonw_metrics",
        suffix=".json",
    )
    cai = data.get("cai")
    return {
        "input_filepath": filepath,
        "metrics_json_filepath": metrics_json_filepath,
        "cai_score": float(cai) if cai is not None else 0.0,
        "enc": float(data["enc"]) if data.get("enc") is not None else 0.0,
        "fop": float(data["fop"]) if data.get("fop") is not None else 0.0,
        "cbi": float(data["cbi"]) if data.get("cbi") is not None else 0.0,
        "hydropathy": float(data["hydropathy"]) if data.get("hydropathy") is not None else 0.0,
        "aromaticity": float(data["aromaticity"]) if data.get("aromaticity") is not None else 0.0,
        "genetic_code": int(data.get("genetic_code", genetic_code)),
        "cds_length_nt": int(data.get("cds_length_nt", 0)),
        "cds_length_codons": int(data.get("cds_length_codons", 0)),
        "normalization_note": str(data.get("normalization_note", "")),
        "silent_base_usage": data.get("silent_base_usage", {}),
        "bases2": data.get("bases2", {}),
        "codon_usage": data.get("codon_usage"),
        "rscu": data.get("rscu"),
        "dinuc": data.get("dinuc"),
        "model": str(data.get("model", "codonw-slim")),
    }


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
        backend = payload.get("backend")
        suffix = f"; backend={backend}" if backend else ""
        return (
            f"filepath={filepath}; "
            f"structure={payload['structure']}; "
            f"mfe={payload['mfe']}{suffix}"
        )
    except requests.RequestException as exc:
        raise ValueError(f"ViennaRNA service request failed: {exc}") from exc


def _parse_two_rna_strands_from_file(content: str) -> tuple[str, str]:
    """Parse sense/antisense from a workspace file.

    Supported layouts:
    - Two FASTA records (first record = sense, second = antisense).
    - Two plain lines of RNA (no ``>`` headers): line1 = sense, line2 = antisense.
    """
    text = content.strip()
    if not text:
        raise ValueError("Duplex input file is empty.")
    if ">" in text:
        records: list[tuple[str, str]] = []
        header: Optional[str] = None
        chunks: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None and chunks:
                    seq = _normalize_nucleic_sequence("".join(chunks))
                    records.append((header, seq))
                header = line[1:].strip().split()[0] if len(line) > 1 else "seq"
                chunks = []
            else:
                chunks.append(line)
        if header is not None and chunks:
            seq = _normalize_nucleic_sequence("".join(chunks))
            records.append((header, seq))
        if len(records) < 2:
            raise ValueError("Duplex FASTA must contain at least two records (sense then antisense).")
        return records[0][1], records[1][1]
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise ValueError(
            "Duplex input must be either two FASTA records or two non-empty RNA lines (sense, antisense)."
        )
    s1 = _normalize_nucleic_sequence(lines[0])
    s2 = _normalize_nucleic_sequence(lines[1])
    if len(s1) < 2 or len(s2) < 2:
        raise ValueError("Sense and antisense sequences look too short after normalization.")
    return s1, s2


class SirnaDuplexViennaInput(BaseModel):
    """Input for ViennaRNA siRNA sense/antisense cofold (duplex MFE)."""

    filepath: str = Field(
        ...,
        description=(
            "Workspace file with two FASTA records (sense then antisense) "
            "or two plain RNA lines without headers."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8003/sirna-duplex",
        description="REST endpoint for ViennaRNA duplex cofold.",
    )


class AsoAccessibilityViennaInput(BaseModel):
    """Input for RNAplfold-based accessibility on a target region."""

    filepath: str = Field(..., description="Workspace file with full target RNA sequence (plain or FASTA).")
    region_start: int = Field(..., ge=1, description="1-based inclusive ASO / binding region start on target RNA.")
    region_end: int = Field(..., ge=1, description="1-based inclusive region end.")
    service_url: str = Field(
        default="http://127.0.0.1:8003/aso-accessibility",
        description="REST endpoint for RNAplfold accessibility.",
    )
    aso_oligo_length: int = Field(
        default=18,
        ge=1,
        le=500,
        description="ASO length (nt) used for joint unpaired stretch probability.",
    )
    winsize: int = Field(default=70, ge=3, le=800, description="RNAplfold window size -W.")
    span: int = Field(default=70, ge=2, le=800, description="RNAplfold max pair span -L.")
    unpaired_ulength: int = Field(default=25, ge=1, le=500, description="RNAplfold -u upper bound (auto-expanded server-side).")
    temp_c: float = Field(default=37.0, description="Temperature in Celsius.")


class InverseFoldViennaInput(BaseModel):
    """Input for RNAinverse secondary-structure inverse folding."""

    filepath: str = Field(
        ...,
        description="Workspace file: first non-empty line = dot-bracket structure; optional second line = IUPAC start hint.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8003/inverse-fold",
        description="REST endpoint for ViennaRNA inverse fold.",
    )
    repeats: int = Field(default=1, ge=1, le=500, description="RNAinverse repeat searches (-R).")
    temp_c: float = Field(default=37.0, description="Temperature in Celsius.")
    function_mode: str = Field(
        default="m",
        description="RNAinverse -F: m (MFE target), p (partition), or mp.",
    )


@tool(args_schema=SirnaDuplexViennaInput)
def compute_sirna_duplex_binding_vienna(
    filepath: str,
    service_url: str = "http://127.0.0.1:8003/sirna-duplex",
) -> dict[str, Any]:
    """Compute siRNA sense/antisense duplex MFE via ViennaRNA (RNAcofold / RNAlib).

    Args:
        filepath: File with two FASTA records (sense then antisense) or two RNA lines.
        service_url: ViennaRNA fold microservice duplex endpoint.

    Returns:
        Dict with sense/antisense, cofold structure, mfe (kcal/mol), backend, and input path.
    """
    raw = read_sequence(filepath)
    sense, antisense = _parse_two_rna_strands_from_file(raw)
    try:
        response = requests.post(
            service_url,
            json={"sense": sense, "antisense": antisense},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ValueError(f"ViennaRNA duplex service request failed: {exc}") from exc
    if "mfe" not in payload or "structure" not in payload:
        raise ValueError("Invalid duplex response: expected `mfe` and `structure`.")
    return {
        "input_filepath": filepath,
        "sense": str(payload.get("sense", sense)),
        "antisense": str(payload.get("antisense", antisense)),
        "cofold_sequence": str(payload.get("cofold_sequence", "")),
        "structure": str(payload["structure"]),
        "mfe_kcal_per_mol": float(payload["mfe"]),
        "backend": str(payload.get("backend", "")),
        "model": str(payload.get("model", "ViennaRNA-RNAcofold")),
    }


@tool(args_schema=AsoAccessibilityViennaInput)
def compute_aso_target_accessibility_vienna(
    filepath: str,
    region_start: int,
    region_end: int,
    service_url: str = "http://127.0.0.1:8003/aso-accessibility",
    aso_oligo_length: int = 18,
    winsize: int = 70,
    span: int = 70,
    unpaired_ulength: int = 25,
    temp_c: float = 37.0,
) -> dict[str, Any]:
    """Estimate target mRNA local accessibility (RNAplfold) for an ASO binding region.

    Args:
        filepath: Full-length target RNA sequence file (plain or FASTA).
        region_start: 1-based inclusive start of the binding site on the target.
        region_end: 1-based inclusive end.
        service_url: ViennaRNA microservice accessibility endpoint.
        aso_oligo_length: ASO length used for joint unpaired probability at region end.
        winsize, span, unpaired_ulength: RNAplfold parameters (-W, -L, -u).
        temp_c: Folding temperature (Celsius).

    Returns:
        Summary dict including mean single-nucleotide unpaired probabilities in the region
        and joint unpaired probability for a contiguous stretch (when computable).
    """
    sequence_text = read_sequence(filepath)
    try:
        response = requests.post(
            service_url,
            json={
                "sequence": sequence_text,
                "region_start": region_start,
                "region_end": region_end,
                "aso_oligo_length": aso_oligo_length,
                "winsize": winsize,
                "span": span,
                "unpaired_ulength": unpaired_ulength,
                "temp_c": temp_c,
            },
            timeout=600,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ValueError(f"ViennaRNA accessibility service request failed: {exc}") from exc
    return {
        "input_filepath": filepath,
        "sequence_length": int(payload.get("sequence_length", 0)),
        "region_start": int(payload.get("region_start", region_start)),
        "region_end": int(payload.get("region_end", region_end)),
        "mean_unpaired_prob_single_nt": payload.get("mean_unpaired_prob_single_nt"),
        "joint_unpaired_prob_stretch_ending_at_region_end": payload.get(
            "joint_unpaired_prob_stretch_ending_at_region_end"
        ),
        "aso_oligo_length_used": int(payload.get("aso_oligo_length_used", aso_oligo_length)),
        "plfold_winsize": int(payload.get("winsize", winsize)),
        "plfold_span": int(payload.get("span", span)),
        "plfold_unpaired_ulength": int(payload.get("unpaired_ulength", unpaired_ulength)),
        "backend": str(payload.get("backend", "")),
        "model": str(payload.get("model", "ViennaRNA-RNAplfold")),
    }


@tool(args_schema=InverseFoldViennaInput)
def inverse_fold_rna_secondary_structure_vienna(
    filepath: str,
    service_url: str = "http://127.0.0.1:8003/inverse-fold",
    repeats: int = 1,
    temp_c: float = 37.0,
    function_mode: str = "m",
) -> dict[str, Any]:
    """Inverse-fold an RNA secondary structure to a sequence (ViennaRNA RNAinverse).

    Args:
        filepath: First non-empty line: target dot-bracket; optional second line: IUPAC start (N = random).
        service_url: ViennaRNA inverse-fold endpoint.
        repeats: Number of RNAinverse search repeats.
        temp_c: Temperature in Celsius.
        function_mode: RNAinverse objective: m, p, or mp.

    Returns:
        Dict with best_sequence, optional hamming_distance, structure, backend.
    """
    raw = read_sequence(filepath)
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("Inverse-fold input file is empty.")
    structure = lines[0]
    start_sequence = lines[1] if len(lines) > 1 else ""
    try:
        response = requests.post(
            service_url,
            json={
                "structure": structure,
                "start_sequence": start_sequence,
                "repeats": repeats,
                "temp_c": temp_c,
                "function_mode": function_mode,
            },
            timeout=300,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ValueError(f"ViennaRNA inverse-fold request failed: {exc}") from exc
    if "best_sequence" not in payload:
        raise ValueError("Invalid inverse-fold response: missing `best_sequence`.")
    out = {
        "input_filepath": filepath,
        "target_structure": str(payload.get("structure", structure)),
        "best_sequence": str(payload["best_sequence"]),
        "hamming_distance": payload.get("hamming_distance"),
        "backend": str(payload.get("backend", "")),
        "model": str(payload.get("model", "ViennaRNA-RNAinverse")),
    }
    best_fp = save_sequence(str(payload["best_sequence"]), prefix="vienna_inverse")
    out["best_sequence_filepath"] = best_fp
    return out


@tool(args_schema=LinearFoldSecondaryInput)
def predict_rna_secondary_structure_with_linearfold(
    filepath: str,
    service_url: str = "http://127.0.0.1:8015/fold",
    beam_size: int = 100,
    use_vienna: bool = False,
    dangles: int = 2,
) -> dict[str, Any]:
    """Predict RNA secondary structure and MFE using the LinearFold service.

    Args:
        filepath: Workspace file path containing RNA sequence content.
        service_url: REST endpoint for the LinearFold fold microservice.
        beam_size: LinearFold beam size (default 100).
        use_vienna: Use LinearFold-V (Vienna parameters) when True.
        dangles: 0 or 2 for dangling-end treatment.

    Returns:
        Dict with sequence, structure, mfe, backend, model, and input filepath.

    Raises:
        ValueError: If the LinearFold request fails or the response is invalid.
    """
    sequence = read_sequence(filepath).strip()
    if dangles not in (0, 2):
        raise ValueError("LinearFold dangles must be 0 or 2.")
    try:
        response = requests.post(
            service_url,
            json={
                "sequence": sequence,
                "beam_size": beam_size,
                "use_vienna": use_vienna,
                "dangles": dangles,
            },
            timeout=600,
        )
        response.raise_for_status()
        payload = response.json()
        if "structure" not in payload or "mfe" not in payload:
            raise ValueError("Missing `structure` or `mfe` in LinearFold response.")
        return {
            "filepath": filepath,
            "sequence": str(payload.get("sequence", "")),
            "structure": str(payload["structure"]),
            "mfe": float(payload["mfe"]),
            "backend": str(payload.get("backend", "")),
            "model": str(payload.get("model", "LinearFold")),
        }
    except requests.RequestException as exc:
        raise ValueError(f"LinearFold service request failed: {exc}") from exc


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


@tool(args_schema=LinearDesignCdsInput)
def design_mrna_cds_with_lineardesign(
    filepath: str,
    service_url: str = "http://127.0.0.1:8014/generate/cds",
    lambda_value: float = 0.0,
    codon_usage_path: Optional[str] = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Design an mRNA CDS sequence from a protein sequence using LinearDesign.

    Args:
        filepath: Workspace file path containing the input protein sequence.
            IMPORTANT: You must pass a workspace filepath, not the sequence itself.
        service_url: REST endpoint for the LinearDesign microservice.
        lambda_value: LinearDesign lambda hyperparameter balancing MFE and CAI.
        codon_usage_path: Optional codon usage table path.
        verbose: Whether to enable verbose output in the LinearDesign backend.

    Returns:
        Dict containing the generated CDS sequence, structure/MFE/CAI summaries, and workspace filepath.

    Raises:
        ValueError: If the LinearDesign service is unreachable or returns an invalid payload.
    """
    protein_sequence = read_sequence(filepath).strip()
    try:
        request_payload: dict[str, Any] = {
            "protein_sequence": protein_sequence,
            "lambda_value": lambda_value,
            "verbose": verbose,
        }
        if codon_usage_path:
            request_payload["codon_usage_path"] = codon_usage_path

        response = requests.post(
            service_url,
            json=request_payload,
            timeout=300,
        )
        response.raise_for_status()
        payload = response.json()
        if "generated_sequence" not in payload:
            raise ValueError("Missing `generated_sequence` in LinearDesign response.")
        output_filepath = save_sequence(payload["generated_sequence"], prefix="lineardesign_cds")
        return {
            "input_filepath": filepath,
            "output_filepath": output_filepath,
            "generated_sequence": payload["generated_sequence"],
            "structure": payload.get("structure", ""),
            "mfe": float(payload.get("mfe", 0.0)),
            "cai_score": float(payload.get("cai_score", 0.0)),
            "lambda_value": float(payload.get("lambda_value", lambda_value)),
            "codon_usage_path": payload.get("codon_usage_path", codon_usage_path or ""),
            "raw_output": payload.get("raw_output", ""),
            "model": payload.get("model", "LinearDesign"),
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
        raise ValueError(f"LinearDesign service request failed: {exc}{suffix}") from exc


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


@tool(args_schema=IRESfinderPredictionInput)
def predict_putative_ires_with_iresfinder(
    filepath: str,
    service_url: str = "http://127.0.0.1:8013/predict",
    mode: int = 0,
    window_size: int = 174,
    step_size: int = 50,
    decision_threshold: float = 0.5,
) -> dict[str, Any]:
    """Score RNA sequence fragments for putative internal ribosome entry sites (IRES) via IRESfinder.

    Args:
        filepath: Path to a file containing plain sequence or FASTA records.
        service_url: REST endpoint for the IRESfinder microservice.
        mode: IRESfinder mode (0=full sequence, 1=coordinate header, 2=sliding window).
        window_size: Window length when ``mode`` is 2.
        step_size: Step size when ``mode`` is 2.
        decision_threshold: Probability cutoff for IRES vs non-IRES labels.

    Returns:
        Summary metrics, a bounded list of per-fragment scores, and a workspace copy of the TSV.

    Raises:
        ValueError: If the service is unreachable or returns an invalid payload.
    """
    fasta_content = read_sequence(filepath).strip()
    if not fasta_content:
        raise ValueError("IRESfinder input file is empty.")

    try:
        request_payload: dict[str, Any] = {
            "fasta_content": fasta_content,
            "mode": int(mode),
            "window_size": int(window_size),
            "step_size": int(step_size),
            "decision_threshold": float(decision_threshold),
        }
        response = requests.post(
            service_url,
            json=request_payload,
            timeout=1800,
        )
        response.raise_for_status()
        payload = response.json()
        required = {
            "fragment_count",
            "positive_count",
            "has_putative_ires",
            "best_fragment_id",
            "max_score",
            "predictions",
        }
        if not required.issubset(payload):
            raise ValueError(
                "IRESfinder response is missing required fields: "
                f"{sorted(required - set(payload))}"
            )

        raw_tsv = str(payload.get("result_tsv_path", "")).strip()
        workspace_tsv = ""
        if raw_tsv:
            try:
                workspace_tsv = copy_file_to_workspace(raw_tsv, prefix="iresfinder_result", suffix=".tsv")
            except OSError:
                workspace_tsv = raw_tsv

        predictions = payload.get("predictions", [])
        if isinstance(predictions, list) and len(predictions) > 80:
            predictions_trimmed = predictions[:80]
            predictions_note = f"trimmed_to_first_80_of_{len(predictions)}"
        else:
            predictions_trimmed = predictions
            predictions_note = ""

        return {
            "input_filepath": filepath,
            "result_tsv_filepath": workspace_tsv or raw_tsv,
            "mode": int(payload.get("mode", mode)),
            "window_size": int(payload.get("window_size", window_size)),
            "step_size": int(payload.get("step_size", step_size)),
            "decision_threshold": float(payload.get("decision_threshold", decision_threshold)),
            "fragment_count": int(payload["fragment_count"]),
            "positive_count": int(payload["positive_count"]),
            "has_putative_ires": bool(payload["has_putative_ires"]),
            "best_fragment_id": str(payload["best_fragment_id"]),
            "max_score": float(payload["max_score"]),
            "model": str(payload.get("model", "IRESfinder-logreg-py3")),
            "predictions": predictions_trimmed,
            "predictions_note": predictions_note,
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
        raise ValueError(f"IRESfinder service request failed: {exc}{suffix}") from exc


@tool(args_schema=ODesignInferenceInput)
def run_odesign_inference(
    input_json_filepath: str,
    service_url: str = "http://127.0.0.1:8012/design/from-json",
    infer_model_name: str = "odesign_base_na_rigid",
    design_modality: str = "rna",
    exp_name: Optional[str] = None,
    seeds_json: str = "[42]",
    n_sample: int = 1,
    use_msa: bool = False,
    num_workers: int = 2,
    cuda_visible_devices: Optional[str] = None,
    enable_partial_diff: bool = False,
    snr: float = 0.1,
    ckpt_root_dir: Optional[str] = None,
    data_root_dir: Optional[str] = None,
) -> dict[str, Any]:
    """Run ODesign inference from an input JSON file via the ODesign microservice.

    Args:
        input_json_filepath: Path to an ODesign input JSON file.
            IMPORTANT: pass a filepath rather than embedding long JSON content inline.
        service_url: REST endpoint for the ODesign microservice.
        infer_model_name: ODesign model name such as `odesign_base_na_rigid`.
        design_modality: ODesign modality such as `rna`, `dna`, `protein`, or `ligand`.
        exp_name: Optional experiment name override.
        seeds_json: JSON list string of seeds.
        n_sample: Number of generated samples per seed.
        use_msa: Whether to enable MSA mode.
        num_workers: Dataloader worker count.
        cuda_visible_devices: Optional CUDA_VISIBLE_DEVICES override.
        enable_partial_diff: Whether to enable ODesign partial diffusion mode.
        snr: Partial diffusion signal-to-noise ratio.
        ckpt_root_dir: Optional checkpoint root directory override for the service.
        data_root_dir: Optional data root directory override for the service.

    Returns:
        Dict with copied workspace artifacts, output metadata, and ODesign runtime info.

    Raises:
        ValueError: If the ODesign service is unreachable or returns an invalid payload.
    """
    try:
        request_payload: dict[str, Any] = {
            "input_json_path": input_json_filepath,
            "infer_model_name": infer_model_name,
            "design_modality": design_modality,
            "seeds_json": seeds_json,
            "n_sample": n_sample,
            "use_msa": use_msa,
            "num_workers": num_workers,
            "enable_partial_diff": enable_partial_diff,
            "snr": snr,
        }
        if exp_name:
            request_payload["exp_name"] = exp_name
        if cuda_visible_devices:
            request_payload["cuda_visible_devices"] = cuda_visible_devices
        if ckpt_root_dir:
            request_payload["ckpt_root_dir"] = ckpt_root_dir
        if data_root_dir:
            request_payload["data_root_dir"] = data_root_dir

        response = requests.post(
            service_url,
            json=request_payload,
            timeout=21600,
        )
        response.raise_for_status()
        payload = response.json()
        if "output_dir" not in payload or "prediction_filepaths" not in payload:
            raise ValueError(
                "Missing `output_dir` or `prediction_filepaths` in ODesign response."
            )

        copied_prediction_paths = [
            copy_file_to_workspace(str(path), prefix="odesign_prediction")
            for path in payload.get("prediction_filepaths", [])
        ]
        copied_error_paths = [
            copy_file_to_workspace(str(path), prefix="odesign_error", suffix=".txt")
            for path in payload.get("error_filepaths", [])
        ]

        result: dict[str, Any] = {
            "input_json_filepath": input_json_filepath,
            "infer_model_name": payload.get("infer_model_name", infer_model_name),
            "design_modality": payload.get("design_modality", design_modality),
            "exp_name": payload.get("exp_name", exp_name or ""),
            "output_dir": payload.get("output_dir", ""),
            "prediction_count": len(copied_prediction_paths),
            "prediction_filepaths": copied_prediction_paths,
            "sample_names": payload.get("sample_names", []),
            "ckpt_root_dir": payload.get("ckpt_root_dir", ckpt_root_dir or ""),
            "data_root_dir": payload.get("data_root_dir", data_root_dir or ""),
            "model": payload.get("model", "ODesign"),
        }

        run_log_path = payload.get("run_log_path")
        if run_log_path:
            result["run_log_filepath"] = copy_file_to_workspace(
                str(run_log_path),
                prefix="odesign_runlog",
                suffix=".log",
            )
        if copied_error_paths:
            result["error_filepaths"] = copied_error_paths
        if payload.get("stdout"):
            result["stdout_filepath"] = save_text_file(
                str(payload["stdout"]),
                prefix="odesign_stdout",
                suffix=".log",
            )
        if payload.get("stderr"):
            result["stderr_filepath"] = save_text_file(
                str(payload["stderr"]),
                prefix="odesign_stderr",
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
        raise ValueError(f"ODesign service request failed: {exc}{suffix}") from exc
