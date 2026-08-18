"""Composable candidate evaluators for RNA workflow evaluation (Layer 2).

Provides a library of reusable evaluator components that wrap Layer-1 capability
calls. Workflows compose evaluators rather than hand-writing tool invocations.

Example::

    evaluator = CompositeEvaluator([
        GCContentEvaluator(capabilities),
        SecondaryStructureEvaluator(capabilities, run_fold=True),
        UnpairedFractionEvaluator(capabilities),
        RNASTOPEvaluator(capabilities),
        CAIEvaluator(capabilities, species_key="cai_species"),
    ])
    metrics = evaluator.evaluate(candidate, {"species": "Homo sapiens"})
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from agent_core.capabilities.base import CapabilityRegistry, CapabilityResult
from agent_core.constants.species import DEFAULT_CAI_SPECIES
from agent_core.file_manager import save_sequence, save_text_file
from agent_core.sequence_utils import _pick_float, _pick_int
from agent_core.workflow_models import Candidate, ToolCallRecord

_LOGGER = logging.getLogger("agent_core.workflows.evaluators")


def _trace_capability_call(
    candidate: Candidate,
    capability_name: str,
    tool_args: dict[str, Any],
    cap_result: CapabilityResult,
    step_name: str = "",
    extra_metrics: dict[str, Any] | None = None,
) -> None:
    """Create a ToolCallRecord from a CapabilityResult and append to candidate."""
    record = ToolCallRecord(
        step_name=step_name or f"{candidate.id}_{capability_name}",
        tool_name=capability_name,
        input_summary=json.dumps(tool_args, default=str),
        output_summary=json.dumps(cap_result.output, default=str)[:500],
        success=cap_result.success,
        error=cap_result.error,
        elapsed_time=cap_result.elapsed_time,
        artifacts=dict(cap_result.output) if cap_result.success else {},
        metrics=extra_metrics or {},
    )
    candidate.add_tool_record(record)


class BaseEvaluator(ABC):
    """Abstract base for a single evaluation step."""

    def __init__(self, capabilities: CapabilityRegistry):
        self.capabilities = capabilities

    @abstractmethod
    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Evaluate *candidate* and return a dict of metrics.

        Args:
            candidate: The candidate to evaluate.
            context: Additional context (e.g. species, workflow state).
                     Must contain ``workflow_state`` key with the dict
                     to pass to capability invocations.

        Returns:
            A dict of metric key-value pairs. Empty dict on skip/failure.
        """
        ...


class GCContentEvaluator(BaseEvaluator):
    """Evaluate GC content via ``compute_rna_sequence_gc_content``."""

    capability_name = "compute_rna_sequence_gc_content"

    def __init__(
        self,
        capabilities: CapabilityRegistry,
        *,
        run_gc: bool = True,
    ):
        super().__init__(capabilities)
        self.run_gc = run_gc

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        if not self.run_gc or not self.capabilities.has(self.capability_name):
            return {}

        filepath = self._ensure_filepath(candidate)
        state = context.get("workflow_state", {})
        args = {"filepath": filepath}

        res = self.capabilities.get(self.capability_name).invoke(args, state=state)
        if res.success:
            metrics = {
                "gc_content": _pick_float(res.output, "gc_content"),
                "sequence_length": _pick_int(res.output, "sequence_length"),
            }
            _trace_capability_call(
                candidate, self.capability_name, args, res, extra_metrics=metrics
            )
            return metrics
        _LOGGER.warning("gc_evaluator_failed error=%s", res.error)
        _trace_capability_call(candidate, self.capability_name, args, res)
        return {}

    @staticmethod
    def _ensure_filepath(candidate: Candidate) -> str:
        fp = candidate.metadata.get("workspace_filepath")
        if not fp:
            fp = save_sequence(candidate.sequence, prefix="eval")
            candidate.metadata["workspace_filepath"] = fp
        return fp


class UContentEvaluator(BaseEvaluator):
    """Evaluate U content via ``compute_rna_sequence_u_content``."""

    capability_name = "compute_rna_sequence_u_content"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        if not self.capabilities.has(self.capability_name):
            return {}

        filepath = self._ensure_filepath(candidate)
        state = context.get("workflow_state", {})
        args = {"filepath": filepath}

        res = self.capabilities.get(self.capability_name).invoke(args, state=state)
        if res.success:
            metrics = {
                "u_fraction": _pick_float(res.output, "u_fraction"),
                "u_count": _pick_int(res.output, "u_count"),
            }
            _trace_capability_call(
                candidate, self.capability_name, args, res, extra_metrics=metrics
            )
            return metrics
        _LOGGER.warning("u_content_evaluator_failed error=%s", res.error)
        _trace_capability_call(candidate, self.capability_name, args, res)
        return {}

    @staticmethod
    def _ensure_filepath(candidate: Candidate) -> str:
        fp = candidate.metadata.get("workspace_filepath")
        if not fp:
            fp = save_sequence(candidate.sequence, prefix="eval")
            candidate.metadata["workspace_filepath"] = fp
        return fp


