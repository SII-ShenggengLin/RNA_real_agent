#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repo root (parent of rna_agent_system/) so `rna_agent_system.microservices...` resolves on PYTHONPATH.
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

HOST="${IRESFINDER_SERVICE_HOST:-127.0.0.1}"
PORT="${IRESFINDER_SERVICE_PORT:-8013}"

cd "${REPO_ROOT}"
exec uvicorn rna_agent_system.microservices.iresfinder_service.main:app \
  --host "${HOST}" \
  --port "${PORT}"
