"""Unified experiment-figure palette (user-specified, 2026-08-25 reset).

Every experiment figure draws its colours exclusively from PALETTE below.
Eleven workflows map onto the ten colours; the lightest blue is reused for the
one workflow whose carpet row is spatially non-adjacent to its first use.
"""
from __future__ import annotations

# The mandated palette (10 colours as supplied; used verbatim).
PALETTE: list[str] = [
    "#FCE8E6",  # pale rose
    "#FFC6BC",  # light coral
    "#F8B9B8",  # rose
    "#D6DFEF",  # pale blue
    "#A5CDE2",  # light blue
    "#5FA3CB",  # blue
    "#668FCA",  # royal blue
    "#C9CEFE",  # periwinkle
    "#66A8CD",  # steel blue
    "#006BAD",  # deep blue
]

PALETTE_BY_NAME: dict[str, str] = {
    "pale_rose": "#FCE8E6",
    "light_coral": "#FFC6BC",
    "rose": "#F8B9B8",
    "pale_blue": "#D6DFEF",
    "light_blue": "#A5CDE2",
    "blue": "#5FA3CB",
    "royal_blue": "#668FCA",
    "periwinkle": "#C9CEFE",
    "steel_blue": "#66A8CD",
    "deep_blue": "#006BAD",
}

# Semantic accents reused across figures (fixed slots of the palette).
NEUTRAL_GRID = "#D9D9D9"
TEXT = "#1A1A1A"

# Canonical workflow order and display names.
WORKFLOW_ORDER: list[str] = [
    "mrna_cds_design",
    "full_length_mrna_design",
    "mrna_sequence_scoring",
    "sirna_design",
    "sgrna_design",
    "rna_secondary_structure_design",
    "rna_tertiary_structure_design",
    "rna_aptamer_design",
    "rna_small_molecule_interaction",
    "aso_target_screening",
    "ires_prediction",
]

WORKFLOW_LABELS: dict[str, str] = {
    "mrna_cds_design": "mRNA CDS",
    "full_length_mrna_design": "Full-length mRNA",
    "mrna_sequence_scoring": "mRNA scoring",
    "sirna_design": "siRNA",
    "sgrna_design": "sgRNA handle",
    "rna_secondary_structure_design": "Secondary structure",
    "rna_tertiary_structure_design": "Tertiary structure",
    "rna_aptamer_design": "Aptamer",
    "rna_small_molecule_interaction": "RNA–small molecule",
    "aso_target_screening": "ASO screening",
    "ires_prediction": "IRES prediction",
}

# Workflow → palette colour. Warm (rose/coral) shades mark the sequence-design
# workflows, blues mark structure/prediction/screening workflows; pale_blue is
# reused once for a spatially separated row.
WORKFLOW_COLORS: dict[str, str] = {
    "mrna_cds_design": "#FFC6BC",
    "full_length_mrna_design": "#F8B9B8",
    "mrna_sequence_scoring": "#FCE8E6",
    "sirna_design": "#006BAD",
    "sgrna_design": "#668FCA",
    "rna_secondary_structure_design": "#A5CDE2",
    "rna_tertiary_structure_design": "#5FA3CB",
    "rna_aptamer_design": "#66A8CD",
    "rna_small_molecule_interaction": "#C9CEFE",
    "aso_target_screening": "#D6DFEF",
    "ires_prediction": "#006BAD",
}