class SecondaryStructureEvaluator(BaseEvaluator):
    """Evaluate secondary structure via LinearFold with ViennaRNA fallback."""

    primary_cap = "predict_rna_secondary_structure_with_linearfold"
    fallback_cap = "predict_rna_secondary_structure"

    def __init__(
        self,
        capabilities: CapabilityRegistry,
        *,
        run_fold: bool = True,
    ):
        super().__init__(capabilities)
        self.run_fold = run_fold

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        if not self.run_fold:
            return {}

        filepath = self._ensure_filepath(candidate)
        state = context.get("workflow_state", {})
        args = {"filepath": filepath}

        # Primary: LinearFold (fast O(n) approximation)
        if self.capabilities.has(self.primary_cap):
            res = self.capabilities.get(self.primary_cap).invoke(args, state=state)
            if res.success:
                structure = res.output.get("structure", "")
                candidate.metadata["structure"] = structure
                metrics = {
                    "mfe_kcal_per_mol": _pick_float(res.output, "mfe"),
                    "structure": structure,
                    "fold_tool": "LinearFold",
                }
                _trace_capability_call(
                    candidate, self.primary_cap, args, res, extra_metrics=metrics
                )
                return metrics
            _LOGGER.warning(
                "fold_primary_failed tool=%s error=%s", self.primary_cap, res.error
            )
            _trace_capability_call(candidate, self.primary_cap, args, res)

        # Fallback: ViennaRNA (exact O(n³) when LinearFold unavailable)
        if self.capabilities.has(self.fallback_cap):
            res = self.capabilities.get(self.fallback_cap).invoke(args, state=state)
            if res.success:
                structure = res.output.get("structure", "")
                candidate.metadata["structure"] = structure
                metrics = {
                    "mfe_kcal_per_mol": _pick_float(res.output, "mfe_kcal_per_mol"),
                    "structure": structure,
                    "fold_tool": "ViennaRNA",
                }
                _trace_capability_call(
                    candidate, self.fallback_cap, args, res, extra_metrics=metrics
                )
                return metrics
            _LOGGER.warning(
                "fold_fallback_failed tool=%s error=%s", self.fallback_cap, res.error
            )
            _trace_capability_call(candidate, self.fallback_cap, args, res)

        return {}

    @staticmethod
    def _ensure_filepath(candidate: Candidate) -> str:
        fp = candidate.metadata.get("workspace_filepath")
        if not fp:
            fp = save_sequence(candidate.sequence, prefix="eval")
            candidate.metadata["workspace_filepath"] = fp
        return fp


class UnpairedFractionEvaluator(BaseEvaluator):
    """Evaluate unpaired fraction from a dot-bracket structure string."""

    capability_name = "compute_dot_bracket_unpaired_fraction"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        structure = candidate.metadata.get("structure")
        if not structure:
            return {}
        if not self.capabilities.has(self.capability_name):
            return {}

        state = context.get("workflow_state", {})
        struct_fp = save_text_file(structure, prefix="structure", suffix=".db")
        args = {"filepath": struct_fp}
        res = self.capabilities.get(self.capability_name).invoke(args, state=state)
        if res.success:
            metrics = {"unpaired_fraction": _pick_float(res.output, "unpaired_fraction")}
            _trace_capability_call(
                candidate, self.capability_name, args, res, extra_metrics=metrics
            )
            return metrics
        _LOGGER.warning("unpaired_evaluator_failed error=%s", res.error)
        _trace_capability_call(candidate, self.capability_name, args, res)
        return {}


