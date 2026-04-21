"""Minimal mRNA candidate generators for scoring/ranking workflows.

Reuse pattern: callers write sequences to workspace via ``file_manager.save_sequence`` before tools run.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Literal, Optional, Sequence, Union

from agent_core.workflow_models import Candidate


def normalize_rna_sequence(raw: str) -> str:
    """Uppercase RNA; collapse whitespace; strip non-letters; map T→U."""

    sequence_lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.lstrip().startswith(">")
    ]
    merged = "".join(sequence_lines).upper().replace("T", "U")
    return re.sub(r"[^AUCG]", "", merged)


CandidateMode = Literal["direct", "synonymous_minimal", "tail_augment"]


# First-position synonymous swaps (codon → alternative). Small static table for demos/tests.
_SYNONYMOUS_SWAP: dict[str, str] = {
    "UUU": "UUC",
    "UUA": "UUG",
    "UCU": "UCC",
    "UAU": "UAC",
    "UGU": "UGC",
    "GUU": "GUC",
    "GUA": "GUG",
    "AUU": "AUC",
    "AUA": "AUG",
    "CCA": "CCC",
    "CCU": "CCC",
}


def generate_candidate_sequences(
    *,
    mode: CandidateMode,
    sequences: Optional[Sequence[str]] = None,
    sequence: Optional[str] = None,
    synonym_source: Optional[str] = None,
    max_synonymous_variants: int = 4,
    tail_augment_extra: int = 2,
) -> List[str]:
    """Return plain RNA strings to wrap as ``Candidate`` objects.

    Parameters
    ----------
    mode:
        - ``direct``: use ``sequences`` or a single ``sequence`` (normalized).
        - ``synonymous_minimal``: start from ``synonym_source`` or first entry of ``sequences``,
          emit the reference plus up to ``max_synonymous_variants`` single-codon swaps.
        - ``tail_augment``: take base sequence(s) from ``direct`` rules and append poly-A tail
          length variants for extra candidate diversity (baseline / ranking experiments).
    """

    if mode == "direct":
        if sequences:
            out = [normalize_rna_sequence(s) for s in sequences]
            return [s for s in out if s]
        if sequence:
            one = normalize_rna_sequence(sequence)
            return [one] if one else []
        return []

    if mode == "synonymous_minimal":
        src = synonym_source or (sequences[0] if sequences else None) or sequence
        if not src:
            return []
        ref = normalize_rna_sequence(src)
        if len(ref) < 3 or len(ref) % 3 != 0:
            # Not a clean CDS frame — still return reference only for a closed loop.
            return [ref] if ref else []

        variants: List[str] = [ref]
        codons = [ref[i : i + 3] for i in range(0, len(ref), 3)]
        cap = max(1, max_synonymous_variants)
        for i, codon in enumerate(codons):
            alt = _SYNONYMOUS_SWAP.get(codon)
            if not alt or alt == codon:
                continue
            mutated = "".join(codons[:i] + [alt] + codons[i + 1 :])
            variants.append(mutated)
            if len(variants) >= cap:
                break
        return variants[:cap]

    if mode == "tail_augment":
        base = generate_candidate_sequences(mode="direct", sequences=sequences, sequence=sequence)
        if not base:
            return []
        aug: List[str] = list(base)
        primary = base[0]
        for k in range(max(0, tail_augment_extra)):
            aug.append(primary + ("A" * (3 + k)))
        return aug

    raise ValueError(f"unsupported mode: {mode}")


def build_candidates(
    seqs: Iterable[str],
    *,
    source: str = "mrna_candidate_generator",
) -> List[Candidate]:
    """Wrap sequences in ``Candidate`` rows (``sequence_type=mrna``)."""

    return [
        Candidate(sequence=s, sequence_type="mrna", source=source, metadata={"generator": source})
        for s in seqs
        if s
    ]
