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



def _raise_service_error(exc: requests.RequestException, service_name: str) -> None:
    """Extract response detail from a requests exception and raise ValueError."""
    detail = ""
    response_obj = getattr(exc, "response", None)
    if response_obj is not None:
        try:
            detail = str(response_obj.json())
        except ValueError:
            detail = response_obj.text
    suffix = f"; detail={detail}" if detail else ""
    raise ValueError(f"{service_name} service request failed: {exc}{suffix}") from exc


def _attach_service_logs(
    result: dict[str, Any],
    payload: dict[str, Any],
    prefix: str,
) -> None:
    """Copy stdout/stderr from a service response into workspace log files.

    Adds ``{prefix}_stdout_filepath`` and ``{prefix}_stderr_filepath`` keys to
    *result* when the corresponding fields are present in *payload*.
    """
    if payload.get("stdout"):
        result[f"{prefix}_stdout_filepath"] = save_text_file(
            str(payload["stdout"]),
            prefix=f"{prefix}_stdout",
            suffix=".log",
        )
    if payload.get("stderr"):
        result[f"{prefix}_stderr_filepath"] = save_text_file(
            str(payload["stderr"]),
            prefix=f"{prefix}_stderr",
            suffix=".log",
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


# ═══════════════════════════════════════════════════════════════════════════════
# Evitar INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 design_sirna_with_evitar 的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

class EvitarDesignInput(BaseModel):
    """Input schema for Evitar siRNA/Cas13 design tool.

    Maps to the upstream Evitar Perl CLI (`external_repos/Evitar/Evitar.pl`).
    All optional fields default to None / False so the upstream defaults are used.

    Deployment notes:
        - CRISPR mode requires R (>=3.4) runtime on the server.
        - Off-target analysis requires user-provided transcriptome / 3'UTR FASTA.
        - Tissue-specific weights are available under Evitar/GenomeData/weightedgene/.
    """

    filepath: str = Field(
        ...,
        description="Path to input FASTA file in workspace or repo-relative path.",
    )
    mode: str = Field(
        default="existing",
        description="Evitar mode: `existing` (single/few-virus design) or `predesign` (future-virus design).",
    )
    predict: str = Field(
        default="predsi",
        description="Evitar predict option: `predsi`, `rnaxs`, `CRISPR`, or `multifapredsi`.",
    )
    strains_path: Optional[str] = Field(
        default=None,
        description="FASTA path with multiple strains. Optional for single-virus existing mode; useful for cross-strain coverage.",
    )
    off_target: bool = Field(
        default=False,
        description="Enable Evitar off-target pipeline.",
    )
    ncores: int = Field(
        default=1,
        ge=1,
        le=128,
        description="Number of threads for Evitar.",
    )
    # ── Off-target analysis files ──
    p3utr_path: Optional[str] = Field(
        default=None,
        description="FASTA file of 3'UTR regions of the transcriptome (required when off_target=True).",
    )
    transcriptome_path: Optional[str] = Field(
        default=None,
        description="FASTA file of the transcriptome (required when off_target=True).",
    )
    weight_path: Optional[str] = Field(
        default=None,
        description="Gene-weight file for tissue-specific off-target evaluation (three columns: ENSEMBL ID, Gene Symbol, weight).",
    )
    # ── Summary / selection parameters (predesign mode) ──
    sumtype: Optional[str] = Field(
        default=None,
        description="Selection algorithm for predesign mode: `SGAR` (default upstream) or `greedy`.",
    )
    limitnum: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of siRNAs/Cas13 gRNAs to output in predesign mode. Default upstream is 50.",
    )
    repeatnum: Optional[int] = Field(
        default=None,
        ge=1,
        description="Multi-siRNA penalty factor for predesign mode. Default upstream is 2.",
    )
    # ── Off-target cutoffs ──
    pmcuff: Optional[int] = Field(
        default=None,
        ge=0,
        description="Perfect-match off-target cutoff. Default upstream is 1.",
    )
    umcuff: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Imperfect-match off-target score cutoff. Default upstream is 20.",
    )
    mircuff: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="miRNA-like off-target score cutoff. Default upstream is 20000.",
    )
    # ── GC-content filters ──
    maxgc: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximal GC-content cutoff for siRNA prediction. Default upstream is 0.6.",
    )
    mingc: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimal GC-content cutoff for siRNA prediction. Default upstream is 0.25.",
    )
    middlegc: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Middle GC-content cutoff (suboptimal threshold). Default upstream is 0.55.",
    )
    # ── Allow / Ban lists ──
    allow_path: Optional[str] = Field(
        default=None,
        description="Text file (one sequence per line, no header) of experimentally verified siRNAs to force-include.",
    )
    ban_path: Optional[str] = Field(
        default=None,
        description="Text file (one sequence per line, no header) of siRNAs to exclude.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8016/design",
        description="REST endpoint for the Evitar microservice.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CRISOT INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 CRISOT ToolSpec 注册区域的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

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
        default="G0",
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
        default="G0",
        description="Cas-OFFinder device flag such as `C` or `G0`.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8011/optimize",
        description="REST endpoint for the CRISOT optimization microservice.",
    )


class CrisotScoresInput(BaseModel):
    """Input schema for CRISOT batch score prediction from a CSV file."""

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
        default="http://127.0.0.1:8011/scores",
        description="REST endpoint for the CRISOT batch scoring microservice.",
    )


class CrisotRescoreInput(BaseModel):
    """Input schema for CRISOT genome-wide rescore and reranking of sgRNAs."""

    txt_filepath: str = Field(
        ...,
        description="Path to a TXT file containing one sgRNA sequence per line.",
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
        default="G0",
        description="Cas-OFFinder device flag such as `C` or `G0`.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8011/rescore",
        description="REST endpoint for the CRISOT rescore microservice.",
    )


class CrisotFpInput(BaseModel):
    """Input schema for CRISOT-FP XGBoost off-target prediction."""

    csv_filepath: str = Field(
        ...,
        description="Path to a CSV file containing sgRNA and off-target sequences.",
    )
    xgb_model: str = Field(
        default="Circle-seq",
        description="XGBoost model name: Circle-seq, Site-seq, or Change-seq.",
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
        default="http://127.0.0.1:8011/crisot-fp",
        description="REST endpoint for the CRISOT-FP microservice.",
    )


