# Reference Genomes & Transcriptomes

> **Last updated**: 2026-07-04

Pre-installed reference sequences for off-target screening in siRNA / ASO / CRISPR workflows.

> **Do NOT commit `.fa` / `.fasta` / `.gz` files to git.**
> They are auto-downloaded by `download_references.py`.

---

## Quick start

```bash
cd rna_agent_system/data/references

# Download all pre-configured species
python download_references.py

# Download only specific species
python download_references.py --species homo_sapiens mus_musculus
```

---

## Pre-configured species

| Species | ID | Default file | Size (approx) | Source |
|---------|-----|-------------|---------------|--------|
| **Homo sapiens** | `homo_sapiens` | `transcripts.fa` | ~120 MB (gz: 35 MB) | GENCODE release 46 |
| **Mus musculus** | `mus_musculus` | `transcripts.fa` | ~100 MB (gz: 28 MB) | GENCODE release M36 |
| **SARS-CoV-2** | `sars_cov_2` | `genome.fa` | ~30 KB | NCBI RefSeq NC_045512.2 |
| **Danio rerio** | `danio_rerio` | `transcripts.fa` | ~80 MB (gz: 22 MB) | GENCODE release 47 |
| **Rattus norvegicus** | `rattus_norvegicus` | `transcripts.fa` | ~90 MB (gz: 25 MB) | GENCODE release M35 |

> **Note**: Only `homo_sapiens` and `sars_cov_2` are downloaded by default.
> Add `--species mus_musculus danio_rerio rattus_norvegicus` to download others.
> The canonical species IDs and display names are maintained in `agent_core/constants/species.py` (`REFERENCE_SPECIES_IDS`, `REFERENCE_SPECIES_DISPLAY_NAMES`).

---

## Evitar GenomeData compatibility

Evitar (`external_repos/Evitar/GenomeData/`) has its own `GenomeData.sh` script that downloads:
- `GRCh38.p13.genome.fa` + `gencode.v34.annotation.gtf`
- Generates `transcripts.fa` and `utrs.fa`

**Evitar's GenomeData is NOT pre-downloaded** — you must run `bash GenomeData.sh` inside Evitar's directory if you want Evitar's built-in off-target analysis to work.

This `data/references/` directory is **independent** of Evitar. It provides a unified, workflow-layer reference library that any workflow (siRNA, ASO, CRISPR) can use via `run_blastn_similarity_search`.

---

## Auto-discovery in workflow

If `transcriptome_fasta_path` is **not** explicitly provided to `SirnaDesignInput`,
the workflow automatically looks for:

```
rna_agent_system/data/references/species/<species_id>/transcripts.fa
```

Default `species_id` is `homo_sapiens`.

You can override the default species via environment variable:

```bash
export RNA_AGENT_DEFAULT_SPECIES=mus_musculus
```

Or per-workflow input:

```python
SirnaDesignInput(
    mode="generic",
    target_sequence="...",
    species="mus_musculus",   # auto-resolves transcriptome path
)
```

---

## Directory layout

```
data/references/
├── README.md
├── download_references.py
└── species/
    ├── homo_sapiens/
    │   ├── transcripts.fa
    │   └── metadata.json
    ├── mus_musculus/
    │   ├── transcripts.fa
    │   └── metadata.json
    └── ...
```

`metadata.json` records download URL, version, and timestamp for reproducibility.
