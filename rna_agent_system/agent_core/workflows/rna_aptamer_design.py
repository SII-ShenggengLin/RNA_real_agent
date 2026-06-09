"""RNA aptamer design workflow — structure-driven generation against protein targets (Layer 2).

Protein (sequence or 3D structure) → hotspot identification →
ODesign aptamer generation → fold + GC + RhoFold (+ EGARPS) evaluation →
scoring → ranking → WorkflowResult.

Key design principles
---------------------
1. **Structure-first**: ODesign is the only tool in the project that supports
   3D-structure-guided RNA design against a protein target.
2. **Binding-centric scoring**: Unlike mRNA workflows that optimise CAI/MFE,
   aptamer workflows optimise binding affinity (EGARPS native_probability)
   and foldability (RhoFold pLDDT, ViennaRNA MFE).
3. **Graceful degradation**: EGARPS requires a complex PDB; if it is unavailable
   or the file format does not match, the workflow continues with the remaining
   metrics rather than failing entirely.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  RnaAptamerDesignWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 rna_aptamer_design workflow 的权威实现。任何字段增删、            ║
║  函数签名变动、返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：║
║                                                                               ║
║    - agent_core/workflows/rna_aptamer_design.py  ← 本文件                   ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/workflows/registry.py                                         ║
║    - agent_core/workflows/__init__.py                                         ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/capabilities/writebacks.py                                    ║
║    - agent_core/planning/llm_critic.py                                        ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - tests/test_rna_aptamer_design.py                                         ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
import re
import time

import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_core.capabilities.base import CapabilityRegistry, CapabilityResult
from agent_core.llm_config import get_llm_for_provider
from agent_core.file_manager import (
    read_sequence,
    resolve_project_path,
    save_sequence,
    save_text_file,
)
from agent_core.sequence_utils import _pick_float
from agent_core.workflow_models import Candidate, WorkflowResult, ToolCallRecord, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.coordinator import (
    AptamerCoordinationRound,
    AptamerCoordinator,
    Issue,
    ModuleFeedback,
)

_LOGGER = logging.getLogger("agent_core.workflows.rna_aptamer_design")

# Input model


class RnaAptamerDesignInput(BaseModel):
    """Input for the RNA aptamer design workflow."""

    model_config = ConfigDict(extra="forbid")

    protein_sequence: Optional[str] = Field(
        default=None,
        description="Amino-acid string (uppercase, 1-letter codes). "
                    "Either this or protein_structure_path must be provided.",
    )
    protein_structure_path: Optional[str] = Field(
        default=None,
        description="Path to protein PDB or CIF file. "
                    "Either this or protein_sequence must be provided.",
    )
    chain_id: str = Field(default="A", description="Protein chain ID to target.")
    aptamer_length: int = Field(
        default=30, ge=10, le=200, description="Desired aptamer length in nucleotides."
    )
    hotspot_residues: Optional[str] = Field(
        default=None,
        description="Explicit hotspot residues, e.g. 'A/18,A/90'. "
                    "If omitted, automatic identification is performed.",
    )
    n_odesign_samples: int = Field(
        default=5, ge=1, le=20, description="Number of ODesign samples to generate."
    )
    odesign_seeds: list[int] = Field(
        default_factory=lambda: [42],
        description="Random seeds for ODesign inference.",
    )
    # Scoring weights (can be overridden for domain-specific tuning)
    weight_egarps: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for EGARPS native probability.")
    weight_rhofold: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for RhoFold pLDDT.")
    bmc_mode: Literal["full", "1round", "no_target", "no_bounds", "llm_coord"] = Field(
        default="full",
        description=(
            "BMC ablation mode. 'full'=normal BMC, '1round'=Phase 1+2 only, "
            "'no_target'=disable hotspot adjustment, 'no_bounds'=remove hard round limit, "
            "'llm_coord'=use LLM-based coordinator instead of deterministic rules."
        ),
    )

    @model_validator(mode="after")
    def _check_weight_sum(self) -> "RnaAptamerDesignInput":
        total = self.weight_egarps + self.weight_rhofold
        if total > 1.0:
            raise ValueError(
                f"weight_egarps + weight_rhofold must be <= 1.0, got {total:.2f}"
            )
        return self

    @field_validator("protein_sequence")
    @classmethod
    def _validate_protein_sequence(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        seq = v.strip().upper()
        invalid = set(ch for ch in seq if ch not in "ACDEFGHIKLMNPQRSTVWY")
        if invalid:
            raise ValueError(
                f"Invalid amino-acid characters: {''.join(sorted(invalid))}. "
                "Only standard 1-letter codes are allowed."
            )
        return seq

    @field_validator("hotspot_residues")
    @classmethod
    def _validate_hotspot_residues(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        pattern = re.compile(r"^([A-Za-z]/\d+|\d+)(,([A-Za-z]/\d+|\d+))*$")
        if not pattern.match(v.strip()):
            raise ValueError(
                "Hotspot residues must be formatted as 'chain/num,chain/num' or 'num,num', "
                "e.g. 'A/18,A/90' or '18,90'."
            )
        return v.strip()


# Workflow implementation


class RnaAptamerDesignWorkflow(BaseDomainWorkflow[RnaAptamerDesignInput, WorkflowResult]):
    """Structure-driven RNA aptamer design: protein target → ODesign → evaluate → rank."""

    name = "rna_aptamer_design"
    description = (
        "Design RNA aptamers against a protein target using 3D-structure-guided generation. "
        "Pipeline: hotspot identification → ODesign generation → fold + RhoFold + EGARPS evaluation → scoring → ranking."
    )
    required_capabilities = [
        "identify_protein_binding_hotspots",
        "build_odesign_aptamer_input_json",
        "run_odesign_inference",
        "compute_rna_sequence_gc_content",
        "predict_rna_tertiary_structure_with_rhofold",
        "score_rna_protein_complex_with_egarps",
        "extract_rna_sequence_from_cif",
        "predict_rna_protein_complex_with_proteinx",
        "analyze_rna_protein_interface",
    ]

    # Mapping of capability → (host, port, health_path, start_script_relative_path)
    _REQUIRED_SERVICES: dict[str, tuple[str, int, str, str]] = {
        "predict_rna_tertiary_structure_with_rhofold": ("127.0.0.1", 8006, "/health", "microservices/rhodesign_service/start.sh"),
        "run_odesign_inference": ("127.0.0.1", 8012, "/health", "microservices/odesign_service/start.sh"),
        "predict_rna_protein_complex_with_proteinx": ("127.0.0.1", 8022, "/health", "microservices/proteinx_service/start.sh"),
        "score_rna_protein_complex_with_egarps": ("127.0.0.1", 8023, "/score", "microservices/egarps_service/start.sh"),
    }

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._bmc_trace: list[Any] = []
        self._workflow_trace: list[ToolCallRecord] = []

    def _ensure_services_running(self) -> None:
        """Check required microservices and auto-start any that are down."""
        import subprocess
        import socket
        import time
        import urllib.request

        project_root = Path(__file__).resolve().parents[2]

        for cap_name, (host, port, path, start_script) in self._REQUIRED_SERVICES.items():
            if not self.capabilities.has(cap_name):
                continue  # capability not registered, skip

            # Check if service is reachable
            reachable = False
            try:
                with socket.create_connection((host, port), timeout=2):
                    # For EGARPS, a TCP connection is enough; for others try HTTP health
                    if path == "/score":
                        reachable = True
                    else:
                        req = urllib.request.Request(f"http://{host}:{port}{path}", method="GET")
                        with urllib.request.urlopen(req, timeout=3) as resp:
                            reachable = resp.status < 500
            except Exception:
                reachable = False

            if reachable:
                _LOGGER.debug("service_ready cap=%s host=%s port=%d", cap_name, host, port)
                continue

            _LOGGER.warning("service_down_auto_starting cap=%s host=%s port=%d script=%s", cap_name, host, port, start_script)
            script_path = project_root / start_script
            if not script_path.exists():
                raise RuntimeError(
                    f"Required microservice '{cap_name}' is not running on {host}:{port} "
                    f"and start script not found: {script_path}"
                )

            # Start the service in background
            log_file = f"/tmp/{cap_name.replace('/', '_')}_autostart.log"
            cmd = f"cd {project_root} && nohup bash {script_path} > {log_file} 2>&1 &"
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Wait for service to come up (max 60s)
            for attempt in range(60):
                time.sleep(1)
                try:
                    with socket.create_connection((host, port), timeout=2):
                        if path == "/score":
                            _LOGGER.info("service_started cap=%s host=%s port=%d", cap_name, host, port)
                            break
                        req = urllib.request.Request(f"http://{host}:{port}{path}", method="GET")
                        with urllib.request.urlopen(req, timeout=3) as resp:
                            if resp.status < 500:
                                _LOGGER.info("service_started cap=%s host=%s port=%d", cap_name, host, port)
                                break
                except Exception:
                    pass
            else:
                raise RuntimeError(
                    f"Required microservice '{cap_name}' failed to start on {host}:{port} "
                    f"within 60 seconds. Check log: {log_file}"
                )

    # ─────────────────────────────────────────────────────────────────────────
    # Structured tracing helper
    # ─────────────────────────────────────────────────────────────────────────

    def _invoke_and_record(
        self,
        cap_name: str,
        args: dict[str, Any],
        *,
        candidate: Optional[Candidate] = None,
        step_name: Optional[str] = None,
        required: bool = False,
    ) -> CapabilityResult:
        """Invoke a capability and create a structured ToolCallRecord.

        Records are attached to *candidate* when provided, otherwise to the
        workflow-level ``_workflow_trace``.  Missing capabilities are logged
        and return a failed CapabilityResult unless *required* is True.
        """
        if not self.capabilities.has(cap_name):
            msg = f"Capability '{cap_name}' not registered"
            if required:
                raise KeyError(msg)
            _LOGGER.warning("capability_missing %s", cap_name)
            return CapabilityResult(success=False, tool_name=cap_name, error=msg)

        cap = self.capabilities.get(cap_name)
        start = time.perf_counter()
        cap_result = cap.invoke(args, state=self._workflow_state)
        elapsed = time.perf_counter() - start

        record = ToolCallRecord(
            step_name=step_name or cap_name,
            tool_name=cap_name,
            input_summary=str(args)[:500],
            output_summary=str(cap_result.output)[:500] if cap_result.success else "",
            success=cap_result.success,
            error=cap_result.error,
            elapsed_time=elapsed,
            artifacts=dict(cap_result.output) if cap_result.success else {},
            metrics={"elapsed_time": elapsed},
        )

        if candidate is not None:
            candidate.add_tool_record(record)
        else:
            self._workflow_trace.append(record)

        return cap_result

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, inp: Any, *, progress_callback=None) -> WorkflowResult:
        """BMC-enabled run: generate → evaluate → rank → bounded iterative refinement.

        Phase 1: Target preparation + Aptamer generation (Module 1 + Module 2).
        Phase 2: Evaluate and score (Complex evaluation).
        Phase 3: AptamerCoordinator diagnoses best candidate; if issues found,
        broadcast structured feedback to affected modules, regenerate, and
        re-evaluate. Hard bounds: max 3 rounds, no improvement → early stop.
        """
        if isinstance(inp, dict):
            inp = RnaAptamerDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._workflow_state["_aptamer_input"] = inp
        self._bmc_trace: list[AptamerCoordinationRound] = []

        # ── Pre-flight: ensure all required microservices are running ──
        self._ensure_services_running()

        # ── Phase 1: Module preparation and initial generation ──
        protein_path, hotspot, protein_seq_len = self._prepare_target_module(inp)
        if not protein_path or not hotspot:
            merged_wb = dict(self._workflow_state)
            merged_wb["_workflow_params"] = inp.model_dump()
            return WorkflowResult(
                success=False,
                task_id="",
                summary="Aptamer design failed during target preparation.",
                errors=["target_preparation_failed"],
                _state_writeback=merged_wb,  # type: ignore[attr-defined]
            )

        candidates = self._generate_aptamer_module(
            protein_path, hotspot, inp, protein_seq_len=protein_seq_len
        )
        if not candidates:
            merged_wb = dict(self._workflow_state)
            merged_wb["_workflow_params"] = inp.model_dump()
            return WorkflowResult(
                success=False,
                task_id="",
                summary="Aptamer design failed during candidate generation.",
                errors=["candidate_generation_failed"],
                _state_writeback=merged_wb,  # type: ignore[attr-defined]
            )

        # ── Phase 2: Evaluate and score all candidates ──
        for i, candidate in enumerate(candidates):
            _LOGGER.info(
                "workflow_evaluating_candidate idx=%d total=%d workflow=%s",
                i + 1,
                len(candidates),
                self.name,
            )
            metrics = self.evaluate(candidate)
            candidate.scores = self.score(metrics)
            candidate.status = "evaluated"
            if progress_callback:
                progress_callback({
                    "event": "evaluate_progress",
                    "current": i + 1,
                    "total": len(candidates),
                    "candidate_id": candidate.id,
                    "workflow": self.name,
                })

        result = self.rank_and_format(candidates)

        if not result.success or not result.all_candidates:
            merged_wb = dict(self._workflow_state)
            merged_wb["_workflow_params"] = inp.model_dump()
            result._state_writeback = merged_wb  # type: ignore[attr-defined]
            return result

        # ── Phase 3: Bounded Multi-Module Coordination ──
        self._workflow_state["_bmc_mode"] = inp.bmc_mode

        if inp.bmc_mode == "llm_coord":
            coordinator: AptamerCoordinator = LLMAptamerCoordinator()
        else:
            coordinator = AptamerCoordinator()

        if inp.bmc_mode == "no_bounds":
            max_rounds = 100
            improvement_threshold = 0.0
        else:
            max_rounds = 3
            improvement_threshold = 0.01

        self._workflow_state["_bmc_max_rounds"] = max_rounds
        self._workflow_state["_bmc_improvement_threshold"] = improvement_threshold

        best = result.best_candidate
        best_score = (
            best.scores.get("total_score", float("-inf")) if best else float("-inf")
        )

        if inp.bmc_mode == "1round":
            _LOGGER.info("bmc_1round_mode_skipping_phase3")
        else:
            for round_num in range(1, max_rounds + 1):
                if best is None:
                    break

                metrics = best.metadata.get("metrics_bundle", {})
                issues = coordinator.diagnose(metrics)

                if not issues:
                    _LOGGER.info("bmc_converged_no_issues round=%d", round_num)
                    break

                feedback = coordinator.broadcast_feedback(issues)
                affected_modules = list(feedback.keys())

                _LOGGER.info(
                    "bmc_round_start round=%d issues=%d modules=%s",
                    round_num,
                    len(issues),
                    affected_modules,
                )

                # Generate new candidates with adjusted parameters
                t0 = time.perf_counter()
                new_candidates = self._regenerate_modules(
                    inp, feedback, protein_path, hotspot, protein_seq_len, best
                )

                if not new_candidates:
                    _LOGGER.info("bmc_no_new_candidates round=%d", round_num)
                    break

                # Evaluate new candidates
                for i, candidate in enumerate(new_candidates):
                    _LOGGER.info(
                        "bmc_evaluating_new idx=%d total=%d round=%d",
                        i + 1,
                        len(new_candidates),
                        round_num,
                    )
                    metrics = self.evaluate(candidate)
                    candidate.scores = self.score(metrics)
                    candidate.status = "evaluated"
                    if progress_callback:
                        progress_callback({
                            "event": "bmc_evaluate_progress",
                            "round": round_num,
                            "current": i + 1,
                            "total": len(new_candidates),
                            "candidate_id": candidate.id,
                            "workflow": self.name,
                        })

                # Merge and re-rank
                all_candidates = result.all_candidates + new_candidates
                result = self.rank_and_format(all_candidates)

                new_best = result.best_candidate
                new_score = (
                    new_best.scores.get("total_score", float("-inf"))
                    if new_best
                    else float("-inf")
                )

                # Record round trace
                time_elapsed_ms = (time.perf_counter() - t0) * 1000.0
                round_trace = AptamerCoordinationRound(
                    round_num=round_num,
                    best_candidate_id=new_best.id if new_best else "",
                    best_total_score=new_score,
                    issues_found=issues,
                    feedback_dispatched=feedback,
                    modules_reinvoked=affected_modules,
                    time_elapsed_ms=time_elapsed_ms,
                )
                self._bmc_trace.append(round_trace)

                should_stop, reason = coordinator.has_converged(
                    new_score,
                    best_score,
                    round_num,
                    max_rounds=max_rounds,
                    improvement_threshold=improvement_threshold,
                )

                _LOGGER.info(
                    "bmc_round_complete round=%d old_score=%.3f new_score=%.3f reason=%s",
                    round_num,
                    best_score,
                    new_score,
                    reason,
                )

                if should_stop:
                    break

                best = new_best
                best_score = new_score

        # Aggregate per-candidate and workflow-level tool records into result.trace
        for c in result.all_candidates:
            result.trace.extend(c.tool_records)
        result.trace.extend(self._workflow_trace)

        # Attach BMC trace and state writeback
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        merged_wb["_bmc_trace"] = [r.to_dict() for r in self._bmc_trace]
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # BMC Module-level helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _prepare_target_module(
        self, inp: RnaAptamerDesignInput
    ) -> tuple[Optional[str], Optional[str], Optional[int]]:
        """Module 1: Resolve protein structure and identify binding hotspots.

        Returns:
            (protein_path, hotspot_residues, protein_seq_len) or (None, None, None) on failure.
        """
        # ── 1. Resolve protein structure ──
        protein_path = self._resolve_protein_structure(inp)
        if not protein_path:
            _LOGGER.error("No valid protein structure available")
            return None, None, None

        protein_seq_len = self._resolve_protein_length(
            protein_path, inp.protein_sequence, chain_id=inp.chain_id
        )
        if protein_seq_len is None or protein_seq_len <= 0:
            _LOGGER.error("Cannot determine protein sequence length")
            return None, None, None

        # ── 2. Hotspot identification ──
        hotspot = inp.hotspot_residues
        # Normalize numeric-only hotspots to chain/num format expected by ODesign
        if hotspot and "/" not in hotspot:
            hotspot = ",".join(
                f"{inp.chain_id}/{part.strip()}" for part in hotspot.split(",")
            )
            _LOGGER.info("hotspot_normalized format=%s", hotspot)
        expand_hotspot = self._workflow_state.get("_aptamer_expand_hotspot", False)
        if not hotspot:
            _LOGGER.info("hotspot_not_provided running_auto_identification")
            hotspot = self._auto_identify_hotspots(protein_path, inp.chain_id)
            if not hotspot:
                _LOGGER.error("hotspot_identification_failed")
                return None, None, None
            _LOGGER.info("hotspot_auto_identified residues=%s", hotspot)

        # Expand hotspot region if requested by legacy critic retry
        if expand_hotspot and hotspot:
            expanded = self._expand_hotspot_residues(
                protein_path, inp.chain_id, hotspot, window=3
            )
            if expanded and expanded != hotspot:
                _LOGGER.info("hotspot_expanded old=%s new=%s", hotspot, expanded)
                hotspot = expanded

        return protein_path, hotspot, protein_seq_len

    def _generate_aptamer_module(
        self,
        protein_path: str,
        hotspot: str,
        inp: RnaAptamerDesignInput,
        *,
        protein_seq_len: Optional[int] = None,
        length_override: Optional[int] = None,
        seeds_override: Optional[list[int]] = None,
        samples_override: Optional[int] = None,
    ) -> list[Candidate]:
        """Module 2: Generate aptamer candidates via ODesign structure-guided generation.

        Supports parameter overrides for BMC regeneration.
        """
        # Resolve protein length if not provided
        if protein_seq_len is None:
            protein_seq_len = self._resolve_protein_length(
                protein_path, inp.protein_sequence, chain_id=inp.chain_id
            )
        if protein_seq_len is None or protein_seq_len <= 0:
            _LOGGER.error("Cannot determine protein sequence length")
            return []

        # Apply parameter overrides
        aptamer_length = length_override if length_override is not None else inp.aptamer_length
        # Legacy retry adjustment (backward compatibility)
        if self._workflow_state.get("_aptamer_retry_adjust_length", False):
            aptamer_length = min(200, aptamer_length + 5)
            _LOGGER.info("aptamer_length_adjusted old=%d new=%d", inp.aptamer_length, aptamer_length)

        seeds = seeds_override if seeds_override is not None else inp.odesign_seeds
        n_sample = samples_override if samples_override is not None else inp.n_odesign_samples

        # ── Build ODesign input JSON ──
        json_result = self._build_odesign_json(
            protein_path=protein_path,
            chain_id=inp.chain_id,
            seq_len=protein_seq_len,
            hotspot=hotspot,
            aptamer_length=aptamer_length,
        )
        if not json_result:
            _LOGGER.error("odesign_json_build_failed")
            return []
        json_path = json_result.get("input_json_filepath", "")
        _LOGGER.info("odesign_json_built path=%s", json_path)

        # ── Run ODesign inference ──
        odesign_result = self._run_odesign_inference(
            json_path=json_path,
            n_sample=n_sample,
            seeds=seeds,
        )
        if not odesign_result:
            _LOGGER.error("odesign_inference_failed")
            return []

        prediction_paths = odesign_result.get("prediction_filepaths", [])
        _LOGGER.info("odesign_predictions count=%d", len(prediction_paths))

        # ── Extract RNA sequences from prediction files ──
        sequences = self._extract_sequences_from_predictions(prediction_paths)
        if not sequences:
            _LOGGER.error("no_sequences_extracted_from_odesign_output")
            return []

        candidates: list[Candidate] = []
        seen: set[str] = set()
        for idx, seq in enumerate(sequences):
            if not seq or seq in seen:
                continue
            seen.add(seq)
            candidates.append(
                Candidate(
                    sequence=seq,
                    sequence_type="rna_aptamer",
                    source=f"odesign_aptamer:s{seeds[0]}:i{idx}",
                    metadata={
                        "protein_structure_path": protein_path,
                        "protein_chain_id": inp.chain_id,
                        "hotspot_residues": hotspot,
                        "aptamer_length": aptamer_length,
                        "odesign_prediction_path": prediction_paths[idx] if idx < len(prediction_paths) else None,
                        "odesign_input_json": json_path,
                        "design_params": {
                            "n_sample": n_sample,
                            "seeds": seeds,
                        },
                    },
                )
            )

        _LOGGER.info("candidates_generated total=%d unique=%d", len(sequences), len(candidates))
        return candidates

    def generate_candidates(self, inp: RnaAptamerDesignInput) -> list[Candidate]:
        """Generate aptamer candidates via ODesign structure-guided generation.

        Public API kept unchanged; delegates to BMC module helpers.
        """
        protein_path, hotspot, protein_seq_len = self._prepare_target_module(inp)
        if not protein_path or not hotspot:
            return []
        return self._generate_aptamer_module(
            protein_path, hotspot, inp, protein_seq_len=protein_seq_len
        )

    def _regenerate_modules(
        self,
        inp: RnaAptamerDesignInput,
        feedback: dict[str, ModuleFeedback],
        protein_path: str,
        hotspot: str,
        protein_seq_len: Optional[int],
        best: Candidate,
    ) -> list[Candidate]:
        """Regenerate candidates based on AptamerCoordinator feedback.

        Maps feedback adjustments to concrete parameter changes and invokes
        the appropriate module regeneration methods.
        """
        new_candidates: list[Candidate] = []
        bmc_mode = self._workflow_state.get("_bmc_mode", "full")

        # ── Target module regeneration (hotspot expansion) ──
        if "Target" in feedback and bmc_mode != "no_target":
            target_fb = feedback["Target"]
            current_window = 3
            for adj in target_fb.adjustments:
                if adj.param == "hotspot_expansion":
                    current_window += int(adj.delta)
            current_window = max(3, min(current_window, 10))  # clamp [3, 10]

            expanded_hotspot = self._expand_hotspot_residues(
                protein_path, inp.chain_id, hotspot, window=current_window
            )
            if expanded_hotspot and expanded_hotspot != hotspot:
                _LOGGER.info(
                    "bmc_regenerating_target expanded_window=%d old=%s new=%s",
                    current_window,
                    hotspot,
                    expanded_hotspot,
                )
                new_candidates = self._generate_aptamer_module(
                    protein_path,
                    expanded_hotspot,
                    inp,
                    protein_seq_len=protein_seq_len,
                )
                # Tag new candidates with regeneration info
                for c in new_candidates:
                    c.metadata["bmc_round"] = len(self._bmc_trace) + 1
                    c.metadata["bmc_module"] = "Target"
                    c.metadata["hotspot_before"] = hotspot
                    c.metadata["hotspot_after"] = expanded_hotspot
            else:
                _LOGGER.info("bmc_hotspot_expansion_no_change fallback_to_aptamer")

        # ── Aptamer module regeneration (length / seeds / samples) ──
        if "Aptamer" in feedback and not new_candidates:
            aptamer_fb = feedback["Aptamer"]
            length_override = None
            seeds_override = None
            samples_override = None

            for adj in aptamer_fb.adjustments:
                if adj.param == "aptamer_length_delta":
                    length_override = min(200, inp.aptamer_length + int(adj.delta))
                elif adj.param == "seed_change":
                    # Shift all seeds by +1 to explore new sequence space
                    seeds_override = [s + 1 for s in inp.odesign_seeds]
                elif adj.param == "n_samples_delta":
                    samples_override = min(20, inp.n_odesign_samples + int(adj.delta))

            _LOGGER.info(
                "bmc_regenerating_aptamer length=%s seeds=%s samples=%s",
                length_override,
                seeds_override,
                samples_override,
            )
            new_candidates = self._generate_aptamer_module(
                protein_path,
                hotspot,
                inp,
                protein_seq_len=protein_seq_len,
                length_override=length_override,
                seeds_override=seeds_override,
                samples_override=samples_override,
            )
            for c in new_candidates:
                c.metadata["bmc_round"] = len(self._bmc_trace) + 1
                c.metadata["bmc_module"] = "Aptamer"
                c.metadata["length_override"] = length_override
                c.metadata["seeds_override"] = seeds_override
                c.metadata["samples_override"] = samples_override

        return new_candidates

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Evaluate an aptamer candidate.

        Metrics collected:
          - gc_content (for critic quality gating)
          - rhofold_mean_plddt (RNA monomer foldability)
          - egarps_native_probability (ODesign complex quality)
          - proteinx_ipTM (AlphaFold-family complex confidence)
          - interface_contacts, buried_sasa, hydrogen_bonds, salt_bridges
        """
        seq = candidate.sequence
        filepath = save_sequence(seq, prefix="aptamer")
        candidate.metadata["workspace_filepath"] = filepath

        metrics: dict[str, Any] = {
            "sequence_length": len(seq),
        }

        # ── GC content (retained for critic quality gating) ──
        gc_content = self._run_capability_float(
            "compute_rna_sequence_gc_content",
            {"filepath": filepath},
            "gc_content",
            candidate=candidate,
            step_name="compute_rna_sequence_gc_content",
        )
        metrics["gc_content"] = gc_content

        # ── RhoFold tertiary structure ──
        rhofold_plddt: Optional[float] = None
        rhofold_pdb: Optional[str] = None
        if self.capabilities.has("predict_rna_tertiary_structure_with_rhofold"):
            rh_res = self._invoke_and_record(
                "predict_rna_tertiary_structure_with_rhofold",
                {"filepath": filepath},
                candidate=candidate,
                step_name="predict_rna_tertiary_structure_with_rhofold",
            )
            if rh_res.success:
                rhofold_plddt = _pick_float(rh_res.output, "mean_plddt")
                rhofold_pdb = rh_res.output.get("pdb_filepath", "")
            else:
                _LOGGER.warning("aptamer_rhofold_failed error=%s", rh_res.error)
        metrics["rhofold_mean_plddt"] = rhofold_plddt
        metrics["rhofold_pdb_path"] = rhofold_pdb
        candidate.metadata["rhofold_pdb_path"] = rhofold_pdb

        # ── EGARPS complex scoring (best-effort) ──
        egarps_prob: Optional[float] = None
        odesign_pred_path = candidate.metadata.get("odesign_prediction_path")
        if odesign_pred_path and self.capabilities.has("score_rna_protein_complex_with_egarps"):
            pred_path_obj = Path(odesign_pred_path)
            suffix = pred_path_obj.suffix.lower()
            if suffix == ".pdb":
                egarps_prob = self._run_egarps(str(pred_path_obj.resolve()), candidate=candidate)
            elif suffix in {".cif", ".mmcif"}:
                egarps_prob = self._try_egarps_from_cif(str(pred_path_obj.resolve()), candidate=candidate)
            else:
                _LOGGER.debug("egarps_skipped_unknown_suffix suffix=%s", suffix)
        else:
            _LOGGER.debug("egarps_skipped_no_odesign_structure")
        metrics["egarps_native_probability"] = egarps_prob

        # ── ProteinX RNA-protein complex prediction (required) ──
        iptm: Optional[float] = None
        proteinx_plddt: Optional[float] = None
        proteinx_pdb: Optional[str] = None
        protein_seq = self._resolve_protein_sequence_for_candidate(candidate)
        if protein_seq and self.capabilities.has("predict_rna_protein_complex_with_proteinx"):
            # Save protein and RNA sequences as FASTA files
            protein_fasta = save_sequence(f">protein\n{protein_seq}\n", prefix="protein_for_complex")
            rna_fasta = save_sequence(f">rna\n{seq}\n", prefix="rna_for_complex")
            px_res = self._invoke_and_record(
                "predict_rna_protein_complex_with_proteinx",
                {
                    "protein_filepath": protein_fasta,
                    "rna_filepath": rna_fasta,
                    "num_models": 1,
                },
                candidate=candidate,
                step_name="predict_rna_protein_complex_with_proteinx",
            )
            if px_res.success:
                iptm = _pick_float(px_res.output, "ipTM")
                proteinx_plddt = _pick_float(px_res.output, "mean_plddt")
                proteinx_pdb = px_res.output.get("pdb_filepath", "")
            else:
                raise RuntimeError(
                    f"ProteinX complex prediction failed: {px_res.error}"
                )
        metrics["proteinx_ipTM"] = iptm
        metrics["proteinx_mean_plddt"] = proteinx_plddt
        metrics["proteinx_pdb_path"] = proteinx_pdb

        # ── Interface analysis on ODesign complex structure (best-effort) ──
        interface_contacts: Optional[int] = None
        buried_sasa: Optional[float] = None
        hydrogen_bonds: Optional[int] = None
        salt_bridges: Optional[int] = None
        if odesign_pred_path and self.capabilities.has("analyze_rna_protein_interface"):
            try:
                # Try to determine chain IDs from the structure; fallback to defaults
                protein_chain = candidate.metadata.get("protein_chain_id", "A")
                rna_chain = "B"  # ODesign typically outputs RNA as chain B

                # ODesign outputs CIF files that lack _atom_site.B_iso_or_equiv,
                # which Bio.PDB.MMCIFParser requires. Convert to PDB on-the-fly.
                iface_input_path = self._ensure_pdb_for_interface_analysis(
                    odesign_pred_path
                )
                if not iface_input_path:
                    _LOGGER.debug("interface_analysis_skipped_cif_conversion_failed")
                else:
                    # ODesign renames chains to A (protein) and B (RNA) regardless
                    # of the original PDB chain IDs. Detect actual chains in the
                    # converted structure to avoid "0 atoms" failures.
                    detected_protein_chain, detected_rna_chain = (
                        self._detect_chains_in_pdb(iface_input_path, protein_chain, rna_chain)
                    )
                    iface_res = self._invoke_and_record(
                        "analyze_rna_protein_interface",
                        {
                            "complex_pdb_filepath": iface_input_path,
                            "protein_chain_id": detected_protein_chain,
                            "rna_chain_id": detected_rna_chain,
                            "contact_cutoff": 5.0,
                        },
                        candidate=candidate,
                        step_name="analyze_rna_protein_interface",
                    )
                    if iface_res.success:
                        interface_contacts = iface_res.output.get("interface_contacts")
                        buried_sasa = _pick_float(iface_res.output, "buried_sasa")
                        hydrogen_bonds = iface_res.output.get("hydrogen_bonds")
                        salt_bridges = iface_res.output.get("salt_bridges")
                    else:
                        _LOGGER.warning("interface_analysis_failed error=%s", iface_res.error)
            except Exception as exc:
                _LOGGER.warning("interface_analysis_exception exc=%s", exc)
        metrics["interface_contacts"] = interface_contacts
        metrics["buried_sasa"] = buried_sasa
        metrics["hydrogen_bonds"] = hydrogen_bonds
        metrics["salt_bridges"] = salt_bridges

        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Combine raw metrics into a single aptamer quality score."""
        inp = self._workflow_state.get("_aptamer_input")
        if inp is not None:
            return score_aptamer_candidate(
                metrics,
                weight_egarps=inp.weight_egarps,
                weight_rhofold=inp.weight_rhofold,
            )
        return score_aptamer_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return self._empty_result("No aptamer candidates produced.")

        ranked = sort_candidates_by_score(
            candidates, score_key="total_score", descending=True
        )
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
                f"RhoFold={mb.get('rhofold_mean_plddt'):.2f}"
                if mb.get("rhofold_mean_plddt") is not None
                else "RhoFold=N/A",
                f"EGARPS={mb.get('egarps_native_probability'):.4f}"
                if mb.get("egarps_native_probability") is not None
                else "EGARPS=N/A",
                f"ipTM={mb.get('proteinx_ipTM'):.4f}"
                if mb.get("proteinx_ipTM") is not None
                else "ipTM=N/A",
                f"contacts={mb.get('interface_contacts')}"
                if mb.get("interface_contacts") is not None
                else "contacts=N/A",
                f"bSASA={mb.get('buried_sasa'):.1f}"
                if mb.get("buried_sasa") is not None
                else "bSASA=N/A",
                f"HB={mb.get('hydrogen_bonds')}"
                if mb.get("hydrogen_bonds") is not None
                else "HB=N/A",
                f"SB={mb.get('salt_bridges')}"
                if mb.get("salt_bridges") is not None
                else "SB=N/A",
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
            task_id=f"aptamer_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_protein_structure(self, inp: RnaAptamerDesignInput) -> Optional[str]:
        """Return a valid protein structure path, or None."""
        if inp.protein_structure_path:
            path = resolve_project_path(inp.protein_structure_path)
            if Path(path).exists():
                return path
            _LOGGER.warning("protein_structure_path_not_found path=%s", path)
        # If only sequence is provided, predict structure with ProteinX
        if inp.protein_sequence and not inp.protein_structure_path:
            _LOGGER.info("protein_sequence_only predicting_structure_with_proteinx")
            if not self.capabilities.has("predict_protein_structure_with_proteinx"):
                _LOGGER.warning("capability_missing predict_protein_structure_with_proteinx")
                return None
            # Save sequence as FASTA
            fasta_content = f">protein\n{inp.protein_sequence}\n"
            fasta_path = save_sequence(fasta_content, prefix="protein")
            abs_fasta = resolve_project_path(fasta_path)
            try:
                cap_result = self._invoke_and_record(
                    "predict_protein_structure_with_proteinx",
                    {
                        "filepath": abs_fasta,
                        "num_models": 1,
                        "msa_mode": "none",
                    },
                    step_name="predict_protein_structure_with_proteinx",
                )
                pdb_path = cap_result.output.get("pdb_filepath", "") if cap_result.success else ""
                if pdb_path and Path(pdb_path).exists():
                    _LOGGER.info("protein_structure_predicted path=%s", pdb_path)
                    return pdb_path
                _LOGGER.error("proteinx_returned_invalid_path path=%s", pdb_path)
            except Exception as exc:
                _LOGGER.error("proteinx_prediction_failed exc=%s", exc)
            return None
        return None

    def _resolve_protein_length(
        self,
        protein_path: str,
        explicit_sequence: Optional[str],
        *,
        chain_id: Optional[str] = None,
    ) -> Optional[int]:
        """Determine protein sequence length from structure or explicit input."""
        if explicit_sequence:
            return len(explicit_sequence)
        # Fallback: parse from PDB/CIF using biopython
        try:
            from Bio.PDB import PDBParser, MMCIFParser
        except ImportError:
            _LOGGER.warning("biopython_not_installed cannot_parse_structure_length")
            return None
        path_obj = Path(protein_path)
        suffix = path_obj.suffix.lower()
        try:
            if suffix in {".cif", ".mmcif"}:
                parser = MMCIFParser(QUIET=True)
            else:
                parser = PDBParser(QUIET=True)
            structure = parser.get_structure("prot", protein_path)
            # Count residues in the requested chain, or the first chain if none specified
            target_chain = (chain_id or "").strip()
            for model in structure:
                for chain in model:
                    if target_chain and chain.id.strip() != target_chain:
                        continue
                    count = sum(
                        1 for r in chain if not r.id[0].strip()
                    )
                    if count > 0:
                        return count
            # If a specific chain was requested but not found, fall back to the first chain
            if target_chain:
                for model in structure:
                    for chain in model:
                        count = sum(
                            1 for r in chain if not r.id[0].strip()
                        )
                        if count > 0:
                            _LOGGER.warning(
                                "chain_id_not_found_in_structure falling_back_to_first_chain "
                                "requested=%s found=%s count=%d",
                                target_chain,
                                chain.id.strip(),
                                count,
                            )
                            return count
        except Exception as exc:
            _LOGGER.warning("structure_parse_failed_for_length err=%s", exc)
        return None

    def _auto_identify_hotspots(self, protein_path: str, chain_id: str) -> Optional[str]:
        """Run the hotspot identification capability."""
        cap_result = self._invoke_and_record(
            "identify_protein_binding_hotspots",
            {"protein_structure_path": protein_path, "chain_id": chain_id},
            step_name="identify_protein_binding_hotspots",
        )
        if not cap_result.success:
            _LOGGER.warning("hotspot_identification_failed error=%s", cap_result.error)
            return None
        hotspot = cap_result.output.get("hotspot_residues", "")
        if not hotspot:
            _LOGGER.warning("hotspot_identification_returned_empty")
        return hotspot if hotspot else None

    def _build_odesign_json(
        self,
        protein_path: str,
        chain_id: str,
        seq_len: int,
        hotspot: str,
        aptamer_length: int,
    ) -> Optional[dict[str, Any]]:
        """Build ODesign aptamer input JSON."""
        cap_result = self._invoke_and_record(
            "build_odesign_aptamer_input_json",
            {
                "protein_structure_path": protein_path,
                "protein_chain_id": chain_id,
                "protein_sequence_length": seq_len,
                "hotspot_residues": hotspot,
                "aptamer_length": aptamer_length,
            },
            step_name="build_odesign_aptamer_input_json",
        )
        if not cap_result.success:
            _LOGGER.warning("odesign_json_build_failed error=%s", cap_result.error)
            return None
        return dict(cap_result.output)

    def _run_odesign_inference(
        self,
        json_path: str,
        n_sample: int,
        seeds: list[int],
    ) -> Optional[dict[str, Any]]:
        """Run ODesign inference and return the result dict."""
        cap_result = self._invoke_and_record(
            "run_odesign_inference",
            {
                "input_json_filepath": json_path,
                "design_modality": "rna",
                "seeds_json": json.dumps(seeds),
                "n_sample": n_sample,
                "infer_model_name": "odesign_base_na_rigid",
            },
            step_name="run_odesign_inference",
        )
        if not cap_result.success:
            _LOGGER.warning("odesign_inference_failed error=%s", cap_result.error)
            return None
        return dict(cap_result.output)

    def _extract_sequences_from_predictions(self, prediction_paths: list[str]) -> list[str]:
        """Extract RNA sequences from ODesign prediction file paths.

        ODesign outputs can be CIF, PDB, or FASTA depending on version/config.
        We attempt extraction in order of reliability.
        """
        sequences: list[str] = []
        for path in prediction_paths:
            if not path:
                continue
            abs_path = resolve_project_path(path)
            suffix = Path(abs_path).suffix.lower()
            seq: Optional[str] = None

            if suffix in {".cif", ".mmcif"}:
                seq = self._extract_rna_from_cif(abs_path)
            elif suffix == ".pdb":
                seq = self._extract_rna_from_pdb(abs_path)
            elif suffix in {".fasta", ".fa", ".seq", ".txt"}:
                try:
                    content = read_sequence(abs_path)
                    # Strip FASTA header if present
                    lines = [ln.strip() for ln in content.splitlines() if not ln.startswith(">")]
                    candidate_seq = "".join(lines).upper().replace("T", "U")
                    # Keep only AUGC
                    candidate_seq = "".join(ch for ch in candidate_seq if ch in "AUGC")
                    if candidate_seq:
                        seq = candidate_seq
                except Exception as exc:
                    _LOGGER.debug("fasta_read_failed path=%s err=%s", path, exc)
            else:
                _LOGGER.debug("unknown_prediction_suffix suffix=%s path=%s", suffix, path)

            if seq:
                sequences.append(seq)
            else:
                _LOGGER.warning("sequence_extraction_failed path=%s", path)

        return sequences

    def _extract_rna_from_cif(self, cif_path: str) -> Optional[str]:
        """Delegate to the extract_rna_sequence_from_cif capability."""
        cap_result = self._invoke_and_record(
            "extract_rna_sequence_from_cif",
            {"cif_filepath": cif_path},
            step_name="extract_rna_sequence_from_cif",
        )
        if cap_result.success:
            return cap_result.output.get("sequence", "")
        _LOGGER.debug("cif_extraction_failed error=%s", cap_result.error)
        return None

    def _extract_rna_from_pdb(self, pdb_path: str) -> Optional[str]:
        """Extract RNA sequence from a PDB file using biopython.

        Detects RNA by checking for the O2' atom (same heuristic as CIF extractor).
        """
        try:
            from Bio.PDB import PDBParser
        except ImportError:
            _LOGGER.debug("biopython_not_installed cannot_extract_from_pdb")
            return None
        try:
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("rna", pdb_path)
            for model in structure:
                for chain in model:
                    is_rna = False
                    for residue in chain:
                        if residue.id[0].strip():
                            continue
                        atom_names = {atom.name for atom in residue}
                        if "O2'" in atom_names:
                            is_rna = True
                            break
                    if is_rna:
                        base_map = {
                            "A": "A", "U": "U", "G": "G", "C": "C",
                            "DA": "A", "DT": "T", "DG": "G", "DC": "C",
                        }
                        parts = []
                        for residue in chain:
                            if residue.id[0].strip():
                                continue
                            resname = residue.resname.strip()
                            base = base_map.get(resname)
                            if base is None:
                                if len(resname) == 1 and resname in "AUGC":
                                    base = resname
                                else:
                                    base = "N"
                            parts.append(base)
                        return "".join(parts)
            _LOGGER.debug("no_rna_chain_found_in_pdb path=%s", pdb_path)
        except Exception as exc:
            _LOGGER.debug("pdb_extraction_failed path=%s err=%s", pdb_path, exc)
        return None

    def _run_egarps(
        self,
        complex_pdb_path: str,
        *,
        candidate: Optional[Candidate] = None,
    ) -> Optional[float]:
        """Run EGARPS on an RNA-protein complex PDB."""
        cap_result = self._invoke_and_record(
            "score_rna_protein_complex_with_egarps",
            {"filepath": complex_pdb_path, "academic": False},
            candidate=candidate,
            step_name="score_rna_protein_complex_with_egarps",
        )
        if cap_result.success:
            return _pick_float(cap_result.output, "native_probability")
        _LOGGER.debug("egarps_scoring_failed error=%s", cap_result.error)
        return None

    def _try_egarps_from_cif(
        self,
        cif_path: str,
        *,
        candidate: Optional[Candidate] = None,
    ) -> Optional[float]:
        """Convert CIF to PDB, rebuild RNA bases, and run EGARPS."""
        complete_pdb = self._get_complete_complex_pdb(cif_path)
        if not complete_pdb:
            return None
        return self._run_egarps(complete_pdb, candidate=candidate)

    def _run_capability_float(
        self,
        cap_name: str,
        args: dict[str, Any],
        key: str,
        *,
        candidate: Optional[Candidate] = None,
        step_name: Optional[str] = None,
    ) -> Optional[float]:
        """Invoke a capability and safely extract a float field."""
        cap_result = self._invoke_and_record(
            cap_name,
            args,
            candidate=candidate,
            step_name=step_name or cap_name,
        )
        if cap_result.success:
            return _pick_float(cap_result.output, key)
        _LOGGER.warning("%s_failed error=%s", cap_name, cap_result.error)
        return None

    def _resolve_protein_sequence_for_candidate(
        self, candidate: Candidate
    ) -> Optional[str]:
        """Return the protein amino-acid sequence if available."""
        # 1. Try the workflow input cached in state
        inp = self._workflow_state.get("_aptamer_input")
        if inp and getattr(inp, "protein_sequence", None):
            return str(inp.protein_sequence)
        # 2. Try to parse from the protein structure file
        protein_path = candidate.metadata.get("protein_structure_path")
        if protein_path:
            parsed = self._extract_protein_sequence_from_structure(protein_path)
            if parsed:
                return parsed
        return None

    def _extract_protein_sequence_from_structure(
        self, protein_path: str
    ) -> Optional[str]:
        """Extract protein sequence from a PDB/CIF file using biopython."""
        try:
            from Bio.PDB import PDBParser, MMCIFParser
        except ImportError:
            _LOGGER.debug("biopython_not_installed cannot_extract_protein_sequence")
            return None
        try:
            path_obj = Path(protein_path)
            suffix = path_obj.suffix.lower()
            if suffix in {".cif", ".mmcif"}:
                parser = MMCIFParser(QUIET=True)
            else:
                parser = PDBParser(QUIET=True)
            structure = parser.get_structure("prot", protein_path)
            aa_map = {
                "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
                "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
                "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
                "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
            }
            seq_parts: list[str] = []
            for model in structure:
                for chain in model:
                    for residue in chain:
                        if residue.id[0].strip():
                            continue
                        resname = residue.resname.strip().upper()
                        if resname in aa_map:
                            seq_parts.append(aa_map[resname])
                    break  # Only first chain
                break  # Only first model
            return "".join(seq_parts) if seq_parts else None
        except Exception as exc:
            _LOGGER.debug("protein_sequence_extraction_failed err=%s", exc)
            return None

    def _expand_hotspot_residues(
        self, protein_path: str, chain_id: str, hotspot: str, window: int = 3
    ) -> str:
        """Expand hotspot by adding adjacent residue numbers that exist in the structure.

        For each residue in *hotspot* (format "chain/num"), add residues
        within ±*window* positions. Only residue numbers that actually exist
        in the target chain are kept.
        """
        try:
            from Bio.PDB import PDBParser, MMCIFParser
        except ImportError:
            _LOGGER.debug("biopython_not_installed cannot_expand_hotspot")
            return hotspot

        path_obj = Path(protein_path)
        suffix = path_obj.suffix.lower()
        try:
            if suffix in {".cif", ".mmcif"}:
                parser = MMCIFParser(QUIET=True)
            else:
                parser = PDBParser(QUIET=True)
            structure = parser.get_structure("prot", protein_path)
        except Exception as exc:
            _LOGGER.debug("structure_parse_failed_for_hotspot_expansion err=%s", exc)
            return hotspot

        # Collect existing residue numbers for the target chain
        existing_resnums: set[int] = set()
        for model in structure:
            for ch in model:
                if ch.id == chain_id:
                    for residue in ch:
                        if not residue.id[0].strip():  # skip hetero / water
                            existing_resnums.add(residue.id[1])

        if not existing_resnums:
            return hotspot

        expanded: set[str] = set()
        for part in hotspot.split(","):
            part = part.strip()
            if not part:
                continue
            if "/" in part:
                cid, num_str = part.split("/", 1)
            else:
                cid, num_str = chain_id, part
            try:
                num = int(num_str)
            except ValueError:
                continue
            for offset in range(-window, window + 1):
                new_num = num + offset
                if new_num in existing_resnums:
                    expanded.add(f"{cid}/{new_num}")

        # Sort by residue number for stable output
        sorted_expanded = sorted(
            expanded, key=lambda x: int(x.split("/", 1)[1])
        )
        return ",".join(sorted_expanded) if sorted_expanded else hotspot

    def _get_complete_complex_pdb(self, cif_path: str) -> Optional[str]:
        """Convert ODesign CIF to a complete PDB with rebuilt RNA bases.

        ODesign outputs backbone-only RNA structures (missing base atoms).
        This helper: (1) converts CIF→PDB, (2) rebuilds RNA base atoms by
        superimposing standard base templates onto the backbone.

        Returns the path to the complete PDB, or None on failure.
        """
        # Step 1: CIF → backbone-only PDB
        backbone_pdb = self._convert_odesign_cif_to_pdb(cif_path)
        if not backbone_pdb:
            return None

        # Step 2: Rebuild RNA bases
        complete_pdb = self._rebuild_rna_bases_in_pdb(backbone_pdb)
        if complete_pdb:
            _LOGGER.info(
                "rna_bases_rebuilt input=%s output=%s",
                backbone_pdb,
                complete_pdb,
            )
            return complete_pdb
        return backbone_pdb

    def _convert_odesign_cif_to_pdb(self, cif_path: str) -> Optional[str]:
        """Convert ODesign mmCIF (which lacks B_iso_or_equiv) to PDB."""
        path_obj = Path(cif_path)
        suffix = path_obj.suffix.lower()
        if suffix not in {".cif", ".mmcif"}:
            return str(path_obj.resolve())

        try:
            from Bio.PDB.MMCIF2Dict import MMCIF2Dict
            from Bio.PDB.StructureBuilder import StructureBuilder
            from Bio.PDB import PDBIO
        except ImportError:
            _LOGGER.debug("biopython_not_installed cannot_convert_cif_to_pdb")
            return str(path_obj.resolve())

        try:
            d = MMCIF2Dict(str(path_obj))
            cartn_x = d.get("_atom_site.Cartn_x", [])
            if not cartn_x:
                return str(path_obj.resolve())

            label_atom_id = d.get("_atom_site.label_atom_id", [])
            type_symbol = d.get("_atom_site.type_symbol", [])
            label_comp_id = d.get("_atom_site.label_comp_id", [])
            label_asym_id = d.get("_atom_site.label_asym_id", [])
            auth_seq_id = d.get("_atom_site.auth_seq_id", [])
            auth_comp_id = d.get("_atom_site.auth_comp_id", [])
            auth_asym_id = d.get("_atom_site.auth_asym_id", [])
            cartn_y = d.get("_atom_site.Cartn_y", [])
            cartn_z = d.get("_atom_site.Cartn_z", [])
            occupancy = d.get("_atom_site.occupancy", [])

            builder = StructureBuilder()
            builder.init_structure("odesign")
            builder.init_model("0", 0)
            current_chain: Optional[str] = None
            current_residue: Optional[tuple] = None
            serial = 1

            for i in range(len(cartn_x)):
                chain_id = auth_asym_id[i] if i < len(auth_asym_id) else label_asym_id[i]
                res_name = auth_comp_id[i] if i < len(auth_comp_id) else label_comp_id[i]
                res_seq = auth_seq_id[i] if i < len(auth_seq_id) else "1"
                atom_name = label_atom_id[i] if i < len(label_atom_id) else "X"
                element = type_symbol[i] if i < len(type_symbol) else ""
                x, y, z = float(cartn_x[i]), float(cartn_y[i]), float(cartn_z[i])
                occ = float(occupancy[i]) if i < len(occupancy) else 1.0

                if current_chain != chain_id:
                    builder.init_chain(chain_id)
                    current_chain = chain_id
                    current_residue = None

                res_id = (" ", int(res_seq), " ")
                if current_residue != res_id:
                    builder.init_residue(res_name, *res_id)
                    current_residue = res_id

                coord = np.array([x, y, z])
                builder.init_atom(
                    atom_name, coord, occ, 0.0, " ",
                    atom_name, serial_number=serial, element=element,
                )
                serial += 1

            structure = builder.get_structure()
            io = PDBIO()
            io.set_structure(structure)
            pdb_path = resolve_project_path(
                save_text_file("", prefix="odesign_backbone", suffix=".pdb")
            )
            io.save(pdb_path)
            return pdb_path
        except Exception as exc:
            _LOGGER.debug("cif_to_pdb_conversion_failed path=%s err=%s", cif_path, exc)
            return str(path_obj.resolve())

    def _load_rna_base_templates(self) -> dict[str, Any]:
        """Load standard RNA base templates from EGARPS example PDB.

        Templates are cached per workflow instance.
        """
        if hasattr(self, "_rna_base_templates_cache"):
            return self._rna_base_templates_cache

        templates: dict[str, Any] = {}
        ref_pdb = (
            Path(__file__).resolve().parents[2]
            / "external_repos"
            / "EGARPS"
            / "example"
            / "complex1_rna.pdb"
        )
        try:
            from Bio.PDB import PDBParser
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("ref", str(ref_pdb))
            for model in structure:
                for chain in model:
                    for residue in chain:
                        resname = residue.resname.strip().upper()
                        if resname in ("A", "U", "G", "C") and resname not in templates:
                            templates[resname] = residue
                    if len(templates) == 4:
                        break
                if len(templates) == 4:
                    break
        except Exception as exc:
            _LOGGER.debug("rna_base_template_load_failed err=%s", exc)

        self._rna_base_templates_cache = templates
        return templates

    def _rebuild_rna_bases_in_pdb(self, pdb_path: str) -> Optional[str]:
        """Rebuild missing RNA base atoms in a backbone-only PDB.

        Uses Kabsch alignment on three reference atoms (C1', glycosidic N,
        C2') to superimpose standard base templates onto each RNA residue.
        """
        try:
            from Bio.PDB import PDBParser, PDBIO
            from Bio.PDB.Atom import Atom
        except ImportError:
            return None

        templates = self._load_rna_base_templates()
        if len(templates) != 4:
            _LOGGER.debug("rna_base_templates_not_available")
            return None

        # Backbone atoms that are already present in the ODesign output
        backbone_atoms = {
            "P", "OP1", "OP2", "O5'", "C5'", "C4'", "O4'",
            "C3'", "O3'", "C2'", "O2'", "C1'",
        }

        # Glycosidic bond atom: N9 for purines, N1 for pyrimidines
        glyco_n = {"A": "N9", "G": "N9", "C": "N1", "U": "N1"}

        try:
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("complex", pdb_path)

            for model in structure:
                for chain in model:
                    for residue in chain:
                        resname = residue.resname.strip().upper()
                        if resname not in ("A", "U", "G", "C"):
                            continue

                        template = templates.get(resname)
                        if template is None:
                            continue

                        # Collect reference atoms for Kabsch
                        # Template uses standard names (N9 for purines, N1 for pyrimidines).
                        # ODesign outputs backbone-only structures where the glycosidic
                        # nitrogen is simply named "N".  We therefore map the template
                        # reference atom to the target "N" when the standard name is absent.
                        template_ref = glyco_n[resname]
                        target_ref = template_ref
                        if not any(a.name == target_ref for a in residue):
                            if any(a.name == "N" for a in residue):
                                target_ref = "N"

                        ref_atoms = [("C1'", "C1'"), (template_ref, target_ref), ("C2'", "C2'")]
                        P = []
                        Q = []
                        for t_name, r_name in ref_atoms:
                            t_atom = None
                            r_atom = None
                            for a in template:
                                if a.name == t_name:
                                    t_atom = a.coord.copy()
                                    break
                            for a in residue:
                                if a.name == r_name:
                                    r_atom = a.coord.copy()
                                    break
                            if t_atom is None or r_atom is None:
                                break
                            P.append(t_atom)
                            Q.append(r_atom)

                        if len(P) != 3:
                            _LOGGER.debug(
                                "rna_base_rebuild_missing_ref_atoms residue=%s%s found=%s",
                                resname, residue.id[1], [a.name for a in residue]
                            )
                            continue

                        P = np.array(P)
                        Q = np.array(Q)

                        # Kabsch algorithm
                        P_center = P.mean(axis=0)
                        Q_center = Q.mean(axis=0)
                        P_norm = P - P_center
                        Q_norm = Q - Q_center
                        H = P_norm.T @ Q_norm
                        U, S, Vt = np.linalg.svd(H)
                        R = Vt.T @ U.T
                        if np.linalg.det(R) < 0:
                            Vt[-1, :] *= -1
                            R = Vt.T @ U.T
                        t_vec = Q_center - R @ P_center

                        # Remove the placeholder "N" atom left by ODesign
                        # (it will be replaced by the proper glycosidic N from the template)
                        for a in list(residue.get_atoms()):
                            if a.name == "N":
                                residue.detach_child(a.id)

                        # Add missing base atoms from template
                        for t_atom in template:
                            if t_atom.name in backbone_atoms:
                                continue
                            if t_atom.name in [a.name for a in residue]:
                                continue
                            new_coord = R @ t_atom.coord + t_vec
                            new_atom = Atom(
                                t_atom.name,
                                new_coord,
                                t_atom.bfactor,
                                t_atom.occupancy,
                                t_atom.altloc,
                                t_atom.fullname,
                                serial_number=t_atom.serial_number,
                                element=t_atom.element,
                            )
                            residue.add(new_atom)

            io = PDBIO()
            io.set_structure(structure)
            out_path = resolve_project_path(
                save_text_file("", prefix="odesign_complete", suffix=".pdb")
            )
            io.save(out_path)
            return out_path

        except Exception as exc:
            _LOGGER.debug("rna_base_rebuild_failed path=%s err=%s", pdb_path, exc)
            return None

    def _ensure_pdb_for_interface_analysis(
        self, structure_path: str
    ) -> Optional[str]:
        """Return a PDB filepath suitable for analyze_rna_protein_interface.

        ODesign outputs mmCIF files that omit ``_atom_site.B_iso_or_equiv``
        and contain backbone-only RNA structures.  This helper produces a
        complete PDB with rebuilt RNA bases.
        """
        path_obj = Path(structure_path)
        suffix = path_obj.suffix.lower()
        if suffix not in {".cif", ".mmcif"}:
            return structure_path
        return self._get_complete_complex_pdb(structure_path)

    def _detect_chains_in_pdb(
        self,
        pdb_path: str,
        fallback_protein_chain: str,
        fallback_rna_chain: str,
    ) -> tuple[str, str]:
        """Detect actual chain IDs in a PDB file.

        ODesign always outputs protein as chain A and RNA as chain B,
        regardless of the original input chain IDs.  This helper peeks
        at the first model and returns the most likely protein/RNA
        chain IDs based on residue composition.
        """
        try:
            from Bio.PDB import PDBParser
        except ImportError:
            return fallback_protein_chain, fallback_rna_chain

        try:
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("complex", pdb_path)
        except Exception:
            return fallback_protein_chain, fallback_rna_chain

        chain_candidates: list[tuple[str, int, int]] = []
        for model in structure:
            for chain in model:
                protein_like = 0
                rna_like = 0
                for residue in chain:
                    if residue.id[0].strip():
                        continue  # skip hetero/water
                    resname = residue.resname.strip().upper()
                    # Standard amino-acid 3-letter codes
                    if resname in {
                        "ALA", "CYS", "ASP", "GLU", "PHE", "GLY", "HIS", "ILE",
                        "LYS", "LEU", "MET", "ASN", "PRO", "GLN", "ARG", "SER",
                        "THR", "VAL", "TRP", "TYR",
                    }:
                        protein_like += 1
                    # Standard RNA nucleotides
                    elif resname in {"A", "U", "G", "C", "DA", "DT", "DG", "DC"}:
                        rna_like += 1
                chain_candidates.append((chain.id, protein_like, rna_like))

        if not chain_candidates:
            return fallback_protein_chain, fallback_rna_chain

        # Sort by protein-like count descending, then by rna-like count ascending
        chain_candidates.sort(key=lambda x: (x[1], -x[2]), reverse=True)
        best_protein = chain_candidates[0][0]

        # For RNA, pick the chain with the most RNA-like residues that isn't the protein chain
        rna_candidates = [c for c in chain_candidates if c[0] != best_protein]
        if rna_candidates:
            rna_candidates.sort(key=lambda x: x[2], reverse=True)
            best_rna = rna_candidates[0][0]
        else:
            best_rna = chain_candidates[-1][0] if len(chain_candidates) > 1 else fallback_rna_chain

        if best_protein != fallback_protein_chain or best_rna != fallback_rna_chain:
            _LOGGER.info(
                "chain_ids_detected_from_structure detected_protein=%s detected_rna=%s "
                "fallback_protein=%s fallback_rna=%s",
                best_protein,
                best_rna,
                fallback_protein_chain,
                fallback_rna_chain,
            )

        return best_protein, best_rna


# Aptamer-specific scoring helpers


def score_aptamer_candidate(
    metrics: dict[str, Any],
    weight_egarps: float = 0.50,
    weight_rhofold: float = 0.50,
) -> dict[str, float]:
    """Standalone scoring function for aptamer candidates (reusable outside the workflow).

    EGARPS, RhoFold pLDDT, and ProteinX ipTM are each normalised to [0, 1]
    and combined using the provided weights.  Missing components are omitted
    and the remaining active weights are re-normalised so that the sum of
    active weights equals 1.0.
    """
    egarps_prob = metrics.get("egarps_native_probability")
    rhofold_plddt = metrics.get("rhofold_mean_plddt")
    iptm = metrics.get("proteinx_ipTM")

    scores: dict[str, float] = {}

    if egarps_prob is not None:
        scores["egarps_component"] = float(egarps_prob)
    else:
        scores["egarps_component"] = 0.0

    if rhofold_plddt is not None:
        scores["rhofold_component"] = max(0.0, min(1.0, float(rhofold_plddt) / 100.0))
    else:
        scores["rhofold_component"] = 0.0

    if iptm is not None:
        scores["iptm_component"] = max(0.0, min(1.0, float(iptm)))
    else:
        scores["iptm_component"] = 0.0

    # ipTM receives the residual weight budget
    weight_iptm = max(0.0, 1.0 - weight_egarps - weight_rhofold)

    # Weighted sum over available components; re-normalise when some are missing
    active_weights = 0.0
    weighted_sum = 0.0

    if egarps_prob is not None:
        active_weights += weight_egarps
        weighted_sum += weight_egarps * scores["egarps_component"]
    if rhofold_plddt is not None:
        active_weights += weight_rhofold
        weighted_sum += weight_rhofold * scores["rhofold_component"]
    if iptm is not None:
        active_weights += weight_iptm
        weighted_sum += weight_iptm * scores["iptm_component"]

    if active_weights > 0.0:
        scores["total_score"] = weighted_sum / active_weights
    else:
        scores["total_score"] = 0.0

    return scores


# LLM Critic Configuration

from agent_core.planning.llm_critic import BaseLLMCritic, CriticConfig

RNA_APTAMER_CRITIC_CONFIG = CriticConfig(
    workflow_name="rna_aptamer_design",
    workflow_description=(
        "Design RNA aptamers against a protein target using 3D-structure-guided generation. "
        "NOTE: Hard biological thresholds (EGARPS ≥ 0.30, RhoFold pLDDT ≥ 70, ipTM ≥ 0.60, "
        "interface contacts ≥ 5, GC 30–70%) are handled internally by AptamerCoordinator. "
        "This Critic focuses on user-intent alignment and scoring strategy, not threshold enforcement."
    ),
    evaluation_dimensions=[
        "User priority alignment: Check whether the user explicitly prioritized binding affinity over foldability (or vice versa). If so, verify that the scoring weights reflect that priority. Coordinator handles raw metric thresholds; you handle intent.",
        "Scoring balance: If weight_egarps is very high (>0.7) but top candidates have poor RhoFold pLDDT, consider reducing the EGARPS weight to allow more foldable sequences. Conversely, if weight_rhofold dominates but binding is weak, consider increasing EGARPS weight.",
        "Candidate diversity: If all top candidates come from the same ODesign seed or have nearly identical sequences, recommend increasing sample count or changing seeds for broader exploration.",
        "Target suitability: If the protein target is very small or has no obvious binding pockets, flag that the problem may be ill-posed rather than suggesting parameter tweaks.",
        "CRITICAL: Do NOT apply hard thresholds for EGARPS, pLDDT, ipTM, or GC content — AptamerCoordinator already does that deterministically. Focus on whether the results align with the user's stated goals and constraints.",
    ],
    adjustable_params={
        # High-level scoring strategy parameters (user intent alignment)
        "weight_egarps": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Weight for EGARPS native probability in scoring. Increase to prioritize binding affinity over foldability.",
        },
        "weight_rhofold": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Weight for RhoFold pLDDT in scoring. Increase to prioritize RNA foldability over binding affinity.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
)


class RnaAptamerDesignLLMCritic(BaseLLMCritic):
    """LLM-driven Critic for RNA aptamer design workflow."""

    def _default_config(self) -> CriticConfig:
        return RNA_APTAMER_CRITIC_CONFIG


class LLMAptamerCoordinator(AptamerCoordinator):
    """LLM-based coordinator for ablation study (BMC-LLM-Coord).

    Replaces the deterministic ``diagnose()`` with an LLM call while preserving
    ``broadcast_feedback()`` and ``has_converged()`` from the parent class.
    On LLM failure, gracefully falls back to the deterministic rule engine.
    """

    def __init__(self, provider: str = "deepseek", temperature: float = 0.1):
        super().__init__()
        self._llm: Any = None
        try:
            self._llm = get_llm_for_provider(provider, temperature=temperature)
        except Exception as exc:
            _LOGGER.warning("llm_coord_init_failed fallback_to_deterministic exc=%s", exc)

    def diagnose(self, metrics: dict[str, Any]) -> list[Issue]:
        if self._llm is None:
            _LOGGER.warning("llm_coord_no_llm fallback_to_deterministic")
            return super().diagnose(metrics)
        try:
            return self._diagnose_with_llm(metrics)
        except Exception as exc:
            _LOGGER.warning("llm_coord_diagnose_failed fallback_to_deterministic exc=%s", exc)
            return super().diagnose(metrics)

    def _diagnose_with_llm(self, metrics: dict[str, Any]) -> list[Issue]:
        from langchain_core.messages import HumanMessage, SystemMessage

        # Build metrics and threshold lines for the prompt
        metrics_lines: list[str] = []
        for k, v in metrics.items():
            if v is not None and not isinstance(v, str):
                metrics_lines.append(f"- {k}: {v}")

        threshold_lines: list[str] = []
        for k, v in self.THRESHOLDS.items():
            if k == "gc_content_min":
                threshold_lines.append(f"- gc_content >= {v}")
            elif k == "gc_content_max":
                threshold_lines.append(f"- gc_content <= {v}")
            else:
                threshold_lines.append(f"- {k} >= {v}")

        metrics_text = "\n".join(metrics_lines) if metrics_lines else "(none)"
        thresholds_text = "\n".join(threshold_lines) if threshold_lines else "(none)"

        prompt = (
            "You are a biomolecular design coordinator diagnosing issues in an "
            "RNA aptamer design candidate.\n\n"
            f"Metrics:\n{metrics_text}\n\n"
            f"Thresholds:\n{thresholds_text}\n\n"
            "Return a JSON array of issues. Each issue must have:\n"
            '- issue_type: one of BINDING_AFFINITY_LOW, RNA_FOLDABILITY_LOW, '
            "COMPLEX_CONFIDENCE_LOW, INTERFACE_TOO_WEAK, EXTREME_GC_CONTENT\n"
            "- value: the actual metric value (number)\n"
            "- target: the threshold value (number)\n"
            '- affected_modules: list containing "Target" and/or "Aptamer"\n'
            "- evidence: a short sentence\n\n"
            "If no thresholds are violated, return an empty array [].\n"
            "Return ONLY the JSON array, no markdown, no explanation."
        )

        messages = [
            SystemMessage(content="You are a deterministic biomolecular design coordinator."),
            HumanMessage(content=prompt),
        ]

        response = self._llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            parts = content.split("```", 2)
            if len(parts) >= 3:
                content = parts[1]
                if content.startswith("json"):
                    content = content[4:].strip()

        items = json.loads(content)
        if not isinstance(items, list):
            raise ValueError(f"Expected JSON array, got {type(items).__name__}")

        issues: list[Issue] = []
        for item in items:
            amods = item.get("affected_modules", [])
            if isinstance(amods, str):
                amods = [amods]
            issue = Issue(
                issue_type=item["issue_type"],
                value=float(item["value"]),
                target=float(item["target"]),
                affected_modules=tuple(amods),
                evidence=item["evidence"],
            )
            issues.append(issue)

        return issues


# Small helpers
