#!/usr/bin/env bash
# Build and install codonw-slim from the git submodule into the active conda env.
# Pip's isolated build env does not see conda-installed Cython; use --no-build-isolation.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RNA_AGENT_ROOT="$(cd "$HERE/../.." && pwd)"
CODONW_ROOT="${RNA_AGENT_ROOT}/external_repos/codonw-slim"

if [[ ! -f "${CODONW_ROOT}/setup.py" ]]; then
  echo "ERROR: Missing ${CODONW_ROOT}"
  echo "Run from repo root: git submodule update --init --recursive"
  exit 1
fi

if [[ -z "${CONDA_DEFAULT_ENV:-}" ]] || [[ "${CONDA_DEFAULT_ENV}" != "codonw_slim_service_env" ]]; then
  echo "Activating codonw_slim_service_env ..."
  # shellcheck source=/dev/null
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate codonw_slim_service_env
fi

# Upstream codonw.pyx uses ``astype(long)``; Python 3 / current Cython reject ``long`` in that
# expression ("undeclared name not builtin: long"). Use numpy dtype instead.
PYX="${CODONW_ROOT}/codonw/codonwlib/codonw.pyx"
if [[ -f "${PYX}" ]]; then
  echo "Ensuring Python3-compatible dinuc() dtype in codonw.pyx ..."
  CODONW_PYX="${PYX}" python <<'PY'
import os
from pathlib import Path

path = Path(os.environ["CODONW_PYX"])
text = path.read_text(encoding="utf-8")
if "astype(long)" in text:
    path.write_text(text.replace("astype(long)", "astype(np.int64)"), encoding="utf-8")
    print("Patched:", path)
elif "astype(np.int64)" in text:
    print("Already patched:", path)
PY
fi

echo "Installing codonw-slim editable from: ${CODONW_ROOT}"
pip install --no-build-isolation -e "${CODONW_ROOT}"

python -c "import codonw; from codonw import CodonSeq; print('codonw-slim OK:', CodonSeq)"