class CrisotGenFpInput(BaseModel):
    """Input schema for CRISOT-FP fingerprint encoding generation."""

    sgrna: str = Field(
        ...,
        description="sgRNA sequence for fingerprint generation. Expected length is 23 nt.",
    )
    target_sequence: str = Field(
        ...,
        description="Target DNA sequence for fingerprint generation. Expected length is 23 nt.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8011/gen-fp",
        description="REST endpoint for the CRISOT-FP encoding microservice.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# sgrna_design INTERFACE LOCK (v0.3.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 design_sgrna_handle_with_crgpt 的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

class SgRNADesignInput(BaseModel):
    """Input schema for sgRNA handle design via sgrna_design_service.

    INTERFACE LOCK (v0.3.0): Locked schema. Modify only in sync with:
    - microservices/sgrna_design_service/main.py :: DesignRequest
    - agent_core/tool_specs.py :: design_sgrna_handle_with_crgpt ToolSpec
    - agent_core/state.py :: sgrna_design_* fields
    - agent_core/nodes.py :: _resolve_sgrna_design_request
    - docs/tools/design_sgrna_handle_with_crgpt.md
    """

    seed_sequence: Optional[str] = Field(
        default=None,
        description="Inline seed/wildtype sgRNA handle sequence (DNA/RNA). Either this or filepath must be provided.",
    )
    filepath: Optional[str] = Field(
        default=None,
        description="Path to a workspace or repo-relative file containing sgRNA handle seed sequence. Either this or seed_sequence must be provided.",
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
    temperature: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=100.0,
        description="MCMC annealing temperature (mcmc mode, default 20.0) or transformer sampling temperature (naive mode, default 1.0).",
    )
    max_length: Optional[int] = Field(
        default=None,
        ge=1,
        le=120,
        description="Optional target sequence length for naive mode (overrides auto-computed max_new_tokens).",
    )
    max_overlap: int = Field(
        default=21,
        ge=1,
        le=60,
        description="Maximum longest-common-substring overlap among accepted candidates.",
    )
    sampling_mode: str = Field(
        default="mcmc",
        description="Sampling strategy: 'mcmc' (original MCMC/annealing) or 'naive' (direct model.generate).",
    )
    path_to_model: Optional[str] = Field(
        default=None,
        description="Optional model directory (relative to sgrna_design root or absolute path).",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device override such as `cuda:0` or `cpu`.",
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Optional output directory override for the microservice.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8017/design",
        description="REST endpoint for sgRNA design microservice.",
    )


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
        _raise_service_error(exc, "BLAST")

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


class RnaGcContentInput(BaseModel):
    """Input schema for RNA/DNA GC fraction (microservice on port 8020)."""

    filepath: str = Field(
        ...,
        description="Path to RNA or DNA sequence (workspace or server absolute); FASTA or plain text.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8020/gc-content",
        description="POST endpoint for GC content microservice.",
    )


class DotBracketUnpairedFractionInput(BaseModel):
    """Input schema for dot-bracket unpaired '.' fraction (microservice on port 8020)."""

    filepath: str = Field(
        ...,
        description="Path to dot-bracket secondary structure (first structural line used; FASTA header skipped).",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8020/unpaired-fraction",
        description="POST endpoint for unpaired-fraction microservice.",
    )


@tool(args_schema=RnaGcContentInput)
def compute_rna_sequence_gc_content(
    filepath: str,
    service_url: str = "http://127.0.0.1:8020/gc-content",
) -> dict[str, Any]:
    """Compute (G+C)/N for an RNA or DNA sequence file (N = count of A/U/G/C after normalization).

    Requires ``rna_sequence_metrics_service`` on port 8020. Pass a filepath under ``workspace/`` or an
    absolute server path; long sequences should not be pasted into the chat.

    Args:
        filepath: Sequence file (plain or FASTA); T is treated as U, non-letters removed.
        service_url: POST ``/gc-content`` endpoint.

    Returns:
        Dict with ``gc_content``, counts, and resolved paths.

    Raises:
        ValueError: If the HTTP call fails or the service reports an error.
    """
    read_sequence(filepath)
    seq_abs = _absolute_path_under_project(filepath)
    try:
        response = requests.post(
            service_url,
            json={"sequence_filepath": seq_abs},
            timeout=120,
        )
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        _raise_service_error(exc, "RNA sequence metrics (GC)")
    return {
        "input_filepath": filepath,
        "resolved_filepath": str(body.get("resolved_filepath", "")),
        "sequence_length": int(body.get("sequence_length", 0)),
        "g_count": int(body.get("g_count", 0)),
        "c_count": int(body.get("c_count", 0)),
        "gc_count": int(body.get("gc_count", 0)),
        "gc_content": float(body.get("gc_content", 0.0)),
        "model": str(body.get("model", "rna-sequence-metrics-gc")),
    }


@tool(args_schema=DotBracketUnpairedFractionInput)
def compute_dot_bracket_unpaired_fraction(
    filepath: str,
    service_url: str = "http://127.0.0.1:8020/unpaired-fraction",
) -> dict[str, Any]:
    """Fraction of unpaired bases in a dot-bracket RNA secondary structure: count('.')/length.

    The structure string must use only ``. ( ) [ ] { } < >`` as in ViennaRNA / LinearFold dot-bracket
    notation. Requires ``rna_sequence_metrics_service`` on port 8020.

    Args:
        filepath: Text file containing the structure (FASTA with structure on sequence line is ok).
        service_url: POST ``/unpaired-fraction`` endpoint.

    Returns:
        Dict with ``unpaired_fraction``, ``dot_count``, ``structure_length``, and paths.

    Raises:
        ValueError: If the HTTP call fails or the structure contains invalid characters.
    """
    read_sequence(filepath)
    struct_abs = _absolute_path_under_project(filepath)
    try:
        response = requests.post(
            service_url,
            json={"structure_filepath": struct_abs},
            timeout=120,
        )
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        _raise_service_error(exc, "RNA sequence metrics (unpaired fraction)")
    return {
        "input_filepath": filepath,
        "resolved_filepath": str(body.get("resolved_filepath", "")),
        "structure_length": int(body.get("structure_length", 0)),
        "dot_count": int(body.get("dot_count", 0)),
        "unpaired_fraction": float(body.get("unpaired_fraction", 0.0)),
        "model": str(body.get("model", "rna-sequence-metrics-unpaired")),
    }


@tool(args_schema=EvitarDesignInput)
def design_sirna_with_evitar(
    filepath: str,
    mode: str = "existing",
    predict: str = "predsi",
    strains_path: Optional[str] = None,
    off_target: bool = False,
    ncores: int = 1,
    p3utr_path: Optional[str] = None,
    transcriptome_path: Optional[str] = None,
    weight_path: Optional[str] = None,
    sumtype: Optional[str] = None,
    limitnum: Optional[int] = None,
    repeatnum: Optional[int] = None,
    pmcuff: Optional[int] = None,
    umcuff: Optional[float] = None,
    mircuff: Optional[float] = None,
    maxgc: Optional[float] = None,
    mingc: Optional[float] = None,
    middlegc: Optional[float] = None,
    allow_path: Optional[str] = None,
    ban_path: Optional[str] = None,
    service_url: str = "http://127.0.0.1:8016/design",
) -> dict[str, Any]:
    """Design siRNAs/Cas13 guides via the Evitar microservice.

    INTERFACE LOCK (v0.2.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: EvitarDesignOutput / design_sirna_with_evitar ToolSpec
    - agent_core/state.py :: evitar_* fields
    - agent_core/nodes.py :: _build_evitar_tool_args / tool_execution_node Evitar branch
    - microservices/evitar_service/main.py :: EvitarDesignRequest / EvitarDesignResponse
    - docs/tools/design_sirna_with_evitar.md

    Args:
        filepath: Path to an input FASTA file.
            IMPORTANT: pass a filepath rather than embedding long sequence text.
        mode: `existing` (single/few-virus) or `predesign` (future-virus).
        predict: Evitar predictor: `predsi`, `rnaxs`, `CRISPR`, or `multifapredsi`.
            NOTE: `CRISPR` requires R (>=3.4) installed on the server.
        strains_path: FASTA path with multiple strains (optional for single-virus existing mode).
        off_target: Enable Evitar off-target analysis.
            NOTE: meaningful results require real transcriptome / 3'UTR FASTA files.
        ncores: Number of threads passed through to Evitar.
        p3utr_path: 3'UTR FASTA for off-target evaluation.
        transcriptome_path: Transcriptome FASTA for off-target evaluation.
        weight_path: Gene-weight file for tissue-specific off-target scoring.
            NOTE: run GenomeData.sh to generate transcripts.fa / utrs.fa if missing.
        sumtype: Selection algorithm for predesign: `SGAR` or `greedy`.
        limitnum: Max siRNAs/Cas13 gRNAs to output in predesign mode.
        repeatnum: Multi-siRNA penalty factor for predesign mode.
        pmcuff: Perfect-match off-target cutoff.
        umcuff: Imperfect-match off-target score cutoff.
        mircuff: miRNA-like off-target score cutoff.
        maxgc: Maximal GC-content cutoff.
        mingc: Minimal GC-content cutoff.
        middlegc: Middle GC-content cutoff (suboptimal threshold).
        allow_path: File of verified siRNAs to force-include.
        ban_path: File of siRNAs to exclude.
        service_url: REST endpoint for the Evitar microservice.

    Returns:
        Dict containing output filepath, candidate count, top rows, and echoed
        upstream parameters for auditability.

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
    if p3utr_path:
        request_payload["p3utr_path"] = p3utr_path
    if transcriptome_path:
        request_payload["transcriptome_path"] = transcriptome_path
    if weight_path:
        request_payload["weight_path"] = weight_path
    if sumtype:
        request_payload["sumtype"] = sumtype
    if limitnum is not None:
        request_payload["limitnum"] = limitnum
    if repeatnum is not None:
        request_payload["repeatnum"] = repeatnum
    if pmcuff is not None:
        request_payload["pmcuff"] = pmcuff
    if umcuff is not None:
        request_payload["umcuff"] = umcuff
    if mircuff is not None:
        request_payload["mircuff"] = mircuff
    if maxgc is not None:
        request_payload["maxgc"] = maxgc
    if mingc is not None:
        request_payload["mingc"] = mingc
    if middlegc is not None:
        request_payload["middlegc"] = middlegc
    if allow_path:
        request_payload["allow_path"] = allow_path
    if ban_path:
        request_payload["ban_path"] = ban_path

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
            # Echo upstream parameters back for auditability / state tracking
            "strains_path": str(strains_path or ""),
            "off_target": bool(off_target),
            "p3utr_path": str(p3utr_path or ""),
            "transcriptome_path": str(transcriptome_path or ""),
            "weight_path": str(weight_path or ""),
            "sumtype": str(sumtype or ""),
            "limitnum": int(limitnum) if limitnum is not None else 0,
            "repeatnum": int(repeatnum) if repeatnum is not None else 0,
            "pmcuff": int(pmcuff) if pmcuff is not None else 0,
            "umcuff": float(umcuff) if umcuff is not None else 0.0,
            "mircuff": float(mircuff) if mircuff is not None else 0.0,
            "maxgc": float(maxgc) if maxgc is not None else 0.0,
            "mingc": float(mingc) if mingc is not None else 0.0,
            "middlegc": float(middlegc) if middlegc is not None else 0.0,
            "allow_path": str(allow_path or ""),
            "ban_path": str(ban_path or ""),
        }
    except requests.RequestException as exc:
        _raise_service_error(exc, "Evitar")


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
        _raise_service_error(exc, "CRISOT score")


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
        _raise_service_error(exc, "CRISOT spec")


@tool(args_schema=CrisotOffSpecInput)
def search_crispr_off_targets_with_crisot(
    filepath: str,
    target_sequence: str,
    genome_path: str,
    mismatches: int = 6,
    device: str = "G0",
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
        _raise_service_error(exc, "CRISOT off-spec")


@tool(args_schema=CrisotOptimizeInput)
def optimize_sgrna_with_crisot(
    filepath: str,
    genome_path: str,
    threshold: float = 0.8,
    mismatches: int = 6,
    device: str = "G0",
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
        _raise_service_error(exc, "CRISOT optimize")


@tool(args_schema=CrisotScoresInput)
def score_batch_crispr_off_targets_with_crisot(
    csv_filepath: str,
    on_item: str = "On",
    off_item: str = "Off",
    service_url: str = "http://127.0.0.1:8011/scores",
) -> dict[str, Any]:
    """Batch calculate CRISOT-Score for sgRNA-target pairs in a CSV file.

    Args:
        csv_filepath: Path to the input CSV containing sgRNA and target sequences.
        on_item: CSV column name for sgRNA/on-target sequences.
        off_item: CSV column name for off-target sequences.
        service_url: REST endpoint for the CRISOT batch scoring microservice.

    Returns:
        Dict with row count and scored CSV artifact path.

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
            timeout=300,
        )
        response.raise_for_status()
        payload = response.json()
        if "scored_csv_path" not in payload:
            raise ValueError("Missing `scored_csv_path` in CRISOT scores response.")
        result: dict[str, Any] = {
            "input_csv_filepath": csv_filepath,
            "on_item": on_item,
            "off_item": off_item,
            "row_count": int(payload.get("row_count", 0)),
            "model": payload.get("model", "CRISOT-Score"),
        }
        scored_csv_path = payload.get("scored_csv_path")
        if scored_csv_path:
            result["scored_csv_filepath"] = copy_file_to_workspace(
                str(scored_csv_path),
                prefix="crisot_scores",
                suffix=".csv",
            )
        return result
    except requests.RequestException as exc:
        _raise_service_error(exc, "CRISOT scores")


