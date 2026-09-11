# RNA-BioBench: Benchmark Datasets for RNADesignAgent

> **Last updated**: 2026-09-02 (FullLength-mRNA target list corrected to the operative set; paper-section column re-based to FIGURE_PLAN_V5 lettering)

This directory contains all benchmark datasets used in the RNADesignAgent paper experiments.
For the experiment plan that consumes these datasets, see [`../../docs/MANUSCRIPT.md`](../../docs/MANUSCRIPT.md).

## Datasets Overview

| Dataset | Purpose | Size | Paper Section |
|---------|---------|------|---------------|
| `RNA-BioBench-FullLength-mRNA` | Full-length mRNA design (CDS + full-length construct campaigns) | **20 targets** (16 human + 2 *E. coli*: GFP, β-galactosidase) | Fig 2b/c, Fig 4d, Fig 5a–c |
| `RNA-BioBench-Aptamer` | RNA aptamer design (oracle-power panels + GenNav campaigns) | **20 targets** (2 with known aptamers: Thrombin/TBA, SARS-CoV-2 N) | Fig 3a–d,h, Fig 5e–h |
| `RNA-BioBench-Platform` | Biological output quality across 11 workflows | **210 tasks** | Fig 2a/2h/2i, Fig 4f |
| `RNA-BioBench-ProcessAware` | Process-level CLI regressions through the user form entries | **31 sessions** (PA_006–PA_036) | Fig 4g/4h |

## Directory Structure

```
benchmarks/
├── README.md                              # This file
├── RNA-BioBench-FullLength-mRNA/
│   ├── dataset_manifest.json
│   ├── targets/                           # 20 JSON files
│   │   ├── SARS-CoV-2_Spike_WT.json       # UniProt P0DTC2, 1273 aa
│   │   ├── Influenza_HA_H1N1.json         # UniProt P03452, 565 aa
│   │   ├── EPO.json                        # UniProt P01588, 193 aa
│   │   ├── GFP.json                        # UniProt P42212, 238 aa
│   │   ├── Luciferase.json                 # UniProt P08659, 550 aa
│   │   ├── HIV-1_Env_gp120.json            # UniProt P04578, 856 aa
│   │   ├── RSV_F_protein.json              # UniProt P03420, 574 aa
│   │   ├── OTC.json                        # UniProt P00480, 354 aa
│   │   ├── PDGFB.json                      # UniProt P01127, 241 aa
│   │   ├── HPV16_L1.json                   # UniProt P03101, 505 aa
│   │   ├── Insulin.json                    # UniProt P01308, 110 aa
│   │   ├── IFN_alpha_2a.json               # UniProt P01562, 188 aa
│   │   ├── IL-2.json                       # UniProt P60568, 153 aa
│   │   ├── HER2.json                       # UniProt P04626, 1255 aa
│   │   ├── A1AT.json                       # UniProt P01009, 418 aa
│   │   ├── Transferrin.json                # UniProt P02787, 698 aa
│   │   ├── Albumin.json                    # UniProt P02768, 609 aa
│   │   ├── Beta_galactosidase.json         # UniProt P00722, 1024 aa
│   │   ├── Growth_hormone.json             # UniProt P01241, 217 aa
│   │   └── Ovalbumin.json                  # UniProt P01012, 386 aa
│   └── sequences/                          # 20 FASTA files
│
├── RNA-BioBench-Aptamer/
│   ├── dataset_manifest.json
│   ├── targets/                            # 20 JSON files
│   │   ├── SARS-CoV-2_Nucleocapsid.json    # PDB 6M3M, UniProt P0DTC9, 419 aa
│   │   ├── Thrombin.json                   # PDB 1HAO, UniProt P00734, 622 aa
│   │   ├── GFP.json                        # PDB 1GFL, UniProt P42212, 238 aa
│   │   ├── VEGF.json                       # PDB 1VPF, UniProt P15692, 395 aa
│   │   ├── Lysozyme.json                   # PDB 6LYZ, UniProt P61626, 148 aa
│   │   ├── Streptavidin.json               # PDB 1STP, UniProt P22629, 183 aa
│   │   ├── RNase_A.json                    # PDB 7RSA, UniProt P61823, 150 aa
│   │   ├── TNF_alpha.json                  # PDB 1TNF, UniProt P01375, 233 aa
│   │   ├── Carbonic_anhydrase_II.json      # PDB 1CA2, UniProt P00918, 260 aa
│   │   ├── Trypsin.json                    # PDB 1MCT, UniProt P07477, 247 aa
│   │   ├── BSA.json                        # PDB 3V03, UniProt P02769, 607 aa
│   │   ├── Myoglobin.json                  # PDB 1MBO, UniProt P02192, 154 aa
│   │   ├── Subtilisin.json                 # PDB 1ST2, UniProt P00782, 382 aa
│   │   ├── MBP.json                        # PDB 1ANF, UniProt P0AEX9, 396 aa
│   │   ├── Cytochrome_c.json               # PDB 1HRC, UniProt P99999, 105 aa
│   │   ├── Ferritin.json                   # PDB 1FHA, UniProt P02792, 175 aa
│   │   ├── Chymotrypsinogen.json           # PDB 2CGA, UniProt P00766, 245 aa
│   │   ├── Concanavalin_A.json             # PDB 3CNA, UniProt P02866, 290 aa
│   │   ├── Pepsin.json                     # PDB 5PEP, UniProt P00791, 385 aa
│   │   └── Papain.json                     # PDB 9PAP, UniProt P00784, 345 aa
│   └── structures/                         # 20 PDB files
│
├── RNA-BioBench-Platform/
│   ├── dataset_manifest.json
│   └── tasks/
│       ├── 01_mrna_cds_design/            # 19 tasks
│       ├── 02_full_length_mrna_design/    # 22 tasks
│       ├── 03_mrna_sequence_scoring/      # 13 tasks
│       ├── 04_sirna_design/               # 22 tasks
│       ├── 05_sgrna_design/               # 30 tasks
│       ├── 06_rna_secondary_structure/    # 25 tasks
│       ├── 07_rna_tertiary_structure/     # 20 tasks
│       ├── 08_rna_aptamer_design/         # 18 tasks
│       ├── 09_rna_small_molecule/         # 15 tasks
│       ├── 10_aso_target_screening/       # 14 tasks
│       └── 11_ires_prediction/            # 12 tasks
│
└── RNA-BioBench-ProcessAware/
    └── task_set_for_llm_comparison.json   # 26 tasks + 6 LLM configs
```

