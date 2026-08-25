"""Unified experiment-figure palette (user-specified, 2026-08-25 reset; rev 6).

Every experiment figure draws its colours exclusively from PALETTE below.
Rev 6: the user's cool pastel twelve-colour set (blue-grey / lavender / green
families), supplied directly as hex codes. Eleven of the twelve identify the
workflows (#dbe0eb held out — nearest neighbour of #d5dee6); the two chromatic
anchors (#7aa490 sage, #8db1e1 cornflower) break the pale runs, and the two
near-twin pairs (#d5dee6/#dbe0eb, #b3c3d5/#acc5d1) are kept rows apart.
"""
from __future__ import annotations

# The mandated palette (twelve colours as supplied; used verbatim).
PALETTE: list[str] = [
    "#d5dee6",  # pale blue grey
    "#b3c3d5",  # light blue grey
    "#d4d2e9",  # pale lavender
    "#d5d3de",  # grey lavender
    "#aecbe0",  # sky blue
    "#dbe0eb",  # blue white (held out: nearest neighbour of #d5dee6)
    "#c0c4c9",  # neutral grey
    "#c4d4de",  # steel blue
    "#acccae",  # pale green
    "#acc5d1",  # teal grey
    "#7aa490",  # sage green (anchor)
    "#8db1e1",  # cornflower (anchor)
]

PALETTE_BY_NAME: dict[str, str] = {
    "pale_blue_grey": "#d5dee6",
    "light_blue_grey": "#b3c3d5",
    "pale_lavender": "#d4d2e9",
    "grey_lavender": "#d5d3de",
    "sky_blue": "#aecbe0",
    "blue_white": "#dbe0eb",
    "neutral_grey": "#c0c4c9",
    "steel_blue": "#c4d4de",
    "pale_green": "#acccae",
    "teal_grey": "#acc5d1",
    "sage_green": "#7aa490",
    "cornflower": "#8db1e1",
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

# Workflow → palette colour (one distinct colour per workflow; the sage and
# cornflower anchors split the carpet into three pale runs, and near-twin
# tones never sit on adjacent rows).
WORKFLOW_COLORS: dict[str, str] = {
    "mrna_cds_design": "#d4d2e9",                 # pale lavender
    "full_length_mrna_design": "#8db1e1",         # cornflower (anchor)
    "mrna_sequence_scoring": "#acccae",           # pale green
    "sirna_design": "#aecbe0",                    # sky blue
    "sgrna_design": "#d5d3de",                    # grey lavender
    "rna_secondary_structure_design": "#7aa490",  # sage green (anchor)
    "rna_tertiary_structure_design": "#d5dee6",   # pale blue grey
    "rna_aptamer_design": "#c0c4c9",              # neutral grey
    "rna_small_molecule_interaction": "#b3c3d5",  # light blue grey
    "aso_target_screening": "#c4d4de",            # steel blue
    "ires_prediction": "#acc5d1",                 # teal grey
}
