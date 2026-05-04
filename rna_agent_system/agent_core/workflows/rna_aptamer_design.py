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
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import (
    copy_file_to_workspace,
    read_sequence,
    resolve_project_path,
    save_sequence,
    save_text_file,
)
from agent_core.planning.base import Critic
from agent_core.workflow_models import Candidate, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow

_LOGGER = logging.getLogger("agent_core.workflows.rna_aptamer_design")

# ═══════════════════════════════════════════════════════════════════════════════
# Input model
# ═══════════════════════════════════════════════════════════════════════════════


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
    # Current scoring uses only EGARPS and RhoFold pLDDT.
    weight_egarps: float = Field(default=0.50, description="Weight for EGARPS native probability.")
    weight_rhofold: float = Field(default=0.50, description="Weight for RhoFold pLDDT.")


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow implementation
# ═══════════════════════════════════════════════════════════════════════════════


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

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, inp: Any) -> WorkflowResult:
        """Accept either ``RnaAptamerDesignInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = RnaAptamerDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._workflow_state["_aptamer_input"] = inp
        result = super().run(inp)
        result._state_writeback = dict(self._workflow_state)  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: RnaAptamerDesignInput) -> list[Candidate]:
        """Generate aptamer candidates via ODesign structure-guided generation.

        Steps:
          1. Resolve protein structure path.
          2. Identify binding hotspots (if not provided), with optional expansion.
          3. Apply retry constraints (adjust aptamer length / expand hotspot).
          4. Build ODesign aptamer input JSON.
          5. Run ODesign inference.
          6. Parse prediction files to extract RNA sequences.
        """
        # ── 1. Resolve protein structure ──
        protein_path = self._resolve_protein_structure(inp)
        if not protein_path:
            _LOGGER.error("No valid protein structure available")
            return []

        # Resolve sequence length from structure or explicit input
        protein_seq_len = self._resolve_protein_length(protein_path, inp.protein_sequence)
        if protein_seq_len is None or protein_seq_len <= 0:
            _LOGGER.error("Cannot determine protein sequence length")
            return []

        # ── 2. Hotspot identification ──
        hotspot = inp.hotspot_residues
        expand_hotspot = self._workflow_state.get("_aptamer_expand_hotspot", False)
        if not hotspot:
            _LOGGER.info("hotspot_not_provided running_auto_identification")
            hotspot = self._auto_identify_hotspots(protein_path, inp.chain_id)
            if not hotspot:
                _LOGGER.error("hotspot_identification_failed")
                return []
            _LOGGER.info("hotspot_auto_identified residues=%s", hotspot)

        # Expand hotspot region if requested by critic retry
        if expand_hotspot and hotspot:
            expanded = self._expand_hotspot_residues(protein_path, inp.chain_id, hotspot, window=3)
            if expanded and expanded != hotspot:
                _LOGGER.info("hotspot_expanded old=%s new=%s", hotspot, expanded)
                hotspot = expanded

        # Apply aptamer length adjustment if requested by critic retry
        aptamer_length = inp.aptamer_length
        if self._workflow_state.get("_aptamer_retry_adjust_length", False):
            aptamer_length = min(200, aptamer_length + 5)
            _LOGGER.info("aptamer_length_adjusted old=%d new=%d", inp.aptamer_length, aptamer_length)

        # ── 3. Build ODesign input JSON ──
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

        # ── 4. Run ODesign inference ──
        odesign_result = self._run_odesign_inference(
            json_path=json_path,
            n_sample=inp.n_odesign_samples,
            seeds=inp.odesign_seeds,
        )
        if not odesign_result:
            _LOGGER.error("odesign_inference_failed")
            return []

        prediction_paths = odesign_result.get("prediction_filepaths", [])
        _LOGGER.info("odesign_predictions count=%d", len(prediction_paths))

        # ── 5. Extract RNA sequences from prediction files ──
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
                    source=f"odesign_aptamer:s{inp.odesign_seeds[0]}:i{idx}",
                    metadata={
                        "protein_structure_path": protein_path,
                        "protein_chain_id": inp.chain_id,
                        "hotspot_residues": hotspot,
                        "aptamer_length": aptamer_length,
                        "odesign_prediction_path": prediction_paths[idx] if idx < len(prediction_paths) else None,
                        "odesign_input_json": json_path,
                        "design_params": {
                            "n_sample": inp.n_odesign_samples,
                            "seeds": inp.odesign_seeds,
                        },
                    },
                )
            )

        _LOGGER.info("candidates_generated total=%d unique=%d", len(sequences), len(candidates))
        return candidates

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
        )
        metrics["gc_content"] = gc_content

        # ── RhoFold tertiary structure ──
        rhofold_plddt: Optional[float] = None
        rhofold_pdb: Optional[str] = None
        if self.capabilities.has("predict_rna_tertiary_structure_with_rhofold"):
            rh_res = self.capabilities.get("predict_rna_tertiary_structure_with_rhofold").invoke(
                {"filepath": filepath}, state=self._workflow_state
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
                egarps_prob = self._run_egarps(str(pred_path_obj.resolve()))
            elif suffix in {".cif", ".mmcif"}:
                egarps_prob = self._try_egarps_from_cif(str(pred_path_obj.resolve()))
            else:
                _LOGGER.debug("egarps_skipped_unknown_suffix suffix=%s", suffix)
        else:
            _LOGGER.debug("egarps_skipped_no_odesign_structure")
        metrics["egarps_native_probability"] = egarps_prob

        # ── ProteinX RNA-protein complex prediction (best-effort) ──
        iptm: Optional[float] = None
        proteinx_plddt: Optional[float] = None
        proteinx_pdb: Optional[str] = None
        protein_seq = self._resolve_protein_sequence_for_candidate(candidate)
        if protein_seq and self.capabilities.has("predict_rna_protein_complex_with_proteinx"):
            # Save protein and RNA sequences as FASTA files
            protein_fasta = save_sequence(f">protein\n{protein_seq}\n", prefix="protein_for_complex")
            rna_fasta = save_sequence(f">rna\n{seq}\n", prefix="rna_for_complex")
            try:
                cap = self.capabilities.get("predict_rna_protein_complex_with_proteinx")
                px_res = cap.invoke(
                    {
                        "protein_filepath": protein_fasta,
                        "rna_filepath": rna_fasta,
                        "num_models": 1,
                    },
                    state=self._workflow_state,
                )
                if px_res.success:
                    iptm = _pick_float(px_res.output, "ipTM")
                    proteinx_plddt = _pick_float(px_res.output, "mean_plddt")
                    proteinx_pdb = px_res.output.get("pdb_filepath", "")
                else:
                    _LOGGER.warning("proteinx_complex_failed error=%s", px_res.error)
            except Exception as exc:
                _LOGGER.warning("proteinx_complex_exception exc=%s", exc)
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
                cap = self.capabilities.get("analyze_rna_protein_interface")
                iface_res = cap.invoke(
                    {
                        "complex_pdb_filepath": odesign_pred_path,
                        "protein_chain_id": protein_chain,
                        "rna_chain_id": rna_chain,
                        "contact_cutoff": 5.0,
                    },
                    state=self._workflow_state,
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
        """Combine raw metrics into a single aptamer quality score.

        EGARPS, RhoFold pLDDT, and ProteinX ipTM are each normalised to [0, 1]
        and added together. Interface metrics are collected but not included in
        the total score (they are reported for reference).
        """
        egarps_prob = metrics.get("egarps_native_probability")
        rhofold_plddt = metrics.get("rhofold_mean_plddt")
        iptm = metrics.get("proteinx_ipTM")

        scores: dict[str, float] = {}

        # EGARPS: native_probability is already in [0, 1]
        if egarps_prob is not None:
            scores["egarps_component"] = float(egarps_prob)
        else:
            scores["egarps_component"] = 0.0

        # RhoFold: pLDDT in [0, 100] → [0, 1]
        if rhofold_plddt is not None:
            scores["rhofold_component"] = max(0.0, min(1.0, float(rhofold_plddt) / 100.0))
        else:
            scores["rhofold_component"] = 0.0

        # ProteinX ipTM: already in [0, 1]
        if iptm is not None:
            scores["iptm_component"] = max(0.0, min(1.0, float(iptm)))
        else:
            scores["iptm_component"] = 0.0

        # Simple sum of normalised components
        scores["total_score"] = (
            scores["egarps_component"]
            + scores["rhofold_component"]
            + scores["iptm_component"]
        )
        return scores

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return WorkflowResult(
                success=False,
                task_id="",
                summary="No aptamer candidates produced.",
                errors=["empty_candidate_list"],
            )

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
                cap = self.capabilities.get("predict_protein_structure_with_proteinx")
                result = cap.invoke(
                    {
                        "filepath": abs_fasta,
                        "num_models": 1,
                        "msa_mode": "none",
                    },
                    state=self._workflow_state,
                )
                pdb_path = result.get("pdb_filepath", "")
                if pdb_path and Path(pdb_path).exists():
                    _LOGGER.info("protein_structure_predicted path=%s", pdb_path)
                    return pdb_path
                _LOGGER.error("proteinx_returned_invalid_path path=%s", pdb_path)
            except Exception as exc:
                _LOGGER.error("proteinx_prediction_failed exc=%s", exc)
            return None
        return None

    def _resolve_protein_length(
        self, protein_path: str, explicit_sequence: Optional[str]
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
            # Count residues in the first chain
            for model in structure:
                for chain in model:
                    count = sum(
                        1 for r in chain if not r.id[0].strip()
                    )
                    return count
        except Exception as exc:
            _LOGGER.warning("structure_parse_failed_for_length err=%s", exc)
        return None

    def _auto_identify_hotspots(self, protein_path: str, chain_id: str) -> Optional[str]:
        """Run the hotspot identification capability."""
        if not self.capabilities.has("identify_protein_binding_hotspots"):
            _LOGGER.warning("capability_missing identify_protein_binding_hotspots")
            return None
        cap = self.capabilities.get("identify_protein_binding_hotspots")
        cap_result = cap.invoke(
            {"protein_structure_path": protein_path, "chain_id": chain_id},
            state=self._workflow_state,
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
        if not self.capabilities.has("build_odesign_aptamer_input_json"):
            _LOGGER.warning("capability_missing build_odesign_aptamer_input_json")
            return None
        cap = self.capabilities.get("build_odesign_aptamer_input_json")
        cap_result = cap.invoke(
            {
                "protein_structure_path": protein_path,
                "protein_chain_id": chain_id,
                "protein_sequence_length": seq_len,
                "hotspot_residues": hotspot,
                "aptamer_length": aptamer_length,
            },
            state=self._workflow_state,
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
        if not self.capabilities.has("run_odesign_inference"):
            _LOGGER.warning("capability_missing run_odesign_inference")
            return None
        cap = self.capabilities.get("run_odesign_inference")
        cap_result = cap.invoke(
            {
                "input_json_filepath": json_path,
                "design_modality": "rna",
                "seeds_json": json.dumps(seeds),
                "n_sample": n_sample,
                "infer_model_name": "odesign_base_na_rigid",
            },
            state=self._workflow_state,
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
        if not self.capabilities.has("extract_rna_sequence_from_cif"):
            _LOGGER.warning("capability_missing extract_rna_sequence_from_cif")
            return None
        cap = self.capabilities.get("extract_rna_sequence_from_cif")
        cap_result = cap.invoke(
            {"cif_filepath": cif_path},
            state=self._workflow_state,
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

    def _run_egarps(self, complex_pdb_path: str) -> Optional[float]:
        """Run EGARPS on an RNA-protein complex PDB."""
        if not self.capabilities.has("score_rna_protein_complex_with_egarps"):
            return None
        cap = self.capabilities.get("score_rna_protein_complex_with_egarps")
        cap_result = cap.invoke(
            {"filepath": complex_pdb_path, "academic": False},
            state=self._workflow_state,
        )
        if cap_result.success:
            return _pick_float(cap_result.output, "native_probability")
        _LOGGER.debug("egarps_scoring_failed error=%s", cap_result.error)
        return None

    def _try_egarps_from_cif(self, cif_path: str) -> Optional[float]:
        """Convert CIF to PDB and run EGARPS."""
        try:
            from Bio.PDB import PDBParser, MMCIFParser, PDBIO
        except ImportError:
            _LOGGER.debug("biopython_not_installed cannot_convert_cif_to_pdb")
            return None
        try:
            parser = MMCIFParser(QUIET=True)
            structure = parser.get_structure("complex", cif_path)
            io = PDBIO()
            io.set_structure(structure)
            tmp_path = save_text_file("", prefix="egarps_tmp", suffix=".pdb")
            # save_text_file writes empty text; we need to overwrite with PDB content
            abs_tmp = resolve_project_path(tmp_path)
            io.save(abs_tmp)
            result = self._run_egarps(abs_tmp)
            # Clean up temp file
            try:
                Path(abs_tmp).unlink(missing_ok=True)
            except Exception:
                pass
            return result
        except Exception as exc:
            _LOGGER.debug("cif_to_pdb_conversion_failed err=%s", exc)
            return None

    def _run_capability_float(
        self, cap_name: str, args: dict[str, Any], key: str
    ) -> Optional[float]:
        """Invoke a capability and safely extract a float field."""
        if not self.capabilities.has(cap_name):
            _LOGGER.warning("capability_missing %s", cap_name)
            return None
        cap = self.capabilities.get(cap_name)
        cap_result = cap.invoke(args, state=self._workflow_state)
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


# ═══════════════════════════════════════════════════════════════════════════════
# Aptamer-specific scoring helpers
# ═══════════════════════════════════════════════════════════════════════════════


def score_aptamer_candidate(
    metrics: dict[str, Any],
) -> dict[str, float]:
    """Standalone scoring function for aptamer candidates (reusable outside the workflow).

    EGARPS, RhoFold pLDDT, and ProteinX ipTM are each normalised to [0, 1]
    and added together.
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

    scores["total_score"] = (
        scores["egarps_component"]
        + scores["rhofold_component"]
        + scores["iptm_component"]
    )
    return scores


