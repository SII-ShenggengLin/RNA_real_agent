# GEMORNA Integration Notes

## Upstream

- Repository: `https://github.com/RainaBio/GEMORNA.git`
- Local clone: `external_repos/GEMORNA`

## Current integration scope

- GEMORNA is exposed as a Conda-isolated FastAPI service under `microservices/gemorna_service/`.
- Current service endpoint:
  - `POST /generate/cds`
- Current Agent tool:
  - `design_mrna_cds_with_gemorna`

## Runtime requirements

1. Install `git-lfs`
2. Run inside `external_repos/GEMORNA`:
   - `git lfs install`
   - `git lfs pull`
3. Create the microservice environment:
   - `cd microservices/gemorna_service`
   - `conda env create -f environment.yml`
4. Start the service:
   - `bash start.sh`

## Known constraints

- `checkpoints/*.pt` must be real model files, not Git LFS pointer files.
- The current service validates LFS status before attempting generation.
- The first integrated ability is CDS design from a protein sequence.

## Planned next steps

- Add 5' UTR / 3' UTR generation endpoints
- Add prediction endpoints for 5' UTR and 3' UTR
- Replace rule-based dispatch with configurable routing after tool chain stabilizes
