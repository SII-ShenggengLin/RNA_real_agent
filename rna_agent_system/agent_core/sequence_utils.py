"""Shared RNA sequence normalization, composition, and dot-bracket structure utilities.

These helpers exist so that agent-core scoring, stubs, and workflow tools do not
duplicate the normalization rules already implemented in the microservices.
"""

from __future__ import annotations

import re

# ───────────────────────────────────────────────────────────────────────────────
# RNA sequence normalization
# ───────────────────────────────────────────────────────────────────────────────


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


# ───────────────────────────────────────────────────────────────────────────────
# Dot-bracket secondary structure utilities
# ───────────────────────────────────────────────────────────────────────────────

_DOT_BRACKET_ALLOWED = re.compile(r"^[.()\[\]{}<>]+$")


def extract_dot_bracket(raw: str) -> str:
    """Extract dot-bracket structure string from raw text.

    Skips FASTA headers (lines starting with ``>``) and empty lines,
    then concatenates all remaining lines.  This mirrors the logic in
    ``microservices/rna_sequence_metrics_service/main.py`` so that
    agent-core stubs and scoring nodes stay consistent with the
    microservice.
    """
    parts: list[str] = []
    for ln in raw.splitlines():
        s = ln.strip()
        if not s or s.startswith(">"):
            continue
        parts.append(s)
    return "".join(parts)


def validate_dot_bracket(struct: str) -> None:
    """Validate that *struct* contains only legal dot-bracket symbols.

    Raises
    ------
    ValueError
        If the string is empty or contains characters outside
        ``. ( ) [ ] { } < >``.
    """
    if not struct:
        raise ValueError("Empty dot-bracket structure after parsing.")
    if not _DOT_BRACKET_ALLOWED.match(struct):
        raise ValueError(
            "Structure must contain only dot-bracket symbols: . ( ) [ ] { } < >"
        )


def compute_dot_bracket_unpaired_fraction(struct: str) -> dict[str, float | int]:
    """Return unpaired-fraction metrics for an already-extracted dot-bracket string.

    Parameters
    ----------
    struct
        Clean dot-bracket string (no headers, no whitespace).

    Returns
    -------
    dict
        Keys: ``structure_length``, ``dot_count``, ``unpaired_fraction``.

    Raises
    ------
    ValueError
        If *struct* is empty or contains invalid characters.
    """
    validate_dot_bracket(struct)
    n = len(struct)
    dots = struct.count(".")
    return {
        "structure_length": n,
        "dot_count": dots,
        "unpaired_fraction": dots / n,
    }