class RNASTOPEvaluator(BaseEvaluator):
    """Evaluate overall stability via RNASTOP."""

    capability_name = "predict_mrna_stability_with_rnastop"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        if not self.capabilities.has(self.capability_name):
            return {}

        filepath = self._ensure_filepath(candidate)
        state = context.get("workflow_state", {})
        args: dict[str, Any] = {"filepath": filepath}
        structure = candidate.metadata.get("structure")
        if structure:
            args["structure"] = structure

        res = self.capabilities.get(self.capability_name).invoke(args, state=state)
        if res.success:
            metrics = {
                "rnastop_overall_stability": _pick_float(
                    res.output, "overall_stability"
                )
            }
            _trace_capability_call(
                candidate, self.capability_name, args, res, extra_metrics=metrics
            )
            return metrics
        _LOGGER.warning("rnastop_evaluator_failed error=%s", res.error)
        _trace_capability_call(candidate, self.capability_name, args, res)
        return {}

    @staticmethod
    def _ensure_filepath(candidate: Candidate) -> str:
        fp = candidate.metadata.get("workspace_filepath")
        if not fp:
            fp = save_sequence(candidate.sequence, prefix="eval")
            candidate.metadata["workspace_filepath"] = fp
        return fp


class CAIEvaluator(BaseEvaluator):
    """Evaluate CAI via ``compute_cai_for_cds_sequence``."""

    capability_name = "compute_cai_for_cds_sequence"

    def __init__(
        self,
        capabilities: CapabilityRegistry,
        *,
        species_key: str = "cai_species",
        default_species: str = DEFAULT_CAI_SPECIES,
    ):
        super().__init__(capabilities)
        self.species_key = species_key
        self.default_species = default_species

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        if not self.capabilities.has(self.capability_name):
            return {}

        filepath = self._ensure_filepath(candidate)
        state = context.get("workflow_state", {})
        species = context.get(
            "species",
            candidate.metadata.get(self.species_key, self.default_species),
        )
        args = {"filepath": filepath, "species": species}

        res = self.capabilities.get(self.capability_name).invoke(args, state=state)
        if res.success:
            metrics = {
                "cai_score": _pick_float(res.output, "cai_score"),
                "cai_species": species,
            }
            _trace_capability_call(
                candidate, self.capability_name, args, res, extra_metrics=metrics
            )
            return metrics
        _LOGGER.warning("cai_evaluator_failed species=%s error=%s", species, res.error)
        _trace_capability_call(candidate, self.capability_name, args, res)
        return {}

    @staticmethod
    def _ensure_filepath(candidate: Candidate) -> str:
        fp = candidate.metadata.get("workspace_filepath")
        if not fp:
            fp = save_sequence(candidate.sequence, prefix="eval")
            candidate.metadata["workspace_filepath"] = fp
        return fp


class DuplexBindingEvaluator(BaseEvaluator):
    """Evaluate siRNA duplex binding energy via ViennaRNA RNAcofold."""

    capability_name = "compute_sirna_duplex_binding_vienna"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        if not self.capabilities.has(self.capability_name):
            return {}

        seq = candidate.sequence
        state = context.get("workflow_state", {})
        rc_map = {"A": "U", "U": "A", "G": "C", "C": "G"}
        antisense = "".join(rc_map.get(b, b) for b in reversed(seq.upper()))
        duplex_content = f">sense\n{seq}\n>antisense\n{antisense}\n"
        duplex_fp = save_sequence(duplex_content, prefix="sirna_duplex")
        args = {"filepath": duplex_fp}

        res = self.capabilities.get(self.capability_name).invoke(args, state=state)
        if res.success:
            metrics = {"duplex_mfe": _pick_float(res.output, "mfe_kcal_per_mol")}
            _trace_capability_call(
                candidate, self.capability_name, args, res, extra_metrics=metrics
            )
            return metrics
        _LOGGER.warning("duplex_evaluator_failed error=%s", res.error)
        _trace_capability_call(candidate, self.capability_name, args, res)
        return {}


