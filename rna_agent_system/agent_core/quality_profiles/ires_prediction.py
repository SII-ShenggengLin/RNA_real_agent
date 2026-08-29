"""QualityProfile for ires_prediction workflow."""

from __future__ import annotations

from typing import Any

from agent_core.agents.quality_agent import QualityProfile
from agent_core.workflow_models import WorkflowResult


def _build_ires_context(
    result: WorkflowResult, state: dict[str, Any]
) -> dict[str, Any]:
    from agent_core.agents.quality_agent import QualityAgent

    ctx = QualityAgent._build_default_context(result, state)

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


IRES_QUALITY_PROFILE = QualityProfile(
    workflow_name="ires_prediction",
    workflow_description="Predict putative IRES elements in an RNA/DNA sequence using IRESfinder with optional structural validation",
    evaluation_dimensions=[
        "IRESfinder probability scores reflect the model's confidence that a region functions as an IRES. Higher scores generally indicate stronger prediction confidence, but the appropriate threshold depends on the application (screening vs. validation). Evaluate relative to other candidates and the user's stated requirements rather than enforcing a fixed cutoff.",
        "Structural validation via LinearFold (primary) or ViennaRNA (fallback) fold provides the predicted secondary structure (dot-bracket notation) and MFE. A stable but not excessively rigid structure is typically desirable for IRES function — overly rigid structures may impede ribosome access, while overly unstable ones lack the scaffold needed for IRES activity.",
        "Mean unpaired fraction from dot-bracket analysis and RNAplfold local accessibility both indicate how much of the structure is single-stranded. IRES function generally benefits from a balance: some structured regions provide scaffold, while exposed single-stranded regions allow ribosome entry. Evaluate this balance relative to the candidate set and user intent rather than applying a universal numeric target.",
        "Coverage and distribution of candidate regions across the input sequence matters. Too few candidates may indicate the sequence lacks IRES-like features or that parameters are too restrictive. Clustered candidates in a small region may suggest a localized IRES element; scattered candidates may indicate multiple weak signals.",
        "CRITICAL: Base your quality assessment on the user's original intent and any explicit constraints they stated. If the user specified thresholds (e.g., 'probability must be > 0.9', 'need at least 3 candidates', 'focus on the 5'UTR region'), evaluate whether the results meet those constraints. Failure to meet user constraints is a CRITICAL issue. Do not apply universal thresholds that may be inappropriate for this specific screening task.",
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
            "hint": "Whether to run structural validation (LinearFold primary / ViennaRNA fallback fold + RNAplfold + dot-bracket analysis). Keep True for better confidence assessment.",
        },
        "iresfinder_mode": {
            "type": "enum",
            "values": [0, 1, 2],
            "hint": "IRESfinder mode: 0=full sequence, 1=header-specified subsequence, 2=sliding window. Switch to mode 2 for long sequences where localized IRES elements are expected.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
    build_context=_build_ires_context,
)
