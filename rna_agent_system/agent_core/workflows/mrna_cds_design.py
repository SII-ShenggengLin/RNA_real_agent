"""mRNA CDS design & optimisation workflow — the golden path (Layer 2).

Protein sequence → CDS design (LinearDesign λ=[0,1,4,10] where λ∈[0,+∞), typically ≤10 + RNARL + GEMORNA) →
fold + GC + unpaired-fraction evaluation → scoring → ranking → WorkflowResult.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  MrnaCdsDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更            ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 mrna_cds_design workflow 的权威实现。任何字段增删、函数签名变动、  ║
║  返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：               ║
║                                                                               ║
║    - agent_core/workflows/mrna_cds_design.py  ← 本文件                       ║
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
║    - tests/test_mrna_cds_design_workflow.py                                   ║
║    - tests/test_mrna_cds_design_comprehensive.py                              ║
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
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.sequence_utils import (
    _load_builtin_codon_tables,
    resolve_species_name,
)
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.sequence_utils import (
    compute_mrna_metric_bundle,
    score_mrna_candidate,
)
from agent_core.workflows.evaluators import (
    CAIEvaluator,
    CompositeEvaluator,
    GCContentEvaluator,
    RNASTOPEvaluator,
    SecondaryStructureEvaluator,
    UContentEvaluator,
    UnpairedFractionEvaluator,
)

_LOGGER = logging.getLogger("agent_core.workflows.mrna_cds_design")


# ─────────────────────────────────────────────────────────────────────────────
# Input model — INTERFACE LOCKED (v1.0.0)
# ─────────────────────────────────────────────────────────────────────────────


class MrnaCdsDesignInput(BaseModel):
    """Input for the mRNA CDS design golden path."""

    model_config = ConfigDict(extra="forbid")

    protein_sequence: str = Field(..., description="Amino-acid string (uppercase, 1-letter codes).")
    design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"] = "all"
    lambda_value: Optional[float] = Field(
        default=None,
        description="LinearDesign MFE/CAI balance (0-20). Required when design_tool='lineardesign'; ignored otherwise.",
    )
    model_type: Literal[
        "Homo sapiens mRNA",
        "Homo sapiens circular RNA",
        "Arabidopsis thaliana mRNA",
        "Escherichia coli mRNA",
        "Penicillium chrysogenum mRNA",
        "Chlamydomonas reinhardtii mRNA",
        "Thermococcus kodakarensis KOD1 mRNA",
    ] = Field(default="Homo sapiens mRNA", description="RNARL model type.")
    cai_species: str = Field(
        default="Homo sapiens",
        description="Species for CAI computation. Built-in: human, mouse, rat, fly, worm, zebrafish, arabidopsis, yeast, ecoli, bsubtilis, cho.",
    )
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


# ─────────────────────────────────────────────────────────────────────────────
# Workflow — INTERFACE LOCKED (v1.0.0)
# ─────────────────────────────────────────────────────────────────────────────


class MrnaCdsDesignWorkflow(BaseDomainWorkflow[MrnaCdsDesignInput, WorkflowResult]):
    """Golden-path workflow: protein → multi-tool CDS → fold + GC + unpaired → score → rank."""

    name = "mrna_cds_design"
    description = "Design mRNA CDS from protein sequence using multiple tools, evaluate, score, and rank candidates."
    input_model = MrnaCdsDesignInput
    required_capabilities = [
        "design_mrna_cds_with_lineardesign",
        "design_mrna_cds_with_rnarl",
        "design_mrna_cds_with_gemorna",
        "predict_rna_secondary_structure",
        "predict_rna_secondary_structure_with_linearfold",
        "compute_rna_sequence_gc_content",
        "compute_rna_sequence_u_content",
        "compute_dot_bracket_unpaired_fraction",
        "predict_mrna_stability_with_rnastop",
        "compute_cai_for_cds_sequence",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._run_fold = True
        self._run_gc = True
        self._generation_errors: list[str] = []
        self.evaluator = CompositeEvaluator([
            GCContentEvaluator(self.capabilities),
            UContentEvaluator(self.capabilities),
            SecondaryStructureEvaluator(self.capabilities, run_fold=True),
            UnpairedFractionEvaluator(self.capabilities),
            RNASTOPEvaluator(self.capabilities),
            CAIEvaluator(self.capabilities, species_key="cai_species"),
        ])

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        inp: MrnaCdsDesignInput | dict[str, Any],
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """Accept either ``MrnaCdsDesignInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = MrnaCdsDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._run_fold = inp.run_fold
        self._run_gc = inp.run_gc
        result = super().run(inp, progress_callback=progress_callback)
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def partial_rerun(
        self,
        inp: MrnaCdsDesignInput | dict[str, Any],
        existing_candidates: list[Candidate],
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """Re-run evaluate → score → rank on existing candidates.

        Updates evaluator flags (``run_fold``, ``run_gc``) from *inp* without
        regenerating candidates.
        """
        if isinstance(inp, dict):
            inp = MrnaCdsDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._run_fold = inp.run_fold
        self._run_gc = inp.run_gc

        for i, candidate in enumerate(existing_candidates):
            metrics = self.evaluate(candidate)
            candidate.scores = self.score(metrics)
            candidate.status = "evaluated"
            if progress_callback:
                progress_callback({
                    "event": "evaluate_progress",
                    "current": i + 1,
                    "total": len(existing_candidates),
                    "candidate_id": candidate.id,
                    "workflow": self.name,
                })

        result = self.rank_and_format(existing_candidates)
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
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
            if inp.design_tool == "all":
                for lam in (0.0, 1.0, 4.0, 10.0):
                    design_configs.append(
                        ("lineardesign", {"lambda_value": lam})
                    )
            else:  # design_tool == "lineardesign"
                # Validator ensures lambda_value is not None; guard anyway.
                lam = inp.lambda_value if inp.lambda_value is not None else 0.0
                design_configs.append(
                    ("lineardesign", {"lambda_value": lam})
                )

        if inp.design_tool in ("all", "rnarl"):
            design_configs.append(
                ("rnarl", {"model_type": inp.model_type})
            )

        if inp.design_tool in ("all", "gemorna"):
            design_configs.append(("gemorna", {}))

        self._generation_errors = []
        candidates: list[Candidate] = []
        for tool_name, extra_args in design_configs:
            try:
                cap_name = f"design_mrna_cds_with_{tool_name}"
                if not self.capabilities.has(cap_name):
                    err_msg = f"capability missing: {cap_name}"
                    _LOGGER.warning(err_msg)
                    self._generation_errors.append(err_msg)
                    continue

                cap = self.capabilities.get(cap_name)
                args: dict[str, Any] = {"filepath": protein_fp, **extra_args}
                cap_result = cap.invoke(args, state=self._workflow_state)

                if not cap_result.success:
                    err_msg = f"design failed tool={tool_name} error={cap_result.error}"
                    _LOGGER.warning(err_msg)
                    self._generation_errors.append(err_msg)
                    continue

                seq = str(cap_result.output.get("generated_sequence", ""))
                if not seq:
                    err_msg = f"design empty tool={tool_name}"
                    _LOGGER.warning(err_msg)
                    self._generation_errors.append(err_msg)
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
                        "cai_species": inp.cai_species,
                    },
                )
                design_record = ToolCallRecord(
                    step_name=f"cds_design:{tool_name}",
                    tool_name=cap_name,
                    input_summary=json.dumps(args, default=str),
                    output_summary=json.dumps(cap_result.output, default=str)[:500],
                    success=cap_result.success,
                    error=cap_result.error,
                    elapsed_time=cap_result.elapsed_time,
                    artifacts=dict(cap_result.output) if cap_result.success else {},
                    metrics={"lambda_value": extra_args["lambda_value"]} if "lambda_value" in extra_args else {},
                )
                candidate.add_tool_record(design_record)
                candidates.append(candidate)
                _LOGGER.info(
                    "candidate_generated tool=%s params=%s len_nt=%d",
                    tool_name,
                    extra_args,
                    len(seq),
                )
            except Exception as exc:
                err_msg = f"design exception tool={tool_name} err={exc}"
                _LOGGER.error(err_msg)
                self._generation_errors.append(err_msg)

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

        # Update evaluator flags from workflow state
        for ev in self.evaluator.evaluators:
            if isinstance(ev, SecondaryStructureEvaluator):
                ev.run_fold = self._run_fold
            if isinstance(ev, GCContentEvaluator):
                ev.run_gc = self._run_gc

        context: dict[str, Any] = {"workflow_state": self._workflow_state}
        if "cai_species" in candidate.metadata:
            context["species"] = candidate.metadata["cai_species"]

        metrics = self.evaluator.evaluate(candidate, context)

        # Domain-specific: warn about missing species when CAI evaluation fails
        cai_species = candidate.metadata.get("cai_species", "Homo sapiens")
        if (
            "cai_score" not in metrics
            and self.capabilities.has("compute_cai_for_cds_sequence")
        ):
            try:
                builtin = _load_builtin_codon_tables()
                resolved = resolve_species_name(cai_species)
                if resolved not in builtin:
                    available = ", ".join(sorted(builtin.keys()))
                    _LOGGER.warning(
                        "Species '%s' not available in built-in codon tables. "
                        "Available species: %s. To compute CAI for this species, "
                        "provide a custom codon usage table JSON via the "
                        "compute_cai_for_cds_sequence tool's custom_codon_table_path parameter.",
                        cai_species,
                        available,
                    )
            except Exception:
                pass

        bundle = compute_mrna_metric_bundle(
            sequence=candidate.sequence,
            gc_from_tools=metrics.get("gc_content"),
            sequence_length_from_tools=metrics.get("sequence_length"),
            mfe_kcal_per_mol=metrics.get("mfe_kcal_per_mol"),
            unpaired_fraction=metrics.get("unpaired_fraction"),
            rnastop_overall_stability=metrics.get("rnastop_overall_stability"),
            cai_score=metrics.get("cai_score"),
            u_fraction=metrics.get("u_fraction"),
        )
        bundle["fold_tool"] = metrics.get("fold_tool")
        bundle["cai_species"] = cai_species
        candidate.metadata["metrics_bundle"] = bundle
        candidate.metadata["fold_tool"] = metrics.get("fold_tool")
        if "structure" not in candidate.metadata:
            candidate.metadata["structure"] = metrics.get("structure")
        return bundle

    # ─────────────────────────────────────────────────────────────────────────
    # Scoring — INTERFACE LOCKED (v1.0.0)
    # ─────────────────────────────────────────────────────────────────────────

    def score(self, metrics: dict[str, Any]) -> dict[str, Any]:
        return score_mrna_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            errors = ["empty_candidate_list"]
            if self._generation_errors:
                errors.extend(self._generation_errors)
            return WorkflowResult(
                success=False,
                task_id="",
                summary="No candidates produced.",
                errors=errors,
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
                f"U={mb.get('u_fraction'):.3f}" if mb.get("u_fraction") is not None else "U=N/A",
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


# LLM Critic Configuration — INTERFACE LOCKED (v1.0.0)

from agent_core.planning.llm_critic import BaseLLMCritic, CriticConfig


MRNA_CDS_CRITIC_CONFIG = CriticConfig(
    workflow_name="mrna_cds_design",
    workflow_description="Design mRNA CDS from protein sequence using LinearDesign, RNARL, or GEMORNA",
    evaluation_dimensions=[
        "CAI (Codon Adaptation Index) measures translation efficiency. For human mRNA, CAI > 0.8 is good, < 0.4 is poor and suggests the codon usage is not optimized for the target organism.",
        "MFE (Minimum Free Energy) measures RNA secondary structure stability. More negative = more stable. Too negative may indicate excessive structure that could impede translation.",
        "GC content is reported for reference but does not directly enter the ranking score.",
        "Unpaired fraction is reported for reference but does not directly enter the ranking score.",
        "If RNASTOP overall_stability is available, values closer to 1.0 indicate higher predicted stability.",
        "LinearDesign lambda parameter controls the MFE/CAI tradeoff: lambda=0 gives the best MFE (most stable structure, most negative) but lowest CAI. As lambda increases towards +∞ (practical range 0–10), CAI gradually improves while MFE gradually worsens (becomes less stable). Lambda cannot directly control GC content.",
        "Diversity of design tools matters: if all candidates come from the same tool, consider switching tools for the retry.",
    ],
    adjustable_params={
        "design_tool": {
            "type": "enum",
            "values": ["lineardesign", "rnarl", "gemorna", "all"],
            "hint": "Which design tool to use. 'all' runs all tools. If one tool consistently underperforms, try a specific tool. GEMORNA and RNARL are both balanced; LinearDesign with high lambda favors stability.",
        },
        "lambda_value": {
            "type": "float",
            "min": 0.0,
            "max": 20.0,
            "hint": "LinearDesign MFE/CAI tradeoff parameter. Range is [0, +∞), typically set ≤10. lambda=0 gives the best MFE (most stable structure, most negative) but lowest CAI. As lambda increases, CAI gradually improves while MFE gradually worsens. Decrease lambda to improve poor MFE; increase lambda to improve poor CAI.",
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
            "hint": "RNARL model type. Only these 7 types are supported. If the user asks for a species not in this list, fall back to 'Homo sapiens mRNA' or switch to GEMORNA/LinearDesign.",
        },
        "cai_species": {
            "type": "str",
            "hint": "Species for CAI computation. Built-in: human, mouse, rat, fly, worm, zebrafish, arabidopsis, yeast, ecoli, bsubtilis, cho. For other species, provide a custom codon usage table JSON.",
        },
        "run_fold": {
            "type": "bool",
            "hint": "Whether to run secondary structure folding (ViennaRNA/LinearFold). Disabling skips the fold evaluator — a fast partial retry when fold results look suspicious.",
        },
        "run_gc": {
            "type": "bool",
            "hint": "Whether to run GC content evaluation. Disabling skips the GC evaluator.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
    evaluator_only_params={"run_fold", "run_gc"},
    param_to_evaluators={
        "run_fold": ["SecondaryStructureEvaluator", "UnpairedFractionEvaluator"],
        "run_gc": ["GCContentEvaluator"],
    },
)


class MrnaCdsDesignLLMCritic(BaseLLMCritic):
    """LLM-driven Critic for mRNA CDS design workflow."""

    def _default_config(self) -> CriticConfig:
        return MRNA_CDS_CRITIC_CONFIG
