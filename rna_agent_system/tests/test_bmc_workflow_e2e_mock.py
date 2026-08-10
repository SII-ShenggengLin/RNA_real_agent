"""End-to-end mock test for reference-point driven BMC full-length mRNA design.

Uses a mock CapabilityRegistry so that no external microservices are required.
Validates the complete BMC loop: generate → evaluate → diagnose → regenerate → re-rank.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.workflow_models import Candidate
from agent_core.workflows.coordinator import Issue, ReferencePointCoordinator
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignInput,
    FullLengthMrnaDesignWorkflow,
)


class _FakeCapResult:
    """Minimal fake capability result."""

    def __init__(self, output: dict | None = None, success: bool = True, error: str = "", elapsed_time: float = 0.0):
        self.output = output or {}
        self.success = success
        self.error = error
        self.elapsed_time = elapsed_time


def _make_mock_registry() -> CapabilityRegistry:
    """Build a registry where every capability returns plausible fake data."""
    registry = MagicMock(spec=CapabilityRegistry)
    _call_count = 0

    def _unique_tag(n: int, length: int = 3) -> str:
        # Per-call unique ACGT tag so BMC-regenerated UTR/CDS combinations
        # never collide with already-seen candidates, regardless of how many
        # capability calls each evaluation path makes.
        chars = "ACGT"
        return "".join(chars[(n // (4**i)) % 4] for i in range(length))

    def _fake_invoke(args: dict, state: dict | None = None) -> _FakeCapResult:
        nonlocal _call_count
        _call_count += 1
        tag = _unique_tag(_call_count)
        return _FakeCapResult(
            output={
                # CDS design
                "cds_sequence": ("ATG" * 99) + tag,
                "generated_sequence": ("ATG" * 99) + tag,
                # UTR design
                "utr5_sequence": ("GGG" * 19) + tag,
                "utr3_sequence": ("CCC" * 19) + tag,
                # Folding
                "mfe_kcal_per_mol": -45.0,
                "structure": "." * 300,
                "fold_tool": "ViennaRNA",
                # CAI
                "cai_score": 0.82,
                "gc_content": 0.52,
                "sequence_length": 300,
                # RNASTOP
                "overall_stability": 0.78,
                # MRL / 3'UTR stability
                "predicted_mrl": 7.5,
                "predicted_stability": 0.65,
                # IRES
                "max_score": 0.3,
            }
        )

    def _has(name: str) -> bool:
        return True

    def _get(name: str):
        cap = MagicMock()
        cap.invoke = _fake_invoke
        return cap

    registry.has = _has
    registry.get = _get
    return registry


class TestBMCEndToEnd:
    def test_bmc_run_produces_trace(self):
        """Full BMC run should produce candidates and a non-empty BMC trace."""
        registry = _make_mock_registry()
        wf = FullLengthMrnaDesignWorkflow(registry)

        inp = FullLengthMrnaDesignInput(
            protein_sequence="M" * 100,  # 100 aa → 300 nt CDS
            design_tool="all",
            utr_mode="short",
            run_fold=True,
            run_gc=True,
        )

        # Force a reference-point gap on the 5'UTR-CDS junction by mocking the
        # coordinator diagnosis.  This keeps the test deterministic and avoids
        # relying on the exact score distribution produced by the mock registry.
        def _force_junction_issue(self, norm_candidate_vector, reference_point, boolean_issues=None):
            return [
                Issue(
                    issue_type="JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE",
                    value=0.3,
                    target=0.8,
                    violation=0.5,
                    affected_modules=("5UTR", "CDS"),
                    evidence="Mock junction gap for testing",
                )
            ]

        with patch.object(ReferencePointCoordinator, "diagnose", _force_junction_issue):
            result = wf.run(inp)

        assert result.success is True
        assert result.best_candidate is not None
        assert len(result.all_candidates) > 0
        # BMC trace should be recorded in workflow state
        assert hasattr(wf, "_bmc_trace")
        # Since a junction gap was diagnosed, at least one round of BMC should execute
        assert len(wf._bmc_trace) >= 1
        # First round should have diagnosed the junction issue
        first_round = wf._bmc_trace[0]
        assert first_round.round_num == 1
        assert any(
            i.issue_type == "JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE"
            for i in first_round.issues_found
        )

    def test_bmc_run_no_issues_no_extra_rounds(self):
        """If no reference-point gaps exist, BMC should not trigger extra rounds."""
        registry = _make_mock_registry()
        wf = FullLengthMrnaDesignWorkflow(registry)

        inp = FullLengthMrnaDesignInput(
            protein_sequence="M" * 100,
            design_tool="all",
            utr_mode="short",
            run_fold=True,
            run_gc=True,
        )

        # Mock coordinator diagnosis to always return no issues.
        with patch.object(ReferencePointCoordinator, "diagnose", return_value=[]):
            result = wf.run(inp)

        assert result.success is True
        # No issues → no BMC rounds beyond initial generation
        assert len(wf._bmc_trace) == 0

    def test_bmc_ranking_prefers_asf_winner(self):
        """When reference-point optimization is active, the best candidate is selected by ASF."""
        registry = _make_mock_registry()
        wf = FullLengthMrnaDesignWorkflow(registry)

        # Create two fake candidates with different junction scores
        cand_good = Candidate(
            sequence="A" * 360,
            sequence_type="mrna",
            source="mock_good",
            metadata={
                "utr5_sequence": "G" * 30,
                "cds_sequence": "A" * 300,
                "utr3_sequence": "C" * 30,
                "metrics_bundle": {
                    "cds_length": 300,
                    "cds_mfe": -50.0,
                    "cds_cai": 0.90,
                    "full_length_mfe": -70.0,
                    "junction_5utr_cds_mfe_per_nt": -0.50,
                    "junction_cds_3utr_mfe_per_nt": -0.50,
                    "junction_5utr_cds_gc_diff": 0.0,
                    "junction_cds_3utr_gc_diff": 0.0,
                },
            },
        )
        cand_bad = Candidate(
            sequence="T" * 360,
            sequence_type="mrna",
            source="mock_bad",
            metadata={
                "utr5_sequence": "G" * 30,
                "cds_sequence": "T" * 300,
                "utr3_sequence": "C" * 30,
                "metrics_bundle": {
                    "cds_length": 300,
                    "cds_mfe": -20.0,
                    "cds_cai": 0.50,
                    "full_length_mfe": -30.0,
                    "junction_5utr_cds_mfe_per_nt": -0.125,
                    "junction_cds_3utr_mfe_per_nt": -0.125,
                    "junction_5utr_cds_gc_diff": 0.20,
                    "junction_cds_3utr_gc_diff": 0.20,
                },
            },
        )

        # Evaluate and score both
        for c in [cand_good, cand_bad]:
            metrics = c.metadata["metrics_bundle"]
            c.scores = wf.score(metrics)

        wf._workflow_state["_full_length_input"] = FullLengthMrnaDesignInput(
            protein_sequence="M" * 100
        )
        result = wf.rank_and_format([cand_bad, cand_good])
        best = result.best_candidate
        assert best is not None
        # Good candidate should win because of much better junction + full MFE
        assert best.source == "mock_good"

    def test_bmc_state_writeback_contains_trace(self):
        """WorkflowResult state writeback should contain BMC trace."""
        registry = _make_mock_registry()
        wf = FullLengthMrnaDesignWorkflow(registry)

        inp = FullLengthMrnaDesignInput(
            protein_sequence="M" * 100,
            design_tool="all",
            utr_mode="short",
        )

        def _force_junction_issue(self, norm_candidate_vector, reference_point, boolean_issues=None):
            return [
                Issue(
                    issue_type="JUNCTION_CDS_3UTR_SCORE_BELOW_REFERENCE",
                    value=0.3,
                    target=0.8,
                    violation=0.5,
                    affected_modules=("CDS", "3UTR"),
                    evidence="Mock junction gap for testing",
                )
            ]

        with patch.object(ReferencePointCoordinator, "diagnose", _force_junction_issue):
            result = wf.run(inp)

        state = getattr(result, "_state_writeback", {})
        assert "_bmc_trace" in state
        trace = state["_bmc_trace"]
        assert isinstance(trace, list)
        assert len(trace) > 0
        assert "round_num" in trace[0]
        assert "issues_found" in trace[0]
