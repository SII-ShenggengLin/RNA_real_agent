"""Unified experiment-figure palette (user-specified, 2026-08-25 reset; rev 4).

Every experiment figure draws its colours exclusively from PALETTE below.
Rev 4: the twelve colours extracted (pixel-level, line-core modal values) from
the user-supplied reference image — two solid bars (blue, green) plus five
top/bottom line pairs in the orange–rose–sand–cyan families. Eleven of the
twelve identify the workflows (the most redundant cream #FBDEBB is held out);
no workflow is identified by a neutral grey.
"""
from __future__ import annotations

# The mandated palette: twelve colours from the user's reference image,
# used verbatim.
PALETTE: list[str] = [
    "#7AACE1",  # blue
    "#A6D08E",  # green
    "#FAA775",  # orange
    "#F1AC83",  # light orange
    "#FBA9A9",  # rose
    "#F3B0A5",  # light rose
    "#EDD8B9",  # sand
    "#C1B298",  # grey sand
    "#CAF3FA",  # pale cyan
    "#A4BEBF",  # grey cyan
    "#FAD8B3",  # cream
    "#FBDEBB",  # light cream (held out: nearest neighbour of #FAD8B3)
]

PALETTE_BY_NAME: dict[str, str] = {
    "blue": "#7AACE1",
    "green": "#A6D08E",
    "orange": "#FAA775",
    "light_orange": "#F1AC83",
    "rose": "#FBA9A9",
    "light_rose": "#F3B0A5",
    "sand": "#EDD8B9",
    "grey_sand": "#C1B298",
    "pale_cyan": "#CAF3FA",
    "grey_cyan": "#A4BEBF",
    "cream": "#FAD8B3",
    "light_cream": "#FBDEBB",
}

# Semantic accents reused across figures.
NEUTRAL_GRID = "#D9D9D9"     # gridlines / tile borders (non-data grey)
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

# Workflow → palette colour (one distinct colour per workflow; adjacent carpet
# rows pairwise separable; the two near-identical pale sands sit 8 rows apart).
WORKFLOW_COLORS: dict[str, str] = {
    "mrna_cds_design": "#FAA775",                 # orange
    "full_length_mrna_design": "#FBA9A9",         # rose
    "mrna_sequence_scoring": "#EDD8B9",           # sand
    "sirna_design": "#7AACE1",                    # blue
    "sgrna_design": "#A6D08E",                    # green
    "rna_secondary_structure_design": "#CAF3FA",  # pale cyan
    "rna_tertiary_structure_design": "#F1AC83",   # light orange
    "rna_aptamer_design": "#C1B298",              # grey sand
    "rna_small_molecule_interaction": "#F3B0A5",  # light rose
    "aso_target_screening": "#A4BEBF",            # grey cyan
    "ires_prediction": "#FAD8B3",                 # cream
}
