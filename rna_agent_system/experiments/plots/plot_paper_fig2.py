#!/usr/bin/env python3
"""Fig 2 (paper draft): platform produces biologically valid outputs at scale.

Decision (2026-08-10, refreshed 2026-08-11 for paper v2): REUSE the campaign
figure `experiments/plots/fig2.png` as the paper Fig 2.

v2 refresh (matches the v2 legend):
  * 210/210 tasks (legacy advisory-abort siRNA task reruns green under the
    2026-08-10 governance);
  * panel a designed arm = the `cai_only` nulls records (n=20, median CAI
    0.7454; OTC/PDGFB replaced the two oversized targets) vs WT 0.729 (n=20)
    vs random-synonymous 0.672 (n=200; WT > random p=4.0e-07);
  * NEW panel d — RNAsmol two-sided boundary (`rnasmol_boundary_panel.json`):
    in-distribution test AUROC 0.974 (ROBIN) / 0.983 (PDB), decoy true-ligand
    ranks 2/1,601 and 7/265, vs OOD short-aptamer AUROC 0.722 / 0.563 with
    CIs spanning chance. Panels after c shift one letter (13 panels, 4x4).

Panel layout (row-major):

  a  mrna_cds_design — codon optimality: CAI WT (n=20) vs random-syn (n=200)
     vs designed (n=20, median 0.745); "WT vs rand: p=4.0e-07, δ=0.69".
  b  mrna_sequence_scoring — arm ordering (WT / random-synonymous / designed).
  c  sirna_design — specificity: n=22, zero off-target 21/22.
  d  RNAsmol oracle — two-sided boundary (in-distribution vs OOD short
     aptamers; decoy ranks annotated).
  e  sgrna_design — CRGPT handle quality (nn_score histogram).
  f  rna_secondary_structure_design — inverse folding exact match 22/25 (88%).
  g  rna_tertiary_structure_design — pLDDT / recovery % (n=20), median pLDDT
     component 0.70.
  h  rna_aptamer_design — component scores (EGARPS / RhoFold / ipTM, n=18).
  i  rna_small_molecule_interaction — binder vs near-cognate vs random-chem;
     workflow-level AUROC 0.72 / 0.31 annotated "(tool boundary)".
  j  aso_target_screening — accessibility vs binding components.
  k  ires_prediction — discrimination, AUROC 0.76 [0.43, 0.98].
  l  full_length_mrna_design — junction MFE distributions.
  m  platform coverage — per-workflow task success, total 210/210.

All numbers agree with docs/PAPER_FACT_SHEET.md §2 (fig2_summary.json,
rnasmol_boundary_panel.json). This script copies the verified PNG into
`experiments/plots/paper/fig2.png` and prints the panel manifest above.

Usage (from `rna_agent_system/`):
    python experiments/plots/plot_fig2.py        # regenerate the source PNG
    python experiments/plots/plot_paper_fig2.py  # then copy it into paper/
"""
from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "fig2.png"
OUT = HERE / "paper" / "fig2.png"

PANELS = [
    ("a", "mrna_cds_design — codon optimality (CAI: designed 0.745 / WT 0.729 / "
          "random 0.672; WT vs random p=4.0e-07, Cliff's δ=0.69)"),
    ("b", "mrna_sequence_scoring — arm ordering (WT / random-syn / designed)"),
    ("c", "sirna_design — specificity (n=22; zero off-target 21/22)"),
    ("d", "RNAsmol oracle — two-sided boundary (in-distribution 0.974/0.983, "
          "decoy ranks 2/1,601 & 7/265; OOD 0.722/0.563, CIs span chance)"),
    ("e", "sgrna_design — CRGPT handle nn_score distribution"),
    ("f", "rna_secondary_structure_design — inverse folding exact 22/25 (88%)"),
    ("g", "rna_tertiary_structure_design — pLDDT & recovery % (n=20; median "
          "pLDDT comp 0.70)"),
    ("h", "rna_aptamer_design — EGARPS / RhoFold / ipTM components (n=18)"),
    ("i", "rna_small_molecule_interaction — workflow-level AUROC 0.72 / 0.31, "
          "annotated tool boundary"),
    ("j", "aso_target_screening — accessibility vs binding components"),
    ("k", "ires_prediction — known IRES vs random UTR, AUROC 0.76 [0.43, 0.98]"),
    ("l", "full_length_mrna_design — 5'UTR–CDS / CDS–3'UTR junction MFE"),
    ("m", "platform coverage — per-workflow success, total 210/210"),
]


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"legacy figure missing: {SRC}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, OUT)
    print(f"copied {SRC} -> {OUT}")
    print("panel manifest (13 panels, 4x4 grid):")
    for letter, desc in PANELS:
        print(f"  {letter}: {desc}")


if __name__ == "__main__":
    main()
