#!/bin/bash
set -e

# Please run first:
# conda env create -f environment.yml
# Then start this service:
# bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate sgrna_design_service_env
python -m uvicorn main:app --host 0.0.0.0 --port 8017
