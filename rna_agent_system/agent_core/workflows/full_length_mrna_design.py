"""Full-length mRNA design workflow — 5'UTR + CDS + 3'UTR (Layer 2).

Protein sequence → CDS candidates (LinearDesign λ=[0,1,4,10] + RNARL + GEMORNA)
→ UTR combinations (GEMORNA short/medium/long) → segmented evaluation →
full-length scoring → ranking → WorkflowResult.

Strategy: Only Strategy C is implemented (CDS-only baseline + UTR append).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence, save_text_file
from agent_core.planning.base import Critic
from agent_core.workflow_models import Candidate, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
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
    target_gc_mid: Optional[float] = Field(default=None, description="Override GC band mid-point for scoring.")


def score_full_length_mrna_candidate(
    metrics: dict[str, Any],
) -> dict[str, float]:
    """Score a full-length mRNA candidate.

    Formula (v0.2.0):
        total_score = cds_combined_score / cds_length + utr5_mrl + utr3_stability

    Where:
    - cds_combined_score: the classic CDS-only score (-mfe + codon_count * log(CAI))
    - cds_length: nucleotide length of the CDS segment
    - utr5_mrl: GEMORNA predicted Mean Ribosomal Load for 5'UTR
    - utr3_stability: GEMORNA predicted stability score for 3'UTR

    All raw metrics from the evaluate phase are preserved in the returned dict
    for display purposes, but only the three terms above affect ranking.
    """

    cds_length = int(metrics.get("cds_length", 0))

    # CDS component: classic combined score (-mfe + codon_count * log(CAI))
    cds_bundle = {
        "mfe_kcal_per_mol": metrics.get("cds_mfe"),
        "cai_score": metrics.get("cds_cai"),
        "sequence_length": cds_length,
    }
    cds_scores = score_mrna_candidate(cds_bundle)
    cds_combined_score = cds_scores.get("combined_score", 0.0)
    cds_component = cds_combined_score / cds_length if cds_length > 0 else 0.0

    # 5'UTR MRL component
    utr5_mrl = metrics.get("utr5_predicted_mrl")
    utr5_component = float(utr5_mrl) if utr5_mrl is not None else 0.0

    # 3'UTR stability component
    utr3_stability = metrics.get("utr3_predicted_stability")
    utr3_component = float(utr3_stability) if utr3_stability is not None else 0.0

    total_score = cds_component + utr5_component + utr3_component

    return {
        "total_score": float(total_score),
        "cds_component": float(cds_component),
        "cds_combined_score": float(cds_combined_score),
        "utr5_mrl": float(utr5_component),
        "utr3_stability": float(utr3_component),
    }


class FullLengthMrnaDesignWorkflow(
    BaseDomainWorkflow[FullLengthMrnaDesignInput, WorkflowResult]
):
    """Full-length mRNA design: protein → CDS + UTR combinations → evaluate → score → rank."""

    name = "full_length_mrna_design"
    description = (
        "Design full-length mRNA (5'UTR + CDS + 3'UTR) from protein sequence, "
        "evaluate segmented metrics, score, and rank candidates."
    )
    required_capabilities = [
        "design_mrna_cds_with_lineardesign",
        "design_mrna_cds_with_rnarl",
        "design_mrna_cds_with_gemorna",
        "design_5utr_with_gemorna",
        "design_3utr_with_gemorna",
        "predict_5utr_mrl_with_gemorna",
        "predict_3utr_stability_with_gemorna",
        "predict_rna_secondary_structure",
        "predict_rna_secondary_structure_with_linearfold",
        "compute_rna_sequence_gc_content",
        "compute_cai_for_cds_sequence",
        "analyze_cds_codon_metrics_with_codonw_slim",
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

        Step 1: Generate CDS candidates (same as MrnaCdsDesignWorkflow).
        Step 2: For each CDS, generate 3×3 UTR combinations (short/medium/long).
        Total: up to 6 unique CDS × 9 UTR combos = 54 candidates.
        """
        protein_fp = save_sequence(inp.protein_sequence, prefix="protein")
        _LOGGER.info(
            "full_length_mrna_design protein_saved filepath=%s len_aa=%d",
            protein_fp,
            len(inp.protein_sequence),
        )

        # ── Step 1: CDS candidates ──
        cds_candidates = self._generate_cds_candidates(inp, protein_fp)
        if not cds_candidates:
            _LOGGER.warning("no_cds_candidates_generated")
            return []

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
                            "protein_filepath": protein_fp,
                            "target_gc_mid": getattr(inp, "target_gc_mid", None),
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

    def _generate_cds_candidates(
        self, inp: FullLengthMrnaDesignInput, protein_fp: str
    ) -> list[Candidate]:
        """Produce CDS candidates using the same logic as MrnaCdsDesignWorkflow."""

        design_configs: list[tuple[str, dict[str, Any]]] = []

        if inp.design_tool in ("all", "lineardesign"):
            for lam in (0.0, 1.0, 4.0, 10.0):
                design_configs.append(("lineardesign", {"lambda_value": lam}))

        if inp.design_tool in ("all", "rnarl"):
            design_configs.append(("rnarl", {"model_type": inp.model_type}))

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
                        "cds_design failed tool=%s error=%s", tool_name, cap_result.error
                    )
                    continue

                seq = str(cap_result.output.get("generated_sequence", ""))
                if not seq:
                    _LOGGER.warning("cds_design empty tool=%s", tool_name)
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
                    },
                )
                candidates.append(candidate)
                _LOGGER.info(
                    "cds_candidate_generated tool=%s params=%s len_nt=%d",
                    tool_name,
                    extra_args,
                    len(seq),
                )
            except Exception as exc:
                _LOGGER.error("cds_design exception tool=%s err=%s", tool_name, exc)

        # Deduplicate by sequence
        seen: set[str] = set()
        unique: list[Candidate] = []
        for c in candidates:
            if c.sequence not in seen:
                seen.add(c.sequence)
                unique.append(c)

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
        """Run segmented evaluation on a full-length candidate."""
        seq = candidate.sequence
        utr5 = candidate.metadata.get("utr5_sequence", "")
        cds = candidate.metadata.get("cds_sequence", "")
        utr3 = candidate.metadata.get("utr3_sequence", "")

        # Save segments to workspace
        full_fp = save_sequence(seq, prefix="full_mrna")
        cds_fp = save_sequence(cds, prefix="cds")
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

        # ── 2. CDS metrics ──
        cds_metrics: dict[str, Any] = {}
        if self.capabilities.has("analyze_cds_codon_metrics_with_codonw_slim"):
            cw_res = self.capabilities.get("analyze_cds_codon_metrics_with_codonw_slim").invoke(
                {"filepath": cds_fp}, state=self._workflow_state
            )
            if cw_res.success:
                cds_metrics = dict(cw_res.output)
            else:
                _LOGGER.warning("codonw_failed error=%s", cw_res.error)

        gc_content: Optional[float] = None
        if self.capabilities.has("compute_rna_sequence_gc_content"):
            gc_res = self.capabilities.get("compute_rna_sequence_gc_content").invoke(
                {"filepath": full_fp}, state=self._workflow_state
            )
            if gc_res.success:
                gc_content = _pick_float(gc_res.output, "gc_content")
            else:
                _LOGGER.warning("gc_failed error=%s", gc_res.error)

        cai_score: Optional[float] = None
        if self.capabilities.has("compute_cai_for_cds_sequence"):
            cai_res = self.capabilities.get("compute_cai_for_cds_sequence").invoke(
                {"filepath": cds_fp, "species": "Homo sapiens"},
                state=self._workflow_state,
            )
            if cai_res.success:
                cai_score = _pick_float(cai_res.output, "cai_score")
            else:
                _LOGGER.warning("cai_failed error=%s", cai_res.error)

        # Use CodonW CAI if available, otherwise fallback to dedicated CAI tool
        effective_cai = cds_metrics.get("cai_score") or cai_score

        # ── 3. 5'UTR specific — IRES potential ──
        utr5_metrics: dict[str, Any] = {}
        if len(utr5) >= 30 and self.capabilities.has("predict_putative_ires_with_iresfinder"):
            ires_res = self.capabilities.get("predict_putative_ires_with_iresfinder").invoke(
                {"filepath": utr5_fp}, state=self._workflow_state
            )
            if ires_res.success:
                # IRESfinder returns max_score directly; scores list may also exist
                max_score = _pick_float(ires_res.output, "max_score")
                if max_score is not None:
                    utr5_metrics["ires_max_score"] = max_score
            else:
                _LOGGER.warning("ires_failed error=%s", ires_res.error)

        # ── 4. Full-length stability ──
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

        # ── 5. 5'UTR folding ──
        utr5_fold: Optional[dict[str, Any]] = None
        if len(utr5) >= 10 and self.capabilities.has("predict_rna_secondary_structure"):
            utr5_fold_res = self.capabilities.get("predict_rna_secondary_structure").invoke(
                {"filepath": utr5_fp}, state=self._workflow_state
            )
            if utr5_fold_res.success:
                utr5_fold = dict(utr5_fold_res.output)
            else:
                _LOGGER.warning("utr5_fold_failed error=%s", utr5_fold_res.error)

        # ── 6. 5'UTR MRL prediction (GEMORNA) ──
        utr5_predicted_mrl: Optional[float] = None
        if self.capabilities.has("predict_5utr_mrl_with_gemorna"):
            mrl_res = self.capabilities.get("predict_5utr_mrl_with_gemorna").invoke(
                {"filepath": utr5_fp}, state=self._workflow_state
            )
            if mrl_res.success:
                utr5_predicted_mrl = _pick_float(mrl_res.output, "predicted_mrl")
            else:
                _LOGGER.warning("utr5_mrl_prediction_failed error=%s", mrl_res.error)

        # ── 7. 3'UTR stability prediction (GEMORNA) ──
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
            "cds_cai": effective_cai,
            "cds_mfe": _pick_float(cds_metrics, "mfe_kcal_per_mol") if cds_metrics else None,
            "cds_gc": gc_content,
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

        ranked = sort_candidates_by_score(
            candidates, score_key="total_score", descending=True
        )
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
            task_id=f"full_mrna_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )


