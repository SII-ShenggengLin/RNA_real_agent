"""Deterministic router for RNA workflow requests.

This module provides ``DeterministicRouter``, which uses keyword/regex matching
to route common user requests directly to the appropriate workflow without
invoking an LLM.  Only requests that fail deterministic matching fall through
to ``LLMPlanner``.

Coverage target: ≥ 60 % of common requests should match deterministically.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from agent_core.planning.base import ExecutionPlan, PlanStep

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _RouteRule:
    """One deterministic routing rule."""

    workflow: str
    # Ordered list of keyword groups.  A group matches if ANY of its patterns
    # is found in the request (case-insensitive).  The rule matches only when
    # ALL groups match (AND across groups, OR inside a group).
    keyword_groups: tuple[tuple[str, ...], ...]
    # Optional negative patterns — if any match, the rule is rejected.
    negative_patterns: tuple[str, ...] = ()
    # Human-readable description for logging
    description: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Keyword routing table — ordered from most-specific to least-specific.
# ──────────────────────────────────────────────────────────────────────────────

_ROUTE_RULES: list[_RouteRule] = [
    # 1. Full-length mRNA (very specific — must come before plain mRNA CDS)
    _RouteRule(
        workflow="full_length_mrna_design",
        keyword_groups=(
            ("full-length", "full length", "complete mRNA", "5'utr", "3'utr",
             "five prime utr", "three prime utr", "utr design",
             "five prime", "three prime"),
            ("mRNA", "mrna", "protein", "utr"),
        ),
        negative_patterns=("cds only", "just cds", "only the cds"),
        description="Full-length mRNA with UTRs",
    ),
    # 2. mRNA CDS design
    _RouteRule(
        workflow="mrna_cds_design",
        keyword_groups=(
            ("mRNA CDS", "mrna cds", "CDS design", "cds design",
             "codon optimization", "codon optimise", "codon optimize",
             "codons", "protein sequence", "cds"),
        ),
        negative_patterns=("full-length", "full length", "5'utr", "3'utr", "utr",
                           "score", "evaluate", "metrics"),
        description="mRNA CDS from protein sequence",
    ),
    # 3. siRNA design
    _RouteRule(
        workflow="sirna_design",
        keyword_groups=(
            ("siRNA", "si-RNA", "sirna", "small interfering RNA",
             "gene silencing", "knockdown"),
        ),
        description="siRNA candidate design",
    ),
    # 4. sgRNA / CRISPR design
    _RouteRule(
        workflow="sgrna_design",
        keyword_groups=(
            ("sgRNA", "sg-RNA", "sgrna", "CRISPR", "crispr",
             "guide RNA", "guide rna", "Cas9", "cas9", "Cas13", "cas13"),
        ),
        description="sgRNA handle design via CRGPT",
    ),
    # 5. RNA aptamer design
    _RouteRule(
        workflow="rna_aptamer_design",
        keyword_groups=(
            ("aptamer", "RNA aptamer", "rna aptamer",
             "protein binding RNA", "target protein"),
        ),
        description="RNA aptamer against protein target",
    ),
    # 6. RNA secondary structure design
    _RouteRule(
        workflow="rna_secondary_structure_design",
        keyword_groups=(
            ("secondary structure", "2D structure", "dot-bracket",
             "dot bracket", "RNAinverse", "rnainverse", "inverse folding",
             "target structure"),
        ),
        negative_patterns=("tertiary", "3D structure", "3d structure", "pdb"),
        description="Design RNA for target secondary structure",
    ),
    # 7. RNA tertiary structure design
    _RouteRule(
        workflow="rna_tertiary_structure_design",
        keyword_groups=(
            ("tertiary structure", "3D structure", "3d structure", "3D RNA",
             "RhoDesign", "rhodesign", "RiboDiffusion", "ribodiffusion",
             "PDB structure", "pdb structure", "inverse fold 3D"),
        ),
        description="Design RNA from 3D structure",
    ),
    # 8. ASO target screening
    _RouteRule(
        workflow="aso_target_screening",
        keyword_groups=(
            ("ASO", "aso", "antisense oligonucleotide", "antisense",
             "RNAplfold", "target accessibility", "binding site"),
        ),
        description="ASO binding site screening",
    ),
    # 9. IRES prediction
    _RouteRule(
        workflow="ires_prediction",
        keyword_groups=(
            ("IRES", "ires", "internal ribosome entry site",
             "ribosome entry", "IRESfinder"),
        ),
        description="IRES element prediction",
    ),
    # 10. mRNA sequence scoring
    _RouteRule(
        workflow="mrna_sequence_scoring",
        keyword_groups=(
            ("score mRNA", "score mrna", "mRNA scoring", "mrna scoring",
             "evaluate mRNA", "evaluate mrna", "mRNA metrics", "mrna metrics",
             "score my mRNA", "score my mrna"),
        ),
        negative_patterns=("design", "generate", "create"),
        description="Score existing mRNA sequences",
    ),
    # 11. RNA-small molecule interaction
    _RouteRule(
        workflow="rna_small_molecule_interaction",
        keyword_groups=(
            ("RNA-small molecule", "rna-small molecule", "RNA ligand",
             "rna ligand", "RNA-ligand", "rna-ligand", "SMILES", "smiles",
             "GerNA-Bind", "gernabind", "RNAsmol", "rnasmol"),
        ),
        description="RNA-small molecule interaction prediction",
    ),
]

# Fallback: plain "mRNA" or "protein" without UTR keywords → CDS design
_MRNA_CDS_FALLBACK_KEYWORDS = ("mRNA", "mrna", "protein sequence", "protein coding")
_MRNA_CDS_FALLBACK_NEGATIVE = ("full-length", "full length", "5'utr", "3'utr", "utr",
                                 "siRNA", "sirna", "sgRNA", "sgrna", "aptamer",
                                 "secondary structure", "tertiary structure", "ASO",
                                 "score", "evaluate", "metrics")


class DeterministicRouter:
    """Fast keyword-based router that skips LLM calls for common requests.

    Usage::

        router = DeterministicRouter()
        plan = router.route("Design siRNA for gene XYZ")
        if plan is not None:
            # matched deterministically
            ...
        else:
            # fallback to LLMPlanner
            ...
    """

    def __init__(self) -> None:
        # Pre-compile regexes for speed
        self._compiled: list[tuple[_RouteRule, list[list[re.Pattern]]]] = []
        for rule in _ROUTE_RULES:
            compiled_groups = [
                [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in group]
                for group in rule.keyword_groups
            ]
            self._compiled.append((rule, compiled_groups))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, user_text: str) -> Optional[ExecutionPlan]:
        """Try to match *user_text* against the keyword table.

        Returns:
            An ``ExecutionPlan`` with a single workflow step if matched,
            or ``None`` if no deterministic match.
        """
        text_lower = user_text.lower()

        for rule, compiled_groups in self._compiled:
            if self._match_rule(text_lower, rule, compiled_groups):
                plan = self._build_single_step_plan(rule.workflow, user_text)
                if plan is not None:
                    _LOGGER.info(
                        "DeterministicRouter matched '%s' → %s (%s)",
                        user_text[:60],
                        rule.workflow,
                        rule.description,
                    )
                    return plan
                # Matched but couldn't extract required params — keep searching
                _LOGGER.debug(
                    "DeterministicRouter matched '%s' → %s but could not extract params",
                    user_text[:60],
                    rule.workflow,
                )

        # Fallback heuristic: plain mRNA / protein → CDS design
        if self._match_fallback(text_lower):
            _LOGGER.info(
                "DeterministicRouter fallback matched '%s' → mrna_cds_design",
                user_text[:60],
            )
            return self._build_single_step_plan("mrna_cds_design", user_text)

        _LOGGER.debug("DeterministicRouter: no match for '%s'", user_text[:60])
        return None

    def match_workflow(self, user_text: str) -> Optional[str]:
        """Return just the workflow name (or None) without building a plan."""
        text_lower = user_text.lower()
        for rule, compiled_groups in self._compiled:
            if self._match_rule(text_lower, rule, compiled_groups):
                return rule.workflow
        if self._match_fallback(text_lower):
            return "mrna_cds_design"
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _match_rule(
        text_lower: str,
        rule: _RouteRule,
        compiled_groups: list[list[re.Pattern]],
    ) -> bool:
        """Check if all keyword groups match and no negative pattern matches."""
        # Negative check first (fast rejection)
        for neg in rule.negative_patterns:
            if neg.lower() in text_lower:
                return False

        # All groups must have at least one match
        for group in compiled_groups:
            matched = False
            for p in group:
                if p.search(text_lower):
                    matched = True
                    break
                # Fallback for multi-word keywords: if all constituent words
                # appear (in any order), treat it as a match.
                # re.escape() may escape spaces as "\ " — normalise first.
                pattern_str = (
                    p.pattern.replace(r"\b", "").replace(r"\ ", " ").lower()
                )
                if " " in pattern_str and all(
                    word in text_lower for word in pattern_str.split()
                ):
                    matched = True
                    break
            if not matched:
                return False
        return True

    @staticmethod
    def _match_fallback(text_lower: str) -> bool:
        """Plain mRNA / protein request without other domain keywords."""
        # Check positive keywords
        has_positive = any(kw.lower() in text_lower for kw in _MRNA_CDS_FALLBACK_KEYWORDS)
        if not has_positive:
            return False
        # Check negatives
        for neg in _MRNA_CDS_FALLBACK_NEGATIVE:
            if neg.lower() in text_lower:
                return False
        return True

    @staticmethod
    def _build_single_step_plan(workflow: str, user_text: str) -> Optional[ExecutionPlan]:
        """Build a minimal ExecutionPlan for a single workflow invocation.

        For workflows that require mandatory parameters from the user text,
        this method attempts to extract them.  If extraction fails it returns
        ``None`` so the caller can fall back to an LLM planner.
        """
        input_binding: dict[str, Any] = {}

        if workflow == "rna_secondary_structure_design":
            candidate = _extract_dot_bracket(user_text)
            if candidate is None:
                return None
            input_binding["target_structure"] = candidate

        elif workflow == "rna_tertiary_structure_design":
            pdb_path = _extract_pdb_path(user_text)
            if pdb_path is None:
                return None
            input_binding["structure_filepath"] = pdb_path

        # Other workflows: rely on LLM planner or state references for params.

        return ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step_1",
                    type="workflow",
                    target=workflow,
                    input_binding=input_binding,
                    output_key="workflow_result",
                    description=f"Deterministic routing: {workflow}",
                )
            ],
            max_retries=2,
            fallback_on_error="retry_with_alternative",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Parameter extraction helpers
# ──────────────────────────────────────────────────────────────────────────────


def _extract_dot_bracket(text: str) -> Optional[str]:
    """Try to extract a dot-bracket RNA secondary structure from free-form text.

    Returns the first candidate that:
      - contains only ``(``, ``)``, ``.`` and whitespace
      - has balanced parentheses
      - contains at least one base-pair
    """
    for match in re.finditer(r"[()\.\s]{3,}", text):
        candidate = re.sub(r"\s+", "", match.group(0))
        if not candidate:
            continue
        if not set(candidate).issubset({"(", ")", "."}):
            continue
        if candidate.count("(") != candidate.count(")"):
            continue
        if "(" not in candidate:
            continue
        return candidate
    return None


def _extract_pdb_path(text: str) -> Optional[str]:
    """Try to extract a PDB file path from free-form text."""
    match = re.search(r"\S+\.pdb\b", text, re.IGNORECASE)
    if match:
        return match.group(0)
    return None
