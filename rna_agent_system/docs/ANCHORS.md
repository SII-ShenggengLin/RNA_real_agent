# External Anchors — Directory Spec & Curation Script Pattern

> Canonical spec for `data/benchmarks/external_anchors/` and its generator scripts.
> Templates: `experiments/curate_e1_anchor_set.py` (pilot) and
> `experiments/curate_e1_anchor_set_v2.py` (extension — the reference implementation).
> Created 2026-08-04 (W3–4 milestone: anchor infrastructure consolidation).

## 1. Directory layout

```
data/benchmarks/external_anchors/
├── SOURCES.md                  # provenance & validation ledger for every set (manual sections)
├── aptamers/
│   ├── known_aptamers.json     # small manual anchors (TBA, SARS-CoV-2 N)
│   ├── pegaptanib.json         # single-anchor detail file
│   ├── calibration_set.json    # P2 calibration anchor set (generated)
│   ├── e1_anchor_set.json      # E1 pilot: 29 entries, 3 targets (generated)
│   ├── e1_anchor_set_v2.json   # E1 extension: 66 entries, 6 targets (generated)
│   ├── proteins/               # target protein fastas consumed by the profiling driver
│   │   ├── <target>.fa         # mature-chain / construct used for scoring
│   │   └── <target>_full.fa    # full-length UniProt fetch (source material, asserted parent)
│   └── structures/             # docking-anchor PDB files, lowercased (<pdb_id>.pdb)
├── wt_cds/                     # one wild-type CDS fasta per Fig-3 target
├── ires/                       # ires_positive.fa + utr_negative.fa panels
├── small_molecule/             # pairs.json (binder / non-binder ligand pairs)
├── utr_mrl/                    # e7_mrl_anchor_set.json — E7 measured-MRL anchors (generated)
└── vaccine_mrna/               # BNT162b2 / mRNA-1273 assembled contigs
```

Rules:

- **Generated sets are never hand-edited.** If the JSON is wrong, fix the generator
  and re-run it. Manual sets (`known_aptamers.json`, `pegaptanib.json`) are the
  exception and are logged as such in `SOURCES.md`.
- Every set, protein fasta, and structure must have a `SOURCES.md` entry stating
  origin, fetch date, and validation status.
- PDB files are stored lowercased (`4dii.pdb`); references in anchor JSONs use the
  uppercase PDB id.

## 2. Anchor-set JSON schema

Top level (`e1_anchor_set_v2.json` is the superset):

| Key | Required | Content |
|-----|----------|---------|
| `description` | yes | one-paragraph scope statement |
| `curated` | yes | ISO date |
| `convention` | yes | scoring convention (e.g. "DNA aptamers scored as RNA via T->U") |
| `preregistration` | yes | pointer to the pre-registration (driver docstring / design doc section) |
| `extends` | extension sets | the parent set carried over verbatim |
| `rejected_candidates` | recommended | name → reason registry of considered-and-rejected targets/entries |
| `n_entries` | yes | asserted equal to `len(entries)` |
| `docking_anchors` | yes (may be empty) | native-complex anchors for docking power |
| `docking_not_available` | yes | target → why docking is N/A (RCSB verification + date) |
| `known_limitations` | yes | registered caveats (assay mixing, in-silico negatives, resolution, …) |
| `entries` | yes | list of entry objects |

Entry object:

