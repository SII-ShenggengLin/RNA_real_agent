#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

UVICORN_HOST="${1:-0.0.0.0}"
UVICORN_PORT="${2:-8022}"

# Set Protenix data root to project directory so weights/cache stay inside the repo.
export PROTENIX_ROOT_DIR="$(cd "${SCRIPT_DIR}/../../external_repos/Protenix" && pwd)"

# Activate dedicated conda environment if available.
if command -v conda &> /dev/null && conda env list | grep -q "proteinx_service"; then
    echo "Activating proteinx_service conda environment"
    eval "$(conda shell.bash hook)"
    # conda activate scripts may reference unbound variables; allow it.
    set +u
    conda activate proteinx_service
    set -u
fi

command -v protenix &> /dev/null || {
    echo "protenix CLI not found. Install with: conda env create -f environment.yml"
    exit 1
}

exec uvicorn main:app --host "${UVICORN_HOST}" --port "${UVICORN_PORT}"
