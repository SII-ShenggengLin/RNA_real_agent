#!/bin/bash
set -e

# EGARPS+ microservice startup script (port 8023)
# Requires: conda environment 'egarps_env' with EGARPS dependencies installed

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SOURCE_DIR}"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate base
python -m uvicorn main:app --host 0.0.0.0 --port 8023
