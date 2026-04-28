"""Minimal mRNA candidate normalisation for scoring workflows.

No sequence generation is performed; input sequences are only normalised
(FASTA headers stripped, T→U, non-AUGC characters removed).
"""

from __future__ import annotations

import re
from typing import List, Sequence

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


def build_candidates(
    seqs: Sequence[str],
    *,
    source: str = "mrna_candidate_generator",
) -> List[Candidate]:
    """Wrap sequences in ``Candidate`` rows (``sequence_type=mrna``)."""

    return [
        Candidate(sequence=s, sequence_type="mrna", source=source, metadata={"generator": source})
        for s in seqs
        if s
    ]
