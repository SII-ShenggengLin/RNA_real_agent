# compute_rna_sequence_gc_content

## Overview

Compute the GC-content fraction `(G+C)/N` of an RNA or DNA sequence file.

- **Identity**: `compute_rna_sequence_gc_content`
- **Version**: `0.1.0-port8020`
- **Source**: in-repo microservice (`microservices/rna_sequence_metrics_service`)
- **Transport**: HTTP
- **Endpoint**: `POST http://127.0.0.1:8020/gc-content`
- **Status**: `available`

## Capabilities

- Compute `(G+C)/N` from a sequence file (A/U/G/C only after normalization).
- Accepts plain text or FASTA format.
- Handles DNA (T→U) and RNA input transparently.

## Limitations

- Ignores non-AUGC characters after normalization.
- Does not check biological correctness beyond parsing.
- Requires the sequence to be provided as a file path; inline long sequences are discouraged.

## Input Schema (`RnaGcContentInput`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `filepath` | `str` | **required** | Path to RNA or DNA sequence (workspace-relative or absolute). |
| `service_url` | `str` | `http://127.0.0.1:8020/gc-content` | POST endpoint for the GC content microservice. |
| `timeout_seconds` | `float` | `120.0` | HTTP request timeout in seconds (must be > 0 and ≤ 600). |

## Output Schema (`RnaGcContentOutput`)

| Field | Type | Description |
|-------|------|-------------|
| `input_filepath` | `str` | Original filepath passed by the caller. |
| `resolved_filepath` | `str` | Absolute path resolved by the microservice. |
| `sequence_length` | `int` | Count of A/U/G/C nucleotides after normalization. |
| `g_count` | `int` | Count of G. |
| `c_count` | `int` | Count of C. |
| `gc_count` | `int` | Count of G + C. |
| `gc_content` | `float` | `(G+C)/N` fraction in [0, 1]. |
| `model` | `str` | Always `"rna-sequence-metrics-gc"`. |

## Example

```python
from agent_core.tools import compute_rna_sequence_gc_content

result = compute_rna_sequence_gc_content.invoke(
    {"filepath": "workspace/sequence.fasta"}
)
# result["gc_content"] → 0.52
# result["sequence_length"] → 150
# result["gc_count"] → 78
```

## State Fields Written

When used inside the agent graph (`nodes.py`), the following state fields are updated:

| State Field | Type | Source |
|-------------|------|--------|
| `sequence_gc_content` | `float` | `gc_content` from tool result. |
| `sequence_gc_length` | `int` | `sequence_length` from tool result. |
| `sequence_gc_count` | `int` | `gc_count` from tool result. |
| `sequence_g_count` | `int` | `g_count` from tool result. |
| `sequence_c_count` | `int` | `c_count` from tool result. |

## INTERFACE LOCK

**v0.1.0** — Any modification must be synchronized across:
- `microservices/rna_sequence_metrics_service/main.py`
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `agent_core/state.py`
- `agent_core/nodes.py`
- `agent_core/workflow_tools/rna_gc_content_workflow.py`
- `agent_core/workflows/mrna_workflow.py`
- `agent_core/workflows/mrna_scoring.py`
- `agent_core/workflow_baseline_eval.py`
- `tests/test_rna_gc_content_workflow.py`
- `tests/test_compute_rna_sequence_gc_content.py`
- This document

## Dependencies

- **rna_sequence_metrics microservice** (`microservices/rna_sequence_metrics_service`, port 8020)
