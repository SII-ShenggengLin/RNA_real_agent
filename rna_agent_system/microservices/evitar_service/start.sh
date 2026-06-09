#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

HOST="${EVITAR_SERVICE_HOST:-127.0.0.1}"
PORT="${EVITAR_SERVICE_PORT:-8016}"

# Activate the Evitar conda environment so that Rscript is on PATH.
# This is required for CRISPR mode (predict=CRISPR) which invokes
# Rscript via Evitar.pl.
if [ -f "$(conda info --base)/etc/profile.d/conda.sh" ]; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate evitar_service_env
fi

cd "${REPO_ROOT}"
exec uvicorn rna_agent_system.microservices.evitar_service.main:app \
  --host "${HOST}" \
  --port "${PORT}"
