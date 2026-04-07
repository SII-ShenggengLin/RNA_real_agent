#!/bin/bash
set -e

# Install CUDA-enabled PyG wheels that match:
# - torch 2.1.x
# - cu118
#
# Run this after:
#   conda env create -f environment.yml
#   conda activate gernabind_service_env

pip install --no-cache-dir \
  pyg-lib \
  torch-scatter \
  torch-sparse \
  torch-cluster \
  torch-spline-conv \
  -f https://data.pyg.org/whl/torch-2.1.0+cu118.html

pip install --no-cache-dir torch-geometric==2.4.0
