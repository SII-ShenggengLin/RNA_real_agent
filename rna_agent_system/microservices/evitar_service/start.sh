#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

HOST="${EVITAR_SERVICE_HOST:-127.0.0.1}"
PORT="${EVITAR_SERVICE_PORT:-8016}"

cd "${REPO_ROOT}"
exec uvicorn rna_agent_system.microservices.evitar_service.main:app \
  --host "${HOST}" \
  --port "${PORT}"
