"""Shared RNA sequence normalization, composition, codon metrics, and dot-bracket structure utilities.

These helpers exist so that agent-core scoring, stubs, and workflow tools do not
duplicate the normalization rules already implemented in the microservices.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

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


# RNA sequence U content INTERFACE LOCK (v0.1.0) —— 禁止单方面变更
# Synchronized files (must all be updated together):
#   - microservices/rna_sequence_metrics_service/main.py
#   - agent_core/tools.py
#   - agent_core/tool_specs.py
#   - agent_core/state.py
#   - agent_core/capabilities/writebacks.py
#   - agent_core/sequence_utils.py  ← 本文件
#   - tests/test_compute_rna_sequence_u_content.py
#   - rna_agent_system/docs/CONTRIBUTING.md


def compute_u_content(normalized_seq: str) -> dict[str, float | int]:
    """Return U metrics for an already-normalized AUGC string.

    Parameters
    ----------
    normalized_seq
        Sequence already normalized to uppercase AUGC (T→U, non-letters removed).

    Returns
    -------
    dict
        Keys: ``sequence_length``, ``u_count``, ``u_fraction``.
    """
    n = len(normalized_seq)
    u = normalized_seq.count("U")
    return {
        "sequence_length": n,
        "u_count": u,
        "u_fraction": u / n if n > 0 else 0.0,
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


# ───────────────────────────────────────────────────────────────────────────────
# CAI (Codon Adaptation Index) computation
# ───────────────────────────────────────────────────────────────────────────────

_BUILTIN_CODON_TABLES: dict[str, dict[str, Any]] | None = None
_SPECIES_ALIASES: dict[str, str] = {
    "human": "Homo sapiens",
    "homo sapiens": "Homo sapiens",
    "mouse": "Mus musculus",
    "mus musculus": "Mus musculus",
    "rat": "Rattus norvegicus",
    "rattus norvegicus": "Rattus norvegicus",
    "fly": "Drosophila melanogaster",
    "drosophila melanogaster": "Drosophila melanogaster",
    "worm": "Caenorhabditis elegans",
    "caenorhabditis elegans": "Caenorhabditis elegans",
    "zebrafish": "Danio rerio",
    "danio rerio": "Danio rerio",
    "arabidopsis": "Arabidopsis thaliana",
    "arabidopsis thaliana": "Arabidopsis thaliana",
    "yeast": "Saccharomyces cerevisiae",
    "saccharomyces cerevisiae": "Saccharomyces cerevisiae",
    "ecoli": "Escherichia coli K-12",
    "e. coli": "Escherichia coli K-12",
    "escherichia coli k-12": "Escherichia coli K-12",
    "bsubtilis": "Bacillus subtilis",
    "b. subtilis": "Bacillus subtilis",
    "bacillus subtilis": "Bacillus subtilis",
    "cho": "Cricetulus griseus",
    "chinese hamster": "Cricetulus griseus",
    "cricetulus griseus": "Cricetulus griseus",
}

_STOP_CODONS = {"UAA", "UAG", "UGA"}


def _load_builtin_codon_tables() -> dict[str, dict[str, Any]]:
    """Load Kazusa codon-usage tables shipped with the agent."""
    global _BUILTIN_CODON_TABLES
    if _BUILTIN_CODON_TABLES is not None:
        return _BUILTIN_CODON_TABLES

    data_path = Path(__file__).with_name("data") / "codon_usage_kazusa.json"
    if not data_path.is_file():
        raise FileNotFoundError(
            f"Built-in codon usage tables not found: {data_path}. "
            "Please provide a custom_codon_table_path."
        )
    with data_path.open("r", encoding="utf-8") as fh:
        _BUILTIN_CODON_TABLES = json.load(fh)
    return _BUILTIN_CODON_TABLES


def resolve_species_name(name: str) -> str:
    """Resolve a species name or alias to the canonical built-in name.

    Returns the original string unchanged if no alias matches, allowing
    custom tables to be looked up by their own keys.
    """
    normalized = name.strip().lower()
    return _SPECIES_ALIASES.get(normalized, name)


def normalize_cds_sequence(raw: str) -> str:
    """Strip FASTA headers, uppercase, T→U, keep AUGC only, validate triplet length.

    Raises
    ------
    ValueError
        If the sequence contains characters outside AUGC or if its length
        is not a multiple of 3.
    """
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    merged = "".join(lines).upper().replace("T", "U")
    seq = re.sub(r"[^AUGC]", "", merged)
    if len(seq) == 0:
        raise ValueError("No A/U/G/C nucleotides found after normalization.")
    if len(seq) % 3 != 0:
        raise ValueError(
            f"CDS length must be a multiple of 3 (codons); got {len(seq)} nt."
        )
    return seq


def build_cai_weights(codon_fractions: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Build Sharp & Li relative adaptiveness weights from Kazusa-style fractions.

    For each amino-acid group, the most frequent codon receives w=1.0;
    all others receive w = fraction / max_fraction_in_group.

    Parameters
    ----------
    codon_fractions
        Mapping ``codon -> {"aa": str, "fraction": float}``.

    Returns
    -------
    dict
        Mapping ``codon -> weight``.
    """
    # Group by amino acid
    aa_groups: dict[str, dict[str, float]] = {}
    for codon, info in codon_fractions.items():
        aa = info["aa"]
        frac = float(info["fraction"])
        aa_groups.setdefault(aa, {})[codon] = frac

    weights: dict[str, float] = {}
    for aa, codons in aa_groups.items():
        max_frac = max(codons.values())
        if max_frac == 0.0:
            max_frac = 1.0  # avoid division by zero
        for codon, frac in codons.items():
            weights[codon] = frac / max_frac

    return weights


