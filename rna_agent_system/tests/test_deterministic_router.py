"""Tests for DeterministicRouter.

Covers:
1. Keyword matching for all 11 workflows
2. Negative pattern rejection
3. Fallback heuristic (plain mRNA → CDS)
4. Case insensitivity
5. No match returns None
6. Plan structure correctness
"""

from __future__ import annotations

import pytest

from agent_core.planning.router import DeterministicRouter
from agent_core.planning.base import ExecutionPlan


@pytest.fixture
def router() -> DeterministicRouter:
    return DeterministicRouter()


# ──────────────────────────────────────────────────────────────────────────────
# 1. Workflow keyword matching
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "user_text,expected_workflow",
    [
        # mRNA CDS design
        ("Design mRNA CDS for protein MKLTEST", "mrna_cds_design"),
        ("codon optimization for my protein", "mrna_cds_design"),
        ("Optimize codons for human expression", "mrna_cds_design"),
        ("CDS design from amino acid sequence", "mrna_cds_design"),
        # Full-length mRNA
        ("Design full-length mRNA with UTRs", "full_length_mrna_design"),
        ("complete mRNA from protein sequence", "full_length_mrna_design"),
        ("Design 5'UTR and 3'UTR for mRNA", "full_length_mrna_design"),
        ("five prime utr design for mRNA", "full_length_mrna_design"),
        # siRNA
        ("Design siRNA for gene silencing", "sirna_design"),
        ("si-RNA knockdown of TP53", "sirna_design"),
        ("small interfering RNA design", "sirna_design"),
        # sgRNA / CRISPR
        ("Design sgRNA for CRISPR", "sgrna_design"),
        ("sg-RNA handle using CRGPT", "sgrna_design"),
        ("CRISPR guide RNA design", "sgrna_design"),
        ("Cas9 guide sequence", "sgrna_design"),
        # Aptamer
        ("Design RNA aptamer for protein X", "rna_aptamer_design"),
        ("aptamer against thrombin", "rna_aptamer_design"),
        # Secondary structure
        ("Design RNA for target secondary structure", "rna_secondary_structure_design"),
        ("inverse folding with RNAinverse", "rna_secondary_structure_design"),
        ("dot-bracket structure design", "rna_secondary_structure_design"),
        # Tertiary structure
        ("Design RNA from 3D structure", "rna_tertiary_structure_design"),
        ("tertiary structure inverse folding", "rna_tertiary_structure_design"),
        ("RhoDesign from PDB", "rna_tertiary_structure_design"),
        # ASO
        ("Screen ASO binding sites", "aso_target_screening"),
        ("antisense oligonucleotide target", "aso_target_screening"),
        ("RNAplfold accessibility for ASO", "aso_target_screening"),
        # IRES
        ("Predict IRES elements", "ires_prediction"),
        ("internal ribosome entry site finder", "ires_prediction"),
        # mRNA scoring
        ("Score my mRNA sequences", "mrna_sequence_scoring"),
        ("evaluate mRNA metrics", "mrna_sequence_scoring"),
        # RNA-small molecule
        ("Predict RNA-ligand interaction", "rna_small_molecule_interaction"),
        ("RNA-small molecule binding with SMILES", "rna_small_molecule_interaction"),
        ("GerNA-Bind prediction", "rna_small_molecule_interaction"),
    ],
)
def test_deterministic_routing(router: DeterministicRouter, user_text: str, expected_workflow: str):
    plan = router.route(user_text)
    assert plan is not None, f"Expected match for: {user_text}"
    assert isinstance(plan, ExecutionPlan)
    assert len(plan.steps) == 1
    assert plan.steps[0].type == "workflow"
    assert plan.steps[0].target == expected_workflow


# ──────────────────────────────────────────────────────────────────────────────
# 2. Negative patterns
# ──────────────────────────────────────────────────────────────────────────────


def test_full_length_negative_rejects_cds_only(router: DeterministicRouter):
    """"cds only" should not match full_length_mrna_design."""
    plan = router.route("Design cds only for my protein")
    # Should fallback to mrna_cds_design via the mRNA fallback, not full_length
    assert plan is not None
    assert plan.steps[0].target == "mrna_cds_design"


def test_mrna_cds_negative_rejects_utr(router: DeterministicRouter):
    """mRNA CDS should not match when UTR keywords are present."""
    plan = router.route("Design mRNA with 5'UTR and CDS")
    assert plan is not None
    assert plan.steps[0].target == "full_length_mrna_design"


