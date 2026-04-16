#!/bin/bash
set -e

# 1) conda env create -f environment.yml
# 2) conda activate codonw_slim_service_env
# 3) bash install_codonw_slim.sh   # compiles codonw-slim with --no-build-isolation
# 4) bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate codonw_slim_service_env
python -c "from codonw import CodonSeq" 2>/dev/null || {
  echo "codonw-slim not installed. Run: bash install_codonw_slim.sh"
  exit 1
}
python -m uvicorn main:app --host 0.0.0.0 --port 8018
