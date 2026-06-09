"""RNA tertiary structure → sequence design workflow (Layer 2).

Input PDB/CIF structure → inverse folding (RhoDesign / RiboDiffusion) →
GC + fold (ViennaRNA) + RhoFold evaluation + structure alignment (RMSD/TM-score) →
scoring → ranking → WorkflowResult.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  RnaTertiaryStructureDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 rna_tertiary_structure_design workflow 的权威实现。任何字段增删、   ║
║  函数签名变动、返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试： ║
║                                                                               ║
║    - agent_core/workflows/rna_tertiary_structure_design.py  ← 本文件         ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/workflows/registry.py                                         ║
║    - agent_core/state.py                                                      ║
║    - agent_core/capabilities/writebacks.py                                    ║
║    - agent_core/capabilities/base.py                                          ║
║    - agent_core/planning/base.py                                              ║
║    - agent_core/planning/llm_critic.py                                        ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - agent_core/llm_config.py                                                 ║
║    - microservices/rhofold_service/main.py                                    ║
║    - microservices/rhodesign_service/main.py                                  ║
║    - microservices/ribodiffusion_service/main.py                              ║
║    - microservices/rna_sequence_metrics_service/main.py                       ║
║    - microservices/viennarna_service/main.py                                  ║
║    - tests/test_rna_tertiary_structure_design.py                              ║
║    - tests/test_rna_tertiary_structure_design_layer3.py                       ║
║    - tests/test_rna_tertiary_structure_design_comprehensive.py                ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Key design principles
---------------------
1. **Structure-first**: Both RhoDesign and RiboDiffusion perform inverse folding
   from a 3D backbone, generating sequences compatible with the input tertiary
   structure.
2. **Foldability-centric scoring**: Unlike mRNA workflows that optimise CAI,
   this workflow optimises structural consistency (RhoFold pLDDT, TM-score, RMSD)
   and thermodynamic stability (ViennaRNA MFE).
3. **Graceful degradation**: If one design tool fails, candidates from the
   remaining tool(s) are still evaluated and ranked.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import resolve_project_path, save_sequence
from agent_core.sequence_utils import _pick_float
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow

_LOGGER = logging.getLogger("agent_core.workflows.rna_tertiary_structure_design")

# Input model


class RnaTertiaryStructureDesignInput(BaseModel):
    """Input for the RNA tertiary-structure-guided sequence design workflow."""

    model_config = ConfigDict(extra="forbid")

    structure_filepath: str = Field(
        ...,
        description="Path to the input RNA tertiary structure file (PDB or CIF).",
    )
    secondary_structure_filepath: Optional[str] = Field(
        default=None,
        description="Optional secondary structure contact-map (``.npy``) for RhoDesign 2D-assisted mode.",
    )
    design_tools: Literal["all", "rhodesign", "ribodiffusion"] = Field(
        default="all",
        description="Which inverse-folding tool(s) to invoke.",
    )
    n_samples_per_tool: int = Field(
        default=3, ge=1, le=20, description="Number of sequences to generate per tool."
    )
    rhodesign_temperature: float = Field(
        default=1e-5, ge=0.0, description="Base sampling temperature for RhoDesign."
    )
    rhodesign_temperature_range: float = Field(
        default=0.05,
        ge=0.0,
        description="Temperature sweep range for multi-sample RhoDesign calls. "
                    "When n_samples_per_tool > 1, temperatures are linearly spaced "
                    "around the base value within ±this range.",
    )
    ribodiffusion_sampling_steps: int = Field(
        default=50, ge=1, le=500, description="Diffusion sampling steps for RiboDiffusion."
    )
    ribodiffusion_cond_scale: float = Field(
        default=-1.0, description="Classifier-free guidance scale for RiboDiffusion (-1 = default)."
    )
    ribodiffusion_checkpoint_name: str = Field(
        default="exp_inf", description="RiboDiffusion checkpoint basename."
    )
    # Scoring weights
    weight_rhofold: float = Field(default=0.50, description="Weight for RhoFold pLDDT component.")
    weight_rmsd: float = Field(default=0.50, description="Weight for RMSD component.")


# Workflow implementation


class RnaTertiaryStructureDesignWorkflow(
    BaseDomainWorkflow[RnaTertiaryStructureDesignInput, WorkflowResult]
):
    """Structure-driven RNA sequence design: 3D structure → inverse folding → evaluate → rank."""

    name = "rna_tertiary_structure_design"
    description = (
        "Design RNA sequences from a tertiary structure using inverse-folding tools. "
        "Pipeline: RhoDesign / RiboDiffusion generation → GC + ViennaRNA fold + RhoFold + "
        "structure alignment (RMSD/TM-score) evaluation → scoring → ranking."
    )
    required_capabilities = [
        "design_rna_sequence_with_rhodesign",
        "design_rna_inverse_fold_with_ribodiffusion",
        "compute_rna_sequence_gc_content",
        "predict_rna_secondary_structure",
        "predict_rna_tertiary_structure_with_rhofold",
        "score_structure_alignment",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._trace_records: list[ToolCallRecord] = []

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        inp: Any,
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """Accept either ``RnaTertiaryStructureDesignInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = RnaTertiaryStructureDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._trace_records = []
        self._workflow_state["_tertiary_design_input"] = inp
        result = super().run(inp, progress_callback=progress_callback)
        # Merge workflow-level trace records + per-candidate tool records
        result.trace = list(self._trace_records) + result.trace
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: RnaTertiaryStructureDesignInput) -> list[Candidate]:
        """Generate RNA sequence candidates from the input 3D structure.

        Steps:
          1. Validate the input structure file exists.
          2. Call requested inverse-folding tool(s).
             - RiboDiffusion: one call with ``n_samples = n_samples_per_tool``.
             - RhoDesign: ``n_samples_per_tool`` independent calls with temperatures
               linearly spaced around ``rhodesign_temperature ± rhodesign_temperature_range``.
          3. Deduplicate by sequence and build Candidate objects.
        """
        struct_path = resolve_project_path(inp.structure_filepath)
        if not Path(struct_path).exists():
            _LOGGER.error("structure_file_not_found path=%s", struct_path)
            return []

        sequences: list[tuple[str, str, dict[str, Any]]] = []  # (seq, source, extra_meta)
        rhodesign_count = 0
        ribodiffusion_count = 0

        # ── RhoDesign ──
        if inp.design_tools in ("all", "rhodesign"):
            if self.capabilities.has("design_rna_sequence_with_rhodesign"):
                # Build temperature sweep
                n = inp.n_samples_per_tool
                if n == 1:
                    temps = [inp.rhodesign_temperature]
                else:
                    half = inp.rhodesign_temperature_range
                    temps = [
                        inp.rhodesign_temperature - half + (2 * half * i / max(1, n - 1))
                        for i in range(n)
                    ]
                    # Clamp to non-negative
                    temps = [max(0.0, t) for t in temps]

                for tidx, temp in enumerate(temps, start=1):
                    try:
                        cap = self.capabilities.get("design_rna_sequence_with_rhodesign")
                        args: dict[str, Any] = {
                            "pdb_filepath": struct_path,
                            "temperature": temp,
                        }
                        if inp.secondary_structure_filepath:
                            args["secondary_structure_filepath"] = resolve_project_path(
                                inp.secondary_structure_filepath
                            )
                        cap_result = cap.invoke(args, state=self._workflow_state)
                        # Record tool call regardless of success/failure
                        record = ToolCallRecord(
                            step_name=f"generate_rhodesign_t{tidx}",
                            tool_name="design_rna_sequence_with_rhodesign",
                            input_summary=json.dumps(args, default=str)[:500],
                            output_summary=json.dumps(cap_result.output, default=str)[:500],
                            success=cap_result.success,
                            error=cap_result.error,
                            elapsed_time=getattr(cap_result, "elapsed_time", 0.0),
                            artifacts=dict(cap_result.output) if cap_result.success else {},
                            metrics={"predicted_sequence_len": len(cap_result.output.get("predicted_sequence", ""))} if cap_result.success else {},
                        )
                        self._trace_records.append(record)
                        if cap_result.success:
                            seq = str(cap_result.output.get("predicted_sequence", ""))
                            if seq:
                                meta = {
                                    "recovery_rate": cap_result.output.get("recovery_rate"),
                                    "output_fasta_filepath": cap_result.output.get("output_fasta_filepath"),
                                    "input_pdb_filepath": cap_result.output.get("input_pdb_filepath"),
                                    "temperature": temp,
                                }
                                sequences.append((seq, f"rhodesign_t{tidx}", meta))
                                rhodesign_count += 1
                                # If the tool returned multiple generated sequences, use them too
                                gen_seqs = cap_result.output.get("generated_sequences")
                                if isinstance(gen_seqs, list):
                                    for gidx, gseq in enumerate(gen_seqs):
                                        if gseq and gseq != seq:
                                            sequences.append((gseq, f"rhodesign_t{tidx}_g{gidx}", meta))
                                            rhodesign_count += 1
                            else:
                                _LOGGER.warning("rhodesign_returned_empty_sequence tidx=%d", tidx)
                        else:
                            _LOGGER.warning("rhodesign_failed tidx=%d error=%s", tidx, cap_result.error)
                    except Exception as exc:
                        _LOGGER.error("rhodesign_exception tidx=%d exc=%s", tidx, exc)
                        self._trace_records.append(
                            ToolCallRecord(
                                step_name=f"generate_rhodesign_t{tidx}",
                                tool_name="design_rna_sequence_with_rhodesign",
                                input_summary=json.dumps(args, default=str)[:500] if 'args' in dir() else "",
                                output_summary="",
                                success=False,
                                error=str(exc),
                                elapsed_time=0.0,
                            )
                        )
            else:
                _LOGGER.warning("capability_missing design_rna_sequence_with_rhodesign")

        # ── RiboDiffusion ──
        if inp.design_tools in ("all", "ribodiffusion"):
            if self.capabilities.has("design_rna_inverse_fold_with_ribodiffusion"):
                try:
                    cap = self.capabilities.get("design_rna_inverse_fold_with_ribodiffusion")
                    rd_args: dict[str, Any] = {
                        "pdb_filepath": struct_path,
                        "n_samples": inp.n_samples_per_tool,
                        "sampling_steps": inp.ribodiffusion_sampling_steps,
                        "cond_scale": inp.ribodiffusion_cond_scale,
                        "checkpoint_name": inp.ribodiffusion_checkpoint_name,
                    }
                    cap_result = cap.invoke(rd_args, state=self._workflow_state)
                    # Record tool call regardless of success/failure
                    record = ToolCallRecord(
                        step_name="generate_ribodiffusion",
                        tool_name="design_rna_inverse_fold_with_ribodiffusion",
                        input_summary=json.dumps(rd_args, default=str)[:500],
                        output_summary=json.dumps(cap_result.output, default=str)[:500],
                        success=cap_result.success,
                        error=cap_result.error,
                        elapsed_time=getattr(cap_result, "elapsed_time", 0.0),
                        artifacts=dict(cap_result.output) if cap_result.success else {},
                        metrics={"predicted_sequence_len": len(cap_result.output.get("predicted_sequence", ""))} if cap_result.success else {},
                    )
                    self._trace_records.append(record)
                    if cap_result.success:
                        seq = str(cap_result.output.get("predicted_sequence", ""))
                        if seq:
                            meta = {
                                "recovery_rate": cap_result.output.get("recovery_rate"),
                                "output_fasta_filepaths": cap_result.output.get("output_fasta_filepaths"),
                                "input_pdb_filepath": cap_result.output.get("input_pdb_filepath"),
                            }
                            sequences.append((seq, "ribodiffusion", meta))
                            ribodiffusion_count += 1
                            # Multi-sample list
                            gen_seqs = cap_result.output.get("generated_sequences")
                            if isinstance(gen_seqs, list):
                                for gidx, gseq in enumerate(gen_seqs):
                                    if gseq and gseq != seq:
                                        sequences.append((gseq, f"ribodiffusion_g{gidx}", meta))
                                        ribodiffusion_count += 1
                        else:
                            _LOGGER.warning("ribodiffusion_returned_empty_sequence")
                    else:
                        _LOGGER.warning("ribodiffusion_failed error=%s", cap_result.error)
                except Exception as exc:
                    _LOGGER.error("ribodiffusion_exception exc=%s", exc)
                    self._trace_records.append(
                        ToolCallRecord(
                            step_name="generate_ribodiffusion",
                            tool_name="design_rna_inverse_fold_with_ribodiffusion",
                            input_summary=json.dumps(rd_args, default=str)[:500] if 'rd_args' in dir() else "",
                            output_summary="",
                            success=False,
                            error=str(exc),
                            elapsed_time=0.0,
                        )
                    )
            else:
                _LOGGER.warning("capability_missing design_rna_inverse_fold_with_ribodiffusion")

        _LOGGER.info(
            "generate_candidates_complete rhodesign=%d ribodiffusion=%d total=%d workflow=%s",
            rhodesign_count,
            ribodiffusion_count,
            len(sequences),
            self.name,
        )

        if not sequences:
            _LOGGER.error("no_sequences_generated")
            return []

        # Deduplicate by sequence
        seen: set[str] = set()
        candidates: list[Candidate] = []
        for seq, source, extra_meta in sequences:
            if not seq or seq in seen:
                continue
            seen.add(seq)
            candidates.append(
                Candidate(
                    sequence=seq,
                    sequence_type="rna",
                    source=source,
                    metadata={
                        "input_structure_filepath": struct_path,
                        "design_tool": source.split("_")[0],
                        "tool_metadata": extra_meta,
                    },
                )
            )

        _LOGGER.info(
            "candidates_generated rhodesign=%d ribodiffusion=%d unique=%d workflow=%s",
            rhodesign_count,
            ribodiffusion_count,
            len(candidates),
            self.name,
        )
        return candidates

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Evaluate a candidate sequence.

        Metrics collected:
          - gc_content, sequence_length
          - vienna_mfe, vienna_structure (ViennaRNA RNAfold)
          - rhofold_mean_plddt, rhofold_pdb_path (RhoFold tertiary prediction)
          - alignment_rmsd, alignment_tm_score (vs. input reference structure)
          - recovery_rate (from design tool metadata, if available)
        """
        seq = candidate.sequence
        filepath = save_sequence(seq, prefix="tertiary_design")
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
            candidate.add_tool_record(
                ToolCallRecord(
                    step_name=f"{candidate.id}_gc_content",
                    tool_name="compute_rna_sequence_gc_content",
                    input_summary=json.dumps(gc_args, default=str)[:500],
                    output_summary=json.dumps(gc_res.output, default=str)[:500],
                    success=gc_res.success,
                    error=gc_res.error,
                    elapsed_time=getattr(gc_res, "elapsed_time", 0.0),
                    artifacts=dict(gc_res.output) if gc_res.success else {},
                    metrics={"gc_content": gc_res.output.get("gc_content")} if gc_res.success else {},
                )
            )
            if gc_res.success:
                gc_content = _pick_float(gc_res.output, "gc_content")
            else:
                _LOGGER.warning("gc_eval_failed error=%s", gc_res.error)
        metrics["gc_content"] = gc_content

        # ── Secondary structure (ViennaRNA) ──
        mfe: Optional[float] = None
        structure: Optional[str] = None
        if self.capabilities.has("predict_rna_secondary_structure"):
            fold_args = {"filepath": filepath}
            try:
                cap = self.capabilities.get("predict_rna_secondary_structure")
                fold_res = cap.invoke(fold_args, state=self._workflow_state)
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name=f"{candidate.id}_secondary_structure",
                        tool_name="predict_rna_secondary_structure",
                        input_summary=json.dumps(fold_args, default=str)[:500],
                        output_summary=json.dumps(fold_res.output, default=str)[:500],
                        success=fold_res.success,
                        error=fold_res.error,
                        elapsed_time=getattr(fold_res, "elapsed_time", 0.0),
                        artifacts=dict(fold_res.output) if fold_res.success else {},
                        metrics={"mfe_kcal_per_mol": fold_res.output.get("mfe_kcal_per_mol")} if fold_res.success else {},
                    )
                )
                if fold_res.success:
                    mfe = _pick_float(fold_res.output, "mfe_kcal_per_mol")
                    structure = fold_res.output.get("structure")
                else:
                    _LOGGER.warning("fold_eval_failed error=%s", fold_res.error)
            except Exception as exc:
                _LOGGER.warning("fold_eval_exception exc=%s", exc)
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name=f"{candidate.id}_secondary_structure",
                        tool_name="predict_rna_secondary_structure",
                        input_summary=json.dumps(fold_args, default=str)[:500],
                        output_summary="",
                        success=False,
                        error=str(exc),
                        elapsed_time=0.0,
                    )
                )
        metrics["vienna_mfe"] = mfe
        metrics["vienna_structure"] = structure

        # ── Tertiary structure (RhoFold) ──
        rhofold_plddt: Optional[float] = None
        rhofold_pdb: Optional[str] = None
        if self.capabilities.has("predict_rna_tertiary_structure_with_rhofold"):
            rh_args = {"filepath": filepath}
            try:
                cap = self.capabilities.get("predict_rna_tertiary_structure_with_rhofold")
                rh_res = cap.invoke(rh_args, state=self._workflow_state)
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name=f"{candidate.id}_tertiary_structure_rhofold",
                        tool_name="predict_rna_tertiary_structure_with_rhofold",
                        input_summary=json.dumps(rh_args, default=str)[:500],
                        output_summary=json.dumps(rh_res.output, default=str)[:500],
                        success=rh_res.success,
                        error=rh_res.error,
                        elapsed_time=getattr(rh_res, "elapsed_time", 0.0),
                        artifacts=dict(rh_res.output) if rh_res.success else {},
                        metrics={"mean_plddt": rh_res.output.get("mean_plddt")} if rh_res.success else {},
                    )
                )
                if rh_res.success:
                    rhofold_plddt = _pick_float(rh_res.output, "mean_plddt")
                    rhofold_pdb = rh_res.output.get("pdb_filepath", "")
                else:
                    _LOGGER.warning("rhofold_eval_failed error=%s", rh_res.error)
            except Exception as exc:
                _LOGGER.warning("rhofold_eval_exception exc=%s", exc)
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name=f"{candidate.id}_tertiary_structure_rhofold",
                        tool_name="predict_rna_tertiary_structure_with_rhofold",
                        input_summary=json.dumps(rh_args, default=str)[:500],
                        output_summary="",
                        success=False,
                        error=str(exc),
                        elapsed_time=0.0,
                    )
                )
        metrics["rhofold_mean_plddt"] = rhofold_plddt
        metrics["rhofold_pdb_path"] = rhofold_pdb
        candidate.metadata["rhofold_pdb_path"] = rhofold_pdb

        # ── Structure alignment vs. reference (RMSD + TM-score) ──
        alignment_rmsd: Optional[float] = None
        alignment_tm_score: Optional[float] = None
        ref_struct = candidate.metadata.get("input_structure_filepath")
        if (
            rhofold_pdb
            and ref_struct
            and self.capabilities.has("score_structure_alignment")
        ):
            align_args: dict[str, Any] = {
                "reference_pdb_filepath": ref_struct,
                "predicted_pdb_filepath": rhofold_pdb,
                "atom_type": "C1'",
            }
            try:
                cap = self.capabilities.get("score_structure_alignment")
                align_res = cap.invoke(align_args, state=self._workflow_state)
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name=f"{candidate.id}_structure_alignment",
                        tool_name="score_structure_alignment",
                        input_summary=json.dumps(align_args, default=str)[:500],
                        output_summary=json.dumps(align_res.output, default=str)[:500],
                        success=align_res.success,
                        error=align_res.error,
                        elapsed_time=getattr(align_res, "elapsed_time", 0.0),
                        artifacts=dict(align_res.output) if align_res.success else {},
                        metrics={
                            "rmsd": align_res.output.get("rmsd"),
                            "tm_score": align_res.output.get("tm_score"),
                        } if align_res.success else {},
                    )
                )
                if align_res.success:
                    alignment_rmsd = _pick_float(align_res.output, "rmsd")
                    alignment_tm_score = _pick_float(align_res.output, "tm_score")
                else:
                    _LOGGER.warning("alignment_eval_failed error=%s", align_res.error)
            except Exception as exc:
                _LOGGER.warning("alignment_eval_exception exc=%s", exc)
                candidate.add_tool_record(
                    ToolCallRecord(
                        step_name=f"{candidate.id}_structure_alignment",
                        tool_name="score_structure_alignment",
                        input_summary=json.dumps(align_args, default=str)[:500],
                        output_summary="",
                        success=False,
                        error=str(exc),
                        elapsed_time=0.0,
                    )
                )
        metrics["alignment_rmsd"] = alignment_rmsd
        metrics["alignment_tm_score"] = alignment_tm_score
        candidate.metadata["alignment_rmsd"] = alignment_rmsd
        candidate.metadata["alignment_tm_score"] = alignment_tm_score

        # ── Recovery rate (from design tool) ──
        recovery_rate: Optional[float] = None
        tool_meta = candidate.metadata.get("tool_metadata", {})
        if tool_meta:
            recovery_rate = _pick_float(tool_meta, "recovery_rate")
        metrics["recovery_rate"] = recovery_rate

        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Turn raw metrics into normalised score components.

        Only two components affect ranking (weights default to 0.5 each):
          - rhofold_component: pLDDT / 100
          - rmsd_component: max(0, 1 - rmsd / 5.0)   (smaller RMSD is better)

        Other metrics (GC, MFE, TM-score, recovery) are still collected in
        evaluate() for reference but do NOT enter total_score.
        """
        rhofold_plddt = metrics.get("rhofold_mean_plddt")
        rmsd = metrics.get("alignment_rmsd")

        scores: dict[str, float] = {}

        # RhoFold pLDDT in [0, 100] → [0, 1]
        if rhofold_plddt is not None:
            scores["rhofold_component"] = max(0.0, min(1.0, float(rhofold_plddt) / 100.0))
        else:
            scores["rhofold_component"] = 0.0

        # RMSD: smaller is better; normalise so that 0 Å → 1, 5 Å → 0
        if rmsd is not None:
            scores["rmsd_component"] = max(0.0, min(1.0, 1.0 - float(rmsd) / 5.0))
        else:
            scores["rmsd_component"] = 0.0

        # Retrieve weights from input stored in workflow state
        inp = self._workflow_state.get("_tertiary_design_input")
        if inp is not None:
            w_rho = float(getattr(inp, "weight_rhofold", 0.50))
            w_rmsd = float(getattr(inp, "weight_rmsd", 0.50))
        else:
            w_rho, w_rmsd = 0.50, 0.50

        total = w_rho * scores["rhofold_component"] + w_rmsd * scores["rmsd_component"]
        scores["total_score"] = total
        return scores

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        """Sort candidates by total score and build a ``WorkflowResult``."""
        if not candidates:
            return self._empty_result("No RNA sequence candidates produced from the tertiary structure.")

        ranked = sort_candidates_by_score(candidates, score_key="total_score", descending=True)
        best = ranked[0] if ranked else None

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
                f"RhoFold={mb.get('rhofold_mean_plddt'):.2f}"
                if mb.get("rhofold_mean_plddt") is not None
                else "RhoFold=N/A",
                f"TM={mb.get('alignment_tm_score'):.3f}"
                if mb.get("alignment_tm_score") is not None
                else "TM=N/A",
                f"RMSD={mb.get('alignment_rmsd'):.2f}"
                if mb.get("alignment_rmsd") is not None
                else "RMSD=N/A",
                f"recovery={mb.get('recovery_rate'):.3f}"
                if mb.get("recovery_rate") is not None
                else "recovery=N/A",
                f"total_score={scores.get('total_score', 0.0):.4f}",
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
            task_id=f"tertiary_design_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )


