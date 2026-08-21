# Layer-0 tool audit on fresh data (2026-08-21)

**Question**: can every Layer-0 tool be invoked correctly, tested on data
created the same day (no reuse of existing fixtures/benchmarks)?

**Answer**: after four fixes, **42/42 registered tools (41 scientific + 1
demo connectivity tool) callable and behaving correctly**. Phase 1: 35/41 production calls passed with fresh
data on first attempt; phase 2 re-verified every fix: 12/12 PASS.

## Fresh inputs (all created 2026-08-21)

- **Sequences**: yeast tRNA^Phe (76 nt, typed from canonical knowledge —
  independently confirmed: RhoDesign's sanitizer recovers the identical
  sequence from 1EHZ coordinates), human ubiquitin (76 aa) + insulin A/B
  chains back-translated with seeded human codon choice (384-nt poly-CDS),
  hsa-miR-21-5p with a synthetic perfect-complement target, seeded UTRs
  (63 nt Kozak 5'UTR, 150 nt AU-rich 3'UTR), 21-nt siRNA duplex, 40-nt
  aptamer-like RNA, 25-nt BLAST probe + 6-entry subject mini-transcriptome,
  CRISPR 23-mer (spacer+NGG from the fresh CDS) + mismatch off-targets,
  sgRNA handle seed (20-nt spacer + SpCas9 scaffold, 103 nt), caffeine
  SMILES (PubChem canonical).
- **Structures**: live RCSB downloads 1EHZ (tRNA^Phe, PDB + CIF), 1HEL
  (hen lysozyme), 1URN (U1A–U1 snRNA hairpin complex, 3 copies) — none of
  the three previously present in the repo.
- Location: `workspace/tool_layer_audit_2026-08-21/fresh_inputs/` (generator:
  `make_fresh_inputs.py` in the same directory). Kept outside `experiments/`
  so the tool-inventory AST scan is not perturbed.

## Defects found & fixed

| # | Where | Defect | Evidence | Fix |
|---|-------|--------|----------|-----|
| 1 | `analyze_rna_protein_interface` | buried SASA = (two chains) − (whole file) ≤ 0 for any multi-chain PDB; salt-bridge detector paired protein Asp/Glu against protein Arg/Lys — impossible across protein-RNA, so salt_bridges ≡ 0; `logging` used without import; 3.5/4.0 Å cutoff comment/code mismatch | 1URN (58 contacts, 32 H-bonds) reported buried_sasa 0.0 / salt_bridges 0 → after fix 1771.6 Å² / 2 | SASA on extracted single-/two-chain temp PDBs; salt bridge = Arg/Lys/His N ≤ 4 Å from OP1/OP2 per residue pair; imports/cutoff corrected |
| 2 | `extract_rna_sequence_from_cif` | modified nucleotides are hetero in mmCIF and were skipped despite the documented "render as N + warn" contract → sequences silently shortened/shifted | 1EHZ came back ~62 nt, zero warnings → after fix 76 nt with N at 14 mod positions + full warnings | keep hetero residues carrying O2' |
| 3 | `predict_rna_protein_complex_with_proteinx` | only the last FASTA line was sent (multi-line FASTA truncated to ~16 nt) | 76 aa/nt files reached the service as 16-char fragments; mean pLDDT 79.6 (truncated) → 81.9 (full) | join via `_extract_sequence` |
| 4 | CRISOT `/spec` (service) | accepted rows of any length — 20-nt spacers silently scored while `/score` enforces 23 nt | 20-nt CSV returned crisot_spec 0.798 in phase 1; negative control after fix → row-numbered 400; 23-nt results bit-identical | per-row 23-nt (spacer+PAM) validation + normalization |
| + | RhoDesign (service) | upstream length assertion crashes on any crystal PDB with waters/ions/mods (1EHZ: 602 residues vs 245 coordinate groups) | phase-1 500 error → after fix designs 76-nt sequence ≈ native tRNA^Phe | PDB sanitizer (drop non-nucleotide HETATM/altlocs, map mods to parent bases) |

Non-bugs (my test data, fixed and retested in phase 2): 20-nt input to CRISOT
score (23 nt required), 9/7-nt UTRs to GEMORNA predicts (≥10 nt required),
20-nt spacer to CRGPT design (40–120 nt handle required) — all rejected with
clear messages, i.e. correct defensive behavior.

## Files

- Phase 1 report: `tool_audit_report.json` (42 calls incl. demo; per-call
  success/elapsed/payload preview/error)
- Phase 2 report: `tool_audit_phase2.json` (12 verdicts incl. 1 negative control)
- Drivers + inputs + logs: `workspace/tool_layer_audit_2026-08-21/`
- Regression tests: `tests/test_tool_layer_fixes_2026_08_21.py` (5 tests;
  suite 539 passed)
- CHANGELOG: `docs/CHANGELOG.md` 2026-08-21 audit entry