class SelfStructureEvaluator(BaseEvaluator):
    """Evaluate self-structure MFE (optional, non-fatal) via LinearFold with ViennaRNA fallback."""

    primary_cap = "predict_rna_secondary_structure_with_linearfold"
    fallback_cap = "predict_rna_secondary_structure"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        filepath = self._ensure_filepath(candidate)
        state = context.get("workflow_state", {})
        args = {"filepath": filepath}

        # Primary: LinearFold (fast O(n) approximation)
        if self.capabilities.has(self.primary_cap):
            res = self.capabilities.get(self.primary_cap).invoke(args, state=state)
            if res.success:
                metrics = {
                    "self_structure_mfe": _pick_float(res.output, "mfe"),
                    "structure": res.output.get("structure", ""),
                    "fold_tool": "LinearFold",
                }
                _trace_capability_call(
                    candidate, self.primary_cap, args, res, extra_metrics=metrics
                )
                return metrics
            _LOGGER.debug("self_structure_linearfold_failed error=%s", res.error)
            _trace_capability_call(candidate, self.primary_cap, args, res)

        # Fallback: ViennaRNA (exact O(n³) when LinearFold unavailable)
        if self.capabilities.has(self.fallback_cap):
            res = self.capabilities.get(self.fallback_cap).invoke(args, state=state)
            if res.success:
                metrics = {
                    "self_structure_mfe": _pick_float(res.output, "mfe_kcal_per_mol"),
                    "structure": res.output.get("structure", ""),
                    "fold_tool": "ViennaRNA",
                }
                _trace_capability_call(
                    candidate, self.fallback_cap, args, res, extra_metrics=metrics
                )
                return metrics
            _LOGGER.debug("self_structure_vienna_failed error=%s", res.error)
            _trace_capability_call(candidate, self.fallback_cap, args, res)

        return {}

    @staticmethod
    def _ensure_filepath(candidate: Candidate) -> str:
        fp = candidate.metadata.get("workspace_filepath")
        if not fp:
            fp = save_sequence(candidate.sequence, prefix="eval")
            candidate.metadata["workspace_filepath"] = fp
        return fp


class CRGPTEvaluator(BaseEvaluator):
    """Evaluate sgRNA handle via CRGPT re-scoring."""

    capability_name = "score_sgrna_handle_with_crgpt"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        evaluate_crgpt = bool(
            candidate.metadata.get("evaluate_crgpt_score", True)
        )
        if not evaluate_crgpt:
            # Use design-time metrics as fallback
            return {
                "nn_score": candidate.metadata.get("design_nn_score"),
                "log_likelihood": candidate.metadata.get("design_log_likelihood"),
                "structure_distance": candidate.metadata.get(
                    "design_structure_distance"
                ),
                "mfe": candidate.metadata.get("design_mfe"),
            }

        if not self.capabilities.has(self.capability_name):
            return {
                "nn_score": candidate.metadata.get("design_nn_score"),
                "log_likelihood": candidate.metadata.get("design_log_likelihood"),
                "structure_distance": candidate.metadata.get(
                    "design_structure_distance"
                ),
                "mfe": candidate.metadata.get("design_mfe"),
            }

        state = context.get("workflow_state", {})
        args = {"sequence": candidate.sequence}
        try:
            res = self.capabilities.get(self.capability_name).invoke(args, state=state)
            if res.success:
                metrics = {
                    "nn_score": _pick_float(res.output, "nn_score"),
                    "log_likelihood": _pick_float(res.output, "log_likelihood"),
                    "structure_distance": res.output.get("structure_distance"),
                    "mfe": _pick_float(res.output, "mfe"),
                }
                _trace_capability_call(
                    candidate, self.capability_name, args, res, extra_metrics=metrics
                )
                return metrics
            _LOGGER.warning("crgpt_evaluator_failed error=%s", res.error)
            _trace_capability_call(candidate, self.capability_name, args, res)
        except Exception as exc:
            _LOGGER.warning("crgpt_evaluator_exception exc=%s", exc)

        return {
            "nn_score": candidate.metadata.get("design_nn_score"),
            "log_likelihood": candidate.metadata.get("design_log_likelihood"),
            "structure_distance": candidate.metadata.get("design_structure_distance"),
            "mfe": candidate.metadata.get("design_mfe"),
        }


class CRISOTEvaluator(BaseEvaluator):
    """Evaluate CRISPR off-target via CRISOT (cached per-run in workflow state)."""

    capability_name = "score_crispr_off_target_with_crisot"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        wf_inp = context.get("workflow_input")
        if wf_inp is None:
            return {"crisot_score": None}

        evaluate_crisot = getattr(wf_inp, "evaluate_crisot", True)
        guide_seq = getattr(wf_inp, "guide_sequence", None)
        target_seq = getattr(wf_inp, "target_sequence", None)

        if not evaluate_crisot or not guide_seq or not target_seq:
            return {"crisot_score": None}

        state = context.get("workflow_state", {})
        if state is None:
            return {"crisot_score": None}

        # Cache CRISOT result per-run (does not vary per candidate)
        cache_key = "_crisot_score_cache"
        if cache_key in state:
            return {"crisot_score": state[cache_key]}

        if not self.capabilities.has(self.capability_name):
            return {"crisot_score": None}

        try:
            guide_fp = save_sequence(guide_seq, prefix="sgrna_guide")
            args = {"filepath": guide_fp, "target_sequence": target_seq}
            res = self.capabilities.get(self.capability_name).invoke(args, state=state)
            if res.success:
                crisot_score = _pick_float(res.output, "crisot_score")
                state[cache_key] = crisot_score
                metrics = {"crisot_score": crisot_score}
                _trace_capability_call(
                    candidate, self.capability_name, args, res, extra_metrics=metrics
                )
                return metrics
            _LOGGER.warning("crisot_evaluator_failed error=%s", res.error)
            _trace_capability_call(candidate, self.capability_name, args, res)
        except Exception as exc:
            _LOGGER.warning("crisot_evaluator_exception exc=%s", exc)

        return {"crisot_score": None}


