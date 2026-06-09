"""RNA secondary structure → sequence design workflow (Layer 2).

Target dot-bracket structure → inverse folding (ViennaRNA RNAinverse) →
fold-back validation (ViennaRNA RNAfold) + GC evaluation → scoring → ranking → WorkflowResult.

Key design principles
---------------------
1. **Structure-first**: The primary objective is finding a sequence that folds
   into the user-provided target secondary structure.
2. **Validation by refolding**: Every designed sequence is folded back with
   ViennaRNA RNAfold to confirm structural fidelity.
3. **Multiple invocations**: Because RNAinverse uses stochastic search, the
   workflow can invoke it multiple times (``num_invocations``) to explore
   different local optima and produce a diverse candidate set.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  RnaSecondaryStructureDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更 ║
║  锁定日期: 2026-05-15 | 测试通过: 67/67 (含 live LLM)                          ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 rna_secondary_structure_design workflow 的权威实现。任何字段增删、  ║
║  函数签名变动、返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试： ║
║                                                                               ║
║    - agent_core/workflows/rna_secondary_structure_design.py  ← 本文件        ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/workflows/__init__.py                                         ║
║    - agent_core/workflows/registry.py                                         ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/planning/base.py                                              ║
║    - agent_core/planning/llm_critic.py                                        ║
║    - agent_core/capabilities/base.py                                          ║
║    - agent_core/capabilities/writebacks.py                                    ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - agent_core/tool_executor.py                                              ║
║    - agent_core/tool_registry.py                                              ║
║    - agent_core/file_manager.py                                               ║
║    - agent_core/sequence_utils.py                                             ║
║    - agent_core/workflow_models.py                                            ║
║    - tests/test_rna_secondary_structure_design.py                             ║
║    - tests/test_rna_secondary_structure_design_layer3.py                      ║
║    - tests/test_rna_secondary_structure_design_full_stack.py                  ║
║    - tests/test_rna_secondary_structure_design_comprehensive.py               ║
║                                                                               ║
║  当前测试状态：全部 67 个 pytest 用例通过（含 1 个 live LLM 测试）。           ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence, save_text_file
from agent_core.sequence_utils import _pick_float
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.evaluators import _trace_capability_call

_LOGGER = logging.getLogger("agent_core.workflows.rna_secondary_structure_design")

# Input model


class RnaSecondaryStructureDesignInput(BaseModel):
    """Input for the RNA secondary-structure-guided sequence design workflow.

    IMPORTANT: The default values below are carefully tuned and battle-tested.
    ONLY override a default parameter when the user explicitly requests a change
    or when you have strong domain-specific justification. Do NOT tweak defaults
    just because they "look like" they could be better.
    """

    model_config = ConfigDict(extra="forbid")

    target_structure: str = Field(
        ...,
        description="Target RNA secondary structure in dot-bracket notation.",
    )
    start_sequence: Optional[str] = Field(
        default=None,
        description=(
            "Optional IUPAC start sequence (same length as target_structure). "
            "'N' means randomizable; other letters are fixed. If omitted, all positions are random."
        ),
    )
    repeats: int = Field(
        default=10,
        ge=1,
        le=500,
        description=(
            "Number of RNAinverse search repeats per invocation. "
            "DEFAULT IS CAREFULLY TUNED — only override if the user explicitly asks for more/less exploration."
        ),
    )
    num_invocations: int = Field(
        default=3,
        ge=1,
        le=10,
        description=(
            "How many independent inverse-fold invocations to run. "
            "Higher values explore more local optima. "
            "DEFAULT IS CAREFULLY TUNED — only override if the user explicitly asks for more/less exploration."
        ),
    )
    temp_c: float = Field(
        default=37.0,
        description=(
            "Temperature in °C for RNAinverse. "
            "DEFAULT IS CAREFULLY TUNED — only override if the user explicitly requests a different temperature."
        ),
    )
    function_mode: Literal["m", "p", "mp"] = Field(
        default="m",
        description=(
            "RNAinverse objective: 'm' = MFE target, 'p' = partition, 'mp' = both. "
            "DEFAULT IS CAREFULLY TUNED — only override if the user explicitly asks for a different objective or if a prior run clearly underperforms."
        ),
    )


# Workflow implementation


class RnaSecondaryStructureDesignWorkflow(
    BaseDomainWorkflow[RnaSecondaryStructureDesignInput, WorkflowResult]
):
    """Design RNA sequences from a target secondary structure.

    Pipeline: ViennaRNA RNAinverse (×N invocations) → GC + RNAfold validation →
    scoring → ranking.
    """

    name = "rna_secondary_structure_design"
    description = (
        "Design RNA sequences that fold into a target secondary structure using "
        "ViennaRNA RNAinverse. Pipeline: inverse folding → GC + fold validation → "
        "scoring → ranking."
    )
    required_capabilities = [
        "inverse_fold_rna_secondary_structure_vienna",
        "predict_rna_secondary_structure",
        "compute_rna_sequence_gc_content",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        inp: Any,
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """Accept either ``RnaSecondaryStructureDesignInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = RnaSecondaryStructureDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._workflow_state["_secondary_design_input"] = inp
        result = super().run(inp, progress_callback=progress_callback)
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: RnaSecondaryStructureDesignInput) -> list[Candidate]:
        """Generate RNA sequence candidates from the target secondary structure.

        Steps:
          1. Write target structure (+ optional start sequence) to a temp file.
          2. Invoke ``inverse_fold_rna_secondary_structure_vienna``
             ``num_invocations`` times.
          3. Deduplicate by sequence and build Candidate objects.
        """
        target = inp.target_structure.strip()
        if not target:
            _LOGGER.error("empty_target_structure")
            return []

        # Build inverse-fold input file: line 1 = structure, line 2 = start sequence (optional)
        start = inp.start_sequence
        if start is not None:
            start = start.strip()
            if len(start) != len(target):
                _LOGGER.error(
                    "start_sequence_length_mismatch target_len=%d start_len=%d",
                    len(target),
                    len(start),
                )
                return []
            file_content = f"{target}\n{start}"
        else:
            file_content = target

        struct_filepath = save_text_file(file_content, prefix="inverse_fold_input", suffix=".txt")

        sequences: list[tuple[str, str, dict[str, Any], Any]] = []  # (seq, source, extra_meta, cap_result)

        if not self.capabilities.has("inverse_fold_rna_secondary_structure_vienna"):
            _LOGGER.error("capability_missing inverse_fold_rna_secondary_structure_vienna")
            return []

        cap = self.capabilities.get("inverse_fold_rna_secondary_structure_vienna")

        for invocation_idx in range(inp.num_invocations):
            try:
                cap_result = cap.invoke(
                    {
                        "filepath": struct_filepath,
                        "repeats": inp.repeats,
                        "temp_c": inp.temp_c,
                        "function_mode": inp.function_mode,
                    },
                    state=self._workflow_state,
                )
                if cap_result.success:
                    seq = str(cap_result.output.get("best_sequence", ""))
                    if seq:
                        meta = {
                            "hamming_distance": cap_result.output.get("hamming_distance"),
                            "partition_probability": cap_result.output.get("partition_probability"),
                            "target_structure": cap_result.output.get("target_structure", target),
                            "invocation_index": invocation_idx,
                        }
                        sequences.append((seq, f"vienna_inverse_{invocation_idx}", meta, cap_result))
                        _LOGGER.info(
                            "inverse_fold_success invocation=%d seq_len=%d hd=%s",
                            invocation_idx,
                            len(seq),
                            meta.get("hamming_distance"),
                        )
                    else:
                        _LOGGER.warning("inverse_fold_empty_sequence invocation=%d", invocation_idx)
                else:
                    _LOGGER.warning(
                        "inverse_fold_failed invocation=%d error=%s",
                        invocation_idx,
                        cap_result.error,
                    )
            except Exception as exc:
                _LOGGER.error("inverse_fold_exception invocation=%d exc=%s", invocation_idx, exc)

        if not sequences:
            _LOGGER.error("no_sequences_generated")
            return []

        # Deduplicate by sequence
        seen: set[str] = set()
        candidates: list[Candidate] = []
        for seq, source, extra_meta, cap_result in sequences:
            if not seq or seq in seen:
                continue
            seen.add(seq)
            cand = Candidate(
                sequence=seq,
                sequence_type="rna",
                source=source,
                metadata={
                    "target_structure": target,
                    "design_tool": "vienna_rnainverse",
                    "tool_metadata": extra_meta,
                },
            )
            _trace_capability_call(
                cand,
                "inverse_fold_rna_secondary_structure_vienna",
                {
                    "filepath": struct_filepath,
                    "repeats": inp.repeats,
                    "temp_c": inp.temp_c,
                    "function_mode": inp.function_mode,
                },
                cap_result,
                step_name=f"inverse_fold_{source}",
            )
            candidates.append(cand)

        _LOGGER.info(
            "candidates_generated total=%d unique=%d workflow=%s",
            len(sequences),
            len(candidates),
            self.name,
        )
        return candidates

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Evaluate a candidate sequence.

        Metrics collected:
          - sequence_length
          - vienna_mfe, folded_structure (RNAfold validation)
          - structure_distance — Hamming distance between folded_structure and target
          - hamming_distance — from inverse-fold output (if available)
        """
        seq = candidate.sequence
        filepath = save_sequence(seq, prefix="secondary_design")
        candidate.metadata["workspace_filepath"] = filepath

        metrics: dict[str, Any] = {
            "sequence_length": len(seq),
        }

        # ── GC content ──
        gc_content: Optional[float] = None
        if self.capabilities.has("compute_rna_sequence_gc_content"):
            gc_args = {"filepath": filepath}
            gc_res = self.capabilities.get("compute_rna_sequence_gc_content").invoke(
                gc_args, state=self._workflow_state
            )
            if gc_res.success:
                gc_content = _pick_float(gc_res.output, "gc_content")
                _trace_capability_call(
                    candidate,
                    "compute_rna_sequence_gc_content",
                    gc_args,
                    gc_res,
                    step_name="gc_content",
                    extra_metrics={"gc_content": gc_content},
                )
            else:
                _LOGGER.warning("gc_eval_failed error=%s", gc_res.error)
                _trace_capability_call(
                    candidate,
                    "compute_rna_sequence_gc_content",
                    gc_args,
                    gc_res,
                    step_name="gc_content",
                )
        metrics["gc_content"] = gc_content

        # ── Secondary structure validation (fold back) ──
        mfe: Optional[float] = None
        folded_structure: Optional[str] = None
        if self.capabilities.has("predict_rna_secondary_structure"):
            try:
                cap = self.capabilities.get("predict_rna_secondary_structure")
                inp = self._workflow_state.get("_secondary_design_input")
                temp_c = getattr(inp, "temp_c", 37.0) if inp is not None else 37.0
                fold_args = {"filepath": filepath, "temp_c": temp_c}
                fold_res = cap.invoke(fold_args, state=self._workflow_state)
                if fold_res.success:
                    mfe = _pick_float(fold_res.output, "mfe_kcal_per_mol")
                    folded_structure = fold_res.output.get("structure")
                    _trace_capability_call(
                        candidate,
                        "predict_rna_secondary_structure",
                        fold_args,
                        fold_res,
                        step_name="fold_validation",
                        extra_metrics={
                            "mfe_kcal_per_mol": mfe,
                            "structure": folded_structure,
                        },
                    )
                else:
                    _LOGGER.warning("fold_eval_failed error=%s", fold_res.error)
                    _trace_capability_call(
                        candidate,
                        "predict_rna_secondary_structure",
                        fold_args,
                        fold_res,
                        step_name="fold_validation",
                    )
            except Exception as exc:
                _LOGGER.warning("fold_eval_exception exc=%s", exc)
        metrics["vienna_mfe"] = mfe
        metrics["folded_structure"] = folded_structure

        # ── Structure distance (Hamming distance on dot-bracket) ──
        target_structure = candidate.metadata.get("target_structure", "")
        structure_distance: Optional[int] = None
        if folded_structure and target_structure:
            if len(folded_structure) == len(target_structure):
                structure_distance = sum(
                    1 for a, b in zip(folded_structure, target_structure) if a != b
                )
            else:
                _LOGGER.warning(
                    "structure_length_mismatch folded=%d target=%d",
                    len(folded_structure),
                    len(target_structure),
                )
        metrics["structure_distance"] = structure_distance

        # ── Hamming distance from inverse-fold tool ──
        tool_meta = candidate.metadata.get("tool_metadata", {})
        metrics["hamming_distance"] = tool_meta.get("hamming_distance")

        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Score candidate using raw metrics (smaller is better).

        Keys:
          - structure_distance_ratio: structure_distance / sequence_length
            (0 = perfect match, 1 = completely different)
          - mfe: raw MFE value (more negative = more stable)
          - total_score: alias for structure_distance_ratio (smaller = better)
        """
        seq_len = metrics.get("sequence_length", 0)
        structure_distance = metrics.get("structure_distance")
        mfe = metrics.get("vienna_mfe")

        scores: dict[str, float] = {}

        if structure_distance is not None and seq_len and seq_len > 0:
            scores["structure_distance_ratio"] = float(structure_distance) / float(seq_len)
        else:
            scores["structure_distance_ratio"] = 1.0

        if mfe is not None:
            scores["mfe"] = float(mfe)

        scores["total_score"] = scores["structure_distance_ratio"]
        return scores

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        """Sort candidates by total score and build a ``WorkflowResult``."""
        if not candidates:
            return self._empty_result("No RNA sequence candidates produced from the target secondary structure.")

        ranked = sort_candidates_by_score(candidates, score_key="total_score", descending=False)
        best = ranked[0] if ranked else None
        inp = self._workflow_state.get("_secondary_design_input")
        target_structure = getattr(inp, "target_structure", "") if inp is not None else ""

        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            line_parts = [
                f"#{i}",
                f"source={c.source}",
                f"len={len(c.sequence)}nt",
                f"GC={mb.get('gc_content'):.3f}" if mb.get("gc_content") is not None else "GC=N/A",
                f"MFE={mb.get('vienna_mfe'):.2f}"
                if mb.get("vienna_mfe") is not None
                else "MFE=N/A",
                f"struc_dist={mb.get('structure_distance')}"
                if mb.get("structure_distance") is not None
                else "struc_dist=N/A",
                f"total_score={scores.get('total_score', 0.0):.4f}",
            ]
            detail_lines.append(" | ".join(line_parts))

        summary_parts = [
            f"target_structure={target_structure}",
            f"candidates={len(ranked)}",
            f"best_total_score={best.scores.get('total_score') if best else None}",
            "---",
            *detail_lines,
        ]
        return WorkflowResult(
            success=True,
            task_id=f"secondary_design_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )


# Standalone scoring helper


def score_secondary_structure_design_candidate(
    metrics: dict[str, Any],
) -> dict[str, float]:
    """Standalone scoring function for secondary-structure-designed candidates.

    Reusable outside the workflow (e.g. in notebooks or downstream analysis).

    Keys:
      - structure_distance_ratio: structure_distance / sequence_length
        (0 = perfect match, 1 = completely different)
      - mfe: raw MFE value (more negative = more stable)
      - total_score: alias for structure_distance_ratio (smaller = better)
    """
    seq_len = metrics.get("sequence_length", 0)
    structure_distance = metrics.get("structure_distance")
    mfe = metrics.get("vienna_mfe")

    scores: dict[str, float] = {}

    if structure_distance is not None and seq_len and seq_len > 0:
        scores["structure_distance_ratio"] = float(structure_distance) / float(seq_len)
    else:
        scores["structure_distance_ratio"] = 1.0

    if mfe is not None:
        scores["mfe"] = float(mfe)

    scores["total_score"] = scores["structure_distance_ratio"]
    return scores


# LLM Critic Configuration

from agent_core.planning.llm_critic import BaseLLMCritic, CriticConfig

RNA_SECONDARY_STRUCTURE_CRITIC_CONFIG = CriticConfig(
    workflow_name="rna_secondary_structure_design",
    workflow_description="Design RNA sequences that fold into a target secondary structure using ViennaRNA RNAinverse",
    evaluation_dimensions=[
        "Structural fidelity is the primary metric. The designed sequence should fold back into the target secondary structure as closely as possible.",
        "Sequence diversity among candidates is important — all candidates should not be identical, which would indicate poor exploration of the sequence space.",
        "MFE (Minimum Free Energy) should indicate reasonable thermodynamic stability. More negative values suggest more stable structures, but excessively negative values may indicate over-stabilization.",
        "Hamming distance from the inverse-fold tool reflects how much the designed sequence deviates from the provided start sequence, if any.",
        "Score semantics: total_score = structure_distance_ratio (distance / length). 0.0 means PERFECT match, 1.0 means completely different. SMALLER is better. mfe is the raw MFE value in kcal/mol; more negative = more stable.",
    ],
    adjustable_params={
        "repeats": {
            "type": "int",
            "hint": "Number of RNAinverse search repeats per invocation. Increase for more candidates and better exploration.",
        },
        "num_invocations": {
            "type": "int",
            "hint": "Number of independent inverse-fold invocations. Higher values explore more local optima.",
        },
        "temp_c": {
            "type": "float",
            "hint": "Temperature in °C for RNAinverse. Adjust if sequences are too stable or unstable.",
        },
        "function_mode": {
            "type": "enum",
            "values": ["m", "p", "mp"],
            "hint": "RNAinverse objective: 'm' = MFE target, 'p' = partition, 'mp' = both. Switch if one mode underperforms.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
)


class RnaSecondaryStructureDesignLLMCritic(BaseLLMCritic):
    """LLM-driven Critic for RNA secondary structure design workflow."""

    def _default_config(self) -> CriticConfig:
        return RNA_SECONDARY_STRUCTURE_CRITIC_CONFIG

    def _build_diagnosis_prompt(self, context: dict[str, Any]) -> list[tuple[str, str]]:
        """Override to inject score interpretation into the user prompt."""
        messages = super()._build_diagnosis_prompt(context)
        score_legend = (
            "\n\n## Score Interpretation (CRITICAL)\n"
            "- total_score = structure_distance_ratio (structure_distance / sequence_length). "
            "0.0 means PERFECT structural match, 1.0 means completely different. SMALLER is better.\n"
            "- mfe = raw MFE value in kcal/mol. More negative = more thermodynamically stable.\n"
            "Do NOT assume total_score follows a 0-1 'higher is better' scale. "
            "A total_score of 0.0 is EXCELLENT, not poor."
        )
        parameter_tuning_guidance = (
            "\n\n## Parameter Tuning Guidance (RNA Secondary Structure Design)\n"
            "The default parameters below are carefully tuned and battle-tested. "
            "Only recommend overrides when you have STRONG evidence that a specific parameter directly caused the issue.\n"
            "- repeats=10: This is an empirically sound value for RNAinverse search repeats. "
            "Only increase if ALL candidates consistently show poor structural fidelity (structure_distance_ratio > 0.3).\n"
            "- num_invocations=3: Sufficient to explore most local optima. "
            "Only increase if candidate sequences show very low diversity (most candidates are identical or nearly identical).\n"
            "- function_mode='m' (MFE target): The most stable and reliable mode. "
            "Do NOT switch to 'p' or 'mp' unless the user explicitly requested partition-function-based design, or MFE mode consistently underperforms across multiple retries.\n"
            "- temp_c=37.0: Standard physiological temperature. "
            "Do NOT change unless the user explicitly requests a different temperature.\n"
            "In short: prefer no parameter changes over speculative adjustments."
        )
        modified = list(messages)
        role, content = modified[-1]
        modified[-1] = (role, content + score_legend + parameter_tuning_guidance)
        return modified


# Backward-compatible alias used by tests and downstream consumers.
RnaSecondaryStructureDesignCritic = RnaSecondaryStructureDesignLLMCritic