def test_secondary_structure_negative_rejects_3d(router: DeterministicRouter):
    """Secondary structure should not match when 3D/tertiary keywords present."""
    plan = router.route("Design RNA tertiary structure from PDB")
    assert plan is not None
    assert plan.steps[0].target == "rna_tertiary_structure_design"


# ──────────────────────────────────────────────────────────────────────────────
# 3. Fallback heuristic
# ──────────────────────────────────────────────────────────────────────────────


def test_plain_mrna_fallback_to_cds(router: DeterministicRouter):
    """Plain 'mRNA' or 'protein' without other domain keywords → CDS design."""
    plan = router.route("Design an mRNA for my protein")
    assert plan is not None
    assert plan.steps[0].target == "mrna_cds_design"


def test_protein_sequence_fallback_to_cds(router: DeterministicRouter):
    plan = router.route("I have a protein sequence, make mRNA")
    assert plan is not None
    assert plan.steps[0].target == "mrna_cds_design"


# ──────────────────────────────────────────────────────────────────────────────
# 4. Case insensitivity
# ──────────────────────────────────────────────────────────────────────────────


def test_case_insensitive_matching(router: DeterministicRouter):
    """All workflow keywords should match regardless of case."""
    assert router.route("DESIGN SIRNA FOR GENE") is not None
    assert router.route("design Sirna for gene") is not None
    assert router.route("design sIRNA for gene") is not None


# ──────────────────────────────────────────────────────────────────────────────
# 5. No match returns None
# ──────────────────────────────────────────────────────────────────────────────


def test_no_match_returns_none(router: DeterministicRouter):
    """Ambiguous or unrelated requests should return None."""
    assert router.route("Hello, how are you?") is None
    assert router.route("What is the weather today?") is None
    assert router.route("Tell me a joke") is None


# ──────────────────────────────────────────────────────────────────────────────
# 6. Plan structure
# ──────────────────────────────────────────────────────────────────────────────


def test_plan_has_correct_structure(router: DeterministicRouter):
    plan = router.route("Design siRNA for TP53")
    assert plan is not None
    assert plan.max_retries == 2
    assert plan.fallback_on_error == "retry_with_alternative"
    step = plan.steps[0]
    assert step.step_id == "step_1"
    assert step.output_key == "workflow_result"
    assert "siRNA" in step.description or "sirna" in step.description.lower()


# ──────────────────────────────────────────────────────────────────────────────
# 7. match_workflow API
# ──────────────────────────────────────────────────────────────────────────────


def test_match_workflow_returns_name_only(router: DeterministicRouter):
    assert router.match_workflow("Design siRNA") == "sirna_design"
    assert router.match_workflow("Hello world") is None


# ──────────────────────────────────────────────────────────────────────────────
# 8. Coverage benchmark
# ──────────────────────────────────────────────────────────────────────────────


WORKFLOW_TEST_CASES = [
    # mRNA CDS
    "Design mRNA CDS from protein MKLW",
    "Codon optimize my protein sequence",
    "Make CDS for human expression",
    # Full-length mRNA
    "Design full-length mRNA with UTRs",
    "Build complete mRNA from protein",
    # siRNA
    "Design siRNA for viral knockdown",
    "si-RNA targeting EGFR",
    # sgRNA
    "Design sgRNA for CRISPR editing",
    "CRISPR guide RNA for Cas9",
    # Aptamer
    "RNA aptamer for protein target",
    "Design aptamer against spike protein",
    # Secondary structure
    "Inverse folding for target structure",
    "RNA sequence for dot-bracket pattern",
    # Tertiary structure
    "Design from 3D RNA structure",
    "RiboDiffusion inverse folding",
    # ASO
    "ASO binding site screening",
    "Antisense oligonucleotide design",
    # IRES
    "Find IRES in my sequence",
    "Internal ribosome entry site prediction",
    # Scoring
    "Score these mRNA sequences",
    # Small molecule
    "RNA-SMILES interaction prediction",
]


def test_coverage_benchmark(router: DeterministicRouter):
    """At least 60% of common requests should match deterministically."""
    matched = sum(1 for text in WORKFLOW_TEST_CASES if router.route(text) is not None)
    coverage = matched / len(WORKFLOW_TEST_CASES)
    assert coverage >= 0.60, f"Coverage {coverage:.1%} below 60% target ({matched}/{len(WORKFLOW_TEST_CASES)})"
