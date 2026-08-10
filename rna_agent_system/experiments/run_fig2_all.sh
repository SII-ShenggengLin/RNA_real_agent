#!/bin/bash
# Fig 2 full orchestration (docs/MANUSCRIPT.md §4).
# Three shards intended to run concurrently as background tasks:
#   bash experiments/run_fig2_all.sh gpu    # GPU-heavy workflows (08 aptamer, 07 tertiary)
#   bash experiments/run_fig2_all.sh cpu_a  # CPU shard A (01-05) + CDS nulls
#   bash experiments/run_fig2_all.sh cpu_b  # CPU shard B (06,09,10,11) + literature panels
# All drivers append to per-shard JSONLs under experiments/results/ and support
# --resume, so re-launching after an interruption continues where it stopped.
set -u
cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

case "${1:?usage: run_fig2_all.sh gpu|cpu_a|cpu_b}" in
  gpu)
    python experiments/run_platform_quality_benchmark.py \
      --workflow 08_ --timeout 3600 --resume \
      --output experiments/results/fig2_gpu.jsonl
    python experiments/run_platform_quality_benchmark.py \
      --workflow 07_ --timeout 3600 --resume \
      --output experiments/results/fig2_gpu.jsonl
    ;;
  cpu_a)
    for w in 01_ 02_ 03_ 04_ 05_; do
      python experiments/run_platform_quality_benchmark.py \
        --workflow "$w" --timeout 3600 --resume \
        --output experiments/results/fig2_cpu_a.jsonl
    done
    python experiments/make_cds_nulls.py --timeout 3600
    ;;
  cpu_b)
    for w in 06_ 09_ 10_ 11_; do
      python experiments/run_platform_quality_benchmark.py \
        --workflow "$w" --timeout 3600 --resume \
        --output experiments/results/fig2_cpu_b.jsonl
    done
    python experiments/run_literature_panels.py --timeout 1800
    ;;
esac
