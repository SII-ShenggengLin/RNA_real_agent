# sgrna_design_service

FastAPI wrapper for `external_repos/sgrna_design` that exposes a stable REST API for sgRNA handle design.

## Endpoints

- `GET /health`
- `POST /design`

### `POST /design` request example

```json
{
  "seed_sequence": "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
  "n_samples": 10,
  "mutation_number": 22,
  "temperature": 1.0,
  "max_overlap": 21,
  "device": "cuda:0"
}
```

### Notes

- The service auto-falls back to CPU if `device` is omitted and CUDA is unavailable.
- It writes outputs under `rna_agent_system/workspace/sgrna_design_service/`.
- ViennaRNA (`import RNA`) is optional; if unavailable, structure-distance fields are omitted.

## Startup

```bash
cd rna_agent_system/microservices/sgrna_design_service
conda env create -f environment.yml
conda activate sgrna_design_service_env
bash start.sh
```
