"""Unified experiment-figure palette (user-specified, 2026-08-25 reset; rev 2).

Every experiment figure draws its colours exclusively from PALETTE below.
Twelve colours for eleven workflows — each workflow owns one distinct colour;
grey is reserved for neutral semantics (failed tiles, null/baseline
categories, annotations) and never identifies a workflow.
"""
from __future__ import annotations

# The mandated palette (12 colours as supplied; used verbatim).
PALETTE: list[str] = [
    "#808080",  # grey (reserved: neutral / failure / baseline)
    "#BB9393",  # dusty rose
    "#F58787",  # coral
    "#FEAD76",  # orange
    "#FFD869",  # yellow
    "#CDF296",  # light green
    "#7CAEF0",  # blue
    "#8FB5DA",  # light blue
    "#B7E4FF",  # pale blue
    "#BBD0FF",  # periwinkle
    "#D1AEEC",  # lilac
    "#91DBB2",  # mint
]

PALETTE_BY_NAME: dict[str, str] = {
    "grey": "#808080",
    "dusty_rose": "#BB9393",
    "coral": "#F58787",
    "orange": "#FEAD76",
    "yellow": "#FFD869",
    "light_green": "#CDF296",
    "blue": "#7CAEF0",
    "light_blue": "#8FB5DA",
    "pale_blue": "#B7E4FF",
    "periwinkle": "#BBD0FF",
    "lilac": "#D1AEEC",
    "mint": "#91DBB2",
}

# Semantic accents reused across figures (fixed slots of the palette).
NEUTRAL = "#808080"          # neutral / failure / null-baseline category
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

# Workflow → palette colour (one distinct colour per workflow; adjacent
# carpet rows kept visually separable; grey excluded from workflow identity).
WORKFLOW_COLORS: dict[str, str] = {
    "mrna_cds_design": "#FEAD76",                 # orange
    "full_length_mrna_design": "#F58787",         # coral
    "mrna_sequence_scoring": "#FFD869",           # yellow
    "sirna_design": "#D1AEEC",                    # lilac
    "sgrna_design": "#7CAEF0",                    # blue
    "rna_secondary_structure_design": "#CDF296",  # light green
    "rna_tertiary_structure_design": "#BBD0FF",   # periwinkle
    "rna_aptamer_design": "#BB9393",              # dusty rose
    "rna_small_molecule_interaction": "#8FB5DA",  # light blue
    "aso_target_screening": "#91DBB2",            # mint
    "ires_prediction": "#B7E4FF",                 # pale blue
}
