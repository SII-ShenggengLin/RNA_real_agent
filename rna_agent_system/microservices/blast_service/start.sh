#!/bin/bash
set -e

# 1) cd rna_agent_system/microservices/blast_service
# 2) conda env create -f environment.yml
# 3) conda activate blast_service_env
# 4) bash start.sh

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate blast_service_env
command -v blastn >/dev/null 2>&1 || {
  echo "blastn not found. Install BLAST+ (e.g. conda install -c bioconda blast)."
  exit 1
}
python -m uvicorn main:app --host 0.0.0.0 --port 8019
