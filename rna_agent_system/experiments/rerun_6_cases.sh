#!/bin/bash
# Re-run 6 failed full_length_mrna_design cases sequentially
# to avoid blocking the single-threaded LinearDesign service.

cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd):$PYTHONPATH"

RESULTS_FILE="experiments/results/rerun_6_cases_$(date +%Y%m%d_%H%M%S).jsonl"
LOG_FILE="experiments/results/rerun_6_cases_$(date +%Y%m%d_%H%M%S).log"

echo "Results will be written to: $RESULTS_FILE" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "Start time: $(date -Iseconds)" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"

TASKS=(
    "02_full_length_mrna_design_004_reporter_gfp"
    "02_full_length_mrna_design_009_ovalbumin"
    "02_full_length_mrna_design_017_zebrafish_cai"
    "02_full_length_mrna_design_022_fly_cai"
    "02_full_length_mrna_design_010_edgecase"
    "02_full_length_mrna_design_002_vaccine_spike"
)

for TASK_ID in "${TASKS[@]}"; do
    echo ""
    echo "[$(date +%H:%M:%S)] Starting $TASK_ID ..." | tee -a "$LOG_FILE"
    START_EPOCH=$(date +%s)

    # Run the task through the standard system entrypoint
    JSON_OUTPUT=$(python experiments/run_single_task.py "$TASK_ID" 2>&1)
    EXIT_CODE=$?

    END_EPOCH=$(date +%s)
    ELAPSED=$((END_EPOCH - START_EPOCH))

    # Try to extract the last JSON line (result record)
    LAST_JSON=$(echo "$JSON_OUTPUT" | tail -n 1)

    echo "[$(date +%H:%M:%S)] Finished $TASK_ID | exit_code=$EXIT_CODE | elapsed=${ELAPSED}s" | tee -a "$LOG_FILE"

    # Write a combined record
    COMBINED=$(python3 -c "
import json, sys
last_line = sys.argv[1]
try:
    rec = json.loads(last_line)
except Exception:
    rec = {'raw_stdout': last_line, 'parse_error': True}
rec['task_id'] = '${TASK_ID}'
rec['runner_exit_code'] = ${EXIT_CODE}
rec['runner_elapsed_seconds'] = ${ELAPSED}
rec['runner_timestamp'] = '$(date -Iseconds)'
print(json.dumps(rec, ensure_ascii=False))
" "$LAST_JSON")
    echo "$COMBINED" >> "$RESULTS_FILE"

done

echo ""
echo "================================================" | tee -a "$LOG_FILE"
echo "All tasks completed at $(date -Iseconds)" | tee -a "$LOG_FILE"
echo "Results: $RESULTS_FILE" | tee -a "$LOG_FILE"
