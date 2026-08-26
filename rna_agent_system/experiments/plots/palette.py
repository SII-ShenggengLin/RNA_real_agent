"""Unified experiment-figure palette (user-specified, 2026-08-25 reset; rev 7).

Every experiment figure draws its colours exclusively from PALETTE below.
Rev 7: the user's earthy Morandi twelve-colour set (dusty rose / terracotta /
sand warm families + sage-green + grey-blue/mauve), supplied directly as hex
codes. Eleven of the twelve identify the workflows (#7A7672 dark warm grey
held out — reserved for neutral/dark semantics such as failed tiles); warm and
cool tones alternate on the carpet and the darkest blue (#6B7B8D) separates
the two palest warm tones.
"""
from __future__ import annotations

# The mandated palette (twelve colours as supplied; used verbatim).
PALETTE: list[str] = [
    "#B5838D",  # dusty mauve pink
    "#D3B5B0",  # pale dusty rose
    "#C08B7C",  # terracotta
    "#D9C3A9",  # sand
    "#CDBF9E",  # khaki
    "#A3B18A",  # sage green
    "#8DA290",  # grey green
    "#8FA6BB",  # grey blue
    "#6B7B8D",  # slate blue (darkest; separator)
    "#A99AAF",  # mauve grey
    "#B7B0A2",  # warm grey
    "#7A7672",  # dark warm grey (held out: reserved neutral-dark semantic)
]

PALETTE_BY_NAME: dict[str, str] = {
    "dusty_mauve_pink": "#B5838D",
    "pale_dusty_rose": "#D3B5B0",
    "terracotta": "#C08B7C",
    "sand": "#D9C3A9",
    "khaki": "#CDBF9E",
    "sage_green": "#A3B18A",
    "grey_green": "#8DA290",
    "grey_blue": "#8FA6BB",
    "slate_blue": "#6B7B8D",
    "mauve_grey": "#A99AAF",
    "warm_grey": "#B7B0A2",
    "dark_warm_grey": "#7A7672",
}

# Semantic accents reused across figures.
NEUTRAL_DARK = "#7A7672"    # failed tiles / neutral-dark categories
NEUTRAL_GRID = "#D9D9D9"    # gridlines / tile borders (non-data grey)
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

# CDS null-model arm colours (Figs 2b/2c): designed reuses the mRNA-CDS
# workflow colour (the arm IS that workflow's deliverable); sage marks
# wild-type/certified; the held-out dark warm grey marks random/null
# baselines (figure-plan null-model convention).
ARM_COLORS = {
    "designed": "#C08B7C",
    "wt": "#A3B18A",
    "random": "#7A7672",
}

# Workflow → palette colour (one distinct colour per workflow; warm and cool
# tones alternate, the slate-blue row separates the two palest warm tones).
WORKFLOW_COLORS: dict[str, str] = {
    "mrna_cds_design": "#C08B7C",                 # terracotta
    "full_length_mrna_design": "#A3B18A",         # sage green
    "mrna_sequence_scoring": "#D9C3A9",           # sand
    "sirna_design": "#6B7B8D",                    # slate blue
    "sgrna_design": "#D3B5B0",                    # pale dusty rose
    "rna_secondary_structure_design": "#8DA290",  # grey green
    "rna_tertiary_structure_design": "#B5838D",   # dusty mauve pink
    "rna_aptamer_design": "#8FA6BB",              # grey blue
    "rna_small_molecule_interaction": "#CDBF9E",  # khaki
    "aso_target_screening": "#A99AAF",            # mauve grey
    "ires_prediction": "#B7B0A2",                 # warm grey
}
