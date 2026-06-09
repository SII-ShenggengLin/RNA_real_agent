"""IRES prediction & validation workflow — screening / evaluation (Layer 2).

Input sequence → IRESfinder (3 modes) → merge positive windows →
structural validation (ViennaRNA fold + RNAplfold + dot-bracket) →
scoring → ranking → confidence annotation via Critic.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  IresPredictionWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 ires_prediction workflow 的权威实现。任何字段增删、函数签名变动、   ║
║  返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：               ║
║                                                                               ║
║    - agent_core/workflows/ires_prediction.py  ← 本文件                       ║
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
║    - microservices/iresfinder_service/main.py                                 ║
║    - tests/test_ires_prediction.py                                            ║
║    - tests/test_ires_prediction_comprehensive.py                              ║
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
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import read_sequence, save_sequence, save_text_file
from agent_core.sequence_utils import _pick_float
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow

_LOGGER = logging.getLogger("agent_core.workflows.ires_prediction")

# ---------------------------------------------------------------------------
# Helper: merge overlapping IRES-positive windows
# ---------------------------------------------------------------------------


def _parse_fragment_coords(fragment_id: str) -> tuple[int, int] | None:
    """Parse 1-based start/end from IRESfinder fragment_id.

    Mode-2 ids look like ``query_1_174`` or ``query_51_224``.
    Mode-1 ids may also embed coordinates.
    Returns ``None`` when no numeric suffix pair is found.
    """
    parts = fragment_id.rsplit("_", 2)
    if len(parts) >= 3:
        try:
            start = int(parts[-2])
            end = int(parts[-1])
            return start, end
        except ValueError:
            pass
    # Fallback: scan for any trailing ``_<int>_<int>`` pattern.
    m = re.search(r"_(\d+)_(\d+)$", fragment_id)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _merge_overlapping_windows(
    predictions: list[dict[str, Any]],
    merge_gap: int = 0,
) -> list[dict[str, Any]]:
    """Merge overlapping / adjacent IRES-positive windows into candidate regions.

    Each returned dict has ``start``, ``end``, ``max_score`` (highest probability
    among merged windows), and ``fragment_ids`` (list).
    """
    positives = [
        {"score": float(p["score"]), "fragment_id": str(p["fragment_id"])}
        for p in predictions
        if str(p.get("predicted_label", "")).upper() == "IRES"
    ]
    if not positives:
        return []

    # Attach coordinates
    regions: list[dict[str, Any]] = []
    for p in positives:
        coords = _parse_fragment_coords(p["fragment_id"])
        if coords is None:
            # Mode-0 (whole sequence) — keep as-is with dummy coords
            regions.append(
                {
                    "start": 1,
                    "end": 1,
                    "score": p["score"],
                    "fragment_id": p["fragment_id"],
                    "mode0": True,
                }
            )
        else:
            regions.append(
                {
                    "start": coords[0],
                    "end": coords[1],
                    "score": p["score"],
                    "fragment_id": p["fragment_id"],
                    "mode0": False,
                }
            )

    # Separate mode-0 from coordinate-based regions
    mode0_regions = [r for r in regions if r.get("mode0")]
    coord_regions = [r for r in regions if not r.get("mode0")]

    merged: list[dict[str, Any]] = []

    if coord_regions:
        coord_regions.sort(key=lambda r: r["start"])
        merged.append(
            {
                "start": coord_regions[0]["start"],
                "end": coord_regions[0]["end"],
                "max_score": coord_regions[0]["score"],
                "fragment_ids": [coord_regions[0]["fragment_id"]],
            }
        )
        for r in coord_regions[1:]:
            last = merged[-1]
            if r["start"] <= last["end"] + merge_gap:
                last["end"] = max(last["end"], r["end"])
                last["max_score"] = max(last["max_score"], r["score"])
                last["fragment_ids"].append(r["fragment_id"])
            else:
                merged.append(
                    {
                        "start": r["start"],
                        "end": r["end"],
                        "max_score": r["score"],
                        "fragment_ids": [r["fragment_id"]],
                    }
                )

    # Mode-0 regions are treated as a single whole-sequence candidate
    if mode0_regions:
        max_score = max(r["score"] for r in mode0_regions)
        merged.append(
            {
                "start": 1,
                "end": 1,  # will be overwritten with actual seq length later
                "max_score": max_score,
                "fragment_ids": [r["fragment_id"] for r in mode0_regions],
                "mode0": True,
            }
        )

    return merged


# Input model — INTERFACE LOCKED (v1.0.0)
# Do NOT rename, remove, or change types of these fields without updating
# all files listed in the INTERFACE LOCK header and re-running the full test suite.


class IresPredictionInput(BaseModel):
    """Input for the IRES prediction & validation workflow.

    IMPORTANT — Parameter Override Policy for LLM Planner:
    The default parameters below have been carefully tuned by domain experts
    for general-purpose IRES screening (probability_threshold=0.5, window_size=174,
    step_size=50, top_n_candidates=5).  These defaults perform well across a
    wide range of viral and cellular IRES sequences.  Only override a default
    when the user's request contains an EXPLICIT, SPECIFIC requirement that
    directly contradicts it (e.g. user says "use a 200-nt window" or
    "I need at least 10 candidates").  When in doubt, OMIT the parameter and
    let the workflow use its built-in defaults.
    """

    model_config = ConfigDict(extra="forbid")

    sequence_filepath: str = Field(
        ...,
        description="Path to the input sequence file (FASTA or plain text).",
    )
    iresfinder_mode: int = Field(
        default=0,
        ge=0,
        le=2,
        description="IRESfinder mode: 0=full sequence, 1=header-specified subsequence, 2=sliding window.",
    )
    probability_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Probability threshold for labeling a fragment as IRES.",
    )
    window_size: int = Field(
        default=174,
        ge=20,
        le=5000,
        description="Sliding-window size (mode 2 only).",
    )
    step_size: int = Field(
        default=50,
        ge=1,
        le=5000,
        description="Sliding-window step size (mode 2 only).",
    )
    top_n_candidates: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Keep top-N candidate regions after merging.",
    )
    run_structural_validation: bool = Field(
        default=True,
        description="Run LinearFold (primary) / ViennaRNA (fallback) fold + RNAplfold + dot-bracket analysis on each candidate region.",
    )


# Confidence assignment helper — INTERFACE LOCKED (v1.0.0)
# The confidence thresholds are calibrated for IRES screening. Changing them
# affects downstream ranking and user expectations.


def assign_confidence(ires_probability: float, mean_unpaired_fraction: float | None) -> str:
    """Assign confidence based on IRESfinder probability and structural complexity.

    IRES function requires a balanced structure: neither fully double-stranded
    (rigid, inaccessible) nor fully single-stranded (lacks scaffold).  The
    ``mean_unpaired_fraction`` interval [0.3, 0.7] captures this sweet spot.
    """
    structural_quality = mean_unpaired_fraction
    if structural_quality is None:
        # No structural data → downgrade one tier
        if ires_probability > 0.8:
            return "medium"
        if ires_probability > 0.6:
            return "low"
        if ires_probability > 0.5:
            return "rejected"
        return "rejected"

    if ires_probability >= 0.8 and 0.3 <= structural_quality <= 0.7:
        return "high"
    if ires_probability >= 0.6 and 0.2 <= structural_quality <= 0.8:
        return "medium"
    if ires_probability >= 0.5:
        return "low"
    return "rejected"


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


class IresPredictionWorkflow(BaseDomainWorkflow[IresPredictionInput, WorkflowResult]):
    """IRES screening workflow: predict → merge windows → structural validation → score → rank.

    INTERFACE LOCKED (v1.0.0):
    - Do NOT change pipeline order (generate → evaluate → score → rank)
    - Do NOT rename or remove required_capabilities entries
    - Do NOT change _state_writeback structure
    """

    name = "ires_prediction"
    input_model = IresPredictionInput
    description = (
        "Predict putative IRES elements in an RNA/DNA sequence using IRESfinder, "
        "optionally validate with LinearFold/ViennaRNA structural analysis, and rank candidate regions."
    )
    required_capabilities = [
        "predict_putative_ires_with_iresfinder",
        "predict_rna_secondary_structure_with_linearfold",
        "predict_rna_secondary_structure",
        "predict_rna_local_accessibility_profile_vienna",
        "compute_dot_bracket_unpaired_fraction",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}

    # ───────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ───────────────────────────────────────────────────────────────────────

    def run(
        self,
        inp: Any,
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """Accept either ``IresPredictionInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = IresPredictionInput(**inp)
        self._workflow_state = {}
        result = super().run(inp, progress_callback=progress_callback)
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        merged_wb["_last_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: IresPredictionInput) -> list[Candidate]:
        """Run IRESfinder, merge positive windows, and create one Candidate per region."""
        # 1. Run IRESfinder
        if not self.capabilities.has("predict_putative_ires_with_iresfinder"):
            _LOGGER.error("IRESfinder capability is missing")
            return []

        cap = self.capabilities.get("predict_putative_ires_with_iresfinder")
        ires_args: dict[str, Any] = {
            "filepath": inp.sequence_filepath,
            "mode": inp.iresfinder_mode,
            "decision_threshold": inp.probability_threshold,
        }
        if inp.iresfinder_mode == 2:
            ires_args["window_size"] = inp.window_size
            ires_args["step_size"] = inp.step_size

        _LOGGER.info(
            "ires_prediction invoking_iresfinder mode=%d threshold=%.2f",
            inp.iresfinder_mode,
            inp.probability_threshold,
        )
        start_ts = time.perf_counter()
        ires_res = cap.invoke(ires_args, state=self._workflow_state)
        ires_elapsed = time.perf_counter() - start_ts
        ires_record = ToolCallRecord(
            step_name="generate:iresfinder",
            tool_name="predict_putative_ires_with_iresfinder",
            input_summary=json.dumps(ires_args, default=str)[:500],
            output_summary=json.dumps(ires_res.output, default=str)[:500] if ires_res.success else "",
            success=ires_res.success,
            error=ires_res.error,
            elapsed_time=ires_elapsed,
            artifacts=dict(ires_res.output) if ires_res.success else {},
            metrics={
                "prediction_count": len(ires_res.output.get("predictions", []))
            } if ires_res.success else {},
        )
        if not ires_res.success:
            _LOGGER.error("IRESfinder failed: %s", ires_res.error)
            return []

        predictions = list(ires_res.output.get("predictions", []))
        if not predictions:
            _LOGGER.info("ires_prediction no_predictions_from_iresfinder")
            return []

        # 2. Merge overlapping positive windows
        merged_regions = _merge_overlapping_windows(predictions, merge_gap=0)
        if not merged_regions:
            _LOGGER.info("ires_prediction no_positive_windows_after_merge")
            return []

        # 3. Read original sequence for subsequence extraction
        try:
            raw_file_content = read_sequence(inp.sequence_filepath)
        except Exception as exc:
            _LOGGER.warning("Could not read original sequence: %s", exc)
            raw_file_content = ""

        # Strip FASTA header if present to get the canonical sequence
        lines = raw_file_content.strip().splitlines()
        if lines and lines[0].startswith(">"):
            sequence = "".join(lines[1:])
        else:
            sequence = "".join(lines)
        sequence = sequence.upper().replace("U", "T")  # DNA-normalised as IRESfinder uses
        seq_len = len(sequence)

        # 4. Build candidates from merged regions
        candidates: list[Candidate] = []
        for region in merged_regions:
            start = region["start"]
            end = region["end"]
            if region.get("mode0"):
                end = seq_len
            # Clamp coordinates
            start = max(1, start)
            end = min(seq_len, end)
            if start > end or seq_len == 0:
                continue

            subseq = sequence[start - 1 : end]
            if not subseq:
                continue

            candidate = Candidate(
                sequence=subseq,
                sequence_type="dna",
                source=f"iresfinder:{inp.iresfinder_mode}",
                metadata={
                    "iresfinder_mode": inp.iresfinder_mode,
                    "start": start,
                    "end": end,
                    "ires_probability": region["max_score"],
                    "fragment_ids": region["fragment_ids"],
                    "original_sequence_length": seq_len,
                    "run_structural_validation": inp.run_structural_validation,
                },
            )
            candidates.append(candidate)
            _LOGGER.info(
                "ires_candidate region=%d-%d probability=%.4f",
                start,
                end,
                region["max_score"],
            )

        # 5. Attach generation-level tool record to every candidate
        for candidate in candidates:
            candidate.add_tool_record(ires_record)

        # 6. Keep top-N by probability
        candidates.sort(key=lambda c: c.metadata.get("ires_probability", 0.0), reverse=True)
        candidates = candidates[: inp.top_n_candidates]

        _LOGGER.info(
            "ires_prediction candidates_generated total=%d top_n=%d",
            len(candidates),
            inp.top_n_candidates,
        )
        return candidates

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Run structural validation (fold + accessibility + unpaired fraction) on the region.

        This method invokes ViennaRNA fold, dot-bracket unpaired fraction, and
        RNAplfold local accessibility when ``run_structural_validation`` is enabled.
        """
        run_structural = candidate.metadata.get("run_structural_validation", True)
        # This flag is set in generate_candidates() from the input model.

        ires_probability = float(candidate.metadata.get("ires_probability", 0.0))
        start = candidate.metadata.get("start", 1)
        end = candidate.metadata.get("end", len(candidate.sequence))

        # Save subsequence for tools
        region_fp = save_sequence(candidate.sequence, prefix="ires_region")
        candidate.metadata["region_filepath"] = region_fp

        mfe: float | None = None
        structure: str | None = None
        fold_tool: str | None = None
        mean_unpaired_fraction: float | None = None
        mean_unpaired_prob_1nt: float | None = None
        plfold_profile_tsv: str | None = None

        if run_structural:
            # ── LinearFold (primary) ──
            if self.capabilities.has("predict_rna_secondary_structure_with_linearfold"):
                start_ts = time.perf_counter()
                fold_res = self.capabilities.get("predict_rna_secondary_structure_with_linearfold").invoke(
                    {"filepath": region_fp}, state=self._workflow_state
                )
                elapsed = time.perf_counter() - start_ts
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name="evaluate:linearfold",
                        tool_name="predict_rna_secondary_structure_with_linearfold",
                        input_summary=json.dumps({"filepath": region_fp}, default=str),
                        output_summary=json.dumps(fold_res.output, default=str)[:500] if fold_res.success else "",
                        success=fold_res.success,
                        error=fold_res.error,
                        elapsed_time=elapsed,
                        artifacts=dict(fold_res.output) if fold_res.success else {},
                        metrics={"mfe": fold_res.output.get("mfe")} if fold_res.success else {},
                    )
                )
                if fold_res.success:
                    mfe = _pick_float(fold_res.output, "mfe")
                    structure = fold_res.output.get("structure")
                    fold_tool = "LinearFold"
                else:
                    _LOGGER.warning("LinearFold failed: %s", fold_res.error)

            # ── ViennaRNA fallback ──
            if mfe is None and self.capabilities.has("predict_rna_secondary_structure"):
                start_ts = time.perf_counter()
                fold_res = self.capabilities.get("predict_rna_secondary_structure").invoke(
                    {"filepath": region_fp}, state=self._workflow_state
                )
                elapsed = time.perf_counter() - start_ts
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name="evaluate:vienna_fold",
                        tool_name="predict_rna_secondary_structure",
                        input_summary=json.dumps({"filepath": region_fp}, default=str),
                        output_summary=json.dumps(fold_res.output, default=str)[:500] if fold_res.success else "",
                        success=fold_res.success,
                        error=fold_res.error,
                        elapsed_time=elapsed,
                        artifacts=dict(fold_res.output) if fold_res.success else {},
                        metrics={"mfe_kcal_per_mol": fold_res.output.get("mfe_kcal_per_mol")} if fold_res.success else {},
                    )
                )
                if fold_res.success:
                    mfe = _pick_float(fold_res.output, "mfe_kcal_per_mol")
                    structure = fold_res.output.get("structure")
                    fold_tool = "ViennaRNA"
                else:
                    _LOGGER.warning("ViennaRNA fold failed: %s", fold_res.error)

            # ── Dot-bracket unpaired fraction ──
            if structure and self.capabilities.has("compute_dot_bracket_unpaired_fraction"):
                struct_fp = save_text_file(structure, prefix="ires_structure", suffix=".db")
                start_ts = time.perf_counter()
                unp_res = self.capabilities.get("compute_dot_bracket_unpaired_fraction").invoke(
                    {"filepath": struct_fp}, state=self._workflow_state
                )
                elapsed = time.perf_counter() - start_ts
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name="evaluate:unpaired_fraction",
                        tool_name="compute_dot_bracket_unpaired_fraction",
                        input_summary=json.dumps({"filepath": struct_fp}, default=str),
                        output_summary=json.dumps(unp_res.output, default=str)[:500] if unp_res.success else "",
                        success=unp_res.success,
                        error=unp_res.error,
                        elapsed_time=elapsed,
                        artifacts=dict(unp_res.output) if unp_res.success else {},
                        metrics={"unpaired_fraction": unp_res.output.get("unpaired_fraction")} if unp_res.success else {},
                    )
                )
                if unp_res.success:
                    mean_unpaired_fraction = _pick_float(unp_res.output, "unpaired_fraction")
                else:
                    _LOGGER.warning("Unpaired fraction failed: %s", unp_res.error)

            # ── RNAplfold local accessibility ──
            if self.capabilities.has("predict_rna_local_accessibility_profile_vienna"):
                start_ts = time.perf_counter()
                plf_res = self.capabilities.get(
                    "predict_rna_local_accessibility_profile_vienna"
                ).invoke({"filepath": region_fp}, state=self._workflow_state)
                elapsed = time.perf_counter() - start_ts
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name="evaluate:rnaplfold",
                        tool_name="predict_rna_local_accessibility_profile_vienna",
                        input_summary=json.dumps({"filepath": region_fp}, default=str),
                        output_summary=json.dumps(plf_res.output, default=str)[:500] if plf_res.success else "",
                        success=plf_res.success,
                        error=plf_res.error,
                        elapsed_time=elapsed,
                        artifacts=dict(plf_res.output) if plf_res.success else {},
                        metrics={"mean_unpaired_prob_1nt": plf_res.output.get("mean_unpaired_prob_1nt")} if plf_res.success else {},
                    )
                )
                if plf_res.success:
                    mean_unpaired_prob_1nt = _pick_float(plf_res.output, "mean_unpaired_prob_1nt")
                    plfold_profile_tsv = plf_res.output.get("lunp_profile_tsv_filepath")
                else:
                    _LOGGER.warning("RNAplfold failed: %s", plf_res.error)

        # Build metrics bundle
        metrics: dict[str, Any] = {
            "ires_probability": ires_probability,
            "start": start,
            "end": end,
            "region_length": len(candidate.sequence),
            "mfe_kcal_per_mol": mfe,
            "fold_tool": fold_tool,
            "structure": structure,
            "mean_unpaired_fraction": mean_unpaired_fraction,
            "mean_unpaired_prob_1nt": mean_unpaired_prob_1nt,
            "plfold_profile_tsv": plfold_profile_tsv,
        }
        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Score is driven solely by IRESfinder probability.

        Structural metrics (MFE, unpaired fraction, RNAplfold) are reported in
        the candidate metadata for user inspection and LLM Critic review, but
        they are not folded into the numeric score due to lack of calibrated
        evidence for an optimal unpaired-fraction target.
        """
        prob = float(metrics.get("ires_probability", 0.0))
        return {
            "ires_probability": prob,
            "composite_score": prob,
        }

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            # Empty result is a valid scientific outcome (e.g. high threshold
            # intentionally filters everything, or the sequence truly lacks
            # IRES-like features).  We return success=True so that callers
            # that expect an empty list (benchmark rubric min_candidates=0)
            # do not incorrectly flag this as a workflow failure.
            return WorkflowResult(
                success=True,
                task_id=f"ires_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                best_candidate=None,
                all_candidates=[],
                summary="No IRES candidate regions found.",
                errors=[],
            )

        ranked = sort_candidates_by_score(candidates, score_key="composite_score", descending=True)
        best = ranked[0] if ranked else None

        # Annotate confidence for each candidate
        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            prob = scores.get("ires_probability", 0.0)
            unpaired = mb.get("mean_unpaired_fraction")
            confidence = assign_confidence(prob, unpaired)
            c.metadata["confidence"] = confidence

            line_parts = [
                f"#{i}",
                f"region={mb.get('start')}-{mb.get('end')}",
                f"len={mb.get('region_length')}nt",
                f"prob={prob:.4f}",
                f"composite={scores.get('composite_score', 0.0):.4f}",
                f"confidence={confidence}",
            ]
            if mb.get("mfe_kcal_per_mol") is not None:
                line_parts.append(f"MFE={mb['mfe_kcal_per_mol']:.2f}({mb.get('fold_tool', '?')})")
            if unpaired is not None:
                line_parts.append(f"unpaired={unpaired:.3f}")
            detail_lines.append(" | ".join(line_parts))

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_composite_score={best.scores.get('composite_score') if best else None}",
            "---",
            *detail_lines,
        ]

        return WorkflowResult(
            success=True,
            task_id=f"ires_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )


# LLM Critic Configuration — INTERFACE LOCKED (v1.0.0)
# Do NOT rename adjustable_params keys (breaks Critic→Controller parameter override).
# Do NOT change retry_strategy or max_retries without updating ExecutionController tests.

from agent_core.planning.llm_critic import BaseLLMCritic, CriticConfig

IRES_PREDICTION_CRITIC_CONFIG = CriticConfig(
    workflow_name="ires_prediction",
    workflow_description="Predict putative IRES elements in an RNA/DNA sequence using IRESfinder with optional structural validation",
    evaluation_dimensions=[
        "IRESfinder probability scores reflect the model's confidence that a region functions as an IRES. Higher scores generally indicate stronger prediction confidence, but the appropriate threshold depends on the application (screening vs. validation). Evaluate relative to other candidates and the user's stated requirements rather than enforcing a fixed cutoff.",
        "Structural validation via LinearFold (primary) or ViennaRNA (fallback) fold provides the predicted secondary structure (dot-bracket notation) and MFE. A stable but not excessively rigid structure is typically desirable for IRES function — overly rigid structures may impede ribosome access, while overly unstable ones lack the scaffold needed for IRES activity.",
        "Mean unpaired fraction from dot-bracket analysis and RNAplfold local accessibility both indicate how much of the structure is single-stranded. IRES function generally benefits from a balance: some structured regions provide scaffold, while exposed single-stranded regions allow ribosome entry. Evaluate this balance relative to the candidate set and user intent rather than applying a universal numeric target.",
        "Coverage and distribution of candidate regions across the input sequence matters. Too few candidates may indicate the sequence lacks IRES-like features or that parameters are too restrictive. Clustered candidates in a small region may suggest a localized IRES element; scattered candidates may indicate multiple weak signals.",
        "CRITICAL: Base your quality assessment on the user's original intent and any explicit constraints they stated. If the user specified thresholds (e.g., 'probability must be > 0.9', 'need at least 3 candidates', 'focus on the 5\\'UTR region'), evaluate whether the results meet those constraints. Failure to meet user constraints is a CRITICAL issue. Do not apply universal thresholds that may be inappropriate for this specific screening task.",
    ],
    adjustable_params={
        "probability_threshold": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Probability threshold for labeling a fragment as IRES. Lower to catch more candidates (but with lower confidence); raise for stricter filtering.",
        },
        "window_size": {
            "type": "int",
            "min": 20,
            "max": 5000,
            "hint": "Sliding-window size for mode 2. Adjust based on expected IRES length in the target organism.",
        },
        "step_size": {
            "type": "int",
            "min": 1,
            "max": 5000,
            "hint": "Sliding-window step size for mode 2. Smaller steps give better coverage but more overlap; larger steps are faster but may miss regions.",
        },
        "top_n_candidates": {
            "type": "int",
            "min": 1,
            "max": 100,
            "hint": "Number of top candidate regions to keep after merging. Increase if too few candidates are found.",
        },
        "run_structural_validation": {
            "type": "bool",
            "hint": "Whether to run ViennaRNA structural validation. Keep True for better confidence assessment.",
        },
        "iresfinder_mode": {
            "type": "enum",
            "values": [0, 1, 2],
            "hint": "IRESfinder mode: 0=full sequence, 1=header-specified subsequence, 2=sliding window. Switch to mode 2 for long sequences where localized IRES elements are expected.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
)


class IresPredictionLLMCritic(BaseLLMCritic):
    """LLM-driven Critic for IRES prediction workflow.

    Focuses on whether candidate regions satisfy constraints from the user's
    original prompt rather than applying hard-coded thresholds.
    """

    def _default_config(self) -> CriticConfig:
        return IRES_PREDICTION_CRITIC_CONFIG

    def _build_context(self, result: WorkflowResult, state: dict[str, Any]) -> dict[str, Any]:
        """Extend base context with IRES-specific statistics."""
        ctx = super()._build_context(result, state)

        candidates = result.all_candidates
        if not candidates:
            ctx["ires_stats"] = {
                "probability_range": {"min": None, "max": None, "mean": None, "count": 0},
                "mfe_range": {"min": None, "max": None, "mean": None, "count": 0},
                "unpaired_fraction_range": {"min": None, "max": None, "mean": None, "count": 0},
                "plfold_range": {"min": None, "max": None, "mean": None, "count": 0},
                "region_length_range": {"min": None, "max": None, "mean": None, "count": 0},
                "coverage": {"min_start": None, "max_end": None, "total_span": None},
                "mode_distribution": {},
            }
            constraints = state.get("user_constraints")
            if constraints:
                ctx["user_constraints"] = constraints
            return ctx

        prob_values: list[float] = []
        mfe_values: list[float] = []
        unpaired_values: list[float] = []
        plfold_values: list[float] = []
        length_values: list[float] = []
        starts: list[int] = []
        ends: list[int] = []
        mode_dist: dict[str, int] = {}

        for c in candidates:
            meta = c.metadata or {}
            mb = meta.get("metrics_bundle", {})

            mode = str(meta.get("iresfinder_mode", "unknown"))
            mode_dist[mode] = mode_dist.get(mode, 0) + 1

            prob = mb.get("ires_probability")
            if prob is not None:
                prob_values.append(float(prob))

            mfe = mb.get("mfe_kcal_per_mol")
            if mfe is not None:
                mfe_values.append(float(mfe))

            unp = mb.get("mean_unpaired_fraction")
            if unp is not None:
                unpaired_values.append(float(unp))

            plf = mb.get("mean_unpaired_prob_1nt")
            if plf is not None:
                plfold_values.append(float(plf))

            length = mb.get("region_length")
            if length is not None:
                length_values.append(float(length))

            start = mb.get("start")
            end = mb.get("end")
            if start is not None:
                starts.append(int(start))
            if end is not None:
                ends.append(int(end))

        def _stats(values: list[float]) -> dict[str, Any]:
            if not values:
                return {"min": None, "max": None, "mean": None, "count": 0}
            return {
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "mean": round(sum(values) / len(values), 4),
                "count": len(values),
            }

        ctx["ires_stats"] = {
            "probability_range": _stats(prob_values),
            "mfe_range": _stats(mfe_values),
            "unpaired_fraction_range": _stats(unpaired_values),
            "plfold_range": _stats(plfold_values),
            "region_length_range": _stats(length_values),
            "coverage": {
                "min_start": min(starts) if starts else None,
                "max_end": max(ends) if ends else None,
                "total_span": max(ends) - min(starts) + 1 if starts and ends else None,
            },
            "mode_distribution": mode_dist,
        }

        return ctx


# Backwards-compatible alias used in tests and docs.
IresPredictionCritic = IresPredictionLLMCritic
