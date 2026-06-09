"""End-to-end mock test for BMC full-length mRNA design workflow.

Uses a mock CapabilityRegistry so that no external microservices are required.
Validates the complete BMC loop: generate → evaluate → diagnose → regenerate → re-rank.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.workflow_models import Candidate
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignInput,
    FullLengthMrnaDesignWorkflow,
)


class _FakeCapResult:
    """Minimal fake capability result."""

    def __init__(self, output: dict | None = None, success: bool = True, error: str = ""):
        self.output = output or {}
        self.success = success
        self.error = error


def _make_mock_registry() -> CapabilityRegistry:
    """Build a registry where every capability returns plausible fake data."""
    registry = MagicMock(spec=CapabilityRegistry)
    _call_count = 0

    def _fake_invoke(args: dict, state: dict | None = None) -> _FakeCapResult:
        nonlocal _call_count
        _call_count += 1
        # Use call count to generate slightly different sequences so that
        # deduplication does not swallow BMC-regenerated candidates.
        suffix = "ACGT"[_call_count % 4]
        return _FakeCapResult(
            output={
                # CDS design
                "cds_sequence": ("ATG" * 99) + f"AT{suffix}",
                "generated_sequence": ("ATG" * 99) + f"AT{suffix}",
                # UTR design
                "utr5_sequence": ("GGG" * 19) + f"GG{suffix}",
                "utr3_sequence": ("CCC" * 19) + f"CC{suffix}",
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

        # Patch junction evaluator to force a BMC iteration by returning
        # an over-stable 5'UTR-CDS junction that impedes ribosome scanning.
        with patch.object(
            wf._junction_evaluator,
            "evaluate",
            return_value={
                "junction_5utr_cds_mfe": -25.0,  # below -20 → triggers TOO_STABLE
                "junction_5utr_cds_gc_diff": 0.05,
                "junction_cds_3utr_mfe": -8.0,
                "junction_cds_3utr_gc_diff": 0.10,
            },
        ):
            result = wf.run(inp)

        assert result.success is True
        assert result.best_candidate is not None
        assert len(result.all_candidates) > 0
        # BMC trace should be recorded in workflow state
        assert hasattr(wf, "_bmc_trace")
        # Since junction is over-stable, at least one round of BMC should execute
        assert len(wf._bmc_trace) >= 1
        # First round should have diagnosed the junction issue
        first_round = wf._bmc_trace[0]
        assert first_round.round_num == 1
        assert any(
            i.issue_type == "JUNCTION_5UTR_CDS_TOO_STABLE"
            for i in first_round.issues_found
        )

    def test_bmc_run_no_issues_no_extra_rounds(self):
        """If all metrics pass thresholds, BMC should not trigger extra rounds."""
        registry = _make_mock_registry()
        wf = FullLengthMrnaDesignWorkflow(registry)

        inp = FullLengthMrnaDesignInput(
            protein_sequence="M" * 100,
            design_tool="all",
            utr_mode="short",
            run_fold=True,
            run_gc=True,
        )

        # Patch the full workflow evaluate() to return metrics that all pass
        # coordinator thresholds, so no BMC rounds are triggered.
        def _fake_evaluate(candidate):
            return {
                "full_length_mfe": -80.0,  # well below -50 threshold
                "cds_cai": 0.85,
                "cds_mfe": -50.0,
                "cds_gc": 0.52,
                "cds_length": 300,
                "utr5_ires_potential": 0.2,
                "utr5_length": 60,
                "utr3_length": 60,
                "utr5_mfe": -10.0,
                "overall_stability": 0.80,
                "total_length": 420,
                "fold_tool": "ViennaRNA",
                "utr5_predicted_mrl": 8.0,
                "utr3_predicted_stability": 0.70,
                "junction_5utr_cds_mfe": -20.0,
                "junction_5utr_cds_gc_diff": 0.02,
                "junction_cds_3utr_mfe": -18.0,
                "junction_cds_3utr_gc_diff": 0.03,
            }

        with patch.object(wf, "evaluate", _fake_evaluate):
            result = wf.run(inp)

        assert result.success is True
        # No issues → no BMC rounds beyond initial generation
        assert len(wf._bmc_trace) == 0

    def test_bmc_ranking_prefers_bmc_score(self):
        """When BMC scoring is active, ranking should use total_score."""
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
                    "junction_5utr_cds_mfe": -20.0,
                    "junction_cds_3utr_mfe": -20.0,
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
                    "junction_5utr_cds_mfe": -5.0,
                    "junction_cds_3utr_mfe": -5.0,
                    "junction_5utr_cds_gc_diff": 0.20,
                    "junction_cds_3utr_gc_diff": 0.20,
                },
            },
        )

        # Evaluate and score both
        for c in [cand_good, cand_bad]:
            metrics = c.metadata["metrics_bundle"]
            c.scores = wf.score(metrics)

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

        with patch.object(
            wf._junction_evaluator,
            "evaluate",
            return_value={
                "junction_5utr_cds_mfe": -5.0,
                "junction_5utr_cds_gc_diff": 0.05,
                "junction_cds_3utr_mfe": -8.0,
                "junction_cds_3utr_gc_diff": 0.10,
            },
        ):
            result = wf.run(inp)

        state = getattr(result, "_state_writeback", {})
        assert "_bmc_trace" in state
        trace = state["_bmc_trace"]
        assert isinstance(trace, list)
        assert len(trace) > 0
        assert "round_num" in trace[0]
        assert "issues_found" in trace[0]
