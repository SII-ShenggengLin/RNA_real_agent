#!/bin/bash
set -e

# 1) conda env create -f environment.yml
# 2) conda activate sirna_attsioff_env
# 3) bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate sirna_attsioff_env
python -m uvicorn main:app --host 0.0.0.0 --port 8001
