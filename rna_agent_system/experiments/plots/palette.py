"""Unified experiment-figure palette (user-specified, 2026-08-25 reset; rev 3).

Every experiment figure draws its colours exclusively from PALETTE below.
Base: the ten user-specified colours. Two coordinated extensions (2026-08-25,
rev 3): #F5A49E (mid coral — the coral family's missing mid lightness) and
#98A4EE (mid periwinkle — the pale periwinkle #C9CEFE deepened toward the
royal blues). Twelve colours for eleven workflows — each workflow owns one
distinct colour; no workflow is identified by a neutral grey.
"""
from __future__ import annotations

# The mandated palette: ten user-specified colours + two coordinated
# extensions (marked NEW), used verbatim.
PALETTE: list[str] = [
    "#FCE8E6",  # pale rose
    "#FFC6BC",  # light coral
    "#F8B9B8",  # rose
    "#F5A49E",  # NEW mid coral (extension)
    "#D6DFEF",  # pale blue
    "#A5CDE2",  # light blue
    "#5FA3CB",  # blue
    "#668FCA",  # royal blue
    "#C9CEFE",  # pale periwinkle
    "#98A4EE",  # NEW mid periwinkle (extension)
    "#66A8CD",  # steel blue
    "#006BAD",  # deep blue
]

PALETTE_BY_NAME: dict[str, str] = {
    "pale_rose": "#FCE8E6",
    "light_coral": "#FFC6BC",
    "rose": "#F8B9B8",
    "mid_coral": "#F5A49E",
    "pale_blue": "#D6DFEF",
    "light_blue": "#A5CDE2",
    "blue": "#5FA3CB",
    "royal_blue": "#668FCA",
    "periwinkle": "#C9CEFE",
    "mid_periwinkle": "#98A4EE",
    "steel_blue": "#66A8CD",
    "deep_blue": "#006BAD",
}

# Semantic accents reused across figures (fixed slots of the palette).
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

# Workflow → palette colour (one distinct colour per workflow; warm shades
# mark the sequence-design workflows, blues the structure/prediction/screening
# workflows; the two extensions cover aptamer and IRES).
WORKFLOW_COLORS: dict[str, str] = {
    "mrna_cds_design": "#FFC6BC",                 # light coral
    "full_length_mrna_design": "#F8B9B8",         # rose
    "mrna_sequence_scoring": "#FCE8E6",           # pale rose
    "sirna_design": "#006BAD",                    # deep blue
    "sgrna_design": "#668FCA",                    # royal blue
    "rna_secondary_structure_design": "#A5CDE2",  # light blue
    "rna_tertiary_structure_design": "#5FA3CB",   # blue
    "rna_aptamer_design": "#F5A49E",              # NEW mid coral
    "rna_small_molecule_interaction": "#C9CEFE",  # pale periwinkle
    "aso_target_screening": "#D6DFEF",            # pale blue
    "ires_prediction": "#98A4EE",                 # NEW mid periwinkle
}
