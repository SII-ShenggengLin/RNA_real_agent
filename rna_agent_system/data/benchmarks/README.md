# RNA-BioBench: Benchmark Datasets for RNADesignAgent

> **Last updated**: 2026-07-17

This directory contains all benchmark datasets used in the RNADesignAgent paper experiments.
For the experiment plan that consumes these datasets, see [`../../docs/MANUSCRIPT.md`](../../docs/MANUSCRIPT.md).

## Datasets Overview

| Dataset | Purpose | Size | Paper Section |
|---------|---------|------|---------------|
| `RNA-BioBench-FullLength-mRNA` | Type-I BMC core experiments (full-length mRNA design) | **20 targets** | Fig 3 |
| `RNA-BioBench-Aptamer` | Type-II BMC core experiments (RNA aptamer design) | **20 targets** (2 with known aptamers: Thrombin/TBA, SARS-CoV-2 N) | Fig 4 |
| `RNA-BioBench-Platform` | Biological output quality across 11 workflows | **210 tasks** | Fig 2 |
| `RNA-BioBench-ProcessAware` | Cross-LLM process-metric behavior analysis | **26 tasks** (PA_001–PA_026) × 6 LLM backends | Fig 6 |

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
│   │   ├── Zika_E_protein.json             # UniProt Q32ZE1, 3419 aa
│   │   ├── HPV16_L1.json                   # UniProt P03101, 505 aa
│   │   ├── Insulin.json                    # UniProt P01308, 110 aa
│   │   ├── Factor_VIII.json                # UniProt P00451, 2351 aa
│   │   ├── IFN_alpha_2a.json               # UniProt P01563, 188 aa
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

## Citation

If you use these datasets, please cite the RNADesignAgent paper (in preparation):

> RNADesignAgent: a tool-first agent platform for RNA design with bounded multi-module coordination

## License

The benchmark datasets are released under the same license as the RNADesignAgent project.
Protein sequences are from UniProt (CC BY 4.0) and PDB structures are from RCSB PDB.