class CRISOTSpecificityEvaluator(BaseEvaluator):
    """Aggregate CRISOT-Spec genome-context specificity (cached per run).

    Consumes the workflow input's optional ``off_target_sequences`` list:
    builds the upstream On/Off CSV (on-target rows against every listed
    off-target) and invokes the CRISOT specificity microservice.  Absent
    list, absent capability, or a failed call degrade to
    ``crisot_specificity = None`` (scoring component skipped).
    """

    capability_name = "calculate_crispr_specificity_with_crisot"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        wf_inp = context.get("workflow_input")
        if wf_inp is None:
            return {"crisot_specificity": None}

        guide_seq = getattr(wf_inp, "guide_sequence", None)
        off_targets = [
            str(s).strip().upper()
            for s in (getattr(wf_inp, "off_target_sequences", None) or [])
            if str(s).strip()
        ]
        if not guide_seq or not off_targets:
            return {"crisot_specificity": None}

        state = context.get("workflow_state", {}) or {}
        cache_key = "_crisot_spec_cache"
        if cache_key in state:
            return {"crisot_specificity": state[cache_key]}

        if not self.capabilities.has(self.capability_name):
            return {"crisot_specificity": None}

        try:
            csv_path = save_text_file(
                "On,Off\n"
                + "".join(f"{str(guide_seq).strip().upper()},{off}\n" for off in off_targets),
                prefix="crisot_on_off",
                suffix=".csv",
            )
            args = {"csv_filepath": csv_path}
            res = self.capabilities.get(self.capability_name).invoke(args, state=state)
            if res.success:
                crisot_spec = _pick_float(res.output, "crisot_spec")
                state[cache_key] = crisot_spec
                metrics = {"crisot_specificity": crisot_spec}
                _trace_capability_call(
                    candidate, self.capability_name, args, res, extra_metrics=metrics
                )
                return metrics
            _LOGGER.warning("crisot_specificity_evaluator_failed error=%s", res.error)
            _trace_capability_call(candidate, self.capability_name, args, res)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("crisot_specificity_evaluator_exception exc=%s", exc)

        return {"crisot_specificity": None}


class UTR5MrlEvaluator(BaseEvaluator):
    """Evaluate 5'UTR MRL via GEMORNA."""

    capability_name = "predict_5utr_mrl_with_gemorna"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        utr5 = candidate.metadata.get("utr5_sequence", "")
        if len(utr5) < 10 or not self.capabilities.has(self.capability_name):
            return {}

        state = context.get("workflow_state", {})
        utr5_fp = save_sequence(utr5, prefix="utr5")
        args = {"filepath": utr5_fp}
        res = self.capabilities.get(self.capability_name).invoke(args, state=state)
        if res.success:
            metrics = {"utr5_predicted_mrl": _pick_float(res.output, "predicted_mrl")}
            _trace_capability_call(
                candidate, self.capability_name, args, res, extra_metrics=metrics
            )
            return metrics
        _LOGGER.warning("utr5_mrl_evaluator_failed error=%s", res.error)
        _trace_capability_call(candidate, self.capability_name, args, res)
        return {}


class UTR3StabilityEvaluator(BaseEvaluator):
    """Evaluate 3'UTR stability via GEMORNA."""

    capability_name = "predict_3utr_stability_with_gemorna"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        utr3 = candidate.metadata.get("utr3_sequence", "")
        if not utr3 or not self.capabilities.has(self.capability_name):
            return {}

        state = context.get("workflow_state", {})
        utr3_fp = save_sequence(utr3, prefix="utr3")
        args = {"filepath": utr3_fp}
        res = self.capabilities.get(self.capability_name).invoke(args, state=state)
        if res.success:
            metrics = {
                "utr3_predicted_stability": _pick_float(
                    res.output, "predicted_stability"
                )
            }
            _trace_capability_call(
                candidate, self.capability_name, args, res, extra_metrics=metrics
            )
            return metrics
        _LOGGER.warning("utr3_stability_evaluator_failed error=%s", res.error)
        _trace_capability_call(candidate, self.capability_name, args, res)
        return {}


