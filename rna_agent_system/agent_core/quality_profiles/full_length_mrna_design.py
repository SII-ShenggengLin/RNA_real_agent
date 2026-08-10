"""QualityProfile for full_length_mrna_design workflow."""

from __future__ import annotations

from typing import Any

from agent_core.agents.quality_agent import QualityAgent, QualityProfile
from agent_core.constants.species import RNARL_MODEL_TYPES_LIST, format_cai_species_aliases
from agent_core.workflow_models import WorkflowResult


def _build_full_length_context(
    result: WorkflowResult, state: dict[str, Any]
) -> dict[str, Any]:
    ctx = QualityAgent._build_default_context(result, state)

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

        p5 = meta.get("utr5_preset", "unknown")
        p3 = meta.get("utr3_preset", "unknown")
        utr5_presets[p5] = utr5_presets.get(p5, 0) + 1
        utr3_presets[p3] = utr3_presets.get(p3, 0) + 1

        cds_src = meta.get("cds_source", "unknown")
        cds_sources[cds_src] = cds_sources.get(cds_src, 0) + 1

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


FULL_LENGTH_MRNA_QUALITY_PROFILE = QualityProfile(
    workflow_name="full_length_mrna_design",
    workflow_description=(
        "Design full-length mRNA (5'UTR + CDS + 3'UTR) from protein sequence. "
        "CDS is generated via MrnaCdsDesignWorkflow (LinearDesign/RNARL/GEMORNA); "
        "UTRs are appended from GEMORNA short/medium/long presets. "
        "BMC coordination is reference-point driven: the coordinator compares each "
        "candidate's normalized objective scores to a user-provided or auto-derived "
        "reference point and regenerates modules when gaps exist. "
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
        "Reference point alignment: If the user provided a reference_point, verify that the best candidate is close to it across the specified dimensions. If no reference point was provided, the system uses the utopian point derived from the candidate pool.",
    ],
    adjustable_params={
        "utr_mode": {
            "type": "enum",
            "values": ["short", "medium", "long", "all"],
            "hint": "UTR length preset. If user asked for specific lengths (e.g. 'long 3'UTR for stability'), set accordingly. 'all' explores all presets.",
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
            "values": RNARL_MODEL_TYPES_LIST,
            "hint": "RNARL model type. Only effective when design_tool='rnarl' or 'all'.",
        },
        "cai_species": {
            "type": "str",
            "hint": f"Species for CAI computation. Built-in: {format_cai_species_aliases()}.",
        },
        "run_fold": {
            "type": "bool",
            "hint": "Whether to run RNA secondary structure folding. Should normally stay True.",
        },
        "run_gc": {
            "type": "bool",
            "hint": "Whether to compute GC content. Should normally stay True.",
        },
        "reference_point": {
            "type": "dict",
            "hint": "Optional per-objective aspiration point for ASF selection and BMC coordination. User-facing keys: cds_component, utr5_mrl, utr3_stability, full_mfe_score. Missing dimensions use the candidate-pool utopian point.",
        },
        "target_cds_mfe": {
            "type": "float",
            "hint": "User-aspired CDS MFE (kcal/mol). Must be provided together with target_cds_cai; converts into a cds_component reference point.",
        },
        "target_cds_cai": {
            "type": "float",
            "hint": "User-aspired CAI in (0, 1]. Must be provided together with target_cds_mfe; converts into a cds_component reference point.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
    build_context=_build_full_length_context,
)
