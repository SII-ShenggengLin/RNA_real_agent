# Change Log: LinearDesign C++ JUNCTION-PATCH (local, 2026-08-04)

> **Scope**: local patch to the `external_repos/LinearDesign` submodule (not
> upstreamed). Additive: the legacy 4-argument invocation is byte-for-byte
> preserved.
> **Binary**: rebuild with `cd external_repos/LinearDesign && make` →
> `bin/LinearDesign_2D`. Pre-patch backup: `/tmp/LinearDesign_2D_prepatch`
> (ephemeral).

## Motivation

P1 v2 NO-GO (`experiments/results/p1_v2_stability_sweep_summary.json`): post-hoc
junction repair cannot control global stability. Design decision (2026-08-04,
REDESIGN §3 E4): move the junction term **into the generation objective** of
LinearDesign.

## Changed files (all under `external_repos/LinearDesign/src/`)

| File | Markers | Content |
|------|---------|---------|
| `linear_design.cpp` | 9 | CLI argument parsing, flank validation/normalization, pseudo-codon machinery, junction-window setup, flank-mode output (`CDS sequence:` / `CDS CAI:` lines), CDS-region final check |
| `beam_cky_parser.cc` | 11 | 10 forward-CKY hook points (hairpin closure/extension, multi-loop closure, stacking, left/right bulge, 4× internal loop) + penalty baked into the precomputed special-hairpin table |
| `backtrace_iter.cc` | 9 | Backtrace mirrors of the forward hook points (same pair-forming transitions) |
| `beam_cky_parser.h` | 3 | `set_junction_penalty` configuration, `junction_pair_penalty(i, j)` helper, penalty state |

Every change site carries a `// JUNCTION-PATCH (2026-08)` comment
(32 markers total).

## New CLI contract

```
LinearDesign_2D lambda verbose codon_usage.csv [w_jun flank5_rna flank3_rna window_nt]
```

- `argc ∈ {4, 5, 7, 8}`; argc == 4 is the legacy path (untouched).
- `argv[4]` = `w_jun` (kcal/mol per window-touching pair), `argv[5]` = 5' flank
  RNA, `argv[6]` = 3' flank RNA, `argv[7]` = junction window half-width (nt).
- Flanks are validated (uppercase, T→U, ACGU only, length a multiple of 3) and
  prepended/appended to the protein as **pseudo-codons**: each flank nucleotide
  triplet is encoded as a fixed "amino acid" letter whose only allowed codon is
  that triplet, so the flanks join the global fold as fixed sequence while the
  CDS codons remain optimizable.

## Energy / sign convention

- Internal score units are 0.01 kcal/mol and the CKY search **maximizes**
  score; printed energy = `score / -100`.
- Penalty application: `newscore -= llround(w_jun * 100)` for each newly formed
  pair with at least one endpoint in a junction window (direction verified
  empirically: higher w_jun → fewer window pairs).
- Consequently the printed `mfe` in flank mode is the **CKY objective value**
  = thermodynamic MFE + `w_jun × (window pair count)`; the thermodynamic MFE
  is recovered service-side as `mfe − w_jun × count` (`mfe_thermo`).

## Regression evidence

- `argc == 4` legacy mode: output byte-for-byte identical to the pre-patch
  binary (verified 2026-08-04 before deployment).
- Live endpoint cross-check: 30 aa protein + 21 nt flanks, w_jun = 1 →
  service result identical to direct binary invocation
  (`junction_window_pair_count = 33`, `mfe = −68.4`, `mfe_thermo = −101.4`).
- Full agent-core suite after integration: pytest 587 passed, 1 skipped.

## Acceptance status

P2 pre-registered acceptance (72 cells): **NO-GO** — see
`experiments/results/junction_integrated_optimizer_summary.json` and
`docs/tools/design_mrna_cds_junction_aware_with_lineardesign.md` §7. The patch
behaves as designed (window pairs are suppressed in the global fold) but the
workflow's fragment-fold burial metric is not repaired (penalty/metric
coordinate mismatch).
