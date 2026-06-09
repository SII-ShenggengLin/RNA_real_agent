"""Full-length mRNA design workflow — 5'UTR + CDS + 3'UTR (Layer 2).

Protein sequence → CDS candidates via MrnaCdsDesignWorkflow (generate + evaluate)
→ UTR combinations (GEMORNA short/medium/long) → full-length / UTR incremental
evaluation → full-length scoring → ranking → WorkflowResult.

Strategy: Only Strategy C is implemented (CDS-only baseline + UTR append).
Architecture: Full-length workflow reuses MrnaCdsDesignWorkflow for CDS
generation and evaluation; only full-length and UTR metrics are computed here.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  FullLengthMrnaDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 full_length_mrna_design workflow 的权威实现。任何字段增删、         ║
║  函数签名变动、返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试： ║
║                                                                               ║
║    - agent_core/workflows/full_length_mrna_design.py  ← 本文件               ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/workflows/mrna_cds_design.py                                  ║
║    - agent_core/sequence_utils.py                                     ║
║    - agent_core/workflows/registry.py                                         ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/capabilities/writebacks.py                                    ║
║    - agent_core/capabilities/base.py                                          ║
║    - agent_core/planning/base.py                                              ║
║    - agent_core/planning/llm_critic.py                                        ║
║    - agent_core/tool_specs.py                                                 ║
║    - tests/test_full_length_mrna_design.py                                    ║
║    - tests/test_full_length_mrna_design_layer3.py                             ║
║    - tests/test_full_length_mrna_design_comprehensive.py                      ║
║    - tests/test_full_length_mrna_e2e_live.py                                  ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.planning.llm_critic import BaseLLMCritic, CriticConfig
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.base import BaseDomainWorkflow, SubWorkflowEvaluator
from agent_core.workflows.coordinator import (
    FullLengthCoordinator,
    CoordinationRound,
    Issue,
)
from agent_core.workflows.evaluators import (
    IRESEvaluator,
    JunctionEvaluator,
    RNASTOPEvaluator,
    SecondaryStructureEvaluator,
    UContentEvaluator,
    UTR3StabilityEvaluator,
    UTR5MrlEvaluator,
)
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput, MrnaCdsDesignWorkflow
from agent_core.workflows.scoring import FullLengthBMCScoringFunction
from agent_core.sequence_utils import score_mrna_candidate

_LOGGER = logging.getLogger("agent_core.workflows.full_length_mrna_design")

# UTR length presets exposed by GEMORNA
_UTR_PRESETS: list[str] = ["short", "medium", "long"]


class FullLengthMrnaDesignInput(BaseModel):
    """Input for the full-length mRNA design workflow."""

    model_config = ConfigDict(extra="forbid")

    protein_sequence: str = Field(..., description="Amino-acid string (uppercase, 1-letter codes).")
    design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"] = "all"
    lambda_value: Optional[float] = Field(
        default=None,
        description="LinearDesign MFE/CAI balance (0-20). Required when design_tool='lineardesign'; ignored otherwise.",
    )
    model_type: str = Field(default="Homo sapiens mRNA", description="RNARL model type.")
    cai_species: str = Field(
        default="Homo sapiens",
        description="Species for CAI computation. Built-in: human, mouse, rat, fly, worm, zebrafish, arabidopsis, yeast, ecoli, bsubtilis, cho.",
    )
    utr_mode: Literal["short", "medium", "long", "all"] = "all"
    run_fold: bool = Field(default=True)
    run_gc: bool = Field(default=True)

    @field_validator("lambda_value")
    @classmethod
    def _require_lambda_for_lineardesign(
        cls, v: Optional[float], info: Any
    ) -> Optional[float]:
        design_tool = info.data.get("design_tool")
        if design_tool == "lineardesign" and v is None:
            raise ValueError("lambda_value is required when design_tool='lineardesign'")
        return v


def score_full_length_mrna_candidate(
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Return per-module raw scores for Borda-count ranking in rank_and_format.

    Args:
        metrics: Raw metrics dict produced by ``evaluate()``. Expected keys:
            - ``cds_cai`` (float | None): CAI score of the CDS.
            - ``cds_mfe`` (float | None): MFE (kcal/mol) of the CDS.
            - ``cds_length`` (int): CDS length in nucleotides.
            - ``utr5_predicted_mrl`` (float | None): Predicted mean ribosomal load of 5'UTR.
            - ``utr3_predicted_stability`` (float | None): Predicted stability of 3'UTR.

    Returns:
        dict[str, float | None]: Score components with keys:
            - ``cds_component``: ``combined_score / cds_length`` (normalized CDS score),
              or ``None`` when ``cds_length`` is 0 or CDS metrics are missing.
            - ``cds_combined_score``: Classic ``-mfe + codon_count * log(CAI)`` score.
            - ``utr5_mrl``: Raw predicted MRL value, or ``None`` if absent.
            - ``utr3_stability``: Raw predicted stability value, or ``None`` if absent.
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
    input_model = FullLengthMrnaDesignInput
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
        "compute_rna_sequence_u_content",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._cds_state_writeback: dict[str, Any] = {}
        self._cds_evaluator = SubWorkflowEvaluator(
            lambda: self._create_cds_workflow(),
            sequence_key="cds_sequence",
            key_map={
                "mfe_kcal_per_mol": "cds_mfe",
                "cai_score": "cds_cai",
                "gc_content": "cds_gc",
                "sequence_length": "cds_length",
                "u_fraction": "cds_u_fraction",
            },
        )
        self._u_content_evaluator = UContentEvaluator(self.capabilities)
        self._full_fold_evaluator = SecondaryStructureEvaluator(
            self.capabilities, run_fold=True
        )
        self._ires_evaluator = IRESEvaluator(self.capabilities)
        self._rnastop_evaluator = RNASTOPEvaluator(self.capabilities)
        self._utr5_fold_evaluator = SecondaryStructureEvaluator(
            self.capabilities, run_fold=True
        )
        self._utr5_mrl_evaluator = UTR5MrlEvaluator(self.capabilities)
        self._utr3_stability_evaluator = UTR3StabilityEvaluator(self.capabilities)
        self._junction_evaluator = JunctionEvaluator(self.capabilities)

    def _create_cds_workflow(self) -> MrnaCdsDesignWorkflow:
        """Factory for the CDS sub-workflow used by SubWorkflowEvaluator."""
        wf = MrnaCdsDesignWorkflow(self.capabilities)
        inp = self._workflow_state.get("_full_length_input")
        if inp:
            wf._run_fold = inp.run_fold
            wf._run_gc = inp.run_gc
        return wf

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        inp: FullLengthMrnaDesignInput | dict[str, Any],
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """BMC-enabled run: generate → evaluate → rank → bounded iterative refinement.

        Phase 1: Generate initial candidates (5'UTR + CDS + 3'UTR combinations).
        Phase 2: Evaluate and rank (classic Borda count + new junction metrics).
        Phase 3: Coordinator diagnoses best candidate; if issues found, broadcast
        structured feedback to affected modules, regenerate, and re-evaluate.
        Hard bounds: max 3 rounds, no improvement → early stop.
        """
        if isinstance(inp, dict):
            inp = FullLengthMrnaDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._cds_state_writeback = {}  # reset per run
        self._workflow_state["_full_length_input"] = inp
        self._bmc_trace: list[CoordinationRound] = []

        # ── Phase 1 & 2: Standard generate → evaluate → score → rank ──
        result = super().run(inp, progress_callback=progress_callback)

        if not result.success or not result.all_candidates:
            merged_wb = dict(self._workflow_state)
            for key, value in self._cds_state_writeback.items():
                if isinstance(value, dict) and isinstance(merged_wb.get(key), dict):
                    merged_wb[key].update(value)
                else:
                    merged_wb[key] = value
            merged_wb["_workflow_params"] = inp.model_dump()
            result._state_writeback = merged_wb  # type: ignore[attr-defined]
            return result

        # ── Phase 3: Bounded Multi-Module Coordination ──
        coordinator = FullLengthCoordinator()
        max_rounds = 1
        improvement_threshold = 1.0

        best = result.best_candidate
        best_score = (
            best.scores.get("total_score", float("-inf")) if best else float("-inf")
        )

        for round_num in range(1, max_rounds + 1):
            if best is None:
                break

            metrics = best.metadata.get("metrics_bundle", {})
            issues = coordinator.diagnose(metrics)

            if not issues:
                _LOGGER.info("bmc_converged_no_issues round=%d", round_num)
                break

            feedback = coordinator.broadcast_feedback(issues)
            affected_modules = list(feedback.keys())

            _LOGGER.info(
                "bmc_round_start round=%d issues=%d modules=%s",
                round_num,
                len(issues),
                affected_modules,
            )

                # Generate new candidates with adjusted parameters
            t0 = time.perf_counter()
            new_candidates = self._regenerate_modules(
                inp, feedback, best, result.all_candidates, issues
            )

            if not new_candidates:
                _LOGGER.info("bmc_no_new_candidates round=%d", round_num)
                break

            # Evaluate new candidates
            for i, candidate in enumerate(new_candidates):
                _LOGGER.info(
                    "bmc_evaluating_new idx=%d total=%d round=%d",
                    i + 1,
                    len(new_candidates),
                    round_num,
                )
                metrics = self.evaluate(candidate)
                candidate.scores = self.score(metrics)
                candidate.status = "evaluated"
                if progress_callback:
                    progress_callback({
                        "event": "bmc_evaluate_progress",
                        "round": round_num,
                        "current": i + 1,
                        "total": len(new_candidates),
                        "candidate_id": candidate.id,
                        "workflow": self.name,
                    })

            # Merge and re-rank
            all_candidates = result.all_candidates + new_candidates
            result = self.rank_and_format(all_candidates)

            new_best = result.best_candidate
            new_score = (
                new_best.scores.get("total_score", float("-inf"))
                if new_best
                else float("-inf")
            )

            # Record round trace
            time_elapsed_ms = (time.perf_counter() - t0) * 1000.0
            round_trace = CoordinationRound(
                round_num=round_num,
                best_candidate_id=new_best.id if new_best else "",
                best_total_score=new_score,
                issues_found=issues,
                feedback_dispatched=feedback,
                modules_reinvoked=affected_modules,
                time_elapsed_ms=time_elapsed_ms,
            )
            self._bmc_trace.append(round_trace)

            should_stop, reason = coordinator.has_converged(
                new_score,
                best_score,
                round_num,
                max_rounds=max_rounds,
                improvement_threshold=improvement_threshold,
            )

            _LOGGER.info(
                "bmc_round_complete round=%d old_score=%.3f new_score=%.3f reason=%s",
                round_num,
                best_score,
                new_score,
                reason,
            )

            best = new_best
            best_score = new_score

            if should_stop:
                break

        # Merge state writeback
        merged_wb = dict(self._workflow_state)
        for key, value in self._cds_state_writeback.items():
            if isinstance(value, dict) and isinstance(merged_wb.get(key), dict):
                merged_wb[key].update(value)
            else:
                merged_wb[key] = value
        merged_wb["_workflow_params"] = inp.model_dump()
        merged_wb["_bmc_trace"] = [r.to_dict() for r in self._bmc_trace]
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: FullLengthMrnaDesignInput) -> list[Candidate]:
        """Generate full-length candidates via Strategy C (CDS baseline + UTR append).

        Step 1: Delegate CDS generation to MrnaCdsDesignWorkflow (evaluate via
        SubWorkflowEvaluator in ``evaluate()``).
        Step 2: For each CDS, generate 3×3 UTR combinations.
        Total: up to 6 unique CDS × 9 UTR combos = 54 candidates.
        """
        # ── Step 1: Generate CDS candidates (evaluation deferred to evaluate()) ──
        cds_inp = MrnaCdsDesignInput(
            protein_sequence=inp.protein_sequence,
            design_tool=inp.design_tool,
            lambda_value=inp.lambda_value,
            model_type=inp.model_type,
            cai_species=inp.cai_species,
            run_fold=inp.run_fold,
            run_gc=inp.run_gc,
        )
        cds_workflow = MrnaCdsDesignWorkflow(self.capabilities)
        cds_candidates = cds_workflow.generate_candidates(cds_inp)
        # Capture design-phase state writeback from the sub-workflow
        self._cds_state_writeback = dict(cds_workflow._workflow_state)

        if not cds_candidates:
            _LOGGER.warning("cds_workflow produced no candidates")
            return []

        _LOGGER.info(
            "cds_workflow_generated candidates=%d",
            len(cds_candidates),
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

        CDS metrics are evaluated via :class:`SubWorkflowEvaluator` wrapping
        :class:`MrnaCdsDesignWorkflow`. Full-length and UTR metrics are
        evaluated via reusable evaluator components.
        """
        seq = candidate.sequence
        utr5 = candidate.metadata.get("utr5_sequence", "")
        cds = candidate.metadata.get("cds_sequence", "")
        utr3 = candidate.metadata.get("utr3_sequence", "")

        context: dict[str, Any] = {"workflow_state": self._workflow_state}

        # ── CDS metrics via SubWorkflowEvaluator (cached by sequence) ──
        cds_metrics = self._cds_evaluator.evaluate(candidate, context)

        # Save full-length sequence to workspace
        full_fp = save_sequence(seq, prefix="full_mrna")
        candidate.metadata["workspace_filepath"] = full_fp

        # ── Full-length fold (run on candidate so structure is in metadata) ──
        full_fold = self._full_fold_evaluator.evaluate(candidate, context)

        # ── Junction evaluation (NEW for BMC) ──
        junction = self._junction_evaluator.evaluate(candidate, context)

        # ── Full-length U content ──
        full_u_content = self._u_content_evaluator.evaluate(candidate, context)

        # NOTE: RNASTOP, IRES, and 5'UTR fold evaluators are skipped in
        # benchmark mode to avoid timeout on large candidate sets.
        rnastop: dict[str, Any] = {}
        ires: dict[str, Any] = {}
        utr5_fold: dict[str, Any] = {}

        # 5'UTR MRL and 3'UTR stability evaluation (GEMORNA)
        utr5_mrl = self._utr5_mrl_evaluator.evaluate(candidate, context)
        utr3_stab = self._utr3_stability_evaluator.evaluate(candidate, context)

        # Compute length-normalized MFE and paired fraction from structure
        full_mfe = full_fold.get("mfe_kcal_per_mol")
        total_len = len(seq)
        mfe_per_nt = (float(full_mfe) / total_len) if full_mfe is not None and total_len > 0 else None

        structure = full_fold.get("structure", "")
        paired_count = structure.count("(") + structure.count(")") if structure else 0
        paired_fraction = (paired_count / len(structure)) if structure else None

        metrics: dict[str, Any] = {
            "full_length_mfe": full_mfe,
            "full_length_structure": structure,
            "full_mfe_per_nt": mfe_per_nt,
            "full_paired_fraction": paired_fraction,
            "cds_cai": cds_metrics.get("cds_cai"),
            "cds_mfe": cds_metrics.get("cds_mfe"),
            "cds_gc": cds_metrics.get("cds_gc"),
            "cds_u_fraction": cds_metrics.get("cds_u_fraction"),
            "cds_length": cds_metrics.get("cds_length", len(cds)),
            "utr5_ires_potential": ires.get("utr5_ires_potential", 0),
            "utr5_length": len(utr5),
            "utr3_length": len(utr3),
            "utr5_mfe": utr5_fold.get("mfe_kcal_per_mol"),
            "overall_stability": rnastop.get("rnastop_overall_stability"),
            "total_length": total_len,
            "full_u_fraction": full_u_content.get("u_fraction"),
            "fold_tool": full_fold.get("fold_tool", "unknown"),
            "utr5_predicted_mrl": utr5_mrl.get("utr5_predicted_mrl"),
            "utr3_predicted_stability": utr3_stab.get("utr3_predicted_stability"),
            # Junction metrics (NEW)
            "junction_5utr_cds_mfe": junction.get("junction_5utr_cds_mfe"),
            "junction_5utr_cds_structure": junction.get("junction_5utr_cds_structure"),
            "junction_5utr_cds_gc_diff": junction.get("junction_5utr_cds_gc_diff"),
            "junction_5utr_cds_left_gc": junction.get("junction_5utr_cds_left_gc"),
            "junction_5utr_cds_right_gc": junction.get("junction_5utr_cds_right_gc"),
            "junction_cds_3utr_mfe": junction.get("junction_cds_3utr_mfe"),
            "junction_cds_3utr_structure": junction.get("junction_cds_3utr_structure"),
            "junction_cds_3utr_gc_diff": junction.get("junction_cds_3utr_gc_diff"),
            "junction_cds_3utr_left_gc": junction.get("junction_cds_3utr_left_gc"),
            "junction_cds_3utr_right_gc": junction.get("junction_cds_3utr_right_gc"),
        }

        candidate.metadata["metrics_bundle"] = metrics
        candidate.metadata["fold_tool"] = full_fold.get("fold_tool")
        candidate.metadata["utr5_mfe"] = metrics.get("utr5_mfe")
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, Any]:
        # Use junction-aware BMC scoring when junction metrics are present;
        # fall back to classic Borda-count scoring otherwise.
        has_junction = (
            "junction_5utr_cds_mfe" in metrics
            or "junction_cds_3utr_mfe" in metrics
        )
        if has_junction:
            return FullLengthBMCScoringFunction().score(metrics)
        return score_full_length_mrna_candidate(metrics)

    # ─────────────────────────────────────────────────────────────────────────
    # BMC module regeneration helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _adjust_input_from_feedback(
        self,
        inp: FullLengthMrnaDesignInput,
        feedback: dict[str, Any],
    ) -> FullLengthMrnaDesignInput:
        """Build a parameter-adjusted input from coordinator feedback.

        Only CDS-level adjustments are actionable in the current architecture;
        UTR adjustments are realized via preset switching in
        ``_regenerate_modules()``.
        """
        # Start from current input values
        new_lambda = inp.lambda_value
        new_design_tool = inp.design_tool
        lambda_adjusted = False

        cds_feedback = feedback.get("CDS")
        if cds_feedback is not None:
            for adj in cds_feedback.adjustments:
                if adj.param == "lambda_value":
                    lambda_adjusted = True
                    if new_lambda is not None:
                        new_lambda = max(0.0, min(20.0, new_lambda + adj.delta))
                    else:
                        # If lambda was not set, start from a heuristic default
                        new_lambda = max(0.0, min(20.0, 2.0 + adj.delta))

        # If lambda is being adjusted but design_tool is "all", the adjustment
        # would be ignored because generate_candidates uses a fixed lambda grid
        # for "all". Switch to "lineardesign" so the lambda change takes effect.
        if lambda_adjusted and new_design_tool == "all":
            new_design_tool = "lineardesign"

        # If no actionable CDS adjustments but UTR is affected, we still
        # return a copy so that _regenerate_modules can try different presets.
        return FullLengthMrnaDesignInput(
            protein_sequence=inp.protein_sequence,
            design_tool=new_design_tool,
            lambda_value=new_lambda,
            model_type=inp.model_type,
            cai_species=inp.cai_species,
            utr_mode=inp.utr_mode,
            run_fold=inp.run_fold,
            run_gc=inp.run_gc,
        )

    def _regenerate_modules(
        self,
        inp: FullLengthMrnaDesignInput,
        feedback: dict[str, Any],
        current_best: Candidate,
        existing_candidates: list[Candidate],
        issues: list[Issue],
    ) -> list[Candidate]:
        """Generate new candidates by adjusting parameters per coordinator feedback.

        Strategy:
        1. Adjust CDS parameters (lambda, tool) based on CDS feedback.
        2. Generate junction-shuffled CDS variants (synonymous codon substitution
           at N- or C-terminus) to directly alter local junction structure.
        3. If UTR feedback exists, explore alternative UTR presets to change
           the junction sequence context.
        4. Combine all CDS candidates (λ-adjusted + shuffled) with UTR presets.
        5. Deduplicate against existing candidates.
        """
        adjusted_inp = self._adjust_input_from_feedback(inp, feedback)

        # Determine whether CDS parameters actually changed.
        # If only junction issues exist (no global MFE issues), coordinator
        # no longer emits lambda adjustments, so re-generating CDS with the
        # same parameters is wasteful.  In that case we reuse the current best
        # CDS and rely on UTR exploration + junction codon shuffling.
        cds_params_unchanged = (
            adjusted_inp.design_tool == inp.design_tool
            and adjusted_inp.lambda_value == inp.lambda_value
        )

        if cds_params_unchanged:
            # Reuse the current best CDS; local junction fixes come from
            # UTR exploration + codon shuffling below.
            best_cds_seq = current_best.metadata.get("cds_sequence", "")
            cds_candidates = [
                Candidate(
                    sequence=best_cds_seq,
                    sequence_type="cds",
                    source="current_best_reused",
                    metadata={"cds_sequence": best_cds_seq},
                )
            ] if best_cds_seq else []
            _LOGGER.info("bmc_reusing_best_cds no_lambda_change")
        else:
            cds_inp = MrnaCdsDesignInput(
                protein_sequence=adjusted_inp.protein_sequence,
                design_tool=adjusted_inp.design_tool,
                lambda_value=adjusted_inp.lambda_value,
                model_type=adjusted_inp.model_type,
                cai_species=adjusted_inp.cai_species,
                run_fold=adjusted_inp.run_fold,
                run_gc=adjusted_inp.run_gc,
            )
            cds_workflow = MrnaCdsDesignWorkflow(self.capabilities)
            cds_candidates = cds_workflow.generate_candidates(cds_inp)

        # ── Junction-focused synonymous codon shuffling (NEW) ────────────────
        # Extract which junction end needs shuffling from diagnosed issues.
        shuffle_end: str | None = None
        for issue in issues:
            if issue.issue_type.startswith("JUNCTION_5UTR_CDS"):
                shuffle_end = "n_terminus"
            elif issue.issue_type.startswith("JUNCTION_CDS_3UTR"):
                shuffle_end = "c_terminus"

        shuffled_cds_variants: list[str] = []
        if (
            shuffle_end
            and current_best
            and self.capabilities.has("shuffle_cds_junction_codons")
        ):
            best_cds = current_best.metadata.get("cds_sequence", "")
            if best_cds:
                try:
                    cds_fp = save_sequence(best_cds, prefix=f"bmc_shuffle_{shuffle_end}")
                    cap = self.capabilities.get("shuffle_cds_junction_codons")
                    res = cap.invoke(
                        {
                            "filepath": cds_fp,
                            "junction_end": shuffle_end,
                            "codon_count": 6,
                            "num_variants": 4,
                            "species": adjusted_inp.cai_species or "Homo sapiens",
                        },
                        state=self._workflow_state,
                    )
                    if res.success and res.output:
                        variants = res.output.get("variants", [])
                        for v in variants:
                            seq = v.get("sequence", "")
                            if seq and seq != best_cds:
                                shuffled_cds_variants.append(seq)
                        _LOGGER.info(
                            "bmc_shuffled_cds end=%s variants=%d unique=%d",
                            shuffle_end,
                            len(variants),
                            len(shuffled_cds_variants),
                        )
                except Exception as exc:
                    _LOGGER.warning("bmc_shuffle_failed end=%s error=%s", shuffle_end, exc)

        # Merge λ-adjusted CDS candidates with shuffled variants.
        # Represent shuffled variants as lightweight pseudo-candidates.
        all_cds_seqs = list({c.sequence for c in cds_candidates})
        for shuffled_seq in shuffled_cds_variants:
            if shuffled_seq not in all_cds_seqs:
                all_cds_seqs.append(shuffled_seq)

        # Determine UTR presets: coordinator emits ``utr_preset_exploration``
        # markers for junction issues.  When present, force exploration of all
        # available presets to increase junction sequence diversity.
        utr_presets = self._resolve_utr_presets(adjusted_inp.utr_mode)
        explore_utr = False
        for mod in ("5UTR", "3UTR"):
            fb = feedback.get(mod)
            if fb and any(a.param == "utr_preset_exploration" for a in fb.adjustments):
                explore_utr = True
                break
        if explore_utr:
            utr_presets = list(_UTR_PRESETS)
        # Limit presets to avoid explosion during BMC
        if len(utr_presets) > 2:
            utr_presets = utr_presets[:2]

        seen = {c.sequence for c in existing_candidates}
        new_candidates: list[Candidate] = []

        for cds_seq in all_cds_seqs[:6]:  # cap at 6 CDS to avoid explosion
            for utr5_preset in utr_presets:
                utr5_seq = self._generate_utr("5utr", utr5_preset)
                if utr5_seq is None:
                    continue
                for utr3_preset in utr_presets:
                    utr3_seq = self._generate_utr("3utr", utr3_preset)
                    if utr3_seq is None:
                        continue

                    full_seq = utr5_seq + cds_seq + utr3_seq
                    if full_seq in seen:
                        continue
                    seen.add(full_seq)

                    # Determine source label for traceability
                    is_shuffled = cds_seq in shuffled_cds_variants
                    best_cds_seq = current_best.metadata.get("cds_sequence", "")
                    is_current_best = (cds_seq == best_cds_seq and not is_shuffled)
                    if is_shuffled:
                        source_label = f"bmc:shuffled_{shuffle_end}:utr5_{utr5_preset}:utr3_{utr3_preset}"
                        cds_source = "shuffled"
                    elif is_current_best:
                        source_label = f"bmc:current_best:utr5_{utr5_preset}:utr3_{utr3_preset}"
                        cds_source = "current_best"
                    else:
                        source_label = f"bmc:lambda_adjusted:utr5_{utr5_preset}:utr3_{utr3_preset}"
                        cds_source = "lambda_adjusted"

                    candidate = Candidate(
                        sequence=full_seq,
                        sequence_type="mrna",
                        source=source_label,
                        metadata={
                            "utr5_sequence": utr5_seq,
                            "cds_sequence": cds_seq,
                            "utr3_sequence": utr3_seq,
                            "utr5_length": len(utr5_seq),
                            "utr3_length": len(utr3_seq),
                            "utr5_preset": utr5_preset,
                            "utr3_preset": utr3_preset,
                            "cds_length": len(cds_seq),
                            "cds_source": cds_source,
                            "protein_sequence": adjusted_inp.protein_sequence,
                            "bmc_regenerated": True,
                            "bmc_feedback_modules": list(feedback.keys()),
                            "bmc_shuffle_end": shuffle_end if is_shuffled else None,
                        },
                    )
                    new_candidates.append(candidate)
                    _LOGGER.info(
                        "bmc_candidate_generated source=%s utr5=%s utr3=%s len=%d",
                        source_label,
                        utr5_preset,
                        utr3_preset,
                        len(full_seq),
                    )

        _LOGGER.info(
            "bmc_regeneration_complete new=%d seen_total=%d",
            len(new_candidates),
            len(seen),
        )
        return new_candidates

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return self._empty_result("No candidates produced.")

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

        # ── 5-dimensional equal-weight Borda count (NEW) ──
        # Each dimension is ranked independently; ranks are summed with equal
        # weight.  This avoids both the量纲 disaster of raw-value weighting
        # and the subjectivity of hand-tuned rank weights.
        cds_rank_map = _module_rank(candidates, "cds_component")
        utr5_rank_map = _module_rank(candidates, "utr5_mrl")
        utr3_rank_map = _module_rank(candidates, "utr3_stability")
        full_mfe_rank_map = _module_rank(candidates, "full_mfe_score")
        junction_rank_map = _module_rank(candidates, "junction_score")

        for c in candidates:
            total_rank = (
                cds_rank_map[c.id]
                + utr5_rank_map[c.id]
                + utr3_rank_map[c.id]
                + full_mfe_rank_map[c.id]
                + junction_rank_map[c.id]
            )
            c.scores["total_rank"] = total_rank
            c.scores["cds_rank"] = cds_rank_map[c.id]
            c.scores["utr5_rank"] = utr5_rank_map[c.id]
            c.scores["utr3_rank"] = utr3_rank_map[c.id]
            c.scores["full_mfe_rank"] = full_mfe_rank_map[c.id]
            c.scores["junction_rank"] = junction_rank_map[c.id]
            # Backward-compat: total_score = -total_rank (higher = better)
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
                f"cdsU={mb.get('cds_u_fraction'):.3f}" if mb.get("cds_u_fraction") is not None else "cdsU=N/A",
                f"fullU={mb.get('full_u_fraction'):.3f}" if mb.get("full_u_fraction") is not None else "fullU=N/A",
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
                f"fullMfeRank={scores.get('full_mfe_rank')} junctionRank={scores.get('junction_rank')}",
                f"total_rank={scores.get('total_rank'):.2f}",
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


