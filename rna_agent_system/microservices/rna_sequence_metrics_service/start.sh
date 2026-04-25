#!/bin/bash
set -e

# 1) cd rna_agent_system/microservices/rna_sequence_metrics_service
# 2) conda env create -f environment.yml
# 3) conda activate rna_sequence_metrics_service_env
# 4) bash start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rna_sequence_metrics_service_env

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}/rna_agent_system:${PYTHONPATH}"
exec uvicorn rna_agent_system.microservices.rna_sequence_metrics_service.main:app \
  --host 0.0.0.0 \
  --port 8020
