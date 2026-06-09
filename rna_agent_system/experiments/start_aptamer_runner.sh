#!/usr/bin/env bash
# Safe startup script for rna_aptamer_design sequential runner.
# This script avoids the self-kill bug by using pgrep instead of grep on $0.

set -euo pipefail

PROJECT_ROOT="/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system"
LOG_FILE="/tmp/run_rna_aptamer_design_v5.log"
TEMP_FILE="${PROJECT_ROOT}/experiments/results/platform_coverage_rna_aptamer_design.jsonl"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting rna_aptamer_design runner..."

# Kill ONLY previous python processes (never match this shell script itself)
PREV_PIDS=$(pgrep -f "python.*run_workflow_sequential.*rna_aptamer" || true)
if [ -n "$PREV_PIDS" ]; then
    echo "Killing previous python runner(s): $PREV_PIDS"
    echo "$PREV_PIDS" | xargs -r kill 2>/dev/null || true
    sleep 3
fi

# Clean temp file from previous interrupted runs
rm -f "$TEMP_FILE"

cd "$PROJECT_ROOT"
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# Start runner with unbuffered output
python -u experiments/run_workflow_sequential.py rna_aptamer_design 2>&1 | tee "$LOG_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Runner finished."
