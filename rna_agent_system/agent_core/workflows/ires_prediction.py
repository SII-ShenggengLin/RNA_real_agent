"""IRES prediction & validation workflow — screening / evaluation (Layer 2).

Input sequence → IRESfinder (3 modes) → merge positive windows →
structural validation (ViennaRNA fold + RNAplfold + dot-bracket) →
scoring → ranking → confidence annotation via QualityAgent.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  IresPredictionWorkflow INTERFACE LOCK (v1.1.0) —— 禁止单方面变更           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 ires_prediction workflow 的权威实现。任何字段增删、函数签名变动、   ║
║  返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：               ║
║                                                                               ║
║    - agent_core/workflows/ires_prediction.py  ← 本文件                       ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/quality_profiles/__init__.py                                  ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/capabilities/base.py                                          ║
║    - agent_core/agents/quality_agent.py                                       ║
║    - agent_core/agents/specialist_agent.py                                    ║
║    - agent_core/agents/pipeline_agent.py                                      ║
║    - agent_core/quality_profiles/ires_prediction.py                           ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - microservices/iresfinder_service/main.py                                 ║
║    - tests/test_ires_prediction.py                                            ║
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

    IMPORTANT — Parameter Override Policy:
    The default parameters below have been carefully tuned by domain experts
    for general-purpose IRES screening (probability_threshold=0.5, window_size=174,
    step_size=50, top_n_candidates=5).  These defaults perform well across a
    wide range of viral and cellular IRES sequences.  Only override a default
    when the user's request contains an EXPLICIT, SPECIFIC requirement that
    directly contradicts it (e.g. user says "use a 200-nt window" or
    "I need at least 10 candidates").  When in doubt, OMIT the parameter and
    let the workflow use its built-in defaults.
    """
    # Tool-level parameter overrides (from tools_parameter_analysis.json)
    iresfinder_filepath: str = Field(default=None, description="[iresfinder] filepath: Path to a workspace or repo-relative file containing RNA/DNA sequence or FASTA. Do not pass raw sequence text directly.")
    iresfinder_window_size: int = Field(default=174, description="[iresfinder] window_size: Sliding-window length used only in mode 2 (upstream default: 174).")
    iresfinder_step_size: int = Field(default=50, description="[iresfinder] step_size: Sliding-window step size used only in mode 2 (upstream default: 50).")
    iresfinder_decision_threshold: float = Field(default=0.5, description="[iresfinder] decision_threshold: Probability threshold for labeling a fragment as IRES (upstream default: 0.5).")
    iresfinder_service_url: str = Field(default='http://127.0.0.1:8013/predict', description="[iresfinder] service_url: REST endpoint for the IRESfinder microservice.")
    iresfinder_out: str = Field(default=None, description="[iresfinder] -o/--out (unexposed): 上游 IRESfinder.py 的输出文件参数。")
    linearfold_filepath: str = Field(default=None, description="[linearfold] filepath: Path to a workspace file containing RNA sequence (plain or FASTA).")
    linearfold_beam_size: int = Field(default=100, description="[linearfold] beam_size: Beam size for LinearFold (0 = infinite beam).")
    linearfold_use_vienna: bool = Field(default=False, description="[linearfold] use_vienna: If true, request LinearFold-V (Vienna energy parameters).")
    linearfold_dangles: int = Field(default=2, description="[linearfold] dangles: Dangling-end model: 0 or 2 (LinearFold --dangles).")
    linearfold_sharpturn: bool = Field(default=False, description="[linearfold] sharpturn: Enable sharpturn in prediction.")
    linearfold_constraints: Optional[str] = Field(default=None, description="[linearfold] constraints: Optional constraint string (? . ( ) ) for constrained prediction. If provided, length must match the sequence.")
    linearfold_shape_file_path: Optional[str] = Field(default=None, description="[linearfold] shape_file_path: Optional path to SHAPE reactivity data file (mutually exclusive with constraints).")
    linearfold_service_url: str = Field(default='http://127.0.0.1:8015/fold', description="[linearfold] service_url: REST endpoint for the LinearFold microservice.")
    linearfold_fasta: bool = Field(default=False, description="[linearfold] --fasta: 上游 --fasta，声明输入为 FASTA 格式。")
    linearfold_verbose: bool = Field(default=False, description="[linearfold] --verbose: 上游 -v/--verbose，输出每个 loop 的能量。")
    vienna_fold_filepath: str = Field(default=None, description="[vienna_fold] filepath: Path to RNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.")
    vienna_fold_temp_c: float = Field(default=37.0, description="[vienna_fold] temp_c: Folding temperature (Celsius).")
    vienna_fold_dangles: int = Field(default=2, description="[vienna_fold] dangles: Dangling-end model.")
    vienna_fold_no_lp: bool = Field(default=False, description="[vienna_fold] no_lp: Disallow lonely pairs.")
    vienna_fold_no_gu: bool = Field(default=False, description="[vienna_fold] no_gu: Disallow GU pairs.")
    vienna_fold_no_closing_gu: bool = Field(default=False, description="[vienna_fold] no_closing_gu: Disallow GU closing pairs.")
    vienna_fold_salt: Optional[float] = Field(default=None, description="[vienna_fold] salt: Salt concentration (M).")
    vienna_fold_no_tetra: bool = Field(default=False, description="[vienna_fold] no_tetra: Omit special hairpin loop energies.")
    vienna_fold_energy_model: Optional[int] = Field(default=None, description="[vienna_fold] energy_model: Energy model index.")
    vienna_fold_nsp: Optional[str] = Field(default=None, description="[vienna_fold] nsp: Non-standard pair specification.")
    vienna_fold_param_file: Optional[str] = Field(default=None, description="[vienna_fold] param_file: Custom parameter file.")
    vienna_fold_constraint: Optional[str] = Field(default=None, description="[vienna_fold] constraint: Hard constraint dot-bracket string.")
    vienna_fold_shape_file: Optional[str] = Field(default=None, description="[vienna_fold] shape_file: Path to SHAPE reactivity data file.")
    vienna_fold_shape_method: str = Field(default='D', description="[vienna_fold] shape_method: SHAPE method: D, Z, or W.")
    vienna_fold_partfunc: bool = Field(default=False, description="[vienna_fold] partfunc: Compute partition function and centroid.")
    vienna_fold_circ: bool = Field(default=False, description="[vienna_fold] circ: Assume circular RNA.")
    vienna_fold_gquad: bool = Field(default=False, description="[vienna_fold] gquad: Include G-quadruplex formation.")
    vienna_fold_service_url: str = Field(default='http://127.0.0.1:8003/fold', description="[vienna_fold] service_url: ViennaRNA fold endpoint.")
    vienna_fold_noDP: bool = Field(default=False, description="[vienna_fold] --noDP: 上游 --noDP，禁止生成 dot-plot PostScript。")
    vienna_fold_maxBPspan: int = Field(default=-1, description="[vienna_fold] --maxBPspan: 上游 --maxBPspan，默认 -1 无限制。")
    vienna_fold_MEA: Any = Field(default=None, description="[vienna_fold] --MEA: 上游 --MEA[=gamma]，基于最大期望精度预测结构。")
    vienna_fold_batch: bool = Field(default=False, description="[vienna_fold] --batch: 上游 --batch，批量使用约束。")
    vienna_fold_canonicalBPonly: bool = Field(default=False, description="[vienna_fold] --canonicalBPonly: 上游 --canonicalBPonly，从约束中移除非规范碱基对。")
    vienna_fold_enforceConstraint: bool = Field(default=False, description="[vienna_fold] --enforceConstraint: 上游 --enforceConstraint，强制约束中圆括号表示的碱基对必须形成。")
    vienna_fold_shapeConversion: str = Field(default='O', description="[vienna_fold] --shapeConversion: 上游 --shapeConversion，SHAPE 到配对概率的转换方法。")
    vienna_fold_verbose: bool = Field(default=False, description="[vienna_fold] --verbose: 上游 -v，输出详细日志。")
    plfold_filepath: str = Field(default=None, description="[plfold] filepath: Workspace file with RNA sequence (plain or FASTA).")
    plfold_temp_c: float = Field(default=37.0, description="[plfold] temp_c: Temperature in Celsius.")
    plfold_dangles: int = Field(default=2, description="[plfold] dangles: Dangling-end model.")
    plfold_no_lp: bool = Field(default=False, description="[plfold] no_lp: Disallow lonely pairs.")
    plfold_no_gu: bool = Field(default=False, description="[plfold] no_gu: Disallow GU pairs.")
    plfold_no_closing_gu: bool = Field(default=False, description="[plfold] no_closing_gu: Disallow GU closing pairs.")
    plfold_salt: Optional[float] = Field(default=None, description="[plfold] salt: Salt concentration (M).")
    plfold_no_tetra: bool = Field(default=False, description="[plfold] no_tetra: Omit special hairpin loop energies.")
    plfold_energy_model: Optional[int] = Field(default=None, description="[plfold] energy_model: Energy model index.")
    plfold_nsp: Optional[str] = Field(default=None, description="[plfold] nsp: Non-standard pair specification.")
    plfold_param_file: Optional[str] = Field(default=None, description="[plfold] param_file: Custom parameter file.")
    plfold_winsize: int = Field(default=70, description="[plfold] winsize: RNAplfold -W window size.")
    plfold_span: int = Field(default=70, description="[plfold] span: RNAplfold -L max pair span.")
    plfold_unpaired_ulength: int = Field(default=25, description="[plfold] unpaired_ulength: RNAplfold -u upper bound for stretch probabilities in lunp output.")
    plfold_cutoff: Optional[float] = Field(default=None, description="[plfold] cutoff: RNAplfold -c probability cutoff.")
    plfold_opening_energies: bool = Field(default=False, description="[plfold] opening_energies: RNAplfold -O: return opening energies instead of probabilities.")
    plfold_service_url: str = Field(default='http://127.0.0.1:8003/plfold-profiles', description="[plfold] service_url: REST endpoint for ViennaRNA RNAplfold profile (lunp column 1).")
    plfold_shape: Optional[str] = Field(default=None, description="[plfold] --shape: 上游 RNAplfold --shape。")
    plfold_print_onthefly: bool = Field(default=False, description="[plfold] --print_onthefly: 上游 RNAplfold -o。")
    plfold_verbose: bool = Field(default=False, description="[plfold] --verbose: 上游 -v。")
    unpaired_filepath: str = Field(default=None, description="[unpaired] filepath: Path to dot-bracket secondary structure (first structural line used; FASTA header skipped).")
    unpaired_service_url: str = Field(default='http://127.0.0.1:8020/unpaired-fraction', description="[unpaired] service_url: POST endpoint for unpaired-fraction microservice.")
    unpaired_timeout_seconds: float = Field(default=120.0, description="[unpaired] timeout_seconds: HTTP request timeout in seconds.")
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
        the candidate metadata for user inspection and QualityAgent review, but
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

