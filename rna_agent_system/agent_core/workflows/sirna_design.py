"""siRNA design workflow — antiviral (Evitar) and generic sliding-window (Layer 2).

Antiviral mode: target FASTA → Evitar → candidate siRNAs → duplex evaluation →
    off-target scan → score → rank.

Generic mode: target sequence → sliding window (19–21 nt) → local filter →
    duplex evaluation → BLAST off-target → score → rank.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  SirnaDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 sirna_design workflow 的权威实现。任何字段增删、函数签名变动、      ║
║  返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：               ║
║                                                                               ║
║    - agent_core/workflows/sirna_design.py  ← 本文件                          ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/workflows/registry.py                                         ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/capabilities/writebacks.py                                    ║
║    - agent_core/capabilities/base.py                                          ║
║    - agent_core/planning/base.py                                              ║
║    - agent_core/planning/llm_critic.py                                        ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - tests/test_sirna_design_workflow.py                                      ║
║    - tests/test_sirna_design_comprehensive.py                                 ║
║    - tests/test_sirna_workflow_api.py                                         ║
║    - tests/test_cli_sirna_entry.py                                            ║
║    - docs/INTERFACE_LOCKS.md                                                  ║
║    - docs/WORKFLOWS.md                                                        ║
║    - AGENTS.md                                                                ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import PROJECT_ROOT, read_sequence, save_sequence
from agent_core.sequence_utils import normalize_rna_sequence
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.evaluators import (
    CompositeEvaluator,
    DuplexBindingEvaluator,
    GCContentEvaluator,
    SelfStructureEvaluator,
)

_LOGGER = logging.getLogger("agent_core.workflows.sirna_design")

# Small helpers


_RC_MAP: dict[str, str] = {"A": "U", "U": "A", "G": "C", "C": "G"}


def _reverse_complement(rna_seq: str) -> str:
    """Return reverse complement of a normalized RNA sequence."""
    return "".join(_RC_MAP.get(base, base) for base in reversed(rna_seq.upper()))


def _has_consecutive_homopolymer(seq: str, max_run: int = 3) -> bool:
    """Return True if *seq* contains a run of identical bases longer than *max_run*."""
    if not seq:
        return False
    current = seq[0]
    count = 1
    for ch in seq[1:]:
        if ch == current:
            count += 1
            if count > max_run:
                return True
        else:
            current = ch
            count = 1
    return False


def _local_gc_content(seq: str) -> float:
    """Fast local GC fraction for filtering (no microservice call)."""
    if not seq:
        return 0.0
    gc = seq.count("G") + seq.count("C")
    return gc / len(seq)


# Input model — INTERFACE LOCKED (v1.0.0)
#
# Do NOT rename, remove, or narrow the type of any field without updating
# INTERFACE_LOCKS.md §10 and re-running the full test suite.


class SirnaDesignInput(BaseModel):
    """Input for the siRNA design workflow.

    DEFAULT PARAMETERS ARE CAREFULLY TUNED — DO NOT CHANGE THEM LIGHTLY.
    The defaults (mode=antiviral, candidate_count=10, maxgc=0.60, mingc=0.25,
    blast_perc_identity=90.0) are chosen by domain experts for typical use cases.
    Only override a parameter when the user EXPLICITLY requests a different value
    with clear biological justification. When in doubt, OMIT the parameter and
    let the workflow use its defaults.
    """

    model_config = ConfigDict(extra="forbid")

    mode: Literal["antiviral", "generic"] = "antiviral"

    # Target sequence (at least one must be provided)
    target_sequence: Optional[str] = Field(
        default=None,
        description="Plain RNA/DNA sequence (generic mode primary).",
    )
    target_fasta_path: Optional[str] = Field(
        default=None,
        description="FASTA filepath (antiviral mode primary; generic fallback).",
    )

    # Candidate count control
    candidate_count: int = Field(default=10, ge=1, le=100)

    # Off-target switch and resources
    off_target_scan: bool = True
    transcriptome_fasta_path: Optional[str] = None
    p3utr_path: Optional[str] = None
    weight_path: Optional[str] = None
    blast_subject_db: Optional[str] = None
    species: str = Field(
        default="homo_sapiens",
        description="Species ID for auto-resolving default transcriptome. "
                    "See data/references/species/ for available IDs.",
    )

    # Antiviral / Evitar parameters — only effective when mode="antiviral"
    evitar_mode: Literal["existing", "predesign"] = Field(
        default="existing",
        description="Evitar mode. Only used when mode='antiviral'. "
                    "'existing' for known-virus design; 'predesign' for future-virus pre-design.",
    )
    evitar_predict: Literal["predsi", "rnaxs", "multifapredsi", "CRISPR"] = Field(
        default="predsi",
        description="Evitar prediction algorithm. Only used when mode='antiviral'. "
                    "'CRISPR' is for Cas13 guide design.",
    )
    strains_path: Optional[str] = None
    ncores: int = 1

    # GC constraints (shared)
    maxgc: float = Field(default=0.60, ge=0.0, le=1.0)
    mingc: float = Field(default=0.25, ge=0.0, le=1.0)
    middlegc: float = Field(default=0.45, ge=0.0, le=1.0)

    # Allow / ban lists
    allow_path: Optional[str] = None
    ban_path: Optional[str] = None

    blast_perc_identity: float = Field(
        default=90.0,
        ge=70.0,
        le=100.0,
        description="BLAST percent identity threshold for off-target scan.",
    )
    alignment_tool: Literal["blast", "bowtie2"] = Field(
        default="bowtie2",
        description="Alignment engine for off-target scan. 'bowtie2' is faster for short sequences; 'blast' is the legacy option.",
    )
    bowtie2_score_min: str = Field(
        default="G,10,4",
        description="Bowtie2 --score-min function. Default G,10,4 allows ~2 mismatches in 21 nt.",
    )


# Scoring — INTERFACE LOCKED (v1.0.0)
#
# compute_sirna_rank_scores() is the canonical scoring function.
# Do NOT change the ranking logic or score keys without updating
# INTERFACE_LOCKS.md §10 and re-running the full test suite.


def compute_sirna_rank_scores(candidates: list[Candidate]) -> None:
    """Rank-based scoring across all candidates.

    For each candidate:
      1. Rank by duplex MFE (ViennaRNA RNAcofold): more negative = better → rank 1
      2. Rank by off-target count: fewer = better → rank 1
      3. total_score = rank_mfe + rank_offtarget (lower = better)
    """
    if not candidates:
        return

    def _duplex_mfe(c: Candidate) -> float:
        mfe = c.metadata.get("metrics_bundle", {}).get("duplex_mfe")
        return float(mfe) if mfe is not None else float("inf")

    def _off_target(c: Candidate) -> int:
        val = c.metadata.get("metrics_bundle", {}).get("off_target_count", 0)
        return int(val) if val is not None else 999999

    # Rank 1 = best (most negative MFE)
    sorted_mfe = sorted(enumerate(candidates), key=lambda x: _duplex_mfe(x[1]))
    mfe_ranks: dict[int, int] = {}
    for rank, (idx, _) in enumerate(sorted_mfe, start=1):
        mfe_ranks[idx] = rank

    # Rank 1 = best (fewest off-target hits)
    sorted_off = sorted(enumerate(candidates), key=lambda x: _off_target(x[1]))
    off_ranks: dict[int, int] = {}
    for rank, (idx, _) in enumerate(sorted_off, start=1):
        off_ranks[idx] = rank

    for i, candidate in enumerate(candidates):
        rank_mfe = mfe_ranks[i]
        rank_off = off_ranks[i]
        total = rank_mfe + rank_off
        mb = candidate.metadata.get("metrics_bundle", {})
        off_target = mb.get("off_target_count", 0)
        candidate.scores = {
            "rank_mfe": float(rank_mfe),
            "rank_offtarget": float(rank_off),
            "total_rank": float(total),
            "off_target_count": float(off_target) if off_target is not None else 999.0,
        }


def score_sirna_candidate(metrics: dict[str, Any]) -> dict[str, float]:
    """Legacy per-candidate scoring (kept for API compatibility).

    New workflows should call ``compute_sirna_rank_scores`` on the full
    candidate list for rank-based scoring.
    """
    duplex_mfe = metrics.get("duplex_mfe")
    off_target = metrics.get("off_target_count", 0)

    scores: dict[str, float] = {}

    # Efficiency: duplex MFE more negative = better; map [-40, 0] -> [0, 1]
    if duplex_mfe is not None:
        scores["efficiency_component"] = min(1.0, max(0.0, -float(duplex_mfe) / 40.0))
    else:
        scores["efficiency_component"] = 0.0

    scores["off_target_count"] = float(off_target)
    scores["specificity_component"] = 1.0 / (1.0 + float(off_target))
    # Legacy total_score kept for API compatibility; rank-based scoring
    # via compute_sirna_rank_scores is preferred.
    scores["total_score"] = scores["efficiency_component"]
    return scores


# Workflow — INTERFACE LOCKED (v1.0.0)
#
# Pipeline order: generate → evaluate → score → rank → WorkflowResult
# Do NOT change execution order, remove required_capabilities, or alter
# _state_writeback structure without updating INTERFACE_LOCKS.md §10.


class SirnaDesignWorkflow(BaseDomainWorkflow[SirnaDesignInput, WorkflowResult]):
    """siRNA design: antiviral (Evitar) or generic sliding-window.

    Pipeline: generate candidates → evaluate (GC + duplex + optional structure +
    off-target) → score → rank → WorkflowResult.
    """

    name = "sirna_design"
    description = (
        "Design siRNA candidates (antiviral via Evitar or generic sliding-window) "
        "with duplex evaluation and off-target safety screening."
    )
    input_model = SirnaDesignInput
    # NOTE: Listed capabilities are runtime-optional; the workflow checks
    # ``capabilities.has()`` before each invocation and degrades gracefully.
    required_capabilities = [
        "design_sirna_with_evitar",          # antiviral mode only
        "compute_rna_sequence_gc_content",   # optional GC evaluation
        "compute_sirna_duplex_binding_vienna",  # optional duplex MFE
        "predict_rna_secondary_structure",   # optional self-structure (fallback)
        "predict_rna_secondary_structure_with_linearfold",  # optional self-structure (primary)
        "run_blastn_similarity_search",      # optional off-target scan (BLAST)
        "run_bowtie2_short_alignment",       # optional off-target scan (Bowtie2, faster)
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._trace_records: list[ToolCallRecord] = []
        self.evaluator = CompositeEvaluator([
            GCContentEvaluator(self.capabilities),
            DuplexBindingEvaluator(self.capabilities),
            SelfStructureEvaluator(self.capabilities),
        ])

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, inp: Any, *, progress_callback=None) -> WorkflowResult:
        """Accept ``SirnaDesignInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = SirnaDesignInput(**inp)
        self._workflow_state = {"_sirna_input": inp}
        self._trace_records = []

        candidates = self.generate_candidates(inp)
        _LOGGER.info("workflow_generated_candidates count=%d workflow=%s", len(candidates), self.name)
        if progress_callback:
            progress_callback({
                "event": "generate_complete",
                "candidate_count": len(candidates),
                "workflow": self.name,
            })

        for i, candidate in enumerate(candidates):
            _LOGGER.info("workflow_evaluating_candidate idx=%d total=%d workflow=%s", i + 1, len(candidates), self.name)
            metrics = self.evaluate(candidate)
            # Unified GC filter — applied in evaluate phase for both branches
            gc_content = metrics.get("gc_content")
            if gc_content is not None and not (inp.mingc <= gc_content <= inp.maxgc):
                candidate.status = "gc_rejected"
                _LOGGER.info(
                    "sirna_gc_rejected idx=%d seq=%s gc=%.3f range=[%.2f,%.2f]",
                    i + 1, candidate.sequence, gc_content, inp.mingc, inp.maxgc,
                )
            else:
                candidate.status = "evaluated"
            if progress_callback:
                progress_callback({
                    "event": "evaluate_progress",
                    "current": i + 1,
                    "total": len(candidates),
                    "candidate_id": candidate.id,
                    "workflow": self.name,
                })

        # If no candidates were generated at all, return early
        if not candidates:
            return self.rank_and_format([])

        # Filter out GC-rejected candidates before scoring and ranking
        passing = [c for c in candidates if c.status != "gc_rejected"]
        _LOGGER.info("workflow_gc_filter total=%d passing=%d rejected=%d", len(candidates), len(passing), len(candidates) - len(passing))

        if not passing:
            return WorkflowResult(
                success=False,
                task_id="",
                summary="No candidates passed GC filter.",
                errors=["all_candidates_gc_rejected"],
            )

        # Rank-based scoring across passing candidates only
        compute_sirna_rank_scores(passing)

        _LOGGER.info("workflow_evaluation_complete count=%d workflow=%s", len(passing), self.name)

        # Limit final output to candidate_count
        if len(passing) > inp.candidate_count:
            passing = passing[:inp.candidate_count]

        result = self.rank_and_format(passing)
        # Aggregate per-candidate tool records + workflow-level records into trace
        result.trace = list(self._trace_records)
        for c in passing:
            result.trace.extend(c.tool_records)
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: SirnaDesignInput) -> list[Candidate]:
        if inp.mode == "antiviral":
            return self._generate_antiviral(inp)
        return self._generate_generic(inp)

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        seq = candidate.sequence
        filepath = save_sequence(seq, prefix="sirna")
        candidate.metadata["workspace_filepath"] = filepath

        context = {"workflow_state": self._workflow_state}
        metrics = self.evaluator.evaluate(candidate, context)
        metrics["sequence_length"] = len(seq)

        # ── Off-target scan (domain-specific, kept in workflow) ──
        off_target_count = 0
        if candidate.metadata.get("off_target_scan", True):
            off_target_count = self._evaluate_off_target(candidate, filepath)
        metrics["off_target_count"] = off_target_count
        metrics["specificity_score"] = 1.0 / (1.0 + float(off_target_count))

        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Legacy hook; actual scoring is done in ``run`` via ``compute_sirna_rank_scores``."""
        return score_sirna_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return self._empty_result("No candidates produced.")

        ranked = sort_candidates_by_score(
            candidates, score_key="total_rank", descending=False
        )
        best = ranked[0] if ranked else None

        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            parts = [
                f"#{i}",
                f"source={c.source}",
                f"len={len(c.sequence)}nt",
                f"GC={mb.get('gc_content'):.3f}" if mb.get("gc_content") is not None else "GC=N/A",
                f"duplexMFE={mb.get('duplex_mfe'):.2f}" if mb.get("duplex_mfe") is not None else "duplexMFE=N/A",
                f"offTarget={mb.get('off_target_count', 0)}",
                f"spec={mb.get('specificity_score', 0):.3f}",
                f"total_rank={scores.get('total_rank', 0.0):.3f}",
            ]
            # Generic mode extra info
            if "window_start" in c.metadata:
                parts.insert(2, f"pos={c.metadata['window_start']}-{c.metadata['window_end']}")
            detail_lines.append(" | ".join(parts))

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_total_rank={best.scores.get('total_rank') if best else None}",
            "---",
            *detail_lines,
        ]
        return WorkflowResult(
            success=True,
            task_id=f"sirna_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Candidate generation — antiviral branch
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_antiviral(self, inp: SirnaDesignInput) -> list[Candidate]:
        # Resolve target FASTA
        fasta_path = inp.target_fasta_path
        if not fasta_path and inp.target_sequence:
            fasta_path = save_sequence(inp.target_sequence, prefix="sirna_target")
            _LOGGER.info("sirna_antiviral_sequence_saved path=%s", fasta_path)
        if not fasta_path:
            _LOGGER.error("sirna_antiviral_no_target")
            return []

        if not self.capabilities.has("design_sirna_with_evitar"):
            _LOGGER.error("capability_missing design_sirna_with_evitar")
            return []

        args: dict[str, Any] = {
            "filepath": fasta_path,
            "mode": inp.evitar_mode,
            "predict": inp.evitar_predict,
            "ncores": inp.ncores,
            "off_target": inp.off_target_scan,
            # GC filtering is handled uniformly in evaluate() for both branches;
            # do not pass to Evitar so generate() is filter-free.
        }
        if inp.strains_path:
            args["strains_path"] = inp.strains_path
        if inp.transcriptome_fasta_path:
            args["transcriptome_path"] = inp.transcriptome_fasta_path
        if inp.p3utr_path:
            args["p3utr_path"] = inp.p3utr_path
        if inp.weight_path:
            args["weight_path"] = inp.weight_path
        if inp.allow_path:
            args["allow_path"] = inp.allow_path
        if inp.ban_path:
            args["ban_path"] = inp.ban_path

        try:
            cap = self.capabilities.get("design_sirna_with_evitar")
            cap_result = cap.invoke(args, state=self._workflow_state)

            # Record Evitar tool call in workflow-level trace
            record = ToolCallRecord(
                step_name="generate_antiviral_evitar",
                tool_name="design_sirna_with_evitar",
                input_summary=json.dumps(args, default=str),
                output_summary=json.dumps(cap_result.output, default=str)[:500],
                success=cap_result.success,
                error=cap_result.error,
                elapsed_time=getattr(cap_result, "elapsed_time", 0.0),
                artifacts=dict(cap_result.output) if cap_result.success else {},
                metrics={"top_results_count": len(cap_result.output.get("top_results", []))} if cap_result.success else {},
            )
            self._trace_records.append(record)
        except Exception as exc:
            _LOGGER.error("sirna_evitar_exception err=%s", exc)
            return []

        if not cap_result.success:
            _LOGGER.error("sirna_evitar_failed error=%s", cap_result.error)
            return []

        top_results = cap_result.output.get("top_results", [])
        if not top_results:
            _LOGGER.warning("sirna_evitar_empty_results")
            return []

        candidates: list[Candidate] = []
        seen: set[str] = set()
        for idx, row in enumerate(top_results):
            seq = self._extract_sequence_from_evitar_row(row)
            if not seq or seq in seen:
                continue
            seen.add(seq)
            candidates.append(
                Candidate(
                    sequence=seq,
                    sequence_type="sirna",
                    source=f"evitar:{inp.evitar_predict}",
                    metadata={
                        "evitar_row": row,
                        "evitar_mode": inp.evitar_mode,
                        "evitar_predict": inp.evitar_predict,
                        "off_target_scan": inp.off_target_scan,
                        "target_fasta_path": fasta_path,
                    },
                )
            )
            if len(candidates) >= inp.candidate_count:
                break

        _LOGGER.info("sirna_antiviral_candidates total=%d unique=%d", len(top_results), len(candidates))
        return candidates

    # ─────────────────────────────────────────────────────────────────────────
    # Candidate generation — generic branch
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_generic(self, inp: SirnaDesignInput) -> list[Candidate]:
        # Resolve target sequence
        target_seq: Optional[str] = None
        if inp.target_sequence:
            target_seq = normalize_rna_sequence(inp.target_sequence)
        elif inp.target_fasta_path:
            try:
                raw = read_sequence(inp.target_fasta_path)
                target_seq = normalize_rna_sequence(raw)
            except Exception as exc:
                _LOGGER.error("sirna_generic_read_failed path=%s err=%s", inp.target_fasta_path, exc)
                return []

        if not target_seq:
            _LOGGER.error("sirna_generic_no_target_sequence")
            return []

        if len(target_seq) < 40:
            _LOGGER.warning("sirna_generic_sequence_too_short len=%d", len(target_seq))
            return []

        window = 21
        step = 1
        candidates: list[Candidate] = []

        for i in range(0, len(target_seq) - window + 1, step):
            sense = target_seq[i : i + window]

            # No homopolymer runs > 3
            if _has_consecutive_homopolymer(sense, max_run=3):
                continue

            # Sense should not end with A (antisense 5' should not start with U)
            if sense.endswith("A"):
                continue

            candidates.append(
                Candidate(
                    sequence=sense,
                    sequence_type="sirna",
                    source=f"sliding_window:pos={i}",
                    metadata={
                        "window_start": i,
                        "window_end": i + window,
                        "target_sequence": target_seq,
                        "off_target_scan": inp.off_target_scan,
                    },
                )
            )

        _LOGGER.info(
            "sirna_generic_candidates windows=%d kept=%d",
            len(target_seq) - window + 1,
            len(candidates),
        )
        return candidates

    # ─────────────────────────────────────────────────────────────────────────
    # Off-target evaluation
    # ─────────────────────────────────────────────────────────────────────────

    def _evaluate_off_target(self, candidate: Candidate, sirna_filepath: str) -> int:
        """Return off-target hit count. 0 if no scan performed."""
        # Antiviral mode: check if Evitar row already has off-target info
        evitar_row = candidate.metadata.get("evitar_row")
        if isinstance(evitar_row, dict):
            for key in ("off_target_hits", "offtarget_hits", "pm_hits", "um_hits"):
                val = evitar_row.get(key)
                if val is not None:
                    try:
                        return int(val)
                    except (TypeError, ValueError):
                        pass

        inp = self._workflow_state.get("_sirna_input")
        alignment_tool = getattr(inp, "alignment_tool", "blast") if inp else "blast"

        if alignment_tool == "bowtie2":
            return self._evaluate_off_target_bowtie2(candidate, sirna_filepath)
        return self._evaluate_off_target_blast(candidate, sirna_filepath)

    def _evaluate_off_target_blast(self, candidate: Candidate, sirna_filepath: str) -> int:
        """BLAST-based off-target scan."""
        if not self.capabilities.has("run_blastn_similarity_search"):
            _LOGGER.debug("blast_capability_missing skipping_off_target")
            return 0

        subject = candidate.metadata.get("blast_subject")
        if not subject:
            wf_inp = self._workflow_state.get("_sirna_input")
            if wf_inp:
                subject = getattr(wf_inp, "transcriptome_fasta_path", None) or getattr(
                    wf_inp, "blast_subject_db", None
                )
        if not subject:
            subject = self._resolve_default_transcriptome()
        if not subject:
            _LOGGER.debug("sirna_no_transcriptome_for_blast skipping")
            return 0

        perc_identity = 90.0
        inp = self._workflow_state.get("_sirna_input")
        if inp and hasattr(inp, "blast_perc_identity"):
            perc_identity = float(inp.blast_perc_identity)

        try:
            blast_args: dict[str, Any] = {
                "filepath": sirna_filepath,
                "task": "blastn-short",
                "perc_identity": perc_identity,
                "max_target_seqs": 50,
            }
            if subject.endswith(".fasta") or subject.endswith(".fa"):
                blast_args["subject_fasta_path"] = subject
            else:
                blast_args["subject_db"] = subject

            cap = self.capabilities.get("run_blastn_similarity_search")
            blast_res = cap.invoke(blast_args, state=self._workflow_state)

            blast_record = ToolCallRecord(
                step_name=f"{candidate.id}_blast_off_target",
                tool_name="run_blastn_similarity_search",
                input_summary=json.dumps(blast_args, default=str),
                output_summary=json.dumps(blast_res.output, default=str)[:500],
                success=blast_res.success,
                error=blast_res.error,
                elapsed_time=getattr(blast_res, "elapsed_time", 0.0),
                artifacts=dict(blast_res.output) if blast_res.success else {},
                metrics={"hit_count": blast_res.output.get("hit_count", 0)} if blast_res.success else {},
            )
            candidate.add_tool_record(blast_record)

            if blast_res.success:
                return int(blast_res.output.get("hit_count", 0))
            _LOGGER.warning("sirna_blast_failed error=%s", blast_res.error)
        except Exception as exc:
            _LOGGER.warning("sirna_blast_exception exc=%s", exc)
        return 0

    def _evaluate_off_target_bowtie2(self, candidate: Candidate, sirna_filepath: str) -> int:
        """Bowtie2-based off-target scan (faster for short sequences)."""
        if not self.capabilities.has("run_bowtie2_short_alignment"):
            _LOGGER.debug("bowtie2_capability_missing skipping_off_target")
            return 0

        subject = candidate.metadata.get("blast_subject")
        if not subject:
            wf_inp = self._workflow_state.get("_sirna_input")
            if wf_inp:
                subject = getattr(wf_inp, "transcriptome_fasta_path", None) or getattr(
                    wf_inp, "blast_subject_db", None
                )
        if not subject:
            subject = self._resolve_default_transcriptome()
        if not subject:
            _LOGGER.debug("sirna_no_transcriptome_for_bowtie2 skipping")
            return 0

        score_min = "G,10,4"
        inp = self._workflow_state.get("_sirna_input")
        if inp and hasattr(inp, "bowtie2_score_min"):
            score_min = str(inp.bowtie2_score_min)

        try:
            bt2_args: dict[str, Any] = {
                "filepath": sirna_filepath,
                "mode": "local",
                "k": 50,
                "score_min": score_min,
            }
            if subject.endswith(".fasta") or subject.endswith(".fa"):
                # Check for pre-built bowtie2 index to avoid rebuilding on every call
                index_prefix = subject[:-6] if subject.endswith(".fasta") else subject[:-3]
                index_path = Path(index_prefix)
                has_index = (
                    (index_path.parent / (index_path.name + ".1.bt2")).exists()
                    or (index_path.parent / (index_path.name + ".1.bt2l")).exists()
                )
                if has_index:
                    bt2_args["subject_index"] = str(index_prefix)
                else:
                    bt2_args["subject_fasta_path"] = subject
            else:
                bt2_args["subject_index"] = subject

            cap = self.capabilities.get("run_bowtie2_short_alignment")
            bt2_res = cap.invoke(bt2_args, state=self._workflow_state)

            bt2_record = ToolCallRecord(
                step_name=f"{candidate.id}_bowtie2_off_target",
                tool_name="run_bowtie2_short_alignment",
                input_summary=json.dumps(bt2_args, default=str),
                output_summary=json.dumps(bt2_res.output, default=str)[:500],
                success=bt2_res.success,
                error=bt2_res.error,
                elapsed_time=getattr(bt2_res, "elapsed_time", 0.0),
                artifacts=dict(bt2_res.output) if bt2_res.success else {},
                metrics={"hit_count": bt2_res.output.get("hit_count", 0)} if bt2_res.success else {},
            )
            candidate.add_tool_record(bt2_record)

            if bt2_res.success:
                return int(bt2_res.output.get("hit_count", 0))
            _LOGGER.warning("sirna_bowtie2_failed error=%s", bt2_res.error)
        except Exception as exc:
            _LOGGER.warning("sirna_bowtie2_exception exc=%s", exc)
        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_default_transcriptome(self) -> Optional[str]:
        """Return path to pre-installed reference transcriptome if available.

        Looks under ``data/references/species/<species>/transcripts.fa``
        relative to the project root.
        """
        inp = self._workflow_state.get("_sirna_input")
        species = getattr(inp, "species", "homo_sapiens") if inp else "homo_sapiens"
        # Allow override via environment variable
        import os
        env_species = os.environ.get("RNA_AGENT_DEFAULT_SPECIES", "").strip()
        if env_species:
            species = env_species

        candidate = (
            PROJECT_ROOT
            / "data"
            / "references"
            / "species"
            / species
            / "transcripts.fa"
        )
        if candidate.exists():
            _LOGGER.info("sirna_auto_transcriptome species=%s path=%s", species, candidate)
            return str(candidate)
        _LOGGER.debug("sirna_auto_transcriptome_not_found species=%s path=%s", species, candidate)
        return None

    @staticmethod
    def _extract_sequence_from_evitar_row(row: dict[str, Any]) -> str:
        """Extract siRNA sequence from an Evitar top_results row."""
        for key in ("siRNA", "siRNA_sequence", "guide", "guide_sequence", "GuideSeq", "sequence"):
            val = row.get(key)
            if val:
                seq = normalize_rna_sequence(str(val))
                if seq:
                    return seq
        return ""


# LLM Critic Configuration — INTERFACE LOCKED (v1.0.0)
#
# SIRNA_CRITIC_CONFIG.adjustable_params keys are consumed by
# ExecutionController._apply_parameter_overrides().
# Do NOT rename adjustable_params keys without updating
# INTERFACE_LOCKS.md §10 and re-running the full test suite.

from agent_core.planning.llm_critic import BaseLLMCritic, CriticConfig

SIRNA_CRITIC_CONFIG = CriticConfig(
    workflow_name="sirna_design",
    workflow_description="Design siRNA candidates for gene silencing",
    evaluation_dimensions=[
        "Duplex MFE (RNAcofold): more negative = more stable duplex. Very positive values indicate poor binding.",
        "Off-target count should be minimal. High off-target counts reduce specificity and increase toxicity.",
        "GC content of siRNA should be 30-60%. Too high GC increases off-target effects; too low reduces stability.",
        "Consecutive homopolymers (>3 identical bases) should be avoided as they can cause non-specific effects.",
        "For antiviral mode: Evitar predicted efficiency should be high.",
    ],
    adjustable_params={
        "mode": {
            "type": "enum",
            "values": ["antiviral", "generic"],
            "hint": "Switch between antiviral (uses Evitar) and generic (sliding window) modes.",
        },
        "candidate_count": {
            "type": "int",
            "min": 1,
            "max": 100,
            "hint": "Number of candidates to generate. Increase if too few survive filtering.",
        },
        "maxgc": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Maximum GC content filter. Lower if candidates have too-high GC.",
        },
        "mingc": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Minimum GC content filter. Raise if candidates have too-low GC.",
        },
        "off_target_scan": {
            "type": "bool",
            "hint": "Whether to run BLAST off-target scan. Keep True unless it's failing.",
        },
        "blast_perc_identity": {
            "type": "float",
            "min": 70.0,
            "max": 100.0,
            "hint": "BLAST percent identity threshold (only used when alignment_tool='blast'). Lower = stricter off-target filtering (fewer matches).",
        },
        "alignment_tool": {
            "type": "enum",
            "values": ["blast", "bowtie2"],
            "hint": "Switch between BLAST (legacy, slower) and Bowtie2 (default, faster) off-target scan engines.",
        },
        "bowtie2_score_min": {
            "type": "str",
            "hint": "Bowtie2 --score-min function (only used when alignment_tool='bowtie2'). Default G,10,4 allows ~2 mismatches in 21 nt. Tighten (e.g. G,20,8) for stricter filtering.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
)


class SirnaDesignLLMCritic(BaseLLMCritic):
    """LLM-driven Critic for siRNA design workflow."""

    def _default_config(self) -> CriticConfig:
        return SIRNA_CRITIC_CONFIG
