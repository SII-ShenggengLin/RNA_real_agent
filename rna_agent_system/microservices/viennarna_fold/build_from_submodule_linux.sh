#!/usr/bin/env bash
# Optional: build ViennaRNA from the git submodule and install into $PREFIX
# (typically your active conda env). Run on Linux after:
#   git submodule update --init --recursive rna_agent_system/external_repos/ViennaRNA
#
# Requires: autoconf, automake, libtool, pkg-config, a C/C++ compiler, swig (for Python),
#   plus steps from upstream README (libsvm / dlib tarballs under src/).
#
# Recommended path for this project remains:
#   conda env create -f environment.yml
# which installs bioconda `viennarna` including RNAlib.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="${ROOT}/external_repos/ViennaRNA"
PREFIX="${PREFIX:-${CONDA_PREFIX:-}}"

if [[ -z "${PREFIX}" ]]; then
  echo "Set CONDA_PREFIX (activate conda env) or PREFIX=... for install destination." >&2
  exit 1
fi

if [[ ! -d "${SRC}" ]]; then
  echo "Missing submodule at ${SRC}. Run: git submodule update --init --recursive" >&2
  exit 1
fi

echo "Source: ${SRC}"
echo "Install prefix: ${PREFIX}"

cd "${SRC}/src"
if [[ ! -d libsvm-3.35 ]]; then
  tar -xzf libsvm-3.35.tar.gz
fi
if [[ ! -d dlib-20.0 ]]; then
  tar -xjf dlib-20.0.tar.bz2
fi
cd "${SRC}"

autoreconf -i
./configure --prefix="${PREFIX}" --with-python
make -j"$(nproc 2>/dev/null || echo 4)"
make install

echo "Done. Reactivate the environment and verify: python -c 'import RNA; print(RNA.__file__)'"
