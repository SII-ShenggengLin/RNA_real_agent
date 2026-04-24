# sgrna_design_service

FastAPI wrapper for `external_repos/sgrna_design` that exposes a stable REST API for sgRNA handle design.

Supports both the original **MCMC annealing** (`sample.py`) and **naive direct generation** (`naive_sample.py`) modes.

## Endpoints

- `GET /health`
- `POST /design`
- `POST /score`

### `POST /design` request example (MCMC mode — default)

```json
{
  "seed_sequence": "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
  "n_samples": 10,
  "mutation_number": 22,
  "temperature": 20.0,
  "max_overlap": 21,
  "sampling_mode": "mcmc",
  "device": "cuda:0"
}
```

### `POST /design` request example (naive mode)

```json
{
  "seed_sequence": "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
  "n_samples": 10,
  "mutation_number": 22,
  "temperature": 1.0,
  "max_overlap": 21,
  "sampling_mode": "naive",
  "device": "cuda:0"
}
```

### Request fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `seed_sequence` | `string?` | `null` | Seed/wildtype sgRNA handle sequence (DNA/RNA). Falls back to built-in 61-nt wildtype if omitted. |
| `n_samples` | `int` | `10` | Number of designed candidates to generate. |
| `mutation_number` | `int` | `22` | Maximum mutation count relative to seed. |
| `temperature` | `float?` | `null` | MCMC annealing temperature (mcmc, defaults to 20.0) or transformer sampling temperature (naive, defaults to 1.0). |
| `max_length` | `int?` | `null` | Optional target sequence length for naive mode (overrides auto-computed `max_new_tokens`). |
| `max_overlap` | `int` | `21` | Maximum longest-common-substring overlap among accepted sequences. |
| `sampling_mode` | `string` | `"mcmc"` | `"mcmc"` (original MCMC/annealing) or `"naive"` (direct `model.generate`). |
| `path_to_model` | `string?` | `null` | Model directory override. |
| `device` | `string?` | `null` | Torch device, e.g. `cuda:0` or `cpu`. |
| `output_dir` | `string?` | `null` | Output directory override. Defaults to `workspace/sgrna_design_service/`. |

### `POST /score` request example

```json
{
  "sequence": "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
  "device": "cuda:0"
}
```

**Response fields**: `sequence`, `normalized_sequence`, `nn_score`, `log_likelihood`, `structure_distance`, `mfe`, `constraint_mutation_count`.

### Notes

- The service auto-falls back to CPU if `device` is omitted and CUDA is unavailable.
- **MCMC mode requires ViennaRNA** (`import RNA`). If unavailable, the service returns a clear error.
- It writes outputs under `rna_agent_system/workspace/sgrna_design_service/` (or `output_dir` if provided).
- Outputs include: `.fasta`, `.ali` (alignment, MCMC mode only), and `.json` summary.

## Startup

```bash
cd rna_agent_system/microservices/sgrna_design_service
conda env create -f environment.yml
conda activate sgrna_design_service_env
bash start.sh
```
