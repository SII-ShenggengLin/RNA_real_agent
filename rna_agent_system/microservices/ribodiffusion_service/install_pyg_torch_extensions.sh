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

_try_cpu_install() {
  local ver="$1"
  local url="https://data.pyg.org/whl/torch-${ver}+cpu.html"
  echo "Trying PyG wheel index: ${url}"
  pip install --no-cache-dir torch-scatter torch-sparse torch-cluster -f "${url}" && return 0 || return 1
}

if [ "${CUDA_TAG}" = "cpu" ] || [ -z "${CUDA_TAG}" ]; then
  echo "WARNING: CPU-only PyTorch; installing CPU PyG wheels where available." >&2
  if _try_cpu_install "${PYTORCH_VERSION}"; then
    exit 0
  fi
  IFS="." read -r MA MI _ <<< "${PYTORCH_VERSION}"
  _try_cpu_install "${MA}.${MI}.0"
  exit 0
fi

# Map CUDA MM.m -> cuMMM for PyG wheel URLs (e.g. 11.7 -> cu117).
CU_MAJOR="${CUDA_TAG%%.*}"
CU_MINOR_PATCH="${CUDA_TAG#*.}"
CU_MINOR="${CU_MINOR_PATCH%%.*}"
WHL_CUDA_TAG="cu${CU_MAJOR}${CU_MINOR}"

_try_cuda_install() {
  local ver="$1"
  local url="https://data.pyg.org/whl/torch-${ver}+${WHL_CUDA_TAG}.html"
  echo "Trying PyG wheel index: ${url}"
  pip install --no-cache-dir torch-scatter torch-sparse torch-cluster -f "${url}" && return 0 || return 1
}

if _try_cuda_install "${PYTORCH_VERSION}"; then
  exit 0
fi

# Wheels are often listed under patch .0 only (e.g. 1.13.0+cu117 for conda 1.13.1).
IFS="." read -r MA MI _ <<< "${PYTORCH_VERSION}"
FALLBACK_VER="${MA}.${MI}.0"
echo "Retrying with fallback torch version ${FALLBACK_VER}+${WHL_CUDA_TAG} (PyG wheel naming)." >&2
_try_cuda_install "${FALLBACK_VER}"