# Standalone scoring helper


def score_tertiary_structure_design_candidate(
    metrics: dict[str, Any],
    *,
    weight_rhofold: float = 0.50,
    weight_rmsd: float = 0.50,
) -> dict[str, float]:
    """Standalone scoring function for tertiary-structure-designed candidates.

    Only pLDDT and RMSD affect the total score. Other metrics are ignored for
    ranking but may still be present in *metrics* for reference.

    Reusable outside the workflow (e.g. in notebooks or downstream analysis).
    """
    rhofold_plddt = metrics.get("rhofold_mean_plddt")
    rmsd = metrics.get("alignment_rmsd")

    scores: dict[str, float] = {}

    if rhofold_plddt is not None:
        scores["rhofold_component"] = max(0.0, min(1.0, float(rhofold_plddt) / 100.0))
    else:
        scores["rhofold_component"] = 0.0

    if rmsd is not None:
        scores["rmsd_component"] = max(0.0, min(1.0, 1.0 - float(rmsd) / 5.0))
    else:
        scores["rmsd_component"] = 0.0

    total = weight_rhofold * scores["rhofold_component"] + weight_rmsd * scores["rmsd_component"]
    scores["total_score"] = total
    return scores


# LLM Critic Configuration

from agent_core.planning.llm_critic import BaseLLMCritic, CriticConfig

