"""Verify that siRNA design workflow populates WorkflowResult.trace with tool calls."""

from agent_core.workflows.sirna_design import SirnaDesignInput, SirnaDesignWorkflow


class FakeCapabilityResult:
    def __init__(self, success=True, output=None, error=None, elapsed_time=0.1):
        self.success = success
        self.output = output or {}
        self.error = error
        self.elapsed_time = elapsed_time


class FakeCapability:
    def __init__(self, name, return_output=None):
        self.tool_name = name
        self._return_output = return_output or {}

    def invoke(self, tool_args, state=None):
        return FakeCapabilityResult(
            success=True,
            output=self._return_output,
            elapsed_time=0.05,
        )


class FakeRegistry:
    """Minimal registry that fakes GC, duplex, and structure evaluators."""

    def __init__(self):
        self._caps = {
            "compute_rna_sequence_gc_content": FakeCapability(
                "compute_rna_sequence_gc_content",
                {"gc_content": 0.45, "sequence_length": 21},
            ),
            "compute_sirna_duplex_binding_vienna": FakeCapability(
                "compute_sirna_duplex_binding_vienna",
                {"mfe_kcal_per_mol": -25.0},
            ),
            "predict_rna_secondary_structure_with_linearfold": FakeCapability(
                "predict_rna_secondary_structure_with_linearfold",
                {"mfe": -10.0, "structure": "...................."},
            ),
            "predict_rna_secondary_structure": FakeCapability(
                "predict_rna_secondary_structure",
                {"mfe_kcal_per_mol": -12.0, "structure": "...................."},
            ),
            "run_blastn_similarity_search": FakeCapability(
                "run_blastn_similarity_search",
                {"hit_count": 0},
            ),
            "run_bowtie2_short_alignment": FakeCapability(
                "run_bowtie2_short_alignment",
                {"hit_count": 0},
            ),
        }

    def has(self, name):
        return name in self._caps

    def get(self, name):
        return self._caps[name]


def test_sirna_generic_trace_populated():
    """Generic siRNA design should record GC, duplex, structure, and off-target calls in trace."""
    import tempfile
    import os

    reg = FakeRegistry()
    wf = SirnaDesignWorkflow(reg)

    # Create a dummy transcriptome file so off-target scan is actually triggered
    with tempfile.NamedTemporaryFile(mode="w", suffix=".fa", delete=False) as f:
        f.write(">dummy\nAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC\n")
        dummy_fa = f.name

    try:
        inp = SirnaDesignInput(
            mode="generic",
            target_sequence="AUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC",
            candidate_count=3,
            off_target_scan=True,
            transcriptome_fasta_path=dummy_fa,
        )

        result = wf.run(inp)

        assert result.success is True
        assert len(result.all_candidates) > 0
        assert len(result.trace) > 0, "WorkflowResult.trace should contain tool call records"

        # Check that each expected tool appears in the trace
        tool_names = {rec.tool_name for rec in result.trace}
        assert "compute_rna_sequence_gc_content" in tool_names
        assert "compute_sirna_duplex_binding_vienna" in tool_names
        assert "predict_rna_secondary_structure_with_linearfold" in tool_names
        # Default alignment tool is bowtie2
        assert "run_bowtie2_short_alignment" in tool_names

        # Verify input_summary contains tool arguments
        for rec in result.trace:
            assert rec.tool_name != ""
            assert rec.input_summary != ""
            # input_summary should be a JSON string with the args
            assert "{" in rec.input_summary or "filepath" in rec.input_summary

        # Verify candidate-level tool_records are also populated
        for cand in result.all_candidates:
            assert len(cand.tool_records) > 0, f"Candidate {cand.id} should have tool_records"
    finally:
        os.unlink(dummy_fa)


def test_sirna_trace_records_metrics_on_success():
    """Successful tool calls should have metrics populated in the trace record."""
    reg = FakeRegistry()
    wf = SirnaDesignWorkflow(reg)

    inp = SirnaDesignInput(
        mode="generic",
        target_sequence="AUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC",
        candidate_count=2,
        off_target_scan=False,
    )

    result = wf.run(inp)
    assert result.success is True

    gc_records = [r for r in result.trace if r.tool_name == "compute_rna_sequence_gc_content"]
    assert len(gc_records) > 0
    for rec in gc_records:
        assert rec.success is True
        assert "gc_content" in rec.metrics or "gc_content" in rec.artifacts


def test_sirna_trace_includes_failed_calls():
    """Failed tool invocations should still be recorded in trace."""

    class FailingGC(FakeCapability):
        def invoke(self, tool_args, state=None):
            return FakeCapabilityResult(success=False, error="simulated failure", elapsed_time=0.01)

    reg = FakeRegistry()
    reg._caps["compute_rna_sequence_gc_content"] = FailingGC("compute_rna_sequence_gc_content")

    wf = SirnaDesignWorkflow(reg)
    inp = SirnaDesignInput(
        mode="generic",
        target_sequence="AUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC",
        candidate_count=2,
        off_target_scan=False,
    )

    result = wf.run(inp)
    assert result.success is True  # workflow degrades gracefully

    failed_records = [r for r in result.trace if r.tool_name == "compute_rna_sequence_gc_content"]
    assert len(failed_records) > 0
    for rec in failed_records:
        assert rec.success is False
        assert rec.error is not None
