#!/bin/bash
# Exp-24 utilization monitor — logs aggregate CPU% and per-GPU utilization /
# memory every INTERVAL seconds (default 60) for the parallel campaign.
# CPU% is computed from two /proc/stat samples 1 s apart (all cores).
set -u
cd "$(dirname "$0")/.."
OUT=experiments/results/exp24_production_campaign/utilization.log
INTERVAL="${1:-60}"
mkdir -p "$(dirname "$OUT")"

while true; do
  ts=$(date '+%F %T')
  read -r _ u1 n1 s1 i1 w1 irq1 sirq1 st1 _ < /proc/stat
  sleep 1
  read -r _ u2 n2 s2 i2 w2 irq2 sirq2 st2 _ < /proc/stat
  t1=$((u1+n1+s1+i1+w1+irq1+sirq1+st1))
  t2=$((u2+n2+s2+i2+w2+irq2+sirq2+st2))
  idle1=$((i1+w1)); idle2=$((i2+w2))
  cpu=$(awk "BEGIN{printf \"%.1f\", 100*($t2-$t1-($idle2-$idle1))/($t2-$t1)}")
  gpus=$(nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader \
         | tr '\n' ';' | sed 's/ //g')
  echo "$ts cpu=${cpu}% ${gpus}" >> "$OUT"
  sleep "$((INTERVAL > 1 ? INTERVAL - 1 : 0))"
done
