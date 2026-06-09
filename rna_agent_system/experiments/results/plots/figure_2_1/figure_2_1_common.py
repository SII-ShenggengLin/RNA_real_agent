#!/usr/bin/env python3
"""
Figure 2.1 — Shared configuration and utilities for all panels.

This module centralises workflows, group mappings, colour palettes, and
plotting styles so that Panels (c), (d), and future panels stay consistent.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# ───────────────────────────────────────────────
# Base directory for platform-coverage data
# ───────────────────────────────────────────────
BASE_DIR = Path(
    "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent"
    "/rna_agent_system/experiments/results/platform_coverage_by_workflow"
)

# ───────────────────────────────────────────────
# Workflow order (used as X-axis category order)
# ───────────────────────────────────────────────
WORKFLOWS = [
    "mrna_cds_design", "full_length_mrna_design", "mrna_sequence_scoring",
    "sirna_design", "sgrna_design", "aso_target_screening",
    "rna_secondary_structure_design", "rna_tertiary_structure_design",
    "rna_aptamer_design", "rna_small_molecule_interaction", "ires_prediction",
]

# ───────────────────────────────────────────────
# Biological group mapping
# ───────────────────────────────────────────────
GROUP_MAP = {
    "mrna_cds_design": "mRNA Therapeutics Development",
    "full_length_mrna_design": "mRNA Therapeutics Development",
    "mrna_sequence_scoring": "mRNA Therapeutics Development",
    "sirna_design": "Gene Silencing & Editing",
    "sgrna_design": "Gene Silencing & Editing",
    "aso_target_screening": "Gene Silencing & Editing",
    "rna_secondary_structure_design": "RNA Structural Engineering",
    "rna_tertiary_structure_design": "RNA Structural Engineering",
    "rna_aptamer_design": "Functional RNA Discovery",
    "rna_small_molecule_interaction": "Functional RNA Discovery",
    "ires_prediction": "Functional RNA Discovery",
}

GROUP_COLORS = {
    "mRNA Therapeutics Development": "#B5C4B1",
    "Gene Silencing & Editing": "#8B9DAF",
    "RNA Structural Engineering": "#D8A7A7",
    "Functional RNA Discovery": "#D8C4A7",
}

# ───────────────────────────────────────────────
# Short display names for X-axis labels
# ───────────────────────────────────────────────
SHORT_NAMES = {
    "mrna_cds_design": "mRNA CDS Design",
    "full_length_mrna_design": "Full-length mRNA Design",
    "mrna_sequence_scoring": "mRNA Scoring",
    "sirna_design": "siRNA Design",
    "sgrna_design": "sgRNA Design",
    "aso_target_screening": "ASO Design",
    "rna_secondary_structure_design": "2D Structure Inverse Folding",
    "rna_tertiary_structure_design": "3D Structure Inverse Folding",
    "rna_aptamer_design": "Aptamer Design",
    "rna_small_molecule_interaction": "RNA-Small Molecule Interaction Prediction",
    "ires_prediction": "IRES Prediction",
}

# ───────────────────────────────────────────────
# Morandi colour palette
# ───────────────────────────────────────────────
MORANDI_COLORS = [
    "#8B9DAF", "#B5C4B1", "#D4C4B7", "#C9B8A8", "#A8B5A0",
    "#D8A7A7", "#A7B8D8", "#C4B7D8", "#D8C4A7", "#A0A0A0",
    "#B8D4C8",
]

# ───────────────────────────────────────────────
# Global Matplotlib style
# ───────────────────────────────────────────────
def setup_mpl_style(grid: bool = False) -> None:
    """Apply the unified Morandi-style rcParams used across Figure 2.1."""
    plt.rcParams.update({
        "figure.facecolor": "#FAFAFA",
        "axes.facecolor": "#FAFAFA",
        "axes.edgecolor": "#333333",
        "axes.labelcolor": "#333333",
        "text.color": "#333333",
        "xtick.color": "#555555",
        "ytick.color": "#555555",
        "grid.color": "#E0E0E0",
        "grid.linewidth": 0.8,
        "axes.grid": grid,
        "axes.axisbelow": True,
        "legend.frameon": True,
        "legend.facecolor": "#FAFAFA",
        "legend.edgecolor": "#CCCCCC",
        "font.size": 10,
        "axes.titlesize": 14,
        "axes.labelsize": 11,
    })


# ───────────────────────────────────────────────
# Data-loading helpers
# ───────────────────────────────────────────────
def load_raw_records(workflow: str) -> list[dict]:
    """Load raw JSONL records for a single workflow."""
    path = BASE_DIR / workflow / "raw" / f"platform_coverage_{workflow}.jsonl"
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_all_records() -> pd.DataFrame:
    """Load all raw records from all workflows into a single DataFrame."""
    rows = []
    for wf in WORKFLOWS:
        for rec in load_raw_records(wf):
            rec["workflow"] = wf
            rec["group"] = GROUP_MAP.get(wf, "Other")
            rows.append(rec)
    return pd.DataFrame(rows)