| Field | Required | Content |
|-------|----------|---------|
| `id` | yes | snake_case unique id, target-suffixed (e.g. `n_tnsp9`) |
| `name` | yes | human-readable, includes the salient caveat |
| `target` | yes | canonical target name (drives per-target grouping) |
| `protein` | yes | `{type: benchmark_pdb, pdb_id, chain}` or `{type: uniprot_fasta, uniprot, range, fasta}` |
| `sequence` | yes | as-printed (DNA or RNA); derivations asserted, see §3 |
| `alphabet` | yes | `dna` / `rna` |
| `length_nt` | yes | generator computes `len(sequence)` — never typed by hand |
| `kd_nm` | nullable | null for `negative` / `binder_no_kd` |
| `role` | yes | `binder` / `binder_no_kd` / `negative` |
| `reference` | yes | pinpoint citation (paper + table/figure + assay) |
| `kd_method` | recommended | assay + how the stored value was obtained (incl. computed Kd = kd/ka) |
| `sequence_verification` | recommended | how the sequence was checked (printout equality, derivation, nesting) |
| `ranking_eligible` | v2+ | same-assay ranking subset flag; ranking analyses MUST filter on it |

Docking anchor object: `aptamer_entry` (entry id), `target`, `pdb_id`,
`aptamer_chain`, `protein_chains`, `method` (incl. resolution), `reference`,
`notes` (resolution caveats, missing residues, modification handling).

## 3. Curation script pattern (assertion-first)

The v2 generator's assertion pattern caught three real transcription errors
(AptAF42 length misreading, tNSP9/10 parent-row offset, Seq15_12_35 literal
typo). It is mandatory for new sets:

1. **Docstring = audit trail.** Pinpoint sources (table/figure-level), derivation
   notes, registered print-vs-text deviations, and the rejected-candidates list
   with reasons. State the usage command.
2. **Derive, don't duplicate.** Truncates/mutants are computed from the parent
   sequence in code (`_mutate`, slicing) and asserted equal to the printed
   sequence. Never store two independent literals for related sequences.
3. **Internal-consistency assertions before assembly:** nested-family substring
   checks, derived length == text length (`69 nt == '69 nucleotide long'`),
   truncate⊆parent nesting, cross-checks against PDB SEQRES / independent
   literature prints.
4. **Guard assertions against known-wrong sequences** circulating in the
   literature (e.g. the PSMA-A9-crosstalk "RB006" string) — one negative
   assertion per documented hazard.
5. **Pre-registered coverage check at write time:** per target
   `≥4` kd-binders and `≥3` negatives, asserted after assembly.
6. **Deterministic in-silico negatives:** fixed-seed RNG, seed recorded in the
   entry's `reference`; literature-validated non-binders preferred where they
   exist.
7. **Extension sets carry the parent verbatim** (`entries` list copied, equality
   asserted) and only add fields; pilot defaults of downstream drivers unchanged.
8. **Protein fastas generated, not fetched by hand:** mature chain sliced from the
   full UniProt fasta in the generator, with `len == range` and substring
   assertions.
9. **Generator is deterministic end-to-end** — re-running it must reproduce the
   JSON byte-for-byte (modulo formatting).

## 4. Sequence verification discipline (carried from PIVOT §3.13)

- **Figure-only sequences are excluded.** Text/table printouts only; when a value
  exists only as a range in text and individual values are figure-only, use
  `role=binder_no_kd` with the range in `kd_method`.
- **Two-pass verification:** new entries verified against Europe PMC / RCSB /
  publisher PDFs; verification material cached under `experiments/lit_cache/`.
- **Print-vs-text discrepancies are registered, not "fixed"** — store the printed
  sequence as-is and record the deviation in `sequence_verification` and
  `known_limitations`.
- **Cross-assay Kd values are not silently mixed into ranking** — mark the
  same-assay subset `ranking_eligible=True`; transcribed-citation Kd values are
  excluded (`ranking_eligible=False`).

## 5. Checklist for a new anchor set

1. Copy the nearest generator as the template; write the docstring first
   (sources, rejections, usage).
2. Encode sequences as literals/derivations with the §3 assertions.
3. Register `rejected_candidates` for everything considered and dropped.
4. Run the generator; confirm the coverage assertions print per-target counts.
5. Add a `SOURCES.md` section (copy the e1_anchor_set_v2 section style).
6. If the set feeds a profiling driver, keep pilot defaults untouched — add
   `--anchor-set`-style parameters instead of changing defaults.