@tool(args_schema=CrisotRescoreInput)
def rescore_sgrnas_with_crisot(
    txt_filepath: str,
    genome_path: str,
    mismatches: int = 6,
    device: str = "G0",
    service_url: str = "http://127.0.0.1:8011/rescore",
) -> dict[str, Any]:
    """Rescore and rerank a list of sgRNAs using CRISOT genome-wide search.

    Args:
        txt_filepath: Path to a TXT file with one sgRNA sequence per line.
        genome_path: Reference genome FASTA path used by Cas-OFFinder.
        mismatches: Cas-OFFinder mismatch tolerance.
        device: Cas-OFFinder device selector such as `C` or `G0`.
        service_url: REST endpoint for the CRISOT rescore microservice.

    Returns:
        Dict with sgRNA count, rescore CSV artifact path, and echoed parameters.

    Raises:
        ValueError: If the CRISOT service is unreachable or returns an invalid payload.
    """
    try:
        response = requests.post(
            service_url,
            json={
                "txt_path": txt_filepath,
                "genome_path": genome_path,
                "mismatches": mismatches,
                "device": device,
            },
            timeout=3600,
        )
        response.raise_for_status()
        payload = response.json()
        if "rescore_csv_path" not in payload:
            raise ValueError("Missing `rescore_csv_path` in CRISOT rescore response.")
        result: dict[str, Any] = {
            "input_txt_filepath": txt_filepath,
            "genome_path": genome_path,
            "mismatches": int(payload.get("mismatches", mismatches)),
            "device": str(payload.get("device", device)),
            "sgrna_count": int(payload.get("sgrna_count", 0)),
            "model": payload.get("model", "CRISOT-Rescore"),
        }
        rescore_csv_path = payload.get("rescore_csv_path")
        if rescore_csv_path:
            result["rescore_csv_filepath"] = copy_file_to_workspace(
                str(rescore_csv_path),
                prefix="crisot_rescore",
                suffix=".csv",
            )
        return result
    except requests.RequestException as exc:
        _raise_service_error(exc, "CRISOT rescore")


@tool(args_schema=CrisotFpInput)
def predict_crispr_off_target_with_crisot_fp(
    csv_filepath: str,
    xgb_model: str = "Circle-seq",
    on_item: str = "On",
    off_item: str = "Off",
    service_url: str = "http://127.0.0.1:8011/crisot-fp",
) -> dict[str, Any]:
    """Predict CRISPR off-target effects using CRISOT-FP XGBoost models.

    Args:
        csv_filepath: Path to the input CSV containing sgRNA and off-target sequences.
        xgb_model: XGBoost model to use: Circle-seq, Site-seq, or Change-seq.
        on_item: CSV column name for sgRNA/on-target sequences.
        off_item: CSV column name for off-target sequences.
        service_url: REST endpoint for the CRISOT-FP microservice.

    Returns:
        Dict with row count, FP CSV artifact path, and model name.

    Raises:
        ValueError: If the CRISOT service is unreachable or returns an invalid payload.
    """
    try:
        response = requests.post(
            service_url,
            json={
                "csv_path": csv_filepath,
                "xgb_model": xgb_model,
                "on_item": on_item,
                "off_item": off_item,
            },
            timeout=600,
        )
        response.raise_for_status()
        payload = response.json()
        if "fp_csv_path" not in payload:
            raise ValueError("Missing `fp_csv_path` in CRISOT-FP response.")
        result: dict[str, Any] = {
            "input_csv_filepath": csv_filepath,
            "xgb_model": str(payload.get("xgb_model", xgb_model)),
            "on_item": on_item,
            "off_item": off_item,
            "row_count": int(payload.get("row_count", 0)),
            "model": payload.get("model", "CRISOT-FP"),
        }
        fp_csv_path = payload.get("fp_csv_path")
        if fp_csv_path:
            result["fp_csv_filepath"] = copy_file_to_workspace(
                str(fp_csv_path),
                prefix="crisot_fp",
                suffix=".csv",
            )
        return result
    except requests.RequestException as exc:
        _raise_service_error(exc, "CRISOT-FP")