class IRESEvaluator(BaseEvaluator):
    """Evaluate IRES potential in 5'UTR via IRESfinder."""

    capability_name = "predict_putative_ires_with_iresfinder"

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        utr5 = candidate.metadata.get("utr5_sequence", "")
        if len(utr5) < 30 or not self.capabilities.has(self.capability_name):
            return {}

        state = context.get("workflow_state", {})
        utr5_fp = save_sequence(utr5, prefix="utr5")
        args = {"filepath": utr5_fp}
        res = self.capabilities.get(self.capability_name).invoke(args, state=state)
        if res.success:
            max_score = _pick_float(res.output, "max_score")
            if max_score is not None:
                metrics = {"utr5_ires_potential": max_score}
                _trace_capability_call(
                    candidate, self.capability_name, args, res, extra_metrics=metrics
                )
                return metrics
        _LOGGER.warning("ires_evaluator_failed error=%s", res.error)
        _trace_capability_call(candidate, self.capability_name, args, res)
        return {}


# Full-length ddG window definitions for the 5'UTR-CDS junction (report-only
# metric; aligned with experiments/junction_ddg_pilot_eval.py, Phase 0 pilot).
_DDG_W1_UPSTREAM_NT = 6
_DDG_W1_DOWNSTREAM_NT = 9   # from CDS start -> 15 nt AUG/Kozak context
_DDG_W2_UTR_NT = 60
_DDG_W2_CDS_NT = 30


def _ddg_constraint_string(full_len: int, start: int, end: int) -> str:
    """'?' everywhere, '.' (forced unpaired) inside [start, end)."""
    c = ["?"] * full_len
    for i in range(max(0, start), min(full_len, end)):
        c[i] = "."
    return "".join(c)


