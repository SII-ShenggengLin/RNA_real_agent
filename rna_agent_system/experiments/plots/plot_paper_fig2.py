#!/usr/bin/env python3
"""Fig 2 (paper draft): platform produces biologically valid outputs at scale.

Decision (2026-08-10): REUSE the legacy campaign figure
`experiments/plots/fig2.png` as the paper Fig 2.

Rationale: visual inspection of the legacy figure shows a 3x4 panel grid whose
content matches the new-paper narrative one-to-one, with no stale BMC-era
annotation in any panel title:

  a  mrna_cds_design — codon optimality: CAI WT 0.730 (n=20) vs random-syn
     0.674 (n=220) vs CAI-only (n=18) vs designed (n=18, median 0.744);
     "WT vs rand: p=5.6e-07, d=0.68".
  b  mrna_sequence_scoring — arm ordering (WT / random-synonymous / CAI-only).
  c  sirna_design — specificity: n=21, zero off-target 20/21; one correct
     QualityAgent abort (governance case).
  d  sgrna_design — CRGPT handle quality (rn_score histogram).
  e  rna_secondary_structure_design — inverse folding exact match 22/25 (88%).
  f  rna_tertiary_structure_design — pLDDT / recovery % (n=20), median pLDDT
     component 0.70.
  g  rna_aptamer_design — component scores (EGARPS / RhoFold / ipTM, n=18).
  h  rna_small_molecule_interaction — binder vs near-cognate vs random-chem;
     AUROC 0.50 / 0.31 annotated "(tool boundary)".
  i  aso_target_screening — accessibility vs binding components.
  j  ires_prediction — discrimination, AUROC 0.76 [0.43, 0.98].
  k  full_length_mrna_design — junction MFE distributions.
  l  platform coverage — per-workflow task success, total 209/210.

All numbers agree with docs/PAPER_FACT_SHEET.md §2 (fig2_summary.json), and
panel (h) already carries the honest "tool boundary" framing the new narrative
requires. This script therefore copies the verified PNG into
`experiments/plots/paper/fig2.png` and prints the panel manifest above.

Usage (from `rna_agent_system/`):
    python experiments/plots/plot_paper_fig2.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "fig2.png"
OUT = HERE / "paper" / "fig2.png"

PANELS = [
    ("a", "mrna_cds_design — codon optimality (CAI: designed 0.744 / WT 0.730 / "
          "random 0.674; WT vs random p=5.6e-07, Cliff's d=0.68)"),
    ("b", "mrna_sequence_scoring — arm ordering (WT / random-syn / CAI-only)"),
    ("c", "sirna_design — specificity (n=21; zero off-target 20/21; 1 correct "
          "QualityAgent abort)"),
    ("d", "sgrna_design — CRGPT handle rn_score distribution"),
    ("e", "rna_secondary_structure_design — inverse folding exact 22/25 (88%)"),
    ("f", "rna_tertiary_structure_design — pLDDT & recovery % (n=20; median "
          "pLDDT comp 0.70)"),
    ("g", "rna_aptamer_design — EGARPS / RhoFold / ipTM components (n=18)"),
    ("h", "rna_small_molecule_interaction — AUROC 0.50 / 0.31, annotated tool "
          "boundary"),
    ("i", "aso_target_screening — accessibility vs binding components"),
    ("j", "ires_prediction — known IRES vs random UTR, AUROC 0.76 [0.43, 0.98]"),
    ("k", "full_length_mrna_design — 5'UTR–CDS / CDS–3'UTR junction MFE"),
    ("l", "platform coverage — per-workflow success, total 209/210"),
]


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"legacy figure missing: {SRC}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, OUT)
    print(f"copied {SRC} -> {OUT}")
    print("panel manifest (12 panels, 3x4 grid):")
    for letter, desc in PANELS:
        print(f"  {letter}: {desc}")


if __name__ == "__main__":
    main()