@tool(args_schema=CrisotGenFpInput)
def generate_crispr_fingerprint_with_crisot(
    sgrna: str,
    target_sequence: str,
    service_url: str = "http://127.0.0.1:8011/gen-fp",
) -> dict[str, Any]:
    """Generate CRISOT-FP molecular interaction fingerprint for an sgRNA-target pair.

    Args:
        sgrna: sgRNA sequence (23 nt including PAM).
        target_sequence: Target DNA sequence (23 nt including PAM).
        service_url: REST endpoint for the CRISOT-FP encoding microservice.

    Returns:
        Dict with normalized sequences and FP encoding CSV artifact path.

    Raises:
        ValueError: If the CRISOT service is unreachable or returns an invalid payload.
    """
    normalized_sgrna = _normalize_crisot_sequence(sgrna)
    normalized_target = _normalize_crisot_sequence(target_sequence)
    try:
        response = requests.post(
            service_url,
            json={
                "sgrna": normalized_sgrna,
                "target_sequence": normalized_target,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if "fp_csv_path" not in payload:
            raise ValueError("Missing `fp_csv_path` in CRISOT gen-fp response.")
        result: dict[str, Any] = {
            "sgrna": normalized_sgrna,
            "target_sequence": normalized_target,
            "model": payload.get("model", "CRISOT-FP-Encoding"),
        }
        fp_csv_path = payload.get("fp_csv_path")
        if fp_csv_path:
            result["fp_csv_filepath"] = copy_file_to_workspace(
                str(fp_csv_path),
                prefix="crisot_genfp",
                suffix=".csv",
            )
        return result
    except requests.RequestException as exc:
        _raise_service_error(exc, "CRISOT gen-fp")


@tool(args_schema=SgRNADesignInput)
def design_sgrna_handle_with_crgpt(
    seed_sequence: Optional[str] = None,
    filepath: Optional[str] = None,
    n_samples: int = 10,
    mutation_number: int = 22,
    temperature: Optional[float] = None,
    max_length: Optional[int] = None,
    max_overlap: int = 21,
    sampling_mode: str = "mcmc",
    path_to_model: Optional[str] = None,
    device: Optional[str] = None,
    output_dir: Optional[str] = None,
    service_url: str = "http://127.0.0.1:8017/design",
) -> dict[str, Any]:
    """Design sgRNA handle candidates through sgrna_design microservice.

    INTERFACE LOCK (v0.3.0): This wrapper's return dict keys are the canonical
    interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: SgRNADesignOutput
    - agent_core/state.py :: sgrna_design_* fields
    - agent_core/nodes.py :: tool_execution_node sgrna_design branch

    Args:
        seed_sequence: Inline seed/wildtype sgRNA handle sequence (DNA/RNA).
            Either this or filepath must be provided.
        filepath: Path to a file containing the seed sgRNA handle sequence.
            Either this or seed_sequence must be provided.
        n_samples: Number of designed candidates to request.
        mutation_number: Maximum mutation count relative to seed sequence.
        temperature: MCMC annealing temperature (mcmc mode) or transformer sampling temperature (naive mode).
        max_overlap: Maximum overlap constraint among candidates.
        sampling_mode: Sampling strategy: 'mcmc' (original MCMC/annealing) or 'naive' (direct model.generate).
        path_to_model: Optional model directory (relative to sgrna_design root or absolute path).
        device: Optional torch device override such as `cuda:0` or `cpu`.
        output_dir: Optional output directory override for the microservice.
        service_url: REST endpoint for the sgrna_design microservice.

    Returns:
        Dict containing best candidate summary and artifact filepaths copied into workspace.

    Raises:
        ValueError: If service request fails or response payload is invalid.
    """
    if seed_sequence:
        resolved_seed = _normalize_sgrna_design_sequence(seed_sequence)
    elif filepath:
        resolved_seed = _normalize_sgrna_design_sequence(read_sequence(filepath))
    else:
        raise ValueError("Either seed_sequence or filepath must be provided for sgRNA design.")

    request_payload: dict[str, Any] = {
        "seed_sequence": resolved_seed,
        "n_samples": int(n_samples),
        "mutation_number": int(mutation_number),
        "max_overlap": int(max_overlap),
        "sampling_mode": sampling_mode,
    }
    if temperature is not None:
        request_payload["temperature"] = float(temperature)
    if max_length is not None:
        request_payload["max_length"] = int(max_length)
    if path_to_model:
        request_payload["path_to_model"] = path_to_model
    if device:
        request_payload["device"] = device
    if output_dir:
        request_payload["output_dir"] = output_dir

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
        raw_ali = payload.get("output_ali_path")
        output_ali_path = str(raw_ali) if raw_ali is not None else ""
        workspace_fasta_path = output_fasta_path
        workspace_summary_path = summary_json_path
        workspace_ali_path = output_ali_path
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
        if output_ali_path:
            try:
                workspace_ali_path = copy_file_to_workspace(
                    output_ali_path,
                    prefix="sgrna_design_align",
                    suffix=".ali",
                )
            except OSError:
                workspace_ali_path = output_ali_path

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
            "seed_sequence": resolved_seed,
            "input_filepath": filepath,
            "normalized_seed": str(payload.get("normalized_seed", resolved_seed)),
            "generated_count": int(payload.get("generated_count", 0)),
            "best_sequence": best_sequence,
            "best_nn_score": best_nn_score,
            "best_mutation_count": best_mutation_count,
            "sampling_mode": str(payload.get("sampling_mode", sampling_mode)),
            "output_fasta_filepath": workspace_fasta_path,
            "output_ali_filepath": workspace_ali_path,
            "summary_json_filepath": workspace_summary_path,
            "raw_output_fasta_path": output_fasta_path,
            "raw_summary_json_path": summary_json_path,
            "raw_output_ali_path": output_ali_path,
            "device": str(payload.get("device", device or "")),
            "model_path": str(payload.get("model_path", path_to_model or "")),
            "has_vienna_rna": bool(payload.get("has_vienna_rna", False)),
            "notes": payload.get("notes", []),
            "model": str(payload.get("model", "sgrna_design_crgpt")),
        }
        if best_sequence:
            result["best_sequence_filepath"] = save_sequence(best_sequence, prefix="sgrna_design_best")
        # Include log_likelihood from the best candidate if available
        if best_candidate and best_candidate.get("log_likelihood") is not None:
            result["best_log_likelihood"] = float(best_candidate["log_likelihood"])
        return result
    except requests.RequestException as exc:
        _raise_service_error(exc, "sgRNA design")


class SgRNADesignScoreInput(BaseModel):
    """Input schema for sgRNA handle scoring via sgrna_design_service.

    INTERFACE LOCK (v0.3.0): Locked schema. Modify only in sync with:
    - microservices/sgrna_design_service/main.py :: ScoreRequest
    - agent_core/tool_specs.py :: score_sgrna_handle_with_crgpt ToolSpec
    - agent_core/state.py :: sgrna_design_score_* fields
    - agent_core/nodes.py :: tool_execution_node score_sgrna branch
    """

    sequence: str = Field(
        ...,
        description="Inline sgRNA handle sequence (DNA/RNA) to score.",
    )
    path_to_model: Optional[str] = Field(
        default=None,
        description="Optional model directory (relative to sgrna_design root or absolute path).",
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional torch device override such as `cuda:0` or `cpu`.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8017/score",
        description="REST endpoint for sgRNA scoring microservice.",
    )


@tool(args_schema=SgRNADesignScoreInput)
def score_sgrna_handle_with_crgpt(
    sequence: str,
    path_to_model: Optional[str] = None,
    device: Optional[str] = None,
    service_url: str = "http://127.0.0.1:8017/score",
) -> dict[str, Any]:
    """Score a single sgRNA handle sequence using the CRGPT model.

    Computes nn_score (exp(loss)), log_likelihood (negative cross-entropy),
    ViennaRNA structure distance / MFE, and constraint mutation count.

    Args:
        sequence: sgRNA handle sequence to score (DNA/RNA).
        path_to_model: Optional model directory override.
        device: Optional torch device such as `cuda:0` or `cpu`.
        service_url: REST endpoint for the sgrna_design scoring endpoint.

    Returns:
        Dict with normalized sequence, nn_score, log_likelihood, structure_distance,
        mfe, and constraint_mutation_count.
    """
    normalized = _normalize_sgrna_design_sequence(sequence)
    payload: dict[str, Any] = {"sequence": normalized}
    if path_to_model:
        payload["path_to_model"] = path_to_model
    if device:
        payload["device"] = device
    try:
        response = requests.post(service_url, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        required = {"nn_score", "log_likelihood", "normalized_sequence", "constraint_mutation_count"}
        if not required.issubset(data):
            raise ValueError(
                "sgRNA score response is missing required fields: "
                f"{sorted(required - set(data))}"
            )
        return {
            "sequence": sequence,
            "normalized_sequence": str(data["normalized_sequence"]),
            "nn_score": float(data["nn_score"]),
            "log_likelihood": float(data["log_likelihood"]),
            "structure_distance": data.get("structure_distance"),
            "mfe": data.get("mfe"),
            "constraint_mutation_count": int(data["constraint_mutation_count"]),
            "model": str(data.get("model", "sgrna_design_crgpt")),
        }
    except requests.RequestException as exc:
        _raise_service_error(exc, "sgRNA score")


class MrnaToolInput(BaseModel):
    """Input schema for workspace-backed mRNA/RNA sequence tools (filepath only)."""

    filepath: str = Field(
        ...,
        description="Path to mRNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# codonw-slim INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 analyze_cds_codon_metrics_with_codonw_slim
# 的 INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。
# ═══════════════════════════════════════════════════════════════════════════════

class CodonwSlimAnalyzeInput(BaseModel):
    """Input schema for codonw-slim CDS codon-usage metrics.

    Mirrors the upstream CodonSeq API so that the agent can access every
    metric and reference table offered by codonw-slim.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - microservices/codonw_slim_service/main.py :: CodonwAnalyzeRequest
    - agent_core/tool_specs.py :: analyze_cds_codon_metrics_with_codonw_slim ToolSpec
    - agent_core/state.py :: codonw_* fields
    - agent_core/nodes.py :: _build_codonw_tool_args / tool_execution_node codonw branch
    """

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
        description=(
            "Genetic code index passed to CodonSeq. "
            "0=universal nuclear, 1=vertebrate mitochondrial, 2=yeast mitochondrial, "
            "3=filamentous fungi mitochondrial, 4=insects/platyhelminthes mitochondrial, "
            "5=nuclear ciliate, 6=nuclear euplotes, 7=echinoderm mitochondrial."
        ),
    )
    cai_ref: int = Field(
        default=0,
        ge=0,
        le=2,
        description=(
            "Reference set index for CAI and CBI. "
            "0=Escherichia coli, 1=Bacillus subtilis, 2=Saccharomyces cerevisiae."
        ),
    )
    fop_ref: int = Field(
        default=0,
        ge=0,
        le=7,
        description=(
            "Fop reference species index. "
            "0=E. coli, 1=B. subtilis, 2=D. discoideum, 3=A. nidulans, "
            "4=S. cerevisiae, 5=D. melanogaster, 6=C. elegans, 7=N. crassa."
        ),
    )
    factor_in_rare: bool = Field(
        default=False,
        description="If true, pass factor_in_rare=True into CodonSeq.fop() (uses (opt-rare)/total formulation).",
    )
    include_codon_tables: bool = Field(
        default=False,
        description="If true, request full codon_usage and rscu tables (larger JSON).",
    )
    include_dinucleotide: bool = Field(
        default=False,
        description="If true, request dinucleotide composition tables by reading frame.",
    )
    include_aa_tables: bool = Field(
        default=False,
        description="If true, request amino-acid usage (aa_usage) and relative amino-acid usage (raau) tables.",
    )
    include_bases: bool = Field(
        default=False,
        description="If true, request base composition by codon position (bases DataFrame).",
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
    """Input schema for GEMORNA CDS design tool.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - microservices/gemorna_service/main.py :: CdsDesignRequest
    - agent_core/tool_specs.py :: design_mrna_cds_with_gemorna ToolSpec
    """

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


class Gemorna5UtrInput(BaseModel):
    """Input schema for GEMORNA 5'UTR design tool.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - microservices/gemorna_service/main.py :: UtrDesignRequest
    - agent_core/tool_specs.py :: design_5utr_with_gemorna ToolSpec
    """

    utr_length: str = Field(
        default="medium",
        description="UTR length category: short | medium | long.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8004/generate/5utr",
        description="REST endpoint for the GEMORNA 5'UTR generation microservice.",
    )


class Gemorna3UtrInput(BaseModel):
    """Input schema for GEMORNA 3'UTR design tool.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - microservices/gemorna_service/main.py :: UtrDesignRequest
    - agent_core/tool_specs.py :: design_3utr_with_gemorna ToolSpec
    """

    utr_length: str = Field(
        default="medium",
        description="UTR length category: short | medium | long.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8004/generate/3utr",
        description="REST endpoint for the GEMORNA 3'UTR generation microservice.",
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
    """Input schema for RNARL CDS design tool.

    WARNING: This schema is locked. Any field change must be synchronized with:
    - microservices/rnarl_service/main.py :: CdsDesignRequest
    - agent_core/tool_specs.py :: RNARLCdsOutput + ToolSpec registration
    - docs/tools/design_mrna_cds_with_rnarl.md
    See the tool documentation for the canonical interface contract.
    """

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
            "RNARL trained model variant (species / RNA type). "
            "Must be one of the following 6 supported values: "
            "`Homo sapiens mRNA` (default), "
            "`Homo sapiens circular RNA`, "
            "`Arabidopsis thaliana mRNA`, "
            "`Escherichia coli mRNA`, "
            "`Penicillium chrysogenum mRNA`, "
            "`Chlamydomonas reinhardtii mRNA`, "
            "`Thermococcus kodakarensis KOD1 mRNA`."
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
    """Input schema for RhoFold tertiary structure prediction.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: RhoFoldOutput / predict_rna_tertiary_structure_with_rhofold ToolSpec
    - microservices/rhofold_service/main.py :: RhoFoldPredictRequest / RhoFoldPredictResponse
    - agent_core/nodes.py :: rhofold result ingestion (tool_result field names)
    - docs/tools/predict_rna_tertiary_structure_with_rhofold.md

    This wrapper exposes the single-sequence prediction mode only.
    MSA-based prediction is not exposed because local MSA databases
    (~900 GB) are not deployed in this environment.
    """

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
    checkpoint_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional path to a custom RhoFold checkpoint. "
            "If omitted, the microservice will search standard pretrained paths."
        ),
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional compute device: cpu, cuda, cuda:0, etc.",
    )


class RhoDesignInput(BaseModel):
    """Input schema for RhoDesign structure-to-sequence design.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: RhoDesignOutput
    - microservices/rhodesign_service/main.py :: RhoDesignRequest / RhoDesignResponse
    - docs/tools/design_rna_sequence_with_rhodesign.md
    """

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
    timeout_seconds: int = Field(
        default=3600,
        ge=60,
        le=21600,
        description="Subprocess timeout for the RhoDesign generation run.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RiboDiffusion INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
# 关联文件清单（修改时必须全部同步）：
#   - microservices/ribodiffusion_service/main.py
#   - agent_core/tools.py  ← 本文件
#   - agent_core/tool_specs.py
#   - agent_core/state.py
#   - agent_core/nodes.py
#   - docs/RNA_AGENT_SYSTEM_GUIDE.md
# 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
# 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
# ═══════════════════════════════════════════════════════════════════════════════

class RiboDiffusionInput(BaseModel):
    """Input schema for RiboDiffusion tertiary inverse folding."""

    pdb_filepath: str = Field(
        ...,
        description="Path to an RNA structure PDB file for RiboDiffusion inverse folding.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8021/design/from-pdb",
        description="REST endpoint for the RiboDiffusion microservice.",
    )
    n_samples: int = Field(default=1, ge=1, le=64, description="Number of sequences to sample.")
    sampling_steps: int = Field(default=50, ge=1, le=500, description="Diffusion sampling steps.")
    cond_scale: float = Field(
        default=-1.0,
        ge=-1.0,
        description="Conditional scale; -1 matches upstream default (disabled).",
    )
    dynamic_threshold: bool = Field(
        default=False,
        description="Enable dynamic thresholding (upstream eval flag).",
    )
    deterministic: bool = Field(default=True, description="Fixed random seed when True.")
    checkpoint_name: str = Field(
        default="exp_inf",
        description="Checkpoint basename without extension. Supported: 'exp_inf' (default), 'exp_inf_large'.",
    )
    device: int = Field(default=0, ge=0, description="CUDA device index for the subprocess.")


# ═══════════════════════════════════════════════════════════════════════════════
# RNAsmOL 接口冻结声明 (v0.2.0) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
# 关联文件清单（修改时必须全部同步）：
#   - microservices/rnasmol_service/main.py
#   - agent_core/tools.py  ← 本文件
#   - agent_core/tool_specs.py
#   - agent_core/state.py
#   - agent_core/nodes.py
#   - docs/tools/score_rna_ligand_binding_with_rnasmol.md
# 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
# 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
# ═══════════════════════════════════════════════════════════════════════════════

class RNAsmolScoreInput(BaseModel):
    """Input schema for RNAsmol RNA-ligand scoring.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - microservices/rnasmol_service/main.py :: ScoreRequest
    - agent_core/tool_specs.py :: score_rna_ligand_binding_with_rnasmol ToolSpec
    - docs/tools/score_rna_ligand_binding_with_rnasmol.md
    """

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
    dataset: Optional[str] = Field(
        default=None,
        description=(
            "Training dataset source hint for checkpoint auto-selection. "
            "Examples: `pdb` (RCSB PDB), `robin` (ROBIN dataset). "
            "When omitted the service uses its default checkpoint."
        ),
    )
    perturbation_type: Optional[str] = Field(
        default=None,
        description=(
            "Data-perturbation strategy hint for checkpoint auto-selection. "
            "Examples: `molperturbation`, `netperturbation`, `rnaperturbation`. "
            "When omitted the service uses its default checkpoint."
        ),
    )
    device: Optional[str] = Field(
        default=None,
        description="Optional PyTorch device string such as `cuda:0` or `cpu`.",
    )


class GerNABindScoreInput(BaseModel):
    """Input schema for GerNA-Bind RNA-ligand scoring.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - microservices/gernabind_service/main.py :: ScoreRequest
    - agent_core/tool_specs.py :: score_rna_ligand_binding_with_gernabind ToolSpec
    - docs/tools/score_rna_ligand_binding_with_gernabind.md
    """

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
    dataset: Optional[str] = Field(
        default=None,
        description=(
            "Optional dataset hint for selecting the default affinity checkpoint. "
            "Supported values: Robin, Biosensor. When omitted, the service tries Robin first."
        ),
    )
    split_method: Optional[str] = Field(
        default=None,
        description=(
            "Optional split-method hint for selecting the default affinity checkpoint. "
            "Supported values: random, RNA, mol, both. Defaults to 'random' when dataset is provided."
        ),
    )


class RNASTOPPredictionInput(BaseModel):
    """Input schema for RNASTOP stability prediction.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be
    synchronized with:
    - microservices/rnastop_service/main.py :: StabilityPredictionRequest
    - agent_core/tool_specs.py :: predict_mrna_stability_with_rnastop ToolSpec
    - docs/tools/predict_mrna_stability_with_rnastop.md

    RNASTOP predicts per-nucleotide degradation profiles (reactivity, deg_Mg_pH10,
    deg_Mg_50C).  The caller may supply a pre-computed secondary structure and/or
    loop annotation; when omitted the service computes them internally with
    ViennaRNA.
    """

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
    structure: Optional[str] = Field(
        default=None,
        description=(
            "Optional dot-bracket secondary structure. "
            "If provided it must have the same length as the RNA sequence. "
            "When omitted the service folds the sequence with ViennaRNA."
        ),
    )
    loop_type: Optional[str] = Field(
        default=None,
        description=(
            "Optional loop-type annotation string (same alphabet as the OpenVaccine "
            "dataset: S/M/I/H/B/E).  When omitted the service derives it from the "
            "structure automatically."
        ),
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
    """Input schema for IRESfinder putative IRES scoring.

    INTERFACE LOCK (v0.2.0): Locked schema — the canonical contract is the
    state after the 2026-04-23 refactor. Any field addition/removal must be
    synchronized with:
    - agent_core/tool_specs.py :: predict_putative_ires_with_iresfinder ToolSpec
    - microservices/iresfinder_service/main.py :: IRESfinderPredictRequest
    - agent_core/state.py :: iresfinder_* fields
    - agent_core/nodes.py :: tool_execution_node IRESfinder branch
    - docs/tools/predict_putative_ires_with_iresfinder.md
    """

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
        description=(
            "IRESfinder processing mode aligned with the upstream repository:\n"
            "- 0 (default): score each complete sequence as one fragment.\n"
            "- 1: extract a subsequence from each FASTA header that ends with ``start_pos end_pos``.\n"
            "- 2: split each sequence into sliding windows (requires ``window_size`` and ``step_size``)."
        ),
    )
    window_size: int = Field(
        default=174,
        ge=20,
        le=5000,
        description="Sliding-window length used only in mode 2 (upstream default: 174).",
    )
    step_size: int = Field(
        default=50,
        ge=1,
        le=5000,
        description="Sliding-window step size used only in mode 2 (upstream default: 50).",
    )
    decision_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Probability threshold for labeling a fragment as IRES (upstream default: 0.5).",
    )


class ODesignInferenceInput(BaseModel):
    """Input schema for ODesign inference.

    INTERFACE LOCK (v0.3.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: run_odesign_inference ToolSpec
    - microservices/odesign_service/main.py :: ODesignInferenceRequest
    - docs/tools/run_odesign_inference.md
    """
    

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
    timeout_seconds: int = Field(
        default=14400,
        ge=300,
        le=86400,
        description="Subprocess timeout for one ODesign inference request.",
    )
    invfold_topk: int = Field(
        default=1,
        ge=1,
        le=20,
        description="Number of designed sequences per backbone structure (inverse folding top-k).",
    )
    invfold_temp: float = Field(
        default=1.0,
        gt=0.0,
        description="Inverse folding sampling temperature.",
    )
    invfold_use_beam: bool = Field(
        default=True,
        description="Whether to use beam search in inverse folding.",
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
    include_aa_tables: bool = False,
    include_bases: bool = False,
) -> dict[str, Any]:
    """Compute codon usage / CAI / Nc (ENC) and related metrics via codonw-slim service.

    INTERFACE LOCK (v0.2.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: CodonwSlimOutput / analyze_cds_codon_metrics_with_codonw_slim ToolSpec
    - agent_core/state.py :: codonw_* fields
    - agent_core/nodes.py :: _build_codonw_tool_args / tool_execution_node codonw branch
    - microservices/codonw_slim_service/main.py :: CodonwAnalyzeRequest / CodonwAnalyzeResponse

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
        include_dinucleotide: Request dinucleotide tables by reading frame.
        include_aa_tables: Request amino-acid usage and relative amino-acid usage tables.
        include_bases: Request base composition by codon position.

    Returns:
        Summary dict including ``cai_score``, ``enc``, ``fop``, ``cbi``,
        ``hydropathy``, ``aromaticity``, ``silent_base_usage``, ``bases2``,
        optional tables, and ``metrics_json_filepath`` pointing to a saved
        JSON artifact in ``workspace/``.
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
        "include_aa_tables": include_aa_tables,
        "include_bases": include_bases,
    }
    try:
        response = requests.post(service_url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        _raise_service_error(exc, "codonw-slim")

    metrics_json_filepath = save_text_file(
        json.dumps(data, indent=2, ensure_ascii=True),
        prefix="codonw_metrics",
        suffix=".json",
    )

    def _f(key: str) -> float:
        v = data.get(key)
        return float(v) if v is not None else 0.0

    return {
        "input_filepath": filepath,
        "metrics_json_filepath": metrics_json_filepath,
        "cai_score": _f("cai"),
        "enc": _f("enc"),
        "fop": _f("fop"),
        "cbi": _f("cbi"),
        "hydropathy": _f("hydropathy"),
        "aromaticity": _f("aromaticity"),
        "genetic_code": int(data.get("genetic_code", genetic_code)),
        "cds_length_nt": int(data.get("cds_length_nt", 0)),
        "cds_length_codons": int(data.get("cds_length_codons", 0)),
        "normalization_note": str(data.get("normalization_note", "")),
        "silent_base_usage": data.get("silent_base_usage", {}),
        "bases2": data.get("bases2", {}),
        "codon_usage": data.get("codon_usage"),
        "rscu": data.get("rscu"),
        "dinuc": data.get("dinuc"),
        "aa_usage": data.get("aa_usage"),
        "raau": data.get("raau"),
        "bases": data.get("bases"),
        "model": str(data.get("model", "codonw-slim")),
    }


@tool(args_schema=MrnaToolInput)
def predict_rna_secondary_structure(
    filepath: str, service_url: str = "http://localhost:8003/fold"
) -> dict[str, Any]:
    """Predict RNA secondary structure and MFE using ViennaRNA service.

    Args:
        filepath: Workspace file path containing RNA sequence content.
            IMPORTANT: You must pass a filepath in workspace, NOT raw sequence text.
        service_url: REST endpoint for ViennaRNA fold microservice.

    Returns:
        Dict containing ``structure`` and ``mfe_kcal_per_mol`` plus audit fields.

    Raises:
        ValueError: If ViennaRNA API request fails or response payload is invalid.
    """
    sequence = _normalize_nucleic_sequence(read_sequence(filepath))
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
        return {
            "input_filepath": filepath,
            "structure": str(payload["structure"]),
            "mfe_kcal_per_mol": float(payload["mfe"]),
            "backend": str(payload.get("backend", "")),
            "model": str(payload.get("model", "ViennaRNA-RNAfold")),
        }
    except requests.RequestException as exc:
        _raise_service_error(exc, "ViennaRNA")


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


class PlfoldLocalProfileViennaInput(BaseModel):
    """Input for whole-sequence RNAplfold local (single-nt) unpaired probability profile."""

    filepath: str = Field(..., description="Workspace file with RNA sequence (plain or FASTA).")
    service_url: str = Field(
        default="http://127.0.0.1:8003/plfold-profiles",
        description="REST endpoint for ViennaRNA RNAplfold profile (lunp column 1).",
    )
    winsize: int = Field(default=70, ge=3, le=800, description="RNAplfold -W window size.")
    span: int = Field(default=70, ge=2, le=800, description="RNAplfold -L max pair span.")
    unpaired_ulength: int = Field(
        default=25,
        ge=1,
        le=500,
        description="RNAplfold -u upper bound for stretch probabilities in lunp output.",
    )
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
        _raise_service_error(exc, "ViennaRNA duplex")
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
        _raise_service_error(exc, "ViennaRNA accessibility")
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


@tool(args_schema=PlfoldLocalProfileViennaInput)
def predict_rna_local_accessibility_profile_vienna(
    filepath: str,
    service_url: str = "http://127.0.0.1:8003/plfold-profiles",
    winsize: int = 70,
    span: int = 70,
    unpaired_ulength: int = 25,
    temp_c: float = 37.0,
) -> dict[str, Any]:
    """Run ViennaRNA ``RNAplfold`` for local single-nucleotide unpaired probabilities (accessibility curve).

    Uses the same sliding-window local folding model as ASO accessibility, but returns a **full-sequence**
    profile (lunp first column: probability each base is unpaired in the local context). Writes a TSV
    under ``workspace/`` with columns ``position`` and ``unpaired_prob_1nt`` for downstream plotting.

    Args:
        filepath: RNA sequence file (workspace path or absolute on the server).
        service_url: ViennaRNA microservice ``POST /plfold-profiles`` URL.
        winsize, span, unpaired_ulength: RNAplfold parameters (-W, -L, -u).
        temp_c: Folding temperature (Celsius).

    Returns:
        Summary statistics, array lengths, and ``lunp_profile_tsv_filepath`` for the saved curve.

    Raises:
        ValueError: If the service request fails or the response is invalid.
    """
    sequence_text = read_sequence(filepath)
    try:
        response = requests.post(
            service_url,
            json={
                "sequence": sequence_text,
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
        _raise_service_error(exc, "ViennaRNA RNAplfold profile")
    required = ("positions", "unpaired_prob_1nt", "sequence_length")
    if any(k not in payload for k in required):
        raise ValueError(f"Invalid plfold-profiles response; expected keys {required}.")
    positions = payload["positions"]
    probs = payload["unpaired_prob_1nt"]
    if not isinstance(positions, list) or not isinstance(probs, list):
        raise ValueError("`positions` and `unpaired_prob_1nt` must be JSON arrays.")
    if len(positions) != len(probs):
        raise ValueError("`positions` and `unpaired_prob_1nt` length mismatch.")
    lines = ["position\tunpaired_prob_1nt"]
    for pos, p in zip(positions, probs):
        lines.append(f"{int(pos)}\t{float(p):.8g}")
    tsv_body = "\n".join(lines) + "\n"
    out_fp = save_text_file(tsv_body, prefix="vienna_rnaplfold_profile", suffix=".tsv")
    return {
        "input_filepath": filepath,
        "sequence_length": int(payload.get("sequence_length", 0)),
        "profile_positions_count": len(positions),
        "mean_unpaired_prob_1nt": float(payload.get("mean_unpaired_prob_1nt", 0.0)),
        "min_unpaired_prob_1nt": float(payload.get("min_unpaired_prob_1nt", 0.0)),
        "max_unpaired_prob_1nt": float(payload.get("max_unpaired_prob_1nt", 0.0)),
        "plfold_winsize": int(payload.get("winsize", winsize)),
        "plfold_span": int(payload.get("span", span)),
        "plfold_unpaired_ulength_effective": int(payload.get("unpaired_ulength_effective", unpaired_ulength)),
        "lunp_profile_tsv_filepath": out_fp,
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
        _raise_service_error(exc, "ViennaRNA inverse-fold")
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
        _raise_service_error(exc, "LinearFold")


@tool(args_schema=GemornaCdsInput)
def design_mrna_cds_with_gemorna(
    filepath: str, service_url: str = "http://127.0.0.1:8004/generate/cds"
) -> dict[str, Any]:
    """Design an mRNA CDS sequence from a protein sequence using GEMORNA.

    INTERFACE LOCK (v0.2.0): The return dict keys must stay synchronized with:
    - agent_core/tool_specs.py :: GemornaCdsOutput
    - microservices/gemorna_service/main.py :: CdsDesignResponse

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
        _raise_service_error(exc, "GEMORNA")


def _call_gemorna_utr(
    service_url: str,
    utr_length: str,
    prefix: str,
    default_model: str,
) -> dict[str, Any]:
    """Shared HTTP helper for GEMORNA 5'UTR / 3'UTR wrappers."""
    try:
        response = requests.post(
            service_url,
            json={"utr_length": utr_length},
            timeout=300,
        )
        response.raise_for_status()
        payload = response.json()
        if "generated_sequence" not in payload:
            raise ValueError(f"Missing `generated_sequence` in {default_model} response.")
        output_filepath = save_sequence(payload["generated_sequence"], prefix=prefix)
        return {
            "output_filepath": output_filepath,
            "generated_sequence": payload["generated_sequence"],
            "utr_length": payload.get("utr_length", utr_length),
            "raw_output": payload.get("raw_output", ""),
            "model": payload.get("model", default_model),
        }
    except requests.RequestException as exc:
        _raise_service_error(exc, default_model)


@tool(args_schema=Gemorna5UtrInput)
def design_5utr_with_gemorna(
    utr_length: str = "medium",
    service_url: str = "http://127.0.0.1:8004/generate/5utr",
) -> dict[str, Any]:
    """Design a 5'UTR sequence using GEMORNA.

    INTERFACE LOCK (v0.2.0): The return dict keys must stay synchronized with:
    - agent_core/tool_specs.py :: Gemorna5UtrOutput
    - microservices/gemorna_service/main.py :: UtrDesignResponse

    Args:
        utr_length: UTR length category — `short`, `medium`, or `long`.
        service_url: REST endpoint for the GEMORNA 5'UTR microservice.

    Returns:
        Dict containing the generated 5'UTR sequence and a new workspace filepath.

    Raises:
        ValueError: If the GEMORNA service is unreachable or returns an invalid payload.
    """
    return _call_gemorna_utr(service_url, utr_length, "gemorna_5utr", "GEMORNA-5utr")


@tool(args_schema=Gemorna3UtrInput)
def design_3utr_with_gemorna(
    utr_length: str = "medium",
    service_url: str = "http://127.0.0.1:8004/generate/3utr",
) -> dict[str, Any]:
    """Design a 3'UTR sequence using GEMORNA.

    INTERFACE LOCK (v0.2.0): The return dict keys must stay synchronized with:
    - agent_core/tool_specs.py :: Gemorna3UtrOutput
    - microservices/gemorna_service/main.py :: UtrDesignResponse

    Args:
        utr_length: UTR length category — `short`, `medium`, or `long`.
        service_url: REST endpoint for the GEMORNA 3'UTR microservice.

    Returns:
        Dict containing the generated 3'UTR sequence and a new workspace filepath.

    Raises:
        ValueError: If the GEMORNA service is unreachable or returns an invalid payload.
    """
    return _call_gemorna_utr(service_url, utr_length, "gemorna_3utr", "GEMORNA-3utr")


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
        _raise_service_error(exc, "LinearDesign")


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

    INTERFACE LOCK (v0.2.0): This wrapper's IO contract is synchronized with
    microservices/rnarl_service/main.py :: generate_cds().
    Any payload key change must be mirrored there and documented in
    docs/tools/design_mrna_cds_with_rnarl.md.

    Args:
        filepath: Workspace file path containing the input protein sequence.
            IMPORTANT: You must pass a workspace filepath, not the sequence itself.
        service_url: REST endpoint for the RNARL microservice.
        model_type: RNARL trained model variant (species / RNA type).
            Supported: `Homo sapiens mRNA` (default), `Homo sapiens circular RNA`,
            `Arabidopsis thaliana mRNA`, `Escherichia coli mRNA`,
            `Penicillium chrysogenum mRNA`, `Chlamydomonas reinhardtii mRNA`,
            `Thermococcus kodakarensis KOD1 mRNA`.
        checkpoint_path: Optional actor checkpoint override for the RNARL service.
        esm2_model_path: Optional local ESM-2 model directory override.
        device: Optional torch device override passed to the RNARL service.

    Returns:
        Dict containing the generated CDS sequence, runtime metadata, and a new workspace filepath.

    Raises:
        ValueError: If the input protein sequence contains invalid characters or the RNARL service is unreachable.
    """
    protein_sequence = read_sequence(filepath).strip()
    valid_residues = set("ARNDCQEGHILKMFPSTWYV*")
    invalid_chars = sorted(set(ch for ch in protein_sequence.upper() if ch not in valid_residues and ch.isalpha()))
    if invalid_chars:
        raise ValueError(
            f"RNARL input protein sequence contains unsupported residue(s): {''.join(invalid_chars)}. "
            f"Only standard amino-acid letters and '*' are allowed."
        )
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
        _raise_service_error(exc, "RNARL")


@tool(args_schema=RhoFoldInput)
def predict_rna_tertiary_structure_with_rhofold(
    filepath: str,
    service_url: str = "http://127.0.0.1:8005/predict",
    relax_steps: int = 0,
    checkpoint_path: Optional[str] = None,
    device: Optional[str] = None,
) -> dict[str, Any]:
    """Predict RNA tertiary structure using the RhoFold microservice.

    INTERFACE LOCK (v0.2.0): Locked return dict keys. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: RhoFoldOutput
    - agent_core/nodes.py :: rhofold result ingestion (pdb_filepath, ct_filepath, etc.)
    - docs/tools/predict_rna_tertiary_structure_with_rhofold.md

    Args:
        filepath: Workspace file path containing the input RNA sequence.
            IMPORTANT: You must pass a workspace filepath, not the sequence itself.
        service_url: REST endpoint for the RhoFold microservice.
        relax_steps: Amber relaxation iterations. Default 0 keeps inference lighter.
        checkpoint_path: Optional path to a custom RhoFold checkpoint.
            If omitted, the microservice searches standard pretrained paths.
        device: Optional compute device such as ``cpu``, ``cuda``, or ``cuda:0``.

    Returns:
        Dict containing workspace paths for generated artifacts and a mean pLDDT summary.

    Raises:
        ValueError: If the RhoFold service is unreachable or returns an invalid payload.
    """
    sequence = _normalize_nucleic_sequence(read_sequence(filepath))
    request_body: dict[str, Any] = {
        "sequence": sequence,
        "single_seq_pred": True,
        "relax_steps": relax_steps,
    }
    if checkpoint_path is not None:
        request_body["checkpoint_path"] = checkpoint_path
    if device is not None:
        request_body["device"] = device

    try:
        response = requests.post(
            service_url,
            json=request_body,
            timeout=1800,
        )
        response.raise_for_status()
        payload = response.json()
        if "output_pdb_path" not in payload:
            raise ValueError("Missing `output_pdb_path` in RhoFold response.")

        mean_plddt = payload.get("mean_plddt")
        pdb_filepath = copy_file_to_workspace(payload["output_pdb_path"], prefix="rhofold_model")
        result: dict[str, Any] = {
            "input_filepath": filepath,
            "pdb_filepath": pdb_filepath,
            "mean_plddt": float(mean_plddt) if mean_plddt is not None else 0.0,
            "model": payload.get("model", "RhoFold+"),
            "service_output_dir": payload.get("service_output_dir", ""),
        }

        secondary_ct_path = payload.get("secondary_structure_ct_path")
        if secondary_ct_path:
            result["ct_filepath"] = copy_file_to_workspace(
                secondary_ct_path,
                prefix="rhofold_ss",
            )

        results_npz_path = payload.get("results_npz_path")
        if results_npz_path:
            result["results_filepath"] = copy_file_to_workspace(
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
        _raise_service_error(exc, "RhoFold")


@tool(args_schema=RhoDesignInput)
def design_rna_sequence_with_rhodesign(
    pdb_filepath: str,
    secondary_structure_filepath: Optional[str] = None,
    service_url: str = "http://127.0.0.1:8006/design/from-structure",
    temperature: float = 1e-5,
    device: int = 0,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Design an RNA sequence from a structure file using the RhoDesign microservice.

    INTERFACE LOCK (v0.2.0): Locked return dict keys. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: RhoDesignOutput
    - microservices/rhodesign_service/main.py :: RhoDesignResponse
    - docs/tools/design_rna_sequence_with_rhodesign.md

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
                "timeout_seconds": timeout_seconds,
            },
            timeout=timeout_seconds + 30,
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

        _attach_service_logs(result, payload, "rhodesign")
        return result
    except requests.RequestException as exc:
        _raise_service_error(exc, "RhoDesign")


@tool(args_schema=RiboDiffusionInput)
def design_rna_inverse_fold_with_ribodiffusion(
    pdb_filepath: str,
    service_url: str = "http://127.0.0.1:8021/design/from-pdb",
    n_samples: int = 1,
    sampling_steps: int = 50,
    cond_scale: float = -1.0,
    dynamic_threshold: bool = False,
    deterministic: bool = True,
    checkpoint_name: str = "exp_inf",
    device: int = 0,
) -> dict[str, Any]:
    """Generate RNA sequence(s) from a PDB structure using the RiboDiffusion microservice.

    Args:
        pdb_filepath: Path to the input PDB file (workspace or repo-relative path).
        service_url: REST endpoint for RiboDiffusion.
        n_samples: Count of independent samples (upstream `config.eval.n_samples`).
        sampling_steps: Number of diffusion sampling steps.
        cond_scale: Optional classifier-free guidance scale; -1 keeps upstream default.
        dynamic_threshold: Whether to enable dynamic thresholding during sampling.
        deterministic: Whether upstream fixes the RNG seed.
        checkpoint_name: Checkpoint basename without extension (`exp_inf` or `exp_inf_large`).
        device: CUDA device index passed via CUDA_VISIBLE_DEVICES.

    Returns:
        Dict with primary `predicted_sequence`, optional multi-sample lists, paths copied into workspace.
    """
    try:
        response = requests.post(
            service_url,
            json={
                "pdb_path": pdb_filepath,
                "n_samples": n_samples,
                "sampling_steps": sampling_steps,
                "cond_scale": cond_scale,
                "dynamic_threshold": dynamic_threshold,
                "deterministic": deterministic,
                "checkpoint_name": checkpoint_name,
                "device": device,
            },
            timeout=7200,
        )
        response.raise_for_status()
        payload = response.json()
        if "predicted_sequence" not in payload:
            raise ValueError("Missing `predicted_sequence` in RiboDiffusion response.")

        output_filepath = save_sequence(payload["predicted_sequence"], prefix="ribodiffusion_seq")
        result: dict[str, Any] = {
            "input_pdb_filepath": pdb_filepath,
            "output_filepath": output_filepath,
            "predicted_sequence": payload["predicted_sequence"],
            "model": payload.get("model", "RiboDiffusion"),
            "pdb_id": payload.get("pdb_id", ""),
            "service_output_dir": payload.get("service_output_dir", ""),
            "checkpoint_path": payload.get("checkpoint_path", ""),
            "fasta_dir": payload.get("fasta_dir", ""),
        }

        generated = payload.get("generated_sequences")
        if isinstance(generated, list) and generated:
            result["generated_sequences"] = generated

        recovery = payload.get("recovery_rate")
        if recovery is not None:
            result["recovery_rate"] = float(recovery)

        out_paths = payload.get("output_fasta_paths")
        if isinstance(out_paths, list) and out_paths:
            copied: list[str] = []
            for idx, fp in enumerate(out_paths):
                if fp:
                    copied.append(
                        copy_file_to_workspace(
                            str(fp),
                            prefix=f"ribodiffusion_fasta_{idx}",
                            suffix=".fasta",
                        )
                    )
            if copied:
                result["output_fasta_filepaths"] = copied

        _attach_service_logs(result, payload, "ribodiffusion")
        return result
    except requests.RequestException as exc:
        _raise_service_error(exc, "RiboDiffusion")


@tool(args_schema=RNAsmolScoreInput)
def score_rna_ligand_binding_with_rnasmol(
    filepath: str,
    smiles: str,
    service_url: str = "http://127.0.0.1:8007/score",
    checkpoint_path: Optional[str] = None,
    dataset: Optional[str] = None,
    perturbation_type: Optional[str] = None,
    device: Optional[str] = None,
) -> dict[str, Any]:
    """Score RNA-ligand binding probability using the RNAsmol microservice.

    INTERFACE LOCK (v0.2.0): The return dict keys below are the canonical interface.
    Any addition/removal must be synchronized with:
    - microservices/rnasmol_service/main.py :: ScoreResponse
    - agent_core/tool_specs.py :: RNAsmolScoreOutput
    - agent_core/state.py :: rnasmol_* fields
    - docs/tools/score_rna_ligand_binding_with_rnasmol.md

    Args:
        filepath: Path to a file containing the RNA sequence.
            IMPORTANT: pass a filepath rather than long inline sequence text.
        smiles: Ligand SMILES string to score against the RNA sequence.
        service_url: REST endpoint for the RNAsmol microservice.
        checkpoint_path: Optional checkpoint override for the RNAsmol service.
        dataset: Training dataset source hint (e.g. `pdb`, `robin`) for checkpoint selection.
        perturbation_type: Data-perturbation strategy hint (e.g. `rnaperturbation`) for checkpoint selection.
        device: Optional PyTorch device string such as `cuda:0` or `cpu`.

    Returns:
        Dict with the following canonical keys (INTERFACE LOCK):
            probability_positive (float): Positive-class binding probability.
            predicted_label (int): Predicted binary label (0 or 1).
            raw_logits (List[float]): Raw model logits [logit_0, logit_1].
            checkpoint_path (str): Path to the loaded model checkpoint.
            device (str): Device used for inference.
            dataset (Optional[str]): Dataset hint reflected back from the service.
            perturbation_type (Optional[str]): Perturbation hint reflected back from the service.
            model (str): Model identifier.

    Raises:
        ValueError: If the RNAsmol service is unreachable or returns an invalid payload.
    """
    sequence = _normalize_nucleic_sequence(read_sequence(filepath))
    try:
        request_payload: dict[str, Any] = {
            "rna_sequence": sequence,
            "smiles": smiles.strip(),
        }
        if checkpoint_path is not None:
            request_payload["checkpoint_path"] = checkpoint_path
        if dataset is not None:
            request_payload["dataset"] = dataset
        if perturbation_type is not None:
            request_payload["perturbation_type"] = perturbation_type
        if device is not None:
            request_payload["device"] = device

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
        _raise_service_error(exc, "RNAsmol")


@tool(args_schema=GerNABindScoreInput)
def score_rna_ligand_binding_with_gernabind(
    filepath: str,
    smiles: str,
    service_url: str = "http://127.0.0.1:8010/score",
    checkpoint_path: Optional[str] = None,
    pdb_path: Optional[str] = None,
    secondary_structure: Optional[str] = None,
    device: Optional[str] = None,
    dataset: Optional[str] = None,
    split_method: Optional[str] = None,
) -> dict[str, Any]:
    """Score RNA-ligand binding probability using the GerNA-Bind microservice.

    INTERFACE LOCK (v0.1.0): The return dict keys below are the canonical interface.
    Any addition/removal must be synchronized with:
    - microservices/gernabind_service/main.py :: ScoreResponse
    - agent_core/tool_specs.py :: GerNABindScoreOutput
    - agent_core/state.py :: gernabind_* fields
    - docs/tools/score_rna_ligand_binding_with_gernabind.md

    Args:
        filepath: Path to a file containing the RNA sequence.
            IMPORTANT: pass a filepath rather than long inline sequence text.
        smiles: Ligand SMILES string to score against the RNA sequence.
        service_url: REST endpoint for the GerNA-Bind microservice.
        checkpoint_path: Optional checkpoint override for the GerNA-Bind service.
        pdb_path: Optional precomputed RNA structure path passed through to GerNA-Bind.
        secondary_structure: Optional dot-bracket secondary structure passed through to GerNA-Bind.
        device: Optional torch device override such as `cuda:0` or `cpu`.
        dataset: Optional dataset hint (Robin or Biosensor) for selecting the default checkpoint.
        split_method: Optional split-method hint (random, RNA, mol, both) for checkpoint selection.

    Returns:
        Dict with the following canonical keys (INTERFACE LOCK):
            probability_positive (float): Positive-class binding probability.
            predicted_label (int): Predicted binary label (0 or 1).
            raw_alpha (List[float]): Evidential alpha parameters [alpha_0, alpha_1].
            checkpoint_path (str): Path to the loaded model checkpoint.
            preprocessing_pdb_path (str): PDB file used for feature generation.
            secondary_structure (str): Dot-bracket structure used for the run.
            device (str): Device used for inference.
            model (str): Model identifier.

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
        if dataset:
            request_payload["dataset"] = dataset
        if split_method:
            request_payload["split_method"] = split_method

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
        _raise_service_error(exc, "GerNA-Bind")


@tool(args_schema=RNASTOPPredictionInput)
def predict_mrna_stability_with_rnastop(
    filepath: str,
    service_url: str = "http://127.0.0.1:8009/predict/stability",
    structure: Optional[str] = None,
    loop_type: Optional[str] = None,
    checkpoint_path: Optional[str] = None,
    device: Optional[str] = None,
) -> dict[str, Any]:
    """Predict mRNA degradation and stability summaries using the RNASTOP microservice.

    INTERFACE LOCK (v0.1.0): The return dict keys below are the canonical interface.
    Any addition/removal must be synchronized with:
    - microservices/rnastop_service/main.py :: StabilityPredictionResponse
    - agent_core/tool_specs.py :: RNASTOPPredictionOutput
    - agent_core/nodes.py :: tool_execution_node RNASTOP branch
    - agent_core/state.py :: rnastop_* fields
    - docs/tools/predict_mrna_stability_with_rnastop.md

    Args:
        filepath: Path to a file containing the RNA sequence.
            IMPORTANT: pass a filepath rather than long inline sequence text.
        service_url: REST endpoint for the RNASTOP microservice.
        structure: Optional dot-bracket secondary structure (must match sequence length).
        loop_type: Optional loop-type annotation string.
        checkpoint_path: Optional checkpoint override for the RNASTOP service.
        device: Optional torch device override such as `cuda:0` or `cpu`.

    Returns:
        Dict with the following canonical keys (INTERFACE LOCK):
            input_filepath (str): Original filepath passed in.
            prediction_filepath (str): Workspace path to the saved per-position JSON.
            sequence (str): Original sequence from service (or local fallback).
            used_sequence (str): Sequence actually evaluated (may be truncated).
            sequence_length (int): len(sequence).
            used_length (int): len(used_sequence).
            truncated (bool): Whether truncation occurred.
            structure (str): Dot-bracket structure.
            loop_type (str): Loop-type annotation.
            mfe (float): Minimum free energy.
            mean_reactivity (float): Mean reactivity score.
            mean_deg_mg_ph10 (float): Mean deg_Mg_pH10 score.
            mean_deg_mg_50c (float): Mean deg_Mg_50C score.
            overall_stability (float): Global mean of the three metrics above.
                Backwards-compatible: computed locally if service omits it.
            checkpoint_path (str): Checkpoint path used.
            device (str): Device used for inference.
            model (str): Fixed to "RNASTOP".

    Raises:
        ValueError: If the RNASTOP service is unreachable or returns an invalid payload.
    """
    sequence = _normalize_nucleic_sequence(read_sequence(filepath))
    try:
        request_payload: dict[str, Any] = {"sequence": sequence}
        if structure is not None:
            request_payload["structure"] = structure
        if loop_type is not None:
            request_payload["loop_type"] = loop_type
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

        # Backwards-compatible: compute overall_stability locally if the
        # microservice is an older version that does not return it yet.
        mean_reactivity = float(payload["mean_reactivity"])
        mean_deg_mg_ph10 = float(payload["mean_deg_Mg_pH10"])
        mean_deg_mg_50c = float(payload["mean_deg_Mg_50C"])
        overall_stability = float(
            payload.get(
                "overall_stability",
                (mean_reactivity + mean_deg_mg_ph10 + mean_deg_mg_50c) / 3.0,
            )
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
            "mean_reactivity": mean_reactivity,
            "mean_deg_mg_ph10": mean_deg_mg_ph10,
            "mean_deg_mg_50c": mean_deg_mg_50c,
            "overall_stability": overall_stability,
            "checkpoint_path": str(payload.get("checkpoint_path", checkpoint_path or "")),
            "device": str(payload.get("device", device or "")),
            "model": payload.get("model", "RNASTOP"),
        }
    except requests.RequestException as exc:
        _raise_service_error(exc, "RNASTOP")


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
        _raise_service_error(exc, "IRESfinder")


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
    timeout_seconds: int = 14400,
    invfold_topk: int = 1,
    invfold_temp: float = 1.0,
    invfold_use_beam: bool = True,
) -> dict[str, Any]:
    """Run ODesign inference from an input JSON file via the ODesign microservice.

    INTERFACE LOCK (v0.3.0): Locked return dict keys. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: ODesignInferenceOutput
    - microservices/odesign_service/main.py :: ODesignInferenceResponse
    - docs/tools/run_odesign_inference.md

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
        timeout_seconds: Subprocess timeout for one ODesign inference request.
        invfold_topk: Number of designed sequences per backbone structure.
        invfold_temp: Inverse folding sampling temperature.
        invfold_use_beam: Whether to use beam search in inverse folding.

    Returns:
        Dict with copied workspace artifacts, output metadata, and ODesign runtime info.

    Raises:
        ValueError: If arguments are invalid or the ODesign service is unreachable.
    """
    if design_modality not in {"protein", "ligand", "dna", "rna"}:
        raise ValueError("design_modality must be one of: protein, ligand, dna, rna.")
    try:
        parsed_seeds = json.loads(seeds_json)
        if not isinstance(parsed_seeds, list) or not parsed_seeds or not all(isinstance(s, int) for s in parsed_seeds):
            raise ValueError
    except Exception:
        raise ValueError("seeds_json must be a non-empty JSON list of integers.")
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
            "timeout_seconds": timeout_seconds,
            "invfold_topk": invfold_topk,
            "invfold_temp": invfold_temp,
            "invfold_use_beam": invfold_use_beam,
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
            timeout=max(21600, timeout_seconds + 600),
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
            "timeout_seconds": payload.get("timeout_seconds", timeout_seconds),
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
        _raise_service_error(exc, "ODesign")


# ---------------------------------------------------------------------------
# LangChain tool sets (single source of truth for graph + tool registry)
# ---------------------------------------------------------------------------


class WorkflowDemoEchoInput(BaseModel):
    """Input for the optional registry/executor smoke-test tool."""

    text: str = Field(..., min_length=1, description="Short text for workflow demo invocations.")


@tool(args_schema=WorkflowDemoEchoInput)
def workflow_demo_echo(text: str) -> dict[str, Any]:
    """Minimal demo tool: echo string and length. Not used by production routing by default."""

    return {"echo": text, "length": len(text), "model": "workflow_demo_echo"}


SIRNA_LANGCHAIN_TOOLS: list[Any] = [
    design_sirna_with_evitar,
    compute_sirna_duplex_binding_vienna,
]
CRISPR_LANGCHAIN_TOOLS: list[Any] = [
    design_sgrna_handle_with_crgpt,
    score_sgrna_handle_with_crgpt,
    score_crispr_off_target_with_crisot,
    score_batch_crispr_off_targets_with_crisot,
    calculate_crispr_specificity_with_crisot,
    search_crispr_off_targets_with_crisot,
    rescore_sgrnas_with_crisot,
    optimize_sgrna_with_crisot,
    predict_crispr_off_target_with_crisot_fp,
    generate_crispr_fingerprint_with_crisot,
]
MRNA_LANGCHAIN_TOOLS: list[Any] = [
    score_rna_ligand_binding_with_gernabind,
    score_rna_ligand_binding_with_rnasmol,
    predict_mrna_stability_with_rnastop,
    predict_putative_ires_with_iresfinder,
    compute_aso_target_accessibility_vienna,
    predict_rna_local_accessibility_profile_vienna,
    inverse_fold_rna_secondary_structure_vienna,
    analyze_cds_codon_metrics_with_codonw_slim,
    compute_rna_sequence_gc_content,
    compute_dot_bracket_unpaired_fraction,
    run_blastn_similarity_search,
    predict_rna_secondary_structure,
    predict_rna_secondary_structure_with_linearfold,
    predict_rna_tertiary_structure_with_rhofold,
    design_mrna_cds_with_lineardesign,
    design_mrna_cds_with_rnarl,
    design_mrna_cds_with_gemorna,
    design_5utr_with_gemorna,
    design_3utr_with_gemorna,
    design_rna_sequence_with_rhodesign,
    design_rna_inverse_fold_with_ribodiffusion,
    run_odesign_inference,
]

ALL_LANGCHAIN_AGENT_TOOLS: list[Any] = (
    SIRNA_LANGCHAIN_TOOLS + CRISPR_LANGCHAIN_TOOLS + MRNA_LANGCHAIN_TOOLS
)

WORKFLOW_DEMO_LANGCHAIN_TOOLS: list[Any] = [workflow_demo_echo]
