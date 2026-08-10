"""Unified species / organism registry for the RNA agent system.

This module is the single source of truth for:

* CAI codon-usage species aliases and canonical names
* RNARL trained model types and checkpoint filenames
* Reference transcriptome species IDs used by siRNA design

All workflow/tool defaults, Literal enums, descriptions, and microservice
mappings should reference the constants defined here instead of hard-coding
species strings.
"""

from __future__ import annotations

from typing import Literal

# ═══════════════════════════════════════════════════════════════════════════════
# CAI / codon-usage species
# ═══════════════════════════════════════════════════════════════════════════════

CAI_SPECIES_ALIASES: dict[str, str] = {
    # Human
    "human": "Homo sapiens",
    "homo sapiens": "Homo sapiens",
    # Mouse
    "mouse": "Mus musculus",
    "mus musculus": "Mus musculus",
    # Rat
    "rat": "Rattus norvegicus",
    "rattus norvegicus": "Rattus norvegicus",
    # Fruit fly
    "fly": "Drosophila melanogaster",
    "drosophila melanogaster": "Drosophila melanogaster",
    # Nematode
    "worm": "Caenorhabditis elegans",
    "caenorhabditis elegans": "Caenorhabditis elegans",
    # Zebrafish
    "zebrafish": "Danio rerio",
    "danio rerio": "Danio rerio",
    # Thale cress
    "arabidopsis": "Arabidopsis thaliana",
    "arabidopsis thaliana": "Arabidopsis thaliana",
    # Baker's yeast
    "yeast": "Saccharomyces cerevisiae",
    "saccharomyces cerevisiae": "Saccharomyces cerevisiae",
    # E. coli
    "ecoli": "Escherichia coli K-12",
    "e. coli": "Escherichia coli K-12",
    "escherichia coli k-12": "Escherichia coli K-12",
    # B. subtilis
    "bsubtilis": "Bacillus subtilis",
    "b. subtilis": "Bacillus subtilis",
    "bacillus subtilis": "Bacillus subtilis",
    # Chinese hamster ovary (CHO)
    "cho": "Cricetulus griseus",
    "chinese hamster": "Cricetulus griseus",
    "cricetulus griseus": "Cricetulus griseus",
}

DEFAULT_CAI_SPECIES: str = "Homo sapiens"


def format_cai_species_aliases() -> str:
    """Return a comma-separated, sorted list of CAI species aliases."""
    return ", ".join(sorted(CAI_SPECIES_ALIASES))


# ═══════════════════════════════════════════════════════════════════════════════
# RNARL model types
# ═══════════════════════════════════════════════════════════════════════════════

RNARLModelType = Literal[
    "Homo sapiens mRNA",
    "Homo sapiens circular RNA",
    "Arabidopsis thaliana mRNA",
    "Escherichia coli mRNA",
    "Penicillium chrysogenum mRNA",
    "Chlamydomonas reinhardtii mRNA",
    "Thermococcus kodakarensis KOD1 mRNA",
]

RNARL_MODEL_TYPES_LIST: list[str] = list(RNARLModelType.__args__)  # type: ignore[attr-defined]
DEFAULT_RNARL_MODEL_TYPE: str = RNARL_MODEL_TYPES_LIST[0]

RNARL_MODEL_TYPE_TO_CHECKPOINT: dict[str, str] = {
    "Homo sapiens mRNA": "homo_mrna.pt",
    "Homo sapiens circular RNA": "homo_circ.pt",
    "Arabidopsis thaliana mRNA": "Arabidopsis.pt",
    "Escherichia coli mRNA": "EscherichiaColi.pt",
    "Penicillium chrysogenum mRNA": "PC.pt",
    "Chlamydomonas reinhardtii mRNA": "CR.pt",
    "Thermococcus kodakarensis KOD1 mRNA": "TK.pt",
}


def format_rnarl_model_types() -> str:
    """Return a comma-separated list of supported RNARL model types."""
    return ", ".join(RNARL_MODEL_TYPES_LIST)


# ═══════════════════════════════════════════════════════════════════════════════
# Reference transcriptome species (siRNA / off-target scans)
# ═══════════════════════════════════════════════════════════════════════════════

REFERENCE_SPECIES_IDS: list[str] = [
    "homo_sapiens",
    "mus_musculus",
    "danio_rerio",
    "rattus_norvegicus",
    "sars_cov_2",
]

DEFAULT_REFERENCE_SPECIES_ID: str = "homo_sapiens"
