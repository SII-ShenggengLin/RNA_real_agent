"""RNA-small molecule interaction prediction workflow (Layer 2).

Given an RNA sequence and a ligand SMILES, predict binding propensity
using RNAsmol and/or GerNA-Bind, evaluate, score, and rank.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  RnaSmallMoleculeInteractionWorkflow INTERFACE LOCK (v1.1.0) —— 禁止单方面变更 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 rna_small_molecule_interaction workflow 的权威实现。任何字段增删、   ║
║  函数签名变动、返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：  ║
║                                                                               ║
║    - agent_core/workflows/rna_small_molecule_interaction.py  ← 本文件         ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/quality_profiles/__init__.py                                  ║
║    - agent_core/workflows/__init__.py                                         ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - tests/test_rna_small_molecule_interaction.py                             ║
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
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.sequence_utils import _pick_float
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow

_LOGGER = logging.getLogger("agent_core.workflows.rna_small_molecule_interaction")


class RnaSmallMoleculeInteractionInput(BaseModel):
    """Input for RNA-small molecule interaction prediction."""
    # Tool-level parameter overrides (from tools_parameter_analysis.json)
    rnasmol_filepath: str = Field(default=None, description="[rnasmol] filepath: Path to a file containing the RNA sequence (plain text or FASTA). The wrapper reads the sequence text.")
    rnasmol_smiles: str = Field(default=None, description="[rnasmol] smiles: Ligand SMILES string.")
    rnasmol_service_url: str = Field(default='http://127.0.0.1:8007/score', description="[rnasmol] service_url: HTTP endpoint of the RNAsmol microservice.")
    rnasmol_checkpoint_path: str = Field(default=None, description="[rnasmol] checkpoint_path: Explicit path to a trained RNAsmol .pt checkpoint. Overrides auto-discovery.")
    rnasmol_dataset: str = Field(default=None, description="[rnasmol] dataset: Training dataset source hint for checkpoint auto-selection (e.g. 'pdb', 'robin').")
    rnasmol_perturbation_type: str = Field(default=None, description="[rnasmol] perturbation_type: Data-perturbation strategy hint for checkpoint auto-selection (e.g. 'molperturbation', 'netperturbation', 'rnaperturbation').")
    rnasmol_device: str = Field(default=None, description="[rnasmol] device: PyTorch device string such as 'cuda:0' or 'cpu'. Falls back to RNASMOL_DEVICE env var or cuda:0.")
    rnasmol_target_len: int = Field(default=500, description="[rnasmol] target_len (internal padding length): Fixed length to which the RNA sequence is padded or truncated in the microservice preprocessing. Not user exposed.")
    gernabind_filepath: str = Field(default=None, description="[gernabind] filepath: Path to a file containing the RNA sequence (plain text or FASTA).")
    gernabind_smiles: str = Field(default=None, description="[gernabind] smiles: Ligand SMILES string.")
    gernabind_service_url: str = Field(default='http://127.0.0.1:8010/score', description="[gernabind] service_url: HTTP endpoint of the GerNA-Bind microservice.")
    gernabind_checkpoint_path: str = Field(default=None, description="[gernabind] checkpoint_path: Explicit path to a GerNA-Bind affinity checkpoint.")
    gernabind_pdb_path: str = Field(default=None, description="[gernabind] pdb_path: Optional precomputed RNA PDB structure. If omitted, the service calls the RhoFold microservice to generate one.")
    gernabind_secondary_structure: str = Field(default=None, description="[gernabind] secondary_structure: Optional dot-bracket RNA secondary structure. If omitted, the service runs RNAfold.")
    gernabind_device: str = Field(default=None, description="[gernabind] device: Torch device such as 'cuda:0' or 'cpu'. Falls back to GERNABIND_DEVICE env var.")
    gernabind_dataset: str = Field(default=None, description="[gernabind] dataset: Dataset hint for selecting the default affinity checkpoint. Supported: 'Robin', 'Biosensor'.")
    gernabind_split_method: str = Field(default=None, description="[gernabind] split_method: Split-method hint for checkpoint selection. Supported: 'random', 'RNA', 'mol', 'both'.")
    gernabind_rhofold_service_url: str = Field(default=None, description="[gernabind] rhofold_service_url: Microservice-only override for the RhoFold endpoint used when pdb_path is omitted.")
    rna_sequence: str = Field(..., description="RNA sequence (A, U, G, C).")
    smiles: str = Field(..., description="Ligand SMILES string.")
    rna_structure_path: Optional[str] = Field(
        default=None,
        description="Optional RNA 3D structure (PDB/CIF) for GerNA-Bind. Only provide if the user explicitly supplies a structure file.",
    )
    secondary_structure: Optional[str] = Field(
        default=None,
        description="Optional dot-bracket secondary structure for GerNA-Bind. Only provide if the user explicitly supplies it.",
    )
    scoring_tools: List[Literal["rnasmol", "gernabind"]] = Field(
        default_factory=lambda: ["rnasmol", "gernabind"],
        description=(
            "Which scoring tools to run. "
            "DEFAULT ['rnasmol', 'gernabind'] is strongly recommended — "
            "running both tools together gives more reliable predictions. "
            "Only reduce to one tool if the user explicitly asks for it."
        ),
    )
    dataset: Optional[str] = Field(
        default=None,
        description=(
            "GerNA-Bind dataset hint (e.g. Robin, Biosensor). "
            "DEFAULT None auto-selects the best general-purpose checkpoint. "
            "Only override if the user explicitly names a specific dataset."
        ),
    )
    split_method: Optional[str] = Field(
        default=None,
        description=(
            "GerNA-Bind split method hint (e.g. random, RNA, mol, both). "
            "DEFAULT None auto-selects the most robust split method. "
            "Only override if the user explicitly requests a different split."
        ),
    )
    @field_validator("rna_sequence")
    @classmethod
    def _validate_rna_sequence(cls, v: str) -> str:
        seq = v.upper().replace("T", "U")
        invalid = set(ch for ch in seq if ch not in "AUGC")
        if invalid:
            raise ValueError(
                f"Invalid RNA characters: {''.join(sorted(invalid))}. "
                "Only A, U, G, C (and T) are allowed."
            )
        return v
    @field_validator("smiles")
    @classmethod
    def _validate_smiles(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("SMILES string cannot be empty")
        # Heuristic sanity check: must contain common organic atom symbols or bracket notation
        if not any(ch in stripped for ch in "CNOSPFIBrIcl[]"):
            raise ValueError("SMILES does not appear to contain valid atom symbols")
        return stripped

class RnaSmallMoleculeInteractionWorkflow(
    BaseDomainWorkflow[RnaSmallMoleculeInteractionInput, WorkflowResult]
):
    input_model = RnaSmallMoleculeInteractionInput

    """Predict RNA-ligand binding using RNAsmol and/or GerNA-Bind.

    Quality review / retry policy
    -----------------------------
    This workflow intentionally does NOT use an LLM quality review and has no
    ``QualityProfile`` beyond the deterministic placeholder.

    Reason: this is a **prediction/scoring** task, not a generative design task.
    The inputs (RNA sequence + SMILES) are fixed; re-running the same
    classifier with the same inputs will produce identical results.  There is
    no design parameter (e.g. length, hotspot, seed) that can be adjusted to
    improve candidate quality on retry.  Therefore a retry loop would only
    waste compute without improving the outcome.
    """

    name = "rna_small_molecule_interaction"
    task_type = "rna_small_molecule"
    description = (
        "Predict RNA-small molecule interaction propensity. "
        "Runs RNAsmol and/or GerNA-Bind on a given RNA sequence + SMILES, "
        "then scores and ranks the interaction."
    )
    required_capabilities = [
        "score_rna_ligand_binding_with_rnasmol",
        "score_rna_ligand_binding_with_gernabind",
        # GerNA-Bind folds the RNA with RhoFold at runtime when no PDB is
        # supplied, so the RhoFold service is a hard runtime dependency.
        "predict_rna_tertiary_structure_with_rhofold",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, inp: Any, *, progress_callback=None) -> WorkflowResult:
        """Accept either ``RnaSmallMoleculeInteractionInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = RnaSmallMoleculeInteractionInput(**inp)
        self._workflow_state = {}  # reset per run
        result = super().run(inp, progress_callback=progress_callback)
        result._state_writeback = dict(self._workflow_state)  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: RnaSmallMoleculeInteractionInput) -> list[Candidate]:
        """Wrap the user-provided RNA + SMILES as a single candidate."""
        candidate = Candidate(
            sequence=inp.rna_sequence.upper().replace("T", "U"),
            sequence_type="rna",
            source="user_input",
            metadata={
                "smiles": inp.smiles,
                "rna_structure_path": inp.rna_structure_path,
                "secondary_structure": inp.secondary_structure,
                "scoring_tools": inp.scoring_tools,
                "dataset": inp.dataset,
                "split_method": inp.split_method,
            },
        )
        _LOGGER.info(
            "candidate_prepared rna_len=%d smiles=%s tools=%s",
            len(candidate.sequence),
            inp.smiles,
            inp.scoring_tools,
        )
        return [candidate]

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Run RNAsmol and/or GerNA-Bind on the candidate."""
        seq = candidate.sequence
        smiles = candidate.metadata.get("smiles", "")
        filepath = save_sequence(seq, prefix="rna_ligand")
        candidate.metadata["workspace_filepath"] = filepath

        metrics: dict[str, Any] = {
            "rna_sequence": seq,
            "smiles": smiles,
            "sequence_length": len(seq),
        }

        # ── RNAsmol ──
        rnasmol_prob: Optional[float] = None
        rnasmol_label: Optional[int] = None
        if "rnasmol" in candidate.metadata.get("scoring_tools", []):
            rnasmol_args: dict[str, Any] = {
                "filepath": filepath,
                "smiles": smiles,
            }
            rnasmol_dataset = candidate.metadata.get("dataset")
            if rnasmol_dataset:
                rnasmol_args["dataset"] = rnasmol_dataset

            if self.capabilities.has("score_rna_ligand_binding_with_rnasmol"):
                try:
                    res = self.capabilities.get(
                        "score_rna_ligand_binding_with_rnasmol"
                    ).invoke(
                        rnasmol_args,
                        state=self._workflow_state,
                    )
                    if res.success:
                        rnasmol_prob = _pick_float(res.output, "probability_positive")
                        rnasmol_label = res.output.get("predicted_label")
                    else:
                        _LOGGER.warning("rnasmol_scoring_failed error=%s", res.error)

                    record = ToolCallRecord(
                        step_name="evaluate:rnasmol",
                        tool_name="score_rna_ligand_binding_with_rnasmol",
                        input_summary=json.dumps(rnasmol_args, default=str),
                        output_summary=json.dumps(res.output, default=str)[:500],
                        success=res.success,
                        error=res.error,
                        elapsed_time=res.elapsed_time,
                        artifacts=dict(res.output) if res.success else {},
                        metrics={
                            "probability_positive": rnasmol_prob,
                            "predicted_label": rnasmol_label,
                        } if res.success else {},
                    )
                    candidate.add_tool_record(record)
                except Exception as exc:
                    _LOGGER.error("rnasmol_scoring_exception exc=%s", exc)
                    record = ToolCallRecord(
                        step_name="evaluate:rnasmol",
                        tool_name="score_rna_ligand_binding_with_rnasmol",
                        input_summary=json.dumps(rnasmol_args, default=str),
                        output_summary="",
                        success=False,
                        error=str(exc),
                        elapsed_time=0.0,
                    )
                    candidate.add_tool_record(record)
            else:
                _LOGGER.warning("capability_missing score_rna_ligand_binding_with_rnasmol")
                record = ToolCallRecord(
                    step_name="evaluate:rnasmol",
                    tool_name="score_rna_ligand_binding_with_rnasmol",
                    input_summary=json.dumps(rnasmol_args, default=str),
                    output_summary="",
                    success=False,
                    error="capability_missing",
                    elapsed_time=0.0,
                )
                candidate.add_tool_record(record)
        metrics["rnasmol_probability_positive"] = rnasmol_prob
        metrics["rnasmol_predicted_label"] = rnasmol_label

        # ── GerNA-Bind ──
        gernabind_prob: Optional[float] = None
        gernabind_label: Optional[int] = None
        if "gernabind" in candidate.metadata.get("scoring_tools", []):
            gernabind_args: dict[str, Any] = {
                "filepath": filepath,
                "smiles": smiles,
            }
            pdb_path = candidate.metadata.get("rna_structure_path")
            if pdb_path:
                gernabind_args["pdb_path"] = pdb_path
            sec_struct = candidate.metadata.get("secondary_structure")
            if sec_struct:
                gernabind_args["secondary_structure"] = sec_struct
            dataset = candidate.metadata.get("dataset")
            if dataset:
                gernabind_args["dataset"] = dataset
            split = candidate.metadata.get("split_method")
            if split:
                gernabind_args["split_method"] = split

            if self.capabilities.has("score_rna_ligand_binding_with_gernabind"):
                try:
                    res = self.capabilities.get(
                        "score_rna_ligand_binding_with_gernabind"
                    ).invoke(gernabind_args, state=self._workflow_state)
                    if res.success:
                        gernabind_prob = _pick_float(res.output, "probability_positive")
                        gernabind_label = res.output.get("predicted_label")
                    else:
                        _LOGGER.warning("gernabind_scoring_failed error=%s", res.error)

                    record = ToolCallRecord(
                        step_name="evaluate:gernabind",
                        tool_name="score_rna_ligand_binding_with_gernabind",
                        input_summary=json.dumps(gernabind_args, default=str),
                        output_summary=json.dumps(res.output, default=str)[:500],
                        success=res.success,
                        error=res.error,
                        elapsed_time=res.elapsed_time,
                        artifacts=dict(res.output) if res.success else {},
                        metrics={
                            "probability_positive": gernabind_prob,
                            "predicted_label": gernabind_label,
                        } if res.success else {},
                    )
                    candidate.add_tool_record(record)
                except Exception as exc:
                    _LOGGER.error("gernabind_scoring_exception exc=%s", exc)
                    record = ToolCallRecord(
                        step_name="evaluate:gernabind",
                        tool_name="score_rna_ligand_binding_with_gernabind",
                        input_summary=json.dumps(gernabind_args, default=str),
                        output_summary="",
                        success=False,
                        error=str(exc),
                        elapsed_time=0.0,
                    )
                    candidate.add_tool_record(record)
            else:
                _LOGGER.warning("capability_missing score_rna_ligand_binding_with_gernabind")
                record = ToolCallRecord(
                    step_name="evaluate:gernabind",
                    tool_name="score_rna_ligand_binding_with_gernabind",
                    input_summary=json.dumps(gernabind_args, default=str),
                    output_summary="",
                    success=False,
                    error="capability_missing",
                    elapsed_time=0.0,
                )
                candidate.add_tool_record(record)
        metrics["gernabind_probability_positive"] = gernabind_prob
        metrics["gernabind_predicted_label"] = gernabind_label

        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        return score_rna_ligand_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return self._empty_result("No candidates to evaluate.")

        ranked = sort_candidates_by_score(
            candidates, score_key="total_score", descending=True
        )
        best = ranked[0] if ranked else None

        # Check if any scoring tool actually produced a result
        has_valid_score = False
        for c in ranked:
            mb = c.metadata.get("metrics_bundle", {})
            if (
                mb.get("rnasmol_probability_positive") is not None
                or mb.get("gernabind_probability_positive") is not None
            ):
                has_valid_score = True
                break

        if not has_valid_score:
            return WorkflowResult(
                success=False,
                task_id=f"rna_ligand_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                summary="No valid scoring results from RNAsmol or GerNA-Bind.",
                errors=["all_scoring_tools_failed"],
                all_candidates=ranked,
            )

        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            parts = [
                f"#{i}",
                f"source={c.source}",
                f"len={len(c.sequence)}nt",
            ]
            if mb.get("rnasmol_probability_positive") is not None:
                parts.append(f"RNAsmol_prob={mb['rnasmol_probability_positive']:.4f}")
            else:
                parts.append("RNAsmol_prob=N/A")
            if mb.get("gernabind_probability_positive") is not None:
                parts.append(f"GerNA-Bind_prob={mb['gernabind_probability_positive']:.4f}")
            else:
                parts.append("GerNA-Bind_prob=N/A")
            total = scores.get("total_score")
            parts.append(f"total_score={total:.4f}" if total is not None else "total_score=N/A")
            detail_lines.append(" | ".join(parts))

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_total_score={best.scores.get('total_score') if best else None}",
            "---",
            *detail_lines,
        ]
        return WorkflowResult(
            success=True,
            task_id=f"rna_ligand_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )


def score_rna_ligand_candidate(metrics: dict[str, Any]) -> dict[str, float]:
    """Standalone scoring function for RNA-ligand interaction.

    Averages available probability scores from RNAsmol and GerNA-Bind.
    Each probability is already in [0, 1].
    """
    rnasmol_prob = metrics.get("rnasmol_probability_positive")
    gernabind_prob = metrics.get("gernabind_probability_positive")

    scores: dict[str, float] = {}
    components: list[float] = []

    if rnasmol_prob is not None:
        scores["rnasmol_component"] = float(rnasmol_prob)
        components.append(scores["rnasmol_component"])
    else:
        scores["rnasmol_component"] = 0.0

    if gernabind_prob is not None:
        scores["gernabind_component"] = float(gernabind_prob)
        components.append(scores["gernabind_component"])
    else:
        scores["gernabind_component"] = 0.0

    if components:
        scores["total_score"] = sum(components) / len(components)
    else:
        scores["total_score"] = 0.0

    return scores