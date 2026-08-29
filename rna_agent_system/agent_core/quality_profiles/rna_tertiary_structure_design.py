"""QualityProfile for rna_tertiary_structure_design workflow."""

from __future__ import annotations

from typing import Any

from agent_core.agents.quality_agent import QualityAgent, QualityProfile
from agent_core.workflow_models import WorkflowResult


def _build_tertiary_context(
    result: WorkflowResult, state: dict[str, Any]
) -> dict[str, Any]:
    ctx = QualityAgent._build_default_context(result, state)

    candidates = result.all_candidates
    if not candidates:
        ctx["tertiary_structure_stats"] = {
            "design_tool_distribution": {},
            "plddt_range": {"min": None, "max": None, "mean": None, "count": 0},
            "rmsd_range": {"min": None, "max": None, "mean": None, "count": 0},
            "tm_score_range": {"min": None, "max": None, "mean": None, "count": 0},
            "gc_range": {"min": None, "max": None, "mean": None, "count": 0},
            "mfe_range": {"min": None, "max": None, "mean": None, "count": 0},
            "recovery_rate_range": {"min": None, "max": None, "mean": None, "count": 0},
        }
        return ctx

    tool_dist: dict[str, int] = {}
    plddt_values: list[float] = []
    rmsd_values: list[float] = []
    tm_values: list[float] = []
    gc_values: list[float] = []
    mfe_values: list[float] = []
    recovery_values: list[float] = []

    for c in candidates:
        meta = c.metadata or {}
        mb = meta.get("metrics_bundle", {})

        tool = meta.get("design_tool", "unknown")
        tool_dist[tool] = tool_dist.get(tool, 0) + 1

        plddt = mb.get("rhofold_mean_plddt")
        if plddt is not None:
            plddt_values.append(float(plddt))
        rmsd = mb.get("alignment_rmsd")
        if rmsd is not None:
            rmsd_values.append(float(rmsd))
        tm = mb.get("alignment_tm_score")
        if tm is not None:
            tm_values.append(float(tm))
        gc = mb.get("gc_content")
        if gc is not None:
            gc_values.append(float(gc))
        mfe = mb.get("vienna_mfe")
        if mfe is not None:
            mfe_values.append(float(mfe))
        rec = mb.get("recovery_rate")
        if rec is not None:
            recovery_values.append(float(rec))

    def _stats(vals: list[float]) -> dict[str, Any]:
        if not vals:
            return {"min": None, "max": None, "mean": None, "count": 0}
        return {
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
            "mean": round(sum(vals) / len(vals), 3),
            "count": len(vals),
        }

    ctx["tertiary_structure_stats"] = {
        "design_tool_distribution": tool_dist,
        "plddt_range": _stats(plddt_values),
        "rmsd_range": _stats(rmsd_values),
        "tm_score_range": _stats(tm_values),
        "gc_range": _stats(gc_values),
        "mfe_range": _stats(mfe_values),
        "recovery_rate_range": _stats(recovery_values),
    }
    return ctx


RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE = QualityProfile(
    workflow_name="rna_tertiary_structure_design",
    workflow_description="Design RNA sequences from a tertiary structure using inverse-folding tools (RhoDesign / RiboDiffusion). Pipeline: inverse folding generation → GC + ViennaRNA fold + RhoFold + structure alignment evaluation → scoring → ranking.",
    evaluation_dimensions=[
        "RhoFold pLDDT reflects the predicted foldability of the designed RNA sequence. Higher values generally indicate more confident tertiary structure prediction, but the appropriate level depends on sequence length, structural complexity, and the user's specific application.",
        "TM-score measures the structural similarity between the RhoFold-predicted structure and the input reference structure. Higher values suggest the designed sequence can recapitulate the target fold, but interpret relative to the target system and other candidates rather than enforcing a fixed cutoff.",
        "RMSD measures the spatial deviation between predicted and reference structures. Lower values generally indicate better structural alignment, but acceptable RMSD depends on target size, flexibility, and the user's tolerance.",
        "GC content affects RNA stability, synthesis, and secondary structure propensity. Extremely high GC can impede synthesis and promote misfolding; extremely low GC reduces thermal stability. Evaluate in context of the specific application rather than enforcing a rigid range.",
        "ViennaRNA MFE (Minimum Free Energy) reflects thermodynamic stability of the designed sequence's secondary structure. More negative values indicate more stable structures. Consider whether the user's application requires high or low stability.",
        "Recovery rate from the design tool indicates how well the designed sequence matches the original structure's sequence profile. Higher recovery generally suggests better compatibility with the target backbone.",
        "Diversity of design tools matters: if all candidates come from the same tool, consider switching tools for retry to explore different sequence spaces.",
        "CRITICAL: Base your quality assessment on the user's original intent and any explicit constraints they stated. If the user specified thresholds (e.g., 'pLDDT must be > 70', 'TM-score > 0.5', 'RMSD < 3.0'), evaluate whether the results meet those constraints. Failure to meet user constraints is a CRITICAL issue. Do not apply universal thresholds that may be inappropriate for this specific design task.",
        "CRITICAL: Default parameters for this workflow have been carefully tuned (n_samples_per_tool=3, rhodesign_temperature=0.1, temperature_range=0.05, ribodiffusion_sampling_steps=50, scoring weights weight_rhofold/weight_rmsd/weight_tm_score=0.30/0.50/0.50 — pLDDT deliberately below the closeness weights so a self-confidence champion cannot bury the structure-closest candidate). These defaults work well for most RNA tertiary structure design tasks. Only recommend parameter overrides when you have strong evidence that the current settings are causing systematic problems. Do not tweak parameters lightly.",
    ],
    adjustable_params={
        "design_tools": {
            "type": "enum",
            "values": ["all", "rhodesign", "ribodiffusion"],
            "hint": "Which inverse-folding tool(s) to use. 'all' runs both. If one tool consistently underperforms, try the other. Default is 'all' and is well-tuned; only change when there is clear evidence that a specific tool performs better for the target structure.",
        },
        "n_samples_per_tool": {
            "type": "int",
            "min": 1,
            "max": 20,
            "hint": "Number of sequences to generate per tool. Increase for more candidate diversity. Default (3) is generally sufficient; only increase if candidate diversity is clearly lacking and the user explicitly asks for more.",
        },
        "rhodesign_temperature": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Base sampling temperature for RhoDesign. Higher values increase diversity but may reduce quality. Default (0.1) is well-tuned for structure fidelity; only adjust when there is strong evidence that the current temperature is causing systematic issues.",
        },
        "rhodesign_temperature_range": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Temperature sweep range for multi-sample RhoDesign calls. Default (0.05) provides good diversity without sacrificing quality; only increase if the current range produces overly homogeneous candidates.",
        },
        "ribodiffusion_sampling_steps": {
            "type": "int",
            "min": 1,
            "max": 500,
            "hint": "Diffusion sampling steps for RiboDiffusion. Default (50) offers a good quality/runtime tradeoff; only increase when the user explicitly requests higher quality and runtime is not a concern.",
        },
        "weight_rhofold": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Weight for RhoFold pLDDT in composite scoring. Default (0.3) sits deliberately below the closeness weights (pool-relative min-max otherwise lets a pLDDT champion bury the native-closest candidate); only adjust when the user explicitly prioritizes foldability confidence over structural closeness.",
        },
        "weight_rmsd": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Weight for RMSD in composite scoring. Default (0.5); only adjust when the user explicitly prioritizes one objective over the others.",
        },
        "weight_tm_score": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Weight for the TM-score component (only measurable when a reference structure exists). Default (0.5); only adjust when the user explicitly prioritizes one objective over the others.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
    build_context=_build_tertiary_context,
)
