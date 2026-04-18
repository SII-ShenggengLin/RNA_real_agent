#!/bin/bash
# Install torch-scatter / torch-sparse / torch-cluster for the *currently active*
# Python + torch+cuda build. RiboDiffusion imports torch_geometric at runtime.
set -euo pipefail

TORCH_V=$(python - <<'PY'
import torch
v = torch.__version__.split("+")[0]
cuda = torch.version.cuda or "cpu"
print(f"{v};{cuda}")
PY
)

PYTORCH_VERSION="${TORCH_V%%;*}"
CUDA_TAG="${TORCH_V##*;}"

echo "Detected torch ${PYTORCH_VERSION}, cuda ${CUDA_TAG}"

if [ "${CUDA_TAG}" = "cpu" ] || [ -z "${CUDA_TAG}" ]; then
  echo "WARNING: CPU-only PyTorch; installing CPU PyG wheels where available." >&2
  pip install --no-cache-dir torch-scatter torch-sparse torch-cluster -f "https://data.pyg.org/whl/torch-${PYTORCH_VERSION}+cpu.html"
  exit 0
fi

# Map torch X.Y.Z + CUDA MM.m -> PyG wheel index torch-X.Y.Z+cuMMM (e.g. cu117).
CU_MAJOR="${CUDA_TAG%%.*}"
CU_MINOR_PATCH="${CUDA_TAG#*.}"
CU_MINOR="${CU_MINOR_PATCH%%.*}"
WHL_CUDA_TAG="cu${CU_MAJOR}${CU_MINOR}"

BASE="torch-${PYTORCH_VERSION}+${WHL_CUDA_TAG}"
URL="https://data.pyg.org/whl/${BASE}.html"

echo "Using PyG wheel index: ${URL}"

pip install --no-cache-dir \
  torch-scatter torch-sparse torch-cluster \
  -f "${URL}"
