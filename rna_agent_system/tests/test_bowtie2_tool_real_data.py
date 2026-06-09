"""Real-data test for the new Bowtie2 tool (PA_006 benchmark task)."""

import json
from pathlib import Path

# Load PA_006 task
BENCH_JSON = Path(__file__).resolve().parents[1] / "data" / "benchmarks" / "RNA-BioBench-ProcessAware" / "task_set_for_llm_comparison.json"
with open(BENCH_JSON) as f:
    bench = json.load(f)
pa006 = next(t for t in bench["tasks"] if t["task_id"] == "PA_006")

import re
query = pa006["user_query"]
seq = re.search(r"[AUGC]{40,}", query).group(0)

from agent_core.file_manager import save_sequence
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

# Save query sequence
query_fp = save_sequence(seq, prefix="bowtie2_query")
print(f"Query saved to: {query_fp}")

# Use small transcriptome for speed
subject_fp = "/tmp/small_transcripts.fa"

# Build executor and run tool
executor = ToolExecutor(build_default_tool_registry(include_demo=False))
result = executor.run_tool(
    "run_bowtie2_short_alignment",
    filepath=query_fp,
    subject_fasta_path=subject_fp,
    mode="local",
    k=50,
    score_min="G,10,4",
)

print(f"Tool success: {result.success}")
print(f"Hit count: {result.artifacts.get('result', {}).get('hit_count', 'N/A')}")
print(f"Command: {result.artifacts.get('result', {}).get('bowtie2_command', 'N/A')[:200]}...")
print(f"Elapsed: {result.elapsed_time:.4f}s")
if result.error:
    print(f"Error: {result.error}")
