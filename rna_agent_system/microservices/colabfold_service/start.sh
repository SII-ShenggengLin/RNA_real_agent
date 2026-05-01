#!/bin/bash
set -e

# ColabFold microservice startup script (port 8022)
#
# Deployment prerequisites:
#   1. conda env create -f environment.yml
#   2. conda activate colabfold_service_env
#   3. (Optional) Download AlphaFold params:
#        mkdir -p ~/.cache/colabfold/params
#        # colabfold_download  # when available
#   4. Ensure MMseqs2 is on PATH for MSA generation
#   5. bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate colabfold_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8022
