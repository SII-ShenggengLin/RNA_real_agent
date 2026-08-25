"""Unified experiment-figure palette (user-specified, 2026-08-25 reset; rev 5).

Every experiment figure draws its colours exclusively from PALETTE below.
Rev 5: the user's muted Morandi twelve-colour set, supplied directly as hex
codes. Eleven of the twelve identify the workflows (#EFE1D6 almond held out —
nearest neighbour of #F3E3E3/#EDE7D9); the layout keeps the darkest tones
(#654E5E plum, #78828B slate) as row separators so no two adjacent carpet
rows share the same lightness band.
"""
from __future__ import annotations

# The mandated palette (twelve colours as supplied; used verbatim).
PALETTE: list[str] = [
    "#A49193",  # mauve grey
    "#EDE7D9",  # ivory
    "#D3DCE3",  # pale blue grey
    "#B5C9BE",  # sage
    "#F3E3E3",  # pale blush
    "#DECCA6",  # wheat
    "#E0DEDF",  # pale lavender grey
    "#78828B",  # slate
    "#D6E3D2",  # pale sage
    "#C89D94",  # dusty rose
    "#EFE1D6",  # almond (held out: nearest neighbour of ivory/blush)
    "#654E5E",  # dark plum
]

PALETTE_BY_NAME: dict[str, str] = {
    "mauve_grey": "#A49193",
    "ivory": "#EDE7D9",
    "pale_blue_grey": "#D3DCE3",
    "sage": "#B5C9BE",
    "pale_blush": "#F3E3E3",
    "wheat": "#DECCA6",
    "pale_lavender_grey": "#E0DEDF",
    "slate": "#78828B",
    "pale_sage": "#D6E3D2",
    "dusty_rose": "#C89D94",
    "almond": "#EFE1D6",
    "dark_plum": "#654E5E",
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

# Workflow → palette colour (one distinct colour per workflow; the dark plum
# and slate rows separate the pale-tone runs so adjacent rows never share a
# lightness band).
WORKFLOW_COLORS: dict[str, str] = {
    "mrna_cds_design": "#DECCA6",                 # wheat
    "full_length_mrna_design": "#C89D94",         # dusty rose
    "mrna_sequence_scoring": "#EDE7D9",           # ivory
    "sirna_design": "#654E5E",                    # dark plum
    "sgrna_design": "#D3DCE3",                    # pale blue grey
    "rna_secondary_structure_design": "#B5C9BE",  # sage
    "rna_tertiary_structure_design": "#A49193",   # mauve grey
    "rna_aptamer_design": "#D6E3D2",              # pale sage
    "rna_small_molecule_interaction": "#78828B",  # slate
    "aso_target_screening": "#F3E3E3",            # pale blush
    "ires_prediction": "#E0DEDF",                 # pale lavender grey
}
