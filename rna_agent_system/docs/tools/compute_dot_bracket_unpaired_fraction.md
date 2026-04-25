# compute_dot_bracket_unpaired_fraction

## Overview

Compute the fraction of unpaired bases in a dot-bracket RNA secondary structure string: `count('.') / length`.

- **Identity**: `compute_dot_bracket_unpaired_fraction`
- **Version**: `0.1.0-port8020`
- **Source**: in-repo microservice (`microservices/rna_sequence_metrics_service`)
- **Transport**: HTTP
- **Endpoint**: `POST http://127.0.0.1:8020/unpaired-fraction`
- **Status**: `available`

## Capabilities

- Compute `count('.') / length` from a dot-bracket structure file.
- Accepts plain text or FASTA format (FASTA headers are skipped).
- Supports all standard dot-bracket symbols: `. ( ) [ ] { } < >`.

## Limitations

- Does **not** validate balanced brackets or biological correctness.
- Ignores anything outside the allowed dot-bracket symbol set.
- Requires the structure to be provided as a file path; inline long structures are discouraged.

## Input Schema (`DotBracketUnpairedFractionInput`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `filepath` | `str` | **required** | Path to dot-bracket structure file (workspace-relative or absolute). |
| `service_url` | `str` | `http://127.0.0.1:8020/unpaired-fraction` | POST endpoint for the unpaired fraction microservice. |
| `timeout_seconds` | `float` | `120.0` | HTTP request timeout in seconds (must be > 0 and ≤ 600). |

## Output Schema (`DotBracketUnpairedFractionOutput`)

| Field | Type | Description |
|-------|------|-------------|
| `input_filepath` | `str` | Original filepath passed by the caller. |
| `resolved_filepath` | `str` | Absolute path resolved by the microservice. |
| `structure_length` | `int` | Total length of the parsed dot-bracket string. |
| `dot_count` | `int` | Count of unpaired symbols `.`. |
| `unpaired_fraction` | `float` | `count('.') / length` fraction in [0, 1]. |
| `model` | `str` | Always `"rna-sequence-metrics-unpaired"`. |

## Example

```python
from agent_core.tools import compute_dot_bracket_unpaired_fraction

result = compute_dot_bracket_unpaired_fraction.invoke(
    {"filepath": "workspace/structure.ss"}
)
# result["unpaired_fraction"] → 0.35
# result["structure_length"] → 200
# result["dot_count"] → 70
```

## State Fields Written

When used inside the agent graph (`nodes.py`), the following state fields are updated:

| State Field | Type | Source |
|-------------|------|--------|
| `dot_bracket_unpaired_fraction` | `float` | `unpaired_fraction` from tool result. |
| `dot_bracket_structure_length` | `int` | `structure_length` from tool result. |
| `dot_bracket_dot_count` | `int` | `dot_count` from tool result. |

## INTERFACE LOCK

**v0.1.0** — Any modification must be synchronized across:
- `microservices/rna_sequence_metrics_service/main.py`
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `agent_core/state.py`
- `agent_core/nodes.py`
- `agent_core/sequence_utils.py`
- This document

## Dependencies

- **rna_sequence_metrics microservice** (`microservices/rna_sequence_metrics_service`, port 8020)