class JunctionEvaluator(BaseEvaluator):
    """Evaluate junction stability, GC continuity, and translation-start openness.

    Assesses the 20-nt overlap regions at:
    - 5'UTR / CDS boundary (last 20 nt of 5'UTR + first 20 nt of CDS)
    - CDS / 3'UTR boundary (last 20 nt of CDS + first 20 nt of 3'UTR)

    For the 5'UTR-CDS junction, additionally reports a full-length
    constrained-fold ddG (``ddG_open = MFE_constrained - MFE_unconstrained``)
    on the concatenated mRNA (utr5 + cds + utr3) with LinearFold, where the
    constraint forces the AUG-context window unpaired. Two windows are
    reported: W1 (narrow, CDS start -6..+9) and W2 (wide, 5'UTR tail 60 nt +
    CDS head 30 nt, clipped to the actual UTR length). This replaces the
    retired fragment-fold AUG/Kozak burial booleans, which were falsified as a
    translation-initiation proxy by pre-registered experiments (P1 v2, P2, and
    the Phase 0 ddG pilot ``junction_ddg_pilot_summary.json``). ddG is a
    report/profile metric only; it never triggers automatic repair.

    Returns MFE, GC-difference, and ddG metrics for each junction.
    """

    primary_cap = "predict_rna_secondary_structure_with_linearfold"
    fallback_cap = "predict_rna_secondary_structure"

    def evaluate(self, candidate: Candidate, context: dict[str, Any]) -> dict[str, Any]:
        utr5 = candidate.metadata.get("utr5_sequence", "")
        cds = candidate.metadata.get("cds_sequence", "")
        utr3 = candidate.metadata.get("utr3_sequence", "")

        if not utr5 or not cds or not utr3:
            return {}

        results: dict[str, Any] = {}

        # Junction 1: 5'UTR - CDS
        j1_left = utr5[-20:] if len(utr5) >= 20 else utr5
        j1_right = cds[:20] if len(cds) >= 20 else cds
        j1_seq = j1_left + j1_right

        if len(j1_seq) >= 10:
            # CDS starts right after the 5'UTR slice in the junction sequence
            j1_metrics = self._evaluate_junction(
                j1_seq,
                "junction_5utr_cds",
                candidate,
                context,
                cds_start_offset=len(j1_left),
                split_offset=len(j1_left),
            )
            results.update(j1_metrics)

        # Junction 2: CDS - 3'UTR
        j2_left = cds[-20:] if len(cds) >= 20 else cds
        j2_right = utr3[:20] if len(utr3) >= 20 else utr3
        j2_seq = j2_left + j2_right

        if len(j2_seq) >= 10:
            j2_metrics = self._evaluate_junction(
                j2_seq,
                "junction_cds_3utr",
                candidate,
                context,
                split_offset=len(j2_left),
            )
            results.update(j2_metrics)

        # Full-length constrained-fold ddG at the 5'UTR-CDS junction
        # (report-only; replaces the retired burial booleans).
        results.update(self._evaluate_ddg_open(utr5, cds, utr3, candidate, context))

        return results

    def _evaluate_junction(
        self,
        seq: str,
        prefix: str,
        candidate: Candidate,
        context: dict[str, Any],
        cds_start_offset: int | None = None,
        split_offset: int | None = None,
    ) -> dict[str, Any]:
        state = context.get("workflow_state", {})
        # Include candidate.id to guarantee unique filenames across evaluations
        unique_prefix = f"{prefix}_{candidate.id}"
        seq_fp = save_sequence(seq, prefix=unique_prefix)

        metrics: dict[str, Any] = {}
        metrics[f"{prefix}_length"] = len(seq)
        args = {"filepath": seq_fp}
        step_name = f"{candidate.id}_{prefix}_fold"

        # Primary: LinearFold (fast O(n) approximation)
        if self.capabilities.has(self.primary_cap):
            res = self.capabilities.get(self.primary_cap).invoke(args, state=state)
            if res.success:
                metrics[f"{prefix}_mfe"] = _pick_float(res.output, "mfe")
                metrics[f"{prefix}_structure"] = res.output.get("structure", "")
                metrics[f"{prefix}_fold_tool"] = "LinearFold"
                _trace_capability_call(
                    candidate, self.primary_cap, args, res,
                    step_name=step_name,
                    extra_metrics={k: v for k, v in metrics.items() if k.startswith(prefix)},
                )
            else:
                _LOGGER.warning(
                    "junction_fold_failed prefix=%s error=%s", prefix, res.error
                )
                _trace_capability_call(
                    candidate, self.primary_cap, args, res, step_name=step_name
                )

        # Fallback: ViennaRNA (exact O(n³) when LinearFold unavailable)
        if f"{prefix}_mfe" not in metrics and self.capabilities.has(self.fallback_cap):
            res = self.capabilities.get(self.fallback_cap).invoke(args, state=state)
            if res.success:
                metrics[f"{prefix}_mfe"] = _pick_float(res.output, "mfe_kcal_per_mol")
                metrics[f"{prefix}_structure"] = res.output.get("structure", "")
                metrics[f"{prefix}_fold_tool"] = "ViennaRNA"
                _trace_capability_call(
                    candidate, self.fallback_cap, args, res,
                    step_name=step_name,
                    extra_metrics={k: v for k, v in metrics.items() if k.startswith(prefix)},
                )
            else:
                _trace_capability_call(
                    candidate, self.fallback_cap, args, res, step_name=step_name
                )

        # Length-normalized junction MFE for fair comparison across variable overlaps
        mfe = metrics.get(f"{prefix}_mfe")
        if mfe is not None and len(seq) > 0:
            metrics[f"{prefix}_mfe_per_nt"] = float(mfe) / len(seq)

        # GC diff: compare GC content of the two sides of the actual junction
        # boundary (UTR fragment vs CDS fragment, or CDS fragment vs UTR
        # fragment).  ``split_offset`` is the length of the left-hand fragment
        # (5'UTR for junction_5utr_cds, CDS for junction_cds_3utr).  This is
        # more biologically meaningful than always splitting at the midpoint,
        # especially when one side is shorter than the 20-nt overlap window.
        effective_split = split_offset
        if effective_split is None and cds_start_offset is not None:
            effective_split = cds_start_offset
        if effective_split is None or effective_split <= 0 or effective_split >= len(seq):
            effective_split = len(seq) // 2
        left_gc = self._gc_content(seq[:effective_split])
        right_gc = self._gc_content(seq[effective_split:])
        metrics[f"{prefix}_gc_diff"] = abs(left_gc - right_gc)
        metrics[f"{prefix}_left_gc"] = left_gc
        metrics[f"{prefix}_right_gc"] = right_gc

        return metrics

    def _evaluate_ddg_open(
        self,
        utr5: str,
        cds: str,
        utr3: str,
        candidate: Candidate,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Full-length constrained-fold ddG at the 5'UTR-CDS junction.

        ``ddG_open = MFE_constrained - MFE_unconstrained`` (>= 0 when the
        constraint is obeyed), both folds on the full construct
        ``utr5 + cds + utr3`` via LinearFold. The constraint string is '?'
        over the full length with '.' (forced unpaired) inside the window.
        Two windows are reported (coordinates recorded per candidate):

        - W1 (narrow): [cds_start - 6, cds_start + 9) — 15 nt AUG/Kozak context
        - W2 (wide): [max(0, cds_start - 60), cds_start + 30) — 5'UTR tail
          60 nt + CDS head 30 nt, clipped to the actual UTR length

        The unconstrained full-length MFE reuses the workflow's full fold from
        ``context["full_length_fold"]`` when it was produced by the same
        backend (LinearFold); otherwise one unconstrained fold is run here.
        On any fold failure the ddG fields stay ``None`` (fault-tolerant,
        consistent with the other evaluators).
        """
        if not self.capabilities.has(self.primary_cap):
            return {}

        full = utr5 + cds + utr3
        n = len(full)
        u5 = len(utr5)
        w1s, w1e = max(0, u5 - _DDG_W1_UPSTREAM_NT), min(n, u5 + _DDG_W1_DOWNSTREAM_NT)
        w2s, w2e = max(0, u5 - _DDG_W2_UTR_NT), min(n, u5 + _DDG_W2_CDS_NT)

        metrics: dict[str, Any] = {
            "junction_5utr_cds_ddg_open_w1": None,
            "junction_5utr_cds_ddg_open_w2": None,
            "junction_5utr_cds_ddg_w1_start": w1s,
            "junction_5utr_cds_ddg_w1_end": w1e,
            "junction_5utr_cds_ddg_w2_start": w2s,
            "junction_5utr_cds_ddg_w2_end": w2e,
        }

        state = context.get("workflow_state", {})

        # Reuse the workflow's full-length fold only when it came from the
        # same backend — mixing LinearFold/ViennaRNA MFEs invalidates ddG.
        mfe_un: float | None = None
        reused = context.get("full_length_fold") or {}
        if reused.get("fold_tool") == "LinearFold" and reused.get("mfe") is not None:
            mfe_un = float(reused["mfe"])
        else:
            mfe_un = self._fold_full_mfe(full, candidate, state, tag="unconstrained")
        if mfe_un is None:
            return metrics

        for tag, (s, e) in (("w1", (w1s, w1e)), ("w2", (w2s, w2e))):
            constraints = _ddg_constraint_string(n, s, e)
            mfe_c = self._fold_full_mfe(
                full, candidate, state, constraints=constraints, tag=f"constrained_{tag}"
            )
            if mfe_c is None:
                continue
            metrics[f"junction_5utr_cds_ddg_open_{tag}"] = mfe_c - mfe_un
        return metrics

    def _fold_full_mfe(
        self,
        full_seq: str,
        candidate: Candidate,
        state: dict[str, Any],
        constraints: str | None = None,
        tag: str = "",
    ) -> float | None:
        """One LinearFold call on the full construct; returns MFE or None."""
        seq_fp = save_sequence(
            full_seq, prefix=f"junction_ddg_{tag}_{candidate.id}"
        )
        args: dict[str, Any] = {"filepath": seq_fp}
        if constraints is not None:
            args["constraints"] = constraints
        step_name = f"{candidate.id}_junction_ddg_{tag}_fold"
        try:
            res = self.capabilities.get(self.primary_cap).invoke(args, state=state)
        except Exception as exc:  # noqa: BLE001 - fault-tolerant report metric
            _LOGGER.warning(
                "junction_ddg_fold_error tag=%s error=%s", tag, exc
            )
            return None
        if not res.success:
            _LOGGER.warning(
                "junction_ddg_fold_failed tag=%s error=%s", tag, res.error
            )
            _trace_capability_call(
                candidate, self.primary_cap, args, res, step_name=step_name
            )
            return None
        mfe = _pick_float(res.output, "mfe")
        _trace_capability_call(
            candidate,
            self.primary_cap,
            args,
            res,
            step_name=step_name,
            extra_metrics={f"junction_5utr_cds_ddg_mfe_{tag}": mfe},
        )
        return mfe

    @staticmethod
    def _gc_content(seq: str) -> float:
        if not seq:
            return 0.0
        gc = seq.upper().count("G") + seq.upper().count("C")
        return gc / len(seq)


class CompositeEvaluator(BaseEvaluator):
    """Run a list of evaluators in order and merge their results.

    Each evaluator's output is merged into a single metrics dict.
    Later evaluators can override earlier ones on key collision.
    """

    def __init__(self, evaluators: list[BaseEvaluator]):
        # CompositeEvaluator does not need capabilities directly
        self.evaluators = evaluators

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for evaluator in self.evaluators:
            result = evaluator.evaluate(candidate, context)
            merged.update(result)
        return merged
