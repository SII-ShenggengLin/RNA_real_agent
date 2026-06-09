"""Bounded Multi-Module Coordination (BMC) coordinator for full-length mRNA design.

Provides a deterministic, rule-based coordinator that diagnoses inter-module
conflicts in assembled full-length mRNA candidates and broadcasts structured
feedback to affected module agents for iterative refinement.

The coordinator is intentionally NOT an LLM — its decisions are fully auditable,
testable, and grounded in explicit tool-derived thresholds.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger("agent_core.workflows.coordinator")


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Issue:
    """One diagnosed inter-module conflict."""

    issue_type: str
    value: float
    target: float
    affected_modules: tuple[str, ...]
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "value": self.value,
            "target": self.target,
            "affected_modules": list(self.affected_modules),
            "evidence": self.evidence,
        }


@dataclass
class ParamAdjustment:
    """A single parameter adjustment for a module agent."""

    param: str
    delta: float
    reason: str = ""


@dataclass
class ModuleFeedback:
    """Structured feedback sent to one module agent."""

    priority: str  # "high" | "medium" | "low"
    adjustments: list[ParamAdjustment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "adjustments": [
                {"param": a.param, "delta": a.delta, "reason": a.reason}
                for a in self.adjustments
            ],
        }


@dataclass
class CoordinationRound:
    """Trace record for one BMC iteration round."""

    round_num: int
    best_candidate_id: str
    best_total_score: float
    issues_found: list[Issue]
    feedback_dispatched: dict[str, ModuleFeedback]
    modules_reinvoked: list[str]
    time_elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_num": self.round_num,
            "best_candidate_id": self.best_candidate_id,
            "best_total_score": self.best_total_score,
            "issues_found": [i.to_dict() for i in self.issues_found],
            "feedback_dispatched": {
                k: v.to_dict() for k, v in self.feedback_dispatched.items()
            },
            "modules_reinvoked": self.modules_reinvoked,
            "time_elapsed_ms": self.time_elapsed_ms,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Full-Length Coordinator
# ─────────────────────────────────────────────────────────────────────────────


class FullLengthCoordinator:
    """Deterministic coordinator for full-length mRNA module conflict diagnosis.

    Thresholds are chosen based on domain heuristics and LinearDesign benchmarks:
    - full_mfe_per_nt: ≤ -0.25 kcal/mol/nt (length-normalized stability;
      MFE is proportional to sequence length, so absolute thresholds are unfair)
    - full_paired_fraction: ≥ 0.65 (≥65% base-paired; wild-type ~63%,
      LinearDesign optimal ~83%; see Zhang et al. Nature 2023)
    - junction_cds_3utr_mfe: ≤ -15 kcal/mol (CDS-3'UTR local stability; 40-nt overlap)
    - junction_gc_diff: ≤ 0.15 (15% GC difference across junction)

    References:
    - LinearDesign objective: MFECAI_λ = MFE − λ·(|r|/3)·log(CAI)
      (Zhang et al., "Algorithm for optimized mRNA design improves stability
      and immunogenicity", Nature 2023)
    - λ=0 → MFE-only (most stable); λ↑ → CAI improves, MFE worsens.
    """

    THRESHOLDS: dict[str, float] = {
        "full_mfe_per_nt": -0.25,     # kcal/mol per nucleotide (wild-type baseline)
        "full_paired_fraction": 0.65,  # minimum fraction of paired bases
        "junction_cds_3utr_mfe": -15.0,  # kcal/mol (40-nt overlap)
        "junction_gc_diff": 0.15,     # max GC diff across junction
    }

    # ── Diagnosis ────────────────────────────────────────────────────────────

    def diagnose(self, metrics: dict[str, Any]) -> list[Issue]:
        """Scan metrics for inter-module conflicts and return structured issues.

        Every issue carries explicit evidence grounded in tool-derived values.
        """
        issues: list[Issue] = []

        # 1. Full-length MFE (length-normalized)
        full_mfe = metrics.get("full_length_mfe")
        total_length = metrics.get("total_length", 0)
        if full_mfe is not None and total_length and total_length > 0:
            mfe_per_nt = float(full_mfe) / int(total_length)
            if mfe_per_nt > self.THRESHOLDS["full_mfe_per_nt"]:
                issues.append(
                    Issue(
                        issue_type="FULL_MFE_TOO_HIGH",
                        value=mfe_per_nt,
                        target=self.THRESHOLDS["full_mfe_per_nt"],
                        affected_modules=("5UTR", "CDS", "3UTR"),
                        evidence=(
                            f"ViennaRNA full-length MFE={full_mfe:.2f} kcal/mol "
                            f"(length={total_length}nt, "
                            f"MFE/nt={mfe_per_nt:.4f} kcal/mol/nt) "
                            f"> threshold={self.THRESHOLDS['full_mfe_per_nt']:.4f}"
                        ),
                    )
                )

        # 1b. Full-length paired fraction (structure stability)
        paired_fraction = metrics.get("full_paired_fraction")
        if paired_fraction is not None and float(paired_fraction) < self.THRESHOLDS["full_paired_fraction"]:
            issues.append(
                Issue(
                    issue_type="FULL_STRUCTURE_TOO_LOOSE",
                    value=float(paired_fraction),
                    target=self.THRESHOLDS["full_paired_fraction"],
                    affected_modules=("5UTR", "CDS", "3UTR"),
                    evidence=(
                        f"Full-length paired fraction={float(paired_fraction):.2%} "
                        f"< threshold={self.THRESHOLDS['full_paired_fraction']:.2%}"
                    ),
                )
            )

        # 2. Junction 5'UTR-CDS: check for OVER-stability and buried start codon
        j1_mfe = metrics.get("junction_5utr_cds_mfe")
        if j1_mfe is not None and float(j1_mfe) < -20.0:
            # 5'UTR-CDS junction too stable → may impede ribosome scanning
            issues.append(
                Issue(
                    issue_type="JUNCTION_5UTR_CDS_TOO_STABLE",
                    value=float(j1_mfe),
                    target=-20.0,
                    affected_modules=("5UTR", "CDS"),
                    evidence=(
                        f"Junction 5'UTR-CDS MFE={j1_mfe:.2f} kcal/mol "
                        f"< -20.0 (overly stable; may block ribosome scanning)"
                    ),
                )
            )

        # 2b. Check if AUG start codon is buried in structure
        aug_buried = metrics.get("junction_5utr_cds_aug_buried")
        if aug_buried:
            aug_pos = metrics.get("junction_5utr_cds_aug_position", -1)
            issues.append(
                Issue(
                    issue_type="JUNCTION_5UTR_CDS_AUG_BURIED",
                    value=1.0,
                    target=0.0,
                    affected_modules=("5UTR", "CDS"),
                    evidence=(
                        f"AUG start codon at junction position {aug_pos} "
                        f"is buried in secondary structure"
                    ),
                )
            )

        # 2c. Check if Kozak region is buried in structure
        kozak_buried = metrics.get("junction_5utr_cds_kozak_buried")
        if kozak_buried:
            kozak_start = metrics.get("junction_5utr_cds_kozak_position_start", -1)
            issues.append(
                Issue(
                    issue_type="JUNCTION_5UTR_CDS_KOZAK_BURIED",
                    value=1.0,
                    target=0.0,
                    affected_modules=("5UTR", "CDS"),
                    evidence=(
                        f"Kozak region (around junction position {kozak_start}) "
                        f"is buried in secondary structure"
                    ),
                )
            )

        # 3. Junction CDS-3'UTR stability
        j2_mfe = metrics.get("junction_cds_3utr_mfe")
        if j2_mfe is not None and float(j2_mfe) > self.THRESHOLDS["junction_cds_3utr_mfe"]:
            issues.append(
                Issue(
                    issue_type="JUNCTION_CDS_3UTR_UNSTABLE",
                    value=float(j2_mfe),
                    target=self.THRESHOLDS["junction_cds_3utr_mfe"],
                    affected_modules=("CDS", "3UTR"),
                    evidence=(
                        f"Junction CDS-3'UTR MFE={j2_mfe:.2f} kcal/mol "
                        f"> threshold={self.THRESHOLDS['junction_cds_3utr_mfe']:.2f}"
                    ),
                )
            )

        # 4. Junction CDS-3'UTR GC mismatch
        j2_gc_diff = metrics.get("junction_cds_3utr_gc_diff")
        if (
            j2_gc_diff is not None
            and float(j2_gc_diff) > self.THRESHOLDS["junction_gc_diff"]
        ):
            j2_left_gc = metrics.get("junction_cds_3utr_left_gc", 0.0)
            j2_right_gc = metrics.get("junction_cds_3utr_right_gc", 0.0)
            issues.append(
                Issue(
                    issue_type="JUNCTION_CDS_3UTR_GC_MISMATCH",
                    value=float(j2_gc_diff),
                    target=self.THRESHOLDS["junction_gc_diff"],
                    affected_modules=("CDS", "3UTR"),
                    evidence=(
                        f"Junction CDS-3'UTR GC diff={j2_gc_diff:.3f} "
                        f"(CDS-side={j2_left_gc:.3f}, 3UTR-side={j2_right_gc:.3f}) "
                        f"> threshold={self.THRESHOLDS['junction_gc_diff']:.3f}"
                    ),
                )
            )

        # 5. Junction 5'UTR-CDS GC mismatch (secondary)
        j1_gc_diff = metrics.get("junction_5utr_cds_gc_diff")
        if (
            j1_gc_diff is not None
            and float(j1_gc_diff) > self.THRESHOLDS["junction_gc_diff"]
        ):
            j1_left_gc = metrics.get("junction_5utr_cds_left_gc", 0.0)
            j1_right_gc = metrics.get("junction_5utr_cds_right_gc", 0.0)
            issues.append(
                Issue(
                    issue_type="JUNCTION_5UTR_CDS_GC_MISMATCH",
                    value=float(j1_gc_diff),
                    target=self.THRESHOLDS["junction_gc_diff"],
                    affected_modules=("5UTR", "CDS"),
                    evidence=(
                        f"Junction 5'UTR-CDS GC diff={j1_gc_diff:.3f} "
                        f"(5UTR-side={j1_left_gc:.3f}, CDS-side={j1_right_gc:.3f}) "
                        f"> threshold={self.THRESHOLDS['junction_gc_diff']:.3f}"
                    ),
                )
            )

        return issues

    # ── Feedback broadcast ───────────────────────────────────────────────────

    def broadcast_feedback(self, issues: list[Issue]) -> dict[str, ModuleFeedback]:
        """Map diagnosed issues to module-specific parameter adjustments."""
        feedback: dict[str, ModuleFeedback] = {}

        for issue in issues:
            if "CDS" in issue.affected_modules:
                fb = feedback.get("CDS", ModuleFeedback(priority="medium"))
                fb.adjustments.extend(self._cds_adjustments(issue))
                fb.priority = self._higher_priority(fb.priority, "medium")
                feedback["CDS"] = fb

            if "5UTR" in issue.affected_modules:
                fb = feedback.get("5UTR", ModuleFeedback(priority="medium"))
                fb.adjustments.extend(self._5utr_adjustments(issue))
                fb.priority = self._higher_priority(fb.priority, "medium")
                feedback["5UTR"] = fb

            if "3UTR" in issue.affected_modules:
                fb = feedback.get("3UTR", ModuleFeedback(priority="medium"))
                fb.adjustments.extend(self._3utr_adjustments(issue))
                fb.priority = self._higher_priority(fb.priority, "medium")
                feedback["3UTR"] = fb

        return feedback

    @staticmethod
    def _higher_priority(a: str, b: str) -> str:
        order = {"low": 0, "medium": 1, "high": 2}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    # ── Per-module adjustment rules ──────────────────────────────────────────

    def _cds_adjustments(self, issue: Issue) -> list[ParamAdjustment]:
        """CDS module adjustments based on issue type.

        Physics reminder: LinearDesign λ is inversely related to MFE stability.
        Lower λ → more negative MFE (more stable structure).
        """
        if issue.issue_type == "FULL_MFE_TOO_HIGH":
            return [
                ParamAdjustment(
                    param="lambda_value",
                    delta=-2.0,
                    reason="Decrease LinearDesign λ to favor MFE (more negative) over CAI",
                )
            ]
        if issue.issue_type == "FULL_STRUCTURE_TOO_LOOSE":
            return [
                ParamAdjustment(
                    param="lambda_value",
                    delta=-2.0,
                    reason="Decrease λ to increase base-pairing and structural stability",
                )
            ]
        # Note: pure junction issues no longer trigger lambda adjustments.
        # Lambda is a global CDS parameter; its effect on a 40-nt junction
        # (only 20 nt from the CDS side) is heavily diluted.  Local junction
        # problems are addressed more effectively by:
        #   1. UTR preset exploration (changes the UTR side of the junction)
        #   2. Junction codon shuffling (synonymous substitution at the CDS
        #      terminus, changing the CDS side of the junction directly)
        # These two local controls are fused in _regenerate_modules().
        if issue.issue_type in (
            "JUNCTION_5UTR_CDS_TOO_STABLE",
            "JUNCTION_5UTR_CDS_AUG_BURIED",
            "JUNCTION_5UTR_CDS_KOZAK_BURIED",
            "JUNCTION_CDS_3UTR_UNSTABLE",
        ):
            return []
        # GC mismatch issues are diagnosed but have no actionable automated
        # adjustment in the current architecture (gc_window / terminal_gc_target
        # are not exposed on the input models).  They are recorded in the BMC
        # trace for human review.
        return []

    def _5utr_adjustments(self, issue: Issue) -> list[ParamAdjustment]:
        """5'UTR module adjustments based on issue type.

        Note: The actual UTR sequence is controlled by GEMORNA presets
        (short/medium/long), not by a numeric length parameter.  The
        coordinator therefore emits a ``utr_preset_exploration`` marker
        instead of a fictitious length delta.
        """
        if issue.issue_type in (
            "JUNCTION_5UTR_CDS_TOO_STABLE",
            "JUNCTION_5UTR_CDS_AUG_BURIED",
            "JUNCTION_5UTR_CDS_KOZAK_BURIED",
        ):
            return [
                ParamAdjustment(
                    param="utr_preset_exploration",
                    delta=0.0,
                    reason="Explore alternative 5'UTR presets to change junction sequence context",
                )
            ]
        return []

    def _3utr_adjustments(self, issue: Issue) -> list[ParamAdjustment]:
        """3'UTR module adjustments based on issue type.

        Note: The actual UTR sequence is controlled by GEMORNA presets
        (short/medium/long), not by a numeric length parameter.
        """
        if issue.issue_type == "JUNCTION_CDS_3UTR_UNSTABLE":
            return [
                ParamAdjustment(
                    param="utr_preset_exploration",
                    delta=0.0,
                    reason="Explore alternative 3'UTR presets to change junction sequence context",
                )
            ]
        return []

    # ── Convergence helpers ──────────────────────────────────────────────────

    @staticmethod
    def has_converged(
        current_best: float,
        previous_best: float,
        round_num: int,
        max_rounds: int = 3,
        improvement_threshold: float = 1.0,
    ) -> tuple[bool, str]:
        """Return (should_stop, reason).

        Hard stop conditions:
        - round_num >= max_rounds
        - score did not improve by at least improvement_threshold
        - score degraded
        """
        if round_num >= max_rounds:
            return True, f"max_rounds_reached ({max_rounds})"
        improvement = current_best - previous_best
        if improvement < 0:
            return True, f"score_degraded ({improvement:.3f})"
        if improvement < improvement_threshold:
            return True, f"insufficient_improvement ({improvement:.3f} < {improvement_threshold})"
        return False, f"improved ({improvement:.3f})"


# ─────────────────────────────────────────────────────────────────────────────
# Aptamer Coordinator
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AptamerCoordinationRound:
    """Trace record for one aptamer BMC iteration round."""

    round_num: int
    best_candidate_id: str
    best_total_score: float
    issues_found: list[Issue]
    feedback_dispatched: dict[str, ModuleFeedback]
    modules_reinvoked: list[str]
    time_elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_num": self.round_num,
            "best_candidate_id": self.best_candidate_id,
            "best_total_score": self.best_total_score,
            "issues_found": [i.to_dict() for i in self.issues_found],
            "feedback_dispatched": {
                k: v.to_dict() for k, v in self.feedback_dispatched.items()
            },
            "modules_reinvoked": self.modules_reinvoked,
            "time_elapsed_ms": self.time_elapsed_ms,
        }


class AptamerCoordinator:
    """Deterministic coordinator for RNA aptamer design module conflict diagnosis.

    Thresholds are chosen based on aptamer domain heuristics:
    - egarps_native_probability: ≥ 0.30 (predicted binding affinity)
    - rhofold_mean_plddt: ≥ 70.0 (RNA monomer foldability confidence)
    - proteinx_ipTM: ≥ 0.60 (AlphaFold-family complex confidence)
    - interface_contacts: ≥ 5 (atomic contacts at binding interface)
    - buried_sasa: ≥ 500.0 Å² (buried solvent-accessible surface area)
    - gc_content: 30–70% (synthesis-friendly range)
    """

    THRESHOLDS: dict[str, float] = {
        "egarps_native_probability": 0.30,
        "rhofold_mean_plddt": 70.0,
        "proteinx_ipTM": 0.60,
        "interface_contacts": 5.0,
        "buried_sasa": 500.0,
        "gc_content_min": 0.30,
        "gc_content_max": 0.70,
    }

    # ── Diagnosis ────────────────────────────────────────────────────────────

    def diagnose(self, metrics: dict[str, Any]) -> list[Issue]:
        """Scan metrics for inter-module conflicts and return structured issues."""
        issues: list[Issue] = []

        # 1. Binding affinity (EGARPS)
        egarps = metrics.get("egarps_native_probability")
        if egarps is not None and float(egarps) < self.THRESHOLDS["egarps_native_probability"]:
            issues.append(
                Issue(
                    issue_type="BINDING_AFFINITY_LOW",
                    value=float(egarps),
                    target=self.THRESHOLDS["egarps_native_probability"],
                    affected_modules=("Target", "Aptamer"),
                    evidence=(
                        f"EGARPS native_probability={float(egarps):.4f} "
                        f"< threshold={self.THRESHOLDS['egarps_native_probability']:.4f}"
                    ),
                )
            )

        # 2. RNA foldability (RhoFold pLDDT)
        plddt = metrics.get("rhofold_mean_plddt")
        if plddt is not None and float(plddt) < self.THRESHOLDS["rhofold_mean_plddt"]:
            issues.append(
                Issue(
                    issue_type="RNA_FOLDABILITY_LOW",
                    value=float(plddt),
                    target=self.THRESHOLDS["rhofold_mean_plddt"],
                    affected_modules=("Aptamer",),
                    evidence=(
                        f"RhoFold mean pLDDT={float(plddt):.2f} "
                        f"< threshold={self.THRESHOLDS['rhofold_mean_plddt']:.2f}"
                    ),
                )
            )

        # 3. Complex confidence (ProteinX ipTM)
        iptm = metrics.get("proteinx_ipTM")
        if iptm is not None and float(iptm) < self.THRESHOLDS["proteinx_ipTM"]:
            issues.append(
                Issue(
                    issue_type="COMPLEX_CONFIDENCE_LOW",
                    value=float(iptm),
                    target=self.THRESHOLDS["proteinx_ipTM"],
                    affected_modules=("Target", "Aptamer"),
                    evidence=(
                        f"ProteinX ipTM={float(iptm):.4f} "
                        f"< threshold={self.THRESHOLDS['proteinx_ipTM']:.4f}"
                    ),
                )
            )

        # 4. Interface strength (contacts or buried SASA)
        contacts = metrics.get("interface_contacts")
        bsasa_raw = metrics.get("buried_sasa")
        bsasa = float(bsasa_raw) if bsasa_raw is not None else None
        if contacts is not None and float(contacts) < self.THRESHOLDS["interface_contacts"]:
            bsasa_str = f"{bsasa:.1f}" if bsasa is not None else "N/A"
            issues.append(
                Issue(
                    issue_type="INTERFACE_TOO_WEAK",
                    value=float(contacts),
                    target=self.THRESHOLDS["interface_contacts"],
                    affected_modules=("Target", "Aptamer"),
                    evidence=(
                        f"Interface contacts={float(contacts):.0f} "
                        f"< threshold={self.THRESHOLDS['interface_contacts']:.0f} "
                        f"(buried SASA={bsasa_str})"
                    ),
                )
            )
        elif bsasa is not None and bsasa < self.THRESHOLDS["buried_sasa"]:
            # Secondary check: even if contacts are OK, very low buried SASA is suspicious
            contacts_str = f"{float(contacts):.0f}" if contacts is not None else "N/A"
            issues.append(
                Issue(
                    issue_type="INTERFACE_TOO_WEAK",
                    value=bsasa,
                    target=self.THRESHOLDS["buried_sasa"],
                    affected_modules=("Target", "Aptamer"),
                    evidence=(
                        f"Buried SASA={bsasa:.1f} "
                        f"< threshold={self.THRESHOLDS['buried_sasa']:.1f} "
                        f"(contacts={contacts_str})"
                    ),
                )
            )

        # 5. GC content extremes
        gc = metrics.get("gc_content")
        if gc is not None:
            if float(gc) < self.THRESHOLDS["gc_content_min"]:
                issues.append(
                    Issue(
                        issue_type="EXTREME_GC_CONTENT",
                        value=float(gc),
                        target=self.THRESHOLDS["gc_content_min"],
                        affected_modules=("Aptamer",),
                        evidence=(
                            f"GC content={float(gc):.3f} "
                            f"< minimum={self.THRESHOLDS['gc_content_min']:.3f}"
                        ),
                    )
                )
            elif float(gc) > self.THRESHOLDS["gc_content_max"]:
                issues.append(
                    Issue(
                        issue_type="EXTREME_GC_CONTENT",
                        value=float(gc),
                        target=self.THRESHOLDS["gc_content_max"],
                        affected_modules=("Aptamer",),
                        evidence=(
                            f"GC content={float(gc):.3f} "
                            f"> maximum={self.THRESHOLDS['gc_content_max']:.3f}"
                        ),
                    )
                )

        return issues

    # ── Feedback broadcast ───────────────────────────────────────────────────

    def broadcast_feedback(self, issues: list[Issue]) -> dict[str, ModuleFeedback]:
        """Map diagnosed issues to module-specific parameter adjustments."""
        feedback: dict[str, ModuleFeedback] = {}

        for issue in issues:
            if "Target" in issue.affected_modules:
                fb = feedback.get("Target", ModuleFeedback(priority="medium"))
                fb.adjustments.extend(self._target_adjustments(issue))
                fb.priority = self._higher_priority(fb.priority, "medium")
                feedback["Target"] = fb
            if "Aptamer" in issue.affected_modules:
                fb = feedback.get("Aptamer", ModuleFeedback(priority="medium"))
                fb.adjustments.extend(self._aptamer_adjustments(issue))
                fb.priority = self._higher_priority(fb.priority, "medium")
                feedback["Aptamer"] = fb

        return feedback

    @staticmethod
    def _higher_priority(a: str, b: str) -> str:
        order = {"low": 0, "medium": 1, "high": 2}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    # ── Per-module adjustment rules ──────────────────────────────────────────

    def _target_adjustments(self, issue: Issue) -> list[ParamAdjustment]:
        """Target (hotspot) module adjustments based on issue type."""
        if issue.issue_type in (
            "BINDING_AFFINITY_LOW",
            "COMPLEX_CONFIDENCE_LOW",
            "INTERFACE_TOO_WEAK",
        ):
            return [
                ParamAdjustment(
                    param="hotspot_expansion",
                    delta=2.0,
                    reason="Expand hotspot window to explore larger binding surface",
                )
            ]
        return []

    def _aptamer_adjustments(self, issue: Issue) -> list[ParamAdjustment]:
        """Aptamer generation module adjustments based on issue type."""
        if issue.issue_type == "RNA_FOLDABILITY_LOW":
            return [
                ParamAdjustment(
                    param="aptamer_length_delta",
                    delta=5.0,
                    reason="Increase aptamer length to improve foldability",
                ),
                ParamAdjustment(
                    param="seed_change",
                    delta=0.0,
                    reason="Change random seeds to explore different sequence space",
                ),
            ]
        if issue.issue_type in (
            "BINDING_AFFINITY_LOW",
            "COMPLEX_CONFIDENCE_LOW",
            "INTERFACE_TOO_WEAK",
        ):
            return [
                ParamAdjustment(
                    param="n_samples_delta",
                    delta=5.0,
                    reason="Generate more candidates for diversity",
                ),
                ParamAdjustment(
                    param="seed_change",
                    delta=0.0,
                    reason="Change random seeds to explore different sequence space",
                ),
            ]
        if issue.issue_type == "EXTREME_GC_CONTENT":
            return [
                ParamAdjustment(
                    param="seed_change",
                    delta=0.0,
                    reason="Change random seeds to find better GC balance",
                ),
            ]
        return []

    # ── Convergence helpers ──────────────────────────────────────────────────

    @staticmethod
    def has_converged(
        current_best: float,
        previous_best: float,
        round_num: int,
        max_rounds: int = 3,
        improvement_threshold: float = 1.0,
    ) -> tuple[bool, str]:
        """Return (should_stop, reason).

        Hard stop conditions:
        - round_num >= max_rounds
        - score did not improve by at least improvement_threshold
        - score degraded
        """
        if round_num >= max_rounds:
            return True, f"max_rounds_reached ({max_rounds})"
        improvement = current_best - previous_best
        if improvement < 0:
            return True, f"score_degraded ({improvement:.3f})"
        if improvement < improvement_threshold:
            return True, f"insufficient_improvement ({improvement:.3f} < {improvement_threshold})"
        return False, f"improved ({improvement:.3f})"
