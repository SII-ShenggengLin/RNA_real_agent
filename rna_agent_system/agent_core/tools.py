"""LangChain @tool wrappers for RNA design microservices."""

from __future__ import annotations

import json
import os
import random
import re
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
from agent_core.sequence_utils import (
    build_cai_weights,
    compute_cai,
    normalize_cds_sequence,
    resolve_species_name,
    _load_builtin_codon_tables,
)
from agent_core.constants.species import (
    DEFAULT_CAI_SPECIES,
    format_cai_species_aliases,
    DEFAULT_RNARL_MODEL_TYPE,
    RNARL_MODEL_TYPE_TO_CHECKPOINT,
    format_rnarl_model_types,
)

# LinearFold INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 microservices/linearfold_service/main.py 顶部的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。


def _extract_sequence(raw_text: str, *, u_to_t: bool = False) -> str:
    """Parse FASTA-like input, uppercase, and optionally map U→T."""
    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    seq = "".join(lines).upper()
    if u_to_t:
        seq = seq.replace("U", "T")
    return re.sub(r"[^A-Z]", "", seq)


def _validate_sequence(
    sequence: str,
    *,
    allowed: set[str],
    tool_name: str,
    exact_length: int | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
) -> None:
    """Raise ValueError if sequence violates constraints."""
    invalid = sorted(set(ch for ch in sequence if ch not in allowed))
    if invalid:
        raise ValueError(
            f"{tool_name} supports only {'/'.join(sorted(allowed))} input. "
            f"Unsupported characters: {''.join(invalid)}"
        )
    if exact_length is not None and len(sequence) != exact_length:
        raise ValueError(
            f"{tool_name} expects {exact_length}-nt sequences; got {len(sequence)} nt."
        )
    if min_length is not None and len(sequence) < min_length:
        raise ValueError(
            f"{tool_name} expects sequence length ≥ {min_length} nt; got {len(sequence)} nt."
        )
    if max_length is not None and len(sequence) > max_length:
        raise ValueError(
            f"{tool_name} expects sequence length ≤ {max_length} nt; got {len(sequence)} nt."
        )


def _normalize_nucleic_sequence(raw_text: str) -> str:
    """Normalize plain-text or FASTA-like nucleotide input for downstream tools."""
    return _extract_sequence(raw_text).replace("T", "U")


def _normalize_crisot_sequence(raw_text: str) -> str:
    """Normalize CRISOT input to uppercase DNA-like sequence with optional N bases."""
    seq = _extract_sequence(raw_text, u_to_t=True)
    _validate_sequence(seq, allowed={"A", "C", "G", "T", "N"}, tool_name="CRISOT", exact_length=23)
    return seq


def _normalize_sgrna_design_sequence(raw_text: str) -> str:
    """Normalize sgRNA-handle DNA sequence input for sgrna_design service."""
    seq = _extract_sequence(raw_text, u_to_t=True)
    _validate_sequence(seq, allowed={"A", "C", "G", "T"}, tool_name="sgRNA design", min_length=40, max_length=120)
    return seq



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