## Data Sources

All protein sequences are downloaded from **UniProt** (https://www.uniprot.org) via the REST API.
All protein structures are downloaded from **RCSB PDB** (https://www.rcsb.org) via the download service.

| Target | UniProt | PDB | NCBI |
|--------|---------|-----|------|
| SARS-CoV-2 Spike | P0DTC2 | — | NC_045512.2 |
| Influenza HA (H1N1) | P03452 | — | — |
| EPO | P01588 | — | — |
| GFP | P42212 | 1GFL | — |
| Luciferase | P08659 | — | — |
| HIV-1 Env gp120 | P04578 | — | — |
| RSV F protein | P03420 | — | — |
| Zika E protein | Q32ZE1 | — | — |
| HPV16 L1 | P03101 | — | — |
| Insulin | P01308 | — | — |
| Factor VIII | P00451 | — | — |
| IFN-alpha-2a | P01563 | — | — |
| IL-2 | P60568 | — | — |
| HER2 | P04626 | — | — |
| A1AT | P01009 | — | — |
| Transferrin | P02787 | — | — |
| Albumin | P02768 | — | — |
| Beta-galactosidase | P00722 | — | — |
| Growth hormone | P01241 | — | — |
| Ovalbumin | P01012 | — | — |
| SARS-CoV-2 Nucleocapsid | P0DTC9 | 6M3M | — |
| Thrombin | P00734 | 1HAO | — |
| VEGF | P15692 | 1VPF | — |
| Lysozyme | P61626 | 6LYZ | — |
| Streptavidin | P22629 | 1STP | — |
| RNase A | P61823 | 7RSA | — |
| TNF-alpha | P01375 | 1TNF | — |
| Carbonic anhydrase II | P00918 | 1CA2 | — |
| Trypsin | P07477 | 1MCT | — |
| BSA | P02769 | 3V03 | — |
| Myoglobin | P02192 | 1MBO | — |
| Subtilisin | P00782 | 1ST2 | — |
| MBP | P0AEX9 | 1ANF | — |
| Cytochrome c | P99999 | 1HRC | — |
| Ferritin | P02792 | 1FHA | — |
| Chymotrypsinogen | P00766 | 2CGA | — |
| Concanavalin A | P02866 | 3CNA | — |
| Pepsin | P00791 | 5PEP | — |
| Papain | P00784 | 9PAP | — |

## Schema Versioning

Each dataset includes a `schema_version` field in its manifest. Current versions:

| Dataset | Schema Version |
|---------|---------------|
| RNA-BioBench-FullLength-mRNA | 1.1.0 |
| RNA-BioBench-Aptamer | 1.1.0 |
| RNA-BioBench-Platform | 2.0.0 |
| RNA-BioBench-ProcessAware | 1.20.0 |

### Known legacy naming (registered 2026-09-11)

- `RNA-BioBench-Platform/tasks/04_sirna_design/04_sirna_design_013_blast_identity_70.json`: the task id and `description` predate the platform default and are retained verbatim because the frozen Exp-6 records embed the description byte-for-byte. The bowtie2 score floor `G,10,4` is the platform default (`agent_core/workflows/sirna_design.py`), not a task-specific strict threshold, and "identity-70" is only an analogy with the BLAST `perc_identity` floor. The task's actual edge character is its synthetic target — a verbatim 86-nt fragment of the segmentally duplicated human lncRNA locus DDX11L2/DDX11L16; see the task JSON's `legacy_name_note` field and the Exp-6 frozen records.

## Citation

If you use these datasets, please cite the RNADesignAgent paper (in preparation):

> A multi-agent system for RNA design with capability-gated prediction and constraint-navigated generation

## License

The benchmark datasets are released under the same license as the RNADesignAgent project.
Protein sequences are from UniProt (CC BY 4.0) and PDB structures are from RCSB PDB.

## PA static fixtures (`RNA-BioBench-ProcessAware/fixtures/`, 2026-08-18)

Regression-benchmark input assets referenced by `pa_benchmarks.json`. They
previously lived untracked under `workspace/` and were lost in a workspace
clean; rebuilt 2026-08-18 from NCBI records and the local Evitar test genomes,
now git-tracked:

| File | Contents | Provenance |
|------|----------|------------|
| `ns1_strains.fasta` | Dengue NS1 gene, 4 serotype references + the PA_006 query isolate | `NC_001477.1` / `NC_001474.2` / `NC_001475.1` / `NC_002640.1` mat_peptide "nonstructural protein NS1" (1056 nt each), efetch 2026-08-18 |
| `sarscov2_nsp12_strains.fasta` | SARS-CoV-2 nsp12 (RdRp) CDS, Wuhan-Hu-1 + 7 early-2020 isolates + the PA_016 query | `NC_045512.2` genome 13442..16236 (2795 nt, direct ORF1ab slice — the GenBank mat_peptide join overlaps 1 nt at the frameshift and must not be used verbatim); isolates from `external_repos/Evitar/test/strains.fa` extracted at the conserved nsp12 start anchor |
| `epo_mrna.fa` | Human EPO mRNA (1340 nt) | `NM_000799.3`, efetch 2026-08-18 |
| `ttr_mrna.fa` | Human TTR mRNA (616 nt) | `NM_000371.4`, efetch 2026-08-18 |
| `emcv_5utr.fa` | EMCV 5'UTR (840 nt, IRES-positive) | batch-B fixture (2026-08-19), single record extracted from `external_anchors/ires/ires_positive.fa` (`NC_001479.1:1-840`) |
| `poliovirus_5utr.fa` | Poliovirus type 1 5'UTR (742 nt, IRES-positive) | batch-B fixture (2026-08-19), single record extracted from `external_anchors/ires/ires_positive.fa` (`NC_002058.3:1-742`) |
