#!/bin/bash
# Exp 8 full matrix — lanes strictly sequential so no cross-lane GPU/CPU
# contention contaminates the timings (pre-registered in exp8_runtime.py).
# Assumes services are already healthy (exp1_bring_up_services.sh).
set -u
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD:${PYTHONPATH:-}"

RESULTS=experiments/results/exp8_runtime
mkdir -p "$RESULTS"
LOG="$RESULTS/run_all.log"

run() {
    echo "=== [$(date '+%F %T')] $* ===" | tee -a "$LOG"
    "$@" >> "$LOG" 2>&1
    rc=$?
    echo "=== [$(date '+%F %T')] exit $rc ===" | tee -a "$LOG"
    return $rc
}

run python experiments/exp8_runtime.py --lane gpu_aptamer --resume || true
run python experiments/exp8_runtime.py --lane gpu_tertiary --resume || true
run python experiments/exp8_runtime.py --lane cpu --resume || true
run python experiments/exp8_runtime.py --pa-batch --resume || true
run python experiments/exp8_runtime.py --summary
tail -n 25 "$LOG"