# ═══════════════════════════════════════════════════════════════════════════════
# Critic
# ═══════════════════════════════════════════════════════════════════════════════


class RnaAptamerCritic(Critic):
    """Quality gate for RNA aptamer design.

    Triggers retry when:
      1. Too few candidates survive basic filters (GC in [0.2, 0.8]).
      2. EGARPS scores are uniformly poor (< 0.4) when EGARPS is available.

    The actual retry count limit (max 3) is enforced by the ExecutionController
    via ExecutionPlan.max_retries.
    """

    MIN_SURVIVING_CANDIDATES: int = 3
    EGARPS_POOR_THRESHOLD: float = 0.4
    GC_MIN: float = 0.2
    GC_MAX: float = 0.8

    def should_retry(self, workflow_result: WorkflowResult, state: dict[str, Any]) -> bool:
        candidates = workflow_result.all_candidates
        if not candidates:
            return False

        # Count candidates with reasonable GC
        gc_ok = 0
        for c in candidates:
            gc = c.metadata.get("metrics_bundle", {}).get("gc_content")
            if gc is not None and self.GC_MIN <= float(gc) <= self.GC_MAX:
                gc_ok += 1

        if gc_ok < self.MIN_SURVIVING_CANDIDATES:
            state.setdefault("next_constraints", {})
            state["next_constraints"]["adjust_aptamer_length"] = True
            # Signal the workflow to use adjusted length on next run
            state["_aptamer_retry_adjust_length"] = True
            return True

        # If EGARPS was run for at least one candidate and all are poor
        egarps_values = [
            c.metadata.get("metrics_bundle", {}).get("egarps_native_probability")
            for c in candidates
        ]
        egarps_values = [v for v in egarps_values if v is not None]
        if egarps_values and all(float(v) < self.EGARPS_POOR_THRESHOLD for v in egarps_values):
            state.setdefault("next_constraints", {})
            state["next_constraints"]["expand_hotspot_region"] = True
            # Signal the workflow to expand hotspot on next run
            state["_aptamer_expand_hotspot"] = True
            return True

        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Small helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _pick_float(data: dict[str, Any], key: str) -> Optional[float]:
    if key in data:
        try:
            return float(data[key])
        except (TypeError, ValueError):
            pass
    return None
