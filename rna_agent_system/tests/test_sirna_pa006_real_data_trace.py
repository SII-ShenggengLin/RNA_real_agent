"""Real-data end-to-end trace verification for siRNA design workflow (PA_006).

Uses the actual PA_006 task from RNA-BioBench-ProcessAware with real tools
(ViennaRNA, BLAST+) and verifies that WorkflowResult.trace captures every
tool invocation with full parameters.
"""

import json
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Load PA_006 task from benchmark dataset
# ------------------------------------------------------------------
BENCH_DIR = Path(__file__).resolve().parents[1] / "data" / "benchmarks" / "RNA-BioBench-ProcessAware"
BENCH_JSON = BENCH_DIR / "task_set_for_llm_comparison.json"

with open(BENCH_JSON) as f:
    bench = json.load(f)

pa006 = next(t for t in bench["tasks"] if t["task_id"] == "PA_006")
print(f"Loaded task: {pa006['task_id']} — {pa006['description']}")
print(f"User query: {pa006['user_query'][:120]}...")
print()

# ------------------------------------------------------------------
# Resolve transcriptome for off-target scan
# ------------------------------------------------------------------
# Use a small subset of the full transcriptome for speed during testing
TRANSCRIPTOME = Path("/tmp/small_transcripts.fa")
print(f"Transcriptome: {TRANSCRIPTOME} (exists={TRANSCRIPTOME.exists()})")
print()

# ------------------------------------------------------------------
# Run siRNA design workflow with real tools
# ------------------------------------------------------------------
from agent_core.capabilities.base import CapabilityRegistry
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflows.sirna_design import SirnaDesignInput, SirnaDesignWorkflow


# Extract target sequence from the user query
def _extract_sequence_from_query(query: str) -> str:
    """Pull out the RNA sequence embedded in the query text."""
    import re
    # Look for a long uppercase RNA sequence
    m = re.search(r"[AUGC]{40,}", query)
    if m:
        return m.group(0)
    raise ValueError("No RNA sequence found in query")


target_seq = _extract_sequence_from_query(pa006["user_query"])
print(f"Target sequence length: {len(target_seq)} nt")
print(f"Target: {target_seq}")
print()

executor = ToolExecutor(build_default_tool_registry(include_demo=False))
cap_reg = CapabilityRegistry(executor)
for name in SirnaDesignWorkflow.required_capabilities:
    cap_reg.register(name)

wf = SirnaDesignWorkflow(cap_reg)

inp = SirnaDesignInput(
    mode="generic",
    target_sequence=target_seq,
    candidate_count=3,
    off_target_scan=True,
    transcriptome_fasta_path=str(TRANSCRIPTOME),
    blast_perc_identity=90.0,
)

result = wf.run(inp)

# ------------------------------------------------------------------
# Verify workflow result
# ------------------------------------------------------------------
print("=" * 60)
print("WORKFLOW RESULT")
print("=" * 60)
print(f"Success: {result.success}")
print(f"Task ID: {result.task_id}")
print(f"Candidates: {len(result.all_candidates)}")
print(f"Errors: {result.errors}")
print()

if not result.success:
    print("Workflow failed — cannot verify trace.")
    sys.exit(1)

# ------------------------------------------------------------------
# Verify trace is populated
# ------------------------------------------------------------------
print("=" * 60)
print("TRACE VERIFICATION")
print("=" * 60)

trace = result.trace
print(f"Total trace records: {len(trace)}")
print()

if not trace:
    print("ERROR: WorkflowResult.trace is empty!")
    sys.exit(1)

# Group by tool name
from collections import Counter
tool_counts = Counter(rec.tool_name for rec in trace)
print("Tool call counts:")
for tool_name, count in sorted(tool_counts.items()):
    print(f"  {tool_name}: {count}")
print()

# Verify expected tools are present
EXPECTED_TOOLS = {
    "compute_rna_sequence_gc_content",
    "compute_sirna_duplex_binding_vienna",
    "predict_rna_secondary_structure",  # ViennaRNA fallback
    "run_blastn_similarity_search",
}
found_tools = set(tool_counts.keys())
missing = EXPECTED_TOOLS - found_tools
if missing:
    print(f"WARNING: Expected tools not found in trace: {missing}")
else:
    print("All expected tools found in trace.")
print()

# ------------------------------------------------------------------
# Deep inspection: verify every record has parameters
# ------------------------------------------------------------------
print("=" * 60)
print("PARAMETER CAPTURE VERIFICATION")
print("=" * 60)

all_ok = True
for rec in trace:
    has_input = bool(rec.input_summary and rec.input_summary.strip() != "")
    has_output = bool(rec.output_summary is not None)
    if not has_input:
        print(f"  MISSING input_summary for {rec.tool_name} @ {rec.step_name}")
        all_ok = False
    if rec.success and not has_output:
        print(f"  MISSING output_summary for {rec.tool_name} @ {rec.step_name}")
        all_ok = False

if all_ok:
    print("Every trace record has non-empty input_summary.")
print()

# Show a sample record for each unique tool
print("=" * 60)
print("SAMPLE RECORDS (one per tool)")
print("=" * 60)
seen_tools = set()
for rec in trace:
    if rec.tool_name in seen_tools:
        continue
    seen_tools.add(rec.tool_name)
    print(f"\nTool: {rec.tool_name}")
    print(f"  step_name: {rec.step_name}")
    print(f"  success: {rec.success}")
    print(f"  elapsed_time: {rec.elapsed_time:.4f}s")
    print(f"  input_summary: {rec.input_summary[:200]}...")
    if rec.error:
        print(f"  error: {rec.error[:200]}")
    else:
        print(f"  output_summary: {rec.output_summary[:200]}...")
    if rec.metrics:
        print(f"  metrics: {rec.metrics}")

# ------------------------------------------------------------------
# Candidate-level tool_records
# ------------------------------------------------------------------
print()
print("=" * 60)
print("CANDIDATE-LEVEL TOOL RECORDS")
print("=" * 60)
for i, cand in enumerate(result.all_candidates[:3], 1):
    print(f"\nCandidate #{i} ({cand.id}):")
    print(f"  sequence: {cand.sequence}")
    print(f"  source: {cand.source}")
    print(f"  tool_records: {len(cand.tool_records)}")
    for rec in cand.tool_records:
        print(f"    - {rec.tool_name}: success={rec.success}, elapsed={rec.elapsed_time:.4f}s")

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
print()
print("=" * 60)
print("FINAL VERDICT")
print("=" * 60)
print(f"✓ Workflow succeeded: {result.success}")
print(f"✓ Trace populated: {len(trace)} records")
print(f"✓ Unique tools: {len(found_tools)}")
print(f"✓ All records have input parameters: {all_ok}")
print()
print("FULL TRACE SUMMARY:")
print(f"  Total tool invocations recorded: {len(trace)}")
print(f"  Per-candidate avg records: {sum(len(c.tool_records) for c in result.all_candidates) / max(len(result.all_candidates), 1):.1f}")
