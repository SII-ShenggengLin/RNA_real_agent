#!/bin/bash
# Run remaining platform coverage tasks sequentially.
# This is a robust fallback when run_platform_coverage.py subprocess runner
# encounters session-management issues.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS_FILE="$PROJECT_ROOT/experiments/results/platform_coverage.jsonl"
LOG_FILE="/tmp/run_remaining_tasks.log"

cd "$PROJECT_ROOT"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

python3 -c "
import json, sys
from data.benchmarks.rna_biobench_loader import load_platform_tasks

with open('${RESULTS_FILE}', 'r') as f:
    completed = {json.loads(line)['task_id'] for line in f if line.strip()}

tasks = load_platform_tasks()
remaining = [t for t in tasks if t.task_id not in completed]

print(f'Remaining tasks: {len(remaining)}')
for t in remaining:
    print(t.task_id)
" > /tmp/remaining_task_ids.txt

TOTAL=$(wc -l < /tmp/remaining_task_ids.txt)
IDX=0

while IFS= read -r task_id; do
    IDX=$((IDX + 1))
    echo "[$IDX/$TOTAL] Running $task_id" | tee -a "$LOG_FILE"

    # Run task and capture last line of stdout as JSON
    if python3 experiments/run_single_task.py "$task_id" > /tmp/task_result.json 2>> "$LOG_FILE"; then
        # Append valid result
        if [ -s /tmp/task_result.json ]; then
            echo "$(tail -n 1 /tmp/task_result.json)" >> "$RESULTS_FILE"
            echo "  -> appended to results" | tee -a "$LOG_FILE"
        else
            echo "  -> EMPTY OUTPUT" | tee -a "$LOG_FILE"
        fi
    else
        echo "  -> FAILED (exit code $?)" | tee -a "$LOG_FILE"
    fi
done < /tmp/remaining_task_ids.txt

echo "All remaining tasks completed. Results in $RESULTS_FILE" | tee -a "$LOG_FILE"
