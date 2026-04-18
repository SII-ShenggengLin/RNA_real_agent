#!/bin/bash
# Install torch-scatter / torch-sparse / torch-cluster for the *currently active*
# Python + torch+cuda build. RiboDiffusion imports torch_geometric at runtime.
#
# Notes:
# - pip may fall back to building from sdist; isolated builds do not see `torch`, so we pass
#   --no-build-isolation so the active env's PyTorch is available if a compile happens.
# - PyG often publishes torch-1.13.x wheels under cu116; conda may report cuda 11.7 — we retry cu116
#   if cu117 only yields sdist (matches upstream RiboDiffusion pt113cu116 pins).
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

# pip must see `torch` during any fallback sdist build
PIP_PYG=(pip install --no-cache-dir --no-build-isolation)

_try_cpu_install() {
  local ver="$1"
  local url="https://data.pyg.org/whl/torch-${ver}+cpu.html"
  echo "Trying PyG wheel index: ${url}"
  "${PIP_PYG[@]}" torch-scatter torch-sparse torch-cluster -f "${url}" && return 0 || return 1
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

_try_cuda_install_url() {
  local ver="$1"
  local cu_tag="$2"
  local url="https://data.pyg.org/whl/torch-${ver}+${cu_tag}.html"
  echo "Trying PyG wheel index: ${url}"
  "${PIP_PYG[@]}" torch-scatter torch-sparse torch-cluster -f "${url}" && return 0 || return 1
}

IFS="." read -r MA MI _ <<< "${PYTORCH_VERSION}"
FALLBACK_VER="${MA}.${MI}.0"

# 1) Exact torch version + detected CUDA tag (e.g. 1.13.1 + cu117)
if _try_cuda_install_url "${PYTORCH_VERSION}" "${WHL_CUDA_TAG}"; then
  exit 0
fi

# 2) Patch .0 + same CUDA tag (PyG listing convention)
echo "Retrying with fallback torch version ${FALLBACK_VER}+${WHL_CUDA_TAG}." >&2
if _try_cuda_install_url "${FALLBACK_VER}" "${WHL_CUDA_TAG}"; then
  exit 0
fi

# 3) cu116 wheels: RiboDiffusion upstream uses pt113cu116; conda sometimes has 11.7 but PyG cu117 index has no binary wheels.
if [ "${WHL_CUDA_TAG}" != "cu116" ]; then
  echo "Retrying with cu116 wheel indices (common for torch 1.13 + PyG; see RiboDiffusion requirements.txt)." >&2
  if _try_cuda_install_url "${PYTORCH_VERSION}" "cu116"; then
    exit 0
  fi
  if _try_cuda_install_url "${FALLBACK_VER}" "cu116"; then
    exit 0
  fi
fi

echo "ERROR: Could not install torch-scatter / torch-sparse / torch-cluster." >&2
echo "Check: python -c \"import torch; print(torch.__version__, torch.version.cuda)\"" >&2
echo "Try manually: ${PIP_PYG[*]} torch-scatter torch-sparse torch-cluster -f https://data.pyg.org/whl/torch-${FALLBACK_VER}+cu116.html" >&2
exit 1
