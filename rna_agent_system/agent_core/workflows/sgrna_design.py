"""sgRNA handle design workflow (Layer 2).

Pipeline: CRGPT handle design → CRGPT re-score + optional CRISOT off-target
score → scoring (nn_score + crisot_score) → ranking → WorkflowResult.

"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import read_sequence, save_sequence
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflow_run_storage import build_public_summary
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.calibrated.objective_assembly import (
    ObjectiveRef,
    assemble_for_workflow,
)
from agent_core.workflows.multi_objective import apply_reference_point_ranking
from agent_core.workflows.evaluators import (
    CRGPTEvaluator,
    CRISOTEvaluator,
    CRISOTSpecificityEvaluator,
    CompositeEvaluator,
)

_LOGGER = logging.getLogger("agent_core.workflows.sgrna_design")

# Ranking governance (DECISIONS (p)): oracle-backed objectives.
# ``crisot_specificity_component`` comes from the aggregate CRISOT
# specificity service (ToolKind.compute), so it never enters the mechanism.
_ORACLE_BACKED_OBJECTIVES: dict[str, ObjectiveRef] = {
    "nn_component": ObjectiveRef(
        dim="nn_component",
        tool_name="score_sgrna_handle_with_crgpt",
        oracle_id="crgpt_handle_score",
    ),
    "crisot_component": ObjectiveRef(
        dim="crisot_component",
        tool_name="score_crispr_off_target_with_crisot",
        oracle_id="crisot_off_target_score",
    ),
}

# Input model


class SgRnaDesignInput(BaseModel):
    """Input for the sgRNA handle design workflow.

    IMPORTANT — default parameters are carefully tuned for general sgRNA handle
    design. Only override them when you have a strong, domain-specific reason
    (e.g. the user explicitly requests more candidates, a specific mutation
    budget, or a different exploration strategy). In most cases, accepting the
    defaults will yield good results.
    """
    # Tool-level parameter overrides (from tools_parameter_analysis.json)
    crgpt_design_seed_sequence: str = Field(default=None, description="[crgpt_design] seed_sequence: Inline seed/wildtype sgRNA handle sequence (DNA or RNA letters). Exactly one of seed_sequence or filepath must be provided.")
    crgpt_design_filepath: str = Field(default=None, description="[crgpt_design] filepath: Path to a file containing the seed sgRNA handle sequence. Exactly one of seed_sequence or filepath must be provided.")
    crgpt_design_n_samples: int = Field(default=10, description="[crgpt_design] n_samples: Number of designed candidate sequences to generate (excluding the wild-type seed).")
    crgpt_design_mutation_number: int = Field(default=22, description="[crgpt_design] mutation_number: Maximum number of mutations allowed relative to the seed sequence (range 1-40).")
    crgpt_design_temperature: Any = Field(default=None, description="[crgpt_design] temperature: For mcmc mode: MCMC annealing temperature controlling acceptance of structure-distance-increasing mutations (defaults to 20.0). For naive mode: transformer sampling temperature (defaults to 1.0).")
    crgpt_design_max_length: Any = Field(default=None, description="[crgpt_design] max_length: Optional target sequence length for naive mode. It overrides the auto-computed max_new_tokens.")
    crgpt_design_max_overlap: int = Field(default=21, description="[crgpt_design] max_overlap: Maximum longest-common-substring overlap allowed among accepted candidate sequences (range 1-60).")
    crgpt_design_sampling_mode: str = Field(default='mcmc', description="[crgpt_design] sampling_mode: Sampling strategy: 'mcmc' (original MCMC/annealing with ViennaRNA structure constraints) or 'naive' (direct GPT-2 model.generate sampling).")
    crgpt_design_path_to_model: str = Field(default=None, description="[crgpt_design] path_to_model: Optional model directory (relative to sgrna_design root or absolute path).")
    crgpt_design_device: str = Field(default=None, description="[crgpt_design] device: Optional torch device override such as 'cuda:0' or 'cpu'. Defaults to SGRNA_DESIGN_DEVICE env var or cuda:0 if available.")
    crgpt_design_output_dir: str = Field(default=None, description="[crgpt_design] output_dir: Optional output directory override for FASTA/JSON artifacts. Defaults to workspace/sgrna_design_service.")
    crgpt_design_service_url: str = Field(default='http://127.0.0.1:8017/design', description="[crgpt_design] service_url: REST endpoint of the sgRNA design microservice.")
    crgpt_score_sequence: str = Field(default=None, description="[crgpt_score] sequence: sgRNA handle sequence to score (DNA or RNA letters). It is normalized to uppercase DNA and fixed positions are enforced before scoring.")
    crgpt_score_path_to_model: str = Field(default=None, description="[crgpt_score] path_to_model: Optional model directory override.")
    crgpt_score_device: str = Field(default=None, description="[crgpt_score] device: Optional torch device override such as 'cuda:0' or 'cpu'.")
    crgpt_score_service_url: str = Field(default='http://127.0.0.1:8017/score', description="[crgpt_score] service_url: REST endpoint of the sgRNA scoring microservice.")
    crisot_filepath: str = Field(default=None, description="[crisot] filepath: Path to a file containing the sgRNA sequence (23 nt including NGG PAM). The wrapper reads the sequence from this file rather than accepting it inline.")
    crisot_target_sequence: str = Field(default=None, description="[crisot] target_sequence: Target DNA sequence (23 nt including NGG PAM) paired with the sgRNA. Both sequences are normalized to uppercase DNA before scoring.")
    crisot_service_url: str = Field(default='http://127.0.0.1:8011/score', description="[crisot] service_url: REST endpoint of the CRISOT score microservice. Pure routing parameter for the wrapper.")
    crisot_ref_genome: str = Field(default=None, description="[crisot] ref_genome: Optional reference genome path accepted by the microservice request model. Not exposed by the agent wrapper. It is passed to the CRISOT constructor but is not used during single-pair scoring.")
    seed_sequence: Optional[str] = Field(
        default=None,
        description="Inline sgRNA handle seed sequence (DNA/RNA, 40–120 nt).",
    )
    seed_filepath: Optional[str] = Field(
        default=None,
        description="Filepath containing the seed sgRNA handle sequence.",
    )
    guide_sequence: Optional[str] = Field(
        default=None,
        description="Optional 23-nt guide sequence for CRISOT off-target scoring.",
    )
    target_sequence: Optional[str] = Field(
        default=None,
        description="Optional 23-nt target sequence for CRISOT off-target scoring.",
    )
    n_samples: int = Field(
        default=10,
        ge=1,
        le=200,
        description="Number of candidates to generate. Default 10 is sufficient for most cases. Only increase if the user explicitly asks for more exploration.",
    )
    mutation_number: int = Field(
        default=22,
        ge=1,
        le=40,
        description="Maximum mutation count relative to seed. Default 22 is well-balanced. Only change if the user has a specific structural constraint.",
    )
    temperature: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=100.0,
        description="MCMC annealing temperature (mcmc mode, default 20.0) or transformer sampling temperature (naive mode, default 1.0). Defaults are tuned for good diversity/quality trade-off. Only override if the user explicitly requests hotter/colder sampling.",
    )
    sampling_mode: str = Field(
        default="mcmc",
        description="'mcmc' (recommended, better exploration) or 'naive' (faster, direct sampling). Stick with 'mcmc' unless the user specifically requests naive mode.",
    )
    max_overlap: int = Field(
        default=21,
        ge=1,
        le=60,
        description="Maximum longest-common-substring overlap among accepted candidates. Default 21 controls diversity well. Only change for specific diversity requirements.",
    )
    max_length: Optional[int] = Field(
        default=None,
        ge=1,
        le=120,
        description="Optional target sequence length for naive mode (overrides auto-computed max_new_tokens).",
    )
    evaluate_crgpt_score: bool = Field(
        default=True,
        description="Re-score each candidate with the CRGPT scoring endpoint. Should almost always stay True.",
    )
    evaluate_crisot: bool = Field(
        default=True,
        description="Score guide-target pair with CRISOT if guide_sequence and target_sequence are provided. Should stay True when guide/target are available.",
    )
    weight_nn_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for CRGPT nn_score in composite scoring. Default 0.5 balances on-target activity and off-target safety. Only adjust if the user explicitly prioritizes one over the other.",
    )
    weight_crisot: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for CRISOT score in composite scoring. Default 0.5 balances on-target activity and off-target safety. Only adjust if the user explicitly prioritizes one over the other.",
    )
    off_target_sequences: list[str] = Field(
        default_factory=list,
        description="Optional candidate off-target DNA sequences (23 nt including NGG PAM). When non-empty and the CRISOT service is reachable, the workflow additionally computes the aggregate CRISOT-Spec genome-context specificity (crisot_specificity component). Empty (default) leaves workflow behaviour unchanged.",
    )
    weight_crisot_specificity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for the CRISOT-Spec specificity component when off_target_sequences is provided. Inactive while the list is empty.",
    )

def score_sgrna_candidate(
    metrics: dict[str, Any],
    weights: dict[str, float],
) -> dict[str, float]:
    """Turn raw sgRNA metrics into normalized score components.

    Components (each in [0, 1]):
      - nn_component:      1 / nn_score  (perplexity lower is better)
      - crisot_component:  crisot_score clamped to [0,1]

    total_score is a weighted average of the two components.
    """
    nn_score = metrics.get("nn_score") or metrics.get("design_nn_score")
    crisot_score = metrics.get("crisot_score")

    scores: dict[str, float] = {}

    if nn_score is not None:
        # nn_score is perplexity (exp(cross_entropy_loss)), range ~[1, +inf).
        # Lower perplexity = model is more familiar with the sequence = better.
        # Map via reciprocal so higher component = better quality.
        scores["nn_component"] = max(0.0, min(1.0, 1.0 / float(nn_score)))
    else:
        scores["nn_component"] = 0.0

    if crisot_score is not None:
        scores["crisot_component"] = max(0.0, min(1.0, float(crisot_score)))
    else:
        scores["crisot_component"] = 0.0

    # Aggregate genome-context specificity (only present when the input
    # supplied off_target_sequences and the CRISOT spec call succeeded).
    crisot_specificity = metrics.get("crisot_specificity")
    if crisot_specificity is not None:
        scores["crisot_specificity_component"] = max(0.0, min(1.0, float(crisot_specificity)))

    active_weights = 0.0
    weighted_sum = 0.0
    for key, weight in weights.items():
        comp_key = f"{key}_component"
        if comp_key in scores:
            active_weights += weight
            weighted_sum += weight * scores[comp_key]

    if active_weights > 0:
        scores["total_score"] = weighted_sum / active_weights
    else:
        scores["total_score"] = 0.0

    return scores


# Workflow


class SgRnaDesignWorkflow(BaseDomainWorkflow[SgRnaDesignInput, WorkflowResult]):
    input_model = SgRnaDesignInput
    """sgRNA handle design using CRGPT.

    Pipeline: generate candidates (CRGPT) → evaluate (CRGPT re-score +
    optional CRISOT) → score (nn_score + crisot_score) → rank → WorkflowResult.
    """

    name = "sgrna_design"
    task_type = "sgrna_design"
    description = (
        "Design sgRNA handle candidates using CRGPT. Pipeline: generate → "
        "evaluate (CRGPT re-score + optional CRISOT) → score → rank."
    )
    # NOTE: Listed capabilities are runtime-optional; the workflow checks
    # ``capabilities.has()`` before each invocation and degrades gracefully.
    required_capabilities = [
        "design_sgrna_handle_with_crgpt",    # mandatory for candidate generation
        "score_sgrna_handle_with_crgpt",     # optional re-scoring
        "score_crispr_off_target_with_crisot",  # optional CRISOT off-target
        "calculate_crispr_specificity_with_crisot",  # optional aggregate CRISOT-Spec
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._trace_logs: list[ToolCallRecord] = []
        self.evaluator = CompositeEvaluator([
            CRGPTEvaluator(self.capabilities),
            CRISOTEvaluator(self.capabilities),
            CRISOTSpecificityEvaluator(self.capabilities),
        ])

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        inp: Any,
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """Accept ``SgRnaDesignInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = SgRnaDesignInput(**inp)
        self._workflow_state = {"_sgrna_input": inp}
        self._trace_logs = []
        result = super().run(inp, progress_callback=progress_callback)
        result.trace = self._collect_trace(result.all_candidates)
        result.completed_at = datetime.now(timezone.utc)
        result.public_summary = build_public_summary(result)
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: SgRnaDesignInput) -> list[Candidate]:
        """Generate sgRNA handle candidates via CRGPT design endpoint."""
        if not self.capabilities.has("design_sgrna_handle_with_crgpt"):
            _LOGGER.error("capability_missing design_sgrna_handle_with_crgpt")
            return []

        args: dict[str, Any] = {
            "n_samples": inp.n_samples,
            "mutation_number": inp.mutation_number,
            "sampling_mode": inp.sampling_mode,
            "max_overlap": inp.max_overlap,
        }
        if inp.seed_sequence:
            args["seed_sequence"] = inp.seed_sequence
        elif inp.seed_filepath:
            args["filepath"] = inp.seed_filepath
        else:
            _LOGGER.error("sgrna_design_no_seed")
            return []
        if inp.temperature is not None:
            args["temperature"] = inp.temperature
        if inp.max_length is not None:
            args["max_length"] = inp.max_length

        try:
            cap = self.capabilities.get("design_sgrna_handle_with_crgpt")
            cap_result = cap.invoke(args, state=self._workflow_state)
        except Exception as exc:
            _LOGGER.error("sgrna_design_exception err=%s", exc)
            return []

        if not cap_result.success:
            _LOGGER.error("sgrna_design_failed error=%s", cap_result.error)
            return []

        # Read summary JSON to obtain the full candidate list
        summary_path = cap_result.output.get("summary_json_filepath", "")
        candidates_data: list[dict[str, Any]] = []
        if summary_path:
            try:
                raw = read_sequence(summary_path)
                summary = json.loads(raw)
                candidates_data = summary.get("candidates", [])
            except Exception as exc:
                _LOGGER.warning("sgrna_summary_read_failed path=%s err=%s", summary_path, exc)

        if not candidates_data:
            # Fallback to best_sequence only
            best_seq = cap_result.output.get("best_sequence", "")
            if best_seq:
                candidates_data = [
                    {
                        "name": "best",
                        "sequence": best_seq,
                        "nn_score": cap_result.output.get("best_nn_score", 0.0),
                        "mutation_count": cap_result.output.get("best_mutation_count", 0),
                    }
                ]
            else:
                _LOGGER.warning("sgrna_design_empty_results")
                return []

        # Record generation-phase tool invocation
        gen_record = ToolCallRecord(
            step_name="generate_candidates",
            tool_name="design_sgrna_handle_with_crgpt",
            input_summary=json.dumps(args, ensure_ascii=True, default=str),
            output_summary=json.dumps(
                cap_result.output if cap_result.success else {"error": cap_result.error},
                ensure_ascii=True,
                default=str,
            )[:500],
            success=cap_result.success,
            error=cap_result.error,
            elapsed_time=cap_result.elapsed_time,
            artifacts={"output": cap_result.output} if cap_result.success else {},
            metrics={"candidate_count": len(candidates_data)} if cap_result.success else {},
        )
        self._trace_logs.append(gen_record)

        candidates: list[Candidate] = []
        seen: set[str] = set()
        wild_record: Optional[dict[str, Any]] = None
        for record in candidates_data:
            seq = str(record.get("sequence", "")).upper().replace("U", "T")
            if not seq or seq in seen:
                continue
            if record.get("name") == "wild":
                wild_record = record
                continue
            seen.add(seq)
            candidates.append(
                Candidate(
                    sequence=seq,
                    sequence_type="sgrna",
                    source=f"crgpt:{record.get('name', 'unknown')}",
                    metadata={
                        "design_nn_score": float(record.get("nn_score", 0.0)),
                        "design_mutation_count": int(record.get("mutation_count", 0)),
                        "design_log_likelihood": record.get("log_likelihood"),
                        "design_structure_distance": record.get("structure_distance"),
                        "design_mfe": record.get("mfe"),
                        "sampling_mode": inp.sampling_mode,
                        "seed_sequence": cap_result.output.get("normalized_seed", ""),
                        "evaluate_crgpt_score": inp.evaluate_crgpt_score,
                    },
                )
            )

        # Fallback: if no designed variants were accepted under strict
        # constraints, keep the wild-type seed so the workflow does not
        # return an empty candidate list (which would be marked as failure).
        if not candidates and wild_record is not None:
            seq = str(wild_record.get("sequence", "")).upper().replace("U", "T")
            if seq:
                candidates.append(
                    Candidate(
                        sequence=seq,
                        sequence_type="sgrna",
                        source="crgpt:wild",
                        metadata={
                            "design_nn_score": float(wild_record.get("nn_score", 0.0)),
                            "design_mutation_count": int(wild_record.get("mutation_count", 0)),
                            "design_log_likelihood": wild_record.get("log_likelihood"),
                            "design_structure_distance": wild_record.get("structure_distance"),
                            "design_mfe": wild_record.get("mfe"),
                            "sampling_mode": inp.sampling_mode,
                            "seed_sequence": cap_result.output.get("normalized_seed", ""),
                            "evaluate_crgpt_score": inp.evaluate_crgpt_score,
                        },
                    )
                )

        _LOGGER.info(
            "sgrna_candidates_generated total=%d unique=%d",
            len(candidates_data),
            len(candidates),
        )
        return candidates

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Re-score candidate with CRGPT and optionally CRISOT off-target scoring."""
        seq = candidate.sequence
        filepath = save_sequence(seq, prefix="sgrna")
        candidate.metadata["workspace_filepath"] = filepath

        context: dict[str, Any] = {
            "workflow_state": self._workflow_state,
            "workflow_input": self._workflow_state.get("_sgrna_input"),
        }
        metrics = self.evaluator.evaluate(candidate, context)
        metrics["sequence_length"] = len(seq)
        metrics["design_nn_score"] = candidate.metadata.get("design_nn_score")
        metrics["design_mutation_count"] = candidate.metadata.get("design_mutation_count")

        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Compute weighted score from nn_score and crisot_score components."""
        inp = self._workflow_state.get("_sgrna_input")
        weights = {
            "nn": float(getattr(inp, "weight_nn_score", 0.5)) if inp else 0.5,
            "crisot": float(getattr(inp, "weight_crisot", 0.5)) if inp else 0.5,
            "crisot_specificity": float(getattr(inp, "weight_crisot_specificity", 0.3)) if inp else 0.3,
        }
        return score_sgrna_candidate(metrics, weights)

    def _collect_trace(self, candidates: list[Candidate]) -> list[ToolCallRecord]:
        """Aggregate tool records from generation phase and every candidate."""
        trace: list[ToolCallRecord] = list(self._trace_logs)
        for c in candidates:
            trace.extend(c.tool_records)
        return trace

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return self._empty_result("No sgRNA handle candidates produced.")

        # ASF reference-point ranking over the per-objective components
        # (replaces the weighted-sum ordering; total_score stays as a reported
        # diagnostic — ASF audit 2026-08-20). 0.0-filled components whose
        # source metric is absent are re-marked None so the shared layer
        # imputes pool-worst instead of distorting the normalization.
        _OBJECTIVES = ("nn_component", "crisot_component", "crisot_specificity_component")
        _METRIC_OF = {
            "nn_component": ("nn_score", "design_nn_score"),
            "crisot_component": ("crisot_score",),
            "crisot_specificity_component": ("crisot_specificity",),
        }
        for c in candidates:
            mb = c.metadata.get("metrics_bundle", {})
            for comp, metric_keys in _METRIC_OF.items():
                if c.scores.get(comp) is not None and all(mb.get(k) is None for k in metric_keys):
                    c.scores[comp] = None
        inp = self._workflow_state.get("_sgrna_input")
        asf_weights = {
            "nn_component": float(getattr(inp, "weight_nn_score", 0.5)) if inp else 0.5,
            "crisot_component": float(getattr(inp, "weight_crisot", 0.5)) if inp else 0.5,
            "crisot_specificity_component": (
                float(getattr(inp, "weight_crisot_specificity", 0.3)) if inp else 0.3
            ),
        }
        # Ranking governance (DECISIONS (p)): nn/crisot are pending-governance
        # oracles (registered data gap, DECISIONS (l)) — kept with a
        # ``pending`` flag; crisot_specificity is aggregate compute, never in
        # the mechanism. The shared layer renormalizes asf_weights over the
        # surviving ranking dims.
        assembly = assemble_for_workflow(list(_OBJECTIVES), _ORACLE_BACKED_OBJECTIVES, self.task_type)
        self._workflow_state["_ranking_governance"] = assembly.to_state()
        ranking = apply_reference_point_ranking(
            candidates, assembly.ranking_dims, None,
            maximize={key: True for key in assembly.ranking_dims},
            weights=asf_weights,
        )
        if ranking.dropped_dims:
            _LOGGER.info(
                "sgrna_asf_ranking_note dropped_dims(unmeasured)=%s", ranking.dropped_dims
            )

        ranked = sorted(
            candidates, key=lambda c: ranking.asf_map.get(c.id, float("inf"))
        )
        for i, c in enumerate(ranked, start=1):
            c.rank = i
            c.scores["asf_distance"] = ranking.asf_map.get(c.id)
        best = ranked[0] if ranked else None
        # Pareto frontier surfacing (consistency across every ASF workflow,
        # 2026-08-22): the shared layer already computes it — surface it.
        pareto_frontier = ranking.pareto_frontier

        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            parts = [
                f"#{i}",
                f"source={c.source}",
                f"len={len(c.sequence)}nt",
                f"mut={mb.get('design_mutation_count', 'N/A')}",
            ]
            nn_val = mb.get("nn_score") or mb.get("design_nn_score")
            if nn_val is not None:
                parts.append(f"nn_score={float(nn_val):.4f}")
            else:
                parts.append("nn_score=N/A")
            if mb.get("crisot_score") is not None:
                parts.append(f"CRISOT={mb['crisot_score']:.4f}")
            else:
                parts.append("CRISOT=N/A")
            parts.append(f"total_score={scores.get('total_score', 0.0):.4f}")
            asf = scores.get("asf_distance")
            parts.append(f"asf={asf:.4f}" if asf is not None else "asf=N/A")
            detail_lines.append(" | ".join(parts))

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_asf_distance={best.scores.get('asf_distance') if best else None}",
            f"pareto_frontier_size={len(pareto_frontier)}",
            "---",
            *detail_lines,
        ]
        return WorkflowResult(
            success=True,
            task_id=f"sgrna_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
            pareto_frontier=pareto_frontier,
        )

