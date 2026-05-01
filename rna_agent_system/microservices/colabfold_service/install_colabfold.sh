#!/bin/bash
set -e

# ColabFold first-time installation helper
# Run this AFTER creating the conda environment from environment.yml

echo "=== Activating colabfold_service_env ==="
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate colabfold_service_env

echo "=== Installing JAX with CUDA support ==="
# Adjust CUDA version to match your system (e.g. cuda11, cuda12)
pip install "jax[cuda12_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html

echo "=== Installing ColabFold ==="
pip install "colabfold[alphafold]"

echo "=== Downloading AlphaFold parameters (~3-5 GB) ==="
# This requires network access and may take several minutes
python -c "from colabfold.download import download; download()" || echo "Download skipped or failed."

echo "=== Checking MMseqs2 availability ==="
which mmseqs || echo "WARNING: MMseqs2 not found. Install via conda: conda install -c bioconda mmseqs2"

echo "=== Installation helper complete ==="
echo "Start the service with: bash start.sh"
