# sgRNA Design Integration Notes

This document records how `sgrna_design` is integrated into this project.

## 1) Upstream repository

- Local path: `rna_agent_system/external_repos/sgrna_design`
- Upstream: <https://github.com/bitguolab/sgrna_design.git>

## 2) Why a wrapper is needed

Directly running upstream `sample.py` is fragile for deployment:

- `environment.yml` in upstream is incomplete.
- Runtime hardcodes `cuda:0`.
- It assumes a working ViennaRNA Python package import (`import RNA`).

The wrapper service stabilizes the API and provides better CPU/GPU handling.

## 3) Microservice location

- Service path: `rna_agent_system/microservices/sgrna_design_service`
- Port: `8017`
- Endpoints:
  - `GET /health`
  - `POST /design`

## 4) Agent integration points

- Tool layer: `agent_core/tools.py`
  - Added `design_sgrna_handle_with_crgpt(...)`
- Workflow layer: `agent_core/nodes.py`
  - Added CRISPR branch trigger for sgRNA-handle design keywords.
- State fields: `agent_core/state.py`
  - Added sgRNA-design result summary fields.

## 5) Linux deployment checklist

On your server clone (`/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent`):

```bash
cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/microservices/sgrna_design_service
conda env create -f environment.yml
conda activate sgrna_design_service_env
bash start.sh
```

Health check:

```bash
curl http://127.0.0.1:8017/health
```

Design check:

```bash
curl -X POST http://127.0.0.1:8017/design \
  -H "Content-Type: application/json" \
  -d '{
    "seed_sequence":"GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
    "n_samples":4,
    "mutation_number":20,
    "temperature":1.0
  }'
```