# LLM Critic Configuration

FULL_LENGTH_MRNA_CRITIC_CONFIG = CriticConfig(
    workflow_name="full_length_mrna_design",
    workflow_description=(
        "Design full-length mRNA (5'UTR + CDS + 3'UTR) from protein sequence. "
        "CDS is generated via MrnaCdsDesignWorkflow (LinearDesign/RNARL/GEMORNA); "
        "UTRs are appended from GEMORNA short/medium/long presets. "
        "CDS-level quality concerns should be addressed by adjusting design_tool "
        "or lambda_value, which are passed down to the CDS sub-workflow."
    ),
    evaluation_dimensions=[
        "UTR length mode: Check whether the user requested a specific utr_mode (short/medium/long). If so, verify that candidates match the request. If utr_mode='all' was used, ensure the result includes a diverse spread across presets.",
        "5'UTR MRL (Mean Ribosomal Load): Predicted by GEMORNA. Higher values generally indicate better translation initiation efficiency. Evaluate against any user-specified MRL thresholds.",
        "3'UTR stability: Predicted by GEMORNA. Higher values indicate better stability. Evaluate against user constraints.",
        "IRES potential: IRESfinder outputs a probability in [0, 1]. Do NOT apply a hard threshold. Instead, check the user's original request: for standard cap-dependent mRNA, high IRES may be undesirable; for IRES-driven applications, it may be desired. Flag as an issue only when it conflicts with the user's stated purpose.",
        "Full-length MFE: Overall RNA secondary structure stability from ViennaRNA/LinearFold. Too negative may impede translation; too positive may indicate instability. Evaluate relative to user constraints.",
        "RNASTOP overall_stability: If available, values closer to 1.0 indicate higher predicted stability.",
        "CDS quality (CAI/MFE): These are computed by the CDS sub-workflow. If the user specified CAI or MFE preferences, they should be propagated via design_tool and lambda_value adjustments. Do not duplicate deep CDS diagnosis here — focus on whether the parameter settings align with user intent.",
        "UTR combination diversity: If all top candidates use the same UTR preset pair, consider switching utr_mode or requesting broader exploration.",
    ],
    adjustable_params={
        "utr_mode": {
            "type": "enum",
            "values": ["short", "medium", "long", "all"],
            "hint": "UTR length preset. If user asked for specific lengths (e.g. 'long 3\\'UTR for stability'), set accordingly. 'all' explores all presets.",
        },
        "design_tool": {
            "type": "enum",
            "values": ["lineardesign", "rnarl", "gemorna", "all"],
            "hint": "CDS design tool. Passed to the CDS sub-workflow. If CDS quality is poor, switch tools. 'all' runs all tools for diversity.",
        },
        "lambda_value": {
            "type": "float",
            "min": 0.0,
            "max": 20.0,
            "hint": "LinearDesign MFE/CAI tradeoff (range [0, +∞), typically ≤10). Only effective when design_tool='lineardesign' or 'all'. Decrease to improve MFE (more negative); increase to improve CAI.",
        },
        "model_type": {
            "type": "enum",
            "values": [
                "Homo sapiens mRNA",
                "Homo sapiens circular RNA",
                "Arabidopsis thaliana mRNA",
                "Escherichia coli mRNA",
                "Penicillium chrysogenum mRNA",
                "Chlamydomonas reinhardtii mRNA",
                "Thermococcus kodakarensis KOD1 mRNA",
            ],
            "hint": "RNARL model type. Only effective when design_tool='rnarl' or 'all'.",
        },
        "cai_species": {
            "type": "str",
            "hint": "Species for CAI computation. Built-in: human, mouse, rat, fly, worm, zebrafish, arabidopsis, yeast, ecoli, bsubtilis, cho.",
        },
        "run_fold": {
            "type": "bool",
            "hint": "Whether to run RNA secondary structure folding. Should normally stay True.",
        },
        "run_gc": {
            "type": "bool",
            "hint": "Whether to compute GC content. Should normally stay True.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
)


class FullLengthMrnaDesignLLMCritic(BaseLLMCritic):
    """LLM-driven Critic for full-length mRNA design.

    Focuses on whether the candidate set satisfies constraints from the user's
    original prompt (UTR length mode, CAI/MFE preferences, IRES tolerance, etc.)
    rather than applying hard-coded thresholds.

    CDS-level concerns are propagated via parameter overrides
    (design_tool, lambda_value) to the nested MrnaCdsDesignWorkflow.
    """

    def _default_config(self) -> CriticConfig:
        return FULL_LENGTH_MRNA_CRITIC_CONFIG

    def _build_context(self, result: WorkflowResult, state: dict[str, Any]) -> dict[str, Any]:
        """Extend base context with full-length mRNA specific statistics."""
        ctx = super()._build_context(result, state)

        candidates = result.all_candidates
        if not candidates:
            ctx["full_length_stats"] = {
                "utr5_preset_distribution": {},
                "utr3_preset_distribution": {},
                "cds_source_distribution": {},
                "utr5_mrl_range": {"min": None, "max": None, "mean": None, "count": 0},
                "utr3_stability_range": {"min": None, "max": None, "mean": None, "count": 0},
                "utr5_ires_range": {"min": None, "max": None, "mean": None, "count": 0},
                "full_length_mfe_range": {"min": None, "max": None, "mean": None, "count": 0},
            }
            return ctx

        # UTR preset distribution
        utr5_presets: dict[str, int] = {}
        utr3_presets: dict[str, int] = {}
        cds_sources: dict[str, int] = {}

        utr5_mrl_values: list[float] = []
        utr3_stab_values: list[float] = []
        ires_values: list[float] = []
        full_mfe_values: list[float] = []

        for c in candidates:
            meta = c.metadata or {}
            mb = meta.get("metrics_bundle", {})

            # Preset counts
            p5 = meta.get("utr5_preset", "unknown")
            p3 = meta.get("utr3_preset", "unknown")
            utr5_presets[p5] = utr5_presets.get(p5, 0) + 1
            utr3_presets[p3] = utr3_presets.get(p3, 0) + 1

            # CDS source counts
            cds_src = meta.get("cds_source", "unknown")
            cds_sources[cds_src] = cds_sources.get(cds_src, 0) + 1

            # Metric ranges
            if (v := mb.get("utr5_predicted_mrl")) is not None:
                utr5_mrl_values.append(float(v))
            if (v := mb.get("utr3_predicted_stability")) is not None:
                utr3_stab_values.append(float(v))
            if (v := mb.get("utr5_ires_potential")) is not None:
                ires_values.append(float(v))
            if (v := mb.get("full_length_mfe")) is not None:
                full_mfe_values.append(float(v))

        def _range(vals: list[float]) -> dict[str, Any]:
            if not vals:
                return {"min": None, "max": None, "mean": None, "count": 0}
            return {"min": min(vals), "max": max(vals), "mean": sum(vals) / len(vals), "count": len(vals)}

        ctx["full_length_stats"] = {
            "utr5_preset_distribution": utr5_presets,
            "utr3_preset_distribution": utr3_presets,
            "cds_source_distribution": cds_sources,
            "utr5_mrl_range": _range(utr5_mrl_values),
            "utr3_stability_range": _range(utr3_stab_values),
            "utr5_ires_range": _range(ires_values),
            "full_length_mfe_range": _range(full_mfe_values),
        }

        # Best candidate breakdown for quick reference
        best = result.best_candidate
        if best and best.metadata:
            bm = best.metadata.get("metrics_bundle", {})
            ctx["best_candidate_breakdown"] = {
                "source": best.source,
                "total_length": bm.get("total_length"),
                "utr5_preset": best.metadata.get("utr5_preset"),
                "utr3_preset": best.metadata.get("utr3_preset"),
                "cds_source": best.metadata.get("cds_source"),
                "utr5_mrl": bm.get("utr5_predicted_mrl"),
                "utr3_stability": bm.get("utr3_predicted_stability"),
                "utr5_ires": bm.get("utr5_ires_potential"),
                "full_mfe": bm.get("full_length_mfe"),
                "cds_cai": bm.get("cds_cai"),
                "cds_mfe": bm.get("cds_mfe"),
                "overall_stability": bm.get("overall_stability"),
            }

        return ctx
