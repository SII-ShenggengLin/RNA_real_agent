#!/bin/bash
set -e

# RiboDiffusion upstream expects PyTorch Geometric extensions matching torch+cuda.
# After `conda env create -f environment.yml`:
#   conda activate ribodiffusion_service_env
#   bash install_pyg_torch_extensions.sh
# Place checkpoint:
#   rna_agent_system/external_repos/RiboDiffusion/ckpts/exp_inf.pth
# (see https://github.com/ml4bio/RiboDiffusion README for download links.)
#
# Start:
#   bash start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$(conda info --base)/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  source "$(conda info --base)/etc/profile.d/conda.sh"
fi
conda activate ribodiffusion_service_env

python -m uvicorn main:app --host 0.0.0.0 --port 8021