def compute_cai(cds_seq: str, codon_weights: dict[str, float]) -> dict[str, Any]:
    """Compute CAI for a normalized CDS sequence.

    Parameters
    ----------
    cds_seq
        Uppercase RNA sequence (AUGC only), length multiple of 3.
    codon_weights
        Mapping ``codon -> relative adaptiveness`` (e.g. from ``build_cai_weights``).

    Returns
    -------
    dict
        Keys: ``cai_score``, ``codon_count``, ``valid_codons``,
        ``invalid_codons``, ``stop_codons_encountered``.
    """
    n = len(cds_seq)
    codon_count = n // 3
    log_sum = 0.0
    valid = 0
    invalid = 0
    stops = 0

    for i in range(0, n, 3):
        codon = cds_seq[i : i + 3]
        if codon in _STOP_CODONS:
            stops += 1
            continue
        w = codon_weights.get(codon)
        if w is None or w <= 0.0:
            invalid += 1
            continue
        valid += 1
        log_sum += math.log(w)

    if valid == 0:
        cai = 0.0
    else:
        cai = math.exp(log_sum / valid)

    return {
        "cai_score": cai,
        "codon_count": codon_count,
        "valid_codons": valid,
        "invalid_codons": invalid,
        "stop_codons_encountered": stops,
    }


# ───────────────────────────────────────────────────────────────────────────────
# Dict value extraction helpers (used by workflows)
# ───────────────────────────────────────────────────────────────────────────────


def _pick_float(data: dict[str, Any], key: str) -> float | None:
    """Safely extract a float from *data* by *key*."""
    if key in data:
        try:
            return float(data[key])
        except (TypeError, ValueError):
            pass
    return None


def _pick_int(data: dict[str, Any], key: str) -> int | None:
    """Safely extract an int from *data* by *key*."""
    if key in data:
        try:
            return int(data[key])
        except (TypeError, ValueError):
            pass
    return None


# ───────────────────────────────────────────────────────────────────────────────
# mRNA scoring helpers (moved from workflows/mrna_scoring.py)
# ───────────────────────────────────────────────────────────────────────────────


def gc_fraction_from_sequence(sequence: str) -> float:
    """(G+C) / length for normalized AUCG string; empty → 0.0."""
    if not sequence:
        return 0.0
    normalized = normalize_rna_sequence(sequence)
    if not normalized:
        return 0.0
    result = compute_gc_content(normalized)
    return float(result["gc_content"])


def compute_mrna_metric_bundle(
    *,
    sequence: str,
    gc_from_tools: float | None,
    sequence_length_from_tools: int | None,
    mfe_kcal_per_mol: float | None,
    unpaired_fraction: float | None = None,
    rnastop_overall_stability: float | None = None,
    cai_score: float | None = None,
    u_fraction: float | None = None,
) -> dict[str, Any]:
    """Collect canonical keys used by scoring and summaries."""
    gc_local = gc_fraction_from_sequence(sequence)
    gc_eff = gc_from_tools if gc_from_tools is not None else gc_local
    length_eff = (
        sequence_length_from_tools
        if sequence_length_from_tools is not None
        else len(sequence)
    )
    mfe_per_nt = None
    if mfe_kcal_per_mol is not None and length_eff > 0:
        try:
            mfe_per_nt = float(mfe_kcal_per_mol) / length_eff
        except (TypeError, ValueError):
            mfe_per_nt = None
    return {
        "gc_content": float(gc_eff),
        "gc_content_local": float(gc_local),
        "sequence_length": int(length_eff),
        "mfe_kcal_per_mol": mfe_kcal_per_mol,
        "mfe_per_nt": mfe_per_nt,
        "unpaired_fraction": unpaired_fraction,
        "rnastop_overall_stability": rnastop_overall_stability,
        "cai_score": cai_score,
        "u_fraction": u_fraction,
    }


def score_mrna_candidate(
    bundle: dict[str, Any],
) -> dict[str, float]:
    """Return ``total_score`` computed as ``-mfe + codon_count * log(CAI)``.

    Raw metrics from *bundle* (gc_content, mfe_kcal_per_mol,
    unpaired_fraction, cai_score) are preserved in the result for display
    purposes but do **not** affect the ranking formula.
    """
    mfe_raw = bundle.get("mfe_kcal_per_mol")
    cai_raw = bundle.get("cai_score")
    length_nt = int(bundle.get("sequence_length", 0))

    result: dict[str, float] = {}

    mfe_per_nt = bundle.get("mfe_per_nt")
    if mfe_per_nt is not None:
        result["mfe_per_nt"] = float(mfe_per_nt)

    if cai_raw is not None:
        result["cai_score"] = float(cai_raw)

    # total_score = -mfe + codon_count * log(CAI)
    if mfe_raw is not None and cai_raw is not None:
        try:
            cai_val = float(cai_raw)
            mfe_val = float(mfe_raw)
            if (
                cai_val > 0.0
                and length_nt > 0
                and math.isfinite(cai_val)
                and math.isfinite(mfe_val)
            ):
                codon_count = length_nt // 3
                combined_score = -mfe_val + codon_count * math.log(cai_val)
                result["combined_score"] = float(combined_score)
                result["total_score"] = float(combined_score)
                return result
        except (TypeError, ValueError):
            pass

    # Fallback when CAI or MFE is missing (should not happen in normal operation)
    result["total_score"] = 0.0
    return result
