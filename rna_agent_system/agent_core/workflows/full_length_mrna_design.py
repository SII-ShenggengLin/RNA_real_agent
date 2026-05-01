"""Full-length mRNA design workflow — 5'UTR + CDS + 3'UTR (Layer 2).

Protein sequence → CDS candidates via MrnaCdsDesignWorkflow (generate + evaluate)
→ UTR combinations (GEMORNA short/medium/long) → full-length / UTR incremental
evaluation → full-length scoring → ranking → WorkflowResult.

Strategy: Only Strategy C is implemented (CDS-only baseline + UTR append).
Architecture: Full-length workflow reuses MrnaCdsDesignWorkflow for CDS
generation and evaluation; only full-length and UTR metrics are computed here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.planning.base import Critic
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput, MrnaCdsDesignWorkflow
from agent_core.workflows.mrna_scoring import score_mrna_candidate

_LOGGER = logging.getLogger("agent_core.workflows.full_length_mrna_design")

# UTR length presets exposed by GEMORNA
_UTR_PRESETS: list[str] = ["short", "medium", "long"]


class FullLengthMrnaDesignInput(BaseModel):
    """Input for the full-length mRNA design workflow."""

    model_config = ConfigDict(extra="forbid")

    protein_sequence: str = Field(..., description="Amino-acid string (uppercase, 1-letter codes).")
    design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"] = "all"
    lambda_value: float = Field(default=0.0, description="LinearDesign MFE/CAI balance.")
    model_type: str = Field(default="Homo sapiens mRNA", description="RNARL model type.")
    utr_mode: Literal["short", "medium", "long", "all"] = "all"
    run_fold: bool = Field(default=True)
    run_gc: bool = Field(default=True)


def score_full_length_mrna_candidate(
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Return per-module raw scores for Borda-count ranking in rank_and_format."""

    cds_length = int(metrics.get("cds_length", 0))

    # CDS component: classic combined score (-mfe + codon_count * log(CAI))
    cds_bundle = {
        "mfe_kcal_per_mol": metrics.get("cds_mfe"),
        "cai_score": metrics.get("cds_cai"),
        "sequence_length": cds_length,
    }
    cds_scores = score_mrna_candidate(cds_bundle)
    cds_combined_score = cds_scores.get("combined_score", 0.0)
    cds_component = cds_combined_score / cds_length if cds_length > 0 else None

    # 5'UTR MRL component
    utr5_mrl = metrics.get("utr5_predicted_mrl")
    utr5_component = float(utr5_mrl) if utr5_mrl is not None else None

    # 3'UTR stability component
    utr3_stability = metrics.get("utr3_predicted_stability")
    utr3_component = float(utr3_stability) if utr3_stability is not None else None

    return {
        "cds_component": cds_component,
        "cds_combined_score": float(cds_combined_score),
        "utr5_mrl": utr5_component,
        "utr3_stability": utr3_component,
    }


