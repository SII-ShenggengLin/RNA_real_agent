"""mRNA CDS design & optimisation workflow — the golden path (Layer 2).

Protein sequence → CDS design (LinearDesign / RNARL / GEMORNA) →
fold + GC evaluation → scoring → ranking → WorkflowResult.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.workflow_models import Candidate, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.mrna_scoring import (
    MrnaScoreWeights,
    compute_mrna_metric_bundle,
    score_mrna_candidate,
)

_LOGGER = logging.getLogger("agent_core.workflows.mrna_cds_design")


class MrnaCdsDesignInput(BaseModel):
    """Input for the mRNA CDS design golden path."""

    model_config = ConfigDict(extra="forbid")

    protein_sequence: str = Field(..., description="Amino-acid string (uppercase, 1-letter codes).")
    design_tool: Literal["lineardesign", "rnarl", "gemorna"] = "lineardesign"
    lambda_value: float = Field(default=0.0, description="LinearDesign MFE/CAI balance.")
    model_type: str = Field(default="Homo sapiens mRNA", description="RNARL model type.")
    run_fold: bool = Field(default=True)
    run_gc: bool = Field(default=True)
    score_weights: Optional[MrnaScoreWeights] = None
    target_length_nt: Optional[int] = Field(default=None)
    target_gc_mid: Optional[float] = Field(default=None, description="Override GC band mid-point for scoring.")


class MrnaCdsDesignWorkflow(BaseDomainWorkflow[MrnaCdsDesignInput, WorkflowResult]):
    """Golden-path workflow: protein → CDS → fold + GC → score → rank."""

    name = "mrna_cds_design"
    description = "Design mRNA CDS from protein sequence, evaluate, score, and rank candidates."
    required_capabilities = [
        "design_mrna_cds_with_lineardesign",
        "design_mrna_cds_with_rnarl",
        "design_mrna_cds_with_gemorna",
        "predict_rna_secondary_structure",
        "predict_rna_secondary_structure_with_linearfold",
        "compute_rna_sequence_gc_content",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, inp: Any) -> WorkflowResult:
        """Accept either ``MrnaCdsDesignInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = MrnaCdsDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        result = super().run(inp)
        # Attach internal writeback state so ExecutionController can merge it
        result._state_writeback = dict(self._workflow_state)  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: MrnaCdsDesignInput) -> list[Candidate]:
        """Design one or more CDS candidates from the protein sequence."""
        protein_fp = save_sequence(inp.protein_sequence, prefix="protein")
        _LOGGER.info("mrna_cds_design protein_saved filepath=%s len_aa=%d", protein_fp, len(inp.protein_sequence))

        design_cap = self._resolve_design_capability(inp.design_tool)
        design_args = self._build_design_args(inp, protein_fp)

        cap_result = design_cap.invoke(design_args, state=self._workflow_state)
        if not cap_result.success:
            _LOGGER.error("mrna_cds_design failed tool=%s error=%s", design_cap.name, cap_result.error)
            return []

        output = cap_result.output
        generated_sequence = str(output.get("generated_sequence", ""))
        if not generated_sequence:
            _LOGGER.error("mrna_cds_design empty_sequence tool=%s", design_cap.name)
            return []

        candidate = Candidate(
            sequence=generated_sequence,
            sequence_type="mrna",
            source=f"cds_design:{inp.design_tool}",
            metadata={
                "design_tool": inp.design_tool,
                "protein_sequence": inp.protein_sequence,
                "protein_filepath": protein_fp,
                "design_output": output,
                "target_gc_mid": getattr(inp, "target_gc_mid", None),
            },
        )
        _LOGGER.info("mrna_cds_design candidate_generated len_nt=%d", len(generated_sequence))
        return [candidate]

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Run fold + GC on the candidate sequence."""
        filepath = save_sequence(candidate.sequence, prefix="mrna_cds")
        candidate.metadata["workspace_filepath"] = filepath

        gc_content: Optional[float] = None
        seq_len: Optional[int] = None
        mfe: Optional[float] = None

        if self.capabilities.has("compute_rna_sequence_gc_content"):
            gc_res = self.capabilities.get("compute_rna_sequence_gc_content").invoke({"filepath": filepath}, state=self._workflow_state)
            if gc_res.success:
                gc_content = _pick_float(gc_res.output, "gc_content")
                seq_len = _pick_int(gc_res.output, "sequence_length")
            else:
                _LOGGER.warning("mrna_cds_design gc_failed error=%s", gc_res.error)

        if self.capabilities.has("predict_rna_secondary_structure"):
            fold_res = self.capabilities.get("predict_rna_secondary_structure").invoke({"filepath": filepath}, state=self._workflow_state)
            if fold_res.success:
                mfe = _pick_float(fold_res.output, "mfe_kcal_per_mol")
            else:
                _LOGGER.warning("mrna_cds_design fold_failed error=%s", fold_res.error)
                # Fallback to LinearFold
                if self.capabilities.has("predict_rna_secondary_structure_with_linearfold"):
                    lf_res = self.capabilities.get("predict_rna_secondary_structure_with_linearfold").invoke({"filepath": filepath}, state=self._workflow_state)
                    if lf_res.success:
                        mfe = _pick_float(lf_res.output, "mfe")

        bundle = compute_mrna_metric_bundle(
            sequence=candidate.sequence,
            gc_from_tools=gc_content,
            sequence_length_from_tools=seq_len,
            mfe_kcal_per_mol=mfe,
            target_length_nt=candidate.metadata.get("target_length_nt"),
        )
        bundle["target_gc_mid"] = candidate.metadata.get("target_gc_mid")
        candidate.metadata["metrics_bundle"] = bundle
        return bundle

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        kwargs: dict[str, Any] = {
            "weights": metrics.get("_score_weights"),
            "target_length_nt": metrics.get("target_length_nt"),
        }
        tgc = metrics.get("target_gc_mid")
        if tgc is not None:
            kwargs["gc_mid"] = float(tgc)
            kwargs["gc_low"] = float(tgc) - 0.08
            kwargs["gc_high"] = float(tgc) + 0.08
        return score_mrna_candidate(metrics, **kwargs)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return WorkflowResult(
                success=False,
                task_id="",
                summary="No candidates produced.",
                errors=["empty_candidate_list"],
            )

        ranked = sort_candidates_by_score(candidates, score_key="total_score", descending=True)
        best = ranked[0] if ranked else None

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_total_score={best.scores.get('total_score') if best else None}",
        ]
        return WorkflowResult(
            success=True,
            task_id=f"mrna_cds_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="; ".join(summary_parts),
            errors=[],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_design_capability(self, design_tool: str):
        cap_name = f"design_mrna_cds_with_{design_tool}"
        if not self.capabilities.has(cap_name):
            raise RuntimeError(f"Design capability '{cap_name}' not registered")
        return self.capabilities.get(cap_name)

    def _build_design_args(self, inp: MrnaCdsDesignInput, protein_fp: str) -> dict[str, Any]:
        args: dict[str, Any] = {"filepath": protein_fp}
        if inp.design_tool == "lineardesign":
            args["lambda_value"] = inp.lambda_value
        elif inp.design_tool == "rnarl":
            args["model_type"] = inp.model_type
        # gemorna uses default args
        return args


# ─────────────────────────────────────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pick_float(data: dict[str, Any], key: str) -> Optional[float]:
    if key in data:
        try:
            return float(data[key])
        except (TypeError, ValueError):
            pass
    return None


def _pick_int(data: dict[str, Any], key: str) -> Optional[int]:
    if key in data:
        try:
            return int(data[key])
        except (TypeError, ValueError):
            pass
    return None