def _post_json(
    service_url: str,
    payload: dict[str, Any],
    timeout: float,
    service_name: str,
) -> dict[str, Any]:
    """POST *payload* to *service_url* and return the JSON body.

    On any ``requests`` error, delegates to ``_raise_service_error``.
    """
    try:
        response = requests.post(service_url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        _raise_service_error(exc, service_name)


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


# BLAST+ INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 run_blastn_similarity_search 的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。


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
    outfmt: Optional[str] = Field(
        default=None,
        description="Optional blastn -outfmt argument override (default is tabular format 6).",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8019/blastn",
        description="URL for the blast_service POST /blastn endpoint.",
    )


# Bowtie2 INTERFACE LOCK (v0.1.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 run_bowtie2_short_alignment 的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。


class Bowtie2AlignInput(BaseModel):
    """Input schema for Bowtie2 short-sequence alignment (microservice on port 8024)."""

    filepath: str = Field(
        ...,
        description="Query nucleotide sequence file (workspace path or absolute on the server).",
    )
    subject_fasta_path: Optional[str] = Field(
        default=None,
        description="Subject multi-FASTA path (server-side). Indexed with bowtie2-build at runtime.",
    )
    subject_index: Optional[str] = Field(
        default=None,
        description="Existing bowtie2 index prefix path (server-side).",
    )
    mode: str = Field(
        default="local",
        description="local | end-to-end. 'local' allows soft-clipping and is preferred for short oligos.",
    )
    k: int = Field(default=50, ge=1, le=10000, description="Report up to <int> alignments per read.")
    score_min: str = Field(
        default="G,20,8",
        description="bowtie2 --score-min function (default G,20,8).",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8024/align",
        description="URL for the bowtie2_service POST /align endpoint.",
    )


# Evitar INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 design_sirna_with_evitar 的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。

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


# CRISOT INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 CRISOT ToolSpec 注册区域的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。

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


# sgrna_design INTERFACE LOCK (v0.3.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 design_sgrna_handle_with_crgpt 的
# INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。

class SgRNADesignInput(BaseModel):
    """Input schema for sgRNA handle design via sgrna_design_service.

    INTERFACE LOCK (v0.3.0): Locked schema. Modify only in sync with:
    - microservices/sgrna_design_service/main.py :: DesignRequest
    - agent_core/tool_specs.py :: design_sgrna_handle_with_crgpt ToolSpec
    - agent_core/state.py :: sgrna_design_* fields
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
    outfmt: Optional[str] = None,
    service_url: str = "http://127.0.0.1:8019/blastn",
) -> dict[str, Any]:
    """Run NCBI blastn against a subject FASTA or an existing nucleotide BLAST database.

    INTERFACE LOCK (v0.2.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: BlastnSearchOutput / run_blastn_similarity_search ToolSpec
    - agent_core/state.py :: blast_* fields
    - microservices/blast_service/main.py :: BlastnRequest / BlastnResponse

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
        outfmt: Optional blastn -outfmt override (default tabular format 6).
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
    if outfmt is not None:
        payload["outfmt"] = str(outfmt)
    body = _post_json(service_url, payload, 660, "BLAST")

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


@tool(args_schema=Bowtie2AlignInput)
def run_bowtie2_short_alignment(
    filepath: str,
    subject_fasta_path: Optional[str] = None,
    subject_index: Optional[str] = None,
    mode: str = "local",
    k: int = 50,
    score_min: str = "G,20,8",
    service_url: str = "http://127.0.0.1:8024/align",
) -> dict[str, Any]:
    """Run Bowtie2 for fast short-sequence alignment against a subject FASTA or pre-built index.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: Bowtie2AlignOutput / run_bowtie2_short_alignment ToolSpec
    - microservices/bowtie2_service/main.py :: Bowtie2AlignRequest / Bowtie2AlignResponse

    Requires the ``bowtie2_service`` microservice (port 8024) and bowtie2 on the server PATH.
    Provide exactly one of ``subject_fasta_path`` or ``subject_index``. The query is read from
    ``filepath`` (plain sequence or FASTA); nucleotides are normalized to DNA for bowtie2.

    Args:
        filepath: Query sequence file (typically under ``workspace/``).
        subject_fasta_path: Path to subject FASTA on the server (bowtie2-build run in the service).
        subject_index: Prefix path of an existing bowtie2 index.
        mode: ``local`` (allows soft-clipping, preferred for short oligos) or ``end-to-end``.
        k: Maximum alignments to report per query.
        score_min: bowtie2 ``--score-min`` function string.
        service_url: POST endpoint for the bowtie2 microservice.

    Returns:
        Dict with hit counts, preview, paths to saved tabular output under ``workspace/``, and commands.

    Raises:
        ValueError: If arguments are inconsistent or the HTTP call fails.
    """
    if bool(subject_fasta_path) == bool(subject_index):
        raise ValueError("Provide exactly one of subject_fasta_path or subject_index.")
    read_sequence(filepath)  # validate readable before calling remote service
    query_abs = _absolute_path_under_project(filepath)
    payload: dict[str, Any] = {
        "query_filepath": query_abs,
        "mode": mode,
        "k": int(k),
        "score_min": score_min,
    }
    if subject_fasta_path:
        payload["subject_fasta_path"] = (
            subject_fasta_path
            if Path(subject_fasta_path).is_absolute()
            else str((Path(__file__).resolve().parents[1] / subject_fasta_path).resolve())
        )
    else:
        assert subject_index is not None
        payload["subject_index"] = (
            subject_index
            if Path(subject_index).is_absolute()
            else str((Path(__file__).resolve().parents[1] / subject_index).resolve())
        )
    body = _post_json(service_url, payload, 310, "Bowtie2")

    tabular = str(body.get("tabular_output", "") or "")
    summary_path = ""
    if tabular.strip():
        summary_path = save_text_file(tabular, prefix="bowtie2_out", suffix=".sam")

    meta = {
        "hit_count": int(body.get("hit_count", 0)),
        "hits_preview": str(body.get("hits_preview", "")),
        "preview_truncated": bool(body.get("preview_truncated", False)),
        "tabular_output_truncated": bool(body.get("tabular_output_truncated", False)),
        "bowtie2_command": str(body.get("bowtie2_command", "")),
        "bowtie2_build_command": body.get("bowtie2_build_command"),
        "stderr": str(body.get("stderr", ""))[:4000],
        "subject_mode": str(body.get("subject_mode", "")),
        "resolved_query_path": str(body.get("resolved_query_path", query_abs)),
        "resolved_subject": str(body.get("resolved_subject", "")),
        "model": str(body.get("model", "bowtie2")),
        "query_filepath": filepath,
        "tabular_sam_filepath": summary_path,
    }
    return meta


# RNA sequence metrics (GC content) INTERFACE LOCK (v0.1.0) —— 禁止单方面变更

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
    timeout_seconds: float = Field(
        default=120.0,
        gt=0,
        le=600,
        description="HTTP request timeout in seconds.",
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
    timeout_seconds: float = Field(
        default=120.0,
        gt=0.0,
        le=600.0,
        description="HTTP request timeout in seconds.",
    )


# RNA sequence U content INTERFACE LOCK (v0.1.0) —— 禁止单方面变更

class RnaUContentInput(BaseModel):
    """Input schema for RNA/DNA U fraction (microservice on port 8020)."""

    filepath: str = Field(
        ...,
        description="Path to RNA or DNA sequence (workspace or server absolute); FASTA or plain text.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8020/u-content",
        description="POST endpoint for U content microservice.",
    )
    timeout_seconds: float = Field(
        default=120.0,
        gt=0,
        le=600,
        description="HTTP request timeout in seconds.",
    )


@tool(args_schema=RnaGcContentInput)
def compute_rna_sequence_gc_content(
    filepath: str,
    service_url: str = "http://127.0.0.1:8020/gc-content",
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Compute (G+C)/N for an RNA or DNA sequence file (N = count of A/U/G/C after normalization).

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: RnaGcContentOutput / compute_rna_sequence_gc_content ToolSpec
    - agent_core/state.py :: sequence_gc_* fields
    - microservices/rna_sequence_metrics_service/main.py :: GcContentRequest / GcContentResponse

    Requires ``rna_sequence_metrics_service`` on port 8020. Pass a filepath under ``workspace/`` or an
    absolute server path; long sequences should not be pasted into the chat.

    Args:
        filepath: Sequence file (plain or FASTA); T is treated as U, non-letters removed.
        service_url: POST ``/gc-content`` endpoint.
        timeout_seconds: HTTP request timeout in seconds.

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
            timeout=float(timeout_seconds),
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
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Fraction of unpaired bases in a dot-bracket RNA secondary structure: count('.')/length.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: DotBracketUnpairedFractionOutput /
      compute_dot_bracket_unpaired_fraction ToolSpec
    - agent_core/state.py :: dot_bracket_unpaired_fraction / dot_bracket_structure_length /
      dot_bracket_dot_count fields
    - microservices/rna_sequence_metrics_service/main.py ::
      UnpairedFractionRequest / UnpairedFractionResponse

    The structure string must use only ``. ( ) [ ] { } < >`` as in ViennaRNA / LinearFold dot-bracket
    notation. Requires ``rna_sequence_metrics_service`` on port 8020.

    Args:
        filepath: Text file containing the structure (FASTA with structure on sequence line is ok).
        service_url: POST ``/unpaired-fraction`` endpoint.
        timeout_seconds: HTTP request timeout in seconds.

    Returns:
        Dict with ``unpaired_fraction``, ``dot_count``, ``structure_length``, and paths.

    Raises:
        ValueError: If the HTTP call fails or the structure contains invalid characters.
    """
    struct_abs = _absolute_path_under_project(filepath)
    try:
        response = requests.post(
            service_url,
            json={"structure_filepath": struct_abs},
            timeout=float(timeout_seconds),
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


@tool(args_schema=RnaUContentInput)
def compute_rna_sequence_u_content(
    filepath: str,
    service_url: str = "http://127.0.0.1:8020/u-content",
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Compute U/N for an RNA or DNA sequence file (N = count of A/U/G/C after normalization).

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: RnaUContentOutput / compute_rna_sequence_u_content ToolSpec
    - agent_core/state.py :: sequence_u_* fields
    - microservices/rna_sequence_metrics_service/main.py :: UContentRequest / UContentResponse
    - rna_agent_system/docs/CONTRIBUTING.md

    Requires ``rna_sequence_metrics_service`` on port 8020. Pass a filepath under ``workspace/`` or an
    absolute server path; long sequences should not be pasted into the chat.

    Args:
        filepath: Sequence file (plain or FASTA); T is treated as U, non-letters removed.
        service_url: POST ``/u-content`` endpoint.
        timeout_seconds: HTTP request timeout in seconds.

    Returns:
        Dict with ``u_fraction``, counts, and resolved paths.

    Raises:
        ValueError: If the HTTP call fails or the service reports an error.
    """
    read_sequence(filepath)
    seq_abs = _absolute_path_under_project(filepath)
    try:
        response = requests.post(
            service_url,
            json={"sequence_filepath": seq_abs},
            timeout=float(timeout_seconds),
        )
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        _raise_service_error(exc, "RNA sequence metrics (U)")
    return {
        "input_filepath": filepath,
        "resolved_filepath": str(body.get("resolved_filepath", "")),
        "sequence_length": int(body.get("sequence_length", 0)),
        "u_count": int(body.get("u_count", 0)),
        "u_fraction": float(body.get("u_fraction", 0.0)),
        "model": str(body.get("model", "rna-u-content")),
    }


# CAI for CDS INTERFACE LOCK (v0.1.0) —— 禁止单方面变更

class CaiForCdsInput(BaseModel):
    """Input schema for CDS CAI computation using Kazusa codon usage tables."""

    filepath: str = Field(
        ...,
        description="Path to CDS sequence file (workspace or absolute); FASTA or plain text. Must be in-frame (length multiple of 3).",
    )
    species: str = Field(
        default=DEFAULT_CAI_SPECIES,
        description=(
            "Species name for the reference codon usage table. "
            f"Built-in aliases: {format_cai_species_aliases()}. "
            "If no built-in table matches, a custom_codon_table_path must be provided."
        ),
    )
    custom_codon_table_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional path to a custom codon usage JSON file. "
            "Format: {\"codon\": {\"aa\": \"X\", \"fraction\": 0.42}, ...}. "
            "When provided, ``species`` is used only for metadata/labeling."
        ),
    )


@tool(args_schema=CaiForCdsInput)
def compute_cai_for_cds_sequence(
    filepath: str,
    species: str = DEFAULT_CAI_SPECIES,
    custom_codon_table_path: Optional[str] = None,
) -> dict[str, Any]:
    """Compute Codon Adaptation Index (CAI) for a CDS sequence file.

    Uses Kazusa codon usage tables (Sharp & Li weights) by default.
    Supports built-in tables for common species plus custom JSON tables.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: CaiForCdsOutput / compute_cai_for_cds_sequence ToolSpec
    - agent_core/state.py :: cai_for_cds_* fields
    - agent_core/sequence_utils.py :: normalize_cds_sequence / build_cai_weights / compute_cai
    - rna_agent_system/docs/CONTRIBUTING.md

    The input sequence is validated as CDS (length multiple of 3, AUGC only).
    Stop codons (UAA/UAG/UGA) are excluded from the CAI calculation.

    Args:
        filepath: CDS sequence file (plain or FASTA); T is treated as U.
        species: Reference species for built-in codon table.
        custom_codon_table_path: Optional custom codon usage JSON path.

    Returns:
        Dict with ``cai_score``, species, codon counts, and validity metrics.

    Raises:
        ValueError: If the file is unreadable, not a valid CDS, or no codon table found.
    """
    raw = read_sequence(filepath)
    cds_seq = normalize_cds_sequence(raw)

    if custom_codon_table_path:
        import json as _json
        from pathlib import Path as _Path
        p = _Path(custom_codon_table_path)
        if not p.is_file():
            raise ValueError(f"Custom codon table not found: {custom_codon_table_path}")
        with p.open("r", encoding="utf-8") as fh:
            codon_fractions: dict[str, Any] = _json.load(fh)
        if not isinstance(codon_fractions, dict):
            raise ValueError("Custom codon table must be a JSON object.")
        resolved_species = species
    else:
        builtin = _load_builtin_codon_tables()
        resolved_species = resolve_species_name(species)
        if resolved_species not in builtin:
            available = ", ".join(sorted(builtin.keys()))
            raise ValueError(
                f"No built-in codon table for '{species}' (resolved: '{resolved_species}'). "
                f"Available: {available}. Provide a custom_codon_table_path."
            )
        codon_fractions = builtin[resolved_species]

    weights = build_cai_weights(codon_fractions)
    metrics = compute_cai(cds_seq, weights)

    return {
        "input_filepath": filepath,
        "cai_score": float(metrics["cai_score"]),
        "species": resolved_species,
        "cds_length_nt": len(cds_seq),
        "codon_count": int(metrics["codon_count"]),
        "valid_codons": int(metrics["valid_codons"]),
        "invalid_codons": int(metrics["invalid_codons"]),
        "stop_codons_encountered": int(metrics["stop_codons_encountered"]),
        "model": "cai-kazusa",
    }


# ── Junction codon shuffler (pure computation; no microservice) ─────────────

class ShuffleCdsJunctionCodonsInput(BaseModel):
    """Input schema for synonymous codon shuffling at CDS termini."""

    filepath: str = Field(
        ...,
        description="Path to CDS sequence file (workspace or absolute); FASTA or plain text. Must be in-frame (length multiple of 3).",
    )
    junction_end: str = Field(
        ...,
        description="Which terminus to shuffle: 'n_terminus' (first codons, affects 5'UTR-CDS junction) or 'c_terminus' (last codons, affects CDS-3'UTR junction).",
    )
    codon_count: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Number of terminal codons to shuffle.",
    )
    num_variants: int = Field(
        default=8,
        ge=1,
        le=32,
        description="Number of variant sequences to generate.",
    )
    species: str = Field(
        default=DEFAULT_CAI_SPECIES,
        description=(
            "Species name for the reference codon usage table "
            f"(same aliases as compute_cai_for_cds_sequence: {format_cai_species_aliases()})."
        ),
    )
    seed: Optional[int] = Field(
        default=None,
        description="Optional random seed for reproducible variant generation.",
    )


@tool(args_schema=ShuffleCdsJunctionCodonsInput)
def shuffle_cds_junction_codons(
    filepath: str,
    junction_end: str,
    codon_count: int = 6,
    num_variants: int = 8,
    species: str = DEFAULT_CAI_SPECIES,
    seed: Optional[int] = None,
) -> dict[str, Any]:
    """Generate synonymous-codon variants at the N- or C-terminus of a CDS.

    Shuffles ``codon_count`` terminal codons while preserving the amino-acid
    sequence.  Synonymous choices are weighted by the species codon-usage
    table so that high-CAI variants are naturally favored.

    Use this to alter local RNA secondary structure at module junctions
    (5'UTR-CDS or CDS-3'UTR) without changing the encoded protein.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: ShuffleCdsJunctionCodonsOutput / shuffle_cds_junction_codons ToolSpec
    - agent_core/state.py :: shuffle_cds_junction_* fields
    - tests/test_shuffle_cds_junction_codons.py

    Args:
        filepath: CDS sequence file (plain or FASTA); T is treated as U.
        junction_end: ``n_terminus`` or ``c_terminus``.
        codon_count: How many terminal codons to randomize (1--12).
        num_variants: How many independent variants to return (1--32).
        species: Reference species for codon-usage weighting.
        seed: Optional RNG seed for reproducibility.

    Returns:
        Dict with ``original_sequence``, ``junction_end``, ``shuffled_region``
        coordinates, and a ``variants`` list.  Each variant contains the full
        CDS ``sequence``, its ``cai_score``, and a ``changes`` list of
        ``{codon_index, original_codon, new_codon}``.
    """
    raw = read_sequence(filepath)
    cds_seq = normalize_cds_sequence(raw)

    if junction_end not in ("n_terminus", "c_terminus"):
        raise ValueError(
            f"junction_end must be 'n_terminus' or 'c_terminus'; got '{junction_end}'"
        )

    builtin = _load_builtin_codon_tables()
    resolved_species = resolve_species_name(species)
    if resolved_species not in builtin:
        available = ", ".join(sorted(builtin.keys()))
        raise ValueError(
            f"No built-in codon table for '{species}' (resolved: '{resolved_species}'). "
            f"Available: {available}."
        )
    codon_fractions = builtin[resolved_species]

    # Build reverse mapping: amino_acid -> list of (codon, fraction)
    _STOP = {"UAA", "UAG", "UGA"}
    aa_to_codons: dict[str, list[tuple[str, float]]] = {}
    for codon, info in codon_fractions.items():
        aa = info["aa"]
        frac = float(info["fraction"])
        if codon in _STOP:
            continue
        aa_to_codons.setdefault(aa, []).append((codon, frac))

    total_codons = len(cds_seq) // 3
    codon_count = min(codon_count, total_codons)

    if junction_end == "n_terminus":
        region_start = 0
        region_end = codon_count
    else:
        region_start = total_codons - codon_count
        region_end = total_codons

    # Prepare position info
    positions: list[dict[str, Any]] = []
    for ci in range(region_start, region_end):
        orig = cds_seq[ci * 3 : ci * 3 + 3]
        aa = None
        for c, info in codon_fractions.items():
            if c == orig:
                aa = info["aa"]
                break
        if aa is None or aa == "*":
            continue
        syns = aa_to_codons.get(aa, [])
        if len(syns) <= 1:
            continue
        positions.append({
            "codon_index": ci,
            "original": orig,
            "amino_acid": aa,
            "synonyms": syns,
        })

    if not positions:
        return {
            "original_sequence": cds_seq,
            "junction_end": junction_end,
            "shuffled_region_start": region_start,
            "shuffled_region_end": region_end,
            "variants": [],
            "model": "junction-codon-shuffler",
        }

    rng = random.Random(seed)
    weights = build_cai_weights(codon_fractions)

    variants: list[dict[str, Any]] = []
    seen_seqs: set[str] = {cds_seq}

    max_attempts = num_variants * 10
    for _ in range(max_attempts):
        if len(variants) >= num_variants:
            break
        seq_list = list(cds_seq)
        changes: list[dict[str, Any]] = []
        for pos in positions:
            syns = pos["synonyms"]
            # Weighted choice by codon-usage fraction
            chosen, _ = rng.choices(syns, weights=[f for _, f in syns])[0]
            if chosen != pos["original"]:
                ci = pos["codon_index"]
                seq_list[ci * 3 : ci * 3 + 3] = list(chosen)
                changes.append({
                    "codon_index": ci,
                    "original_codon": pos["original"],
                    "new_codon": chosen,
                })
        new_seq = "".join(seq_list)
        if new_seq in seen_seqs:
            continue
        seen_seqs.add(new_seq)
        cai_metrics = compute_cai(new_seq, weights)
        variants.append({
            "sequence": new_seq,
            "cai_score": float(cai_metrics["cai_score"]),
            "changed_codons": len(changes),
            "changes": changes,
        })

    variants.sort(key=lambda v: v["cai_score"], reverse=True)

    return {
        "original_sequence": cds_seq,
        "junction_end": junction_end,
        "shuffled_region_start": region_start,
        "shuffled_region_end": region_end,
        "variants": variants,
        "model": "junction-codon-shuffler",
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
    - microservices/evitar_service/main.py :: EvitarDesignRequest / EvitarDesignResponse

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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Score one sgRNA-target pair with CRISOT.

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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Calculate CRISOT specificity from a CSV of one sgRNA and its candidate off-targets.

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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Run CRISOT genome-wide off-target specificity search using Cas-OFFinder.

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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Optimize one sgRNA with CRISOT-Opti.

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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Batch calculate CRISOT-Score for sgRNA-target pairs in a CSV file.

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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Rescore and rerank a list of sgRNAs using CRISOT genome-wide search.

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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Predict CRISPR off-target effects using CRISOT-FP XGBoost models.

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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Generate CRISOT-FP molecular interaction fingerprint for an sgRNA-target pair.

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
    """
    INTERFACE LOCK (v0.3.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Score a single sgRNA handle sequence using the CRGPT model.

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


# ViennaRNA INTERFACE LOCK (v0.4.0) —— 禁止单方面变更


class FoldViennaInput(BaseModel):
    """Input for ViennaRNA RNAfold (MFE + optional partition function / centroid / MEA)."""

    filepath: str = Field(
        ...,
        description="Path to RNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.",
    )
    temp_c: float = Field(default=37.0, description="Folding temperature (Celsius).")
    dangles: int = Field(default=2, ge=0, le=3, description="Dangling-end model.")
    no_lp: bool = Field(default=False, description="Disallow lonely pairs.")
    no_gu: bool = Field(default=False, description="Disallow GU pairs.")
    no_closing_gu: bool = Field(default=False, description="Disallow GU closing pairs.")
    salt: Optional[float] = Field(default=None, description="Salt concentration (M).")
    no_tetra: bool = Field(default=False, description="Omit special hairpin loop energies.")
    energy_model: Optional[int] = Field(default=None, description="Energy model index.")
    nsp: Optional[str] = Field(default=None, description="Non-standard pair specification.")
    param_file: Optional[str] = Field(default=None, description="Custom parameter file.")
    constraint: Optional[str] = Field(default=None, description="Hard constraint dot-bracket string.")
    shape_file: Optional[str] = Field(default=None, description="Path to SHAPE reactivity data file.")
    shape_method: str = Field(default="D", description="SHAPE method: D, Z, or W.")
    partfunc: bool = Field(default=False, description="Compute partition function and centroid.")
    circ: bool = Field(default=False, description="Assume circular RNA.")
    gquad: bool = Field(default=False, description="Include G-quadruplex formation.")
    service_url: str = Field(default="http://127.0.0.1:8003/fold", description="ViennaRNA fold endpoint.")


# codonw-slim INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
# 关联文件清单见 agent_core/tool_specs.py 中 analyze_cds_codon_metrics_with_codonw_slim
# 的 INTERFACE LOCK 注释。任何修改必须全部同步并重新跑通端到端测试。

class CodonwSlimAnalyzeInput(BaseModel):
    """Input schema for codonw-slim CDS codon-usage metrics.

    Mirrors the upstream CodonSeq API so that the agent can access every
    metric and reference table offered by codonw-slim.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - microservices/codonw_slim_service/main.py :: CodonwAnalyzeRequest
    - agent_core/tool_specs.py :: analyze_cds_codon_metrics_with_codonw_slim ToolSpec
    - agent_core/state.py :: codonw_* fields
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
    sharpturn: bool = Field(
        default=False,
        description="Enable sharpturn in prediction.",
    )
    constraints: Optional[str] = Field(
        default=None,
        description=(
            "Optional constraint string (? . ( ) ) for constrained prediction. "
            "If provided, length must match the sequence."
        ),
    )
    shape_file_path: Optional[str] = Field(
        default=None,
        description="Optional path to SHAPE reactivity data file (mutually exclusive with constraints).",
    )


class LinearFoldEvalInput(BaseModel):
    """Input schema for LinearFold energy evaluation (eval mode)."""

    sequence_filepath: str = Field(
        ...,
        description="Path to a workspace file containing the RNA sequence.",
    )
    structure_filepath: str = Field(
        ...,
        description="Path to a workspace file containing the dot-bracket structure.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8015/eval",
        description="REST endpoint for the LinearFold eval microservice.",
    )
    use_vienna: bool = Field(
        default=False,
        description="If true, request LinearFold-V (Vienna energy parameters).",
    )
    dangles: int = Field(
        default=2,
        description="Dangling-end model: 0 or 2.",
    )
    verbose: bool = Field(
        default=False,
        description="Return per-loop energy decomposition.",
    )


class LinearFoldZukerSuboptInput(BaseModel):
    """Input schema for LinearFold Zuker suboptimal structures."""

    filepath: str = Field(
        ...,
        description="Path to a workspace file containing RNA sequence (plain or FASTA).",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8015/fold/zuker_subopt",
        description="REST endpoint for the LinearFold Zuker subopt microservice.",
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
        description="Dangling-end model: 0 or 2.",
    )
    sharpturn: bool = Field(
        default=False,
        description="Enable sharpturn in prediction.",
    )
    delta: float = Field(
        default=5.0,
        ge=0.0,
        description="Energy range (kcal/mol) for suboptimal structures.",
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


class Gemorna5UtrPredictionInput(BaseModel):
    """Input schema for GEMORNA 5'UTR MRL prediction tool.

    INTERFACE LOCK (v0.1.0): Locked schema. Modify only in sync with:
    - microservices/gemorna_service/main.py :: UtrPredictionRequest
    - agent_core/tool_specs.py :: predict_5utr_mrl_with_gemorna ToolSpec
    """

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace file containing the 5'UTR RNA sequence. "
            "Do not pass raw sequence text directly."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8004/predict/5utr_mrl",
        description="REST endpoint for the GEMORNA 5'UTR MRL prediction microservice.",
    )


class Gemorna3UtrPredictionInput(BaseModel):
    """Input schema for GEMORNA 3'UTR stability prediction tool.

    INTERFACE LOCK (v0.1.0): Locked schema. Modify only in sync with:
    - microservices/gemorna_service/main.py :: UtrPredictionRequest
    - agent_core/tool_specs.py :: predict_3utr_stability_with_gemorna ToolSpec
    """

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace file containing the 3'UTR RNA sequence. "
            "Do not pass raw sequence text directly."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8004/predict/3utr_stability",
        description="REST endpoint for the GEMORNA 3'UTR stability prediction microservice.",
    )


# LinearDesign INTERFACE LOCK (v0.2.0) —— 禁止单方面变更


class LinearDesignCdsInput(BaseModel):
    """Input schema for LinearDesign CDS design tool (single sequence).

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - microservices/lineardesign_service/main.py :: LinearDesignRequest
    - agent_core/tool_specs.py :: design_mrna_cds_with_lineardesign ToolSpec
    - agent_core/state.py :: lineardesign_* fields
    """

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


class LinearDesignCdsBatchInput(BaseModel):
    """Input schema for LinearDesign CDS batch design tool.

    Mirrors the upstream ``cat FASTA_FILE | ./lineardesign`` capability by
    accepting a FASTA (or plain-text) file with one or more protein sequences.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - microservices/lineardesign_service/main.py :: LinearDesignBatchRequest
    - agent_core/tool_specs.py :: design_mrna_cds_batch_with_lineardesign ToolSpec
    - agent_core/state.py :: lineardesign_* fields
    """

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace file containing one or more protein sequences. "
            "FASTA format with '>' headers is supported; plain text (one sequence per line) is also accepted."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8014/generate/cds/batch",
        description="REST endpoint for the LinearDesign CDS batch microservice.",
    )
    lambda_value: float = Field(
        default=0.0,
        ge=0.0,
        description="LinearDesign lambda balancing MFE and CAI (applied to all sequences).",
    )
    codon_usage_path: Optional[str] = Field(
        default=None,
        description="Optional codon usage CSV path passed through to LinearDesign service.",
    )
    verbose: bool = Field(
        default=False,
        description="Whether to enable verbose output in LinearDesign.",
    )


