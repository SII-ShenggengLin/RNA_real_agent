#!/bin/bash
set -e

# 1) cd rna_agent_system/microservices/blast_service
# 2) conda env create -f environment.yml
# 3) conda activate blast_service_env
# 4) bash start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/rna_agent_system:${PYTHONPATH}"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate blast_service_env
command -v blastn >/dev/null 2>&1 || {
  echo "blastn not found. Install BLAST+ (e.g. conda install -c bioconda blast)."
  exit 1
}
python -m uvicorn main:app --host 0.0.0.0 --port 8019