class FullLengthMrnaDesignWorkflow(
    BaseDomainWorkflow[FullLengthMrnaDesignInput, WorkflowResult]
):
    """Protein → CDS (via MrnaCdsDesignWorkflow) + UTR → incremental eval → Borda rank."""

    name = "full_length_mrna_design"
    description = (
        "Design full-length mRNA (5'UTR + CDS + 3'UTR) from protein sequence, "
        "reuse MrnaCdsDesignWorkflow for CDS generation and evaluation, "
        "evaluate full-length + UTR metrics incrementally, score, and rank candidates."
    )
    required_capabilities = [
        "design_5utr_with_gemorna",
        "design_3utr_with_gemorna",
        "predict_5utr_mrl_with_gemorna",
        "predict_3utr_stability_with_gemorna",
        "predict_rna_secondary_structure",
        "predict_rna_secondary_structure_with_linearfold",
        "predict_putative_ires_with_iresfinder",
        "predict_mrna_stability_with_rnastop",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, inp: Any) -> WorkflowResult:
        """Accept either ``FullLengthMrnaDesignInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = FullLengthMrnaDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        result = super().run(inp)
        result._state_writeback = dict(self._workflow_state)  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: FullLengthMrnaDesignInput) -> list[Candidate]:
        """Generate full-length candidates via Strategy C (CDS baseline + UTR append).

        Step 1: Delegate CDS generation and evaluation to MrnaCdsDesignWorkflow.
        Step 2: For each evaluated CDS, generate 3×3 UTR combinations.
        Total: up to 6 unique CDS × 9 UTR combos = 54 candidates.
        """
        # ── Step 1: Reuse CDS workflow for generation + evaluation ──
        cds_inp = MrnaCdsDesignInput(
            protein_sequence=inp.protein_sequence,
            design_tool=inp.design_tool,
            lambda_value=inp.lambda_value,
            model_type=inp.model_type,
            run_fold=inp.run_fold,
            run_gc=inp.run_gc,
        )
        cds_workflow = MrnaCdsDesignWorkflow(self.capabilities)
        cds_result = cds_workflow.run(cds_inp)

        cds_candidates = cds_result.all_candidates
        if not cds_candidates:
            _LOGGER.warning("cds_workflow produced no candidates")
            return []

        _LOGGER.info(
            "cds_workflow_completed candidates=%d best_total_score=%s",
            len(cds_candidates),
            cds_result.best_candidate.scores.get("total_score") if cds_result.best_candidate else None,
        )

        # ── Step 2: UTR combinations ──
        utr_presets = self._resolve_utr_presets(inp.utr_mode)
        full_candidates: list[Candidate] = []

        for cds_cand in cds_candidates:
            cds_seq = cds_cand.sequence
            if len(cds_seq) % 3 != 0:
                _LOGGER.warning(
                    "cds_length_not_multiple_of_3 source=%s len=%d",
                    cds_cand.source,
                    len(cds_seq),
                )
                continue

            # Reuse CDS evaluation results stored by MrnaCdsDesignWorkflow
            cds_metrics = cds_cand.metadata.get("metrics_bundle", {})
            cds_scores = cds_cand.scores

            for utr5_preset in utr_presets:
                utr5_seq = self._generate_utr("5utr", utr5_preset)
                if utr5_seq is None:
                    continue
                for utr3_preset in utr_presets:
                    utr3_seq = self._generate_utr("3utr", utr3_preset)
                    if utr3_seq is None:
                        continue

                    full_seq = utr5_seq + cds_seq + utr3_seq
                    candidate = Candidate(
                        sequence=full_seq,
                        sequence_type="mrna",
                        source=f"full_length:{cds_cand.source}:utr5_{utr5_preset}:utr3_{utr3_preset}",
                        metadata={
                            "utr5_sequence": utr5_seq,
                            "cds_sequence": cds_seq,
                            "utr3_sequence": utr3_seq,
                            "utr5_length": len(utr5_seq),
                            "utr3_length": len(utr3_seq),
                            "utr5_preset": utr5_preset,
                            "utr3_preset": utr3_preset,
                            "cds_length": len(cds_seq),
                            "cds_source": cds_cand.source,
                            "protein_sequence": inp.protein_sequence,
                            "cds_metrics": cds_metrics,
                            "cds_scores": cds_scores,
                        },
                    )
                    full_candidates.append(candidate)
                    _LOGGER.info(
                        "full_candidate_generated cds_source=%s utr5=%s utr3=%s total_len=%d",
                        cds_cand.source,
                        utr5_preset,
                        utr3_preset,
                        len(full_seq),
                    )

        # Deduplicate by full sequence
        seen: set[str] = set()
        unique: list[Candidate] = []
        for c in full_candidates:
            if c.sequence not in seen:
                seen.add(c.sequence)
                unique.append(c)

        _LOGGER.info(
            "full_candidates_generated total=%d unique=%d",
            len(full_candidates),
            len(unique),
        )
        return unique

    def _resolve_utr_presets(self, utr_mode: str) -> list[str]:
        if utr_mode == "all":
            return list(_UTR_PRESETS)
        if utr_mode in _UTR_PRESETS:
            return [utr_mode]
        return list(_UTR_PRESETS)

    def _generate_utr(self, utr_type: str, preset: str) -> Optional[str]:
        """Generate a single UTR sequence via GEMORNA.

        *utr_type* is ``5utr`` or ``3utr``.
        Returns the generated sequence string, or ``None`` on failure.
        """
        cap_name = f"design_{utr_type}_with_gemorna"
        if not self.capabilities.has(cap_name):
            _LOGGER.warning("utr_capability missing: %s", cap_name)
            return None

        try:
            cap = self.capabilities.get(cap_name)
            cap_result = cap.invoke(
                {"utr_length": preset},
                state=self._workflow_state,
            )
            if not cap_result.success:
                _LOGGER.warning(
                    "utr_design failed type=%s preset=%s error=%s",
                    utr_type,
                    preset,
                    cap_result.error,
                )
                return None

            seq = str(cap_result.output.get("generated_sequence", ""))
            if not seq:
                _LOGGER.warning("utr_design empty type=%s preset=%s", utr_type, preset)
                return None

            return seq
        except Exception as exc:
            _LOGGER.error("utr_design exception type=%s preset=%s err=%s", utr_type, preset, exc)
            return None

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Run incremental evaluation on a full-length candidate.

        CDS metrics are reused from MrnaCdsDesignWorkflow results stored in
        candidate metadata. Only full-length and UTR metrics are computed here.
        """
        seq = candidate.sequence
        utr5 = candidate.metadata.get("utr5_sequence", "")
        cds = candidate.metadata.get("cds_sequence", "")
        utr3 = candidate.metadata.get("utr3_sequence", "")

        # ── Reuse CDS metrics from MrnaCdsDesignWorkflow ──
        cds_metrics = candidate.metadata.get("cds_metrics", {})
        cds_mfe = cds_metrics.get("mfe_kcal_per_mol")
        cds_cai = cds_metrics.get("cai_score")
        cds_gc = cds_metrics.get("gc_content")

        # Save segments to workspace
        full_fp = save_sequence(seq, prefix="full_mrna")
        utr5_fp = save_sequence(utr5, prefix="utr5")
        utr3_fp = save_sequence(utr3, prefix="utr3")
        candidate.metadata["workspace_filepath"] = full_fp

        # ── 1. Full-length structure (ViennaRNA primary, LinearFold fallback) ──
        full_fold: Optional[dict[str, Any]] = None
        fold_tool: Optional[str] = None
        if self.capabilities.has("predict_rna_secondary_structure"):
            fold_res = self.capabilities.get("predict_rna_secondary_structure").invoke(
                {"filepath": full_fp}, state=self._workflow_state
            )
            if fold_res.success:
                full_fold = dict(fold_res.output)
                fold_tool = "ViennaRNA"
            else:
                _LOGGER.warning("full_fold vienna_failed error=%s", fold_res.error)
                if self.capabilities.has("predict_rna_secondary_structure_with_linearfold"):
                    lf_res = self.capabilities.get(
                        "predict_rna_secondary_structure_with_linearfold"
                    ).invoke({"filepath": full_fp}, state=self._workflow_state)
                    if lf_res.success:
                        full_fold = dict(lf_res.output)
                        fold_tool = "LinearFold"
                    else:
                        _LOGGER.warning("full_fold linearfold_failed error=%s", lf_res.error)

        # ── 2. 5'UTR specific — IRES potential ──
        utr5_metrics: dict[str, Any] = {}
        if len(utr5) >= 30 and self.capabilities.has("predict_putative_ires_with_iresfinder"):
            ires_res = self.capabilities.get("predict_putative_ires_with_iresfinder").invoke(
                {"filepath": utr5_fp}, state=self._workflow_state
            )
            if ires_res.success:
                max_score = _pick_float(ires_res.output, "max_score")
                if max_score is not None:
                    utr5_metrics["ires_max_score"] = max_score
            else:
                _LOGGER.warning("ires_failed error=%s", ires_res.error)

        # ── 3. Full-length stability ──
        overall_stability: Optional[float] = None
        if self.capabilities.has("predict_mrna_stability_with_rnastop"):
            rnastop_args: dict[str, Any] = {"filepath": full_fp}
            if full_fold:
                rnastop_args["structure"] = full_fold.get("structure", "")
            rnastop_res = self.capabilities.get("predict_mrna_stability_with_rnastop").invoke(
                rnastop_args, state=self._workflow_state
            )
            if rnastop_res.success:
                overall_stability = _pick_float(rnastop_res.output, "overall_stability")
            else:
                _LOGGER.warning("rnastop_failed error=%s", rnastop_res.error)

        # ── 4. 5'UTR folding ──
        utr5_fold: Optional[dict[str, Any]] = None
        if len(utr5) >= 10 and self.capabilities.has("predict_rna_secondary_structure"):
            utr5_fold_res = self.capabilities.get("predict_rna_secondary_structure").invoke(
                {"filepath": utr5_fp}, state=self._workflow_state
            )
            if utr5_fold_res.success:
                utr5_fold = dict(utr5_fold_res.output)
            else:
                _LOGGER.warning("utr5_fold_failed error=%s", utr5_fold_res.error)

        # ── 5. 5'UTR MRL prediction (GEMORNA) ──
        utr5_predicted_mrl: Optional[float] = None
        if self.capabilities.has("predict_5utr_mrl_with_gemorna"):
            mrl_res = self.capabilities.get("predict_5utr_mrl_with_gemorna").invoke(
                {"filepath": utr5_fp}, state=self._workflow_state
            )
            if mrl_res.success:
                utr5_predicted_mrl = _pick_float(mrl_res.output, "predicted_mrl")
            else:
                _LOGGER.warning("utr5_mrl_prediction_failed error=%s", mrl_res.error)

        # ── 6. 3'UTR stability prediction (GEMORNA) ──
        utr3_predicted_stability: Optional[float] = None
        if self.capabilities.has("predict_3utr_stability_with_gemorna"):
            stab_res = self.capabilities.get("predict_3utr_stability_with_gemorna").invoke(
                {"filepath": utr3_fp}, state=self._workflow_state
            )
            if stab_res.success:
                utr3_predicted_stability = _pick_float(stab_res.output, "predicted_stability")
            else:
                _LOGGER.warning("utr3_stability_prediction_failed error=%s", stab_res.error)

        metrics: dict[str, Any] = {
            "full_length_mfe": _pick_float(full_fold, "mfe_kcal_per_mol") if full_fold else None,
            "full_length_structure": full_fold.get("structure") if full_fold else None,
            "cds_cai": cds_cai,
            "cds_mfe": cds_mfe,
            "cds_gc": cds_gc,
            "cds_length": len(cds),
            "utr5_ires_potential": utr5_metrics.get("ires_max_score", 0),
            "utr5_length": len(utr5),
            "utr3_length": len(utr3),
            "utr5_mfe": _pick_float(utr5_fold, "mfe_kcal_per_mol") if utr5_fold else None,
            "overall_stability": overall_stability,
            "total_length": len(seq),
            "fold_tool": fold_tool or "unknown",
            "utr5_predicted_mrl": utr5_predicted_mrl,
            "utr3_predicted_stability": utr3_predicted_stability,
        }

        candidate.metadata["metrics_bundle"] = metrics
        candidate.metadata["fold_tool"] = fold_tool
        candidate.metadata["utr5_mfe"] = metrics.get("utr5_mfe")
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        return score_full_length_mrna_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return WorkflowResult(
                success=False,
                task_id="",
                summary="No candidates produced.",
                errors=["empty_candidate_list"],
            )

        def _module_rank(candidates: list[Candidate], score_key: str) -> dict[str, int]:
            with_score = [
                (c.scores[score_key], c.id)
                for c in candidates
                if score_key in c.scores and c.scores[score_key] is not None
            ]
            without_score = [
                c.id
                for c in candidates
                if score_key not in c.scores or c.scores[score_key] is None
            ]
            sorted_with = sorted(with_score, key=lambda x: x[0], reverse=True)
            rank_map: dict[str, int] = {}
            for rank, (_, cid) in enumerate(sorted_with, start=1):
                rank_map[cid] = rank
            penalty_rank = len(with_score) + 1 if with_score else 1
            for cid in without_score:
                rank_map[cid] = penalty_rank
            return rank_map

        cds_rank_map = _module_rank(candidates, "cds_component")
        utr5_rank_map = _module_rank(candidates, "utr5_mrl")
        utr3_rank_map = _module_rank(candidates, "utr3_stability")

        for c in candidates:
            total_rank = cds_rank_map[c.id] + utr5_rank_map[c.id] + utr3_rank_map[c.id]
            c.scores["total_rank"] = total_rank
            c.scores["cds_rank"] = cds_rank_map[c.id]
            c.scores["utr5_rank"] = utr5_rank_map[c.id]
            c.scores["utr3_rank"] = utr3_rank_map[c.id]
            # Backward-compatible total_score: negative rank so higher = better
            c.scores["total_score"] = -total_rank

        ranked = sorted(candidates, key=lambda c: c.scores["total_rank"])
        for i, c in enumerate(ranked, start=1):
            c.rank = i

        best = ranked[0] if ranked else None

        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            line_parts = [
                f"#{i}",
                f"source={c.source}",
                f"total_len={mb.get('total_length')}nt",
                f"utr5={mb.get('utr5_length')}nt({c.metadata.get('utr5_preset', '?')})",
                f"utr3={mb.get('utr3_length')}nt({c.metadata.get('utr3_preset', '?')})",
                f"cds_source={c.metadata.get('cds_source', '?')}",
                f"GC={mb.get('cds_gc'):.3f}" if mb.get("cds_gc") is not None else "GC=N/A",
                f"fullMFE={mb.get('full_length_mfe'):.2f}({mb.get('fold_tool', '?')})"
                if mb.get("full_length_mfe") is not None
                else "fullMFE=N/A",
                f"utr5IRES={mb.get('utr5_ires_potential'):.3f}"
                if mb.get("utr5_ires_potential") is not None
                else "utr5IRES=N/A",
                f"utr5MRL={mb.get('utr5_predicted_mrl'):.2f}"
                if mb.get("utr5_predicted_mrl") is not None
                else "utr5MRL=N/A",
                f"utr3Stab={mb.get('utr3_predicted_stability'):.4f}"
                if mb.get("utr3_predicted_stability") is not None
                else "utr3Stab=N/A",
                f"RNASTOP={mb.get('overall_stability'):.4f}"
                if mb.get("overall_stability") is not None
                else "RNASTOP=N/A",
                f"CAI={mb.get('cds_cai'):.4f}" if mb.get("cds_cai") is not None else "CAI=N/A",
                f"cdsRank={scores.get('cds_rank')} utr5Rank={scores.get('utr5_rank')} utr3Rank={scores.get('utr3_rank')}",
                f"total_rank={scores.get('total_rank')}",
            ]
            detail_lines.append(" | ".join(line_parts))

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_total_rank={best.scores.get('total_rank') if best else None}",
            "---",
            *detail_lines,
        ]
        return WorkflowResult(
            success=True,
            task_id=f"full_mrna_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )


class FullLengthMrnaCritic(Critic):
    """Critic for full-length mRNA design.

    Only filters on 5'UTR IRES potential.  IRESfinder outputs a probability
    in [0, 1]; the default decision threshold is 0.5.  For standard mRNA
    (cap-dependent translation) a putative IRES in the 5'UTR is undesirable
    because it can interfere with canonical ribosome loading.

    Retry is triggered **only** when the number of candidates that survive the
    IRES filter (≤ threshold) drops below ``MIN_GOOD_CANDIDATES``.
    """

    IRES_THRESHOLD: float = 0.5
    MIN_GOOD_CANDIDATES: int = 5

    def should_retry(self, workflow_result: WorkflowResult, state: dict[str, Any]) -> bool:
        all_candidates = workflow_result.all_candidates
        if not all_candidates:
            return False

        # Count candidates that are explicitly bad (IRES > threshold)
        bad_count = 0
        for c in all_candidates:
            mb = c.metadata.get("metrics_bundle", {})
            ires = mb.get("utr5_ires_potential")
            if ires is not None and float(ires) > self.IRES_THRESHOLD:
                bad_count += 1

        remaining = len(all_candidates) - bad_count
        if remaining < self.MIN_GOOD_CANDIDATES:
            state.setdefault("next_constraints", {})
            state["next_constraints"]["avoid_ires_in_5utr"] = True
            return True

        return False


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
