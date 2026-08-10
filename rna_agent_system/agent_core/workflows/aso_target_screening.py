"""ASO (antisense oligonucleotide) target screening workflow (Layer 2).

Target mRNA → full-length accessibility profiling (RNAplfold) →
sliding-window ranking → ASO design (reverse complement) →
binding evaluation (RNAup / RNAcofold) → rank-based scoring → ranking → WorkflowResult.

This is an **evaluation-only workflow**; it does not generate novel sequences
but instead screens a target transcript for the most accessible binding sites.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  AsoTargetScreeningWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 aso_target_screening workflow 的权威实现。任何字段增删、            ║
║  函数签名变动、返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试： ║
║                                                                               ║
║    - agent_core/workflows/aso_target_screening.py  ← 本文件                  ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/quality_profiles/__init__.py                                  ║
║    - agent_core/workflows/__init__.py                                         ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/capabilities/base.py                                          ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - agent_core/sequence_utils.py                                             ║
║    - tests/test_aso_target_screening.py                                       ║
║    - docs/INTERFACE_LOCKS.md                                                  ║
║    - docs/WORKFLOWS.md                                                        ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import read_sequence, save_sequence, save_text_file
from agent_core.sequence_utils import _pick_float, normalize_rna_sequence
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult
from agent_core.workflows.base import BaseDomainWorkflow

_LOGGER = logging.getLogger("agent_core.workflows.aso_target_screening")

# Input / output models


class AsoScreeningInput(BaseModel):
    """Input for the ASO target screening workflow.

    NOTE — default parameter guidance for the planner:
    The defaults below (aso_length=18, window_step=1, top_n_windows=10,
    binding_evaluation_tool="rnaup") have been carefully tuned for general-use
    ASO target screening. Only override them when the user makes an explicit,
    well-justified request. If the user does not specify a parameter, always
    use the default value rather than inventing an alternative.
    """
    # Tool-level parameter overrides (from tools_parameter_analysis.json)
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
    aso_accessibility_filepath: str = Field(default=None, description="[aso_accessibility] filepath: Workspace file with full target RNA sequence (plain or FASTA).")
    aso_accessibility_region_start: int = Field(default=None, description="[aso_accessibility] region_start: 1-based inclusive ASO / binding region start on target RNA.")
    aso_accessibility_region_end: int = Field(default=None, description="[aso_accessibility] region_end: 1-based inclusive region end.")
    aso_accessibility_aso_oligo_length: int = Field(default=18, description="[aso_accessibility] aso_oligo_length: ASO length (nt) used for joint unpaired stretch probability.")
    aso_accessibility_temp_c: float = Field(default=37.0, description="[aso_accessibility] temp_c: Temperature in Celsius.")
    aso_accessibility_dangles: int = Field(default=2, description="[aso_accessibility] dangles: Dangling-end model.")
    aso_accessibility_no_lp: bool = Field(default=False, description="[aso_accessibility] no_lp: Disallow lonely pairs.")
    aso_accessibility_no_gu: bool = Field(default=False, description="[aso_accessibility] no_gu: Disallow GU pairs.")
    aso_accessibility_no_closing_gu: bool = Field(default=False, description="[aso_accessibility] no_closing_gu: Disallow GU closing pairs.")
    aso_accessibility_salt: Optional[float] = Field(default=None, description="[aso_accessibility] salt: Salt concentration (M).")
    aso_accessibility_no_tetra: bool = Field(default=False, description="[aso_accessibility] no_tetra: Omit special hairpin loop energies.")
    aso_accessibility_energy_model: Optional[int] = Field(default=None, description="[aso_accessibility] energy_model: Energy model index.")
    aso_accessibility_nsp: Optional[str] = Field(default=None, description="[aso_accessibility] nsp: Non-standard pair specification.")
    aso_accessibility_param_file: Optional[str] = Field(default=None, description="[aso_accessibility] param_file: Custom parameter file.")
    aso_accessibility_winsize: int = Field(default=70, description="[aso_accessibility] winsize: RNAplfold window size -W.")
    aso_accessibility_span: int = Field(default=70, description="[aso_accessibility] span: RNAplfold max pair span -L.")
    aso_accessibility_unpaired_ulength: int = Field(default=25, description="[aso_accessibility] unpaired_ulength: RNAplfold -u upper bound (auto-expanded server-side).")
    aso_accessibility_cutoff: Optional[float] = Field(default=None, description="[aso_accessibility] cutoff: RNAplfold -c probability cutoff.")
    aso_accessibility_opening_energies: bool = Field(default=False, description="[aso_accessibility] opening_energies: RNAplfold -O: return opening energies instead of probabilities.")
    aso_accessibility_service_url: str = Field(default='http://127.0.0.1:8003/aso-accessibility', description="[aso_accessibility] service_url: REST endpoint for RNAplfold accessibility.")
    aso_accessibility_shape: Optional[str] = Field(default=None, description="[aso_accessibility] --shape: 上游 RNAplfold --shape，使用 SHAPE 数据。")
    aso_accessibility_print_onthefly: bool = Field(default=False, description="[aso_accessibility] --print_onthefly: 上游 RNAplfold -o，边计算边输出以节省内存。")
    aso_accessibility_verbose: bool = Field(default=False, description="[aso_accessibility] --verbose: 上游 -v，输出详细日志。")
    rnaup_filepath1: str = Field(default=None, description="[rnaup] filepath1: Workspace file with first RNA sequence (target, typically longer).")
    rnaup_filepath2: str = Field(default=None, description="[rnaup] filepath2: Workspace file with second RNA sequence (probe / small RNA).")
    rnaup_temp_c: float = Field(default=37.0, description="[rnaup] temp_c: Folding temperature (Celsius).")
    rnaup_dangles: int = Field(default=2, description="[rnaup] dangles: Dangling-end model.")
    rnaup_no_lp: bool = Field(default=False, description="[rnaup] no_lp: Disallow lonely pairs.")
    rnaup_no_gu: bool = Field(default=False, description="[rnaup] no_gu: Disallow GU pairs.")
    rnaup_no_closing_gu: bool = Field(default=False, description="[rnaup] no_closing_gu: Disallow GU closing pairs.")
    rnaup_salt: Optional[float] = Field(default=None, description="[rnaup] salt: Salt concentration (M).")
    rnaup_no_tetra: bool = Field(default=False, description="[rnaup] no_tetra: Omit special hairpin loop energies.")
    rnaup_energy_model: Optional[int] = Field(default=None, description="[rnaup] energy_model: Energy model index.")
    rnaup_nsp: Optional[str] = Field(default=None, description="[rnaup] nsp: Non-standard pair specification.")
    rnaup_param_file: Optional[str] = Field(default=None, description="[rnaup] param_file: Custom parameter file.")
    rnaup_ulength: int = Field(default=4, description="[rnaup] ulength: Length of unstructured region (-u).")
    rnaup_window: int = Field(default=25, description="[rnaup] window: Maximal interaction region length (-w).")
    rnaup_include_both: bool = Field(default=False, description="[rnaup] include_both: Include unpaired probabilities in both RNAs (-b).")
    rnaup_extend5: int = Field(default=0, description="[rnaup] extend5: Extend interaction on 5' side (-5).")
    rnaup_extend3: int = Field(default=0, description="[rnaup] extend3: Extend interaction on 3' side (-3).")
    rnaup_contributions: str = Field(default='S', description="[rnaup] contributions: Contributions to output (-c): S, H, I, M, E.")
    rnaup_service_url: str = Field(default='http://127.0.0.1:8003/rnaup', description="[rnaup] service_url: REST endpoint for ViennaRNA RNAup.")
    rnaup_constraint1: Optional[str] = Field(default=None, description="[rnaup] constraint1: \u5fae\u670d\u52a1 RnaUpRequest \u652f\u6301\u4f46 wrapper \u672a\u66b4\u9732\u7684 target \u7ea6\u675f\u3002")
    rnaup_constraint2: Optional[str] = Field(default=None, description="[rnaup] constraint2: \u5fae\u670d\u52a1 RnaUpRequest \u652f\u6301\u4f46 wrapper \u672a\u66b4\u9732\u7684 probe \u7ea6\u675f\u3002")
    rnaup_interaction_pairwise: bool = Field(default=False, description="[rnaup] --interaction_pairwise: 上游 --interaction_pairwise，激活成对相互作用模式。")
    rnaup_interaction_first: bool = Field(default=False, description="[rnaup] --interaction_first: 上游 --interaction_first，仅使用第一条序列的相互作用模式。")
    rnaup_no_header: bool = Field(default=False, description="[rnaup] --no_header: 上游 --no_header，输出文件不带头信息。")
    rnaup_no_output_file: bool = Field(default=False, description="[rnaup] --no_output_file: 上游 -o/--no_output_file，微服务内部固定开启，不写入文件。")
    sirna_duplex_filepath: str = Field(default=None, description="[sirna_duplex] filepath: Workspace file with two FASTA records (sense then antisense) or two plain RNA lines without headers.")
    sirna_duplex_temp_c: float = Field(default=37.0, description="[sirna_duplex] temp_c: Folding temperature (Celsius).")
    sirna_duplex_dangles: int = Field(default=2, description="[sirna_duplex] dangles: Dangling-end model.")
    sirna_duplex_no_lp: bool = Field(default=False, description="[sirna_duplex] no_lp: Disallow lonely pairs.")
    sirna_duplex_no_gu: bool = Field(default=False, description="[sirna_duplex] no_gu: Disallow GU pairs.")
    sirna_duplex_no_closing_gu: bool = Field(default=False, description="[sirna_duplex] no_closing_gu: Disallow GU closing pairs.")
    sirna_duplex_salt: Optional[float] = Field(default=None, description="[sirna_duplex] salt: Salt concentration (M).")
    sirna_duplex_no_tetra: bool = Field(default=False, description="[sirna_duplex] no_tetra: Omit special hairpin loop energies.")
    sirna_duplex_energy_model: Optional[int] = Field(default=None, description="[sirna_duplex] energy_model: Energy model index.")
    sirna_duplex_nsp: Optional[str] = Field(default=None, description="[sirna_duplex] nsp: Non-standard pair specification.")
    sirna_duplex_param_file: Optional[str] = Field(default=None, description="[sirna_duplex] param_file: Custom parameter file.")
    sirna_duplex_constraint: Optional[str] = Field(default=None, description="[sirna_duplex] constraint: Hard constraint dot-bracket string.")
    sirna_duplex_shape_file: Optional[str] = Field(default=None, description="[sirna_duplex] shape_file: Path to SHAPE reactivity data file.")
    sirna_duplex_shape_method: str = Field(default='D', description="[sirna_duplex] shape_method: SHAPE method: D, Z, or W.")
    sirna_duplex_concentrations: bool = Field(default=False, description="[sirna_duplex] concentrations: Compute equilibrium concentrations.")
    sirna_duplex_conc_a: Optional[float] = Field(default=None, description="[sirna_duplex] conc_a: Initial monomer A concentration [mol/L].")
    sirna_duplex_conc_b: Optional[float] = Field(default=None, description="[sirna_duplex] conc_b: Initial monomer B concentration [mol/L].")
    sirna_duplex_partfunc: bool = Field(default=False, description="[sirna_duplex] partfunc: Compute partition function for dimer.")
    sirna_duplex_service_url: str = Field(default='http://127.0.0.1:8003/sirna-duplex', description="[sirna_duplex] service_url: REST endpoint for ViennaRNA duplex cofold.")
    sirna_duplex_noPS: bool = Field(default=False, description="[sirna_duplex] --noPS: 微服务内部固定传入 --noPS，禁止生成 PostScript 结构图。")
    sirna_duplex_all_pf: bool = Field(default=False, description="[sirna_duplex] --all_pf: 上游 RNAcofold -a，计算 AA/BB 单体与 AB 二聚体的配分函数。")
    sirna_duplex_centroid: bool = Field(default=False, description="[sirna_duplex] --centroid: 上游 RNAcofold --centroid，计算 centroid 结构。")
    sirna_duplex_gquad: bool = Field(default=False, description="[sirna_duplex] --gquad: 上游 RNAcofold -g，考虑 G-四链体形成。")
    sirna_duplex_maxBPspan: int = Field(default=-1, description="[sirna_duplex] --maxBPspan: 上游 --maxBPspan，限制最大碱基对跨度；默认 -1 表示无限制。")
    sirna_duplex_batch: bool = Field(default=False, description="[sirna_duplex] --batch: 上游 --batch，对多条序列使用同一约束文件。")
    sirna_duplex_verbose: bool = Field(default=False, description="[sirna_duplex] --verbose: 上游 -v，输出详细日志。")
    target_mrna_filepath: str = Field(
        ...,
        description="Path to target mRNA sequence file (plain or FASTA).",
    )
    aso_length: int = Field(
        default=18,
        ge=10,
        le=50,
        description="ASO oligonucleotide length in nucleotides.",
    )
    window_step: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Step size for sliding window scan.",
    )
    top_n_windows: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of top accessibility windows to evaluate with binding tools.",
    )
    binding_evaluation_tool: Literal["rnaup", "rnacofold"] = Field(
        default="rnaup",
        description="Tool for ASO-target binding evaluation: RNAup (thermodynamic) or RNAcofold (duplex MFE).",
    )

class AsoSite(BaseModel):
    """One ranked ASO binding site result."""

    model_config = ConfigDict(extra="allow")

    start: int = Field(..., description="1-based start coordinate on target mRNA.")
    end: int = Field(..., description="1-based end coordinate (inclusive).")
    aso_sequence: str = Field(..., description="Designed ASO sequence (RNA, 5'→3').")
    target_sequence: str = Field(..., description="Target sub-sequence (RNA, 5'→3').")
    mean_unpaired_prob: Optional[float] = None
    joint_unpaired_prob: Optional[float] = None
    binding_dg_kcal_per_mol: Optional[float] = None
    duplex_mfe_kcal_per_mol: Optional[float] = None
    duplex_structure: Optional[str] = None
    composite_score: float = 0.0
    accessibility_rank: Optional[int] = None
    binding_rank: Optional[int] = None
    sum_rank: Optional[int] = None


# Scoring helpers


_RC_MAP: dict[str, str] = {"A": "U", "U": "A", "G": "C", "C": "G"}


def _reverse_complement(rna_seq: str) -> str:
    """Return reverse complement of a normalized RNA sequence."""
    return "".join(_RC_MAP.get(base, base) for base in reversed(rna_seq.upper()))


# Workflow


class AsoTargetScreeningWorkflow(
    BaseDomainWorkflow[AsoScreeningInput, WorkflowResult]
):
    """Screen a target mRNA for optimal ASO binding sites.

    Pipeline:
        1. Full-sequence RNAplfold accessibility profile.
        2. Sliding-window scan → rank by mean unpaired probability.
        3. Top-N windows: design reverse-complement ASO.
        4. Binding evaluation (RNAup or RNAcofold).
        5. Rank-based scoring (accessibility rank + binding rank) + final ranking.
    """

    name = "aso_target_screening"
    input_model = AsoScreeningInput
    description = (
        "Screen a target mRNA for optimal ASO binding sites. "
        "Pipeline: RNAplfold profile → sliding-window ranking → ASO design → "
        "RNAup/RNAcofold binding evaluation → rank-based scoring."
    )
    required_capabilities = [
        "predict_rna_local_accessibility_profile_vienna",
        "compute_aso_target_accessibility_vienna",
        "compute_rna_rna_interaction_vienna",
        "compute_sirna_duplex_binding_vienna",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._trace_records: list[ToolCallRecord] = []

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, inp: Any, *, progress_callback=None) -> WorkflowResult:
        """Accept ``AsoScreeningInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = AsoScreeningInput(**inp)
        self._workflow_state = {}  # reset per run
        self._workflow_state["_aso_input"] = inp
        self._trace_records = []  # reset per run
        result = super().run(inp, progress_callback=progress_callback)
        result._state_writeback = dict(self._workflow_state)  # type: ignore[attr-defined]
        result.trace.extend(self._trace_records)
        return result

    def generate_candidates(self, inp: AsoScreeningInput) -> list[Candidate]:
        """Generate candidate windows from the target mRNA accessibility profile.

        Steps:
          1. Read and normalize target sequence.
          2. Run RNAplfold whole-sequence profile.
          3. Sliding-window scan; compute mean unpaired probability per window.
          4. Keep top ``top_n_windows`` unique windows as candidates.
        """
        target_seq = self._read_target_sequence(inp.target_mrna_filepath)
        if not target_seq:
            _LOGGER.error("aso_empty_target_sequence filepath=%s", inp.target_mrna_filepath)
            return []

        if len(target_seq) < inp.aso_length + 10:
            _LOGGER.error(
                "aso_sequence_too_short len=%d required_at_least=%d",
                len(target_seq),
                inp.aso_length + 10,
            )
            return []

        # Save normalized sequence to workspace for tool calls
        target_fp = save_sequence(
            f">target\n{target_seq}\n", prefix="aso_target"
        )
        self._workflow_state["target_filepath"] = target_fp
        self._workflow_state["target_sequence"] = target_seq

        # ── 1. Full-length RNAplfold profile ──
        profile = self._run_plfold_profile(target_fp)
        if not profile:
            _LOGGER.error("aso_plfold_profile_failed")
            return []

        positions = profile.get("positions", [])
        probs = profile.get("unpaired_prob_1nt", [])
        if len(positions) != len(probs) or not positions:
            _LOGGER.error("aso_plfold_profile_mismatch positions=%d probs=%d", len(positions), len(probs))
            return []

        # Save profile TSV path for reporting
        profile_tsv = profile.get("lunp_profile_tsv_filepath", "")
        self._workflow_state["profile_tsv"] = profile_tsv

        # ── 2. Sliding-window scan ──
        window_size = inp.aso_length
        step = inp.window_step
        windows: list[tuple[int, int, float]] = []  # (start, end, mean_prob)

        for i in range(0, len(target_seq) - window_size + 1, step):
            start_1based = i + 1
            end_1based = i + window_size
            # Map to profile indices (positions are 1-based)
            window_probs: list[float] = []
            for pos, prob in zip(positions, probs):
                if start_1based <= pos <= end_1based:
                    window_probs.append(prob)
            if not window_probs:
                continue
            mean_prob = sum(window_probs) / len(window_probs)
            windows.append((start_1based, end_1based, mean_prob))

        if not windows:
            _LOGGER.error("aso_no_windows_generated")
            return []

        # Sort by mean unpaired prob descending; keep top N
        windows.sort(key=lambda x: x[2], reverse=True)
        top_windows = windows[: inp.top_n_windows]

        candidates: list[Candidate] = []
        seen: set[str] = set()
        for start, end, mean_prob in top_windows:
            target_subseq = target_seq[start - 1 : end]
            aso_seq = _reverse_complement(target_subseq)
            key = f"{start}:{end}:{aso_seq}"
            if key in seen:
                continue
            seen.add(key)

            candidate = Candidate(
                sequence=aso_seq,
                sequence_type="aso",
                source=f"window:{start}-{end}",
                metadata={
                    "aso_sequence": aso_seq,
                    "target_sequence": target_subseq,
                    "target_start": start,
                    "target_end": end,
                    "mean_unpaired_prob": mean_prob,
                    "aso_length": inp.aso_length,
                    "target_filepath": target_fp,
                    "target_full_sequence": target_seq,
                },
            )
            candidates.append(candidate)

        _LOGGER.info(
            "aso_candidates_generated windows=%d top=%d unique=%d",
            len(windows),
            len(top_windows),
            len(candidates),
        )
        return candidates

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Evaluate one ASO candidate window.

        Metrics:
          - Accessibility (region-specific RNAplfold)
          - ASO-target binding (RNAup or RNAcofold)
        """
        target_fp = candidate.metadata.get("target_filepath", "")
        start = int(candidate.metadata.get("target_start", 0))
        end = int(candidate.metadata.get("target_end", 0))
        aso_seq = candidate.metadata.get("aso_sequence", "")
        target_subseq = candidate.metadata.get("target_sequence", "")
        mean_unpaired = candidate.metadata.get("mean_unpaired_prob")

        metrics: dict[str, Any] = {
            "target_start": start,
            "target_end": end,
            "aso_sequence": aso_seq,
            "target_sequence": target_subseq,
            "mean_unpaired_prob": mean_unpaired,
        }

        # Detect binding tool from cached input
        inp = self._workflow_state.get("_aso_input")
        binding_tool = "rnaup"
        if isinstance(inp, AsoScreeningInput):
            binding_tool = inp.binding_evaluation_tool

        # ── 1. Region-specific accessibility (refined) ──
        joint_prob: Optional[float] = None
        if target_fp and start > 0 and end > 0 and self.capabilities.has(
            "compute_aso_target_accessibility_vienna"
        ):
            acc_res = self.capabilities.get(
                "compute_aso_target_accessibility_vienna"
            ).invoke(
                {
                    "filepath": target_fp,
                    "region_start": start,
                    "region_end": end,
                    "aso_oligo_length": len(aso_seq),
                },
                state=self._workflow_state,
            )
            acc_record = ToolCallRecord(
                step_name=f"{candidate.id}_accessibility",
                tool_name="compute_aso_target_accessibility_vienna",
                input_summary=json.dumps(
                    {
                        "filepath": target_fp,
                        "region_start": start,
                        "region_end": end,
                        "aso_oligo_length": len(aso_seq),
                    }
                ),
                output_summary=json.dumps(acc_res.output, default=str)[:500],
                success=acc_res.success,
                error=acc_res.error,
                elapsed_time=getattr(acc_res, "elapsed_time", 0.0),
                artifacts=dict(acc_res.output) if acc_res.success else {},
                metrics={},
            )
            candidate.add_tool_record(acc_record)
            if acc_res.success:
                joint_prob = _pick_float(
                    acc_res.output,
                    "joint_unpaired_prob_stretch_ending_at_region_end",
                )
                refined_mean = _pick_float(
                    acc_res.output, "mean_unpaired_prob_single_nt"
                )
                if refined_mean is not None:
                    metrics["mean_unpaired_prob"] = refined_mean
                    candidate.metadata["mean_unpaired_prob"] = refined_mean
            else:
                _LOGGER.warning("aso_accessibility_failed error=%s", acc_res.error)
        metrics["joint_unpaired_prob"] = joint_prob

        # ── 2. Binding evaluation ──
        binding_dg: Optional[float] = None
        duplex_mfe: Optional[float] = None
        duplex_struct: Optional[str] = None

        if binding_tool == "rnaup" and self.capabilities.has(
            "compute_rna_rna_interaction_vienna"
        ):
            # Save ASO sequence to file for RNAup
            aso_fp = save_sequence(f">aso\n{aso_seq}\n", prefix="aso_oligo")
            try:
                up_res = self.capabilities.get(
                    "compute_rna_rna_interaction_vienna"
                ).invoke(
                    {
                        "filepath1": target_fp,
                        "filepath2": aso_fp,
                    },
                    state=self._workflow_state,
                )
                up_record = ToolCallRecord(
                    step_name=f"{candidate.id}_rnaup_binding",
                    tool_name="compute_rna_rna_interaction_vienna",
                    input_summary=json.dumps({"filepath1": target_fp, "filepath2": aso_fp}),
                    output_summary=json.dumps(up_res.output, default=str)[:500],
                    success=up_res.success,
                    error=up_res.error,
                    elapsed_time=getattr(up_res, "elapsed_time", 0.0),
                    artifacts=dict(up_res.output) if up_res.success else {},
                    metrics={"binding_dg_kcal_per_mol": _pick_float(up_res.output, "interaction_energy")} if up_res.success else {},
                )
                candidate.add_tool_record(up_record)
                if up_res.success:
                    binding_dg = _pick_float(up_res.output, "interaction_energy")
                    duplex_struct = up_res.output.get("interaction_structure")
                else:
                    _LOGGER.warning("aso_rnaup_failed error=%s", up_res.error)
            except Exception as exc:
                _LOGGER.warning("aso_rnaup_exception exc=%s", exc)
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name=f"{candidate.id}_rnaup_binding",
                        tool_name="compute_rna_rna_interaction_vienna",
                        input_summary=json.dumps({"filepath1": target_fp, "filepath2": aso_fp}),
                        output_summary="",
                        success=False,
                        error=str(exc),
                        elapsed_time=0.0,
                        artifacts={},
                        metrics={},
                    )
                )

        elif binding_tool == "rnacofold" and self.capabilities.has(
            "compute_sirna_duplex_binding_vienna"
        ):
            # Build duplex FASTA: target subseq + ASO
            duplex_content = f">target\n{target_subseq}\n>aso\n{aso_seq}\n"
            duplex_fp = save_sequence(duplex_content, prefix="aso_duplex")
            try:
                cof_res = self.capabilities.get(
                    "compute_sirna_duplex_binding_vienna"
                ).invoke(
                    {"filepath": duplex_fp},
                    state=self._workflow_state,
                )
                cof_record = ToolCallRecord(
                    step_name=f"{candidate.id}_rnacofold_binding",
                    tool_name="compute_sirna_duplex_binding_vienna",
                    input_summary=json.dumps({"filepath": duplex_fp}),
                    output_summary=json.dumps(cof_res.output, default=str)[:500],
                    success=cof_res.success,
                    error=cof_res.error,
                    elapsed_time=getattr(cof_res, "elapsed_time", 0.0),
                    artifacts=dict(cof_res.output) if cof_res.success else {},
                    metrics={"duplex_mfe_kcal_per_mol": _pick_float(cof_res.output, "mfe_kcal_per_mol")} if cof_res.success else {},
                )
                candidate.add_tool_record(cof_record)
                if cof_res.success:
                    duplex_mfe = _pick_float(cof_res.output, "mfe_kcal_per_mol")
                    duplex_struct = cof_res.output.get("structure")
                    # Use duplex MFE as proxy for binding strength
                    binding_dg = duplex_mfe
                else:
                    _LOGGER.warning("aso_cofold_failed error=%s", cof_res.error)
            except Exception as exc:
                _LOGGER.warning("aso_cofold_exception exc=%s", exc)
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name=f"{candidate.id}_rnacofold_binding",
                        tool_name="compute_sirna_duplex_binding_vienna",
                        input_summary=json.dumps({"filepath": duplex_fp}),
                        output_summary="",
                        success=False,
                        error=str(exc),
                        elapsed_time=0.0,
                        artifacts={},
                        metrics={},
                    )
                )

        metrics["binding_dg_kcal_per_mol"] = binding_dg
        metrics["duplex_mfe_kcal_per_mol"] = duplex_mfe
        metrics["duplex_structure"] = duplex_struct
        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Return raw score components for later rank-based aggregation.

        Accessibility is the mean unpaired probability [0, 1].
        Binding is the negative thermodynamic ΔG (more negative = stronger binding).
        Both values are used only for ordering (rank-based), so no normalization
        to [0, 1] is required.
        """
        mean_unpaired = metrics.get("mean_unpaired_prob")
        binding_dg = metrics.get("binding_dg_kcal_per_mol")

        acc_score = float(mean_unpaired) if mean_unpaired is not None else 0.0

        bind_score = 0.0
        if binding_dg is not None:
            try:
                bind_score = -float(binding_dg)
            except (TypeError, ValueError):
                pass

        return {
            "accessibility_component": acc_score,
            "binding_component": bind_score,
        }

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return self._empty_result("No ASO candidate sites produced.")

        # ── Rank-based scoring ──
        # Step 1: rank by accessibility (descending) → 1 = best
        by_acc = sorted(
            candidates,
            key=lambda c: c.scores.get("accessibility_component", 0.0),
            reverse=True,
        )
        acc_rank_map = {id(c): r for r, c in enumerate(by_acc, start=1)}

        # Step 2: rank by binding (descending) → 1 = best
        by_bind = sorted(
            candidates,
            key=lambda c: c.scores.get("binding_component", 0.0),
            reverse=True,
        )
        bind_rank_map = {id(c): r for r, c in enumerate(by_bind, start=1)}

        # Step 3: sum ranks and final sort (ascending) → 1 = best
        for c in candidates:
            c.scores["accessibility_rank"] = float(acc_rank_map[id(c)])
            c.scores["binding_rank"] = float(bind_rank_map[id(c)])
            c.scores["sum_rank"] = float(acc_rank_map[id(c)] + bind_rank_map[id(c)])

        ranked = sorted(
            candidates,
            key=lambda c: c.scores.get("sum_rank", float("inf")),
        )
        for idx, c in enumerate(ranked, start=1):
            c.rank = idx
            c.scores["composite_score"] = float(idx)  # 1 = best

        best = ranked[0] if ranked else None

        # Build per-site detail lines
        detail_lines: list[str] = []
        sites: list[AsoSite] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            start = mb.get("target_start", 0)
            end = mb.get("target_end", 0)
            aso_seq = mb.get("aso_sequence", "")
            target_seq = mb.get("target_sequence", "")
            mean_up = mb.get("mean_unpaired_prob")
            bind_dg = mb.get("binding_dg_kcal_per_mol")
            duplex_mfe = mb.get("duplex_mfe_kcal_per_mol")

            site = AsoSite(
                start=start,
                end=end,
                aso_sequence=aso_seq,
                target_sequence=target_seq,
                mean_unpaired_prob=mean_up,
                binding_dg_kcal_per_mol=bind_dg,
                duplex_mfe_kcal_per_mol=duplex_mfe,
                duplex_structure=mb.get("duplex_structure"),
                composite_score=scores.get("composite_score", 0.0),
                accessibility_rank=int(scores["accessibility_rank"]),
                binding_rank=int(scores["binding_rank"]),
                sum_rank=int(scores["sum_rank"]),
            )
            sites.append(site)

            parts = [
                f"#{i}",
                f"pos={start}-{end}",
                f"ASO={aso_seq}",
                f"accessibility={mean_up:.3f}" if mean_up is not None else "accessibility=N/A",
                f"bindingΔG={bind_dg:.2f}" if bind_dg is not None else "bindingΔG=N/A",
                f"duplexMFE={duplex_mfe:.2f}" if duplex_mfe is not None else "duplexMFE=N/A",
                f"acc_rank={int(scores['accessibility_rank'])}",
                f"bind_rank={int(scores['binding_rank'])}",
                f"sum_rank={int(scores['sum_rank'])}",
                f"composite={scores.get('composite_score', 0.0):.1f}",
            ]
            detail_lines.append(" | ".join(parts))

        # Persist site list as JSON artifact
        sites_json = ""
        try:
            sites_json = "\n".join(s.model_dump_json() for s in sites)
        except Exception:
            pass
        if sites_json:
            save_text_file(sites_json, prefix="aso_sites", suffix=".jsonl")

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_composite_score={best.scores.get('composite_score') if best else None}",
            f"profile_tsv={self._workflow_state.get('profile_tsv', 'N/A')}",
            "---",
            *detail_lines,
        ]
        return WorkflowResult(
            success=True,
            task_id=f"aso_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _read_target_sequence(self, filepath: str) -> str:
        """Read and normalize target mRNA sequence."""
        try:
            raw = read_sequence(filepath)
            seq = normalize_rna_sequence(raw)
            return seq
        except Exception as exc:
            _LOGGER.error("aso_read_target_failed path=%s err=%s", filepath, exc)
            return ""

    def _run_plfold_profile(self, target_filepath: str) -> Optional[dict[str, Any]]:
        """Run RNAplfold whole-sequence profile and return result dict."""
        if not self.capabilities.has("predict_rna_local_accessibility_profile_vienna"):
            _LOGGER.warning("aso_capability_missing predict_rna_local_accessibility_profile_vienna")
            return None
        cap = self.capabilities.get("predict_rna_local_accessibility_profile_vienna")
        cap_result = cap.invoke(
            {"filepath": target_filepath},
            state=self._workflow_state,
        )
        record = ToolCallRecord(
            step_name="plfold_profile",
            tool_name="predict_rna_local_accessibility_profile_vienna",
            input_summary=json.dumps({"filepath": target_filepath}),
            output_summary=json.dumps(cap_result.output, default=str)[:500],
            success=cap_result.success,
            error=cap_result.error,
            elapsed_time=getattr(cap_result, "elapsed_time", 0.0),
            artifacts=dict(cap_result.output) if cap_result.success else {},
            metrics={"position_count": len(cap_result.output.get("positions", []))} if cap_result.success else {},
        )
        self._trace_records.append(record)
        if not cap_result.success:
            _LOGGER.warning("aso_plfold_failed error=%s", cap_result.error)
            return None
        return dict(cap_result.output)