class FullLengthMrnaCritic(Critic):
    """Critic for full-length mRNA design.

    Currently returns ``False`` (no retry) to avoid unnecessary compute in the
    initial rollout. The retry logic is structurally complete and can be enabled
    by registering the critic in ``WORKFLOW_CRITIC_PAIRS``.
    """

    def should_retry(self, workflow_result: WorkflowResult, state: dict[str, Any]) -> bool:
        best = workflow_result.best_candidate
        if best is None:
            return False

        mb = best.metadata.get("metrics_bundle", {})

        # Failure mode 1: full-length structure too unstable
        full_mfe = mb.get("full_length_mfe")
        if full_mfe is not None and full_mfe > -10:
            state.setdefault("next_constraints", {})
            state["next_constraints"]["avoid_utr_cds_interaction"] = True
            return True

        # Failure mode 2: 5'UTR overly folded (blocks ribosome access)
        utr5_mfe = best.metadata.get("utr5_mfe", 0)
        if utr5_mfe is not None and utr5_mfe < -15:
            state.setdefault("next_constraints", {})
            state["next_constraints"]["utr5_max_stability"] = -10
            return True

        # Failure mode 3: CDS quality insufficient
        cds_cai = mb.get("cds_cai")
        if cds_cai is not None and cds_cai < 0.5:
            state.setdefault("next_constraints", {})
            state["next_constraints"]["prioritize_cai"] = True
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
