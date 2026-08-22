#!/bin/bash
set -e

# Bowtie2 short-alignment service (port 8024).
# Requires: bowtie2 binary on PATH (base env provides it), fastapi + uvicorn.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH}"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate base
command -v bowtie2 >/dev/null 2>&1 || {
  echo "bowtie2 not found. Install it (e.g. conda install -c bioconda bowtie2)."
  exit 1
}
python -m uvicorn main:app --host 0.0.0.0 --port 8024
