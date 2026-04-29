"""mRNA CDS design & optimisation workflow — the golden path (Layer 2).

Protein sequence → CDS design (LinearDesign λ=[0,1,4,10] + RNARL + GEMORNA) →
fold + GC + unpaired-fraction evaluation → scoring → ranking → WorkflowResult.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence, save_text_file
from agent_core.workflow_models import Candidate, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.mrna_scoring import (
    compute_mrna_metric_bundle,
    score_mrna_candidate,
)

_LOGGER = logging.getLogger("agent_core.workflows.mrna_cds_design")


class MrnaCdsDesignInput(BaseModel):
    """Input for the mRNA CDS design golden path."""

    model_config = ConfigDict(extra="forbid")

    protein_sequence: str = Field(..., description="Amino-acid string (uppercase, 1-letter codes).")
    design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"] = "all"
    lambda_value: float = Field(default=0.0, description="LinearDesign MFE/CAI balance.")
    model_type: str = Field(default="Homo sapiens mRNA", description="RNARL model type.")
    run_fold: bool = Field(default=True)
    run_gc: bool = Field(default=True)
    target_gc_mid: Optional[float] = Field(default=None, description="Override GC band mid-point for scoring.")


class MrnaCdsDesignWorkflow(BaseDomainWorkflow[MrnaCdsDesignInput, WorkflowResult]):
    """Golden-path workflow: protein → multi-tool CDS → fold + GC + unpaired → score → rank."""

    name = "mrna_cds_design"
    description = "Design mRNA CDS from protein sequence using multiple tools, evaluate, score, and rank candidates."
    required_capabilities = [
        "design_mrna_cds_with_lineardesign",
        "design_mrna_cds_with_rnarl",
        "design_mrna_cds_with_gemorna",
        "predict_rna_secondary_structure",
        "predict_rna_secondary_structure_with_linearfold",
        "compute_rna_sequence_gc_content",
        "compute_dot_bracket_unpaired_fraction",
        "predict_mrna_stability_with_rnastop",
        "compute_cai_for_cds_sequence",
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
        """Design CDS candidates from the protein sequence using multiple tools.

        Default strategy (``design_tool="all"``):
        - LinearDesign: λ = 0, 1, 4, 10  → 4 candidates
        - RNARL: 1 call → 1 candidate
        - GEMORNA: 1 call → 1 candidate
        Total = 6 candidates (deduplicated).
        """
        protein_fp = save_sequence(inp.protein_sequence, prefix="protein")
        _LOGGER.info(
            "mrna_cds_design protein_saved filepath=%s len_aa=%d",
            protein_fp,
            len(inp.protein_sequence),
        )

        design_configs: list[tuple[str, dict[str, Any]]] = []

        if inp.design_tool in ("all", "lineardesign"):
            for lam in (0.0, 1.0, 4.0, 10.0):
                design_configs.append(
                    ("lineardesign", {"lambda_value": lam})
                )

        if inp.design_tool in ("all", "rnarl"):
            design_configs.append(
                ("rnarl", {"model_type": inp.model_type})
            )

        if inp.design_tool in ("all", "gemorna"):
            design_configs.append(("gemorna", {}))

        candidates: list[Candidate] = []
        for tool_name, extra_args in design_configs:
            try:
                cap_name = f"design_mrna_cds_with_{tool_name}"
                if not self.capabilities.has(cap_name):
                    _LOGGER.warning("capability missing: %s", cap_name)
                    continue

                cap = self.capabilities.get(cap_name)
                args: dict[str, Any] = {"filepath": protein_fp, **extra_args}
                cap_result = cap.invoke(args, state=self._workflow_state)

                if not cap_result.success:
                    _LOGGER.warning(
                        "design failed tool=%s error=%s", tool_name, cap_result.error
                    )
                    continue

                seq = str(cap_result.output.get("generated_sequence", ""))
                if not seq:
                    _LOGGER.warning("design empty tool=%s", tool_name)
                    continue

                param_label = ""
                if tool_name == "lineardesign" and "lambda_value" in extra_args:
                    param_label = f"_lambda{extra_args['lambda_value']}"

                candidate = Candidate(
                    sequence=seq,
                    sequence_type="mrna",
                    source=f"cds_design:{tool_name}{param_label}",
                    metadata={
                        "design_tool": tool_name,
                        "design_params": extra_args,
                        "protein_sequence": inp.protein_sequence,
                        "protein_filepath": protein_fp,
                        "design_output": cap_result.output,
                        "target_gc_mid": getattr(inp, "target_gc_mid", None),
                    },
                )
                candidates.append(candidate)
                _LOGGER.info(
                    "candidate_generated tool=%s params=%s len_nt=%d",
                    tool_name,
                    extra_args,
                    len(seq),
                )
            except Exception as exc:
                _LOGGER.error("design exception tool=%s err=%s", tool_name, exc)

        # Deduplicate by sequence
        seen: set[str] = set()
        unique: list[Candidate] = []
        for c in candidates:
            if c.sequence not in seen:
                seen.add(c.sequence)
                unique.append(c)

        _LOGGER.info(
            "candidates_generated total=%d unique=%d",
            len(candidates),
            len(unique),
        )
        return unique

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Run GC + fold (+ unpaired fraction) on the candidate sequence."""
        filepath = save_sequence(candidate.sequence, prefix="mrna_cds")
        candidate.metadata["workspace_filepath"] = filepath

        gc_content: Optional[float] = None
        seq_len: Optional[int] = None
        mfe: Optional[float] = None
        fold_tool: Optional[str] = None
        structure: Optional[str] = None
        unpaired: Optional[float] = None
        rnastop_overall_stability: Optional[float] = None
        cai_score: Optional[float] = None

        # ── GC content ──
        if self.capabilities.has("compute_rna_sequence_gc_content"):
            gc_res = self.capabilities.get("compute_rna_sequence_gc_content").invoke(
                {"filepath": filepath}, state=self._workflow_state
            )
            if gc_res.success:
                gc_content = _pick_float(gc_res.output, "gc_content")
                seq_len = _pick_int(gc_res.output, "sequence_length")
            else:
                _LOGGER.warning("mrna_cds_design gc_failed error=%s", gc_res.error)

        # ── Secondary structure (ViennaRNA → LinearFold fallback) ──
        if self.capabilities.has("predict_rna_secondary_structure"):
            fold_res = self.capabilities.get(
                "predict_rna_secondary_structure"
            ).invoke({"filepath": filepath}, state=self._workflow_state)
            if fold_res.success:
                mfe = _pick_float(fold_res.output, "mfe_kcal_per_mol")
                fold_tool = "ViennaRNA"
                structure = fold_res.output.get("structure", "")
            else:
                _LOGGER.warning(
                    "mrna_cds_design fold_failed error=%s", fold_res.error
                )
                if self.capabilities.has(
                    "predict_rna_secondary_structure_with_linearfold"
                ):
                    lf_res = self.capabilities.get(
                        "predict_rna_secondary_structure_with_linearfold"
                    ).invoke({"filepath": filepath}, state=self._workflow_state)
                    if lf_res.success:
                        mfe = _pick_float(lf_res.output, "mfe")
                        fold_tool = "LinearFold"
                        structure = lf_res.output.get("structure", "")

        # ── Unpaired fraction (needs dot-bracket structure) ──
        if structure and self.capabilities.has(
            "compute_dot_bracket_unpaired_fraction"
        ):
            struct_fp = save_text_file(structure, prefix="structure", suffix=".db")
            unp_res = self.capabilities.get(
                "compute_dot_bracket_unpaired_fraction"
            ).invoke({"filepath": struct_fp}, state=self._workflow_state)
            if unp_res.success:
                unpaired = _pick_float(unp_res.output, "unpaired_fraction")
            else:
                _LOGGER.warning(
                    "mrna_cds_design unpaired_failed error=%s", unp_res.error
                )

        # ── RNASTOP overall stability ──
        if self.capabilities.has("predict_mrna_stability_with_rnastop"):
            rnastop_args: dict[str, Any] = {"filepath": filepath}
            if structure:
                rnastop_args["structure"] = structure
            rnastop_res = self.capabilities.get(
                "predict_mrna_stability_with_rnastop"
            ).invoke(rnastop_args, state=self._workflow_state)
            if rnastop_res.success:
                rnastop_overall_stability = _pick_float(
                    rnastop_res.output, "overall_stability"
                )
            else:
                _LOGGER.warning(
                    "mrna_cds_design rnastop_failed error=%s", rnastop_res.error
                )

        # ── CAI (always computed via compute_cai_for_cds_sequence) ──
        if self.capabilities.has("compute_cai_for_cds_sequence"):
            cai_res = self.capabilities.get("compute_cai_for_cds_sequence").invoke(
                {"filepath": filepath, "species": "Homo sapiens"},
                state=self._workflow_state,
            )
            if cai_res.success:
                cai_score = _pick_float(cai_res.output, "cai_score")
            else:
                _LOGGER.warning(
                    "mrna_cds_design cai_failed error=%s", cai_res.error
                )

        bundle = compute_mrna_metric_bundle(
            sequence=candidate.sequence,
            gc_from_tools=gc_content,
            sequence_length_from_tools=seq_len,
            mfe_kcal_per_mol=mfe,
            unpaired_fraction=unpaired,
            rnastop_overall_stability=rnastop_overall_stability,
            cai_score=cai_score,
        )
        bundle["fold_tool"] = fold_tool
        bundle["target_gc_mid"] = candidate.metadata.get("target_gc_mid")
        candidate.metadata["metrics_bundle"] = bundle
        candidate.metadata["fold_tool"] = fold_tool
        candidate.metadata["structure"] = structure
        return bundle

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        return score_mrna_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return WorkflowResult(
                success=False,
                task_id="",
                summary="No candidates produced.",
                errors=["empty_candidate_list"],
            )

        ranked = sort_candidates_by_score(
            candidates, score_key="total_score", descending=True
        )
        best = ranked[0] if ranked else None

        # Build rich per-candidate summary lines
        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            line_parts = [
                f"#{i}",
                f"source={c.source}",
                f"len={len(c.sequence)}nt",
                f"GC={mb.get('gc_content'):.3f}" if mb.get("gc_content") is not None else "GC=N/A",
                f"MFE={mb.get('mfe_kcal_per_mol'):.2f}({mb.get('fold_tool', '?')})" if mb.get("mfe_kcal_per_mol") is not None else "MFE=N/A",
                f"MFE/nt={mb.get('mfe_per_nt'):.4f}" if mb.get("mfe_per_nt") is not None else "MFE/nt=N/A",
                f"unpaired={mb.get('unpaired_fraction'):.3f}" if mb.get("unpaired_fraction") is not None else "unpaired=N/A",
                f"RNASTOP={mb.get('rnastop_overall_stability'):.4f}" if mb.get("rnastop_overall_stability") is not None else "RNASTOP=N/A",
                f"CAI={mb.get('cai_score'):.4f}" if mb.get("cai_score") is not None else "CAI=N/A",
                f"total_score={scores.get('total_score', 0.0):.3f}",
            ]
            detail_lines.append(" | ".join(line_parts))

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_total_score={best.scores.get('total_score') if best else None}",
            "---",
            *detail_lines,
        ]
        return WorkflowResult(
            success=True,
            task_id=f"mrna_cds_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )


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