# Junction-aware LinearDesign tool (2026-08, additive; v0.2.0 locked schemas above
# are untouched). Mirrors microservices/lineardesign_service/main.py ::
# LinearDesignJunctionAwareRequest (/generate/cds_junction_aware).


class LinearDesignCdsJunctionAwareInput(BaseModel):
    """Input schema for junction-aware LinearDesign CDS design tool.

    Synchronized with:
    - microservices/lineardesign_service/main.py :: LinearDesignJunctionAwareRequest
    - agent_core/tool_specs.py :: design_mrna_cds_junction_aware_with_lineardesign ToolSpec
    """

    filepath: str = Field(
        ...,
        description=(
            "Path to a workspace file containing a protein sequence for LinearDesign CDS design. "
            "Do not pass raw sequence text directly."
        ),
    )
    protein_sequence: Optional[str] = Field(
        default=None,
        description="Optional explicit protein sequence; when provided (non-empty) it "
        "overrides the sequence read from filepath.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8014/generate/cds_junction_aware",
        description="REST endpoint for the junction-aware LinearDesign CDS microservice.",
    )
    lambda_value: float = Field(
        default=0.0,
        ge=0.0,
        description="LinearDesign lambda balancing MFE and CAI.",
    )
    utr5_flank: Optional[str] = Field(
        default=None,
        description="Optional 5' UTR flank RNA sequence; the junction-side flank_nt "
        "(default 21) nt are folded as fixed sequence with the CDS.",
    )
    utr3_flank: Optional[str] = Field(
        default=None,
        description="Optional 3' UTR flank RNA sequence; the junction-side flank_nt "
        "(default 21) nt are folded as fixed sequence with the CDS.",
    )
    junction_weight: float = Field(
        default=0.0,
        ge=0.0,
        description="w_jun: penalty in kcal/mol per newly formed base pair touching a "
        "junction window (0 disables the penalty).",
    )
    junction_window_nt: int = Field(
        default=20,
        gt=0,
        description="Half-width (nt) of the junction windows around the flank|CDS boundaries.",
    )
    flank_nt: int = Field(
        default=21,
        description="Number of junction-side flank nucleotides used per side; must be "
        "a multiple of 3 and >= 3.",
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
        default=DEFAULT_RNARL_MODEL_TYPE,
        description=(
            "RNARL trained model variant (species / RNA type). "
            f"Supported values: {format_rnarl_model_types()}."
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
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducible sampling. If omitted, the service generates a per-call seed.",
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


# RiboDiffusion INTERFACE LOCK (v0.2.0) —— 禁止单方面变更

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


# RNAsmOL 接口冻结声明 (v0.2.0) —— 禁止单方面变更
# 关联文件清单（修改时必须全部同步）：
#   - microservices/rnasmol_service/main.py
#   - agent_core/tools.py  ← 本文件
#   - agent_core/tool_specs.py
#   - agent_core/state.py
# 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
# 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。

class RNAsmolScoreInput(BaseModel):
    """Input schema for RNAsmol RNA-ligand scoring.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - microservices/rnasmol_service/main.py :: ScoreRequest
    - agent_core/tool_specs.py :: score_rna_ligand_binding_with_rnasmol ToolSpec
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


class EGARPSInput(BaseModel):
    """Input schema for EGARPS+ RNA-protein complex scoring.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - microservices/egarps_service/main.py :: EGARPSRequest
    - agent_core/tool_specs.py :: score_rna_protein_complex_with_egarps ToolSpec
    """

    filepath: str = Field(
        ...,
        description="Path to a PDB file containing the RNA-protein complex structure.",
    )
    academic: bool = Field(
        default=False,
        description=(
            "If True, use full academic mode (requires DSSR and NACCESS licenses). "
            "If False, use non-academic mode with reduced features."
        ),
    )
    service_url: str = Field(
        default="http://127.0.0.1:8023/score",
        description="REST endpoint for the EGARPS+ microservice.",
    )


class RNASTOPPredictionInput(BaseModel):
    """Input schema for RNASTOP stability prediction.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be
    synchronized with:
    - microservices/rnastop_service/main.py :: StabilityPredictionRequest
    - agent_core/tool_specs.py :: predict_mrna_stability_with_rnastop ToolSpec

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
    data = _post_json(service_url, payload, 120, "codonw-slim")

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


@tool(args_schema=FoldViennaInput)
def predict_rna_secondary_structure(
    filepath: str,
    temp_c: float = 37.0,
    dangles: int = 2,
    no_lp: bool = False,
    no_gu: bool = False,
    no_closing_gu: bool = False,
    salt: Optional[float] = None,
    no_tetra: bool = False,
    energy_model: Optional[int] = None,
    nsp: Optional[str] = None,
    param_file: Optional[str] = None,
    constraint: Optional[str] = None,
    shape_file: Optional[str] = None,
    shape_method: str = "D",
    partfunc: bool = False,
    circ: bool = False,
    gquad: bool = False,
    service_url: str = "http://127.0.0.1:8003/fold",
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.4.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Predict RNA secondary structure and MFE using ViennaRNA RNAfold.

    Supports partition function (-p), constraints (-C), SHAPE-guided folding,
    circular RNA (--circ), G-quadruplexes (--gquad), and full energy-model tuning.

    Args:
        filepath: Workspace file path containing RNA sequence.
        temp_c, dangles, no_lp, no_gu, no_closing_gu, salt, no_tetra,
        energy_model, nsp, param_file: Energy-model parameters.
        constraint: Hard constraint dot-bracket string.
        shape_file: Path to SHAPE reactivity data file.
        shape_method: SHAPE method (D/Z/W).
        partfunc: Compute partition function and centroid structure.
        circ: Assume circular RNA.
        gquad: Include G-quadruplex formation.
        service_url: REST endpoint for ViennaRNA fold microservice.

    Returns:
        Dict containing structure, mfe, and optional ensemble/centroid/MEA fields.
    """
    sequence = _normalize_nucleic_sequence(read_sequence(filepath))
    payload: dict[str, Any] = {
        "sequence": sequence,
        "params": {
            "temp_c": temp_c,
            "dangles": dangles,
            "noLP": no_lp,
            "noGU": no_gu,
            "noClosingGU": no_closing_gu,
            "salt": salt,
            "noTetra": no_tetra,
            "energyModel": energy_model,
            "nsp": nsp,
            "paramFile": param_file,
        },
        "constraint": constraint,
        "shape_file": shape_file,
        "shape_method": shape_method,
        "partfunc": partfunc,
        "circ": circ,
        "gquad": gquad,
    }
    body = _post_json(service_url, payload, 60, "ViennaRNA RNAfold")
    if "structure" not in body or "mfe" not in body:
        raise ValueError("Missing `structure` or `mfe` in ViennaRNA response.")
    return {
        "input_filepath": filepath,
        "structure": str(body["structure"]),
        "mfe_kcal_per_mol": float(body["mfe"]),
        "backend": str(body.get("backend", "")),
        "model": str(body.get("model", "ViennaRNA-RNAfold")),
        "ensemble_free_energy": body.get("ensemble_free_energy"),
        "centroid_structure": body.get("centroid_structure"),
        "centroid_distance": body.get("centroid_distance"),
        "mea_structure": body.get("mea_structure"),
        "mea_score": body.get("mea_score"),
        "mea_gamma": body.get("mea_gamma"),
    }


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
    temp_c: float = Field(default=37.0, description="Folding temperature (Celsius).")
    dangles: int = Field(default=2, ge=0, le=3, description="Dangling-end model.")
    no_lp: bool = Field(default=False, description="Disallow lonely pairs.")
    no_gu: bool = Field(default=False, description="Disallow GU pairs.")
    no_closing_gu: bool = Field(default=False, description="Disallow GU closing pairs.")
    salt: Optional[float] = Field(default=None, description="Salt concentration (M).")
    no_tetra: bool = Field(default=False, description="Omit special hairpin loop energies.")
    energy_model: Optional[int] = Field(default=None, description="Energy model index.")
    nsp: Optional[str] = Field(default=None, description="Non-standard pair specification.")
    param_file: Optional[str] = Field(default=None, description="Custom parameter file.")
    constraint: Optional[str] = Field(default=None, description="Hard constraint dot-bracket string.")
    shape_file: Optional[str] = Field(default=None, description="Path to SHAPE reactivity data file.")
    shape_method: str = Field(default="D", description="SHAPE method: D, Z, or W.")
    concentrations: bool = Field(default=False, description="Compute equilibrium concentrations.")
    conc_a: Optional[float] = Field(default=None, description="Initial monomer A concentration [mol/L].")
    conc_b: Optional[float] = Field(default=None, description="Initial monomer B concentration [mol/L].")
    partfunc: bool = Field(default=False, description="Compute partition function for dimer.")
    service_url: str = Field(
        default="http://127.0.0.1:8003/sirna-duplex",
        description="REST endpoint for ViennaRNA duplex cofold.",
    )


class RnaUpViennaInput(BaseModel):
    """Input for ViennaRNA RNAup RNA-RNA interaction thermodynamics."""

    filepath1: str = Field(..., description="Workspace file with first RNA sequence (target, typically longer).")
    filepath2: str = Field(..., description="Workspace file with second RNA sequence (probe / small RNA).")
    temp_c: float = Field(default=37.0, description="Folding temperature (Celsius).")
    dangles: int = Field(default=2, ge=0, le=3, description="Dangling-end model.")
    no_lp: bool = Field(default=False, description="Disallow lonely pairs.")
    no_gu: bool = Field(default=False, description="Disallow GU pairs.")
    no_closing_gu: bool = Field(default=False, description="Disallow GU closing pairs.")
    salt: Optional[float] = Field(default=None, description="Salt concentration (M).")
    no_tetra: bool = Field(default=False, description="Omit special hairpin loop energies.")
    energy_model: Optional[int] = Field(default=None, description="Energy model index.")
    nsp: Optional[str] = Field(default=None, description="Non-standard pair specification.")
    param_file: Optional[str] = Field(default=None, description="Custom parameter file.")
    ulength: int = Field(default=4, ge=1, le=100, description="Length of unstructured region (-u).")
    window: int = Field(default=25, ge=1, le=1000, description="Maximal interaction region length (-w).")
    include_both: bool = Field(default=False, description="Include unpaired probabilities in both RNAs (-b).")
    extend5: int = Field(default=0, ge=0, description="Extend interaction on 5' side (-5).")
    extend3: int = Field(default=0, ge=0, description="Extend interaction on 3' side (-3).")
    contributions: str = Field(default="S", description="Contributions to output (-c): S, H, I, M, E.")
    service_url: str = Field(
        default="http://127.0.0.1:8003/rnaup",
        description="REST endpoint for ViennaRNA RNAup.",
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
    temp_c: float = Field(default=37.0, description="Temperature in Celsius.")
    dangles: int = Field(default=2, ge=0, le=3, description="Dangling-end model.")
    no_lp: bool = Field(default=False, description="Disallow lonely pairs.")
    no_gu: bool = Field(default=False, description="Disallow GU pairs.")
    no_closing_gu: bool = Field(default=False, description="Disallow GU closing pairs.")
    salt: Optional[float] = Field(default=None, description="Salt concentration (M).")
    no_tetra: bool = Field(default=False, description="Omit special hairpin loop energies.")
    energy_model: Optional[int] = Field(default=None, description="Energy model index.")
    nsp: Optional[str] = Field(default=None, description="Non-standard pair specification.")
    param_file: Optional[str] = Field(default=None, description="Custom parameter file.")
    winsize: int = Field(default=70, ge=3, le=800, description="RNAplfold window size -W.")
    span: int = Field(default=70, ge=2, le=800, description="RNAplfold max pair span -L.")
    unpaired_ulength: int = Field(default=25, ge=1, le=500, description="RNAplfold -u upper bound (auto-expanded server-side).")
    cutoff: Optional[float] = Field(default=None, description="RNAplfold -c probability cutoff.")
    opening_energies: bool = Field(default=False, description="RNAplfold -O: return opening energies instead of probabilities.")


class PlfoldLocalProfileViennaInput(BaseModel):
    """Input for whole-sequence RNAplfold local (single-nt) unpaired probability profile."""

    filepath: str = Field(..., description="Workspace file with RNA sequence (plain or FASTA).")
    service_url: str = Field(
        default="http://127.0.0.1:8003/plfold-profiles",
        description="REST endpoint for ViennaRNA RNAplfold profile (lunp column 1).",
    )
    temp_c: float = Field(default=37.0, description="Temperature in Celsius.")
    dangles: int = Field(default=2, ge=0, le=3, description="Dangling-end model.")
    no_lp: bool = Field(default=False, description="Disallow lonely pairs.")
    no_gu: bool = Field(default=False, description="Disallow GU pairs.")
    no_closing_gu: bool = Field(default=False, description="Disallow GU closing pairs.")
    salt: Optional[float] = Field(default=None, description="Salt concentration (M).")
    no_tetra: bool = Field(default=False, description="Omit special hairpin loop energies.")
    energy_model: Optional[int] = Field(default=None, description="Energy model index.")
    nsp: Optional[str] = Field(default=None, description="Non-standard pair specification.")
    param_file: Optional[str] = Field(default=None, description="Custom parameter file.")
    winsize: int = Field(default=70, ge=3, le=800, description="RNAplfold -W window size.")
    span: int = Field(default=70, ge=2, le=800, description="RNAplfold -L max pair span.")
    unpaired_ulength: int = Field(
        default=25,
        ge=1,
        le=500,
        description="RNAplfold -u upper bound for stretch probabilities in lunp output.",
    )
    cutoff: Optional[float] = Field(default=None, description="RNAplfold -c probability cutoff.")
    opening_energies: bool = Field(default=False, description="RNAplfold -O: return opening energies instead of probabilities.")


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
    dangles: int = Field(default=2, ge=0, le=3, description="Dangling-end model.")
    no_gu: bool = Field(default=False, description="Disallow GU pairs.")
    no_closing_gu: bool = Field(default=False, description="Disallow GU closing pairs.")
    salt: Optional[float] = Field(default=None, description="Salt concentration (M).")
    no_tetra: bool = Field(default=False, description="Omit special hairpin loop energies.")
    energy_model: Optional[int] = Field(default=None, description="Energy model index.")
    nsp: Optional[str] = Field(default=None, description="Non-standard pair specification.")
    param_file: Optional[str] = Field(default=None, description="Custom parameter file.")
    function_mode: str = Field(
        default="m",
        description="RNAinverse -F: m (MFE target), p (partition), or mp.",
    )
    final_cost: Optional[float] = Field(default=None, description="RNAinverse -f: stop threshold for -Fp.")
    alphabet: Optional[str] = Field(default=None, description="RNAinverse -a: custom nucleotide alphabet.")


@tool(args_schema=SirnaDuplexViennaInput)
def compute_sirna_duplex_binding_vienna(
    filepath: str,
    temp_c: float = 37.0,
    dangles: int = 2,
    no_lp: bool = False,
    no_gu: bool = False,
    no_closing_gu: bool = False,
    salt: Optional[float] = None,
    no_tetra: bool = False,
    energy_model: Optional[int] = None,
    nsp: Optional[str] = None,
    param_file: Optional[str] = None,
    constraint: Optional[str] = None,
    shape_file: Optional[str] = None,
    shape_method: str = "D",
    concentrations: bool = False,
    conc_a: Optional[float] = None,
    conc_b: Optional[float] = None,
    partfunc: bool = False,
    service_url: str = "http://127.0.0.1:8003/sirna-duplex",
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.4.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Compute siRNA sense/antisense duplex MFE via ViennaRNA RNAcofold.

    Supports concentration-dependent equilibrium analysis (-c) and partition function (-p).
    """
    raw = read_sequence(filepath)
    sense, antisense = _parse_two_rna_strands_from_file(raw)
    payload: dict[str, Any] = {
        "sense": sense,
        "antisense": antisense,
        "params": {
            "temp_c": temp_c,
            "dangles": dangles,
            "noLP": no_lp,
            "noGU": no_gu,
            "noClosingGU": no_closing_gu,
            "salt": salt,
            "noTetra": no_tetra,
            "energyModel": energy_model,
            "nsp": nsp,
            "paramFile": param_file,
        },
        "constraint": constraint,
        "shape_file": shape_file,
        "shape_method": shape_method,
        "concentrations": concentrations,
        "conc_A": conc_a,
        "conc_B": conc_b,
        "partfunc": partfunc,
    }
    body = _post_json(service_url, payload, 120, "ViennaRNA duplex")
    if "mfe" not in body or "structure" not in body:
        raise ValueError("Invalid duplex response: expected `mfe` and `structure`.")
    return {
        "input_filepath": filepath,
        "sense": str(body.get("sense", sense)),
        "antisense": str(body.get("antisense", antisense)),
        "cofold_sequence": str(body.get("cofold_sequence", "")),
        "structure": str(body["structure"]),
        "mfe_kcal_per_mol": float(body["mfe"]),
        "backend": str(body.get("backend", "")),
        "model": str(body.get("model", "ViennaRNA-RNAcofold")),
        "ensemble_free_energy": body.get("ensemble_free_energy"),
        "equilibrium_concentrations": body.get("equilibrium_concentrations"),
    }


@tool(args_schema=RnaUpViennaInput)
def compute_rna_rna_interaction_vienna(
    filepath1: str,
    filepath2: str,
    temp_c: float = 37.0,
    dangles: int = 2,
    no_lp: bool = False,
    no_gu: bool = False,
    no_closing_gu: bool = False,
    salt: Optional[float] = None,
    no_tetra: bool = False,
    energy_model: Optional[int] = None,
    nsp: Optional[str] = None,
    param_file: Optional[str] = None,
    ulength: int = 4,
    window: int = 25,
    include_both: bool = False,
    extend5: int = 0,
    extend3: int = 0,
    contributions: str = "S",
    service_url: str = "http://127.0.0.1:8003/rnaup",
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.4.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Compute RNA-RNA interaction thermodynamics via ViennaRNA RNAup.

    Returns interaction energy, structure, and raw stdout for downstream parsing.
    """
    seq1 = _normalize_nucleic_sequence(read_sequence(filepath1))
    seq2 = _normalize_nucleic_sequence(read_sequence(filepath2))
    payload: dict[str, Any] = {
        "sequence1": seq1,
        "sequence2": seq2,
        "params": {
            "temp_c": temp_c,
            "dangles": dangles,
            "noLP": no_lp,
            "noGU": no_gu,
            "noClosingGU": no_closing_gu,
            "salt": salt,
            "noTetra": no_tetra,
            "energyModel": energy_model,
            "nsp": nsp,
            "paramFile": param_file,
        },
        "ulength": ulength,
        "window": window,
        "include_both": include_both,
        "extend5": extend5,
        "extend3": extend3,
        "contributions": contributions,
    }
    body = _post_json(service_url, payload, 300, "ViennaRNA RNAup")
    return {
        "input_filepath1": filepath1,
        "input_filepath2": filepath2,
        "sequence1": seq1,
        "sequence2": seq2,
        "interaction_energy": body.get("interaction_energy"),
        "interaction_structure": body.get("interaction_structure"),
        "raw_stdout": body.get("raw_stdout", ""),
        "backend": str(body.get("backend", "")),
        "model": str(body.get("model", "ViennaRNA-RNAup")),
    }


@tool(args_schema=AsoAccessibilityViennaInput)
def compute_aso_target_accessibility_vienna(
    filepath: str,
    region_start: int,
    region_end: int,
    service_url: str = "http://127.0.0.1:8003/aso-accessibility",
    aso_oligo_length: int = 18,
    temp_c: float = 37.0,
    dangles: int = 2,
    no_lp: bool = False,
    no_gu: bool = False,
    no_closing_gu: bool = False,
    salt: Optional[float] = None,
    no_tetra: bool = False,
    energy_model: Optional[int] = None,
    nsp: Optional[str] = None,
    param_file: Optional[str] = None,
    winsize: int = 70,
    span: int = 70,
    unpaired_ulength: int = 25,
    cutoff: Optional[float] = None,
    opening_energies: bool = False,
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.4.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Estimate target mRNA local accessibility (RNAplfold) for an ASO binding region.

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
    payload: dict[str, Any] = {
        "sequence": sequence_text,
        "region_start": region_start,
        "region_end": region_end,
        "aso_oligo_length": aso_oligo_length,
        "params": {
            "temp_c": temp_c,
            "dangles": dangles,
            "noLP": no_lp,
            "noGU": no_gu,
            "noClosingGU": no_closing_gu,
            "salt": salt,
            "noTetra": no_tetra,
            "energyModel": energy_model,
            "nsp": nsp,
            "paramFile": param_file,
        },
        "winsize": winsize,
        "span": span,
        "unpaired_ulength": unpaired_ulength,
        "cutoff": cutoff,
        "opening_energies": opening_energies,
    }
    body = _post_json(service_url, payload, 600, "ViennaRNA accessibility")
    return {
        "input_filepath": filepath,
        "sequence_length": int(body.get("sequence_length", 0)),
        "region_start": int(body.get("region_start", region_start)),
        "region_end": int(body.get("region_end", region_end)),
        "mean_unpaired_prob_single_nt": body.get("mean_unpaired_prob_single_nt"),
        "joint_unpaired_prob_stretch_ending_at_region_end": body.get(
            "joint_unpaired_prob_stretch_ending_at_region_end"
        ),
        "aso_oligo_length_used": int(body.get("aso_oligo_length_used", aso_oligo_length)),
        "plfold_winsize": int(body.get("winsize", winsize)),
        "plfold_span": int(body.get("span", span)),
        "plfold_unpaired_ulength": int(body.get("unpaired_ulength", unpaired_ulength)),
        "backend": str(body.get("backend", "")),
        "model": str(body.get("model", "ViennaRNA-RNAplfold")),
    }


@tool(args_schema=PlfoldLocalProfileViennaInput)
def predict_rna_local_accessibility_profile_vienna(
    filepath: str,
    service_url: str = "http://127.0.0.1:8003/plfold-profiles",
    temp_c: float = 37.0,
    dangles: int = 2,
    no_lp: bool = False,
    no_gu: bool = False,
    no_closing_gu: bool = False,
    salt: Optional[float] = None,
    no_tetra: bool = False,
    energy_model: Optional[int] = None,
    nsp: Optional[str] = None,
    param_file: Optional[str] = None,
    winsize: int = 70,
    span: int = 70,
    unpaired_ulength: int = 25,
    cutoff: Optional[float] = None,
    opening_energies: bool = False,
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.4.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Run ViennaRNA ``RNAplfold`` for local single-nucleotide unpaired probabilities (accessibility curve).

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
    payload: dict[str, Any] = {
        "sequence": sequence_text,
        "params": {
            "temp_c": temp_c,
            "dangles": dangles,
            "noLP": no_lp,
            "noGU": no_gu,
            "noClosingGU": no_closing_gu,
            "salt": salt,
            "noTetra": no_tetra,
            "energyModel": energy_model,
            "nsp": nsp,
            "paramFile": param_file,
        },
        "winsize": winsize,
        "span": span,
        "unpaired_ulength": unpaired_ulength,
        "cutoff": cutoff,
        "opening_energies": opening_energies,
    }
    body = _post_json(service_url, payload, 600, "ViennaRNA RNAplfold profile")
    required = ("positions", "unpaired_prob_1nt", "sequence_length")
    if any(k not in body for k in required):
        raise ValueError(f"Invalid plfold-profiles response; expected keys {required}.")
    positions = body["positions"]
    probs = body["unpaired_prob_1nt"]
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
        "sequence_length": int(body.get("sequence_length", 0)),
        "positions": positions,
        "unpaired_prob_1nt": probs,
        "profile_positions_count": len(positions),
        "mean_unpaired_prob_1nt": float(body.get("mean_unpaired_prob_1nt", 0.0)),
        "min_unpaired_prob_1nt": float(body.get("min_unpaired_prob_1nt", 0.0)),
        "max_unpaired_prob_1nt": float(body.get("max_unpaired_prob_1nt", 0.0)),
        "plfold_winsize": int(body.get("winsize", winsize)),
        "plfold_span": int(body.get("span", span)),
        "plfold_unpaired_ulength_effective": int(body.get("unpaired_ulength_effective", unpaired_ulength)),
        "lunp_profile_tsv_filepath": out_fp,
        "backend": str(body.get("backend", "")),
        "model": str(body.get("model", "ViennaRNA-RNAplfold")),
    }


@tool(args_schema=InverseFoldViennaInput)
def inverse_fold_rna_secondary_structure_vienna(
    filepath: str,
    service_url: str = "http://127.0.0.1:8003/inverse-fold",
    repeats: int = 1,
    temp_c: float = 37.0,
    dangles: int = 2,
    no_gu: bool = False,
    no_closing_gu: bool = False,
    salt: Optional[float] = None,
    no_tetra: bool = False,
    energy_model: Optional[int] = None,
    nsp: Optional[str] = None,
    param_file: Optional[str] = None,
    function_mode: str = "m",
    final_cost: Optional[float] = None,
    alphabet: Optional[str] = None,
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.4.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Inverse-fold an RNA secondary structure to a sequence (ViennaRNA RNAinverse).

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
    payload: dict[str, Any] = {
        "structure": structure,
        "start_sequence": start_sequence,
        "params": {
            "temp_c": temp_c,
            "dangles": dangles,
            "noGU": no_gu,
            "noClosingGU": no_closing_gu,
            "salt": salt,
            "noTetra": no_tetra,
            "energyModel": energy_model,
            "nsp": nsp,
            "paramFile": param_file,
        },
        "repeats": repeats,
        "function_mode": function_mode,
        "final_cost": final_cost,
        "alphabet": alphabet,
    }
    body = _post_json(service_url, payload, 300, "ViennaRNA inverse-fold")
    if "best_sequence" not in body:
        raise ValueError("Invalid inverse-fold response: missing `best_sequence`.")
    out = {
        "input_filepath": filepath,
        "target_structure": str(body.get("structure", structure)),
        "best_sequence": str(body["best_sequence"]),
        "hamming_distance": body.get("hamming_distance"),
        "partition_probability": body.get("partition_probability"),
        "backend": str(body.get("backend", "")),
        "model": str(body.get("model", "ViennaRNA-RNAinverse")),
    }
    best_fp = save_sequence(str(body["best_sequence"]), prefix="vienna_inverse")
    out["best_sequence_filepath"] = best_fp
    return out


@tool(args_schema=LinearFoldSecondaryInput)
def predict_rna_secondary_structure_with_linearfold(
    filepath: str,
    service_url: str = "http://127.0.0.1:8015/fold",
    beam_size: int = 100,
    use_vienna: bool = False,
    dangles: int = 2,
    sharpturn: bool = False,
    constraints: Optional[str] = None,
    shape_file_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Predict RNA secondary structure and MFE using the LinearFold service.

    Args:
        filepath: Workspace file path containing RNA sequence content.
        service_url: REST endpoint for the LinearFold fold microservice.
        beam_size: LinearFold beam size (default 100).
        use_vienna: Use LinearFold-V (Vienna parameters) when True.
        dangles: 0 or 2 for dangling-end treatment.
        sharpturn: Enable sharpturn in prediction.
        constraints: Optional constraint string (? . ( ) ) for constrained prediction.
        shape_file_path: Optional path to SHAPE reactivity data file.

    Returns:
        Dict with sequence, structure, mfe, backend, model, and input filepath.

    Raises:
        ValueError: If the LinearFold request fails or the response is invalid.
    """
    sequence = read_sequence(filepath).strip()
    if dangles not in (0, 2):
        raise ValueError("LinearFold dangles must be 0 or 2.")
    body: dict[str, Any] = {
        "sequence": sequence,
        "beam_size": beam_size,
        "use_vienna": use_vienna,
        "dangles": dangles,
        "sharpturn": sharpturn,
    }
    if constraints is not None:
        body["constraints"] = constraints
    if shape_file_path is not None:
        body["shape_file_path"] = shape_file_path
    try:
        response = requests.post(service_url, json=body, timeout=600)
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


@tool(args_schema=LinearFoldEvalInput)
def evaluate_rna_structure_with_linearfold(
    sequence_filepath: str,
    structure_filepath: str,
    service_url: str = "http://127.0.0.1:8015/eval",
    use_vienna: bool = False,
    dangles: int = 2,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Evaluate free energy of a known RNA structure using LinearFold.

    Args:
        sequence_filepath: Workspace file path containing the RNA sequence.
        structure_filepath: Workspace file path containing the dot-bracket structure.
        service_url: REST endpoint for the LinearFold eval microservice.
        use_vienna: Use LinearFold-V (Vienna parameters) when True.
        dangles: 0 or 2 for dangling-end treatment.
        verbose: Return per-loop energy decomposition.

    Returns:
        Dict with sequence, structure, energy, backend, model, and input filepath.
    """
    sequence = read_sequence(sequence_filepath).strip()
    structure = read_sequence(structure_filepath).strip()
    if dangles not in (0, 2):
        raise ValueError("LinearFold dangles must be 0 or 2.")
    try:
        response = requests.post(
            service_url,
            json={
                "sequence": sequence,
                "structure": structure,
                "use_vienna": use_vienna,
                "dangles": dangles,
                "verbose": verbose,
            },
            timeout=600,
        )
        response.raise_for_status()
        payload = response.json()
        if "energy" not in payload:
            raise ValueError("Missing `energy` in LinearFold eval response.")
        return {
            "sequence_filepath": sequence_filepath,
            "structure_filepath": structure_filepath,
            "sequence": str(payload.get("sequence", "")),
            "structure": str(payload.get("structure", "")),
            "energy": float(payload["energy"]),
            "backend": str(payload.get("backend", "")),
            "model": str(payload.get("model", "LinearFold")),
            "verbose_details": payload.get("verbose_details"),
        }
    except requests.RequestException as exc:
        _raise_service_error(exc, "LinearFold")


@tool(args_schema=LinearFoldZukerSuboptInput)
def predict_rna_secondary_structure_with_linearfold_zuker(
    filepath: str,
    service_url: str = "http://127.0.0.1:8015/fold/zuker_subopt",
    beam_size: int = 100,
    use_vienna: bool = False,
    dangles: int = 2,
    sharpturn: bool = False,
    delta: float = 5.0,
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Enumerate Zuker suboptimal RNA structures using LinearFold.

    Args:
        filepath: Workspace file path containing RNA sequence content.
        service_url: REST endpoint for the LinearFold Zuker subopt microservice.
        beam_size: LinearFold beam size (default 100).
        use_vienna: Use LinearFold-V (Vienna parameters) when True.
        dangles: 0 or 2 for dangling-end treatment.
        sharpturn: Enable sharpturn in prediction.
        delta: Energy range (kcal/mol) for suboptimal structures.

    Returns:
        Dict with sequence, mfe, structures list, backend, model, and input filepath.
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
                "sharpturn": sharpturn,
                "delta": delta,
            },
            timeout=600,
        )
        response.raise_for_status()
        payload = response.json()
        if "structures" not in payload or "mfe" not in payload:
            raise ValueError("Missing `structures` or `mfe` in LinearFold Zuker response.")
        return {
            "filepath": filepath,
            "sequence": str(payload.get("sequence", "")),
            "mfe": float(payload["mfe"]),
            "structures": list(payload.get("structures", [])),
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
    sequences = _parse_fasta_protein_sequences(read_sequence(filepath))
    if not sequences:
        raise ValueError(f"No protein sequences found in file: {filepath}")
    protein_sequence = sequences[0]
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


def _call_gemorna_prediction(
    service_url: str,
    filepath: str,
    default_model: str,
) -> dict[str, Any]:
    """Shared HTTP helper for GEMORNA 5'UTR MRL / 3'UTR stability prediction wrappers."""
    sequence = _normalize_nucleic_sequence(read_sequence(filepath))
    try:
        response = requests.post(
            service_url,
            json={"sequence": sequence},
            timeout=300,
        )
        response.raise_for_status()
        payload = response.json()
        if "predicted_mrl" not in payload and "predicted_stability" not in payload:
            raise ValueError(f"Missing prediction value in {default_model} response.")
        result: dict[str, Any] = {
            "input_filepath": filepath,
            "input_sequence": payload.get("input_sequence", sequence),
            "model": payload.get("model", default_model),
        }
        if "predicted_mrl" in payload:
            result["predicted_mrl"] = payload["predicted_mrl"]
        if "predicted_stability" in payload:
            result["predicted_stability"] = payload["predicted_stability"]
        return result
    except requests.RequestException as exc:
        _raise_service_error(exc, default_model)


@tool(args_schema=Gemorna5UtrPredictionInput)
def predict_5utr_mrl_with_gemorna(
    filepath: str,
    service_url: str = "http://127.0.0.1:8004/predict/5utr_mrl",
) -> dict[str, Any]:
    """Predict 5'UTR Mean Ribosomal Load (MRL) using GEMORNA.

    INTERFACE LOCK (v0.1.0): The return dict keys must stay synchronized with:
    - agent_core/tool_specs.py :: Gemorna5UtrMrlPredictionOutput
    - microservices/gemorna_service/main.py :: Utr5MrlPredictionResponse

    Args:
        filepath: Path to a file containing the 5'UTR RNA sequence.
            IMPORTANT: pass a filepath rather than long inline sequence text.
        service_url: REST endpoint for the GEMORNA 5'UTR MRL prediction microservice.

    Returns:
        Dict containing:
            input_filepath (str): Original filepath passed in.
            input_sequence (str): Normalized RNA sequence evaluated.
            predicted_mrl (float): Predicted Mean Ribosomal Load score.
            model (str): Model identifier.

    Raises:
        ValueError: If the GEMORNA service is unreachable or returns an invalid payload.
    """
    return _call_gemorna_prediction(service_url, filepath, "GEMORNA-5utr-mrl")


@tool(args_schema=Gemorna3UtrPredictionInput)
def predict_3utr_stability_with_gemorna(
    filepath: str,
    service_url: str = "http://127.0.0.1:8004/predict/3utr_stability",
) -> dict[str, Any]:
    """Predict 3'UTR stability using GEMORNA.

    INTERFACE LOCK (v0.1.0): The return dict keys must stay synchronized with:
    - agent_core/tool_specs.py :: Gemorna3UtrStabilityPredictionOutput
    - microservices/gemorna_service/main.py :: Utr3StabilityPredictionResponse

    Args:
        filepath: Path to a file containing the 3'UTR RNA sequence.
            IMPORTANT: pass a filepath rather than long inline sequence text.
        service_url: REST endpoint for the GEMORNA 3'UTR stability prediction microservice.

    Returns:
        Dict containing:
            input_filepath (str): Original filepath passed in.
            input_sequence (str): Normalized RNA sequence evaluated.
            predicted_stability (float): Predicted stability score.
            model (str): Model identifier.

    Raises:
        ValueError: If the GEMORNA service is unreachable or returns an invalid payload.
    """
    return _call_gemorna_prediction(service_url, filepath, "GEMORNA-3utr-stability")


def _parse_fasta_protein_sequences(raw_text: str) -> list[str]:
    """Parse protein sequences from FASTA or plain text.

    Supports:
      - FASTA with '>' headers (multiple records)
      - Plain text (one sequence per line, or single continuous sequence)
    Empty lines and whitespace are ignored.
    """
    sequences: list[str] = []
    current: list[str] = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current:
                sequences.append("".join(current))
                current = []
        else:
            current.append(line.upper())
    if current:
        sequences.append("".join(current))
    # If no '>' headers were found and we have a single accumulated sequence,
    # also split by lines in case the file contains one sequence per line
    # without headers.
    if not sequences:
        # This path should rarely be hit because current would be populated,
        # but guard just in case.
        stripped = "".join(raw_text.split()).upper()
        if stripped:
            sequences.append(stripped)
    return sequences


@tool(args_schema=LinearDesignCdsInput)
def design_mrna_cds_with_lineardesign(
    filepath: str,
    service_url: str = "http://127.0.0.1:8014/generate/cds",
    lambda_value: float = 0.0,
    codon_usage_path: Optional[str] = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Design an mRNA CDS sequence from a protein sequence using LinearDesign.

    INTERFACE LOCK (v0.2.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - microservices/lineardesign_service/main.py
    - agent_core/tool_specs.py :: LinearDesignCdsOutput / ToolSpec
    - agent_core/state.py :: lineardesign_* fields

    OPERATIONAL ENVELOPE (2026-07 experiment finding): the upstream LinearDesign
    C++ binary is OOM-killed (returncode=-9/SIGKILL, surfaced as a 500 from the
    microservice) on CDS of roughly 7 kb and longer (observed: Factor VIII 7053 nt,
    Zika polyprotein 10257 nt, both deterministic). ~4 kb CDS (Spike 3822 nt) is
    fine. Do not treat this as transient — it is a hard capacity boundary of the
    tool; long targets must use RNARL/GEMORNA instead (workflow `design_tool`
    parameter), and the boundary belongs in the manuscript's limitations.

    Args:
        filepath: Workspace file path containing the input protein sequence.
            IMPORTANT: You must pass a workspace filepath, not the sequence itself.
        service_url: REST endpoint for the LinearDesign microservice.
        lambda_value: LinearDesign lambda hyperparameter balancing MFE and CAI.
        codon_usage_path: Optional codon usage table path.
        verbose: Whether to enable verbose output in the LinearDesign backend.

    Returns:
        Dict containing the generated CDS sequence, structure/MFE/CAI summaries,
        workspace filepath, raw stdout, and stderr.

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

        # Empirical: 1273 aa takes ~778s, 1024 aa takes ~507s.
        # Use 0.8s/aa + 180s buffer to tolerate system load / GC pauses.
        seq_len = len(protein_sequence)
        timeout = max(300, int(seq_len * 0.8) + 180)

        response = requests.post(
            service_url,
            json=request_payload,
            timeout=timeout,
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
            "stderr": payload.get("stderr", ""),
            "model": payload.get("model", "LinearDesign"),
        }
    except requests.RequestException as exc:
        _raise_service_error(exc, "LinearDesign")


@tool(args_schema=LinearDesignCdsBatchInput)
def design_mrna_cds_batch_with_lineardesign(
    filepath: str,
    service_url: str = "http://127.0.0.1:8014/generate/cds/batch",
    lambda_value: float = 0.0,
    codon_usage_path: Optional[str] = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Batch-design mRNA CDS sequences from multiple protein sequences using LinearDesign.

    Reads a FASTA (or plain-text) file, sends all sequences to the batch
    endpoint, and returns aggregated results with per-item success/error tracking.

    INTERFACE LOCK (v0.2.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - microservices/lineardesign_service/main.py :: LinearDesignBatchRequest/Response
    - agent_core/tool_specs.py :: LinearDesignCdsBatchOutput / ToolSpec
    - agent_core/state.py :: lineardesign_* fields

    Args:
        filepath: Workspace file path containing one or more protein sequences.
            FASTA format with '>' headers is supported.
        service_url: REST endpoint for the LinearDesign batch microservice.
        lambda_value: LinearDesign lambda hyperparameter balancing MFE and CAI.
        codon_usage_path: Optional codon usage table path.
        verbose: Whether to enable verbose output in the LinearDesign backend.

    Returns:
        Dict with ``count``, ``success_count``, ``items`` (list of per-sequence
        results), and artifact filepaths copied into workspace.

    Raises:
        ValueError: If the LinearDesign batch service is unreachable.
    """
    raw_text = read_sequence(filepath)
    sequences = _parse_fasta_protein_sequences(raw_text)
    if not sequences:
        raise ValueError(f"No protein sequences found in file: {filepath}")

    try:
        request_payload: dict[str, Any] = {
            "protein_sequences": sequences,
            "lambda_value": lambda_value,
            "verbose": verbose,
        }
        if codon_usage_path:
            request_payload["codon_usage_path"] = codon_usage_path

        # Batch runs sequentially on the server; timeout scales with total work.
        max_len = max(len(s) for s in sequences)
        timeout = max(600, int(max_len * 0.8 * len(sequences)) + 180)

        response = requests.post(
            service_url,
            json=request_payload,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items", [])
        success_count = sum(1 for it in items if it.get("success"))

        # Save best (first successful) sequence as primary artifact
        best_sequence = ""
        best_structure = ""
        best_mfe = 0.0
        best_cai = 0.0
        for it in items:
            if it.get("success"):
                best_sequence = it.get("generated_sequence", "")
                best_structure = it.get("structure", "")
                best_mfe = float(it.get("mfe", 0.0))
                best_cai = float(it.get("cai_score", 0.0))
                break

        output_filepath = ""
        if best_sequence:
            output_filepath = save_sequence(best_sequence, prefix="lineardesign_cds_batch")

        # Copy raw response into workspace for auditability
        batch_json_path = save_text_file(
            str(payload),
            prefix="lineardesign_batch_response",
            suffix=".json",
        )

        return {
            "input_filepath": filepath,
            "output_filepath": output_filepath,
            "best_generated_sequence": best_sequence,
            "best_structure": best_structure,
            "best_mfe": best_mfe,
            "best_cai_score": best_cai,
            "count": int(payload.get("count", 0)),
            "success_count": success_count,
            "items": items,
            "lambda_value": float(payload.get("lambda_value", lambda_value)),
            "codon_usage_path": payload.get("codon_usage_path", codon_usage_path or ""),
            "batch_json_filepath": batch_json_path,
            "model": payload.get("model", "LinearDesign"),
        }
    except requests.RequestException as exc:
        _raise_service_error(exc, "LinearDesign batch")


@tool(args_schema=LinearDesignCdsJunctionAwareInput)
def design_mrna_cds_junction_aware_with_lineardesign(
    filepath: str,
    protein_sequence: Optional[str] = None,
    service_url: str = "http://127.0.0.1:8014/generate/cds_junction_aware",
    lambda_value: float = 0.0,
    utr5_flank: Optional[str] = None,
    utr3_flank: Optional[str] = None,
    junction_weight: float = 0.0,
    junction_window_nt: int = 20,
    flank_nt: int = 21,
    codon_usage_path: Optional[str] = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Design an mRNA CDS with junction-aware LinearDesign (fixed UTR flanks + w_jun).

    The full construct (flank5 + CDS + flank3) is folded as one sequence: the
    junction-side flank slices are fixed nucleotides, and newly formed base pairs
    touching the junction windows are penalized by ``junction_weight`` (kcal/mol)
    inside the CKY objective. With both flanks empty the call degenerates to the
    legacy LinearDesign behavior.

    Synchronized with:
    - microservices/lineardesign_service/main.py :: /generate/cds_junction_aware
    - agent_core/tool_specs.py :: LinearDesignCdsJunctionAwareOutput / ToolSpec

    Args:
        filepath: Workspace file path containing the input protein sequence.
        protein_sequence: Optional explicit protein sequence overriding the file content.
        service_url: REST endpoint for the junction-aware LinearDesign microservice.
        lambda_value: LinearDesign lambda hyperparameter balancing MFE and CAI.
        utr5_flank: Optional 5' UTR flank RNA sequence (junction-side flank_nt nt used).
        utr3_flank: Optional 3' UTR flank RNA sequence (junction-side flank_nt nt used).
        junction_weight: w_jun penalty in kcal/mol per window-touching pair (0 = off).
        junction_window_nt: Half-width (nt) of the junction windows.
        flank_nt: Junction-side flank length used per side (multiple of 3, >= 3).
        codon_usage_path: Optional codon usage table path.
        verbose: Whether to enable verbose output in the LinearDesign backend.

    Returns:
        Dict containing the full-construct sequence, CDS-only fields, junction
        metadata (pair count, thermodynamic MFE), workspace filepath, raw stdout,
        and stderr.

    Raises:
        ValueError: If the LinearDesign service is unreachable or returns an invalid payload.
    """
    protein = (protein_sequence or read_sequence(filepath)).strip()
    try:
        request_payload: dict[str, Any] = {
            "protein_sequence": protein,
            "lambda_value": lambda_value,
            "junction_weight": junction_weight,
            "junction_window_nt": junction_window_nt,
            "flank_nt": flank_nt,
            "verbose": verbose,
        }
        if utr5_flank:
            request_payload["utr5_flank"] = utr5_flank
        if utr3_flank:
            request_payload["utr3_flank"] = utr3_flank
        if codon_usage_path:
            request_payload["codon_usage_path"] = codon_usage_path

        # Same rule as the legacy wrapper, but on the full-construct length (nt).
        total_nt = 3 * len(protein) + len(utr5_flank or "") + len(utr3_flank or "")
        timeout = max(300, int(total_nt * 0.8) + 180)

        response = requests.post(
            service_url,
            json=request_payload,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if "generated_sequence" not in payload:
            raise ValueError("Missing `generated_sequence` in LinearDesign junction-aware response.")
        output_filepath = save_sequence(
            payload["generated_sequence"], prefix="lineardesign_cds_junction_aware"
        )
        return {
            "input_filepath": filepath,
            "output_filepath": output_filepath,
            "generated_sequence": payload["generated_sequence"],
            "structure": payload.get("structure", ""),
            "mfe": float(payload.get("mfe", 0.0)),
            "cai_score": float(payload.get("cai_score", 0.0)),
            "cds_sequence": payload.get("cds_sequence", ""),
            "cds_cai": float(payload.get("cds_cai", 0.0)),
            "full_construct_sequence": payload.get(
                "full_construct_sequence", payload["generated_sequence"]
            ),
            "utr5_flank": payload.get("utr5_flank", ""),
            "utr3_flank": payload.get("utr3_flank", ""),
            "junction_weight": float(payload.get("junction_weight", junction_weight)),
            "junction_window_nt": int(payload.get("junction_window_nt", junction_window_nt)),
            "flank_nt": int(payload.get("flank_nt", flank_nt)),
            "junction_window_pair_count": int(payload.get("junction_window_pair_count", 0)),
            "mfe_thermo": float(payload.get("mfe_thermo", payload.get("mfe", 0.0))),
            "lambda_value": float(payload.get("lambda_value", lambda_value)),
            "codon_usage_path": payload.get("codon_usage_path", codon_usage_path or ""),
            "raw_output": payload.get("raw_output", ""),
            "stderr": payload.get("stderr", ""),
            "model": payload.get("model", "LinearDesign"),
        }
    except requests.RequestException as exc:
        _raise_service_error(exc, "LinearDesign junction-aware")


@tool(args_schema=RNARLCdsInput)
def design_mrna_cds_with_rnarl(
    filepath: str,
    service_url: str = "http://127.0.0.1:8008/generate/cds",
    model_type: str = DEFAULT_RNARL_MODEL_TYPE,
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
    sequences = _parse_fasta_protein_sequences(read_sequence(filepath))
    if not sequences:
        raise ValueError(f"No protein sequences found in file: {filepath}")
    protein_sequence = sequences[0]
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
    seed: Optional[int] = None,
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
        seed: Random seed for reproducible sampling.
        device: CUDA device index used by the upstream RhoDesign script.

    Returns:
        Dict containing the designed RNA sequence, a new workspace sequence filepath,
        copied FASTA/log artifacts when available, and summary metadata.

    Raises:
        ValueError: If the RhoDesign service is unreachable or returns an invalid payload.
    """
    try:
        payload: dict[str, Any] = {
            "pdb_path": pdb_filepath,
            "secondary_structure_path": secondary_structure_filepath,
            "temperature": temperature,
            "device": device,
        }
        if seed is not None:
            payload["seed"] = seed
        response = requests.post(
            service_url,
            json={**payload, "timeout_seconds": timeout_seconds},
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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Generate RNA sequence(s) from a PDB structure using the RiboDiffusion microservice.

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
    - agent_core/workflows/rna_small_molecule_interaction.py :: evaluate() consumption

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
    - agent_core/workflows/rna_small_molecule_interaction.py :: evaluate() consumption

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


@tool(args_schema=EGARPSInput)
def score_rna_protein_complex_with_egarps(
    filepath: str,
    academic: bool = False,
    service_url: str = "http://127.0.0.1:8023/score",
) -> dict[str, Any]:
    """Score RNA-protein complex structure using the EGARPS+ microservice.

    INTERFACE LOCK (v0.1.0): The return dict keys below are the canonical interface.
    Any addition/removal must be synchronized with:
    - microservices/egarps_service/main.py :: EGARPSResponse
    - agent_core/tool_specs.py :: EGARPSOutput
    - agent_core/state.py :: egarps_* fields

    Args:
        filepath: Path to a PDB file containing the RNA-protein complex structure.
            WARNING (2026-07-27 campaign): this must be a REAL `.pdb` file.
            (a) The EGARPS pipeline (external_repos/EGARPS/scripts/ins.py)
            derives cache paths via `pdb.replace('.pdb', ...)` — a no-op for
            non-`.pdb` inputs — and dumps its pickle caches OVER the input
            file itself. (b) Its CIF reader rejects the OP3 atoms Protenix
            writes (`OP3 not in STD_ATOM_NAMES`). (c) Its chain typing keys on
            `re.search('protein', basename+...)` — basenames containing
            'protein' (e.g. 'proteinx') misroute RNA chains into the protein
            feature path. Convert mmCIF via gemmi into a sanitized `.pdb`
            copy first (see experiments/run_known_aptamer_validation.py::
            _proteinx_cif_to_pdb).
        academic: If True, use full academic mode (requires DSSR and NACCESS licenses).
            If False (default), use non-academic mode with reduced features.
        service_url: REST endpoint for the EGARPS+ microservice.

    Returns:
        Dict with the following canonical keys (INTERFACE LOCK):
            complex_id (str): Identifier of the RNA-protein complex.
            native_probability (float): Probability of being a native structure (0-1).
            academic (bool): Whether academic mode was used.
            model (str): Model identifier.
            pdb_path (str): Path to the input PDB file.

    Raises:
        ValueError: If the EGARPS+ service is unreachable or returns an invalid payload.
    """
    try:
        request_payload: dict[str, Any] = {
            "pdb_path": filepath,
            "academic": academic,
        }
        response = requests.post(
            service_url,
            json=request_payload,
            timeout=900,
        )
        response.raise_for_status()
        payload = response.json()
        if "native_probability" not in payload:
            raise ValueError(
                "Missing `native_probability` in EGARPS+ response."
            )
        payload["input_filepath"] = filepath
        return payload
    except requests.RequestException as exc:
        _raise_service_error(exc, "EGARPS+")


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
    - agent_core/state.py :: rnastop_* fields

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
    """
    INTERFACE LOCK (v0.2.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Score RNA sequence fragments for putative internal ribosome entry sites (IRES) via IRESfinder.

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


# Extract RNA from CIF INTERFACE LOCK (v0.1.0) —— 禁止单方面变更


class ExtractRnaFromCifInput(BaseModel):
    """Input schema for extracting RNA sequence from a CIF/MMCIF file."""

    cif_filepath: str = Field(
        ...,
        description="Path to CIF/MMCIF file (workspace or absolute).",
    )
    chain_id: Optional[str] = Field(
        default=None,
        description="Chain ID to extract; auto-detect first RNA chain if omitted.",
    )


def _ensure_cif_has_b_iso_or_equiv(cif_filepath: str) -> str:
    """Return a CIF filepath guaranteed to have _atom_site.B_iso_or_equiv.

    ODesign and some other tools omit the B-factor column in their CIF outputs,
    which causes biopython's MMCIFParser to crash.  This helper injects a
    dummy ``0.0`` B-factor column when it is missing and writes the patched
    content to a temporary file.
    """
    import tempfile

    with open(cif_filepath, "r") as fh:
        lines = fh.readlines()

    header_indices = [
        i for i, line in enumerate(lines) if line.strip().startswith("_atom_site.")
    ]
    if not header_indices:
        return cif_filepath

    has_b_iso = any(
        lines[idx].strip().startswith("_atom_site.B_iso_or_equiv")
        for idx in header_indices
    )
    if has_b_iso:
        return cif_filepath

    data_start = header_indices[-1] + 1
    data_end = len(lines)
    for i in range(data_start, len(lines)):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith(("_", "loop_", "data_")):
            data_end = i
            break

    new_lines = lines[:data_start]
    new_lines.append("_atom_site.B_iso_or_equiv\n")
    for i in range(data_start, data_end):
        line = lines[i]
        if line.strip() and not line.strip().startswith("#"):
            new_lines.append(line.rstrip("\n") + " 0.0\n")
        else:
            new_lines.append(line)
    new_lines.extend(lines[data_end:])

    fd, temp_path = tempfile.mkstemp(suffix=".cif")
    with os.fdopen(fd, "w") as fh:
        fh.writelines(new_lines)
    return temp_path


@tool(args_schema=ExtractRnaFromCifInput)
def extract_rna_sequence_from_cif(
    cif_filepath: str,
    chain_id: Optional[str] = None,
) -> dict[str, Any]:
    """Extract RNA sequence from a CIF/MMCIF file using biopython.

    Detects RNA vs DNA vs protein by checking for the O2' atom.
    Non-standard nucleotides are represented as 'N' with a warning recorded.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: ExtractRnaFromCifOutput / ToolSpec
    - agent_core/state.py :: extract_rna_from_cif_* fields

    Args:
        cif_filepath: CIF/MMCIF file path.
        chain_id: Optional chain ID; if omitted the first RNA chain is selected.

    Returns:
        Dict with ``sequence``, ``chain_id``, ``residue_count``, ``is_rna``,
        ``warnings``, and paths.

    Raises:
        ValueError: If no RNA chain is found or the specified chain does not exist.
        ImportError: If biopython is not installed.
    """
    try:
        from Bio.PDB.MMCIFParser import MMCIFParser
    except ImportError as exc:
        raise ImportError(
            "biopython is required for CIF parsing. Install it with: pip install biopython"
        ) from exc

    parser = MMCIFParser(QUIET=True)
    patched_path = _ensure_cif_has_b_iso_or_equiv(cif_filepath)
    structure = parser.get_structure("cif_structure", patched_path)

    rna_chains = []
    for model in structure:
        for chain in model:
            is_rna_chain = False
            for residue in chain:
                if residue.id[0].strip():  # Skip hetero atoms / waters
                    continue
                atom_names = {atom.name for atom in residue}
                if "O2'" in atom_names:
                    is_rna_chain = True
                    break
            if is_rna_chain:
                rna_chains.append(chain)

    if not rna_chains:
        raise ValueError(
            f"No RNA chain found in {cif_filepath}. "
            "Ensure the file contains RNA residues with O2' atoms."
        )

    selected_chain = None
    if chain_id is not None:
        for ch in rna_chains:
            if ch.id == chain_id:
                selected_chain = ch
                break
        if selected_chain is None:
            available = [ch.id for ch in rna_chains]
            raise ValueError(
                f"Chain '{chain_id}' not found or is not RNA. "
                f"Available RNA chains: {available}"
            )
    else:
        selected_chain = rna_chains[0]

    # Standard RNA base mapping
    base_map = {
        "A": "A", "U": "U", "G": "G", "C": "C",
        "DA": "A", "DT": "T", "DG": "G", "DC": "C",
    }
    sequence_parts = []
    non_standard_warnings = []
    residue_count = 0
    for residue in selected_chain:
        if residue.id[0].strip():  # Skip hetero / water
            continue
        residue_count += 1
        resname = residue.resname.strip()
        base = base_map.get(resname, None)
        if base is None:
            if len(resname) == 1 and resname in "AUGC":
                base = resname
            else:
                base = "N"
                non_standard_warnings.append(
                    f"Non-standard residue '{resname}' at position {residue.id[1]}"
                )
        sequence_parts.append(base)

    sequence = "".join(sequence_parts)
    warnings = "; ".join(non_standard_warnings) if non_standard_warnings else ""

    return {
        "sequence": sequence,
        "chain_id": selected_chain.id,
        "residue_count": residue_count,
        "is_rna": True,
        "cif_filepath": cif_filepath,
        "warnings": warnings,
        "model": "biopython-mmcif-extract",
    }


# ODesign aptamer input JSON builder INTERFACE LOCK (v0.1.0) —— 禁止单方面变更


class BuildOdesignAptamerInput(BaseModel):
    """Input schema for building ODesign aptamer design JSON."""

    protein_structure_path: str = Field(
        ...,
        description="Path to protein PDB or CIF file.",
    )
    protein_chain_id: str = Field(
        ...,
        description="Protein chain ID, e.g. 'C'.",
    )
    protein_sequence_length: int = Field(
        ...,
        ge=1,
        description="Protein sequence length.",
    )
    hotspot_residues: str = Field(
        ...,
        description="Hotspot residues, format like 'C/18,C/90,C/79,C/49'.",
    )
    aptamer_length: int = Field(
        ...,
        ge=1,
        description="Desired RNA aptamer length in nucleotides.",
    )
    output_prefix: Optional[str] = Field(
        default=None,
        description="Output filename prefix.",
    )


@tool(args_schema=BuildOdesignAptamerInput)
def build_odesign_aptamer_input_json(
    protein_structure_path: str,
    protein_chain_id: str,
    protein_sequence_length: int,
    hotspot_residues: str,
    aptamer_length: int,
    output_prefix: Optional[str] = None,
) -> dict[str, Any]:
    """Build an ODesign input JSON for RNA aptamer design against a protein target.

    Constructs the JSON structure for ODesign ``odesign_base_na_rigid`` + ``rna`` modality.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: BuildOdesignAptamerOutput / ToolSpec
    - agent_core/state.py :: odesign_aptamer_input_* fields

    Args:
        protein_structure_path: Protein structure file path.
        protein_chain_id: Protein chain ID.
        protein_sequence_length: Length of the protein sequence.
        hotspot_residues: Comma-separated hotspot residues.
        aptamer_length: Target aptamer length in nt.
        output_prefix: Optional filename prefix for the generated JSON.

    Returns:
        Dict with ``input_json_filepath`` and ``design_config``.
    """
    prefix = output_prefix or "odesign_aptamer_input"
    design_config = [
        {
            "name": prefix,
            "ref_file": protein_structure_path,
            "chains": [
                {
                    "chain_type": "proteinChain",
                    "sequence": f"{protein_chain_id}/1-{protein_sequence_length}",
                },
                {
                    "chain_type": "rnaChain",
                    "sequence": f"{aptamer_length}-{aptamer_length}",
                },
            ],
            "hotspot": hotspot_residues,
            "center_method": "hotspot_center",
        }
    ]

    json_content = json.dumps(design_config, indent=2, ensure_ascii=False)
    input_json_filepath = save_text_file(
        json_content,
        prefix=prefix,
        suffix=".json",
    )

    return {
        "input_json_filepath": input_json_filepath,
        "design_config": design_config,
        "model": "odesign-aptamer-input-builder",
    }


# ProteinX protein structure prediction INTERFACE LOCK (v0.1.0) —— 禁止单方面变更


class ProteinXProteinInput(BaseModel):
    """Input schema for ProteinX (Protenix) protein structure prediction."""

    filepath: str = Field(
        ...,
        description="Path to FASTA file containing protein sequence(s).",
    )
    num_models: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Number of inference samples to generate.",
    )
    num_recycles: int = Field(
        default=3,
        ge=1,
        le=12,
        description="Number of Pairformer cycles (ignored when use_default_params is true).",
    )
    stop_at_score: float = Field(
        default=100,
        ge=0,
        description="Early stopping threshold (pLDDT). Not enforced by Protenix.",
    )
    msa_mode: str = Field(
        default="none",
        description="MSA generation mode. 'none' disables MSA; 'protenix' enables Protenix MSA server.",
    )
    service_url: str = Field(
        default="http://127.0.0.1:8022/predict/protein",
        description="ProteinX microservice endpoint.",
    )
    timeout_seconds: int = Field(
        default=7200,
        ge=60,
        le=28800,
        description="Request timeout in seconds.",
    )


@tool(args_schema=ProteinXProteinInput)
def predict_protein_structure_with_proteinx(
    filepath: str,
    num_models: int = 5,
    num_recycles: int = 3,
    stop_at_score: float = 100,
    msa_mode: str = "none",
    service_url: str = "http://127.0.0.1:8022/predict/protein",
    timeout_seconds: int = 7200,
) -> dict[str, Any]:
    """Predict protein 3D structure from sequence using ProteinX (Protenix).

    Requires the ``proteinx_service`` microservice on port 8022.
    Pass a filepath under ``workspace/`` or an absolute server path.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - microservices/proteinx_service/main.py
    - agent_core/tool_specs.py :: ProteinXProteinOutput / ToolSpec
    - agent_core/state.py :: protein_structure_* fields

    Args:
        filepath: FASTA file with protein sequence.
        num_models: Number of inference samples to generate.
        num_recycles: Pairformer cycles (ignored when Protenix use_default_params is true).
        stop_at_score: pLDDT early-stop threshold (interface compat, not enforced).
        msa_mode: MSA mode. 'none' disables MSA; 'protenix' enables Protenix MSA server.
        service_url: ProteinX microservice URL.
        timeout_seconds: HTTP timeout (default 7200 s = 2 h).

    Returns:
        Dict with ``pdb_filepath``, ``mean_pae``, ``mean_plddt``,
        ``ranking_confidence``, ``model_scores``.

    Raises:
        ValueError: If the HTTP call fails or the service reports an error.
    """
    seq_abs = _absolute_path_under_project(filepath)
    try:
        response = requests.post(
            service_url,
            json={
                "sequence_filepath": str(seq_abs),
                "num_models": num_models,
                "num_recycles": num_recycles,
                "stop_at_score": stop_at_score,
                "msa_mode": msa_mode,
            },
            timeout=float(timeout_seconds),
        )
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        _raise_service_error(exc, "ProteinX")
    return {
        "pdb_filepath": str(body.get("pdb_filepath", "")),
        "mean_pae": float(body.get("mean_pae", 0.0)),
        "mean_plddt": float(body.get("mean_plddt", 0.0)),
        "ranking_confidence": float(body.get("ranking_confidence", 0.0)),
        "model_scores": list(body.get("model_scores", [])),
        "model": str(body.get("model", "proteinx")),
    }


# ProteinX RNA-protein complex prediction (v0.1.0)


class ProteinXComplexInput(BaseModel):
    """Input schema for ProteinX RNA-protein complex structure prediction."""

    protein_filepath: str = Field(
        ...,
        description="Path to FASTA file containing the protein sequence.",
    )
    rna_filepath: str = Field(
        ...,
        description="Path to FASTA file containing the RNA sequence.",
    )
    num_models: int = Field(default=1, ge=1, le=5)
    num_recycles: int = Field(default=10, ge=1, le=12)
    msa_mode: str = Field(default="none")
    service_url: str = Field(default="http://127.0.0.1:8022/predict/complex")
    timeout_seconds: int = Field(default=7200, ge=60, le=28800)


@tool(args_schema=ProteinXComplexInput)
def predict_rna_protein_complex_with_proteinx(
    protein_filepath: str,
    rna_filepath: str,
    num_models: int = 1,
    num_recycles: int = 10,
    msa_mode: str = "none",
    service_url: str = "http://127.0.0.1:8022/predict/complex",
    timeout_seconds: int = 7200,
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.1.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Predict RNA-protein complex structure using ProteinX (Protenix).

    Args:
        protein_filepath: FASTA file with protein sequence.
        rna_filepath: FASTA file with RNA sequence.
        num_models: Number of inference samples.
        num_recycles: Pairformer cycles.
        msa_mode: MSA mode ('none' disables MSA).
        service_url: ProteinX complex prediction endpoint.
        timeout_seconds: HTTP timeout in seconds.

    Returns:
        Dict with pdb_filepath, mean_plddt, ipTM, ranking_confidence, model_scores.
    """
    protein_abs = _absolute_path_under_project(protein_filepath)
    rna_abs = _absolute_path_under_project(rna_filepath)

    try:
        response = requests.post(
            service_url,
            json={
                "protein_sequence": read_sequence(protein_abs).strip().split("\n")[-1],
                "rna_sequence": read_sequence(rna_abs).strip().split("\n")[-1],
                "num_models": num_models,
                "num_recycles": num_recycles,
                "msa_mode": msa_mode,
            },
            timeout=float(timeout_seconds),
        )
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        _raise_service_error(exc, "ProteinX-complex")

    return {
        "pdb_filepath": str(body.get("pdb_filepath", "")),
        "mean_pae": float(body.get("mean_pae", 0.0)),
        "mean_plddt": float(body.get("mean_plddt", 0.0)),
        "ipTM": float(body.get("ipTM", 0.0)),
        "ranking_confidence": float(body.get("ranking_confidence", 0.0)),
        "model_scores": list(body.get("model_scores", [])),
        "model": str(body.get("model", "proteinx")),
    }


# RNA-protein interface analysis (v0.1.0)


class RnaProteinInterfaceInput(BaseModel):
    """Input schema for RNA-protein interface structure analysis."""

    complex_pdb_filepath: str = Field(
        ...,
        description="Path to RNA-protein complex PDB or CIF file.",
    )
    protein_chain_id: str = Field(default="A", description="Protein chain ID.")
    rna_chain_id: str = Field(default="B", description="RNA chain ID.")
    contact_cutoff: float = Field(
        default=5.0, ge=2.0, le=15.0,
        description="Distance cutoff (Å) for interface contacts.",
    )


@tool(args_schema=RnaProteinInterfaceInput)
def analyze_rna_protein_interface(
    complex_pdb_filepath: str,
    protein_chain_id: str = "A",
    rna_chain_id: str = "B",
    contact_cutoff: float = 5.0,
) -> dict[str, Any]:
    """
    INTERFACE LOCK (v0.1.0)
    Do NOT modify any function signature, Pydantic field, return dict key, or state field
    without updating all files listed in the lock comment and re-running the full test suite.

    Analyze RNA-protein interface from a complex structure.

    Computes interface contacts, buried SASA, hydrogen bonds, and salt bridges.

    Args:
        complex_pdb_filepath: Path to complex PDB/CIF.
        protein_chain_id: Protein chain ID.
        rna_chain_id: RNA chain ID.
        contact_cutoff: Distance cutoff in Angstroms.

    Returns:
        Dict with interface_contacts, buried_sasa, hydrogen_bonds, salt_bridges,
        interface_area, protein_surface_area, rna_surface_area.
    """
    try:
        from Bio.PDB import PDBParser, MMCIFParser
    except ImportError as exc:
        raise ImportError(
            "biopython and numpy are required for interface analysis. "
            "Install with: pip install biopython numpy"
        ) from exc

    path_obj = Path(complex_pdb_filepath)
    suffix = path_obj.suffix.lower()
    try:
        if suffix in {".cif", ".mmcif"}:
            parser = MMCIFParser(QUIET=True)
        else:
            parser = PDBParser(QUIET=True)
        structure = parser.get_structure("complex", complex_pdb_filepath)
    except Exception as exc:
        raise ValueError(f"Structure parsing failed: {exc}") from exc

    # Collect atoms by chain
    protein_atoms: list[Any] = []
    rna_atoms: list[Any] = []
    for model in structure:
        for chain in model:
            if chain.id == protein_chain_id:
                for residue in chain:
                    if not residue.id[0].strip():
                        for atom in residue:
                            protein_atoms.append(atom)
            elif chain.id == rna_chain_id:
                for residue in chain:
                    if not residue.id[0].strip():
                        for atom in residue:
                            rna_atoms.append(atom)

    if not protein_atoms or not rna_atoms:
        raise ValueError(
            f"Could not find both chains. Protein '{protein_chain_id}' has "
            f"{len(protein_atoms)} atoms, RNA '{rna_chain_id}' has {len(rna_atoms)} atoms."
        )

    # Interface contacts
    interface_contacts = 0
    contact_pairs: set[tuple[str, str]] = set()
    for patom in protein_atoms:
        for ratom in rna_atoms:
            if patom - ratom <= contact_cutoff:
                pres = patom.get_parent()
                rres = ratom.get_parent()
                if pres is not None and rres is not None:
                    pair = (f"{pres.resname.strip()}/{pres.id[1]}", f"{rres.resname.strip()}/{rres.id[1]}")
                    if pair not in contact_pairs:
                        contact_pairs.add(pair)
                        interface_contacts += 1

    # Hydrogen bonds and salt bridges (simplified geometric criteria)
    hydrogen_bonds = 0
    salt_bridges = 0
    hbdonor = {"N", "O", "S", "F"}
    acceptor = {"N", "O", "S"}
    charged_positive = {"ARG", "LYS", "HIS"}
    charged_negative = {"ASP", "GLU"}

    for patom in protein_atoms:
        for ratom in rna_atoms:
            dist = patom - ratom
            if dist > 3.5:
                continue
            # H-bond: donor-acceptor distance 2.5-3.5 Å
            if 2.5 <= dist <= 3.5:
                pelem = patom.element.strip().upper()
                relem = ratom.element.strip().upper()
                if (pelem in hbdonor and relem in acceptor) or (pelem in acceptor and relem in hbdonor):
                    hydrogen_bonds += 1
            # Salt bridge: charged residues within 4.0 Å
            if dist <= 4.0:
                pres = patom.get_parent()
                rres = ratom.get_parent()
                if pres is not None and rres is not None:
                    pname = pres.resname.strip().upper()
                    rname = rres.resname.strip().upper()
                    if (pname in charged_positive and rname in charged_negative) or \
                       (pname in charged_negative and rname in charged_positive):
                        salt_bridges += 1

    # Buried SASA using freesasa
    buried_sasa = 0.0
    protein_surface_area = 0.0
    rna_surface_area = 0.0
    try:
        import freesasa
        # Compute SASA for the whole complex
        complex_structure = freesasa.Structure(complex_pdb_filepath)
        complex_result = freesasa.calc(complex_structure)
        complex_area = complex_result.totalArea()

        # Build temporary PDBs for individual chains and compute SASA
        # Use a simplified approach: sum chain areas from residue areas
        prot_area = 0.0
        rna_area = 0.0
        areas = complex_result.residueAreas()
        for chain_id_val, res_areas in areas.items():
            for resnum, ra in res_areas.items():
                if chain_id_val == protein_chain_id:
                    prot_area += ra.total
                elif chain_id_val == rna_chain_id:
                    rna_area += ra.total
        protein_surface_area = prot_area
        rna_surface_area = rna_area
        buried_sasa = max(0.0, prot_area + rna_area - complex_area)
    except ImportError:
        pass
    except Exception as exc:
        logging.getLogger(__name__).warning("freesasa_interface_analysis_failed: %s", exc)

    return {
        "interface_contacts": interface_contacts,
        "buried_sasa": round(buried_sasa, 2),
        "hydrogen_bonds": hydrogen_bonds,
        "salt_bridges": salt_bridges,
        "interface_area": round(buried_sasa * 0.5, 2),  # Approximation
        "protein_surface_area": round(protein_surface_area, 2),
        "rna_surface_area": round(rna_surface_area, 2),
        "contact_cutoff": contact_cutoff,
        "complex_pdb_filepath": complex_pdb_filepath,
    }


# Protein binding hotspot identification INTERFACE LOCK (v0.1.0) —— 禁止单方面变更


class IdentifyProteinBindingHotspotsInput(BaseModel):
    """Input schema for protein binding hotspot identification."""

    protein_structure_path: str = Field(
        ...,
        description="Path to protein PDB or CIF file.",
    )
    chain_id: str = Field(
        default="",
        description="Protein chain ID to analyze.",
    )


@tool(args_schema=IdentifyProteinBindingHotspotsInput)
def identify_protein_binding_hotspots(
    protein_structure_path: str,
    chain_id: str = "",
) -> dict[str, Any]:
    """Automatically identify RNA aptamer binding hotspot residues on a protein surface.

    Algorithm:
      1. Parse protein coordinates with biopython (PDB or CIF).
      2. Compute per-residue SASA with freesasa.
      3. Filter exposed residues (relative SASA > 30%).
      4. Filter basic residues (Arg/Lys/His).
      5. Spatial clustering of exposed basic residues with DBSCAN (eps=10 A, min_samples=2).
      6. Select largest patch and output its center residues as hotspots.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: IdentifyProteinBindingHotspotsOutput / ToolSpec
    - agent_core/state.py :: hotspot_* fields

    Args:
        protein_structure_path: Path to the protein structure file (PDB or CIF).
        chain_id: Chain ID to analyze; if omitted the first chain is used.

    Returns:
        Dict with ``hotspot_residues``, ``hotspot_patch_size``,
        ``patch_center_coords``, ``exposed_basic_count``.

    Raises:
        ValueError: If the file is unreadable, chain not found, or no suitable residues.
        ImportError: If biopython, freesasa, or scikit-learn is not installed.
    """
    try:
        from Bio.PDB import PDBParser, PDBIO, MMCIFParser
        from Bio.PDB.PDBExceptions import PDBConstructionException
        import freesasa
        from sklearn.cluster import DBSCAN
        import numpy as np
    except ImportError as exc:
        raise ImportError(
            "biopython, freesasa, and scikit-learn are required for hotspot identification. "
            "Install with: pip install biopython freesasa scikit-learn"
        ) from exc

    path_obj = Path(protein_structure_path)
    suffix = path_obj.suffix.lower()

    # Parse structure
    try:
        if suffix in {".cif", ".mmcif"}:
            parser = MMCIFParser(QUIET=True)
            structure = parser.get_structure("prot", protein_structure_path)
        else:
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("prot", protein_structure_path)
    except PDBConstructionException as exc:
        raise ValueError(f"Structure parsing failed: {exc}") from exc

    # Select chain
    target_chain = None
    available_chains = []
    for model in structure:
        for ch in model:
            available_chains.append(ch.id)
            if chain_id and ch.id == chain_id:
                target_chain = ch
            elif not chain_id and target_chain is None:
                target_chain = ch
        if target_chain is not None and chain_id:
            break

    if target_chain is None:
        raise ValueError(
            f"Chain '{chain_id}' not found. Available chains: {available_chains}"
        )
    resolved_chain_id = target_chain.id

    # Build a temporary PDB for freesasa if input is CIF,
    # otherwise use the PDB file directly.
    tmp_pdb_path = None
    try:
        if suffix in {".cif", ".mmcif"}:
            from tempfile import NamedTemporaryFile
            io = PDBIO()
            io.set_structure(structure)
            with NamedTemporaryFile(suffix=".pdb", delete=False, mode="w") as fh:
                tmp_pdb_path = fh.name
                io.save(tmp_pdb_path)
            fs_structure = freesasa.Structure(tmp_pdb_path)
        else:
            fs_structure = freesasa.Structure(protein_structure_path)

        result = freesasa.calc(fs_structure)
        areas = result.residueAreas()
    finally:
        if tmp_pdb_path is not None:
            Path(tmp_pdb_path).unlink(missing_ok=True)

    if resolved_chain_id not in areas:
        raise ValueError(
            f"Chain '{resolved_chain_id}' not found in freesasa output. "
            f"Available chains: {list(areas.keys())}"
        )

    # Identify exposed basic residues
    basic_residues = {"ARG", "LYS", "HIS"}
    exposed_basic = []
    for residue in target_chain:
        if residue.id[0].strip():  # Skip hetero / water
            continue
        resname = residue.resname.strip()
        resnum = str(residue.id[1])
        if resnum not in areas[resolved_chain_id]:
            continue
        ra = areas[resolved_chain_id][resnum]
        rel_sasa = float(ra.relativeTotal) if ra.hasRelativeAreas else 0.0
        if rel_sasa > 0.3 and resname in basic_residues:
            ca_coord = None
            for atom in residue:
                if atom.name == "CA":
                    ca_coord = atom.coord
                    break
            if ca_coord is not None:
                exposed_basic.append(
                    {
                        "resname": resname,
                        "resnum": resnum,
                        "coord": ca_coord,
                        "rel_sasa": rel_sasa,
                    }
                )

    if not exposed_basic:
        return {
            "hotspot_residues": "",
            "hotspot_patch_size": 0,
            "patch_center_coords": [0.0, 0.0, 0.0],
            "exposed_basic_count": 0,
            "protein_structure_path": protein_structure_path,
            "chain_id": resolved_chain_id,
            "model": "freesasa-dbscan-hotspot",
            "warning": "No exposed basic residues found (relSASA > 30%).",
        }

    # DBSCAN clustering on CA coordinates
    coords = np.array([r["coord"] for r in exposed_basic])
    if len(coords) >= 2:
        clustering = DBSCAN(eps=10.0, min_samples=2).fit(coords)
        labels = clustering.labels_
    else:
        labels = np.array([-1])

    # Build clusters (noise points treated as singleton clusters)
    from collections import defaultdict
    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        clusters[label].append(i)

    # Find largest cluster
    largest_label = max(clusters.keys(), key=lambda k: len(clusters[k]))
    patch_indices = clusters[largest_label]
    patch_residues = [exposed_basic[i] for i in patch_indices]
    patch_size = len(patch_residues)

    patch_coords = np.array([r["coord"] for r in patch_residues])
    center = patch_coords.mean(axis=0).tolist()

    hotspot = ",".join(
        f"{resolved_chain_id}/{r['resnum']}" for r in patch_residues
    )

    return {
        "hotspot_residues": hotspot,
        "hotspot_patch_size": patch_size,
        "patch_center_coords": center,
        "exposed_basic_count": len(exposed_basic),
        "protein_structure_path": protein_structure_path,
        "chain_id": resolved_chain_id,
        "model": "freesasa-dbscan-hotspot",
        "warning": "",
    }


# Structure alignment (RMSD + TM-score) INTERFACE LOCK (v0.1.0) —— 禁止单方面变更


class StructureAlignmentInput(BaseModel):
    """Input schema for RNA 3D structure alignment scoring."""

    reference_pdb_filepath: str = Field(
        ...,
        description="Path to reference PDB file.",
    )
    predicted_pdb_filepath: str = Field(
        ...,
        description="Path to predicted PDB file.",
    )
    chain_id: Optional[str] = Field(
        default=None,
        description="Chain ID to align; auto-detect if omitted.",
    )
    atom_type: str = Field(
        default="C1'",
        description="Atom type to align, e.g. 'C1'' for RNA or 'CA' for protein.",
    )


@tool(args_schema=StructureAlignmentInput)
def score_structure_alignment(
    reference_pdb_filepath: str,
    predicted_pdb_filepath: str,
    chain_id: Optional[str] = None,
    atom_type: str = "C1'",
) -> dict[str, Any]:
    """Compute RMSD and TM-score between two RNA 3D structures.

    Uses biopython PDBParser and SVDSuperimposer for alignment.
    If residue counts differ, aligns the shorter length and records a warning.
    Missing atoms are skipped with a warning.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: StructureAlignmentOutput / ToolSpec
    - agent_core/state.py :: structure_rmsd / structure_tm_score fields

    Args:
        reference_pdb_filepath: Reference structure PDB path.
        predicted_pdb_filepath: Predicted structure PDB path.
        chain_id: Optional chain ID; auto-detects first chain if omitted.
        atom_type: Atom name used for superposition (default C1' for RNA).

    Returns:
        Dict with ``rmsd``, ``tm_score``, ``aligned_residue_count``,
        ``superposition_matrix``, ``warning``.

    Raises:
        ValueError: If chain not found, atom missing, or parsing fails.
        ImportError: If biopython is not installed.
    """
    try:
        from Bio.PDB import PDBParser
        from Bio.PDB.PDBExceptions import PDBConstructionException
        from Bio.SVDSuperimposer import SVDSuperimposer
    except ImportError as exc:
        raise ImportError(
            "biopython is required for structure alignment. Install it with: pip install biopython"
        ) from exc

    parser = PDBParser(QUIET=True)

    def _get_chain(structure, target_chain_id):
        for model in structure:
            for ch in model:
                if target_chain_id is None or ch.id == target_chain_id:
                    return ch
        available = []
        for model in structure:
            for ch in model:
                available.append(ch.id)
        raise ValueError(
            f"Chain '{target_chain_id}' not found. Available chains: {available}"
        )

    def _extract_coords(chain_obj, target_atom):
        coords = []
        res_ids = []
        for residue in chain_obj:
            if residue.id[0].strip():  # Skip hetero / water
                continue
            for atom in residue:
                if atom.name == target_atom:
                    coords.append(atom.coord)
                    res_ids.append(residue.id[1])
                    break
        return coords, res_ids

    try:
        ref_structure = parser.get_structure("ref", reference_pdb_filepath)
        pred_structure = parser.get_structure("pred", predicted_pdb_filepath)
    except PDBConstructionException as exc:
        raise ValueError(f"PDB parsing failed: {exc}") from exc

    ref_chain = _get_chain(ref_structure, chain_id)
    pred_chain = _get_chain(pred_structure, chain_id)

    ref_coords, _ = _extract_coords(ref_chain, atom_type)
    pred_coords, _ = _extract_coords(pred_chain, atom_type)

    if not ref_coords:
        raise ValueError(
            f"No '{atom_type}' atoms found in reference chain '{ref_chain.id}'."
        )
    if not pred_coords:
        raise ValueError(
            f"No '{atom_type}' atoms found in predicted chain '{pred_chain.id}'."
        )

    # Align shorter length
    min_len = min(len(ref_coords), len(pred_coords))
    if len(ref_coords) != len(pred_coords):
        warning = (
            f"Residue counts differ ({len(ref_coords)} vs {len(pred_coords)}); "
            f"aligning first {min_len} residues."
        )
    else:
        warning = ""

    ref_coords_arr = ref_coords[:min_len]
    pred_coords_arr = pred_coords[:min_len]

    if len(ref_coords_arr) < 3:
        raise ValueError(
            f"Need at least 3 atoms for alignment; got {len(ref_coords_arr)}."
        )

    import numpy as np

    sup = SVDSuperimposer()
    sup.set(np.array(ref_coords_arr), np.array(pred_coords_arr))
    sup.run()

    rmsd = float(sup.get_rms())
    rot, tran = sup.get_rotran()

    # TM-score calculation
    L_aligned = min_len
    L_target = max(len(ref_coords), len(pred_coords))

    if L_aligned <= 15:
        d0 = 0.5
    else:
        d0 = 1.24 * ((L_aligned - 15) ** (1.0 / 3.0)) - 1.8
        if d0 < 0.5:
            d0 = 0.5

    transformed_coords = [rot @ c + tran for c in pred_coords_arr]
    distances = [
        float(((ref_coords_arr[i] - transformed_coords[i]) ** 2).sum() ** 0.5)
        for i in range(L_aligned)
    ]
    tm_score = sum(1.0 / (1.0 + (d / d0) ** 2) for d in distances) / L_target

    superposition_matrix = [
        [float(rot[i][j]) for j in range(3)] + [float(tran[i])]
        for i in range(3)
    ]

    return {
        "rmsd": rmsd,
        "tm_score": tm_score,
        "aligned_residue_count": L_aligned,
        "superposition_matrix": superposition_matrix,
        "reference_pdb_filepath": reference_pdb_filepath,
        "predicted_pdb_filepath": predicted_pdb_filepath,
        "chain_id": ref_chain.id,
        "atom_type": atom_type,
        "warning": warning,
        "model": "biopython-svd-alignment",
    }


# ---------------------------------------------------------------------------
# LangChain tool sets (single source of truth for the tool registry)
# ---------------------------------------------------------------------------


# Workflow Demo Echo INTERFACE LOCK (v0.1.0) —— 禁止单方面变更

class WorkflowDemoEchoInput(BaseModel):
    """Input for the optional registry/executor smoke-test tool."""

    text: str = Field(..., min_length=1, description="Short text for workflow demo invocations.")


@tool(args_schema=WorkflowDemoEchoInput)
def workflow_demo_echo(text: str) -> dict[str, Any]:
    """Minimal demo tool: echo string and length. Not used by production routing by default.

    INTERFACE LOCK (v0.1.0): This wrapper's schema and return dict keys are the
    canonical interface. Any addition/removal must be synchronized with:
    - agent_core/tool_specs.py :: WorkflowDemoEchoOutput / workflow_demo_echo ToolSpec
    - agent_core/state.py :: workflow_demo_echo_* fields (if any)
    """

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
# Every non-siRNA/non-CRISPR tool (mRNA, structure prediction, aptamer, BLAST,
# scoring, ...). Named GENERAL — not MRNA — because it covers far more than mRNA.
GENERAL_LANGCHAIN_TOOLS: list[Any] = [
    score_rna_ligand_binding_with_gernabind,
    score_rna_ligand_binding_with_rnasmol,
    predict_mrna_stability_with_rnastop,
    predict_putative_ires_with_iresfinder,
    compute_rna_rna_interaction_vienna,
    compute_aso_target_accessibility_vienna,
    predict_rna_local_accessibility_profile_vienna,
    inverse_fold_rna_secondary_structure_vienna,
    analyze_cds_codon_metrics_with_codonw_slim,
    compute_cai_for_cds_sequence,
    shuffle_cds_junction_codons,
    compute_rna_sequence_gc_content,
    compute_rna_sequence_u_content,
    compute_dot_bracket_unpaired_fraction,
    run_blastn_similarity_search,
    run_bowtie2_short_alignment,
    predict_rna_secondary_structure,
    predict_rna_secondary_structure_with_linearfold,
    evaluate_rna_structure_with_linearfold,
    predict_rna_secondary_structure_with_linearfold_zuker,
    predict_rna_tertiary_structure_with_rhofold,
    design_mrna_cds_with_lineardesign,
    design_mrna_cds_batch_with_lineardesign,
    design_mrna_cds_junction_aware_with_lineardesign,
    design_mrna_cds_with_rnarl,
    design_mrna_cds_with_gemorna,
    design_5utr_with_gemorna,
    design_3utr_with_gemorna,
    predict_5utr_mrl_with_gemorna,
    predict_3utr_stability_with_gemorna,
    design_rna_sequence_with_rhodesign,
    design_rna_inverse_fold_with_ribodiffusion,
    run_odesign_inference,
    extract_rna_sequence_from_cif,
    build_odesign_aptamer_input_json,
    predict_protein_structure_with_proteinx,
    predict_rna_protein_complex_with_proteinx,
    score_rna_protein_complex_with_egarps,
    analyze_rna_protein_interface,
    identify_protein_binding_hotspots,
    score_structure_alignment,
]

ALL_LANGCHAIN_AGENT_TOOLS: list[Any] = (
    SIRNA_LANGCHAIN_TOOLS + CRISPR_LANGCHAIN_TOOLS + GENERAL_LANGCHAIN_TOOLS
)

WORKFLOW_DEMO_LANGCHAIN_TOOLS: list[Any] = [workflow_demo_echo]