RNA_TERTIARY_STRUCTURE_CRITIC_CONFIG = CriticConfig(
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
        "CRITICAL: Default parameters for this workflow have been carefully tuned (n_samples_per_tool=3, rhodesign_temperature=1e-5, temperature_range=0.05, ribodiffusion_sampling_steps=50, scoring weights=0.5/0.5). These defaults work well for most RNA tertiary structure design tasks. Only recommend parameter overrides when you have strong evidence that the current settings are causing systematic problems. Do not tweak parameters lightly.",
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
            "hint": "Base sampling temperature for RhoDesign. Higher values increase diversity but may reduce quality. Default (1e-5) is well-tuned for structure fidelity; only adjust when there is strong evidence that the current temperature is causing systematic issues.",
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
            "hint": "Weight for RhoFold pLDDT in composite scoring. Default (0.5) balances foldability and structural fidelity; only adjust when the user explicitly prioritizes one over the other.",
        },
        "weight_rmsd": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Weight for RMSD in composite scoring. Default (0.5) balances foldability and structural fidelity; only adjust when the user explicitly prioritizes one over the other.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
)


class RnaTertiaryStructureDesignLLMCritic(BaseLLMCritic):
    """LLM-driven Critic for RNA tertiary structure design workflow.

    Focuses on whether candidate sequences satisfy constraints from the user's
    original prompt rather than applying hard-coded thresholds.
    """

    def _default_config(self) -> CriticConfig:
        return RNA_TERTIARY_STRUCTURE_CRITIC_CONFIG

    def _build_context(self, result: WorkflowResult, state: dict[str, Any]) -> dict[str, Any]:
        """Extend base context with tertiary structure design specific statistics."""
        ctx = super()._build_context(result, state)

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

        # Tool distribution
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

            # Design tool source
            tool = meta.get("design_tool", "unknown")
            tool_dist[tool] = tool_dist.get(tool, 0) + 1

            # Metrics
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
