# CRISOT Integration Notes

## What Was Added

- Upstream repository added at `rna_agent_system/external_repos/CRISOT` as a git submodule.
- New microservice added at `rna_agent_system/microservices/crisot_service/`.
- Agent-side tools and routing now support CRISOT-based CRISPR requests.

## Supported Agent Capabilities

- `CRISOT score`
  - single sgRNA-target pair scoring
- `CRISOT spec`
  - specificity calculation from a CSV file with `On` / `Off` columns
- `CRISOT off-spec`
  - genome-wide specificity calculation through Cas-OFFinder
- `CRISOT optimize`
  - single-guide optimization through CRISOT-Opti

## Important Engineering Choice

The upstream `CRISOT.py` imports `utils.py` at module import time, and `utils.py` hard-imports `xgboost`.
That means even the lightweight `score` command fails if `xgboost` is absent.

This project's `crisot_service` avoids that problem by calling the lower-level
`crisot_modules.py` runtime directly for `score/spec/off-spec/optimize`.

## Linux Deployment Checklist

1. Pull the repo with submodules:

```bash
git pull
git submodule update --init --recursive
```

2. Create the CRISOT service environment:

```bash
cd rna_agent_system/microservices/crisot_service
conda env create -f environment.yml
```

3. Install `cas-offinder` and ensure it is available in `PATH` if you want `/off-spec` or `/optimize`.

4. Prepare a reference genome FASTA on the Linux server for `/off-spec` or `/optimize`.

5. Start the service:

```bash
bash start.sh
```

6. Verify health:

```bash
curl http://127.0.0.1:8011/health
```

## Example Requests

Single-pair score:

```json
{
  "sgrna": "GAGTCCGAGCAGAAGAAGAANGG",
  "target_sequence": "GAGTCCGAGCAGAAGAAGAANGG"
}
```

CSV spec:

```json
{
  "csv_path": "rna_agent_system/external_repos/CRISOT/example/example.csv",
  "on_item": "On",
  "off_item": "Off"
}
```

Genome-wide off-spec:

```json
{
  "sgrna": "GAGTCCGAGCAGAAGAAGAANGG",
  "target_sequence": "GAGTCCGAGCAGAAGAAGAAGGG",
  "genome_path": "/absolute/path/to/hg38.fa",
  "mismatches": 6,
  "device": "C"
}
```

Optimization:

```json
{
  "target_sequence": "GAGTCCGAGGAGAAGACGAAGGG",
  "genome_path": "/absolute/path/to/hg38.fa",
  "threshold": 0.8,
  "mismatches": 6,
  "device": "C"
}
```
