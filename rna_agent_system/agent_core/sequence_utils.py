"""Shared RNA sequence normalization and composition utilities.

These helpers exist so that agent-core scoring, stubs, and workflow tools do not
duplicate the normalization rules already implemented in the microservices.
"""

from __future__ import annotations

import re


def normalize_rna_sequence(raw: str) -> str:
    """Strip FASTA headers, uppercase, T→U, keep AUGC only.

    Mirrors the normalization logic in
    ``microservices/rna_sequence_metrics_service/main.py``.
    """
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    merged = "".join(lines).upper().replace("T", "U")
    return re.sub(r"[^AUGC]", "", merged)


def compute_gc_content(normalized_seq: str) -> dict[str, float | int]:
    """Return GC metrics for an already-normalized AUGC string.

    Returns
    -------
    dict
        Keys: ``sequence_length``, ``g_count``, ``c_count``,
        ``gc_count``, ``gc_content``.
    """
    n = len(normalized_seq)
    if n == 0:
        return {
            "sequence_length": 0,
            "g_count": 0,
            "c_count": 0,
            "gc_count": 0,
            "gc_content": 0.0,
        }
    g = normalized_seq.count("G")
    c = normalized_seq.count("C")
    gc = g + c
    return {
        "sequence_length": n,
        "g_count": g,
        "c_count": c,
        "gc_count": gc,
        "gc_content": gc / n,
    }
